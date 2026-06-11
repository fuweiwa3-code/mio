import asyncio
from dataclasses import dataclass
from uuid import UUID


@dataclass
class ActiveRequest:
    request_id: UUID
    cancelled: asyncio.Event


class ActiveRequestRegistry:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._by_conversation: dict[UUID, ActiveRequest] = {}
        self._conversation_by_request: dict[UUID, UUID] = {}

    async def reserve(self, conversation_id: UUID, request_id: UUID) -> bool:
        async with self._lock:
            if conversation_id in self._by_conversation:
                return False
            self._by_conversation[conversation_id] = ActiveRequest(
                request_id=request_id,
                cancelled=asyncio.Event(),
            )
            self._conversation_by_request[request_id] = conversation_id
            return True

    async def cancel(self, request_id: UUID) -> bool:
        async with self._lock:
            conversation_id = self._conversation_by_request.get(request_id)
            if conversation_id is None:
                return False
            self._by_conversation[conversation_id].cancelled.set()
            return True

    async def is_cancelled(self, request_id: UUID) -> bool:
        async with self._lock:
            conversation_id = self._conversation_by_request.get(request_id)
            if conversation_id is None:
                return False
            return self._by_conversation[conversation_id].cancelled.is_set()

    async def release(self, conversation_id: UUID, request_id: UUID) -> None:
        async with self._lock:
            active = self._by_conversation.get(conversation_id)
            if active is None or active.request_id != request_id:
                return
            self._by_conversation.pop(conversation_id, None)
            self._conversation_by_request.pop(request_id, None)

