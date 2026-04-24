/**
 * AtAGlanceStats — minimal live-accuracy card for the Home hero right
 * rail (~340px wide). One card, three rows:
 *
 *   1. Big rank "#12" and "of N analysts"
 *   2. Exact-hits sentence with hit-rate pill
 *   3. 32-pin strip showing hit / miss for each R1 slot
 *
 * The dense histogram / dot-plot lives on the full /accuracy page.
 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';
import { SmallCaps } from './editorial';

type AnalystRow = { name: string; exact: number; rank: number };
type PickRow = {
  pick: number;
  actual_player: string | null;
  colin_hit: boolean | null;
};
type AccuracyResp = {
  r1_picks_drafted: number;
  total_r1_picks: number;
  total_analysts: number;
  analysts: AnalystRow[];
  picks: PickRow[];
};

export function AtAGlanceStats() {
  const [data, setData] = useState<AccuracyResp | null>(null);

  useEffect(() => {
    fetch('/api/accuracy')
      .then(r => r.ok ? r.json() : null)
      .then(setData)
      .catch(() => {});
  }, []);

  if (!data || data.r1_picks_drafted === 0) return null;
  const colin = data.analysts.find(a => a.name === 'Colin');
  if (!colin) return null;

  const scored = data.r1_picks_drafted;
  const hitPct = scored > 0 ? Math.round(colin.exact / scored * 100) : 0;

  return (
    <div className="space-y-2.5">
      <div className="flex items-baseline justify-between">
        <SmallCaps tight>Mock accuracy</SmallCaps>
        <Link
          to="/accuracy"
          className="font-mono text-[0.62rem] text-accent-brass hover:text-accent-brassDeep inline-flex items-center gap-0.5"
        >
          full <ArrowUpRight size={10} />
        </Link>
      </div>

      <div className="border border-ink-edge bg-paper-surface px-4 py-4 space-y-3">
        {/* Rank */}
        <div className="flex items-baseline gap-3">
          <span className="display-num text-5xl leading-none text-accent-brass">
            #{colin.rank}
          </span>
          <span className="font-mono text-[0.68rem] text-ink-muted leading-tight pb-0.5">
            of {data.total_analysts}<br />
            analysts
          </span>
        </div>

        {/* Exact hits + pill */}
        <div className="flex items-baseline justify-between border-t border-ink-edge pt-2.5">
          <span className="font-mono text-xs text-ink">
            <span className="display-num text-lg text-ink">{colin.exact}</span>
            <span className="text-ink-muted"> / {scored} exact</span>
          </span>
          <span
            className="caps-tight text-[0.58rem] font-bold px-1.5 py-[2px] rounded-sm"
            style={{ background: '#B68A2F', color: '#FAF6E6' }}
          >
            {hitPct}% hit rate
          </span>
        </div>

        {/* 32-pin hit strip */}
        <PinStrip picks={data.picks} />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// PinStrip — one small square per R1 slot (hit / miss / pending)
// ─────────────────────────────────────────────────────────────────────
function PinStrip({ picks }: { picks: PickRow[] }) {
  return (
    <div>
      <div
        className="grid gap-[2px]"
        style={{ gridTemplateColumns: 'repeat(16, minmax(0, 1fr))' }}
      >
        {Array.from({ length: 32 }, (_, i) => {
          const slot = i + 1;
          const p = picks.find(pk => pk.pick === slot);
          const drafted = p?.actual_player != null;
          const hit = p?.colin_hit === true;
          const bg = !drafted ? '#E8E2D4' : hit ? '#3A6B46' : '#8C2E2A';
          return (
            <div
              key={slot}
              className="aspect-square rounded-[2px]"
              style={{ background: bg }}
              title={
                drafted
                  ? `Pick ${slot}: ${hit ? 'hit' : 'miss'}`
                  : `Pick ${slot}: pending`
              }
            />
          );
        })}
      </div>
      <div className="flex items-center gap-3 mt-2 font-mono text-[0.58rem] text-ink-muted">
        <span className="inline-flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-sm" style={{ background: '#3A6B46' }} />
          hit
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-sm" style={{ background: '#8C2E2A' }} />
          miss
        </span>
      </div>
    </div>
  );
}
