# -*- coding: utf-8 -*-
"""Tushare Pro 數據源適配器

此模組整合 Tushare Pro API 到現有的數據源架構中，
提供統一的數據接口和格式標準化。

主要功能：
- Tushare Pro API 封裝和適配
- 積分管理和 API 限制處理
- 數據格式標準化
- 錯誤處理和重試機制
- 數據質量檢查
- 緩存和性能優化

支援的數據類型：
- 股票日線數據
- 實時行情數據
- 財務報表數據
- 基本面數據
- 宏觀經濟數據

Example:
    >>> from src.data_sources.base_data_source import DataSourceConfig
    >>> config = DataSourceConfig(
    ...     name="tushare",
    ...     credentials={'token': 'your_token_here'},
    ...     api_limits={'daily_calls': 10000}
    ... )
    >>> adapter = TushareAdapter(config)
    >>> df = await adapter.get_daily_data('000001.SZ', '20230101', '20231231')
"""

import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import pandas as pd
import numpy as np

from .base_data_source import BaseDataSource, DataSourceConfig
from ..utils.data_validator import DataValidator
from ..utils.cache_manager import CacheManager

# 設定日誌
logger = logging.getLogger(__name__)


class TusharePointsManager:
    """Tushare 積分管理器
    
    管理 Tushare Pro API 的積分使用和限制。
    
    Attributes:
        daily_limit (int): 每日積分限制
        used_points (int): 已使用積分
        reset_time (datetime): 積分重置時間
    """
    
    def __init__(self, daily_limit: int = 10000):
        """初始化積分管理器
        
        Args:
            daily_limit: 每日積分限制
        """
        self.daily_limit = daily_limit
        self.used_points = 0
        self.reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.last_request_time = 0
        self.min_interval = 0.1  # 最小請求間隔（秒）
        
        logger.info(f"Tushare積分管理器初始化，每日限制: {daily_limit}")
    
    def can_make_request(self, points_needed: int = 1) -> bool:
        """檢查是否可以發起請求
        
        Args:
            points_needed: 需要的積分數
            
        Returns:
            是否可以發起請求
        """
        # 檢查是否需要重置每日使用量
        if datetime.now() >= self.reset_time + timedelta(days=1):
            self._reset_daily_usage()
        
        # 檢查積分限制
        if self.used_points + points_needed > self.daily_limit:
            logger.warning(f"積分不足，已使用: {self.used_points}, 需要: {points_needed}, 限制: {self.daily_limit}")
            return False
        
        # 檢查請求頻率限制
        current_time = time.time()
        if current_time - self.last_request_time < self.min_interval:
            time.sleep(self.min_interval - (current_time - self.last_request_time))
        
        return True
    
    def use_points(self, points: int = 1):
        """使用積分
        
        Args:
            points: 使用的積分數
        """
        self.used_points += points
        self.last_request_time = time.time()
        logger.debug(f"使用積分: {points}, 總計: {self.used_points}/{self.daily_limit}")
    
    def _reset_daily_usage(self):
        """重置每日使用量"""
        self.used_points = 0
        self.reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        logger.info("每日積分使用量已重置")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """獲取使用統計
        
        Returns:
            使用統計信息
        """
        return {
            'used_points': self.used_points,
            'daily_limit': self.daily_limit,
            'remaining_points': self.daily_limit - self.used_points,
            'usage_percentage': (self.used_points / self.daily_limit) * 100,
            'reset_time': self.reset_time.strftime('%Y-%m-%d %H:%M:%S')
        }


class TushareAdapter(BaseDataSource):
    """Tushare Pro 數據源適配器
    
    提供 Tushare Pro API 的統一接口，包括積分管理、
    數據格式標準化、錯誤處理等功能。
    
    Attributes:
        token (str): Tushare Pro API token
        pro: Tushare Pro API 實例
        points_manager: 積分管理器
        
    Example:
        >>> config = DataSourceConfig(
        ...     name="tushare",
        ...     credentials={'token': 'your_token'},
        ...     api_limits={'daily_calls': 10000}
        ... )
        >>> adapter = TushareAdapter(config)
        >>> data = await adapter.get_daily_data('000001.SZ', '20230101', '20231231')
    """
    
    def __init__(self, config: DataSourceConfig):
        """初始化 Tushare 適配器
        
        Args:
            config: 數據源配置
            
        Raises:
            ImportError: 當 tushare 模組未安裝時
            ValueError: 當配置參數無效時
        """
        super().__init__(config)
        
        # 獲取配置參數
        self.token = config.credentials.get('token')
        if not self.token:
            logger.warning("Tushare token 未配置，部分功能可能不可用")
        
        # 初始化 Tushare Pro API
        self.pro = None
        self._initialize_api()
        
        # 初始化積分管理器
        daily_limit = config.api_limits.get('daily_calls', 10000)
        self.points_manager = TusharePointsManager(daily_limit)
        
        # 數據格式映射
        self.column_mapping = {
            'ts_code': 'symbol',
            'trade_date': 'date',
            'open': 'open',
            'high': 'high', 
            'low': 'low',
            'close': 'close',
            'vol': 'volume',
            'amount': 'amount',
            'pct_chg': 'pct_change',
            'pre_close': 'pre_close'
        }
        
        logger.info(f"Tushare適配器初始化完成，可用性: {self.is_available()}")
    
    def _initialize_api(self):
        """初始化 Tushare Pro API"""
        try:
            import tushare as ts
            
            if self.token:
                ts.set_token(self.token)
                self.pro = ts.pro_api()
                logger.info("Tushare Pro API 初始化成功")
            else:
                logger.warning("Tushare token 未提供，無法初始化 Pro API")
                
        except ImportError as e:
            logger.error(f"Tushare 模組導入失敗: {e}")
            raise ImportError("請安裝 tushare: pip install tushare") from e
        except Exception as e:
            logger.error(f"Tushare API 初始化失敗: {e}")
            raise
    
    def is_available(self) -> bool:
        """檢查數據源是否可用
        
        Returns:
            數據源是否可用
        """
        return self.pro is not None and self.token is not None
    
    async def connect(self) -> bool:
        """連接到數據源
        
        Returns:
            連接是否成功
        """
        if not self.is_available():
            return False
        
        try:
            # 測試 API 連接
            test_df = self.pro.trade_cal(exchange='SSE', start_date='20230101', end_date='20230102')
            return len(test_df) > 0
        except Exception as e:
            logger.error(f"Tushare 連接測試失敗: {e}")
            return False
    
    async def get_daily_data(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str,
        **kwargs
    ) -> pd.DataFrame:
        """獲取日線數據
        
        Args:
            symbol: 股票代碼 (如 '000001.SZ')
            start_date: 開始日期 (格式: 'YYYYMMDD')
            end_date: 結束日期 (格式: 'YYYYMMDD')
            **kwargs: 其他參數
            
        Returns:
            標準化的日線數據
            
        Raises:
            ValueError: 當參數無效時
            RuntimeError: 當 API 調用失敗時
        """
        if not self.is_available():
            raise RuntimeError("Tushare 數據源不可用")
        
        # 檢查積分限制
        if not self.points_manager.can_make_request(1):
            raise RuntimeError("Tushare 積分不足或請求過於頻繁")
        
        try:
            # 調用 Tushare API
            df = self.pro.daily(
                ts_code=symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            # 記錄積分使用
            self.points_manager.use_points(1)
            
            # 數據格式標準化
            standardized_df = self._standardize_data_format(df)
            
            # 數據質量檢查
            quality_score = self._check_data_quality(standardized_df)
            logger.debug(f"數據質量評分: {quality_score:.2f}")
            
            logger.info(f"成功獲取 {symbol} 日線數據，共 {len(standardized_df)} 條記錄")
            return standardized_df
            
        except Exception as e:
            logger.error(f"獲取日線數據失敗 {symbol}: {e}")
            raise RuntimeError(f"獲取日線數據失敗: {e}") from e
    
    async def get_realtime_data(self, symbols: List[str]) -> pd.DataFrame:
        """獲取實時數據
        
        Args:
            symbols: 股票代碼列表
            
        Returns:
            實時數據
        """
        if not self.is_available():
            raise RuntimeError("Tushare 數據源不可用")
        
        # 檢查積分限制
        points_needed = len(symbols)
        if not self.points_manager.can_make_request(points_needed):
            raise RuntimeError("Tushare 積分不足")
        
        try:
            # 獲取實時數據
            df_list = []
            for symbol in symbols:
                df = self.pro.realtime_quote(ts_code=symbol)
                if not df.empty:
                    df_list.append(df)
            
            if df_list:
                combined_df = pd.concat(df_list, ignore_index=True)
                self.points_manager.use_points(points_needed)
                return self._standardize_data_format(combined_df)
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"獲取實時數據失敗: {e}")
            raise RuntimeError(f"獲取實時數據失敗: {e}") from e
    
    def _standardize_data_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """標準化數據格式
        
        Args:
            df: 原始數據
            
        Returns:
            標準化後的數據
        """
        if df.empty:
            return df
        
        # 重命名欄位
        standardized_df = df.rename(columns=self.column_mapping)
        
        # 數據類型轉換
        if 'date' in standardized_df.columns:
            standardized_df['date'] = pd.to_datetime(standardized_df['date'], format='%Y%m%d')
        
        # 數值欄位轉換
        numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'amount', 'pct_change']
        for col in numeric_columns:
            if col in standardized_df.columns:
                standardized_df[col] = pd.to_numeric(standardized_df[col], errors='coerce')
        
        # 排序
        if 'date' in standardized_df.columns:
            standardized_df = standardized_df.sort_values('date')
        
        return standardized_df
    
    def _check_data_quality(self, df: pd.DataFrame) -> float:
        """檢查數據質量
        
        Args:
            df: 數據框架
            
        Returns:
            質量評分 (0-1)
        """
        if df.empty:
            return 0.0
        
        quality_score = 1.0
        
        # 檢查缺失值
        missing_ratio = df.isnull().sum().sum() / (df.shape[0] * df.shape[1])
        quality_score -= missing_ratio * 0.3
        
        # 檢查價格邏輯
        if all(col in df.columns for col in ['high', 'low', 'open', 'close']):
            invalid_price = ((df['high'] < df['low']) | 
                           (df['open'] > df['high']) | (df['open'] < df['low']) |
                           (df['close'] > df['high']) | (df['close'] < df['low'])).sum()
            quality_score -= (invalid_price / len(df)) * 0.4
        
        # 檢查數據連續性
        if 'date' in df.columns and len(df) > 1:
            date_gaps = (df['date'].diff().dt.days > 7).sum()  # 超過7天的間隔
            quality_score -= (date_gaps / len(df)) * 0.3
        
        return max(0.0, quality_score)
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """獲取使用統計
        
        Returns:
            使用統計信息
        """
        stats = self.points_manager.get_usage_stats()
        stats.update({
            'adapter_name': self.name,
            'is_available': self.is_available(),
            'token_configured': bool(self.token)
        })
        return stats
