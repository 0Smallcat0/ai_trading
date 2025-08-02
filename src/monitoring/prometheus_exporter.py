"""
Prometheus 指標導出器

此模組提供 Prometheus 指標導出功能，用於收集和導出系統指標。
"""

import os
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import psutil
import requests
from prometheus_client import Counter, Gauge, Histogram, Info, start_http_server

# 導入配置
from src.config import CHECK_INTERVAL
from src.core.logger import get_logger

# 設置日誌
logger = get_logger("prometheus_exporter")


# 定義指標
class PrometheusExporter:
    """Prometheus 指標導出器"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """實現單例模式"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PrometheusExporter, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(
        self,
        port: int = 9090,
        collection_interval: int = CHECK_INTERVAL,
        api_endpoints: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        初始化 Prometheus 指標導出器

        Args:
            port: 指標導出端口
            collection_interval: 指標收集間隔（秒）
            api_endpoints: API 端點列表，用於監控 API 延遲
        """
        # 避免重複初始化
        if self._initialized:
            return

        self.port = port
        self.collection_interval = collection_interval
        self.api_endpoints = api_endpoints or []

        # 系統資源指標
        self.cpu_usage = Gauge("system_cpu_usage", "CPU 使用率（%）")
        self.memory_usage = Gauge("system_memory_usage", "內存使用率（%）")
        self.memory_available = Gauge("system_memory_available", "可用內存（字節）")
        self.disk_usage = Gauge("system_disk_usage", "磁盤使用率（%）")
        self.disk_free = Gauge("system_disk_free", "可用磁盤空間（字節）")

        # API 指標
        self.api_latency = Histogram(
            "api_latency_seconds",
            "API 延遲（秒）",
            ["endpoint", "method"],
            buckets=(
                0.01,
                0.025,
                0.05,
                0.075,
                0.1,
                0.25,
                0.5,
                0.75,
                1.0,
                2.5,
                5.0,
                7.5,
                10.0,
            ),
        )
        self.api_requests_total = Counter(
            "api_requests_total", "API 請求總數", ["endpoint", "method", "status"]
        )
        self.api_errors_total = Counter(
            "api_errors_total", "API 錯誤總數", ["endpoint", "method", "error_type"]
        )

        # 數據更新指標
        self.data_update_delay = Gauge(
            "data_update_delay_seconds", "數據更新延遲（秒）", ["data_type"]
        )
        self.data_update_success = Counter(
            "data_update_success_total", "數據更新成功次數", ["data_type"]
        )
        self.data_update_failure = Counter(
            "data_update_failure_total", "數據更新失敗次數", ["data_type"]
        )

        # 模型指標
        self.model_prediction_accuracy = Gauge(
            "model_prediction_accuracy", "模型預測準確率", ["model_name"]
        )
        self.model_prediction_latency = Histogram(
            "model_prediction_latency_seconds",
            "模型預測延遲（秒）",
            ["model_name"],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0),
        )
        self.model_drift = Gauge(
            "model_drift", "模型漂移指標", ["model_name", "metric"]
        )

        # 交易指標
        self.trade_success_rate = Gauge("trade_success_rate", "交易成功率")
        self.trade_count = Counter(
            "trade_count_total", "交易次數", ["direction", "status"]
        )
        self.capital_change = Gauge("capital_change_percent", "資本變化百分比")
        self.position_value = Gauge("position_value", "持倉價值", ["symbol"])

        # 系統信息
        self.system_info = Info("system_info", "系統信息")
        self.system_info.info(
            {
                "version": "1.0.0",
                "start_time": datetime.now().isoformat(),
                "hostname": os.uname().nodename if hasattr(os, "uname") else "unknown",
            }
        )

        # 監控線程
        self.monitoring_thread = None
        self.running = False

        # 標記為已初始化
        self._initialized = True
        logger.info(f"Prometheus 指標導出器已初始化，端口: {port}")

    def start(self):
        """啟動指標導出器"""
        if self.running:
            logger.warning("指標導出器已經在運行中")
            return

        # 啟動 HTTP 服務器
        try:
            start_http_server(self.port)
            logger.info(f"Prometheus 指標 HTTP 服務器已啟動，端口: {self.port}")
        except Exception as e:
            logger.error(f"啟動 Prometheus 指標 HTTP 服務器時發生錯誤: {e}")
            return

        # 啟動監控線程
        self.running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()

        logger.info("Prometheus 指標導出器已啟動")

    def stop(self):
        """停止指標導出器"""
        if not self.running:
            logger.warning("指標導出器未運行")
            return

        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)

        logger.info("Prometheus 指標導出器已停止")

    def _monitoring_loop(self):
        """監控循環"""
        while self.running:
            try:
                # 收集系統資源指標
                self._collect_system_metrics()

                # 收集 API 指標
                self._collect_api_metrics()

                # 等待下一個收集間隔
                time.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"指標收集循環發生錯誤: {e}")
                time.sleep(10)  # 發生錯誤時等待較長時間

    def _collect_system_metrics(self):
        """收集系統資源指標"""
        try:
            # 獲取 CPU 使用率
            cpu_usage = psutil.cpu_percent(interval=1)
            self.cpu_usage.set(cpu_usage)

            # 獲取內存使用率
            memory = psutil.virtual_memory()
            self.memory_usage.set(memory.percent)
            self.memory_available.set(memory.available)

            # 獲取磁盤使用率
            disk = psutil.disk_usage("/")
            self.disk_usage.set(disk.percent)
            self.disk_free.set(disk.free)
        except Exception as e:
            logger.error(f"收集系統資源指標時發生錯誤: {e}")

    def _collect_api_metrics(self):
        """收集 API 指標"""
        for endpoint in self.api_endpoints:
            try:
                url = endpoint.get("url")
                method = endpoint.get("method", "GET")
                headers = endpoint.get("headers", {})
                data = endpoint.get("data")

                # 測量 API 延遲
                start_time = time.time()
                response = requests.request(
                    method, url, headers=headers, json=data, timeout=10
                )
                latency = time.time() - start_time

                # 記錄指標
                self.api_latency.labels(endpoint=url, method=method).observe(latency)
                self.api_requests_total.labels(
                    endpoint=url, method=method, status=response.status_code
                ).inc()

                # 檢查錯誤
                if response.status_code >= 400:
                    self.api_errors_total.labels(
                        endpoint=url,
                        method=method,
                        error_type=f"HTTP_{response.status_code}",
                    ).inc()
            except Exception as e:
                logger.error(f"收集 API 指標時發生錯誤: {e}")
                self.api_errors_total.labels(
                    endpoint=url, method=method, error_type=type(e).__name__
                ).inc()

    def record_data_update(self, data_type: str, delay: float, success: bool):
        """
        記錄數據更新指標

        Args:
            data_type: 數據類型
            delay: 更新延遲（秒）
            success: 是否成功
        """
        self.data_update_delay.labels(data_type=data_type).set(delay)
        if success:
            self.data_update_success.labels(data_type=data_type).inc()
        else:
            self.data_update_failure.labels(data_type=data_type).inc()

    def record_model_metrics(
        self,
        model_name: str,
        accuracy: float,
        latency: float,
        drift_metrics: Dict[str, float],
    ):
        """
        記錄模型指標

        Args:
            model_name: 模型名稱
            accuracy: 預測準確率
            latency: 預測延遲（秒）
            drift_metrics: 漂移指標
        """
        self.model_prediction_accuracy.labels(model_name=model_name).set(accuracy)
        self.model_prediction_latency.labels(model_name=model_name).observe(latency)
        for metric_name, value in drift_metrics.items():
            self.model_drift.labels(model_name=model_name, metric=metric_name).set(
                value
            )

    def record_trade_metrics(
        self, success_rate: float, direction: str, status: str, capital_change: float
    ):
        """
        記錄交易指標

        Args:
            success_rate: 交易成功率
            direction: 交易方向 (buy/sell)
            status: 交易狀態 (success/failure)
            capital_change: 資本變化百分比
        """
        self.trade_success_rate.set(success_rate)
        self.trade_count.labels(direction=direction, status=status).inc()
        self.capital_change.set(capital_change)

    def record_position(self, symbol: str, value: float):
        """
        記錄持倉價值

        Args:
            symbol: 股票代碼
            value: 持倉價值
        """
        self.position_value.labels(symbol=symbol).set(value)


# 創建全局指標導出器實例
prometheus_exporter = PrometheusExporter()
