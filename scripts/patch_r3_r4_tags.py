"""Merge R3-R4 scouting tags into prospect_archetypes_2026.json.

Tags drawn from PFF 2026 Draft Guide, Brugler's The Beast, Jeremiah NFL.com,
Legwold ESPN Top 100, Zierlein NFL.com, CBS Sports, Walter Football, PFN.
Scope: consensus ranks ~80-150.
"""
import json

PATH = r'C:\Users\colin\nfl-draft-predictor\data\features\prospect_archetypes_2026.json'

patches = {
    # EDGE / DL
    "Romello Height": [
        "bend_around_the_arc", "inside_counter_spin", "stand_up_rusher",
        "3_4_olb_fit", "wide_9_fit", "late_bloomer_production_2025",
        "underdeveloped_run_defense", "hand_fighter", "sub_package_weapon",
        "texas_tech_transfer_production",
    ],
    "Joshua Josephs": [
        "long_arms_83_wingspan", "edge_setter_run_game", "two_gap_capable",
        "4_3_strongside_de_fit", "3_4_5_tech_fit", "bull_rush_developmental",
        "tennessee_multi_year_starter", "limited_bend_athlete",
        "power_over_finesse_rusher", "inside_stunt_contributor",
    ],
    "Keyron Crawford": [
        "first_step_quickness", "underdeveloped_counter_moves",
        "3_4_olb_convert", "wide_9_rotational_fit", "auburn_one_year_production",
        "long_levered_edge", "ascending_rusher_trajectory", "hand_usage_raw",
        "sub_package_rusher", "processor_slow_vs_run",
    ],
    "L.T. Overton": [
        "5_tech_body_type", "power_base_at_the_point", "alabama_rotational_starter",
        "hand_length_at_strikes", "3_4_de_fit", "4_3_strongside_de_fit",
        "anchor_vs_double_teams", "underwhelming_sack_production",
        "stack_and_shed_developmental", "two_gap_capable",
    ],
    "Anthony Lucas": [
        "usc_transfer_production", "quick_twitch_off_snap", "3_4_olb_fit",
        "4_3_de_fit", "length_edge_setter", "inside_counter_flashes",
        "pass_rush_plan_developing", "rotational_contributor",
        "senior_bowl_participant", "run_defense_physical_developing",
    ],
    "Caden Curry": [
        "ohio_state_rotational_starter", "high_motor_rusher",
        "inside_outside_versatility", "4i_technique_snaps",
        "4_3_de_fit", "3_4_base_de_fit", "run_fits_sound",
        "average_get_off_burst", "hand_usage_refined",
        "senior_bowl_invite_consideration",
    ],
    "Max Llewellyn": [
        "iowa_multi_year_starter", "effort_based_rusher", "stand_up_rusher",
        "3_4_olb_fit", "4_3_strongside_de_fit", "long_frame_edge",
        "underwhelming_athletic_testing", "technique_over_traits",
        "run_defense_functional", "rotational_edge_projection",
    ],
    "Darrell Jackson Jr.": [
        "florida_state_transfer", "86_wingspan_length_edge", "5_tech_projection",
        "power_anchor_developmental", "3_4_de_fit", "two_gap_capable",
        "stack_and_shed_flashes", "run_defense_first_role",
        "limited_pass_rush_moves", "rotational_starter_ceiling",
    ],
    "Kaleb Proctor": [
        "small_school_fcs_production", "southeastern_louisiana_standout",
        "3_tech_projection", "penetrating_interior_rusher",
        "block_shedder_flashes", "level_of_competition_concerns",
        "senior_bowl_measurables", "rotational_interior_fit",
        "one_gap_shoot_the_gap", "developmental_nfl_jump",
    ],
    "Chris McClellan": [
        "missouri_transfer_from_florida", "3_tech_one_gap_fit",
        "pad_level_inconsistent", "flashes_pass_rush_upside",
        "penetrating_interior_rusher", "rotational_interior_dl",
        "block_shedder_developing", "pass_rush_juice_glimpses",
        "run_defense_adequate", "short_area_quickness",
    ],
    "Zxavian Harris": [
        "nose_tackle_build", "mississippi_multi_year_rotation",
        "0_1_tech_fit", "run_stuffer_first", "two_gap_anchor",
        "block_occupier", "special_teams_block_history",
        "limited_pass_rush_ceiling", "3_4_nose_fit", "base_down_run_defender",
    ],
    "Tyler Onyedim": [
        "texas_am_transfer_from_iowa_state", "3_4_de_projection",
        "5_tech_heavy_hands", "power_base_anchor", "gap_integrity_player",
        "limited_pass_rush_production", "rotational_base_de",
        "long_armed_edge_setter", "senior_bowl_invite",
        "two_gap_capable",
    ],
    "Dontay_Corleone": [],
    "Dontay Corleone": [
        "cincinnati_multi_year_starter", "0_1_tech_nose_fit",
        "run_stuffing_nt", "interior_anchor", "block_occupier_two_gap",
        "blood_clot_2024_health_concern", "limited_pass_rush_snaps",
        "base_down_run_defender", "3_4_nose_fit", "power_base_at_the_point",
    ],
    "Zane Durant": [
        "penn_state_rotational_starter", "3_tech_one_gap_fit",
        "quick_off_the_snap", "penetrating_interior_rusher",
        "undersized_interior", "leverage_wins_underneath_pads",
        "pass_rush_flashes_on_games", "4_3_under_fit",
        "rotational_interior_dl", "senior_bowl_participant",
    ],
    "Rayshaun Benny": [
        "michigan_multi_year_rotation", "4i_5_tech_fit",
        "base_de_projection", "run_defense_first_role",
        "pass_rush_developmental", "long_armed_edge_setter",
        "3_4_de_fit", "rotational_base_de", "hand_usage_developing",
        "two_gap_capable",
    ],
    "DeMonte Capehart": [
        "clemson_multi_year_rotation", "penetrating_3_tech",
        "one_gap_penetrator", "pass_rush_flashes_2025",
        "block_shedder_developmental", "senior_bowl_invite",
        "rotational_interior_dl", "4_3_under_fit",
        "short_area_quickness", "run_defense_inconsistent",
    ],

    # CB
    "Davison Igbinosun": [
        "53_career_starts_durability", "physical_press_corner",
        "ohio_state_multi_year_starter", "flag_prone_downfield",
        "boundary_cb_projection", "cover_3_sky_fit", "cover_1_press_fit",
        "press_bail_technique", "zone_off_snaps", "long_speed_questions",
    ],
    "Malik Muhammad": [
        "texas_multi_year_starter", "442_speed", "plant_and_drive_burst",
        "pattern_match_cb", "boundary_cb_fit", "cover_1_press_fit",
        "slot_cross_train_snaps", "change_of_direction_fluid",
        "undersized_boundary_frame", "zone_off_triangle",
    ],
    "Julian Neal": [
        "arkansas_multi_year_starter", "off_zone_cb", "cover_3_sky_fit",
        "tackle_wrap_physical", "press_man_developmental",
        "plant_and_drive_downhill", "ball_skills_6_pbus_2025",
        "boundary_cb_projection", "zone_heavy_scheme_fit",
        "run_support_corner",
    ],
    "Devin Moore": [
        "florida_transfer_from_kansas_state", "press_bail_fluid",
        "long_speed_442_flashes", "cover_1_press_fit",
        "boundary_cb_fit", "man_heavy_scheme_fit", "hip_fluidity_clean",
        "ball_skills_developing", "undersized_frame", "zone_off_capable",
    ],
    "Chandler Rivers": [
        "duke_four_year_starter", "technician_corner_traits",
        "442_speed_underwhelming", "plant_and_drive_ball_skills",
        "cover_3_sky_fit", "off_zone_cb", "slot_cross_train_potential",
        "undersized_boundary_concern", "special_teams_kick_block",
        "acc_multi_year_production",
    ],
    "Daylen Everette": [
        "georgia_multi_year_rotation", "press_man_snaps",
        "boundary_cb_projection", "cover_1_press_fit",
        "sec_pedigree_development", "press_bail_technique",
        "physical_at_line_of_scrimmage", "ball_skills_inconsistent",
        "long_frame_edge_corner", "zone_off_snaps",
    ],
    "Julian_Neal_dup": [],
    "Will Lee III": [
        "texas_am_transfer_from_kansas_state", "442_speed_flashes",
        "press_man_snaps", "boundary_cb_projection", "cover_1_press_fit",
        "undersized_frame_concern", "plant_and_drive_ball_skills",
        "four_interceptions_career", "hip_fluidity_clean",
        "zone_off_capable",
    ],
    "Tacario Davis": [
        "washington_transfer_from_arizona", "6_4_length_cb", "press_man_cb",
        "long_speed_adequate", "boundary_cb_projection", "cover_1_press_fit",
        "tight_hips_concerns", "physical_jam_at_line", "red_zone_matchup_corner",
        "zone_match_fit",
    ],
    "Ephesians Prysock": [
        "washington_transfer_from_arizona", "6_4_length_cb",
        "press_man_developmental", "boundary_cb_projection",
        "cover_3_sky_fit", "plant_and_drive_stiff",
        "long_frame_edge_corner", "tight_hips_concerns",
        "red_zone_matchup_corner", "cover_1_press_fit",
    ],

    # SAFETY
    "Kamari Ramsey": [
        "usc_transfer_from_ucla", "cover_4_quarter_fit", "box_safety_snaps",
        "nickel_safety_versatility", "single_high_rep_fit", "downhill_trigger",
        "tackle_wrap_physical", "range_to_cover_deep_third_questions",
        "big_nickel_fit", "multi_year_pac12_starter",
    ],
    "Bud Clark": [
        "tcu_multi_year_starter", "free_safety_profile", "deep_half_reader",
        "ball_hawk_15_career_ints", "single_high_rep_fit", "range_traits",
        "cover_4_quarter_fit", "cover_3_middle_fit", "undersized_frame_concern",
        "angles_to_the_ball",
    ],
    "Jalon Kilgore": [
        "south_carolina_multi_year_starter", "big_nickel_fit",
        "star_position_versatility", "box_safety_fit", "downhill_trigger",
        "tackle_wrap_physical", "cover_4_quarter_fit",
        "blitz_package_contributor", "slot_defender_cross_train",
        "21_pbus_career_ball_production",
    ],
    "Zakee Wheatley": [
        "penn_state_multi_year_starter", "deep_half_reader",
        "cover_4_quarter_fit", "single_high_rep_fit", "range_to_cover_deep_third",
        "click_and_close_trigger", "ball_production_career",
        "free_safety_profile", "angles_to_the_ball",
        "cover_3_middle_fit",
    ],
    "Genesis Smith": [
        "arizona_multi_year_starter", "box_safety_profile",
        "downhill_trigger", "tackle_wrap_physical",
        "big_nickel_fit", "blitz_package_contributor",
        "cover_4_quarter_fit", "undersized_box_safety",
        "run_support_first_role", "cover_3_buzz_fit",
    ],
    "VJ Payne": [
        "kansas_state_multi_year_starter", "big_12_defensive_production",
        "box_safety_fit", "tackle_wrap_physical", "cover_4_quarter_fit",
        "blitz_package_contributor", "downhill_trigger",
        "range_to_cover_deep_third_questions", "big_nickel_fit",
        "senior_bowl_invite",
    ],

    # LB
    "Jaishawn Barham": [
        "michigan_transfer_from_maryland", "4_sacks_23_pressures_2024",
        "blitz_package_weapon", "3_4_inside_lb_fit", "4_3_will_lb_fit",
        "pass_rush_flashes_from_off_ball", "downhill_trigger",
        "coverage_processor_developing", "angles_to_ball_inconsistent",
        "tackle_wrap_physical",
    ],
    "Deontae Lawson": [
        "alabama_multi_year_starter", "3_4_mike_fit", "4_3_mike_fit",
        "tampa_2_mike_fit", "downhill_trigger", "tackle_wrap_physical",
        "sideline_to_sideline_range_questions", "coverage_zone_match",
        "sec_production_pedigree", "run_fits_sound",
    ],
    "Harold Perkins": [
        "lsu_multi_year_starter", "2024_acl_injury_recovery",
        "3_4_olb_fit", "weakside_lb_fit", "blitz_package_weapon",
        "sub_package_rusher", "medical_red_flag", "sec_production_pedigree",
        "pass_rush_flashes_career", "coverage_range_traits",
    ],
    "Keyshaun Elliott": [
        "arizona_state_transfer", "3_4_inside_lb_fit",
        "4_3_will_lb_fit", "downhill_trigger", "tackle_wrap_physical",
        "coverage_zone_match", "run_fits_sound",
        "blitz_package_contributor", "angles_to_ball_developing",
        "senior_bowl_invite",
    ],
    "Kaleb Elarms-Orr": [
        "tcu_multi_year_starter", "4_3_will_lb_fit",
        "3_4_inside_lb_fit", "coverage_zone_match",
        "tackle_wrap_physical", "downhill_trigger",
        "blitz_package_contributor", "big_12_defensive_production",
        "senior_bowl_invite", "range_traits",
    ],
    "Bryce Boettcher": [
        "oregon_multi_year_starter", "walk_on_origin_story",
        "tampa_2_mike_fit", "4_3_mike_fit", "coverage_zone_match",
        "run_fits_sound", "tackle_wrap_physical",
        "blitz_package_contributor", "sideline_to_sideline_range_questions",
        "special_teams_contributor",
    ],

    # QB
    "Drew Allar": [
        "penn_state_multi_year_starter", "6_5_prototype_build",
        "arm_talent_all_levels", "pocket_passer_profile",
        "accuracy_inconsistent_intermediate", "big_arm_thrower",
        "pro_style_under_center", "progression_reader_developing",
        "escapability_limited", "2024_cfp_experience",
    ],
    "Garrett Nussmeier": [
        "lsu_multi_year_starter", "undersized_qb_frame",
        "air_raid_system_fit", "anticipation_thrower",
        "aggressive_risk_tolerance", "17_ints_two_seasons",
        "off_platform_throw_talent", "west_coast_system_fit",
        "developmental_backup_qb", "pocket_movement_adequate",
    ],
    "Cole Payton": [
        "north_dakota_state_multi_year_starter", "fcs_production_level",
        "dual_threat_qb_profile", "rpo_system_fit",
        "777_rushing_yards_career", "31_career_rushing_tds",
        "development_nfl_jump_concerns", "gadget_qb_package_fit",
        "arm_strength_flashes", "backup_qb_projection",
    ],
    "Taylen Green": [
        "arkansas_transfer_from_boise_state", "dual_threat_qb_profile",
        "rpo_system_fit", "6_6_prototype_build", "rushing_upside_qb",
        "accuracy_inconsistent", "arm_talent_flashes",
        "developmental_backup_qb", "pocket_passer_questions",
        "gadget_qb_package_fit",
    ],

    # OT / IOL
    "Sam Hecht": [
        "kansas_state_multi_year_starter", "wide_zone_guard_fit",
        "gap_scheme_guard_fit", "hand_placement_refined",
        "anchor_vs_bull_rush", "second_level_climber",
        "interior_kick_candidate", "body_control_redirecting",
        "combo_block_seals", "big_12_production_pedigree",
    ],
    "Logan Jones": [
        "iowa_four_year_starter_at_center", "dl_to_ol_conversion_history",
        "wide_zone_center_fit", "combo_block_seals", "second_level_climber",
        "snap_accuracy_clean", "undersized_center_frame",
        "anchor_vs_bull_rush_questions", "bradbury_career_comp",
        "big_ten_production_pedigree",
    ],
    "Dametrious Crownover": [
        "texas_am_multi_year_starter", "left_tackle_experience",
        "kick_to_guard_potential", "wide_zone_tackle_fit",
        "gap_scheme_guard_fit", "hand_placement_developing",
        "anchor_vs_bull_rush", "body_control_redirecting",
        "senior_bowl_invite", "sec_production_pedigree",
    ],
    "Jalen Farmer": [
        "kentucky_multi_year_starter", "interior_kick_candidate",
        "gap_scheme_guard_fit", "wide_zone_guard_fit",
        "anchor_vs_bull_rush", "second_level_climber",
        "combo_block_seals", "hand_placement_developing",
        "senior_bowl_invite", "sec_production_pedigree",
    ],
    "Jake Slaughter": [
        "florida_multi_year_starter_center", "wide_zone_center_fit",
        "gap_scheme_center_fit", "snap_accuracy_clean",
        "combo_block_seals", "second_level_climber",
        "hand_placement_refined", "pass_pro_under_6_pressures",
        "sec_production_pedigree", "plug_and_play_center",
    ],
    "Markel Bell": [
        "miami_transfer_from_nc_state", "left_tackle_experience",
        "wide_zone_tackle_fit", "gap_scheme_tackle_fit",
        "hand_placement_developing", "anchor_vs_bull_rush_questions",
        "body_control_redirecting", "senior_bowl_invite",
        "kick_slide_fluid", "acc_production_pedigree",
    ],
    "Brian Parker II": [
        "duke_multi_year_starter", "left_tackle_experience",
        "wide_zone_tackle_fit", "gap_scheme_tackle_fit",
        "hand_placement_developing", "anchor_vs_bull_rush",
        "kick_to_guard_potential", "acc_production_pedigree",
        "combo_block_seals", "second_level_climber",
    ],
    "Austin Barber": [
        "florida_multi_year_starter", "left_tackle_experience",
        "wide_zone_tackle_fit", "gap_scheme_tackle_fit",
        "hand_placement_refined", "anchor_vs_bull_rush",
        "kick_slide_fluid", "sec_production_pedigree",
        "combo_block_seals", "senior_bowl_invite",
    ],
    "Trey Zuhn III": [
        "texas_am_multi_year_starter", "48_left_tackle_starts",
        "interior_kick_candidate", "wide_zone_tackle_fit",
        "gap_scheme_guard_fit", "hand_placement_refined",
        "anchor_vs_bull_rush", "body_control_redirecting",
        "senior_bowl_invite", "sec_production_pedigree",
    ],
    "Kage Casey": [
        "boise_state_multi_year_starter", "left_tackle_experience",
        "wide_zone_tackle_fit", "gap_scheme_tackle_fit",
        "hand_placement_developing", "anchor_vs_bull_rush_questions",
        "kick_to_guard_potential", "body_control_redirecting",
        "mountain_west_production_pedigree", "senior_bowl_invite",
    ],
    "Jude Bowry": [
        "boston_college_multi_year_starter", "right_tackle_experience",
        "wide_zone_tackle_fit", "gap_scheme_tackle_fit",
        "hand_placement_developing", "anchor_vs_bull_rush",
        "kick_to_guard_potential", "acc_production_pedigree",
        "kick_slide_fluid", "body_control_redirecting",
    ],
    "Billy Schrauth": [
        "notre_dame_multi_year_starter", "interior_kick_candidate",
        "gap_scheme_guard_fit", "wide_zone_guard_fit",
        "anchor_vs_bull_rush", "second_level_climber",
        "combo_block_seals", "hand_placement_refined",
        "senior_bowl_invite", "power_scheme_fit",
    ],
    "Isaiah World": [
        "oregon_transfer_from_nevada", "left_tackle_experience",
        "wide_zone_tackle_fit", "gap_scheme_tackle_fit",
        "hand_placement_developing", "long_arm_edge_setter",
        "anchor_vs_bull_rush", "kick_slide_fluid",
        "body_control_redirecting", "senior_bowl_invite",
    ],
    "Beau Stephens": [
        "iowa_transfer_from_kansas_state", "interior_kick_candidate",
        "gap_scheme_guard_fit", "wide_zone_guard_fit",
        "anchor_vs_bull_rush", "second_level_climber",
        "combo_block_seals", "hand_placement_developing",
        "power_scheme_fit", "big_ten_production_pedigree",
    ],
    "Travis Burke": [
        "memphis_multi_year_starter", "left_tackle_experience",
        "wide_zone_tackle_fit", "gap_scheme_tackle_fit",
        "hand_placement_developing", "anchor_vs_bull_rush",
        "kick_to_guard_potential", "body_control_redirecting",
        "aac_production_pedigree", "senior_bowl_invite",
    ],

    # WR
    "Bryce Lance": [
        "north_dakota_state_multi_year_starter", "fcs_production_level",
        "x_receiver_fit", "big_frame_target", "contested_catch_winner",
        "17_tds_2024_season", "red_zone_target", "route_running_developing",
        "long_speed_questions", "nfl_ready_run_blocker",
    ],
    "Deion Burks": [
        "oklahoma_transfer_from_purdue", "slot_receiver_fit",
        "motion_heavy_usage", "route_precision", "advanced_footwork",
        "yards_after_catch_traits", "undersized_frame_concern",
        "57_receptions_2023_season", "injury_history_2024",
        "gadget_player_package_fit",
    ],
    "Ja'Kobi Lane": [
        "usc_multi_year_starter", "x_receiver_fit", "basketball_frame_target",
        "jump_ball_specialist", "red_zone_target_17_tds",
        "contested_catch_winner", "route_running_developing",
        "long_speed_questions", "high_point_catcher",
        "pac12_production_pedigree",
    ],
    "De'Zhaun Stribling": [
        "mississippi_transfer_from_washington_state",
        "z_receiver_fit", "possession_receiver_profile",
        "back_to_back_800_yard_seasons", "contested_catch_winner",
        "route_running_refined", "nfl_ready_run_blocker",
        "outside_alignment_primary", "yards_after_catch_average",
        "sec_production_pedigree",
    ],
    "Brenen Thompson": [
        "mississippi_state_transfer_from_texas", "z_receiver_fit",
        "vertical_speed_threat", "gadget_player_package_fit",
        "motion_heavy_usage", "undersized_frame_concern",
        "route_running_developing", "4_3_or_faster_speed_profile",
        "slot_cross_train_potential", "deep_ball_win_rate",
    ],

    # TE
    "Oscar Delp": [
        "georgia_multi_year_starter", "inline_te_fit",
        "12_personnel_fit", "y_te_projection",
        "inline_blocker_willing", "contested_catch_winner",
        "route_running_developing", "yards_after_catch_limited",
        "sec_production_pedigree", "goedert_career_comp",
    ],
    "Sam Roush": [
        "stanford_multi_year_starter", "inline_te_fit",
        "y_te_projection", "12_personnel_fit",
        "inline_blocker_willing", "contested_catch_flashes",
        "route_running_developing", "yards_after_catch_limited",
        "senior_bowl_invite", "pac12_production_pedigree",
    ],
    "Michael Trigg": [
        "baylor_transfer_from_mississippi", "move_te_profile",
        "f_te_fit", "pass_catching_specialist",
        "yards_after_catch_traits", "inline_blocker_limited",
        "big_slot_alignment_potential", "route_running_refined",
        "catch_radius_wide", "11_personnel_fit",
    ],
    "Justin Joly": [
        "nc_state_transfer_from_uconn", "move_te_profile",
        "f_te_fit", "pass_catching_specialist",
        "contested_catch_winner", "red_zone_target_history",
        "inline_blocker_willing", "11_personnel_fit",
        "yards_after_catch_traits", "acc_production_pedigree",
    ],
    "Eli Raridon": [
        "notre_dame_multi_year_starter", "move_te_profile",
        "h_back_alignment_potential", "f_te_fit",
        "inline_blocker_willing", "contested_catch_flashes",
        "route_running_developing", "two_acl_injury_history",
        "12_personnel_fit", "big_frame_target",
    ],
    "Jack Endries": [
        "texas_transfer_from_cal", "move_te_profile",
        "f_te_fit", "pass_catching_specialist",
        "yards_after_catch_traits", "inline_blocker_developing",
        "route_running_refined", "11_personnel_fit",
        "red_zone_target_developing", "senior_bowl_invite",
    ],

    # RB
    "Jonah Coleman": [
        "washington_transfer_from_arizona", "compact_frame_power_back",
        "contact_balance_plus", "receiving_back_capable",
        "zone_scheme_fit", "one_cut_decisive_runner",
        "pass_protection_developing", "yards_after_contact_traits",
        "three_down_capability", "pac12_production_pedigree",
    ],
    "Emmett Johnson": [
        "nebraska_multi_year_starter", "zone_scheme_fit",
        "three_down_capability", "receiving_back_capable",
        "forced_missed_tackles_93_2024", "compact_frame_burst",
        "pass_protection_developing", "contact_balance_plus",
        "one_cut_decisive_runner", "big_ten_production_pedigree",
    ],
    "Kaytron Allen": [
        "penn_state_multi_year_starter", "power_back_profile",
        "short_yardage_specialist", "between_the_tackles_runner",
        "contact_balance_plus", "gap_scheme_fit",
        "receiving_back_limited", "yards_after_contact_traits",
        "pass_protection_willing", "two_back_committee_fit",
    ],
    "Nick Singleton": [
        "penn_state_multi_year_starter", "zone_scheme_fit",
        "home_run_speed_threat", "receiving_back_capable",
        "kick_return_experience", "one_cut_decisive_runner",
        "pass_protection_developing", "two_back_committee_fit",
        "contact_balance_average", "big_ten_production_pedigree",
    ],
}

# Drop dup entries created as placeholders
patches.pop("Julian_Neal_dup", None)
patches.pop("Dontay_Corleone", None)

with open(PATH, 'r', encoding='utf-8') as f:
    archs = json.load(f)

updated = 0
new_created = 0
for name, new_tags in patches.items():
    if not new_tags:
        continue
    if name not in archs:
        archs[name] = {"tags": []}
        new_created += 1
    e = archs[name]
    if not isinstance(e, dict):
        archs[name] = {"tags": []}
        e = archs[name]
    existing = set(e.get("tags") or [])
    merged = sorted(existing | set(new_tags))
    added = len(merged) - len(existing)
    e["tags"] = merged
    if added > 0:
        updated += 1

with open(PATH, 'w', encoding='utf-8') as f:
    json.dump(archs, f, indent=2, ensure_ascii=False)

print(f"Updated: {updated} prospects")
print(f"New entries created: {new_created}")
print(f"Total prospects in archetypes: {len(archs) - 2}")  # exclude meta/archetypes keys
