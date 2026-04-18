"""
Parse the PFF top-prospects Excel dump and populate these columns in
data/processed/prospects_2026_enriched.csv:

  pff_rank             (from block header)
  pff_grade_3yr        (mean of 2023/2024/2025 season grades present)
  pff_waa              (2025 season PFF WAA, when populated)
  pff_minus_consensus  pff_rank - consensus rank (big-board)

Layout (observed): 24-row blocks, first row "PFF Rank" label. See repo notes.
"""

import re
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

ROOT = Path(__file__).resolve().parents[2]
XL_PATH = Path("C:/Users/colin/Downloads/Untitled spreadsheet.xlsx")
PROS_CSV = ROOT / "data" / "processed" / "prospects_2026_enriched.csv"

FUZZ_THRESHOLD = 85


def parse_excel(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="Sheet1", header=None)
    print(f"Loaded raw Excel: {df.shape}")

    # Every block begins with "PFF Rank" in column 0
    block_starts = df.index[df[0] == "PFF Rank"].tolist()
    print(f"Found {len(block_starts)} PFF block starts")

    rows = []
    for start in block_starts:
        try:
            rank = int(df.iloc[start + 1, 0])
        except (ValueError, TypeError):
            continue

        try:
            name = str(df.iloc[start + 2, 0]).strip()
        except IndexError:
            continue
        if not name or name == "nan":
            continue

        grades: list[float] = []
        waa_2025 = None
        for season_offset in (21, 22, 23):
            r = start + season_offset
            if r >= len(df):
                break
            year_cell = df.iloc[r, 0]
            grade_cell = df.iloc[r, 2]
            waa_cell = df.iloc[r, 3] if df.shape[1] > 3 else None

            if pd.notna(grade_cell):
                m = re.match(r"\s*([0-9]+(?:\.[0-9]+)?)", str(grade_cell))
                if m:
                    try:
                        grades.append(float(m.group(1)))
                    except ValueError:
                        pass
            if pd.notna(year_cell) and str(year_cell).strip() == "2025" and pd.notna(waa_cell):
                try:
                    waa_2025 = float(waa_cell)
                except (ValueError, TypeError):
                    pass

        rows.append({
            "pff_rank": rank,
            "pff_name": name,
            "pff_grade_3yr": (sum(grades) / len(grades)) if grades else None,
            "pff_waa": waa_2025,
            "_seasons_with_grades": len(grades),
        })

    return pd.DataFrame(rows)


def main():
    if not XL_PATH.exists():
        raise SystemExit(f"Excel file not found: {XL_PATH}")
    pff = parse_excel(XL_PATH)
    print(f"\nParsed {len(pff)} PFF prospects")
    print("Sample:")
    print(pff.head(10).to_string(index=False))

    pros = pd.read_csv(PROS_CSV)
    # Fuzzy match PFF name → prospect name with greedy one-to-one resolution.
    # Without this, a PFF entry like "Sonny Styles" can match both the real
    # Sonny Styles AND "Lorenzo Styles Jr." etc.
    pff_names = pff["pff_name"].tolist()
    candidates: list[tuple[float, int, str]] = []
    for idx, name in enumerate(pros["player"].astype(str)):
        best = process.extractOne(name, pff_names, scorer=fuzz.WRatio)
        if best and best[1] >= FUZZ_THRESHOLD:
            candidates.append((best[1], idx, best[0]))
    candidates.sort(key=lambda t: -t[0])
    assigned: dict[int, str] = {}
    used: set[str] = set()
    for score, idx, mname in candidates:
        if idx in assigned or mname in used:
            continue
        assigned[idx] = mname
        used.add(mname)
    matched = [assigned.get(i) for i in range(len(pros))]

    pff_map = pff.set_index("pff_name")
    pros["_pff_match"] = matched
    for col in ("pff_rank", "pff_grade_3yr", "pff_waa"):
        pros[col] = pros["_pff_match"].map(pff_map[col])

    if "rank" in pros.columns:
        pros["pff_minus_consensus"] = pros["pff_rank"] - pros["rank"]
    else:
        pros["pff_minus_consensus"] = None

    pros = pros.drop(columns=["_pff_match"])
    pros.to_csv(PROS_CSV, index=False)

    matched_n = int(pros["pff_rank"].notna().sum())
    print(f"\nMatch rate: {matched_n}/{len(pros)} ({matched_n / len(pros) * 100:.1f}%)")

    # Show examples of the matched population
    matched_df = pros[pros["pff_rank"].notna()].sort_values("pff_rank")
    cols = [c for c in ("pff_rank", "rank", "player", "position", "college",
                        "pff_grade_3yr", "pff_waa", "pff_minus_consensus")
            if c in matched_df.columns]
    print("\nMatched sample (top 10 by PFF rank):")
    print(matched_df[cols].head(10).to_string(index=False))

    print(f"\nColumns now in {PROS_CSV.name}: {pros.shape[1]}")


if __name__ == "__main__":
    main()
