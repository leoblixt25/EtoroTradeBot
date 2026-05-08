import numpy as np
from typing import Any, List, Dict
from datetime import datetime, timedelta, timezone


class PortfolioCalculator:

    @staticmethod
    def calculate_total_value(positions: List[Dict[str, Any]]) -> float:
        total = 0.0
        for p in positions:
            qty = float(p.get("amount", p.get("quantity", 0)))
            price = float(p.get("current_price", p.get("price", 0)))
            total += qty * price
        return round(total, 2)

    @staticmethod
    def calculate_daily_pnl(positions: List[Dict[str, Any]]) -> Dict[str, float]:
        value = 0.0
        cost_basis = 0.0
        for p in positions:
            qty = float(p.get("amount", p.get("quantity", 0)))
            current = float(p.get("current_price", p.get("price", 0)))
            entry = float(p.get("entry_price", 0))
            value += qty * current
            cost_basis += qty * entry
        pnl = value - cost_basis
        cost_basis = cost_basis if cost_basis != 0 else 1
        return {"value": round(pnl, 2), "percent": round((pnl / cost_basis) * 100, 4)}

    @staticmethod
    def calculate_weekly_pnl(positions: List[Dict[str, Any]]) -> Dict[str, float]:
        value = 0.0
        cost_basis = 0.0
        for p in positions:
            qty = float(p.get("amount", p.get("quantity", 0)))
            current = float(p.get("current_price", p.get("price", 0)))
            entry = float(p.get("entry_price", 0))
            pnl_weekly = float(p.get("weekly_pnl", 0))
            value += qty * current
            cost_basis += qty * entry
        pnl = value - cost_basis
        cost_basis = cost_basis if cost_basis != 0 else 1
        return {"value": round(pnl, 2), "percent": round((pnl / cost_basis) * 100, 4)}

    @staticmethod
    def calculate_monthly_pnl(positions: List[Dict[str, Any]], history: List[Dict[str, Any]]) -> Dict[str, float]:
        if not positions:
            return {"value": 0.0, "percent": 0.0}
        current_value = PortfolioCalculator.calculate_total_value(positions)
        history = sorted(history, key=lambda h: h.get("date", ""))
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        past_value = current_value
        for h in history:
            h_date = h.get("date")
            if isinstance(h_date, str):
                h_date = datetime.fromisoformat(h_date)
            if h_date and h_date <= thirty_days_ago:
                past_value = float(h.get("value", current_value))
                break
        if not history:
            past_value = 0
        pnl = current_value - past_value
        past_value = past_value if past_value != 0 else 1
        return {"value": round(pnl, 2), "percent": round((pnl / past_value) * 100, 4)}

    @staticmethod
    def calculate_allocation_percentages(positions: List[Dict[str, Any]]) -> Dict[str, float]:
        if not positions:
            return {}
        type_totals: Dict[str, float] = {}
        total_value = PortfolioCalculator.calculate_total_value(positions)
        for p in positions:
            itype = p.get("instrument_type", "unknown")
            qty = float(p.get("amount", p.get("quantity", 0)))
            price = float(p.get("current_price", p.get("price", 0)))
            type_totals[itype] = type_totals.get(itype, 0) + (qty * price)
        total_value = total_value if total_value != 0 else 1
        return {k: round((v / total_value) * 100, 2) for k, v in type_totals.items()}

    @staticmethod
    def calculate_unrealized_pnl(positions: List[Dict[str, Any]]) -> Dict[str, float]:
        value = 0.0
        cost = 0.0
        for p in positions:
            qty = float(p.get("amount", p.get("quantity", 0)))
            current = float(p.get("current_price", p.get("price", 0)))
            entry = float(p.get("entry_price", 0))
            value += qty * current
            cost += qty * entry
        pnl = value - cost
        cost = cost if cost != 0 else 1
        return {"value": round(pnl, 2), "percent": round((pnl / cost) * 100, 4)}

    @staticmethod
    def calculate_realized_pnl(trades: List[Dict[str, Any]]) -> float:
        total = 0.0
        for t in trades:
            total += float(t.get("pnl", t.get("realized_pnl", 0)))
        return round(total, 2)

    @staticmethod
    def calculate_max_drawdown(history: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not history:
            return {"value": 0.0, "percent": 0.0, "date_from": None, "date_to": None}
        values = [float(h.get("value", 0)) for h in sorted(history, key=lambda x: x.get("date", ""))]
        if not values:
            return {"value": 0.0, "percent": 0.0, "date_from": None, "date_to": None}
        peak = values[0]
        max_dd = 0.0
        dd_from_idx = 0
        dd_to_idx = 0
        peak_idx = 0
        for i, v in enumerate(values):
            if v > peak:
                peak = v
                peak_idx = i
            dd = (peak - v) / peak if peak != 0 else 0
            if dd > max_dd:
                max_dd = dd
                dd_from_idx = peak_idx
                dd_to_idx = i
        dates = [h.get("date") for h in sorted(history, key=lambda x: x.get("date", ""))]
        date_from = dates[dd_from_idx] if dd_from_idx < len(dates) else None
        date_to = dates[dd_to_idx] if dd_to_idx < len(dates) else None
        return {"value": round(peak * max_dd, 2), "percent": round(max_dd * 100, 2,), "date_from": date_from, "date_to": date_to}

    @staticmethod
    def calculate_var_95(returns: List[float]) -> float:
        if len(returns) < 2:
            return 0.0
        arr = np.array(returns, dtype=np.float64)
        return round(float(np.percentile(arr, 5)), 4)

    @staticmethod
    def calculate_volatility(returns: List[float], period: int = 252) -> float:
        if len(returns) < 2:
            return 0.0
        arr = np.array(returns, dtype=np.float64)
        std = np.std(arr, ddof=1)
        return round(float(std * np.sqrt(period)), 4)

    @staticmethod
    def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.05) -> float:
        if len(returns) < 2:
            return 0.0
        arr = np.array(returns, dtype=np.float64)
        excess = np.mean(arr) - (risk_free_rate / 252)
        std = np.std(arr, ddof=1)
        if std == 0:
            return 0.0
        return round(float(excess / std * np.sqrt(252)), 4)

    @staticmethod
    def calculate_sortino_ratio(returns: List[float], risk_free_rate: float = 0.05) -> float:
        if len(returns) < 2:
            return 0.0
        arr = np.array(returns, dtype=np.float64)
        excess = np.mean(arr) - (risk_free_rate / 252)
        downside = arr[arr < 0]
        if len(downside) == 0:
            return float("inf") if excess > 0 else 0.0
        downside_std = np.std(downside, ddof=1)
        if downside_std == 0:
            return 0.0
        return round(float(excess / downside_std * np.sqrt(252)), 4)

    @staticmethod
    def calculate_calmar_ratio(returns: List[float], max_dd: float) -> float:
        if len(returns) < 2 or max_dd == 0:
            return 0.0
        arr = np.array(returns, dtype=np.float64)
        annualized_return = float(np.mean(arr) * 252)
        dd_decimal = max_dd / 100 if max_dd > 1 else max_dd
        return round(annualized_return / dd_decimal, 4) if dd_decimal != 0 else 0.0

    @staticmethod
    def calculate_win_rate(trades: List[Dict[str, Any]]) -> float:
        if not trades:
            return 0.0
        wins = sum(1 for t in trades if float(t.get("pnl", t.get("realized_pnl", 0))) > 0)
        return round((wins / len(trades)) * 100, 2)

    @staticmethod
    def calculate_average_return(returns: List[float], period: str = "monthly") -> float:
        if not returns:
            return 0.0
        arr = np.array(returns, dtype=np.float64)
        periods_map = {"daily": 252, "weekly": 52, "monthly": 12, "yearly": 1}
        n = periods_map.get(period, 12)
        avg = float(np.mean(arr))
        return round(avg * n * 100, 4)

    @staticmethod
    def calculate_profit_factor(gross_profit: float, gross_loss: float) -> float:
        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0
        return round(abs(gross_profit / gross_loss), 4)

    @staticmethod
    def calculate_concentration_risk(allocations: Dict[str, float]) -> float:
        if not allocations:
            return 0.0
        pcts = np.array(list(allocations.values()), dtype=np.float64)
        pcts = pcts / pcts.sum() if pcts.sum() != 0 else pcts
        hhi = float(np.sum(pcts ** 2))
        n = len(pcts)
        normalized = (hhi - (1 / n)) / (1 - (1 / n)) if n > 1 else 1.0
        return round(normalized, 4)

    @staticmethod
    def calculate_correlation_risk(returns_dict: Dict[str, List[float]]) -> float:
        if len(returns_dict) < 2:
            return 0.0
        keys = list(returns_dict.keys())
        min_len = min(len(v) for v in returns_dict.values())
        if min_len < 2:
            return 0.0
        arrs = np.array([returns_dict[k][:min_len] for k in keys], dtype=np.float64)
        corr_matrix = np.corrcoef(arrs)
        n = corr_matrix.shape[0]
        upper_tri = corr_matrix[np.triu_indices(n, k=1)]
        if len(upper_tri) == 0:
            return 0.0
        avg_corr = float(np.mean(np.abs(upper_tri)))
        return round(avg_corr, 4)

    @staticmethod
    def calculate_health_score(metrics: Dict[str, float]) -> int:
        score = 100
        drawdown = abs(metrics.get("max_drawdown_pct", 0))
        if drawdown > 30:
            score -= 30
        elif drawdown > 20:
            score -= 20
        elif drawdown > 10:
            score -= 10
        volatility = metrics.get("volatility", 0)
        if volatility > 0.40:
            score -= 20
        elif volatility > 0.30:
            score -= 10
        elif volatility > 0.20:
            score -= 5
        concentration = metrics.get("concentration_risk", 0)
        if concentration > 0.60:
            score -= 20
        elif concentration > 0.40:
            score -= 10
        elif concentration > 0.25:
            score -= 5
        win_rate = metrics.get("win_rate", 50)
        if win_rate < 30:
            score -= 15
        elif win_rate < 45:
            score -= 10
        elif win_rate < 55:
            score -= 0
        sharpe = metrics.get("sharpe_ratio", 1)
        if sharpe < 0:
            score -= 20
        elif sharpe < 0.5:
            score -= 10
        elif sharpe < 1.0:
            score -= 5
        diversity = metrics.get("diversification_count", 1)
        if diversity < 3:
            score -= 15
        elif diversity < 5:
            score -= 5
        correlation = metrics.get("correlation_risk", 0)
        if correlation > 0.80:
            score -= 15
        elif correlation > 0.60:
            score -= 10
        elif correlation > 0.40:
            score -= 5
        return max(0, min(100, score))
