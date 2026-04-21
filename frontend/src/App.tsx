import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { RefreshCw, Info, Menu, X } from 'lucide-react';
import { Home } from './pages/Home';
import { Dashboard } from './pages/Dashboard';
import { TeamDetail } from './pages/TeamDetail';
import { Simulate } from './pages/Simulate';
import { Prospects } from './pages/Prospects';
import { League } from './pages/League';
import { BuildMock } from './pages/BuildMock';
import { Settings } from './pages/Settings';
import { AboutModal } from './components/AboutModal';
import { ModeProvider, useMode, MODE_META } from './lib/mode';
import { api, type MetaInfo } from './lib/api';
import { cn } from './lib/format';

// Primary navigation — trimmed to the 5 user-facing jobs only.
// /build, /league, /settings remain routable but hidden from nav
// (they're internal tools, not part of the public product surface).
const NAV_LINKS = [
  { to: '/',          label: 'Home',        end: true },
  { to: '/teams',     label: 'Teams',       end: true },
  { to: '/prospects', label: 'Prospects',   end: true },
  { to: '/simulate',  label: 'First round', end: true },
  { to: '/compare',   label: 'Compare',     end: true },
  { to: '/method',    label: 'Method',      end: true },
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
              'px-4 py-2 caps-tight transition-all ease-broadcast duration-150 border-b-2 whitespace-nowrap',
              isActive
                ? 'text-ink border-mode-indie'
                : 'text-ink-soft hover:text-ink border-transparent',
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
    <div className="mode-chip" data-mode={mode} title={meta.description}>
      <span className="mode-dot" data-mode={mode} />
      <span className="hidden sm:inline">{meta.label}</span>
      <span className="hidden md:inline text-ink-soft/70 font-normal normal-case tracking-normal text-[0.7rem] ml-1">
        · {meta.caption}
      </span>
    </div>
  );
}

function Header({ onAbout }: {
  meta: MetaInfo | null;
  onAbout: () => void;
}) {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => { setMobileOpen(false); }, [location.pathname]);

  const hardReload = () => {
    try { (window as any).location.reload(true); }
    catch { window.location.href = window.location.href; }
  };

  return (
    <header className="sticky top-0 z-30 backdrop-blur-md bg-paper/85 border-b border-ink-edge">
      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 h-16 flex items-center gap-4 sm:gap-8">
        <Link to="/" className="flex items-center gap-2.5 group flex-none">
          <span
            className="display-num text-2xl leading-none px-2 py-1"
            style={{
              background: '#D9A400',
              color: '#12151B',
              fontStyle: 'italic',
            }}
          >
            26
          </span>
          <span className="display-broadcast text-xl leading-none hidden sm:inline text-ink">
            Draft<span className="text-ink-soft/60">/</span><span style={{ color: '#D9A400' }}>Intel</span>
          </span>
        </Link>

        <div className="hidden lg:block flex-1">
          <Nav />
        </div>

        <div className="ml-auto flex items-center gap-3">
          <ModePill />

          <div className="hidden md:flex items-center gap-1 pl-3 border-l border-ink-edge">
            <button
              onClick={onAbout}
              className="p-2 hover:bg-paper-hover transition text-ink-soft hover:text-ink"
              title="About this model"
              aria-label="About this model"
            >
              <Info size={16} />
            </button>
            <button
              onClick={hardReload}
              className="p-2 hover:bg-paper-hover transition text-ink-soft hover:text-ink"
              title="Hard refresh"
              aria-label="Refresh page"
            >
              <RefreshCw size={16} />
            </button>
          </div>

          <button
            onClick={() => setMobileOpen((v) => !v)}
            className="lg:hidden p-2 hover:bg-paper-hover transition"
            aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={mobileOpen}
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <div className="lg:hidden border-t border-ink-edge bg-paper/95 backdrop-blur">
          <div className="max-w-[1280px] mx-auto px-4 py-3 flex flex-col">
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
                      ? 'text-ink border-mode-indie bg-paper-hover'
                      : 'text-ink-soft border-transparent hover:text-ink hover:bg-paper-hover',
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
  }, []);

  return (
    <div className="min-h-full flex flex-col">
      <Header
        meta={meta}
        onAbout={() => setAboutOpen(true)}
      />
      <main className="max-w-[1280px] w-full mx-auto px-4 sm:px-6 py-6 sm:py-10 flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/teams" element={<Dashboard />} />
          <Route path="/team/:abbr" element={<TeamDetail />} />
          <Route path="/simulate" element={<Simulate />} />
          <Route path="/prospects" element={<Prospects />} />
          <Route path="/compare" element={<ComparePlaceholder />} />
          <Route path="/method" element={<MethodPlaceholder />} />
          {/* Internal-only routes (not in primary nav) */}
          <Route path="/league" element={<League />} />
          <Route path="/build" element={<BuildMock />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
      <footer className="max-w-[1280px] w-full mx-auto px-4 sm:px-6 py-6 mt-10 border-t border-ink-edge">
        <div className="chevron-stripe mb-5 opacity-70" />
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-ink-soft/80">
          <div className="flex items-center gap-3">
            <span className="display-broadcast text-ink">2026 Draft Intel</span>
            <span className="text-ink-edge">·</span>
            <span>Built by <span className="text-ink-soft">Colin Sica</span></span>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setAboutOpen(true)}
              className="caps-tight hover:text-ink transition"
            >
              About the model
            </button>
            <span>© {new Date().getFullYear()}</span>
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

// Placeholder routes
function ComparePlaceholder() {
  return (
    <div className="py-16 max-w-2xl mx-auto text-center">
      <div className="space-y-5">
        <span className="caps-tight text-mode-compare">Compare mode</span>
        <h1 className="display-broadcast text-6xl md:text-7xl leading-[0.85] text-ink">
          Independent <span className="italic text-ink-soft/70">vs.</span><br />
          <span style={{ color: '#1F6FEB' }}>Benchmark.</span>
        </h1>
        <hr className="hrule-accent mx-auto w-24" />
        <p className="text-ink-soft leading-relaxed text-lg max-w-lg mx-auto">
          Side-by-side comparison view coming soon. Will show each slot with the
          Independent model's pick, the analyst Benchmark pick, and where they diverge.
        </p>
      </div>
    </div>
  );
}

function MethodPlaceholder() {
  return (
    <div className="py-16 max-w-2xl mx-auto text-center">
      <div className="space-y-5">
        <span className="caps-tight text-ink-soft">Method</span>
        <h1 className="display-broadcast text-6xl md:text-7xl leading-[0.85] text-ink">
          How the model <span className="italic" style={{ color: '#D9A400' }}>actually</span> works.
        </h1>
        <hr className="hrule-accent mx-auto w-24" />
        <p className="text-ink-soft leading-relaxed text-lg max-w-lg mx-auto">
          Full method write-up coming soon. Stage 1 board construction, Stage 2
          team-agent simulation, the independence contract, feature inventory,
          and confidence methodology.
        </p>
      </div>
    </div>
  );
}
