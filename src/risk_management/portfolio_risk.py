"""
投資組合風險管理模組

此模組實現了投資組合級別的風險管理策略，包括分散化、相關性分析和風險平價等。

注意：此檔案已被重構為多個子模組以提高可維護性。
請使用以下導入方式：
- from .portfolio_risk_base import PortfolioRiskManager
- from .correlation_analyzer import CorrelationAnalyzer
- from .diversification_manager import DiversificationManager, RiskParityStrategy
- from .sector_exposure_manager import SectorExposureManager, ConcentrationRiskManager
"""

# 為了向後相容性，重新導出所有類別
from .portfolio_risk_base import PortfolioRiskManager
from .correlation_analyzer import CorrelationAnalyzer
from .diversification_manager import DiversificationManager, RiskParityStrategy
from .sector_exposure_manager import SectorExposureManager, ConcentrationRiskManager

__all__ = [
    "PortfolioRiskManager",
    "CorrelationAnalyzer",
    "DiversificationManager",
    "RiskParityStrategy",
    "SectorExposureManager",
    "ConcentrationRiskManager",
]

# 注意：原始類別定義已移至子模組
# 為了向後相容性，所有類別都可以從此模組直接導入
# 建議使用子模組導入以獲得更好的程式碼組織

# 使用範例：
# from src.risk_management.portfolio_risk import PortfolioRiskManager  # 向後相容
# from src.risk_management.portfolio_risk_base import PortfolioRiskManager  # 建議方式
