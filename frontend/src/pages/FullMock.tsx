/**
 * Full Mock — 257 picks, sortable and filterable.
 *
 * Each pick is a team-color-header + cream-body card (readable on
 * any team's palette). A Sort selector groups the board by one of:
 *   • Pick order  — round tabs switch the active round, chronological
 *   • By Round    — one section per round, all 7 stacked
 *   • By Position — one section per position, pick-ascending inside
 *   • By Team     — one section per team, ordered by earliest pick
 *
 * The Pos, Team, and Round filters *remove* non-matching picks so
 * the counts in each section header stay honest.
 *
 * Click any card to surface the team-specific reasoning, model
 * factors, and close alternates beneath the board. Data comes from
 * scripts/build_full_mock.py — a greedy team-fit walk over the
 * independent model's 727-prospect board.
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

type SortMode = 'pick' | 'round' | 'position' | 'team';

const ROUND_LABELS: Record<number, string> = {
  1: 'Round One', 2: 'Round Two', 3: 'Round Three', 4: 'Round Four',
  5: 'Round Five', 6: 'Round Six', 7: 'Round Seven',
};

const POS_FILTERS = ['All', 'QB', 'RB', 'WR', 'TE', 'OT', 'IOL', 'EDGE',
                     'DL', 'IDL', 'LB', 'CB', 'S'];

const POS_ORDER = ['QB', 'RB', 'WR', 'TE', 'OT', 'IOL', 'EDGE', 'DL', 'IDL',
                   'LB', 'CB', 'S', 'K', 'P', 'LS'];

// ─── Pick row — compact single-line list entry ──────────────────────
function PickRow({
  pick, selected, onClick,
}: {
  pick: FullPick;
  selected: boolean;
  onClick: () => void;
}) {
  const tc = teamColor(pick.team);
  const chipInk = contrastInk(tc.primary);
  const secInk = contrastInk(tc.secondary);
  const rankDelta = pick.rank - pick.pick;
  const value = rankDelta <= -5;
  const reach = rankDelta >= 10;

  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full text-left flex items-stretch group transition
                  border-b border-ink-edge/60 last:border-b-0
                  ${selected
                    ? 'bg-accent-highlight'
                    : 'odd:bg-paper even:bg-paper-raised hover:bg-paper-hover'}`}
      title={`#${pick.pick} · ${pick.player} · ${pick.position} · ${pick.college ?? ''}`}
    >
      {/* Team color edge */}
      <div className="w-1 shrink-0" style={{ background: tc.primary }} />

      <div className="flex items-center gap-3 py-2 px-3 flex-1 min-w-0 text-[0.82rem]">
        {/* Pick number */}
        <span className="display-num text-sm w-10 tabular-nums text-ink-muted shrink-0">
          {String(pick.pick).padStart(3, '0')}
        </span>

        {/* Team chip */}
        <span
          className="display-broadcast text-[0.62rem] px-1.5 py-0.5 shrink-0 w-12 text-center"
          style={{ background: tc.primary, color: chipInk }}
        >
          {pick.team}
        </span>

        {/* Player name */}
        <span className="body-serif font-semibold text-ink truncate flex-1 min-w-0">
          {pick.player}
        </span>

        {/* Position chip */}
        <span
          className="font-mono text-[0.6rem] font-bold px-1.5 py-[1px] shrink-0 w-12 text-center leading-tight rounded-sm"
          style={{ background: tc.secondary, color: secInk }}
        >
          {pick.position}
        </span>

        {/* College */}
        <span className="font-mono text-[0.66rem] text-ink-soft italic truncate shrink-0 hidden sm:inline w-40">
          {pick.college ?? ''}
        </span>

        {/* Round */}
        <span className="font-mono text-[0.62rem] text-ink-muted tabular-nums shrink-0 hidden md:inline w-10 text-right">
          R{pick.round}
        </span>

        {/* Rank */}
        <span className="font-mono text-[0.62rem] text-ink-muted tabular-nums shrink-0 w-14 text-right">
          rk {pick.rank}
        </span>

        {/* Value / Reach flag */}
        <span className="shrink-0 w-10 text-right">
          {value && (
            <span className="caps-tight text-[0.56rem] font-bold px-1 leading-tight"
                  style={{ background: '#B68A2F', color: '#0B1F3A' }}>
              VAL
            </span>
          )}
          {reach && (
            <span className="caps-tight text-[0.56rem] font-bold px-1 leading-tight"
                  style={{ background: '#8C2E2A', color: '#FAF6E6' }}>
              RCH
            </span>
          )}
        </span>
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

// ─── Section — one group header + card grid ─────────────────────────
function Section({
  title, subtitle, accentColor, picks, selectedPick, onSelect,
}: {
  title: string;
  subtitle?: string;
  accentColor?: string;
  picks: FullPick[];
  selectedPick: number | null;
  onSelect: (pk: number) => void;
}) {
  if (picks.length === 0) return null;
  return (
    <section className="border border-ink-edge bg-paper">
      <div
        className="flex items-baseline justify-between border-b-2 border-ink px-3 py-2 flex-wrap gap-2 bg-paper-surface"
        style={accentColor ? { borderBottomColor: accentColor } : undefined}
      >
        <div className="flex items-baseline gap-3 flex-wrap">
          <h2 className="display-broadcast text-lg">{title}</h2>
          {subtitle && (
            <span className="font-mono text-[0.62rem] text-ink-muted">{subtitle}</span>
          )}
        </div>
        <span className="caps-tight text-ink-muted text-[0.62rem]">
          {picks.length} pick{picks.length === 1 ? '' : 's'}
        </span>
      </div>
      <div>
        {picks.map(p => (
          <PickRow
            key={p.pick}
            pick={p}
            selected={selectedPick === p.pick}
            onClick={() => onSelect(p.pick)}
          />
        ))}
      </div>
    </section>
  );
}

export function FullMock() {
  const [data, setData] = useState<FullMockResp | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const [sortMode, setSortMode] = useState<SortMode>('pick');
  const [posFilter, setPosFilter] = useState('All');
  const [teamFilter, setTeamFilter] = useState('');
  const [roundFilter, setRoundFilter] = useState<number | 'All'>('All');
  const [activeRound, setActiveRound] = useState<number | 'all'>(1);
  const [selectedPick, setSelectedPick] = useState<number | null>(null);

  useEffect(() => {
    fetch('/api/full-mock')
      .then(r => r.json())
      .then(d => setData(d))
      .catch(e => setErr(String(e)));
  }, []);

  const allPicks = data?.picks ?? [];

  const teams = useMemo(() => {
    const s = new Set<string>();
    allPicks.forEach(p => s.add(p.team));
    return Array.from(s).sort();
  }, [allPicks]);

  // Derived: filtered + sort-ordered picks.
  const filtered = useMemo(() => {
    return allPicks.filter(p =>
      (posFilter === 'All' || p.position === posFilter) &&
      (!teamFilter || p.team === teamFilter) &&
      (roundFilter === 'All' || p.round === roundFilter)
    ).sort((a, b) => a.pick - b.pick);
  }, [allPicks, posFilter, teamFilter, roundFilter]);

  const selected = useMemo(
    () => allPicks.find(p => p.pick === selectedPick) ?? null,
    [allPicks, selectedPick],
  );

  // Build the section list based on sort mode.
  type GroupedSection = {
    key: string;
    title: string;
    subtitle?: string;
    accentColor?: string;
    picks: FullPick[];
  };

  const sections: GroupedSection[] = useMemo(() => {
    if (sortMode === 'pick') {
      // Chronological: active round, or every pick when activeRound === 'all'.
      const picks = activeRound === 'all'
        ? filtered
        : filtered.filter(p => p.round === activeRound);
      const posCount: Record<string, number> = {};
      picks.forEach(p => { posCount[p.position] = (posCount[p.position] ?? 0) + 1; });
      const posSummary = Object.entries(posCount)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 6)
        .map(([p, c]) => `${c}${p}`)
        .join(' · ');
      return [{
        key: activeRound === 'all' ? 'all' : `r${activeRound}`,
        title: activeRound === 'all' ? 'All 257 picks' : ROUND_LABELS[activeRound],
        subtitle: posSummary,
        picks,
      }];
    }

    if (sortMode === 'round') {
      // All rounds, each in its own section, pick-ascending.
      return [1,2,3,4,5,6,7].map(r => {
        const picks = filtered.filter(p => p.round === r);
        return {
          key: `r${r}`,
          title: ROUND_LABELS[r],
          subtitle: undefined,
          picks,
        };
      });
    }

    if (sortMode === 'position') {
      // Groups in POS_ORDER (unknown positions tacked on at end).
      const byPos = new Map<string, FullPick[]>();
      filtered.forEach(p => {
        const arr = byPos.get(p.position) ?? [];
        arr.push(p);
        byPos.set(p.position, arr);
      });
      const seen = new Set<string>();
      const out: GroupedSection[] = [];
      POS_ORDER.forEach(pos => {
        const picks = byPos.get(pos);
        if (picks && picks.length) {
          seen.add(pos);
          out.push({ key: `p${pos}`, title: pos, picks });
        }
      });
      // Any positions outside our canonical order, alphabetical.
      Array.from(byPos.keys())
        .filter(p => !seen.has(p))
        .sort()
        .forEach(pos => out.push({
          key: `p${pos}`, title: pos, picks: byPos.get(pos)!,
        }));
      return out;
    }

    // sortMode === 'team': sections per team, ordered by earliest pick.
    const byTeam = new Map<string, FullPick[]>();
    filtered.forEach(p => {
      const arr = byTeam.get(p.team) ?? [];
      arr.push(p);
      byTeam.set(p.team, arr);
    });
    return Array.from(byTeam.entries())
      .map(([team, picks]) => ({ team, picks }))
      .sort((a, b) => a.picks[0].pick - b.picks[0].pick)
      .map(({ team, picks }) => {
        const tc = teamColor(team);
        return {
          key: `t${team}`,
          title: `${team} · ${tc.name}`,
          accentColor: tc.primary,
          picks,
        };
      });
  }, [sortMode, filtered, activeRound]);

  const visiblePickCount = sections.reduce((n, s) => n + s.picks.length, 0);

  const hasFilter =
    posFilter !== 'All' || teamFilter !== '' || roundFilter !== 'All';

  return (
    <div className="space-y-6 pb-16">
      <SectionHeader
        kicker="The full mock"
        title="All seven rounds, 257 picks."
        deck="Sortable, filterable draft list. One row per pick, team-color edge, player and position at a glance. Sort by pick order, round, position, or team; filter by any combination. Click a row for the per-pick reasoning and close alternates. Data comes from the independent team-agent model — no fabricated scouting prose."
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
          {/* Controls bar */}
          <div className="space-y-2 bg-paper-surface border border-ink-edge p-3">
            {/* Sort selector */}
            <div className="flex flex-wrap items-center gap-2">
              <SmallCaps tight className="text-ink-muted mr-1">Sort</SmallCaps>
              {([
                ['pick',     'Pick order'],
                ['round',    'By round'],
                ['position', 'By position'],
                ['team',     'By team'],
              ] as const).map(([m, label]) => (
                <button
                  key={m}
                  onClick={() => setSortMode(m)}
                  className={`px-2 py-0.5 caps-tight text-[0.62rem] border transition ${
                    sortMode === m
                      ? 'bg-ink text-paper border-ink'
                      : 'bg-paper text-ink-muted border-ink-edge hover:border-ink hover:text-ink'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* Filters — round tabs in pick mode, round dropdown otherwise */}
            <div className="flex flex-wrap items-center gap-3 pt-1">
              {sortMode === 'pick' ? (
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
                  <button
                    onClick={() => setActiveRound('all')}
                    className={`h-7 px-2 caps-tight text-[0.62rem] font-mono border transition ml-1 ${
                      activeRound === 'all'
                        ? 'bg-ink text-paper border-ink'
                        : 'bg-paper text-ink-muted border-ink-edge hover:border-ink hover:text-ink'
                    }`}
                    title="Show every pick, all seven rounds"
                  >
                    All 257
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-1.5">
                  <SmallCaps tight className="text-ink-muted">Round</SmallCaps>
                  <select
                    value={String(roundFilter)}
                    onChange={e => setRoundFilter(e.target.value === 'All' ? 'All' : Number(e.target.value))}
                    className="font-mono text-xs border border-ink-edge px-2 py-1 bg-paper hover:border-ink"
                  >
                    <option value="All">All</option>
                    {[1,2,3,4,5,6,7].map(r => (
                      <option key={r} value={r}>Round {r}</option>
                    ))}
                  </select>
                </div>
              )}

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
                {hasFilter && (
                  <button
                    onClick={() => {
                      setPosFilter('All');
                      setTeamFilter('');
                      setRoundFilter('All');
                    }}
                    className="caps-tight text-[0.62rem] text-ink-muted hover:text-ink"
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between pt-1 text-[0.62rem] font-mono text-ink-soft italic">
              <span>
                {visiblePickCount} of {allPicks.length} picks visible
              </span>
              <span className="not-italic text-ink-muted">
                Tap any row for reasoning & alternates
              </span>
            </div>
          </div>

          {/* Sections */}
          {visiblePickCount === 0 ? (
            <MissingText>No picks match the current filters.</MissingText>
          ) : (
            <div className="space-y-4">
              {sections.map(s => (
                <Section
                  key={s.key}
                  title={s.title}
                  subtitle={s.subtitle}
                  accentColor={s.accentColor}
                  picks={s.picks}
                  selectedPick={selectedPick}
                  onSelect={(pk) =>
                    setSelectedPick(prev => (prev === pk ? null : pk))
                  }
                />
              ))}
            </div>
          )}

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
