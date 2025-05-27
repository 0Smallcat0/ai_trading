"""Grafana 模板生成器

此模組實現動態生成 Grafana 儀表板模板的功能。
"""

import logging
from typing import Any, Dict, List, Optional

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class TemplateGenerator:
    """Grafana 模板生成器

    動態生成各種類型的 Grafana 儀表板模板。

    Attributes:
        default_time_range: 預設時間範圍
        default_refresh: 預設刷新間隔
    """

    def __init__(
        self,
        default_time_range: Dict[str, str] = None,
        default_refresh: str = "30s"
    ):
        """初始化模板生成器

        Args:
            default_time_range: 預設時間範圍
            default_refresh: 預設刷新間隔
        """
        self.default_time_range = default_time_range or {
            "from": "now-1h",
            "to": "now"
        }
        self.default_refresh = default_refresh

        module_logger.info("模板生成器初始化成功")

    def create_panel(
        self,
        panel_id: int,
        title: str,
        panel_type: str,
        targets: List[Dict[str, Any]],
        grid_pos: Dict[str, int],
        field_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """創建儀表板面板

        Args:
            panel_id: 面板 ID
            title: 面板標題
            panel_type: 面板類型
            targets: 查詢目標列表
            grid_pos: 網格位置
            field_config: 欄位配置

        Returns:
            Dict[str, Any]: 面板配置
        """
        panel = {
            "id": panel_id,
            "title": title,
            "type": panel_type,
            "targets": targets,
            "gridPos": grid_pos,
        }

        if field_config:
            panel["fieldConfig"] = field_config

        return panel

    def create_stat_panel(
        self,
        panel_id: int,
        title: str,
        metric_expr: str,
        legend_format: str,
        grid_pos: Dict[str, int],
        unit: str = "short",
        thresholds: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """創建統計面板

        Args:
            panel_id: 面板 ID
            title: 面板標題
            metric_expr: 指標查詢表達式
            legend_format: 圖例格式
            grid_pos: 網格位置
            unit: 單位
            thresholds: 閾值配置

        Returns:
            Dict[str, Any]: 統計面板配置
        """
        default_thresholds = [
            {"color": "green", "value": 0},
            {"color": "yellow", "value": 70},
            {"color": "red", "value": 90},
        ]

        targets = [
            {
                "expr": metric_expr,
                "legendFormat": legend_format,
            }
        ]

        field_config = {
            "defaults": {
                "unit": unit,
                "thresholds": {
                    "steps": thresholds or default_thresholds
                },
            }
        }

        return self.create_panel(
            panel_id, title, "stat", targets, grid_pos, field_config
        )

    def create_gauge_panel(
        self,
        panel_id: int,
        title: str,
        metric_expr: str,
        legend_format: str,
        grid_pos: Dict[str, int],
        min_value: float = 0,
        max_value: float = 100,
        unit: str = "percent"
    ) -> Dict[str, Any]:
        """創建儀表盤面板

        Args:
            panel_id: 面板 ID
            title: 面板標題
            metric_expr: 指標查詢表達式
            legend_format: 圖例格式
            grid_pos: 網格位置
            min_value: 最小值
            max_value: 最大值
            unit: 單位

        Returns:
            Dict[str, Any]: 儀表盤面板配置
        """
        targets = [
            {
                "expr": metric_expr,
                "legendFormat": legend_format,
            }
        ]

        field_config = {
            "defaults": {
                "unit": unit,
                "min": min_value,
                "max": max_value,
                "thresholds": {
                    "steps": [
                        {"color": "green", "value": 0},
                        {"color": "yellow", "value": 70},
                        {"color": "red", "value": 90},
                    ]
                },
            }
        }

        return self.create_panel(
            panel_id, title, "gauge", targets, grid_pos, field_config
        )

    def create_graph_panel(
        self,
        panel_id: int,
        title: str,
        targets: List[Dict[str, str]],
        grid_pos: Dict[str, int],
        y_axes_unit: str = "short"
    ) -> Dict[str, Any]:
        """創建圖表面板

        Args:
            panel_id: 面板 ID
            title: 面板標題
            targets: 查詢目標列表
            grid_pos: 網格位置
            y_axes_unit: Y軸單位

        Returns:
            Dict[str, Any]: 圖表面板配置
        """
        panel = self.create_panel(
            panel_id, title, "graph", targets, grid_pos
        )

        panel["yAxes"] = [{"unit": y_axes_unit, "min": 0}]

        return panel

    def create_dashboard_template(
        self,
        title: str,
        tags: List[str],
        panels: List[Dict[str, Any]],
        timezone: str = "Asia/Taipei"
    ) -> Dict[str, Any]:
        """創建儀表板模板

        Args:
            title: 儀表板標題
            tags: 標籤列表
            panels: 面板列表
            timezone: 時區

        Returns:
            Dict[str, Any]: 儀表板模板
        """
        return {
            "dashboard": {
                "id": None,
                "title": title,
                "tags": tags,
                "timezone": timezone,
                "panels": panels,
                "time": self.default_time_range,
                "refresh": self.default_refresh,
            },
            "overwrite": True,
        }

    def generate_system_dashboard(self) -> Dict[str, Any]:
        """生成系統監控儀表板

        Returns:
            Dict[str, Any]: 系統監控儀表板配置
        """
        panels = [
            self.create_stat_panel(
                1, "CPU 使用率", "system_cpu_usage_percent", "CPU 使用率",
                {"h": 8, "w": 6, "x": 0, "y": 0}, "percent"
            ),
            self.create_stat_panel(
                2, "記憶體使用率", "system_memory_usage_percent", "記憶體使用率",
                {"h": 8, "w": 6, "x": 6, "y": 0}, "percent"
            ),
            self.create_gauge_panel(
                3, "系統健康分數", "system_health_score", "健康分數",
                {"h": 8, "w": 6, "x": 12, "y": 0}, 0, 100, "short"
            ),
        ]

        return self.create_dashboard_template(
            "AI 交易系統 - 系統監控",
            ["trading", "system", "monitoring"],
            panels
        )

    def generate_trading_dashboard(self) -> Dict[str, Any]:
        """生成交易監控儀表板

        Returns:
            Dict[str, Any]: 交易監控儀表板配置
        """
        panels = [
            self.create_stat_panel(
                1, "訂單成功率", "trading_order_success_rate",
                "{{order_type}} 成功率",
                {"h": 8, "w": 8, "x": 0, "y": 0}, "percent"
            ),
            self.create_gauge_panel(
                2, "資金使用率", "trading_capital_utilization_percent",
                "資金使用率",
                {"h": 8, "w": 8, "x": 8, "y": 0}
            ),
        ]

        return self.create_dashboard_template(
            "AI 交易系統 - 交易監控",
            ["trading", "performance", "monitoring"],
            panels
        )

    def generate_risk_dashboard(self) -> Dict[str, Any]:
        """生成風險監控儀表板

        Returns:
            Dict[str, Any]: 風險監控儀表板配置
        """
        panels = [
            self.create_stat_panel(
                1, "活躍警報", "sum(active_alerts_count)", "總警報數",
                {"h": 8, "w": 12, "x": 0, "y": 0}, "short",
                [
                    {"color": "green", "value": 0},
                    {"color": "yellow", "value": 5},
                    {"color": "red", "value": 10},
                ]
            ),
        ]

        return self.create_dashboard_template(
            "AI 交易系統 - 風險監控",
            ["trading", "risk", "monitoring"],
            panels
        )

    def generate_custom_dashboard(
        self,
        title: str,
        tags: List[str],
        panel_configs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成自定義儀表板

        Args:
            title: 儀表板標題
            tags: 標籤列表
            panel_configs: 面板配置列表

        Returns:
            Dict[str, Any]: 自定義儀表板配置
        """
        panels = []

        for i, config in enumerate(panel_configs, 1):
            panel_type = config.get("type", "stat")
            
            if panel_type == "stat":
                panel = self.create_stat_panel(
                    i,
                    config["title"],
                    config["metric"],
                    config.get("legend", config["title"]),
                    config["grid_pos"],
                    config.get("unit", "short"),
                    config.get("thresholds")
                )
            elif panel_type == "gauge":
                panel = self.create_gauge_panel(
                    i,
                    config["title"],
                    config["metric"],
                    config.get("legend", config["title"]),
                    config["grid_pos"],
                    config.get("min", 0),
                    config.get("max", 100),
                    config.get("unit", "percent")
                )
            else:
                continue

            panels.append(panel)

        return self.create_dashboard_template(title, tags, panels)
