"""快取管理器

此模組實現了訊號產生器的快取機制，提升計算效能。
"""

import hashlib
import logging
import pickle
import time
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class CacheManager:
    """快取管理器

    提供 LRU 快取、時間戳快取和持久化快取功能。
    """

    def __init__(self, cache_dir: str = "cache", max_memory_items: int = 100):
        """初始化快取管理器

        Args:
            cache_dir (str): 快取目錄
            max_memory_items (int): 記憶體快取最大項目數
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # 記憶體快取 (LRU)
        self.memory_cache: Dict[str, Tuple[Any, float]] = {}
        self.access_times: Dict[str, float] = {}
        self.max_memory_items = max_memory_items

        # 快取統計
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'disk_reads': 0,
            'disk_writes': 0
        }

    def _generate_cache_key(self, func_name: str, *args, **kwargs) -> str:
        """生成快取鍵值

        Args:
            func_name (str): 函數名稱
            *args: 位置參數
            **kwargs: 關鍵字參數

        Returns:
            str: 快取鍵值
        """
        # 創建參數的雜湊值
        key_data = {
            'func': func_name,
            'args': str(args),
            'kwargs': sorted(kwargs.items())
        }

        key_str = str(key_data)
        return hashlib.md5(key_str.encode(), usedforsecurity=False).hexdigest()

    def _evict_lru_item(self):
        """移除最久未使用的項目"""
        if not self.access_times:
            return

        # 找到最久未使用的項目
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])

        # 移除項目
        del self.memory_cache[lru_key]
        del self.access_times[lru_key]
        self.stats['evictions'] += 1

        logger.debug("移除 LRU 快取項目: %s", lru_key)

    def get(self, key: str) -> Optional[Any]:
        """獲取快取項目

        Args:
            key (str): 快取鍵值

        Returns:
            Optional[Any]: 快取的值，如果不存在則返回 None
        """
        current_time = time.time()

        # 檢查記憶體快取
        if key in self.memory_cache:
            value, timestamp = self.memory_cache[key]
            self.access_times[key] = current_time
            self.stats['hits'] += 1
            logger.debug("記憶體快取命中: %s", key)
            return value

        # 檢查磁碟快取
        cache_file = self.cache_dir / f"{key}.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    value, timestamp = cached_data['value'], cached_data['timestamp']

                # 將項目載入記憶體快取
                self._put_memory_cache(key, value, timestamp)
                self.stats['hits'] += 1
                self.stats['disk_reads'] += 1
                logger.debug("磁碟快取命中: %s", key)
                return value

            except Exception as e:
                logger.warning("讀取磁碟快取失敗: %s", e)
                # 刪除損壞的快取檔案
                cache_file.unlink(missing_ok=True)

        self.stats['misses'] += 1
        return None

    def put(self, key: str, value: Any, persist: bool = True):
        """存儲快取項目

        Args:
            key (str): 快取鍵值
            value (Any): 要快取的值
            persist (bool): 是否持久化到磁碟
        """
        current_time = time.time()

        # 存儲到記憶體快取
        self._put_memory_cache(key, value, current_time)

        # 持久化到磁碟
        if persist:
            try:
                cache_file = self.cache_dir / f"{key}.pkl"
                cached_data = {
                    'value': value,
                    'timestamp': current_time
                }

                with open(cache_file, 'wb') as f:
                    pickle.dump(cached_data, f)

                self.stats['disk_writes'] += 1
                logger.debug("快取已持久化: %s", key)

            except Exception as e:
                logger.warning("持久化快取失敗: %s", e)

    def _put_memory_cache(self, key: str, value: Any, timestamp: float):
        """存儲到記憶體快取"""
        # 檢查是否需要清理空間
        if len(self.memory_cache) >= self.max_memory_items:
            self._evict_lru_item()

        self.memory_cache[key] = (value, timestamp)
        self.access_times[key] = timestamp

    def invalidate(self, pattern: Optional[str] = None):
        """使快取失效

        Args:
            pattern (str, optional): 鍵值模式，如果為 None 則清除所有快取
        """
        if pattern is None:
            # 清除所有快取
            self.memory_cache.clear()
            self.access_times.clear()

            # 清除磁碟快取
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()

            logger.info("已清除所有快取")
        else:
            # 清除匹配模式的快取
            keys_to_remove = [key for key in self.memory_cache.keys() if pattern in key]

            for key in keys_to_remove:
                del self.memory_cache[key]
                del self.access_times[key]

                # 刪除磁碟快取檔案
                cache_file = self.cache_dir / f"{key}.pkl"
                cache_file.unlink(missing_ok=True)

            logger.info("已清除匹配模式 '%s' 的快取，共 %d 項", pattern, len(keys_to_remove))

    def get_stats(self) -> Dict[str, Any]:
        """獲取快取統計資訊

        Returns:
            Dict[str, Any]: 快取統計資訊
        """
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0

        return {
            **self.stats,
            'hit_rate': hit_rate,
            'memory_items': len(self.memory_cache),
            'disk_items': len(list(self.cache_dir.glob("*.pkl")))
        }

    def cleanup_expired(self, max_age_hours: float = 24):
        """清理過期的快取項目

        Args:
            max_age_hours (float): 最大快取時間（小時）
        """
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600

        # 清理記憶體快取
        expired_keys = []
        for key, (value, timestamp) in self.memory_cache.items():
            if current_time - timestamp > max_age_seconds:
                expired_keys.append(key)

        for key in expired_keys:
            del self.memory_cache[key]
            del self.access_times[key]

        # 清理磁碟快取
        disk_expired = 0
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                if current_time - cache_file.stat().st_mtime > max_age_seconds:
                    cache_file.unlink()
                    disk_expired += 1
            except Exception as e:
                logger.warning("清理過期快取檔案失敗: %s", e)

        logger.info("清理過期快取完成，記憶體: %d 項，磁碟: %d 項",
                   len(expired_keys), disk_expired)


# 全域快取管理器實例
_cache_manager = CacheManager()


def cached(expire_hours: float = 24, persist: bool = True):
    """快取裝飾器

    Args:
        expire_hours (float): 快取過期時間（小時）
        persist (bool): 是否持久化到磁碟

    Returns:
        function: 裝飾後的函數
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成快取鍵值
            cache_key = _cache_manager._generate_cache_key(func.__name__, *args, **kwargs)

            # 嘗試從快取獲取
            cached_result = _cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 執行函數並快取結果
            result = func(*args, **kwargs)
            _cache_manager.put(cache_key, result, persist=persist)

            return result

        # 添加快取管理方法
        wrapper.invalidate_cache = lambda pattern=None: _cache_manager.invalidate(pattern)
        wrapper.get_cache_stats = lambda: _cache_manager.get_stats()

        return wrapper
    return decorator


def get_cache_manager() -> CacheManager:
    """獲取全域快取管理器

    Returns:
        CacheManager: 快取管理器實例
    """
    return _cache_manager
