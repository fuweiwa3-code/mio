import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse

from mio.api.dependencies import get_conversation_service
from mio.api.errors import AppError
from mio.api.schemas import (
    CancelResponse,
    CompanionProfileResponse,
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
    MessageCreate,
    MessageListResponse,
)
from mio.db.models import CompanionProfile, Conversation
from mio.services.conversations import ConversationService

health_router = APIRouter(prefix="/api/health", tags=["health"])
api_router = APIRouter(prefix="/api/v1")
ConversationServiceDep = Annotated[
    ConversationService,
    Depends(get_conversation_service),
]


@health_router.get("/live")
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


@health_router.get("/ready")
async def readiness(
    service: ConversationServiceDep,
) -> dict[str, str]:
    await service.get_profile()
    return {"status": "ready", "database": "reachable"}


@api_router.get(
    "/companion/profile",
    response_model=CompanionProfileResponse,
    tags=["companion"],
)
async def get_companion_profile(
    service: ConversationServiceDep,
) -> CompanionProfile:
    return await service.get_profile()


@api_router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["conversations"],
)
async def create_conversation(
    payload: ConversationCreate,
    service: ConversationServiceDep,
) -> Conversation:
    return await service.create_conversation(payload.title, payload.channel)


@api_router.get(
    "/conversations",
    response_model=ConversationListResponse,
    tags=["conversations"],
)
async def list_conversations(
    service: ConversationServiceDep,
) -> ConversationListResponse:
    return ConversationListResponse(items=await service.list_conversations())


@api_router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    tags=["conversations"],
)
async def get_conversation(
    conversation_id: UUID,
    service: ConversationServiceDep,
) -> Conversation:
    return await service.get_conversation(conversation_id)


@api_router.get(
    "/conversations/{conversation_id}/messages",
    response_model=MessageListResponse,
    tags=["messages"],
)
async def list_messages(
    conversation_id: UUID,
    service: ConversationServiceDep,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
) -> MessageListResponse:
    items, next_cursor = await service.list_messages(conversation_id, limit, cursor)
    return MessageListResponse(items=items, next_cursor=next_cursor)


@api_router.post(
    "/conversations/{conversation_id}/messages",
    tags=["messages"],
)
async def send_message(
    conversation_id: UUID,
    payload: MessageCreate,
    service: ConversationServiceDep,
) -> StreamingResponse:
    turn = await service.start_turn(conversation_id, payload)

    async def events() -> AsyncIterator[str]:
        async for event in service.stream_turn(turn):
            event_name = event.pop("event")
            data = json.dumps(event, default=str, ensure_ascii=False)
            yield f"event: {event_name}\ndata: {data}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@api_router.post(
    "/chat/requests/{request_id}/cancel",
    response_model=CancelResponse,
    tags=["chat"],
)
async def cancel_request(
    request_id: UUID,
    service: ConversationServiceDep,
) -> CancelResponse:
    cancelled = await service.cancel(request_id)
    if not cancelled:
        raise AppError(404, "request_not_active", "生成请求不存在或已经结束。")
    return CancelResponse(request_id=request_id, cancelled=True)
