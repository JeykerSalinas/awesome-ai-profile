<script setup lang="ts">
import { ref } from 'vue'
import type { StreamEvent } from '@/types/events'
import { isStreamEvent } from '@/types/events'

type AssistantImage = {
  src: string
  alt: string
}

const message = ref('')
const assistantMessage = ref('')
const assistantImages = ref<AssistantImage[]>([])
const errorMessage = ref('')
const isLoading = ref(false)
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

const sendMessage = async () => {
  if (!message.value.trim()) return

  assistantMessage.value = ''
  assistantImages.value = []
  errorMessage.value = ''
  isLoading.value = true
  try {
    const response = await fetch(`${apiBaseUrl}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: message.value,
      }),
    })

    if (!response.ok) {
      const detail = await extractErrorMessage(response)
      throw new Error(detail || `Request failed with status ${response.status}`)
    }

    if (!response.body) {
      throw new Error('No response body')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()

      buffer += decoder.decode(value || new Uint8Array(), { stream: !done })

      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed) continue

        const parsed: unknown = JSON.parse(trimmed)
        if (isStreamEvent(parsed)) {
          handleStreamEvent(parsed)
        }
      }

      if (done) break
    }

    if (buffer.trim()) {
      const parsed: unknown = JSON.parse(buffer)
      if (isStreamEvent(parsed)) {
        handleStreamEvent(parsed)
      }
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unexpected error'
  } finally {
    isLoading.value = false
  }
}

const extractErrorMessage = async (response: Response) => {
  try {
    const payload: unknown = await response.json()
    if (
      payload &&
      typeof payload === 'object' &&
      'detail' in payload &&
      typeof payload.detail === 'string'
    ) {
      return payload.detail
    }
  } catch {
    return ''
  }

  return ''
}

const handleStreamEvent = (event: StreamEvent) => {
  if (event.event === 'message_delta') {
    assistantMessage.value += event.data.text
    return
  }

  if (event.event === 'error') {
    throw new Error(event.data.message)
  }

  if (event.event === 'image') {
    assistantImages.value.push(event.data)
  }
}
</script>

<template>
  <main class="container py-5">
    <h1 class="mb-4">Awesome AI Profile</h1>

    <div class="mb-3">
      <label class="form-label">Ask something</label>

      <input
        v-model="message"
        class="form-control"
        placeholder="Why should we hire Jeyker?"
        @keyup.enter="sendMessage"
      />
    </div>

    <button
      class="btn btn-primary"
      :disabled="isLoading"
      @click="sendMessage"
    >
      {{ isLoading ? 'Thinking...' : 'Send' }}
    </button>

    <div
      v-if="errorMessage"
      class="alert alert-danger mt-3"
      role="alert"
    >
      {{ errorMessage }}
    </div>

    <div
      v-if="assistantMessage || assistantImages.length"
      class="mt-4 p-3 border rounded"
    >
      <div v-if="assistantMessage">
        {{ assistantMessage }}
      </div>

      <img
        v-for="(image, index) in assistantImages"
        :key="`${image.src}-${index}`"
        :src="image.src"
        :alt="image.alt"
        class="img-fluid rounded mt-3"
      />
    </div>
  </main>
</template>
