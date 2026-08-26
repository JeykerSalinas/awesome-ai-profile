import assert from 'node:assert/strict'
import { test } from 'node:test'

import { renderMarkdown } from '../src/utils/chatMarkdown.ts'

const baseUrl = 'https://profile.example/chat'
const photo = '/jeyker.jpg'
const markdownPhoto = 'Aquí tienes su foto: ![Jeyker Salinas](/jeyker.jpg)'

test('photo card suppresses the duplicate Markdown image, retaining surrounding text', () => {
  const html = renderMarkdown(markdownPhoto, [photo], baseUrl)
  assert.doesNotMatch(html, /<img\b/)
  assert.match(html, /Aquí tienes su foto:/)
})

test('Markdown-only photo is still displayed', () => {
  assert.match(renderMarkdown(markdownPhoto, [], baseUrl), /<img src="\/jeyker\.jpg"/)
})

test('other images, origins and query variants are preserved', () => {
  for (const src of ['/project.png', 'https://other.example/jeyker.jpg', '/jeyker.jpg?v=2']) {
    assert.match(renderMarkdown(`![Other](${src})`, [photo], baseUrl), /<img\b/)
  }
})

test('relative, absolute, normalized and fragment URLs identify the same photo', () => {
  for (const src of [photo, './jeyker.jpg', '/images/../jeyker.jpg',
    'https://profile.example/jeyker.jpg', '//profile.example/jeyker.jpg', '/jeyker.jpg#portrait']) {
    assert.doesNotMatch(renderMarkdown(`![Jeyker](${src})`, [photo], baseUrl), /<img\b/)
  }
})

test('reference-style images are also suppressed', () => {
  const markdown = '![Jeyker][photo]\n\n[photo]: /jeyker.jpg'
  assert.doesNotMatch(renderMarkdown(markdown, [photo], baseUrl), /<img\b/)
})

test('a photo part arriving after text hides the duplicate on the next render', () => {
  const sources: string[] = []
  assert.match(renderMarkdown(markdownPhoto, sources, baseUrl), /<img\b/)
  sources.push(photo)
  assert.doesNotMatch(renderMarkdown(markdownPhoto, sources, baseUrl), /<img\b/)
})

test('photo state does not leak into other messages', () => {
  assert.doesNotMatch(renderMarkdown(markdownPhoto, [photo], baseUrl), /<img\b/)
  assert.match(renderMarkdown(markdownPhoto, [], baseUrl), /<img\b/)
})

test('all duplicates of every photo card are suppressed', () => {
  const markdown = `${markdownPhoto}\n\n![Again](${photo})\n\n![Second](/second.jpg)`
  assert.doesNotMatch(renderMarkdown(markdown, [photo, '/second.jpg'], baseUrl), /<img\b/)
})

test('normal links to the photo and Markdown formatting remain intact', () => {
  const html = renderMarkdown(`**Photo**\n\n[Download](${photo})\n\n- Item`, [photo], baseUrl)
  assert.match(html, /<strong>Photo<\/strong>/)
  assert.match(html, /<a href="\/jeyker\.jpg"/)
  assert.match(html, /<li>Item<\/li>/)
})

test('raw HTML stays escaped and unsafe image/link protocols stay blocked', () => {
  const html = renderMarkdown('<img src=x onerror=alert(1)>\n\n![Bad](javascript:alert)\n\n[Bad](javascript:alert)')
  assert.doesNotMatch(html, /<img\b|<a\b/)
  assert.match(html, /&lt;img/)
})

test('agent-written public contact links support phone, email, GitHub and LinkedIn', () => {
  const html = renderMarkdown('[Phone](tel:+34624179342) [Email](mailto:jeyker.salinas13@gmail.com) [GitHub](https://github.com/JeykerSalinas) [LinkedIn](https://www.linkedin.com/in/jeyker-salinas-608486158/)')
  assert.match(html, /href="tel:\+34624179342"/)
  assert.match(html, /href="mailto:jeyker.salinas13@gmail.com"/)
  assert.match(html, /href="https:\/\/github.com\/JeykerSalinas"/)
  assert.match(html, /href="https:\/\/www.linkedin.com\/in\/jeyker-salinas-608486158\/"/)
})

test('malformed card URLs do not break rendering or suppress unrelated images', () => {
  assert.match(renderMarkdown(markdownPhoto, ['http://['], baseUrl), /<img\b/)
})
