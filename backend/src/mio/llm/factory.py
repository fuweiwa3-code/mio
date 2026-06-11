from mio.config import Settings
from mio.llm.base import ChatModelProvider
from mio.llm.mock import MockChatModelProvider
from mio.llm.openai_compatible import OpenAICompatibleChatModelProvider


def create_chat_model_provider(settings: Settings) -> ChatModelProvider:
    if settings.llm_provider == "openai_compatible":
        if not settings.llm_base_url:
            raise ValueError("MIO_LLM_BASE_URL is required for openai_compatible")
        return OpenAICompatibleChatModelProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
        )
    return MockChatModelProvider(chunk_delay_ms=settings.mock_chunk_delay_ms)

