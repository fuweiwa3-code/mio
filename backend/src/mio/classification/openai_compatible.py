"""OpenAI-compatible message classifier using /chat/completions."""

from __future__ import annotations

import asyncio
import json
from uuid import UUID

import httpx

from mio.classification.base import MessageClassifier
from mio.classification.exceptions import (
    ClassificationCancelledError,
    ClassificationProviderError,
    ClassificationSchemaInvalidError,
)
from mio.classification.models import ClassificationResult


class OpenAICompatibleMessageClassifier(MessageClassifier):
    """Classifies messages via an OpenAI-compatible /chat/completions endpoint.

    Uses stream=false, temperature=0, and requests strict JSON Schema output.
    The raw response content must be valid JSON matching ClassificationResult —
    no Markdown fence stripping, regex extraction, or fuzzy parsing.

    Lifecycle: prepare → classify → cancel → release
    The prepare() call registers the cancel Event before the SSE stream
    starts, eliminating the race where cancel arrives before classify.
    """

    name = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client = client or httpx.AsyncClient(timeout=60)
        self._owns_client = client is None
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._schema = ClassificationResult.model_json_schema()
        self._cancel_events: dict[UUID, asyncio.Event] = {}
        self._active_tasks: dict[UUID, asyncio.Task[ClassificationResult]] = {}

    async def prepare(self, request_id: UUID) -> None:
        """Register cancel Event so cancel() can find it before classify starts.

        Idempotent: does not overwrite an already-set Event.
        """
        if request_id not in self._cancel_events:
            self._cancel_events[request_id] = asyncio.Event()

    async def classify(self, text: str, *, request_id: UUID) -> ClassificationResult:
        """Classify with interruptible HTTP cancellation.

        Reuses the Event from prepare().  If no prepare() was called
        (e.g. direct unit test), creates one.  If the Event is already
        set, raises ClassificationCancelledError without I/O.
        """
        cancel_event = self._cancel_events.get(request_id)
        if cancel_event is None:
            cancel_event = asyncio.Event()
            self._cancel_events[request_id] = cancel_event

        if cancel_event.is_set():
            raise ClassificationCancelledError(
                f"classification cancelled for {request_id}"
            )

        current_task = asyncio.current_task()
        if current_task is not None:
            self._active_tasks[request_id] = current_task
        try:
            return await self._do_classify(text, request_id, cancel_event)
        except ClassificationCancelledError:
            raise
        except asyncio.CancelledError:
            raise
        except Exception:
            raise
        finally:
            # Only remove if we are still the active task for this request.
            if self._active_tasks.get(request_id) is current_task:
                del self._active_tasks[request_id]

    async def _do_classify(
        self,
        text: str,
        request_id: UUID,
        cancel_event: asyncio.Event,
    ) -> ClassificationResult:
        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Classify the user message into emotion, intent, and risk. "
                        "Respond with a JSON object matching the provided schema."
                    ),
                },
                {"role": "user", "content": text},
            ],
            "temperature": 0,
            "stream": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "classification_result",
                    "strict": True,
                    "schema": self._schema,
                },
            },
        }

        http_task: asyncio.Task[httpx.Response] = asyncio.ensure_future(
            self._client.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
        )
        cancel_task: asyncio.Task[bool] = asyncio.ensure_future(cancel_event.wait())

        try:
            await asyncio.wait(
                [http_task, cancel_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            if cancel_event.is_set():
                raise ClassificationCancelledError(
                    f"classification cancelled for {request_id}"
                )

            try:
                response = http_task.result()
            except httpx.HTTPError as exc:
                raise ClassificationProviderError(
                    f"Classification HTTP error: {exc}"
                ) from exc

            if response.status_code >= 400:
                raise ClassificationProviderError(
                    f"Classification provider returned HTTP {response.status_code}"
                )

            try:
                data = response.json()
            except (json.JSONDecodeError, ValueError) as exc:
                raise ClassificationProviderError(
                    "Classification provider returned invalid JSON response"
                ) from exc

            choices = data.get("choices")
            if not choices or not isinstance(choices, list):
                raise ClassificationProviderError(
                    "Classification response has empty or missing choices"
                )

            content = choices[0].get("message", {}).get("content")
            if not content or not isinstance(content, str):
                raise ClassificationSchemaInvalidError(
                    "Classification response has empty or missing content"
                )

            try:
                result = ClassificationResult.model_validate_json(content)
            except Exception as exc:
                raise ClassificationSchemaInvalidError(
                    f"Classification response failed schema validation: {exc}"
                ) from exc

            return result

        finally:
            if not http_task.done():
                http_task.cancel()
            if not cancel_task.done():
                cancel_task.cancel()
            await asyncio.gather(http_task, cancel_task, return_exceptions=True)

    async def cancel(self, request_id: UUID) -> None:
        """Signal cancellation for a prepared or in-flight request.

        Only signals if the Event exists (from prepare or classify).
        Does NOT create new Events — non-active request_ids are no-op.
        """
        event = self._cancel_events.get(request_id)
        if event is not None:
            event.set()

    async def release(self, request_id: UUID) -> None:
        """Remove all state for request_id.  Safe to call multiple times."""
        self._cancel_events.pop(request_id, None)
        self._active_tasks.pop(request_id, None)

    async def aclose(self) -> None:
        """Cancel all in-flight classifications and release resources."""
        # Signal all active cancel events.
        for event in self._cancel_events.values():
            event.set()
        # Wait for all active classify tasks to finish.
        active = list(self._active_tasks.values())
        if active:
            await asyncio.gather(*active, return_exceptions=True)
        self._cancel_events.clear()
        self._active_tasks.clear()
        if self._owns_client:
            await self._client.aclose()
