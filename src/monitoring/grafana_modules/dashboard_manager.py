"""Grafana 儀表板管理器

此模組實現 Grafana 儀表板的管理功能，包括創建、更新、刪除和部署儀表板。
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class DashboardManager:
    """Grafana 儀表板管理器

    管理 Grafana 儀表板的創建、配置和部署。

    Attributes:
        grafana_api: Grafana API 客戶端
        templates_dir: 儀表板模板目錄
    """

    def __init__(self, grafana_api: Any, config_dir: Path):
        """初始化儀表板管理器

        Args:
            grafana_api: Grafana API 客戶端
            config_dir: 配置檔案根目錄

        Raises:
            Exception: 初始化失敗時拋出異常
        """
        self.grafana_api = grafana_api
        self.templates_dir = config_dir / "grafana_dashboards"
        
        # 確保目錄存在
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化預設儀表板模板
        self._init_default_templates()
        
        module_logger.info("儀表板管理器初始化成功")

    def _init_default_templates(self) -> None:
        """初始化預設儀表板模板"""
        try:
            # 創建系統概覽儀表板
            system_overview = self._create_system_overview_template()
            self._save_template("system_overview.json", system_overview)

            # 創建交易監控儀表板
            trading_monitoring = self._create_trading_monitoring_template()
            self._save_template("trading_performance.json", trading_monitoring)

            # 創建風險監控儀表板
            risk_monitoring = self._create_risk_monitoring_template()
            self._save_template("risk_monitoring.json", risk_monitoring)

            module_logger.info("預設儀表板模板初始化完成")

        except Exception as e:
            module_logger.error("初始化預設儀表板模板失敗: %s", e)

    def _create_system_overview_template(self) -> Dict[str, Any]:
        """創建系統概覽儀表板模板

        Returns:
            Dict[str, Any]: 儀表板配置字典
        """
        return {
            "dashboard": {
                "id": None,
                "title": "AI 交易系統 - 系統概覽",
                "tags": ["trading", "system", "overview"],
                "timezone": "Asia/Taipei",
                "panels": [
                    {
                        "id": 1,
                        "title": "CPU 使用率",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "system_cpu_usage_percent",
                                "legendFormat": "CPU 使用率",
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percent",
                                "min": 0,
                                "max": 100,
                                "thresholds": {
                                    "steps": [
                                        {"color": "green", "value": 0},
                                        {"color": "yellow", "value": 70},
                                        {"color": "red", "value": 90},
                                    ]
                                },
                            }
                        },
                        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0},
                    },
                    {
                        "id": 2,
                        "title": "記憶體使用率",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "system_memory_usage_percent",
                                "legendFormat": "記憶體使用率",
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percent",
                                "min": 0,
                                "max": 100,
                                "thresholds": {
                                    "steps": [
                                        {"color": "green", "value": 0},
                                        {"color": "yellow", "value": 70},
                                        {"color": "red", "value": 90},
                                    ]
                                },
                            }
                        },
                        "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0},
                    },
                ],
                "time": {"from": "now-1h", "to": "now"},
                "refresh": "30s",
            },
            "overwrite": True,
        }

    def _create_trading_monitoring_template(self) -> Dict[str, Any]:
        """創建交易監控儀表板模板

        Returns:
            Dict[str, Any]: 儀表板配置字典
        """
        return {
            "dashboard": {
                "id": None,
                "title": "AI 交易系統 - 交易效能監控",
                "tags": ["trading", "performance", "monitoring"],
                "timezone": "Asia/Taipei",
                "panels": [
                    {
                        "id": 1,
                        "title": "訂單成功率",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "trading_order_success_rate",
                                "legendFormat": "{{order_type}} 成功率",
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "percent",
                                "min": 0,
                                "max": 100,
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 80},
                                        {"color": "green", "value": 95},
                                    ]
                                },
                            }
                        },
                        "gridPos": {"h": 8, "w": 8, "x": 0, "y": 0},
                    },
                ],
                "time": {"from": "now-1h", "to": "now"},
                "refresh": "30s",
            },
            "overwrite": True,
        }

    def _create_risk_monitoring_template(self) -> Dict[str, Any]:
        """創建風險監控儀表板模板

        Returns:
            Dict[str, Any]: 儀表板配置字典
        """
        return {
            "dashboard": {
                "id": None,
                "title": "AI 交易系統 - 風險監控",
                "tags": ["trading", "risk", "monitoring"],
                "timezone": "Asia/Taipei",
                "panels": [
                    {
                        "id": 1,
                        "title": "活躍警報",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "sum(active_alerts_count)",
                                "legendFormat": "總警報數",
                            }
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "short",
                                "thresholds": {
                                    "steps": [
                                        {"color": "green", "value": 0},
                                        {"color": "yellow", "value": 5},
                                        {"color": "red", "value": 10},
                                    ]
                                },
                            }
                        },
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                    },
                ],
                "time": {"from": "now-1h", "to": "now"},
                "refresh": "30s",
            },
            "overwrite": True,
        }

    def _save_template(self, filename: str, template: Dict[str, Any]) -> None:
        """儲存儀表板模板到檔案

        Args:
            filename: 檔案名稱
            template: 儀表板模板配置
        """
        template_file = self.templates_dir / filename
        with open(template_file, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=2, ensure_ascii=False)

    def deploy_dashboard(self, dashboard_config: Dict[str, Any]) -> Optional[str]:
        """部署儀表板

        Args:
            dashboard_config: 儀表板配置

        Returns:
            Optional[str]: 成功返回儀表板 URL，失敗返回 None
        """
        try:
            result = self.grafana_api.dashboard.update_dashboard(dashboard_config)
            dashboard_url = f"{self.grafana_api.host}/d/{result['uid']}"
            module_logger.info("儀表板部署成功: %s", dashboard_url)
            return dashboard_url

        except Exception as e:
            module_logger.error("部署儀表板失敗: %s", e)
            return None

    def load_template(self, filename: str) -> Optional[Dict[str, Any]]:
        """從檔案載入儀表板模板

        Args:
            filename: 模板檔案名稱

        Returns:
            Optional[Dict[str, Any]]: 儀表板模板，失敗返回 None
        """
        try:
            template_file = self.templates_dir / filename
            if not template_file.exists():
                module_logger.error("模板檔案不存在: %s", template_file)
                return None

            with open(template_file, "r", encoding="utf-8") as f:
                template = json.load(f)

            module_logger.info("載入儀表板模板成功: %s", filename)
            return template

        except Exception as e:
            module_logger.error("載入儀表板模板失敗: %s", e)
            return None

    def deploy_all_templates(self) -> Dict[str, Optional[str]]:
        """部署所有儀表板模板

        Returns:
            Dict[str, Optional[str]]: 部署結果字典，鍵為檔案名，值為儀表板 URL
        """
        results = {}

        try:
            # 獲取所有模板檔案
            template_files = list(self.templates_dir.glob("*.json"))

            for template_file in template_files:
                try:
                    template = self.load_template(template_file.name)
                    if template:
                        url = self.deploy_dashboard(template)
                        results[template_file.name] = url
                    else:
                        results[template_file.name] = None

                except Exception as e:
                    module_logger.error(
                        "部署儀表板模板失敗 %s: %s",
                        template_file.name,
                        e
                    )
                    results[template_file.name] = None

            success_count = sum(1 for url in results.values() if url is not None)
            total_count = len(results)
            module_logger.info(
                "儀表板部署完成，成功 %d/%d",
                success_count,
                total_count
            )

        except Exception as e:
            module_logger.error("部署所有儀表板失敗: %s", e)

        return results
