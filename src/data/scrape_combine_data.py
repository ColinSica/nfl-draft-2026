"""
Scrape NFL Scouting Combine data (2011-2025) from Pro Football Reference.
Uses undetected_chromedriver to bypass Cloudflare protection.
Saves combine data to data/raw/combine_data_2011_2025.csv, then merges
with historical draft data to produce data/processed/draft_with_combine.csv.
"""

import time
from pathlib import Path

import pandas as pd
import undetected_chromedriver as uc
from bs4 import BeautifulSoup, Comment

PRIMARY_URL = (
    "https://www.pro-football-reference.com/play-index/"
    "nfl-combine-results.cgi?request=1&year_min={year}&year_max={year}"
)
FALLBACK_URL = "https://www.pro-football-reference.com/draft/{year}-combine.htm"

YEARS = range(2011, 2026)
ROOT = Path(__file__).resolve().parents[2]
RAW_OUTPUT = ROOT / "data" / "raw" / "combine_data_2011_2025.csv"
DRAFT_INPUT = ROOT / "data" / "raw" / "historical_drafts_2011_2025.csv"
MERGED_OUTPUT = ROOT / "data" / "processed" / "draft_with_combine.csv"

REQUEST_DELAY_SEC = 2.0

# PFR data-stat -> our column name
COLUMNS_MAP = {
    "player": "player",
    "pos": "position",
    "school": "college",
    "college": "college",   # fallback stat name used on some pages
    "height": "height",
    "weight": "weight",
    "forty_yd": "40_yard",
    "vertical": "vertical",
    "bench_reps": "bench_press",
    "broad_jump": "broad_jump",
    "cone": "three_cone",
    "shuttle": "shuttle",
}

COMBINE_METRIC_COLS = [
    "height", "weight", "40_yard", "vertical",
    "bench_press", "broad_jump", "three_cone", "shuttle",
]


def create_driver() -> uc.Chrome:
    opts = uc.ChromeOptions()
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,720")
    return uc.Chrome(options=opts)


def fetch_page(driver: uc.Chrome, url: str) -> str | None:
    try:
        driver.get(url)
        time.sleep(5)
        if "Just a moment" in driver.title:
            print("  Waiting for Cloudflare challenge...", end=" ", flush=True)
            time.sleep(10)
        if "Just a moment" in driver.title:
            print("  ERROR: stuck on Cloudflare challenge")
            return None
        return driver.page_source
    except Exception as e:
        print(f"  ERROR fetching {url}: {e}")
        return None


def find_combine_table(html: str):
    """Locate the combine results table. PFR sometimes hides it in HTML comments."""
    soup = BeautifulSoup(html, "lxml")

    # Try direct find with a few known IDs
    for table_id in ("combine", "results"):
        table = soup.find("table", id=table_id)
        if table is not None:
            return table

    # Look inside HTML comments
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        if 'id="combine"' in comment or 'id="results"' in comment:
            comment_soup = BeautifulSoup(comment, "lxml")
            for table_id in ("combine", "results"):
                table = comment_soup.find("table", id=table_id)
                if table is not None:
                    return table

    # Last resort: first table with combine-looking columns
    for table in soup.find_all("table"):
        if table.find(attrs={"data-stat": "forty_yd"}):
            return table

    return None


def parse_combine_table(html: str, year: int) -> list[dict]:
    table = find_combine_table(html)
    if table is None:
        print(f"  WARNING: No combine table found for {year}")
        return []

    tbody = table.find("tbody")
    if tbody is None:
        return []

    rows = []
    for tr in tbody.find_all("tr"):
        if tr.get("class") and "thead" in tr["class"]:
            continue

        row = {"year": year}
        for stat_name, col_name in COLUMNS_MAP.items():
            cell = tr.find(["td", "th"], attrs={"data-stat": stat_name})
            if cell is None:
                # Don't overwrite a value that was set by an alias (e.g. school vs college)
                row.setdefault(col_name, None)
                continue
            if stat_name == "player":
                link = cell.find("a")
                row[col_name] = link.get_text(strip=True) if link else cell.get_text(strip=True)
            else:
                text = cell.get_text(strip=True)
                row[col_name] = text if text else None

        if row.get("player"):
            rows.append(row)

    return rows


def scrape_year(driver: uc.Chrome, year: int, use_fallback: bool) -> tuple[list[dict], bool]:
    """Try primary URL first; on failure, switch to fallback for this year AND return
    a flag telling the caller to skip the primary for all subsequent years."""
    if not use_fallback:
        html = fetch_page(driver, PRIMARY_URL.format(year=year))
        if html is not None:
            rows = parse_combine_table(html, year)
            if rows:
                return rows, False
        print("  (primary URL empty — switching to fallback for this and remaining years)")
        use_fallback = True

    html = fetch_page(driver, FALLBACK_URL.format(year=year))
    if html is None:
        return [], use_fallback
    return parse_combine_table(html, year), use_fallback


def height_to_inches(val):
    """Convert '6-2' style height to inches. Leave numeric/missing values alone."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip()
    if "-" in s:
        try:
            feet, inches = s.split("-")
            return int(feet) * 12 + int(inches)
        except ValueError:
            return None
    try:
        return float(s)
    except ValueError:
        return None


def scrape_all_years() -> tuple[pd.DataFrame, list[int]]:
    all_rows = []
    errors = []

    print(f"Scraping combine data from {YEARS.start} to {YEARS.stop - 1}...")
    print("Launching Chrome browser...")
    print("-" * 50)

    driver = create_driver()
    driver.get("https://www.pro-football-reference.com/")
    time.sleep(8)

    use_fallback = False
    try:
        for year in YEARS:
            print(f"Fetching {year}...", end=" ", flush=True)
            try:
                rows, use_fallback = scrape_year(driver, year, use_fallback)
            except Exception as e:
                print(f"ERROR: {e}")
                errors.append(year)
                time.sleep(REQUEST_DELAY_SEC)
                continue

            if not rows:
                print("no rows")
                errors.append(year)
            else:
                all_rows.extend(rows)
                print(f"{len(rows)} players scraped")

            time.sleep(REQUEST_DELAY_SEC)
    finally:
        try:
            driver.quit()
        except OSError:
            pass

    print("-" * 50)

    if not all_rows:
        return pd.DataFrame(), errors

    df = pd.DataFrame(all_rows)

    col_order = ["year", "player", "position", "college"] + COMBINE_METRIC_COLS
    df = df[[c for c in col_order if c in df.columns]]

    df["height"] = df["height"].apply(height_to_inches)
    for col in ["weight", "40_yard", "vertical", "bench_press",
                "broad_jump", "three_cone", "shuttle"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df, errors


def merge_with_drafts(combine_df: pd.DataFrame) -> pd.DataFrame:
    drafts = pd.read_csv(DRAFT_INPUT)

    combine_for_merge = combine_df.drop(columns=["position", "college"], errors="ignore")
    combine_for_merge["_matched"] = 1

    merged = drafts.merge(
        combine_for_merge,
        how="left",
        on=["player", "year"],
    )
    merged["combine_invite"] = merged["_matched"].fillna(0).astype(int)
    merged = merged.drop(columns=["_matched"])
    return merged


def print_summary(combine_df: pd.DataFrame, merged_df: pd.DataFrame, errors: list[int]) -> None:
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)

    print(f"Rows in combine data: {len(combine_df)}")

    total_picks = len(merged_df)
    matched = int(merged_df["combine_invite"].sum())
    match_rate = (matched / total_picks * 100) if total_picks else 0.0
    print(f"Draft picks matched to combine: {matched}/{total_picks} ({match_rate:.1f}%)")

    # Missingness across combine metric columns (only meaningful where we expect values)
    present_cols = [c for c in COMBINE_METRIC_COLS if c in merged_df.columns]
    flagged = []
    for col in present_cols:
        missing_pct = merged_df[col].isna().mean() * 100
        if missing_pct > 20:
            flagged.append((col, missing_pct))

    flagged_frac = len(flagged) / len(present_cols) * 100 if present_cols else 0.0
    print(f"Combine columns with >20% missing: {len(flagged)}/{len(present_cols)} "
          f"({flagged_frac:.1f}%)")
    for col, pct in flagged:
        print(f"  - {col}: {pct:.1f}% missing")

    if errors:
        print(f"Years with scraping errors: {errors}")
    else:
        print("All years scraped successfully.")

    print("\nFirst 3 rows of merged output:")
    print(merged_df.head(3).to_string(index=False))


def main():
    combine_df, errors = scrape_all_years()

    if combine_df.empty:
        print("No combine data scraped. Exiting without writing files.")
        return

    RAW_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    combine_df.to_csv(RAW_OUTPUT, index=False)
    print(f"Saved combine data -> {RAW_OUTPUT}")

    merged = merge_with_drafts(combine_df)
    MERGED_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(MERGED_OUTPUT, index=False)
    print(f"Saved merged data  -> {MERGED_OUTPUT}")

    print_summary(combine_df, merged, errors)


if __name__ == "__main__":
    main()
