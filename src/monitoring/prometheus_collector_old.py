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
import time
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
            else:
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

    def _init_api_metrics(self) -> None:
        """
        初始化 API 效能指標

        包括回應時間、錯誤率、QPS 統計等 API 相關指標。
        """
        # API 請求指標
        self.metrics["api_requests_total"] = Counter(
            "api_requests_total",
            "API 請求總數",
            ["method", "endpoint", "status_code"],
            registry=self.registry,
        )

        # API 回應時間
        self.metrics["api_request_duration_seconds"] = Histogram(
            "api_request_duration_seconds",
            "API 請求持續時間（秒）",
            ["method", "endpoint"],
            buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry,
        )

        # API 錯誤率
        self.metrics["api_error_rate"] = Gauge(
            "api_error_rate", "API 錯誤率", ["endpoint"], registry=self.registry
        )

        # 活躍連接數
        self.metrics["api_active_connections"] = Gauge(
            "api_active_connections", "API 活躍連接數", registry=self.registry
        )

        # 佇列長度
        self.metrics["api_queue_length"] = Gauge(
            "api_queue_length",
            "API 請求佇列長度",
            ["queue_type"],
            registry=self.registry,
        )

    def _init_business_metrics(self) -> None:
        """
        初始化自定義業務指標

        包括策略績效、風險暴露、資金使用率等業務相關指標。
        """
        # 策略績效指標
        self.metrics["strategy_pnl"] = Gauge(
            "strategy_pnl", "策略損益", ["strategy_name"], registry=self.registry
        )

        self.metrics["strategy_sharpe_ratio"] = Gauge(
            "strategy_sharpe_ratio",
            "策略夏普比率",
            ["strategy_name"],
            registry=self.registry,
        )

        self.metrics["strategy_max_drawdown"] = Gauge(
            "strategy_max_drawdown_percent",
            "策略最大回撤百分比",
            ["strategy_name"],
            registry=self.registry,
        )

        # 風險指標
        self.metrics["portfolio_var"] = Gauge(
            "portfolio_var",
            "投資組合風險價值（VaR）",
            ["confidence_level"],
            registry=self.registry,
        )

        self.metrics["position_exposure"] = Gauge(
            "position_exposure", "部位暴露", ["symbol", "side"], registry=self.registry
        )

        # 系統健康指標
        self.metrics["system_health_score"] = Gauge(
            "system_health_score", "系統健康分數（0-100）", registry=self.registry
        )

        self.metrics["active_alerts"] = Gauge(
            "active_alerts_count", "活躍警報數量", ["severity"], registry=self.registry
        )

    def start_collection(self) -> bool:
        """
        啟動指標收集

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
                target=self._collection_loop, daemon=True, name="PrometheusCollector"
            )
            self._collection_thread.start()

            module_logger.info("Prometheus 指標收集已啟動")
            return True

        except Exception as e:
            module_logger.error(f"啟動指標收集失敗: {e}")
            self.is_collecting = False
            return False

    def stop_collection(self) -> bool:
        """
        停止指標收集

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

            module_logger.info("Prometheus 指標收集已停止")
            return True

        except Exception as e:
            module_logger.error(f"停止指標收集失敗: {e}")
            return False

    def _collection_loop(self) -> None:
        """
        指標收集主循環

        定期收集系統和業務指標，直到收到停止信號。
        """
        module_logger.info("指標收集循環已啟動")

        while not self._stop_event.is_set():
            try:
                start_time = time.time()

                # 收集系統指標
                self._collect_system_metrics()

                # 收集交易指標
                self._collect_trading_metrics()

                # 收集API指標
                self._collect_api_metrics()

                # 收集業務指標
                self._collect_business_metrics()

                collection_time = time.time() - start_time
                module_logger.debug(f"指標收集完成，耗時: {collection_time:.3f}秒")

                # 等待下次收集
                self._stop_event.wait(self.collection_interval)

            except Exception as e:
                module_logger.error(f"指標收集過程中發生錯誤: {e}")
                # 發生錯誤時等待較短時間後重試
                self._stop_event.wait(min(self.collection_interval, 30))

        module_logger.info("指標收集循環已結束")

    def _collect_system_metrics(self) -> None:
        """
        收集系統資源指標

        收集 CPU、記憶體、磁碟、網路等系統資源使用情況。
        """
        try:
            # CPU 指標
            cpu_percent = psutil.cpu_percent(interval=None)
            self.metrics["cpu_usage_percent"].set(cpu_percent)
            self.metrics["cpu_count"].set(psutil.cpu_count())

            # 記憶體指標
            memory = psutil.virtual_memory()
            self.metrics["memory_usage_percent"].set(memory.percent)
            self.metrics["memory_total_bytes"].set(memory.total)
            self.metrics["memory_available_bytes"].set(memory.available)

            # 磁碟指標
            disk_partitions = psutil.disk_partitions()
            for partition in disk_partitions:
                try:
                    disk_usage = psutil.disk_usage(partition.mountpoint)
                    mount_point = partition.mountpoint

                    self.metrics["disk_usage_percent"].labels(
                        mount_point=mount_point
                    ).set(disk_usage.percent)

                    self.metrics["disk_total_bytes"].labels(
                        mount_point=mount_point
                    ).set(disk_usage.total)

                    self.metrics["disk_free_bytes"].labels(mount_point=mount_point).set(
                        disk_usage.free
                    )

                except (PermissionError, OSError):
                    # 跳過無法存取的磁碟分區
                    continue

            # 網路指標
            network_io = psutil.net_io_counters(pernic=True)
            for interface, stats in network_io.items():
                # 更新計數器（Prometheus 會自動計算增量）
                self.metrics["network_bytes_sent"].labels(
                    interface=interface
                )._value._value = stats.bytes_sent

                self.metrics["network_bytes_recv"].labels(
                    interface=interface
                )._value._value = stats.bytes_recv

            # 進程指標
            self.metrics["process_count"].set(len(psutil.pids()))

            # 系統負載（僅在支援的系統上）
            if hasattr(os, "getloadavg"):
                load_avg = os.getloadavg()
                self.metrics["load_average_1m"].set(load_avg[0])
                self.metrics["load_average_5m"].set(load_avg[1])
                self.metrics["load_average_15m"].set(load_avg[2])

        except Exception as e:
            module_logger.error(f"收集系統指標失敗: {e}")

    def _collect_trading_metrics(self) -> None:
        """
        收集交易效能指標

        從交易系統收集訂單、成交、滑點等相關指標。
        """
        try:
            # 這裡應該從交易系統獲取實際數據
            # 目前使用模擬數據作為示例

            # 模擬訂單成功率
            self.metrics["order_success_rate"].labels(order_type="market").set(95.5)

            self.metrics["order_success_rate"].labels(order_type="limit").set(88.2)

            # 模擬資金使用率
            self.metrics["capital_utilization"].set(75.3)

        except Exception as e:
            module_logger.error(f"收集交易指標失敗: {e}")

    def _collect_api_metrics(self) -> None:
        """
        收集 API 效能指標

        從 API 服務收集回應時間、錯誤率等相關指標。
        """
        try:
            # 這裡應該從 API 服務獲取實際數據
            # 目前使用模擬數據作為示例

            # 模擬活躍連接數
            self.metrics["api_active_connections"].set(42)

            # 模擬佇列長度
            self.metrics["api_queue_length"].labels(queue_type="order").set(5)

            self.metrics["api_queue_length"].labels(queue_type="data").set(12)

        except Exception as e:
            module_logger.error(f"收集API指標失敗: {e}")

    def _collect_business_metrics(self) -> None:
        """
        收集自定義業務指標

        從業務系統收集策略績效、風險暴露等相關指標。
        """
        try:
            # 這裡應該從業務系統獲取實際數據
            # 目前使用模擬數據作為示例

            # 模擬系統健康分數
            self.metrics["system_health_score"].set(87.5)

            # 模擬活躍警報數量
            self.metrics["active_alerts"].labels(severity="INFO").set(2)
            self.metrics["active_alerts"].labels(severity="WARNING").set(1)
            self.metrics["active_alerts"].labels(severity="ERROR").set(0)
            self.metrics["active_alerts"].labels(severity="CRITICAL").set(0)

        except Exception as e:
            module_logger.error(f"收集業務指標失敗: {e}")

    def get_metrics(self) -> str:
        """
        獲取 Prometheus 格式的指標數據

        Returns:
            str: Prometheus 格式的指標數據
        """
        try:
            return generate_latest(self.registry).decode("utf-8")
        except Exception as e:
            module_logger.error(f"生成指標數據失敗: {e}")
            return ""

    def get_content_type(self) -> str:
        """
        獲取 Prometheus 指標的 Content-Type

        Returns:
            str: Prometheus 指標的 MIME 類型
        """
        return CONTENT_TYPE_LATEST

    def record_api_request(
        self, method: str, endpoint: str, status_code: int, duration: float
    ) -> None:
        """
        記錄 API 請求指標

        Args:
            method: HTTP 方法
            endpoint: API 端點
            status_code: HTTP 狀態碼
            duration: 請求持續時間（秒）
        """
        try:
            # 記錄請求總數
            self.metrics["api_requests_total"].labels(
                method=method, endpoint=endpoint, status_code=str(status_code)
            ).inc()

            # 記錄請求持續時間
            self.metrics["api_request_duration_seconds"].labels(
                method=method, endpoint=endpoint
            ).observe(duration)

        except Exception as e:
            module_logger.error(f"記錄API請求指標失敗: {e}")

    def record_trading_order(
        self, order_type: str, status: str, latency: Optional[float] = None
    ) -> None:
        """
        記錄交易訂單指標

        Args:
            order_type: 訂單類型
            status: 訂單狀態
            latency: 訂單延遲（秒），可選
        """
        try:
            # 記錄訂單總數
            self.metrics["orders_total"].labels(
                status=status, order_type=order_type
            ).inc()

            # 記錄訂單延遲
            if latency is not None:
                self.metrics["order_latency_seconds"].labels(
                    order_type=order_type
                ).observe(latency)

        except Exception as e:
            module_logger.error(f"記錄交易訂單指標失敗: {e}")

    def record_trade_execution(
        self,
        symbol: str,
        side: str,
        amount: float,
        slippage_bps: Optional[float] = None,
    ) -> None:
        """
        記錄交易成交指標

        Args:
            symbol: 交易標的
            side: 交易方向（buy/sell）
            amount: 成交金額
            slippage_bps: 滑點（基點），可選
        """
        try:
            # 記錄成交總數
            self.metrics["executions_total"].labels(symbol=symbol, side=side).inc()

            # 記錄成交金額
            self.metrics["execution_amount"].labels(symbol=symbol, side=side).inc(
                amount
            )

            # 記錄滑點
            if slippage_bps is not None:
                self.metrics["slippage_bps"].labels(symbol=symbol).observe(slippage_bps)

        except Exception as e:
            module_logger.error(f"記錄交易成交指標失敗: {e}")

    def update_strategy_metrics(
        self,
        strategy_name: str,
        pnl: float,
        sharpe_ratio: Optional[float] = None,
        max_drawdown: Optional[float] = None,
    ) -> None:
        """
        更新策略績效指標

        Args:
            strategy_name: 策略名稱
            pnl: 策略損益
            sharpe_ratio: 夏普比率，可選
            max_drawdown: 最大回撤百分比，可選
        """
        try:
            # 更新策略損益
            self.metrics["strategy_pnl"].labels(strategy_name=strategy_name).set(pnl)

            # 更新夏普比率
            if sharpe_ratio is not None:
                self.metrics["strategy_sharpe_ratio"].labels(
                    strategy_name=strategy_name
                ).set(sharpe_ratio)

            # 更新最大回撤
            if max_drawdown is not None:
                self.metrics["strategy_max_drawdown"].labels(
                    strategy_name=strategy_name
                ).set(max_drawdown)

        except Exception as e:
            module_logger.error(f"更新策略指標失敗: {e}")

    def get_metric_names(self) -> List[str]:
        """
        獲取所有已註冊的指標名稱

        Returns:
            List[str]: 指標名稱列表
        """
        return list(self.metrics.keys())

    def is_healthy(self) -> bool:
        """
        檢查收集器健康狀態

        Returns:
            bool: 健康返回 True，否則返回 False
        """
        return (
            self.is_collecting
            and self._collection_thread is not None
            and self._collection_thread.is_alive()
        )
