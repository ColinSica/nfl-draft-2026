import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import {
  Activity, LayoutDashboard, PlayCircle, RefreshCw, Info,
  UserCircle, Globe, ClipboardList, Sliders,
  Menu, X,
} from 'lucide-react';
import { Dashboard } from './pages/Dashboard';
import { TeamDetail } from './pages/TeamDetail';
import { Simulate } from './pages/Simulate';
import { Prospects } from './pages/Prospects';
import { League } from './pages/League';
import { BuildMock } from './pages/BuildMock';
import { Settings } from './pages/Settings';
import { AboutModal } from './components/AboutModal';
import { api, type MetaInfo } from './lib/api';
import { cn, fmtDate } from './lib/format';

const NAV_LINKS = [
  { to: '/',          label: 'Teams',      Icon: LayoutDashboard, end: true },
  { to: '/simulate',  label: 'Simulate',   Icon: PlayCircle,      end: true },
  { to: '/build',     label: 'Build mock', Icon: ClipboardList,   end: true },
  { to: '/prospects', label: 'Prospects',  Icon: UserCircle,      end: true },
  { to: '/league',    label: 'League',     Icon: Globe,           end: true },
  { to: '/settings',  label: 'Settings',   Icon: Sliders,         end: true },
];

function Nav({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="flex items-center gap-1 flex-wrap lg:flex-nowrap">
      {NAV_LINKS.map((l) => (
        <NavLink
          key={l.to}
          to={l.to}
          end={l.end}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition whitespace-nowrap',
              isActive
                ? 'bg-bg-hover text-text'
                : 'text-text-muted hover:text-text hover:bg-bg-raised',
            )
          }
        >
          <l.Icon size={15} />
          {l.label}
        </NavLink>
      ))}
    </nav>
  );
}

function Header({ meta, onAbout }: {
  meta: MetaInfo | null;
  onAbout: () => void;
}) {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const gen = meta?.generated_at;
  const intelDate = meta?.analyst_intel_meta?.latest_intel_date;

  // Close mobile menu whenever we navigate
  useEffect(() => { setMobileOpen(false); }, [location.pathname]);

  const hardReload = () => {
    try { (window as any).location.reload(true); }
    catch { window.location.href = window.location.href; }
  };

  return (
    <header className="sticky top-0 z-30 backdrop-blur bg-bg/80 border-b border-border">
      <div className="max-w-[1400px] mx-auto px-3 sm:px-6 h-14 flex items-center gap-3 sm:gap-6">
        <Link to="/" className="flex items-center gap-2 group flex-none">
          <div className="w-7 h-7 rounded-md bg-gradient-to-br from-accent to-violet-400 grid place-items-center shadow-glow">
            <span className="text-[11px] font-bold text-white tracking-tight">2026</span>
          </div>
          <span className="font-semibold tracking-tight">Draft Predictor</span>
          <span className="hidden sm:inline text-text-subtle text-xs">
            · NFL 2026
          </span>
        </Link>

        {/* Desktop nav */}
        <div className="flex-1 hidden lg:block">
          <Nav />
        </div>

        {/* Desktop meta + actions */}
        <div className="hidden md:flex items-center gap-3 text-xs text-text-muted">
          {intelDate && (
            <span className="badge border-border text-text-muted">
              <Activity size={12} /> intel {intelDate}
            </span>
          )}
          {gen && (
            <span title={`Model built ${fmtDate(gen)}`}>
              v{meta?.schema_version ?? '—'}
            </span>
          )}
          <button
            onClick={onAbout}
            className="p-1.5 rounded-md hover:bg-bg-hover transition"
            title="About this model"
            aria-label="About this model"
          >
            <Info size={14} className="text-text-muted" />
          </button>
          <button
            onClick={hardReload}
            className="p-1.5 rounded-md hover:bg-bg-hover transition"
            title="Hard refresh — picks up new data AND new website versions"
            aria-label="Refresh page"
          >
            <RefreshCw size={14} className="text-text-muted" />
          </button>
        </div>

        {/* Mobile hamburger */}
        <button
          onClick={() => setMobileOpen((v) => !v)}
          className="lg:hidden ml-auto p-2 rounded-md hover:bg-bg-hover transition"
          aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={mobileOpen}
        >
          {mobileOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Mobile menu drawer */}
      {mobileOpen && (
        <div className="lg:hidden border-t border-border bg-bg/95 backdrop-blur">
          <div className="max-w-[1400px] mx-auto px-3 py-3 flex flex-col gap-1">
            {NAV_LINKS.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.end}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-[15px] font-medium transition',
                    isActive
                      ? 'bg-bg-hover text-text'
                      : 'text-text-muted hover:text-text hover:bg-bg-raised',
                  )
                }
              >
                <l.Icon size={17} />
                {l.label}
              </NavLink>
            ))}
            <div className="flex items-center gap-3 pt-2 mt-2 border-t border-border text-xs text-text-muted">
              {intelDate && (
                <span className="badge border-border text-text-muted">
                  <Activity size={12} /> intel {intelDate}
                </span>
              )}
              {gen && (
                <span title={`Model built ${fmtDate(gen)}`}>
                  v{meta?.schema_version ?? '—'}
                </span>
              )}
              <button
                onClick={() => { setMobileOpen(false); onAbout(); }}
                className="ml-auto flex items-center gap-1.5 p-1.5 rounded-md hover:bg-bg-hover transition"
              >
                <Info size={14} /> About
              </button>
              <button
                onClick={hardReload}
                className="flex items-center gap-1.5 p-1.5 rounded-md hover:bg-bg-hover transition"
                aria-label="Refresh page"
              >
                <RefreshCw size={14} /> Refresh
              </button>
            </div>
          </div>
        </div>
      )}

      {/* subtle page title bar */}
      <div className="max-w-[1400px] mx-auto px-3 sm:px-6 h-10 flex items-center text-xs sm:text-sm text-text-muted">
        <span className="truncate">
          {location.pathname === '/'              ? 'All 32 teams · R1 needs at a glance'
           : location.pathname === '/simulate'    ? 'Monte Carlo simulation · game-theoretic agent model'
           : location.pathname === '/prospects'   ? 'Consensus big board · top 80 prospects'
           : location.pathname === '/league'      ? 'League-wide patterns · cascades · known unknowns'
           : location.pathname === '/build'       ? 'Build your own mock · re-cascade model after each pick'
           : location.pathname === '/settings'    ? 'Model configuration · tunable weights'
           : location.pathname.startsWith('/team/') ? 'Team profile'
           : ''}
        </span>
      </div>
    </header>
  );
}

export default function App() {
  const [meta, setMeta] = useState<MetaInfo | null>(null);
  const [aboutOpen, setAboutOpen] = useState(false);

  useEffect(() => {
    api.meta().then(setMeta).catch(() => {/* backend may be warming */});
  }, []);

  return (
    <div className="min-h-full bg-bg text-text flex flex-col">
      <Header
        meta={meta}
        onAbout={() => setAboutOpen(true)}
      />
      <main className="max-w-[1400px] w-full mx-auto px-3 sm:px-6 py-4 sm:py-6 flex-1">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/team/:abbr" element={<TeamDetail />} />
          <Route path="/simulate" element={<Simulate />} />
          <Route path="/prospects" element={<Prospects />} />
          <Route path="/league" element={<League />} />
          <Route path="/build" element={<BuildMock />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
      <footer className="max-w-[1400px] w-full mx-auto px-3 sm:px-6 py-4 sm:py-6 text-xs text-text-subtle border-t border-border flex flex-wrap items-center justify-between gap-3">
        <div>
          Created by <span className="text-text-muted font-medium">Colin Sica</span> ·
          2026 NFL Draft Predictor ·
          {meta?.generated_at && ` built ${fmtDate(meta.generated_at)}`}
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => setAboutOpen(true)}
            className="hover:text-text transition"
          >
            About this model
          </button>
          <span>© {new Date().getFullYear()}</span>
        </div>
      </footer>
      <AboutModal open={aboutOpen} onClose={() => setAboutOpen(false)} />
    </div>
  );
}
