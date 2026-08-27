<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";

import { useLocale } from "@/composables/useLocale";
import FeatureExplainer from "@/components/chat/FeatureExplainer.vue";
import {
  buildLiveWebSocketUrl,
  LIVE_OUTPUT_SAMPLE_RATE,
  pcm16ToFloat32,
  resampleToPcm16,
} from "@/utils/liveAudio";

type LiveState = "idle" | "connecting" | "listening" | "speaking" | "error";
type LiveControlMessage = {
  type: "ready" | "error" | "interrupted" | "ending" | "turn_complete" | "transcript" | "tool";
  message?: string;
  code?: string;
  detail?: string;
  retryable?: boolean;
  stage?: string;
  name?: string;
  status?: "running" | "completed";
  role?: "user" | "assistant";
  text?: string;
  result?: string;
};

const props = defineProps<{
  apiBaseUrl: string;
  documentIds?: string[];
  history?: Array<{ role: "user" | "assistant"; content: string }>;
}>();

const { locale, text } = useLocale();
const state = ref<LiveState>("idle");
const errorMessage = ref("");
const errorCode = ref("");
const errorDetail = ref("");
const errorStage = ref("");
const errorRetryable = ref(false);
const activeTool = ref("");
const transcript = ref("");
const photoUrl = ref("");
let socket: WebSocket | null = null;
let microphoneStream: MediaStream | null = null;
let audioContext: AudioContext | null = null;
let microphoneSource: MediaStreamAudioSourceNode | null = null;
let captureProcessor: ScriptProcessorNode | null = null;
let silentGain: GainNode | null = null;
let nextPlaybackTime = 0;
const playbackSources = new Set<AudioBufferSourceNode>();

const active = computed(() => state.value !== "idle" && state.value !== "error");
const panelVisible = computed(() => state.value !== "idle" || Boolean(errorMessage.value));
const statusLabel = computed(() => {
  if (activeTool.value) return text.value.liveUsingTool.replace("{tool}", activeTool.value);
  if (state.value === "connecting") return text.value.liveConnecting;
  if (state.value === "speaking") return text.value.liveSpeaking;
  if (state.value === "error") return errorMessage.value || text.value.liveError;
  return text.value.liveListening;
});

function stopPlayback() {
  for (const source of playbackSources) {
    try {
      source.stop();
    } catch {
      // The source may already have finished.
    }
  }
  playbackSources.clear();
  nextPlaybackTime = audioContext?.currentTime ?? 0;
}

function playAudio(buffer: ArrayBuffer) {
  if (!audioContext) return;
  const samples = pcm16ToFloat32(buffer);
  const audioBuffer = audioContext.createBuffer(
    1,
    samples.length,
    LIVE_OUTPUT_SAMPLE_RATE
  );
  audioBuffer.copyToChannel(samples, 0);
  const source = audioContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(audioContext.destination);
  const startAt = Math.max(audioContext.currentTime, nextPlaybackTime);
  nextPlaybackTime = startAt + audioBuffer.duration;
  playbackSources.add(source);
  source.onended = () => {
    playbackSources.delete(source);
    if (playbackSources.size === 0 && state.value === "speaking") {
      state.value = "listening";
    }
  };
  state.value = "speaking";
  source.start(startAt);
}

function startMicrophoneCapture() {
  if (!audioContext || !microphoneStream || captureProcessor) return;
  microphoneSource = audioContext.createMediaStreamSource(microphoneStream);
  captureProcessor = audioContext.createScriptProcessor(4096, 1, 1);
  silentGain = audioContext.createGain();
  silentGain.gain.value = 0;
  captureProcessor.onaudioprocess = (event) => {
    if (socket?.readyState !== WebSocket.OPEN || state.value === "connecting") return;
    const channel = event.inputBuffer.getChannelData(0);
    socket.send(resampleToPcm16(channel, event.inputBuffer.sampleRate));
  };
  microphoneSource.connect(captureProcessor);
  captureProcessor.connect(silentGain);
  silentGain.connect(audioContext.destination);
}

function handleControlMessage(message: LiveControlMessage) {
  if (message.type === "ready") {
    state.value = "listening";
    startMicrophoneCapture();
    return;
  }
  if (message.type === "interrupted") {
    stopPlayback();
    state.value = "listening";
    return;
  }
  if (message.type === "tool") {
    activeTool.value = message.status === "running" ? message.name || "tool" : "";
    if (
      message.status === "completed" &&
      message.name === "get_candidate_photo" &&
      message.result
    ) {
      photoUrl.value = message.result;
    }
    return;
  }
  if (message.type === "transcript" && message.text) {
    transcript.value = message.text;
    return;
  }
  if (message.type === "error") {
    errorMessage.value = message.message || text.value.liveError;
    errorCode.value = message.code || "live_session_failed";
    errorDetail.value = message.detail || "";
    errorStage.value = message.stage || "";
    errorRetryable.value = Boolean(message.retryable);
    state.value = "error";
    return;
  }
  if (message.type === "ending") {
    errorMessage.value ||= text.value.liveSessionEnding;
    errorCode.value ||= "session_ending";
    errorRetryable.value = true;
    state.value = "error";
  }
}

async function startConversation() {
  if (active.value) return;
  errorMessage.value = "";
  errorCode.value = "";
  errorDetail.value = "";
  errorStage.value = "";
  errorRetryable.value = false;
  transcript.value = "";
  photoUrl.value = "";
  state.value = "connecting";

  try {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error(text.value.liveMicrophoneUnavailable);
    }
    microphoneStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    audioContext = new AudioContext();
    await audioContext.resume();
    nextPlaybackTime = audioContext.currentTime;

    socket = new WebSocket(buildLiveWebSocketUrl(props.apiBaseUrl));
    socket.binaryType = "arraybuffer";
    socket.onopen = () => {
      socket?.send(
        JSON.stringify({
          type: "start",
          locale: locale.value,
          documents: props.documentIds || [],
          history: props.history || [],
        })
      );
    };
    socket.onmessage = (event) => {
      if (typeof event.data === "string") {
        handleControlMessage(JSON.parse(event.data) as LiveControlMessage);
      } else {
        playAudio(event.data as ArrayBuffer);
      }
    };
    socket.onerror = () => {
      errorMessage.value = text.value.liveConnectionError;
      errorCode.value = "browser_websocket_error";
      errorStage.value = state.value === "connecting" ? "connecting" : "streaming";
      errorRetryable.value = true;
      state.value = "error";
    };
    socket.onclose = () => {
      if (state.value !== "error") state.value = "idle";
      cleanupMedia();
    };
  } catch (cause) {
    errorMessage.value =
      cause instanceof Error ? cause.message : text.value.liveError;
    state.value = "error";
    cleanupMedia();
  }
}

function cleanupMedia() {
  captureProcessor?.disconnect();
  microphoneSource?.disconnect();
  silentGain?.disconnect();
  captureProcessor = null;
  microphoneSource = null;
  silentGain = null;
  microphoneStream?.getTracks().forEach((track) => track.stop());
  microphoneStream = null;
  stopPlayback();
  if (audioContext) void audioContext.close();
  audioContext = null;
}

function stopConversation(clearError = true) {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: "stop" }));
  }
  socket?.close();
  socket = null;
  cleanupMedia();
  activeTool.value = "";
  transcript.value = "";
  photoUrl.value = "";
  state.value = "idle";
  if (clearError) {
    errorMessage.value = "";
    errorCode.value = "";
    errorDetail.value = "";
    errorStage.value = "";
    errorRetryable.value = false;
  }
}

function retryConversation() {
  stopConversation();
  void startConversation();
}

function toggleConversation() {
  if (active.value) stopConversation();
  else void startConversation();
}

onBeforeUnmount(() => stopConversation());
</script>

<template>
  <UButton
    icon="i-lucide-mic"
    type="button"
    :aria-label="text.liveMode"
    :title="text.liveMode"
    :color="active ? 'primary' : 'neutral'"
    :variant="active ? 'soft' : 'ghost'"
    size="sm"
    @click="toggleConversation"
  />

  <Teleport to="body">
    <Transition name="live-panel">
      <aside
        v-if="panelVisible"
        class="live-conversation-panel"
        :role="state === 'error' ? 'alert' : 'status'"
        aria-live="polite"
      >
        <div class="live-orb" :class="`live-orb--${state}`" aria-hidden="true">
          <span v-for="bar in 5" :key="bar" />
        </div>
        <div class="min-w-0 flex-1">
          <p class="text-sm font-semibold text-(--django-heading)">
            {{ statusLabel }}
          </p>
          <p v-if="transcript" class="mt-1 truncate text-xs text-(--django-muted)">
            {{ transcript }}
          </p>
          <p v-else-if="state !== 'error'" class="mt-1 text-xs text-(--django-muted)">
            {{ text.liveHint }}
          </p>
          <details v-if="state === 'error' && (errorCode || errorDetail)" class="mt-2 text-xs text-(--django-muted)">
            <summary class="cursor-pointer font-medium">{{ text.liveTechnicalDetails }}</summary>
            <p class="mt-1 break-words font-mono">
              {{ [errorCode, errorStage, errorDetail].filter(Boolean).join(' · ') }}
            </p>
          </details>
        </div>
        <UButton
          v-if="state !== 'error'"
          icon="i-lucide-phone-off"
          :aria-label="text.liveStop"
          color="error"
          variant="soft"
          size="sm"
          @click="() => stopConversation()"
        />
        <div v-else class="flex items-center gap-1">
          <UButton
            v-if="errorRetryable"
            icon="i-lucide-refresh-cw"
            :aria-label="text.liveRetry"
            :label="text.liveRetry"
            color="primary"
            variant="soft"
            size="sm"
            @click="retryConversation"
          />
          <UButton
            icon="i-lucide-x"
            :aria-label="text.liveClose"
            color="neutral"
            variant="ghost"
            size="sm"
            @click="() => stopConversation()"
          />
        </div>
        <div v-if="photoUrl" class="flex w-full items-center gap-3 rounded-[5px] bg-(--django-surface-soft) p-2">
          <img :src="photoUrl" :alt="text.liveCandidatePhoto" class="size-14 rounded-[5px] object-cover" />
          <p class="text-xs text-(--django-copy)">{{ text.liveCandidatePhoto }}</p>
        </div>
        <div v-if="state !== 'error'" class="w-full">
          <FeatureExplainer feature="live" />
        </div>
      </aside>
    </Transition>
  </Teleport>
</template>

<style scoped>
.live-conversation-panel {
  position: fixed;
  z-index: 60;
  right: 1rem;
  bottom: 1rem;
  display: flex;
  width: min(28rem, calc(100vw - 2rem));
  align-items: center;
  flex-wrap: wrap;
  gap: 0.875rem;
  padding: 1rem;
  border: 1px solid var(--django-border);
  border-radius: 5px;
  background: color-mix(in srgb, var(--django-surface) 94%, transparent);
  box-shadow: 0 20px 55px rgb(50 8 8 / 24%);
  backdrop-filter: blur(16px);
}

.live-orb {
  display: flex;
  width: 3.25rem;
  height: 3.25rem;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  gap: 3px;
  border-radius: 999px;
  color: white;
  background: var(--color-django-red);
  box-shadow: 0 0 0 8px rgb(235 8 8 / 10%);
}

.live-orb span {
  width: 3px;
  height: 8px;
  border-radius: 999px;
  background: currentColor;
  animation: live-wave 900ms ease-in-out infinite alternate;
}

.live-orb span:nth-child(2),
.live-orb span:nth-child(4) { animation-delay: 160ms; }
.live-orb span:nth-child(3) { animation-delay: 320ms; }
.live-orb--connecting span { animation-duration: 1.6s; }
.live-orb--error { background: var(--color-django-burgundy); }

@keyframes live-wave {
  from { transform: scaleY(0.55); opacity: 0.65; }
  to { transform: scaleY(2.1); opacity: 1; }
}

.live-panel-enter-active,
.live-panel-leave-active { transition: opacity 180ms ease, transform 180ms ease; }
.live-panel-enter-from,
.live-panel-leave-to { opacity: 0; transform: translateY(12px); }

@media (prefers-reduced-motion: reduce) {
  .live-orb span { animation: none; }
}
</style>
