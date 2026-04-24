/**
 * AtAGlanceStats — interactive live-accuracy widget for the Home hero's
 * right rail (~340px wide).
 *
 *   Rank card     — prose-clear "#X of Y" + interactive dot plot where
 *                   each analyst is a hoverable / clickable dot.
 *   Hit-rate card — progress ring + "X of Y" sentence.
 *
 * Interactions:
 *   - Hover any analyst dot -> tooltip with name, rank, exact hits.
 *   - Click a dot -> pins it; a "Selected" strip below compares that
 *     analyst to you head-to-head.
 */
import { useEffect, useMemo, useState } from 'react';
import { SmallCaps } from './editorial';

type AnalystRow = { name: string; exact: number; rank: number };
type AccuracyResp = {
  r1_picks_drafted: number;
  total_r1_picks: number;
  total_analysts: number;
  analysts: AnalystRow[];
};

export function AtAGlanceStats() {
  const [data, setData] = useState<AccuracyResp | null>(null);
  const [hoverName, setHoverName] = useState<string | null>(null);
  const [pinnedName, setPinnedName] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/accuracy')
      .then(r => r.ok ? r.json() : null)
      .then(setData)
      .catch(() => {});
  }, []);

  const colin = useMemo(
    () => data?.analysts.find(a => a.name === 'Colin') ?? null,
    [data]
  );

  if (!data || data.r1_picks_drafted === 0 || !colin) return null;

  const scored = data.r1_picks_drafted;
  const hitPct = scored > 0 ? colin.exact / scored : 0;
  const behind = data.analysts.filter(a => a.exact < colin.exact).length;
  const totalOthers = data.total_analysts - 1;
  const behindClamped = Math.min(behind, totalOthers);

  const hovered = hoverName ? data.analysts.find(a => a.name === hoverName) : null;
  const pinned = pinnedName ? data.analysts.find(a => a.name === pinnedName) : null;
  const active = hovered ?? pinned ?? null;  // hover takes priority

  return (
    <div className="space-y-3">
      <SmallCaps tight>Live mock accuracy</SmallCaps>

      {/* Rank card */}
      <div className="border border-ink-edge bg-paper-surface">
        <div className="px-4 py-4 border-b border-ink-edge">
          <p className="body-serif text-sm text-ink leading-snug">
            The model ranks{' '}
            <span className="display-num text-2xl text-accent-brass mx-0.5">
              #{colin.rank}
            </span>{' '}
            of {data.total_analysts} published 2026 mocks —
            ahead of{' '}
            <span className="font-bold text-ink">{behindClamped}</span>{' '}
            of {totalOthers} other analysts.
          </p>
        </div>

        {/* Dot plot: each analyst is a dot on an exact-hits axis */}
        <div className="px-4 py-3">
          <div className="flex items-baseline justify-between mb-2">
            <SmallCaps tight className="text-ink-muted text-[0.6rem]">
              Field by exact hits
            </SmallCaps>
            <span className="font-mono text-[0.58rem] text-ink-muted italic">
              hover · click to pin
            </span>
          </div>
          <DotPlot
            analysts={data.analysts}
            scored={scored}
            activeName={active?.name ?? null}
            pinnedName={pinnedName}
            onHover={setHoverName}
            onClick={(n) => setPinnedName(prev => prev === n ? null : n)}
          />
          {/* Active analyst strip — hover tooltip + pinned state share */}
          <div className="mt-2 min-h-[28px]">
            {active ? (
              <ActiveLine
                active={active}
                colin={colin}
                scored={scored}
                isPinned={pinnedName === active.name && !hovered}
                onClear={() => setPinnedName(null)}
              />
            ) : (
              <p className="text-[0.68rem] text-ink-muted italic">
                Hover any dot to inspect an analyst; click to pin.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Hit rate ring */}
      <div className="border border-ink-edge bg-paper-surface px-4 py-4">
        <div className="flex items-center gap-4">
          <ProgressRing pct={hitPct} size={68} />
          <div className="flex-1 min-w-0">
            <SmallCaps tight className="text-ink-muted text-[0.6rem] block">
              R1 hit rate
            </SmallCaps>
            <div className="display-num text-2xl text-ink leading-tight mt-0.5">
              {Math.round(hitPct * 100)}%
            </div>
            <p className="font-mono text-[0.68rem] text-ink-muted mt-0.5">
              {colin.exact} of {scored} picks correct
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// ActiveLine — renders below the dot plot when something is hovered/pinned
// ─────────────────────────────────────────────────────────────────────
function ActiveLine({
  active, colin, scored, isPinned, onClear,
}: {
  active: AnalystRow;
  colin: AnalystRow;
  scored: number;
  isPinned: boolean;
  onClear: () => void;
}) {
  const isModel = active.name === 'Colin';
  const delta = active.exact - colin.exact;
  return (
    <div className="flex items-baseline gap-2 text-xs flex-wrap">
      {isPinned && (
        <span className="caps-tight text-[0.55rem] font-bold px-1 py-[1px]"
              style={{ background: '#B68A2F', color: '#FAF6E6' }}>
          pinned
        </span>
      )}
      <span className={`font-mono ${isModel ? 'text-accent-brass font-bold' : 'text-ink'}`}>
        #{active.rank} {isModel ? 'The model' : active.name}
      </span>
      <span className="font-mono text-ink-muted">·</span>
      <span className="font-mono text-ink">{active.exact}/{scored}</span>
      {!isModel && (
        <span className={`font-mono ${delta === 0 ? 'text-ink-muted' : delta > 0 ? 'text-live' : 'text-accent-brass'}`}>
          {delta > 0 ? `+${delta} vs model` : delta < 0 ? `${delta} vs model` : 'tied w/ model'}
        </span>
      )}
      {isPinned && (
        <button
          onClick={onClear}
          className="ml-auto text-[0.6rem] caps-tight text-ink-muted hover:text-ink underline underline-offset-2"
          aria-label="Unpin analyst"
        >
          clear
        </button>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Interactive dot plot
// ─────────────────────────────────────────────────────────────────────
function DotPlot({
  analysts, scored, activeName, pinnedName, onHover, onClick,
}: {
  analysts: AnalystRow[];
  scored: number;
  activeName: string | null;
  pinnedName: string | null;
  onHover: (n: string | null) => void;
  onClick: (n: string) => void;
}) {
  const maxScore = Math.max(...analysts.map(a => a.exact), 1);
  const xMax = Math.max(maxScore, scored);

  // Count max stack depth so we can size the chart so dots + label never clip.
  const stackCounts: Record<number, number> = {};
  analysts.forEach(a => { stackCounts[a.exact] = (stackCounts[a.exact] ?? 0) + 1; });
  const maxStack = Math.max(...Object.values(stackCounts), 1);

  // Deterministic dot stacking per score (order preserves analyst order).
  const byScore: Record<number, number> = {};
  const withPos = analysts.map(a => {
    const stackIdx = (byScore[a.exact] ?? 0);
    byScore[a.exact] = stackIdx + 1;
    return { ...a, stackIdx };
  });

  const DOT_GAP = 7;
  const BASE_PAD = 6;          // gap between baseline and first dot center
  const LABEL_PAD = 14;        // headroom reserved for "MODEL" label above Colin
  const stackHeight = BASE_PAD + (maxStack - 1) * DOT_GAP;
  const innerH = stackHeight + LABEL_PAD + 4;

  const W = 260;
  const PAD_L = 6, PAD_R = 6, PAD_T = 10, PAD_B = 22;
  const H = PAD_T + innerH + PAD_B;
  const innerW = W - PAD_L - PAD_R;

  return (
    <svg viewBox={`0 0 ${W} ${H}`}
         className="w-full h-auto block select-none"
         aria-label="Exact hits per analyst; click a dot to pin">
      {/* Axis baseline */}
      <line x1={PAD_L} y1={PAD_T + innerH} x2={W - PAD_R} y2={PAD_T + innerH}
            stroke="#B8B0A4" strokeWidth={1} />
      {/* Axis ticks */}
      {Array.from({ length: xMax + 1 }, (_, i) => {
        const x = PAD_L + (i / xMax) * innerW;
        const showLabel = i === 0 || i === xMax || i % 2 === 0;
        return (
          <g key={i}>
            <line x1={x} y1={PAD_T + innerH} x2={x} y2={PAD_T + innerH + 3}
                  stroke="#B8B0A4" strokeWidth={1} />
            {showLabel && (
              <text x={x} y={PAD_T + innerH + 13} textAnchor="middle"
                    className="font-mono" fontSize={9} fill="#6E6650">
                {i}
              </text>
            )}
          </g>
        );
      })}

      {/* Dots — sorted so Colin and active render on top */}
      {withPos
        .slice()
        .sort((a, b) => {
          const aKey = a.name === 'Colin' ? 2 : (a.name === activeName ? 1 : 0);
          const bKey = b.name === 'Colin' ? 2 : (b.name === activeName ? 1 : 0);
          return aKey - bKey;
        })
        .map(a => {
          const cx = PAD_L + (a.exact / xMax) * innerW;
          const cy = PAD_T + innerH - 6 - a.stackIdx * 7;
          const isColin = a.name === 'Colin';
          const isActive = a.name === activeName;
          const isPinned = a.name === pinnedName;
          const r = isColin ? 6 : isActive ? 5 : 3.5;
          const fill = isColin ? '#B68A2F'
                    : isActive ? '#0B1F3A'
                    : '#0B1F3A';
          const opacity = activeName && !isActive && !isColin ? 0.2 : (isColin ? 1 : 0.45);
          return (
            <g
              key={a.name + a.rank}
              onMouseEnter={() => onHover(a.name)}
              onMouseLeave={() => onHover(null)}
              onFocus={() => onHover(a.name)}
              onBlur={() => onHover(null)}
              onClick={() => onClick(a.name)}
              style={{ cursor: 'pointer' }}
              tabIndex={0}
              role="button"
              aria-label={`${a.name}, rank ${a.rank}, ${a.exact} exact hits`}
            >
              {/* Generous invisible hitbox for hover/click */}
              <circle cx={cx} cy={cy} r={Math.max(r + 4, 8)}
                      fill="transparent" />
              <circle cx={cx} cy={cy} r={r}
                      fill={fill}
                      opacity={opacity}
                      stroke={isPinned ? '#7A5A1E' : isActive && !isColin ? '#0B1F3A' : isColin ? '#7A5A1E' : 'none'}
                      strokeWidth={isPinned ? 2 : isColin ? 1 : 0} />
              {isColin && (
                <text x={cx} y={cy - r - 4} textAnchor="middle"
                      className="font-mono" fontSize={9}
                      fill="#B68A2F" fontWeight={700}
                      pointerEvents="none">
                  MODEL
                </text>
              )}
            </g>
          );
        })}

      {/* Axis caption */}
      <text x={W/2} y={H - 2} textAnchor="middle"
            className="font-mono" fontSize={8.5} fill="#6E6650">
        → exact R1 hits (higher = better)
      </text>
    </svg>
  );
}

function ProgressRing({ pct, size = 56 }: { pct: number; size?: number }) {
  const R = size / 2 - 5;
  const C = 2 * Math.PI * R;
  const offset = C * (1 - Math.min(1, Math.max(0, pct)));
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}
         aria-label="Hit rate ring">
      <circle cx={size/2} cy={size/2} r={R} fill="none"
              stroke="#E8E2D4" strokeWidth={5} />
      <circle
        cx={size/2} cy={size/2} r={R} fill="none"
        stroke="#B68A2F" strokeWidth={5}
        strokeDasharray={C} strokeDashoffset={offset}
        strokeLinecap="round"
        transform={`rotate(-90 ${size/2} ${size/2})`}
      />
    </svg>
  );
}
