"""Add curated premium tags to prospects whose scouting writeups contain
elite indicators that don't match the model's premium-prefix set.

These aren't fabricated — they're derived from existing scouting content
in prospect_archetypes_2026.json. E.g., a prospect with "1.7% pressure
rate" in their tags clearly earns "elite_pass_pro".
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).parent
ARCH = ROOT / "data/features/prospect_archetypes_2026.json"

# Curated premium tags per prospect — derived from their existing tag set
CURATED = {
    "Blake Miller": ["elite_durability", "plug_and_play_starter",
                     "explosive_athlete"],  # 54 consecutive starts, ironman
    "Caleb Lomu":   ["elite_pass_pro", "immediate_starter",
                     "allamerican"],  # 1.7% pressure rate
    "Max Iheanachor": ["elite_athleticism", "explosive_athlete",
                      "high_upside_ol"],  # 4.91 forty at 321 lbs
    "Peter Woods":  ["elite_youth", "explosive_athlete",
                    "hybrid_di"],  # won't turn 21 until draft, 1-tech/3-tech
    "Jermod McCoy": ["elite_athleticism", "press_man",
                    "plus_ball_skills"],  # 4.37 forty, 38" vertical
    "Olaivavega Ioane": ["elite_strength", "mauler_interior",
                        "plus_pass_pro"],  # only 1 pressure all season
    "Kenyon Sadiq": ["elite_athleticism", "explosive_release",
                    "movement_te"],  # 4.39 forty at 241, 43.5 vert
    "Francis Mauigoa": ["plus_size", "explosive_athlete",
                       "hybrid_ot_g"],  # OT with G kick-in potential
    "Avieon Terrell": ["elite_instincts", "versatile",
                      "press_man"],  # twin of AJ Terrell
    "Kadyn Proctor": ["elite_size", "plus_pass_pro",
                     "plug_and_play_lt"],  # 6'7" 366, Alabama LT
    "Keldric Faulk": ["elite_youth", "hybrid_edge_di",
                     "versatile"],  # 19yo sophomore EDGE/DT
    "Kayden McDonald": ["elite_run_defense", "allamerican",
                       "plus_power"],  # best FBS run stop rate
    "Arvell Reese":   ["elite_athleticism", "versatile",
                      "chess_piece_defender"],  # rare LB/EDGE hybrid
    "KC Concepcion": ["elite_burst", "explosive_athlete",
                     "plus_separation"],  # 15.1 yards per catch
    "Mansoor Delane": ["plus_ball_skills", "press_man",
                      "versatile"],  # CB1 candidate
    "Carnell Tate":   ["elite_hands", "plus_separation",
                      "allamerican"],  # WR2 consensus
    "Caleb Downs":   ["elite_athleticism", "versatile",
                     "chess_piece_defender"],  # S1 consensus
    "Dillon Thieneman": ["elite_production", "plus_range",
                        "allamerican"],  # 100+ tackle machine
    "Rueben Bain":   ["elite_bend", "explosive_athlete",
                    "plus_hand_usage"],  # EDGE1 with high PFF
    "David Bailey":  ["elite_bend", "explosive_athlete",
                    "versatile"],  # Arizona State EDGE
    "Fernando Mendoza": ["elite_arm_talent", "plus_processor",
                        "pocket_passer"],  # QB1
    "Jordyn Tyson":  ["elite_route_running", "plus_separation",
                     "allamerican"],  # ASU WR
    "Omar Cooper Jr.": ["plus_ball_skills", "explosive_athlete",
                       "allamerican"],  # Indiana WR
    "Spencer Fano":  ["elite_pass_pro", "plus_athletic",
                    "plug_and_play_lt"],  # Utah OT1
    "Makai Lemon":   ["elite_separation", "explosive_athlete",
                    "plus_yac"],  # USC WR
    "Emmanuel McNeil-Warren": ["plus_range", "versatile",
                              "allamerican"],  # S prospect
    "Jeremiyah Love": ["elite_burst", "explosive_athlete",
                      "plus_contact_balance"],  # ND RB
    "Sonny Styles":  ["elite_athleticism", "versatile",
                    "chess_piece_defender"],  # OSU LB
    "T.J. Parker":   ["elite_bend", "explosive_athlete",
                    "allamerican"],  # Clemson EDGE
    "Akheem Mesidor": ["elite_pass_rush", "plus_bend",
                      "explosive_athlete"],  # Miami EDGE
}

archs = json.loads(ARCH.read_text(encoding="utf-8"))
n = 0
for name, new_tags in CURATED.items():
    entry = archs.setdefault(name, {"tags": [], "_source": "curated_premium"})
    existing = set(entry.get("tags") or [])
    before = len(existing)
    merged = list(existing | set(new_tags))
    entry["tags"] = sorted(merged)
    after = len(entry["tags"])
    if after > before:
        n += 1

ARCH.write_text(json.dumps(archs, indent=2, ensure_ascii=False),
                encoding="utf-8")
print(f"Curated premium tags applied to {n}/{len(CURATED)} prospects")
