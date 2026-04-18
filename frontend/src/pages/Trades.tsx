import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Shield, AlertTriangle } from 'lucide-react';
import { api } from '../lib/api';
import { cn } from '../lib/format';
import { teamMeta } from '../lib/teams';

type Trade = {
  pick: number | null;
  up_team: string | null;
  down_team: string | null;
  target_player: string;
  times_mocked: number;
  tier1_credible: boolean;
  compensation: string;
  trade_type: string;
  analysts: string;
  notes: string;
};

export function Trades() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [constraints, setConstraints] = useState<any[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [tier1Only, setTier1Only] = useState(false);
  const [minMocks, setMinMocks] = useState(1);

  useEffect(() => {
    Promise.all([api.analystConsensus(), api.league()])
      .then(([ac, lg]) => {
        setTrades(ac.trades as Trade[]);
        setConstraints(lg?.hard_trade_constraints_struct ?? []);
      })
      .catch((e) => setErr(String(e)));
  }, []);

  if (err) return <div className="card p-6 text-tier-low text-sm">{err}</div>;

  const filtered = trades.filter((t) => {
    if (tier1Only && !t.tier1_credible) return false;
    if (t.times_mocked < minMocks) return false;
    return true;
  }).sort((a, b) => b.times_mocked - a.times_mocked);

  return (
    <div className="space-y-5">
      <div>
        <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted mb-1">
          Scenarios from analyst mocks
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">Trades</h1>
        <p className="text-sm text-text-muted mt-1 max-w-3xl">
          Every trade scenario from the 20-mock analyst panel, ranked by how
          many independent analysts mocked the same trade. Tier-1 credibility
          marks trades confirmed by Brugler, Kiper, McShay, Schrager, ESPN Scouts,
          or post-combine PFF consensus.
        </p>
      </div>

      {/* Hard trade constraints */}
      {constraints.length > 0 && (
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3">
            <Shield size={14} className="text-accent" />
            <h3 className="text-sm font-semibold tracking-tight">
              Hard trade constraints
            </h3>
          </div>
          <div className="text-xs text-text-muted mb-3">
            Teams with strong historical patterns that override mock projections.
          </div>
          <div className="space-y-2">
            {constraints.map((c, i) => (
              <div key={i} className="flex items-start gap-3 text-sm">
                <div className="flex items-center gap-1 flex-none">
                  {(c.teams ?? []).map((t: string) => (
                    <span
                      key={t}
                      className="badge border-border text-text font-mono"
                    >
                      {t}
                    </span>
                  ))}
                </div>
                <div className="text-text-muted">{c.constraint}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="card p-3 flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm text-text cursor-pointer select-none">
          <input
            type="checkbox"
            checked={tier1Only}
            onChange={(e) => setTier1Only(e.target.checked)}
            className="accent-accent"
          />
          Tier-1 credible only
        </label>
        <div className="h-4 w-px bg-border" />
        <label className="flex items-center gap-2 text-sm text-text-muted">
          Min mocks:
          <input
            type="number"
            min={1}
            max={10}
            value={minMocks}
            onChange={(e) => setMinMocks(Number(e.target.value) || 1)}
            className="bg-bg-raised border border-border rounded-md px-2 py-1 text-sm w-16 outline-none focus:border-accent font-mono"
          />
        </label>
        <div className="text-xs text-text-subtle ml-auto">
          {filtered.length} / {trades.length} scenarios
        </div>
      </div>

      {/* Trade list */}
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[10px] uppercase tracking-wider text-text-subtle border-b border-border bg-bg-raised/60">
              <th className="text-left font-medium py-2.5 pl-4 pr-2 w-14">Pick</th>
              <th className="text-left font-medium py-2.5 px-2">Trade</th>
              <th className="text-left font-medium py-2.5 px-2">Target player</th>
              <th className="text-right font-medium py-2.5 px-2 w-20">Mocks</th>
              <th className="text-left font-medium py-2.5 px-2 w-24">Tier-1</th>
              <th className="text-left font-medium py-2.5 pr-4 pl-2">Compensation</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((t, i) => {
              const upTeam = teamMeta(t.up_team ?? '');
              const downTeam = teamMeta(t.down_team ?? '');
              return (
                <tr key={i} className="border-b border-border/60 last:border-0 hover:bg-bg-hover/40">
                  <td className="py-2.5 pl-4 pr-2 font-mono text-text-muted tabular-nums">
                    {t.pick ?? '—'}
                  </td>
                  <td className="py-2.5 px-2">
                    <div className="flex items-center gap-1.5 text-sm">
                      {upTeam && (
                        <Link to={`/team/${upTeam.abbr}`} className="hover:underline">
                          <span className="font-semibold">{upTeam.abbr}</span>
                          <span className="text-text-subtle text-xs"> up</span>
                        </Link>
                      )}
                      <ArrowRight size={12} className="text-text-subtle" />
                      {downTeam && (
                        <Link to={`/team/${downTeam.abbr}`} className="hover:underline">
                          <span className="font-semibold">{downTeam.abbr}</span>
                          <span className="text-text-subtle text-xs"> down</span>
                        </Link>
                      )}
                    </div>
                    {t.trade_type && (
                      <div className="text-[10px] text-text-subtle mt-0.5">{t.trade_type}</div>
                    )}
                  </td>
                  <td className="py-2.5 px-2 text-sm">{t.target_player}</td>
                  <td className="py-2.5 px-2 text-right font-mono tabular-nums">
                    <span className={cn(
                      t.times_mocked >= 4 ? 'text-tier-high font-semibold' :
                      t.times_mocked >= 2 ? 'text-tier-midhi' :
                      'text-text-muted',
                    )}>
                      {t.times_mocked}
                    </span>
                  </td>
                  <td className="py-2.5 px-2">
                    {t.tier1_credible ? (
                      <span className="badge border-tier-high/40 bg-tier-high/10 text-tier-high">YES</span>
                    ) : (
                      <span className="text-xs text-text-subtle">no</span>
                    )}
                  </td>
                  <td className="py-2.5 pr-4 pl-2 text-xs text-text-muted max-w-xs">
                    {t.compensation || '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="card p-4 flex items-start gap-3 text-xs text-text-muted">
        <AlertTriangle size={14} className="text-text-muted mt-0.5 flex-none" />
        <div>
          <span className="font-medium text-text">Reminder:</span> these are
          scenarios mocked by analysts, not guaranteed outcomes. Many single-mock
          trades are individual analyst guesses — the Monte Carlo simulator
          only scripts the 4 tier-1 credible trades with ≥2 mentions, treating
          others as low-probability noise.
        </div>
      </div>
    </div>
  );
}
