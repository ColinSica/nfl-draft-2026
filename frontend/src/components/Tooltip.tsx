import { useState, type ReactNode } from 'react';
import { HelpCircle } from 'lucide-react';
import { cn } from '../lib/format';

// A lightweight controlled tooltip — hover on desktop, tap on mobile. No
// third-party Popper/Radix dependency; positions itself via absolute
// placement within a relatively-positioned parent.
export function Tooltip({
  text,
  children,
  side = 'top',
  className,
}: {
  text: string;
  children?: ReactNode;
  side?: 'top' | 'bottom' | 'right' | 'left';
  className?: string;
}) {
  const [open, setOpen] = useState(false);

  return (
    <span
      className={cn('relative inline-flex items-center', className)}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {children ?? (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setOpen((o) => !o);
          }}
          className="inline-flex text-text-subtle hover:text-text-muted transition"
          aria-label="More info"
        >
          <HelpCircle size={12} />
        </button>
      )}
      {open && (
        <span
          className={cn(
            'absolute z-50 w-64 px-3 py-2 text-xs leading-5 text-text',
            'bg-bg-card border border-border rounded-lg shadow-card',
            'pointer-events-none',
            side === 'top' && 'bottom-full left-1/2 -translate-x-1/2 mb-2',
            side === 'bottom' && 'top-full left-1/2 -translate-x-1/2 mt-2',
            side === 'right' && 'left-full top-1/2 -translate-y-1/2 ml-2',
            side === 'left' && 'right-full top-1/2 -translate-y-1/2 mr-2',
          )}
        >
          {text}
        </span>
      )}
    </span>
  );
}

// Glossary of dashboard jargon — single source of truth so tooltip text
// stays consistent across pages.
export const GLOSSARY = {
  predictability: 'How confident the model is in this team\'s R1 pick. HIGH (LV Mendoza, TB Licht) means the archetype and player are both clear; LOW means regime change, trade-heavy, or multiple live archetypes.',
  scheme: 'The team\'s offensive/defensive system (e.g. Shanahan zone, Bradley Cover-3). Drives which body types and skill sets the front office prefers.',
  cap: 'Salary-cap tier derived from public cap space + dead money. TIGHT teams avoid high-APY rookies unless forced; FLUSH teams accept premium picks more freely.',
  trade_up: 'Historical rate at which this GM has traded UP in the first round. Higher = more likely to jump slots for a target.',
  trade_down: 'Historical rate at which this GM has traded DOWN in the first round. Higher = more likely to accumulate picks.',
  need_score: 'Severity of the roster need at that position. 5.0 = catastrophic hole; 3.0 = clear need; 1.0 = depth concern only. Latent needs score ~2.0 at half weight.',
  consensus_rank: 'The player\'s rank on aggregated analyst big boards. Pick #N << consensus #M means the team reached down the board.',
  variance: 'How much this player\'s landing pick swings across simulations. Higher = the model is uncertain where they go.',
  qb_urgency: 'How likely the team is to take a QB in R1. 0 = QB-locked (no R1 QB); 1.0 = desperate (Mendoza to LV).',
  predictability_high: 'HIGH predictability: archetype + player both clear. Model will be very tight.',
  predictability_low:  'LOW predictability: multiple plausible archetypes, trade-heavy GM, or regime change. Model will be loose.',
};
