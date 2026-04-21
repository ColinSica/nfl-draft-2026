// Editorial primitives — hairline rules, small-caps labels, stat displays.
// Used throughout the product as its visual signature.

import { type ReactNode } from 'react';

export function HRule({ thick = false, className = '' }: { thick?: boolean; className?: string }) {
  return <hr className={`${thick ? 'hrule-thick' : 'hrule'} ${className}`} />;
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
        className={big ? 'stat-big' : 'display-serif text-2xl font-semibold'}
        style={{ color: accent ?? '#EDE7D8' }}
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
    <header className={`space-y-2 ${className}`}>
      <div className="flex items-baseline gap-3">
        {number !== undefined && (
          <span className="display-serif text-sm text-paper-subtle font-mono">
            §{String(number).padStart(2, '0')}
          </span>
        )}
        {kicker && <span className="caps-tight text-mode-indie">{kicker}</span>}
      </div>
      <h2 className="display-serif text-3xl md:text-4xl font-semibold tracking-tight">
        {title}
      </h2>
      <HRule className="rule-draw" />
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
