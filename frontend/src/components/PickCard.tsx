import { useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown } from 'lucide-react';
import { displayNum, displayValue } from '../lib/display';
import { teamColor } from '../lib/teamColors';

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
  confidence?: 'HIGH' | 'MEDIUM' | 'LOW' | null;
  accent?: string;
};

const conf: Record<string, { color: string; label: string }> = {
  HIGH:   { color: '#2EE09A', label: 'High confidence' },
  MEDIUM: { color: '#FFD23F', label: 'Medium confidence' },
  LOW:    { color: '#E63946', label: 'Low confidence' },
};

export function PickCard({ data, expanded: initialExpanded = false }: {
  data: PickData;
  expanded?: boolean;
}) {
  const [expanded, setExpanded] = useState(initialExpanded);
  const accent = data.accent ?? '#FFD23F';
  const tc = teamColor(data.team);
  const prob = data.probability ?? null;
  const cons = data.consensusRank ?? null;
  const c = data.confidence ? conf[data.confidence] : null;

  const style: React.CSSProperties = {
    ['--team-primary' as any]: tc.primary,
    ['--team-secondary' as any]: tc.secondary,
  };

  return (
    <article
      className="card group hover:border-paper-muted transition-all ease-broadcast duration-200 flex"
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
              background: `linear-gradient(180deg, ${tc.primary}25 0%, ${tc.primary}05 100%)`,
            }}
          >
            <span className="caps-tight text-paper-subtle mb-0.5">Pick</span>
            <span
              className="display-num"
              style={{
                color: '#F3F6FA',
                fontSize: 'clamp(2.75rem, 6vw, 3.75rem)',
                textShadow: `0 0 20px ${tc.primary}40`,
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
                  color: tc.secondary === '#000000' ? '#FFFFFF' : tc.secondary,
                  border: `1px solid ${tc.secondary}40`,
                }}
              >
                {data.team}
              </span>
              <div className="min-w-0">
                <div className="display-broadcast text-lg leading-none text-paper truncate">
                  {tc.name}
                </div>
                <div className="text-[0.7rem] text-paper-subtle mono-label mt-0.5">
                  {displayValue(data.teamName, `${data.team}`)}
                </div>
              </div>
            </Link>

            {prob !== null && (
              <div className="text-right shrink-0">
                <div
                  className="display-num"
                  style={{ fontSize: '1.75rem', color: accent }}
                >
                  {displayNum(prob * 100, { digits: 0 })}
                  <span className="text-sm text-paper-muted font-normal ml-0.5">%</span>
                </div>
                <div className="caps-tight text-paper-subtle text-[0.65rem]">Pick prob</div>
              </div>
            )}
          </div>
        </div>

        <hr className="hrule" />

        {/* Player — the hero */}
        <div className="px-5 py-4">
          <div className="flex items-baseline justify-between gap-3 flex-wrap">
            <h3 className="display-broadcast text-2xl md:text-3xl leading-none">
              {displayValue(data.player).toUpperCase()}
            </h3>
            <div className="flex items-center gap-2.5 text-xs text-paper-muted font-mono">
              <span
                className="px-1.5 py-0.5"
                style={{
                  background: '#141A25',
                  border: '1px solid #252D3D',
                  color: '#F3F6FA',
                  fontWeight: 700,
                }}
              >
                {data.position}
              </span>
              {data.college && <span className="text-paper-subtle">{data.college}</span>}
            </div>
          </div>

          <div className="mt-3 flex items-center gap-4 text-xs font-mono flex-wrap">
            {data.grade !== null && data.grade !== undefined && (
              <span className="text-paper-muted">
                <span className="caps-tight mr-1.5 text-paper-subtle">Grade</span>
                <span className="text-paper font-bold">{displayNum(data.grade, { digits: 1 })}</span>
              </span>
            )}
            {cons !== null && (
              <span className="text-paper-muted">
                <span className="caps-tight mr-1.5 text-paper-subtle">Consensus</span>
                <span className="text-paper font-bold">#{cons}</span>
              </span>
            )}
            {c && (
              <span className="inline-flex items-center gap-1.5 ml-auto" style={{ color: c.color }}>
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: c.color }} />
                <span className="caps-tight">{c.label}</span>
              </span>
            )}
          </div>
        </div>

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
                <div className="flex-1 text-paper leading-relaxed text-sm">
                  {data.whySummary ?? (
                    <span className="italic text-paper-subtle">
                      Reasoning not yet generated for this pick.
                    </span>
                  )}
                </div>
                {data.whyDetail && (
                  <ChevronDown
                    size={16}
                    className="shrink-0 mt-1 text-paper-subtle transition-transform duration-200"
                    style={{ transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
                  />
                )}
              </button>
              {expanded && data.whyDetail && (
                <div className="mt-3 pt-3 border-t border-ink-edge text-sm text-paper-muted leading-relaxed">
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
