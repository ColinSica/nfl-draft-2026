/**
 * Draft countdown — live ticker to the 2026 NFL Draft start time.
 * Draft: April 23, 2026, 8:00 PM ET (Pittsburgh).
 */
import { useEffect, useState } from 'react';

const DRAFT_START_ISO = '2026-04-23T20:00:00-04:00';

type TimeLeft = {
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
  totalMs: number;
};

function computeTimeLeft(): TimeLeft {
  const target = new Date(DRAFT_START_ISO).getTime();
  const now = Date.now();
  const totalMs = target - now;
  if (totalMs <= 0) {
    return { days: 0, hours: 0, minutes: 0, seconds: 0, totalMs };
  }
  return {
    days:    Math.floor(totalMs / (1000 * 60 * 60 * 24)),
    hours:   Math.floor((totalMs / (1000 * 60 * 60)) % 24),
    minutes: Math.floor((totalMs / (1000 * 60)) % 60),
    seconds: Math.floor((totalMs / 1000) % 60),
    totalMs,
  };
}

export function DraftCountdown({ compact = false }: { compact?: boolean }) {
  const [t, setT] = useState(computeTimeLeft());

  useEffect(() => {
    const id = setInterval(() => setT(computeTimeLeft()), 1000);
    return () => clearInterval(id);
  }, []);

  const started = t.totalMs <= 0;

  if (compact) {
    if (started) {
      return <span className="caps-tight text-live">Draft live</span>;
    }
    return (
      <span className="caps-tight font-mono text-ink">
        T-{t.days}d {String(t.hours).padStart(2,'0')}:{String(t.minutes).padStart(2,'0')}:{String(t.seconds).padStart(2,'0')}
      </span>
    );
  }

  if (started) {
    return (
      <div className="card p-5 flex items-center gap-4">
        <span className="live-dot" style={{ width: 14, height: 14 }} />
        <div>
          <div className="display-broadcast text-2xl text-live">Draft is live.</div>
          <div className="text-xs text-ink-soft">
            April 23–25, 2026 · Pittsburgh
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card p-5">
      <div className="flex items-center gap-3 mb-3">
        <span className="live-dot" />
        <span className="caps text-live">Draft countdown</span>
      </div>
      <div className="flex items-baseline gap-5 flex-wrap">
        <Unit val={t.days} label="days" />
        <span className="display-num text-4xl text-ink-soft">:</span>
        <Unit val={t.hours} label="hours" />
        <span className="display-num text-4xl text-ink-soft">:</span>
        <Unit val={t.minutes} label="min" />
        <span className="display-num text-4xl text-ink-soft">:</span>
        <Unit val={t.seconds} label="sec" />
      </div>
      <div className="mt-3 text-xs text-ink-soft">
        Draft begins April 23, 8:00 PM ET · Pittsburgh
      </div>
    </div>
  );
}

function Unit({ val, label }: { val: number; label: string }) {
  return (
    <div className="text-center">
      <div className="display-num text-4xl md:text-5xl text-ink leading-none tabular-nums">
        {String(val).padStart(2, '0')}
      </div>
      <div className="caps-tight text-ink-soft text-[0.6rem] mt-0.5">{label}</div>
    </div>
  );
}
