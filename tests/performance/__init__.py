"""
效能測試框架

此模組提供完整的 API 效能測試基礎設施，包括：
- API 回應時間測試
- 併發負載測試
- 記憶體使用量監控
- 效能基準測試
- 自動化報告生成

使用方法:
    pytest tests/performance/ -v --benchmark-only
    pytest tests/performance/test_api_performance.py::test_api_response_time
"""

from .utils.performance_monitor import PerformanceMonitor
from .utils.load_tester import LoadTester
from .utils.memory_profiler import MemoryProfiler
from .utils.report_generator import ReportGenerator

__all__ = ["PerformanceMonitor", "LoadTester", "MemoryProfiler", "ReportGenerator"]

# 效能測試配置
PERFORMANCE_CONFIG = {
    "api_response_time_threshold": 100,  # ms
    "memory_leak_threshold": 10,  # MB per hour
    "concurrent_users_max": 100,
    "test_duration": 60,  # seconds
    "benchmark_rounds": 10,
}
