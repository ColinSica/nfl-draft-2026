/**
 * Method — how the model actually works.
 * Stage 1, Stage 2, independence contract, features, limitations.
 */
import { SmallCaps, HRule } from '../components/editorial';

export function Method() {
  return (
    <div className="space-y-14 pb-16 max-w-4xl">
      <div className="space-y-5">
        <SmallCaps className="text-ink-soft">Method</SmallCaps>
        <h1
          className="display-broadcast leading-[0.85] text-ink"
          style={{ fontSize: 'clamp(2.5rem, 8vw, 6rem)' }}
        >
          How the model <span className="italic" style={{ color: '#D9A400' }}>actually</span> works.
        </h1>
        <HRule accent />
        <p className="text-lg text-ink-soft leading-relaxed max-w-2xl">
          Two stages. Thirty-two agents. No analyst picks as inputs. Here's the mechanism.
        </p>
      </div>

      {/* Stage 1 */}
      <section className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-8 items-start">
        <div className="display-num leading-none" style={{ color: '#D9A400', fontSize: '6rem' }}>
          01
        </div>
        <div className="space-y-4">
          <SmallCaps className="text-ink-soft">Stage 1 · Player board</SmallCaps>
          <h2 className="display-broadcast text-4xl text-ink leading-[0.9]">
            Value from tape, not mocks.
          </h2>
          <HRule />
          <p className="text-ink-soft leading-relaxed">
            Every prospect is scored from factual, measurable inputs. Analyst ranks and mock picks
            are banned from the pipeline; a test suite enforces this on every commit.
          </p>
          <ul className="space-y-2 text-sm">
            {[
              ['PFF 3-year tape grade', 'Play-by-play coaching-film grade aggregated over three seasons.'],
              ['RAS athletic composite', 'Kent Lee Platte\'s Relative Athletic Score from combine + pro-day testing.'],
              ['Visit coverage', 'Official top-30 visits, private workouts, coaching dinners — public reports only.'],
              ['Medical flags', 'Documented injuries, ACL/spine/shoulder severity tags.'],
              ['Production splits', 'College stats normalized against conference strength-of-schedule.'],
              ['Age curve', 'Early-entry vs. senior discount, calibrated from 2015–2024 draft outcomes.'],
              ['Scheme-fit tags', 'Archetype fit per position (press-man CB, wide-zone OT, hybrid LB, etc.).'],
            ].map(([label, desc]) => (
              <li key={label} className="flex items-baseline gap-3 py-2 border-b border-ink-edge last:border-b-0">
                <SmallCaps tight className="shrink-0 w-[180px] text-ink">{label}</SmallCaps>
                <span className="text-ink-soft">{desc}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Stage 2 */}
      <section className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-8 items-start">
        <div className="display-num leading-none" style={{ color: '#1F6FEB', fontSize: '6rem' }}>
          02
        </div>
        <div className="space-y-4">
          <SmallCaps className="text-ink-soft">Stage 2 · Team agents</SmallCaps>
          <h2 className="display-broadcast text-4xl text-ink leading-[0.9]">
            32 teams simulated as agents.
          </h2>
          <HRule />
          <p className="text-ink-soft leading-relaxed">
            Monte Carlo simulation runs the first round hundreds of times. Each team picks based
            on its own profile — not a global "best player available" rule. Trades emerge
            organically when capital, need, and tier scarcity align.
          </p>
          <ul className="space-y-2 text-sm">
            {[
              ['GM affinity', 'Positional preference derived from each GM\'s 2019–2025 pick history.'],
              ['Coaching tree', 'Shanahan / Harbaugh / Payton / Belichick / McVay / etc. — positional multipliers.'],
              ['Scheme premium', 'OC+DC scheme archetype determines which prospect types fit.'],
              ['Roster depth', 'Post-free-agency roster rooms scored 1–5 per position.'],
              ['Cap posture', 'Tight / moderate / flexible / abundant — affects expensive-position weighting.'],
              ['QB urgency', 'Scaled 0–1; teams with high urgency prioritize QB R1.'],
              ['Visit spread', 'Which prospects each team has publicly visited.'],
              ['Trade behavior', 'Historical trade-up / trade-down rates per GM.'],
            ].map(([label, desc]) => (
              <li key={label} className="flex items-baseline gap-3 py-2 border-b border-ink-edge last:border-b-0">
                <SmallCaps tight className="shrink-0 w-[180px] text-ink">{label}</SmallCaps>
                <span className="text-ink-soft">{desc}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* The Contract */}
      <section className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-8 items-start">
        <div className="display-num leading-none" style={{ color: '#17A870', fontSize: '6rem' }}>
          03
        </div>
        <div className="space-y-4">
          <SmallCaps className="text-ink-soft">The contract</SmallCaps>
          <h2 className="display-broadcast text-4xl text-ink leading-[0.9]">
            How we keep it honest.
          </h2>
          <HRule />
          <p className="text-ink-soft leading-relaxed">
            A pytest suite enforces the independence contract: any analyst-rank column
            (<code className="font-mono text-xs px-1 bg-paper-hover">consensus_rank</code>,{' '}
            <code className="font-mono text-xs px-1 bg-paper-hover">pff_rank</code>,{' '}
            <code className="font-mono text-xs px-1 bg-paper-hover">kiper_rank</code>,
            etc.) touching the Independent pipeline fails the build. Eight tests currently pass
            on every commit.
          </p>
          <p className="text-ink-soft leading-relaxed">
            The product goal is <strong className="text-ink">organic convergence</strong>: if the
            model, fed only tape and team profiles, lands at the same place as analyst consensus,
            that's a sign both are correctly modeling the same underlying team behavior. If the
            model diverges, it's a signal to enrich team profiles — not to loosen the contract.
          </p>
        </div>
      </section>

      {/* Confidence calibration */}
      <section className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-8 items-start">
        <div className="display-num leading-none" style={{ color: '#D9A400', fontSize: '6rem' }}>
          04
        </div>
        <div className="space-y-4">
          <SmallCaps className="text-ink-soft">Confidence calibration</SmallCaps>
          <h2 className="display-broadcast text-4xl text-ink leading-[0.9]">
            Labels tied to real history.
          </h2>
          <HRule />
          <p className="text-ink-soft leading-relaxed">
            Confidence labels on each pick are calibrated against what actually
            happened in the <strong className="text-ink">2024 and 2025 R1</strong> drafts
            (n=64 picks). For each pre-draft consensus probability bucket, we measured the
            real hit rate — whether the modal pick actually occurred.
          </p>
          <div className="border border-ink-edge bg-paper-surface mt-4">
            <div className="grid grid-cols-[1fr_auto_auto] px-4 py-2 border-b-2 border-ink-edge">
              <SmallCaps tight className="text-ink">Bucket</SmallCaps>
              <SmallCaps tight className="text-ink text-right pr-6">Threshold</SmallCaps>
              <SmallCaps tight className="text-ink text-right">Historical hit rate</SmallCaps>
            </div>
            {[
              ['HIGH',         '#17A870', '≥ 0.55 probability', '85%+ hits'],
              ['Moderate-high','#7BC043', '0.40–0.55',          '~65% hits'],
              ['Moderate-low', '#D9A400', '0.25–0.40',          '~45% hits'],
              ['Toss-up',      '#DC2F3D', '< 0.25',             '~20% hits'],
            ].map(([label, color, threshold, hit]) => (
              <div key={label} className="grid grid-cols-[1fr_auto_auto] px-4 py-2.5 border-b border-ink-edge last:border-b-0 items-baseline">
                <span className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full" style={{ background: color }} />
                  <span className="caps-tight" style={{ color }}>{label}</span>
                </span>
                <span className="font-mono text-sm text-ink pr-6">{threshold}</span>
                <span className="font-mono text-sm text-ink">{hit}</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-ink-soft italic">
            Source: historical consensus-to-actual backtest across 2024 + 2025 R1 (64 picks).
            Full data in <code className="text-[0.7rem]">confidence_calibration_2024_2025.json</code>.
          </p>
        </div>
      </section>

      {/* Limitations */}
      <section className="grid grid-cols-1 md:grid-cols-[80px_1fr] gap-8 items-start">
        <div className="display-num leading-none" style={{ color: '#848B98', fontSize: '6rem' }}>
          05
        </div>
        <div className="space-y-4">
          <SmallCaps className="text-ink-soft">Limitations</SmallCaps>
          <h2 className="display-broadcast text-4xl text-ink leading-[0.9]">
            What we don't claim.
          </h2>
          <HRule />
          <ul className="space-y-3 text-sm">
            {[
              ['Not a stock picker.', 'Tape grades have variance. The model ranks prospects relative to each other — it does not assert any prospect\'s pro outcome.'],
              ['Trade mechanics are probabilistic.', 'Simulated trades fire based on structural priors. Any specific trade is a possibility, not a prediction.'],
              ['Consensus ≠ truth.', 'Analyst consensus is a comparison baseline, not the correct answer. The real test is the draft itself.'],
              ['Last-minute intel drift.', 'Team-level leaks in the final 48h can move picks in ways no model can keep up with. Fresh news is encoded when public.'],
            ].map(([h, d]) => (
              <li key={h} className="py-2 border-b border-ink-edge last:border-b-0">
                <div className="display-broadcast text-base text-ink mb-1">{h}</div>
                <div className="text-ink-soft leading-relaxed">{d}</div>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
