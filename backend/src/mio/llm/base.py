from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ModelOptions:
    model: str
    temperature: float = 0.7


class ChatModelProvider(ABC):
    name: str

    @abstractmethod
    def stream(
        self,
        request_id: UUID,
        messages: list[ChatMessage],
        options: ModelOptions,
    ) -> AsyncIterator[str]:
        raise NotImplementedError

    @abstractmethod
    async def cancel(self, request_id: UUID) -> None:
        raise NotImplementedError

    async def aclose(self) -> None:
        return None

