# -*- coding: utf-8 -*-
"""BaoStock 連接管理器

實現 BaoStock 連接的單例模式管理，提供連接緩存、懶加載和連接池功能，
解決多個適配器重複登錄導致的性能問題。

主要功能：
- 單例模式確保全局唯一連接管理器
- 連接緩存避免重複登錄/登出操作
- 懶加載連接，只在需要時才登錄
- 自動會話管理和超時處理
- 線程安全的連接操作

Example:
    >>> manager = BaoStockConnectionManager.get_instance()
    >>> bs = await manager.get_connection()
    >>> # 使用 bs 進行數據查詢
    >>> # 連接會自動管理，無需手動登出
"""

import logging
import threading
import time
import asyncio
from typing import Optional, Any
from datetime import datetime, timedelta

# 設定日誌
logger = logging.getLogger(__name__)


class BaoStockConnectionManager:
    """BaoStock 連接管理器
    
    使用單例模式管理 BaoStock 連接，提供連接緩存和懶加載功能。
    解決多個適配器重複登錄導致的性能問題。
    
    Features:
        - 單例模式：全局唯一實例
        - 連接緩存：避免重複登錄
        - 懶加載：只在需要時連接
        - 自動重連：處理會話超時
        - 線程安全：支持並發訪問
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """單例模式實現"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化連接管理器"""
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.bs = None
        self.is_connected = False
        self.last_activity = None
        self.connection_lock = threading.Lock()
        self.session_timeout = 3600  # 1小時會話超時
        self.max_retry_attempts = 3
        self.retry_delay = 1.0
        
        logger.info("BaoStock 連接管理器初始化完成")
    
    @classmethod
    def get_instance(cls) -> 'BaoStockConnectionManager':
        """獲取單例實例
        
        Returns:
            BaoStockConnectionManager: 連接管理器實例
        """
        return cls()
    
    def is_module_available(self) -> bool:
        """檢查 BaoStock 模組是否可用
        
        Returns:
            bool: 模組是否可用
        """
        if self.bs is not None:
            return True
        
        try:
            import baostock as bs
            self.bs = bs
            logger.debug("BaoStock 模組導入成功")
            return True
        except ImportError as e:
            logger.warning(f"BaoStock 模組不可用: {e}")
            return False
    
    async def get_connection(self) -> Optional[Any]:
        """獲取 BaoStock 連接（懶加載）
        
        Returns:
            BaoStock API 實例，如果連接失敗則返回 None
        """
        if not self.is_module_available():
            return None
        
        with self.connection_lock:
            # 檢查現有連接是否有效
            if self._is_connection_valid():
                self._update_activity()
                return self.bs
            
            # 需要建立新連接
            return await self._establish_connection()
    
    def _is_connection_valid(self) -> bool:
        """檢查連接是否有效
        
        Returns:
            bool: 連接是否有效
        """
        if not self.is_connected or self.bs is None:
            return False
        
        # 檢查會話是否超時
        if self.last_activity:
            elapsed = time.time() - self.last_activity
            if elapsed > self.session_timeout:
                logger.info("BaoStock 會話超時，需要重新連接")
                self._disconnect_internal()
                return False
        
        return True
    
    async def _establish_connection(self) -> Optional[Any]:
        """建立 BaoStock 連接
        
        Returns:
            BaoStock API 實例，如果連接失敗則返回 None
        """
        for attempt in range(self.max_retry_attempts):
            try:
                logger.info(f"嘗試連接 BaoStock (第 {attempt + 1}/{self.max_retry_attempts} 次)")
                
                # 確保先斷開舊連接
                if self.is_connected:
                    self._disconnect_internal()
                
                # 執行登錄
                lg = self.bs.login()
                if lg.error_code == '0':
                    self.is_connected = True
                    self._update_activity()
                    logger.info("BaoStock 連接建立成功")
                    return self.bs
                else:
                    logger.warning(f"BaoStock 登錄失敗: {lg.error_msg}")
                    
            except Exception as e:
                logger.error(f"BaoStock 連接失敗 (第 {attempt + 1} 次): {e}")
            
            # 重試前等待
            if attempt < self.max_retry_attempts - 1:
                await asyncio.sleep(self.retry_delay)
        
        logger.error("BaoStock 連接建立失敗，已達最大重試次數")
        return None
    
    def _update_activity(self):
        """更新最後活動時間"""
        self.last_activity = time.time()
    
    def _disconnect_internal(self):
        """內部斷開連接方法"""
        if self.bs and self.is_connected:
            try:
                self.bs.logout()
                logger.debug("BaoStock 連接已斷開")
            except Exception as e:
                logger.warning(f"BaoStock 登出失敗: {e}")
            finally:
                self.is_connected = False
                self.last_activity = None
    
    def disconnect(self):
        """手動斷開連接"""
        with self.connection_lock:
            self._disconnect_internal()
    
    def get_connection_status(self) -> dict:
        """獲取連接狀態信息
        
        Returns:
            dict: 連接狀態信息
        """
        return {
            'is_connected': self.is_connected,
            'module_available': self.bs is not None,
            'last_activity': self.last_activity,
            'session_timeout': self.session_timeout,
            'connection_age': time.time() - self.last_activity if self.last_activity else None
        }
    
    def __del__(self):
        """析構函數，確保連接被正確關閉"""
        try:
            self.disconnect()
        except Exception:
            pass  # 忽略析構時的錯誤


# 全局連接管理器實例
_connection_manager = None


def get_baostock_connection_manager() -> BaoStockConnectionManager:
    """獲取全局 BaoStock 連接管理器實例
    
    Returns:
        BaoStockConnectionManager: 連接管理器實例
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = BaoStockConnectionManager.get_instance()
    return _connection_manager


async def get_baostock_connection() -> Optional[Any]:
    """便捷函數：獲取 BaoStock 連接
    
    Returns:
        BaoStock API 實例，如果連接失敗則返回 None
    """
    manager = get_baostock_connection_manager()
    return await manager.get_connection()


def is_baostock_available() -> bool:
    """便捷函數：檢查 BaoStock 是否可用
    
    Returns:
        bool: BaoStock 是否可用
    """
    manager = get_baostock_connection_manager()
    return manager.is_module_available()
