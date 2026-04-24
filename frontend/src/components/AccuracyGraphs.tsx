/**
 * AccuracyGraphs — interactive visualizations for the accuracy section.
 *
 *   1. Field-distribution histogram. Hover any bar -> see which analysts
 *      scored that many exact hits. Click a bar -> pin that list.
 *
 *   2. Pick ribbon. Hover/focus any of the 32 slots -> floating tooltip
 *      showing actual player, your pick, and whether it hit.
 */
import { useEffect, useMemo, useState } from 'react';
import { SmallCaps } from './editorial';

type AnalystRow = { name: string; exact: number; in_r1: number; rank: number };
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
          hover / click for detail
        </SmallCaps>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="border border-ink-edge bg-paper-surface p-5">
          <Histogram data={data} />
        </div>
        <div className="border border-ink-edge bg-paper-surface p-5">
          <PickRibbon data={data} />
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Histogram — interactive bars of exact-hit counts across the field
// ─────────────────────────────────────────────────────────────────────
function Histogram({ data }: { data: AccuracyResp }) {
  const [hoverScore, setHoverScore] = useState<number | null>(null);
  const [pinnedScore, setPinnedScore] = useState<number | null>(null);

  const colin = data.analysts.find(a => a.name === 'Colin');
  const maxScore = Math.max(...data.analysts.map(a => a.exact));
  const buckets = useMemo(() => {
    const out: Record<number, AnalystRow[]> = {};
    for (let s = 0; s <= maxScore; s++) out[s] = [];
    data.analysts.forEach(a => { out[a.exact].push(a); });
    return out;
  }, [data, maxScore]);

  const maxCount = Math.max(...Object.values(buckets).map(b => b.length), 1);
  const activeScore = hoverScore ?? pinnedScore;

  const W = 480, H = 200;
  const PAD_L = 40, PAD_R = 16, PAD_T = 20, PAD_B = 40;
  const innerW = W - PAD_L - PAD_R;
  const innerH = H - PAD_T - PAD_B;
  const barW = innerW / (maxScore + 1);

  return (
    <div>
      <div className="flex items-baseline justify-between mb-3">
        <SmallCaps className="text-ink">Exact-hit distribution</SmallCaps>
        <span className="font-mono text-xs text-ink-muted">
          {data.total_analysts} analysts · you{' '}
          <span className="text-accent-brass font-bold">
            #{colin?.rank ?? '—'}
          </span>
        </span>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto"
           aria-label="Histogram of exact hits per analyst">
        {/* y-axis */}
        <line x1={PAD_L} y1={PAD_T} x2={PAD_L} y2={PAD_T + innerH}
              stroke="#B8B0A4" strokeWidth={1} />
        <text x={PAD_L - 6} y={PAD_T - 6} textAnchor="end"
              className="font-mono" fontSize={9} fill="#6E6650">
          analysts
        </text>
        {/* y grid */}
        {[0, 0.5, 1].map((t, i) => {
          const y = PAD_T + innerH - t * innerH;
          const val = Math.round(maxCount * t);
          return (
            <g key={i}>
              <line x1={PAD_L - 4} y1={y} x2={W - PAD_R} y2={y}
                    stroke="#E8E2D4" strokeWidth={1}
                    strokeDasharray={i === 0 ? "" : "2 3"} />
              <text x={PAD_L - 8} y={y + 3} textAnchor="end"
                    className="font-mono" fontSize={9} fill="#6E6650">
                {val}
              </text>
            </g>
          );
        })}
        {/* bars */}
        {Array.from({ length: maxScore + 1 }, (_, score) => {
          const cnt = buckets[score].length;
          const x = PAD_L + score * barW + barW * 0.12;
          const w = barW * 0.76;
          const h = cnt > 0 ? (cnt / maxCount) * innerH : 0;
          const y = PAD_T + innerH - h;
          const isColinBucket = colin && score === colin.exact;
          const isActive = activeScore === score;
          const fill = isColinBucket ? '#B68A2F' : '#0B1F3A';
          const opacity = !activeScore && activeScore !== 0
            ? (isColinBucket ? 1 : 0.6)
            : (isActive ? 1 : 0.25);
          return (
            <g key={score}
               onMouseEnter={() => setHoverScore(score)}
               onMouseLeave={() => setHoverScore(null)}
               onFocus={() => setHoverScore(score)}
               onBlur={() => setHoverScore(null)}
               onClick={() =>
                 setPinnedScore(prev => prev === score ? null : score)}
               style={{ cursor: 'pointer' }}
               tabIndex={0}
               role="button"
               aria-label={`${cnt} analyst${cnt === 1 ? '' : 's'} with ${score} exact hits`}>
              {/* Full-width hitbox */}
              <rect x={PAD_L + score * barW} y={PAD_T}
                    width={barW} height={innerH}
                    fill="transparent" />
              <rect x={x} y={y} width={w} height={h}
                    fill={fill} opacity={opacity}
                    rx={1} />
              {/* count label on top */}
              {cnt > 0 && (
                <text x={x + w/2} y={y - 4} textAnchor="middle"
                      className="font-mono" fontSize={9}
                      fill={isColinBucket ? '#7A5A1E' : '#6E6650'}
                      fontWeight={isColinBucket || isActive ? 700 : 400}
                      pointerEvents="none">
                  {cnt}
                </text>
              )}
              {/* x label */}
              <text x={x + w/2} y={PAD_T + innerH + 14} textAnchor="middle"
                    className="font-mono" fontSize={9}
                    fill={isColinBucket ? '#B68A2F' : '#6E6650'}
                    fontWeight={isColinBucket ? 700 : 400}
                    pointerEvents="none">
                {score}
              </text>
              {isColinBucket && (
                <text x={x + w/2} y={PAD_T + innerH + 26} textAnchor="middle"
                      className="font-mono" fontSize={8}
                      fill="#B68A2F" fontWeight={700}
                      pointerEvents="none">
                  YOU
                </text>
              )}
            </g>
          );
        })}
        {/* x-axis caption */}
        <text x={PAD_L + innerW/2} y={H - 4} textAnchor="middle"
              className="font-mono" fontSize={9} fill="#6E6650">
          exact R1 hits · of {data.r1_picks_drafted}
        </text>
      </svg>

      {/* Bucket detail */}
      <div className="mt-2 min-h-[40px]">
        {activeScore !== null && (
          <BucketDetail
            score={activeScore}
            rows={buckets[activeScore] ?? []}
            pinned={pinnedScore === activeScore}
            onClear={() => setPinnedScore(null)}
          />
        )}
        {activeScore === null && (
          <p className="text-[0.7rem] text-ink-muted italic">
            Each bar = how many published mocks got that many R1 picks
            right. Hover to see the names; click to pin.
          </p>
        )}
      </div>
    </div>
  );
}

function BucketDetail({
  score, rows, pinned, onClear,
}: { score: number; rows: AnalystRow[]; pinned: boolean; onClear: () => void }) {
  return (
    <div className="text-xs">
      <div className="flex items-baseline gap-2 mb-1 flex-wrap">
        {pinned && (
          <span className="caps-tight text-[0.55rem] font-bold px-1 py-[1px]"
                style={{ background: '#B68A2F', color: '#FAF6E6' }}>
            pinned
          </span>
        )}
        <span className="caps-tight text-[0.62rem] text-ink-muted">
          {rows.length} analyst{rows.length === 1 ? '' : 's'} with{' '}
          <span className="text-ink font-bold">{score}</span>{' '}
          exact hit{score === 1 ? '' : 's'}
        </span>
        {pinned && (
          <button onClick={onClear}
                  className="ml-auto text-[0.6rem] caps-tight text-ink-muted hover:text-ink underline underline-offset-2">
            clear
          </button>
        )}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-0.5">
        {rows.map(a => {
          const isYou = a.name === 'Colin';
          return (
            <span key={a.name}
                  className={`font-mono text-[0.7rem] ${isYou ? 'text-accent-brass font-bold' : 'text-ink'}`}>
              #{a.rank} {a.name}
              {isYou && <span className="ml-1">← you</span>}
            </span>
          );
        })}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// PickRibbon — 32-square strip with floating HTML tooltip
// ─────────────────────────────────────────────────────────────────────
function PickRibbon({ data }: { data: AccuracyResp }) {
  const picks = data.picks.filter(p => p.pick <= 32);
  const [hoverSlot, setHoverSlot] = useState<number | null>(null);

  const drafted = picks.filter(p => p.actual_player != null);
  const hits = drafted.filter(p => p.colin_hit).length;
  const hoverPick = hoverSlot ? picks.find(p => p.pick === hoverSlot) : null;

  return (
    <div>
      <div className="flex items-baseline justify-between mb-3">
        <SmallCaps className="text-ink">Pick-by-pick</SmallCaps>
        <span className="font-mono text-xs text-ink-muted">
          <span className="text-accent-brass font-bold">{hits}</span> / {drafted.length} hits
          · {Math.round(hits / Math.max(1, drafted.length) * 100)}%
        </span>
      </div>

      {/* Ribbon grid — 16 columns × 2 rows */}
      <div
        className="grid gap-[3px]"
        style={{ gridTemplateColumns: 'repeat(16, minmax(0, 1fr))' }}
      >
        {Array.from({ length: 32 }, (_, i) => {
          const slot = i + 1;
          const p = picks.find(pk => pk.pick === slot);
          const draft = p?.actual_player != null;
          const hit = p?.colin_hit === true;
          const bg = !draft
            ? '#E8E2D4'
            : hit ? '#3A6B46' : '#8C2E2A';
          const fg = draft ? '#FAF6E6' : '#8A806A';
          const isHover = hoverSlot === slot;
          return (
            <button
              key={slot}
              onMouseEnter={() => setHoverSlot(slot)}
              onMouseLeave={() => setHoverSlot(null)}
              onFocus={() => setHoverSlot(slot)}
              onBlur={() => setHoverSlot(null)}
              className="aspect-square flex items-center justify-center font-mono font-bold text-[0.68rem] transition-transform rounded-sm"
              style={{
                background: bg,
                color: fg,
                transform: isHover ? 'scale(1.18)' : 'scale(1)',
                boxShadow: isHover ? '0 2px 8px rgba(11,31,58,0.25)' : 'none',
                zIndex: isHover ? 2 : 1,
              }}
              aria-label={
                draft
                  ? `Pick ${slot}: ${p!.actual_team} selected ${p!.actual_player}. You had ${p!.colin ?? 'no pick'}. ${hit ? 'Hit.' : 'Miss.'}`
                  : `Pick ${slot}: pending`
              }
            >
              {slot}
            </button>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-3 mt-3 font-mono text-[0.62rem] text-ink-muted">
        <span className="inline-flex items-center gap-1.5">
          <span className="w-2.5 h-2.5" style={{ background: '#3A6B46' }} /> hit
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-2.5 h-2.5" style={{ background: '#8C2E2A' }} /> miss
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-2.5 h-2.5" style={{ background: '#E8E2D4' }} /> pending
        </span>
      </div>

      {/* Floating detail card */}
      <div className="mt-3 min-h-[72px]">
        {hoverPick ? (
          <SlotCard pick={hoverPick} />
        ) : (
          <p className="text-[0.7rem] text-ink-muted italic">
            Hover a square for the actual pick vs your mock. Tab to
            navigate by keyboard.
          </p>
        )}
      </div>
    </div>
  );
}

function SlotCard({ pick }: { pick: PickRow }) {
  const drafted = pick.actual_player != null;
  const hit = pick.colin_hit === true;
  return (
    <div className="border border-ink-edge bg-paper px-3 py-2 text-xs">
      <div className="flex items-baseline justify-between mb-1">
        <span className="display-broadcast text-base text-ink">Pick #{pick.pick}</span>
        <span className="font-mono text-[0.62rem] text-ink-muted">
          {pick.actual_team ?? 'pending'}
        </span>
      </div>
      {drafted ? (
        <div className="grid grid-cols-2 gap-2">
          <div>
            <SmallCaps tight className="text-ink-muted text-[0.55rem] block">Actual</SmallCaps>
            <div className="font-serif text-ink">{pick.actual_player}</div>
          </div>
          <div>
            <SmallCaps tight className="text-ink-muted text-[0.55rem] block">Your pick</SmallCaps>
            <div className={`font-serif ${hit ? 'text-state-fresh' : 'text-ink-soft'}`}>
              {pick.colin ?? '—'}{' '}
              <span className="caps-tight text-[0.55rem] font-bold ml-1"
                    style={{ color: hit ? '#3A6B46' : '#8C2E2A' }}>
                {hit ? '✓ hit' : '✗ miss'}
              </span>
            </div>
          </div>
        </div>
      ) : (
        <p className="italic text-ink-muted">Not drafted yet.</p>
      )}
    </div>
  );
}
