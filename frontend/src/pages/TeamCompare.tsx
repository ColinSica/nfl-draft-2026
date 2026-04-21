/**
 * Team compare — pick any two teams, see their picks/needs/trade behavior
 * side-by-side. Answers "how do these two teams differ going into the draft?"
 */
import { useEffect, useMemo, useState } from 'react';
import { api, type TeamSummary } from '../lib/api';
import { teamColor } from '../lib/teamColors';
import { SectionHeader, SmallCaps, HRule } from '../components/editorial';
import { displayValue, displayQbSituation, displayCapTier } from '../lib/display';

export function TeamCompare() {
  const [teams, setTeams] = useState<TeamSummary[] | null>(null);
  const [a, setA] = useState<string>('');
  const [b, setB] = useState<string>('');
  const [detailA, setDetailA] = useState<any>(null);
  const [detailB, setDetailB] = useState<any>(null);

  useEffect(() => {
    api.teams().then(r => {
      setTeams(r.teams);
      // default pair: first two with distinct R1 picks
      if (r.teams.length >= 2) {
        const first = r.teams.find(t => (t.r1_picks ?? []).length);
        const second = r.teams.find(t => (t.r1_picks ?? []).length && t.team !== first?.team);
        if (first) setA(first.team);
        if (second) setB(second.team);
      }
    }).catch(() => setTeams([]));
  }, []);

  useEffect(() => {
    if (a) api.team(a).then(setDetailA).catch(() => setDetailA(null));
  }, [a]);
  useEffect(() => {
    if (b) api.team(b).then(setDetailB).catch(() => setDetailB(null));
  }, [b]);

  const options = useMemo(() => {
    return (teams ?? [])
      .map(t => ({ val: t.team, label: t.team, sort: t.r1_picks?.[0] ?? 999 }))
      .sort((x, y) => x.sort - y.sort);
  }, [teams]);

  return (
    <div className="space-y-10 pb-16">
      <SectionHeader kicker="Compare" title="Two teams, side by side." />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <TeamPicker label="Team A" value={a} onChange={setA} options={options} />
        <TeamPicker label="Team B" value={b} onChange={setB} options={options} />
      </div>

      {detailA && detailB ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <TeamPanel data={detailA} />
          <TeamPanel data={detailB} />
        </div>
      ) : (
        <div className="card p-10 text-center text-ink-soft italic">
          Pick two teams to compare.
        </div>
      )}
    </div>
  );
}

function TeamPicker({
  label, value, onChange, options,
}: { label: string; value: string; onChange: (v: string) => void; options: { val: string; label: string }[] }) {
  return (
    <label className="flex flex-col gap-2">
      <SmallCaps tight className="text-ink-soft">{label}</SmallCaps>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="px-3 py-2.5 bg-paper-surface border border-ink-edge text-ink font-mono display-broadcast text-lg"
      >
        <option value="">Choose…</option>
        {options.map(o => <option key={o.val} value={o.val}>{o.val}</option>)}
      </select>
    </label>
  );
}

function TeamPanel({ data }: { data: any }) {
  const tc = teamColor(data.team);
  const needs = Object.entries(data.roster_needs ?? {})
    .map(([p, w]) => [p, Number(w)] as [string, number])
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);

  return (
    <article className="card overflow-hidden" style={{ borderLeft: `4px solid ${tc.primary}` }}>
      <div className="p-5 space-y-4" style={{ background: `linear-gradient(180deg, ${tc.primary}08 0%, transparent 45%)` }}>
        <div className="flex items-center gap-3">
          <span className="display-broadcast text-2xl px-2.5 py-1"
            style={{
              background: tc.primary,
              color: tc.secondary === '#000000' ? '#FFFFFF' : tc.secondary,
            }}>
            {data.team}
          </span>
          <div>
            <h3 className="display-broadcast text-2xl text-ink leading-none">{tc.name}</h3>
            <div className="text-xs text-ink-soft mt-1 font-mono">
              {displayValue(data.coaching?.hc ?? data.hc, 'HC —')} · {displayValue(data.gm, 'GM —')}
            </div>
          </div>
        </div>

        <HRule />

        <Row label="R1 pick(s)" value={data.r1_picks?.join(' · ') ?? '—'} emphasize />
        <Row label="Total picks" value={data.total_picks ?? '—'} />
        <Row label="QB situation" value={displayQbSituation(data.qb_situation)} />
        <Row label="Cap tier" value={displayCapTier(data.cap_context?.cap_tier ?? data.cap_tier)} />
        <Row label="Scheme" value={data.scheme?.type ?? data.scheme?.base ?? '—'} />
        <Row label="Coaching tree" value={data.coaching?.hc_tree ?? '—'} />
        <Row label="Trade-up rate"
          value={`${Math.round(Number(data.trade_behavior?.trade_up_rate ?? data.trade_up_rate ?? 0) * 100)}%`} />
        <Row label="Trade-down rate"
          value={`${Math.round(Number(data.trade_behavior?.trade_down_rate ?? data.trade_down_rate ?? 0) * 100)}%`} />

        <HRule />
        <div>
          <SmallCaps tight className="text-ink-soft block mb-2">Top needs</SmallCaps>
          <div className="space-y-1.5">
            {needs.map(([pos, w]) => (
              <div key={pos} className="flex items-center gap-3">
                <span className="caps-tight text-ink w-12 shrink-0">{pos}</span>
                <div className="flex-1 h-1.5 bg-paper-hover overflow-hidden">
                  <div
                    className="h-full"
                    style={{ width: `${Math.min(100, (w / 5) * 100)}%`, background: tc.primary }}
                  />
                </div>
                <span className="font-mono text-xs text-ink-soft w-10 shrink-0 text-right">{w.toFixed(1)}</span>
              </div>
            ))}
          </div>
        </div>

        {data._4_21_news && (
          <div className="mt-3 p-3 text-xs" style={{ background: `${tc.primary}08`, borderLeft: `2px solid ${tc.primary}` }}>
            <SmallCaps tight className="text-ink-soft block mb-0.5">Latest intel</SmallCaps>
            <p className="text-ink leading-relaxed">
              {Array.isArray(data._4_21_news) ? data._4_21_news.join(' · ') : data._4_21_news}
            </p>
          </div>
        )}
      </div>
    </article>
  );
}

function Row({ label, value, emphasize }: { label: string; value: React.ReactNode; emphasize?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-3 text-sm">
      <SmallCaps tight className="text-ink-soft">{label}</SmallCaps>
      <span className={`text-right ${emphasize ? 'display-broadcast text-lg text-ink' : 'text-ink font-mono'}`}>
        {value}
      </span>
    </div>
  );
}
