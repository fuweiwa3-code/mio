import json
from collections.abc import AsyncIterator
from uuid import UUID

import httpx

from mio.llm.base import ChatMessage, ChatModelProvider, ModelOptions


class OpenAICompatibleChatModelProvider(ChatModelProvider):
    name = "openai_compatible"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client = client or httpx.AsyncClient(timeout=60)
        self._owns_client = client is None
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._cancelled: set[UUID] = set()

    async def stream(
        self,
        request_id: UUID,
        messages: list[ChatMessage],
        options: ModelOptions,
    ) -> AsyncIterator[str]:
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        payload = {
            "model": options.model,
            "messages": [
                {"role": message.role, "content": message.content} for message in messages
            ],
            "temperature": options.temperature,
            "stream": True,
        }
        async with self._client.stream(
            "POST",
            f"{self._base_url}/chat/completions",
            headers=headers,
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if request_id in self._cancelled:
                    break
                if not line.startswith("data: "):
                    continue
                data = line.removeprefix("data: ")
                if data == "[DONE]":
                    break
                chunk = json.loads(data)
                content = chunk["choices"][0].get("delta", {}).get("content")
                if content:
                    yield content
        self._cancelled.discard(request_id)

    async def cancel(self, request_id: UUID) -> None:
        self._cancelled.add(request_id)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

