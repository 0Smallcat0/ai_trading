# -*- coding: utf-8 -*-
"""增強快取管理器

此模組提供針對數據源系統優化的快取管理功能，支援增量更新、
智能失效和多層快取架構。

主要功能：
- 多層快取架構 (內存 + 磁盤 + Redis)
- 智能快取策略 (LRU, TTL, 增量更新)
- 數據源專用快取優化
- 增量更新和差異檢測
- 快取統計和性能監控
- 自動快取清理和優化

支援的快取類型：
- realtime: 實時數據快取 (TTL: 60秒)
- daily: 日線數據快取 (TTL: 1小時)
- historical: 歷史數據快取 (TTL: 24小時)
- metadata: 元數據快取 (TTL: 1週)
- computed: 計算結果快取 (TTL: 可配置)

Example:
    >>> from src.utils.enhanced_cache_manager import EnhancedCacheManager
    >>> cache = EnhancedCacheManager({
    ...     'memory_size_mb': 512,
    ...     'disk_size_gb': 10,
    ...     'enable_redis': True
    ... })
    >>> 
    >>> # 快取實時數據
    >>> cache.set('realtime:000001', price_data, cache_type='realtime')
    >>> 
    >>> # 增量更新歷史數據
    >>> cache.update_incremental('daily:000001', new_data, merge_key='date')
    >>> 
    >>> # 獲取快取數據
    >>> data = cache.get('daily:000001')
"""

import logging
import pickle
import hashlib
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
from collections import OrderedDict, defaultdict
from pathlib import Path
import pandas as pd
import numpy as np

# 設定日誌
logger = logging.getLogger(__name__)


class CacheStats:
    """快取統計"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.evictions = 0
        self.size_bytes = 0
        self.start_time = datetime.now()
        self.lock = threading.Lock()
    
    def record_hit(self):
        with self.lock:
            self.hits += 1
    
    def record_miss(self):
        with self.lock:
            self.misses += 1
    
    def record_set(self, size_bytes: int = 0):
        with self.lock:
            self.sets += 1
            self.size_bytes += size_bytes
    
    def record_delete(self, size_bytes: int = 0):
        with self.lock:
            self.deletes += 1
            self.size_bytes -= size_bytes
    
    def record_eviction(self, size_bytes: int = 0):
        with self.lock:
            self.evictions += 1
            self.size_bytes -= size_bytes
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def uptime_seconds(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()
    
    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            return {
                'hits': self.hits,
                'misses': self.misses,
                'sets': self.sets,
                'deletes': self.deletes,
                'evictions': self.evictions,
                'hit_rate': self.hit_rate,
                'size_bytes': self.size_bytes,
                'size_mb': self.size_bytes / (1024 * 1024),
                'uptime_seconds': self.uptime_seconds
            }


class CacheEntry:
    """快取條目"""
    
    def __init__(self, key: str, value: Any, ttl: Optional[int] = None, 
                 cache_type: str = 'default', metadata: Optional[Dict] = None):
        self.key = key
        self.value = value
        self.cache_type = cache_type
        self.metadata = metadata or {}
        
        self.created_at = datetime.now()
        self.accessed_at = self.created_at
        self.access_count = 0
        
        # 設定過期時間
        if ttl is not None:
            self.expires_at = self.created_at + timedelta(seconds=ttl)
        else:
            self.expires_at = None
        
        # 計算大小
        self.size_bytes = self._calculate_size()
    
    def _calculate_size(self) -> int:
        """計算條目大小"""
        try:
            return len(pickle.dumps(self.value))
        except:
            return 1024  # 預設大小
    
    def is_expired(self) -> bool:
        """檢查是否過期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def touch(self):
        """更新訪問時間"""
        self.accessed_at = datetime.now()
        self.access_count += 1
    
    def get_age_seconds(self) -> float:
        """獲取條目年齡（秒）"""
        return (datetime.now() - self.created_at).total_seconds()


class MemoryCache:
    """內存快取"""
    
    def __init__(self, max_size_mb: int = 256):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()
        self.stats = CacheStats()
    
    def get(self, key: str) -> Optional[Any]:
        """獲取快取值"""
        with self.lock:
            if key not in self.cache:
                self.stats.record_miss()
                return None
            
            entry = self.cache[key]
            
            # 檢查過期
            if entry.is_expired():
                del self.cache[key]
                self.stats.record_delete(entry.size_bytes)
                self.stats.record_miss()
                return None
            
            # 更新訪問信息
            entry.touch()
            
            # 移到最後（LRU）
            self.cache.move_to_end(key)
            
            self.stats.record_hit()
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, 
            cache_type: str = 'default', metadata: Optional[Dict] = None):
        """設定快取值"""
        with self.lock:
            entry = CacheEntry(key, value, ttl, cache_type, metadata)
            
            # 檢查是否需要清理空間
            self._ensure_space(entry.size_bytes)
            
            # 如果鍵已存在，先刪除舊值
            if key in self.cache:
                old_entry = self.cache[key]
                self.stats.record_delete(old_entry.size_bytes)
            
            self.cache[key] = entry
            self.stats.record_set(entry.size_bytes)
    
    def delete(self, key: str) -> bool:
        """刪除快取值"""
        with self.lock:
            if key in self.cache:
                entry = self.cache.pop(key)
                self.stats.record_delete(entry.size_bytes)
                return True
            return False
    
    def _ensure_space(self, needed_bytes: int):
        """確保有足夠空間"""
        while (self.stats.size_bytes + needed_bytes > self.max_size_bytes and 
               len(self.cache) > 0):
            # 移除最舊的條目（LRU）
            oldest_key, oldest_entry = self.cache.popitem(last=False)
            self.stats.record_eviction(oldest_entry.size_bytes)
    
    def clear(self):
        """清空快取"""
        with self.lock:
            self.cache.clear()
            self.stats = CacheStats()
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取統計信息"""
        with self.lock:
            stats = self.stats.get_stats()
            stats.update({
                'entries': len(self.cache),
                'max_size_bytes': self.max_size_bytes,
                'max_size_mb': self.max_size_bytes / (1024 * 1024)
            })
            return stats


class DiskCache:
    """磁盤快取"""
    
    def __init__(self, cache_dir: str = 'cache', max_size_gb: int = 5):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_gb * 1024 * 1024 * 1024
        self.lock = threading.Lock()
        self.stats = CacheStats()
        
        # 初始化時清理過期文件
        self._cleanup_expired_files()
    
    def _get_file_path(self, key: str) -> Path:
        """獲取快取文件路徑"""
        # 使用 hash 避免文件名過長或包含特殊字符
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    def _get_metadata_path(self, key: str) -> Path:
        """獲取元數據文件路徑"""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.meta"
    
    def get(self, key: str) -> Optional[Any]:
        """獲取快取值"""
        with self.lock:
            file_path = self._get_file_path(key)
            meta_path = self._get_metadata_path(key)
            
            if not file_path.exists() or not meta_path.exists():
                self.stats.record_miss()
                return None
            
            try:
                # 讀取元數據
                with open(meta_path, 'rb') as f:
                    metadata = pickle.load(f)
                
                # 檢查過期
                if metadata.get('expires_at'):
                    expires_at = datetime.fromisoformat(metadata['expires_at'])
                    if datetime.now() > expires_at:
                        file_path.unlink(missing_ok=True)
                        meta_path.unlink(missing_ok=True)
                        self.stats.record_miss()
                        return None
                
                # 讀取數據
                with open(file_path, 'rb') as f:
                    value = pickle.load(f)
                
                # 更新訪問時間
                metadata['accessed_at'] = datetime.now().isoformat()
                metadata['access_count'] = metadata.get('access_count', 0) + 1
                
                with open(meta_path, 'wb') as f:
                    pickle.dump(metadata, f)
                
                self.stats.record_hit()
                return value
                
            except Exception as e:
                logger.warning(f"讀取磁盤快取失敗 {key}: {e}")
                file_path.unlink(missing_ok=True)
                meta_path.unlink(missing_ok=True)
                self.stats.record_miss()
                return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, 
            cache_type: str = 'default', metadata: Optional[Dict] = None):
        """設定快取值"""
        with self.lock:
            file_path = self._get_file_path(key)
            meta_path = self._get_metadata_path(key)
            
            try:
                # 準備元數據
                meta = {
                    'key': key,
                    'cache_type': cache_type,
                    'created_at': datetime.now().isoformat(),
                    'accessed_at': datetime.now().isoformat(),
                    'access_count': 0,
                    'metadata': metadata or {}
                }
                
                if ttl is not None:
                    expires_at = datetime.now() + timedelta(seconds=ttl)
                    meta['expires_at'] = expires_at.isoformat()
                
                # 寫入數據
                with open(file_path, 'wb') as f:
                    pickle.dump(value, f)
                
                # 寫入元數據
                with open(meta_path, 'wb') as f:
                    pickle.dump(meta, f)
                
                # 計算大小
                size_bytes = file_path.stat().st_size + meta_path.stat().st_size
                self.stats.record_set(size_bytes)
                
                # 檢查磁盤空間
                self._cleanup_if_needed()
                
            except Exception as e:
                logger.error(f"寫入磁盤快取失敗 {key}: {e}")
    
    def delete(self, key: str) -> bool:
        """刪除快取值"""
        with self.lock:
            file_path = self._get_file_path(key)
            meta_path = self._get_metadata_path(key)
            
            deleted = False
            size_bytes = 0
            
            if file_path.exists():
                size_bytes += file_path.stat().st_size
                file_path.unlink()
                deleted = True
            
            if meta_path.exists():
                size_bytes += meta_path.stat().st_size
                meta_path.unlink()
                deleted = True
            
            if deleted:
                self.stats.record_delete(size_bytes)
            
            return deleted
    
    def _cleanup_expired_files(self):
        """清理過期文件"""
        for meta_file in self.cache_dir.glob("*.meta"):
            try:
                with open(meta_file, 'rb') as f:
                    metadata = pickle.load(f)
                
                if metadata.get('expires_at'):
                    expires_at = datetime.fromisoformat(metadata['expires_at'])
                    if datetime.now() > expires_at:
                        # 刪除過期文件
                        key_hash = meta_file.stem
                        cache_file = self.cache_dir / f"{key_hash}.cache"
                        
                        meta_file.unlink(missing_ok=True)
                        cache_file.unlink(missing_ok=True)
                        
            except Exception as e:
                logger.warning(f"清理過期文件失敗 {meta_file}: {e}")
                meta_file.unlink(missing_ok=True)
    
    def _cleanup_if_needed(self):
        """如果需要則清理磁盤空間"""
        total_size = sum(f.stat().st_size for f in self.cache_dir.iterdir() if f.is_file())
        
        if total_size > self.max_size_bytes:
            # 獲取所有文件的訪問時間
            files_info = []
            
            for meta_file in self.cache_dir.glob("*.meta"):
                try:
                    with open(meta_file, 'rb') as f:
                        metadata = pickle.load(f)
                    
                    accessed_at = datetime.fromisoformat(metadata.get('accessed_at', metadata['created_at']))
                    files_info.append((accessed_at, meta_file.stem))
                    
                except Exception:
                    continue
            
            # 按訪問時間排序，刪除最舊的文件
            files_info.sort()
            
            for _, key_hash in files_info:
                if total_size <= self.max_size_bytes * 0.8:  # 清理到80%
                    break
                
                cache_file = self.cache_dir / f"{key_hash}.cache"
                meta_file = self.cache_dir / f"{key_hash}.meta"
                
                file_size = 0
                if cache_file.exists():
                    file_size += cache_file.stat().st_size
                    cache_file.unlink()
                
                if meta_file.exists():
                    file_size += meta_file.stat().st_size
                    meta_file.unlink()
                
                total_size -= file_size
                self.stats.record_eviction(file_size)
    
    def clear(self):
        """清空快取"""
        with self.lock:
            for file_path in self.cache_dir.iterdir():
                if file_path.is_file():
                    file_path.unlink()
            self.stats = CacheStats()
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取統計信息"""
        with self.lock:
            stats = self.stats.get_stats()
            
            # 計算實際磁盤使用
            total_size = sum(f.stat().st_size for f in self.cache_dir.iterdir() if f.is_file())
            file_count = len(list(self.cache_dir.glob("*.cache")))
            
            stats.update({
                'entries': file_count,
                'actual_size_bytes': total_size,
                'actual_size_mb': total_size / (1024 * 1024),
                'max_size_bytes': self.max_size_bytes,
                'max_size_gb': self.max_size_bytes / (1024 * 1024 * 1024),
                'cache_dir': str(self.cache_dir)
            })
            
            return stats


class EnhancedCacheManager:
    """增強快取管理器
    
    提供多層快取架構和數據源專用優化。
    
    Attributes:
        memory_cache: 內存快取
        disk_cache: 磁盤快取
        cache_policies: 快取策略配置
        
    Example:
        >>> cache = EnhancedCacheManager({
        ...     'memory_size_mb': 512,
        ...     'disk_size_gb': 10
        ... })
        >>> cache.set('key', data, cache_type='realtime')
        >>> data = cache.get('key')
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化增強快取管理器
        
        Args:
            config: 配置參數
        """
        self.config = config or {}
        
        # 初始化快取層
        self.memory_cache = MemoryCache(
            max_size_mb=self.config.get('memory_size_mb', 256)
        )
        
        self.disk_cache = DiskCache(
            cache_dir=self.config.get('cache_dir', 'cache'),
            max_size_gb=self.config.get('disk_size_gb', 5)
        )
        
        # 快取策略配置
        self.cache_policies = {
            'realtime': {'ttl': 60, 'memory_only': True},
            'daily': {'ttl': 3600, 'use_disk': True},
            'historical': {'ttl': 86400, 'use_disk': True},
            'metadata': {'ttl': 604800, 'use_disk': True},  # 1週
            'computed': {'ttl': 7200, 'use_disk': True},    # 2小時
            'default': {'ttl': 3600, 'use_disk': True}
        }
        
        # 更新用戶配置
        if 'cache_policies' in self.config:
            self.cache_policies.update(self.config['cache_policies'])
        
        logger.info("增強快取管理器初始化完成")
    
    def get(self, key: str) -> Optional[Any]:
        """獲取快取值
        
        Args:
            key: 快取鍵
            
        Returns:
            快取值，如果不存在則返回 None
        """
        # 先檢查內存快取
        value = self.memory_cache.get(key)
        if value is not None:
            return value
        
        # 檢查磁盤快取
        value = self.disk_cache.get(key)
        if value is not None:
            # 將熱數據提升到內存快取
            cache_type = self._extract_cache_type(key)
            policy = self.cache_policies.get(cache_type, self.cache_policies['default'])
            
            if not policy.get('memory_only', False):
                self.memory_cache.set(key, value, ttl=policy['ttl'], cache_type=cache_type)
            
            return value
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, 
            cache_type: str = 'default', metadata: Optional[Dict] = None):
        """設定快取值
        
        Args:
            key: 快取鍵
            value: 快取值
            ttl: 生存時間（秒）
            cache_type: 快取類型
            metadata: 元數據
        """
        policy = self.cache_policies.get(cache_type, self.cache_policies['default'])
        effective_ttl = ttl or policy['ttl']
        
        # 設定內存快取
        self.memory_cache.set(key, value, effective_ttl, cache_type, metadata)
        
        # 根據策略決定是否使用磁盤快取
        if policy.get('use_disk', False) and not policy.get('memory_only', False):
            self.disk_cache.set(key, value, effective_ttl, cache_type, metadata)
    
    def delete(self, key: str) -> bool:
        """刪除快取值
        
        Args:
            key: 快取鍵
            
        Returns:
            是否成功刪除
        """
        memory_deleted = self.memory_cache.delete(key)
        disk_deleted = self.disk_cache.delete(key)
        
        return memory_deleted or disk_deleted
    
    def update_incremental(self, key: str, new_data: pd.DataFrame, 
                          merge_key: str = 'date', cache_type: str = 'daily') -> bool:
        """增量更新快取數據
        
        Args:
            key: 快取鍵
            new_data: 新數據
            merge_key: 合併鍵
            cache_type: 快取類型
            
        Returns:
            是否成功更新
        """
        try:
            # 獲取現有數據
            existing_data = self.get(key)
            
            if existing_data is None:
                # 如果沒有現有數據，直接設定新數據
                self.set(key, new_data, cache_type=cache_type)
                return True
            
            if not isinstance(existing_data, pd.DataFrame) or not isinstance(new_data, pd.DataFrame):
                # 如果不是 DataFrame，直接替換
                self.set(key, new_data, cache_type=cache_type)
                return True
            
            # 合併數據
            if merge_key in existing_data.columns and merge_key in new_data.columns:
                # 移除重複的數據
                existing_data = existing_data[~existing_data[merge_key].isin(new_data[merge_key])]
                
                # 合併數據
                merged_data = pd.concat([existing_data, new_data], ignore_index=True)
                
                # 按合併鍵排序
                if merged_data[merge_key].dtype in ['datetime64[ns]', 'object']:
                    merged_data = merged_data.sort_values(merge_key)
                
                # 更新快取
                self.set(key, merged_data, cache_type=cache_type)
                
                logger.debug(f"增量更新快取 {key}: {len(existing_data)} + {len(new_data)} = {len(merged_data)}")
                return True
            else:
                # 如果沒有合併鍵，直接替換
                self.set(key, new_data, cache_type=cache_type)
                return True
                
        except Exception as e:
            logger.error(f"增量更新快取失敗 {key}: {e}")
            return False
    
    def _extract_cache_type(self, key: str) -> str:
        """從鍵中提取快取類型"""
        if ':' in key:
            return key.split(':', 1)[0]
        return 'default'
    
    def clear(self, cache_type: Optional[str] = None):
        """清空快取
        
        Args:
            cache_type: 要清空的快取類型，None 表示清空所有
        """
        if cache_type is None:
            self.memory_cache.clear()
            self.disk_cache.clear()
        else:
            # TODO: 實現按類型清空
            logger.warning("按類型清空快取功能尚未實現")
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取快取統計信息
        
        Returns:
            快取統計信息
        """
        return {
            'memory_cache': self.memory_cache.get_stats(),
            'disk_cache': self.disk_cache.get_stats(),
            'cache_policies': self.cache_policies,
            'config': self.config
        }
    
    def optimize(self):
        """優化快取性能"""
        # 清理過期的磁盤文件
        self.disk_cache._cleanup_expired_files()
        
        # 如果需要，可以添加更多優化邏輯
        logger.info("快取優化完成")
