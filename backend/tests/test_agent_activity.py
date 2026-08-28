import json
import unittest

from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langchain_core.tools import tool

from agents.activity import observe_agent_stream


def event(kind, run_id, name="Gemini", **data):
    return {"event": kind, "run_id": run_id, "name": name, "data": data}


class EventAgent:
    def __init__(self, events, failure=None):
        self.events = events
        self.failure = failure

    async def astream_events(self, messages, **kwargs):
        assert kwargs == {"version": "v2", "include_types": ["chat_model", "tool"]}
        for item in self.events:
            yield item
        if self.failure:
            raise self.failure


class ToolCapableFakeModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


class AgentActivityTests(unittest.IsolatedAsyncioTestCase):
    async def collect(self, events):
        return [item async for item in observe_agent_stream(EventAgent(events), [{"role": "user", "content": "hello"}])]

    async def test_tool_lifecycle_counts_sources_and_privacy(self):
        payload = {"query": "private query", "results": [
            {"source": "offer.pdf", "content": "private document"},
            {"source": "offer.pdf", "content": "private document"},
        ]}
        result = await self.collect([
            event("on_tool_start", "t1", "search_documents", input={"query": "private query"}),
            event("on_tool_end", "t1", "search_documents", output=ToolMessage(content=json.dumps(payload), tool_call_id="c1")),
        ])
        self.assertEqual([item["type"] for item in result], ["activity", "activity", "source"])
        start, end = result[0]["data"], result[1]["data"]
        self.assertEqual(start["id"], end["id"])
        self.assertEqual((start["status"], end["status"]), ("running", "completed"))
        self.assertEqual(end["result_count"], 2)
        self.assertGreaterEqual(end["duration_ms"], 0)
        self.assertNotIn("private", json.dumps(result))

    async def test_parallel_calls_finish_independently_and_keep_zero_results(self):
        result = await self.collect([
            event("on_tool_start", "t1", "search_documents"),
            event("on_tool_start", "t2", "search_experience"),
            event("on_tool_end", "t2", "search_experience", output={"results": []}),
            event("on_tool_end", "t1", "search_documents", output={"results": []}),
        ])
        self.assertEqual([item["data"]["id"] for item in result], ["t1", "t2", "t2", "t1"])
        self.assertEqual(result[-1]["data"]["result_count"], 0)

    async def test_streams_only_public_text_without_duplicate_final_answer(self):
        chunk = AIMessageChunk(content=[
            {"type": "thinking", "thinking": "private reasoning"},
            {"type": "reasoning", "reasoning": "private reasoning"},
            {"type": "text", "text": "private thought", "thought": True},
            {"type": "text", "text": "Hello"},
        ])
        result = await self.collect([
            event("on_chat_model_start", "m1", input={"messages": "private prompt"}),
            event("on_chat_model_stream", "m1", chunk=chunk),
            event("on_chat_model_stream", "m1", chunk=AIMessageChunk(content=" there")),
            event("on_chat_model_end", "m1", output=AIMessage(content="Hello there")),
        ])
        self.assertEqual(''.join(item['text'] for item in result if item['type'] == 'message_delta'), 'Hello there')
        self.assertEqual(sum(item['type'] == 'feature' for item in result), 1)
        self.assertNotIn('private', json.dumps(result))

    async def test_non_streaming_model_fallback_does_not_claim_token_streaming(self):
        result = await self.collect([
            event("on_chat_model_start", "m1"),
            event("on_chat_model_end", "m1", output=AIMessage(content="Hello")),
        ])
        self.assertEqual(result[1], {"type": "message_delta", "text": "Hello"})
        self.assertFalse(any(item['type'] == 'feature' for item in result))

    async def test_deduplicates_photo_and_duplicate_end_events(self):
        result = await self.collect([
            event("on_tool_start", "t1", "get_candidate_photo"),
            event("on_tool_end", "t1", "get_candidate_photo", output="/jeyker.jpg"),
            event("on_tool_end", "t1", "get_candidate_photo", output="/jeyker.jpg"),
            event("on_tool_start", "t2", "get_candidate_photo"),
            event("on_tool_end", "t2", "get_candidate_photo", output="/jeyker.jpg"),
        ])
        self.assertEqual(sum(item['type'] == 'image' for item in result), 1)
        self.assertEqual(sum(item['type'] == 'activity' for item in result), 4)

    async def test_exposes_contact_lookup_lifecycle_without_contact_values(self):
        result = await self.collect([
            event("on_tool_start", "contact", "get_contact_details"),
            event(
                "on_tool_end",
                "contact",
                "get_contact_details",
                output='{"email":"jeyker.salinas13@gmail.com"}',
            ),
        ])
        self.assertEqual([item["type"] for item in result], ["activity", "activity"])
        self.assertNotIn("jeyker.salinas13", json.dumps(result))

    async def test_ignores_unknown_tools_and_malformed_payloads(self):
        for payload in ['not json', '[]', None, {"results": "not a list"}]:
            result = await self.collect([
                event("on_tool_start", "secret", "private_tool"),
                event("on_tool_end", "secret", "private_tool", output="private data"),
                event("on_tool_start", "t1", "search_documents"),
                event("on_tool_end", "t1", "search_documents", output=payload),
            ])
            self.assertEqual(len(result), 2)
            self.assertNotIn('private', json.dumps(result))

    async def test_error_results_do_not_emit_sources(self):
        result = await self.collect([
            event("on_tool_start", "t1", "search_documents"),
            event("on_tool_end", "t1", "search_documents", output=ToolMessage(
                content='{"source":"private-error"}', tool_call_id="c1", status="error")),
        ])
        self.assertEqual(result[-1]["data"]["status"], "error")
        self.assertNotIn('private', json.dumps(result))

    async def test_exception_finishes_pending_activities_before_propagation(self):
        result = []
        agent = EventAgent([event("on_tool_start", "t1", "search_documents")], RuntimeError("private-key"))
        with self.assertRaises(RuntimeError):
            async for item in observe_agent_stream(agent, []):
                result.append(item)
        self.assertEqual(result[-1]["data"]["status"], "error")
        self.assertNotIn('private-key', json.dumps(result))

    async def test_unfinished_stream_is_interrupted_not_completed(self):
        result = await self.collect([event("on_tool_start", "t1", "search_documents")])
        self.assertEqual(result[-1]["data"]["status"], "interrupted")

    async def test_real_langchain_agent_tool_lifecycle_without_network(self):
        @tool
        def search_documents(query: str) -> str:
            """Search a local fake knowledge base."""
            return json.dumps({"results": [{"source": "knowledge/profile.json", "content": "private excerpt"}]})

        model = ToolCapableFakeModel(responses=[
            AIMessage(content="", tool_calls=[{"name": "search_documents", "args": {"query": "Vue"}, "id": "call-1", "type": "tool_call"}]),
            AIMessage(content="A grounded answer."),
        ])
        agent = create_agent(model=model, tools=[search_documents])
        result = [item async for item in observe_agent_stream(agent, [{"role": "user", "content": "Vue experience?"}])]
        tool_events = [item['data'] for item in result if item['type'] == 'activity' and item['data']['kind'] == 'tool']
        self.assertEqual([item['status'] for item in tool_events], ['running', 'completed'])
        self.assertEqual(tool_events[-1]['result_count'], 1)
        self.assertIn({'type': 'source', 'path': 'knowledge/profile.json'}, result)
        self.assertEqual(''.join(item['text'] for item in result if item['type'] == 'message_delta'), 'A grounded answer.')
        self.assertNotIn('private excerpt', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
