/**
 * First round — full 32-pick view of the latest simulation.
 * Each pick card shows team, player, probability, top-3 alternates,
 * and the model's actual reasoning. Users can filter by team,
 * position, or confidence tier and star picks to a watchlist.
 */
import { useEffect, useMemo, useState } from 'react';
import { Star, Filter, X } from 'lucide-react';
import { api, type PickRow } from '../lib/api';
import { useMode, MODE_META } from '../lib/mode';
import { SectionHeader, HRule, SmallCaps } from '../components/editorial';
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
  const [filterTeam, setFilterTeam] = useState<string>('ALL');
  const [filterPos, setFilterPos] = useState<string>('ALL');
  const [filterConf, setFilterConf] = useState<ConfBucket>('ALL');
  const [onlyStarred, setOnlyStarred] = useState(false);
  const wl = useWatchlist();

  useEffect(() => {
    api.latestSim().then(r => {
      setPicks(r.picks);
      setSimMeta(r.meta);
    }).catch(() => setPicks([]));
    fetch('/api/simulations/reasoning')
      .then(r => r.json()).then(setReasoning).catch(() => {});
  }, []);

  // Build full 32 picks
  const all32: PickData[] = useMemo(() => {
    return (picks ?? [])
      .filter(p => p.pick_number <= 32)
      .sort((a, b) => a.pick_number - b.pick_number)
      .map(p => {
        const pri = p.candidates?.[0];
        const modelReasoning = reasoning?.picks?.[String(p.pick_number)];
        return {
          slot: p.pick_number,
          team: p.most_likely_team ?? p.team ?? '—',
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
                <ul className="space-y-1">
                  {modelReasoning.top_factors.slice(0, 6).map((f: any, i: number) => (
                    <li key={i}>
                      <span className="font-mono text-xs text-ink-soft/80 mr-2">
                        {typeof f === 'object' && f.weight !== undefined
                          ? `+${Number(f.weight).toFixed(2)}`
                          : '·'}
                      </span>
                      <span>{typeof f === 'object' ? (f.label ?? f.factor ?? '') : String(f)}</span>
                    </li>
                  ))}
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

  const clearFilters = () => {
    setFilterTeam('ALL');
    setFilterPos('ALL');
    setFilterConf('ALL');
    setOnlyStarred(false);
  };

  const hasFilters = filterTeam !== 'ALL' || filterPos !== 'ALL' || filterConf !== 'ALL' || onlyStarred;

  return (
    <div className="space-y-10 pb-16">
      <SectionHeader kicker="Full first round" title="All 32 picks." />

      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-baseline gap-5">
          <div>
            <div className="caps-tight text-ink-soft">Simulations</div>
            <div className="display-num text-3xl text-ink">{simMeta?.n_sims ?? '—'}</div>
          </div>
          <div>
            <div className="caps-tight text-ink-soft">Showing</div>
            <div className="display-num text-3xl text-ink">
              {filtered.length}<span className="text-ink-soft/60">/{all32.length}</span>
            </div>
          </div>
          <div>
            <div className="caps-tight text-ink-soft">Watchlist</div>
            <div className="display-num text-3xl text-ink">{wl.count}</div>
          </div>
        </div>
        <span className="ml-auto text-xs text-ink-soft italic">
          Click a pick to expand reasoning · star to watchlist
        </span>
      </div>

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
            <Star size={14} style={onlyStarred ? { color: '#D9A400', fill: '#D9A400' } : undefined} />
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
