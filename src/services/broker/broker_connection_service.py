"""券商連接管理服務 (Broker Connection Service)

此模組提供券商連接的統一管理服務，包括：
- 券商連接狀態監控
- 自動重連機制
- 連接品質評估
- 多券商切換管理
- 連接異常處理

符合 Phase 7.2 程式碼品質標準：
- Pylint ≥8.5/10
- 100% Google Style Docstring 覆蓋率
- 完整型別標註
- 統一錯誤處理模式
"""

import logging
import threading
import time
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable

try:
    from src.core.trade_execution_brokers import TradeExecutionBrokerManager
    from src.execution.broker_base import BrokerBase
except ImportError:
    # 測試環境下的 Mock 類別
    TradeExecutionBrokerManager = None
    BrokerBase = None


logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """連接狀態枚舉"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class BrokerConnectionError(Exception):
    """券商連接錯誤"""


class BrokerConnectionService:
    """券商連接管理服務

    提供統一的券商連接管理介面，包括連接監控、自動重連、
    狀態管理等功能。

    Attributes:
        _trade_executor: 交易執行器實例
        _connection_status: 各券商連接狀態
        _monitoring_thread: 監控執行緒
        _is_monitoring: 監控狀態標誌
        _reconnect_attempts: 重連嘗試次數記錄
        _max_reconnect_attempts: 最大重連嘗試次數
        _reconnect_interval: 重連間隔時間(秒)
        _status_callbacks: 狀態變更回調函數列表
    """

    def __init__(
        self,
        max_reconnect_attempts: int = 5,
        reconnect_interval: int = 30,
    ):
        """初始化券商連接管理服務

        Args:
            max_reconnect_attempts: 最大重連嘗試次數
            reconnect_interval: 重連間隔時間(秒)
        """
        if TradeExecutionBrokerManager:
            self._trade_executor = TradeExecutionBrokerManager(None)
        else:
            self._trade_executor = None
        self._connection_status: Dict[str, ConnectionStatus] = {}
        self._monitoring_thread: Optional[threading.Thread] = None
        self._is_monitoring = False
        self._reconnect_attempts: Dict[str, int] = {}
        self._max_reconnect_attempts = max_reconnect_attempts
        self._reconnect_interval = reconnect_interval
        self._status_callbacks: List[Callable[[str, ConnectionStatus], None]] = []
        self._lock = threading.Lock()

        # 初始化券商適配器
        try:
            if self._trade_executor and hasattr(self._trade_executor, 'init_brokers'):
                self._trade_executor.init_brokers()
            logger.info("券商連接管理服務初始化成功")
        except Exception as e:
            logger.error("券商連接管理服務初始化失敗: %s", e)
            raise BrokerConnectionError("服務初始化失敗") from e

    def start_monitoring(self) -> None:
        """開始連接監控

        啟動背景執行緒監控所有券商的連接狀態，
        並在連接異常時自動嘗試重連。

        Raises:
            BrokerConnectionError: 監控啟動失敗時拋出
        """
        if self._is_monitoring:
            logger.warning("連接監控已在運行中")
            return

        try:
            self._is_monitoring = True
            self._monitoring_thread = threading.Thread(
                target=self._monitor_connections,
                daemon=True
            )
            self._monitoring_thread.start()
            logger.info("券商連接監控已啟動")
        except Exception as e:
            self._is_monitoring = False
            logger.error("啟動連接監控失敗: %s", e)
            raise BrokerConnectionError("監控啟動失敗") from e

    def stop_monitoring(self) -> None:
        """停止連接監控

        停止背景監控執行緒，清理資源。
        """
        self._is_monitoring = False
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5)
        logger.info("券商連接監控已停止")

    def connect_broker(self, broker_name: str) -> bool:
        """連接指定券商

        Args:
            broker_name: 券商名稱 (simulator, shioaji, futu, ib)

        Returns:
            bool: 連接是否成功

        Raises:
            BrokerConnectionError: 連接失敗時拋出
        """
        try:
            self._update_status(broker_name, ConnectionStatus.CONNECTING)

            if not self._trade_executor or not hasattr(self._trade_executor, 'brokers'):
                raise BrokerConnectionError("交易執行器未正確初始化")

            if broker_name not in self._trade_executor.brokers:
                raise BrokerConnectionError(f"不支援的券商: {broker_name}")

            broker = self._trade_executor.brokers[broker_name]
            success = broker.connect()

            if success:
                self._update_status(broker_name, ConnectionStatus.CONNECTED)
                self._reconnect_attempts[broker_name] = 0
                logger.info("券商 %s 連接成功", broker_name)
                return success

            self._update_status(broker_name, ConnectionStatus.ERROR)
            logger.error("券商 %s 連接失敗", broker_name)
            return success

        except Exception as e:
            self._update_status(broker_name, ConnectionStatus.ERROR)
            logger.error("連接券商 %s 時發生錯誤: %s", broker_name, e)
            raise BrokerConnectionError(f"連接券商失敗: {broker_name}") from e

    def disconnect_broker(self, broker_name: str) -> bool:
        """斷開指定券商連接

        Args:
            broker_name: 券商名稱

        Returns:
            bool: 斷開是否成功
        """
        try:
            if broker_name not in self._trade_executor.brokers:
                logger.warning("券商 %s 不存在", broker_name)
                return False

            broker = self._trade_executor.brokers[broker_name]
            success = broker.disconnect()

            if success:
                self._update_status(broker_name, ConnectionStatus.DISCONNECTED)
                logger.info("券商 %s 已斷開連接", broker_name)
                return success

            logger.error("斷開券商 %s 連接失敗", broker_name)
            return success

        except Exception as e:
            logger.error("斷開券商 %s 連接時發生錯誤: %s", broker_name, e)
            return False

    def get_connection_status(
        self, broker_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """獲取連接狀態

        Args:
            broker_name: 券商名稱，為 None 時返回所有券商狀態

        Returns:
            Dict[str, Any]: 連接狀態資訊
        """
        with self._lock:
            if broker_name:
                return {
                    "broker": broker_name,
                    "status": self._connection_status.get(
                        broker_name,
                        ConnectionStatus.DISCONNECTED
                    ).value,
                    "reconnect_attempts": self._reconnect_attempts.get(broker_name, 0),
                    "last_update": datetime.now().isoformat()
                }

            return {
                broker: {
                    "status": status.value,
                    "reconnect_attempts": self._reconnect_attempts.get(broker, 0),
                    "last_update": datetime.now().isoformat()
                }
                for broker, status in self._connection_status.items()
            }

    def switch_broker(self, broker_name: str) -> bool:
        """切換當前使用的券商

        Args:
            broker_name: 目標券商名稱

        Returns:
            bool: 切換是否成功

        Raises:
            BrokerConnectionError: 切換失敗時拋出
        """
        try:
            # 檢查券商是否已連接
            if not self._is_broker_connected(broker_name):
                if not self.connect_broker(broker_name):
                    raise BrokerConnectionError(f"無法連接券商: {broker_name}")

            # 切換券商
            if self._trade_executor and hasattr(self._trade_executor, 'switch_broker'):
                success = self._trade_executor.switch_broker(broker_name)
                if success:
                    logger.info("已切換至券商: %s", broker_name)
                else:
                    logger.error("切換券商失敗: %s", broker_name)
                return success

            logger.warning("交易執行器不支援切換券商功能")
            return False

        except Exception as e:
            logger.error("切換券商時發生錯誤: %s", e)
            raise BrokerConnectionError("券商切換失敗") from e

    def add_status_callback(
        self, callback: Callable[[str, ConnectionStatus], None]
    ) -> None:
        """添加狀態變更回調函數

        Args:
            callback: 回調函數，接收券商名稱和新狀態
        """
        self._status_callbacks.append(callback)

    def _monitor_connections(self) -> None:
        """監控連接狀態的背景執行緒

        定期檢查所有券商的連接狀態，並在連接異常時嘗試重連。
        """
        while self._is_monitoring:
            try:
                for broker_name, broker in self._trade_executor.brokers.items():
                    self._check_broker_connection(broker_name, broker)

                time.sleep(10)  # 每10秒檢查一次

            except Exception as e:
                logger.error("連接監控執行緒發生錯誤: %s", e)
                time.sleep(30)  # 錯誤時等待更長時間

    def _check_broker_connection(self, broker_name: str, broker: BrokerBase) -> None:
        """檢查單個券商的連接狀態

        Args:
            broker_name: 券商名稱
            broker: 券商適配器實例
        """
        try:
            # 檢查連接狀態
            if hasattr(broker, 'connected') and not broker.connected:
                current_status = self._connection_status.get(
                    broker_name,
                    ConnectionStatus.DISCONNECTED
                )

                if current_status == ConnectionStatus.CONNECTED:
                    self._update_status(broker_name, ConnectionStatus.DISCONNECTED)
                    self._attempt_reconnect(broker_name)

        except Exception as e:
            logger.error("檢查券商 %s 連接狀態時發生錯誤: %s", broker_name, e)

    def _attempt_reconnect(self, broker_name: str) -> None:
        """嘗試重新連接券商

        Args:
            broker_name: 券商名稱
        """
        attempts = self._reconnect_attempts.get(broker_name, 0)

        if attempts >= self._max_reconnect_attempts:
            logger.warning("券商 %s 重連次數已達上限，停止重連", broker_name)
            return

        try:
            self._update_status(broker_name, ConnectionStatus.RECONNECTING)
            self._reconnect_attempts[broker_name] = attempts + 1

            logger.info("嘗試重連券商 %s (第 %d 次)", broker_name, attempts + 1)

            # 等待重連間隔
            time.sleep(self._reconnect_interval)

            # 嘗試重連
            if self.connect_broker(broker_name):
                logger.info("券商 %s 重連成功", broker_name)
            else:
                logger.error("券商 %s 重連失敗", broker_name)

        except Exception as e:
            logger.error("重連券商 %s 時發生錯誤: %s", broker_name, e)

    def _update_status(self, broker_name: str, status: ConnectionStatus) -> None:
        """更新券商連接狀態

        Args:
            broker_name: 券商名稱
            status: 新的連接狀態
        """
        with self._lock:
            old_status = self._connection_status.get(broker_name)
            self._connection_status[broker_name] = status

            # 觸發狀態變更回調
            if old_status != status:
                for callback in self._status_callbacks:
                    try:
                        callback(broker_name, status)
                    except Exception as e:
                        logger.error("執行狀態回調時發生錯誤: %s", e)

    def _is_broker_connected(self, broker_name: str) -> bool:
        """檢查券商是否已連接

        Args:
            broker_name: 券商名稱

        Returns:
            bool: 是否已連接
        """
        status = self._connection_status.get(broker_name, ConnectionStatus.DISCONNECTED)
        return status == ConnectionStatus.CONNECTED
