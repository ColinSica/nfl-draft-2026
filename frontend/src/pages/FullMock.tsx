/**
 * Full Mock — team-row draft board.
 *
 * One row per team (32 total), ordered by each team's earliest pick.
 * Left side of each row is a team-colored header (abbr, name, pick
 * count). The right side is a wrap-friendly strip of that team's
 * picks in pick-ascending order, with subtle round dividers so you
 * can read the class like a draft report card.
 *
 * Click any pick card to surface the team-specific reasoning, model
 * factors, and close alternates below the board.
 *
 * Data comes from scripts/build_full_mock.py — a greedy team-fit walk
 * over the independent model's 727-prospect board.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
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

const POS_FILTERS = ['All', 'QB', 'RB', 'WR', 'TE', 'OT', 'IOL', 'EDGE',
                     'DL', 'IDL', 'LB', 'CB', 'S'];

// ─── One pick card inside a team's draft strip ──────────────────────
// Team-color header strip + cream body with dark ink — readable on
// any team's palette, unlike all-dark-on-dark.
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
      className={`relative w-[160px] shrink-0 text-left overflow-hidden border bg-paper-raised
                  transition focus:outline-none
                  ${selected
                    ? 'ring-2 ring-accent-brass ring-offset-1 ring-offset-paper border-accent-brass z-10 scale-[1.02]'
                    : 'border-ink/15 hover:z-10 hover:scale-[1.02] hover:shadow-card-raised'}
                  ${dimmed ? 'opacity-25 grayscale' : ''}`}
      title={`#${pick.pick} · ${pick.player} · ${pick.position} · ${pick.college ?? ''}`}
    >
      {/* Header strip — team colors carry the identity */}
      <div
        className="flex items-center justify-between gap-1 px-2 py-1"
        style={{ background: tc.primary, color: headerInk }}
      >
        <span className="display-num text-[0.62rem] tabular-nums tracking-wider font-semibold">
          #{pick.pick}
        </span>
        <span className="font-mono text-[0.55rem] opacity-80">
          R{pick.round}
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
        <div className="body-serif text-[0.85rem] font-semibold leading-[1.15] text-ink line-clamp-2 min-h-[2.05rem]">
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

// ─── Team row — header + pick strip ─────────────────────────────────
function TeamRow({
  team, picks, posFilter, selectedPick, onSelect, scrollTargetRef,
}: {
  team: string;
  picks: FullPick[];
  posFilter: string;
  selectedPick: number | null;
  onSelect: (pick: number) => void;
  scrollTargetRef?: (el: HTMLDivElement | null) => void;
}) {
  const tc = teamColor(team);
  const ink = contrastInk(tc.primary);
  const secInk = contrastInk(tc.secondary);

  // Intersperse subtle round dividers between picks from different rounds.
  const items: Array<{ kind: 'pick'; p: FullPick } | { kind: 'rd'; round: number }> = [];
  let lastRound = -1;
  picks.forEach(p => {
    if (p.round !== lastRound) {
      items.push({ kind: 'rd', round: p.round });
      lastRound = p.round;
    }
    items.push({ kind: 'pick', p });
  });

  return (
    <div
      ref={scrollTargetRef}
      className="flex items-stretch border-b border-ink-edge/60 last:border-b-0"
    >
      {/* Team header — sticky to the left edge of the scroll container */}
      <Link
        to={`/team/${team}`}
        className="sticky left-0 z-10 w-[108px] shrink-0 flex flex-col justify-center px-3 py-3
                   hover:brightness-110 transition relative"
        style={{ background: tc.primary, color: ink }}
        title={tc.name}
      >
        <div
          className="absolute top-0 bottom-0 right-0 w-[3px]"
          style={{ background: tc.secondary }}
        />
        <span className="display-broadcast text-xl leading-none">{team}</span>
        <span className="font-sans text-[0.62rem] font-medium opacity-85 mt-0.5 leading-tight">
          {tc.name}
        </span>
        <span
          className="caps-tight text-[0.55rem] tabular-nums mt-1 inline-block px-1.5 py-[1px] self-start leading-tight"
          style={{ background: tc.secondary, color: secInk }}
        >
          {picks.length} PICKS
        </span>
      </Link>

      {/* Pick strip — wraps onto multiple lines if a team has a large haul */}
      <div className="flex-1 bg-paper-surface p-2 flex flex-wrap items-start gap-2">
        {items.map((it, i) => {
          if (it.kind === 'rd') {
            return (
              <div
                key={`rd-${it.round}-${i}`}
                className="flex items-center self-stretch px-0.5"
                title={`Round ${it.round}`}
              >
                <span className="display-broadcast text-[0.62rem] text-ink-muted rotate-0 tracking-wider">
                  R{it.round}
                </span>
              </div>
            );
          }
          const p = it.p;
          const posHit = posFilter === 'All' || p.position === posFilter;
          return (
            <PickCard
              key={p.pick}
              pick={p}
              selected={selectedPick === p.pick}
              dimmed={!posHit}
              onClick={() => onSelect(p.pick)}
            />
          );
        })}
      </div>
    </div>
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
  const [selectedPick, setSelectedPick] = useState<number | null>(null);
  const teamRowRefs = useRef<Record<string, HTMLDivElement | null>>({});

  useEffect(() => {
    fetch('/api/full-mock')
      .then(r => r.json())
      .then(d => setData(d))
      .catch(e => setErr(String(e)));
  }, []);

  // Group picks by team, sort by earliest pick (TEN first → MR. IRRELEVANT last).
  const teamRows = useMemo(() => {
    const byTeam = new Map<string, FullPick[]>();
    (data?.picks ?? []).forEach(p => {
      const arr = byTeam.get(p.team) ?? [];
      arr.push(p);
      byTeam.set(p.team, arr);
    });
    const rows = Array.from(byTeam.entries()).map(([team, picks]) => ({
      team,
      picks: picks.slice().sort((a, b) => a.pick - b.pick),
    }));
    rows.sort((a, b) => a.picks[0].pick - b.picks[0].pick);
    return rows;
  }, [data]);

  const teams = useMemo(() => teamRows.map(r => r.team), [teamRows]);

  const visibleRows = useMemo(
    () => (teamFilter ? teamRows.filter(r => r.team === teamFilter) : teamRows),
    [teamRows, teamFilter],
  );

  const selected = useMemo(
    () => (data?.picks ?? []).find(p => p.pick === selectedPick) ?? null,
    [data, selectedPick],
  );

  useEffect(() => {
    if (!teamFilter) return;
    const el = teamRowRefs.current[teamFilter];
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [teamFilter]);

  return (
    <div className="space-y-6 pb-16">
      <SectionHeader
        kicker="The full mock"
        title="All seven rounds, 257 picks."
        deck="Team-by-team draft report cards. Every team's class laid out on its own row, in pick order, colored in team paint. Tap a card for the per-pick reasoning and the close alternates the team considered. Data comes from the independent team-agent model — no fabricated scouting prose."
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
                <option value="">All 32</option>
                {teams.map(t => (
                  <option key={t} value={t}>{t}</option>
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

          {/* Board */}
          <div className="border border-ink bg-paper">
            {visibleRows.map(row => (
              <TeamRow
                key={row.team}
                team={row.team}
                picks={row.picks}
                posFilter={posFilter}
                selectedPick={selectedPick}
                onSelect={(pk) => setSelectedPick(prev => (prev === pk ? null : pk))}
                scrollTargetRef={el => { teamRowRefs.current[row.team] = el; }}
              />
            ))}
          </div>

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
