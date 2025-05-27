"""
風險指標計算模組

此模組實現了各種風險指標的計算，包括 VaR、最大回撤、波動率等。

注意：原始類別定義已移至子模組以提高可維護性。
為了向後相容性，所有類別都可以從此模組直接導入。

子模組：
- risk_metrics_base: 基礎風險指標計算器
- var_calculator: VaR 和 CVaR 計算器
- drawdown_calculator: 最大回撤計算器
- volatility_calculator: 波動率計算器
"""

# 為了向後相容性，重新導出所有類別
from .risk_metrics_base import RiskMetricsCalculator
from .var_calculator import ValueAtRisk, ConditionalValueAtRisk
from .drawdown_calculator import MaximumDrawdown
from .volatility_calculator import VolatilityCalculator

__all__ = [
    "RiskMetricsCalculator",
    "ValueAtRisk",
    "ConditionalValueAtRisk",
    "MaximumDrawdown",
    "VolatilityCalculator",
]

# 保留原始類別定義以確保向後相容性
# 這些將在未來版本中移除，請使用上述子模組導入

# 使用範例：
# from src.risk_management.risk_metrics import RiskMetricsCalculator  # 向後相容
# from src.risk_management.risk_metrics_base import RiskMetricsCalculator  # 建議方式


