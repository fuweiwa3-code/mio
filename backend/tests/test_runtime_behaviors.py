from uuid import uuid4

from sqlalchemy import select

from mio.chat.registry import ActiveRequestRegistry
from mio.db.models import AgentTrace, Conversation, Message, MessageStatus
from mio.services.recovery import recover_incomplete_generations


async def test_active_request_registry_rejects_second_request_for_conversation() -> None:
    registry = ActiveRequestRegistry()
    conversation_id = uuid4()
    first_request = uuid4()

    assert await registry.reserve(conversation_id, first_request) is True
    assert await registry.reserve(conversation_id, uuid4()) is False

    await registry.release(conversation_id, first_request)
    assert await registry.reserve(conversation_id, uuid4()) is True


async def test_recovery_marks_incomplete_message_and_trace_failed(app) -> None:
    session_factory = app.state.session_factory
    ids = app.state.demo_ids
    request_id = uuid4()

    async with session_factory() as session:
        conversation = Conversation(
            user_id=ids.user_id,
            companion_id=ids.companion_id,
            channel="web",
            title="恢复测试",
        )
        session.add(conversation)
        await session.flush()
        message = Message(
            conversation_id=conversation.id,
            role="assistant",
            display_text="未完成",
            status=MessageStatus.streaming,
            request_id=request_id,
        )
        trace = AgentTrace(
            conversation_id=conversation.id,
            request_id=request_id,
            status="streaming",
            provider="mock",
            model="mock",
        )
        session.add_all([message, trace])
        await session.commit()

    recovered = await recover_incomplete_generations(session_factory)

    async with session_factory() as session:
        stored_message = await session.scalar(
            select(Message).where(Message.request_id == request_id)
        )
        stored_trace = await session.scalar(
            select(AgentTrace).where(AgentTrace.request_id == request_id)
        )

    assert recovered == 1
    assert stored_message is not None
    assert stored_message.status == MessageStatus.failed
    assert stored_message.error_code == "generation_interrupted"
    assert stored_trace is not None
    assert stored_trace.status == "failed"
