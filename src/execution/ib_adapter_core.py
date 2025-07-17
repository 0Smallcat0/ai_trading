"""Interactive Brokers 適配器核心連接管理模組

此模組負責 IB API 的連接管理、認證和基本通信功能。

版本: v2.0
作者: AI Trading System
"""

import logging
import threading
import time
from typing import Optional

try:
    from ibapi.client import EClient
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False
    class EClient:
        """模擬 EClient 類"""
        def __init__(self, wrapper):
            pass
        def isConnected(self):
            return False
        def connect(self, host, port, client_id):
            return True
        def disconnect(self):
            return True
        def run(self):
            pass

from src.execution.ib_utils import IBConstants

logger = logging.getLogger("execution.ib.core")


class IBConnectionManager:
    """IB 連接管理器
    
    負責管理與 Interactive Brokers API 的連接，包括：
    - 連接建立和斷開
    - 連接狀態監控
    - 重連機制
    - 連接參數驗證
    """
    
    def __init__(self, wrapper, host: str = None, port: int = None, client_id: int = None):
        """初始化連接管理器
        
        Args:
            wrapper: IB API 包裝器
            host: 主機地址
            port: 端口號
            client_id: 客戶端 ID
        """
        self.wrapper = wrapper
        self.host = host or IBConstants.DEFAULT_HOST
        self.port = port or IBConstants.DEFAULT_TWS_PORT
        self.client_id = client_id or IBConstants.DEFAULT_CLIENT_ID
        
        # 驗證參數
        self._validate_connection_params()
        
        # 創建客戶端
        self.client = EClient(wrapper)
        
        # 連接狀態
        self._connected = False
        self._connection_lock = threading.Lock()
        self._next_order_id = 1
        
        logger.info("IB 連接管理器初始化完成 - %s:%d", self.host, self.port)
    
    def _validate_connection_params(self) -> None:
        """驗證連接參數
        
        Raises:
            ValueError: 如果參數無效
        """
        if not isinstance(self.host, str) or not self.host.strip():
            raise ValueError("主機地址不能為空")
        
        if not isinstance(self.port, int) or self.port <= 0 or self.port > 65535:
            raise ValueError(f"無效的端口號: {self.port}")
        
        if not isinstance(self.client_id, int) or self.client_id < 0:
            raise ValueError(f"無效的客戶端 ID: {self.client_id}")
    
    @property
    def connected(self) -> bool:
        """檢查是否已連接到 IB API
        
        Returns:
            bool: 連接狀態
        """
        with self._connection_lock:
            return self._connected and self.client.isConnected()
    
    def connect(self) -> bool:
        """連接 Interactive Brokers API
        
        建立與 IB Gateway/TWS 的連接，並等待連接確認和下一個有效訂單 ID。
        
        Returns:
            bool: 是否連接成功
            
        Raises:
            Exception: 連接過程中發生的任何異常
        """
        if self.connected:
            logger.info("已經連接到 IB API")
            return True
        
        try:
            logger.info("正在連接 IB API - %s:%d", self.host, self.port)
            
            # 連接到 IB Gateway/TWS
            self.client.connect(self.host, self.port, self.client_id)
            
            # 啟動消息循環線程
            api_thread = threading.Thread(target=self.client.run, daemon=True)
            api_thread.start()
            
            # 等待連接確認
            if not self._wait_for_connection():
                logger.error("連接 IB API 超時")
                return False
            
            # 等待下一個有效訂單 ID
            if not self._wait_for_next_order_id():
                logger.error("獲取下一個有效訂單 ID 超時")
                return False
            
            with self._connection_lock:
                self._connected = True
            
            logger.info("已連接到 IB API，下一個訂單 ID: %d", self._next_order_id)
            return True
            
        except Exception as e:
            logger.exception("連接 IB API 失敗: %s", e)
            return False
    
    def disconnect(self) -> bool:
        """斷開 Interactive Brokers API 連接
        
        Returns:
            bool: 是否成功斷開連接
        """
        try:
            if not self.connected:
                logger.info("已經斷開 IB API 連接")
                return True
            
            logger.info("正在斷開 IB API 連接")
            self.client.disconnect()
            
            # 等待斷開確認
            timeout = 5.0
            start_time = time.time()
            while self.client.isConnected() and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            with self._connection_lock:
                self._connected = False
            
            if self.client.isConnected():
                logger.warning("斷開 IB API 連接超時")
                return False
            
            logger.info("已斷開 IB API 連接")
            return True
            
        except Exception as e:
            logger.exception("斷開 IB API 連接失敗: %s", e)
            return False
    
    def force_reconnect(self) -> bool:
        """強制重連
        
        Returns:
            bool: 是否重連成功
        """
        logger.info("執行強制重連")
        
        # 先斷開
        self.disconnect()
        time.sleep(1.0)  # 等待一秒
        
        # 重新連接
        return self.connect()
    
    def _wait_for_connection(self) -> bool:
        """等待連接確認
        
        Returns:
            bool: 是否連接成功
        """
        timeout = 10.0  # 10 秒超時
        start_time = time.time()
        
        while not self.client.isConnected() and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        return self.client.isConnected()
    
    def _wait_for_next_order_id(self) -> bool:
        """等待下一個有效訂單 ID
        
        Returns:
            bool: 是否成功獲取訂單 ID
        """
        timeout = 5.0  # 5 秒超時
        start_time = time.time()
        
        # 請求下一個有效訂單 ID
        self.client.reqIds(-1)
        
        while self._next_order_id <= 1 and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        return self._next_order_id > 1
    
    def set_next_order_id(self, order_id: int) -> None:
        """設定下一個訂單 ID
        
        Args:
            order_id: 訂單 ID
        """
        self._next_order_id = order_id
        logger.debug("設定下一個訂單 ID: %d", order_id)
    
    def get_next_order_id(self) -> int:
        """獲取並遞增下一個訂單 ID
        
        Returns:
            int: 下一個可用的訂單 ID
        """
        current_id = self._next_order_id
        self._next_order_id += 1
        return current_id
