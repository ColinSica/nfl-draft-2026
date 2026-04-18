import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ArrowLeft, Briefcase, AlertOctagon, Target, Calendar, DollarSign,
  GraduationCap, Users, TrendingDown, TrendingUp, Shield,
} from 'lucide-react';
import { api } from '../lib/api';
import { cn, fmtPct, tierClass } from '../lib/format';
import { teamMeta } from '../lib/teams';
import { Tooltip, GLOSSARY } from '../components/Tooltip';

type Tab = 'overview' | 'needs' | 'roster' | 'narrative' | 'intel';

export function TeamDetail() {
  const { abbr } = useParams<{ abbr: string }>();
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('overview');

  useEffect(() => {
    if (!abbr) return;
    api.team(abbr).then(setData).catch((e) => setErr(String(e)));
  }, [abbr]);

  if (err) return <div className="card p-6 text-tier-low text-sm">{err}</div>;
  if (!data) return <div className="text-text-muted text-sm">Loading {abbr}…</div>;

  const tMeta = teamMeta(data.team);

  const narrative = data.narrative ?? {};
  const roster = data.roster_context ?? {};
  const cap = data.cap_context ?? {};
  const coaching = data.coaching ?? {};
  const inj = narrative.injury_flags ?? [];
  const cliffs = roster.age_cliffs ?? [];
  const prevAlloc = roster.previous_year_allocation ?? {};
  const archetypes = narrative.player_archetypes ?? {};
  const hardConstraints = (narrative.hard_constraints ?? []).map((c: any) => c.type);

  return (
    <div className="space-y-5">
      {/* Team color banner */}
      <div
        className="card overflow-hidden relative"
        style={{
          borderLeft: `4px solid ${tMeta?.primary ?? '#303648'}`,
          background: `linear-gradient(90deg, ${tMeta?.primary ?? '#161a23'}15 0%, transparent 40%)`,
        }}
      >
        <div className="p-5 flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-start gap-4">
            {tMeta && (
              <img
                src={tMeta.logo}
                alt={tMeta.abbr}
                className="w-16 h-16 object-contain flex-none"
                onError={(e) => ((e.target as HTMLImageElement).style.display = 'none')}
              />
            )}
            <div>
              <Link
                to="/"
                className="inline-flex items-center gap-1.5 text-xs text-text-muted hover:text-text mb-2"
              >
                <ArrowLeft size={12} /> All teams
              </Link>
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-3xl font-semibold tracking-tight">
                  {tMeta?.full ?? data.team}
                </h1>
                <span className={cn('badge', tierClass(data.predictability))}>
                  {data.predictability || '—'}
                </span>
                {data.new_gm && (
                  <span className="badge border-tier-midhi/40 bg-tier-midhi/10 text-tier-midhi">
                    new GM
                  </span>
                )}
                {data.new_hc && (
                  <span className="badge border-tier-midhi/40 bg-tier-midhi/10 text-tier-midhi">
                    new HC
                  </span>
                )}
              </div>
              <div className="text-sm text-text-muted mt-1">
                GM {data.gm} · HC {data.hc} · record {((data.win_pct ?? 0) * 17).toFixed(0)}–
                {(17 - (data.win_pct ?? 0) * 17).toFixed(0)}
              </div>
            </div>
          </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-center">
          {(data.all_r1_picks ?? []).map((pn: number) => (
            <div key={pn} className="card px-4 py-2 min-w-[80px]">
              <div className="font-mono text-3xl font-semibold">#{pn}</div>
              <div className="text-[10px] text-text-subtle uppercase tracking-wide">
                R1 pick
              </div>
            </div>
          ))}
          <div className="card px-4 py-2">
            <div className="font-mono text-3xl font-semibold">{data.total_picks}</div>
            <div className="text-[10px] text-text-subtle uppercase tracking-wide">
              total picks
            </div>
          </div>
        </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {(['overview', 'needs', 'roster', 'narrative', 'intel'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition',
              tab === t
                ? 'border-accent text-text'
                : 'border-transparent text-text-muted hover:text-text',
            )}
          >
            {t[0].toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <InfoCard title="Leadership" Icon={Briefcase}>
            <pre className="text-xs text-text whitespace-pre-wrap leading-5 font-sans">
              {narrative.leadership || '—'}
            </pre>
          </InfoCard>
          <InfoCard title="2025 context" Icon={Calendar}>
            <p className="text-sm text-text leading-6">
              {narrative.context_2025 || '—'}
            </p>
          </InfoCard>
          <InfoCard title="QB situation" Icon={Target}>
            <p className="text-sm text-text leading-6">
              {narrative.qb_situation || '—'}
            </p>
            <div className="mt-2 text-xs text-text-muted">
              Urgency: {fmtPct((data.qb_urgency ?? 0))}
            </div>
          </InfoCard>

          <InfoCard title="Scheme identity" Icon={Shield} tip={GLOSSARY.scheme}>
            <div className="text-xs text-text-muted mb-2">
              type: <span className="text-text font-mono">
                {data.scheme?.type ?? 'default'}
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5 mb-2">
              {(data.scheme?.premium ?? []).map((p: string) => (
                <span key={p} className="badge border-accent/40 bg-accent/10 text-accent">
                  {p}
                </span>
              ))}
            </div>
            <p className="text-xs text-text leading-5">
              {narrative.scheme_identity ?? ''}
            </p>
          </InfoCard>

          <InfoCard title="Draft capital" Icon={TrendingUp}>
            <div className="text-sm space-y-1">
              <Row label="R1 picks">
                <span className="font-mono">{(data.all_r1_picks ?? []).join(', ') || '—'}</span>
              </Row>
              <Row label="Total">
                <span className="font-mono">{data.total_picks}</span>
              </Row>
              <Row label="Abundance">
                <span className="capitalize">{data.draft_capital?.capital_abundance ?? '—'}</span>
              </Row>
              <Row label="Cap tier">
                <span className={cn(
                  'capitalize',
                  cap.constraint_tier === 'tight' && 'text-tier-midlo',
                  cap.constraint_tier === 'flush' && 'text-tier-high',
                )}>
                  {cap.constraint_tier ?? '—'}
                </span>
              </Row>
            </div>
          </InfoCard>

          <InfoCard title="Trade behavior" Icon={TrendingDown} tip="Historical trade rates for this GM, adjusted by PDF narrative signals and hard constraints.">

            <div className="text-sm space-y-1">
              <Row label="Trade up">
                <span className="font-mono">{fmtPct(data.trade_behavior?.trade_up_rate)}</span>
              </Row>
              <Row label="Trade down">
                <span className="font-mono">{fmtPct(data.trade_behavior?.trade_down_rate)}</span>
              </Row>
              {hardConstraints.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {hardConstraints.map((c: string) => (
                    <span
                      key={c}
                      className="badge border-tier-low/40 bg-tier-low/10 text-tier-low"
                    >
                      {c.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </InfoCard>
        </div>
      )}

      {tab === 'needs' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <InfoCard title="Roster needs" Icon={Target}>
            <div className="space-y-2">
              {Object.entries(data.roster_needs ?? {})
                .sort((a: any, b: any) => b[1] - a[1])
                .map(([pos, score]: any) => (
                <div key={pos} className="flex items-center gap-3 text-sm">
                  <div className="w-12 font-mono text-text-muted">{pos}</div>
                  <div className="flex-1 h-2 bg-bg-raised rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-accent/60 to-accent"
                      style={{ width: `${Math.min(100, (score / 5) * 100)}%` }}
                    />
                  </div>
                  <div className="font-mono tabular-nums text-text w-10 text-right">
                    {Number(score).toFixed(1)}
                  </div>
                </div>
              ))}
            </div>
            {Object.keys(data.latent_needs ?? {}).length > 0 && (
              <>
                <div className="mt-4 mb-1 text-xs uppercase tracking-wide text-text-muted">
                  Latent (2027+ cliff)
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {Object.entries(data.latent_needs).map(([pos, score]: any) => (
                    <span
                      key={pos}
                      className="badge border-border text-text-muted"
                    >
                      {pos} · {Number(score).toFixed(1)}
                    </span>
                  ))}
                </div>
              </>
            )}
          </InfoCard>

          <InfoCard title="Roster needs (tiered, from PDF)" Icon={Target}>
            <pre className="text-xs text-text whitespace-pre-wrap leading-5 font-sans">
              {narrative.roster_needs_tiered || '—'}
            </pre>
          </InfoCard>

          {Object.entries(archetypes).map(([pick, txt]: any) => (
            <InfoCard key={pick} title={`Archetype at #${pick}`} Icon={Target}>
              <p className="text-sm text-text leading-6">{txt}</p>
            </InfoCard>
          ))}
        </div>
      )}

      {tab === 'roster' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <InfoCard title={`Age cliffs (${cliffs.length})`} Icon={AlertOctagon}>
            {cliffs.length === 0 ? (
              <div className="text-sm text-text-subtle">No starters past their age threshold.</div>
            ) : (
              <ul className="text-sm space-y-1.5">
                {cliffs.map((c: any, i: number) => (
                  <li key={i} className="flex items-center justify-between">
                    <span>
                      <span className="font-medium">{c.player}</span>{' '}
                      <span className="text-text-muted">{c.position}</span>
                    </span>
                    <span className={cn(
                      'font-mono tabular-nums',
                      c.severity === 'high' ? 'text-tier-low' : 'text-tier-midlo',
                    )}>
                      {c.age_2026}yo
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </InfoCard>

          <InfoCard title="Injury flags" Icon={AlertOctagon}>
            {inj.length === 0 ? (
              <div className="text-sm text-text-subtle">No injury signals.</div>
            ) : (
              <ul className="text-sm space-y-2">
                {inj.map((i: any, idx: number) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className={cn(
                      'badge flex-none',
                      i.severity === 'high' ? 'border-tier-low/40 bg-tier-low/10 text-tier-low'
                      : i.severity === 'medium' ? 'border-tier-midlo/40 bg-tier-midlo/10 text-tier-midlo'
                      : 'border-border text-text-muted',
                    )}>
                      {i.severity}
                    </span>
                    <span className="text-text">
                      <span className="font-medium">{i.player}</span>
                      <span className="text-text-muted"> — {i.injury}</span>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </InfoCard>

          <InfoCard title="Cap context" Icon={DollarSign} tip={GLOSSARY.cap}>
            <div className="text-sm space-y-1">
              <Row label="Tier">
                <span className="capitalize">{cap.constraint_tier}</span>
              </Row>
              <Row label="Cap space">
                <span className="font-mono">
                  {cap.cap_space_m != null ? `$${cap.cap_space_m}M` : '—'}
                </span>
              </Row>
              <Row label="Dead cap">
                <span className="font-mono">
                  {cap.dead_cap_m != null ? `$${cap.dead_cap_m}M` : '—'}
                </span>
              </Row>
            </div>
            {cap.notes && (
              <div className="mt-2 text-xs text-text-muted italic">{cap.notes}</div>
            )}
          </InfoCard>

          <InfoCard title="Coaching tree" Icon={GraduationCap}>
            <div className="text-sm space-y-1">
              <Row label="HC tree">
                <span className="font-mono">{coaching.hc_tree || '—'}</span>
              </Row>
              <Row label="College stints">
                <span className="text-right">
                  {(coaching.hc_college_stints ?? []).join(', ') || '—'}
                </span>
              </Row>
            </div>
          </InfoCard>

          <InfoCard title="Previous-year R1/R2 allocation" Icon={TrendingUp}>
            {Object.keys(prevAlloc).length === 0 ? (
              <div className="text-sm text-text-subtle">No prior-year data.</div>
            ) : (
              <div className="space-y-1 text-sm">
                {['2025_r1', '2025_r2', '2024_r1', '2024_r2'].map((k) => {
                  const picks = prevAlloc[k] ?? [];
                  if (picks.length === 0) return null;
                  return (
                    <Row key={k} label={k.replace('_', ' R').toUpperCase()}>
                      <span className="font-mono text-xs">
                        {picks.map((p: any) => `${p.pos}#${p.pick}`).join(', ')}
                      </span>
                    </Row>
                  );
                })}
              </div>
            )}
          </InfoCard>

          <InfoCard title="FA moves" Icon={Users}>
            <div className="text-sm">
              <div className="text-xs uppercase tracking-wide text-text-muted">
                Arrivals
              </div>
              <ul className="mt-1 mb-3 space-y-0.5">
                {(data.fa_moves?.arrivals ?? []).map((a: string, i: number) => (
                  <li key={i} className="text-tier-high/80 text-xs">+ {a}</li>
                ))}
                {(data.fa_moves?.arrivals ?? []).length === 0 && (
                  <li className="text-text-subtle text-xs">—</li>
                )}
              </ul>
              <div className="text-xs uppercase tracking-wide text-text-muted">
                Departures
              </div>
              <ul className="mt-1 space-y-0.5">
                {(data.fa_moves?.departures ?? []).map((d: string, i: number) => (
                  <li key={i} className="text-tier-low/80 text-xs">− {d}</li>
                ))}
                {(data.fa_moves?.departures ?? []).length === 0 && (
                  <li className="text-text-subtle text-xs">—</li>
                )}
              </ul>
            </div>
          </InfoCard>
        </div>
      )}

      {tab === 'narrative' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <NarrativeBlock title="Leadership" text={narrative.leadership} />
          <NarrativeBlock title="Offseason moves" text={narrative.offseason_moves} />
          <NarrativeBlock title="Scheme identity" text={narrative.scheme_identity} />
          <NarrativeBlock title="Roster needs (tiered)" text={narrative.roster_needs_tiered} />
          <NarrativeBlock title="GM fingerprint" text={narrative.gm_fingerprint} />
          <NarrativeBlock title="Uncertainty flags" text={narrative.uncertainty_flags} />
          {narrative.predictability_tier && (
            <NarrativeBlock title="Predictability tier" text={narrative.predictability_tier} />
          )}
          {narrative.trade_up_scenario && (
            <NarrativeBlock title="Trade-up scenario" text={narrative.trade_up_scenario} />
          )}
          {narrative.cascade_rule && (
            <NarrativeBlock title="Cascade" text={narrative.cascade_rule} />
          )}
          {Object.entries(archetypes).map(([pick, txt]: any) => (
            <NarrativeBlock key={pick} title={`Archetype at #${pick}`} text={txt} />
          ))}
        </div>
      )}

      {tab === 'intel' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <InfoCard title={`Confirmed visits (${data.visit_signals?.n_confirmed ?? 0})`} Icon={Users}>
            <div className="flex flex-wrap gap-1.5">
              {(data.visit_signals?.confirmed_visits ?? []).map((p: string) => (
                <span key={p} className="badge border-border text-text">
                  {p}
                </span>
              ))}
              {(data.visit_signals?.confirmed_visits ?? []).length === 0 && (
                <div className="text-sm text-text-subtle">No confirmed visits.</div>
              )}
            </div>
          </InfoCard>

          <InfoCard title="GM affinity (vs. league avg)" Icon={TrendingUp}>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
              {Object.entries(data.gm_affinity ?? {})
                .sort((a: any, b: any) => b[1] - a[1])
                .map(([pos, delta]: any) => (
                <div key={pos} className="flex items-center justify-between">
                  <span className="font-mono text-text-muted">{pos}</span>
                  <span className={cn(
                    'font-mono tabular-nums text-xs',
                    delta > 0 ? 'text-tier-high' : delta < -0.02 ? 'text-tier-low' : 'text-text-subtle',
                  )}>
                    {delta > 0 ? '+' : ''}{(delta * 100).toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          </InfoCard>
        </div>
      )}
    </div>
  );
}

function InfoCard({
  title, Icon, children, tip,
}: {
  title: string;
  Icon?: React.ComponentType<{ size?: number; className?: string }>;
  children: React.ReactNode;
  tip?: string;
}) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-text-muted mb-3">
        {Icon && <Icon size={13} />}
        {title}
        {tip && <Tooltip text={tip} />}
      </div>
      {children}
    </div>
  );
}

function NarrativeBlock({ title, text }: { title: string; text?: string }) {
  if (!text) return null;
  return (
    <div className="card p-4">
      <div className="text-xs uppercase tracking-wide text-text-muted mb-2">{title}</div>
      <p className="text-sm text-text leading-6 whitespace-pre-wrap">{text}</p>
    </div>
  );
}

function Row({
  label, children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-text-muted">{label}</span>
      <span>{children}</span>
    </div>
  );
}
