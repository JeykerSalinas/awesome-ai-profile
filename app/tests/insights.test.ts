import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { test } from 'node:test'
import { readUIMessageStream, type UIMessageChunk } from 'ai'
import { activityStatus, firstFeatureMessages, messageActivities, messageFeatures } from '../src/features/insights/activity.ts'
import { features, featureSourceUrl, insightCopy, toolFeatures, type FeatureId } from '../src/features/insights/catalog.ts'
import type { AgentActivityData, ProfileMessage } from '../src/types/chat.ts'

function activity(id: string, tool_name: string, status: AgentActivityData['status'] = 'completed'): ProfileMessage['parts'][number] {
  return { type: 'data-agent-activity', id, data: { id, kind: 'tool', tool_name, status } }
}
function message(id: string, parts: ProfileMessage['parts']): ProfileMessage {
  return { id, role: 'assistant', parts }
}

test('running and failed tools do not claim a successful RAG lookup', () => {
  for (const status of ['running', 'error', 'interrupted'] as const)
    assert.deepEqual(messageFeatures(message('m', [activity('a', 'search_documents', status)])), ['tools'])
  assert.deepEqual(messageFeatures(message('m', [activity('a', 'search_documents')])), ['tools', 'rag'])
})

test('actual tool names map to distinct explanations', () => {
  for (const [name, feature] of Object.entries(toolFeatures))
    assert.deepEqual(messageFeatures(message('m', [activity('a', name)])), ['tools', feature])
  assert.deepEqual(messageFeatures(message('m', [activity('a', 'unknown_tool')])), [])
})

test('text mentioning RAG does not trigger a discovery', () => {
  assert.deepEqual(messageFeatures(message('m', [{ type: 'text', text: 'I searched the RAG and showed a photo.' }])), [])
})

test('features appear once per conversation but remain attached to their original message', () => {
  const first = message('first', [activity('a', 'search_documents'), activity('b', 'search_documents')])
  const second = message('second', [activity('c', 'search_documents'), activity('d', 'get_candidate_photo')])
  assert.deepEqual([...firstFeatureMessages([first, second])], [['tools', 'first'], ['rag', 'first'], ['photo', 'second']])
  assert.equal(firstFeatureMessages([second]).get('rag'), 'second')
  assert.equal(firstFeatureMessages([]).size, 0)
})

test('typed parts discover uploads, sources, photos and observed streaming', () => {
  assert.deepEqual(messageFeatures(message('m', [
    { type: 'data-user-document', data: { filename: 'offer.pdf' } },
    { type: 'data-source', data: { path: 'knowledge/profile.json' } },
    { type: 'data-candidate-photo', data: { src: '/jeyker.jpg', alt: 'Jeyker' } },
    { type: 'data-feature-used', data: { feature: 'streaming' } },
  ])), ['uploads', 'sources', 'photo', 'streaming'])
})

test('activity updates deduplicate by run id while preserving separate invocations', () => {
  const entries = messageActivities(message('m', [
    activity('a', 'search_documents', 'running'), activity('b', 'search_documents'), activity('a', 'search_documents'),
  ]))
  assert.equal(entries.length, 2)
  assert.equal(entries[0]?.status, 'completed')
  assert.equal(entries[0]?.id, 'a')
})

test('stopped and failed streams never leave a historical spinner', () => {
  const running: AgentActivityData = { id: 'a', kind: 'model', status: 'running' }
  assert.equal(activityStatus(running, true), 'running')
  assert.equal(activityStatus(running, false), 'interrupted')
  assert.equal(activityStatus({ ...running, status: 'error' }, false), 'error')
  assert.equal(activityStatus({ ...running, status: 'completed' }, false), 'completed')
})

test('all copy is bilingual and references real project code', () => {
  assert.deepEqual(Object.keys(insightCopy.en), Object.keys(insightCopy.es))
  for (const id of Object.keys(features) as FeatureId[]) {
    const feature = features[id]
    assert.deepEqual(Object.keys(feature.en), Object.keys(feature.es))
    for (const locale of ['es', 'en'] as const)
      for (const value of Object.values(feature[locale])) assert.ok(value.length > 0)
    assert.ok(existsSync(new URL(`../../${feature.source}`, import.meta.url)))
    assert.equal(new URL(featureSourceUrl(id)).hostname, 'github.com')
  }
  assert.ok(features.rag.es.how.includes('ChromaDB'))
  assert.ok(features.experience.es.caveat.includes('no embeddings'))
})

test('explanations stay local and MainView only composes the feature', () => {
  const component = readFileSync(new URL('../src/components/chat/FeatureExplainer.vue', import.meta.url), 'utf8')
  for (const forbidden of ['fetch(', 'sendMessage(', 'v-html', 'localStorage']) assert.ok(!component.includes(forbidden))
  for (const required of ['aria-expanded', 'aria-controls', 'role="region"', 'type="button"']) assert.ok(component.includes(required))
  const view = readFileSync(new URL('../src/views/MainView.vue', import.meta.url), 'utf8')
  assert.ok(view.includes('provideFeatureDiscovery(messages)'))
  assert.ok(!view.includes('ChromaDB'))
})

test('AI SDK reconciles real custom stream parts with stable IDs', async () => {
  const events: UIMessageChunk[] = [
    { type: 'start', messageId: 'm' }, { type: 'start-step' },
    { type: 'data-agent-activity', id: 'activity-a', data: { id: 'a', kind: 'tool', tool_name: 'search_documents', status: 'running' } },
    { type: 'text-start', id: 'text-a' }, { type: 'text-delta', id: 'text-a', delta: 'Hello' },
    { type: 'data-agent-activity', id: 'activity-a', data: { id: 'a', kind: 'tool', tool_name: 'search_documents', status: 'completed', result_count: 0, duration_ms: 12 } },
    { type: 'data-feature-used', id: 'feature-streaming', data: { feature: 'streaming' } },
    { type: 'text-end', id: 'text-a' }, { type: 'finish-step' }, { type: 'finish', finishReason: 'stop' },
  ]
  let latest: ProfileMessage | undefined
  const stream = new ReadableStream<UIMessageChunk>({ start(controller) { for (const event of events) controller.enqueue(event); controller.close() } })
  for await (const snapshot of readUIMessageStream<ProfileMessage>({ stream })) latest = snapshot
  assert.ok(latest)
  assert.equal(messageActivities(latest).length, 1)
  assert.equal(messageActivities(latest)[0]?.status, 'completed')
  assert.equal(messageActivities(latest)[0]?.result_count, 0)
  assert.deepEqual(messageFeatures(latest), ['tools', 'rag', 'streaming'])
})
