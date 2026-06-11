# Mio AI Companion Backend

第一波后端实现提供固定 Demo 用户、默认「澪」人设、Conversation、Message、基础 Agent Trace、Mock/OpenAI-compatible LLM Provider 和 SSE 流式聊天。

详细说明：

- [聊天后端开发文档](../docs/development/chat-backend.md)
- [Python AI 聊天后端学习文档](../docs/learning/01-python-fastapi-chat-backend.md)

常用命令：

```bash
cd backend
uv sync
uv run pytest
uv run ruff check .
uv run mypy src
```

使用 PostgreSQL：

```bash
docker compose up -d postgres
cd backend
uv run alembic upgrade head
uv run uvicorn mio.main:app --reload
```

接口文档启动后位于 <http://127.0.0.1:8000/docs>。

