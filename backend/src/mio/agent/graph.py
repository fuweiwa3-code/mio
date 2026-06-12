"""LangGraph agent workflow with classification, conditional routing, and safety."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any, TypedDict, cast
from uuid import UUID

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from mio.agent.prompt import build_persona_prompt
from mio.agent.safety import build_safety_response, stream_safety_response
from mio.classification.base import MessageClassifier
from mio.classification.exceptions import ClassificationCancelledError, ClassificationError
from mio.classification.models import (
    ClassificationResult,
    EmotionLabel,
    IntentLabel,
    RiskLevel,
    classification_fallback,
)
from mio.llm.base import ChatMessage, ChatModelProvider, ModelOptions


class AgentState(TypedDict, total=False):
    """State shared across graph nodes."""

    request_id: UUID
    current_user_text: str
    profile: dict[str, Any]
    history: list[ChatMessage]
    model: str
    classification: ClassificationResult
    classification_status: str  # "success" | "fallback"
    classification_error_code: str  # provider_error | schema_invalid
    route: str  # "safety" | "persona"
    prompt_messages: list[ChatMessage]
    safety_response: str
    display_text: str
    status: str
    node_summary: dict[str, Any]


AgentGraph = CompiledStateGraph[AgentState, None, AgentState, AgentState]


def _is_safety_route(classification: ClassificationResult) -> bool:
    """Determine if this classification should route to safety."""
    return (
        classification.risk.level is RiskLevel.high
        or classification.emotion.label is EmotionLabel.crisis
        or classification.intent.label is IntentLabel.unsafe
    )


def create_agent_graph(
    provider: ChatModelProvider,
    classifier: MessageClassifier,
) -> AgentGraph:
    """Create the agent graph with classification and conditional routing.

    Graph topology:
        START → load_context → classify_message
            → [safety] → build_safety_response → stream_safety_response → finalize_response → END
            → [persona] → build_persona_prompt → stream_llm → finalize_response → END

    Args:
        provider: ChatModelProvider for persona LLM responses.
        classifier: MessageClassifier for message classification.

    Returns:
        Compiled agent graph.
    """

    async def load_context(state: AgentState) -> dict[str, Any]:
        return {
            "status": "context_loaded",
            "node_summary": {
                **state.get("node_summary", {}),
                "load_context": {"status": "completed", "error_code": None},
            },
        }

    async def classify_message(state: AgentState) -> dict[str, Any]:
        request_id = state["request_id"]
        text = state.get("current_user_text", "")
        start = time.perf_counter()

        try:
            result = await classifier.classify(text, request_id=request_id)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return {
                "classification": result,
                "classification_status": "success",
                "classification_error_code": "",
                "route": "safety" if _is_safety_route(result) else "persona",
                "node_summary": {
                    **state.get("node_summary", {}),
                    "classify_message": {
                        "status": "completed",
                        "duration_ms": elapsed_ms,
                        "error_code": None,
                    },
                },
            }
        except ClassificationCancelledError:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            fallback = classification_fallback()
            return {
                "classification": fallback,
                "classification_status": "fallback",
                "classification_error_code": "classification_cancelled",
                "route": "persona",
                "node_summary": {
                    **state.get("node_summary", {}),
                    "classify_message": {
                        "status": "cancelled",
                        "duration_ms": elapsed_ms,
                        "error_code": "classification_cancelled",
                    },
                },
            }
        except ClassificationError as exc:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            error_code = (
                "classification_provider_error"
                if "provider" in type(exc).__name__.lower()
                else "classification_schema_invalid"
            )
            fallback = classification_fallback()
            return {
                "classification": fallback,
                "classification_status": "fallback",
                "classification_error_code": error_code,
                "route": "persona",
                "node_summary": {
                    **state.get("node_summary", {}),
                    "classify_message": {
                        "status": "fallback",
                        "duration_ms": elapsed_ms,
                        "error_code": error_code,
                    },
                },
            }

    async def build_safety_response_node(state: AgentState) -> dict[str, Any]:
        classification = state["classification"]
        response_text = build_safety_response(classification)
        return {
            "safety_response": response_text,
            "status": "safety_built",
            "node_summary": {
                **state.get("node_summary", {}),
                "build_safety_response": {
                    "status": "completed",
                    "error_code": None,
                },
            },
        }

    async def build_persona_prompt_node(state: AgentState) -> dict[str, Any]:
        profile = state["profile"]
        classification = state.get("classification")
        classification_status = state.get("classification_status", "success")

        system_prompt = build_persona_prompt(
            name=profile["name"],
            relationship_type=profile["relationship_type"],
            speaking_style=profile["speaking_style"],
            boundaries=profile["boundaries"],
            classification=classification,
            classification_status=classification_status,
        )
        return {
            "prompt_messages": [
                ChatMessage(role="system", content=system_prompt),
                *state["history"],
            ],
            "status": "prompt_built",
            "node_summary": {
                **state.get("node_summary", {}),
                "build_persona_prompt": {
                    "status": "completed",
                    "error_code": None,
                },
            },
        }

    async def stream_safety_response_node(state: AgentState) -> dict[str, Any]:
        writer = get_stream_writer()
        response_text = state.get("safety_response", "")
        async for event in stream_safety_response(response_text):
            writer(event)
        return {
            "display_text": response_text,
            "status": "safety_streamed",
            "node_summary": {
                **state.get("node_summary", {}),
                "stream_safety_response": {
                    "status": "completed",
                    "error_code": None,
                },
            },
        }

    async def stream_llm_node(state: AgentState) -> dict[str, Any]:
        writer = get_stream_writer()
        chunks: list[str] = []
        try:
            async for chunk in provider.stream(
                request_id=state["request_id"],
                messages=state["prompt_messages"],
                options=ModelOptions(model=state["model"]),
            ):
                chunks.append(chunk)
                writer({"event": "message.delta", "text": chunk})
            return {
                "display_text": "".join(chunks),
                "status": "generated",
                "node_summary": {
                    **state.get("node_summary", {}),
                    "stream_llm": {
                        "status": "completed",
                        "error_code": None,
                    },
                },
            }
        except Exception:
            return {
                "display_text": "".join(chunks),
                "status": "provider_error",
                "node_summary": {
                    **state.get("node_summary", {}),
                    "stream_llm": {
                        "status": "failed",
                        "error_code": "provider_error",
                    },
                },
            }

    async def finalize_response(state: AgentState) -> dict[str, Any]:
        return {
            "status": "completed",
            "display_text": state.get("display_text", ""),
            "node_summary": {
                **state.get("node_summary", {}),
                "finalize_response": {
                    "status": "completed",
                    "error_code": None,
                },
            },
        }

    def route_after_classify(state: AgentState) -> str:
        if state.get("route") == "safety":
            return "build_safety_response"
        return "build_persona_prompt"

    graph = StateGraph(AgentState)
    graph.add_node("load_context", load_context)
    graph.add_node("classify_message", classify_message)
    graph.add_node("build_safety_response", build_safety_response_node)
    graph.add_node("build_persona_prompt", build_persona_prompt_node)
    graph.add_node("stream_safety_response", stream_safety_response_node)
    graph.add_node("stream_llm", stream_llm_node)
    graph.add_node("finalize_response", finalize_response)

    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "classify_message")
    graph.add_conditional_edges(
        "classify_message",
        route_after_classify,
        {
            "build_safety_response": "build_safety_response",
            "build_persona_prompt": "build_persona_prompt",
        },
    )
    graph.add_edge("build_safety_response", "stream_safety_response")
    graph.add_edge("build_persona_prompt", "stream_llm")
    graph.add_edge("stream_safety_response", "finalize_response")
    graph.add_edge("stream_llm", "finalize_response")
    graph.add_edge("finalize_response", END)

    return graph.compile()


async def stream_agent_events(
    graph: AgentGraph,
    state: AgentState,
) -> AsyncIterator[dict[str, Any]]:
    """Stream events from the agent graph.

    Yields:
        - message.delta events (from custom stream writer)
        - agent.completed event (from final values)
    """
    async for mode, data in graph.astream(state, stream_mode=["custom", "values"]):
        event_data = cast(dict[str, Any], data)
        if mode == "custom":
            yield event_data
        elif mode == "values" and event_data.get("status") == "completed":
            yield {
                "event": "agent.completed",
                "display_text": event_data.get("display_text", ""),
                "classification": event_data.get("classification"),
                "classification_status": event_data.get("classification_status"),
                "route": event_data.get("route"),
                "node_summary": event_data.get("node_summary", {}),
                "classification_error_code": event_data.get(
                    "classification_error_code", ""
                ),
            }
