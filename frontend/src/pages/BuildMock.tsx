import { useEffect, useMemo, useReducer, useState } from 'react';
import {
  Search, Undo2, RotateCcw, Download, ArrowRightLeft, Check,
  ChevronRight, X, PencilLine, Zap, Loader2,
} from 'lucide-react';
import { api } from '../lib/api';
import { cn } from '../lib/format';
import { TEAMS, teamMeta, positionColor } from '../lib/teams';

// -----------------------------------------------------------------------------
// Types + state
// -----------------------------------------------------------------------------

type DraftPick = {
  pick_number: number;
  team: string;            // current owner (may differ after trades)
  original_team: string;   // who originally held this slot
  player: string | null;
  position: string | null;
  college: string | null;
  consensus_rank: number | null;
  source: 'user' | 'model' | null;
};

type Prospect = {
  player: string;
  position: string | null;
  college: string | null;
  rank: number | null;
};

type ModelSimPick = {
  pick_number: number;
  team: string | null;
  player: string | null;
  position: string | null;
  college: string | null;
  consensus_rank: number | null;
};

type State = {
  picks: DraftPick[];
  currentPick: number;               // 1-32
  taken: Set<string>;                // player names
  history: Array<Action>;            // for undo
  mode: 'full' | 'team';
  selectedTeam: string | null;       // team mode: who the user is drafting for
};

type Action =
  | { type: 'draft'; pick_number: number; prospect: Prospect; source: 'user' | 'model' }
  | { type: 'trade'; pick_a: number; pick_b: number }
  | { type: 'unpick'; pick_number: number; prev: DraftPick }
  | { type: 'undo' }
  | { type: 'reset'; next: State };

const STORAGE_KEY = 'draft_dash_custom_mock';

// -----------------------------------------------------------------------------
// Initial state builder — every slot starts unassigned with its current team
// ownership (from the model).
// -----------------------------------------------------------------------------
function makeInitialState(modelPicks: ModelSimPick[], mode: 'full' | 'team',
                          selectedTeam: string | null): State {
  const picks: DraftPick[] = [];
  for (let pn = 1; pn <= 32; pn++) {
    const m = modelPicks.find((p) => p.pick_number === pn);
    picks.push({
      pick_number:    pn,
      team:           m?.team ?? 'TBD',
      original_team:  m?.team ?? 'TBD',
      player:         null,
      position:       null,
      college:        null,
      consensus_rank: null,
      source:         null,
    });
  }
  return {
    picks,
    currentPick: 1,
    taken: new Set<string>(),
    history: [],
    mode,
    selectedTeam,
  };
}

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'draft': {
      const picks = state.picks.map((p) =>
        p.pick_number === action.pick_number
          ? {
              ...p,
              player: action.prospect.player,
              position: action.prospect.position,
              college: action.prospect.college,
              consensus_rank: action.prospect.rank,
              source: action.source,
            }
          : p
      );
      const taken = new Set(state.taken);
      taken.add(action.prospect.player);
      // Advance currentPick to next unfilled slot (or stay if none).
      let next = state.currentPick;
      while (next <= 32 && picks.find((p) => p.pick_number === next)?.player) {
        next += 1;
      }
      return {
        ...state,
        picks,
        taken,
        currentPick: next,
        history: [...state.history, action],
      };
    }
    case 'trade': {
      const picks = state.picks.map((p) => {
        if (p.pick_number === action.pick_a) {
          const other = state.picks.find((x) => x.pick_number === action.pick_b)!;
          return { ...p, team: other.team };
        }
        if (p.pick_number === action.pick_b) {
          const other = state.picks.find((x) => x.pick_number === action.pick_a)!;
          return { ...p, team: other.team };
        }
        return p;
      });
      return {
        ...state,
        picks,
        history: [...state.history, action],
      };
    }
    case 'unpick': {
      const picks = state.picks.map((p) =>
        p.pick_number === action.pick_number ? action.prev : p
      );
      const taken = new Set(state.taken);
      if (action.prev.player === null && state.picks.find((p) =>
        p.pick_number === action.pick_number)?.player
      ) {
        const removed = state.picks.find((p) =>
          p.pick_number === action.pick_number)!.player!;
        taken.delete(removed);
      }
      return {
        ...state,
        picks,
        taken,
        currentPick: Math.min(state.currentPick, action.pick_number),
        history: state.history.slice(0, -1),
      };
    }
    case 'undo': {
      const last = state.history[state.history.length - 1];
      if (!last) return state;
      if (last.type === 'draft') {
        const picks = state.picks.map((p) =>
          p.pick_number === last.pick_number
            ? {
                ...p,
                player: null,
                position: null,
                college: null,
                consensus_rank: null,
                source: null,
              }
            : p
        );
        const taken = new Set(state.taken);
        taken.delete(last.prospect.player);
        return {
          ...state,
          picks,
          taken,
          currentPick: Math.min(state.currentPick, last.pick_number),
          history: state.history.slice(0, -1),
        };
      }
      if (last.type === 'trade') {
        // Re-swap to revert, drop the recorded trade.
        const picks = state.picks.map((p) => {
          if (p.pick_number === last.pick_a) {
            const other = state.picks.find((x) => x.pick_number === last.pick_b)!;
            return { ...p, team: other.team };
          }
          if (p.pick_number === last.pick_b) {
            const other = state.picks.find((x) => x.pick_number === last.pick_a)!;
            return { ...p, team: other.team };
          }
          return p;
        });
        return { ...state, picks, history: state.history.slice(0, -1) };
      }
      return state;
    }
    case 'reset':
      return action.next;
    default:
      return state;
  }
}

// -----------------------------------------------------------------------------
// Main page
// -----------------------------------------------------------------------------
export function BuildMock() {
  const [prospects, setProspects] = useState<Prospect[]>([]);
  const [modelPicks, setModelPicks] = useState<ModelSimPick[]>([]);
  const [loaded, setLoaded] = useState(false);

  // Hydrate data
  useEffect(() => {
    Promise.all([
      api.prospects(120),
      api.latestSim(),
    ]).then(([p, s]) => {
      setProspects(p.prospects as Prospect[]);
      // Flatten the sim's top-1 per slot
      const mp: ModelSimPick[] = [];
      for (const r of s.picks) {
        const top = r.candidates[0];
        mp.push({
          pick_number: r.pick_number,
          team: r.team,
          player: top?.player ?? null,
          position: top?.position ?? null,
          college: top?.college ?? null,
          consensus_rank: top?.consensus_rank ?? null,
        });
      }
      setModelPicks(mp);
      setLoaded(true);
    });
  }, []);

  // Restore from localStorage or make fresh
  const [state, dispatch] = useReducer(reducer, null as any, () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        return { ...parsed, taken: new Set(parsed.taken) };
      }
    } catch { /* ignore */ }
    return makeInitialState([], 'full', null);
  });

  // Re-init once model picks arrive, but only if the current state has
  // no teams assigned yet (saved state already has real teams). This
  // runs exactly once after data hydrates so team-mode users get the
  // proper pick template even before making a pick.
  useEffect(() => {
    if (!loaded) return;
    if (state.picks.every((p) => p.team === 'TBD')) {
      dispatch({
        type: 'reset',
        next: makeInitialState(modelPicks, state.mode, state.selectedTeam),
      });
    }
  }, [loaded, modelPicks]);

  // Persist on every change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        ...state,
        taken: Array.from(state.taken),
      }));
    } catch { /* ignore quota errors */ }
  }, [state]);

  // UI state
  const [search, setSearch] = useState('');
  const [posFilter, setPosFilter] = useState('ALL');
  const [tradeOpen, setTradeOpen] = useState(false);
  const [replaying, setReplaying] = useState(false);
  const [replayError, setReplayError] = useState<string | null>(null);

  // Re-cascade: call /api/simulate/replay with all user-picked forced picks
  // and refresh the unfilled slots with new model predictions.
  const recascade = async () => {
    const forced: Record<number, string> = {};
    for (const p of state.picks) {
      if (p.player && p.source === 'user') {
        forced[p.pick_number] = p.player;
      }
    }
    if (Object.keys(forced).length === 0) {
      setReplayError('Make at least one pick first before re-running the model.');
      return;
    }
    setReplaying(true);
    setReplayError(null);
    try {
      const r = await api.simulateReplay(forced, 10);
      // Update model-source picks with fresh predictions from replay.
      for (const slot of r.picks) {
        const top = slot.candidates[0];
        if (!top) continue;
        const existing = state.picks.find((x) => x.pick_number === slot.pick_number);
        // Only update if this pick is NOT a user pick (don't overwrite user choices).
        if (!existing || existing.source === 'user') continue;
        dispatch({
          type: 'draft',
          pick_number: slot.pick_number,
          prospect: {
            player: top.player,
            position: top.position,
            college: top.college,
            rank: top.consensus_rank,
          },
          source: 'model',
        });
      }
    } catch (e) {
      setReplayError(String(e));
    } finally {
      setReplaying(false);
    }
  };

  const positions = useMemo(
    () => Array.from(new Set(prospects.map((p) => p.position).filter(Boolean) as string[])).sort(),
    [prospects],
  );

  const available = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return prospects
      .filter((p) => !state.taken.has(p.player))
      .filter((p) => posFilter === 'ALL' || p.position === posFilter)
      .filter((p) =>
        !needle ||
        p.player.toLowerCase().includes(needle) ||
        (p.college ?? '').toLowerCase().includes(needle)
      )
      .sort((a, b) => (a.rank ?? 999) - (b.rank ?? 999))
      .slice(0, 60);
  }, [prospects, state.taken, search, posFilter]);

  const currentPickObj = state.picks.find((p) => p.pick_number === state.currentPick);
  const currentTeam = teamMeta(currentPickObj?.team);

  // In team mode, auto-fill picks for non-selected teams with model prediction
  const autoFillOthers = () => {
    if (state.mode !== 'team' || !state.selectedTeam) return;
    let pn = state.currentPick;
    while (pn <= 32) {
      const pick = state.picks.find((p) => p.pick_number === pn);
      if (!pick || pick.player) { pn += 1; continue; }
      if (pick.team === state.selectedTeam) break;   // stop at user's team
      const modelPlayer = modelPicks.find((m) => m.pick_number === pn);
      if (modelPlayer?.player && !state.taken.has(modelPlayer.player)) {
        dispatch({
          type: 'draft',
          pick_number: pn,
          prospect: {
            player: modelPlayer.player,
            position: modelPlayer.position,
            college: modelPlayer.college,
            rank: modelPlayer.consensus_rank,
          },
          source: 'model',
        });
      }
      pn += 1;
    }
  };

  // Trigger auto-fill when in team mode and current pick is NOT user's team
  useEffect(() => {
    if (state.mode === 'team' && state.selectedTeam
        && currentPickObj && currentPickObj.team !== state.selectedTeam
        && !currentPickObj.player) {
      // Slight delay to let UI render "advancing" state
      const t = setTimeout(autoFillOthers, 100);
      return () => clearTimeout(t);
    }
  }, [state.currentPick, state.mode, state.selectedTeam]);

  const reset = () => {
    if (!confirm('Reset the entire mock draft? Your picks will be cleared.')) return;
    dispatch({
      type: 'reset',
      next: makeInitialState(modelPicks, state.mode, state.selectedTeam),
    });
  };

  const undo = () => dispatch({ type: 'undo' });

  const exportMock = () => {
    const blob = new Blob([JSON.stringify({
      generated_at: new Date().toISOString(),
      mode: state.mode,
      selected_team: state.selectedTeam,
      picks: state.picks,
    }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `my_mock_draft_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const pickSelectableNow = state.mode === 'full'
    || (state.mode === 'team' && currentPickObj?.team === state.selectedTeam);

  const filledCount = state.picks.filter((p) => p.player).length;
  const isDone = filledCount === 32;

  if (!loaded) {
    return <div className="text-text-muted text-sm">Loading draft board…</div>;
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted mb-1">
            Manual mock draft builder
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">Build your own mock</h1>
          <p className="text-sm text-text-muted mt-1 max-w-3xl">
            Pick for every slot, or pick for just one team and let the model
            fill in the other 31 teams. Make trades, undo mistakes, save your
            mock as JSON.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {filledCount > 0 && (
            <div className="text-xs text-text-muted px-3 py-1.5 bg-bg-raised border border-border rounded-md">
              <span className="font-mono font-semibold text-text">{filledCount}</span>/32 picks
            </div>
          )}
          <button onClick={undo} disabled={state.history.length === 0}
            className="btn-ghost text-xs py-1.5 px-3 disabled:opacity-50 disabled:cursor-not-allowed"
            title="Undo last pick or trade">
            <Undo2 size={14} /> Undo
          </button>
          <button
            onClick={recascade}
            disabled={replaying}
            className="btn-primary text-xs py-1.5 px-3 disabled:opacity-60"
            title="Re-run the model with all your picks locked in — downstream slots update to reflect the new board"
          >
            {replaying
              ? <><Loader2 size={14} className="animate-spin" /> Re-running…</>
              : <><Zap size={14} /> Re-cascade model</>}
          </button>
          <button onClick={() => setTradeOpen(true)}
            className="btn-ghost text-xs py-1.5 px-3">
            <ArrowRightLeft size={14} /> Trade picks
          </button>
          <button onClick={exportMock} disabled={filledCount === 0}
            className="btn-ghost text-xs py-1.5 px-3 disabled:opacity-50">
            <Download size={14} /> Export
          </button>
          <button onClick={reset}
            className="btn-ghost text-xs py-1.5 px-3 border-tier-low/40 text-tier-low hover:bg-tier-low/10">
            <RotateCcw size={14} /> Reset
          </button>
        </div>
      </div>

      {/* Mode toggle */}
      <div className="card p-3 flex items-center gap-2 sm:gap-3 flex-wrap">
        <span className="text-xs text-text-muted uppercase tracking-wider">Mode:</span>
        <button
          onClick={() => {
            if (state.mode === 'full') return;
            if (filledCount > 0 && !confirm('Switching mode resets the draft. Continue?')) return;
            dispatch({ type: 'reset', next: makeInitialState(modelPicks, 'full', null) });
          }}
          className={cn('px-3 py-1.5 rounded-md text-sm font-medium transition',
            state.mode === 'full' ? 'bg-accent text-white' : 'bg-bg-raised text-text-muted hover:text-text')}
        >
          Full draft (32 picks)
        </button>
        <button
          onClick={() => {
            if (state.mode === 'team') return;
            if (filledCount > 0 && !confirm('Switching mode resets the draft. Continue?')) return;
            dispatch({
              type: 'reset',
              next: makeInitialState(modelPicks, 'team', state.selectedTeam ?? 'NYG'),
            });
          }}
          className={cn('px-3 py-1.5 rounded-md text-sm font-medium transition',
            state.mode === 'team' ? 'bg-accent text-white' : 'bg-bg-raised text-text-muted hover:text-text')}
        >
          Team-only (pick for one team)
        </button>

        {state.mode === 'team' && (
          <>
            <span className="text-xs text-text-muted">drafting for:</span>
            <select
              value={state.selectedTeam ?? 'NYG'}
              onChange={(e) => {
                dispatch({
                  type: 'reset',
                  next: makeInitialState(modelPicks, 'team', e.target.value),
                });
              }}
              className="bg-bg-raised border border-border rounded-md px-2.5 py-1.5 text-sm outline-none focus:border-accent"
            >
              {Object.values(TEAMS)
                .sort((a, b) => a.full.localeCompare(b.full))
                .map((t) => (
                  <option key={t.abbr} value={t.abbr}>{t.full}</option>
                ))}
            </select>
          </>
        )}

        <span className="w-full sm:w-auto sm:ml-auto text-xs text-text-subtle">
          Autosaves locally — refresh and your draft will still be here.
        </span>
      </div>

      {replayError && (
        <div className="card p-3 text-xs text-tier-low bg-tier-low/5 border-tier-low/30">
          {replayError}
        </div>
      )}

      {replaying && (
        <div className="card p-3 text-xs text-text-muted flex items-center gap-2">
          <Loader2 size={14} className="animate-spin text-accent" />
          Re-running the model with your picks locked in — typically 30-40 seconds for a 10-sim replay.
        </div>
      )}

      {/* Done state */}
      {isDone && (
        <div className="card p-5 border-tier-high/40">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-tier-high/10 border border-tier-high/40 grid place-items-center">
              <Check size={18} className="text-tier-high" />
            </div>
            <div>
              <div className="font-semibold">Mock draft complete</div>
              <div className="text-sm text-text-muted">
                All 32 R1 picks assigned. Export JSON or continue tweaking.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main split */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* DRAFT BOARD */}
        <div className="lg:col-span-3 space-y-1.5">
          {state.picks.map((pick) => (
            <DraftRow
              key={pick.pick_number}
              pick={pick}
              isCurrent={pick.pick_number === state.currentPick}
              isUserTeam={state.mode === 'team' && pick.team === state.selectedTeam}
              onClick={() => {
                // Click a completed pick to jump back + re-edit
                if (pick.player) {
                  if (confirm(`Un-pick ${pick.player} and redo this pick?`)) {
                    dispatch({
                      type: 'unpick',
                      pick_number: pick.pick_number,
                      prev: { ...pick, player: null, position: null,
                              college: null, consensus_rank: null, source: null },
                    });
                  }
                }
              }}
            />
          ))}
        </div>

        {/* AVAILABLE PLAYERS */}
        <aside className="lg:col-span-2 space-y-3 lg:sticky lg:top-28 lg:self-start">
          <div className="card p-4">
            {/* Who's on the clock */}
            <div className="flex items-center gap-2 mb-3">
              <div
                className="w-1 h-8 rounded-full flex-none"
                style={{ backgroundColor: currentTeam?.primary ?? '#303648' }}
              />
              <div className="flex-1 min-w-0">
                <div className="text-[10px] uppercase tracking-wider text-text-muted">
                  {pickSelectableNow ? 'On the clock' : 'Model auto-picking'}
                </div>
                <div className="font-semibold text-sm truncate">
                  Pick #{state.currentPick} · {currentTeam?.full ?? currentPickObj?.team}
                </div>
              </div>
              {state.mode === 'team' && currentPickObj?.team === state.selectedTeam && (
                <span className="badge border-accent/40 bg-accent/10 text-accent">
                  <PencilLine size={10} /> your pick
                </span>
              )}
            </div>

            {pickSelectableNow ? (
              <>
                <div className="flex items-center gap-2 px-3 py-1.5 bg-bg-raised border border-border rounded-md mb-2">
                  <Search size={13} className="text-text-subtle" />
                  <input
                    placeholder="Search player / college"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="bg-transparent outline-none flex-1 text-sm"
                  />
                </div>
                <select
                  value={posFilter}
                  onChange={(e) => setPosFilter(e.target.value)}
                  className="w-full bg-bg-raised border border-border rounded-md px-3 py-1.5 text-sm outline-none focus:border-accent mb-2"
                >
                  <option value="ALL">All positions</option>
                  {positions.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>

                <div className="max-h-[520px] overflow-y-auto space-y-1 pr-1">
                  {available.length === 0 ? (
                    <div className="text-xs text-text-subtle p-3">No matches.</div>
                  ) : (
                    available.map((p) => (
                      <button
                        key={p.player}
                        onClick={() => dispatch({
                          type: 'draft',
                          pick_number: state.currentPick,
                          prospect: p,
                          source: 'user',
                        })}
                        className="w-full text-left px-3 py-2 rounded-md border border-border hover:border-accent/60 hover:bg-bg-hover/60 transition"
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs text-text-subtle w-8 text-right tabular-nums">
                            {p.rank != null ? `#${p.rank}` : '—'}
                          </span>
                          {p.position && (
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
                          )}
                          <span className="flex-1 text-sm text-text font-medium truncate">
                            {p.player}
                          </span>
                          <span className="text-[11px] text-text-muted truncate max-w-[90px]">
                            {p.college ?? ''}
                          </span>
                        </div>
                      </button>
                    ))
                  )}
                </div>
              </>
            ) : (
              <div className="text-xs text-text-muted italic py-4 text-center">
                Waiting for non-user teams to pick (using model predictions)…
              </div>
            )}
          </div>
        </aside>
      </div>

      {tradeOpen && (
        <TradeModal
          state={state}
          onClose={() => setTradeOpen(false)}
          onTrade={(a, b) => {
            dispatch({ type: 'trade', pick_a: a, pick_b: b });
            setTradeOpen(false);
          }}
        />
      )}
    </div>
  );
}

// -----------------------------------------------------------------------------
// Draft board row
// -----------------------------------------------------------------------------
function DraftRow({ pick, isCurrent, isUserTeam, onClick }: {
  pick: DraftPick;
  isCurrent: boolean;
  isUserTeam: boolean;
  onClick: () => void;
}) {
  const team = teamMeta(pick.team);
  const traded = pick.team !== pick.original_team;
  const posColor = positionColor(pick.position);

  return (
    <button
      onClick={onClick}
      disabled={!pick.player}
      className={cn(
        'w-full text-left card p-3 flex items-center gap-3 transition',
        isCurrent && !pick.player && 'ring-2 ring-accent/60 shadow-glow',
        isUserTeam && 'border-accent/40',
        pick.player && 'hover:border-border-strong cursor-pointer',
        !pick.player && !isCurrent && 'opacity-75',
      )}
      style={{ borderLeft: `3px solid ${team?.primary ?? '#303648'}` }}
    >
      <div className="font-mono text-xl font-semibold w-8 text-center tabular-nums flex-none">
        {pick.pick_number}
      </div>

      <div className="flex items-center gap-2 w-32 flex-none min-w-0">
        {team && (
          <img src={team.logo} alt="" className="w-6 h-6 object-contain flex-none"
               onError={(e) => ((e.target as HTMLImageElement).style.display = 'none')} />
        )}
        <div className="min-w-0">
          <div className="text-sm font-medium truncate">{team?.abbr ?? pick.team}</div>
          {traded && (
            <div className="text-[9px] text-accent flex items-center gap-0.5 truncate">
              <ArrowRightLeft size={9} /> from {pick.original_team}
            </div>
          )}
        </div>
      </div>

      {pick.player ? (
        <>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              {pick.position && (
                <span
                  className="badge flex-none"
                  style={{
                    color: posColor,
                    borderColor: `${posColor}4D`,
                    backgroundColor: `${posColor}1A`,
                  }}
                >
                  {pick.position}
                </span>
              )}
              <span className="text-sm font-semibold truncate">{pick.player}</span>
              {pick.consensus_rank && (
                <span className="text-[10px] text-text-subtle font-mono">
                  #{pick.consensus_rank}
                </span>
              )}
            </div>
            <div className="text-[11px] text-text-muted truncate">{pick.college}</div>
          </div>
          <div className="flex-none text-[10px] text-text-subtle flex items-center gap-1">
            {pick.source === 'user' ? (
              <><PencilLine size={10} className="text-accent" /> your pick</>
            ) : (
              <>model</>
            )}
          </div>
        </>
      ) : (
        <div className="flex-1 text-sm text-text-muted italic flex items-center gap-1.5">
          {isCurrent ? (
            <><ChevronRight size={14} className="text-accent" /> Pick now</>
          ) : (
            'awaiting pick'
          )}
        </div>
      )}
    </button>
  );
}

// -----------------------------------------------------------------------------
// Trade modal — swap ownership of two picks
// -----------------------------------------------------------------------------
function TradeModal({ state, onClose, onTrade }: {
  state: State;
  onClose: () => void;
  onTrade: (pickA: number, pickB: number) => void;
}) {
  const [pickA, setPickA] = useState<number>(state.currentPick);
  const [pickB, setPickB] = useState<number>(
    state.picks.find((p) => p.pick_number !== state.currentPick && !p.player)?.pick_number
      ?? state.currentPick + 1,
  );

  const unfilledPicks = state.picks.filter((p) => !p.player);
  const picksByNumber = (pn: number) => state.picks.find((p) => p.pick_number === pn);

  const a = picksByNumber(pickA);
  const b = picksByNumber(pickB);
  const canTrade = a && b && pickA !== pickB && !a.player && !b.player;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="card p-6 max-w-xl w-full border-border-strong"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold">Trade picks</h3>
            <p className="text-xs text-text-muted mt-1 max-w-sm">
              Swap ownership of two unpicked R1 slots. Players already drafted
              can't be included. Compensation isn't tracked — this is a
              simplified swap (like ESPN's quick-trade tool).
            </p>
          </div>
          <button onClick={onClose}
            className="p-1 text-text-muted hover:text-text">
            <X size={18} />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <TradeSide
            label="Pick A"
            value={pickA}
            onChange={setPickA}
            picks={unfilledPicks}
            detail={a}
          />
          <TradeSide
            label="Pick B"
            value={pickB}
            onChange={setPickB}
            picks={unfilledPicks}
            detail={b}
          />
        </div>

        {canTrade && a && b && (
          <div className="bg-bg-raised border border-border rounded-md p-3 text-sm mb-4">
            <div className="text-[10px] uppercase tracking-wider text-text-muted mb-1">
              After trade
            </div>
            <div className="flex items-center gap-2">
              <span className="font-mono font-semibold">#{a.pick_number}</span>
              <span className="text-text-muted">→</span>
              <span className="font-semibold">{b.team}</span>
              <span className="text-text-subtle mx-2">·</span>
              <span className="font-mono font-semibold">#{b.pick_number}</span>
              <span className="text-text-muted">→</span>
              <span className="font-semibold">{a.team}</span>
            </div>
          </div>
        )}

        <div className="flex items-center justify-end gap-2">
          <button onClick={onClose} className="btn-ghost text-sm">
            Cancel
          </button>
          <button
            onClick={() => onTrade(pickA, pickB)}
            disabled={!canTrade}
            className="btn-primary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ArrowRightLeft size={14} /> Execute trade
          </button>
        </div>
      </div>
    </div>
  );
}

function TradeSide({ label, value, onChange, picks, detail }: {
  label: string;
  value: number;
  onChange: (n: number) => void;
  picks: DraftPick[];
  detail: DraftPick | undefined;
}) {
  const team = teamMeta(detail?.team);
  return (
    <div className="bg-bg-raised border border-border rounded-md p-3">
      <div className="text-[10px] uppercase tracking-wider text-text-muted mb-1">
        {label}
      </div>
      <select
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full bg-bg border border-border rounded-md px-2 py-1.5 text-sm outline-none focus:border-accent font-mono mb-2"
      >
        {picks.map((p) => (
          <option key={p.pick_number} value={p.pick_number}>
            #{p.pick_number} — {p.team}
          </option>
        ))}
      </select>
      {detail && team && (
        <div className="flex items-center gap-2 text-sm">
          <img src={team.logo} alt="" className="w-7 h-7 object-contain flex-none"
               onError={(e) => ((e.target as HTMLImageElement).style.display = 'none')} />
          <div className="min-w-0">
            <div className="font-semibold truncate">{team.full}</div>
            <div className="text-[11px] text-text-muted">currently owns #{detail.pick_number}</div>
          </div>
        </div>
      )}
    </div>
  );
}
