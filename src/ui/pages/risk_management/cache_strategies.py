"""風險管理緩存策略模組

此模組提供多層緩存策略，包括：
- 內存緩存
- 文件緩存
- 數據庫查詢緩存
- 計算結果緩存

Author: AI Trading System
Version: 1.0.0
"""

import json
import pickle
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Union, Callable
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd


class MemoryCache:
    """內存緩存管理器"""
    
    def __init__(self, max_size: int = 100, default_ttl: int = 300):
        """初始化內存緩存
        
        Args:
            max_size (int): 最大緩存條目數
            default_ttl (int): 預設存活時間（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = {}
        self.access_times = {}
    
    def _generate_key(self, key: str, params: Dict[str, Any] = None) -> str:
        """生成緩存鍵
        
        Args:
            key (str): 基礎鍵名
            params (Dict[str, Any], optional): 參數字典
            
        Returns:
            str: 生成的緩存鍵
        """
        if params:
            param_str = json.dumps(params, sort_keys=True)
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            return f"{key}_{param_hash}"
        return key
    
    def get(self, key: str, params: Dict[str, Any] = None) -> Optional[Any]:
        """獲取緩存值
        
        Args:
            key (str): 緩存鍵
            params (Dict[str, Any], optional): 參數字典
            
        Returns:
            Optional[Any]: 緩存值，如果不存在或過期則返回 None
        """
        cache_key = self._generate_key(key, params)
        
        if cache_key in self.cache:
            cache_data = self.cache[cache_key]
            
            # 檢查是否過期
            if datetime.now() < cache_data["expires_at"]:
                self.access_times[cache_key] = datetime.now()
                return cache_data["value"]
            else:
                # 清理過期緩存
                del self.cache[cache_key]
                if cache_key in self.access_times:
                    del self.access_times[cache_key]
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, params: Dict[str, Any] = None) -> None:
        """設置緩存值
        
        Args:
            key (str): 緩存鍵
            value (Any): 緩存值
            ttl (Optional[int]): 存活時間（秒），如果為 None 則使用預設值
            params (Dict[str, Any], optional): 參數字典
        """
        cache_key = self._generate_key(key, params)
        ttl = ttl or self.default_ttl
        
        # 如果緩存已滿，移除最舊的條目
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        expires_at = datetime.now() + timedelta(seconds=ttl)
        self.cache[cache_key] = {
            "value": value,
            "expires_at": expires_at,
            "created_at": datetime.now()
        }
        self.access_times[cache_key] = datetime.now()
    
    def _evict_oldest(self) -> None:
        """移除最舊的緩存條目"""
        if self.access_times:
            oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
            del self.cache[oldest_key]
            del self.access_times[oldest_key]
    
    def clear(self) -> None:
        """清空所有緩存"""
        self.cache.clear()
        self.access_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取緩存統計信息
        
        Returns:
            Dict[str, Any]: 緩存統計信息
        """
        return {
            "total_entries": len(self.cache),
            "max_size": self.max_size,
            "hit_rate": "N/A",  # 需要額外追蹤來計算
            "oldest_entry": min(self.access_times.values()) if self.access_times else None,
            "newest_entry": max(self.access_times.values()) if self.access_times else None
        }


class FileCache:
    """文件緩存管理器"""
    
    def __init__(self, cache_dir: str = "cache", default_ttl: int = 3600):
        """初始化文件緩存
        
        Args:
            cache_dir (str): 緩存目錄
            default_ttl (int): 預設存活時間（秒）
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.default_ttl = default_ttl
    
    def _get_cache_path(self, key: str) -> Path:
        """獲取緩存文件路徑
        
        Args:
            key (str): 緩存鍵
            
        Returns:
            Path: 緩存文件路徑
        """
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.cache"
    
    def get(self, key: str) -> Optional[Any]:
        """獲取緩存值
        
        Args:
            key (str): 緩存鍵
            
        Returns:
            Optional[Any]: 緩存值，如果不存在或過期則返回 None
        """
        cache_path = self._get_cache_path(key)
        
        if cache_path.exists():
            try:
                with open(cache_path, 'rb') as f:
                    cache_data = pickle.load(f)
                
                # 檢查是否過期
                if datetime.now() < cache_data["expires_at"]:
                    return cache_data["value"]
                else:
                    # 刪除過期文件
                    cache_path.unlink()
            except Exception:
                # 如果讀取失敗，刪除損壞的緩存文件
                if cache_path.exists():
                    cache_path.unlink()
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """設置緩存值
        
        Args:
            key (str): 緩存鍵
            value (Any): 緩存值
            ttl (Optional[int]): 存活時間（秒），如果為 None 則使用預設值
        """
        cache_path = self._get_cache_path(key)
        ttl = ttl or self.default_ttl
        
        expires_at = datetime.now() + timedelta(seconds=ttl)
        cache_data = {
            "value": value,
            "expires_at": expires_at,
            "created_at": datetime.now()
        }
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
        except Exception as e:
            st.warning(f"無法保存緩存到文件: {e}")
    
    def clear(self) -> None:
        """清空所有緩存文件"""
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                cache_file.unlink()
            except Exception:
                pass
    
    def cleanup_expired(self) -> int:
        """清理過期的緩存文件
        
        Returns:
            int: 清理的文件數量
        """
        cleaned_count = 0
        current_time = datetime.now()
        
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                with open(cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
                
                if current_time >= cache_data["expires_at"]:
                    cache_file.unlink()
                    cleaned_count += 1
            except Exception:
                # 刪除損壞的文件
                cache_file.unlink()
                cleaned_count += 1
        
        return cleaned_count


class CacheManager:
    """統一緩存管理器"""
    
    def __init__(self):
        """初始化緩存管理器"""
        self.memory_cache = MemoryCache(max_size=50, default_ttl=300)  # 5 分鐘
        self.file_cache = FileCache(cache_dir="cache/risk_management", default_ttl=3600)  # 1 小時
    
    def get_risk_indicators(self, portfolio_id: str) -> Optional[Dict[str, Any]]:
        """獲取風險指標（帶緩存）
        
        Args:
            portfolio_id (str): 投資組合 ID
            
        Returns:
            Optional[Dict[str, Any]]: 風險指標字典
        """
        cache_key = f"risk_indicators_{portfolio_id}"
        
        # 先檢查內存緩存
        result = self.memory_cache.get(cache_key)
        if result is not None:
            return result
        
        # 再檢查文件緩存
        result = self.file_cache.get(cache_key)
        if result is not None:
            # 將結果放入內存緩存
            self.memory_cache.set(cache_key, result, ttl=300)
            return result
        
        return None
    
    def set_risk_indicators(self, portfolio_id: str, indicators: Dict[str, Any]) -> None:
        """設置風險指標緩存
        
        Args:
            portfolio_id (str): 投資組合 ID
            indicators (Dict[str, Any]): 風險指標字典
        """
        cache_key = f"risk_indicators_{portfolio_id}"
        
        # 同時設置內存和文件緩存
        self.memory_cache.set(cache_key, indicators, ttl=300)
        self.file_cache.set(cache_key, indicators, ttl=3600)
    
    def get_historical_data(self, symbol: str, period: str) -> Optional[pd.DataFrame]:
        """獲取歷史數據（帶緩存）
        
        Args:
            symbol (str): 股票代碼
            period (str): 時間週期
            
        Returns:
            Optional[pd.DataFrame]: 歷史數據
        """
        cache_key = f"historical_data_{symbol}_{period}"
        
        # 歷史數據較大，直接使用文件緩存
        return self.file_cache.get(cache_key)
    
    def set_historical_data(self, symbol: str, period: str, data: pd.DataFrame) -> None:
        """設置歷史數據緩存
        
        Args:
            symbol (str): 股票代碼
            period (str): 時間週期
            data (pd.DataFrame): 歷史數據
        """
        cache_key = f"historical_data_{symbol}_{period}"
        
        # 歷史數據較大，使用文件緩存，TTL 設為 4 小時
        self.file_cache.set(cache_key, data, ttl=14400)
    
    def clear_all_cache(self) -> None:
        """清空所有緩存"""
        self.memory_cache.clear()
        self.file_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """獲取緩存統計信息
        
        Returns:
            Dict[str, Any]: 緩存統計信息
        """
        return {
            "memory_cache": self.memory_cache.get_stats(),
            "file_cache": {
                "cache_dir": str(self.file_cache.cache_dir),
                "file_count": len(list(self.file_cache.cache_dir.glob("*.cache")))
            }
        }


# 全局緩存管理器實例
cache_manager = CacheManager()


def cached_calculation(cache_key: str, ttl: int = 300):
    """緩存計算結果的裝飾器
    
    Args:
        cache_key (str): 緩存鍵前綴
        ttl (int): 存活時間（秒）
        
    Returns:
        Callable: 裝飾後的函數
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # 生成完整的緩存鍵
            full_key = f"{cache_key}_{hash(str(args) + str(kwargs))}"
            
            # 檢查緩存
            result = cache_manager.memory_cache.get(full_key)
            if result is not None:
                return result
            
            # 執行計算並緩存結果
            result = func(*args, **kwargs)
            cache_manager.memory_cache.set(full_key, result, ttl=ttl)
            
            return result
        return wrapper
    return decorator


@cached_calculation("var_calculation", 600)  # 10 分鐘緩存
def calculate_var_with_cache(returns: pd.Series, confidence: float = 0.95) -> float:
    """計算 VaR（帶緩存）
    
    Args:
        returns (pd.Series): 收益率序列
        confidence (float): 信心水準
        
    Returns:
        float: VaR 值
    """
    # 模擬複雜的 VaR 計算
    import time
    time.sleep(0.1)  # 模擬計算時間
    
    return float(np.percentile(returns, (1 - confidence) * 100))


@cached_calculation("correlation_calculation", 1800)  # 30 分鐘緩存
def calculate_correlation_matrix_with_cache(price_data: pd.DataFrame) -> pd.DataFrame:
    """計算相關性矩陣（帶緩存）
    
    Args:
        price_data (pd.DataFrame): 價格數據
        
    Returns:
        pd.DataFrame: 相關性矩陣
    """
    # 模擬複雜的相關性計算
    import time
    time.sleep(0.2)  # 模擬計算時間
    
    returns = price_data.pct_change().dropna()
    return returns.corr()
