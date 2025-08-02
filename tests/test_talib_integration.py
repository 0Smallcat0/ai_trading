"""
TA-LIB整合測試
"""

import pytest
import numpy as np
import pandas as pd
from src.indicators.basic_indicators import BasicIndicators

class TestTALibIntegration:
    """TA-LIB整合測試類"""
    
    def setup_method(self):
        """設置測試數據"""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
        self.test_data = pd.Series(prices, index=dates)
    
    def test_sma_calculation(self):
        """測試SMA計算"""
        sma = BasicIndicators.sma(self.test_data, period=20)
        
        assert isinstance(sma, pd.Series)
        assert len(sma) == len(self.test_data)
        assert not sma.iloc[-1] != sma.iloc[-1]  # 檢查不是NaN
    
    def test_ema_calculation(self):
        """測試EMA計算"""
        ema = BasicIndicators.ema(self.test_data, period=20)
        
        assert isinstance(ema, pd.Series)
        assert len(ema) == len(self.test_data)
    
    def test_rsi_calculation(self):
        """測試RSI計算"""
        rsi = BasicIndicators.rsi(self.test_data, period=14)
        
        assert isinstance(rsi, pd.Series)
        assert len(rsi) == len(self.test_data)
        # RSI應該在0-100之間
        valid_rsi = rsi.dropna()
        assert all(0 <= val <= 100 for val in valid_rsi)
    
    def test_macd_calculation(self):
        """測試MACD計算"""
        macd_result = BasicIndicators.macd(self.test_data)
        
        assert isinstance(macd_result, dict)
        assert 'macd' in macd_result
        assert 'signal' in macd_result
        assert 'histogram' in macd_result
        
        for key, series in macd_result.items():
            assert isinstance(series, pd.Series)
            assert len(series) == len(self.test_data)

if __name__ == "__main__":
    # 簡單測試運行
    test = TestTALibIntegration()
    test.setup_method()
    
    try:
        test.test_sma_calculation()
        print("✅ SMA測試通過")
        
        test.test_ema_calculation()
        print("✅ EMA測試通過")
        
        test.test_rsi_calculation()
        print("✅ RSI測試通過")
        
        test.test_macd_calculation()
        print("✅ MACD測試通過")
        
        print("🎉 所有測試通過!")
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
