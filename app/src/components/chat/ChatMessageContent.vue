<script setup lang="ts">
import { computed } from 'vue'
import { isToolUIPart } from 'ai'
import { marked } from 'marked'

import CandidatePhotoCard from '@/components/chat/CandidatePhotoCard.vue'
import ToolApprovalCard from '@/components/chat/ToolApprovalCard.vue'
import { useLocale } from '@/composables/useLocale'
import type { ProfileMessage } from '@/types/chat'

defineProps<{ message: ProfileMessage }>()

const emit = defineEmits<{
  approve: [approvalId: string]
  reject: [approvalId: string]
}>()

const { text } = useLocale()

marked.setOptions({
  breaks: true,
  gfm: true,
})

const safeLinkProtocols = ['http:', 'https:', 'mailto:']

function escapeHtml(value: string) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function sanitizeUrl(href: string | null | undefined) {
  if (!href) return null

  try {
    const url = new URL(href, 'https://example.com')
    return safeLinkProtocols.includes(url.protocol) ? href : null
  } catch {
    return null
  }
}

const renderer = new marked.Renderer()

renderer.link = ({ href, title, tokens }) => {
  const safeHref = sanitizeUrl(href)
  const content = renderer.parser.parseInline(tokens)

  if (!safeHref) return content

  const titleAttr = title ? ` title="${escapeHtml(title)}"` : ''
  return `<a href="${escapeHtml(safeHref)}" target="_blank" rel="noreferrer noopener"${titleAttr}>${content}</a>`
}

renderer.image = ({ href, text: alt, title }) => {
  const safeHref = sanitizeUrl(href)
  if (!safeHref) return ''

  const titleAttr = title ? ` title="${escapeHtml(title)}"` : ''
  return `<img src="${escapeHtml(safeHref)}" alt="${escapeHtml(alt || '')}" loading="lazy"${titleAttr}>`
}

function renderMarkdown(value: string) {
  return marked.parse(escapeHtml(value), { async: false, renderer })
}
</script>

<template>
  <div class="min-w-0 space-y-3">
    <template v-for="(part, index) in message.parts" :key="`${message.id}-${index}`">
      <div
        v-if="part.type === 'text'"
        class="markdown-content text-[15px] leading-7 text-(--django-copy)"
        v-html="renderMarkdown(part.text)"
      />

      <CandidatePhotoCard
        v-else-if="part.type === 'data-candidate-photo'"
        :photo="part.data"
      />

      <div
        v-else-if="part.type === 'data-source'"
        class="inline-flex max-w-full items-center gap-2 rounded-full border border-(--django-border) bg-(--django-surface-soft) px-3 py-1.5 text-xs text-(--django-copy)"
      >
        <UIcon name="i-lucide-file-check-2" class="size-4 shrink-0 text-primary" />
        <span class="font-medium">{{ text.verifiedSource }}:</span>
        <span class="truncate">{{ part.data.path }}</span>
      </div>

      <div
        v-else-if="part.type === 'data-technologies'"
        class="rounded-[5px] border border-(--django-border) bg-(--django-surface) p-4"
      >
        <p class="mb-3 text-sm font-medium text-(--django-copy)">{{ part.data.label }}</p>
        <div class="flex flex-wrap gap-2">
          <UBadge
            v-for="technology in part.data.items"
            :key="technology"
            color="neutral"
            variant="soft"
          >
            {{ technology }}
          </UBadge>
        </div>
      </div>

      <UCard v-else-if="part.type === 'data-project'" class="max-w-lg bg-(--django-surface)">
        <p class="font-semibold text-(--django-heading)">{{ part.data.title }}</p>
        <p class="mt-2 text-sm text-(--django-copy)">{{ part.data.description }}</p>
        <div v-if="part.data.technologies?.length" class="mt-3 flex flex-wrap gap-2">
          <UBadge
            v-for="technology in part.data.technologies"
            :key="technology"
            color="primary"
            variant="subtle"
          >
            {{ technology }}
          </UBadge>
        </div>
        <UButton
          v-if="part.data.url"
          :to="part.data.url"
          target="_blank"
          variant="link"
          trailing-icon="i-lucide-arrow-up-right"
          class="mt-2 px-0"
          :label="text.viewProject"
        />
      </UCard>

      <ToolApprovalCard
        v-else-if="isToolUIPart(part) && part.state === 'approval-requested'"
        :approval-id="part.approval.id"
        :tool-name="part.type === 'dynamic-tool' ? part.toolName : part.type.replace('tool-', '')"
        :input="part.input"
        @approve="emit('approve', $event)"
        @reject="emit('reject', $event)"
      />
    </template>
  </div>
</template>

<style scoped>
.markdown-content :deep(*) {
  min-width: 0;
}

.markdown-content :deep(p),
.markdown-content :deep(ul),
.markdown-content :deep(ol),
.markdown-content :deep(pre),
.markdown-content :deep(blockquote),
.markdown-content :deep(table) {
  margin: 0.8rem 0;
}

.markdown-content :deep(:first-child) {
  margin-top: 0;
}

.markdown-content :deep(:last-child) {
  margin-bottom: 0;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4) {
  margin: 1.2rem 0 0.65rem;
  color: var(--django-heading);
  font-weight: 600;
  line-height: 1.25;
  text-wrap: balance;
}

.markdown-content :deep(h1) {
  font-size: 1.5rem;
}

.markdown-content :deep(h2) {
  font-size: 1.25rem;
}

.markdown-content :deep(h3) {
  font-size: 1.1rem;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  padding-left: 1.25rem;
}

.markdown-content :deep(ul) {
  list-style: disc;
}

.markdown-content :deep(ol) {
  list-style: decimal;
}

.markdown-content :deep(li + li) {
  margin-top: 0.35rem;
}

.markdown-content :deep(a) {
  color: var(--ui-primary);
  text-decoration: underline;
  text-decoration-thickness: 0.08em;
  text-underline-offset: 0.16em;
}

.markdown-content :deep(strong) {
  color: var(--django-heading);
  font-weight: 600;
}

.markdown-content :deep(code) {
  border: 1px solid var(--django-border);
  border-radius: 5px;
  background: var(--django-surface-soft);
  padding: 0.1rem 0.35rem;
  font-size: 0.9em;
}

.markdown-content :deep(pre) {
  overflow-x: auto;
  border: 1px solid var(--django-border);
  border-radius: 5px;
  background: var(--django-surface-soft);
  padding: 0.9rem 1rem;
}

.markdown-content :deep(pre code) {
  border: 0;
  background: transparent;
  padding: 0;
}

.markdown-content :deep(blockquote) {
  border-left: 3px solid var(--ui-primary);
  background: color-mix(in srgb, var(--django-surface-soft) 80%, transparent);
  padding: 0.75rem 1rem;
  color: var(--django-heading);
}

.markdown-content :deep(hr) {
  margin: 1rem 0;
  border: 0;
  border-top: 1px solid var(--django-border);
}

.markdown-content :deep(table) {
  display: block;
  max-width: 100%;
  overflow-x: auto;
  border-collapse: collapse;
}

.markdown-content :deep(th),
.markdown-content :deep(td) {
  border: 1px solid var(--django-border);
  padding: 0.6rem 0.8rem;
  text-align: left;
}

.markdown-content :deep(th) {
  background: var(--django-surface-soft);
  color: var(--django-heading);
  font-weight: 600;
}

.markdown-content :deep(img) {
  max-width: 100%;
  border-radius: 5px;
}
</style>
