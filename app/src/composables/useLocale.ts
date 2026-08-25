import { computed, watchEffect } from 'vue'
import { en, es } from '@nuxt/ui/locale'
import { useStorage } from '@vueuse/core'

const translations = {
  en: {
    documentTitle: 'Django AI · Jeyker Salinas',
    assistantDescription: "Jeyker's professional sidekick",
    availableForWork: 'Available for work',
    portfolioBadge: 'Interactive AI portfolio',
    greeting: 'Meet Jeyker,',
    greetingHighlight: 'through Django.',
    introduction:
      'Ask anything about his engineering experience, AI projects, favorite technologies, or why this résumé has its own canine assistant.',
    suggestions: [
      'Why should we hire Jeyker?',
      'What has he built with Vue and TypeScript?',
      'Tell me about his AI experience.',
      'Show me a picture of Jeyker.',
    ],
    thinking: 'Django is thinking...',
    placeholder: 'Ask Django about Jeyker...',
    poweredBy: 'Powered by Gemini & LangChain',
    builtWith: 'Built with Vue 3, Nuxt UI, FastAPI and the AI SDK.',
    candidateRole: 'Full-stack & AI engineer',
    approvalRequired: 'Your approval is required',
    approvalDescription: 'The assistant wants to run',
    approve: 'Approve',
    reject: 'Reject',
    viewProject: 'View project',
    lightMode: 'Switch to light mode',
    darkMode: 'Switch to dark mode',
    switchLanguage: 'Switch language to Spanish',
  },
  es: {
    documentTitle: 'Django IA · Jeyker Salinas',
    assistantDescription: 'El asistente profesional de Jeyker',
    availableForWork: 'Disponible para trabajar',
    portfolioBadge: 'Portafolio interactivo con IA',
    greeting: 'Conoce a Jeyker,',
    greetingHighlight: 'a través de Django.',
    introduction:
      'Pregunta sobre su experiencia como ingeniero, sus proyectos de IA, sus tecnologías favoritas o por qué este currículum tiene su propio asistente canino.',
    suggestions: [
      '¿Por qué deberíamos contratar a Jeyker?',
      '¿Qué ha construido con Vue y TypeScript?',
      'Cuéntame sobre su experiencia en inteligencia artificial.',
      'Muéstrame una foto de Jeyker.',
    ],
    thinking: 'Django está pensando...',
    placeholder: 'Pregúntale a Django sobre Jeyker...',
    poweredBy: 'Desarrollado con Gemini y LangChain',
    builtWith: 'Construido con Vue 3, Nuxt UI, FastAPI y AI SDK.',
    candidateRole: 'Ingeniero full-stack y de IA',
    approvalRequired: 'Se necesita tu aprobación',
    approvalDescription: 'El asistente quiere ejecutar',
    approve: 'Aprobar',
    reject: 'Rechazar',
    viewProject: 'Ver proyecto',
    lightMode: 'Cambiar al modo claro',
    darkMode: 'Cambiar al modo oscuro',
    switchLanguage: 'Cambiar idioma a inglés',
  },
} as const

export type SupportedLocale = keyof typeof translations

export function resolveBrowserLocale(languages: readonly string[]): SupportedLocale {
  for (const language of languages) {
    const code = language.toLowerCase().split('-')[0]
    if (code === 'es' || code === 'en') return code
  }

  return 'en'
}

const browserLanguages =
  typeof navigator === 'undefined'
    ? []
    : navigator.languages.length
      ? navigator.languages
      : [navigator.language]

const locale = useStorage<SupportedLocale>(
  'django-preferred-language',
  resolveBrowserLocale(browserLanguages),
)

if (typeof document !== 'undefined') {
  watchEffect(() => {
    document.documentElement.lang = locale.value
    document.title = translations[locale.value].documentTitle
  })
}

export function useLocale() {
  const text = computed(() => translations[locale.value])
  const uiLocale = computed(() => (locale.value === 'es' ? es : en))

  return { locale, text, uiLocale }
}
