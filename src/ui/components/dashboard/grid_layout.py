"""
網格佈局組件

提供 12 欄網格系統和響應式佈局管理功能。
"""

import logging
from typing import Any, Dict, Optional, Tuple

import streamlit as st

logger = logging.getLogger(__name__)


class GridPosition:
    """網格位置類"""

    def __init__(self, x: int, y: int, width: int, height: int):
        """初始化網格位置

        Args:
            x: X座標 (0-11)
            y: Y座標 (0+)
            width: 寬度 (1-12)
            height: 高度 (1+)
        """
        self.x = max(0, min(11, x))
        self.y = max(0, y)
        self.width = max(1, min(12, width))
        self.height = max(1, height)

        # 確保不超出網格邊界
        if self.x + self.width > 12:
            self.width = 12 - self.x

    def overlaps(self, other: "GridPosition") -> bool:
        """檢查是否與另一個位置重疊

        Args:
            other: 另一個網格位置

        Returns:
            是否重疊
        """
        return not (
            self.x + self.width <= other.x
            or other.x + other.width <= self.x
            or self.y + self.height <= other.y
            or other.y + other.height <= self.y
        )

    def to_dict(self) -> Dict[str, int]:
        """轉換為字典

        Returns:
            位置字典
        """
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> "GridPosition":
        """從字典創建位置

        Args:
            data: 位置字典

        Returns:
            網格位置實例
        """
        return cls(
            data.get("x", 0),
            data.get("y", 0),
            data.get("width", 1),
            data.get("height", 1),
        )

    def __str__(self) -> str:
        return f"GridPosition(x={self.x}, y={self.y}, w={self.width}, h={self.height})"


class ResponsiveBreakpoints:
    """響應式斷點配置"""

    DESKTOP = 1200
    TABLET = 768
    MOBILE = 480

    @classmethod
    def get_device_type(cls, width: int) -> str:
        """根據寬度獲取設備類型

        Args:
            width: 螢幕寬度

        Returns:
            設備類型
        """
        if width >= cls.DESKTOP:
            return "desktop"
        elif width >= cls.TABLET:
            return "tablet"
        else:
            return "mobile"

    @classmethod
    def get_grid_columns(cls, device_type: str) -> int:
        """根據設備類型獲取網格列數

        Args:
            device_type: 設備類型

        Returns:
            網格列數
        """
        columns_map = {"desktop": 12, "tablet": 8, "mobile": 4}
        return columns_map.get(device_type, 12)


class GridLayout:
    """網格佈局管理器"""

    def __init__(self, columns: int = 12, row_height: int = 60):
        """初始化網格佈局

        Args:
            columns: 網格列數
            row_height: 行高度 (像素)
        """
        self.columns = columns
        self.row_height = row_height
        self.widgets: Dict[str, GridPosition] = {}
        self.z_index: Dict[str, int] = {}
        self.snap_to_grid = True
        self.auto_arrange = True

    def add_widget(
        self, widget_id: str, position: GridPosition, z_index: int = 0
    ) -> bool:
        """添加小工具到網格

        Args:
            widget_id: 小工具ID
            position: 網格位置
            z_index: 層級

        Returns:
            是否成功添加
        """
        # 檢查位置是否有效
        if not self._is_position_valid(position):
            logger.warning(f"無效的網格位置: {position}")
            return False

        # 檢查是否與現有小工具重疊
        if self._has_collision(widget_id, position):
            if self.auto_arrange:
                position = self._find_available_position(position)
                if position is None:
                    logger.warning(f"無法找到可用位置給小工具: {widget_id}")
                    return False
            else:
                logger.warning(f"位置衝突: {widget_id}")
                return False

        self.widgets[widget_id] = position
        self.z_index[widget_id] = z_index

        logger.info(f"已添加小工具到網格: {widget_id} at {position}")
        return True

    def remove_widget(self, widget_id: str) -> bool:
        """從網格移除小工具

        Args:
            widget_id: 小工具ID

        Returns:
            是否成功移除
        """
        if widget_id in self.widgets:
            del self.widgets[widget_id]
            if widget_id in self.z_index:
                del self.z_index[widget_id]
            logger.info(f"已從網格移除小工具: {widget_id}")
            return True
        return False

    def move_widget(self, widget_id: str, new_position: GridPosition) -> bool:
        """移動小工具

        Args:
            widget_id: 小工具ID
            new_position: 新位置

        Returns:
            是否成功移動
        """
        if widget_id not in self.widgets:
            return False

        # 暫時移除小工具以檢查新位置
        old_position = self.widgets[widget_id]
        del self.widgets[widget_id]

        # 檢查新位置是否可用
        if self._has_collision(widget_id, new_position):
            # 恢復原位置
            self.widgets[widget_id] = old_position
            return False

        # 應用磁吸功能
        if self.snap_to_grid:
            new_position = self._snap_to_grid(new_position)

        self.widgets[widget_id] = new_position
        logger.info(f"已移動小工具: {widget_id} to {new_position}")
        return True

    def resize_widget(self, widget_id: str, new_width: int, new_height: int) -> bool:
        """調整小工具大小

        Args:
            widget_id: 小工具ID
            new_width: 新寬度
            new_height: 新高度

        Returns:
            是否成功調整
        """
        if widget_id not in self.widgets:
            return False

        current_pos = self.widgets[widget_id]
        new_position = GridPosition(current_pos.x, current_pos.y, new_width, new_height)

        # 暫時移除小工具以檢查新尺寸
        del self.widgets[widget_id]

        if self._has_collision(widget_id, new_position):
            # 恢復原尺寸
            self.widgets[widget_id] = current_pos
            return False

        self.widgets[widget_id] = new_position
        logger.info(f"已調整小工具大小: {widget_id} to {new_width}x{new_height}")
        return True

    def get_widget_position(self, widget_id: str) -> Optional[GridPosition]:
        """獲取小工具位置

        Args:
            widget_id: 小工具ID

        Returns:
            網格位置
        """
        return self.widgets.get(widget_id)

    def get_layout_bounds(self) -> Tuple[int, int]:
        """獲取佈局邊界

        Returns:
            (寬度, 高度)
        """
        if not self.widgets:
            return self.columns, 1

        max_x = max(pos.x + pos.width for pos in self.widgets.values())
        max_y = max(pos.y + pos.height for pos in self.widgets.values())

        return max_x, max_y

    def compact_layout(self) -> None:
        """壓縮佈局，移除空隙"""
        if not self.widgets:
            return

        # 按Y座標排序小工具
        sorted_widgets = sorted(self.widgets.items(), key=lambda x: (x[1].y, x[1].x))

        # 重新排列小工具
        for widget_id, position in sorted_widgets:
            new_y = self._find_lowest_available_y(position.x, position.width)
            if new_y < position.y:
                new_position = GridPosition(
                    position.x, new_y, position.width, position.height
                )
                self.widgets[widget_id] = new_position

        logger.info("已壓縮佈局")

    def _is_position_valid(self, position: GridPosition) -> bool:
        """檢查位置是否有效

        Args:
            position: 網格位置

        Returns:
            是否有效
        """
        return (
            0 <= position.x < self.columns
            and position.x + position.width <= self.columns
            and position.y >= 0
            and position.width > 0
            and position.height > 0
        )

    def _has_collision(self, widget_id: str, position: GridPosition) -> bool:
        """檢查是否有碰撞

        Args:
            widget_id: 小工具ID
            position: 網格位置

        Returns:
            是否有碰撞
        """
        for other_id, other_pos in self.widgets.items():
            if other_id != widget_id and position.overlaps(other_pos):
                return True
        return False

    def _find_available_position(
        self, preferred_position: GridPosition
    ) -> Optional[GridPosition]:
        """尋找可用位置

        Args:
            preferred_position: 偏好位置

        Returns:
            可用位置
        """
        # 從偏好位置開始搜尋
        for y in range(preferred_position.y, preferred_position.y + 20):
            for x in range(self.columns - preferred_position.width + 1):
                test_position = GridPosition(
                    x, y, preferred_position.width, preferred_position.height
                )

                if not self._has_collision("", test_position):
                    return test_position

        return None

    def _find_lowest_available_y(self, x: int, width: int) -> int:
        """尋找最低可用Y座標

        Args:
            x: X座標
            width: 寬度

        Returns:
            最低可用Y座標
        """
        y = 0
        while True:
            test_position = GridPosition(x, y, width, 1)
            if not self._has_collision("", test_position):
                return y
            y += 1

    def _snap_to_grid(self, position: GridPosition) -> GridPosition:
        """磁吸到網格

        Args:
            position: 原始位置

        Returns:
            磁吸後位置
        """
        # 這裡可以實現磁吸邏輯
        # 目前直接返回原位置
        return position

    def render_grid_overlay(self, show_grid: bool = True) -> None:
        """渲染網格覆蓋層

        Args:
            show_grid: 是否顯示網格線
        """
        if not show_grid:
            return

        # 使用CSS顯示網格線
        grid_css = f"""
        <style>
        .grid-overlay {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 1000;
        }}

        .grid-line-vertical {{
            position: absolute;
            width: 1px;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.1);
            border-left: 1px dashed #ccc;
        }}

        .grid-line-horizontal {{
            position: absolute;
            width: 100%;
            height: 1px;
            background-color: rgba(0, 0, 0, 0.1);
            border-top: 1px dashed #ccc;
        }}
        </style>
        """

        st.markdown(grid_css, unsafe_allow_html=True)

    def export_layout(self) -> Dict[str, Any]:
        """匯出佈局配置

        Returns:
            佈局配置
        """
        return {
            "columns": self.columns,
            "row_height": self.row_height,
            "widgets": {
                widget_id: position.to_dict()
                for widget_id, position in self.widgets.items()
            },
            "z_index": self.z_index.copy(),
        }

    def import_layout(self, layout_data: Dict[str, Any]) -> None:
        """匯入佈局配置

        Args:
            layout_data: 佈局配置
        """
        self.columns = layout_data.get("columns", 12)
        self.row_height = layout_data.get("row_height", 60)

        self.widgets = {}
        for widget_id, pos_data in layout_data.get("widgets", {}).items():
            position = GridPosition.from_dict(pos_data)
            self.widgets[widget_id] = position

        self.z_index = layout_data.get("z_index", {})

        logger.info("已匯入佈局配置")

    def get_responsive_layout(self, device_type: str) -> "GridLayout":
        """獲取響應式佈局

        Args:
            device_type: 設備類型

        Returns:
            響應式佈局
        """
        responsive_columns = ResponsiveBreakpoints.get_grid_columns(device_type)
        responsive_layout = GridLayout(responsive_columns, self.row_height)

        # 調整小工具位置以適應新的列數
        for widget_id, position in self.widgets.items():
            # 計算比例
            scale_factor = responsive_columns / self.columns

            new_x = int(position.x * scale_factor)
            new_width = max(1, int(position.width * scale_factor))

            # 確保不超出邊界
            if new_x + new_width > responsive_columns:
                new_width = responsive_columns - new_x

            new_position = GridPosition(new_x, position.y, new_width, position.height)

            responsive_layout.add_widget(
                widget_id, new_position, self.z_index.get(widget_id, 0)
            )

        return responsive_layout
