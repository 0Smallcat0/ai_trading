"""
部位管理器模組

此模組負責計算最適的部位大小，整合風險管理規則，包括：
- 部位大小計算
- 風險限制檢查
- 資金管理
- 槓桿控制
"""

import logging
from typing import Any, Dict, Optional, Tuple

from .models import ExecutionOrder, ExecutionConfig

# 嘗試導入風險管理模組
try:
    from src.risk_management.position_sizing import (
        PositionSizingStrategy,
        PercentPositionSizing,
        RiskBasedPositionSizing,
        VolatilityPositionSizing,
    )
    from src.risk_management.portfolio_risk import PortfolioRiskManager
    RISK_MANAGEMENT_AVAILABLE = True
except ImportError:
    RISK_MANAGEMENT_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("風險管理模組不可用，將使用簡化的部位計算")

logger = logging.getLogger(__name__)


class PositionManager:
    """部位管理器
    
    負責計算最適的部位大小並進行風險控制。
    
    Attributes:
        config: 執行配置
        position_sizing_strategy: 部位計算策略
        portfolio_risk_manager: 投資組合風險管理器
        current_positions: 當前持倉
    """
    
    def __init__(
        self,
        config: ExecutionConfig,
        portfolio_value: float = 1000000.0,
        position_sizing_strategy: Optional[str] = "percent",
    ):
        """初始化部位管理器
        
        Args:
            config: 執行配置
            portfolio_value: 投資組合價值
            position_sizing_strategy: 部位計算策略類型
        """
        self.config = config
        self.portfolio_value = portfolio_value
        self.current_positions: Dict[str, float] = {}
        
        # 初始化部位計算策略
        self.position_sizing_strategy = self._init_position_sizing_strategy(
            position_sizing_strategy
        )
        
        # 初始化投資組合風險管理器
        if RISK_MANAGEMENT_AVAILABLE:
            self.portfolio_risk_manager = PortfolioRiskManager()
        else:
            self.portfolio_risk_manager = None
        
        logger.info("部位管理器初始化完成，投資組合價值: %f", portfolio_value)
    
    def _init_position_sizing_strategy(
        self, strategy_type: str
    ) -> Optional[PositionSizingStrategy]:
        """初始化部位計算策略
        
        Args:
            strategy_type: 策略類型
            
        Returns:
            Optional[PositionSizingStrategy]: 部位計算策略實例
        """
        if not RISK_MANAGEMENT_AVAILABLE:
            return None
        
        strategy_mapping = {
            "percent": PercentPositionSizing,
            "risk_based": RiskBasedPositionSizing,
            "volatility": VolatilityPositionSizing,
        }
        
        strategy_class = strategy_mapping.get(strategy_type, PercentPositionSizing)
        
        # 使用配置參數初始化策略
        if strategy_type == "percent":
            return strategy_class(percent=0.05)  # 預設 5%
        elif strategy_type == "risk_based":
            return strategy_class(risk_per_trade=0.02)  # 預設 2% 風險
        elif strategy_type == "volatility":
            return strategy_class(base_percent=0.05, volatility_factor=2.0)
        else:
            return strategy_class()
    
    def calculate_position_size(
        self,
        order: ExecutionOrder,
        current_price: Optional[float] = None,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, Dict[str, Any]]:
        """計算部位大小
        
        Args:
            order: 執行訂單
            current_price: 當前價格
            market_data: 市場數據
            
        Returns:
            Tuple[int, Dict[str, Any]]: (計算的數量, 計算詳情)
        """
        try:
            # 如果訂單已有數量且大於 0，直接使用
            if order.quantity and order.quantity > 0:
                # 仍需進行風險檢查
                risk_check = self._check_risk_limits(order, current_price)
                if not risk_check["passed"]:
                    return 0, risk_check
                return order.quantity, {"method": "predefined", "risk_check": risk_check}
            
            # 使用部位計算策略
            if self.position_sizing_strategy:
                quantity = self._calculate_with_strategy(order, current_price, market_data)
            else:
                quantity = self._calculate_simple(order, current_price)
            
            # 風險檢查
            order.quantity = quantity
            risk_check = self._check_risk_limits(order, current_price)
            
            if not risk_check["passed"]:
                return 0, risk_check
            
            # 調整數量以符合風險限制
            adjusted_quantity = self._adjust_for_risk_limits(quantity, order, current_price)
            
            calculation_details = {
                "method": "calculated",
                "original_quantity": quantity,
                "adjusted_quantity": adjusted_quantity,
                "risk_check": risk_check,
                "portfolio_value": self.portfolio_value,
            }
            
            logger.info(
                "部位計算完成 %s: %d -> %d",
                order.symbol,
                quantity,
                adjusted_quantity,
            )
            
            return adjusted_quantity, calculation_details
            
        except Exception as e:
            logger.error("計算部位大小時發生錯誤: %s", e, exc_info=True)
            return 0, {"error": str(e), "passed": False}
    
    def _calculate_with_strategy(
        self,
        order: ExecutionOrder,
        current_price: Optional[float],
        market_data: Optional[Dict[str, Any]],
    ) -> int:
        """使用部位計算策略計算數量
        
        Args:
            order: 執行訂單
            current_price: 當前價格
            market_data: 市場數據
            
        Returns:
            int: 計算的數量
        """
        # 準備策略參數
        kwargs = {}
        
        if market_data:
            kwargs.update(market_data)
        
        if current_price:
            kwargs["current_price"] = current_price
        
        # 計算部位大小（金額）
        position_size = self.position_sizing_strategy.calculate_position_size(
            self.portfolio_value, **kwargs
        )
        
        # 轉換為股數
        price = current_price or order.price or 100.0  # 預設價格
        quantity = int(position_size / price)
        
        return max(quantity, 0)
    
    def _calculate_simple(self, order: ExecutionOrder, current_price: Optional[float]) -> int:
        """簡單部位計算（當風險管理模組不可用時）
        
        Args:
            order: 執行訂單
            current_price: 當前價格
            
        Returns:
            int: 計算的數量
        """
        # 使用固定百分比計算
        position_percent = 0.05  # 5%
        position_size = self.portfolio_value * position_percent
        
        price = current_price or order.price or 100.0
        quantity = int(position_size / price)
        
        return max(quantity, 0)
    
    def _check_risk_limits(
        self, order: ExecutionOrder, current_price: Optional[float]
    ) -> Dict[str, Any]:
        """檢查風險限制
        
        Args:
            order: 執行訂單
            current_price: 當前價格
            
        Returns:
            Dict[str, Any]: 風險檢查結果
        """
        risk_check = {
            "passed": True,
            "reasons": [],
            "limits": {},
        }
        
        try:
            price = current_price or order.price or 100.0
            position_value = order.quantity * price
            
            # 檢查最大部位大小
            if position_value > self.config.max_position_size:
                risk_check["passed"] = False
                risk_check["reasons"].append("超過最大部位大小限制")
                risk_check["limits"]["max_position_size"] = self.config.max_position_size
            
            # 檢查投資組合風險限制
            portfolio_risk = position_value / self.portfolio_value
            if portfolio_risk > self.config.risk_limit:
                risk_check["passed"] = False
                risk_check["reasons"].append("超過投資組合風險限制")
                risk_check["limits"]["risk_limit"] = self.config.risk_limit
            
            # 檢查當前持倉集中度
            current_position = self.current_positions.get(order.symbol, 0)
            new_position = current_position + (
                position_value if order.action == "buy" else -position_value
            )
            concentration = abs(new_position) / self.portfolio_value
            
            max_concentration = 0.2  # 20% 集中度限制
            if concentration > max_concentration:
                risk_check["passed"] = False
                risk_check["reasons"].append("超過持倉集中度限制")
                risk_check["limits"]["max_concentration"] = max_concentration
            
            # 使用投資組合風險管理器進行額外檢查
            if self.portfolio_risk_manager:
                portfolio_check = self._check_portfolio_risk(order, position_value)
                if not portfolio_check["passed"]:
                    risk_check["passed"] = False
                    risk_check["reasons"].extend(portfolio_check["reasons"])
            
        except Exception as e:
            logger.error("風險檢查時發生錯誤: %s", e)
            risk_check["passed"] = False
            risk_check["reasons"].append(f"風險檢查錯誤: {e}")
        
        return risk_check
    
    def _check_portfolio_risk(
        self, order: ExecutionOrder, position_value: float
    ) -> Dict[str, Any]:
        """使用投資組合風險管理器進行檢查
        
        Args:
            order: 執行訂單
            position_value: 部位價值
            
        Returns:
            Dict[str, Any]: 檢查結果
        """
        # 這裡可以整合更複雜的投資組合風險檢查
        # 目前返回通過
        return {"passed": True, "reasons": []}
    
    def _adjust_for_risk_limits(
        self, quantity: int, order: ExecutionOrder, current_price: Optional[float]
    ) -> int:
        """根據風險限制調整數量
        
        Args:
            quantity: 原始數量
            order: 執行訂單
            current_price: 當前價格
            
        Returns:
            int: 調整後的數量
        """
        price = current_price or order.price or 100.0
        position_value = quantity * price
        
        # 調整以符合最大部位大小
        if position_value > self.config.max_position_size:
            quantity = int(self.config.max_position_size / price)
        
        # 調整以符合風險限制
        max_risk_value = self.portfolio_value * self.config.risk_limit
        if position_value > max_risk_value:
            quantity = int(max_risk_value / price)
        
        return max(quantity, 0)
    
    def update_position(self, symbol: str, quantity: int, price: float, action: str):
        """更新持倉記錄
        
        Args:
            symbol: 股票代碼
            quantity: 數量
            price: 價格
            action: 動作
        """
        position_value = quantity * price
        
        if action == "buy":
            self.current_positions[symbol] = (
                self.current_positions.get(symbol, 0) + position_value
            )
        elif action == "sell":
            self.current_positions[symbol] = (
                self.current_positions.get(symbol, 0) - position_value
            )
        
        logger.debug("更新持倉 %s: %f", symbol, self.current_positions[symbol])
    
    def get_current_position(self, symbol: str) -> float:
        """獲取當前持倉
        
        Args:
            symbol: 股票代碼
            
        Returns:
            float: 持倉價值
        """
        return self.current_positions.get(symbol, 0)
    
    def get_portfolio_utilization(self) -> float:
        """獲取投資組合使用率
        
        Returns:
            float: 使用率 (0-1)
        """
        total_position_value = sum(abs(value) for value in self.current_positions.values())
        return total_position_value / self.portfolio_value
    
    def update_portfolio_value(self, new_value: float):
        """更新投資組合價值
        
        Args:
            new_value: 新的投資組合價值
        """
        self.portfolio_value = new_value
        logger.info("投資組合價值更新為: %f", new_value)
