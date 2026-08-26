<script setup lang="ts">
import { computed, onMounted, ref, useId } from 'vue'
import { useLocale } from '@/composables/useLocale'
import { contactPresentation } from '@/features/contact/copy'
import { validDraft, type createContactController } from '@/features/contact/flow'

const props = defineProps<{ controller: ReturnType<typeof createContactController> }>()
const { locale } = useLocale()
const state = props.controller.state
const copy = computed(() => contactPresentation(locale.value, state.mode))
const receiptCopy = computed(() => contactPresentation(locale.value,
  state.result === 'accepted' ? 'resend' : state.result === 'simulated' ? 'simulation' : state.mode))
const resultText = computed(() => state.result === null ? copy.value.usedNotice
  : receiptCopy.value.success)
const closed = ref(false)
const id = useId()
const canSubmit = computed(() => validDraft(state.draft) && !state.used && !state.loading && !state.submitting
  && state.ready && state.available
  && !['expired', 'storage'].includes(state.error))
const errorText = computed(() => copy.value.errors[state.error as keyof typeof copy.value.errors] || copy.value.errors.unavailable)
onMounted(() => { void props.controller.load() })
</script>

<template>
  <section class="contact-card" :aria-labelledby="`${id}-title`">
    <div class="flex items-start gap-3">
      <UIcon name="i-lucide-mail" class="mt-1 size-5 shrink-0 text-primary" />
      <div class="min-w-0">
        <h3 :id="`${id}-title`" class="font-semibold text-(--django-heading)">{{ copy.editorTitle }}</h3>
      </div>
    </div>
    <p v-if="state.loading" role="status" class="text-sm text-(--django-muted)">{{ copy.loading }}</p>

    <div v-if="state.used" role="status" class="contact-notice">
      <p class="font-medium">{{ resultText }}</p>
      <p class="mt-1 text-sm">{{ receiptCopy.limit }}</p>
    </div>

    <UButton v-else-if="closed" type="button" variant="soft" @click="closed = false">{{ copy.reopen }}</UButton>
    <form v-else :id="`${id}-compose`" class="contact-editor" @submit.prevent="controller.submit()">
      <p class="contact-notice text-sm">{{ copy.demo }}</p>
      <p v-if="state.ready && !state.available" role="alert">{{ copy.unavailable }}</p>
      <p v-if="state.locked" role="status" class="contact-notice text-sm">{{ copy.locked }}</p>
      <p class="text-sm text-(--django-muted)">{{ copy.to }}: <strong>Jeyker Salinas</strong></p>
      <fieldset :disabled="state.submitting || state.loading || state.locked" class="grid min-w-0 gap-4">
        <div class="grid gap-4 sm:grid-cols-2">
          <label :for="`${id}-name`">{{ copy.name }} <span class="contact-required">({{ copy.required }})</span>
            <input :id="`${id}-name`" v-model="state.draft.sender_name" name="sender_name" autocomplete="name" required maxlength="100" :placeholder="copy.namePlaceholder" />
          </label>
          <label :for="`${id}-email`">{{ copy.replyEmail }}
            <input :id="`${id}-email`" v-model="state.draft.reply_email" name="reply_email" autocomplete="email" type="email" maxlength="254" />
          </label>
        </div>
        <label :for="`${id}-subject`">{{ copy.subject }} <span class="contact-required">({{ copy.required }})</span>
          <input :id="`${id}-subject`" v-model="state.draft.subject" name="subject" required maxlength="160" :placeholder="copy.subjectPlaceholder" />
        </label>
        <label :for="`${id}-message`">{{ copy.message }} <span class="contact-required">({{ copy.required }})</span>
          <textarea :id="`${id}-message`" v-model="state.draft.message" name="message" required maxlength="4000" rows="6" :placeholder="copy.messagePlaceholder" :aria-describedby="`${id}-consent`" />
        </label>
      </fieldset>
      <p :id="`${id}-consent`" class="text-xs leading-5 text-(--django-muted)">{{ copy.consent }}</p>
      <div class="flex flex-wrap gap-2">
        <UButton type="submit" icon="i-lucide-send" :loading="state.submitting" :disabled="!canSubmit">{{ state.submitting ? copy.sending : copy.send }}</UButton>
        <UButton type="button" color="neutral" variant="ghost" :disabled="state.submitting" @click="closed = true">{{ copy.cancel }}</UButton>
      </div>
      <p class="text-xs text-(--django-muted)">{{ copy.session }}</p>
    </form>

    <div v-if="state.error && !state.used" role="alert" class="text-sm text-(--django-copy)">
      <p>{{ errorText }}</p>
      <UButton v-if="!state.loading && !state.submitting" type="button" variant="link" @click="controller.load(true)">{{ copy.retry }}</UButton>
    </div>
    <details class="text-sm text-(--django-muted)">
      <summary class="cursor-pointer text-primary">{{ copy.why }}</summary>
      <p class="mt-2 leading-6">{{ copy.explanation }}</p>
    </details>
  </section>
</template>

<style scoped>
.contact-card { display: grid; gap: 1rem; min-width: 0; padding: 1.25rem; border: 1px solid var(--django-border); border-left: 3px solid var(--ui-primary); border-radius: 5px; background: var(--django-surface-soft); }
.contact-editor { display: grid; gap: 1rem; }
.contact-editor label { display: block; min-width: 0; color: var(--django-heading); font-size: .875rem; }
.contact-editor input, .contact-editor textarea { display: block; width: 100%; min-width: 0; margin-top: .4rem; padding: .65rem .75rem; border: 1px solid var(--django-border); border-radius: 5px; background: var(--django-surface); color: var(--django-copy); font: inherit; }
.contact-editor textarea { resize: vertical; }
.contact-editor input:focus-visible, .contact-editor textarea:focus-visible { outline: 2px solid var(--ui-primary); outline-offset: 2px; }
.contact-editor fieldset:disabled { opacity: .65; }
.contact-required { color: var(--django-muted); font-size: .7rem; }
.contact-notice { border-radius: 5px; padding: .8rem; background: var(--django-surface); color: var(--django-copy); }
</style>
