from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mio.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ConversationStatus(StrEnum):
    active = "active"
    archived = "archived"


class MessageRole(StrEnum):
    user = "user"
    assistant = "assistant"
    system = "system"


class MessageStatus(StrEnum):
    completed = "completed"
    pending = "pending"
    streaming = "streaming"
    cancelled = "cancelled"
    failed = "failed"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)


class CompanionProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "companion_profiles"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_companion_user_name"),)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False)
    speaking_style: Mapped[str] = mapped_column(Text, nullable=False)
    boundaries: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_user_updated", "user_id", "updated_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    companion_id: Mapped[UUID] = mapped_column(
        ForeignKey("companion_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(String(32), default="web", nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="新对话", nullable=False)
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus, native_enum=False, length=32),
        default=ConversationStatus.active,
        nullable=False,
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class Message(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_created", "conversation_id", "created_at", "id"),
        Index("ix_messages_active_generation", "conversation_id", "status"),
        UniqueConstraint("request_id", name="uq_messages_request_id"),
    )

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, native_enum=False, length=32),
        nullable=False,
    )
    display_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    speech_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[MessageStatus] = mapped_column(
        Enum(MessageStatus, native_enum=False, length=32),
        default=MessageStatus.completed,
        nullable=False,
    )
    request_id: Mapped[UUID | None] = mapped_column(nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="text", nullable=False)
    persist_history: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_memory_extraction: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class AgentTrace(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_traces"

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    request_id: Mapped[UUID] = mapped_column(unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    error_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    node_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

