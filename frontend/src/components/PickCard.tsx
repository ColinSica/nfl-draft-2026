import { useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown } from 'lucide-react';
import { displayNum, displayValue } from '../lib/display';

export type PickData = {
  slot: number;
  team: string;          // team abbr e.g. 'LV'
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
  accent?: string;        // mode color accent
};

const conf: Record<string, { color: string; label: string }> = {
  HIGH:   { color: '#7CC77C', label: 'High confidence' },
  MEDIUM: { color: '#E6AF5A', label: 'Medium confidence' },
  LOW:    { color: '#D66C5A', label: 'Low confidence' },
};

export function PickCard({ data, expanded: initialExpanded = false }: {
  data: PickData;
  expanded?: boolean;
}) {
  const [expanded, setExpanded] = useState(initialExpanded);
  const accent = data.accent ?? '#C8F169';
  const prob = data.probability ?? null;
  const cons = data.consensusRank ?? null;
  const c = data.confidence ? conf[data.confidence] : null;

  return (
    <article
      className="card group hover:border-paper-muted transition-all ease-editorial duration-200"
      style={{ borderRadius: '2px' }}
    >
      {/* Top row: slot / team / probability */}
      <div className="flex items-stretch">
        <div
          className="flex flex-col items-center justify-center px-4 py-3 border-r border-ink-edge min-w-[72px]"
          style={{ background: `${accent}08` }}
        >
          <span className="caps-tight text-paper-subtle">Pick</span>
          <span
            className="display-serif text-3xl font-bold leading-none"
            style={{ color: accent }}
          >
            {String(data.slot).padStart(2, '0')}
          </span>
        </div>

        <div className="flex-1 px-4 py-3 flex items-center justify-between gap-3">
          <div>
            <Link
              to={`/team/${data.team}`}
              className="inline-flex items-center gap-2 caps-tight text-paper hover:text-mode-indie transition"
            >
              <span className="w-6 h-6 rounded-sm bg-ink-hover flex items-center justify-center text-[0.68rem] font-bold">
                {data.team}
              </span>
              <span>{displayValue(data.teamName, data.team)}</span>
            </Link>
          </div>
          <div className="text-right">
            {prob !== null && (
              <div className="font-mono text-lg text-paper">
                {displayNum(prob * 100, { digits: 0, suffix: '%' })}
              </div>
            )}
            <div className="caps-tight text-paper-subtle">Pick probability</div>
          </div>
        </div>
      </div>

      <hr className="hrule" />

      {/* Player row — the hero */}
      <div className="px-4 py-4">
        <div className="flex items-baseline justify-between gap-3 flex-wrap">
          <h3 className="display-serif text-2xl md:text-3xl font-semibold tracking-tight leading-none">
            {displayValue(data.player)}
          </h3>
          <div className="flex items-center gap-3 text-sm text-paper-muted font-mono">
            <span>{data.position}</span>
            {data.college && <><span className="text-ink-edge">·</span><span>{data.college}</span></>}
          </div>
        </div>

        <div className="mt-3 flex items-center gap-4 text-xs font-mono">
          {data.grade !== null && data.grade !== undefined && (
            <span className="text-paper-muted">
              <span className="caps-tight mr-1.5 text-paper-subtle">Grade</span>
              {displayNum(data.grade, { digits: 1 })}
            </span>
          )}
          {cons !== null && (
            <span className="text-paper-muted">
              <span className="caps-tight mr-1.5 text-paper-subtle">Consensus</span>
              #{cons}
            </span>
          )}
          {c && (
            <span className="inline-flex items-center gap-1.5" style={{ color: c.color }}>
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: c.color }} />
              <span className="caps-tight">{c.label}</span>
            </span>
          )}
        </div>
      </div>

      {/* Why-this-pick — the product-defining explanation */}
      {(data.whySummary || data.whyDetail) && (
        <>
          <hr className="hrule" />
          <div className="px-4 py-3">
            <button
              onClick={() => setExpanded(!expanded)}
              className="w-full flex items-start gap-3 text-left group/why"
            >
              <span
                className="caps-tight shrink-0 mt-1"
                style={{ color: accent }}
              >
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
    </article>
  );
}
