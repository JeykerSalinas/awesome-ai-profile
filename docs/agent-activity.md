# Agent activity and contextual feature explanations

## What the visitor sees

Each assistant message can show an expandable **Agent activity / Actividad del agente** panel. It lists actual model and tool executions, their status, elapsed time and (for searches) the number of returned results. Calls with no results display **0**, not success evidence that was never found. A completed tool call means execution succeeded, not that its answer has been independently verified.

The first observed use of a feature in the current conversation adds an expandable **Why is this feature so cool? / ¿Por qué este feature es tan cool?** button. It stays with that message, can be reopened, and follows the selected EN/ES locale. Repeated uses do not add another introduction. Nothing opens automatically or sends a chat message.

Eight explanations cover tool calling, semantic RAG, structured profile lookup, keyword experience search, photo components, sources, streaming and temporary PDF uploads. The content names the actual implementation: **ChromaDB and Gemini embeddings**, not pgvector. It distinguishes keyword search from vector search, existing photos from image generation, and retrieved sources from proof of correctness.

## Observable execution is not private thinking

The panel does **not** expose chain of thought or claim to show a model's inner reasoning. Its model rows mean a model request started/finished. No hidden prompts, raw tool arguments, complete outputs, document excerpts, provider metadata or thought signatures are copied into activity events. Structured reasoning/thought blocks are excluded from answer text too. A future provider-supported public summary would need its own explicitly labeled contract; it must not silently become raw reasoning output.

Explanations are editorial data shipped with the frontend. Opening them consumes no extra LLM tokens and makes no API call. Activity lives in the current in-memory conversation, with no new server logging, analytics service or browser persistence. Existing source chips may contain an uploaded filename; they do not contain its text. The normal RAG still sends text to Google for embeddings and answer context, as explained in the upload card.

## Architecture

1. `backend/agents/agent.py` creates the Gemini/LangChain agent with the four retrieval/photo tools and the harmless `offer_contact` UI tool. It delegates streaming to `agents/activity.py`. Contact offers do not send mail; see [contact flow](contact-flow.md).
2. `observe_agent_stream` consumes LangChain `astream_events(..., version="v2")`, filtered to chat model and tool events. Known tool names are allowlisted. Run IDs distinguish repeated or concurrent calls. Time is measured with a monotonic clock. Normal tool outputs still produce the existing photo and source events, with deduplication.
3. `backend/agents/events.py` defines the public internal event types. The public activity payload contains only `id`, `kind`, `status`, optional `tool_name`, `duration_ms` and `result_count`.
4. `services/ai_sdk_stream.py` translates activity into `data-agent-activity`. Running and terminal updates share the same data-part ID, allowing AI SDK to update one row. Activity updates do not close an active text block, preserving streamed Markdown. `data-feature-used` marks streaming only after a public text chunk actually arrives.
5. `app/src/types/chat.ts` types these custom message parts. `features/insights/activity.ts` derives the timeline and first-use feature map from message history. Regenerating/removing messages naturally recomputes discovery without stale global flags. Mere model text saying “I used RAG” cannot trigger a discovery.
6. `useFeatureDiscovery` provides that map to the message components. `AgentActivityPanel`, `FeatureDiscoveries` and `FeatureExplainer` own rendering, disclosure state and styling. `MainView` only provides history and identifies the currently streaming message.

The original guided tour remains independent and retains its existing lifecycle. `ChatStreamRequest.to_agent_messages()` still forwards text only; activity and explanation metadata are not added to future prompts.

## Errors, stopping and compatibility

- A successful search can have zero results. Failed calls never unlock a successful retrieval explanation.
- Unknown tools and malformed JSON outputs are not copied verbatim into the public stream.
- Runtime exceptions close outstanding activity rows as errors before the stream returns a generic failure message. Exception text is not sent to the browser by the stream adapter.
- When the visitor stops a response or loses the stream, pending rows render as interrupted once that message is no longer active; historical spinners cannot continue indefinitely. This UI state does not claim that cancellation of a synchronous remote operation was confirmed.
- Non-streaming model implementations have a final-answer fallback without falsely triggering the streaming introduction.
- Photo rendering and Markdown deduplication are preserved. Existing messages without activity parts still render normally.
- Disclosures use native keyboard controls or buttons with `aria-expanded`/`aria-controls`; styling follows existing light/dark tokens. Spinner animation respects reduced-motion preferences.

## Testing

```sh
cd backend
python -m unittest discover -s tests -v

cd ../app
npm test
npm run build
```

The tests exercise real LangChain agent execution with a deterministic fake model and local tools (no Google calls), lifecycle ordering, parallel calls, error propagation, private-output filtering, zero results, duplicate photos, SSE ordering and metadata exclusion from history. Frontend tests also use the actual AI SDK stream reader to verify data-part reconciliation, feature discovery, retry behavior, EN/ES copy and code links. Existing RAG, Markdown-photo and tour tests remain in the suite.

Manual verification after deploying the backend and frontend together:

1. Ask for Jeyker's photo. Observe the photo tool, one photo card and the contextual introductions.
2. Upload a text-based PDF and ask to compare it with the profile. Look for `search_documents`, result count and RAG/source explanations. No-result searches must still show zero explicitly.
3. Ask a second question that uses the same feature. Its activity remains visible, but the first-use explanation remains only on the first message.
4. Stop a response, retry it, switch EN/ES, and operate disclosures with keyboard and on a narrow viewport.

## Extension points

To expose another tool, add it to the backend's public allowlist, give it a feature mapping and bilingual copy in `features/insights/catalog.ts`, and add tests. Do not derive feature detection from generated prose. Features with new output types need an explicit typed part rather than forwarding arbitrary provider events.

References: [LangChain event stream contract](https://reference.langchain.com/python/langchain-core/runnables/base/Runnable/astream_events), [AI SDK custom data reconciliation](https://ai-sdk.dev/docs/ai-sdk-ui/streaming-data).
