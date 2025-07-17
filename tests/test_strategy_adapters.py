# -*- coding: utf-8 -*-
"""
策略適配器測試模組

此模組測試策略適配器的功能，包括：
- 適配器基類測試
- 雙移動平均線適配器測試
- Alpha101 因子庫適配器測試
- 數據格式轉換測試
- 錯誤處理測試

測試覆蓋：
- 單元測試：測試各個組件的獨立功能
- 整合測試：測試適配器與系統的整合
- 性能測試：測試適配器的執行性能
- 錯誤測試：測試異常情況的處理
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.strategies.adapters import (
    LegacyStrategyAdapter,
    DataFormatConverter,
    StrategyWrapper,
    DoubleMaAdapter,
    Alpha101Adapter,
    AdapterError,
    DataConversionError,
    StrategyExecutionError,
)


class TestDataFormatConverter:
    """測試數據格式轉換器"""
    
    def test_standardize_columns(self):
        """測試欄位標準化"""
        # 創建測試數據
        data = pd.DataFrame({
            '收盤價': [100, 101, 102, 103, 104],
            '開盤價': [99, 100, 101, 102, 103],
            '交易日期': pd.date_range('2023-01-01', periods=5),
            '成交量': [1000, 1100, 1200, 1300, 1400]
        })
        
        # 標準化欄位
        standardized = DataFormatConverter.standardize_columns(data)
        
        # 驗證結果
        assert 'close' in standardized.columns
        assert 'open' in standardized.columns
        assert 'date' in standardized.columns
        assert 'volume' in standardized.columns
        assert len(standardized) == 5
    
    def test_convert_to_legacy_format(self):
        """測試轉換為舊版格式"""
        # 創建測試數據
        data = pd.DataFrame({
            'close': [100.0, 101.0, 102.0, 103.0, 104.0],
            'date': pd.date_range('2023-01-01', periods=5),
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        
        # 轉換格式
        legacy_data = DataFormatConverter.convert_to_legacy_format(data)
        
        # 驗證結果
        assert isinstance(legacy_data, pd.DataFrame)
        assert 'close' in legacy_data.columns
        assert 'date' in legacy_data.columns
        assert len(legacy_data) == 5
        assert legacy_data['close'].dtype in [np.float64, np.float32]
    
    def test_missing_required_columns(self):
        """測試缺少必要欄位的情況"""
        # 創建缺少必要欄位的數據
        data = pd.DataFrame({
            'open': [99, 100, 101, 102, 103],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        
        # 應該拋出異常
        with pytest.raises(DataConversionError):
            DataFormatConverter.standardize_columns(data)


class TestStrategyWrapper:
    """測試策略包裝器"""
    
    def test_successful_execution(self):
        """測試成功執行"""
        def test_func(x, y):
            return x + y
        
        wrapper = StrategyWrapper(test_func, "test_strategy")
        result = wrapper.execute(1, 2)
        
        assert result == 3
        assert wrapper.execution_count == 1
        assert wrapper.error_count == 0
        assert wrapper.success_rate == 1.0
    
    def test_execution_error(self):
        """測試執行錯誤"""
        def error_func():
            raise ValueError("Test error")
        
        wrapper = StrategyWrapper(error_func, "error_strategy")
        
        with pytest.raises(StrategyExecutionError):
            wrapper.execute()
        
        assert wrapper.execution_count == 1
        assert wrapper.error_count == 1
        assert wrapper.success_rate == 0.0


class TestDoubleMaAdapter:
    """測試雙移動平均線適配器"""
    
    @pytest.fixture
    def sample_data(self):
        """創建測試數據"""
        dates = pd.date_range('2023-01-01', periods=50)
        prices = 100 + np.cumsum(np.random.randn(50) * 0.01)
        
        return pd.DataFrame({
            'date': dates,
            'close': prices,
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.98,
            'volume': np.random.randint(1000, 5000, 50)
        })
    
    def test_initialization(self):
        """測試初始化"""
        adapter = DoubleMaAdapter(short_window=5, long_window=20)
        
        assert adapter.name == "DoubleMaStrategy"
        assert adapter.short_window == 5
        assert adapter.long_window == 20
        assert adapter.legacy_strategy is not None
    
    def test_parameter_validation(self):
        """測試參數驗證"""
        # 測試無效參數
        with pytest.raises(Exception):  # ParameterError
            DoubleMaAdapter(short_window=0, long_window=20)
        
        with pytest.raises(Exception):  # ParameterError
            DoubleMaAdapter(short_window=20, long_window=10)
    
    def test_generate_signals(self, sample_data):
        """測試訊號生成"""
        adapter = DoubleMaAdapter(short_window=5, long_window=10)
        signals = adapter.generate_signals(sample_data)
        
        # 驗證結果格式
        assert isinstance(signals, pd.DataFrame)
        assert 'signal' in signals.columns
        assert 'buy_signal' in signals.columns
        assert 'sell_signal' in signals.columns
        assert len(signals) == len(sample_data)
        
        # 驗證訊號值
        assert signals['signal'].isin([0.0, 1.0, -1.0]).all()
        assert signals['buy_signal'].isin([0, 1]).all()
        assert signals['sell_signal'].isin([0, 1]).all()
    
    def test_strategy_info(self):
        """測試策略資訊"""
        adapter = DoubleMaAdapter(short_window=5, long_window=20)
        info = adapter.get_strategy_info()
        
        assert info['name'] == "DoubleMaStrategy"
        assert info['type'] == 'Technical Analysis'
        assert info['category'] == 'Moving Average'
        assert info['parameters']['short_window'] == 5
        assert info['parameters']['long_window'] == 20


class TestAlpha101Adapter:
    """測試 Alpha101 因子庫適配器"""
    
    @pytest.fixture
    def sample_data(self):
        """創建測試數據"""
        dates = pd.date_range('2023-01-01', periods=100)
        prices = 100 + np.cumsum(np.random.randn(100) * 0.01)
        
        return pd.DataFrame({
            'date': dates,
            'close': prices,
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.98,
            'volume': np.random.randint(1000, 5000, 100)
        })
    
    def test_initialization(self):
        """測試初始化"""
        adapter = Alpha101Adapter(
            factors=['alpha001', 'alpha002'],
            weights=[0.6, 0.4],
            signal_threshold=0.02
        )
        
        assert adapter.name == "Alpha101Strategy"
        assert adapter.factors == ['alpha001', 'alpha002']
        assert adapter.weights == [0.6, 0.4]
        assert adapter.signal_threshold == 0.02
    
    def test_parameter_validation(self):
        """測試參數驗證"""
        # 測試權重不匹配
        with pytest.raises(Exception):  # ParameterError
            Alpha101Adapter(
                factors=['alpha001', 'alpha002'],
                weights=[0.6]  # 權重數量不匹配
            )
        
        # 測試權重總和不為1
        with pytest.raises(Exception):  # ParameterError
            Alpha101Adapter(
                factors=['alpha001', 'alpha002'],
                weights=[0.6, 0.6]  # 總和不為1
            )
    
    def test_calculate_factors(self, sample_data):
        """測試因子計算"""
        adapter = Alpha101Adapter(factors=['alpha001', 'alpha002'])
        factor_results = adapter.calculate_factors(sample_data)
        
        # 驗證結果
        assert isinstance(factor_results, dict)
        assert 'alpha001' in factor_results
        assert 'alpha002' in factor_results
        
        for factor_name, factor_value in factor_results.items():
            assert isinstance(factor_value, pd.Series)
            assert len(factor_value) == len(sample_data)
    
    def test_generate_signals(self, sample_data):
        """測試訊號生成"""
        adapter = Alpha101Adapter(
            factors=['alpha001', 'alpha002'],
            weights=[0.6, 0.4],
            signal_threshold=0.01
        )
        signals = adapter.generate_signals(sample_data)
        
        # 驗證結果格式
        assert isinstance(signals, pd.DataFrame)
        assert 'signal' in signals.columns
        assert 'buy_signal' in signals.columns
        assert 'sell_signal' in signals.columns
        assert 'combined_factor' in signals.columns
        assert len(signals) == len(sample_data)
        
        # 驗證訊號值
        assert signals['signal'].isin([0.0, 1.0, -1.0]).all()
        assert signals['buy_signal'].isin([0, 1]).all()
        assert signals['sell_signal'].isin([0, 1]).all()
    
    def test_strategy_info(self):
        """測試策略資訊"""
        adapter = Alpha101Adapter(factors=['alpha001', 'alpha002'])
        info = adapter.get_strategy_info()
        
        assert info['name'] == "Alpha101Strategy"
        assert info['type'] == 'Factor-based'
        assert info['category'] == 'Alpha101'
        assert info['parameters']['factors'] == ['alpha001', 'alpha002']


class TestIntegration:
    """整合測試"""
    
    @pytest.fixture
    def sample_data(self):
        """創建測試數據"""
        dates = pd.date_range('2023-01-01', periods=100)
        prices = 100 + np.cumsum(np.random.randn(100) * 0.01)
        
        return pd.DataFrame({
            'date': dates,
            'close': prices,
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.98,
            'volume': np.random.randint(1000, 5000, 100)
        })
    
    def test_multiple_adapters(self, sample_data):
        """測試多個適配器同時使用"""
        # 創建多個適配器
        double_ma = DoubleMaAdapter(short_window=5, long_window=20)
        alpha101 = Alpha101Adapter(factors=['alpha001', 'alpha002'])
        
        # 生成訊號
        ma_signals = double_ma.generate_signals(sample_data)
        alpha_signals = alpha101.generate_signals(sample_data)
        
        # 驗證結果
        assert len(ma_signals) == len(sample_data)
        assert len(alpha_signals) == len(sample_data)
        assert 'signal' in ma_signals.columns
        assert 'signal' in alpha_signals.columns
    
    def test_performance_comparison(self, sample_data):
        """測試性能比較"""
        adapters = [
            DoubleMaAdapter(short_window=5, long_window=20),
            Alpha101Adapter(factors=['alpha001'])
        ]
        
        results = {}
        for adapter in adapters:
            signals = adapter.generate_signals(sample_data)
            metrics = adapter.evaluate(sample_data, signals)
            results[adapter.name] = metrics
        
        # 驗證所有適配器都能正常執行
        assert len(results) == 2
        for name, metrics in results.items():
            assert isinstance(metrics, dict)
            assert 'total_return' in metrics


if __name__ == '__main__':
    # 運行測試
    pytest.main([__file__, '-v'])
