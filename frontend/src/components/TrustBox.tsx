import { useMode } from '../lib/mode';

/**
 * Trust statement — a product-defining affirmation shown near the top
 * of the homepage. Makes the Independent model's contract explicit.
 */
export function TrustBox() {
  const { mode } = useMode();
  const showIndieTrust = mode === 'independent';

  return (
    <section
      aria-label="Model transparency"
      className="border border-ink-edge bg-ink-raised/60 backdrop-blur-sm"
      style={{ borderRadius: '2px' }}
    >
      <div className="grid grid-cols-1 md:grid-cols-[auto_1fr] gap-0">
        <div
          className="px-6 py-5 md:border-r border-b md:border-b-0 border-ink-edge
                     flex items-center justify-center"
          style={{
            background: showIndieTrust
              ? 'linear-gradient(135deg, rgba(200,241,105,0.08), rgba(200,241,105,0.02))'
              : 'transparent',
          }}
        >
          <span
            className="display-serif text-4xl md:text-5xl font-bold italic"
            style={{ color: showIndieTrust ? '#C8F169' : '#A29987' }}
          >
            01
          </span>
        </div>
        <div className="px-6 py-5 space-y-2.5">
          <h3 className="caps text-mode-indie">The contract</h3>
          <p className="text-paper leading-relaxed text-[0.95rem]">
            This model <span className="display-serif italic font-medium">does not copy analyst mocks.</span>
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
