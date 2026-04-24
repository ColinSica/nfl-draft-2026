/**
 * Accuracy — full live scoreboard vs public analyst mocks.
 * Uses the shared AccuracyDashboard component in "full" mode.
 */
import { SectionHeader } from '../components/editorial';
import { AccuracyDashboard } from '../components/AccuracyDashboard';
import { AccuracyGraphs } from '../components/AccuracyGraphs';
import { LockBadge } from './Home';

export function Accuracy() {
  return (
    <div className="space-y-8 pb-16">
      <SectionHeader
        kicker="Live accuracy"
        title="Scoreboard."
        deck="How The Draft Ledger and ~30 published 2026 analyst mocks stack up against the actual R1 board. One point per exact player match at the correct slot."
      />
      <LockBadge />
      <AccuracyDashboard compact={false} />
      <AccuracyGraphs />
    </div>
  );
}
