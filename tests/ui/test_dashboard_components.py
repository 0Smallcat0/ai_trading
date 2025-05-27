"""
自定義儀表板組件測試

測試儀表板管理器、小工具庫、網格佈局等核心功能。
"""

import unittest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加專案根目錄到 Python 路徑
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ui.utils.dashboard_manager import DashboardConfig, DashboardManager
from src.ui.components.dashboard.widget_library import WidgetLibrary
from src.ui.components.dashboard.grid_layout import GridLayout, GridPosition
from src.ui.components.dashboard.widgets.base_widget import (
    BaseWidget,
    WidgetSize,
    WidgetTheme,
)


class TestDashboardConfig(unittest.TestCase):
    """測試儀表板配置類"""

    def setUp(self):
        """設置測試環境"""
        self.config = DashboardConfig(name="測試儀表板", description="測試用儀表板")

    def test_initialization(self):
        """測試初始化"""
        self.assertEqual(self.config.name, "測試儀表板")
        self.assertEqual(self.config.description, "測試用儀表板")
        self.assertEqual(self.config.template_type, "custom")
        self.assertEqual(self.config.version, "1.0.0")
        self.assertIsInstance(self.config.widgets, list)
        self.assertEqual(len(self.config.widgets), 0)

    def test_add_widget(self):
        """測試添加小工具"""
        widget_id = self.config.add_widget(
            "stock_price_card",
            {"x": 0, "y": 0},
            {"width": 3, "height": 2},
            {"symbol": "2330.TW"},
        )

        self.assertIsInstance(widget_id, str)
        self.assertEqual(len(self.config.widgets), 1)

        widget = self.config.widgets[0]
        self.assertEqual(widget["type"], "stock_price_card")
        self.assertEqual(widget["position"], {"x": 0, "y": 0})
        self.assertEqual(widget["size"], {"width": 3, "height": 2})
        self.assertEqual(widget["config"], {"symbol": "2330.TW"})

    def test_remove_widget(self):
        """測試移除小工具"""
        widget_id = self.config.add_widget(
            "test_widget", {"x": 0, "y": 0}, {"width": 1, "height": 1}
        )

        # 移除存在的小工具
        result = self.config.remove_widget(widget_id)
        self.assertTrue(result)
        self.assertEqual(len(self.config.widgets), 0)

        # 移除不存在的小工具
        result = self.config.remove_widget("nonexistent")
        self.assertFalse(result)

    def test_update_widget(self):
        """測試更新小工具"""
        widget_id = self.config.add_widget(
            "test_widget", {"x": 0, "y": 0}, {"width": 1, "height": 1}
        )

        # 更新存在的小工具
        result = self.config.update_widget(widget_id, {"position": {"x": 1, "y": 1}})
        self.assertTrue(result)

        widget = self.config.get_widget(widget_id)
        self.assertEqual(widget["position"], {"x": 1, "y": 1})

        # 更新不存在的小工具
        result = self.config.update_widget(
            "nonexistent", {"position": {"x": 2, "y": 2}}
        )
        self.assertFalse(result)

    def test_get_widget(self):
        """測試獲取小工具"""
        widget_id = self.config.add_widget(
            "test_widget", {"x": 0, "y": 0}, {"width": 1, "height": 1}
        )

        # 獲取存在的小工具
        widget = self.config.get_widget(widget_id)
        self.assertIsNotNone(widget)
        self.assertEqual(widget["id"], widget_id)

        # 獲取不存在的小工具
        widget = self.config.get_widget("nonexistent")
        self.assertIsNone(widget)

    def test_to_dict_and_from_dict(self):
        """測試序列化和反序列化"""
        # 添加一些小工具
        self.config.add_widget("widget1", {"x": 0, "y": 0}, {"width": 2, "height": 2})
        self.config.add_widget("widget2", {"x": 2, "y": 0}, {"width": 3, "height": 2})

        # 轉換為字典
        config_dict = self.config.to_dict()
        self.assertIsInstance(config_dict, dict)
        self.assertEqual(config_dict["name"], "測試儀表板")
        self.assertEqual(len(config_dict["widgets"]), 2)

        # 從字典創建配置
        new_config = DashboardConfig.from_dict(config_dict)
        self.assertEqual(new_config.name, self.config.name)
        self.assertEqual(new_config.description, self.config.description)
        self.assertEqual(len(new_config.widgets), len(self.config.widgets))

    def test_validate(self):
        """測試配置驗證"""
        # 有效配置
        is_valid, errors = self.config.validate()
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

        # 無效配置 - 空名稱
        self.config.name = ""
        is_valid, errors = self.config.validate()
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

        # 恢復有效名稱
        self.config.name = "測試儀表板"

        # 添加無效小工具
        self.config.widgets.append(
            {
                "id": "",  # 無效ID
                "type": "",  # 無效類型
                "position": {"x": -1, "y": -1},  # 無效位置
                "size": {"width": 0, "height": 0},  # 無效尺寸
            }
        )

        is_valid, errors = self.config.validate()
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)


class TestDashboardManager(unittest.TestCase):
    """測試儀表板管理器"""

    def setUp(self):
        """設置測試環境"""
        # 模擬 streamlit session state
        self.mock_session_state = {}

        with patch("streamlit.session_state", self.mock_session_state):
            self.manager = DashboardManager()

    def test_initialization(self):
        """測試初始化"""
        self.assertIsInstance(self.manager.storage_key, str)
        self.assertIsInstance(self.manager.history_key, str)
        self.assertEqual(self.manager.max_history, 5)

    @patch("streamlit.session_state")
    def test_create_dashboard(self, mock_session_state):
        """測試創建儀表板"""
        mock_session_state.__getitem__ = lambda key: {}
        mock_session_state.__setitem__ = lambda key, value: None
        mock_session_state.__contains__ = lambda key: True

        config = self.manager.create_dashboard("測試儀表板", "測試描述")

        self.assertIsInstance(config, DashboardConfig)
        self.assertEqual(config.name, "測試儀表板")
        self.assertEqual(config.description, "測試描述")

    def test_save_and_load_dashboard(self):
        """測試儲存和載入儀表板"""
        # 直接使用字典模擬 session_state
        with patch(
            "streamlit.session_state",
            {
                "dashboard_configs": {},
                "dashboard_history": {},
                "current_dashboard": None,
            },
        ):
            # 創建和儲存儀表板
            config = DashboardConfig(name="測試儀表板")
            result = self.manager.save_dashboard(config)
            self.assertTrue(result)

            # 載入儀表板
            loaded_config = self.manager.load_dashboard(config.config_id)
            self.assertIsNotNone(loaded_config)
            self.assertEqual(loaded_config.name, config.name)
            self.assertEqual(loaded_config.config_id, config.config_id)


class TestWidgetLibrary(unittest.TestCase):
    """測試小工具庫"""

    def setUp(self):
        """設置測試環境"""
        self.library = WidgetLibrary()

    def test_initialization(self):
        """測試初始化"""
        self.assertIsInstance(self.library._widgets, dict)
        self.assertIsInstance(self.library._categories, dict)
        self.assertGreater(len(self.library._widgets), 0)  # 應該有預設小工具

    def test_register_widget(self):
        """測試註冊小工具"""

        # 創建測試小工具類
        class TestWidget(BaseWidget):
            def get_widget_type(self):
                return "test_widget"

            def get_default_title(self):
                return "測試小工具"

            def get_default_size(self):
                return {"width": 2, "height": 2}

            def render_content(self):
                pass

        # 註冊小工具
        self.library.register_widget("test_widget", TestWidget, "測試分類")

        # 檢查是否註冊成功
        self.assertIn("test_widget", self.library._widgets)
        self.assertIn("測試分類", self.library._categories)
        self.assertIn("test_widget", self.library._categories["測試分類"])

    def test_create_widget(self):
        """測試創建小工具"""
        # 創建已註冊的小工具
        widget = self.library.create_widget(
            "stock_price_card", "test_id", {"symbol": "2330.TW"}
        )
        self.assertIsNotNone(widget)
        self.assertEqual(widget.widget_id, "test_id")

        # 創建未註冊的小工具
        widget = self.library.create_widget("nonexistent_widget", "test_id")
        self.assertIsNone(widget)

    def test_get_widget_info(self):
        """測試獲取小工具資訊"""
        # 獲取存在的小工具資訊
        info = self.library.get_widget_info("stock_price_card")
        self.assertIsNotNone(info)
        self.assertEqual(info["type"], "stock_price_card")
        self.assertIn("name", info)
        self.assertIn("default_size", info)

        # 獲取不存在的小工具資訊
        info = self.library.get_widget_info("nonexistent")
        self.assertIsNone(info)

    def test_get_available_widgets(self):
        """測試獲取可用小工具"""
        widgets = self.library.get_available_widgets()
        self.assertIsInstance(widgets, dict)

        # 檢查是否有分類
        self.assertGreater(len(widgets), 0)

        # 檢查每個分類是否有小工具
        for category, widget_list in widgets.items():
            self.assertIsInstance(widget_list, list)
            if widget_list:  # 如果分類不為空
                self.assertIsInstance(widget_list[0], dict)

    def test_search_widgets(self):
        """測試搜尋小工具"""
        # 搜尋存在的小工具
        results = self.library.search_widgets("股價")
        self.assertIsInstance(results, list)

        # 搜尋不存在的小工具
        results = self.library.search_widgets("不存在的小工具")
        self.assertIsInstance(results, list)

    def test_get_widget_templates(self):
        """測試獲取小工具模板"""
        templates = self.library.get_widget_templates()
        self.assertIsInstance(templates, dict)
        self.assertGreater(len(templates), 0)

        # 檢查模板結構
        for template_name, template_config in templates.items():
            self.assertIn("type", template_config)
            self.assertIn("size", template_config)
            self.assertIn("config", template_config)


class TestGridLayout(unittest.TestCase):
    """測試網格佈局"""

    def setUp(self):
        """設置測試環境"""
        self.grid = GridLayout()

    def test_initialization(self):
        """測試初始化"""
        self.assertEqual(self.grid.columns, 12)
        self.assertEqual(self.grid.row_height, 60)
        self.assertIsInstance(self.grid.widgets, dict)
        self.assertEqual(len(self.grid.widgets), 0)

    def test_grid_position(self):
        """測試網格位置"""
        pos = GridPosition(2, 3, 4, 2)
        self.assertEqual(pos.x, 2)
        self.assertEqual(pos.y, 3)
        self.assertEqual(pos.width, 4)
        self.assertEqual(pos.height, 2)

        # 測試邊界檢查
        pos = GridPosition(-1, -1, 15, 0)
        self.assertEqual(pos.x, 0)  # 最小值限制
        self.assertEqual(pos.y, 0)  # 最小值限制
        self.assertEqual(pos.width, 12)  # 最大值限制
        self.assertEqual(pos.height, 1)  # 最小值限制

    def test_position_overlap(self):
        """測試位置重疊檢測"""
        pos1 = GridPosition(0, 0, 4, 2)
        pos2 = GridPosition(2, 1, 4, 2)  # 重疊
        pos3 = GridPosition(5, 0, 4, 2)  # 不重疊

        self.assertTrue(pos1.overlaps(pos2))
        self.assertFalse(pos1.overlaps(pos3))

    def test_add_widget(self):
        """測試添加小工具"""
        pos = GridPosition(0, 0, 3, 2)

        # 添加有效小工具
        result = self.grid.add_widget("widget1", pos)
        self.assertTrue(result)
        self.assertIn("widget1", self.grid.widgets)

        # 添加重疊小工具
        pos2 = GridPosition(1, 1, 3, 2)  # 與第一個重疊
        result = self.grid.add_widget("widget2", pos2)
        # 根據 auto_arrange 設定，可能成功或失敗
        self.assertIsInstance(result, bool)

    def test_remove_widget(self):
        """測試移除小工具"""
        pos = GridPosition(0, 0, 3, 2)
        self.grid.add_widget("widget1", pos)

        # 移除存在的小工具
        result = self.grid.remove_widget("widget1")
        self.assertTrue(result)
        self.assertNotIn("widget1", self.grid.widgets)

        # 移除不存在的小工具
        result = self.grid.remove_widget("nonexistent")
        self.assertFalse(result)

    def test_move_widget(self):
        """測試移動小工具"""
        pos = GridPosition(0, 0, 3, 2)
        self.grid.add_widget("widget1", pos)

        # 移動到有效位置
        new_pos = GridPosition(4, 0, 3, 2)
        result = self.grid.move_widget("widget1", new_pos)
        self.assertTrue(result)

        current_pos = self.grid.get_widget_position("widget1")
        self.assertEqual(current_pos.x, 4)

    def test_resize_widget(self):
        """測試調整小工具大小"""
        pos = GridPosition(0, 0, 3, 2)
        self.grid.add_widget("widget1", pos)

        # 調整到有效尺寸
        result = self.grid.resize_widget("widget1", 4, 3)
        self.assertTrue(result)

        current_pos = self.grid.get_widget_position("widget1")
        self.assertEqual(current_pos.width, 4)
        self.assertEqual(current_pos.height, 3)

    def test_export_import_layout(self):
        """測試匯出匯入佈局"""
        # 添加一些小工具
        self.grid.add_widget("widget1", GridPosition(0, 0, 3, 2))
        self.grid.add_widget("widget2", GridPosition(4, 0, 4, 3))

        # 匯出佈局
        layout_data = self.grid.export_layout()
        self.assertIsInstance(layout_data, dict)
        self.assertEqual(layout_data["columns"], 12)
        self.assertEqual(len(layout_data["widgets"]), 2)

        # 創建新網格並匯入佈局
        new_grid = GridLayout()
        new_grid.import_layout(layout_data)

        self.assertEqual(len(new_grid.widgets), 2)
        self.assertIn("widget1", new_grid.widgets)
        self.assertIn("widget2", new_grid.widgets)


class TestWidgetTheme(unittest.TestCase):
    """測試小工具主題"""

    def test_get_theme(self):
        """測試獲取主題"""
        # 測試淺色主題
        light_theme = WidgetTheme.get_theme("light")
        self.assertIsInstance(light_theme, dict)
        self.assertEqual(light_theme["background"], "#FFFFFF")

        # 測試深色主題
        dark_theme = WidgetTheme.get_theme("dark")
        self.assertIsInstance(dark_theme, dict)
        self.assertEqual(dark_theme["background"], "#1E1E1E")

        # 測試預設主題
        default_theme = WidgetTheme.get_theme("invalid")
        self.assertEqual(default_theme, WidgetTheme.LIGHT)


class TestWidgetSize(unittest.TestCase):
    """測試小工具尺寸"""

    def test_size_definitions(self):
        """測試尺寸定義"""
        self.assertEqual(WidgetSize.SMALL["width"], 2)
        self.assertEqual(WidgetSize.SMALL["height"], 2)

        self.assertEqual(WidgetSize.MEDIUM["width"], 4)
        self.assertEqual(WidgetSize.MEDIUM["height"], 3)

        self.assertEqual(WidgetSize.LARGE["width"], 6)
        self.assertEqual(WidgetSize.LARGE["height"], 4)

    def test_get_size_options(self):
        """測試獲取尺寸選項"""
        options = WidgetSize.get_size_options()
        self.assertIsInstance(options, dict)
        self.assertIn("小", options)
        self.assertIn("中", options)
        self.assertIn("大", options)


if __name__ == "__main__":
    # 運行測試
    unittest.main(verbosity=2)
