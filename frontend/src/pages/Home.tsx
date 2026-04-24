import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';
import { api, type MetaInfo } from '../lib/api';
import { DraftCountdown } from '../components/DraftCountdown';
import { AccuracyDashboard } from '../components/AccuracyDashboard';
import { AccuracyGraphs } from '../components/AccuracyGraphs';
import { AtAGlanceStats } from '../components/AtAGlanceStats';
import {
  HRule, SmallCaps, SectionHeader, Dateline, Byline, Stamp, Footnote,
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
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    api.meta().then(setMeta).catch(() => {});
    fetch('/api/independent-stats')
      .then(r => r.ok ? r.json() : null)
      .then(setStats)
      .catch(() => {});
  }, []);

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
              <Stamp variant="brass">Lead Story</Stamp>
              <span className="caps text-ink-muted">The 2026 First Round</span>
            </div>

            <h1 className="display-jumbo text-ink reveal reveal-2"
                style={{ fontSize: 'clamp(2rem, 8.5vw, 6.5rem)' }}>
              Thirty-two front offices, <em>simulated independently</em>.
            </h1>

            <div className="reveal reveal-3">
              <Byline role="Quantitative research · University of Washington" />
            </div>

            <div className="reveal reveal-3">
              <HRule thick className="rule-draw" />
            </div>

            <p className="body-serif-lead text-ink reveal reveal-4 lede">
              Every NFL front office is modelled as an autonomous agent with
              its own roster need, scheme premium, coaching-tree DNA, cap
              posture, and GM draft-history fingerprint. A Monte Carlo drives
              them through the 2026 board a thousand times. The output is a
              probability distribution per slot, not a single prediction
              copied from somewhere else.
            </p>
          </div>

          {/* Side rail — vitals + live accuracy mini-widget */}
          <aside className="border-t-2 border-ink pt-5 lg:border-t-0 lg:border-l lg:border-ink-edge lg:pt-0 lg:pl-8 space-y-6 reveal reveal-4">
            <div className="space-y-3">
              <SmallCaps>At a glance</SmallCaps>
              <VitalsGrid stats={stats} simMeta={null} meta={meta} />
            </div>
            <HRule />
            <AtAGlanceStats />
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
            <TocEntry num="01" to="/accuracy"  title="Live accuracy." deck="Your rank vs the analyst field, updated as picks come off the board." />
            <TocEntry num="02" to="/full-mock" title="Full Mock."    deck="Every pick, all seven rounds — 257 assignments end-to-end." />
            <TocEntry num="03" to="/prospects" title="Prospects."    deck="Landing distributions per player, board rank, college." />
            <TocEntry num="04" to="/teams"     title="Teams."        deck="Front-office dossiers: needs, cap, scheme, coaching tree." />
            <TocEntry num="05" to="/lab"       title="Mock Lab."     deck="Adjust positional demand, lock picks, re-allocate the board." />
            <TocEntry num="06" to="/method"    title="Methodology."  deck="Stages, inputs, calibration." />
          </ul>
        </div>
      </section>

      {/* ═════════════════════════════════════════════════════════════
       * LIVE ACCURACY DASHBOARD
       * ═════════════════════════════════════════════════════════════ */}
      <section>
        <SectionHeader
          number={1}
          kicker="Live scoreboard"
          title="How the mock is doing."
          deck="Real-time accuracy vs ~30 published analyst mocks. Updates as the R1 picks come off the board."
        />
        <div className="mt-4">
          <LockBadge />
        </div>
        <div className="mt-4">
          <AccuracyDashboard compact />
        </div>

        {/* Graphs — histogram + pick-strip */}
        <div className="mt-8">
          <AccuracyGraphs />
        </div>

        <div className="mt-6 flex justify-end">
          <Link to="/accuracy" className="btn-primary">
            <span>Full scoreboard</span>
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
            title="Player value from tape, traits, and context."
            body={[
              'PFF 3-year tape grades, athletic composite (RAS), team-visit coverage, age, injury history, and conference tier combine into an independent grade per prospect.',
              'Pre-draft pressers and documented team visits feed in as structured factual signals. Tape, traits, measurables, and reporting — never somebody else\'s ranking.',
            ]}
          />
          <MethodBlock
            index="02"
            label="Stage 2 · Team-agent simulation"
            title="32 front offices, Monte Carlo."
            body={[
              'Each team is modelled as an autonomous agent with its own scoring function: roster need (post-FA), scheme premium, coaching-tree tendencies, GM positional affinity (from their 2019-2025 picks), cap posture, and confirmed pre-draft visits.',
              'Picks converge via softmax over a top-K candidate pool. The sim runs 200+ times; the output is a probability distribution per slot, not a single point prediction.',
            ]}
            border
          />
        </div>
      </section>

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
          Reasoning citations pull from a team-tagged reporting cache
          (ESPN, CBS Sports, The Ringer, Pro Football Network, NFL.com,
          Bleacher Report, Sports Illustrated).
        </Footnote>
      </section>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────

export function LockBadge() {
  return (
    <div
      className="inline-flex items-center gap-3 px-4 py-2.5 border"
      style={{
        background: 'rgba(182,138,47,0.08)',
        borderColor: 'rgba(182,138,47,0.4)',
      }}
      role="note"
      aria-label="Mock draft lock timestamp"
    >
      <span className="w-1.5 h-1.5 rounded-full bg-accent-brass shrink-0" />
      <span className="font-mono text-[0.7rem] caps-tight text-accent-brass tracking-wider">
        Mock locked
      </span>
      <span className="font-mono text-xs text-ink">
        4/23/2026 · 4:59pm PT
      </span>
      <span className="font-mono text-[0.68rem] text-ink-muted hidden sm:inline">
        — before the draft started (5:00pm PT)
      </span>
    </div>
  );
}

function VitalsGrid({ stats }: { stats: any; simMeta: any; meta: any }) {
  // Show '—' rather than lying with a plausible default; the endpoint is
  // authoritative and defaults drift every time the model re-runs.
  const fmt = (v: any): string => {
    if (v === null || v === undefined) return '—';
    return String(v);
  };
  return (
    <dl className="space-y-3">
      <Vital label="R1 picks modelled" value="32" />
      <Vital label="Team agents" value={fmt(stats?.n_agents)} />
      <Vital label="Prospects graded" value={fmt(stats?.n_prospects)} />
      <Vital label="Simulations" value={fmt(stats?.n_sims)} />
    </dl>
  );
}

function Vital({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 pb-2 border-b border-ink-edge last:border-b-0">
      <dt className="caps-tight text-ink-muted">{label}</dt>
      <dd className="display-num text-base font-medium" style={{ color: accent ?? '#0B1F3A' }}>{value}</dd>
    </div>
  );
}

function TocEntry({
  num, to, title, deck,
}: { num: string; to: string; title: string; deck: string }) {
  return (
    <li className="group border-b border-ink-edge last:border-b-0 pb-2 last:pb-0">
      <Link to={to} className="flex items-baseline gap-3 hover:bg-accent-highlight transition-colors duration-150 py-1 px-1 -mx-1">
        <span className="display-num text-xs text-accent-brass">§ {num}</span>
        <span className="font-display font-medium text-ink" style={{ fontSize: '1.05rem' }}>
          {title}
        </span>
        <span className="flex-1 border-b border-dotted border-ink-edge mx-2 mb-1 hidden sm:block" />
        <span className="text-sm text-ink-muted italic hidden sm:inline">{deck}</span>
        <ArrowUpRight size={12} className="text-ink-muted group-hover:text-accent-brass group-hover:-translate-y-0.5 transition" />
      </Link>
    </li>
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
        <span className="display-num text-3xl text-accent-brass">{index}</span>
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

