"""
UI 工具模組

提供快取管理、效能優化等工具功能。
"""

from .cache_manager import (
    CacheManager,
    cache_manager,
    cache_result,
    cache_dataframe_query,
    get_static_resource,
    optimize_memory_usage,
    get_cache_dashboard_data,
)

from .performance_optimizer import (
    PerformanceOptimizer,
    performance_optimizer,
    optimize_page_load,
    optimize_query,
    optimize_render,
    create_performance_dashboard,
    enable_performance_optimizations,
)

__all__ = [
    "CacheManager",
    "cache_manager",
    "cache_result",
    "cache_dataframe_query",
    "get_static_resource",
    "optimize_memory_usage",
    "get_cache_dashboard_data",
    "PerformanceOptimizer",
    "performance_optimizer",
    "optimize_page_load",
    "optimize_query",
    "optimize_render",
    "create_performance_dashboard",
    "enable_performance_optimizations",
]
