/**
 * Team Detail — full team dossier.
 *
 * Structure:
 *   1. Masthead (name, brass stripe, GM/HC, R1 picks)
 *   2. At-a-glance tiles (predictability, QB, cap, scheme)
 *   3. Latest intel + 4/21 pressers
 *   4. Model's pick reasoning
 *   5. Narrative dossier (gm fingerprint, context, scheme identity)
 *   6. Need stack + tiered needs narrative
 *   7. Roster context (age cliffs, previous R1, FA moves)
 *   8. QB situation (status, urgency, narrative)
 *   9. Trade behavior + propensity tier
 *  10. Intel — visits, GM affinity, player archetypes
 *  11. Signals panel (coaching, scheme, capital)
 */
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { api } from '../lib/api';
import { teamColor } from '../lib/teamColors';
import { HRule, SectionHeader, SmallCaps, MissingText, Stamp, Footnote } from '../components/editorial';
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
        <p className="text-ink-muted text-sm mt-2">{err}</p>
      </div>
    );
  }
  if (!data) return <div className="text-ink-muted italic">Loading {abbr}…</div>;

  const tc = teamColor(data.team);
  const needs: [string, number][] = Object.entries(data.roster_needs ?? {})
    .map(([p, w]) => [p, Number(w)] as [string, number])
    .filter(([, w]) => w > 0)
    .sort((a, b) => b[1] - a[1]);

  const tradeBehavior = data.trade_behavior ?? {};
  const scheme = data.scheme ?? {};
  const capCtx = data.cap_context ?? {};
  const coaching = data.coaching ?? {};
  const visits = (data.visit_signals?.confirmed_visits ?? []) as any[];
  const narrative = data.narrative ?? {};
  const rosterContext = data.roster_context ?? {};
  const ageCliffs = (rosterContext.age_cliffs ?? []) as any[];
  const prevAllocation = rosterContext.previous_year_allocation ?? {};
  const faArrivals = (data.fa_moves?.arrivals ?? []) as any[];
  const faDepartures = (data.fa_moves?.departures ?? []) as any[];

  // Gather all dated news/pressers arrays, find the freshest.
  const allDatedEntries = Object.entries(data as any)
    .filter(([k]) => /^_\d+_\d+_(news|pressers)$/.test(k))
    .sort(([a], [b]) => (a as string).localeCompare(b as string));
  const latestNews = (() => {
    const newsEntry = [...allDatedEntries].reverse().find(([k]) => (k as string).endsWith('_news'));
    return newsEntry ? (newsEntry[1] as any) : null;
  })();
  const latestPressers = (() => {
    const p = [...allDatedEntries].reverse().find(([k]) => (k as string).endsWith('_pressers'));
    return p ? (p[1] as any) : null;
  })();

  const firstPick = data.r1_picks?.[0] ?? data.pick;
  const modelPick = firstPick && reasoning?.picks?.[String(firstPick)];
  const playerArchetypes = (narrative.player_archetypes ?? {}) as Record<string, string>;

  return (
    <div className="space-y-12 pb-16">
      {/* Back link */}
      <div>
        <Link
          to="/teams"
          className="inline-flex items-center gap-1.5 caps-tight text-ink-muted hover:text-ink mb-3"
        >
          <ArrowLeft size={13} /> All teams
        </Link>

        {/* ──────── Masthead ──────── */}
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
                <h1 className="display-jumbo text-ink"
                    style={{ fontSize: 'clamp(2rem, 5vw, 3.5rem)' }}>
                  {tc.name}
                </h1>
                <div className="mt-2 text-sm text-ink-soft flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <span><strong className="text-ink">{displayValue(coaching.hc, '—')}</strong>
                    <span className="text-ink-muted ml-1">HC</span></span>
                  <span className="text-ink-edge">·</span>
                  <span><strong className="text-ink">{displayValue(data.gm, '—')}</strong>
                    <span className="text-ink-muted ml-1">GM</span></span>
                  {coaching.hc_tree && (
                    <>
                      <span className="text-ink-edge">·</span>
                      <span className="font-mono text-xs text-ink-muted">{coaching.hc_tree} tree</span>
                    </>
                  )}
                  {(data.new_hc || data.new_gm) && (
                    <Stamp variant="brass">
                      {data.new_hc && data.new_gm ? 'New HC + GM' : data.new_hc ? 'New HC' : 'New GM'}
                    </Stamp>
                  )}
                </div>
              </div>
            </div>

            <div className="text-right">
              {data.r1_picks?.length ? (
                <>
                  <div className="caps-tight text-ink-muted">R1 picks</div>
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
              <div className="caps-tight text-ink-muted mt-1 text-[0.65rem]">
                {data.total_picks ?? '—'} total · {data.draft_capital?.capital_abundance ?? 'normal'} capital
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ──────── § 1 At a glance ──────── */}
      <section>
        <SectionHeader number={1} kicker="At a glance" title="Front-office vitals." />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-0 mt-6 border border-ink-edge bg-paper-surface">
          <SummaryTile label="Predictability" value={displayPredictability(data.predictability)}
                       sub={narrative.predictability_tier} accent={tc.primary} />
          <SummaryTile label="QB situation" value={displayQbSituation(data.qb_situation)}
                       sub={displayQbUrgency(data.qb_urgency)} />
          <SummaryTile label="Cap posture" value={displayCapTier(capCtx.cap_tier ?? data.cap_tier)}
                       sub={capCtx.constraint_tier} />
          <SummaryTile label="Scheme" value={displayValue(scheme.type ?? scheme.base, 'Unclear')}
                       sub={Array.isArray(scheme.premium) ? scheme.premium.slice(0,3).join(' · ') : undefined} />
        </div>

        {(latestNews || latestPressers) && (
          <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-0 border border-ink-edge bg-paper-raised">
            {latestNews && (
              <div className="p-5 md:border-r border-ink-edge">
                <SmallCaps tight>Latest intel</SmallCaps>
                <p className="mt-2 body-serif text-sm text-ink leading-relaxed">
                  {renderArrayOrString(latestNews)}
                </p>
              </div>
            )}
            {latestPressers && (
              <div className="p-5">
                <SmallCaps tight>Pre-draft pressers</SmallCaps>
                <p className="mt-2 body-serif text-sm text-ink leading-relaxed">
                  {renderArrayOrString(latestPressers)}
                </p>
              </div>
            )}
          </div>
        )}
      </section>

      {/* ──────── § 2 Model's pick ──────── */}
      {modelPick && (
        <section>
          <SectionHeader number={2} kicker="Model's pick"
                         title={`At pick ${firstPick}: ${modelPick.player ?? '—'}.`} />
          <article className="mt-6 card">
            <div className="h-1" style={{ background: tc.primary }} />
            <div className="p-6 space-y-4">
              <div className="flex items-baseline justify-between gap-3 flex-wrap">
                <h3 className="display-broadcast text-3xl md:text-4xl text-ink">
                  {modelPick.player}
                </h3>
                <div className="flex items-center gap-2 font-mono text-sm">
                  <span className="px-2 py-0.5 bg-ink text-paper text-xs font-bold">
                    {modelPick.position}
                  </span>
                  {modelPick.probability !== undefined && (
                    <span className="caps-tight text-ink-muted">
                      {Math.round(modelPick.probability * 100)}% modal
                    </span>
                  )}
                </div>
              </div>
              <HRule />
              {modelPick.reasoning_summary ? (
                <p className="body-serif text-ink leading-relaxed">
                  <span className="caps-tight mr-2" style={{ color: tc.primary }}>Why</span>
                  {modelPick.reasoning_summary}
                </p>
              ) : (
                <MissingText>No reasoning summary for this slot.</MissingText>
              )}
              {modelPick.top_factors && Array.isArray(modelPick.top_factors) && modelPick.top_factors.length > 0 && (
                <div>
                  <SmallCaps tight className="text-ink-muted block mb-2">Top contributing factors</SmallCaps>
                  <ul className="space-y-1.5 text-sm">
                    {modelPick.top_factors.slice(0, 6).map((f: any, i: number) => (
                      <li key={i} className="flex items-baseline gap-2">
                        <span className="font-mono text-xs text-ink-muted w-10 shrink-0">
                          {typeof f === 'object' && f.weight !== undefined
                            ? `+${Number(f.weight).toFixed(2)}`
                            : '·'}
                        </span>
                        <span className="flex-1 body-serif text-ink">
                          {typeof f === 'object' ? (f.label ?? f.factor ?? '') : String(f)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </article>
        </section>
      )}

      {/* ──────── § 3 Narrative dossier ──────── */}
      {(narrative.gm_fingerprint || narrative.context_2026 || narrative.scheme_identity ||
        narrative.offseason_moves || narrative.uncertainty_flags) && (
        <section>
          <SectionHeader number={3} kicker="Dossier"
                         title="Front-office fingerprint." />
          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-0 border border-ink-edge bg-paper-surface">
            <NarrativeBlock title="GM fingerprint"      body={narrative.gm_fingerprint} />
            <NarrativeBlock title="Scheme identity"    body={narrative.scheme_identity} border />
            <NarrativeBlock title="Context — 2026"     body={narrative.context_2026} />
            <NarrativeBlock title="Offseason moves"    body={narrative.offseason_moves} border />
            {narrative.uncertainty_flags && (
              <NarrativeBlock
                title="Uncertainty flags"
                body={narrative.uncertainty_flags}
                spanFull
                variant="warn"
              />
            )}
          </div>
        </section>
      )}

      {/* ──────── § 4 QB situation ──────── */}
      {(narrative.qb_situation || data.qb_urgency !== undefined) && (
        <section>
          <SectionHeader number={4} kicker="Quarterback" title="The position that decides the draft." />
          <div className="mt-6 card p-6 space-y-3">
            <div className="flex items-baseline gap-4 flex-wrap">
              <SmallCaps>Status</SmallCaps>
              <span className="display-broadcast text-xl text-ink">
                {displayQbSituation(data.qb_situation)}
              </span>
              <span className="text-ink-edge">·</span>
              <SmallCaps>Urgency</SmallCaps>
              <span className="display-num text-xl" style={{
                color: (data.qb_urgency ?? 0) >= 0.7 ? '#8C2E2A'
                     : (data.qb_urgency ?? 0) >= 0.4 ? '#B68A2F'
                     : '#3A6B46'
              }}>
                {((data.qb_urgency ?? 0) * 100).toFixed(0)} / 100
              </span>
            </div>
            {narrative.qb_situation && (
              <p className="body-serif text-ink leading-relaxed">
                {narrative.qb_situation}
              </p>
            )}
          </div>
        </section>
      )}

      {/* ──────── § 5 Need stack ──────── */}
      <section>
        <SectionHeader number={5} kicker="Need stack"
                       title="What they're looking for."
                       deck={narrative.roster_needs_tiered ? undefined : 'Positional need weights drive Stage 2 fit scores.'} />
        <div className="mt-6 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
          {needs.length === 0 ? (
            <MissingText>No active needs.</MissingText>
          ) : (
            needs.slice(0, 10).map(([pos, w]) => (
              <div key={pos} className="card p-4 space-y-1.5">
                <div className="display-broadcast text-2xl leading-none text-ink">{pos}</div>
                <div className="w-full h-1.5 bg-paper-hover relative overflow-hidden">
                  <div
                    className="absolute inset-y-0 left-0"
                    style={{
                      width: `${Math.min(100, (w / 5) * 100)}%`,
                      background: w >= 4 ? tc.primary : w >= 2.5 ? '#B68A2F' : '#6E6650',
                    }}
                  />
                </div>
                <div className="text-xs font-mono text-ink-muted">weight {w.toFixed(1)}</div>
              </div>
            ))
          )}
        </div>
        {narrative.roster_needs_tiered && (
          <div className="mt-5 p-5 border border-ink-edge bg-paper-raised">
            <SmallCaps tight className="block mb-2">Tiered analyst notes</SmallCaps>
            <p className="body-serif text-sm text-ink leading-relaxed whitespace-pre-line">
              {narrative.roster_needs_tiered}
            </p>
          </div>
        )}
      </section>

      {/* ──────── § 6 Roster context ──────── */}
      {(ageCliffs.length > 0 || faArrivals.length > 0 || faDepartures.length > 0 ||
        Object.keys(prevAllocation).length > 0) && (
        <section>
          <SectionHeader number={6} kicker="Roster context"
                         title="Why the needs look the way they do." />
          <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Age cliffs */}
            <div className="card">
              <header className="px-5 py-3 border-b border-ink-edge">
                <SmallCaps>Age cliffs · {ageCliffs.length}</SmallCaps>
              </header>
              <div className="p-5">
                {ageCliffs.length === 0 ? (
                  <MissingText>No major age cliffs flagged.</MissingText>
                ) : (
                  <ul className="space-y-2 text-sm">
                    {ageCliffs.slice(0, 10).map((c: any, i: number) => (
                      <li key={i} className="flex items-baseline justify-between gap-3 pb-2 border-b border-ink-edge last:border-b-0 last:pb-0">
                        <div>
                          <span className="text-ink">{c.player}</span>
                          <span className="font-mono text-xs text-ink-muted ml-2">{c.position}</span>
                        </div>
                        <div className="flex items-baseline gap-2">
                          <span className="font-mono text-xs text-ink-muted">age {c.age_2026}</span>
                          <span className={`caps-tight ${c.severity === 'high' ? 'text-signal-neg' : 'text-signal-warn'}`}>
                            {c.severity}
                          </span>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {/* Previous R1 allocation */}
            <div className="card">
              <header className="px-5 py-3 border-b border-ink-edge">
                <SmallCaps>Recent R1 history</SmallCaps>
              </header>
              <div className="p-5 space-y-3">
                {['2025_r1', '2024_r1'].map((year) => {
                  const entries = (prevAllocation[year] ?? []) as any[];
                  if (entries.length === 0) return null;
                  return (
                    <div key={year}>
                      <SmallCaps tight className="block mb-1">{year.replace('_', ' · ')}</SmallCaps>
                      <ul className="space-y-1 text-sm">
                        {entries.map((e: any, i: number) => (
                          <li key={i} className="flex items-baseline justify-between gap-3">
                            <span className="text-ink">{e.player ?? '—'}</span>
                            <span className="font-mono text-xs text-ink-muted">
                              {e.pos ?? e.position ?? ''} · pick {e.pick ?? '—'}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  );
                })}
                {Object.keys(prevAllocation).length === 0 && <MissingText>No prior-R1 history.</MissingText>}
              </div>
            </div>

            {/* FA arrivals */}
            <div className="card">
              <header className="px-5 py-3 border-b border-ink-edge bg-signal-pos/10">
                <SmallCaps>FA arrivals · {faArrivals.length}</SmallCaps>
              </header>
              <div className="p-5">
                {faArrivals.length === 0 ? (
                  <MissingText>No notable signings.</MissingText>
                ) : (
                  <ul className="space-y-1.5 text-sm body-serif text-ink">
                    {faArrivals.slice(0, 10).map((m: any, i: number) => (
                      <li key={i} className="flex gap-2">
                        <span className="text-signal-pos font-mono shrink-0">+</span>
                        <span>{typeof m === 'string' ? m : (m.player ?? m.name ?? JSON.stringify(m))}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            {/* FA departures */}
            <div className="card">
              <header className="px-5 py-3 border-b border-ink-edge bg-signal-neg/10">
                <SmallCaps>FA departures · {faDepartures.length}</SmallCaps>
              </header>
              <div className="p-5">
                {faDepartures.length === 0 ? (
                  <MissingText>No notable losses.</MissingText>
                ) : (
                  <ul className="space-y-1.5 text-sm body-serif text-ink">
                    {faDepartures.slice(0, 10).map((m: any, i: number) => (
                      <li key={i} className="flex gap-2">
                        <span className="text-signal-neg font-mono shrink-0">−</span>
                        <span>{typeof m === 'string' ? m : (m.player ?? m.name ?? JSON.stringify(m))}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* ──────── § 7 Trade behavior ──────── */}
      <section>
        <SectionHeader number={7} kicker="Trade behavior"
                       title="How aggressive the GM gets." />
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-0 border border-ink-edge bg-paper-surface">
          <TradeTile
            label="Trade-up rate"
            value={tradeBehavior.trade_up_rate ?? data.trade_up_rate}
            note="Historical prob this GM moves up"
          />
          <TradeTile
            label="Trade-down rate"
            value={tradeBehavior.trade_down_rate ?? data.trade_down_rate}
            note="Historical prob this GM moves back"
            border
          />
        </div>
        {(tradeBehavior.pdf_tier?.reason || narrative.trade_up_scenario || narrative.cascade_rule) && (
          <div className="mt-5 space-y-3">
            {tradeBehavior.pdf_tier?.tier && (
              <p className="body-serif text-sm text-ink-soft">
                <span className="caps-tight text-accent-brass mr-2">Tier</span>
                <strong className="text-ink">{tradeBehavior.pdf_tier.tier}</strong>
                {tradeBehavior.pdf_tier.reason && <> — {tradeBehavior.pdf_tier.reason}</>}
              </p>
            )}
            {narrative.trade_up_scenario && (
              <p className="body-serif text-sm text-ink-soft italic">
                <span className="caps-tight text-accent-brass mr-2 not-italic">Scenario</span>
                {narrative.trade_up_scenario}
              </p>
            )}
            {narrative.cascade_rule && (
              <p className="body-serif text-sm text-ink-soft italic">
                <span className="caps-tight text-accent-brass mr-2 not-italic">Cascade rule</span>
                {narrative.cascade_rule}
              </p>
            )}
          </div>
        )}
      </section>

      {/* ──────── § 8 Intel ──────── */}
      <section>
        <SectionHeader number={8} kicker="Intel"
                       title="Visits, GM affinity, archetypes." />
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Confirmed visits */}
          <div className="card">
            <header className="px-5 py-3 border-b border-ink-edge">
              <SmallCaps>Confirmed visits · {visits.length}</SmallCaps>
            </header>
            <div className="p-5">
              {visits.length === 0 ? (
                <MissingText>No confirmed visits logged.</MissingText>
              ) : (
                <ul className="space-y-2 text-sm">
                  {visits.slice(0, 12).map((v: any, i: number) => (
                    <li key={i} className="flex items-baseline justify-between gap-3 pb-2 border-b border-ink-edge last:border-b-0 last:pb-0">
                      <span className="text-ink">
                        {typeof v === 'string' ? v : displayValue(v.player ?? v, 'Unknown')}
                      </span>
                      {typeof v === 'object' && (v.position || v.source) && (
                        <span className="font-mono text-xs text-ink-muted">
                          {displayValue(v.position, '')} {v.source ? `· ${v.source}` : ''}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* GM affinity */}
          <div className="card">
            <header className="px-5 py-3 border-b border-ink-edge">
              <SmallCaps>GM positional affinity</SmallCaps>
            </header>
            <div className="p-5">
              {data.gm_affinity && Object.keys(data.gm_affinity).length > 0 ? (
                <div className="space-y-2 text-sm">
                  {Object.entries(data.gm_affinity)
                    .sort((a: any, b: any) => Math.abs(Number(b[1])) - Math.abs(Number(a[1])))
                    .slice(0, 10)
                    .map(([pos, raw]: any) => {
                      const v = Number(raw);
                      return (
                        <div key={pos} className="flex items-center justify-between pb-2 border-b border-ink-edge last:border-b-0 last:pb-0">
                          <span className="caps-tight text-ink">{pos}</span>
                          <div className="flex items-center gap-2">
                            <div className="w-16 h-1 bg-paper-hover relative">
                              <div
                                className="absolute top-0 bottom-0"
                                style={{
                                  width: `${Math.min(100, Math.abs(v) * 100)}%`,
                                  left: v >= 0 ? '50%' : `${50 - Math.min(50, Math.abs(v) * 50)}%`,
                                  background: v >= 0 ? '#3A6B46' : '#8C2E2A',
                                }}
                              />
                              <div className="absolute top-0 bottom-0 left-1/2 w-px bg-ink-edge" />
                            </div>
                            <span
                              className="font-mono text-xs font-medium w-10 text-right"
                              style={{ color: v > 0 ? '#3A6B46' : v < 0 ? '#8C2E2A' : '#6E6650' }}
                            >
                              {v > 0 ? '+' : ''}{v.toFixed(2)}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                </div>
              ) : (
                <MissingText>No GM affinity signals.</MissingText>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ──────── § 9 Player archetypes — analyst-tagged names ──────── */}
      {Object.keys(playerArchetypes).length > 0 && (
        <section>
          <SectionHeader number={9} kicker="Archetypes"
                         title="Prospects flagged by slot in team research." />
          <div className="mt-6 card">
            <div className="p-5 space-y-3">
              {Object.entries(playerArchetypes).slice(0, 8).map(([slot, text]) => (
                <div key={slot} className="flex gap-3 pb-3 border-b border-ink-edge last:border-b-0 last:pb-0">
                  <span className="display-num text-sm text-accent-brass shrink-0 w-8">
                    § {String(slot).padStart(2, '0')}
                  </span>
                  <p className="body-serif text-sm text-ink leading-relaxed flex-1">{text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ──────── § 10 Signals panel ──────── */}
      <section>
        <SectionHeader number={10} kicker="Signals"
                       title="The parameters feeding Stage 2." />
        <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
          <SignalCard title="Coaching">
            <SignalRow label="HC" value={coaching.hc} />
            <SignalRow label="OC" value={coaching.oc} />
            <SignalRow label="DC" value={coaching.dc} />
            <SignalRow label="Tree" value={coaching.hc_tree} />
            {coaching.hc_college_stints && coaching.hc_college_stints.length > 0 && (
              <SignalRow label="College" value={coaching.hc_college_stints.join(', ')} />
            )}
          </SignalCard>
          <SignalCard title="Scheme">
            <SignalRow label="Base" value={scheme.type ?? scheme.base} />
            <SignalRow
              label="Premium"
              value={Array.isArray(scheme.premium) ? scheme.premium.join(' · ') : scheme.premium}
            />
            {data.scheme_archetype_tags && Array.isArray(data.scheme_archetype_tags) && (
              <SignalRow label="Archetypes" value={data.scheme_archetype_tags.join(', ')} />
            )}
          </SignalCard>
          <SignalCard title="Capital">
            <SignalRow label="Cap tier" value={displayCapTier(capCtx.cap_tier ?? data.cap_tier)} />
            <SignalRow label="Constraint" value={capCtx.constraint_tier} />
            <SignalRow label="Capital" value={data.draft_capital?.capital_abundance} />
            <SignalRow label="Total picks" value={data.total_picks} />
            <SignalRow label="Win %" value={data.win_pct?.toFixed(3)} />
          </SignalCard>
        </div>
      </section>

      {/* Footer note */}
      <section className="border-t-2 border-ink pt-5">
        <Footnote>
          Team profile compiled from: roster rooms (post-FA), public team-visit reporting,
          GM draft history 2019–2025, scheme / coaching-tree taxonomy, cap-space model,
          and PDF-parsed team briefings (4/21/26 refresh).
        </Footnote>
      </section>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────

function renderArrayOrString(val: any): string {
  if (!val) return '';
  if (Array.isArray(val)) return val.join(' · ');
  return String(val);
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
      <SmallCaps tight className="text-ink-muted block">{label}</SmallCaps>
      <div
        className="display-broadcast text-xl md:text-2xl leading-[1.05] mt-1 text-ink"
        style={accent ? { color: accent } : undefined}
      >
        {value}
      </div>
      {sub && <div className="text-xs text-ink-muted mt-0.5">{String(sub)}</div>}
    </div>
  );
}

function TradeTile({
  label, value, note, border,
}: {
  label: string;
  value: number | null | undefined;
  note: string;
  border?: boolean;
}) {
  const pct = (value !== null && value !== undefined)
    ? `${Math.round(Number(value) * 100)}%`
    : '—';
  return (
    <div className={`p-6 ${border ? 'border-l border-ink-edge' : ''}`}>
      <SmallCaps tight className="text-ink-muted block">{label}</SmallCaps>
      <div className="display-num text-5xl md:text-6xl mt-2 text-ink">{pct}</div>
      <div className="text-xs text-ink-muted mt-1">{note}</div>
    </div>
  );
}

function NarrativeBlock({
  title, body, border = false, spanFull = false, variant,
}: {
  title: string;
  body: any;
  border?: boolean;
  spanFull?: boolean;
  variant?: 'warn';
}) {
  if (!body) return null;
  const borderCls = border ? 'md:border-l border-ink-edge' : '';
  const spanCls = spanFull ? 'md:col-span-2 md:border-t border-ink-edge' : '';
  const warnCls = variant === 'warn' ? 'bg-signal-warn/5' : '';
  return (
    <div className={`p-5 md:p-6 ${borderCls} ${spanCls} ${warnCls}`}>
      <SmallCaps className="block mb-2">{title}</SmallCaps>
      <p className="body-serif text-sm text-ink leading-relaxed whitespace-pre-line">
        {typeof body === 'string' ? body : JSON.stringify(body)}
      </p>
    </div>
  );
}

function SignalCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card">
      <header className="px-4 py-2.5 border-b border-ink-edge">
        <SmallCaps>{title}</SmallCaps>
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
      <SmallCaps tight className="text-ink-muted shrink-0">{label}</SmallCaps>
      <span className="text-right text-ink">{display}</span>
    </div>
  );
}
