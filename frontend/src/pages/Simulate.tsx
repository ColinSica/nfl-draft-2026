import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Play, Loader2, Check, AlertTriangle, Lock, Eye,
  BarChart3, Info, ChevronDown, Users, Target, Clock, Terminal, Activity,
  ArrowRightLeft,
} from 'lucide-react';
import {
  api, tokenStore, type MetaInfo, type PickRow, type ProspectRow, type SimState,
} from '../lib/api';
import { cn, fmtDate } from '../lib/format';
import { teamMeta, positionColor, TEAMS } from '../lib/teams';

// ----- Confidence tier ------------------------------------------------------
function confidenceTier(p: number): { label: string; color: string; dot: string } {
  if (p >= 0.8)  return { label: 'Very likely', color: 'text-tier-high',  dot: 'bg-tier-high'  };
  if (p >= 0.55) return { label: 'Likely',      color: 'text-tier-midhi', dot: 'bg-tier-midhi' };
  if (p >= 0.35) return { label: 'Leaning',     color: 'text-tier-mid',   dot: 'bg-tier-mid'   };
  if (p >= 0.20) return { label: 'Possible',    color: 'text-tier-midlo', dot: 'bg-tier-midlo' };
  return            { label: 'Longshot',    color: 'text-tier-low',   dot: 'bg-tier-low'   };
}

// ----- Types ----------------------------------------------------------------
type AnalystPerPick = {
  team: string;
  picks_all: Record<string, number>;
  picks_tier1: Record<string, number>;
  consensus_player: string;
  consensus_tier1: string;
  trade_noted: boolean;
};

// Scripted trade scenarios from determine_trades() — probability of the
// pick changing hands in any given sim. Used to show a trade badge on the
// pick card.
const SCRIPTED_TRADE_PROB: Record<number, { pct: number; note: string }> = {
  6:  { pct: 40, note: 'DAL trades up (Styles target)' },
  4:  { pct: 15, note: 'DAL trades up to 4' },
  5:  { pct: 3,  note: 'CIN rarely trades up' },
  11: { pct: 20, note: 'MIA trades down (Sullivan accumulation)' },
  12: { pct: 8,  note: 'CLE trades up for Proctor' },
  13: { pct: 55, note: 'LAR trades down (Snead pattern)' },
  18: { pct: 10, note: 'PHI trade-up target' },
  20: { pct: 12, note: 'CLE trades up for Concepcion' },
  30: { pct: 25, note: 'ARI trades up for Simpson' },
  32: { pct: 65, note: 'SEA trades down (Schneider)' },
};

// ----- Pick card (keeps runner-ups behind expand, per user preference) ------
type ModelReasoning = {
  team: string;
  player: string;
  position: string;
  components: {
    bpa: number; need: number; visit: number; intel: number;
    pv_mult: number; gm_affinity: number; score_final: number;
  };
  top_factors: Array<{ key: string; magnitude: number; label: string; detail: string }>;
};

function PickCard({
  row, expanded, onToggle, analyst, reasoning, modelReasoning, nAnalysts, nTier1,
}: {
  row: PickRow;
  expanded: boolean;
  onToggle: () => void;
  analyst?: AnalystPerPick;
  reasoning?: Array<{ analyst: string; text: string }>;
  modelReasoning?: ModelReasoning;
  nAnalysts: number;
  nTier1: number;
}) {
  const top = row.candidates[0];
  const team = teamMeta(row.team);
  const tier = confidenceTier(top?.probability ?? 0);
  const posColor = positionColor(top?.position);
  const stripe = team?.primary ?? '#303648';
  const runnerCount = Math.max(0, row.candidates.length - 1);

  // Analyst agreement — does the model's top-1 match the analyst consensus?
  const analystPick = analyst?.consensus_tier1 || analyst?.consensus_player;
  const analystAgreed = top?.player && analystPick &&
    (top.player.toLowerCase().includes(analystPick.toLowerCase().split(' ').pop()?.toLowerCase() ?? '') ||
     analystPick.toLowerCase().includes(top.player.toLowerCase().split(' ').pop()?.toLowerCase() ?? ''));

  return (
    <div
      className={cn(
        'card overflow-hidden transition-all',
        expanded && 'shadow-glow border-border-strong',
      )}
      style={{ borderLeft: `4px solid ${stripe}` }}
    >
      {/* Clickable header */}
      <button
        onClick={onToggle}
        className="w-full px-4 py-3.5 flex items-center gap-3 md:gap-4 text-left hover:bg-bg-hover/60 focus:bg-bg-hover/60 focus:outline-none transition-colors"
        aria-expanded={expanded}
      >
        {/* Pick number */}
        <div className="flex-none w-12 md:w-14 text-center">
          <div className="font-mono text-2xl md:text-3xl font-semibold leading-none tabular-nums">
            {row.pick_number}
          </div>
          <div className="text-[10px] text-text-subtle uppercase tracking-wider mt-1">
            pick
          </div>
        </div>

        {/* Team identity */}
        <div className="flex-none flex items-center gap-2.5 w-36 md:w-40">
          {team && (
            <img
              src={team.logo}
              alt=""
              className="w-9 h-9 object-contain flex-none"
              onError={(e) => ((e.target as HTMLImageElement).style.display = 'none')}
            />
          )}
          <div className="min-w-0">
            <div className="font-semibold text-sm truncate">
              {team?.city ?? row.team ?? '—'}
            </div>
            <div className="text-xs text-text-muted truncate">
              {team?.name ?? ''}
            </div>
          </div>
        </div>

        {/* Player + agreement indicator */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-base text-text truncate">
              {top?.player ?? '—'}
            </span>
            {top?.position && (
              <span
                className="badge flex-none"
                style={{
                  color: posColor,
                  borderColor: `${posColor}4D`,
                  backgroundColor: `${posColor}1A`,
                }}
              >
                {top.position}
              </span>
            )}
            {analyst && analystPick && (
              <span
                className={cn(
                  'badge flex-none text-[10px] font-medium',
                  analystAgreed
                    ? 'border-tier-high/40 bg-tier-high/10 text-tier-high'
                    : 'border-tier-midlo/40 bg-tier-midlo/10 text-tier-midlo',
                )}
                title={
                  analystAgreed
                    ? `Model matches analyst consensus (${analystPick})`
                    : `Model disagrees with analysts — they had ${analystPick}`
                }
              >
                {analystAgreed ? 'Matches analysts' : 'Differs from analysts'}
              </span>
            )}
            {SCRIPTED_TRADE_PROB[row.pick_number] && (
              <span
                className="badge flex-none border-accent/40 bg-accent/10 text-accent flex items-center gap-1"
                title={SCRIPTED_TRADE_PROB[row.pick_number].note}
              >
                <ArrowRightLeft size={10} />
                Traded {SCRIPTED_TRADE_PROB[row.pick_number].pct}%
              </span>
            )}
          </div>
          <div className="text-xs text-text-muted truncate mt-1 flex items-center gap-2">
            <span className="truncate">{top?.college ?? '—'}</span>
            {top?.consensus_rank != null && (
              <>
                <span className="text-text-subtle">·</span>
                <span>Board rank #{top.consensus_rank}</span>
              </>
            )}
          </div>
        </div>

        {/* Probability */}
        <div className="flex-none w-36 md:w-44">
          <div className="flex items-center justify-between mb-1.5">
            <span className={cn('text-xs font-medium flex items-center gap-1.5', tier.color)}>
              <span className={cn('w-1.5 h-1.5 rounded-full', tier.dot)} />
              {tier.label}
            </span>
            <span className="font-mono text-base font-semibold tabular-nums">
              {((top?.probability ?? 0) * 100).toFixed(0)}%
            </span>
          </div>
          <div className="h-2 bg-bg-raised rounded-full overflow-hidden">
            <div
              className="h-full transition-all"
              style={{
                width: `${(top?.probability ?? 0) * 100}%`,
                background: `linear-gradient(90deg, ${stripe}99, ${stripe})`,
              }}
            />
          </div>
        </div>

        {/* Expand affordance */}
        <div className={cn(
          'flex-none flex items-center gap-1 text-xs font-medium transition',
          expanded ? 'text-accent' : 'text-text-muted group-hover:text-text',
        )}>
          <span className="hidden md:inline">
            {expanded ? 'Hide' : runnerCount > 0 ? `+${runnerCount}` : 'Details'}
          </span>
          <ChevronDown
            size={14}
            className={cn('transition-transform', expanded && 'rotate-180')}
          />
        </div>
      </button>

      {/* Expanded: runner-ups + analyst consensus + reasoning */}
      {expanded && (
        <div className="px-4 pb-4 pt-3 border-t border-border bg-bg-raised/30 space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Runner-ups (model) */}
            <div>
              <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-text-muted mb-2">
                <Target size={12} />
                Model runner-ups ({runnerCount})
              </div>
              {runnerCount > 0 ? (
                <table className="w-full text-sm">
                  <tbody>
                    {row.candidates.slice(1).map((c) => (
                      <tr key={c.player} className="border-b border-border last:border-0">
                        <td className="py-2 pr-2 w-14">
                          <span
                            className="badge"
                            style={{
                              color: positionColor(c.position),
                              borderColor: `${positionColor(c.position)}4D`,
                              backgroundColor: `${positionColor(c.position)}1A`,
                            }}
                          >
                            {c.position}
                          </span>
                        </td>
                        <td className="py-2 pr-2">
                          <div className="font-medium text-text">{c.player}</div>
                          <div className="text-xs text-text-subtle">
                            {c.college}
                            {c.consensus_rank != null && ` · #${c.consensus_rank}`}
                          </div>
                        </td>
                        <td className="py-2 pl-2 w-28">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 h-1.5 bg-bg-hover rounded-full overflow-hidden">
                              <div
                                className="h-full bg-accent/70"
                                style={{ width: `${c.probability * 100}%` }}
                              />
                            </div>
                            <span className="font-mono text-xs tabular-nums text-text w-9 text-right">
                              {(c.probability * 100).toFixed(0)}%
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="text-sm text-text-subtle italic py-2">
                  No other plausible candidates — model converged on a single name.
                </div>
              )}
            </div>

            {/* Analyst consensus */}
            <div>
              <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-text-muted mb-2">
                <Users size={12} />
                Analyst consensus
                <span className="text-text-subtle ml-auto font-normal normal-case">
                  {nAnalysts} mocks · {nTier1} tier-1
                </span>
              </div>
              {analyst ? (
                <AnalystTable
                  analyst={analyst}
                  nAnalysts={nAnalysts}
                  nTier1={nTier1}
                />
              ) : (
                <div className="text-sm text-text-subtle italic py-2">
                  No analyst consensus data for this pick.
                </div>
              )}
            </div>
          </div>

          {/* Model reasoning — show ONLY when the model disagreed with the
              tier-1 analyst plurality. Lists the top factors that drove the
              model's alternate pick. */}
          {modelReasoning && analystPick && !analystAgreed && modelReasoning.top_factors.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-text-muted mb-2">
                <Activity size={12} />
                Why the model picked {modelReasoning.player} over analysts' {analystPick}
              </div>
              <ul className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {modelReasoning.top_factors.map((f, i) => (
                  <li
                    key={i}
                    className="text-xs leading-relaxed bg-bg-card border-l-2 border-accent/60 border-y border-r border-border rounded-md p-3"
                  >
                    <div className="font-medium text-text mb-1">{f.label}</div>
                    <div className="text-text-muted">{f.detail}</div>
                  </li>
                ))}
              </ul>
              <div className="mt-2 text-[11px] text-text-subtle font-mono">
                Score breakdown — BPA: {modelReasoning.components.bpa.toFixed(2)} ·
                Need: {modelReasoning.components.need.toFixed(2)} ·
                Visit: {modelReasoning.components.visit.toFixed(2)} ·
                Position multiplier: {modelReasoning.components.pv_mult.toFixed(2)}× ·
                GM affinity: {modelReasoning.components.gm_affinity.toFixed(2)}×
              </div>
            </div>
          )}

          {/* Analyst reasoning — parse the analyst's actual picked player out
              of the reasoning text (pattern: "analyst: PLAYER — ..." or
              "analyst: PLAYER ..."). Only show excerpts where the extracted
              picked-player matches the model's top-1. Avoids showing
              reasoning from analysts who projected a different player. */}
          {(() => {
            const modelPick = top?.player ?? '';
            if (!modelPick) return null;
            const modelLast = modelPick.split(' ').pop()?.toLowerCase() ?? '';
            const modelFirst = modelPick.split(' ')[0]?.toLowerCase() ?? '';

            // Extract the picked-player from each reasoning text using the
            // "Analyst: PlayerName — ..." pattern.
            const extractPick = (text: string): string => {
              // Match first Player name after first colon, ending at " — ",
              // " - ", "(", ";", ".", or end of line/word boundary.
              const m = text.match(/:\s*([A-Z][a-zA-Z.'’\- ]+?)(?=\s*[—–\-(;.,]|\s+\w+ —| $|\n)/);
              return m ? m[1].trim() : '';
            };

            const matching = (reasoning ?? []).filter((r) => {
              const extracted = extractPick(r.text).toLowerCase();
              if (!extracted) return false;
              return (
                (modelLast.length >= 3 && extracted.includes(modelLast)) ||
                (modelFirst.length >= 3 && extracted.includes(modelFirst))
              );
            });

            if (matching.length === 0) return null;
            return (
              <div>
                <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-text-muted mb-2">
                  <Info size={12} />
                  Why analysts project {modelPick} here
                  <span className="font-normal normal-case text-text-subtle ml-1">
                    ({matching.length} of {reasoning?.length ?? 0} analysts agreed)
                  </span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {matching.slice(0, 6).map((r, i) => (
                    <div
                      key={i}
                      className="text-xs leading-relaxed bg-bg-card border border-border rounded-md p-3"
                    >
                      <div className="font-medium text-text-muted mb-1">
                        {r.analyst}
                      </div>
                      <div className="text-text">{r.text}</div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}

          {/* Quick meta + profile link */}
          <div className="flex items-center justify-between pt-2 border-t border-border/60 text-xs text-text-muted">
            <div className="flex items-center gap-4">
              <span>
                Landing variance:
                <span className="ml-1 font-mono text-text">
                  ±{Math.sqrt(top?.variance_landing_pick ?? 0).toFixed(1)} picks
                </span>
              </span>
            </div>
            {team && (
              <Link
                to={`/team/${team.abbr}`}
                className="text-accent hover:underline font-medium"
              >
                Open {team.full} profile →
              </Link>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ----- Analyst table --------------------------------------------------------
function AnalystTable({
  analyst, nTier1,
}: {
  analyst: AnalystPerPick;
  nAnalysts: number;
  nTier1: number;
}) {
  // Top 5 picks by all-analyst count, with tier-1 counts inline
  const top5 = Object.entries(analyst.picks_all ?? {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  if (top5.length === 0) {
    return <div className="text-sm text-text-subtle italic">No analyst picks recorded.</div>;
  }

  const maxAll = Math.max(...top5.map(([_, n]) => n));

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-[10px] uppercase tracking-wider text-text-subtle border-b border-border">
          <th className="text-left font-medium py-1.5 pr-2">Player</th>
          <th className="text-right font-medium py-1.5 w-16">All 20</th>
          <th className="text-right font-medium py-1.5 pl-2 w-16">Tier-1</th>
        </tr>
      </thead>
      <tbody>
        {top5.map(([name, count]) => {
          const tier1Count = analyst.picks_tier1?.[name] ?? 0;
          const isConsensus = name === (analyst.consensus_tier1 || analyst.consensus_player);
          return (
            <tr key={name} className="border-b border-border/60 last:border-0">
              <td className="py-2 pr-2">
                <div className="flex items-center gap-2">
                  <span className={cn(
                    'font-medium',
                    isConsensus ? 'text-text' : 'text-text-muted',
                  )}>
                    {name}
                  </span>
                  {isConsensus && (
                    <span className="badge border-accent/40 bg-accent/10 text-accent text-[9px]">
                      TOP
                    </span>
                  )}
                </div>
              </td>
              <td className="py-2 text-right">
                <div className="inline-flex items-center gap-1.5">
                  <div className="w-10 h-1 bg-bg-hover rounded-full overflow-hidden">
                    <div
                      className="h-full bg-text-muted/60"
                      style={{ width: `${(count / maxAll) * 100}%` }}
                    />
                  </div>
                  <span className="font-mono tabular-nums text-text w-6 text-right">
                    {count}
                  </span>
                </div>
              </td>
              <td className="py-2 pl-2 text-right">
                <span className={cn(
                  'font-mono tabular-nums',
                  tier1Count > 0 ? 'text-text' : 'text-text-subtle',
                )}>
                  {tier1Count}/{nTier1}
                </span>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

// ----- Round-break divider --------------------------------------------------
function RoundBreak({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 my-3 px-1 text-[11px] uppercase tracking-[0.12em] text-text-subtle font-medium">
      <div className="flex-1 h-px bg-border" />
      <span>{label}</span>
      <div className="flex-1 h-px bg-border" />
    </div>
  );
}

// ----- Position mix donut ---------------------------------------------------
function PositionMixChart({ picks }: { picks: PickRow[] }) {
  const counts: Record<string, number> = {};
  for (const p of picks) {
    const pos = p.candidates[0]?.position;
    if (pos) counts[pos] = (counts[pos] ?? 0) + 1;
  }
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((a, [, n]) => a + n, 0) || 1;

  if (entries.length === 0) return null;

  return (
    <div className="card p-5">
      <div className="flex items-center gap-2 mb-1">
        <Target size={14} className="text-accent" />
        <h3 className="text-sm font-semibold tracking-tight">
          R1 position mix
        </h3>
      </div>
      <div className="text-xs text-text-muted mb-4">
        Distribution of modal picks across positions (R1 only).
      </div>

      {/* Horizontal stacked bar */}
      <div className="flex h-8 rounded-md overflow-hidden border border-border">
        {entries.map(([pos, n]) => (
          <div
            key={pos}
            className="relative group flex items-center justify-center transition-all hover:flex-[1.15]"
            style={{
              backgroundColor: positionColor(pos),
              flex: n,
              minWidth: 20,
            }}
            title={`${pos}: ${n} picks (${((n / total) * 100).toFixed(0)}%)`}
          >
            {n >= 2 && (
              <span className="text-[10px] font-semibold text-white/90 mix-blend-screen">
                {pos}
              </span>
            )}
          </div>
        ))}
      </div>

      <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
        {entries.map(([pos, n]) => (
          <div key={pos} className="flex items-center gap-2">
            <span
              className="w-2.5 h-2.5 rounded-sm flex-none"
              style={{ backgroundColor: positionColor(pos) }}
            />
            <span className="text-text-muted flex-1">{pos}</span>
            <span className="font-mono tabular-nums text-text">
              {n}
              <span className="text-text-subtle"> ({((n / total) * 100).toFixed(0)}%)</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ----- Confidence-by-pick chart --------------------------------------------
function ConfidenceByPickChart({ picks }: { picks: PickRow[] }) {
  if (picks.length === 0) return null;
  // Map pick_number -> top probability. Chart shows all 32 slots (blank for
  // picks with no data so the eye can see where certainty drops).
  const probBySlot: Record<number, { prob: number; player: string; position: string }> = {};
  for (const p of picks) {
    const top = p.candidates[0];
    if (top) {
      probBySlot[p.pick_number] = {
        prob: top.probability,
        player: top.player,
        position: top.position,
      };
    }
  }

  return (
    <div className="card p-5">
      <div className="flex items-center gap-2 mb-1">
        <BarChart3 size={14} className="text-accent" />
        <h3 className="text-sm font-semibold tracking-tight">
          Model confidence by pick
        </h3>
      </div>
      <div className="text-xs text-text-muted mb-3">
        Tall bars = model has a clear favorite. Short bars = pick is a coin flip.
      </div>

      {/* 32 bars in a row */}
      <div className="flex items-end gap-[3px] h-24 border-b border-border pb-0.5">
        {Array.from({ length: 32 }, (_, i) => i + 1).map((slot) => {
          const info = probBySlot[slot];
          const pct = info ? info.prob * 100 : 0;
          let color = '#606a80';
          if (pct >= 80) color = '#22c55e';
          else if (pct >= 55) color = '#4ade80';
          else if (pct >= 35) color = '#eab308';
          else if (pct >= 20) color = '#f97316';
          else if (pct > 0) color = '#ef4444';
          return (
            <div
              key={slot}
              className="flex-1 relative group"
              title={info
                ? `Pick ${slot}: ${info.player} (${info.position}) — ${pct.toFixed(0)}%`
                : `Pick ${slot}: no data`}
            >
              <div
                className="w-full rounded-t-sm transition-all group-hover:opacity-80"
                style={{
                  height: info ? `${Math.max(4, pct)}%` : '2%',
                  backgroundColor: color,
                  opacity: info ? 1 : 0.3,
                }}
              />
            </div>
          );
        })}
      </div>

      {/* Axis labels — only every 4th */}
      <div className="flex gap-[3px] mt-1 text-[10px] font-mono text-text-subtle">
        {Array.from({ length: 32 }, (_, i) => i + 1).map((slot) => (
          <div key={slot} className="flex-1 text-center">
            {slot % 4 === 1 || slot === 32 ? slot : ''}
          </div>
        ))}
      </div>
    </div>
  );
}

// ----- Model-vs-analyst agreement chart ------------------------------------
function AgreementChart({
  picks, consensus,
}: {
  picks: PickRow[];
  consensus: any;
}) {
  const perPick = consensus?.per_pick ?? {};
  const data = picks.map((p) => {
    const analyst = perPick[String(p.pick_number)] as AnalystPerPick | undefined;
    const modelPick = p.candidates[0]?.player ?? '';
    const analystPick = analyst?.consensus_tier1 ?? analyst?.consensus_player ?? '';
    // Fuzzy match on last-name token since analyst data uses surnames.
    const agreed =
      modelPick && analystPick &&
      (modelPick.toLowerCase().includes(analystPick.toLowerCase()) ||
       analystPick.toLowerCase().includes(modelPick.split(' ').pop()?.toLowerCase() ?? ''));
    return {
      pick: p.pick_number,
      agreed: agreed ? 1 : 0,
    };
  });

  const totalAgreed = data.reduce((a, d) => a + d.agreed, 0);
  const pct = (totalAgreed / Math.max(1, data.length)) * 100;

  if (data.length === 0 || !consensus?.per_pick) return null;

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <Users size={14} className="text-accent" />
          <h3 className="text-sm font-semibold tracking-tight">
            Model vs analyst agreement
          </h3>
        </div>
        <span className="font-mono text-base font-semibold tabular-nums">
          {pct.toFixed(0)}%
        </span>
      </div>
      <div className="text-xs text-text-muted mb-3">
        Green = model picks the same player as the tier-1 analyst plurality.
      </div>
      <div className="grid grid-cols-16 gap-0.5" style={{gridTemplateColumns: 'repeat(16, 1fr)'}}>
        {data.slice(0, 32).map((d) => (
          <div
            key={d.pick}
            className={cn(
              'h-6 rounded-sm flex items-center justify-center text-[9px] font-mono',
              d.agreed
                ? 'bg-tier-high/30 border border-tier-high/50 text-tier-high'
                : 'bg-tier-midlo/20 border border-tier-midlo/40 text-tier-midlo',
            )}
            title={`Pick ${d.pick}: ${d.agreed ? 'matches' : 'differs from'} tier-1 consensus`}
          >
            {d.pick}
          </div>
        ))}
      </div>
    </div>
  );
}

// ----- Summary stats --------------------------------------------------------
function SummaryStats({ picks }: { picks: PickRow[] }) {
  if (picks.length === 0) return null;
  const avgConf = picks.reduce((a, r) => a + (r.candidates[0]?.probability ?? 0), 0) / picks.length;
  const veryLikely = picks.filter((r) => (r.candidates[0]?.probability ?? 0) >= 0.8).length;
  const longshots = picks.filter((r) => (r.candidates[0]?.probability ?? 0) < 0.3).length;

  // Position distribution — top-3 only so tile doesn't overflow.
  const positions: Record<string, number> = {};
  for (const r of picks) {
    const p = r.candidates[0]?.position;
    if (p) positions[p] = (positions[p] ?? 0) + 1;
  }
  const top3Positions = Object.entries(positions).sort((a, b) => b[1] - a[1]).slice(0, 3);

  const tiles = [
    { Icon: Activity,       label: 'Avg confidence',    value: `${(avgConf * 100).toFixed(0)}%` },
    { Icon: Check,          label: 'Very likely picks', value: `${veryLikely}/${picks.length}` },
    { Icon: AlertTriangle,  label: 'Longshot picks',    value: `${longshots}/${picks.length}` },
    {
      Icon: Target,
      label: 'Top positions',
      value: top3Positions.map(([p, n]) => `${p} ×${n}`).join('   '),
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {tiles.map((t) => (
        <div key={t.label} className="card px-4 py-3">
          <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-text-muted">
            <t.Icon size={12} />
            {t.label}
          </div>
          <div className="text-xl font-semibold mt-1 tabular-nums truncate">
            {t.value || '—'}
          </div>
        </div>
      ))}
    </div>
  );
}

// ----- Main page ------------------------------------------------------------
type ViewMode = 'by_pick' | 'by_team' | 'by_prospect';

// Empirical timing measured April 2026: 50-sim=148s, 150-sim=322s. Linear
// fit: ~60s setup overhead + 1.75s per sim. Setup time covers loading
// stage-1 predictions, prospects, team-agents, analyst consensus, and
// warming the pandas frames. Per-sim cost is dominated by the 32-pick
// override/scoring loop with analyst-consensus blending.
const SECONDS_PER_SIM = 1.75;
const SIM_SETUP_OVERHEAD_S = 60;

function estimateSeconds(nSims: number): number {
  return Math.max(10, Math.round(SIM_SETUP_OVERHEAD_S + nSims * SECONDS_PER_SIM));
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `~${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s > 10 ? `~${m}m ${s}s` : `~${m} minute${m !== 1 ? 's' : ''}`;
}

export function Simulate() {
  // Default 30 sims → ~80s. Small enough to run interactively on the
  // website, large enough to show the key modal picks and a handful of
  // runner-ups. Users can bump to 100/200 for higher-fidelity runs.
  const [n, setN] = useState(30);
  const [sim, setSim] = useState<SimState | null>(null);
  const [picks, setPicks] = useState<PickRow[]>([]);
  const [prospects, setProspects] = useState<ProspectRow[]>([]);
  const [meta, setMeta] = useState<any>(null);
  const [appMeta, setAppMeta] = useState<MetaInfo | null>(null);
  const [consensus, setConsensus] = useState<any>(null);
  const [modelReasoning, setModelReasoning] = useState<Record<string, ModelReasoning>>({});
  const [token, setToken] = useState(() => tokenStore.get());
  const [err, setErr] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [filterLow, setFilterLow] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('by_pick');
  const [teamFilter, setTeamFilter] = useState<string>('ALL');
  const pollRef = useRef<number | null>(null);

  const loadLatest = async () => {
    try {
      const [r, p, mr] = await Promise.all([
        api.latestSim(),
        api.prospectLandings(),
        api.simulationReasoning().catch(() => ({ picks: {} })),
      ]);
      setPicks(r.picks);
      setMeta(r.meta);
      setProspects(p.prospects);
      setModelReasoning(mr.picks as Record<string, ModelReasoning>);
    } catch (e) {
      setErr(String(e));
    }
  };

  // Resume polling if a sim is already running when the user navigates to
  // this page (e.g., they hit "Run", moved to Dashboard, came back).
  const startPolling = () => {
    if (pollRef.current) return;
    pollRef.current = window.setInterval(async () => {
      try {
        const s = await api.simStatus();
        setSim(s);
        if (s.status === 'complete') {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          await loadLatest();
        } else if (s.status === 'error') {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          setErr(s.error || 'Simulation failed');
        }
      } catch {
        /* transient network hiccup — next tick will retry */
      }
    }, 1000);
  };

  useEffect(() => {
    loadLatest();
    api.meta().then(setAppMeta).catch(() => {});
    api.analystConsensus().then(setConsensus).catch(() => {});
    // Initial status check — if a sim is already running, resume polling
    api.simStatus().then((s) => {
      setSim(s);
      if (s.status === 'running') startPolling();
    }).catch(() => {});
    // Cleanup on unmount
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, []);

  const readOnly = appMeta?.share_mode?.read_only ?? false;
  const tokenRequired = appMeta?.share_mode?.token_required ?? false;

  const startSim = async () => {
    setErr(null);
    if (tokenRequired && !token.trim()) {
      setErr('This host requires an auth token to run simulations.');
      return;
    }
    if (tokenRequired) tokenStore.set(token.trim());
    try {
      await api.runSim(n, tokenRequired ? token.trim() : undefined);
      // Kick an immediate status refresh so the UI flips to "running"
      // without waiting a full poll interval.
      const s0 = await api.simStatus();
      setSim(s0);
      startPolling();
    } catch (e) {
      const msg = String(e);
      // 409 = another visitor is already running a sim on this host.
      // Rather than show a raw error, poll so we can watch THEIR run.
      if (msg.includes('409')) {
        setErr(null);
        const s0 = await api.simStatus();
        setSim(s0);
        startPolling();
      } else {
        setErr(msg);
      }
    }
  };

  const running = sim?.status === 'running';
  const toggle = (pn: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(pn) ? next.delete(pn) : next.add(pn);
      return next;
    });
  };
  const expandAll = () => setExpanded(new Set(picks.map((p) => p.pick_number)));
  const collapseAll = () => setExpanded(new Set());

  const dividers: Record<number, string> = {
    1:  'Top of the board · picks 1-10',
    11: 'Mid-first · picks 11-20',
    21: 'Late first · picks 21-32',
  };

  const nAnalysts = consensus?.meta?.n_analysts ?? 0;
  const nTier1 = consensus?.meta?.n_tier1 ?? 0;

  // Filter low-confidence if toggled
  const displayed = filterLow
    ? picks.filter((r) => (r.candidates[0]?.probability ?? 0) >= 0.30)
    : picks;

  return (
    <div className="space-y-5">
      {/* ============ Control panel ============ */}
      <section className="card p-5 md:p-6">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted mb-1">
              Stage 2 — Game-theoretic simulation
            </div>
            <h2 className="text-2xl font-semibold tracking-tight">
              First round Monte Carlo
            </h2>
            <p className="text-sm text-text-muted mt-2 max-w-3xl leading-relaxed">
              Replays the first round hundreds of times with the full intel pipeline:
              scheme fit, cap tier, cascade rules, analyst-consensus blend, trade
              probabilities, GM behavioral fingerprints. Each row below is the modal
              pick for that slot — expand to compare against the 20-mock analyst consensus.
            </p>
          </div>

          <div className="flex flex-wrap items-end gap-3 flex-none">
            {tokenRequired && !readOnly && (
              <div className="flex flex-col gap-1">
                <label className="text-[10px] text-text-muted uppercase tracking-wider flex items-center gap-1">
                  <Lock size={10} /> Token
                </label>
                <input
                  type="password"
                  placeholder="Enter token"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  className="bg-bg-raised border border-border rounded-md px-3 py-2 text-sm w-40 outline-none focus:border-accent font-mono"
                />
              </div>
            )}
            <div className="flex flex-col gap-1">
              <label
                htmlFor="sim-count"
                className="text-[10px] text-text-muted uppercase tracking-wider flex items-center justify-between"
              >
                <span>Simulations</span>
                <span className="font-normal normal-case text-text-subtle">
                  {formatDuration(estimateSeconds(n))}
                </span>
              </label>
              <input
                id="sim-count"
                type="number"
                min={10}
                max={appMeta?.share_mode?.max_sims ?? 5000}
                step={10}
                value={n}
                onChange={(e) => {
                  const cap = appMeta?.share_mode?.max_sims ?? 5000;
                  setN(Math.min(cap, Math.max(10, Number(e.target.value))));
                }}
                disabled={running || readOnly}
                className="bg-bg-raised border border-border rounded-md px-3 py-2 text-sm w-28 outline-none focus:border-accent disabled:opacity-60 font-mono tabular-nums"
                title={`Estimated time: ${formatDuration(estimateSeconds(n))} · Max ${appMeta?.share_mode?.max_sims ?? 5000}`}
              />
              <div className="flex gap-1 text-[10px] text-text-subtle">
                {[30, 50, 100, 200].map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    onClick={() => setN(preset)}
                    disabled={running || readOnly}
                    className={cn(
                      'px-1.5 py-0.5 rounded border transition',
                      n === preset
                        ? 'border-accent text-accent'
                        : 'border-border hover:border-border-strong hover:text-text-muted',
                    )}
                  >
                    {preset}
                  </button>
                ))}
              </div>
            </div>
            <button
              onClick={startSim}
              disabled={running || readOnly}
              title={readOnly ? 'This dashboard is in read-only mode' : undefined}
              className={cn(
                'btn-primary px-5 py-2 text-sm font-semibold',
                'disabled:opacity-60 disabled:cursor-not-allowed',
              )}
            >
              {readOnly ? (
                <><Eye size={16} /> Read-only</>
              ) : running ? (
                <><Loader2 size={16} className="animate-spin" /> Running…</>
              ) : sim?.status === 'complete' ? (
                <><Play size={16} /> Run again</>
              ) : (
                <><Play size={16} /> Run simulation</>
              )}
            </button>
          </div>
        </div>

        {readOnly && (
          <div className="mt-4 text-sm text-text-muted flex items-start gap-2.5 bg-bg-raised border border-border rounded-md px-4 py-3">
            <Eye size={15} className="mt-0.5 flex-none text-text-muted" />
            <div>
              <div className="font-medium text-text">Read-only share mode</div>
              You can browse the latest simulation results but cannot start a new run.
            </div>
          </div>
        )}
      </section>

      {/* ============ Progress / status ============ */}
      {sim && sim.status !== 'idle' && (
        <section className="card p-5">
          {running && (
            <>
              <div className="flex items-center gap-3 mb-3">
                <Loader2 size={18} className="animate-spin text-accent flex-none" />
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-sm">
                    Running {sim.progress_current ?? 0} of {sim.n_simulations} simulations
                  </div>
                  <div className="text-xs text-text-muted">
                    {sim.progress_pct > 0 ? (
                      <>
                        {sim.progress_pct.toFixed(0)}% complete · ETA {formatDuration(
                          Math.max(1, Math.round(estimateSeconds(sim.n_simulations)
                            * (1 - sim.progress_pct / 100)))
                        )}
                      </>
                    ) : (
                      <>Initializing… total estimated: {formatDuration(estimateSeconds(sim.n_simulations))}</>
                    )}
                    <span className="text-text-subtle"> · this host serializes sims, so you may be watching someone else's run</span>
                  </div>
                </div>
                <div className="font-mono text-base font-semibold tabular-nums text-accent flex-none">
                  {(sim.progress_pct ?? 0).toFixed(0)}%
                </div>
              </div>

              {/* Progress bar */}
              <div className="h-2 bg-bg-raised rounded-full overflow-hidden mb-3">
                <div
                  className="h-full bg-gradient-to-r from-accent/70 to-accent transition-all duration-500"
                  style={{ width: `${Math.max(2, sim.progress_pct ?? 0)}%` }}
                />
              </div>

              <details className="text-xs">
                <summary className="cursor-pointer text-text-muted hover:text-text select-none mb-2">
                  Live log (last 25 lines)
                </summary>
                <pre className="max-h-52 overflow-auto bg-bg-raised border border-border rounded-md p-3 font-mono text-text-muted leading-5 whitespace-pre-wrap">
                  {(sim.log_tail ?? []).slice(-25).join('\n') || 'Initializing…'}
                </pre>
              </details>
            </>
          )}
          {sim.status === 'complete' && sim.finished_at && (
            <div className="flex items-center gap-3 text-sm">
              <div className="w-8 h-8 rounded-full bg-tier-high/10 border border-tier-high/40 grid place-items-center">
                <Check size={16} className="text-tier-high" />
              </div>
              <div>
                <div className="font-semibold">
                  Simulation complete · {sim.n_simulations} runs
                </div>
                <div className="text-xs text-text-muted">
                  Finished {fmtDate(sim.finished_at)}
                </div>
              </div>
            </div>
          )}
          {sim.status === 'error' && (
            <div className="flex items-start gap-3 text-sm">
              <AlertTriangle size={18} className="text-tier-low mt-0.5" />
              <div>
                <div className="font-semibold text-tier-low">Simulation failed</div>
                <div className="text-xs text-text-muted font-mono mt-1">
                  {sim.error}
                </div>
              </div>
            </div>
          )}
        </section>
      )}

      {err && !running && (
        <div className="card border-tier-low/40 bg-tier-low/5 p-4 text-sm text-tier-low flex items-start gap-2.5">
          <AlertTriangle size={16} className="mt-0.5 flex-none" />
          <div className="font-mono text-xs">{err}</div>
        </div>
      )}

      {meta && (
        <div className="flex items-center gap-3 text-xs text-text-subtle px-1">
          <Terminal size={12} />
          Latest results: <span className="text-text-muted">{meta.source ?? '—'}</span>
          <span className="text-text-subtle/50">·</span>
          <Clock size={12} />
          <span className="text-text-muted">{meta.mtime ?? '—'}</span>
          {nAnalysts > 0 && (
            <>
              <span className="text-text-subtle/50">·</span>
              <Users size={12} />
              <span className="text-text-muted">
                {nAnalysts} analysts ({nTier1} tier-1)
              </span>
            </>
          )}
        </div>
      )}

      {/* ============ Summary + toolbar ============ */}
      {picks.length > 0 && (
        <>
          <SummaryStats picks={picks} />

          {/* View-mode tabs */}
          <div className="card p-1 inline-flex items-center gap-1">
            {([
              { key: 'by_pick',     label: 'By pick',     hint: 'Draft order' },
              { key: 'by_team',     label: 'By team',     hint: 'Team lens' },
              { key: 'by_prospect', label: 'By prospect', hint: 'Landing distribution' },
            ] as const).map((m) => (
              <button
                key={m.key}
                onClick={() => setViewMode(m.key)}
                className={cn(
                  'px-3.5 py-1.5 rounded-md text-sm font-medium transition',
                  viewMode === m.key
                    ? 'bg-bg-hover text-text shadow-sm'
                    : 'text-text-muted hover:text-text',
                )}
                title={m.hint}
              >
                {m.label}
              </button>
            ))}
          </div>

          {/* Toolbar */}
          <div className="card px-4 py-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-4 flex-wrap text-xs text-text-muted">
              <LegendItem color="bg-tier-high"  label="80%+" />
              <LegendItem color="bg-tier-midhi" label="55-80%" />
              <LegendItem color="bg-tier-mid"   label="35-55%" />
              <LegendItem color="bg-tier-midlo" label="20-35%" />
              <LegendItem color="bg-tier-low"   label="<20%" />
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              {viewMode === 'by_team' && (
                <select
                  value={teamFilter}
                  onChange={(e) => setTeamFilter(e.target.value)}
                  className="bg-bg-raised border border-border rounded-md px-2.5 py-1.5 text-xs outline-none focus:border-accent"
                >
                  <option value="ALL">All teams</option>
                  {Object.values(TEAMS)
                    .sort((a, b) => a.full.localeCompare(b.full))
                    .map((t) => (
                      <option key={t.abbr} value={t.abbr}>{t.full}</option>
                    ))}
                </select>
              )}
              {viewMode === 'by_pick' && (
                <>
                  <label className="flex items-center gap-2 text-xs text-text-muted cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={filterLow}
                      onChange={(e) => setFilterLow(e.target.checked)}
                      className="accent-accent"
                    />
                    Hide longshots (&lt;30%)
                  </label>
                  <div className="h-4 w-px bg-border" />
                  <button
                    onClick={expandAll}
                    className="text-xs px-2.5 py-1 rounded border border-border hover:bg-bg-hover hover:border-border-strong text-text-muted hover:text-text transition"
                  >
                    Expand all
                  </button>
                  <button
                    onClick={collapseAll}
                    className="text-xs px-2.5 py-1 rounded border border-border hover:bg-bg-hover hover:border-border-strong text-text-muted hover:text-text transition"
                  >
                    Collapse
                  </button>
                </>
              )}
            </div>
          </div>
        </>
      )}

      {/* ============ Results ============ */}
      {picks.length > 0 ? (
        <div className="grid grid-cols-1 xl:grid-cols-5 gap-4">
          <div className="xl:col-span-3 space-y-2">
            {viewMode === 'by_pick' && (
              <>
                {displayed.map((r, i) => {
                  const prevPick = i > 0 ? displayed[i - 1].pick_number : 0;
                  const shouldBreak = !!dividers[r.pick_number]
                    && r.pick_number !== prevPick;
                  const perPick =
                    consensus?.per_pick?.[String(r.pick_number)] as AnalystPerPick | undefined;
                  const reasoning =
                    consensus?.reasoning?.[String(r.pick_number)] as
                      | Array<{ analyst: string; text: string }>
                      | undefined;
                  return (
                    <div key={r.pick_number}>
                      {shouldBreak && <RoundBreak label={dividers[r.pick_number]} />}
                      <PickCard
                        row={r}
                        expanded={expanded.has(r.pick_number)}
                        onToggle={() => toggle(r.pick_number)}
                        analyst={perPick}
                        reasoning={reasoning}
                        modelReasoning={modelReasoning[String(r.pick_number)]}
                        nAnalysts={nAnalysts}
                        nTier1={nTier1}
                      />
                    </div>
                  );
                })}
                {displayed.length === 0 && filterLow && (
                  <div className="card p-6 text-center text-sm text-text-muted">
                    All picks are below the 30% confidence threshold.
                    <button
                      onClick={() => setFilterLow(false)}
                      className="ml-1 text-accent hover:underline"
                    >
                      Show all picks
                    </button>
                  </div>
                )}
              </>
            )}

            {viewMode === 'by_team' && (
              <TeamView
                teamFilter={teamFilter}
                picks={picks}
                prospects={prospects}
              />
            )}

            {viewMode === 'by_prospect' && (
              <ProspectView prospects={prospects} />
            )}
          </div>

          <aside className="xl:col-span-2 space-y-3 xl:sticky xl:top-28 xl:self-start">
            <PositionMixChart picks={picks} />
            <ConfidenceByPickChart picks={picks} />
            <AgreementChart picks={picks} consensus={consensus} />
          </aside>
        </div>
      ) : (
        <div className="card p-8">
          <div className="flex items-start gap-4">
            <div className="w-1 h-12 bg-accent rounded-full flex-none" />
            <div>
              <h3 className="text-base font-semibold mb-1">No simulation results yet</h3>
              <p className="text-sm text-text-muted max-w-lg">
                Click <span className="font-medium text-text">Run simulation</span> above
                to generate a Monte Carlo mock draft. Results appear here when complete —
                500 sims typically take 60-90 seconds.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ----- By-team view ---------------------------------------------------------
function TeamView({
  teamFilter, picks, prospects,
}: {
  teamFilter: string;
  picks: PickRow[];
  prospects: ProspectRow[];
}) {
  // When ALL is selected, show every team's R1 picks in a compact list.
  const teamsWithPicks = Array.from(new Set(picks.map((p) => p.team).filter(Boolean) as string[]));

  if (teamFilter !== 'ALL') {
    const team = teamMeta(teamFilter);
    const teamPicks = picks.filter((p) => p.team === teamFilter);
    if (!team) return <div className="card p-6 text-sm text-text-muted">Team not found.</div>;
    if (teamPicks.length === 0) {
      return (
        <div className="card p-6">
          <div className="flex items-center gap-3 mb-2">
            <img src={team.logo} alt="" className="w-10 h-10 object-contain"
                 onError={(e) => ((e.target as HTMLImageElement).style.display = 'none')} />
            <div>
              <div className="font-semibold">{team.full}</div>
              <div className="text-xs text-text-muted">No R1 picks owned in this sim.</div>
            </div>
          </div>
        </div>
      );
    }
    return (
      <div className="space-y-3">
        <div className="card p-5" style={{ borderLeft: `4px solid ${team.primary}` }}>
          <div className="flex items-center gap-3">
            <img src={team.logo} alt="" className="w-12 h-12 object-contain"
                 onError={(e) => ((e.target as HTMLImageElement).style.display = 'none')} />
            <div className="flex-1">
              <div className="text-lg font-semibold">{team.full}</div>
              <div className="text-xs text-text-muted">
                {teamPicks.length} R1 pick{teamPicks.length !== 1 ? 's' : ''} ·
                picks {teamPicks.map((p) => `#${p.pick_number}`).join(', ')}
              </div>
            </div>
            <Link
              to={`/team/${team.abbr}`}
              className="text-xs text-accent hover:underline font-medium whitespace-nowrap"
            >
              Full team profile →
            </Link>
          </div>
        </div>

        {teamPicks.map((pick) => (
          <TeamPickDetail key={pick.pick_number} pick={pick} team={team} />
        ))}

        {/* Related prospects — ones whose landing distribution includes this team */}
        <ProspectsForTeam
          teamAbbr={team.abbr}
          prospects={prospects}
        />
      </div>
    );
  }

  // ALL teams compact view
  return (
    <div className="card divide-y divide-border">
      {teamsWithPicks.sort((a, b) => {
        const paMin = Math.min(...picks.filter(p => p.team === a).map(p => p.pick_number));
        const pbMin = Math.min(...picks.filter(p => p.team === b).map(p => p.pick_number));
        return paMin - pbMin;
      }).map((abbr) => {
        const team = teamMeta(abbr);
        if (!team) return null;
        const teamPicks = picks.filter((p) => p.team === abbr);
        return (
          <div key={abbr} className="px-4 py-3 flex items-center gap-3"
               style={{ borderLeft: `3px solid ${team.primary}` }}>
            <img src={team.logo} alt="" className="w-7 h-7 object-contain flex-none"
                 onError={(e) => ((e.target as HTMLImageElement).style.display = 'none')} />
            <div className="flex-1 min-w-0">
              <div className="font-medium text-sm truncate">{team.full}</div>
              <div className="text-xs text-text-muted">
                {teamPicks.map((p) => {
                  const top = p.candidates[0];
                  return top ? `#${p.pick_number}: ${top.player} (${top.position})` : `#${p.pick_number}`;
                }).join(' · ')}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function TeamPickDetail({ pick, team }: { pick: PickRow; team: any }) {
  const top = pick.candidates[0];
  const tier = confidenceTier(top?.probability ?? 0);
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-text-muted">
            Pick #{pick.pick_number}
          </div>
          <div className="text-base font-semibold mt-1">
            Candidates across simulations
          </div>
        </div>
        <span className={cn(
          'badge',
          tier.color,
          `border-current bg-current/10`,
        )}>
          Top: {((top?.probability ?? 0) * 100).toFixed(0)}% {tier.label}
        </span>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[10px] uppercase tracking-wider text-text-subtle border-b border-border">
            <th className="text-left font-medium py-2 pr-2 w-8">#</th>
            <th className="text-left font-medium py-2 pr-2">Player</th>
            <th className="text-left font-medium py-2 pr-2">College</th>
            <th className="text-right font-medium py-2 w-16">Cons</th>
            <th className="text-right font-medium py-2 pl-2 w-40">Probability</th>
          </tr>
        </thead>
        <tbody>
          {pick.candidates.map((c, i) => (
            <tr key={c.player} className="border-b border-border/60 last:border-0">
              <td className="py-2 pr-2 font-mono text-text-subtle text-xs">
                {i + 1}
              </td>
              <td className="py-2 pr-2">
                <div className="flex items-center gap-2">
                  <span
                    className="badge flex-none"
                    style={{
                      color: positionColor(c.position),
                      borderColor: `${positionColor(c.position)}4D`,
                      backgroundColor: `${positionColor(c.position)}1A`,
                    }}
                  >
                    {c.position}
                  </span>
                  <span className="font-medium text-text">{c.player}</span>
                </div>
              </td>
              <td className="py-2 pr-2 text-xs text-text-muted">{c.college}</td>
              <td className="py-2 text-right font-mono text-xs text-text-muted">
                {c.consensus_rank != null ? `#${c.consensus_rank}` : '—'}
              </td>
              <td className="py-2 pl-2">
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1.5 bg-bg-hover rounded-full overflow-hidden">
                    <div
                      className="h-full"
                      style={{
                        width: `${c.probability * 100}%`,
                        background: `linear-gradient(90deg, ${team.primary}99, ${team.primary})`,
                      }}
                    />
                  </div>
                  <span className="font-mono text-xs tabular-nums text-text w-10 text-right">
                    {(c.probability * 100).toFixed(0)}%
                  </span>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ProspectsForTeam({
  teamAbbr, prospects,
}: {
  teamAbbr: string;
  prospects: ProspectRow[];
}) {
  const related = prospects
    .filter((p) => p.landings.some((l) => l.team === teamAbbr))
    .map((p) => ({
      ...p,
      team_prob: p.landings.filter((l) => l.team === teamAbbr)
                            .reduce((a, l) => a + l.probability, 0),
    }))
    .filter((p) => p.team_prob >= 0.05)
    .sort((a, b) => b.team_prob - a.team_prob)
    .slice(0, 15);

  if (related.length === 0) return null;

  return (
    <div className="card p-5">
      <div className="flex items-center gap-2 mb-1">
        <Users size={14} className="text-accent" />
        <h3 className="text-sm font-semibold tracking-tight">
          Prospects landing with this team ≥5% of sims
        </h3>
      </div>
      <div className="text-xs text-text-muted mb-3">
        All prospects who landed with this team in at least 5% of simulations, across any pick slot.
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-[10px] uppercase tracking-wider text-text-subtle border-b border-border">
            <th className="text-left font-medium py-1.5 pr-2">Player</th>
            <th className="text-right font-medium py-1.5 w-16">Cons</th>
            <th className="text-right font-medium py-1.5 pl-2 w-40">Team landing %</th>
          </tr>
        </thead>
        <tbody>
          {related.map((p) => (
            <tr key={p.player} className="border-b border-border/60 last:border-0">
              <td className="py-2 pr-2">
                <div className="flex items-center gap-2">
                  <span
                    className="badge flex-none"
                    style={{
                      color: positionColor(p.position),
                      borderColor: `${positionColor(p.position)}4D`,
                      backgroundColor: `${positionColor(p.position)}1A`,
                    }}
                  >
                    {p.position}
                  </span>
                  <span className="font-medium text-text">{p.player}</span>
                  <span className="text-xs text-text-subtle">{p.college}</span>
                </div>
              </td>
              <td className="py-2 text-right font-mono text-xs text-text-muted">
                {p.consensus_rank != null ? `#${p.consensus_rank}` : '—'}
              </td>
              <td className="py-2 pl-2">
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1.5 bg-bg-hover rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent/70"
                      style={{ width: `${p.team_prob * 100}%` }}
                    />
                  </div>
                  <span className="font-mono text-xs tabular-nums text-text w-10 text-right">
                    {(p.team_prob * 100).toFixed(0)}%
                  </span>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ----- By-prospect view -----------------------------------------------------
function ProspectView({ prospects }: { prospects: ProspectRow[] }) {
  const [search, setSearch] = useState('');
  const [posFilter, setPosFilter] = useState('ALL');
  const [sortKey, setSortKey] = useState<'mean' | 'variance' | 'rank'>('mean');

  const positions = Array.from(new Set(prospects.map((p) => p.position).filter(Boolean))).sort();

  const filtered = prospects
    .filter((p) => {
      if (posFilter !== 'ALL' && p.position !== posFilter) return false;
      if (search && !p.player.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    })
    .sort((a, b) => {
      switch (sortKey) {
        case 'variance':
          return b.variance_landing - a.variance_landing;
        case 'rank':
          return (a.consensus_rank ?? 999) - (b.consensus_rank ?? 999);
        default:
          return a.mean_landing - b.mean_landing;
      }
    });

  return (
    <div className="space-y-3">
      <div className="card p-3 flex flex-wrap items-center gap-3">
        <input
          type="text"
          placeholder="Search prospect…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="bg-bg-raised border border-border rounded-md px-3 py-1.5 text-sm flex-1 min-w-[180px] outline-none focus:border-accent"
        />
        <select
          value={posFilter}
          onChange={(e) => setPosFilter(e.target.value)}
          className="bg-bg-raised border border-border rounded-md px-3 py-1.5 text-sm outline-none focus:border-accent"
        >
          <option value="ALL">All positions</option>
          {positions.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <select
          value={sortKey}
          onChange={(e) => setSortKey(e.target.value as any)}
          className="bg-bg-raised border border-border rounded-md px-3 py-1.5 text-sm outline-none focus:border-accent"
        >
          <option value="mean">Sort: mean landing</option>
          <option value="variance">Sort: variance</option>
          <option value="rank">Sort: consensus rank</option>
        </select>
        <div className="text-xs text-text-subtle ml-auto">
          {filtered.length} / {prospects.length}
        </div>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[10px] uppercase tracking-wider text-text-subtle border-b border-border bg-bg-raised/60">
              <th className="text-left font-medium py-2.5 px-4">Player</th>
              <th className="text-right font-medium py-2.5 px-2 w-16">Cons</th>
              <th className="text-right font-medium py-2.5 px-2 w-24">Mean pick</th>
              <th className="text-right font-medium py-2.5 px-2 w-20">±StDev</th>
              <th className="text-left font-medium py-2.5 px-2 w-32">Top landing</th>
              <th className="text-right font-medium py-2.5 px-4 w-16">R1%</th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 80).map((p) => {
              const topLanding = p.landings[0];
              const stdev = Math.sqrt(p.variance_landing).toFixed(1);
              return (
                <tr
                  key={p.player}
                  className="border-b border-border/60 last:border-0 hover:bg-bg-hover/40"
                >
                  <td className="py-2 px-4">
                    <div className="flex items-center gap-2">
                      <span
                        className="badge flex-none"
                        style={{
                          color: positionColor(p.position),
                          borderColor: `${positionColor(p.position)}4D`,
                          backgroundColor: `${positionColor(p.position)}1A`,
                        }}
                      >
                        {p.position}
                      </span>
                      <div>
                        <div className="font-medium text-text">{p.player}</div>
                        <div className="text-xs text-text-subtle">{p.college}</div>
                      </div>
                    </div>
                  </td>
                  <td className="py-2 px-2 text-right font-mono text-xs text-text-muted">
                    {p.consensus_rank != null ? `#${p.consensus_rank}` : '—'}
                  </td>
                  <td className="py-2 px-2 text-right font-mono tabular-nums">
                    {p.mean_landing.toFixed(1)}
                  </td>
                  <td className="py-2 px-2 text-right font-mono tabular-nums text-text-muted text-xs">
                    ±{stdev}
                  </td>
                  <td className="py-2 px-2">
                    {topLanding && (
                      <div className="flex items-center gap-2 text-xs">
                        <span className="font-medium">
                          {topLanding.team ?? '—'}
                        </span>
                        <span className="text-text-subtle">
                          #{topLanding.slot} ({(topLanding.probability * 100).toFixed(0)}%)
                        </span>
                      </div>
                    )}
                  </td>
                  <td className="py-2 px-4 text-right font-mono tabular-nums text-text-muted">
                    {(p.total_prob * 100).toFixed(0)}%
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {filtered.length > 80 && (
          <div className="px-4 py-2 text-[11px] text-text-subtle bg-bg-raised/40 border-t border-border">
            Showing first 80 of {filtered.length} — refine filters to narrow.
          </div>
        )}
      </div>
    </div>
  );
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5 whitespace-nowrap">
      <span className={cn('w-2 h-2 rounded-full flex-none', color)} />
      <span>{label}</span>
    </span>
  );
}
