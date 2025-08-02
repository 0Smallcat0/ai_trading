"""
組件懶加載管理器

提供智能的組件懶加載功能，支援條件載入、預載入和快取機制。
目標：提升頁面加載性能，實現 <2 秒加載時間。
"""

import time
import threading
import asyncio
from typing import Any, Dict, List, Optional, Callable, Union, Set
from functools import wraps
from datetime import datetime, timedelta
import streamlit as st
import logging

logger = logging.getLogger(__name__)


class LazyLoader:
    """組件懶加載管理器
    
    提供智能的組件懶加載功能，包括：
    - 條件載入：只在需要時載入組件
    - 預載入：預先載入關鍵組件
    - 快取機制：避免重複載入
    - 優先級管理：高優先級組件優先載入
    """
    
    def __init__(self):
        """初始化懶加載管理器"""
        self.component_registry: Dict[str, Dict[str, Any]] = {}
        self.load_queue: List[Dict[str, Any]] = []
        self.cache: Dict[str, Any] = {}
        self.loading_states: Dict[str, bool] = {}
        self.priorities: Dict[str, int] = {}
        self._lock = threading.Lock()
        
        # 性能指標
        self.metrics = {
            "total_loads": 0,
            "cache_hits": 0,
            "load_times": [],
            "failed_loads": 0
        }
    
    def register_component(
        self, 
        component_id: str, 
        loader_func: Callable,
        priority: int = 1,
        cache_ttl: int = 300,
        preload: bool = False,
        dependencies: List[str] = None
    ) -> None:
        """註冊組件
        
        Args:
            component_id: 組件唯一標識
            loader_func: 載入函數
            priority: 優先級 (1-10, 10最高)
            cache_ttl: 快取存活時間（秒）
            preload: 是否預載入
            dependencies: 依賴的其他組件
        """
        with self._lock:
            self.component_registry[component_id] = {
                "loader_func": loader_func,
                "priority": priority,
                "cache_ttl": cache_ttl,
                "preload": preload,
                "dependencies": dependencies or [],
                "registered_at": datetime.now(),
                "load_count": 0
            }
            
            self.priorities[component_id] = priority
            
            if preload:
                self._add_to_load_queue(component_id, priority)
        
        logger.debug(f"組件 {component_id} 已註冊，優先級: {priority}")
    
    def _add_to_load_queue(self, component_id: str, priority: int) -> None:
        """添加到載入佇列"""
        load_item = {
            "component_id": component_id,
            "priority": priority,
            "queued_at": datetime.now()
        }
        
        # 按優先級插入
        inserted = False
        for i, item in enumerate(self.load_queue):
            if priority > item["priority"]:
                self.load_queue.insert(i, load_item)
                inserted = True
                break
        
        if not inserted:
            self.load_queue.append(load_item)
    
    def load_component(
        self, 
        component_id: str, 
        *args, 
        show_spinner: bool = True,
        **kwargs
    ) -> Any:
        """載入組件
        
        Args:
            component_id: 組件標識
            *args: 傳遞給載入函數的參數
            show_spinner: 是否顯示載入指示器
            **kwargs: 傳遞給載入函數的關鍵字參數
            
        Returns:
            組件載入結果
        """
        start_time = time.time()
        
        # 檢查快取
        cache_key = self._generate_cache_key(component_id, args, kwargs)
        cached_result = self._get_from_cache(cache_key)
        
        if cached_result is not None:
            with self._lock:
                self.metrics["cache_hits"] += 1
            return cached_result
        
        # 檢查是否已註冊
        if component_id not in self.component_registry:
            logger.error(f"組件 {component_id} 未註冊")
            return None
        
        component_info = self.component_registry[component_id]
        
        # 檢查依賴
        if not self._check_dependencies(component_id):
            logger.warning(f"組件 {component_id} 的依賴未滿足")
            return None
        
        # 防止重複載入
        if component_id in self.loading_states and self.loading_states[component_id]:
            return self._wait_for_loading(component_id)
        
        try:
            self.loading_states[component_id] = True
            
            # 顯示載入指示器
            if show_spinner:
                with st.spinner(f"載入 {component_id}..."):
                    result = self._execute_loader(component_info, args, kwargs)
            else:
                result = self._execute_loader(component_info, args, kwargs)
            
            # 快取結果
            self._cache_result(cache_key, result, component_info["cache_ttl"])
            
            # 更新統計
            load_time = time.time() - start_time
            with self._lock:
                self.metrics["total_loads"] += 1
                self.metrics["load_times"].append(load_time)
                component_info["load_count"] += 1
            
            logger.debug(f"組件 {component_id} 載入完成，耗時 {load_time:.3f}秒")
            return result
            
        except Exception as e:
            logger.error(f"載入組件 {component_id} 失敗: {e}")
            with self._lock:
                self.metrics["failed_loads"] += 1
            return None
            
        finally:
            self.loading_states[component_id] = False
    
    def _generate_cache_key(self, component_id: str, args: tuple, kwargs: dict) -> str:
        """生成快取鍵"""
        import hashlib
        key_data = f"{component_id}_{str(args)}_{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode(), usedforsecurity=False).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """從快取獲取結果"""
        if cache_key in self.cache:
            cache_item = self.cache[cache_key]
            if cache_item["expires_at"] > datetime.now():
                return cache_item["data"]
            else:
                del self.cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: Any, ttl: int) -> None:
        """快取結果"""
        self.cache[cache_key] = {
            "data": result,
            "cached_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(seconds=ttl)
        }
    
    def _check_dependencies(self, component_id: str) -> bool:
        """檢查組件依賴"""
        component_info = self.component_registry[component_id]
        dependencies = component_info.get("dependencies", [])
        
        for dep_id in dependencies:
            if dep_id not in self.component_registry:
                return False
            # 可以添加更複雜的依賴檢查邏輯
        
        return True
    
    def _wait_for_loading(self, component_id: str, timeout: int = 30) -> Optional[Any]:
        """等待組件載入完成"""
        start_time = time.time()
        while self.loading_states.get(component_id, False):
            if time.time() - start_time > timeout:
                logger.warning(f"等待組件 {component_id} 載入超時")
                return None
            time.sleep(0.1)
        
        # 嘗試從快取獲取結果
        for cache_key, cache_item in self.cache.items():
            if component_id in cache_key:
                if cache_item["expires_at"] > datetime.now():
                    return cache_item["data"]
        
        return None
    
    def _execute_loader(self, component_info: Dict[str, Any], args: tuple, kwargs: dict) -> Any:
        """執行載入函數"""
        loader_func = component_info["loader_func"]
        return loader_func(*args, **kwargs)
    
    def preload_components(self, component_ids: List[str] = None) -> None:
        """預載入組件
        
        Args:
            component_ids: 要預載入的組件列表，None 表示載入所有標記為預載入的組件
        """
        if component_ids is None:
            component_ids = [
                cid for cid, info in self.component_registry.items()
                if info.get("preload", False)
            ]
        
        # 按優先級排序
        component_ids.sort(key=lambda x: self.priorities.get(x, 0), reverse=True)
        
        for component_id in component_ids:
            try:
                self.load_component(component_id, show_spinner=False)
            except Exception as e:
                logger.error(f"預載入組件 {component_id} 失敗: {e}")
    
    def clear_cache(self, component_id: str = None) -> None:
        """清理快取
        
        Args:
            component_id: 特定組件ID，None 表示清理所有快取
        """
        if component_id is None:
            self.cache.clear()
            logger.info("所有組件快取已清理")
        else:
            keys_to_remove = [key for key in self.cache.keys() if component_id in key]
            for key in keys_to_remove:
                del self.cache[key]
            logger.info(f"組件 {component_id} 的快取已清理")
    
    def get_metrics(self) -> Dict[str, Any]:
        """獲取性能指標"""
        with self._lock:
            avg_load_time = (
                sum(self.metrics["load_times"]) / len(self.metrics["load_times"])
                if self.metrics["load_times"] else 0
            )
            
            cache_hit_rate = (
                self.metrics["cache_hits"] / self.metrics["total_loads"] * 100
                if self.metrics["total_loads"] > 0 else 0
            )
            
            return {
                "total_loads": self.metrics["total_loads"],
                "cache_hits": self.metrics["cache_hits"],
                "cache_hit_rate": f"{cache_hit_rate:.1f}%",
                "failed_loads": self.metrics["failed_loads"],
                "avg_load_time": f"{avg_load_time:.3f}s",
                "registered_components": len(self.component_registry),
                "cached_items": len(self.cache),
                "loading_queue_size": len(self.load_queue)
            }


# 全域懶加載管理器
lazy_loader = LazyLoader()


def lazy_component(
    component_id: str,
    priority: int = 1,
    cache_ttl: int = 300,
    preload: bool = False,
    dependencies: List[str] = None
):
    """懶加載組件裝飾器
    
    Args:
        component_id: 組件唯一標識
        priority: 優先級 (1-10)
        cache_ttl: 快取存活時間（秒）
        preload: 是否預載入
        dependencies: 依賴組件列表
    """
    def decorator(func: Callable) -> Callable:
        # 註冊組件
        lazy_loader.register_component(
            component_id=component_id,
            loader_func=func,
            priority=priority,
            cache_ttl=cache_ttl,
            preload=preload,
            dependencies=dependencies
        )
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return lazy_loader.load_component(component_id, *args, **kwargs)
        
        return wrapper
    
    return decorator
