import { computed, watchEffect } from "vue";
import { en, es } from "@nuxt/ui/locale";
import { useStorage } from "@vueuse/core";

const translations = {
  en: {
    documentTitle: "AI-assistant",
    assistantDescription: "Jeyker's professional sidekick",
    availableForWork: "Available for work",
    greeting: "Meet Jeyker,",
    greetingHighlight: "through Django.",
    introduction:
      "Ask anything about his engineering experience, AI projects, favorite technologies, or why this résumé has its own canine assistant.",
    suggestions: [
      "Why should we hire Jeyker?",
      "Tell me about his AI experience.",
      "Show me a picture of Jeyker.",
    ],
    thinking: "Django is thinking...",
    placeholder: "Ask Django about Jeyker...",
    poweredBy: "Powered by Gemini & LangChain",
    builtWith: "Built with Vue 3, Nuxt UI, FastAPI and the AI SDK.",
    candidateRole: "Full-stack & AI engineer",
    approvalRequired: "Your approval is required",
    approvalDescription: "The assistant wants to run",
    approve: "Approve",
    reject: "Reject",
    viewProject: "View project",
    lightMode: "Switch to light mode",
    darkMode: "Switch to dark mode",
    switchLanguage: "Switch language to Spanish",
    verifiedSource: "Verified source",
    uploadDocument: "Attach a PDF",
    uploadingDocument: "Indexing document...",
    uploadedDocument: "Document ready for questions",
    removeDocument: "Remove document from this chat",
    documentUploadError: "The document could not be indexed.",
    liveMode: "Start live voice conversation",
    liveTryMode: "Try conversational mode",
    liveConnecting: "Connecting to Django...",
    liveListening: "Django is listening",
    liveSpeaking: "Django is speaking",
    liveUsingTool: "Using {tool}...",
    liveHint: "Speak naturally. You can interrupt at any time.",
    liveTurnsRemaining: "{count} demo voice turn(s) remaining today.",
    liveLimitReached: "You have used today's 2 demo voice turns. You can continue in text chat.",
    liveStop: "End live conversation",
    liveClose: "Close",
    liveRetry: "Try again",
    liveTechnicalDetails: "Technical details",
    liveSessionEnding: "Gemini is ending this live session. Try connecting again.",
    liveError: "Live conversation is unavailable.",
    liveConnectionError: "Could not connect to the live conversation service.",
    liveMicrophoneUnavailable: "This browser cannot access a microphone.",
    liveCandidatePhoto: "Jeyker's professional profile photo",
  },
  es: {
    documentTitle: "Asistente IA",
    assistantDescription: "El asistente profesional de Jeyker",
    availableForWork: "Disponible para trabajar",
    greeting: "Conoce a Jeyker,",
    greetingHighlight: "a través de Django.",
    introduction:
      "Pregunta sobre su experiencia como ingeniero, sus proyectos de IA, sus tecnologías favoritas o por qué este currículum tiene su propio asistente canino.",
    suggestions: [
      "¿Por qué deberíamos contratar a Jeyker?",
      "Cuéntame sobre su experiencia en IA.",
      "Muéstrame una foto de Jeyker.",
    ],
    thinking: "Django está pensando...",
    placeholder: "Pregúntale a Django sobre Jeyker...",
    poweredBy: "Desarrollado con Gemini y LangChain",
    builtWith: "Construido con Vue 3, Nuxt UI, FastAPI y AI SDK.",
    candidateRole: "Ingeniero full-stack y de IA",
    approvalRequired: "Se necesita tu aprobación",
    approvalDescription: "El asistente quiere ejecutar",
    approve: "Aprobar",
    reject: "Rechazar",
    viewProject: "Ver proyecto",
    lightMode: "Cambiar al modo claro",
    darkMode: "Cambiar al modo oscuro",
    switchLanguage: "Cambiar idioma a inglés",
    verifiedSource: "Fuente verificada",
    uploadDocument: "Adjuntar un PDF",
    uploadingDocument: "Indexando documento...",
    uploadedDocument: "Documento listo para preguntas",
    removeDocument: "Quitar documento de esta conversación",
    documentUploadError: "No se pudo indexar el documento.",
    liveMode: "Iniciar conversación de voz en vivo",
    liveTryMode: "Prueba el modo conversacional",
    liveConnecting: "Conectando con Django...",
    liveListening: "Django está escuchando",
    liveSpeaking: "Django está hablando",
    liveUsingTool: "Usando {tool}...",
    liveHint: "Habla con naturalidad. Puedes interrumpir cuando quieras.",
    liveTurnsRemaining: "Te quedan {count} turno(s) de voz del demo por hoy.",
    liveLimitReached: "Ya utilizaste los 2 turnos de voz del demo disponibles hoy. Puedes continuar por texto.",
    liveStop: "Finalizar conversación en vivo",
    liveClose: "Cerrar",
    liveRetry: "Reintentar",
    liveTechnicalDetails: "Detalles técnicos",
    liveSessionEnding: "Gemini está cerrando esta sesión. Intenta conectarte de nuevo.",
    liveError: "La conversación en vivo no está disponible.",
    liveConnectionError: "No se pudo conectar con el servicio de conversación en vivo.",
    liveMicrophoneUnavailable: "Este navegador no puede acceder al micrófono.",
    liveCandidatePhoto: "Foto de perfil profesional de Jeyker",
  },
} as const;

export type SupportedLocale = keyof typeof translations;

export function resolveBrowserLocale(
  languages: readonly string[]
): SupportedLocale {
  for (const language of languages) {
    const code = language.toLowerCase().split("-")[0];
    if (code === "es" || code === "en") return code;
  }

  return "en";
}

const browserLanguages =
  typeof navigator === "undefined"
    ? []
    : navigator.languages.length
    ? navigator.languages
    : [navigator.language];

const locale = useStorage<SupportedLocale>(
  "django-preferred-language",
  resolveBrowserLocale(browserLanguages)
);

if (typeof document !== "undefined") {
  watchEffect(() => {
    document.documentElement.lang = locale.value;
    document.title = translations[locale.value].documentTitle;
  });
}

export function useLocale() {
  const text = computed(() => translations[locale.value]);
  const uiLocale = computed(() => (locale.value === "es" ? es : en));

  return { locale, text, uiLocale };
}
