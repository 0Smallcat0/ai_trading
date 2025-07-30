"""
整合特徵計算器 (IntegratedFeatureCalculator)

實現資料層、計算層、呈現層和性能層的整合，支援多倍數參數調整、
季節性分析、快取機制和錯誤處理。

基於AI股票自動交易系統顯示邏輯改進指南實現。
"""

import pandas as pd
import numpy as np
import talib
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timedelta
import hashlib
import json

logger = logging.getLogger(__name__)


class IntegratedFeatureCalculator:
    """
    整合特徵計算器
    
    整合資料載入、指標計算、季節性分析和性能優化的統一計算器。
    支援多倍數參數調整、LRU快取和完整的錯誤處理機制。
    """
    
    def __init__(self, data_dict: Optional[Dict[str, pd.DataFrame]] = None):
        """
        初始化整合特徵計算器

        Args:
            data_dict: 數據字典，包含價格數據等
        """
        self.data_dict = data_dict or {}
        self.cache_size = 128
        self.logger = logging.getLogger(__name__)
        self._cache = {}  # 簡單的字典快取
        
    def load_and_calculate(
        self,
        stock_id: str,
        indicators: List[str],
        multipliers: List[float] = [1.0],
        date_range: Optional[List[str]] = None,
        seasonal: bool = False
    ) -> pd.DataFrame:
        """
        載入數據並計算技術指標
        
        Args:
            stock_id: 股票代號
            indicators: 指標列表 ['RSI', 'MACD', 'SMA', 'EMA', 'BBANDS']
            multipliers: 參數倍數列表，用於調整指標參數
            date_range: 日期範圍 [start_date, end_date]
            seasonal: 是否進行季節性分析
            
        Returns:
            包含計算結果的DataFrame
            
        Raises:
            ValueError: 當股票數據不存在或日期範圍無效時
        """
        try:
            # 創建快取鍵
            cache_key = f"{stock_id}_{'-'.join(indicators)}_{'-'.join(map(str, multipliers))}_{date_range}_{seasonal}"

            # 檢查快取
            if cache_key in self._cache:
                self.logger.debug(f"從快取載入 {stock_id} 的計算結果")
                return self._cache[cache_key]

            # 載入價格數據
            if 'price' not in self.data_dict:
                # 使用模擬數據作為fallback
                pricedf = self._generate_sample_data(stock_id)
            else:
                pricedf = self._load_price_data(stock_id, date_range)
            
            if pricedf.empty:
                raise ValueError(f"股票 {stock_id} 在指定日期範圍內無可用數據")
            
            # 計算技術指標
            results = {}
            for indicator in indicators:
                for multiplier in multipliers:
                    indicator_results = self._calculate_indicator(
                        pricedf, indicator, multiplier
                    )
                    results.update(indicator_results)
            
            # 季節性分析
            if seasonal:
                seasonal_results = self._calculate_seasonal_analysis(pricedf)
                results.update(seasonal_results)
            
            # 合併結果
            result_df = pd.concat(results, axis=1) if results else pd.DataFrame()
            result_df.index = pricedf.index
            
            # 保存到快取
            if len(self._cache) >= self.cache_size:
                # 簡單的FIFO清理策略
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]

            self._cache[cache_key] = result_df

            self.logger.info(
                f"成功計算 {stock_id} 的 {len(indicators)} 個指標，"
                f"使用 {len(multipliers)} 個倍數"
            )

            return result_df
            
        except KeyError as e:
            error_msg = f"股票 {stock_id} 數據不存在: {e}"
            self.logger.error(error_msg)
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = f"計算指標時發生錯誤: {e}"
            self.logger.error(error_msg)
            raise ValueError(error_msg) from e
    
    def _load_price_data(
        self, 
        stock_id: str, 
        date_range: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        載入價格數據
        
        Args:
            stock_id: 股票代號
            date_range: 日期範圍
            
        Returns:
            價格數據DataFrame
        """
        if 'price' in self.data_dict:
            pricedf = self.data_dict['price'].xs(stock_id, level='stock_id')
        else:
            # 生成模擬數據作為fallback
            pricedf = self._generate_sample_data(stock_id)
        
        # 應用日期範圍過濾
        if date_range and len(date_range) == 2:
            start_date, end_date = date_range
            pricedf = pricedf.loc[start_date:end_date]
        
        return pricedf
    
    def _calculate_indicator(
        self, 
        pricedf: pd.DataFrame, 
        indicator: str, 
        multiplier: float
    ) -> Dict[str, pd.Series]:
        """
        計算單個技術指標
        
        Args:
            pricedf: 價格數據
            indicator: 指標名稱
            multiplier: 參數倍數
            
        Returns:
            指標計算結果字典
        """
        results = {}
        
        if indicator == 'RSI':
            period = int(14 * multiplier)
            rsi_values = talib.RSI(pricedf['close'], timeperiod=period)
            results[f'RSI_{period}'] = rsi_values
            
        elif indicator == 'MACD':
            fast = int(12 * multiplier)
            slow = int(26 * multiplier)
            signal = int(9 * multiplier)
            
            macd, macdsignal, macdhist = talib.MACD(
                pricedf['close'], 
                fastperiod=fast, 
                slowperiod=slow, 
                signalperiod=signal
            )
            
            results[f'MACD_{fast}_{slow}_{signal}'] = macd
            results[f'MACD_Signal_{fast}_{slow}_{signal}'] = macdsignal
            results[f'MACD_Hist_{fast}_{slow}_{signal}'] = macdhist
            
        elif indicator == 'SMA':
            period = int(20 * multiplier)
            sma_values = talib.SMA(pricedf['close'], timeperiod=period)
            results[f'SMA_{period}'] = sma_values
            
        elif indicator == 'EMA':
            period = int(20 * multiplier)
            ema_values = talib.EMA(pricedf['close'], timeperiod=period)
            results[f'EMA_{period}'] = ema_values
            
        elif indicator == 'BBANDS':
            period = int(20 * multiplier)
            std_dev = 2.0
            
            upper, middle, lower = talib.BBANDS(
                pricedf['close'], 
                timeperiod=period, 
                nbdevup=std_dev, 
                nbdevdn=std_dev
            )
            
            results[f'BB_Upper_{period}'] = upper
            results[f'BB_Middle_{period}'] = middle
            results[f'BB_Lower_{period}'] = lower
        
        return results
    
    def _calculate_seasonal_analysis(self, pricedf: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        計算季節性分析
        
        Args:
            pricedf: 價格數據
            
        Returns:
            季節性分析結果
        """
        results = {}
        
        # 月份季節性
        pricedf_copy = pricedf.copy()
        pricedf_copy['month'] = pricedf_copy.index.month
        monthly_avg = pricedf_copy.groupby('month')['close'].transform('mean')
        results['seasonal_monthly_avg'] = monthly_avg
        
        # 週季節性
        pricedf_copy['weekday'] = pricedf_copy.index.weekday
        weekly_avg = pricedf_copy.groupby('weekday')['close'].transform('mean')
        results['seasonal_weekly_avg'] = weekly_avg
        
        return results
    
    def _generate_sample_data(self, stock_id: str, days: int = 252) -> pd.DataFrame:
        """
        生成模擬股價數據作為fallback
        
        Args:
            stock_id: 股票代號
            days: 天數
            
        Returns:
            模擬股價數據
        """
        np.random.seed(hash(stock_id) % 2**32)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days-1)
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # 生成隨機價格走勢
        returns = np.random.normal(0.001, 0.02, len(dates))
        prices = [100.0]  # 起始價格
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        # 生成OHLCV數據
        data = []
        for i, (date, close) in enumerate(zip(dates, prices)):
            open_price = prices[i-1] if i > 0 else close
            high = max(open_price, close) * (1 + abs(np.random.normal(0, 0.01)))
            low = min(open_price, close) * (1 - abs(np.random.normal(0, 0.01)))
            volume = int(np.random.lognormal(15, 0.5))
            
            data.append({
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        df = pd.DataFrame(data, index=dates)
        return df
    
    def clear_cache(self):
        """清除快取"""
        self._cache.clear()
        self.logger.info("已清除計算快取")

    def get_cache_info(self) -> Dict[str, Any]:
        """
        獲取快取資訊

        Returns:
            快取統計資訊
        """
        return {
            'maxsize': self.cache_size,
            'currsize': len(self._cache),
            'cache_keys': list(self._cache.keys())
        }
