import test from 'node:test';
import assert from 'node:assert/strict';
import { groupByStage, pipelineSummary, currentRound, relativeActivity, type BoardEntry } from '../../client/src/lib/fundraisingPipeline';

const e = (id: string, stage: BoardEntry['stage'], warm = false): BoardEntry =>
  ({ id, firm: id, partner: '', check_size: '', warm_intro: warm, stage, last_activity_at: null });

test('an empty company has an empty funnel, not a made-up one', () => {
  const s = pipelineSummary([]);
  assert.equal(s.total, 0);
  assert.deepEqual(s.funnel.map(f => f.count), [0, 0, 0, 0, 0]);
});

test('the banner funnel counts what the board columns show', () => {
  const entries = [e('a', 'sourced'), e('b', 'meeting', true), e('c', 'partner_meeting'), e('d', 'committed'), e('x', 'passed', true)];
  const board = groupByStage(entries);
  const s = pipelineSummary(entries);
  assert.equal(s.funnel[2].count, board.meeting.length + board.partner_meeting.length);
  assert.equal(s.funnel.reduce((n, f) => n + f.count, 0) + s.passed, s.total);
  assert.equal(s.warmIntros, 1, 'passed investors are not counted as warm intros');
  assert.equal(s.committed, 1);
});

test('current round prefers active, then planned, never closed', () => {
  assert.equal(currentRound([{ name: 'Seed', status: 'closed' }]), null);
  assert.equal(currentRound([{ name: 'P', status: 'planned' }, { name: 'A', status: 'active' }])?.name, 'A');
  assert.equal(currentRound(undefined), null);
});

test('relative activity', () => {
  const now = new Date('2026-11-18T12:00:00Z');
  assert.equal(relativeActivity('2026-11-18T08:00:00', now), 'Today');
  assert.equal(relativeActivity('2026-11-15T08:00:00Z', now), '3 days ago');
  assert.equal(relativeActivity(null, now), '');
});
