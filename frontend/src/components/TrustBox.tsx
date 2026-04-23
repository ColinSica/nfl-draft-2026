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
              ? 'linear-gradient(135deg, rgba(182,138,47,0.18), rgba(182,138,47,0.02))'
              : 'transparent',
          }}
        >
          <span
            className="display-num"
            style={{
              color: showIndieTrust ? '#B68A2F' : '#6E6650',
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
            <h3 className="caps" style={{ color: '#B68A2F' }}>How the engine works</h3>
          </div>
          <p className="text-ink leading-relaxed text-lg">
            <span className="display-broadcast text-2xl tracking-tight" style={{ color: '#B68A2F' }}>
              32 team agents. One board. 200+ simulations.
            </span>
          </p>
          <p className="text-ink-soft leading-relaxed">
            Every prediction is derived: PFF tape grades, athletic testing,
            medicals, and documented team visits build the 727-prospect board.
            Each front office then decides for itself using its own needs,
            scheme, coaching tree, cap posture, and GM draft-history fingerprint.
          </p>
          <p className="text-ink-soft/80 text-sm">
            Outputs are probability distributions per slot, not point predictions
            copied from somewhere else.
          </p>
        </div>
      </div>
    </section>
  );
}
