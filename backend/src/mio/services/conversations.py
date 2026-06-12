"""Conversation management service — drives turns, streaming, and persistence."""

import base64
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from time import perf_counter
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from mio.agent.graph import AgentGraph, AgentState, stream_agent_events
from mio.api.errors import AppError
from mio.api.schemas import MessageCreate
from mio.chat.registry import ActiveRequestRegistry
from mio.classification.base import MessageClassifier
from mio.db.models import (
    AgentTrace,
    CompanionProfile,
    Conversation,
    ConversationStatus,
    Message,
    MessageRole,
    MessageStatus,
)
from mio.db.seed import DemoIds
from mio.llm.base import ChatMessage, ChatModelProvider


@dataclass(frozen=True)
class TurnContext:
    conversation_id: UUID
    request_id: UUID
    user_message_id: UUID
    assistant_message_id: UUID
    trace_id: UUID


class ConversationService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        demo_ids: DemoIds,
        registry: ActiveRequestRegistry,
        provider: ChatModelProvider,
        classifier: MessageClassifier,
        agent_graph: AgentGraph,
        model: str,
        context_message_limit: int,
    ) -> None:
        self._session_factory = session_factory
        self._demo_ids = demo_ids
        self._registry = registry
        self._provider = provider
        self._classifier = classifier
        self._agent_graph = agent_graph
        self._model = model
        self._context_message_limit = context_message_limit

    async def _get_conversation(
        self,
        session: AsyncSession,
        conversation_id: UUID,
    ) -> Conversation:
        conversation = await session.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == self._demo_ids.user_id,
            )
        )
        if conversation is None:
            raise AppError(404, "conversation_not_found", "对话不存在。")
        return conversation

    async def get_profile(self) -> CompanionProfile:
        async with self._session_factory() as session:
            profile = await session.get(CompanionProfile, self._demo_ids.companion_id)
            if profile is None:
                raise AppError(500, "profile_not_found", "默认澪人设未初始化。")
            return profile

    async def create_conversation(self, title: str, channel: str) -> Conversation:
        async with self._session_factory() as session:
            conversation = Conversation(
                user_id=self._demo_ids.user_id,
                companion_id=self._demo_ids.companion_id,
                title=title,
                channel=channel,
                status=ConversationStatus.active,
            )
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)
            return conversation

    async def list_conversations(self) -> list[Conversation]:
        async with self._session_factory() as session:
            return list(
                await session.scalars(
                    select(Conversation)
                    .where(Conversation.user_id == self._demo_ids.user_id)
                    .order_by(Conversation.updated_at.desc())
                )
            )

    async def get_conversation(self, conversation_id: UUID) -> Conversation:
        async with self._session_factory() as session:
            return await self._get_conversation(session, conversation_id)

    @staticmethod
    def _encode_cursor(message: Message) -> str:
        raw = f"{message.created_at.isoformat()}|{message.id}"
        return base64.urlsafe_b64encode(raw.encode()).decode()

    @staticmethod
    def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
        try:
            raw = base64.urlsafe_b64decode(cursor.encode()).decode()
            created_at, message_id = raw.split("|", maxsplit=1)
            return datetime.fromisoformat(created_at), UUID(message_id)
        except (ValueError, UnicodeDecodeError) as exc:
            raise AppError(400, "invalid_cursor", "分页游标无效。") from exc

    async def list_messages(
        self,
        conversation_id: UUID,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[Message], str | None]:
        async with self._session_factory() as session:
            await self._get_conversation(session, conversation_id)
            query = select(Message).where(Message.conversation_id == conversation_id)
            if cursor:
                created_at, message_id = self._decode_cursor(cursor)
                query = query.where(
                    or_(
                        Message.created_at > created_at,
                        and_(
                            Message.created_at == created_at,
                            Message.id > message_id,
                        ),
                    )
                )
            messages = list(
                await session.scalars(
                    query.order_by(Message.created_at, Message.id).limit(limit + 1)
                )
            )
            has_more = len(messages) > limit
            page = messages[:limit]
            next_cursor = self._encode_cursor(page[-1]) if has_more and page else None
            return page, next_cursor

    async def start_turn(
        self,
        conversation_id: UUID,
        payload: MessageCreate,
    ) -> TurnContext:
        request_id = uuid4()
        if not await self._registry.reserve(conversation_id, request_id):
            raise AppError(
                409,
                "conversation_busy",
                "该对话已有回复正在生成，请等待完成或先取消。",
            )

        try:
            async with self._session_factory() as session:
                conversation = await self._get_conversation(session, conversation_id)
                user_message = Message(
                    conversation_id=conversation.id,
                    role=MessageRole.user,
                    display_text=payload.content,
                    status=MessageStatus.completed,
                    source=payload.source,
                    persist_history=payload.persist_history,
                    allow_memory_extraction=payload.allow_memory_extraction,
                )
                assistant_message = Message(
                    conversation_id=conversation.id,
                    role=MessageRole.assistant,
                    display_text="",
                    status=MessageStatus.pending,
                    request_id=request_id,
                    source="text",
                    persist_history=True,
                    allow_memory_extraction=False,
                )
                trace = AgentTrace(
                    conversation_id=conversation.id,
                    request_id=request_id,
                    status="pending",
                    provider=self._provider.name,
                    model=self._model,
                    node_summary={},
                )
                session.add_all([user_message, assistant_message, trace])
                await session.commit()
                return TurnContext(
                    conversation_id=conversation.id,
                    request_id=request_id,
                    user_message_id=user_message.id,
                    assistant_message_id=assistant_message.id,
                    trace_id=trace.id,
                )
        except Exception:
            await self._registry.release(conversation_id, request_id)
            raise

    async def _load_agent_state(
        self, turn: TurnContext, user_text: str
    ) -> AgentState:
        async with self._session_factory() as session:
            profile = await session.get(CompanionProfile, self._demo_ids.companion_id)
            if profile is None:
                raise AppError(500, "profile_not_found", "默认澪人设未初始化。")
            recent_desc = list(
                await session.scalars(
                    select(Message)
                    .where(
                        Message.conversation_id == turn.conversation_id,
                        Message.status == MessageStatus.completed,
                        Message.persist_history.is_(True),
                    )
                    .order_by(Message.created_at.desc(), Message.id.desc())
                    .limit(self._context_message_limit)
                )
            )
            history = [
                ChatMessage(role=message.role.value, content=message.display_text)
                for message in reversed(recent_desc)
            ]
            return {
                "request_id": turn.request_id,
                "current_user_text": user_text,
                "profile": {
                    "name": profile.name,
                    "relationship_type": profile.relationship_type,
                    "speaking_style": profile.speaking_style,
                    "boundaries": profile.boundaries,
                },
                "history": history,
                "model": self._model,
                "display_text": "",
                "status": "pending",
                "node_summary": {},
                "classification_status": "success",
                "classification_error_code": "",
                "route": "",
            }

    async def _update_streaming_text(
        self,
        turn: TurnContext,
        display_text: str,
    ) -> None:
        async with self._session_factory() as session:
            message = await session.get(Message, turn.assistant_message_id)
            trace = await session.get(AgentTrace, turn.trace_id)
            if message is not None:
                message.display_text = display_text
                message.status = MessageStatus.streaming
            if trace is not None:
                trace.status = "streaming"
            await session.commit()

    async def _finish(
        self,
        turn: TurnContext,
        status: MessageStatus,
        display_text: str,
        started_at: float,
        error_code: str | None = None,
        error_message: str | None = None,
        node_summary: dict[str, object] | None = None,
        route: str | None = None,
    ) -> None:
        async with self._session_factory() as session:
            message = await session.get(Message, turn.assistant_message_id)
            trace = await session.get(AgentTrace, turn.trace_id)
            if message is not None:
                message.display_text = display_text
                message.status = status
                message.error_code = error_code
                message.error_message = error_message
            if trace is not None:
                trace.status = status.value
                trace.duration_ms = int((perf_counter() - started_at) * 1000)
                trace.error_stage = "stream_llm" if error_code else None
                trace.error_code = error_code
                if node_summary:
                    trace.node_summary = node_summary
                else:
                    trace.node_summary = {
                        "load_context": "completed",
                        "build_persona_prompt": "completed",
                        "stream_llm": status.value,
                        "finalize_response": (
                            "completed"
                            if status == MessageStatus.completed
                            else "skipped"
                        ),
                    }
            await session.commit()

    async def stream_turn(
        self,
        turn: TurnContext,
    ) -> AsyncIterator[dict[str, object]]:
        started_at = perf_counter()
        text = ""
        terminal = False
        final_node_summary: dict[str, object] = {}
        final_route: str | None = None

        # Register the cancel Event BEFORE yielding message.started.
        # This eliminates the race where cancel() arrives between
        # message.started and classify()'s Event registration.
        await self._classifier.prepare(turn.request_id)

        yield {
            "event": "message.started",
            "request_id": turn.request_id,
            "message_id": turn.assistant_message_id,
            "trace_id": turn.trace_id,
        }
        try:
            # Load user text by exact ID from the turn context.
            async with self._session_factory() as session:
                user_msg = await session.get(Message, turn.user_message_id)
                if (
                    user_msg is None
                    or user_msg.conversation_id != turn.conversation_id
                    or user_msg.role != MessageRole.user
                ):
                    raise AppError(
                        500,
                        "user_message_not_found",
                        "无法读取当前用户消息。",
                    )
                user_text = user_msg.display_text

            state = await self._load_agent_state(turn, user_text)
            async for event in stream_agent_events(self._agent_graph, state):
                if await self._registry.is_cancelled(turn.request_id):
                    await self._classifier.cancel(turn.request_id)
                    await self._provider.cancel(turn.request_id)
                    await self._finish(
                        turn,
                        MessageStatus.cancelled,
                        text,
                        started_at,
                        node_summary=final_node_summary or None,
                        route=final_route,
                    )
                    terminal = True
                    yield {
                        "event": "message.cancelled",
                        "request_id": turn.request_id,
                        "message_id": turn.assistant_message_id,
                        "trace_id": turn.trace_id,
                        "display_text": text,
                        "speech_text": None,
                    }
                    return
                if event["event"] == "message.delta":
                    text += event["text"]
                    await self._update_streaming_text(turn, text)
                    yield {
                        "event": "message.delta",
                        "request_id": turn.request_id,
                        "message_id": turn.assistant_message_id,
                        "trace_id": turn.trace_id,
                        "delta": event["text"],
                    }
                elif event["event"] == "agent.completed":
                    text = event["display_text"]
                    final_node_summary = event.get("node_summary", {})
                    final_route = event.get("route")

            # Re-check cancel after graph completes.  When the classifier
            # was cancelled mid-flight the graph finishes with a fallback
            # classification and persona route, but the assistant message
            # must still be persisted as *cancelled*, not completed.
            if await self._registry.is_cancelled(turn.request_id):
                await self._finish(
                    turn,
                    MessageStatus.cancelled,
                    text,
                    started_at,
                    node_summary=final_node_summary or None,
                    route=final_route,
                )
                terminal = True
                yield {
                    "event": "message.cancelled",
                    "request_id": turn.request_id,
                    "message_id": turn.assistant_message_id,
                    "trace_id": turn.trace_id,
                    "display_text": text,
                    "speech_text": None,
                }
                return

            # Check for provider error in node_summary
            provider_error = False
            if final_node_summary:
                stream_llm_info = final_node_summary.get("stream_llm", {})
                if isinstance(stream_llm_info, dict) and stream_llm_info.get("status") == "failed":
                    provider_error = True

            if provider_error:
                await self._finish(
                    turn,
                    MessageStatus.failed,
                    text,
                    started_at,
                    error_code="provider_error",
                    error_message="回复生成失败，已保留你的消息。",
                    node_summary=final_node_summary or None,
                    route=final_route,
                )
                terminal = True
                yield {
                    "event": "message.failed",
                    "request_id": turn.request_id,
                    "message_id": turn.assistant_message_id,
                    "trace_id": turn.trace_id,
                    "display_text": text,
                    "speech_text": None,
                    "code": "provider_error",
                    "message": "回复生成失败，已保留你的消息。",
                    "details": {},
                }
            else:
                await self._finish(
                    turn,
                    MessageStatus.completed,
                    text,
                    started_at,
                    node_summary=final_node_summary or None,
                    route=final_route,
                )
                terminal = True
                yield {
                    "event": "message.completed",
                    "request_id": turn.request_id,
                    "message_id": turn.assistant_message_id,
                    "trace_id": turn.trace_id,
                    "display_text": text,
                    "speech_text": None,
                }
        except Exception as exc:
            await self._finish(
                turn,
                MessageStatus.failed,
                text,
                started_at,
                error_code="provider_error",
                error_message=str(exc),
                node_summary=final_node_summary or None,
                route=final_route,
            )
            terminal = True
            yield {
                "event": "message.failed",
                "request_id": turn.request_id,
                "message_id": turn.assistant_message_id,
                "trace_id": turn.trace_id,
                "display_text": text,
                "speech_text": None,
                "code": "provider_error",
                "message": "回复生成失败，已保留你的消息。",
                "details": {},
            }
        finally:
            try:
                if not terminal:
                    await self._classifier.cancel(turn.request_id)
                    await self._provider.cancel(turn.request_id)
                    await self._finish(
                        turn,
                        MessageStatus.cancelled,
                        text,
                        started_at,
                        node_summary=final_node_summary or None,
                        route=final_route,
                    )
            finally:
                # Release classifier state BEFORE registry release.
                await self._classifier.release(turn.request_id)
                await self._registry.release(turn.conversation_id, turn.request_id)

    async def cancel(self, request_id: UUID) -> bool:
        cancelled = await self._registry.cancel(request_id)
        if cancelled:
            await self._classifier.cancel(request_id)
            await self._provider.cancel(request_id)
        return cancelled
