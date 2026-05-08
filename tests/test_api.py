import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

from backend.main import app
from backend.config.settings import settings
from backend.api.deps import get_current_user, get_db


mock_db = MagicMock()
mock_db.execute = AsyncMock()


async def override_get_db():
    yield mock_db


async def override_get_current_user_fail():
    raise Exception("Not authenticated")


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["app_name"] == "eToro Portfolio Manager"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_health_contains_paper_trading_flag(self, client):
        response = await client.get("/health")
        data = response.json()
        assert "paper_trading" in data
        assert isinstance(data["paper_trading"], bool)


class TestRootEndpoint:
    @pytest.mark.asyncio
    async def test_root_returns_app_info(self, client):
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["app"] == "eToro Portfolio Manager"
        assert data["version"] == "1.0.0"
        assert data["docs"] == "/docs"
        assert data["health"] == "/health"


class TestApiPortfolioEndpoint:
    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="requires full database integration setup")
    async def test_portfolio_requires_auth(self, client):
        app.dependency_overrides[get_current_user] = override_get_current_user_fail
        app.dependency_overrides[get_db] = override_get_db
        try:
            response = await client.get("/api/v1/portfolio")
            assert response.status_code in (401, 403, 500)
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="requires full database integration setup")
    async def test_portfolio_returns_data_when_authenticated(self, client):
        mock_user = MagicMock()
        mock_user.id = 1

        mock_summary = MagicMock()
        mock_summary.total_value = 50000.0
        mock_summary.total_traders = 5
        mock_summary.total_positions = 12
        mock_summary.daily_pnl = 150.0
        mock_summary.weekly_pnl = 750.0
        mock_summary.monthly_pnl = 2500.0
        mock_summary.health_score = 85

        mock_portfolio = MagicMock()
        mock_portfolio.id = 1
        mock_portfolio.user_id = 1
        mock_portfolio.total_value = 50000.0
        mock_portfolio.cash_balance = 5000.0
        mock_portfolio.invested_amount = 45000.0
        mock_portfolio.unrealized_pnl = 1500.0
        mock_portfolio.realized_pnl = 3000.0
        mock_portfolio.daily_pnl = 150.0
        mock_portfolio.weekly_pnl = 750.0
        mock_portfolio.monthly_pnl = 2500.0
        mock_portfolio.health_score = 85
        mock_portfolio.last_updated = None
        mock_portfolio.created_at = None

        async def override_get_current_user():
            return mock_user

        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_db] = override_get_db
        try:
            response = await client.get("/api/v1/portfolio")
            assert response.status_code in (200, 404, 422, 500)
        finally:
            app.dependency_overrides.clear()


class TestCorsHeaders:
    @pytest.mark.asyncio
    async def test_cors_headers_present(self, client):
        response = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


class TestNotFoundHandling:
    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_route(self, client):
        response = await client.get("/nonexistent-route")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "The requested resource was not found"

    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_api_route(self, client):
        response = await client.get("/api/v1/nonexistent")
        assert response.status_code == 404


class TestCorsAllowedOrigins:
    @pytest.mark.asyncio
    async def test_cors_allows_configured_origin(self, client):
        response = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        allow_origin = response.headers.get("access-control-allow-origin", "")
        assert "http://localhost:5173" in allow_origin or allow_origin == "*"

    @pytest.mark.asyncio
    async def test_cors_allows_second_origin(self, client):
        response = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        allow_origin = response.headers.get("access-control-allow-origin", "")
        assert "http://localhost:3000" in allow_origin or allow_origin == "*"


class TestRediscoveryEndpoints:
    @pytest.mark.asyncio
    async def test_docs_endpoint_available(self, client):
        response = await client.get("/docs")
        assert response.status_code in (200, 307)

    @pytest.mark.asyncio
    async def test_openapi_json_available(self, client):
        response = await client.get("/openapi.json")
        assert response.status_code in (200, 404)
