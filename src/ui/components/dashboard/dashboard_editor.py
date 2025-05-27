"""
儀表板編輯器

提供拖拽式儀表板編輯功能，包含組件庫、佈局管理、配置面板等。
"""

import streamlit as st
import uuid
from typing import Dict, List, Any, Optional
import logging

from .grid_layout import GridLayout, GridPosition
from .widget_library import widget_library
from src.ui.utils.dashboard_manager import dashboard_manager, DashboardConfig

logger = logging.getLogger(__name__)


class DashboardEditor:
    """儀表板編輯器類"""

    def __init__(self):
        """初始化儀表板編輯器"""
        self.grid_layout = GridLayout()
        self.edit_mode = False
        self.selected_widget = None
        self.show_grid = True

        # 初始化 session state
        if "dashboard_editor_state" not in st.session_state:
            st.session_state.dashboard_editor_state = {
                "current_dashboard": None,
                "unsaved_changes": False,
                "widget_counter": 0,
            }

    def render_editor(self, dashboard_config: Optional[DashboardConfig] = None) -> None:
        """渲染儀表板編輯器

        Args:
            dashboard_config: 儀表板配置
        """
        # 載入儀表板配置
        if dashboard_config:
            self._load_dashboard_config(dashboard_config)

        # 渲染編輯器界面
        self._render_editor_header()

        # 主要編輯區域
        col1, col2 = st.columns([3, 1])

        with col1:
            self._render_dashboard_canvas()

        with col2:
            self._render_editor_sidebar()

    def _render_editor_header(self) -> None:
        """渲染編輯器標題欄"""
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

        with col1:
            st.subheader("🎨 儀表板編輯器")

        with col2:
            self.edit_mode = st.toggle("編輯模式", value=self.edit_mode)

        with col3:
            if st.button("💾 儲存", type="primary"):
                self._save_dashboard()

        with col4:
            if st.button("👁️ 預覽"):
                self.edit_mode = False
                st.rerun()

    def _render_dashboard_canvas(self) -> None:
        """渲染儀表板畫布"""
        # 顯示網格覆蓋層
        if self.edit_mode and self.show_grid:
            self.grid_layout.render_grid_overlay(True)

        # 獲取當前儀表板配置
        current_config = st.session_state.dashboard_editor_state.get(
            "current_dashboard"
        )

        if current_config and current_config.widgets:
            self._render_widgets(current_config.widgets)
        else:
            # 空儀表板提示
            st.info("🎯 點擊右側組件庫添加小工具到儀表板")

    def _render_widgets(self, widgets: List[Dict[str, Any]]) -> None:
        """渲染小工具

        Args:
            widgets: 小工具列表
        """
        # 按 z_index 排序
        sorted_widgets = sorted(widgets, key=lambda w: w.get("z_index", 0))

        for widget_data in sorted_widgets:
            widget_id = widget_data["id"]
            widget_type = widget_data["type"]
            position = widget_data["position"]
            size = widget_data["size"]
            config = widget_data.get("config", {})

            # 創建小工具實例
            widget = widget_library.create_widget(widget_type, widget_id, config)

            if widget:
                # 創建小工具容器
                with st.container():
                    # 渲染小工具
                    widget.render(position, size, self.edit_mode)

                    # 編輯模式下的額外控制
                    if self.edit_mode:
                        self._render_widget_controls(widget_id, widget_data)

    def _render_widget_controls(
        self, widget_id: str, widget_data: Dict[str, Any]
    ) -> None:
        """渲染小工具控制項

        Args:
            widget_id: 小工具ID
            widget_data: 小工具數據
        """
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("⬆️", key=f"{widget_id}_up", help="向上移動"):
                self._move_widget(widget_id, 0, -1)

        with col2:
            if st.button("⬇️", key=f"{widget_id}_down", help="向下移動"):
                self._move_widget(widget_id, 0, 1)

        with col3:
            if st.button("⬅️", key=f"{widget_id}_left", help="向左移動"):
                self._move_widget(widget_id, -1, 0)

        with col4:
            if st.button("➡️", key=f"{widget_id}_right", help="向右移動"):
                self._move_widget(widget_id, 1, 0)

    def _render_editor_sidebar(self) -> None:
        """渲染編輯器側邊欄"""
        # 儀表板設定
        with st.expander("⚙️ 儀表板設定", expanded=True):
            self._render_dashboard_settings()

        # 組件庫
        with st.expander("📦 組件庫", expanded=True):
            self._render_widget_library()

        # 佈局設定
        with st.expander("📐 佈局設定", expanded=False):
            self._render_layout_settings()

        # 已添加的小工具
        with st.expander("📋 小工具列表", expanded=False):
            self._render_widget_list()

    def _render_dashboard_settings(self) -> None:
        """渲染儀表板設定"""
        current_config = st.session_state.dashboard_editor_state.get(
            "current_dashboard"
        )

        if current_config:
            # 儀表板名稱
            new_name = st.text_input(
                "儀表板名稱", value=current_config.name, key="dashboard_name"
            )

            if new_name != current_config.name:
                current_config.name = new_name
                self._mark_unsaved_changes()

            # 描述
            new_description = st.text_area(
                "描述", value=current_config.description, key="dashboard_description"
            )

            if new_description != current_config.description:
                current_config.description = new_description
                self._mark_unsaved_changes()

            # 主題
            theme_options = ["light", "dark"]
            current_theme = current_config.theme

            new_theme = st.selectbox(
                "主題",
                theme_options,
                index=theme_options.index(current_theme),
                key="dashboard_theme",
            )

            if new_theme != current_theme:
                current_config.theme = new_theme
                self._mark_unsaved_changes()

            # 自動刷新
            auto_refresh = st.checkbox(
                "自動刷新",
                value=current_config.auto_refresh,
                key="dashboard_auto_refresh",
            )

            if auto_refresh != current_config.auto_refresh:
                current_config.auto_refresh = auto_refresh
                self._mark_unsaved_changes()

            # 刷新間隔
            if auto_refresh:
                refresh_interval = st.slider(
                    "刷新間隔 (秒)",
                    min_value=5,
                    max_value=300,
                    value=current_config.refresh_interval,
                    key="dashboard_refresh_interval",
                )

                if refresh_interval != current_config.refresh_interval:
                    current_config.refresh_interval = refresh_interval
                    self._mark_unsaved_changes()

    def _render_widget_library(self) -> None:
        """渲染組件庫"""
        # 搜尋框
        search_query = st.text_input("🔍 搜尋組件", key="widget_search")

        if search_query:
            widgets = widget_library.search_widgets(search_query)
            st.write("搜尋結果:")
            for widget_info in widgets:
                self._render_widget_item(widget_info)
        else:
            # 按分類顯示
            categories = widget_library.get_widget_categories()

            for category in categories:
                st.write(f"**{category}**")
                widgets = widget_library.get_widgets_by_category(category)

                for widget_info in widgets:
                    self._render_widget_item(widget_info)

    def _render_widget_item(self, widget_info: Dict[str, Any]) -> None:
        """渲染組件項目

        Args:
            widget_info: 組件資訊
        """
        col1, col2 = st.columns([3, 1])

        with col1:
            st.write(f"📊 {widget_info['name']}")
            st.caption(f"類型: {widget_info['type']}")

        with col2:
            if st.button("➕", key=f"add_{widget_info['type']}", help="添加到儀表板"):
                self._add_widget_to_dashboard(widget_info)

    def _render_layout_settings(self) -> None:
        """渲染佈局設定"""
        # 顯示網格
        self.show_grid = st.checkbox("顯示網格", value=self.show_grid)

        # 自動排列
        auto_arrange = st.checkbox("自動排列", value=self.grid_layout.auto_arrange)
        self.grid_layout.auto_arrange = auto_arrange

        # 磁吸網格
        snap_to_grid = st.checkbox("磁吸網格", value=self.grid_layout.snap_to_grid)
        self.grid_layout.snap_to_grid = snap_to_grid

        # 壓縮佈局
        if st.button("🗜️ 壓縮佈局"):
            self.grid_layout.compact_layout()
            self._mark_unsaved_changes()

    def _render_widget_list(self) -> None:
        """渲染小工具列表"""
        current_config = st.session_state.dashboard_editor_state.get(
            "current_dashboard"
        )

        if current_config and current_config.widgets:
            for widget_data in current_config.widgets:
                widget_id = widget_data["id"]
                widget_type = widget_data["type"]

                col1, col2 = st.columns([3, 1])

                with col1:
                    widget_info = widget_library.get_widget_info(widget_type)
                    widget_name = widget_info["name"] if widget_info else widget_type
                    st.write(f"📊 {widget_name}")

                with col2:
                    if st.button("🗑️", key=f"delete_{widget_id}", help="刪除"):
                        self._remove_widget_from_dashboard(widget_id)
        else:
            st.info("尚未添加任何小工具")

    def _add_widget_to_dashboard(self, widget_info: Dict[str, Any]) -> None:
        """添加小工具到儀表板

        Args:
            widget_info: 小工具資訊
        """
        current_config = st.session_state.dashboard_editor_state.get(
            "current_dashboard"
        )

        if not current_config:
            # 創建新儀表板
            current_config = dashboard_manager.create_dashboard("新儀表板")
            st.session_state.dashboard_editor_state["current_dashboard"] = (
                current_config
            )

        # 生成小工具ID
        widget_counter = st.session_state.dashboard_editor_state["widget_counter"]
        widget_id = f"widget_{widget_counter}"
        st.session_state.dashboard_editor_state["widget_counter"] = widget_counter + 1

        # 獲取預設尺寸和位置
        default_size = widget_info["default_size"]
        position = self._find_available_position(default_size)

        # 添加小工具到配置
        current_config.add_widget(widget_info["type"], position, default_size, {})

        self._mark_unsaved_changes()
        st.success(f"已添加 {widget_info['name']} 到儀表板")
        st.rerun()

    def _remove_widget_from_dashboard(self, widget_id: str) -> None:
        """從儀表板移除小工具

        Args:
            widget_id: 小工具ID
        """
        current_config = st.session_state.dashboard_editor_state.get(
            "current_dashboard"
        )

        if current_config:
            if current_config.remove_widget(widget_id):
                self._mark_unsaved_changes()
                st.success("已移除小工具")
                st.rerun()

    def _move_widget(self, widget_id: str, dx: int, dy: int) -> None:
        """移動小工具

        Args:
            widget_id: 小工具ID
            dx: X方向偏移
            dy: Y方向偏移
        """
        current_config = st.session_state.dashboard_editor_state.get(
            "current_dashboard"
        )

        if current_config:
            # 找到小工具
            for widget_data in current_config.widgets:
                if widget_data["id"] == widget_id:
                    position = widget_data["position"]
                    new_position = {
                        "x": max(0, min(11, position["x"] + dx)),
                        "y": max(0, position["y"] + dy),
                    }

                    widget_data["position"] = new_position
                    self._mark_unsaved_changes()
                    st.rerun()
                    break

    def _find_available_position(self, size: Dict[str, int]) -> Dict[str, int]:
        """尋找可用位置

        Args:
            size: 小工具尺寸

        Returns:
            可用位置
        """
        current_config = st.session_state.dashboard_editor_state.get(
            "current_dashboard"
        )

        if not current_config or not current_config.widgets:
            return {"x": 0, "y": 0}

        # 簡單的位置分配邏輯
        max_y = max(
            w["position"]["y"] + w["size"]["height"] for w in current_config.widgets
        )

        return {"x": 0, "y": max_y}

    def _load_dashboard_config(self, config: DashboardConfig) -> None:
        """載入儀表板配置

        Args:
            config: 儀表板配置
        """
        st.session_state.dashboard_editor_state["current_dashboard"] = config
        st.session_state.dashboard_editor_state["unsaved_changes"] = False

    def _save_dashboard(self) -> None:
        """儲存儀表板"""
        current_config = st.session_state.dashboard_editor_state.get(
            "current_dashboard"
        )

        if current_config:
            if dashboard_manager.save_dashboard(current_config):
                st.session_state.dashboard_editor_state["unsaved_changes"] = False
                st.success("儀表板已儲存")
            else:
                st.error("儲存失敗")

    def _mark_unsaved_changes(self) -> None:
        """標記未儲存變更"""
        st.session_state.dashboard_editor_state["unsaved_changes"] = True
