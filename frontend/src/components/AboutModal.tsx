import { useEffect } from 'react';
import { X, Sparkles, Database, BarChart3, Shield } from 'lucide-react';
import { cn } from '../lib/format';

export function AboutModal({
  open, onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in"
      onClick={onClose}
    >
      <div
        className={cn(
          'card p-6 max-w-2xl w-full max-h-[85vh] overflow-y-auto',
          'border-border-strong',
        )}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-accent to-violet-400 grid place-items-center shadow-glow">
              <span className="text-xs font-bold text-white">2026</span>
            </div>
            <div>
              <h2 className="text-xl font-semibold tracking-tight">
                About this model
              </h2>
              <div className="text-xs text-text-muted">
                Created by <span className="text-text font-medium">Colin Sica</span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-md hover:bg-bg-hover text-text-muted hover:text-text transition"
          >
            <X size={18} />
          </button>
        </div>

        <div className="space-y-4 text-sm leading-6">
          <Section Icon={Sparkles} title="What you're looking at">
            A two-stage predictive model for the 2026 NFL Draft. Stage 1 ranks
            prospects using combine metrics, college production, and analyst
            boards. Stage 2 is a game-theoretic Monte Carlo simulator that
            drafts for all 32 teams given their rosters, schemes, GM
            behavioral patterns, cap situation, and live visit intel.
          </Section>

          <Section Icon={Database} title="Per-team profile sources">
            Every team card pulls from: a comprehensive 2026 draft PDF report
            (team context, GM fingerprints, archetypes); nflverse 2025 roster
            data for age cliffs; historical drafts 2011-2025 for GM positional
            tendencies; daily visit/market/stock-move scrapes (nfltr, PFN,
            WalterFootball, CBS, Vegas Insider, TWSN); public cap-constraint
            fallback derived from the PDF narrative.
          </Section>

          <Section Icon={BarChart3} title="What the sim does">
            For each simulation run the model walks picks 1 through 32.
            High-confidence slots use scripted intel overrides (e.g. Mendoza
            to LV at -20000 odds); everything else uses a scoring function
            that weights BPA, need (with latent + scheme-premium + injury +
            age-cliff + previous-year-repeat adjustments), confirmed visits,
            GM positional affinity, cap tier, and coach-prospect college
            connections. Trades are sampled probabilistically using the PDF's
            per-GM tiers, with hard constraints like "NO never trades down"
            enforced.
          </Section>

          <Section Icon={Shield} title="What it is NOT">
            Not a guarantee. The predictability tier on each team reflects
            genuine uncertainty — LOW teams (new regimes, trade-heavy GMs)
            have wide output distributions by design. Treat the probabilities
            as distributions over realistic scenarios, not point forecasts.
          </Section>
        </div>

        <div className="mt-5 pt-4 border-t border-border text-[11px] text-text-subtle flex items-center justify-between">
          <span>Press <kbd className="kbd">Esc</kbd> to close</span>
          <span>© {new Date().getFullYear()} Colin Sica</span>
        </div>
      </div>
    </div>
  );
}

function Section({
  Icon, title, children,
}: {
  Icon: React.ComponentType<{ size?: number; className?: string }>;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-text-muted mb-1.5">
        <Icon size={12} />
        {title}
      </div>
      <p className="text-text-muted">{children}</p>
    </div>
  );
}
