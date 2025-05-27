"""
儀表板配置管理器

提供儀表板配置的 CRUD 操作、版本控制、匯入匯出等功能。
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import streamlit as st
import logging

logger = logging.getLogger(__name__)


class DashboardConfig:
    """儀表板配置類"""

    def __init__(
        self,
        config_id: str = None,
        name: str = "新儀表板",
        description: str = "",
        template_type: str = "custom",
    ):
        """初始化儀表板配置

        Args:
            config_id: 配置唯一標識
            name: 儀表板名稱
            description: 儀表板描述
            template_type: 模板類型
        """
        self.config_id = config_id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.template_type = template_type
        self.version = "1.0.0"
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.layout = {
            "grid_columns": 12,
            "grid_rows": 8,
            "responsive_breakpoints": {"desktop": 1200, "tablet": 768, "mobile": 480},
        }
        self.widgets: List[Dict[str, Any]] = []
        self.theme = "light"
        self.auto_refresh = True
        self.refresh_interval = 30  # 秒

    def add_widget(
        self,
        widget_type: str,
        position: Dict[str, int],
        size: Dict[str, int],
        config: Dict[str, Any] = None,
    ) -> str:
        """添加小工具

        Args:
            widget_type: 小工具類型
            position: 位置 {x, y}
            size: 大小 {width, height}
            config: 小工具配置

        Returns:
            小工具ID
        """
        widget_id = str(uuid.uuid4())
        widget = {
            "id": widget_id,
            "type": widget_type,
            "position": position,
            "size": size,
            "config": config or {},
            "z_index": len(self.widgets),
            "created_at": datetime.now().isoformat(),
        }
        self.widgets.append(widget)
        self.updated_at = datetime.now().isoformat()
        return widget_id

    def remove_widget(self, widget_id: str) -> bool:
        """移除小工具

        Args:
            widget_id: 小工具ID

        Returns:
            是否成功移除
        """
        for i, widget in enumerate(self.widgets):
            if widget["id"] == widget_id:
                self.widgets.pop(i)
                self.updated_at = datetime.now().isoformat()
                return True
        return False

    def update_widget(self, widget_id: str, updates: Dict[str, Any]) -> bool:
        """更新小工具

        Args:
            widget_id: 小工具ID
            updates: 更新內容

        Returns:
            是否成功更新
        """
        for widget in self.widgets:
            if widget["id"] == widget_id:
                widget.update(updates)
                self.updated_at = datetime.now().isoformat()
                return True
        return False

    def get_widget(self, widget_id: str) -> Optional[Dict[str, Any]]:
        """獲取小工具

        Args:
            widget_id: 小工具ID

        Returns:
            小工具配置
        """
        for widget in self.widgets:
            if widget["id"] == widget_id:
                return widget
        return None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典

        Returns:
            配置字典
        """
        return {
            "config_id": self.config_id,
            "name": self.name,
            "description": self.description,
            "template_type": self.template_type,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "layout": self.layout,
            "widgets": self.widgets,
            "theme": self.theme,
            "auto_refresh": self.auto_refresh,
            "refresh_interval": self.refresh_interval,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DashboardConfig":
        """從字典創建配置

        Args:
            data: 配置字典

        Returns:
            儀表板配置實例
        """
        config = cls(
            config_id=data.get("config_id"),
            name=data.get("name", "新儀表板"),
            description=data.get("description", ""),
            template_type=data.get("template_type", "custom"),
        )

        config.version = data.get("version", "1.0.0")
        config.created_at = data.get("created_at", datetime.now().isoformat())
        config.updated_at = data.get("updated_at", datetime.now().isoformat())
        config.layout = data.get("layout", config.layout)
        config.widgets = data.get("widgets", [])
        config.theme = data.get("theme", "light")
        config.auto_refresh = data.get("auto_refresh", True)
        config.refresh_interval = data.get("refresh_interval", 30)

        return config

    def validate(self) -> Tuple[bool, List[str]]:
        """驗證配置

        Returns:
            (是否有效, 錯誤訊息列表)
        """
        errors = []

        # 檢查基本屬性
        if not self.name or not self.name.strip():
            errors.append("儀表板名稱不能為空")

        if not self.config_id:
            errors.append("配置ID不能為空")

        # 檢查佈局
        if (
            not isinstance(self.layout.get("grid_columns"), int)
            or self.layout["grid_columns"] <= 0
        ):
            errors.append("網格列數必須為正整數")

        if (
            not isinstance(self.layout.get("grid_rows"), int)
            or self.layout["grid_rows"] <= 0
        ):
            errors.append("網格行數必須為正整數")

        # 檢查小工具
        for i, widget in enumerate(self.widgets):
            if not widget.get("id"):
                errors.append(f"小工具 {i} 缺少ID")

            if not widget.get("type"):
                errors.append(f"小工具 {i} 缺少類型")

            position = widget.get("position", {})
            if not isinstance(position.get("x"), int) or position["x"] < 0:
                errors.append(f"小工具 {i} 的X座標無效")

            if not isinstance(position.get("y"), int) or position["y"] < 0:
                errors.append(f"小工具 {i} 的Y座標無效")

            size = widget.get("size", {})
            if not isinstance(size.get("width"), int) or size["width"] <= 0:
                errors.append(f"小工具 {i} 的寬度無效")

            if not isinstance(size.get("height"), int) or size["height"] <= 0:
                errors.append(f"小工具 {i} 的高度無效")

        return len(errors) == 0, errors


class DashboardManager:
    """儀表板管理器"""

    def __init__(self):
        """初始化儀表板管理器"""
        self.storage_key = "dashboard_configs"
        self.history_key = "dashboard_history"
        self.max_history = 5

        # 初始化 session state
        if self.storage_key not in st.session_state:
            st.session_state[self.storage_key] = {}

        if self.history_key not in st.session_state:
            st.session_state[self.history_key] = {}

        if "current_dashboard" not in st.session_state:
            st.session_state["current_dashboard"] = None

    def create_dashboard(
        self, name: str, description: str = "", template_type: str = "custom"
    ) -> DashboardConfig:
        """創建新儀表板

        Args:
            name: 儀表板名稱
            description: 描述
            template_type: 模板類型

        Returns:
            儀表板配置
        """
        config = DashboardConfig(
            name=name, description=description, template_type=template_type
        )

        # 根據模板類型初始化
        if template_type != "custom":
            self._apply_template(config, template_type)

        self.save_dashboard(config)
        return config

    def save_dashboard(
        self, config: DashboardConfig, save_history: bool = True
    ) -> bool:
        """儲存儀表板

        Args:
            config: 儀表板配置
            save_history: 是否保存歷史版本

        Returns:
            是否成功儲存
        """
        try:
            # 驗證配置
            is_valid, errors = config.validate()
            if not is_valid:
                logger.error(f"儀表板配置驗證失敗: {errors}")
                return False

            # 保存歷史版本
            if save_history and config.config_id in st.session_state[self.storage_key]:
                self._save_history(
                    config.config_id,
                    st.session_state[self.storage_key][config.config_id],
                )

            # 更新時間戳
            config.updated_at = datetime.now().isoformat()

            # 儲存配置
            st.session_state[self.storage_key][config.config_id] = config.to_dict()

            logger.info(f"儀表板 {config.name} 已儲存")
            return True

        except Exception as e:
            logger.error(f"儲存儀表板失敗: {e}")
            return False

    def load_dashboard(self, config_id: str) -> Optional[DashboardConfig]:
        """載入儀表板

        Args:
            config_id: 配置ID

        Returns:
            儀表板配置
        """
        try:
            if config_id in st.session_state[self.storage_key]:
                data = st.session_state[self.storage_key][config_id]
                config = DashboardConfig.from_dict(data)
                st.session_state["current_dashboard"] = config
                return config
            return None

        except Exception as e:
            logger.error(f"載入儀表板失敗: {e}")
            return None

    def delete_dashboard(self, config_id: str) -> bool:
        """刪除儀表板

        Args:
            config_id: 配置ID

        Returns:
            是否成功刪除
        """
        try:
            if config_id in st.session_state[self.storage_key]:
                del st.session_state[self.storage_key][config_id]

                # 清理歷史記錄
                if config_id in st.session_state[self.history_key]:
                    del st.session_state[self.history_key][config_id]

                # 如果是當前儀表板，清除引用
                if (
                    st.session_state.get("current_dashboard")
                    and st.session_state["current_dashboard"].config_id == config_id
                ):
                    st.session_state["current_dashboard"] = None

                return True
            return False

        except Exception as e:
            logger.error(f"刪除儀表板失敗: {e}")
            return False

    def list_dashboards(self) -> List[Dict[str, Any]]:
        """列出所有儀表板

        Returns:
            儀表板列表
        """
        dashboards = []
        for config_id, data in st.session_state[self.storage_key].items():
            dashboards.append(
                {
                    "config_id": config_id,
                    "name": data.get("name", "未命名"),
                    "description": data.get("description", ""),
                    "template_type": data.get("template_type", "custom"),
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                    "widget_count": len(data.get("widgets", [])),
                }
            )

        # 按更新時間排序
        dashboards.sort(key=lambda x: x["updated_at"], reverse=True)
        return dashboards

    def export_dashboard(self, config_id: str) -> Optional[str]:
        """匯出儀表板配置

        Args:
            config_id: 配置ID

        Returns:
            JSON 字符串
        """
        try:
            if config_id in st.session_state[self.storage_key]:
                data = st.session_state[self.storage_key][config_id]
                return json.dumps(data, indent=2, ensure_ascii=False)
            return None

        except Exception as e:
            logger.error(f"匯出儀表板失敗: {e}")
            return None

    def import_dashboard(self, json_data: str) -> Optional[DashboardConfig]:
        """匯入儀表板配置

        Args:
            json_data: JSON 字符串

        Returns:
            儀表板配置
        """
        try:
            data = json.loads(json_data)
            config = DashboardConfig.from_dict(data)

            # 生成新的ID避免衝突
            config.config_id = str(uuid.uuid4())
            config.name = f"{config.name} (匯入)"

            # 驗證並儲存
            is_valid, errors = config.validate()
            if is_valid:
                self.save_dashboard(config, save_history=False)
                return config
            else:
                logger.error(f"匯入的儀表板配置無效: {errors}")
                return None

        except Exception as e:
            logger.error(f"匯入儀表板失敗: {e}")
            return None

    def _save_history(self, config_id: str, config_data: Dict[str, Any]):
        """保存歷史版本

        Args:
            config_id: 配置ID
            config_data: 配置數據
        """
        if config_id not in st.session_state[self.history_key]:
            st.session_state[self.history_key][config_id] = []

        history = st.session_state[self.history_key][config_id]

        # 添加時間戳
        config_data["history_timestamp"] = datetime.now().isoformat()
        history.append(config_data.copy())

        # 限制歷史記錄數量
        if len(history) > self.max_history:
            history.pop(0)

    def _apply_template(self, config: DashboardConfig, template_type: str):
        """應用模板

        Args:
            config: 儀表板配置
            template_type: 模板類型
        """
        if template_type == "trading_monitor":
            self._apply_trading_monitor_template(config)
        elif template_type == "technical_analysis":
            self._apply_technical_analysis_template(config)
        elif template_type == "portfolio_overview":
            self._apply_portfolio_overview_template(config)

    def _apply_trading_monitor_template(self, config: DashboardConfig):
        """應用交易監控模板"""
        config.add_widget(
            "stock_price_card", {"x": 0, "y": 0}, {"width": 3, "height": 2}
        )
        config.add_widget("market_status", {"x": 3, "y": 0}, {"width": 3, "height": 2})
        config.add_widget(
            "portfolio_summary", {"x": 6, "y": 0}, {"width": 6, "height": 2}
        )
        config.add_widget(
            "candlestick_chart", {"x": 0, "y": 2}, {"width": 8, "height": 4}
        )
        config.add_widget(
            "trading_activity", {"x": 8, "y": 2}, {"width": 4, "height": 4}
        )
        config.add_widget("alerts_panel", {"x": 0, "y": 6}, {"width": 12, "height": 2})

    def _apply_technical_analysis_template(self, config: DashboardConfig):
        """應用技術分析模板"""
        config.add_widget(
            "candlestick_chart", {"x": 0, "y": 0}, {"width": 8, "height": 4}
        )
        config.add_widget("volume_chart", {"x": 8, "y": 0}, {"width": 4, "height": 2})
        config.add_widget("rsi_indicator", {"x": 8, "y": 2}, {"width": 4, "height": 2})
        config.add_widget("macd_indicator", {"x": 0, "y": 4}, {"width": 6, "height": 2})
        config.add_widget(
            "bollinger_bands", {"x": 6, "y": 4}, {"width": 6, "height": 2}
        )
        config.add_widget(
            "correlation_heatmap", {"x": 0, "y": 6}, {"width": 12, "height": 2}
        )

    def _apply_portfolio_overview_template(self, config: DashboardConfig):
        """應用投資組合概覽模板"""
        config.add_widget(
            "portfolio_value", {"x": 0, "y": 0}, {"width": 4, "height": 2}
        )
        config.add_widget("daily_pnl", {"x": 4, "y": 0}, {"width": 4, "height": 2})
        config.add_widget("allocation_pie", {"x": 8, "y": 0}, {"width": 4, "height": 4})
        config.add_widget(
            "performance_chart", {"x": 0, "y": 2}, {"width": 8, "height": 3}
        )
        config.add_widget("top_holdings", {"x": 0, "y": 5}, {"width": 6, "height": 3})
        config.add_widget("risk_metrics", {"x": 6, "y": 5}, {"width": 6, "height": 3})


# 全域儀表板管理器實例
dashboard_manager = DashboardManager()
