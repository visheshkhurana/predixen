import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  canJudgeHealth,
  hasFinancialData,
  joinWithAnd,
  missingDataHints,
  runwayKind,
  scoreDisplay,
  MIN_CONFIDENCE_TO_JUDGE,
} from '../../client/src/lib/dataSufficiency';
import {
  journalEntriesToShow,
  stripSampleJournalEntries,
  SAMPLE_JOURNAL_ENTRIES,
} from '../../client/src/lib/journalSample';

test('an empty company has no financial data', () => {
  assert.equal(hasFinancialData(null), false);
  assert.equal(hasFinancialData({ mrr: 0, cashOnHand: 0, totalMonthlyExpenses: 0, netBurn: 0 }), false);
  assert.equal(hasFinancialData({ mrr: 450000 }), true);
  assert.equal(hasFinancialData({ cashOnHand: 1 }), true);
  assert.equal(hasFinancialData({ netBurn: -2000 }), true);
  assert.equal(hasFinancialData({ mrr: NaN }), false);
});

test('no verdict without data or with confidence under the threshold', () => {
  assert.equal(MIN_CONFIDENCE_TO_JUDGE, 20);
  assert.equal(canJudgeHealth({ hasData: false, confidence: 90 }), false);
  assert.equal(canJudgeHealth({ hasData: true, confidence: 0 }), false);
  assert.equal(canJudgeHealth({ hasData: true, confidence: 19 }), false);
  assert.equal(canJudgeHealth({ hasData: true, confidence: null }), false);
  assert.equal(canJudgeHealth({ hasData: true, confidence: 20 }), true);
});

test('missing data hints are plain language', () => {
  assert.deepEqual(missingDataHints({}), ['monthly revenue', 'monthly expenses', 'cash in the bank']);
  assert.deepEqual(missingDataHints({ mrr: 10, cashOnHand: 5 }), ['monthly expenses']);
  assert.equal(joinWithAnd(['a', 'b', 'c']), 'a, b and c');
  assert.equal(joinWithAnd(['a']), 'a');
  assert.equal(joinWithAnd([]), '');
});

test('a 0 score with no data is "Not scored yet", a real score is kept', () => {
  assert.deepEqual(scoreDisplay(0, { hasData: false }), { scored: false, label: 'Not scored yet' });
  assert.deepEqual(scoreDisplay(null, { hasData: true }), { scored: false, label: 'Not scored yet' });
  assert.deepEqual(scoreDisplay(0, { hasData: true }), { scored: true, value: 0 });
  assert.deepEqual(scoreDisplay(42.4, { hasData: true }), { scored: true, value: 42 });
  // A default score on an empty company (the old 45/100) is not a judgement.
  assert.deepEqual(scoreDisplay(45, { hasData: false }), { scored: false, label: 'Not scored yet' });
});

test('zero burn from zero figures is never "Sustainable"', () => {
  assert.equal(runwayKind({ sustainableFlag: true, runway: Infinity, revenue: 0, expenses: 0, cash: 0 }), 'unknown');
  assert.equal(runwayKind({ runway: 999 }), 'unknown');
  assert.equal(runwayKind({ runway: 0, revenue: 0, expenses: 0, cash: 0 }), 'unknown');
  // Cash but no revenue: unlimited runway is only because no expenses are entered.
  assert.equal(runwayKind({ runway: Infinity, cash: 100000 }), 'unknown');
  assert.equal(runwayKind({ sustainableFlag: true, runway: Infinity, revenue: 50000, expenses: 40000, cash: 0 }), 'sustainable');
  assert.equal(runwayKind({ runway: 14.2, revenue: 10000, expenses: 30000, cash: 280000 }), 'finite');
});

test('journal: real companies never see sample entries', () => {
  assert.deepEqual(journalEntriesToShow({ stored: null, isSample: false }), []);
  assert.deepEqual(journalEntriesToShow({ stored: [], isSample: false }), []);
  // Older builds saved the sample entries next to the founder's own one.
  const mine = { id: 1730000000000, title: 'Hire ops lead', decision: 'Hire', reasoning: '', status: 'pending', date: '2026-11-01', impact: 'medium' };
  const legacy = [mine, ...SAMPLE_JOURNAL_ENTRIES.map(({ sample: _s, ...rest }) => rest)];
  assert.deepEqual(journalEntriesToShow({ stored: legacy, isSample: false }), [mine]);
  assert.deepEqual(stripSampleJournalEntries('garbage'), []);
});

test('journal: sample companies see labelled sample entries until they log one', () => {
  const shown = journalEntriesToShow({ stored: [], isSample: true });
  assert.equal(shown.length, SAMPLE_JOURNAL_ENTRIES.length);
  assert.ok(shown.every((e) => e.sample === true));
  const mine = { id: 99, title: 'Mine', decision: 'x', reasoning: '', status: 'pending', date: '2026-11-01', impact: 'low' };
  assert.deepEqual(journalEntriesToShow({ stored: [mine], isSample: true }), [mine]);
});
