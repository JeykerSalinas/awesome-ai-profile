# Behind the chat — guided technology story

## Why a guided story?

Recruiters should be able to inspect the engineering behind the portfolio without knowing which technical questions to ask. This feature is an editorial layer over the real application, not a second chat and not a simulated agent run.

The seven chapters follow a visitor's experience:

| Chapter | What it explains | Evidence |
| --- | --- | --- |
| Interface | Reactive, typed chat components; Nuxt UI is not a Nuxt server | `app/src/views/MainView.vue` |
| Streaming | FastAPI adapts agent events to AI SDK HTTP/SSE messages | `backend/services/ai_sdk_stream.py` |
| RAG | Text extraction, overlapping chunks, embeddings, semantic search and source names | `backend/services/vector_store_service.py` |
| Temporary uploads | Separate persistent profile / in-memory visitor stores; ID filtering and lazy TTL cleanup | `backend/services/vector_store_service.py` |
| Tools | Named Python functions and custom frontend message rendering | `backend/agents/tools.py` |
| Localization | Browser-language detection, saved preferences and locale-aware requests | `app/src/composables/useLocale.ts` |
| Delivery | Automated frontend delivery; command-driven Docker/Azure backend deployment | `Makefile` |

No claim is made that contact workflows, enforced approvals, OCR or automated backend deployment already exist. The privacy chapter explicitly explains that document text is processed by Google for embeddings and model context; memory-only application storage is not a promise of on-device processing. Expired uploads are cleaned during subsequent ingestion/search, not by a background timer.

## How it works

1. `MainView.vue` only composes the tour entry points and binds its chat draft to `TechnologyTourHost.vue`. `TechnologyTourLauncher.vue` owns both entry-point variants (welcome invitation / header icon), their translated labels and all invitation styles. The host owns open/loaded state, lazy loading, announcements and draft preparation, exposing only `openTour()` to the view. `defineAsyncComponent` loads the dialog implementation on first use. Nothing starts automatically.
2. `features/tour/story.ts` is the typed, bilingual chapter catalog. It contains the narrative, diagram labels, technologies, stable UI target and source path. `storyCopy` contains the controls. The existing `useLocale` preference remains the single language source.
3. `TechnologyTour.vue` opens a native `<dialog>` with `showModal()`. The browser provides modal focus containment and makes the underlying page inert. Escape and explicit controls close it. Opening remembers focus and scroll positions; closing/unmounting removes listeners and restores them.
4. Stable `data-tour` attributes identify the UI regions independently of layout classes or translated text. The target's viewport rectangle cuts a hole in a dimmed SVG layer. A border marks the highlighted region. These are geometrical UI effects, not screenshots or copies of the chat.
5. `placement.ts` prefers space beside, below or above the target. Missing anchors fall back to a centered card. Small screens use a bottom-aligned card with an independently scrollable body and visible navigation. Resize/scroll listeners and `ResizeObserver` keep measurements current, including while chat content changes.
6. CSS animates chapter entry, spotlight movement and packets across an illustrative three-node diagram. Diagrams are explicitly labeled as illustrations, run for a limited number of cycles, and make no API calls. The pause control and reduced-motion media query disable distracting movement.
7. The final action emits `prepareQuestion` to `TechnologyTourHost.vue`. The host appends the proposed text to its draft model, closes the dialog, focuses the composer and announces the change. Its `v-model:draft` binding updates the existing chat input without the view knowing the tour's lifecycle. Only the visitor's normal send action can call the chat API.

The tour does not modify backend behavior, document lifetime, chat history, deployment configuration or stored visitor data. Opening the tour while a response streams does not stop the response. Tour progress is deliberately not persisted; reopening starts a fresh, deterministic walkthrough.

## Add or change a chapter

- Update the English and Spanish content together in `story.ts`.
- Choose an existing stable target or add a `data-tour` attribute to a persistent UI region. Include empty-chat and active-chat states when a region is conditional.
- Link to an existing source file. Links currently target `main`, so they follow the released implementation after merging.
- Keep implementation claims factual; separate planned functionality from working features.
- The invitation count is derived from the catalog. If changing the chapter count, update the duration/copy and the count assertion in the tests.

## Verification

```bash
cd app
npm ci
npm run test:tour
npm run build
```

`test:tour` uses Node's built-in test runner and native TypeScript stripping, supported by the Node versions already required by the application. It checks source/anchor integrity, bilingual completeness, navigation boundaries, source URLs, missing targets, desktop placements, narrow/short viewports, draft preservation and the component separation contract. These are unit/content checks, not browser or accessibility certification.

Manual review checklist:

- Launch from the invitation and header, before and after sending a message.
- Navigate all chapters using buttons, progress controls and arrow keys; check both ends.
- Check EN/ES and light/dark variants, a 320px viewport, landscape and browser zoom.
- Check Tab/Shift+Tab containment, Escape, focus restoration and restored chat scroll.
- Pause animations, navigate again, and test the OS reduced-motion setting.
- Scroll a long chapter on a short screen; the next chapter should start at its heading.
- Open during streaming or with an attached PDF; closing must preserve both.
- Prepare the final question with an existing draft; it must append without sending.
- Confirm there are no network calls merely from navigating the tour, apart from loading its frontend assets.

## Deliberate tradeoffs

- Native dialog avoids another runtime dependency but targets the modern browsers supported by the Vue/Vite application.
- On very small screens the readable card may cover the spotlight. The chapter remains usable and its explanation does not depend on seeing the highlighted element.
- Chapter content is editorial, not generated by the LLM. Updating the underlying architecture should include reviewing the corresponding chapter.
- No autoplay or forced onboarding: visitors choose when to explore and how quickly to proceed.
