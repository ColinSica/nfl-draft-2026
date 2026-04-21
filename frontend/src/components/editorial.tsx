// Broadcast/editorial primitives — hairlines, small-caps, stat display.
import { type ReactNode } from 'react';

export function HRule({ thick = false, live = false, accent = false, className = '' }: {
  thick?: boolean;
  live?: boolean;
  accent?: boolean;
  className?: string;
}) {
  const cls = live ? 'hrule-live' : accent ? 'hrule-accent' : thick ? 'hrule-thick' : 'hrule';
  return <hr className={`${cls} ${className}`} />;
}

export function SmallCaps({
  children,
  as: As = 'span' as any,
  className = '',
  tight = false,
}: {
  children: ReactNode;
  as?: any;
  className?: string;
  tight?: boolean;
}) {
  return (
    <As className={`${tight ? 'caps-tight' : 'caps'} ${className}`}>
      {children}
    </As>
  );
}

export function Stat({
  label,
  value,
  sub,
  big = false,
  accent,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  big?: boolean;
  accent?: string;
}) {
  return (
    <div className="space-y-1">
      <div className="caps-tight text-paper-subtle">{label}</div>
      <div
        className={big ? 'stat-big' : 'display-broadcast text-3xl'}
        style={{ color: accent ?? '#F3F6FA' }}
      >
        {value}
      </div>
      {sub && <div className="text-xs text-paper-muted">{sub}</div>}
    </div>
  );
}

export function SectionHeader({
  number,
  kicker,
  title,
  className = '',
}: {
  number?: string | number;
  kicker?: string;
  title: string;
  className?: string;
}) {
  return (
    <header className={`space-y-3 ${className}`}>
      <div className="flex items-baseline gap-3">
        {number !== undefined && (
          <span className="display-num font-mono text-sm text-paper-subtle">
            §{String(number).padStart(2, '0')}
          </span>
        )}
        {kicker && <span className="caps text-mode-indie">{kicker}</span>}
      </div>
      <h2 className="display-broadcast text-4xl md:text-5xl tracking-tight">
        {title}
      </h2>
      <HRule accent className="rule-draw" />
    </header>
  );
}

export function MissingText({ children = 'Not available' }: { children?: ReactNode }) {
  return (
    <span className="italic text-paper-subtle text-sm">
      {children}
    </span>
  );
}

/** Pulsing LIVE / ON THE CLOCK indicator */
export function LiveBadge({ children = 'Live' }: { children?: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-2 px-2.5 py-1 caps-tight bg-live/10 text-live border border-live/40">
      <span className="live-dot" />
      {children}
    </span>
  );
}
