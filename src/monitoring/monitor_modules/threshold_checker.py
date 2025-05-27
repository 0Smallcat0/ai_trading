"""閾值檢查器

此模組實現各種指標的閾值檢查功能。
"""

import logging
from typing import Any, Dict, Optional

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class ThresholdChecker:
    """閾值檢查器

    檢查各種系統和業務指標是否超過預設閾值。

    Attributes:
        thresholds: 閾值配置字典
        alert_handler: 警報處理器
    """

    def __init__(self, thresholds: Dict[str, Any], alert_handler: Any):
        """初始化閾值檢查器

        Args:
            thresholds: 閾值配置字典
            alert_handler: 警報處理器

        Raises:
            ValueError: 當配置無效時
        """
        if not thresholds:
            raise ValueError("閾值配置不能為空")
        if not alert_handler:
            raise ValueError("警報處理器不能為空")

        self.thresholds = thresholds
        self.alert_handler = alert_handler

        module_logger.info("閾值檢查器初始化成功")

    def check_all_metrics(self, metrics: Dict[str, Any]) -> None:
        """檢查所有指標

        Args:
            metrics: 指標數據字典
        """
        try:
            # 檢查系統指標
            self.check_system_metrics(metrics)

            # 檢查 API 指標
            self.check_api_metrics(metrics)

            # 檢查模型指標
            self.check_model_metrics(metrics)

            # 檢查交易指標
            self.check_trade_metrics(metrics)

        except Exception as e:
            module_logger.error("檢查指標時發生錯誤: %s", e)

    def check_system_metrics(self, metrics: Dict[str, Any]) -> None:
        """檢查系統指標

        Args:
            metrics: 指標數據字典
        """
        try:
            system_metrics = metrics.get("system", {})
            system_thresholds = self.thresholds.get("system", {})

            # 檢查 CPU 使用率
            self._check_cpu_usage(system_metrics, system_thresholds)

            # 檢查記憶體使用率
            self._check_memory_usage(system_metrics, system_thresholds)

            # 檢查磁碟使用率
            self._check_disk_usage(system_metrics, system_thresholds)

        except Exception as e:
            module_logger.error("檢查系統指標失敗: %s", e)

    def _check_cpu_usage(
        self,
        system_metrics: Dict[str, Any],
        system_thresholds: Dict[str, Any]
    ) -> None:
        """檢查 CPU 使用率

        Args:
            system_metrics: 系統指標數據
            system_thresholds: 系統閾值配置
        """
        cpu_usage = system_metrics.get("cpu_usage")
        cpu_threshold = system_thresholds.get("cpu_usage", 80)

        if cpu_usage is not None and cpu_usage > cpu_threshold:
            self.alert_handler.create_system_alert(
                "高 CPU 使用率",
                f"CPU 使用率超過閾值: {cpu_usage:.2f}% > {cpu_threshold}%",
                {
                    "cpu_usage": cpu_usage,
                    "threshold": cpu_threshold,
                }
            )

    def _check_memory_usage(
        self,
        system_metrics: Dict[str, Any],
        system_thresholds: Dict[str, Any]
    ) -> None:
        """檢查記憶體使用率

        Args:
            system_metrics: 系統指標數據
            system_thresholds: 系統閾值配置
        """
        memory_usage = system_metrics.get("memory_usage")
        memory_threshold = system_thresholds.get("memory_usage", 80)

        if memory_usage is not None and memory_usage > memory_threshold:
            self.alert_handler.create_system_alert(
                "高記憶體使用率",
                f"記憶體使用率超過閾值: {memory_usage:.2f}% > {memory_threshold}%",
                {
                    "memory_usage": memory_usage,
                    "threshold": memory_threshold,
                }
            )

    def _check_disk_usage(
        self,
        system_metrics: Dict[str, Any],
        system_thresholds: Dict[str, Any]
    ) -> None:
        """檢查磁碟使用率

        Args:
            system_metrics: 系統指標數據
            system_thresholds: 系統閾值配置
        """
        disk_usage = system_metrics.get("disk_usage")
        disk_threshold = system_thresholds.get("disk_usage", 85)

        if disk_usage is not None and disk_usage > disk_threshold:
            self.alert_handler.create_system_alert(
                "高磁碟使用率",
                f"磁碟使用率超過閾值: {disk_usage:.2f}% > {disk_threshold}%",
                {
                    "disk_usage": disk_usage,
                    "threshold": disk_threshold,
                }
            )

    def check_api_metrics(self, metrics: Dict[str, Any]) -> None:
        """檢查 API 指標

        Args:
            metrics: 指標數據字典
        """
        try:
            api_metrics = metrics.get("api", {})
            api_thresholds = self.thresholds.get("api", {})

            # 檢查 API 延遲
            self._check_api_latency(api_metrics, api_thresholds)

            # 檢查 API 錯誤率
            self._check_api_error_rate(api_metrics, api_thresholds)

        except Exception as e:
            module_logger.error("檢查 API 指標失敗: %s", e)

    def _check_api_latency(
        self,
        api_metrics: Dict[str, Any],
        api_thresholds: Dict[str, Any]
    ) -> None:
        """檢查 API 延遲

        Args:
            api_metrics: API 指標數據
            api_thresholds: API 閾值配置
        """
        api_latency = api_metrics.get("latency", {})
        latency_threshold = api_thresholds.get("latency", 1.0)

        for endpoint, latency in api_latency.items():
            if latency > latency_threshold:
                self.alert_handler.create_api_alert(
                    "高 API 延遲",
                    f"API 延遲超過閾值: {endpoint} - {latency:.2f}s > {latency_threshold}s",
                    {
                        "endpoint": endpoint,
                        "latency": latency,
                        "threshold": latency_threshold,
                    }
                )

    def _check_api_error_rate(
        self,
        api_metrics: Dict[str, Any],
        api_thresholds: Dict[str, Any]
    ) -> None:
        """檢查 API 錯誤率

        Args:
            api_metrics: API 指標數據
            api_thresholds: API 閾值配置
        """
        api_requests = api_metrics.get("requests_total", {})
        api_errors = api_metrics.get("errors_total", {})
        error_rate_threshold = api_thresholds.get("error_rate", 0.05)

        for endpoint in api_requests:
            if endpoint in api_errors and api_requests[endpoint] > 0:
                error_rate = api_errors[endpoint] / api_requests[endpoint]
                if error_rate > error_rate_threshold:
                    self.alert_handler.create_api_alert(
                        "高 API 錯誤率",
                        f"API 錯誤率超過閾值: {endpoint} - {error_rate:.2%} > {error_rate_threshold:.2%}",
                        {
                            "endpoint": endpoint,
                            "error_rate": error_rate,
                            "threshold": error_rate_threshold,
                            "requests": api_requests[endpoint],
                            "errors": api_errors[endpoint],
                        }
                    )

    def check_model_metrics(self, metrics: Dict[str, Any]) -> None:
        """檢查模型指標

        Args:
            metrics: 指標數據字典
        """
        try:
            model_metrics = metrics.get("model", {})
            model_thresholds = self.thresholds.get("model", {})

            # 檢查模型準確率
            self._check_model_accuracy(model_metrics, model_thresholds)

            # 檢查模型延遲
            self._check_model_latency(model_metrics, model_thresholds)

            # 檢查模型漂移
            self._check_model_drift(model_metrics, model_thresholds)

        except Exception as e:
            module_logger.error("檢查模型指標失敗: %s", e)

    def _check_model_accuracy(
        self,
        model_metrics: Dict[str, Any],
        model_thresholds: Dict[str, Any]
    ) -> None:
        """檢查模型準確率

        Args:
            model_metrics: 模型指標數據
            model_thresholds: 模型閾值配置
        """
        model_accuracy = model_metrics.get("prediction_accuracy", {})
        accuracy_threshold = model_thresholds.get("accuracy", 0.8)

        for model_name, accuracy in model_accuracy.items():
            if accuracy < accuracy_threshold:
                self.alert_handler.create_model_alert(
                    "低模型準確率",
                    f"模型準確率低於閾值: {model_name} - {accuracy:.2%} < {accuracy_threshold:.2%}",
                    {
                        "model_name": model_name,
                        "accuracy": accuracy,
                        "threshold": accuracy_threshold,
                    }
                )

    def _check_model_latency(
        self,
        model_metrics: Dict[str, Any],
        model_thresholds: Dict[str, Any]
    ) -> None:
        """檢查模型延遲

        Args:
            model_metrics: 模型指標數據
            model_thresholds: 模型閾值配置
        """
        model_latency = model_metrics.get("prediction_latency", {})
        latency_threshold = model_thresholds.get("latency", 1.0)

        for model_name, latency in model_latency.items():
            if latency > latency_threshold:
                self.alert_handler.create_model_alert(
                    "高模型延遲",
                    f"模型延遲超過閾值: {model_name} - {latency:.2f}s > {latency_threshold}s",
                    {
                        "model_name": model_name,
                        "latency": latency,
                        "threshold": latency_threshold,
                    }
                )

    def _check_model_drift(
        self,
        model_metrics: Dict[str, Any],
        model_thresholds: Dict[str, Any]
    ) -> None:
        """檢查模型漂移

        Args:
            model_metrics: 模型指標數據
            model_thresholds: 模型閾值配置
        """
        model_drift = model_metrics.get("drift", {})
        drift_threshold = model_thresholds.get("drift", 0.1)

        for model_name, drift in model_drift.items():
            if drift > drift_threshold:
                self.alert_handler.create_model_alert(
                    "高模型漂移",
                    f"模型漂移超過閾值: {model_name} - {drift:.2f} > {drift_threshold}",
                    {
                        "model_name": model_name,
                        "drift": drift,
                        "threshold": drift_threshold,
                    }
                )

    def check_trade_metrics(self, metrics: Dict[str, Any]) -> None:
        """檢查交易指標

        Args:
            metrics: 指標數據字典
        """
        try:
            trade_metrics = metrics.get("trade", {})
            trade_thresholds = self.thresholds.get("trade", {})

            # 檢查交易成功率
            self._check_trade_success_rate(trade_metrics, trade_thresholds)

            # 檢查資本變化
            self._check_capital_change(trade_metrics, trade_thresholds)

        except Exception as e:
            module_logger.error("檢查交易指標失敗: %s", e)

    def _check_trade_success_rate(
        self,
        trade_metrics: Dict[str, Any],
        trade_thresholds: Dict[str, Any]
    ) -> None:
        """檢查交易成功率

        Args:
            trade_metrics: 交易指標數據
            trade_thresholds: 交易閾值配置
        """
        success_rate = trade_metrics.get("success_rate")
        success_rate_threshold = trade_thresholds.get("success_rate", 0.7)

        if success_rate is not None and success_rate < success_rate_threshold:
            self.alert_handler.create_trade_alert(
                "低交易成功率",
                f"交易成功率低於閾值: {success_rate:.2%} < {success_rate_threshold:.2%}",
                {
                    "success_rate": success_rate,
                    "threshold": success_rate_threshold,
                }
            )

    def _check_capital_change(
        self,
        trade_metrics: Dict[str, Any],
        trade_thresholds: Dict[str, Any]
    ) -> None:
        """檢查資本變化

        Args:
            trade_metrics: 交易指標數據
            trade_thresholds: 交易閾值配置
        """
        capital_change = trade_metrics.get("capital_change")
        capital_change_threshold = trade_thresholds.get("capital_change", -10.0)

        if capital_change is not None and capital_change < capital_change_threshold:
            self.alert_handler.create_trade_alert(
                "資本大幅下降",
                f"資本下降超過閾值: {capital_change:.2f}% < {capital_change_threshold}%",
                {
                    "capital_change": capital_change,
                    "threshold": capital_change_threshold,
                },
                severity="critical"
            )
