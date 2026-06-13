"""FastAPI application factory and lifecycle management."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from mio.agent.graph import create_agent_graph
from mio.api.errors import install_error_handlers
from mio.api.routes import api_router, health_router
from mio.chat.registry import ActiveRequestRegistry
from mio.classification.factory import create_message_classifier
from mio.config import Settings, get_settings
from mio.db.base import Base
from mio.db.seed import seed_demo_data
from mio.db.session import create_engine_and_session_factory
from mio.llm.factory import create_chat_model_provider
from mio.services.conversations import ConversationService
from mio.services.recovery import recover_incomplete_generations
from mio.services.traces import TraceService


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    engine, session_factory = create_engine_and_session_factory(
        resolved_settings.database_url
    )
    provider = create_chat_model_provider(resolved_settings)
    classifier = create_message_classifier(resolved_settings)
    registry = ActiveRequestRegistry()
    agent_graph = create_agent_graph(provider, classifier)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if resolved_settings.environment == "test":
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
        else:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))

        await recover_incomplete_generations(session_factory)
        demo_ids = await seed_demo_data(session_factory)
        app.state.demo_ids = demo_ids
        app.state.conversation_service = ConversationService(
            session_factory=session_factory,
            demo_ids=demo_ids,
            registry=registry,
            provider=provider,
            classifier=classifier,
            agent_graph=agent_graph,
            model=resolved_settings.llm_model,
            context_message_limit=resolved_settings.context_message_limit,
        )
        app.state.trace_service = TraceService(
            session_factory=session_factory,
            demo_user_id=demo_ids.user_id,
        )
        yield
        await classifier.aclose()
        await provider.aclose()
        await engine.dispose()

    app = FastAPI(
        title="Mio AI Companion API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.registry = registry
    app.state.seed_demo_data = lambda: seed_demo_data(session_factory)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def attach_trace_id(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request.state.trace_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Trace-ID"] = request.state.trace_id
        return response

    install_error_handlers(app)
    app.include_router(health_router)
    app.include_router(api_router)
    return app


app = create_app()
