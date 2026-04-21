/**
 * First round — full 32-pick view of the latest simulation.
 * Each pick card shows team, player, probability, and the model's
 * actual reasoning from the simulations/reasoning endpoint.
 */
import { useEffect, useState } from 'react';
import { api, type PickRow } from '../lib/api';
import { useMode, MODE_META } from '../lib/mode';
import { SectionHeader, HRule } from '../components/editorial';
import { PickCard, type PickData } from '../components/PickCard';
import { FreshnessPanel } from '../components/FreshnessPanel';

export function Simulate() {
  const { mode } = useMode();
  const accent = MODE_META[mode].accent;
  const [picks, setPicks] = useState<PickRow[] | null>(null);
  const [reasoning, setReasoning] = useState<any>(null);
  const [simMeta, setSimMeta] = useState<any>(null);

  useEffect(() => {
    api.latestSim().then(r => {
      setPicks(r.picks);
      setSimMeta(r.meta);
    }).catch(() => setPicks([]));
    fetch('/api/simulations/reasoning')
      .then(r => r.json()).then(setReasoning).catch(() => {});
  }, []);

  const all32: PickData[] = (picks ?? [])
    .filter(p => p.pick_number <= 32)
    .sort((a, b) => a.pick_number - b.pick_number)
    .map(p => {
      const pri = p.candidates?.[0];
      const modelReasoning = reasoning?.picks?.[String(p.pick_number)];
      return {
        slot: p.pick_number,
        team: p.most_likely_team ?? p.team ?? '—',
        player: pri?.player ?? 'Pending',
        position: pri?.position ?? '',
        college: pri?.college ?? null,
        probability: pri?.probability ?? null,
        consensusRank: pri?.consensus_rank ?? null,
        confidence: pri
          ? (pri.probability >= 0.6 ? 'HIGH' : pri.probability >= 0.35 ? 'MEDIUM' : 'LOW')
          : null,
        whySummary: modelReasoning?.reasoning_summary
          ?? `Modal pick at slot ${p.pick_number}.`,
        whyDetail: modelReasoning?.top_factors
          ? (
              <ul className="space-y-1">
                {modelReasoning.top_factors.slice(0, 6).map((f: any, i: number) => (
                  <li key={i}>
                    <span className="font-mono text-xs text-ink-soft/80 mr-2">
                      {typeof f === 'object' && f.weight !== undefined
                        ? `+${Number(f.weight).toFixed(2)}`
                        : '·'}
                    </span>
                    <span>{typeof f === 'object' ? (f.label ?? f.factor ?? '') : String(f)}</span>
                  </li>
                ))}
              </ul>
            )
          : null,
        accent,
      };
    });

  return (
    <div className="space-y-12 pb-16">
      <SectionHeader kicker="Full first round" title="All 32 picks." />

      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-baseline gap-5">
          <div>
            <div className="caps-tight text-ink-soft">Simulations</div>
            <div className="display-num text-3xl text-ink">{simMeta?.n_sims ?? '—'}</div>
          </div>
          <div>
            <div className="caps-tight text-ink-soft">Avg R1 trades</div>
            <div className="display-num text-3xl text-ink">
              {simMeta?.avg_trades?.toFixed?.(1) ?? '—'}
            </div>
          </div>
        </div>
        <span className="ml-auto text-xs text-ink-soft italic">
          Click any pick to expand the model's reasoning.
        </span>
      </div>

      {!picks ? (
        <div className="card p-10 text-center text-ink-soft italic">Loading first round…</div>
      ) : all32.length === 0 ? (
        <div className="card p-10 text-center text-ink-soft italic">No picks available.</div>
      ) : (
        <div className="space-y-3">
          {all32.map((pd, i) => (
            <div key={pd.slot} className="reveal" style={{ animationDelay: `${Math.min(i * 0.02, 0.5)}s` }}>
              <PickCard data={pd} />
            </div>
          ))}
        </div>
      )}

      <HRule />

      <FreshnessPanel
        data={{
          modelRefresh: simMeta?.generated_at ?? null,
          intelRefresh: null,
          simRun: simMeta?.finished_at ?? simMeta?.generated_at ?? null,
        }}
      />
    </div>
  );
}
