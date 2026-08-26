"""Project LangChain lifecycle events into a minimal, safe public activity feed."""
import json
from collections.abc import AsyncIterator
from time import monotonic
from typing import Any

from agents.events import ActivityStatus, AgentActivityData, AgentStreamEvent

PUBLIC_TOOLS = frozenset({
    "get_candidate_photo", "get_profile_section", "search_experience", "search_documents",
    "offer_contact",
})


def visible_text(message: Any) -> str:
    """Only final-answer text blocks, never reasoning, thought signatures or metadata."""
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "".join(
        block["text"] for block in content
        if isinstance(block, dict) and block.get("type") == "text"
        and not block.get("thought") and isinstance(block.get("text"), str)
    )


def tool_payload(output: Any) -> dict[str, Any]:
    content = getattr(output, "content", output)
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except (ValueError, TypeError):
            return {}
    return content if isinstance(content, dict) else {}


async def observe_agent_stream(agent: Any, messages: list[dict[str, str]]) -> AsyncIterator[AgentStreamEvent]:
    pending: dict[str, tuple[AgentActivityData, float]] = {}
    finished: set[str] = set()
    text_runs: set[str] = set()
    emitted_sources: set[str] = set()
    emitted_photos: set[str] = set()
    streaming_observed = False
    contact_offered = False

    def finish(run_id: str, status: ActivityStatus, result_count: int | None = None) -> AgentStreamEvent:
        activity, started = pending.pop(run_id)
        finished.add(run_id)
        data: AgentActivityData = {**activity, "status": status, "duration_ms": max(0, round((monotonic() - started) * 1000))}
        if result_count is not None:
            data["result_count"] = result_count
        return {"type": "activity", "data": data}

    try:
        async for event in agent.astream_events(
            {"messages": messages}, version="v2", include_types=["chat_model", "tool"],
        ):
            event_type = event["event"]
            name = event.get("name", "")
            run_id = str(event["run_id"])
            data = event.get("data", {})
            is_tool = event_type.startswith("on_tool_")
            if is_tool and name not in PUBLIC_TOOLS:
                continue

            if event_type in {"on_chat_model_start", "on_tool_start"}:
                if run_id in pending or run_id in finished:
                    continue
                activity: AgentActivityData = {
                    "id": run_id, "kind": "tool" if is_tool else "model", "status": "running",
                }
                if is_tool:
                    activity["tool_name"] = name
                pending[run_id] = (activity, monotonic())
                yield {"type": "activity", "data": activity}

            elif event_type == "on_chat_model_stream":
                text = visible_text(data.get("chunk"))
                if text:
                    if not streaming_observed:
                        streaming_observed = True
                        yield {"type": "feature", "feature": "streaming"}
                    text_runs.add(run_id)
                    yield {"type": "message_delta", "text": text}

            elif event_type == "on_chat_model_end":
                # Integrations that do not stream tokens can still return an answer.
                if run_id not in text_runs:
                    text = visible_text(data.get("output"))
                    if text:
                        yield {"type": "message_delta", "text": text}
                if run_id in pending:
                    yield finish(run_id, "completed")

            elif event_type == "on_tool_end" and run_id in pending:
                output = data.get("output")
                if getattr(output, "status", None) == "error":
                    yield finish(run_id, "error")
                    continue
                payload = tool_payload(output)
                results = payload.get("results")
                results = results if isinstance(results, list) else None
                yield finish(run_id, "completed", len(results) if results is not None else None)

                if name == "offer_contact":
                    if payload.get("contact_offer") is True and not contact_offered:
                        contact_offered = True
                        yield {"type": "contact_offer"}
                    continue

                if name == "get_candidate_photo":
                    src = getattr(output, "content", output)
                    if src == "/jeyker.jpg" and src not in emitted_photos:
                        emitted_photos.add(src)
                        yield {"type": "image", "src": src, "alt": "Jeyker Salinas"}
                    continue

                sources = [payload.get("source")]
                sources.extend(result.get("source") for result in (results or []) if isinstance(result, dict))
                for source in sources:
                    if isinstance(source, str) and source and source not in emitted_sources:
                        emitted_sources.add(source)
                        yield {"type": "source", "path": source}

            elif event_type in {"on_tool_error", "on_chat_model_error"} and run_id in pending:
                yield finish(run_id, "error")
    except Exception:
        # Some LangChain versions propagate errors without an on_tool_error event.
        for run_id in list(pending):
            yield finish(run_id, "error")
        raise

    for run_id in list(pending):
        yield finish(run_id, "interrupted")
