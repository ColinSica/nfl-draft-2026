/**
 * First round — full 32-pick view of the latest simulation.
 * Each pick card shows team, player, probability, top-3 alternates,
 * and the model's actual reasoning. Users can filter by team,
 * position, or confidence tier and star picks to a watchlist.
 */
import { useEffect, useMemo, useState } from 'react';
import { Star, Filter, X, Download } from 'lucide-react';
import { api, type PickRow } from '../lib/api';
import { downloadCsv } from '../lib/csvExport';
import { useMode, MODE_META } from '../lib/mode';
import { HRule, SmallCaps, Dateline, Byline, Stamp } from '../components/editorial';
import { Link } from 'react-router-dom';
import { PickCard, type PickData } from '../components/PickCard';
import { FreshnessPanel } from '../components/FreshnessPanel';
import { useWatchlist } from '../lib/watchlist';
import { getConfidence } from '../lib/display';

type ConfBucket = 'ALL' | 'HIGH' | 'MEDIUM_HIGH' | 'MEDIUM_LOW' | 'LOW';

export function Simulate() {
  const { mode } = useMode();
  const accent = MODE_META[mode].accent;
  const [picks, setPicks] = useState<PickRow[] | null>(null);
  const [reasoning, setReasoning] = useState<any>(null);
  const [simMeta, setSimMeta] = useState<any>(null);
  const [trades, setTrades] = useState<any>(null);
  const [filterTeam, setFilterTeam] = useState<string>('ALL');
  const [filterPos, setFilterPos] = useState<string>('ALL');
  const [filterConf, setFilterConf] = useState<ConfBucket>('ALL');
  const [onlyStarred, setOnlyStarred] = useState(false);
  // Show original draft order (no trades) vs post-trade order.
  const [showTrades, setShowTrades] = useState<boolean>(true);
  const wl = useWatchlist();

  useEffect(() => {
    api.latestSim().then(r => {
      setPicks(r.picks);
      setSimMeta(r.meta);
    }).catch(() => setPicks([]));
    fetch('/api/simulations/reasoning')
      .then(r => r.json()).then(setReasoning).catch(() => {});
    api.simulationTrades()
      .then(setTrades).catch(() => {});
  }, []);

  // Top 3-5 most-likely trades, filtered for realism (prob >= 30%).
  // Rank by execution frequency in the Monte Carlo.
  const topTrades = useMemo(() => {
    if (!trades?.per_pick) return [];
    const events: any[] = [];
    for (const [slotStr, arr] of Object.entries(trades.per_pick)) {
      for (const ev of (arr as any[])) {
        if ((ev.prob ?? 0) >= 0.3) {
          events.push({ ...ev, slot: parseInt(slotStr, 10) });
        }
      }
    }
    events.sort((a, b) => (b.prob ?? 0) - (a.prob ?? 0));
    // Cap at 5, min 3 if we have them.
    return events.slice(0, 5);
  }, [trades]);

  // Build full 32 picks — team label changes based on showTrades toggle.
  const all32: PickData[] = useMemo(() => {
    return (picks ?? [])
      .filter(p => p.pick_number <= 32)
      .sort((a, b) => a.pick_number - b.pick_number)
      .map(p => {
        const pri = p.candidates?.[0];
        const modelReasoning = reasoning?.picks?.[String(p.pick_number)];
        const actualTeam = p.most_likely_team ?? p.team ?? '—';
        const originalTeam = p.original_team ?? p.team ?? actualTeam;
        const displayTeam = showTrades ? actualTeam : originalTeam;
        return {
          slot: p.pick_number,
          team: displayTeam,
          player: pri?.player ?? 'Pending',
          position: pri?.position ?? '',
          college: pri?.college ?? null,
          probability: pri?.probability ?? null,
          consensusRank: pri?.consensus_rank ?? null,
          confidence: null,
          alternates: (p.candidates ?? []).slice(1, 4).map(c => ({
            player: c.player,
            position: c.position,
            college: c.college,
            probability: c.probability,
          })),
          whySummary: modelReasoning?.reasoning_summary
            ?? `Modal pick at slot ${p.pick_number}.`,
          whyDetail: modelReasoning?.top_factors
            ? (
                <ul className="space-y-1.5">
                  {modelReasoning.top_factors.slice(0, 6).map((f: any, i: number) => {
                    const src = (typeof f === 'object' && f.source) ? String(f.source) : '';
                    const srcLabel = src.startsWith('research:')
                      ? src.slice('research:'.length)
                      : src === 'team_profile' ? 'team profile'
                      : src === 'qb_situation' ? 'QB situation'
                      : src === 'scheme' ? 'scheme'
                      : src === 'coaching_tree' ? 'coaching tree'
                      : src === 'gm_fingerprint' ? 'GM fingerprint'
                      : src === 'team_profile_narrative' ? 'team narrative'
                      : src === 'model' ? 'model'
                      : src;
                    return (
                      <li key={i} className="flex items-baseline gap-2 text-sm">
                        <span className="font-mono text-xs text-ink-soft/80 shrink-0">
                          {typeof f === 'object' && f.weight !== undefined
                            ? `+${Number(f.weight).toFixed(2)}`
                            : '·'}
                        </span>
                        <span className="flex-1">
                          {typeof f === 'object' ? (f.label ?? f.factor ?? '') : String(f)}
                        </span>
                        {srcLabel && (
                          <span className="font-mono text-[10px] uppercase tracking-wider text-ink-soft/60 shrink-0">
                            {srcLabel}
                          </span>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )
            : null,
          accent,
        };
      });
  }, [picks, reasoning, accent]);

  // Options for filter dropdowns
  const teams = useMemo(() => {
    const s = new Set<string>();
    all32.forEach(p => s.add(p.team));
    return ['ALL', ...Array.from(s).sort()];
  }, [all32]);

  const positions = useMemo(() => {
    const s = new Set<string>();
    all32.forEach(p => p.position && s.add(p.position));
    return ['ALL', ...Array.from(s).sort()];
  }, [all32]);

  // Apply filters
  const filtered = useMemo(() => {
    return all32.filter(p => {
      if (onlyStarred && !wl.has(p.player)) return false;
      if (filterTeam !== 'ALL' && p.team !== filterTeam) return false;
      if (filterPos !== 'ALL' && p.position !== filterPos) return false;
      if (filterConf !== 'ALL') {
        const cb = getConfidence(p.probability).label;
        if (cb !== filterConf) return false;
      }
      return true;
    });
  }, [all32, filterTeam, filterPos, filterConf, onlyStarred, wl]);

  // Map slot -> whether the displayed team is different from the original owner
  // (i.e., a trade happened at that slot in the MC)
  const tradedSlots = useMemo(() => {
    const s = new Set<number>();
    (picks ?? []).forEach(p => {
      if (p.pick_number <= 32 && p.original_team && p.most_likely_team
          && p.original_team !== p.most_likely_team) {
        s.add(p.pick_number);
      }
    });
    return s;
  }, [picks]);

  const clearFilters = () => {
    setFilterTeam('ALL');
    setFilterPos('ALL');
    setFilterConf('ALL');
    setOnlyStarred(false);
  };

  const hasFilters = filterTeam !== 'ALL' || filterPos !== 'ALL' || filterConf !== 'ALL' || onlyStarred;

  return (
    <div className="space-y-10 pb-16">
      <Dateline issue="First Round Edition" />

      <header className="space-y-4">
        <Stamp variant="slate">Lead Table</Stamp>
        <h1 className="display-jumbo text-ink"
            style={{ fontSize: 'clamp(2rem, 6vw, 4.75rem)' }}>
          First round, <em>all thirty-two picks</em>.
        </h1>
        <Byline role="Market-blended probabilities · latest committed run" />
        <HRule thick />
        <p className="body-serif-lead text-ink-soft max-w-3xl">
          Every first-round slot in the 2026 NFL Draft, with the model's
          posterior probability and analyst-sourced thesis per pick. Filter
          by team, position, or confidence. Want to stress-test a different
          round?{' '}
          <Link to="/lab" className="text-accent-brass underline underline-offset-2 hover:text-accent-brassDeep">
            Open the Mock Lab
          </Link>{' '}
          to adjust positional demand or lock specific picks.
        </p>
      </header>

      <div className="flex flex-wrap items-baseline gap-8 border-y border-ink py-4">
        <Metric label="Simulations" value={simMeta?.n_sims != null ? String(simMeta.n_sims) : '—'} />
        <Metric label="Picks shown" value={`${filtered.length} / ${all32.length}`} />
        <Metric label="Trades modelled" value={String(tradedSlots.size)} />
        <Metric label="Watchlist" value={String(wl.count)} />

        {/* Trades ON/OFF toggle */}
        <div className="ml-auto flex items-center gap-2">
          <SmallCaps tight className="text-ink-muted">Trades</SmallCaps>
          <div className="inline-flex border border-ink-edge">
            <button
              onClick={() => setShowTrades(false)}
              className={`caps-tight px-3 py-1.5 transition ${
                !showTrades ? 'bg-ink text-paper' : 'text-ink-muted hover:text-ink'
              }`}
              title="Show original draft order — no trades"
            >
              Off
            </button>
            <button
              onClick={() => setShowTrades(true)}
              className={`caps-tight px-3 py-1.5 transition ${
                showTrades ? 'bg-ink text-paper' : 'text-ink-muted hover:text-ink'
              }`}
              title="Show post-trade draft order — model's most-likely trade events applied"
            >
              On
            </button>
          </div>
          <button
            onClick={() => downloadCsv('2026-r1-predictions.csv', all32.map(p => ({
              slot: p.slot, team: p.team, player: p.player,
              position: p.position, college: p.college ?? '',
              probability: p.probability, consensus_rank: p.consensusRank ?? '',
            })))}
            className="btn-ghost"
            title="Download CSV"
          >
            <Download size={14} />
            <span>CSV</span>
          </button>
        </div>
      </div>

      {/* Trades panel — shown when Trades is ON */}
      {showTrades && topTrades.length > 0 && (
        <section className="border-y border-ink-edge bg-paper-raised p-5">
          <div className="flex items-baseline justify-between gap-4 mb-3 flex-wrap">
            <div className="flex items-center gap-3 flex-wrap">
              <SmallCaps>Most-likely R1 trade events</SmallCaps>
              <span className="caps-tight text-ink-muted">
                {topTrades.length} trade{topTrades.length === 1 ? '' : 's'} projected · filtered to ≥30% MC freq.
              </span>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {topTrades.map((t: any, i: number) => (
              <div key={i} className="border border-ink-edge bg-paper-surface p-3 space-y-1">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="display-num text-sm text-accent-brass">Pick #{t.slot}</span>
                  <span className="font-mono text-xs text-ink-muted">{Math.round(t.prob * 100)}% freq.</span>
                </div>
                <div className="flex items-center gap-2 font-mono text-xs">
                  <span className="text-ink font-medium">{t.from_team ?? '?'}</span>
                  <span className="text-accent-brass">→</span>
                  <span className="text-ink font-medium">{t.to_team ?? '?'}</span>
                </div>
                {t.compensation && (
                  <p className="text-xs text-ink-muted font-serif italic">
                    {t.compensation}
                  </p>
                )}
                {t.reason && !t.compensation && (
                  <p className="text-xs text-ink-muted font-serif italic">{t.reason}</p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Filter controls */}
      <div className="card p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Filter size={14} className="text-ink-soft" />
          <SmallCaps tight className="text-ink">Filters</SmallCaps>
          {hasFilters && (
            <button
              onClick={clearFilters}
              className="ml-auto inline-flex items-center gap-1 caps-tight text-ink-soft hover:text-ink"
            >
              <X size={12} /> Clear
            </button>
          )}
        </div>
        <div className="flex flex-wrap gap-3">
          <FilterSelect label="Team" value={filterTeam} options={teams} onChange={setFilterTeam} />
          <FilterSelect label="Position" value={filterPos} options={positions} onChange={setFilterPos} />
          <FilterSelect
            label="Confidence"
            value={filterConf}
            options={['ALL', 'HIGH', 'MEDIUM_HIGH', 'MEDIUM_LOW', 'LOW']}
            onChange={(v) => setFilterConf(v as ConfBucket)}
          />
          <button
            onClick={() => setOnlyStarred(!onlyStarred)}
            className={`btn-ghost ${onlyStarred ? 'bg-mode-indie/15 border-mode-indie text-ink' : ''}`}
          >
            <Star size={14} style={onlyStarred ? { color: '#B68A2F', fill: '#B68A2F' } : undefined} />
            <span>Watchlist only</span>
          </button>
        </div>
      </div>

      {!picks ? (
        <div className="card p-10 text-center text-ink-soft italic">Loading first round…</div>
      ) : filtered.length === 0 ? (
        <div className="card p-10 text-center text-ink-soft italic">
          No picks match. {hasFilters && <button onClick={clearFilters} className="underline">Clear filters</button>}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((pd, i) => (
            <div key={pd.slot} className="reveal" style={{ animationDelay: `${Math.min(i * 0.02, 0.5)}s` }}>
              <PickCard data={pd} />
            </div>
          ))}
        </div>
      )}

      <HRule />

      <FreshnessPanel
        data={{
          modelRefresh: simMeta?.generated_at ?? null,
          intelRefresh: null,
          simRun: simMeta?.finished_at ?? simMeta?.generated_at ?? null,
        }}
      />
    </div>
  );
}

function FilterSelect({
  label, value, options, onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <SmallCaps tight className="text-ink-soft shrink-0">{label}</SmallCaps>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="px-3 py-1.5 bg-paper-surface border border-ink-edge text-sm text-ink font-mono"
      >
        {options.map(o => (
          <option key={o} value={o}>
            {o === 'ALL' ? 'All' : o.replace('_', ' ').toLowerCase()}
          </option>
        ))}
      </select>
    </label>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="mono-label">{label}</div>
      <div className="display-num text-2xl md:text-3xl text-ink mt-1">{value}</div>
    </div>
  );
}
