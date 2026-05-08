import pytest
from datetime import datetime

from backend.risk.manager import RiskManager
from backend.risk.limits import RiskLimits
from backend.risk.emergency import EmergencyProtection


SAMPLE_PORTFOLIO = {
    "total_value": 50000.0,
    "traders": [
        {"trader_name": "Alpha", "allocation_percent": 0.25, "status": "active"},
        {"trader_name": "Beta", "allocation_percent": 0.20, "status": "active"},
        {"trader_name": "Gamma", "allocation_percent": 0.15, "status": "active"},
        {"trader_name": "Delta", "allocation_percent": 0.10, "status": "active"},
    ],
    "positions": [
        {"instrument_type": "stocks", "instrument_symbol": "AAPL", "amount": 10, "current_price": 150.0},
        {"instrument_type": "stocks", "instrument_symbol": "GOOGL", "amount": 5, "current_price": 200.0},
        {"instrument_type": "crypto", "instrument_symbol": "BTC", "amount": 1, "current_price": 30000.0},
        {"instrument_type": "etf", "instrument_symbol": "SPY", "amount": 20, "current_price": 450.0},
        {"instrument_type": "etf", "instrument_symbol": "QQQ", "amount": 15, "current_price": 350.0},
    ],
    "allocations": {"stocks": 40.0, "crypto": 10.0, "etf": 50.0},
    "volatility": 0.15,
    "max_drawdown": 0.12,
    "health_score": 85,
    "invested_amount": 45000.0,
    "correlation_risk": 0.35,
}


@pytest.fixture
def risk_manager():
    return RiskManager()


@pytest.fixture
def sample_portfolio():
    return dict(SAMPLE_PORTFOLIO)


# --- RiskManager Tests ---

class TestCheckPositionSizing:
    def test_approved_small_position(self, risk_manager):
        position = {"allocated_amount": 5000}
        portfolio = {"total_value": 100000}
        result = risk_manager.check_position_sizing(position, portfolio)
        assert result["approved"] is True

    def test_rejected_large_position(self, risk_manager):
        position = {"allocated_amount": 50000}
        portfolio = {"total_value": 100000}
        result = risk_manager.check_position_sizing(position, portfolio)
        assert result["approved"] is False
        assert "exceeds maximum" in result["reason"]

    def test_approaching_limit(self, risk_manager):
        position = {"allocated_amount": 18000}
        portfolio = {"total_value": 100000}
        result = risk_manager.check_position_sizing(position, portfolio)
        assert result["approved"] is True
        assert "approaching" in result["reason"]

    def test_zero_portfolio_value(self, risk_manager):
        position = {"allocated_amount": 5000}
        portfolio = {"total_value": 0}
        result = risk_manager.check_position_sizing(position, portfolio)
        assert result["approved"] is False
        assert "no value" in result["reason"]


class TestEnforceDiversification:
    def test_compliant_portfolio(self, risk_manager, sample_portfolio):
        result = risk_manager.enforce_diversification(sample_portfolio)
        assert result["compliant"] is True
        assert len(result["issues"]) == 0

    def test_few_traders(self, risk_manager):
        portfolio = dict(SAMPLE_PORTFOLIO)
        portfolio["traders"] = [
            {"trader_name": "Alpha", "allocation_percent": 0.50},
            {"trader_name": "Beta", "allocation_percent": 0.50},
        ]
        result = risk_manager.enforce_diversification(portfolio)
        assert result["compliant"] is False
        assert any("Only 2 copied traders" in i for i in result["issues"])

    def test_few_positions(self, risk_manager):
        portfolio = dict(SAMPLE_PORTFOLIO)
        portfolio["positions"] = [
            {"instrument_type": "stocks"},
            {"instrument_type": "stocks"},
        ]
        result = risk_manager.enforce_diversification(portfolio)
        assert result["compliant"] is False

    def test_high_crypto_exposure(self, risk_manager):
        portfolio = dict(SAMPLE_PORTFOLIO)
        portfolio["allocations"] = {"crypto": 50.0, "stocks": 50.0}
        result = risk_manager.enforce_diversification(portfolio)
        assert result["compliant"] is False
        assert any("Crypto" in i for i in result["issues"])

    def test_high_trader_allocation(self, risk_manager):
        portfolio = dict(SAMPLE_PORTFOLIO)
        portfolio["traders"] = [
            {"trader_name": "Alpha", "allocation_percent": 0.50},
            {"trader_name": "Beta", "allocation_percent": 0.25},
            {"trader_name": "Gamma", "allocation_percent": 0.25},
        ]
        result = risk_manager.enforce_diversification(portfolio)
        assert result["compliant"] is False
        assert any("Alpha" in i for i in result["issues"])


class TestCheckLimits:
    def test_passed_all_within_limits(self, risk_manager, sample_portfolio):
        result = risk_manager.check_limits(sample_portfolio)
        assert result["passed"] is True
        assert len(result["violations"]) == 0

    def test_drawdown_exceeded(self, risk_manager):
        portfolio = dict(SAMPLE_PORTFOLIO)
        portfolio["max_drawdown"] = 0.30
        result = risk_manager.check_limits(portfolio)
        assert result["passed"] is False
        violations = [v for v in result["violations"] if v["limit"] == "max_portfolio_drawdown"]
        assert len(violations) == 1

    def test_health_score_below_minimum(self, risk_manager):
        portfolio = dict(SAMPLE_PORTFOLIO)
        portfolio["health_score"] = 20
        result = risk_manager.check_limits(portfolio)
        assert result["passed"] is False
        violations = [v for v in result["violations"] if v["limit"] == "min_health_score"]
        assert len(violations) == 1

    def test_volatility_exceeded(self, risk_manager):
        portfolio = dict(SAMPLE_PORTFOLIO)
        portfolio["volatility"] = 0.50
        result = risk_manager.check_limits(portfolio)
        assert result["passed"] is False


class TestCalculateMaxAllocation:
    def test_high_risk_score(self, risk_manager):
        assert risk_manager.calculate_max_allocation(85) == 0.05
        assert risk_manager.calculate_max_allocation(80) == 0.05

    def test_medium_risk_scores(self, risk_manager):
        assert risk_manager.calculate_max_allocation(70) == 0.10
        assert risk_manager.calculate_max_allocation(60) == 0.10
        assert risk_manager.calculate_max_allocation(50) == 0.15
        assert risk_manager.calculate_max_allocation(40) == 0.15

    def test_low_risk_scores(self, risk_manager):
        assert risk_manager.calculate_max_allocation(30) == 0.25
        assert risk_manager.calculate_max_allocation(20) == 0.25
        assert risk_manager.calculate_max_allocation(10) == 0.30
        assert risk_manager.calculate_max_allocation(0) == 0.30


class TestGetExposureLimits:
    def test_returns_all_limits(self, risk_manager):
        limits = risk_manager.get_exposure_limits()
        assert "max_portfolio_drawdown" in limits
        assert "max_allocation_per_trader" in limits
        assert "max_single_position" in limits
        assert "max_crypto_exposure" in limits
        assert "max_volatility" in limits
        assert "min_health_score" in limits
        assert "max_daily_loss" in limits
        assert "emergency_stop_drawdown" in limits
        assert limits["max_portfolio_drawdown"] == 0.25


class TestAssessPortfolioRisk:
    def test_error_for_missing_portfolio(self, risk_manager):
        mock_service = type("Mock", (), {"get_portfolio_snapshot": lambda self, pid: None})()
        result = risk_manager.assess_portfolio_risk(999, mock_service, None)
        assert result["error"] == "Portfolio not found"


# --- RiskLimits Tests ---

class TestRiskLimits:
    def test_get_all_limits(self):
        limits = RiskLimits.get_all_limits()
        assert limits["max_portfolio_drawdown"] == 0.25
        assert limits["max_allocation_per_trader"] == 0.30
        assert limits["min_diversification"] == 3
        assert limits["max_single_position"] == 0.20
        assert limits["max_volatility"] == 0.40
        assert limits["cooldown_days_after_loss"] == 7

    def test_update_limit_valid(self):
        RiskLimits.reset_defaults()
        assert RiskLimits.update_limit("max_portfolio_drawdown", 0.15) is True
        assert RiskLimits.MAX_PORTFOLIO_DRAWDOWN == 0.15

    def test_update_limit_invalid(self):
        assert RiskLimits.update_limit("nonexistent_limit", 100) is False

    def test_reset_defaults(self):
        RiskLimits.MAX_PORTFOLIO_DRAWDOWN = 0.50
        RiskLimits.reset_defaults()
        assert RiskLimits.MAX_PORTFOLIO_DRAWDOWN == 0.25

    def test_from_dict(self):
        RiskLimits.reset_defaults()
        RiskLimits.from_dict({"max_portfolio_drawdown": 0.10, "min_diversification": 5})
        assert RiskLimits.MAX_PORTFOLIO_DRAWDOWN == 0.10
        assert RiskLimits.MIN_DIVERSIFICATION == 5


# --- EmergencyProtection Tests ---

class TestEmergencyProtection:
    @pytest.fixture
    def emergency(self):
        return EmergencyProtection()

    def test_all_conditions_normal(self, emergency):
        portfolio = {"max_drawdown": 0.05, "health_score": 90, "volatility": 0.10, "daily_loss": 0.01}
        metrics = {"risk_score": 15}
        result = emergency.check_emergency_conditions(portfolio, metrics)
        assert result["emergency"] is False
        assert result["severity"] == 0

    def test_level_4_critical_drawdown(self, emergency):
        portfolio = {"max_drawdown": 0.40, "health_score": 90, "volatility": 0.10, "daily_loss": 0.01}
        metrics = {"risk_score": 30}
        result = emergency.check_emergency_conditions(portfolio, metrics)
        assert result["emergency"] is True
        assert result["severity"] == 4

    def test_level_4_risk_score(self, emergency):
        portfolio = {"max_drawdown": 0.10, "health_score": 80, "volatility": 0.10, "daily_loss": 0.01}
        metrics = {"risk_score": 85}
        result = emergency.check_emergency_conditions(portfolio, metrics)
        assert result["emergency"] is True
        assert result["severity"] == 4

    def test_level_4_health_score(self, emergency):
        portfolio = {"max_drawdown": 0.10, "health_score": 10, "volatility": 0.10, "daily_loss": 0.01}
        metrics = {"risk_score": 30}
        result = emergency.check_emergency_conditions(portfolio, metrics)
        assert result["emergency"] is True
        assert result["severity"] == 4

    def test_level_3_severe_drawdown(self, emergency):
        portfolio = {"max_drawdown": 0.28, "health_score": 80, "volatility": 0.10, "daily_loss": 0.01}
        metrics = {"risk_score": 30}
        result = emergency.check_emergency_conditions(portfolio, metrics)
        assert result["emergency"] is True
        assert result["severity"] == 3

    def test_level_3_daily_loss(self, emergency):
        portfolio = {"max_drawdown": 0.10, "health_score": 80, "volatility": 0.10, "daily_loss": 0.12}
        metrics = {"risk_score": 30}
        result = emergency.check_emergency_conditions(portfolio, metrics)
        assert result["emergency"] is True
        assert result["severity"] == 3

    def test_level_2_moderate_drawdown(self, emergency):
        portfolio = {"max_drawdown": 0.20, "health_score": 80, "volatility": 0.10, "daily_loss": 0.01}
        metrics = {"risk_score": 30}
        result = emergency.check_emergency_conditions(portfolio, metrics)
        assert result["emergency"] is True
        assert result["severity"] == 2

    def test_level_2_high_volatility(self, emergency):
        portfolio = {"max_drawdown": 0.10, "health_score": 80, "volatility": 0.50, "daily_loss": 0.01}
        metrics = {"risk_score": 30}
        result = emergency.check_emergency_conditions(portfolio, metrics)
        assert result["emergency"] is True
        assert result["severity"] == 2

    def test_level_1_daily_loss(self, emergency):
        portfolio = {"max_drawdown": 0.05, "health_score": 80, "volatility": 0.10, "daily_loss": 0.06}
        metrics = {"risk_score": 20}
        result = emergency.check_emergency_conditions(portfolio, metrics)
        assert result["emergency"] is True
        assert result["severity"] == 1

    def test_level_1_drawdown_approaching(self, emergency):
        portfolio = {"max_drawdown": 0.14, "health_score": 80, "volatility": 0.10, "daily_loss": 0.01}
        metrics = {"risk_score": 20}
        result = emergency.check_emergency_conditions(portfolio, metrics)
        assert result["emergency"] is True
        assert result["severity"] == 1

    def test_emergency_protocols_structure(self, emergency):
        protocols = emergency.emergency_protocols()
        assert 1 in protocols
        assert 2 in protocols
        assert 3 in protocols
        assert 4 in protocols
        assert protocols[1]["name"] == "level_1_warning"
        assert protocols[4]["name"] == "level_4_critical"

    def test_get_emergency_actions(self, emergency):
        actions = emergency.get_emergency_actions(1)
        assert len(actions) > 0
        assert all("action" in a and "status" in a for a in actions)

    def test_get_emergency_actions_fallback(self, emergency):
        actions = emergency.get_emergency_actions(99)
        assert len(actions) > 0

    def test_validate_emergency_deactivation(self, emergency):
        assert emergency.validate_emergency_deactivation(1, False) is False
        assert emergency.validate_emergency_deactivation(1, True) is True
