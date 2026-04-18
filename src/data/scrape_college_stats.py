"""
Scrape college football final-season stats for every drafted player in
data/processed/draft_with_combine.csv, using sports-reference.com/cfb.

- Browser-based (undetected_chromedriver) because CFB Reference sits behind
  Cloudflare and blocks plain requests / cloudscraper.
- Resumable: already-scraped players and previously-errored players are skipped
  on restart.
- 3-second polite delay between requests.
- Writes partial progress to CSV after every player.

Outputs:
  data/raw/college_stats_2011_2025.csv
  data/raw/college_stats_errors.csv
  data/processed/draft_with_college.csv  (final merge step)
"""

import csv
import time
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import undetected_chromedriver as uc
from bs4 import BeautifulSoup, Comment
from selenium.common.exceptions import TimeoutException, WebDriverException

ROOT = Path(__file__).resolve().parents[2]
INPUT_CSV = ROOT / "data" / "processed" / "draft_with_combine.csv"
OUTPUT_CSV = ROOT / "data" / "raw" / "college_stats_2011_2025.csv"
ERROR_CSV = ROOT / "data" / "raw" / "college_stats_errors.csv"
MERGED_CSV = ROOT / "data" / "processed" / "draft_with_college.csv"

SEARCH_URL = "https://www.sports-reference.com/cfb/search/search.fcgi?search={q}"

REQUEST_DELAY_SEC = 3.0

QB_POS = {"QB"}
SKILL_POS = {"RB", "WR", "TE", "FB", "HB"}
OL_POS = {"C", "G", "OG", "OT", "T", "OL"}

OUT_COLUMNS = [
    "player", "college", "year", "position", "position_group",
    "final_season_year", "seasons_played", "career_games",
    # QB
    "pass_games", "pass_cmp", "pass_att", "pass_cmp_pct",
    "pass_yds", "pass_td", "pass_int",
    # Rushing (QB + SKILL)
    "rush_att", "rush_yds", "rush_td",
    # Receiving (SKILL)
    "rec", "rec_yds", "rec_td",
    # OL
    "ol_games",
    # Defense
    "def_games", "tackles", "sacks", "def_int_stat", "pass_def",
]

ERROR_COLUMNS = ["player", "college", "year", "position", "reason", "detail"]


def position_group(pos: str | None) -> str:
    p = (pos or "").upper()
    if p in QB_POS:
        return "QB"
    if p in SKILL_POS:
        return "SKILL"
    if p in OL_POS:
        return "OL"
    return "DEF"


def create_driver() -> uc.Chrome:
    opts = uc.ChromeOptions()
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,720")
    # 'eager' returns control as soon as DOMContentLoaded fires, skipping
    # the long tail of third-party script onload events.
    opts.page_load_strategy = "eager"
    driver = uc.Chrome(options=opts)
    driver.set_page_load_timeout(15)
    driver.set_script_timeout(10)
    return driver


def get_soup_allowing_comments(html: str) -> BeautifulSoup:
    """Return a soup where all commented-out HTML has been spliced back in.
    sports-reference wraps most stat tables in HTML comments."""
    soup = BeautifulSoup(html, "lxml")
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        text = str(comment)
        if "<table" in text:
            comment.replace_with(BeautifulSoup(text, "lxml"))
    return soup


def cell_text(tr, stat):
    c = tr.find(["td", "th"], attrs={"data-stat": stat})
    return c.get_text(strip=True) if c else ""


def to_float(s):
    if s is None or s == "":
        return None
    try:
        return float(s.replace("%", "").replace(",", ""))
    except (ValueError, AttributeError):
        return None


def season_rows(table) -> list:
    """Return non-summary <tr> rows from a stats table (one per season)."""
    if table is None:
        return []
    tbody = table.find("tbody")
    if tbody is None:
        return []
    out = []
    for tr in tbody.find_all("tr"):
        classes = tr.get("class") or []
        if "thead" in classes:
            continue
        year = cell_text(tr, "year_id")
        if not year or year.lower().startswith("career"):
            continue
        out.append(tr)
    return out


def pick_final_season(rows):
    """Return the row with the highest year_id (the final college season)."""
    if not rows:
        return None
    def year_key(tr):
        y = cell_text(tr, "year_id").strip("*")
        try:
            return int(y[:4])
        except ValueError:
            return -1
    return max(rows, key=year_key)


def extract_stats(soup: BeautifulSoup, pgroup: str) -> dict:
    """Pull final-season + career stats for the given position group."""
    out = {k: None for k in OUT_COLUMNS if k not in
           ("player", "college", "year", "position", "position_group")}

    # Find tables. sports-reference updated IDs to use a "_standard" suffix.
    passing = (soup.find("table", id="passing_standard")
               or soup.find("table", id="passing"))
    rush_rec = (soup.find("table", id="rushing_standard")
                or soup.find("table", id="receiving_standard")
                or soup.find("table", id="rushing_and_receiving")
                or soup.find("table", id="receiving_and_rushing"))
    defense = (soup.find("table", id="defense_standard")
               or soup.find("table", id="defense_and_fumbles")
               or soup.find("table", id="defense"))
    scoring = (soup.find("table", id="scoring_standard")
               or soup.find("table", id="scoring"))

    # Gather all season years across all tables we care about, to derive
    # seasons_played and final_season_year.
    all_years, all_games = set(), 0
    for t in (passing, rush_rec, defense, scoring):
        for tr in season_rows(t):
            y = cell_text(tr, "year_id").strip("*")
            try:
                all_years.add(int(y[:4]))
            except ValueError:
                pass

    if all_years:
        out["final_season_year"] = max(all_years)
        out["seasons_played"] = len(all_years)

    # Career games: sum "g" across seasons of the primary position's table
    # (or the most-populated table we have).
    primary_table = None
    if pgroup == "QB":
        primary_table = passing or rush_rec
    elif pgroup == "SKILL":
        primary_table = rush_rec
    elif pgroup == "DEF":
        primary_table = defense
    elif pgroup == "OL":
        primary_table = scoring or rush_rec or defense  # OL rarely has own table
    if primary_table is not None:
        total_g = 0
        for tr in season_rows(primary_table):
            g = to_float((cell_text(tr, "games") or cell_text(tr, "g")))
            if g is not None:
                total_g += g
        if total_g:
            out["career_games"] = total_g

    # Scope the detail stats to the position group so a QB's incidental tackle
    # doesn't populate defensive columns (and vice-versa).
    want_passing = pgroup == "QB"
    want_rushrec = pgroup in ("QB", "SKILL")
    want_defense = pgroup == "DEF"

    # QB passing stats (final season)
    if want_passing and passing is not None:
        tr = pick_final_season(season_rows(passing))
        if tr is not None:
            out["pass_games"] = to_float((cell_text(tr, "games") or cell_text(tr, "g")))
            out["pass_cmp"] = to_float(cell_text(tr, "pass_cmp"))
            out["pass_att"] = to_float(cell_text(tr, "pass_att"))
            out["pass_cmp_pct"] = to_float(cell_text(tr, "pass_cmp_pct"))
            out["pass_yds"] = to_float(cell_text(tr, "pass_yds"))
            out["pass_td"] = to_float(cell_text(tr, "pass_td"))
            out["pass_int"] = to_float(cell_text(tr, "pass_int"))

    # Rushing / receiving stats (final season)
    if want_rushrec and rush_rec is not None:
        tr = pick_final_season(season_rows(rush_rec))
        if tr is not None:
            out["rush_att"] = to_float(cell_text(tr, "rush_att"))
            out["rush_yds"] = to_float(cell_text(tr, "rush_yds"))
            out["rush_td"] = to_float(cell_text(tr, "rush_td"))
            out["rec"] = to_float(cell_text(tr, "rec"))
            out["rec_yds"] = to_float(cell_text(tr, "rec_yds"))
            out["rec_td"] = to_float(cell_text(tr, "rec_td"))

    # Defense (final season)
    if want_defense and defense is not None:
        tr = pick_final_season(season_rows(defense))
        if tr is not None:
            out["def_games"] = to_float((cell_text(tr, "games") or cell_text(tr, "g")))
            # Prefer total tackles; fall back to solo
            tackles = (cell_text(tr, "tackles_combined")
                       or cell_text(tr, "tackles_total")
                       or cell_text(tr, "tackles_solo"))
            out["tackles"] = to_float(tackles)
            out["sacks"] = to_float(cell_text(tr, "sacks"))
            out["def_int_stat"] = to_float(cell_text(tr, "def_int"))
            # Column called either pass_defended or pass_def depending on season
            pd_ = cell_text(tr, "pass_defended") or cell_text(tr, "pass_def")
            out["pass_def"] = to_float(pd_)

    # OL: if there's a scoring/rush_rec table we can still report g from it
    if pgroup == "OL":
        for t in (scoring, rush_rec, defense):
            if t is None:
                continue
            tr = pick_final_season(season_rows(t))
            if tr is not None:
                g = to_float((cell_text(tr, "games") or cell_text(tr, "g")))
                if g is not None:
                    out["ol_games"] = g
                    break

    return out


def find_player_links(search_html: str):
    """Return list of (name, href) from a CFB search results page."""
    soup = BeautifulSoup(search_html, "lxml")
    links = []
    for item in soup.select("div.search-item"):
        a = item.find("a", href=True)
        if a and "/cfb/players/" in a["href"]:
            name = a.get_text(strip=True)
            links.append((name, a["href"]))
    # Dedupe while preserving order
    seen, out = set(), []
    for name, href in links:
        if href in seen:
            continue
        seen.add(href)
        out.append((name, href))
    return out


def fetch(driver, url, wait=2):
    """Navigate and return (final_url, html). Recovers from page-load hangs."""
    try:
        driver.get(url)
    except TimeoutException:
        try:
            driver.execute_script("window.stop();")
        except WebDriverException:
            pass
    time.sleep(wait)
    # If Cloudflare is still challenging, give it one more chance
    try:
        if "Just a moment" in driver.title:
            time.sleep(6)
    except WebDriverException:
        pass
    try:
        return driver.current_url, driver.page_source
    except WebDriverException:
        return url, ""


def scrape_player(driver, player: str, college: str, pgroup: str):
    """Return (stats_dict_or_None, error_reason_or_None, detail)."""
    search_url = SEARCH_URL.format(q=quote_plus(player))
    final_url, html = fetch(driver, search_url)

    # Case 1: redirected straight to a player page
    if "/cfb/players/" in final_url:
        soup = get_soup_allowing_comments(html)
        return extract_stats(soup, pgroup), None, final_url

    # Case 2: landed on a search results page
    if "/cfb/search/" in final_url:
        links = find_player_links(html)
        if not links:
            return None, "no_results", ""
        if len(links) > 1:
            # Try to disambiguate by college substring in the displayed label
            coll = (college or "").lower()
            matches = [l for l in links if coll and coll[:6] in l[0].lower()]
            if len(matches) == 1:
                links = matches
            else:
                return None, "multiple_results", f"{len(links)} results"

        # Single link -> follow it
        href = links[0][1]
        if href.startswith("/"):
            href = "https://www.sports-reference.com" + href
        time.sleep(REQUEST_DELAY_SEC)
        final_url, html = fetch(driver, href)
        if "/cfb/players/" not in final_url:
            return None, "redirect_failed", final_url
        soup = get_soup_allowing_comments(html)
        return extract_stats(soup, pgroup), None, final_url

    return None, "unexpected_url", final_url


def load_already_done():
    done = set()
    if OUTPUT_CSV.exists():
        df = pd.read_csv(OUTPUT_CSV)
        done.update(zip(df["player"].astype(str), df["year"].astype(int)))
    if ERROR_CSV.exists():
        df = pd.read_csv(ERROR_CSV)
        done.update(zip(df["player"].astype(str), df["year"].astype(int)))
    return done


def ensure_files():
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    if not OUTPUT_CSV.exists():
        with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(OUT_COLUMNS)
    if not ERROR_CSV.exists():
        with ERROR_CSV.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(ERROR_COLUMNS)


def append_row(path: Path, row: list):
    with path.open("a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)


def run_scrape():
    drafts = pd.read_csv(INPUT_CSV)
    drafts = drafts.dropna(subset=["player", "year"]).copy()
    drafts["year"] = drafts["year"].astype(int)
    players = drafts[["player", "college", "year", "position"]].drop_duplicates()
    players["position_group"] = players["position"].apply(position_group)

    ensure_files()
    done = load_already_done()
    todo = players[~players.apply(
        lambda r: (str(r["player"]), int(r["year"])) in done, axis=1
    )].reset_index(drop=True)

    print(f"Total unique players: {len(players)}")
    print(f"Already processed:    {len(players) - len(todo)}")
    print(f"Remaining to scrape:  {len(todo)}")
    print(f"Est. runtime:         ~{len(todo) * REQUEST_DELAY_SEC / 60:.0f} min "
          f"(at {REQUEST_DELAY_SEC:.0f}s/player, excluding page-load time)")
    print("-" * 60)

    if todo.empty:
        return

    driver = create_driver()
    # Warm up Cloudflare
    driver.get("https://www.sports-reference.com/cfb/")
    time.sleep(8)

    try:
        for i, row in todo.iterrows():
            player = str(row["player"])
            college = str(row["college"]) if pd.notna(row["college"]) else ""
            year = int(row["year"])
            pos = str(row["position"]) if pd.notna(row["position"]) else ""
            pgroup = row["position_group"]

            print(f"[{i+1}/{len(todo)}] {player} ({pos}, {college}, {year}) ...",
                  end=" ", flush=True)
            try:
                stats, err, detail = scrape_player(driver, player, college, pgroup)
            except Exception as e:
                # Recover from driver crashes
                err = "exception"
                detail = str(e)[:200]
                stats = None
                try:
                    driver.quit()
                except Exception:
                    pass
                time.sleep(5)
                driver = create_driver()
                driver.get("https://www.sports-reference.com/cfb/")
                time.sleep(8)

            if stats is not None:
                base = {
                    "player": player, "college": college, "year": year,
                    "position": pos, "position_group": pgroup,
                }
                base.update(stats)
                append_row(OUTPUT_CSV, [base.get(c) for c in OUT_COLUMNS])
                print(f"OK (final_yr={base.get('final_season_year')})")
            else:
                append_row(ERROR_CSV, [player, college, year, pos, err, detail])
                print(f"SKIP ({err})")

            time.sleep(REQUEST_DELAY_SEC)
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def merge_with_drafts():
    drafts = pd.read_csv(INPUT_CSV)
    stats = pd.read_csv(OUTPUT_CSV)
    # Merge on (player, year); keep all draft picks.
    stats_for_merge = stats.drop(columns=["position", "college"], errors="ignore")
    merged = drafts.merge(stats_for_merge, how="left", on=["player", "year"])
    MERGED_CSV.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(MERGED_CSV, index=False)
    return merged, stats


def print_summary(merged: pd.DataFrame, stats: pd.DataFrame):
    drafts = pd.read_csv(INPUT_CSV)
    drafts["position_group"] = drafts["position"].apply(position_group)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    n_matched = merged["position_group"].notna().sum()
    print(f"Players with college stats: {len(stats)} / {len(drafts)} "
          f"({len(stats)/len(drafts)*100:.1f}%)")

    print("\nMatch rate by position group:")
    grp_all = drafts.groupby("position_group").size()
    matched = stats.merge(drafts[["player", "year", "position_group"]],
                          on=["player", "year"], how="inner")
    grp_matched = matched.groupby("position_group").size()
    for g in ("QB", "SKILL", "OL", "DEF"):
        total = int(grp_all.get(g, 0))
        hit = int(grp_matched.get(g, 0))
        rate = hit / total * 100 if total else 0.0
        print(f"  {g:<6} {hit:>4}/{total:<4} ({rate:.1f}%)")

    print("\nColumns with >30% missing in merged output "
          "(among rows that got matched):")
    stat_cols = [c for c in OUT_COLUMNS
                 if c not in ("player", "college", "year", "position",
                              "position_group")]
    flagged = []
    match_mask = merged["position_group"].notna()
    sub = merged.loc[match_mask]
    for c in stat_cols:
        if c not in sub.columns:
            continue
        pct = sub[c].isna().mean() * 100
        if pct > 30:
            flagged.append((c, pct))
    for c, pct in sorted(flagged, key=lambda x: -x[1]):
        print(f"  - {c}: {pct:.1f}% missing")
    if not flagged:
        print("  (none)")

    err_rows = 0
    if ERROR_CSV.exists():
        err_rows = max(0, sum(1 for _ in ERROR_CSV.open(encoding="utf-8")) - 1)
    print(f"\nError log rows: {err_rows}  ({ERROR_CSV})")

    print(f"\nOutputs:")
    print(f"  {OUTPUT_CSV}")
    print(f"  {ERROR_CSV}")
    print(f"  {MERGED_CSV}")


def main():
    run_scrape()
    merged, stats = merge_with_drafts()
    print_summary(merged, stats)


if __name__ == "__main__":
    main()
