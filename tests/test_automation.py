import pytest
import structlog
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from backend.automation.safeguards import Safeguards
from backend.automation.rules_engine import RulesEngine
from backend.automation.executor import AutomationExecutor


@pytest.fixture
def sample_portfolio():
    return {
        "total_value": 100000.0,
        "current_drawdown": 0.08,
        "max_drawdown": 0.12,
        "health_score": 80,
        "allocations": {"trader_a": 30.0, "trader_b": 25.0, "trader_c": 20.0, "trader_d": 15.0, "trader_e": 10.0},
        "traders": [
            {"id": 1, "trader_name": "Trader A", "allocation_percent": 0.30, "status": "active"},
            {"id": 2, "trader_name": "Trader B", "allocation_percent": 0.25, "status": "active"},
        ],
    }


@pytest.fixture
def sample_config():
    return {"max_portfolio_drawdown": 0.25}


@pytest.fixture
def sample_rule():
    return {
        "id": 1,
        "name": "Take Profit AAPL",
        "rule_type": "take_profit",
        "enabled": True,
        "cooldown_days": 7,
        "config": {"take_profit_target": 0.25},
        "__logs": [],
    }


# --- Safeguards Tests ---

class TestCheckDrawdownLimit:
    def test_within_limit(self, sample_portfolio, sample_config):
        result = Safeguards.check_drawdown_limit(sample_portfolio, sample_config)
        assert result["passed"] is True
        assert result["severity"] == "ok"

    def test_exceeds_limit(self):
        portfolio = {"current_drawdown": 0.30}
        config = {"max_portfolio_drawdown": 0.25}
        result = Safeguards.check_drawdown_limit(portfolio, config)
        assert result["passed"] is False
        assert result["severity"] == "critical"

    def test_approaching_limit(self):
        portfolio = {"current_drawdown": 0.22}
        config = {"max_portfolio_drawdown": 0.25}
        result = Safeguards.check_drawdown_limit(portfolio, config)
        assert result["passed"] is True
        assert result["severity"] == "warning"

    def test_uses_max_drawdown_fallback(self):
        portfolio = {"max_drawdown": 0.30}
        config = {"max_portfolio_drawdown": 0.25}
        result = Safeguards.check_drawdown_limit(portfolio, config)
        assert result["passed"] is False


class TestCheckCooldownPeriod:
    def test_no_cooldown_needed(self):
        rule = {"cooldown_days": 0}
        result = Safeguards.check_cooldown_period(rule, [])
        assert result["passed"] is True

    def test_cooldown_active(self):
        rule = {"cooldown_days": 7}
        log = [{"triggered_at": datetime.now(timezone.utc) - timedelta(days=2)}]
        result = Safeguards.check_cooldown_period(rule, log)
        assert result["passed"] is False
        assert "remaining_days" in result
        assert result["remaining_days"] > 0

    def test_cooldown_expired(self):
        rule = {"cooldown_days": 7}
        log = [{"triggered_at": datetime.now(timezone.utc) - timedelta(days=10)}]
        result = Safeguards.check_cooldown_period(rule, log)
        assert result["passed"] is True

    def test_no_logs(self):
        rule = {"cooldown_days": 7}
        result = Safeguards.check_cooldown_period(rule, [])
        assert result["passed"] is True

    def test_empty_log_entry(self):
        rule = {"cooldown_days": 7}
        log = [{}]
        result = Safeguards.check_cooldown_period(rule, log)
        assert result["passed"] is True

    def test_string_date_parsing(self):
        rule = {"cooldown_days": 7}
        log = [{"triggered_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()}]
        result = Safeguards.check_cooldown_period(rule, log)
        assert result["passed"] is False


class TestCheckMarketConditions:
    def test_normal_market(self):
        data = {"vix": 15, "market_trend": "bullish"}
        result = Safeguards.check_market_conditions(data)
        assert result["passed"] is True
        assert result["severity"] == "ok"

    def test_cautionary_market(self):
        data = {"vix": 35, "market_trend": "bearish"}
        result = Safeguards.check_market_conditions(data)
        assert result["passed"] is True
        assert result["severity"] == "warning"

    def test_unfavorable_market(self):
        data = {"vix": 50, "market_trend": "strongly_bearish"}
        result = Safeguards.check_market_conditions(data)
        assert result["passed"] is False
        assert result["severity"] == "critical"

    def test_crisis_trend(self):
        data = {"vix": 25, "market_trend": "crisis"}
        result = Safeguards.check_market_conditions(data)
        assert result["passed"] is False


class TestCheckPortfolioHealth:
    def test_healthy_portfolio(self):
        portfolio = {"health_score": 90}
        result = Safeguards.check_portfolio_health(portfolio)
        assert result["passed"] is True
        assert result["severity"] == "ok"

    def test_critical_health(self):
        portfolio = {"health_score": 15}
        result = Safeguards.check_portfolio_health(portfolio)
        assert result["passed"] is False
        assert result["severity"] == "critical"

    def test_below_minimum(self):
        portfolio = {"health_score": 25}
        result = Safeguards.check_portfolio_health(portfolio)
        assert result["passed"] is False
        assert result["severity"] == "critical"

    def test_reduced_health(self):
        portfolio = {"health_score": 40}
        result = Safeguards.check_portfolio_health(portfolio)
        assert result["passed"] is True
        assert result["severity"] == "warning"


class TestValidateAction:
    def test_approved_all_checks_pass(self, sample_portfolio):
        result = Safeguards.validate_action("reduce_allocation", {"reduction_pct": 0.1}, sample_portfolio)
        assert result["approved"] is True

    def test_blocked_bad_action(self, sample_portfolio):
        result = Safeguards.validate_action("reduce_allocation", {"reduction_pct": 1.5}, sample_portfolio)
        assert result["approved"] is False

    def test_insufficient_balance(self):
        portfolio = {"total_value": 100, "health_score": 90, "current_drawdown": 0.05}
        result = Safeguards.validate_action("take_profit", {"value": 99, "reduction_pct": 0.99}, portfolio)
        assert result["approved"] is False


class TestCheckConsecutiveLosses:
    def test_no_loss_issue(self):
        trader = {"performance_history": [{"monthly_return": 0.05}, {"monthly_return": 0.03}, {"monthly_return": 0.02}]}
        result = Safeguards.check_consecutive_losses(trader, limit=3)
        assert result["passed"] is True
        assert result["severity"] == "ok"

    def test_consecutive_losses_detected(self):
        trader = {"performance_history": [{"monthly_return": -0.05}, {"monthly_return": -0.03}, {"monthly_return": -0.02}]}
        result = Safeguards.check_consecutive_losses(trader, limit=3)
        assert result["passed"] is False
        assert result["severity"] == "critical"

    def test_approaching_limit(self):
        trader = {"performance_history": [{"monthly_return": 0.05}, {"monthly_return": -0.03}, {"monthly_return": -0.02}]}
        result = Safeguards.check_consecutive_losses(trader, limit=3)
        assert result["passed"] is True
        assert result["severity"] == "warning"


class TestCheckVolatilitySpike:
    def test_normal_volatility(self):
        metrics = {"current_volatility": 0.15, "historical_volatility": 0.18}
        result = Safeguards.check_volatility_spike(metrics, threshold=3.0)
        assert result["passed"] is True
        assert result["severity"] == "ok"

    def test_volatility_spike_detected(self):
        metrics = {"current_volatility": 0.60, "historical_volatility": 0.15}
        result = Safeguards.check_volatility_spike(metrics, threshold=3.0)
        assert result["passed"] is False
        assert result["severity"] == "critical"

    def test_elevated_volatility(self):
        metrics = {"current_volatility": 0.45, "historical_volatility": 0.18}
        result = Safeguards.check_volatility_spike(metrics, threshold=3.0)
        assert result["passed"] is True
        assert result["severity"] == "warning"

    def test_insufficient_data(self):
        metrics = {"current_volatility": 0.15, "historical_volatility": 0}
        result = Safeguards.check_volatility_spike(metrics, threshold=3.0)
        assert result["passed"] is True


# --- RulesEngine Tests ---

class TestEvaluateTakeProfit:
    @pytest.fixture
    def engine(self):
        return RulesEngine()

    def test_triggers_when_target_reached(self, engine):
        config = {"take_profit_target": 0.25}
        positions = [
            {"instrument_name": "AAPL", "pnl_percent": 0.30},
            {"instrument_name": "GOOGL", "pnl_percent": 0.10},
        ]
        result = engine.evaluate_take_profit(config, positions)
        assert result["triggered"] is True
        assert "AAPL" in result["reason"]
        assert result["action"]["details"]["position_count"] == 1

    def test_no_trigger_below_target(self, engine):
        config = {"take_profit_target": 0.25}
        positions = [{"instrument_name": "AAPL", "pnl_percent": 0.10}]
        result = engine.evaluate_take_profit(config, positions)
        assert result["triggered"] is False

    def test_no_positions(self, engine):
        result = engine.evaluate_take_profit({"take_profit_target": 0.25}, [])
        assert result["triggered"] is False


class TestEvaluatePauseCopy:
    @pytest.fixture
    def engine(self):
        return RulesEngine()

    def test_pause_on_high_drawdown(self, engine):
        config = {"pause_copy_drawdown": 0.25}
        trader = {"id": 1, "trader_name": "Trader A"}
        metrics = {"max_drawdown": 0.30}
        result = engine.evaluate_pause_copy(config, trader, metrics)
        assert result["triggered"] is True
        assert result["action"]["type"] == "pause_copy"

    def test_pause_on_consecutive_negative(self, engine):
        config = {"pause_copy_drawdown": 0.25}
        trader = {"id": 1, "trader_name": "Trader B"}
        metrics = {
            "max_drawdown": 0.10,
            "performance_history": [
                {"monthly_return": -0.05},
                {"monthly_return": -0.03},
                {"monthly_return": -0.02},
            ],
        }
        result = engine.evaluate_pause_copy(config, trader, metrics)
        assert result["triggered"] is True
        assert "consecutive negative months" in result["reason"]

    def test_no_pause_acceptable(self, engine):
        config = {"pause_copy_drawdown": 0.25}
        trader = {"id": 1, "trader_name": "Trader C"}
        metrics = {"max_drawdown": 0.10, "performance_history": []}
        result = engine.evaluate_pause_copy(config, trader, metrics)
        assert result["triggered"] is False

    def test_pnl_percent_greater_than_1_handled(self, engine):
        config = {"take_profit_target": 0.25}
        positions = [{"instrument_name": "AAPL", "pnl_percent": 30.0}]
        result = engine.evaluate_take_profit(config, positions)
        assert result["triggered"] is True


class TestEvaluateDynamicExposure:
    @pytest.fixture
    def engine(self):
        return RulesEngine()

    def test_reduce_exposure_on_high_volatility(self, engine):
        config = {"dynamic_exposure_volatility_threshold": 0.30}
        portfolio = {"total_value": 50000}
        result = engine.evaluate_dynamic_exposure(config, 0.50, portfolio)
        assert result["triggered"] is True
        assert result["action"]["type"] == "dynamic_exposure"
        assert result["action"]["params"]["reduction_pct"] > 0

    def test_increase_exposure_on_low_volatility(self, engine):
        config = {"dynamic_exposure_volatility_threshold": 0.30}
        portfolio = {"total_value": 50000}
        result = engine.evaluate_dynamic_exposure(config, 0.10, portfolio)
        assert result["triggered"] is True
        assert result["action"]["params"]["reduction_pct"] < 0

    def test_no_change_normal_volatility(self, engine):
        config = {"dynamic_exposure_volatility_threshold": 0.30}
        portfolio = {"total_value": 50000}
        result = engine.evaluate_dynamic_exposure(config, 0.18, portfolio)
        assert result["triggered"] is False


class TestEvaluateRuleDispatch:
    @pytest.fixture
    def engine(self):
        return RulesEngine()

    def test_unknown_rule_type(self, engine):
        result = engine.evaluate_rule({"rule_type": "invalid_type", "config": {}, "cooldown_days": 0, "__logs": []}, {}, {})
        assert result["triggered"] is False
        assert "Unknown rule type" in result["reason"]

    def test_disabled_rule_not_evaluated(self, engine):
        result = engine.evaluate_all_rules(1, [{"rule_type": "take_profit", "enabled": False, "config": {}, "id": 1, "name": "test", "cooldown_days": 0, "__logs": []}], {}, {})
        assert len(result) == 0


# --- AutomationExecutor Tests ---

class TestExecuteAction:
    @pytest.fixture
    def executor(self):
        return AutomationExecutor()

    def test_unknown_action_type(self, executor):
        action = {"type": "unknown_action", "params": {}}
        rule = {"id": 1}
        result = executor.execute_action(action, rule, 1, {}, None)
        assert result["action"] == "unknown_action"
        assert result["status"] == "failed"

    def test_take_profit_execution_fails_gracefully(self, executor):
        action = {"type": "take_profit", "params": {"positions": [{"id": 1, "instrument_symbol": "AAPL", "pnl": 100}], "target": 0.25}}
        rule = {"id": 1}
        result = executor.execute_action(action, rule, 1, {}, None)
        assert result["rule_id"] == 1
        assert result["action"] == "take_profit"
        assert result["status"] == "failed"
        assert "details" in result

    def test_execute_action_logs(self, executor):
        action = {"type": "take_profit", "params": {"positions": [{"id": 1}], "target": 0.25}}
        rule = {"id": 1}
        mock_services = MagicMock()
        result = executor.execute_action(action, rule, 1, {"portfolio_service": mock_services}, None)
        assert result["rule_id"] == 1
        assert result["action"] in ("take_profit",)
        assert result["status"] in ("completed", "failed")
