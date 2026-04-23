/**
 * Full Mock — Sleeper-style team-column draft board.
 *
 * Columns = every team that has picks, ordered by their first pick.
 * Rows = rounds 1–7. Each cell holds the pick(s) that team made in
 * that round (usually one; teams can have zero or several after
 * trades). Click a card to surface the team-specific reasoning,
 * model factors, and close alternates beneath the board.
 *
 * Data comes from scripts/build_full_mock.py — a greedy team-fit walk
 * over the independent model's 727-prospect board. Reasoning is built
 * from real team roster_needs, documented GM draft history, confirmed
 * pre-draft visits, and PFF-anchored prospect grades.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { X } from 'lucide-react';
import { SectionHeader, SmallCaps, MissingText, Footnote } from '../components/editorial';
import { teamColor } from '../lib/teamColors';

// Pick a readable text color for a given team-primary hex.
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

const POS_FILTERS = ['All', 'QB', 'RB', 'WR', 'TE', 'OT', 'IOL', 'EDGE',
                     'DL', 'IDL', 'LB', 'CB', 'S'];

const COL_WIDTH = 132;        // px
const GUTTER_WIDTH = 44;      // px — left round-label column

// ─── Team column header ─────────────────────────────────────────────
function TeamHeader({ team, pickCount }: { team: string; pickCount: number }) {
  const tc = teamColor(team);
  const ink = contrastInk(tc.primary);
  return (
    <Link
      to={`/team/${team}`}
      className="flex flex-col items-center justify-center h-full px-1 py-2 border-r border-paper/20 hover:brightness-110 transition"
      style={{ background: tc.primary, color: ink }}
      title={tc.name}
    >
      <span className="display-broadcast text-base leading-none">{team}</span>
      <span
        className="font-mono text-[0.55rem] mt-0.5 opacity-70 tabular-nums tracking-wider"
      >
        {pickCount} PK{pickCount === 1 ? '' : 'S'}
      </span>
      <span
        className="absolute bottom-0 left-0 right-0 h-[2px]"
        style={{ background: tc.secondary }}
      />
    </Link>
  );
}

// ─── Player card inside a (team, round) cell ────────────────────────
function PickCell({
  pick, selected, dimmed, onClick,
}: {
  pick: FullPick;
  selected: boolean;
  dimmed: boolean;
  onClick: () => void;
}) {
  const tc = teamColor(pick.team);
  const ink = contrastInk(tc.primary);
  const chipOnDark = ink === '#FAF6E6';
  const rankDelta = pick.rank - pick.pick;
  const value = rankDelta <= -5;
  const reach = rankDelta >= 10;

  return (
    <button
      type="button"
      onClick={onClick}
      className={`relative w-full text-left overflow-hidden border border-ink/10 transition
                  focus:outline-none group
                  ${selected ? 'ring-2 ring-accent-brass ring-offset-1 ring-offset-paper z-10 scale-[1.02]' : ''}
                  ${dimmed ? 'opacity-25 grayscale' : 'hover:z-10 hover:scale-[1.02] hover:shadow-card-raised'}`}
      style={{ background: tc.primary, color: ink }}
      title={`#${pick.pick} · ${pick.player} · ${pick.position} · ${pick.college ?? ''}`}
    >
      {/* Secondary-color accent bar */}
      <div className="absolute top-0 left-0 right-0 h-[2px]" style={{ background: tc.secondary }} />

      <div className="px-1.5 pt-2 pb-1.5 flex flex-col gap-0.5">
        <div className="flex items-center justify-between">
          <span className="display-num text-[0.55rem] tabular-nums opacity-70 tracking-wider">
            #{pick.pick}
          </span>
          <span
            className="font-mono text-[0.52rem] px-1 py-[1px] font-semibold tracking-wide leading-none"
            style={{
              background: chipOnDark ? 'rgba(250,246,230,0.18)' : 'rgba(11,31,58,0.14)',
              color: ink,
            }}
          >
            {pick.position}
          </span>
        </div>
        <div className="body-serif text-[0.78rem] font-semibold leading-[1.1] line-clamp-2">
          {pick.player}
        </div>
        <div className="font-mono text-[0.55rem] italic opacity-70 truncate">
          {pick.college ?? '—'}
        </div>
        <div className="flex items-center justify-between gap-1 pt-0.5">
          <span className="font-mono text-[0.52rem] opacity-60 tabular-nums">
            rk {pick.rank}
          </span>
          {value && (
            <span className="caps-tight text-[0.5rem] font-bold px-1 leading-tight"
                  style={{ background: '#B68A2F', color: '#0B1F3A' }}>
              VAL
            </span>
          )}
          {reach && (
            <span className="caps-tight text-[0.5rem] font-bold px-1 leading-tight"
                  style={{ background: '#8C2E2A', color: '#FAF6E6' }}>
              RCH
            </span>
          )}
        </div>
      </div>
    </button>
  );
}

// ─── Detail panel shown below the board ─────────────────────────────
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
  const [selectedPick, setSelectedPick] = useState<number | null>(null);
  const teamColRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    fetch('/api/full-mock')
      .then(r => r.json())
      .then(d => setData(d))
      .catch(e => setErr(String(e)));
  }, []);

  // Teams ordered by earliest pick (so TEN/first-overall is leftmost).
  const teamsOrdered = useMemo(() => {
    const byTeam = new Map<string, { team: string; first: number; picks: FullPick[] }>();
    (data?.picks ?? []).forEach(p => {
      const cur = byTeam.get(p.team);
      if (cur) {
        cur.picks.push(p);
        cur.first = Math.min(cur.first, p.pick);
      } else {
        byTeam.set(p.team, { team: p.team, first: p.pick, picks: [p] });
      }
    });
    return Array.from(byTeam.values()).sort((a, b) => a.first - b.first);
  }, [data]);

  // Quick lookup: (team, round) → picks in that cell, pick-ascending.
  const cellMap = useMemo(() => {
    const m = new Map<string, FullPick[]>();
    (data?.picks ?? []).forEach(p => {
      const k = `${p.team}:${p.round}`;
      if (!m.has(k)) m.set(k, []);
      m.get(k)!.push(p);
    });
    m.forEach(arr => arr.sort((a, b) => a.pick - b.pick));
    return m;
  }, [data]);

  const selected = useMemo(
    () => (data?.picks ?? []).find(p => p.pick === selectedPick) ?? null,
    [data, selectedPick],
  );

  // Scroll to a team column when the team filter changes.
  useEffect(() => {
    if (!teamFilter) return;
    const el = teamColRefs.current[teamFilter];
    const wrap = scrollRef.current;
    if (el && wrap) {
      wrap.scrollTo({ left: el.offsetLeft - GUTTER_WIDTH - 8, behavior: 'smooth' });
    }
  }, [teamFilter, teamsOrdered.length]);

  const rounds = [1, 2, 3, 4, 5, 6, 7];

  return (
    <div className="space-y-6 pb-16">
      <SectionHeader
        kicker="The full mock"
        title="All seven rounds, 257 picks."
        deck="Sleeper-style team-column board — every team across the top, every pick stacked underneath, colored in team paint. Tap any card for the team-specific reasoning, model factors, and close alternates. Data comes from the independent team-agent model — no fabricated scouting prose."
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
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-3 bg-paper-surface p-3 border border-ink-edge">
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
                  {teamsOrdered.map(t => (
                    <option key={t.team} value={t.team}>{t.team}</option>
                  ))}
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
            <p className="font-mono text-[0.62rem] text-ink-soft italic">
              Scroll horizontally through the team columns. Tap a card for the full reasoning.
            </p>
          </div>

          {/* ── The board ────────────────────────────────────────── */}
          <div
            ref={scrollRef}
            className="relative overflow-x-auto border border-ink bg-paper-surface"
            style={{ scrollbarGutter: 'stable' }}
          >
            {/* Header row — sticky to top of the scroll container */}
            <div
              className="grid sticky top-0 z-20 bg-ink"
              style={{
                gridTemplateColumns: `${GUTTER_WIDTH}px repeat(${teamsOrdered.length}, ${COL_WIDTH}px)`,
                height: 48,
              }}
            >
              <div className="sticky left-0 z-30 bg-ink border-r border-paper/20 flex items-center justify-center">
                <span className="caps-tight text-[0.55rem] text-paper/70 tracking-wider">RD</span>
              </div>
              {teamsOrdered.map(t => (
                <div
                  key={t.team}
                  ref={el => { teamColRefs.current[t.team] = el; }}
                  className="relative"
                >
                  <TeamHeader team={t.team} pickCount={t.picks.length} />
                </div>
              ))}
            </div>

            {/* Round rows */}
            {rounds.map(round => {
              // max picks any single team has this round → row min-height
              let maxPerCell = 1;
              teamsOrdered.forEach(t => {
                const n = (cellMap.get(`${t.team}:${round}`) ?? []).length;
                if (n > maxPerCell) maxPerCell = n;
              });
              const rowHeight = Math.max(110, 110 * maxPerCell + 6 * (maxPerCell - 1));

              return (
                <div
                  key={round}
                  className="grid border-t-2 border-ink"
                  style={{
                    gridTemplateColumns: `${GUTTER_WIDTH}px repeat(${teamsOrdered.length}, ${COL_WIDTH}px)`,
                  }}
                >
                  {/* Round gutter — sticky to the left edge */}
                  <div
                    className="sticky left-0 z-10 bg-paper border-r border-ink flex items-center justify-center"
                    style={{ minHeight: rowHeight }}
                  >
                    <div className="flex flex-col items-center gap-0.5">
                      <span className="display-broadcast text-[0.7rem] text-ink">R{round}</span>
                    </div>
                  </div>

                  {/* Cells */}
                  {teamsOrdered.map(t => {
                    const cellPicks = cellMap.get(`${t.team}:${round}`) ?? [];
                    return (
                      <div
                        key={t.team}
                        className="border-r border-ink-edge/60 p-1 flex flex-col gap-1.5 bg-paper/60"
                        style={{ minHeight: rowHeight }}
                      >
                        {cellPicks.length === 0 ? (
                          <div className="flex-1 flex items-center justify-center">
                            <span className="font-mono text-[0.6rem] text-ink-edge">—</span>
                          </div>
                        ) : (
                          cellPicks.map(p => {
                            const posHit = posFilter === 'All' || p.position === posFilter;
                            const teamHit = !teamFilter || p.team === teamFilter;
                            return (
                              <PickCell
                                key={p.pick}
                                pick={p}
                                selected={selected?.pick === p.pick}
                                dimmed={!posHit || !teamHit}
                                onClick={() =>
                                  setSelectedPick(prev => (prev === p.pick ? null : p.pick))
                                }
                              />
                            );
                          })
                        )}
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>

          {/* Detail panel — below the board so it doesn't fight the horizontal scroll */}
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
