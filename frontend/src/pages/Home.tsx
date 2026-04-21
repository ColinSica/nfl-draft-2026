import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, Users, UserCircle2, GitCompare, BookOpen } from 'lucide-react';
import { api, type MetaInfo, type PickRow } from '../lib/api';
import { useMode, MODE_META } from '../lib/mode';
import { ModeDescription, ModeSwitcher } from '../components/ModeSwitcher';
import { FreshnessPanel } from '../components/FreshnessPanel';
import { TrustBox } from '../components/TrustBox';
import { HRule, SmallCaps, SectionHeader } from '../components/editorial';
import { PickCard, type PickData } from '../components/PickCard';

export function Home() {
  const { mode } = useMode();
  const meta_ = MODE_META[mode];
  const [meta, setMeta] = useState<MetaInfo | null>(null);
  const [latestPicks, setLatestPicks] = useState<PickRow[] | null>(null);
  const [simMeta, setSimMeta] = useState<any>(null);

  useEffect(() => {
    api.meta().then(setMeta).catch(() => {});
    api.latestSim()
      .then((r) => { setLatestPicks(r.picks); setSimMeta(r.meta); })
      .catch(() => {});
  }, []);

  // Pick the most likely candidate per slot for the top-10 preview
  const top10: PickData[] = (latestPicks ?? [])
    .filter((p) => p.pick_number <= 10)
    .map((p) => {
      const pri = p.candidates?.[0];
      return {
        slot: p.pick_number,
        team: p.most_likely_team ?? p.team ?? '—',
        teamName: null,
        player: pri?.player ?? 'Pending',
        position: pri?.position ?? '',
        college: pri?.college ?? null,
        probability: pri?.probability ?? null,
        consensusRank: pri?.consensus_rank ?? null,
        grade: null,
        confidence: pri ? (pri.probability >= 0.6 ? 'HIGH' : pri.probability >= 0.35 ? 'MEDIUM' : 'LOW') : null,
        whySummary: pri
          ? buildWhyHint(pri.player, pri.position, pri.probability)
          : 'Awaiting latest simulation.',
        accent: meta_.accent,
      };
    });

  const modelRefresh = meta?.generated_at ?? null;
  const intelRefresh = meta?.analyst_intel_meta?.latest_intel_date ?? null;
  const simRun = simMeta?.finished_at ?? simMeta?.generated_at ?? null;

  return (
    <div className="space-y-14 pb-16">
      {/* ───────────────────────── HERO ───────────────────────── */}
      <section className="relative pt-6 md:pt-10">
        <div className="space-y-5">
          <div className="flex items-center gap-3 reveal reveal-1">
            <SmallCaps className="text-paper-subtle">2026 NFL Draft</SmallCaps>
            <span className="font-mono text-[0.68rem] text-paper-faint">—</span>
            <SmallCaps tight className="text-paper-muted">Analyst-independent prediction engine</SmallCaps>
          </div>

          <h1 className="display-serif tracking-[-0.03em] leading-[0.95] reveal reveal-2"
              style={{ fontSize: 'clamp(2.5rem, 7vw, 5.5rem)', fontWeight: 700 }}>
            How the draft
            <br />
            <span className="italic font-normal text-paper-muted">will actually play out.</span>
          </h1>

          <div className="reveal reveal-3">
            <HRule thick className="rule-draw" />
          </div>

          <p className="max-w-2xl text-lg leading-[1.55] text-paper-muted reveal reveal-3">
            A two-stage simulation of the 2026 NFL Draft.&nbsp;
            <span className="text-paper">Stage&nbsp;1</span> builds the player board from tape grades,
            athletic testing, and scheme-fit signals.&nbsp;
            <span className="text-paper">Stage&nbsp;2</span> simulates the draft as 32 autonomous team agents —
            each acting on its own needs, cap, coaches, and visit intel.
          </p>

          <div className="flex flex-wrap items-center gap-3 pt-2 reveal reveal-4">
            <ModeSwitcher />
            <span className="font-mono text-xs text-paper-subtle">
              viewing in <span style={{ color: meta_.accent }}>{meta_.label}</span> mode
            </span>
          </div>

          <div className="reveal reveal-5">
            <ModeDescription />
          </div>
        </div>
      </section>

      {/* ───────────────────────── TRUST BOX ───────────────────────── */}
      <TrustBox />

      {/* ───────────────────────── LATEST 1st ROUND ───────────────────────── */}
      <section>
        <SectionHeader
          number={1}
          kicker="Latest simulation"
          title="First round preview"
        />
        <div className="mt-6 space-y-3">
          {top10.length === 0 ? (
            <div className="card px-6 py-10 text-center">
              <p className="text-paper-muted italic">Loading latest simulation…</p>
            </div>
          ) : (
            top10.map((pd, i) => (
              <div key={pd.slot} className="reveal" style={{ animationDelay: `${0.05 * i}s` }}>
                <PickCard data={pd} />
              </div>
            ))
          )}
        </div>

        <div className="mt-6 flex items-center justify-between gap-4 flex-wrap">
          <span className="text-sm text-paper-muted">
            Showing picks 1–10 of 32.
          </span>
          <Link
            to="/simulate"
            className="btn-ghost group"
          >
            <span>View full first round</span>
            <ArrowUpRight size={14} className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
          </Link>
        </div>
      </section>

      {/* ───────────────────────── FRESHNESS ───────────────────────── */}
      <section>
        <FreshnessPanel
          data={{
            modelRefresh: modelRefresh,
            intelRefresh: intelRefresh,
            simRun: simRun,
          }}
        />
      </section>

      {/* ───────────────────────── FOUR ENTRY POINTS ───────────────────────── */}
      <section>
        <SectionHeader
          number={2}
          kicker="Explore"
          title="Four ways in"
        />
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          <EntryCard
            kicker="01"
            title="Teams"
            description="Open a team and see what they'll likely do, why, their trade odds, and confidence."
            to="/teams"
            Icon={Users}
            questionMark="what will they do?"
          />
          <EntryCard
            kicker="02"
            title="Prospects"
            description="Open a prospect and see their top landing spots, fit scores, and reasoning signals."
            to="/prospects"
            Icon={UserCircle2}
            questionMark="where will they land?"
          />
          <EntryCard
            kicker="03"
            title="Compare"
            description="Compare Independent vs Benchmark picks slot-by-slot. See where the market and model disagree."
            to="/compare"
            Icon={GitCompare}
            questionMark="who got it right?"
            accent="#6AA4D9"
          />
          <EntryCard
            kicker="04"
            title="Method"
            description="How the model works. Stage 1 board construction. Stage 2 team-agent simulation. Independence contract."
            to="/method"
            Icon={BookOpen}
            questionMark="how does it work?"
            accent="#A29987"
          />
        </div>
      </section>

      {/* ───────────────────────── HOW IT WORKS (TWO-STAGE) ───────────────────────── */}
      <section>
        <SectionHeader
          number={3}
          kicker="Method"
          title="Two stages, thirty-two agents"
        />
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-0 border border-ink-edge" style={{ borderRadius: '2px' }}>
          <StageBlock
            index="01"
            label="Stage 1 · Board"
            title="The player board."
            body={[
              'Every prospect is graded from factual signals only: PFF tape grades, RAS athletic composite, visit intel, medicals, conference, age, production.',
              'No analyst rank or mock pick data feeds into this stage. Guard tests enforce the contract.',
            ]}
          />
          <StageBlock
            index="02"
            label="Stage 2 · Draft"
            title="The 32 team agents."
            body={[
              'Each team acts as an autonomous agent. Profile includes GM, coach, scheme, win-now pressure, QB urgency, cap tier, roster depth, visit spread, coaching-tree tendencies, and trade behavior.',
              'Monte Carlo simulation runs the draft thousands of times. Trades emerge organically from capital + need + aggressiveness.',
            ]}
            accent="#E6AF5A"
            border
          />
        </div>
      </section>
    </div>
  );
}

/* ──────────────── Supporting components ──────────────── */

function EntryCard({
  kicker, title, description, to, Icon, questionMark, accent = '#C8F169',
}: {
  kicker: string;
  title: string;
  description: string;
  to: string;
  Icon: any;
  questionMark: string;
  accent?: string;
}) {
  return (
    <Link
      to={to}
      className="card p-6 hover:border-paper-muted transition-all ease-editorial duration-200 group
                 flex flex-col gap-4"
      style={{ borderRadius: '2px' }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="font-mono text-xs text-paper-subtle">{kicker}</span>
          <SmallCaps tight className="text-paper-subtle">{questionMark}</SmallCaps>
        </div>
        <Icon size={18} style={{ color: accent }} />
      </div>
      <h3 className="display-serif text-3xl md:text-4xl font-semibold leading-none tracking-tight">
        {title}
      </h3>
      <p className="text-paper-muted text-sm leading-relaxed">{description}</p>
      <div className="mt-auto pt-2 flex items-center justify-between border-t border-ink-edge">
        <span className="caps-tight text-paper-subtle">Explore</span>
        <ArrowUpRight
          size={16}
          className="text-paper-muted group-hover:text-paper transition-transform duration-200 group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
          style={{ color: accent }}
        />
      </div>
    </Link>
  );
}

function StageBlock({
  index, label, title, body, accent = '#C8F169', border = false,
}: {
  index: string;
  label: string;
  title: string;
  body: string[];
  accent?: string;
  border?: boolean;
}) {
  return (
    <div
      className={`p-6 md:p-8 space-y-4 ${border ? 'md:border-l border-ink-edge' : ''}`}
      style={{
        background: `linear-gradient(180deg, ${accent}04 0%, transparent 50%)`,
      }}
    >
      <div className="flex items-baseline gap-3">
        <span
          className="display-serif text-6xl md:text-7xl font-bold italic leading-none"
          style={{ color: accent }}
        >
          {index}
        </span>
        <div>
          <SmallCaps tight className="text-paper-subtle">{label}</SmallCaps>
        </div>
      </div>
      <h3 className="display-serif text-2xl md:text-3xl font-semibold tracking-tight leading-tight">
        {title}
      </h3>
      <div className="space-y-3 text-paper-muted text-sm leading-relaxed max-w-md">
        {body.map((b, i) => <p key={i}>{b}</p>)}
      </div>
    </div>
  );
}

// Infer a short 'why' hint from minimal data (until backend provides reasoning)
function buildWhyHint(
  player: string,
  position: string,
  probability: number | null | undefined,
): string {
  const probPct = probability ? Math.round(probability * 100) : null;
  if (!probPct) return `${player} emerges from team-agent consensus at this slot.`;
  if (probPct >= 80) {
    return `${player} locks in at this slot across ${probPct}% of simulations — the team's ${position} need and board availability converge strongly.`;
  }
  if (probPct >= 50) {
    return `${player} is the modal pick (${probPct}% of sims). Alternative paths include need-at-${position} alternatives and small probability of trade activity.`;
  }
  return `${player} narrowly edges competing prospects at this slot (${probPct}% share). Multiple reasonable outcomes remain in play.`;
}
