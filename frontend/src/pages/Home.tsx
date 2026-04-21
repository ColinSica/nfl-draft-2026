import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, Users, UserCircle2, GitCompare, BookOpen } from 'lucide-react';
import { api, type MetaInfo, type PickRow } from '../lib/api';
import { useMode, MODE_META } from '../lib/mode';
import { ModeDescription, ModeSwitcher } from '../components/ModeSwitcher';
import { FreshnessPanel } from '../components/FreshnessPanel';
import { TrustBox } from '../components/TrustBox';
import { HRule, SmallCaps, SectionHeader, LiveBadge } from '../components/editorial';
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

  // Show top 5 picks — friendlier, less overwhelming than 10
  const top5: PickData[] = (latestPicks ?? [])
    .filter((p) => p.pick_number <= 5)
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
        whySummary: pri ? buildWhyHint(pri.player, pri.position, pri.probability) : 'Awaiting latest simulation.',
        accent: meta_.accent,
      };
    });

  return (
    <div className="space-y-16 pb-16">
      {/* ───── HERO ───── */}
      <section className="relative pt-4 md:pt-8">
        <div className="space-y-6">
          <div className="flex items-center flex-wrap gap-3 reveal reveal-1">
            <LiveBadge>T-3 Days · Draft week</LiveBadge>
            <SmallCaps className="text-ink-soft">2026 NFL Draft</SmallCaps>
          </div>

          <h1 className="display-broadcast tracking-[-0.02em] leading-[0.85] text-ink reveal reveal-2"
              style={{ fontSize: 'clamp(3rem, 10vw, 7.5rem)' }}>
            Who picks
            <br />
            <span className="italic" style={{ color: '#D9A400' }}>whom</span>
            <span className="italic text-ink-soft/70 ml-4" style={{ fontSize: '0.6em' }}>
              and why
            </span>
            <span style={{ color: '#D9A400' }}>.</span>
          </h1>

          <div className="reveal reveal-3">
            <HRule accent className="rule-draw" />
          </div>

          <p className="max-w-2xl text-lg leading-[1.55] text-ink-soft reveal reveal-3">
            A prediction engine for the 2026 NFL Draft.&nbsp;
            <span className="text-ink font-semibold">Stage&nbsp;1</span> builds the player board.&nbsp;
            <span className="text-ink font-semibold">Stage&nbsp;2</span> runs the draft as 32 team agents —
            each picking based on its own needs, coaches, cap, and visit intel.
          </p>

          <div className="flex flex-wrap items-center gap-4 pt-2 reveal reveal-4">
            <ModeSwitcher />
            <span className="text-sm text-ink-soft">
              Viewing in&nbsp;
              <span className="caps-tight" style={{ color: meta_.accent }}>{meta_.label}</span>
              &nbsp;mode.
            </span>
          </div>

          <div className="reveal reveal-5 max-w-2xl">
            <ModeDescription />
          </div>
        </div>
      </section>

      {/* ───── TRUST ───── */}
      <TrustBox />

      {/* ───── LATEST PICKS (top 5 only — friendlier) ───── */}
      <section>
        <SectionHeader
          number={1}
          kicker="Latest simulation"
          title="The top 5 picks."
        />
        <div className="mt-8 space-y-3">
          {top5.length === 0 ? (
            <div className="card px-6 py-10 text-center">
              <p className="text-ink-soft italic">Loading latest simulation…</p>
            </div>
          ) : (
            top5.map((pd, i) => (
              <div key={pd.slot} className="reveal" style={{ animationDelay: `${0.05 * i}s` }}>
                <PickCard data={pd} />
              </div>
            ))
          )}
        </div>

        <div className="mt-8 flex items-center justify-between gap-4 flex-wrap">
          <span className="text-sm text-ink-soft">
            Showing the top 5. Full 32 picks with reasoning below.
          </span>
          <Link to="/simulate" className="btn-primary group">
            <span>See full first round</span>
            <ArrowUpRight size={16} className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
          </Link>
        </div>
      </section>

      {/* ───── FOUR ENTRY POINTS — simplified copy ───── */}
      <section>
        <SectionHeader
          number={2}
          kicker="Explore"
          title="Pick your lane."
        />
        <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-5">
          <EntryCard
            kicker="A"
            title="Teams"
            description="Open any of the 32 teams. See their likely pick, why, trade odds, needs."
            to="/teams"
            Icon={Users}
            questionMark="What will they do?"
            accent="#D9A400"
          />
          <EntryCard
            kicker="B"
            title="Prospects"
            description="Open any prospect. See their likely landing spots, team fits, and reasoning."
            to="/prospects"
            Icon={UserCircle2}
            questionMark="Where will they land?"
            accent="#1F6FEB"
          />
          <EntryCard
            kicker="C"
            title="Compare"
            description="Compare our model against analyst consensus, slot by slot."
            to="/compare"
            Icon={GitCompare}
            questionMark="Who got it right?"
            accent="#17A870"
          />
          <EntryCard
            kicker="D"
            title="Method"
            description="How the model works. Stage 1, Stage 2, and the independence contract."
            to="/method"
            Icon={BookOpen}
            questionMark="How does it work?"
            accent="#5B6370"
          />
        </div>
      </section>

      {/* ───── FRESHNESS (smaller, less prominent) ───── */}
      <section>
        <FreshnessPanel
          data={{
            modelRefresh: meta?.generated_at ?? null,
            intelRefresh: meta?.analyst_intel_meta?.latest_intel_date ?? null,
            simRun: simMeta?.finished_at ?? simMeta?.generated_at ?? null,
          }}
        />
      </section>

      {/* ───── HOW IT WORKS ───── */}
      <section>
        <SectionHeader
          number={3}
          kicker="Method"
          title="Two stages, thirty-two agents."
        />
        <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-0 border border-ink-edge bg-paper-surface">
          <StageBlock
            index="01"
            label="Stage 1 · Board"
            title="The player board."
            body={[
              'Every prospect is graded from factual signals — tape grades, athletic testing, visit intel, medicals, age, production.',
              'No analyst rank feeds in. Independence tests lock the contract in place.',
            ]}
            accent="#D9A400"
          />
          <StageBlock
            index="02"
            label="Stage 2 · Draft"
            title="The 32 team agents."
            body={[
              'Each team picks on its own profile — GM, coach, scheme, cap, roster depth, visit spread, trade behavior.',
              'Monte Carlo runs the draft thousands of times. Trades emerge organically from capital and need.',
            ]}
            accent="#1F6FEB"
            border
          />
        </div>
      </section>
    </div>
  );
}

function EntryCard({
  kicker, title, description, to, Icon, questionMark, accent = '#D9A400',
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
      className="card p-7 hover:shadow-card-raised hover:-translate-y-0.5 transition-all ease-broadcast duration-200 group
                 flex flex-col gap-5 relative overflow-hidden"
    >
      <span
        className="absolute top-0 left-0 right-0 h-[3px] scale-x-0 group-hover:scale-x-100 origin-left transition-transform duration-300 ease-broadcast"
        style={{ background: accent }}
      />
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span
            className="display-num text-xs px-1.5 py-0.5 text-ink"
            style={{ background: `${accent}22` }}
          >
            {kicker}
          </span>
          <SmallCaps tight className="text-ink-soft">{questionMark}</SmallCaps>
        </div>
        <Icon size={22} style={{ color: accent }} />
      </div>
      <h3 className="display-broadcast text-5xl md:text-6xl leading-[0.85] text-ink">
        {title}
      </h3>
      <p className="text-ink-soft leading-relaxed">{description}</p>
      <div className="mt-auto pt-3 flex items-center justify-between border-t border-ink-edge">
        <span className="caps-tight text-ink-soft">Open</span>
        <ArrowUpRight
          size={20}
          className="transition-transform duration-200 group-hover:translate-x-1 group-hover:-translate-y-1"
          style={{ color: accent }}
        />
      </div>
    </Link>
  );
}

function StageBlock({
  index, label, title, body, accent = '#D9A400', border = false,
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
      className={`p-7 md:p-10 space-y-5 relative ${border ? 'md:border-l border-ink-edge' : ''}`}
      style={{
        background: `linear-gradient(180deg, ${accent}0A 0%, transparent 60%)`,
      }}
    >
      <div className="flex items-baseline gap-4">
        <span
          className="display-num leading-none"
          style={{
            color: accent,
            fontSize: 'clamp(4.5rem, 9vw, 7rem)',
          }}
        >
          {index}
        </span>
        <SmallCaps tight className="text-ink-soft">{label}</SmallCaps>
      </div>
      <h3 className="display-broadcast text-3xl md:text-4xl leading-[0.9] text-ink">
        {title}
      </h3>
      <div className="space-y-3 text-ink-soft leading-relaxed max-w-md">
        {body.map((b, i) => <p key={i}>{b}</p>)}
      </div>
    </div>
  );
}

function buildWhyHint(
  player: string,
  position: string,
  probability: number | null | undefined,
): string {
  const probPct = probability ? Math.round(probability * 100) : null;
  if (!probPct) return `${player} emerges from team-agent consensus at this slot.`;
  if (probPct >= 80) {
    return `${player} locks in across ${probPct}% of simulations — team need at ${position} and board availability converge strongly.`;
  }
  if (probPct >= 50) {
    return `${player} is the modal pick (${probPct}% of sims). Alternative paths include other ${position} options and small trade probability.`;
  }
  return `${player} narrowly edges competing prospects here (${probPct}% share). Multiple reasonable outcomes remain in play.`;
}
