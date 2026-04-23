"""Apply the 4/22 day-of-draft intel to team_agents_2026.json.

Source file: data/features/day_of_news_2026_04_22.json

Appends a `_4_22_news` (array) to affected teams and adjusts a small set of
numerical knobs (trade rates, need scores) where the market signal is hard.
The frontend TeamDetail page auto-picks the freshest `_<M>_<D>_news` entry,
so writing this key surfaces the new intel on every team page.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
TA = ROOT / "data/features/team_agents_2026.json"
d = json.loads(TA.read_text(encoding="utf-8"))


def append_news(team: str, note: str) -> None:
    if team not in d or not isinstance(d[team], dict):
        print(f"  [skip] unknown team {team}")
        return
    existing = d[team].get("_4_22_news", [])
    if isinstance(existing, str):
        existing = [existing]
    existing.append(note)
    d[team]["_4_22_news"] = existing


def set_path(team: str, dotted: str, value) -> None:
    if team not in d:
        return
    obj = d[team]
    keys = dotted.split(".")
    for k in keys[:-1]:
        obj = obj.setdefault(k, {})
    obj[keys[-1]] = value


def bump_need(team: str, pos: str, floor: float) -> None:
    needs = d.get(team, {}).get("roster_needs", {})
    if not needs:
        return
    needs[pos] = max(float(needs.get(pos, 0)), floor)
    d[team]["roster_needs"] = dict(sorted(needs.items(), key=lambda kv: -kv[1]))


# ──────────────────────── LV @ 1 ────────────────────────
# No new Mendoza news today — 4/21 already locked him; hold.

# ──────────────────────── NYJ @ 2 ────────────────────────
append_news(
    "NYJ",
    "Rapoport 4/22: #2 pick narrowed to two EDGE — David Bailey (TTU) and Arvell Reese (OSU). Books within ~2 bps.",
)
append_news(
    "NYJ",
    "NFL.com 4/22: Jets cancelled David Bailey top-30 visit this week. Ambiguous: 'decision made' signal either direction.",
)

# ──────────────────────── ARI @ 3 ────────────────────────
append_news(
    "ARI",
    "Schefter 4/22: Cardinals shopped #3 with no takers. If they hold, Jeremiyah Love (ND RB) is the 'logical' pick.",
)
# Trade-down priced lower now that no buyer materialized.
set_path("ARI", "trade_behavior.trade_down_rate", 0.18)
set_path("ARI", "trade_behavior.pdf_tier.trade_down_tier", "LOW")
set_path("ARI", "trade_behavior.pdf_tier.trade_down_prob", 0.18)

# ──────────────────────── TEN @ 4 ────────────────────────
append_news(
    "TEN",
    "ESPN beat 4/22: Titans want to trade down from 4. If they hold and Bailey is there, Bailey is the pick. Otherwise highest-graded WR (Carnell Tate or Jordyn Tyson).",
)
set_path("TEN", "trade_behavior.trade_down_rate", 0.45)
bump_need("TEN", "WR", 3.0)  # surface the Tate/Tyson branch

# ──────────────────────── NYG @ 5 & 10 ────────────────────────
append_news(
    "NYG",
    "ESPN beat 4/22: Giants at 5 most likely Jeremiyah Love (if there) or Caleb Downs. At 10: Styles, Downs, Tate, Love + post-Lawrence IDL.",
)

# ──────────────────────── CLE @ 6 ────────────────────────
append_news(
    "CLE",
    "Graziano 4/22: Browns open to trading down from 6. Named up-partners: KC, NYG, MIA, LAR, WAS. Berry front office has circulated the offer.",
)
# Keep 0.70 trade-down; we had it.

# ──────────────────────── WAS @ 7 ────────────────────────
append_news(
    "WAS",
    "ESPN beat 4/22: Commanders narrowed #7 targets to Sonny Styles, Caleb Downs, Carnell Tate, Jeremiyah Love.",
)

# ──────────────────────── NO @ 8 ────────────────────────
append_news(
    "NO",
    "Schefter 4/22: Saints open to BPA at 8. Would take Carnell Tate quickly if on board (Ohio State reunion w/ Chris Olave). OC Nussmeier excused from draft duties — son in draft. Kamara/Cameron Jordan futures pivot on draft outcome.",
)

# ──────────────────────── KC @ 9 ────────────────────────
append_news(
    "KC",
    "NFL Net 4/22: Chiefs at 9 — Rueben Bain (EDGE) if there, else Jordyn Tyson (WR). Veach trade-up to 3-4 for a top EDGE also live.",
)

# ──────────────────────── MIA @ 11 ────────────────────────
append_news(
    "MIA",
    "NFL.com 4/22: Dolphins still in the QB market. Packaging 11 + 30 for a veteran QB, or grabbing a passer at 11, both live scenarios.",
)

# ──────────────────────── DAL @ 12/20 ────────────────────────
append_news(
    "DAL",
    "Jerry Jones presser 4/22: 'We have trades... Picks or players, you could imagine that.' Stephen Jones: not required to keep both R1s.",
)

# ──────────────────────── DET @ 17 ────────────────────────
append_news(
    "DET",
    "Rapoport 4/22: teams could try to trade up to 15-16 to jump Lions for an OT. Named: CAR, PHI, SF. DET OT need urgent.",
)
set_path("DET", "trade_behavior.trade_up_rate", 0.50)
bump_need("DET", "OT", 4.5)

# ──────────────────────── PIT @ 21 ────────────────────────
append_news(
    "PIT",
    "CBS/books 4/22: PIT +330 second-favorite for Carson Beck (Miami QB). Beat writers: 'not in R1.' OT R1 lock unless Beck slides further.",
)

# ──────────────────────── SEA @ 32 ────────────────────────
append_news(
    "SEA",
    "John Schneider presser 4/22: 'We have four picks. We'll be looking to trade back.' Seattle very likely ships 32.",
)
set_path("SEA", "trade_behavior.trade_down_rate", 0.75)

# ──────────────────────── MIN @ 24 ────────────────────────
append_news(
    "MIN",
    "Schefter 4/22: Vikings 'will draft a defensive player.' Aligns with Flores scheme premium — DB/front-seven dominant.",
)
# Skew MIN position prob via need emphasis
bump_need("MIN", "CB", 3.5)
bump_need("MIN", "S", 3.5)
bump_need("MIN", "EDGE", 3.5)

# ──────────────────────── CHI ────────────────────────
append_news(
    "CHI",
    "Mock chatter 4/22: Bears could nab Keldric Faulk at 21 (from Steelers) per multiple finals. EDGE group still the clearest gap.",
)

# ──────────────────────── CIN ────────────────────────
append_news(
    "CIN",
    "No R1 pick after Dexter Lawrence trade. Schefter 4/22: Cincy's veteran market activity during draft likely — watch for picks 32-65.",
)

# ──────────────────────── Player medical flags ────────────────────────
med = d.get("_meta_medical_flags_2026", {})
if not isinstance(med, dict):
    med = {}

med["Chris Bell"] = {
    "date": "2026-04-22",
    "status": "ahead_of_schedule",
    "note": "ACL rehab: running 18+ mph per agent (Rapoport). Pre-injury R1 grade; Day 2 realistic.",
    "impact": "upgrade_late_r2",
}
med["Jermod McCoy"] = {
    "date": "2026-04-22",
    "status": "wide_range",
    "note": "ACL + sluggish pre-draft (Breer). Tumble to R2 materially likely.",
    "impact": "downgrade_to_r2",
}
med["Caleb Banks"] = {
    "date": "2026-04-22",
    "status": "cleared_june",
    "note": "CT scan 4/21 shows healing; full football clearance expected early June. Teams received letter.",
    "impact": "day2_lock",
}
med["Francis Mauigoa"] = {
    "date": "2026-04-22",
    "status": "red_flag",
    "note": "Herniated disc; asymptomatic but teams expect surgery. Slide risk into late R1.",
    "impact": "variance_spike",
}

d["_meta_medical_flags_2026"] = med

# ──────────────────────── Meta / freshness ────────────────────────
meta = d.get("_meta", {})
if not isinstance(meta, dict):
    meta = {}
meta["latest_intel_date"] = "2026-04-22"
meta["latest_intel_scraped_at"] = datetime.now(timezone.utc).isoformat(
    timespec="seconds"
)
sources = meta.setdefault("analyst_intel_meta", {}).setdefault("sources", {})
sources.setdefault("2026-04-22", []).extend(
    [
        "Schefter (ESPN)",
        "Rapoport (NFL Network)",
        "Pelissero (NFL Network)",
        "Graziano (ESPN)",
        "Breer (The Ringer)",
        "Schrager (ESPN)",
        "CBS Sports red-flag tracker",
        "PrizePicks live tracker",
        "Team-beat pressers (DAL, SEA, NO, WAS)",
    ]
)
meta["analyst_intel_meta"]["latest_intel_date"] = "2026-04-22"
d["_meta"] = meta

# ──────────────────────── Persist ────────────────────────
TA.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"[4/22] wrote {TA}")

# Summary
touched = [k for k, v in d.items() if isinstance(v, dict) and "_4_22_news" in v]
print(f"[4/22] teams with 4/22 news: {len(touched)} — {', '.join(touched)}")
