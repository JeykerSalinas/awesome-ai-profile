import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { test } from 'node:test'
import {
  chapters,
  chapterIndex,
  sourceUrl,
  storyCopy,
} from '../src/features/tour/story.ts'
import { placeCard } from '../src/features/tour/placement.ts'

test('every chapter has a unique ID, a real UI anchor and an existing source file', () => {
  const view = readFileSync(
    new URL('../src/views/MainView.vue', import.meta.url),
    'utf8',
  )
  assert.equal(
    new Set(chapters.map((chapter) => chapter.id)).size,
    chapters.length,
  )
  for (const chapter of chapters) {
    assert.ok(view.includes(`data-tour="${chapter.target}"`), chapter.target)
    assert.ok(
      existsSync(new URL(`../../${chapter.source}`, import.meta.url)),
      chapter.source,
    )
    assert.ok(chapter.technologies.length > 0)
    assert.equal(new URL(sourceUrl(chapter.source)).hostname, 'github.com')
  }
})

test('all seven chapters and every control have matching English and Spanish content', () => {
  assert.equal(chapters.length, 7)
  assert.deepEqual(
    Object.keys(storyCopy.en).sort(),
    Object.keys(storyCopy.es).sort(),
  )
  for (const chapter of chapters) {
    assert.deepEqual(
      Object.keys(chapter.en).sort(),
      Object.keys(chapter.es).sort(),
    )
    for (const locale of ['en', 'es']) {
      assert.equal(chapter[locale].flow.length, 3)
      for (const value of Object.values(chapter[locale]))
        assert.ok(value.length > 0)
    }
  }
})

test('chapter navigation clamps at either boundary and handles invalid indexes', () => {
  assert.equal(chapterIndex(-1), 0)
  assert.equal(chapterIndex(7), 6)
  assert.equal(chapterIndex(2), 2)
  assert.equal(chapterIndex(2.7), 2)
  assert.equal(chapterIndex(NaN), 0)
})

test('source links are constrained to the project and encode individual path segments', () => {
  assert.equal(
    sourceUrl('app/a file.ts'),
    'https://github.com/JeykerSalinas/awesome-ai-profile/blob/main/app/a%20file.ts',
  )
})

test('missing targets place the card in the center', () => {
  assert.deepEqual(
    placeCard({ width: 1440, height: 900 }, { width: 450, height: 600 }, null),
    { left: 495, top: 150 },
  )
})

test('desktop placement leaves small targets unobstructed', () => {
  const target = { left: 60, top: 50, width: 200, height: 50 }
  const position = placeCard(
    { width: 1440, height: 900 },
    { width: 450, height: 600 },
    target,
  )
  assert.ok(position.left >= target.left + target.width)
  assert.ok(position.top >= 16)
})

test('a right-edge target moves the card to its left', () => {
  const target = { left: 1320, top: 50, width: 80, height: 50 }
  const position = placeCard(
    { width: 1440, height: 900 },
    { width: 450, height: 600 },
    target,
  )
  assert.ok(position.left + 450 < target.left)
})

test('full-width lower and upper anchors use the available space above or below', () => {
  const viewport = { width: 1440, height: 1000 }
  const card = { width: 450, height: 600 }
  assert.equal(
    placeCard(viewport, card, { left: 20, top: 850, width: 1400, height: 70 })
      .top,
    226,
  )
  assert.equal(
    placeCard(viewport, card, { left: 20, top: 20, width: 1400, height: 70 })
      .top,
    114,
  )
})

test('mobile and short-screen placements stay inside the visible viewport', () => {
  for (const viewport of [
    { width: 320, height: 568 },
    { width: 390, height: 844 },
    { width: 844, height: 390 },
  ]) {
    const card = {
      width: Math.min(450, viewport.width - 32),
      height: viewport.height - 32,
    }
    const position = placeCard(viewport, card, {
      left: 20,
      top: 80,
      width: 30,
      height: 30,
    })
    assert.ok(position.left >= 16)
    assert.ok(position.top >= 16)
    assert.ok(position.left + card.width <= viewport.width - 16)
    assert.ok(position.top + card.height <= viewport.height - 16)
  }
})
