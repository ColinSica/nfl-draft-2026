// Presentation dictionary — converts raw model values into human strings.
// User requirement: never show None/nan/broken placeholders.

export function displayValue<T>(v: T | null | undefined, fallback = 'Not available'): string {
  if (v === null || v === undefined) return fallback;
  const s = String(v).trim();
  if (!s || s.toLowerCase() === 'nan' || s.toLowerCase() === 'none' || s === 'null') {
    return fallback;
  }
  return s;
}

export function displayNum(
  v: number | null | undefined,
  opts: { fallback?: string; digits?: number; suffix?: string } = {}
): string {
  const { fallback = 'n/a', digits = 0, suffix = '' } = opts;
  if (v === null || v === undefined || Number.isNaN(v)) return fallback;
  return v.toFixed(digits) + suffix;
}

export function displayPct(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  return (v * 100).toFixed(digits) + '%';
}

// Human-readable QB situation labels
const QB_SITUATION: Record<string, string> = {
  locked: 'QB locked in',
  bridge: 'Bridge QB in place',
  rebuilding: 'Rebuilding at QB',
  watson_locked_ceiling_uncertain: 'Contract-locked but uncertain',
  open_r1_candidate: 'Open R1 QB candidate',
};

export function displayQbSituation(v: string | null | undefined): string {
  if (!v) return 'QB situation unclear';
  return QB_SITUATION[v] ?? v.replace(/_/g, ' ');
}

// Human-readable cap tier
const CAP_TIER: Record<string, string> = {
  tight:    'Cap-tight',
  moderate: 'Moderate cap',
  flexible: 'Cap-flexible',
  abundant: 'Cap-abundant',
};

export function displayCapTier(v: string | null | undefined): string {
  if (!v) return 'Cap unclear';
  return CAP_TIER[v.toLowerCase()] ?? v;
}

// Pressure / predictability labels
export function displayPredictability(v: string | null | undefined): string {
  if (!v) return 'Predictability: n/a';
  return v.charAt(0).toUpperCase() + v.slice(1).toLowerCase();
}

// QB urgency numeric -> human string
export function displayQbUrgency(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return 'Not urgent';
  if (v >= 0.8) return 'Critical QB need';
  if (v >= 0.5) return 'Moderate QB need';
  if (v >= 0.3) return 'Low QB need';
  return 'Not urgent';
}

// Freshness relative time
export function relTime(iso: string | null | undefined): string {
  if (!iso) return 'not yet computed';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return 'unknown';
  const diff = Date.now() - d.getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function freshnessState(iso: string | null | undefined): 'fresh' | 'stale' | 'missing' {
  if (!iso) return 'missing';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return 'missing';
  const hrs = (Date.now() - d.getTime()) / 3600000;
  if (hrs < 24) return 'fresh';
  if (hrs < 168) return 'stale';
  return 'missing';
}
