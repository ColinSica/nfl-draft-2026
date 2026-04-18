"""
Daily intel updater.

Scrapes 4 sources, merges what succeeds, computes deltas vs the most recent
prior snapshot, and updates prospects_2026_enriched.csv with the latest values.

Outputs
-------
  data/live/betting_odds_{YYYY-MM-DD}.json       (if VegasInsider or CBS works)
  data/live/visits_{YYYY-MM-DD}.json             (NFL Trade Rumors + CBS visits)
  data/live/master_intel_latest.json             merged snapshot
  data/processed/prospects_2026_enriched_{YYYY-MM-DD}.csv   dated snapshot

Known limitations:
  - profootballnetwork.com/nfl-draft-hq/top-30-visits returns 403 (bot-blocked)
  - VegasInsider draft page exists but carries very little per-player odds data
  - CBS top-10 odds tracker has betting content; best-effort parse
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz, process

ROOT = Path(__file__).resolve().parents[2]
LIVE_DIR = ROOT / "data" / "live"
PROC_DIR = ROOT / "data" / "processed"
PROS_CSV = PROC_DIR / "prospects_2026_enriched.csv"

LIVE_DIR.mkdir(parents=True, exist_ok=True)
PROC_DIR.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")
TODAY = date.today().isoformat()

SOURCES = {
    "vegasinsider": "https://www.vegasinsider.com/nfl/odds/draft/",
    "cbs_odds":     "https://www.cbssports.com/betting/news/2026-nfl-draft-odds-tracker-top-10-picks/",
    "nflvisits":    "https://nfltraderumors.co/2026-nfl-draft-visit-tracker/",
    "walterfootball": "https://walterfootball.com/ProspectMeetingsByTeam2026.php",
    "twsn_stock":   "https://twsn.net/2026/04/12/2026-nfl-draft-risers-fallers-offense/",
    # pfn_visits returns 403; dropped. Sharp Football lacks per-player names; skipped.
}

NICKNAMES = {
    "49ers": "SF", "Bears": "CHI", "Bengals": "CIN", "Bills": "BUF",
    "Broncos": "DEN", "Browns": "CLE", "Buccaneers": "TB", "Cardinals": "ARI",
    "Chargers": "LAC", "Chiefs": "KC", "Colts": "IND", "Commanders": "WAS",
    "Cowboys": "DAL", "Dolphins": "MIA", "Eagles": "PHI", "Falcons": "ATL",
    "Giants": "NYG", "Jaguars": "JAX", "Jets": "NYJ", "Lions": "DET",
    "Packers": "GB", "Panthers": "CAR", "Patriots": "NE", "Raiders": "LV",
    "Rams": "LAR", "Ravens": "BAL", "Saints": "NO", "Seahawks": "SEA",
    "Steelers": "PIT", "Texans": "HOU", "Titans": "TEN", "Vikings": "MIN",
}


def fetch(url: str) -> str | None:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=25, allow_redirects=True)
        if r.status_code != 200 or len(r.text) < 1000:
            return None
        return r.text
    except requests.RequestException:
        return None


def parse_cbs_odds(html: str, prospect_names: list[str]) -> dict[str, dict]:
    """Best-effort: CBS article has odds scattered in prose. Extract player-odds pairs."""
    text = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
    out: dict[str, dict] = {}
    for name in prospect_names:
        if len(name) < 5 or name not in text:
            continue
        idx = text.find(name)
        window = text[max(0, idx - 80): idx + 250]
        m = re.search(r"([+-]\d{3,5})\b", window)
        if m:
            odds = int(m.group(1))
            prob = (100 / (odds + 100)) if odds > 0 else (-odds / (-odds + 100))
            out[name] = {"american_odds": odds, "implied_prob": prob}
    return out


def parse_visits_article(html: str, prospect_names: list[str]) -> dict[str, dict]:
    """Scan article text for player-name -> nearby team nicknames."""
    text = BeautifulSoup(html, "lxml").get_text("\n", strip=True)
    out: dict[str, dict] = {}
    nick_re = re.compile(
        r"\b(" + "|".join(re.escape(n) for n in NICKNAMES.keys()) + r")\b")
    for name in prospect_names:
        if len(name) < 5 or name not in text:
            continue
        idx = text.find(name)
        window = text[max(0, idx - 120): idx + 500]
        teams = {NICKNAMES[m.group(1)] for m in nick_re.finditer(window)}
        cancelled = bool(re.search(r"cancel|withdraw|pull", window, re.IGNORECASE))
        out[name] = {
            "teams_visited": sorted(teams),
            "cancelled_visit_flag": int(cancelled),
        }
    return out


def load_latest_snapshot() -> dict | None:
    f = LIVE_DIR / "master_intel_latest.json"
    if not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))


def main():
    pros = pd.read_csv(PROS_CSV)
    names = pros["player"].dropna().astype(str).tolist()

    print(f"Probing {len(SOURCES)} sources...")
    htmls = {key: fetch(url) for key, url in SOURCES.items()}
    for key, html in htmls.items():
        status = "OK" if html else "FAIL"
        n = len(html) if html else 0
        print(f"  {key:<14} {status}  bytes={n}")

    # Parse
    odds_cbs = parse_cbs_odds(htmls["cbs_odds"], names) if htmls["cbs_odds"] else {}
    odds_vi = parse_cbs_odds(htmls["vegasinsider"], names) if htmls["vegasinsider"] else {}
    visits_nfl = parse_visits_article(htmls["nflvisits"], names) if htmls["nflvisits"] else {}
    visits_wf = parse_visits_article(htmls["walterfootball"], names) if htmls.get("walterfootball") else {}
    # TWSN stock-direction parse: detect "rise" vs "fall" near each name
    stock_moves: dict[str, dict] = {}
    if htmls.get("twsn_stock"):
        twsn_text = BeautifulSoup(htmls["twsn_stock"], "lxml").get_text(" ", strip=True).lower()
        falling_anchor = twsn_text.find("falling")
        for name in names:
            if len(name) < 5 or name.lower() not in twsn_text:
                continue
            loc = twsn_text.find(name.lower())
            direction = -1 if (falling_anchor > 0 and loc >= falling_anchor) else 1
            stock_moves[name] = {"stock_direction_daily": direction}

    # Persist source-level snapshots
    for key, payload in [
        ("betting_odds_cbs", odds_cbs),
        ("betting_odds_vegasinsider", odds_vi),
        ("visits_nfltr", visits_nfl),
        ("visits_walterfootball", visits_wf),
        ("stock_moves_twsn", stock_moves),
    ]:
        (LIVE_DIR / f"{key}_{TODAY}.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8")

    # Merge into master
    master: dict = {"timestamp": TODAY, "players": {}}
    for source_dict in (odds_cbs, odds_vi):
        for name, info in source_dict.items():
            master["players"].setdefault(name, {})
            master["players"][name].update(info)
    for source_dict in (visits_nfl, visits_wf):
        for name, info in source_dict.items():
            master["players"].setdefault(name, {})
            # Union of teams if already present
            existing = master["players"][name].get("teams_visited", [])
            master["players"][name]["teams_visited"] = sorted(set(existing) | set(info["teams_visited"]))
            master["players"][name]["cancelled_visit_flag"] = max(
                master["players"][name].get("cancelled_visit_flag", 0),
                info.get("cancelled_visit_flag", 0))

    # Compare with prior snapshot
    prior = load_latest_snapshot()
    changes = []
    if prior:
        prior_players = prior.get("players", {})
        for name, now in master["players"].items():
            before = prior_players.get(name, {})
            if set(now.get("teams_visited", [])) > set(before.get("teams_visited", [])):
                new_teams = sorted(set(now["teams_visited"]) - set(before.get("teams_visited", [])))
                changes.append(f"{name}: new visits {new_teams}")
            if now.get("cancelled_visit_flag", 0) and not before.get("cancelled_visit_flag", 0):
                changes.append(f"{name}: visit cancelled (new)")
            if (now.get("implied_prob") is not None
                    and before.get("implied_prob") is not None
                    and abs(now["implied_prob"] - before["implied_prob"]) > 0.05):
                changes.append(f"{name}: betting prob "
                               f"{before['implied_prob']:.2f}→{now['implied_prob']:.2f}")

    (LIVE_DIR / "master_intel_latest.json").write_text(
        json.dumps(master, indent=2), encoding="utf-8")

    # Propagate simple fields back onto prospects_2026_enriched.csv
    # Only when the intel is non-empty and more authoritative than what's there.
    updated_visit_rows = 0
    updated_betting_rows = 0
    for idx, row in pros.iterrows():
        name = row.get("player")
        info = master["players"].get(name, {})
        if info.get("teams_visited"):
            # Update visit_count / top30_visit_flag / visited_teams
            visits = info["teams_visited"]
            pros.at[idx, "visit_count"] = len(visits)
            pros.at[idx, "top30_visit_flag"] = 1 if visits else 0
            pros.at[idx, "visited_teams"] = ",".join(visits)
            updated_visit_rows += 1
        if info.get("implied_prob") is not None:
            pros.at[idx, "betting_implied_prob"] = info["implied_prob"]
            updated_betting_rows += 1

    pros.to_csv(PROS_CSV, index=False)
    dated_snapshot = PROC_DIR / f"prospects_2026_enriched_{TODAY}.csv"
    pros.to_csv(dated_snapshot, index=False)

    # Report
    print("\n" + "=" * 60)
    print("DAILY INTEL UPDATE — change report")
    print("=" * 60)
    print(f"Date: {TODAY}")
    print(f"Prospects with visits merged: {updated_visit_rows}")
    print(f"Prospects with betting odds merged: {updated_betting_rows}")
    print(f"Unique players in master intel: {len(master['players'])}")
    if prior is None:
        print("(first-ever run — no change comparison)")
    else:
        print(f"\nChanges vs prior ({prior.get('timestamp', '?')}):")
        if changes:
            for c in changes[:30]:
                print(f"  {c}")
        else:
            print("  (no material changes)")

    print(f"\nSnapshots:")
    print(f"  {LIVE_DIR / 'master_intel_latest.json'}")
    print(f"  {dated_snapshot}")


if __name__ == "__main__":
    main()
