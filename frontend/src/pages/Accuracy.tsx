/**
 * Accuracy — live scoreboard vs ~30 public analyst mocks.
 *
 * Source: /api/accuracy (backed by data/processed/accuracy_2026.json,
 * built from the Updated 2026 Real Progress Excel).
 */
import { useEffect, useMemo, useState } from 'react';
import { SectionHeader, SmallCaps, HRule, MissingText } from '../components/editorial';
import { ErrorBlock, LoadingBlock } from '../components/LoadState';

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

export function Accuracy() {
  const [data, setData] = useState<AccuracyResp | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    setErr(null);
    setData(null);
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

  return (
    <div className="space-y-10 pb-16">
      <SectionHeader
        kicker="Live accuracy"
        title="Colin vs the analyst field."
        deck="Real-time scoreboard as the R1 picks come off the board. Each row is a published 2026 mock; one point per exact player match at the correct slot."
      />

      {err && <ErrorBlock message={err} onRetry={() => setReloadKey(k => k + 1)} />}
      {!data && !err && <LoadingBlock label="Loading scoreboard…" />}

      {data && data.r1_picks_drafted === 0 && (
        <MissingText>
          No R1 picks drafted yet. Scoreboard will populate as picks come in.
        </MissingText>
      )}

      {data && data.r1_picks_drafted > 0 && (
        <>
          {/* Headline stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-0 border border-ink-edge">
            <HeadlineStat
              label="R1 picks scored"
              value={`${data.r1_picks_drafted}/${data.total_r1_picks}`}
            />
            <HeadlineStat
              label="Your rank"
              value={colin?.rank ? `#${colin.rank}/${data.total_analysts}` : '—'}
              accent
            />
            <HeadlineStat
              label="Your exact hits"
              value={colin ? `${colin.exact} / ${data.r1_picks_drafted}` : '—'}
              sub={colin ? `${colin.exact_pct}%` : ''}
            />
            <HeadlineStat
              label="Field median (exact)"
              value={fieldMedian.toFixed(1)}
            />
          </div>

          {/* Leaderboard */}
          <section>
            <div className="flex items-baseline justify-between border-b-2 border-ink px-1 pb-2 mb-3">
              <h2 className="display-broadcast text-xl text-ink">Leaderboard</h2>
              <SmallCaps tight className="text-ink-muted">
                sorted by exact hits
              </SmallCaps>
            </div>
            <div className="overflow-x-auto">
              <table className="research-table w-full">
                <thead>
                  <tr>
                    <th className="num w-12">#</th>
                    <th>Analyst</th>
                    <th className="num">Exact</th>
                    <th className="num">In R1</th>
                    <th className="num">Team</th>
                    <th className="num">Exact %</th>
                  </tr>
                </thead>
                <tbody>
                  {data.analysts.map(a => {
                    const isColin = a.name.startsWith('Colin');
                    return (
                      <tr key={a.name} className={isColin ? 'bg-accent-brass/10' : ''}>
                        <td className="num font-mono">
                          {isColin && (
                            <span className="text-accent-brass mr-1">▶</span>
                          )}
                          {a.rank}
                        </td>
                        <td className={isColin ? 'font-semibold text-ink' : ''}>
                          {a.name}
                        </td>
                        <td className="num font-mono">
                          <span className={`text-ink ${isColin ? 'font-bold' : ''}`}>
                            {a.exact}
                          </span>
                          <span className="text-ink-muted"> / {data.r1_picks_drafted}</span>
                        </td>
                        <td className="num font-mono text-ink-soft">{a.in_r1}</td>
                        <td className="num font-mono text-ink-soft">{a.team_match}</td>
                        <td className="num font-mono text-ink-soft">{a.exact_pct.toFixed(1)}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-ink-muted mt-2 font-mono">
              <strong>Exact</strong> = correct player at the exact slot ·
              <strong> In R1</strong> = player taken somewhere in the first round ·
              <strong> Team</strong> = picked player ended up with that team
            </p>
          </section>

          {/* Pick-by-pick */}
          {data.picks.length > 0 && (
            <section>
              <div className="flex items-baseline justify-between border-b-2 border-ink px-1 pb-2 mb-3">
                <h2 className="display-broadcast text-xl text-ink">Pick-by-pick</h2>
                <SmallCaps tight className="text-ink-muted">
                  Colin's mock vs the board
                </SmallCaps>
              </div>
              <div className="overflow-x-auto">
                <table className="research-table w-full">
                  <thead>
                    <tr>
                      <th className="num w-12">Pick</th>
                      <th>Team</th>
                      <th>Actual</th>
                      <th>Colin's mock</th>
                      <th>Colin w/Trade</th>
                      <th className="num w-20">Hit</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.picks.map(p => {
                      const drafted = p.actual_player != null;
                      return (
                        <tr key={p.pick}>
                          <td className="num font-mono">{p.pick}</td>
                          <td className="text-ink-muted text-xs">
                            {p.actual_team ?? '—'}
                          </td>
                          <td className="font-serif">
                            {drafted ? p.actual_player : <span className="text-ink-muted italic">pending</span>}
                          </td>
                          <td className="font-serif text-sm">{p.colin ?? '—'}</td>
                          <td className="font-serif text-sm text-ink-soft">{p.colin_trade ?? '—'}</td>
                          <td className="num">
                            {drafted ? (
                              <HitBadge
                                colin={!!p.colin_hit}
                                trade={!!p.trade_hit}
                              />
                            ) : (
                              <span className="text-ink-muted">—</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Trade-mock footnote */}
          {colinTrade && (
            <section className="border-t border-ink-edge pt-4">
              <SmallCaps tight className="text-ink-muted">Colin w/Trade</SmallCaps>
              <p className="text-sm text-ink-soft mt-1.5">
                The trade-aware variant ranks{' '}
                <span className="font-bold text-ink">#{colinTrade.rank}</span>{' '}
                with {colinTrade.exact} exact hits
                ({colinTrade.exact_pct.toFixed(1)}%). Exact matches are harder
                with trades because the team at each slot can shift.
              </p>
            </section>
          )}

          <HRule />
          <p className="text-xs text-ink-muted font-mono">
            Updated {data.generated_at
              ? new Date(data.generated_at).toLocaleString()
              : '—'}{' '}
            · Source: data/Updated 2026 Real Progress.xlsx
          </p>
        </>
      )}
    </div>
  );
}

function HeadlineStat({ label, value, sub, accent }: {
  label: string;
  value: string;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <div className="p-4 border-r border-ink-edge last:border-r-0 border-b md:border-b-0">
      <SmallCaps tight className="text-ink-muted block mb-1">{label}</SmallCaps>
      <div
        className="display-num text-3xl md:text-4xl"
        style={{ color: accent ? '#B68A2F' : '#0B1F3A' }}
      >
        {value}
      </div>
      {sub && <div className="font-mono text-xs text-ink-muted mt-0.5">{sub}</div>}
    </div>
  );
}

function HitBadge({ colin, trade }: { colin: boolean; trade: boolean }) {
  const anyHit = colin || trade;
  if (!anyHit) {
    return (
      <span
        className="caps-tight text-[0.56rem] font-bold px-1.5 py-[1px]"
        style={{ background: '#8C2E2A33', color: '#8C2E2A' }}
      >
        miss
      </span>
    );
  }
  return (
    <span
      className="caps-tight text-[0.58rem] font-bold px-1.5 py-[1px]"
      style={{ background: '#3A6B4633', color: '#3A6B46' }}
      title={colin && trade ? 'Both mocks hit' : colin ? 'Colin hit' : 'Trade-mock hit'}
    >
      {colin && trade ? 'hit ×2' : colin ? 'hit' : 'trade hit'}
    </span>
  );
}
