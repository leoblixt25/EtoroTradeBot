import structlog
import math
from datetime import datetime, timedelta, timezone
from typing import List
from sqlalchemy import select, func as sa_func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import (
    Portfolio,
    Position,
    CopiedTrader,
    RiskMetric,
    AuditLog,
)
from backend.database.schema import (
    PortfolioSummary,
    PortfolioTimelinePoint,
)
from backend.config.settings import settings
from backend.services.etoro_client import EtoroClient, EtoroAPIError

logger = structlog.get_logger(__name__)


class PortfolioService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_portfolio(self, user_id: int) -> Portfolio | None:
        stmt = select(Portfolio).where(Portfolio.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_portfolio(self, user_id: int) -> Portfolio:
        portfolio = await self.get_portfolio(user_id)
        if portfolio is None:
            portfolio = Portfolio(
                user_id=user_id,
                total_value=10000.0,
                cash_balance=10000.0,
                invested_amount=0.0,
            )
            self.db.add(portfolio)
            await self.db.flush()
            logger.info("created default portfolio", user_id=user_id, portfolio_id=portfolio.id)
        return portfolio

    async def get_positions(self, portfolio_id: int) -> List[Position]:
        stmt = select(Position).where(Position.portfolio_id == portfolio_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_portfolio_summary(self, portfolio_id: int) -> PortfolioSummary:
        portfolio = await self.db.get(Portfolio, portfolio_id)
        if portfolio is None:
            return PortfolioSummary(
                total_value=0, cash_balance=0, invested_amount=0,
                unrealized_pnl=0, realized_pnl=0, daily_pnl=0,
                weekly_pnl=0, monthly_pnl=0, health_score=100,
            )

        positions = await self.get_positions(portfolio_id)
        stmt = select(CopiedTrader).where(CopiedTrader.portfolio_id == portfolio_id)
        traders_result = await self.db.execute(stmt)
        traders = list(traders_result.scalars().all())

        total_positions = len(positions)
        total_traders = len(traders)
        active_traders = sum(1 for t in traders if t.status == "active")
        diversification_count = len(set(p.instrument_type for p in positions))
        largest_allocation = 0.0
        if traders:
            largest_allocation = max(t.allocation_percent for t in traders)

        total_value = portfolio.total_value or 0
        day_change = portfolio.daily_pnl or 0
        day_change_percent = (day_change / (total_value - day_change)) * 100 if (total_value - day_change) > 0 else 0.0

        return PortfolioSummary(
            total_value=round(total_value, 2),
            cash_balance=round(portfolio.cash_balance or 0, 2),
            invested_amount=round(portfolio.invested_amount or 0, 2),
            unrealized_pnl=round(portfolio.unrealized_pnl or 0, 2),
            realized_pnl=round(portfolio.realized_pnl or 0, 2),
            daily_pnl=round(portfolio.daily_pnl or 0, 2),
            weekly_pnl=round(portfolio.weekly_pnl or 0, 2),
            monthly_pnl=round(portfolio.monthly_pnl or 0, 2),
            health_score=round(portfolio.health_score or 100, 1),
            total_positions=total_positions,
            total_traders=total_traders,
            active_traders=active_traders,
            diversification_count=diversification_count,
            largest_allocation=round(largest_allocation, 2),
            day_change_percent=round(day_change_percent, 2),
        )

    async def calculate_health_score(self, portfolio_id: int) -> float:
        risk_stmt = (
            select(RiskMetric)
            .where(RiskMetric.portfolio_id == portfolio_id)
            .order_by(desc(RiskMetric.timestamp))
            .limit(1)
        )
        risk_result = await self.db.execute(risk_stmt)
        latest_risk = risk_result.scalar_one_or_none()

        if latest_risk:
            return round(latest_risk.health_score, 1)

        portfolio = await self.db.get(Portfolio, portfolio_id)
        if portfolio is None:
            return 100.0

        score = 100.0

        positions = await self.get_positions(portfolio_id)
        traders_stmt = select(CopiedTrader).where(CopiedTrader.portfolio_id == portfolio_id)
        traders_result = await self.db.execute(traders_stmt)
        traders = list(traders_result.scalars().all())

        if positions and traders:
            total_pnl = sum(p.pnl for p in positions)
            if total_pnl < -portfolio.total_value * 0.1:
                score -= 20
            elif total_pnl < -portfolio.total_value * 0.05:
                score -= 10

            max_alloc = max(t.allocation_percent for t in traders)
            if max_alloc > settings.MAX_ALLOCATION_PER_TRADER:
                score -= 15

            if len(traders) < settings.MIN_DIVERSIFICATION:
                score -= 10

            negative_traders = sum(1 for t in traders if t.total_pnl < 0)
            if negative_traders > len(traders) * 0.5:
                score -= 10

        unrealized_pnl = portfolio.unrealized_pnl or 0
        invested = portfolio.invested_amount or 1
        if invested > 0:
            pnl_ratio = unrealized_pnl / invested
            if pnl_ratio < -0.15:
                score -= 25
            elif pnl_ratio < -0.1:
                score -= 15
            elif pnl_ratio < -0.05:
                score -= 5

        score = max(0, min(100, score))
        portfolio.health_score = score
        return round(score, 1)

    async def get_performance_history(
        self, portfolio_id: int, period: str = "1m"
    ) -> List[PortfolioTimelinePoint]:
        days_map = {"1w": 7, "1m": 30, "3m": 90, "6m": 180, "1y": 365, "all": 730}
        days = days_map.get(period, 30)

        portfolio = await self.db.get(Portfolio, portfolio_id)
        if portfolio is None:
            return []

        positions = await self.get_positions(portfolio_id)
        base_value = float(portfolio.total_value or 10000.0)

        now = datetime.now(timezone.utc)
        points = []
        current_value = 10000.0

        for i in range(days, -1, -1):
            day = now - timedelta(days=i)
            date_key = day.strftime("%Y%m%d")
            seed = hash(f"{portfolio_id}:{date_key}") & 0x7FFFFFFF
            rng = __import__("random").Random(seed)
            daily_change = rng.uniform(-0.025, 0.025)
            current_value += current_value * daily_change
            points.append(
                PortfolioTimelinePoint(
                    date=day.strftime("%Y-%m-%d"),
                    value=round(current_value, 2),
                    pnl=round(current_value - base_value, 2),
                )
            )

        return points

    async def sync_portfolio(self, user_id: int) -> dict:
        start = datetime.now(timezone.utc)
        portfolio = await self.get_or_create_portfolio(user_id)
        etoro = EtoroClient()

        if etoro.is_enabled and not settings.PAPER_TRADING:
            return await self._sync_from_etoro(portfolio, etoro, user_id, start)

        return await self._sync_simulated(portfolio, user_id, start)

    async def _sync_from_etoro(
        self, portfolio: Portfolio, etoro: EtoroClient, user_id: int, start: datetime
    ) -> dict:
        try:
            account = await etoro.get_account()
            etoro_positions = await etoro.get_positions()
            mirrors = await etoro.get_mirrors()
        except EtoroAPIError as e:
            logger.error("etoro sync failed", error=str(e))
            return {"status": "error", "message": str(e), "positions_synced": 0, "traders_synced": 0}

        portfolio.total_value = round(account.get("totalValue", 0), 2)
        portfolio.cash_balance = round(account.get("cashBalance", 0), 2)
        portfolio.invested_amount = round(account.get("investedAmount", 0), 2)
        portfolio.unrealized_pnl = round(account.get("unrealizedPnl", 0), 2)
        portfolio.daily_pnl = round(account.get("dailyPnl", 0), 2)
        portfolio.weekly_pnl = round(account.get("weeklyPnl", 0), 2)
        portfolio.monthly_pnl = round(account.get("monthlyPnl", 0), 2)
        portfolio.last_updated = datetime.now(timezone.utc)

        from sqlalchemy import delete as sa_delete
        await self.db.execute(sa_delete(Position).where(Position.portfolio_id == portfolio.id))
        await self.db.execute(sa_delete(CopiedTrader).where(CopiedTrader.portfolio_id == portfolio.id))

        total_allocated = 0
        for ep in etoro_positions:
            market_value = float(ep.get("amount", 0))
            units = float(ep.get("amountInUnits", 0) or 0)
            entry_price = float(ep.get("openRate", 0))
            is_buy = ep.get("isBuy", True)

            if units > 0 and entry_price > 0:
                current_price = market_value / units
                pnl = market_value - (units * entry_price)
            else:
                current_price = entry_price
                pnl = 0.0

            total_allocated += market_value

            pos = Position(
                portfolio_id=portfolio.id,
                instrument_type="cfd",
                instrument_symbol=str(ep.get("instrumentId", "")),
                instrument_name=f"Instrument {ep.get('instrumentId', '')}",
                amount=units,
                entry_price=entry_price,
                current_price=current_price,
                allocated_amount=round(market_value, 2),
                pnl=round(pnl, 2),
                pnl_percent=round((pnl / (units * entry_price) * 100) if units * entry_price else 0, 2),
                allocation_percent=0,
            )
            self.db.add(pos)

        traders_synced = 0
        for mirror in mirrors:
            parent_username = mirror.get("parentUsername", "") or f"Trader_{mirror.get('cid', 0)}"
            available_amount = float(mirror.get("availableAmount", 0))
            initial_investment = float(mirror.get("initialInvestment", 0))
            mirror_pnl = available_amount - initial_investment
            mirror_roi = (mirror_pnl / initial_investment * 100) if initial_investment else 0

            trader = CopiedTrader(
                portfolio_id=portfolio.id,
                trader_name=parent_username,
                trader_id=str(mirror.get("mirrorId", mirror.get("cid", 0))),
                allocation_percent=round(available_amount / (portfolio.total_value or 1) * 100, 2),
                current_value=round(available_amount, 2),
                total_pnl=round(mirror_pnl, 2),
                total_roi=round(mirror_roi, 2),
                status="active" if not mirror.get("isPaused", False) else "paused",
                classification="balanced",
            )
            self.db.add(trader)
            traders_synced += 1

        portfolio.health_score = await self.calculate_health_score(portfolio.id)
        total_value = portfolio.total_value or 1

        # Update allocation percentages for positions
        positions_db = await self.get_positions(portfolio.id)
        for p in positions_db:
            p.allocation_percent = round((p.allocated_amount / total_value * 100) if total_value else 0, 2)

        max_alloc_pct = max(
            (p.allocated_amount / total_value if total_value else 0)
            for p in positions_db
        ) if positions_db else 0

        risk = RiskMetric(
            portfolio_id=portfolio.id,
            total_exposure=round(total_allocated, 2),
            var_95=round(total_value * 0.05, 2),
            max_drawdown=0.0,
            volatility=0.0,
            concentration_risk=round(max_alloc_pct, 2),
            correlation_risk=0.3,
            leverage_ratio=1.0,
            risk_score=round(100 - portfolio.health_score, 1),
            health_score=portfolio.health_score,
        )
        self.db.add(risk)

        audit = AuditLog(
            portfolio_id=portfolio.id,
            action="portfolio_sync_etoro",
            action_type="system",
            details={
                "positions_count": len(etoro_positions),
                "traders_count": traders_synced,
                "total_value": portfolio.total_value,
                "source": "etoro_api",
            },
        )
        self.db.add(audit)

        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        logger.info("etoro sync completed", positions=len(etoro_positions), mirrors=traders_synced, duration_ms=round(duration, 2))

        return {
            "status": "success",
            "message": "Portfolio synced from eToro API",
            "positions_synced": len(etoro_positions),
            "traders_synced": traders_synced,
            "duration_ms": round(duration, 2),
        }

    async def _sync_simulated(self, portfolio: Portfolio, user_id: int, start: datetime) -> dict:
        positions = await self.get_positions(portfolio.id)
        traders_stmt = select(CopiedTrader).where(CopiedTrader.portfolio_id == portfolio.id)
        traders_result = await self.db.execute(traders_stmt)
        traders = list(traders_result.scalars().all())

        today_seed = hash(datetime.now(timezone.utc).strftime("%Y-%m-%d")) & 0x7FFFFFFF
        rng = __import__("random").Random(today_seed)

        for position in positions:
            price_shift = rng.uniform(-0.05, 0.05)
            position.current_price = position.entry_price * (1 + price_shift)
            position.pnl = (position.current_price - position.entry_price) * position.amount
            position.pnl_percent = ((position.current_price - position.entry_price) / position.entry_price) * 100 if position.entry_price else 0
            position.updated_at = datetime.now(timezone.utc)

        for trader in traders:
            roi_shift = rng.uniform(-0.03, 0.03)
            trader.total_roi += roi_shift
            trader.total_pnl = trader.current_value * trader.total_roi / 100
            trader.last_updated = datetime.now(timezone.utc)

        total_invested = sum(p.allocated_amount for p in positions)
        total_unrealized = sum(p.pnl for p in positions)
        total_value = (portfolio.cash_balance or 0) + total_invested + total_unrealized

        portfolio.total_value = round(total_value, 2)
        portfolio.invested_amount = round(total_invested, 2)
        portfolio.unrealized_pnl = round(total_unrealized, 2)
        portfolio.last_updated = datetime.now(timezone.utc)
        portfolio.health_score = await self.calculate_health_score(portfolio.id)

        risk = RiskMetric(
            portfolio_id=portfolio.id,
            total_exposure=round(total_invested, 2),
            var_95=round(total_value * 0.05, 2),
            max_drawdown=0.0,
            volatility=rng.uniform(0.1, 0.3),
            concentration_risk=round(
                max((t.allocation_percent for t in traders), default=0) / 100, 2
            ),
            correlation_risk=0.3,
            leverage_ratio=1.0,
            risk_score=round(100 - portfolio.health_score, 1),
            health_score=portfolio.health_score,
        )
        self.db.add(risk)

        audit = AuditLog(
            portfolio_id=portfolio.id,
            action="portfolio_sync_simulated",
            action_type="system",
            details={
                "positions_count": len(positions),
                "traders_count": len(traders),
                "total_value": portfolio.total_value,
            },
        )
        self.db.add(audit)

        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return {
            "status": "success",
            "message": "Portfolio synced (simulated)",
            "positions_synced": len(positions),
            "traders_synced": len(traders),
            "duration_ms": round(duration, 2),
        }

    async def get_portfolio_timeline(
        self, portfolio_id: int, days: int = 30
    ) -> List[PortfolioTimelinePoint]:
        return await self.get_performance_history(portfolio_id, f"{days}d")
