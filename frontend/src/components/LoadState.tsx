// Shared empty-state blocks so every page uses the same language.

export function LoadingBlock({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="card p-10 text-center text-ink-soft italic" role="status" aria-live="polite">
      {label}
    </div>
  );
}

export function ErrorBlock({
  message, onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div
      className="card p-6 md:p-8 border-l-4 border-live"
      role="alert"
    >
      <div className="caps-tight text-live mb-1">Couldn't load data</div>
      <p className="body-serif text-sm text-ink mb-3">
        The server didn't return what this page needed. Your connection may be
        offline, or the backend is restarting.
      </p>
      <details className="mb-3">
        <summary className="caps-tight text-[0.62rem] text-ink-muted cursor-pointer">
          Error detail
        </summary>
        <pre className="mt-2 font-mono text-xs bg-paper-surface border border-ink-edge p-2 overflow-x-auto text-ink-soft whitespace-pre-wrap">
          {message}
        </pre>
      </details>
      {onRetry && (
        <button onClick={onRetry} className="btn-ghost">Try again</button>
      )}
    </div>
  );
}
