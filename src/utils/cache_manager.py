# -*- coding: utf-8 -*-
"""
緩存管理器

此模組提供高效的數據緩存管理功能，
支持多種緩存策略和存儲後端。

主要功能：
- 內存緩存管理
- 磁盤緩存管理
- 緩存過期策略
- 緩存統計和監控
- 緩存清理和優化

緩存策略：
- LRU (Least Recently Used)
- TTL (Time To Live)
- 大小限制
- 自動清理
"""

import logging
import os
import pickle
import json
import hashlib
import time
import threading
from typing import Any, Optional, Dict, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import OrderedDict
import pandas as pd
import gzip

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """緩存條目"""
    key: str
    value: Any
    created_time: datetime
    last_accessed: datetime
    access_count: int
    ttl: Optional[int] = None  # 生存時間（秒）
    size: int = 0  # 數據大小（字節）
    
    def is_expired(self) -> bool:
        """檢查是否過期"""
        if self.ttl is None:
            return False
        
        elapsed = (datetime.now() - self.created_time).total_seconds()
        return elapsed > self.ttl
    
    def update_access(self):
        """更新訪問信息"""
        self.last_accessed = datetime.now()
        self.access_count += 1


class LRUCache:
    """LRU緩存實現"""
    
    def __init__(self, max_size: int = 1000):
        """
        初始化LRU緩存
        
        Args:
            max_size: 最大緩存條目數
        """
        self.max_size = max_size
        self.cache = OrderedDict()
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """獲取緩存值"""
        with self.lock:
            if key in self.cache:
                # 移動到末尾（最近使用）
                value = self.cache.pop(key)
                self.cache[key] = value
                return value
            return None
    
    def set(self, key: str, value: Any):
        """設置緩存值"""
        with self.lock:
            if key in self.cache:
                # 更新現有值
                self.cache.pop(key)
            elif len(self.cache) >= self.max_size:
                # 移除最久未使用的項目
                self.cache.popitem(last=False)
            
            self.cache[key] = value
    
    def delete(self, key: str) -> bool:
        """刪除緩存項"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self):
        """清空緩存"""
        with self.lock:
            self.cache.clear()
    
    def size(self) -> int:
        """獲取緩存大小"""
        return len(self.cache)


class CacheManager:
    """
    緩存管理器
    
    提供統一的緩存管理接口，支持內存和磁盤緩存
    """
    
    def __init__(
        self,
        cache_dir: str = "cache",
        max_memory_size: int = 1000,
        default_ttl: int = 3600,
        enable_disk_cache: bool = True,
        max_disk_size: int = 1024 * 1024 * 1024,  # 1GB
        compression: bool = True
    ):
        """
        初始化緩存管理器
        
        Args:
            cache_dir: 磁盤緩存目錄
            max_memory_size: 最大內存緩存條目數
            default_ttl: 默認TTL（秒）
            enable_disk_cache: 是否啟用磁盤緩存
            max_disk_size: 最大磁盤緩存大小（字節）
            compression: 是否啟用壓縮
        """
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl
        self.enable_disk_cache = enable_disk_cache
        self.max_disk_size = max_disk_size
        self.compression = compression
        
        # 內存緩存
        self.memory_cache = LRUCache(max_memory_size)
        
        # 緩存條目元數據
        self.cache_entries: Dict[str, CacheEntry] = {}
        self.lock = threading.RLock()
        
        # 統計信息
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'disk_reads': 0,
            'disk_writes': 0
        }
        
        # 創建緩存目錄
        if self.enable_disk_cache:
            os.makedirs(self.cache_dir, exist_ok=True)
        
        # 啟動清理線程
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        
        logger.info(f"緩存管理器初始化完成，緩存目錄: {self.cache_dir}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        獲取緩存值
        
        Args:
            key: 緩存鍵
            
        Returns:
            緩存值或None
        """
        with self.lock:
            # 檢查內存緩存
            value = self.memory_cache.get(key)
            if value is not None:
                # 更新訪問信息
                if key in self.cache_entries:
                    self.cache_entries[key].update_access()
                
                self.stats['hits'] += 1
                logger.debug(f"內存緩存命中: {key}")
                return value
            
            # 檢查磁盤緩存
            if self.enable_disk_cache:
                value = self._load_from_disk(key)
                if value is not None:
                    # 加載到內存緩存
                    self.memory_cache.set(key, value)
                    
                    # 更新訪問信息
                    if key in self.cache_entries:
                        self.cache_entries[key].update_access()
                    
                    self.stats['hits'] += 1
                    self.stats['disk_reads'] += 1
                    logger.debug(f"磁盤緩存命中: {key}")
                    return value
            
            self.stats['misses'] += 1
            logger.debug(f"緩存未命中: {key}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        設置緩存值
        
        Args:
            key: 緩存鍵
            value: 緩存值
            ttl: 生存時間（秒），None使用默認值
        """
        with self.lock:
            if ttl is None:
                ttl = self.default_ttl
            
            # 計算數據大小
            try:
                size = len(pickle.dumps(value))
            except:
                size = 0
            
            # 創建緩存條目
            entry = CacheEntry(
                key=key,
                value=value,
                created_time=datetime.now(),
                last_accessed=datetime.now(),
                access_count=1,
                ttl=ttl,
                size=size
            )
            
            # 存儲到內存緩存
            self.memory_cache.set(key, value)
            
            # 存儲到磁盤緩存
            if self.enable_disk_cache:
                self._save_to_disk(key, value, entry)
            
            # 更新元數據
            self.cache_entries[key] = entry
            
            self.stats['sets'] += 1
            logger.debug(f"緩存設置: {key}, TTL: {ttl}s, 大小: {size}字節")
    
    def delete(self, key: str) -> bool:
        """
        刪除緩存項
        
        Args:
            key: 緩存鍵
            
        Returns:
            是否成功刪除
        """
        with self.lock:
            deleted = False
            
            # 從內存緩存刪除
            if self.memory_cache.delete(key):
                deleted = True
            
            # 從磁盤緩存刪除
            if self.enable_disk_cache:
                disk_path = self._get_disk_path(key)
                if os.path.exists(disk_path):
                    try:
                        os.remove(disk_path)
                        deleted = True
                    except Exception as e:
                        logger.error(f"刪除磁盤緩存失敗 {key}: {e}")
            
            # 刪除元數據
            if key in self.cache_entries:
                del self.cache_entries[key]
                deleted = True
            
            if deleted:
                self.stats['deletes'] += 1
                logger.debug(f"緩存刪除: {key}")
            
            return deleted
    
    def clear(self):
        """清空所有緩存"""
        with self.lock:
            # 清空內存緩存
            self.memory_cache.clear()
            
            # 清空磁盤緩存
            if self.enable_disk_cache:
                try:
                    import shutil
                    if os.path.exists(self.cache_dir):
                        shutil.rmtree(self.cache_dir)
                        os.makedirs(self.cache_dir, exist_ok=True)
                except Exception as e:
                    logger.error(f"清空磁盤緩存失敗: {e}")
            
            # 清空元數據
            self.cache_entries.clear()
            
            logger.info("所有緩存已清空")
    
    def _load_from_disk(self, key: str) -> Optional[Any]:
        """從磁盤加載緩存"""
        if not self.enable_disk_cache:
            return None
        
        disk_path = self._get_disk_path(key)
        if not os.path.exists(disk_path):
            return None
        
        try:
            # 檢查緩存條目是否過期
            if key in self.cache_entries:
                entry = self.cache_entries[key]
                if entry.is_expired():
                    # 刪除過期緩存
                    os.remove(disk_path)
                    del self.cache_entries[key]
                    return None
            
            # 加載數據
            if self.compression:
                with gzip.open(disk_path, 'rb') as f:
                    return pickle.load(f)
            else:
                with open(disk_path, 'rb') as f:
                    return pickle.load(f)
                    
        except Exception as e:
            logger.error(f"從磁盤加載緩存失敗 {key}: {e}")
            # 刪除損壞的緩存文件
            try:
                os.remove(disk_path)
            except:
                pass
            return None
    
    def _save_to_disk(self, key: str, value: Any, entry: CacheEntry):
        """保存到磁盤緩存"""
        if not self.enable_disk_cache:
            return
        
        disk_path = self._get_disk_path(key)
        
        try:
            # 檢查磁盤空間
            if self._get_disk_usage() > self.max_disk_size:
                self._cleanup_disk_cache()
            
            # 保存數據
            os.makedirs(os.path.dirname(disk_path), exist_ok=True)
            
            if self.compression:
                with gzip.open(disk_path, 'wb') as f:
                    pickle.dump(value, f)
            else:
                with open(disk_path, 'wb') as f:
                    pickle.dump(value, f)
            
            self.stats['disk_writes'] += 1
            
        except Exception as e:
            logger.error(f"保存到磁盤緩存失敗 {key}: {e}")
    
    def _get_disk_path(self, key: str) -> str:
        """獲取磁盤緩存路徑"""
        # 使用MD5哈希避免文件名過長或包含特殊字符
        hash_key = hashlib.md5(key.encode()).hexdigest()
        subdir = hash_key[:2]  # 使用前兩個字符作為子目錄
        filename = hash_key + ('.gz' if self.compression else '.pkl')
        return os.path.join(self.cache_dir, subdir, filename)
    
    def _get_disk_usage(self) -> int:
        """獲取磁盤緩存使用量"""
        if not os.path.exists(self.cache_dir):
            return 0
        
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(self.cache_dir):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    total_size += os.path.getsize(filepath)
        except Exception as e:
            logger.error(f"計算磁盤使用量失敗: {e}")
        
        return total_size
    
    def _cleanup_disk_cache(self):
        """清理磁盤緩存"""
        if not self.enable_disk_cache:
            return
        
        try:
            # 獲取所有緩存文件及其訪問時間
            cache_files = []
            for dirpath, dirnames, filenames in os.walk(self.cache_dir):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        stat = os.stat(filepath)
                        cache_files.append((filepath, stat.st_atime, stat.st_size))
                    except:
                        continue
            
            # 按訪問時間排序，刪除最久未訪問的文件
            cache_files.sort(key=lambda x: x[1])
            
            current_size = sum(f[2] for f in cache_files)
            target_size = self.max_disk_size * 0.8  # 清理到80%
            
            for filepath, atime, size in cache_files:
                if current_size <= target_size:
                    break
                
                try:
                    os.remove(filepath)
                    current_size -= size
                    logger.debug(f"清理磁盤緩存文件: {filepath}")
                except Exception as e:
                    logger.error(f"刪除緩存文件失敗 {filepath}: {e}")
            
        except Exception as e:
            logger.error(f"清理磁盤緩存失敗: {e}")
    
    def _cleanup_loop(self):
        """清理循環"""
        while True:
            try:
                time.sleep(300)  # 每5分鐘清理一次
                self._cleanup_expired_entries()
            except Exception as e:
                logger.error(f"清理循環出錯: {e}")
    
    def _cleanup_expired_entries(self):
        """清理過期條目"""
        with self.lock:
            expired_keys = []
            
            for key, entry in self.cache_entries.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                self.delete(key)
            
            if expired_keys:
                logger.info(f"清理了 {len(expired_keys)} 個過期緩存條目")
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取緩存統計信息"""
        with self.lock:
            hit_rate = self.stats['hits'] / (self.stats['hits'] + self.stats['misses']) if (self.stats['hits'] + self.stats['misses']) > 0 else 0
            
            return {
                'memory_cache_size': self.memory_cache.size(),
                'total_entries': len(self.cache_entries),
                'disk_usage_bytes': self._get_disk_usage() if self.enable_disk_cache else 0,
                'hit_rate': hit_rate,
                'stats': self.stats.copy()
            }
    
    def get_cache_info(self, key: str) -> Optional[Dict[str, Any]]:
        """獲取緩存條目信息"""
        with self.lock:
            if key in self.cache_entries:
                entry = self.cache_entries[key]
                return {
                    'key': entry.key,
                    'created_time': entry.created_time.isoformat(),
                    'last_accessed': entry.last_accessed.isoformat(),
                    'access_count': entry.access_count,
                    'ttl': entry.ttl,
                    'size': entry.size,
                    'is_expired': entry.is_expired()
                }
            return None
