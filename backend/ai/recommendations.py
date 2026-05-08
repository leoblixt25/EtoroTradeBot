import structlog
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = structlog.get_logger(__name__)


class RecommendationEngine:

    def generate_recommendations(
        self,
        portfolio_id: int,
        portfolio_service: Any,
        ai_client: Any,
    ) -> List[Dict[str, Any]]:
        portfolio = portfolio_service.get_portfolio_snapshot(portfolio_id)
        if not portfolio:
            return []

        all_recs = []
        all_recs.extend(self._check_concentration(portfolio))
        all_recs.extend(self._check_trader_risk(portfolio.get("traders", [])))
        all_recs.extend(self._check_profit_taking(portfolio.get("positions", [])))
        all_recs.extend(self._check_drawdown(portfolio.get("risk_metrics", {})))
        all_recs.extend(self._check_diversification(portfolio))

        ai_data = {
            "portfolio": portfolio,
            "risk_metrics": portfolio.get("risk_metrics", {}),
            "traders": portfolio.get("traders", []),
        }

        try:
            ai_recs = ai_client.analyze_portfolio(
                portfolio_data=portfolio,
                risk_data=portfolio.get("risk_metrics", {}),
                trader_data=portfolio.get("traders", []),
            )
            for rec in ai_recs.get("recommendations", []):
                if ai_client.validate_recommendation(rec):
                    rec["source"] = "ai"
                    all_recs.append(rec)
        except Exception as e:
            logger.warning("ai recommendation generation failed", error=str(e))

        return self._prioritize_recommendations(all_recs)

    def _check_concentration(self, portfolio: Dict[str, Any]) -> List[Dict[str, Any]]:
        recs = []
        traders = portfolio.get("traders", [])
        if not traders:
            return recs
        for t in traders:
            alloc = t.get("allocation_percent", 0)
            if alloc > 25:
                recs.append({
                    "type": "reduce",
                    "source": "engine",
                    "title": f"High concentration in {t.get('trader_name', 'unknown')}",
                    "summary": f"Trader allocation of {alloc:.1f}% exceeds 25% threshold. Consider reducing to limit single-trader risk.",
                    "confidence_score": 0.85,
                    "reasoning": f"{alloc:.1f}% allocation creates concentrated risk. Single trader underperformance significantly impacts portfolio.",
                    "risk_impact": "high",
                    "action_required": True,
                    "automated_possible": True,
                    "trader_id": t.get("id"),
                })
            elif alloc > 20:
                recs.append({
                    "type": "monitor",
                    "source": "engine",
                    "title": f"Approaching concentration limit: {t.get('trader_name', 'unknown')}",
                    "summary": f"Trader allocation at {alloc:.1f}% is approaching 25% threshold.",
                    "confidence_score": 0.60,
                    "reasoning": "Preventive monitoring recommended before concentration becomes problematic.",
                    "risk_impact": "medium",
                    "action_required": False,
                    "automated_possible": False,
                    "trader_id": t.get("id"),
                })
        return recs

    def _check_trader_risk(self, traders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        recs = []
        for t in traders:
            classification = t.get("classification", "balanced")
            pnl = t.get("total_pnl", 0)
            roi = t.get("total_roi", 0)
            if classification == "high_risk":
                recs.append({
                    "type": "pause",
                    "source": "engine",
                    "title": f"High risk trader: {t.get('trader_name', 'unknown')}",
                    "summary": "High risk classification suggests elevated loss probability.",
                    "confidence_score": 0.80,
                    "reasoning": "High risk traders are不适合 for capital preservation-focused portfolios.",
                    "risk_impact": "high",
                    "action_required": True,
                    "automated_possible": True,
                    "trader_id": t.get("id"),
                })
            elif classification == "aggressive" and pnl < 0:
                recs.append({
                    "type": "reduce",
                    "source": "engine",
                    "title": f"Aggressive trader losing: {t.get('trader_name', 'unknown')}",
                    "summary": f"Aggressive trader showing losses ({pnl:.2f}). Consider reducing allocation.",
                    "confidence_score": 0.65,
                    "reasoning": "Aggressive strategies in drawdown period may experience further losses.",
                    "risk_impact": "medium",
                    "action_required": True,
                    "automated_possible": True,
                    "trader_id": t.get("id"),
                })
            elif t.get("is_underperforming"):
                recs.append({
                    "type": "reduce",
                    "source": "engine",
                    "title": f"Underperforming trader: {t.get('trader_name', 'unknown')}",
                    "summary": "Trader detected as underperforming compared to historical metrics.",
                    "confidence_score": 0.70,
                    "reasoning": "Sustained underperformance may indicate strategy degradation.",
                    "risk_impact": "medium",
                    "action_required": True,
                    "automated_possible": False,
                    "trader_id": t.get("id"),
                })
        return recs

    def _check_profit_taking(self, positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        recs = []
        for p in positions:
            pnl_pct = p.get("pnl_percent", 0)
            if pnl_pct > 30:
                recs.append({
                    "type": "take_profit",
                    "source": "engine",
                    "title": f"Significant gains: {p.get('instrument_name', p.get('instrument_symbol', 'unknown'))}",
                    "summary": f"Position up {pnl_pct:.1f}%. Consider taking partial profits to lock in gains.",
                    "confidence_score": 0.75,
                    "reasoning": "Positions with >30% gains should be evaluated for profit-taking to reduce reversal risk.",
                    "risk_impact": "medium",
                    "action_required": False,
                    "automated_possible": True,
                    "position_id": p.get("id"),
                })
            elif pnl_pct > 15:
                recs.append({
                    "type": "monitor",
                    "source": "engine",
                    "title": f"Notable gains: {p.get('instrument_name', p.get('instrument_symbol', 'unknown'))}",
                    "summary": f"Position up {pnl_pct:.1f}%. Set profit-taking alert.",
                    "confidence_score": 0.45,
                    "reasoning": "Moderate gains worth monitoring for profit-taking opportunities.",
                    "risk_impact": "low",
                    "action_required": False,
                    "automated_possible": False,
                    "position_id": p.get("id"),
                })
        return recs

    def _check_drawdown(self, risk_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        recs = []
        dd = risk_metrics.get("max_drawdown", 0)
        if dd > 25:
            recs.append({
                "type": "reduce",
                "source": "engine",
                "title": "Portfolio drawdown exceeds 25%",
                "summary": f"Current drawdown of {dd:.1f}% exceeds risk threshold. Immediate action recommended.",
                "confidence_score": 0.95,
                "reasoning": "Drawdown >25% indicates significant capital erosion. Risk reduction actions needed.",
                "risk_impact": "critical",
                "action_required": True,
                "automated_possible": True,
            })
        elif dd > 15:
            recs.append({
                "type": "reduce",
                "source": "engine",
                "title": "Elevated drawdown level",
                "summary": f"Drawdown at {dd:.1f}%. Consider reducing risky positions.",
                "confidence_score": 0.80,
                "reasoning": "Drawdown approaching critical levels. Proactive reduction may prevent further losses.",
                "risk_impact": "high",
                "action_required": True,
                "automated_possible": True,
            })
        elif dd > 10:
            recs.append({
                "type": "monitor",
                "source": "engine",
                "title": "Moderate drawdown detected",
                "summary": f"Drawdown at {dd:.1f}%. Continue monitoring closely.",
                "confidence_score": 0.50,
                "reasoning": "Moderate drawdown warrants increased monitoring frequency.",
                "risk_impact": "medium",
                "action_required": False,
                "automated_possible": False,
            })
        return recs

    def _check_diversification(self, portfolio: Dict[str, Any]) -> List[Dict[str, Any]]:
        recs = []
        traders = portfolio.get("traders", [])
        positions = portfolio.get("positions", [])
        allocations = portfolio.get("allocations", {})
        num_traders = len(traders)
        num_positions = len(positions)
        instrument_types = set(p.get("instrument_type") for p in positions)
        if num_traders < 3:
            recs.append({
                "type": "rebalance",
                "source": "engine",
                "title": "Insufficient diversification in traders",
                "summary": f"Only {num_traders} copied traders. Minimum 3 recommended for adequate diversification.",
                "confidence_score": 0.80,
                "reasoning": "Low trader count increases vulnerability to single-trader underperformance.",
                "risk_impact": "high",
                "action_required": True,
                "automated_possible": False,
            })
        if len(instrument_types) < 3:
            recs.append({
                "type": "rebalance",
                "source": "engine",
                "title": "Limited instrument type diversification",
                "summary": f"Only {len(instrument_types)} instrument types. Broaden exposure across asset classes.",
                "confidence_score": 0.70,
                "reasoning": "Concentration in few asset classes increases correlation risk.",
                "risk_impact": "medium",
                "action_required": True,
                "automated_possible": False,
            })
        crypto_pct = allocations.get("crypto", 0)
        if crypto_pct > 30:
            recs.append({
                "type": "rebalance",
                "source": "engine",
                "title": "Crypto exposure exceeds 30%",
                "summary": f"Crypto allocation at {crypto_pct:.1f}% exceeds recommended 30% maximum.",
                "confidence_score": 0.85,
                "reasoning": "High crypto exposure introduces excessive volatility to a capital preservation portfolio.",
                "risk_impact": "high",
                "action_required": True,
                "automated_possible": True,
            })
        return recs

    def _prioritize_recommendations(self, recs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        priority_map = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        def sort_key(r: Dict[str, Any]) -> tuple:
            risk = r.get("risk_impact", "low")
            prio = priority_map.get(risk, 99)
            confidence = r.get("confidence_score", 0)
            return (prio, -confidence)
        recs.sort(key=sort_key)
        for rec in recs:
            rec["priority_rank"] = recs.index(rec) + 1
        return recs

    @staticmethod
    def get_confidence_label(score: float) -> str:
        if score >= 0.90:
            return "very_high"
        if score >= 0.70:
            return "high"
        if score >= 0.40:
            return "medium"
        return "low"

    @staticmethod
    def save_recommendations(portfolio_id: int, recs: List[Dict[str, Any]], db_session: Any) -> None:
        from backend.database.models import AiRecommendation
        for rec in recs:
            existing = db_session.query(AiRecommendation).filter(
                AiRecommendation.portfolio_id == portfolio_id,
                AiRecommendation.recommendation_type == rec.get("type", ""),
                AiRecommendation.title == rec.get("title", ""),
                AiRecommendation.applied == False,
            ).first()
            if existing:
                continue
            db_rec = AiRecommendation(
                portfolio_id=portfolio_id,
                recommendation_type=rec.get("type", "general"),
                title=rec.get("title", ""),
                summary=rec.get("summary", ""),
                confidence_score=rec.get("confidence_score", 0.0),
                details=rec,
            )
            db_session.add(db_rec)
        db_session.commit()
