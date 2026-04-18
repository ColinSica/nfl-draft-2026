"""
Fetch 2026 NFL Combine results from CBS Sports, merge into prospects_2026.csv.

CBS renders combine data as 22 HTML tables, one pair per position group:
  - measurements (Player, School, Height, Weight, Hand, Arm, Wingspan)
  - performance   (Player, 40, 10, Vert, Broad, 3-cone, Shuttle, Bench)

We pair tables by document order, join on player name, fuzzy-match to the
consensus big board, and add combine columns.

Outputs
-------
  data/raw/_combine_2026_raw.html       (cached HTML source)
  data/raw/combine_2026.csv             (parsed combine table)
  data/processed/prospects_2026.csv     (updated in place)
"""

import re
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz, process

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

CBS_URL = ("https://www.cbssports.com/nfl/draft/news/"
           "2026-nfl-combine-results-full-list-measurements-40-times/")
RAW_HTML = RAW_DIR / "_combine_2026_raw.html"
COMBINE_CSV = RAW_DIR / "combine_2026.csv"
PROSPECTS_CSV = PROCESSED_DIR / "prospects_2026.csv"

FUZZ_THRESHOLD = 85

FRAC_MAP = {"⅛": 0.125, "¼": 0.25, "⅜": 0.375, "½": 0.5,
            "⅝": 0.625, "¾": 0.75, "⅞": 0.875}

COMBINE_COLS = ["height", "weight", "40_yard", "vertical",
                "bench_press", "broad_jump", "three_cone", "shuttle"]


def to_inches_ft_in(s: Optional[str]) -> Optional[float]:
    """'6-4', '6-4⅜', '9-7' (broad jump) -> inches. None if unparseable."""
    if s is None or not str(s).strip():
        return None
    s = str(s).strip()
    frac = 0.0
    for ch, val in FRAC_MAP.items():
        if ch in s:
            frac += val
            s = s.replace(ch, "")
    m = re.match(r"(\d+)-(\d+(?:\.\d+)?)$", s)
    if m:
        return int(m.group(1)) * 12 + float(m.group(2)) + frac
    try:
        return float(s) + frac
    except ValueError:
        return None


def to_float(s: Optional[str]) -> Optional[float]:
    if s is None or not str(s).strip():
        return None
    try:
        return float(str(s).strip())
    except ValueError:
        return None


def position_code(heading: str) -> str:
    t = heading.upper()
    if "TACKLE" in t and "DEFENSIVE" not in t:
        return "OT"
    if "INTERIOR" in t or "GUARD" in t or "CENTER" in t:
        return "IOL"
    if "WIDE RECEIVER" in t or "RECEIVER" in t:
        return "WR"
    if "RUNNING BACK" in t:
        return "RB"
    if "QUARTERBACK" in t:
        return "QB"
    if "TIGHT END" in t:
        return "TE"
    if "EDGE" in t:
        return "EDGE"
    if "DEFENSIVE" in t:
        return "DL"
    if "LINEBACKER" in t:
        return "LB"
    if "CORNERBACK" in t:
        return "CB"
    if "SAFETY" in t or "DEFENSIVE BACK" in t:
        return "S"
    return ""


def fetch_html() -> str:
    if RAW_HTML.exists():
        html = RAW_HTML.read_text(encoding="utf-8", errors="ignore")
        print(f"Loaded cached HTML ({len(html):,} bytes)")
        return html
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/122.0 Safari/537.36"}
    r = requests.get(CBS_URL, headers=headers, timeout=30)
    r.raise_for_status()
    RAW_HTML.write_bytes(r.content)
    print(f"Fetched CBS combine page ({len(r.text):,} bytes)")
    return r.text


def parse_combine(html: str) -> pd.DataFrame:
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    print(f"Tables found: {len(tables)}")
    if len(tables) % 2 != 0:
        print(f"  WARNING: odd table count; last one will be ignored")

    rows = []
    for i in range(0, len(tables) - 1, 2):
        mtable, ptable = tables[i], tables[i + 1]

        heading_el = mtable.find_previous(["h2", "h3", "h4"])
        heading = heading_el.get_text(strip=True) if heading_el else ""
        pos = position_code(heading)

        meas = {}
        tbody = mtable.find("tbody") or mtable
        for tr in tbody.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if len(cells) < 4 or cells[0].lower() == "player":
                continue
            meas[cells[0]] = {
                "player": cells[0],
                "combine_school": cells[1],
                "combine_position": pos,
                "height": to_inches_ft_in(cells[2]),
                "weight": to_float(cells[3]),
            }

        perf = {}
        tbody = ptable.find("tbody") or ptable
        for tr in tbody.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if not cells or cells[0].lower() == "player":
                continue
            cells = cells + [""] * (8 - len(cells))
            perf[cells[0]] = {
                "40_yard": to_float(cells[1]),
                "vertical": to_float(cells[3]),
                "broad_jump": to_inches_ft_in(cells[4]),
                "three_cone": to_float(cells[5]),
                "shuttle": to_float(cells[6]),
                "bench_press": to_float(cells[7]),
            }

        for name, m in meas.items():
            row = dict(m)
            row.update(perf.get(name, {}))
            rows.append(row)

    df = pd.DataFrame(rows)
    # Dedupe in case a name appears across more than one position section
    df = df.drop_duplicates(subset=["player"], keep="first").reset_index(drop=True)
    return df


def merge_into_prospects(prospects: pd.DataFrame, combine: pd.DataFrame) -> pd.DataFrame:
    prospects = prospects.copy()
    # If a previous run already added combine cols, drop them before re-merging
    for c in COMBINE_COLS + ["combine_invite"]:
        if c in prospects.columns:
            prospects = prospects.drop(columns=[c])

    combine_names = combine["player"].tolist()

    # Score every prospect's best combine candidate, then greedy-assign
    # each combine entry to the highest-scoring prospect. This prevents
    # two different prospects from both claiming the same combine row
    # (e.g. "Lance St. Louis" stealing "Kyle Louis"'s record).
    candidates = []
    for idx, name in enumerate(prospects["player"]):
        best = process.extractOne(name, combine_names, scorer=fuzz.WRatio)
        if best is None:
            continue
        mname, score, _ = best
        if score >= FUZZ_THRESHOLD:
            candidates.append((score, idx, mname))

    candidates.sort(key=lambda t: -t[0])
    assigned: dict[int, str] = {}
    used: set[str] = set()
    for score, idx, mname in candidates:
        if mname in used or idx in assigned:
            continue
        assigned[idx] = mname
        used.add(mname)

    prospects["_combine_match"] = [assigned.get(i) for i in range(len(prospects))]
    prospects["combine_invite"] = prospects["_combine_match"].notna().astype(int)

    slim = combine[["player"] + COMBINE_COLS].rename(columns={"player": "_combine_match"})
    merged = prospects.merge(slim, how="left", on="_combine_match")
    return merged.drop(columns=["_combine_match"])


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    html = fetch_html()
    combine = parse_combine(html)
    combine.to_csv(COMBINE_CSV, index=False)
    print(f"Parsed {len(combine)} combine entries -> {COMBINE_CSV}")

    prospects = pd.read_csv(PROSPECTS_CSV)
    merged = merge_into_prospects(prospects, combine)
    merged.to_csv(PROSPECTS_CSV, index=False)
    print(f"Saved -> {PROSPECTS_CSV} ({merged.shape[1]} cols)")

    matched = int(merged["combine_invite"].sum())
    total = len(merged)
    print(f"\n2026 prospects matched to combine: {matched}/{total} "
          f"({matched / total * 100:.1f}%)")
    print("\n% missing among all prospects (combine cols):")
    for c in COMBINE_COLS:
        pct = merged[c].isna().mean() * 100
        print(f"  {pct:5.1f}%  {c}")


if __name__ == "__main__":
    main()
