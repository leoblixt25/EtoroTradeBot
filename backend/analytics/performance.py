import numpy as np
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, date, timezone


class PerformanceAnalyzer:

    @staticmethod
    def analyze_performance(history: List[Dict[str, Any]], period: str = "1m") -> Dict[str, Any]:
        if not history:
            return {"error": "No history data", "metrics": {}}

        sorted_history = sorted(history, key=lambda h: h.get("date", ""))
        daily_values = [float(h.get("value", 0)) for h in sorted_history]
        returns = PerformanceAnalyzer._compute_returns(daily_values)

        days_map = {"1w": 7, "1m": 30, "3m": 90, "6m": 180, "1y": 365, "all": 730}
        days = days_map.get(period, 30)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        period_history = [h for h in sorted_history if isinstance(h.get("date"), str) and datetime.fromisoformat(h["date"]) >= cutoff]
        if not period_history:
            period_history = sorted_history[-min(days, len(sorted_history)):]

        period_values = [float(h.get("value", 0)) for h in period_history]
        period_returns = PerformanceAnalyzer._compute_returns(period_values)

        start_val = period_values[0] if period_values else 0
        end_val = period_values[-1] if period_values else 0
        total_return = ((end_val - start_val) / start_val * 100) if start_val != 0 else 0

        monthly_dict = PerformanceAnalyzer.calculate_monthly_returns(returns)
        monthly_returns_list = list(monthly_dict.values()) if monthly_dict else [0]

        best = PerformanceAnalyzer.calculate_best_month(monthly_returns_list)
        worst = PerformanceAnalyzer.calculate_worst_month(monthly_returns_list)

        return {
            "period": period,
            "total_return": round(total_return, 2),
            "start_value": round(start_val, 2),
            "end_value": round(end_val, 2),
            "growth_curve": PerformanceAnalyzer.calculate_growth_curve(daily_values),
            "rolling_returns": PerformanceAnalyzer.calculate_rolling_returns(returns)[-30:],
            "rolling_volatility": PerformanceAnalyzer.calculate_rolling_volatility(returns)[-30:],
            "monthly_returns": monthly_dict,
            "annualized_return": PerformanceAnalyzer.calculate_annualized_return(returns),
            "best_month": best,
            "worst_month": worst,
            "percent_positive_months": PerformanceAnalyzer.calculate_percent_positive_months(returns),
            "ulcer_index": PerformanceAnalyzer.calculate_ulcer_index(daily_values),
            "summary": PerformanceAnalyzer.generate_performance_summary({
                "total_return": total_return,
                "annualized_return": PerformanceAnalyzer.calculate_annualized_return(returns),
                "best_month": best,
                "worst_month": worst,
                "percent_positive_months": PerformanceAnalyzer.calculate_percent_positive_months(returns),
                "ulcer_index": PerformanceAnalyzer.calculate_ulcer_index(daily_values),
                "volatility": float(np.std(returns, ddof=1) * np.sqrt(252)) if len(returns) > 1 else 0,
            }),
        }

    @staticmethod
    def calculate_growth_curve(daily_values: List[float]) -> List[Dict[str, Any]]:
        if not daily_values:
            return []
        base = daily_values[0] if daily_values[0] != 0 else 1
        return [{"date": i, "value": round(v, 2)} for i, v in enumerate(daily_values)]

    @staticmethod
    def calculate_rolling_returns(returns: List[float], window: int = 30) -> List[float]:
        if len(returns) < window:
            return []
        arr = np.array(returns, dtype=np.float64)
        rolling = np.array([float(np.mean(arr[i:i + window])) for i in range(len(arr) - window + 1)])
        return [round(float(v), 6) for v in rolling]

    @staticmethod
    def calculate_rolling_volatility(returns: List[float], window: int = 30) -> List[float]:
        if len(returns) < window:
            return []
        arr = np.array(returns, dtype=np.float64)
        rolling = np.array([float(np.std(arr[i:i + window], ddof=1) * np.sqrt(252)) for i in range(len(arr) - window + 1)])
        return [round(float(v), 6) for v in rolling]

    @staticmethod
    def calculate_monthly_returns(returns: List[float]) -> Dict[str, float]:
        if not returns:
            return {}
        monthly = {}
        days_per_month = 21
        for i in range(0, len(returns), days_per_month):
            chunk = returns[i:i + days_per_month]
            month_num = i // days_per_month
            label = f"month_{month_num + 1}"
            monthly[label] = round(float(np.prod(1 + np.array(chunk, dtype=np.float64)) - 1) * 100, 4)
        return monthly

    @staticmethod
    def calculate_annualized_return(returns: List[float]) -> float:
        if not returns:
            return 0.0
        arr = np.array(returns, dtype=np.float64)
        total_return = float(np.prod(1 + arr)) - 1
        n = len(arr)
        if n < 1:
            return 0.0
        ann_factor = 252 / n
        annualized = (1 + total_return) ** ann_factor - 1
        return round(annualized * 100, 4)

    @staticmethod
    def calculate_best_month(returns: List[float]) -> Dict[str, Any]:
        if not returns:
            return {"month": None, "return": 0.0}
        monthly = PerformanceAnalyzer.calculate_monthly_returns(returns)
        if not monthly:
            return {"month": None, "return": 0.0}
        best_label = max(monthly, key=monthly.get)
        return {"month": best_label, "return": monthly[best_label]}

    @staticmethod
    def calculate_worst_month(returns: List[float]) -> Dict[str, Any]:
        if not returns:
            return {"month": None, "return": 0.0}
        monthly = PerformanceAnalyzer.calculate_monthly_returns(returns)
        if not monthly:
            return {"month": None, "return": 0.0}
        worst_label = min(monthly, key=monthly.get)
        return {"month": worst_label, "return": monthly[worst_label]}

    @staticmethod
    def calculate_percent_positive_months(returns: List[float]) -> float:
        if not returns:
            return 0.0
        monthly = PerformanceAnalyzer.calculate_monthly_returns(returns)
        if not monthly:
            return 0.0
        positive = sum(1 for v in monthly.values() if v > 0)
        return round((positive / len(monthly)) * 100, 2)

    @staticmethod
    def calculate_ulcer_index(returns: List[float]) -> float:
        if len(returns) < 2:
            return 0.0
        arr = np.array(returns, dtype=np.float64)
        cum = np.cumprod(1 + arr)
        running_max = np.maximum.accumulate(cum)
        drawdowns = (cum - running_max) / running_max
        squared = drawdowns ** 2
        ui = float(np.sqrt(np.mean(squared)))
        return round(ui * 100, 4)

    @staticmethod
    def generate_performance_summary(metrics: Dict[str, Any]) -> Dict[str, str]:
        lines = {}
        total_ret = metrics.get("total_return", 0)
        if total_ret > 0:
            lines["performance"] = f"Positive return of {total_ret:.2f}% for the period"
        elif total_ret < 0:
            lines["performance"] = f"Negative return of {total_ret:.2f}% for the period"
        else:
            lines["performance"] = "Flat performance for the period"

        ann_ret = metrics.get("annualized_return", 0)
        lines["annualized"] = f"Annualized return: {ann_ret:.2f}%"

        best = metrics.get("best_month", {})
        worst = metrics.get("worst_month", {})
        lines["best_month"] = f"Best month: {best.get('return', 0):.2f}%"
        lines["worst_month"] = f"Worst month: {worst.get('return', 0):.2f}%"

        pos_pct = metrics.get("percent_positive_months", 0)
        lines["positive_months"] = f"Positive months: {pos_pct:.1f}% of all months"

        vol = metrics.get("volatility", 0)
        if vol < 0.10:
            lines["volatility"] = f"Low volatility ({vol:.2f}%)"
        elif vol < 0.20:
            lines["volatility"] = f"Moderate volatility ({vol:.2f}%)"
        elif vol < 0.30:
            lines["volatility"] = f"Elevated volatility ({vol:.2f}%)"
        else:
            lines["volatility"] = f"High volatility ({vol:.2f}%)"

        ui = metrics.get("ulcer_index", 0)
        if ui < 2:
            lines["ulcer"] = "Very low downside risk (Ulcer Index)"
        elif ui < 5:
            lines["ulcer"] = "Low downside risk"
        elif ui < 10:
            lines["ulcer"] = "Moderate downside risk"
        else:
            lines["ulcer"] = "Elevated downside risk"

        return lines

    @staticmethod
    def _compute_returns(values: List[float]) -> List[float]:
        if len(values) < 2:
            return []
        arr = np.array(values, dtype=np.float64)
        returns = (arr[1:] - arr[:-1]) / arr[:-1]
        returns = np.where(np.isinf(returns) | np.isnan(returns), 0, returns)
        return [float(r) for r in returns]
