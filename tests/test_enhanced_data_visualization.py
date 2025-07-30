# -*- coding: utf-8 -*-
"""
增強數據視覺化組件測試

此模組測試AI顯示邏輯改進功能中的增強數據視覺化組件，
驗證季節性分析、多時間框架分析等功能的正確性。

測試內容：
- 增強數據視覺化器初始化
- 季節性分析圖表生成
- 多時間框架分析圖表生成
- 交易訊號性能分析
- 用戶行為分析
- 系統性能監控儀表板

Example:
    運行測試：
    ```bash
    pytest tests/test_enhanced_data_visualization.py -v
    ```

Note:
    此測試模組專門驗證AI顯示邏輯改進說明中增強視覺化功能的實施效果。
"""

import pytest
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# 導入待測試的模組
try:
    from src.ui.components.enhanced_data_visualization import EnhancedDataVisualizer
except ImportError as e:
    pytest.skip(f"無法導入測試模組: {e}", allow_module_level=True)


class TestEnhancedDataVisualizer:
    """測試增強數據視覺化器"""
    
    def setup_method(self):
        """設置測試環境"""
        self.visualizer = EnhancedDataVisualizer()
        self.test_data = self._create_test_data()
        
    def _create_test_data(self):
        """創建測試數據"""
        dates = pd.date_range('2024-01-01', '2024-12-31', freq='D')
        np.random.seed(42)  # 確保測試結果可重現
        
        # 生成模擬股價數據
        base_price = 100
        prices = []
        for i in range(len(dates)):
            change = np.random.normal(0, 1)
            base_price += change
            base_price = max(base_price, 10)
            prices.append(base_price)
            
        return pd.DataFrame({
            'date': dates,
            'open': [p * (1 + np.random.uniform(-0.01, 0.01)) for p in prices],
            'high': [p * (1 + abs(np.random.uniform(0, 0.02))) for p in prices],
            'low': [p * (1 - abs(np.random.uniform(0, 0.02))) for p in prices],
            'close': prices,
            'volume': [np.random.randint(1000000, 10000000) for _ in prices]
        })
        
    def test_visualizer_initialization(self):
        """測試視覺化器初始化"""
        assert self.visualizer is not None
        assert hasattr(self.visualizer, 'color_palette')
        assert isinstance(self.visualizer.color_palette, dict)
        assert 'primary' in self.visualizer.color_palette
        assert 'secondary' in self.visualizer.color_palette
        
    def test_seasonal_analysis_creation(self):
        """測試季節性分析圖表創建"""
        fig = self.visualizer.create_seasonal_analysis(self.test_data, 'TEST')
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0  # 應該有數據系列
        
        # 檢查圖表標題
        assert 'TEST 季節性分析' in fig.layout.title.text
        
        # 檢查子圖數量（應該有4個子圖）
        assert len(fig.data) >= 4
        
    def test_seasonal_analysis_with_date_column(self):
        """測試包含date欄位的季節性分析"""
        # 測試數據已經有date欄位
        fig = self.visualizer.create_seasonal_analysis(self.test_data, 'TEST')
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        
    def test_seasonal_analysis_with_indexed_data(self):
        """測試已設置日期索引的數據"""
        indexed_data = self.test_data.set_index('date')
        fig = self.visualizer.create_seasonal_analysis(indexed_data, 'TEST')
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        
    def test_multi_timeframe_analysis_creation(self):
        """測試多時間框架分析圖表創建"""
        fig = self.visualizer.create_multi_timeframe_analysis(self.test_data, 'TEST')
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        
        # 檢查圖表標題
        assert 'TEST 多時間框架分析' in fig.layout.title.text
        
        # 應該有多個數據系列（日線、週線、月線及其移動平均）
        assert len(fig.data) >= 6
        
    def test_signal_performance_analysis_empty_data(self):
        """測試空訊號數據的性能分析"""
        fig = self.visualizer.create_signal_performance_analysis([])
        
        assert isinstance(fig, go.Figure)
        # 空數據應該返回帶有提示信息的圖表
        assert len(fig.layout.annotations) > 0
        assert "暫無交易訊號數據" in fig.layout.annotations[0].text
        
    def test_signal_performance_analysis_with_data(self):
        """測試有訊號數據的性能分析"""
        sample_signals = [
            {"signal_type": "MACD金叉", "date": "2024-01-15", "strength": 0.8},
            {"signal_type": "RSI超賣", "date": "2024-02-20", "strength": 0.9},
            {"signal_type": "MACD死叉", "date": "2024-03-10", "strength": 0.7},
            {"signal_type": "RSI超買", "date": "2024-04-05", "strength": 0.85}
        ]
        
        fig = self.visualizer.create_signal_performance_analysis(sample_signals)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert '交易訊號性能分析' in fig.layout.title.text
        
    def test_user_behavior_analysis_empty_data(self):
        """測試空用戶互動數據的行為分析"""
        fig = self.visualizer.create_user_behavior_analysis([])
        
        assert isinstance(fig, go.Figure)
        # 空數據應該返回帶有提示信息的圖表
        assert len(fig.layout.annotations) > 0
        assert "暫無用戶互動數據" in fig.layout.annotations[0].text
        
    def test_user_behavior_analysis_with_data(self):
        """測試有用戶互動數據的行為分析"""
        sample_interactions = [
            {
                "interaction_type": "chart_view",
                "timestamp": "2024-01-15T10:30:00",
                "parameters": {"indicators": ["RSI", "MACD"]},
                "result_quality": 0.8
            },
            {
                "interaction_type": "ai_analysis",
                "timestamp": "2024-01-16T14:20:00", 
                "parameters": {"indicators": ["SMA"]},
                "result_quality": 0.9
            }
        ]
        
        fig = self.visualizer.create_user_behavior_analysis(sample_interactions)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert '用戶行為分析' in fig.layout.title.text
        
    def test_system_performance_dashboard_creation(self):
        """測試系統性能監控儀表板創建"""
        performance_data = {
            'cpu_usage': 45.2,
            'memory_usage': 62.8,
            'chart_generation_times': [1.2, 1.5, 1.1, 1.8, 1.3],
            'processing_speeds': {
                '數據載入': 0.8,
                '指標計算': 1.2,
                '圖表渲染': 0.9
            },
            'error_rate': 2.1,
            'user_satisfaction': 8.5
        }
        
        fig = self.visualizer.create_system_performance_dashboard(performance_data)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        assert '系統性能監控儀表板' in fig.layout.title.text
        
        # 檢查是否有指示器類型的圖表（儀表板）
        indicator_traces = [trace for trace in fig.data if trace.type == 'indicator']
        assert len(indicator_traces) > 0
        
    def test_performance_color_calculation(self):
        """測試性能顏色計算"""
        # 測試正常情況（值越高越好）
        color1 = self.visualizer._get_performance_color(50, 80, reverse=False)
        assert color1 == "green"  # 50 < 80，應該是綠色
        
        color2 = self.visualizer._get_performance_color(85, 80, reverse=False)
        assert color2 == "orange"  # 85 > 80 但 < 96，應該是橙色
        
        color3 = self.visualizer._get_performance_color(100, 80, reverse=False)
        assert color3 == "red"  # 100 > 96，應該是紅色
        
        # 測試反向情況（值越低越好）
        color4 = self.visualizer._get_performance_color(30, 80, reverse=True)
        assert color4 == "green"  # 30 < 40，應該是綠色
        
        color5 = self.visualizer._get_performance_color(60, 80, reverse=True)
        assert color5 == "orange"  # 60 < 80 但 > 40，應該是橙色
        
        color6 = self.visualizer._get_performance_color(90, 80, reverse=True)
        assert color6 == "red"  # 90 > 80，應該是紅色
        
    def test_error_handling_in_seasonal_analysis(self):
        """測試季節性分析的錯誤處理"""
        # 測試無效數據
        invalid_data = pd.DataFrame({'invalid': [1, 2, 3]})
        fig = self.visualizer.create_seasonal_analysis(invalid_data, 'TEST')
        
        assert isinstance(fig, go.Figure)
        # 應該有錯誤提示
        assert len(fig.layout.annotations) > 0
        
    def test_error_handling_in_multi_timeframe_analysis(self):
        """測試多時間框架分析的錯誤處理"""
        # 測試無效數據
        invalid_data = pd.DataFrame({'invalid': [1, 2, 3]})
        fig = self.visualizer.create_multi_timeframe_analysis(invalid_data, 'TEST')
        
        assert isinstance(fig, go.Figure)
        # 應該有錯誤提示
        assert len(fig.layout.annotations) > 0
        
    def test_color_palette_completeness(self):
        """測試顏色調色板的完整性"""
        required_colors = [
            'primary', 'secondary', 'success', 'danger', 
            'warning', 'info', 'light', 'dark'
        ]
        
        for color in required_colors:
            assert color in self.visualizer.color_palette
            assert isinstance(self.visualizer.color_palette[color], str)
            assert self.visualizer.color_palette[color].startswith('#')
            
    def test_data_preprocessing_in_seasonal_analysis(self):
        """測試季節性分析中的數據預處理"""
        # 創建包含缺失值的測試數據
        data_with_na = self.test_data.copy()
        data_with_na.loc[10:20, 'close'] = np.nan
        
        fig = self.visualizer.create_seasonal_analysis(data_with_na, 'TEST')
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0  # 應該能處理缺失值
        
    def test_resampling_in_multi_timeframe_analysis(self):
        """測試多時間框架分析中的重採樣"""
        # 使用較短的時間序列測試
        short_data = self.test_data.head(100).copy()
        fig = self.visualizer.create_multi_timeframe_analysis(short_data, 'TEST')
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0
        
    def test_signal_data_validation(self):
        """測試訊號數據驗證"""
        # 測試不完整的訊號數據
        incomplete_signals = [
            {"signal_type": "MACD金叉"},  # 缺少其他欄位
            {"date": "2024-01-15"},       # 缺少signal_type
        ]
        
        fig = self.visualizer.create_signal_performance_analysis(incomplete_signals)
        
        assert isinstance(fig, go.Figure)
        # 應該能處理不完整的數據
        
    def test_interaction_data_validation(self):
        """測試互動數據驗證"""
        # 測試不完整的互動數據
        incomplete_interactions = [
            {"interaction_type": "chart_view"},  # 缺少其他欄位
            {"timestamp": "2024-01-15T10:30:00"}, # 缺少interaction_type
        ]
        
        fig = self.visualizer.create_user_behavior_analysis(incomplete_interactions)
        
        assert isinstance(fig, go.Figure)
        # 應該能處理不完整的數據


class TestEnhancedDataVisualizationIntegration:
    """測試增強數據視覺化整合"""
    
    def test_data_management_integration(self):
        """測試與數據管理頁面的整合"""
        try:
            from src.ui.pages.data_management import _show_enhanced_analysis_section
            
            # 檢查函數是否存在且可調用
            assert callable(_show_enhanced_analysis_section)
            
        except ImportError:
            pytest.skip("數據管理模組不可用")
            
    def test_visualizer_import_in_data_management(self):
        """測試數據管理頁面中的視覺化器導入"""
        try:
            # 模擬在數據管理頁面中導入視覺化器
            from src.ui.components.enhanced_data_visualization import EnhancedDataVisualizer
            
            visualizer = EnhancedDataVisualizer()
            assert visualizer is not None
            
        except ImportError as e:
            pytest.fail(f"視覺化器導入失敗: {e}")


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v", "--tb=short"])
