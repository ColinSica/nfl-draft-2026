# NFL Draft Predictor — Stage 2 Game-Theoretic Model Factor Inventory

Reviewer-ready audit of every factor the Stage 2 simulator uses per team agent.

- **Primary model file**: `src/models/stage2_game_theoretic.py` (2708 lines)
- **Agent producer**: `src/data/build_team_agents.py` → `data/features/team_agents_2026.json`
- **Schema version**: `2.0` (see `build_team_agents.py:781`)
- **Default N simulations**: `500` (`stage2_game_theoretic.py:268`)
- **Current date anchor**: 2026-04-19

All citations are `file:line_number`. When a line contains a load-bearing numeric constant it is quoted.

---

## 1. Team-Agent Schema

This section walks every top-level key emitted for each of the 32 teams in `data/features/team_agents_2026.json` (plus the `_league` and `_meta` sentinel keys). Each row lists the field, the script that writes it, and where Stage 2 reads it (if anywhere).

The canonical construction site is `build_team_agents.py:656-747` (the `profile = {...}` dict literal).

### 1.1 Identity & meta

| Field | Producing script / line | Stage 2 consumer | Notes |
|---|---|---|---|
| `team` | `build_team_agents.py:657` | —  | Mirror of the dict key. |
| `pick` | `build_team_agents.py:658` (`r1_picks[0] if r1_picks else None`) | — (Stage 2 reads pick list from `team_context_2026_enriched.csv`) | First R1 pick for UI only. |
| `second_pick` | `build_team_agents.py:659` | — | Second R1 pick when present. |
| `all_r1_picks` | `build_team_agents.py:660` | — | Full list of R1 slots owned. |
| `total_picks` | `build_team_agents.py:661` (`pick_counts[team]`) | `stage2_game_theoretic.py:441` (`draft_capital` read via `_agent_*` merge) | Integer. |
| `r1_count` | `build_team_agents.py:662` | — | Duplicated under `draft_capital.r1_count`. |
| `gm`, `hc`, `new_hc`, `new_gm` | `build_team_agents.py:663-666` — sourced from `TEAM_META` dict at `build_team_agents.py:66-99` | `stage2_game_theoretic.py:426-428` reads `new_gm` / `new_hc` for trade-aggression boost `*= 1.12` (`stage2_game_theoretic.py:429`). | Identity strings. |
| `win_pct` | `build_team_agents.py:668` (from `team_context_2026_enriched.csv`) | — | Rounded to 3 dp. |
| `win_now_pressure` | `build_team_agents.py:669` — via `classify_win_now` at `build_team_agents.py:427-435` (three-tier: `<0.375→0.2`, `<0.562→0.5`, else `0.9`) | `stage2_game_theoretic.py:419` — `if win_now >= 0.7 and any(n in PREMIUM_TRADE_POSITIONS for n in current_needs): boost *= 1.15` (`stage2_game_theoretic.py:421`). | Contender trade-up driver. |
| `bpa_weight`, `need_weight` | `build_team_agents.py:670-671` — from `classify_win_now`. | `stage2_game_theoretic.py:1381` **used only as the fallback** when the round is not in `_ROUND_BPA_NEED`. For R1 (round 1) the round table at `stage2_game_theoretic.py:1371-1379` (`(0.55, 0.45)`) overrides. | See §2 for the override table. |

### 1.2 QB situation

| Field | Producing script / line | Stage 2 consumer |
|---|---|---|
| `qb_situation` | `build_team_agents.py:673` — from `EXPLICIT_PROFILES` dict (`build_team_agents.py:104-343`), defaulting to `"locked"`. | — (not read directly; `qb_urgency` is the quantitative proxy). |
| `qb_urgency` | `build_team_agents.py:674` — `explicit.get("qb_urgency", row.get("qb_urgency") or 0.0)` | `stage2_game_theoretic.py:690` (backfilled into profile if missing); `stage2_game_theoretic.py:1523-1530` — zeros out QB need when `qb_urg_eff == 0.0`; forces no-WR in picks 1-5 when `>=0.8`. `stage2_game_theoretic.py:1759` — suppresses QB by `0.7×` when cap-tight and `qb_urg_eff < 0.5`. |

### 1.3 Needs

| Field | Producing script / line | Stage 2 consumer |
|---|---|---|
| `roster_needs` | `build_team_agents.py:676` — `explicit["roster_needs"]` (`EXPLICIT_PROFILES`) or derived via `derive_needs_from_team_needs` (`build_team_agents.py:415-424`, uses top-3 rows from `team_needs_2026.csv` scored 3.5 / 2.5 / 1.5). | Stage 2 converts to a 5-entry list in `get_team_profile` (`stage2_game_theoretic.py:695-698`) when no hardcoded override exists. Used as `team_needs_list` at `stage2_game_theoretic.py:1392-1394`. |
| `latent_needs` | `build_team_agents.py:677` — union of `EXPLICIT_PROFILES.latent_needs` and PDF-derived `latent_needs_struct` (`build_team_agents.py:652-654`). | `stage2_game_theoretic.py:1401-1416` — positions in `latent` set `need_match = 0.5` (vs 1.0 for hard needs) **before** elite-override logic fires. |
| `needs_source` | `build_team_agents.py:678` — one of `"explicit_user_spec"` (USER_PRIORITY teams), `"researched_default"` (in EXPLICIT_PROFILES but not priority), `"derived_from_team_needs"` (fallback). Values assigned at `build_team_agents.py:556-561`. | Not read at runtime; informational only for audit. |

### 1.4 Free-agency context

| Field | Producing script / line | Stage 2 consumer |
|---|---|---|
| `fa_moves.arrivals`, `fa_moves.departures` | `build_team_agents.py:644-649` — `_merge_moves(pdf_fa, explicit_fa)` (first-name dedup at `build_team_agents.py:635-642`). | `stage2_game_theoretic.py:707-708` — mirrored under `_agent_fa_moves`. **Not consumed by any scoring logic.** Used only by dashboards / audit. (Flag in §12.) |

### 1.5 GM affinity

| Field | Producing script / line | Stage 2 consumer |
|---|---|---|
| `gm_affinity` | `build_team_agents.py:682` — `load_gm_affinity(team)` (`build_team_agents.py:375-384`) returns `{position_group: delta}` from `data/processed/gm_positional_allocation.csv`. The CSV itself is written by `compute_gm_allocation.py` (see §5). | `stage2_game_theoretic.py:709` exposes as `_agent_gm_affinity`, but the **actual consumer** reads the CSV directly at `stage2_game_theoretic.py:251-257` (`load_gm_affinity`) into `GM_AFFINITY_CACHE`. Applied at `stage2_game_theoretic.py:1732-1737`: `gm_mult = (1.0 + gm_deltas * 3.0).clip(0.80, 1.25)`. |

### 1.6 Trade behaviour

| Field | Producing script / line | Stage 2 consumer |
|---|---|---|
| `trade_behavior.trade_up_rate` | `build_team_agents.py:685` — `TRADE_OVERRIDES[team]` (`build_team_agents.py:350-361`) if present, else `row["trade_up_rate"]`. New-GM default `0.35` (`build_team_agents.py:569`). | `stage2_game_theoretic.py:1873-1874` — bilateral trade rival search: `tur = emp_up if emp_has_signal else csv_up` then threshold at `0.4` (`stage2_game_theoretic.py:1875`). |
| `trade_behavior.trade_down_rate` | `build_team_agents.py:686` | `stage2_game_theoretic.py:2073-2076` — blended with empirical rate: `(base_trade_rate + team_down_rate) / 2 if has_signal else base_trade_rate`. |
| `trade_behavior.pdf_tier` | `build_team_agents.py:690` — from narrative `trade_probability` struct (e.g. `{trade_down_tier: "HIGH", trade_down_prob: 0.7}`). | `stage2_game_theoretic.py:2077-2080` — `tier_rate = TRADE_TIER_RATE[pdf_tier]`, then `effective_trade_rate = max(blended, tier_rate)`. Tier table at `stage2_game_theoretic.py:477-483`: `VERY_HIGH 0.70 / HIGH 0.50 / MODERATE 0.25 / LOW 0.10 / VERY_LOW 0.03`. |

### 1.7 Visit signals

| Field | Producing script / line | Stage 2 consumer |
|---|---|---|
| `visit_signals.confirmed_visits` | `build_team_agents.py:694` — sorted `visits_by_team[team]` from `load_visits` at `build_team_agents.py:387-400` (reads `data/live/master_intel_latest.json`, each player's `teams_visited` list mapped through `NICKNAME_TO_ABBR`). | Stage 2 **does not re-read this**. Instead it reads the `visited_teams` column from `prospects_2026_enriched.csv` and parses via `parse_visits` (`stage2_game_theoretic.py:2181-2202`) into `_visit_set`. See `stage2_game_theoretic.py:1563` (`visit_flag`). |
| `visit_signals.n_confirmed` | `build_team_agents.py:695` | — (display only). |
| `visit_signals.cancelled_anywhere` | `build_team_agents.py:696` — `cancelled_any` is the team-agnostic list from `load_cancelled_visits()` at `build_team_agents.py:403-412`. **Same list is copied verbatim to all 32 teams** (see the ARI sample in team_agents_2026.json). | **NOT consumed by Stage 2.** Confirmed via `grep -r cancelled_anywhere src/models` → zero hits. Flag in §12. |

### 1.8 Scheme

| Field | Producing script / line | Stage 2 consumer |
|---|---|---|
| `scheme.type` | `build_team_agents.py:620-626` — prefer `scheme_hints` (hardcoded for 11 teams at `build_team_agents.py:584-605`) else PDF-derived `scheme_struct.type`. | `stage2_game_theoretic.py:1772-1778` — when non-default, invokes `compute_scheme_fit` (`stage2_game_theoretic.py:545-598`) against `SCHEME_FIT_RULES` (`stage2_game_theoretic.py:498-542`). Poor fit `<0.5 → 0.90×`; strong fit (`==1.0` AND position is a need) `→ 1.04×`. |
| `scheme.premium` | Same as `.type`; falls back to PDF `premium` list (`build_team_agents.py:625-626`). | `stage2_game_theoretic.py:1408-1421` — scheme_premium adds `+0.25` to `need_match` (only on positions already in `team_needs_list`). |

### 1.9 Predictability

| Field | Producing script / line | Stage 2 consumer |
|---|---|---|
| `predictability` | `build_team_agents.py:704` — from `pdf_pred_enum` (one of `HIGH | MEDIUM-HIGH | MEDIUM | LOW-MEDIUM | LOW`, see `PREDICTABILITY_ENUM` map at `parse_team_profiles_pdf.py:398-408`). | `stage2_game_theoretic.py:1797-1805` — multiplicative noise `1 + N(0, 0.04 * mult)` with `mult` from `PREDICTABILITY_NOISE_MULT` (`stage2_game_theoretic.py:463-470`): `HIGH 0.50, MEDIUM-HIGH 0.80, MEDIUM 1.00, LOW-MEDIUM 1.30, LOW 1.70`. Noise clipped to `[0.5, 1.5]`. |

### 1.10 Draft capital

| Field | Producing script / line | Stage 2 consumer |
|---|---|---|
| `draft_capital.r1_count`, `.total_picks` | `build_team_agents.py:707-708`. | — |
| `draft_capital.capital_abundance` | `build_team_agents.py:709-713` — `"very_high"` if ≥10, `"high"` ≥8, `"medium"` ≥6, else `"low"`. | `stage2_game_theoretic.py:440-452` — `"low"` or `total_picks ≤ 5` → `boost *= 0.85`; `"very_high"` or `≥11` → `boost *= 1.10` (only if premium need present). |

### 1.11 Narrative (PDF)

`narrative` key (`build_team_agents.py:721`) embeds the entire parsed PDF block per team from `parse_team_profiles_pdf.py`. Sub-fields:

| Sub-field | PDF extractor | Stage 2 consumer |
|---|---|---|
| `leadership`, `context_2025`, `qb_situation`, `offseason_moves`, `scheme_identity`, `roster_needs_tiered`, `gm_fingerprint`, `uncertainty_flags`, `predictability_tier`, `trade_up_scenario`, `cascade_rule` | `parse_team_profiles_pdf.py:74-88` section markers; `parse_team_block` at `parse_team_profiles_pdf.py:192-287`. | Prose only — not consumed. |
| `player_archetypes` | `parse_team_profiles_pdf.py:90-92` (`ARCHETYPE_RE`). | Prose only. |
| `scheme_struct` | `extract_scheme_struct` (`parse_team_profiles_pdf.py:416-437`). | Same as `scheme.type` / `.premium` (see 1.8). |
| `fa_moves_struct` | `extract_fa_moves_struct` (`parse_team_profiles_pdf.py:440-478`). | Mirror of `fa_moves` — not read. |
| `latent_needs_struct` | `extract_latent_needs_struct` (`parse_team_profiles_pdf.py:481-496`). | Merged into `latent_needs` at `build_team_agents.py:653-654`. |
| `predictability_enum` | `extract_predictability_enum` (`parse_team_profiles_pdf.py:499-510`). | Drives `predictability` field (1.9). |
| `trade_probability` | `extract_trade_probability` (`parse_team_profiles_pdf.py:513-539`). | Drives `trade_behavior.pdf_tier`. |
| `injury_flags` | `extract_injury_flags` (`parse_team_profiles_pdf.py:616-666`). | `stage2_game_theoretic.py:714` (`_agent_injury_flags`); consumed at `stage2_game_theoretic.py:1484-1499` — high-severity flag adds `+0.3` to `need_match` at matched position when it's a team need. |
| `decision_maker` | `extract_decision_maker` (`parse_team_profiles_pdf.py:669-696`) — returns `{primary, tiebreaker, advisor_weight, source}`. | `stage2_game_theoretic.py:715` (`_agent_decision_maker`). **Only MIN→O'Connell and DAL→Jerry+Stephen get non-default.** `advisor_weight` is set to `0.5` or `0.2` (`parse_team_profiles_pdf.py:688, 694`) but **never read** by `stage2_game_theoretic.py` — verified via grep. Flag in §12. |
| `hard_constraints` | `extract_hard_constraints_team` (`parse_team_profiles_pdf.py:699-724`) — enumerates constraint `type` strings: `no_trade_down`, `trade_up_only`, `stay_put_stated`, `rarely_trades`, `no_r1_movement_streak`, `aggressive_trader`, `heavy_trade_down`. | `stage2_game_theoretic.py:716-718` (`_agent_hard_constraints`); consumed at `stage2_game_theoretic.py:2100-2105`: `no_trade_down` → rate = 0; `rarely_trades`/`no_r1_movement_streak` → min(rate, 0.05); `stay_put_stated` → min(rate, 0.10). `trade_up_only`, `aggressive_trader`, `heavy_trade_down` are **parsed but never consumed**. Flag in §12. |

### 1.12 Roster context

| Field | Producing script / line | Stage 2 consumer |
|---|---|---|
| `roster_context.age_cliffs` | `compute_roster_context.py:68-120` (`compute_age_cliffs`). Thresholds at `compute_roster_context.py:40-47`: OT/G/C/T/OL `32`, QB `35`, TE `32`, WR `30`, RB `28`, EDGE/DE/DT/DL/NT `31`, LB/ILB/OLB/MLB `30`, CB/DB/S/FS/SS `30`. Severity = `"high"` if age ≥ threshold+3, else `"medium"`. | `stage2_game_theoretic.py:721` (`_agent_age_cliffs`); consumed at `stage2_game_theoretic.py:1454-1465`: `severity=="high"` positions add `+0.2` to `need_match` (only on positions already in `team_needs_list`). |
| `roster_context.previous_year_allocation` | `compute_roster_context.py:123-148` — dict with keys `2024_r1`, `2024_r2`, `2025_r1`, `2025_r2`, each holding lists of `{pos, player, pick}`. | `stage2_game_theoretic.py:722` (`_agent_prev_year_alloc`); consumed at `stage2_game_theoretic.py:1470-1478`: positions in `2025_r1` get `need_match *= 0.6` (40% same-position repeat penalty). `2024_r1`, `2024_r2`, `2025_r2` parsed but **not consumed**. Flag in §12. |

### 1.13 Cap context

| Field | Producing script / line | Stage 2 consumer |
|---|---|---|
| `cap_context.cap_space_m`, `.dead_cap_m`, `.notes` | `build_cap_and_coaching.py:145-184` — reads `data/external/cap_2026.csv` if present, else `FALLBACK_CAP` dict at `build_cap_and_coaching.py:56-89`. | `stage2_game_theoretic.py:726-727` (`_agent_cap_space_m`, `_agent_dead_cap_m`). **Not consumed at runtime** — only `constraint_tier` matters. |
| `cap_context.constraint_tier` | Tier rules at `build_cap_and_coaching.py:155-160`: `cap_m<15 or dead_m>25 → "tight"`; `cap_m>45 → "flush"`; else `"normal"`. | `stage2_game_theoretic.py:725` (`_agent_cap_tier`); consumed at `stage2_game_theoretic.py:1754-1766`: `tight` suppresses QB `×0.7` (when `qb_urg_eff<0.5`), RB/TE `×0.92`; `flush` boosts QB/EDGE/OT/CB `×1.05`. |

### 1.14 Coaching

| Field | Producing script / line | Stage 2 consumer |
|---|---|---|
| `coaching.hc`, `.hc_tree`, `.hc_college_stints` | `build_cap_and_coaching.py:187-204` — `hc_tree` and `hc_college_stints` come from hardcoded `COACHING_DATA` dict at `build_cap_and_coaching.py:99-132`. | `stage2_game_theoretic.py:729-730` (`_agent_hc_tree`, `_agent_hc_college_stints`); `hc_college_stints` consumed at `stage2_game_theoretic.py:1782-1791`: prospect whose `college` contains any stint substring gets `score *= 1.08`. `hc_tree` is **exposed but never consumed** by Stage 2 scoring. Flag in §12. |

### 1.15 Analyst consensus (team-level)

| Field | Producing script / line | Stage 2 consumer |
|---|---|---|
| `analyst_consensus[str(pick_num)] = {team, consensus_all, consensus_tier1, picks_all_top5, picks_tier1_top5, trade_noted, reasoning}` | `build_team_agents.py:744-746` via `_analyst_for_team` (`build_team_agents.py:438-462`). Source: `data/features/analyst_consensus_2026.json` produced by `ingest_analyst_mocks.py`. | **Not consumed by Stage 2 under the team-agent key.** Stage 2 reads `analyst_consensus_2026.json` directly (`stage2_game_theoretic.py:92-93` → `_ANALYST_CONSENSUS`) and uses it via `analyst_distribution` (`stage2_game_theoretic.py:96-157`). |

### 1.16 `_league` key

`_league` is written at `build_team_agents.py:754-755`, containing the PDF's league-wide synthesis. Subfields consumed:

| Subfield | Producer | Stage 2 consumer |
|---|---|---|
| `cascade_rules_struct` | `extract_cascade_rules` at `parse_team_profiles_pdf.py:568-594`. | `stage2_game_theoretic.py:67-68` loads `_CASCADE_RULES`; `stage2_game_theoretic.py:1426-1448` applies `CASCADE_NEED_DAMPING = 0.5` (`stage2_game_theoretic.py:69`). |
| `trade_up_candidates_struct`, `trade_down_candidates_struct`, `known_unknowns_struct`, `hard_trade_constraints_struct` | `parse_team_profiles_pdf.py:788-803`. | **Parsed but not consumed** by Stage 2. Flag in §12. |

### 1.17 `_meta` key

Written at `build_team_agents.py:769-782`. Contains `generated_at`, source mtimes, `analyst_intel_meta`, `schema_version: "2.0"`. Audit/dashboard only.

---

## 2. Per-Pick Scoring Formula (`compute_base_scores`)

Defined at `stage2_game_theoretic.py:1353-1840`. Takes prospects DF + a single pick dict; returns a Series of float scores.

### 2.1 Round-scaled BPA vs need weights

`stage2_game_theoretic.py:1371-1382` — the `_ROUND_BPA_NEED` table:

```
1: (0.55, 0.45)
2: (0.45, 0.55)
3: (0.35, 0.65)
4: (0.30, 0.70)
5: (0.25, 0.75)
6: (0.25, 0.75)
7: (0.20, 0.80)
```

Fallback to `(pick["bpa_weight"], pick["need_weight"])` from CSV when round is absent (`stage2_game_theoretic.py:1381`).

### 2.2 `bpa_term`

`stage2_game_theoretic.py:1384-1385`:

```
final_sc = prospects[final_score_col].clip(lower=0, upper=728).fillna(728)
bpa_term = (1 - final_sc / 728.0) * bpa_w
```

Reads from either `final_score_noised_early` (picks 1-16) or `final_score_noised_late` (picks 17-32) — columns built per-sim at `stage2_game_theoretic.py:2003-2008` by adding Gaussian noise with `sigma = NOISE_STD_FINAL_SCORE = 15.0` (`stage2_game_theoretic.py:276`) for early, `NOISE_STD_LATE_PICKS = 25.0` (`stage2_game_theoretic.py:277`) for late.

### 2.3 `need_term`

Five-step construction (`stage2_game_theoretic.py:1387-1561`):

1. **Base match** (`stage2_game_theoretic.py:1412`): `need_match = pos_canon.isin(team_needs_list).astype(float)`
2. **Latent** (`stage2_game_theoretic.py:1414-1416`): positions in latent set (needs_override-filtered) → `0.5`.
3. **Scheme premium** (`stage2_game_theoretic.py:1419-1421`): if `pos ∈ scheme.premium ∩ team_needs_list`, `need_match += 0.25`.
4. **Cascade damping** (`stage2_game_theoretic.py:1426-1448`): consult `_CASCADE_RULES`; if trigger pick already took a player at trigger_position, then `need_match *= 0.5` at dependent_position.
5. **Age cliffs** (`stage2_game_theoretic.py:1454-1465`): high-severity cliffs → `need_match += 0.2` (intersect with `team_needs_list`).
6. **Previous year repeat** (`stage2_game_theoretic.py:1470-1478`): 2025 R1 same-position → `need_match *= 0.6`.
7. **Injury flags** (`stage2_game_theoretic.py:1484-1499`): high severity → `need_match += 0.3` (intersect with `team_needs_list`).
8. **Trade scenario adjustments** (`stage2_game_theoretic.py:1502-1516`):
   - `PHI` + `aj_brown_traded`: WR `need_match = clip(lower=1.0) + 0.5`.
   - `NYG` + `lawrence_traded`: DL `need_match = clip(1.0) + 0.5`; else `0.0`.
9. **Hard block** (`stage2_game_theoretic.py:1519-1520`): positions in `r1_blocked_positions` → `need_match = 0`.
10. **QB lock** (`stage2_game_theoretic.py:1523-1526`): `qb_urg_eff == 0.0` → QB need_match = 0.
11. **ARI-style WR gate** (`stage2_game_theoretic.py:1529-1530`): `qb_urg_eff >= 0.8 AND pick_num <= 5` → WR = 0.
12. **Elite BPA override** (`stage2_game_theoretic.py:1535-1537`): consensus rank ≤ `ELITE_CONS_RANK_THRESHOLD = 20` (`stage2_game_theoretic.py:873`) → `need_match = clip(lower=1.0)`.

Then scarcity + panic multipliers (`stage2_game_theoretic.py:1545-1561`):

- `DEEP_CLASS = {"EDGE", "OT", "CB"}` → `scarcity = 0.8` (`stage2_game_theoretic.py:794, 796`) unless EDGE with `cons ≤ 15` (`stage2_game_theoretic.py:798`) or not a team need.
- `THIN_CLASS = {"QB", "WR"}` (`stage2_game_theoretic.py:795`) → `scarcity = 1.3` (`stage2_game_theoretic.py:797`) when need match.
- `panic_mult = 1.5` (`stage2_game_theoretic.py:1559`) when last two picks were same canonical position.

Finally:

```
need_term = need_match * need_w * scarcity * panic_mult
```

### 2.4 `visit_term`

`stage2_game_theoretic.py:1563-1578`:

```
visit_flag = prospects["_visit_set"].apply(lambda s: 1 if team in s else 0)
# Multi-source weight from _ANALYST_AGG[player].visits.per_source:
#   ≥3 sources → 0.28, ≥2 → 0.22, else 0.15
visit_term = visit_flag * visit_weight
```

Constants inlined at `stage2_game_theoretic.py:1572-1576` (`0.28`, `0.22`, `0.15`).

### 2.5 `intel_term`

`stage2_game_theoretic.py:1580-1581`:

```
intel_flag = (prospects["intel_top_team"] == team).astype(float)
intel_term = intel_flag * prospects["intel_link_max"].fillna(0) * 0.10
```

`intel_top_team` and `intel_link_max` are produced by `add_chatgpt_features.py:165-166` and land in `prospects_2026_enriched.csv`.

### 2.6 Composition

`stage2_game_theoretic.py:1583`:

```
score = bpa_term + need_term + visit_term + intel_term
```

### 2.7 Injury-flag penalty (per prospect)

`stage2_game_theoretic.py:1589-1593`: multiplicative subtraction by round:

```
R1 0.02, R2 0.08, R3 0.15, R4-5 0.20, R6-7 0.25
```

Applied as `score -= injury_flag * round_penalty`.

### 2.8 League visit-count bonus (round-scaled)

`stage2_game_theoretic.py:1600-1604`:

```
vcount = prospects["visit_count"].fillna(0).clip(upper=10)
round_visit_wt = {1:0.005, 2:0.010, 3:0.015, 4:0.020,
                  5:0.025, 6:0.030, 7:0.030}.get(round_num, 0.010)
score += vcount * round_visit_wt
```

Differs from §2.4 in that it's team-agnostic — rewards generally-visited prospects.

### 2.9 Positional-value multiplier

Base table (`stage2_game_theoretic.py:856-871`):

| Position | Multiplier |
|---|---|
| QB | 1.40 |
| EDGE | 1.25 |
| CB | 1.22 |
| OT | 1.10 |
| WR | 1.08 |
| LB | 1.02 |
| IOL / G / C | 0.95 |
| TE | 0.95 |
| S | 0.95 |
| RB / HB | 0.90 |
| FB | 0.85 |
| DL / DT / IDL | 1.05 |
| NT | 1.00 |

Then further adjustments:

- **Non-premium top-1** (`stage2_game_theoretic.py:1610-1613`): top-1 at raw position in `NON_PREMIUM_RAW = {TE,RB,FB,HB,IOL,G,C,DL,DT,NT}` (`stage2_game_theoretic.py:872`) → multiplier set to `0.95`.
- **RB bimodal** (`stage2_game_theoretic.py:1620-1624`): elite RB (cons≤10) `×1.15`; mid RB (cons>10) `×0.55`.
- **Early LB cap** (`stage2_game_theoretic.py:1629-1631`): pick ≤ 16 LB multiplier `×0.60`.
- **Safety slide** (`stage2_game_theoretic.py:1638-1652`): top-S `×0.75` (pick<15) or `×0.85` (pick<22); 2nd-S `×0.55` (pick<25).
- **IOL slide** (`stage2_game_theoretic.py:1657-1664`): 2nd-IOL `×0.65` when pick<25.

Then `score = score * pv_mult` (`stage2_game_theoretic.py:1666`).

### 2.10 Proximity

`stage2_game_theoretic.py:1669-1670`: if `cons_rank > 3 * pick_num` → `score *= 0.5`.

### 2.11 Reach prevention

`stage2_game_theoretic.py:1672-1708`:

- `REACH_GAP_THRESHOLD = 8` (`stage2_game_theoretic.py:874`) for picks 1-20.
- `LATE_PICK_REACH_THRESHOLD = 8` (`stage2_game_theoretic.py:875`) for picks 21-32.
- `premium_need` (`stage2_game_theoretic.py:1677-1679`): QB or OT in needs and visited — exempt.
- **Scaled reach penalty** (`stage2_game_theoretic.py:1685-1687`):

```
reach_distance = (-(pick_num - cons) - gap_threshold).clip(lower=0)
reach_multiplier = (0.55 - 0.035 * reach_distance).clip(lower=0.10)
```

- **Non-premium hard cap** (`stage2_game_theoretic.py:1693-1695`): `cons - pick_num > 15` AND position in `NON_REACH_POSITIONS = NON_PREMIUM_RAW | {LB, S, FS, SS}` → `score *= 0.10`.
- **EDGE deep reach** (`stage2_game_theoretic.py:1703-1704`): `>12` slot gap → `score *= 0.12`.
- **CB deep reach** (`stage2_game_theoretic.py:1705-1706`): `>10` slot gap → `score *= 0.20`.
- **IDL deep reach** (`stage2_game_theoretic.py:1707-1708`): `>12` slot gap → `score *= 0.12`.

### 2.12 Slippage boost

`stage2_game_theoretic.py:1717-1722`:

```
slippage = pick_num - cons
elite_slip = (cons <= 15) & (slippage > 0)  # hard-blocked positions excluded
slip_boost = (1.0 + 0.06 * slippage).clip(upper=1.55)
score = score.where(~elite_slip, score * slip_boost)
```

### 2.13 Global cap

`stage2_game_theoretic.py:1726-1728`:

```
cap = cap_threshold(pick_num)  # 22 if ≤10, 38 if ≤20, 48 if ≤28, else 55
over_cap = cons > cap
score = score.where(~over_cap, -1e6)
```

See §3 for `cap_threshold`.

### 2.14 GM affinity multiplier

`stage2_game_theoretic.py:1732-1737`:

```
gm_deltas = gm_group.apply(lambda g: GM_AFFINITY_CACHE[(team, g)])
gm_mult = (1.0 + gm_deltas * 3.0).clip(0.80, 1.25)
score *= gm_mult
```

Constants: `GM_AFFINITY_SCALE = 3.0` (`stage2_game_theoretic.py:262`), `_MIN = 0.80`, `_MAX = 1.25` (`stage2_game_theoretic.py:263-264`).

### 2.15 Player-level multipliers

- **Medical penalty** (`stage2_game_theoretic.py:1740-1741`, dict at `stage2_game_theoretic.py:803-811`): currently just `"Jermod McCoy": 0.50`.
- **Post-combine boosts** (`stage2_game_theoretic.py:1745`, dict at `stage2_game_theoretic.py:818-826`): `Sonny Styles: 1.20`, `Mike Washington Jr.: 1.25`.
- **Position scarcity top-1** (`stage2_game_theoretic.py:1746-1748`): `_compute_position_scarcity` (`stage2_game_theoretic.py:836-851`) returns `1.15` boost when the top at a position has ≥20 rank-gap to #2.

### 2.16 Cap-tier suppression

`stage2_game_theoretic.py:1754-1766`: see §1.13 — `tight` suppresses QB ×0.7 (when `qb_urg_eff<0.5`), RB/TE ×0.92; `flush` boosts QB/EDGE/OT/CB ×1.05.

### 2.17 Scheme-fit multiplier

`stage2_game_theoretic.py:1772-1778`: poor fit `<0.5` → `×0.90`; strong fit (`==1.0` AND need) → `×1.04`.

### 2.18 HC-college connection

`stage2_game_theoretic.py:1782-1791`: if prospect's college contains any `_agent_hc_college_stints` substring → `score *= 1.08`.

### 2.19 Predictability noise

See §1.9. `stage2_game_theoretic.py:1797-1805`.

### 2.20 Hard-block floor

`stage2_game_theoretic.py:1823-1831`: positions in `r1_blocked_positions` (or QB if `qb_urg_eff == 0.0`) → `score = -1e9` (worse than cap-violation `-1e6`).

### 2.21 GM multipliers (by team)

`stage2_game_theoretic.py:1833-1839` routes through `apply_gm_multipliers` (`stage2_game_theoretic.py:943-966`) for CLE / GB / PHI / NO / KC only:

| Team | Bias | Trigger | Multiplier |
|---|---|---|---|
| CLE | Youth (Berry) | `age > 22` | `× 0.9` |
| GB | Athleticism (Gutekunst) | `ras_score > 8.0` | `× 1.15` |
| PHI | Premium position (Roseman) | `positional_value_prior > 7` | `× 1.10` |
| NO | Impact/consensus<20 (Loomis) | `rank < 20` | `× 1.20` |
| KC | Premium position (Veach) | `positional_value_prior > 7` | `× 1.10` |

---

## 3. Position Scarcity / Tier Logic

### 3.1 `_compute_position_scarcity`

`stage2_game_theoretic.py:836-851`. For each position group, if the top-1's rank gap to #2 ≥ `POSITION_SCARCITY_GAP_THRESHOLD = 20` (`stage2_game_theoretic.py:832`) then top-1 gets `POSITION_SCARCITY_BOOST = 1.15` (`stage2_game_theoretic.py:833`). Cached in `_POS_SCARCITY_CACHE` (`stage2_game_theoretic.py:834`).

### 3.2 `cap_threshold`

`stage2_game_theoretic.py:916-927`:

```
pick_num ≤ 10 → 22
pick_num ≤ 20 → 38
pick_num ≤ 28 → 48
else          → 55
```

Applied in §2.13.

### 3.3 Tier-exhaustion triggers (for trade logic)

`stage2_game_theoretic.py:294` — `TIER_SIZES = {EDGE:5, OT:5, CB:5, WR:6, QB:2, IDL:4}`. Consumed by `compute_dynamic_trade_boost` (§4.b driver 2).

---

## 4. Trade Logic

### 4.a Pre-scripted scenarios

**`_load_trade_scenarios`** at `stage2_game_theoretic.py:1162-1174` reads `data/features/trade_scenarios_expanded_2026.json` (61 scenarios; `trade_scenarios_expanded_2026.json:2-3`). Each scenario has `pick, up_team, down_team, target_player, target_position, times_mocked, tier1_credible, empirical_rate, trade_reason, notes, source, archetype`.

**`determine_trades`** at `stage2_game_theoretic.py:1177-1324`:

1. Pass 1 (`stage2_game_theoretic.py:1192-1219`): iterate every JSON scenario; each fires independently at its `empirical_rate`; first-writer-wins per pick. Skipped if `down_team ∈ {any, unknown, tbd, ""}` (`stage2_game_theoretic.py:1203-1204`).
2. DAL chain propagation (`stage2_game_theoretic.py:1226-1250`):
   - If pick 6 already = DAL (scenario A): propagate `trades[12] = "CLE"`, `trades[20] = "CLE"`, `DAL_trade_scenario = "A"`.
   - If pick 4 = DAL (scenario B): propagate `trades[12] = "TEN"`, `DAL_trade_scenario = "B"`.
   - If neither: roll legacy backup — `<0.08` → A; `0.08-0.11` → B.
3. Other pre-scripted:
   - **PHI trade up to 18** at `rng.random() < 0.10` (`stage2_game_theoretic.py:1260-1262`).
   - **CLE up to 20** at `rng.random() < 0.10` (`stage2_game_theoretic.py:1267-1270`), conditional on DAL scenario A being false OR scenario B active.
   - **CLE up to 12** at `rng.random() < 0.08` (`stage2_game_theoretic.py:1275-1278`).
   - **LAR down from 13** at `rng.random() < 0.40` (`stage2_game_theoretic.py:1284-1286`).
   - **SEA down from 32** at `rng.random() < 0.45` (`stage2_game_theoretic.py:1291-1293`).
   - **MIA down from 11** at `rng.random() < 0.12` (`stage2_game_theoretic.py:1297-1299`).
   - **ARI up from R2 to 30** at `rng.random() < 0.28` (`stage2_game_theoretic.py:1305-1307`).
4. Known-unknown scenario flags:
   - `aj_brown_traded`: `rng.random() < 0.20` (`stage2_game_theoretic.py:1315`).
   - `lawrence_traded`: `rng.random() < 0.50` (`stage2_game_theoretic.py:1319`).
   - `nyj_qb_at_2`: `rng.random() < 0.10` (`stage2_game_theoretic.py:1322`).

**`apply_trade_team_swaps`** at `stage2_game_theoretic.py:1333-1346`: rewrites `team` on each pick dict for any `trades[pick_num]` whose value is a valid 3-letter team code (`_VALID_TEAM_RE`, `stage2_game_theoretic.py:1327-1330`).

### 4.b Dynamic in-sim trades

**`compute_dynamic_trade_boost`** at `stage2_game_theoretic.py:303-456`. Returns multiplicative boost (default 1.0) on the pre-existing `effective_trade_rate`. Full enumeration:

| Driver | Trigger | Multiplier | Citation |
|---|---|---|---|
| **D1a: QB cascade — demand ≥ supply** | `n_avail_qbs > 0` AND `QB ∉ current_needs` AND `qb_needy_count ≥ n_avail_qbs` within `QB_CASCADE_WINDOW = 8` (`stage2_game_theoretic.py:293`) | `×2.50` | `stage2_game_theoretic.py:352` |
| **D1b: QB cascade — ≥1 needy behind** | `qb_needy_count ≥ 1` (fallback) | `×1.60` | `stage2_game_theoretic.py:355` |
| **D1c: sliding elite QB** | Any `avail_qbs` row with `rank < pick_num - 5` | `×1.40` | `stage2_game_theoretic.py:359` |
| **D2: tier exhaustion (premium only)** | Position ∈ `PREMIUM_TRADE_POSITIONS = {QB,EDGE,OT,CB,WR,IDL,DL}` (`stage2_game_theoretic.py:301`), `taken_at_pos ≥ tier_n - 1`, ≥2 teams behind need it in next `LEAPFROG_WINDOW + 2 = 4` picks | `×1.50` | `stage2_game_theoretic.py:380` |
| **D3: leapfrog** | Next pick team shares a need position that's premium | `×1.40` if `pick_num ≥ 20` else `×1.15` | `stage2_game_theoretic.py:394` |
| **D4: 5YO grab** | Pick 28-32 AND premium-position prospect available at `rank ≤ pick_num + 5` | `×1.25` | `stage2_game_theoretic.py:408` |
| **D5: win-now aggression** | `win_now_pressure ≥ 0.7` AND premium need | `×1.15` | `stage2_game_theoretic.py:421` |
| **D5b: new GM/HC urgency** | `new_gm` or `new_hc` AND premium need | `×1.12` | `stage2_game_theoretic.py:429` |
| **D7a: capital poor** | `capital_abundance == "low"` OR `total_picks ≤ 5` | `×0.85` | `stage2_game_theoretic.py:445` |
| **D7b: capital rich** | `capital_abundance == "very_high"` OR `total_picks ≥ 11`, premium need | `×1.10` | `stage2_game_theoretic.py:451` |

**`try_bilateral_trade`** at `stage2_game_theoretic.py:1847-1916`:

- Iterates later picks; requires partner `trade_up_rate ≥ 0.4` (`stage2_game_theoretic.py:1875`).
- Requires `top_pos ∈ partner.top3_needs` (`stage2_game_theoretic.py:1877`).
- `offer = FITZ_VALUES[partner_pick] * 1.18` (`stage2_game_theoretic.py:1879`); rejected if `offer < value_now * 0.85` (`stage2_game_theoretic.py:1880`).
- "Will fall anyway" filter (`stage2_game_theoretic.py:1888-1890`): R1 picks skip if `target_cons > partner_pick + 3` — unless QB or current pick ≤ 10.

### 4.c `derive_trade_compensation` (Fitzgerald-Spielberger chart)

`FITZ_VALUES` table (`stage2_game_theoretic.py:734-739`):

```
1:3000  2:2600  3:2200  4:1800  5:1600  6:1400  7:1300  8:1200
9:1100  10:1000 11:900  12:850  13:800  14:750  15:700  16:650
17:600  18:550  19:525  20:500  21:475  22:450  23:425  24:400
25:375  26:350  27:325  28:300  29:275  30:250  31:225  32:200
```

`FITZ_ROUND_APPROX` (`stage2_game_theoretic.py:743-750`): R2 250, R3 110, R4 55, R5 30, R6 16, R7 7.

**`derive_trade_compensation`** (`stage2_game_theoretic.py:753-786`) targets `value_up * 1.18` (18% premium) and packs with Round 2-7 approximations, up to 4 items total.

### 4.d `trade_behavior` usage

- `trade_up_rate` → `stage2_game_theoretic.py:1873-1874` bilateral partner search.
- `trade_down_rate` → `stage2_game_theoretic.py:2073-2076` blended with empirical rate.
- `pdf_tier.trade_down_tier` → `stage2_game_theoretic.py:2077-2080` mapped through `TRADE_TIER_RATE` (`stage2_game_theoretic.py:477-483`).

---

## 5. GM / Coaching Factors

### 5.1 `gm_affinity`

Built by `compute_gm_allocation.py` (full file reviewed). Key rules:

- `GM_TENURE` dict at `compute_gm_allocation.py:26-56` lists 26 GMs with `(team, first_year_at_team)`. Five first-year GMs excluded.
- Window: `max(start_year, 2020)` to 2025 (`compute_gm_allocation.py:85`).
- Requires ≥3 top-64 picks at current team (`compute_gm_allocation.py:87`).
- `team_pct = fraction of GM's top-64 picks at position`; `league_pct = 2020-2025 top-64 baseline`; `delta = team_pct - league_pct` (`compute_gm_allocation.py:94-95`).
- Position groups per `POS_TO_GROUP` (`compute_gm_allocation.py:58-71`) — note `DE → EDGE`, `DT/NT/DL → IDL`, `OG/G → G`, etc.

**Stage 2 consumption**:

- `load_gm_affinity` (`stage2_game_theoretic.py:251-257`) populates `GM_AFFINITY_CACHE`.
- `apply_gm_multipliers` helper (`stage2_game_theoretic.py:1732-1737`) computes: `gm_mult = (1.0 + delta * 3.0).clip(0.80, 1.25)`.

Concrete example per source comment at `stage2_game_theoretic.py:260-261`: Roseman PHI LB `+12%` → `1 + 0.12 * 3 = 1.36`, clipped to `1.25`.

### 5.2 `coaching.hc_tree`

Hardcoded at `build_cap_and_coaching.py:99-132`. Values (unique set): `belichick, bowles, cowboys, detroit, falcons, harbaugh, indiana, internal, mcvay, mccarthy, ohio_state, payton, reid, ravens, saints, seattle, shanahan, tomlin, 49ers_dc`.

**Stage 2 consumption**: `_agent_hc_tree` is exposed via `get_team_profile` (`stage2_game_theoretic.py:729`) but **never read** in scoring logic (see §12).

### 5.3 `hc_college_stints`

Hardcoded at `build_cap_and_coaching.py:99-132`. Examples: BAL `[Michigan]`, CLE `[Georgia, Oklahoma State]`, MIA `[Ohio State, Boston College]`.

**Stage 2 consumption**: `stage2_game_theoretic.py:1782-1791` — substring match on prospect's `college`; matches → `score *= 1.08`.

### 5.4 `new_gm` / `new_hc` urgency boost

`stage2_game_theoretic.py:426-432`:

```
new_gm = bool(prof.get("new_gm"))
new_hc = bool(prof.get("new_hc"))
if (new_gm or new_hc) and any(n in PREMIUM_TRADE_POSITIONS for n in current_needs):
    boost *= 1.12
```

Applies in `compute_dynamic_trade_boost` only.

### 5.5 `decision_maker` / `advisor_weight`

`decision_maker` field is exposed at `stage2_game_theoretic.py:715`. Populated at `parse_team_profiles_pdf.py:669-696` with special cases:

- MIN (`O'Connell unusual power`): `primary="Kevin O'Connell", advisor_weight=0.5, source="narrative"`.
- DAL (`Jerry emotional/aggressive`): `primary="Jerry Jones", tiebreaker="Stephen Jones", advisor_weight=0.2`.

**Verified via grep**: `advisor_weight` appears nowhere in `src/models/` other than the agent merge. Flag in §12.

---

## 6. Need Logic

### 6.1 Numeric scale → `need_term` conversion

- Input: `roster_needs = {position: score}` where scores are derived either (a) explicitly as hardcoded user specs (e.g. `LV: {QB:5.0, WR:3.5, OT:3.0, IDL:2.5}`, `build_team_agents.py:107`), or (b) synthetically via `derive_needs_from_team_needs` (`build_team_agents.py:415-424`, scores 3.5 / 2.5 / 1.5 for top-3).
- Stage 2 converts these to a **list** via `sorted(items, key=-score)[:5]` (`stage2_game_theoretic.py:696-698`).
- `need_match` is a **boolean 0/1** indicator of position in that list (`stage2_game_theoretic.py:1412`). **Numeric magnitudes are discarded** — QB=5.0 and IDL=2.5 both yield `need_match=1.0`.
- After the additive adjustments (latent 0.5, scheme +0.25, injury +0.3, age cliff +0.2), `need_match` is multiplied by `need_w` (round-scaled) × `scarcity` (0.8/1.0/1.3) × `panic_mult` (1.0 or 1.5).

### 6.2 Latent needs handling

`stage2_game_theoretic.py:1401-1416`:

```
latent = {p for p in profile._agent_latent_needs
          if p not in blocked and p not in team_needs_list}
need_match = pos_canon.isin(team_needs_list).astype(float)
if latent:
    latent_mask = pos_canon.isin(latent)
    need_match = need_match.where(~latent_mask, 0.5)
```

Latent numeric score (typically `2.0` per `extract_latent_needs_struct` at `parse_team_profiles_pdf.py:494`) is also discarded — presence-only flag.

### 6.3 Scheme premium +0.25

`stage2_game_theoretic.py:1408-1421`:

```
scheme_premium = set(profile._agent_scheme.premium or [])
if scheme_premium:
    mask = pos_canon.isin(scheme_premium) & pos_canon.isin(team_needs_list)
    need_match = need_match.where(~mask, need_match + 0.25)
```

Intersection with existing needs prevents non-need scheme-premium positions from being inflated.

### 6.4 `needs_source` values

Set by `build_team_agents.py:556-561`:

- `"explicit_user_spec"`: team in `USER_PRIORITY` set at `build_team_agents.py:550-552` (16 teams: LV, NYJ, ARI, TEN, NYG, CLE, DAL, NO, KC, CIN, MIA, LAR, BAL, DET, PHI, CHI).
- `"researched_default"`: in EXPLICIT_PROFILES but not USER_PRIORITY (the remaining 16 at `build_team_agents.py:242-343`).
- `"derived_from_team_needs"`: not in EXPLICIT_PROFILES — fallback via `derive_needs_from_team_needs`.

---

## 7. Visit / Intel Signals

### 7.1 `_visit_set` (per-team)

`stage2_game_theoretic.py:2181-2202` — `parse_visits` normalizes the `visited_teams` column of `prospects_2026_enriched.csv` via nickname→abbr map, stored as a Python `set`.

### 7.2 `visit_term` + multi-source bump

See §2.4. Constants at `stage2_game_theoretic.py:1572-1576`.

The `_ANALYST_AGG` dict (`stage2_game_theoretic.py:74-76`) is loaded from `data/features/analyst_aggregate_2026.json` (built by `aggregate_live_intel.py`). Each player entry has `visits.per_source[source] = {teams, cancelled_flag}`. The `hits` count at `stage2_game_theoretic.py:1570-1571` is the number of distinct sources that list this team for this player.

### 7.3 `cancelled_anywhere`

Loaded at `build_team_agents.py:403-412` via `load_cancelled_visits`. Replicated on every team's agent. **Not consumed anywhere by Stage 2** — verified via grep in §12.

### 7.4 League-wide visit count bonus

See §2.8. Column `visit_count` is produced upstream in `prospects_2026_enriched.csv`. Round weights at `stage2_game_theoretic.py:1602-1603`:

```
R1 0.005, R2 0.010, R3 0.015, R4 0.020, R5 0.025, R6 0.030, R7 0.030
```

Applied as `score += vcount * round_visit_wt`.

### 7.5 `intel_term`

See §2.5. `intel_top_team` and `intel_link_max` come from `add_chatgpt_features.py:165-166` (`pros["intel_link_max"] = ...; pros["intel_top_team"] = ...`). Upstream data: `data/live/master_intel_latest.json`.

---

## 8. Analyst Consensus

### 8.1 `analyst_distribution` — the fallback sampler

`stage2_game_theoretic.py:96-157`. Steps:

1. Look up `_ANALYST_CONSENSUS.per_pick[str(pick_num)]` (`stage2_game_theoretic.py:107`).
2. Blend: `0.50 * freq_tier1[name] + 0.50 * freq_all[name]` per player (`stage2_game_theoretic.py:116-120`). Comment at `stage2_game_theoretic.py:113-115` notes this was tightened from 0.60 tier-1 weight.
3. Resolve short surnames to full names via `_ANALYST_NAME_MAP` (`stage2_game_theoretic.py:162-213`) and `_resolve_analyst_name` (`stage2_game_theoretic.py:215-218`).
4. ADP-reach damping (`stage2_game_theoretic.py:132-138`):

```
if adp - pick_num > 8:
    excess = adp - pick_num - 8
    w *= max(0.03, 0.4 * (0.80 ** excess))
```

5. Elite-slider floor (`stage2_game_theoretic.py:145-152`): any top-5 consensus prospect not in the dist gets injected at `0.70 * max(resolved.values())`.
6. Normalize to sum 1.

### 8.2 `get_override_distribution` — hardcoded scripted overrides

`stage2_game_theoretic.py:973-1156`. Picks 1, 2, 3, 4, 5, 6, 7, 8, 9, 16, 21, 30, 32 have scripted distributions. Everything else (including 10-15, 17-20, 22-29, 31) falls through to `blend_with_analyst(None)` (`stage2_game_theoretic.py:1156`) which is analyst-only.

Picks 11, 12, 13 explicitly `return None` (`stage2_game_theoretic.py:1088-1094`) forcing base utility. Pick 19 returns None only when pick 18 took Thieneman (`stage2_game_theoretic.py:1113-1117`). Pick 20 and 22 always None (`stage2_game_theoretic.py:1129-1130`).

**`blend_with_analyst`** (`stage2_game_theoretic.py:989-1005`): 50/50 blend between scripted and analyst distribution.

### 8.3 `picks_all_top5` / `picks_tier1_top5` / reasoning flow

`_analyst_for_team` at `build_team_agents.py:438-462`:

- Input: `per_pick = _ANALYST_CONSENSUS.per_pick` and `reasoning` dict.
- For each R1 pick, keep top-5 entries of `picks_all` and `picks_tier1` dicts (raw counts).
- Attach `reasoning[str(pick_num)][:8]` (first 8 analyst-prose entries).

**Embedded in `team_agents_2026.json` per team** but **not consumed by Stage 2** (the model reads `_ANALYST_CONSENSUS` directly at `stage2_game_theoretic.py:92-93`).

### 8.4 Verification: "analysts feed profiles only, not picks" claim

The user's memory note asserts "each team is an autonomous entity; analyst content feeds profiles only, never picks directly."

**Actual behaviour of the code**: Analyst content **does feed picks**, through two specific channels:

1. `get_override_distribution` falls through to `blend_with_analyst(None)` for ~15 picks per round (`stage2_game_theoretic.py:1156`), meaning the analyst-consensus distribution **directly samples the player** when no scripted override is set.
2. `blend_with_analyst(scripted)` (`stage2_game_theoretic.py:989-1005`) explicitly mixes analyst weights into the scripted distribution 50/50 for picks that DO have scripted overrides.

The analyst consensus does **not** feed base-scoring `compute_base_scores`. But the override path (the path taken for most picks) is analyst-driven when no hardcoded scripted dist exists. So: the memory-note claim is **contradicted by the current code path**; the override hierarchy is:

1. Forced pick (user pin).
2. Scripted overrides where defined.
3. Analyst-consensus distribution (fallback for any pick without scripted override).
4. Base-utility scoring only when analyst dist is empty for that slot (`stage2_game_theoretic.py:1155`).

---

## 9. Hard Constraints and Overrides

### 9.1 `TEAM_PROFILE_OVERRIDES` enumeration

`stage2_game_theoretic.py:603-666`. All 32 teams (some have only `qb_urgency`):

| Team | qb_urgency | r1_blocked_positions | needs_override |
|---|---|---|---|
| NE | 0.0 | `{QB}` | `[OT, WR, EDGE, TE, CB]` |
| TEN | 0.0 | — | `[RB, OT, EDGE, CB]` |
| NYG | 0.0 | — | `[WR, OT, S, LB, RB]` |
| ARI | 1.0 | — | — |
| PIT | 0.65 | — | `[OL, WR, IOL, S, QB]` |
| CHI | 0.0 | `{WR, QB}` | `[EDGE, S, OL, IDL]` |
| CIN | 0.0 | `{QB, RB}` | `[CB, S, EDGE, LB]` |
| BAL | 0.0 | `{QB}` | `[EDGE, OT, WR, IDL]` |
| WAS | 0.0 | — | `[WR, LB, S, EDGE]` |
| BUF | 0.0 | — | — |
| KC | 0.0 | — | `[CB, OL, EDGE, WR]` |
| JAX | 0.0 | — | — |
| CLE | 0.0 | — | — |
| DET | 0.0 | — | — |
| DAL | 0.0 | — | `[EDGE, CB, LB, S, OT]` |
| MIN | 0.0 | — | — |
| IND | 0.0 | — | — |
| TB | 0.0 | — | — |
| GB | 0.0 | — | — |
| DEN | 0.0 | — | — |
| SEA | 0.0 | `{QB}` | `[RB, CB, EDGE, WR]` |
| SF | 0.0 | — | `[OT, EDGE, CB, IOL, DL]` |
| LAC | 0.0 | `{WR}` | `[DL, EDGE, CB, IOL]` |
| MIA | 0.0 | — | `[WR, CB, S, OT, EDGE]` |
| LAR | 0.3 | — | `[WR, OT, CB, QB, S]` |
| HOU | 0.0 | `{WR}` | `[DL, IOL, OT, CB]` |
| PHI | 0.0 | — | — |
| ATL | 0.0 | — | — |
| CAR | 0.0 | — | — |
| LV | 1.0 | — | — |
| NYJ | 1.0 | — | — |
| NO | 0.7 | — | `[WR, EDGE, CB, OT]` |

Lookup via `get_team_profile` (`stage2_game_theoretic.py:669-731`) with backfill from `_TEAM_AGENTS`.

### 9.2 Hard-constraint string types

From `parse_team_profiles_pdf.py:708-718` — the constraint `type` strings exposed to Stage 2:

- `no_trade_down`
- `trade_up_only`
- `stay_put_stated`
- `rarely_trades`
- `no_r1_movement_streak`
- `aggressive_trader`
- `heavy_trade_down`

Consumed at `stage2_game_theoretic.py:2100-2105` — **only** `no_trade_down`, `rarely_trades`, `no_r1_movement_streak`, `stay_put_stated` have effects:

```
if "no_trade_down" in constraints:
    effective_trade_rate = 0.0
elif "rarely_trades" in constraints or "no_r1_movement_streak" in constraints:
    effective_trade_rate = min(effective_trade_rate, 0.05)
elif "stay_put_stated" in constraints:
    effective_trade_rate = min(effective_trade_rate, 0.10)
effective_trade_rate = min(effective_trade_rate, 0.95)
```

---

## 10. Monte Carlo Flow

### 10.1 RNG seeding

`stage2_game_theoretic.py:273-275`:

```
import os as _os
_env_seed = _os.environ.get("DRAFT_RNG_SEED")
RNG_SEED = int(_env_seed) if _env_seed and _env_seed.isdigit() else None
```

`main()` at `stage2_game_theoretic.py:2223` and the re-run loop at `stage2_game_theoretic.py:2257`: `rng = np.random.default_rng(RNG_SEED)`. When `DRAFT_RNG_SEED` is unset, `RNG_SEED = None`, which means NumPy seeds from OS entropy — **different every run**. Recent commit `7924215 "Fix hardcoded RNG seed + calibrate position multipliers to historical R1 distribution"` fixed a previous hardcoded seed.

### 10.2 Default N sims

`stage2_game_theoretic.py:268`: `N_SIMULATIONS = 500`.

### 10.3 `simulate_one`

`stage2_game_theoretic.py:1923-2163`. Per-sim flow:

1. Determine trades: `trades = forced_trades if forced_trades is not None else determine_trades(rng)` (`stage2_game_theoretic.py:1937`).
2. Apply team swaps: `picks = apply_trade_team_swaps(picks_template, trades)` (`stage2_game_theoretic.py:1938`).
3. Build scripted trade log with reasons dict at `stage2_game_theoretic.py:1951-1959`.
4. Build noised score columns (`stage2_game_theoretic.py:2003-2008`).
5. For each pick in order:
   - If forced → take it (`stage2_game_theoretic.py:2025-2036`).
   - Lazy scoring via `get_scores`/`invalidate_scores` closure (`stage2_game_theoretic.py:2042-2053`).
   - Compute `dist = get_override_distribution(...)` (`stage2_game_theoretic.py:2056`).
   - Compute `effective_trade_rate` from blended empirical + PDF tier + dynamic boost + constraint caps (`stage2_game_theoretic.py:2070-2107`).
   - If trade fires → call `try_bilateral_trade` (`stage2_game_theoretic.py:2113-2118`).
   - If override dist → apply medical / post-combine multipliers to dist weights (`stage2_game_theoretic.py:2122-2127`), sample, continue.
   - Else base-model: `winner_idx = scores_avail.idxmax()` (`stage2_game_theoretic.py:2146`).

### 10.4 Aggregation outputs

- `data/processed/monte_carlo_2026_v12.csv` (`OUT_MC`, `stage2_game_theoretic.py:43`): written at `stage2_game_theoretic.py:2371-2373`. One row per `(player, slot)` with `probability, most_likely_team, mean_landing_pick, variance_landing_pick`. Filtered to slots with `prob ≥ 0.02` (`stage2_game_theoretic.py:2339`).
- `data/processed/predictions_2026.csv`: **not written by stage2** — stage2 reads it as input at `stage2_game_theoretic.py:35` (merged into prospects via `load_data` at `stage2_game_theoretic.py:2168-2170`). Produced upstream by `src/models/predict_2026.py`.
- `data/processed/monte_carlo_trades_2026.json` (`OUT_TRADES`, `stage2_game_theoretic.py:44`): written at `stage2_game_theoretic.py:2501-2503`.
- `data/processed/model_reasoning_2026.json`: written at `stage2_game_theoretic.py:2643-2650` — per-pick factor decomposition for UI consumption.

### 10.5 Position-distribution calibration & reach caps

Recent commit `7924215` & `34a50a6` calibrations visible in code:

- `POS_VALUE_MULT` calibration notes at `stage2_game_theoretic.py:857-871` reference 2021-2025 R1 distribution (QB 2-4/yr, EDGE 4-6/yr, OT 4-6/yr, CB 4-6/yr, WR 5-7/yr, LB ~2/yr, S ~1/yr, IDL 2-3/yr).
- OT trimmed `1.20 → 1.10` to prevent 8+ R1 OTs in 2026 class.
- CB bumped to 1.22 to match hist.
- RB bimodal split at `stage2_game_theoretic.py:1620-1624` (elite `×1.15`, mid `×0.55`).
- Early-pick LB cap `×0.60` at `stage2_game_theoretic.py:1631`.
- EDGE/CB/IDL deep-reach caps at `stage2_game_theoretic.py:1703-1708` (multipliers 0.12, 0.20, 0.12).

---

## 11. Data Provenance Table

| Output artifact | Built by | Upstream source | Consumed by |
|---|---|---|---|
| `data/features/team_agents_2026.json` | `src/data/build_team_agents.py:518-790` | `team_context_2026_enriched.csv`, `prospects_2026_enriched.csv`, `team_needs_2026.csv`, `gm_positional_allocation.csv`, `master_intel_latest.json`, `team_profiles_narrative_2026.json`, `roster_context_2026.json`, `cap_context_2026.json`, `coaching_tree_2026.json`, `analyst_consensus_2026.json` | `stage2_game_theoretic.py:57-59` → `_TEAM_AGENTS` |
| `data/features/team_profiles_narrative_2026.json` | `src/data/parse_team_profiles_pdf.py:807-827` | `data/2026_NFL_Draft_Team_Profiles.txt` | `build_team_agents.py:474-481` |
| `data/features/roster_context_2026.json` | `src/data/compute_roster_context.py:151-181` | `data/raw/nflverse_roster_2025.csv`, `nflverse_depth_charts_2025.csv`, `historical_drafts_2011_2025.csv` | `build_team_agents.py:484-491` |
| `data/features/cap_context_2026.json` | `src/data/build_cap_and_coaching.py:145-184` | `data/external/cap_2026.csv` (optional) or `FALLBACK_CAP` dict | `build_team_agents.py:494-499` |
| `data/features/coaching_tree_2026.json` | `src/data/build_cap_and_coaching.py:187-204` | `COACHING_DATA` hardcoded dict + `team_agents_2026.json` (for HC name) | `build_team_agents.py:502-507` |
| `data/features/analyst_aggregate_2026.json` | `src/data/aggregate_live_intel.py:170-228` | `data/live/visits_*_YYYY-MM-DD.json`, `betting_odds_*_*.json`, `stock_moves_*_*.json` | `stage2_game_theoretic.py:74-76` → `_ANALYST_AGG` |
| `data/features/analyst_consensus_2026.json` | `src/data/ingest_analyst_mocks.py:259-315` | `data/2026 Mock Draft Data.xlsx` | `stage2_game_theoretic.py:91-93` → `_ANALYST_CONSENSUS`; `build_team_agents.py:510-515` |
| `data/features/trade_empirical_2021_2025.json` | `src/data/compute_empirical_trade_rates.py:53-157` | `data/raw/r1_trades_2021_2025.json` (from `scrape_r1_trades.py`) | `stage2_game_theoretic.py:83-85` → `_TRADE_EMPIRICAL` |
| `data/features/trade_scenarios_expanded_2026.json` | Hand-curated (2026-04-18, 61 scenarios) | April 2026 mock-draft universe + GM patterns | `stage2_game_theoretic.py:1162-1174` → `_TRADE_SCENARIOS_CACHE` |
| `data/processed/gm_positional_allocation.csv` | `src/data/compute_gm_allocation.py:74-125` | `data/processed/draft_with_college.csv` | `stage2_game_theoretic.py:251-257` → `GM_AFFINITY_CACHE` |
| `data/processed/prospects_2026_enriched.csv` | Upstream enrichment pipeline (`enrich_all_features.py`, `add_chatgpt_features.py`, `add_positional_value.py`, `add_final_enrichment.py`, `add_sackseer_analyst_biases.py`) | `fetch_2026_prospects.py`, `fetch_2026_combine.py`, `fetch_2026_ages.py` + college stats + `master_intel_latest.json` | `stage2_game_theoretic.py:34, 2167` |
| `data/processed/team_context_2026_enriched.csv` | `src/data/enhance_team_context.py` | `team_context_2026.csv`, `fetch_2026_team_needs.py`, `fetch_2026_draft_order.py` | `stage2_game_theoretic.py:36, 2172`; `build_team_agents.py:519` |
| `data/processed/team_needs_2026.csv` | `fetch_2026_team_needs.py` | External needs sources | `stage2_game_theoretic.py:37, 2173`; `build_team_agents.py:415-424` |
| `data/processed/predictions_2026.csv` | `src/models/predict_2026.py` | `prospects_2026_enriched.csv` + historical Stage 1 model | `stage2_game_theoretic.py:35, 2168` (final_score + model_pred) |
| `data/processed/monte_carlo_2026_v12.csv` | `stage2_game_theoretic.py:2371-2373` | `simulate_one` × 500 | Dashboard / `frontend` |
| `data/processed/monte_carlo_trades_2026.json` | `stage2_game_theoretic.py:2501-2503` | Accumulated `trade_log` events | Dashboard |
| `data/processed/model_reasoning_2026.json` | `stage2_game_theoretic.py:2643-2650` | Deterministic re-score of top-1 per pick | Dashboard |
| `data/live/master_intel_latest.json` | `src/data/daily_intel_update.py:192` | Daily scraping (cbs, vegasinsider, nfltr, pfn, walterfootball, twsn per `data/live/` listing) | `build_team_agents.py:52` (via `load_visits`, `load_cancelled_visits`); `add_chatgpt_features.py` |

---

## 12. Known Gaps / Audit Questions

Concrete, line-cited flags.

### 12.1 Fields parsed but never consumed by Stage 2

- **`cancelled_anywhere`** — populated at `build_team_agents.py:696` (the same team-agnostic list copied to all 32 teams). **Zero consumers** in `src/models/stage2_game_theoretic.py` (verified via grep). Either wire it in or drop from schema.
- **`advisor_weight`** in `decision_maker` — set to `0.5` for MIN, `0.2` for DAL (`parse_team_profiles_pdf.py:688, 694`). `stage2_game_theoretic.py:715` exposes it, but grep confirms `advisor_weight` appears only in the merge line — never read in scoring.
- **`_agent_hc_tree`** — exposed at `stage2_game_theoretic.py:729` but not referenced downstream (verified via grep). Only `hc_college_stints` is actually used (`stage2_game_theoretic.py:1782`).
- **`fa_moves`** — mirrored under `_agent_fa_moves` (`stage2_game_theoretic.py:707-708`). Grep confirms zero downstream consumers.
- **`2024_r1`, `2024_r2`, `2025_r2`** in `previous_year_allocation` — only `2025_r1` is consumed (`stage2_game_theoretic.py:1472`).
- **`known_unknowns_struct`**, **`trade_up_candidates_struct`**, **`trade_down_candidates_struct`**, **`hard_trade_constraints_struct`** — written under `_league` (`parse_team_profiles_pdf.py:788-803`) but never consumed.
- **Hard-constraint types `trade_up_only`, `aggressive_trader`, `heavy_trade_down`** — emitted by `parse_team_profiles_pdf.py:710, 716, 717-718` but the consumer checks only 4 strings at `stage2_game_theoretic.py:2100-2105`.
- **`pick`, `second_pick`** (`build_team_agents.py:658-659`) — exist for UI; Stage 2 reads pick numbers from `team_context_2026_enriched.csv`.

### 12.2 Hardcoded magic numbers without explicit calibration

- `0.18` Fitzgerald premium at `stage2_game_theoretic.py:764, 1879`. Source comment claims "academic studies of 2006-2022 R1 trade-ups show ~15-25%" but no actual citation.
- `0.4` trade-up-rate threshold at `stage2_game_theoretic.py:1875` — hard cutoff, not calibrated.
- `0.85` offer-value floor at `stage2_game_theoretic.py:1880`.
- Noise sigmas `NOISE_STD_FINAL_SCORE = 15.0`, `NOISE_STD_LATE_PICKS = 25.0` (`stage2_game_theoretic.py:276-277`) — no calibration source cited.
- `PREDICTABILITY_SCORE_SIGMA = 0.04` (`stage2_game_theoretic.py:471`) — no source.
- Injury-flag round penalties `{1:0.02, 2:0.08, 3:0.15, 4-5:0.20, 6-7:0.25}` at `stage2_game_theoretic.py:1591-1592` — calibrated "analyst logic" per comment, no external source.
- Reach multiplier formula `(0.55 - 0.035 * reach_distance).clip(lower=0.10)` at `stage2_game_theoretic.py:1685-1686` — hand-tuned coefficients.
- Cascade damping `0.5` (`stage2_game_theoretic.py:69`) — source comment references "PDF phrasing" for MIN→CAR cascade, but only one anecdotal anchor.
- `ELITE_CONS_RANK_THRESHOLD = 20` (`stage2_game_theoretic.py:873`) — comment says "was 15"; no rationale for 20.
- Slippage formula `1.0 + 0.06 * slippage, cap 1.55` at `stage2_game_theoretic.py:1721` — hand-tuned.
- `NE`'s qb_urgency override hardcoded to `0.0` (`stage2_game_theoretic.py:605`) — contradicts `EXPLICIT_PROFILES["NE"]["qb_urgency"] = 0.0` (`build_team_agents.py:306`) consistently, but both are hardcoded independently — sync risk.
- `NOISE_STD_LATE_PICKS = 25.0` — per comment labelled "BUG 2" but unclear what the original bug was.

### 12.3 Overrides that contradict agent JSON

- `TEAM_PROFILE_OVERRIDES["PIT"]["qb_urgency"] = 0.65` (`stage2_game_theoretic.py:613`); `EXPLICIT_PROFILES["PIT"]["qb_urgency"] = 0.65` (`build_team_agents.py:312`) — match. **No contradiction.**
- `TEAM_PROFILE_OVERRIDES["NO"]["qb_urgency"] = 0.7` (`stage2_game_theoretic.py:664`); `EXPLICIT_PROFILES["NO"]["qb_urgency"] = 0.7` (`build_team_agents.py:166`) — match.
- `TEAM_PROFILE_OVERRIDES["LAR"]["qb_urgency"] = 0.3` (`stage2_game_theoretic.py:652`); `EXPLICIT_PROFILES["LAR"]["qb_urgency"] = 0.3` (`build_team_agents.py:204`) — match.
- `TEAM_PROFILE_OVERRIDES["MIA"]["qb_urgency"] = 0.0` (`stage2_game_theoretic.py:649`); `EXPLICIT_PROFILES["MIA"]["qb_urgency"] = 0.8` (`build_team_agents.py:194`) — **CONTRADICTION**. Stage 2 wins (hardcoded), but the agent JSON's 0.8 is misleading for any downstream tool reading it.
- `TEAM_PROFILE_OVERRIDES["NYJ"]["qb_urgency"] = 1.0` (`stage2_game_theoretic.py:662`); `EXPLICIT_PROFILES["NYJ"]["qb_urgency"] = 0.3` (`build_team_agents.py:115`) — **CONTRADICTION**. Stage 2 wins. Dashboards reading the JSON will show the wrong urgency.
- `TEAM_PROFILE_OVERRIDES["CLE"]["qb_urgency"] = 0.0` (`stage2_game_theoretic.py:629`); `EXPLICIT_PROFILES["CLE"]["qb_urgency"] = 0.0` (`build_team_agents.py:150`) — match.
- `TEAM_PROFILE_OVERRIDES["ARI"]["qb_urgency"] = 1.0` (`stage2_game_theoretic.py:611`); `EXPLICIT_PROFILES["ARI"]["qb_urgency"] = 0.8` (`build_team_agents.py:127`) — **CONTRADICTION**. Stage 2 forces 1.0; JSON shows 0.8.

### 12.4 Duplicated / forked hardcodes

- `POS_TO_NEEDS` (`stage2_game_theoretic.py:930-939`) vs. `POS_TO_GM_GROUP` (`stage2_game_theoretic.py:237-248`) vs. `POS_GROUP` (`compute_roster_context.py:50-59`) vs. `POS_TO_GROUP` (`compute_gm_allocation.py:58-71`) — four near-identical maps that each handle IOL/OT/EDGE/IDL slightly differently. Drift risk.
- `NICKNAME_TO_ABBR` nickname→abbr map exists in 3 places: `stage2_game_theoretic.py:2185-2195` (`parse_visits`), `build_team_agents.py:363-372`, `ingest_analyst_mocks.py:62-72` (as `TEAM_ABBR`). No single source of truth.
- `TEAM_META` in `build_team_agents.py:66-99` and `GM_TENURE` in `compute_gm_allocation.py:26-56` must be kept in sync; no shared fixture.

### 12.5 Silent fallbacks

- `FITZ_VALUES.get(int(up_pick), 150)` (`stage2_game_theoretic.py:762`): picks > 32 silently get `150`. Acceptable only if R1 is the universe; worth asserting.
- `empirical_pick_rate` (`stage2_game_theoretic.py:222-225`) returns `EMPIRICAL_LEAGUE_RATE = 0.30` for any missing slot (`stage2_game_theoretic.py:220`). The source file's `league_avg_rate_per_pick` is read but defaulted if missing — mixing definitions.
- `analyst_distribution` returns `{}` (`stage2_game_theoretic.py:110`) when no data for a pick, causing the caller to silently fall through to base scoring — no warning.
- `try_bilateral_trade` uses `FITZ_VALUES.get(p2["pick_number"], 50) * 1.18` at `stage2_game_theoretic.py:1879` — falls back to `50`, not to round-approx, inconsistent with `derive_trade_compensation`.
- `classify_win_now` (`build_team_agents.py:427-435`) returns `(0.5, 0.5, 0.5)` when `win_pct` is NaN — an invisible default.

### 12.6 Stale / hardcoded counters visible in source

- `MEDICAL_PENALTIES` at `stage2_game_theoretic.py:803-811` has exactly one entry (`Jermod McCoy`). Structure supports many but content is news-driven.
- `POST_COMBINE_BOOSTS` at `stage2_game_theoretic.py:818-826` has exactly two entries (Sonny Styles, Mike Washington Jr.).
- `ANALYST_PICKS` dict at `stage2_game_theoretic.py:881-912` hardcodes analyst picks for only 10 slots (10, 11, 17, 21, 22, 23, 26, 27, 28, 31) — used only for the "analyst agreement" print; not consumed by the model itself.

### 12.7 RNG semantics

- `main()` creates a fresh RNG at `stage2_game_theoretic.py:2223` and **another fresh RNG at `stage2_game_theoretic.py:2257`** to re-run the simulation loop. If `DRAFT_RNG_SEED` is set, these are both seeded identically (reproducible but double-work). If unset, the two loops produce different sequences — the per-pick tally (`landing`) and the conditional-breakdown pass (`team_at_slot`, `pick3_conditional`, etc.) are from **different** 500-sim samples. Line ranges 2229-2251 vs 2272-2331.
- `NE`'s `qb_urgency=0.0` override combined with `r1_blocked_positions={QB}` at `stage2_game_theoretic.py:605-606` is redundant (both zero QB). Harmless.

### 12.8 Scenario-JSON rate calibration

Every scenario in `trade_scenarios_expanded_2026.json` has an independent `empirical_rate`. The cumulative probability at any pick is `1 - prod(1 - rate)` which can exceed the league baseline if many scenarios target the same slot. First-writer-wins at `stage2_game_theoretic.py:1207-1208` caps at one trade per slot but does **not** down-weight scenarios run earlier in the JSON. Order of scenarios in the JSON materially affects sim outputs.

### 12.9 Ambiguities in coaching data

- `TEAM_META["NYG"]["hc"] = "John Harbaugh"` (`build_team_agents.py:90`) contradicts real 2026 timeline (Jim Harbaugh is at LAC; John Harbaugh is at BAL). Self-acknowledged at `build_team_agents.py:13-15`: "NYG HC identity: PDF flagged John Harbaugh vs Jim Harbaugh ambiguity; agent currently says 'John Harbaugh' per TEAM_META. Verify externally."
- `TEAM_META["LAC"]["hc"] = "Jim Harbaugh (LAC)"` (`build_team_agents.py:83`) — correct, but the literal string differs from `coaching_tree_2026.json` values. Minor.
- `TEN`'s `coaching_tree`: `hc_tree = "49ers_dc"` (`build_cap_and_coaching.py:130`) but `TEAM_META["TEN"]["hc"] = "Robert Saleh"` — Saleh came from NYJ HC role, not 49ers DC. Label is loose.

### 12.10 Dynamic trade boost — cumulative ceiling

`compute_dynamic_trade_boost` applies up to 9 multipliers multiplicatively (see §4.b). Stacking worst case: `2.50 * 1.40 * 1.50 * 1.40 * 1.25 * 1.15 * 1.12 * 1.10 = 12.97×`. The hard ceiling comes from `effective_trade_rate = min(effective_trade_rate, 0.95)` at `stage2_game_theoretic.py:2107`, so the ceiling on the scorer is 0.95, but the "boost" itself has no per-stage cap — opaque.

### 12.11 LAR trade-down legacy hardcode vs JSON

`stage2_game_theoretic.py:1284-1286` fires LAR down at 40% unconditionally. This bypasses the "first-writer-wins" JSON logic — any JSON scenario that would have moved pick 13 has already claimed it via `trades[int(pick)] = up`, but the LAR legacy check doesn't consult `trades` first. In sims where a JSON scenario already moved pick 13, the `trades["LAR_traded_down"] = True` flag still fires and `trades[13] = "unknown"` **overwrites** the JSON's team (line 1286). Bug candidate.

### 12.12 `forced_picks` / `forced_trades`

`simulate_one` accepts `forced_picks: {pick_number: player_name}` and `forced_trades: dict` (`stage2_game_theoretic.py:1923-1936`). Forced picks bypass all scoring; downstream picks see them in `taken` and adapt. Not exercised by `main()` but documented for an external mock-draft builder. No safety check that `forced_name` exists in prospects — if missing, falls through silently (`stage2_game_theoretic.py:2028-2036`).

### 12.13 Position mapping inconsistencies

`POS_TO_NEEDS` (`stage2_game_theoretic.py:930-939`) maps all OL variants (OT/G/C/OG/IOL/T) to `"OL"`. But `TEAM_PROFILE_OVERRIDES["SF"]["needs_override"]` includes `"IOL"` and `"OT"` as distinct tokens (`stage2_game_theoretic.py:643`). Since `pos_canon` for an OT prospect is `"OL"`, it matches neither `"OT"` nor `"IOL"` in SF's override list, so SF's OT and IOL tokens **never match**. A careful reader should confirm whether `IOL` and `OT` in `needs_override` across `TEAM_PROFILE_OVERRIDES` are dead tokens.

Spot-check: HOU's `needs_override = [DL, IOL, OT, CB]` (`stage2_game_theoretic.py:657`). An OT prospect has `pos_canon = "OL"`, which is not in that list → `need_match = 0` for OT prospects at HOU (unless elite override at cons≤20 kicks in). Likely unintended.

### 12.14 `_TEAM_AGENTS._league` skipped in enumeration

`stage2_game_theoretic.py:2264-2267`:

```
_all_known_teams = (set(TEAM_PROFILE_OVERRIDES)
                    | {t for t in _TEAM_AGENTS if not t.startswith("_")})
```

Correctly excludes `_league` and `_meta`. But `get_team_profile("_league")` would silently return the narrative data as if it were a team — no asserted invariant.

### 12.15 No explicit R2+ scoring path

Despite `_ROUND_BPA_NEED` having entries for rounds 2-7, `main()` iterates only R1 picks: `r1 = team_ctx[team_ctx["round"] == 1]` at `stage2_game_theoretic.py:2220`. The R2+ weights are scaffolding that is **never exercised in production runs**. External callers invoking `compute_base_scores` for later rounds would trigger code paths that have not been tuned.

### 12.16 Hardcoded "SEA RB need" gap

`TEAM_PROFILE_OVERRIDES["SEA"]["needs_override"] = ["RB", "CB", "EDGE", "WR"]` (`stage2_game_theoretic.py:640`). Combined with RB bimodal penalty for mid-class RBs (`×0.55`, `stage2_game_theoretic.py:1624`) and LB `×0.60` early (pick 32 is not early). Pick 32 is SEA — but if SEA's override gives pre-scripted dist, the LB/RB scorer path is bypassed. Confirm intent.

### 12.17 `0.10` intel multiplier

`stage2_game_theoretic.py:1581`: `intel_term = intel_flag * intel_link_max * 0.10`. The `0.10` weight is uncalibrated and the same as the previous model. Consider A/B-testing.

### 12.18 Deep_edge_protection_threshold magic

`DEEP_EDGE_PROTECTION_THRESHOLD = 15` (`stage2_game_theoretic.py:798`) exempts top-15 EDGE from the deep-class 0.8× penalty. But `ELITE_CONS_RANK_THRESHOLD = 20` at `stage2_game_theoretic.py:873` uses a different threshold for a different exemption. No comment ties the two together.

### 12.19 `visit_term` dependence on `_visit_set`

`_visit_set` is parsed from `prospects_2026_enriched.csv["visited_teams"]` (`stage2_game_theoretic.py:2208`). If the CSV is stale relative to `master_intel_latest.json`, the visit signal degrades silently. No freshness assertion between the two sources.

### 12.20 `POS_VALUE_MULT` keys

`stage2_game_theoretic.py:856-871` has both `DL` and `DT` and `IDL` all at `1.05`. Prospects will have various `position` strings; the mapping at `raw_pos = prospects["position"].fillna("").astype(str).str.upper()` (`stage2_game_theoretic.py:1541`) means a prospect labeled `"DL"` and one labeled `"IDL"` both pass, but a prospect labeled `"dt"` would not (upper-cased first). Lowercase-safe given `.upper()`, but any rare mixed codes (`"dl/edge"`) silently get `pv_mult = 1.0` fallback.

---

## Appendix A — Key constants quick reference

| Name | Value | File:line |
|---|---|---|
| `N_SIMULATIONS` | 500 | `stage2_game_theoretic.py:268` |
| `RNG_SEED` | env `DRAFT_RNG_SEED` else None | `stage2_game_theoretic.py:275` |
| `NOISE_STD_FINAL_SCORE` | 15.0 | `stage2_game_theoretic.py:276` |
| `NOISE_STD_LATE_PICKS` | 25.0 | `stage2_game_theoretic.py:277` |
| `QB_CASCADE_WINDOW` | 8 | `stage2_game_theoretic.py:293` |
| `LEAPFROG_WINDOW` | 2 | `stage2_game_theoretic.py:295` |
| `CASCADE_NEED_DAMPING` | 0.5 | `stage2_game_theoretic.py:69` |
| `GM_AFFINITY_SCALE` | 3.0 | `stage2_game_theoretic.py:262` |
| `GM_AFFINITY_MIN / MAX` | 0.80 / 1.25 | `stage2_game_theoretic.py:263-264` |
| `PREDICTABILITY_SCORE_SIGMA` | 0.04 | `stage2_game_theoretic.py:471` |
| `POSITION_SCARCITY_GAP_THRESHOLD` | 20 | `stage2_game_theoretic.py:832` |
| `POSITION_SCARCITY_BOOST` | 1.15 | `stage2_game_theoretic.py:833` |
| `ELITE_CONS_RANK_THRESHOLD` | 20 | `stage2_game_theoretic.py:873` |
| `REACH_GAP_THRESHOLD` | 8 | `stage2_game_theoretic.py:874` |
| `LATE_PICK_REACH_THRESHOLD` | 8 | `stage2_game_theoretic.py:875` |
| `SLIDER_BOOST_THRESHOLD` | 10 | `stage2_game_theoretic.py:876` |
| `DEEP_MULT / THIN_MULT` | 0.8 / 1.3 | `stage2_game_theoretic.py:796-797` |
| `DEEP_EDGE_PROTECTION_THRESHOLD` | 15 | `stage2_game_theoretic.py:798` |
| `EMPIRICAL_LEAGUE_RATE` (default) | 0.30 | `stage2_game_theoretic.py:220` |
| `PROB_THRESHOLD` (MC output filter) | 0.02 | `stage2_game_theoretic.py:2339` |
| Fitzgerald premium | 1.18 | `stage2_game_theoretic.py:764, 1879` |
| Offer floor | 0.85 | `stage2_game_theoretic.py:1880` |
| Partner `trade_up_rate` threshold | 0.4 | `stage2_game_theoretic.py:1875` |
| Injury high-severity `need_match` bonus | +0.3 | `stage2_game_theoretic.py:1499` |
| Age-cliff high-severity bonus | +0.2 | `stage2_game_theoretic.py:1465` |
| Latent need_match | 0.5 | `stage2_game_theoretic.py:1416` |
| Scheme premium bonus | +0.25 | `stage2_game_theoretic.py:1421` |
| Previous-year repeat multiplier | 0.6 | `stage2_game_theoretic.py:1478` |
| Visit weight tiers (≥3 / ≥2 / base) | 0.28 / 0.22 / 0.15 | `stage2_game_theoretic.py:1573-1576` |
| Intel term weight | 0.10 | `stage2_game_theoretic.py:1581` |
| HC college stint bonus | 1.08 | `stage2_game_theoretic.py:1791` |
| Panic multiplier (back-to-back pos) | 1.5 | `stage2_game_theoretic.py:1559` |
| Slippage slope | 0.06 | `stage2_game_theoretic.py:1721` |
| Slippage cap | 1.55 | `stage2_game_theoretic.py:1721` |
| Cap threshold (picks 1-10 / 11-20 / 21-28 / 29-32) | 22 / 38 / 48 / 55 | `stage2_game_theoretic.py:921-927` |
| Over-cap sentinel | -1e6 | `stage2_game_theoretic.py:1728` |
| Hard-block sentinel | -1e9 | `stage2_game_theoretic.py:1831` |

## Appendix B — `_TEAM_OVERRIDES` completeness check

All 32 teams have an entry in `TEAM_PROFILE_OVERRIDES` (`stage2_game_theoretic.py:603-666`). See §9.1 table. Spot checks:

- `BUF` only has `qb_urgency: 0.0` (`stage2_game_theoretic.py:624`); needs fallback to agent JSON's `EXPLICIT_PROFILES["BUF"]` (`build_team_agents.py:252-255`) which sets needs `[EDGE, CB, WR, IDL]`.
- `JAX`, `CLE`, `DET`, `MIN`, `IND`, `TB`, `GB`, `DEN`, `PHI`, `ATL`, `CAR` similarly only have qb_urgency. Their needs come from `EXPLICIT_PROFILES` backfill.

End of document.
