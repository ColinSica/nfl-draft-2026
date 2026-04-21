"""Apply fixes verified via web research on 2026-04-20 (pre-draft, T-3).

Sources (see conversation log):
  - Wikipedia 'List of current NFL head coaches' (verified HC roster)
  - NFL.com, ESPN, CBS Sports, Falcons/Colts official sites
  - Texans/Will Anderson, Saints/Shough, Falcons/Stefanski, Cowboys/Parker,
    Colts/Jones, Dolphins/Tua cap hit, Evans-SF, Gary-DAL

Scope of this patch:
  1. ATL: Terry Fontenot -> Ian Cunningham GM; Raheem Morris -> Kevin
     Stefanski HC (both NEW for 2026 cycle). Add Penix ACL injury flag
     (Nov 2025, targeting Week 1). Note Tua $1.3M min acquisition.
  2. DAL: DC Eberflus was fired Jan 2026; new DC is Christian Parker.
     Eberflus took 49ers asst-HC role. Our earlier narrative had this
     wrong.
  3. IND: Jones re-ruptured Achilles but signed 2yr/$88M, expects Week 1
     return. Lower qb_urgency 0.65 -> 0.30. Richardson trade market
     'soft', may stay. Leonard is 6th-round backup. IND unlikely to
     chase a R1 QB.
  4. MIA: $100M dead-cap hit from Tua release — cap is tighter than our
     current tier suggests.
  5. HOU: Anderson 3yr/$150M ext confirmed 4/17; already patched in A,
     but re-affirm.
  6. TEN: confirm Bailey (Texas Tech) visit; Saleh quotes EDGE as
     playmaker equivalent to Love.
  7. NYG: already patched for Lawrence trade (Section A); re-affirm
     Schoen retained and cap +$12.8M.
  8. Add 'preferences_sources' note to each edited team pointing at the
     research date.
"""
import json, shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
AGENTS_P = ROOT / "data/features/team_agents_2026.json"

def load(p): return json.loads(p.read_text(encoding="utf-8"))
def save(p, obj):
    bak = p.with_suffix(".pre_research_bak.json")
    if p.exists() and not bak.exists():
        shutil.copy2(p, bak)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

agents = load(AGENTS_P)
fixes = []

# ---- 1. ATL ----
atl = agents["ATL"]
atl["gm"] = "Ian Cunningham"
atl["hc"] = "Kevin Stefanski"
atl["new_gm"] = True
atl["new_hc"] = True
if "coaching" in atl:
    atl["coaching"]["hc"] = "Kevin Stefanski"
    atl["coaching"]["hc_tree"] = "shanahan_kubiak"  # Stefanski lineage
atl_cliffs = atl.setdefault("roster_context", {}).setdefault("age_cliffs", [])
# Add Penix injury flag as a 'cliff' entry so the medical system sees it
if not any(c.get("player") == "Michael Penix Jr. (ACL)" for c in atl_cliffs):
    atl_cliffs.insert(0, {
        "player": "Michael Penix Jr. (ACL)",
        "position": "QB",
        "age_2026": 26,
        "threshold": 99,
        "severity": "high",
        "note": "Torn ACL Week 11 of 2025. Targeting Week 1 2026 return. "
                "Tua signed at $1.3M veteran min as competition/insurance.",
    })
atl_narr = atl.setdefault("narrative", {})
atl_narr["leadership"] = ("GM Ian Cunningham (NEW — from CHI asst GM, hired 2026) | "
                         "HC Kevin Stefanski (NEW — from CLE, hired 2026-01-17) | "
                         "OC Tommy Rees (NEW) | OL coach Bill Callahan (NEW) | "
                         "DC Jeff Ulbrich (retained)")
atl_narr["context_2026"] = (
    "Full regime change: Morris and Fontenot out, Stefanski-Cunningham in. "
    "Penix ACL (Nov 2025) forced Tua $1.3M vet min signing as competition. "
    "Cousins released at start of league year. QB hierarchy TBD. "
    "Priority needs: WR speed, OL depth, secondary."
)
atl_narr["qb_situation"] = (
    "COMPETITION. Penix (ACL, Week 1 TBD) + Tua ($1.3M min) compete. "
    "No R1 QB on roster pre-draft."
)
atl["qb_situation"] = "competition_with_medical_risk"
atl["qb_urgency"] = 0.25
fixes.append("ATL: HC Morris->Stefanski, GM Fontenot->Cunningham, Penix ACL flag, Tua acquisition")

# ---- 2. DAL DC ----
dal = agents["DAL"]
dal_narr = dal.setdefault("narrative", {})
# Overwrite the Eberflus mention from Section A; correct DC is Christian Parker
dal_narr["defense_identity"] = (
    "DC Christian Parker (NEW 2026 — from PHI) after Eberflus was fired "
    "Jan 2026 (his unit finished 30th in yards, 32nd in points allowed). "
    "Eberflus took 49ers asst-HC job. Parker brings Fangio-influenced shell."
)
dal_narr["leadership"] = ("GM Jerry Jones (de facto) | HC Brian Schottenheimer "
                         "(2nd year) | OC Klayton Adams | "
                         "DC Christian Parker (NEW 2026)")
fixes.append("DAL: DC Eberflus->Christian Parker; note Eberflus went to SF as asst HC")

# ---- 3. IND ----
ind = agents["IND"]
ind["qb_urgency"] = 0.30  # was 0.65 (Section A was too high)
ind["qb_situation"] = "jones_starter_recovering"
# Correct/trim needs — QB shouldn't be top
ind_needs = ind.get("roster_needs", {})
ind_needs["QB"] = 1.5  # was 3.5 — Jones expected back Week 1
ind["roster_needs"] = dict(sorted(ind_needs.items(), key=lambda kv: -kv[1]))
ind_narr = ind.setdefault("narrative", {})
ind_narr["qb_situation"] = (
    "Daniel Jones signed 2yr/$88M after career year pre-Achilles (3101 yds / "
    "8.1 YPA / 68% / 63.5 QBR in 13 games). Re-ruptured Achilles during rehab "
    "(rare), but expects to be Week 1 2026 ready. Richardson granted "
    "permission to seek trade — 'soft' market, may stay. Leonard is 6th-round "
    "rookie. IND hosted visits with Altmyer, Payton, Nussmeier, Morton, King "
    "(Day 2/3 QB depth options — not R1 targets)."
)
# Scrub the earlier aggressive QB need messaging
ind_narr["qb_urgency_note"] = (
    "qb_urgency lowered to 0.30 after research: Jones is $88M starter, "
    "Richardson staying is live scenario. This is NOT a R1 QB team."
)
fixes.append("IND: qb_urgency 0.65->0.30 (Jones expected Week 1), QB need 3.5->1.5")

# ---- 4. MIA cap ----
mia = agents["MIA"]
mia_cap = mia.setdefault("cap_context", {})
mia_cap["dead_cap_m"] = 100.0  # record Tua release
mia_cap["constraint_tier"] = "severely_tight"
mia_cap["notes"] = (
    "Record $100M dead-cap hit from Tua release. GM Jon-Eric Sullivan "
    "(NEW 2026, from GB). Rebuild mode with cap constraints."
)
fixes.append("MIA: dead_cap_m None->$100M (record Tua release hit)")

# ---- 5. TEN visits confirmation ----
ten = agents["TEN"]
ten_vs = ten.setdefault("visit_signals", {}).setdefault("confirmed_visits", [])
if "David Bailey" not in ten_vs:
    ten_vs.append("David Bailey")
ten_narr = ten.setdefault("narrative", {})
ten_narr["saleh_philosophy_2026"] = (
    "Saleh at NFL meetings: 'Edge rushers are playmakers too... when "
    "you're drafting that high, it's: who can change the game in one play? "
    "And edge rushers can change the game in one play.' Titans hosted "
    "David Bailey (TTU, 14.5 FCS-leading sacks) — confirms EDGE is "
    "alive alongside Love (RB) at #4."
)
fixes.append("TEN: added David Bailey visit, Saleh EDGE-as-playmaker quote")

# ---- 6. Meta ----
agents["_meta_research"] = {
    "applied_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    "research_date": "2026-04-20",
    "sources_consulted": [
        "en.wikipedia.org/wiki/List_of_current_NFL_head_coaches",
        "nfl.com (Stefanski hire, Penix ACL, Tua comp, Saleh quote, Wilson-Anderson, Shough)",
        "espn.com (Jones recovery, Tyson workout, Dexter Lawrence trade)",
        "cbssports.com (Lawrence trade grades, Tyson injury)",
        "dallascowboys.com (Eberflus fired, Christian Parker hired)",
        "colts.com (Jones Week 1 timeline, Richardson trade market)",
        "azcardinals.com (LaFleur hire date, Gannon fired 1/5/26)",
        "steelers.com (McCarthy hired 1/27/26, Tomlin stepped down)",
        "atlantafalcons.com (Stefanski + Cunningham + staff)",
    ],
    "fixes_applied": fixes,
    "verified_roster_ATL_GM": "Ian Cunningham (prev: Terry Fontenot)",
    "verified_roster_ATL_HC": "Kevin Stefanski (prev: Raheem Morris)",
    "verified_roster_PIT_HC": "Mike McCarthy (confirmed, Tomlin stepped down Jan 2026)",
    "verified_roster_ARI_HC": "Mike LaFleur (confirmed, Gannon fired 1/5/26)",
    "verified_DAL_DC": "Christian Parker (NEW 2026 from PHI)",
    "verified_IND_QB_plan": "Jones Week 1 recovery; Richardson soft market",
    "verified_MIA_cap": "$100M record dead cap from Tua release",
    "verified_ATL_QB": "Penix ACL Nov 2025 + Tua $1.3M min competition",
}

save(AGENTS_P, agents)
print(f"Patched {AGENTS_P}")
print(f"\n{len(fixes)} fixes applied:")
for i, f in enumerate(fixes, 1):
    print(f"  {i}. {f}")
