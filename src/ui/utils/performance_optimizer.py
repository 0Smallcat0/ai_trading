"""
效能優化模組

提供頁面載入優化、資源壓縮、延遲載入等效能優化功能。
支援 <2 秒頁面加載時間目標和智能狀態管理。
"""

import time
import gzip
import io
import threading
import asyncio
from typing import Any, Dict, List, Optional, Callable, Union
from functools import wraps
import streamlit as st
import pandas as pd
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """效能優化器類別

    提供各種效能優化功能，包括資源壓縮、延遲載入、批次處理等。
    目標：頁面加載時間 <2 秒，優化狀態管理和組件懶加載。
    """

    def __init__(self):
        """初始化效能優化器"""
        self.performance_metrics = {
            "page_load_times": [],
            "query_times": [],
            "render_times": [],
            "memory_usage": [],
            "component_load_times": [],
            "state_update_times": [],
        }
        self._lock = threading.Lock()
        self.lazy_load_registry = {}
        self.component_cache = {}
        self.state_optimization_enabled = True
        self.target_load_time = 2.0  # 2 秒目標

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
        """智能延遲載入組件

        支援組件快取和條件載入，提升性能。

        Args:
            component_func: 組件函數
            *args: 位置參數
            **kwargs: 關鍵字參數
        """
        start_time = time.time()

        if "lazy_load_registry" not in st.session_state:
            st.session_state.lazy_load_registry = {}

        component_key = f"{component_func.__name__}_{hash(str(args) + str(kwargs))}"

        # 檢查是否已快取
        if component_key in self.component_cache:
            cached_result = self.component_cache[component_key]
            if cached_result.get("expires_at", 0) > time.time():
                return cached_result["data"]

        # 檢查是否需要載入
        if component_key not in st.session_state.lazy_load_registry:
            with st.spinner("載入中..."):
                result = component_func(*args, **kwargs)
                st.session_state.lazy_load_registry[component_key] = True

                # 快取結果（5分鐘）
                self.component_cache[component_key] = {
                    "data": result,
                    "expires_at": time.time() + 300
                }

                load_time = time.time() - start_time
                with self._lock:
                    self.performance_metrics["component_load_times"].append(load_time)

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

    def optimize_session_state(self) -> None:
        """優化 session state 管理

        清理過期的狀態和不必要的數據，減少重新渲染。
        """
        if not self.state_optimization_enabled:
            return

        start_time = time.time()

        # 清理過期的懶加載註冊
        if hasattr(st.session_state, 'lazy_load_registry'):
            # 保留最近使用的組件
            current_time = time.time()
            expired_keys = []

            for key in list(self.component_cache.keys()):
                if self.component_cache[key].get("expires_at", 0) < current_time:
                    expired_keys.append(key)

            for key in expired_keys:
                del self.component_cache[key]
                if key in st.session_state.lazy_load_registry:
                    del st.session_state.lazy_load_registry[key]

        # 清理大型臨時數據
        temp_keys = [key for key in st.session_state.keys() if key.startswith('temp_')]
        for key in temp_keys:
            if hasattr(st.session_state[key], '__len__'):
                # 如果是大型對象（>1MB），清理它
                try:
                    import sys
                    if sys.getsizeof(st.session_state[key]) > 1024 * 1024:
                        del st.session_state[key]
                except:
                    pass

        optimization_time = time.time() - start_time
        with self._lock:
            self.performance_metrics["state_update_times"].append(optimization_time)

        logger.debug(f"Session state 優化完成，耗時 {optimization_time:.3f}秒")

    def preload_critical_components(self, component_list: List[str]) -> None:
        """預載入關鍵組件

        Args:
            component_list: 要預載入的組件名稱列表
        """
        for component_name in component_list:
            if component_name not in self.lazy_load_registry:
                self.lazy_load_registry[component_name] = {
                    "preloaded": True,
                    "timestamp": time.time()
                }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """獲取效能指標

        Returns:
            效能指標字典，包含性能分析和建議
        """
        with self._lock:
            metrics = {}

            for metric_type, times in self.performance_metrics.items():
                if times:
                    avg_time = sum(times) / len(times)
                    metrics[metric_type] = {
                        "count": len(times),
                        "avg": avg_time,
                        "min": min(times),
                        "max": max(times),
                        "total": sum(times),
                        "meets_target": avg_time < self.target_load_time if metric_type == "page_load_times" else True
                    }
                else:
                    metrics[metric_type] = {
                        "count": 0,
                        "avg": 0,
                        "min": 0,
                        "max": 0,
                        "total": 0,
                        "meets_target": True
                    }

            # 添加性能分析
            metrics["performance_analysis"] = self._analyze_performance()
            metrics["cache_efficiency"] = {
                "component_cache_size": len(self.component_cache),
                "lazy_load_registry_size": len(self.lazy_load_registry)
            }

            return metrics

    def _analyze_performance(self) -> Dict[str, Any]:
        """分析性能並提供建議

        Returns:
            性能分析結果和建議
        """
        analysis = {
            "overall_status": "good",
            "recommendations": [],
            "warnings": []
        }

        # 檢查頁面加載時間
        if self.performance_metrics["page_load_times"]:
            avg_load_time = sum(self.performance_metrics["page_load_times"]) / len(self.performance_metrics["page_load_times"])
            if avg_load_time > self.target_load_time:
                analysis["overall_status"] = "needs_improvement"
                analysis["warnings"].append(f"平均頁面加載時間 {avg_load_time:.2f}s 超過目標 {self.target_load_time}s")
                analysis["recommendations"].append("考慮啟用更多組件懶加載")
                analysis["recommendations"].append("優化大型數據集的處理")

        # 檢查組件加載時間
        if self.performance_metrics["component_load_times"]:
            avg_component_time = sum(self.performance_metrics["component_load_times"]) / len(self.performance_metrics["component_load_times"])
            if avg_component_time > 1.0:
                analysis["warnings"].append(f"組件平均加載時間 {avg_component_time:.2f}s 較長")
                analysis["recommendations"].append("考慮組件預載入或快取優化")

        # 檢查快取效率
        if len(self.component_cache) > 100:
            analysis["warnings"].append("組件快取項目過多，可能影響記憶體使用")
            analysis["recommendations"].append("定期清理過期快取")

        return analysis

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
    """創建增強的效能監控儀表板"""
    st.subheader("🚀 效能監控儀表板")

    metrics = performance_optimizer.get_performance_metrics()
    analysis = metrics.get("performance_analysis", {})

    # 總體狀態指示器
    status = analysis.get("overall_status", "unknown")
    status_colors = {
        "good": "🟢",
        "needs_improvement": "🟡",
        "poor": "🔴"
    }
    st.info(f"{status_colors.get(status, '⚪')} 總體性能狀態: {status}")

    # 主要指標
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        load_time = metrics['page_load_times']['avg']
        target_met = "✅" if metrics['page_load_times']['meets_target'] else "❌"
        st.metric(
            "平均頁面載入時間",
            f"{load_time:.3f}s {target_met}",
            f"目標: <{performance_optimizer.target_load_time}s",
        )

    with col2:
        st.metric(
            "平均查詢時間",
            f"{metrics['query_times']['avg']:.3f}s",
            f"共 {metrics['query_times']['count']} 次",
        )

    with col3:
        st.metric(
            "組件載入時間",
            f"{metrics['component_load_times']['avg']:.3f}s",
            f"共 {metrics['component_load_times']['count']} 次",
        )

    with col4:
        cache_info = metrics.get("cache_efficiency", {})
        st.metric(
            "快取效率",
            f"{cache_info.get('component_cache_size', 0)} 項目",
            f"註冊: {cache_info.get('lazy_load_registry_size', 0)}",
        )

    # 性能建議
    if analysis.get("warnings") or analysis.get("recommendations"):
        st.subheader("📊 性能分析與建議")

        if analysis.get("warnings"):
            st.warning("⚠️ 性能警告:")
            for warning in analysis["warnings"]:
                st.write(f"• {warning}")

        if analysis.get("recommendations"):
            st.info("💡 優化建議:")
            for rec in analysis["recommendations"]:
                st.write(f"• {rec}")

    # 控制面板
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🧹 清空指標"):
            performance_optimizer.clear_metrics()
            st.rerun()

    with col2:
        if st.button("🔧 優化 Session State"):
            performance_optimizer.optimize_session_state()
            st.success("Session State 已優化")

    with col3:
        if st.button("📈 啟用性能優化"):
            enable_performance_optimizations()
            st.success("性能優化已啟用")

    # 詳細指標（可摺疊）
    with st.expander("📋 詳細效能指標"):
        st.json(metrics)


def enable_performance_optimizations():
    """啟用效能優化設定"""
    # 設定 Streamlit 效能優化選項
    if "performance_optimized" not in st.session_state:
        st.session_state.performance_optimized = True

        # 啟用快取
        st.cache_data.clear()
        st.cache_resource.clear()

        # 初始化性能優化狀態
        st.session_state.lazy_load_enabled = True
        st.session_state.component_cache_enabled = True
        st.session_state.auto_optimization = True

        logger.info("效能優化已啟用")


class SmartStateManager:
    """智能狀態管理器

    提供智能的 session state 管理，減少不必要的重新渲染。
    """

    def __init__(self):
        """初始化智能狀態管理器"""
        self.state_history = {}
        self.change_tracking = {}
        self.optimization_rules = {}

    def smart_update(self, key: str, value: Any, force_update: bool = False) -> bool:
        """智能更新狀態

        只在值真正改變時才更新，避免不必要的重新渲染。

        Args:
            key: 狀態鍵
            value: 新值
            force_update: 是否強制更新

        Returns:
            bool: 是否實際更新了狀態
        """
        current_value = st.session_state.get(key)

        # 檢查值是否真的改變了
        if not force_update and current_value == value:
            return False

        # 記錄變更歷史
        if key not in self.state_history:
            self.state_history[key] = []

        self.state_history[key].append({
            "old_value": current_value,
            "new_value": value,
            "timestamp": datetime.now(),
        })

        # 限制歷史記錄數量
        if len(self.state_history[key]) > 10:
            self.state_history[key] = self.state_history[key][-10:]

        # 更新狀態
        st.session_state[key] = value

        # 記錄變更統計
        if key not in self.change_tracking:
            self.change_tracking[key] = 0
        self.change_tracking[key] += 1

        return True

    def batch_update(self, updates: Dict[str, Any]) -> List[str]:
        """批量更新狀態

        Args:
            updates: 要更新的狀態字典

        Returns:
            List[str]: 實際更新的鍵列表
        """
        updated_keys = []

        for key, value in updates.items():
            if self.smart_update(key, value):
                updated_keys.append(key)

        return updated_keys

    def get_change_summary(self) -> Dict[str, Any]:
        """獲取狀態變更摘要

        Returns:
            Dict[str, Any]: 變更摘要
        """
        return {
            "total_keys": len(self.change_tracking),
            "total_changes": sum(self.change_tracking.values()),
            "most_changed_keys": sorted(
                self.change_tracking.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            "recent_changes": {
                key: history[-3:] for key, history in self.state_history.items()
                if history
            }
        }


# 全域智能狀態管理器
smart_state_manager = SmartStateManager()
