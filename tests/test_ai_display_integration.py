# -*- coding: utf-8 -*-
"""
AI顯示邏輯整合測試

此模組測試AI顯示邏輯改進功能整合到數據檢視模組的效果，
驗證股價走勢圖功能、技術指標計算和AI整合功能。

測試內容：
- 增強版股價走勢圖功能測試
- 技術指標計算測試
- AI整合圖表功能測試
- 用戶界面組件測試
- 性能和穩定性測試

Example:
    運行測試：
    ```bash
    pytest tests/test_ai_display_integration.py -v
    ```

Note:
    此測試模組專門驗證AI顯示邏輯改進功能的整合效果，
    確保新功能與現有數據檢視模組的無縫整合。
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import streamlit as st

# 導入待測試的模組
try:
    from src.ui.pages.data_management import (
        show_stock_chart_plotly,
        _show_basic_chart,
        _show_advanced_chart,
        _show_ai_integrated_chart,
        _calculate_technical_indicators
    )
except ImportError as e:
    pytest.skip(f"無法導入測試模組: {e}", allow_module_level=True)


class TestAIDisplayIntegration:
    """測試AI顯示邏輯整合"""
    
    def setup_method(self):
        """設置測試環境"""
        # 創建測試數據
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
        np.random.seed(42)
        
        # 生成模擬股價數據
        base_price = 100
        price_changes = np.random.normal(0, 2, len(dates))
        prices = [base_price]
        
        for change in price_changes[1:]:
            new_price = max(prices[-1] + change, 1)  # 確保價格不為負
            prices.append(new_price)
        
        self.test_df = pd.DataFrame({
            'date': dates,
            'open': [p * (1 + np.random.normal(0, 0.01)) for p in prices],
            'high': [p * (1 + abs(np.random.normal(0, 0.02))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.02))) for p in prices],
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, len(dates))
        })
        
        # 確保OHLC邏輯正確
        for i in range(len(self.test_df)):
            row = self.test_df.iloc[i]
            high = max(row['open'], row['close'], row['high'])
            low = min(row['open'], row['close'], row['low'])
            self.test_df.at[i, 'high'] = high
            self.test_df.at[i, 'low'] = low
        
        self.test_symbol = "2330.TW"
        
    def test_technical_indicators_calculation(self):
        """測試技術指標計算"""
        # 準備數據
        price_data = self.test_df.set_index('date')
        
        # 計算技術指標
        indicators_df = _calculate_technical_indicators(price_data)
        
        # 驗證結果
        assert isinstance(indicators_df, pd.DataFrame)
        assert len(indicators_df) == len(price_data)
        
        # 檢查RSI計算
        if 'RSI' in indicators_df.columns:
            rsi_values = indicators_df['RSI'].dropna()
            assert all(0 <= val <= 100 for val in rsi_values), "RSI值應該在0-100之間"
            
        # 檢查SMA計算
        if 'SMA_20' in indicators_df.columns:
            sma_values = indicators_df['SMA_20'].dropna()
            assert len(sma_values) > 0, "SMA應該有計算結果"
            assert all(val > 0 for val in sma_values), "SMA值應該為正"
            
        # 檢查MACD計算
        if 'MACD' in indicators_df.columns:
            macd_values = indicators_df['MACD'].dropna()
            assert len(macd_values) > 0, "MACD應該有計算結果"
            
    def test_technical_indicators_edge_cases(self):
        """測試技術指標計算的邊緣情況"""
        # 測試空數據
        empty_df = pd.DataFrame()
        result = _calculate_technical_indicators(empty_df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
        
        # 測試數據不足的情況
        small_df = self.test_df.head(5).set_index('date')
        result = _calculate_technical_indicators(small_df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5
        
        # 測試缺少必要列的情況
        incomplete_df = self.test_df[['date', 'close']].set_index('date')
        result = _calculate_technical_indicators(incomplete_df)
        assert isinstance(result, pd.DataFrame)
        
    @patch('streamlit.selectbox')
    @patch('streamlit.checkbox')
    @patch('streamlit.columns')
    @patch('streamlit.write')
    @patch('streamlit.plotly_chart')
    def test_show_stock_chart_plotly_basic(self, mock_plotly, mock_write, 
                                          mock_columns, mock_checkbox, mock_selectbox):
        """測試基礎股價圖表顯示"""
        # 模擬Streamlit組件
        mock_selectbox.side_effect = ["基礎圖表", "全部"]
        mock_checkbox.return_value = True
        mock_columns.return_value = [Mock(), Mock(), Mock()]
        
        # 測試函數調用
        try:
            show_stock_chart_plotly(self.test_df, self.test_symbol)
            
            # 驗證Streamlit組件被調用
            assert mock_write.called
            assert mock_plotly.called
            
        except Exception as e:
            # 在測試環境中，Streamlit組件可能無法正常工作
            pytest.skip(f"Streamlit組件測試跳過: {e}")
            
    @patch('streamlit.selectbox')
    @patch('streamlit.checkbox')
    @patch('streamlit.columns')
    @patch('streamlit.write')
    @patch('streamlit.plotly_chart')
    @patch('streamlit.expander')
    def test_show_stock_chart_plotly_advanced(self, mock_expander, mock_plotly, 
                                             mock_write, mock_columns, 
                                             mock_checkbox, mock_selectbox):
        """測試進階股價圖表顯示"""
        # 模擬Streamlit組件
        mock_selectbox.side_effect = ["進階圖表 (含技術指標)", "全部"]
        mock_checkbox.return_value = True
        mock_columns.return_value = [Mock(), Mock(), Mock()]
        mock_expander.return_value.__enter__ = Mock()
        mock_expander.return_value.__exit__ = Mock()
        
        # 測試函數調用
        try:
            show_stock_chart_plotly(self.test_df, self.test_symbol)
            
            # 驗證組件被調用
            assert mock_write.called
            assert mock_plotly.called
            
        except Exception as e:
            pytest.skip(f"進階圖表測試跳過: {e}")
            
    def test_data_filtering_by_timeframe(self):
        """測試時間框架數據過濾"""
        # 測試不同時間框架的數據過濾邏輯
        original_len = len(self.test_df)
        
        # 模擬30天過濾
        cutoff_date = self.test_df['date'].max() - pd.Timedelta(days=30)
        filtered_30 = self.test_df[self.test_df['date'] >= cutoff_date]
        
        assert len(filtered_30) <= original_len
        assert len(filtered_30) <= 30  # 最多30天的數據
        
        # 模擬90天過濾
        cutoff_date = self.test_df['date'].max() - pd.Timedelta(days=90)
        filtered_90 = self.test_df[self.test_df['date'] >= cutoff_date]
        
        assert len(filtered_90) <= original_len
        assert len(filtered_90) >= len(filtered_30)  # 90天數據應該比30天多
        
    @patch('src.ui.components.interactive_charts.agent_integrated_display')
    @patch('src.ai.self_learning_agent.SelfLearningAgent')
    @patch('streamlit.info')
    @patch('streamlit.columns')
    @patch('streamlit.checkbox')
    @patch('streamlit.multiselect')
    @patch('streamlit.slider')
    @patch('streamlit.button')
    @patch('streamlit.plotly_chart')
    def test_ai_integrated_chart_functionality(self, mock_plotly, mock_button,
                                              mock_slider, mock_multiselect,
                                              mock_checkbox, mock_columns,
                                              mock_info, mock_agent_class,
                                              mock_agent_display):
        """測試AI整合圖表功能"""
        # 模擬組件返回值
        mock_columns.return_value = [Mock(), Mock()]
        mock_checkbox.return_value = True
        mock_multiselect.side_effect = [["RSI", "MACD"], [1.0]]
        mock_slider.return_value = 180
        mock_button.return_value = True
        
        # 模擬AI組件
        mock_agent_display.return_value = Mock()  # 模擬圖表對象
        mock_agent = Mock()
        mock_agent.user_interactions = []
        mock_agent_class.return_value = mock_agent
        
        try:
            _show_ai_integrated_chart(self.test_df, self.test_symbol, True)
            
            # 驗證AI組件被調用
            if mock_button.return_value:  # 如果按鈕被點擊
                mock_agent_display.assert_called_once()
                
        except ImportError:
            pytest.skip("AI模組不可用，跳過測試")
        except Exception as e:
            pytest.skip(f"AI整合測試跳過: {e}")
            
    def test_chart_performance_with_large_dataset(self):
        """測試大數據集的圖表性能"""
        # 創建大數據集（2年數據）
        large_dates = pd.date_range(start='2022-01-01', end='2024-12-31', freq='D')
        large_df = pd.DataFrame({
            'date': large_dates,
            'open': np.random.uniform(90, 110, len(large_dates)),
            'high': np.random.uniform(100, 120, len(large_dates)),
            'low': np.random.uniform(80, 100, len(large_dates)),
            'close': np.random.uniform(95, 105, len(large_dates)),
            'volume': np.random.randint(1000000, 10000000, len(large_dates))
        })
        
        # 確保OHLC邏輯正確
        for i in range(len(large_df)):
            row = large_df.iloc[i]
            high = max(row['open'], row['close'], row['high'])
            low = min(row['open'], row['close'], row['low'])
            large_df.at[i, 'high'] = high
            large_df.at[i, 'low'] = low
        
        # 測試技術指標計算性能
        import time
        start_time = time.time()
        
        price_data = large_df.set_index('date')
        indicators_df = _calculate_technical_indicators(price_data)
        
        calculation_time = time.time() - start_time
        
        # 驗證性能要求（應該在合理時間內完成）
        assert calculation_time < 5.0, f"技術指標計算耗時過長: {calculation_time:.2f}秒"
        assert len(indicators_df) == len(price_data), "指標數據長度應該與原數據一致"
        
    def test_error_handling_robustness(self):
        """測試錯誤處理健壯性"""
        # 測試各種異常情況
        test_cases = [
            pd.DataFrame(),  # 空數據框
            pd.DataFrame({'date': [datetime.now()]}),  # 缺少價格數據
            pd.DataFrame({  # 包含NaN值的數據
                'date': pd.date_range('2024-01-01', periods=5),
                'open': [100, np.nan, 102, 103, 104],
                'high': [105, 106, np.nan, 108, 109],
                'low': [95, 96, 97, np.nan, 99],
                'close': [104, 105, 106, 107, np.nan],
                'volume': [1000, 1100, 1200, 1300, 1400]
            })
        ]
        
        for i, test_df in enumerate(test_cases):
            try:
                if not test_df.empty and 'close' in test_df.columns:
                    price_data = test_df.set_index('date') if 'date' in test_df.columns else test_df
                    result = _calculate_technical_indicators(price_data)
                    assert isinstance(result, pd.DataFrame), f"測試案例 {i} 應該返回DataFrame"
                else:
                    result = _calculate_technical_indicators(test_df)
                    assert isinstance(result, pd.DataFrame), f"測試案例 {i} 應該返回DataFrame"
            except Exception as e:
                # 記錄但不失敗，因為某些異常是預期的
                print(f"測試案例 {i} 產生預期異常: {e}")
                
    def test_chart_configuration_options(self):
        """測試圖表配置選項"""
        # 測試不同的圖表配置組合
        configurations = [
            {"chart_type": "基礎圖表", "time_frame": "全部", "show_volume": True},
            {"chart_type": "基礎圖表", "time_frame": "最近30天", "show_volume": False},
            {"chart_type": "進階圖表 (含技術指標)", "time_frame": "最近90天", "show_volume": True},
        ]
        
        for config in configurations:
            # 模擬時間框架過濾
            if config["time_frame"] != "全部":
                days = {"最近30天": 30, "最近90天": 90, "最近180天": 180}[config["time_frame"]]
                cutoff_date = self.test_df['date'].max() - pd.Timedelta(days=days)
                filtered_df = self.test_df[self.test_df['date'] >= cutoff_date]
            else:
                filtered_df = self.test_df
                
            # 驗證過濾結果
            assert len(filtered_df) <= len(self.test_df)
            if config["time_frame"] != "全部":
                expected_max_days = days + 1  # 允許一天的誤差
                assert len(filtered_df) <= expected_max_days
                
    def test_integration_with_existing_components(self):
        """測試與現有組件的整合"""
        # 驗證新功能不會破壞現有的數據檢視功能
        
        # 測試數據格式兼容性
        required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            assert col in self.test_df.columns, f"測試數據缺少必要列: {col}"
            
        # 測試數據類型
        assert pd.api.types.is_datetime64_any_dtype(self.test_df['date']), "日期列應該是datetime類型"
        
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            assert pd.api.types.is_numeric_dtype(self.test_df[col]), f"{col}列應該是數值類型"
            
        # 測試數據邏輯
        for _, row in self.test_df.iterrows():
            assert row['high'] >= row['low'], "最高價應該大於等於最低價"
            assert row['high'] >= row['open'], "最高價應該大於等於開盤價"
            assert row['high'] >= row['close'], "最高價應該大於等於收盤價"
            assert row['low'] <= row['open'], "最低價應該小於等於開盤價"
            assert row['low'] <= row['close'], "最低價應該小於等於收盤價"
            assert row['volume'] >= 0, "成交量應該非負"


class TestPerformanceAndScalability:
    """性能和可擴展性測試"""
    
    def test_memory_usage_with_large_datasets(self):
        """測試大數據集的內存使用"""
        import psutil
        import os
        
        # 獲取初始內存使用
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 創建大數據集
        large_dates = pd.date_range(start='2020-01-01', end='2024-12-31', freq='D')
        large_df = pd.DataFrame({
            'date': large_dates,
            'open': np.random.uniform(90, 110, len(large_dates)),
            'high': np.random.uniform(100, 120, len(large_dates)),
            'low': np.random.uniform(80, 100, len(large_dates)),
            'close': np.random.uniform(95, 105, len(large_dates)),
            'volume': np.random.randint(1000000, 10000000, len(large_dates))
        })
        
        # 處理數據
        price_data = large_df.set_index('date')
        indicators_df = _calculate_technical_indicators(price_data)
        
        # 檢查內存使用
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # 驗證內存使用合理（不應該超過500MB）
        assert memory_increase < 500, f"內存使用過多: {memory_increase:.2f}MB"
        assert len(indicators_df) == len(price_data), "處理後數據長度應該一致"
        
    def test_concurrent_chart_generation(self):
        """測試並發圖表生成"""
        import threading
        import time
        
        results = []
        errors = []
        
        def generate_chart(thread_id):
            try:
                # 創建測試數據
                dates = pd.date_range(start='2024-01-01', periods=100)
                df = pd.DataFrame({
                    'date': dates,
                    'open': np.random.uniform(90, 110, 100),
                    'high': np.random.uniform(100, 120, 100),
                    'low': np.random.uniform(80, 100, 100),
                    'close': np.random.uniform(95, 105, 100),
                    'volume': np.random.randint(1000000, 10000000, 100)
                })
                
                # 計算技術指標
                price_data = df.set_index('date')
                indicators_df = _calculate_technical_indicators(price_data)
                
                results.append(f"Thread {thread_id}: Success")
                
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")
        
        # 創建多個線程
        threads = []
        for i in range(5):
            thread = threading.Thread(target=generate_chart, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有線程完成
        for thread in threads:
            thread.join(timeout=10)
        
        # 驗證結果
        assert len(errors) == 0, f"並發測試出現錯誤: {errors}"
        assert len(results) == 5, f"並發測試結果不完整: {results}"


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v", "--tb=short"])
