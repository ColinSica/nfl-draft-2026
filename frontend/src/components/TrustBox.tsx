import { useMode } from '../lib/mode';

export function TrustBox() {
  const { mode } = useMode();
  const showIndieTrust = mode === 'independent';

  return (
    <section
      aria-label="Model transparency"
      className="relative bg-paper-surface border border-ink-edge shadow-card overflow-hidden"
    >
      <div className="chevron-stripe" />

      <div className="grid grid-cols-1 md:grid-cols-[auto_1fr]">
        <div
          className="px-6 py-7 md:border-r border-b md:border-b-0 border-ink-edge
                     flex items-center justify-center min-w-[160px]"
          style={{
            background: showIndieTrust
              ? 'linear-gradient(135deg, rgba(217,164,0,0.16), rgba(217,164,0,0.02))'
              : 'transparent',
          }}
        >
          <span
            className="display-num"
            style={{
              color: showIndieTrust ? '#D9A400' : '#848B98',
              fontSize: 'clamp(3.5rem, 7vw, 5.5rem)',
              lineHeight: 1,
            }}
          >
            01
          </span>
        </div>
        <div className="px-6 md:px-8 py-6 space-y-3">
          <div className="flex items-center gap-2">
            <span className="live-dot" />
            <h3 className="caps" style={{ color: '#D9A400' }}>The contract</h3>
          </div>
          <p className="text-ink leading-relaxed text-lg">
            This model <span className="display-broadcast text-2xl" style={{ color: '#D9A400' }}>does not copy analyst mocks.</span>
            &nbsp;Analyst picks are never fed into the Independent engine.
          </p>
          <p className="text-ink-soft leading-relaxed">
            Analyst data appears only in <span className="caps-tight text-mode-bench">Benchmark</span> mode or as a comparison baseline.
            Independent predictions come from tape grades, athletic testing, visit intel, scheme fit,
            and team-agent simulation.
          </p>
        </div>
      </div>
    </section>
  );
}
