"""
基礎技術指標
包含常用的技術指標計算
"""

import numpy as np
import pandas as pd

class BasicIndicators:
    """基礎技術指標類"""
    
    @staticmethod
    def sma(data: pd.Series, period: int = 20) -> pd.Series:
        """簡單移動平均線"""
        try:
            import talib
            return pd.Series(talib.SMA(data.values, timeperiod=period), index=data.index)
        except ImportError:
            # 備用實現
            return data.rolling(window=period).mean()
    
    @staticmethod
    def ema(data: pd.Series, period: int = 20) -> pd.Series:
        """指數移動平均線"""
        try:
            import talib
            return pd.Series(talib.EMA(data.values, timeperiod=period), index=data.index)
        except ImportError:
            # 備用實現
            return data.ewm(span=period).mean()
    
    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """相對強弱指標"""
        try:
            import talib
            return pd.Series(talib.RSI(data.values, timeperiod=period), index=data.index)
        except ImportError:
            # 備用實現
            delta = data.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))
    
    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
        """MACD指標"""
        try:
            import talib
            macd, signal_line, histogram = talib.MACD(data.values, 
                                                     fastperiod=fast, 
                                                     slowperiod=slow, 
                                                     signalperiod=signal)
            return {
                'macd': pd.Series(macd, index=data.index),
                'signal': pd.Series(signal_line, index=data.index),
                'histogram': pd.Series(histogram, index=data.index)
            }
        except ImportError:
            # 備用實現
            ema_fast = data.ewm(span=fast).mean()
            ema_slow = data.ewm(span=slow).mean()
            macd = ema_fast - ema_slow
            signal_line = macd.ewm(span=signal).mean()
            histogram = macd - signal_line
            return {
                'macd': macd,
                'signal': signal_line,
                'histogram': histogram
            }
