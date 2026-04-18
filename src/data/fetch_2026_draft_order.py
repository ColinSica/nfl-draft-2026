"""
Fetch the 2026 NFL draft order (all 7 rounds) from NFL.com and save
one row per pick to data/processed/team_context_2026.csv.

Schema: pick_number, round, team
"""

import re
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_CSV = ROOT / "data" / "processed" / "team_context_2026.csv"

URL = "https://www.nfl.com/news/2026-nfl-draft-order-for-all-seven-rounds"

TEAM_ABBR = {
    "Arizona Cardinals": "ARI",
    "Atlanta Falcons": "ATL",
    "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR",
    "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN",
    "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN",
    "Detroit Lions": "DET",
    "Green Bay Packers": "GB",
    "Houston Texans": "HOU",
    "Indianapolis Colts": "IND",
    "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC",
    "Las Vegas Raiders": "LV",
    "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LAR",
    "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN",
    "New England Patriots": "NE",
    "New Orleans Saints": "NO",
    "New York Giants": "NYG",
    "New York Jets": "NYJ",
    "Philadelphia Eagles": "PHI",
    "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA",
    "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN",
    "Washington Commanders": "WAS",
}

PICK_RE = re.compile(r"^\s*(\d+)\.\s+(.+?)\s*$")
ROUND_RE = re.compile(r"^\s*Round\s+(\d+)\s*:?\s*$", re.IGNORECASE)


def strip_annotations(team_text: str) -> str:
    """Drop '(via Foo)' and '(Compensatory Selection)' suffixes."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", team_text).strip()


def parse(html: str) -> pd.DataFrame:
    soup = BeautifulSoup(html, "lxml")
    article = soup.find("article") or soup.find("main") or soup
    text = article.get_text("\n")

    rows = []
    current_round = None
    unknown_teams: set[str] = set()
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        m_round = ROUND_RE.match(line)
        if m_round:
            current_round = int(m_round.group(1))
            continue
        m_pick = PICK_RE.match(line)
        if not m_pick:
            continue
        pick_num = int(m_pick.group(1))
        if not (1 <= pick_num <= 260):
            continue
        if current_round is None:
            continue
        team_full = strip_annotations(m_pick.group(2))
        abbr = TEAM_ABBR.get(team_full)
        if abbr is None:
            unknown_teams.add(team_full)
            continue
        rows.append({"pick_number": pick_num, "round": current_round, "team": abbr})

    if unknown_teams:
        print(f"WARNING: {len(unknown_teams)} unmapped team strings: {unknown_teams}")

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["pick_number"], keep="first")
    df = df.sort_values("pick_number").reset_index(drop=True)
    return df


def main():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/122.0 Safari/537.36"}
    r = requests.get(URL, headers=headers, timeout=30)
    r.raise_for_status()

    df = parse(r.text)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved {len(df)} picks -> {OUTPUT_CSV}")

    print("\nPicks per round:")
    for rnd, n in df.groupby("round").size().items():
        print(f"  Round {rnd}: {n}")

    print(f"\nUnique teams: {df['team'].nunique()}")
    print("\nFirst 5 picks:")
    print(df.head().to_string(index=False))


if __name__ == "__main__":
    main()
