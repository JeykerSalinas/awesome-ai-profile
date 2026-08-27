/** Editorial content only: the tour never calls the chat or document APIs. */
export type StoryLocale = 'en' | 'es'
export type StoryTarget =
  'identity' | 'composer' | 'upload' | 'conversation' | 'preferences' | 'live' | 'stack'

interface ChapterCopy {
  label: string
  title: string
  description: string
  detail: string
  flow: readonly [string, string, string]
}

interface Chapter {
  id: string
  target: StoryTarget
  icon: string
  technologies: readonly string[]
  source: string
  en: ChapterCopy
  es: ChapterCopy
}

export const chapters = [
  {
    id: 'interface',
    target: 'identity',
    icon: 'i-lucide-panels-top-left',
    technologies: ['Vue 3', 'TypeScript', 'Nuxt UI'],
    source: 'app/src/views/MainView.vue',
    en: {
      label: 'The experience',
      title: 'A résumé you can talk to.',
      description:
        'This is not a chat pasted onto a portfolio. The conversation is the portfolio: a purpose-built interface for exploring Jeyker’s work.',
      detail:
        'Vue 3 manages reactive state, TypeScript defines message contracts, and Nuxt UI supplies the chat components. It runs on Vite, not a Nuxt server.',
      flow: ['Vue interface', 'Typed messages', 'Nuxt UI'],
    },
    es: {
      label: 'La experiencia',
      title: 'Un currículum que conversa.',
      description:
        'No es un chat pegado a un portafolio. La conversación es el portafolio: una interfaz diseñada para explorar el trabajo de Jeyker.',
      detail:
        'Vue 3 gestiona el estado reactivo, TypeScript define los contratos de mensajes y Nuxt UI aporta los componentes del chat. Se ejecuta con Vite, sin servidor Nuxt.',
      flow: ['Interfaz Vue', 'Mensajes tipados', 'Nuxt UI'],
    },
  },
  {
    id: 'streaming',
    target: 'composer',
    icon: 'i-lucide-radio',
    technologies: ['AI SDK', 'FastAPI', 'HTTP / SSE'],
    source: 'backend/services/ai_sdk_stream.py',
    en: {
      label: 'The conversation',
      title: 'An answer, as it happens.',
      description:
        'You don’t have to wait for the entire answer. Django’s words arrive progressively, keeping the conversation responsive.',
      detail:
        'FastAPI translates agent events into the AI SDK stream protocol over HTTP/SSE. The Vue client assembles text and custom message parts, with stop and retry controls.',
      flow: ['Agent events', 'SSE stream', 'Live response'],
    },
    es: {
      label: 'La conversación',
      title: 'La respuesta cobra vida.',
      description:
        'No tienes que esperar a que termine toda la respuesta. Las palabras de Django llegan progresivamente y la conversación se siente ágil.',
      detail:
        'FastAPI traduce los eventos del agente al protocolo de streaming de AI SDK mediante HTTP/SSE. Vue reconstruye texto y mensajes personalizados, con controles para detener y reintentar.',
      flow: ['Eventos', 'Flujo SSE', 'Respuesta en vivo'],
    },
  },
  {
    id: 'retrieval',
    target: 'upload',
    icon: 'i-lucide-scan-search',
    technologies: ['LangChain', 'Gemini embeddings', 'ChromaDB'],
    source: 'backend/services/vector_store_service.py',
    en: {
      label: 'The evidence',
      title: 'Less guessing. More context.',
      description:
        'A job offer can become part of the conversation. RAG retrieves relevant evidence from Jeyker’s knowledge base and attached PDFs to help the model answer.',
      detail:
        'Selectable PDF text is split into overlapping chunks and embedded as vectors. Semantic search returns relevant passages; retrieved source names appear in the chat. Scanned PDFs need OCR first.',
      flow: ['Text chunks', 'Vector search', 'Cited context'],
    },
    es: {
      label: 'La evidencia',
      title: 'Menos suposiciones. Más contexto.',
      description:
        'Una oferta laboral puede formar parte de la conversación. El RAG recupera evidencia relevante del perfil de Jeyker y de los PDFs adjuntos para ayudar al modelo a responder.',
      detail:
        'El texto seleccionable del PDF se divide en fragmentos solapados y se transforma en vectores. La búsqueda semántica devuelve pasajes relevantes y sus fuentes aparecen en el chat. Los escaneos necesitan OCR previo.',
      flow: ['Fragmentos', 'Búsqueda vectorial', 'Contexto citado'],
    },
  },
  {
    id: 'privacy',
    target: 'upload',
    icon: 'i-lucide-shield-check',
    technologies: ['In-memory ChromaDB', 'Document ID filters', 'TTL'],
    source: 'backend/services/vector_store_service.py',
    en: {
      label: 'The boundary',
      title: 'Your PDF is a guest, too.',
      description:
        'The professional profile and visitor uploads have different lifetimes. Your document does not become part of the permanent profile index.',
      detail:
        'Uploads stay in backend memory and retrieval filters by attached document IDs. Removal discards them; expired uploads are cleaned on the next upload or search (30 minutes idle by default). Text is sent to Google for embeddings and model context.',
      flow: ['Attached PDF', 'Temporary RAM', 'Remove / expire'],
    },
    es: {
      label: 'Los límites',
      title: 'Tu PDF también está de visita.',
      description:
        'El perfil profesional y los archivos de visitantes tienen vidas distintas. Tu documento no se incorpora al índice permanente del perfil.',
      detail:
        'Los adjuntos viven en la memoria del backend y se filtran por los IDs enviados en el chat. Se descartan al quitarlos; los caducados se limpian en la siguiente carga o búsqueda (30 minutos de inactividad por defecto). El texto se envía a Google para embeddings y contexto del modelo.',
      flow: ['PDF adjunto', 'RAM temporal', 'Borrado / caducidad'],
    },
  },
  {
    id: 'tools',
    target: 'conversation',
    icon: 'i-lucide-workflow',
    technologies: ['Gemini', 'LangChain tools', 'Vue components'],
    source: 'backend/agents/tools.py',
    en: {
      label: 'The action',
      title: 'More than a text generator.',
      description:
        'Ask to see Jeyker’s photo and the agent can call a real function. Its result becomes a photo card inside the conversation.',
      detail:
        'LangChain exposes named Python tools for profile sections, experience, documents and photos. The backend emits typed results and Vue renders them. Contact actions and enforced approvals are still future work.',
      flow: ['Model selects', 'Python tool', 'Rendered result'],
    },
    es: {
      label: 'La acción',
      title: 'No solo genera texto.',
      description:
        'Pide una foto de Jeyker y el agente puede llamar a una función real. Su resultado se convierte en una tarjeta dentro de la conversación.',
      detail:
        'LangChain expone herramientas Python para consultar el perfil, experiencia, documentos y fotos. El backend emite resultados tipados y Vue los representa. Las acciones de contacto y las aprobaciones obligatorias siguen pendientes.',
      flow: ['El modelo elige', 'Herramienta Python', 'Resultado visual'],
    },
  },
  {
    id: 'locale',
    target: 'preferences',
    icon: 'i-lucide-languages',
    technologies: ['VueUse', 'EN / ES', 'Locale-aware prompts'],
    source: 'app/src/composables/useLocale.ts',
    en: {
      label: 'The details',
      title: 'One profile. Two languages.',
      description:
        'The interface adapts to your browser language and remembers your choice. Light and dark modes belong to the same visual identity.',
      detail:
        'The selected language travels with each chat request. A locale-aware system prompt asks Gemini to respond in English or Spanish, using the same English knowledge base.',
      flow: ['Your language', 'System prompt', 'Localized answer'],
    },
    es: {
      label: 'Los detalles',
      title: 'Un perfil. Dos idiomas.',
      description:
        'La interfaz detecta el idioma del navegador y recuerda tu elección. Los modos claro y oscuro mantienen la misma identidad visual.',
      detail:
        'El idioma seleccionado viaja en cada petición del chat. Un prompt de sistema pide a Gemini responder en español o inglés usando la misma base de conocimiento en inglés.',
      flow: ['Tu idioma', 'Prompt de sistema', 'Respuesta localizada'],
    },
  },
  {
    id: 'live',
    target: 'live',
    icon: 'i-lucide-audio-waveform',
    technologies: ['Gemini Live', 'WebSocket', 'Native audio'],
    source: 'backend/services/live_service.py',
    en: {
      label: 'The voice',
      title: 'The conversation leaves the keyboard.',
      description:
        'The microphone opens a real-time voice session where both sides can speak naturally, interrupt and keep the transcript in the same chat history.',
      detail:
        'Vue converts microphone frames to 16 kHz PCM and sends them through a FastAPI WebSocket bridge. Gemini returns native 24 kHz audio, transcriptions and tool calls. The public demo allows two voice turns per day in each browser.',
      flow: ['Microphone PCM', 'Gemini Live + tools', 'Audio and transcript'],
    },
    es: {
      label: 'La voz',
      title: 'La conversación sale del teclado.',
      description:
        'El micrófono abre una sesión de voz en tiempo real donde ambos pueden hablar con naturalidad, interrumpirse y conservar la transcripción en el mismo historial.',
      detail:
        'Vue convierte el micrófono a PCM de 16 kHz y lo envía mediante un puente WebSocket en FastAPI. Gemini devuelve audio nativo de 24 kHz, transcripciones y llamadas a tools. El demo público permite dos turnos de voz diarios por navegador.',
      flow: ['Micrófono PCM', 'Gemini Live + tools', 'Audio y transcripción'],
    },
  },
  {
    id: 'deployment',
    target: 'stack',
    icon: 'i-lucide-cloud',
    technologies: ['GitHub Actions', 'Docker', 'Azure'],
    source: 'Makefile',
    en: {
      label: 'The delivery',
      title: 'From repository to reality.',
      description:
        'The experience connects frontend engineering, applied AI and deployment. Every chapter has an implementation you can inspect.',
      detail:
        'GitHub Actions deploys the frontend to Azure Static Web Apps. The FastAPI backend has a Docker image and Makefile commands for Azure Container Registry and Container Apps; backend deployment is not yet automated.',
      flow: ['GitHub Actions', 'Vue → Static Apps', 'Docker → API'],
    },
    es: {
      label: 'La entrega',
      title: 'Del repositorio a la realidad.',
      description:
        'Esta experiencia une frontend, IA aplicada y despliegue. Cada capítulo tiene una implementación que puedes inspeccionar.',
      detail:
        'GitHub Actions despliega el frontend en Azure Static Web Apps. FastAPI tiene una imagen Docker y comandos Makefile para Azure Container Registry y Container Apps; el despliegue del backend aún no está automatizado.',
      flow: ['GitHub Actions', 'Vue → Static Apps', 'Docker → API'],
    },
  },
] as const satisfies readonly Chapter[]

export const storyCopy = {
  en: {
    eyebrow: 'BEHIND THE CHAT',
    launch: 'Why this project is so cool?',
    teaser:
      'Eight chapters. One conversation. Explore the engineering behind Django.',
    duration: 'About 3 minutes',
    close: 'Close tour',
    previous: 'Back',
    next: 'Next chapter',
    finish: 'Back to the chat',
    chapter: 'Chapter',
    of: 'of',
    code: 'Explore the code',
    mechanism: 'Under the hood',
    diagram: 'Illustrative flow · no live API calls',
    navigation: 'Tour chapters',
    keyboard: '← → to explore · Esc to close',
    motion: 'Pause animations',
    resumeMotion: 'Resume animations',
    prompt:
      'Show me a picture of Jeyker and tell me about his experience building AI applications.',
    tryIt: 'Prepare a question',
    draftReady: 'Question prepared in the chat. Review it before sending.',
  },
  es: {
    eyebrow: 'DETRÁS DEL CHAT',
    launch: '¿Por qué este proyecto es tan genial?',
    teaser:
      'Ocho capítulos. Una conversación. Explora la ingeniería detrás de Django.',
    duration: 'Unos 3 minutos',
    close: 'Cerrar recorrido',
    previous: 'Anterior',
    next: 'Siguiente capítulo',
    finish: 'Volver al chat',
    chapter: 'Capítulo',
    of: 'de',
    code: 'Explorar el código',
    mechanism: 'Cómo funciona',
    diagram: 'Esquema ilustrativo · sin llamadas a la API',
    navigation: 'Capítulos del recorrido',
    keyboard: '← → para explorar · Esc para cerrar',
    motion: 'Pausar animaciones',
    resumeMotion: 'Reanudar animaciones',
    prompt:
      'Muéstrame una foto de Jeyker y cuéntame sobre su experiencia construyendo aplicaciones de IA.',
    tryIt: 'Preparar una pregunta',
    draftReady: 'Pregunta preparada en el chat. Revísala antes de enviarla.',
  },
} as const

export function sourceUrl(path: string): string {
  return `https://github.com/JeykerSalinas/awesome-ai-profile/blob/main/${path.split('/').map(encodeURIComponent).join('/')}`
}

export function chapterIndex(index: number): number {
  return Math.max(0, Math.min(chapters.length - 1, Math.trunc(index) || 0))
}

/** Preparing a tour question must preserve existing text and never send it. */
export function appendTourQuestion(draft: string, question: string): string {
  return draft.trim() ? `${draft}\n\n${question}` : question
}
