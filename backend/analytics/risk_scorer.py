import numpy as np
from typing import Any, Dict, List, Tuple


class RiskScorer:

    @staticmethod
    def calculate_portfolio_risk_score(portfolio_data: Dict[str, Any]) -> int:
        score = 0
        allocation = portfolio_data.get("allocations", {})
        volatility = portfolio_data.get("volatility", 0)
        drawdown = portfolio_data.get("current_drawdown", 0)
        max_dd = portfolio_data.get("max_drawdown", 0)
        health = portfolio_data.get("health_score", 100)

        score += RiskScorer.calculate_concentration_score(allocation)
        score += RiskScorer.calculate_volatility_score(volatility)
        score += RiskScorer.calculate_drawdown_score(drawdown, max_dd)

        if health < 30:
            score += 25
        elif health < 50:
            score += 15
        elif health < 70:
            score += 5

        leverage = portfolio_data.get("leverage_ratio", 1.0)
        if leverage > 2.0:
            score += 10
        elif leverage > 1.5:
            score += 5

        correlation = portfolio_data.get("correlation_risk", 0)
        if correlation > 0.7:
            score += 10
        elif correlation > 0.5:
            score += 5

        crypto_exposure = allocation.get("crypto", 0)
        if crypto_exposure > 30:
            score += 10

        return min(100, max(0, score))

    @staticmethod
    def calculate_trader_risk_score(performance_data: Dict[str, Any]) -> int:
        score = 0
        volatility = performance_data.get("volatility", 0)
        dd = performance_data.get("max_drawdown", 0)
        win_rate = performance_data.get("win_rate", 50)
        consistency = performance_data.get("consistency_score", 50)
        classification = performance_data.get("classification", "balanced")

        score += RiskScorer.calculate_volatility_score(volatility)
        score += RiskScorer.calculate_drawdown_score(dd, max(1, dd))

        if win_rate < 30:
            score += 20
        elif win_rate < 45:
            score += 10

        if consistency < 30:
            score += 15
        elif consistency < 50:
            score += 8

        class_map = {"conservative": 5, "balanced": 15, "aggressive": 30, "high_risk": 50}
        score += class_map.get(classification, 15)

        trade_count = performance_data.get("trade_count", 0)
        if trade_count < 5:
            score += 10

        return min(100, max(0, score))

    @staticmethod
    def calculate_market_risk_score(market_data: Dict[str, Any]) -> int:
        score = 0
        vix = market_data.get("vix", 20)
        if vix > 40:
            score += 30
        elif vix > 30:
            score += 20
        elif vix > 20:
            score += 10

        trend = market_data.get("market_trend", "neutral")
        if trend == "bearish":
            score += 15
        elif trend == "strongly_bearish":
            score += 25

        economic_events = market_data.get("economic_events", [])
        high_impact = sum(1 for e in economic_events if e.get("impact") == "high")
        score += min(high_impact * 5, 20)

        sector_risk = market_data.get("sector_risk", "low")
        sector_map = {"low": 0, "moderate": 5, "elevated": 10, "high": 15}
        score += sector_map.get(sector_risk, 0)

        liquidity = market_data.get("liquidity_risk", "low")
        liquidity_map = {"low": 0, "moderate": 5, "high": 10}
        score += liquidity_map.get(liquidity, 0)

        return min(100, max(0, score))

    @staticmethod
    def calculate_volatility_score(volatility: float) -> int:
        vol = abs(volatility)
        if vol > 0.50:
            return 40
        if vol > 0.40:
            return 30
        if vol > 0.30:
            return 20
        if vol > 0.20:
            return 10
        if vol > 0.10:
            return 5
        return 0

    @staticmethod
    def calculate_concentration_score(allocation_pcts: Dict[str, float]) -> int:
        if not allocation_pcts:
            return 0
        values = np.array(list(allocation_pcts.values()), dtype=np.float64)
        total = values.sum()
        if total == 0:
            return 0
        norm = values / total
        hhi = float(np.sum(norm ** 2))
        if hhi > 0.80:
            return 30
        if hhi > 0.60:
            return 20
        if hhi > 0.40:
            return 10
        if hhi > 0.25:
            return 5
        return 0

    @staticmethod
    def calculate_drawdown_score(current_drawdown: float, max_drawdown: float) -> int:
        current = abs(current_drawdown)
        max_dd = max(abs(max_drawdown), 0.01)
        severity = current / max_dd

        if current > 0.30:
            return 35
        if current > 0.20:
            return 25
        if current > 0.15:
            return 10
        if current > 0.10:
            return 8
        if severity > 0.65:
            return 15
        if severity > 0.40:
            return 8
        if severity > 0.15:
            return 3
        return 0

    @staticmethod
    def calculate_composite_risk(portfolio_risk: int, trader_risk: int, market_risk: int) -> int:
        composite = int(portfolio_risk * 0.50 + trader_risk * 0.30 + market_risk * 0.20)
        return min(100, max(0, composite))

    @staticmethod
    def get_risk_level(score: int) -> str:
        if score <= 20:
            return "low"
        if score <= 40:
            return "moderate"
        if score <= 60:
            return "elevated"
        if score <= 80:
            return "high"
        return "critical"

    @staticmethod
    def get_risk_breakdown(portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
        allocation = portfolio_data.get("allocations", {})
        volatility = portfolio_data.get("volatility", 0)
        drawdown = portfolio_data.get("current_drawdown", 0)
        max_dd = portfolio_data.get("max_drawdown", 0)
        health = portfolio_data.get("health_score", 100)
        leverage = portfolio_data.get("leverage_ratio", 1.0)
        correlation = portfolio_data.get("correlation_risk", 0)

        vol_score = RiskScorer.calculate_volatility_score(volatility)
        conc_score = RiskScorer.calculate_concentration_score(allocation)
        dd_score = RiskScorer.calculate_drawdown_score(drawdown, max_dd)

        components = {
            "volatility_score": vol_score,
            "concentration_score": conc_score,
            "drawdown_score": dd_score,
            "correlation_score": min(20, int(correlation * 20)),
            "leverage_score": min(10, int((leverage - 1) * 20)) if leverage > 1 else 0,
            "health_penalty": max(0, 100 - health) // 4,
        }

        total = sum(components.values())
        return {
            "components": components,
            "total_score": min(100, total),
            "risk_level": RiskScorer.get_risk_level(min(100, total)),
            "risk_levels": {k: RiskScorer.get_risk_level(v) for k, v in components.items()},
        }

    @staticmethod
    def check_risk_thresholds(metrics: Dict[str, Any], limits: Dict[str, float]) -> List[Dict[str, Any]]:
        exceeded = []
        threshold_map = {
            "max_drawdown": ("max_drawdown_pct", "max_drawdown", "Portfolio drawdown exceeds limit"),
            "max_volatility": ("volatility", "max_volatility", "Volatility exceeds limit"),
            "max_concentration": ("concentration_risk", "max_concentration", "Concentration exceeds limit"),
            "min_health_score": ("health_score", "min_health_score", "Health score below minimum"),
            "max_allocation_per_trader": ("largest_allocation", "max_allocation_per_trader", "Single trader allocation exceeds limit"),
            "max_crypto_exposure": ("crypto_exposure", "max_crypto_exposure", "Crypto exposure exceeds limit"),
        }
        for limit_name, (metric_key, limit_key, message) in threshold_map.items():
            metric_val = metrics.get(metric_key, 0)
            limit_val = limits.get(limit_key, limits.get(limit_name, 0))
            is_min_threshold = limit_name.startswith("min_")
            is_exceeded = metric_val < limit_val if is_min_threshold else metric_val > limit_val
            if is_exceeded:
                exceeded.append({
                    "threshold": limit_name,
                    "current": metric_val,
                    "limit": limit_val,
                    "message": message,
                    "severity": "critical" if (metric_val > limit_val * 1.5 if not is_min_threshold else metric_val < limit_val * 0.5) else "warning",
                })
        return exceeded
