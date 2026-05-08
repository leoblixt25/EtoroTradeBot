from typing import Any, Dict


class RiskLimits:
    MAX_PORTFOLIO_DRAWDOWN = 0.25
    MAX_ALLOCATION_PER_TRADER = 0.30
    MIN_DIVERSIFICATION = 3
    MAX_SINGLE_POSITION = 0.20
    MAX_CRYPTO_EXPOSURE = 0.30
    MAX_VOLATILITY = 0.40
    MIN_HEALTH_SCORE = 30
    COOLDOWN_DAYS_AFTER_LOSS = 7
    VOLATILITY_EXPOSURE_REDUCTION = 0.50
    MAX_DAILY_LOSS = 0.05
    EMERGENCY_STOP_DRAWDOWN = 0.35

    @classmethod
    def get_all_limits(cls) -> Dict[str, Any]:
        return {
            "max_portfolio_drawdown": cls.MAX_PORTFOLIO_DRAWDOWN,
            "max_allocation_per_trader": cls.MAX_ALLOCATION_PER_TRADER,
            "min_diversification": cls.MIN_DIVERSIFICATION,
            "max_single_position": cls.MAX_SINGLE_POSITION,
            "max_crypto_exposure": cls.MAX_CRYPTO_EXPOSURE,
            "max_volatility": cls.MAX_VOLATILITY,
            "min_health_score": cls.MIN_HEALTH_SCORE,
            "cooldown_days_after_loss": cls.COOLDOWN_DAYS_AFTER_LOSS,
            "volatility_exposure_reduction": cls.VOLATILITY_EXPOSURE_REDUCTION,
            "max_daily_loss": cls.MAX_DAILY_LOSS,
            "emergency_stop_drawdown": cls.EMERGENCY_STOP_DRAWDOWN,
        }

    @classmethod
    def update_limit(cls, name: str, value: Any) -> bool:
        valid_limits = cls.get_all_limits()
        if name not in valid_limits:
            return False
        setattr(cls, name.upper(), value)
        return True

    @classmethod
    def reset_defaults(cls) -> None:
        cls.MAX_PORTFOLIO_DRAWDOWN = 0.25
        cls.MAX_ALLOCATION_PER_TRADER = 0.30
        cls.MIN_DIVERSIFICATION = 3
        cls.MAX_SINGLE_POSITION = 0.20
        cls.MAX_CRYPTO_EXPOSURE = 0.30
        cls.MAX_VOLATILITY = 0.40
        cls.MIN_HEALTH_SCORE = 30
        cls.COOLDOWN_DAYS_AFTER_LOSS = 7
        cls.VOLATILITY_EXPOSURE_REDUCTION = 0.50
        cls.MAX_DAILY_LOSS = 0.05
        cls.EMERGENCY_STOP_DRAWDOWN = 0.35

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> None:
        for key, value in config.items():
            attr_name = key.upper()
            if hasattr(cls, attr_name):
                setattr(cls, attr_name, value)
