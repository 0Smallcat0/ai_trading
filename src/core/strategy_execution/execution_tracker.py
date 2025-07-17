"""
執行追蹤器模組

此模組負責監控訂單執行狀態和成交情況，包括：
- 訂單狀態實時追蹤
- 成交確認處理
- 滑點分析
- 執行品質評估
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable

from .models import (
    ExecutionOrder,
    ExecutionResult,
    ExecutionStatus,
    SlippageAnalysis,
)

# 嘗試導入執行模組
try:
    from src.execution.broker_base import Order, OrderStatus
    from src.execution.order_manager import OrderManager
    EXECUTION_AVAILABLE = True
except ImportError:
    EXECUTION_AVAILABLE = False

logger = logging.getLogger(__name__)


class ExecutionTracker:
    """執行追蹤器
    
    負責監控訂單執行狀態並分析執行品質。
    
    Attributes:
        order_manager: 訂單管理器
        active_orders: 活躍訂單字典
        execution_results: 執行結果列表
        callbacks: 回調函數列表
        monitoring_thread: 監控線程
    """
    
    def __init__(
        self,
        order_manager: Optional[OrderManager] = None,
        monitoring_interval: float = 1.0,
    ):
        """初始化執行追蹤器
        
        Args:
            order_manager: 訂單管理器
            monitoring_interval: 監控間隔（秒）
        """
        self.order_manager = order_manager
        self.monitoring_interval = monitoring_interval
        
        # 訂單追蹤
        self.active_orders: Dict[str, ExecutionOrder] = {}
        self.execution_results: List[ExecutionResult] = []
        
        # 回調函數
        self.callbacks: List[Callable] = []
        
        # 監控線程
        self.monitoring_thread: Optional[threading.Thread] = None
        self.monitoring_active = False
        self._lock = threading.Lock()
        
        logger.info("執行追蹤器初始化完成")
    
    def start_monitoring(self):
        """開始監控"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            logger.warning("監控已在運行中")
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
        )
        self.monitoring_thread.start()
        logger.info("開始執行監控")
    
    def stop_monitoring(self):
        """停止監控"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5.0)
        logger.info("停止執行監控")
    
    def track_order(self, order: ExecutionOrder) -> str:
        """開始追蹤訂單
        
        Args:
            order: 執行訂單
            
        Returns:
            str: 追蹤ID
        """
        with self._lock:
            self.active_orders[order.order_id] = order
        
        logger.info("開始追蹤訂單: %s", order.order_id)
        return order.order_id
    
    def update_order_status(
        self,
        order_id: str,
        status: ExecutionStatus,
        filled_quantity: int = 0,
        filled_price: Optional[float] = None,
        error_message: Optional[str] = None,
    ):
        """更新訂單狀態
        
        Args:
            order_id: 訂單ID
            status: 執行狀態
            filled_quantity: 已成交數量
            filled_price: 成交價格
            error_message: 錯誤訊息
        """
        with self._lock:
            if order_id not in self.active_orders:
                logger.warning("未找到追蹤的訂單: %s", order_id)
                return
            
            order = self.active_orders[order_id]
            
            # 創建執行結果
            result = ExecutionResult(
                execution_id=f"{order_id}_{int(time.time())}",
                order_id=order_id,
                status=status,
                filled_quantity=filled_quantity,
                filled_price=filled_price,
                execution_time=datetime.now(),
                error_message=error_message,
            )
            
            # 計算滑點
            if filled_price and order.price:
                result.slippage = self._calculate_slippage(
                    order.price, filled_price, order.action
                )
            
            # 計算手續費（簡化計算）
            if filled_quantity and filled_price:
                result.commission = self._calculate_commission(
                    filled_quantity, filled_price
                )
            
            self.execution_results.append(result)
            
            # 如果訂單完成，從活躍列表中移除
            if status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
                del self.active_orders[order_id]
            
            # 觸發回調
            self._trigger_callbacks(order, result)
            
            logger.info(
                "訂單狀態更新 %s: %s, 成交: %d@%s",
                order_id,
                status.value,
                filled_quantity,
                filled_price,
            )
    
    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """獲取訂單狀態
        
        Args:
            order_id: 訂單ID
            
        Returns:
            Optional[Dict[str, Any]]: 訂單狀態資訊
        """
        with self._lock:
            if order_id in self.active_orders:
                order = self.active_orders[order_id]
                return {
                    "order_id": order_id,
                    "symbol": order.symbol,
                    "status": "active",
                    "created_at": order.created_at,
                }
            
            # 查找執行結果
            for result in reversed(self.execution_results):
                if result.order_id == order_id:
                    return {
                        "order_id": order_id,
                        "status": result.status.value,
                        "filled_quantity": result.filled_quantity,
                        "filled_price": result.filled_price,
                        "execution_time": result.execution_time,
                        "slippage": result.slippage,
                        "commission": result.commission,
                        "error_message": result.error_message,
                    }
        
        return None
    
    def analyze_slippage(
        self,
        symbol: str,
        expected_price: float,
        actual_price: float,
        execution_time_ms: float,
        volume_ratio: float = 0.0,
    ) -> SlippageAnalysis:
        """分析滑點
        
        Args:
            symbol: 股票代碼
            expected_price: 預期價格
            actual_price: 實際價格
            execution_time_ms: 執行時間（毫秒）
            volume_ratio: 成交量比例
            
        Returns:
            SlippageAnalysis: 滑點分析結果
        """
        # 計算滑點（基點）
        slippage_bps = abs(actual_price - expected_price) / expected_price * 10000
        
        # 估算市場衝擊（簡化計算）
        market_impact_bps = volume_ratio * 10  # 假設每1%成交量造成1基點衝擊
        
        analysis = SlippageAnalysis(
            symbol=symbol,
            expected_price=expected_price,
            actual_price=actual_price,
            slippage_bps=slippage_bps,
            market_impact_bps=market_impact_bps,
            execution_time_ms=execution_time_ms,
            volume_ratio=volume_ratio,
        )
        
        logger.info(
            "滑點分析 %s: %.2f bps, 市場衝擊: %.2f bps",
            symbol,
            slippage_bps,
            market_impact_bps,
        )
        
        return analysis
    
    def get_execution_statistics(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """獲取執行統計
        
        Args:
            symbol: 股票代碼（可選，用於過濾）
            
        Returns:
            Dict[str, Any]: 執行統計資訊
        """
        with self._lock:
            results = self.execution_results
            
            if symbol:
                # 需要從訂單中獲取symbol資訊
                results = [
                    r for r in results
                    if any(
                        o.symbol == symbol and o.order_id == r.order_id
                        for o in self.active_orders.values()
                    )
                ]
            
            if not results:
                return {"total_orders": 0}
            
            # 計算統計指標
            total_orders = len(results)
            completed_orders = len([r for r in results if r.status == ExecutionStatus.COMPLETED])
            failed_orders = len([r for r in results if r.status == ExecutionStatus.FAILED])
            
            # 滑點統計
            slippages = [r.slippage for r in results if r.slippage is not None]
            avg_slippage = sum(slippages) / len(slippages) if slippages else 0
            
            # 手續費統計
            commissions = [r.commission for r in results if r.commission is not None]
            total_commission = sum(commissions)
            
            return {
                "total_orders": total_orders,
                "completed_orders": completed_orders,
                "failed_orders": failed_orders,
                "success_rate": completed_orders / total_orders if total_orders > 0 else 0,
                "average_slippage": avg_slippage,
                "total_commission": total_commission,
                "average_commission": total_commission / len(commissions) if commissions else 0,
            }
    
    def add_callback(self, callback: Callable):
        """添加回調函數
        
        Args:
            callback: 回調函數，接收 (order, result) 參數
        """
        self.callbacks.append(callback)
        logger.debug("添加回調函數: %s", callback.__name__)
    
    def _monitoring_loop(self):
        """監控循環"""
        logger.info("開始執行監控循環")
        
        while self.monitoring_active:
            try:
                self._check_order_updates()
                time.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error("監控循環錯誤: %s", e, exc_info=True)
                time.sleep(self.monitoring_interval)
        
        logger.info("執行監控循環結束")
    
    def _check_order_updates(self):
        """檢查訂單更新"""
        if not self.order_manager or not EXECUTION_AVAILABLE:
            return
        
        with self._lock:
            for order_id, order in list(self.active_orders.items()):
                try:
                    # 從訂單管理器獲取狀態更新
                    # 這裡需要根據實際的訂單管理器API進行調整
                    broker_order = self.order_manager.get_order(order_id)
                    if broker_order:
                        self._process_broker_order_update(order, broker_order)
                except Exception as e:
                    logger.error("檢查訂單 %s 更新時錯誤: %s", order_id, e)
    
    def _process_broker_order_update(self, order: ExecutionOrder, broker_order: Order):
        """處理券商訂單更新
        
        Args:
            order: 執行訂單
            broker_order: 券商訂單
        """
        # 將券商訂單狀態映射到執行狀態
        status_mapping = {
            OrderStatus.PENDING: ExecutionStatus.PENDING,
            OrderStatus.SUBMITTED: ExecutionStatus.PROCESSING,
            OrderStatus.FILLED: ExecutionStatus.COMPLETED,
            OrderStatus.PARTIALLY_FILLED: ExecutionStatus.PROCESSING,
            OrderStatus.CANCELLED: ExecutionStatus.CANCELLED,
            OrderStatus.REJECTED: ExecutionStatus.FAILED,
            OrderStatus.EXPIRED: ExecutionStatus.FAILED,
        }
        
        execution_status = status_mapping.get(broker_order.status, ExecutionStatus.PENDING)
        
        self.update_order_status(
            order.order_id,
            execution_status,
            broker_order.filled_quantity,
            broker_order.filled_price,
            broker_order.error_message,
        )
    
    def _calculate_slippage(self, expected_price: float, actual_price: float, action: str) -> float:
        """計算滑點
        
        Args:
            expected_price: 預期價格
            actual_price: 實際價格
            action: 交易動作
            
        Returns:
            float: 滑點（百分比）
        """
        if action == "buy":
            # 買入時，實際價格高於預期為負滑點
            return (actual_price - expected_price) / expected_price
        else:
            # 賣出時，實際價格低於預期為負滑點
            return (expected_price - actual_price) / expected_price
    
    def _calculate_commission(self, quantity: int, price: float) -> float:
        """計算手續費（簡化）
        
        Args:
            quantity: 數量
            price: 價格
            
        Returns:
            float: 手續費
        """
        # 簡化的手續費計算：0.1425%
        trade_value = quantity * price
        return trade_value * 0.001425
    
    def _trigger_callbacks(self, order: ExecutionOrder, result: ExecutionResult):
        """觸發回調函數
        
        Args:
            order: 執行訂單
            result: 執行結果
        """
        for callback in self.callbacks:
            try:
                callback(order, result)
            except Exception as e:
                logger.error("回調函數執行錯誤: %s", e, exc_info=True)
