<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'
import { useLocale } from '@/composables/useLocale'
import {
  chapters,
  chapterIndex,
  sourceUrl,
  storyCopy,
} from '@/features/tour/story'
import { placeCard, type Rect } from '@/features/tour/placement'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{
  close: []
  complete: []
  prepareQuestion: [question: string]
}>()
const { locale } = useLocale()
const copy = computed(() => storyCopy[locale.value])
const index = ref(0)
const chapter = computed(() => chapters[chapterIndex(index.value)]!)
const content = computed(() => chapter.value[locale.value])
const isLast = computed(() => index.value === chapters.length - 1)
const dialog = ref<HTMLDialogElement | null>(null)
const card = ref<HTMLElement | null>(null)
const heading = ref<HTMLElement | null>(null)
const paused = ref(false)
const target = ref<Rect | null>(null)
const position = ref({ left: 16, top: 16 })
const maskId = `tour-mask-${useId()}`
let opener: HTMLElement | null = null
let observer: ResizeObserver | undefined
let frame = 0
let oldOverflow = ''
let active = false
let scrollPositions: Array<{ element: Element; top: number; left: number }> = []

function measure() {
  if (!props.open || !card.value) return
  const element = document.querySelector<HTMLElement>(
    `[data-tour="${chapter.value.target}"]`,
  )
  const bounds = element?.getBoundingClientRect()
  const width = document.documentElement.clientWidth
  const height = window.innerHeight
  // A removed/offscreen anchor degrades to a centered card, never a broken tour.
  target.value =
    bounds &&
    bounds.width > 0 &&
    bounds.height > 0 &&
    bounds.bottom > 0 &&
    bounds.top < height
      ? {
          left: Math.max(8, bounds.left - 8),
          top: Math.max(8, bounds.top - 8),
          width: Math.max(
            0,
            Math.min(width - 8, bounds.right + 8) -
              Math.max(8, bounds.left - 8),
          ),
          height: Math.max(
            0,
            Math.min(height - 8, bounds.bottom + 8) -
              Math.max(8, bounds.top - 8),
          ),
        }
      : null
  position.value = placeCard(
    { width, height },
    card.value.getBoundingClientRect(),
    target.value,
  )
}

function scheduleMeasure() {
  cancelAnimationFrame(frame)
  frame = requestAnimationFrame(measure)
}

async function revealChapter() {
  await nextTick()
  if (!props.open) return
  document
    .querySelector<HTMLElement>(`[data-tour="${chapter.value.target}"]`)
    ?.scrollIntoView({
      behavior: 'instant',
      block: 'center',
      inline: 'nearest',
    })
  card.value
    ?.querySelector('.tour-scroll')
    ?.scrollTo({ top: 0, behavior: 'instant' })
  measure()
  heading.value?.focus({ preventScroll: true })
}

function goTo(value: number) {
  index.value = chapterIndex(value)
}

function onKeydown(event: KeyboardEvent) {
  // Do not steal browser/assistive shortcuts or native control navigation.
  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return
  if (
    (event.target as HTMLElement).closest(
      'input, textarea, select, [contenteditable="true"]',
    )
  )
    return
  if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
    event.preventDefault()
    goTo(index.value + (event.key === 'ArrowRight' ? 1 : -1))
  }
}

function cleanup() {
  if (!active) return
  active = false
  cancelAnimationFrame(frame)
  observer?.disconnect()
  window.removeEventListener('resize', scheduleMeasure)
  document.removeEventListener('scroll', scheduleMeasure, true)
  window.visualViewport?.removeEventListener('resize', scheduleMeasure)
  document.body.style.overflow = oldOverflow
  dialog.value?.close()
  for (const { element, top, left } of scrollPositions)
    element.scrollTo({ top, left, behavior: 'instant' })
  scrollPositions = []
  if (opener?.isConnected) opener.focus({ preventScroll: true })
}

watch(
  () => props.open,
  async (open) => {
    if (!open) return cleanup()
    await nextTick()
    if (!props.open || !dialog.value) return
    opener =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null
    scrollPositions = Array.from(document.querySelectorAll('main, main *'))
      .filter((element) => element.scrollHeight > element.clientHeight)
      .map((element) => ({
        element,
        top: element.scrollTop,
        left: element.scrollLeft,
      }))
    if (document.scrollingElement)
      scrollPositions.push({
        element: document.scrollingElement,
        top: document.scrollingElement.scrollTop,
        left: document.scrollingElement.scrollLeft,
      })
    index.value = 0
    oldOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    active = true
    dialog.value.showModal()
    observer = new ResizeObserver(scheduleMeasure)
    if (card.value) observer.observe(card.value)
    document
      .querySelectorAll('[data-tour]')
      .forEach((element) => observer?.observe(element))
    window.addEventListener('resize', scheduleMeasure)
    document.addEventListener('scroll', scheduleMeasure, true)
    window.visualViewport?.addEventListener('resize', scheduleMeasure)
    await revealChapter()
  },
  { immediate: true },
)

watch(index, revealChapter)
watch(locale, () => nextTick(scheduleMeasure))
onBeforeUnmount(cleanup)
</script>

<template>
  <Teleport to="body">
    <dialog
      ref="dialog"
      class="tech-tour"
      :class="{ 'tech-tour--paused': paused }"
      aria-labelledby="tour-heading"
      aria-describedby="tour-description"
      @cancel.prevent="emit('close')"
      @keydown="onKeydown"
    >
      <template v-if="open">
        <svg class="tour-shade" width="100%" height="100%" aria-hidden="true">
          <defs>
            <mask :id="maskId">
              <rect width="100%" height="100%" fill="white" />
              <rect
                v-if="target"
                :x="target.left"
                :y="target.top"
                :width="target.width"
                :height="target.height"
                rx="16"
                fill="black"
                class="tour-cutout"
              />
            </mask>
          </defs>
          <rect
            width="100%"
            height="100%"
            fill="rgba(20, 5, 5, .76)"
            :mask="`url(#${maskId})`"
          />
        </svg>
        <div
          v-if="target"
          class="tour-spotlight"
          :style="{
            left: `${target.left}px`,
            top: `${target.top}px`,
            width: `${target.width}px`,
            height: `${target.height}px`,
          }"
          aria-hidden="true"
        />

        <section
          ref="card"
          class="tour-card"
          :style="{ left: `${position.left}px`, top: `${position.top}px` }"
        >
          <header class="tour-topbar">
            <span class="tour-eyebrow"
              ><span class="tour-status-dot" />{{ copy.eyebrow }}</span
            >
            <div class="tour-utilities">
              <button
                type="button"
                class="tour-icon-button"
                :aria-label="paused ? copy.resumeMotion : copy.motion"
                :title="paused ? copy.resumeMotion : copy.motion"
                :aria-pressed="paused"
                @click="paused = !paused"
              >
                <UIcon :name="paused ? 'i-lucide-play' : 'i-lucide-pause'" />
              </button>
              <button
                type="button"
                class="tour-icon-button"
                :aria-label="copy.close"
                :title="copy.close"
                @click="emit('close')"
              >
                <UIcon name="i-lucide-x" />
              </button>
            </div>
          </header>

          <nav class="tour-progress" :aria-label="copy.navigation">
            <button
              v-for="(item, itemIndex) in chapters"
              :key="item.id"
              type="button"
              :aria-label="`${copy.chapter} ${itemIndex + 1}: ${item[locale].label}`"
              :aria-current="index === itemIndex ? 'step' : undefined"
              :title="item[locale].label"
              :class="{
                'is-complete': itemIndex < index,
                'is-current': itemIndex === index,
              }"
              @click="goTo(itemIndex)"
            >
              <span />
            </button>
          </nav>

          <div class="tour-scroll">
            <div :key="chapter.id" class="tour-chapter">
              <div class="tour-chapter-label">
                <span
                  >{{ String(index + 1).padStart(2, '0') }} /
                  {{ String(chapters.length).padStart(2, '0') }}</span
                ><span>{{ content.label }}</span>
              </div>
              <h2 id="tour-heading" ref="heading" tabindex="-1">
                {{ content.title }}
              </h2>
              <p id="tour-description" class="tour-description">
                {{ content.description }}
              </p>

              <figure class="tour-flow" :class="`tour-flow--${chapter.id}`">
                <div class="tour-flow-header">
                  <UIcon :name="chapter.icon" /><span>{{
                    chapter.technologies[0]
                  }}</span
                  ><span class="tour-flow-signal" aria-hidden="true"
                    ><i /><i /><i
                  /></span>
                </div>
                <ol class="tour-flow-nodes">
                  <li
                    v-for="(node, nodeIndex) in content.flow"
                    :key="node"
                    :style="{ '--node': nodeIndex }"
                  >
                    <span class="tour-node-number">{{ nodeIndex + 1 }}</span
                    ><span>{{ node }}</span>
                  </li>
                </ol>
                <figcaption>{{ copy.diagram }}</figcaption>
              </figure>

              <div class="tour-detail">
                <h3>{{ copy.mechanism }}</h3>
                <p>{{ content.detail }}</p>
              </div>
              <ul class="tour-tags" aria-label="Stack">
                <li
                  v-for="technology in chapter.technologies"
                  :key="technology"
                >
                  {{ technology }}
                </li>
              </ul>
              <a
                class="tour-source"
                :href="sourceUrl(chapter.source)"
                target="_blank"
                rel="noopener noreferrer"
                ><UIcon name="i-lucide-code-xml" />{{ copy.code
                }}<UIcon name="i-lucide-arrow-up-right"
              /></a>
              <button
                v-if="isLast"
                type="button"
                class="tour-try"
                @click="emit('prepareQuestion', copy.prompt)"
              >
                <UIcon name="i-lucide-message-circle" />{{ copy.tryIt
                }}<UIcon name="i-lucide-arrow-up-right" />
              </button>
            </div>
          </div>

          <footer class="tour-footer">
            <div class="tour-actions">
              <button
                type="button"
                class="tour-back"
                :disabled="index === 0"
                @click="goTo(index - 1)"
              >
                <UIcon name="i-lucide-arrow-left" />{{ copy.previous }}
              </button>
              <button
                type="button"
                class="tour-next"
                @click="isLast ? emit('complete') : goTo(index + 1)"
              >
                {{ isLast ? copy.finish : copy.next
                }}<UIcon
                  :name="isLast ? 'i-lucide-check' : 'i-lucide-arrow-right'"
                />
              </button>
            </div>
            <p class="tour-keyboard">{{ copy.keyboard }}</p>
          </footer>
        </section>
      </template>
    </dialog>
  </Teleport>
</template>

<style scoped>
.tech-tour {
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100dvh;
  max-width: none;
  max-height: none;
  padding: 0;
  border: 0;
  margin: 0;
  overflow: hidden;
  background: transparent;
  color: var(--django-copy);
}
.tech-tour::backdrop {
  background: transparent;
}
.tour-shade {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.tour-cutout {
  transition:
    x 420ms ease,
    y 420ms ease,
    width 420ms ease,
    height 420ms ease;
}
.tour-spotlight {
  position: absolute;
  pointer-events: none;
  border: 1px solid #ffba91;
  border-radius: 16px;
  box-shadow:
    0 0 0 4px rgb(229 109 88 / 16%),
    0 0 32px rgb(229 109 88 / 24%);
  transition:
    left 420ms ease,
    top 420ms ease,
    width 420ms ease,
    height 420ms ease;
}
.tour-card {
  position: absolute;
  display: flex;
  flex-direction: column;
  width: min(450px, calc(100vw - 32px));
  max-height: calc(100dvh - 32px);
  overflow: hidden;
  border: 1px solid var(--django-border);
  border-radius: 22px;
  background: var(--django-surface);
  box-shadow: 0 28px 90px rgb(0 0 0 / 35%);
  transition:
    left 350ms ease,
    top 350ms ease;
}
.tour-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 20px 4px;
}
.tour-eyebrow {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 0.16em;
  color: var(--django-heading);
}
.tour-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-django-terracotta);
  box-shadow: 0 0 0 4px rgb(229 109 88 / 12%);
}
.tour-utilities {
  display: flex;
  gap: 2px;
}
.tour-icon-button {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  color: var(--django-muted);
  cursor: pointer;
}
.tour-icon-button:hover {
  background: var(--django-surface-soft);
  color: var(--django-heading);
}
.tour-progress {
  display: flex;
  gap: 5px;
  padding: 0 24px;
}
.tour-progress button {
  flex: 1;
  padding: 12px 0;
  cursor: pointer;
}
.tour-progress span {
  display: block;
  height: 3px;
  border-radius: 8px;
  background: var(--django-border);
  transition: background 200ms;
}
.tour-progress .is-complete span {
  background: var(--color-django-terracotta);
}
.tour-progress .is-current span {
  background: var(--ui-primary);
  box-shadow: 0 0 8px rgb(235 8 8 / 20%);
}
.tour-scroll {
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 10px 26px 20px;
}
.tour-chapter {
  animation: chapter-in 360ms cubic-bezier(0.2, 0.7, 0.2, 1) both;
}
.tour-chapter-label {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
  font-size: 11px;
  font-weight: 650;
  color: var(--django-muted);
}
.tour-chapter-label > :first-child {
  font-variant-numeric: tabular-nums;
  font-family: ui-monospace, monospace;
  letter-spacing: 0.06em;
}
h2 {
  color: var(--django-heading);
  font-size: clamp(25px, 4vw, 32px);
  font-weight: 650;
  letter-spacing: -0.045em;
  line-height: 1.13;
  text-wrap: balance;
  margin: 0;
}
h2:focus {
  outline: none;
}
.tour-description {
  font-size: 14px;
  line-height: 1.7;
  margin-top: 14px;
  text-wrap: pretty;
}
.tour-flow {
  position: relative;
  margin: 20px 0;
  overflow: hidden;
  border: 1px solid rgb(255 255 255 / 12%);
  border-radius: 14px;
  background: #320808;
  color: #fbefce;
  padding: 16px;
}
.tour-flow::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(
    ellipse at 90% 0%,
    rgb(229 109 88 / 22%),
    transparent 65%
  );
}
.tour-flow-header {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: ui-monospace, monospace;
  font-size: 10px;
  letter-spacing: 0.02em;
  color: #ccb68c;
}
.tour-flow-header > :first-child {
  width: 16px;
  height: 16px;
  color: #e56d58;
}
.tour-flow-signal {
  margin-left: auto;
  display: flex;
  align-items: end;
  gap: 3px;
  height: 14px;
}
.tour-flow-signal i {
  width: 3px;
  height: 9px;
  border-radius: 3px;
  background: #e56d58;
  animation: signal 1.8s ease-in-out 2;
}
.tour-flow-signal i:nth-child(2) {
  height: 14px;
  animation-delay: 0.2s;
}
.tour-flow-signal i:nth-child(3) {
  height: 6px;
  animation-delay: 0.4s;
}
.tour-flow-nodes {
  position: relative;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin: 20px 0 16px;
  padding: 0;
  list-style: none;
}
.tour-flow-nodes::before {
  content: '';
  position: absolute;
  height: 1px;
  background: #75312a;
  top: 14px;
  left: 15%;
  right: 15%;
}
.tour-flow-nodes::after {
  content: '';
  position: absolute;
  height: 2px;
  width: 18%;
  background: linear-gradient(90deg, transparent, #ffba91, transparent);
  top: 14px;
  left: 15%;
  animation: packet 2.4s ease-in-out 2;
}
.tour-flow-nodes li {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  text-align: center;
  font-size: 10px;
  line-height: 1.4;
}
.tour-node-number {
  display: grid;
  place-items: center;
  width: 29px;
  height: 29px;
  border-radius: 9px;
  background: #571614;
  border: 1px solid #a64e40;
  color: #fbefce;
  font-family: ui-monospace, monospace;
  animation: node-glow 2.4s ease-in-out 2;
  animation-delay: calc(var(--node) * 0.4s);
}
figcaption {
  position: relative;
  font-size: 9px;
  line-height: 1.5;
  color: #ccb68c;
  text-align: center;
}
.tour-detail h3 {
  color: var(--django-heading);
  font-size: 11px;
  font-weight: 750;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  margin: 0 0 7px;
}
.tour-detail p {
  font-size: 12px;
  line-height: 1.8;
  margin: 0;
}
.tour-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  list-style: none;
  padding: 0;
  margin: 15px 0 12px;
}
.tour-tags li {
  border: 1px solid var(--django-border);
  border-radius: 5px;
  padding: 4px 7px;
  font-size: 10px;
  font-family: ui-monospace, monospace;
}
.tour-source {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 32px;
  font-size: 12px;
  font-weight: 600;
  color: var(--django-heading);
  text-decoration: none;
}
.tour-source:hover {
  text-decoration: underline;
  text-underline-offset: 4px;
}
.tour-source > :last-child {
  color: var(--django-muted);
}
.tour-try {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 12px;
  width: 100%;
  padding: 12px;
  border: 1px dashed var(--django-border);
  border-radius: 9px;
  font-size: 12px;
  cursor: pointer;
}
.tour-try:hover {
  background: var(--django-surface-soft);
}
.tour-footer {
  flex-shrink: 0;
  padding: 16px 24px 12px;
  border-top: 1px solid var(--django-border);
}
.tour-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.tour-actions button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 14px;
  border-radius: 9px;
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
}
.tour-back {
  color: var(--django-copy);
}
.tour-back:hover:not(:disabled) {
  background: var(--django-surface-soft);
}
.tour-back:disabled {
  opacity: 0.35;
  cursor: default;
}
.tour-next {
  background: #b82016;
  color: #fff8e8;
  box-shadow: 0 4px 12px rgb(184 32 22 / 16%);
}
.tour-next:hover {
  background: #991c14;
}
.tour-keyboard {
  margin: 12px 0 0;
  text-align: center;
  font-size: 10px;
  color: var(--django-muted);
}
button:focus-visible,
a:focus-visible {
  outline: 2px solid var(--color-django-terracotta);
  outline-offset: 3px;
}
.tech-tour--paused *,
.tech-tour--paused *::after {
  animation-play-state: paused !important;
  transition: none !important;
}
.tech-tour--paused .tour-chapter {
  animation: none !important;
}
@keyframes chapter-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
@keyframes packet {
  0% {
    transform: translateX(0);
    opacity: 0;
  }
  20% {
    opacity: 1;
  }
  100% {
    transform: translateX(300%);
    opacity: 0;
  }
}
@keyframes node-glow {
  0%,
  100% {
    border-color: #a64e40;
  }
  45% {
    border-color: #ffba91;
    box-shadow: 0 0 16px rgb(229 109 88 / 24%);
  }
}
@keyframes signal {
  50% {
    transform: scaleY(0.4);
  }
}
@media (max-width: 639px) {
  .tour-card {
    border-radius: 18px;
  }
  .tour-scroll {
    padding: 8px 20px 16px;
  }
  .tour-topbar {
    padding: 10px 14px 0;
  }
  .tour-footer {
    padding: 12px 16px;
  }
  .tour-keyboard {
    display: none;
  }
  .tour-flow {
    margin: 16px 0;
  }
}
@media (max-height: 650px) {
  .tour-flow {
    margin: 12px 0;
    padding: 12px;
  }
  .tour-description {
    margin-top: 10px;
  }
}
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation: none !important;
    transition: none !important;
    scroll-behavior: auto !important;
  }
}
</style>
