"""
快取管理器模組

提供頁面載入快取、資料查詢結果快取、靜態資源優化和記憶體使用優化功能。
"""

import time
import hashlib
import pickle
import threading
from typing import Any, Dict, Optional, Callable, Union
from functools import wraps
from datetime import datetime, timedelta
import streamlit as st
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """快取管理器類別

    提供多層級快取機制，包括記憶體快取、會話快取和持久化快取。
    """

    def __init__(self, max_memory_size: int = 100 * 1024 * 1024):  # 100MB
        """初始化快取管理器

        Args:
            max_memory_size: 最大記憶體使用量（位元組）
        """
        self.max_memory_size = max_memory_size
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "memory_usage": 0,
            "last_cleanup": datetime.now(),
        }
        self._lock = threading.Lock()

    def _generate_cache_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """生成快取鍵值

        Args:
            func_name: 函數名稱
            args: 位置參數
            kwargs: 關鍵字參數

        Returns:
            快取鍵值
        """
        key_data = f"{func_name}_{str(args)}_{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode(), usedforsecurity=False).hexdigest()

    def _get_object_size(self, obj: Any) -> int:
        """計算物件大小

        Args:
            obj: 要計算大小的物件

        Returns:
            物件大小（位元組）
        """
        try:
            return len(pickle.dumps(obj))
        except Exception:
            return 1024  # 預設大小

    def _cleanup_memory_cache(self):
        """清理記憶體快取"""
        with self._lock:
            if self.cache_stats["memory_usage"] > self.max_memory_size:
                # 按照最後存取時間排序，刪除最舊的項目
                sorted_items = sorted(
                    self.memory_cache.items(), key=lambda x: x[1]["last_access"]
                )

                # 刪除一半的快取項目
                items_to_remove = len(sorted_items) // 2
                for i in range(items_to_remove):
                    key = sorted_items[i][0]
                    item_size = self._get_object_size(self.memory_cache[key]["data"])
                    del self.memory_cache[key]
                    self.cache_stats["memory_usage"] -= item_size

                self.cache_stats["last_cleanup"] = datetime.now()
                logger.info(f"快取清理完成，移除 {items_to_remove} 個項目")

    def get(self, key: str) -> Optional[Any]:
        """從快取中獲取資料

        Args:
            key: 快取鍵值

        Returns:
            快取的資料，如果不存在則返回 None
        """
        with self._lock:
            if key in self.memory_cache:
                cache_item = self.memory_cache[key]

                # 檢查是否過期
                if (
                    cache_item["expires_at"]
                    and datetime.now() > cache_item["expires_at"]
                ):
                    del self.memory_cache[key]
                    self.cache_stats["misses"] += 1
                    return None

                # 更新最後存取時間
                cache_item["last_access"] = datetime.now()
                self.cache_stats["hits"] += 1
                return cache_item["data"]

            self.cache_stats["misses"] += 1
            return None

    def set(self, key: str, data: Any, ttl: int = 3600):
        """設定快取資料

        Args:
            key: 快取鍵值
            data: 要快取的資料
            ttl: 存活時間（秒），0 表示永不過期
        """
        with self._lock:
            expires_at = datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None
            data_size = self._get_object_size(data)

            cache_item = {
                "data": data,
                "created_at": datetime.now(),
                "last_access": datetime.now(),
                "expires_at": expires_at,
                "size": data_size,
            }

            self.memory_cache[key] = cache_item
            self.cache_stats["memory_usage"] += data_size

            # 檢查是否需要清理快取
            if self.cache_stats["memory_usage"] > self.max_memory_size:
                self._cleanup_memory_cache()

    def delete(self, key: str):
        """刪除快取項目

        Args:
            key: 快取鍵值
        """
        with self._lock:
            if key in self.memory_cache:
                item_size = self.memory_cache[key]["size"]
                del self.memory_cache[key]
                self.cache_stats["memory_usage"] -= item_size

    def clear(self):
        """清空所有快取"""
        with self._lock:
            self.memory_cache.clear()
            self.cache_stats["memory_usage"] = 0
            self.cache_stats["hits"] = 0
            self.cache_stats["misses"] = 0

    def get_stats(self) -> Dict[str, Any]:
        """獲取快取統計資訊

        Returns:
            快取統計資訊
        """
        with self._lock:
            total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
            hit_rate = (
                (self.cache_stats["hits"] / total_requests * 100)
                if total_requests > 0
                else 0
            )

            return {
                "hits": self.cache_stats["hits"],
                "misses": self.cache_stats["misses"],
                "hit_rate": f"{hit_rate:.2f}%",
                "memory_usage": f"{self.cache_stats['memory_usage'] / 1024 / 1024:.2f} MB",
                "cache_items": len(self.memory_cache),
                "last_cleanup": self.cache_stats["last_cleanup"].strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            }


# 全域快取管理器實例
cache_manager = CacheManager()


def cache_result(ttl: int = 3600, key_prefix: str = ""):
    """快取函數結果的裝飾器

    Args:
        ttl: 快取存活時間（秒）
        key_prefix: 快取鍵值前綴

    Returns:
        裝飾器函數
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成快取鍵值
            cache_key = cache_manager._generate_cache_key(
                f"{key_prefix}{func.__name__}", args, kwargs
            )

            # 嘗試從快取中獲取結果
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 執行函數並快取結果
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


@st.cache_data(ttl=3600)
def cache_dataframe_query(query: str, params: Dict[str, Any] = None) -> Any:
    """快取資料框查詢結果

    Args:
        query: 查詢語句
        params: 查詢參數

    Returns:
        查詢結果
    """
    # 這裡應該實際執行資料庫查詢
    # 為了示例，我們返回一個模擬結果
    return f"Query result for: {query} with params: {params}"


@st.cache_resource
def get_static_resource(resource_path: str) -> Any:
    """快取靜態資源

    Args:
        resource_path: 資源路徑

    Returns:
        資源內容
    """
    # 這裡應該載入實際的靜態資源
    # 為了示例，我們返回一個模擬結果
    return f"Static resource: {resource_path}"


def optimize_memory_usage():
    """優化記憶體使用"""
    # 清理過期的快取項目
    cache_manager._cleanup_memory_cache()

    # 清理 Streamlit 的內建快取
    st.cache_data.clear()
    st.cache_resource.clear()

    logger.info("記憶體優化完成")


def get_cache_dashboard_data() -> Dict[str, Any]:
    """獲取快取儀表板資料

    Returns:
        快取儀表板資料
    """
    stats = cache_manager.get_stats()

    return {
        "cache_stats": stats,
        "streamlit_cache_info": {
            "data_cache_size": len(st.cache_data._cache_info),
            "resource_cache_size": len(st.cache_resource._cache_info),
        },
    }
