from datetime import datetime
from typing import List, Generic, TypeVar, Any, Optional
from pydantic import BaseModel, Field, field_validator
import json

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int = 1
    page_size: int = 20
    total_pages: int = 1


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., max_length=255)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PositionResponse(BaseModel):
    id: int
    portfolio_id: int
    instrument_type: str
    instrument_symbol: str
    instrument_name: str
    amount: float
    entry_price: float
    current_price: float
    allocated_amount: float
    pnl: float
    pnl_percent: float
    allocation_percent: float
    opened_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TraderPerformanceResponse(BaseModel):
    id: int
    trader_id: int
    date: datetime
    monthly_return: float
    volatility: float
    max_drawdown: float
    sharpe_score: float
    risk_score: float
    consistency_score: float
    trade_count: int
    win_rate: float
    avg_holding_days: float
    diversification_score: float
    is_underperforming: bool

    model_config = {"from_attributes": True}


class TraderResponse(BaseModel):
    id: int
    portfolio_id: int
    trader_name: str
    trader_id: str
    allocation_percent: float
    current_value: float
    total_pnl: float
    total_roi: float
    status: str
    classification: str
    copied_at: datetime
    last_updated: datetime

    model_config = {"from_attributes": True}


class TraderAnalysis(BaseModel):
    trader: TraderResponse
    classification: str
    classification_reason: str = ""
    risk_metrics: dict = {}
    ai_summary: str = ""
    performance_trend: str = ""
    recommendation: str = ""


class PortfolioSummary(BaseModel):
    total_value: float
    cash_balance: float
    invested_amount: float
    unrealized_pnl: float
    realized_pnl: float
    daily_pnl: float
    weekly_pnl: float
    monthly_pnl: float
    health_score: float
    total_positions: int = 0
    total_traders: int = 0
    active_traders: int = 0
    diversification_count: int = 0
    largest_allocation: float = 0.0
    day_change_percent: float = 0.0


class PortfolioResponse(BaseModel):
    id: int
    user_id: int
    total_value: float
    cash_balance: float
    invested_amount: float
    unrealized_pnl: float
    realized_pnl: float
    daily_pnl: float
    weekly_pnl: float
    monthly_pnl: float
    health_score: float
    last_updated: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class RiskMetricResponse(BaseModel):
    id: int
    portfolio_id: int
    timestamp: datetime
    total_exposure: float
    var_95: float
    max_drawdown: float
    volatility: float
    concentration_risk: float
    correlation_risk: float
    leverage_ratio: float
    risk_score: float
    health_score: float

    model_config = {"from_attributes": True}


class PortfolioDetailResponse(BaseModel):
    id: int
    user_id: int
    total_value: float
    cash_balance: float
    invested_amount: float
    unrealized_pnl: float
    realized_pnl: float
    daily_pnl: float
    weekly_pnl: float
    monthly_pnl: float
    health_score: float
    last_updated: datetime
    created_at: datetime
    summary: Any = None
    positions: List[PositionResponse] = []
    traders: List[TraderResponse] = []
    metrics: Any = None
    model_config = {"from_attributes": True}


class RiskLimitsResponse(BaseModel):
    max_drawdown: float
    max_allocation_per_trader: float
    min_diversification: int
    volatility_exposure_reduction: float
    cooldown_days_after_loss: int


class RiskLimitsUpdate(BaseModel):
    max_drawdown: float | None = Field(None, ge=0.0, le=1.0)
    max_allocation_per_trader: float | None = Field(None, ge=0.0, le=1.0)
    min_diversification: int | None = Field(None, ge=1)
    volatility_exposure_reduction: float | None = Field(None, ge=0.0, le=1.0)
    cooldown_days_after_loss: int | None = Field(None, ge=0)


class AutomationRuleConfig(BaseModel):
    take_profit_target: float | None = None
    partial_profit_percent: float | None = None
    partial_profit_threshold: float | None = None
    rebalance_threshold: float | None = None
    reduce_allocation_threshold: float | None = None
    reduce_allocation_by: float | None = None
    pause_copy_drawdown: float | None = None
    dynamic_exposure_volatility_threshold: float | None = None
    dynamic_exposure_max_allocation: float | None = None

    @classmethod
    def from_json(cls, data: dict) -> "AutomationRuleConfig":
        return cls(**{k: v for k, v in data.items() if v is not None})

    def to_json(self) -> dict:
        return self.model_dump(exclude_none=True)


class AutomationRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    rule_type: str
    enabled: bool = True
    config: dict = {}
    cooldown_days: int = 0


class AutomationRuleUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    config: dict | None = None
    cooldown_days: int | None = None


class AutomationRuleResponse(BaseModel):
    id: int
    portfolio_id: int
    name: str
    rule_type: str
    enabled: bool
    config: dict
    cooldown_days: int
    last_triggered: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AutomationLogResponse(BaseModel):
    id: int
    rule_id: int
    action: str
    status: str
    details: dict
    triggered_at: datetime

    model_config = {"from_attributes": True}


class AlertResponse(BaseModel):
    id: int
    portfolio_id: int
    type: str
    title: str
    message: str
    severity: str
    read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertCreate(BaseModel):
    type: str
    title: str
    message: str
    severity: str = "info"


class AiRecommendationResponse(BaseModel):
    id: int
    portfolio_id: int
    recommendation_type: str
    title: str
    summary: str
    confidence_score: float
    details: dict
    applied: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogResponse(BaseModel):
    id: int
    portfolio_id: int
    action: str
    action_type: str
    details: dict
    ip_address: str
    created_at: datetime

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    app_name: str = "eToro Portfolio Manager"


class PortfolioTimelinePoint(BaseModel):
    date: str
    value: float
    pnl: float


class SyncResponse(BaseModel):
    status: str
    message: str
    positions_synced: int = 0
    traders_synced: int = 0
    duration_ms: float = 0.0


class AnalyzeRequest(BaseModel):
    force: bool = False


class EmergencyStopResponse(BaseModel):
    status: str
    message: str
    actions_taken: List[str] = []


class MessageResponse(BaseModel):
    message: str
    status: str = "success"


class SettingsResponse(BaseModel):
    paper_trading: bool
    etoro_demo_mode: bool = False
    telegram_configured: bool
    etoro_configured: bool
    etoro_public_key_masked: str | None = None
    etoro_user_key_masked: str | None = None
    telegram_bot_token_masked: str | None = None
    telegram_chat_id_masked: str | None = None


class PaperTradingUpdate(BaseModel):
    paper_trading: bool


class EtoroDemoModeUpdate(BaseModel):
    etoro_demo_mode: bool


class EtoroKeysUpdate(BaseModel):
    public_api_key: str | None = None
    user_key: str | None = None


class TelegramConfigUpdate(BaseModel):
    bot_token: str | None = None
    chat_id: str | None = None
