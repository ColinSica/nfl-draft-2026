// The Draft Ledger — editorial primitives.
// Serif headlines, mono labels, hairline rules. Every component below is the
// front-page vocabulary of the site: headers, kickers, datelines, stat grids.
import { type ReactNode } from 'react';

export function HRule({ thick = false, live = false, accent = false, double = false, className = '' }: {
  thick?: boolean;
  live?: boolean;
  accent?: boolean;
  double?: boolean;
  className?: string;
}) {
  const cls = live ? 'hrule-live'
            : double ? 'hrule-double'
            : accent ? 'hrule-accent'
            : thick ? 'hrule-thick'
            : 'hrule';
  return <hr className={`${cls} ${className}`} />;
}

export function SmallCaps({
  children,
  as: As = 'span' as any,
  className = '',
  tight = false,
  style,
}: {
  children: ReactNode;
  as?: any;
  className?: string;
  tight?: boolean;
  style?: React.CSSProperties;
}) {
  return (
    <As className={`${tight ? 'caps-tight' : 'caps'} ${className}`} style={style}>
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
    <div className="space-y-1.5">
      <div className="mono-label">{label}</div>
      <div
        className={big ? 'stat-big' : 'display-num text-3xl'}
        style={{ color: accent ?? '#1A1612' }}
      >
        {value}
      </div>
      {sub && <div className="text-caption text-ink-muted font-serif">{sub}</div>}
    </div>
  );
}

/**
 * SectionHeader — the broadsheet dateline above every major section.
 * Heavy top rule + kicker + headline + hairline bottom rule.
 */
export function SectionHeader({
  number,
  kicker,
  title,
  deck,
  className = '',
}: {
  number?: string | number;
  kicker?: string;
  title: string;
  deck?: string;          // optional sub-headline/standfirst
  className?: string;
}) {
  return (
    <header className={`space-y-4 ${className}`}>
      <HRule thick />
      <div className="flex items-center justify-between gap-4 flex-wrap pt-1">
        <div className="flex items-baseline gap-3">
          {number !== undefined && (
            <span className="display-num text-sm text-accent-salmon">
              § {String(number).padStart(2, '0')}
            </span>
          )}
          {kicker && <span className="caps">{kicker}</span>}
        </div>
      </div>
      <h2 className="display-broadcast text-ink"
          style={{ fontSize: 'clamp(1.875rem, 3.8vw, 3rem)' }}>
        {title}
      </h2>
      {deck && (
        <p className="body-serif-lead text-ink-soft max-w-3xl"
           style={{ fontStyle: 'italic', fontWeight: 400 }}>
          {deck}
        </p>
      )}
      <HRule />
    </header>
  );
}

export function MissingText({ children = 'Not available' }: { children?: ReactNode }) {
  return (
    <span className="italic text-ink-muted text-sm font-serif">
      {children}
    </span>
  );
}

export function LiveBadge({ children = 'Live' }: { children?: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-2 px-2 py-0.5 caps-tight border border-live text-live">
      <span className="live-dot" />
      {children}
    </span>
  );
}

/**
 * Dateline — the top-of-page newspaper metadata strip.
 * Use once per page, usually directly under the masthead.
 */
export function Dateline({
  volume = 'Vol. I',
  issue,
  date,
  location = 'Seattle',
}: {
  volume?: string;
  issue?: string;
  date?: string;
  location?: string;
}) {
  const today = date ?? new Date().toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  });
  return (
    <div className="dateline flex items-center gap-3 flex-wrap border-y border-ink py-1.5 px-1 text-ink">
      <span>{volume}</span>
      <span className="text-ink-edge">·</span>
      {issue && (<>
        <span>{issue}</span>
        <span className="text-ink-edge">·</span>
      </>)}
      <span>{today}</span>
      <span className="text-ink-edge">·</span>
      <span>{location}</span>
      <span className="ml-auto caps-tight text-ink-muted">Price · Free edition</span>
    </div>
  );
}

/**
 * Byline — "By Colin Sica — Quantitative Research"
 */
export function Byline({
  author = 'Colin Sica',
  role = 'Quantitative research, University of Washington',
}: { author?: string; role?: string }) {
  return (
    <p className="byline">
      By <span className="not-italic font-medium" style={{ color: '#1A1612' }}>{author}</span>
      {role && <> &nbsp;·&nbsp; {role}</>}
    </p>
  );
}

/**
 * Stamp — small kicker pill. Black fill by default, salmon/slate variants.
 */
export function Stamp({
  variant = 'ink',
  children,
}: {
  variant?: 'ink' | 'salmon' | 'slate' | 'sage';
  children: ReactNode;
}) {
  const cls = variant === 'salmon' ? 'stamp stamp-salmon'
           : variant === 'slate'  ? 'stamp stamp-slate'
           : variant === 'sage'   ? 'stamp stamp-sage'
           : 'stamp';
  return <span className={cls}>{children}</span>;
}

/**
 * FigureCaption — italic serif under a chart or table.
 */
export function FigureCaption({ children }: { children: ReactNode }) {
  return <p className="figure-caption mt-2">{children}</p>;
}

/**
 * Footnote — small-type citation / clarification, with optional marker.
 */
export function Footnote({ mark, children }: { mark?: string; children: ReactNode }) {
  return (
    <p className="footnote">
      {mark && <span className="footnote-mark">{mark}</span>}
      {children}
    </p>
  );
}
