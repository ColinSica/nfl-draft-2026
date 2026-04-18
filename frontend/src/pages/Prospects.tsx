import { useEffect, useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { api } from '../lib/api';
import { cn } from '../lib/format';
import { positionColor } from '../lib/teams';

type Prospect = {
  player: string;
  position: string | null;
  college: string | null;
  rank: number | null;
  final_score: number | null;
  ras_score: number | null;
  weight: number | null;
  height: number | null;
};

export function Prospects() {
  const [data, setData] = useState<Prospect[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [posFilter, setPosFilter] = useState('ALL');
  const [sortKey, setSortKey] = useState<'rank' | 'ras' | 'weight' | 'model'>('rank');

  useEffect(() => {
    api.prospects(80).then((r) => setData(r.prospects as Prospect[]))
      .catch((e) => setErr(String(e)));
  }, []);

  const positions = useMemo(
    () => Array.from(new Set(data.map((p) => p.position).filter(Boolean) as string[])).sort(),
    [data],
  );

  // Derive model rank by sorting ALL prospects by final_score desc — stays
  // stable regardless of the current position/search filter so a player's
  // model rank is an absolute ordering across the whole board.
  const modelRankMap = useMemo(() => {
    const byScore = [...data]
      .filter((p) => p.final_score != null)
      .sort((a, b) => (b.final_score ?? -Infinity) - (a.final_score ?? -Infinity));
    const m = new Map<string, number>();
    byScore.forEach((p, i) => m.set(p.player, i + 1));
    return m;
  }, [data]);

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    const out = data.filter((p) => {
      if (posFilter !== 'ALL' && p.position !== posFilter) return false;
      if (!needle) return true;
      return (
        p.player.toLowerCase().includes(needle) ||
        (p.college ?? '').toLowerCase().includes(needle) ||
        (p.position ?? '').toLowerCase() === needle
      );
    });
    out.sort((a, b) => {
      if (sortKey === 'ras') return (b.ras_score ?? 0) - (a.ras_score ?? 0);
      if (sortKey === 'weight') return (b.weight ?? 0) - (a.weight ?? 0);
      if (sortKey === 'model') {
        return (modelRankMap.get(a.player) ?? 9999) - (modelRankMap.get(b.player) ?? 9999);
      }
      return (a.rank ?? 999) - (b.rank ?? 999);
    });
    return out;
  }, [data, search, posFilter, sortKey, modelRankMap]);

  if (err) return <div className="card p-6 text-tier-low text-sm">{err}</div>;

  return (
    <div className="space-y-5">
      <div>
        <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted mb-1">
          Consensus big board
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">Prospects</h1>
        <p className="text-sm text-text-muted mt-1 max-w-3xl">
          Top-ranked prospects by consensus rank, with combine measurements
          and stage-1 model's predicted draft slot.
        </p>
      </div>

      <div className="card p-3 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 px-3 py-1.5 bg-bg-raised border border-border rounded-md flex-1 min-w-0 sm:min-w-[240px]">
          <Search size={14} className="text-text-subtle" />
          <input
            className="bg-transparent outline-none flex-1 text-sm placeholder:text-text-subtle"
            placeholder="Search prospect / college / position…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          value={posFilter}
          onChange={(e) => setPosFilter(e.target.value)}
          className="bg-bg-raised border border-border rounded-md px-3 py-1.5 text-sm outline-none focus:border-accent"
        >
          <option value="ALL">All positions</option>
          {positions.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <select
          value={sortKey}
          onChange={(e) => setSortKey(e.target.value as any)}
          className="bg-bg-raised border border-border rounded-md px-3 py-1.5 text-sm outline-none focus:border-accent"
        >
          <option value="rank">Sort: consensus rank</option>
          <option value="model">Sort: model rank</option>
          <option value="ras">Sort: RAS score</option>
          <option value="weight">Sort: weight</option>
        </select>
        <div className="text-xs text-text-subtle">
          {filtered.length} / {data.length}
        </div>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm min-w-[640px]">
          <thead>
            <tr className="text-[10px] uppercase tracking-wider text-text-subtle border-b border-border bg-bg-raised/60">
              <th className="text-left font-medium py-2.5 pl-4 pr-2 w-20" title="Consensus analyst rank (blended across 20+ mock drafts)">Cons rank</th>
              <th className="text-left font-medium py-2.5 px-2 w-20" title="Model rank — ordering by stage-1 model score across all prospects">Model rank</th>
              <th className="text-left font-medium py-2.5 px-2">Player</th>
              <th className="text-left font-medium py-2.5 px-2">College</th>
              <th className="text-right font-medium py-2.5 px-2 w-20">Weight</th>
              <th className="text-right font-medium py-2.5 px-2 w-16">RAS</th>
              <th className="text-right font-medium py-2.5 pr-4 pl-2 w-24">Model score</th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 100).map((p) => {
              const modelRank = modelRankMap.get(p.player);
              const gap = (p.rank != null && modelRank != null) ? p.rank - modelRank : null;
              return (
              <tr key={p.player} className="border-b border-border/60 last:border-0 hover:bg-bg-hover/40">
                <td className="py-2 pl-4 pr-2 font-mono tabular-nums">
                  {p.rank != null ? (
                    <span className="text-text">#{p.rank}</span>
                  ) : <span className="text-text-subtle">—</span>}
                </td>
                <td className="py-2 px-2 font-mono tabular-nums">
                  {modelRank != null ? (
                    <span className="inline-flex items-center gap-1.5">
                      <span className="text-text">#{modelRank}</span>
                      {gap != null && gap !== 0 && (
                        <span className={cn(
                          'text-[10px] font-medium',
                          gap > 0 ? 'text-tier-high' : 'text-tier-midlo',
                        )}
                        title={gap > 0
                          ? `Model ranks ${Math.abs(gap)} spots higher than consensus`
                          : `Model ranks ${Math.abs(gap)} spots lower than consensus`}>
                          {gap > 0 ? `↑${gap}` : `↓${Math.abs(gap)}`}
                        </span>
                      )}
                    </span>
                  ) : <span className="text-text-subtle">—</span>}
                </td>
                <td className="py-2 px-2">
                  <div className="flex items-center gap-2">
                    {p.position && (
                      <span
                        className="badge flex-none"
                        style={{
                          color: positionColor(p.position),
                          borderColor: `${positionColor(p.position)}4D`,
                          backgroundColor: `${positionColor(p.position)}1A`,
                        }}
                      >
                        {p.position}
                      </span>
                    )}
                    <span className="font-medium text-text">{p.player}</span>
                  </div>
                </td>
                <td className="py-2 px-2 text-text-muted text-xs">{p.college ?? '—'}</td>
                <td className="py-2 px-2 text-right font-mono tabular-nums text-xs text-text-muted">
                  {p.weight ? p.weight.toFixed(0) : '—'}
                </td>
                <td className="py-2 px-2 text-right font-mono tabular-nums text-xs">
                  {p.ras_score ? (
                    <span className={cn(
                      p.ras_score >= 9 ? 'text-tier-high' :
                      p.ras_score >= 7 ? 'text-tier-midhi' :
                      p.ras_score >= 5 ? 'text-tier-mid' :
                      p.ras_score > 0  ? 'text-tier-midlo' : 'text-text-subtle',
                    )}>
                      {p.ras_score.toFixed(2)}
                    </span>
                  ) : <span className="text-text-subtle">—</span>}
                </td>
                <td className="py-2 pr-4 pl-2 text-right font-mono tabular-nums text-text-muted">
                  {p.final_score != null ? p.final_score.toFixed(1) : '—'}
                </td>
              </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
