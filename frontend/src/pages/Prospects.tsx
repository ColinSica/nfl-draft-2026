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
  const [sortKey, setSortKey] = useState<'rank' | 'ras' | 'weight'>('rank');

  useEffect(() => {
    api.prospects(80).then((r) => setData(r.prospects as Prospect[]))
      .catch((e) => setErr(String(e)));
  }, []);

  const positions = useMemo(
    () => Array.from(new Set(data.map((p) => p.position).filter(Boolean) as string[])).sort(),
    [data],
  );

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
      return (a.rank ?? 999) - (b.rank ?? 999);
    });
    return out;
  }, [data, search, posFilter, sortKey]);

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
          <option value="ras">Sort: RAS score</option>
          <option value="weight">Sort: weight</option>
        </select>
        <div className="text-xs text-text-subtle">
          {filtered.length} / {data.length}
        </div>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[10px] uppercase tracking-wider text-text-subtle border-b border-border bg-bg-raised/60">
              <th className="text-left font-medium py-2.5 pl-4 pr-2 w-12">#</th>
              <th className="text-left font-medium py-2.5 px-2">Player</th>
              <th className="text-left font-medium py-2.5 px-2">College</th>
              <th className="text-right font-medium py-2.5 px-2 w-20">Weight</th>
              <th className="text-right font-medium py-2.5 px-2 w-16">RAS</th>
              <th className="text-right font-medium py-2.5 pr-4 pl-2 w-24">Model score</th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 100).map((p) => (
              <tr key={p.player} className="border-b border-border/60 last:border-0 hover:bg-bg-hover/40">
                <td className="py-2 pl-4 pr-2 font-mono tabular-nums text-text-muted">
                  {p.rank ?? '—'}
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
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
