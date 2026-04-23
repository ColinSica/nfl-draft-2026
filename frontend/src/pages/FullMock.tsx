/**
 * Full Mock — pick-order list of team-color cards.
 *
 * Chronological: pick 1 through 257, grouped by round. Each pick is
 * a card with a team-color header strip (pick #, round, team, pos)
 * over a cream body with dark ink for the player name — readable on
 * every team's palette. Round tabs switch the active round. Click
 * any card to surface the team-specific reasoning, model factors,
 * and close alternates beneath the grid.
 *
 * Data comes from scripts/build_full_mock.py — a greedy team-fit walk
 * over the independent model's 727-prospect board.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { X } from 'lucide-react';
import { SectionHeader, SmallCaps, MissingText, Footnote } from '../components/editorial';
import { teamColor } from '../lib/teamColors';

function contrastInk(hex: string): string {
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return lum > 0.6 ? '#0B1F3A' : '#FAF6E6';
}

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

// ─── Pick card — team header strip + cream body ─────────────────────
function PickCard({
  pick, selected, dimmed, onClick,
}: {
  pick: FullPick;
  selected: boolean;
  dimmed: boolean;
  onClick: () => void;
}) {
  const tc = teamColor(pick.team);
  const headerInk = contrastInk(tc.primary);
  const secInk = contrastInk(tc.secondary);
  const rankDelta = pick.rank - pick.pick;
  const value = rankDelta <= -5;
  const reach = rankDelta >= 10;

  return (
    <button
      type="button"
      onClick={onClick}
      className={`relative w-full text-left overflow-hidden border bg-paper-raised
                  transition focus:outline-none
                  ${selected
                    ? 'ring-2 ring-accent-brass ring-offset-1 ring-offset-paper border-accent-brass z-10 scale-[1.02]'
                    : 'border-ink/15 hover:z-10 hover:scale-[1.02] hover:shadow-card-raised'}
                  ${dimmed ? 'opacity-25 grayscale' : ''}`}
      title={`#${pick.pick} · ${pick.player} · ${pick.position} · ${pick.college ?? ''}`}
    >
      {/* Team-color header strip */}
      <div
        className="flex items-center justify-between gap-1 px-2 py-1"
        style={{ background: tc.primary, color: headerInk }}
      >
        <span className="display-num text-[0.65rem] tabular-nums tracking-wider font-semibold">
          #{pick.pick}
        </span>
        <span className="display-broadcast text-[0.6rem] opacity-95">
          {pick.team}
        </span>
        <span
          className="font-mono text-[0.56rem] font-bold px-1.5 py-[1px] leading-none rounded-sm"
          style={{ background: tc.secondary, color: secInk }}
        >
          {pick.position}
        </span>
      </div>

      {/* Body */}
      <div className="px-2 pt-1.5 pb-2 flex flex-col gap-0.5">
        <div className="body-serif text-[0.88rem] font-semibold leading-[1.15] text-ink line-clamp-2 min-h-[2.05rem]">
          {pick.player}
        </div>
        <div className="font-mono text-[0.6rem] italic text-ink-muted truncate">
          {pick.college ?? '—'}
        </div>
        <div className="flex items-center justify-between gap-1 pt-0.5">
          <span className="font-mono text-[0.56rem] text-ink-soft tabular-nums">
            rank {pick.rank}
          </span>
          {value && (
            <span className="caps-tight text-[0.52rem] font-bold px-1 leading-tight"
                  style={{ background: '#B68A2F', color: '#0B1F3A' }}>
              VAL
            </span>
          )}
          {reach && (
            <span className="caps-tight text-[0.52rem] font-bold px-1 leading-tight"
                  style={{ background: '#8C2E2A', color: '#FAF6E6' }}>
              RCH
            </span>
          )}
        </div>
      </div>
    </button>
  );
}

// ─── Detail panel ───────────────────────────────────────────────────
function PickDetailPanel({ pick, onClose }: { pick: FullPick; onClose: () => void }) {
  const tc = teamColor(pick.team);
  return (
    <section
      className="border border-ink-edge bg-paper-raised shadow-card-raised"
      style={{ borderTopWidth: 3, borderTopColor: tc.primary }}
    >
      <header className="flex items-start justify-between gap-3 px-4 py-3 border-b border-ink-edge">
        <div className="min-w-0">
          <div className="flex items-baseline gap-2 flex-wrap">
            <Link
              to={`/team/${pick.team}`}
              className="display-broadcast text-[0.65rem] px-1.5 py-0.5 shrink-0"
              style={{ background: tc.primary,
                       color: tc.secondary === '#000000' ? '#FFFFFF' : tc.secondary }}
              title={tc.name}
            >
              {pick.team}
            </Link>
            <span className="font-mono text-[0.65rem] text-ink-muted tabular-nums">
              Pick #{pick.pick}
            </span>
            <span className="font-mono text-[0.6rem] text-ink-soft">
              · Round {pick.round}
            </span>
          </div>
          <h3 className="display-broadcast text-xl mt-1 truncate">{pick.player}</h3>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="font-mono text-[0.62rem] px-1 bg-paper-surface text-ink-muted">
              {pick.position}
            </span>
            <span className="font-mono text-[0.62rem] text-ink-soft italic truncate">
              {pick.college ?? ''}
            </span>
            <span className="font-mono text-[0.62rem] text-ink-muted ml-auto">
              board rank #{pick.rank}
            </span>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-ink-muted hover:text-ink shrink-0 p-1 -mt-1 -mr-1"
          aria-label="Close"
        >
          <X size={16} />
        </button>
      </header>
      <div className="px-4 py-3 space-y-3">
        <p className="body-serif text-sm text-ink leading-relaxed">{pick.reasoning}</p>
        <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr] gap-4">
          <div>
            <SmallCaps tight className="text-ink-muted block mb-1.5">Model scoring</SmallCaps>
            <div className="flex flex-wrap gap-x-3 gap-y-1 font-mono text-[0.65rem]">
              <span className="text-ink-muted">grade <span className="text-ink">{pick.factors.grade.toFixed(2)}</span></span>
              <span className="text-ink-muted">need <span className="text-ink">{pick.factors.need >= 0 ? '+' : ''}{pick.factors.need.toFixed(2)}</span></span>
              {pick.factors.scheme > 0 && (
                <span className="text-ink-muted">scheme <span className="text-accent-brass">+{pick.factors.scheme.toFixed(2)}</span></span>
              )}
              {pick.factors.visit > 0 && (
                <span className="text-ink-muted">visit <span className="text-accent-brass">+{pick.factors.visit.toFixed(2)}</span></span>
              )}
              {pick.factors.aff !== 0 && (
                <span className="text-ink-muted">GM-history <span className="text-ink">{pick.factors.aff >= 0 ? '+' : ''}{pick.factors.aff.toFixed(2)}</span></span>
              )}
              {pick.factors.reach < 0 && (
                <span className="text-ink-muted">reach <span className="text-live">{pick.factors.reach.toFixed(2)}</span></span>
              )}
            </div>
          </div>
          {pick.alternates && pick.alternates.length > 0 && (
            <div>
              <SmallCaps tight className="text-ink-muted block mb-1.5">Close alternates</SmallCaps>
              <div className="flex flex-col gap-0.5 text-[0.7rem] font-mono text-ink-soft">
                {pick.alternates.slice(0, 3).map(a => (
                  <span key={a.player} className="truncate">
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
    </section>
  );
}

export function FullMock() {
  const [data, setData] = useState<FullMockResp | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [posFilter, setPosFilter] = useState('All');
  const [teamFilter, setTeamFilter] = useState('');
  const [activeRound, setActiveRound] = useState<number>(1);
  const [selectedPick, setSelectedPick] = useState<number | null>(null);

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
    map.forEach(arr => arr.sort((a, b) => a.pick - b.pick));
    return map;
  }, [data]);

  const teams = useMemo(() => {
    const s = new Set<string>();
    (data?.picks ?? []).forEach(p => s.add(p.team));
    return Array.from(s).sort();
  }, [data]);

  const selected = useMemo(
    () => (data?.picks ?? []).find(p => p.pick === selectedPick) ?? null,
    [data, selectedPick],
  );

  const activePicks = byRound.get(activeRound) ?? [];
  const posCount: Record<string, number> = {};
  activePicks.forEach(p => { posCount[p.position] = (posCount[p.position] ?? 0) + 1; });
  const posSummary = Object.entries(posCount)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([p, c]) => `${c}${p}`)
    .join(' · ');

  return (
    <div className="space-y-6 pb-16">
      <SectionHeader
        kicker="The full mock"
        title="All seven rounds, 257 picks."
        deck="Chronological draft board — every pick in order, rendered in team colors with a readable cream-body card. Click any card for the team-specific reasoning, model factors, and close alternates. Data comes from the independent team-agent model — no fabricated scouting prose."
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
          <div className="flex flex-wrap items-center gap-3 bg-paper-surface p-3 border border-ink-edge">
            <div className="flex items-center gap-1">
              <SmallCaps tight className="text-ink-muted mr-1">Round</SmallCaps>
              {[1,2,3,4,5,6,7].map(r => (
                <button
                  key={r}
                  onClick={() => setActiveRound(r)}
                  className={`w-7 h-7 text-xs font-mono border transition ${
                    activeRound === r
                      ? 'bg-ink text-paper border-ink'
                      : 'bg-paper text-ink-muted border-ink-edge hover:border-ink hover:text-ink'
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-1.5">
              <SmallCaps tight className="text-ink-muted">Pos</SmallCaps>
              <div className="flex flex-wrap gap-1">
                {POS_FILTERS.map(p => (
                  <button
                    key={p}
                    onClick={() => setPosFilter(p)}
                    className={`px-1.5 py-0.5 caps-tight text-[0.62rem] border transition ${
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
                className="font-mono text-xs border border-ink-edge px-2 py-1 bg-paper hover:border-ink"
              >
                <option value="">All</option>
                {teams.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              {(posFilter !== 'All' || teamFilter) && (
                <button
                  onClick={() => { setPosFilter('All'); setTeamFilter(''); }}
                  className="caps-tight text-[0.62rem] text-ink-muted hover:text-ink"
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Round header + grid */}
          <section className="border border-ink-edge bg-paper">
            <div className="flex items-baseline justify-between border-b-2 border-ink px-3 py-2 flex-wrap gap-2 bg-paper-surface">
              <div className="flex items-baseline gap-3 flex-wrap">
                <h2 className="display-broadcast text-lg">{ROUND_LABELS[activeRound]}</h2>
                <span className="font-mono text-[0.62rem] text-ink-muted">{posSummary}</span>
              </div>
              <span className="caps-tight text-ink-muted text-[0.62rem]">
                {activePicks.length} pick{activePicks.length === 1 ? '' : 's'}
              </span>
            </div>

            <div className="p-2 sm:p-3 grid gap-2 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-7">
              {activePicks.map(p => {
                const posHit = posFilter === 'All' || p.position === posFilter;
                const teamHit = !teamFilter || p.team === teamFilter;
                return (
                  <PickCard
                    key={p.pick}
                    pick={p}
                    selected={selected?.pick === p.pick}
                    dimmed={!posHit || !teamHit}
                    onClick={() =>
                      setSelectedPick(prev => (prev === p.pick ? null : p.pick))
                    }
                  />
                );
              })}
            </div>
          </section>

          {/* Detail */}
          {selected && (
            <PickDetailPanel pick={selected} onClose={() => setSelectedPick(null)} />
          )}

          <section className="border-t-2 border-ink pt-4">
            <Footnote>
              {data.methodology ?? ''}
              {data.generated_at && (
                <>
                  {' '}Generated{' '}
                  <span className="font-mono text-[0.62rem]">
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
