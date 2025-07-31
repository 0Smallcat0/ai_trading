"""
互動式圖表組件測試

測試 Plotly 互動式圖表功能和組件。
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加專案根目錄到 Python 路徑
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ui.components.interactive_charts import (
    ChartTheme,
    InteractiveChartManager,
    create_enhanced_candlestick_chart,
    create_correlation_heatmap,
    create_performance_comparison_chart,
    create_volume_profile_chart,
    generate_sample_stock_data,
    calculate_rsi,
    create_advanced_technical_indicators,
    chart_manager,
)


class TestChartTheme(unittest.TestCase):
    """測試圖表主題類"""

    def test_theme_structure(self):
        """測試主題結構"""
        for theme_name, theme_config in ChartTheme.THEMES.items():
            self.assertIsInstance(theme_name, str)
            self.assertIsInstance(theme_config, dict)

            # 檢查必要的顏色配置
            required_colors = [
                "background",
                "grid",
                "text",
                "primary",
                "secondary",
                "success",
                "danger",
                "warning",
            ]

            for color in required_colors:
                self.assertIn(color, theme_config)
                self.assertIsInstance(theme_config[color], str)
                self.assertTrue(theme_config[color].startswith("#"))

    def test_get_theme(self):
        """測試獲取主題"""
        # 測試有效主題
        light_theme = ChartTheme.get_theme("light")
        self.assertIsInstance(light_theme, dict)
        self.assertEqual(light_theme["background"], "#FFFFFF")

        # 測試無效主題（應返回預設主題）
        invalid_theme = ChartTheme.get_theme("invalid")
        self.assertEqual(invalid_theme, ChartTheme.THEMES["light"])

    def test_all_themes_available(self):
        """測試所有主題都可用"""
        expected_themes = ["light", "dark", "professional"]

        for theme_name in expected_themes:
            self.assertIn(theme_name, ChartTheme.THEMES)
            theme = ChartTheme.get_theme(theme_name)
            self.assertIsInstance(theme, dict)


class TestInteractiveChartManager(unittest.TestCase):
    """測試互動式圖表管理器"""

    def setUp(self):
        """設置測試環境"""
        self.manager = InteractiveChartManager()

    def test_initialization(self):
        """測試初始化"""
        self.assertIsInstance(self.manager.chart_registry, dict)
        self.assertIsInstance(self.manager.chart_links, dict)
        self.assertIsInstance(self.manager.selected_data, dict)
        self.assertEqual(len(self.manager.chart_registry), 0)

    def test_register_chart(self):
        """測試註冊圖表"""
        chart_id = "test_chart"
        chart_type = "candlestick"
        data_source = "test_data"

        self.manager.register_chart(chart_id, chart_type, data_source)

        # 檢查圖表是否已註冊
        self.assertIn(chart_id, self.manager.chart_registry)
        self.assertIn(chart_id, self.manager.chart_links)

        chart_info = self.manager.chart_registry[chart_id]
        self.assertEqual(chart_info["type"], chart_type)
        self.assertEqual(chart_info["data_source"], data_source)
        self.assertIsInstance(chart_info["last_update"], datetime)

    def test_link_charts(self):
        """測試圖表聯動"""
        source_chart = "source"
        target_charts = ["target1", "target2"]

        # 先註冊源圖表
        self.manager.register_chart(source_chart, "line", "data")

        # 建立聯動關係
        self.manager.link_charts(source_chart, target_charts)

        self.assertEqual(self.manager.chart_links[source_chart], target_charts)

    def test_update_chart_selection(self):
        """測試更新圖表選擇"""
        chart_id = "test_chart"
        selected_data = {"x": [1, 2, 3], "y": [4, 5, 6]}

        self.manager.update_chart_selection(chart_id, selected_data)

        self.assertEqual(self.manager.selected_data[chart_id], selected_data)

    def test_chart_callback_execution(self):
        """測試圖表回調執行"""
        source_chart = "source"
        target_chart = "target"

        # 創建模擬回調
        callback = Mock()

        # 註冊圖表
        self.manager.register_chart(source_chart, "line", "data")
        self.manager.register_chart(target_chart, "bar", "data", callback)

        # 建立聯動
        self.manager.link_charts(source_chart, [target_chart])

        # 更新選擇（應觸發回調）
        test_data = {"selection": "test"}
        self.manager.update_chart_selection(source_chart, test_data)

        # 檢查回調是否被調用
        callback.assert_called_once_with(test_data)


class TestDataGeneration(unittest.TestCase):
    """測試數據生成功能"""

    def test_generate_sample_stock_data(self):
        """測試生成模擬股價數據"""
        symbol = "TEST.TW"
        days = 100
        start_price = 500.0

        data = generate_sample_stock_data(symbol, days, start_price)

        # 檢查數據結構
        self.assertIsInstance(data, pd.DataFrame)
        self.assertEqual(len(data), days)

        # 檢查必要欄位
        required_columns = ["open", "high", "low", "close", "volume"]
        for col in required_columns:
            self.assertIn(col, data.columns)

        # 檢查數據合理性
        self.assertTrue((data["high"] >= data["low"]).all())
        self.assertTrue((data["high"] >= data["open"]).all())
        self.assertTrue((data["high"] >= data["close"]).all())
        self.assertTrue((data["low"] <= data["open"]).all())
        self.assertTrue((data["low"] <= data["close"]).all())
        self.assertTrue((data["volume"] > 0).all())

        # 檢查起始價格
        self.assertAlmostEqual(data["close"].iloc[0], start_price, places=0)

    def test_calculate_rsi(self):
        """測試 RSI 計算"""
        # 創建測試數據
        prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109])

        rsi = calculate_rsi(prices, window=5)

        # 檢查結果
        self.assertIsInstance(rsi, pd.Series)
        self.assertEqual(len(rsi), len(prices))

        # RSI 應該在 0-100 之間
        valid_rsi = rsi.dropna()
        self.assertTrue((valid_rsi >= 0).all())
        self.assertTrue((valid_rsi <= 100).all())

    def test_create_advanced_technical_indicators(self):
        """測試進階技術指標計算"""
        # 生成測試數據
        data = generate_sample_stock_data(days=100)

        indicators = create_advanced_technical_indicators(data)

        # 檢查指標類型
        self.assertIsInstance(indicators, dict)

        # 檢查必要指標
        expected_indicators = [
            "macd",
            "macd_signal",
            "macd_histogram",
            "bb_upper",
            "bb_middle",
            "bb_lower",
            "k",
            "d",
        ]

        for indicator in expected_indicators:
            self.assertIn(indicator, indicators)
            self.assertIsInstance(indicators[indicator], pd.Series)

        # 檢查布林通道關係
        bb_data = indicators["bb_upper"].dropna()
        bb_middle = indicators["bb_middle"].dropna()
        bb_lower = indicators["bb_lower"].dropna()

        # 確保上軌 > 中軌 > 下軌
        min_len = min(len(bb_data), len(bb_middle), len(bb_lower))
        if min_len > 0:
            self.assertTrue(
                (bb_data.iloc[-min_len:] >= bb_middle.iloc[-min_len:]).all()
            )
            self.assertTrue(
                (bb_middle.iloc[-min_len:] >= bb_lower.iloc[-min_len:]).all()
            )


class TestChartCreation(unittest.TestCase):
    """測試圖表創建功能"""

    def setUp(self):
        """設置測試環境"""
        self.test_data = generate_sample_stock_data(days=50)

    @patch("streamlit.session_state")
    def test_create_enhanced_candlestick_chart(self, mock_session_state):
        """測試創建增強K線圖"""
        # 模擬 session state
        mock_session_state.chart_config = {"theme": "light", "enable_zoom": True}

        fig = create_enhanced_candlestick_chart(
            data=self.test_data, chart_id="test_candlestick", title="測試K線圖"
        )

        # 檢查圖表對象
        self.assertIsNotNone(fig)
        self.assertTrue(hasattr(fig, "data"))
        self.assertTrue(hasattr(fig, "layout"))

        # 檢查是否有K線數據
        self.assertGreater(len(fig.data), 0)

        # 檢查圖表是否已註冊
        self.assertIn("test_candlestick", chart_manager.chart_registry)

    @patch("streamlit.session_state")
    def test_create_correlation_heatmap(self, mock_session_state):
        """測試創建相關性熱力圖"""
        mock_session_state.chart_config = {"theme": "light"}

        # 創建測試數據
        test_data = pd.DataFrame(
            {
                "A": np.random.randn(100),
                "B": np.random.randn(100),
                "C": np.random.randn(100),
            }
        )

        fig = create_correlation_heatmap(
            data=test_data, chart_id="test_heatmap", title="測試熱力圖"
        )

        self.assertIsNotNone(fig)
        self.assertTrue(hasattr(fig, "data"))
        self.assertGreater(len(fig.data), 0)

    @patch("streamlit.session_state")
    def test_create_performance_comparison_chart(self, mock_session_state):
        """測試創建績效比較圖"""
        mock_session_state.chart_config = {"theme": "light"}

        # 創建測試數據
        test_data = {
            "Stock A": pd.Series(np.random.randn(100).cumsum() + 100),
            "Stock B": pd.Series(np.random.randn(100).cumsum() + 100),
        }

        fig = create_performance_comparison_chart(
            data=test_data, chart_id="test_performance", title="測試績效比較"
        )

        self.assertIsNotNone(fig)
        self.assertTrue(hasattr(fig, "data"))
        self.assertGreaterEqual(len(fig.data), 2)  # 至少兩條線

    @patch("streamlit.session_state")
    def test_create_volume_profile_chart(self, mock_session_state):
        """測試創建成交量分佈圖"""
        mock_session_state.chart_config = {"theme": "light"}

        fig = create_volume_profile_chart(
            data=self.test_data, chart_id="test_volume_profile", title="測試成交量分佈"
        )

        self.assertIsNotNone(fig)
        self.assertTrue(hasattr(fig, "data"))
        self.assertGreater(len(fig.data), 0)


class TestChartIntegration(unittest.TestCase):
    """測試圖表整合功能"""

    def test_chart_manager_singleton(self):
        """測試圖表管理器單例"""
        # chart_manager 應該是全域單例
        from src.ui.components.interactive_charts import chart_manager as manager1
        from src.ui.components.interactive_charts import chart_manager as manager2

        self.assertIs(manager1, manager2)

    def test_chart_registration_persistence(self):
        """測試圖表註冊持久性"""
        chart_id = "persistent_chart"

        # 註冊圖表
        chart_manager.register_chart(chart_id, "line", "test_data")

        # 檢查註冊是否持久
        self.assertIn(chart_id, chart_manager.chart_registry)

        # 清理
        if chart_id in chart_manager.chart_registry:
            del chart_manager.chart_registry[chart_id]
        if chart_id in chart_manager.chart_links:
            del chart_manager.chart_links[chart_id]


class TestErrorHandling(unittest.TestCase):
    """測試錯誤處理"""

    def test_invalid_data_handling(self):
        """測試無效數據處理"""
        # 測試空數據
        empty_data = pd.DataFrame()

        # 這些函數應該能處理空數據而不崩潰
        try:
            rsi = calculate_rsi(pd.Series([]), window=14)
            self.assertTrue(rsi.empty)
        except Exception as e:
            self.fail(f"calculate_rsi 無法處理空數據: {e}")

    def test_invalid_parameters(self):
        """測試無效參數處理"""
        # 測試無效主題
        invalid_theme = ChartTheme.get_theme("nonexistent")
        self.assertEqual(invalid_theme, ChartTheme.THEMES["light"])

        # 測試無效窗口大小
        prices = pd.Series([1, 2, 3, 4, 5])
        rsi = calculate_rsi(prices, window=10)  # 窗口大於數據長度
        self.assertIsInstance(rsi, pd.Series)


if __name__ == "__main__":
    # 運行測試
    unittest.main(verbosity=2)
