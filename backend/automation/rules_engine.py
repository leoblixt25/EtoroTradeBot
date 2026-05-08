import structlog
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone

logger = structlog.get_logger(__name__)


class RulesEngine:

    def evaluate_rule(
        self,
        rule: Dict[str, Any],
        portfolio_data: Dict[str, Any],
        market_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        rule_type = rule.get("rule_type", "")
        config = rule.get("config", {})

        evaluators = {
            "take_profit": self.evaluate_take_profit,
            "partial_profit": self.evaluate_partial_profit,
            "rebalance": self.evaluate_rebalance,
            "reduce_allocation": self.evaluate_reduce_allocation,
            "pause_copy": self.evaluate_pause_copy,
            "dynamic_exposure": self.evaluate_dynamic_exposure,
        }

        evaluator = evaluators.get(rule_type)
        if not evaluator:
            return {"triggered": False, "reason": f"Unknown rule type: {rule_type}", "action": {}}

        if not self._check_frequency_limit(rule):
            return {
                "triggered": False,
                "reason": "Frequency limit exceeded for this rule",
                "action": {},
            }

        logs = rule.get("__logs", [])
        if not self._check_cooldown(rule, logs):
            last = logs[-1]["triggered_at"] if logs else "unknown"
            return {
                "triggered": False,
                "reason": f"Cooldown period active since {last}",
                "action": {},
            }

        return evaluator(config, portfolio_data)

    def evaluate_take_profit(self, rule_config: Dict[str, Any], positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        target = rule_config.get("take_profit_target", 0.25)
        triggered_positions = []
        for p in positions:
            pnl_pct = p.get("pnl_percent", 0) / 100.0 if p.get("pnl_percent", 0) > 1 else p.get("pnl_percent", 0)
            if pnl_pct >= target:
                triggered_positions.append(p)
        if triggered_positions:
            names = [p.get("instrument_name", p.get("instrument_symbol", "unknown")) for p in triggered_positions]
            return {
                "triggered": True,
                "reason": f"Take profit target ({target:.0%}) reached for: {', '.join(names)}",
                "action": {
                    "type": "take_profit",
                    "params": {"positions": triggered_positions, "target": target},
                    "details": {"position_count": len(triggered_positions), "positions": names},
                },
            }
        return {"triggered": False, "reason": "No positions at take profit target", "action": {}}

    def evaluate_partial_profit(self, rule_config: Dict[str, Any], positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        threshold = rule_config.get("partial_profit_threshold", 0.15)
        profit_pct = rule_config.get("partial_profit_percent", 0.50)
        triggered = []
        for p in positions:
            pnl_pct = p.get("pnl_percent", 0) / 100.0 if p.get("pnl_percent", 0) > 1 else p.get("pnl_percent", 0)
            if pnl_pct >= threshold:
                triggered.append({
                    "position": p,
                    "pnl_pct": pnl_pct,
                    "lock_amount": p.get("allocated_amount", 0) * profit_pct,
                })
        if triggered:
            details = [f"{t['position'].get('instrument_name', 'unknown')} @ {t['pnl_pct']:.1%} - lock {profit_pct:.0%}" for t in triggered]
            return {
                "triggered": True,
                "reason": f"Partial profit trigger: {len(triggered)} positions above {threshold:.0%} threshold",
                "action": {
                    "type": "partial_profit",
                    "params": {"positions": triggered, "profit_percent": profit_pct},
                    "details": {"triggered": details},
                },
            }
        return {"triggered": False, "reason": "No positions at partial profit threshold", "action": {}}

    def evaluate_rebalance(self, rule_config: Dict[str, Any], portfolio: Dict[str, Any]) -> Dict[str, Any]:
        threshold = rule_config.get("rebalance_threshold", 0.05)
        allocations = portfolio.get("allocations", {})
        target_allocations = rule_config.get("target_allocations", {})
        max_allocation = rule_config.get("max_allocation_per_trader", 0.30)
        issues = []
        for name, pct in allocations.items():
            pct_dec = pct / 100.0 if pct > 1 else pct
            target = target_allocations.get(name, 1.0 / max(len(allocations), 1))
            if abs(pct_dec - target) > threshold:
                issues.append({"instrument": name, "current": round(pct_dec, 3), "target": round(target, 3)})
        for t in portfolio.get("traders", []):
            alloc = t.get("allocation_percent", 0) / 100.0 if t.get("allocation_percent", 0) > 1 else t.get("allocation_percent", 0)
            if alloc > max_allocation:
                issues.append({"trader": t.get("trader_name", "unknown"), "current": round(alloc, 3), "max": max_allocation})
        if issues:
            return {
                "triggered": True,
                "reason": f"Rebalance needed: {len(issues)} allocation deviations detected",
                "action": {
                    "type": "rebalance",
                    "params": {"issues": issues, "threshold": threshold},
                    "details": {"allocation_issues": issues},
                },
            }
        return {"triggered": False, "reason": "Allocations within acceptable range", "action": {}}

    def evaluate_reduce_allocation(self, rule_config: Dict[str, Any], trader: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        threshold = rule_config.get("reduce_allocation_threshold", 0.15)
        reduction = rule_config.get("reduce_allocation_by", 0.50)
        current_dd = metrics.get("max_drawdown", 0)
        dd_dec = current_dd / 100.0 if current_dd > 1 else current_dd
        if dd_dec >= threshold:
            current_alloc = trader.get("allocation_percent", 0)
            new_alloc = current_alloc * (1 - reduction)
            return {
                "triggered": True,
                "reason": f"Trader drawdown ({dd_dec:.1%}) exceeded threshold ({threshold:.0%}). Reducing allocation by {reduction:.0%}.",
                "action": {
                    "type": "reduce_allocation",
                    "params": {
                        "trader_id": trader.get("id"),
                        "reduction_pct": reduction,
                        "current_allocation": current_alloc,
                        "new_allocation": round(new_alloc, 2),
                    },
                    "details": {
                        "trader_name": trader.get("trader_name", "unknown"),
                        "drawdown": dd_dec,
                        "threshold": threshold,
                    },
                },
            }
        return {"triggered": False, "reason": "Trader drawdown within acceptable range", "action": {}}

    def evaluate_pause_copy(self, rule_config: Dict[str, Any], trader: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        dd_threshold = rule_config.get("pause_copy_drawdown", 0.25)
        current_dd = metrics.get("max_drawdown", 0)
        dd_dec = current_dd / 100.0 if current_dd > 1 else current_dd
        if dd_dec >= dd_threshold:
            return {
                "triggered": True,
                "reason": f"Trader drawdown ({dd_dec:.1%}) exceeds pause threshold ({dd_threshold:.0%})",
                "action": {
                    "type": "pause_copy",
                    "params": {"trader_id": trader.get("id")},
                    "details": {
                        "trader_name": trader.get("trader_name", "unknown"),
                        "drawdown": dd_dec,
                        "threshold": dd_threshold,
                    },
                },
            }
        recent = metrics.get("performance_history", [])[-3:] if metrics.get("performance_history") else []
        consecutive_negative = all(r.get("monthly_return", 0) < 0 for r in recent if r.get("monthly_return") is not None)
        if len(recent) >= 3 and consecutive_negative:
            return {
                "triggered": True,
                "reason": "Trader has 3 consecutive negative months",
                "action": {
                    "type": "pause_copy",
                    "params": {"trader_id": trader.get("id")},
                    "details": {"trader_name": trader.get("trader_name", "unknown"), "reason": "three consecutive negative months"},
                },
            }
        return {"triggered": False, "reason": "Trader conditions acceptable", "action": {}}

    def evaluate_dynamic_exposure(self, rule_config: Dict[str, Any], volatility: float, portfolio: Dict[str, Any]) -> Dict[str, Any]:
        vol_threshold = rule_config.get("dynamic_exposure_volatility_threshold", 0.30)
        max_allocation = rule_config.get("dynamic_exposure_max_allocation", 0.20)
        vol_dec = volatility / 100.0 if volatility > 1 else volatility
        if vol_dec > vol_threshold:
            excess = (vol_dec - vol_threshold) / vol_threshold
            reduction = min(0.75, max(0.1, excess * 0.5))
            return {
                "triggered": True,
                "reason": f"Volatility ({vol_dec:.1%}) exceeds threshold ({vol_threshold:.0%}). Reducing exposure by {reduction:.0%}.",
                "action": {
                    "type": "dynamic_exposure",
                    "params": {
                        "reduction_pct": round(reduction, 2),
                        "current_volatility": vol_dec,
                        "threshold": vol_threshold,
                    },
                    "details": {
                        "current_volatility": vol_dec,
                        "threshold": vol_threshold,
                        "reduction": reduction,
                    },
                },
            }
        lower_bound = vol_threshold * 0.5
        if vol_dec < lower_bound:
            return {
                "triggered": True,
                "reason": f"Volatility ({vol_dec:.1%}) below threshold. Opportunity to increase exposure.",
                "action": {
                    "type": "dynamic_exposure",
                    "params": {
                        "reduction_pct": -0.2,
                        "current_volatility": vol_dec,
                        "threshold": vol_threshold,
                    },
                    "details": {
                        "current_volatility": vol_dec,
                        "threshold": vol_threshold,
                        "action": "increase_exposure",
                    },
                },
            }
        return {"triggered": False, "reason": "Volatility within normal range", "action": {}}

    def evaluate_all_rules(
        self,
        portfolio_id: int,
        rules: List[Dict[str, Any]],
        portfolio_data: Dict[str, Any],
        market_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        triggered = []
        for rule in rules:
            if not rule.get("enabled", True):
                continue
            result = self.evaluate_rule(rule, portfolio_data, market_data)
            if result.get("triggered"):
                result["rule_id"] = rule.get("id")
                result["rule_name"] = rule.get("name", "")
                result["portfolio_id"] = portfolio_id
                triggered.append(result)
        triggered.sort(key=lambda r: r.get("action", {}).get("type", ""))
        return triggered

    def _check_frequency_limit(self, rule: Dict[str, Any]) -> bool:
        max_frequency = rule.get("config", {}).get("max_frequency_per_day", 3)
        logs = rule.get("__logs", [])
        today = datetime.now(timezone.utc).date()
        today_count = sum(
            1 for l in logs
            if isinstance(l.get("triggered_at"), datetime) and l["triggered_at"].date() == today
        )
        return today_count < max_frequency

    def _check_cooldown(self, rule: Dict[str, Any], logs: List[Dict[str, Any]]) -> bool:
        cooldown_days = rule.get("cooldown_days", 0)
        if cooldown_days <= 0 or not logs:
            return True
        last = logs[-1]
        last_time = last.get("triggered_at")
        if isinstance(last_time, str):
            last_time = datetime.fromisoformat(last_time)
        if last_time:
            elapsed = (datetime.now(timezone.utc) - last_time).days
            return elapsed >= cooldown_days
        return True
