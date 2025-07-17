"""
訂單執行狀態追蹤系統

此模組提供完整的訂單執行狀態追蹤功能，包括：
- 訂單生命週期管理
- 狀態同步
- 執行統計
- 異常監控
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field

from .broker_base import Order, OrderStatus

# 設定日誌
logger = logging.getLogger("execution.order_tracker")


class OrderEvent(Enum):
    """訂單事件枚舉"""
    CREATED = "created"
    SUBMITTED = "submitted"
    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ERROR = "error"


@dataclass
class OrderTrackingInfo:
    """訂單追蹤資訊"""
    order: Order
    broker_name: str
    broker_order_id: Optional[str] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    avg_fill_price: float = 0.0
    commission: float = 0.0
    created_time: datetime = field(default_factory=datetime.now)
    updated_time: datetime = field(default_factory=datetime.now)
    events: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None
    
    def add_event(self, event: OrderEvent, message: str = "", **kwargs):
        """添加訂單事件"""
        event_data = {
            'event': event.value,
            'message': message,
            'timestamp': datetime.now(),
            **kwargs
        }
        self.events.append(event_data)
        self.updated_time = datetime.now()


class OrderTracker:
    """訂單執行狀態追蹤器"""
    
    def __init__(
        self,
        cleanup_interval: int = 3600,  # 1 小時
        max_history_days: int = 30,
    ):
        """
        初始化訂單追蹤器
        
        Args:
            cleanup_interval (int): 清理間隔 (秒)
            max_history_days (int): 最大歷史記錄天數
        """
        self.cleanup_interval = cleanup_interval
        self.max_history_days = max_history_days
        
        # 訂單追蹤資訊
        self.tracking_orders: Dict[str, OrderTrackingInfo] = {}
        self.completed_orders: Dict[str, OrderTrackingInfo] = {}
        
        # 統計資訊
        self.stats = {
            'total_orders': 0,
            'filled_orders': 0,
            'cancelled_orders': 0,
            'rejected_orders': 0,
            'error_orders': 0,
            'total_volume': 0.0,
            'total_commission': 0.0,
        }
        
        # 回調函數
        self.on_order_update: Optional[Callable] = None
        self.on_order_filled: Optional[Callable] = None
        self.on_order_error: Optional[Callable] = None
        
        # 清理線程
        self._cleanup_thread = None
        self._running = False
        self._lock = threading.Lock()
    
    def start_tracking(self):
        """開始追蹤"""
        if self._running:
            logger.warning("訂單追蹤已經在運行")
            return
            
        self._running = True
        
        # 啟動清理線程
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="OrderTracker"
        )
        self._cleanup_thread.start()
        
        logger.info("訂單追蹤已啟動")
    
    def stop_tracking(self):
        """停止追蹤"""
        self._running = False
        
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
            
        logger.info("訂單追蹤已停止")
    
    def track_order(self, order: Order, broker_name: str, broker_order_id: Optional[str] = None):
        """
        開始追蹤訂單
        
        Args:
            order (Order): 訂單物件
            broker_name (str): 券商名稱
            broker_order_id (str, optional): 券商訂單 ID
        """
        with self._lock:
            tracking_info = OrderTrackingInfo(
                order=order,
                broker_name=broker_name,
                broker_order_id=broker_order_id,
            )
            tracking_info.add_event(OrderEvent.CREATED, "訂單已創建")
            
            self.tracking_orders[order.order_id] = tracking_info
            self.stats['total_orders'] += 1
            
        logger.info(f"開始追蹤訂單: {order.order_id}")
        
        # 調用回調函數
        if self.on_order_update:
            self.on_order_update(order.order_id, tracking_info)
    
    def update_order_status(
        self,
        order_id: str,
        status: OrderStatus,
        filled_quantity: float = 0.0,
        avg_fill_price: float = 0.0,
        commission: float = 0.0,
        message: str = "",
    ):
        """
        更新訂單狀態
        
        Args:
            order_id (str): 訂單 ID
            status (OrderStatus): 新狀態
            filled_quantity (float): 已成交數量
            avg_fill_price (float): 平均成交價格
            commission (float): 佣金
            message (str): 狀態訊息
        """
        with self._lock:
            if order_id not in self.tracking_orders:
                logger.warning(f"找不到追蹤中的訂單: {order_id}")
                return
                
            tracking_info = self.tracking_orders[order_id]
            old_status = tracking_info.status
            
            # 更新狀態
            tracking_info.status = status
            tracking_info.filled_quantity = filled_quantity
            tracking_info.avg_fill_price = avg_fill_price
            tracking_info.commission = commission
            tracking_info.updated_time = datetime.now()
            
            # 添加事件
            if status == OrderStatus.PENDING:
                tracking_info.add_event(OrderEvent.PENDING, message)
            elif status == OrderStatus.PARTIALLY_FILLED:
                tracking_info.add_event(
                    OrderEvent.PARTIALLY_FILLED,
                    f"部分成交: {filled_quantity}/{tracking_info.order.quantity}",
                    filled_quantity=filled_quantity,
                    avg_fill_price=avg_fill_price,
                )
            elif status == OrderStatus.FILLED:
                tracking_info.add_event(
                    OrderEvent.FILLED,
                    f"完全成交: {filled_quantity}",
                    filled_quantity=filled_quantity,
                    avg_fill_price=avg_fill_price,
                    commission=commission,
                )
                self._move_to_completed(order_id, tracking_info)
                self.stats['filled_orders'] += 1
                self.stats['total_volume'] += filled_quantity * avg_fill_price
                self.stats['total_commission'] += commission
                
                # 調用成交回調
                if self.on_order_filled:
                    self.on_order_filled(order_id, tracking_info)
                    
            elif status == OrderStatus.CANCELLED:
                tracking_info.add_event(OrderEvent.CANCELLED, message)
                self._move_to_completed(order_id, tracking_info)
                self.stats['cancelled_orders'] += 1
                
            elif status == OrderStatus.REJECTED:
                tracking_info.add_event(OrderEvent.REJECTED, message)
                self._move_to_completed(order_id, tracking_info)
                self.stats['rejected_orders'] += 1
                
                # 調用錯誤回調
                if self.on_order_error:
                    self.on_order_error(order_id, tracking_info, message)
            
            logger.info(f"訂單狀態更新: {order_id} {old_status} -> {status}")
            
        # 調用更新回調
        if self.on_order_update:
            self.on_order_update(order_id, tracking_info)
    
    def update_order_error(self, order_id: str, error_message: str):
        """
        更新訂單錯誤
        
        Args:
            order_id (str): 訂單 ID
            error_message (str): 錯誤訊息
        """
        with self._lock:
            if order_id not in self.tracking_orders:
                logger.warning(f"找不到追蹤中的訂單: {order_id}")
                return
                
            tracking_info = self.tracking_orders[order_id]
            tracking_info.error_message = error_message
            tracking_info.add_event(OrderEvent.ERROR, error_message)
            
            self.stats['error_orders'] += 1
            
        logger.error(f"訂單錯誤: {order_id} - {error_message}")
        
        # 調用錯誤回調
        if self.on_order_error:
            self.on_order_error(order_id, tracking_info, error_message)
    
    def get_order_info(self, order_id: str) -> Optional[OrderTrackingInfo]:
        """
        獲取訂單追蹤資訊
        
        Args:
            order_id (str): 訂單 ID
            
        Returns:
            OrderTrackingInfo: 訂單追蹤資訊或 None
        """
        with self._lock:
            # 先查找追蹤中的訂單
            if order_id in self.tracking_orders:
                return self.tracking_orders[order_id]
            
            # 再查找已完成的訂單
            if order_id in self.completed_orders:
                return self.completed_orders[order_id]
                
            return None
    
    def get_active_orders(self) -> List[OrderTrackingInfo]:
        """
        獲取活躍訂單列表
        
        Returns:
            List[OrderTrackingInfo]: 活躍訂單列表
        """
        with self._lock:
            return list(self.tracking_orders.values())
    
    def get_completed_orders(self, limit: int = 100) -> List[OrderTrackingInfo]:
        """
        獲取已完成訂單列表
        
        Args:
            limit (int): 限制數量
            
        Returns:
            List[OrderTrackingInfo]: 已完成訂單列表
        """
        with self._lock:
            orders = list(self.completed_orders.values())
            # 按更新時間排序，最新的在前
            orders.sort(key=lambda x: x.updated_time, reverse=True)
            return orders[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        獲取統計資訊
        
        Returns:
            Dict[str, Any]: 統計資訊
        """
        with self._lock:
            stats = self.stats.copy()
            stats['active_orders'] = len(self.tracking_orders)
            stats['completed_orders'] = len(self.completed_orders)
            
            # 計算成功率
            if stats['total_orders'] > 0:
                stats['fill_rate'] = stats['filled_orders'] / stats['total_orders']
                stats['cancel_rate'] = stats['cancelled_orders'] / stats['total_orders']
                stats['error_rate'] = stats['error_orders'] / stats['total_orders']
            else:
                stats['fill_rate'] = 0.0
                stats['cancel_rate'] = 0.0
                stats['error_rate'] = 0.0
                
            return stats

    def _move_to_completed(self, order_id: str, tracking_info: OrderTrackingInfo):
        """
        將訂單移動到已完成列表

        Args:
            order_id (str): 訂單 ID
            tracking_info (OrderTrackingInfo): 追蹤資訊
        """
        if order_id in self.tracking_orders:
            del self.tracking_orders[order_id]
            self.completed_orders[order_id] = tracking_info

    def _cleanup_loop(self):
        """清理循環"""
        while self._running:
            try:
                self._cleanup_old_orders()
                time.sleep(self.cleanup_interval)
            except Exception as e:
                logger.exception(f"清理循環錯誤: {e}")
                time.sleep(60)  # 錯誤時等待 1 分鐘

    def _cleanup_old_orders(self):
        """清理舊訂單"""
        cutoff_time = datetime.now() - timedelta(days=self.max_history_days)

        with self._lock:
            # 清理已完成的舊訂單
            orders_to_remove = []
            for order_id, tracking_info in self.completed_orders.items():
                if tracking_info.updated_time < cutoff_time:
                    orders_to_remove.append(order_id)

            for order_id in orders_to_remove:
                del self.completed_orders[order_id]

            if orders_to_remove:
                logger.info(f"清理了 {len(orders_to_remove)} 個舊訂單記錄")

    def cancel_all_orders(self) -> List[str]:
        """
        標記所有活躍訂單為取消狀態

        Returns:
            List[str]: 被取消的訂單 ID 列表
        """
        with self._lock:
            cancelled_orders = []
            for order_id, tracking_info in list(self.tracking_orders.items()):
                if tracking_info.status in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]:
                    self.update_order_status(
                        order_id,
                        OrderStatus.CANCELLED,
                        tracking_info.filled_quantity,
                        tracking_info.avg_fill_price,
                        tracking_info.commission,
                        "系統取消所有訂單"
                    )
                    cancelled_orders.append(order_id)

            return cancelled_orders

    def get_orders_by_status(self, status: OrderStatus) -> List[OrderTrackingInfo]:
        """
        根據狀態獲取訂單

        Args:
            status (OrderStatus): 訂單狀態

        Returns:
            List[OrderTrackingInfo]: 符合狀態的訂單列表
        """
        with self._lock:
            orders = []

            # 查找活躍訂單
            for tracking_info in self.tracking_orders.values():
                if tracking_info.status == status:
                    orders.append(tracking_info)

            # 查找已完成訂單
            for tracking_info in self.completed_orders.values():
                if tracking_info.status == status:
                    orders.append(tracking_info)

            return orders

    def get_orders_by_symbol(self, symbol: str) -> List[OrderTrackingInfo]:
        """
        根據股票代號獲取訂單

        Args:
            symbol (str): 股票代號

        Returns:
            List[OrderTrackingInfo]: 符合條件的訂單列表
        """
        with self._lock:
            orders = []

            # 查找活躍訂單
            for tracking_info in self.tracking_orders.values():
                if tracking_info.order.stock_id == symbol:
                    orders.append(tracking_info)

            # 查找已完成訂單
            for tracking_info in self.completed_orders.values():
                if tracking_info.order.stock_id == symbol:
                    orders.append(tracking_info)

            return orders

    def export_order_history(self, start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        導出訂單歷史

        Args:
            start_date (datetime, optional): 開始日期
            end_date (datetime, optional): 結束日期

        Returns:
            List[Dict[str, Any]]: 訂單歷史數據
        """
        with self._lock:
            history = []

            # 合併活躍和已完成訂單
            all_orders = {**self.tracking_orders, **self.completed_orders}

            for order_id, tracking_info in all_orders.items():
                # 日期過濾
                if start_date and tracking_info.created_time < start_date:
                    continue
                if end_date and tracking_info.created_time > end_date:
                    continue

                order_data = {
                    'order_id': order_id,
                    'broker_name': tracking_info.broker_name,
                    'broker_order_id': tracking_info.broker_order_id,
                    'symbol': tracking_info.order.stock_id,
                    'action': tracking_info.order.action,
                    'quantity': tracking_info.order.quantity,
                    'price': tracking_info.order.price,
                    'order_type': tracking_info.order.order_type.value,
                    'status': tracking_info.status.value,
                    'filled_quantity': tracking_info.filled_quantity,
                    'avg_fill_price': tracking_info.avg_fill_price,
                    'commission': tracking_info.commission,
                    'created_time': tracking_info.created_time.isoformat(),
                    'updated_time': tracking_info.updated_time.isoformat(),
                    'error_message': tracking_info.error_message,
                    'events': tracking_info.events,
                }
                history.append(order_data)

            # 按創建時間排序
            history.sort(key=lambda x: x['created_time'], reverse=True)
            return history
