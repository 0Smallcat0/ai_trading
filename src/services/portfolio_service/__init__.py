"""投資組合服務模組

此模組提供完整的投資組合管理服務，包括：
- 核心服務功能（CRUD 操作）
- 投資組合最佳化服務
- 風險分析服務
- 資料庫操作服務

主要類別：
- PortfolioService: 主要服務類別，整合所有功能
- PortfolioServiceCore: 核心服務
- PortfolioOptimizationService: 最佳化服務
- PortfolioRiskAnalysisService: 風險分析服務
- PortfolioDatabaseService: 資料庫服務

為了保持向後相容性，原始的 PortfolioService 類別仍然可用。
"""

from .core import PortfolioServiceCore, Portfolio, PortfolioHolding

from .optimization import PortfolioOptimizationService
from .risk_analysis import PortfolioRiskAnalysisService
from .database import PortfolioDatabaseService

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# 設定日誌
logger = logging.getLogger(__name__)


class PortfolioService:
    """投資組合服務主類別

    整合所有投資組合管理功能的主要服務類別。
    這個類別提供了一個統一的介面來訪問所有投資組合相關的功能。
    """

    def __init__(self, db_path: str = None):
        """初始化投資組合服務

        Args:
            db_path: 資料庫路徑
        """
        # 初始化核心服務
        self.core = PortfolioServiceCore(db_path)

        # 初始化子服務
        self.optimization = PortfolioOptimizationService(self.core)
        self.risk_analysis = PortfolioRiskAnalysisService(self.core)
        self.database = PortfolioDatabaseService(self.core)

    # ==================== 核心功能 ====================

    def create_portfolio(
        self,
        name: str,
        description: str = "",
        holdings: List[Dict] = None,
        benchmark: str = "^TWII",
        risk_free_rate: float = 0.02,
    ) -> str:
        """創建投資組合

        Args:
            name: 投資組合名稱
            description: 描述
            holdings: 初始持倉列表
            benchmark: 基準指數
            risk_free_rate: 無風險利率

        Returns:
            投資組合ID
        """
        return self.core.create_portfolio_simple(
            name=name,
            description=description,
            holdings=holdings,
            benchmark=benchmark,
            risk_free_rate=risk_free_rate,
        )

    def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        """獲取投資組合

        Args:
            portfolio_id: 投資組合ID

        Returns:
            投資組合物件
        """
        return self.core.get_portfolio(portfolio_id)

    def get_portfolio_list(self, limit: int = 50) -> List[Dict]:
        """獲取投資組合列表

        Args:
            limit: 限制數量

        Returns:
            投資組合列表
        """
        return self.database.get_portfolio_list(limit)

    def update_portfolio(
        self,
        portfolio_id: str,
        name: str = None,
        description: str = None,
        benchmark: str = None,
        risk_free_rate: float = None,
    ) -> bool:
        """更新投資組合基本資訊

        Args:
            portfolio_id: 投資組合ID
            name: 新名稱
            description: 新描述
            benchmark: 新基準指數
            risk_free_rate: 新無風險利率

        Returns:
            是否成功
        """
        return self.database.update_portfolio(
            portfolio_id=portfolio_id,
            name=name,
            description=description,
            benchmark=benchmark,
            risk_free_rate=risk_free_rate,
        )

    def delete_portfolio(self, portfolio_id: str) -> bool:
        """刪除投資組合

        Args:
            portfolio_id: 投資組合ID

        Returns:
            是否成功
        """
        return self.database.delete_portfolio(portfolio_id)

    # ==================== 最佳化功能 ====================

    def rebalance_portfolio(
        self,
        portfolio_id: str,
        optimization_method: str = "equal_weight",
        constraints: Dict[str, Any] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """重新平衡投資組合（重構後的版本）

        Args:
            portfolio_id: 投資組合ID
            optimization_method: 最佳化方法
            constraints: 約束條件
            **kwargs: 其他參數

        Returns:
            再平衡結果
        """
        try:
            # 1. 驗證再平衡配置
            portfolio = self.core.get_portfolio(portfolio_id)
            if not portfolio:
                return {"success": False, "error": f"投資組合不存在: {portfolio_id}"}

            # 獲取當前權重
            current_weights = {h.symbol: h.weight for h in portfolio.holdings}
            symbols = list(current_weights.keys())

            # 2. 計算目標權重
            target_weights = self.optimization._calculate_target_weights(
                symbols=symbols, optimization_method=optimization_method, **kwargs
            )

            # 3. 驗證目標權重
            is_valid, error_msg = self.optimization._validate_rebalance_config(
                portfolio_id=portfolio_id,
                target_weights=target_weights,
                constraints=constraints,
            )

            if not is_valid:
                return {"success": False, "error": error_msg}

            # 4. 執行交易
            success, trade_error, trade_details = self.optimization._execute_trades(
                portfolio_id=portfolio_id,
                current_weights=current_weights,
                target_weights=target_weights,
                total_value=portfolio.total_value,
            )

            if not success:
                return {"success": False, "error": trade_error}

            # 5. 更新持倉
            new_holdings = []
            for symbol, weight in target_weights.items():
                # 這裡簡化處理，實際應該根據交易結果更新
                market_value = weight * portfolio.total_value
                price = 100.0  # 假設價格，實際應該從市場資料獲取
                quantity = market_value / price

                holding = PortfolioHolding(
                    symbol=symbol,
                    name=symbol,  # 簡化處理
                    quantity=quantity,
                    price=price,
                    market_value=market_value,
                    weight=weight,
                )
                new_holdings.append(holding)

            # 更新資料庫
            update_success = self.database.update_holdings(portfolio_id, new_holdings)

            if update_success:
                # 記錄調整歷史
                self.core._record_adjustment(
                    portfolio_id=portfolio_id,
                    adjustment_type="rebalance",
                    old_weights=current_weights,
                    new_weights=target_weights,
                    reason=f"使用 {optimization_method} 方法進行再平衡",
                )

                return {
                    "success": True,
                    "portfolio_id": portfolio_id,
                    "optimization_method": optimization_method,
                    "old_weights": current_weights,
                    "new_weights": target_weights,
                    "trade_details": trade_details,
                    "rebalance_date": datetime.now().isoformat(),
                }
            else:
                return {"success": False, "error": "更新持倉失敗"}

        except Exception as e:
            logger.error(f"投資組合再平衡錯誤: {e}")
            return {"success": False, "error": f"再平衡失敗: {e}"}

    # ==================== 風險分析功能 ====================

    def calculate_var(
        self,
        portfolio_id: str,
        confidence_level: float = 0.05,
        time_horizon: int = 1,
        method: str = "historical",
    ) -> Dict[str, Any]:
        """計算投資組合 VaR

        Args:
            portfolio_id: 投資組合ID
            confidence_level: 信心水準
            time_horizon: 時間範圍
            method: 計算方法

        Returns:
            VaR 計算結果
        """
        return self.risk_analysis.calculate_var(
            portfolio_id=portfolio_id,
            confidence_level=confidence_level,
            time_horizon=time_horizon,
            method=method,
        )

    def calculate_risk_metrics(
        self, portfolio_id: str, benchmark_returns=None
    ) -> Dict[str, Any]:
        """計算綜合風險指標

        Args:
            portfolio_id: 投資組合ID
            benchmark_returns: 基準收益率

        Returns:
            風險指標字典
        """
        return self.risk_analysis.calculate_risk_metrics(
            portfolio_id=portfolio_id, benchmark_returns=benchmark_returns
        )

    def stress_test(
        self, portfolio_id: str, scenarios: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """投資組合壓力測試

        Args:
            portfolio_id: 投資組合ID
            scenarios: 壓力測試情境

        Returns:
            壓力測試結果
        """
        return self.risk_analysis.stress_test(
            portfolio_id=portfolio_id, scenarios=scenarios
        )

    # ==================== 資料管理功能 ====================

    def get_adjustment_history(self, portfolio_id: str, limit: int = 50) -> List[Dict]:
        """獲取調整歷史

        Args:
            portfolio_id: 投資組合ID
            limit: 限制數量

        Returns:
            調整歷史列表
        """
        return self.database.get_adjustment_history(portfolio_id, limit)

    def export_portfolio_data(
        self, portfolio_id: str, include_history: bool = True
    ) -> Dict[str, Any]:
        """匯出投資組合資料

        Args:
            portfolio_id: 投資組合ID
            include_history: 是否包含歷史記錄

        Returns:
            匯出的資料
        """
        return self.database.export_portfolio_data(portfolio_id, include_history)

    def import_portfolio_data(
        self, import_data: Dict[str, Any], overwrite: bool = False
    ) -> Optional[str]:
        """匯入投資組合資料

        Args:
            import_data: 匯入的資料
            overwrite: 是否覆蓋現有資料

        Returns:
            匯入的投資組合ID
        """
        return self.database.import_portfolio_data(import_data, overwrite)

    def get_portfolio_statistics(self) -> Dict[str, Any]:
        """獲取投資組合統計資訊

        Returns:
            統計資訊字典
        """
        return self.database.get_portfolio_statistics()


# 向後相容性：保留原始的函數介面
def create_portfolio_service(db_path: str = None) -> PortfolioService:
    """創建投資組合服務實例（向後相容函數）

    Args:
        db_path: 資料庫路徑

    Returns:
        投資組合服務實例
    """
    return PortfolioService(db_path)


# 模組版本資訊
__version__ = "2.0.0"
__author__ = "AI Trading System"

# 公開的 API
__all__ = [
    "PortfolioService",
    "PortfolioServiceCore",
    "PortfolioOptimizationService",
    "PortfolioRiskAnalysisService",
    "PortfolioDatabaseService",
    "Portfolio",
    "PortfolioHolding",
    "create_portfolio_service",
]
