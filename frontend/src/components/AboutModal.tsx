import { useEffect } from 'react';
import { X } from 'lucide-react';

export function AboutModal({
  open, onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-ink/60 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="card p-7 max-w-2xl w-full max-h-[85vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-5 gap-4">
          <div className="flex items-center gap-3">
            <span
              className="display-num text-2xl leading-none px-2 py-1"
              style={{ background: '#B68A2F', color: '#0B1F3A', fontStyle: 'italic' }}
            >
              26
            </span>
            <div>
              <h2 className="display-broadcast text-2xl text-ink leading-tight">About the model</h2>
              <p className="text-xs text-ink-soft mt-0.5">2026 NFL Draft · Independent prediction engine</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-paper-hover text-ink-soft hover:text-ink"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        <div className="chevron-stripe mb-6" />

        <div className="space-y-5 text-sm leading-relaxed">
          <section>
            <h3 className="caps text-ink mb-2">What this is</h3>
            <p className="text-ink-soft">
              A two-stage prediction engine for the 2026 NFL Draft.{' '}
              <span className="text-ink font-semibold">Stage&nbsp;1</span> builds the player board from
              tape, athletic testing, medicals, visit coverage, and production.{' '}
              <span className="text-ink font-semibold">Stage&nbsp;2</span> simulates the draft as 32
              autonomous team agents — each acting on its own scheme, cap, coaches, and intel.
            </p>
          </section>

          <section>
            <h3 className="caps text-ink mb-2">The independence contract</h3>
            <p className="text-ink-soft">
              <span className="display-broadcast" style={{ color: '#B68A2F' }}>
                Analyst picks are not inputs to this model.
              </span>{' '}
              A pytest suite enforces this: any analyst-rank column touching the Independent
              pipeline fails the build. 8/8 tests currently pass.
            </p>
          </section>

          <section>
            <h3 className="caps text-ink mb-2">Modes</h3>
            <ul className="space-y-1.5 text-ink-soft">
              <li>
                <span className="caps-tight" style={{ color: '#B68A2F' }}>Independent</span> — core
                model output (default).
              </li>
              <li>
                <span className="caps-tight" style={{ color: '#1F6FEB' }}>Benchmark</span> — analyst
                consensus baseline. Shown for comparison only.
              </li>
              <li>
                <span className="caps-tight" style={{ color: '#17A870' }}>Compare</span> — slot-by-slot
                Independent vs. Benchmark.
              </li>
            </ul>
          </section>

          <section>
            <h3 className="caps text-ink mb-2">Current accuracy</h3>
            <div className="grid grid-cols-2 gap-3 mt-2">
              {[
                ['91%', 'Top-32 board overlap'],
                ['200', 'Sims per run'],
                ['32', 'Autonomous agents'],
                ['8/8', 'Independence tests'],
              ].map(([v, l]) => (
                <div key={l} className="border border-ink-edge p-3">
                  <div className="display-num text-3xl text-ink">{v}</div>
                  <div className="caps-tight text-ink-soft text-[0.65rem] mt-0.5">{l}</div>
                </div>
              ))}
            </div>
          </section>

          <section>
            <h3 className="caps text-ink mb-2">Built by</h3>
            <p className="text-ink-soft">
              Colin Sica. 2026 NFL Draft Predictor · released under a personal license.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
