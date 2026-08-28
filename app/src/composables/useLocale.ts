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
    chatErrorTitle: "Django could not respond",
    chatErrorRetry: "Try again",
    chatErrorDismiss: "Dismiss",
    chatErrorReference: "Error reference",
    liveMode: "Start live voice conversation",
    liveTryMode: "Try conversational mode",
    liveConnecting: "Connecting to Django...",
    liveListening: "Django is listening",
    liveSpeaking: "Django is speaking",
    liveUsingTool: "Using {tool}...",
    liveHint: "Speak naturally. You can interrupt at any time.",
    liveTurnsRemaining: "{count} demo voice turn(s) remaining today.",
    liveLimitReached: "You have used today's {limit} demo voice turns. You can continue in text chat.",
    liveStop: "End live conversation",
    liveClose: "Close",
    liveRetry: "Try again",
    liveTechnicalDetails: "Technical details",
    liveSessionEnding: "Gemini is ending this live session. Try connecting again.",
    liveError: "Live conversation is unavailable.",
    liveConnectionError: "Could not connect to the live conversation service.",
    liveConnectionTimeout: "The live conversation service took too long to respond.",
    liveConnectionClosed: "The live conversation ended unexpectedly.",
    liveMicrophoneUnavailable: "This browser cannot access a microphone.",
    liveMicrophoneError: "Microphone access was denied or could not be started.",
    liveCandidatePhoto: "Jeyker's professional profile photo",
    demoNoticeEyebrow: "Public technology demo",
    demoNoticeTitle: "Before you try Django",
    demoNoticePurpose:
      "This platform is a portfolio demo designed to show the technologies Jeyker works with. It is not a production service.",
    demoNoticeLimits:
      "It currently uses free-tier, limited-capacity generative AI services, so responses and live voice availability may be restricted, inaccurate, or interrupted.",
    demoNoticePrivacy:
      "Your messages, voice audio, and attached documents are sent to Google Gemini to generate responses. Depending on the service plan and region, the provider may use inputs and outputs to improve its products, and human reviewers may process them under its terms.",
    demoNoticeWarning:
      "Do not enter personal, sensitive, confidential, or third-party information.",
    demoNoticeStorage:
      "This demo does not persist chat history. Attached PDFs are held temporarily in memory and expire after a short period. Continuing only acknowledges that you have read this notice.",
    demoNoticeTerms: "Google Gemini API terms",
    demoNoticePrivacyPolicy: "Google privacy policy",
    demoNoticeAccept: "I understand and continue",
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
    chatErrorTitle: "Django no pudo responder",
    chatErrorRetry: "Reintentar",
    chatErrorDismiss: "Cerrar",
    chatErrorReference: "Referencia del error",
    liveMode: "Iniciar conversación de voz en vivo",
    liveTryMode: "Prueba el modo conversacional",
    liveConnecting: "Conectando con Django...",
    liveListening: "Django está escuchando",
    liveSpeaking: "Django está hablando",
    liveUsingTool: "Usando {tool}...",
    liveHint: "Habla con naturalidad. Puedes interrumpir cuando quieras.",
    liveTurnsRemaining: "Te quedan {count} turno(s) de voz del demo por hoy.",
    liveLimitReached: "Ya utilizaste los {limit} turnos de voz del demo disponibles hoy. Puedes continuar por texto.",
    liveStop: "Finalizar conversación en vivo",
    liveClose: "Cerrar",
    liveRetry: "Reintentar",
    liveTechnicalDetails: "Detalles técnicos",
    liveSessionEnding: "Gemini está cerrando esta sesión. Intenta conectarte de nuevo.",
    liveError: "La conversación en vivo no está disponible.",
    liveConnectionError: "No se pudo conectar con el servicio de conversación en vivo.",
    liveConnectionTimeout: "El servicio de conversación tardó demasiado en responder.",
    liveConnectionClosed: "La conversación en vivo terminó inesperadamente.",
    liveMicrophoneUnavailable: "Este navegador no puede acceder al micrófono.",
    liveMicrophoneError: "Se rechazó el acceso al micrófono o no pudo iniciarse.",
    liveCandidatePhoto: "Foto de perfil profesional de Jeyker",
    demoNoticeEyebrow: "Demo tecnológico público",
    demoNoticeTitle: "Antes de probar Django",
    demoNoticePurpose:
      "Esta plataforma es un demo de portafolio creado para mostrar las tecnologías que domina Jeyker. No es un servicio de producción.",
    demoNoticeLimits:
      "Actualmente utiliza servicios gratuitos de IA generativa con capacidad limitada, por lo que las respuestas y la disponibilidad del modo de voz pueden ser restringidas, inexactas o interrumpirse.",
    demoNoticePrivacy:
      "Tus mensajes, el audio de voz y los documentos adjuntos se envían a Google Gemini para generar respuestas. Según el plan del servicio y la región, el proveedor puede utilizar las entradas y salidas para mejorar sus productos, y revisores humanos pueden procesarlas conforme a sus términos.",
    demoNoticeWarning:
      "No introduzcas información personal, sensible, confidencial ni datos de terceros.",
    demoNoticeStorage:
      "Este demo no conserva el historial del chat. Los PDF adjuntos se mantienen temporalmente en memoria y caducan después de un periodo breve. Continuar solo confirma que has leído este aviso.",
    demoNoticeTerms: "Términos de la API de Google Gemini",
    demoNoticePrivacyPolicy: "Política de privacidad de Google",
    demoNoticeAccept: "Entiendo y continuar",
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
