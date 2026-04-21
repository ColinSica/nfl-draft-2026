/**
 * Watchlist — starred picks stored in localStorage.
 * Users can star a pick (player + slot) and see starred items across pages.
 */

const KEY = 'draft-predictor-watchlist-v1';

export type WatchItem = {
  player: string;
  slot?: number;
  team?: string;
  addedAt: number;
};

function read(): WatchItem[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch { return []; }
}

function write(items: WatchItem[]) {
  try { localStorage.setItem(KEY, JSON.stringify(items)); } catch {}
  // Tell other hooks in the same tab to refresh
  window.dispatchEvent(new CustomEvent('watchlist-change'));
}

export const watchlist = {
  all: read,

  has(player: string): boolean {
    return read().some(w => w.player === player);
  },

  toggle(player: string, meta?: { slot?: number; team?: string }) {
    const items = read();
    const idx = items.findIndex(w => w.player === player);
    if (idx >= 0) items.splice(idx, 1);
    else items.push({ player, slot: meta?.slot, team: meta?.team, addedAt: Date.now() });
    write(items);
  },

  remove(player: string) {
    write(read().filter(w => w.player !== player));
  },

  clear() {
    write([]);
  },
};

// React hook
import { useEffect, useState } from 'react';

export function useWatchlist() {
  const [items, setItems] = useState<WatchItem[]>(watchlist.all());

  useEffect(() => {
    const refresh = () => setItems(watchlist.all());
    window.addEventListener('watchlist-change', refresh);
    window.addEventListener('storage', refresh);
    return () => {
      window.removeEventListener('watchlist-change', refresh);
      window.removeEventListener('storage', refresh);
    };
  }, []);

  return {
    items,
    has: (player: string) => items.some(w => w.player === player),
    toggle: (player: string, meta?: { slot?: number; team?: string }) => {
      watchlist.toggle(player, meta);
    },
    remove: (p: string) => watchlist.remove(p),
    clear: () => watchlist.clear(),
    count: items.length,
  };
}
