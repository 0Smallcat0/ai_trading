"""Prometheus 指標收集器

此模組實現了 Prometheus 指標收集功能，整合各個子模組：
- 系統資源指標收集（CPU、記憶體、磁碟、網路）
- 交易效能指標（訂單延遲、成交率、滑點統計）
- API效能監控（回應時間、錯誤率、QPS統計）
- 自定義業務指標（策略績效、風險暴露、資金使用率）

遵循 Google Style Docstring 標準和 Phase 5.3 開發規範。
"""

import logging
import threading
from typing import Any, Dict, List, Optional

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        generate_latest,
    )
except ImportError:
    # 提供 fallback 以避免匯入錯誤
    CollectorRegistry = None
    generate_latest = None
    CONTENT_TYPE_LATEST = "text/plain"

try:
    from .prometheus_modules import (
        APIMetricsCollector,
        BusinessMetricsCollector,
        SystemMetricsCollector,
        TradingMetricsCollector,
    )
except ImportError:
    # 提供 fallback
    SystemMetricsCollector = None
    TradingMetricsCollector = None
    APIMetricsCollector = None
    BusinessMetricsCollector = None

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class PrometheusCollector:
    """Prometheus 指標收集器

    整合各個子模組的指標收集器，提供統一的介面。

    Attributes:
        registry: Prometheus 指標註冊表
        collectors: 子收集器字典
        collection_interval: 指標收集間隔（秒）
        is_collecting: 是否正在收集指標
    """

    def __init__(self, collection_interval: int = 15):
        """初始化 Prometheus 指標收集器

        Args:
            collection_interval: 指標收集間隔，預設 15 秒

        Raises:
            ImportError: 當必要套件未安裝時
        """
        if CollectorRegistry is None:
            raise ImportError("prometheus_client 套件未安裝")

        self.registry = CollectorRegistry()
        self.collectors: Dict[str, Any] = {}
        self.collection_interval = collection_interval
        self.is_collecting = False
        self._collection_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # 初始化子收集器
        self._init_collectors()

        module_logger.info("Prometheus 指標收集器初始化成功")

    def _init_collectors(self) -> None:
        """初始化各個子收集器"""
        try:
            # 初始化系統指標收集器
            if SystemMetricsCollector is not None:
                self.collectors["system"] = SystemMetricsCollector(
                    self.collection_interval
                )
                module_logger.info("系統指標收集器初始化成功")

            # 初始化交易指標收集器
            if TradingMetricsCollector is not None:
                self.collectors["trading"] = TradingMetricsCollector(
                    self.collection_interval
                )
                module_logger.info("交易指標收集器初始化成功")

            # 初始化 API 指標收集器
            if APIMetricsCollector is not None:
                self.collectors["api"] = APIMetricsCollector(
                    self.collection_interval
                )
                module_logger.info("API 指標收集器初始化成功")

            # 初始化業務指標收集器
            if BusinessMetricsCollector is not None:
                self.collectors["business"] = BusinessMetricsCollector(
                    self.collection_interval
                )
                module_logger.info("業務指標收集器初始化成功")

        except Exception as e:
            module_logger.error("初始化子收集器失敗: %s", e)
            raise

    def start_collection(self) -> bool:
        """啟動所有子收集器的指標收集

        Returns:
            bool: 啟動成功返回 True，否則返回 False
        """
        try:
            if self.is_collecting:
                module_logger.warning("指標收集已在運行中")
                return True

            success_count = 0
            total_count = len(self.collectors)

            for name, collector in self.collectors.items():
                try:
                    if collector.start_collection():
                        success_count += 1
                        module_logger.info("子收集器 %s 啟動成功", name)
                    else:
                        module_logger.error("子收集器 %s 啟動失敗", name)
                except Exception as e:
                    module_logger.error("啟動子收集器 %s 時發生錯誤: %s", name, e)

            if success_count > 0:
                self.is_collecting = True
                module_logger.info(
                    "指標收集已啟動，成功啟動 %d/%d 個子收集器",
                    success_count,
                    total_count
                )
                return True

            module_logger.error("所有子收集器啟動失敗")
            return False

        except Exception as e:
            module_logger.error("啟動指標收集失敗: %s", e)
            return False

    def stop_collection(self) -> bool:
        """停止所有子收集器的指標收集

        Returns:
            bool: 停止成功返回 True，否則返回 False
        """
        try:
            if not self.is_collecting:
                module_logger.warning("指標收集未在運行")
                return True

            success_count = 0
            total_count = len(self.collectors)

            for name, collector in self.collectors.items():
                try:
                    if collector.stop_collection():
                        success_count += 1
                        module_logger.info("子收集器 %s 停止成功", name)
                    else:
                        module_logger.error("子收集器 %s 停止失敗", name)
                except Exception as e:
                    module_logger.error("停止子收集器 %s 時發生錯誤: %s", name, e)

            self.is_collecting = False
            module_logger.info(
                "指標收集已停止，成功停止 %d/%d 個子收集器",
                success_count,
                total_count
            )
            return True

        except Exception as e:
            module_logger.error("停止指標收集失敗: %s", e)
            return False

    def get_metrics(self) -> str:
        """獲取 Prometheus 格式的指標數據

        Returns:
            str: Prometheus 格式的指標數據
        """
        try:
            if generate_latest is None:
                return ""

            # 合併所有子收集器的註冊表
            combined_metrics = []

            for name, collector in self.collectors.items():
                try:
                    if hasattr(collector, 'registry') and collector.registry:
                        metrics_data = generate_latest(collector.registry)
                        combined_metrics.append(metrics_data.decode("utf-8"))
                except Exception as e:
                    module_logger.error("獲取子收集器 %s 指標失敗: %s", name, e)

            return "\n".join(combined_metrics)

        except Exception as e:
            module_logger.error("生成指標數據失敗: %s", e)
            return ""

    def get_content_type(self) -> str:
        """獲取 Prometheus 指標的 Content-Type

        Returns:
            str: Prometheus 指標的 MIME 類型
        """
        return CONTENT_TYPE_LATEST

    def is_healthy(self) -> bool:
        """檢查收集器健康狀態

        Returns:
            bool: 健康返回 True，否則返回 False
        """
        if not self.is_collecting:
            return False

        # 檢查所有子收集器的健康狀態
        healthy_count = 0
        total_count = len(self.collectors)

        for collector in self.collectors.values():
            try:
                if hasattr(collector, 'is_healthy') and collector.is_healthy():
                    healthy_count += 1
            except Exception:
                continue

        # 至少有一半的子收集器健康才認為整體健康
        return healthy_count >= (total_count / 2) if total_count > 0 else False

    def get_collector_status(self) -> Dict[str, Any]:
        """獲取所有子收集器的狀態

        Returns:
            Dict[str, Any]: 子收集器狀態字典
        """
        status = {
            "is_collecting": self.is_collecting,
            "collection_interval": self.collection_interval,
            "collectors": {}
        }

        for name, collector in self.collectors.items():
            try:
                collector_status = {
                    "is_healthy": (
                        hasattr(collector, 'is_healthy')
                        and collector.is_healthy()
                    ),
                    "is_collecting": (
                        hasattr(collector, 'is_collecting')
                        and collector.is_collecting
                    ),
                    "metric_count": (
                        len(collector.metrics)
                        if hasattr(collector, 'metrics')
                        else 0
                    )
                }
                status["collectors"][name] = collector_status
            except Exception as e:
                status["collectors"][name] = {
                    "error": str(e),
                    "is_healthy": False
                }

        return status

    def get_collector(self, name: str) -> Optional[Any]:
        """獲取指定的子收集器

        Args:
            name: 子收集器名稱

        Returns:
            Optional[Any]: 子收集器實例，如果不存在則返回 None
        """
        return self.collectors.get(name)

    def get_metric_names(self) -> List[str]:
        """獲取所有已註冊的指標名稱

        Returns:
            List[str]: 指標名稱列表
        """
        metric_names = []

        for collector in self.collectors.values():
            try:
                if hasattr(collector, 'get_metric_names'):
                    metric_names.extend(collector.get_metric_names())
            except Exception as e:
                module_logger.error("獲取指標名稱失敗: %s", e)

        return metric_names
