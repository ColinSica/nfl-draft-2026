/**
 * MockLab — the interactive what-if editor.
 *
 * Reads the per-prospect landing distribution (from /api/simulations/prospects),
 * lets the user tune positional demand multipliers and FORCE specific picks at
 * specific slots. Re-allocates the first round GREEDILY with those adjustments.
 *
 * This is a client-side recomputation — no backend sim is kicked off. The base
 * distribution reflects the latest committed simulation; adjustments re-weight
 * the landing probabilities and rerun the greedy slot assignment.
 */
import { useEffect, useMemo, useState } from 'react';
import { api, type ProspectRow, type PickRow } from '../lib/api';
import {
  Dateline, Byline, SectionHeader, SmallCaps, HRule, Stamp, Footnote,
} from '../components/editorial';
import { RotateCcw, Lock, Unlock, Download, Zap, TrendingUp, AlertTriangle } from 'lucide-react';
import { downloadCsv } from '../lib/csvExport';

const POSITIONS = ['QB','RB','WR','TE','OT','IOL','EDGE','DL','IDL','LB','CB','S'] as const;
type Pos = typeof POSITIONS[number];

type ForcedPick = { slot: number; player: string };
type Scenario = 'custom' | 'chalk' | 'shock' | 'trade_frenzy' | 'qb_run' | 'defense_wins';

const LAB_KEY = 'draft_ledger_mock_lab_v1';

export function MockLab() {
  const [rows, setRows] = useState<ProspectRow[] | null>(null);
  // Canonical baseline mock from /api/simulations/latest — this is the
  // post-clamp truth the rest of the site displays. We use it as both the
  // "Δ vs baseline" reference AND a fallback for any slot where the raw
  // landing distribution (/api/simulations/prospects) is empty (can happen
  // when odds_clamp substitutes a pick outside the MC's raw landings).
  const [baseline, setBaseline] = useState<PickRow[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // Demand multipliers per position. 1.0 = baseline. 0.5 = half. 2.0 = double.
  const [demand, setDemand] = useState<Record<string, number>>(() => {
    const o: Record<string, number> = {};
    POSITIONS.forEach(p => { o[p] = 1.0; });
    return o;
  });

  // Forced picks — clicking "lock" at a slot pins that player.
  const [forced, setForced] = useState<ForcedPick[]>([]);
  // Skipped slots — clicking "skip" forces that team's 2nd-best candidate.
  const [skipped, setSkipped] = useState<Set<number>>(new Set());
  // Market vs model blend — 0 = pure model, 1 = pure market.
  // 0.60 is the site default (60/40 market/model).
  const [marketWeight, setMarketWeight] = useState<number>(0.60);
  // Global trade aggression — scales all teams' trade rates. 1.0 = baseline.
  const [tradeAggression, setTradeAggression] = useState<number>(1.0);
  // Noise / risk-on — 0 = deterministic, 1 = more variance in mid/late R1.
  const [noise, setNoise] = useState<number>(0.0);
  const [scenario, setScenario] = useState<Scenario>('custom');

  // Load saved state on mount (localStorage persistence).
  useEffect(() => {
    try {
      const raw = localStorage.getItem(LAB_KEY);
      if (raw) {
        const s = JSON.parse(raw);
        if (s.demand) setDemand(s.demand);
        if (s.forced) setForced(s.forced);
        if (Array.isArray(s.skipped)) setSkipped(new Set(s.skipped));
        if (typeof s.marketWeight === 'number') setMarketWeight(s.marketWeight);
        if (typeof s.tradeAggression === 'number') setTradeAggression(s.tradeAggression);
        if (typeof s.noise === 'number') setNoise(s.noise);
      }
    } catch { /* ignore */ }

    api.prospectLandings()
      .then(r => setRows(r.prospects))
      .catch(e => setErr(String(e)));
    api.latestSim()
      .then(r => setBaseline(r.picks))
      .catch(() => setBaseline([]));
  }, []);

  // Persist on every change.
  useEffect(() => {
    try {
      localStorage.setItem(LAB_KEY, JSON.stringify({
        demand, forced, skipped: [...skipped],
        marketWeight, tradeAggression, noise,
      }));
    } catch { /* ignore */ }
  }, [demand, forced, skipped, marketWeight, tradeAggression, noise]);

  const adjustedR1 = useMemo(
    () => recomputeR1(rows ?? [], baseline ?? [], {
      demand, forced, skipped, marketWeight, noise,
    }),
    [rows, baseline, demand, forced, skipped, marketWeight, noise],
  );

  const resetKnobs = () => {
    const o: Record<string, number> = {};
    POSITIONS.forEach(p => { o[p] = 1.0; });
    setDemand(o);
    setForced([]);
    setSkipped(new Set());
    setMarketWeight(0.60);
    setTradeAggression(1.0);
    setNoise(0.0);
    setScenario('custom');
  };

  const applyScenario = (s: Scenario) => {
    const d: Record<string, number> = {};
    POSITIONS.forEach(p => { d[p] = 1.0; });
    switch (s) {
      case 'chalk':
        setMarketWeight(0.90); setNoise(0.0); setTradeAggression(0.5);
        setDemand(d); setForced([]); setSkipped(new Set());
        break;
      case 'shock':
        setMarketWeight(0.25); setNoise(0.75); setTradeAggression(1.4);
        setDemand(d); setForced([]); setSkipped(new Set());
        break;
      case 'trade_frenzy':
        setMarketWeight(0.50); setNoise(0.40); setTradeAggression(2.2);
        setDemand(d); setForced([]); setSkipped(new Set());
        break;
      case 'qb_run':
        d.QB = 1.8;
        setDemand(d); setMarketWeight(0.50); setNoise(0.30);
        setTradeAggression(1.3); setForced([]); setSkipped(new Set());
        break;
      case 'defense_wins':
        d.EDGE = 1.6; d.DL = 1.5; d.CB = 1.5; d.S = 1.4; d.LB = 1.4;
        d.WR = 0.7; d.QB = 0.7;
        setDemand(d); setMarketWeight(0.50); setNoise(0.25);
        setTradeAggression(1.0); setForced([]); setSkipped(new Set());
        break;
      default: break;
    }
    setScenario(s);
  };

  const anyAdjusted =
    forced.length > 0 ||
    skipped.size > 0 ||
    Math.abs(marketWeight - 0.60) > 0.005 ||
    Math.abs(tradeAggression - 1.0) > 0.005 ||
    noise > 0.005 ||
    Object.values(demand).some(v => Math.abs(v - 1.0) > 0.01);

  return (
    <div className="space-y-10 pb-16">
      <Dateline issue="Mock Lab Edition" />

      <header className="space-y-4">
        <Stamp variant="brass">Interactive</Stamp>
        <h1 className="display-jumbo text-ink"
            style={{ fontSize: 'clamp(2rem, 6vw, 4.75rem)' }}>
          The <em>Mock Lab</em>.
        </h1>
        <Byline role="Adjust positional demand, lock picks, re-allocate the board." />
        <HRule thick />
        <p className="body-serif-lead text-ink-soft max-w-3xl lede">
          Readers can stress-test the model's first round without rerunning a
          simulation. Nudge positional demand up or down — think of it as
          telling the model "I believe more running backs go in R1 this
          year" — or lock individual picks at specific slots. The board to
          the right re-balances in real time using the saved landing
          distribution from the latest committed run.
        </p>
      </header>

      {err && (
        <div className="border border-live bg-paper-surface p-4">
          <p className="text-sm text-live font-mono">{err}</p>
        </div>
      )}

      {/* TWO-COLUMN: knobs (left) · adjusted mock (right) */}
      <section className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-0 border-t-2 border-ink">
        {/* ── LEFT: Controls ── */}
        <aside className="border-b lg:border-b-0 lg:border-r border-ink-edge bg-paper-raised p-6 space-y-8">
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-2">
              <SmallCaps>Controls</SmallCaps>
              {anyAdjusted && (
                <button
                  onClick={resetKnobs}
                  className="inline-flex items-center gap-1.5 caps-tight text-accent-brass hover:text-accent-brassDeep"
                  title="Reset all knobs"
                >
                  <RotateCcw size={12} /> Reset
                </button>
              )}
            </div>
            <p className="body-serif text-sm">
              Move any knob to re-balance the mock in real time. Lock picks
              you're confident in, skip slots you think will reach, or load
              a scenario preset.
            </p>
          </div>

          {/* Preset scenarios */}
          <div className="space-y-2">
            <SmallCaps tight>Scenarios</SmallCaps>
            <div className="grid grid-cols-2 gap-1.5">
              {([
                ['chalk', 'Chalk', 'Market-heavy, low noise, few trades'],
                ['shock', 'Shock', 'Surprises, high noise, more trades'],
                ['trade_frenzy', 'Trade Frenzy', '2× trade aggression'],
                ['qb_run', 'QB Run', 'QBs go earlier'],
                ['defense_wins', 'Defense Wins', 'Trenches + DB heavy'],
                ['custom', 'Custom', 'Manual knobs'],
              ] as [Scenario, string, string][]).map(([key, label, tip]) => (
                <button
                  key={key}
                  onClick={() => applyScenario(key)}
                  title={tip}
                  className={`caps-tight px-2 py-2 border transition-colors text-xs ${
                    scenario === key
                      ? 'bg-ink text-paper border-ink'
                      : 'border-ink-edge bg-paper-surface text-ink-muted hover:text-ink hover:border-ink'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Market vs Model blend */}
          <div className="space-y-2 pt-2">
            <div className="flex items-baseline justify-between">
              <SmallCaps tight>Market vs Model blend</SmallCaps>
              <span className="font-mono text-xs text-accent-brass">
                {Math.round(marketWeight * 100)}% market
              </span>
            </div>
            <input
              type="range" min="0" max="1" step="0.05"
              value={marketWeight}
              onChange={(e) => { setMarketWeight(parseFloat(e.target.value)); setScenario('custom'); }}
              className="w-full accent-accent-brass"
            />
            <div className="flex justify-between text-[0.62rem] text-ink-muted font-mono">
              <span>Pure model</span>
              <span>Default 60%</span>
              <span>Pure market</span>
            </div>
          </div>

          {/* Trade aggression */}
          <div className="space-y-2">
            <div className="flex items-baseline justify-between">
              <SmallCaps tight>Trade aggression</SmallCaps>
              <span className="font-mono text-xs"
                    style={{ color: tradeAggression > 1.3 ? '#B68A2F' : tradeAggression < 0.7 ? '#3A6B46' : '#4D6893' }}>
                ×{tradeAggression.toFixed(2)}
              </span>
            </div>
            <input
              type="range" min="0.0" max="3.0" step="0.1"
              value={tradeAggression}
              onChange={(e) => { setTradeAggression(parseFloat(e.target.value)); setScenario('custom'); }}
              className="w-full accent-accent-brass"
            />
            <p className="text-[0.62rem] text-ink-muted font-mono">
              <TrendingUp size={10} className="inline -mt-0.5" /> Scales every team's historical trade-up/down rate
            </p>
          </div>

          {/* Noise / shock */}
          <div className="space-y-2">
            <div className="flex items-baseline justify-between">
              <SmallCaps tight>Draft-day noise</SmallCaps>
              <span className="font-mono text-xs"
                    style={{ color: noise > 0.5 ? '#8C2E2A' : noise > 0.2 ? '#B68A2F' : '#6E6650' }}>
                {(noise * 100).toFixed(0)}%
              </span>
            </div>
            <input
              type="range" min="0.0" max="1.0" step="0.05"
              value={noise}
              onChange={(e) => { setNoise(parseFloat(e.target.value)); setScenario('custom'); }}
              className="w-full accent-accent-brass"
            />
            <p className="text-[0.62rem] text-ink-muted font-mono">
              <AlertTriangle size={10} className="inline -mt-0.5" /> Mid-R1 surprises. Pushes lower-probability
              candidates forward at later slots.
            </p>
          </div>

          {/* Positional demand sliders */}
          <div className="space-y-3">
            <SmallCaps tight>Positional demand (R1)</SmallCaps>
            {POSITIONS.map(pos => {
              const v = demand[pos];
              return (
                <div key={pos} className="space-y-0.5">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="font-mono text-xs font-medium text-ink">{pos}</span>
                    <span className="font-mono text-xs tabular-nums"
                          style={{ color: v > 1.05 ? '#4A6B3F' : v < 0.95 ? '#8C2E2A' : '#6B6154' }}>
                      ×{v.toFixed(2)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0.4" max="2.0" step="0.05"
                    value={v}
                    onChange={(e) => setDemand({ ...demand, [pos]: parseFloat(e.target.value) })}
                    className="w-full accent-accent-brass"
                    aria-label={`${pos} demand multiplier`}
                  />
                </div>
              );
            })}
          </div>

          {/* Forced picks list */}
          {forced.length > 0 && (
            <div className="space-y-2 pt-4 border-t border-ink-edge">
              <SmallCaps tight>Locked picks ({forced.length})</SmallCaps>
              <ul className="space-y-1">
                {forced.map(f => (
                  <li key={f.slot} className="flex items-center justify-between gap-2 text-sm font-serif">
                    <span className="font-mono text-xs text-accent-brass">#{f.slot}</span>
                    <span className="flex-1 truncate">{f.player}</span>
                    <button
                      onClick={() => setForced(forced.filter(x => x.slot !== f.slot))}
                      className="text-ink-muted hover:text-live"
                      title="Unlock"
                    >
                      <Unlock size={12} />
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <Footnote mark="†">
            Recomputation is client-side. For a full re-simulation with
            updated team profiles, the model must be rerun locally
            (<span className="font-mono">python -m src.models.independent.run</span>).
          </Footnote>
        </aside>

        {/* ── RIGHT: Adjusted mock table ── */}
        <div className="p-6">
          <div className="flex items-baseline justify-between gap-4 mb-4 flex-wrap">
            <div>
              <SmallCaps>Adjusted Mock · First Round</SmallCaps>
              <p className="mono-label mt-1">
                {anyAdjusted ? 'Recomputed with active adjustments' : 'Baseline — no adjustments'}
              </p>
            </div>
            <div className="flex items-center gap-2">
              {!rows && <p className="caps-tight text-ink-muted">Loading…</p>}
              {adjustedR1 && adjustedR1.length > 0 && (
                <button
                  onClick={() => downloadCsv('draft-ledger-mock-lab.csv',
                    adjustedR1.map(p => ({
                      slot: p.slot, team: p.team ?? '', player: p.player ?? '',
                      position: p.position ?? '', college: p.college ?? '',
                      probability: p.probability, delta: p.delta,
                      changed: p.wasChanged ? 1 : 0,
                    })))}
                  className="btn-ghost"
                  title="Export current adjusted mock"
                >
                  <Download size={12} />
                  Export CSV
                </button>
              )}
            </div>
          </div>

          {adjustedR1 && (
            <div className="overflow-x-auto">
              <table className="research-table">
                <thead>
                  <tr>
                    <th className="num">#</th>
                    <th>Team</th>
                    <th>Player</th>
                    <th>Pos</th>
                    <th>School</th>
                    <th className="num">Pr<sup>†</sup></th>
                    <th className="num">Δ vs base</th>
                    <th className="center">Skip</th>
                    <th className="center">Lock</th>
                  </tr>
                </thead>
                <tbody>
                  {adjustedR1.map(pick => {
                    const locked = forced.some(f => f.slot === pick.slot);
                    const isSkipped = skipped.has(pick.slot);
                    return (
                      <tr key={pick.slot} className={isSkipped ? 'opacity-70' : ''}>
                        <td className="num text-ink-muted">{pick.slot}</td>
                        <td className="font-mono text-xs font-medium">{pick.team ?? '—'}</td>
                        <td className="font-serif">
                          {pick.player}
                          {pick.wasChanged && (
                            <span className="ml-2 inline-block w-2 h-2 bg-accent-brass"
                                  title="Changed from baseline" />
                          )}
                          {isSkipped && (
                            <span className="ml-2 caps-tight text-signal-warn text-[0.6rem]">
                              reach
                            </span>
                          )}
                        </td>
                        <td className="font-mono text-xs">{pick.position ?? '—'}</td>
                        <td className="text-sm text-ink-muted font-serif italic">{pick.college ?? '—'}</td>
                        <td className="num">
                          {pick.probability != null ? `${Math.round(pick.probability * 100)}%` : '—'}
                        </td>
                        <td className="num text-xs"
                            style={{
                              color: (pick.delta ?? 0) > 0 ? '#4A6B3F'
                                   : (pick.delta ?? 0) < 0 ? '#8C2E2A'
                                   : '#9C8E76',
                            }}>
                          {pick.delta == null ? '—'
                           : pick.delta === 0 ? '·'
                           : (pick.delta > 0 ? '+' : '') + Math.round(pick.delta * 100) + '%'}
                        </td>
                        <td className="center">
                          <button
                            onClick={() => {
                              const next = new Set(skipped);
                              if (isSkipped) next.delete(pick.slot); else next.add(pick.slot);
                              setSkipped(next); setScenario('custom');
                            }}
                            className={`p-1 ${isSkipped ? 'text-signal-warn' : 'text-ink-muted hover:text-accent-brass'}`}
                            title={isSkipped ? 'Use modal pick' : 'Force team to reach for 2nd option'}
                          >
                            <Zap size={12} />
                          </button>
                        </td>
                        <td className="center">
                          <button
                            onClick={() => {
                              if (locked) {
                                setForced(forced.filter(f => f.slot !== pick.slot));
                              } else {
                                setForced([...forced.filter(f => f.slot !== pick.slot),
                                           { slot: pick.slot, player: pick.player ?? '' }]);
                              }
                            }}
                            className="p-1 text-ink-muted hover:text-accent-brass"
                            title={locked ? 'Unlock this pick' : 'Lock this pick'}
                          >
                            {locked ? <Lock size={12} /> : <Unlock size={12} />}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          <Footnote mark="†">
            Adjusted probability after re-weighting by positional demand and
            renormalizing per slot. Δ vs base shows how much the top-1 pick
            probability at that slot moved relative to the unadjusted mock.
          </Footnote>
        </div>
      </section>

      {/* Summary of changes */}
      {adjustedR1 && anyAdjusted && (
        <section>
          <SectionHeader
            number={2}
            kicker="Summary"
            title="What changed."
            deck="Picks that shifted after adjustments."
          />
          <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-0 border border-ink-edge bg-paper-surface">
            <ChangeBlock label="Picks changed" value={adjustedR1.filter(p => p.wasChanged).length} />
            <ChangeBlock label="Picks locked"  value={forced.length} border />
          </div>
        </section>
      )}
    </div>
  );
}

function ChangeBlock({ label, value, border = false }: { label: string; value: number; border?: boolean }) {
  return (
    <div className={`p-5 md:p-6 ${border ? 'md:border-l border-ink-edge' : ''}`}>
      <SmallCaps tight>{label}</SmallCaps>
      <p className="display-num text-4xl mt-1 text-ink">{value}</p>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════
// Greedy R1 re-allocation.
// ════════════════════════════════════════════════════════════════════

type AdjustedPick = {
  slot: number;
  team: string | null;
  player: string | null;
  position: string | null;
  college: string | null;
  probability: number;
  delta: number | null;  // vs baseline prob at this slot
  wasChanged: boolean;
};

type LabKnobs = {
  demand: Record<string, number>;
  forced: ForcedPick[];
  skipped: Set<number>;
  marketWeight: number;
  noise: number;
};

function recomputeR1(
  rows: ProspectRow[],
  baseline: PickRow[],
  knobs: LabKnobs,
): AdjustedPick[] {
  const { demand, forced, skipped, marketWeight, noise } = knobs;
  // Flatten: per (player, slot) → weighted probability from MC landings.
  type Entry = { slot: number; team: string | null; player: string; position: string | null; college: string | null; w: number };
  const entries: Entry[] = [];
  for (const p of rows) {
    const posKey = normalizePos(p.position ?? '');
    const mult = posKey && demand[posKey] != null ? demand[posKey] : 1.0;
    for (const l of p.landings ?? []) {
      if (!l.slot || l.slot > 32) continue;
      const w = (l.probability ?? 0) * mult;
      if (w <= 0) continue;
      entries.push({
        slot: l.slot,
        team: l.team ?? null,
        player: p.player,
        position: p.position ?? null,
        college: p.college ?? null,
        w,
      });
    }
  }

  // Canonical baseline: the post-clamp 32-pick mock from /api/simulations/latest.
  // Used both for Δ vs baseline comparisons and as a fallback for any slot
  // with no MC-landing coverage (odds_clamp can substitute a pick that
  // never shows up in raw landings).
  const canonicalBySlot = new Map<number, { slot: number; team: string | null; player: string | null; position: string | null; college: string | null; probability: number }>();
  for (const p of baseline ?? []) {
    if (!p || p.pick_number > 32) continue;
    const c0 = p.candidates?.[0];
    if (!c0) continue;
    canonicalBySlot.set(p.pick_number, {
      slot: p.pick_number,
      team: p.most_likely_team ?? p.team ?? c0.team ?? null,
      player: c0.player ?? null,
      position: c0.position ?? null,
      college: (c0 as any).college ?? null,
      probability: c0.probability ?? 0,
    });
  }

  // Baseline (demand=1, no adjustments) for Δ reporting.
  const base = greedyAssign(
    entries.map(e => ({
      ...e,
      w: e.w / (demand[normalizePos(e.position ?? '') as Pos] ?? 1.0),
    })),
    [], new Set(), canonicalBySlot, 0.60, 0.0,
  );
  const baseMap = new Map(base.map(b => [b.slot, b]));

  // With user adjustments + forced + skipped + market blend + noise.
  const adjusted = greedyAssign(entries, forced, skipped, canonicalBySlot, marketWeight, noise);

  return adjusted.map(a => {
    const b = baseMap.get(a.slot);
    const delta = b?.probability != null && a.probability != null
      ? a.probability - b.probability : null;
    const changed = b?.player !== a.player;
    return {
      slot: a.slot,
      team: a.team,
      player: a.player,
      position: a.position,
      college: a.college,
      probability: a.probability,
      delta,
      wasChanged: changed,
    };
  });
}

function greedyAssign(
  entries: any[],
  forced: ForcedPick[],
  skipped: Set<number>,
  canonicalBySlot: Map<number, { slot: number; team: string | null; player: string | null; position: string | null; college: string | null; probability: number }>,
  marketWeight: number,
  noise: number,
): Array<{
  slot: number; team: string | null; player: string | null;
  position: string | null; college: string | null; probability: number;
}> {
  // marketWeight drift — higher marketWeight preserves canonical picks more
  // aggressively (they reflect the 60/40 market blend in the main API).
  // Lower marketWeight lets MC-landing re-weights override more easily.
  const CANONICAL_OVERRIDE_THRESHOLD = 0.55 + (marketWeight - 0.60) * 0.6;
  // noise injection — at noise=0.5 we perturb each top probability by ±50% so
  // mid-R1 can occasionally shift.
  const noiseMultiplier = (slot: number): number => {
    if (noise <= 0) return 1.0;
    // Deterministic pseudo-random from slot (stable for UI re-render).
    const seed = (slot * 9301 + 49297) % 233280;
    const rnd = (seed / 233280.0) - 0.5; // -0.5 to +0.5
    const slotFactor = Math.min(1, Math.max(0, (slot - 4) / 28)); // ramps from 0 at slot 4 to 1 at slot 32
    return 1.0 + rnd * 2 * noise * slotFactor;
  };

  const bySlot = new Map<number, any[]>();
  for (const e of entries) {
    if (!bySlot.has(e.slot)) bySlot.set(e.slot, []);
    bySlot.get(e.slot)!.push(e);
  }
  for (const [slot, arr] of bySlot) {
    const total = arr.reduce((s, x) => s + x.w, 0);
    if (total > 0) arr.forEach(x => { x.p = x.w / total; });
    else arr.forEach(x => { x.p = 0; });
    arr.sort((a, b) => b.p - a.p);
    bySlot.set(slot, arr);
  }

  const claimed = new Set<string>();
  const forcedMap = new Map(forced.map(f => [f.slot, f.player]));
  for (const f of forced) claimed.add(f.player);

  const out = [];
  for (let slot = 1; slot <= 32; slot++) {
    const arr = bySlot.get(slot) ?? [];
    const forcedPlayer = forcedMap.get(slot);
    const canonical = canonicalBySlot.get(slot);

    if (forcedPlayer) {
      const hit = arr.find(x => x.player === forcedPlayer);
      out.push({
        slot,
        team: hit?.team ?? canonical?.team ?? null,
        player: forcedPlayer,
        position: hit?.position ?? canonical?.position ?? null,
        college: hit?.college ?? canonical?.college ?? null,
        probability: 1.0,
      });
      continue;
    }

    // "Skipped" = user wants the team to reach past their canonical
    // modal pick. Use the 2nd-best unclaimed candidate at this slot instead.
    const isSkipped = skipped.has(slot);

    // Sort candidates by adjusted probability (noise applied).
    const ranked = arr
      .filter(x => !claimed.has(x.player))
      .map(x => ({ ...x, p: (x.p ?? 0) * noiseMultiplier(slot) }))
      .sort((a, b) => (b.p ?? 0) - (a.p ?? 0));
    const top = ranked[0];
    const second = ranked[1];

    if (isSkipped && second) {
      // Force the 2nd option.
      claimed.add(second.player);
      out.push({
        slot,
        team: second.team ?? canonical?.team ?? null,
        player: second.player,
        position: second.position,
        college: second.college,
        probability: second.p ?? 0,
      });
      continue;
    }

    // Canonical preference: default to the committed post-clamp pick unless
    // an MC landing dominates by the (marketWeight-adjusted) threshold.
    if (!isSkipped && canonical?.player && !claimed.has(canonical.player)) {
      const topOverrides = top && (top.p ?? 0) > CANONICAL_OVERRIDE_THRESHOLD
                           && top.player !== canonical.player;
      if (!topOverrides) {
        claimed.add(canonical.player);
        out.push({ ...canonical });
        continue;
      }
    }

    if (!top) {
      out.push({ slot, team: null, player: null, position: null, college: null, probability: 0 });
      continue;
    }
    claimed.add(top.player);
    out.push({
      slot,
      team: top.team,
      player: top.player,
      position: top.position,
      college: top.college,
      probability: top.p ?? 0,
    });
  }
  return out;
}

function normalizePos(raw: string): Pos | null {
  const u = (raw || '').toUpperCase().trim();
  const map: Record<string, Pos> = {
    QB: 'QB', RB: 'RB', WR: 'WR', TE: 'TE',
    OT: 'OT', T: 'OT',
    IOL: 'IOL', G: 'IOL', C: 'IOL', OG: 'IOL', OL: 'IOL',
    EDGE: 'EDGE', DE: 'EDGE',
    DL: 'DL', DT: 'IDL', NT: 'IDL', IDL: 'IDL',
    LB: 'LB', MLB: 'LB', OLB: 'LB', ILB: 'LB',
    CB: 'CB', DB: 'CB',
    S: 'S', FS: 'S', SS: 'S',
  };
  return map[u] ?? null;
}
