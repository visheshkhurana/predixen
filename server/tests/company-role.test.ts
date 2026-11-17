import { test } from 'node:test';
import assert from 'node:assert/strict';
import { isViewOnlyMember } from '../../client/src/lib/companyRole';

const members = [
  { user_id: 1, role: 'owner', status: 'active' },
  { user_id: 2, role: 'editor', status: 'active' },
  { user_id: 3, role: 'viewer', status: 'active' },
  { user_id: 4, role: 'viewer', status: 'suspended' },
];

test('viewer is view-only', () => assert.equal(isViewOnlyMember(members, 3), true));
test('owner and editor are not', () => {
  assert.equal(isViewOnlyMember(members, 1), false);
  assert.equal(isViewOnlyMember(members, 2), false);
});
test('unknown user, inactive viewer, or no data fails open to showing actions', () => {
  assert.equal(isViewOnlyMember(members, 99), false);
  assert.equal(isViewOnlyMember(members, 4), false);
  assert.equal(isViewOnlyMember(undefined, 3), false);
  assert.equal(isViewOnlyMember(members, undefined), false);
});
