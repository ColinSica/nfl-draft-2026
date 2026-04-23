/**
 * Full Mock — every pick, all seven rounds (257 picks).
 * Each row is reached by greedy team-fit assignment against the independent
 * model's Kalshi-anchored player board. Grouped by round, filterable.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { SectionHeader, SmallCaps, MissingText, Footnote } from '../components/editorial';
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

function RoundBlock({
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
  return (
    <section className="space-y-3">
      <div className="flex items-baseline justify-between border-b-2 border-ink pb-1.5">
        <h2 className="display-broadcast text-2xl">{ROUND_LABELS[round]}</h2>
        <span className="caps-tight text-ink-muted text-xs">
          {list.length} pick{list.length === 1 ? '' : 's'}
        </span>
      </div>
      <div className="divide-y divide-ink-edge">
        {list.map(p => <PickRow key={p.pick} pick={p} />)}
      </div>
    </section>
  );
}

function PickRow({ pick }: { pick: FullPick }) {
  const [open, setOpen] = useState(false);
  const tc = teamColor(pick.team);
  return (
    <div
      className="py-2.5 px-2 hover:bg-paper-hover transition-all cursor-pointer"
      onClick={() => setOpen(v => !v)}
    >
      <div className="flex items-baseline gap-3 flex-wrap">
        <span className="display-num text-lg w-10 tabular-nums text-ink-muted shrink-0">
          {String(pick.pick).padStart(3, '0')}
        </span>
        <Link
          to={`/team/${pick.team}`}
          onClick={e => e.stopPropagation()}
          className="display-broadcast text-sm w-12 text-center shrink-0 px-1.5 py-0.5"
          style={{ background: tc.primary,
                   color: tc.secondary === '#000000' ? '#FFFFFF' : tc.secondary }}
          title={tc.name}
        >
          {pick.team}
        </Link>
        <span className="body-serif text-base font-medium flex-1 min-w-[160px]">
          {pick.player}
        </span>
        <span className="font-mono text-xs text-ink-muted w-10 text-right shrink-0">
          {pick.position}
        </span>
        <span className="font-mono text-[0.65rem] text-ink-soft w-24 truncate hidden sm:inline text-right shrink-0">
          {pick.college ?? ''}
        </span>
        <span className="font-mono text-[0.65rem] text-ink-muted w-10 text-right shrink-0">
          #{pick.rank}
        </span>
      </div>
      {open && (
        <div className="mt-2 pl-[3.25rem] space-y-2 text-xs">
          <p className="body-serif text-ink leading-relaxed italic">
            {pick.reasoning}
          </p>
          <div className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-[0.65rem] text-ink-muted">
            <span>grade <span className="text-ink">{pick.factors.grade.toFixed(2)}</span></span>
            <span>need <span className="text-ink">{pick.factors.need >= 0 ? '+' : ''}{pick.factors.need.toFixed(2)}</span></span>
            {pick.factors.scheme > 0 && (
              <span>scheme <span className="text-accent-brass">+{pick.factors.scheme.toFixed(2)}</span></span>
            )}
            {pick.factors.visit > 0 && (
              <span>visit <span className="text-accent-brass">+{pick.factors.visit.toFixed(2)}</span></span>
            )}
            {pick.factors.aff !== 0 && (
              <span>GM <span className="text-ink">{pick.factors.aff >= 0 ? '+' : ''}{pick.factors.aff.toFixed(2)}</span></span>
            )}
            {pick.factors.reach < 0 && (
              <span>reach <span className="text-live">{pick.factors.reach.toFixed(2)}</span></span>
            )}
            <span className="ml-auto">total <span className="text-ink font-semibold">{pick.score.toFixed(2)}</span></span>
          </div>
          {pick.alternates && pick.alternates.length > 0 && (
            <div>
              <SmallCaps tight className="text-ink-muted block mb-1">
                Top alternates
              </SmallCaps>
              <div className="flex flex-wrap gap-3 text-[0.7rem]">
                {pick.alternates.map(a => (
                  <span key={a.player} className="font-mono text-ink-soft">
                    {a.player}
                    <span className="text-ink-edge mx-1">·</span>
                    <span className="text-ink-muted">{a.position}</span>
                    <span className="text-ink-edge mx-1">·</span>
                    <span className="text-ink-muted">#{a.rank}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
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
        title="All 257 picks, seven rounds."
        deck="A greedy team-fit walk through the independent model's 727-prospect board. Kalshi-anchored grades meet each team's roster needs, GM affinities, scheme premiums, and documented pre-draft visits. Click any pick for the scoring breakdown."
      />

      {err && <MissingText>Full mock unavailable: {err}</MissingText>}
      {!data && !err && (
        <MissingText>Loading 257 picks…</MissingText>
      )}

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

          {/* Round blocks */}
          <div className="space-y-10">
            {[1,2,3,4,5,6,7].map(rnd => (
              <RoundBlock
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
