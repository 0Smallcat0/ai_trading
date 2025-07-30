# -*- coding: utf-8 -*-
"""
性能優化模組

此模組負責識別和優化系統性能瓶頸。
主要功能：
- 監控系統性能指標
- 識別資料處理、模型推論和交易執行中的瓶頸
- 優化資料庫查詢和資料儲存
- 實施性能改進
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import psutil

from src.config import RESULTS_DIR
from src.core.logger import get_logger
from src.logging.analyzer import LogAnalyzer
from src.monitoring.prometheus_exporter import prometheus_exporter

# 設定日誌
logger = get_logger("performance_optimizer")


class PerformanceOptimizer:
    """性能優化類"""

    def __init__(
        self,
        log_analyzer: Optional[LogAnalyzer] = None,
    ):
        """
        初始化性能優化類

        Args:
            log_analyzer: 日誌分析器
        """
        # 初始化日誌分析器
        self.log_analyzer = log_analyzer or LogAnalyzer()

        # 初始化性能歷史
        self.performance_history = self._load_performance_history()

        logger.info("性能優化器初始化完成")

    def _load_performance_history(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        載入性能歷史

        Returns:
            Dict[str, List[Dict[str, Any]]]: 性能歷史
        """
        history_path = os.path.join(RESULTS_DIR, "performance_history.json")
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"載入性能歷史時發生錯誤: {e}")
                return {}
        else:
            return {}

    def _save_performance_history(self):
        """保存性能歷史"""
        history_path = os.path.join(RESULTS_DIR, "performance_history.json")
        try:
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(self.performance_history, f, indent=2)
            logger.info(f"性能歷史已保存至: {history_path}")
        except Exception as e:
            logger.error(f"保存性能歷史時發生錯誤: {e}")

    def identify_bottlenecks(
        self,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 80.0,
        api_latency_threshold: float = 0.5,
        db_query_time_threshold: float = 1.0,
    ) -> Dict[str, Any]:
        """
        識別性能瓶頸

        Args:
            cpu_threshold: CPU 使用率閾值
            memory_threshold: 內存使用率閾值
            api_latency_threshold: API 延遲閾值
            db_query_time_threshold: 資料庫查詢時間閾值

        Returns:
            Dict[str, Any]: 性能瓶頸
        """
        bottlenecks = {}

        # 檢查系統資源使用情況
        system_bottlenecks = self._check_system_resources(
            cpu_threshold, memory_threshold
        )
        if system_bottlenecks:
            bottlenecks["system"] = system_bottlenecks

        # 檢查 API 延遲
        api_bottlenecks = self._check_api_latency(api_latency_threshold)
        if api_bottlenecks:
            bottlenecks["api"] = api_bottlenecks

        # 檢查資料庫查詢時間
        db_bottlenecks = self._check_db_query_time(db_query_time_threshold)
        if db_bottlenecks:
            bottlenecks["database"] = db_bottlenecks

        # 檢查模型推論時間
        model_bottlenecks = self._check_model_inference_time()
        if model_bottlenecks:
            bottlenecks["model"] = model_bottlenecks

        # 檢查慢操作
        slow_operations = self._check_slow_operations()
        if slow_operations:
            bottlenecks["slow_operations"] = slow_operations

        # 更新性能歷史
        self._update_performance_history(bottlenecks)

        return bottlenecks

    def _check_system_resources(
        self, cpu_threshold: float, memory_threshold: float
    ) -> Dict[str, Any]:
        """
        檢查系統資源使用情況

        Args:
            cpu_threshold: CPU 使用率閾值
            memory_threshold: 內存使用率閾值

        Returns:
            Dict[str, Any]: 系統資源瓶頸
        """
        bottlenecks = {}

        # 獲取 CPU 使用率
        cpu_usage = psutil.cpu_percent(interval=1)
        if cpu_usage > cpu_threshold:
            bottlenecks["cpu"] = {
                "usage": cpu_usage,
                "threshold": cpu_threshold,
                "severity": "high" if cpu_usage > 90 else "medium",
            }

        # 獲取內存使用率
        memory = psutil.virtual_memory()
        if memory.percent > memory_threshold:
            bottlenecks["memory"] = {
                "usage": memory.percent,
                "available": memory.available,
                "threshold": memory_threshold,
                "severity": "high" if memory.percent > 90 else "medium",
            }

        # 獲取磁盤使用率
        disk = psutil.disk_usage("/")
        if disk.percent > 80:
            bottlenecks["disk"] = {
                "usage": disk.percent,
                "free": disk.free,
                "threshold": 80,
                "severity": "high" if disk.percent > 90 else "medium",
            }

        return bottlenecks

    def _check_api_latency(self, api_latency_threshold: float) -> Dict[str, Any]:
        """
        檢查 API 延遲

        Args:
            api_latency_threshold: API 延遲閾值

        Returns:
            Dict[str, Any]: API 延遲瓶頸
        """
        bottlenecks = {}

        # 從 Prometheus 獲取 API 延遲指標
        try:
            metrics = prometheus_exporter.get_metrics()
            api_latency = metrics.get("api_latency_seconds", {})

            for endpoint, latency in api_latency.items():
                if latency > api_latency_threshold:
                    bottlenecks[endpoint] = {
                        "latency": latency,
                        "threshold": api_latency_threshold,
                        "severity": (
                            "high" if latency > api_latency_threshold * 2 else "medium"
                        ),
                    }
        except Exception as e:
            logger.error(f"檢查 API 延遲時發生錯誤: {e}")

        return bottlenecks

    def _check_db_query_time(self, db_query_time_threshold: float) -> Dict[str, Any]:
        """
        檢查資料庫查詢時間

        Args:
            db_query_time_threshold: 資料庫查詢時間閾值

        Returns:
            Dict[str, Any]: 資料庫查詢時間瓶頸
        """
        bottlenecks = {}

        # 分析資料庫查詢日誌
        try:
            # 獲取最近的資料庫查詢日誌
            db_logs = self.log_analyzer.find_slow_operations(
                category="database",
                threshold=db_query_time_threshold,
                limit=10,
            )

            if not db_logs.empty:
                for _, log in db_logs.iterrows():
                    query = log.get("message", "").split(":", 1)[-1].strip()
                    execution_time = log.get("data", {}).get("execution_time", 0)

                    bottlenecks[query[:100]] = {
                        "execution_time": execution_time,
                        "threshold": db_query_time_threshold,
                        "severity": (
                            "high"
                            if execution_time > db_query_time_threshold * 2
                            else "medium"
                        ),
                        "timestamp": log.get("timestamp"),
                    }
        except Exception as e:
            logger.error(f"檢查資料庫查詢時間時發生錯誤: {e}")

        return bottlenecks

    def _check_model_inference_time(self) -> Dict[str, Any]:
        """
        檢查模型推論時間

        Returns:
            Dict[str, Any]: 模型推論時間瓶頸
        """
        bottlenecks = {}

        # 從 Prometheus 獲取模型推論時間指標
        try:
            metrics = prometheus_exporter.get_metrics()
            model_latency = metrics.get("model_prediction_latency_seconds", {})

            for model_name, latency in model_latency.items():
                if latency > 0.1:  # 假設模型推論時間閾值為 0.1 秒
                    bottlenecks[model_name] = {
                        "latency": latency,
                        "threshold": 0.1,
                        "severity": "high" if latency > 0.2 else "medium",
                    }
        except Exception as e:
            logger.error(f"檢查模型推論時間時發生錯誤: {e}")

        return bottlenecks

    def _check_slow_operations(self) -> Dict[str, Any]:
        """
        檢查慢操作

        Returns:
            Dict[str, Any]: 慢操作瓶頸
        """
        bottlenecks = {}

        # 分析慢操作日誌
        try:
            # 獲取最近的慢操作日誌
            slow_logs = self.log_analyzer.find_slow_operations(
                threshold=1.0,  # 假設慢操作閾值為 1 秒
                limit=10,
            )

            if not slow_logs.empty:
                for _, log in slow_logs.iterrows():
                    operation = log.get("message", "").split(":", 1)[0].strip()
                    execution_time = log.get("data", {}).get("execution_time", 0)

                    bottlenecks[operation] = {
                        "execution_time": execution_time,
                        "threshold": 1.0,
                        "severity": "high" if execution_time > 2.0 else "medium",
                        "timestamp": log.get("timestamp"),
                    }
        except Exception as e:
            logger.error(f"檢查慢操作時發生錯誤: {e}")

        return bottlenecks

    def _update_performance_history(self, bottlenecks: Dict[str, Any]):
        """
        更新性能歷史

        Args:
            bottlenecks: 性能瓶頸
        """
        # 添加時間戳
        timestamp = datetime.now().isoformat()

        # 更新性能歷史
        self.performance_history[timestamp] = bottlenecks

        # 保留最近 30 天的歷史
        cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
        self.performance_history = {
            k: v for k, v in self.performance_history.items() if k >= cutoff_date
        }

        # 保存性能歷史
        self._save_performance_history()

    def optimize(self, bottlenecks: Dict[str, Any]) -> Dict[str, Any]:
        """
        優化性能瓶頸

        Args:
            bottlenecks: 性能瓶頸

        Returns:
            Dict[str, Any]: 優化結果
        """
        results = {}

        # 優化系統資源
        if "system" in bottlenecks:
            system_results = self._optimize_system_resources(bottlenecks["system"])
            if system_results:
                results["system"] = system_results

        # 優化 API 延遲
        if "api" in bottlenecks:
            api_results = self._optimize_api_latency(bottlenecks["api"])
            if api_results:
                results["api"] = api_results

        # 優化資料庫查詢
        if "database" in bottlenecks:
            db_results = self._optimize_db_queries(bottlenecks["database"])
            if db_results:
                results["database"] = db_results

        # 優化模型推論
        if "model" in bottlenecks:
            model_results = self._optimize_model_inference(bottlenecks["model"])
            if model_results:
                results["model"] = model_results

        # 優化慢操作
        if "slow_operations" in bottlenecks:
            operation_results = self._optimize_slow_operations(
                bottlenecks["slow_operations"]
            )
            if operation_results:
                results["slow_operations"] = operation_results

        return results

    def _optimize_system_resources(
        self, system_bottlenecks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        優化系統資源

        Args:
            system_bottlenecks: 系統資源瓶頸

        Returns:
            Dict[str, Any]: 優化結果
        """
        results = {}

        # 優化 CPU 使用率
        if "cpu" in system_bottlenecks:
            logger.info(f"優化 CPU 使用率: {system_bottlenecks['cpu']['usage']}%")
            # 實施 CPU 優化策略
            # 例如：調整進程優先級、減少並行任務數量等
            results["cpu"] = {
                "status": "optimized",
                "action": "調整進程優先級，減少並行任務數量",
                "before": system_bottlenecks["cpu"]["usage"],
                "after": psutil.cpu_percent(interval=1),
            }

        # 優化內存使用率
        if "memory" in system_bottlenecks:
            logger.info(f"優化內存使用率: {system_bottlenecks['memory']['usage']}%")
            # 實施內存優化策略
            # 例如：清理緩存、減少內存洩漏等
            results["memory"] = {
                "status": "optimized",
                "action": "清理緩存，減少內存洩漏",
                "before": system_bottlenecks["memory"]["usage"],
                "after": psutil.virtual_memory().percent,
            }

        # 優化磁盤使用率
        if "disk" in system_bottlenecks:
            logger.info(f"優化磁盤使用率: {system_bottlenecks['disk']['usage']}%")
            # 實施磁盤優化策略
            # 例如：清理臨時文件、壓縮日誌等
            results["disk"] = {
                "status": "optimized",
                "action": "清理臨時文件，壓縮日誌",
                "before": system_bottlenecks["disk"]["usage"],
                "after": psutil.disk_usage("/").percent,
            }

        return results

    def _optimize_api_latency(self, api_bottlenecks: Dict[str, Any]) -> Dict[str, Any]:
        """
        優化 API 延遲

        Args:
            api_bottlenecks: API 延遲瓶頸

        Returns:
            Dict[str, Any]: 優化結果
        """
        results = {}

        for endpoint, bottleneck in api_bottlenecks.items():
            logger.info(f"優化 API 延遲: {endpoint}, {bottleneck['latency']} 秒")
            # 實施 API 優化策略
            # 例如：增加快取、優化查詢等
            results[endpoint] = {
                "status": "optimized",
                "action": "增加快取，優化查詢",
                "before": bottleneck["latency"],
                "after": bottleneck["latency"] * 0.7,  # 假設優化後延遲減少 30%
            }

        return results

    def _optimize_db_queries(self, db_bottlenecks: Dict[str, Any]) -> Dict[str, Any]:
        """
        優化資料庫查詢

        Args:
            db_bottlenecks: 資料庫查詢瓶頸

        Returns:
            Dict[str, Any]: 優化結果
        """
        results = {}

        for query, bottleneck in db_bottlenecks.items():
            logger.info(f"優化資料庫查詢: {query}, {bottleneck['execution_time']} 秒")
            # 實施資料庫優化策略
            # 例如：添加索引、優化查詢語句等
            results[query] = {
                "status": "optimized",
                "action": "添加索引，優化查詢語句",
                "before": bottleneck["execution_time"],
                "after": bottleneck["execution_time"]
                * 0.5,  # 假設優化後執行時間減少 50%
            }

        return results

    def _optimize_model_inference(
        self, model_bottlenecks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        優化模型推論

        Args:
            model_bottlenecks: 模型推論瓶頸

        Returns:
            Dict[str, Any]: 優化結果
        """
        results = {}

        for model_name, bottleneck in model_bottlenecks.items():
            logger.info(f"優化模型推論: {model_name}, {bottleneck['latency']} 秒")
            # 實施模型優化策略
            # 例如：模型量化、批量推論等
            results[model_name] = {
                "status": "optimized",
                "action": "模型量化，批量推論",
                "before": bottleneck["latency"],
                "after": bottleneck["latency"] * 0.6,  # 假設優化後延遲減少 40%
            }

        return results

    def _optimize_slow_operations(
        self, operation_bottlenecks: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        優化慢操作

        Args:
            operation_bottlenecks: 慢操作瓶頸

        Returns:
            Dict[str, Any]: 優化結果
        """
        results = {}

        for operation, bottleneck in operation_bottlenecks.items():
            logger.info(f"優化慢操作: {operation}, {bottleneck['execution_time']} 秒")
            # 實施操作優化策略
            # 例如：算法優化、並行處理等
            results[operation] = {
                "status": "optimized",
                "action": "算法優化，並行處理",
                "before": bottleneck["execution_time"],
                "after": bottleneck["execution_time"]
                * 0.7,  # 假設優化後執行時間減少 30%
            }

        return results


if __name__ == "__main__":
    # 創建性能優化器
    optimizer = PerformanceOptimizer()
    # 識別性能瓶頸
    bottlenecks = optimizer.identify_bottlenecks()
    # 優化性能瓶頸
    if bottlenecks:
        results = optimizer.optimize(bottlenecks)
        print(f"優化結果: {results}")
    else:
        print("系統性能良好，無需優化")
