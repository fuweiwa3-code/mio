from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from mio.db.models import ConversationStatus, MessageRole, MessageStatus


class CompanionProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    relationship_type: str
    speaking_style: str
    boundaries: list[str]


class ConversationCreate(BaseModel):
    title: str = Field(default="新对话", min_length=1, max_length=200)
    channel: Literal["web"] = "web"


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    channel: str
    title: str
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)
    source: Literal["text", "voice", "active_care", "system"] = "text"
    persist_history: bool = True
    allow_memory_extraction: bool = True


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: MessageRole
    display_text: str
    speech_text: str | None
    status: MessageStatus
    request_id: UUID | None
    source: str
    created_at: datetime
    updated_at: datetime


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    next_cursor: str | None


class CancelResponse(BaseModel):
    request_id: UUID
    cancelled: bool


class SSEPayload(BaseModel):
    request_id: UUID
    message_id: UUID
    trace_id: UUID
    display_text: str | None = None
    speech_text: str | None = None
    delta: str | None = None
    code: str | None = None
    message: str | None = None
    details: dict[str, Any] = {}

