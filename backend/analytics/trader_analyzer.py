import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta


class TraderAnalyzer:

    @staticmethod
    def analyze_trader(performance_history: List[Dict[str, Any]], trader_info: Dict[str, Any]) -> Dict[str, Any]:
        if not performance_history:
            return {
                "trader": trader_info,
                "classification": "unknown",
                "classification_reason": "insufficient data",
                "risk_metrics": {},
                "ai_summary": "",
                "performance_trend": "stable",
                "recommendation": "monitor",
            }
        monthly_returns = [p.get("monthly_return", 0) for p in performance_history if p.get("monthly_return") is not None]
        volatilities = [p.get("volatility", 0) for p in performance_history if p.get("volatility") is not None]
        drawdowns = [p.get("max_drawdown", 0) for p in performance_history if p.get("max_drawdown") is not None]
        win_rates = [p.get("win_rate", 0) for p in performance_history if p.get("win_rate") is not None]
        risk_scores = [p.get("risk_score", 0) for p in performance_history if p.get("risk_score") is not None]

        avg_monthly = float(np.mean(monthly_returns)) if monthly_returns else 0
        avg_vol = float(np.mean(volatilities)) if volatilities else 0
        max_dd = float(np.max(drawdowns)) if drawdowns else 0
        avg_win_rate = float(np.mean(win_rates)) if win_rates else 0
        trade_freq = sum(p.get("trade_count", 0) for p in performance_history[-6:]) if len(performance_history) > 0 else 0

        metrics = {
            "avg_monthly_return": round(avg_monthly * 100, 2) if abs(avg_monthly) < 10 else round(avg_monthly, 2),
            "avg_volatility": round(avg_vol * 100, 2) if abs(avg_vol) < 10 else round(avg_vol, 2),
            "max_drawdown": round(max_dd * 100, 2) if abs(max_dd) < 10 else round(max_dd, 2),
            "avg_win_rate": round(avg_win_rate, 2),
            "trade_frequency": trade_freq,
        }

        classification = TraderAnalyzer.classify_trader(metrics)
        consistency = TraderAnalyzer.calculate_consistency_score(monthly_returns)
        div_score = TraderAnalyzer.calculate_diversification_score(trader_info.get("positions", []))

        rec_3m = performance_history[-3:] if len(performance_history) >= 3 else performance_history
        prev_3m = performance_history[-6:-3] if len(performance_history) >= 6 else []
        underperformance = TraderAnalyzer.detect_underperformance(
            [r.get("monthly_return", 0) for r in rec_3m],
            [r.get("monthly_return", 0) for r in prev_3m],
        )

        trend = TraderAnalyzer.compute_risk_score_trend(risk_scores)

        return {
            "trader": trader_info,
            "classification": classification,
            "classification_reason": TraderAnalyzer._classification_reason(classification, metrics),
            "risk_metrics": {
                **metrics,
                "consistency_score": round(consistency, 1),
                "diversification_score": div_score,
                "sharpe_like_score": TraderAnalyzer.calculate_sharpe_like_score(monthly_returns),
            },
            "ai_summary": "",
            "performance_trend": trend,
            "underperformance": underperformance,
            "recommendation": TraderAnalyzer._generate_recommendation(classification, underperformance, consistency),
        }

    @staticmethod
    def classify_trader(metrics: Dict[str, float]) -> str:
        monthly = abs(metrics.get("avg_monthly_return", 0))
        vol = abs(metrics.get("avg_volatility", 0))
        dd = abs(metrics.get("max_drawdown", 0))
        wr = metrics.get("avg_win_rate", 50)
        freq = metrics.get("trade_frequency", 0)

        if monthly < 3 and vol < 10 and dd < 10 and wr > 60 and freq < 20:
            return "conservative"
        if monthly < 8 and vol < 20 and dd < 20 and wr >= 45 and wr <= 60 and freq <= 50:
            return "balanced"
        if monthly < 15 and vol < 35 and dd < 35 and wr >= 35 and wr <= 45:
            return "aggressive"
        return "high_risk"

    @staticmethod
    def calculate_consistency_score(monthly_returns: List[float]) -> float:
        if len(monthly_returns) < 2:
            return 50.0
        arr = np.array(monthly_returns, dtype=np.float64)
        mean_ret = float(np.mean(arr))
        std_ret = float(np.std(arr, ddof=1))
        if std_ret == 0:
            return 100.0
        positive_ratio = float(np.sum(arr > 0)) / len(arr) * 100
        cv = abs(std_ret / mean_ret) if mean_ret != 0 else 999
        stability = max(0, 100 - min(cv * 10, 100))
        positivity = positive_ratio
        score = (stability * 0.6) + (positivity * 0.4)
        return round(min(100, max(0, score)), 1)

    @staticmethod
    def calculate_diversification_score(trader_positions: List[Dict[str, Any]]) -> int:
        if not trader_positions:
            return 0
        instruments = set()
        sectors = set()
        for p in trader_positions:
            if p.get("instrument_symbol"):
                instruments.add(p.get("instrument_symbol"))
            if p.get("sector"):
                sectors.add(p.get("sector"))
        inst_score = min(len(instruments) * 10, 50)
        sector_score = min(len(sectors) * 15, 50)
        return min(100, inst_score + sector_score)

    @staticmethod
    def detect_underperformance(recent_3m: List[float], previous_3m: List[float]) -> Dict[str, Any]:
        if not previous_3m:
            return {"is_underperforming": False, "severity": "none", "details": "no previous data"}
        rec_avg = float(np.mean(recent_3m)) if recent_3m else 0
        prev_avg = float(np.mean(previous_3m)) if previous_3m else 0
        if prev_avg <= 0:
            if rec_avg < prev_avg:
                return {"is_underperforming": True, "severity": "moderate", "details": "negative returns worsening"}
            return {"is_underperforming": False, "severity": "none", "details": "stable negative performance"}
        decline_pct = ((prev_avg - rec_avg) / abs(prev_avg)) * 100
        if decline_pct > 50:
            return {"is_underperforming": True, "severity": "high", "details": f"performance declined {decline_pct:.1f}% vs prior period"}
        if decline_pct > 25:
            return {"is_underperforming": True, "severity": "moderate", "details": f"performance declined {decline_pct:.1f}% vs prior period"}
        if decline_pct > 10:
            return {"is_underperforming": True, "severity": "low", "details": f"performance declined {decline_pct:.1f}% vs prior period"}
        return {"is_underperforming": False, "severity": "none", "details": "consistent performance"}

    @staticmethod
    def compute_risk_score_trend(monthly_risk_scores: List[float]) -> str:
        if len(monthly_risk_scores) < 2:
            return "stable"
        recent = monthly_risk_scores[-3:] if len(monthly_risk_scores) >= 3 else monthly_risk_scores
        earlier = monthly_risk_scores[:-3] if len(monthly_risk_scores) > 3 else monthly_risk_scores[:1]
        if not earlier:
            return "stable"
        recent_avg = float(np.mean(recent))
        earlier_avg = float(np.mean(earlier))
        if recent_avg > earlier_avg * 1.1:
            return "increasing"
        if recent_avg < earlier_avg * 0.9:
            return "decreasing"
        return "stable"

    @staticmethod
    def calculate_sharpe_like_score(returns: List[float], risk_free: float = 0.05) -> float:
        if len(returns) < 2:
            return 0.0
        arr = np.array(returns, dtype=np.float64)
        excess = float(np.mean(arr) - (risk_free / 12))
        std = float(np.std(arr, ddof=1))
        if std == 0:
            return 0.0
        return round((excess / std) * np.sqrt(12), 4)

    @staticmethod
    def calculate_max_drawdown(returns: List[float]) -> Dict[str, Any]:
        if not returns:
            return {"value": 0.0, "start_date": None, "end_date": None, "recovery_date": None}
        arr = np.array(returns, dtype=np.float64)
        cum = np.cumprod(1 + arr)
        running_max = np.maximum.accumulate(cum)
        dd = (cum - running_max) / running_max
        max_dd_idx = int(np.argmin(dd))
        max_dd_val = float(dd[max_dd_idx])
        peak_idx = int(np.argmax(cum[:max_dd_idx + 1]))
        recovery_idx = None
        for i in range(max_dd_idx + 1, len(cum)):
            if cum[i] >= cum[peak_idx]:
                recovery_idx = i
                break
        return {
            "value": round(max_dd_val * 100, 2),
            "start_date": peak_idx,
            "end_date": max_dd_idx,
            "recovery_date": recovery_idx,
        }

    @staticmethod
    def get_trader_summary(analysis: Dict[str, Any]) -> str:
        trader = analysis.get("trader", {})
        name = trader.get("trader_name", "Unknown Trader")
        classification = analysis.get("classification", "unknown")
        metrics = analysis.get("risk_metrics", {})
        trend = analysis.get("performance_trend", "stable")
        under = analysis.get("underperformance", {})
        lines = [
            f"*Trader Analysis: {name}*",
            f"Classification: {classification.upper()}",
            f"Trend: {trend}",
            f"Monthly Return: {metrics.get('avg_monthly_return', 'N/A')}%",
            f"Volatility: {metrics.get('avg_volatility', 'N/A')}%",
            f"Max Drawdown: {metrics.get('max_drawdown', 'N/A')}%",
            f"Win Rate: {metrics.get('avg_win_rate', 'N/A')}%",
            f"Consistency: {metrics.get('consistency_score', 'N/A')}/100",
            f"Sharpe-like: {metrics.get('sharpe_like_score', 'N/A')}",
            f"Sharsification: {metrics.get('diversification_score', 'N/A')}/100",
        ]
        if under.get("is_underperforming"):
            lines.append(f"*UNDERPERFORMING*: {under.get('details', '')}")
        rec = analysis.get("recommendation", "")
        if rec:
            lines.append(f"Recommendation: {rec}")
        return "\n".join(lines)

    @staticmethod
    def _classification_reason(classification: str, metrics: Dict[str, float]) -> str:
        reasons = {
            "conservantive": "Low returns, low volatility, high win rate, low trade frequency",
            "balanced": "Moderate returns and risk metrics within balanced ranges",
            "aggressive": "High returns with elevated volatility and drawdown",
            "high_risk": "Exceeds aggressive thresholds, elevated risk of loss",
        }
        return reasons.get(classification, "Insufficient data to classify")

    @staticmethod
    def _generate_recommendation(classification: str, underperformance: Dict[str, Any], consistency: float) -> str:
        if underperformance.get("severity") == "high":
            return "Consider pausing or reducing allocation - significant underperformance detected"
        if classification == "high_risk":
            return "Monitor closely and consider reducing exposure - high risk profile"
        if consistency < 30:
            return "Inconsistent performance - monitor before increasing allocation"
        if classification == "conservative":
            return "Suitable for capital preservation allocation"
        if classification == "balanced":
            return "Good fit for core portfolio allocation"
        if classification == "aggressive":
            return "Limited allocation recommended - suitable for growth portion only"
        return "Continue monitoring performance"
