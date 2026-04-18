"""
Enhance team_context_2026_enriched.csv with:
  - wins / losses / ties / win_pct (from nflverse 2025 regular-season games)
  - bpa_weight / need_weight (derived from win_pct)
  - qb_urgency (from OverTheCap QB contracts)

Simplifications vs. the user's spec:
  - The user asked for positional_urgency across every position using FA-tracker
    data. We don't have FA-tracker data (step 23 from the pipeline was a stub).
    We populate qb_urgency explicitly from OverTheCap; for other positions the
    scoring function derives urgency on-the-fly from need_rank.
  - need_created_by_departure isn't available — no column is written for it.
"""

import io
import re
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
TEAM_CTX = ROOT / "data" / "processed" / "team_context_2026_enriched.csv"
GAMES_URL = "https://github.com/nflverse/nfldata/raw/master/data/games.csv"
OTC_QB_URL = "https://overthecap.com/position/quarterback"

NICKNAME_TO_ABBR = {
    "49ers": "SF", "Bears": "CHI", "Bengals": "CIN", "Bills": "BUF",
    "Broncos": "DEN", "Browns": "CLE", "Buccaneers": "TB", "Cardinals": "ARI",
    "Chargers": "LAC", "Chiefs": "KC", "Colts": "IND", "Commanders": "WAS",
    "Cowboys": "DAL", "Dolphins": "MIA", "Eagles": "PHI", "Falcons": "ATL",
    "Giants": "NYG", "Jaguars": "JAX", "Jets": "NYJ", "Lions": "DET",
    "Packers": "GB", "Panthers": "CAR", "Patriots": "NE", "Raiders": "LV",
    "Rams": "LAR", "Ravens": "BAL", "Saints": "NO", "Seahawks": "SEA",
    "Steelers": "PIT", "Texans": "HOU", "Titans": "TEN", "Vikings": "MIN",
}

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")


def fetch_2025_records() -> pd.DataFrame:
    r = requests.get(GAMES_URL, timeout=60)
    r.raise_for_status()
    games = pd.read_csv(io.BytesIO(r.content))
    g = games[(games["season"] == 2025) & (games["game_type"] == "REG")].copy()
    g = g.dropna(subset=["home_score", "away_score"])
    print(f"Found {len(g)} 2025 regular-season games with scores")

    wins: dict[str, int] = {}
    losses: dict[str, int] = {}
    ties: dict[str, int] = {}
    for _, row in g.iterrows():
        ht, at = row["home_team"], row["away_team"]
        hs, as_ = row["home_score"], row["away_score"]
        if hs > as_:
            wins[ht] = wins.get(ht, 0) + 1
            losses[at] = losses.get(at, 0) + 1
        elif as_ > hs:
            wins[at] = wins.get(at, 0) + 1
            losses[ht] = losses.get(ht, 0) + 1
        else:
            ties[ht] = ties.get(ht, 0) + 1
            ties[at] = ties.get(at, 0) + 1

    teams = set(wins) | set(losses) | set(ties)
    rows = []
    for t in sorted(teams):
        w, l, tt = wins.get(t, 0), losses.get(t, 0), ties.get(t, 0)
        gp = w + l + tt
        wp = (w + 0.5 * tt) / gp if gp else 0.0
        rows.append({"team": t, "wins": w, "losses": l, "ties": tt, "win_pct": wp})
    return pd.DataFrame(rows)


def fetch_otc_qbs() -> pd.DataFrame:
    r = requests.get(OTC_QB_URL, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    table = soup.find("table")
    if table is None:
        raise RuntimeError("No table on OverTheCap QB page")

    tbody = table.find("tbody")
    rows = []
    for tr in tbody.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) < 8:
            continue
        player, team_nick, age, total, apy, tg, fg, fa = cells[:8]
        apy_num = int(re.sub(r"[^0-9]", "", apy) or 0)
        try:
            age_num = int(re.sub(r"[^0-9]", "", age))
        except ValueError:
            age_num = 0
        m = re.match(r"(\d{4})", fa)
        if m:
            fa_year = int(m.group(1))
            years_remaining = max(0, fa_year - 2025)
        else:
            years_remaining = 1
        abbr = NICKNAME_TO_ABBR.get(team_nick, team_nick[:3].upper())
        rows.append({
            "team": abbr, "qb_name": player, "qb_age": age_num,
            "qb_apy": apy_num, "qb_years_remaining": years_remaining,
        })
    df = pd.DataFrame(rows)
    # Keep one row per team (highest APY = the starter)
    df = df.sort_values("qb_apy", ascending=False).drop_duplicates("team").reset_index(drop=True)
    return df


def qb_urgency(qb_row) -> float:
    if qb_row is None:
        return 1.0
    yr = qb_row.get("qb_years_remaining", 0)
    apy = qb_row.get("qb_apy", 0)
    age = qb_row.get("qb_age", 0)
    if yr >= 2 and apy > 35_000_000:
        return 0.0
    if yr == 1 and age > 32:
        return 0.5
    if yr == 1 and age <= 32:
        return 0.3
    return 1.0


def bpa_weights(win_pct: float) -> tuple[float, float]:
    if win_pct < 0.375:
        return (0.7, 0.3)
    if win_pct < 0.562:
        return (0.5, 0.5)
    return (0.3, 0.7)


def main():
    records = fetch_2025_records()
    print(f"Records computed for {len(records)} teams")
    qbs = fetch_otc_qbs()
    print(f"OverTheCap QB rows parsed: {len(qbs)} teams with a franchise QB entry")

    team = pd.read_csv(TEAM_CTX)
    # Drop any prior enrichment to keep the merge clean
    for c in ("wins", "losses", "ties", "win_pct", "bpa_weight",
              "need_weight", "qb_urgency", "qb_name", "qb_years_remaining"):
        if c in team.columns:
            team = team.drop(columns=[c])

    team = team.merge(records, how="left", on="team")

    w = team["win_pct"].fillna(0.5).apply(bpa_weights)
    team["bpa_weight"] = w.apply(lambda t: t[0])
    team["need_weight"] = w.apply(lambda t: t[1])

    qb_map = qbs.set_index("team").to_dict("index")
    team["qb_name"] = team["team"].map(lambda t: (qb_map.get(t) or {}).get("qb_name", ""))
    team["qb_years_remaining"] = team["team"].map(
        lambda t: (qb_map.get(t) or {}).get("qb_years_remaining"))
    team["qb_urgency"] = team["team"].apply(lambda t: qb_urgency(qb_map.get(t)))

    team.to_csv(TEAM_CTX, index=False)
    print(f"\nSaved team_context_2026_enriched.csv ({team.shape[1]} cols)")

    uniq = team[["team", "wins", "losses", "win_pct",
                 "bpa_weight", "need_weight", "qb_name", "qb_urgency"]].drop_duplicates("team")
    print("\nSample (top 6 by win_pct):")
    print(uniq.sort_values("win_pct", ascending=False).head(6).to_string(index=False))
    print("\nSample (bottom 6 by win_pct):")
    print(uniq.sort_values("win_pct").head(6).to_string(index=False))


if __name__ == "__main__":
    main()
