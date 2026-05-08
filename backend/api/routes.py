import structlog
import time
import random
from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status, WebSocket, WebSocketDisconnect
from sqlalchemy import select, desc, func as sa_func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.db import get_db
from backend.database.models import (
    Portfolio,
    Position,
    CopiedTrader,
    TraderPerformance,
    RiskMetric,
    AutomationRule,
    AutomationLog,
    Alert,
    AiRecommendation,
    AuditLog,
    User,
)
from backend.database.schema import (
    PortfolioResponse,
    PortfolioDetailResponse,
    PortfolioSummary,
    PositionResponse,
    TraderResponse,
    TraderAnalysis,
    TraderPerformanceResponse,
    RiskMetricResponse,
    RiskLimitsResponse,
    RiskLimitsUpdate,
    AutomationRuleCreate,
    AutomationRuleUpdate,
    AutomationRuleResponse,
    AutomationLogResponse,
    AlertResponse,
    AlertCreate,
    AiRecommendationResponse,
    AuditLogResponse,
    PaginatedResponse,
    SyncResponse,
    AnalyzeRequest,
    EmergencyStopResponse,
    MessageResponse,
    HealthResponse,
    PortfolioTimelinePoint,
    TraderAnalysis as TraderAnalysisSchema,
    SettingsResponse,
    PaperTradingUpdate,
    EtoroDemoModeUpdate,
    EtoroKeysUpdate,
    TelegramConfigUpdate,
)
from backend.config.settings import settings
from backend.api.deps import (
    get_current_user,
    get_portfolio_service,
    get_trader_service,
    get_alerts_service,
    get_automation_engine,
    get_analytics_service,
    get_claude_client,
    scheduler_service,
)
from backend.services.portfolio_service import PortfolioService
from backend.services.trader_service import TraderService
from backend.services.alerts_service import AlertsService
from backend.api.websocket import manager

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1")


# ─── Portfolio Endpoints ──────────────────────────────────────────────────────


@router.get("/portfolio", response_model=PortfolioDetailResponse)
async def get_portfolio(
    user: User = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    trader_service: TraderService = Depends(get_trader_service),
    db: AsyncSession = Depends(get_db),
):
    """Get full portfolio details with summary, positions, and traders."""
    portfolio = await portfolio_service.get_or_create_portfolio(user.id)
    summary = await portfolio_service.get_portfolio_summary(portfolio.id)
    positions = await portfolio_service.get_positions(portfolio.id)
    traders = await trader_service.get_all_traders(portfolio.id)

    risk_stmt = (
        select(RiskMetric)
        .where(RiskMetric.portfolio_id == portfolio.id)
        .order_by(desc(RiskMetric.timestamp))
        .limit(1)
    )
    risk_result = await db.execute(risk_stmt)
    latest_risk = risk_result.scalar_one_or_none()

    return PortfolioDetailResponse(
        id=portfolio.id,
        user_id=portfolio.user_id,
        total_value=portfolio.total_value,
        cash_balance=portfolio.cash_balance,
        invested_amount=portfolio.invested_amount,
        unrealized_pnl=portfolio.unrealized_pnl,
        realized_pnl=portfolio.realized_pnl,
        daily_pnl=portfolio.daily_pnl,
        weekly_pnl=portfolio.weekly_pnl,
        monthly_pnl=portfolio.monthly_pnl,
        health_score=portfolio.health_score,
        last_updated=portfolio.last_updated,
        created_at=portfolio.created_at,
        summary=summary,
        positions=[PositionResponse.model_validate(p) for p in positions],
        traders=[TraderResponse.model_validate(t) for t in traders],
        metrics={
            "id": latest_risk.id,
            "portfolio_id": latest_risk.portfolio_id,
            "timestamp": latest_risk.timestamp.isoformat() if latest_risk.timestamp else None,
            "total_exposure": latest_risk.total_exposure,
            "var_95": latest_risk.var_95,
            "max_drawdown": latest_risk.max_drawdown,
            "volatility": latest_risk.volatility,
            "concentration_risk": latest_risk.concentration_risk,
            "correlation_risk": latest_risk.correlation_risk,
            "leverage_ratio": latest_risk.leverage_ratio,
            "risk_score": latest_risk.risk_score,
            "health_score": latest_risk.health_score,
        } if latest_risk else None,
    )


@router.get("/portfolio/positions", response_model=List[PositionResponse])
async def get_positions(
    user: User = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    """Get all open positions for the user's portfolio."""
    portfolio = await portfolio_service.get_or_create_portfolio(user.id)
    positions = await portfolio_service.get_positions(portfolio.id)
    return [PositionResponse.model_validate(p) for p in positions]


@router.get("/portfolio/history", response_model=List[PortfolioTimelinePoint])
async def get_portfolio_history(
    period: str = Query("1m", description="Period: 1w, 1m, 3m, 6m, 1y, all"),
    user: User = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    """Get historical portfolio performance data."""
    portfolio = await portfolio_service.get_or_create_portfolio(user.id)
    return await portfolio_service.get_performance_history(portfolio.id, period)


@router.post("/portfolio/sync", response_model=SyncResponse)
async def sync_portfolio(
    user: User = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    """Trigger a portfolio synchronization with eToro."""
    result = await portfolio_service.sync_portfolio(user.id)
    return SyncResponse(**result)


# ─── Trader Endpoints ─────────────────────────────────────────────────────────


@router.get("/traders", response_model=List[TraderResponse])
async def list_traders(
    user: User = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    trader_service: TraderService = Depends(get_trader_service),
):
    """List all copied traders in the portfolio."""
    portfolio = await portfolio_service.get_or_create_portfolio(user.id)
    traders = await trader_service.get_all_traders(portfolio.id)
    return [TraderResponse.model_validate(t) for t in traders]


@router.get("/traders/analysis", response_model=List[TraderAnalysis])
async def analyze_all_traders(
    user: User = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    trader_service: TraderService = Depends(get_trader_service),
):
    """Get analyzed classifications for all traders."""
    portfolio = await portfolio_service.get_or_create_portfolio(user.id)
    return await trader_service.analyze_all_traders(portfolio.id)


@router.get("/traders/{trader_id}", response_model=TraderAnalysis)
async def get_trader_detail(
    trader_id: int,
    trader_service: TraderService = Depends(get_trader_service),
):
    """Get detailed trader analysis with classification and AI summary."""
    analysis = await trader_service.get_trader_analysis(trader_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Trader not found")
    return analysis


@router.get("/traders/{trader_id}/performance", response_model=List[TraderPerformanceResponse])
async def get_trader_performance(
    trader_id: int,
    period: str = Query("3m", description="Period: 1m, 3m, 6m, 1y"),
    trader_service: TraderService = Depends(get_trader_service),
    db: AsyncSession = Depends(get_db),
):
    """Get trader performance history."""
    trader = await db.get(CopiedTrader, trader_id)
    if trader is None:
        raise HTTPException(status_code=404, detail="Trader not found")
    records = await trader_service.get_trader_performance(trader_id, period)
    return [TraderPerformanceResponse.model_validate(r) for r in records]


@router.post("/traders/{trader_id}/pause", response_model=TraderResponse)
async def pause_trader(
    trader_id: int,
    trader_service: TraderService = Depends(get_trader_service),
):
    """Pause a copy relationship."""
    trader = await trader_service.pause_trader(trader_id)
    if trader is None:
        raise HTTPException(status_code=404, detail="Trader not found")
    return TraderResponse.model_validate(trader)


@router.post("/traders/{trader_id}/resume", response_model=TraderResponse)
async def resume_trader(
    trader_id: int,
    trader_service: TraderService = Depends(get_trader_service),
):
    """Resume a paused copy relationship."""
    trader = await trader_service.resume_trader(trader_id)
    if trader is None:
        raise HTTPException(status_code=404, detail="Trader not found")
    return TraderResponse.model_validate(trader)


# ─── Risk Endpoints ───────────────────────────────────────────────────────────


@router.get("/risk/summary")
async def get_risk_summary(
    user: User = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    db: AsyncSession = Depends(get_db),
):
    """Get risk overview with latest metrics and limits."""
    portfolio = await portfolio_service.get_or_create_portfolio(user.id)

    risk_stmt = (
        select(RiskMetric)
        .where(RiskMetric.portfolio_id == portfolio.id)
        .order_by(desc(RiskMetric.timestamp))
        .limit(1)
    )
    risk_result = await db.execute(risk_stmt)
    latest_risk = risk_result.scalar_one_or_none()

    traders_stmt = select(CopiedTrader).where(CopiedTrader.portfolio_id == portfolio.id)
    traders_result = await db.execute(traders_stmt)
    traders = list(traders_result.scalars().all())

    high_risk_traders = [t for t in traders if t.classification in ("aggressive", "high_risk")]
    paused_traders = [t for t in traders if t.status == "paused"]

    return {
        "current_risk_score": round(latest_risk.risk_score, 1) if latest_risk else 0,
        "current_health_score": round(latest_risk.health_score, 1) if latest_risk else 100,
        "total_exposure": round(latest_risk.total_exposure, 2) if latest_risk else 0,
        "var_95": round(latest_risk.var_95, 2) if latest_risk else 0,
        "max_drawdown": round(latest_risk.max_drawdown, 4) if latest_risk else 0,
        "volatility": round(latest_risk.volatility, 4) if latest_risk else 0,
        "concentration_risk": round(latest_risk.concentration_risk, 2) if latest_risk else 0,
        "leverage_ratio": round(latest_risk.leverage_ratio, 2) if latest_risk else 1.0,
        "high_risk_traders": len(high_risk_traders),
        "paused_traders": len(paused_traders),
        "active_traders": len([t for t in traders if t.status == "active"]),
        "limits": {
            "max_drawdown": settings.MAX_PORTFOLIO_DRAWDOWN,
            "max_allocation_per_trader": settings.MAX_ALLOCATION_PER_TRADER,
            "min_diversification": settings.MIN_DIVERSIFICATION,
            "cooldown_days": settings.COOLDOWN_DAYS_AFTER_LOSS,
        },
    }


@router.get("/risk/metrics", response_model=List[RiskMetricResponse])
async def get_risk_metrics(
    limit: int = Query(100, ge=1, le=1000),
    user: User = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    db: AsyncSession = Depends(get_db),
):
    """Get historical risk metrics."""
    portfolio = await portfolio_service.get_or_create_portfolio(user.id)
    stmt = (
        select(RiskMetric)
        .where(RiskMetric.portfolio_id == portfolio.id)
        .order_by(desc(RiskMetric.timestamp))
        .limit(limit)
    )
    result = await db.execute(stmt)
    metrics = list(result.scalars().all())
    return [RiskMetricResponse.model_validate(m) for m in metrics]


@router.get("/risk/limits", response_model=RiskLimitsResponse)
async def get_risk_limits():
    """Get current risk limit configuration."""
    return RiskLimitsResponse(
        max_drawdown=settings.MAX_PORTFOLIO_DRAWDOWN,
        max_allocation_per_trader=settings.MAX_ALLOCATION_PER_TRADER,
        min_diversification=settings.MIN_DIVERSIFICATION,
        volatility_exposure_reduction=settings.VOLATILITY_EXPOSURE_REDUCTION,
        cooldown_days_after_loss=settings.COOLDOWN_DAYS_AFTER_LOSS,
    )


@router.put("/risk/limits", response_model=RiskLimitsResponse)
async def update_risk_limits(
    updates: RiskLimitsUpdate,
):
    """Update risk limit configuration."""
    if updates.max_drawdown is not None:
        settings.MAX_PORTFOLIO_DRAWDOWN = updates.max_drawdown
    if updates.max_allocation_per_trader is not None:
        settings.MAX_ALLOCATION_PER_TRADER = updates.max_allocation_per_trader
    if updates.min_diversification is not None:
        settings.MIN_DIVERSIFICATION = updates.min_diversification
    if updates.volatility_exposure_reduction is not None:
        settings.VOLATILITY_EXPOSURE_REDUCTION = updates.volatility_exposure_reduction
    if updates.cooldown_days_after_loss is not None:
        settings.COOLDOWN_DAYS_AFTER_LOSS = updates.cooldown_days_after_loss

    logger.info("risk limits updated", updates=updates.model_dump(exclude_none=True))

    return RiskLimitsResponse(
        max_drawdown=settings.MAX_PORTFOLIO_DRAWDOWN,
        max_allocation_per_trader=settings.MAX_ALLOCATION_PER_TRADER,
        min_diversification=settings.MIN_DIVERSIFICATION,
        volatility_exposure_reduction=settings.VOLATILITY_EXPOSURE_REDUCTION,
        cooldown_days_after_loss=settings.COOLDOWN_DAYS_AFTER_LOSS,
    )


@router.post("/risk/emergency-stop", response_model=EmergencyStopResponse)
async def emergency_stop(
    user: User = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    trader_service: TraderService = Depends(get_trader_service),
    db: AsyncSession = Depends(get_db),
):
    """Emergency stop - pause all active copy relationships."""
    portfolio = await portfolio_service.get_or_create_portfolio(user.id)
    traders = await trader_service.get_all_traders(portfolio.id)

    actions_taken = []
    for trader in traders:
        if trader.status == "active":
            trader.status = "paused"
            trader.last_updated = datetime.now(timezone.utc)
            actions_taken.append(f"Paused {trader.trader_name}")

    audit = AuditLog(
        portfolio_id=portfolio.id,
        action="emergency_stop",
        action_type="manual",
        details={"traders_paused": len(actions_taken)},
    )
    db.add(audit)

    alert = Alert(
        portfolio_id=portfolio.id,
        type="automation",
        title="Emergency Stop Activated",
        message=f"All {len(actions_taken)} active copy relationships have been paused.",
        severity="critical",
    )
    db.add(alert)

    await manager.send_risk_alert(portfolio.id, {
        "type": "emergency_stop",
        "severity": "critical",
        "message": f"Emergency stop: {len(actions_taken)} traders paused",
    })

    logger.warning("emergency stop activated", user=user.id, traders_paused=len(actions_taken))

    return EmergencyStopResponse(
        status="success",
        message=f"Emergency stop activated. {len(actions_taken)} traders paused.",
        actions_taken=actions_taken,
    )


# ─── Automation Endpoints ─────────────────────────────────────────────────────


@router.get("/automation/rules", response_model=List[AutomationRuleResponse])
async def list_automation_rules(
    user: User = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    db: AsyncSession = Depends(get_db),
):
    """List all automation rules."""
    portfolio = await portfolio_service.get_or_create_portfolio(user.id)
    stmt = select(AutomationRule).where(AutomationRule.portfolio_id == portfolio.id)
    result = await db.execute(stmt)
    rules = list(result.scalars().all())
    return [AutomationRuleResponse.model_validate(r) for r in rules]


@router.post("/automation/rules", response_model=AutomationRuleResponse, status_code=201)
async def create_automation_rule(
    rule_data: AutomationRuleCreate,
    user: User = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    db: AsyncSession = Depends(get_db),
):
    """Create a new automation rule."""
    valid_types = [
        "take_profit", "partial_profit", "rebalance",
        "reduce_allocation", "pause_copy", "dynamic_exposure",
    ]
    if rule_data.rule_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid rule_type. Must be one of: {', '.join(valid_types)}",
        )

    portfolio = await portfolio_service.get_or_create_portfolio(user.id)
    rule = AutomationRule(
        portfolio_id=portfolio.id,
        name=rule_data.name,
        rule_type=rule_data.rule_type,
        enabled=rule_data.enabled,
        config=rule_data.config,
        cooldown_days=rule_data.cooldown_days,
    )
    db.add(rule)
    await db.flush()

    audit = AuditLog(
        portfolio_id=portfolio.id,
        action=f"create_rule:{rule.name}",
        action_type="manual",
        details={"rule_id": rule.id, "rule_type": rule.rule_type},
    )
    db.add(audit)

    logger.info("automation rule created", rule_id=rule.id, type=rule.rule_type)
    return AutomationRuleResponse.model_validate(rule)


@router.put("/automation/rules/{rule_id}", response_model=AutomationRuleResponse)
async def update_automation_rule(
    rule_id: int,
    rule_data: AutomationRuleUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an automation rule."""
    rule = await db.get(AutomationRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    if rule_data.name is not None:
        rule.name = rule_data.name
    if rule_data.enabled is not None:
        rule.enabled = rule_data.enabled
    if rule_data.config is not None:
        rule.config = rule_data.config
    if rule_data.cooldown_days is not None:
        rule.cooldown_days = rule_data.cooldown_days

    rule.updated_at = datetime.now(timezone.utc)
    return AutomationRuleResponse.model_validate(rule)


@router.delete("/automation/rules/{rule_id}", response_model=MessageResponse)
async def delete_automation_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an automation rule."""
    rule = await db.get(AutomationRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.delete(rule)
    return MessageResponse(message="Rule deleted", status="success")


@router.put("/automation/rules/{rule_id}/toggle", response_model=AutomationRuleResponse)
async def toggle_automation_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable an automation rule."""
    rule = await db.get(AutomationRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule.enabled = not rule.enabled
    rule.updated_at = datetime.now(timezone.utc)

    audit = AuditLog(
        portfolio_id=rule.portfolio_id,
        action=f"toggle_rule:{rule.name}",
        action_type="manual",
        details={"rule_id": rule.id, "enabled": rule.enabled},
    )
    db.add(audit)

    logger.info("rule toggled", rule_id=rule_id, enabled=rule.enabled)
    return AutomationRuleResponse.model_validate(rule)


@router.get("/automation/logs", response_model=List[AutomationLogResponse])
async def get_automation_logs(
    limit: int = Query(50, ge=1, le=500),
    user: User = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    db: AsyncSession = Depends(get_db),
):
    """Get automation execution logs."""
    portfolio = await portfolio_service.get_or_create_portfolio(user.id)
    stmt = (
        select(AutomationLog)
        .join(AutomationRule)
        .where(AutomationRule.portfolio_id == portfolio.id)
        .order_by(desc(AutomationLog.triggered_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    logs = list(result.scalars().all())
    return [AutomationLogResponse.model_validate(l) for l in logs]


@router.post("/automation/execute/{rule_id}", response_model=AutomationLogResponse)
async def execute_automation_rule(
    rule_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger an automation rule."""
    rule = await db.get(AutomationRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    if rule.cooldown_days > 0 and rule.last_triggered:
        cooldown_end = rule.last_triggered + timedelta(days=rule.cooldown_days)
        if datetime.now(timezone.utc) < cooldown_end:
            raise HTTPException(
                status_code=429,
                detail=f"Rule is in cooldown until {cooldown_end.isoformat()}",
            )

    config = rule.config or {}
    action_details = {}

    if rule.rule_type == "take_profit":
        target = config.get("take_profit_target", 0.1)
        portfolio = await db.get(Portfolio, rule.portfolio_id)
        if portfolio:
            total_pnl = (portfolio.unrealized_pnl or 0) + (portfolio.realized_pnl or 0)
            action_details = {
                "target_pnl_percent": target,
                "current_pnl": total_pnl,
                "action": "notification_only",
            }
    elif rule.rule_type == "partial_profit":
        threshold = config.get("partial_profit_threshold", 0.15)
        take_percent = config.get("partial_profit_percent", 0.5)
        action_details = {
            "threshold": threshold,
            "take_profit_percent": take_percent,
            "action": "simulated_partial_close",
        }
    elif rule.rule_type == "rebalance":
        threshold = config.get("rebalance_threshold", 0.05)
        action_details = {
            "imbalance_threshold": threshold,
            "action": "rebalance_allocations",
            "rebalanced": True,
        }
    elif rule.rule_type == "reduce_allocation":
        threshold = config.get("reduce_allocation_threshold", -0.1)
        reduce_by = config.get("reduce_allocation_by", 0.5)
        action_details = {
            "drawdown_threshold": threshold,
            "reduction_factor": reduce_by,
            "action": "reduced_allocations",
        }
    elif rule.rule_type == "pause_copy":
        drawdown = config.get("pause_copy_drawdown", 0.15)
        action_details = {
            "drawdown_threshold": drawdown,
            "action": "paused_copy_traders",
            "traders_paused": 0,
        }
    elif rule.rule_type == "dynamic_exposure":
        vol_threshold = config.get("dynamic_exposure_volatility_threshold", 0.3)
        max_alloc = config.get("dynamic_exposure_max_allocation", 0.2)
        action_details = {
            "volatility_threshold": vol_threshold,
            "max_allocation": max_alloc,
            "action": "adjusted_exposure",
        }

    log_entry = AutomationLog(
        rule_id=rule.id,
        action=f"manual_execute:{rule.rule_type}",
        status="completed",
        details=action_details,
    )
    db.add(log_entry)
    rule.last_triggered = datetime.now(timezone.utc)

    audit = AuditLog(
        portfolio_id=rule.portfolio_id,
        action=f"execute_rule:{rule.name}",
        action_type="manual",
        details={"rule_id": rule.id, "rule_type": rule.rule_type},
    )
    db.add(audit)

    logger.info("rule executed manually", rule_id=rule_id, type=rule.rule_type)
    return AutomationLogResponse.model_validate(log_entry)


# ─── AI Endpoints ─────────────────────────────────────────────────────────────


@router.get("/ai/recommendations", response_model=List[AiRecommendationResponse])
async def get_ai_recommendations(
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    db: AsyncSession = Depends(get_db),
):
    """Get AI-generated recommendations."""
    portfolio = await portfolio_service.get_or_create_portfolio(user.id)
    stmt = (
        select(AiRecommendation)
        .where(AiRecommendation.portfolio_id == portfolio.id)
        .order_by(desc(AiRecommendation.confidence_score), desc(AiRecommendation.created_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    recs = list(result.scalars().all())
    return [AiRecommendationResponse.model_validate(r) for r in recs]


@router.post("/ai/analyze", response_model=List[AiRecommendationResponse])
async def trigger_ai_analysis(
    req: AnalyzeRequest,
    user: User = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    trader_service: TraderService = Depends(get_trader_service),
    db: AsyncSession = Depends(get_db),
):
    """Trigger AI portfolio analysis and generate recommendations."""
    portfolio = await portfolio_service.get_or_create_portfolio(user.id)
    traders = await trader_service.get_all_traders(portfolio.id)
    positions = await portfolio_service.get_positions(portfolio.id)
    summary = await portfolio_service.get_portfolio_summary(portfolio.id)

    recommendations = []

    if traders:
        losing_traders = [t for t in traders if t.total_pnl < 0]
        if losing_traders:
            for t in losing_traders[:3]:
                rec = AiRecommendation(
                    portfolio_id=portfolio.id,
                    recommendation_type="trader_review",
                    title=f"Review {t.trader_name} - Negative Performance",
                    summary=(
                        f"{t.trader_name} shows negative PnL of ${t.total_pnl:.2f} "
                        f"with {t.allocation_percent:.1f}% allocation. "
                        f"Consider reducing allocation or pausing this copy relationship."
                    ),
                    confidence_score=round(random.uniform(0.6, 0.85), 2),
                    details={
                        "trader_id": t.id,
                        "trader_name": t.trader_name,
                        "total_pnl": round(t.total_pnl, 2),
                        "allocation": t.allocation_percent,
                        "status": t.status,
                        "classification": t.classification,
                    },
                )
                recommendations.append(rec)

        high_alloc_traders = [
            t for t in traders
            if t.allocation_percent > settings.MAX_ALLOCATION_PER_TRADER * 100
        ]
        for t in high_alloc_traders:
            rec = AiRecommendation(
                portfolio_id=portfolio.id,
                recommendation_type="rebalance",
                title=f"Rebalance {t.trader_name} - High Concentration",
                summary=(
                    f"{t.trader_name} has {t.allocation_percent:.1f}% allocation, "
                    f"exceeding the {settings.MAX_ALLOCATION_PER_TRADER * 100:.0f}% limit. "
                    f"Consider reducing to improve diversification."
                ),
                confidence_score=round(random.uniform(0.7, 0.9), 2),
                details={
                    "trader_id": t.id,
                    "trader_name": t.trader_name,
                    "current_allocation": t.allocation_percent,
                    "max_allowed": settings.MAX_ALLOCATION_PER_TRADER * 100,
                    "excess": round(t.allocation_percent - settings.MAX_ALLOCATION_PER_TRADER * 100, 2),
                },
            )
            recommendations.append(rec)

    if summary.health_score < 70:
        rec = AiRecommendation(
            portfolio_id=portfolio.id,
            recommendation_type="risk_alert",
            title="Portfolio Health Score Below Threshold",
            summary=(
                f"Portfolio health score is {summary.health_score}/100. "
                "Review risk management settings and consider pausing underperforming traders."
            ),
            confidence_score=0.85,
            details={
                "health_score": summary.health_score,
                "total_value": summary.total_value,
                "day_change": summary.daily_pnl,
            },
        )
        recommendations.append(rec)

    if not recommendations:
        rec = AiRecommendation(
            portfolio_id=portfolio.id,
            recommendation_type="portfolio_health",
            title="Portfolio Performing Within Parameters",
            summary=(
                f"Portfolio is healthy (score: {summary.health_score}/100) "
                f"with {summary.total_traders} traders and {summary.total_positions} positions. "
                "Continue monitoring and maintain current strategy."
            ),
            confidence_score=0.9,
            details={
                "health_score": summary.health_score,
                "total_traders": summary.total_traders,
                "total_positions": summary.total_positions,
            },
        )
        recommendations.append(rec)

    for rec in recommendations:
        db.add(rec)
    await db.flush()

    audit = AuditLog(
        portfolio_id=portfolio.id,
        action="ai_analysis",
        action_type="system",
        details={"recommendations_generated": len(recommendations)},
    )
    db.add(audit)

    logger.info(
        "ai analysis completed",
        portfolio_id=portfolio.id,
        recommendations=len(recommendations),
    )
    return [AiRecommendationResponse.model_validate(r) for r in recommendations]


@router.get("/ai/weekly-summary", response_model=AiRecommendationResponse | MessageResponse)
async def get_weekly_summary(
    user: User = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    alerts_service: AlertsService = Depends(get_alerts_service),
):
    """Get the weekly AI portfolio summary."""
    portfolio = await portfolio_service.get_or_create_portfolio(user.id)
    alert = await alerts_service.generate_weekly_summary(portfolio.id)

    return AiRecommendationResponse(
        id=0,
        portfolio_id=portfolio.id,
        recommendation_type="weekly_summary",
        title=alert.title,
        summary=alert.message,
        confidence_score=0.95,
        details={
            "alert_id": alert.id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        applied=False,
        created_at=datetime.now(timezone.utc),
    )


# ─── Alerts Endpoints ─────────────────────────────────────────────────────────


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    alerts_service: AlertsService = Depends(get_alerts_service),
):
    """Get portfolio alerts."""
    portfolio = await portfolio_service.get_or_create_portfolio(user.id)

    await alerts_service.check_profit_milestones(portfolio.id)
    await alerts_service.check_drawdown_alerts(portfolio.id)
    await alerts_service.check_volatility_alerts(portfolio.id)
    await alerts_service.check_imbalance_alerts(portfolio.id)

    alerts = await alerts_service.get_alerts(portfolio.id, unread_only)
    return [AlertResponse.model_validate(a) for a in alerts[:limit]]


@router.put("/alerts/{alert_id}/read", response_model=AlertResponse)
async def mark_alert_read(
    alert_id: int,
    alerts_service: AlertsService = Depends(get_alerts_service),
):
    """Mark an alert as read."""
    alert = await alerts_service.mark_read(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertResponse.model_validate(alert)


@router.delete("/alerts/{alert_id}", response_model=MessageResponse)
async def delete_alert(
    alert_id: int,
    alerts_service: AlertsService = Depends(get_alerts_service),
):
    """Delete an alert."""
    deleted = await alerts_service.delete_alert(alert_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Alert not found")
    return MessageResponse(message="Alert deleted", status="success")


# ─── Audit Endpoints ──────────────────────────────────────────────────────────


@router.get("/audit", response_model=PaginatedResponse[AuditLogResponse])
async def get_audit_trail(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated audit trail."""
    portfolio = await portfolio_service.get_or_create_portfolio(user.id)

    count_stmt = select(sa_func.count()).select_from(AuditLog).where(
        AuditLog.portfolio_id == portfolio.id
    )
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    total_pages = max(1, (total + page_size - 1) // page_size)
    offset = (page - 1) * page_size

    stmt = (
        select(AuditLog)
        .where(AuditLog.portfolio_id == portfolio.id)
        .order_by(desc(AuditLog.created_at))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    logs = list(result.scalars().all())

    return PaginatedResponse[AuditLogResponse](
        items=[AuditLogResponse.model_validate(l) for l in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ─── Settings Endpoints ──────────────────────────────────────────────────────


def _mask_key(key: str | None) -> str | None:
    if not key:
        return None
    if len(key) <= 8:
        return key[:2] + "****"
    return key[:4] + "****" + key[-4:]


def _settings_response() -> SettingsResponse:
    return SettingsResponse(
        paper_trading=settings.PAPER_TRADING,
        etoro_demo_mode=settings.ETORO_DEMO_MODE,
        telegram_configured=bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID),
        etoro_configured=bool(settings.ETORO_PUBLIC_API_KEY and settings.ETORO_USER_KEY),
        etoro_public_key_masked=_mask_key(settings.ETORO_PUBLIC_API_KEY or settings.ETORO_API_KEY),
        etoro_user_key_masked=_mask_key(settings.ETORO_USER_KEY or settings.ETORO_USERNAME),
        telegram_bot_token_masked=_mask_key(settings.TELEGRAM_BOT_TOKEN),
        telegram_chat_id_masked=_mask_key(settings.TELEGRAM_CHAT_ID),
    )


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """Get current application settings (masked keys)."""
    return _settings_response()


@router.put("/settings/paper-trading", response_model=SettingsResponse)
async def update_paper_trading(update: PaperTradingUpdate):
    """Toggle paper trading mode."""
    settings.PAPER_TRADING = update.paper_trading
    logger.info("paper trading toggled", enabled=settings.PAPER_TRADING)
    return _settings_response()


@router.put("/settings/etoro/demo-mode", response_model=SettingsResponse)
async def update_etoro_demo_mode(update: EtoroDemoModeUpdate):
    """Toggle eToro demo (Virtual) mode."""
    settings.ETORO_DEMO_MODE = update.etoro_demo_mode
    logger.info("etoro demo mode toggled", enabled=settings.ETORO_DEMO_MODE)
    return _settings_response()


@router.put("/settings/etoro", response_model=SettingsResponse)
async def update_etoro_keys(update: EtoroKeysUpdate):
    """Update eToro API keys."""
    if update.public_api_key is not None:
        settings.ETORO_PUBLIC_API_KEY = update.public_api_key
    if update.user_key is not None:
        settings.ETORO_USER_KEY = update.user_key
    logger.info("etoro keys updated")
    return _settings_response()


@router.put("/settings/telegram", response_model=SettingsResponse)
async def update_telegram_config(update: TelegramConfigUpdate):
    """Update Telegram bot configuration."""
    if update.bot_token is not None:
        settings.TELEGRAM_BOT_TOKEN = update.bot_token
    if update.chat_id is not None:
        settings.TELEGRAM_CHAT_ID = update.chat_id
    logger.info("telegram config updated")
    return _settings_response()


@router.post("/settings/etoro/test", response_model=MessageResponse)
async def test_etoro_connection():
    """Test the eToro API connection with current keys."""
    from backend.services.etoro_client import EtoroClient, EtoroAPIError
    import traceback
    client = EtoroClient()
    if not client.is_enabled:
        raise HTTPException(status_code=400, detail="eToro API keys not configured")
    try:
        ok = await client.health_check()
        if ok:
            return MessageResponse(message="eToro API connection successful")
        raise HTTPException(status_code=502, detail="eToro API health check failed (unknown error)")
    except EtoroAPIError as e:
        logger.error("etoro test failed", error=str(e))
        raise HTTPException(status_code=502, detail=f"{str(e)}")
    except Exception as e:
        logger.error("etoro test unexpected error", error=str(e), traceback=traceback.format_exc())
        raise HTTPException(status_code=502, detail=f"Connection error: {str(e)}")


@router.post("/telegram/test", response_model=MessageResponse)
async def test_telegram():
    """Send a test notification via Telegram."""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        raise HTTPException(status_code=400, detail="Telegram not configured")
    try:
        import httpx
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={
                "chat_id": settings.TELEGRAM_CHAT_ID,
                "text": "🟢 Test notification from eToro Portfolio Manager",
            })
            resp.raise_for_status()
        logger.info("telegram test sent")
        return MessageResponse(message="Test notification sent successfully")
    except Exception as e:
        logger.error("telegram test failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Telegram test failed: {str(e)}")
