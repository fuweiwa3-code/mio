"""Regression tests for classification cancel lifecycle and per-turn isolation.

Tests go through ConversationService.stream_turn to verify the real
prepare → classify → cancel → release lifecycle.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest

from mio.api.schemas import MessageCreate
from mio.classification.exceptions import ClassificationCancelledError, ClassificationProviderError


async def _drain(stream):
    return [e async for e in stream]


# ── Helpers ────────────────────────────────────────────────────────


def _valid_json(
    emotion: str = "calm", intent: str = "companion", risk: str = "none"
) -> str:
    import json
    return json.dumps({
        "emotion": {"label": emotion, "confidence": 0.9},
        "intent": {"label": intent, "confidence": 0.85},
        "risk": {"level": risk, "confidence": 0.95},
    })


def _ok_response(content: str) -> dict:
    return {
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "model": "m",
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


# ── A. Cancel before classify (prepare ensures Event exists) ──────


class TestCancelBeforeClassify:
    """cancel() after prepare() but before classify() must prevent HTTP."""

    async def test_cancel_after_prepare_no_http(self, app, client) -> None:
        """message.started → cancel → message.cancelled.  HTTP handler never called."""
        from mio.agent.graph import create_agent_graph
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )
        from mio.llm.mock import MockChatModelProvider

        http_called = False

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal http_called
            http_called = True
            return httpx.Response(200, json=_ok_response(_valid_json()))

        oai_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=oai_client,
        )
        provider = MockChatModelProvider()
        graph = create_agent_graph(provider, classifier)

        created = await client.post("/api/v1/conversations", json={})
        cid = created.json()["id"]
        service = app.state.conversation_service
        old_c, old_g = service._classifier, service._agent_graph
        service._classifier = classifier
        service._agent_graph = graph

        try:
            turn = await service.start_turn(
                conversation_id=UUID(cid),
                payload=MessageCreate(content="测试", source="text"),
            )
            stream = service.stream_turn(turn)

            started = await anext(stream)
            assert started["event"] == "message.started"

            # Cancel immediately — classify hasn't run yet.
            resp = await client.post(
                f"/api/v1/chat/requests/{turn.request_id}/cancel"
            )
            assert resp.status_code == 200

            remaining = await _drain(stream)
            names = [e["event"] for e in remaining]

            assert names == ["message.cancelled"], f"got: {names}"
            assert http_called is False

            history = await client.get(f"/api/v1/conversations/{cid}/messages")
            assert history.json()["items"][-1]["status"] == "cancelled"

            assert turn.request_id not in classifier._cancel_events
            assert turn.request_id not in classifier._active_tasks

            # Next turn works.
            next_turn = await service.start_turn(
                conversation_id=UUID(cid),
                payload=MessageCreate(content="继续", source="text"),
            )
            next_events = await _drain(service.stream_turn(next_turn))
            assert any(e["event"] == "message.completed" for e in next_events)
        finally:
            service._classifier = old_c
            service._agent_graph = old_g
            await classifier.aclose()


# ── B. Cancel during HTTP classification ──────────────────────────


class TestCancelDuringHTTPClassification:
    """cancel() while HTTP is in-flight must abort within 2s."""

    async def test_cancel_during_http(self, app, client) -> None:
        from mio.agent.graph import create_agent_graph
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )
        from mio.llm.mock import MockChatModelProvider

        request_started = asyncio.Event()
        call_count = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                request_started.set()
                await asyncio.sleep(60)
            return httpx.Response(200, json=_ok_response(_valid_json()))

        oai_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=oai_client,
        )
        provider = MockChatModelProvider()
        graph = create_agent_graph(provider, classifier)

        created = await client.post("/api/v1/conversations", json={})
        cid = created.json()["id"]
        service = app.state.conversation_service
        old_c, old_g = service._classifier, service._agent_graph
        service._classifier = classifier
        service._agent_graph = graph

        try:
            turn = await service.start_turn(
                conversation_id=UUID(cid),
                payload=MessageCreate(content="测试HTTP取消", source="text"),
            )
            stream_task = asyncio.ensure_future(_drain(service.stream_turn(turn)))

            await asyncio.wait_for(request_started.wait(), timeout=2.0)

            resp = await client.post(
                f"/api/v1/chat/requests/{turn.request_id}/cancel"
            )
            assert resp.status_code == 200

            events = await asyncio.wait_for(stream_task, timeout=3.0)
            names = [e["event"] for e in events]

            assert names[0] == "message.started"
            assert names[-1] == "message.cancelled"
            assert "message.completed" not in names
            assert "message.failed" not in names

            history = await client.get(f"/api/v1/conversations/{cid}/messages")
            assert history.json()["items"][-1]["status"] == "cancelled"

            assert turn.request_id not in classifier._cancel_events
            assert turn.request_id not in classifier._active_tasks
        finally:
            service._classifier = old_c
            service._agent_graph = old_g
            await classifier.aclose()


# ── C. Normal completion resource cleanup ─────────────────────────


class TestNormalCompletionCleanup:
    """20 sequential classifications — no task/event leaks."""

    async def test_no_leak_after_20_runs(self) -> None:
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_ok_response(_valid_json()))

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )

        for i in range(20):
            rid = uuid4()
            await classifier.prepare(rid)
            result = await classifier.classify(f"msg-{i}", request_id=rid)
            assert result.emotion.label is not None
            await classifier.release(rid)
            assert rid not in classifier._cancel_events
            assert rid not in classifier._active_tasks

        assert len(classifier._cancel_events) == 0
        assert len(classifier._active_tasks) == 0
        await classifier.aclose()


# ── D. HTTP error resource cleanup ────────────────────────────────


class TestHTTPErrorCleanup:
    """HTTP 500 → ClassificationProviderError, tasks cleaned up."""

    async def test_http_500_cleanup(self) -> None:
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "fail"})

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        rid = uuid4()
        await classifier.prepare(rid)
        with pytest.raises(ClassificationProviderError):
            await classifier.classify("test", request_id=rid)
        await classifier.release(rid)
        assert rid not in classifier._cancel_events
        assert rid not in classifier._active_tasks
        await classifier.aclose()


# ── E. aclose interrupts active classification ────────────────────


class TestAcloseInterruptsActive:
    """aclose() must abort in-flight classify within 2s."""

    async def test_aclose_aborts_inflight(self) -> None:
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        request_started = asyncio.Event()

        async def handler(request: httpx.Request) -> httpx.Response:
            request_started.set()
            await asyncio.sleep(60)
            return httpx.Response(200, json=_ok_response(_valid_json()))

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        rid = uuid4()
        await classifier.prepare(rid)

        task = asyncio.create_task(classifier.classify("test", request_id=rid))
        await asyncio.wait_for(request_started.wait(), timeout=2.0)

        await asyncio.wait_for(classifier.aclose(), timeout=2.0)

        with pytest.raises(ClassificationCancelledError):
            await asyncio.wait_for(task, timeout=2.0)

        assert len(classifier._cancel_events) == 0
        assert len(classifier._active_tasks) == 0


# ── F. Per-turn isolation ─────────────────────────────────────────


class TestPerTurnIsolation:
    """Two consecutive turns use independent classifications."""

    async def test_crisis_then_normal(self, app, client) -> None:
        created = await client.post("/api/v1/conversations", json={})
        cid = created.json()["id"]
        service = app.state.conversation_service

        turn1 = await service.start_turn(
            conversation_id=UUID(cid),
            payload=MessageCreate(content="我不想活了", source="text"),
        )
        events1 = await _drain(service.stream_turn(turn1))
        completed1 = [e for e in events1 if e["event"] == "message.completed"]
        assert len(completed1) == 1
        text1 = completed1[0]["display_text"]
        assert "安全" in text1 or "紧急" in text1 or "联系" in text1

        turn2 = await service.start_turn(
            conversation_id=UUID(cid),
            payload=MessageCreate(content="你好呀", source="text"),
        )
        events2 = await _drain(service.stream_turn(turn2))
        completed2 = [e for e in events2 if e["event"] == "message.completed"]
        assert len(completed2) == 1
        text2 = completed2[0]["display_text"]
        assert "紧急" not in text2

    async def test_unsafe_then_reminder(self, app, client) -> None:
        created = await client.post("/api/v1/conversations", json={})
        cid = created.json()["id"]
        service = app.state.conversation_service

        turn1 = await service.start_turn(
            conversation_id=UUID(cid),
            payload=MessageCreate(content="想自残", source="text"),
        )
        events1 = await _drain(service.stream_turn(turn1))
        completed1 = [e for e in events1 if e["event"] == "message.completed"]
        text1 = completed1[0]["display_text"]
        assert "紧急" in text1 or "安全" in text1

        turn2 = await service.start_turn(
            conversation_id=UUID(cid),
            payload=MessageCreate(content="提醒我明天开会", source="text"),
        )
        events2 = await _drain(service.stream_turn(turn2))
        completed2 = [e for e in events2 if e["event"] == "message.completed"]
        assert "紧急" not in completed2[0]["display_text"]


# ── F (cont). Mock cancel regression ──────────────────────────────


class TestMockCancelLifecycle:
    """Mock classifier prepare/cancel/release lifecycle."""

    async def test_prepare_cancel_classify_raises(self) -> None:
        from mio.classification.mock import MockMessageClassifier

        c = MockMessageClassifier()
        rid = uuid4()
        await c.prepare(rid)
        await c.cancel(rid)
        with pytest.raises(ClassificationCancelledError):
            await c.classify("test", request_id=rid)
        await c.release(rid)
        assert rid not in c._cancel_events

    async def test_release_idempotent(self) -> None:
        from mio.classification.mock import MockMessageClassifier

        c = MockMessageClassifier()
        rid = uuid4()
        await c.prepare(rid)
        await c.release(rid)
        await c.release(rid)  # no-op
        assert rid not in c._cancel_events

    async def test_classify_without_prepare_creates_event(self) -> None:
        from mio.classification.mock import MockMessageClassifier

        c = MockMessageClassifier()
        rid = uuid4()
        result = await c.classify("你好", request_id=rid)
        assert result.emotion.label is not None
        await c.release(rid)
        assert rid not in c._cancel_events


# ── F (cont). Graph-level ClassificationCancelledError ─────────────


class TestGraphCancelledError:
    """Graph catches ClassificationCancelledError → fallback, not failed."""

    async def test_cancelled_produces_fallback(self) -> None:
        from mio.agent.graph import AgentState, create_agent_graph, stream_agent_events
        from mio.classification.mock import MockMessageClassifier
        from mio.llm.base import ChatModelProvider

        class SpyProvider(ChatModelProvider):
            name = "spy"

            def __init__(self) -> None:
                self.stream_called = False

            async def stream(self, request_id, messages, options) -> AsyncIterator[str]:
                self.stream_called = True
                yield "spy"

            async def cancel(self, request_id) -> None:
                pass

        class PreCancelledClassifier(MockMessageClassifier):
            name = "pre_cancelled"

            async def classify(self, text, *, request_id):
                raise ClassificationCancelledError("test")

        provider = SpyProvider()
        classifier = PreCancelledClassifier()
        graph = create_agent_graph(provider, classifier)

        state: AgentState = {
            "request_id": uuid4(),
            "current_user_text": "test",
            "profile": {
                "name": "澪",
                "relationship_type": "稳定陪伴者",
                "speaking_style": "清冷慢热",
                "boundaries": ["不冒充真人"],
            },
            "history": [],
            "model": "test",
            "display_text": "",
            "status": "pending",
            "node_summary": {},
            "classification_status": "success",
            "classification_error_code": "",
            "route": "",
        }

        events: list[dict[str, Any]] = [
            e async for e in stream_agent_events(graph, state)
        ]
        completed = next(e for e in events if e["event"] == "agent.completed")
        assert completed["route"] == "persona"
        assert completed["classification_status"] == "fallback"
        assert provider.stream_called is True
        assert "message.failed" not in [e["event"] for e in events]
