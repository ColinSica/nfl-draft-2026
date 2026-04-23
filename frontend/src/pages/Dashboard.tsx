/**
 * Teams directory — all 32 NFL teams in a grid, color-coded by primary,
 * sortable by pick number. Light broadcast theme.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search } from 'lucide-react';
import { api, type TeamSummary } from '../lib/api';
import { teamColor } from '../lib/teamColors';
import { secondaryInk } from '../lib/color';
import { SectionHeader, SmallCaps, MissingText } from '../components/editorial';
import { LoadingBlock, ErrorBlock } from '../components/LoadState';
import { displayValue, displayQbUrgency, displayCapTier } from '../lib/display';

type SortKey = 'pick' | 'team' | 'needs';

export function Dashboard() {
  const [teams, setTeams] = useState<TeamSummary[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<SortKey>('pick');

  useEffect(() => {
    setErr(null);
    setTeams(null);
    api.teams()
      .then((r) => setTeams(r.teams))
      .catch((e) => { setErr(String(e?.message ?? e)); setTeams([]); });
  }, [reloadKey]);

  const filtered = useMemo(() => {
    if (!teams) return [];
    const q = query.trim().toLowerCase();
    const arr = teams.filter((t) => {
      if (!q) return true;
      return (
        t.team.toLowerCase().includes(q) ||
        (t.gm ?? '').toLowerCase().includes(q) ||
        (t.hc ?? '').toLowerCase().includes(q)
      );
    });
    arr.sort((a, b) => {
      if (sort === 'team') return a.team.localeCompare(b.team);
      if (sort === 'needs') {
        const aw = a.top_needs?.[0]?.score ?? 0;
        const bw = b.top_needs?.[0]?.score ?? 0;
        return bw - aw;
      }
      const ap = a.r1_picks?.[0] ?? 999;
      const bp = b.r1_picks?.[0] ?? 999;
      return ap - bp;
    });
    return arr;
  }, [teams, query, sort]);

  return (
    <div className="space-y-10 pb-12">
      <SectionHeader kicker="Directory" title="All 32 teams." />

      <div className="flex flex-wrap items-center gap-3">
        <label
          htmlFor="teams-search"
          className="flex items-center gap-2 bg-paper-surface border border-ink-edge px-3 py-2 min-w-[240px] flex-1 max-w-md"
        >
          <Search size={16} className="text-ink-soft" aria-hidden="true" />
          <span className="sr-only">Search teams</span>
          <input
            id="teams-search"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search team, GM, or HC…"
            className="flex-1 bg-transparent outline-none text-sm text-ink placeholder:text-ink-soft/60"
          />
        </label>
        <div className="inline-flex border border-ink-edge bg-paper-surface">
          {(['pick', 'team', 'needs'] as SortKey[]).map((k) => (
            <button
              key={k}
              onClick={() => setSort(k)}
              className={`px-3 py-2 caps-tight border-r border-ink-edge last:border-r-0 transition ${
                sort === k ? 'bg-ink text-paper' : 'text-ink-soft hover:text-ink'
              }`}
            >
              {k === 'pick' ? 'By pick' : k === 'team' ? 'A–Z' : 'By need'}
            </button>
          ))}
        </div>
        <span className="ml-auto text-sm text-ink-soft">
          {filtered.length} {filtered.length === 1 ? 'team' : 'teams'}
        </span>
      </div>

      {err && (!teams || teams.length === 0) ? (
        <ErrorBlock message={err} onRetry={() => setReloadKey(k => k + 1)} />
      ) : !teams ? (
        <LoadingBlock label="Loading teams…" />
      ) : filtered.length === 0 ? (
        <div className="card p-10 text-center text-ink-soft italic">No teams match.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((t) => <TeamCard key={t.team} t={t} />)}
        </div>
      )}
    </div>
  );
}

function TeamCard({ t }: { t: TeamSummary }) {
  const tc = teamColor(t.team);
  const firstPick = t.r1_picks?.[0];
  const topNeed = t.top_needs?.[0];

  return (
    <Link
      to={`/team/${t.team}`}
      className="card group hover:shadow-card-raised hover:-translate-y-0.5 transition-all ease-broadcast duration-200 relative overflow-hidden"
    >
      <div className="h-1" style={{ background: tc.primary }} />

      <div className="p-5 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span
                className="w-8 h-8 flex items-center justify-center text-xs font-bold shrink-0"
                style={{
                  background: tc.primary,
                  color: secondaryInk(tc.secondary),
                }}
              >
                {t.team}
              </span>
              <div className="min-w-0">
                <div className="display-broadcast text-xl leading-none text-ink truncate">
                  {tc.name}
                </div>
                <div className="text-[0.7rem] mono-label mt-0.5 truncate">
                  {displayValue(t.hc, '—')} · {displayValue(t.gm, '—')}
                </div>
              </div>
            </div>
          </div>
          <div className="text-right shrink-0">
            {firstPick ? (
              <>
                <div className="display-num text-3xl leading-none text-ink">
                  {String(firstPick).padStart(2, '0')}
                </div>
                <div className="caps-tight text-ink-soft text-[0.65rem]">
                  {t.r1_picks.length > 1 ? `+${t.r1_picks.length - 1} R1` : 'R1 pick'}
                </div>
              </>
            ) : (
              <span className="caps-tight text-ink-soft">No R1</span>
            )}
          </div>
        </div>

        {(t.new_gm || t.new_hc) && (
          <div className="flex flex-wrap gap-1.5">
            {t.new_gm && <span className="badge">New GM</span>}
            {t.new_hc && <span className="badge">New HC</span>}
          </div>
        )}

        <div className="border-t border-ink-edge pt-3 space-y-2">
          <SmallCaps tight className="text-ink-soft block">Top need</SmallCaps>
          {topNeed ? (
            <div className="flex items-baseline gap-2">
              <span
                className="display-broadcast text-lg leading-none px-2 py-0.5"
                style={{ background: `${tc.primary}15`, color: tc.primary }}
              >
                {topNeed.pos}
              </span>
              <span className="text-ink-soft text-xs font-mono">
                weight {topNeed.score.toFixed(1)}
              </span>
            </div>
          ) : (
            <MissingText>No stack</MissingText>
          )}
        </div>

        <div className="flex flex-wrap gap-1.5 text-[0.7rem]">
          <span className="badge">{displayQbUrgency(t.qb_urgency)}</span>
          <span className="badge">{displayCapTier(t.cap_tier)}</span>
        </div>
      </div>
    </Link>
  );
}
