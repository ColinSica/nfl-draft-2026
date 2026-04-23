import { useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown } from 'lucide-react';
import { displayNum, displayValue, getConfidence, type ConfLabel } from '../lib/display';
import { teamColor } from '../lib/teamColors';
import { secondaryInk } from '../lib/color';

export type PickAlternate = {
  player: string;
  position: string;
  college?: string | null;
  probability?: number | null;
};

export type PickData = {
  slot: number;
  team: string;
  teamName?: string | null;
  player: string;
  position: string;
  college?: string | null;
  probability?: number | null;
  grade?: number | null;
  consensusRank?: number | null;
  whySummary?: string | null;
  whyDetail?: ReactNode | null;
  confidence?: ConfLabel | 'HIGH' | 'MEDIUM' | 'LOW' | null;
  accent?: string;
  alternates?: PickAlternate[] | null;   // runners-up from the MC distribution
};

// Legacy aliases kept for back-compat with any call sites still passing old labels
const LEGACY_TO_NEW: Record<string, ConfLabel> = {
  HIGH:        'HIGH',
  MEDIUM:      'MEDIUM_HIGH',
  MEDIUM_HIGH: 'MEDIUM_HIGH',
  MEDIUM_LOW:  'MEDIUM_LOW',
  LOW:         'LOW',
};

// Representative probability per confidence bucket — used when a caller
// passes an explicit confidence label instead of a raw probability.
const LABEL_TO_PROB: Record<ConfLabel, number> = {
  HIGH: 0.70,
  MEDIUM_HIGH: 0.45,
  MEDIUM_LOW: 0.30,
  LOW: 0.15,
};

function resolveConfidence(
  prob: number | null,
  label: PickData['confidence'],
) {
  if (prob !== null) return getConfidence(prob);
  if (!label) return null;
  const key = LEGACY_TO_NEW[label as string] ?? (label as ConfLabel);
  return getConfidence(LABEL_TO_PROB[key] ?? 0.15);
}

export function PickCard({ data, expanded: initialExpanded = false }: {
  data: PickData;
  expanded?: boolean;
}) {
  const [expanded, setExpanded] = useState(initialExpanded);
  const accent = data.accent ?? '#B68A2F';
  const tc = teamColor(data.team);
  const prob = data.probability ?? null;
  const cons = data.consensusRank ?? null;
  // Prefer prob-based calibrated label. Fall back to explicit confidence prop (mapped via legacy).
  const c = resolveConfidence(prob, data.confidence);

  const style: React.CSSProperties = {
    ['--team-primary' as any]: tc.primary,
    ['--team-secondary' as any]: tc.secondary,
  };

  return (
    <article
      className="card group hover:shadow-card-raised transition-all ease-broadcast duration-200 flex"
      style={style}
    >
      {/* Team color edge — sports identity */}
      <div className="team-edge" />
      <div className="team-edge-secondary" />

      <div className="flex-1 min-w-0">
        {/* Top row: PICK NUMBER (hero) / TEAM / PROBABILITY */}
        <div className="flex items-stretch">
          <div
            className="flex flex-col items-center justify-center px-5 py-4 border-r border-ink-edge min-w-[108px]"
            style={{
              background: `linear-gradient(180deg, ${tc.primary}18 0%, ${tc.primary}04 100%)`,
            }}
          >
            <span className="caps-tight text-ink-soft mb-0.5">Pick</span>
            <span
              className="display-num"
              style={{
                color: tc.primary,
                fontSize: 'clamp(2.75rem, 6vw, 3.75rem)',
              }}
            >
              {String(data.slot).padStart(2, '0')}
            </span>
          </div>

          <div className="flex-1 px-4 py-3 flex items-center justify-between gap-3 min-w-0">
            <Link
              to={`/team/${data.team}`}
              className="inline-flex items-center gap-2.5 min-w-0"
            >
              <span
                className="w-8 h-8 flex items-center justify-center font-bold text-xs"
                style={{
                  background: tc.primary,
                  color: secondaryInk(tc.secondary),
                  border: `1px solid ${tc.secondary}40`,
                }}
              >
                {data.team}
              </span>
              <div className="min-w-0">
                <div className="display-broadcast text-lg leading-none text-ink truncate">
                  {tc.name}
                </div>
                <div className="text-[0.7rem] text-ink-soft/70 mono-label mt-0.5">
                  {displayValue(data.teamName, `${data.team}`)}
                </div>
              </div>
            </Link>

            {prob !== null && (
              <div className="text-right shrink-0">
                <div
                  className="display-num text-ink"
                  style={{ fontSize: '1.75rem' }}
                >
                  {displayNum(prob * 100, { digits: 0 })}
                  <span className="text-sm text-ink-soft/70 font-normal ml-0.5">%</span>
                </div>
                <div className="caps-tight text-ink-soft text-[0.65rem]">Pick prob</div>
              </div>
            )}
          </div>
        </div>

        <hr className="hrule" />

        {/* Player — the hero */}
        <div className="px-5 py-5">
          <div className="flex items-baseline justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-3 flex-wrap">
              <h3 className="display-broadcast text-2xl md:text-3xl leading-none text-ink">
                {displayValue(data.player).toUpperCase()}
              </h3>
            </div>
            <div className="flex items-center gap-2.5 text-xs text-ink-soft font-mono">
              <span
                className="px-1.5 py-0.5 font-bold"
                style={{
                  background: '#0B1F3A',
                  color: '#F3ECD6',
                }}
              >
                {data.position}
              </span>
              {data.college && <span className="text-ink-soft/80">{data.college}</span>}
            </div>
          </div>

          <div className="mt-3 flex items-center gap-4 text-xs font-mono flex-wrap">
            {data.grade !== null && data.grade !== undefined && (
              <span className="text-ink-soft">
                <span className="caps-tight mr-1.5 text-ink-soft/70">Grade</span>
                <span className="text-ink font-bold">{displayNum(data.grade, { digits: 1 })}</span>
              </span>
            )}
            {cons !== null && (
              <span className="text-ink-soft">
                <span className="caps-tight mr-1.5 text-ink-soft/70">Board</span>
                <span className="text-ink font-bold">#{cons}</span>
              </span>
            )}
            {c && (
              <span
                className="inline-flex items-center gap-1.5 ml-auto"
                style={{ color: c.color }}
                title={`Calibrated against 2024+2025 R1 outcomes — ${c.historicalHitRate}`}
              >
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: c.color }} />
                <span className="caps-tight">{c.display}</span>
                <span className="text-[0.6rem] text-ink-soft/60 font-normal normal-case tracking-normal">
                  ({c.historicalHitRate})
                </span>
              </span>
            )}
          </div>
        </div>

        {/* Alternates strip — runner-up candidates from MC distribution */}
        {data.alternates && data.alternates.length > 0 && (
          <>
            <hr className="hrule" />
            <div className="px-5 py-3">
              <div className="caps-tight text-ink-soft mb-2">
                Also in play
                {data.alternates.length > 5 && (
                  <span className="ml-1 normal-case tracking-normal text-[0.62rem] text-ink-soft/70">
                    (top 5 of {data.alternates.length})
                  </span>
                )}
              </div>
              <div className="flex flex-wrap gap-x-5 gap-y-1.5 text-sm">
                {data.alternates.slice(0, 5).map((alt, i) => (
                  <span key={`${alt.player}-${i}`} className="inline-flex items-baseline gap-2">
                    <span className="font-mono text-xs text-ink-soft/80 shrink-0">
                      {alt.probability ? `${Math.round(alt.probability * 100)}%` : '—'}
                    </span>
                    <span className="text-ink font-semibold">{alt.player}</span>
                    <span className="font-mono text-[0.65rem] text-ink-soft">{alt.position}</span>
                  </span>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Why-this-pick */}
        {(data.whySummary || data.whyDetail) && (
          <>
            <hr className="hrule" />
            <div className="px-5 py-3.5">
              <button
                onClick={() => setExpanded(!expanded)}
                className="w-full flex items-start gap-3 text-left"
              >
                <span className="caps-tight shrink-0 mt-1" style={{ color: accent }}>
                  Why this pick?
                </span>
                <div className="flex-1 text-ink leading-relaxed text-sm">
                  {data.whySummary ?? (
                    <span className="italic text-ink-soft">
                      Reasoning not yet generated for this pick.
                    </span>
                  )}
                </div>
                {data.whyDetail && (
                  <ChevronDown
                    size={16}
                    className="shrink-0 mt-1 text-ink-soft transition-transform duration-200"
                    style={{ transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
                  />
                )}
              </button>
              {expanded && data.whyDetail && (
                <div className="mt-3 pt-3 border-t border-ink-edge text-sm text-ink-soft leading-relaxed">
                  {data.whyDetail}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </article>
  );
}
