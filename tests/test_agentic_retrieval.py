"""Loop-control-logic tests for LLMClient.chat_agentic (app/clients/
llm_client.py) — the ReAct-style loop the agentic retrieval architecture
(app/retrieval/agentic.py) is built on. Mocks the OpenAI SDK response
shape directly, no real Neo4j, no real LLM call — mirrors
tests/test_traversal.py's pattern of testing only the control flow
(termination, max-turns, error handling, trace shape), not any real
model's actual tool-use quality.

Run: python -m unittest tests.test_agentic_retrieval -v
"""
from __future__ import annotations

import json
import os
import unittest
from unittest.mock import MagicMock

os.environ.setdefault("NEBIUS_API_KEY", "test")

from app.clients.llm_client import LLMClient, Role


class FakeFunction:
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


class FakeToolCall:
    def __init__(self, call_id: str, name: str, arguments: dict):
        self.id = call_id
        self.function = FakeFunction(name, json.dumps(arguments))

    def model_dump(self) -> dict:
        return {"id": self.id, "function": {"name": self.function.name,
                                            "arguments": self.function.arguments}}


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class FakeUsage:
    def __init__(self, prompt_tokens: int = 10, completion_tokens: int = 5):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class FakeResponse:
    def __init__(self, message: FakeMessage):
        self.choices = [type("C", (), {"message": message})()]
        self.usage = FakeUsage()


def _client_with_responses(responses: list[FakeResponse]) -> LLMClient:
    client = LLMClient(Role.ANSWER_ENGINE)
    create = MagicMock(side_effect=responses)
    client._client = MagicMock()
    client._client.with_options.return_value.chat.completions.create = create
    return client, create


_TOOLS = [{"name": "search", "description": "search", "input_schema": {"type": "object", "properties": {}}}]


class AgenticLoopTests(unittest.TestCase):
    def test_terminates_on_submit_answer_before_max_turns(self):
        responses = [
            FakeResponse(FakeMessage(tool_calls=[FakeToolCall("c1", "search", {"query": "x"})])),
            FakeResponse(FakeMessage(tool_calls=[FakeToolCall("c2", "submit_answer",
                        {"answer_text": "done", "citations": []})])),
        ]
        client, create = _client_with_responses(responses)
        tool_fn = MagicMock(return_value={"results": ["hit"]})

        result, trace, usage = client.chat_agentic("sys", "prompt", _TOOLS, tool_fn, max_turns=6)

        self.assertEqual(result, {"answer_text": "done", "citations": []})
        self.assertEqual(len(trace), 1)
        self.assertEqual(trace[0]["tool"], "search")
        self.assertEqual(create.call_count, 2)
        self.assertEqual(usage, {"input_tokens": 20, "output_tokens": 10})

    def test_hits_max_turns_with_no_terminal_call(self):
        # Every turn searches again, never submits — the loop must stop
        # at max_turns rather than running forever.
        responses = [
            FakeResponse(FakeMessage(tool_calls=[FakeToolCall(f"c{i}", "search", {"query": "x"})]))
            for i in range(3)
        ]
        client, create = _client_with_responses(responses)
        tool_fn = MagicMock(return_value={"results": []})

        result, trace, usage = client.chat_agentic("sys", "prompt", _TOOLS, tool_fn, max_turns=3)

        self.assertIsNone(result)
        self.assertEqual(len(trace), 3)
        self.assertEqual(create.call_count, 3)

    def test_tool_execution_error_feeds_back_instead_of_raising(self):
        responses = [
            FakeResponse(FakeMessage(tool_calls=[FakeToolCall("c1", "search", {"query": "x"})])),
            FakeResponse(FakeMessage(tool_calls=[FakeToolCall("c2", "submit_answer",
                        {"answer_text": "done", "citations": []})])),
        ]
        client, _create = _client_with_responses(responses)
        tool_fn = MagicMock(side_effect=RuntimeError("store unavailable"))

        result, trace, _usage = client.chat_agentic("sys", "prompt", _TOOLS, tool_fn, max_turns=6)

        # The loop didn't crash — it reached submit_answer on the next turn.
        self.assertEqual(result, {"answer_text": "done", "citations": []})
        self.assertEqual(len(trace), 1)
        self.assertIn("error", trace[0]["output"])
        self.assertIn("store unavailable", trace[0]["output"]["error"])

    def test_no_tool_call_turn_nudges_instead_of_losing_the_turn(self):
        responses = [
            FakeResponse(FakeMessage(content="I'm thinking...", tool_calls=[])),
            FakeResponse(FakeMessage(tool_calls=[FakeToolCall("c1", "submit_answer",
                        {"answer_text": "done", "citations": []})])),
        ]
        client, create = _client_with_responses(responses)
        tool_fn = MagicMock()

        result, trace, _usage = client.chat_agentic("sys", "prompt", _TOOLS, tool_fn, max_turns=6)

        self.assertEqual(result, {"answer_text": "done", "citations": []})
        self.assertEqual(create.call_count, 2)
        tool_fn.assert_not_called()

    def test_trace_entries_are_ordered_and_one_per_real_tool_call(self):
        responses = [
            FakeResponse(FakeMessage(tool_calls=[FakeToolCall("c1", "search", {"query": "a"})])),
            FakeResponse(FakeMessage(tool_calls=[FakeToolCall("c2", "search", {"query": "b"})])),
            FakeResponse(FakeMessage(tool_calls=[FakeToolCall("c3", "submit_answer",
                        {"answer_text": "done", "citations": []})])),
        ]
        client, _create = _client_with_responses(responses)
        tool_fn = MagicMock(side_effect=[{"results": ["r1"]}, {"results": ["r2"]}])

        _result, trace, _usage = client.chat_agentic("sys", "prompt", _TOOLS, tool_fn, max_turns=6)

        self.assertEqual([t["input"]["query"] for t in trace], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
