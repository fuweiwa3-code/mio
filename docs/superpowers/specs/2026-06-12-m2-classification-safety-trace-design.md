# M2 Classification, Safety Routing & Agent Trace Enhancement Design

**Date:** 2026-06-12
**Status:** Approved for implementation
**Baseline:** M1 chat backend (21 tests passing, Ruff/Mypy clean)

## 1. Goal

Add structured message classification (emotion/intent/risk), conditional LangGraph safety routing, enhanced AgentTrace with classification data, Trace query API, and Alembic migration — all without breaking existing SSE, cancellation, disconnect recovery, or concurrency constraints.

## 2. Scope

**In scope:**
- Classification module (`mio.classification`) with abstract base, mock, and OpenAI-compatible providers
- Pydantic classification schemas with strict validation and cross-field constraints
- LangGraph conditional routing: classify → safety branch or persona branch
- Deterministic safety response templates for high-risk messages
- Enhanced AgentTrace with classification fields, real node execution tracking, and sensitive data filtering
- Alembic migration for new nullable classification columns + `trace_schema_version`
- Trace query API (single + list with cursor pagination)
- Comprehensive tests (27 categories per spec)
- Updated development docs and learning docs
- Database migration runbook for cloud PostgreSQL

**Out of scope (M2 does NOT implement):**
- Memory, RAG, Tool, Skill, MCP, Reminder
- Statistics dashboard
- User registration/login

## 3. Architecture

### 3.1 Classification Module

New package: `backend/src/mio/classification/`

```
classification/
├── __init__.py          # re-exports
├── models.py            # EmotionLabel, IntentLabel, RiskLevel, ClassificationResult
├── base.py              # MessageClassifier ABC
├── mock.py              # MockMessageClassifier (deterministic, keyword-based)
├── openai_compatible.py # OpenAICompatibleMessageClassifier
└── factory.py           # create_message_classifier(settings)
```

**ClassificationResult** (Pydantic, `extra="forbid"`):
```json
{
  "emotion": {"label": "tired", "confidence": 0.94},
  "intent": {"label": "mixed", "confidence": 0.82},
  "risk": {"level": "none", "confidence": 0.97}
}
```

Cross-field validators:
- `emotion=crisis` → `risk.level` must be `high`
- `intent=unsafe` → `risk.level` must be `high`
- Confidence range: `0.0 ≤ x ≤ 1.0`

**Fallback** (on classification failure):
```
emotion=calm, intent=companion, risk=medium, all confidence=0, classification_status=fallback
```

**Mock priority rules:**
```
Emotion: crisis > angry > anxious > sad/lonely > tired > happy > embarrassed > calm
Intent: unsafe > reminder > mixed > knowledge_qa > companion
```

**OpenAI-compatible:** `stream=false`, `temperature=0`, Pydantic-generated JSON Schema. Invalid output → fallback (no string patching).

### 3.2 LangGraph Conditional Routing

New graph topology:
```text
START
→ load_context
→ classify_message
  → [high/crisis/unsafe] → build_safety_response → stream_safety_response → finalize_response → END
  → [otherwise] → build_persona_prompt → stream_llm → finalize_response → END
```

**AgentState** additions:
- `user_text: str` — current user message for classification
- `classification: ClassificationResult | None`
- `classification_status: str` — "success" | "fallback"
- `route: str` — "persona" | "safety"
- `node_results: dict[str, NodeResult]` — per-node execution tracking

**Routing logic:**
- `risk=high` OR `emotion=crisis` OR `intent=unsafe` → safety branch
- `risk=medium` or fallback → persona branch with cautious safety prompt addition
- `risk=none/low` → normal persona branch

**Safety branch:**
- Uses backend deterministic templates (NOT the persona ChatModelProvider)
- Stops romantic/roleplay behavior
- Confirms user safety
- Encourages contacting trusted people
- Suggests emergency services if immediate danger
- No medical diagnosis
- No hardcoded country-specific phone numbers
- Streams via existing `message.delta` events

**Important:** Safety responses must also use `message.delta` + `message.completed` SSE events. Internal node events must NOT leak as chat SSE events.

### 3.3 AgentTrace Enhancement

New fields on `agent_traces` table (all nullable for backward compat):
- `emotion_label: str | None`
- `emotion_confidence: float | None`
- `intent_label: str | None`
- `intent_confidence: float | None`
- `risk_level: str | None`
- `risk_confidence: float | None`
- `classification_status: str | None` — "success" | "fallback" | null (for v1 traces)
- `classification_provider: str | None`
- `classification_model: str | None`
- `route: str | None` — "persona" | "safety"
- `trace_schema_version: int` — default 2, historical traces treated as 1

**node_summary** changes from static strings to structured objects:
```json
{
  "classify_message": {"status": "completed", "duration_ms": 18, "error_code": null},
  "build_persona_prompt": {"status": "completed", "duration_ms": 1, "error_code": null},
  "build_safety_response": {"status": "skipped", "duration_ms": null, "error_code": null}
}
```

**Sensitive data filtering** — must NOT log:
- Full user/assistant chat content
- Full system prompt
- API keys, Authorization headers, Provider base URLs
- Raw model classification responses
- Exception stacks or raw exception text containing sensitive data

### 3.4 Trace Query API

```http
GET /api/v1/agent-traces/{trace_id}
GET /api/v1/conversations/{conversation_id}/agent-traces?limit=20&cursor=...
```

- Owner isolation: trace must belong to a conversation owned by demo user
- 404 `trace_not_found` if not found or not owned
- Cursor pagination (stable, same pattern as messages)
- Dedicated Pydantic response schemas
- Returns sanitized data only: classification, route, node results, provider name, model name, duration, error codes
- Does NOT return message content or prompts

Historical trace (v1) response:
```json
{
  "trace_schema_version": 1,
  "classification": null
}
```

### 3.5 Alembic Migration

File: `backend/migrations/versions/20260612_0002_m2_classification_trace.py`
Down revision: `20260609_0001`

Adds to `agent_traces`:
- `emotion_label` VARCHAR(32) NULLABLE
- `emotion_confidence` FLOAT NULLABLE
- `intent_label` VARCHAR(32) NULLABLE
- `intent_confidence` FLOAT NULLABLE
- `risk_level` VARCHAR(32) NULLABLE
- `risk_confidence` FLOAT NULLABLE
- `classification_status` VARCHAR(32) NULLABLE
- `classification_provider` VARCHAR(64) NULLABLE
- `classification_model` VARCHAR(128) NULLABLE
- `route` VARCHAR(32) NULLABLE
- `trace_schema_version` INTEGER NOT NULL DEFAULT 2

Historical traces: all classification fields NULL, `trace_schema_version` defaults to 2 on new writes but existing rows keep NULL version (application treats NULL as v1). New traces write version 2.

Both `upgrade()` and `downgrade()` implemented. Migration must NOT be executed against cloud PostgreSQL from this machine.

### 3.6 Configuration

New Settings fields:
```python
classifier_provider: Literal["mock", "openai_compatible"] = "mock"
classifier_model: str = "mock-classifier"
classifier_base_url: str = ""
classifier_api_key: str = ""
```

Can reuse LLM base URL/API key but classifier is a separate object with separate config.

### 3.7 SSE Compatibility

Public event names unchanged:
```
message.started
message.delta
message.completed
message.cancelled
message.failed
```

Requirements:
- Normal chat event order unchanged
- High-risk safety reply produces delta + completed
- Classification fallback does NOT produce `message.failed`
- Provider failure still produces `message.failed code=provider_error`
- Explicit cancel preserves partial text
- SSE disconnect converges to cancelled
- After cancel, next turn works normally
- Same conversation concurrent returns `409 conversation_busy`
- Recovery logic compatible with new Trace fields
- No internal classification/node events exposed via chat SSE

## 4. Implementation Order

1. Classification Pydantic models (schemas with validators)
2. Mock classifier (deterministic, priority rules)
3. OpenAI-compatible classifier
4. Classifier factory + Settings additions
5. LangGraph conditional routing (classify_message node, routing, safety nodes)
6. AgentTrace model changes + real node_summary tracking
7. Alembic migration file
8. Trace query API endpoints
9. All tests (27 categories)
10. Documentation updates

## 5. Testing Strategy

All tests use SQLite, no cloud PostgreSQL connection needed.

Key test categories:
- Classification enums, confidence boundaries, extra="forbid"
- crisis/unsafe → high cross-constraints
- Mock classifier determinism and priority
- OpenAI-compatible payload, valid/invalid responses
- 4 graph paths: normal, medium, high-risk, fallback
- High-risk does NOT call persona ChatModelProvider
- Safety response streaming
- Classification failure → chat completes, trace records fallback
- SSE regression, cancel during classification/generation, disconnect
- Conversation concurrency, provider failure, startup recovery
- Trace API owner isolation, sanitization, cursor pagination
- Historical v1 traces
- OpenAPI new routes
- Migration upgrade/downgrade structure

## 6. Known Limitations

1. Classification uses LLM (or mock) — not a dedicated small model. Production may want a faster/cheaper classifier.
2. Mock classifier is keyword-based, not semantic.
3. Single-process ActiveRequestRegistry — multi-instance needs Redis/DB lock.
4. Safety templates are deterministic — no LLM-generated safety responses in M2.
5. `knowledge_qa`, `mixed`, `reminder` intents are recorded but not acted upon (no RAG/Tool in M2).
