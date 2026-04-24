import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { RefreshCw, Info, Menu, X } from 'lucide-react';
import { Home } from './pages/Home';
import { Dashboard } from './pages/Dashboard';
import { TeamDetail } from './pages/TeamDetail';
import { Prospects } from './pages/Prospects';
import { FullMock } from './pages/FullMock';
import { Method } from './pages/Method';
import { MockLab } from './pages/MockLab';
import { Accuracy } from './pages/Accuracy';
import { AboutModal } from './components/AboutModal';
import { MobileModeBar } from './components/MobileModeBar';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ModeProvider, useMode, MODE_META } from './lib/mode';
import { api, type MetaInfo } from './lib/api';
import { cn } from './lib/format';
import { SOURCE_REPO_URL } from './lib/constants';

// Primary navigation — six sections, the ones fans actually scan on draft day.
// Prospects, Teams, First Round are the load-bearing pages. Mock Lab and
// Method are secondary. Watchlist/Positions/TeamCompare are kept as live
// routes (star icons, position filter on Prospects, dashboard compare button
// all link to them) but are cut from the top nav to reduce noise.
const NAV_LINKS = [
  { to: '/',          label: 'Home',         end: true },
  { to: '/full-mock', label: 'Full Mock',    end: true },
  { to: '/teams',     label: 'Teams',        end: true },
  { to: '/prospects', label: 'Prospects',    end: true },
  { to: '/accuracy',  label: 'Accuracy',     end: true },
  { to: '/lab',       label: 'Mock Lab',     end: true },
  { to: '/method',    label: 'Methodology',  end: true },
];

function Nav({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="flex items-center gap-0 flex-wrap lg:flex-nowrap">
      {NAV_LINKS.map((l) => (
        <NavLink
          key={l.to}
          to={l.to}
          end={l.end}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              'px-3 py-2 caps-tight transition-all ease-editorial duration-150 border-b whitespace-nowrap inline-flex items-center gap-1.5',
              isActive
                ? 'text-ink border-accent-brass'
                : 'text-ink-muted hover:text-ink border-transparent',
            )
          }
        >
          {l.label}
        </NavLink>
      ))}
    </nav>
  );
}

function ModePill() {
  const { mode } = useMode();
  const meta = MODE_META[mode];
  return (
    <div className="mode-chip" data-mode={mode} title={meta.description + ' · ' + meta.caption}>
      <span className="mode-dot" data-mode={mode} />
      <span className="hidden md:inline">{meta.label}</span>
      <span className="hidden 2xl:inline text-ink-soft/70 font-normal normal-case tracking-normal text-[0.7rem] ml-1">
        · {meta.caption}
      </span>
    </div>
  );
}

function formatRelative(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const t = new Date(iso).getTime();
  if (isNaN(t)) return null;
  const mins = Math.max(1, Math.round((Date.now() - t) / 60000));
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.round(hrs / 24);
  return `${days}d ago`;
}

function Header({ meta, onAbout }: {
  meta: MetaInfo | null;
  onAbout: () => void;
}) {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => { setMobileOpen(false); }, [location.pathname]);

  // `location.reload(true)` is legacy Firefox — modern browsers ignore the
  // argument. Plain reload is universally supported.
  const hardReload = () => window.location.reload();

  const todayStr = new Date().toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  });

  return (
    <header className="sticky top-0 z-30 bg-paper/95 backdrop-blur-md border-b-2 border-ink overflow-hidden">
      {/* Masthead top rule */}
      <div className="masthead-rule" />

      <div className="max-w-[1280px] mx-auto px-4 sm:px-6">
        {/* Dateline strip */}
        <div className="dateline flex items-center gap-3 py-1.5 text-ink-muted border-b border-ink-edge">
          <span>Vol. I · No. 26</span>
          <span className="text-ink-edge">·</span>
          <span className="hidden sm:inline">{todayStr}</span>
          <span className="text-ink-edge hidden sm:inline">·</span>
          <span className="hidden md:inline">Seattle</span>
          {meta?.generated_at && (
            <>
              <span className="text-ink-edge hidden md:inline">·</span>
              <span className="hidden md:inline" title={meta.generated_at}>
                Model run <span className="text-accent-brass">{formatRelative(meta.generated_at)}</span>
              </span>
            </>
          )}
          <span className="ml-auto hidden lg:inline">A Quantitative Study · Free Edition</span>
        </div>

        {/* Nameplate row */}
        <div className="flex items-center gap-3 sm:gap-6 py-3 min-w-0">
          <Link to="/" className="flex items-baseline gap-3 group flex-none min-w-0">
            <span className="nameplate text-[1.5rem] sm:text-[2rem] md:text-[2.4rem] truncate">
              The Draft <em>Ledger</em>
            </span>
          </Link>

          <div className="hidden xl:block flex-1">
            <Nav />
          </div>

          <div className="ml-auto flex items-center gap-2 sm:gap-3 shrink-0">
            <ModePill />

            <div className="hidden xl:flex items-center gap-1 pl-3 border-l border-ink-edge">
              <span className="text-[0.62rem] text-ink-muted font-mono mr-2 hidden 2xl:inline">
                / to search
              </span>
              <button
                onClick={onAbout}
                className="p-2 hover:bg-paper-hover transition text-ink-muted hover:text-ink"
                title="About this model (?)"
                aria-label="About this model"
              >
                <Info size={16} />
              </button>
              <button
                onClick={hardReload}
                className="p-2 hover:bg-paper-hover transition text-ink-muted hover:text-ink"
                title="Hard refresh"
                aria-label="Refresh page"
              >
                <RefreshCw size={16} />
              </button>
            </div>

            <button
              onClick={() => setMobileOpen((v) => !v)}
              className="xl:hidden p-2 hover:bg-paper-hover transition"
              aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={mobileOpen}
            >
              {mobileOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>

        {/* Navigation row, own line (below nameplate) for better density */}
        <div className="hidden lg:block xl:hidden border-t border-ink-edge py-1">
          <Nav />
        </div>
      </div>

      {mobileOpen && (
        <div className="xl:hidden border-t border-ink bg-paper/98 backdrop-blur">
          <div className="max-w-[1280px] mx-auto px-4 py-2 flex flex-col">
            {NAV_LINKS.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.end}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  cn(
                    'px-4 py-3 caps-tight transition border-l-2',
                    isActive
                      ? 'text-ink border-accent-brass bg-paper-hover'
                      : 'text-ink-muted border-transparent hover:text-ink hover:bg-paper-hover',
                  )
                }
              >
                {l.label}
              </NavLink>
            ))}
            <div className="flex items-center gap-2 pt-3 mt-2 border-t border-ink-edge">
              <button
                onClick={() => { setMobileOpen(false); onAbout(); }}
                className="flex items-center gap-1.5 p-2 caps-tight text-ink-soft hover:text-ink"
              >
                <Info size={14} /> About
              </button>
              <button
                onClick={hardReload}
                className="flex items-center gap-1.5 p-2 caps-tight text-ink-soft hover:text-ink"
              >
                <RefreshCw size={14} /> Refresh
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}

function AppInner() {
  const [meta, setMeta] = useState<MetaInfo | null>(null);
  const [aboutOpen, setAboutOpen] = useState(false);

  useEffect(() => {
    api.meta().then(setMeta).catch(() => {});
    // Global keyboard shortcut: `/` focuses any search input on the page,
    // or navigates to Prospects (which has a search) if none found.
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (e.key === '/' && tag !== 'input' && tag !== 'textarea') {
        e.preventDefault();
        const search = document.querySelector<HTMLInputElement>(
          'input[type="text"][placeholder*="Search" i], input[placeholder*="prospect" i]'
        );
        if (search) {
          search.focus();
          search.select();
        } else if (window.location.pathname !== '/prospects') {
          window.location.href = '/prospects';
        }
      }
      // `?` opens About
      if (e.key === '?' && tag !== 'input' && tag !== 'textarea') {
        e.preventDefault();
        setAboutOpen(true);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div className="min-h-full flex flex-col">
      {/* Screen-reader + keyboard skip link — appears on focus only. */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:bg-ink focus:text-paper focus:px-3 focus:py-2 focus:caps-tight"
      >
        Skip to main content
      </a>
      <Header
        meta={meta}
        onAbout={() => setAboutOpen(true)}
      />
      <MobileModeBar />
      <main
        id="main-content"
        className="max-w-[1280px] w-full mx-auto px-4 sm:px-6 py-6 sm:py-10 flex-1"
      >
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/teams" element={<Dashboard />} />
            <Route path="/team/:abbr" element={<TeamDetail />} />
            <Route path="/prospects" element={<Prospects />} />
            <Route path="/full-mock" element={<FullMock />} />
            <Route path="/accuracy" element={<Accuracy />} />
            <Route path="/lab" element={<MockLab />} />
            <Route path="/method" element={<Method />} />
          </Routes>
        </ErrorBoundary>
      </main>
      <footer className="max-w-[1280px] w-full mx-auto px-4 sm:px-6 py-6 mt-10 border-t-2 border-ink">
        <div className="hrule mb-4" />
        <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-4 items-baseline">
          <div className="space-y-1">
            <p className="nameplate text-2xl">The Draft <em>Ledger</em></p>
            <p className="byline">
              A quantitative study by <span className="not-italic font-medium text-ink">Colin Sica</span>,
              finance · University of Washington
            </p>
            <p className="footnote">
              Quantitative 32-agent Monte Carlo. Each front office is a discrete
              decision function driven by roster need, scheme premium, coaching-
              tree priors, cap posture, and a GM positional-affinity fingerprint.
              Simulated over a 727-prospect board built from tape grades,
              athletic testing, medicals, and documented team visits.
            </p>
          </div>
          <div className="flex items-center gap-5 text-xs text-ink-muted">
            <button
              onClick={() => setAboutOpen(true)}
              className="caps-tight hover:text-ink transition"
            >
              About
            </button>
            <a href={SOURCE_REPO_URL} target="_blank" rel="noopener"
               className="caps-tight hover:text-ink transition">
              Source
            </a>
            <span className="caps-tight">© {new Date().getFullYear()}</span>
          </div>
        </div>
      </footer>
      <AboutModal open={aboutOpen} onClose={() => setAboutOpen(false)} />
    </div>
  );
}

export default function App() {
  return (
    <ModeProvider>
      <AppInner />
    </ModeProvider>
  );
}
