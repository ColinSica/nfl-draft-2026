import { relTime, freshnessState } from '../lib/display';

export type FreshnessInput = {
  modelRefresh?: string | null;
  intelRefresh?: string | null;
  simRun?: string | null;
};

const dotClass: Record<'fresh' | 'stale' | 'missing', string> = {
  fresh:   'bg-state-fresh',
  stale:   'bg-state-stale',
  missing: 'bg-state-broken',
};

const stateLabel: Record<'fresh' | 'stale' | 'missing', string> = {
  fresh:   'Fresh',
  stale:   'Stale',
  missing: 'Missing',
};

function Row({ label, iso }: { label: string; iso?: string | null }) {
  const s = freshnessState(iso);
  return (
    <div className="flex items-baseline justify-between gap-4 py-3 border-b border-ink-edge last:border-b-0">
      <div className="flex items-center gap-2.5">
        <span className={`w-1.5 h-1.5 rounded-full ${dotClass[s]}`} />
        <span className="caps-tight text-ink-soft">{label}</span>
      </div>
      <div className="flex items-baseline gap-3">
        <span className="font-mono text-xs text-ink-soft/70">[{stateLabel[s]}]</span>
        <span className="font-mono text-sm text-ink">{relTime(iso)}</span>
      </div>
    </div>
  );
}

export function FreshnessPanel({ data, compact }: { data: FreshnessInput; compact?: boolean }) {
  if (compact) {
    return (
      <div className="flex items-center gap-4 text-xs text-ink-soft">
        <span>
          <span className="caps-tight mr-1.5">model</span>
          <span className="font-mono">{relTime(data.modelRefresh)}</span>
        </span>
        <span className="text-ink-edge">·</span>
        <span>
          <span className="caps-tight mr-1.5">intel</span>
          <span className="font-mono">{relTime(data.intelRefresh)}</span>
        </span>
        <span className="text-ink-edge">·</span>
        <span>
          <span className="caps-tight mr-1.5">sim</span>
          <span className="font-mono">{relTime(data.simRun)}</span>
        </span>
      </div>
    );
  }

  return (
    <section aria-label="Data freshness" className="card">
      <header className="flex items-center justify-between px-5 py-3 border-b border-ink-edge">
        <h2 className="caps-tight text-ink">Data freshness</h2>
        <span className="font-mono text-[0.68rem] text-ink-soft/70">
          cached-first · stale-while-revalidate
        </span>
      </header>
      <div className="px-5 py-1">
        <Row label="Model refresh" iso={data.modelRefresh} />
        <Row label="Intel refresh" iso={data.intelRefresh} />
        <Row label="Latest simulation" iso={data.simRun} />
      </div>
    </section>
  );
}
