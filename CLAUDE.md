# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mio AI Companion is a PersonaRAG AI companion agent — a girlfriend-type companion for developers, built as a portfolio/demo project. The default persona is "澪" (Mio): cool, reserved, caring, speaks in short sentences, never oily or performative.

**Core principle**: Companion identity first. Knowledge answers must maintain persona; never sound like customer service. When the user is down, respond emotionally before solving technical problems.

## Commands

### Backend (Python 3.12, FastAPI, LangGraph)

```bash
cd backend
uv sync                                    # install dependencies
uv run pytest                              # run all tests
uv run pytest tests/test_config.py         # run single test file
uv run pytest -k "test_name"               # run test by name
uv run ruff check .                        # lint
uv run ruff format .                       # format
uv run mypy src                            # type check
uv run uvicorn mio.main:app --reload       # start dev server (needs PostgreSQL)
```

### Frontend (React 19, Vite, TypeScript)

```bash
cd frontend
npm install
npm run dev          # vite dev server
npm run build        # tsc + vite build
npm run lint         # eslint
npm run test         # vitest run
npm run test:watch   # vitest watch mode
```

### Database

```bash
docker compose up -d postgres              # start PostgreSQL 16
cd backend
uv run alembic upgrade head                # run migrations
```

API docs at http://127.0.0.1:8000/docs when server is running.

## Architecture

### Backend (`backend/src/mio/`)

The agent pipeline is a **LangGraph StateGraph** with conditional routing:

```
START → load_context → classify_message
    → [safety route] → build_safety_response → stream_safety_response → finalize → END
    → [persona route] → build_persona_prompt → stream_llm → finalize → END
```

Routing decision: high risk, crisis emotion, or unsafe intent → safety route; otherwise → persona route.

Key modules:

- **`agent/graph.py`** — LangGraph workflow definition, `AgentState` TypedDict, `stream_agent_events()` for SSE
- **`agent/prompt.py`** — Persona prompt builder (system prompt assembly)
- **`agent/safety.py`** — Safety response templates for crisis/unsafe messages
- **`classification/`** — Message classifier with `MessageClassifier` ABC, mock and OpenAI-compatible implementations, factory pattern via `create_message_classifier()`
- **`llm/`** — `ChatModelProvider` ABC with `stream()` and `cancel()`, mock and OpenAI-compatible implementations, factory via `create_chat_model_provider()`
- **`api/routes.py`** — FastAPI routes; `api_router` for business endpoints, `health_router` for health checks
- **`api/errors.py`** — Unified error handling installed via `install_error_handlers()`
- **`api/schemas.py`** — Pydantic request/response models
- **`api/dependencies.py`** — FastAPI dependency injection helpers
- **`services/conversations.py`** — `ConversationService` orchestrates DB, agent graph, provider, classifier
- **`services/recovery.py`** — Recovers incomplete generations on startup
- **`chat/registry.py`** — `ActiveRequestRegistry` tracks in-flight requests for cancellation
- **`db/models.py`** — SQLAlchemy async models
- **`db/session.py`** — Engine and session factory creation
- **`db/seed.py`** — Demo data seeding (demo user, default persona)
- **`config.py`** — `Settings` via pydantic-settings, env prefix `MIO_`, reads from `backend/.env`

**Provider pattern**: Both LLM and Classifier use ABC → factory → mock/openai_compatible. Config selects via `MIO_LLM_PROVIDER` and `MIO_CLASSIFIER_PROVIDER` (both default to `mock`). Mock providers work without API keys for testing.

### Frontend (`frontend/src/`)

Two top-level features:

- **`features/chat/`** — Chat page with sidebar, message list, composer. Uses `useChatSession` hook, SSE streaming via `api/sse.ts`
- **`features/voice-call/`** — Immersive fullscreen voice call overlay. `VoiceCallPage` renders on top of chat; `inert` attribute disables chat when active

`App.tsx` toggles between chat (always mounted) and voice call (conditional overlay). Voice call shares the same conversation — no separate state.

### Testing

- Backend: `pytest` with `asyncio_mode = "auto"`, test files in `backend/tests/`. Conftest provides fixtures for app, client, and DB session
- Frontend: `vitest` with `@testing-library/react`, setup in `frontend/src/test/setup.ts`
- Mock providers enable full test runs without API keys or database

## Coding Conventions

- Python: `ruff` for linting/formatting (line-length 100, target py312), `mypy --strict` with pydantic plugin
- TypeScript: ESLint with react-hooks and react-refresh plugins
- All AI decisions must have trace fields — `node_summary` in agent state tracks each node's status, duration, and error code
- Structured schema validation for LLM output (no fragile string parsing)
- Prompt, Provider, Retriever, Tool, and Channel must stay decoupled — never mix channel logic into Conversation Service or scatter persona text in business code
- Never log API keys or full sensitive chat content

## Environment Variables

All prefixed with `MIO_`:

| Variable | Default | Description |
|---|---|---|
| `MIO_ENVIRONMENT` | `development` | `development` / `test` / `production` |
| `MIO_DATABASE_URL` | `postgresql+asyncpg://mio:mio@localhost:5432/mio` | Async PostgreSQL URL |
| `MIO_LLM_PROVIDER` | `mock` | `mock` or `openai_compatible` |
| `MIO_LLM_BASE_URL` | — | OpenAI-compatible LLM endpoint |
| `MIO_LLM_API_KEY` | — | LLM API key |
| `MIO_LLM_MODEL` | `mock-mio` | Model identifier |
| `MIO_CLASSIFIER_PROVIDER` | `mock` | `mock` or `openai_compatible` |
| `MIO_CLASSIFIER_MODEL` | `mock-classifier` | Classifier model identifier |
| `MIO_MOCK_CHUNK_DELAY_MS` | `0` | Delay between mock stream chunks |
| `MIO_CONTEXT_MESSAGE_LIMIT` | `20` | Max history messages sent to LLM |
| `MIO_CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins |

## Docs Workflow

Every backend feature must produce three artifacts: working code with tests, a dev doc at `docs/development/<module>.md`, and a learning doc at `docs/learning/<seq>-<topic>.md` (Chinese, aimed at Java/Spring Boot developers learning Python AI). Docs must reflect actual implementation, not planned features. See `AGENTS.md` for the full checklist.
