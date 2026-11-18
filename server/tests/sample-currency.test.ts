import test from 'node:test';
import assert from 'node:assert/strict';
import { sampleInsightFor, sampleScale } from '../../client/src/lib/sampleCompany';

test('sample insight is sized for the company currency, runway unchanged', () => {
  const usd = sampleInsightFor('USD');
  const inr = sampleInsightFor('INR');
  assert.equal(inr.inputs.monthly_revenue, usd.inputs.monthly_revenue * 20);
  assert.equal(inr.outputs.runway_months, usd.outputs.runway_months);
  assert.equal(sampleScale('xyz'), 1);
});
