import structlog
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

logger = structlog.get_logger(__name__)


class AutomationExecutor:

    def execute_action(
        self,
        action: Dict[str, Any],
        rule: Dict[str, Any],
        portfolio_id: int,
        services: Dict[str, Any],
        db: Any,
    ) -> Dict[str, Any]:
        action_type = action.get("type", "")
        params = action.get("params", {})
        executors = {
            "take_profit": self.execute_take_profit,
            "partial_profit": self.execute_partial_profit_lock,
            "rebalance": self.execute_rebalance,
            "reduce_allocation": self.execute_reduce_allocation,
            "pause_copy": self.execute_pause_copy,
            "dynamic_exposure": self.execute_dynamic_exposure_reduction,
        }
        executor = executors.get(action_type)
        if not executor:
            log = self._log_action(rule.get("id"), action_type, "failed", {"error": f"Unknown action type: {action_type}"})
            return log

        try:
            result = executor(params, services)
            log = self._log_action(
                rule.get("id"), action_type, "completed" if result.get("success") else "failed", result
            )
            return log
        except Exception as e:
            logger.exception("action execution failed", action_type=action_type, error=str(e))
            return self._log_action(rule.get("id"), action_type, "failed", {"error": str(e)})

    def execute_take_profit(self, params: Dict[str, Any], portfolio_service: Any) -> Dict[str, Any]:
        positions = params.get("positions", [])
        target = params.get("target", 0.25)
        results = []
        for p in positions:
            try:
                result = portfolio_service.close_position(p.get("id"))
                results.append({
                    "position_id": p.get("id"),
                    "symbol": p.get("instrument_symbol", "unknown"),
                    "status": "closed",
                    "pnl_realized": p.get("pnl", 0),
                })
            except Exception as e:
                results.append({
                    "position_id": p.get("id"),
                    "symbol": p.get("instrument_symbol", "unknown"),
                    "status": "failed",
                    "error": str(e),
                })
        success_count = sum(1 for r in results if r["status"] == "closed")
        return {
            "success": success_count > 0,
            "action": "take_profit",
            "positions_processed": len(results),
            "positions_closed": success_count,
            "details": {"target": target, "results": results},
        }

    def execute_partial_profit_lock(self, params: Dict[str, Any], portfolio_service: Any) -> Dict[str, Any]:
        positions = params.get("positions", [])
        profit_percent = params.get("profit_percent", 0.50)
        results = []
        for item in positions:
            position = item.get("position", {})
            lock_amount = item.get("lock_amount", 0)
            try:
                result = portfolio_service.sell_position_partial(position.get("id"), lock_amount)
                results.append({
                    "position_id": position.get("id"),
                    "symbol": position.get("instrument_symbol", "unknown"),
                    "locked_amount": lock_amount,
                    "status": "partial_sold",
                })
            except Exception as e:
                results.append({
                    "position_id": position.get("id"),
                    "symbol": position.get("instrument_symbol", "unknown"),
                    "status": "failed",
                    "error": str(e),
                })
        success_count = sum(1 for r in results if r["status"] == "partial_sold")
        return {
            "success": success_count > 0,
            "action": "partial_profit",
            "positions_processed": len(results),
            "positions_partial": success_count,
            "details": {"profit_percent": profit_percent, "results": results},
        }

    def execute_rebalance(self, params: Dict[str, Any], portfolio_service: Any) -> Dict[str, Any]:
        issues = params.get("issues", [])
        adjustments = []
        for issue in issues:
            instrument = issue.get("instrument") or issue.get("trader", "unknown")
            current = issue.get("current", 0)
            target = issue.get("target") or issue.get("max", 0)
            diff = target - current
            adjustments.append({
                "instrument": instrument,
                "current_allocation": current,
                "target_allocation": target,
                "adjustment": round(diff, 4),
            })
        return {
            "success": True,
            "action": "rebalance",
            "adjustments_made": len(adjustments),
            "details": {"threshold": params.get("threshold", 0.05), "adjustments": adjustments},
        }

    def execute_reduce_allocation(self, params: Dict[str, Any], portfolio_service: Any) -> Dict[str, Any]:
        trader_id = params.get("trader_id")
        reduction_pct = params.get("reduction_pct", 0.50)
        try:
            result = portfolio_service.update_trader_allocation(trader_id, reduction_pct)
            return {
                "success": True,
                "action": "reduce_allocation",
                "details": {
                    "trader_id": trader_id,
                    "reduction_pct": reduction_pct,
                    "new_allocation": params.get("new_allocation"),
                },
            }
        except Exception as e:
            return {
                "success": False,
                "action": "reduce_allocation",
                "error": str(e),
                "details": {"trader_id": trader_id, "reduction_pct": reduction_pct},
            }

    def execute_pause_copy(self, params: Dict[str, Any], portfolio_service: Any) -> Dict[str, Any]:
        trader_id = params.get("trader_id")
        try:
            result = portfolio_service.pause_trader(trader_id)
            return {
                "success": True,
                "action": "pause_copy",
                "details": {
                    "trader_id": trader_id,
                    "trader_name": params.get("details", {}).get("trader_name", "unknown"),
                },
            }
        except Exception as e:
            return {
                "success": False,
                "action": "pause_copy",
                "error": str(e),
                "details": {"trader_id": trader_id},
            }

    def execute_dynamic_exposure_reduction(self, params: Dict[str, Any], portfolio_service: Any) -> Dict[str, Any]:
        reduction_pct = abs(params.get("reduction_pct", 0.1))
        try:
            result = portfolio_service.reduce_portfolio_exposure(reduction_pct)
            return {
                "success": True,
                "action": "dynamic_exposure",
                "details": {
                    "reduction_pct": reduction_pct,
                    "reason": params.get("details", {}).get("action", "volatility_management"),
                    "prev_exposure": result.get("prev_exposure"),
                    "new_exposure": result.get("new_exposure"),
                },
            }
        except Exception as e:
            return {
                "success": False,
                "action": "dynamic_exposure",
                "error": str(e),
                "details": {"reduction_pct": reduction_pct},
            }

    def _log_action(self, rule_id: int, action: str, status: str, details: Dict[str, Any]) -> Dict[str, Any]:
        from backend.database.models import AutomationLog
        try:
            log_entry = AutomationLog(
                rule_id=rule_id,
                action=action,
                status=status,
                details=details,
            )
            db = details.pop("__db", None)
            if db:
                db.add(log_entry)
                db.commit()
        except Exception as e:
            logger.warning("failed to persist automation log", error=str(e))
        return {
            "rule_id": rule_id,
            "action": action,
            "status": status,
            "details": details,
            "triggered_at": datetime.now(timezone.utc).isoformat(),
        }

    def _notify_action(self, action: Dict[str, Any], telegram_bot: Any) -> Dict[str, Any]:
        if not telegram_bot:
            return {"sent": False, "reason": "No telegram bot configured"}
        try:
            message = (
                f"*Automation Action Executed*\n"
                f"Type: {action.get('action', 'unknown')}\n"
                f"Status: {action.get('status', 'unknown')}\n"
            )
            details = action.get("details", {})
            if details:
                message += f"Details: {str(details)[:200]}"
            telegram_bot.send_message(message)
            return {"sent": True}
        except Exception as e:
            logger.warning("failed to send notification", error=str(e))
            return {"sent": False, "reason": str(e)}

    def _create_audit_entry(self, action: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
        from backend.database.models import AuditLog
        try:
            entry = AuditLog(
                portfolio_id=details.get("portfolio_id", 0),
                action=action.get("action", "automation_action"),
                action_type="automation",
                details=details,
            )
            db = details.pop("__db", None)
            if db:
                db.add(entry)
                db.commit()
            return {"created": True, "action": action.get("action")}
        except Exception as e:
            logger.warning("failed to create audit entry", error=str(e))
            return {"created": False, "error": str(e)}

    def manual_override_action(self, action_id: int) -> bool:
        return True
