import json
from uuid import UUID

from httpx import AsyncClient

from mio.api.schemas import MessageCreate


def parse_sse_events(body: str) -> list[tuple[str, dict[str, object]]]:
    events: list[tuple[str, dict[str, object]]] = []
    event_name = ""
    for block in body.strip().split("\n\n"):
        for line in block.splitlines():
            if line.startswith("event: "):
                event_name = line.removeprefix("event: ")
            if line.startswith("data: "):
                events.append((event_name, json.loads(line.removeprefix("data: "))))
    return events


async def create_conversation(client: AsyncClient) -> str:
    response = await client.post("/api/v1/conversations", json={})
    assert response.status_code == 201
    return response.json()["id"]


async def test_create_list_and_get_conversation(client: AsyncClient) -> None:
    conversation_id = await create_conversation(client)

    listing = await client.get("/api/v1/conversations")
    detail = await client.get(f"/api/v1/conversations/{conversation_id}")

    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()["items"]] == [conversation_id]
    assert detail.status_code == 200
    assert detail.json()["channel"] == "web"
    assert detail.json()["status"] == "active"


async def test_stream_message_persists_user_and_assistant_messages(
    client: AsyncClient,
) -> None:
    conversation_id = await create_conversation(client)

    response = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={
            "content": "今天写代码有点累。",
            "source": "text",
            "persist_history": True,
            "allow_memory_extraction": True,
        },
    )
    events = parse_sse_events(response.text)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert events[0][0] == "message.started"
    assert any(name == "message.delta" for name, _ in events)
    assert events[-1][0] == "message.completed"
    assert "陪你" in str(events[-1][1]["display_text"])
    assert events[-1][1]["speech_text"] is None

    history = await client.get(
        f"/api/v1/conversations/{conversation_id}/messages",
        params={"limit": 50},
    )
    items = history.json()["items"]
    assert [item["role"] for item in items] == ["user", "assistant"]
    assert items[0]["display_text"] == "今天写代码有点累。"
    assert items[1]["status"] == "completed"
    assert items[1]["display_text"] == events[-1][1]["display_text"]


async def test_messages_use_cursor_pagination_in_ascending_order(
    client: AsyncClient,
) -> None:
    conversation_id = await create_conversation(client)
    for index in range(2):
        await client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={"content": f"第 {index + 1} 轮", "source": "text"},
        )

    first_page = await client.get(
        f"/api/v1/conversations/{conversation_id}/messages",
        params={"limit": 2},
    )
    first_items = first_page.json()["items"]
    second_page = await client.get(
        f"/api/v1/conversations/{conversation_id}/messages",
        params={"limit": 2, "cursor": first_page.json()["next_cursor"]},
    )

    assert len(first_items) == 2
    assert first_items[0]["created_at"] <= first_items[1]["created_at"]
    assert len(second_page.json()["items"]) == 2


async def test_unknown_conversation_uses_unified_error_shape(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/conversations/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
    assert response.json()["code"] == "conversation_not_found"
    assert response.json()["trace_id"]
    assert response.json()["details"] == {}


async def test_second_generation_for_same_conversation_returns_conflict(
    app,
    client: AsyncClient,
) -> None:
    conversation_id = await create_conversation(client)
    service = app.state.conversation_service
    first_turn = await service.start_turn(
        conversation_id=UUID(conversation_id),
        payload=MessageCreate(content="第一条还没有开始消费", source="text"),
    )

    response = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "第二条", "source": "text"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "conversation_busy"
    await service.cancel(first_turn.request_id)
    async for _ in service.stream_turn(first_turn):
        pass


async def test_cancelled_generation_emits_cancel_event_and_persists_partial_text(
    app,
    client: AsyncClient,
) -> None:
    conversation_id = await create_conversation(client)
    service = app.state.conversation_service
    turn = await service.start_turn(
        conversation_id=UUID(conversation_id),
        payload=MessageCreate(content="请测试取消", source="text"),
    )
    stream = service.stream_turn(turn)

    started = await anext(stream)
    delta = await anext(stream)
    cancel_response = await client.post(
        f"/api/v1/chat/requests/{turn.request_id}/cancel"
    )
    final = await anext(stream)

    assert started["event"] == "message.started"
    assert delta["event"] == "message.delta"
    assert cancel_response.status_code == 200
    assert cancel_response.json()["cancelled"] is True
    assert final["event"] == "message.cancelled"

    history = await client.get(f"/api/v1/conversations/{conversation_id}/messages")
    assistant = history.json()["items"][-1]
    assert assistant["status"] == "cancelled"
    assert assistant["display_text"] == delta["delta"]


async def test_client_disconnect_marks_streaming_message_cancelled(
    app,
    client: AsyncClient,
) -> None:
    conversation_id = await create_conversation(client)
    service = app.state.conversation_service
    turn = await service.start_turn(
        conversation_id=UUID(conversation_id),
        payload=MessageCreate(content="客户端准备断开", source="text"),
    )
    stream = service.stream_turn(turn)

    await anext(stream)
    delta = await anext(stream)
    await stream.aclose()

    history = await client.get(f"/api/v1/conversations/{conversation_id}/messages")
    assistant = history.json()["items"][-1]
    assert assistant["status"] == "cancelled"
    assert assistant["display_text"] == delta["delta"]

    next_turn = await service.start_turn(
        conversation_id=UUID(conversation_id),
        payload=MessageCreate(content="断开后可以继续", source="text"),
    )
    await service.cancel(next_turn.request_id)
    async for _ in service.stream_turn(next_turn):
        pass


async def test_ten_rounds_of_mock_chat_remain_queryable(client: AsyncClient) -> None:
    conversation_id = await create_conversation(client)
    for index in range(10):
        response = await client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={"content": f"第 {index + 1} 轮", "source": "text"},
        )
        assert response.status_code == 200

    history = await client.get(
        f"/api/v1/conversations/{conversation_id}/messages",
        params={"limit": 50},
    )

    assert len(history.json()["items"]) == 20
    assert history.json()["next_cursor"] is None


async def test_openapi_exposes_first_wave_contracts(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")
    paths = response.json()["paths"]

    assert "/api/v1/companion/profile" in paths
    assert "/api/v1/conversations" in paths
    assert "/api/v1/conversations/{conversation_id}/messages" in paths
    assert "/api/v1/chat/requests/{request_id}/cancel" in paths
