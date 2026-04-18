"""
Scrape first-round pick origins from Wikipedia for 2021-2025 drafts.

Wikipedia's draft tables include a Notes column that flags traded picks with
"from <OriginalTeam>" text. By parsing this we recover each pick's original
owner and, by comparing to the team that actually made the selection, we can
determine:
  - direction: trade-up (original owned a later pick), trade-down (original
    owned an earlier pick), no trade (original == final).
  - per-pick trade frequency (did this slot get traded that year?).
  - per-team trade-up / trade-down counts.

Output: data/raw/r1_trades_2021_2025.json
Schema:
{
  "years": [2021, 2022, 2023, 2024, 2025],
  "trades": [
    {"year": 2025, "pick": 2, "final_team": "JAX", "original_team": "CLE",
     "player": "Travis Hunter", "position": "CB/WR",
     "direction": "up|down|none"},
    ...
  ],
  "r1_pick_counts": {"2021": 32, ...}
}
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
OUT_JSON = ROOT / "data" / "raw" / "r1_trades_2021_2025.json"
CACHE_DIR = ROOT / "data" / "raw"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
       "AppleWebKit/537.36 (KHTML, like Gecko) "
       "Chrome/120.0 Safari/537.36")

# Map Wikipedia's city-only links to our canonical 3-letter abbreviations.
# Wikipedia often uses links like "2025 Cleveland Browns season" -> "CLE".
TEAM_NICK_TO_ABBR = {
    "Cardinals": "ARI", "Falcons": "ATL", "Ravens": "BAL", "Bills": "BUF",
    "Panthers": "CAR", "Bears": "CHI", "Bengals": "CIN", "Browns": "CLE",
    "Cowboys": "DAL", "Broncos": "DEN", "Lions": "DET", "Packers": "GB",
    "Texans": "HOU", "Colts": "IND", "Jaguars": "JAX", "Chiefs": "KC",
    "Chargers": "LAC", "Rams": "LAR", "Raiders": "LV", "Dolphins": "MIA",
    "Vikings": "MIN", "Patriots": "NE", "Saints": "NO", "Giants": "NYG",
    "Jets": "NYJ", "Eagles": "PHI", "Steelers": "PIT", "Seahawks": "SEA",
    "49ers": "SF", "Buccaneers": "TB", "Titans": "TEN",
    "Commanders": "WAS", "Washington": "WAS",  # pre-2022 also "Football Team"
    "Football Team": "WAS",
}

# Wikipedia note text sometimes only gives the CITY ("from Cleveland") without
# the full nickname. Map these to canonical abbrs. "New York" is ambiguous so
# we fall back to Giants (they're the more common draft trader) — but if the
# note specifies Jets/Giants it wins via TEAM_NICK_TO_ABBR above.
CITY_TO_ABBR = {
    "Arizona": "ARI", "Atlanta": "ATL", "Baltimore": "BAL", "Buffalo": "BUF",
    "Carolina": "CAR", "Chicago": "CHI", "Cincinnati": "CIN", "Cleveland": "CLE",
    "Dallas": "DAL", "Denver": "DEN", "Detroit": "DET", "Green Bay": "GB",
    "Houston": "HOU", "Indianapolis": "IND", "Jacksonville": "JAX",
    "Kansas City": "KC", "Las Vegas": "LV", "Miami": "MIA",
    "Minnesota": "MIN", "New England": "NE", "New Orleans": "NO",
    "Philadelphia": "PHI", "Pittsburgh": "PIT", "Seattle": "SEA",
    "San Francisco": "SF", "Tampa Bay": "TB", "Tennessee": "TEN",
    "Washington": "WAS",
    # LA-area teams and ambiguous "New York" fall back via longer matches.
    "Los Angeles Rams": "LAR", "Los Angeles Chargers": "LAC",
    "New York Giants": "NYG", "New York Jets": "NYJ",
}

TEAM_LINK_RX = re.compile(
    r'<a [^>]*title="\d{4} ([A-Za-z ]+) season"[^>]*>[^<]+</a>'
)

# Row parser — matches a <tr> block that represents one pick.
# We look for the Pick anchor, then the team link, player, position, notes.
ROW_RX = re.compile(
    r'<span class="anchor" id="Pick[^>]+></span>\s*'
    r'<b>(?:<a [^>]*>)?(\d+)(?:</a>)?</b>',   # pick number
    re.IGNORECASE,
)


def fetch_page(year: int) -> str:
    cache = CACHE_DIR / f"wiki_draft_{year}.html"
    if cache.exists():
        return cache.read_text(encoding="utf-8")
    url = f"https://en.wikipedia.org/wiki/{year}_NFL_draft"
    print(f"[fetch] {url}")
    r = requests.get(url, headers={"User-Agent": UA}, timeout=25)
    r.raise_for_status()
    cache.write_text(r.text, encoding="utf-8")
    time.sleep(1.5)   # be polite
    return r.text


def team_from_link_match(fragment: str) -> str | None:
    """Given an HTML fragment containing a team link, return 3-letter abbr."""
    m = TEAM_LINK_RX.search(fragment)
    if not m:
        return None
    nickname = m.group(1).strip()
    # nickname like "Cleveland Browns" or "Washington Commanders" or "New York Giants"
    for key, abbr in TEAM_NICK_TO_ABBR.items():
        if nickname.endswith(key):
            return abbr
    # As a fallback try the last word
    last = nickname.split()[-1]
    return TEAM_NICK_TO_ABBR.get(last)


FROM_RX = re.compile(r'from\s+<a [^>]*title="\d{4} ([A-Za-z ]+) season"',
                      re.IGNORECASE)
FROM_TEXT_RX = re.compile(r'from\s+(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                          re.IGNORECASE)


def origin_from_notes(notes_html: str) -> str | None:
    """Pull the original team out of a pick's Notes cell."""
    m = FROM_RX.search(notes_html)
    if m:
        nick = m.group(1).strip()
        for key, abbr in TEAM_NICK_TO_ABBR.items():
            if nick.endswith(key):
                return abbr
        for key, abbr in CITY_TO_ABBR.items():
            if nick.startswith(key):
                return abbr
    # Fallback: plain-text "from XYZ"
    stripped = re.sub(r"<[^>]+>", " ", notes_html)
    m = FROM_TEXT_RX.search(stripped)
    if m:
        raw = m.group(1).strip()
        # Try progressively — longest city-match first, then nickname.
        for key, abbr in sorted(CITY_TO_ABBR.items(), key=lambda kv: -len(kv[0])):
            if raw.startswith(key):
                return abbr
        for key, abbr in TEAM_NICK_TO_ABBR.items():
            if raw.endswith(key) or key in raw:
                return abbr
    return None


PLAYER_RX = re.compile(r'<span class="fn">(?:<a [^>]*>)?([^<]+)')
POSITION_RX = re.compile(r'title="(Quarterback|Running back|Wide receiver|'
                          r'Tight end|Offensive tackle|Offensive guard|Center|'
                          r'Defensive end|Defensive tackle|Linebacker|Cornerback|'
                          r'Safety|Fullback)"')


def extract_round_one(html: str, year: int) -> list[dict]:
    """Split on <tr> boundaries, keep R1 rows, extract fields per row."""
    # Find the main draft table's body.
    start = html.find('<table class="wikitable sortable plainrowheaders"')
    if start < 0:
        return []
    end = html.find('</table>', start)
    body = html[start:end]
    # Decode the &#95; -> _ encoding used in anchors so regexes match.
    body = body.replace("&#95;", "_")

    rows = re.split(r'<tr', body)
    out: list[dict] = []
    current_round: int | None = None
    for r in rows:
        # Round header detection — rows with id="Round_N" OR a <th> with round
        m = re.search(r'id="Round&#95;(\d+)"', r) or re.search(r'id="Round_(\d+)"', r)
        if m:
            current_round = int(m.group(1))
        # Tag round from the first <th>N</th> if no id seen yet
        if current_round is None:
            m = re.search(r'<th>(\d+)\s*</th>', r)
            if m:
                current_round = int(m.group(1))
        if current_round != 1:
            continue
        pick_m = ROW_RX.search(r)
        if not pick_m:
            continue
        pick = int(pick_m.group(1))
        if pick > 32:
            # Once we exceed R1, stop processing this table (pick counter
            # increments monotonically within a round; anything >32 is R2+).
            break

        # Cells layout: [round-color td][team][player][position][college][conf][notes]
        # The leading round-indicator cell is always empty, so shift by 1.
        cells = re.findall(r'<td[^>]*>(.*?)</td>', r, re.DOTALL)
        if len(cells) < 5:
            continue
        team_cell = cells[1]
        player_cell = cells[2] if len(cells) > 2 else ""
        pos_cell = cells[3] if len(cells) > 3 else ""
        notes_cell = cells[-1]   # notes is always last

        final_team = team_from_link_match(team_cell)
        origin = origin_from_notes(notes_cell) or final_team
        player_m = PLAYER_RX.search(player_cell)
        pos_m = POSITION_RX.search(pos_cell) or POSITION_RX.search(player_cell)
        player = player_m.group(1).strip() if player_m else None
        pos = pos_m.group(1)[:2].upper() if pos_m else None

        if final_team is None:
            continue

        direction = "none"
        if origin and origin != final_team:
            # Direction relative to original pick holder.
            # If original team OWNED this slot (pick N) and traded it to the
            # final team which had a LATER slot originally, the final team
            # traded UP (gave up later pick for earlier). We don't have
            # original-slot for final team here, so we mark the pick as
            # "traded" and compute direction heuristically by pick bucket
            # later. For now keep it as "swap".
            direction = "swap"

        out.append({
            "year": year,
            "pick": pick,
            "final_team": final_team,
            "original_team": origin,
            "player": player,
            "position": pos,
            "direction": direction,
        })
    return out


def main() -> None:
    all_rows: list[dict] = []
    counts: dict[int, int] = {}
    for year in [2021, 2022, 2023, 2024, 2025]:
        try:
            html = fetch_page(year)
        except Exception as e:
            print(f"[error] fetch {year}: {e}", file=sys.stderr)
            continue
        rows = extract_round_one(html, year)
        counts[year] = len(rows)
        all_rows.extend(rows)
        n_trades = sum(1 for r in rows if r["direction"] == "swap")
        print(f"[{year}] {len(rows)} R1 rows, {n_trades} traded")

    trades = [r for r in all_rows if r["direction"] == "swap"]

    OUT_JSON.write_text(
        json.dumps({
            "years": list(counts.keys()),
            "r1_pick_counts": counts,
            "total_trades": len(trades),
            "all_rows": all_rows,
            "trades": trades,
        }, indent=2),
        encoding="utf-8",
    )
    print(f"\nSaved -> {OUT_JSON}")
    print(f"Total R1 trades 2021-2025: {len(trades)} "
          f"across {sum(counts.values())} picks")

    # Per-team summary
    down_counts: dict[str, int] = {}
    up_counts: dict[str, int] = {}
    for t in trades:
        # Original team (traded away) -> trade-DOWN column
        down_counts[t["original_team"]] = down_counts.get(t["original_team"], 0) + 1
        # Final team (acquired) -> trade-UP column
        up_counts[t["final_team"]] = up_counts.get(t["final_team"], 0) + 1
    print("\nTrade-down counts (team gave up R1 slot):")
    for t, n in sorted(down_counts.items(), key=lambda kv: -kv[1]):
        print(f"  {t}: {n}")
    print("\nTrade-up counts (team acquired an R1 slot):")
    for t, n in sorted(up_counts.items(), key=lambda kv: -kv[1]):
        print(f"  {t}: {n}")


if __name__ == "__main__":
    main()
