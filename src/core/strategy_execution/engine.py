"""
策略執行引擎主控制器

此模組是策略實盤執行引擎的核心，負責協調所有子模組，包括：
- 策略訊號處理
- 部位大小計算
- 執行優化
- 狀態監控
- 風險控制
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from .models import (
    ExecutionConfig,
    ExecutionOrder,
    ExecutionResult,
    SignalData,
    TradingSignal,
)
from .signal_processor import SignalProcessor
from .position_manager import PositionManager
from .execution_tracker import ExecutionTracker
from .execution_optimizer import ExecutionOptimizer

# 嘗試導入相關模組
try:
    from src.execution.order_manager import OrderManager
    from src.execution.broker_base import Order, OrderType
    from src.core.trade_execution_service import TradeExecutionService
    EXECUTION_AVAILABLE = True
except ImportError:
    EXECUTION_AVAILABLE = False

logger = logging.getLogger(__name__)


class StrategyExecutionEngine:
    """策略執行引擎
    
    負責將策略訊號轉換為實際的交易執行，整合所有執行相關功能。
    
    Attributes:
        config: 執行配置
        signal_processor: 訊號處理器
        position_manager: 部位管理器
        execution_tracker: 執行追蹤器
        execution_optimizer: 執行優化器
        order_manager: 訂單管理器
        trade_service: 交易執行服務
    """
    
    def __init__(
        self,
        config: Optional[ExecutionConfig] = None,
        portfolio_value: float = 1000000.0,
        order_manager: Optional[OrderManager] = None,
        trade_service: Optional[TradeExecutionService] = None,
    ):
        """初始化策略執行引擎
        
        Args:
            config: 執行配置
            portfolio_value: 投資組合價值
            order_manager: 訂單管理器
            trade_service: 交易執行服務
        """
        self.config = config or ExecutionConfig()
        self.portfolio_value = portfolio_value
        
        # 初始化子模組
        self.signal_processor = SignalProcessor()
        self.position_manager = PositionManager(self.config, portfolio_value)
        self.execution_tracker = ExecutionTracker(order_manager)
        self.execution_optimizer = ExecutionOptimizer(self.config)
        
        # 外部服務
        self.order_manager = order_manager
        self.trade_service = trade_service
        
        # 執行統計
        self.execution_stats = {
            "total_signals": 0,
            "processed_signals": 0,
            "executed_orders": 0,
            "failed_orders": 0,
        }
        
        logger.info("策略執行引擎初始化完成")
    
    def execute_strategy_signal(
        self,
        signal_data: SignalData,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """執行策略訊號
        
        Args:
            signal_data: 策略訊號數據
            market_data: 市場數據
            
        Returns:
            Dict[str, Any]: 執行結果
        """
        execution_id = str(uuid.uuid4())
        
        try:
            self.execution_stats["total_signals"] += 1
            
            logger.info("開始執行策略訊號: %s", execution_id)
            
            # 1. 處理訊號
            order = self.signal_processor.process_signal(signal_data)
            if not order:
                return self._create_result(
                    execution_id, False, "訊號處理失敗或被過濾"
                )
            
            self.execution_stats["processed_signals"] += 1
            
            # 2. 計算部位大小
            current_price = self._get_current_price(order.symbol, market_data)
            quantity, position_details = self.position_manager.calculate_position_size(
                order, current_price, market_data
            )
            
            if quantity <= 0:
                return self._create_result(
                    execution_id,
                    False,
                    f"部位計算失敗: {position_details.get('error', '數量為0')}",
                    {"position_details": position_details},
                )
            
            # 更新訂單數量
            order.quantity = quantity
            
            # 3. 執行優化
            optimized_orders = self.execution_optimizer.optimize_execution(
                order, market_data
            )
            
            # 4. 執行訂單
            execution_results = []
            for opt_order in optimized_orders:
                result = self._execute_single_order(opt_order, market_data)
                execution_results.append(result)
                
                if result["success"]:
                    self.execution_stats["executed_orders"] += 1
                else:
                    self.execution_stats["failed_orders"] += 1
            
            # 5. 更新持倉記錄
            if any(r["success"] for r in execution_results):
                self.position_manager.update_position(
                    order.symbol, quantity, current_price or 0, order.action
                )
            
            # 6. 生成執行報告
            success = any(r["success"] for r in execution_results)
            message = "執行完成" if success else "執行失敗"
            
            return self._create_result(
                execution_id,
                success,
                message,
                {
                    "original_signal": signal_data,
                    "processed_order": order.__dict__,
                    "position_details": position_details,
                    "optimized_orders": len(optimized_orders),
                    "execution_results": execution_results,
                    "current_price": current_price,
                },
            )
            
        except Exception as e:
            logger.error("執行策略訊號時發生錯誤: %s", e, exc_info=True)
            self.execution_stats["failed_orders"] += 1
            return self._create_result(
                execution_id, False, f"執行錯誤: {e}"
            )
    
    def execute_signals_batch(
        self,
        signals: List[SignalData],
        market_data: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """批量執行策略訊號
        
        Args:
            signals: 策略訊號列表
            market_data: 市場數據
            
        Returns:
            List[Dict[str, Any]]: 執行結果列表
        """
        results = []
        
        logger.info("開始批量執行 %d 個策略訊號", len(signals))
        
        for signal in signals:
            result = self.execute_strategy_signal(signal, market_data)
            results.append(result)
        
        logger.info("批量執行完成，成功: %d, 失敗: %d",
                   sum(1 for r in results if r["success"]),
                   sum(1 for r in results if not r["success"]))
        
        return results
    
    def _execute_single_order(
        self,
        order: ExecutionOrder,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """執行單個訂單
        
        Args:
            order: 執行訂單
            market_data: 市場數據
            
        Returns:
            Dict[str, Any]: 執行結果
        """
        try:
            # 開始追蹤訂單
            self.execution_tracker.track_order(order)
            
            # 如果是模擬模式
            if self.config.dry_run:
                return self._simulate_order_execution(order)
            
            # 實際執行訂單
            if self.trade_service and EXECUTION_AVAILABLE:
                return self._execute_with_trade_service(order)
            elif self.order_manager and EXECUTION_AVAILABLE:
                return self._execute_with_order_manager(order)
            else:
                logger.warning("沒有可用的執行服務，使用模擬模式")
                return self._simulate_order_execution(order)
                
        except Exception as e:
            logger.error("執行訂單 %s 時發生錯誤: %s", order.order_id, e)
            return {
                "success": False,
                "order_id": order.order_id,
                "error": str(e),
                "timestamp": datetime.now(),
            }
    
    def _execute_with_trade_service(self, order: ExecutionOrder) -> Dict[str, Any]:
        """使用交易執行服務執行訂單
        
        Args:
            order: 執行訂單
            
        Returns:
            Dict[str, Any]: 執行結果
        """
        # 轉換為交易服務格式
        order_data = {
            "symbol": order.symbol,
            "action": order.action,
            "quantity": order.quantity,
            "order_type": order.order_type,
            "price": order.price,
            "stop_price": order.stop_price,
            "strategy_name": order.strategy_name,
            "signal_id": order.signal_id,
        }
        
        success, message, trade_order_id = self.trade_service.submit_order(order_data)
        
        return {
            "success": success,
            "order_id": order.order_id,
            "trade_order_id": trade_order_id,
            "message": message,
            "timestamp": datetime.now(),
        }
    
    def _execute_with_order_manager(self, order: ExecutionOrder) -> Dict[str, Any]:
        """使用訂單管理器執行訂單
        
        Args:
            order: 執行訂單
            
        Returns:
            Dict[str, Any]: 執行結果
        """
        # 創建券商訂單
        broker_order = Order(
            stock_id=order.symbol,
            action=order.action,
            quantity=order.quantity,
            order_type=OrderType(order.order_type),
            price=order.price,
            stop_price=order.stop_price,
        )
        broker_order.order_id = order.order_id
        
        submitted_order_id = self.order_manager.submit_order(broker_order)
        
        success = submitted_order_id is not None
        
        return {
            "success": success,
            "order_id": order.order_id,
            "submitted_order_id": submitted_order_id,
            "message": "訂單提交成功" if success else "訂單提交失敗",
            "timestamp": datetime.now(),
        }
    
    def _simulate_order_execution(self, order: ExecutionOrder) -> Dict[str, Any]:
        """模擬訂單執行
        
        Args:
            order: 執行訂單
            
        Returns:
            Dict[str, Any]: 模擬執行結果
        """
        logger.info("模擬執行訂單: %s %s %d@%s",
                   order.symbol, order.action, order.quantity, order.price)
        
        # 模擬成功執行
        return {
            "success": True,
            "order_id": order.order_id,
            "message": "模擬執行成功",
            "simulated": True,
            "timestamp": datetime.now(),
        }
    
    def _get_current_price(
        self,
        symbol: str,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[float]:
        """獲取當前價格
        
        Args:
            symbol: 股票代碼
            market_data: 市場數據
            
        Returns:
            Optional[float]: 當前價格
        """
        if market_data and "prices" in market_data:
            return market_data["prices"].get(symbol)
        
        # 這裡應該整合實際的市場數據服務
        # 目前返回 None，讓部位管理器使用訂單中的價格
        return None
    
    def _create_result(
        self,
        execution_id: str,
        success: bool,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """創建執行結果
        
        Args:
            execution_id: 執行ID
            success: 是否成功
            message: 結果訊息
            data: 額外數據
            
        Returns:
            Dict[str, Any]: 執行結果
        """
        return {
            "execution_id": execution_id,
            "success": success,
            "message": message,
            "timestamp": datetime.now(),
            "data": data or {},
        }
    
    def get_execution_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """獲取執行狀態
        
        Args:
            order_id: 訂單ID
            
        Returns:
            Optional[Dict[str, Any]]: 執行狀態
        """
        return self.execution_tracker.get_order_status(order_id)
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """獲取執行統計
        
        Returns:
            Dict[str, Any]: 執行統計資訊
        """
        tracker_stats = self.execution_tracker.get_execution_statistics()
        
        return {
            "engine_stats": self.execution_stats.copy(),
            "tracker_stats": tracker_stats,
            "portfolio_utilization": self.position_manager.get_portfolio_utilization(),
            "portfolio_value": self.portfolio_value,
        }
    
    def start_monitoring(self):
        """開始監控"""
        self.execution_tracker.start_monitoring()
        logger.info("策略執行引擎監控已啟動")
    
    def stop_monitoring(self):
        """停止監控"""
        self.execution_tracker.stop_monitoring()
        logger.info("策略執行引擎監控已停止")
    
    def update_config(self, new_config: ExecutionConfig):
        """更新配置
        
        Args:
            new_config: 新的執行配置
        """
        self.config = new_config
        logger.info("執行配置已更新")
    
    def update_portfolio_value(self, new_value: float):
        """更新投資組合價值
        
        Args:
            new_value: 新的投資組合價值
        """
        self.portfolio_value = new_value
        self.position_manager.update_portfolio_value(new_value)
        logger.info("投資組合價值已更新為: %f", new_value)
