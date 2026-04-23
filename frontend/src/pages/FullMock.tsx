/**
 * Full Mock — every pick, all seven rounds (257 picks).
 *
 * Layout matches how real draft sites (ESPN/NFL.com/PFF) present multi-round
 * mocks: Round 1 gets full prose per pick; Rounds 2-7 are compact tables.
 * Filters available for position and team.
 *
 * Data comes from scripts/build_full_mock.py — a greedy team-fit walk over
 * the independent model's 727-prospect board. No fabricated info: reasoning
 * is generated from real team roster_needs, documented GM draft history,
 * confirmed pre-draft visits, and PFF-anchored prospect grades.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { SectionHeader, SmallCaps, MissingText, Footnote, HRule } from '../components/editorial';
import { teamColor } from '../lib/teamColors';

type FullPick = {
  pick: number;
  round: number;
  team: string;
  player: string;
  position: string;
  college: string | null;
  rank: number;
  tier: string;
  reasoning: string;
  score: number;
  factors: {
    grade: number;
    need: number;
    aff: number;
    scheme: number;
    visit: number;
    reach: number;
    late: number;
  };
  alternates: { player: string; position: string; rank: number; score: number }[];
};

type FullMockResp = {
  generated_at: string | null;
  source_board_mtime?: string;
  n_picks: number;
  methodology?: string | null;
  picks: FullPick[];
};

const ROUND_LABELS: Record<number, string> = {
  1: 'Round One', 2: 'Round Two', 3: 'Round Three', 4: 'Round Four',
  5: 'Round Five', 6: 'Round Six', 7: 'Round Seven',
};

const POS_FILTERS = ['All', 'QB', 'RB', 'WR', 'TE', 'OT', 'IOL', 'EDGE',
                     'DL', 'IDL', 'LB', 'CB', 'S'];

// ─── Round One card — full prose, alternates, factor chips ────────────
function Round1Card({ pick }: { pick: FullPick }) {
  const tc = teamColor(pick.team);
  return (
    <article className="card">
      <div className="h-0.5" style={{ background: tc.primary }} />
      <div className="p-4 sm:p-5">
        <div className="flex items-start gap-4 flex-wrap">
          <div className="flex flex-col items-center justify-center shrink-0 min-w-[72px]">
            <span className="caps-tight text-ink-muted text-[0.6rem]">Pick</span>
            <span className="display-num text-4xl leading-none" style={{ color: tc.primary }}>
              {String(pick.pick).padStart(2, '0')}
            </span>
          </div>
          <Link
            to={`/team/${pick.team}`}
            className="display-broadcast text-sm px-2 py-1 shrink-0"
            style={{ background: tc.primary,
                     color: tc.secondary === '#000000' ? '#FFFFFF' : tc.secondary }}
            title={tc.name}
          >
            {pick.team}
          </Link>
          <div className="flex-1 min-w-[180px]">
            <h3 className="display-broadcast text-xl sm:text-2xl text-ink leading-tight">
              {pick.player}
            </h3>
            <div className="font-mono text-xs text-ink-muted mt-1 flex flex-wrap gap-x-2 gap-y-0.5 items-baseline">
              <span>{pick.position}</span>
              <span className="text-ink-edge">·</span>
              <span>{pick.college ?? ''}</span>
              <span className="text-ink-edge">·</span>
              <span>board #{pick.rank}</span>
              {pick.tier && (
                <>
                  <span className="text-ink-edge">·</span>
                  <span>{pick.tier}</span>
                </>
              )}
            </div>
          </div>
        </div>

        <HRule className="my-3" />

        <p className="body-serif text-sm sm:text-base text-ink leading-relaxed">
          {pick.reasoning}
        </p>

        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <SmallCaps tight className="text-ink-muted block mb-1.5">
              Model factors
            </SmallCaps>
            <div className="flex flex-wrap gap-x-3 gap-y-1 font-mono text-[0.65rem] text-ink-muted">
              <span>grade <span className="text-ink">{pick.factors.grade.toFixed(2)}</span></span>
              <span>need <span className="text-ink">{pick.factors.need >= 0 ? '+' : ''}{pick.factors.need.toFixed(2)}</span></span>
              {pick.factors.scheme > 0 && (
                <span>scheme <span className="text-accent-brass">+{pick.factors.scheme.toFixed(2)}</span></span>
              )}
              {pick.factors.visit > 0 && (
                <span>visit <span className="text-accent-brass">+{pick.factors.visit.toFixed(2)}</span></span>
              )}
              {pick.factors.aff !== 0 && (
                <span>GM-history <span className="text-ink">{pick.factors.aff >= 0 ? '+' : ''}{pick.factors.aff.toFixed(2)}</span></span>
              )}
              {pick.factors.reach < 0 && (
                <span>reach <span className="text-live">{pick.factors.reach.toFixed(2)}</span></span>
              )}
            </div>
          </div>
          {pick.alternates && pick.alternates.length > 0 && (
            <div>
              <SmallCaps tight className="text-ink-muted block mb-1.5">
                Close alternates
              </SmallCaps>
              <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[0.7rem] font-mono text-ink-soft">
                {pick.alternates.slice(0, 3).map(a => (
                  <span key={a.player}>
                    <span className="text-ink">{a.player}</span>
                    <span className="text-ink-edge mx-1">·</span>
                    {a.position}
                    <span className="text-ink-edge mx-1">·</span>
                    #{a.rank}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}

// ─── Rounds 2-7 compact table row ────────────────────────────────────
function CompactRow({ pick }: { pick: FullPick }) {
  const tc = teamColor(pick.team);
  return (
    <tr className="hover:bg-paper-hover transition">
      <td className="num text-ink-muted font-mono text-xs w-12">
        {pick.pick}
      </td>
      <td className="w-14">
        <Link
          to={`/team/${pick.team}`}
          className="inline-block display-broadcast text-[0.7rem] px-1.5 py-0.5"
          style={{ background: tc.primary,
                   color: tc.secondary === '#000000' ? '#FFFFFF' : tc.secondary }}
        >
          {pick.team}
        </Link>
      </td>
      <td className="body-serif text-sm font-medium text-ink">
        {pick.player}
      </td>
      <td className="font-mono text-xs text-ink-muted w-12">
        {pick.position}
      </td>
      <td className="font-serif italic text-xs text-ink-soft hidden md:table-cell">
        {pick.college ?? ''}
      </td>
      <td className="font-mono text-[0.65rem] text-ink-muted w-12 text-right">
        #{pick.rank}
      </td>
    </tr>
  );
}

function CompactRound({
  round, picks, posFilter, teamFilter,
}: {
  round: number;
  picks: FullPick[];
  posFilter: string;
  teamFilter: string;
}) {
  const list = picks.filter(p =>
    (posFilter === 'All' || p.position === posFilter) &&
    (!teamFilter || p.team === teamFilter)
  );
  if (list.length === 0) return null;
  const byPos: Record<string, number> = {};
  list.forEach(p => { byPos[p.position] = (byPos[p.position] ?? 0) + 1; });
  const posSummary = Object.entries(byPos)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([p, c]) => `${c}${p}`)
    .join(' · ');
  return (
    <section className="space-y-2">
      <div className="flex items-baseline justify-between border-b-2 border-ink pb-1.5 flex-wrap gap-2">
        <div className="flex items-baseline gap-3 flex-wrap">
          <h2 className="display-broadcast text-xl">{ROUND_LABELS[round]}</h2>
          <span className="font-mono text-[0.65rem] text-ink-muted">{posSummary}</span>
        </div>
        <span className="caps-tight text-ink-muted text-xs">
          {list.length} pick{list.length === 1 ? '' : 's'}
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <tbody className="divide-y divide-ink-edge">
            {list.map(p => <CompactRow key={p.pick} pick={p} />)}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Round1Block({
  picks, posFilter, teamFilter,
}: {
  picks: FullPick[];
  posFilter: string;
  teamFilter: string;
}) {
  const list = picks.filter(p =>
    (posFilter === 'All' || p.position === posFilter) &&
    (!teamFilter || p.team === teamFilter)
  );
  if (list.length === 0) return null;
  const byPos: Record<string, number> = {};
  list.forEach(p => { byPos[p.position] = (byPos[p.position] ?? 0) + 1; });
  const posSummary = Object.entries(byPos)
    .sort((a, b) => b[1] - a[1])
    .map(([p, c]) => `${c}${p}`)
    .join(' · ');
  return (
    <section className="space-y-4">
      <div className="flex items-baseline justify-between border-b-2 border-ink pb-1.5 flex-wrap gap-2">
        <div className="flex items-baseline gap-3 flex-wrap">
          <h2 className="display-broadcast text-3xl">Round One</h2>
          <span className="font-mono text-xs text-ink-muted">{posSummary}</span>
        </div>
        <span className="caps-tight text-ink-muted text-xs">
          {list.length} picks · full prose per selection
        </span>
      </div>
      <div className="grid grid-cols-1 gap-3">
        {list.map(p => <Round1Card key={p.pick} pick={p} />)}
      </div>
    </section>
  );
}

export function FullMock() {
  const [data, setData] = useState<FullMockResp | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [posFilter, setPosFilter] = useState('All');
  const [teamFilter, setTeamFilter] = useState('');

  useEffect(() => {
    fetch('/api/full-mock')
      .then(r => r.json())
      .then(d => setData(d))
      .catch(e => setErr(String(e)));
  }, []);

  const byRound = useMemo(() => {
    const map = new Map<number, FullPick[]>();
    (data?.picks ?? []).forEach(p => {
      if (!map.has(p.round)) map.set(p.round, []);
      map.get(p.round)!.push(p);
    });
    return map;
  }, [data]);

  const teams = useMemo(() => {
    const s = new Set<string>();
    (data?.picks ?? []).forEach(p => s.add(p.team));
    return Array.from(s).sort();
  }, [data]);

  return (
    <div className="space-y-8 pb-16">
      <SectionHeader
        kicker="The full mock"
        title="All seven rounds, 257 picks."
        deck="A greedy team-fit walk through the independent model's prospect board. Reasoning is built from real team roster needs (post-free-agency), documented GM draft history 2019–2025, confirmed pre-draft visits, and PFF-anchored tape grades — no fabricated scouting prose. Round One gets full treatment; Rounds Two through Seven are compact for scannability, as most drafts already are."
      />

      {err && <MissingText>Full mock unavailable: {err}</MissingText>}
      {!data && !err && <MissingText>Loading 257 picks…</MissingText>}

      {data && data.picks.length === 0 && (
        <MissingText>
          The full mock has not been generated yet. Run
          <code className="font-mono text-xs mx-1">python scripts/build_full_mock.py</code>
          on the server.
        </MissingText>
      )}

      {data && data.picks.length > 0 && (
        <>
          {/* Filters */}
          <div className="card p-4 flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5">
              <SmallCaps tight className="text-ink-muted">Position</SmallCaps>
              <div className="flex flex-wrap gap-1">
                {POS_FILTERS.map(p => (
                  <button
                    key={p}
                    onClick={() => setPosFilter(p)}
                    className={`px-2 py-1 caps-tight text-[0.65rem] border transition ${
                      posFilter === p
                        ? 'bg-ink text-paper border-ink'
                        : 'bg-paper text-ink-muted border-ink-edge hover:border-ink hover:text-ink'
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-1.5 ml-auto">
              <SmallCaps tight className="text-ink-muted">Team</SmallCaps>
              <select
                value={teamFilter}
                onChange={e => setTeamFilter(e.target.value)}
                className="font-mono text-xs border border-ink-edge px-2 py-1 bg-paper-surface hover:border-ink"
              >
                <option value="">All teams</option>
                {teams.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              {(posFilter !== 'All' || teamFilter) && (
                <button
                  onClick={() => { setPosFilter('All'); setTeamFilter(''); }}
                  className="caps-tight text-[0.65rem] text-ink-muted hover:text-ink"
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Round 1: full prose cards */}
          <Round1Block
            picks={byRound.get(1) ?? []}
            posFilter={posFilter}
            teamFilter={teamFilter}
          />

          {/* Rounds 2-7: compact tables */}
          <div className="space-y-8">
            {[2,3,4,5,6,7].map(rnd => (
              <CompactRound
                key={rnd}
                round={rnd}
                picks={byRound.get(rnd) ?? []}
                posFilter={posFilter}
                teamFilter={teamFilter}
              />
            ))}
          </div>

          <section className="border-t-2 border-ink pt-5">
            <Footnote>
              {data.methodology ?? ''}
              {data.generated_at && (
                <>
                  {' '}Generated{' '}
                  <span className="font-mono text-[0.65rem]">
                    {new Date(data.generated_at).toLocaleString()}
                  </span>.
                </>
              )}
            </Footnote>
          </section>
        </>
      )}
    </div>
  );
}
