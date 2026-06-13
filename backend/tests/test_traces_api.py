"""Tests for AgentTrace query API (Phase 4A).

Covers list, detail, cursor pagination, owner isolation, sanitization,
and sensitive data filtering for GET /api/v1/traces and
GET /api/v1/traces/{trace_id}.
"""

from __future__ import annotations

import base64
from uuid import UUID, uuid4

from httpx import AsyncClient

from mio.db.models import AgentTrace, Conversation, ConversationStatus, User

# ── Helpers ────────────────────────────────────────────────────────


async def _create_conversation(client: AsyncClient) -> str:
    response = await client.post("/api/v1/conversations", json={})
    assert response.status_code == 201
    return response.json()["id"]


async def _send_message(client: AsyncClient, conversation_id: str, content: str) -> None:
    response = await client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": content, "source": "text"},
    )
    assert response.status_code == 200


async def _drain(stream):
    return [e async for e in stream]


# ── Test 1: List normal return ─────────────────────────────────────


class TestTraceListNormalReturn:
    """Verify GET /api/v1/traces returns items and next_cursor."""

    async def test_list_traces_returns_items(self, app, client: AsyncClient) -> None:
        cid = await _create_conversation(client)
        await _send_message(client, cid, "你好")

        response = await client.get("/api/v1/traces")

        assert response.status_code == 200
        body = response.json()
        assert "items" in body
        assert "next_cursor" in body
        assert isinstance(body["items"], list)
        assert len(body["items"]) >= 1
        # Verify first item has required fields
        item = body["items"][0]
        assert "id" in item
        assert "conversation_id" in item
        assert "request_id" in item
        assert "status" in item
        assert "provider" in item
        assert "model" in item
        assert "node_summary" in item
        assert "created_at" in item
        assert "updated_at" in item


# ── Test 2: List descending order ──────────────────────────────────


class TestTraceListDescendingOrder:
    """Verify traces are ordered by created_at DESC, id DESC."""

    async def test_list_traces_descending_order(self, app, client: AsyncClient) -> None:
        cid = await _create_conversation(client)
        await _send_message(client, cid, "第一条")
        await _send_message(client, cid, "第二条")

        response = await client.get("/api/v1/traces", params={"limit": 50})
        items = response.json()["items"]

        assert len(items) >= 2
        # Most recent first
        assert items[0]["created_at"] >= items[1]["created_at"]


# ── Test 3: conversation_id filter ─────────────────────────────────


class TestTraceListConversationFilter:
    """Verify filtering by conversation_id returns only matching traces."""

    async def test_filter_by_conversation_id(self, app, client: AsyncClient) -> None:
        cid1 = await _create_conversation(client)
        cid2 = await _create_conversation(client)
        await _send_message(client, cid1, "对话一")
        await _send_message(client, cid2, "对话二")

        response = await client.get(
            "/api/v1/traces",
            params={"conversation_id": cid1},
        )
        items = response.json()["items"]

        assert len(items) >= 1
        for item in items:
            assert item["conversation_id"] == cid1


# ── Test 4: status filter ──────────────────────────────────────────


class TestTraceListStatusFilter:
    """Verify filtering by status."""

    async def test_filter_by_status(self, app, client: AsyncClient) -> None:
        cid = await _create_conversation(client)
        await _send_message(client, cid, "你好")

        response = await client.get(
            "/api/v1/traces",
            params={"status": "completed"},
        )
        items = response.json()["items"]

        assert len(items) >= 1
        for item in items:
            assert item["status"] == "completed"

    async def test_filter_by_nonexistent_status_returns_empty(
        self, app, client: AsyncClient
    ) -> None:
        response = await client.get(
            "/api/v1/traces",
            params={"status": "nonexistent_status"},
        )
        assert response.status_code == 200
        assert response.json()["items"] == []


# ── Test 5: limit validation ───────────────────────────────────────


class TestTraceListLimitValidation:
    """Verify limit parameter bounds (1~100)."""

    async def test_limit_below_minimum_returns_422(
        self, app, client: AsyncClient
    ) -> None:
        response = await client.get("/api/v1/traces", params={"limit": 0})
        assert response.status_code == 422

    async def test_limit_above_maximum_returns_422(
        self, app, client: AsyncClient
    ) -> None:
        response = await client.get("/api/v1/traces", params={"limit": 101})
        assert response.status_code == 422

    async def test_limit_at_minimum_works(self, app, client: AsyncClient) -> None:
        response = await client.get("/api/v1/traces", params={"limit": 1})
        assert response.status_code == 200

    async def test_limit_at_maximum_works(self, app, client: AsyncClient) -> None:
        response = await client.get("/api/v1/traces", params={"limit": 100})
        assert response.status_code == 200


# ── Test 6: Multi-page cursor no duplicates/omissions ─────────────


class TestTraceListCursorPagination:
    """Verify cursor pagination has no duplicates or omissions."""

    async def test_cursor_pagination_completeness(self, app, client: AsyncClient) -> None:
        cid = await _create_conversation(client)
        # Create 5 traces
        for i in range(5):
            await _send_message(client, cid, f"消息 {i + 1}")

        all_ids: list[str] = []
        cursor: str | None = None
        pages = 0

        while True:
            params: dict[str, object] = {"limit": 2}
            if cursor:
                params["cursor"] = cursor
            response = await client.get("/api/v1/traces", params=params)
            body = response.json()
            for item in body["items"]:
                all_ids.append(item["id"])
            cursor = body["next_cursor"]
            pages += 1
            if cursor is None:
                break
            if pages > 20:
                raise AssertionError("Cursor pagination did not terminate")

        # No duplicates
        assert len(all_ids) == len(set(all_ids))
        # All 5 traces accounted for (may be more if other tests left data,
        # but in test isolation each test gets its own DB)
        assert len(all_ids) >= 5


# ── Test 7: Invalid cursor returns 400 ─────────────────────────────


class TestTraceListInvalidCursor:
    """Verify invalid cursor returns unified 400 error."""

    async def test_invalid_cursor_returns_400(self, app, client: AsyncClient) -> None:
        response = await client.get(
            "/api/v1/traces",
            params={"cursor": "not-a-valid-cursor"},
        )
        assert response.status_code == 400
        body = response.json()
        assert body["code"] == "invalid_cursor"
        assert "trace_id" in body

    async def test_malformed_base64_cursor_returns_400(
        self, app, client: AsyncClient
    ) -> None:
        cursor = base64.urlsafe_b64encode(b"invalid|data").decode()
        response = await client.get(
            "/api/v1/traces",
            params={"cursor": cursor},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "invalid_cursor"


# ── Test 8: Single detail normal return ────────────────────────────


class TestTraceDetailNormalReturn:
    """Verify GET /api/v1/traces/{trace_id} returns full trace."""

    async def test_get_trace_detail(self, app, client: AsyncClient) -> None:
        cid = await _create_conversation(client)
        await _send_message(client, cid, "你好")

        # Get trace id from list
        listing = await client.get("/api/v1/traces")
        trace_id = listing.json()["items"][0]["id"]

        response = await client.get(f"/api/v1/traces/{trace_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == trace_id
        assert body["conversation_id"] is not None
        assert body["request_id"] is not None
        assert body["status"] is not None
        assert body["provider"] is not None
        assert body["model"] is not None
        assert "duration_ms" in body
        assert "error_stage" in body
        assert "error_code" in body
        assert "emotion_label" in body
        assert "emotion_confidence" in body
        assert "intent_label" in body
        assert "intent_confidence" in body
        assert "risk_level" in body
        assert "risk_confidence" in body
        assert "classification_status" in body
        assert "classification_error_code" in body
        assert "route" in body
        assert "trace_schema_version" in body
        assert "node_summary" in body
        assert "created_at" in body
        assert "updated_at" in body


# ── Test 9: Non-existent trace returns 404 ─────────────────────────


class TestTraceDetailNotFound:
    """Verify non-existent trace returns 404 trace_not_found."""

    async def test_nonexistent_trace_returns_404(self, app, client: AsyncClient) -> None:
        fake_id = uuid4()
        response = await client.get(f"/api/v1/traces/{fake_id}")

        assert response.status_code == 404
        body = response.json()
        assert body["code"] == "trace_not_found"
        assert "trace_id" in body
        assert body["details"] == {}


# ── Test 10: Other owner's trace returns 404 ───────────────────────


class TestTraceDetailOwnerIsolation:
    """Verify other user's trace returns 404, not 403."""

    async def test_other_owner_trace_returns_404(
        self, app, client: AsyncClient
    ) -> None:
        """Insert a trace owned by another user, verify 404 (not 403)."""
        service = app.state.conversation_service

        # Create another user and conversation directly in DB
        other_user_id = uuid4()
        other_conv_id = uuid4()
        other_trace_id = uuid4()

        async with service._session_factory() as session:
            other_user = User(
                id=other_user_id,
                username="other_user",
                display_name="Other",
            )
            session.add(other_user)
            await session.flush()

            other_conv = Conversation(
                id=other_conv_id,
                user_id=other_user_id,
                companion_id=app.state.demo_ids.companion_id,
                channel="web",
                title="Other conversation",
                status=ConversationStatus.active,
            )
            session.add(other_conv)
            await session.flush()

            other_trace = AgentTrace(
                id=other_trace_id,
                conversation_id=other_conv_id,
                request_id=uuid4(),
                status="completed",
                provider="mock",
                model="mock-mio",
                duration_ms=100,
                node_summary={},
            )
            session.add(other_trace)
            await session.commit()

        # Try to access other user's trace via API
        response = await client.get(f"/api/v1/traces/{other_trace_id}")

        assert response.status_code == 404
        body = response.json()
        assert body["code"] == "trace_not_found"
        # Must NOT return 403 to avoid information disclosure

    async def test_other_owner_trace_not_in_list(
        self, app, client: AsyncClient
    ) -> None:
        """Other user's traces must not appear in list endpoint."""
        service = app.state.conversation_service

        other_user_id = uuid4()
        other_conv_id = uuid4()

        async with service._session_factory() as session:
            other_user = User(
                id=other_user_id,
                username="other_user_2",
                display_name="Other 2",
            )
            session.add(other_user)
            await session.flush()

            other_conv = Conversation(
                id=other_conv_id,
                user_id=other_user_id,
                companion_id=app.state.demo_ids.companion_id,
                channel="web",
                title="Other conversation 2",
                status=ConversationStatus.active,
            )
            session.add(other_conv)
            await session.flush()

            other_trace = AgentTrace(
                conversation_id=other_conv_id,
                request_id=uuid4(),
                status="completed",
                provider="mock",
                model="mock-mio",
                duration_ms=100,
                node_summary={},
            )
            session.add(other_trace)
            await session.commit()

        response = await client.get("/api/v1/traces")
        items = response.json()["items"]

        # Other user's trace must NOT appear
        trace_ids = [item["id"] for item in items]
        assert str(other_trace.id) not in trace_ids


# ── Test 11: Historical NULL classification fields ─────────────────


class TestTraceDetailHistoricalNull:
    """Verify v1 traces with NULL classification fields return properly."""

    async def test_historical_trace_null_fields(self, app, client: AsyncClient) -> None:
        service = app.state.conversation_service
        cid = await _create_conversation(client)

        # Insert a historical v1 trace with NULL classification fields
        trace_id = uuid4()
        async with service._session_factory() as session:
            trace = AgentTrace(
                id=trace_id,
                conversation_id=UUID(cid),
                request_id=uuid4(),
                status="completed",
                provider="mock",
                model="mock-mio",
                duration_ms=150,
                node_summary={
                    "load_context": "completed",
                    "stream_llm": "completed",
                },
                # All classification fields NULL (v1 style)
            )
            session.add(trace)
            await session.commit()

        response = await client.get(f"/api/v1/traces/{trace_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["emotion_label"] is None
        assert body["emotion_confidence"] is None
        assert body["intent_label"] is None
        assert body["intent_confidence"] is None
        assert body["risk_level"] is None
        assert body["risk_confidence"] is None
        assert body["classification_status"] is None
        assert body["classification_error_code"] is None
        assert body["route"] is None
        # trace_schema_version: NULL in DB → API returns 1 per spec decision
        assert body["trace_schema_version"] == 1


# ── Test 12: New trace returns classification/risk/route fields ────


class TestTraceDetailNewTraceFields:
    """Verify new v2 traces return classification, risk, and route fields."""

    async def test_new_trace_has_classification_fields(
        self, app, client: AsyncClient
    ) -> None:
        cid = await _create_conversation(client)
        await _send_message(client, cid, "好累啊")

        listing = await client.get("/api/v1/traces")
        items = listing.json()["items"]
        assert len(items) >= 1

        trace_id = items[0]["id"]
        response = await client.get(f"/api/v1/traces/{trace_id}")
        body = response.json()

        # New trace (v2) must have classification fields
        assert body["trace_schema_version"] == 2
        assert body["emotion_label"] is not None
        assert body["emotion_confidence"] is not None
        assert body["intent_label"] is not None
        assert body["intent_confidence"] is not None
        assert body["risk_level"] is not None
        assert body["risk_confidence"] is not None
        assert body["classification_status"] is not None
        assert body["route"] is not None


# ── Test 13: node_summary only returns whitelist fields ────────────


class TestTraceNodeSummaryWhitelist:
    """Verify node_summary only returns status, duration_ms, error_code."""

    async def test_node_summary_whitelist_fields_only(
        self, app, client: AsyncClient
    ) -> None:
        cid = await _create_conversation(client)
        await _send_message(client, cid, "你好")

        listing = await client.get("/api/v1/traces")
        trace_id = listing.json()["items"][0]["id"]
        response = await client.get(f"/api/v1/traces/{trace_id}")
        node_summary = response.json()["node_summary"]

        allowed_keys = {"status", "duration_ms", "error_code"}
        for node_name, node_data in node_summary.items():
            if isinstance(node_data, dict):
                for key in node_data:
                    assert key in allowed_keys, (
                        f"Node '{node_name}' has unexpected key '{key}'"
                    )


# ── Test 14: Sensitive keys not leaked in detail ───────────────────


class TestTraceDetailSensitiveDataFiltering:
    """Verify sensitive data never appears in API response."""

    async def test_sensitive_keys_filtered_from_node_summary(
        self, app, client: AsyncClient
    ) -> None:
        """Construct node_summary with sensitive keys, verify none leak."""
        service = app.state.conversation_service
        cid = await _create_conversation(client)

        sensitive_summary = {
            "load_context": {
                "status": "completed",
                "duration_ms": 5,
                "error_code": None,
                "prompt": "SECRET_SYSTEM_PROMPT_VALUE",
                "messages": "user said something private",
                "api_key": "sk-1234567890abcdef",
                "authorization": "Bearer sk-secret-token",
                "stack_trace": "Traceback (most recent call last):\n  File ...",
                "error_message": "connection to db failed: postgres://user:pass@host",
                "details": {"raw_response": "full model output"},
            },
            "stream_llm": {
                "status": "completed",
                "duration_ms": 200,
                "error_code": None,
                "api_key": "sk-leaked-key",
                "prompt": "You are Mio...",
            },
        }

        trace_id = uuid4()
        async with service._session_factory() as session:
            trace = AgentTrace(
                id=trace_id,
                conversation_id=UUID(cid),
                request_id=uuid4(),
                status="completed",
                provider="mock",
                model="mock-mio",
                duration_ms=200,
                node_summary=sensitive_summary,
                trace_schema_version=2,
            )
            session.add(trace)
            await session.commit()

        response = await client.get(f"/api/v1/traces/{trace_id}")
        assert response.status_code == 200
        body = response.text

        # None of these sensitive values must appear in the response
        sensitive_values = [
            "SECRET_SYSTEM_PROMPT_VALUE",
            "user said something private",
            "sk-1234567890abcdef",
            "Bearer sk-secret-token",
            "Traceback (most recent call last)",
            "connection to db failed",
            "postgres://user:pass@host",
            "full model output",
            "sk-leaked-key",
            "You are Mio...",
        ]
        for value in sensitive_values:
            assert value not in body, (
                f"Sensitive value '{value}' found in API response"
            )

        # Also verify only whitelist keys remain in the sanitized output
        node_summary = response.json()["node_summary"]
        allowed_keys = {"status", "duration_ms", "error_code"}
        for node_data in node_summary.values():
            if isinstance(node_data, dict):
                for key in node_data:
                    assert key in allowed_keys


# ── Test 15: List also doesn't leak sensitive info ─────────────────


class TestTraceListSensitiveDataFiltering:
    """Verify list endpoint also filters sensitive data."""

    async def test_list_endpoint_filters_sensitive_data(
        self, app, client: AsyncClient
    ) -> None:
        service = app.state.conversation_service
        cid = await _create_conversation(client)

        sensitive_summary = {
            "stream_llm": {
                "status": "completed",
                "duration_ms": 100,
                "error_code": None,
                "api_key": "sk-list-leak-test",
                "prompt": "SECRET_LIST_PROMPT",
                "authorization": "Bearer list-secret",
            },
        }

        async with service._session_factory() as session:
            trace = AgentTrace(
                conversation_id=UUID(cid),
                request_id=uuid4(),
                status="completed",
                provider="mock",
                model="mock-mio",
                duration_ms=100,
                node_summary=sensitive_summary,
                trace_schema_version=2,
            )
            session.add(trace)
            await session.commit()

        response = await client.get("/api/v1/traces")
        body = response.text

        assert "sk-list-leak-test" not in body
        assert "SECRET_LIST_PROMPT" not in body
        assert "Bearer list-secret" not in body

        # Verify whitelist in list items
        items = response.json()["items"]
        allowed_keys = {"status", "duration_ms", "error_code"}
        for item in items:
            for node_data in item["node_summary"].values():
                if isinstance(node_data, dict):
                    for key in node_data:
                        assert key in allowed_keys


# ── Test 16: Existing tests regression ─────────────────────────────
# This is validated by running the full test suite; no separate test needed here.
# The full pytest run will confirm no regression in chat, SSE, cancel,
# and concurrency tests.


# ── Helpers for security tests ─────────────────────────────────────


async def _insert_trace_with_summary(
    client: AsyncClient,
    conversation_id: str,
    node_summary: dict[str, object],
) -> str:
    """Insert a trace with a custom node_summary and return its ID."""
    from mio.services.conversations import ConversationService

    service: ConversationService = client._transport.app.state.conversation_service  # type: ignore[attr-defined]
    trace_id = uuid4()
    async with service._session_factory() as session:
        trace = AgentTrace(
            id=trace_id,
            conversation_id=UUID(conversation_id),
            request_id=uuid4(),
            status="completed",
            provider="mock",
            model="mock-mio",
            duration_ms=100,
            node_summary=node_summary,
            trace_schema_version=2,
        )
        session.add(trace)
        await session.commit()
    return str(trace_id)


# ── Test 17: Historical known status strings normalized ────────────


class TestSanitizeKnownStatusStrings:
    """Known status strings are converted to {"status": ...} objects."""

    async def test_known_status_strings_normalized(
        self, app, client: AsyncClient
    ) -> None:
        cid = await _create_conversation(client)
        summary = {
            "load_context": "completed",
            "stream_llm": "failed",
            "build_persona_prompt": "skipped",
        }
        trace_id = await _insert_trace_with_summary(client, cid, summary)

        response = await client.get(f"/api/v1/traces/{trace_id}")
        assert response.status_code == 200
        ns = response.json()["node_summary"]

        assert ns["load_context"] == {"status": "completed"}
        assert ns["stream_llm"] == {"status": "failed"}
        assert ns["build_persona_prompt"] == {"status": "skipped"}


# ── Test 18: Unknown strings not leaked ────────────────────────────


class TestSanitizeUnknownStrings:
    """Unknown string values must become empty objects, not leak."""

    async def test_unknown_string_value_sanitized(
        self, app, client: AsyncClient
    ) -> None:
        cid = await _create_conversation(client)
        summary = {"legacy": "SECRET_CHAT_CONTENT"}
        trace_id = await _insert_trace_with_summary(client, cid, summary)

        response = await client.get(f"/api/v1/traces/{trace_id}")
        assert response.status_code == 200
        ns = response.json()["node_summary"]
        assert ns["legacy"] == {}
        assert "SECRET_CHAT_CONTENT" not in response.text


# ── Test 19: List values not leaked ────────────────────────────────


class TestSanitizeListValues:
    """List/tuple values must become empty objects."""

    async def test_list_value_sanitized(self, app, client: AsyncClient) -> None:
        cid = await _create_conversation(client)
        summary: dict[str, object] = {
            "raw": ["sk-secret-key", {"prompt": "SECRET_SYSTEM_PROMPT"}],
        }
        trace_id = await _insert_trace_with_summary(client, cid, summary)

        response = await client.get(f"/api/v1/traces/{trace_id}")
        assert response.status_code == 200
        ns = response.json()["node_summary"]
        assert ns["raw"] == {}
        assert "sk-secret-key" not in response.text
        assert "SECRET_SYSTEM_PROMPT" not in response.text


# ── Test 20: Malicious values in whitelist keys not leaked ─────────


class TestSanitizeMaliciousWhitelistValues:
    """Non-conforming values in whitelist keys must be dropped."""

    async def test_malicious_whitelist_values_sanitized(
        self, app, client: AsyncClient
    ) -> None:
        cid = await _create_conversation(client)
        summary: dict[str, object] = {
            "node": {
                "status": "SECRET_CHAT_CONTENT",
                "duration_ms": "postgres://user:pass@host",
                "error_code": {"api_key": "sk-secret"},
            },
        }
        trace_id = await _insert_trace_with_summary(client, cid, summary)

        response = await client.get(f"/api/v1/traces/{trace_id}")
        assert response.status_code == 200
        ns = response.json()["node_summary"]
        # status is not a known status string → dropped
        assert "status" not in ns["node"]
        # duration_ms is not a non-negative int → dropped
        assert "duration_ms" not in ns["node"]
        # error_code is not None or str → dropped
        assert "error_code" not in ns["node"]
        # node value is empty
        assert ns["node"] == {}
        # Sensitive values must not leak
        assert "SECRET_CHAT_CONTENT" not in response.text
        assert "postgres://user:pass@host" not in response.text
        assert "sk-secret" not in response.text


# ── Test 21: Legitimate fields return correctly ────────────────────


class TestSanitizeLegitimateFields:
    """Valid dict entries return only whitelist fields."""

    async def test_legitimate_dict_sanitized_correctly(
        self, app, client: AsyncClient
    ) -> None:
        cid = await _create_conversation(client)
        summary: dict[str, object] = {
            "classify_message": {
                "status": "completed",
                "duration_ms": 12,
                "error_code": None,
                "prompt": "SECRET_PROMPT",
            },
        }
        trace_id = await _insert_trace_with_summary(client, cid, summary)

        response = await client.get(f"/api/v1/traces/{trace_id}")
        assert response.status_code == 200
        ns = response.json()["node_summary"]
        assert ns["classify_message"] == {
            "status": "completed",
            "duration_ms": 12,
            "error_code": None,
        }
        assert "SECRET_PROMPT" not in response.text


# ── Test 22: Bool duration_ms not returned ─────────────────────────


class TestSanitizeBoolDuration:
    """duration_ms=True must not be returned as a valid value."""

    async def test_bool_duration_ms_sanitized(
        self, app, client: AsyncClient
    ) -> None:
        cid = await _create_conversation(client)
        summary: dict[str, object] = {"node": {"duration_ms": True}}
        trace_id = await _insert_trace_with_summary(client, cid, summary)

        response = await client.get(f"/api/v1/traces/{trace_id}")
        assert response.status_code == 200
        ns = response.json()["node_summary"]
        assert ns["node"] == {}


# ── Test 23: Illegal node names not leaked ─────────────────────────


class TestSanitizeIllegalNodeNames:
    """Node names that don't match identifier pattern are dropped."""

    async def test_illegal_node_name_sanitized(
        self, app, client: AsyncClient
    ) -> None:
        cid = await _create_conversation(client)
        summary: dict[str, object] = {
            "SECRET_API_KEY_sk-xxxx": {"status": "completed"},
            "valid_node": {"status": "completed"},
            "a" * 100: {"status": "completed"},  # too long
        }
        trace_id = await _insert_trace_with_summary(client, cid, summary)

        response = await client.get(f"/api/v1/traces/{trace_id}")
        assert response.status_code == 200
        ns = response.json()["node_summary"]
        # Illegal names must not appear
        assert "SECRET_API_KEY_sk-xxxx" not in ns
        assert "a" * 100 not in ns
        # Valid name must remain
        assert "valid_node" in ns
        # Sensitive node name must not leak
        assert "SECRET_API_KEY_sk-xxxx" not in response.text


# ── Test 24: Schema contract — trace_schema_version not nullable ───


class TestTraceSchemaContract:
    """Verify trace_schema_version is always int, never null."""

    async def test_trace_schema_version_is_int(
        self, app, client: AsyncClient
    ) -> None:
        cid = await _create_conversation(client)
        await _send_message(client, cid, "你好")

        listing = await client.get("/api/v1/traces")
        item = listing.json()["items"][0]
        assert isinstance(item["trace_schema_version"], int)
        assert item["trace_schema_version"] >= 1

    async def test_historical_null_maps_to_1(
        self, app, client: AsyncClient
    ) -> None:
        service = app.state.conversation_service
        cid = await _create_conversation(client)

        trace_id = uuid4()
        async with service._session_factory() as session:
            trace = AgentTrace(
                id=trace_id,
                conversation_id=UUID(cid),
                request_id=uuid4(),
                status="completed",
                provider="mock",
                model="mock-mio",
                duration_ms=100,
                node_summary={},
                # trace_schema_version is NULL in DB
            )
            session.add(trace)
            await session.commit()

        response = await client.get(f"/api/v1/traces/{trace_id}")
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body["trace_schema_version"], int)
        assert body["trace_schema_version"] == 1
