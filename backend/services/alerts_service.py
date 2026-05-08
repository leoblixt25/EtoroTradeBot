import structlog
import random
from datetime import datetime, timedelta, timezone
from typing import List


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
from sqlalchemy import select, desc, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import (
    Alert,
    Portfolio,
    Position,
    CopiedTrader,
    RiskMetric,
)
from backend.database.schema import AlertResponse
from backend.config.settings import settings

logger = structlog.get_logger(__name__)


class AlertsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_alerts(
        self, portfolio_id: int, unread_only: bool = False
    ) -> List[Alert]:
        stmt = select(Alert).where(Alert.portfolio_id == portfolio_id)
        if unread_only:
            stmt = stmt.where(Alert.read == False)
        stmt = stmt.order_by(desc(Alert.created_at)).limit(100)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_alert(
        self,
        portfolio_id: int,
        alert_type: str,
        title: str,
        message: str,
        severity: str = "info",
    ) -> Alert:
        alert = Alert(
            portfolio_id=portfolio_id,
            type=alert_type,
            title=title,
            message=message,
            severity=severity,
        )
        self.db.add(alert)
        await self.db.flush()
        logger.info(
            "alert created",
            portfolio_id=portfolio_id,
            type=alert_type,
            severity=severity,
        )
        return alert

    async def mark_read(self, alert_id: int) -> Alert | None:
        alert = await self.db.get(Alert, alert_id)
        if alert is None:
            return None
        alert.read = True
        return alert

    async def delete_alert(self, alert_id: int) -> bool:
        alert = await self.db.get(Alert, alert_id)
        if alert is None:
            return False
        await self.db.delete(alert)
        return True

    async def check_profit_milestones(self, portfolio_id: int) -> List[Alert]:
        alerts = []
        portfolio = await self.db.get(Portfolio, portfolio_id)
        if portfolio is None:
            return alerts

        total_pnl = (portfolio.unrealized_pnl or 0) + (portfolio.realized_pnl or 0)
        milestones = [500, 1000, 2500, 5000, 10000, 25000, 50000]

        for milestone in milestones:
            if total_pnl >= milestone:
                exists_stmt = select(Alert).where(
                    Alert.portfolio_id == portfolio_id,
                    Alert.type == "profit_milestone",
                    Alert.title.ilike(f"%${milestone}%"),
                )
                exists_result = await self.db.execute(exists_stmt)
                existing = exists_result.scalar_one_or_none()

                if existing is None:
                    alert = await self.create_alert(
                        portfolio_id=portfolio_id,
                        alert_type="profit_milestone",
                        title=f"Profit Milestone: ${milestone:,.0f}",
                        message=(
                            f"Your portfolio has reached ${milestone:,.0f} in total profits. "
                            f"Current total PnL: ${total_pnl:,.2f}"
                        ),
                        severity="info",
                    )
                    alerts.append(alert)

        return alerts

    async def check_drawdown_alerts(self, portfolio_id: int) -> List[Alert]:
        alerts = []
        portfolio = await self.db.get(Portfolio, portfolio_id)
        if portfolio is None:
            return alerts

        risk_stmt = (
            select(RiskMetric)
            .where(RiskMetric.portfolio_id == portfolio_id)
            .order_by(desc(RiskMetric.timestamp))
            .limit(1)
        )
        risk_result = await self.db.execute(risk_stmt)
        latest_risk = risk_result.scalar_one_or_none()

        if latest_risk is None:
            return alerts

        max_dd = abs(latest_risk.max_drawdown)
        thresholds = [
            (0.10, "warning", "10% Drawdown Warning"),
            (0.15, "warning", "15% Drawdown Warning"),
            (0.20, "critical", "20% Drawdown Alert"),
            (0.25, "critical", "25% Maximum Drawdown Reached"),
        ]

        for threshold, severity, title in thresholds:
            if max_dd >= threshold:
                exists_stmt = select(Alert).where(
                    Alert.portfolio_id == portfolio_id,
                    Alert.type == "drawdown",
                    Alert.title == title,
                    Alert.created_at >= _utcnow() - timedelta(days=1),
                )
                exists_result = await self.db.execute(exists_stmt)
                if exists_result.scalar_one_or_none() is None:
                    alert = await self.create_alert(
                        portfolio_id=portfolio_id,
                        alert_type="drawdown",
                        title=title,
                        message=(
                            f"Portfolio drawdown has reached {max_dd:.1%}. "
                            f"Current risk score: {latest_risk.risk_score:.1f}. "
                            f"{'Consider pausing high-risk copy relationships.' if severity == 'critical' else 'Monitor positions closely.'}"
                        ),
                        severity=severity,
                    )
                    alerts.append(alert)

        return alerts

    async def check_volatility_alerts(self, portfolio_id: int) -> List[Alert]:
        alerts = []
        portfolio = await self.db.get(Portfolio, portfolio_id)
        if portfolio is None:
            return alerts

        risk_stmt = (
            select(RiskMetric)
            .where(RiskMetric.portfolio_id == portfolio_id)
            .order_by(desc(RiskMetric.timestamp))
            .limit(1)
        )
        risk_result = await self.db.execute(risk_stmt)
        latest_risk = risk_result.scalar_one_or_none()

        if latest_risk is None or latest_risk.volatility < 0.3:
            return alerts

        vol = latest_risk.volatility
        severity = "warning" if vol < 0.5 else "critical"

        alert = await self.create_alert(
            portfolio_id=portfolio_id,
            alert_type="volatility",
            title=f"High Portfolio Volatility: {vol:.1%}",
            message=(
                f"Portfolio volatility is at {vol:.1%}, which exceeds normal levels. "
                f"{'Consider reducing high-risk trader allocations.' if severity == 'critical' else 'Monitor positions.'}"
            ),
            severity=severity,
        )
        alerts.append(alert)
        return alerts

    async def check_imbalance_alerts(self, portfolio_id: int) -> List[Alert]:
        alerts = []
        traders_stmt = select(CopiedTrader).where(
            CopiedTrader.portfolio_id == portfolio_id,
            CopiedTrader.status == "active",
        )
        traders_result = await self.db.execute(traders_stmt)
        traders = list(traders_result.scalars().all())

        if not traders:
            return alerts

        for trader in traders:
            if trader.allocation_percent > settings.MAX_ALLOCATION_PER_TRADER * 100:
                alert = await self.create_alert(
                    portfolio_id=portfolio_id,
                    alert_type="imbalance",
                    title=f"Allocation Imbalance: {trader.trader_name}",
                    message=(
                        f"{trader.trader_name} has {trader.allocation_percent:.1f}% allocation, "
                        f"exceeding the maximum of {settings.MAX_ALLOCATION_PER_TRADER * 100:.0f}%. "
                        f"Consider rebalancing to reduce concentration risk."
                    ),
                    severity="warning",
                )
                alerts.append(alert)

        if len(traders) < settings.MIN_DIVERSIFICATION:
            alert = await self.create_alert(
                portfolio_id=portfolio_id,
                alert_type="imbalance",
                title="Insufficient Diversification",
                message=(
                    f"Only {len(traders)} active traders, below minimum of "
                    f"{settings.MIN_DIVERSIFICATION}. Consider adding more copy relationships."
                ),
                severity="warning",
            )
            alerts.append(alert)

        return alerts

    async def generate_weekly_summary(self, portfolio_id: int) -> Alert:
        portfolio = await self.db.get(Portfolio, portfolio_id)
        if portfolio is None:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        weekly_pnl = portfolio.weekly_pnl or 0
        total_value = portfolio.total_value or 0
        health = portfolio.health_score or 100

        positions = await self.db.execute(
            select(Position).where(Position.portfolio_id == portfolio_id)
        )
        positions_list = list(positions.scalars().all())
        top_positions = sorted(positions_list, key=lambda p: abs(p.pnl), reverse=True)[:3]

        traders_stmt = select(CopiedTrader).where(CopiedTrader.portfolio_id == portfolio_id)
        traders_result = await self.db.execute(traders_stmt)
        traders = list(traders_result.scalars().all())

        top_trader = max(traders, key=lambda t: t.total_pnl, default=None)
        worst_trader = min(traders, key=lambda t: t.total_pnl, default=None)

        lines = [
            f"Weekly Portfolio Summary",
            f"Portfolio Value: ${total_value:,.2f}",
            f"Weekly PnL: ${weekly_pnl:,.2f} ({weekly_pnl / max(total_value - weekly_pnl, 1) * 100:.2f}%)",
            f"Health Score: {health}/100",
            f"Active Traders: {len(traders)}",
            f"Open Positions: {len(positions_list)}",
        ]

        if top_trader:
            lines.append(f"Best Trader: {top_trader.trader_name} (PnL: ${top_trader.total_pnl:,.2f})")
        if worst_trader and worst_trader != top_trader:
            lines.append(f"Worst Trader: {worst_trader.trader_name} (PnL: ${worst_trader.total_pnl:,.2f})")

        if top_positions:
            pos_lines = [f"  {p.instrument_symbol}: ${p.pnl:+,.2f}" for p in top_positions]
            lines.append("Top Positions:")
            lines.extend(pos_lines)

        message = "\n".join(lines)

        alert = await self.create_alert(
            portfolio_id=portfolio_id,
            alert_type="weekly_summary",
            title=f"Weekly Summary - {_utcnow().strftime('%b %d, %Y')}",
            message=message,
            severity="info",
        )
        return alert
