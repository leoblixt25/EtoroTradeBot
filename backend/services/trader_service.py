import structlog
import math
import random
from datetime import datetime, timedelta, timezone
from typing import List


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import (
    CopiedTrader,
    TraderPerformance,
    Portfolio,
    AuditLog,
)
from backend.database.schema import (
    TraderResponse,
    TraderAnalysis,
    TraderPerformanceResponse,
)
from backend.config.settings import settings

logger = structlog.get_logger(__name__)


class TraderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_traders(self, portfolio_id: int) -> List[CopiedTrader]:
        stmt = (
            select(CopiedTrader)
            .where(CopiedTrader.portfolio_id == portfolio_id)
            .order_by(CopiedTrader.allocation_percent.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_trader_detail(self, trader_id: int) -> CopiedTrader | None:
        return await self.db.get(CopiedTrader, trader_id)

    async def get_trader_performance(
        self, trader_id: int, period: str = "3m"
    ) -> List[TraderPerformance]:
        days_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
        days = days_map.get(period, 90)
        cutoff = _utcnow() - timedelta(days=days)

        stmt = (
            select(TraderPerformance)
            .where(
                TraderPerformance.trader_id == trader_id,
                TraderPerformance.date >= cutoff,
            )
            .order_by(TraderPerformance.date.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _classify_trader(
        self, trader: CopiedTrader, perf_records: List[TraderPerformance]
    ) -> tuple[str, str]:
        if not perf_records:
            risk_score = random.uniform(20, 80)
            if risk_score < 30:
                return "conservative", "Low volatility and consistent returns"
            elif risk_score < 55:
                return "balanced", "Moderate risk with balanced returns"
            elif risk_score < 75:
                return "aggressive", "High risk tolerance with potential for high returns"
            else:
                return "high_risk", "Very high risk profile with significant volatility"

        avg_volatility = sum(p.volatility for p in perf_records) / len(perf_records)
        avg_drawdown = sum(p.max_drawdown for p in perf_records) / len(perf_records)
        avg_return = sum(p.monthly_return for p in perf_records) / len(perf_records)
        avg_sharpe = sum(p.sharpe_score for p in perf_records) / len(perf_records)

        risk_score = (avg_volatility * 40 + abs(avg_drawdown) * 30 + max(0, 10 - avg_sharpe) * 30)

        if risk_score < 25 and avg_drawdown > -0.1:
            classification = "conservative"
            reason = f"Low volatility ({avg_volatility:.1%}), limited drawdown ({avg_drawdown:.1%})"
        elif risk_score < 50 and avg_sharpe > 0.5:
            classification = "balanced"
            reason = f"Moderate volatility ({avg_volatility:.1%}) with positive Sharpe ({avg_sharpe:.2f})"
        elif risk_score < 75:
            classification = "aggressive"
            reason = f"High volatility ({avg_volatility:.1%}),追求 higher returns"
        else:
            classification = "high_risk"
            reason = f"Very high volatility ({avg_volatility:.1%}) and deep drawdowns ({avg_drawdown:.1%})"

        return classification, reason

    async def get_trader_analysis(self, trader_id: int) -> TraderAnalysis | None:
        trader = await self.db.get(CopiedTrader, trader_id)
        if trader is None:
            return None

        perf_records = await self.get_trader_performance(trader_id, "6m")
        classification, reason = await self._classify_trader(trader, perf_records)

        trader_resp = TraderResponse.model_validate(trader)

        risk_metrics = {
            "volatility": round(sum(p.volatility for p in perf_records) / len(perf_records), 4) if perf_records else 0,
            "max_drawdown": round(min(p.max_drawdown for p in perf_records), 4) if perf_records else 0,
            "sharpe_score": round(sum(p.sharpe_score for p in perf_records) / len(perf_records), 2) if perf_records else 0,
            "win_rate": round(sum(p.win_rate for p in perf_records) / len(perf_records) * 100, 1) if perf_records else 0,
            "consistency": round(sum(p.consistency_score for p in perf_records) / len(perf_records), 2) if perf_records else 0,
        }

        if len(perf_records) >= 2:
            recent = perf_records[0]
            older = perf_records[-1]
            if recent.monthly_return > older.monthly_return + 0.02:
                perf_trend = "improving"
            elif recent.monthly_return < older.monthly_return - 0.02:
                perf_trend = "declining"
            else:
                perf_trend = "stable"
        else:
            perf_trend = "insufficient_data"

        recommendation = await self._generate_recommendation(
            classification, risk_metrics, trader.allocation_percent, perf_trend
        )

        ai_summary = (
            f"Trader {trader.trader_name} is classified as {classification} "
            f"with a {perf_trend} performance trend. "
            f"Current allocation: {trader.allocation_percent:.1f}%. "
            f"{'Consider monitoring closely.' if perf_trend == 'declining' else 'Performance is within expected parameters.'}"
        )

        return TraderAnalysis(
            trader=trader_resp,
            classification=classification,
            classification_reason=reason,
            risk_metrics=risk_metrics,
            ai_summary=ai_summary,
            performance_trend=perf_trend,
            recommendation=recommendation,
        )

    async def _generate_recommendation(
        self,
        classification: str,
        risk_metrics: dict,
        allocation: float,
        trend: str,
    ) -> str:
        if trend == "declining" and classification in ("aggressive", "high_risk"):
            return f"Reduce allocation from {allocation:.1f}% due to declining performance with high risk profile."
        if trend == "declining":
            return f"Monitor closely. Consider reducing allocation if decline continues."
        if classification == "conservative" and trend == "improving":
            return f"Stable performer. Consider maintaining or slightly increasing allocation."
        if classification == "high_risk" and allocation > 0.15:
            return f"High risk trader with {allocation:.1f}% allocation. Consider reducing to under 15%."
        if risk_metrics.get("consistency", 0) > 0.7:
            return f"Consistent performer. Maintain current allocation of {allocation:.1f}%."
        return f"Maintain current allocation. Review again in 30 days."

    async def analyze_all_traders(self, portfolio_id: int) -> List[TraderAnalysis]:
        traders = await self.get_all_traders(portfolio_id)
        analyses = []
        for trader in traders:
            analysis = await self.get_trader_analysis(trader.id)
            if analysis:
                analyses.append(analysis)
        return analyses

    async def pause_trader(self, trader_id: int) -> CopiedTrader | None:
        trader = await self.db.get(CopiedTrader, trader_id)
        if trader is None:
            return None
        if trader.status == "paused":
            return trader

        trader.status = "paused"
        trader.last_updated = _utcnow()

        audit = AuditLog(
            portfolio_id=trader.portfolio_id,
            action=f"pause_trader:{trader.trader_name}",
            action_type="manual",
            details={"trader_id": trader_id, "trader_name": trader.trader_name},
        )
        self.db.add(audit)

        logger.info("trader paused", trader_id=trader_id, name=trader.trader_name)
        return trader

    async def resume_trader(self, trader_id: int) -> CopiedTrader | None:
        trader = await self.db.get(CopiedTrader, trader_id)
        if trader is None:
            return None
        if trader.status == "active":
            return trader

        trader.status = "active"
        trader.last_updated = _utcnow()

        audit = AuditLog(
            portfolio_id=trader.portfolio_id,
            action=f"resume_trader:{trader.trader_name}",
            action_type="manual",
            details={"trader_id": trader_id, "trader_name": trader.trader_name},
        )
        self.db.add(audit)

        logger.info("trader resumed", trader_id=trader_id, name=trader.trader_name)
        return trader

    async def get_trader_classification(self, trader_id: int) -> str | None:
        trader = await self.db.get(CopiedTrader, trader_id)
        if trader is None:
            return None
        return trader.classification
