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
  variance_landing_pick: number;
};

export type PickRow = {
  pick_number: number;
  team: string | null;
  original_team?: string | null;
  most_likely_team?: string | null;
  candidates: Candidate[];
};

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

export type SimState = {
  status: 'idle' | 'running' | 'complete' | 'error';
  started_at: string | null;
  finished_at: string | null;
  n_simulations: number;
  progress_current: number;
  progress_pct: number;
  log_tail: string[];
  error: string | null;
};

async function getJson<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}: ${url}`);
  return r.json();
}

async function postJson<T>(url: string, body: unknown, token?: string): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) headers['X-Auth-Token'] = token;
  const r = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`${r.status} ${r.statusText}: ${text}`);
  }
  return r.json();
}

// Token persistence across page loads (localStorage). Only used when
// /api/meta reports share_mode.token_required === true.
const TOKEN_KEY = 'draft_dash_auth_token';
export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY) || '',
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export const api = {
  teams: () => getJson<{ teams: TeamSummary[] }>('/api/teams'),
  team: (abbr: string) => getJson<any>(`/api/teams/${abbr}`),
  league: () => getJson<any>('/api/league'),
  meta: () => getJson<MetaInfo>('/api/meta'),
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
  simulateReplay: (forcedPicks: Record<number, string>, nSims = 10) =>
    postJson<{ picks: PickRow[]; meta: any }>(
      '/api/simulate/replay',
      { forced_picks: forcedPicks, n_simulations: nSims },
    ),
  runSim: (n: number, token?: string) =>
    postJson<{ status: string }>(
      '/api/simulate',
      { n_simulations: n },
      token,
    ),
  simStatus: () => getJson<SimState>('/api/simulate/status'),
};
