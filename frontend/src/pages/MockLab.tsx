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
import { RotateCcw, Lock, Unlock } from 'lucide-react';

// Positions we let the user tweak. Mirrors team_fit canonical codes.
const POSITIONS = ['QB','RB','WR','TE','OT','IOL','EDGE','DL','IDL','LB','CB','S'] as const;
type Pos = typeof POSITIONS[number];

type ForcedPick = { slot: number; player: string };

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

  // User-forced picks — clicking "lock" at a slot pins a player.
  const [forced, setForced] = useState<ForcedPick[]>([]);

  useEffect(() => {
    api.prospectLandings()
      .then(r => setRows(r.prospects))
      .catch(e => setErr(String(e)));
    api.latestSim()
      .then(r => setBaseline(r.picks))
      .catch(() => setBaseline([]));
  }, []);

  const adjustedR1 = useMemo(
    () => recomputeR1(rows ?? [], baseline ?? [], demand, forced),
    [rows, baseline, demand, forced],
  );

  const resetKnobs = () => {
    const o: Record<string, number> = {};
    POSITIONS.forEach(p => { o[p] = 1.0; });
    setDemand(o); setForced([]);
  };

  const anyAdjusted =
    forced.length > 0 ||
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
              Baseline is 1.00 per position. Raise a slider to increase
              demand; lower to suppress. The mock re-allocates slots
              proportionally to adjusted landing weights.
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
          <div className="flex items-baseline justify-between gap-4 mb-4">
            <div>
              <SmallCaps>Adjusted Mock · First Round</SmallCaps>
              <p className="mono-label mt-1">
                {anyAdjusted ? 'Recomputed with active adjustments' : 'Baseline — no adjustments'}
              </p>
            </div>
            {!rows && <p className="caps-tight text-ink-muted">Loading…</p>}
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
                    <th className="center">Lock</th>
                  </tr>
                </thead>
                <tbody>
                  {adjustedR1.map(pick => {
                    const locked = forced.some(f => f.slot === pick.slot);
                    return (
                      <tr key={pick.slot}>
                        <td className="num text-ink-muted">{pick.slot}</td>
                        <td className="font-mono text-xs font-medium">{pick.team ?? '—'}</td>
                        <td className="font-serif">
                          {pick.player}
                          {pick.wasChanged && (
                            <span className="ml-2 inline-block w-2 h-2 bg-accent-brass"
                                  title="Changed from baseline" />
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

function recomputeR1(
  rows: ProspectRow[],
  baseline: PickRow[],
  demand: Record<string, number>,
  forced: ForcedPick[],
): AdjustedPick[] {
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

  // Baseline (demand=1, no locks) for Δ reporting.
  const base = greedyAssign(
    entries.map(e => ({
      ...e,
      w: e.w / (demand[normalizePos(e.position ?? '') as Pos] ?? 1.0),
    })),
    [],
    canonicalBySlot,
  );
  const baseMap = new Map(base.map(b => [b.slot, b]));

  // With adjustments + forced picks.
  const adjusted = greedyAssign(entries, forced, canonicalBySlot);

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
  canonicalBySlot: Map<number, { slot: number; team: string | null; player: string | null; position: string | null; college: string | null; probability: number }>,
): Array<{
  slot: number; team: string | null; player: string | null;
  position: string | null; college: string | null; probability: number;
}> {
  // Per-slot map of candidates
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

    // Prefer the canonical baseline pick if it exists and isn't claimed —
    // this is what the site shows by default, so the Mock Lab shouldn't
    // silently diverge from it when no user adjustments have been made.
    // Apply positional demand as a multiplicative nudge only if the MC
    // landing for this canonical pick is competitive; otherwise keep it.
    const top = arr.find(x => !claimed.has(x.player));

    // If we have a canonical pick AND no MC landing disagrees AND no
    // adjustment has moved a stronger candidate here, use canonical.
    if (canonical?.player && !claimed.has(canonical.player)) {
      const topOverrides = top && (top.p ?? 0) > 0.55 && top.player !== canonical.player;
      if (!topOverrides) {
        claimed.add(canonical.player);
        out.push({ ...canonical });
        continue;
      }
    }

    if (!top) {
      // No MC landing AND no canonical — genuine empty slot (shouldn't happen).
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
