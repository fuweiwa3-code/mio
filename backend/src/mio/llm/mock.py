import asyncio
from collections.abc import AsyncIterator
from uuid import UUID

from mio.llm.base import ChatMessage, ChatModelProvider, ModelOptions


class MockChatModelProvider(ChatModelProvider):
    name = "mock"

    def __init__(self, chunk_delay_ms: int = 0) -> None:
        self._chunk_delay = chunk_delay_ms / 1000
        self._cancelled: set[UUID] = set()

    def _response_for(self, messages: list[ChatMessage]) -> str:
        user_text = next(
            (message.content for message in reversed(messages) if message.role == "user"),
            "",
        )
        if "累" in user_text or "烦" in user_text:
            return "嗯，先别逼自己太紧。我在这里，陪你把最难受的那一点慢慢拆开。"
        if "在吗" in user_text:
            return "在。你叫我，我就会回应。"
        return f"我听见了。关于“{user_text}”，我们可以慢一点说，我陪你。"

    async def stream(
        self,
        request_id: UUID,
        messages: list[ChatMessage],
        options: ModelOptions,
    ) -> AsyncIterator[str]:
        del options
        text = self._response_for(messages)
        for index in range(0, len(text), 6):
            if request_id in self._cancelled:
                break
            if self._chunk_delay:
                await asyncio.sleep(self._chunk_delay)
            if request_id in self._cancelled:
                break
            yield text[index : index + 6]
        self._cancelled.discard(request_id)

    async def cancel(self, request_id: UUID) -> None:
        self._cancelled.add(request_id)

