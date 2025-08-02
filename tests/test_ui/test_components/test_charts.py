"""圖表組件單元測試

此模組測試圖表組件的各種功能，包括錯誤處理、配置管理和圖表生成。
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

from src.ui.components.charts import (
    line_chart,
    bar_chart,
    candlestick_chart,
    pie_chart,
    heatmap,
    ChartConfig,
    CandlestickConfig,
    HAS_STREAMLIT,
)


@pytest.fixture
def sample_data():
    """提供測試用的樣本數據"""
    return pd.DataFrame(
        {
            "x": range(10),
            "y": np.random.randn(10),
            "category": ["A", "B"] * 5,
            "value": np.random.randint(1, 100, 10),
        }
    )


@pytest.fixture
def candlestick_data():
    """提供K線圖測試數據"""
    dates = pd.date_range("2023-01-01", periods=10, freq="D")
    return pd.DataFrame(
        {
            "日期": dates,
            "開盤價": np.random.uniform(100, 110, 10),
            "最高價": np.random.uniform(110, 120, 10),
            "最低價": np.random.uniform(90, 100, 10),
            "收盤價": np.random.uniform(100, 110, 10),
            "成交量": np.random.randint(1000, 10000, 10),
        }
    )


@pytest.fixture
def chart_config():
    """提供圖表配置"""
    return ChartConfig(
        title="測試圖表",
        height=500,
        width=800,
        template="plotly_dark",
        show_legend=False,
    )


class TestChartConfig:
    """測試圖表配置類別"""

    def test_chart_config_defaults(self):
        """測試預設配置"""
        config = ChartConfig()
        assert config.title == "圖表"
        assert config.height == 400
        assert config.width is None
        assert config.template == "plotly_white"
        assert config.show_legend is True
        assert config.use_container_width is True

    def test_chart_config_custom(self):
        """測試自定義配置"""
        config = ChartConfig(
            title="自定義圖表",
            height=600,
            width=1000,
            template="plotly_dark",
            show_legend=False,
            use_container_width=False,
        )
        assert config.title == "自定義圖表"
        assert config.height == 600
        assert config.width == 1000
        assert config.template == "plotly_dark"
        assert config.show_legend is False
        assert config.use_container_width is False


class TestCandlestickConfig:
    """測試K線圖配置類別"""

    def test_candlestick_config_defaults(self):
        """測試K線圖預設配置"""
        config = CandlestickConfig()
        assert config.open_col == "開盤價"
        assert config.high_col == "最高價"
        assert config.low_col == "最低價"
        assert config.close_col == "收盤價"
        assert config.date_col == "日期"
        assert config.volume_col is None
        assert config.title == "K線圖"
        assert config.height == 600

    def test_candlestick_config_custom(self):
        """測試自定義K線圖配置"""
        config = CandlestickConfig(
            open_col="open",
            high_col="high",
            low_col="low",
            close_col="close",
            date_col="date",
            volume_col="volume",
            title="自定義K線圖",
            height=800,
        )
        assert config.open_col == "open"
        assert config.high_col == "high"
        assert config.low_col == "low"
        assert config.close_col == "close"
        assert config.date_col == "date"
        assert config.volume_col == "volume"
        assert config.title == "自定義K線圖"
        assert config.height == 800


class TestLineChart:
    """測試折線圖功能"""

    @patch("src.ui.components.charts.st")
    def test_line_chart_basic(self, mock_st, sample_data):
        """測試基本折線圖生成"""
        fig = line_chart(sample_data, x="x", y="y")

        assert fig is not None
        assert fig.data[0].type == "scatter"
        mock_st.plotly_chart.assert_called_once()

    @patch("src.ui.components.charts.st")
    def test_line_chart_with_config(self, mock_st, sample_data, chart_config):
        """測試使用配置的折線圖"""
        fig = line_chart(sample_data, x="x", y="y", config=chart_config)

        assert fig is not None
        assert fig.layout.title.text == "測試圖表"
        assert fig.layout.height == 500
        mock_st.plotly_chart.assert_called_once()

    @patch("src.ui.components.charts.st")
    def test_line_chart_empty_data(self, mock_st):
        """測試空數據錯誤處理"""
        empty_data = pd.DataFrame()

        with pytest.raises(ValueError, match="折線圖生成失敗"):
            line_chart(empty_data)

        mock_st.error.assert_called_once()

    @patch("src.ui.components.charts.st")
    def test_line_chart_multiple_y(self, mock_st, sample_data):
        """測試多Y軸折線圖"""
        sample_data["y2"] = np.random.randn(10)
        fig = line_chart(sample_data, x="x", y=["y", "y2"])

        assert fig is not None
        assert len(fig.data) == 2
        mock_st.plotly_chart.assert_called_once()


class TestBarChart:
    """測試柱狀圖功能"""

    @patch("src.ui.components.charts.st")
    def test_bar_chart_basic(self, mock_st, sample_data):
        """測試基本柱狀圖生成"""
        fig = bar_chart(sample_data, x="category", y="value")

        assert fig is not None
        assert fig.data[0].type == "bar"
        mock_st.plotly_chart.assert_called_once()

    @patch("src.ui.components.charts.st")
    def test_bar_chart_with_color(self, mock_st, sample_data):
        """測試帶顏色的柱狀圖"""
        fig = bar_chart(sample_data, x="category", y="value", color="category")

        assert fig is not None
        mock_st.plotly_chart.assert_called_once()

    @patch("src.ui.components.charts.st")
    def test_bar_chart_empty_data(self, mock_st):
        """測試空數據錯誤處理"""
        empty_data = pd.DataFrame()

        with pytest.raises(ValueError, match="柱狀圖生成失敗"):
            bar_chart(empty_data)

        mock_st.error.assert_called_once()


class TestCandlestickChart:
    """測試K線圖功能"""

    @patch("src.ui.components.charts.st")
    def test_candlestick_chart_basic(self, mock_st, candlestick_data):
        """測試基本K線圖生成"""
        fig = candlestick_chart(candlestick_data)

        assert fig is not None
        assert fig.data[0].type == "candlestick"
        mock_st.plotly_chart.assert_called_once()

    @patch("src.ui.components.charts.st")
    def test_candlestick_chart_with_volume(self, mock_st, candlestick_data):
        """測試帶成交量的K線圖"""
        config = CandlestickConfig(volume_col="成交量")
        fig = candlestick_chart(candlestick_data, config=config)

        assert fig is not None
        assert len(fig.data) == 2  # K線 + 成交量
        mock_st.plotly_chart.assert_called_once()

    @patch("src.ui.components.charts.st")
    def test_candlestick_chart_missing_columns(self, mock_st):
        """測試缺少必要欄位的錯誤處理"""
        incomplete_data = pd.DataFrame({"日期": ["2023-01-01"]})

        with pytest.raises(ValueError, match="K線圖生成失敗"):
            candlestick_chart(incomplete_data)

        mock_st.error.assert_called_once()

    @patch("src.ui.components.charts.st")
    def test_candlestick_chart_empty_data(self, mock_st):
        """測試空數據錯誤處理"""
        empty_data = pd.DataFrame()

        with pytest.raises(ValueError, match="K線圖生成失敗"):
            candlestick_chart(empty_data)

        mock_st.error.assert_called_once()


class TestPieChart:
    """測試圓餅圖功能"""

    @patch("src.ui.components.charts.st")
    def test_pie_chart_basic(self, mock_st, sample_data):
        """測試基本圓餅圖生成"""
        fig = pie_chart(sample_data, names="category", values="value")

        assert fig is not None
        assert fig.data[0].type == "pie"
        mock_st.plotly_chart.assert_called_once()

    @patch("src.ui.components.charts.st")
    def test_pie_chart_empty_data(self, mock_st):
        """測試空數據錯誤處理"""
        empty_data = pd.DataFrame()

        with pytest.raises(ValueError, match="圓餅圖生成失敗"):
            pie_chart(empty_data)

        mock_st.error.assert_called_once()


class TestHeatmap:
    """測試熱力圖功能"""

    @patch("src.ui.components.charts.st")
    def test_heatmap_basic(self, mock_st):
        """測試基本熱力圖生成"""
        data = pd.DataFrame(np.random.randn(5, 5))
        fig = heatmap(data)

        assert fig is not None
        mock_st.plotly_chart.assert_called_once()

    @patch("src.ui.components.charts.st")
    def test_heatmap_empty_data(self, mock_st):
        """測試空數據錯誤處理"""
        empty_data = pd.DataFrame()

        with pytest.raises(ValueError, match="熱力圖生成失敗"):
            heatmap(empty_data)

        mock_st.error.assert_called_once()


class TestErrorHandling:
    """測試錯誤處理機制"""

    @patch("src.ui.components.charts.st")
    @patch("src.ui.components.charts.px.line")
    def test_exception_chaining(self, mock_px_line, mock_st, sample_data):
        """測試異常鏈接（'from e' 語法）"""
        # 模擬 plotly 拋出異常
        mock_px_line.side_effect = Exception("Plotly error")

        with pytest.raises(ValueError, match="折線圖生成失敗") as exc_info:
            line_chart(sample_data, x="x", y="y")

        # 驗證異常鏈接
        assert exc_info.value.__cause__ is not None
        assert str(exc_info.value.__cause__) == "Plotly error"
        mock_st.error.assert_called_once()


class TestStreamlitIntegration:
    """測試 Streamlit 整合"""

    def test_has_streamlit_flag(self):
        """測試 Streamlit 可用性標誌"""
        assert isinstance(HAS_STREAMLIT, bool)

    @patch("src.ui.components.charts.st")
    def test_streamlit_mock_functionality(self, mock_st, sample_data):
        """測試 Streamlit 模擬功能"""
        # 即使在沒有 streamlit 的環境中，函數也應該正常工作
        fig = line_chart(sample_data, x="x", y="y")
        assert fig is not None
        mock_st.plotly_chart.assert_called_once()
