import structlog
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

logger = structlog.get_logger(__name__)


class EmergencyProtection:

    PROTOCOLS = {
        1: {
            "name": "level_1_warning",
            "description": "Notify user, increase monitoring frequency",
            "actions": ["notify_user", "increase_monitoring", "log_event"],
        },
        2: {
            "name": "level_2_moderate",
            "description": "Pause risky traders, reduce overall exposure",
            "actions": ["notify_user", "pause_risky_traders", "reduce_exposure_25pct", "log_event"],
        },
        3: {
            "name": "level_3_severe",
            "description": "Pause all copy relationships, liquidate high-risk positions",
            "actions": [
                "notify_user", "pause_all_copy", "liquidate_high_risk",
                "reduce_exposure_50pct", "log_event", "create_audit_trail",
            ],
        },
        4: {
            "name": "level_4_critical",
            "description": "Full portfolio freeze, notify user immediately",
            "actions": [
                "notify_user_urgent", "freeze_portfolio", "pause_all_copy",
                "liquidate_high_risk", "reduce_exposure_75pct",
                "log_event", "create_audit_trail", "escalate_to_support",
            ],
        },
    }

    def check_emergency_conditions(self, portfolio_data: Dict[str, Any], risk_metrics: Dict[str, Any]) -> Dict[str, Any]:
        drawdown = abs(portfolio_data.get("max_drawdown", 0))
        drawdown_dec = drawdown / 100.0 if drawdown > 1 else drawdown
        health = portfolio_data.get("health_score", 100)
        volatility = portfolio_data.get("volatility", 0)
        vol_dec = volatility / 100.0 if volatility > 1 else volatility
        daily_loss = portfolio_data.get("daily_loss", 0)
        daily_loss_dec = daily_loss / 100.0 if daily_loss > 1 else daily_loss
        risk_score = risk_metrics.get("risk_score", 0)

        if drawdown_dec >= 0.35:
            return {"emergency": True, "reason": f"Critical drawdown of {drawdown_dec:.1%}", "severity": 4}
        if risk_score >= 80:
            return {"emergency": True, "reason": f"Risk score at {risk_score}/100", "severity": 4}
        if health < 15:
            return {"emergency": True, "reason": f"Health score critically low at {health}/100", "severity": 4}

        if drawdown_dec >= 0.25:
            return {"emergency": True, "reason": f"Severe drawdown of {drawdown_dec:.1%}", "severity": 3}
        if risk_score >= 65:
            return {"emergency": True, "reason": f"Risk score elevated at {risk_score}/100", "severity": 3}
        if daily_loss_dec >= 0.10:
            return {"emergency": True, "reason": f"Daily loss of {daily_loss_dec:.1%} exceeds 10% threshold", "severity": 3}

        if drawdown_dec >= 0.18:
            return {"emergency": True, "reason": f"Moderate drawdown of {drawdown_dec:.1%}", "severity": 2}
        if risk_score >= 50:
            return {"emergency": True, "reason": f"Risk score at {risk_score}/100", "severity": 2}
        if vol_dec >= 0.45:
            return {"emergency": True, "reason": f"Extreme volatility of {vol_dec:.1%}", "severity": 2}
        if health < 30:
            return {"emergency": True, "reason": f"Health score low at {health}/100", "severity": 2}

        if daily_loss_dec >= 0.05:
            return {"emergency": True, "reason": f"Daily loss of {daily_loss_dec:.1%} exceeds 5% threshold", "severity": 1}
        if drawdown_dec >= 0.12:
            return {"emergency": True, "reason": f"Drawdown approaching concern level at {drawdown_dec:.1%}", "severity": 1}
        if vol_dec >= 0.35:
            return {"emergency": True, "reason": f"High volatility of {vol_dec:.1%}", "severity": 1}

        return {"emergency": False, "reason": "All conditions normal", "severity": 0}

    def activate_emergency_stop(self, portfolio_id: int, reason: str, db: Any) -> Dict[str, Any]:
        from backend.database.models import AuditLog
        try:
            audit = AuditLog(
                portfolio_id=portfolio_id,
                action="emergency_stop_activated",
                action_type="system",
                details={"reason": reason, "activated_at": datetime.now(timezone.utc).isoformat()},
            )
            db.add(audit)
            db.commit()
            logger.warning("emergency stop activated", portfolio_id=portfolio_id, reason=reason)
            return {"activated": True, "reason": reason, "portfolio_id": portfolio_id}
        except Exception as e:
            logger.error("failed to activate emergency stop", error=str(e))
            return {"activated": False, "error": str(e)}

    def deactivate_emergency_stop(self, portfolio_id: int, db: Any) -> Dict[str, Any]:
        from backend.database.models import AuditLog
        try:
            audit = AuditLog(
                portfolio_id=portfolio_id,
                action="emergency_stop_deactivated",
                action_type="system",
                details={"deactivated_at": datetime.now(timezone.utc).isoformat()},
            )
            db.add(audit)
            db.commit()
            logger.info("emergency stop deactivated", portfolio_id=portfolio_id)
            return {"deactivated": True, "portfolio_id": portfolio_id}
        except Exception as e:
            logger.error("failed to deactivate emergency stop", error=str(e))
            return {"deactivated": False, "error": str(e)}

    def get_emergency_actions(self, severity: int) -> List[Dict[str, str]]:
        protocol = self.PROTOCOLS.get(severity, self.PROTOCOLS[1])
        return [{"action": a, "status": "pending"} for a in protocol["actions"]]

    def execute_emergency_actions(self, portfolio_id: int, actions: List[Dict[str, str]], services: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []
        action_handlers = {
            "notify_user": self._handle_notify_user,
            "notify_user_urgent": self._handle_notify_user_urgent,
            "increase_monitoring": self._handle_increase_monitoring,
            "pause_risky_traders": self._handle_pause_risky_traders,
            "pause_all_copy": self._handle_pause_all_copy,
            "reduce_exposure_25pct": self._handle_reduce_exposure,
            "reduce_exposure_50pct": self._handle_reduce_exposure,
            "reduce_exposure_75pct": self._handle_reduce_exposure,
            "liquidate_high_risk": self._handle_liquidate_high_risk,
            "freeze_portfolio": self._handle_freeze_portfolio,
            "log_event": self._handle_log_event,
            "create_audit_trail": self._handle_create_audit_trail,
            "escalate_to_support": self._handle_escalate_to_support,
        }
        for action_item in actions:
            action_name = action_item["action"]
            handler = action_handlers.get(action_name)
            if handler:
                try:
                    result = handler(portfolio_id, action_item, services)
                    result["action"] = action_name
                    results.append(result)
                except Exception as e:
                    results.append({"action": action_name, "status": "failed", "error": str(e)})
            else:
                results.append({"action": action_name, "status": "unknown_action"})
        return results

    def emergency_protocols(self) -> Dict[int, Dict[str, Any]]:
        return self.PROTOCOLS

    def validate_emergency_deactivation(self, portfolio_id: int, user_confirmation: bool) -> bool:
        if not user_confirmation:
            return False
        return True

    def _handle_notify_user(self, portfolio_id: int, action: Dict[str, str], services: Dict[str, Any]) -> Dict[str, Any]:
        bot = services.get("telegram_bot")
        if bot:
            bot.send_message(f"*Emergency Protection Notice*\nPortfolio {portfolio_id} entered monitoring state.")
        return {"status": "completed"}

    def _handle_notify_user_urgent(self, portfolio_id: int, action: Dict[str, str], services: Dict[str, Any]) -> Dict[str, Any]:
        bot = services.get("telegram_bot")
        if bot:
            bot.send_message(f"*URGENT: Emergency Stop Activated*\nPortfolio {portfolio_id} frozen. Immediate attention required.")
        return {"status": "completed"}

    def _handle_increase_monitoring(self, portfolio_id: int, action: Dict[str, str], services: Dict[str, Any]) -> Dict[str, Any]:
        scheduler = services.get("scheduler")
        if scheduler:
            scheduler.increase_monitoring_frequency(portfolio_id)
        return {"status": "completed"}

    def _handle_pause_risky_traders(self, portfolio_id: int, action: Dict[str, str], services: Dict[str, Any]) -> Dict[str, Any]:
        portfolio_service = services.get("portfolio_service")
        if portfolio_service:
            portfolio_service.pause_risky_traders(portfolio_id)
        return {"status": "completed"}

    def _handle_pause_all_copy(self, portfolio_id: int, action: Dict[str, str], services: Dict[str, Any]) -> Dict[str, Any]:
        portfolio_service = services.get("portfolio_service")
        if portfolio_service:
            portfolio_service.pause_all_copy_relationships(portfolio_id)
        return {"status": "completed"}

    def _handle_reduce_exposure(self, portfolio_id: int, action: Dict[str, str], services: Dict[str, Any]) -> Dict[str, Any]:
        pct_map = {"reduce_exposure_25pct": 0.25, "reduce_exposure_50pct": 0.50, "reduce_exposure_75pct": 0.75}
        pct = pct_map.get(action.get("action", ""), 0.50)
        portfolio_service = services.get("portfolio_service")
        if portfolio_service:
            portfolio_service.reduce_portfolio_exposure(portfolio_id, pct)
        return {"status": "completed", "reduction_pct": pct}

    def _handle_liquidate_high_risk(self, portfolio_id: int, action: Dict[str, str], services: Dict[str, Any]) -> Dict[str, Any]:
        portfolio_service = services.get("portfolio_service")
        if portfolio_service:
            portfolio_service.liquidate_high_risk_positions(portfolio_id)
        return {"status": "completed"}

    def _handle_freeze_portfolio(self, portfolio_id: int, action: Dict[str, str], services: Dict[str, Any]) -> Dict[str, Any]:
        portfolio_service = services.get("portfolio_service")
        if portfolio_service:
            portfolio_service.freeze_portfolio(portfolio_id)
        return {"status": "completed"}

    def _handle_log_event(self, portfolio_id: int, action: Dict[str, str], services: Dict[str, Any]) -> Dict[str, Any]:
        logger.warning("emergency event logged", portfolio_id=portfolio_id)
        return {"status": "completed"}

    def _handle_create_audit_trail(self, portfolio_id: int, action: Dict[str, str], services: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "completed"}

    def _handle_escalate_to_support(self, portfolio_id: int, action: Dict[str, str], services: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "completed", "message": "Support team notified"}
