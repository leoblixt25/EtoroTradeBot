import structlog
import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

logger = structlog.get_logger(__name__)


class RiskManager:

    def __init__(self, limits: Optional[Any] = None):
        self.limits = limits

    def assess_portfolio_risk(self, portfolio_id: int, portfolio_service: Any, db: Any) -> Dict[str, Any]:
        portfolio = portfolio_service.get_portfolio_snapshot(portfolio_id)
        if not portfolio:
            return {"error": "Portfolio not found", "risk_level": "unknown", "score": 0}
        from backend.analytics.risk_scorer import RiskScorer
        allocations = portfolio.get("allocations", {})
        volatility = portfolio.get("volatility", 0)
        drawdown = portfolio.get("max_drawdown", 0)
        concentration = RiskScorer.calculate_concentration_score(allocations)
        vol_score = RiskScorer.calculate_volatility_score(volatility)
        dd_score = RiskScorer.calculate_drawdown_score(drawdown, max(drawdown, 0.01))
        health = portfolio.get("health_score", 100)
        health_penalty = max(0, 100 - health) // 5
        total = min(100, vol_score + dd_score + concentration * 3 + health_penalty)
        risk_level = RiskScorer.get_risk_level(total)
        breakdown = RiskScorer.get_risk_breakdown(portfolio)
        return {
            "portfolio_id": portfolio_id,
            "score": total,
            "risk_level": risk_level,
            "breakdown": breakdown,
            "components": {
                "volatility_score": vol_score,
                "drawdown_score": dd_score,
                "concentration_score": concentration,
                "health_penalty": health_penalty,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def check_position_sizing(self, position: Dict[str, Any], portfolio: Dict[str, Any]) -> Dict[str, Any]:
        position_value = float(position.get("allocated_amount", 0))
        portfolio_value = float(portfolio.get("total_value", 1))
        if portfolio_value == 0:
            return {"approved": False, "max_size": 0, "reason": "Portfolio has no value"}
        max_single = portfolio_value * 0.20
        current_pct = position_value / portfolio_value
        if current_pct > 0.20:
            return {
                "approved": False,
                "max_size": round(max_single, 2),
                "reason": f"Position size ({current_pct:.1%}) exceeds maximum 20% of portfolio",
            }
        if current_pct > 0.15:
            return {
                "approved": True,
                "max_size": round(max_single, 2),
                "reason": f"Position size ({current_pct:.1%}) approaching 20% limit",
            }
        return {"approved": True, "max_size": round(max_single, 2), "reason": "Position size acceptable"}

    def enforce_diversification(self, portfolio: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        traders = portfolio.get("traders", [])
        positions = portfolio.get("positions", [])
        allocations = portfolio.get("allocations", {})
        if len(traders) < 3:
            issues.append(f"Only {len(traders)} copied traders (minimum 3 required)")
        if len(positions) < 5:
            issues.append(f"Only {len(positions)} total positions (minimum 5 recommended)")
        instrument_types = set(p.get("instrument_type") for p in positions)
        if len(instrument_types) < 3:
            issues.append(f"Only {len(instrument_types)} instrument types (minimum 3 recommended)")
        crypto = allocations.get("crypto", 0)
        if crypto > 30:
            issues.append(f"Crypto exposure at {crypto:.1f}% exceeds 30% maximum")
        for t in traders:
            alloc = t.get("allocation_percent", 0) / 100.0 if t.get("allocation_percent", 0) > 1 else t.get("allocation_percent", 0)
            if alloc > 0.30:
                issues.append(f"Trader {t.get('trader_name', 'unknown')} allocation at {alloc:.1%} exceeds 30% limit")
        return {
            "compliant": len(issues) == 0,
            "issues": issues,
        }

    def calculate_max_allocation(self, trader_risk_score: int) -> float:
        if trader_risk_score >= 80:
            return 0.05
        if trader_risk_score >= 60:
            return 0.10
        if trader_risk_score >= 40:
            return 0.15
        if trader_risk_score >= 20:
            return 0.25
        return 0.30

    def get_exposure_limits(self) -> Dict[str, float]:
        return {
            "max_portfolio_drawdown": 0.25,
            "max_allocation_per_trader": 0.30,
            "max_single_position": 0.20,
            "max_crypto_exposure": 0.30,
            "max_volatility": 0.40,
            "min_health_score": 30,
            "max_daily_loss": 0.05,
            "emergency_stop_drawdown": 0.35,
        }

    def check_limits(self, portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        violations = []
        dd = abs(portfolio_data.get("max_drawdown", 0))
        if dd > 0.25:
            violations.append({"limit": "max_portfolio_drawdown", "current": round(dd, 3), "max": 0.25, "severity": "critical"})
        for t in portfolio_data.get("traders", []):
            alloc = t.get("allocation_percent", 0) / 100.0 if t.get("allocation_percent", 0) > 1 else t.get("allocation_percent", 0)
            if alloc > 0.30:
                violations.append({"limit": "max_allocation_per_trader", "current": round(alloc, 3), "max": 0.30, "severity": "warning", "trader": t.get("trader_name")})
        volatility = portfolio_data.get("volatility", 0)
        vol_dec = volatility / 100.0 if volatility > 1 else volatility
        if vol_dec > 0.40:
            violations.append({"limit": "max_volatility", "current": round(vol_dec, 3), "max": 0.40, "severity": "critical"})
        health = portfolio_data.get("health_score", 100)
        if health < 30:
            violations.append({"limit": "min_health_score", "current": health, "min": 30, "severity": "critical"})
        crypto = portfolio_data.get("allocations", {}).get("crypto", 0)
        if crypto > 30:
            violations.append({"limit": "max_crypto_exposure", "current": crypto, "max": 30, "severity": "warning"})
        return {"passed": len(violations) == 0, "violations": violations}

    def generate_risk_report(self, portfolio_id: int, portfolio_service: Any, db: Any) -> Dict[str, Any]:
        assessment = self.assess_portfolio_risk(portfolio_id, portfolio_service, db)
        portfolio = portfolio_service.get_portfolio_snapshot(portfolio_id) or {}
        limits_check = self.check_limits(portfolio)
        from backend.analytics.risk_scorer import RiskScorer
        breakdown = RiskScorer.get_risk_breakdown(portfolio)
        return {
            "portfolio_id": portfolio_id,
            "report_date": datetime.now(timezone.utc).isoformat(),
            "risk_assessment": assessment,
            "limits_check": limits_check,
            "breakdown": breakdown,
            "recommendations": self._generate_risk_recommendations(assessment, limits_check),
            "exposure_limits": self.get_exposure_limits(),
        }

    def get_emergency_status(self, portfolio_id: int, db: Any) -> Dict[str, Any]:
        from backend.database.models import Portfolio
        portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if not portfolio:
            return {"active": False, "reason": "Portfolio not found", "since": None}
        return {"active": False, "reason": None, "since": None}

    def update_risk_metrics(self, portfolio_id: int, portfolio_service: Any, db: Any) -> Any:
        from backend.database.models import RiskMetric
        portfolio = portfolio_service.get_portfolio_snapshot(portfolio_id)
        if not portfolio:
            return None
        assessment = self.assess_portfolio_risk(portfolio_id, portfolio_service, db)
        metric = RiskMetric(
            portfolio_id=portfolio_id,
            total_exposure=round(portfolio.get("invested_amount", 0), 2),
            var_95=round(portfolio.get("total_value", 0) * 0.05, 2),
            max_drawdown=round(portfolio.get("max_drawdown", 0), 4),
            volatility=round(portfolio.get("volatility", 0), 4),
            concentration_risk=round(assessment.get("components", {}).get("concentration_score", 0) / 100, 4),
            correlation_risk=round(portfolio.get("correlation_risk", 0), 4),
            leverage_ratio=1.0,
            risk_score=assessment.get("score", 0),
            health_score=portfolio.get("health_score", 100),
        )
        db.add(metric)
        db.commit()
        return metric

    def _generate_risk_recommendations(self, assessment: Dict[str, Any], limits_check: Dict[str, Any]) -> List[Dict[str, str]]:
        recs = []
        if assessment.get("score", 0) > 60:
            recs.append({"action": "reduce_exposure", "reason": "Overall risk score exceeds 60"})
        if assessment.get("components", {}).get("drawdown_score", 0) > 20:
            recs.append({"action": "review_drawdown", "reason": "High drawdown score"})
        if assessment.get("components", {}).get("concentration_score", 0) > 15:
            recs.append({"action": "diversify", "reason": "High concentration risk"})
        if not limits_check.get("passed", True):
            recs.append({"action": "address_violations", "reason": f"{len(limits_check.get('violations', []))} limit violations detected"})
        if not recs:
            recs.append({"action": "maintain", "reason": "All risk metrics within acceptable ranges"})
        return recs
