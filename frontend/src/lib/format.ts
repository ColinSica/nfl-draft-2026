import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const PREDICTABILITY_COLOR: Record<string, string> = {
  HIGH: 'text-tier-high border-tier-high/40 bg-tier-high/10',
  'MEDIUM-HIGH': 'text-tier-midhi border-tier-midhi/40 bg-tier-midhi/10',
  MEDIUM: 'text-tier-mid border-tier-mid/40 bg-tier-mid/10',
  'LOW-MEDIUM': 'text-tier-midlo border-tier-midlo/40 bg-tier-midlo/10',
  LOW: 'text-tier-low border-tier-low/40 bg-tier-low/10',
};

export function tierClass(tier: string | null | undefined) {
  return PREDICTABILITY_COLOR[tier ?? ''] ?? 'text-text-muted border-border bg-bg-raised';
}

export function fmtDate(iso: string | null | undefined) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
  } catch {
    return iso;
  }
}

export function fmtPct(x: number | null | undefined, digits = 1) {
  if (x == null || Number.isNaN(x)) return '—';
  return `${(x * 100).toFixed(digits)}%`;
}
