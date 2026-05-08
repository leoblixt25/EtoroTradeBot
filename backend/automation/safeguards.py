import structlog
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone

logger = structlog.get_logger(__name__)


class Safeguards:

    @staticmethod
    def check_drawdown_limit(portfolio: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        current_dd = portfolio.get("current_drawdown", portfolio.get("max_drawdown", 0))
        max_dd = config.get("max_portfolio_drawdown", 0.25)
        if current_dd >= max_dd:
            return {
                "passed": False,
                "message": f"Portfolio drawdown of {current_dd:.1%} exceeds maximum of {max_dd:.1%}",
                "severity": "critical",
            }
        approaching = max_dd * 0.85
        if current_dd >= approaching:
            return {
                "passed": True,
                "message": f"Drawdown ({current_dd:.1%}) approaching limit ({max_dd:.1%}). Monitoring closely.",
                "severity": "warning",
            }
        return {"passed": True, "message": "Drawdown within acceptable range", "severity": "ok"}

    @staticmethod
    def check_cooldown_period(rule: Dict[str, Any], log: List[Dict[str, Any]]) -> Dict[str, Any]:
        cooldown_days = rule.get("cooldown_days", 0)
        if cooldown_days <= 0 or not log:
            return {"passed": True, "message": "No cooldown restrictions"}
        last_action = log[-1] if log else None
        if not last_action:
            return {"passed": True, "message": "No previous actions logged"}
        last_time = last_action.get("triggered_at") or last_action.get("created_at")
        if isinstance(last_time, str):
            last_time = datetime.fromisoformat(last_time)
        if last_time:
            elapsed = (datetime.now(timezone.utc) - last_time).days
            if elapsed < cooldown_days:
                remaining = cooldown_days - elapsed
                return {
                    "passed": False,
                    "message": f"Cooldown period active. {remaining} days remaining out of {cooldown_days}.",
                    "remaining_days": remaining,
                }
        return {"passed": True, "message": "Cooldown period satisfied"}

    @staticmethod
    def check_market_conditions(market_data: Dict[str, Any]) -> Dict[str, Any]:
        vix = market_data.get("vix", 20)
        trend = market_data.get("market_trend", "neutral")
        if vix > 40 or trend in ("strongly_bearish", "crisis"):
            return {
                "passed": False,
                "message": f"Unfavorable market conditions: VIX={vix}, trend={trend}",
                "severity": "critical",
            }
        if vix > 30 or trend == "bearish":
            return {
                "passed": True,
                "message": f"Cautionary market conditions: VIX={vix}, trend={trend}. Proceeding with extra checks.",
                "severity": "warning",
            }
        return {"passed": True, "message": "Market conditions normal", "severity": "ok"}

    @staticmethod
    def check_portfolio_health(portfolio: Dict[str, Any]) -> Dict[str, Any]:
        health = portfolio.get("health_score", 100)
        if health < 20:
            return {
                "passed": False,
                "message": f"Portfolio health critically low ({health}/100)",
                "severity": "critical",
            }
        if health < 30:
            return {
                "passed": False,
                "message": f"Portfolio health score {health}/100 below minimum threshold",
                "severity": "critical",
            }
        if health < 50:
            return {
                "passed": True,
                "message": f"Portfolio health reduced ({health}/100). Proceeding with caution.",
                "severity": "warning",
            }
        return {"passed": True, "message": f"Portfolio health acceptable ({health}/100)", "severity": "ok"}

    @staticmethod
    def check_consecutive_losses(trader: Dict[str, Any], limit: int = 3) -> Dict[str, Any]:
        performance = trader.get("performance_history", [])
        recent = performance[-limit:] if len(performance) >= limit else performance
        consecutive = 0
        for p in recent:
            monthly_pnl = p.get("monthly_return", 0) or p.get("pnl", 0)
            if monthly_pnl < 0:
                consecutive += 1
            else:
                consecutive = 0
        if consecutive >= limit:
            return {
                "passed": False,
                "message": f"Trader has {consecutive} consecutive losing periods (limit: {limit})",
                "consecutive_losses": consecutive,
                "severity": "critical",
            }
        if consecutive >= max(1, limit - 1):
            return {
                "passed": True,
                "message": f"Trader has {consecutive} consecutive losses, approaching limit of {limit}",
                "consecutive_losses": consecutive,
                "severity": "warning",
            }
        return {"passed": True, "message": "No consecutive loss issue", "severity": "ok"}

    @staticmethod
    def check_volatility_spike(metrics: Dict[str, Any], threshold: float) -> Dict[str, Any]:
        current_vol = metrics.get("current_volatility", metrics.get("volatility", 0))
        historical_vol = metrics.get("historical_volatility", current_vol)
        if historical_vol == 0:
            return {"passed": True, "message": "Insufficient data for volatility comparison"}
        ratio = current_vol / historical_vol if historical_vol > 0 else 1
        if ratio > threshold:
            return {
                "passed": False,
                "message": f"Volatility spike detected: {ratio:.1f}x historical average (threshold: {threshold}x)",
                "ratio": round(ratio, 2),
                "severity": "critical",
            }
        warning_threshold = threshold * 0.8
        if ratio > warning_threshold:
            return {
                "passed": True,
                "message": f"Volatility elevated at {ratio:.1f}x historical average",
                "ratio": round(ratio, 2),
                "severity": "warning",
            }
        return {"passed": True, "message": "Volatility within normal range", "severity": "ok"}

    @staticmethod
    def check_max_daily_actions(action_type: str, log: List[Dict[str, Any]], limit: int = 5) -> Dict[str, Any]:
        today = datetime.now(timezone.utc).date()
        today_actions = [
            entry for entry in log
            if entry.get("action") == action_type and
            (isinstance(entry.get("triggered_at"), datetime) and entry["triggered_at"].date() == today)
        ]
        if len(today_actions) >= limit:
            return {
                "passed": False,
                "message": f"Daily limit of {limit} {action_type} actions reached ({len(today_actions)} today)",
                "count": len(today_actions),
                "severity": "critical",
            }
        return {"passed": True, "message": f"{len(today_actions)}/{limit} daily actions used", "severity": "ok"}

    @staticmethod
    def validate_action(action_type: str, params: Dict[str, Any], portfolio: Dict[str, Any]) -> Dict[str, Any]:
        checks = []
        drawdown_check = Safeguards.check_drawdown_limit(portfolio, params)
        checks.append(("drawdown", drawdown_check))
        health_check = Safeguards.check_portfolio_health(portfolio)
        checks.append(("health", health_check))
        reduction_pct = params.get("reduction_pct", params.get("amount", 0))
        if action_type in ("reduce_allocation", "take_profit", "partial_profit"):
            if reduction_pct > 1.0:
                for name, check in checks:
                    if check["passed"]:
                        check["passed"] = False
                        check["message"] = f"Reduction amount {reduction_pct:.0%} exceeds 100%"
                        check["severity"] = "blocked"
            portfolio_value = portfolio.get("total_value", 0)
            action_value = params.get("value", params.get("amount", 0)) * (params.get("allocation_pct", 1) if isinstance(params.get("allocation_pct"), (int, float)) else 1)
            min_retain = portfolio_value * 0.05
            if portfolio_value - action_value < min_retain:
                check = ("minimum_balance", {"passed": False, "message": "Action would leave insufficient portfolio balance", "severity": "blocked"})
                checks.append(check)

        failed = [c for c in checks if not c[1]["passed"]]
        critical = [c for c in failed if c[1].get("severity") in ("critical", "blocked")]

        if critical:
            return {
                "approved": False,
                "reason": "; ".join(c[1]["message"] for c in critical),
                "overrides": [],
            }
        if failed:
            return {
                "approved": True,
                "reason": "; ".join(c[1]["message"] for c in failed),
                "overrides": [c[0] for c in failed],
            }
        return {"approved": True, "reason": "All checks passed", "overrides": []}

    @staticmethod
    def check_manual_override(rule_id: int) -> bool:
        return False

    @staticmethod
    def emergency_stop_active(portfolio_id: int) -> bool:
        return False

    @staticmethod
    def get_active_restrictions(portfolio_id: int) -> List[str]:
        return []
