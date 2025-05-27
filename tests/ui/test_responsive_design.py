"""
響應式設計測試

此模組測試響應式設計功能，包括：
- 響應式斷點檢測
- 響應式佈局管理
- 響應式組件渲染
- 跨平台兼容性
"""

import pytest
import streamlit as st
from unittest.mock import Mock, patch
import pandas as pd
from typing import Dict, List, Any

# 導入要測試的模組
from src.ui.responsive import (
    ResponsiveBreakpoints,
    ResponsiveCSS,
    ResponsiveLayoutManager,
    ResponsiveComponents,
    ResponsiveUtils,
    responsive_manager,
)


class TestResponsiveBreakpoints:
    """測試響應式斷點"""

    def test_breakpoint_values(self):
        """測試斷點數值"""
        assert ResponsiveBreakpoints.MOBILE == 768
        assert ResponsiveBreakpoints.TABLET == 1024
        assert ResponsiveBreakpoints.DESKTOP == 1200

    def test_get_breakpoints(self):
        """測試獲取斷點字典"""
        breakpoints = ResponsiveBreakpoints.get_breakpoints()

        assert isinstance(breakpoints, dict)
        assert "mobile" in breakpoints
        assert "tablet" in breakpoints
        assert "desktop" in breakpoints
        assert breakpoints["mobile"] == 768
        assert breakpoints["tablet"] == 1024
        assert breakpoints["desktop"] == 1200


class TestResponsiveCSS:
    """測試響應式 CSS"""

    def test_get_base_styles(self):
        """測試基礎樣式"""
        styles = ResponsiveCSS.get_base_styles()

        assert isinstance(styles, str)
        assert "<style>" in styles
        assert "</style>" in styles
        assert "responsive-container" in styles
        assert "responsive-grid" in styles
        assert "@media" in styles

    def test_get_streamlit_overrides(self):
        """測試 Streamlit 覆蓋樣式"""
        styles = ResponsiveCSS.get_streamlit_overrides()

        assert isinstance(styles, str)
        assert "<style>" in styles
        assert "</style>" in styles
        assert "stButton" in styles
        assert "stDataFrame" in styles
        assert "@media" in styles


class TestResponsiveLayoutManager:
    """測試響應式佈局管理器"""

    def setup_method(self):
        """設置測試環境"""
        self.manager = ResponsiveLayoutManager()

    def test_initialization(self):
        """測試初始化"""
        assert hasattr(self.manager, "current_breakpoint")
        assert hasattr(self.manager, "is_mobile")
        assert hasattr(self.manager, "is_tablet")
        assert hasattr(self.manager, "is_desktop")

    def test_detect_breakpoint_mobile(self):
        """測試手機斷點檢測"""
        with patch("streamlit.session_state", {"screen_width": 500}):
            manager = ResponsiveLayoutManager()
            assert manager.current_breakpoint == "mobile"
            assert manager.is_mobile is True
            assert manager.is_tablet is False
            assert manager.is_desktop is False

    def test_detect_breakpoint_tablet(self):
        """測試平板斷點檢測"""
        with patch("streamlit.session_state", {"screen_width": 900}):
            manager = ResponsiveLayoutManager()
            assert manager.current_breakpoint == "tablet"
            assert manager.is_mobile is False
            assert manager.is_tablet is True
            assert manager.is_desktop is False

    def test_detect_breakpoint_desktop(self):
        """測試桌面斷點檢測"""
        with patch("streamlit.session_state", {"screen_width": 1300}):
            manager = ResponsiveLayoutManager()
            assert manager.current_breakpoint == "desktop"
            assert manager.is_mobile is False
            assert manager.is_tablet is False
            assert manager.is_desktop is True

    def test_get_columns_config(self):
        """測試列數配置"""
        # 測試桌面配置
        with patch("streamlit.session_state", {"screen_width": 1300}):
            manager = ResponsiveLayoutManager()
            cols = manager.get_columns_config(desktop=4, tablet=2, mobile=1)
            assert cols == 4

        # 測試平板配置
        with patch("streamlit.session_state", {"screen_width": 900}):
            manager = ResponsiveLayoutManager()
            cols = manager.get_columns_config(desktop=4, tablet=2, mobile=1)
            assert cols == 2

        # 測試手機配置
        with patch("streamlit.session_state", {"screen_width": 500}):
            manager = ResponsiveLayoutManager()
            cols = manager.get_columns_config(desktop=4, tablet=2, mobile=1)
            assert cols == 1

    @patch("streamlit.columns")
    def test_create_responsive_columns(self, mock_columns):
        """測試創建響應式列"""
        mock_columns.return_value = ["col1", "col2"]

        with patch("streamlit.session_state", {"screen_width": 1300}):
            manager = ResponsiveLayoutManager()
            cols = manager.create_responsive_columns(
                desktop_cols=2, tablet_cols=1, mobile_cols=1
            )

            mock_columns.assert_called_once_with(2)
            assert cols == ["col1", "col2"]

    def test_get_chart_height(self):
        """測試圖表高度配置"""
        # 測試桌面高度
        with patch("streamlit.session_state", {"screen_width": 1300}):
            manager = ResponsiveLayoutManager()
            height = manager.get_chart_height(400)
            assert height == 400

        # 測試平板高度
        with patch("streamlit.session_state", {"screen_width": 900}):
            manager = ResponsiveLayoutManager()
            height = manager.get_chart_height(400)
            assert height == 350

        # 測試手機高度
        with patch("streamlit.session_state", {"screen_width": 500}):
            manager = ResponsiveLayoutManager()
            height = manager.get_chart_height(400)
            assert height == 300

    def test_get_button_config(self):
        """測試按鈕配置"""
        # 測試桌面按鈕配置
        with patch("streamlit.session_state", {"screen_width": 1300}):
            manager = ResponsiveLayoutManager()
            config = manager.get_button_config()
            assert config["use_container_width"] is False
            assert config["type"] == "secondary"

        # 測試手機按鈕配置
        with patch("streamlit.session_state", {"screen_width": 500}):
            manager = ResponsiveLayoutManager()
            config = manager.get_button_config()
            assert config["use_container_width"] is True
            assert config["type"] == "primary"


class TestResponsiveComponents:
    """測試響應式組件"""

    @patch("streamlit.columns")
    @patch("src.ui.components.common.UIComponents.status_card")
    def test_responsive_metric_cards(self, mock_status_card, mock_columns):
        """測試響應式指標卡片"""
        mock_columns.return_value = [Mock(), Mock()]

        metrics = [{"title": "測試1", "value": 100}, {"title": "測試2", "value": 200}]

        ResponsiveComponents.responsive_metric_cards(metrics)

        mock_columns.assert_called_once()
        assert mock_status_card.call_count == 2

    @patch("streamlit.markdown")
    @patch("streamlit.subheader")
    def test_responsive_chart(self, mock_subheader, mock_markdown):
        """測試響應式圖表"""
        mock_chart_func = Mock()
        mock_data = {"test": "data"}

        ResponsiveComponents.responsive_chart(
            mock_chart_func, mock_data, title="測試圖表", height=400
        )

        mock_subheader.assert_called_once_with("測試圖表")
        mock_chart_func.assert_called_once()
        assert mock_markdown.call_count >= 2  # 開始和結束標籤

    @patch("streamlit.subheader")
    @patch("streamlit.dataframe")
    @patch("streamlit.expander")
    def test_responsive_dataframe_desktop(
        self, mock_expander, mock_dataframe, mock_subheader
    ):
        """測試桌面版響應式數據框"""
        with patch("streamlit.session_state", {"screen_width": 1300}):
            df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

            ResponsiveComponents.responsive_dataframe(df, title="測試表格")

            mock_subheader.assert_called_once_with("測試表格")
            mock_dataframe.assert_called_once()
            mock_expander.assert_not_called()

    @patch("streamlit.subheader")
    @patch("streamlit.dataframe")
    @patch("streamlit.expander")
    def test_responsive_dataframe_mobile(
        self, mock_expander, mock_dataframe, mock_subheader
    ):
        """測試手機版響應式數據框"""
        with patch("streamlit.session_state", {"screen_width": 500}):
            df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})

            ResponsiveComponents.responsive_dataframe(df, title="測試表格")

            mock_subheader.assert_called_once_with("測試表格")
            mock_dataframe.assert_not_called()
            assert mock_expander.call_count == 2  # 每行一個 expander


class TestResponsiveUtils:
    """測試響應式工具函數"""

    @patch("streamlit.markdown")
    def test_inject_screen_size_detector(self, mock_markdown):
        """測試注入螢幕尺寸檢測器"""
        ResponsiveUtils.inject_screen_size_detector()

        mock_markdown.assert_called_once()
        args, kwargs = mock_markdown.call_args
        assert "<script>" in args[0]
        assert "updateScreenSize" in args[0]
        assert kwargs.get("unsafe_allow_html") is True

    def test_get_responsive_config(self):
        """測試獲取響應式配置"""
        config = ResponsiveUtils.get_responsive_config()

        assert isinstance(config, dict)
        assert "breakpoints" in config
        assert "current_breakpoint" in config
        assert "is_mobile" in config
        assert "is_tablet" in config
        assert "is_desktop" in config

    @patch("streamlit.set_page_config")
    @patch("src.ui.responsive.responsive_manager.apply_responsive_styles")
    @patch("src.ui.responsive.ResponsiveUtils.inject_screen_size_detector")
    def test_apply_responsive_page_config(
        self, mock_inject, mock_apply_styles, mock_set_config
    ):
        """測試應用響應式頁面配置"""
        ResponsiveUtils.apply_responsive_page_config("測試頁面", "🧪")

        mock_set_config.assert_called_once()
        mock_apply_styles.assert_called_once()
        mock_inject.assert_called_once()


class TestConvenienceFunctions:
    """測試便捷函數"""

    @patch("src.ui.responsive.responsive_manager.apply_responsive_styles")
    def test_apply_responsive_design(self, mock_apply_styles):
        """測試應用響應式設計便捷函數"""
        from src.ui.responsive import apply_responsive_design

        apply_responsive_design()
        mock_apply_styles.assert_called_once()

    def test_get_responsive_columns(self):
        """測試獲取響應式列數便捷函數"""
        from src.ui.responsive import get_responsive_columns

        with patch("streamlit.session_state", {"screen_width": 1300}):
            cols = get_responsive_columns(desktop=4, tablet=2, mobile=1)
            assert cols == 4

    def test_is_mobile_device(self):
        """測試檢查行動裝置便捷函數"""
        from src.ui.responsive import is_mobile_device

        with patch("streamlit.session_state", {"screen_width": 500}):
            assert is_mobile_device() is True

        with patch("streamlit.session_state", {"screen_width": 1300}):
            assert is_mobile_device() is False


class TestIntegration:
    """整合測試"""

    def test_responsive_manager_singleton(self):
        """測試響應式管理器單例"""
        from src.ui.responsive import responsive_manager

        assert responsive_manager is not None
        assert isinstance(responsive_manager, ResponsiveLayoutManager)

    @patch("streamlit.session_state", {"screen_width": 500})
    def test_mobile_workflow(self):
        """測試手機版工作流程"""
        manager = ResponsiveLayoutManager()

        # 檢查斷點檢測
        assert manager.is_mobile is True

        # 檢查列數配置
        cols = manager.get_columns_config(4, 2, 1)
        assert cols == 1

        # 檢查圖表高度
        height = manager.get_chart_height(400)
        assert height == 300

        # 檢查按鈕配置
        button_config = manager.get_button_config()
        assert button_config["use_container_width"] is True

    @patch("streamlit.session_state", {"screen_width": 1300})
    def test_desktop_workflow(self):
        """測試桌面版工作流程"""
        manager = ResponsiveLayoutManager()

        # 檢查斷點檢測
        assert manager.is_desktop is True

        # 檢查列數配置
        cols = manager.get_columns_config(4, 2, 1)
        assert cols == 4

        # 檢查圖表高度
        height = manager.get_chart_height(400)
        assert height == 400

        # 檢查按鈕配置
        button_config = manager.get_button_config()
        assert button_config["use_container_width"] is False


if __name__ == "__main__":
    pytest.main([__file__])
