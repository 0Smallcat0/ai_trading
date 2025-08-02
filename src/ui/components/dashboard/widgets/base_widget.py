"""
基礎小工具類

定義所有儀表板小工具的基礎介面和共用功能。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class WidgetSize:
    """小工具尺寸定義"""

    SMALL = {"width": 2, "height": 2}
    MEDIUM = {"width": 4, "height": 3}
    LARGE = {"width": 6, "height": 4}
    EXTRA_LARGE = {"width": 8, "height": 5}
    FULL_WIDTH = {"width": 12, "height": 3}

    @classmethod
    def get_size_options(cls) -> Dict[str, Dict[str, int]]:
        """獲取尺寸選項

        Returns:
            尺寸選項字典
        """
        return {
            "小": cls.SMALL,
            "中": cls.MEDIUM,
            "大": cls.LARGE,
            "特大": cls.EXTRA_LARGE,
            "全寬": cls.FULL_WIDTH,
        }


class WidgetTheme:
    """小工具主題配置"""

    LIGHT = {
        "background": "#FFFFFF",
        "border": "#E5E5E5",
        "text": "#333333",
        "primary": "#1f77b4",
        "secondary": "#ff7f0e",
        "success": "#2ca02c",
        "danger": "#d62728",
        "warning": "#ff7f0e",
        "shadow": "0 2px 4px rgba(0,0,0,0.1)",
    }

    DARK = {
        "background": "#1E1E1E",
        "border": "#404040",
        "text": "#FFFFFF",
        "primary": "#00D4FF",
        "secondary": "#FF6B35",
        "success": "#00C851",
        "danger": "#FF4444",
        "warning": "#FFBB33",
        "shadow": "0 2px 4px rgba(0,0,0,0.3)",
    }

    @classmethod
    def get_theme(cls, theme_name: str = "light") -> Dict[str, str]:
        """獲取主題配置

        Args:
            theme_name: 主題名稱

        Returns:
            主題配置
        """
        return cls.DARK if theme_name == "dark" else cls.LIGHT


class BaseWidget(ABC):
    """基礎小工具抽象類"""

    def __init__(self, widget_id: str, config: Dict[str, Any] = None):
        """初始化小工具

        Args:
            widget_id: 小工具唯一標識
            config: 小工具配置
        """
        self.widget_id = widget_id
        self.config = config or {}
        self.theme = WidgetTheme.get_theme(self.config.get("theme", "light"))
        self.title = self.config.get("title", self.get_default_title())
        self.show_border = self.config.get("show_border", True)
        self.show_header = self.config.get("show_header", True)
        self.refresh_interval = self.config.get("refresh_interval", 30)
        self.last_update = None

    @abstractmethod
    def get_widget_type(self) -> str:
        """獲取小工具類型

        Returns:
            小工具類型字符串
        """
        pass

    @abstractmethod
    def get_default_title(self) -> str:
        """獲取預設標題

        Returns:
            預設標題
        """
        pass

    @abstractmethod
    def get_default_size(self) -> Dict[str, int]:
        """獲取預設尺寸

        Returns:
            預設尺寸
        """
        pass

    @abstractmethod
    def render_content(self) -> None:
        """渲染小工具內容"""
        pass

    def render(
        self, position: Dict[str, int], size: Dict[str, int], edit_mode: bool = False
    ) -> None:
        """渲染小工具

        Args:
            position: 位置 {x, y}
            size: 尺寸 {width, height}
            edit_mode: 是否為編輯模式
        """
        try:
            # 計算實際尺寸（基於12欄網格）
            actual_width = size["width"] / 12

            # 創建容器
            container_style = self._get_container_style(size, edit_mode)

            with st.container():
                if self.show_border:
                    st.markdown(
                        f"""
                    <div style="{container_style}">
                    """,
                        unsafe_allow_html=True,
                    )

                # 渲染標題
                if self.show_header:
                    self._render_header(edit_mode)

                # 渲染內容
                self.render_content()

                # 渲染編輯控制
                if edit_mode:
                    self._render_edit_controls()

                if self.show_border:
                    st.markdown("</div>", unsafe_allow_html=True)

                # 更新最後更新時間
                self.last_update = datetime.now()

        except Exception as e:
            logger.error(f"渲染小工具 {self.widget_id} 失敗: {e}")
            st.error(f"小工具渲染錯誤: {e}")

    def _get_container_style(self, size: Dict[str, int], edit_mode: bool) -> str:
        """獲取容器樣式

        Args:
            size: 尺寸
            edit_mode: 是否為編輯模式

        Returns:
            CSS 樣式字符串
        """
        border_color = self.theme["primary"] if edit_mode else self.theme["border"]
        border_width = "2px" if edit_mode else "1px"

        return f"""
            background-color: {self.theme["background"]};
            border: {border_width} solid {border_color};
            border-radius: 8px;
            padding: 16px;
            margin: 8px 0;
            box-shadow: {self.theme["shadow"]};
            min-height: {size["height"] * 60}px;
            position: relative;
        """

    def _render_header(self, edit_mode: bool) -> None:
        """渲染標題欄

        Args:
            edit_mode: 是否為編輯模式
        """
        col1, col2 = st.columns([4, 1])

        with col1:
            if edit_mode:
                new_title = st.text_input(
                    "標題",
                    value=self.title,
                    key=f"{self.widget_id}_title",
                    label_visibility="collapsed",
                )
                if new_title != self.title:
                    self.title = new_title
                    self.config["title"] = new_title
            else:
                st.markdown(
                    f"""
                <h4 style="color: {self.theme['text']}; margin: 0 0 16px 0;">
                    {self.title}
                </h4>
                """,
                    unsafe_allow_html=True,
                )

        with col2:
            if edit_mode:
                if st.button("🗑️", key=f"{self.widget_id}_delete", help="刪除小工具"):
                    self._handle_delete()

    def _render_edit_controls(self) -> None:
        """渲染編輯控制"""
        with st.expander("⚙️ 小工具設定", expanded=False):
            # 主題選擇
            theme_options = ["light", "dark"]
            current_theme = self.config.get("theme", "light")

            new_theme = st.selectbox(
                "主題",
                theme_options,
                index=theme_options.index(current_theme),
                key=f"{self.widget_id}_theme",
            )

            if new_theme != current_theme:
                self.config["theme"] = new_theme
                self.theme = WidgetTheme.get_theme(new_theme)

            # 邊框設定
            self.show_border = st.checkbox(
                "顯示邊框", value=self.show_border, key=f"{self.widget_id}_border"
            )
            self.config["show_border"] = self.show_border

            # 標題設定
            self.show_header = st.checkbox(
                "顯示標題", value=self.show_header, key=f"{self.widget_id}_header"
            )
            self.config["show_header"] = self.show_header

            # 刷新間隔
            self.refresh_interval = st.slider(
                "刷新間隔 (秒)",
                min_value=5,
                max_value=300,
                value=self.refresh_interval,
                key=f"{self.widget_id}_refresh",
            )
            self.config["refresh_interval"] = self.refresh_interval

            # 小工具特定設定
            self.render_widget_settings()

    def render_widget_settings(self) -> None:
        """渲染小工具特定設定（子類可覆寫）"""
        pass

    def _handle_delete(self) -> None:
        """處理刪除操作"""
        # 這裡應該觸發父組件的刪除邏輯
        if "widgets_to_delete" not in st.session_state:
            st.session_state.widgets_to_delete = []

        st.session_state.widgets_to_delete.append(self.widget_id)
        st.rerun()

    def get_config(self) -> Dict[str, Any]:
        """獲取小工具配置

        Returns:
            配置字典
        """
        return {
            "title": self.title,
            "theme": self.config.get("theme", "light"),
            "show_border": self.show_border,
            "show_header": self.show_header,
            "refresh_interval": self.refresh_interval,
            **self.config,
        }

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """更新小工具配置

        Args:
            new_config: 新配置
        """
        self.config.update(new_config)
        self.title = self.config.get("title", self.get_default_title())
        self.theme = WidgetTheme.get_theme(self.config.get("theme", "light"))
        self.show_border = self.config.get("show_border", True)
        self.show_header = self.config.get("show_header", True)
        self.refresh_interval = self.config.get("refresh_interval", 30)

    def should_refresh(self) -> bool:
        """檢查是否需要刷新

        Returns:
            是否需要刷新
        """
        if self.last_update is None:
            return True

        elapsed = (datetime.now() - self.last_update).total_seconds()
        return elapsed >= self.refresh_interval

    def get_data_requirements(self) -> List[str]:
        """獲取數據需求（子類可覆寫）

        Returns:
            數據類型列表
        """
        return []

    def validate_config(self) -> Tuple[bool, List[str]]:
        """驗證配置（子類可覆寫）

        Returns:
            (是否有效, 錯誤訊息列表)
        """
        errors = []

        if not isinstance(self.refresh_interval, int) or self.refresh_interval < 5:
            errors.append("刷新間隔必須至少為5秒")

        return len(errors) == 0, errors
