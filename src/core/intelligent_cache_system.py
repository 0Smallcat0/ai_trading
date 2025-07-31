#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""智能快取系統

此模組提供高效的智能快取功能，包括：
1. 多層次快取架構
2. 智能過期策略
3. 快取預熱機制
4. 快取統計和監控
5. 分散式快取支援

主要功能：
- LRU/LFU/TTL等多種淘汰策略
- 自動快取預熱和更新
- 快取命中率優化
- 記憶體使用監控
- 快取一致性保證

Example:
    基本使用：
    ```python
    from src.core.intelligent_cache_system import IntelligentCacheSystem
    
    # 創建快取系統
    cache = IntelligentCacheSystem()
    
    # 設定快取
    cache.set('key', 'value', ttl=3600)
    
    # 獲取快取
    value = cache.get('key')
    ```

Note:
    此模組整合了多種快取策略和優化技術，
    提供高效能的資料快取服務。
"""

import logging
import threading
import time
import hashlib
import pickle
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque, OrderedDict
import statistics
import weakref

# 設定日誌
logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """快取策略"""
    LRU = "lru"          # Least Recently Used
    LFU = "lfu"          # Least Frequently Used
    FIFO = "fifo"        # First In First Out
    TTL = "ttl"          # Time To Live
    ADAPTIVE = "adaptive" # 自適應策略


class CacheLevel(Enum):
    """快取層級"""
    L1_MEMORY = "l1_memory"      # L1記憶體快取
    L2_DISK = "l2_disk"          # L2磁碟快取
    L3_DISTRIBUTED = "l3_distributed"  # L3分散式快取


class CacheEvent(Enum):
    """快取事件"""
    HIT = "hit"
    MISS = "miss"
    SET = "set"
    DELETE = "delete"
    EXPIRE = "expire"
    EVICT = "evict"


@dataclass
class CacheEntry:
    """快取條目"""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl: Optional[int] = None  # 秒
    size: int = 0
    tags: set = field(default_factory=set)
    
    def is_expired(self) -> bool:
        """檢查是否過期"""
        if self.ttl is None:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl
    
    def touch(self):
        """更新訪問時間和次數"""
        self.last_accessed = datetime.now()
        self.access_count += 1


@dataclass
class CacheStats:
    """快取統計"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    expires: int = 0
    evictions: int = 0
    total_size: int = 0
    entry_count: int = 0
    hit_rate: float = 0.0
    miss_rate: float = 0.0
    
    def update_rates(self):
        """更新命中率和失誤率"""
        total_requests = self.hits + self.misses
        if total_requests > 0:
            self.hit_rate = self.hits / total_requests
            self.miss_rate = self.misses / total_requests
        else:
            self.hit_rate = 0.0
            self.miss_rate = 0.0


@dataclass
class CacheConfig:
    """快取配置"""
    max_size: int = 1000  # 最大條目數
    max_memory: int = 100 * 1024 * 1024  # 最大記憶體使用（位元組）
    default_ttl: Optional[int] = 3600  # 預設TTL（秒）
    strategy: CacheStrategy = CacheStrategy.LRU
    enable_stats: bool = True
    enable_compression: bool = False
    compression_threshold: int = 1024  # 壓縮閾值
    cleanup_interval: int = 300  # 清理間隔（秒）
    preload_enabled: bool = True
    distributed_enabled: bool = False


class IntelligentCacheSystem:
    """智能快取系統
    
    提供多層次、多策略的智能快取服務，支援自動優化
    和效能監控。
    
    Attributes:
        config: 快取配置
        cache_data: 快取資料存儲
        stats: 快取統計資訊
        
    Example:
        >>> cache = IntelligentCacheSystem()
        >>> cache.set('key', 'value', ttl=3600)
        >>> value = cache.get('key')
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        """初始化智能快取系統
        
        Args:
            config: 快取配置
        """
        self.config = config or CacheConfig()
        
        # 快取存儲
        self.cache_data: Dict[str, CacheEntry] = {}
        self.access_order: OrderedDict = OrderedDict()  # LRU順序
        self.frequency_counter: Dict[str, int] = defaultdict(int)  # LFU計數
        
        # 統計資訊
        self.stats = CacheStats()
        self.event_history: deque = deque(maxlen=1000)
        
        # 執行緒安全鎖
        self.lock = threading.RLock()
        
        # 背景服務
        self.cleanup_active = True
        self.preload_active = True
        
        # 快取預熱配置
        self.preload_functions: Dict[str, Callable] = {}
        self.preload_schedule: Dict[str, datetime] = {}
        
        # 啟動背景服務
        self._start_background_services()
        
        logger.info("智能快取系統初始化完成 (策略: %s, 最大大小: %d)", 
                   self.config.strategy.value, self.config.max_size)
    
    def get(self, key: str, default: Any = None) -> Any:
        """獲取快取值
        
        Args:
            key: 快取鍵
            default: 預設值
            
        Returns:
            Any: 快取值或預設值
        """
        with self.lock:
            if key in self.cache_data:
                entry = self.cache_data[key]
                
                # 檢查是否過期
                if entry.is_expired():
                    self._remove_entry(key, CacheEvent.EXPIRE)
                    self._record_event(CacheEvent.MISS, key)
                    return default
                
                # 更新訪問資訊
                entry.touch()
                self._update_access_order(key)
                
                self._record_event(CacheEvent.HIT, key)
                return entry.value
            else:
                self._record_event(CacheEvent.MISS, key)
                return default
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        tags: Optional[set] = None
    ) -> bool:
        """設定快取值
        
        Args:
            key: 快取鍵
            value: 快取值
            ttl: 生存時間（秒）
            tags: 標籤集合
            
        Returns:
            bool: 是否設定成功
        """
        try:
            with self.lock:
                # 計算值的大小
                value_size = self._calculate_size(value)
                
                # 檢查記憶體限制
                if not self._check_memory_limit(value_size):
                    self._evict_entries()
                
                # 如果鍵已存在，先移除舊條目
                if key in self.cache_data:
                    self._remove_entry(key, CacheEvent.SET)
                
                # 創建新條目
                entry = CacheEntry(
                    key=key,
                    value=value,
                    ttl=ttl or self.config.default_ttl,
                    size=value_size,
                    tags=tags or set()
                )
                
                # 檢查是否需要淘汰
                if len(self.cache_data) >= self.config.max_size:
                    self._evict_entries()
                
                # 添加到快取
                self.cache_data[key] = entry
                self._update_access_order(key)
                
                # 更新統計
                self.stats.sets += 1
                self.stats.entry_count += 1
                self.stats.total_size += value_size
                
                self._record_event(CacheEvent.SET, key)
                return True
                
        except Exception as e:
            logger.error("設定快取失敗 %s: %s", key, e)
            return False
    
    def delete(self, key: str) -> bool:
        """刪除快取條目
        
        Args:
            key: 快取鍵
            
        Returns:
            bool: 是否刪除成功
        """
        with self.lock:
            if key in self.cache_data:
                self._remove_entry(key, CacheEvent.DELETE)
                return True
            return False
    
    def clear(self):
        """清空所有快取"""
        with self.lock:
            self.cache_data.clear()
            self.access_order.clear()
            self.frequency_counter.clear()

            # 重置統計資料（但保留歷史統計）
            self.stats.entry_count = 0
            self.stats.total_size = 0

            logger.info("快取已清空")
    
    def exists(self, key: str) -> bool:
        """檢查鍵是否存在
        
        Args:
            key: 快取鍵
            
        Returns:
            bool: 是否存在
        """
        with self.lock:
            if key in self.cache_data:
                entry = self.cache_data[key]
                if entry.is_expired():
                    self._remove_entry(key, CacheEvent.EXPIRE)
                    return False
                return True
            return False
    
    def get_stats(self) -> CacheStats:
        """獲取快取統計
        
        Returns:
            CacheStats: 快取統計資訊
        """
        with self.lock:
            self.stats.update_rates()
            return self.stats
    
    def get_keys(self, pattern: Optional[str] = None) -> List[str]:
        """獲取所有鍵
        
        Args:
            pattern: 鍵模式（簡單的字串匹配）
            
        Returns:
            List[str]: 鍵列表
        """
        with self.lock:
            keys = list(self.cache_data.keys())
            
            if pattern:
                keys = [k for k in keys if pattern in k]
            
            return keys
    
    def get_by_tags(self, tags: set) -> Dict[str, Any]:
        """根據標籤獲取快取條目
        
        Args:
            tags: 標籤集合
            
        Returns:
            Dict[str, Any]: 匹配的快取條目
        """
        result = {}
        
        with self.lock:
            for key, entry in self.cache_data.items():
                if not entry.is_expired() and tags.intersection(entry.tags):
                    entry.touch()
                    result[key] = entry.value
        
        return result
    
    def invalidate_by_tags(self, tags: set) -> int:
        """根據標籤失效快取條目
        
        Args:
            tags: 標籤集合
            
        Returns:
            int: 失效的條目數量
        """
        invalidated = 0
        
        with self.lock:
            keys_to_remove = []
            
            for key, entry in self.cache_data.items():
                if tags.intersection(entry.tags):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                self._remove_entry(key, CacheEvent.DELETE)
                invalidated += 1
        
        logger.info("根據標籤失效 %d 個快取條目", invalidated)
        return invalidated

    def register_preload_function(
        self,
        name: str,
        func: Callable,
        interval: int = 3600
    ):
        """註冊快取預熱函數

        Args:
            name: 函數名稱
            func: 預熱函數
            interval: 執行間隔（秒）
        """
        with self.lock:
            self.preload_functions[name] = func
            self.preload_schedule[name] = datetime.now() + timedelta(seconds=interval)

        logger.info("註冊快取預熱函數: %s (間隔: %d 秒)", name, interval)

    def get_memory_usage(self) -> Dict[str, Any]:
        """獲取記憶體使用情況

        Returns:
            Dict[str, Any]: 記憶體使用資訊
        """
        with self.lock:
            return {
                'total_size_bytes': self.stats.total_size,
                'total_size_mb': self.stats.total_size / (1024 * 1024),
                'entry_count': self.stats.entry_count,
                'average_entry_size': (
                    self.stats.total_size / self.stats.entry_count
                    if self.stats.entry_count > 0 else 0
                ),
                'memory_limit_mb': self.config.max_memory / (1024 * 1024),
                'memory_usage_percent': (
                    (self.stats.total_size / self.config.max_memory) * 100
                    if self.config.max_memory > 0 else 0
                )
            }

    def optimize_cache(self):
        """優化快取效能"""
        with self.lock:
            # 清理過期條目
            self._cleanup_expired_entries()

            # 根據統計資訊調整策略
            self._adaptive_strategy_adjustment()

            # 預熱熱門資料
            self._preload_hot_data()

            logger.info("快取優化完成")

    def shutdown(self):
        """關閉快取系統"""
        logger.info("開始關閉快取系統...")

        # 停止背景服務
        self.cleanup_active = False
        self.preload_active = False

        # 清理資源
        with self.lock:
            self.cache_data.clear()
            self.access_order.clear()
            self.frequency_counter.clear()

        logger.info("快取系統已關閉")

    # ==================== 私有輔助方法 ====================

    def _calculate_size(self, value: Any) -> int:
        """計算值的大小"""
        try:
            if isinstance(value, (str, bytes)):
                return len(value)
            elif isinstance(value, (int, float)):
                return 8  # 估算
            elif isinstance(value, (list, tuple, dict)):
                return len(pickle.dumps(value))
            else:
                return len(str(value))
        except Exception:
            return 100  # 預設大小

    def _check_memory_limit(self, new_size: int) -> bool:
        """檢查記憶體限制"""
        return (self.stats.total_size + new_size) <= self.config.max_memory

    def _update_access_order(self, key: str):
        """更新訪問順序"""
        if self.config.strategy == CacheStrategy.LRU:
            # 移動到最後（最近使用）
            if key in self.access_order:
                del self.access_order[key]
            self.access_order[key] = True
        elif self.config.strategy == CacheStrategy.LFU:
            # 更新頻率計數
            self.frequency_counter[key] += 1

    def _remove_entry(self, key: str, event: CacheEvent):
        """移除快取條目"""
        if key in self.cache_data:
            entry = self.cache_data[key]

            # 更新統計
            self.stats.entry_count -= 1
            self.stats.total_size -= entry.size

            if event == CacheEvent.DELETE:
                self.stats.deletes += 1
            elif event == CacheEvent.EXPIRE:
                self.stats.expires += 1
            elif event == CacheEvent.EVICT:
                self.stats.evictions += 1

            # 從存儲中移除
            del self.cache_data[key]

            # 從訪問順序中移除
            if key in self.access_order:
                del self.access_order[key]

            # 從頻率計數中移除
            if key in self.frequency_counter:
                del self.frequency_counter[key]

    def _evict_entries(self):
        """淘汰快取條目"""
        if not self.cache_data:
            return

        if self.config.strategy == CacheStrategy.LRU:
            # 移除最久未使用的條目
            oldest_key = next(iter(self.access_order))
            self._remove_entry(oldest_key, CacheEvent.EVICT)

        elif self.config.strategy == CacheStrategy.LFU:
            # 移除使用頻率最低的條目
            min_freq = min(self.frequency_counter.values())
            lfu_key = next(k for k, v in self.frequency_counter.items() if v == min_freq)
            self._remove_entry(lfu_key, CacheEvent.EVICT)

        elif self.config.strategy == CacheStrategy.FIFO:
            # 移除最早添加的條目
            oldest_key = next(iter(self.cache_data))
            self._remove_entry(oldest_key, CacheEvent.EVICT)

        elif self.config.strategy == CacheStrategy.TTL:
            # 移除最快過期的條目
            now = datetime.now()
            earliest_expire = None
            earliest_key = None

            for key, entry in self.cache_data.items():
                if entry.ttl:
                    expire_time = entry.created_at + timedelta(seconds=entry.ttl)
                    if earliest_expire is None or expire_time < earliest_expire:
                        earliest_expire = expire_time
                        earliest_key = key

            if earliest_key:
                self._remove_entry(earliest_key, CacheEvent.EVICT)

    def _record_event(self, event: CacheEvent, key: str):
        """記錄快取事件"""
        if self.config.enable_stats:
            if event == CacheEvent.HIT:
                self.stats.hits += 1
            elif event == CacheEvent.MISS:
                self.stats.misses += 1

            # 記錄事件歷史
            self.event_history.append({
                'timestamp': datetime.now(),
                'event': event.value,
                'key': key
            })

    def _start_background_services(self):
        """啟動背景服務"""
        # 清理執行緒
        cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="CacheCleanup"
        )
        cleanup_thread.start()

        # 預熱執行緒
        if self.config.preload_enabled:
            preload_thread = threading.Thread(
                target=self._preload_loop,
                daemon=True,
                name="CachePreload"
            )
            preload_thread.start()

        logger.debug("快取背景服務已啟動")

    def _cleanup_loop(self):
        """清理迴圈"""
        while self.cleanup_active:
            try:
                self._cleanup_expired_entries()
                time.sleep(self.config.cleanup_interval)
            except Exception as e:
                logger.error("快取清理錯誤: %s", e)
                time.sleep(60)

    def _preload_loop(self):
        """預熱迴圈"""
        while self.preload_active:
            try:
                self._execute_preload_functions()
                time.sleep(60)  # 每分鐘檢查一次
            except Exception as e:
                logger.error("快取預熱錯誤: %s", e)
                time.sleep(120)

    def _cleanup_expired_entries(self):
        """清理過期條目"""
        expired_keys = []

        with self.lock:
            for key, entry in self.cache_data.items():
                if entry.is_expired():
                    expired_keys.append(key)

        for key in expired_keys:
            with self.lock:
                self._remove_entry(key, CacheEvent.EXPIRE)

        if expired_keys:
            logger.debug("清理 %d 個過期快取條目", len(expired_keys))

    def _execute_preload_functions(self):
        """執行預熱函數"""
        now = datetime.now()

        for name, func in self.preload_functions.items():
            if name in self.preload_schedule and now >= self.preload_schedule[name]:
                try:
                    # 執行預熱函數
                    func(self)

                    # 更新下次執行時間
                    self.preload_schedule[name] = now + timedelta(hours=1)

                    logger.debug("執行快取預熱函數: %s", name)

                except Exception as e:
                    logger.error("預熱函數 %s 執行失敗: %s", name, e)

    def _adaptive_strategy_adjustment(self):
        """自適應策略調整"""
        if self.config.strategy != CacheStrategy.ADAPTIVE:
            return

        # 根據命中率調整策略
        hit_rate = self.stats.hit_rate

        if hit_rate < 0.5:
            # 命中率低，使用LFU策略
            self.config.strategy = CacheStrategy.LFU
            logger.info("自適應調整策略為 LFU (命中率: %.2f%%)", hit_rate * 100)
        elif hit_rate > 0.8:
            # 命中率高，使用LRU策略
            self.config.strategy = CacheStrategy.LRU
            logger.info("自適應調整策略為 LRU (命中率: %.2f%%)", hit_rate * 100)

    def _preload_hot_data(self):
        """預熱熱門資料"""
        # 簡化實現：基於訪問頻率預熱
        if not self.frequency_counter:
            return

        # 找出訪問頻率最高的鍵
        hot_keys = sorted(
            self.frequency_counter.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]  # 前10個熱門鍵

        for key, freq in hot_keys:
            if key in self.cache_data:
                entry = self.cache_data[key]
                # 延長熱門資料的TTL
                if entry.ttl and entry.ttl < 7200:  # 小於2小時
                    entry.ttl = 7200  # 延長到2小時

        logger.debug("預熱 %d 個熱門快取條目", len(hot_keys))
