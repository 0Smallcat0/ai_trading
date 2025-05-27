"""Grafana 配置管理器

此模組實現了 Grafana 儀表板配置管理功能，包括：
- 儀表板模板自動化部署（JSON配置檔案）
- 數據源配置管理（Prometheus連接設定）
- 視圖模板庫（系統概覽、交易監控、風險儀表板、效能分析）
- 動態儀表板生成API

遵循 Google Style Docstring 標準和 Phase 5.3 開發規範。
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from grafana_api.grafana_face import GrafanaFace

    GRAFANA_API_AVAILABLE = True
except ImportError:
    GRAFANA_API_AVAILABLE = False
    GrafanaFace = None

try:
    from src.config import CACHE_DIR
except ImportError:
    CACHE_DIR = "cache"

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class GrafanaConfigManager:
    """
    Grafana 配置管理器

    提供完整的 Grafana 儀表板和數據源管理功能，支援自動化部署、
    模板管理和動態配置生成。

    Attributes:
        grafana_url: Grafana 服務器 URL
        api_key: Grafana API 金鑰
        grafana_api: Grafana API 客戶端
        config_dir: 配置檔案目錄
        templates_dir: 模板檔案目錄
    """

    def __init__(
        self,
        grafana_url: str = "http://localhost:3000",
        api_key: Optional[str] = None,
        username: str = "admin",
        password: str = "admin",
    ):
        """
        初始化 Grafana 配置管理器

        Args:
            grafana_url: Grafana 服務器 URL
            api_key: Grafana API 金鑰，優先使用
            username: Grafana 用戶名（當無 API 金鑰時使用）
            password: Grafana 密碼（當無 API 金鑰時使用）

        Raises:
            ImportError: 當 grafana-api 套件未安裝時
            Exception: 初始化失敗時拋出異常
        """
        try:
            if not GRAFANA_API_AVAILABLE:
                raise ImportError(
                    "grafana-api 套件未安裝，請執行: pip install grafana-api"
                )

            self.grafana_url = grafana_url
            self.api_key = api_key
            self.username = username
            self.password = password

            # 初始化 Grafana API 客戶端
            if api_key:
                self.grafana_api = GrafanaFace(auth=api_key, host=grafana_url)
            else:
                self.grafana_api = GrafanaFace(
                    auth=(username, password), host=grafana_url
                )

            # 設置配置目錄
            self.config_dir = Path("config")
            self.templates_dir = self.config_dir / "grafana_dashboards"
            self.datasources_dir = self.config_dir / "grafana_datasources"

            # 確保目錄存在
            self.templates_dir.mkdir(parents=True, exist_ok=True)
            self.datasources_dir.mkdir(parents=True, exist_ok=True)

            # 初始化預設配置
            self._init_default_configs()

            module_logger.info("Grafana 配置管理器初始化成功")

        except Exception as e:
            module_logger.error(f"Grafana 配置管理器初始化失敗: {e}")
            raise

    def _init_default_configs(self) -> None:
        """
        初始化預設配置

        創建預設的數據源和儀表板模板配置。
        """
        try:
            # 創建預設 Prometheus 數據源配置
            self._create_default_datasource_config()

            # 創建預設儀表板模板
            self._create_default_dashboard_templates()

            module_logger.info("預設配置初始化完成")

        except Exception as e:
            module_logger.error(f"初始化預設配置失敗: {e}")

    def _create_default_datasource_config(self) -> None:
        """
        創建預設 Prometheus 數據源配置
        """
        prometheus_config = {
            "name": "Prometheus",
            "type": "prometheus",
            "url": "http://localhost:9090",
            "access": "proxy",
            "isDefault": True,
            "basicAuth": False,
            "jsonData": {"httpMethod": "POST", "timeInterval": "15s"},
        }

        config_file = self.datasources_dir / "prometheus.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(prometheus_config, f, indent=2, ensure_ascii=False)

    def _create_default_dashboard_templates(self) -> None:
        """
        創建預設儀表板模板
        """
        # 系統概覽儀表板
        system_overview = self._create_system_overview_dashboard()
        self._save_dashboard_template("system_overview.json", system_overview)

        # 交易監控儀表板
        trading_monitoring = self._create_trading_monitoring_dashboard()
        self._save_dashboard_template("trading_performance.json", trading_monitoring)

        # 風險監控儀表板
        risk_monitoring = self._create_risk_monitoring_dashboard()
        self._save_dashboard_template("risk_monitoring.json", risk_monitoring)

    def _create_system_overview_dashboard(self) -> Dict[str, Any]:
        """
        創建系統概覽儀表板配置

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
                    {
                        "id": 3,
                        "title": "磁碟使用率",
                        "type": "stat",
                        "targets": [
                            {
                                "expr": "system_disk_usage_percent",
                                "legendFormat": "磁碟使用率",
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
                                        {"color": "yellow", "value": 80},
                                        {"color": "red", "value": 95},
                                    ]
                                },
                            }
                        },
                        "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0},
                    },
                    {
                        "id": 4,
                        "title": "系統健康分數",
                        "type": "gauge",
                        "targets": [
                            {"expr": "system_health_score", "legendFormat": "健康分數"}
                        ],
                        "fieldConfig": {
                            "defaults": {
                                "unit": "short",
                                "min": 0,
                                "max": 100,
                                "thresholds": {
                                    "steps": [
                                        {"color": "red", "value": 0},
                                        {"color": "yellow", "value": 60},
                                        {"color": "green", "value": 80},
                                    ]
                                },
                            }
                        },
                        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0},
                    },
                ],
                "time": {"from": "now-1h", "to": "now"},
                "refresh": "30s",
            },
            "overwrite": True,
        }

    def _create_trading_monitoring_dashboard(self) -> Dict[str, Any]:
        """
        創建交易監控儀表板配置

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
                    {
                        "id": 2,
                        "title": "資金使用率",
                        "type": "gauge",
                        "targets": [
                            {
                                "expr": "trading_capital_utilization_percent",
                                "legendFormat": "資金使用率",
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
                                        {"color": "yellow", "value": 80},
                                        {"color": "red", "value": 95},
                                    ]
                                },
                            }
                        },
                        "gridPos": {"h": 8, "w": 8, "x": 8, "y": 0},
                    },
                    {
                        "id": 3,
                        "title": "API 回應時間",
                        "type": "graph",
                        "targets": [
                            {
                                "expr": "histogram_quantile(0.95, api_request_duration_seconds_bucket)",
                                "legendFormat": "P95 延遲",
                            },
                            {
                                "expr": "histogram_quantile(0.99, api_request_duration_seconds_bucket)",
                                "legendFormat": "P99 延遲",
                            },
                        ],
                        "yAxes": [{"unit": "s", "min": 0}],
                        "gridPos": {"h": 8, "w": 8, "x": 16, "y": 0},
                    },
                ],
                "time": {"from": "now-1h", "to": "now"},
                "refresh": "30s",
            },
            "overwrite": True,
        }

    def _create_risk_monitoring_dashboard(self) -> Dict[str, Any]:
        """
        創建風險監控儀表板配置

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
                    {
                        "id": 2,
                        "title": "警報分布",
                        "type": "piechart",
                        "targets": [
                            {
                                "expr": "active_alerts_count",
                                "legendFormat": "{{severity}}",
                            }
                        ],
                        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                    },
                ],
                "time": {"from": "now-1h", "to": "now"},
                "refresh": "30s",
            },
            "overwrite": True,
        }

    def _save_dashboard_template(
        self, filename: str, dashboard_config: Dict[str, Any]
    ) -> None:
        """
        儲存儀表板模板到檔案

        Args:
            filename: 檔案名稱
            dashboard_config: 儀表板配置
        """
        template_file = self.templates_dir / filename
        with open(template_file, "w", encoding="utf-8") as f:
            json.dump(dashboard_config, f, indent=2, ensure_ascii=False)

    def test_connection(self) -> bool:
        """
        測試 Grafana 連接

        Returns:
            bool: 連接成功返回 True，否則返回 False
        """
        try:
            # 嘗試獲取 Grafana 健康狀態
            health = self.grafana_api.health.check()
            module_logger.info(f"Grafana 連接測試成功: {health}")
            return True

        except Exception as e:
            module_logger.error(f"Grafana 連接測試失敗: {e}")
            return False

    def create_datasource(self, datasource_config: Dict[str, Any]) -> bool:
        """
        創建數據源

        Args:
            datasource_config: 數據源配置

        Returns:
            bool: 創建成功返回 True，否則返回 False
        """
        try:
            result = self.grafana_api.datasource.create_datasource(datasource_config)
            module_logger.info(f"數據源創建成功: {result}")
            return True

        except Exception as e:
            module_logger.error(f"創建數據源失敗: {e}")
            return False

    def deploy_dashboard(self, dashboard_config: Dict[str, Any]) -> Optional[str]:
        """
        部署儀表板

        Args:
            dashboard_config: 儀表板配置

        Returns:
            Optional[str]: 成功返回儀表板 URL，失敗返回 None
        """
        try:
            result = self.grafana_api.dashboard.update_dashboard(dashboard_config)
            dashboard_url = f"{self.grafana_url}/d/{result['uid']}"
            module_logger.info(f"儀表板部署成功: {dashboard_url}")
            return dashboard_url

        except Exception as e:
            module_logger.error(f"部署儀表板失敗: {e}")
            return None

    def deploy_all_templates(self) -> Dict[str, Optional[str]]:
        """
        部署所有儀表板模板

        Returns:
            Dict[str, Optional[str]]: 模板名稱到 URL 的映射
        """
        results = {}

        try:
            # 首先確保 Prometheus 數據源存在
            self._ensure_prometheus_datasource()

            # 部署所有模板
            for template_file in self.templates_dir.glob("*.json"):
                try:
                    with open(template_file, "r", encoding="utf-8") as f:
                        dashboard_config = json.load(f)

                    url = self.deploy_dashboard(dashboard_config)
                    results[template_file.stem] = url

                except Exception as e:
                    module_logger.error(f"部署模板 {template_file.name} 失敗: {e}")
                    results[template_file.stem] = None

            module_logger.info(
                f"模板部署完成，成功: {sum(1 for v in results.values() if v)}/{len(results)}"
            )
            return results

        except Exception as e:
            module_logger.error(f"批量部署模板失敗: {e}")
            return results

    def _ensure_prometheus_datasource(self) -> bool:
        """
        確保 Prometheus 數據源存在

        Returns:
            bool: 成功返回 True，否則返回 False
        """
        try:
            # 檢查是否已存在 Prometheus 數據源
            datasources = self.grafana_api.datasource.list_datasources()

            for ds in datasources:
                if ds.get("type") == "prometheus":
                    module_logger.info("Prometheus 數據源已存在")
                    return True

            # 創建 Prometheus 數據源
            prometheus_config_file = self.datasources_dir / "prometheus.json"
            if prometheus_config_file.exists():
                with open(prometheus_config_file, "r", encoding="utf-8") as f:
                    prometheus_config = json.load(f)

                return self.create_datasource(prometheus_config)
            else:
                module_logger.error("Prometheus 數據源配置檔案不存在")
                return False

        except Exception as e:
            module_logger.error(f"確保 Prometheus 數據源失敗: {e}")
            return False

    def create_custom_dashboard(
        self, title: str, panels: List[Dict[str, Any]], tags: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        創建自定義儀表板

        Args:
            title: 儀表板標題
            panels: 面板配置列表
            tags: 標籤列表，可選

        Returns:
            Optional[str]: 成功返回儀表板 URL，失敗返回 None
        """
        try:
            dashboard_config = {
                "dashboard": {
                    "id": None,
                    "title": title,
                    "tags": tags or ["custom"],
                    "timezone": "Asia/Taipei",
                    "panels": panels,
                    "time": {"from": "now-1h", "to": "now"},
                    "refresh": "30s",
                },
                "overwrite": True,
            }

            return self.deploy_dashboard(dashboard_config)

        except Exception as e:
            module_logger.error(f"創建自定義儀表板失敗: {e}")
            return None

    def get_dashboard_list(self) -> List[Dict[str, Any]]:
        """
        獲取儀表板列表

        Returns:
            List[Dict[str, Any]]: 儀表板資訊列表
        """
        try:
            dashboards = self.grafana_api.search.search_dashboards()
            return dashboards

        except Exception as e:
            module_logger.error(f"獲取儀表板列表失敗: {e}")
            return []

    def delete_dashboard(self, dashboard_uid: str) -> bool:
        """
        刪除儀表板

        Args:
            dashboard_uid: 儀表板 UID

        Returns:
            bool: 刪除成功返回 True，否則返回 False
        """
        try:
            self.grafana_api.dashboard.delete_dashboard(dashboard_uid)
            module_logger.info(f"儀表板 {dashboard_uid} 刪除成功")
            return True

        except Exception as e:
            module_logger.error(f"刪除儀表板失敗: {e}")
            return False

    def export_dashboard(
        self, dashboard_uid: str, output_file: Optional[str] = None
    ) -> Optional[str]:
        """
        匯出儀表板配置

        Args:
            dashboard_uid: 儀表板 UID
            output_file: 輸出檔案路徑，可選

        Returns:
            Optional[str]: 成功返回配置 JSON 字串，失敗返回 None
        """
        try:
            dashboard = self.grafana_api.dashboard.get_dashboard(dashboard_uid)
            dashboard_json = json.dumps(dashboard, indent=2, ensure_ascii=False)

            if output_file:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(dashboard_json)
                module_logger.info(f"儀表板配置已匯出到: {output_file}")

            return dashboard_json

        except Exception as e:
            module_logger.error(f"匯出儀表板配置失敗: {e}")
            return None

    def update_datasource_config(
        self, datasource_name: str, config_updates: Dict[str, Any]
    ) -> bool:
        """
        更新數據源配置

        Args:
            datasource_name: 數據源名稱
            config_updates: 配置更新內容

        Returns:
            bool: 更新成功返回 True，否則返回 False
        """
        try:
            # 獲取現有數據源
            datasources = self.grafana_api.datasource.list_datasources()
            target_datasource = None

            for ds in datasources:
                if ds.get("name") == datasource_name:
                    target_datasource = ds
                    break

            if not target_datasource:
                module_logger.error(f"數據源 {datasource_name} 不存在")
                return False

            # 更新配置
            target_datasource.update(config_updates)

            # 應用更新
            self.grafana_api.datasource.update_datasource(
                target_datasource["id"], target_datasource
            )

            module_logger.info(f"數據源 {datasource_name} 配置更新成功")
            return True

        except Exception as e:
            module_logger.error(f"更新數據源配置失敗: {e}")
            return False

    def get_dashboard_metrics(self, dashboard_uid: str) -> Dict[str, Any]:
        """
        獲取儀表板使用指標

        Args:
            dashboard_uid: 儀表板 UID

        Returns:
            Dict[str, Any]: 儀表板指標資訊
        """
        try:
            # 這裡可以實現儀表板使用統計
            # 目前返回基本資訊
            dashboard = self.grafana_api.dashboard.get_dashboard(dashboard_uid)

            metrics = {
                "uid": dashboard_uid,
                "title": dashboard.get("dashboard", {}).get("title", "Unknown"),
                "panels_count": len(dashboard.get("dashboard", {}).get("panels", [])),
                "tags": dashboard.get("dashboard", {}).get("tags", []),
                "last_updated": datetime.now().isoformat(),
                "version": dashboard.get("dashboard", {}).get("version", 0),
            }

            return metrics

        except Exception as e:
            module_logger.error(f"獲取儀表板指標失敗: {e}")
            return {}

    def backup_all_dashboards(self, backup_dir: Optional[str] = None) -> bool:
        """
        備份所有儀表板

        Args:
            backup_dir: 備份目錄，可選

        Returns:
            bool: 備份成功返回 True，否則返回 False
        """
        try:
            if backup_dir is None:
                backup_dir = (
                    Path(CACHE_DIR)
                    / "grafana_backup"
                    / datetime.now().strftime("%Y%m%d_%H%M%S")
                )
            else:
                backup_dir = Path(backup_dir)

            backup_dir.mkdir(parents=True, exist_ok=True)

            # 獲取所有儀表板
            dashboards = self.get_dashboard_list()

            success_count = 0
            for dashboard in dashboards:
                try:
                    uid = dashboard.get("uid")
                    title = dashboard.get("title", "unknown")

                    if uid:
                        # 匯出儀表板
                        config = self.export_dashboard(uid)
                        if config:
                            # 儲存到備份目錄
                            filename = f"{title.replace('/', '_')}_{uid}.json"
                            backup_file = backup_dir / filename

                            with open(backup_file, "w", encoding="utf-8") as f:
                                f.write(config)

                            success_count += 1

                except Exception as e:
                    module_logger.error(
                        f"備份儀表板 {dashboard.get('title')} 失敗: {e}"
                    )

            module_logger.info(
                f"儀表板備份完成: {success_count}/{len(dashboards)} 成功"
            )
            return success_count > 0

        except Exception as e:
            module_logger.error(f"備份所有儀表板失敗: {e}")
            return False

    def get_available_templates(self) -> List[str]:
        """
        獲取可用的儀表板模板列表

        Returns:
            List[str]: 模板名稱列表
        """
        try:
            templates = []
            for template_file in self.templates_dir.glob("*.json"):
                templates.append(template_file.stem)
            return templates

        except Exception as e:
            module_logger.error(f"獲取模板列表失敗: {e}")
            return []

    def is_healthy(self) -> bool:
        """
        檢查 Grafana 配置管理器健康狀態

        Returns:
            bool: 健康返回 True，否則返回 False
        """
        return self.test_connection()
