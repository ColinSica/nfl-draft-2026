// Thin typed wrapper around the FastAPI backend. In dev, Vite proxies /api
// to localhost:8000 (see vite.config.ts); in prod, FastAPI serves this SPA.

export type TopNeed = { pos: string; score: number };

export type TeamSummary = {
  team: string;
  gm: string | null;
  hc: string | null;
  new_hc: boolean;
  new_gm: boolean;
  win_pct: number | null;
  r1_picks: number[];
  total_picks: number;
  qb_situation: string | null;
  qb_urgency: number | null;
  predictability: string;
  top_needs: TopNeed[];
  scheme_type: string;
  scheme_premium: string[];
  capital_abundance: string | null;
  n_confirmed_visits: number;
  cap_tier: string | null;
  trade_up_rate: number | null;
  trade_down_rate: number | null;
};

export type MetaInfo = {
  generated_at?: string;
  schema_version?: string;
  source_mtimes?: Record<string, string | null>;
  analyst_intel_meta?: {
    latest_intel_date?: string;
    sources?: Record<string, string[]>;
  };
  share_mode?: {
    read_only: boolean;
    token_required: boolean;
    max_sims?: number;
  };
  files_present?: Record<string, boolean>;
  files_mtime?: Record<string, string | null>;
};

export type Candidate = {
  player: string;
  position: string;
  college: string | null;
  probability: number;
  team: string | null;
  consensus_rank: number | null;
  variance_landing_pick?: number;
};

export type PickRow = {
  pick_number: number;
  team: string | null;
  original_team?: string | null;
  most_likely_team?: string | null;
  candidates: Candidate[];
};

// Variance is optional because /api/simulate/replay (mock-draft rebuild)
// doesn't compute per-slot variance — only /api/simulations/latest does.

// Prospect-centric row — aggregated landing distribution for one player
// across all simulated slots. Computed client-side from latestSim picks.
export type ProspectRow = {
  player: string;
  position: string;
  college: string | null;
  consensus_rank: number | null;
  landings: { slot: number; team: string | null; probability: number }[];
  mean_landing: number;
  variance_landing: number;
  total_prob: number;
  most_likely_slot: number;
  most_likely_team: string | null;
};

async function getJson<T>(url: string): Promise<T> {
  let r: Response;
  try {
    r = await fetch(url);
  } catch (netErr: any) {
    throw new Error(`Network unreachable (${url}): ${netErr?.message ?? netErr}`);
  }
  if (!r.ok) {
    // Pull the body so server-side error detail survives into the UI.
    let body = '';
    try { body = (await r.text()).slice(0, 400); } catch { /* noop */ }
    const detail = body ? ` — ${body.replace(/\s+/g, ' ').trim()}` : '';
    throw new Error(`${r.status} ${r.statusText} at ${url}${detail}`);
  }
  try {
    return (await r.json()) as T;
  } catch {
    throw new Error(`Invalid JSON from ${url}`);
  }
}

// One-shot promise cache for endpoints that are safe to share across
// components mounted in the same session. Meta is the obvious case — the
// app header and Home both ask for it on mount.
const cache = new Map<string, Promise<any>>();
function cachedJson<T>(url: string): Promise<T> {
  const hit = cache.get(url);
  if (hit) return hit as Promise<T>;
  const p = getJson<T>(url).catch(err => {
    // Don't poison the cache on failure — let the next caller retry.
    cache.delete(url);
    throw err;
  });
  cache.set(url, p);
  return p;
}

export const api = {
  teams: () => getJson<{ teams: TeamSummary[] }>('/api/teams'),
  team: (abbr: string) => getJson<any>(`/api/teams/${abbr}`),
  league: () => getJson<any>('/api/league'),
  meta: () => cachedJson<MetaInfo>('/api/meta'),
  prospects: (limit = 64) =>
    getJson<{ prospects: any[]; count: number }>(
      `/api/prospects?limit=${limit}`,
    ),
  analystConsensus: () => getJson<any>('/api/analyst-consensus'),
  latestSim: () =>
    getJson<{ picks: PickRow[]; meta: any }>('/api/simulations/latest'),
  simulationTrades: () =>
    getJson<{
      n_simulations: number;
      total_trade_events: number;
      per_pick: Record<string, Array<{
        from_team: string;
        to_team: string;
        prob: number;
        count: number;
        reason?: string;
        trade_type?: string;
        compensation?: string;
        slots_moved?: number;
        top_targets: Array<{ player: string; count: number }>;
      }>>;
    }>('/api/simulations/trades'),
  prospectLandings: () =>
    getJson<{ prospects: ProspectRow[]; meta: any }>(
      '/api/simulations/prospects',
    ),
  simulationReasoning: () =>
    getJson<{ picks: Record<string, any>; meta: any }>(
      '/api/simulations/reasoning',
    ),
};
