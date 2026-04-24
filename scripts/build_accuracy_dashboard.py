"""Parse data/Updated 2026 Real Progress.xlsx -> data/processed/accuracy_2026.json

The accuracy JSON drives a Dashboard page on the website that compares
Colin's mock against ~30 other analysts as real picks come in.

Output schema:
{
  "generated_at":  ISO,
  "picks_scored":  int,
  "r1_picks_drafted": int,
  "total_r1_picks": 32,
  "analysts": [
    {
      "name": "Colin",
      "exact": int,
      "in_r1": int,
      "team_match": int,
      "exact_pct": float,
      "rank": int,    // 1 = best by exact hits
    },
    ...
  ],
  "picks": [
    {
      "pick": 1,
      "actual_team": "Raiders",
      "actual_player": "Fernando Mendoza",
      "colin_pick": "Fernando Mendoza",
      "colin_hit": bool,
    },
    ...
  ]
}
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
XLSX = ROOT / "data/Updated 2026 Real Progress.xlsx"
OUT = ROOT / "data/processed/accuracy_2026.json"

# Analyst label -> (exact_col, in_r1_col, team_match_col)
ANALYST_COLUMNS: list[tuple[str, str, str, str]] = [
    # (display_name, exact_col, in_r1_col, team_match_col)
    ("Colin",             "Colin Exact",       "Colin in R1",       "Colin Team Match"),
    ("Colin w/Trade",     "ColinTrade Exact",  "ColinTrade in R1",  "ColinTrade Team Match"),
    ("Mel Kiper Jr.",     "Kiper Exact",       "Kiper in R1",       "Kiper Team Match"),
    ("Daniel Jeremiah",   "Jeremiah Exact",    "Jeremiah in R1",    "Jeremiah Team Match"),
    ("Todd McShay",       "Todd Exact",        "Todd in R1",        "Todd Team Match"),
    ("Jordan Reid",       "Reid Exact",        "Reid in R1",        "Reid Team Match"),
    ("Field Yates",       "Yates Exact",       "Yates in R1",       "Yates Team Match"),
    ("Peter Schrager",    "Schrager Exact",    "Schrager in R1",    "Schrager Team Match"),
    ("Matt Miller",       "Miller Exact",      "Miller in R1",      "Miller Team Match"),
    ("Lance Zierlein",    "Lance Exact",       "Lance in R1",       "Lance Team Match"),
    ("Bucky Brooks",      "Bucky Exact",       "Bucky in R1",       "Bucky Team Match"),
    ("Eric Edholm",       "Eric Exact",        "Eric in R1",        "Eric Team Match"),
    ("Ryan Wilson",       "Wilson Exact",      "Wilson in R1",      "Wilson Team Match"),
    ("Brendan Donahue",   "Donahue Exact",     "Donahue in R1",     "Donahue Team Match"),
    ("Dan Parr",          "Dan Exact",         "Dan in R1",         "Dan Team Match"),
    ("Yahoo (Tice/McDonald)", "Yahoo Exact",   "Yahoo in R1",       "Yahoo Team Match"),
    ("Rob Rang",          "Rob Exact",         "Rob in R1",         "Rob Team Match"),
    ("Pete Prisco",       "Pete Exact",        "Pete in R1",        "Pete Team Match"),
    ("Josh Edwards",      "Edwards Exact",     "Edwards in R1",     "Edwards Team Match"),
    ("Pauline",           "Pauline Exact",     "Pauline in R1",     "Pauline Team Match"),
    ("Charles Davis",     "Davis Exact",       "Davis in R1",       "Davis Team Match"),
    ("Ryan McCrystal",    "McCrystal Exact",   "McCrystal in R1",   "McCrystal Team Match"),
    ("Luke Easterling",   "Easter Exact",      "Easter in R1",      "Easter Team Match"),
    ("Vinnie Iyer",       "Iyer Exact",        "Iyer in R1",        "Iyer Team Match"),
    ("Walt Cherepinsky",  "Walt Exact",        "Walt in R1",        "Walt Team Match"),
    ("Charlie Campbell",  "Charlie Exact",     "Charlie in R1",     "Charlie Team Match"),
    ("Chad Reuter",       "Chad Exact",        "Chad in R1",        "Chad Team Match"),
    ("Jason Boris",       "Jason Exact",       "Jason in R1",       "Jason Team Match"),
    ("NFL Nation (ESPN)", "NFLNation Exact",   "NFLNation in R1",   "NFLNation Team Match"),
    ("Rob Paul (SBR)",    "RobPaul Exact",     "RobPaul in R1",     "RobPaul Team Match"),
    ("PFF ADP",           "PFF Exact",         "PFF in R1",         "PFF Team Match"),
    ("Brent Sobleski (B/R)","Brent Exact",     "Brent in R1",       "Brent Team Match"),
    ("Lou Pickney (DKDB)","Lou Exact",         "Lou in R1",         "Lou Team Match"),
    ("Brendan Donahue",   "Donahue Exact",     "Donahue in R1",     "Donahue Team Match"),
]


def _sum(col: pd.Series) -> int:
    return int(pd.to_numeric(col, errors="coerce").fillna(0).sum())


def main() -> None:
    import warnings
    warnings.filterwarnings("ignore")
    df = pd.read_excel(XLSX, sheet_name="Accuracy Analysis", header=0)
    # Keep only R1 (picks 1-32) for apples-to-apples comparison; most analyst
    # mocks stop at 32.
    df["Pick #"] = pd.to_numeric(df["Pick #"], errors="coerce")
    r1 = df[df["Pick #"].between(1, 32, inclusive="both")].copy()
    drafted_r1 = r1[r1["Actual Player"].notna()]
    n_drafted = int(len(drafted_r1))

    analysts: list[dict] = []
    seen: set[str] = set()
    for name, ex_col, r1_col, tm_col in ANALYST_COLUMNS:
        if name in seen:
            continue
        if ex_col not in r1.columns:
            continue
        seen.add(name)
        exact = _sum(drafted_r1[ex_col]) if ex_col in drafted_r1.columns else 0
        in_r1 = _sum(drafted_r1[r1_col]) if r1_col in drafted_r1.columns else 0
        team_match = _sum(drafted_r1[tm_col]) if tm_col in drafted_r1.columns else 0
        total = max(1, n_drafted)
        analysts.append({
            "name":       name,
            "exact":      exact,
            "in_r1":      in_r1,
            "team_match": team_match,
            "exact_pct":  round(exact / total * 100, 1),
            "in_r1_pct":  round(in_r1 / total * 100, 1),
            "team_pct":   round(team_match / total * 100, 1),
        })

    # Rank by exact hits, break ties by in_r1
    analysts.sort(key=lambda a: (-a["exact"], -a["in_r1"], -a["team_match"], a["name"]))
    for i, a in enumerate(analysts, start=1):
        a["rank"] = i

    # Per-pick detail rows (R1 only)
    picks: list[dict] = []
    for _, row in r1.iterrows():
        pick_num = int(row["Pick #"]) if pd.notna(row["Pick #"]) else None
        if pick_num is None:
            continue
        picks.append({
            "pick":           pick_num,
            "actual_team":    row.get("Actual Team") if pd.notna(row.get("Actual Team")) else None,
            "actual_player":  row.get("Actual Player") if pd.notna(row.get("Actual Player")) else None,
            "colin":          row.get("Colin's Mock") if pd.notna(row.get("Colin's Mock")) else None,
            "colin_trade":    row.get("Colin w/Trade") if pd.notna(row.get("Colin w/Trade")) else None,
            "colin_hit":      bool(row.get("Colin Exact")) if pd.notna(row.get("Colin Exact")) else None,
            "trade_hit":      bool(row.get("ColinTrade Exact")) if pd.notna(row.get("ColinTrade Exact")) else None,
        })

    colin_entry = next((a for a in analysts if a["name"] == "Colin"), None)
    colin_trade_entry = next((a for a in analysts if a["name"] == "Colin w/Trade"), None)

    out = {
        "generated_at":      datetime.now(timezone.utc).astimezone().isoformat(),
        "total_r1_picks":    32,
        "r1_picks_drafted":  n_drafted,
        "colin_rank":        colin_entry["rank"] if colin_entry else None,
        "colin_rank_trade":  colin_trade_entry["rank"] if colin_trade_entry else None,
        "total_analysts":    len(analysts),
        "analysts":          analysts,
        "picks":             picks,
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[accuracy] wrote {OUT.name}")
    print(f"  R1 picks drafted: {n_drafted}/32")
    print(f"  Colin rank: #{out['colin_rank']} / {out['total_analysts']}  "
          f"(exact {colin_entry['exact']}, in-R1 {colin_entry['in_r1']})"
          if colin_entry else "  Colin: —")
    # Top 5 leaderboard
    print("  Top 5 by exact:")
    for a in analysts[:5]:
        print(f"    #{a['rank']}  {a['name']:<22} exact={a['exact']}  in-R1={a['in_r1']}")


if __name__ == "__main__":
    main()
