"""
執行優化器模組

此模組負責優化訂單執行，最小化市場衝擊，包括：
- TWAP (時間加權平均價格) 執行
- VWAP (成交量加權平均價格) 執行
- 分批執行策略
- 市場衝擊最小化
"""

import logging
import math
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .models import ExecutionOrder, ExecutionMode, ExecutionConfig

logger = logging.getLogger(__name__)


class ExecutionOptimizer:
    """執行優化器
    
    負責優化大額訂單的執行，減少市場衝擊。
    
    Attributes:
        config: 執行配置
        active_optimizations: 活躍的優化執行
        market_data_provider: 市場數據提供者
    """
    
    def __init__(
        self,
        config: ExecutionConfig,
        market_data_provider: Optional[Any] = None,
    ):
        """初始化執行優化器
        
        Args:
            config: 執行配置
            market_data_provider: 市場數據提供者
        """
        self.config = config
        self.market_data_provider = market_data_provider
        self.active_optimizations: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        
        logger.info("執行優化器初始化完成")
    
    def optimize_execution(
        self,
        order: ExecutionOrder,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> List[ExecutionOrder]:
        """優化訂單執行
        
        Args:
            order: 原始執行訂單
            market_data: 市場數據
            
        Returns:
            List[ExecutionOrder]: 優化後的子訂單列表
        """
        if not self.config.enable_optimization:
            logger.debug("執行優化已停用，直接返回原訂單")
            return [order]
        
        try:
            if order.execution_mode == ExecutionMode.IMMEDIATE:
                return self._immediate_execution(order)
            elif order.execution_mode == ExecutionMode.TWAP:
                return self._twap_execution(order, market_data)
            elif order.execution_mode == ExecutionMode.VWAP:
                return self._vwap_execution(order, market_data)
            elif order.execution_mode == ExecutionMode.BATCH:
                return self._batch_execution(order, market_data)
            else:
                logger.warning("未知的執行模式: %s", order.execution_mode)
                return [order]
                
        except Exception as e:
            logger.error("執行優化時發生錯誤: %s", e, exc_info=True)
            return [order]  # 發生錯誤時返回原訂單
    
    def _immediate_execution(self, order: ExecutionOrder) -> List[ExecutionOrder]:
        """立即執行模式
        
        Args:
            order: 執行訂單
            
        Returns:
            List[ExecutionOrder]: 子訂單列表
        """
        # 檢查是否需要分批
        if order.quantity > self.config.batch_size:
            return self._split_large_order(order)
        else:
            return [order]
    
    def _twap_execution(
        self,
        order: ExecutionOrder,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> List[ExecutionOrder]:
        """TWAP 執行模式
        
        Args:
            order: 執行訂單
            market_data: 市場數據
            
        Returns:
            List[ExecutionOrder]: 時間分散的子訂單列表
        """
        duration_minutes = self.config.twap_duration
        interval_minutes = 5  # 每5分鐘執行一次
        
        num_slices = max(1, duration_minutes // interval_minutes)
        slice_quantity = order.quantity // num_slices
        remaining_quantity = order.quantity % num_slices
        
        sub_orders = []
        current_time = datetime.now()
        
        for i in range(num_slices):
            # 計算每個切片的數量
            quantity = slice_quantity
            if i == num_slices - 1:  # 最後一個切片包含剩餘數量
                quantity += remaining_quantity
            
            # 創建子訂單
            sub_order = self._create_sub_order(
                order,
                quantity,
                f"{order.order_id}_twap_{i}",
                current_time + timedelta(minutes=i * interval_minutes),
            )
            sub_orders.append(sub_order)
        
        logger.info(
            "TWAP 執行計劃 %s: %d 個子訂單，持續 %d 分鐘",
            order.symbol,
            len(sub_orders),
            duration_minutes,
        )
        
        return sub_orders
    
    def _vwap_execution(
        self,
        order: ExecutionOrder,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> List[ExecutionOrder]:
        """VWAP 執行模式
        
        Args:
            order: 執行訂單
            market_data: 市場數據
            
        Returns:
            List[ExecutionOrder]: 成交量加權的子訂單列表
        """
        # 獲取歷史成交量分佈
        volume_profile = self._get_volume_profile(order.symbol, market_data)
        
        if not volume_profile:
            logger.warning("無法獲取成交量分佈，使用 TWAP 模式")
            return self._twap_execution(order, market_data)
        
        sub_orders = []
        current_time = datetime.now()
        
        for i, (time_slot, volume_weight) in enumerate(volume_profile):
            # 根據成交量權重計算數量
            quantity = int(order.quantity * volume_weight)
            
            if quantity > 0:
                sub_order = self._create_sub_order(
                    order,
                    quantity,
                    f"{order.order_id}_vwap_{i}",
                    current_time + time_slot,
                )
                sub_orders.append(sub_order)
        
        # 確保總數量正確
        total_allocated = sum(sub_order.quantity for sub_order in sub_orders)
        if total_allocated != order.quantity:
            # 調整最後一個訂單的數量
            if sub_orders:
                sub_orders[-1].quantity += order.quantity - total_allocated
        
        logger.info(
            "VWAP 執行計劃 %s: %d 個子訂單",
            order.symbol,
            len(sub_orders),
        )
        
        return sub_orders
    
    def _batch_execution(
        self,
        order: ExecutionOrder,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> List[ExecutionOrder]:
        """分批執行模式
        
        Args:
            order: 執行訂單
            market_data: 市場數據
            
        Returns:
            List[ExecutionOrder]: 分批的子訂單列表
        """
        batch_size = self.config.batch_size
        num_batches = math.ceil(order.quantity / batch_size)
        
        sub_orders = []
        current_time = datetime.now()
        
        for i in range(num_batches):
            # 計算批次數量
            start_qty = i * batch_size
            end_qty = min((i + 1) * batch_size, order.quantity)
            quantity = end_qty - start_qty
            
            # 計算執行時間（間隔30秒）
            execution_time = current_time + timedelta(seconds=i * 30)
            
            sub_order = self._create_sub_order(
                order,
                quantity,
                f"{order.order_id}_batch_{i}",
                execution_time,
            )
            sub_orders.append(sub_order)
        
        logger.info(
            "分批執行計劃 %s: %d 個批次",
            order.symbol,
            num_batches,
        )
        
        return sub_orders
    
    def _split_large_order(self, order: ExecutionOrder) -> List[ExecutionOrder]:
        """分割大額訂單
        
        Args:
            order: 大額訂單
            
        Returns:
            List[ExecutionOrder]: 分割後的子訂單列表
        """
        max_size = self.config.batch_size
        num_splits = math.ceil(order.quantity / max_size)
        
        sub_orders = []
        
        for i in range(num_splits):
            start_qty = i * max_size
            end_qty = min((i + 1) * max_size, order.quantity)
            quantity = end_qty - start_qty
            
            sub_order = self._create_sub_order(
                order,
                quantity,
                f"{order.order_id}_split_{i}",
            )
            sub_orders.append(sub_order)
        
        logger.info(
            "大額訂單分割 %s: %d -> %d 個子訂單",
            order.symbol,
            order.quantity,
            len(sub_orders),
        )
        
        return sub_orders
    
    def _create_sub_order(
        self,
        parent_order: ExecutionOrder,
        quantity: int,
        sub_order_id: str,
        execution_time: Optional[datetime] = None,
    ) -> ExecutionOrder:
        """創建子訂單
        
        Args:
            parent_order: 父訂單
            quantity: 子訂單數量
            sub_order_id: 子訂單ID
            execution_time: 執行時間
            
        Returns:
            ExecutionOrder: 子訂單
        """
        sub_order = ExecutionOrder(
            order_id=sub_order_id,
            symbol=parent_order.symbol,
            action=parent_order.action,
            quantity=quantity,
            order_type=parent_order.order_type,
            price=parent_order.price,
            stop_price=parent_order.stop_price,
            execution_mode=ExecutionMode.IMMEDIATE,  # 子訂單使用立即執行
            created_at=execution_time or datetime.now(),
            signal_id=parent_order.signal_id,
            strategy_name=parent_order.strategy_name,
            risk_params=parent_order.risk_params.copy(),
        )
        
        # 添加父訂單資訊
        sub_order.risk_params["parent_order_id"] = parent_order.order_id
        sub_order.risk_params["is_sub_order"] = True
        
        return sub_order
    
    def _get_volume_profile(
        self,
        symbol: str,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[timedelta, float]]:
        """獲取成交量分佈
        
        Args:
            symbol: 股票代碼
            market_data: 市場數據
            
        Returns:
            List[Tuple[timedelta, float]]: (時間偏移, 成交量權重) 列表
        """
        # 簡化的成交量分佈模型
        # 實際應用中應該使用歷史數據分析
        
        if market_data and "volume_profile" in market_data:
            return market_data["volume_profile"]
        
        # 預設的成交量分佈（基於一般市場規律）
        default_profile = [
            (timedelta(minutes=0), 0.15),    # 開盤
            (timedelta(minutes=30), 0.10),   # 開盤後30分鐘
            (timedelta(minutes=60), 0.08),   # 開盤後1小時
            (timedelta(minutes=120), 0.12),  # 午盤前
            (timedelta(minutes=210), 0.10),  # 午盤後
            (timedelta(minutes=270), 0.15),  # 收盤前1小時
            (timedelta(minutes=300), 0.20),  # 收盤前30分鐘
            (timedelta(minutes=330), 0.10),  # 收盤
        ]
        
        return default_profile
    
    def estimate_market_impact(
        self,
        symbol: str,
        quantity: int,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> float:
        """估算市場衝擊
        
        Args:
            symbol: 股票代碼
            quantity: 交易數量
            market_data: 市場數據
            
        Returns:
            float: 預估市場衝擊（基點）
        """
        try:
            # 獲取平均日成交量
            avg_daily_volume = self._get_average_daily_volume(symbol, market_data)
            
            if avg_daily_volume <= 0:
                return 0.0
            
            # 計算成交量比例
            volume_ratio = quantity / avg_daily_volume
            
            # 簡化的市場衝擊模型：衝擊 = sqrt(成交量比例) * 基礎衝擊
            base_impact = 10.0  # 基礎衝擊（基點）
            market_impact = math.sqrt(volume_ratio) * base_impact
            
            logger.debug(
                "市場衝擊估算 %s: 數量=%d, 日均量=%d, 比例=%.4f, 衝擊=%.2f bps",
                symbol,
                quantity,
                avg_daily_volume,
                volume_ratio,
                market_impact,
            )
            
            return market_impact
            
        except Exception as e:
            logger.error("估算市場衝擊時發生錯誤: %s", e)
            return 0.0
    
    def _get_average_daily_volume(
        self,
        symbol: str,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> int:
        """獲取平均日成交量
        
        Args:
            symbol: 股票代碼
            market_data: 市場數據
            
        Returns:
            int: 平均日成交量
        """
        if market_data and "avg_daily_volume" in market_data:
            return market_data["avg_daily_volume"]
        
        # 如果有市場數據提供者，從中獲取
        if self.market_data_provider:
            try:
                return self.market_data_provider.get_average_daily_volume(symbol)
            except Exception as e:
                logger.warning("從市場數據提供者獲取成交量失敗: %s", e)
        
        # 預設值（應該根據實際股票調整）
        return 1000000  # 100萬股
    
    def get_optimization_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """獲取優化狀態
        
        Args:
            order_id: 訂單ID
            
        Returns:
            Optional[Dict[str, Any]]: 優化狀態資訊
        """
        with self._lock:
            return self.active_optimizations.get(order_id)
    
    def cancel_optimization(self, order_id: str) -> bool:
        """取消優化執行
        
        Args:
            order_id: 訂單ID
            
        Returns:
            bool: 是否成功取消
        """
        with self._lock:
            if order_id in self.active_optimizations:
                self.active_optimizations[order_id]["cancelled"] = True
                logger.info("取消優化執行: %s", order_id)
                return True
        
        return False
