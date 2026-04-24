/**
 * AccuracyGraphs — two SVG visualizations pulled from /api/accuracy.
 *
 *   1. Exact-hits histogram: distribution of exact-match scores across
 *      every analyst in the field, with Colin's bar highlighted in brass.
 *
 *   2. Pick-strip: 32-square ribbon showing hit / miss for each R1 slot
 *      (Colin's mock) with the actual player / pick tooltip.
 */
import { useEffect, useState } from 'react';
import { SmallCaps } from './editorial';

type AnalystRow = {
  name: string;
  exact: number;
  in_r1: number;
  rank: number;
};

type PickRow = {
  pick: number;
  actual_team: string | null;
  actual_player: string | null;
  colin: string | null;
  colin_hit: boolean | null;
};

type AccuracyResp = {
  r1_picks_drafted: number;
  total_r1_picks: number;
  total_analysts: number;
  analysts: AnalystRow[];
  picks: PickRow[];
};

export function AccuracyGraphs() {
  const [data, setData] = useState<AccuracyResp | null>(null);

  useEffect(() => {
    fetch('/api/accuracy')
      .then(r => r.ok ? r.json() : null)
      .then(setData)
      .catch(() => {});
  }, []);

  if (!data || data.r1_picks_drafted === 0) return null;

  return (
    <section>
      <div className="flex items-baseline justify-between border-b-2 border-ink px-1 pb-2 mb-4">
        <h2 className="display-broadcast text-lg md:text-xl text-ink">
          At a glance, visualised.
        </h2>
        <SmallCaps tight className="text-ink-muted">
          live as picks come in
        </SmallCaps>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="border border-ink-edge bg-paper-surface p-5">
          <Histogram data={data} />
        </div>
        <div className="border border-ink-edge bg-paper-surface p-5">
          <PickStrip data={data} />
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Histogram — exact-hit distribution across the analyst field
// ─────────────────────────────────────────────────────────────────────
function Histogram({ data }: { data: AccuracyResp }) {
  const colin = data.analysts.find(a => a.name === 'Colin');
  if (!colin) return null;
  const maxScore = Math.max(...data.analysts.map(a => a.exact));
  // Bucket per exact-score value
  const buckets: number[] = Array.from({ length: maxScore + 1 }, () => 0);
  data.analysts.forEach(a => { buckets[a.exact] += 1; });
  const maxCount = Math.max(...buckets, 1);

  const W = 480, H = 180;
  const PAD_L = 36, PAD_R = 16, PAD_T = 16, PAD_B = 28;
  const innerW = W - PAD_L - PAD_R;
  const innerH = H - PAD_T - PAD_B;
  const barW = innerW / buckets.length;

  return (
    <div>
      <div className="flex items-baseline justify-between mb-3">
        <SmallCaps className="text-ink">Field distribution</SmallCaps>
        <span className="font-mono text-xs text-ink-muted">
          {data.total_analysts} analysts · you ranked{' '}
          <span className="text-accent-brass font-bold">#{colin.rank}</span>
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" aria-label="Exact-hits histogram">
        {/* y-axis */}
        <line x1={PAD_L} y1={PAD_T} x2={PAD_L} y2={PAD_T + innerH}
              stroke="#B8B0A4" strokeWidth={1} />
        {/* y grid ticks */}
        {[0, 0.5, 1].map((t, i) => {
          const y = PAD_T + innerH - t * innerH;
          const val = Math.round(maxCount * t);
          return (
            <g key={i}>
              <line x1={PAD_L - 4} y1={y} x2={W - PAD_R} y2={y}
                    stroke="#E8E2D4" strokeWidth={1} strokeDasharray={i===0?"":"2 3"} />
              <text x={PAD_L - 8} y={y + 3} textAnchor="end"
                    className="font-mono" fontSize={9} fill="#6E6650">
                {val}
              </text>
            </g>
          );
        })}
        {/* bars */}
        {buckets.map((cnt, score) => {
          const x = PAD_L + score * barW + barW * 0.12;
          const w = barW * 0.76;
          const h = cnt > 0 ? (cnt / maxCount) * innerH : 0;
          const y = PAD_T + innerH - h;
          const isColin = score === colin.exact;
          return (
            <g key={score}>
              <rect x={x} y={y} width={w} height={h}
                    fill={isColin ? '#B68A2F' : '#0B1F3A'}
                    opacity={isColin ? 1 : 0.6}>
                <title>{`${cnt} analyst${cnt === 1 ? '' : 's'} with ${score} exact hit${score === 1 ? '' : 's'}`}</title>
              </rect>
              {isColin && cnt > 0 && (
                <text x={x + w/2} y={y - 4} textAnchor="middle"
                      className="font-mono" fontSize={9} fill="#B68A2F"
                      fontWeight={700}>
                  YOU
                </text>
              )}
              <text x={x + w/2} y={PAD_T + innerH + 14} textAnchor="middle"
                    className="font-mono" fontSize={9} fill="#6E6650">
                {score}
              </text>
            </g>
          );
        })}
        {/* x-axis label */}
        <text x={PAD_L + innerW/2} y={H - 4} textAnchor="middle"
              className="font-mono" fontSize={9} fill="#6E6650">
          exact hits (of {data.r1_picks_drafted})
        </text>
      </svg>
      <p className="text-[0.7rem] text-ink-muted mt-2 italic">
        Each bar = number of published mocks that scored that many exact
        R1 hits. Higher bar = more crowding.
      </p>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// PickStrip — 32 squares, hit / miss for each slot
// ─────────────────────────────────────────────────────────────────────
function PickStrip({ data }: { data: AccuracyResp }) {
  const picks = data.picks.filter(p => p.actual_player);
  const hits = picks.filter(p => p.colin_hit).length;
  const total = picks.length || 1;

  const COLS = 16;
  const ROWS = Math.ceil(32 / COLS);
  const CELL = 24;
  const GAP = 3;
  const W = COLS * CELL + (COLS - 1) * GAP;
  const H = ROWS * CELL + (ROWS - 1) * GAP;

  return (
    <div>
      <div className="flex items-baseline justify-between mb-3">
        <SmallCaps className="text-ink">Pick ribbon</SmallCaps>
        <span className="font-mono text-xs text-ink-muted">
          <span className="text-accent-brass font-bold">{hits}</span>/{total} hits
          · {Math.round(hits/total*100)}%
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H + 24}`} className="w-full h-auto"
           aria-label="Pick-by-pick hit/miss ribbon">
        {Array.from({ length: 32 }, (_, i) => {
          const slot = i + 1;
          const row = Math.floor(i / COLS);
          const col = i % COLS;
          const x = col * (CELL + GAP);
          const y = row * (CELL + GAP);
          const p = picks.find(pk => pk.pick === slot);
          const hit = p?.colin_hit ?? null;
          const drafted = p?.actual_player != null;
          const fill = !drafted
            ? '#E8E2D4'
            : hit === true
            ? '#3A6B46'
            : '#8C2E2A';
          const title = drafted
            ? `#${slot} · ${p!.actual_team ?? ''} · actual: ${p!.actual_player} · your pick: ${p!.colin ?? '—'}`
            : `#${slot} · pending`;
          return (
            <g key={slot}>
              <rect x={x} y={y} width={CELL} height={CELL} fill={fill} rx={2}>
                <title>{title}</title>
              </rect>
              <text x={x + CELL/2} y={y + CELL/2 + 3.5} textAnchor="middle"
                    className="font-mono" fontSize={9}
                    fill={drafted ? '#FAF6E6' : '#8A806A'}
                    fontWeight={600}>
                {slot}
              </text>
            </g>
          );
        })}
        {/* Legend */}
        <g transform={`translate(0, ${H + 10})`}>
          <rect x={0} y={0} width={10} height={10} fill="#3A6B46" rx={1} />
          <text x={15} y={9} className="font-mono" fontSize={9} fill="#6E6650">hit</text>
          <rect x={50} y={0} width={10} height={10} fill="#8C2E2A" rx={1} />
          <text x={65} y={9} className="font-mono" fontSize={9} fill="#6E6650">miss</text>
          <rect x={100} y={0} width={10} height={10} fill="#E8E2D4" rx={1} />
          <text x={115} y={9} className="font-mono" fontSize={9} fill="#6E6650">pending</text>
        </g>
      </svg>
      <p className="text-[0.7rem] text-ink-muted mt-2 italic">
        Hover a square for the actual pick vs your mock. Green = exact
        match, red = miss, grey = not drafted yet.
      </p>
    </div>
  );
}
