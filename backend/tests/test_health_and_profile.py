from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


async def test_health_endpoints_report_liveness_and_database_readiness(
    client: AsyncClient,
) -> None:
    live = await client.get("/api/health/live")
    ready = await client.get("/api/health/ready")

    assert live.status_code == 200
    assert live.json() == {"status": "alive"}
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready", "database": "reachable"}


async def test_default_companion_profile_is_seeded_idempotently(
    app,
    client: AsyncClient,
) -> None:
    first = await client.get("/api/v1/companion/profile")
    await app.state.seed_demo_data()
    second = await client.get("/api/v1/companion/profile")

    assert first.status_code == 200
    assert first.json()["name"] == "澪"
    assert "清冷慢热" in first.json()["speaking_style"]
    assert second.json()["id"] == first.json()["id"]


async def test_validation_errors_use_unified_error_shape(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/conversations",
        json={"title": "", "channel": "web"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert response.json()["trace_id"]
    assert response.json()["details"]["errors"]


async def test_unhandled_errors_do_not_leak_internal_details(
    app: FastAPI,
) -> None:
    @app.get("/test/unhandled-error")
    async def unhandled_error() -> None:
        raise RuntimeError("database password must not leak")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/test/unhandled-error")

    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"
    assert response.json()["message"] == "服务暂时不可用，请稍后重试。"
    assert "password" not in response.text
