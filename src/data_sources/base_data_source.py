"""
基礎資料來源模組

此模組定義了資料來源的基礎類別和配置，
為所有資料來源適配器提供統一的介面。

主要功能：
- 定義資料來源基礎類別
- 提供統一的配置管理
- 實現通用的錯誤處理
- 支援快取和重試機制
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

import pandas as pd

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class DataSourceConfig:
    """資料來源配置類別

    Attributes:
        name: 資料來源名稱
        cache_dir: 快取目錄
        cache_ttl: 快取存活時間（秒）
        api_limits: API 限制配置
        retry_config: 重試配置
        credentials: API 認證資訊
    """
    name: str
    cache_dir: str = "cache"
    cache_ttl: int = 3600
    api_limits: Dict[str, Any] = None
    retry_config: Dict[str, Any] = None
    credentials: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """初始化後處理"""
        if self.api_limits is None:
            self.api_limits = {"min_interval": 1.0}
        if self.retry_config is None:
            self.retry_config = {"max_retries": 3, "backoff_factor": 1.0}
        if self.credentials is None:
            self.credentials = {}


class BaseDataSource(ABC):
    """資料來源基礎類別
    
    所有資料來源適配器都應該繼承此類別，
    並實現必要的抽象方法。
    """
    
    def __init__(self, config: DataSourceConfig):
        """初始化資料來源
        
        Args:
            config: 資料來源配置
        """
        self.config = config
        self.name = config.name
        self.is_available = False
        self.last_request_time = 0
        self._initialize()
    
    def _initialize(self):
        """初始化資料來源"""
        try:
            self._setup_connection()
            self.is_available = True
            logger.info(f"資料來源 {self.name} 初始化成功")
        except Exception as e:
            logger.error(f"資料來源 {self.name} 初始化失敗: {e}")
            self.is_available = False
    
    @abstractmethod
    def _setup_connection(self):
        """設定連接（子類別必須實現）"""
        pass
    
    @abstractmethod
    def get_historical_data(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str, 
        **kwargs
    ) -> pd.DataFrame:
        """獲取歷史資料（子類別必須實現）
        
        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期
            **kwargs: 其他參數
            
        Returns:
            pd.DataFrame: 歷史資料
        """
        pass
    
    def test_connection(self) -> bool:
        """測試連接
        
        Returns:
            bool: 連接是否正常
        """
        try:
            # 嘗試獲取測試資料
            test_data = self.get_historical_data(
                "AAPL", 
                "2024-01-01", 
                "2024-01-02"
            )
            return not test_data.empty
        except Exception as e:
            logger.debug(f"資料來源 {self.name} 連接測試失敗: {e}")
            return False
    
    def _check_rate_limit(self):
        """檢查速率限制"""
        min_interval = self.config.api_limits.get("min_interval", 1.0)
        current_time = time.time()
        
        if current_time - self.last_request_time < min_interval:
            sleep_time = min_interval - (current_time - self.last_request_time)
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _retry_request(self, func, *args, **kwargs):
        """重試請求
        
        Args:
            func: 要重試的函數
            *args: 位置參數
            **kwargs: 關鍵字參數
            
        Returns:
            函數執行結果
        """
        max_retries = self.config.retry_config.get("max_retries", 3)
        backoff_factor = self.config.retry_config.get("backoff_factor", 1.0)
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                
                sleep_time = backoff_factor * (2 ** attempt)
                logger.warning(
                    f"資料來源 {self.name} 請求失敗 (嘗試 {attempt + 1}/{max_retries}): {e}"
                )
                time.sleep(sleep_time)
    
    def get_status(self) -> Dict[str, Any]:
        """獲取資料來源狀態
        
        Returns:
            Dict[str, Any]: 狀態資訊
        """
        return {
            "name": self.name,
            "is_available": self.is_available,
            "last_request_time": self.last_request_time,
            "config": {
                "cache_dir": self.config.cache_dir,
                "cache_ttl": self.config.cache_ttl,
                "api_limits": self.config.api_limits
            }
        }


class MockDataSource(BaseDataSource):
    """模擬資料來源（用於測試）"""
    
    def _setup_connection(self):
        """設定連接"""
        # 模擬連接設定
        pass
    
    def get_historical_data(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str, 
        **kwargs
    ) -> pd.DataFrame:
        """獲取模擬歷史資料
        
        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期
            **kwargs: 其他參數
            
        Returns:
            pd.DataFrame: 模擬歷史資料
        """
        # 檢查速率限制
        self._check_rate_limit()
        
        # 生成模擬資料
        import numpy as np
        from datetime import datetime, timedelta
        
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        dates = pd.date_range(start, end, freq='D')
        n_days = len(dates)
        
        # 生成模擬價格資料
        np.random.seed(hash(symbol) % 2**32)
        base_price = 100
        returns = np.random.normal(0, 0.02, n_days)
        prices = base_price * np.exp(np.cumsum(returns))
        
        data = pd.DataFrame({
            'date': dates,
            'symbol': symbol,
            'open': prices * (1 + np.random.normal(0, 0.01, n_days)),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.02, n_days))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.02, n_days))),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, n_days),
            'data_source': self.name
        })
        
        return data


# 向後相容性別名
DataSource = BaseDataSource
