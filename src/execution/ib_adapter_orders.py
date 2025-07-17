"""Interactive Brokers 適配器訂單管理模組

此模組負責訂單的提交、取消、修改和狀態追蹤。

版本: v2.0
作者: AI Trading System
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
import threading

# 修復導入：Order 和 OrderStatus 實際定義在 broker_base 中
from src.execution.broker_base import Order, OrderStatus

logger = logging.getLogger("execution.ib.orders")


class IBOrderManager:
    """IB 訂單管理器
    
    負責管理訂單的完整生命週期，包括：
    - 訂單提交和取消
    - 訂單狀態追蹤
    - 訂單映射管理
    - 執行詳情處理
    """
    
    def __init__(self, client, contract_manager, order_manager):
        """初始化訂單管理器
        
        Args:
            client: IB 客戶端
            contract_manager: 合約管理器
            order_manager: 訂單創建管理器
        """
        self.client = client
        self.contract_manager = contract_manager
        self.order_manager = order_manager
        
        # 訂單映射
        self.order_map: Dict[str, Dict[str, Any]] = {}  # order_id -> order_info
        self.ib_order_map: Dict[int, str] = {}  # ib_order_id -> order_id
        
        # 執行和佣金記錄
        self.executions: Dict[str, Dict[str, Any]] = {}
        self.commissions: Dict[str, Dict[str, Any]] = {}
        
        # 線程鎖
        self._lock = threading.Lock()
        
        # 回調函數
        self.on_order_status = None
        self.on_execution = None
        
        logger.info("IB 訂單管理器初始化完成")
    
    def place_order(self, order: Order, next_order_id: int) -> Optional[str]:
        """下單
        
        Args:
            order: 訂單物件
            next_order_id: 下一個 IB 訂單 ID
            
        Returns:
            str: 訂單 ID 或 None (如果下單失敗)
            
        Raises:
            ValueError: 如果訂單參數無效
        """
        try:
            self._validate_order(order)
            
            with self._lock:
                return self._execute_order_placement(order, next_order_id)
                
        except Exception as e:
            logger.exception("下單失敗: %s", e)
            return None
    
    def _validate_order(self, order: Order) -> None:
        """驗證訂單
        
        Args:
            order: 訂單物件
            
        Raises:
            ValueError: 如果訂單參數無效
        """
        if not order:
            raise ValueError("訂單物件不能為 None")
        
        if not order.stock_id:
            raise ValueError("股票代號不能為空")
        
        if order.quantity <= 0:
            raise ValueError("訂單數量必須大於 0")
    
    def _execute_order_placement(self, order: Order, ib_order_id: int) -> Optional[str]:
        """執行訂單下單流程
        
        Args:
            order: 訂單物件
            ib_order_id: IB 訂單 ID
            
        Returns:
            str: 訂單 ID 或 None (如果下單失敗)
        """
        # 生成訂單 ID
        if not order.order_id:
            order.order_id = str(uuid.uuid4())
        
        # 創建合約和訂單
        contract, ib_order = self._create_order_components(order)
        if not contract or not ib_order:
            return None
        
        # 提交訂單
        self.client.placeOrder(ib_order_id, contract, ib_order)
        
        # 保存訂單映射
        self._save_order_mapping(order, ib_order_id, ib_order, contract)
        
        logger.info(
            "已提交訂單 - ID: %s, IB ID: %d, 代號: %s, 方向: %s, 數量: %d",
            order.order_id, ib_order_id, order.stock_id, order.action, order.quantity
        )
        return order.order_id
    
    def _create_order_components(self, order: Order) -> tuple:
        """創建訂單組件
        
        Args:
            order: 訂單物件
            
        Returns:
            tuple: (contract, ib_order) 或 (None, None) 如果創建失敗
        """
        # 創建 IB 合約
        contract = self.contract_manager.create_stock_contract(order.stock_id)
        if not contract:
            logger.error("無法創建合約: %s", order.stock_id)
            return None, None
        
        # 創建 IB 訂單
        ib_order = self.order_manager.create_order_from_base(order)
        if not ib_order:
            logger.error("無法創建 IB 訂單")
            return None, None
        
        return contract, ib_order
    
    def _save_order_mapping(self, order: Order, ib_order_id: int, ib_order, contract) -> None:
        """保存訂單映射
        
        Args:
            order: 訂單物件
            ib_order_id: IB 訂單 ID
            ib_order: IB 訂單物件
            contract: IB 合約物件
        """
        self.order_map[order.order_id] = {
            'ib_order_id': ib_order_id,
            'order': order,
            'ib_order': ib_order,
            'contract': contract,
            'status': OrderStatus.PENDING,
            'filled_quantity': 0,
            'avg_fill_price': 0.0,
            'timestamp': datetime.now(),
        }
        self.ib_order_map[ib_order_id] = order.order_id
    
    def cancel_order(self, order_id: str) -> bool:
        """取消訂單
        
        Args:
            order_id: 訂單 ID
            
        Returns:
            bool: 是否成功取消
        """
        try:
            with self._lock:
                if order_id not in self.order_map:
                    logger.warning("訂單不存在: %s", order_id)
                    return False
                
                order_info = self.order_map[order_id]
                ib_order_id = order_info['ib_order_id']
                
                # 檢查訂單狀態
                if order_info['status'] in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                    logger.warning("訂單已完成或已取消，無法取消: %s", order_id)
                    return False
                
                # 發送取消請求
                self.client.cancelOrder(ib_order_id)
                
                logger.info("已發送取消訂單請求 - ID: %s, IB ID: %d", order_id, ib_order_id)
                return True
                
        except Exception as e:
            logger.exception("取消訂單失敗: %s", e)
            return False
    
    def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """獲取訂單狀態
        
        Args:
            order_id: 訂單 ID
            
        Returns:
            OrderStatus: 訂單狀態或 None
        """
        with self._lock:
            if order_id in self.order_map:
                return self.order_map[order_id]['status']
            return None
    
    def get_orders(self, status: Optional[OrderStatus] = None) -> List[Dict[str, Any]]:
        """獲取訂單列表
        
        Args:
            status: 篩選狀態（可選）
            
        Returns:
            List[Dict]: 訂單列表
        """
        with self._lock:
            orders = []
            for order_id, order_info in self.order_map.items():
                if status is None or order_info['status'] == status:
                    orders.append({
                        'order_id': order_id,
                        'stock_id': order_info['order'].stock_id,
                        'action': order_info['order'].action,
                        'quantity': order_info['order'].quantity,
                        'status': order_info['status'],
                        'filled_quantity': order_info['filled_quantity'],
                        'avg_fill_price': order_info['avg_fill_price'],
                        'timestamp': order_info['timestamp'],
                    })
            return orders
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """獲取訂單資訊
        
        Args:
            order_id: 訂單 ID
            
        Returns:
            Order: 訂單物件或 None
        """
        with self._lock:
            if order_id in self.order_map:
                order_info = self.order_map[order_id]
                return order_info['order']
            return None
    
    def modify_order(self, order_id: str, **kwargs) -> bool:
        """修改訂單
        
        Args:
            order_id: 訂單 ID
            **kwargs: 修改參數
            
        Returns:
            bool: 是否成功修改
        """
        try:
            with self._lock:
                if order_id not in self.order_map:
                    logger.warning("訂單不存在: %s", order_id)
                    return False
                
                order_info = self.order_map[order_id]
                
                # 檢查訂單狀態
                if order_info['status'] in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                    logger.warning("訂單已完成或已取消，無法修改: %s", order_id)
                    return False
                
                # 修改訂單參數
                ib_order = order_info['ib_order']
                ib_order_id = order_info['ib_order_id']
                contract = order_info['contract']
                
                # 應用修改
                for key, value in kwargs.items():
                    if hasattr(ib_order, key):
                        setattr(ib_order, key, value)
                        logger.debug("修改訂單參數 %s: %s -> %s", order_id, key, value)
                
                # 重新提交訂單
                self.client.placeOrder(ib_order_id, contract, ib_order)
                
                logger.info("已修改訂單: %s", order_id)
                return True
                
        except Exception as e:
            logger.exception("修改訂單失敗: %s", e)
            return False
