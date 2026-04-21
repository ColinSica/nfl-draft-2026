import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, Users, UserCircle2, GitCompare, BookOpen } from 'lucide-react';
import { api, type MetaInfo, type PickRow } from '../lib/api';
import { useMode, MODE_META } from '../lib/mode';
import { ModeDescription, ModeSwitcher } from '../components/ModeSwitcher';
import { FreshnessPanel, StaleBadge } from '../components/FreshnessPanel';
import { useMemo } from 'react';
import { TrustBox } from '../components/TrustBox';
import { HRule, SmallCaps, SectionHeader, LiveBadge } from '../components/editorial';
import { PickCard, type PickData } from '../components/PickCard';

export function Home() {
  const { mode } = useMode();
  const meta_ = MODE_META[mode];
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

  // Show top 5 picks — friendlier, less overwhelming than 10
  const top5: PickData[] = (latestPicks ?? [])
    .filter((p) => p.pick_number <= 5)
    .map((p) => {
      const pri = p.candidates?.[0];
      const modelReasoning = reasoning?.picks?.[String(p.pick_number)];
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
        confidence: null,
        whySummary: modelReasoning?.reasoning_summary
          ?? (pri ? buildWhyHint(pri.player, pri.position, pri.probability) : 'Awaiting latest simulation.'),
        accent: meta_.accent,
        alternates: (p.candidates ?? []).slice(1, 4).map(c => ({
          player: c.player,
          position: c.position,
          college: c.college,
          probability: c.probability,
        })),
      };
    });

  return (
    <div className="space-y-16 pb-16">
      {/* ───── HERO ───── */}
      <section className="relative pt-4 md:pt-8">
        <div className="space-y-7">
          <div className="flex items-center flex-wrap gap-3 reveal reveal-1">
            <LiveBadge>T-3 Days</LiveBadge>
            <SmallCaps className="text-ink-soft">2026 NFL Draft · Independent prediction engine</SmallCaps>
          </div>

          <h1 className="display-broadcast tracking-[-0.02em] leading-[0.85] text-ink reveal reveal-2"
              style={{ fontSize: 'clamp(2.75rem, 9vw, 7rem)' }}>
            The 2026 Draft,
            <br />
            <span style={{ color: '#D9A400' }}>simulated.</span>
            <br />
            <span className="text-ink-soft/60" style={{ fontSize: '0.42em', fontStyle: 'italic', display: 'inline-block', marginTop: '0.6em', fontWeight: 500, letterSpacing: '0.05em' }}>
              Without copying a single analyst mock.
            </span>
          </h1>

          <div className="reveal reveal-3">
            <HRule accent className="rule-draw" />
          </div>

          <p className="max-w-3xl text-[1.0625rem] leading-[1.6] text-ink-soft reveal reveal-3">
            A two-stage engine.&nbsp;
            <span className="text-ink font-semibold">Stage 1</span> builds the board from tape grades, athletic testing, medicals, and production — zero analyst rank as input.&nbsp;
            <span className="text-ink font-semibold">Stage 2</span> runs Monte Carlo simulations where all 32 teams act as autonomous agents, each picking on its own scheme, cap tier, coaching tree, and visit intel.
          </p>

          {/* By-the-numbers strip — pulled live from the API */}
          <div className="reveal reveal-4 pt-1">
            <div className="flex flex-wrap items-end gap-x-10 gap-y-5">
              <ByTheNumber
                value={stats?.top32_overlap_pct != null ? `${Math.round(stats.top32_overlap_pct)}%` : '—'}
                label="Top-32 overlap"
                sub="with consensus — organic convergence"
              />
              <ByTheNumber
                value={String(stats?.n_agents ?? 32)}
                label="Team agents"
                sub="autonomous, per-sim"
              />
              <ByTheNumber
                value={stats?.n_sims != null ? String(stats.n_sims) : '—'}
                label="Simulations"
                sub="in the latest run"
              />
              <ByTheNumber
                value={String(stats?.n_analyst_inputs ?? 0)}
                label="Analyst picks"
                sub="used as input · tests enforce"
                accent="#D9A400"
              />
              <ByTheNumber
                value={stats?.independence_tests_passing ?? '—'}
                label="Independence tests"
                sub="passing"
                accent="#17A870"
              />
            </div>
          </div>

          <div className="reveal reveal-5 pt-2">
            <hr className="hrule" />
          </div>

          <div className="flex flex-wrap items-center gap-4 pt-1 reveal reveal-5">
            <ModeSwitcher />
            <span className="text-sm text-ink-soft">
              Currently viewing&nbsp;
              <span className="caps-tight" style={{ color: meta_.accent }}>{meta_.label}</span>.
            </span>
          </div>

          <div className="reveal reveal-5 max-w-3xl">
            <ModeDescription />
          </div>
        </div>
      </section>

      {/* ───── TRUST ───── */}
      <TrustBox />

      {/* ───── LATEST PICKS (top 5 only) ───── */}
      <section>
        <SectionHeader
          number={1}
          kicker="Latest simulation"
          title="Top of the board."
        />
        <div className="mt-4 flex items-center gap-3 flex-wrap">
          <StaleBadge iso={simMeta?.finished_at ?? simMeta?.generated_at ?? null} />
          <span className="text-xs text-ink-soft">
            Cached-first · refreshes in background on new runs.
          </span>
        </div>
        <div className="mt-6 space-y-3">
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
            Top 5 shown. Full 32-pick first round with reasoning, trade frequency, and landing distributions →
          </span>
          <Link to="/simulate" className="btn-primary group">
            <span>Full first round</span>
            <ArrowUpRight size={16} className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
          </Link>
        </div>
      </section>

      {/* ───── FOUR ENTRY POINTS ───── */}
      <section>
        <SectionHeader
          number={2}
          kicker="Explore"
          title="Four views."
        />
        <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-5">
          <EntryCard
            kicker="A"
            title="Teams"
            description="32 team profiles. Pick odds, need stack, scheme fit, trade behavior, cap posture, visit intel."
            to="/teams"
            Icon={Users}
            questionMark="What will they do?"
            accent="#D9A400"
          />
          <EntryCard
            kicker="B"
            title="Prospects"
            description="Board, landing distributions, team-fit scores, injury flags, reasoning signals, visit coverage."
            to="/prospects"
            Icon={UserCircle2}
            questionMark="Where do they land?"
            accent="#1F6FEB"
          />
          <EntryCard
            kicker="C"
            title="Compare"
            description="Independent model vs analyst consensus, slot-by-slot. Overlap, divergence, and the reasoning behind each."
            to="/compare"
            Icon={GitCompare}
            questionMark="Independent vs market"
            accent="#17A870"
          />
          <EntryCard
            kicker="D"
            title="Method"
            description="Stage 1 board construction, Stage 2 team-agent simulation, the independence contract, feature inventory."
            to="/method"
            Icon={BookOpen}
            questionMark="Under the hood"
            accent="#5B6370"
          />
        </div>
      </section>

      {/* ───── FRESHNESS ───── */}
      <section>
        <FreshnessPanel
          data={{
            modelRefresh: meta?.generated_at ?? null,
            intelRefresh: meta?.analyst_intel_meta?.latest_intel_date ?? null,
            simRun: simMeta?.finished_at ?? simMeta?.generated_at ?? null,
          }}
        />
      </section>

      {/* ───── R1 POSITION DISTRIBUTION ───── */}
      <PositionHistogram picks={latestPicks ?? []} />

      {/* ───── HOW IT WORKS ───── */}
      <section>
        <SectionHeader
          number={3}
          kicker="Method"
          title="Two stages. Thirty-two agents."
        />
        <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-0 border border-ink-edge bg-paper-surface">
          <StageBlock
            index="01"
            label="Stage 1 · Board"
            title="Player value from tape."
            body={[
              'PFF 3-year grades. RAS athletic composite. Top-30 visit coverage. Medical flags. Conference tier. Age curve. Production splits.',
              'No analyst rank inputs. Independence test suite enforces the contract on every run.',
            ]}
            accent="#D9A400"
          />
          <StageBlock
            index="02"
            label="Stage 2 · Draft"
            title="32 teams as agents."
            body={[
              'Per-team profile: GM affinity, coaching tree, scheme premium, roster depth, cap posture, QB urgency, visit spread, trade behavior.',
              'Monte Carlo simulates the full first round N times. Trades fire when capital, need, and tier scarcity align — not from scripts.',
            ]}
            accent="#1F6FEB"
            border
          />
        </div>
      </section>
    </div>
  );
}

function PositionHistogram({ picks }: { picks: PickRow[] }) {
  const counts = useMemo(() => {
    const r1 = picks.filter(p => p.pick_number <= 32);
    const byPos: Record<string, number> = {};
    r1.forEach(p => {
      const pos = p.candidates?.[0]?.position ?? '—';
      byPos[pos] = (byPos[pos] ?? 0) + 1;
    });
    return Object.entries(byPos)
      .sort((a, b) => b[1] - a[1]);
  }, [picks]);

  if (counts.length === 0) return null;
  const max = Math.max(...counts.map(([, c]) => c));
  const POS_COLOR: Record<string, string> = {
    QB: '#D9A400', RB: '#B88A00', WR: '#1F6FEB', TE: '#4A9EFF',
    OT: '#DC2F3D', IOL: '#E68A6A',
    EDGE: '#17A870', DL: '#0E6945', IDL: '#0E6945',
    LB: '#7BC043', CB: '#5B6370', S: '#848B98',
  };

  return (
    <section>
      <SectionHeader
        number={4}
        kicker="R1 mix"
        title="Position count in the first round."
      />
      <div className="mt-8 card p-5">
        <div className="space-y-3">
          {counts.map(([pos, c]) => (
            <div key={pos} className="flex items-center gap-3">
              <span
                className="display-broadcast w-14 shrink-0 text-right text-ink"
                style={{ color: POS_COLOR[pos] ?? '#848B98' }}
              >
                {pos}
              </span>
              <div className="flex-1 h-5 bg-paper-hover relative overflow-hidden">
                <div
                  className="absolute inset-y-0 left-0 flex items-center justify-end pr-2"
                  style={{
                    width: `${(c / max) * 100}%`,
                    background: POS_COLOR[pos] ?? '#848B98',
                  }}
                >
                  <span className="display-num text-sm text-paper">{c}</span>
                </div>
              </div>
              <span className="font-mono text-xs text-ink-soft w-14 shrink-0">
                {Math.round((c / 32) * 100)}% of R1
              </span>
            </div>
          ))}
        </div>
        <p className="text-xs text-ink-soft/80 italic mt-4">
          Aggregated across all simulation runs. Top positions drafted in R1 this year.
        </p>
      </div>
    </section>
  );
}

function ByTheNumber({
  value, label, sub, accent,
}: {
  value: string;
  label: string;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="space-y-1">
      <div
        className="display-num leading-[0.85]"
        style={{
          fontSize: 'clamp(2rem, 4vw, 3rem)',
          color: accent ?? '#12151B',
        }}
      >
        {value}
      </div>
      <div className="caps-tight text-ink leading-none">{label}</div>
      {sub && <div className="text-xs text-ink-soft/80 mt-0.5">{sub}</div>}
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
