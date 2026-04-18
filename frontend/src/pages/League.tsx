import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertOctagon, GitBranch, HelpCircle, TrendingUp, TrendingDown } from 'lucide-react';
import { api } from '../lib/api';
import { teamMeta } from '../lib/teams';

export function League() {
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.league().then(setData).catch((e) => setErr(String(e)));
  }, []);

  if (err) return <div className="card p-6 text-tier-low text-sm">{err}</div>;
  if (!data) return <div className="text-text-muted text-sm">Loading…</div>;

  const cascades = data.cascade_rules_struct ?? [];
  const unknowns = data.known_unknowns_struct ?? [];
  const tradeUp = data.trade_up_candidates_struct ?? [];
  const tradeDown = data.trade_down_candidates_struct ?? [];

  return (
    <div className="space-y-5">
      <div>
        <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted mb-1">
          Draft-wide synthesis
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">League intel</h1>
        <p className="text-sm text-text-muted mt-1 max-w-3xl">
          League-wide patterns, cascade dependencies, and model-breaking
          scenarios extracted from the comprehensive team profile PDF.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Trade-up candidates */}
        <InfoCard Icon={TrendingUp} title="Trade-up candidates">
          <ol className="space-y-2">
            {tradeUp.map((t: any, i: number) => (
              <li key={i} className="flex items-start gap-3 text-sm">
                <span className="font-mono text-text-subtle w-5 flex-none">{t.rank}.</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <Link to={`/team/${t.team}`} className="font-semibold hover:underline">
                      {teamMeta(t.team)?.full ?? t.team}
                    </Link>
                    {t.picks && (
                      <span className="text-xs text-text-muted font-mono">
                        picks {t.picks}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-text-muted mt-0.5">{t.notes}</div>
                </div>
              </li>
            ))}
          </ol>
        </InfoCard>

        {/* Trade-down candidates */}
        <InfoCard Icon={TrendingDown} title="Trade-down candidates">
          <ol className="space-y-2">
            {tradeDown.map((t: any, i: number) => (
              <li key={i} className="flex items-start gap-3 text-sm">
                <span className="font-mono text-text-subtle w-5 flex-none">{t.rank}.</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <Link to={`/team/${t.team}`} className="font-semibold hover:underline">
                      {teamMeta(t.team)?.full ?? t.team}
                    </Link>
                    {t.picks && (
                      <span className="text-xs text-text-muted font-mono">
                        pick {t.picks}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-text-muted mt-0.5">{t.notes}</div>
                </div>
              </li>
            ))}
          </ol>
        </InfoCard>

        {/* Cascade rules */}
        <InfoCard Icon={GitBranch} title="Cascade rules" span={2}>
          <div className="text-xs text-text-muted mb-3">
            When a trigger team takes a specific position, the dependent team's
            probability at that position shifts. The simulator applies these live.
          </div>
          <div className="space-y-2">
            {cascades.map((c: any, i: number) => (
              <div key={i} className="flex items-start gap-3 text-sm bg-bg-raised rounded-md p-3">
                <div className="flex items-center gap-1 flex-none">
                  <Link to={`/team/${c.trigger_team}`} className="font-semibold hover:underline">
                    {c.trigger_team}
                  </Link>
                  <span className="text-xs text-text-subtle font-mono">
                    #{c.trigger_pick} {c.trigger_position}
                  </span>
                  <span className="text-text-subtle mx-1">→</span>
                  <Link to={`/team/${c.dependent_team}`} className="font-semibold hover:underline">
                    {c.dependent_team}
                  </Link>
                  <span className="text-xs text-text-subtle font-mono">
                    #{c.dependent_pick}
                  </span>
                </div>
                <div className="flex-1 text-text-muted">{c.effect}</div>
              </div>
            ))}
          </div>
        </InfoCard>

        {/* Model-breaking scenarios */}
        <InfoCard Icon={AlertOctagon} title="Known unknowns" span={2}>
          <div className="text-xs text-text-muted mb-3">
            Scenarios that could break mock predictions — flag these if they
            materialize during draft day.
          </div>
          <ol className="space-y-2">
            {unknowns.map((u: string, i: number) => (
              <li key={i} className="flex items-start gap-3 text-sm">
                <span className="font-mono text-text-subtle w-5 flex-none">{i + 1}.</span>
                <div className="text-text">{u}</div>
              </li>
            ))}
          </ol>
        </InfoCard>

        {/* Position urgency heat map */}
        {data.position_urgency_heat_map && (
          <InfoCard Icon={HelpCircle} title="Position urgency" span={2}>
            <pre className="text-xs text-text-muted leading-5 font-sans whitespace-pre-wrap">
              {data.position_urgency_heat_map}
            </pre>
          </InfoCard>
        )}
      </div>
    </div>
  );
}

function InfoCard({
  title, Icon, children, span,
}: {
  title: string;
  Icon: React.ComponentType<{ size?: number; className?: string }>;
  children: React.ReactNode;
  span?: number;
}) {
  return (
    <div className={`card p-5 ${span === 2 ? 'lg:col-span-2' : ''}`}>
      <div className="flex items-center gap-2 mb-3">
        <Icon size={14} className="text-accent" />
        <h3 className="text-sm font-semibold tracking-tight">{title}</h3>
      </div>
      {children}
    </div>
  );
}
