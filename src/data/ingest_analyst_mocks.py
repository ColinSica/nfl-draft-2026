"""
Parse the user-provided 2026 Mock Draft Data.xlsx into structured JSON.

The spreadsheet has three sheets:
  Sheet1    — 20 analyst credibility rows + a 32-pick table where each
              column is an analyst's pick per slot.
  Trades    — 54 mock-draft trade scenarios with Times Mocked counts and
              Tier-1 credibility flags.
  Reasoning — per-pick, per-analyst prose explaining the selection.

Outputs: data/features/analyst_consensus_2026.json

Schema:
{
  "meta": {
    "n_analysts": 20,
    "n_tier1": 6,
    "mock_date_range": [...],
    "generated_at": "...",
  },
  "analysts": [{"idx": 1, "name": "Dane Brugler ...", "tier1": true, "date": ...}, ...],
  "per_pick": {
     "1": {
       "team": "LV",
       "picks_all":  {"Mendoza": 20, ...},        // raw counts, all 20 analysts
       "picks_tier1":{"Mendoza": 6, ...},         // counts, top-6 analysts only
       "freq_all":   {"Mendoza": 1.0, ...},       // normalized
       "freq_tier1": {"Mendoza": 1.0, ...},
       "consensus_player": "Mendoza",             // plurality across all 20
       "consensus_tier1":  "Mendoza",             // plurality across top 6
       "trade_noted":      true|false,            // any analyst flagged a trade
     },
     ...
  },
  "reasoning": {
    "1": [{"analyst": "Brugler 7rd", "text": "Raiders desperate..."}, ...],
    ...
  },
  "trades": [
    {"pick":6, "up_team":"DAL","down_team":"CLE","target":"Sonny Styles",
     "times_mocked":6, "tier1_credible":true, "compensation":"...","analysts":"..."},
    ...
  ]
}
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC_XLSX = ROOT / "data" / "2026 Mock Draft Data.xlsx"
OUT_JSON = ROOT / "data" / "features" / "analyst_consensus_2026.json"


# Team name -> 3-letter abbr. Matches on longest suffix first.
TEAM_ABBR = {
    "Cardinals": "ARI", "Falcons": "ATL", "Ravens": "BAL", "Bills": "BUF",
    "Panthers": "CAR", "Bears": "CHI", "Bengals": "CIN", "Browns": "CLE",
    "Cowboys": "DAL", "Broncos": "DEN", "Lions": "DET", "Packers": "GB",
    "Texans": "HOU", "Colts": "IND", "Jaguars": "JAX", "Chiefs": "KC",
    "Chargers": "LAC", "Rams": "LAR", "Raiders": "LV", "Dolphins": "MIA",
    "Vikings": "MIN", "Patriots": "NE", "Saints": "NO", "Giants": "NYG",
    "Jets": "NYJ", "Eagles": "PHI", "Steelers": "PIT", "Seahawks": "SEA",
    "49ers": "SF", "Buccaneers": "TB", "Titans": "TEN",
    "Commanders": "WAS",
}


def team_to_abbr(text: str | float | None) -> str | None:
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return None
    s = str(text)
    # Direct abbr match (for Trades sheet where Pick is like '#6 CLE')
    m = re.search(r"\b([A-Z]{2,3})\b", s)
    if m and m.group(1) in {
        "ARI","ATL","BAL","BUF","CAR","CHI","CIN","CLE","DAL","DEN","DET","GB",
        "HOU","IND","JAX","KC","LAC","LAR","LV","MIA","MIN","NE","NO","NYG",
        "NYJ","PHI","PIT","SEA","SF","TB","TEN","WAS",
    }:
        return m.group(1)
    for nick, abbr in TEAM_ABBR.items():
        if nick in s:
            return abbr
    return None


# Strip trailing "(→ trade)" annotations and any position-in-parens suffix so
# we get the bare player name for grouping.
CLEAN_PLAYER_RX = re.compile(r"\s*\([^)]*\)|\s*→[^)]*")


def clean_player(raw: str) -> str:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return ""
    s = str(raw).strip()
    if s in {"—", "-", "nan", ""}:
        return ""
    # Remove parenthetical annotations (position, notes, trade indicators).
    s = CLEAN_PLAYER_RX.sub("", s).strip()
    return s


def parse_analysts(df: pd.DataFrame) -> list[dict]:
    """Top portion of Sheet1: 20 analyst credibility rows. Stops at the
    first NaN-rank row (the blank separator before the picks table) so we
    don't accidentally treat picks-table rows as extra analysts."""
    out = []
    for _, row in df.iterrows():
        rank = row.get("Credibility Rank")
        if pd.isna(rank):
            break   # blank separator — analyst section ends here
        try:
            rank_i = int(rank)
        except (ValueError, TypeError):
            break
        if rank_i > 20:
            break   # picks table rows have ints 1..32 in col 0
        name = str(row.get("Analyst (Outlet)", "")).strip()
        date = row.get("Mock Date")
        tier1 = str(row.get("In Consensus?", "")).strip().upper() == "YES"
        out.append({
            "idx": rank_i,
            "name": name,
            "date": date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date),
            "tier1": tier1,
        })
    return out


def parse_picks_table(raw: pd.DataFrame, analysts: list[dict]) -> dict:
    """Picks start at the row with header 'Pick #' ... 'CONSENSUS'. Each
    subsequent row is one pick (1-32), columns are analyst selections."""
    # Find the header row (has 'Pick #' in col 0).
    header_idx = None
    for i in range(raw.shape[0]):
        if str(raw.iloc[i, 0]).strip() == "Pick #":
            header_idx = i
            break
    if header_idx is None:
        raise RuntimeError("Could not locate 'Pick #' header row in Sheet1")

    # Analyst columns: rank 1..20 live at col 2..21 (skipping the blank
    # between col 21 and the CONSENSUS column).
    analyst_cols = list(range(2, 2 + len(analysts)))

    per_pick: dict = {}
    for row_idx in range(header_idx + 2, raw.shape[0]):
        pick_val = raw.iloc[row_idx, 0]
        try:
            pick = int(pick_val)
        except (ValueError, TypeError):
            continue
        if pick < 1 or pick > 32:
            continue
        team_abbr = team_to_abbr(raw.iloc[row_idx, 1])
        all_counts: dict[str, int] = {}
        tier1_counts: dict[str, int] = {}
        trade_noted = False
        for col in analyst_cols:
            raw_cell = raw.iloc[row_idx, col]
            player = clean_player(raw_cell)
            if not player:
                continue
            # Detect any trade annotation in the raw cell.
            if isinstance(raw_cell, str) and ("→" in raw_cell or "trade" in raw_cell.lower()):
                trade_noted = True
            all_counts[player] = all_counts.get(player, 0) + 1
            # The analyst at this column: col-2 corresponds to analysts[idx-1]
            a_idx = col - 2
            if a_idx < len(analysts) and analysts[a_idx]["tier1"]:
                tier1_counts[player] = tier1_counts.get(player, 0) + 1

        total_all = sum(all_counts.values()) or 1
        total_tier1 = sum(tier1_counts.values()) or 1

        consensus_all = (max(all_counts.items(), key=lambda kv: kv[1])[0]
                          if all_counts else "")
        consensus_tier1 = (max(tier1_counts.items(), key=lambda kv: kv[1])[0]
                            if tier1_counts else consensus_all)

        per_pick[str(pick)] = {
            "team": team_abbr,
            "picks_all":   all_counts,
            "picks_tier1": tier1_counts,
            "freq_all":    {k: round(v / total_all, 3) for k, v in all_counts.items()},
            "freq_tier1":  {k: round(v / total_tier1, 3) for k, v in tier1_counts.items()},
            "consensus_player": consensus_all,
            "consensus_tier1":  consensus_tier1,
            "trade_noted": trade_noted,
        }
    return per_pick


def parse_reasoning(raw: pd.DataFrame, analysts: list[dict]) -> dict:
    """Reasoning sheet: pick rows, analyst columns, prose in each cell."""
    # Header in row 3 (we already pass header=3). Columns are like
    # '#1 Brugler 7rd', '#2 Brugler 1st', etc.
    analyst_cols = [c for c in raw.columns if str(c).startswith("#")]
    out: dict = {}
    for _, row in raw.iterrows():
        pick_val = row.get("Pick")
        try:
            pick = int(pick_val)
        except (ValueError, TypeError):
            continue
        if pick < 1 or pick > 32:
            continue
        entries = []
        for col in analyst_cols:
            text = row.get(col)
            if pd.isna(text) or not str(text).strip():
                continue
            # Short label from col header: e.g. '#1 Brugler 7rd' -> 'Brugler 7rd'
            short = re.sub(r"^#\d+\s+", "", str(col))
            entries.append({
                "analyst": short,
                "text": str(text).strip(),
            })
        out[str(pick)] = entries
    return out


def parse_trades(raw: pd.DataFrame) -> list[dict]:
    out = []
    for _, row in raw.iterrows():
        if pd.isna(row.get("Pick")):
            continue
        pick_text = str(row.get("Pick", ""))
        # Extract slot number: '#6 CLE' -> 6
        m = re.match(r"#(\d+)", pick_text)
        pick = int(m.group(1)) if m else None
        tier1 = str(row.get("Tier-1 Credible?", "")).strip().upper().startswith("YES")
        times = row.get("Times Mocked") or 0
        try:
            times = int(times)
        except (ValueError, TypeError):
            times = 0
        out.append({
            "pick":              pick,
            "up_team":           team_to_abbr(row.get("Team Trading UP")),
            "down_team":         team_to_abbr(row.get("Team Trading DOWN") or pick_text),
            "target_player":     clean_player(row.get("Target Player")),
            "times_mocked":      times,
            "tier1_credible":    tier1,
            "compensation":      str(row.get("Compensation (typical)") or "").strip(),
            "trade_type":        str(row.get("Trade Type") or "").strip(),
            "analysts":          str(row.get("Analysts Mocking This Trade") or "").strip(),
            "notes":             str(row.get("Notes") or "").strip(),
        })
    return out


def main() -> None:
    if not SRC_XLSX.exists():
        raise SystemExit(f"Missing {SRC_XLSX}")

    # --- Sheet1 --- analyst meta + picks table ---------------------------
    raw_sheet1 = pd.read_excel(SRC_XLSX, sheet_name="Sheet1", header=None)
    analysts_df = pd.read_excel(SRC_XLSX, sheet_name="Sheet1", header=3)
    analysts_df = analysts_df.loc[:, ~analysts_df.columns.str.startswith("Unnamed")]
    analysts = parse_analysts(analysts_df)
    per_pick = parse_picks_table(raw_sheet1, analysts)

    # --- Reasoning sheet ------------------------------------------------
    raw_reason = pd.read_excel(SRC_XLSX, sheet_name="Reasoning", header=3)
    raw_reason = raw_reason.loc[:, ~raw_reason.columns.str.startswith("Unnamed")]
    reasoning = parse_reasoning(raw_reason, analysts)

    # --- Trades sheet ---------------------------------------------------
    raw_trades = pd.read_excel(SRC_XLSX, sheet_name="Trades", header=3)
    raw_trades = raw_trades.loc[:, ~raw_trades.columns.str.startswith("Unnamed")]
    trades = parse_trades(raw_trades)

    dates = [a["date"] for a in analysts if a.get("date")]
    n_tier1 = sum(1 for a in analysts if a["tier1"])

    out = {
        "meta": {
            "n_analysts":      len(analysts),
            "n_tier1":         n_tier1,
            "mock_date_range": [min(dates) if dates else "", max(dates) if dates else ""],
            "generated_at":    datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        "analysts":  analysts,
        "per_pick":  per_pick,
        "reasoning": reasoning,
        "trades":    trades,
    }
    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Saved -> {OUT_JSON}")
    print(f"  {len(analysts)} analysts ({n_tier1} tier-1)")
    print(f"  {len(per_pick)} picks parsed")
    print(f"  {sum(len(v) for v in reasoning.values())} reasoning entries")
    print(f"  {len(trades)} trade scenarios")

    # Summary of consensus picks (for sanity check)
    print("\nConsensus per pick (all 20 / tier-1 only):")
    for pk in range(1, 33):
        info = per_pick.get(str(pk), {})
        if not info:
            continue
        all_top = info.get("consensus_player", "?")
        all_n   = info.get("picks_all", {}).get(all_top, 0)
        t1_top  = info.get("consensus_tier1", "?")
        t1_n    = info.get("picks_tier1", {}).get(t1_top, 0)
        print(f"  P{pk:>2}  {info.get('team','?'):<4}  "
              f"all=[{all_top} {all_n}/{len(analysts)}]  "
              f"tier1=[{t1_top} {t1_n}/{n_tier1}]")


if __name__ == "__main__":
    main()
