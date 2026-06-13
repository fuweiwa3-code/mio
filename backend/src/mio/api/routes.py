import json
from collections.abc import AsyncIterator
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
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
    TraceListResponse,
    TraceResponse,
)
from mio.db.models import CompanionProfile, Conversation
from mio.services.conversations import ConversationService
from mio.services.traces import TraceService, sanitize_node_summary

health_router = APIRouter(prefix="/api/health", tags=["health"])
api_router = APIRouter(prefix="/api/v1")
ConversationServiceDep = Annotated[
    ConversationService,
    Depends(get_conversation_service),
]


def get_trace_service(request: Request) -> TraceService:
    return cast(TraceService, request.app.state.trace_service)


TraceServiceDep = Annotated[TraceService, Depends(get_trace_service)]


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


# ── Trace query endpoints ───────────────────────────────────────────


@api_router.get(
    "/traces",
    response_model=TraceListResponse,
    tags=["traces"],
)
async def list_traces(
    trace_service: TraceServiceDep,
    conversation_id: UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = None,
) -> TraceListResponse:
    traces, next_cursor = await trace_service.list_traces(
        conversation_id=conversation_id,
        status=status_filter,
        limit=limit,
        cursor=cursor,
    )
    items = [
        TraceResponse(
            id=t.id,
            conversation_id=t.conversation_id,
            request_id=t.request_id,
            status=t.status,
            provider=t.provider,
            model=t.model,
            duration_ms=t.duration_ms,
            error_stage=t.error_stage,
            error_code=t.error_code,
            emotion_label=t.emotion_label,
            emotion_confidence=t.emotion_confidence,
            intent_label=t.intent_label,
            intent_confidence=t.intent_confidence,
            risk_level=t.risk_level,
            risk_confidence=t.risk_confidence,
            classification_status=t.classification_status,
            classification_error_code=t.classification_error_code,
            route=t.route,
            # NULL in DB → 1 for historical traces
            trace_schema_version=t.trace_schema_version or 1,
            node_summary=sanitize_node_summary(t.node_summary),
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in traces
    ]
    return TraceListResponse(items=items, next_cursor=next_cursor)


@api_router.get(
    "/traces/{trace_id}",
    response_model=TraceResponse,
    tags=["traces"],
)
async def get_trace(
    trace_id: UUID,
    trace_service: TraceServiceDep,
) -> TraceResponse:
    t = await trace_service.get_trace(trace_id)
    return TraceResponse(
        id=t.id,
        conversation_id=t.conversation_id,
        request_id=t.request_id,
        status=t.status,
        provider=t.provider,
        model=t.model,
        duration_ms=t.duration_ms,
        error_stage=t.error_stage,
        error_code=t.error_code,
        emotion_label=t.emotion_label,
        emotion_confidence=t.emotion_confidence,
        intent_label=t.intent_label,
        intent_confidence=t.intent_confidence,
        risk_level=t.risk_level,
        risk_confidence=t.risk_confidence,
        classification_status=t.classification_status,
        classification_error_code=t.classification_error_code,
        route=t.route,
        trace_schema_version=t.trace_schema_version or 1,
        node_summary=sanitize_node_summary(t.node_summary),
        created_at=t.created_at,
        updated_at=t.updated_at,
    )
