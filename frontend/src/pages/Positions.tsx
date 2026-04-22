/**
 * Positions — top prospects by position group.
 * Answers "who are the top QBs / WRs / EDGEs / etc?"
 */
import { useEffect, useMemo, useState } from 'react';
import { Star } from 'lucide-react';
import { SectionHeader, SmallCaps, MissingText } from '../components/editorial';
import { teamColor } from '../lib/teamColors';
import { displayValue } from '../lib/display';
import { useWatchlist } from '../lib/watchlist';

type Prospect = {
  player: string;
  position: string;
  college: string | null;
  consensus_rank: number | null;
  most_likely_slot: number;
  most_likely_team: string | null;
  mean_landing: number;
};

// The positions we care about
const POS_ORDER = ['QB', 'RB', 'WR', 'TE', 'OT', 'IOL', 'EDGE', 'DL', 'IDL', 'LB', 'CB', 'S'];
const POS_LABELS: Record<string, string> = {
  QB: 'Quarterback', RB: 'Running back', WR: 'Wide receiver', TE: 'Tight end',
  OT: 'Offensive tackle', IOL: 'Interior OL', EDGE: 'Edge rusher',
  DL: 'Defensive line', IDL: 'Interior DL', LB: 'Linebacker',
  CB: 'Cornerback', S: 'Safety',
};

export function Positions() {
  const [prospects, setProspects] = useState<Prospect[] | null>(null);
  const [pos, setPos] = useState<string>('QB');
  const wl = useWatchlist();

  useEffect(() => {
    fetch('/api/simulations/prospects')
      .then(r => r.json())
      .then(d => setProspects(d.prospects ?? []))
      .catch(() => setProspects([]));
  }, []);

  const available = useMemo(() => {
    const s = new Set<string>();
    (prospects ?? []).forEach(p => p.position && s.add(p.position));
    return POS_ORDER.filter(p => s.has(p)).concat(
      Array.from(s).filter(p => !POS_ORDER.includes(p)).sort()
    );
  }, [prospects]);

  const list = useMemo(() => {
    return (prospects ?? [])
      .filter(p => p.position === pos)
      .sort((a, b) => (a.mean_landing ?? 999) - (b.mean_landing ?? 999));
  }, [prospects, pos]);

  return (
    <div className="space-y-10 pb-16">
      <SectionHeader
        kicker="Position rankings"
        title="Best at each position."
      />

      {/* Position tabs */}
      <div className="flex flex-wrap gap-0 border border-ink-edge bg-paper-surface overflow-x-auto">
        {available.map(p => (
          <button
            key={p}
            onClick={() => setPos(p)}
            className={`px-4 py-2.5 caps-tight border-r border-ink-edge last:border-r-0 transition whitespace-nowrap ${
              pos === p ? 'bg-ink text-paper' : 'text-ink-soft hover:text-ink hover:bg-paper-hover'
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      <div>
        <h2 className="display-broadcast text-4xl text-ink leading-[0.9] mb-2">
          {POS_LABELS[pos] ?? pos}
        </h2>
        <div className="text-sm text-ink-soft mb-6">
          Top {list.length} {pos === 'QB' ? 'quarterbacks' : pos.toLowerCase() + 's'} in the 2026 class, sorted by simulated mean landing.
        </div>
      </div>

      {!prospects ? (
        <div className="card p-10 text-center text-ink-soft italic">Loading…</div>
      ) : list.length === 0 ? (
        <div className="card p-10 text-center">
          <MissingText>No {pos} prospects in the simulation data.</MissingText>
        </div>
      ) : (
        <div className="border border-ink-edge bg-paper-surface">
          {list.slice(0, 40).map((p, i) => {
            const starred = wl.has(p.player);
            const tc = teamColor(p.most_likely_team ?? undefined);
            return (
              <div
                key={p.player + i}
                className="flex items-baseline gap-4 px-4 py-3 border-b border-ink-edge last:border-b-0 hover:bg-paper-hover transition"
              >
                <span className="display-num text-2xl text-ink-soft w-10 shrink-0 text-right">
                  #{i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="display-broadcast text-lg leading-none text-ink truncate">
                    {p.player.toUpperCase()}
                  </div>
                  <div className="text-xs text-ink-soft mt-0.5 font-mono">
                    {displayValue(p.college, '—')}
                    {p.consensus_rank && <span className="ml-2">· Consensus #{p.consensus_rank}</span>}
                  </div>
                </div>
                <div className="text-right shrink-0 text-xs font-mono">
                  <div>
                    <span className="caps-tight text-ink-soft">Mean slot</span>{' '}
                    <span className="text-ink font-bold">{p.mean_landing?.toFixed?.(1) ?? '—'}</span>
                  </div>
                  {p.most_likely_team && (
                    <div className="mt-0.5">
                      <span
                        className="inline-block w-6 h-4 text-[0.55rem] font-bold text-center"
                        style={{
                          background: tc.primary,
                          color: tc.secondary === '#000000' ? '#FFFFFF' : tc.secondary,
                          lineHeight: '1rem',
                        }}
                      >
                        {p.most_likely_team}
                      </span>
                      <span className="ml-1 text-ink-soft">slot {p.most_likely_slot}</span>
                    </div>
                  )}
                </div>
                <button
                  onClick={() => wl.toggle(p.player, { slot: p.most_likely_slot, team: p.most_likely_team ?? undefined })}
                  className="p-2 text-ink-soft hover:text-ink shrink-0"
                  title={starred ? 'Remove from watchlist' : 'Add to watchlist'}
                >
                  <Star size={14} style={{ color: starred ? '#B68A2F' : undefined, fill: starred ? '#B68A2F' : 'transparent' }} />
                </button>
              </div>
            );
          })}
        </div>
      )}

      <div className="flex items-center gap-3 text-sm text-ink-soft">
        <SmallCaps tight>Jump to</SmallCaps>
        {available.map(p => (
          <button
            key={p}
            onClick={() => setPos(p)}
            className={`caps-tight transition ${
              pos === p ? 'text-ink' : 'text-ink-soft hover:text-ink'
            }`}
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}
