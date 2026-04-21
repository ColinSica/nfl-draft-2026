"""Apply insider intel from 4/20 sweep to team_agents_2026.json.
Source: data/features/final_intel_2026_04_20.json + agent report."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).parent
TA = ROOT / "data/features/team_agents_2026.json"
d = json.loads(TA.read_text(encoding="utf-8"))

def bump(team: str, key: str, value, reason: str):
    if team in d and isinstance(d[team], dict):
        # nested keys supported via dot-path
        if "." in key:
            a, b = key.split(".", 1)
            d[team].setdefault(a, {})[b] = value
        else:
            d[team][key] = value
        existing = d[team].get("_4_21_news", [])
        if isinstance(existing, str):
            existing = [existing]
        existing.append(reason)
        d[team]["_4_21_news"] = existing
        print(f"  {team}: {key} -> {value} ({reason})")

# LV — Mendoza near-lock, cut trade-down
bump("LV", "trade_behavior.trade_down_rate", 0.05,
     "Spytek presser 4/20: 'teams know where they stand' — Mendoza effective lock")

# ARI — Love chatter growing; keep trade-down as branch
ari_needs = d.get("ARI", {}).get("roster_needs", {})
ari_needs["RB"] = max(float(ari_needs.get("RB", 0)), 3.5)
d["ARI"]["roster_needs"] = dict(sorted(ari_needs.items(), key=lambda kv: -kv[1]))
bump("ARI", "trade_behavior.trade_down_rate", 0.30,
     "Schefter 4/20: growing chatter on Love at 3; trade-down still live")

# NYG already has 5,10; enforce IDL need post-Lawrence dep; reduce EDGE
nyg_needs = d.get("NYG", {}).get("roster_needs", {})
nyg_needs["IDL"] = max(float(nyg_needs.get("IDL", 0)), 4.0)
if "EDGE" in nyg_needs: nyg_needs["EDGE"] = min(float(nyg_needs["EDGE"]), 2.0)
d["NYG"]["roster_needs"] = dict(sorted(nyg_needs.items(), key=lambda kv: -kv[1]))
d["NYG"]["_4_21_news"] = ["Rapoport 4/19: Dexter Lawrence to CIN — NYG now holds 5 AND 10; IDL need spikes; Thibodeaux staying"]

# CIN — no R1 pick; remove R1 pick ownership confirmation
cin = d.get("CIN", {})
cin["pick"] = None
cin["r1_picks"] = []
cin["all_r1_picks"] = []
cin["_4_21_news"] = ["Out of R1: sent pick 10 to NYG for Dexter Lawrence (Rapoport 4/19)"]
d["CIN"] = cin

# PIT — OT need R1 tier
pit_needs = d.get("PIT", {}).get("roster_needs", {})
pit_needs["OT"] = max(float(pit_needs.get("OT", 0)), 5.0)
d["PIT"]["roster_needs"] = dict(sorted(pit_needs.items(), key=lambda kv: -kv[1]))
bump("PIT", "_4_21_news_qb", "Rodgers silence + Broderick Jones neck setback — OT R1 lock contingent on QB path",
     "Breer 4/20")

# PHI — trade-up 0.35; Brown deferred = cap WR
phi_needs = d.get("PHI", {}).get("roster_needs", {})
if "WR" in phi_needs: phi_needs["WR"] = min(float(phi_needs["WR"]), 2.0)
d["PHI"]["roster_needs"] = dict(sorted(phi_needs.items(), key=lambda kv: -kv[1]))
bump("PHI", "trade_behavior.trade_up_rate", 0.35,
     "Schefter 4/20: Roseman 'plotting a deal' — WR urgency deferred post-Jun-1")

# CLE — multi-path asset; bump trade up AND down
bump("CLE", "trade_behavior.trade_up_rate", 0.25,
     "Berry presser 4/20: 'maximize the asset' — trade-up branch new")
bump("CLE", "trade_behavior.trade_down_rate", 0.70,
     "Berry 4/20: trade-down also live")

# SEA — trade-down + RB
sea_needs = d.get("SEA", {}).get("roster_needs", {})
sea_needs["RB"] = max(float(sea_needs.get("RB", 0)), 4.5)
d["SEA"]["roster_needs"] = dict(sorted(sea_needs.items(), key=lambda kv: -kv[1]))
bump("SEA", "trade_behavior.trade_down_rate", 0.55,
     "4/20: SEA actively shopping 32 — RB top need")

# KC — trade-up 0.25 for EDGE
bump("KC", "trade_behavior.trade_up_rate", 0.25,
     "4/20: Veach exploring trade-up to 3-4 for top EDGE; contacted ARI & TEN")

# TEN — Styles backup if Love gone
bump("TEN", "_4_21_news_pick4", "Schefter 4/20: P(Styles at 4 | Love gone) ~0.45",
     "conditional on ARI not taking Love at 3")

# CHI — remove QB latent need
chi_latent = d.get("CHI", {}).get("latent_needs", {})
if chi_latent and "QB" in chi_latent:
    del chi_latent["QB"]
    d["CHI"]["_4_21_news"] = ["Bears-Bagent cooling (smoke 4/20) — QB latent need removed"]

# MIN — Greenard contingency
bump("MIN", "_4_21_news_edge", "Schefter 4/20: Greenard trade talks reignited — EDGE replacement contingent",
     "if PHI completes Greenard deal, MIN pivots draft")

# Medical updates
med = d.get("_meta_medical_flags_2026", {}) or {}
# Nussmeier stabilized
med["Garrett Nussmeier"] = {
    "type": "spinal_cyst_asymptomatic",
    "severity": "low",
    "detail": "Pelissero 4/20: asymptomatic post-diagnosis; Day 2 projection stable."
}
# Tyson DOWN (hamstring)
med["Jordyn Tyson"] = {
    "type": "hamstring_durability",
    "severity": "medium",
    "detail": "Jeremiah 4/20 mock: dropped 4 spots to WR21 over hamstring durability concerns."
}
# McCoy DOWN (medical file)
med["Jermod McCoy"] = {
    "type": "acl_medical_file_reviewed",
    "severity": "medium",
    "detail": "4/20: despite 4.39 pro day, teams flagging medical file — late-R1 / early-R2."
}
# Broderick Jones setback (not in draft but affects PIT planning) — skip
d["_meta_medical_flags_2026"] = med
print("  Medical flags updated (Nussmeier low, Tyson medium, McCoy medium)")

TA.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
print("\nWrote team_agents_2026.json with 4/21 insider intel")
