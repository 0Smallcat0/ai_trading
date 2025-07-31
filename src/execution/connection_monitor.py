"""
API 連接狀態監控系統

此模組提供統一的 API 連接狀態監控功能，包括：
- 心跳檢測
- 斷線重連
- 狀態通知
- 連接品質監控
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from .broker_base import BrokerBase

# 設定日誌
logger = logging.getLogger("execution.connection_monitor")


class ConnectionStatus(Enum):
    """連接狀態枚舉"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class ConnectionHealth(Enum):
    """連接健康狀態枚舉"""
    EXCELLENT = "excellent"  # 延遲 < 100ms
    GOOD = "good"           # 延遲 100-300ms
    FAIR = "fair"           # 延遲 300-1000ms
    POOR = "poor"           # 延遲 > 1000ms
    UNKNOWN = "unknown"     # 無法測量


class ConnectionMonitor:
    """API 連接狀態監控器"""
    
    def __init__(
        self,
        heartbeat_interval: int = 30,
        reconnect_interval: int = 5,
        max_reconnect_attempts: int = 10,
        health_check_interval: int = 60,
    ):
        """
        初始化連接監控器
        
        Args:
            heartbeat_interval (int): 心跳檢測間隔 (秒)
            reconnect_interval (int): 重連間隔 (秒)
            max_reconnect_attempts (int): 最大重連次數
            health_check_interval (int): 健康檢查間隔 (秒)
        """
        self.heartbeat_interval = heartbeat_interval
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.health_check_interval = health_check_interval
        
        # 監控的適配器
        self.adapters: Dict[str, BrokerBase] = {}
        
        # 連接狀態
        self.connection_status: Dict[str, ConnectionStatus] = {}
        self.connection_health: Dict[str, ConnectionHealth] = {}
        self.last_heartbeat: Dict[str, datetime] = {}
        self.reconnect_attempts: Dict[str, int] = {}
        
        # 統計資訊
        self.connection_stats: Dict[str, Dict[str, Any]] = {}
        
        # 回調函數
        self.on_status_change: Optional[Callable] = None
        self.on_health_change: Optional[Callable] = None
        self.on_reconnect_failed: Optional[Callable] = None
        
        # 監控線程
        self._monitor_thread = None
        self._health_thread = None
        self._running = False
        self._lock = threading.Lock()
    
    def add_adapter(self, name: str, adapter: BrokerBase):
        """
        添加適配器到監控
        
        Args:
            name (str): 適配器名稱
            adapter (BrokerBase): 適配器實例
        """
        with self._lock:
            self.adapters[name] = adapter
            self.connection_status[name] = ConnectionStatus.DISCONNECTED
            self.connection_health[name] = ConnectionHealth.UNKNOWN
            self.last_heartbeat[name] = datetime.now()
            self.reconnect_attempts[name] = 0
            
            # 初始化統計資訊
            self.connection_stats[name] = {
                'total_connections': 0,
                'total_disconnections': 0,
                'total_reconnects': 0,
                'uptime_start': None,
                'total_uptime': timedelta(0),
                'avg_response_time': 0.0,
                'response_times': [],
            }
            
        logger.info(f"已添加適配器到監控: {name}")
    
    def remove_adapter(self, name: str):
        """
        從監控中移除適配器
        
        Args:
            name (str): 適配器名稱
        """
        with self._lock:
            if name in self.adapters:
                del self.adapters[name]
                del self.connection_status[name]
                del self.connection_health[name]
                del self.last_heartbeat[name]
                del self.reconnect_attempts[name]
                del self.connection_stats[name]
                
        logger.info(f"已從監控中移除適配器: {name}")
    
    def start_monitoring(self):
        """開始監控"""
        if self._running:
            logger.warning("監控已經在運行")
            return
            
        self._running = True
        
        # 啟動心跳監控線程
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="ConnectionMonitor"
        )
        self._monitor_thread.start()
        
        # 啟動健康檢查線程
        self._health_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True,
            name="HealthChecker"
        )
        self._health_thread.start()
        
        logger.info("連接監控已啟動")
    
    def stop_monitoring(self):
        """停止監控"""
        self._running = False
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
            
        if self._health_thread and self._health_thread.is_alive():
            self._health_thread.join(timeout=5)
            
        logger.info("連接監控已停止")
    
    def get_status(self, name: str) -> Optional[ConnectionStatus]:
        """
        獲取適配器連接狀態
        
        Args:
            name (str): 適配器名稱
            
        Returns:
            ConnectionStatus: 連接狀態或 None
        """
        return self.connection_status.get(name)
    
    def get_health(self, name: str) -> Optional[ConnectionHealth]:
        """
        獲取適配器連接健康狀態
        
        Args:
            name (str): 適配器名稱
            
        Returns:
            ConnectionHealth: 連接健康狀態或 None
        """
        return self.connection_health.get(name)
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """
        獲取所有適配器狀態
        
        Returns:
            Dict[str, Dict[str, Any]]: 所有適配器狀態
        """
        with self._lock:
            status = {}
            for name in self.adapters:
                status[name] = {
                    'connection_status': self.connection_status[name].value,
                    'connection_health': self.connection_health[name].value,
                    'last_heartbeat': self.last_heartbeat[name].isoformat(),
                    'reconnect_attempts': self.reconnect_attempts[name],
                    'stats': self.connection_stats[name].copy(),
                }
            return status
    
    def force_reconnect(self, name: str) -> bool:
        """
        強制重連適配器
        
        Args:
            name (str): 適配器名稱
            
        Returns:
            bool: 是否重連成功
        """
        if name not in self.adapters:
            logger.error(f"找不到適配器: {name}")
            return False
            
        return self._reconnect_adapter(name)
    
    def _monitor_loop(self):
        """監控循環"""
        while self._running:
            try:
                with self._lock:
                    adapters_copy = dict(self.adapters)
                
                for name, adapter in adapters_copy.items():
                    self._check_connection(name, adapter)
                    
                time.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.exception(f"監控循環錯誤: {e}")
                time.sleep(1)
    
    def _health_check_loop(self):
        """健康檢查循環"""
        while self._running:
            try:
                with self._lock:
                    adapters_copy = dict(self.adapters)
                
                for name, adapter in adapters_copy.items():
                    self._check_health(name, adapter)
                    
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.exception(f"健康檢查循環錯誤: {e}")
                time.sleep(1)

    def _check_connection(self, name: str, adapter: BrokerBase):
        """
        檢查連接狀態

        Args:
            name (str): 適配器名稱
            adapter (BrokerBase): 適配器實例
        """
        try:
            current_status = self.connection_status[name]
            is_connected = adapter.connected

            if is_connected:
                if current_status != ConnectionStatus.CONNECTED:
                    self._update_status(name, ConnectionStatus.CONNECTED)
                    self._update_stats_on_connect(name)

                # 更新心跳時間
                self.last_heartbeat[name] = datetime.now()
                self.reconnect_attempts[name] = 0

            else:
                if current_status == ConnectionStatus.CONNECTED:
                    self._update_status(name, ConnectionStatus.DISCONNECTED)
                    self._update_stats_on_disconnect(name)

                # 嘗試重連
                if self.reconnect_attempts[name] < self.max_reconnect_attempts:
                    self._reconnect_adapter(name)

        except Exception as e:
            logger.exception(f"檢查連接狀態失敗 ({name}): {e}")
            self._update_status(name, ConnectionStatus.ERROR)

    def _check_health(self, name: str, adapter: BrokerBase):
        """
        檢查連接健康狀態

        Args:
            name (str): 適配器名稱
            adapter (BrokerBase): 適配器實例
        """
        try:
            if not adapter.connected:
                self._update_health(name, ConnectionHealth.UNKNOWN)
                return

            # 測量響應時間
            start_time = time.time()

            # 嘗試獲取帳戶資訊作為健康檢查
            try:
                adapter.get_account_info()
                response_time = (time.time() - start_time) * 1000  # 轉換為毫秒

                # 記錄響應時間
                stats = self.connection_stats[name]
                stats['response_times'].append(response_time)

                # 只保留最近 100 次的響應時間
                if len(stats['response_times']) > 100:
                    stats['response_times'] = stats['response_times'][-100:]

                # 計算平均響應時間
                stats['avg_response_time'] = sum(stats['response_times']) / len(stats['response_times'])

                # 判斷健康狀態
                if response_time < 100:
                    health = ConnectionHealth.EXCELLENT
                elif response_time < 300:
                    health = ConnectionHealth.GOOD
                elif response_time < 1000:
                    health = ConnectionHealth.FAIR
                else:
                    health = ConnectionHealth.POOR

                self._update_health(name, health)

            except Exception:
                self._update_health(name, ConnectionHealth.POOR)

        except Exception as e:
            logger.exception(f"檢查連接健康狀態失敗 ({name}): {e}")
            self._update_health(name, ConnectionHealth.UNKNOWN)

    def _reconnect_adapter(self, name: str) -> bool:
        """
        重連適配器

        Args:
            name (str): 適配器名稱

        Returns:
            bool: 是否重連成功
        """
        try:
            adapter = self.adapters[name]

            # 更新狀態為重連中
            self._update_status(name, ConnectionStatus.RECONNECTING)

            # 增加重連次數
            self.reconnect_attempts[name] += 1

            logger.info(f"嘗試重連適配器 {name} (第 {self.reconnect_attempts[name]} 次)")

            # 先斷開連接
            try:
                adapter.disconnect()
            except Exception as e:
                logger.warning(f"斷開連接失敗 ({name}): {e}")

            # 等待一段時間
            time.sleep(self.reconnect_interval)

            # 嘗試重新連接
            if adapter.connect():
                logger.info(f"適配器 {name} 重連成功")
                self._update_status(name, ConnectionStatus.CONNECTED)
                self._update_stats_on_reconnect(name)
                return True
            else:
                logger.error(f"適配器 {name} 重連失敗")
                self._update_status(name, ConnectionStatus.DISCONNECTED)

                # 如果達到最大重連次數，通知失敗
                if self.reconnect_attempts[name] >= self.max_reconnect_attempts:
                    if self.on_reconnect_failed:
                        self.on_reconnect_failed(name, self.reconnect_attempts[name])

                return False

        except Exception as e:
            logger.exception(f"重連適配器失敗 ({name}): {e}")
            self._update_status(name, ConnectionStatus.ERROR)
            return False

    def _update_status(self, name: str, status: ConnectionStatus):
        """
        更新連接狀態

        Args:
            name (str): 適配器名稱
            status (ConnectionStatus): 新狀態
        """
        old_status = self.connection_status.get(name)
        if old_status != status:
            self.connection_status[name] = status
            logger.info(f"適配器 {name} 狀態變更: {old_status} -> {status}")

            # 調用回調函數
            if self.on_status_change:
                self.on_status_change(name, old_status, status)

    def _update_health(self, name: str, health: ConnectionHealth):
        """
        更新連接健康狀態

        Args:
            name (str): 適配器名稱
            health (ConnectionHealth): 新健康狀態
        """
        old_health = self.connection_health.get(name)
        if old_health != health:
            self.connection_health[name] = health
            logger.debug(f"適配器 {name} 健康狀態變更: {old_health} -> {health}")

            # 調用回調函數
            if self.on_health_change:
                self.on_health_change(name, old_health, health)

    def _update_stats_on_connect(self, name: str):
        """連接時更新統計資訊"""
        stats = self.connection_stats[name]
        stats['total_connections'] += 1
        stats['uptime_start'] = datetime.now()

    def _update_stats_on_disconnect(self, name: str):
        """斷開連接時更新統計資訊"""
        stats = self.connection_stats[name]
        stats['total_disconnections'] += 1

        if stats['uptime_start']:
            uptime = datetime.now() - stats['uptime_start']
            stats['total_uptime'] += uptime
            stats['uptime_start'] = None

    def _update_stats_on_reconnect(self, name: str):
        """重連時更新統計資訊"""
        stats = self.connection_stats[name]
        stats['total_reconnects'] += 1
        stats['uptime_start'] = datetime.now()
