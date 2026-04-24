/**
 * AtAGlanceStats — compact visualizations sized for the Home hero's
 * right rail (340px wide). Two blocks:
 *
 *   1. Rank card — big number + percentile + "YOU vs field" mini strip.
 *   2. Hit rate card — progress ring showing your R1 hit rate.
 *
 * Pulls from /api/accuracy.
 */
import { useEffect, useState } from 'react';
import { SmallCaps } from './editorial';

type AnalystRow = {
  name: string;
  exact: number;
  rank: number;
};
type AccuracyResp = {
  r1_picks_drafted: number;
  total_r1_picks: number;
  total_analysts: number;
  analysts: AnalystRow[];
};

export function AtAGlanceStats() {
  const [data, setData] = useState<AccuracyResp | null>(null);

  useEffect(() => {
    fetch('/api/accuracy')
      .then(r => r.ok ? r.json() : null)
      .then(setData)
      .catch(() => {});
  }, []);

  if (!data || data.r1_picks_drafted === 0) return null;
  const colin = data.analysts.find(a => a.name === 'Colin');
  if (!colin) return null;

  const scored = data.r1_picks_drafted;
  const hitPct = scored > 0 ? colin.exact / scored : 0;
  // Percentile: fraction of analysts we beat or tied (higher rank # = worse,
  // so "beat" = fewer exact than you, or same rank)
  const beat = data.analysts.filter(a =>
    a.exact < colin.exact || (a.exact === colin.exact && a.rank >= colin.rank)
  ).length - 1;  // exclude self
  const pct = Math.max(0, Math.round(beat / Math.max(1, data.total_analysts - 1) * 100));

  // Mini strip distribution: sort analysts descending by exact, place Colin
  const sorted = [...data.analysts].sort((a, b) => b.exact - a.exact);
  const maxExact = sorted[0]?.exact ?? 1;

  return (
    <div className="space-y-3">
      <SmallCaps tight>Mock accuracy</SmallCaps>

      {/* Rank card */}
      <div className="border border-ink-edge bg-paper-surface overflow-hidden">
        <div className="flex items-stretch">
          {/* Big rank number */}
          <div className="px-4 py-3 flex flex-col items-center justify-center border-r border-ink-edge"
               style={{ background: 'linear-gradient(135deg, rgba(182,138,47,0.12), rgba(182,138,47,0.02))' }}>
            <span className="caps-tight text-[0.55rem] text-ink-muted mb-0.5">Rank</span>
            <div className="display-num text-4xl leading-none"
                 style={{ color: '#B68A2F' }}>
              #{colin.rank}
            </div>
            <span className="font-mono text-[0.6rem] text-ink-muted mt-0.5">
              of {data.total_analysts}
            </span>
          </div>
          {/* Right column: percentile + hit number */}
          <div className="flex-1 px-3 py-3 flex flex-col justify-between">
            <div>
              <div className="flex items-baseline gap-1.5">
                <span className="display-num text-2xl text-ink">{pct}%</span>
                <span className="caps-tight text-[0.6rem] text-ink-muted">beaten</span>
              </div>
              <div className="mt-1 h-1 bg-paper-hover overflow-hidden">
                <div className="h-full bg-accent-brass"
                     style={{ width: `${pct}%` }} />
              </div>
            </div>
            <div className="flex items-baseline gap-1.5 mt-2">
              <span className="display-num text-xl text-ink">{colin.exact}</span>
              <span className="caps-tight text-[0.6rem] text-ink-muted">
                of {scored} hit
              </span>
            </div>
          </div>
        </div>

        {/* Field strip — each analyst as a thin vertical bar */}
        <div className="border-t border-ink-edge px-3 py-2">
          <div className="flex items-baseline justify-between mb-1.5">
            <SmallCaps tight className="text-ink-muted text-[0.55rem]">
              You vs field
            </SmallCaps>
            <span className="font-mono text-[0.55rem] text-ink-muted">
              left=best
            </span>
          </div>
          <div className="flex items-end gap-[1px] h-10">
            {sorted.map((a, i) => {
              const h = (a.exact / Math.max(1, maxExact)) * 100;
              const isColin = a.name === 'Colin';
              return (
                <div
                  key={a.name + i}
                  className="flex-1 min-w-[2px]"
                  style={{
                    height: `${Math.max(6, h)}%`,
                    background: isColin ? '#B68A2F' : '#0B1F3A',
                    opacity: isColin ? 1 : 0.35,
                  }}
                  title={`${a.rank}. ${a.name} — ${a.exact} exact`}
                />
              );
            })}
          </div>
        </div>
      </div>

      {/* Hit-rate progress ring */}
      <div className="border border-ink-edge bg-paper-surface p-3">
        <div className="flex items-center gap-3">
          <ProgressRing pct={hitPct} />
          <div className="flex-1 min-w-0">
            <SmallCaps tight className="text-ink-muted text-[0.55rem] block">
              R1 hit rate
            </SmallCaps>
            <div className="display-num text-2xl text-ink leading-tight mt-0.5">
              {Math.round(hitPct * 100)}%
            </div>
            <div className="font-mono text-[0.6rem] text-ink-muted mt-0.5 truncate">
              {colin.exact} exact · {scored} scored
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ProgressRing({ pct }: { pct: number }) {
  const R = 22;
  const C = 2 * Math.PI * R;
  const offset = C * (1 - Math.min(1, Math.max(0, pct)));
  return (
    <svg width={56} height={56} viewBox="0 0 56 56" aria-label="Hit rate ring">
      <circle cx={28} cy={28} r={R} fill="none" stroke="#E8E2D4" strokeWidth={5} />
      <circle
        cx={28} cy={28} r={R} fill="none" stroke="#B68A2F" strokeWidth={5}
        strokeDasharray={C} strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 28 28)"
      />
    </svg>
  );
}
