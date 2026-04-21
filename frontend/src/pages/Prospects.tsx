/**
 * Prospects — big board with landing distributions.
 * Per user brief: Summary / Landing spots / Team fits / Intel / Reasoning.
 * Rebuilt for light theme.
 */
import { useEffect, useMemo, useState } from 'react';
import { Search, Star, Download } from 'lucide-react';
import { teamColor } from '../lib/teamColors';
import { SectionHeader, SmallCaps, MissingText, HRule } from '../components/editorial';
import { displayValue } from '../lib/display';
import { useWatchlist } from '../lib/watchlist';
import { downloadCsv } from '../lib/csvExport';

type Prospect = {
  player: string;
  position: string;
  college: string | null;
  consensus_rank: number | null;
  landings: { slot: number; team: string | null; probability: number }[];
  mean_landing: number;
  variance_landing: number;
  most_likely_slot: number;
  most_likely_team: string | null;
};

export function Prospects() {
  const [prospects, setProspects] = useState<Prospect[] | null>(null);
  const [query, setQuery] = useState('');
  const [posFilter, setPosFilter] = useState<string>('ALL');
  const [selected, setSelected] = useState<string | null>(null);
  const [onlyStarred, setOnlyStarred] = useState(false);
  const wl = useWatchlist();

  useEffect(() => {
    fetch('/api/simulations/prospects')
      .then(r => r.json())
      .then(d => setProspects(d.prospects ?? []))
      .catch(() => setProspects([]));
  }, []);

  const positions = useMemo(() => {
    const s = new Set<string>();
    (prospects ?? []).forEach(p => p.position && s.add(p.position));
    return ['ALL', ...Array.from(s).sort()];
  }, [prospects]);

  const filtered = useMemo(() => {
    if (!prospects) return [];
    const q = query.trim().toLowerCase();
    return prospects.filter(p => {
      if (onlyStarred && !wl.has(p.player)) return false;
      if (posFilter !== 'ALL' && p.position !== posFilter) return false;
      if (!q) return true;
      return (
        p.player.toLowerCase().includes(q) ||
        (p.college ?? '').toLowerCase().includes(q) ||
        (p.position ?? '').toLowerCase().includes(q)
      );
    });
  }, [prospects, query, posFilter, onlyStarred, wl]);

  const selectedProspect = filtered.find(p => p.player === selected) ?? null;

  return (
    <div className="space-y-10 pb-16">
      <SectionHeader
        kicker="Big board"
        title="Prospects and landing spots."
      />

      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 bg-paper-surface border border-ink-edge px-3 py-2 min-w-[240px] flex-1 max-w-md">
            <Search size={16} className="text-ink-soft" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search prospect, college, position…"
              className="flex-1 bg-transparent outline-none text-sm text-ink placeholder:text-ink-soft/60"
            />
          </label>
          <button
            onClick={() => setOnlyStarred(!onlyStarred)}
            className={`btn-ghost ${onlyStarred ? 'bg-mode-indie/15 border-mode-indie text-ink' : ''}`}
          >
            <Star size={14} style={onlyStarred ? { color: '#D9A400', fill: '#D9A400' } : undefined} />
            <span>Watchlist ({wl.count})</span>
          </button>
          <button
            onClick={() => downloadCsv('2026-big-board.csv', filtered.map(p => ({
              most_likely_slot: p.most_likely_slot,
              most_likely_team: p.most_likely_team ?? '',
              player: p.player,
              position: p.position,
              college: p.college ?? '',
              consensus_rank: p.consensus_rank ?? '',
              mean_landing: p.mean_landing,
              variance_landing: p.variance_landing,
            })))}
            className="btn-ghost"
            title="Download CSV"
          >
            <Download size={14} />
            <span>Export</span>
          </button>
          <span className="ml-auto text-sm text-ink-soft">
            {filtered.length} {filtered.length === 1 ? 'prospect' : 'prospects'}
          </span>
        </div>

        {/* Position tab strip */}
        <div className="flex flex-wrap gap-0 border border-ink-edge bg-paper-surface overflow-x-auto">
          {positions.map(p => (
            <button
              key={p}
              onClick={() => setPosFilter(p)}
              className={`px-3 py-2 caps-tight border-r border-ink-edge last:border-r-0 transition whitespace-nowrap ${
                posFilter === p
                  ? 'bg-ink text-paper'
                  : 'text-ink-soft hover:text-ink hover:bg-paper-hover'
              }`}
            >
              {p === 'ALL' ? 'All' : p}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_420px] gap-6">
        {/* Left: prospect list */}
        <div>
          {!prospects ? (
            <div className="card p-10 text-center text-ink-soft italic">Loading big board…</div>
          ) : filtered.length === 0 ? (
            <div className="card p-10 text-center text-ink-soft italic">No prospects match.</div>
          ) : (
            <div className="border border-ink-edge bg-paper-surface">
              {filtered.slice(0, 120).map((p, i) => {
                const starred = wl.has(p.player);
                return (
                  <div
                    key={p.player + i}
                    className={`flex items-center gap-2 border-b border-ink-edge last:border-b-0 transition ${
                      selected === p.player ? 'bg-mode-indie/12' : 'hover:bg-paper-hover'
                    }`}
                  >
                    <button
                      onClick={() => setSelected(p.player)}
                      className="flex-1 text-left flex items-baseline gap-4 px-4 py-3 min-w-0"
                    >
                      <span className="display-num text-xl text-ink-soft w-8 shrink-0 text-right">
                        {p.most_likely_slot || '·'}
                      </span>
                      <span className="flex-1 min-w-0">
                        <div className="display-broadcast text-lg leading-none text-ink truncate">
                          {p.player.toUpperCase()}
                        </div>
                        <div className="text-xs text-ink-soft mt-0.5 font-mono">
                          {p.position} · {displayValue(p.college, '—')}
                        </div>
                      </span>
                      <span className="text-right shrink-0 text-xs font-mono">
                        {p.most_likely_team && (
                          <>
                            <span className="caps-tight text-ink-soft">to</span>{' '}
                            <span className="text-ink font-bold">{p.most_likely_team}</span>
                          </>
                        )}
                      </span>
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); wl.toggle(p.player, { slot: p.most_likely_slot, team: p.most_likely_team ?? undefined }); }}
                      className="p-3 text-ink-soft hover:text-ink transition shrink-0"
                      title={starred ? 'Remove from watchlist' : 'Add to watchlist'}
                    >
                      <Star size={16} style={{ color: starred ? '#D9A400' : undefined, fill: starred ? '#D9A400' : 'transparent' }} />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
          {filtered.length > 120 && (
            <p className="mt-4 text-xs text-ink-soft text-center">
              Showing first 120 of {filtered.length}. Refine search to see others.
            </p>
          )}
        </div>

        {/* Right: detail panel */}
        <aside className="space-y-5 lg:sticky lg:top-20 self-start">
          {!selectedProspect ? (
            <div className="card p-6 text-center">
              <p className="text-ink-soft italic">Select a prospect to see landing distribution and details.</p>
            </div>
          ) : (
            <ProspectDetail p={selectedProspect} />
          )}
        </aside>
      </div>
    </div>
  );
}

function ProspectDetail({ p }: { p: Prospect }) {
  const landings = p.landings.slice(0, 8);
  const totalProb = landings.reduce((s, l) => s + l.probability, 0);

  return (
    <>
      <div className="card">
        <div className="p-5 space-y-3">
          <div>
            <SmallCaps tight className="text-ink-soft">Selected</SmallCaps>
            <h3 className="display-broadcast text-3xl md:text-4xl leading-[0.9] text-ink mt-1">
              {p.player.toUpperCase()}
            </h3>
            <div className="mt-2 text-xs font-mono text-ink-soft">
              <span className="px-1.5 py-0.5 bg-ink text-paper font-bold mr-2">{p.position}</span>
              {displayValue(p.college, '—')}
              {p.consensus_rank && (
                <span className="ml-2">· Consensus #{p.consensus_rank}</span>
              )}
            </div>
          </div>
          <HRule />
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <SmallCaps tight className="text-ink-soft block">Mean landing</SmallCaps>
              <div className="display-num text-3xl text-ink mt-1">
                {p.mean_landing?.toFixed(1) ?? '—'}
              </div>
            </div>
            <div>
              <SmallCaps tight className="text-ink-soft block">Variance</SmallCaps>
              <div className="display-num text-3xl text-ink mt-1">
                ±{Math.sqrt(p.variance_landing ?? 0).toFixed(1)}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <header className="px-5 py-3 border-b border-ink-edge">
          <SmallCaps className="text-ink">Landing distribution</SmallCaps>
        </header>
        <div className="p-5">
          {landings.length === 0 ? (
            <MissingText>No simulated landings.</MissingText>
          ) : (
            <ul className="space-y-3">
              {landings.map((l, i) => {
                const tc = teamColor(l.team ?? undefined);
                const pct = l.probability / (totalProb || 1);
                return (
                  <li key={i} className="flex items-center gap-3">
                    <span className="display-num text-lg text-ink-soft w-10 shrink-0 text-right">
                      {l.slot}
                    </span>
                    <div className="flex-1 flex items-center gap-2">
                      <span
                        className="w-7 h-7 flex items-center justify-center text-[0.65rem] font-bold shrink-0"
                        style={{
                          background: tc.primary,
                          color: tc.secondary === '#000000' ? '#FFFFFF' : tc.secondary,
                        }}
                      >
                        {l.team}
                      </span>
                      <div className="flex-1 h-2 bg-paper-hover overflow-hidden relative">
                        <div
                          className="absolute inset-y-0 left-0"
                          style={{
                            width: `${pct * 100}%`,
                            background: tc.primary,
                          }}
                        />
                      </div>
                    </div>
                    <span className="font-mono text-xs text-ink w-12 shrink-0 text-right">
                      {Math.round(l.probability * 100)}%
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </>
  );
}
