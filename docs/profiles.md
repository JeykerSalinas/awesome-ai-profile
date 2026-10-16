# Configuración por perfiles

Un mismo código sirve a dos despliegues de frontend y un backend compartido. `VITE_PROFILE_ID=jeyker` conserva Django; `VITE_PROFILE_ID=sara` selecciona Sara. Es una variable de **compilación**, no una opción que pueda cambiarse después de publicar los archivos estáticos.

## Archivos y precedencia

| Archivo | Responsabilidad |
| --- | --- |
| `backend/profiles/defaults/public.json` | Funciones, colores, analítica y textos compartidos |
| `backend/profiles/<id>/public.json` | Identidad, imágenes, textos y opciones públicas del perfil |
| `backend/profiles/defaults/agent.json` | Herramientas y servicios comunes |
| `backend/profiles/<id>/agent.json` | Nombre completo, contexto, contacto, instrucciones y servicios privados |
| `backend/knowledge/` | Datos verificados de Jeyker, conservados en su ubicación original |
| `backend/profiles/sara/knowledge/` | Datos verificados de Sara |

Los objetos se combinan recursivamente. Valores escalares, listas y `null` reemplazan el valor común; `false` desactiva una opción. La identidad, el contacto y el directorio de conocimiento se declaran por persona: no se heredan los de Jeyker para Sara. El backend valida campos, tipos, herramientas e identificadores al importar la configuración y falla si hay errores. Los archivos se almacenan en caché: reinicia el backend después de cambiarlos.

El frontend importa exclusivamente los archivos `public.json`; no importa `agent.json`, documentos ni credenciales. Todos los valores públicos pueden ser inspeccionados en el navegador. La ubicación bajo `backend/` permite incluir la configuración en la imagen Docker actual sin duplicarla entre aplicaciones. Para compilar el frontend es necesario el checkout completo del repositorio.

## Identidad, imágenes, colores y textos

Edita `public.json` del perfil. `assistantName` es el nombre del asistente, `candidateName` el nombre corto de la persona. `logo` configura el logotipo y favicon; `avatar` y `avatarDark` configuran los avatares. Con `null` se muestra la inicial. Guarda nuevos recursos en `app/public/profiles/<id>/` y usa rutas como `/profiles/sara/logo.svg`.

Sara utiliza el logo añadido en `app/public/sara_design/sara_logo.jpeg` y un acento rosa; sus avatares permanecen como inicial hasta configurarlos. Para modificar colores, añade propiedades CSS en `colors`, por ejemplo:

```json
{
  "colors": {
    "--color-django-red": "#7756a8",
    "--color-django-brown": "#291d38",
    "--color-django-cream": "#f6efff"
  }
}
```

Los nombres históricos de las variables se mantienen por compatibilidad. Consulta `app/src/assets/css/main.css` para ver todos los tokens. Los colores base alimentan los modos claro y oscuro; un override directo de `--django-page`, por ejemplo, se aplica a ambos modos.

`texts.en` y `texts.es` permiten reemplazar textos de la interfaz. Sus claves corresponden a `app/src/composables/useLocale.ts`. Las listas usan índices y el tour usa prefijos:

```json
{
  "texts": {
    "es": {
      "documentTitle": "Sara · Perfil profesional",
      "candidateRole": "Perfil profesional",
      "introduction": "Conoce mi trayectoria profesional.",
      "suggestions.0": "¿Cuál es la experiencia de Sara?",
      "chapters.interface.title": "Un perfil que conversa.",
      "chapters.interface.flow.0": "Interfaz personalizada"
    }
  }
}
```

Para el texto general del tour usa `tour.<clave>` según `storyCopy` en `app/src/features/tour/story.ts`; para capítulos, `chapters.<id>.<clave>`. Los textos no sobrescritos conservan el texto compartido con los nombres personalizados. Revisa afirmaciones personales y avisos al crear un nuevo perfil. Sara ya tiene presentación, sugerencias y rol neutrales; su tour está desactivado de inicio.

## Contexto y herramientas

`agent.json` contiene `candidate_name`, `knowledge_path` (relativa a `backend/`), `photo`, `contact`, `instructions`, `allowed_tools` y `services`. `instructions` amplía el prompt común; no sustituye sus reglas de veracidad. El contacto solo se publica si está configurado y el visitante lo solicita. La foto es una URL pública del frontend o un recurso remoto accesible.

Añade biografía, experiencia, educación, habilidades y proyectos siguiendo los JSON existentes. El índice RAG recorre JSON y Markdown bajo `knowledge_path`. Los PDF de visitantes se procesan a través de la función de documentos; no son el formato de los archivos permanentes de contexto. Sara tiene contexto y contacto vacíos hasta recibir datos verificados.

Las herramientas admitidas son `get_contact_details`, `get_candidate_photo`, `get_profile_section`, `search_experience` y `search_documents`. `allowed_tools` reemplaza la lista completa. Por ejemplo:

```json
{
  "instructions": "Usa un tono breve y cercano.",
  "allowed_tools": ["get_profile_section", "search_experience"]
}
```

Texto y voz usan la misma lista. La herramienta de foto solo se incluye si existe una foto configurada. El modelo no puede elegir otro perfil mediante los argumentos de las herramientas.

## Funciones

```json
{
  "features": {
    "voice": true,
    "documents": false,
    "tools": true,
    "tour": false
  }
}
```

- `voice`: oculta el acceso a voz y el backend rechaza el inicio WebSocket con código 1008.
- `documents`: oculta adjuntos; upload/delete y chat con adjuntos devuelven 403. Voz con adjuntos devuelve 1008. El RAG del perfil sigue disponible mediante `search_documents`; solo se desactivan los archivos del visitante.
- `tools`: impide registrar herramientas tanto en el agente de texto como en voz. Sin herramientas, no hay consulta de hechos profesionales.
- `tour`: controla los lanzadores y el montaje del tour, que es una función local del frontend.

Para que adjuntar PDF resulte útil, habilita también `tools` y `search_documents`. Los flags del frontend y backend deben publicarse desde la misma revisión: el servidor aplica la configuración aunque un cliente la manipule o use un bundle antiguo.

## Servicios y claves

Los servicios siguen siendo Gemini, Chroma y PostHog. Se pueden configurar sus parámetros y cuentas por perfil; esto no introduce proveedores alternativos.

Ejemplo de `services` privado en `sara/agent.json`:

```json
{
  "services": {
    "google_api_key_env": "SARA_GOOGLE_API_KEY",
    "vector_store_path": "/data/sara/chroma",
    "chat_model": "gemini-3.1-flash-lite",
    "embedding_model": "models/gemini-embedding-001",
    "live_model": "gemini-3.1-flash-live-preview",
    "live_voice": "Kore"
  }
}
```

Inyecta `SARA_GOOGLE_API_KEY` en el entorno del proceso del backend (por ejemplo, mediante un secreto de Azure Container Apps). Guarda solo el **nombre** de la variable en Git. No uses una variable `VITE_*` para secretos. Si se declara una variable específica y falta o está vacía, la petición falla; nunca toma silenciosamente la clave compartida. Para desarrollo local, exporta la variable antes de arrancar el backend.

Con `google_api_key_env: null` se usa `GOOGLE_API_KEY`. Los campos de almacenamiento, embeddings y voz en `null` usan los ajustes globales existentes. La clave seleccionada se aplica al chat, voz y embeddings. `chat_model` usa el valor común configurado. Los límites de PDF, TTL y turnos continúan siendo globales en `settings.py`.

Cada perfil usa colecciones Chroma y mapas de expiración separados, incluso si comparte directorio de almacenamiento. Los nombres de las colecciones de Jeyker no cambian; Sara lleva sufijo propio. Monta almacenamiento persistente para conservar índices entre reinicios. Cambiar el modelo de embeddings exige un directorio nuevo o reconstruir el índice con una dimensión compatible.

En `public.json`, `analytics.enabled: false` desactiva PostHog. `analytics.projectToken` y `analytics.host` permiten un proyecto distinto por perfil; `null` toma `VITE_POSTHOG_PROJECT_TOKEN` y `VITE_POSTHOG_HOST` del build. Usa únicamente el token público de captura de PostHog, nunca una clave personal o administrativa. Los eventos incluyen `profile_id` para distinguir perfiles que comparten proyecto.

`apiBaseUrl` permite un backend distinto por perfil; con `null` se utiliza `VITE_API_BASE_URL` y, en su defecto, `http://127.0.0.1:8000`.

## Publicar las dos instancias

Desde `app/`:

```sh
VITE_PROFILE_ID=jeyker npm run build
VITE_PROFILE_ID=sara npm run build
```

Cada build produce `app/dist`; publícalos por separado en sus respectivas Static Web Apps, con su propio token de despliegue. Para desarrollo usa `VITE_PROFILE_ID=sara npm run dev`. Agrega ambos orígenes a `CORS_ALLOW_ORIGINS` y a la política CORS del ingress de Container Apps, si existe. Publica el backend con los archivos actualizados y luego los frontends compatibles.

Este PR prepara ambas configuraciones, pero no crea recursos Azure, claves ni un segundo workflow de producción. Los perfiles son públicos: `profile_id` es selección de configuración, **no autenticación**. Un visitante puede seleccionar cualquiera de los perfiles admitidos. Las preferencias de navegador y el uso local de voz están separados por perfil; se conservan las claves antiguas de Jeyker.

## Validación y ampliación

La CI ejecuta pruebas de frontend, compilaciones de ambos perfiles y pruebas de backend sin llamadas reales a Gemini. Las pruebas cubren rechazo de perfiles desconocidos, separación de datos, selección de servicios, overrides y bloqueo de funciones en HTTP/WebSocket.

```sh
cd app
npm test
VITE_PROFILE_ID=sara npm run build
cd ../backend
GOOGLE_API_KEY=test-key python -m unittest discover -s tests
```

Para agregar un tercer perfil: crea sus archivos y conocimiento; registra el identificador en `ProfileId`/`PROFILE_IDS` del backend, en el registro y tipo del frontend y en la validación de `app/vite.config.ts`; amplía la matriz de CI y el tamaño de las cachés de perfiles/servicios. La lista explícita evita resolver rutas a partir de entradas arbitrarias del cliente.
