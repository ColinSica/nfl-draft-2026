import { useEffect, useState } from 'react';
import { RotateCcw, Save, Info, AlertTriangle } from 'lucide-react';
import { cn } from '../lib/format';

// Tunable knobs — names match the stage2 Python constants.
type ModelSettings = {
  reach_gap_threshold: number;
  late_pick_reach_threshold: number;
  elite_cons_rank_threshold: number;
  slider_boost_threshold: number;
  position_scarcity_gap: number;
  position_scarcity_boost: number;
  predictability_score_sigma: number;
  post_combine_boosts: Record<string, number>;
  qb_cascade_window: number;
  tier_sizes: Record<string, number>;
  pos_value_mult: Record<string, number>;
};

const STORAGE_KEY = 'draft_dash_model_settings';

export function Settings() {
  const [defaults, setDefaults] = useState<ModelSettings | null>(null);
  const [edited, setEdited] = useState<ModelSettings | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetch('/api/settings/defaults').then((r) => r.json()).then((d: ModelSettings) => {
      setDefaults(d);
      // Load user overrides from localStorage, fall back to server defaults
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) {
          const parsed = JSON.parse(raw) as Partial<ModelSettings>;
          setEdited({ ...d, ...parsed });
          return;
        }
      } catch { /* noop */ }
      setEdited({ ...d });
    });
  }, []);

  const save = () => {
    if (!edited) return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(edited));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const reset = async () => {
    if (!confirm('Reset all model settings to server defaults? Your local tweaks will be cleared.')) return;
    const r = await fetch('/api/settings/defaults').then((r) => r.json());
    setDefaults(r);
    setEdited({ ...r });
    localStorage.removeItem(STORAGE_KEY);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  if (!edited || !defaults) {
    return <div className="text-text-muted text-sm">Loading settings…</div>;
  }

  const isChanged = (key: keyof ModelSettings) =>
    JSON.stringify(edited[key]) !== JSON.stringify(defaults[key]);

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted mb-1">
            Model configuration
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">Tune the model</h1>
          <p className="text-sm text-text-muted mt-1 max-w-3xl">
            Adjust weights and thresholds that control how the Monte Carlo sim
            reasons about picks and trades. Values save locally in your browser —
            reset to defaults anytime to pull the latest server-side values.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={save}
            className="btn-primary text-sm"
          >
            <Save size={14} /> {saved ? 'Saved' : 'Save'}
          </button>
          <button
            onClick={reset}
            className="btn-ghost text-sm border-tier-midlo/30 text-tier-midlo hover:bg-tier-midlo/10"
            title="Fetch latest server defaults — picks up code changes"
          >
            <RotateCcw size={14} /> Reset to defaults
          </button>
        </div>
      </div>

      <div className="card p-4 flex items-start gap-3 text-xs text-text-muted border-accent/20 bg-accent/5">
        <Info size={14} className="mt-0.5 flex-none text-accent" />
        <div>
          <div className="font-medium text-text mb-1">How this works</div>
          Local overrides are stored in your browser. Sim runs use the server's
          built-in defaults unless you save your changes and the backend
          version accepts the override (some knobs are currently display-only;
          others feed directly into sim runs).
          <span className="text-tier-midlo font-medium ml-1">
            If a knob is marked "live," your value applies to new sim runs.
          </span>
        </div>
      </div>

      {/* Scoring thresholds */}
      <Section title="Scoring thresholds" subtitle="How far the model will reach or defer to sliders">
        <NumInput
          label="Reach gap (picks 1-20)"
          help="How many slots below the current pick a player can be before the model halves their score. Lower = stricter."
          value={edited.reach_gap_threshold}
          defaultValue={defaults.reach_gap_threshold}
          onChange={(v) => setEdited({ ...edited, reach_gap_threshold: v })}
          changed={isChanged('reach_gap_threshold')}
          live
        />
        <NumInput
          label="Reach gap (picks 21-32)"
          help="Same idea for late R1. Allows slightly wider reach late."
          value={edited.late_pick_reach_threshold}
          defaultValue={defaults.late_pick_reach_threshold}
          onChange={(v) => setEdited({ ...edited, late_pick_reach_threshold: v })}
          changed={isChanged('late_pick_reach_threshold')}
        />
        <NumInput
          label="Elite consensus threshold"
          help="Top-N consensus players always get need_match >= 1.0 (elite BPA override)."
          value={edited.elite_cons_rank_threshold}
          defaultValue={defaults.elite_cons_rank_threshold}
          onChange={(v) => setEdited({ ...edited, elite_cons_rank_threshold: v })}
          changed={isChanged('elite_cons_rank_threshold')}
        />
        <NumInput
          label="Slider boost threshold"
          help="Top-N consensus prospects get progressive boost as they slide past their expected slot."
          value={edited.slider_boost_threshold}
          defaultValue={defaults.slider_boost_threshold}
          onChange={(v) => setEdited({ ...edited, slider_boost_threshold: v })}
          changed={isChanged('slider_boost_threshold')}
        />
      </Section>

      {/* Positional scarcity */}
      <Section title="Positional scarcity" subtitle="When a position has a clear #1 and a big gap to #2">
        <NumInput
          label="Scarcity gap threshold"
          help="If #2-at-position is ranked this many spots below #1, apply scarcity boost to #1."
          value={edited.position_scarcity_gap}
          defaultValue={defaults.position_scarcity_gap}
          onChange={(v) => setEdited({ ...edited, position_scarcity_gap: v })}
          changed={isChanged('position_scarcity_gap')}
        />
        <NumInput
          label="Scarcity boost multiplier"
          help="How much to boost the top-1 at position when there's a big tier gap. 1.15 = 15% boost."
          step={0.05}
          value={edited.position_scarcity_boost}
          defaultValue={defaults.position_scarcity_boost}
          onChange={(v) => setEdited({ ...edited, position_scarcity_boost: v })}
          changed={isChanged('position_scarcity_boost')}
        />
      </Section>

      {/* Variance knobs */}
      <Section title="Simulation variance" subtitle="How much sim-to-sim noise the model accepts">
        <NumInput
          label="Predictability noise sigma"
          help="Base noise scale for per-team predictability multiplier. Higher = more variance."
          step={0.01}
          value={edited.predictability_score_sigma}
          defaultValue={defaults.predictability_score_sigma}
          onChange={(v) => setEdited({ ...edited, predictability_score_sigma: v })}
          changed={isChanged('predictability_score_sigma')}
        />
        <NumInput
          label="QB cascade window"
          help="How many picks ahead to look when detecting QB demand > supply."
          value={edited.qb_cascade_window}
          defaultValue={defaults.qb_cascade_window}
          onChange={(v) => setEdited({ ...edited, qb_cascade_window: v })}
          changed={isChanged('qb_cascade_window')}
        />
      </Section>

      {/* Post-combine boosts */}
      <Section title="Post-combine boosts" subtitle="Per-player multipliers for prospects whose stage-1 data is stale">
        {Object.entries(edited.post_combine_boosts).map(([name, mult]) => (
          <NumInput
            key={name}
            label={name}
            help={`Multiplier on this player's score. 1.20 = +20%. Server default: ${defaults.post_combine_boosts[name]}x`}
            step={0.05}
            value={mult}
            defaultValue={defaults.post_combine_boosts[name] ?? 1.0}
            onChange={(v) => setEdited({
              ...edited,
              post_combine_boosts: { ...edited.post_combine_boosts, [name]: v },
            })}
            changed={edited.post_combine_boosts[name] !== defaults.post_combine_boosts[name]}
          />
        ))}
      </Section>

      {/* Position values */}
      <Section title="Position-value multipliers" subtitle="How much the model discounts non-premium positions">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {Object.entries(edited.pos_value_mult).map(([pos, mult]) => (
            <NumInput
              key={pos}
              label={pos}
              help={`Position-value multiplier. >1.0 = premium; <1.0 = discounted. Default: ${defaults.pos_value_mult[pos]}x`}
              step={0.05}
              value={mult}
              defaultValue={defaults.pos_value_mult[pos] ?? 1.0}
              onChange={(v) => setEdited({
                ...edited,
                pos_value_mult: { ...edited.pos_value_mult, [pos]: v },
              })}
              changed={edited.pos_value_mult[pos] !== defaults.pos_value_mult[pos]}
            />
          ))}
        </div>
      </Section>

      {/* Warning */}
      <div className="card p-4 flex items-start gap-3 text-xs border-tier-midlo/30 bg-tier-midlo/5">
        <AlertTriangle size={14} className="mt-0.5 flex-none text-tier-midlo" />
        <div className="text-text-muted">
          <span className="font-medium text-text">Tinkering warning:</span> the
          defaults are calibrated against 2021-2025 historical data and the
          2026 analyst consensus. Aggressive changes to position-value
          multipliers or post-combine boosts can produce unrealistic mocks
          (e.g. 15 EDGEs in R1). Click <span className="kbd">Reset to defaults</span> anytime.
        </div>
      </div>
    </div>
  );
}

function Section({
  title, subtitle, children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card p-5">
      <div className="mb-4">
        <h3 className="text-sm font-semibold tracking-tight">{title}</h3>
        {subtitle && (
          <div className="text-xs text-text-muted mt-0.5">{subtitle}</div>
        )}
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function NumInput({
  label, help, value, defaultValue, onChange, step = 1, changed, live,
}: {
  label: string;
  help?: string;
  value: number;
  defaultValue: number;
  onChange: (v: number) => void;
  step?: number;
  changed: boolean;
  live?: boolean;
}) {
  return (
    <div className={cn(
      'flex flex-wrap items-center gap-3 p-2.5 rounded-md',
      changed && 'bg-accent/5 border border-accent/20',
    )}>
      <div className="flex-1 min-w-[200px]">
        <div className="flex items-center gap-2">
          <div className="text-sm font-medium text-text">{label}</div>
          {live && (
            <span className="badge border-tier-high/40 bg-tier-high/10 text-tier-high text-[9px]">
              LIVE
            </span>
          )}
          {changed && (
            <span className="badge border-accent/40 bg-accent/10 text-accent text-[9px]">
              MODIFIED
            </span>
          )}
        </div>
        {help && (
          <div className="text-[11px] text-text-muted mt-0.5 leading-snug">{help}</div>
        )}
      </div>
      <input
        type="number"
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="bg-bg-raised border border-border rounded-md px-3 py-1.5 text-sm w-24 outline-none focus:border-accent font-mono tabular-nums text-right"
      />
      <div className="text-[10px] text-text-subtle font-mono whitespace-nowrap">
        default: <span className="text-text-muted">{defaultValue}</span>
      </div>
    </div>
  );
}
