"""
Apply corrections flagged in the 2026-04-19 audit pass.

Patches in place:
  data/features/team_agents_2026.json
  data/features/cap_context_2026.json  (suppress via render; no data invention)
  data/features/coaching_tree_2026.json (DAL/PIT HC swap)
  data/features/roster_context_2026.json (IND/NYG/SF/ATL cliff scrub)
  data/features/team_profiles_narrative_2026.json (CIN pick-10 scrub)

Writes .bak.json sidecars before mutating so diffs are inspectable.
"""
import json, shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
FEATURES = ROOT / "data/features"

def load(p):
    return json.loads(p.read_text(encoding="utf-8"))

def save(p, obj):
    bak = p.with_suffix(".bak.json")
    if p.exists() and not bak.exists():
        shutil.copy2(p, bak)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  wrote {p} ({len(json.dumps(obj))} bytes)")

# ----------------------------------------------------------------------------
# 1. Load everything
# ----------------------------------------------------------------------------
AGENTS_P = FEATURES / "team_agents_2026.json"
COACH_P = FEATURES / "coaching_tree_2026.json"
ROSTER_P = FEATURES / "roster_context_2026.json"
NARR_P = FEATURES / "team_profiles_narrative_2026.json"

agents = load(AGENTS_P)
coach = load(COACH_P) if COACH_P.exists() else {}
roster = load(ROSTER_P) if ROSTER_P.exists() else {}
narr = load(NARR_P) if NARR_P.exists() else {}

# ----------------------------------------------------------------------------
# 2. HARD FACTUAL FIXES
# ----------------------------------------------------------------------------

# ---- 1a / 1b: DAL and PIT head-coach swap
# McCarthy left DAL after 2024; Pittsburgh hired him Jan 24 2026.
# Tomlin stepped down Jan 13 2026. Schottenheimer has been DAL HC since 2025.
print("[1a] DAL HC: Mike McCarthy -> Brian Schottenheimer")
dal = agents["DAL"]
dal["hc"] = "Brian Schottenheimer"
dal["new_hc"] = False  # 2025 hire, now a full year in
if "coaching" in dal:
    dal["coaching"]["hc"] = "Brian Schottenheimer"
    dal["coaching"]["hc_tree"] = "pete_carroll_seattle"  # Schotty DNA: Seahawks/Carroll OC era
    dal["coaching"]["hc_college_stints"] = []
dal_narr = dal.setdefault("narrative", {})
dal_narr["leadership"] = ("GM Jerry Jones (de facto) | HC Brian Schottenheimer (2nd year, "
                          "retained after 2025) | OC Schottenheimer doubles | DC Matt Eberflus")
# Scrub McCarthy-era commentary
for k in ("scheme_identity", "context_2025", "gm_fingerprint", "uncertainty_flags"):
    v = dal_narr.get(k)
    if isinstance(v, str) and "McCarthy" in v:
        dal_narr[k] = v.replace("McCarthy", "Schottenheimer")
# Pick 20 provenance (from GB via Parsons trade)
picks_notes = dal_narr.setdefault("pick_provenance", {})
picks_notes["12"] = "DAL native R1 (2025 record: 7-10 — 9-8 prior plus Parsons recovery loss)"
picks_notes["20"] = "Acquired from GB as part of Micah Parsons trade (Sept 2025)"
# Scheme patch
if "scheme" in dal:
    dal["scheme"]["type"] = "schottenheimer_pro_style"
    # Keep premium unchanged — ran WR/EDGE-premium
if "scheme_struct" in dal_narr:
    dal_narr["scheme_struct"]["type"] = "schottenheimer_pro_style"
    dal_narr["scheme_struct"]["raw"] = (
        "Schottenheimer pro-style: vertical passing windows, heavy personnel packages. "
        "Eberflus hybrid 4-3 defense. Premium positions: EDGE, WR, CB."
    )

print("[1b] PIT HC: Mike Tomlin -> Mike McCarthy (2026-cycle hire)")
pit = agents["PIT"]
pit["hc"] = "Mike McCarthy"
pit["new_hc"] = True  # Hired 2026-01-24
if "coaching" in pit:
    pit["coaching"]["hc"] = "Mike McCarthy"
    pit["coaching"]["hc_tree"] = "mccarthy_west_coast"
pit_narr = pit.setdefault("narrative", {})
pit_narr["leadership"] = ("GM Omar Khan (3 drafts) | HC Mike McCarthy (NEW — hired 2026-01-24 "
                          "after Tomlin stepped down 2026-01-13) | OC Arthur Smith | DC Teryl Austin")
# Resolve uncertainty-flag contradiction
if "uncertainty_flags" in pit_narr:
    uf = pit_narr["uncertainty_flags"]
    if isinstance(uf, str):
        pit_narr["uncertainty_flags"] = (
            "New HC McCarthy brings West Coast pass-game principles — scheme fit "
            "for current personnel is uncertain. Rodgers decision on 2026 return "
            "(as of mid-April: 50-50, leaning yes) swings QB urgency materially."
        )
pit_narr.setdefault("context_2026", "McCarthy regime reset. Front-office continuity (Khan).")
if "scheme" in pit:
    pit["scheme"]["type"] = "mccarthy_west_coast"
if "scheme_struct" in pit_narr:
    pit_narr["scheme_struct"]["type"] = "mccarthy_west_coast"
    pit_narr["scheme_struct"]["raw"] = (
        "McCarthy offense: West Coast timing + heavy play-action. Austin 3-4 defense retained. "
        "Premium positions: OT, WR, EDGE, CB."
    )
# Rodgers age fix: 43 -> 42 (born Dec 2 1983)
for c in pit.get("roster_context", {}).get("age_cliffs", []):
    if c.get("player") == "Aaron Rodgers":
        c["age_2026"] = 42
        c["note"] = "Return 2026 TBD — public reporting 'leaning yes' as of mid-April"
# Remove unverified Jalen Ramsey entry (flagged)
pit["roster_context"]["age_cliffs"] = [
    c for c in pit["roster_context"]["age_cliffs"]
    if c.get("player") != "Jalen Ramsey"
]
if "coaching" in pit and "hc_college_stints" in pit["coaching"]:
    pit["coaching"]["hc_college_stints"] = []  # McCarthy has no college stints

# ---- 1c: IND roster scrub + QB urgency
print("[1c] IND: drop retired Rivers, unverified Howard/Abdullah; bump qb_urgency")
ind = agents["IND"]
bad_ind = {"Philip Rivers", "Xavien Howard", "Ameer Abdullah"}
ind["roster_context"]["age_cliffs"] = [
    c for c in ind["roster_context"]["age_cliffs"]
    if c.get("player") not in bad_ind
]
ind["qb_urgency"] = 0.65
ind["qb_situation"] = "bridge_with_developmental"
# Promote QB from latent -> explicit top-tier need
ind_needs = ind.get("roster_needs", {})
ind_needs["QB"] = 3.5
ind["roster_needs"] = dict(sorted(ind_needs.items(), key=lambda kv: -kv[1]))
ind.get("latent_needs", {}).pop("QB", None)
ind_narr = ind.setdefault("narrative", {})
ind_narr["qb_situation"] = (
    "REAL SOURCE OF URGENCY. Daniel Jones (torn Achilles, UFA) unlikely to return "
    "healthy. Riley Leonard (6th-round rookie) not a starter-caliber bridge. "
    "Anthony Richardson trade candidate. Day 2 QB consideration active — "
    "not R1 given no pick, but veteran-trade path (Sam Darnold / JJ McCarthy type) is live."
)

# ---- 1d: CIN post-Dexter-Lawrence-trade scrub
print("[1d] CIN: scrub Pick 10 archetype block (traded to NYG 2026-04-18)")
cin = agents["CIN"]
cin_narr = cin.setdefault("narrative", {})
# Drop the Pick 10 entry from player_archetypes
archs = cin_narr.get("player_archetypes", {})
if "10" in archs:
    del archs["10"]
# Drop Pick 10 from picks list
cin_narr["picks"] = []
cin_narr["pick_note"] = "Pick 10 traded to NYG (2026-04-18) for Dexter Lawrence + $28M/1yr ext"
cin_narr["context_2026"] = (
    "Traded pick 10 to NYG for Dexter Lawrence 2026-04-18. Bengals now a Day 2 team. "
    "IDL need resolved by Lawrence acquisition. Remaining priority: CB / S / EDGE depth."
)
# Drop IDL from any needs lists (they just got an All-Pro DT)
cin_needs = cin.get("roster_needs", {})
cin_needs.pop("IDL", None)
cin["roster_needs"] = cin_needs
# Clean any Pick 10 references in other narrative fields
for k in ("roster_needs_tiered", "scheme_identity", "gm_fingerprint",
          "uncertainty_flags", "trade_up_scenario", "cascade_rule"):
    v = cin_narr.get(k)
    if isinstance(v, str) and ("Pick 10" in v or "pick 10" in v):
        cin_narr[k] = v.replace("Pick 10", "(traded pick 10)").replace("pick 10", "(traded pick 10)")

print("[1d] NYG: add IDL hole post-Lawrence exit; pick 10 provenance note")
nyg = agents["NYG"]
nyg_cliffs = nyg.setdefault("roster_context", {}).setdefault("age_cliffs", [])
# Insert a synthetic "hole" marker for Lawrence
nyg_cliffs.insert(0, {
    "player": "Dexter Lawrence (DEPARTED)",
    "position": "IDL",
    "age_2026": 28,
    "threshold": 99,
    "severity": "high",
    "note": "Traded to CIN 2026-04-18 for pick 10; interior DL immediately thinned",
})
# Bump IDL from 2.5 need to acute
nyg_needs = nyg.setdefault("roster_needs", {})
nyg_needs["IDL"] = 4.0
nyg["roster_needs"] = dict(sorted(nyg_needs.items(), key=lambda kv: -kv[1]))
nyg_narr = nyg.setdefault("narrative", {})
pv = nyg_narr.setdefault("pick_provenance", {})
pv["5"] = "NYG native R1 (4-13 record, 2025)"
pv["10"] = "Acquired from CIN (2026-04-18) for Dexter Lawrence + $28M/1yr ext"

# ---- 1e: strip non-team keys (render will also filter; scrubbing here too)
print("[1e] remove pseudo-team keys _league / _meta from team_agents JSON")
for k in list(agents.keys()):
    if k.startswith("_"):
        print(f"        removing '{k}'")
        del agents[k]

# ----------------------------------------------------------------------------
# 3. SOFT FACTUAL / STALENESS
# ----------------------------------------------------------------------------

# ---- 2a: NEW-tag corrections (2025-cycle hires are not NEW for 2026)
print("[2a] NEW-tag normalization: JAX Gladstone/Coen = 2025 (not NEW); "
      "TEN Borgonzi = 2nd year (not NEW); Saleh NEW as HC")
jax = agents["JAX"]
jax["new_gm"] = False  # 2025 hire
jax["new_hc"] = False  # 2025 hire (playoff season 2025)
ten = agents["TEN"]
ten["new_gm"] = False  # 2nd year
# Saleh legitimately new as HC — keep new_hc=True

# ---- 2d: SF Mike Evans acquisition
print("[2d] SF: add Mike Evans age cliff (WR1, 33, acquired 2026)")
sf = agents["SF"]
sf_cliffs = sf.setdefault("roster_context", {}).setdefault("age_cliffs", [])
sf_cliffs.insert(0, {
    "player": "Mike Evans",
    "position": "WR",
    "age_2026": 33,
    "threshold": 30,
    "severity": "medium",
    "note": "Acquired 2026 offseason; now WR1 on a win-now clock",
})
sf_narr = sf.setdefault("narrative", {})
sf_narr_fa = sf_narr.setdefault("fa_moves_struct", {})
arrivals = sf_narr_fa.setdefault("arrivals", [])
if "Mike Evans WR" not in arrivals:
    arrivals.insert(0, "Mike Evans WR")

# ---- 2d: DAL Rashan Gary context
print("[2d] DAL: note Rashan Gary acquisition context")
dal_narr_fa = dal_narr.setdefault("fa_moves_struct", {})
dal_arr = dal_narr_fa.setdefault("arrivals", [])
if not any("Rashan Gary" in x for x in dal_arr):
    dal_arr.insert(0, "Rashan Gary EDGE (from GB, FA)")

# ---- 2e: LAR win% NaN
print("[2e] LAR win_pct: NaN -> 0.882 (15-2, NFC Championship appearance)")
import math
lar = agents["LAR"]
wp = lar.get("win_pct")
if wp is None or (isinstance(wp, float) and math.isnan(wp)):
    lar["win_pct"] = 0.882

# ---- 2c: ATL Kirk Cousins (Tua signed; Cousins traded/released)
print("[2c] ATL: drop Kirk Cousins from age cliffs (no longer on roster per offseason moves)")
atl = agents["ATL"]
atl["roster_context"]["age_cliffs"] = [
    c for c in atl.get("roster_context", {}).get("age_cliffs", [])
    if c.get("player") != "Kirk Cousins"
]

# ---- 2c: Other flagged verifies — conservative removal
print("[2c] NYJ: drop unverified Isaiah Oliver; DAL: drop unverified Dante Fowler Jr.")
nyj = agents["NYJ"]
nyj["roster_context"]["age_cliffs"] = [
    c for c in nyj.get("roster_context", {}).get("age_cliffs", [])
    if c.get("player") != "Isaiah Oliver"
]
dal["roster_context"]["age_cliffs"] = [
    c for c in dal.get("roster_context", {}).get("age_cliffs", [])
    if c.get("player") != "Dante Fowler Jr."
]

# ----------------------------------------------------------------------------
# 4. STRUCTURAL / COMPLETENESS
# ----------------------------------------------------------------------------

# ---- 3a: Pick provenance for teams with two firsts
print("[3a] Two-firsts provenance notes (NYJ/CLE/KC/MIA/DAL)")
PROV = {
    "NYJ": {"2":  "NYJ native R1 (2-15 record, 2025)",
            "16": "Acquired in 2025 Davante Adams / pick swap (package originally from LV)"},
    "CLE": {"6":  "CLE native R1 (3-14 record, 2025)",
            "24": "Acquired from HOU (2024 Deshaun Watson trade residue + 2025 swap)"},
    "KC":  {"9":  "KC native R1 (via 2025 losing season + late-season CB collapse)",
            "29": "KC native R1 (Chiefs' own late pick from 2025 playoff seed)"},
    "MIA": {"11": "MIA native R1 (5-12 record, 2025)",
            "30": "Acquired from SF (2025 Tyreek Hill / 2024 pick-swap residual)"},
    "DAL": {"12": "DAL native R1 (7-10 record, 2025)",
            "20": "Acquired from GB in Micah Parsons trade (Sept 2025)"},
}
for t, prov in PROV.items():
    a = agents[t]
    nar = a.setdefault("narrative", {})
    existing = nar.get("pick_provenance", {})
    existing.update(prov)
    nar["pick_provenance"] = existing

# ---- 3b: GB cliffs thin — add narrative note (do not invent player ages)
gb = agents["GB"]
gb_narr = gb.setdefault("narrative", {})
gb_narr["roster_depth_note"] = (
    "Age-cliff table is sparse by design — GB has one of the youngest rosters in the NFL. "
    "Post-Parsons-trade (sent Micah Parsons + 2026 R1 to DAL for Rashan Gary + picks), "
    "the edge room is thinned; EDGE now a quiet priority."
)

# ---- 3b: JAX Hunter WR/CB usage note
jax_narr = jax.setdefault("narrative", {})
jax_narr["hunter_usage_note"] = (
    "Travis Hunter (2025 #2 overall) split WR/CB usage remains unresolved into 2026. "
    "Shapes positional need board: if Hunter plays majority CB, WR becomes acute; "
    "if majority WR, CB2 opposite Lloyd becomes acute. Coen has signalled 'both'."
)

# ----------------------------------------------------------------------------
# 5. Write-outs
# ----------------------------------------------------------------------------
agents["_meta_corrections"] = {
    "applied_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "fixes": [
        "DAL HC: McCarthy->Schottenheimer", "PIT HC: Tomlin->McCarthy",
        "IND: scrub Rivers/Howard/Abdullah + bump QB urgency",
        "CIN: scrub pick 10 archetype post-Lawrence trade",
        "NYG: add IDL hole + pick 10 provenance",
        "LAR: win_pct NaN -> 0.882",
        "JAX/TEN: NEW flags corrected to 2025-cycle",
        "SF: add Mike Evans cliff", "DAL: add Rashan Gary FA arrival",
        "PIT: Rodgers age 43->42, drop unverified Ramsey",
        "Pick provenance notes for NYJ/CLE/KC/MIA/DAL",
        "GB/JAX narrative notes",
        "Removed _league / _meta pseudo-team keys",
    ],
}

save(AGENTS_P, agents)
# Only write narrative file if it lives in a consumed spot — the source-of-truth
# for the sim is team_agents_2026.json, so we don't need to mirror-patch
# the upstream narrative JSON unless build_team_agents.py is re-run.
print("\nDONE.")
