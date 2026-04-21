import { useMode } from '../lib/mode';

export function TrustBox() {
  const { mode } = useMode();
  const showIndieTrust = mode === 'independent';

  return (
    <section
      aria-label="Model transparency"
      className="relative border border-ink-edge bg-ink-raised/70 backdrop-blur-sm overflow-hidden"
    >
      {/* yellow chevron stripe top-edge — broadcast motif */}
      <div className="chevron-stripe" />

      <div className="grid grid-cols-1 md:grid-cols-[auto_1fr]">
        <div
          className="px-6 py-6 md:border-r border-b md:border-b-0 border-ink-edge
                     flex items-center justify-center min-w-[140px]"
          style={{
            background: showIndieTrust
              ? 'linear-gradient(135deg, rgba(255,210,63,0.14), rgba(255,210,63,0.03))'
              : 'transparent',
          }}
        >
          <span
            className="display-num"
            style={{
              color: showIndieTrust ? '#FFD23F' : '#9FACC2',
              fontSize: 'clamp(3.5rem, 7vw, 5rem)',
              lineHeight: 1,
            }}
          >
            01
          </span>
        </div>
        <div className="px-6 py-5 space-y-2.5">
          <div className="flex items-center gap-2">
            <span className="live-dot" />
            <h3 className="caps" style={{ color: '#FFD23F' }}>The contract</h3>
          </div>
          <p className="text-paper leading-relaxed text-[0.95rem]">
            This model <span className="display-broadcast text-xl" style={{ color: '#FFD23F' }}>DOES NOT COPY ANALYST MOCKS.</span>
            &nbsp;Analyst picks are never fed into the Independent engine.
          </p>
          <p className="text-paper-muted text-sm leading-relaxed">
            Analyst data appears only in <span className="caps-tight text-mode-bench">Benchmark</span> mode or as a comparison baseline.
            Independent predictions are derived from tape grades, athletic testing, visit intel, scheme fit, and team-agent simulation.
          </p>
        </div>
      </div>
    </section>
  );
}
