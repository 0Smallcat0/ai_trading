"""Web UI 性能優化模組

此模組提供 Web UI 的性能優化功能，包括：
- 頁面加載時間監控
- 組件懶加載
- 快取管理
- 資源優化
- 狀態管理優化

目標：UI 加載時間 <2s，響應時間 <100ms
"""

import streamlit as st
import time
import functools
from typing import Any, Callable, Dict, Optional, List
import logging
import threading
from datetime import datetime, timedelta

# 設定日誌
logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """性能監控器
    
    監控和優化 Web UI 的性能表現。
    """
    
    def __init__(self):
        """初始化性能監控器"""
        self._metrics = {}
        self._cache = {}
        self._cache_ttl = {}
        self._lock = threading.Lock()
        self._initialize_session_state()
    
    def _initialize_session_state(self) -> None:
        """初始化 session state 中的性能相關設定"""
        if "performance_monitoring" not in st.session_state:
            st.session_state.performance_monitoring = True
        if "page_load_times" not in st.session_state:
            st.session_state.page_load_times = {}
        if "component_cache" not in st.session_state:
            st.session_state.component_cache = {}
    
    def measure_time(self, operation_name: str):
        """時間測量裝飾器
        
        Args:
            operation_name: 操作名稱
            
        Returns:
            裝飾器函數
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not st.session_state.get("performance_monitoring", True):
                    return func(*args, **kwargs)
                
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.time()
                    duration = end_time - start_time
                    self._record_metric(operation_name, duration)
                    
                    # 如果操作時間過長，記錄警告
                    if duration > 2.0:  # 2秒閾值
                        logger.warning(f"操作 {operation_name} 耗時 {duration:.2f}s，超過建議閾值")
            
            return wrapper
        return decorator
    
    def _record_metric(self, operation_name: str, duration: float) -> None:
        """記錄性能指標
        
        Args:
            operation_name: 操作名稱
            duration: 持續時間（秒）
        """
        with self._lock:
            if operation_name not in self._metrics:
                self._metrics[operation_name] = []
            
            self._metrics[operation_name].append({
                "timestamp": datetime.now(),
                "duration": duration
            })
            
            # 只保留最近 100 次記錄
            if len(self._metrics[operation_name]) > 100:
                self._metrics[operation_name] = self._metrics[operation_name][-100:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """獲取性能摘要
        
        Returns:
            性能摘要字典
        """
        summary = {}
        
        with self._lock:
            for operation_name, metrics in self._metrics.items():
                if not metrics:
                    continue
                
                durations = [m["duration"] for m in metrics]
                summary[operation_name] = {
                    "count": len(durations),
                    "avg_duration": sum(durations) / len(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                    "last_duration": durations[-1] if durations else 0,
                }
        
        return summary
    
    def show_performance_dashboard(self) -> None:
        """顯示性能儀表板"""
        if not st.session_state.get("performance_monitoring", True):
            st.info("性能監控已禁用")
            return
        
        st.subheader("🚀 性能監控儀表板")
        
        summary = self.get_performance_summary()
        
        if not summary:
            st.info("暫無性能數據")
            return
        
        # 顯示性能指標
        cols = st.columns(3)
        
        with cols[0]:
            st.metric("監控操作數", len(summary))
        
        with cols[1]:
            avg_times = [s["avg_duration"] for s in summary.values()]
            overall_avg = sum(avg_times) / len(avg_times) if avg_times else 0
            st.metric("平均響應時間", f"{overall_avg:.3f}s")
        
        with cols[2]:
            slow_operations = sum(1 for s in summary.values() if s["avg_duration"] > 1.0)
            st.metric("慢操作數", slow_operations)
        
        # 詳細性能表格
        st.subheader("詳細性能指標")
        
        performance_data = []
        for operation, metrics in summary.items():
            performance_data.append({
                "操作": operation,
                "平均時間(s)": f"{metrics['avg_duration']:.3f}",
                "最小時間(s)": f"{metrics['min_duration']:.3f}",
                "最大時間(s)": f"{metrics['max_duration']:.3f}",
                "執行次數": metrics['count'],
                "狀態": "⚠️ 慢" if metrics['avg_duration'] > 1.0 else "✅ 正常"
            })
        
        if performance_data:
            st.dataframe(performance_data, use_container_width=True)


class CacheManager:
    """快取管理器
    
    管理 UI 組件和數據的快取。
    """
    
    def __init__(self, default_ttl: int = 300):
        """初始化快取管理器
        
        Args:
            default_ttl: 預設快取存活時間（秒）
        """
        self.default_ttl = default_ttl
        self._cache = {}
        self._cache_times = {}
        self._lock = threading.Lock()
    
    def cached_component(self, ttl: Optional[int] = None):
        """快取組件裝飾器
        
        Args:
            ttl: 快取存活時間（秒）
            
        Returns:
            裝飾器函數
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # 生成快取鍵
                cache_key = f"{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"
                
                # 檢查快取
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # 執行函數並快取結果
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl or self.default_ttl)
                
                return result
            
            return wrapper
        return decorator
    
    def get(self, key: str) -> Any:
        """獲取快取值
        
        Args:
            key: 快取鍵
            
        Returns:
            快取值或 None
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            # 檢查是否過期
            if key in self._cache_times:
                if datetime.now() > self._cache_times[key]:
                    del self._cache[key]
                    del self._cache_times[key]
                    return None
            
            return self._cache[key]
    
    def set(self, key: str, value: Any, ttl: int) -> None:
        """設定快取值
        
        Args:
            key: 快取鍵
            value: 快取值
            ttl: 存活時間（秒）
        """
        with self._lock:
            self._cache[key] = value
            self._cache_times[key] = datetime.now() + timedelta(seconds=ttl)
    
    def clear(self) -> None:
        """清除所有快取"""
        with self._lock:
            self._cache.clear()
            self._cache_times.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """獲取快取統計
        
        Returns:
            快取統計字典
        """
        with self._lock:
            return {
                "total_items": len(self._cache),
                "expired_items": sum(
                    1 for key, expire_time in self._cache_times.items()
                    if datetime.now() > expire_time
                ),
                "cache_keys": list(self._cache.keys())
            }


class LazyLoader:
    """懶加載管理器
    
    實現組件的懶加載以提升初始加載性能。
    """
    
    def __init__(self):
        """初始化懶加載管理器"""
        self._loaded_components = set()
    
    def lazy_load_component(self, component_id: str, loader_func: Callable) -> Any:
        """懶加載組件
        
        Args:
            component_id: 組件 ID
            loader_func: 加載函數
            
        Returns:
            組件實例或 None
        """
        # 檢查是否已加載
        if component_id in self._loaded_components:
            return None
        
        # 檢查是否應該加載（基於用戶交互或可見性）
        if self._should_load_component(component_id):
            try:
                result = loader_func()
                self._loaded_components.add(component_id)
                logger.info(f"懶加載組件 {component_id} 成功")
                return result
            except Exception as e:
                logger.error(f"懶加載組件 {component_id} 失敗: {e}")
                return None
        
        return None
    
    def _should_load_component(self, component_id: str) -> bool:
        """判斷是否應該加載組件
        
        Args:
            component_id: 組件 ID
            
        Returns:
            是否應該加載
        """
        # 簡化的加載策略：檢查 session state 中的標記
        return st.session_state.get(f"load_{component_id}", False)
    
    def mark_for_loading(self, component_id: str) -> None:
        """標記組件需要加載
        
        Args:
            component_id: 組件 ID
        """
        st.session_state[f"load_{component_id}"] = True


class StateOptimizer:
    """狀態優化器
    
    優化 Streamlit session state 的使用。
    """
    
    @staticmethod
    def optimize_session_state() -> None:
        """優化 session state"""
        # 清理過期的狀態
        StateOptimizer._cleanup_expired_state()
        
        # 壓縮大型狀態對象
        StateOptimizer._compress_large_objects()
    
    @staticmethod
    def _cleanup_expired_state() -> None:
        """清理過期的狀態"""
        current_time = datetime.now()
        keys_to_remove = []
        
        for key in st.session_state.keys():
            if key.startswith("temp_") and "_timestamp" in key:
                timestamp_key = key.replace("temp_", "temp_timestamp_")
                if timestamp_key in st.session_state:
                    timestamp = st.session_state[timestamp_key]
                    if current_time - timestamp > timedelta(hours=1):  # 1小時過期
                        keys_to_remove.extend([key, timestamp_key])
        
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]
    
    @staticmethod
    def _compress_large_objects() -> None:
        """壓縮大型對象"""
        # 檢查大型 DataFrame 並考慮採樣
        for key, value in st.session_state.items():
            if hasattr(value, '__len__') and len(str(value)) > 1000000:  # 1MB
                logger.warning(f"檢測到大型狀態對象: {key}")


# 全域實例
performance_monitor = PerformanceMonitor()
cache_manager = CacheManager()
lazy_loader = LazyLoader()
state_optimizer = StateOptimizer()
