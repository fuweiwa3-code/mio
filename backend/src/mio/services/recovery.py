from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from mio.db.models import AgentTrace, Message, MessageStatus


async def recover_incomplete_generations(
    session_factory: async_sessionmaker[AsyncSession],
) -> int:
    async with session_factory() as session:
        messages = list(
            await session.scalars(
                select(Message).where(
                    Message.status.in_([MessageStatus.pending, MessageStatus.streaming])
                )
            )
        )
        request_ids = [message.request_id for message in messages if message.request_id]
        for message in messages:
            message.status = MessageStatus.failed
            message.error_code = "generation_interrupted"
            message.error_message = "服务重启导致生成中断。"

        if request_ids:
            traces = list(
                await session.scalars(
                    select(AgentTrace).where(AgentTrace.request_id.in_(request_ids))
                )
            )
            for trace in traces:
                trace.status = "failed"
                trace.error_stage = "recovery"
                trace.error_code = "generation_interrupted"

        await session.commit()
        return len(messages)

