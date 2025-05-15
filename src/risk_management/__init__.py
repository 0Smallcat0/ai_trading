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

from .circuit_breakers import (
    CircuitBreaker,
    CompositeCircuitBreaker,
    DrawdownCircuitBreaker,
    LossCircuitBreaker,
    TimeCircuitBreaker,
    VolatilityCircuitBreaker,
)
from .portfolio_risk import (
    ConcentrationRiskManager,
    CorrelationAnalyzer,
    DiversificationManager,
    PortfolioRiskManager,
    RiskParityStrategy,
    SectorExposureManager,
)
from .position_sizing import (
    FixedAmountPositionSizing,
    KellyPositionSizing,
    OptimalFPositionSizing,
    PercentPositionSizing,
    PositionSizingStrategy,
    PyramidingPositionSizing,
    RiskBasedPositionSizing,
    VolatilityPositionSizing,
)
from .risk_manager import RiskManager
from .risk_metrics import (
    ConditionalValueAtRisk,
    MaximumDrawdown,
    RiskMetricsCalculator,
    ValueAtRisk,
)
from .stop_loss import (
    ATRStopLoss,
    MultipleStopLoss,
    PercentStopLoss,
    StopLossStrategy,
    SupportResistanceStopLoss,
    TimeBasedStopLoss,
    TrailingStopLoss,
    VolatilityStopLoss,
)
from .take_profit import (
    MultipleTakeProfit,
    PercentTakeProfit,
    RiskRewardTakeProfit,
    TakeProfitStrategy,
    TargetTakeProfit,
    TimeBasedTakeProfit,
    TrailingTakeProfit,
)

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
