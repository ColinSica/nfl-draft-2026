// Persistent mode context — the product's organizing principle.
// Independent: analyst-independent model output (the core)
// Benchmark:   analyst consensus view (comparison-only)
import { createContext, useContext, useEffect, useState } from 'react';

export type Mode = 'independent' | 'benchmark';

export const MODE_META: Record<Mode, {
  label: string;
  caption: string;
  description: string;
  accent: string;
  accentDim: string;
}> = {
  independent: {
    label: 'Independent',
    caption: 'Model prediction',
    description:
      'Analyst-independent prediction engine. Stage 1 builds the board from tape and traits. Stage 2 simulates the draft with 32 team agents. Analyst picks are not used as input.',
    accent: '#B68A2F',
    accentDim: '#7A5D00',
  },
  benchmark: {
    label: 'Benchmark',
    caption: 'Analyst consensus',
    description:
      'Aggregate of public analyst mocks and big boards. Shown for comparison only — never feeds into the Independent model.',
    accent: '#1F6FEB',
    accentDim: '#104399',
  },
};

type Ctx = {
  mode: Mode;
  setMode: (m: Mode) => void;
};

const ModeContext = createContext<Ctx>({
  mode: 'independent',
  setMode: () => {},
});

const STORAGE_KEY = 'draft-predictor-mode';

export function ModeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<Mode>(() => {
    if (typeof window === 'undefined') return 'independent';
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved === 'independent' || saved === 'benchmark') return saved;
    } catch { /* private-browsing, fine */ }
    return 'independent';
  });

  const setMode = (m: Mode) => {
    setModeState(m);
    try { localStorage.setItem(STORAGE_KEY, m); } catch {}
  };

  // Reflect mode on <html data-mode="..."> for CSS hooks
  useEffect(() => {
    document.documentElement.dataset.mode = mode;
  }, [mode]);

  return (
    <ModeContext.Provider value={{ mode, setMode }}>
      {children}
    </ModeContext.Provider>
  );
}

export function useMode() { return useContext(ModeContext); }
