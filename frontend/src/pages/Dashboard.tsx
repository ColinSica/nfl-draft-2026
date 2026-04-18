import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, Users, TrendingUp, AlertTriangle } from 'lucide-react';
import { api, type TeamSummary } from '../lib/api';
import { cn, tierClass } from '../lib/format';
import { teamMeta } from '../lib/teams';
import { Tooltip, GLOSSARY } from '../components/Tooltip';

type SortKey = 'pick' | 'team' | 'win_pct' | 'predictability' | 'visits';

function TeamCard({ t }: { t: TeamSummary }) {
  const firstPick = t.r1_picks[0];
  const meta = teamMeta(t.team);
  const stripeColor = meta?.primary ?? '#303648';
  return (
    <Link
      to={`/team/${t.team}`}
      className="card p-4 hover:border-border-strong hover:bg-bg-hover/20 transition-colors group relative overflow-hidden"
      style={{ borderLeft: `3px solid ${stripeColor}` }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          {meta && (
            <img
              src={meta.logo}
              alt={meta.abbr}
              className="w-10 h-10 object-contain flex-none"
              onError={(e) => ((e.target as HTMLImageElement).style.display = 'none')}
            />
          )}
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-base tracking-tight">
                {meta?.name ?? t.team}
              </span>
              {(t.new_hc || t.new_gm) && (
                <span className="badge border-tier-midhi/40 bg-tier-midhi/10 text-tier-midhi">
                  new {t.new_gm && t.new_hc ? 'GM+HC' : t.new_gm ? 'GM' : 'HC'}
                </span>
              )}
            </div>
            <div className="text-xs text-text-muted mt-0.5 truncate">
              {t.gm} · {t.hc}
            </div>
          </div>
        </div>
        <div className="text-right">
          {firstPick ? (
            <div className="font-mono text-2xl font-semibold tracking-tight text-text">
              #{firstPick}
            </div>
          ) : (
            <div className="text-text-subtle text-xs">No R1</div>
          )}
          <div className="text-[10px] text-text-subtle uppercase tracking-wide">
            {t.total_picks} picks
          </div>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <span className={cn('badge', tierClass(t.predictability))}>
          {t.predictability || '—'}
        </span>
        {t.qb_situation && (
          <span className="badge border-border text-text-muted">
            QB {t.qb_situation}
          </span>
        )}
        {t.cap_tier && t.cap_tier !== 'normal' && (
          <span className="badge border-border text-text-muted capitalize">
            cap {t.cap_tier}
          </span>
        )}
      </div>

      <div className="mt-4 space-y-1">
        {t.top_needs.slice(0, 3).map((n) => (
          <div key={n.pos} className="flex items-center gap-2 text-xs">
            <span className="font-mono w-10 text-text-muted">{n.pos}</span>
            <div className="flex-1 h-1.5 bg-bg-raised rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-accent/60 to-accent"
                style={{ width: `${Math.min(100, (n.score / 5) * 100)}%` }}
              />
            </div>
            <span className="font-mono text-text-subtle tabular-nums">
              {n.score.toFixed(1)}
            </span>
          </div>
        ))}
      </div>

      <div className="mt-3 flex items-center justify-between text-[11px] text-text-subtle">
        <span>{t.scheme_premium.length > 0 ? `Scheme: ${t.scheme_premium.join(', ')}` : 'No scheme premium'}</span>
        <span className="font-mono">
          {t.n_confirmed_visits} visits
        </span>
      </div>
    </Link>
  );
}

export function Dashboard() {
  const [teams, setTeams] = useState<TeamSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState('');
  const [tierFilter, setTierFilter] = useState<string>('all');
  const [sortKey, setSortKey] = useState<SortKey>('pick');

  useEffect(() => {
    api.teams()
      .then((r) => setTeams(r.teams))
      .catch((e) => setError(String(e)));
  }, []);

  const filtered = useMemo(() => {
    if (!teams) return [];
    const needle = q.trim().toLowerCase();
    const out = teams.filter((t) => {
      if (tierFilter !== 'all' && t.predictability !== tierFilter) return false;
      if (!needle) return true;
      return (
        t.team.toLowerCase().includes(needle) ||
        t.gm?.toLowerCase().includes(needle) ||
        t.hc?.toLowerCase().includes(needle) ||
        t.top_needs.some((n) => n.pos.toLowerCase() === needle)
      );
    });
    return out.sort((a, b) => {
      switch (sortKey) {
        case 'team':
          return a.team.localeCompare(b.team);
        case 'win_pct':
          return (b.win_pct ?? 0) - (a.win_pct ?? 0);
        case 'visits':
          return b.n_confirmed_visits - a.n_confirmed_visits;
        case 'predictability': {
          const order = ['HIGH', 'MEDIUM-HIGH', 'MEDIUM', 'LOW-MEDIUM', 'LOW'];
          return order.indexOf(a.predictability) - order.indexOf(b.predictability);
        }
        case 'pick':
        default: {
          const ap = a.r1_picks[0] ?? 99;
          const bp = b.r1_picks[0] ?? 99;
          return ap - bp;
        }
      }
    });
  }, [teams, q, tierFilter, sortKey]);

  const predCounts = useMemo(() => {
    if (!teams) return {} as Record<string, number>;
    const c: Record<string, number> = {};
    for (const t of teams) c[t.predictability] = (c[t.predictability] ?? 0) + 1;
    return c;
  }, [teams]);

  if (error) {
    return (
      <div className="card p-6 text-sm text-tier-low flex items-start gap-3">
        <AlertTriangle size={18} />
        <div>
          <div className="font-medium">Backend error</div>
          <div className="text-text-muted mt-1 font-mono">{error}</div>
        </div>
      </div>
    );
  }

  if (!teams) {
    return <div className="text-text-muted text-sm">Loading teams…</div>;
  }

  return (
    <div className="space-y-5">
      {/* Top stat strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <StatCard label="Teams" value={teams.length} Icon={Users} />
        <StatCard
          label="Total picks"
          value={teams.reduce((a, t) => a + t.total_picks, 0)}
          Icon={TrendingUp}
        />
        {(['HIGH', 'MEDIUM-HIGH', 'MEDIUM', 'LOW-MEDIUM', 'LOW'] as const).map((k) => (
          <div key={k} className={cn('card p-3 text-center border-l-4', tierClass(k))}>
            <div className="text-[11px] uppercase tracking-wide text-text-muted flex items-center justify-center gap-1">
              {k}
              {k === 'HIGH' && (
                <Tooltip text={GLOSSARY.predictability_high} side="bottom" />
              )}
              {k === 'LOW' && (
                <Tooltip text={GLOSSARY.predictability_low} side="bottom" />
              )}
            </div>
            <div className="text-2xl font-semibold mt-1 tabular-nums">
              {predCounts[k] ?? 0}
            </div>
          </div>
        ))}
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 px-3 py-2 bg-bg-card border border-border rounded-lg flex-1 min-w-[240px]">
          <Search size={14} className="text-text-subtle" />
          <input
            className="bg-transparent outline-none flex-1 text-sm placeholder:text-text-subtle"
            placeholder="Search team / GM / HC / position…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <select
          value={tierFilter}
          onChange={(e) => setTierFilter(e.target.value)}
          className="bg-bg-card border border-border rounded-lg px-3 py-2 text-sm outline-none"
        >
          <option value="all">All predictability</option>
          <option value="HIGH">HIGH</option>
          <option value="MEDIUM-HIGH">MEDIUM-HIGH</option>
          <option value="MEDIUM">MEDIUM</option>
          <option value="LOW-MEDIUM">LOW-MEDIUM</option>
          <option value="LOW">LOW</option>
        </select>
        <select
          value={sortKey}
          onChange={(e) => setSortKey(e.target.value as SortKey)}
          className="bg-bg-card border border-border rounded-lg px-3 py-2 text-sm outline-none"
        >
          <option value="pick">Sort: R1 pick</option>
          <option value="team">Sort: team code</option>
          <option value="win_pct">Sort: win %</option>
          <option value="predictability">Sort: predictability</option>
          <option value="visits">Sort: visits</option>
        </select>
        <div className="text-xs text-text-subtle">
          {filtered.length} / {teams.length}
        </div>
      </div>

      {/* Team grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {filtered.map((t) => (
          <TeamCard key={t.team} t={t} />
        ))}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  Icon,
}: {
  label: string;
  value: number | string;
  Icon: React.ComponentType<{ size?: number; className?: string }>;
}) {
  return (
    <div className="card p-3">
      <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-text-muted">
        <Icon size={12} />
        {label}
      </div>
      <div className="text-2xl font-semibold mt-1 tabular-nums">{value}</div>
    </div>
  );
}
