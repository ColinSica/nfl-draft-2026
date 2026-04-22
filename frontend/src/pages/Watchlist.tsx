/**
 * Watchlist — user-starred players and picks, persisted in localStorage.
 * Shows what the user is tracking + latest landing data for each.
 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Star, Trash2, ArrowUpRight } from 'lucide-react';
import { SectionHeader, SmallCaps, MissingText, HRule } from '../components/editorial';
import { useWatchlist } from '../lib/watchlist';
import { teamColor } from '../lib/teamColors';

type ProspectRow = {
  player: string;
  position: string;
  college: string | null;
  consensus_rank: number | null;
  most_likely_slot: number;
  most_likely_team: string | null;
  mean_landing: number;
  landings: { slot: number; team: string | null; probability: number }[];
};

export function Watchlist() {
  const wl = useWatchlist();
  const [prospects, setProspects] = useState<ProspectRow[] | null>(null);

  useEffect(() => {
    fetch('/api/simulations/prospects')
      .then(r => r.json())
      .then(d => setProspects(d.prospects ?? []))
      .catch(() => setProspects([]));
  }, []);

  const byName = new Map<string, ProspectRow>((prospects ?? []).map(p => [p.player, p]));

  const enriched = wl.items
    .map(w => ({
      ...w,
      prospect: byName.get(w.player),
    }))
    .sort((a, b) => (a.prospect?.most_likely_slot ?? 999) - (b.prospect?.most_likely_slot ?? 999));

  return (
    <div className="space-y-10 pb-16">
      <SectionHeader
        kicker="Watchlist"
        title={`Your tracked picks${wl.count ? ` (${wl.count})` : ''}.`}
      />

      {wl.count === 0 ? (
        <div className="card p-10 text-center space-y-3">
          <Star size={28} className="mx-auto text-ink-soft" />
          <p className="text-ink-soft">Your watchlist is empty.</p>
          <p className="text-sm text-ink-soft">
            Star any player from&nbsp;
            <Link to="/prospects" className="text-mode-indie hover:underline">Prospects</Link>,
            or star a pick from&nbsp;
            <Link to="/simulate" className="text-mode-indie hover:underline">First round</Link>
            &nbsp;to track them here.
          </p>
        </div>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <span className="caps-tight text-ink-soft">
              {wl.count} {wl.count === 1 ? 'item' : 'items'} tracked
            </span>
            <button
              onClick={() => { if (confirm('Clear your entire watchlist?')) wl.clear(); }}
              className="btn-ghost ml-auto text-live border-live/30 hover:bg-live/5"
            >
              <Trash2 size={14} /> Clear all
            </button>
          </div>

          <div className="space-y-3">
            {enriched.map(item => {
              const p = item.prospect;
              const tc = teamColor(p?.most_likely_team ?? item.team);
              return (
                <article
                  key={item.player}
                  className="card relative overflow-hidden flex"
                  style={{ borderLeft: `4px solid ${tc.primary}` }}
                >
                  <div className="flex-1 p-5 space-y-2">
                    <div className="flex items-baseline justify-between gap-3 flex-wrap">
                      <div>
                        <h3 className="display-broadcast text-2xl text-ink leading-none">
                          {item.player.toUpperCase()}
                        </h3>
                        {p && (
                          <div className="mt-1 text-xs font-mono text-ink-soft">
                            <span className="px-1.5 py-0.5 bg-ink text-paper font-bold mr-2">{p.position}</span>
                            {p.college} {p.consensus_rank && <span>· Consensus #{p.consensus_rank}</span>}
                          </div>
                        )}
                      </div>
                      <button
                        onClick={() => wl.remove(item.player)}
                        className="p-2 text-ink-soft hover:text-live transition"
                        title="Remove from watchlist"
                      >
                        <Star size={16} style={{ color: '#B68A2F', fill: '#B68A2F' }} />
                      </button>
                    </div>

                    {p ? (
                      <>
                        <HRule />
                        <div className="flex items-baseline gap-6 flex-wrap pt-2">
                          <div>
                            <SmallCaps tight className="text-ink-soft block">Most likely slot</SmallCaps>
                            <div className="display-num text-3xl text-ink mt-1">
                              {p.most_likely_slot} {p.most_likely_team && <span className="text-ink-soft text-sm">to {p.most_likely_team}</span>}
                            </div>
                          </div>
                          <div>
                            <SmallCaps tight className="text-ink-soft block">Mean landing</SmallCaps>
                            <div className="display-num text-3xl text-ink mt-1">{p.mean_landing?.toFixed?.(1) ?? '—'}</div>
                          </div>
                          <div className="ml-auto">
                            <Link to="/prospects" className="btn-ghost">
                              <span>Full detail</span>
                              <ArrowUpRight size={14} />
                            </Link>
                          </div>
                        </div>
                        {p.landings && p.landings.length > 1 && (
                          <div className="mt-3">
                            <SmallCaps tight className="text-ink-soft block mb-1">Alt landings</SmallCaps>
                            <div className="flex flex-wrap gap-3 text-sm">
                              {p.landings.slice(1, 4).map((l, i) => (
                                <span key={i} className="inline-flex items-baseline gap-1.5 font-mono text-xs">
                                  <span className="text-ink-soft/70">{Math.round(l.probability * 100)}%</span>
                                  <span className="text-ink font-bold">#{l.slot}</span>
                                  <span className="text-ink-soft">{l.team ?? '—'}</span>
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </>
                    ) : (
                      <MissingText>No simulation data for this player yet.</MissingText>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
