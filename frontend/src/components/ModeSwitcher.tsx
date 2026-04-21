import { MODE_META, useMode, type Mode } from '../lib/mode';

const ORDER: Mode[] = ['independent', 'benchmark', 'compare'];

export function ModeSwitcher({ compact = false }: { compact?: boolean }) {
  const { mode, setMode } = useMode();

  if (compact) {
    const meta = MODE_META[mode];
    return (
      <div className="mode-chip" data-mode={mode}>
        <span className="mode-dot" data-mode={mode} />
        <span>{meta.label} mode</span>
      </div>
    );
  }

  return (
    <div
      role="radiogroup"
      aria-label="Prediction mode"
      className="inline-flex items-stretch border border-ink-edge bg-ink-raised"
    >
      {ORDER.map((m) => {
        const meta = MODE_META[m];
        const active = m === mode;
        return (
          <button
            key={m}
            role="radio"
            aria-checked={active}
            onClick={() => setMode(m)}
            className="relative px-4 py-2 caps-tight transition-all ease-editorial duration-200
                       border-r border-ink-edge last:border-r-0"
            style={{
              color: active ? meta.accent : 'var(--tw-paper-muted, #A29987)',
              background: active ? `${meta.accent}15` : 'transparent',
            }}
          >
            <span className="flex items-center gap-2">
              <span className="mode-dot" data-mode={m}
                style={{ opacity: active ? 1 : 0.35 }} />
              {meta.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export function ModeDescription() {
  const { mode } = useMode();
  const meta = MODE_META[mode];
  return (
    <p className="text-paper-muted text-sm leading-relaxed max-w-2xl">
      <span className="caps-tight" style={{ color: meta.accent }}>
        {meta.caption}
      </span>
      <span className="ml-3">{meta.description}</span>
    </p>
  );
}
