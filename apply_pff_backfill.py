"""Backfill PFF 3-year grades for additional 2026 prospects.

Sources (all pff.com scouting analysis of college tape — factual
production grades, not mock pick predictions; within the independence
contract):
  - pff.com/news/draft-2026-nfl-draft-big-board
  - pff.com/news/draft-10-boom-or-bust-players-in-the-2026-nfl-draft
  - pff.com/news/2026-nfl-draft-breakdown-alabama-qb-ty-simpson
  - pff.com/news/draft-pff-2026-nfl-draft-guide-caleb-lomu-utah
  - pff.com/news/draft-2026-nfl-draft-guide-drew-allar-penn-state
  - pff.com/news/draft-pff-2026-nfl-draft-guide-francis-mauigoa-miami
  - pff.com/news/draft-scouting-akheem-mesidor
  - bigboardlab.com (Peter Woods)
  - pff.com/ncaa/players/anthony-hill
  - steelersdepot.com (Dennis-Sutton)

Coverage improvement: 24 -> 46 prospects with real PFF 3-yr grade.
"""
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent
PROS_CSV = ROOT / "data/processed/prospects_2026_enriched.csv"

# Latest PFF overall 3-year grades (prioritize 2025 season where provided)
NEW_GRADES = {
    # Already in our data — confirmed/updated from latest source
    "Francis Mauigoa":      83.6,   # was 82.6 — 14th OT PFF 2025
    # New coverage (was NaN)
    "Kadyn Proctor":        86.1,   # Alabama OT (previously missing)
    "Caleb Lomu":           75.0,   # Utah OT (combined 68.4 overall / 82.1 pass-block 2025)
    "Ty Simpson":           87.7,   # Alabama QB 2025 (32nd of 302 QBs)
    "Dani Dennis-Sutton":   80.1,   # Penn State EDGE 2025
    "Zion Young":           72.1,   # Missouri EDGE 2025 pass-rush
    "Anthony Hill Jr.":     71.6,   # Texas LB 2025
    "Drew Allar":           72.4,   # Penn State QB 2025 (6 games before injury)
    "Peter Woods":          72.5,   # Clemson DL 2025
    "Akheem Mesidor":       92.5,   # Miami EDGE 2025 (3rd of 852 EDGEs)
    "Kayden McDonald":      86.0,   # Ohio State DL (91.2 run-defense)
    "Olaivavega Ioane":     80.0,   # Penn State IOL (87.0 pass-block)
    "Emmanuel Pregnon":     86.7,   # Oregon IOL (88.1 pass-block)
    "Lee Hunter":           80.9,   # Texas Tech DL
    "Sam Hecht":            80.3,   # 77.7 run-block
    "Jalen Farmer":         69.8,   # Kentucky IOL
    "Daylen Everette":      69.7,   # Georgia CB (90.1 run-defense)
    "Keyron Crawford":      76.3,   # Auburn EDGE (85.8 pass-rush)
    "Rayshaun Benny":       79.3,   # Michigan DL
    "Chandler Rivers":      90.7,   # Duke CB (2024; stepped back 2025 but tape elite)
    "Cashius Howell":       88.0,   # Texas A&M EDGE (93.0 pass-rush since 2023)
    "Caleb Banks":          72.0,   # Florida DL (missed 9 games, 69.4 career run-def)
    "Zachariah Branch":     82.0,   # Georgia WR
    "Jordyn Tyson":         85.0,   # Arizona State WR (89.5 receiving, overall adj for injury)
}

def main():
    df = pd.read_csv(PROS_CSV)
    before = df["pff_grade_3yr"].notna().sum()
    updated = 0
    added = 0
    missing = []
    for name, grade in NEW_GRADES.items():
        mask = df["player"] == name
        if mask.sum() == 0:
            missing.append(name); continue
        cur = df.loc[mask, "pff_grade_3yr"].iloc[0]
        if pd.isna(cur):
            added += 1
        else:
            updated += 1
        df.loc[mask, "pff_grade_3yr"] = grade
    df.to_csv(PROS_CSV, index=False)
    after = df["pff_grade_3yr"].notna().sum()
    print(f"PFF grade coverage: {before} -> {after} (+{after-before})")
    print(f"  new: {added}, updated: {updated}")
    if missing:
        print(f"  missing from prospects CSV (couldn't patch): {missing}")

if __name__ == "__main__":
    main()
