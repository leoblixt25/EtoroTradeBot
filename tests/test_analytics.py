import pytest
import numpy as np
from datetime import datetime, timedelta, timezone

from backend.analytics.calculator import PortfolioCalculator
from backend.analytics.trader_analyzer import TraderAnalyzer
from backend.analytics.risk_scorer import RiskScorer
from backend.analytics.performance import PerformanceAnalyzer


SAMPLE_POSITIONS = [
    {"amount": 10, "current_price": 150.0, "entry_price": 140.0, "instrument_type": "stocks", "instrument_symbol": "AAPL"},
    {"amount": 5, "current_price": 200.0, "entry_price": 210.0, "instrument_type": "stocks", "instrument_symbol": "GOOGL"},
    {"amount": 2, "current_price": 3000.0, "entry_price": 2800.0, "instrument_type": "crypto", "instrument_symbol": "BTC"},
]


@pytest.fixture
def sample_positions():
    return SAMPLE_POSITIONS


@pytest.fixture
def empty_positions():
    return []


@pytest.fixture
def sample_history():
    base = 10000.0
    return [{"date": (datetime.now(timezone.utc) - timedelta(days=i)).isoformat(), "value": base * (1 + 0.01 * (30 - i) / 30)} for i in range(30)]


@pytest.fixture
def sample_returns():
    return [0.01, -0.005, 0.02, 0.015, -0.01, 0.03, -0.008, 0.012, 0.005, -0.003]


@pytest.fixture
def sample_trades():
    return [
        {"pnl": 150.0},
        {"pnl": -50.0},
        {"pnl": 200.0},
        {"pnl": -30.0},
        {"pnl": 80.0},
    ]


@pytest.fixture
def sample_allocations():
    return {"stocks": 60.0, "crypto": 25.0, "etf": 15.0}


# --- PortfolioCalculator Tests ---

class TestCalculateTotalValue:
    def test_returns_sum_of_positions(self, sample_positions):
        result = PortfolioCalculator.calculate_total_value(sample_positions)
        expected = (10 * 150.0) + (5 * 200.0) + (2 * 3000.0)
        assert result == pytest.approx(expected, 0.01)
        assert isinstance(result, float)

    def test_returns_zero_for_empty(self, empty_positions):
        assert PortfolioCalculator.calculate_total_value(empty_positions) == 0.0

    def test_handles_missing_keys(self):
        positions = [{"amount": 5}]
        result = PortfolioCalculator.calculate_total_value(positions)
        assert result == 0.0


class TestCalculateDailyPnl:
    def test_positive_pnl(self, sample_positions):
        result = PortfolioCalculator.calculate_daily_pnl(sample_positions)
        expected_value = (10 * 150 + 5 * 200 + 2 * 3000) - (10 * 140 + 5 * 210 + 2 * 2800)
        assert result["value"] == pytest.approx(expected_value, 0.01)
        assert result["percent"] > 0

    def test_empty_returns_zero(self, empty_positions):
        result = PortfolioCalculator.calculate_daily_pnl(empty_positions)
        assert result["value"] == 0.0
        assert result["percent"] == 0.0

    def test_negative_pnl(self):
        positions = [{"amount": 10, "current_price": 100.0, "entry_price": 150.0}]
        result = PortfolioCalculator.calculate_daily_pnl(positions)
        assert result["value"] < 0

    def test_zero_cost_basis_does_not_divide_by_zero(self):
        positions = [{"amount": 10, "current_price": 100.0, "entry_price": 0.0}]
        result = PortfolioCalculator.calculate_daily_pnl(positions)
        assert result["value"] == 1000.0
        assert isinstance(result["percent"], float)


class TestCalculateMaxDrawdown:
    def test_no_drawdown_for_increasing_values(self):
        history = [{"date": "2024-01-01", "value": 100}, {"date": "2024-01-02", "value": 110}, {"date": "2024-01-03", "value": 120}]
        result = PortfolioCalculator.calculate_max_drawdown(history)
        assert result["percent"] == 0.0
        assert result["value"] == 0.0

    def test_known_drawdown(self):
        history = [{"date": "2024-01-01", "value": 100}, {"date": "2024-01-02", "value": 90}, {"date": "2024-01-03", "value": 80}]
        result = PortfolioCalculator.calculate_max_drawdown(history)
        assert result["percent"] == pytest.approx(20.0, 0.01)
        assert result["value"] == pytest.approx(20.0, 0.01)

    def test_drawdown_with_recovery(self):
        history = [{"date": "2024-01-01", "value": 100}, {"date": "2024-01-02", "value": 80}, {"date": "2024-01-03", "value": 120}]
        result = PortfolioCalculator.calculate_max_drawdown(history)
        assert result["percent"] == pytest.approx(20.0, 0.01)
        assert result["date_from"] == "2024-01-01"
        assert result["date_to"] == "2024-01-02"

    def test_empty_history(self):
        result = PortfolioCalculator.calculate_max_drawdown([])
        assert result["percent"] == 0.0
        assert result["date_from"] is None
        assert result["date_to"] is None


class TestCalculateSharpeRatio:
    def test_positive_sharpe(self, sample_returns):
        result = PortfolioCalculator.calculate_sharpe_ratio(sample_returns)
        assert isinstance(result, float)
        assert result != 0.0

    def test_negative_sharpe_for_negative_returns(self):
        returns = [-0.01, -0.02, -0.015, -0.01]
        result = PortfolioCalculator.calculate_sharpe_ratio(returns)
        assert result < 0

    def test_zero_for_insufficient_data(self):
        assert PortfolioCalculator.calculate_sharpe_ratio([]) == 0.0
        assert PortfolioCalculator.calculate_sharpe_ratio([0.01]) == 0.0

    def test_zero_for_zero_std(self):
        returns = [0.01, 0.01, 0.01]
        result = PortfolioCalculator.calculate_sharpe_ratio(returns)
        assert result == 0.0


class TestCalculateHealthScore:
    def test_perfect_health(self):
        metrics = {"max_drawdown_pct": 0, "volatility": 0, "concentration_risk": 0, "win_rate": 100, "sharpe_ratio": 2, "diversification_count": 10, "correlation_risk": 0}
        assert PortfolioCalculator.calculate_health_score(metrics) == 100

    def test_max_drawdown_penalties(self):
        metrics = {"max_drawdown_pct": 35, "volatility": 0, "concentration_risk": 0, "win_rate": 100, "sharpe_ratio": 2, "diversification_count": 10, "correlation_risk": 0}
        assert PortfolioCalculator.calculate_health_score(metrics) == 70

    def test_all_penalties_applied(self):
        metrics = {"max_drawdown_pct": 35, "volatility": 0.5, "concentration_risk": 0.7, "win_rate": 20, "sharpe_ratio": -0.5, "diversification_count": 1, "correlation_risk": 0.9}
        score = PortfolioCalculator.calculate_health_score(metrics)
        assert 0 <= score <= 100
        assert score < 50

    def test_score_clamped_between_zero_and_hundred(self):
        metrics = {"max_drawdown_pct": 100, "volatility": 1.0, "concentration_risk": 1.0, "win_rate": 0, "sharpe_ratio": -2, "diversification_count": 1, "correlation_risk": 1.0}
        score = PortfolioCalculator.calculate_health_score(metrics)
        assert score == 0


class TestAdditionalCalculators:
    def test_calculate_volatility(self, sample_returns):
        result = PortfolioCalculator.calculate_volatility(sample_returns)
        assert result >= 0
        assert isinstance(result, float)

    def test_calculate_var_95(self, sample_returns):
        result = PortfolioCalculator.calculate_var_95(sample_returns)
        assert result <= 0
        assert isinstance(result, float)

    def test_calculate_win_rate(self, sample_trades):
        result = PortfolioCalculator.calculate_win_rate(sample_trades)
        assert result == pytest.approx(60.0, 0.01)

    def test_calculate_win_rate_empty(self):
        assert PortfolioCalculator.calculate_win_rate([]) == 0.0

    def test_calculate_profit_factor(self):
        assert PortfolioCalculator.calculate_profit_factor(500, 200) == pytest.approx(2.5, 0.01)

    def test_calculate_profit_factor_no_loss(self):
        assert PortfolioCalculator.calculate_profit_factor(500, 0) == float("inf")

    def test_calculate_concentration_risk(self, sample_allocations):
        result = PortfolioCalculator.calculate_concentration_risk(sample_allocations)
        assert 0 <= result <= 1

    def test_calculate_concentration_risk_empty(self):
        assert PortfolioCalculator.calculate_concentration_risk({}) == 0.0

    def test_calculate_allocation_percentages(self, sample_positions):
        result = PortfolioCalculator.calculate_allocation_percentages(sample_positions)
        total = 10 * 150 + 5 * 200 + 2 * 3000
        assert result["stocks"] == pytest.approx((10 * 150 + 5 * 200) / total * 100, 0.01)
        assert result["crypto"] == pytest.approx((2 * 3000) / total * 100, 0.01)

    def test_calculate_allocation_percentages_empty(self, empty_positions):
        assert PortfolioCalculator.calculate_allocation_percentages(empty_positions) == {}

    def test_calculate_unrealized_pnl(self, sample_positions):
        result = PortfolioCalculator.calculate_unrealized_pnl(sample_positions)
        expected = (10 * 150 + 5 * 200 + 2 * 3000) - (10 * 140 + 5 * 210 + 2 * 2800)
        assert result["value"] == pytest.approx(expected, 0.01)

    def test_calculate_realized_pnl(self, sample_trades):
        result = PortfolioCalculator.calculate_realized_pnl(sample_trades)
        assert result == pytest.approx(150 - 50 + 200 - 30 + 80, 0.01)


# --- TraderAnalyzer Tests ---

class TestTraderAnalyzer:
    def test_classify_conservative(self):
        metrics = {"avg_monthly_return": 2.0, "avg_volatility": 5.0, "max_drawdown": 5.0, "avg_win_rate": 70, "trade_frequency": 10}
        assert TraderAnalyzer.classify_trader(metrics) == "conservative"

    def test_classify_balanced(self):
        metrics = {"avg_monthly_return": 5.0, "avg_volatility": 15.0, "max_drawdown": 15.0, "avg_win_rate": 50, "trade_frequency": 30}
        assert TraderAnalyzer.classify_trader(metrics) == "balanced"

    def test_classify_aggressive(self):
        metrics = {"avg_monthly_return": 10.0, "avg_volatility": 25.0, "max_drawdown": 25.0, "avg_win_rate": 40, "trade_frequency": 60}
        assert TraderAnalyzer.classify_trader(metrics) == "aggressive"

    def test_classify_high_risk(self):
        metrics = {"avg_monthly_return": 20.0, "avg_volatility": 40.0, "max_drawdown": 40.0, "avg_win_rate": 30, "trade_frequency": 100}
        assert TraderAnalyzer.classify_trader(metrics) == "high_risk"

    def test_detect_underperformance_high(self):
        recent = [0.01, 0.02, 0.01]
        previous = [0.05, 0.06, 0.07]
        result = TraderAnalyzer.detect_underperformance(recent, previous)
        assert result["is_underperforming"] is True
        assert result["severity"] == "high"

    def test_detect_underperformance_moderate(self):
        recent = [0.04, 0.03, 0.04]
        previous = [0.06, 0.05, 0.05]
        result = TraderAnalyzer.detect_underperformance(recent, previous)
        assert result["is_underperforming"] is True
        assert result["severity"] == "moderate"

    def test_detect_underperformance_low(self):
        recent = [0.045, 0.055, 0.045]
        previous = [0.055, 0.06, 0.05]
        result = TraderAnalyzer.detect_underperformance(recent, previous)
        assert result["is_underperforming"] is True
        assert result["severity"] == "low"

    def test_detect_no_underperformance(self):
        recent = [0.06, 0.07, 0.06]
        previous = [0.05, 0.06, 0.05]
        result = TraderAnalyzer.detect_underperformance(recent, previous)
        assert result["is_underperforming"] is False

    def test_detect_underperformance_no_previous_data(self):
        recent = [0.01, 0.02]
        result = TraderAnalyzer.detect_underperformance(recent, [])
        assert result["is_underperforming"] is False

    def test_detect_underperformance_negative_previous(self):
        recent = [-0.02, -0.03]
        previous = [-0.01, -0.01]
        result = TraderAnalyzer.detect_underperformance(recent, previous)
        assert result["is_underperforming"] is True

    def test_analyze_trader_insufficient_data(self):
        result = TraderAnalyzer.analyze_trader([], {})
        assert result["classification"] == "unknown"
        assert result["classification_reason"] == "insufficient data"

    def test_analyze_trader_valid_data(self):
        history = [{"monthly_return": 0.03, "volatility": 0.15, "max_drawdown": 0.10, "win_rate": 0.65, "risk_score": 20, "trade_count": 10}]
        result = TraderAnalyzer.analyze_trader(history, {"trader_name": "Test Trader"})
        assert result["classification"] != "unknown"
        assert "risk_metrics" in result
        assert "avg_monthly_return" in result["risk_metrics"]

    def test_calculate_sharpe_like_score(self):
        returns = [0.03, 0.02, 0.04, 0.01, 0.05]
        result = TraderAnalyzer.calculate_sharpe_like_score(returns)
        assert isinstance(result, float)
        assert result > 0

    def test_calculate_max_drawdown_from_returns(self):
        returns = [0.01, -0.05, 0.02, -0.03, 0.01]
        result = TraderAnalyzer.calculate_max_drawdown(returns)
        assert result["value"] < 0


# --- RiskScorer Tests ---

class TestRiskScorer:
    def test_calculate_portfolio_risk_score_low(self):
        data = {"allocations": {"stocks": 50, "etf": 30, "bonds": 20}, "volatility": 0.05, "current_drawdown": 0.02, "max_drawdown": 0.05, "health_score": 95}
        score = RiskScorer.calculate_portfolio_risk_score(data)
        assert score <= 20

    def test_calculate_portfolio_risk_score_high(self):
        data = {"allocations": {"crypto": 60, "stocks": 40}, "volatility": 0.5, "current_drawdown": 0.3, "max_drawdown": 0.4, "health_score": 20, "leverage_ratio": 2.5, "correlation_risk": 0.9}
        score = RiskScorer.calculate_portfolio_risk_score(data)
        assert score >= 60

    def test_calculate_portfolio_risk_score_clamped(self):
        data = {"allocations": {"crypto": 100}, "volatility": 1.0, "current_drawdown": 0.5, "max_drawdown": 0.6, "health_score": 10, "leverage_ratio": 5.0, "correlation_risk": 1.0}
        score = RiskScorer.calculate_portfolio_risk_score(data)
        assert score == 100

    def test_get_risk_level_low(self):
        assert RiskScorer.get_risk_level(10) == "low"
        assert RiskScorer.get_risk_level(20) == "low"

    def test_get_risk_level_moderate(self):
        assert RiskScorer.get_risk_level(25) == "moderate"
        assert RiskScorer.get_risk_level(40) == "moderate"

    def test_get_risk_level_elevated(self):
        assert RiskScorer.get_risk_level(45) == "elevated"
        assert RiskScorer.get_risk_level(60) == "elevated"

    def test_get_risk_level_high(self):
        assert RiskScorer.get_risk_level(65) == "high"
        assert RiskScorer.get_risk_level(80) == "high"

    def test_get_risk_level_critical(self):
        assert RiskScorer.get_risk_level(85) == "critical"
        assert RiskScorer.get_risk_level(100) == "critical"

    def test_calculate_volatility_score(self):
        assert RiskScorer.calculate_volatility_score(0.05) == 0
        assert RiskScorer.calculate_volatility_score(0.15) == 5
        assert RiskScorer.calculate_volatility_score(0.25) == 10
        assert RiskScorer.calculate_volatility_score(0.35) == 20
        assert RiskScorer.calculate_volatility_score(0.45) == 30
        assert RiskScorer.calculate_volatility_score(0.6) == 40

    def test_calculate_concentration_score(self):
        assert RiskScorer.calculate_concentration_score({}) == 0
        assert RiskScorer.calculate_concentration_score({"a": 100}) >= 25
        allocs = {"a": 30, "b": 30, "c": 40}
        score = RiskScorer.calculate_concentration_score(allocs)
        assert 0 <= score <= 30

    def test_calculate_drawdown_score(self):
        assert RiskScorer.calculate_drawdown_score(0.05, 0.25) == 3
        assert RiskScorer.calculate_drawdown_score(0.12, 0.25) == 8
        assert RiskScorer.calculate_drawdown_score(0.18, 0.25) == 10
        assert RiskScorer.calculate_drawdown_score(0.25, 0.30) == 25
        assert RiskScorer.calculate_drawdown_score(0.35, 0.40) == 35

    def test_calculate_composite_risk(self):
        result = RiskScorer.calculate_composite_risk(50, 50, 50)
        assert result == 50
        result2 = RiskScorer.calculate_composite_risk(100, 100, 100)
        assert result2 == 100

    def test_calculate_market_risk_score(self):
        data = {"vix": 15, "market_trend": "bullish", "economic_events": [], "sector_risk": "low", "liquidity_risk": "low"}
        assert RiskScorer.calculate_market_risk_score(data) == 0

    def test_calculate_market_risk_score_vix_spike(self):
        data = {"vix": 50, "market_trend": "bearish", "economic_events": [{"impact": "high"}], "sector_risk": "high", "liquidity_risk": "low"}
        score = RiskScorer.calculate_market_risk_score(data)
        assert score > 30

    def test_check_risk_thresholds(self):
        metrics = {"max_drawdown_pct": 0.30, "health_score": 25}
        limits = {"max_drawdown": 0.25, "min_health_score": 30}
        exceeded = RiskScorer.check_risk_thresholds(metrics, limits)
        assert len(exceeded) == 2
        assert any(e["threshold"] == "max_drawdown" for e in exceeded)
        assert any(e["threshold"] == "min_health_score" for e in exceeded)

    def test_get_risk_breakdown(self):
        data = {"allocations": {"a": 50, "b": 50}, "volatility": 0.15, "current_drawdown": 0.08, "max_drawdown": 0.20, "health_score": 80}
        breakdown = RiskScorer.get_risk_breakdown(data)
        assert "components" in breakdown
        assert "total_score" in breakdown
        assert "risk_level" in breakdown
        assert breakdown["total_score"] > 0


# --- PerformanceAnalyzer Tests ---

class TestPerformanceAnalyzer:
    def test_calculate_monthly_returns_basic(self):
        returns = [0.01] * 63
        result = PerformanceAnalyzer.calculate_monthly_returns(returns)
        assert len(result) == 3

    def test_calculate_monthly_returns_empty(self):
        assert PerformanceAnalyzer.calculate_monthly_returns([]) == {}

    def test_calculate_monthly_returns_single_month(self):
        returns = [0.01] * 21
        result = PerformanceAnalyzer.calculate_monthly_returns(returns)
        assert len(result) == 1
        assert result["month_1"] > 0

    def test_calculate_annualized_return(self):
        returns = [0.01] * 252
        result = PerformanceAnalyzer.calculate_annualized_return(returns)
        assert result > 0
        assert isinstance(result, float)

    def test_calculate_annualized_return_empty(self):
        assert PerformanceAnalyzer.calculate_annualized_return([]) == 0.0

    def test_calculate_best_month(self):
        returns = [0.01] * 42
        result = PerformanceAnalyzer.calculate_best_month(returns)
        assert "month" in result
        assert "return" in result

    def test_calculate_best_month_empty(self):
        result = PerformanceAnalyzer.calculate_best_month([])
        assert result["month"] is None
        assert result["return"] == 0.0

    def test_calculate_worst_month(self):
        returns = [-0.01] * 42
        result = PerformanceAnalyzer.calculate_worst_month(returns)
        assert result["return"] < 0

    def test_calculate_percent_positive_months_all_positive(self):
        returns = [0.01] * 63
        result = PerformanceAnalyzer.calculate_percent_positive_months(returns)
        assert result == 100.0

    def test_calculate_percent_positive_months_empty(self):
        assert PerformanceAnalyzer.calculate_percent_positive_months([]) == 0.0

    def test_calculate_ulcer_index(self):
        returns = [0.01, -0.02, 0.015, -0.01, 0.02]
        result = PerformanceAnalyzer.calculate_ulcer_index(returns)
        assert result >= 0

    def test_calculate_ulcer_index_insufficient(self):
        assert PerformanceAnalyzer.calculate_ulcer_index([0.01]) == 0.0

    def test_analyze_performance_no_history(self):
        result = PerformanceAnalyzer.analyze_performance([])
        assert result["error"] == "No history data"

    def test_analyze_performance_with_data(self, sample_history):
        result = PerformanceAnalyzer.analyze_performance(sample_history, period="1m")
        assert "total_return" in result
        assert "monthly_returns" in result
        assert result["period"] == "1m"

    def test_calculate_growth_curve(self):
        values = [100, 110, 105]
        result = PerformanceAnalyzer.calculate_growth_curve(values)
        assert len(result) == 3
        assert result[0]["value"] == 100

    def test_calculate_growth_curve_empty(self):
        assert PerformanceAnalyzer.calculate_growth_curve([]) == []

    def test_calculate_rolling_returns(self):
        returns = [0.01, 0.02, 0.015, 0.01, 0.005, 0.02, 0.015, 0.01, 0.005, 0.02] * 3
        result = PerformanceAnalyzer.calculate_rolling_returns(returns, window=5)
        assert len(result) > 0
        assert all(isinstance(v, float) for v in result)

    def test_calculate_rolling_returns_insufficient_data(self):
        assert PerformanceAnalyzer.calculate_rolling_returns([0.01], window=30) == []

    def test_calculate_rolling_volatility(self):
        returns = [0.01, -0.02, 0.03, -0.01, 0.02] * 10
        result = PerformanceAnalyzer.calculate_rolling_volatility(returns, window=5)
        assert len(result) > 0
        assert all(isinstance(v, float) for v in result)

    def test_generate_performance_summary_positive(self):
        metrics = {"total_return": 5.5, "annualized_return": 12.3, "best_month": {"return": 4.5}, "worst_month": {"return": -2.3}, "percent_positive_months": 65.0, "volatility": 0.15, "ulcer_index": 3.5}
        summary = PerformanceAnalyzer.generate_performance_summary(metrics)
        assert "Positive return" in summary["performance"]
        assert "Moderate volatility" in summary["volatility"]

    def test_generate_performance_summary_negative(self):
        metrics = {"total_return": -5.5, "annualized_return": -8.0, "best_month": {"return": 2.0}, "worst_month": {"return": -5.0}, "percent_positive_months": 40.0, "volatility": 0.25, "ulcer_index": 8.0}
        summary = PerformanceAnalyzer.generate_performance_summary(metrics)
        assert "Negative return" in summary["performance"]
        assert "Elevated volatility" in summary["volatility"]
