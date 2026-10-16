import test from 'node:test'
import assert from 'node:assert/strict'
import { resolveProfile } from '../src/config/profile.ts'

test('default branding remains Django', () => {
  assert.equal(resolveProfile().assistantName, 'Django')
  assert.ok(resolveProfile().logo)
})
test('Sara does not inherit the Django logo', () => {
  assert.equal(resolveProfile('sara').assistantName, 'Sara')
  assert.equal(resolveProfile('sara').logo, null)
})
test('invalid profile fails instead of displaying another identity', () => {
  assert.throws(() => resolveProfile('unknown'))
  assert.throws(() => resolveProfile('__proto__'))
})
