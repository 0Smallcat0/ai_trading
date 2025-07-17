"""Interactive Brokers 適配器回調處理模組

此模組負責處理來自 IB API 的各種回調事件。

版本: v2.0
作者: AI Trading System
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional
import threading

# 修復導入：OrderStatus 實際定義在 broker_base 中
from src.execution.broker_base import OrderStatus
from src.execution.ib_utils import format_ib_error, is_critical_error

try:
    from ibapi.execution import Execution
    from ibapi.commission_report import CommissionReport
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False
    class Execution:
        pass
    class CommissionReport:
        pass

logger = logging.getLogger("execution.ib.callbacks")


class IBCallbackHandler:
    """IB 回調處理器
    
    負責處理來自 IB API 的各種回調事件，包括：
    - 訂單狀態更新
    - 執行詳情
    - 佣金報告
    - 錯誤處理
    - 市場數據回調
    """
    
    def __init__(self, order_manager):
        """初始化回調處理器
        
        Args:
            order_manager: 訂單管理器
        """
        self.order_manager = order_manager
        
        # 執行和佣金記錄
        self.executions: Dict[str, Dict[str, Any]] = {}
        self.commissions: Dict[str, Dict[str, Any]] = {}
        
        # 線程鎖
        self._lock = threading.Lock()
        
        # 回調函數
        self.on_order_status = None
        self.on_execution = None
        self.on_error = None
        
        logger.info("IB 回調處理器初始化完成")
    
    def handle_order_status(
        self,
        ib_order_id: int,
        status: str,
        filled: float,
        remaining: float,
        avg_fill_price: float
    ) -> None:
        """處理訂單狀態更新
        
        Args:
            ib_order_id: IB 訂單 ID
            status: 狀態
            filled: 已成交數量
            remaining: 剩餘數量
            avg_fill_price: 平均成交價格
        """
        try:
            with self._lock:
                order_info = self._get_order_info_by_ib_id(ib_order_id)
                if not order_info:
                    return
                
                order_id = self.order_manager.ib_order_map[ib_order_id]
                self._update_order_status(order_info, status, filled, avg_fill_price)
                self._trigger_order_status_callback(order_id, order_info, filled, avg_fill_price)
                
        except Exception as e:
            logger.exception("處理訂單狀態更新失敗: %s", e)
    
    def _get_order_info_by_ib_id(self, ib_order_id: int) -> Optional[Dict[str, Any]]:
        """根據 IB 訂單 ID 獲取訂單資訊
        
        Args:
            ib_order_id: IB 訂單 ID
            
        Returns:
            Dict: 訂單資訊或 None
        """
        if ib_order_id not in self.order_manager.ib_order_map:
            return None
        
        order_id = self.order_manager.ib_order_map[ib_order_id]
        if order_id not in self.order_manager.order_map:
            return None
        
        return self.order_manager.order_map[order_id]
    
    def _update_order_status(self, order_info: Dict[str, Any], status: str,
                           filled: float, avg_fill_price: float) -> None:
        """更新訂單狀態資訊
        
        Args:
            order_info: 訂單資訊字典
            status: 狀態字符串
            filled: 已成交數量
            avg_fill_price: 平均成交價格
        """
        # 轉換狀態
        status_mapping = {
            "Submitted": OrderStatus.PENDING,
            "Filled": OrderStatus.FILLED,
            "Cancelled": OrderStatus.CANCELLED,
            "PartiallyFilled": OrderStatus.PARTIALLY_FILLED,
        }
        order_info['status'] = status_mapping.get(status, OrderStatus.PENDING)
        
        # 更新成交資訊
        order_info['filled_quantity'] = filled
        order_info['avg_fill_price'] = avg_fill_price
        order_info['timestamp'] = datetime.now()
    
    def _trigger_order_status_callback(self, order_id: str, order_info: Dict[str, Any],
                                     filled: float, avg_fill_price: float) -> None:
        """觸發訂單狀態回調
        
        Args:
            order_id: 訂單 ID
            order_info: 訂單資訊
            filled: 已成交數量
            avg_fill_price: 平均成交價格
        """
        if self.on_order_status:
            self.on_order_status(order_id, order_info['status'], filled, avg_fill_price)
    
    def handle_execution(self, req_id: int, contract, execution: Execution) -> None:
        """處理執行詳情
        
        Args:
            req_id: 請求 ID
            contract: 合約
            execution: 執行詳情
        """
        try:
            # 記錄執行詳情
            self.executions[execution.execId] = {
                'order_id': execution.orderId,
                'symbol': contract.symbol,
                'side': execution.side,
                'shares': execution.shares,
                'price': execution.price,
                'perm_id': execution.permId,
                'client_id': execution.clientId,
                'liquidation': execution.liquidation,
                'cum_qty': execution.cumQty,
                'avg_price': execution.avgPrice,
                'order_ref': execution.orderRef,
                'ev_rule': execution.evRule,
                'ev_multiplier': execution.evMultiplier,
                'model_code': execution.modelCode,
                'last_liquidity': execution.lastLiquidity,
                'time': execution.time,
                'timestamp': datetime.now(),
            }
            
            # 調用回調函數
            if self.on_execution:
                self.on_execution(execution.orderId, execution)
                
        except Exception as e:
            logger.exception("處理執行詳情失敗: %s", e)
    
    def handle_commission(self, commission_report: CommissionReport) -> None:
        """處理佣金報告
        
        Args:
            commission_report: 佣金報告
        """
        try:
            # 記錄佣金資訊
            self.commissions[commission_report.execId] = {
                'commission': commission_report.commission,
                'currency': commission_report.currency,
                'realized_pnl': commission_report.realizedPNL,
                'timestamp': datetime.now(),
            }
            
        except Exception as e:
            logger.exception("處理佣金報告失敗: %s", e)
    
    def handle_error(self, req_id: int, error_code: int, error_string: str) -> None:
        """處理錯誤
        
        Args:
            req_id: 請求 ID
            error_code: 錯誤代碼
            error_string: 錯誤訊息
        """
        try:
            # 格式化錯誤訊息
            formatted_error = format_ib_error(error_code, error_string)
            
            # 根據錯誤嚴重性記錄日誌
            if is_critical_error(error_code):
                logger.error("嚴重錯誤 - 請求 ID: %d, %s", req_id, formatted_error)
            else:
                logger.warning("警告 - 請求 ID: %d, %s", req_id, formatted_error)
            
            # 調用回調函數
            if self.on_error:
                self.on_error(req_id, error_code, error_string)
                
        except Exception as e:
            logger.exception("處理錯誤回調失敗: %s", e)
    
    def handle_next_valid_id(self, order_id: int) -> None:
        """處理下一個有效訂單 ID
        
        Args:
            order_id: 下一個有效訂單 ID
        """
        logger.debug("收到下一個有效訂單 ID: %d", order_id)
    
    def handle_connection_ack(self) -> None:
        """處理連接確認"""
        logger.debug("收到連接確認")
    
    def handle_account_summary(self, req_id: int, account: str, tag: str, 
                             value: str, currency: str) -> None:
        """處理帳戶摘要
        
        Args:
            req_id: 請求 ID
            account: 帳戶
            tag: 標籤
            value: 值
            currency: 貨幣
        """
        logger.debug("帳戶摘要 - %s: %s %s", tag, value, currency)
    
    def handle_position(self, account: str, contract, position: float, avg_cost: float) -> None:
        """處理持倉資訊
        
        Args:
            account: 帳戶
            contract: 合約
            position: 持倉數量
            avg_cost: 平均成本
        """
        logger.debug("持倉 - %s: %.2f @ %.2f", contract.symbol, position, avg_cost)
    
    def create_tick_price_callback(self, original_callback, market_data_manager):
        """創建價格回調函數
        
        Args:
            original_callback: 原始回調函數
            market_data_manager: 市場數據管理器
            
        Returns:
            Callable: 新的回調函數
        """
        def callback(req_id, tick_type, price, attrib):
            original_callback(req_id, tick_type, price, attrib)
            market_data_manager.on_tick_price(req_id, tick_type, price)
        return callback
    
    def create_tick_size_callback(self, original_callback, market_data_manager):
        """創建數量回調函數
        
        Args:
            original_callback: 原始回調函數
            market_data_manager: 市場數據管理器
            
        Returns:
            Callable: 新的回調函數
        """
        def callback(req_id, tick_type, size):
            original_callback(req_id, tick_type, size)
            market_data_manager.on_tick_size(req_id, tick_type, size)
        return callback
