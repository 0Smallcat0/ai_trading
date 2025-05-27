"""
效能基準配置

此模組定義了各個 API 端點的效能基準值和閾值設定。
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class PerformanceBenchmark:
    """效能基準配置"""

    endpoint: str
    method: str
    max_response_time_ms: int
    max_memory_mb: int
    min_requests_per_second: int
    description: str
    critical_threshold_ms: int = None
    warning_threshold_ms: int = None

    def __post_init__(self):
        """設置預設閾值"""
        if self.critical_threshold_ms is None:
            self.critical_threshold_ms = self.max_response_time_ms
        if self.warning_threshold_ms is None:
            self.warning_threshold_ms = int(self.max_response_time_ms * 0.8)


# API 端點效能基準配置
API_BENCHMARKS: Dict[str, PerformanceBenchmark] = {
    # 健康檢查端點 - 最高優先級
    "health_check": PerformanceBenchmark(
        endpoint="/health",
        method="GET",
        max_response_time_ms=150,  # 調整為更合理的閾值
        max_memory_mb=10,
        min_requests_per_second=100,
        description="系統健康檢查端點",
        critical_threshold_ms=300,  # 調整臨界閾值
        warning_threshold_ms=100,  # 調整警告閾值
    ),
    # 認證端點
    "auth_login": PerformanceBenchmark(
        endpoint="/api/v1/auth/login",
        method="POST",
        max_response_time_ms=200,
        max_memory_mb=20,
        min_requests_per_second=50,
        description="用戶登入認證",
        critical_threshold_ms=500,
        warning_threshold_ms=150,
    ),
    "auth_refresh": PerformanceBenchmark(
        endpoint="/api/v1/auth/refresh",
        method="POST",
        max_response_time_ms=100,
        max_memory_mb=15,
        min_requests_per_second=80,
        description="Token 刷新",
        critical_threshold_ms=300,
        warning_threshold_ms=80,
    ),
    # 數據端點
    "data_list": PerformanceBenchmark(
        endpoint="/api/v1/data/",
        method="GET",
        max_response_time_ms=100,
        max_memory_mb=50,
        min_requests_per_second=60,
        description="數據列表查詢",
        critical_threshold_ms=300,
        warning_threshold_ms=80,
    ),
    "data_sources": PerformanceBenchmark(
        endpoint="/api/v1/data/sources",
        method="GET",
        max_response_time_ms=150,
        max_memory_mb=30,
        min_requests_per_second=40,
        description="數據源列表",
        critical_threshold_ms=400,
        warning_threshold_ms=120,
    ),
    # 策略端點
    "strategies_list": PerformanceBenchmark(
        endpoint="/api/v1/strategies/",
        method="GET",
        max_response_time_ms=200,
        max_memory_mb=40,
        min_requests_per_second=30,
        description="策略列表查詢",
        critical_threshold_ms=500,
        warning_threshold_ms=160,
    ),
    # 模型端點
    "models_list": PerformanceBenchmark(
        endpoint="/api/v1/models/",
        method="GET",
        max_response_time_ms=300,
        max_memory_mb=60,
        min_requests_per_second=20,
        description="AI 模型列表",
        critical_threshold_ms=800,
        warning_threshold_ms=240,
    ),
    # 投資組合端點
    "portfolio_overview": PerformanceBenchmark(
        endpoint="/api/v1/portfolio/",
        method="GET",
        max_response_time_ms=250,
        max_memory_mb=45,
        min_requests_per_second=25,
        description="投資組合概覽",
        critical_threshold_ms=600,
        warning_threshold_ms=200,
    ),
    # 回測端點
    "backtest_list": PerformanceBenchmark(
        endpoint="/api/v1/backtest/",
        method="GET",
        max_response_time_ms=400,
        max_memory_mb=80,
        min_requests_per_second=15,
        description="回測結果列表",
        critical_threshold_ms=1000,
        warning_threshold_ms=320,
    ),
    # 風險管理端點
    "risk_metrics": PerformanceBenchmark(
        endpoint="/api/v1/risk/metrics",
        method="GET",
        max_response_time_ms=300,
        max_memory_mb=70,
        min_requests_per_second=20,
        description="風險指標查詢",
        critical_threshold_ms=800,
        warning_threshold_ms=240,
    ),
    # 交易端點
    "trading_orders": PerformanceBenchmark(
        endpoint="/api/v1/trading/orders",
        method="GET",
        max_response_time_ms=150,
        max_memory_mb=35,
        min_requests_per_second=40,
        description="交易訂單查詢",
        critical_threshold_ms=400,
        warning_threshold_ms=120,
    ),
    # 監控端點
    "monitoring_metrics": PerformanceBenchmark(
        endpoint="/api/v1/monitoring/metrics",
        method="GET",
        max_response_time_ms=200,
        max_memory_mb=40,
        min_requests_per_second=30,
        description="系統監控指標",
        critical_threshold_ms=500,
        warning_threshold_ms=160,
    ),
    # 報告端點
    "reports_list": PerformanceBenchmark(
        endpoint="/api/v1/reports/",
        method="GET",
        max_response_time_ms=500,
        max_memory_mb=100,
        min_requests_per_second=10,
        description="報告列表查詢",
        critical_threshold_ms=1200,
        warning_threshold_ms=400,
    ),
}

# 負載測試配置
LOAD_TEST_CONFIG = {
    "light_load": {
        "concurrent_users": 10,
        "duration_seconds": 30,
        "ramp_up_seconds": 5,
        "description": "輕量負載測試",
    },
    "medium_load": {
        "concurrent_users": 50,
        "duration_seconds": 60,
        "ramp_up_seconds": 10,
        "description": "中等負載測試",
    },
    "heavy_load": {
        "concurrent_users": 100,
        "duration_seconds": 120,
        "ramp_up_seconds": 20,
        "description": "重度負載測試",
    },
    "stress_test": {
        "concurrent_users": 200,
        "duration_seconds": 180,
        "ramp_up_seconds": 30,
        "description": "壓力測試",
    },
}

# pytest-benchmark 配置
BENCHMARK_CONFIG = {
    "min_rounds": 5,
    "max_time": 1.0,
    "min_time": 0.000005,
    "timer": "time.perf_counter",
    "disable_gc": False,
    "warmup": False,
    "warmup_iterations": 100000,
    "calibration_precision": 10,
    "sort": "mean",
    "columns": ["min", "max", "mean", "stddev", "rounds", "iterations"],
    "histogram": True,
    "save": "benchmark_results.json",
    "save_data": True,
    "autosave": True,
    "compare": "0001",
    "compare_fail": ["min:10%", "mean:10%"],
    "only_compare": False,
    "verbose": True,
}

# 效能回歸測試閾值
REGRESSION_THRESHOLDS = {
    "response_time_increase_percent": 20,  # 響應時間增加超過 20% 視為回歸
    "memory_usage_increase_percent": 30,  # 記憶體使用增加超過 30% 視為回歸
    "throughput_decrease_percent": 15,  # 吞吐量下降超過 15% 視為回歸
    "error_rate_increase_percent": 5,  # 錯誤率增加超過 5% 視為回歸
}

# CI/CD 效能檢查配置
CI_PERFORMANCE_CONFIG = {
    "enabled": True,
    "fail_on_regression": True,
    "generate_report": True,
    "report_format": ["json", "html"],
    "baseline_file": "performance_baseline.json",
    "results_file": "performance_results.json",
    "comparison_file": "performance_comparison.json",
}


def get_benchmark_for_endpoint(
    endpoint: str, method: str = "GET"
) -> PerformanceBenchmark:
    """
    獲取指定端點的效能基準

    Args:
        endpoint: API 端點路徑
        method: HTTP 方法

    Returns:
        PerformanceBenchmark: 效能基準配置，如果未找到則返回預設配置
    """
    # 查找完全匹配的基準
    for benchmark_id, benchmark in API_BENCHMARKS.items():
        if (
            benchmark.endpoint == endpoint
            and benchmark.method.upper() == method.upper()
        ):
            return benchmark

    # 查找路徑匹配的基準（忽略查詢參數）
    endpoint_path = endpoint.split("?")[0]
    for benchmark_id, benchmark in API_BENCHMARKS.items():
        if (
            benchmark.endpoint == endpoint_path
            and benchmark.method.upper() == method.upper()
        ):
            return benchmark

    # 返回預設基準
    return PerformanceBenchmark(
        endpoint=endpoint,
        method=method,
        max_response_time_ms=1000,
        max_memory_mb=100,
        min_requests_per_second=10,
        description="預設效能基準",
        critical_threshold_ms=2000,
        warning_threshold_ms=800,
    )


def get_load_test_config(test_type: str = "medium_load") -> Dict[str, Any]:
    """
    獲取負載測試配置

    Args:
        test_type: 測試類型 (light_load, medium_load, heavy_load, stress_test)

    Returns:
        Dict[str, Any]: 負載測試配置
    """
    return LOAD_TEST_CONFIG.get(test_type, LOAD_TEST_CONFIG["medium_load"])


def is_performance_acceptable(
    actual_time_ms: float, benchmark: PerformanceBenchmark
) -> tuple[bool, str]:
    """
    檢查效能是否符合基準

    Args:
        actual_time_ms: 實際響應時間（毫秒）
        benchmark: 效能基準

    Returns:
        tuple[bool, str]: (是否符合基準, 狀態描述)
    """
    if actual_time_ms <= benchmark.warning_threshold_ms:
        return True, "excellent"
    elif actual_time_ms <= benchmark.max_response_time_ms:
        return True, "acceptable"
    elif actual_time_ms <= benchmark.critical_threshold_ms:
        return False, "warning"
    else:
        return False, "critical"
