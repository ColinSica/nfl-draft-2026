/**
 * Methodology · The Draft Ledger.
 *
 * The portfolio page for the quantitative framework. Three stages:
 *   1. Board construction (tape + traits)
 *   2. Team-agent Monte Carlo
 *   3. Market calibration against Kalshi prediction-market pricing
 *
 * Plus the independence contract, calibration story, and limitations.
 */
import { HRule, SmallCaps, Dateline, Byline, Stamp, Footnote, FigureCaption } from '../components/editorial';

export function Method() {
  return (
    <div className="space-y-14 pb-16 max-w-4xl">
      <Dateline issue="Methodology Edition" />

      <header className="space-y-4">
        <Stamp variant="ink">White Paper</Stamp>
        <h1 className="display-jumbo text-ink"
            style={{ fontSize: 'clamp(2rem, 6vw, 4.5rem)' }}>
          How the <em>model</em> actually works.
        </h1>
        <Byline role="A quantitative framework for forecasting the 2026 NFL Draft" />
        <HRule thick />
        <p className="body-serif-lead text-ink lede">
          The Draft Ledger forecasts the 2026 NFL Draft by running a full
          Monte Carlo simulation where every team acts as an autonomous
          agent, then calibrating every pick against live Kalshi prediction-
          market pricing. The pipeline is three stages: build the board
          from tape and traits, simulate the draft with team-specific
          decision functions, and overlay real-money market signals to
          produce a posterior probability for each pick.
        </p>
      </header>

      {/* ───── Stage 1 ───── */}
      <section className="space-y-5">
        <div className="flex items-baseline gap-4 pt-2">
          <span className="display-num text-5xl text-accent-brass">01</span>
          <SmallCaps>Stage One · Player Board</SmallCaps>
        </div>
        <h2 className="display-broadcast text-ink"
            style={{ fontSize: 'clamp(1.75rem, 3.2vw, 2.5rem)' }}>
          Grading 727 prospects on tape and traits.
        </h2>
        <HRule accent />
        <div className="grid grid-cols-1 md:grid-cols-[1fr_260px] gap-8">
          <div className="body-serif space-y-4 text-ink">
            <p>
              Stage One constructs an independent player board of 727
              prospects, scored from factual inputs only: PFF 3-year tape
              grades, RAS athletic composite scores, official combine and
              senior-bowl invitations, publicly reported team visits,
              medical flags, age, and conference tier.
            </p>
            <p>
              Where a player has a live Kalshi pick-position market
              (over/under contracts of the form <em>"Will X be drafted
              before pick N.5?"</em>), the market-implied P50 is used as
              the primary anchor for that player's grade. Players without
              market coverage fall through to a blended signal: PFF
              grade-to-pick interpolation (55%) plus the Stage-1 ensemble
              prediction shrunk toward positional historical averages.
            </p>
            <p>
              The board is then adjusted by reasoning bonuses drawn from
              factual sources only — visit counts, senior-bowl standout
              status, RAS, injury flags, stock direction, position
              scarcity — never from analyst rank.
            </p>
          </div>
          <aside className="border-l border-ink-edge pl-5 space-y-3 text-sm">
            <SmallCaps tight>Inputs</SmallCaps>
            <ul className="space-y-2 body-serif text-sm">
              {[
                'PFF 3-yr grade',
                'RAS athletic composite',
                'Combine / senior-bowl invites',
                'Team-visit counts',
                'Medical flags',
                'Conference tier, age',
                'Kalshi pick-position markets',
              ].map(x => <li key={x} className="flex gap-2"><span className="text-accent-brass">§</span>{x}</li>)}
            </ul>
          </aside>
        </div>
      </section>

      {/* ───── Stage 2 ───── */}
      <section className="space-y-5">
        <div className="flex items-baseline gap-4 pt-2">
          <span className="display-num text-5xl text-accent-brass">02</span>
          <SmallCaps>Stage Two · Team Agents</SmallCaps>
        </div>
        <h2 className="display-broadcast text-ink"
            style={{ fontSize: 'clamp(1.75rem, 3.2vw, 2.5rem)' }}>
          Thirty-two front offices, Monte Carlo.
        </h2>
        <HRule accent />
        <div className="grid grid-cols-1 md:grid-cols-[1fr_260px] gap-8">
          <div className="body-serif space-y-4 text-ink">
            <p>
              Stage Two runs the full draft 100 times. Each of the 32
              teams is modelled as an autonomous agent with its own
              scoring function over the remaining board, walking picks
              1 through 257 in order.
            </p>
            <p>
              A team's fit score for any prospect is a weighted sum of
              best-player-available, roster need (5-tier positional),
              scheme premium, coaching-tree positional bias, cap posture,
              QB urgency, age-cliff triggers, previous-year R1 allocation
              penalty, GM historical affinity, college connection, visit
              signal, and archetype match. The round weights shift as the
              draft progresses — R1 is 75% need / 125% BPA; R4–7 is 35%
              need / 130% BPA — so late-round picks lean upside.
            </p>
            <p>
              Picks are resolved via softmax over the top-10 candidates
              with temperature 0.12, so near-ties split realistically
              across sims. The bilateral-trade module fires when an
              earlier team has structural trade-down motive and a later
              team has trade-up motive and the Fitzgerald chart allows
              compatibility — trades are emergent, not scripted.
            </p>
          </div>
          <aside className="border-l border-ink-edge pl-5 space-y-3 text-sm">
            <SmallCaps tight>Per-team signals</SmallCaps>
            <ul className="space-y-2 body-serif text-sm">
              {[
                'Roster needs (tiered)',
                'Scheme premium',
                'Coaching tree DNA',
                'GM positional affinity',
                'Cap tier',
                'QB urgency score',
                'Historical trade rates',
                'Age-cliff triggers',
                'Official team visits',
              ].map(x => <li key={x} className="flex gap-2"><span className="text-accent-brass">§</span>{x}</li>)}
            </ul>
          </aside>
        </div>
      </section>

      {/* ───── Stage 3 — THE NEW HOOK ───── */}
      <section className="space-y-5 border-l-2 border-accent-brass pl-6 -ml-6">
        <div className="flex items-baseline gap-4 pt-2">
          <span className="display-num text-5xl text-accent-brass">03</span>
          <SmallCaps>Stage Three · Market Calibration</SmallCaps>
          <Stamp variant="brass">Kalshi</Stamp>
        </div>
        <h2 className="display-broadcast text-ink"
            style={{ fontSize: 'clamp(1.75rem, 3.2vw, 2.5rem)' }}>
          Real money, aggregated, as the honesty check.
        </h2>
        <HRule accent />
        <div className="body-serif space-y-4 text-ink">
          <p>
            The third stage is the differentiator. Every simulated pick
            is calibrated against Kalshi — a CFTC-regulated event-contract
            exchange where traders buy YES or NO on specific draft
            outcomes. We pull <span className="font-mono font-semibold text-accent-brass">1,909
            markets</span> across the 2026 draft series at runtime,
            including pick-position over/unders, top-3 / top-5 / top-10
            / top-32 threshold contracts, per-pick exact-outcome markets,
            per-position rank markets (<em>"Will Player X be the
            Nth QB drafted?"</em>), and per-team landing markets
            (<em>"Will Player X be drafted by Team Y?"</em>).
          </p>
          <p>
            Each Kalshi market type is parsed into the model's posterior.
            The team-landing signal becomes a <span className="font-mono font-semibold">+5× additive fit
            bonus</span> during the Monte Carlo, gated at 3% above uniform
            noise floor so only meaningful market priors contribute. The
            pick-slot P10–P90 band contributes a slot-alignment bonus so
            the sim places prospects within their market-implied range.
            After the sim, the <span className="font-mono font-semibold">odds_clamp</span> post-
            processor snaps any pick outside its P10–P90 band back to the
            market-compatible candidate closest to the slot.
          </p>
          <p>
            The displayed pick probability is a <span className="font-semibold">60% market / 40%
            model</span> Bayesian blend, with a 20% epistemic discount on
            the model side (our sim can't observe medical news, war-room
            reads, or late trade talks), a further 10% world-uncertainty
            haircut applied after blending, and a hard ceiling of 78% —
            nothing about the draft is truly certain.
          </p>
        </div>
        <FigureCaption>
          Figure · The calibration layer. Raw sim frequency → blended
          with market-implied landing → haircut for real-world unknowns →
          final displayed probability.
        </FigureCaption>
      </section>

      {/* ───── Probability math ───── */}
      <section className="space-y-5">
        <div className="flex items-baseline gap-4 pt-2">
          <span className="display-num text-5xl text-accent-brass">04</span>
          <SmallCaps>Calibration · The Number You See</SmallCaps>
        </div>
        <h2 className="display-broadcast text-ink"
            style={{ fontSize: 'clamp(1.75rem, 3.2vw, 2.5rem)' }}>
          What the probability actually represents.
        </h2>
        <HRule accent />
        <div className="body-serif space-y-4 text-ink">
          <p>
            The probability next to each pick is the model's belief that{' '}
            <em>this specific team drafts this specific player at this
            specific slot</em>. Not the probability a player is picked
            at this slot by anyone, and not just the market odds. It
            decomposes as:
          </p>
        </div>

        {/* The formula block — rendered as a mono calloutish box */}
        <div className="border-y-2 border-ink py-6 px-4 md:px-8 bg-paper-raised">
          <pre className="font-mono text-sm md:text-base text-ink-soft whitespace-pre-wrap leading-relaxed">
{`P(team X picks player Y at slot N) =

  ┌─  model_prior   = raw_sim_freq × (1 − 0.20 − 0.005·max(0, N−5))
  │                    clipped to [0, 0.88]
  │
  ├─  market_prior  = Kalshi team-landing(Y, X) × slot_share(Y, X, N)
  │                    where slot_share distributes across X's R1 picks
  │                    weighted by inverse distance to Y's market P50
  │
  ├─  blended       = 0.60 · market_prior  +  0.40 · model_prior
  │
  ├─  world_haircut = 0.10 + 0.006·max(0, N−10) + 0.03·[N>20]
  │
  └─  DISPLAYED     = min(0.78, blended × (1 − world_haircut))`}
          </pre>
        </div>
        <FigureCaption>
          Posterior probability decomposition. All constants calibrated
          against 2024 and 2025 R1 hit rates.
        </FigureCaption>
      </section>

      {/* ───── Contract ───── */}
      <section className="space-y-5">
        <div className="flex items-baseline gap-4 pt-2">
          <span className="display-num text-5xl text-accent-brass">05</span>
          <SmallCaps>The Contract</SmallCaps>
        </div>
        <h2 className="display-broadcast text-ink"
            style={{ fontSize: 'clamp(1.75rem, 3.2vw, 2.5rem)' }}>
          How we keep the model honest.
        </h2>
        <HRule accent />
        <div className="body-serif space-y-4 text-ink">
          <p>
            A pytest suite enforces the <em>independence contract</em>: any
            analyst-rank column (<code className="font-mono text-sm px-1 bg-paper-hover">consensus_rank</code>,{' '}
            <code className="font-mono text-sm px-1 bg-paper-hover">pff_rank</code>,{' '}
            <code className="font-mono text-sm px-1 bg-paper-hover">kiper_rank</code>,{' '}
            <code className="font-mono text-sm px-1 bg-paper-hover">mcshay_rank</code>)
            touching the modelling pipeline fails the build. Eight tests pass on every
            commit. Kalshi market data is allowed because it is factual
            price data — not analyst opinion — aggregated across many
            independent traders.
          </p>
          <p>
            The product goal is <em>organic convergence</em>: if the model,
            fed only tape and traits and priced against live markets,
            lands at the same place as analyst consensus, that's a sign
            both are correctly modelling the same underlying team
            behaviour. Where it diverges, it's a signal to enrich the
            team profiles — never to loosen the contract.
          </p>
        </div>
      </section>

      {/* ───── Calibration buckets ───── */}
      <section className="space-y-5">
        <div className="flex items-baseline gap-4 pt-2">
          <span className="display-num text-5xl text-accent-brass">06</span>
          <SmallCaps>Historical Accuracy · Confidence Buckets</SmallCaps>
        </div>
        <h2 className="display-broadcast text-ink"
            style={{ fontSize: 'clamp(1.75rem, 3.2vw, 2.5rem)' }}>
          What the confidence labels empirically mean.
        </h2>
        <HRule accent />
        <p className="body-serif text-ink">
          Confidence labels are calibrated against the 2024 and 2025 R1
          drafts (n = 64 modal picks). For each pre-draft probability
          bucket, we measured the rate at which the modal pick actually
          hit.
        </p>
        <div className="overflow-x-auto">
          <table className="research-table">
            <thead>
              <tr>
                <th>Bucket</th>
                <th className="num">Threshold</th>
                <th className="num">2024–25 hit rate</th>
                <th>Example pick</th>
              </tr>
            </thead>
            <tbody>
              <tr><td><span className="caps-tight text-signal-pos">High</span></td>
                  <td className="num">≥ 0.55</td><td className="num">85%+</td>
                  <td className="font-serif italic text-sm">Caleb Williams, #1 2024</td></tr>
              <tr><td><span className="caps-tight">Moderate-High</span></td>
                  <td className="num">0.40 – 0.55</td><td className="num">~65%</td>
                  <td className="font-serif italic text-sm">Jayden Daniels, #2 2024</td></tr>
              <tr><td><span className="caps-tight">Moderate-Low</span></td>
                  <td className="num">0.25 – 0.40</td><td className="num">~45%</td>
                  <td className="font-serif italic text-sm">Drake Maye, #3 2024</td></tr>
              <tr><td><span className="caps-tight text-signal-neg">Low</span></td>
                  <td className="num">&lt; 0.25</td><td className="num">~20%</td>
                  <td className="font-serif italic text-sm">Coin flips — late R1</td></tr>
            </tbody>
          </table>
        </div>
        <FigureCaption>
          Figure · Hit rates by pre-draft probability bucket. Full calibration data in{' '}
          <code className="font-mono">confidence_calibration_2024_2025.json</code>.
        </FigureCaption>
      </section>

      {/* ───── Limitations ───── */}
      <section className="space-y-4 pt-2">
        <SmallCaps>Limitations & Known Unknowns</SmallCaps>
        <HRule />
        <ul className="space-y-3 body-serif text-ink">
          <li className="flex gap-3">
            <span className="text-accent-brass shrink-0 font-mono">·</span>
            <span>
              The model has no access to private team intel, medical
              updates past the combine, locker-room conversations, or
              last-minute trade-call dynamics. The world-uncertainty
              haircut is the acknowledgement.
            </span>
          </li>
          <li className="flex gap-3">
            <span className="text-accent-brass shrink-0 font-mono">·</span>
            <span>
              Kalshi market coverage is deepest for the top ~25 prospects.
              Mid-to-late-round picks fall back to sim-frequency with
              epistemic discount.
            </span>
          </li>
          <li className="flex gap-3">
            <span className="text-accent-brass shrink-0 font-mono">·</span>
            <span>
              The trade module is structural, not opportunistic — it
              fires when capital, need, and tier scarcity align, but
              doesn't model specific reported trade rumours.
            </span>
          </li>
        </ul>
      </section>

      {/* Footer notes */}
      <section className="pt-4 space-y-3 border-t border-ink">
        <SmallCaps>Colophon</SmallCaps>
        <Footnote>
          Built in Python (FastAPI, pandas, scikit-learn, lightgbm) and
          React 19 (Vite, Tailwind). Live odds via Kalshi API. Deployed
          on Render. Source at{' '}
          <a href="https://github.com/ColinSica/nfl-draft-2026" target="_blank" rel="noopener"
             className="text-accent-brass underline underline-offset-2">
            github.com/ColinSica/nfl-draft-2026
          </a>.
        </Footnote>
      </section>
    </div>
  );
}
