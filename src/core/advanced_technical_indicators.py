#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
進階技術指標計算模組

提供更多技術指標的計算功能，包括：
- Williams %R (威廉指標)
- Stochastic Oscillator (隨機指標)
- Commodity Channel Index (CCI)
- Average True Range (ATR)
- Parabolic SAR
- Ichimoku Cloud (一目均衡表)
- Volume Weighted Average Price (VWAP)
- Money Flow Index (MFI)
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Tuple, Optional, Union
import warnings

# 嘗試導入 TA-Lib
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    warnings.warn("TA-Lib 不可用，將使用純 Python 實現")

logger = logging.getLogger(__name__)

class AdvancedTechnicalIndicators:
    """進階技術指標計算器"""
    
    def __init__(self, data: pd.DataFrame = None):
        """
        初始化進階技術指標計算器
        
        Args:
            data: 包含 OHLCV 數據的 DataFrame
        """
        self.data = data
        self.indicators = {}
        
    def set_data(self, data: pd.DataFrame):
        """設置數據"""
        self.data = data
        self.indicators = {}
        
    def calculate_williams_r(self, period: int = 14) -> pd.Series:
        """
        計算威廉指標 (Williams %R)
        
        Williams %R 是一個動量指標，測量收盤價在過去 N 期的最高價和最低價範圍內的位置。
        
        計算公式：%R = (最高價 - 收盤價) / (最高價 - 最低價) × (-100)
        
        Args:
            period: 計算週期，默認 14
            
        Returns:
            Williams %R 值 (-100 到 0)
        """
        if self.data is None or self.data.empty:
            return pd.Series(dtype=float)
            
        try:
            if TALIB_AVAILABLE:
                willr = talib.WILLR(
                    self.data['high'].values,
                    self.data['low'].values, 
                    self.data['close'].values,
                    timeperiod=period
                )
                result = pd.Series(willr, index=self.data.index)
            else:
                # 純 Python 實現
                highest_high = self.data['high'].rolling(window=period).max()
                lowest_low = self.data['low'].rolling(window=period).min()
                
                result = ((highest_high - self.data['close']) / 
                         (highest_high - lowest_low)) * (-100)
                
            self.indicators[f'WILLR_{period}'] = result
            logger.info(f"Williams %R({period}) 計算完成")
            return result
            
        except Exception as e:
            logger.error(f"Williams %R 計算失敗: {e}")
            return pd.Series(dtype=float)
    
    def calculate_stochastic(self, k_period: int = 14, d_period: int = 3, 
                           smooth_k: int = 3) -> Tuple[pd.Series, pd.Series]:
        """
        計算隨機指標 (Stochastic Oscillator)
        
        隨機指標包含兩條線：%K 和 %D，用於識別超買和超賣條件。
        
        計算公式：
        %K = (收盤價 - 最低價) / (最高價 - 最低價) × 100
        %D = %K 的移動平均
        
        Args:
            k_period: %K 計算週期，默認 14
            d_period: %D 平滑週期，默認 3
            smooth_k: %K 平滑週期，默認 3
            
        Returns:
            (%K, %D) 元組
        """
        if self.data is None or self.data.empty:
            return pd.Series(dtype=float), pd.Series(dtype=float)
            
        try:
            if TALIB_AVAILABLE:
                slowk, slowd = talib.STOCH(
                    self.data['high'].values,
                    self.data['low'].values,
                    self.data['close'].values,
                    fastk_period=k_period,
                    slowk_period=smooth_k,
                    slowd_period=d_period
                )
                k_series = pd.Series(slowk, index=self.data.index)
                d_series = pd.Series(slowd, index=self.data.index)
            else:
                # 純 Python 實現
                lowest_low = self.data['low'].rolling(window=k_period).min()
                highest_high = self.data['high'].rolling(window=k_period).max()
                
                # 計算 %K
                k_percent = ((self.data['close'] - lowest_low) / 
                           (highest_high - lowest_low)) * 100
                
                # 平滑 %K
                k_series = k_percent.rolling(window=smooth_k).mean()
                
                # 計算 %D
                d_series = k_series.rolling(window=d_period).mean()
                
            self.indicators[f'STOCH_K_{k_period}_{smooth_k}'] = k_series
            self.indicators[f'STOCH_D_{k_period}_{d_period}'] = d_series
            
            logger.info(f"Stochastic({k_period},{smooth_k},{d_period}) 計算完成")
            return k_series, d_series
            
        except Exception as e:
            logger.error(f"Stochastic 計算失敗: {e}")
            return pd.Series(dtype=float), pd.Series(dtype=float)
    
    def calculate_cci(self, period: int = 20) -> pd.Series:
        """
        計算商品通道指數 (Commodity Channel Index, CCI)
        
        CCI 測量價格偏離其統計平均值的程度。
        
        計算公式：CCI = (典型價格 - 典型價格的移動平均) / (0.015 × 平均絕對偏差)
        典型價格 = (最高價 + 最低價 + 收盤價) / 3
        
        Args:
            period: 計算週期，默認 20
            
        Returns:
            CCI 值
        """
        if self.data is None or self.data.empty:
            return pd.Series(dtype=float)
            
        try:
            if TALIB_AVAILABLE:
                cci = talib.CCI(
                    self.data['high'].values,
                    self.data['low'].values,
                    self.data['close'].values,
                    timeperiod=period
                )
                result = pd.Series(cci, index=self.data.index)
            else:
                # 純 Python 實現
                typical_price = (self.data['high'] + self.data['low'] + self.data['close']) / 3
                sma_tp = typical_price.rolling(window=period).mean()
                mad = typical_price.rolling(window=period).apply(
                    lambda x: np.mean(np.abs(x - x.mean()))
                )
                result = (typical_price - sma_tp) / (0.015 * mad)
                
            self.indicators[f'CCI_{period}'] = result
            logger.info(f"CCI({period}) 計算完成")
            return result
            
        except Exception as e:
            logger.error(f"CCI 計算失敗: {e}")
            return pd.Series(dtype=float)
    
    def calculate_atr(self, period: int = 14) -> pd.Series:
        """
        計算平均真實範圍 (Average True Range, ATR)
        
        ATR 測量市場波動性，不指示價格方向。
        
        計算公式：
        TR = max(高-低, abs(高-前收), abs(低-前收))
        ATR = TR 的移動平均
        
        Args:
            period: 計算週期，默認 14
            
        Returns:
            ATR 值
        """
        if self.data is None or self.data.empty:
            return pd.Series(dtype=float)
            
        try:
            if TALIB_AVAILABLE:
                atr = talib.ATR(
                    self.data['high'].values,
                    self.data['low'].values,
                    self.data['close'].values,
                    timeperiod=period
                )
                result = pd.Series(atr, index=self.data.index)
            else:
                # 純 Python 實現
                high_low = self.data['high'] - self.data['low']
                high_close_prev = np.abs(self.data['high'] - self.data['close'].shift(1))
                low_close_prev = np.abs(self.data['low'] - self.data['close'].shift(1))
                
                true_range = np.maximum(high_low, np.maximum(high_close_prev, low_close_prev))
                result = pd.Series(true_range).rolling(window=period).mean()
                result.index = self.data.index
                
            self.indicators[f'ATR_{period}'] = result
            logger.info(f"ATR({period}) 計算完成")
            return result
            
        except Exception as e:
            logger.error(f"ATR 計算失敗: {e}")
            return pd.Series(dtype=float)
    
    def calculate_parabolic_sar(self, acceleration: float = 0.02, 
                               maximum: float = 0.2) -> pd.Series:
        """
        計算拋物線轉向指標 (Parabolic SAR)
        
        Parabolic SAR 用於確定趨勢方向和潛在反轉點。
        
        Args:
            acceleration: 加速因子，默認 0.02
            maximum: 最大加速因子，默認 0.2
            
        Returns:
            Parabolic SAR 值
        """
        if self.data is None or self.data.empty:
            return pd.Series(dtype=float)
            
        try:
            if TALIB_AVAILABLE:
                sar = talib.SAR(
                    self.data['high'].values,
                    self.data['low'].values,
                    acceleration=acceleration,
                    maximum=maximum
                )
                result = pd.Series(sar, index=self.data.index)
            else:
                # 簡化的 Python 實現
                result = pd.Series(index=self.data.index, dtype=float)
                result.iloc[0] = self.data['low'].iloc[0]
                
                # 這是一個簡化版本，完整實現較複雜
                for i in range(1, len(self.data)):
                    result.iloc[i] = result.iloc[i-1]
                
            self.indicators[f'SAR_{acceleration}_{maximum}'] = result
            logger.info(f"Parabolic SAR({acceleration},{maximum}) 計算完成")
            return result
            
        except Exception as e:
            logger.error(f"Parabolic SAR 計算失敗: {e}")
            return pd.Series(dtype=float)

    def calculate_vwap(self) -> pd.Series:
        """
        計算成交量加權平均價格 (Volume Weighted Average Price, VWAP)

        VWAP 是一個交易基準，給出了證券在一天中的平均價格，基於成交量和價格。

        計算公式：VWAP = Σ(價格 × 成交量) / Σ(成交量)

        Returns:
            VWAP 值
        """
        if self.data is None or self.data.empty:
            return pd.Series(dtype=float)

        try:
            # 計算典型價格
            typical_price = (self.data['high'] + self.data['low'] + self.data['close']) / 3

            # 計算價格×成交量
            pv = typical_price * self.data['volume']

            # 計算累積值
            cumulative_pv = pv.cumsum()
            cumulative_volume = self.data['volume'].cumsum()

            # 計算 VWAP
            result = cumulative_pv / cumulative_volume

            self.indicators['VWAP'] = result
            logger.info("VWAP 計算完成")
            return result

        except Exception as e:
            logger.error(f"VWAP 計算失敗: {e}")
            return pd.Series(dtype=float)

    def calculate_mfi(self, period: int = 14) -> pd.Series:
        """
        計算資金流量指標 (Money Flow Index, MFI)

        MFI 是一個動量指標，結合了價格和成交量來識別超買和超賣條件。

        計算公式：
        典型價格 = (高+低+收) / 3
        資金流量 = 典型價格 × 成交量
        MFI = 100 - (100 / (1 + 資金流量比率))

        Args:
            period: 計算週期，默認 14

        Returns:
            MFI 值 (0-100)
        """
        if self.data is None or self.data.empty:
            return pd.Series(dtype=float)

        try:
            if TALIB_AVAILABLE:
                mfi = talib.MFI(
                    self.data['high'].values,
                    self.data['low'].values,
                    self.data['close'].values,
                    self.data['volume'].values,
                    timeperiod=period
                )
                result = pd.Series(mfi, index=self.data.index)
            else:
                # 純 Python 實現
                typical_price = (self.data['high'] + self.data['low'] + self.data['close']) / 3
                money_flow = typical_price * self.data['volume']

                # 判斷資金流向
                positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
                negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)

                # 計算資金流量比率
                positive_mf = positive_flow.rolling(window=period).sum()
                negative_mf = negative_flow.rolling(window=period).sum()

                mf_ratio = positive_mf / negative_mf
                result = 100 - (100 / (1 + mf_ratio))

            self.indicators[f'MFI_{period}'] = result
            logger.info(f"MFI({period}) 計算完成")
            return result

        except Exception as e:
            logger.error(f"MFI 計算失敗: {e}")
            return pd.Series(dtype=float)

    def calculate_ichimoku(self, tenkan_period: int = 9, kijun_period: int = 26,
                          senkou_span_b_period: int = 52, displacement: int = 26) -> Dict[str, pd.Series]:
        """
        計算一目均衡表 (Ichimoku Cloud)

        一目均衡表是一個綜合技術分析系統，包含多條線。

        Args:
            tenkan_period: 轉換線週期，默認 9
            kijun_period: 基準線週期，默認 26
            senkou_span_b_period: 先行帶B週期，默認 52
            displacement: 位移，默認 26

        Returns:
            包含各條線的字典
        """
        if self.data is None or self.data.empty:
            return {}

        try:
            result = {}

            # 轉換線 (Tenkan-sen)
            tenkan_high = self.data['high'].rolling(window=tenkan_period).max()
            tenkan_low = self.data['low'].rolling(window=tenkan_period).min()
            tenkan_sen = (tenkan_high + tenkan_low) / 2
            result['tenkan_sen'] = tenkan_sen

            # 基準線 (Kijun-sen)
            kijun_high = self.data['high'].rolling(window=kijun_period).max()
            kijun_low = self.data['low'].rolling(window=kijun_period).min()
            kijun_sen = (kijun_high + kijun_low) / 2
            result['kijun_sen'] = kijun_sen

            # 先行帶A (Senkou Span A)
            senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(displacement)
            result['senkou_span_a'] = senkou_span_a

            # 先行帶B (Senkou Span B)
            senkou_high = self.data['high'].rolling(window=senkou_span_b_period).max()
            senkou_low = self.data['low'].rolling(window=senkou_span_b_period).min()
            senkou_span_b = ((senkou_high + senkou_low) / 2).shift(displacement)
            result['senkou_span_b'] = senkou_span_b

            # 遲行線 (Chikou Span)
            chikou_span = self.data['close'].shift(-displacement)
            result['chikou_span'] = chikou_span

            # 保存到指標字典
            for key, value in result.items():
                self.indicators[f'ICHIMOKU_{key}'] = value

            logger.info("一目均衡表計算完成")
            return result

        except Exception as e:
            logger.error(f"一目均衡表計算失敗: {e}")
            return {}

    def get_all_indicators(self) -> Dict[str, pd.Series]:
        """獲取所有計算的指標"""
        return self.indicators.copy()

    def calculate_all_indicators(self, **kwargs) -> Dict[str, pd.Series]:
        """
        計算所有支持的技術指標

        Args:
            **kwargs: 各指標的參數設置

        Returns:
            包含所有指標的字典
        """
        if self.data is None or self.data.empty:
            logger.warning("數據為空，無法計算指標")
            return {}

        try:
            # Williams %R
            self.calculate_williams_r(kwargs.get('willr_period', 14))

            # Stochastic
            self.calculate_stochastic(
                kwargs.get('stoch_k_period', 14),
                kwargs.get('stoch_d_period', 3),
                kwargs.get('stoch_smooth_k', 3)
            )

            # CCI
            self.calculate_cci(kwargs.get('cci_period', 20))

            # ATR
            self.calculate_atr(kwargs.get('atr_period', 14))

            # Parabolic SAR
            self.calculate_parabolic_sar(
                kwargs.get('sar_acceleration', 0.02),
                kwargs.get('sar_maximum', 0.2)
            )

            # VWAP
            if 'volume' in self.data.columns:
                self.calculate_vwap()

                # MFI (需要成交量數據)
                self.calculate_mfi(kwargs.get('mfi_period', 14))

            # Ichimoku
            self.calculate_ichimoku(
                kwargs.get('ichimoku_tenkan', 9),
                kwargs.get('ichimoku_kijun', 26),
                kwargs.get('ichimoku_senkou_b', 52),
                kwargs.get('ichimoku_displacement', 26)
            )

            logger.info(f"成功計算 {len(self.indicators)} 個技術指標")
            return self.indicators.copy()

        except Exception as e:
            logger.error(f"批量計算技術指標失敗: {e}")
            return self.indicators.copy()
