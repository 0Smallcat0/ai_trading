"""
風險管理模組

此模組提供全面的風險管理和保護功能，包括：
- 停損策略
- 停利策略
- 資金管理
- 倉位大小控制
- 投資組合風險控制
- 風險指標計算
- 自動停單機制
"""

from .stop_loss import (
    StopLossStrategy,
    PercentStopLoss,
    ATRStopLoss,
    TimeBasedStopLoss,
    TrailingStopLoss,
    VolatilityStopLoss,
    SupportResistanceStopLoss,
    MultipleStopLoss,
)

from .take_profit import (
    TakeProfitStrategy,
    PercentTakeProfit,
    TargetTakeProfit,
    TrailingTakeProfit,
    RiskRewardTakeProfit,
    TimeBasedTakeProfit,
    MultipleTakeProfit,
)

from .position_sizing import (
    PositionSizingStrategy,
    FixedAmountPositionSizing,
    PercentPositionSizing,
    RiskBasedPositionSizing,
    KellyPositionSizing,
    VolatilityPositionSizing,
    OptimalFPositionSizing,
    PyramidingPositionSizing,
)

from .portfolio_risk import (
    PortfolioRiskManager,
    DiversificationManager,
    CorrelationAnalyzer,
    RiskParityStrategy,
    SectorExposureManager,
    ConcentrationRiskManager,
)

from .risk_metrics import (
    RiskMetricsCalculator,
    ValueAtRisk,
    ConditionalValueAtRisk,
    MaximumDrawdown,
)

from .circuit_breakers import (
    CircuitBreaker,
    DrawdownCircuitBreaker,
    VolatilityCircuitBreaker,
    LossCircuitBreaker,
    TimeCircuitBreaker,
    CompositeCircuitBreaker,
)

from .risk_manager import RiskManager

__all__ = [
    # 停損策略
    "StopLossStrategy",
    "PercentStopLoss",
    "ATRStopLoss",
    "TimeBasedStopLoss",
    "TrailingStopLoss",
    "VolatilityStopLoss",
    "SupportResistanceStopLoss",
    "MultipleStopLoss",
    # 停利策略
    "TakeProfitStrategy",
    "PercentTakeProfit",
    "TargetTakeProfit",
    "TrailingTakeProfit",
    "RiskRewardTakeProfit",
    "TimeBasedTakeProfit",
    "MultipleTakeProfit",
    # 倉位大小策略
    "PositionSizingStrategy",
    "FixedAmountPositionSizing",
    "PercentPositionSizing",
    "RiskBasedPositionSizing",
    "KellyPositionSizing",
    "VolatilityPositionSizing",
    "OptimalFPositionSizing",
    "PyramidingPositionSizing",
    # 投資組合風險管理
    "PortfolioRiskManager",
    "DiversificationManager",
    "CorrelationAnalyzer",
    "RiskParityStrategy",
    "SectorExposureManager",
    "ConcentrationRiskManager",
    # 風險指標計算
    "RiskMetricsCalculator",
    "ValueAtRisk",
    "ConditionalValueAtRisk",
    "MaximumDrawdown",
    # 熔斷機制
    "CircuitBreaker",
    "DrawdownCircuitBreaker",
    "VolatilityCircuitBreaker",
    "LossCircuitBreaker",
    "TimeCircuitBreaker",
    "CompositeCircuitBreaker",
    # 風險管理器
    "RiskManager",
]
