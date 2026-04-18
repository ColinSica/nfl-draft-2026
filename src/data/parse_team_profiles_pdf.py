"""
Parse data/2026_NFL_Draft_Team_Profiles.txt (extracted from the PDF) into a
structured JSON keyed by team abbreviation, plus a `_league` entry with the
league-wide synthesis section.

Output: data/features/team_profiles_narrative_2026.json

This is purely a parsing step — no model state is touched. The result is
consumed by build_team_agents.py, which merges the narrative under each
team's `narrative` key in team_agents_2026.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_TXT = ROOT / "data" / "2026_NFL_Draft_Team_Profiles.txt"
OUT_JSON = ROOT / "data" / "features" / "team_profiles_narrative_2026.json"

FULL_NAME_TO_ABBR: dict[str, str] = {
    "Arizona Cardinals": "ARI",
    "Atlanta Falcons": "ATL",
    "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR",
    "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN",
    "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN",
    "Detroit Lions": "DET",
    "Green Bay Packers": "GB",
    "Houston Texans": "HOU",
    "Indianapolis Colts": "IND",
    "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC",
    "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LAR",
    "Las Vegas Raiders": "LV",
    "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN",
    "New England Patriots": "NE",
    "New Orleans Saints": "NO",
    "New York Giants": "NYG",
    "New York Jets": "NYJ",
    "Philadelphia Eagles": "PHI",
    "Pittsburgh Steelers": "PIT",
    "Seattle Seahawks": "SEA",
    "San Francisco 49ers": "SF",
    "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN",
    "Washington Commanders": "WAS",
}

# Ligatures and whitespace anomalies introduced by pdftotext / pypdf.
LIGATURE_FIXES = [
    ("\ufb00", "ff"),
    ("\ufb01", "fi"),
    ("\ufb02", "fl"),
    ("\ufb03", "ffi"),
    ("\ufb04", "ffl"),
    ("\u2013", "-"),   # en dash
    ("\u2014", "-"),   # em dash (paragraph dashes are normalized too)
    ("\u2019", "'"),
    ("\u2018", "'"),
    ("\u201c", '"'),
    ("\u201d", '"'),
    ("\u2026", "..."),
]

# Section markers inside a team block. Order matches the PDF template.
SECTION_MARKERS = [
    ("leadership",            re.compile(r"^Leadership:\s*", re.I)),
    ("context_2025",          re.compile(r"^2025 context:\s*", re.I)),
    ("qb_situation",          re.compile(r"^QB situation:\s*", re.I)),
    ("offseason_moves",       re.compile(r"^Key 2026 offseason moves:\s*", re.I)),
    ("scheme_identity",       re.compile(r"^Scheme identity:\s*", re.I)),
    ("roster_needs_tiered",   re.compile(r"^Roster needs \(tiered\):\s*", re.I)),
    # player archetype lines are captured specially (multiple, one per pick)
    ("gm_fingerprint",        re.compile(r"^GM behavioral fingerprint", re.I)),
    ("uncertainty_flags",     re.compile(r"^Uncertainty flags:\s*", re.I)),
    ("predictability_tier",   re.compile(r"^Predictability tier:\s*", re.I)),
    ("trade_up_scenario",     re.compile(r"^Trade-up scenario[^:\n]*:\s*", re.I)),
    ("cascade_rule",          re.compile(r"^Cascade (rule|dependency):\s*", re.I)),
]

ARCHETYPE_RE = re.compile(
    r"^Player archetype sought at (\d+)(?:\s*\([^)]*\))?:\s*(.*)$", re.I
)
TEAM_HEADER_RE = re.compile(
    r"^(?P<name>[A-Z][A-Za-z0-9\. ]+?)\s*[-–—]\s*Pick[s]?\s+(?P<picks>[^\n\(]+?)(?:\s*\((?P<note>[^)]*)\))?\s*$"
)

# League-wide section headers we want to capture as separate keys.
LEAGUE_SECTION_HEADERS = [
    ("league_context",           "League-Wide Context"),
    ("high_uncertainty_teams",   "The Seven High-Uncertainty Teams"),
    ("most_predictable_picks",   "The Six Most Predictable Picks"),
    ("gm_strongest_fingerprints","GMs With Strongest Behavioral Fingerprints"),
    ("trade_up_candidates",      "Trade-Up Candidates"),
    ("trade_down_candidates",    "Trade-Down Candidates"),
    ("hard_trade_constraints",   "Hard Trade Constraints to Encode"),
    ("predictability_summary",   "Predictability Tier Summary"),
    ("position_run_dependencies","Position Run Dependencies"),
    ("position_urgency_heat_map","Position Urgency Heat Map"),
    ("scheme_change_flags",      "Scheme Change Flags"),
    ("known_unknowns",           "Known Unknowns"),
    ("by_team_quick_reference",  "By-Team Quick Reference"),
    ("position_demand_rank",     "Position-Specific Demand Rank"),
    ("data_quality_notes",       "Final Notes on Data Quality"),
    ("how_to_read",              "How to Read These Profiles"),
    ("position_abbreviation_key","Position Abbreviation Key"),
]


def normalize(text: str) -> str:
    """Strip ligatures, page markers, and redundant whitespace."""
    for src, dst in LIGATURE_FIXES:
        text = text.replace(src, dst)
    text = re.sub(r"={3,}\s*PAGE\s+\d+\s*={3,}", "", text)
    lines = [ln.rstrip() for ln in text.splitlines()]
    # Drop blank-run noise but keep paragraph breaks.
    out, prev_blank = [], False
    for ln in lines:
        if not ln.strip():
            if prev_blank:
                continue
            out.append("")
            prev_blank = True
        else:
            out.append(ln)
            prev_blank = False
    return "\n".join(out).strip()


def split_team_blocks(text: str) -> tuple[dict[str, dict], str]:
    """Scan the text line-by-line. Anything between a team header and the next
    team header (or a league-synthesis heading) belongs to that team. Returns
    (teams_dict, league_text)."""
    lines = text.splitlines()
    teams: dict[str, dict] = {}
    league_start = None

    headers: list[tuple[int, str, str]] = []  # (idx, abbr, raw_header_line)
    for i, ln in enumerate(lines):
        m = TEAM_HEADER_RE.match(ln.strip())
        if not m:
            continue
        name = m.group("name").strip()
        abbr = FULL_NAME_TO_ABBR.get(name)
        if not abbr:
            continue
        headers.append((i, abbr, ln.strip()))

    # Find start of the "LEAGUE-WIDE SYNTHESIS" section.
    for i, ln in enumerate(lines):
        if ln.strip() == "LEAGUE-WIDE SYNTHESIS":
            league_start = i
            break

    # Assign each team the text between its header and the next header or
    # the league-synthesis boundary.
    boundaries = [h[0] for h in headers] + [league_start if league_start else len(lines)]
    for idx, (start, abbr, raw) in enumerate(headers):
        end = boundaries[idx + 1] if idx + 1 < len(boundaries) else len(lines)
        block_lines = lines[start:end]
        teams[abbr] = {
            "header_raw": raw,
            "block_text": "\n".join(block_lines).strip(),
        }

    league_text = "\n".join(lines[league_start:]) if league_start is not None else ""
    return teams, league_text


def parse_picks(header_raw: str) -> tuple[list[int], str | None]:
    """Pull pick numbers out of a header line like 'Buffalo Bills - Pick 26' or
    'Miami Dolphins - Picks 11, 30' or 'Denver Broncos - Pick 62 (No R1, ...)'.
    Returns (picks, note)."""
    m = TEAM_HEADER_RE.match(header_raw)
    if not m:
        return ([], None)
    picks_str = m.group("picks") or ""
    note = (m.group("note") or "").strip() or None
    nums = [int(n) for n in re.findall(r"\d+", picks_str)]
    return (nums, note)


def parse_team_block(block: str) -> dict:
    """Walk the block top-to-bottom. When we hit a section marker we start
    capturing lines until the next known section marker appears."""
    lines = block.splitlines()
    # Skip the first line (the header) and any immediate blanks.
    body_start = 1
    while body_start < len(lines) and not lines[body_start].strip():
        body_start += 1
    body = lines[body_start:]

    sections: dict[str, list[str]] = {}
    archetypes: dict[str, list[str]] = {}
    current_key: str | None = None
    current_buf: list[str] = []

    def flush():
        nonlocal current_key, current_buf
        if current_key is None:
            return
        text_ = "\n".join(current_buf).strip()
        if current_key.startswith("__archetype__"):
            pick_num = current_key.split(":", 1)[1]
            archetypes.setdefault(pick_num, []).append(text_)
        else:
            existing = sections.get(current_key)
            if existing:
                sections[current_key] = existing + "\n\n" + text_
            else:
                sections[current_key] = text_
        current_key, current_buf = None, []

    for ln in body:
        # Archetype line? Special-case: "Player archetype sought at NN: ..."
        arche_m = ARCHETYPE_RE.match(ln.strip())
        if arche_m:
            flush()
            pick_num = arche_m.group(1)
            initial = arche_m.group(2).strip()
            current_key = f"__archetype__:{pick_num}"
            current_buf = [initial] if initial else []
            continue

        matched = None
        for key, rx in SECTION_MARKERS:
            m = rx.match(ln.strip())
            if m:
                matched = key
                # Text on the same line after the marker:
                rest = rx.sub("", ln.strip(), count=1).strip()
                flush()
                current_key = key
                current_buf = [rest] if rest else []
                break
        if matched:
            continue

        # Continuation line of whatever section is open.
        if current_key is not None:
            current_buf.append(ln)

    flush()

    # Collapse archetypes: if only one entry per pick, unwrap list; else keep
    # list of {text} dicts to preserve multiple (e.g. trade-up scenario adds
    # to Dallas).
    archetype_out: dict[str, str] = {}
    for pick, entries in archetypes.items():
        archetype_out[pick] = "\n\n".join(entries).strip()

    # Fallback: if gm_fingerprint is empty but an archetype contains the
    # classic "Trade tendency:" block, split it out. This rescues teams
    # where the PDF extraction dropped the "GM behavioral fingerprint:" line
    # itself (observed for LAR).
    if not sections.get("gm_fingerprint"):
        for pick, text_ in list(archetype_out.items()):
            m = re.search(r"\n\s*Trade tendency\s*:", text_)
            if m:
                split_at = m.start()
                archetype_out[pick] = text_[:split_at].strip()
                sections["gm_fingerprint"] = text_[split_at:].strip()
                break

    return {
        "leadership":              sections.get("leadership", ""),
        "context_2025":            sections.get("context_2025", ""),
        "qb_situation":            sections.get("qb_situation", ""),
        "offseason_moves":         sections.get("offseason_moves", ""),
        "scheme_identity":         sections.get("scheme_identity", ""),
        "roster_needs_tiered":     sections.get("roster_needs_tiered", ""),
        "player_archetypes":       archetype_out,
        "gm_fingerprint":          sections.get("gm_fingerprint", ""),
        "uncertainty_flags":       sections.get("uncertainty_flags", ""),
        "predictability_tier":     sections.get("predictability_tier", ""),
        "trade_up_scenario":       sections.get("trade_up_scenario", ""),
        "cascade_rule":            sections.get("cascade_rule", ""),
    }


def parse_league_section(league_text: str, full_text: str) -> dict:
    """Parse the league synthesis tail (after LEAGUE-WIDE SYNTHESIS) plus the
    two intro sections that appear *before* the first team (how-to-read,
    position abbreviation key, league-wide context)."""
    lines = full_text.splitlines()

    # Build an index of heading line positions so we can slice between them.
    heading_positions: list[tuple[int, str]] = []
    for i, ln in enumerate(lines):
        raw = ln.strip()
        for key, hdr in LEAGUE_SECTION_HEADERS:
            if raw.startswith(hdr):
                heading_positions.append((i, key))
                break
        # also stop when we hit a team header — those aren't league sections.
        if TEAM_HEADER_RE.match(raw):
            heading_positions.append((i, "__team__"))

    # Extra boundary: the division banners (AFC EAST, etc.) are not sections
    # we want to capture, but they do terminate the intro "League-Wide
    # Context" section.
    DIVISION_BANNERS = {"AFC EAST", "AFC NORTH", "AFC SOUTH", "AFC WEST",
                        "NFC EAST", "NFC NORTH", "NFC SOUTH", "NFC WEST"}
    for i, ln in enumerate(lines):
        if ln.strip() in DIVISION_BANNERS:
            heading_positions.append((i, "__division__"))

    heading_positions.sort()

    out: dict[str, str] = {}
    for idx, (start, key) in enumerate(heading_positions):
        if key in {"__team__", "__division__"}:
            continue
        # Find the next heading (of any kind) to bound this section.
        end = len(lines)
        for nxt_start, _ in heading_positions[idx + 1:]:
            if nxt_start > start:
                end = nxt_start
                break
        chunk = "\n".join(lines[start:end]).strip()
        # Drop the heading line itself from the body (keep it as the key).
        body_lines = chunk.splitlines()[1:]
        body = "\n".join(body_lines).strip()
        # Preserve the longest instance if we saw the heading twice.
        if key not in out or len(body) > len(out[key]):
            out[key] = body

    # Also capture the opening preamble ("2026 NFL Draft - Comprehensive ...").
    preamble: list[str] = []
    for ln in lines:
        if ln.strip().startswith("How to Read These Profiles"):
            break
        preamble.append(ln)
    out["preamble"] = "\n".join(preamble).strip()
    return out


# ---------------------------------------------------------------------------
# Post-processing: derive structured sub-fields from the raw narrative so that
# downstream consumers (build_team_agents.py, stage2 simulator) can key on
# typed values instead of re-parsing prose every run.
# ---------------------------------------------------------------------------

# Canonical position tokens used everywhere in the codebase.
POSITION_TOKENS = ["QB", "RB", "WR", "TE", "OT", "OL", "IOL", "G", "C",
                   "EDGE", "IDL", "DT", "DL", "LB", "CB", "S", "DB"]

# Map prose scheme descriptors -> canonical scheme-type string. Used when we
# need a short label; premium positions are extracted separately.
SCHEME_TYPE_PATTERNS = [
    (r"shanahan", "shanahan_zone"),
    (r"mcvay",    "mcvay_spread"),
    (r"mahomes|reid",    "reid_spread"),
    (r"harbaugh|michigan","harbaugh_power"),
    (r"fangio",   "fangio_match"),
    (r"minter",   "minter_multiple"),
    (r"flores",   "flores_pressure"),
    (r"bradley|cover-3|legion","bradley_cover3"),
    (r"monken",   "monken_vertical"),
    (r"golden",   "golden_hybrid"),
    (r"bowles",   "bowles_blitz"),
    (r"anarumo",  "anarumo_pressure"),
    (r"fangio",   "fangio_match"),
    (r"saleh",    "saleh_wide9"),
    (r"vic fangio","fangio_match"),
    (r"quinn",    "quinn_aggressive"),
    (r"ryans",    "ryans_wide9"),
    (r"payton",   "payton_westcoast"),
    (r"schwartz", "schwartz_wide9"),
    (r"hafley|haefley","hafley_ohio"),
    (r"glenn",    "glenn_multiple"),
    (r"staley",   "staley_3-4"),
    (r"kubiak",   "shanahan_zone"),
    (r"macdonald","macdonald_multiple"),
    (r"leonhard|modified leonhard","leonhard_3-4"),
    (r"brady",    "brady_rpo"),
    (r"canales",  "canales_westcoast"),
    (r"morris",   "morris_hybrid"),
    (r"parker.*phi|parker from phi", "parker_zonematch"),
    (r"sirianni", "sirianni_rpo"),
    (r"moore",    "moore_pass"),
    (r"coen",     "coen_pass"),
    (r"mcdaniels","mcdaniels_pro"),
    (r"oconnell|o'connell","oconnell_mcvay"),
    (r"stenavich|lafleur","lafleur_zone"),
    (r"shanahan","shanahan_zone"),
]

PREDICTABILITY_ENUM = {
    "HIGHEST":      "HIGH",
    "HIGH":         "HIGH",
    "MEDIUM-HIGH":  "MEDIUM-HIGH",
    "MED-HIGH":     "MEDIUM-HIGH",
    "MEDIUM":       "MEDIUM",
    "LOW-MEDIUM":   "LOW-MEDIUM",
    "MEDIUM-LOW":   "LOW-MEDIUM",
    "LOW-MED":      "LOW-MEDIUM",
    "LOW":          "LOW",
}

TRADE_PROB_TOKENS = {
    "VERY HIGH": 0.85, "HIGH": 0.70, "MODERATE": 0.35, "MOD": 0.35,
    "LOW": 0.15, "VERY LOW": 0.05, "LOW-MEDIUM": 0.25, "MEDIUM": 0.40,
}


def extract_scheme_struct(text_: str) -> dict:
    """Parse a scheme_identity blob into {type, premium, raw}.
    - type: best-matching canonical scheme label (or 'default')
    - premium: list of position tokens mentioned after 'Premium positions:'
    """
    if not text_:
        return {"type": "default", "premium": [], "raw": ""}
    lower = text_.lower()
    stype = "default"
    for rx, lbl in SCHEME_TYPE_PATTERNS:
        if re.search(rx, lower):
            stype = lbl
            break
    # Pull positions after 'Premium positions:' (case-insensitive)
    premium: list[str] = []
    m = re.search(r"Premium positions[^:]*:\s*([^\n\.]+)", text_, re.I)
    if m:
        tail = m.group(1)
        for tok in re.findall(r"\b[A-Z]{1,4}\b", tail):
            if tok in POSITION_TOKENS and tok not in premium:
                premium.append(tok)
    return {"type": stype, "premium": premium, "raw": text_.strip()}


def extract_fa_moves_struct(text_: str) -> dict:
    """Pull 'Added:'/'Lost:' lines from offseason_moves prose into structured
    arrivals/departures lists. Each entry keeps the raw player descriptor
    ('DJ Moore WR (trade to BUF - major)') so downstream tools can decide how
    to normalize it."""
    out = {"arrivals": [], "departures": []}
    if not text_:
        return out

    def _parse_list(label_rx: str) -> list[str]:
        m = re.search(label_rx + r":\s*(.+?)(?=\n\s*(?:Added|Lost|Net effect|Major|Catastrophic)\b|\Z)",
                      text_, re.I | re.S)
        if not m:
            return []
        chunk = re.sub(r"\s+", " ", m.group(1)).strip()
        # Split on commas that separate player entries. Respect parentheses
        # by counting depth so "DJ Moore WR (trade to BUF, major)" stays whole.
        parts, buf, depth = [], [], 0
        for ch in chunk:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(0, depth - 1)
            if ch == "," and depth == 0:
                parts.append("".join(buf).strip())
                buf = []
            else:
                buf.append(ch)
        if buf:
            parts.append("".join(buf).strip())
        return [p for p in parts if p]

    # Also capture "Major acquisitions:" / "Catastrophic losses:" / "Major
    # losses:" / "Added:" / "Lost:" labels used inconsistently across teams.
    out["arrivals"] = (_parse_list(r"(?:Added|Major acquisitions|Key additions)")
                       or [])
    out["departures"] = (_parse_list(r"(?:Lost|Major losses|Catastrophic losses|Key losses)")
                         or [])
    return out


def extract_latent_needs_struct(roster_needs_text: str) -> dict[str, float]:
    """Pull 'Latent:' bullet into {position: synthetic_score}. Latent gets a
    fixed 2.0 score (consistent with what EXPLICIT_PROFILES uses for the
    `latent_needs` dict already)."""
    if not roster_needs_text:
        return {}
    m = re.search(r"Latent[^:]*:\s*(.+?)(?=\n\s*[A-Z][a-z]+\s*\([^)]*\)\s*:|\Z)",
                  roster_needs_text, re.I | re.S)
    if not m:
        return {}
    chunk = re.sub(r"\s+", " ", m.group(1)).strip()
    needs: dict[str, float] = {}
    for tok in re.findall(r"\b[A-Z]{1,4}\b", chunk):
        if tok in POSITION_TOKENS and tok not in needs:
            needs[tok] = 2.0
    return needs


def extract_predictability_enum(text_: str) -> str:
    """Return the canonical enum (HIGH / MEDIUM-HIGH / MEDIUM / LOW-MEDIUM /
    LOW) from the opening of the predictability_tier blob."""
    if not text_:
        return ""
    up = text_.upper().strip()
    for key in ("LOW-MEDIUM", "MEDIUM-LOW", "LOW-MED", "MEDIUM-HIGH",
                "MED-HIGH", "HIGHEST", "VERY HIGH", "HIGH", "MEDIUM",
                "MODERATE", "LOW"):
        if up.startswith(key) or re.match(rf"^{re.escape(key)}\b", up):
            return PREDICTABILITY_ENUM.get(key, key)
    return ""


def extract_trade_probability(text_: str) -> dict:
    """Scan uncertainty_flags + gm_fingerprint for explicit trade-up / trade-
    down language. Returns {trade_up_tier, trade_up_prob, trade_down_tier,
    trade_down_prob} where tiers are VERY_HIGH/HIGH/MODERATE/LOW/VERY_LOW and
    probabilities are float priors (0-1). Empty fields mean not detected."""
    if not text_:
        return {}
    out: dict = {}
    # Direct "X trade-down probability" / "trade-up rate" phrasing.
    for direction in ("up", "down"):
        rx = re.compile(
            rf"trade-{direction}[^.\n]*?(very high|high|moderate|low|very low)",
            re.I)
        m = rx.search(text_)
        if m:
            tier = m.group(1).upper().replace(" ", "_")
            out[f"trade_{direction}_tier"] = tier
            prob_key = m.group(1).upper()
            prob = TRADE_PROB_TOKENS.get(prob_key)
            if prob is not None:
                out[f"trade_{direction}_prob"] = prob
    # Explicit numeric rates like "0.89 historical rate" / "(0.65 trade-up rate)"
    num_rx = re.compile(r"0\.\d{1,3}", re.I)
    for m in num_rx.finditer(text_):
        # No attribution — skip; we already have tier-based estimates.
        pass
    return out


def extract_trade_candidates(league_text: str, direction: str) -> list[dict]:
    """Parse the 'Trade-Up Candidates' / 'Trade-Down Candidates' section into
    [{rank, team, picks, notes}, ...]. direction is 'up' or 'down'."""
    out: list[dict] = []
    if not league_text:
        return out
    # Each entry starts with an index like '1.' followed by a team name and
    # optionally picks in parens.
    for line in league_text.splitlines():
        ln = line.strip()
        m = re.match(r"^(\d+)\.\s+([A-Z][A-Za-z ]+?)(?:\s*\(([^)]+)\))?\s*[-–—]\s*(.+)$", ln)
        if not m:
            continue
        rank, name, picks, notes = m.groups()
        abbr = FULL_NAME_TO_ABBR.get(name.strip())
        if not abbr:
            continue
        out.append({
            "rank": int(rank),
            "team": abbr,
            "picks": picks.strip() if picks else None,
            "notes": notes.strip(),
        })
    return out


def extract_cascade_rules(league_text: str) -> list[dict]:
    """Parse the 'Position Run Dependencies (Cascade Rules)' section into
    typed rules: [{trigger_team, trigger_pick, trigger_position,
    dependent_team, dependent_pick, dependent_position, effect, raw}]."""
    out: list[dict] = []
    if not league_text:
        return out
    rx = re.compile(
        r"([A-Z]{2,3})\s*#(\d+)\s+([A-Z]{1,4})\s*(?:->|→)\s*"
        r"([A-Z]{2,3})\s*#(\d+)(?:\s+([A-Z]{1,4}))?\s*:\s*(.+)",
    )
    for line in league_text.splitlines():
        m = rx.search(line.strip())
        if not m:
            continue
        trig_team, trig_pick, trig_pos, dep_team, dep_pick, dep_pos, effect = m.groups()
        out.append({
            "trigger_team": trig_team,
            "trigger_pick": int(trig_pick),
            "trigger_position": trig_pos,
            "dependent_team": dep_team,
            "dependent_pick": int(dep_pick),
            "dependent_position": dep_pos or trig_pos,
            "effect": effect.strip(),
            "raw": line.strip(),
        })
    return out


def extract_known_unknowns(league_text: str) -> list[str]:
    """Pull bullets from the 'Known Unknowns / Model-Breaking Scenarios'
    section as a list of scenario strings."""
    if not league_text:
        return []
    out: list[str] = []
    for line in league_text.splitlines():
        ln = line.strip()
        m = re.match(r"^\d+\.\s+(.+)$", ln)
        if m:
            out.append(m.group(1).strip())
    return out


INJURY_KEYWORDS = [
    "ACL", "Achilles", "torn ACL", "torn", "neck injury", "hamstring",
    "rehab", "recover", "injured", "penalty/availability",
]

def extract_injury_flags(team_blob: str) -> list[dict]:
    """Pull player-level injury mentions from the full team narrative blob.
    Each entry: {player: str, injury: str, severity: 'high'|'medium'|'low',
    raw: str}. Severity is a crude heuristic driven by keyword — ACL/torn
    Achilles = high, rehab/recover = medium, hamstring/availability = low.
    """
    if not team_blob:
        return []
    out: list[dict] = []
    seen: set[str] = set()
    rx = re.compile(
        r"([A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-\.]+){0,2})\s+"
        r"(?:[A-Z]{1,4}\s+)?\(?\s*([^)\n]*?(?:"
        + "|".join(re.escape(k) for k in INJURY_KEYWORDS)
        + r")[^)\n]*)\)?",
        re.I,
    )
    severity_map = {
        "acl": "high", "torn": "high", "achilles": "high",
        "neck": "high",
        "rehab": "medium", "recover": "medium", "injured": "medium",
        "hamstring": "low", "availability": "low", "penalty": "low",
    }
    # Common words that look capitalized in context but aren't names.
    STOP_TOKENS = {"Injury", "Year", "Playoff", "Last", "From", "Lost",
                    "Added", "Added:", "Net", "Secondary", "Urgent", "Latent",
                    "Moderate", "Trade", "Scheme", "Premium", "Potential",
                    "JJ", "Draft", "EDGE", "CB", "OT"}
    for m in rx.finditer(team_blob):
        player = m.group(1).strip()
        phrase = m.group(2).strip()
        first_tok = player.split()[0] if player.split() else ""
        # Filter: must have at least two capitalized words AND first token
        # is not a generic English word.
        words = player.split()
        if (len(words) < 2 or first_tok in STOP_TOKENS
                or not first_tok[0].isupper()
                or first_tok.lower() == first_tok):
            continue
        key = f"{player}|{phrase[:40]}"
        if key in seen or len(player) < 4:
            continue
        seen.add(key)
        low = phrase.lower()
        severity = "medium"
        for kw, sev in severity_map.items():
            if kw in low:
                severity = sev
                break
        out.append({"player": player, "injury": phrase, "severity": severity})
    return out


def extract_decision_maker(leadership_text: str, gm_fingerprint: str,
                            uncertainty_flags: str) -> dict:
    """Identify the primary draft-day decision-maker. Default: GM.
    Overrides applied when the narrative explicitly says someone else has
    unusual draft-room power (Jerry Jones for DAL, O'Connell for MIN, etc.).
    Returns {primary: str, tiebreaker: str|None, advisor_weight: float,
    source: 'narrative'|'default'}."""
    out = {"primary": "", "tiebreaker": None, "advisor_weight": 0.0,
           "source": "default"}
    # Default: the GM from leadership line.
    m = re.search(r"GM\s+([A-Z][A-Za-z.'\- ]+?)(?:\s*\(|\s*\||\s*$)",
                  leadership_text)
    if m:
        out["primary"] = m.group(1).strip()
    blob = " ".join([gm_fingerprint or "", uncertainty_flags or ""])
    if re.search(r"O'Connell.*unusual power|unusual power.*O'Connell",
                 blob, re.I):
        out["tiebreaker"] = out["primary"]
        out["primary"] = "Kevin O'Connell"
        out["advisor_weight"] = 0.5
        out["source"] = "narrative"
    elif re.search(r"Jerry.*(?:emotional|aggressive|picks for|most excited)",
                   blob, re.I):
        out["tiebreaker"] = "Stephen Jones"
        out["primary"] = "Jerry Jones"
        out["advisor_weight"] = 0.2
        out["source"] = "narrative"
    return out


def extract_hard_constraints_team(gm_fp: str, uncertainty: str) -> list[dict]:
    """Extract explicit GM-level trade / drafting constraints from the
    narrative. Examples:
      - 'Famously NEVER trades down' -> {type: 'no_trade_down'}
      - 'publicly said stay-put preference' -> {type: 'stay_put_stated'}
      - 'extremely low trade probability' -> {type: 'low_trade_probability'}
    Each entry: {type, raw}. Downstream code keys on `type` for logic."""
    blob = " ".join([gm_fp or "", uncertainty or ""])
    out: list[dict] = []
    patterns = [
        (r"never trade[s]?[- ]down|zero trade[- ]?downs",  "no_trade_down"),
        (r"never trades? up|only trades? up",              "trade_up_only"),
        (r"stay[- ]put|staying at \d+|not trading down from", "stay_put_stated"),
        (r"hates? trades?|famous for staying put|essentially never move",
         "rarely_trades"),
        (r"has not moved.*R1.*\d+ consecutive|\d+ consecutive drafts",
         "no_r1_movement_streak"),
        (r"openly said.*trade.*heavy|aggressive trader",   "aggressive_trader"),
        (r"trade down is the modal outcome|heavy trade[- ]down|ultimate trade[- ]down",
         "heavy_trade_down"),
    ]
    for rx, ctype in patterns:
        m = re.search(rx, blob, re.I)
        if m:
            out.append({"type": ctype, "raw": m.group(0)})
    return out


def extract_hard_trade_constraints(league_text: str) -> list[dict]:
    """Parse 'Hard Trade Constraints to Encode' section into a list of
    {team_or_group, constraint, raw} dicts."""
    if not league_text:
        return []
    out: list[dict] = []
    for line in league_text.splitlines():
        ln = line.strip()
        if ":" not in ln:
            continue
        lhs, rhs = ln.split(":", 1)
        teams = re.findall(r"[A-Z]{2,3}", lhs)
        if not teams:
            continue
        out.append({
            "teams": teams,
            "constraint": rhs.strip(),
            "raw": ln,
        })
    return out


def augment_team(parsed: dict) -> dict:
    """Add structured sub-fields derived from the raw narrative sections."""
    parsed["scheme_struct"] = extract_scheme_struct(parsed.get("scheme_identity", ""))
    parsed["fa_moves_struct"] = extract_fa_moves_struct(parsed.get("offseason_moves", ""))
    parsed["latent_needs_struct"] = extract_latent_needs_struct(
        parsed.get("roster_needs_tiered", "")
    )
    parsed["predictability_enum"] = extract_predictability_enum(
        parsed.get("predictability_tier", "")
    )
    combined_trade_text = " ".join([
        parsed.get("gm_fingerprint", ""),
        parsed.get("uncertainty_flags", ""),
        parsed.get("trade_up_scenario", ""),
    ])
    parsed["trade_probability"] = extract_trade_probability(combined_trade_text)

    # Phase 3: narrative-derived structured fields
    team_blob = " ".join([
        parsed.get("context_2025", ""),
        parsed.get("offseason_moves", ""),
        parsed.get("roster_needs_tiered", ""),
        parsed.get("scheme_identity", ""),
        parsed.get("uncertainty_flags", ""),
        parsed.get("gm_fingerprint", ""),
    ])
    parsed["injury_flags"] = extract_injury_flags(team_blob)
    parsed["decision_maker"] = extract_decision_maker(
        parsed.get("leadership", ""),
        parsed.get("gm_fingerprint", ""),
        parsed.get("uncertainty_flags", ""),
    )
    parsed["hard_constraints"] = extract_hard_constraints_team(
        parsed.get("gm_fingerprint", ""),
        parsed.get("uncertainty_flags", ""),
    )
    return parsed


def augment_league(league: dict) -> dict:
    league["trade_up_candidates_struct"] = extract_trade_candidates(
        league.get("trade_up_candidates", ""), "up"
    )
    league["trade_down_candidates_struct"] = extract_trade_candidates(
        league.get("trade_down_candidates", ""), "down"
    )
    league["cascade_rules_struct"] = extract_cascade_rules(
        league.get("position_run_dependencies", "")
    )
    league["known_unknowns_struct"] = extract_known_unknowns(
        league.get("known_unknowns", "")
    )
    league["hard_trade_constraints_struct"] = extract_hard_trade_constraints(
        league.get("hard_trade_constraints", "")
    )
    return league


def main() -> None:
    raw = SRC_TXT.read_text(encoding="utf-8")
    text = normalize(raw)
    teams_raw, league_text = split_team_blocks(text)

    teams: dict[str, dict] = {}
    for abbr, data in teams_raw.items():
        picks, note = parse_picks(data["header_raw"])
        parsed = parse_team_block(data["block_text"])
        parsed["picks"] = picks
        parsed["pick_note"] = note
        parsed["header_raw"] = data["header_raw"]
        parsed = augment_team(parsed)
        teams[abbr] = parsed

    league = parse_league_section(league_text, text)
    league = augment_league(league)

    out = {"_league": league, **{t: teams[t] for t in sorted(teams)}}
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                        encoding="utf-8")

    # Summary
    covered = sorted(teams.keys())
    missing = sorted(set(FULL_NAME_TO_ABBR.values()) - set(covered))
    print(f"Parsed {len(teams)} team profiles -> {OUT_JSON}")
    print(f"Covered: {', '.join(covered)}")
    if missing:
        print(f"MISSING ({len(missing)}): {', '.join(missing)}")
    else:
        print("All 32 teams covered.")

    # Coverage per section (how many teams populated each field)
    print("\nPer-section coverage:")
    keys = ["leadership", "context_2025", "qb_situation", "offseason_moves",
            "scheme_identity", "roster_needs_tiered", "gm_fingerprint",
            "uncertainty_flags", "predictability_tier"]
    for k in keys:
        n = sum(1 for t in teams.values() if t.get(k))
        print(f"  {k:<24} {n}/{len(teams)}")
    n_arche = sum(1 for t in teams.values() if t.get("player_archetypes"))
    print(f"  player_archetypes        {n_arche}/{len(teams)}")

    print(f"\nLeague sections captured: {len(league)}")
    for k, v in league.items():
        if isinstance(v, str):
            print(f"  {k:<32} {len(v)} chars")
        else:
            print(f"  {k:<32} {len(v)} entries")

    # Structured-field coverage
    print("\nStructured sub-field coverage:")
    for key, checker in [
        ("scheme_struct.type!=default",
         lambda t: t.get("scheme_struct", {}).get("type", "default") != "default"),
        ("scheme_struct.premium non-empty",
         lambda t: bool(t.get("scheme_struct", {}).get("premium"))),
        ("fa_moves_struct.arrivals",
         lambda t: bool(t.get("fa_moves_struct", {}).get("arrivals"))),
        ("fa_moves_struct.departures",
         lambda t: bool(t.get("fa_moves_struct", {}).get("departures"))),
        ("latent_needs_struct",
         lambda t: bool(t.get("latent_needs_struct"))),
        ("predictability_enum",
         lambda t: bool(t.get("predictability_enum"))),
        ("trade_probability",
         lambda t: bool(t.get("trade_probability"))),
    ]:
        n = sum(1 for t in teams.values() if checker(t))
        print(f"  {key:<35} {n}/{len(teams)}")


if __name__ == "__main__":
    main()
