"""Apply day-of 4/20/26 news deltas to team profiles and medical flags.

Source: data/features/day_of_news_2026_04_20.json (Agent 7 output).

Concrete updates:
  - Nussmeier: downgrade medical flag (asymptomatic post-spinal-cyst)
  - PIT: bump OT need (Broderick Jones neck setback)
  - KC: bump trade_up_rate (Veach exploring jump to 3/4)
  - CLE: bump trade_down_rate (Berry openly shopping 6)
  - SEA: bump trade_down_rate (SEA shopping 32)
  - PHI: remove WR from needs (Brown trade deferred post-June 1)
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).parent
TEAM_AGENTS = ROOT / "data/features/team_agents_2026.json"

d = json.loads(TEAM_AGENTS.read_text(encoding="utf-8"))

# Medical flag delta — Nussmeier cleared
med = d.get("_meta_medical_flags_2026", {}) or {}
if "Garrett Nussmeier" in med:
    med["Garrett Nussmeier"] = {
        "type": "spinal_cyst_asymptomatic",
        "severity": "low",  # downgraded from prior
        "detail": "Pelissero 2026-04-20: asymptomatic post-spinal-cyst diagnosis; stabilizes at Day 2."
    }
d["_meta_medical_flags_2026"] = med
print(f"  [med] Nussmeier downgraded to severity=low")

# PIT — OT need bump (Jones neck, Schefter 4/20)
pit = d.get("PIT", {})
rn = pit.get("roster_needs", {}) or {}
rn["OT"] = max(float(rn.get("OT", 0)), 4.5)
pit["roster_needs"] = dict(sorted(rn.items(), key=lambda kv: -float(kv[1])))
pit["_4_20_news"] = "Broderick Jones neck setback (Schefter) — OT R1/early D2 now likely"
d["PIT"] = pit
print(f"  [PIT] OT bumped to 4.5 per Jones news")

# KC — trade-up exploration to 3/4 from 9 (Veach, 4/20)
kc = d.get("KC", {})
tb = kc.get("trade_behavior", {}) or {}
tb["trade_up_rate"] = min(float(tb.get("trade_up_rate", 0.15)) + 0.20, 0.70)
tb.setdefault("pdf_tier", {})["trade_up_prob"] = tb["trade_up_rate"]
tb["pdf_tier"]["reason"] = (tb["pdf_tier"].get("reason","") +
    " | 4/20: Veach exploring jump to 3/4").strip()
kc["trade_behavior"] = tb
kc["_4_20_news"] = "Veach exploring trade-up to 3/4 from 9"
d["KC"] = kc
print(f"  [KC] trade_up_rate bumped to {tb['trade_up_rate']:.2f}")

# CLE — openly shopping pick 6 (Berry presser 4/20)
cle = d.get("CLE", {})
tb = cle.get("trade_behavior", {}) or {}
tb["trade_down_rate"] = min(float(tb.get("trade_down_rate", 0.30)) + 0.20, 0.85)
tb.setdefault("pdf_tier", {})["trade_down_prob"] = tb["trade_down_rate"]
tb["pdf_tier"]["reason"] = (tb["pdf_tier"].get("reason","") +
    " | 4/20: Berry presser — 'maximize the asset' at 6").strip()
cle["trade_behavior"] = tb
cle["_4_20_news"] = "Berry openly shopping pick 6"
d["CLE"] = cle
print(f"  [CLE] trade_down_rate bumped to {tb['trade_down_rate']:.2f}")

# SEA — actively shopping pick 32 (4/20)
sea = d.get("SEA", {})
tb = sea.get("trade_behavior", {}) or {}
tb["trade_down_rate"] = min(float(tb.get("trade_down_rate", 0.30)) + 0.25, 0.85)
tb.setdefault("pdf_tier", {})["trade_down_prob"] = tb["trade_down_rate"]
tb["pdf_tier"]["reason"] = (tb["pdf_tier"].get("reason","") +
    " | 4/20: shopping 32, 4 total picks").strip()
sea["trade_behavior"] = tb
sea["_4_20_news"] = "Actively shopping pick 32; 4 total picks; RB top need"
d["SEA"] = sea
print(f"  [SEA] trade_down_rate bumped to {tb['trade_down_rate']:.2f}")

# PHI — Brown to NE deferred post-June 1 so no immediate WR replacement needed
phi = d.get("PHI", {})
rn = phi.get("roster_needs", {}) or {}
if "WR" in rn and float(rn["WR"]) > 2.0:
    rn["WR"] = min(float(rn["WR"]), 2.0)
phi["roster_needs"] = dict(sorted(rn.items(), key=lambda kv: -float(kv[1])))
phi["_4_20_news"] = "Brown-to-NE deferred post-June 1 — no draft WR urgency"
d["PHI"] = phi
print(f"  [PHI] WR need capped at 2.0 (Brown trade deferred)")

# NYG — Thibodeaux "less likely traded" (Rapoport 4/20) — their EDGE need less critical
nyg = d.get("NYG", {})
rn = nyg.get("roster_needs", {}) or {}
if "EDGE" in rn and float(rn["EDGE"]) > 2.5:
    rn["EDGE"] = min(float(rn["EDGE"]), 2.5)
nyg["roster_needs"] = dict(sorted(rn.items(), key=lambda kv: -float(kv[1])))
nyg["_4_20_news"] = "Thibodeaux less likely traded (Rapoport) — EDGE urgency drops"
d["NYG"] = nyg
print(f"  [NYG] EDGE capped at 2.5 (Thibodeaux staying)")

# ARI — growing chatter on Love at 3 (Schefter 4/20)
ari = d.get("ARI", {})
rn = ari.get("roster_needs", {}) or {}
rn["RB"] = max(float(rn.get("RB", 0)), 3.5)  # RB wasn't there before
ari["roster_needs"] = dict(sorted(rn.items(), key=lambda kv: -float(kv[1])))
ari["_4_20_news"] = "Schefter: growing chatter on Love at 3"
d["ARI"] = ari
print(f"  [ARI] RB added at 3.5 (Love chatter)")

TEAM_AGENTS.write_text(json.dumps(d, indent=2, ensure_ascii=False),
                       encoding="utf-8")
print("\nWrote:", TEAM_AGENTS.name)
