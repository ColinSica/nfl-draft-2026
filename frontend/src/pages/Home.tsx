import { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';
import { api, type MetaInfo, type PickRow } from '../lib/api';
import { DraftCountdown } from '../components/DraftCountdown';
import {
  HRule, SmallCaps, SectionHeader, Dateline, Byline, Stamp, Footnote, FigureCaption,
} from '../components/editorial';

/**
 * The Draft Ledger · Front Page.
 *
 * Broadsheet cover-page layout:
 *   1. Masthead dateline + lead headline + byline
 *   2. Abstract (italic serif intro)
 *   3. "In this issue" table of contents
 *   4. Lead story: top-10 mock with reasoning (research table)
 *   5. Methodology summary (two-column)
 *   6. Position mix chart
 *   7. Footer notes
 */
export function Home() {
  const [meta, setMeta] = useState<MetaInfo | null>(null);
  const [latestPicks, setLatestPicks] = useState<PickRow[] | null>(null);
  const [simMeta, setSimMeta] = useState<any>(null);
  const [reasoning, setReasoning] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    api.meta().then(setMeta).catch(() => {});
    api.latestSim()
      .then((r) => { setLatestPicks(r.picks); setSimMeta(r.meta); })
      .catch(() => {});
    fetch('/api/simulations/reasoning')
      .then(r => r.json()).then(setReasoning).catch(() => {});
    fetch('/api/independent-stats')
      .then(r => r.json()).then(setStats).catch(() => {});
  }, []);

  const top10 = (latestPicks ?? []).filter(p => p.pick_number <= 10);

  return (
    <div className="space-y-14 pb-20">
      {/* ═════════════════════════════════════════════════════════════
       * FRONT PAGE — masthead, lede, abstract
       * ═════════════════════════════════════════════════════════════ */}
      <section className="relative">
        <Dateline issue="No. 26 · 2026 Draft Edition" />

        <div className="mt-8 grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-0 lg:gap-10">
          {/* Lead column */}
          <div className="space-y-6">
            <div className="flex items-center gap-3 flex-wrap reveal reveal-1">
              <Stamp variant="salmon">Lead Story</Stamp>
              <span className="caps text-ink-muted">The 2026 First Round</span>
            </div>

            <h1 className="display-jumbo text-ink reveal reveal-2"
                style={{ fontSize: 'clamp(2.75rem, 8.5vw, 6.5rem)' }}>
              Thirty-two agents, <em>one round</em>, simulated against live markets.
            </h1>

            <div className="reveal reveal-3">
              <Byline role="Quantitative research · University of Washington" />
            </div>

            <div className="reveal reveal-3">
              <HRule thick className="rule-draw" />
            </div>

            <p className="body-serif-lead text-ink reveal reveal-4 lede">
              A Monte Carlo simulator runs the 2026 NFL Draft thousands of times,
              modelling every front office as an autonomous agent with its own
              roster need, scheme premium, coaching-tree DNA, and cap posture.
              The simulated picks are then priced against live Kalshi prediction
              markets &mdash; real money on specific team-player outcomes &mdash;
              to produce a calibrated probability for every slot. Pick
              probabilities below reflect the model's posterior belief, blending
              our team-fit signal (40%) with market-implied odds (60%).
            </p>
          </div>

          {/* Side rail — vitals */}
          <aside className="border-t-2 border-ink pt-5 lg:border-t-0 lg:border-l lg:border-ink-edge lg:pt-0 lg:pl-8 space-y-6 reveal reveal-4">
            <SmallCaps>At a glance</SmallCaps>
            <VitalsGrid stats={stats} simMeta={simMeta} meta={meta} />
            <HRule />
            <div className="space-y-2">
              <SmallCaps tight>Latest simulation</SmallCaps>
              <p className="font-mono text-xs">
                {simMeta?.mtime
                  ? new Date(simMeta.mtime).toLocaleString('en-US', {
                      month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
                    })
                  : '—'}
              </p>
            </div>
            <HRule />
            <div className="space-y-2">
              <SmallCaps tight>Odds source</SmallCaps>
              <p className="body-serif text-sm">
                Live via Kalshi · KXNFLDRAFT series · 1,909+ markets parsed
              </p>
            </div>
          </aside>
        </div>
      </section>

      {/* ═════════════════════════════════════════════════════════════
       * COUNTDOWN + IN THIS ISSUE
       * ═════════════════════════════════════════════════════════════ */}
      <section className="grid grid-cols-1 lg:grid-cols-[1fr_2fr] gap-0 border-y border-ink">
        <div className="p-6 lg:p-8 lg:border-r border-ink-edge bg-paper-raised">
          <DraftCountdown />
        </div>
        <div className="p-6 lg:p-8 space-y-4">
          <SmallCaps>In This Issue</SmallCaps>
          <ul className="space-y-2 body-serif">
            <TocEntry num="01" to="/simulate" title="First round." deck="Full 32 picks with calibrated probabilities and reasoning." />
            <TocEntry num="02" to="/lab"      title="Mock Lab."    deck="Adjust positional demand, lock picks, re-allocate the board." />
            <TocEntry num="03" to="/prospects" title="Prospects."  deck="Landing distributions per player, consensus rank, college." />
            <TocEntry num="04" to="/teams"    title="Teams."       deck="Front-office dossiers: needs, cap, scheme, coaching tree." />
            <TocEntry num="05" to="/compare"  title="Markets."     deck="Model vs consensus, slot-by-slot divergence." />
            <TocEntry num="06" to="/method"   title="Methodology." deck="Stages, inputs, independence contract, calibration." />
          </ul>
        </div>
      </section>

      {/* ═════════════════════════════════════════════════════════════
       * LEAD STORY — Top 10 picks as a research table
       * ═════════════════════════════════════════════════════════════ */}
      <section>
        <SectionHeader
          number={1}
          kicker="Lead Story"
          title="Top of the board."
          deck="Ten picks, with market-blended probabilities and per-pick reasoning drawn from analyst sources and team profiles."
        />

        <div className="mt-6 overflow-x-auto">
          <table className="research-table">
            <thead>
              <tr>
                <th className="num">Pk</th>
                <th>Team</th>
                <th>Player</th>
                <th>Pos</th>
                <th>School</th>
                <th className="num">P<sub>(pick)</sub></th>
                <th>Thesis</th>
              </tr>
            </thead>
            <tbody>
              {top10.length === 0 ? (
                <tr><td colSpan={7} className="text-center py-10 italic text-ink-muted">Loading simulation…</td></tr>
              ) : top10.map(p => {
                const c0 = p.candidates?.[0];
                const r = reasoning?.picks?.[String(p.pick_number)];
                const summary = (r?.reasoning_summary ?? '').replace(/\s+/g, ' ').trim();
                return (
                  <tr key={p.pick_number}>
                    <td className="num text-ink-muted" style={{ width: 40 }}>
                      {String(p.pick_number).padStart(2, '0')}
                    </td>
                    <td className="font-mono text-xs font-medium" style={{ width: 60 }}>
                      {p.most_likely_team ?? p.team ?? '—'}
                    </td>
                    <td className="font-serif" style={{ fontSize: '0.98rem', minWidth: 160 }}>
                      <Link to="/simulate" className="hover:text-accent-salmon transition">
                        {c0?.player ?? '—'}
                      </Link>
                    </td>
                    <td className="font-mono text-xs">{c0?.position ?? '—'}</td>
                    <td className="font-serif italic text-sm text-ink-muted" style={{ maxWidth: 140 }}>
                      {c0?.college ?? '—'}
                    </td>
                    <td className="num">
                      <ProbBar p={c0?.probability ?? 0} />
                    </td>
                    <td className="text-sm font-serif text-ink" style={{ maxWidth: 480 }}>
                      {summary || <span className="italic text-ink-muted">—</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="mt-4 flex items-center justify-between gap-4 flex-wrap">
          <FigureCaption>
            Figure 1 · Modal pick per slot with model posterior probability.
            See First Round for the full 32-pick table with alternates and
            expanded thesis.
          </FigureCaption>
          <Link to="/simulate" className="btn-primary">
            <span>Full first round</span>
            <ArrowUpRight size={14} />
          </Link>
        </div>
      </section>

      {/* ═════════════════════════════════════════════════════════════
       * METHODOLOGY — two-column summary
       * ═════════════════════════════════════════════════════════════ */}
      <section>
        <SectionHeader
          number={2}
          kicker="How the model works"
          title="Two stages, three signals."
          deck="A sell-side primer for the quantitative framework."
        />

        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-0 border border-ink-edge">
          <MethodBlock
            index="01"
            label="Stage 1 · Board construction"
            title="Player value from tape, traits, and markets."
            body={[
              'Stage 1 converts tape grades (PFF 3-year), athletic composite (RAS), team-visit coverage, age, injury history, and conference tier into an independent grade per prospect.',
              'Market prices from Kalshi pick-position O/U contracts serve as an anchor &mdash; where the market says a player goes, the model\'s grade is pulled toward that slot, weighted by market confidence.',
            ]}
          />
          <MethodBlock
            index="02"
            label="Stage 2 · Team-agent simulation"
            title="32 front offices, Monte Carlo."
            body={[
              'Each team is modelled as an autonomous agent with its own scoring function: need, best-player-available, scheme premium, coaching-tree bias, visit signal, and GM positional affinity.',
              'Picks converge via softmax over a top-K candidate pool. Market team-landing priors contribute a large additive bonus, so Kalshi-endorsed (team, player) pairs win close calls.',
            ]}
            border
          />
        </div>
      </section>

      {/* ═════════════════════════════════════════════════════════════
       * POSITION MIX
       * ═════════════════════════════════════════════════════════════ */}
      <PositionMix picks={latestPicks ?? []} />

      {/* ═════════════════════════════════════════════════════════════
       * FOOTER NOTES
       * ═════════════════════════════════════════════════════════════ */}
      <section className="border-t-2 border-ink pt-6 space-y-3">
        <SmallCaps>Notes</SmallCaps>
        <Footnote mark="*">
          "P<sub>(pick)</sub>" is the model's posterior belief that the listed
          team drafts the listed player at this slot, not the raw frequency
          from Monte Carlo. Calibration layers a 20% model haircut, 10% world-
          uncertainty discount, and a hard ceiling of 78% to reflect real-draft
          unknowns (late trades, medical news, private intel).
        </Footnote>
        <Footnote mark="†">
          For teams with multiple R1 picks, the team-landing market is
          allocated across slots weighted by player market P50. Single-slot
          teams receive full allocation at their one pick.
        </Footnote>
        <Footnote mark="‡">
          Reasoning citations pull from a team-tagged analyst-quote cache
          sourced from ESPN, CBS Sports, The Ringer, Pro Football Network,
          NFL.com, Bleacher Report, and Sports Illustrated.
        </Footnote>
      </section>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────

function VitalsGrid({ stats }: { stats: any; simMeta: any; meta: any }) {
  return (
    <dl className="space-y-3">
      <Vital label="R1 picks modelled" value="32" />
      <Vital label="Kalshi markets" value={stats?.n_kalshi_markets ?? '1,909'} />
      <Vital label="Team agents" value={String(stats?.n_agents ?? 32)} />
      <Vital label="Prospects graded" value={String(stats?.n_prospects ?? 727)} />
      <Vital label="Simulations" value={stats?.n_sims ? String(stats.n_sims) : '100'} />
      <Vital label="Analyst picks as input" value="0" accent="#4A6B3F" />
    </dl>
  );
}

function Vital({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 pb-2 border-b border-ink-edge last:border-b-0">
      <dt className="caps-tight text-ink-muted">{label}</dt>
      <dd className="display-num text-base font-medium" style={{ color: accent ?? '#1A1612' }}>{value}</dd>
    </div>
  );
}

function TocEntry({
  num, to, title, deck,
}: { num: string; to: string; title: string; deck: string }) {
  return (
    <li className="group border-b border-ink-edge last:border-b-0 pb-2 last:pb-0">
      <Link to={to} className="flex items-baseline gap-3 hover:bg-accent-highlight transition-colors duration-150 py-1 px-1 -mx-1">
        <span className="display-num text-xs text-accent-salmon">§ {num}</span>
        <span className="font-display font-medium text-ink" style={{ fontSize: '1.05rem' }}>
          {title}
        </span>
        <span className="flex-1 border-b border-dotted border-ink-edge mx-2 mb-1 hidden sm:block" />
        <span className="text-sm text-ink-muted italic hidden sm:inline">{deck}</span>
        <ArrowUpRight size={12} className="text-ink-muted group-hover:text-accent-salmon group-hover:-translate-y-0.5 transition" />
      </Link>
    </li>
  );
}

function ProbBar({ p }: { p: number }) {
  const pct = Math.round(p * 100);
  return (
    <div className="flex items-center gap-2 justify-end">
      <div className="w-14 h-1.5 bg-paper-hover relative overflow-hidden">
        <div className="absolute inset-y-0 left-0 bg-accent-salmon"
             style={{ width: `${Math.min(100, pct)}%` }} />
      </div>
      <span className="font-mono text-xs tabular-nums w-10 text-right">
        {pct}%
      </span>
    </div>
  );
}

function MethodBlock({
  index, label, title, body, border = false,
}: {
  index: string;
  label: string;
  title: string;
  body: string[];
  border?: boolean;
}) {
  return (
    <div className={`p-6 md:p-8 space-y-4 bg-paper-surface ${border ? 'md:border-l border-ink-edge' : ''}`}>
      <div className="flex items-baseline gap-3">
        <span className="display-num text-3xl text-accent-salmon">{index}</span>
        <SmallCaps tight>{label}</SmallCaps>
      </div>
      <h3 className="display-broadcast text-2xl md:text-3xl text-ink"
          style={{ fontSize: 'clamp(1.5rem, 2.6vw, 2rem)' }}>
        {title}
      </h3>
      <div className="space-y-3 body-serif text-ink-soft text-base">
        {body.map((b, i) => (
          <p key={i} dangerouslySetInnerHTML={{ __html: b }} />
        ))}
      </div>
    </div>
  );
}

function PositionMix({ picks }: { picks: PickRow[] }) {
  const counts = useMemo(() => {
    const r1 = picks.filter(p => p.pick_number <= 32);
    const byPos: Record<string, number> = {};
    r1.forEach(p => {
      const pos = p.candidates?.[0]?.position ?? '—';
      byPos[pos] = (byPos[pos] ?? 0) + 1;
    });
    return Object.entries(byPos).sort((a, b) => b[1] - a[1]);
  }, [picks]);

  if (counts.length === 0) return null;
  const max = Math.max(...counts.map(([, c]) => c));

  return (
    <section>
      <SectionHeader
        number={3}
        kicker="R1 Position Mix"
        title="Where the first round spent its capital."
      />
      <div className="mt-6 border border-ink-edge bg-paper-surface p-6">
        <div className="space-y-2.5">
          {counts.map(([pos, c]) => (
            <div key={pos} className="flex items-center gap-4">
              <span className="font-mono text-sm font-medium w-10 shrink-0 text-right text-ink">
                {pos}
              </span>
              <div className="flex-1 h-4 bg-paper-hover relative overflow-hidden">
                <div
                  className="absolute inset-y-0 left-0 bg-ink"
                  style={{ width: `${(c / max) * 100}%` }}
                />
              </div>
              <span className="display-num text-sm w-7 shrink-0 text-right">{c}</span>
              <span className="font-mono text-xs text-ink-muted w-12 shrink-0 text-right">
                {Math.round((c / 32) * 100)}%
              </span>
            </div>
          ))}
        </div>
        <FigureCaption>
          Figure 2 · First-round position counts from the latest committed run.
        </FigureCaption>
      </div>
    </section>
  );
}
