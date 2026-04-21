"""Apply 4/21 pressers + final mocks to team_agents_2026.json.
Source: data/features/final_pressers_mocks_4_21.json + agent report."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).parent
TA = ROOT / "data/features/team_agents_2026.json"
d = json.loads(TA.read_text(encoding="utf-8"))

def nset(team, path, value, note):
    if team not in d or not isinstance(d[team], dict): return
    keys = path.split(".")
    obj = d[team]
    for k in keys[:-1]:
        obj = obj.setdefault(k, {})
    obj[keys[-1]] = value
    news = d[team].get("_4_21_pressers", [])
    if isinstance(news, str): news = [news]
    news.append(note)
    d[team]["_4_21_pressers"] = news

# WAS — Peters presser: staying at 7, zero NFC-East trades
nset("WAS", "trade_behavior.trade_down_rate", 0.15,
     "Peters 4/21 presser: 'more likely than not staying at 7'; zero intra-NFC-East trades")

# LV — Spytek reaffirmed Mendoza near-certainty
nset("LV", "trade_behavior.trade_down_rate", 0.03,
     "Spytek 4/21: re-affirmed willingness to stay at 1; P(Mendoza) ~= 0.97")

# MIA — Sullivan presser: much more likely to trade down at 11
nset("MIA", "trade_behavior.trade_down_rate", 0.62,
     "Sullivan 4/21: 'much more likely to trade down' at 11")

# SEA — Schneider: publicly declared trade-back intent
nset("SEA", "trade_behavior.trade_down_rate", 0.65,
     "Schneider 4/20: publicly declared trade-back intent at 32, willing to deal in NFC West")

# ARI — Ossenfort hinted R2 QB (Ty Simpson smokescreen)
ari = d.get("ARI", {})
if "latent_needs" not in ari: ari["latent_needs"] = {}
ari["latent_needs"]["QB_R2"] = 0.35
d["ARI"] = ari
nset("ARI", "_4_21_presser_note", "Ossenfort 4/21: hinted R2 QB (Ty Simpson type)",
     "Smokescreen-adjusted; don't force R1 QB")

# PIT — Khan: may pick non-visit R1 player (loosen visit prior for PIT)
nset("PIT", "_4_21_presser_loosen_visit", True,
     "Khan 4/20: hinted R1 player not hosted on pre-draft visit — breaks visit-correlation prior")

# DAL — Jones: "Absolutely" open + double-1st = highest trade-activity signal
nset("DAL", "trade_behavior.trade_up_rate", 0.40,
     "Jones 4/21: 'Absolutely' open to trade")
nset("DAL", "trade_behavior.trade_down_rate", 0.45,
     "Jones 4/21: double-1st + open = highest trade-activity signal")

# TEN — Love at 4 very high consensus (9 finals)
nset("TEN", "_4_21_lock_signal", "Love @ 4 agreed across 9 final mocks (Kiper, Jeremiah, Brugler, Zierlein, PFF, McShay, BR, Simms, CBS)",
     "High-confidence lock contingent on ARI not taking Love at 3")

# NYJ — Reese risk (Schrager/McShay dissent)
nset("NYJ", "_4_21_reese_dissent", "Schrager/McShay finals dissent on Reese at 2 — Bailey remains competitive alt",
     "Signals Reese not 100% — alternate EDGE still live")

# GB — scheme/presser info
nset("GB", "_4_21_presser_note", "Low-key pre-draft presser; no major shifts",
     "Standard board-driven")

# Write
TA.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
print("Applied 4/21 presser-based edits to 10 teams")
print("Teams updated: WAS, LV, MIA, SEA, ARI, PIT, DAL, TEN, NYJ, GB")
