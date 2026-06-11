from collections.abc import AsyncIterator
from uuid import UUID

from mio.agent.graph import create_agent_graph
from mio.api.schemas import MessageCreate
from mio.llm.base import ChatMessage, ChatModelProvider, ModelOptions
from mio.services.conversations import ConversationService


class FailingProvider(ChatModelProvider):
    name = "failing"

    async def stream(
        self,
        request_id: UUID,
        messages: list[ChatMessage],
        options: ModelOptions,
    ) -> AsyncIterator[str]:
        del request_id, messages, options
        if False:
            yield ""
        raise RuntimeError("provider unavailable")

    async def cancel(self, request_id: UUID) -> None:
        del request_id


async def test_provider_failure_emits_failed_event_and_keeps_user_message(
    app,
    client,
) -> None:
    created = await client.post("/api/v1/conversations", json={})
    conversation_id = UUID(created.json()["id"])
    provider = FailingProvider()
    service = ConversationService(
        session_factory=app.state.session_factory,
        demo_ids=app.state.demo_ids,
        registry=app.state.registry,
        provider=provider,
        agent_graph=create_agent_graph(provider),
        model="failing-model",
        context_message_limit=20,
    )
    turn = await service.start_turn(
        conversation_id,
        MessageCreate(content="这条用户消息必须保留", source="text"),
    )

    events = [event async for event in service.stream_turn(turn)]

    assert [event["event"] for event in events] == [
        "message.started",
        "message.failed",
    ]
    history = await client.get(f"/api/v1/conversations/{conversation_id}/messages")
    assert history.json()["items"][0]["display_text"] == "这条用户消息必须保留"
    assert history.json()["items"][1]["status"] == "failed"
