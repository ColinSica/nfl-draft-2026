"""
SECTION A — apply verified Excel deltas from the 2026-04-19 8:41 PM PT refresh.

Scope:
- NO: QB locked (Shough confirmed starter, Carr retired), urgency 0.7 -> 0.0
- HOU: Will Anderson 3yr/$150M ext 4/17 — EDGE removed from scheme premium
       (already absent from needs; consistent)
- TEN: Saleh defensive HC — EDGE bumped ahead of OT in needs (3.0 -> 3.75,
       OT 3.5 -> 3.0); scheme labeled 4-3 wide-9
- NYG: need ordering per Excel (LB first, IDL second w/ FA-fill caveat).
       Drop IDL 4.0 -> 3.0 and raise LB 1.5 -> 3.5 so Harbaugh-spine logic
       dominates; add narrative note that IDL likely addressed in FA.
       Fill cap context $18.4M post-trade.
- DAL: add DC Matt Eberflus (Tampa-2 / wide-9) to narrative
- NYJ: per Excel QB is paid/set — drop qb_urgency 0.3 -> 0.0; also drop
       stale QB 1.5 from needs (Excel lists EDGE/WR/C-G/S)
- CLE: needs has QB 3.5 but urgency 0.0 — internally inconsistent.
       Watson is cap-locked so urgency stays modest but raise 0.0 -> 0.35.
- Pick provenance corrections: #16 (Sauce Gardner era), #24 (Trevor Lawrence),
  #30 (Ramsey/Chubb era)
- NYG Schoen "two top-10 picks twice in 5 yrs" narrative fact added
- Flag NYG gm_affinity IDL = -0.15 (Harbaugh structurally avoids R1 DT)
  against current IDL top-need — document the tension rather than auto-fix

Does NOT touch:
- ARI HC (user confirmed LaFleur; Excel stale)
- PIT HC (user confirmed McCarthy; Excel stale)
- SF Mike Evans (Excel silent; keep as-is pending user confirmation)
"""
import json, shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
AGENTS_P = ROOT / "data/features/team_agents_2026.json"

def load(p): return json.loads(p.read_text(encoding="utf-8"))
def save(p, obj):
    bak = p.with_suffix(".section_a_bak.json")
    if p.exists() and not bak.exists():
        shutil.copy2(p, bak)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

agents = load(AGENTS_P)
contradictions_found = []

# -------- NO QB --------
no = agents["NO"]
old_urg = no.get("qb_urgency")
if old_urg and old_urg > 0:
    contradictions_found.append(
        f"NO qb_urgency was {old_urg} but needs list had no QB entry and "
        "Excel confirms Shough is committed starter — internally inconsistent."
    )
no["qb_urgency"] = 0.0
no["qb_situation"] = "locked"
no_narr = no.setdefault("narrative", {})
no_narr["qb_situation"] = (
    "LOCKED. Tyler Shough (2025 R2) started 9 games, Pepsi ORoY / AP ORoY finalist, "
    "67.6% / 2384 yds / 10 TD. Carr retired April 2025. Loomis & Moore publicly "
    "committed to Shough as starter (Jan 2026)."
)

# -------- HOU EDGE --------
hou = agents["HOU"]
hou_sch = hou.setdefault("scheme", {})
premium = hou_sch.get("premium", [])
if "EDGE" in premium:
    premium.remove("EDGE")
    hou_sch["premium"] = premium
hou_narr = hou.setdefault("narrative", {})
hou_narr["context_2026"] = (
    "Will Anderson Jr. signed 3-yr/$150M extension (4/17/26) — "
    "highest-paid non-QB contract in NFL history ($134M gtd, through 2030). "
    "Combined with Danielle Hunter 1-yr/$40M, EDGE is fully addressed. "
    "Texans now cap-tight after WR/DE/CB deals."
)
# Confirm EDGE is not in needs
if "EDGE" in hou.get("roster_needs", {}):
    hou["roster_needs"].pop("EDGE")
    contradictions_found.append("HOU had EDGE in needs but $150M Anderson ext makes it non-need — removed.")

# -------- TEN Saleh defense --------
ten = agents["TEN"]
ten_needs = ten.setdefault("roster_needs", {})
# Bump EDGE above OT
ten_needs["EDGE"] = 3.75  # was 3.0
ten_needs["OT"] = 3.0    # was 3.5 (Saleh priority #1 is EDGE, not OT)
ten["roster_needs"] = dict(sorted(ten_needs.items(), key=lambda kv: -kv[1]))
ten_sch = ten.setdefault("scheme", {})
ten_sch["type"] = "saleh_4-3_wide-9"
ten_narr = ten.setdefault("narrative", {})
ten_narr["scheme_identity"] = (
    "Saleh runs aggressive 4-3 wide-9 (SF/Seattle Cover-3 tree). "
    "Top-10 defense 5x as DC. Priority: explosive EDGE + length on D-line. "
    "Drafted Jermaine Johnson (EDGE) #1 as NYJ HC in 2022 — pattern predicts "
    "EDGE at #4 if Bailey/Reese falls."
)

# -------- NYG Harbaugh-spine restructure --------
nyg = agents["NYG"]
nyg_needs = nyg.setdefault("roster_needs", {})
# Prior state: IDL 4.0, WR 3.5, OT 3.0, S 2.5, CB 2.5, LB 1.5
# Excel ordering: 1.LB (spine) 2.DT (FA-fill) 3.S 4.WR2 5.OT/G
nyg_needs["LB"] = 3.75   # was 1.5 — Harbaugh spine = top priority
nyg_needs["IDL"] = 3.0    # was 4.0 — real but expected FA fill
nyg_needs["S"] = 3.25     # was 2.5 — Ravens-style cover S
nyg_needs["WR"] = 3.0     # was 3.5 — Nabers complement, still real
nyg_needs["OT"] = 2.75    # was 3.0 — Dart protection, handled in FA partially
nyg_needs["CB"] = 2.25    # was 2.5
nyg["roster_needs"] = dict(sorted(nyg_needs.items(), key=lambda kv: -kv[1]))
nyg_cc = nyg.setdefault("cap_context", {})
nyg_cc["cap_space_m"] = 18.4
nyg_cc["constraint_tier"] = "flush"
nyg_cc["notes"] = (
    "Post-Lawrence trade: +$12.8M recovered ($18.5M base − $5.7M pick-10 cap hit). "
    "OverTheCap shows $18.4M as of 4/19 AM ET. Likely pursues DT FA "
    "(Reader / Harris / Campbell) before or after draft."
)
nyg_narr = nyg.setdefault("narrative", {})
nyg_narr["schoen_factoid"] = (
    "Schoen is only modern-era GM with TWO top-10 picks TWICE in 5 years."
)
nyg_narr["harbaugh_r1_dt_note"] = (
    "Harbaugh NEVER drafted a DT in Round 1 in 18 seasons at BAL. "
    "Suggests NYG will fill Lawrence's IDL hole via FA (Reader/Harris/Campbell) "
    "+ Day 2 (e.g. Kayden McDonald) rather than at #5 or #10."
)
contradictions_found.append(
    "NYG structural tension: roster_needs has IDL as top need (post-Lawrence void) "
    "BUT gm_affinity shows IDL -0.15 AND Harbaugh's 18-yr BAL record shows zero "
    "Rd1 DT selections. Net: model's IDL weighting will be self-dampened by "
    "affinity. Kept elevated to reflect real roster gap; Harbaugh-spine LB "
    "(Styles) is the more likely R1 outcome."
)

# -------- DAL DC Eberflus --------
dal = agents["DAL"]
dal_narr = dal.setdefault("narrative", {})
dal_narr["defense_identity"] = (
    "DC Matt Eberflus (hired 2026 after CHI firing). Tampa-2 influence + wide-9 "
    "fronts. DAL needs LB/CB/DL to fit Eberflus's aggressive front-seven."
)

# -------- NYJ QB fix --------
nyj = agents["NYJ"]
old_nyj_urg = nyj.get("qb_urgency")
nyj["qb_urgency"] = 0.0
nyj["qb_situation"] = "locked"
if "QB" in nyj.get("roster_needs", {}):
    nyj["roster_needs"].pop("QB")
    contradictions_found.append(
        f"NYJ had qb_urgency={old_nyj_urg} + QB 1.5 in needs, but Excel confirms "
        "QB is paid/set (Rodgers era + Glenn plan). Both cleared."
    )
nyj_narr = nyj.setdefault("narrative", {})
nyj_narr["qb_situation"] = (
    "LOCKED. Glenn offense under OC Engstrand. QB plan is set heading into 2026."
)

# -------- CLE QB consistency --------
cle = agents["CLE"]
old_cle_urg = cle.get("qb_urgency")
if (cle.get("roster_needs", {}).get("QB", 0) >= 3.0 and old_cle_urg == 0.0):
    contradictions_found.append(
        f"CLE had QB=3.5 in needs but qb_urgency=0.0. Watson is cap-dead but "
        "contractually tied; a QB taken at #6 is a live scenario (Allar). "
        "Raising urgency to 0.35 to reflect the real QB question."
    )
cle["qb_urgency"] = 0.35
cle["qb_situation"] = "watson_locked_ceiling_uncertain"
cle_narr = cle.setdefault("narrative", {})
cle_narr["qb_situation"] = (
    "Watson contract is cap-dead weight; starter long-term unsettled. "
    "Drew Allar at #6 is a real scenario per analyst mocks. "
    "Urgency is moderate — not 1.0 because Watson's cap hit blocks a clean reset."
)

# -------- Pick provenance corrections --------
PROV_FIX = {
    "NYJ": {"16": "Acquired from IND (Sauce Gardner-era deal)"},
    "CLE": {"24": "Acquired from JAX (Trevor Lawrence-era deal)"},
    "MIA": {"30": "Acquired from DEN (Jalen Ramsey / Bradley Chubb-era deal)"},
    "KC":  {"29": "Acquired from LAR (Matthew Stafford-era deal)"},
}
for t, prov in PROV_FIX.items():
    nar = agents[t].setdefault("narrative", {})
    p = nar.setdefault("pick_provenance", {})
    p.update(prov)

# -------- Metadata --------
agents["_meta_section_a"] = {
    "applied_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    "source": "2026 Mock Draft Data.xlsx refresh 2026-04-19 8:41 PM PT",
    "excel_stale_on": [
        "ARI HC (listed Gannon; actually LaFleur per user)",
        "PIT HC (listed Tomlin; actually McCarthy per user)",
    ],
    "contradictions_resolved": contradictions_found,
}

save(AGENTS_P, agents)
print(f"Patched {AGENTS_P}")
print(f"\nContradictions surfaced:")
for i, c in enumerate(contradictions_found, 1):
    print(f"  {i}. {c}")
