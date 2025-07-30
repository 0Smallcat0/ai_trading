"""整合特徵計算器模組 (Integrated Feature Calculator Module)

此模組實現資料層、計算層、呈現層和性能層的整合，
提供統一的技術指標計算和數據處理接口。

主要功能：
- 多倍數指標計算（RSI、MACD等）
- 季節性分析
- 錯誤處理和數據驗證
- 性能優化（LRU快取）
- 數據驅動的邏輯處理

作者: AI Trading System
版本: v1.0
日期: 2025-07-29
"""

import logging
import warnings
from functools import lru_cache
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# 嘗試導入 TA-Lib
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError as e:
    warnings.warn(f"無法匯入 TA-Lib，將使用內建計算方法: {e}")
    TALIB_AVAILABLE = False

logger = logging.getLogger(__name__)


class DataValidationError(Exception):
    """數據驗證錯誤"""
    pass


class IntegratedFeatureCalculator:
    """整合特徵計算器
    
    整合資料載入、指標計算、錯誤處理和性能優化的統一接口。
    支持多倍數參數、季節性分析和快取機制。
    
    Attributes:
        data_dict (Dict): 數據字典，包含價格數據等
        cache_size (int): LRU快取大小
        
    Example:
        >>> data_dict = {'price': price_dataframe}
        >>> calculator = IntegratedFeatureCalculator(data_dict)
        >>> indicators = calculator.load_and_calculate(
        ...     '2330.TW', ['RSI', 'MACD'], multipliers=[0.5, 1, 2]
        ... )
    """
    
    def __init__(self, data_dict: Dict[str, pd.DataFrame], cache_size: int = 128):
        """初始化整合特徵計算器
        
        Args:
            data_dict: 數據字典，必須包含 'price' 鍵
            cache_size: LRU快取大小，預設128
            
        Raises:
            ValueError: 當數據字典格式不正確時
        """
        if not isinstance(data_dict, dict):
            raise ValueError("data_dict 必須是字典類型")
        
        if 'price' not in data_dict:
            raise ValueError("data_dict 必須包含 'price' 鍵")
            
        self.data_dict = data_dict
        self.cache_size = cache_size
        
        # 驗證價格數據格式
        self._validate_price_data_format()
        
        logger.info("整合特徵計算器初始化完成，快取大小: %d", cache_size)
    
    def _validate_price_data_format(self) -> None:
        """驗證價格數據格式"""
        price_data = self.data_dict['price']
        
        if not isinstance(price_data, pd.DataFrame):
            raise ValueError("價格數據必須是 pandas DataFrame")
        
        # 檢查必要的欄位
        required_columns = ['close']
        missing_columns = [col for col in required_columns if col not in price_data.columns]
        
        if missing_columns:
            # 嘗試中文欄位名稱
            chinese_mapping = {
                'close': '收盤價',
                'open': '開盤價', 
                'high': '最高價',
                'low': '最低價',
                'volume': '成交股數'
            }
            
            for eng_col, chi_col in chinese_mapping.items():
                if eng_col in missing_columns and chi_col in price_data.columns:
                    # 創建英文欄位映射
                    price_data[eng_col] = price_data[chi_col]
                    missing_columns.remove(eng_col)
        
        if missing_columns:
            raise ValueError(f"價格數據缺少必要欄位: {missing_columns}")
    
    @lru_cache(maxsize=128)
    def load_and_calculate(
        self, 
        stock_id: str, 
        indicators: List[str], 
        multipliers: List[float] = None,
        date_range: Optional[Tuple[str, str]] = None,
        seasonal: bool = False
    ) -> pd.DataFrame:
        """載入數據並計算指標（帶快取）
        
        Args:
            stock_id: 股票代碼
            indicators: 指標列表，支持 ['RSI', 'MACD', 'SMA', 'EMA', 'BBANDS']
            multipliers: 參數倍數列表，預設 [1]
            date_range: 日期範圍 (start_date, end_date)，格式 'YYYY-MM-DD'
            seasonal: 是否進行季節性分析
            
        Returns:
            pd.DataFrame: 包含所有計算指標的數據框架
            
        Raises:
            ValueError: 當股票數據不存在或日期範圍無效時
            DataValidationError: 當輸入參數格式不正確時
        """
        try:
            # 參數驗證和預設值設定
            if multipliers is None:
                multipliers = [1.0]
            
            # 轉換為元組以支持快取
            if isinstance(indicators, list):
                indicators = tuple(indicators)
            if isinstance(multipliers, list):
                multipliers = tuple(multipliers)
            
            # 載入價格數據
            pricedf = self._load_stock_data(stock_id, date_range)
            
            # 計算指標
            results = {}
            
            for indicator in indicators:
                for multiplier in multipliers:
                    indicator_results = self._calculate_indicator(
                        pricedf, indicator, multiplier
                    )
                    results.update(indicator_results)
            
            # 季節性分析
            if seasonal:
                seasonal_results = self._calculate_seasonal_features(pricedf)
                results.update(seasonal_results)
            
            # 合併結果
            result_df = pd.concat(results, axis=1) if results else pd.DataFrame()
            
            logger.info(
                "成功計算 %s 的 %d 個指標，數據點: %d", 
                stock_id, len(results), len(result_df)
            )
            
            return result_df
            
        except KeyError as e:
            error_msg = f"股票 {stock_id} 數據不存在: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = f"計算指標時發生錯誤: {e}"
            logger.error(error_msg, exc_info=True)
            raise DataValidationError(error_msg) from e
    
    def _load_stock_data(
        self, 
        stock_id: str, 
        date_range: Optional[Tuple[str, str]]
    ) -> pd.DataFrame:
        """載入股票數據
        
        Args:
            stock_id: 股票代碼
            date_range: 日期範圍
            
        Returns:
            pd.DataFrame: 過濾後的價格數據
            
        Raises:
            ValueError: 當股票數據不存在或日期範圍無效時
        """
        price_data = self.data_dict['price']
        
        # 檢查是否為多層索引（stock_id, date）
        if isinstance(price_data.index, pd.MultiIndex):
            if stock_id not in price_data.index.get_level_values(0):
                raise ValueError(f"股票 {stock_id} 數據不存在")
            pricedf = price_data.xs(stock_id, level=0)
        else:
            # 假設單一股票數據
            pricedf = price_data.copy()
        
        # 日期範圍過濾
        if date_range:
            start_date, end_date = date_range
            try:
                pricedf = pricedf.loc[start_date:end_date]
                if pricedf.empty:
                    raise ValueError(
                        f"日期範圍 {start_date} 到 {end_date} 無可用數據，請擴大範圍"
                    )
            except (KeyError, TypeError) as e:
                raise ValueError(f"無效的日期範圍: {date_range}") from e
        
        return pricedf
    
    def _calculate_indicator(
        self, 
        pricedf: pd.DataFrame, 
        indicator: str, 
        multiplier: float
    ) -> Dict[str, pd.Series]:
        """計算單一指標
        
        Args:
            pricedf: 價格數據
            indicator: 指標名稱
            multiplier: 參數倍數
            
        Returns:
            Dict[str, pd.Series]: 指標結果字典
        """
        results = {}
        
        if indicator == 'RSI':
            period = int(14 * multiplier)
            rsi_values = self._calculate_rsi(pricedf['close'], period)
            results[f'RSI_{period}'] = rsi_values
            
        elif indicator == 'MACD':
            fast = int(12 * multiplier)
            slow = int(26 * multiplier) 
            signal = int(9 * multiplier)
            macd_results = self._calculate_macd(pricedf['close'], fast, slow, signal)
            
            results[f'MACD_{fast}_{slow}_{signal}'] = pd.DataFrame({
                'MACD': macd_results[0],
                'Signal': macd_results[1], 
                'Hist': macd_results[2]
            }, index=pricedf.index)
            
        elif indicator == 'SMA':
            period = int(20 * multiplier)
            sma_values = self._calculate_sma(pricedf['close'], period)
            results[f'SMA_{period}'] = sma_values
            
        elif indicator == 'EMA':
            period = int(20 * multiplier)
            ema_values = self._calculate_ema(pricedf['close'], period)
            results[f'EMA_{period}'] = ema_values
            
        elif indicator == 'BBANDS':
            period = int(20 * multiplier)
            bb_results = self._calculate_bollinger_bands(pricedf['close'], period)
            results[f'BBANDS_{period}'] = pd.DataFrame({
                'Upper': bb_results[0],
                'Middle': bb_results[1],
                'Lower': bb_results[2]
            }, index=pricedf.index)
            
        else:
            logger.warning("不支援的指標: %s", indicator)
        
        return results
    
    def _calculate_seasonal_features(self, pricedf: pd.DataFrame) -> Dict[str, pd.Series]:
        """計算季節性特徵
        
        Args:
            pricedf: 價格數據
            
        Returns:
            Dict[str, pd.Series]: 季節性特徵字典
        """
        results = {}
        
        # 確保索引是日期時間類型
        if not isinstance(pricedf.index, pd.DatetimeIndex):
            try:
                pricedf.index = pd.to_datetime(pricedf.index)
            except Exception as e:
                logger.warning("無法轉換索引為日期時間格式: %s", e)
                return results
        
        # 月份平均
        pricedf_copy = pricedf.copy()
        pricedf_copy['month'] = pricedf_copy.index.month
        monthly_avg = pricedf_copy.groupby('month')['close'].transform('mean')
        results['seasonal_monthly_avg'] = monthly_avg
        
        # 季度平均
        pricedf_copy['quarter'] = pricedf_copy.index.quarter
        quarterly_avg = pricedf_copy.groupby('quarter')['close'].transform('mean')
        results['seasonal_quarterly_avg'] = quarterly_avg
        
        # 星期效應
        pricedf_copy['weekday'] = pricedf_copy.index.weekday
        weekday_avg = pricedf_copy.groupby('weekday')['close'].transform('mean')
        results['seasonal_weekday_avg'] = weekday_avg
        
        return results
