import { Component, type ErrorInfo, type ReactNode } from 'react';

type Props = { children: ReactNode };
type State = { error: Error | null };

// Top-level error boundary — catches render-time exceptions in any page so
// a single broken component doesn't blank the whole app.
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    if (typeof console !== 'undefined') {
      console.error('ErrorBoundary caught:', error, info);
    }
  }

  reset = () => {
    this.setState({ error: null });
  };

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    return (
      <div className="max-w-[720px] mx-auto my-20 px-6 card p-8">
        <div className="caps-tight text-live mb-2">Something broke on this page</div>
        <h2 className="display-broadcast text-2xl text-ink mb-3">
          The Draft Ledger tripped on its own shoelaces.
        </h2>
        <p className="body-serif text-sm text-ink-soft mb-5">
          A component threw an unexpected error and stopped rendering. You can
          try reloading, or head back to the front page. The error message is
          below in case it helps.
        </p>
        <pre className="font-mono text-xs bg-paper-surface border border-ink-edge p-3 overflow-x-auto text-ink-soft whitespace-pre-wrap">
          {error.message}
        </pre>
        <div className="mt-5 flex gap-3 flex-wrap">
          <button
            onClick={() => { this.reset(); window.location.href = '/'; }}
            className="btn-primary"
          >
            Front page
          </button>
          <button
            onClick={() => window.location.reload()}
            className="btn-ghost"
          >
            Reload
          </button>
        </div>
      </div>
    );
  }
}
