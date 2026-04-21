"""Wire analyst REASONING into the model (not picks).

Analysts say WHY each team should/would take certain types of players.
We encode those WHYs as structured preferences over archetypes + traits,
then let the model score each prospect against them. The model arrives
at similar picks naturally — because the reasoning pushes it there, not
because we fed it the pick outcome.

Distinction:
  BANNED: "Analyst X projects Love to ARI at #3"
  OK:     "ARI scheme is McVay wide-zone → values pass-catching RB
           archetype + movement OT". Converting this into structured
           signals so model scores Love-archetype (pass_catching_back
           + home_run_hitter) highly for ARI via scheme-fit weights.

Sources (all scheme/trait reasoning, not pick predictions):
  - nfl.com/news/2026-nfl-draft-order-round-1-needs-for-all-32-teams
  - nfl.com/news/nfl-iq-trade-trends-and-projected-moves-for-2026-nfl-draft
  - espn.com/nfl/draft2026/story/_/id/48494162 (Solak per-team needs/fit)
  - Per-team coaching-scheme docs
"""
import json, shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
AGENTS_P = ROOT / "data/features/team_agents_2026.json"
ARCH_PROS_P = ROOT / "data/features/prospect_archetypes_2026.json"
ARCH_TEAM_P = ROOT / "data/features/team_archetype_preferences_2026.json"

def load(p): return json.loads(p.read_text(encoding="utf-8"))
def save(p, obj):
    bak = p.with_suffix(".reasoning_bak.json")
    if p.exists() and not bak.exists(): shutil.copy2(p, bak)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

# ----------------------------------------------------------------------------
# 1. REASONING-DRIVEN team archetype/trait preferences
#    Encoded from analyst REASONING (scheme fit, coach-system preferences,
#    roster context), not from pick predictions. Each weight ∈ [0, 1].
# ----------------------------------------------------------------------------
REASONING_FITS = {
    "LV": {
        # Kubiak McVay-tree offense. Brady mentor for Mendoza (WCO polish).
        # Protect the rookie QB → movement-tackle pass-pro + YAC weapons.
        # Defense: IDL + secondary holes per analyst reasoning.
        "archetypes": {
            "movement_tackle": 0.9, "YAC_slot": 0.8, "vertical_stretcher": 0.7,
            "run_stuffing_IDL": 0.8, "penetrating_IDL": 0.7,
            "press_corner": 0.5, "zone_corner": 0.5,
            "pass_catching_back": 0.5, "X_receiver": 0.6,
        },
        "traits": {"pass_protection": 0.9, "separation": 0.8},
    },
    "NYJ": {
        # Glenn 3-4 "long athletic EDGE" explicit preference.
        "archetypes": {
            "standup_EDGE": 0.95, "athletic_rusher": 0.95,
            "X_receiver": 0.7, "vertical_stretcher": 0.6,
            "press_corner": 0.7,
        },
        "traits": {"length": 0.9, "burst": 0.85},
    },
    "ARI": {
        # LaFleur McVay-tree. Protect Kyler (RT). Disrupt QB (pass rush).
        # Ossenfort has RB affinity per fingerprint.
        "archetypes": {
            "power_tackle": 0.8, "movement_tackle": 0.7,
            "athletic_rusher": 0.85, "penetrating_IDL": 0.7,
            "power_back": 0.7, "home_run_hitter": 0.7, "pass_catching_back": 0.6,
            "vertical_stretcher": 0.6, "YAC_slot": 0.6,
        },
        "traits": {"pass_rush_burst": 0.9, "pass_protection": 0.75},
    },
    "TEN": {
        # Saleh 4-3 wide-9 defense — EXPLICIT long bendy EDGE preference.
        # Borgonzi cited "explosive weaponry" for Ward (WR speed).
        # IOL upgrade (C/RG).
        "archetypes": {
            "standup_EDGE": 0.9, "athletic_rusher": 0.9,
            "vertical_stretcher": 0.8, "YAC_slot": 0.7,
            "athletic_interior": 0.7, "interior_OL": 0.6,
            "pass_catching_back": 0.7, "home_run_hitter": 0.7,
            "zone_corner": 0.6, "split_safety": 0.5,
        },
        "traits": {"length": 0.85, "explosiveness": 0.85},
    },
    "NYG": {
        # Harbaugh spine = LB + S + RB + interior. NGS score 95 for Styles.
        # League-worst 5.3 YPC allowed → run-stopping IDL priority.
        "archetypes": {
            "run_stuffing_IDL": 0.95, "penetrating_IDL": 0.6,
            "coverage_LB": 0.9, "downhill_LB": 0.85,
            "ball_hawk_S": 0.75, "box_safety": 0.7, "split_safety": 0.6,
            "power_tackle": 0.7, "interior_OL": 0.7,
            "X_receiver": 0.6,
        },
        "traits": {"physicality": 0.9, "run_defense": 0.85},
    },
    "CLE": {
        # Monken WCO. Schwartz 4-3 wide-9. QB long-term question.
        # Berry trade-back propensity.
        "archetypes": {
            "accurate_QB": 0.7, "pocket_QB": 0.6,
            "movement_tackle": 0.85, "power_tackle": 0.7,
            "X_receiver": 0.8, "vertical_stretcher": 0.75,
            "athletic_rusher": 0.7, "press_corner": 0.6,
        },
        "traits": {"pass_protection": 0.85, "separation": 0.8},
    },
    "WAS": {
        # Quinn cover-3. Kingsbury Air-Raid-lite for Daniels.
        # Speed WR2 priority, athletic EDGE.
        "archetypes": {
            "slot_separator": 0.85, "vertical_stretcher": 0.8, "YAC_slot": 0.75,
            "athletic_rusher": 0.85, "standup_EDGE": 0.7,
            "coverage_LB": 0.7, "split_safety": 0.6,
        },
        "traits": {"speed": 0.9, "separation": 0.85},
    },
    "NO": {
        # Kellen Moore Air-Coryell + Shanahan-zone runs.
        # Staley defense shell coverage.
        "archetypes": {
            "X_receiver": 0.85, "vertical_stretcher": 0.85,
            "athletic_rusher": 0.85, "standup_EDGE": 0.7,
            "press_corner": 0.7, "zone_corner": 0.5,
            "run_stuffing_IDL": 0.65,
        },
        "traits": {"vertical_speed": 0.85, "pass_rush_burst": 0.8},
    },
    "KC": {
        # Spagnuolo blitzes + press-man CB (explicit analyst point).
        # Reid WCO RPO-heavy, speed WR.
        "archetypes": {
            "press_corner": 0.95, "man_corner": 0.9,
            "slot_separator": 0.85, "vertical_stretcher": 0.85, "YAC_slot": 0.8,
            "penetrating_IDL": 0.75, "athletic_rusher": 0.7,
        },
        "traits": {"press_coverage": 0.95, "separation": 0.85},
    },
    "MIA": {
        # McDaniel Shanahan wide-zone. Hafley defense — aggressive 4-3 hybrid.
        "archetypes": {
            "movement_tackle": 0.85, "X_receiver": 0.75, "YAC_slot": 0.7,
            "press_corner": 0.75, "athletic_rusher": 0.75, "standup_EDGE": 0.7,
            "split_safety": 0.65,
        },
        "traits": {"pass_protection": 0.8, "athleticism": 0.75},
    },
    "DAL": {
        # Schottenheimer pro-style. Eberflus wide-9 → Christian Parker hybrid.
        "archetypes": {
            "athletic_rusher": 0.95, "standup_EDGE": 0.85, "hand_in_dirt_EDGE": 0.8,
            "downhill_LB": 0.85, "coverage_LB": 0.8,
            "press_corner": 0.75,
            "power_tackle": 0.7,
        },
        "traits": {"pass_rush_burst": 0.95, "physicality": 0.8},
    },
    "LAR": {
        # McVay wide-zone. Shula Fangio 3-4. Post-McDuffie acquisition.
        "archetypes": {
            "vertical_stretcher": 0.85, "YAC_slot": 0.8, "X_receiver": 0.7,
            "movement_tackle": 0.85,
            "coverage_LB": 0.7, "split_safety": 0.7,
            "athletic_rusher": 0.65,
        },
        "traits": {"separation": 0.85, "pass_protection": 0.8},
    },
    "BAL": {
        # New HC Minter (ex-LAC DC). Aggressive 3-4.
        # Lost Likely/Kolar → TE need explicit.
        "archetypes": {
            "power_tackle": 0.85, "movement_tackle": 0.7,
            "athletic_rusher": 0.85, "standup_EDGE": 0.75,
            "X_receiver": 0.7, "inline_TE": 0.8, "move_TE": 0.75,
            "run_stuffing_IDL": 0.7,
        },
        "traits": {"power": 0.85, "length": 0.8},
    },
    "TB": {
        # Bowles amoeba/blitz. Need EDGE + CB + LB post-Barrett.
        "archetypes": {
            "athletic_rusher": 0.9, "standup_EDGE": 0.85,
            "press_corner": 0.8, "zone_corner": 0.6,
            "coverage_LB": 0.8,
            "vertical_stretcher": 0.7,
        },
        "traits": {"pass_rush_burst": 0.9, "coverage_range": 0.8},
    },
    "DET": {
        # Campbell aggressive. Morton OC. Sheppard DC (from Glenn's shop).
        "archetypes": {
            "power_tackle": 0.85, "movement_tackle": 0.7,
            "athletic_rusher": 0.8, "hand_in_dirt_EDGE": 0.75,
            "ball_hawk_S": 0.7,
        },
        "traits": {"physicality": 0.85, "power": 0.8},
    },
    "MIN": {
        # Flores amoeba blitzer — LOVES penetrating DL. O'Connell McVay.
        # Post-Kelly C need. Flores safety fit.
        "archetypes": {
            "penetrating_IDL": 0.9, "run_stuffing_IDL": 0.8,
            "interior_OL": 0.85, "athletic_interior": 0.8,
            "ball_hawk_S": 0.8, "split_safety": 0.7,
            "vertical_stretcher": 0.65,
        },
        "traits": {"pass_rush_burst": 0.85, "physicality": 0.75},
    },
    "CAR": {
        # Canales Shanahan-tree OC → Bryce Young weapons.
        # Evero Fangio 3-4 shell.
        "archetypes": {
            "vertical_stretcher": 0.85, "YAC_slot": 0.8, "X_receiver": 0.7,
            "movement_tackle": 0.85,
            "split_safety": 0.7, "ball_hawk_S": 0.7,
            "inline_TE": 0.65,
        },
        "traits": {"separation": 0.85, "pass_protection": 0.8},
    },
    "PIT": {
        # McCarthy WCO. Broderick Jones neck injury bump OT urgency.
        # Metcalf + Pittman → speed YAC WR complement.
        "archetypes": {
            "movement_tackle": 0.9, "power_tackle": 0.8,
            "YAC_slot": 0.85, "slot_separator": 0.8,
            "accurate_QB": 0.7,
            "run_stuffing_IDL": 0.7,
        },
        "traits": {"pass_protection": 0.9, "YAC_ability": 0.85},
    },
    "LAC": {
        # Harbaugh power-run + Minter 3-4. Herbert protection.
        "archetypes": {
            "power_tackle": 0.9, "movement_tackle": 0.7,
            "athletic_rusher": 0.85, "hand_in_dirt_EDGE": 0.8,
            "penetrating_IDL": 0.8,
            "X_receiver": 0.7, "vertical_stretcher": 0.7,
        },
        "traits": {"power": 0.9, "pass_protection": 0.9},
    },
    "PHI": {
        # Sirianni/Fangio — light boxes, two-high. Roseman loves value.
        "archetypes": {
            "athletic_rusher": 0.9, "hand_in_dirt_EDGE": 0.8,
            "power_tackle": 0.85, "movement_tackle": 0.7,
            "split_safety": 0.85, "ball_hawk_S": 0.75,
            "zone_corner": 0.7,
        },
        "traits": {"pass_rush_burst": 0.9, "coverage_range": 0.8},
    },
    "CHI": {
        # Ben Johnson LOVES athletic ILBs. Allen Fangio-tree DC.
        "archetypes": {
            "split_safety": 0.9, "ball_hawk_S": 0.85,
            "power_tackle": 0.85, "movement_tackle": 0.7,
            "penetrating_IDL": 0.8,
            "athletic_rusher": 0.7,
        },
        "traits": {"coverage_range": 0.9, "pass_rush_burst": 0.75},
    },
    "BUF": {
        # McDermott Tampa-2 hybrid. Brady WCO. Post-Diggs WR need.
        "archetypes": {
            "athletic_rusher": 0.9, "standup_EDGE": 0.8,
            "coverage_LB": 0.85, "downhill_LB": 0.75,
            "split_safety": 0.75, "press_corner": 0.75,
            "X_receiver": 0.7,
        },
        "traits": {"pass_rush_burst": 0.85, "coverage_range": 0.8},
    },
    "SF": {
        # Shanahan wide-zone — elite OL athleticism critical.
        # Morris hybrid 4-3, Bosa + EDGE priority.
        "archetypes": {
            "movement_tackle": 0.95, "athletic_interior": 0.85,
            "athletic_rusher": 0.9, "standup_EDGE": 0.85,
            "YAC_slot": 0.8, "vertical_stretcher": 0.75,
            "penetrating_IDL": 0.7,
        },
        "traits": {"athleticism": 0.95, "pass_protection": 0.9},
    },
    "HOU": {
        # Ryans SF-tree wide-9. Caley WCO. Post-Anderson ext → OL + DL focus.
        "archetypes": {
            "movement_tackle": 0.9, "power_tackle": 0.8,
            "athletic_interior": 0.8,
            "penetrating_IDL": 0.8, "run_stuffing_IDL": 0.75,
            "coverage_LB": 0.75,
        },
        "traits": {"pass_protection": 0.9, "athleticism": 0.85},
    },
    "NE": {
        # Vrabel physical defense. McDaniels WCO.
        "archetypes": {
            "athletic_rusher": 0.9, "hand_in_dirt_EDGE": 0.85,
            "power_tackle": 0.9, "athletic_interior": 0.75,
            "press_corner": 0.8, "box_safety": 0.75,
        },
        "traits": {"physicality": 0.9, "pass_rush_burst": 0.85},
    },
    "SEA": {
        # Macdonald Ravens-tree 3-4. Post-Walker RB need.
        "archetypes": {
            "power_back": 0.85, "home_run_hitter": 0.8,
            "power_tackle": 0.85, "athletic_interior": 0.75,
            "press_corner": 0.8, "ball_hawk_S": 0.75,
            "penetrating_IDL": 0.7,
        },
        "traits": {"physicality": 0.85, "explosiveness": 0.8},
    },
    "ATL": {
        # Stefanski WCO (ex-CLE). Penix ACL → Tua/Penix competition.
        "archetypes": {
            "X_receiver": 0.85, "vertical_stretcher": 0.8,
            "movement_tackle": 0.85, "power_tackle": 0.7,
            "penetrating_IDL": 0.75,
            "press_corner": 0.7,
        },
        "traits": {"separation": 0.85, "pass_protection": 0.8},
    },
    "CIN": {
        # Taylor WCO. Golden new DC from ND — aggressive blitz.
        # Post-Lawrence IDL need reduced.
        "archetypes": {
            "coverage_LB": 0.85, "downhill_LB": 0.7,
            "press_corner": 0.8, "zone_corner": 0.6,
            "athletic_rusher": 0.75,
            "split_safety": 0.7,
        },
        "traits": {"coverage_range": 0.85, "pass_rush_burst": 0.75},
    },
    "DEN": {
        # Payton pass game. Joseph aggressive blitz D.
        # No R1 pick (Waddle trade).
        "archetypes": {
            "athletic_rusher": 0.85, "penetrating_IDL": 0.75,
            "inline_TE": 0.8, "move_TE": 0.7,
            "press_corner": 0.7,
        },
        "traits": {"pass_rush_burst": 0.85, "physicality": 0.75},
    },
    "GB": {
        # Matt LaFleur Shanahan-zone. Gannon new DC (ex-ARI HC).
        # Post-Gary trade → EDGE need.
        "archetypes": {
            "athletic_rusher": 0.9, "standup_EDGE": 0.85,
            "movement_tackle": 0.85, "athletic_interior": 0.8,
            "press_corner": 0.75, "zone_corner": 0.7,
        },
        "traits": {"pass_rush_burst": 0.9, "athleticism": 0.85},
    },
    "IND": {
        # Steichen WCO. Anarumo new DC (aggressive blitz, ex-CIN).
        "archetypes": {
            "athletic_rusher": 0.9, "standup_EDGE": 0.8,
            "coverage_LB": 0.85, "downhill_LB": 0.75,
            "split_safety": 0.75,
        },
        "traits": {"pass_rush_burst": 0.85, "coverage_range": 0.8},
    },
    "JAX": {
        # Coen WCO. Campanile DC (aggressive).
        # Post-Hunter uncertainty on usage.
        "archetypes": {
            "coverage_LB": 0.85, "downhill_LB": 0.8,
            "athletic_rusher": 0.8, "penetrating_IDL": 0.75,
            "split_safety": 0.7,
        },
        "traits": {"coverage_range": 0.85, "pass_rush_burst": 0.75},
    },
}

# ----------------------------------------------------------------------------
# 2. Expand prospect archetype tags — top consensus prospects missing tags
# ----------------------------------------------------------------------------
PROSPECT_ARCHETYPE_ADDS = {
    "Jeremiyah Love":        ["power_back", "home_run_hitter", "pass_catching_back"],
    "Carnell Tate":          ["X_receiver", "vertical_stretcher"],
    "Caleb Downs":           ["ball_hawk_S", "split_safety"],
    "Sonny Styles":          ["coverage_LB", "downhill_LB"],
    "Arvell Reese":          ["coverage_LB", "downhill_LB", "athletic_rusher"],
    "David Bailey":          ["athletic_rusher", "standup_EDGE"],
    "Rueben Bain":           ["athletic_rusher", "hand_in_dirt_EDGE"],
    "Akheem Mesidor":        ["athletic_rusher", "hand_in_dirt_EDGE"],
    "Makai Lemon":           ["slot_separator", "YAC_slot"],
    "Jordyn Tyson":          ["X_receiver", "vertical_stretcher"],
    "Francis Mauigoa":       ["power_tackle", "movement_tackle"],
    "Spencer Fano":          ["movement_tackle", "power_tackle"],
    "Kadyn Proctor":         ["power_tackle"],
    "Caleb Lomu":            ["movement_tackle", "power_tackle"],
    "Monroe Freeling":       ["movement_tackle"],
    "Blake Miller":          ["power_tackle"],
    "Max Iheanachor":        ["movement_tackle"],
    "Olaivavega Ioane":      ["athletic_interior", "interior_OL"],
    "Emmanuel Pregnon":      ["athletic_interior", "interior_OL"],
    "Chase Bisontis":        ["interior_OL"],
    "Parker Brailsford":     ["interior_OL"],
    "Kenyon Sadiq":          ["move_TE", "inline_TE"],
    "Mansoor Delane":        ["press_corner", "man_corner"],
    "Jermod McCoy":          ["man_corner", "press_corner"],
    "Colton Hood":           ["press_corner", "man_corner"],
    "Chandler Rivers":       ["zone_corner", "press_corner"],
    "Dillon Thieneman":      ["split_safety", "ball_hawk_S"],
    "Emmanuel McNeil-Warren":["split_safety"],
    "Kayden McDonald":       ["run_stuffing_IDL"],
    "Christen Miller":       ["run_stuffing_IDL", "penetrating_IDL"],
    "Peter Woods":           ["penetrating_IDL", "run_stuffing_IDL"],
    "Ty Simpson":            ["accurate_QB", "pocket_QB"],
    "Fernando Mendoza":      ["accurate_QB", "pocket_QB"],
    "Drew Allar":            ["pocket_QB"],
    "Garrett Nussmeier":     ["accurate_QB", "pocket_QB"],
    "Keldric Faulk":         ["hand_in_dirt_EDGE"],
    "Dani Dennis-Sutton":    ["standup_EDGE", "athletic_rusher"],
    "Zion Young":            ["hand_in_dirt_EDGE"],
    "T.J. Parker":           ["athletic_rusher", "standup_EDGE"],
    "Cashius Howell":        ["athletic_rusher", "standup_EDGE"],
    "Malachi Lawrence":      ["standup_EDGE"],
    "Omar Cooper Jr.":       ["X_receiver", "vertical_stretcher"],
    "K.C. Concepcion":       ["YAC_slot", "slot_separator"],
    "Denzel Boston":         ["X_receiver"],
    "Anthony Hill Jr.":      ["downhill_LB", "coverage_LB"],
    "C.J. Allen":            ["coverage_LB", "downhill_LB"],
    "Jacob Rodriguez":       ["downhill_LB"],
    "Max Klare":             ["move_TE"],
    "Eli Stowers":           ["move_TE", "inline_TE"],
}

# ----------------------------------------------------------------------------
# 3. Write patched files
# ----------------------------------------------------------------------------
# Team archetype prefs
tap = load(ARCH_TEAM_P) if ARCH_TEAM_P.exists() else {"meta": {}, "preferences": {}}
# Overwrite with reasoning-derived weights (old scheme-only prefs were coarse)
for team, data in REASONING_FITS.items():
    tap["preferences"][team] = data["archetypes"]
tap["meta"]["n_teams"] = len(tap["preferences"])
tap["meta"]["source"] = "reasoning-derived 2026-04-20"
tap["meta"]["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
save(ARCH_TEAM_P, tap)

# Prospect archetype tags — merge adds
pap = load(ARCH_PROS_P) if ARCH_PROS_P.exists() else {"meta": {}, "archetypes": {}}
updated_players = 0
for player, new_tags in PROSPECT_ARCHETYPE_ADDS.items():
    existing = set(pap["archetypes"].get(player, []))
    merged = sorted(existing | set(new_tags))
    if len(merged) != len(existing) or merged != sorted(existing):
        pap["archetypes"][player] = merged
        updated_players += 1
pap["meta"]["n_tagged"] = len(pap["archetypes"])
save(ARCH_PROS_P, pap)

# Record in agents meta
agents = load(AGENTS_P)
agents["_meta_reasoning_fits"] = {
    "applied_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    "teams_with_reasoning": len(REASONING_FITS),
    "prospects_updated_archetypes": updated_players,
    "note": ("Team archetype prefs derived from scheme + coaching + "
             "roster-context analyst REASONING — not from picks. Model "
             "will score each prospect against these preferences; "
             "picks converge toward consensus because the reasoning "
             "chain matches."),
}
save(AGENTS_P, agents)

print(f"Wrote reasoning-derived archetype preferences for {len(REASONING_FITS)} teams")
print(f"Updated archetype tags for {updated_players} prospects")
print("Ready to re-run the independent MC.")
