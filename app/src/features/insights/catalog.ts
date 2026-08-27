/** Local editorial copy: opening an explanation never invokes an LLM. */
export type InsightLocale = 'es' | 'en'
interface Explanation {
  title: string
  why: string
  how: string
  caveat: string
  flow: readonly [string, string, string]
}
interface Feature {
  icon: string
  technologies: readonly string[]
  source: string
  en: Explanation
  es: Explanation
}

export const features = {
  live: {
    icon: 'i-lucide-audio-waveform', technologies: ['Gemini Live', 'WebSocket', 'PCM audio', 'FastAPI'],
    source: 'backend/services/live_service.py',
    es: {
      title: 'Conversación de voz nativa',
      why: 'La voz no se convierte primero en un chat de texto: Gemini recibe audio continuo y responde con audio nativo de baja latencia.',
      how: 'El navegador envía PCM de 16 kHz por WebSocket a FastAPI. El backend conserva la API key, abre la sesión Live, ejecuta las mismas tools y devuelve audio PCM de 24 kHz.',
      caveat: 'Gemini Live sigue siendo una API preview. Para controlar el consumo, el demo permite dos turnos de voz al día por navegador y el backend corta cada WebSocket después de dos respuestas. Sin autenticación, esto reduce el uso casual pero no constituye una cuota antiabuso estricta.',
      flow: ['Micrófono y PCM', 'FastAPI y Gemini Live', 'Audio nativo y tools'],
    },
    en: {
      title: 'Native voice conversation',
      why: 'Voice is not first converted into a text chat: Gemini receives continuous audio and responds with low-latency native audio.',
      how: 'The browser sends 16 kHz PCM over WebSocket to FastAPI. The backend protects the API key, opens the Live session, runs the same tools and returns 24 kHz PCM audio.',
      caveat: 'Gemini Live remains a preview API. To control usage, the demo allows two voice turns per browser each day and the backend closes each WebSocket after two responses. Without authentication, this limits casual use but is not a strict anti-abuse quota.',
      flow: ['Microphone and PCM', 'FastAPI and Gemini Live', 'Native audio and tools'],
    },
  },
  tools: {
    icon: 'i-lucide-workflow', technologies: ['Gemini', 'LangChain', 'Python'],
    source: 'backend/agents/tools.py',
    es: {
      title: 'Tool calling',
      why: 'El modelo no solo escribe: puede pedir al backend que ejecute una función real para conseguir información.',
      how: 'LangChain presenta las herramientas y sus argumentos al modelo. Python ejecuta la función elegida y devuelve su resultado para que el agente continúe.',
      caveat: 'Esta actividad muestra ejecuciones observadas, no el pensamiento privado del modelo. Las herramientas actuales son de consulta.',
      flow: ['El modelo elige', 'Python ejecuta', 'El agente recibe'],
    },
    en: {
      title: 'Tool calling',
      why: 'The model does more than write: it can ask the backend to run a real function to retrieve information.',
      how: 'LangChain describes tools and their arguments to the model. Python executes the selected function and returns its result so the agent can continue.',
      caveat: 'This activity shows observed executions, not the model’s private thinking. Current tools are read-only lookups.',
      flow: ['Model selects', 'Python executes', 'Agent receives'],
    },
  },
  rag: {
    icon: 'i-lucide-scan-search', technologies: ['ChromaDB', 'Gemini embeddings', 'LangChain'],
    source: 'backend/services/vector_store_service.py',
    es: {
      title: 'RAG · búsqueda semántica',
      why: 'El agente puede apoyar su respuesta en tu perfil y en una oferta adjunta, en vez de depender solo de lo que aprendió el modelo.',
      how: 'El texto se divide en fragmentos solapados. Los embeddings representan esos fragmentos con vectores; ChromaDB busca los más similares a la consulta y los devuelve como contexto al LLM.',
      caveat: 'El código actual usa ChromaDB, no pgvector. Recuperar un pasaje no garantiza que la respuesta sea correcta: conviene revisar las fuentes.',
      flow: ['Fragmentos y vectores', 'Búsqueda en ChromaDB', 'Contexto para el LLM'],
    },
    en: {
      title: 'RAG · semantic search',
      why: 'The agent can ground its answer in the profile and an attached job offer instead of relying only on model training.',
      how: 'Text is split into overlapping chunks. Embeddings represent those chunks as vectors; ChromaDB finds passages similar to the query and returns them as LLM context.',
      caveat: 'This implementation uses ChromaDB, not pgvector. Retrieving a passage does not guarantee a correct answer: check the sources.',
      flow: ['Chunks and vectors', 'ChromaDB search', 'Context for the LLM'],
    },
  },
  profile: {
    icon: 'i-lucide-id-card', technologies: ['JSON', 'Python', 'Typed tool arguments'],
    source: 'backend/services/knowledge_service.py',
    es: {
      title: 'Perfil estructurado',
      why: 'Para una pregunta concreta no hace falta buscar por todo el currículum: el agente puede pedir una sección exacta.',
      how: 'get_profile_section acepta profile, experience, education, skills o projects y lee el JSON correspondiente del conocimiento profesional.',
      caveat: 'Es una consulta directa de datos curados, no una búsqueda vectorial ni una verificación externa del CV.',
      flow: ['Sección solicitada', 'Archivo JSON', 'Datos y fuente'],
    },
    en: {
      title: 'Structured profile',
      why: 'A focused question does not require searching the entire résumé: the agent can request one exact section.',
      how: 'get_profile_section accepts profile, experience, education, skills or projects and reads the corresponding professional-knowledge JSON file.',
      caveat: 'This is a direct lookup of curated data, not vector search or an external verification of the résumé.',
      flow: ['Requested section', 'JSON file', 'Data and source'],
    },
  },
  experience: {
    icon: 'i-lucide-briefcase-business', technologies: ['Keyword scoring', 'ES / EN aliases', 'Python'],
    source: 'backend/services/knowledge_service.py',
    es: {
      title: 'Búsqueda de experiencia',
      why: 'Permite localizar proyectos relacionados con una tecnología sin enviar todo el historial profesional en cada consulta.',
      how: 'search_experience normaliza palabras, añade equivalencias español-inglés y puntúa coincidencias en títulos, tecnologías y contenido.',
      caveat: 'Esta búsqueda usa palabras clave, no embeddings. No comprende cualquier sinónimo: para significado semántico existe search_documents.',
      flow: ['Palabras de consulta', 'Coincidencias puntuadas', 'Experiencia relevante'],
    },
    en: {
      title: 'Experience search',
      why: 'It finds projects related to a technology without sending the entire professional history on every lookup.',
      how: 'search_experience normalizes words, expands Spanish-English aliases and scores matches in titles, technologies and content.',
      caveat: 'This is keyword search, not embeddings. It cannot understand every synonym; search_documents provides semantic retrieval.',
      flow: ['Query terms', 'Scored matches', 'Relevant experience'],
    },
  },
  photo: {
    icon: 'i-lucide-image', technologies: ['Custom data parts', 'AI SDK', 'Vue'],
    source: 'app/src/components/chat/CandidatePhotoCard.vue',
    es: {
      title: 'Respuestas con componentes',
      why: 'Una respuesta no tiene por qué ser solo texto: el resultado de una herramienta puede convertirse en una tarjeta visual.',
      how: 'get_candidate_photo devuelve /jeyker.jpg. El backend envía un evento de imagen y Vue renderiza CandidatePhotoCard, separado del Markdown.',
      caveat: 'Es una foto existente. La herramienta no genera ni modifica imágenes.',
      flow: ['Herramienta de foto', 'Evento tipado', 'Tarjeta Vue'],
    },
    en: {
      title: 'Component-based answers',
      why: 'An answer need not be just text: a tool result can become a visual card.',
      how: 'get_candidate_photo returns /jeyker.jpg. The backend sends an image event and Vue renders CandidatePhotoCard separately from Markdown.',
      caveat: 'This is an existing photo. The tool does not generate or edit images.',
      flow: ['Photo tool', 'Typed event', 'Vue card'],
    },
  },
  sources: {
    icon: 'i-lucide-file-check-2', technologies: ['Source metadata', 'SSE', 'Deduplication'],
    source: 'backend/agents/activity.py',
    es: {
      title: 'Fuentes visibles',
      why: 'Puedes ver de dónde salió la información recuperada y contrastarla con los documentos originales.',
      how: 'El backend extrae los nombres de fuentes de los resultados de las herramientas, elimina duplicados y los envía como partes del mensaje.',
      caveat: 'La lista identifica documentos recuperados; no demuestra por sí sola que cada frase de la respuesta esté respaldada.',
      flow: ['Resultados de tools', 'Fuentes sin duplicados', 'Referencias en el chat'],
    },
    en: {
      title: 'Visible sources',
      why: 'You can see where retrieved information came from and compare it with the original documents.',
      how: 'The backend extracts source names from tool results, removes duplicates and streams them as message parts.',
      caveat: 'The list identifies retrieved documents; it does not by itself prove that every claim in the answer is supported.',
      flow: ['Tool results', 'Deduplicated sources', 'Chat references'],
    },
  },
  streaming: {
    icon: 'i-lucide-radio', technologies: ['FastAPI', 'HTTP / SSE', 'AI SDK'],
    source: 'backend/services/ai_sdk_stream.py',
    es: {
      title: 'Streaming en tiempo real',
      why: 'Puedes empezar a leer mientras la respuesta se está generando, en lugar de esperar al mensaje completo.',
      how: 'FastAPI adapta los fragmentos del modelo y los eventos de actividad al protocolo de AI SDK. Vue actualiza el mensaje conforme llegan por HTTP/SSE.',
      caveat: 'Mejora la espera percibida, pero no implica que el modelo termine antes ni que consuma menos tokens.',
      flow: ['Fragmentos del modelo', 'Eventos SSE', 'Texto progresivo'],
    },
    en: {
      title: 'Real-time streaming',
      why: 'You can start reading while the answer is still being generated instead of waiting for the complete message.',
      how: 'FastAPI adapts model chunks and activity events to the AI SDK protocol. Vue updates the message as they arrive over HTTP/SSE.',
      caveat: 'It improves perceived waiting time, but does not mean the model finishes sooner or uses fewer tokens.',
      flow: ['Model chunks', 'SSE events', 'Progressive text'],
    },
  },
  uploads: {
    icon: 'i-lucide-shield-check', technologies: ['pypdf', 'In-memory ChromaDB', 'TTL'],
    source: 'backend/services/vector_store_service.py',
    es: {
      title: 'PDF temporal',
      why: 'Puedes aportar contexto a la conversación sin convertir tu documento en parte permanente del perfil de Jeyker.',
      how: 'pypdf extrae texto seleccionable. Sus fragmentos se indexan en ChromaDB en memoria, separados del perfil persistente; la búsqueda filtra por los IDs adjuntos a la petición.',
      caveat: 'El texto se envía a Google para embeddings y contexto del modelo. La limpieza por caducidad ocurre en la siguiente carga o búsqueda; el valor por defecto es 30 minutos de inactividad. Los escaneos requieren OCR previo.',
      flow: ['PDF y extracción', 'Índice temporal', 'Filtro por adjuntos'],
    },
    en: {
      title: 'Temporary PDF',
      why: 'You can add context without making your document a permanent part of Jeyker’s profile.',
      how: 'pypdf extracts selectable text. Its chunks are indexed in memory with ChromaDB, separately from the persistent profile; retrieval filters by the document IDs attached to the request.',
      caveat: 'Text is sent to Google for embeddings and model context. Expired uploads are cleaned on the next upload or search; the default is 30 idle minutes. Scans require OCR first.',
      flow: ['PDF extraction', 'Temporary index', 'Attachment filter'],
    },
  },
} as const satisfies Record<string, Feature>

export type FeatureId = keyof typeof features
export const toolFeatures: Record<string, FeatureId> = {
  get_candidate_photo: 'photo', get_profile_section: 'profile',
  search_experience: 'experience', search_documents: 'rag',
}

export const insightCopy = {
  es: {
    activity: 'Actividad del agente', model: 'Consultando el modelo',
    running: 'En curso', completed: 'Completado', error: 'Error', interrupted: 'Interrumpido',
    results: 'resultados', observed: 'Pasos observables, no pensamiento interno del modelo. No se muestran prompts, argumentos ni contenido privado de documentos.',
    discoveries: 'Acabas de ver estas funciones en acción', why: '¿Por qué este feature es tan cool?',
    how: 'Cómo funciona', caveat: 'Qué conviene saber', code: 'Ver el código',
    noTools: 'No se ha observado ninguna llamada a herramientas en esta respuesta.',
  },
  en: {
    activity: 'Agent activity', model: 'Consulting the model',
    running: 'Running', completed: 'Completed', error: 'Error', interrupted: 'Interrupted',
    results: 'results', observed: 'Observable steps, not the model’s internal thinking. Prompts, arguments and private document content are not shown.',
    discoveries: 'You just saw these features in action', why: 'Why is this feature so cool?',
    how: 'How it works', caveat: 'Worth knowing', code: 'Explore the code',
    noTools: 'No tool calls have been observed in this response.',
  },
} as const

export function featureSourceUrl(feature: FeatureId): string {
  return `https://github.com/JeykerSalinas/awesome-ai-profile/blob/develop/${features[feature].source}`
}
