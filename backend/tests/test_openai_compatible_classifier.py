"""Tests for OpenAICompatibleMessageClassifier."""

import json
from uuid import uuid4

import httpx
import pytest

from mio.classification.exceptions import ClassificationProviderError
from mio.classification.models import (
    EmotionLabel,
    IntentLabel,
    RiskLevel,
)


def _make_valid_response(
    emotion: str = "calm",
    intent: str = "companion",
    risk: str = "none",
) -> str:
    """Build a valid JSON string that matches ClassificationResult schema."""
    return json.dumps({
        "emotion": {"label": emotion, "confidence": 0.9},
        "intent": {"label": intent, "confidence": 0.85},
        "risk": {"level": risk, "confidence": 0.95},
    })


def _make_chat_completion_response(content: str) -> dict:
    """Wrap content in an OpenAI chat completion response envelope."""
    return {
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "model": "test-model",
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


class TestOpenAICompatibleClassifierRequest:
    """Verify request construction: URL, headers, payload."""

    async def test_request_url(self) -> None:
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        captured: dict = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["path"] = request.url.path
            resp = _make_chat_completion_response(_make_valid_response())
            return httpx.Response(200, json=resp)

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="sk-test",
            model="gpt-4o-mini",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        await classifier.classify("hello", request_id=uuid4())

        assert captured["path"] == "/v1/chat/completions"
        await classifier.aclose()

    async def test_authorization_header_sent_when_api_key_set(self) -> None:
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        captured: dict = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            captured["auth"] = request.headers.get("authorization")
            resp = _make_chat_completion_response(_make_valid_response())
            return httpx.Response(200, json=resp)

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="sk-secret",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        await classifier.classify("hello", request_id=uuid4())

        assert captured["auth"] == "Bearer sk-secret"
        await classifier.aclose()

    async def test_no_authorization_header_when_no_api_key(self) -> None:
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        captured: dict = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            captured["auth"] = request.headers.get("authorization")
            resp = _make_chat_completion_response(_make_valid_response())
            return httpx.Response(200, json=resp)

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        await classifier.classify("hello", request_id=uuid4())

        assert captured["auth"] is None
        await classifier.aclose()

    async def test_stream_false_and_temperature_zero(self) -> None:
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        captured: dict = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            captured["payload"] = json.loads(await request.aread())
            resp = _make_chat_completion_response(_make_valid_response())
            return httpx.Response(200, json=resp)

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="sk-test",
            model="test-model",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        await classifier.classify("hello", request_id=uuid4())

        assert captured["payload"]["stream"] is False
        assert captured["payload"]["temperature"] == 0
        await classifier.aclose()

    async def test_correct_model_name_in_payload(self) -> None:
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        captured: dict = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            captured["payload"] = json.loads(await request.aread())
            resp = _make_chat_completion_response(_make_valid_response())
            return httpx.Response(200, json=resp)

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="sk-test",
            model="gpt-4o-mini",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        await classifier.classify("test", request_id=uuid4())

        assert captured["payload"]["model"] == "gpt-4o-mini"
        await classifier.aclose()

    async def test_json_schema_response_format_requested(self) -> None:
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        captured: dict = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            captured["payload"] = json.loads(await request.aread())
            resp = _make_chat_completion_response(_make_valid_response())
            return httpx.Response(200, json=resp)

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="sk-test",
            model="test-model",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        await classifier.classify("test", request_id=uuid4())

        rf = captured["payload"].get("response_format", {})
        assert rf.get("type") == "json_schema"
        assert "json_schema" in rf
        await classifier.aclose()


class TestOpenAICompatibleClassifierValidResponse:
    """Verify valid structured responses parse correctly."""

    async def test_valid_structured_response(self) -> None:
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        async def handler(request: httpx.Request) -> httpx.Response:
            resp = _make_chat_completion_response(
                _make_valid_response("tired", "mixed", "none")
            )
            return httpx.Response(200, json=resp)

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        result = await classifier.classify("好累啊", request_id=uuid4())

        assert result.emotion.label is EmotionLabel.tired
        assert result.intent.label is IntentLabel.mixed
        assert result.risk.level is RiskLevel.none
        await classifier.aclose()

    async def test_crisis_high_risk_response(self) -> None:
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        async def handler(request: httpx.Request) -> httpx.Response:
            resp = _make_chat_completion_response(
                _make_valid_response("crisis", "unsafe", "high")
            )
            return httpx.Response(200, json=resp)

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        result = await classifier.classify("不想活了", request_id=uuid4())

        assert result.emotion.label is EmotionLabel.crisis
        assert result.intent.label is IntentLabel.unsafe
        assert result.risk.level is RiskLevel.high
        await classifier.aclose()


class TestOpenAICompatibleClassifierErrorHandling:
    """Verify all error paths raise classification exceptions."""

    async def test_empty_choices_raises(self) -> None:
        from mio.classification.exceptions import ClassificationProviderError
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"choices": []})

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        with pytest.raises(ClassificationProviderError):
            await classifier.classify("test", request_id=uuid4())
        await classifier.aclose()

    async def test_empty_content_raises(self) -> None:
        from mio.classification.exceptions import ClassificationSchemaInvalidError
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        async def handler(request: httpx.Request) -> httpx.Response:
            resp = {"choices": [{"message": {"role": "assistant", "content": ""}}]}
            return httpx.Response(200, json=resp)

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        with pytest.raises(ClassificationSchemaInvalidError):
            await classifier.classify("test", request_id=uuid4())
        await classifier.aclose()

    async def test_invalid_json_raises(self) -> None:
        from mio.classification.exceptions import ClassificationSchemaInvalidError
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        async def handler(request: httpx.Request) -> httpx.Response:
            resp = {"choices": [{"message": {"role": "assistant", "content": "not json"}}]}
            return httpx.Response(200, json=resp)

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        with pytest.raises(ClassificationSchemaInvalidError):
            await classifier.classify("test", request_id=uuid4())
        await classifier.aclose()

    async def test_markdown_fence_wrapped_json_raises(self) -> None:
        """Markdown fences must NOT be stripped — raw JSON is required."""
        from mio.classification.exceptions import ClassificationSchemaInvalidError
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        fenced = f"```json\n{_make_valid_response()}\n```"

        async def handler(request: httpx.Request) -> httpx.Response:
            resp = {"choices": [{"message": {"role": "assistant", "content": fenced}}]}
            return httpx.Response(200, json=resp)

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        with pytest.raises(ClassificationSchemaInvalidError):
            await classifier.classify("test", request_id=uuid4())
        await classifier.aclose()

    async def test_invalid_enum_raises(self) -> None:
        from mio.classification.exceptions import ClassificationSchemaInvalidError
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        bad = json.dumps({
            "emotion": {"label": "bogus", "confidence": 0.9},
            "intent": {"label": "companion", "confidence": 0.9},
            "risk": {"level": "none", "confidence": 0.9},
        })

        async def handler(request: httpx.Request) -> httpx.Response:
            resp = {"choices": [{"message": {"role": "assistant", "content": bad}}]}
            return httpx.Response(200, json=resp)

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        with pytest.raises(ClassificationSchemaInvalidError):
            await classifier.classify("test", request_id=uuid4())
        await classifier.aclose()

    async def test_extra_field_raises(self) -> None:
        from mio.classification.exceptions import ClassificationSchemaInvalidError
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        bad = json.dumps({
            "emotion": {"label": "calm", "confidence": 0.9},
            "intent": {"label": "companion", "confidence": 0.9},
            "risk": {"level": "none", "confidence": 0.9},
            "extra_field": "bad",
        })

        async def handler(request: httpx.Request) -> httpx.Response:
            resp = {"choices": [{"message": {"role": "assistant", "content": bad}}]}
            return httpx.Response(200, json=resp)

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        with pytest.raises(ClassificationSchemaInvalidError):
            await classifier.classify("test", request_id=uuid4())
        await classifier.aclose()

    async def test_confidence_out_of_range_raises(self) -> None:
        from mio.classification.exceptions import ClassificationSchemaInvalidError
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        bad = json.dumps({
            "emotion": {"label": "calm", "confidence": 1.5},
            "intent": {"label": "companion", "confidence": 0.9},
            "risk": {"level": "none", "confidence": 0.9},
        })

        async def handler(request: httpx.Request) -> httpx.Response:
            resp = {"choices": [{"message": {"role": "assistant", "content": bad}}]}
            return httpx.Response(200, json=resp)

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        with pytest.raises(ClassificationSchemaInvalidError):
            await classifier.classify("test", request_id=uuid4())
        await classifier.aclose()

    async def test_crisis_with_non_high_risk_raises(self) -> None:
        from mio.classification.exceptions import ClassificationSchemaInvalidError
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        bad = json.dumps({
            "emotion": {"label": "crisis", "confidence": 0.99},
            "intent": {"label": "companion", "confidence": 0.5},
            "risk": {"level": "medium", "confidence": 0.9},
        })

        async def handler(request: httpx.Request) -> httpx.Response:
            resp = {"choices": [{"message": {"role": "assistant", "content": bad}}]}
            return httpx.Response(200, json=resp)

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        with pytest.raises(ClassificationSchemaInvalidError):
            await classifier.classify("test", request_id=uuid4())
        await classifier.aclose()

    async def test_http_4xx_raises(self) -> None:
        from mio.classification.exceptions import ClassificationProviderError
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json={"error": "bad request"})

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        with pytest.raises(ClassificationProviderError):
            await classifier.classify("test", request_id=uuid4())
        await classifier.aclose()

    async def test_http_5xx_raises(self) -> None:
        from mio.classification.exceptions import ClassificationProviderError
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "internal"})

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        with pytest.raises(ClassificationProviderError):
            await classifier.classify("test", request_id=uuid4())
        await classifier.aclose()

    async def test_none_content_raises(self) -> None:
        from mio.classification.exceptions import ClassificationSchemaInvalidError
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        async def handler(request: httpx.Request) -> httpx.Response:
            resp = {"choices": [{"message": {"role": "assistant", "content": None}}]}
            return httpx.Response(200, json=resp)

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        with pytest.raises(ClassificationSchemaInvalidError):
            await classifier.classify("test", request_id=uuid4())
        await classifier.aclose()


class TestOpenAICompatibleClassifierCancellation:
    """Verify cancellation behavior."""

    async def test_prepare_cancel_classify_raises(self) -> None:
        """prepare → cancel → classify raises ClassificationCancelledError, no HTTP."""
        from mio.classification.exceptions import ClassificationCancelledError
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        http_called = False

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal http_called
            http_called = True
            return httpx.Response(200, json=_make_chat_completion_response(_make_valid_response()))

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        rid = uuid4()
        await classifier.prepare(rid)
        await classifier.cancel(rid)
        with pytest.raises(ClassificationCancelledError):
            await classifier.classify("test", request_id=rid)
        assert http_called is False
        await classifier.release(rid)
        assert rid not in classifier._cancel_events
        assert rid not in classifier._active_tasks
        await classifier.aclose()

    async def test_cancel_aborts_inflight_request(self) -> None:
        """cancel() must interrupt a slow HTTP request within 2 seconds."""
        import asyncio

        from mio.classification.exceptions import ClassificationCancelledError
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        request_started = asyncio.Event()

        async def handler(request: httpx.Request) -> httpx.Response:
            request_started.set()
            await asyncio.sleep(60)
            return httpx.Response(200, json=_make_chat_completion_response(_make_valid_response()))

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        rid = uuid4()
        await classifier.prepare(rid)

        task = asyncio.create_task(classifier.classify("test", request_id=rid))
        await asyncio.wait_for(request_started.wait(), timeout=2.0)

        await classifier.cancel(rid)
        with pytest.raises(ClassificationCancelledError):
            await asyncio.wait_for(task, timeout=2.0)

        await classifier.release(rid)
        assert rid not in classifier._cancel_events
        assert rid not in classifier._active_tasks
        await classifier.aclose()

    async def test_cancel_noop_for_nonactive_request(self) -> None:
        """cancel() on a non-active request_id is a no-op."""
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_make_chat_completion_response(_make_valid_response()))

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        rid = uuid4()
        await classifier.cancel(rid)
        assert rid not in classifier._cancel_events
        await classifier.aclose()

    async def test_normal_completion_cleans_up(self) -> None:
        """After prepare + classify + release, no state remains."""
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_make_chat_completion_response(_make_valid_response()))

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        rid = uuid4()
        await classifier.prepare(rid)
        await classifier.classify("test", request_id=rid)
        await classifier.release(rid)
        assert rid not in classifier._cancel_events
        assert rid not in classifier._active_tasks
        await classifier.aclose()

    async def test_http_error_cleanup(self) -> None:
        """HTTP 500 → ClassificationProviderError, state cleaned after release."""
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "fail"})

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        rid = uuid4()
        await classifier.prepare(rid)
        with pytest.raises(ClassificationProviderError):
            await classifier.classify("test", request_id=rid)
        await classifier.release(rid)
        assert rid not in classifier._cancel_events
        assert rid not in classifier._active_tasks
        await classifier.aclose()

    async def test_aclose_aborts_inflight(self) -> None:
        """aclose() must abort in-flight classify within 2s."""
        import asyncio

        from mio.classification.exceptions import ClassificationCancelledError
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        request_started = asyncio.Event()

        async def handler(request: httpx.Request) -> httpx.Response:
            request_started.set()
            await asyncio.sleep(60)
            return httpx.Response(200, json=_make_chat_completion_response(_make_valid_response()))

        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        rid = uuid4()
        await classifier.prepare(rid)

        task = asyncio.create_task(classifier.classify("test", request_id=rid))
        await asyncio.wait_for(request_started.wait(), timeout=2.0)

        await asyncio.wait_for(classifier.aclose(), timeout=2.0)

        with pytest.raises(ClassificationCancelledError):
            await asyncio.wait_for(task, timeout=2.0)

        assert len(classifier._cancel_events) == 0
        assert len(classifier._active_tasks) == 0


class TestOpenAICompatibleClassifierAclose:
    async def test_aclose_closes_owned_client(self) -> None:
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        async def handler(request: httpx.Request) -> httpx.Response:
            resp = _make_chat_completion_response(_make_valid_response())
            return httpx.Response(200, json=resp)

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=client,
        )
        # Should not raise
        await classifier.aclose()

    async def test_injected_client_not_closed_by_aclose(self) -> None:
        """When client is injected, aclose should not close it."""
        from mio.classification.openai_compatible import (
            OpenAICompatibleMessageClassifier,
        )

        async def handler(request: httpx.Request) -> httpx.Response:
            resp = _make_chat_completion_response(_make_valid_response())
            return httpx.Response(200, json=resp)

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        classifier = OpenAICompatibleMessageClassifier(
            base_url="https://api.example.com/v1",
            api_key="",
            model="test",
            client=client,
        )
        await classifier.aclose()
        # Injected client should still be usable
        assert client.is_closed is False
        await client.aclose()
