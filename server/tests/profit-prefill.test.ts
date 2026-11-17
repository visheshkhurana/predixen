import { test } from 'node:test';
import assert from 'node:assert/strict';
import { monthIsEmpty, prefillFromBaseline } from '../../client/src/lib/profitPrefill';

const baseline = { gross_sales: 2500000.4, cogs: 1125000, period: '2026-11' };

test('empty month gets sales and COGS from the baseline', () => {
  assert.deepEqual(prefillFromBaseline(undefined, baseline), { gross_sales: '2500000', cogs: '1125000' });
  assert.deepEqual(prefillFromBaseline({ orders_shipped: null }, baseline), { gross_sales: '2500000', cogs: '1125000' });
});

test('a month with any saved number is left alone', () => {
  assert.deepEqual(prefillFromBaseline({ orders_shipped: 900 }, baseline), {});
});

test('no baseline or no sales means no prefill; COGS alone is not used', () => {
  assert.deepEqual(prefillFromBaseline(undefined, null), {});
  assert.deepEqual(prefillFromBaseline(undefined, { gross_sales: null, cogs: 5, period: '2026-11' }), {});
  assert.deepEqual(prefillFromBaseline(undefined, { gross_sales: 100, cogs: null, period: '2026-11' }), { gross_sales: '100' });
});

test('monthIsEmpty', () => {
  assert.equal(monthIsEmpty({}), true);
  assert.equal(monthIsEmpty({ cogs: 0 }), false);
});
