"""Interactive Brokers API 適配器 - 重構版本

此模組提供與 Interactive Brokers API (IB Gateway/TWS) 的連接和交易功能。
採用模組化設計，將功能拆分為多個專門的管理器。

重構版本特點：
- 模組化設計，符合單一職責原則
- 每個檔案不超過 300 行
- 完整的類型提示和文檔
- 改進的錯誤處理和日誌記錄

版本: v2.1
作者: AI Trading System
"""

import logging
import os
import threading
from typing import Any, Dict, List, Optional

# 修復導入：Order 和 OrderStatus 實際定義在 broker_base 中
from src.execution.broker_base import Order, OrderStatus
from src.execution.broker_base import BrokerBase
from src.execution.ib_adapter_core import IBConnectionManager
from src.execution.ib_adapter_orders import IBOrderManager
from src.execution.ib_adapter_callbacks import IBCallbackHandler
from src.execution.ib_wrapper import IBWrapper
from src.execution.ib_contracts import IBContractManager
from src.execution.ib_orders import IBOrderManager as IBOrderCreator
from src.execution.ib_options import IBOptionsManager
from src.execution.ib_market_data import IBMarketDataManager
from src.execution.ib_utils import IBConstants

logger = logging.getLogger("execution.ib")


class IBAdapterRefactored(BrokerBase):
    """Interactive Brokers API 適配器 - 重構版本
    
    提供與 Interactive Brokers API 的完整交易功能，採用模組化設計。
    
    主要功能：
    - 連接管理（IBConnectionManager）
    - 訂單管理（IBOrderManager）
    - 回調處理（IBCallbackHandler）
    - 市場數據（IBMarketDataManager）
    - 期權交易（IBOptionsManager）
    
    Example:
        >>> adapter = IBAdapterRefactored()
        >>> if adapter.connect():
        ...     order_id = adapter.place_order(order)
        ...     adapter.disconnect()
    """
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        client_id: int = None,
        log_path: str = None
    ):
        """初始化 IB 適配器
        
        Args:
            host: IB Gateway/TWS 主機地址
            port: 端口號
            client_id: 客戶端 ID
            log_path: 日誌檔案路徑
            
        Raises:
            ValueError: 如果參數無效
        """
        super().__init__()
        
        # 基本參數
        self.host = host or IBConstants.DEFAULT_HOST
        self.port = port or IBConstants.DEFAULT_TWS_PORT
        self.client_id = client_id or IBConstants.DEFAULT_CLIENT_ID
        self.log_path = log_path or "logs/ib_adapter.log"
        
        # 設定日誌
        self._setup_logging()
        
        # 初始化包裝器
        self.wrapper = IBWrapper()
        
        # 初始化管理器
        self._initialize_managers()
        
        # 設定回調
        self._setup_callbacks()
        
        logger.info("IB 適配器初始化完成 - %s:%d", self.host, self.port)
    
    def _setup_logging(self) -> None:
        """設定日誌系統"""
        try:
            log_dir = os.path.dirname(self.log_path)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            logger.debug("日誌系統設定完成 - 路徑: %s", self.log_path)
        except Exception as e:
            logger.warning("設定日誌系統失敗: %s", e)
    
    def _initialize_managers(self) -> None:
        """初始化各個管理器"""
        # 連接管理器
        self.connection_manager = IBConnectionManager(
            self.wrapper, self.host, self.port, self.client_id
        )
        
        # 合約管理器
        self.contract_manager = IBContractManager()
        
        # 訂單創建管理器
        self.order_creator = IBOrderCreator()
        
        # 訂單管理器
        self.order_manager = IBOrderManager(
            self.connection_manager.client,
            self.contract_manager,
            self.order_creator
        )
        
        # 回調處理器
        self.callback_handler = IBCallbackHandler(self.order_manager)
        
        # 期權管理器
        self.options_manager = IBOptionsManager(
            self.connection_manager.client,
            self.contract_manager,
            self.order_creator
        )
        
        # 市場數據管理器
        self.market_data_manager = IBMarketDataManager(
            self.connection_manager.client,
            self.contract_manager
        )
        
        logger.debug("所有管理器初始化完成")
    
    def _setup_callbacks(self) -> None:
        """設定回調函數"""
        # 設定包裝器回調
        self.wrapper.orderStatus = self.callback_handler.handle_order_status
        self.wrapper.execDetails = self.callback_handler.handle_execution
        self.wrapper.commissionReport = self.callback_handler.handle_commission
        self.wrapper.error = self.callback_handler.handle_error
        self.wrapper.nextValidId = self.connection_manager.set_next_order_id
        self.wrapper.connectAck = self.callback_handler.handle_connection_ack
        
        # 連接市場數據回調
        if hasattr(self.wrapper, 'tickPrice'):
            original_tick_price = self.wrapper.tickPrice
            self.wrapper.tickPrice = self.callback_handler.create_tick_price_callback(
                original_tick_price, self.market_data_manager
            )
        
        if hasattr(self.wrapper, 'tickSize'):
            original_tick_size = self.wrapper.tickSize
            self.wrapper.tickSize = self.callback_handler.create_tick_size_callback(
                original_tick_size, self.market_data_manager
            )
        
        logger.debug("回調函數設定完成")
    
    @property
    def connected(self) -> bool:
        """檢查是否已連接到 IB API
        
        Returns:
            bool: 連接狀態
        """
        return self.connection_manager.connected
    
    def connect(self) -> bool:
        """連接 Interactive Brokers API
        
        Returns:
            bool: 是否連接成功
        """
        return self.connection_manager.connect()
    
    def disconnect(self) -> bool:
        """斷開 Interactive Brokers API 連接
        
        Returns:
            bool: 是否成功斷開連接
        """
        return self.connection_manager.disconnect()
    
    def force_reconnect(self) -> bool:
        """強制重連
        
        Returns:
            bool: 是否重連成功
        """
        return self.connection_manager.force_reconnect()
    
    def place_order(self, order: Order) -> Optional[str]:
        """下單
        
        Args:
            order: 訂單物件
            
        Returns:
            str: 訂單 ID 或 None (如果下單失敗)
            
        Raises:
            RuntimeError: 如果 API 未連接
        """
        if not self.connected:
            raise RuntimeError("未連接到 IB API")
        
        next_order_id = self.connection_manager.get_next_order_id()
        return self.order_manager.place_order(order, next_order_id)
    
    def cancel_order(self, order_id: str) -> bool:
        """取消訂單
        
        Args:
            order_id: 訂單 ID
            
        Returns:
            bool: 是否成功取消
        """
        return self.order_manager.cancel_order(order_id)
    
    def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """獲取訂單狀態
        
        Args:
            order_id: 訂單 ID
            
        Returns:
            OrderStatus: 訂單狀態或 None
        """
        return self.order_manager.get_order_status(order_id)
    
    def get_orders(self, status: Optional[OrderStatus] = None) -> List[Dict[str, Any]]:
        """獲取訂單列表
        
        Args:
            status: 篩選狀態（可選）
            
        Returns:
            List[Dict]: 訂單列表
        """
        return self.order_manager.get_orders(status)
    
    def modify_order(self, order_id: str, **kwargs) -> bool:
        """修改訂單
        
        Args:
            order_id: 訂單 ID
            **kwargs: 修改參數
            
        Returns:
            bool: 是否成功修改
        """
        return self.order_manager.modify_order(order_id, **kwargs)
    
    def place_option_order(self, symbol: str, expiry: str, strike: float, 
                          right: str, action: str, quantity: int, **kwargs) -> Optional[str]:
        """下期權單
        
        Args:
            symbol: 標的股票代號
            expiry: 到期日
            strike: 行權價
            right: 期權類型
            action: 買賣方向
            quantity: 數量
            **kwargs: 其他參數
            
        Returns:
            str: 訂單 ID 或 None
        """
        if not self.connected:
            raise RuntimeError("未連接到 IB API")
        
        next_order_id = self.connection_manager.get_next_order_id()
        return self.options_manager.place_option_order(
            symbol, expiry, strike, right, action, quantity, next_order_id, **kwargs
        )
    
    def get_market_data(self, stock_id: str) -> Dict[str, Any]:
        """獲取市場資料

        Args:
            stock_id: 股票代號

        Returns:
            Dict: 市場資料
        """
        return self.market_data_manager.get_market_data(stock_id)

    def get_order(self, order_id: str) -> Optional[Order]:
        """獲取訂單資訊

        Args:
            order_id: 訂單 ID

        Returns:
            Order: 訂單物件或 None
        """
        try:
            order_info = self.order_manager.get_order_info(order_id)
            if not order_info:
                return None

            # 將 IB 訂單資訊轉換為標準 Order 物件
            order = Order(
                stock_id=order_info.get('symbol', ''),
                action=order_info.get('action', '').lower(),
                quantity=order_info.get('quantity', 0),
                order_type=self._convert_ib_order_type(order_info.get('order_type', '')),
                price=order_info.get('price'),
                order_id=order_id
            )

            # 設置訂單狀態
            ib_status = order_info.get('status', '')
            order.status = self._convert_ib_status(ib_status)

            return order

        except Exception as e:
            logger.error("獲取訂單 %s 失敗: %s", order_id, e, exc_info=True)
            return None

    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """獲取持倉資訊

        Returns:
            Dict: 持倉資訊，key 為股票代號
        """
        try:
            if not self.connected:
                logger.warning("未連接到 IB API，無法獲取持倉")
                return {}

            # 從 IB API 獲取持倉資訊
            positions = {}

            # 這裡需要實現實際的持倉查詢邏輯
            # 由於 IB API 的持倉查詢是異步的，這裡提供一個簡化的實現
            logger.debug("獲取持倉資訊")

            return positions

        except Exception as e:
            logger.error("獲取持倉失敗: %s", e, exc_info=True)
            return {}

    def _convert_ib_order_type(self, ib_order_type: str) -> 'OrderType':
        """轉換 IB 訂單類型到標準訂單類型

        Args:
            ib_order_type: IB 訂單類型

        Returns:
            OrderType: 標準訂單類型
        """
        from src.execution.broker_base import OrderType

        type_mapping = {
            'MKT': OrderType.MARKET,
            'LMT': OrderType.LIMIT,
            'STP': OrderType.STOP,
            'STP LMT': OrderType.STOP_LIMIT
        }

        return type_mapping.get(ib_order_type, OrderType.MARKET)

    def _convert_ib_status(self, ib_status: str) -> 'OrderStatus':
        """轉換 IB 訂單狀態到標準訂單狀態

        Args:
            ib_status: IB 訂單狀態

        Returns:
            OrderStatus: 標準訂單狀態
        """
        status_mapping = {
            'PendingSubmit': OrderStatus.PENDING,
            'Submitted': OrderStatus.SUBMITTED,
            'Filled': OrderStatus.FILLED,
            'Cancelled': OrderStatus.CANCELLED,
            'Inactive': OrderStatus.REJECTED
        }

        return status_mapping.get(ib_status, OrderStatus.PENDING)
    
    def get_account_info(self) -> Dict[str, Any]:
        """獲取帳戶資訊
        
        Returns:
            Dict: 帳戶資訊
        """
        # 這裡可以添加帳戶資訊獲取邏輯
        return {
            "connected": self.connected,
            "host": self.host,
            "port": self.port,
            "client_id": self.client_id,
        }
