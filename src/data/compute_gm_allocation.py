"""
Compute per-GM positional allocation in picks 1-64 (rounds 1-2) from
historical draft data, 2020-2025 only.

For each GM with >= 3 picks at their CURRENT team since they took over,
we compute:
    team_pct[pos]    fraction of that GM's top-64 picks at each position
    league_pct[pos]  baseline fraction across all top-64 picks 2020-2025
    delta[pos]       team_pct - league_pct  (affinity signal)

Output: data/processed/gm_positional_allocation.csv
        one row per (gm, team, position_group).
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
HIST = ROOT / "data" / "processed" / "draft_with_college.csv"
OUT = ROOT / "data" / "processed" / "gm_positional_allocation.csv"

# GM → (team_abbr, first_year_at_team)
# Sources: public NFL press / team pages. Jerry Jones listed as de facto
# DAL "GM" since 1989 (pre-Will McClay era continues under Stephen Jones).
GM_TENURE: dict[str, tuple[str, int]] = {
    "Howie Roseman":      ("PHI", 2016),
    "Les Snead":          ("LAR", 2012),
    "Jason Licht":        ("TB",  2014),
    "Brett Veach":        ("KC",  2017),
    "Brian Gutekunst":    ("GB",  2018),
    "John Lynch":         ("SF",  2017),
    "Mickey Loomis":      ("NO",  2002),
    "Duke Tobin":         ("CIN", 2003),
    "Chris Ballard":      ("IND", 2017),
    "Brandon Beane":      ("BUF", 2017),
    "Eric DeCosta":       ("BAL", 2019),
    "Andrew Berry":       ("CLE", 2020),
    "Brad Holmes":        ("DET", 2021),
    "Nick Caserio":       ("HOU", 2021),
    "Terry Fontenot":     ("ATL", 2021),
    "George Paton":       ("DEN", 2021),
    "Ryan Poles":         ("CHI", 2022),
    "Kwesi Adofo-Mensah": ("MIN", 2022),
    "Omar Khan":          ("PIT", 2022),
    "Joe Schoen":         ("NYG", 2022),
    "Monti Ossenfort":    ("ARI", 2023),
    "Adam Peters":        ("WAS", 2024),
    "Joe Hortiz":         ("LAC", 2024),
    "Eliot Wolf":         ("NE",  2024),
    "Dan Morgan":         ("CAR", 2024),
    "Jerry Jones":        ("DAL", 1989),
    # Skip first-year GMs — no usable allocation signal yet:
    #   Mougey (NYJ), Borgonzi (TEN), Spytek (LV), Sullivan (MIA),
    #   Gladstone (JAX). They'll simply lack a row in the output.
}

POS_TO_GROUP = {
    "QB": "QB",
    "RB": "RB", "FB": "RB", "HB": "RB",
    "WR": "WR", "TE": "TE",
    "OT": "OT", "T": "OT",
    "G": "G", "OG": "G",
    "C": "C",
    "DE": "EDGE",
    "DT": "IDL", "NT": "IDL", "DL": "IDL",
    "LB": "LB", "ILB": "LB", "OLB": "LB",
    "MLB": "LB", "SLB": "LB", "WLB": "LB",
    "CB": "CB",
    "S": "S", "FS": "S", "SS": "S", "SAF": "S",
}


def main():
    hist = pd.read_csv(HIST)
    r1_r2 = hist[(hist["pick"].between(1, 64)) & (hist["year"] >= 2020)].copy()
    r1_r2["canon_pos"] = r1_r2["position"].map(POS_TO_GROUP)
    r1_r2 = r1_r2.dropna(subset=["canon_pos"])

    # League baseline allocation 2020-2025 (picks 1-64, valid positions)
    league_counts = (r1_r2["canon_pos"].value_counts(normalize=True).to_dict())

    rows: list[dict] = []
    for gm_name, (team, start_year) in GM_TENURE.items():
        window_start = max(start_year, 2020)
        gm_picks = r1_r2[(r1_r2["team"] == team) & (r1_r2["year"] >= window_start)]
        if len(gm_picks) < 3:
            continue
        alloc = gm_picks["canon_pos"].value_counts(normalize=True).to_dict()
        for pos, league_pct in league_counts.items():
            team_pct = alloc.get(pos, 0.0)
            rows.append({
                "gm": gm_name, "team": team, "position_group": pos,
                "team_pct": team_pct, "league_pct": league_pct,
                "delta": team_pct - league_pct,
                "n_picks_total": int(len(gm_picks)),
                "tenure_start_effective": window_start,
            })

    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    print(f"Saved -> {OUT} ({len(out)} rows, "
          f"{out['gm'].nunique()} GMs with >=3 top-64 picks since 2020)")

    # League baseline
    print("\nLeague baseline allocation (top-64 picks 2020-2025):")
    for pos, pct in sorted(league_counts.items(), key=lambda kv: -kv[1]):
        print(f"  {pos:<6} {pct:.1%}")

    # Validation — print top-3 affinities for notable GMs
    print("\nValidation — top-3 affinities per GM:")
    for gm_name in ("Howie Roseman", "Les Snead", "Mickey Loomis",
                    "Andrew Berry", "Brian Gutekunst", "Jason Licht",
                    "Brett Veach", "Brad Holmes", "Ryan Poles", "Duke Tobin"):
        sub = out[out["gm"] == gm_name]
        if sub.empty:
            continue
        team = sub["team"].iloc[0]
        n = sub["n_picks_total"].iloc[0]
        top3 = sub.sort_values("delta", ascending=False).head(3)
        top_str = ", ".join(
            f"{r['position_group']}({r['team_pct']:.0%}/{r['league_pct']:.0%}={r['delta']:+.0%})"
            for _, r in top3.iterrows())
        print(f"  {gm_name:<22} {team}  n={n:>2}  {top_str}")


if __name__ == "__main__":
    main()
