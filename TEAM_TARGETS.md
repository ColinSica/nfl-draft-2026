# 2026 NFL Draft — Per-Team Target Readout

**Draft dates:** April 23–25, 2026 (Pittsburgh, PA)

Generated from Monte Carlo v12 (500 sims) + model reasoning.
- Source: `monte_carlo_2026_v12.csv` (202 R1 landings), `model_reasoning_2026.json`, `team_agents_2026.json`
- `prob` = fraction of 500 sims in which the player was that team's R1 pick
- `trade_down_prob` / `trade_up_prob` = PDF-tier from analyst consensus
- "(NEW)" flag = 2026-cycle hire only. 2025 hires are not labeled NEW.


---

## LV — Pick 1

**Front office:** GM John Spytek (NEW) · HC Klint Kubiak (NEW)

**Situation:** 0.176 win% · win-now pressure 0.20 · QB bridge (urgency 1.00)

**Cap:** $50.0M space · tier `flush` · dead $8.0M

**Scheme:** Shanahan zone (Kubiak) · premium positions: OT, WR, TE

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| QB | 5.0 |
| WR | 3.5 |
| OT | 3.0 |
| IDL | 2.5 |

**Needs source:** `explicit_user_spec`

**Trade behavior:** trade_up_rate=0.35, trade_down_rate=0.30

**Predictability:** HIGH · Capital: very_high (10 picks total)

**Confirmed visits (2):** Fernando Mendoza, Pat Coogan

**Age cliffs (starters aging out):**

- Geno Smith (QB), age 36 — severity medium
- Raheem Mostert (RB), age 34 — severity high
- Adam Butler (DL), age 32 — severity medium
- Elandon Roberts (LB), age 32 — severity medium
- Jamal Adams (LB), age 31 — severity medium
- Alex Bachman (WR), age 30 — severity medium

### Modal R1 pick(s) from 500-sim MC

**Pick 1** — modal player: **Fernando Mendoza** (QB)

- Components: bpa=0.544, need=0.585, visit=0.15, intel=0.3, pv_mult=1.4, gm_aff=1.0, **final=2.759**
- Top reasons:
  - **QB is a top roster need** (team_need, magnitude 0.59): Need score contributed 0.59 to the total
  - **QB position premium** (positional_value, magnitude 0.40): Position-value multiplier 1.40x (premium slot)
  - **Analyst intel scripted this pick** (intel, magnitude 0.30): Tier-1 analyst consensus pushed prob 0.30

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Fernando Mendoza | QB | Indiana | 1 | 1.000 | 1.00 |

### Analyst/scout archetype notes

- **Pick 1:** Mendoza. Locked. -20000 odds. Universal consensus. Mendoza
fits the Kubiak scheme perfectly: strong-armed pocket passer with play-action/mobility combo,
CFP winner, Heisman credentials.

**Needs (tiered, from team-profile PDF):**

Urgent (4.5+ but addressed at 1): QB (addressed by Mendoza)
Secondary (3+): WR (one of weakest rooms in league), OT (long-term build around
Mendoza), IDL (Leonard scheme needs interior)
Moderate: CB (Johnson added, depth still thin)

**GM fingerprint:** (Spytek):
Trade tendency: Zero drafts in role - league-average priors
Positional affinity: No data (new GM)
Pattern: Spytek comes from TB under Licht. Licht tree values trench investment and
premium positions. Has explicitly said "teams know where they stand" - suggests he's
NOT trading down from 1.

**Uncertainty flags:** Despite consensus certainty on Mendoza, any shock medical or interview concern could
change the calculus
New HC AND new GM = scheme details for future picks are unpredictable


---

## NYJ — Pick 2, 16

- **Pick 2:** NYJ native R1 (2-15 record, 2025)
- **Pick 16:** Acquired from IND (Sauce Gardner-era deal)

**Front office:** GM Darren Mougey (NEW) · HC Aaron Glenn

**Situation:** 0.176 win% · win-now pressure 0.20 · QB locked (urgency 0.00)

**Cap:** $65.0M space · tier `flush` · dead $10.0M

**Scheme:** 3-4 multiple (Glenn) · premium positions: EDGE, LB

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| EDGE | 4.5 |
| WR | 3.5 |
| CB | 2.5 |
| S | 1.0 |

**Latent / future needs:** QB (2.0)

**Needs source:** `explicit_user_spec`

**Trade behavior:** trade_up_rate=0.35, trade_down_rate=0.30

**Predictability:** MEDIUM · Capital: high (9 picks total)

**Confirmed visits (6):** Cian Slone, Joe Fagnano, Logan Taylor, Malachi Fields, Parker Brailsford, Tyre West

**Age cliffs (starters aging out):**

- Tyrod Taylor (QB), age 37 — severity medium
- Quincy Williams (LB), age 30 — severity medium
- Andrew Beck (RB), age 30 — severity medium
- Kene Nwangwu (RB), age 28 — severity medium
- Avery Williams (RB), age 28 — severity medium

**Recent draft history:** 2024_r1: OL Olumuyiwa Fashanu (#11) · 2025_r1: OL Armand Membou (#7) · 2025_r2: TE Mason Taylor (#42)

### Modal R1 pick(s) from 500-sim MC

**Pick 2** — modal player: **David Bailey** (EDGE)

- Components: bpa=0.535, need=0.562, visit=0.0, intel=0.0, pv_mult=1.25, gm_aff=1.0, **final=1.485**
- Top reasons:
  - **EDGE is a top roster need** (team_need, magnitude 0.56): Need score contributed 0.56 to the total
  - **EDGE position premium** (positional_value, magnitude 0.25): Position-value multiplier 1.25x (premium slot)

**Pick 16** — modal player: **Omar Cooper Jr.** (WR)

- Components: bpa=0.519, need=0.585, visit=0.0, intel=0.0, pv_mult=1.08, gm_aff=1.0, **final=1.223**
- Top reasons:
  - **WR is a top roster need** (team_need, magnitude 0.59): Need score contributed 0.59 to the total

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| David Bailey | EDGE | Texas Tech | 2 | 0.562 | 2.93 |
| Arvell Reese | LB | Ohio State | 2 | 0.438 | 3.51 |
| Omar Cooper Jr. | WR | Indiana | 16 | 0.424 | 18.71 |
| Ty Simpson | QB | Alabama | 16 | 0.258 | 24.94 |
| Avieon Terrell | CB | Clemson | 16 | 0.078 | 24.94 |
| Colton Hood | CB | Tennessee | 16 | 0.074 | 28.36 |
| Chris Johnson | CB | San Diego State | 16 | 0.064 | 27.17 |
| Jermod McCoy | CB | Tennessee | 16 | 0.058 | 16.45 |

### Analyst/scout archetype notes

- **Pick 2:** Given Glenn's scheme and pressure-rate failures, the archetype
is an elite edge rusher or versatile chess-piece LB with pass-rush ability. The two dominant
profiles in the consensus board (Bailey/Reese types - edge vs. rangy LB) both fit. Glenn has

openly said he wants "multiple fronts" players, which favors the versatile LB profile over a pure
edge. Secondary option: blue-chip CB to replace Gardner's production.
- **Pick 16:** A separation WR or YAC WR1 type to give Geno (or future QB) a
legitimate weapon. Alternative: long press-CB to complete the secondary rebuild. Low but non-
zero QB probability given 2027 plans.

**Needs (tiered, from team-profile PDF):**

Urgent (4.5+): EDGE (31st in sacks at 26, 27th pressure rate), WR (no receiver hit 400
yards last year beyond Wilson)
Secondary (3): CB (Gardner gone, Wright is backup-level replacement), S (beyond
Fitzpatrick, depth thin)
Moderate (1.5-2): QB (Geno bridge), LB (Davis is 37)

**GM fingerprint:** (Mougey):
Trade tendency: 1 draft of data - some evidence of aggressive willingness ("always open"
per his own quote)
Positional affinity: No meaningful sample
Historical context: Mougey is ex-DEN scouting - comes from analytics-informed front
office

**Uncertainty flags:** New GM with 1 draft = league-average priors
Glenn on hot seat = win-now pressure at odds with rebuild
5 future firsts = extreme flexibility to trade up OR down on draft day


---

## ARI — Pick 3

**Front office:** GM Monti Ossenfort · HC Mike LaFleur (NEW)

**Situation:** 0.176 win% · win-now pressure 0.20 · QB rebuilding (urgency 0.80)

**Cap:** $40.0M space · tier `flush` · dead $12.0M

**Scheme:** McVay tree (LaFleur) · premium positions: WR, OT, RB

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| QB | 4.0 |
| OT | 3.5 |
| EDGE | 3.0 |
| CB | 2.0 |
| WR | 1.5 |

**Needs source:** `explicit_user_spec`

**GM positional affinity** (from 2023-2025 draft history):

- Favors: IDL +0.25, CB +0.11, EDGE +0.09
- Avoids: LB -0.10, QB -0.08, RB -0.07

**Trade behavior:** trade_up_rate=0.50, trade_down_rate=0.50, trade_down_tier=HIGH, trade_down_prob=0.7

**Predictability:** LOW · Capital: medium (7 picks total)

**Confirmed visits (5):** Caleb Banks, David Bailey, Drew Allar, Reggie Virgil, Zavion Thomas

**Age cliffs (starters aging out):**

- Calais Campbell (DL), age 40 — severity high
- Kelvin Beachum (OL), age 37 — severity high
- Dalvin Tomlinson (DL), age 32 — severity medium
- James Conner (RB), age 31 — severity high
- Budda Baker (DB), age 30 — severity medium

**Recent draft history:** 2024_r1: WR Marvin Harrison Jr. (#4), IDL Darius Robinson (#27) · 2024_r2: CB Max Melton (#43) · 2025_r1: IDL Walter Nolen (#16) · 2025_r2: CB Will Johnson (#47)

### Modal R1 pick(s) from 500-sim MC

**Pick 3** — modal player: **Arvell Reese** (LB)

- Components: bpa=0.535, need=0.45, visit=0.0, intel=0.0, pv_mult=0.612, gm_aff=0.8, **final=0.477**
- Top reasons:
  - **LB is a top roster need** (team_need, magnitude 0.45): Need score contributed 0.45 to the total
  - **LB is a non-premium position** (non_premium_discount, magnitude 0.39): Discounted 39% but still outscored alternatives
  - **GM rarely drafts LB** (gm_aversion, magnitude 0.20): Positional-affinity penalty 0.80x (model picked anyway)

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Arvell Reese | LB | Ohio State | 3 | 0.424 | 3.51 |
| David Bailey | EDGE | Texas Tech | 3 | 0.350 | 2.93 |
| Francis Mauigoa | OT | Miami (FL) | 3 | 0.156 | 15.49 |
| Sonny Styles | LB | Ohio State | 3 | 0.070 | 5.12 |
| Cashius Howell | EDGE | Texas A&M | 29 | 0.060 | 27.47 |
| Ty Simpson | QB | Alabama | 29 | 0.048 | 24.94 |
| Avieon Terrell | CB | Clemson | 29 | 0.036 | 24.94 |
| Max Iheanachor | OT | Arizona State | 30 | 0.020 | 26.13 |

### Analyst/scout archetype notes

- **Pick 3:** Pick 3 faces the best-available-EDGE vs. scheme-fit-QB vs.
cornerstone-OT debate. Given pick value (3 is premium), the archetype is the best EDGE on
the board - this is both need and value. A QB at 3 would be a reach per most analysts because
better QB value exists at Day 2 (Simpson). OT also fits. Ossenfort's trade-down history makes a
move to 5-10 range plausible, in which case target shifts to a specific scheme-fit QB (Simpson
profile - accurate passer with developmental upside).

**Needs (tiered, from team-profile PDF):**

Urgent (4+): QB (real possibility - but at 3 is too rich), EDGE (bottom-5 sacks twice in 3
years - best need-meets-value at 3), OT (OL hasn't progressed enough)
Secondary (3+): IDL
Moderate (2.5): WR

**GM fingerprint:** (Ossenfort, 3 drafts):
Trade tendency: Strong trade-down tendency - 6 trade-downs, 1 trade-up in 2 years.
Heavy accumulator.

Positional affinity (computed): IDL +24.7%, CB +11.0%, EDGE +9.0%
Pattern: Ossenfort is a rebuilder - classic "trade back and accumulate picks"

**Uncertainty flags:** Trade-down probability is HIGH (0.45+)
Full regime change makes scheme predictions uncertain
QB vs best-player-available tension at this exact slot


---

## TEN — Pick 4

**Front office:** GM Mike Borgonzi · HC Robert Saleh (NEW)

**Situation:** 0.176 win% · win-now pressure 0.20 · QB locked (urgency 0.00)

**Cap:** $55.0M space · tier `flush` · dead $8.0M

**Scheme:** saleh_4-3_wide-9 · premium positions: EDGE, CB, S

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| EDGE | 3.75 |
| OT | 3.0 |
| WR | 3.0 |
| RB | 2.5 |
| CB | 1.5 |

**Needs source:** `explicit_user_spec`

**Trade behavior:** trade_up_rate=0.35, trade_down_rate=0.30

**Predictability:** LOW · Capital: high (9 picks total)

**Confirmed visits (3):** Chris Hilton, Dan Villari, Nadame Tucker

**Age cliffs (starters aging out):**

- Kevin Zeitler (OL), age 36 — severity high
- Jihad Ward (LB), age 32 — severity medium
- Corey Levin (OL), age 32 — severity medium
- Calvin Ridley (WR), age 32 — severity medium
- Xavier Woods (DB), age 31 — severity medium
- Sebastian Joseph-Day (DL), age 31 — severity medium

**Recent draft history:** 2024_r1: OL JC Latham (#7) · 2024_r2: IDL T'Vondre Sweat (#38) · 2025_r1: QB Cam Ward (#1) · 2025_r2: EDGE Oluwafemi Oladejo (#52)

### Modal R1 pick(s) from 500-sim MC

**Pick 4** — modal player: **Jeremiyah Love** (RB)

- Components: bpa=0.532, need=0.45, visit=0.0, intel=0.3, pv_mult=1.15, gm_aff=1.0, **final=1.951**
- Top reasons:
  - **RB is a top roster need** (team_need, magnitude 0.45): Need score contributed 0.45 to the total
  - **Analyst intel scripted this pick** (intel, magnitude 0.30): Tier-1 analyst consensus pushed prob 0.30
  - **RB position premium** (positional_value, magnitude 0.15): Position-value multiplier 1.15x (premium slot)

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Jeremiyah Love | RB | Notre Dame | 4 | 0.442 | 6.31 |
| Sonny Styles | LB | Ohio State | 4 | 0.416 | 5.12 |
| Caleb Downs | S | Ohio State | 4 | 0.128 | 7.03 |

### Analyst/scout archetype notes

- **Pick 4:** Pick 4 faces genuine debate between three distinct archetypes:
(1) an elite, explosive RB with pass-catching ability (Ward-weapon argument), (2) a blue-chip
edge rusher or twitchy pass-rushing LB (Saleh/Bradley defensive priority), or (3) a bookend
tackle (OL foundation). The strongest consensus across five analyst mocks favors the RB
archetype, but that arguably reflects "mock inertia" - the newer reasoning pieces (NFL.com,
CBS) explicitly argue for EDGE/OL at this slot because of positional value. The Bradley scheme
specifically suggests the EDGE or rangy LB archetype fits best ideologically; the RB archetype
fits best from a Ward-development standpoint. Both are defensible.

**Needs (tiered, from team-profile PDF):**

Urgent (3.5+): OL (multiple holes), EDGE (Bradley scheme demands leverage rushers;
Johnson II alone insufficient), WR (Ward needs weapons beyond Ridley), RB (Love is the
ultimate weapon for a young QB)
Secondary (2.5-3): CB (Sneed gone, need press-coverage types), S (centerfield specialist
for Cover-3)
Moderate (2): IDL

**GM fingerprint:** (Borgonzi):
Trade tendency: Small sample (2 drafts) - somewhat willing
Positional affinity: Insufficient data
Pattern: Borgonzi comes from KC scouting under Veach - Veach tree is aggressive,
premium-position-focused
Trade-down candidate: Multiple sources confirm TEN is a willing trade-down partner
(Dallas primary suitor)

**Uncertainty flags:** Complete regime change (new HC, new OC, new DC, 2nd-year GM) = maximum
uncertainty
Borgonzi has explicitly said he wants more top-100 picks - trade-down is live
If Cowboys trade up to pick 4, TEN moves back and the calculus changes entirely


---

## NYG — Pick 5, 10

- **Pick 5:** NYG native R1 (4-13 record, 2025)
- **Pick 10:** Acquired from CIN (2026-04-18) for Dexter Lawrence + $28M/1yr ext

**Front office:** GM Joe Schoen · HC John Harbaugh (NEW)

**Situation:** 0.235 win% · win-now pressure 0.20 · QB locked (urgency 0.00)

**Cap:** $18.4M space · tier `flush`

**Scheme:** Michigan / Harbaugh (physical) · premium positions: OL, LB, EDGE

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| LB | 3.75 |
| S | 3.25 |
| IDL | 3.0 |
| WR | 3.0 |
| OT | 2.75 |
| CB | 2.25 |

**Latent / future needs:** WR (2.0), IOL (2.0)

**Needs source:** `explicit_user_spec`

**GM positional affinity** (from 2023-2025 draft history):

- Favors: EDGE +0.29, WR +0.19, QB +0.12
- Avoids: IDL -0.15, LB -0.10, CB -0.09

**Trade behavior:** trade_up_rate=0.30, trade_down_rate=0.70, trade_down_tier=HIGH, trade_down_prob=0.7, reason=two top-10 picks (5 + 10 via Lawrence trade) — capital-rich

**Predictability:** MEDIUM · Capital: medium (8 picks total)

**Confirmed visits (6):** Brenen Thompson, Eli Heidenreich, J.C. Davis, Jaeden Roberts, Logan Taylor, Will Lee III

**Age cliffs (starters aging out):**

- Dexter Lawrence (DEPARTED) (IDL), age 28 — severity high
- Russell Wilson (QB), age 38 — severity high
- Greg Van Roten (OL), age 36 — severity high
- Roy Robertson-Harris (DL), age 33 — severity medium
- Rakeem Nunez-Roches (DL), age 33 — severity medium
- Jermaine Eluemunor (OL), age 32 — severity medium

**Recent draft history:** 2024_r1: WR Malik Nabers (#6) · 2024_r2: CB Tyler Nubin (#47) · 2025_r1: EDGE Abdul Carter (#3), QB Jaxson Dart (#25)

### Modal R1 pick(s) from 500-sim MC

**Pick 5** — modal player: **Caleb Downs** (S)

- Components: bpa=0.534, need=0.45, visit=0.0, intel=0.0, pv_mult=0.712, gm_aff=0.85, **final=0.647**
- Top reasons:
  - **S is a top roster need** (team_need, magnitude 0.45): Need score contributed 0.45 to the total
  - **S is a non-premium position** (non_premium_discount, magnitude 0.29): Discounted 29% but still outscored alternatives
  - **GM rarely drafts S** (gm_aversion, magnitude 0.15): Positional-affinity penalty 0.85x (model picked anyway)

**Pick 10** — modal player: **Mansoor Delane** (CB)

- Components: bpa=0.529, need=0.45, visit=0.0, intel=0.0, pv_mult=1.22, gm_aff=0.8, **final=1.218**
- Top reasons:
  - **CB is a top roster need** (team_need, magnitude 0.45): Need score contributed 0.45 to the total
  - **CB position premium** (positional_value, magnitude 0.22): Position-value multiplier 1.22x (premium slot)
  - **GM rarely drafts CB** (gm_aversion, magnitude 0.20): Positional-affinity penalty 0.80x (model picked anyway)

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Mansoor Delane | CB | LSU | 10 | 0.476 | 9.63 |
| Caleb Downs | S | Ohio State | 5 | 0.364 | 7.03 |
| Sonny Styles | LB | Ohio State | 5 | 0.272 | 5.12 |
| Jeremiyah Love | RB | Notre Dame | 5 | 0.160 | 6.31 |
| Jermod McCoy | CB | Tennessee | 10 | 0.160 | 16.45 |
| Caleb Downs | S | Ohio State | 10 | 0.152 | 7.03 |
| Carnell Tate | WR | Ohio State | 5 | 0.128 | 7.60 |
| Peter Woods | DL | Clemson | 10 | 0.062 | 20.63 |

### Analyst/scout archetype notes

- **Pick 5:** Given Harbaugh's physicality mandate and the cascade of needs,
several archetypes are live: (1) a versatile LB/S hybrid with coverage ability and downhill
physicality - exactly Harbaugh's archetype, (2) an elite safety with ball-hawk ability, (3) a
dominant RB who can be the offensive centerpiece (also fits Harbaugh's run-first DNA), or (4)
a big-bodied WR to pair with Nabers. Schefter intel: "A lot of people think Giants first pick
comes from Columbus" - referencing multiple Ohio State prospects visited. This suggests a
defensive-priority pick.

**Needs (tiered, from team-profile PDF):**

Urgent (3.5-4): WR (Nabers + Dart need WR2), OT (RT Eluemunor unproven full-time),
IDL (if Lawrence traded - catastrophic), IOL (RG unproven)
Secondary (2.5-3): CB (CB2 thin), S, LB depth
Latent: IDL (Lawrence impasse), WR (age at key positions), IOL (RG)

**GM fingerprint:** (Schoen, 4 drafts):
Trade tendency: Moderate (has received "couple of calls" about trading 5 - per his own
statement)
Positional affinity (computed): EDGE +29.0%, WR +19.0% - skill + pass rush heavy
Pattern: Schoen has shown willingness to use multiple picks on same position group (WR
in 2023, OL in 2024)

**Uncertainty flags:** Harbaugh identity question in source data (John vs Jim) - high priority to resolve
Lawrence trade impasse creates moving target for IDL need
Trade-down probability exists but not dominant


---

## CLE — Pick 6, 24

- **Pick 6:** CLE native R1 (3-14 record, 2025)
- **Pick 24:** Acquired from JAX (Trevor Lawrence-era deal)

**Front office:** GM Andrew Berry · HC Todd Monken (NEW)

**Situation:** 0.294 win% · win-now pressure 0.20 · QB watson_locked_ceiling_uncertain (urgency 0.35)

**Cap:** tier `tight` · dead $72.0M

**Scheme:** Monken offense · premium positions: WR, TE, OT

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| WR | 4.0 |
| QB | 3.5 |
| OT | 2.0 |
| EDGE | 1.5 |
| LB | 1.0 |

**Latent / future needs:** QB (2.0)

**Needs source:** `explicit_user_spec`

**GM positional affinity** (from 2023-2025 draft history):

- Favors: LB +0.18, IDL +0.13, S +0.09
- Avoids: WR -0.21, EDGE -0.11, CB -0.09

**Trade behavior:** trade_up_rate=0.50, trade_down_rate=0.50

**Predictability:** LOW · Capital: high (9 picks total)

**Confirmed visits (19):** Akheem Mesidor, Arvell Reese, Blake Miller, Cam Porter, Carnell Tate, Carson Beck, Febechi Nwaiwu, Jack Kelly, Jacob Rodriguez, Joe Royer, Landon Robinson, Lorenzo Styles Jr., Makai Lemon, Markel Bell, Monroe Freeling, Sonny Styles, Ty Simpson, Wade Woodaz, Will Kacmarek

**Age cliffs (starters aging out):**

- Shelby Harris (DL), age 35 — severity high
- Joel Bitonio (OL), age 35 — severity high
- Cornelius Lucas (OL), age 35 — severity high
- DeAndre Carter (WR), age 33 — severity high
- Wyatt Teller (OL), age 32 — severity medium
- Jack Conklin (OL), age 32 — severity medium

**Recent draft history:** 2024_r2: IDL Michael Hall (#54) · 2025_r1: IDL Mason Graham (#5) · 2025_r2: LB Carson Schwesinger (#33), RB Quinshon Judkins (#36)

### Modal R1 pick(s) from 500-sim MC

**Pick 6** — modal player: **Rueben Bain** (EDGE)

- Components: bpa=0.537, need=0.45, visit=0.0, intel=0.0, pv_mult=1.25, gm_aff=0.8, **final=1.011**
- Top reasons:
  - **EDGE is a top roster need** (team_need, magnitude 0.45): Need score contributed 0.45 to the total
  - **EDGE position premium** (positional_value, magnitude 0.25): Position-value multiplier 1.25x (premium slot)
  - **GM rarely drafts EDGE** (gm_aversion, magnitude 0.20): Positional-affinity penalty 0.80x (model picked anyway)

**Pick 24** — modal player: **Emmanuel McNeil-Warren** (S)

- Components: bpa=0.52, need=0.45, visit=0.0, intel=0.0, pv_mult=0.522, gm_aff=1.25, **final=0.627**
- Top reasons:
  - **S is a non-premium position** (non_premium_discount, magnitude 0.48): Discounted 48% but still outscored alternatives
  - **S is a top roster need** (team_need, magnitude 0.45): Need score contributed 0.45 to the total
  - **GM historically favors S** (gm_affinity, magnitude 0.25): Positional-affinity multiplier 1.25x

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Rueben Bain | EDGE | Miami (FL) | 6 | 0.402 | 7.02 |
| Emmanuel McNeil-Warren | S | Toledo | 24 | 0.398 | 25.30 |
| Monroe Freeling | OT | Georgia | 12 | 0.380 | 11.81 |
| Monroe Freeling | OT | Georgia | 6 | 0.314 | 11.81 |
| Spencer Fano | OT | Utah | 20 | 0.240 | 18.72 |
| Francis Mauigoa | OT | Miami (FL) | 20 | 0.222 | 15.49 |
| Anthony Hill Jr. | LB | Texas | 24 | 0.204 | 24.01 |
| Carnell Tate | WR | Ohio State | 6 | 0.130 | 7.60 |

### Analyst/scout archetype notes

- **Pick 6:** Two very different archetypes live: (1) an elite separator WR or
big-bodied X-receiver to give whoever plays QB a legitimate weapon, or (2) a developmental
franchise QB to plan around long-term. Given Berry's historical aggression in trades and the
three-analyst consensus projecting CLE trades down, the most likely scenario is they trade
back to acquire more capital and take WR later. Standing pat at 6 favors WR over QB given class
depth.
- **Pick 24:** If they stand pat at 6 and take WR, pick 24 becomes best
available trench player (tackle or EDGE). If they trade down from 6, pick 24 becomes part of a
broader multi-pick strategy targeting CB/EDGE/OT.

**Needs (tiered, from team-profile PDF):**

Urgent (4+): WR (dead last in receiving TDs - catastrophic), QB (situation genuinely
unresolved)
Secondary (2.5-3): OT (LT long-term despite FA additions - Howard is RT), CB (depth)

Moderate (2): EDGE depth, secondary help

**GM fingerprint:** (Berry):
Trade tendency: Very high trade-down rate - Berry averages 5.2 trades per draft (above
average)
Positional affinity (computed, 7 drafts): LB +18.2%, IDL +13.2%, S +9.3%, OT +8.9% -
defense-heavy with OL emphasis
Pattern: Youngest average draft pick age of any GM - prioritizes developmental upside
over immediate impact. This matters: Berry is more likely than most GMs to take a high-
upside young WR over a polished veteran-ready one.
The Berry affinity data contradicts the WR narrative - his actual pattern is defense-
heavy. Watch for a surprise defensive selection at 6 if the board breaks that way.

**Uncertainty flags:** Trade-down is the modal outcome per multiple analysts (~40% probability)
Berry's computed affinity (defense-heavy) conflicts with obvious WR need - possible
curveball
QB plans genuinely unclear even internally


---

## WAS — Pick 7

**Front office:** GM Adam Peters · HC Dan Quinn

**Situation:** 0.294 win% · win-now pressure 0.20 · QB locked (urgency 0.00)

**Scheme:** quinn_aggressive · premium positions: —

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| WR | 3.5 |
| LB | 2.5 |
| S | 2.0 |
| EDGE | 2.0 |

**Latent / future needs:** WR (2.0), C (2.0)

**Needs source:** `researched_default`

**GM positional affinity** (from 2023-2025 draft history):

- Favors: TE +0.19, QB +0.17, CB +0.16
- Avoids: WR -0.21, EDGE -0.11, LB -0.10

**Trade behavior:** trade_up_rate=0.50, trade_down_rate=0.50

**Predictability:** MEDIUM · Capital: medium (6 picks total)

**Confirmed visits (4):** Alan Herron, Eric Rivers, Keyron Crawford, Mark Gronowski

**Age cliffs (starters aging out):**

- Nick Bellore (LB), age 37 — severity high
- Von Miller (LB), age 37 — severity high
- Bobby Wagner (LB), age 36 — severity high
- Zach Ertz (TE), age 36 — severity high
- Preston Smith (DL), age 34 — severity high
- Jonathan Jones (DB), age 33 — severity high

**Recent draft history:** 2024_r1: QB Jayden Daniels (#2) · 2024_r2: IDL Jer'Zhan Newton (#36), CB Mike Sainristil (#50), TE Ben Sinnott (#53) · 2025_r1: OL Josh Conerly (#29) · 2025_r2: CB Trey Amos (#61)

### Modal R1 pick(s) from 500-sim MC

**Pick 7** — modal player: **Carnell Tate** (WR)

- Components: bpa=0.526, need=0.702, visit=0.0, intel=0.2, pv_mult=1.08, gm_aff=0.8, **final=1.274**
- Top reasons:
  - **WR is a top roster need** (team_need, magnitude 0.70): Need score contributed 0.70 to the total
  - **GM rarely drafts WR** (gm_aversion, magnitude 0.20): Positional-affinity penalty 0.80x (model picked anyway)

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Carnell Tate | WR | Ohio State | 7 | 0.406 | 7.60 |
| Rueben Bain | EDGE | Miami (FL) | 7 | 0.218 | 7.02 |
| Makai Lemon | WR | USC | 7 | 0.158 | 11.44 |
| Caleb Downs | S | Ohio State | 7 | 0.126 | 7.03 |
| Sonny Styles | LB | Ohio State | 7 | 0.092 | 5.12 |

### Analyst/scout archetype notes

- **Pick 7:** Given Daniels' need for weapons and McLaurin's age, the
dominant archetype is an elite separation WR or big-bodied X-receiver to stabilize the passing

game. Alternative: a dynamic LB/S hybrid to continue defensive build. Tertiary: a dominant
RB who can be the offensive spark (Love archetype).

**Needs (tiered, from team-profile PDF):**

Urgent (4+): WR (McLaurin aging + zero WR2 option), EDGE (Quinn always wants pass
rush)
Secondary (3+): OL (Biadasz gone - center thin), CB (Flott gone), S
Latent: WR (McLaurin succession), C (Biadasz gone)

**GM fingerprint:** (Peters, 2 drafts):
Trade tendency: Low (0.15/0.15) - Peters has publicly said "more likely than not staying
at 7"
Positional affinity (computed, 2 drafts - small sample): TE +19.3%, QB +16.7%, CB
+16.0%
Pattern: Peters from SF/Baltimore scouting tree - BPA-leaning

**Uncertainty flags:** Only 6 total picks - cannot afford misses, tends to conservative
Peters publicly stated stay-put preference
Multiple visit signals suggest heavy WR board work (Tate, Lemon, Cooper, Hurst all
visited)


---

## NO — Pick 8

**Front office:** GM Mickey Loomis · HC Kellen Moore

**Situation:** 0.353 win% · win-now pressure 0.20 · QB locked (urgency 0.00)

**Cap:** tier `tight` · dead $50.0M

**Scheme:** staley_3-4 · premium positions: EDGE, WR, CB

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| WR | 4.0 |
| EDGE | 3.5 |
| CB | 3.0 |
| OT | 2.0 |

**Needs source:** `explicit_user_spec`

**GM positional affinity** (from 2023-2025 draft history):

- Favors: OT +0.35, OL +0.35, C +0.25
- Avoids: RB -0.07, TE -0.05, QB -0.05

**Trade behavior:** trade_up_rate=0.95, trade_down_rate=0.00

**Predictability:** MEDIUM · Capital: high (8 picks total)

**Confirmed visits (9):** Elijah Sarratt, Jaeden Roberts, Jalen Stroman, Jude Bowry, Malik Spencer, Mason Reiger, Robert Spears-Jennings, Tywone Malone, Zakee Wheatley

**Age cliffs (starters aging out):**

- Cameron Jordan (LB), age 37 — severity high
- Demario Davis (LB), age 37 — severity high
- Davon Godchaux (DL), age 32 — severity medium
- Alvin Kamara (RB), age 31 — severity high
- Dante Pettis (WR), age 31 — severity medium
- Isaac Yiadom (DB), age 30 — severity medium

**Recent draft history:** 2024_r1: OL Taliese Fuaga (#14) · 2024_r2: CB Kool-Aid McKinstry (#41) · 2025_r1: OL Kelvin Banks (#9) · 2025_r2: QB Tyler Shough (#40)

### Modal R1 pick(s) from 500-sim MC

**Pick 8** — modal player: **Sonny Styles** (LB)

- Components: bpa=0.538, need=0.45, visit=0.0, intel=0.0, pv_mult=0.612, gm_aff=1.0, **final=0.934**
- Top reasons:
  - **LB is a top roster need** (team_need, magnitude 0.45): Need score contributed 0.45 to the total
  - **LB is a non-premium position** (non_premium_discount, magnitude 0.39): Discounted 39% but still outscored alternatives
  - **Post-combine riser** (post_combine_boost, magnitude 0.20): Stage-1 under-rated; boosted 20% to reflect current mocks

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Rueben Bain | EDGE | Miami (FL) | 8 | 0.328 | 7.02 |
| Jeremiyah Love | RB | Notre Dame | 8 | 0.180 | 6.31 |
| Carnell Tate | WR | Ohio State | 8 | 0.118 | 7.60 |
| Arvell Reese | LB | Ohio State | 8 | 0.102 | 3.51 |
| Sonny Styles | LB | Ohio State | 8 | 0.084 | 5.12 |
| Mansoor Delane | CB | LSU | 8 | 0.072 | 9.63 |
| David Bailey | EDGE | Texas Tech | 8 | 0.066 | 2.93 |
| Makai Lemon | WR | USC | 8 | 0.050 | 11.44 |

### Analyst/scout archetype notes

- **Pick 8:** Given Loomis's BPA+premium-position tiebreaker pattern, the
archetype is the highest-graded EDGE or WR the board offers. Loomis takes talent - he
doesn't scheme-reach. If a top-3 EDGE somehow falls to 8, that's the pick. If the WRs are the
cleanest value, that's the pick.

**Needs (tiered, from team-profile PDF):**

Urgent (4+): WR (Olave is only established threat - depth catastrophic), EDGE (Jordan's
future uncertain, Cameron Jordan aging)
Secondary (3+): CB (Taylor gone, nickel hole)
Moderate (2.5-3): IDL depth, OL

**GM fingerprint:** (Loomis, 15+ drafts - largest sample in dataset):
Trade tendency:Famously NEVER trades down - 20 trade-ups, 0 trade-downs since
2011. This is a HARDCODED truth in any trade modeling.
Positional affinity: BPA-heavy with premium position tiebreaker
Pattern: Loomis picks impact players, not need players. Ignores year-to-year positional
trends.

**Uncertainty flags:** Loomis's BPA approach means the specific prospect is very board-dependent
Dead cap creates rebuild vs contend tension


---

## KC — Pick 9, 29

- **Pick 9:** KC native R1 (via 2025 losing season + late-season CB collapse)
- **Pick 29:** Acquired from LAR (Matthew Stafford-era deal)

**Front office:** GM Brett Veach · HC Andy Reid

**Situation:** 0.353 win% · win-now pressure 0.20 · QB locked (urgency 0.00)

**Scheme:** reid_spread · premium positions: CB, WR, EDGE

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| CB | 5.0 |
| WR | 3.5 |
| EDGE | 2.5 |
| OT | 1.5 |

**Needs source:** `explicit_user_spec`

**Trade behavior:** trade_up_rate=0.75, trade_down_rate=0.40

**Predictability:** MEDIUM · Capital: high (9 picks total)

**Confirmed visits (11):** Brandon Cisse, Chandler Rivers, Chris Johnson, Cole Payton, Colton Hood, Demond Claiborne, Jaden Dugger, Kaytron Allen, Keldric Faulk, Louis Moore, Rene Konga

**Age cliffs (starters aging out):**

- Travis Kelce (TE), age 37 — severity high
- Mike Pennel (DL), age 35 — severity high
- Chris Jones (DL), age 32 — severity medium
- Drue Tranquill (LB), age 31 — severity medium
- Kareem Hunt (RB), age 31 — severity high
- Mike Edwards (DB), age 30 — severity medium

**Recent draft history:** 2024_r1: WR Xavier Worthy (#28) · 2024_r2: OL Kingsley Suamataia (#63) · 2025_r1: OL Josh Simmons (#32) · 2025_r2: IDL Omarr Norman-Lott (#63)

### Modal R1 pick(s) from 500-sim MC

**Pick 9** — modal player: **Jordyn Tyson** (WR)

- Components: bpa=0.52, need=0.731, visit=0.0, intel=0.0, pv_mult=1.08, gm_aff=1.0, **final=0.572**
- Top reasons:
  - **WR is a top roster need** (team_need, magnitude 0.73): Need score contributed 0.73 to the total

**Pick 29** — modal player: **Colton Hood** (CB)

- Components: bpa=0.512, need=0.0, visit=0.0, intel=0.0, pv_mult=1.22, gm_aff=1.063, **final=0.651**
- Top reasons:
  - **CB position premium** (positional_value, magnitude 0.22): Position-value multiplier 1.22x (premium slot)

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Jordyn Tyson | WR | Arizona State | 9 | 0.568 | 11.08 |
| Mansoor Delane | CB | LSU | 9 | 0.346 | 9.63 |
| Kadyn Proctor | OT | Alabama | 25 | 0.284 | 22.00 |
| T.J. Parker | EDGE | Clemson | 25 | 0.136 | 22.44 |
| Emmanuel McNeil-Warren | S | Toledo | 25 | 0.120 | 25.30 |
| Jeremiyah Love | RB | Notre Dame | 10 | 0.108 | 6.31 |
| KC Concepcion | WR | Texas A&M | 25 | 0.092 | 24.65 |
| Caleb Lomu | OT | Utah | 25 | 0.084 | 26.42 |

### Analyst/scout archetype notes

- **Pick 9:** Given the acute CB emergency and the WR need, two archetypes
are live: (1) a blue-chip press-man CB with positional flexibility (scheme fit for Spagnuolo), or
(2) a separation WR1 with speed (Reid's ideal). The CB archetype is more urgent; the WR
archetype is more "Mahomes era-defining" in potential impact.
- **Pick 29:** The other of the two. If they take CB at 9, pick 29 targets a speed
WR or big-slot X. If they take WR at 9, pick 29 becomes an outside press CB.

**Needs (tiered, from team-profile PDF):**

Urgent (5+): CB (BOTH starters literally gone - Kohou is slot only)
Secondary (3+): WR (Kelce aging, Brown gone, Worthy inconsistent), EDGE (35 sacks t-
7th fewest, Anudike-Uzomah hamstring issues)
Moderate (2-2.5): IDL (Jones aging succession), OL depth

**GM fingerprint:** (Veach):
Trade tendency: VERY aggressive (0.75 trade-up rate) - Veach openly said this will be a
trade-heavy draft for them
Positional affinity: Premium-position-biased, aggressive trader
Pattern: Veach has explicit history of moving up for specific targets (Pacheco, Sneed,
Worthy trade). Expect in-draft movement.
First top-10 pick since Mahomes 2017 - this alone makes the situation unusual for Veach

**Uncertainty flags:** Mahomes ACL recovery creates uncertainty about full Year 10+ ceiling
Veach's trade aggression means pick 9 specifically could move
Two needs are essentially equal priority - split outcomes


---

## MIA — Pick 11, 30

- **Pick 11:** MIA native R1 (5-12 record, 2025)
- **Pick 30:** Acquired from DEN (Jalen Ramsey / Bradley Chubb-era deal)

**Front office:** GM Jon-Eric Sullivan (NEW) · HC Jeff Hafley (NEW)

**Situation:** 0.412 win% · win-now pressure 0.50 · QB rebuilding (urgency 0.80)

**Cap:** $45.0M space · tier `tight` · dead $30.0M

**Scheme:** Hafley defense · premium positions: CB, S, EDGE

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| WR | 5.0 |
| CB | 4.0 |
| S | 3.0 |
| EDGE | 2.5 |
| QB | 2.0 |

**Latent / future needs:** QB (2.0), OL (2.0)

**Needs source:** `explicit_user_spec`

**Trade behavior:** trade_up_rate=0.25, trade_down_rate=0.50

**Predictability:** LOW · Capital: very_high (11 picks total)

**Confirmed visits (4):** Aamil Wagner, Cyrus Allen, Hezekiah Masses, Isaiah World

**Age cliffs (starters aging out):**

- Darren Waller (TE), age 34 — severity medium
- Rasul Douglas (DB), age 32 — severity medium
- Daniel Brunskill (OL), age 32 — severity medium
- Tyreek Hill (WR), age 32 — severity medium
- Zach Sieler (DL), age 31 — severity medium
- Ashtyn Davis (DB), age 30 — severity medium

**Recent draft history:** 2024_r1: EDGE Chop Robinson (#21) · 2024_r2: OL Patrick Paul (#55) · 2025_r1: IDL Kenneth Grant (#13) · 2025_r2: OL Jonah Savaiinaea (#37)

### Modal R1 pick(s) from 500-sim MC

**Pick 11** — modal player: **Makai Lemon** (WR)

- Components: bpa=0.528, need=0.585, visit=0.0, intel=0.0, pv_mult=1.08, gm_aff=1.0, **final=1.239**
- Top reasons:
  - **WR is a top roster need** (team_need, magnitude 0.59): Need score contributed 0.59 to the total

**Pick 30** — modal player: **Ty Simpson** (QB)

- Components: bpa=0.525, need=0.0, visit=0.0, intel=0.0, pv_mult=1.4, gm_aff=1.0, **final=0.505**
- Top reasons:
  - **QB position premium** (positional_value, magnitude 0.40): Position-value multiplier 1.40x (premium slot)

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Ty Simpson | QB | Alabama | 30 | 0.418 | 24.94 |
| Makai Lemon | WR | USC | 11 | 0.364 | 11.44 |
| Chris Johnson | CB | San Diego State | 30 | 0.296 | 27.17 |
| Carnell Tate | WR | Ohio State | 11 | 0.148 | 7.60 |
| Jeremiyah Love | RB | Notre Dame | 11 | 0.104 | 6.31 |
| Mansoor Delane | CB | LSU | 11 | 0.096 | 9.63 |
| Francis Mauigoa | OT | Miami (FL) | 11 | 0.082 | 15.49 |
| Caleb Downs | S | Ohio State | 11 | 0.052 | 7.03 |

### Analyst/scout archetype notes

- **Pick 11:** Given Haefley's scheme and acute CB need, a long, athletic
press-man CB with Cover-3 experience is the cleanest archetype. Alternative: elite separation
WR1 profile to anchor the rebuild. Either works; both fill catastrophic holes. Low QB probability
here because better value waits.
- **Pick 30:** A second impact skill player (WR2 or TE) OR a high-floor S to
pair with their CB pick. If they trade down (likely given 11 picks), target shifts to Day 2 capital
accumulation.

**Needs (tiered, from team-profile PDF):**

Urgent (4.5+): WR (Waddle AND Hill both gone - only Tyreek replacements), CB
(Fitzpatrick gone plus multiple secondary)
Secondary (3+): S, EDGE, OT (Austin Jackson missed 11 games)
Latent: QB (Willis is placeholder - 2027 franchise QB plan real), OL depth

**GM fingerprint:** (Sullivan): ZERO drafts in role. Use league-average priors. Sullivan
comes from Green Bay scouting tree under Gutekunst - historical Packers pattern is high-RAS
athletes with developmental upside.

**Uncertainty flags:** Brand-new GM AND brand-new HC = highest-variance team in the league
11 picks total - very high trade-down probability at 30 (likely) and even at 11 (possible)
Willis contract means QB is on the table but not forced


---

## DAL — Pick 12, 20

- **Pick 12:** DAL native R1 (7-10 record, 2025)
- **Pick 20:** Acquired from GB in Micah Parsons trade (Sept 2025)

**Front office:** GM Jerry Jones · HC Brian Schottenheimer

**Situation:** 0.441 win% · win-now pressure 0.50 · QB locked (urgency 0.00)

**Scheme:** schottenheimer_pro_style · premium positions: EDGE

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| EDGE | 4.5 |
| CB | 3.5 |
| LB | 3.0 |
| S | 2.0 |
| OT | 1.5 |

**Needs source:** `explicit_user_spec`

**GM positional affinity** (from 2023-2025 draft history):

- Favors: EDGE +0.14, IDL +0.10, TE +0.07
- Avoids: WR -0.09, QB -0.08, RB -0.07

**Trade behavior:** trade_up_rate=0.65, trade_down_rate=0.20, trade_up_tier=HIGH, trade_up_prob=0.7

**Predictability:** LOW · Capital: high (8 picks total)

**Confirmed visits (20):** Beau Stephens, Carnell Tate, Dametrious Crownover, Davison Igbinosun, Drew Shelton, Jordyn Tyson, Joshua Josephs, Kenyon Sadiq, Latrell McCutchin, Makai Lemon, Matthew Hibner, Nick Dawkins, Nick Singleton, Nolan Rucci, Rayshaun Benny, Romello Brinson, Taylen Green, Wesley Williams, Zachariah Branch, Zakee Wheatley

**Age cliffs (starters aging out):**

- Donovan Wilson (DB), age 31 — severity medium
- Kenny Clark (DL), age 31 — severity medium
- Malik Hooker (DB), age 30 — severity medium
- Logan Wilson (LB), age 30 — severity medium
- KaVontae Turpin (WR), age 30 — severity medium

**Recent draft history:** 2024_r1: OL Tyler Guyton (#29) · 2024_r2: IDL Marshawn Kneeland (#56) · 2025_r1: OL Tyler Booker (#12) · 2025_r2: EDGE Donovan Ezeiruaku (#44)

### Modal R1 pick(s) from 500-sim MC

**Pick 12** — modal player: **Keldric Faulk** (EDGE)

- Components: bpa=0.525, need=0.45, visit=0.0, intel=0.0, pv_mult=1.25, gm_aff=1.25, **final=1.56**
- Top reasons:
  - **EDGE is a top roster need** (team_need, magnitude 0.45): Need score contributed 0.45 to the total
  - **EDGE position premium** (positional_value, magnitude 0.25): Position-value multiplier 1.25x (premium slot)
  - **GM historically favors EDGE** (gm_affinity, magnitude 0.25): Positional-affinity multiplier 1.25x

**Pick 20** — modal player: **Spencer Fano** (OT)

- Components: bpa=0.533, need=0.45, visit=0.0, intel=0.0, pv_mult=1.1, gm_aff=1.25, **final=1.93**
- Top reasons:
  - **OT is a top roster need** (team_need, magnitude 0.45): Need score contributed 0.45 to the total
  - **GM historically favors OT** (gm_affinity, magnitude 0.25): Positional-affinity multiplier 1.25x

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Keldric Faulk | EDGE | Auburn | 12 | 0.444 | 16.52 |
| T.J. Parker | EDGE | Clemson | 20 | 0.214 | 22.44 |
| Caleb Downs | S | Ohio State | 6 | 0.114 | 7.03 |
| Akheem Mesidor | EDGE | Miami (FL) | 20 | 0.070 | 17.78 |
| Kenyon Sadiq | TE | Oregon | 20 | 0.070 | 15.09 |
| Kenyon Sadiq | TE | Oregon | 12 | 0.058 | 15.09 |
| Keldric Faulk | EDGE | Auburn | 20 | 0.054 | 16.52 |
| Sonny Styles | LB | Ohio State | 6 | 0.040 | 5.12 |

### Analyst/scout archetype notes

- **Pick 12:** Given the acute defensive collapse and Jerry's
win-now mentality, the archetype is a blue-chip defensive impact player at any level -
specifically a rangy off-ball LB with coverage ability, a long press-CB, or an elite S. Multiple
archetypes fit; Jerry tends to pick the "brightest star" available.
- **Pick 20:** The second defender - likely an EDGE or
secondary player to continue the defensive rebuild. Offensive selection here would be
surprising given needs.

**Needs (tiered, from team-profile PDF):**

Urgent (4.5+): EDGE (Parsons gone, no elite rusher, Gary addition insufficient), CB (251.5
pass yards/game allowed - worst in NFL)
Secondary (3+): LB (second level weak), S (Thompson added but depth thin)
Moderate (2.5): IDL (Williams added but rotation needed)

**GM fingerprint:** (Jones family, 15+ drafts):
Trade tendency: HIGH trade-up rate (0.65) - Jerry's pattern of aggressive moves is well-
documented
Positional affinity (computed): EDGE +14.0%, IDL +9.7%, TE +6.8% - historically trench
and TE heavy
Pattern: Jerry's drafts are famously emotional - he picks players he's "excited about."
Less BPA-rigorous than most GMs.

**Uncertainty flags:** Trade-up scenario is the highest-impact variable in the entire draft - if Cowboys move
up, every pick in top 12 shifts
Jerry's public comments sometimes leak intent - worth monitoring draft week
Parker's first draft as DC - positional value weights are new


---

## LAR — Pick 13

**Front office:** GM Les Snead · HC Sean McVay

**Situation:** 0.882 win% · win-now pressure 0.50 · QB bridge (urgency 0.30)

**Cap:** $8.0M space · tier `tight` · dead $18.0M

**Scheme:** mcvay_spread · premium positions: WR

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| WR | 3.5 |
| OT | 2.5 |
| CB | 2.0 |

**Latent / future needs:** QB (2.0), OT (2.0), WR (2.0)

**Needs source:** `explicit_user_spec`

**GM positional affinity** (from 2023-2025 draft history):

- Favors: C +0.13, IDL +0.13, TE +0.09
- Avoids: EDGE -0.11, LB -0.10, CB -0.09

**Trade behavior:** trade_up_rate=0.11, trade_down_rate=0.89, trade_down_tier=HIGH, trade_down_prob=0.7

**Predictability:** LOW-MEDIUM · Capital: medium (7 picks total)

**Confirmed visits (3):** Gabe Jacas, Isaiah World, Pat Coogan

**Age cliffs (starters aging out):**

- Matthew Stafford (QB), age 38 — severity high
- Rob Havenstein (OL), age 34 — severity medium
- Darious Williams (DB), age 33 — severity high
- Tyler Higbee (TE), age 33 — severity medium
- Ahkello Witherspoon (DB), age 31 — severity medium
- Poona Ford (DL), age 31 — severity medium

**Recent draft history:** 2024_r1: IDL Jared Verse (#19) · 2024_r2: IDL Braden Fiske (#39) · 2025_r2: TE Terrance Ferguson (#46)

### Modal R1 pick(s) from 500-sim MC

**Pick 13** — modal player: **Kenyon Sadiq** (TE)

- Components: bpa=0.524, need=0.45, visit=0.0, intel=0.0, pv_mult=0.95, gm_aff=1.25, **final=1.211**
- Top reasons:
  - **TE is a top roster need** (team_need, magnitude 0.45): Need score contributed 0.45 to the total
  - **GM historically favors TE** (gm_affinity, magnitude 0.25): Positional-affinity multiplier 1.25x
  - **TE is a non-premium position** (non_premium_discount, magnitude 0.05): Discounted 5% but still outscored alternatives

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Jordyn Tyson | WR | Arizona State | 13 | 0.332 | 11.08 |
| Makai Lemon | WR | USC | 13 | 0.268 | 11.44 |
| Kenyon Sadiq | TE | Oregon | 13 | 0.144 | 15.09 |
| Olaivavega Ioane | IOL | Penn State | 13 | 0.094 | 15.51 |
| Makai Lemon | WR | USC | 16 | 0.026 | 11.44 |

### Analyst/scout archetype notes

- **Pick 13:** Given McVay's win-now mandate and Adams' finality, the
primary archetype is a YAC-ready separation WR who can step into the slot or flex. Alternative:
a franchise RT given Havenstein's retirement. Snead's history of trade-down suggests moving
back to add picks is also live.

**Needs (tiered, from team-profile PDF):**

Urgent (3.5-4): WR (Adams 34 final year, Nacua rehab), OT (Havenstein retired - RT
succession)
Secondary (3): LB (second level thin), IDL
Latent: QB (Stafford 38), OT (succession), WR (Adams final year)

**GM fingerprint:** Trade tendency:Ultimate trade-down GM - 25 trade-downs since 2012 (highest in
league). Pick 13 is prime trade-back candidate.
Positional affinity (computed, 14+ drafts):C +13.3%, IDL +13.2%, TE +9.0% - this is a
DIVERGENCE from the "Snead loves WRs" narrative. Snead's historical pattern is
interior trenches + TE.
Pattern: Heavy trader, selective about positional priorities

**Uncertainty flags:** Snead computed affinity diverges from narrative - interior focus, not WR
Trade-down probability is HIGH (0.89 historical rate)
Adams' presence technically reduces WR urgency in 2026 specifically


---

## BAL — Pick 14

**Front office:** GM Eric DeCosta · HC Jesse Minter (NEW)

**Situation:** 0.471 win% · win-now pressure 0.50 · QB locked (urgency 0.00)

**Scheme:** defensive multiple (Minter) · premium positions: EDGE, IDL, CB

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| OT | 3.5 |
| WR | 3.0 |
| EDGE | 2.5 |
| IDL | 2.0 |

**Latent / future needs:** IOL (2.0)

**Needs source:** `explicit_user_spec`

**GM positional affinity** (from 2023-2025 draft history):

- Favors: S +0.15, CB +0.10, LB +0.10
- Avoids: IDL -0.15, QB -0.08, TE -0.06

**Trade behavior:** trade_up_rate=0.50, trade_down_rate=0.50

**Predictability:** LOW-MEDIUM · Capital: very_high (11 picks total)

**Confirmed visits (9):** Beau Stephens, Cash Jones, Denzel Boston, Devin Moore, Emmanuel McNeil-Warren, Haynes King, Justin Jefferson, Travis Burke, Zion Young

**Age cliffs (starters aging out):**

- John Jenkins (DL), age 37 — severity high
- Brent Urban (DL), age 35 — severity high
- Kyle Van Noy (LB), age 35 — severity high
- Ronnie Stanley (OL), age 32 — severity medium
- Derrick Henry (RB), age 32 — severity high
- Patrick Ricard (RB), age 32 — severity high

**Recent draft history:** 2024_r1: CB Nate Wiggins (#30) · 2024_r2: OL Roger Rosengarten (#62) · 2025_r1: SAF Malaki Starks (#27) · 2025_r2: EDGE Mike Green (#59)

### Modal R1 pick(s) from 500-sim MC

**Pick 14** — modal player: **Olaivavega Ioane** (IOL)

- Components: bpa=0.534, need=0.45, visit=0.0, intel=0.0, pv_mult=0.95, gm_aff=0.97, **final=1.212**
- Top reasons:
  - **IOL is a top roster need** (team_need, magnitude 0.45): Need score contributed 0.45 to the total
  - **IOL is a non-premium position** (non_premium_discount, magnitude 0.05): Discounted 5% but still outscored alternatives

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Kenyon Sadiq | TE | Oregon | 14 | 0.428 | 15.09 |
| Olaivavega Ioane | IOL | Penn State | 14 | 0.308 | 15.51 |
| Spencer Fano | OT | Utah | 14 | 0.208 | 18.72 |
| Akheem Mesidor | EDGE | Miami (FL) | 13 | 0.100 | 17.78 |
| Caleb Downs | S | Ohio State | 14 | 0.024 | 7.03 |
| Keldric Faulk | EDGE | Auburn | 13 | 0.022 | 16.52 |
| Monroe Freeling | OT | Georgia | 14 | 0.020 | 11.81 |

### Analyst/scout archetype notes

- **Pick 14:** Because Baltimore historically takes BPA with premium-
position tiebreakers, two distinct archetypes are live: (1) a big-bodied power-slot or contested-
catch WR to complement Flowers and give Lamar a red-zone target, or (2) a versatile OL who
can play center and kick out to tackle (Fano-type profile) to solve both the Linderbaum
replacement and tackle depth issues at once. A third less likely but plausible: a tight end with
inline blocking + seam-stretching receiving ability given Lamar's love of TE usage.

**Needs (tiered, from team-profile PDF):**

Urgent (3.5+): OT (Linderbaum gone - center succession critical; tackle depth also thin),
WR (need hulking complement to Zay Flowers - they lack a true X)
Secondary (3): EDGE depth behind Hendrickson, IDL (Madubuike injury)
Latent: IOL depth (Simpson is one-year stop-gap)

**GM fingerprint:** (DeCosta):
Trade tendency: Low - BAL has NOT moved their R1 pick in 5 consecutive drafts. Near-
zero trade-down probability.
Positional affinity (computed from 7 drafts): S +15.0%, LB +9.7%, EDGE +9.0% -
historically defense-heavy
Pattern: BPA tiebreaker is premium position. Comfortable waiting for the board to come
to them.

**Uncertainty flags:** New HC (Minter) but GM continuity - DeCosta's board dominates
Board is unusually wide at 14 (many defensible archetypes)
Pick 14 is one of the harder R1 picks to predict league-wide


---

## TB — Pick 15

**Front office:** GM Jason Licht · HC Todd Bowles

**Situation:** 0.471 win% · win-now pressure 0.50 · QB locked (urgency 0.00)

**Scheme:** bowles_blitz · premium positions: EDGE, CB, LB

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| EDGE | 3.5 |
| WR | 3.0 |
| CB | 2.5 |
| S | 1.5 |

**Latent / future needs:** WR (1.5)

**Needs source:** `researched_default`

**Trade behavior:** trade_up_rate=0.55, trade_down_rate=0.45

**Predictability:** HIGH · Capital: medium (7 picks total)

**Confirmed visits (11):** Bauer Sharp, Chip Trayanum, Cyrus Allen, Gabe Jacas, Genesis Smith, Justin Jefferson, Kaleb Proctor, Kyle Louis, Mike Washington Jr., Nadame Tucker, Tyler Onyedim

**Age cliffs (starters aging out):**

- Lavonte David (LB), age 36 — severity high
- Mike Evans (WR), age 33 — severity high
- Haason Reddick (LB), age 32 — severity medium
- Dan Feeney (OL), age 32 — severity medium
- Vita Vea (DL), age 31 — severity medium
- Jamel Dean (DB), age 30 — severity medium

**Recent draft history:** 2024_r1: OL Graham Barton (#26) · 2024_r2: LB Chris Braswell (#57) · 2025_r1: WR Emeka Egbuka (#19) · 2025_r2: CB Benjamin Morrison (#53)

### Modal R1 pick(s) from 500-sim MC

**Pick 15** — modal player: **Akheem Mesidor** (EDGE)

- Components: bpa=0.525, need=0.45, visit=0.0, intel=0.0, pv_mult=1.25, gm_aff=1.0, **final=1.261**
- Top reasons:
  - **EDGE is a top roster need** (team_need, magnitude 0.45): Need score contributed 0.45 to the total
  - **EDGE position premium** (positional_value, magnitude 0.25): Position-value multiplier 1.25x (premium slot)

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Akheem Mesidor | EDGE | Miami (FL) | 15 | 0.474 | 17.78 |
| Olaivavega Ioane | IOL | Penn State | 15 | 0.302 | 15.51 |
| Kenyon Sadiq | TE | Oregon | 15 | 0.170 | 15.09 |

### Analyst/scout archetype notes

- **Pick 15:** Given Licht's explicit EDGE mandate and the 4-year sack
drought, the dominant archetype is a disruptive, high-floor EDGE rusher with immediate
pass-rush production ability. Alternative: a seam-stretching TE - Kiper has repeatedly
connected TB to TE prospects, and TB confirmed heavy TE board work. Tertiary: a versatile LB
to replace David's leadership/production.

**Needs (tiered, from team-profile PDF):**

Urgent (5+): EDGE (4 consecutive years without a 10-sack player - Licht said publicly
they "must get more QB pressure")
Secondary (3+): CB (Dean gone, Morrison next up), LB (David retired - institution gone),
WR (Evans gone)
Moderate (2): OL depth

**GM fingerprint:** (Licht, 12+ drafts):
Trade tendency: Moderate (0.30/0.30)
Positional affinity: Premium position tilted, particularly EDGE
Pattern: Licht gets his guy - strong history of sticking with his target

**Uncertainty flags:** New OC (Grizzard) changes offensive scheme
David's retirement is generational loss - may drive emotional pick
Publicly stated EDGE mandate is rare - highest-conviction positional need in the league


---

## DET — Pick 17

**Front office:** GM Brad Holmes · HC Dan Campbell

**Situation:** 0.529 win% · win-now pressure 0.50 · QB locked (urgency 0.00)

**Scheme:** glenn_multiple · premium positions: —

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| OT | 4.5 |
| EDGE | 3.5 |
| S | 2.5 |
| CB | 2.0 |

**Needs source:** `explicit_user_spec`

**GM positional affinity** (from 2023-2025 draft history):

- Favors: EDGE +0.14, IDL +0.10, TE +0.07
- Avoids: CB -0.09, WR -0.09, QB -0.08

**Trade behavior:** trade_up_rate=0.60, trade_down_rate=0.40

**Predictability:** MEDIUM-HIGH · Capital: high (9 picks total)

**Confirmed visits (7):** Bobby Jamison-Travis, Bud Clark, Jadon Canady, Max Klare, Tanner Koziol, Taurean York, Tyreak Sapp

**Age cliffs (starters aging out):**

- Graham Glasgow (OL), age 34 — severity medium
- Arthur Maulet (DB), age 33 — severity high
- Taylor Decker (OL), age 33 — severity medium
- DJ Reader (DL), age 32 — severity medium
- Alex Anzalone (LB), age 32 — severity medium
- Kalif Raymond (WR), age 32 — severity medium

**Recent draft history:** 2024_r1: CB Terrion Arnold (#24) · 2024_r2: CB Ennis Rakestraw (#61) · 2025_r1: IDL Tyleik Williams (#28) · 2025_r2: OL Tate Ratledge (#57)

### Modal R1 pick(s) from 500-sim MC

**Pick 17** — modal player: **Blake Miller** (OT)

- Components: bpa=0.516, need=0.0, visit=0.0, intel=0.0, pv_mult=1.1, gm_aff=0.84, **final=0.463**
- Top reasons:
  - **GM rarely drafts OT** (gm_aversion, magnitude 0.16): Positional-affinity penalty 0.84x (model picked anyway)

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Blake Miller | OT | Clemson | 17 | 0.322 | 24.21 |
| Kadyn Proctor | OT | Alabama | 17 | 0.208 | 22.00 |
| Monroe Freeling | OT | Georgia | 17 | 0.170 | 11.81 |
| Omar Cooper Jr. | WR | Indiana | 17 | 0.086 | 18.71 |
| Olaivavega Ioane | IOL | Penn State | 17 | 0.080 | 15.51 |
| Dillon Thieneman | S | Oregon | 17 | 0.076 | 18.05 |
| Francis Mauigoa | OT | Miami (FL) | 17 | 0.050 | 15.49 |

### Analyst/scout archetype notes

- **Pick 17:** Given the Decker void and LT urgency, the primary archetype is
a bookend franchise LT with pass-protection and run-blocking balance - someone Sewell
can eventually flip tackle sides with. Alternative: a bendy, explosive EDGE rusher given
Holmes' +14% EDGE affinity (STRONGEST single-GM positional signal in the entire dataset).
Both archetypes fit.

**Needs (tiered, from team-profile PDF):**

Urgent (4.5+): OT (Decker released - Borom stop-gap, Sewell could kick to LT, LT
succession critical), EDGE (Holmes' strongest affinity + depth need opposite Hutchinson)
Secondary (3+): CB (Arnold penalty/availability concerns), S (Joseph + Branch recovering
injuries)
Moderate (2): IDL

**GM fingerprint:** (Holmes, 5 drafts):
Trade tendency: Moderate - known for in-draft "curveball" picks (Gibbs Year 1,
Campbell DL Year 2, Williams Year 3). Expect a surprise.
Positional affinity (computed):EDGE +14.0% - STRONGEST single-GM affinity of any
active GM in the entire dataset. This is real signal.
Pattern: Holmes never misses a chance to add a pass rusher. Also values athletic RAS-
tested players. OT affinity also positive.

**Uncertainty flags:** EDGE vs OT tension - both have +3-4 urgency scores

Holmes' historical "curveball" picks mean surprise is on the table
OC change (Morton replaces Johnson) changes offensive scheme slightly


---

## MIN — Pick 18

**Front office:** GM Kwesi Adofo-Mensah · HC Kevin O'Connell

**Situation:** 0.529 win% · win-now pressure 0.50 · QB locked (urgency 0.00)

**Cap:** $15.0M space · tier `tight` · dead $20.0M

**Scheme:** mcvay_spread · premium positions: IDL

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| S | 3.5 |
| IDL | 3.0 |
| EDGE | 2.5 |
| CB | 2.0 |

**Latent / future needs:** S (2.0)

**Needs source:** `researched_default`

**GM positional affinity** (from 2023-2025 draft history):

- Favors: G +0.19, QB +0.12, CB +0.11
- Avoids: IDL -0.15, EDGE -0.11, RB -0.07

**Trade behavior:** trade_up_rate=0.40, trade_down_rate=0.60

**Predictability:** MEDIUM · Capital: high (9 picks total)

**Confirmed visits (5):** Demond Claiborne, Hezekiah Masses, Jonah Coleman, Lance Mason, Rahsul Faison

**Age cliffs (starters aging out):**

- Harrison Smith (DB), age 37 — severity high
- Javon Hargrave (DL), age 33 — severity medium
- Ryan Kelly (OL), age 33 — severity medium
- C.J. Ham (RB), age 33 — severity high
- Eric Wilson (LB), age 32 — severity medium
- Jonathan Allen (DL), age 31 — severity medium

**Recent draft history:** 2024_r1: QB J.J. McCarthy (#10), LB Dallas Turner (#17) · 2025_r1: OL Donovan Jackson (#24)

### Modal R1 pick(s) from 500-sim MC

**Pick 18** — modal player: **Dillon Thieneman** (S)

- Components: bpa=0.531, need=0.45, visit=0.0, intel=0.0, pv_mult=0.95, gm_aff=0.85, **final=0.815**
- Top reasons:
  - **S is a top roster need** (team_need, magnitude 0.45): Need score contributed 0.45 to the total
  - **GM rarely drafts S** (gm_aversion, magnitude 0.15): Positional-affinity penalty 0.85x (model picked anyway)
  - **S is a non-premium position** (non_premium_discount, magnitude 0.05): Discounted 5% but still outscored alternatives

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Dillon Thieneman | S | Oregon | 18 | 0.736 | 18.05 |
| Denzel Boston | WR | Washington | 18 | 0.126 | 24.41 |
| Jermod McCoy | CB | Tennessee | 18 | 0.080 | 16.45 |
| Peter Woods | DL | Clemson | 18 | 0.034 | 20.63 |

### Analyst/scout archetype notes

- **Pick 18:** Given the interior DL emergency, the primary archetype is a
disruptive 3-technique DT or versatile interior defender - ideally with both pass-rush and

run-stopping ability. Alternative: an alpha safety with Flores-scheme versatility (box, deep,
man coverage) given Smith's succession.

**Needs (tiered, from team-profile PDF):**

Urgent (4.5+): IDL (BOTH starters gone - catastrophic), S (Smith retired/uncertain)
Secondary (3+): C (Kelly retired), OL depth, CB
Moderate (2): WR depth

**GM fingerprint:** (Adofo-Mensah, 3 drafts):
Trade tendency: Moderate (0.35/0.30)
Positional affinity (computed, small sample): G +19.0%, QB +11.7%, CB +11.0%
Pattern: Adofo-Mensah is analytics-informed; takes value when the board falls
Important nuance: Organization has "interim GM" dynamics per reporting - O'Connell
has unusual power in draft room. Watch for "shiny offensive toy" possibility.

**Uncertainty flags:** O'Connell having unusual power could override positional value logic
Allen + Hargrave + Kelly + Smith all gone = 4-starter hole, any of which could be 18
Flores scheme places premium on specific archetypes that not all analysts recognize


---

## CAR — Pick 19

**Front office:** GM Dan Morgan · HC Dave Canales

**Situation:** 0.471 win% · win-now pressure 0.50 · QB unknown (urgency 0.40)

**Scheme:** canales_westcoast · premium positions: OL, S, TE

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| OT | 3.5 |
| WR | 3.0 |
| CB | 2.5 |
| IDL | 2.0 |

**Latent / future needs:** QB (1.5)

**Needs source:** `researched_default`

**GM positional affinity** (from 2023-2025 draft history):

- Favors: WR +0.29, RB +0.18, EDGE +0.14
- Avoids: IDL -0.15, LB -0.10, CB -0.09

**Trade behavior:** trade_up_rate=0.50, trade_down_rate=0.50

**Predictability:** LOW-MEDIUM · Capital: medium (7 picks total)

**Confirmed visits (9):** Darrell Jackson Jr., Diego Pavia, Dillon Thieneman, Jack Stonehouse, Jarod Washington, Josiah Trotter, Julian Neal, Justin Joly, Kaelon Black

**Age cliffs (starters aging out):**

- Taylor Moton (OL), age 32 — severity medium
- Nick Scott (DB), age 31 — severity medium
- A'Shawn Robinson (DL), age 31 — severity medium
- David Moore (WR), age 31 — severity medium
- Rico Dowdle (RB), age 28 — severity medium

**Recent draft history:** 2024_r1: WR Xavier Legette (#32) · 2024_r2: RB Jonathon Brooks (#46) · 2025_r1: WR Tetairoa McMillan (#8) · 2025_r2: EDGE Nic Scourton (#51)

### Modal R1 pick(s) from 500-sim MC

**Pick 19** — modal player: **Francis Mauigoa** (OT)

- Components: bpa=0.529, need=0.45, visit=0.0, intel=0.0, pv_mult=1.1, gm_aff=0.84, **final=1.371**
- Top reasons:
  - **OT is a top roster need** (team_need, magnitude 0.45): Need score contributed 0.45 to the total
  - **GM rarely drafts OT** (gm_aversion, magnitude 0.16): Positional-affinity penalty 0.84x (model picked anyway)

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Keldric Faulk | EDGE | Auburn | 19 | 0.286 | 16.52 |
| Francis Mauigoa | OT | Miami (FL) | 19 | 0.196 | 15.49 |
| Olaivavega Ioane | IOL | Penn State | 19 | 0.102 | 15.51 |
| Dillon Thieneman | S | Oregon | 19 | 0.086 | 18.05 |
| Emmanuel McNeil-Warren | S | Toledo | 19 | 0.078 | 25.30 |
| Blake Miller | OT | Clemson | 19 | 0.056 | 24.21 |
| Makai Lemon | WR | USC | 19 | 0.052 | 11.44 |
| Spencer Fano | OT | Utah | 19 | 0.036 | 18.72 |

### Analyst/scout archetype notes

- **Pick 19:** Given Canales' scheme and the interior line emergency, two
archetypes live: (1) a mauler guard or versatile interior OL to stabilize protection for Young, or
(2) a safety with Cover-3 centerfield range to pair with Moehrig. Tertiary: a seam-stretching
TE given Canales' scheme loves TE mismatches.

**Needs (tiered, from team-profile PDF):**

Urgent (4.5+): OL (Ekwonu ACL rehab, Walker stop-gap, no long-term C)
Secondary (3+): S (Moehrig complement needed), WR (McMillan alone - need WR2)
Moderate (2.5): EDGE depth, IDL

**GM fingerprint:** (Morgan, 2 drafts):
Trade tendency: Moderate, small sample
Positional affinity (computed, 2 drafts - noisy): WR +29.0%, RB +18.0%, EDGE +14.0% -
but sample too small for confidence
Pattern: Morgan from Buffalo scouting tree - historical Beane-influenced patterns

**Uncertainty flags:** Small GM sample
Position-run dependency: if Minnesota takes S at 18, Carolina S drops in probability
Young's surprising ascent changes WR urgency


---

## PIT — Pick 21

**Front office:** GM Omar Khan · HC Mike McCarthy (NEW)

**Situation:** 0.588 win% · win-now pressure 0.90 · QB bridge (urgency 0.65)

**Scheme:** mccarthy_west_coast · premium positions: OL, WR

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| OL | 4.0 |
| WR | 3.0 |
| IOL | 2.5 |
| S | 1.5 |
| QB | 1.5 |

**Latent / future needs:** QB (2.0), OT (2.0)

**Needs source:** `researched_default`

**GM positional affinity** (from 2023-2025 draft history):

- Favors: IDL +0.25, QB +0.12, CB +0.11
- Avoids: EDGE -0.11, LB -0.10, RB -0.07

**Trade behavior:** trade_up_rate=0.50, trade_down_rate=0.50

**Predictability:** MEDIUM · Capital: very_high (12 picks total)

**Confirmed visits (6):** Ephesians Prysock, Jeff Caldwell, Kaden Wetjen, Kendrick Law, Khalil Dinkins, Olaivavega Ioane

**Age cliffs (starters aging out):**

- Aaron Rodgers (QB), age 42 — severity high
- Cameron Heyward (DL), age 37 — severity high
- Isaac Seumalo (OL), age 33 — severity medium
- Andrus Peat (OL), age 33 — severity medium
- T.J. Watt (LB), age 32 — severity medium
- Chuck Clark (DB), age 31 — severity medium

**Recent draft history:** 2024_r1: OL Troy Fautanu (#20) · 2024_r2: OL Zach Frazier (#51) · 2025_r1: IDL Derrick Harmon (#21)

### Modal R1 pick(s) from 500-sim MC

**Pick 21** — modal player: **T.J. Parker** (EDGE)

- Components: bpa=0.518, need=0.0, visit=0.0, intel=0.0, pv_mult=1.25, gm_aff=0.8, **final=0.503**
- Top reasons:
  - **EDGE position premium** (positional_value, magnitude 0.25): Position-value multiplier 1.25x (premium slot)
  - **GM rarely drafts EDGE** (gm_aversion, magnitude 0.20): Positional-affinity penalty 0.80x (model picked anyway)

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Omar Cooper Jr. | WR | Indiana | 21 | 0.252 | 18.71 |
| T.J. Parker | EDGE | Clemson | 21 | 0.250 | 22.44 |
| Jermod McCoy | CB | Tennessee | 21 | 0.164 | 16.45 |
| Denzel Boston | WR | Washington | 21 | 0.128 | 24.41 |
| Chris Johnson | CB | San Diego State | 21 | 0.110 | 27.17 |
| Akheem Mesidor | EDGE | Miami (FL) | 21 | 0.084 | 17.78 |

### Analyst/scout archetype notes

- **Pick 21:** Two plausible archetypes: (1) a mauler-style interior OL or
swing tackle who can anchor the line for a decade, or (2) a developmental QB with starter
upside (low at 21, but draft is in Pittsburgh and Khan knows Rodgers is near the end). The OL
archetype is cleaner; the QB archetype requires a specific profile to fall to 21, which most
analysts say is unlikely value-wise.

**Needs (tiered, from team-profile PDF):**

Urgent (4+): OL (47 sacks allowed, Seumalo gone, Broderick Jones LT concern), WR
(Pittman is WR2 - still need WR3 or successor)
Secondary (2.5-3): IOL, S depth, QB (for 2027)
Latent: QB (Rodgers near end), OT (Jones uncertain)

**GM fingerprint:** (Khan):
Trade tendency: Moderate, small sample (4 drafts)
Positional affinity: Limited data - IDL emphasis emerging
Pattern: Khan has shown willingness to acquire veterans via trade (Pittman, Heyward
extensions) - less of a "stick and pick" GM than most

**Uncertainty flags:** New HC McCarthy brings West Coast pass-game principles — scheme fit for current personnel is uncertain. Rodgers decision on 2026 return (as of mid-April: 50-50, leaning yes) swings QB urgency materially.

**2026 context:** McCarthy regime reset. Front-office continuity (Khan).


---

## LAC — Pick 22

**Front office:** GM Joe Hortiz · HC Jim Harbaugh (LAC)

**Situation:** 0.647 win% · win-now pressure 0.90 · QB locked (urgency 0.00)

**Scheme:** harbaugh_power · premium positions: OL, IOL, EDGE

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| IDL | 4.0 |
| EDGE | 3.0 |
| CB | 2.5 |
| IOL | 1.5 |

**Latent / future needs:** EDGE (2.0), OL (2.0)

**Needs source:** `researched_default`

**GM positional affinity** (from 2023-2025 draft history):

- Favors: WR +0.46, RB +0.26, C -0.01
- Avoids: IDL -0.15, EDGE -0.11, LB -0.10

**Trade behavior:** trade_up_rate=0.10, trade_down_rate=0.10

**Predictability:** MEDIUM-HIGH · Capital: low (5 picks total)

**Confirmed visits (10):** Chase Bisontis, Colton Hood, Demond Claiborne, Fernando Mendoza, Harold Perkins, Isaiah World, Jalen Farmer, Kaytron Allen, Michael Heldman, Thaddeus Dixon

**Age cliffs (starters aging out):**

- Khalil Mack (LB), age 35 — severity high
- Tony Jefferson (DB), age 34 — severity high
- Denzel Perryman (LB), age 34 — severity high
- Bud Dupree (LB), age 33 — severity high
- Bradley Bozeman (OL), age 32 — severity medium
- Bobby Hart (OL), age 32 — severity medium

**Recent draft history:** 2024_r1: OL Joe Alt (#5) · 2024_r2: WR Ladd McConkey (#34) · 2025_r1: RB Omarion Hampton (#22) · 2025_r2: WR Tre Harris (#55)

### Modal R1 pick(s) from 500-sim MC

**Pick 22** — modal player: **Avieon Terrell** (CB)

- Components: bpa=0.513, need=0.432, visit=0.0, intel=0.0, pv_mult=1.22, gm_aff=0.8, **final=0.822**
- Top reasons:
  - **CB position premium** (positional_value, magnitude 0.22): Position-value multiplier 1.22x (premium slot)
  - **GM rarely drafts CB** (gm_aversion, magnitude 0.20): Positional-affinity penalty 0.80x (model picked anyway)

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Spencer Fano | OT | Utah | 22 | 0.378 | 18.72 |
| T.J. Parker | EDGE | Clemson | 22 | 0.130 | 22.44 |
| Francis Mauigoa | OT | Miami (FL) | 22 | 0.118 | 15.49 |
| Akheem Mesidor | EDGE | Miami (FL) | 22 | 0.092 | 17.78 |
| Keldric Faulk | EDGE | Auburn | 22 | 0.058 | 16.52 |
| Kenyon Sadiq | TE | Oregon | 22 | 0.052 | 15.09 |
| Olaivavega Ioane | IOL | Penn State | 22 | 0.048 | 15.51 |
| Avieon Terrell | CB | Clemson | 22 | 0.034 | 24.94 |

### Analyst/scout archetype notes

- **Pick 22:** Given Harbaugh's explicit trench-physicality identity and the
60-sack season, the cleanest archetype is a mauler interior OL (guard or center) with road-
grading ability or a bull-rush-first DT to pair with Bosa. Alternative: a bendy, high-floor EDGE
rusher given the 2027 contract cliff.

**Needs (tiered, from team-profile PDF):**

Urgent (4+): OL (LG void specifically, 60 sacks allowed - t-2nd most in NFL), EDGE
(Mack/Dupree/Tuipulotu all expire after 2026)
Secondary (3+): IDL (Tomlinson 32 years old), WR (McDaniel motion offense wants
another playmaker)
Latent: EDGE (all 3 expire after 2026 - succession), OL depth

**GM fingerprint:** (Hortiz):
Trade tendency: Very low (0.10/0.10) - Bengals/Chargers combined 7 trades over last 5
drafts, essentially never move
Positional affinity (computed, 2 drafts - small sample): WR +45.7%, RB +26.3% - but
this is noisy due to sample size
Pattern: Hortiz comes from Baltimore front office under DeCosta - historical Ravens
pattern is BPA with trench emphasis

**Uncertainty flags:** Ansley replaces Minter as DC - scheme details shift
Harbaugh's identity overrides most positional affinity data - expect trench pick
Extremely low trade probability


---

## PHI — Pick 23

**Front office:** GM Howie Roseman · HC Nick Sirianni

**Situation:** 0.647 win% · win-now pressure 0.90 · QB locked (urgency 0.00)

**Cap:** $12.0M space · tier `normal` · dead $15.0M

**Scheme:** fangio_match · premium positions: EDGE, OT, CB, S

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| EDGE | 3.5 |
| OT | 3.0 |
| S | 2.5 |
| LB | 2.0 |
| WR | 1.5 |

**Latent / future needs:** OT (1.5), WR (1.5), TE (2.0)

**Needs source:** `explicit_user_spec`

**GM positional affinity** (from 2023-2025 draft history):

- Favors: IDL +0.23, LB +0.12, WR +0.09
- Avoids: EDGE -0.11, RB -0.07, TE -0.06

**Trade behavior:** trade_up_rate=0.60, trade_down_rate=0.40

**Predictability:** MEDIUM · Capital: high (8 picks total)

**Confirmed visits (6):** Derrick Moore, Garrett Nussmeier, Jack Endries, Luke Altmyer, Marlin Klein, Trebor Pena

**Age cliffs (starters aging out):**

- Lane Johnson (OL), age 36 — severity high
- Za'Darius Smith (LB), age 34 — severity high
- Adoree' Jackson (DB), age 31 — severity medium
- Marcus Epps (DB), age 30 — severity medium
- Zack Baun (LB), age 30 — severity medium
- Saquon Barkley (RB), age 29 — severity medium

**Recent draft history:** 2024_r1: CB Quinyon Mitchell (#22) · 2024_r2: CB Cooper DeJean (#40) · 2025_r1: LB Jihaad Campbell (#31) · 2025_r2: SAF Andrew Mukuba (#64)

### Modal R1 pick(s) from 500-sim MC

**Pick 23** — modal player: **Max Iheanachor** (OT)

- Components: bpa=0.5, need=0.558, visit=0.15, intel=0.0, pv_mult=1.1, gm_aff=0.84, **final=1.103**
- Top reasons:
  - **OT is a top roster need** (team_need, magnitude 0.56): Need score contributed 0.56 to the total
  - **GM rarely drafts OT** (gm_aversion, magnitude 0.16): Positional-affinity penalty 0.84x (model picked anyway)

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Colton Hood | CB | Tennessee | 29 | 0.686 | 28.36 |
| KC Concepcion | WR | Texas A&M | 23 | 0.154 | 24.65 |
| Denzel Boston | WR | Washington | 29 | 0.142 | 24.41 |
| Denzel Boston | WR | Washington | 23 | 0.070 | 24.41 |
| Francis Mauigoa | OT | Miami (FL) | 23 | 0.056 | 15.49 |
| Spencer Fano | OT | Utah | 23 | 0.054 | 18.72 |
| KC Concepcion | WR | Texas A&M | 30 | 0.050 | 24.65 |
| Omar Cooper Jr. | WR | Indiana | 23 | 0.024 | 18.71 |

### Analyst/scout archetype notes

- **Pick 23:** Given Fangio scheme and EDGE need, the cleanest archetype is
a long, bendy EDGE rusher with developmental pass-rush ceiling. Alternative: a bookend OT
with long-term starter upside given the aging line. If AJ Brown is traded closer to draft day,
archetype shifts to elite separation WR.

**Needs (tiered, from team-profile PDF):**

Urgent (3.5-4): EDGE (Sweat gone - NFL.com called this "water the edge farm"), OT
(Johnson age 36, Dickerson/Jurgens recovering injuries)
Secondary (2.5-3): S (Blankenship gone), IOL (Jurgens/Dickerson health concerns)
Latent (2+): WR (AJ Brown trade rumors - if traded, becomes urgent), OT (Johnson
succession), TE (Goedert 2027 expiration)

**GM fingerprint:** (Roseman, 15+ drafts):
Trade tendency: High (0.55 trade-up rate) - Roseman averages 5.6 trades per draft.
Known for tactical moves for specific targets.
Positional affinity (computed, 15+ drafts):LB +11.9%, IDL +6.9%, S +6.1% - this is a
KEY divergence from the "Eagles love OL" narrative. Roseman's actual pattern is
DEFENSE-HEAVY recently. Do not assume OL at 23 just because Eagles traditionally love
OL.

Pattern: Roseman is the best public tactician. Willingness to trade up for specific target is
real.

**Uncertainty flags:** The Roseman affinity data (defense-heavy) contradicts common narrative (OL-heavy)
- key divergence to watch
AJ Brown trade rumor could transform pick 23 into a WR situation
Roseman's trade aggression creates volatility


---

## CHI — Pick 25

**Front office:** GM Ryan Poles · HC Ben Johnson

**Situation:** 0.647 win% · win-now pressure 0.90 · QB locked (urgency 0.00)

**Scheme:** default · premium positions: EDGE, S, IDL, OL

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| EDGE | 5.0 |
| S | 4.0 |
| OT | 3.0 |
| IDL | 1.5 |

**Needs source:** `explicit_user_spec`

**GM positional affinity** (from 2023-2025 draft history):

- Favors: CB +0.11, S +0.05, IDL +0.05
- Avoids: LB -0.10, RB -0.07, OT -0.05

**Trade behavior:** trade_up_rate=0.50, trade_down_rate=0.50

**Predictability:** MEDIUM-HIGH · Capital: medium (7 picks total)

**Confirmed visits (41):** Akheem Mesidor, Anterio Thompson, Antonio Williams, Cole Payton, Dan Villari, Daylen Everette, Deion Burks, Devin Moore, Diego Pavia, Dillon Thieneman, Domonique Orange, Febechi Nwaiwu, Gracen Halton, Jacob Rodriguez, Jager Burton, James Brockermeyer, Jaren Kanak, Jaydn Ott, Jermod McCoy, Jimmy Rolder, Jordan van den Berg, Josh Cuevas, Julian Neal, Karon Prunty, Kayden McDonald, Keionte Scott, Kevin Coleman Jr., Keylan Rutledge, Lee Hunter, Max Iheanachor, Michael Taaffe, Mikail Kamara, Oscar Delp, R Mason Thomas, Robert Spears-Jennings, Sam Hecht, Seth McGowan, Tacario Davis, Tristan Leigh, Zion Young, Zxavian Harris

**Age cliffs (starters aging out):**

- Joe Thuney (OL), age 34 — severity medium
- Grady Jarrett (DL), age 33 — severity medium
- Jalen Reeves-Maybin (LB), age 31 — severity medium
- T.J. Edwards (LB), age 30 — severity medium

**Recent draft history:** 2024_r1: QB Caleb Williams (#1), WR Rome Odunze (#9) · 2025_r1: TE Colston Loveland (#10) · 2025_r2: WR Luther Burden (#39), OL Ozzy Trapilo (#56), EDGE Shemar Turner (#62)

### Modal R1 pick(s) from 500-sim MC

**Pick 25** — modal player: **Kadyn Proctor** (OT)

- Components: bpa=0.523, need=0.216, visit=0.0, intel=0.0, pv_mult=1.1, gm_aff=1.0, **final=0.828**

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Max Iheanachor | OT | Arizona State | 23 | 0.272 | 26.13 |
| T.J. Parker | EDGE | Clemson | 23 | 0.148 | 22.44 |
| Akheem Mesidor | EDGE | Miami (FL) | 23 | 0.116 | 17.78 |
| Keldric Faulk | EDGE | Auburn | 23 | 0.038 | 16.52 |
| Dillon Thieneman | S | Oregon | 23 | 0.024 | 18.05 |

### Analyst/scout archetype notes

- **Pick 25:** Given the EDGE emergency, the primary archetype is a power
edge rusher with consistent pressure-generation - someone who can replace Odeyingbo's
contract while actually producing. Alternative: an alpha free safety with centerfield range
given both safety starters are gone. Tertiary: a center-of-the-box DT to anchor the interior.

**Needs (tiered, from team-profile PDF):**

Urgent (5+): EDGE (Odeyingbo torn ACL + $48M bust, 35 sacks t-7th fewest, only Sweat
reliable)
Secondary (4): S (Brisker + Byard both gone)
Moderate (3): OT (Trapilo ACL, depth thin), IDL
Moderate (2.5): LB (Edmunds gone but Bush added)

**GM fingerprint:** (Poles, 4 drafts):
Trade tendency: Moderate (0.30/0.35)
Positional affinity (computed): CB +11.0%, IDL +4.7%, S +5.0% - defense-leaning with
secondary bias
Pattern: Poles has invested heavily in offense recently (Caleb Williams, DJ Moore trade,
Burden pick) - expect defensive priority in 2026. The "Poles never drafts EDGE"
narrative is actually false - his pattern is CB-forward, not EDGE-avoidant.

**Uncertainty flags:** Ben Johnson's first draft as HC - scheme details shifting
EDGE depth in class determines if they can get starter-caliber at 25 or should reach
Safety class is boom/bust (Downs/Thieneman then dropoff)


---

## BUF — Pick 26

**Front office:** GM Brandon Beane · HC Joe Brady (NEW)

**Situation:** 0.706 win% · win-now pressure 0.90 · QB locked (urgency 0.00)

**Scheme:** Brady offense · premium positions: WR, OT

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| EDGE | 4.0 |
| CB | 3.0 |
| WR | 2.5 |
| IDL | 1.5 |

**Latent / future needs:** EDGE (2.0), CB (2.0)

**Needs source:** `researched_default`

**GM positional affinity** (from 2023-2025 draft history):

- Favors: IDL +0.15, CB +0.11, S +0.05
- Avoids: WR -0.11, LB -0.10, QB -0.08

**Trade behavior:** trade_up_rate=0.60, trade_down_rate=0.40

**Predictability:** MEDIUM · Capital: medium (7 picks total)

**Confirmed visits (24):** A.J. Haulcy, Andre Fuller, Chris Bell, Christen Miller, Dontay Corleone, Gavin Ortega, Germie Bernard, Jack Stonehouse, Jackson Kuwatch, Jaishawn Barham, Jakobe Thomas, Jalon Daniels, Jarod Washington, Jordyn Tyson, Josh Gesky, Justin Joly, Kaleb Elarms-Orr, Kamari Ramsey, Malik Benson, Mansoor Delane, Skyler Bell, Travis Burke, Xavian Sorey Jr., Zane Durant

**Age cliffs (starters aging out):**

- Jordan Poyer (DB), age 35 — severity high
- DaQuan Jones (DL), age 35 — severity high
- Larry Ogunjobi (DL), age 32 — severity medium
- Matt Milano (LB), age 32 — severity medium
- Shaq Thompson (LB), age 32 — severity medium
- Dion Dawkins (OL), age 32 — severity medium

**Recent draft history:** 2024_r2: WR Keon Coleman (#33), SAF Cole Bishop (#60) · 2025_r1: CB Maxwell Hairston (#30) · 2025_r2: IDL T.J. Sanders (#41)

### Modal R1 pick(s) from 500-sim MC

**Pick 26** — modal player: **Kayden McDonald** (DL)

- Components: bpa=0.519, need=0.0, visit=0.0, intel=0.0, pv_mult=1.05, gm_aff=1.25, **final=0.668**
- Top reasons:
  - **GM historically favors DL** (gm_affinity, magnitude 0.25): Positional-affinity multiplier 1.25x

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Kayden McDonald | DL | Ohio State | 26 | 0.412 | 26.96 |
| Cashius Howell | EDGE | Texas A&M | 26 | 0.204 | 27.47 |
| Denzel Boston | WR | Washington | 26 | 0.154 | 24.41 |
| Avieon Terrell | CB | Clemson | 26 | 0.098 | 24.94 |
| Malachi Lawrence | EDGE | UCF | 26 | 0.050 | 28.67 |
| Keldric Faulk | EDGE | Auburn | 26 | 0.034 | 16.52 |
| C.J. Allen | LB | Georgia | 26 | 0.028 | 29.77 |
| Avieon Terrell | CB | Clemson | 25 | 0.024 | 24.94 |

### Analyst/scout archetype notes

- **Pick 26:** Given pick 26 and the class shape, the natural profile is a run-
stuffing interior defender with pass-rush juice (the nose tackle the scheme demands) OR a
long-limbed edge rusher with developmental upside to replace the aging trio. Buffalo at 26
sits exactly in the tier break where top-10 IDL talent is gone but mid-first IDL/EDGE are at their
best value-to-cost ratio. A third archetype: versatile off-ball LB with 3-down coverage ability
to replace Milano's role.

**Needs (tiered, from team-profile PDF):**

Urgent (4+): EDGE (depth behind aging Chubb, Bosa/Epenesa gone), IDL (run D 28th,
need nose tackle anchor for scheme shift)
Secondary (3): LB (Milano replacement), IOL (Edwards gone)
Latent: EDGE succession (Chubb, Mack, Dupree all expire after 2026), CB depth for 2027

**GM fingerprint:** (Beane):
Trade tendency: Moderate - willing to move back for volume when board cooperates
(~35% up, ~40% down)
Positional affinity (computed from 8 drafts): IDL +14.7%, CB +11.0%, S +5.0% - defense-
heavy historical investor
Athletic profile: Above-average RAS preference
Pattern: Aggressive in-trade GM (Diggs trade, Moore trade, Chubb signing) - has shown
willingness to swing big

**Uncertainty flags:** New HC (Brady) makes scheme specifics uncertain
Pick 26 is in a classic tier-break zone - high trade-down probability
Post-Moore trade, WR is NOT a need anymore; model should suppress WR probability


---

## SF — Pick 27

**Front office:** GM John Lynch · HC Kyle Shanahan

**Situation:** 0.706 win% · win-now pressure 0.90 · QB locked (urgency 0.00)

**Cap:** $22.0M space · tier `normal` · dead $12.0M

**Scheme:** shanahan_zone · premium positions: OT, EDGE, WR

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| OT | 4.0 |
| EDGE | 3.5 |
| CB | 2.5 |
| IDL | 2.0 |

**Latent / future needs:** OT (4.0), EDGE (2.0)

**Needs source:** `researched_default`

**Trade behavior:** trade_up_rate=0.60, trade_down_rate=0.40

**Predictability:** MEDIUM-HIGH · Capital: medium (6 picks total)

**Confirmed visits (30):** Akheem Mesidor, Alex Harkey, Antonio Williams, Caleb Douglas, Caleb Lomu, Carver Willis, Chris Brazzell, Chris McClellan, Colbie Young, Cole Wisniewski, Daylen Everette, Denzel Boston, Ephesians Prysock, Harold Perkins, John Michael Gyllenborg, Jordan Hudson, Kadyn Proctor, Kendal Daniels, Keylan Rutledge, Kyle Louis, Malachi Lawrence, Malik Muhammad, Michael Taaffe, Mikail Kamara, Omar Cooper Jr., Romello Height, Travis Burke, Treydan Stukes, Uar Bernard, Zxavian Harris

**Age cliffs (starters aging out):**

- Mike Evans (WR), age 33 — severity medium
- Trent Williams (OL), age 38 — severity high
- Kyle Juszczyk (RB), age 35 — severity high
- Eric Kendricks (LB), age 34 — severity high
- Jake Brendel (OL), age 34 — severity medium
- George Kittle (TE), age 33 — severity medium

**Recent draft history:** 2024_r1: WR Ricky Pearsall (#31) · 2024_r2: CB Renardo Green (#64) · 2025_r1: IDL Mykel Williams (#11) · 2025_r2: IDL Alfred Collins (#43)

### Modal R1 pick(s) from 500-sim MC

**Pick 27** — modal player: **Caleb Lomu** (OT)

- Components: bpa=0.525, need=0.0, visit=0.15, intel=0.0, pv_mult=1.1, gm_aff=1.0, **final=0.731**

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Caleb Lomu | OT | Utah | 27 | 0.560 | 26.42 |
| Max Iheanachor | OT | Arizona State | 27 | 0.234 | 26.13 |
| Cashius Howell | EDGE | Texas A&M | 27 | 0.090 | 27.47 |
| Blake Miller | OT | Clemson | 27 | 0.028 | 24.21 |
| Kadyn Proctor | OT | Alabama | 27 | 0.024 | 22.00 |
| Avieon Terrell | CB | Clemson | 27 | 0.020 | 24.94 |

### Analyst/scout archetype notes

- **Pick 27:** Given Williams' age and the sack drought, two archetypes are
live: (1) a developmental franchise LT to apprentice under Williams, or (2) a high-floor sub-
package pass rusher to add behind/beside Bosa. The OT archetype is more urgent longer-term;
the EDGE archetype is more immediate.

**Needs (tiered, from team-profile PDF):**

Urgent (4.5+): OT (Trent Williams 38 - succession critical), EDGE (dead last in sacks
with 20, Bosa ACL recovery)

Secondary (3+): S (safety depth), IDL (rotation), IOL (Burford gone, interior aging)
Latent: OT (Williams ticking clock), EDGE (behind Bosa thin)

**GM fingerprint:** (Lynch, 8 drafts):
Trade tendency: Moderate (0.25/0.35)
Positional affinity: Historical SF pattern is skill-heavy (WR, TE, RB)
Pattern: Ranked 31st in 2025 draft value per Sharp Football - recent draft performance is
a warning flag. May be overcompensating by reaching for "need" players.

**Uncertainty flags:** Only 4 total picks (among lowest in league)
Lynch's recent draft performance warning
Pick 27 is in contender-zone tier break


---

## HOU — Pick 28

**Front office:** GM Nick Caserio · HC DeMeco Ryans

**Situation:** 0.706 win% · win-now pressure 0.90 · QB locked (urgency 0.00)

**Scheme:** shanahan_zone · premium positions: IDL, CB

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| IDL | 3.5 |
| OT | 3.0 |
| CB | 2.5 |
| LB | 1.5 |

**Needs source:** `researched_default`

**GM positional affinity** (from 2023-2025 draft history):

- Favors: WR +0.12, S +0.12, QB +0.08
- Avoids: IDL -0.15, EDGE -0.11, RB -0.07

**Trade behavior:** trade_up_rate=0.60, trade_down_rate=0.40

**Predictability:** MEDIUM · Capital: high (8 picks total)

**Confirmed visits (8):** Behren Morton, Billy Schrauth, Connor Lew, Ethan Onianwa, Jacob Thomas, Miles Kitselman, Trey Zuhn III, Tyren Montgomery

**Age cliffs (starters aging out):**

- Jimmie Ward (DB), age 35 — severity high
- Trent Brown (OL), age 33 — severity medium
- Danielle Hunter (DL), age 32 — severity medium
- Sheldon Rankins (DL), age 32 — severity medium
- Jakob Johnson (RB), age 32 — severity high
- M.J. Stewart (DB), age 31 — severity medium

**Recent draft history:** 2024_r2: CB Kamari Lassiter (#42), OL Blake Fisher (#59) · 2025_r2: WR Jayden Higgins (#34), OL Aireontae Ersery (#48)

### Modal R1 pick(s) from 500-sim MC

**Pick 28** — modal player: **Chase Bisontis** (IOL)

- Components: bpa=0.518, need=0.0, visit=0.0, intel=0.0, pv_mult=0.95, gm_aff=0.97, **final=0.198**
- Top reasons:
  - **IOL is a non-premium position** (non_premium_discount, magnitude 0.05): Discounted 5% but still outscored alternatives

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Max Iheanachor | OT | Arizona State | 28 | 0.328 | 26.13 |
| Chase Bisontis | IOL | Texas A&M | 28 | 0.248 | 28.00 |
| Kayden McDonald | DL | Ohio State | 28 | 0.136 | 26.96 |
| Avieon Terrell | CB | Clemson | 24 | 0.118 | 24.94 |
| C.J. Allen | LB | Georgia | 28 | 0.114 | 29.77 |
| Peter Woods | DL | Clemson | 28 | 0.108 | 20.63 |
| Caleb Banks | DL | Florida | 28 | 0.036 | 25.83 |
| Christen Miller | DL | Georgia | 28 | 0.030 | 28.00 |

### Analyst/scout archetype notes

- **Pick 28:** Given Ryans' defensive priorities and the OL holes, two
archetypes: (1) an interior OL (guard or center) with plug-and-play ability to immediately
stabilize Stroud's protection, or (2) a penetrating 3-technique DT to continue building the
defensive front. The interior OL archetype is more acutely needed; the IDL archetype is Ryans'
historical preference.

**Needs (tiered, from team-profile PDF):**

Urgent (4+): OL (Howard and Scruggs both gone), WR (Tank Dell health uncertain, need
legit complement)
Secondary (3): IDL (Ryans always adds trench talent), LB depth
Moderate (2-2.5): CB depth

**GM fingerprint:** (Caserio):
Trade tendency: Moderately active (0.30/0.30)
Positional affinity (computed, 5 drafts): WR +12.3%, S +11.7%, QB +8.3% - historically
skill-position investor
Pattern: Caserio is willing to make in-draft trades, often accumulates Day 2/3 picks

**Uncertainty flags:** Ryans' defense-first mindset vs. Caserio's skill-position affinity creates internal tension
OC situation worth monitoring
Pick 28 is in the "contender tier-break" zone

**2026 context:** Will Anderson Jr. signed 3-yr/$150M extension (4/17/26) — highest-paid non-QB contract in NFL history ($134M gtd, through 2030). Combined with Danielle Hunter 1-yr/$40M, EDGE is fully addressed. Texans now cap-tight after WR/DE/CB deals.


---

## NE — Pick 31

**Front office:** GM Eliot Wolf · HC Mike Vrabel

**Situation:** 0.824 win% · win-now pressure 0.90 · QB locked (urgency 0.00)

**Cap:** $50.0M space · tier `flush` · dead $8.0M

**Scheme:** mcdaniels_pro · premium positions: EDGE, OT, WR

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| OT | 4.0 |
| WR | 3.5 |
| EDGE | 3.0 |
| CB | 2.0 |
| TE | 1.5 |

**Latent / future needs:** TE (1.5)

**Needs source:** `researched_default`

**Trade behavior:** trade_up_rate=0.50, trade_down_rate=0.50

**Predictability:** MEDIUM · Capital: very_high (11 picks total)

**Confirmed visits (3):** Malik Spencer, Mason Reiger, Seth McGowan

**Age cliffs (starters aging out):**

- Morgan Moses (OL), age 35 — severity high
- Stefon Diggs (WR), age 33 — severity high
- Hunter Henry (TE), age 32 — severity medium
- Robert Spillane (LB), age 31 — severity medium
- Carlton Davis III (DB), age 30 — severity medium
- Harold Landry III (LB), age 30 — severity medium

**Recent draft history:** 2024_r1: QB Drake Maye (#3) · 2024_r2: WR Ja'Lynn Polk (#37) · 2025_r1: OT Will Campbell (#4) · 2025_r2: RB TreVeyon Henderson (#38)

### Modal R1 pick(s) from 500-sim MC

**Pick 31** — modal player: **C.J. Allen** (LB)

- Components: bpa=0.493, need=0.0, visit=0.0, intel=0.0, pv_mult=1.02, gm_aff=1.0, **final=0.483**

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Blake Miller | OT | Clemson | 31 | 0.374 | 24.21 |
| C.J. Allen | LB | Georgia | 31 | 0.248 | 29.77 |
| Emmanuel McNeil-Warren | S | Toledo | 31 | 0.148 | 25.30 |
| Cashius Howell | EDGE | Texas A&M | 31 | 0.116 | 27.47 |
| Kayden McDonald | DL | Ohio State | 31 | 0.052 | 26.96 |
| Denzel Boston | WR | Washington | 31 | 0.026 | 24.41 |
| Eli Stowers | TE | Vanderbilt | 31 | 0.020 | 31.00 |

### Analyst/scout archetype notes

- **Pick 31:** Pick 31 is a fifth-year-option pivot slot. Given Maye is locked and
playing well, the archetype should be either a bookend tackle with pass-protection ceiling
(protect the franchise QB long-term) OR a long, bendy edge rusher (Chaisson replacement).
Both fit Vrabel's "sturdy and physical" identity. WR is possible but less likely at this specific slot
because WR options better fit day 2.

**Needs (tiered, from team-profile PDF):**

Urgent (4+): EDGE (Chaisson gone, 35 sacks t-7th fewest), OT (Morgan Moses
succession, Vera-Tucker on prove-it deal), WR (Diggs gone, need legit WR2 for Maye)
Secondary (3): DL rotation, C (Bradbury gone)
Latent: TE (Hunter Henry final contract year)

**GM fingerprint:** (Wolf):
Trade tendency: Near league-average, modest sample (3 drafts)
Positional affinity: Small sample - defaults to Wolf family scouting (Packers/Browns
tree): prioritizes trenches and athletic profile
Pattern: Has shown willingness to trade mid-round picks for players but hasn't made bold
R1 moves

**Uncertainty flags:** Small sample on Wolf - predictions have wider intervals
Pick 31 is prime trade-back territory (fifth-year-option deadline)

Eleven total picks means they can afford to trade back and add volume


---

## SEA — Pick 32

**Front office:** GM John Schneider · HC Mike Macdonald

**Situation:** 0.824 win% · win-now pressure 0.90 · QB locked (urgency 0.00)

**Scheme:** macdonald_multiple · premium positions: —

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| RB | 4.0 |
| CB | 3.0 |
| EDGE | 2.5 |
| OL | 1.5 |

**Needs source:** `researched_default`

**Trade behavior:** trade_up_rate=0.35, trade_down_rate=0.65, trade_down_tier=HIGH, trade_down_prob=0.7

**Predictability:** LOW · Capital: low (4 picks total)

**Confirmed visits (4):** Brandon Cleveland, Chip Trayanum, Colbie Young, Keyshawn James-Newby

**Age cliffs (starters aging out):**

- Jarran Reed (DL), age 34 — severity high
- DeMarcus Lawrence (LB), age 34 — severity high
- Leonard Williams (DL), age 32 — severity medium
- Uchenna Nwosu (LB), age 30 — severity medium
- Brady Russell (RB), age 28 — severity medium

**Recent draft history:** 2024_r1: IDL Byron Murphy (#16) · 2025_r1: OT Grey Zabel (#18) · 2025_r2: SAF Nick Emmanwori (#35), TE Elijah Arroyo (#50)

### Modal R1 pick(s) from 500-sim MC

**Pick 32** — modal player: **Jadarian Price** (RB)

- Components: bpa=0.484, need=0.45, visit=0.0, intel=0.0, pv_mult=0.55, gm_aff=1.0, **final=0.216**
- Top reasons:
  - **RB is a top roster need** (team_need, magnitude 0.45): Need score contributed 0.45 to the total
  - **RB is a non-premium position** (non_premium_discount, magnitude 0.45): Discounted 45% but still outscored alternatives

### Top prospects whose most-likely R1 landing = this team

| Player | Pos | School | Pick | P(landing) | Mean pick |
|---|---|---|---|---|---|
| Jadarian Price | RB | Notre Dame | 32 | 0.396 | 32.00 |
| Chris Johnson | CB | San Diego State | 32 | 0.132 | 27.17 |
| Colton Hood | CB | Tennessee | 32 | 0.128 | 28.36 |
| Denzel Boston | WR | Washington | 32 | 0.052 | 24.41 |
| Kayden McDonald | DL | Ohio State | 32 | 0.050 | 26.96 |
| Avieon Terrell | CB | Clemson | 32 | 0.050 | 24.94 |
| T.J. Parker | EDGE | Clemson | 32 | 0.040 | 22.44 |
| Malachi Lawrence | EDGE | UCF | 32 | 0.040 | 28.67 |

### Analyst/scout archetype notes

- **Pick 32:** Given Macdonald's preference for versatile DBs and the acute
RB/OL needs, the archetype options are: (1) a three-down RB with receiving ability to replace
Walker's production, (2) a versatile safety with Cover-2/Cover-3 range, or (3) a press-capable
CB. Schneider's trade-down history (24 trade-downs) plus only 4 total picks strongly suggests
trade-down is likely to add Day 2 capital.

**Needs (tiered, from team-profile PDF):**

Urgent (5): RB (Walker gone, Charbonnet ACL - no proven RB)
Secondary (4): RG (Bradford gone - starting hole), CB (Woolen gone)
Moderate (3): EDGE (Mafe gone), S

**GM fingerprint:** (Schneider, 16+ drafts):
Trade tendency: HEAVY trade-down - 24 career trade-downs, 13 trade-ups. Pick 32 is
classic slide-back spot.
Positional affinity: Defense-heavy historical pattern
Pattern: Schneider specializes in accumulating value late in drafts

**Uncertainty flags:** Trade-down probability is HIGH (0.65) given only 4 picks
Super Bowl champion status means roster is deep; luxury pick options exist
Darnold's extension absolutely blocks QB - model must respect this hard constraint


---

## ATL — Pick — (no R1)

**Front office:** GM Terry Fontenot · HC Raheem Morris

**Situation:** 0.471 win% · win-now pressure 0.50 · QB locked (urgency 0.00)

**Scheme:** shanahan_zone · premium positions: WR, OT, EDGE

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| EDGE | 4.0 |
| CB | 3.0 |
| OT | 2.5 |
| IDL | 1.5 |

**Latent / future needs:** QB (1.5)

**Needs source:** `researched_default`

**GM positional affinity** (from 2023-2025 draft history):

- Favors: EDGE +0.22, TE +0.05, RB +0.04
- Avoids: WR -0.10, CB -0.09, OT -0.05

**Trade behavior:** trade_up_rate=0.50, trade_down_rate=0.50

**Predictability:** LOW · Capital: low (5 picks total)

**Confirmed visits (17):** Arvell Reese, Avery Smith, Brenen Thompson, Caleb Tiernan, Chris McClellan, Derrick Moore, Drew Stevens, Germie Bernard, Jack Strand, Josh Cameron, Kaleb Proctor, Reggie Virgil, Treydan Stukes, Ty Simpson, Tyler Onyedim, Zachariah Branch, Zavion Thomas

**Age cliffs (starters aging out):**

- David Onyemata (DL), age 34 — severity high
- Leonard Floyd (DL), age 34 — severity high
- Jake Matthews (OL), age 34 — severity medium
- Kaden Elliss (LB), age 31 — severity medium

**Recent draft history:** 2024_r1: QB Michael Penix (#8) · 2024_r2: IDL Ruke Orhorhoro (#35) · 2025_r1: EDGE Jalon Walker (#15), EDGE James Pearce (#26)

### Modal R1 pick(s) from 500-sim MC

_No R1 pick; Stage 2 sim operates in R1 only. Day-2 targets not modeled here._

### Top prospects whose most-likely R1 landing = this team

_No R1 picks attributed to this team in the 500-sim MC._

### Analyst/scout archetype notes

- **Pick 48:** Day 2 archetype - an interior OL with versatility or a second-
level defender (LB or S) with athletic upside.

**Needs (tiered, from team-profile PDF):**

Urgent (4+): WR (London needs real WR2 - Dotson/Zaccheaus are WR3/4 talent), OT
(McGary retired)
Secondary (3): EDGE (Pearce uncertainty), CB, IDL
Moderate: Defensive depth

**GM fingerprint:** (Fontenot, 5 drafts):
Trade tendency: Moderate
Positional affinity (computed): EDGE +22.3%, TE +5.4%, RB +4.1% - Fontenot loves pass
rushers
Pattern: Fontenot has a strong EDGE affinity - expect them to hunt for pass rush even
without R1

**Uncertainty flags:** No R1 reduces coverage
QB competition creates offensive uncertainty


---

## CIN — Pick — (no R1)

**Front office:** GM Duke Tobin · HC Zac Taylor

**Situation:** 0.353 win% · win-now pressure 0.20 · QB locked (urgency 0.00)

**Scheme:** golden_hybrid · premium positions: CB, LB, EDGE, S

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| CB | 4.5 |
| S | 3.0 |
| EDGE | 2.0 |
| LB | 1.5 |

**Needs source:** `explicit_user_spec`

**GM positional affinity** (from 2023-2025 draft history):

- Favors: EDGE +0.11, OT +0.06, QB +0.03
- Avoids: RB -0.07, TE -0.06, S -0.05

**Trade behavior:** trade_up_rate=0.05, trade_down_rate=0.05

**Predictability:** MEDIUM-HIGH · Capital: high (7 picks total)

**Confirmed visits (49):** Anterio Thompson, Anthony Hill Jr., Athan Kaliakmanis, Austin Barber, Avieon Terrell, Barion Brown, Behren Morton, Caleb Banks, Caleb Downs, Caleb Lomu, Cam Porter, Cashius Howell, Dani Dennis-Sutton, David Bailey, De'Zhaun Stribling, DeMonte Capehart, Dontay Corleone, Emmanuel McNeil-Warren, Emmanuel Pregnon, Francis Mauigoa, Jacob Rodriguez, Jake Golday, Jalon Kilgore, Jeremiah Wright, Jeremiyah Love, Jermod McCoy, Jimmy Rolder, Joe Royer, Jordan van den Berg, Josiah Trotter, Jude Bowry, Kaelon Black, Kapena Gushiken, Kayden McDonald, Keionte Scott, Landon Robinson, Mansoor Delane, Markel Bell, Nate Boerkircher, Peter Woods, Rueben Bain, Skyler Thomas, Sonny Styles, Spencer Fano, T.J. Parker, Ted Hurst, Trey Moore, Tristan Leigh, Zane Durant

**Age cliffs (starters aging out):**

- Joe Flacco (QB), age 41 — severity high
- Ted Karras (OL), age 33 — severity medium
- Lucas Patrick (OL), age 33 — severity medium
- Trey Hendrickson (DL), age 32 — severity medium
- B.J. Hill (DL), age 31 — severity medium
- Oren Burks (LB), age 31 — severity medium

**Recent draft history:** 2024_r1: OL Amarius Mims (#18) · 2024_r2: IDL Kris Jenkins (#49) · 2025_r1: EDGE Shemar Stewart (#17) · 2025_r2: LB Demetrius Knight (#49)

### Modal R1 pick(s) from 500-sim MC

_No R1 pick; Stage 2 sim operates in R1 only. Day-2 targets not modeled here._

### Top prospects whose most-likely R1 landing = this team

_No R1 picks attributed to this team in the 500-sim MC._

**Needs (tiered, from team-profile PDF):**

Urgent (4.5+): CB (Taylor-Britt gone, CB2 wide open, new scheme demands coverage
talent)
Secondary (3+): S, LB (second level weak - Golden wants rangy LBs), EDGE
(Hendrickson hole unfilled)
Moderate (2): IDL depth (Allen is aging)

**GM fingerprint:** (Tobin):
Trade tendency: Extremely low - Bengals + Chargers combined for just 7 trades over last
5 drafts
Positional affinity (computed from 9 drafts): EDGE +11.2%, OT +5.8% - strong trench
orientation

Pattern: Famous for staying put. Willingness to trade up is hypothetically discussed (pick
5 for Styles) but historical base rate is near zero.

**Uncertainty flags:** New DC (Golden) changes positional value weightings from prior years
Potential McCoy decision: if available, his torn ACL (missed all 2025) creates medical-
discount calculus that could override "best CB available" logic
Tobin historically hates trades - if they're mocked into a trade-up, treat skeptically

**2026 context:** Traded pick 10 to NYG for Dexter Lawrence 2026-04-18. Bengals now a Day 2 team. IDL need resolved by Lawrence acquisition. Remaining priority: CB / S / EDGE depth.


---

## DEN — Pick — (no R1)

**Front office:** GM George Paton · HC Sean Payton

**Situation:** 0.824 win% · win-now pressure 0.90 · QB locked (urgency 0.00)

**Scheme:** payton_westcoast · premium positions: RB, TE, OL, WR

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| WR | 3.0 |
| CB | 3.0 |
| EDGE | 2.5 |
| S | 2.0 |

**Latent / future needs:** RB (2.0), TE (2.0)

**Needs source:** `researched_default`

**GM positional affinity** (from 2023-2025 draft history):

- Favors: RB +0.26, QB +0.08, CB +0.08
- Avoids: IDL -0.15, EDGE -0.11, TE -0.06

**Trade behavior:** trade_up_rate=0.50, trade_down_rate=0.50

**Predictability:** MEDIUM · Capital: medium (7 picks total)

**Confirmed visits (29):** Adam Randall, Avieon Terrell, Bryce Boettcher, Caden Barnett, Caleb Tiernan, Cole Wisniewski, Dasan McCullough, Eli Stowers, Emmett Johnson, Evan Beerntsen, Gavin Ortega, Jack Kelly, Jadarian Price, Jaishawn Barham, Jeremiah Wright, Jonah Coleman, Josh Gesky, Kamari Ramsey, Keagen Trost, Kenyon Sadiq, Max Klare, Micah Morris, Monroe Freeling, Namdi Obiazor, Nick Barrett, Oscar Delp, Wade Woodaz, Wesley Williams, Zach Durfee

**Age cliffs (starters aging out):**

- Garett Bolles (OL), age 34 — severity medium
- Michael Burton (RB), age 34 — severity high
- Alex Singleton (LB), age 33 — severity high
- Evan Engram (TE), age 32 — severity medium
- D.J. Jones (DL), age 31 — severity medium
- Courtland Sutton (WR), age 31 — severity medium

**Recent draft history:** 2024_r1: QB Bo Nix (#12) · 2025_r1: CB Jahdae Barron (#20) · 2025_r2: RB RJ Harvey (#60)

### Modal R1 pick(s) from 500-sim MC

_No R1 pick; Stage 2 sim operates in R1 only. Day-2 targets not modeled here._

### Top prospects whose most-likely R1 landing = this team

_No R1 picks attributed to this team in the 500-sim MC._

### Analyst/scout archetype notes

- **Pick 62:** No R1. At 62, the archetype becomes a mid-round RB with
three-down upside or a mismatch TE (classic Payton joker). DB depth also live.

**Needs (tiered, from team-profile PDF):**

Urgent (4.5+): RB (Dobbins injured again, Charbonnet ACL, Walker III gone -
catastrophic backfield)
Secondary (3): IDL (Franklin-Myers gone), TE (Engram final year), LB (Greenlaw gone)
Latent: RB (depth), TE (succession)

**GM fingerprint:** (Paton):
Trade tendency: Moderate
Positional affinity (computed): RB +26.3% (one of the highest RB affinities in the league),
CB +7.7% - Paton invests in skill and DBs
Pattern: Paton's RB affinity is notable given the team's need - a strong pre-indicator that
RB is likely

**Uncertainty flags:** No R1 reduces the stakes of analyst coverage
Payton's unique positional preferences don't always follow convention


---

## GB — Pick — (no R1)

**Front office:** GM Brian Gutekunst · HC Matt LaFleur (GB)

**Situation:** 0.559 win% · win-now pressure 0.50 · QB locked (urgency 0.00)

**Scheme:** shanahan_zone · premium positions: EDGE, IDL, CB, OL

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| CB | 3.5 |
| S | 2.5 |
| IDL | 2.0 |
| OT | 1.5 |

**Needs source:** `researched_default`

**Trade behavior:** trade_up_rate=0.50, trade_down_rate=0.50

**Predictability:** LOW · Capital: high (8 picks total)

**Confirmed visits (6):** Bobby Jamison-Travis, Darrell Jackson Jr., Ethan Onianwa, Jacob Thomas, TJ Quinn, Tyre West

**Age cliffs (starters aging out):**

- Josh Jacobs (RB), age 28 — severity medium

**Recent draft history:** 2024_r1: OL Jordan Morgan (#25) · 2024_r2: LB Edgerrin Cooper (#45), CB Javon Bullard (#58) · 2025_r1: WR Matthew Golden (#23) · 2025_r2: OT Anthony Belton (#54)

### Modal R1 pick(s) from 500-sim MC

_No R1 pick; Stage 2 sim operates in R1 only. Day-2 targets not modeled here._

### Top prospects whose most-likely R1 landing = this team

_No R1 picks attributed to this team in the 500-sim MC._

### Analyst/scout archetype notes

- **Pick 52:** No R1. At 52, the archetype is a high-RAS athlete at defensive
line or linebacker - Gutekunst's signature.

**Needs (tiered, from team-profile PDF):**

Urgent (4+): EDGE (depth behind Parsons), IDL (Clark gone, Hargrave is short-term
bridge), OL (Jenkins gone, tackle depth thin)
Secondary (3): CB (Valentine's tackling struggles)
Moderate (2.5): WR (Doubs gone)

**GM fingerprint:** (Gutekunst, 8 drafts):
Trade tendency: Moderate

Positional affinity (computed): Strongly athleticism-biased - highest average RAS in
league among drafted players. Not position-specific but profile-specific.
Pattern: Gutekunst rarely takes WRs in R1 (historical data). Defense and trenches
dominate. High athletic testing thresholds.

**Uncertainty flags:** No R1 = Day 2 variance
Hafley departure + new DC (Mason) changes defensive positional weights

**Roster depth note:** Age-cliff table is sparse by design — GB has one of the youngest rosters in the NFL. Post-Parsons-trade (sent Micah Parsons + 2026 R1 to DAL for Rashan Gary + picks), the edge room is thinned; EDGE now a quiet priority.


---

## IND — Pick — (no R1)

**Front office:** GM Chris Ballard · HC Shane Steichen

**Situation:** 0.471 win% · win-now pressure 0.50 · QB bridge_with_developmental (urgency 0.65)

**Scheme:** anarumo_pressure · premium positions: EDGE, LB, S

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| QB | 3.5 |
| OT | 2.5 |
| CB | 2.0 |
| EDGE | 2.0 |
| WR | 1.5 |

**Needs source:** `researched_default`

**GM positional affinity** (from 2023-2025 draft history):

- Favors: IDL +0.15, WR +0.09, TE +0.04
- Avoids: LB -0.10, CB -0.09, OT -0.05

**Trade behavior:** trade_up_rate=0.25, trade_down_rate=0.75

**Predictability:** LOW · Capital: medium (7 picks total)

**Confirmed visits (8):** Adam Randall, Charles Demmings, Garrett Nussmeier, Haynes King, Jackson Kuwatch, Jayden Williams, Jerand Bradley, Trey Zuhn III

**Age cliffs (starters aging out):**

- Grover Stewart (DL), age 33 — severity medium
- DeForest Buckner (DL), age 32 — severity medium
- Kenny Moore II (DB), age 31 — severity medium
- Tyquan Lewis (DL), age 31 — severity medium
- Charvarius Ward (DB), age 30 — severity medium
- Germaine Pratt (LB), age 30 — severity medium

**Recent draft history:** 2024_r1: IDL Laiatu Latu (#15) · 2024_r2: WR Adonai Mitchell (#52) · 2025_r1: TE Tyler Warren (#14) · 2025_r2: EDGE JT Tuimoloau (#45)

### Modal R1 pick(s) from 500-sim MC

_No R1 pick; Stage 2 sim operates in R1 only. Day-2 targets not modeled here._

### Top prospects whose most-likely R1 landing = this team

_No R1 picks attributed to this team in the 500-sim MC._

### Analyst/scout archetype notes

- **Pick 47:** No R1 pick. At 47 the archetype is a downhill LB with coverage
ability OR a powerful sub-package EDGE rusher. Day 2 is about roster-complement players for
Ballard.

**Needs (tiered, from team-profile PDF):**

Urgent (4+): EDGE (aging Paye, no elite rusher), LB (no R1 pick means can't address this
at top of draft)

Secondary (3+): S (aging room), OL depth
Moderate: WR (Pittman replacement), CB depth behind Gardner

**GM fingerprint:** (Ballard):
Trade tendency: Heavy trade-down (15 trade-downs, 5 trade-ups over 8 drafts - one of
the most trade-down-heavy GMs)
Positional affinity (computed): IDL +14.7%, WR +9.0% - trench-heavy historical pattern
Pattern: Classic accumulator. Without R1 pick, likely to trade back further from 47 to add
volume.

**Uncertainty flags:** No R1 pick = less analyst coverage = more uncertain projections
Recent Gardner trade reshapes positional needs


---

## JAX — Pick — (no R1)

**Front office:** GM James Gladstone · HC Liam Coen

**Situation:** 0.765 win% · win-now pressure 0.90 · QB locked (urgency 0.00)

**Scheme:** Coen offense · premium positions: WR, OT

**Scored roster needs** (higher = more urgent):

| Pos | Score |
|---|---|
| OL | 3.5 |
| WR | 3.0 |
| IDL | 2.5 |
| CB | 1.5 |

**Needs source:** `researched_default`

**Trade behavior:** trade_up_rate=0.35, trade_down_rate=0.30

**Predictability:** LOW · Capital: very_high (11 picks total)

**Confirmed visits (4):** Cole Payton, Devon Marshall, Louis Moore, Parker Brailsford

**Age cliffs (starters aging out):**

- Arik Armstead (DL), age 33 — severity medium
- Eric Murray (DB), age 32 — severity medium
- Dennis Gardeck (LB), age 32 — severity medium
- Johnny Mundt (TE), age 32 — severity medium
- Jourdan Lewis (DB), age 31 — severity medium
- Andrew Wingard (DB), age 30 — severity medium

**Recent draft history:** 2024_r1: WR Brian Thomas (#23) · 2024_r2: IDL Maason Smith (#48) · 2025_r1: WR Travis Hunter (#2)

### Modal R1 pick(s) from 500-sim MC

_No R1 pick; Stage 2 sim operates in R1 only. Day-2 targets not modeled here._

### Top prospects whose most-likely R1 landing = this team

_No R1 picks attributed to this team in the 500-sim MC._

### Analyst/scout archetype notes

- **Pick 56:** A three-down LB with coverage versatility (Lloyd
replacement) or a power-edge rusher with inside/outside versatility. Mid-round Day 2 gives
them starter-caliber options at either spot.

**Needs (tiered, from team-profile PDF):**

Urgent (4.5+): LB (Lloyd gone, no viable starter replacement), EDGE (Hines-Allen alone,
27th in sacks)
Secondary (3): IDL, S
Moderate: OL depth

**GM fingerprint:** (Gladstone):
Trade tendency: Small sample, modest activity
Positional affinity: Insufficient data (2 drafts)
Pattern: New GM with Rams-scouting-tree background - typically values RAS-tested
athletes and positional versatility

**Uncertainty flags:** Small GM sample
No R1 = focus on Day 2 which is wider variance

**Hunter (WR/CB) usage note:** Travis Hunter (2025 #2 overall) split WR/CB usage remains unresolved into 2026. Shapes positional need board: if Hunter plays majority CB, WR becomes acute; if majority WR, CB2 opposite Lloyd becomes acute. Coen has signalled 'both'.

