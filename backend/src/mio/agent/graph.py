from collections.abc import AsyncIterator
from typing import Any, TypedDict, cast
from uuid import UUID

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from mio.agent.prompt import build_persona_prompt
from mio.llm.base import ChatMessage, ChatModelProvider, ModelOptions


class AgentState(TypedDict, total=False):
    request_id: UUID
    profile: dict[str, Any]
    history: list[ChatMessage]
    model: str
    prompt_messages: list[ChatMessage]
    display_text: str
    status: str


AgentGraph = CompiledStateGraph[AgentState, None, AgentState, AgentState]


def create_agent_graph(provider: ChatModelProvider) -> AgentGraph:
    async def load_context(state: AgentState) -> dict[str, Any]:
        return {"status": "context_loaded"}

    async def build_prompt(state: AgentState) -> dict[str, Any]:
        profile = state["profile"]
        system_prompt = build_persona_prompt(
            name=profile["name"],
            relationship_type=profile["relationship_type"],
            speaking_style=profile["speaking_style"],
            boundaries=profile["boundaries"],
        )
        return {
            "prompt_messages": [
                ChatMessage(role="system", content=system_prompt),
                *state["history"],
            ],
            "status": "prompt_built",
        }

    async def stream_llm(state: AgentState) -> dict[str, Any]:
        writer = get_stream_writer()
        chunks: list[str] = []
        async for chunk in provider.stream(
            request_id=state["request_id"],
            messages=state["prompt_messages"],
            options=ModelOptions(model=state["model"]),
        ):
            chunks.append(chunk)
            writer({"event": "message.delta", "text": chunk})
        return {"display_text": "".join(chunks), "status": "generated"}

    async def finalize_response(state: AgentState) -> dict[str, Any]:
        return {"status": "completed", "display_text": state.get("display_text", "")}

    graph = StateGraph(AgentState)
    graph.add_node("load_context", load_context)
    graph.add_node("build_persona_prompt", build_prompt)
    graph.add_node("stream_llm", stream_llm)
    graph.add_node("finalize_response", finalize_response)
    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "build_persona_prompt")
    graph.add_edge("build_persona_prompt", "stream_llm")
    graph.add_edge("stream_llm", "finalize_response")
    graph.add_edge("finalize_response", END)
    return graph.compile()


async def stream_agent_events(
    graph: AgentGraph,
    state: AgentState,
) -> AsyncIterator[dict[str, Any]]:
    async for mode, data in graph.astream(state, stream_mode=["custom", "values"]):
        event_data = cast(dict[str, Any], data)
        if mode == "custom":
            yield event_data
        elif mode == "values" and event_data.get("status") == "completed":
            yield {
                "event": "agent.completed",
                "display_text": event_data.get("display_text", ""),
            }
