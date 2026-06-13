"""Trace query service — owner-isolated, sanitized trace reads."""

import base64
import re
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from mio.api.errors import AppError
from mio.db.models import AgentTrace, Conversation

# Whitelist: only these keys are allowed in node_summary dict values.
_NODE_SUMMARY_ALLOWED_KEYS = {"status", "duration_ms", "error_code"}

# Known status strings from graph node execution.
_NODE_SUMMARY_ALLOWED_STATUSES = {
    "pending",
    "streaming",
    "completed",
    "failed",
    "cancelled",
    "fallback",
    "skipped",
}

# Node names must look like valid identifiers starting with a lowercase letter
# (max 64 chars).  Rejects names starting with uppercase or containing
# characters that don't belong in typical Python/JS node identifiers.
_NODE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def sanitize_node_summary(
    node_summary: dict[str, object] | None,
) -> dict[str, dict[str, object]]:
    """Strip all keys except the whitelist from each node entry.

    Rules:
    - **dict values**: only ``status`` (must be a known status string),
      ``duration_ms`` (must be a non-negative int, not bool), and
      ``error_code`` (None or str ≤ 100 chars) are kept.
    - **known status strings**: converted to ``{"status": <value>}``.
    - **everything else** (unknown strings, lists, numbers, bools, nested
      objects): replaced with ``{}``.
    - Node names must match ``^[a-z][a-z0-9_]{0,63}$``; illegal names
      are silently dropped.
    """
    if not node_summary:
        return {}

    sanitized: dict[str, dict[str, object]] = {}

    for node_name, node_data in node_summary.items():
        # Filter illegal node names.
        if not _NODE_NAME_RE.match(node_name):
            continue

        if isinstance(node_data, dict):
            clean: dict[str, object] = {}

            status = node_data.get("status")
            if (
                isinstance(status, str)
                and status in _NODE_SUMMARY_ALLOWED_STATUSES
            ):
                clean["status"] = status

            duration_ms = node_data.get("duration_ms")
            if (
                isinstance(duration_ms, int)
                and not isinstance(duration_ms, bool)
                and duration_ms >= 0
            ):
                clean["duration_ms"] = duration_ms

            # Only include error_code when the key is present in input.
            if "error_code" in node_data:
                error_code = node_data["error_code"]
                if error_code is None:
                    clean["error_code"] = None
                elif isinstance(error_code, str):
                    # Limit length to prevent stuffing chat content.
                    clean["error_code"] = error_code[:100]

            sanitized[node_name] = clean

        elif isinstance(node_data, str) and node_data in _NODE_SUMMARY_ALLOWED_STATUSES:
            sanitized[node_name] = {"status": node_data}

        else:
            # Unknown strings, lists, tuples, numbers, bools, nested objects.
            sanitized[node_name] = {}

    return sanitized


class TraceService:
    """Query-only service for AgentTrace with owner isolation."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        demo_user_id: UUID,
    ) -> None:
        self._session_factory = session_factory
        self._demo_user_id = demo_user_id

    # ── Cursor helpers ──────────────────────────────────────────────

    @staticmethod
    def _encode_cursor(created_at: datetime, trace_id: UUID) -> str:
        raw = f"{created_at.isoformat()}|{trace_id}"
        return base64.urlsafe_b64encode(raw.encode()).decode()

    @staticmethod
    def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
        try:
            raw = base64.urlsafe_b64decode(cursor.encode()).decode()
            created_at_str, trace_id_str = raw.split("|", maxsplit=1)
            return datetime.fromisoformat(created_at_str), UUID(trace_id_str)
        except (ValueError, UnicodeDecodeError) as exc:
            raise AppError(400, "invalid_cursor", "分页游标无效。") from exc

    # ── Owner isolation predicate ───────────────────────────────────

    def _owner_filter(self) -> ColumnElement[bool]:
        """Return a SQLAlchemy WHERE clause that restricts traces
        to the demo user via the Conversation join."""
        return Conversation.user_id == self._demo_user_id

    # ── List traces ─────────────────────────────────────────────────

    async def list_traces(
        self,
        *,
        conversation_id: UUID | None = None,
        status: str | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> tuple[list[AgentTrace], str | None]:
        async with self._session_factory() as session:
            query = (
                select(AgentTrace)
                .join(Conversation, AgentTrace.conversation_id == Conversation.id)
                .where(self._owner_filter())
            )

            if conversation_id is not None:
                query = query.where(AgentTrace.conversation_id == conversation_id)
            if status is not None:
                query = query.where(AgentTrace.status == status)

            if cursor:
                created_at, trace_id = self._decode_cursor(cursor)
                query = query.where(
                    or_(
                        AgentTrace.created_at < created_at,
                        and_(
                            AgentTrace.created_at == created_at,
                            AgentTrace.id < trace_id,
                        ),
                    )
                )

            query = query.order_by(
                AgentTrace.created_at.desc(), AgentTrace.id.desc()
            ).limit(limit + 1)

            result = await session.scalars(query)
            traces = list(result)

            has_more = len(traces) > limit
            page = traces[:limit]
            next_cursor = (
                self._encode_cursor(page[-1].created_at, page[-1].id)
                if has_more and page
                else None
            )
            return page, next_cursor

    # ── Single trace detail ─────────────────────────────────────────

    async def get_trace(self, trace_id: UUID) -> AgentTrace:
        async with self._session_factory() as session:
            trace = await session.scalar(
                select(AgentTrace)
                .join(Conversation, AgentTrace.conversation_id == Conversation.id)
                .where(AgentTrace.id == trace_id, self._owner_filter())
            )
            if trace is None:
                raise AppError(404, "trace_not_found", "Trace 不存在。")
            return trace
