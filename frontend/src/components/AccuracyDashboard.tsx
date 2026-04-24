/**
 * AccuracyDashboard — live scoreboard vs public analyst mocks.
 *
 * Two modes:
 *   compact: headline tiles + top-5 leaderboard (used on Home)
 *   full:    headline tiles + full leaderboard + pick-by-pick (used on /accuracy)
 *
 * Source: /api/accuracy.
 */
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, Trophy, Target, Users, Activity } from 'lucide-react';
import { SmallCaps } from './editorial';
import { ErrorBlock } from './LoadState';

type AnalystRow = {
  name: string;
  exact: number;
  in_r1: number;
  team_match: number;
  exact_pct: number;
  in_r1_pct: number;
  team_pct: number;
  rank: number;
};

type PickRow = {
  pick: number;
  actual_team: string | null;
  actual_player: string | null;
  colin: string | null;
  colin_trade: string | null;
  colin_hit: boolean | null;
  trade_hit: boolean | null;
};

type AccuracyResp = {
  generated_at: string | null;
  total_r1_picks: number;
  r1_picks_drafted: number;
  colin_rank: number | null;
  colin_rank_trade: number | null;
  total_analysts: number;
  analysts: AnalystRow[];
  picks: PickRow[];
};

export function AccuracyDashboard({ compact = false }: { compact?: boolean }) {
  const [data, setData] = useState<AccuracyResp | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    setErr(null);
    fetch('/api/accuracy')
      .then(r => { if (!r.ok) throw new Error(`${r.status} ${r.statusText}`); return r.json(); })
      .then(setData)
      .catch(e => setErr(String(e?.message ?? e)));
  }, [reloadKey]);

  const colin = useMemo(
    () => data?.analysts.find(a => a.name === 'Colin') ?? null,
    [data]
  );
  const colinTrade = useMemo(
    () => data?.analysts.find(a => a.name === 'Colin w/Trade') ?? null,
    [data]
  );
  const fieldMedian = useMemo(() => {
    if (!data?.analysts?.length) return 0;
    const scores = [...data.analysts].map(a => a.exact).sort((a, b) => a - b);
    const mid = Math.floor(scores.length / 2);
    return scores.length % 2 ? scores[mid] : (scores[mid - 1] + scores[mid]) / 2;
  }, [data]);
  const fieldTop = data?.analysts[0]?.exact ?? 0;

  if (err) return <ErrorBlock message={err} onRetry={() => setReloadKey(k => k + 1)} />;
  if (!data) return (
    <div className="card p-8 text-center text-ink-muted italic">Loading scoreboard…</div>
  );
  if (data.r1_picks_drafted === 0) return (
    <div className="card p-8 text-center text-ink-muted italic">
      Live scoreboard will populate as R1 picks come in.
    </div>
  );

  const leaderboard = compact ? data.analysts.slice(0, 5) : data.analysts;

  return (
    <div className="space-y-6">
      {/* Headline tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-0 border border-ink">
        <Tile
          icon={<Trophy size={18} />}
          label="Your rank"
          value={colin?.rank ? `#${colin.rank}` : '—'}
          sub={colin ? `of ${data.total_analysts} analysts` : ''}
          accent
        />
        <Tile
          icon={<Target size={18} />}
          label="Exact hits"
          value={colin ? `${colin.exact}` : '—'}
          sub={colin ? `of ${data.r1_picks_drafted} · ${colin.exact_pct.toFixed(0)}%` : ''}
          progress={colin ? colin.exact / Math.max(fieldTop, 1) : 0}
        />
        <Tile
          icon={<Activity size={18} />}
          label="Field top / median"
          value={`${fieldTop} / ${fieldMedian.toFixed(1)}`}
          sub={data.analysts[0] ? data.analysts[0].name : ''}
        />
        <Tile
          icon={<Users size={18} />}
          label="R1 picks scored"
          value={`${data.r1_picks_drafted} / ${data.total_r1_picks}`}
          sub={data.r1_picks_drafted === data.total_r1_picks ? 'round complete' : 'live'}
        />
      </div>

      {/* Leaderboard */}
      <section>
        <div className="flex items-baseline justify-between border-b-2 border-ink px-1 pb-2 mb-3">
          <h2 className="display-broadcast text-lg md:text-xl text-ink">
            {compact ? 'Top-5 leaderboard' : 'Leaderboard'}
          </h2>
          {compact ? (
            <Link to="/accuracy" className="caps-tight text-xs text-accent-brass hover:text-accent-brassDeep inline-flex items-center gap-1">
              Full board <ArrowUpRight size={12} />
            </Link>
          ) : (
            <SmallCaps tight className="text-ink-muted">sorted by exact hits</SmallCaps>
          )}
        </div>
        <div className="overflow-hidden border border-ink-edge bg-paper-surface">
          <LeaderboardTable rows={leaderboard} scored={data.r1_picks_drafted} />
        </div>
        {!compact && (
          <p className="text-xs text-ink-muted mt-2 font-mono">
            <strong>Exact</strong> = correct player at the exact slot ·{' '}
            <strong>In R1</strong> = player taken somewhere in the first round ·{' '}
            <strong>Team</strong> = picked player ended up with that team
          </p>
        )}
      </section>

      {/* Pick-by-pick (full mode only) */}
      {!compact && data.picks.length > 0 && (
        <section>
          <div className="flex items-baseline justify-between border-b-2 border-ink px-1 pb-2 mb-3">
            <h2 className="display-broadcast text-xl text-ink">Pick-by-pick</h2>
            <SmallCaps tight className="text-ink-muted">
              your mock vs the board
            </SmallCaps>
          </div>
          <div className="overflow-x-auto border border-ink-edge bg-paper-surface">
            <table className="research-table w-full">
              <thead>
                <tr>
                  <th className="num w-12">Pick</th>
                  <th className="w-24">Team</th>
                  <th>Actual</th>
                  <th>Your mock</th>
                  <th>With trades</th>
                  <th className="num w-24">Hit</th>
                </tr>
              </thead>
              <tbody>
                {data.picks.map(p => (
                  <tr key={p.pick}>
                    <td className="num font-mono">{p.pick}</td>
                    <td className="text-ink-muted text-xs">{p.actual_team ?? '—'}</td>
                    <td className="font-serif">
                      {p.actual_player ?? <span className="text-ink-muted italic">pending</span>}
                    </td>
                    <td className="font-serif text-sm">{p.colin ?? '—'}</td>
                    <td className="font-serif text-sm text-ink-soft">{p.colin_trade ?? '—'}</td>
                    <td className="num">
                      {p.actual_player ? (
                        <HitBadge colin={!!p.colin_hit} trade={!!p.trade_hit} />
                      ) : (
                        <span className="text-ink-muted">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Trade variant note (full mode) */}
      {!compact && colinTrade && (
        <section className="border-t border-ink-edge pt-4">
          <SmallCaps tight className="text-ink-muted">Trade-aware variant</SmallCaps>
          <p className="text-sm text-ink-soft mt-1.5">
            The trade-mock ranks <span className="font-bold text-ink">#{colinTrade.rank}</span>{' '}
            with {colinTrade.exact} exact hits ({colinTrade.exact_pct.toFixed(1)}%).
            Exact matches are harder with trades because the team at each slot can shift.
          </p>
        </section>
      )}
    </div>
  );
}

function Tile({ icon, label, value, sub, accent, progress }: {
  icon?: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  accent?: boolean;
  progress?: number;   // 0..1
}) {
  return (
    <div className="p-4 lg:p-5 border-r border-ink-edge last:border-r-0 border-b lg:border-b-0 bg-paper-surface">
      <div className="flex items-center gap-2 mb-1.5 text-ink-muted">
        {icon}
        <SmallCaps tight>{label}</SmallCaps>
      </div>
      <div
        className="display-num text-3xl md:text-4xl leading-none"
        style={{ color: accent ? '#B68A2F' : '#0B1F3A' }}
      >
        {value}
      </div>
      {sub && (
        <div className="font-mono text-[0.68rem] text-ink-muted mt-1.5 truncate">
          {sub}
        </div>
      )}
      {typeof progress === 'number' && progress > 0 && (
        <div className="mt-2 h-1 bg-paper-hover rounded-sm overflow-hidden">
          <div
            className="h-full rounded-sm"
            style={{
              width: `${Math.min(100, progress * 100)}%`,
              background: accent ? '#B68A2F' : '#0B1F3A',
            }}
          />
        </div>
      )}
    </div>
  );
}

function LeaderboardTable({ rows, scored }: { rows: AnalystRow[]; scored: number }) {
  const top = rows[0]?.exact ?? 1;
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="bg-paper-raised border-b border-ink-edge">
          <th className="px-3 py-2 text-left font-mono text-[0.62rem] caps-tight text-ink-muted w-10">#</th>
          <th className="px-3 py-2 text-left font-mono text-[0.62rem] caps-tight text-ink-muted">Analyst</th>
          <th className="px-3 py-2 text-right font-mono text-[0.62rem] caps-tight text-ink-muted w-20">Exact</th>
          <th className="px-3 py-2 text-left font-mono text-[0.62rem] caps-tight text-ink-muted w-32">Progress</th>
          <th className="px-3 py-2 text-right font-mono text-[0.62rem] caps-tight text-ink-muted w-16">In R1</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(a => {
          const isColin = a.name.startsWith('Colin');
          const pct = Math.max(top, 1) > 0 ? a.exact / Math.max(top, 1) : 0;
          return (
            <tr
              key={a.name}
              className={`border-b border-ink-edge/50 last:border-b-0 ${
                isColin ? 'bg-accent-brass/8' : 'hover:bg-paper-hover'
              }`}
            >
              <td className={`px-3 py-2 font-mono text-xs ${isColin ? 'text-accent-brass font-bold' : 'text-ink-muted'}`}>
                {isColin && <span className="mr-1">▶</span>}
                {a.rank}
              </td>
              <td className={`px-3 py-2 ${isColin ? 'text-ink font-semibold' : 'text-ink'}`}>
                {a.name}
              </td>
              <td className="px-3 py-2 text-right font-mono">
                <span className={isColin ? 'text-ink font-bold' : 'text-ink'}>{a.exact}</span>
                <span className="text-ink-muted">/{scored}</span>
              </td>
              <td className="px-3 py-2">
                <div className="h-1.5 bg-paper-hover overflow-hidden">
                  <div
                    className="h-full"
                    style={{
                      width: `${pct * 100}%`,
                      background: isColin ? '#B68A2F' : '#0B1F3A',
                    }}
                  />
                </div>
              </td>
              <td className="px-3 py-2 text-right font-mono text-ink-muted text-xs">
                {a.in_r1}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function HitBadge({ colin, trade }: { colin: boolean; trade: boolean }) {
  const anyHit = colin || trade;
  if (!anyHit) {
    return (
      <span className="caps-tight text-[0.56rem] font-bold px-1.5 py-[1px]"
            style={{ background: '#8C2E2A33', color: '#8C2E2A' }}>
        miss
      </span>
    );
  }
  return (
    <span
      className="caps-tight text-[0.58rem] font-bold px-1.5 py-[1px]"
      style={{ background: '#3A6B4633', color: '#3A6B46' }}
      title={colin && trade ? 'Both mocks hit' : colin ? 'Main mock hit' : 'Trade mock hit'}
    >
      {colin && trade ? 'hit ×2' : colin ? 'hit' : 'trade hit'}
    </span>
  );
}
