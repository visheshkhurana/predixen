import { test } from 'node:test';
import assert from 'node:assert/strict';
import { errorMessageFromBody } from '../../client/src/lib/queryClient';

test('string detail is shown', () => {
  assert.equal(errorMessageFromBody({ detail: 'Editing requires editor access' }), 'Editing requires editor access');
});
test('object detail message', () => {
  assert.equal(errorMessageFromBody({ detail: { message: 'Plan limit reached', error: 'plan_limit_reached' } }), 'Plan limit reached');
});
test('validation list joins msgs', () => {
  assert.equal(errorMessageFromBody({ detail: [{ msg: 'field required' }, { msg: 'too long' }] }), 'field required; too long');
});
test('top-level message/error and empty bodies', () => {
  assert.equal(errorMessageFromBody({ message: 'Nope' }), 'Nope');
  assert.equal(errorMessageFromBody({ error: 'Notion request failed.' }), 'Notion request failed.');
  assert.equal(errorMessageFromBody({}), null);
  assert.equal(errorMessageFromBody(null), null);
});
