"""Deep research patch — 2026-04-20.

Sources:
  - nfl.com 2026-nfl-draft-order-round-1-needs-for-all-32-teams
  - walterfootball.com ProspectMeetingsByTeam2026 (top-30 visits tracker)
  - profootballnetwork.com (Tyson injury slide, Banks foot injury)
  - atozsports.com (KC trade-up tendencies, per-team intel)

Rebuilds each team's roster_needs from the authoritative NFL.com top-5
and MERGES all pre-draft visit names from Walter Football into each
team's visit_signals.confirmed_visits. Also flags Tyson and Banks
medical concerns at the top of their team-fit deltas.

Goal: make each team profile as rich as analyst knowledge allows so the
independent model converges toward consensus via reasoning, not by
consuming analyst picks.
"""
import json, shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
AGENTS_P = ROOT / "data/features/team_agents_2026.json"

def load(p): return json.loads(p.read_text(encoding="utf-8"))
def save(p, obj):
    bak = p.with_suffix(".pre_deep_research_bak.json")
    if p.exists() and not bak.exists():
        shutil.copy2(p, bak)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

agents = load(AGENTS_P)

# --- NFL.com top-5 needs for each team (verified 2026-04-20) ---
# Ordered best-to-5th priority.
NEEDS_2026 = {
    "LV":  ["QB","WR","OL","DL","CB"],
    "NYJ": ["QB","EDGE","WR","CB","OL"],
    "ARI": ["QB","OL","EDGE","DL","LB"],
    "TEN": ["OL","EDGE","WR","RB","LB"],
    "NYG": ["DL","OL","CB","LB","WR"],
    "CLE": ["QB","OL","WR","CB","EDGE"],
    "WAS": ["WR","EDGE","OL","DB","RB"],
    "NO":  ["WR","EDGE","CB","DL","OL"],
    "KC":  ["CB","WR","EDGE","DL","OL"],
    "MIA": ["WR","CB","EDGE","OL","S"],
    "DAL": ["EDGE","LB","CB","DL","OL"],
    "LAR": ["WR","OL","LB","EDGE","DB"],
    "BAL": ["OL","EDGE","WR","DL","TE"],
    "TB":  ["EDGE","CB","LB","OL","DL"],
    "DET": ["OL","EDGE","S","CB","LB"],
    "MIN": ["DL","OL","S","WR","CB"],
    "CAR": ["OL","S","WR","TE","DL"],
    "PIT": ["QB","OL","WR","TE","LB"],
    "LAC": ["OL","EDGE","DL","DB","WR"],
    "PHI": ["EDGE","OL","S","WR","TE"],
    "CHI": ["S","OL","DL","EDGE","WR"],
    "BUF": ["EDGE","OL","LB","DB","WR"],
    "SF":  ["OL","EDGE","WR","DL","S"],
    "HOU": ["OL","DL","LB","DB","EDGE"],
    "NE":  ["EDGE","OL","DL","TE","WR"],
    "SEA": ["RB","OL","DB","EDGE","WR"],
    "ATL": ["WR","OL","DL","CB","EDGE"],
    "CIN": ["LB","DB","EDGE","OL","WR"],
    "DEN": ["DL","TE","DB","LB","OL"],
    "GB":  ["EDGE","DL","OL","CB","RB"],
    "IND": ["EDGE","LB","S","OL","WR"],
    "JAX": ["LB","EDGE","DL","OL","S"],
}
# Rank → need weight (scale 5.0 top → 2.0 fifth)
NEED_WEIGHT = {0: 5.0, 1: 4.0, 2: 3.0, 3: 2.5, 4: 2.0}

# Position name canonicalization to our schema
CANON = {
    "QB": "QB", "WR": "WR", "RB": "RB", "TE": "TE",
    "OL": "OT",      # analyst shorthand → our OT (primary OL need = tackle)
    "OT": "OT", "T": "OT",
    "IOL": "IOL", "G": "IOL", "C": "IOL", "OG": "IOL",
    "DL": "IDL",     # defensive tackle
    "EDGE": "EDGE", "DE": "EDGE",
    "LB": "LB", "ILB": "LB", "OLB": "LB",
    "CB": "CB",
    "S": "S", "FS": "S", "SS": "S",
    "DB": "S",       # ambiguous; map to S (if team already has CB high, this covers S)
}

def build_needs(team: str) -> dict:
    """Return {POS: weight} from the authoritative top-5 list, de-duped."""
    out = {}
    for rank, pos in enumerate(NEEDS_2026[team]):
        c = CANON.get(pos, pos)
        # if canonical already filled, don't overwrite with lower rank
        if c not in out:
            out[c] = NEED_WEIGHT[rank]
    # If OL showed up in the top-5 but not IOL explicitly, also seed a
    # secondary IOL need at half weight — analysts use "OL" loosely.
    if "OT" in out and "IOL" not in out:
        out["IOL"] = out["OT"] * 0.5
    return out


# --- Walter Football visit lists (verified 2026-04-20) ---
VISITS_2026 = {
    "ARI": ["Drew Allar","David Bailey","Caleb Banks","Austin Barber","Carson Beck",
            "Chris Brazzell II","Caleb Douglas","Max Iheanachor","Malachi Lawrence",
            "Jeremiyah Love","Chris McClellan","Tyler Onyedim","Cole Payton",
            "Kaleb Proctor","Kadyn Proctor","Arvell Reese","Ty Simpson",
            "Treydan Stukes","Zavion Thomas","Caleb Tiernan","Reggie Virgil"],
    "ATL": ["Germie Bernard","Zachariah Branch","Josh Cameron","Kevin Coleman Jr.",
            "Alan Herron","Justin Jefferson","Haynes King","Christian Miller",
            "Devin Moore","Beau Stephens","Treydan Stukes","Mike Washington","Zion Young"],
    "BAL": ["Denzel Boston","Travis Burke","K.C. Concepcion","Mansoor Delane",
            "Oscar Delp","A.J. Haulcy","Jackson Kuwatch","Malachi Lawrence"],
    "BUF": ["Chris Bell","Malik Benson","Denzel Boston","K.C. Concepcion",
            "A.J. Haulcy","Justin Joly","Christian Miller","Julian Neal",
            "Dominique Orange","Josiah Trotter"],
    "CAR": ["Denzel Boston","Chris Brazzell II","Travis Burke","Deion Burks",
            "Omar Cooper","Keyron Crawford","Oscar Delp","A.J. Haulcy","Haynes King",
            "Chris McClellan","Jermod McCoy","Dominique Orange","Diego Pavia",
            "Treydan Stukes"],
    "CHI": ["James Brockermeyer","Caleb Lomu","Kayden McDonald","Dominique Orange",
            "Jimmy Rolder","Keionte Scott","De'Zhaun Stribling","Anterio Thompson"],
    "CIN": ["Austin Barber","Kaelon Black","Mansoor Delane","Romello Height",
            "Lee Hunter","Athan Kaliakmanis","Jeremiyah Love","Emmanuel McNeil-Warren",
            "Akheem Mesidor","Febechi Nwaiwu","Jayden Ott","Landon Robinson",
            "Jacob Rodriguez","Josiah Trotter"],
    "CLE": ["Chris Bell","Germie Bernard","Denzel Boston","K.C. Concepcion",
            "Omar Cooper","Oscar Delp","Makai Lemon","Caleb Lomu","Kadyn Proctor",
            "Ty Simpson","Carnell Tate","Jordyn Tyson"],
    "DAL": ["David Bailey","Brandon Cisse","Omar Cooper","Mansoor Delane",
            "Caleb Downs","Jaden Dugger","Kaleb Elarms-Orr","Keldric Faulk",
            "Colton Hood","Rene Konga","Jermod McCoy","Emmanuel McNeil-Warren",
            "D'Angelo Ponds","Kamari Ramsey","Arvell Reese","Keionte Scott",
            "Beau Stephens","Eli Stowers","Treydan Stukes","Sonny Styles",
            "Avieon Terrell","Josiah Trotter","Cole Wisniewski"],
    "DEN": ["Nick Barnett","Kaelon Black","Nate Boerkircher","Jonah Coleman",
            "Omar Cooper","Kaleb Elarms-Orr","Josh Gesky","Justin Joly",
            "Chris McClellan","Christian Miller","Jimmy Rolder","Eli Stowers"],
    "DET": ["Caleb Banks","Andre Fuller","Tyre West"],
    "GB":  ["Damon Bankston","Kaelon Black","Chris Brazzell II","Charles Demmings",
            "Malcolm DeWalt","Jaden Dugger","Josh Gesky","A.J. Haulcy",
            "Romello Height","Michael Heldman","Ted Hurst","Nyjalik Kelly",
            "Will Lee III","Christian Miller","Behren Morton","Ethan Onianwa",
            "D'arco Perkins-McAllister","Kaleb Proctor","Karon Punty",
            "Anthony Smith","Jacob Thomas","Mike Washington"],
    "HOU": ["Kaelon Black","Charles Demmings","Caleb Douglas","A.J. Haulcy",
            "Colton Hood","Justin Jefferson","Javon Kilgore","Miles Kitselman",
            "Malachi Lawrence","Connor Lew","Kayden McDonald","Christian Miller",
            "Dominique Orange","Kadyn Proctor","Zion Young"],
    "IND": ["Chris Bell","Chris Brazzell II","Ted Hurst","Javon Kilgore",
            "Jackson Kuwatch","Malachi Lawrence","Christian Miller","Cole Payton"],
    "JAX": [],  # WF lists none; analyst notes no T30 confirmed
    "KC":  ["David Bailey","Rueben Bain Jr.","Caleb Banks","Chris Bell",
            "Chris Brazzell II","Kevin Coleman Jr.","Oscar Delp","Jack Dingle",
            "Colton Hood","Ted Hurst","Chris Johnson","Justin Joly","Rene Konga",
            "Malachi Lawrence","Makai Lemon","Kadyn Proctor","Arvell Reese",
            "Kenyon Sadiq","Treydan Stukes","Carnell Tate"],
    "LV":  ["Caleb Banks","Chris Bell","Germie Bernard","Kaelon Black",
            "Zachariah Branch","K.C. Concepcion","Keyron Crawford","Jack Dingle",
            "Caleb Douglas","Daylen Everette","Colton Hood","Ted Hurst",
            "Chris Johnson","Malachi Lawrence","Chris McClellan","Christian Miller",
            "Kamari Ramsey",
            # Add Mendoza — confirmed formal interview + Brady direct comms
            "Fernando Mendoza"],
    "LAC": ["Chase Bisontis","K.C. Concepcion","Oscar Delp","Greg Desrosiers",
            "Michael Heldman","Gabe Jacas","Malachi Lawrence","Caleb Lomu",
            "Jayden Ott","Isaiah World"],
    "LAR": ["Carnell Tate","Makai Lemon"],  # LAR has well-reported Lemon interest
    "MIA": ["Cyrus Allen","Chase Bisontis","Kaelon Black","K.C. Concepcion",
            "Mansoor Delane","Charles Demmings","Taylen Green","Mark Gronowski",
            "A.J. Haulcy","Jordan Hudson","Ted Hurst","Max Iheanachor","Justin Joly",
            "Rene Konga","Makai Lemon","Hezekiah Masses","Kayden McDonald",
            "Emmanuel McNeil-Warren","Christian Miller","Le'Veon Moss","Ty Simpson",
            "Zion Young"],
    "MIN": ["Demond Claiborne","Jonah Coleman","Oscar Delp","Anthony Hill Jr.",
            "Ted Hurst","Emmett Johnson","Tristan Leigh","Lance Mason",
            "Seth McGowan","Dominique Orange","De'Zhaun Stribling","Cole Wisniewski"],
    "NE":  ["Travis Burke","K.C. Concepcion","Jalon Daniels","Oscar Delp",
            "Max Iheanachor","Gabe Jacas","Khalil Jacobs","Malachi Lawrence",
            "Emmanuel McNeil-Warren","Adam Randall","Malik Spencer",
            "De'Zhaun Stribling","Zakee Wheatley"],
    "NO":  ["Chris Bell","Jude Bowry","Travis Burke","Alan Herron","Ted Hurst",
            "Malachi Lawrence","Makai Lemon","Carnell Tate","Jordyn Tyson"],
    "NYG": ["Malik Benson","Chase Bisontis","Travis Burke","K.C. Concepcion",
            "J.C. Davis","Tacario Davis","Mansoor Delane","Thaddeus Dixon",
            "Spencer Fano","Andre Fuller","Lee Hunter","Ted Hurst","Chris Johnson",
            "Makai Lemon","Caleb Lomu","Jeremiyah Love","Chris McClellan",
            "Christian Miller","Febechi Nwaiwu","Arvell Reese","Carnell Tate",
            "Josiah Trotter"],
    "NYJ": ["Drew Allar","Cyrus Allen","Chris Bell","Kaelon Black","Denzel Boston",
            "Omar Cooper","Nick Dawkins","Colton Hood","Khalil Jacobs",
            "Chris Johnson","Jackson Kuwatch","Malachi Lawrence","Makai Lemon",
            "Tyler Onyedim","Arvell Reese","Nicholas Singleton","Cian Stone",
            "Sonny Styles","Tyre West","Cole Wisniewski"],
    "PHI": ["Luke Altmyer","Chris Bell","Markel Bell","Nate Boerkircher",
            "Jude Bowry","Travis Burke","Omar Cooper","Caleb Douglas",
            "Romello Height","Max Iheanachor","Javon Kilgore","Malachi Lawrence",
            "Caleb Lomu","Eli Stowers","De'Zhaun Stribling","Treydan Stukes",
            "Isaiah World"],
    "PIT": ["Carson Beck","Markel Bell","Germie Bernard","Denzel Boston",
            "Travis Burke","Jeff Caldwell","Tacario Davis","Josiah Green",
            "Taylen Green","Chris Johnson","Marlin Klein","Kendrick Law",
            "Makai Lemon","Kyle Louis","Emmanuel McNeil-Warren","Malik Muhammad",
            "Cole Payton","Harold Perkins","Ephesians Prysock","Jacob Rodriguez",
            "Keylan Rutledge"],
    "SF":  ["Denzel Boston","Chris Brazzell II","K.C. Concepcion","Omar Cooper",
            "Caleb Douglas","Romello Height","Malachi Lawrence","Caleb Lomu",
            "Chris McClellan","Tyler Onyedim","Cole Wisniewski","Colbie Young"],
    "SEA": ["Brandon Cisse","Jonah Coleman","Keyron Crawford","Daylen Everette",
            "Andre Fuller","A.J. Haulcy","Colton Hood","Cashius Howell",
            "Keyshan James-Newby","Javon Kilgore","Malachi Lawrence",
            "Kayden McDonald","Beau Stephens","Treydan Stukes","Chip Trayanum",
            "Josiah Trotter","Mike Washington","Zion Young"],
    "TB":  ["Jalon Daniels","Oscar Delp","Gracen Halton","Lee Hunter","Max Klare",
            "Christian Miller","Kaleb Proctor","Jimmy Rolder","De'Zhaun Stribling",
            "R. Mason Thomas","Nadame Tucker","Dan Villari","Mike Washington",
            "Cole Wisniewski","Zion Young"],
    "TEN": ["Jordan van den Berg","David Bailey","Rueben Bain Jr.","Caleb Banks",
            "Austin Barber","Chase Bisontis","James Brockermeyer","K.C. Concepcion",
            "Keyron Crawford","Mansoor Delane","Justin Jefferson","Justin Joly",
            "Malachi Lawrence","Tristan Leigh","Makai Lemon","Jeremiyah Love",
            "Arvell Reese","Carnell Tate","Treydan Stukes","Zion Young"],
    "WAS": ["David Bailey","Rueben Bain Jr.","Denzel Boston","Chris Brazzell II",
            "Omar Cooper","Mansoor Delane","Caleb Downs","Gracen Halton",
            "Alan Herron","Emmett Johnson","Athan Kaliakmanis","Javon Kilgore",
            "Malachi Lawrence","Makai Lemon","Jeremiyah Love","Arvell Reese",
            "Keionte Scott","Sonny Styles","Carnell Tate","Jordyn Tyson"],
}

# --- Medical concerns to propagate into injury_flags ---
MEDICAL_2026 = {
    "Jordyn Tyson": {
        "type": "durability",
        "severity": "high",
        "detail": "ACL/MCL/PCL tears 2022, fractured collarbone 2024, "
                  "hamstring 2025. Did NOT work out at combine or ASU pro day. "
                  "David Pollack: 'trending wrong direction'.",
    },
    "Caleb Banks": {
        "type": "foot",
        "severity": "medium",
        "detail": "Missed 9 games of 2025 with foot injury. "
                  "Pass-rush production solid; run defense grade weak.",
    },
    "Jermod McCoy": {
        "type": "ACL",
        "severity": "medium",
        "detail": "Torn ACL January 2025; missed entire 2025 season. "
                  "Expected recovered by combine.",
    },
    "Drew Allar": {
        "type": "ankle",
        "severity": "medium",
        "detail": "Ankle injury ended 2025 season after 6 starts. "
                  "Underwhelming campaign before the injury.",
    },
    "Garrett Nussmeier": {
        "type": "abdomen",
        "severity": "low",
        "detail": "Abdominal strain in 2025; returned.",
    },
}

# --- Apply patches ---
counts = {"needs": 0, "visits": 0, "medical": 0}

for team in agents:
    if team.startswith("_"): continue
    if team not in NEEDS_2026: continue

    # 1. Authoritative top-5 needs
    new_needs = build_needs(team)
    agents[team]["roster_needs"] = dict(sorted(new_needs.items(),
                                              key=lambda kv: -kv[1]))
    agents[team]["needs_source"] = "nfl_com_top5_verified_2026-04-20"
    counts["needs"] += 1

    # 2. Merge visits
    vs = agents[team].setdefault("visit_signals", {})
    existing = set(vs.get("confirmed_visits", []) or [])
    research_visits = set(VISITS_2026.get(team, []))
    merged = sorted(existing | research_visits)
    vs["confirmed_visits"] = merged
    vs["n_confirmed"] = len(merged)
    vs["source"] = "walterfootball.com + prior scraped"
    counts["visits"] += 1

# 3. Attach medical flags at league level for team_fit to read
agents.setdefault("_meta_medical_flags_2026", {}).update(MEDICAL_2026)
counts["medical"] = len(MEDICAL_2026)

# 4. Record the patch
agents["_meta_deep_research"] = {
    "applied_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    "research_date": "2026-04-20",
    "sources": [
        "nfl.com/news/2026-nfl-draft-order-round-1-needs-for-all-32-teams",
        "walterfootball.com/ProspectMeetingsByTeam2026.php",
        "profootballnetwork.com (Tyson injury reporting)",
        "bleacherreport.com, atozsports.com (per-team intel)",
    ],
    "counts": counts,
    "notes": (
        "All 32 teams' roster_needs rebuilt from NFL.com authoritative "
        "top-5. Visit lists MERGED (research additions + prior entries) "
        "so prior team-specific visit data is preserved. Medical flags "
        "are stored at league level for player_value to read at board "
        "construction time."
    ),
}

save(AGENTS_P, agents)
print(f"Patched {AGENTS_P}")
print(f"  needs rebuilt for {counts['needs']} teams")
print(f"  visits merged for {counts['visits']} teams")
print(f"  medical flags registered: {counts['medical']}")
