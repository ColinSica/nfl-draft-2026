/**
 * Compare — slot-by-slot Independent vs Benchmark (analyst consensus).
 * Shows overlap, divergence, and which side the market falls on.
 */
import { useEffect, useMemo, useState } from 'react';
import { api, type PickRow } from '../lib/api';
import { teamColor } from '../lib/teamColors';
import { SectionHeader, SmallCaps } from '../components/editorial';

export function Compare() {
  const [indePicks, setIndePicks] = useState<PickRow[] | null>(null);
  const [consensus, setConsensus] = useState<any>(null);

  useEffect(() => {
    api.latestSim().then(r => setIndePicks(r.picks)).catch(() => setIndePicks([]));
    api.analystConsensus().then(setConsensus).catch(() => setConsensus(null));
  }, []);

  const rows = useMemo(() => {
    if (!indePicks) return [];
    return indePicks
      .filter(p => p.pick_number <= 32)
      .sort((a, b) => a.pick_number - b.pick_number)
      .map(p => {
        const pri = p.candidates?.[0];
        const slot = p.pick_number;
        const cons = consensus?.per_pick?.[String(slot)] ?? {};
        return {
          slot,
          team: p.most_likely_team ?? p.team ?? '—',
          indPlayer: pri?.player ?? '—',
          indPos: pri?.position ?? '',
          indProb: pri?.probability ?? 0,
          benchPlayer: cons?.consensus_tier1 ?? cons?.consensus_player ?? '—',
          benchTeam: cons?.team ?? (p.most_likely_team ?? p.team),
        };
      });
  }, [indePicks, consensus]);

  const agreements = rows.filter(r => r.indPlayer && r.benchPlayer && r.indPlayer.split(' ').pop() === r.benchPlayer?.split(' ').pop()).length;

  return (
    <div className="space-y-10 pb-16">
      <SectionHeader
        kicker="Compare"
        title="Independent vs Benchmark."
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Stat label="Slot agreement" value={`${agreements}/32`} note="Exact player at slot" />
        <Stat label="Independent accent" value="Yellow" note="Our model (no analyst inputs)" accent="#D9A400" />
        <Stat label="Benchmark accent" value="Blue" note="Analyst consensus baseline" accent="#1F6FEB" />
      </div>

      {!indePicks ? (
        <div className="card p-10 text-center text-ink-soft italic">Loading comparison…</div>
      ) : (
        <div className="card">
          <header className="grid grid-cols-[60px_1fr_1fr_80px] gap-2 px-4 py-3 border-b-2 border-ink-edge">
            <SmallCaps tight className="text-ink-soft">Slot</SmallCaps>
            <SmallCaps tight style={{ color: '#D9A400' }}>Independent</SmallCaps>
            <SmallCaps tight style={{ color: '#1F6FEB' }}>Benchmark</SmallCaps>
            <SmallCaps tight className="text-ink-soft text-right">Diff</SmallCaps>
          </header>
          <div>
            {rows.map(r => {
              const tc = teamColor(r.team);
              const match = r.indPlayer && r.benchPlayer
                && r.indPlayer.split(' ').pop() === r.benchPlayer?.split(' ').pop();
              return (
                <div
                  key={r.slot}
                  className="grid grid-cols-[60px_1fr_1fr_80px] gap-2 px-4 py-3 border-b border-ink-edge last:border-b-0 items-baseline"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="w-1.5 self-stretch rounded"
                      style={{ background: tc.primary, minHeight: '1.5rem' }}
                    />
                    <span className="display-num text-xl text-ink">{r.slot}</span>
                  </div>
                  <div>
                    <div className="display-broadcast text-base text-ink leading-tight">
                      {r.indPlayer?.toUpperCase?.() ?? '—'}
                    </div>
                    <div className="text-[0.65rem] font-mono text-ink-soft mt-0.5">
                      {r.indPos} · {r.team} · {Math.round(r.indProb * 100)}%
                    </div>
                  </div>
                  <div>
                    <div className="display-broadcast text-base text-ink leading-tight">
                      {typeof r.benchPlayer === 'string' ? r.benchPlayer.toUpperCase() : '—'}
                    </div>
                    {r.benchTeam && r.benchTeam !== r.team && (
                      <div className="text-[0.65rem] font-mono text-ink-soft mt-0.5">
                        to {r.benchTeam}
                      </div>
                    )}
                  </div>
                  <div className="text-right">
                    <span
                      className="caps-tight px-2 py-0.5"
                      style={{
                        color: match ? '#17A870' : '#DC2F3D',
                        background: match ? 'rgba(23,168,112,0.1)' : 'rgba(220,47,61,0.08)',
                      }}
                    >
                      {match ? 'Match' : 'Diff'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <p className="text-xs text-ink-soft italic">
        Benchmark source: aggregate of public analyst mocks. Independent model does not use
        any analyst pick data as input — matches above are organic convergence.
      </p>
    </div>
  );
}

function Stat({
  label, value, note, accent,
}: { label: string; value: string; note: string; accent?: string }) {
  return (
    <div className="card p-5 space-y-1">
      <SmallCaps tight className="text-ink-soft block">{label}</SmallCaps>
      <div className="display-num text-4xl text-ink" style={accent ? { color: accent } : undefined}>
        {value}
      </div>
      <div className="text-xs text-ink-soft">{note}</div>
    </div>
  );
}
