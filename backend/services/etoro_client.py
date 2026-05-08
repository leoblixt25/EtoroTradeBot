import structlog
import uuid
from datetime import datetime
from typing import Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from backend.config.settings import settings

logger = structlog.get_logger(__name__)

ETORO_BASE_URL = "https://public-api.etoro.com/api/v1"


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

    def _resolve_path(self, path: str) -> str:
        """Resolve API path, inserting /demo for trading endpoints in demo mode."""
        if settings.ETORO_DEMO_MODE and path.startswith("/trading/"):
            parts = path.split("/")
            parts.insert(3, "demo")
            return "/".join(parts)
        return path

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    )
    async def _get(self, path: str) -> dict[str, Any] | list[Any]:
        if not self.is_enabled:
            raise EtoroAPIError("eToro API not configured — set ETORO_PUBLIC_API_KEY and ETORO_USER_KEY")
        url = f"{ETORO_BASE_URL}{self._resolve_path(path)}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._headers())
            if resp.status_code == 429:
                logger.warning("etoro rate limited", path=path)
                raise EtoroAPIError("Rate limited")
            if resp.status_code == 401:
                raise EtoroAPIError("Unauthorized — check API keys")
            if resp.status_code == 404:
                return {}
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise EtoroAPIError(f"HTTP {resp.status_code}: {resp.text[:200]}") from e
            try:
                body = resp.json()
                if "portfolio" in path:
                    logger.info("etoro portfolio response", body=str(body)[:500])
                return body
            except ValueError as e:
                raise EtoroAPIError(f"Invalid JSON response: {resp.text[:200]}") from e

    async def get_portfolio(self) -> dict[str, Any]:
        """Get comprehensive portfolio info including positions and account status."""
        return await self._get("/trading/info/portfolio")

    async def get_positions(self) -> list[dict[str, Any]]:
        """Extract positions from portfolio data, including mirror (copy-trade) positions."""
        data = await self._get("/trading/info/portfolio")
        if isinstance(data, dict):
            client_portfolio = data.get("clientPortfolio", {})
            positions = list(client_portfolio.get("positions", []) or [])
            mirrors = client_portfolio.get("mirrors", []) or []
            for mirror in mirrors:
                mirror_positions = mirror.get("positions", []) or []
                for mp in mirror_positions:
                    mp["_mirrorId"] = mirror.get("mirrorId")
                    mp["_parentUsername"] = mirror.get("parentUsername", "")
                positions.extend(mirror_positions)
            return positions
        return []

    async def get_mirrors(self) -> list[dict[str, Any]]:
        """Extract mirror copy-trading relationships from portfolio data."""
        data = await self._get("/trading/info/portfolio")
        if isinstance(data, dict):
            return data.get("clientPortfolio", {}).get("mirrors", []) or []
        return []

    async def get_account(self) -> dict[str, Any]:
        """Get account summary from portfolio endpoint.

        eToro API returns:
          - clientPortfolio.credit (cash balance)
          - clientPortfolio.unrealizedPnL (total unrealized P&L)
          - clientPortfolio.positions[].amount (current market value per position)
          - clientPortfolio.mirrors[].availableAmount (current value per mirror)
        """
        data = await self._get("/trading/info/portfolio")
        if isinstance(data, dict):
            cp = data.get("clientPortfolio", {})
            positions = cp.get("positions", []) or []
            mirrors = cp.get("mirrors", []) or []

            credit = float(cp.get("credit", 0))
            unrealized_pnl = float(cp.get("unrealizedPnL", 0))
            invested_amount = sum(float(p.get("amount", 0)) for p in positions)
            invested_amount += sum(float(m.get("availableAmount", 0)) for m in mirrors)
            total_value = credit + invested_amount + unrealized_pnl

            return {
                "totalValue": round(total_value, 2),
                "cashBalance": round(credit, 2),
                "investedAmount": round(invested_amount, 2),
                "unrealizedPnl": round(unrealized_pnl, 2),
                "dailyPnl": round(unrealized_pnl, 2),
                "weeklyPnl": round(unrealized_pnl, 2),
                "monthlyPnl": round(unrealized_pnl, 2),
            }
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
