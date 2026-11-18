import { test } from 'node:test';
import assert from 'node:assert/strict';
import { runwayChange, describeRunwayChange, runwayDeltaForScoring, scenarioConsistency, isSustainable } from '../../client/src/lib/simulationConsistency';

test('sentinel runway is never subtracted', () => {
  assert.deepEqual(runwayChange(28, 999), { kind: 'becomes_sustainable' });
  assert.deepEqual(runwayChange(999, 999), { kind: 'both_sustainable' });
  assert.deepEqual(runwayChange(999, 14), { kind: 'loses_sustainable', months: 14 });
  assert.equal(describeRunwayChange(runwayChange(28, 999)), 'runway becomes sustainable');
  assert.equal(runwayDeltaForScoring(runwayChange(28, 999)), 12);
  assert.equal(describeRunwayChange(runwayChange(10, 12.5)), '+2.5mo runway');
  assert.equal(describeRunwayChange(runwayChange(999, 999)), null);
  assert.equal(isSustainable(null), true);
  assert.equal(isSustainable(21.3), false);
});

test('adverse-only scenario that improves runway is flagged', () => {
  const r = scenarioConsistency({ burn_reduction_pct: -100, hiring_plan: [{}, {}] }, { runwayP50: 21, survival18m: 85 }, { runwayP50: 999, survival18m: 100 });
  assert.equal(r.consistent, false);
  assert.match(r.reason!, /cannot be right/);
});

test('adverse scenario that worsens runway is fine', () => {
  assert.equal(scenarioConsistency({ burn_reduction_pct: -50 }, { runwayP50: 21, survival18m: 85 }, { runwayP50: 10, survival18m: 60 }).consistent, true);
});

test('mixed levers (cost up, growth up) are not judged', () => {
  assert.equal(scenarioConsistency({ burn_reduction_pct: -15, growth_uplift_pct: 3 }, { runwayP50: 21 }, { runwayP50: 30 }).consistent, true);
});

test('no inputs or no baseline: nothing to compare', () => {
  assert.equal(scenarioConsistency(null, { runwayP50: 1 }, { runwayP50: 999 }).consistent, true);
  assert.equal(scenarioConsistency({ burn_reduction_pct: -10 }, null, { runwayP50: 999 }).consistent, true);
});

test('approximate (dashboard) baseline only flags the impossible case', () => {
  // Growth can legitimately lift a simulated runway above cash ÷ burn.
  assert.equal(scenarioConsistency({ hiring_plan: [{}] }, { runwayP50: 4.0 }, { runwayP50: 4.4 }, { approximate: true }).consistent, true);
  assert.equal(scenarioConsistency({ hiring_plan: [{}] }, { runwayP50: 10 }, { runwayP50: 999 }, { approximate: true }).consistent, false);
});

import { formatRunwayShort, runwaySentence } from '../../client/src/lib/simulationConsistency';

test('runway display never shows the sentinel or extrapolated precision', () => {
  assert.equal(formatRunwayShort(999), 'Sustainable');
  assert.equal(formatRunwayShort(222.3), '24+ mo');
  assert.equal(formatRunwayShort(9.04), '9.0 mo');
  assert.equal(formatRunwayShort(undefined), '?');
  assert.equal(runwaySentence(165), 'more than 24 months of runway');
  assert.equal(runwaySentence(999), 'a sustainable runway');
  assert.equal(runwaySentence(8.6), '9 months of runway');
});
