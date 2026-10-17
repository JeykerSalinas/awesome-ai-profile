import test from 'node:test'
import assert from 'node:assert/strict'
import { resolveProfile, mergeConfig, profileCopy } from '../src/config/profile.ts'

test('default branding remains Django', () => {
  assert.equal(resolveProfile().assistantName, 'Django')
  assert.ok(resolveProfile().logo)
})
test('Sara does not inherit the Django logo', () => {
  assert.equal(resolveProfile('sara').assistantName, 'Sara')
  assert.equal(resolveProfile('sara').logo, '/sara_design/sara_logo.jpeg')
})
test('invalid profile fails instead of displaying another identity', () => {
  assert.throws(() => resolveProfile('unknown'))
  assert.throws(() => resolveProfile('__proto__'))
})


test('nested overrides preserve defaults and false/null replace values', () => {
  assert.deepEqual(mergeConfig({ flags: { voice: true, tour: true }, logo: 'old', tools: ['a'] },
    { flags: { voice: false }, logo: null, tools: [] }),
    { flags: { voice: false, tour: true }, logo: null, tools: [] })
})
test('Sara copy overrides personal facts and indexed suggestions', () => {
  const sara = resolveProfile('sara')
  const copy = profileCopy({ candidateRole: 'Engineer', suggestions: ['Hire Jeyker', 'AI experience', 'Photo'] }, 'en', '', sara)
  assert.equal(copy.candidateRole, 'Professional profile')
  assert.equal(copy.suggestions[1], 'What verified information is available?')
  assert.equal(sara.features.tour, false)
  assert.equal(resolveProfile().features.tour, true)
})
test('tour copy supports stable chapter and nested array paths', () => {
  const profile = resolveProfile('sara')
  profile.texts.en['chapters.interface.flow.0'] = 'Custom flow'
  assert.deepEqual(profileCopy({ flow: ['Original'] }, 'en', 'chapters.interface', profile), { flow: ['Custom flow'] })
})
