"""Tests for LangGraph classification routing, safety response, and fallback."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID, uuid4

from mio.agent.graph import AgentState, create_agent_graph, stream_agent_events
from mio.classification.mock import MockMessageClassifier
from mio.classification.models import (
    ClassificationResult,
)
from mio.llm.base import ChatMessage, ChatModelProvider, ModelOptions

# ── Test helpers ───────────────────────────────────────────────────


class SpyProvider(ChatModelProvider):
    """Tracks whether stream() was called."""

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


class FailingClassifier(MockMessageClassifier):
    """Always raises ClassificationError."""

    name = "failing"

    async def classify(self, text: str, *, request_id: UUID) -> ClassificationResult:
        from mio.classification.exceptions import ClassificationProviderError

        raise ClassificationProviderError("simulated failure")


class CollectingProvider(ChatModelProvider):
    """Records messages passed to stream()."""

    name = "collecting"

    def __init__(self, response: str = "collected response") -> None:
        self.stream_called = False
        self.captured_messages: list[ChatMessage] = []
        self._response = response

    async def stream(
        self,
        request_id: UUID,
        messages: list[ChatMessage],
        options: ModelOptions,
    ) -> AsyncIterator[str]:
        self.stream_called = True
        self.captured_messages = list(messages)
        for i in range(0, len(self._response), 6):
            yield self._response[i : i + 6]

    async def cancel(self, request_id: UUID) -> None:
        pass


def _make_state(
    text: str,
    *,
    history: list[ChatMessage] | None = None,
) -> AgentState:
    """Create a minimal AgentState for graph testing."""
    return {
        "request_id": uuid4(),
        "current_user_text": text,
        "profile": {
            "name": "澪",
            "relationship_type": "稳定陪伴者",
            "speaking_style": "清冷慢热、认真克制",
            "boundaries": ["不冒充真人"],
        },
        "history": history or [],
        "model": "test-model",
        "display_text": "",
        "status": "pending",
        "node_summary": {},
        "classification_status": "success",
        "classification_error_code": "",
        "route": "",
    }


async def _collect_events(graph, state: AgentState) -> list[dict[str, Any]]:
    """Collect all events from graph execution."""
    return [event async for event in stream_agent_events(graph, state)]


# ── Routing tests ──────────────────────────────────────────────────


class TestPersonaRouting:
    """Verify normal messages route to persona path."""

    async def test_calm_companion_routes_to_persona(self) -> None:
        provider = SpyProvider()
        classifier = MockMessageClassifier()
        graph = create_agent_graph(provider, classifier)
        state = _make_state("你好呀")
        events = await _collect_events(graph, state)

        assert provider.stream_called is True
        assert any(e["event"] == "agent.completed" for e in events)
        completed = next(e for e in events if e["event"] == "agent.completed")
        assert completed["route"] == "persona"

    async def test_tired_companion_routes_to_persona(self) -> None:
        provider = SpyProvider()
        classifier = MockMessageClassifier()
        graph = create_agent_graph(provider, classifier)
        state = _make_state("好累啊，不想动")
        events = await _collect_events(graph, state)

        assert provider.stream_called is True
        completed = next(e for e in events if e["event"] == "agent.completed")
        assert completed["route"] == "persona"

    async def test_happy_companion_routes_to_persona(self) -> None:
        provider = SpyProvider()
        classifier = MockMessageClassifier()
        graph = create_agent_graph(provider, classifier)
        state = _make_state("太开心了！")
        events = await _collect_events(graph, state)

        assert provider.stream_called is True
        completed = next(e for e in events if e["event"] == "agent.completed")
        assert completed["route"] == "persona"


class TestSafetyRouting:
    """Verify high-risk messages route to safety path."""

    async def test_crisis_routes_to_safety(self) -> None:
        provider = SpyProvider()
        classifier = MockMessageClassifier()
        graph = create_agent_graph(provider, classifier)
        state = _make_state("我不想活了")
        events = await _collect_events(graph, state)

        assert provider.stream_called is False
        completed = next(e for e in events if e["event"] == "agent.completed")
        assert completed["route"] == "safety"
        assert completed["display_text"]  # has safety content

    async def test_unsafe_intent_routes_to_safety(self) -> None:
        provider = SpyProvider()
        classifier = MockMessageClassifier()
        graph = create_agent_graph(provider, classifier)
        state = _make_state("想自残")
        events = await _collect_events(graph, state)

        assert provider.stream_called is False
        completed = next(e for e in events if e["event"] == "agent.completed")
        assert completed["route"] == "safety"

    async def test_safety_path_does_not_call_chat_model_provider(self) -> None:
        """High-risk path must NEVER invoke the persona ChatModelProvider."""
        provider = SpyProvider()
        classifier = MockMessageClassifier()
        graph = create_agent_graph(provider, classifier)
        state = _make_state("想自杀")
        events = await _collect_events(graph, state)

        assert provider.stream_called is False
        completed = next(e for e in events if e["event"] == "agent.completed")
        assert completed["route"] == "safety"

    async def test_safety_response_contains_safety_content(self) -> None:
        provider = SpyProvider()
        classifier = MockMessageClassifier()
        graph = create_agent_graph(provider, classifier)
        state = _make_state("不想活了")
        events = await _collect_events(graph, state)

        completed = next(e for e in events if e["event"] == "agent.completed")
        text = completed["display_text"]
        assert "安全" in text
        assert "紧急" in text

    async def test_safety_produces_delta_events(self) -> None:
        provider = SpyProvider()
        classifier = MockMessageClassifier()
        graph = create_agent_graph(provider, classifier)
        state = _make_state("不想活了")
        events = await _collect_events(graph, state)

        deltas = [e for e in events if e["event"] == "message.delta"]
        assert len(deltas) > 0


class TestMediumRiskRouting:
    """Verify medium risk routes to cautious persona."""

    async def test_angry_routes_to_persona_with_caution(self) -> None:
        provider = CollectingProvider()
        classifier = MockMessageClassifier()
        graph = create_agent_graph(provider, classifier)
        state = _make_state("气死我了")
        events = await _collect_events(graph, state)

        assert provider.stream_called is True
        completed = next(e for e in events if e["event"] == "agent.completed")
        assert completed["route"] == "persona"
        # Check that the prompt contains cautious strategy
        system_msg = provider.captured_messages[0]
        assert "谨慎" in system_msg.content or "安全" in system_msg.content

    async def test_anxious_routes_to_persona_with_stabilize_strategy(self) -> None:
        provider = CollectingProvider()
        classifier = MockMessageClassifier()
        graph = create_agent_graph(provider, classifier)
        state = _make_state("好焦虑，睡不着")
        await _collect_events(graph, state)

        assert provider.stream_called is True
        system_msg = provider.captured_messages[0]
        assert "焦虑" in system_msg.content


class TestClassificationFallback:
    """Verify classifier failures produce fallback behavior."""

    async def test_classifier_error_routes_to_persona_with_fallback(self) -> None:
        provider = CollectingProvider()
        classifier = FailingClassifier()
        graph = create_agent_graph(provider, classifier)
        state = _make_state("你好")
        events = await _collect_events(graph, state)

        assert provider.stream_called is True
        completed = next(e for e in events if e["event"] == "agent.completed")
        assert completed["route"] == "persona"
        assert completed["classification_status"] == "fallback"

    async def test_fallback_classification_uses_medium_risk(self) -> None:
        provider = CollectingProvider()
        classifier = FailingClassifier()
        graph = create_agent_graph(provider, classifier)
        state = _make_state("你好")
        events = await _collect_events(graph, state)

        completed = next(e for e in events if e["event"] == "agent.completed")
        assert completed["classification_status"] == "fallback"
        # The prompt should contain cautious strategy for fallback
        system_msg = provider.captured_messages[0]
        assert "谨慎" in system_msg.content or "不可用" in system_msg.content

    async def test_fallback_does_not_cause_message_failed(self) -> None:
        """Classification fallback must NOT produce a failed terminal event."""
        provider = CollectingProvider()
        classifier = FailingClassifier()
        graph = create_agent_graph(provider, classifier)
        state = _make_state("你好")
        events = await _collect_events(graph, state)

        event_names = [e["event"] for e in events]
        assert "message.failed" not in event_names
        assert "agent.completed" in event_names


class TestGraphStatePreservation:
    """Verify classification, route, status, and node_summary are preserved."""

    async def test_node_summary_contains_all_executed_nodes(self) -> None:
        provider = SpyProvider()
        classifier = MockMessageClassifier()
        graph = create_agent_graph(provider, classifier)
        state = _make_state("你好")
        events = await _collect_events(graph, state)

        completed = next(e for e in events if e["event"] == "agent.completed")
        ns = completed["node_summary"]
        assert "load_context" in ns
        assert "classify_message" in ns
        assert "build_persona_prompt" in ns
        assert "stream_llm" in ns
        assert "finalize_response" in ns

    async def test_safety_node_summary_skips_persona_nodes(self) -> None:
        provider = SpyProvider()
        classifier = MockMessageClassifier()
        graph = create_agent_graph(provider, classifier)
        state = _make_state("不想活了")
        events = await _collect_events(graph, state)

        completed = next(e for e in events if e["event"] == "agent.completed")
        ns = completed["node_summary"]
        assert "build_safety_response" in ns
        assert "stream_safety_response" in ns
        # build_persona_prompt and stream_llm should NOT be in safety path
        assert "build_persona_prompt" not in ns
        assert "stream_llm" not in ns

    async def test_display_text_is_set_correctly(self) -> None:
        provider = CollectingProvider(response="test response text")
        classifier = MockMessageClassifier()
        graph = create_agent_graph(provider, classifier)
        state = _make_state("你好")
        events = await _collect_events(graph, state)

        completed = next(e for e in events if e["event"] == "agent.completed")
        assert completed["display_text"] == "test response text"

    async def test_safety_display_text_is_set_correctly(self) -> None:
        provider = SpyProvider()
        classifier = MockMessageClassifier()
        graph = create_agent_graph(provider, classifier)
        state = _make_state("不想活了")
        events = await _collect_events(graph, state)

        completed = next(e for e in events if e["event"] == "agent.completed")
        assert len(completed["display_text"]) > 0
        assert completed["route"] == "safety"


class TestPromptStrategyIntegration:
    """Verify classification-aware prompt strategies."""

    async def test_sad_emotion_adds_empathy_strategy(self) -> None:
        provider = CollectingProvider()
        classifier = MockMessageClassifier()
        graph = create_agent_graph(provider, classifier)
        state = _make_state("好难过，想哭")
        await _collect_events(graph, state)

        system_msg = provider.captured_messages[0]
        assert "难过" in system_msg.content or "感受" in system_msg.content

    async def test_reminder_intent_adds_no_pretend_strategy(self) -> None:
        provider = CollectingProvider()
        classifier = MockMessageClassifier()
        graph = create_agent_graph(provider, classifier)
        state = _make_state("提醒我明天开会")
        await _collect_events(graph, state)

        system_msg = provider.captured_messages[0]
        assert "提醒" in system_msg.content

    async def test_mixed_intent_adds_mixed_strategy(self) -> None:
        provider = CollectingProvider()
        classifier = MockMessageClassifier()
        graph = create_agent_graph(provider, classifier)
        state = _make_state("好累，Python的GIL是什么")
        await _collect_events(graph, state)

        system_msg = provider.captured_messages[0]
        assert "情绪" in system_msg.content or "问题" in system_msg.content

    async def test_knowledge_qa_intent_adds_knowledge_strategy(self) -> None:
        provider = CollectingProvider()
        classifier = MockMessageClassifier()
        graph = create_agent_graph(provider, classifier)
        state = _make_state("什么是Python的GIL")
        await _collect_events(graph, state)

        system_msg = provider.captured_messages[0]
        assert "人设" in system_msg.content or "回答" in system_msg.content

    async def test_crisis_safety_response_stops_roleplay(self) -> None:
        """Safety response should not contain romantic/roleplay language."""
        provider = SpyProvider()
        classifier = MockMessageClassifier()
        graph = create_agent_graph(provider, classifier)
        state = _make_state("不想活了")
        events = await _collect_events(graph, state)

        completed = next(e for e in events if e["event"] == "agent.completed")
        text = completed["display_text"]
        # Safety response should be serious, not romantic
        assert "亲" not in text
        assert "抱抱" not in text
