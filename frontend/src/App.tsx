import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import {
  Activity, LayoutDashboard, PlayCircle, RefreshCw, Info,
  UserCircle, ArrowRightLeft, Globe, ClipboardList,
} from 'lucide-react';
import { Dashboard } from './pages/Dashboard';
import { TeamDetail } from './pages/TeamDetail';
import { Simulate } from './pages/Simulate';
import { Prospects } from './pages/Prospects';
import { Trades } from './pages/Trades';
import { League } from './pages/League';
import { BuildMock } from './pages/BuildMock';
import { AboutModal } from './components/AboutModal';
import { api, type MetaInfo } from './lib/api';
import { cn, fmtDate } from './lib/format';

function Nav() {
  const links = [
    { to: '/',          label: 'Teams',      Icon: LayoutDashboard, end: true },
    { to: '/simulate',  label: 'Simulate',   Icon: PlayCircle,      end: true },
    { to: '/build',     label: 'Build mock', Icon: ClipboardList,   end: true },
    { to: '/prospects', label: 'Prospects',  Icon: UserCircle,      end: true },
    { to: '/trades',    label: 'Trades',     Icon: ArrowRightLeft,  end: true },
    { to: '/league',    label: 'League',     Icon: Globe,           end: true },
  ];
  return (
    <nav className="flex items-center gap-1">
      {links.map((l) => (
        <NavLink
          key={l.to}
          to={l.to}
          end={l.end}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition',
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
  const gen = meta?.generated_at;
  const intelDate = meta?.analyst_intel_meta?.latest_intel_date;
  return (
    <header className="sticky top-0 z-30 backdrop-blur bg-bg/80 border-b border-border">
      <div className="max-w-[1400px] mx-auto px-6 h-14 flex items-center gap-6">
        <Link to="/" className="flex items-center gap-2 group">
          <div className="w-7 h-7 rounded-md bg-gradient-to-br from-accent to-violet-400 grid place-items-center shadow-glow">
            <span className="text-[11px] font-bold text-white tracking-tight">2026</span>
          </div>
          <span className="font-semibold tracking-tight">Draft Predictor</span>
          <span className="hidden sm:inline text-text-subtle text-xs">
            · NFL 2026
          </span>
        </Link>
        <div className="flex-1">
          <Nav />
        </div>
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
          >
            <Info size={14} className="text-text-muted" />
          </button>
          <button
            onClick={() => {
              // Hard-reload so both (a) the model's JSON/CSV outputs AND
              // (b) the website bundle itself (if it was rebuilt) are
              // refetched. Cache-bust via window.location.href reassignment
              // which bypasses some caches that location.reload() hits.
              try { (window as any).location.reload(true); }
              catch { window.location.href = window.location.href; }
            }}
            className="p-1.5 rounded-md hover:bg-bg-hover transition"
            title="Hard refresh — picks up new data AND new website versions"
            aria-label="Refresh page"
          >
            <RefreshCw size={14} className="text-text-muted" />
          </button>
        </div>
      </div>
      {/* subtle page title bar */}
      <div className="max-w-[1400px] mx-auto px-6 h-10 flex items-center text-sm text-text-muted">
        <span>
          {location.pathname === '/'              ? 'All 32 teams · R1 needs at a glance'
           : location.pathname === '/simulate'    ? 'Monte Carlo simulation · game-theoretic agent model'
           : location.pathname === '/prospects'   ? 'Consensus big board · top 80 prospects'
           : location.pathname === '/trades'      ? 'Analyst-mocked trade scenarios · tier-1 credibility'
           : location.pathname === '/league'      ? 'League-wide patterns · cascades · known unknowns'
           : location.pathname === '/build'       ? 'Build your own mock · re-cascade model after each pick'
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
      <main className="max-w-[1400px] w-full mx-auto px-6 py-6 flex-1">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/team/:abbr" element={<TeamDetail />} />
          <Route path="/simulate" element={<Simulate />} />
          <Route path="/prospects" element={<Prospects />} />
          <Route path="/trades" element={<Trades />} />
          <Route path="/league" element={<League />} />
          <Route path="/build" element={<BuildMock />} />
        </Routes>
      </main>
      <footer className="max-w-[1400px] w-full mx-auto px-6 py-6 text-xs text-text-subtle border-t border-border flex flex-wrap items-center justify-between gap-3">
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
