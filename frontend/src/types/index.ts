export enum TraderClassification {
  CONSERVATIVE = 'conservative',
  BALANCED = 'balanced',
  AGGRESSIVE = 'aggressive',
  HIGH_RISK = 'high_risk',
}

export interface PortfolioSummary {
  total_value: number;
  cash_balance: number;
  invested_amount: number;
  daily_pnl: number;
  weekly_pnl: number;
  monthly_pnl: number;
  unrealized_pnl: number;
  realized_pnl: number;
  health_score: number;
  total_positions: number;
  total_traders: number;
  active_traders: number;
  diversification_count: number;
  largest_allocation: number;
  day_change_percent: number;
}

export interface Position {
  id: number;
  portfolio_id: number;
  instrument_type: string;
  instrument_symbol: string;
  instrument_name: string;
  amount: number;
  entry_price: number;
  current_price: number;
  allocated_amount: number;
  pnl: number;
  pnl_percent: number;
  allocation_percent: number;
  opened_at: string;
  updated_at: string;
}

export interface CopiedTrader {
  id: number;
  portfolio_id: number;
  trader_name: string;
  trader_id: string;
  allocation_percent: number;
  current_value: number;
  total_pnl: number;
  total_roi: number;
  status: 'active' | 'paused' | 'stopped';
  classification: string;
  copied_at: string;
  last_updated: string;
}

export interface TraderAnalysis {
  trader: CopiedTrader;
  classification: string;
  classification_reason: string;
  risk_metrics: {
    volatility: number;
    max_drawdown: number;
    sharpe_score: number;
    win_rate: number;
    consistency: number;
  };
  ai_summary: string;
  performance_trend: string;
  recommendation: string;
}

export interface RiskMetrics {
  current_risk_score: number;
  current_health_score: number;
  total_exposure: number;
  var_95: number;
  max_drawdown: number;
  volatility: number;
  concentration_risk: number;
  leverage_ratio: number;
  high_risk_traders: number;
  paused_traders: number;
  active_traders: number;
  limits: {
    max_drawdown: number;
    max_allocation_per_trader: number;
    min_diversification: number;
    cooldown_days: number;
  };
}

export interface RiskLimits {
  max_drawdown: number;
  max_allocation_per_trader: number;
  min_diversification: number;
  volatility_exposure_reduction: number;
  cooldown_days_after_loss: number;
}

export interface AutomationRule {
  id: number;
  portfolio_id: number;
  name: string;
  rule_type: string;
  enabled: boolean;
  config: AutomationRuleConfig;
  cooldown_days: number;
  last_triggered: string | null;
  created_at: string;
  updated_at: string;
}

export interface AutomationRuleConfig {
  take_profit_target?: number;
  partial_profit_percent?: number;
  rebalance_threshold?: number;
  reduce_allocation_threshold?: number;
  reduce_allocation_by?: number;
  pause_copy_drawdown?: number;
  dynamic_exposure_volatility_threshold?: number;
  dynamic_exposure_max_allocation?: number;
}

export interface AutomationLog {
  id: number;
  rule_id: number;
  action: string;
  status: string;
  details: Record<string, unknown>;
  triggered_at: string;
}

export interface AiRecommendation {
  id: number;
  portfolio_id: number;
  recommendation_type: string;
  title: string;
  summary: string;
  confidence_score: number;
  details: Record<string, unknown>;
  applied: boolean;
  created_at: string;
}

export interface Alert {
  id: number;
  portfolio_id: number;
  type: string;
  title: string;
  message: string;
  severity: string;
  read: boolean;
  created_at: string;
}

export interface PerformanceData {
  date: string;
  value: number;
  pnl: number;
}

export interface ChartDataPoint {
  label: string;
  value: number;
  color?: string;
}

export interface HealthScoreBreakdown {
  diversification: number;
  risk_management: number;
  returns: number;
  stability: number;
  trader_quality: number;
  overall: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AppSettings {
  paper_trading: boolean;
  telegram_configured: boolean;
  etoro_configured: boolean;
  etoro_public_key_masked: string | null;
  etoro_user_key_masked: string | null;
  telegram_bot_token_masked: string | null;
  telegram_chat_id_masked: string | null;
}
