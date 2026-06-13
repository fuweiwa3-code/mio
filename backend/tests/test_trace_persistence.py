"""Tests for AgentTrace classification field persistence (Phase 3).

Verifies that classification results are written to AgentTrace after each turn,
including normal, safety, fallback, cancelled, and historical-null scenarios.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import os
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import httpx

from mio.agent.graph import create_agent_graph
from mio.api.schemas import MessageCreate
from mio.classification.exceptions import (
    ClassificationProviderError,
    ClassificationSchemaInvalidError,
)
from mio.classification.mock import MockMessageClassifier
from mio.classification.models import ClassificationResult
from mio.db.models import AgentTrace
from mio.llm.base import ChatMessage, ChatModelProvider, ModelOptions
from mio.llm.mock import MockChatModelProvider
from mio.services.conversations import ConversationService

# ── Helpers ────────────────────────────────────────────────────────


async def _drain(stream):
    return [e async for e in stream]


class SpyProvider(ChatModelProvider):
    name = "spy"

    def __init__(self) -> None:
        self.stream_called = False
        self._cancelled: set[UUID] = set()

    async def stream(
        self,
        request_id: UUID,
        messages: list[ChatMessage],
        options: ModelOptions,
    ) -> AsyncIterator[str]:
        self.stream_called = True
        yield "spy response"

    async def cancel(self, request_id: UUID) -> None:
        self._cancelled.add(request_id)


class ProviderFailureClassifier(MockMessageClassifier):
    """Raises ClassificationProviderError on classify."""

    name = "provider_failure"

    async def classify(self, text: str, *, request_id: UUID) -> ClassificationResult:
        raise ClassificationProviderError("simulated provider failure")


class SchemaInvalidClassifier(MockMessageClassifier):
    """Raises ClassificationSchemaInvalidError on classify."""

    name = "schema_invalid"

    async def classify(self, text: str, *, request_id: UUID) -> ClassificationResult:
        raise ClassificationSchemaInvalidError("simulated schema invalid")


async def _get_trace(session_factory, trace_id: UUID) -> AgentTrace | None:
    async with session_factory() as session:
        return await session.get(AgentTrace, trace_id)


# ── Test: Normal persona route trace fields ────────────────────────


class TestNormalPersonaTraceFields:
    """Verify classification fields are persisted for normal persona turns."""

    async def test_calm_companion_trace_has_classification(
        self, app, client
    ) -> None:
        created = await client.post("/api/v1/conversations", json={})
        cid = created.json()["id"]
        service: ConversationService = app.state.conversation_service

        turn = await service.start_turn(
            conversation_id=UUID(cid),
            payload=MessageCreate(content="你好呀", source="text"),
        )
        events = await _drain(service.stream_turn(turn))
        assert any(e["event"] == "message.completed" for e in events)

        trace = await _get_trace(service._session_factory, turn.trace_id)
        assert trace is not None
        assert trace.emotion_label is not None
        assert trace.emotion_confidence is not None
        assert trace.intent_label is not None
        assert trace.intent_confidence is not None
        assert trace.risk_level is not None
        assert trace.risk_confidence is not None
        assert trace.classification_status == "success"
        assert trace.classification_error_code is None
        assert trace.route == "persona"
        assert trace.trace_schema_version == 2

    async def test_tired_emotion_trace_fields(self, app, client) -> None:
        created = await client.post("/api/v1/conversations", json={})
        cid = created.json()["id"]
        service: ConversationService = app.state.conversation_service

        turn = await service.start_turn(
            conversation_id=UUID(cid),
            payload=MessageCreate(content="好累啊，不想动", source="text"),
        )
        await _drain(service.stream_turn(turn))

        trace = await _get_trace(service._session_factory, turn.trace_id)
        assert trace is not None
        assert trace.emotion_label == "tired"
        assert trace.intent_label == "companion"
        assert trace.route == "persona"
        assert trace.classification_status == "success"

    async def test_knowledge_qa_intent_trace_fields(self, app, client) -> None:
        created = await client.post("/api/v1/conversations", json={})
        cid = created.json()["id"]
        service: ConversationService = app.state.conversation_service

        turn = await service.start_turn(
            conversation_id=UUID(cid),
            payload=MessageCreate(content="什么是Python的GIL", source="text"),
        )
        await _drain(service.stream_turn(turn))

        trace = await _get_trace(service._session_factory, turn.trace_id)
        assert trace is not None
        assert trace.intent_label == "knowledge_qa"
        assert trace.route == "persona"


# ── Test: Safety route trace fields ────────────────────────────────


class TestSafetyRouteTraceFields:
    """Verify classification fields for crisis/unsafe safety routes."""

    async def test_crisis_emotion_safety_trace(self, app, client) -> None:
        created = await client.post("/api/v1/conversations", json={})
        cid = created.json()["id"]
        service: ConversationService = app.state.conversation_service

        turn = await service.start_turn(
            conversation_id=UUID(cid),
            payload=MessageCreate(content="我不想活了", source="text"),
        )
        events = await _drain(service.stream_turn(turn))
        assert any(e["event"] == "message.completed" for e in events)

        trace = await _get_trace(service._session_factory, turn.trace_id)
        assert trace is not None
        assert trace.emotion_label == "crisis"
        assert trace.risk_level == "high"
        assert trace.route == "safety"
        assert trace.classification_status == "success"
        assert trace.classification_error_code is None
        assert trace.trace_schema_version == 2

    async def test_unsafe_intent_safety_trace(self, app, client) -> None:
        created = await client.post("/api/v1/conversations", json={})
        cid = created.json()["id"]
        service: ConversationService = app.state.conversation_service

        turn = await service.start_turn(
            conversation_id=UUID(cid),
            payload=MessageCreate(content="想自残", source="text"),
        )
        await _drain(service.stream_turn(turn))

        trace = await _get_trace(service._session_factory, turn.trace_id)
        assert trace is not None
        assert trace.intent_label == "unsafe"
        assert trace.risk_level == "high"
        assert trace.route == "safety"

    async def test_angry_emotion_persona_trace(self, app, client) -> None:
        """Angry emotion is medium risk → persona route, not safety."""
        created = await client.post("/api/v1/conversations", json={})
        cid = created.json()["id"]
        service: ConversationService = app.state.conversation_service

        turn = await service.start_turn(
            conversation_id=UUID(cid),
            payload=MessageCreate(content="气死我了", source="text"),
        )
        await _drain(service.stream_turn(turn))

        trace = await _get_trace(service._session_factory, turn.trace_id)
        assert trace is not None
        assert trace.emotion_label == "angry"
        assert trace.risk_level == "medium"
        assert trace.route == "persona"


# ── Test: Provider failure fallback trace fields ───────────────────


class TestProviderFailureFallbackTrace:
    """Verify fallback trace fields when classifier raises ClassificationProviderError."""

    async def test_provider_failure_fallback_trace(self, app, client) -> None:
        created = await client.post("/api/v1/conversations", json={})
        cid = created.json()["id"]
        service: ConversationService = app.state.conversation_service

        old_classifier = service._classifier
        old_graph = service._agent_graph
        provider = SpyProvider()
        classifier = ProviderFailureClassifier()
        graph = create_agent_graph(provider, classifier)
        service._classifier = classifier
        service._agent_graph = graph

        try:
            turn = await service.start_turn(
                conversation_id=UUID(cid),
                payload=MessageCreate(content="你好", source="text"),
            )
            events = await _drain(service.stream_turn(turn))
            assert any(e["event"] == "message.completed" for e in events)

            trace = await _get_trace(service._session_factory, turn.trace_id)
            assert trace is not None
            assert trace.emotion_label == "calm"
            assert trace.intent_label == "companion"
            assert trace.risk_level == "medium"
            assert trace.classification_status == "fallback"
            assert trace.classification_error_code == "classification_provider_error"
            assert trace.route == "persona"
            assert trace.trace_schema_version == 2
            assert provider.stream_called is True
        finally:
            service._classifier = old_classifier
            service._agent_graph = old_graph


# ── Test: Schema invalid fallback trace fields ─────────────────────


class TestSchemaInvalidFallbackTrace:
    """Verify fallback trace fields when classifier raises ClassificationSchemaInvalidError."""

    async def test_schema_invalid_fallback_trace(self, app, client) -> None:
        created = await client.post("/api/v1/conversations", json={})
        cid = created.json()["id"]
        service: ConversationService = app.state.conversation_service

        old_classifier = service._classifier
        old_graph = service._agent_graph
        provider = SpyProvider()
        classifier = SchemaInvalidClassifier()
        graph = create_agent_graph(provider, classifier)
        service._classifier = classifier
        service._agent_graph = graph

        try:
            turn = await service.start_turn(
                conversation_id=UUID(cid),
                payload=MessageCreate(content="你好", source="text"),
            )
            events = await _drain(service.stream_turn(turn))
            assert any(e["event"] == "message.completed" for e in events)

            trace = await _get_trace(service._session_factory, turn.trace_id)
            assert trace is not None
            assert trace.emotion_label == "calm"
            assert trace.intent_label == "companion"
            assert trace.risk_level == "medium"
            assert trace.classification_status == "fallback"
            assert trace.classification_error_code == "classification_schema_invalid"
            assert trace.route == "persona"
        finally:
            service._classifier = old_classifier
            service._agent_graph = old_graph


# ── Test: Cancelled trace fields ───────────────────────────────────


class TestCancelledTraceFields:
    """Verify trace is saved even when turn is cancelled."""

    async def test_cancel_during_classify_saves_trace(self, app, client) -> None:
        """Cancel during classify → fallback classification, trace saved."""
        import asyncio

        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        created = await client.post("/api/v1/conversations", json={})
        cid = created.json()["id"]
        service: ConversationService = app.state.conversation_service

        request_started = asyncio.Event()
        call_count = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                request_started.set()
                await asyncio.sleep(60)
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": json.dumps({
                                    "emotion": {"label": "calm", "confidence": 0.9},
                                    "intent": {"label": "companion", "confidence": 0.9},
                                    "risk": {"level": "none", "confidence": 0.9},
                                }),
                            }
                        }
                    ],
                    "model": "m",
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                },
            )

        oai_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=oai_client,
        )
        provider = MockChatModelProvider()
        graph = create_agent_graph(provider, classifier)

        old_classifier = service._classifier
        old_graph = service._agent_graph
        service._classifier = classifier
        service._agent_graph = graph

        try:
            turn = await service.start_turn(
                conversation_id=UUID(cid),
                payload=MessageCreate(content="测试取消", source="text"),
            )
            stream_task = asyncio.ensure_future(_drain(service.stream_turn(turn)))

            await asyncio.wait_for(request_started.wait(), timeout=2.0)

            resp = await client.post(
                f"/api/v1/chat/requests/{turn.request_id}/cancel"
            )
            assert resp.status_code == 200

            events = await asyncio.wait_for(stream_task, timeout=5.0)
            names = [e["event"] for e in events]
            assert names[0] == "message.started"
            assert names[-1] == "message.cancelled"

            trace = await _get_trace(service._session_factory, turn.trace_id)
            assert trace is not None
            assert trace.status == "cancelled"
            assert trace.trace_schema_version == 2
        finally:
            service._classifier = old_classifier
            service._agent_graph = old_graph
            await classifier.aclose()

    async def test_explicit_cancel_still_saves_trace(self, app, client) -> None:
        """Explicit cancel via registry → trace saved."""
        created = await client.post("/api/v1/conversations", json={})
        cid = created.json()["id"]
        service: ConversationService = app.state.conversation_service

        turn = await service.start_turn(
            conversation_id=UUID(cid),
            payload=MessageCreate(content="测试显式取消", source="text"),
        )
        stream = service.stream_turn(turn)
        started = await anext(stream)
        assert started["event"] == "message.started"

        await service.cancel(turn.request_id)
        remaining = await _drain(stream)
        assert remaining[-1]["event"] == "message.cancelled"

        trace = await _get_trace(service._session_factory, turn.trace_id)
        assert trace is not None
        assert trace.status == "cancelled"


# ── Test: Historical NULL trace compatibility ──────────────────────


class TestHistoricalNullTraceCompat:
    """Verify that AgentTrace with NULL classification fields is readable."""

    async def test_null_classification_fields_readable(self, app, client) -> None:
        """Simulate historical v1 trace with NULL classification fields."""
        service: ConversationService = app.state.conversation_service

        created = await client.post("/api/v1/conversations", json={})
        cid = created.json()["id"]

        # Insert a historical trace with NULL classification fields (v1 style)
        async with service._session_factory() as session:
            trace = AgentTrace(
                conversation_id=UUID(cid),
                request_id=uuid4(),
                status="completed",
                provider="mock",
                model="mock-mio",
                duration_ms=100,
                node_summary={
                    "load_context": "completed",
                    "build_persona_prompt": "completed",
                    "stream_llm": "completed",
                    "finalize_response": "completed",
                },
                # All classification fields left as NULL (default)
            )
            session.add(trace)
            await session.commit()
            trace_id = trace.id

        # Read it back — must not raise
        trace = await _get_trace(service._session_factory, trace_id)
        assert trace is not None
        assert trace.emotion_label is None
        assert trace.emotion_confidence is None
        assert trace.intent_label is None
        assert trace.intent_confidence is None
        assert trace.risk_level is None
        assert trace.risk_confidence is None
        assert trace.classification_status is None
        assert trace.classification_error_code is None
        assert trace.route is None
        assert trace.trace_schema_version is None  # historical: no version column

    async def test_new_trace_has_version_2(self, app, client) -> None:
        """New traces must have trace_schema_version=2."""
        created = await client.post("/api/v1/conversations", json={})
        cid = created.json()["id"]
        service: ConversationService = app.state.conversation_service

        turn = await service.start_turn(
            conversation_id=UUID(cid),
            payload=MessageCreate(content="你好", source="text"),
        )
        await _drain(service.stream_turn(turn))

        trace = await _get_trace(service._session_factory, turn.trace_id)
        assert trace is not None
        assert trace.trace_schema_version == 2


# ── Test: Node summary structured format ───────────────────────────


class TestNodeSummaryStructured:
    """Verify node_summary uses structured dict format."""

    async def test_persona_node_summary_structure(self, app, client) -> None:
        created = await client.post("/api/v1/conversations", json={})
        cid = created.json()["id"]
        service: ConversationService = app.state.conversation_service

        turn = await service.start_turn(
            conversation_id=UUID(cid),
            payload=MessageCreate(content="你好", source="text"),
        )
        await _drain(service.stream_turn(turn))

        trace = await _get_trace(service._session_factory, turn.trace_id)
        assert trace is not None
        ns = trace.node_summary
        assert "load_context" in ns
        assert "classify_message" in ns
        assert "build_persona_prompt" in ns
        assert "stream_llm" in ns
        assert "finalize_response" in ns

    async def test_safety_node_summary_structure(self, app, client) -> None:
        created = await client.post("/api/v1/conversations", json={})
        cid = created.json()["id"]
        service: ConversationService = app.state.conversation_service

        turn = await service.start_turn(
            conversation_id=UUID(cid),
            payload=MessageCreate(content="我不想活了", source="text"),
        )
        await _drain(service.stream_turn(turn))

        trace = await _get_trace(service._session_factory, turn.trace_id)
        assert trace is not None
        ns = trace.node_summary
        assert "classify_message" in ns
        assert "build_safety_response" in ns
        assert "stream_safety_response" in ns
        assert "finalize_response" in ns


# ── Test: Provider failure event still emits message.failed ────────


class TestProviderFailureEventRegression:
    """Ensure provider failure still emits message.failed (no regression)."""

    async def test_provider_failure_emits_failed(self, app, client) -> None:
        from mio.llm.base import ChatModelProvider

        class FailingProvider(ChatModelProvider):
            name = "failing"

            async def stream(
                self, request_id, messages, options
            ) -> AsyncIterator[str]:
                if False:
                    yield ""
                raise RuntimeError("provider unavailable")

            async def cancel(self, request_id) -> None:
                pass

        created = await client.post("/api/v1/conversations", json={})
        cid = created.json()["id"]
        service: ConversationService = app.state.conversation_service

        old_classifier = service._classifier
        old_graph = service._agent_graph
        provider = FailingProvider()
        classifier = MockMessageClassifier()
        graph = create_agent_graph(provider, classifier)
        service._classifier = classifier
        service._agent_graph = graph

        try:
            turn = await service.start_turn(
                conversation_id=UUID(cid),
                payload=MessageCreate(content="测试provider失败", source="text"),
            )
            events = await _drain(service.stream_turn(turn))
            assert events[0]["event"] == "message.started"
            assert events[-1]["event"] == "message.failed"

            trace = await _get_trace(service._session_factory, turn.trace_id)
            assert trace is not None
            assert trace.status == "failed"
            assert trace.error_code == "provider_error"
            # Classification succeeded before provider failed → fields saved
            assert trace.classification_status == "success"
            assert trace.emotion_label is not None
            assert trace.intent_label is not None
            assert trace.risk_level is not None
            assert trace.route == "persona"
            assert trace.trace_schema_version == 2
        finally:
            service._classifier = old_classifier
            service._agent_graph = old_graph


# ── Test: Alembic migration structure ──────────────────────────────


class TestAlembicMigrationStructure:
    """Verify migration file structure (offline, no DB connection)."""

    def test_migration_file_exists(self) -> None:
        migration_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "migrations",
            "versions",
            "20260613_0002_m2_classification_trace.py",
        )
        assert os.path.exists(migration_path), (
            f"Migration file not found: {migration_path}"
        )

    def test_migration_has_upgrade_and_downgrade(self) -> None:
        migration_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "migrations",
            "versions",
            "20260613_0002_m2_classification_trace.py",
        )
        spec = importlib.util.spec_from_file_location("migration", migration_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert hasattr(module, "upgrade"), "Migration must define upgrade()"
        assert hasattr(module, "downgrade"), "Migration must define downgrade()"
        assert callable(module.upgrade)
        assert callable(module.downgrade)

    def test_migration_revision_chain(self) -> None:
        migration_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "migrations",
            "versions",
            "20260613_0002_m2_classification_trace.py",
        )
        spec = importlib.util.spec_from_file_location("migration", migration_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert module.revision == "20260613_0002"
        assert module.down_revision == "20260609_0001"

    def test_migration_upgrade_adds_columns(self) -> None:
        """Verify upgrade() calls op.add_column for all classification fields."""
        migration_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "migrations",
            "versions",
            "20260613_0002_m2_classification_trace.py",
        )
        spec = importlib.util.spec_from_file_location("migration", migration_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        source = inspect.getsource(module.upgrade)
        expected_columns = [
            "emotion_label",
            "emotion_confidence",
            "intent_label",
            "intent_confidence",
            "risk_level",
            "risk_confidence",
            "classification_status",
            "classification_error_code",
            "route",
            "trace_schema_version",
        ]
        for col in expected_columns:
            assert col in source, f"upgrade() must add column '{col}'"

    def test_migration_downgrade_removes_columns(self) -> None:
        """Verify downgrade() calls op.drop_column for all classification fields."""
        migration_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "migrations",
            "versions",
            "20260613_0002_m2_classification_trace.py",
        )
        spec = importlib.util.spec_from_file_location("migration", migration_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        source = inspect.getsource(module.downgrade)
        expected_columns = [
            "emotion_label",
            "emotion_confidence",
            "intent_label",
            "intent_confidence",
            "risk_level",
            "risk_confidence",
            "classification_status",
            "classification_error_code",
            "route",
            "trace_schema_version",
        ]
        for col in expected_columns:
            assert col in source, f"downgrade() must drop column '{col}'"
