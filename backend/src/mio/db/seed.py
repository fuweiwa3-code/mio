from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from mio.db.models import CompanionProfile, User


@dataclass(frozen=True)
class DemoIds:
    user_id: UUID
    companion_id: UUID


async def seed_demo_data(
    session_factory: async_sessionmaker[AsyncSession],
) -> DemoIds:
    async with session_factory() as session:
        user = await session.scalar(select(User).where(User.username == "demo"))
        if user is None:
            user = User(username="demo", display_name="Demo Owner")
            session.add(user)
            await session.flush()

        profile = await session.scalar(
            select(CompanionProfile).where(
                CompanionProfile.user_id == user.id,
                CompanionProfile.name == "澪",
            )
        )
        if profile is None:
            profile = CompanionProfile(
                user_id=user.id,
                name="澪",
                relationship_type="稳定陪伴者",
                speaking_style="清冷慢热、认真克制、害羞可爱、短句优先，不使用客服腔。",
                boundaries=[
                    "不冒充真人或已有动漫角色",
                    "不诱导现实依赖",
                    "危机风险时停止暧昧表达并进入安全支持",
                ],
            )
            session.add(profile)
            await session.flush()

        await session.commit()
        return DemoIds(user_id=user.id, companion_id=profile.id)

