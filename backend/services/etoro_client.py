import structlog
import uuid
from datetime import datetime
from typing import Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from backend.config.settings import settings

logger = structlog.get_logger(__name__)

ETORO_BASE_URL = "https://public-api.etoro.com/api/v1"
ETORO_DEMO_PREFIX = "/demo"


class EtoroAPIError(Exception):
    pass


class EtoroClient:
    def __init__(self):
        pass

    @property
    def is_enabled(self) -> bool:
        api_key = settings.ETORO_PUBLIC_API_KEY or settings.ETORO_API_KEY
        user_key = settings.ETORO_USER_KEY or settings.ETORO_USERNAME
        return bool(api_key and user_key)

    def _get_api_key(self) -> str:
        return settings.ETORO_PUBLIC_API_KEY or settings.ETORO_API_KEY or ""

    def _get_user_key(self) -> str:
        return settings.ETORO_USER_KEY or settings.ETORO_USERNAME or ""

    def _headers(self) -> dict[str, str]:
        return {
            "x-request-id": str(uuid.uuid4()),
            "x-api-key": self._get_api_key(),
            "x-user-key": self._get_user_key(),
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    )
    async def _get(self, path: str) -> dict[str, Any] | list[Any]:
        if not self.is_enabled:
            raise EtoroAPIError("eToro API not configured — set ETORO_PUBLIC_API_KEY and ETORO_USER_KEY")
        prefix = ETORO_DEMO_PREFIX if settings.ETORO_DEMO_MODE else ""
        url = f"{ETORO_BASE_URL}{prefix}{path}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._headers())
            if resp.status_code == 429:
                logger.warning("etoro rate limited", path=path)
                raise EtoroAPIError("Rate limited")
            if resp.status_code == 401:
                raise EtoroAPIError("Unauthorized — check API keys")
            if resp.status_code == 404:
                return {}
            resp.raise_for_status()
            return resp.json()

    async def get_portfolio(self) -> dict[str, Any]:
        """Get comprehensive portfolio info including positions and account status."""
        return await self._get("/trading/info/portfolio")

    async def get_positions(self) -> list[dict[str, Any]]:
        """Extract positions from portfolio data."""
        data = await self._get("/trading/info/portfolio")
        if isinstance(data, dict):
            client_portfolio = data.get("clientPortfolio", {})
            positions = client_portfolio.get("positions", [])
            return positions if isinstance(positions, list) else []
        return []

    async def get_account(self) -> dict[str, Any]:
        """Get account summary from portfolio endpoint."""
        data = await self._get("/trading/info/portfolio")
        if isinstance(data, dict):
            client_portfolio = data.get("clientPortfolio", {})
            account = {
                "totalValue": client_portfolio.get("currentValue", 0),
                "cashBalance": client_portfolio.get("cashBalance", 0),
                "investedAmount": client_portfolio.get("investedAmount", 0),
                "realizedPnl": client_portfolio.get("realizedPnl", 0),
                "dailyPnl": client_portfolio.get("dailyPnl", 0),
                "weeklyPnl": client_portfolio.get("weeklyPnl", 0),
                "monthlyPnl": client_portfolio.get("monthlyPnl", 0),
                "maxDrawdown": client_portfolio.get("maxDrawdown", 0),
                "volatility": client_portfolio.get("volatility", 0),
                "leverage": client_portfolio.get("leverage", 1),
            }
            return account
        return {}

    async def get_watchlists(self) -> list[dict[str, Any]]:
        data = await self._get("/watchlists")
        return data if isinstance(data, list) else data.get("data", [])

    async def get_trader(self, trader_username: str) -> dict[str, Any]:
        return await self._get(f"/user-info/people/{trader_username}/tradeinfo")

    async def get_trader_activities(self, trader_username: str) -> list[dict[str, Any]]:
        data = await self._get(f"/user-info/people/{trader_username}/tradeinfo")
        if isinstance(data, dict):
            return data.get("trades", [])
        return data if isinstance(data, list) else []

    async def health_check(self) -> bool:
        try:
            await self._get("/me")
            return True
        except EtoroAPIError:
            raise
        except Exception:
            return False
