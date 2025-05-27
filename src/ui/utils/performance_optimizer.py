"""
效能優化模組

提供頁面載入優化、資源壓縮、延遲載入等效能優化功能。
"""

import time
import gzip
import io
import threading
from typing import Any, Dict, List, Optional, Callable
from functools import wraps
import streamlit as st
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """效能優化器類別

    提供各種效能優化功能，包括資源壓縮、延遲載入、批次處理等。
    """

    def __init__(self):
        """初始化效能優化器"""
        self.performance_metrics = {
            "page_load_times": [],
            "query_times": [],
            "render_times": [],
            "memory_usage": [],
        }
        self._lock = threading.Lock()

    def measure_time(self, operation_type: str = "general"):
        """測量執行時間的裝飾器

        Args:
            operation_type: 操作類型

        Returns:
            裝飾器函數
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()

                execution_time = end_time - start_time

                with self._lock:
                    if operation_type == "page_load":
                        self.performance_metrics["page_load_times"].append(
                            execution_time
                        )
                    elif operation_type == "query":
                        self.performance_metrics["query_times"].append(execution_time)
                    elif operation_type == "render":
                        self.performance_metrics["render_times"].append(execution_time)

                logger.debug(f"{func.__name__} 執行時間: {execution_time:.3f}秒")
                return result

            return wrapper

        return decorator

    def compress_data(self, data: str) -> bytes:
        """壓縮資料

        Args:
            data: 要壓縮的資料

        Returns:
            壓縮後的資料
        """
        return gzip.compress(data.encode("utf-8"))

    def decompress_data(self, compressed_data: bytes) -> str:
        """解壓縮資料

        Args:
            compressed_data: 壓縮的資料

        Returns:
            解壓縮後的資料
        """
        return gzip.decompress(compressed_data).decode("utf-8")

    def optimize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """優化 DataFrame 記憶體使用

        Args:
            df: 要優化的 DataFrame

        Returns:
            優化後的 DataFrame
        """
        optimized_df = df.copy()

        # 優化數值型欄位
        for col in optimized_df.select_dtypes(include=["int64"]).columns:
            col_min = optimized_df[col].min()
            col_max = optimized_df[col].max()

            if col_min >= -128 and col_max <= 127:
                optimized_df[col] = optimized_df[col].astype("int8")
            elif col_min >= -32768 and col_max <= 32767:
                optimized_df[col] = optimized_df[col].astype("int16")
            elif col_min >= -2147483648 and col_max <= 2147483647:
                optimized_df[col] = optimized_df[col].astype("int32")

        # 優化浮點數欄位
        for col in optimized_df.select_dtypes(include=["float64"]).columns:
            optimized_df[col] = pd.to_numeric(optimized_df[col], downcast="float")

        # 優化字串欄位
        for col in optimized_df.select_dtypes(include=["object"]).columns:
            if optimized_df[col].nunique() / len(optimized_df) < 0.5:
                optimized_df[col] = optimized_df[col].astype("category")

        return optimized_df

    def lazy_load_component(self, component_func: Callable, *args, **kwargs):
        """延遲載入組件

        Args:
            component_func: 組件函數
            *args: 位置參數
            **kwargs: 關鍵字參數
        """
        if "lazy_load_key" not in st.session_state:
            st.session_state.lazy_load_key = set()

        component_key = f"{component_func.__name__}_{hash(str(args) + str(kwargs))}"

        if component_key not in st.session_state.lazy_load_key:
            with st.spinner("載入中..."):
                result = component_func(*args, **kwargs)
                st.session_state.lazy_load_key.add(component_key)
                return result
        else:
            return component_func(*args, **kwargs)

    def batch_process(
        self, items: List[Any], batch_size: int = 100, process_func: Callable = None
    ) -> List[Any]:
        """批次處理資料

        Args:
            items: 要處理的項目列表
            batch_size: 批次大小
            process_func: 處理函數

        Returns:
            處理結果列表
        """
        results = []
        total_batches = len(items) // batch_size + (1 if len(items) % batch_size else 0)

        progress_bar = st.progress(0)
        status_text = st.empty()

        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            batch_num = i // batch_size + 1

            status_text.text(f"處理批次 {batch_num}/{total_batches}")

            if process_func:
                batch_results = process_func(batch)
                results.extend(batch_results)
            else:
                results.extend(batch)

            progress = min(batch_num / total_batches, 1.0)
            progress_bar.progress(progress)

        progress_bar.empty()
        status_text.empty()

        return results

    def get_performance_metrics(self) -> Dict[str, Any]:
        """獲取效能指標

        Returns:
            效能指標字典
        """
        with self._lock:
            metrics = {}

            for metric_type, times in self.performance_metrics.items():
                if times:
                    metrics[metric_type] = {
                        "count": len(times),
                        "avg": sum(times) / len(times),
                        "min": min(times),
                        "max": max(times),
                        "total": sum(times),
                    }
                else:
                    metrics[metric_type] = {
                        "count": 0,
                        "avg": 0,
                        "min": 0,
                        "max": 0,
                        "total": 0,
                    }

            return metrics

    def clear_metrics(self):
        """清空效能指標"""
        with self._lock:
            for metric_type in self.performance_metrics:
                self.performance_metrics[metric_type].clear()


# 全域效能優化器實例
performance_optimizer = PerformanceOptimizer()


def optimize_page_load(func: Callable) -> Callable:
    """頁面載入優化裝飾器

    Args:
        func: 要優化的函數

    Returns:
        優化後的函數
    """

    @wraps(func)
    @performance_optimizer.measure_time("page_load")
    def wrapper(*args, **kwargs):
        # 設定頁面配置以提升效能
        if not hasattr(st, "_page_config_set"):
            st.set_page_config(layout="wide", initial_sidebar_state="expanded")
            st._page_config_set = True

        return func(*args, **kwargs)

    return wrapper


def optimize_query(func: Callable) -> Callable:
    """查詢優化裝飾器

    Args:
        func: 要優化的查詢函數

    Returns:
        優化後的函數
    """

    @wraps(func)
    @performance_optimizer.measure_time("query")
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def optimize_render(func: Callable) -> Callable:
    """渲染優化裝飾器

    Args:
        func: 要優化的渲染函數

    Returns:
        優化後的函數
    """

    @wraps(func)
    @performance_optimizer.measure_time("render")
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def create_performance_dashboard():
    """創建效能監控儀表板"""
    st.subheader("🚀 效能監控儀表板")

    metrics = performance_optimizer.get_performance_metrics()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "平均頁面載入時間",
            f"{metrics['page_load_times']['avg']:.3f}s",
            f"共 {metrics['page_load_times']['count']} 次",
        )

    with col2:
        st.metric(
            "平均查詢時間",
            f"{metrics['query_times']['avg']:.3f}s",
            f"共 {metrics['query_times']['count']} 次",
        )

    with col3:
        st.metric(
            "平均渲染時間",
            f"{metrics['render_times']['avg']:.3f}s",
            f"共 {metrics['render_times']['count']} 次",
        )

    with col4:
        if st.button("清空指標"):
            performance_optimizer.clear_metrics()
            st.rerun()

    # 顯示詳細指標
    if st.expander("詳細效能指標"):
        st.json(metrics)


def enable_performance_optimizations():
    """啟用效能優化設定"""
    # 設定 Streamlit 效能優化選項
    if "performance_optimized" not in st.session_state:
        st.session_state.performance_optimized = True

        # 啟用快取
        st.cache_data.clear()
        st.cache_resource.clear()

        logger.info("效能優化已啟用")
