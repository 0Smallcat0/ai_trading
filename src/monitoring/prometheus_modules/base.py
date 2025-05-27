"""Prometheus 指標收集器基礎類別

此模組定義了 Prometheus 指標收集器的基礎架構和共用功能。
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

try:
    from prometheus_client import CollectorRegistry
except ImportError:
    CollectorRegistry = None

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class PrometheusCollectorBase(ABC):
    """Prometheus 指標收集器基礎類別

    提供指標收集器的基本架構和共用功能。

    Attributes:
        registry: Prometheus 指標註冊表
        metrics: 已註冊的指標字典
        collection_interval: 指標收集間隔（秒）
        is_collecting: 是否正在收集指標
    """

    def __init__(self, collection_interval: int = 15):
        """初始化 Prometheus 指標收集器基礎類別

        Args:
            collection_interval: 指標收集間隔，預設 15 秒

        Raises:
            ImportError: 當 prometheus_client 套件未安裝時
        """
        if CollectorRegistry is None:
            raise ImportError("prometheus_client 套件未安裝")

        self.registry = CollectorRegistry()
        self.metrics: Dict[str, Any] = {}
        self.collection_interval = collection_interval
        self.is_collecting = False
        self._collection_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        module_logger.info("Prometheus 指標收集器基礎類別初始化成功")

    @abstractmethod
    def _init_metrics(self) -> None:
        """初始化指標

        子類別必須實現此方法來定義具體的指標。
        """
        pass

    @abstractmethod
    def _collect_metrics(self) -> None:
        """收集指標

        子類別必須實現此方法來收集具體的指標數據。
        """
        pass

    def start_collection(self) -> bool:
        """啟動指標收集

        Returns:
            bool: 啟動成功返回 True，否則返回 False
        """
        try:
            if self.is_collecting:
                module_logger.warning("指標收集已在運行中")
                return True

            self.is_collecting = True
            self._stop_event.clear()

            # 啟動收集線程
            self._collection_thread = threading.Thread(
                target=self._collection_loop,
                daemon=True,
                name=f"{self.__class__.__name__}Thread"
            )
            self._collection_thread.start()

            module_logger.info("指標收集已啟動")
            return True

        except Exception as e:
            module_logger.error("啟動指標收集失敗: %s", e)
            self.is_collecting = False
            return False

    def stop_collection(self) -> bool:
        """停止指標收集

        Returns:
            bool: 停止成功返回 True，否則返回 False
        """
        try:
            if not self.is_collecting:
                module_logger.warning("指標收集未在運行")
                return True

            self.is_collecting = False
            self._stop_event.set()

            # 等待收集線程結束
            if self._collection_thread and self._collection_thread.is_alive():
                self._collection_thread.join(timeout=5.0)

            module_logger.info("指標收集已停止")
            return True

        except Exception as e:
            module_logger.error("停止指標收集失敗: %s", e)
            return False

    def _collection_loop(self) -> None:
        """指標收集主循環

        定期收集指標，直到收到停止信號。
        """
        module_logger.info("指標收集循環已啟動")

        while not self._stop_event.is_set():
            try:
                start_time = time.time()

                # 收集指標
                self._collect_metrics()

                collection_time = time.time() - start_time
                module_logger.debug("指標收集完成，耗時: %.3f秒", collection_time)

                # 等待下次收集
                self._stop_event.wait(self.collection_interval)

            except Exception as e:
                module_logger.error("指標收集過程中發生錯誤: %s", e)
                # 發生錯誤時等待較短時間後重試
                self._stop_event.wait(min(self.collection_interval, 30))

        module_logger.info("指標收集循環已結束")

    def is_healthy(self) -> bool:
        """檢查收集器健康狀態

        Returns:
            bool: 健康返回 True，否則返回 False
        """
        return (
            self.is_collecting
            and self._collection_thread is not None
            and self._collection_thread.is_alive()
        )

    def get_metric_names(self) -> list:
        """獲取所有已註冊的指標名稱

        Returns:
            list: 指標名稱列表
        """
        return list(self.metrics.keys())
