<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";
import { useStorage } from "@vueuse/core";

import { useLocale } from "@/composables/useLocale";
import FeatureExplainer from "@/components/chat/FeatureExplainer.vue";
import {
  mergeLiveTranscriptText,
  type LiveTranscriptRole,
  type LiveTranscriptUpdate,
} from "@/features/live/transcript";
import {
  DEFAULT_LIVE_TURN_LIMIT,
  liveUsageDay,
  normalizeLiveUsage,
  recordLiveTurns,
  remainingLiveTurns,
  type LiveDailyUsage,
} from "@/features/live/usage";
import {
  buildLiveWebSocketUrl,
  LIVE_OUTPUT_SAMPLE_RATE,
  pcm16ToFloat32,
  resampleToPcm16,
} from "@/utils/liveAudio";

type LiveState = "idle" | "connecting" | "listening" | "speaking" | "limit" | "error";
const LIVE_CONNECTION_TIMEOUT_MS = 20_000;

type LiveControlMessage = {
  type: "ready" | "error" | "interrupted" | "ending" | "turn_complete" | "limit_reached" | "transcript" | "tool";
  message?: string;
  code?: string;
  detail?: string;
  retryable?: boolean;
  stage?: string;
  name?: string;
  status?: "running" | "completed";
  role?: "user" | "assistant";
  text?: string;
  finished?: boolean;
  max_turns?: number;
  turns_used?: number;
  turns_remaining?: number;
  result?: string;
};

const props = defineProps<{
  apiBaseUrl: string;
  documentIds?: string[];
  history?: Array<{ role: "user" | "assistant"; content: string }>;
  pulse?: boolean;
}>();

const emit = defineEmits<{
  transcript: [update: LiveTranscriptUpdate];
  tried: [];
}>();

const { locale, text } = useLocale();
const state = ref<LiveState>("idle");
const errorMessage = ref("");
const errorCode = ref("");
const errorDetail = ref("");
const errorStage = ref("");
const errorRetryable = ref(false);
const serverTurnLimit = ref(DEFAULT_LIVE_TURN_LIMIT);
const sessionTurnsRecorded = ref(0);
const limitMessage = ref("");
const dailyUsage = useStorage<LiveDailyUsage>("django-live-daily-usage", {
  day: liveUsageDay(),
  turns: 0,
});
const activeTool = ref("");
const transcript = ref("");
const photoUrl = ref("");
let socket: WebSocket | null = null;
let connectionTimeout: ReturnType<typeof setTimeout> | null = null;
let microphoneStream: MediaStream | null = null;
let audioContext: AudioContext | null = null;
let microphoneSource: MediaStreamAudioSourceNode | null = null;
let captureProcessor: ScriptProcessorNode | null = null;
let silentGain: GainNode | null = null;
let nextPlaybackTime = 0;
let closeWhenPlaybackEnds = false;
const playbackSources = new Set<AudioBufferSourceNode>();
let transcriptTurnId = "";
let transcriptTurnNumber = 0;
const transcriptBuffers: Record<LiveTranscriptRole, string> = {
  user: "",
  assistant: "",
};

function clearConnectionTimeout() {
  if (connectionTimeout === null) return;
  clearTimeout(connectionTimeout);
  connectionTimeout = null;
}

function failConversation(options: {
  message: string;
  code: string;
  stage: string;
  detail?: string;
  retryable?: boolean;
}) {
  clearConnectionTimeout();
  errorMessage.value = options.message;
  errorCode.value = options.code;
  errorDetail.value = options.detail || "";
  errorStage.value = options.stage;
  errorRetryable.value = options.retryable ?? true;
  state.value = "error";

  const failedSocket = socket;
  socket = null;
  if (failedSocket && failedSocket.readyState < WebSocket.CLOSING) {
    failedSocket.close();
  }
  cleanupMedia();
}

const active = computed(() =>
  ["connecting", "listening", "speaking"].includes(state.value)
);
const turnsRemaining = computed(() =>
  remainingLiveTurns(dailyUsage.value, serverTurnLimit.value)
);
const liveLimitReached = computed(() =>
  text.value.liveLimitReached.replace("{limit}", String(serverTurnLimit.value))
);
const panelVisible = computed(
  () => state.value !== "idle" || Boolean(errorMessage.value || limitMessage.value)
);
const buttonTooltip = computed(() =>
  turnsRemaining.value === 0
    ? liveLimitReached.value
    : props.pulse
      ? text.value.liveTryMode
      : text.value.liveMode
);
const remainingLabel = computed(() =>
  text.value.liveTurnsRemaining.replace("{count}", String(turnsRemaining.value))
);
const statusLabel = computed(() => {
  if (activeTool.value) return text.value.liveUsingTool.replace("{tool}", activeTool.value);
  if (state.value === "connecting") return text.value.liveConnecting;
  if (state.value === "speaking") return text.value.liveSpeaking;
  if (state.value === "limit") return limitMessage.value || liveLimitReached.value;
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
    if (playbackSources.size === 0 && closeWhenPlaybackEnds) {
      socket?.close();
      socket = null;
      cleanupMedia();
      return;
    }
    if (playbackSources.size === 0 && state.value === "speaking") {
      state.value = "listening";
    }
  };
  state.value = "speaking";
  source.start(startAt);
}

function stopMicrophoneCapture() {
  captureProcessor?.disconnect();
  microphoneSource?.disconnect();
  silentGain?.disconnect();
  captureProcessor = null;
  microphoneSource = null;
  silentGain = null;
  microphoneStream?.getTracks().forEach((track) => track.stop());
  microphoneStream = null;
}

function showUsageLimit() {
  limitMessage.value = liveLimitReached.value;
  state.value = "limit";
  closeWhenPlaybackEnds = true;
  stopMicrophoneCapture();
  if (playbackSources.size === 0) {
    socket?.close();
    socket = null;
    cleanupMedia();
  }
}

function beginTranscriptSession() {
  transcriptTurnNumber = 0;
  transcriptTurnId = `live-${crypto.randomUUID()}-${transcriptTurnNumber}`;
  transcriptBuffers.user = "";
  transcriptBuffers.assistant = "";
}

function emitTranscriptUpdate(
  role: LiveTranscriptRole,
  fragment: string,
  finished: boolean
) {
  transcriptBuffers[role] = mergeLiveTranscriptText(
    transcriptBuffers[role],
    fragment
  );
  const completeText = transcriptBuffers[role];
  if (!completeText) return;

  transcript.value = completeText;
  emit("transcript", {
    id: `${transcriptTurnId}-${role}`,
    turnId: transcriptTurnId,
    role,
    text: completeText,
    finished,
  });
}

function completeTranscriptTurn() {
  emitTranscriptUpdate("user", "", true);
  emitTranscriptUpdate("assistant", "", true);
  transcriptTurnNumber += 1;
  transcriptTurnId = transcriptTurnId.replace(/-\d+$/, `-${transcriptTurnNumber}`);
  transcriptBuffers.user = "";
  transcriptBuffers.assistant = "";
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
    clearConnectionTimeout();
    serverTurnLimit.value = message.max_turns || DEFAULT_LIVE_TURN_LIMIT;
    dailyUsage.value = normalizeLiveUsage(dailyUsage.value);
    if (turnsRemaining.value === 0) {
      showUsageLimit();
      return;
    }
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
    if (message.role) {
      emitTranscriptUpdate(message.role, message.text, Boolean(message.finished));
    }
    return;
  }
  if (message.type === "transcript" && message.role && message.finished) {
    emitTranscriptUpdate(message.role, "", true);
    return;
  }
  if (message.type === "turn_complete") {
    completeTranscriptTurn();
    const reportedTurns = message.turns_used || sessionTurnsRecorded.value + 1;
    const newTurns = Math.max(0, reportedTurns - sessionTurnsRecorded.value);
    sessionTurnsRecorded.value = Math.max(sessionTurnsRecorded.value, reportedTurns);
    dailyUsage.value = recordLiveTurns(
      dailyUsage.value,
      newTurns,
      serverTurnLimit.value
    );
    if (turnsRemaining.value === 0) showUsageLimit();
    return;
  }
  if (message.type === "limit_reached") {
    showUsageLimit();
    return;
  }
  if (message.type === "error") {
    failConversation({
      message: message.message || text.value.liveError,
      code: message.code || "live_session_failed",
      detail: message.detail,
      stage: message.stage || (state.value === "connecting" ? "connecting" : "streaming"),
      retryable: Boolean(message.retryable),
    });
    return;
  }
  if (message.type === "ending") {
    failConversation({
      message: text.value.liveSessionEnding,
      code: "session_ending",
      stage: "streaming",
    });
  }
}

async function startConversation() {
  if (active.value) return;
  emit("tried");
  dailyUsage.value = normalizeLiveUsage(dailyUsage.value);
  if (turnsRemaining.value === 0) {
    showUsageLimit();
    return;
  }
  errorMessage.value = "";
  errorCode.value = "";
  errorDetail.value = "";
  errorStage.value = "";
  errorRetryable.value = false;
  transcript.value = "";
  photoUrl.value = "";
  limitMessage.value = "";
  sessionTurnsRecorded.value = 0;
  closeWhenPlaybackEnds = false;
  beginTranscriptSession();
  state.value = "connecting";
  let startStage = "microphone";

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

    startStage = "connecting";
    const activeSocket = new WebSocket(buildLiveWebSocketUrl(props.apiBaseUrl));
    socket = activeSocket;
    activeSocket.binaryType = "arraybuffer";
    connectionTimeout = setTimeout(() => {
      if (socket !== activeSocket || state.value !== "connecting") return;
      failConversation({
        message: text.value.liveConnectionTimeout,
        code: "live_connection_timeout",
        detail: `The live service did not become ready within ${LIVE_CONNECTION_TIMEOUT_MS / 1000} seconds.`,
        stage: "connecting",
      });
    }, LIVE_CONNECTION_TIMEOUT_MS);
    activeSocket.onopen = () => {
      if (socket !== activeSocket) return;
      activeSocket.send(
        JSON.stringify({
          type: "start",
          locale: locale.value,
          documents: props.documentIds || [],
          history: props.history || [],
        })
      );
    };
    activeSocket.onmessage = (event) => {
      if (socket !== activeSocket) return;
      if (typeof event.data === "string") {
        try {
          handleControlMessage(JSON.parse(event.data) as LiveControlMessage);
        } catch {
          failConversation({
            message: text.value.liveConnectionError,
            code: "invalid_live_message",
            detail: "The live service returned an invalid control message.",
            stage: state.value === "connecting" ? "connecting" : "streaming",
          });
        }
      } else {
        playAudio(event.data as ArrayBuffer);
      }
    };
    activeSocket.onerror = () => {
      if (socket !== activeSocket) return;
      failConversation({
        message: text.value.liveConnectionError,
        code: "browser_websocket_error",
        stage: state.value === "connecting" ? "connecting" : "streaming",
      });
    };
    activeSocket.onclose = (event) => {
      if (socket !== activeSocket) return;
      socket = null;
      clearConnectionTimeout();
      if (state.value === "connecting" || state.value === "listening" || state.value === "speaking") {
        failConversation({
          message: text.value.liveConnectionClosed,
          code: "live_connection_closed",
          detail: `WebSocket closed with code ${event.code}.`,
          stage: state.value === "connecting" ? "connecting" : "streaming",
        });
        return;
      }
      if (state.value === "limit" && playbackSources.size > 0) {
        stopMicrophoneCapture();
        return;
      }
      cleanupMedia();
    };
  } catch (cause) {
    failConversation({
      message:
        startStage === "microphone"
          ? text.value.liveMicrophoneError
          : text.value.liveConnectionError,
      code: startStage === "microphone" ? "microphone_error" : "live_connection_failed",
      detail: cause instanceof Error ? cause.message : undefined,
      stage: startStage,
    });
  }
}

function cleanupMedia() {
  stopMicrophoneCapture();
  stopPlayback();
  if (audioContext) void audioContext.close();
  audioContext = null;
}

function stopConversation(clearError = true) {
  clearConnectionTimeout();
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: "stop" }));
  }
  socket?.close();
  socket = null;
  cleanupMedia();
  activeTool.value = "";
  transcript.value = "";
  photoUrl.value = "";
  limitMessage.value = "";
  closeWhenPlaybackEnds = false;
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
  <span class="inline-flex">
    <UTooltip :text="buttonTooltip">
      <UButton
        icon="i-lucide-mic"
        type="button"
        :aria-label="buttonTooltip"
        :title="buttonTooltip"
        :color="active ? 'primary' : 'neutral'"
        :variant="active ? 'soft' : 'ghost'"
        :class="{ 'live-trigger--pulsing': pulse && turnsRemaining > 0 }"
        size="sm"
        @click="toggleConversation"
      />
    </UTooltip>
  </span>

  <Teleport to="body">
    <Transition name="live-panel">
      <aside
        v-if="panelVisible"
        class="live-conversation-panel"
        :role="state === 'error' || state === 'limit' ? 'alert' : 'status'"
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
          <p v-else-if="state !== 'error' && state !== 'limit'" class="mt-1 text-xs text-(--django-muted)">
            {{ text.liveHint }} {{ remainingLabel }}
          </p>
          <details v-if="state === 'error' && (errorCode || errorDetail)" class="mt-2 text-xs text-(--django-muted)">
            <summary class="cursor-pointer font-medium">{{ text.liveTechnicalDetails }}</summary>
            <p class="mt-1 break-words font-mono">
              {{ [errorCode, errorStage, errorDetail].filter(Boolean).join(' · ') }}
            </p>
          </details>
        </div>
        <UButton
          v-if="state !== 'error' && state !== 'limit'"
          icon="i-lucide-phone-off"
          :aria-label="text.liveStop"
          color="error"
          variant="soft"
          size="sm"
          @click="() => stopConversation()"
        />
        <div v-else-if="state === 'error'" class="flex items-center gap-1">
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
        <UButton
          v-else
          icon="i-lucide-x"
          :aria-label="text.liveClose"
          color="neutral"
          variant="ghost"
          size="sm"
          @click="() => stopConversation()"
        />
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

.live-trigger--pulsing {
  animation: live-trigger-pulse 2.2s ease-in-out infinite;
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
.live-orb--error,
.live-orb--limit { background: var(--color-django-burgundy); }

@keyframes live-wave {
  from { transform: scaleY(0.55); opacity: 0.65; }
  to { transform: scaleY(2.1); opacity: 1; }
}

@keyframes live-trigger-pulse {
  0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgb(229 109 88 / 0); }
  50% { transform: scale(1.08); box-shadow: 0 0 0 7px rgb(229 109 88 / 14%); }
}

.live-panel-enter-active,
.live-panel-leave-active { transition: opacity 180ms ease, transform 180ms ease; }
.live-panel-enter-from,
.live-panel-leave-to { opacity: 0; transform: translateY(12px); }

@media (prefers-reduced-motion: reduce) {
  .live-orb span { animation: none; }
  .live-trigger--pulsing { animation: none; }
}
</style>
