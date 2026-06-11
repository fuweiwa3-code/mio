from uuid import uuid4

import httpx

from mio.agent.prompt import build_persona_prompt
from mio.llm.base import ChatMessage, ModelOptions
from mio.llm.mock import MockChatModelProvider
from mio.llm.openai_compatible import OpenAICompatibleChatModelProvider


async def collect(provider, messages: list[ChatMessage]) -> str:
    chunks = [
        chunk
        async for chunk in provider.stream(
            request_id=uuid4(),
            messages=messages,
            options=ModelOptions(model="test-model"),
        )
    ]
    return "".join(chunks)


def test_persona_prompt_uses_profile_instead_of_hard_coded_route_text() -> None:
    prompt = build_persona_prompt(
        name="澪",
        relationship_type="陪伴者",
        speaking_style="清冷慢热，短句优先",
        boundaries=["不冒充真人", "危机时进入安全支持"],
    )

    assert "澪" in prompt
    assert "清冷慢热，短句优先" in prompt
    assert "不冒充真人" in prompt


async def test_mock_provider_is_deterministic_and_streams_multiple_chunks() -> None:
    provider = MockChatModelProvider(chunk_delay_ms=0)
    messages = [ChatMessage(role="user", content="今天写代码有点累。")]

    first = await collect(provider, messages)
    second = await collect(provider, messages)

    assert first == second
    assert "陪你" in first


async def test_mock_provider_honors_cancellation() -> None:
    provider = MockChatModelProvider(chunk_delay_ms=5)
    request_id = uuid4()
    iterator = provider.stream(
        request_id=request_id,
        messages=[ChatMessage(role="user", content="测试取消")],
        options=ModelOptions(model="mock"),
    )

    first = await anext(iterator)
    await provider.cancel(request_id)

    assert first
    assert [chunk async for chunk in iterator] == []


async def test_openai_compatible_provider_parses_chat_completion_sse() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        lines = [
            'data: {"choices":[{"delta":{"content":"嗯，"}}]}',
            'data: {"choices":[{"delta":{"content":"我在。"}}]}',
            "data: [DONE]",
        ]
        return httpx.Response(200, text="\n\n".join(lines))

    provider = OpenAICompatibleChatModelProvider(
        base_url="https://llm.example/v1",
        api_key="secret",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    result = await collect(provider, [ChatMessage(role="user", content="你在吗")])

    assert result == "嗯，我在。"
    await provider.aclose()
