/**
 * Mobile-only sticky mode bar — pinned below header as the user scrolls.
 * Ensures mode (Independent / Benchmark / Compare) is always visible on
 * small screens where the top-bar chip is easy to miss.
 */
import { MODE_META, useMode } from '../lib/mode';

export function MobileModeBar() {
  const { mode } = useMode();
  const meta = MODE_META[mode];

  return (
    <div
      className="lg:hidden sticky z-20 border-b"
      style={{
        top: '4rem', // sits right under the 64px header
        background: `${meta.accent}18`,
        borderColor: `${meta.accent}55`,
        backdropFilter: 'blur(8px)',
      }}
    >
      <div className="max-w-[1280px] mx-auto px-4 py-1.5 flex items-center gap-2.5">
        <span className="mode-dot" data-mode={mode} />
        <span className="caps-tight" style={{ color: meta.accent }}>
          {meta.label} mode
        </span>
        <span className="text-[0.65rem] text-ink-soft ml-auto truncate">
          {meta.caption}
        </span>
      </div>
    </div>
  );
}
