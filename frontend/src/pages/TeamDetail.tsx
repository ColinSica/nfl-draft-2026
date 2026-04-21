/**
 * Team detail — answers "what will this team do, and why?"
 * Structure: Summary / Why / Need stack / Trade behavior / Intel / Signals.
 */
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { api } from '../lib/api';
import { teamColor } from '../lib/teamColors';
import { HRule, SectionHeader, SmallCaps, MissingText } from '../components/editorial';
import {
  displayValue, displayQbUrgency, displayQbSituation, displayCapTier,
  displayPredictability,
} from '../lib/display';

export function TeamDetail() {
  const { abbr } = useParams<{ abbr: string }>();
  const [data, setData] = useState<any>(null);
  const [reasoning, setReasoning] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!abbr) return;
    api.team(abbr).then(setData).catch((e) => setErr(String(e)));
    fetch('/api/simulations/reasoning').then(r => r.json()).then(setReasoning).catch(() => {});
  }, [abbr]);

  if (err) {
    return (
      <div className="card p-8 text-center">
        <p className="text-live">Couldn't load team data.</p>
        <p className="text-ink-soft text-sm mt-2">{err}</p>
      </div>
    );
  }
  if (!data) return <div className="text-ink-soft italic">Loading {abbr}…</div>;

  const tc = teamColor(data.team);
  const needs: [string, number][] = Object.entries(data.roster_needs ?? {})
    .map(([p, w]) => [p, Number(w)] as [string, number])
    .sort((a, b) => b[1] - a[1]);

  const tradeBehavior = data.trade_behavior ?? {};
  const scheme = data.scheme ?? {};
  const capCtx = data.cap_context ?? {};
  const coaching = data.coaching ?? {};
  const visits = (data.visit_signals?.confirmed_visits ?? []) as any[];
  // Find the most recent _MM_DD_news field (data is dated per source refresh)
  const latestNews = (() => {
    const newsKeys = Object.keys(data)
      .filter(k => /^_\d+_\d+_news$/.test(k))
      .sort();  // date suffix sorts lexicographically
    const latest = newsKeys[newsKeys.length - 1];
    return latest ? (data as any)[latest] : null;
  })();
  const firstPick = data.r1_picks?.[0] ?? data.pick;
  const modelPick = firstPick && reasoning?.picks?.[String(firstPick)];

  return (
    <div className="space-y-12 pb-16">
      <div>
        <Link
          to="/teams"
          className="inline-flex items-center gap-1.5 caps-tight text-ink-soft hover:text-ink mb-3"
        >
          <ArrowLeft size={13} /> All teams
        </Link>

        <div
          className="card overflow-hidden relative"
          style={{ borderLeft: `4px solid ${tc.primary}` }}
        >
          <div
            className="px-6 py-7 flex items-start justify-between gap-5 flex-wrap"
            style={{ background: `linear-gradient(90deg, ${tc.primary}12 0%, transparent 45%)` }}
          >
            <div className="flex items-center gap-4">
              <span
                className="display-broadcast text-3xl w-16 h-16 flex items-center justify-center shrink-0"
                style={{
                  background: tc.primary,
                  color: tc.secondary === '#000000' ? '#FFFFFF' : tc.secondary,
                }}
              >
                {data.team}
              </span>
              <div>
                <h1 className="display-broadcast text-5xl md:text-6xl leading-[0.85] text-ink">
                  {tc.name}
                </h1>
                <div className="mt-2 text-sm text-ink-soft">
                  {displayValue(coaching.hc, 'HC —')} · {displayValue(data.gm, 'GM —')}
                  {coaching.hc_tree && (
                    <span className="ml-2 text-ink-soft/70 font-mono text-xs">
                      {coaching.hc_tree} tree
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="text-right">
              {data.r1_picks?.length ? (
                <>
                  <div className="caps-tight text-ink-soft">R1 picks</div>
                  <div
                    className="display-num text-5xl leading-none"
                    style={{ color: tc.primary }}
                  >
                    {data.r1_picks.join(' · ')}
                  </div>
                </>
              ) : (
                <span className="badge">No R1</span>
              )}
              <div className="caps-tight text-ink-soft mt-1 text-[0.65rem]">
                {data.total_picks ?? '—'} total picks
              </div>
            </div>
          </div>
        </div>
      </div>

      <section>
        <SectionHeader number={1} kicker="Summary" title="At a glance." />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-0 mt-8 border border-ink-edge bg-paper-surface">
          <SummaryTile label="Predictability" value={displayPredictability(data.predictability)} accent={tc.primary} />
          <SummaryTile label="QB situation" value={displayQbSituation(data.qb_situation)} sub={displayQbUrgency(data.qb_urgency)} />
          <SummaryTile label="Cap posture" value={displayCapTier(capCtx.cap_tier ?? data.cap_tier)} />
          <SummaryTile label="Scheme" value={displayValue(scheme.type ?? scheme.base, 'Unclear')} />
        </div>
        {latestNews && (
          <div className="mt-4 p-4 border border-ink-edge" style={{ background: 'rgba(217,164,0,0.08)' }}>
            <div className="flex items-start gap-2">
              <SmallCaps tight className="shrink-0 mt-0.5" style={{ color: '#D9A400' }}>Latest intel</SmallCaps>
              <p className="text-sm text-ink leading-relaxed">{latestNews}</p>
            </div>
          </div>
        )}
      </section>

      {modelPick && (
        <section>
          <SectionHeader number={2} kicker="Why" title={`Pick ${firstPick}: the model's choice.`} />
          <article className="mt-8 card">
            <div className="h-1" style={{ background: tc.primary }} />
            <div className="p-6 space-y-4">
              <div className="flex items-baseline justify-between gap-3 flex-wrap">
                <h3 className="display-broadcast text-4xl md:text-5xl leading-[0.9] text-ink">
                  {modelPick.player?.toUpperCase()}
                </h3>
                <div className="flex items-center gap-2 font-mono text-sm">
                  <span className="px-2 py-0.5 bg-ink text-paper font-bold text-xs">
                    {modelPick.position}
                  </span>
                  {modelPick.probability !== undefined && (
                    <span className="caps-tight text-ink-soft">
                      {Math.round(modelPick.probability * 100)}% of sims
                    </span>
                  )}
                </div>
              </div>
              <HRule />
              {modelPick.reasoning_summary ? (
                <p className="text-ink leading-relaxed">
                  <span className="caps-tight mr-2" style={{ color: tc.primary }}>Why</span>
                  {modelPick.reasoning_summary}
                </p>
              ) : (
                <MissingText>No reasoning summary for this slot.</MissingText>
              )}
              {modelPick.top_factors && Array.isArray(modelPick.top_factors) && modelPick.top_factors.length > 0 && (
                <div>
                  <SmallCaps tight className="text-ink-soft block mb-2">Top contributing factors</SmallCaps>
                  <ul className="space-y-1.5 text-sm text-ink-soft">
                    {modelPick.top_factors.slice(0, 5).map((f: any, i: number) => (
                      <li key={i} className="flex items-baseline gap-2">
                        <span className="font-mono text-xs text-ink-soft/70">
                          {typeof f === 'object' && f.weight !== undefined
                            ? `+${Number(f.weight).toFixed(2)}`
                            : '·'}
                        </span>
                        <span>{typeof f === 'object' ? (f.label ?? f.factor ?? '') : String(f)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </article>
        </section>
      )}

      <section>
        <SectionHeader number={3} kicker="Need stack" title="What they're looking for." />
        <div className="mt-8 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
          {needs.length === 0 ? (
            <MissingText>No need data.</MissingText>
          ) : (
            needs.slice(0, 10).map(([pos, w]) => (
              <div key={pos} className="card p-4 space-y-1.5">
                <div className="display-broadcast text-2xl leading-none text-ink">{pos}</div>
                <div className="w-full h-1.5 bg-ink-edge relative overflow-hidden">
                  <div
                    className="absolute inset-y-0 left-0"
                    style={{
                      width: `${Math.min(100, (w / 5) * 100)}%`,
                      background: w >= 4 ? tc.primary : w >= 2.5 ? '#D9A400' : '#848B98',
                    }}
                  />
                </div>
                <div className="text-xs font-mono text-ink-soft">weight {w.toFixed(1)}</div>
              </div>
            ))
          )}
        </div>
      </section>

      <section>
        <SectionHeader number={4} kicker="Trade behavior" title="How aggressive they are." />
        <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-0 border border-ink-edge bg-paper-surface">
          <TradeTile
            label="Trade-up rate"
            value={tradeBehavior.trade_up_rate ?? data.trade_up_rate}
            note="Historical prob this GM moves up"
            accent="#1F6FEB"
          />
          <TradeTile
            label="Trade-down rate"
            value={tradeBehavior.trade_down_rate ?? data.trade_down_rate}
            note="Historical prob this GM moves back"
            accent="#17A870"
            border
          />
        </div>
        {tradeBehavior.pdf_tier?.reason && (
          <p className="mt-4 text-sm text-ink-soft italic">{tradeBehavior.pdf_tier.reason}</p>
        )}
      </section>

      <section>
        <SectionHeader number={5} kicker="Intel" title="Visits, news, signals." />
        <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-5">
          <div className="card">
            <header className="px-5 py-3 border-b border-ink-edge">
              <SmallCaps className="text-ink">Confirmed visits ({visits.length})</SmallCaps>
            </header>
            <div className="p-5">
              {visits.length === 0 ? (
                <MissingText>No confirmed visits logged.</MissingText>
              ) : (
                <ul className="space-y-2 text-sm">
                  {visits.slice(0, 12).map((v: any, i: number) => (
                    <li key={i} className="flex items-baseline justify-between gap-3 border-b border-ink-edge pb-2 last:border-b-0 last:pb-0">
                      <span className="text-ink">{displayValue(v.player ?? v, 'Unknown')}</span>
                      <span className="font-mono text-xs text-ink-soft">
                        {displayValue(v.position, '')} {v.source ? `· ${v.source}` : ''}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div className="card">
            <header className="px-5 py-3 border-b border-ink-edge">
              <SmallCaps className="text-ink">GM affinity</SmallCaps>
            </header>
            <div className="p-5">
              {data.gm_affinity && Object.keys(data.gm_affinity).length > 0 ? (
                <div className="space-y-2 text-sm">
                  {Object.entries(data.gm_affinity)
                    .sort((a: any, b: any) => Math.abs(Number(b[1])) - Math.abs(Number(a[1])))
                    .slice(0, 8)
                    .map(([pos, raw]: any) => (
                      <div key={pos} className="flex items-center justify-between border-b border-ink-edge pb-2 last:border-b-0 last:pb-0">
                        <span className="caps-tight text-ink">{pos}</span>
                        <span
                          className="font-mono text-xs font-bold"
                          style={{
                            color: Number(raw) > 0 ? '#17A870' : Number(raw) < 0 ? '#DC2F3D' : '#848B98',
                          }}
                        >
                          {Number(raw) > 0 ? '+' : ''}{Number(raw).toFixed(2)}
                        </span>
                      </div>
                    ))}
                </div>
              ) : (
                <MissingText>No GM affinity signals.</MissingText>
              )}
            </div>
          </div>
        </div>
      </section>

      <section>
        <SectionHeader number={6} kicker="Signals" title="Underneath the pick." />
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          <SignalCard title="Coaching">
            <SignalRow label="HC" value={coaching.hc} />
            <SignalRow label="OC" value={coaching.oc} />
            <SignalRow label="DC" value={coaching.dc} />
            <SignalRow label="Tree" value={coaching.hc_tree} />
          </SignalCard>
          <SignalCard title="Scheme">
            <SignalRow label="Base" value={scheme.type ?? scheme.base} />
            <SignalRow
              label="Premium"
              value={Array.isArray(scheme.premium) ? scheme.premium.join(' · ') : scheme.premium}
            />
          </SignalCard>
          <SignalCard title="Capital">
            <SignalRow label="Cap tier" value={displayCapTier(capCtx.cap_tier ?? data.cap_tier)} />
            <SignalRow label="Capital" value={data.draft_capital?.capital_abundance} />
            <SignalRow label="Total picks" value={data.total_picks} />
          </SignalCard>
        </div>
      </section>
    </div>
  );
}

function SummaryTile({
  label, value, sub, accent,
}: {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  accent?: string;
}) {
  return (
    <div className="p-5 border-b md:border-b-0 md:border-r border-ink-edge last:border-r-0">
      <SmallCaps tight className="text-ink-soft block">{label}</SmallCaps>
      <div
        className="display-broadcast text-xl md:text-2xl leading-[1.05] mt-1 text-ink"
        style={accent ? { color: accent } : undefined}
      >
        {value}
      </div>
      {sub && <div className="text-xs text-ink-soft mt-0.5">{sub}</div>}
    </div>
  );
}

function TradeTile({
  label, value, note, accent, border,
}: {
  label: string;
  value: number | null | undefined;
  note: string;
  accent: string;
  border?: boolean;
}) {
  const pct = (value !== null && value !== undefined)
    ? `${Math.round(Number(value) * 100)}%`
    : '—';
  return (
    <div className={`p-6 ${border ? 'border-l border-ink-edge' : ''}`}>
      <SmallCaps tight className="text-ink-soft block">{label}</SmallCaps>
      <div className="display-num text-5xl md:text-6xl mt-2" style={{ color: accent }}>
        {pct}
      </div>
      <div className="text-xs text-ink-soft/80 mt-1">{note}</div>
    </div>
  );
}

function SignalCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card">
      <header className="px-4 py-2.5 border-b border-ink-edge">
        <SmallCaps className="text-ink">{title}</SmallCaps>
      </header>
      <div className="p-4 space-y-2">{children}</div>
    </div>
  );
}

function SignalRow({ label, value }: { label: string; value: any }) {
  const display = value === null || value === undefined || value === ''
    ? <MissingText />
    : String(value);
  return (
    <div className="flex items-baseline justify-between gap-3 text-sm">
      <SmallCaps tight className="text-ink-soft shrink-0">{label}</SmallCaps>
      <span className="text-right text-ink">{display}</span>
    </div>
  );
}
