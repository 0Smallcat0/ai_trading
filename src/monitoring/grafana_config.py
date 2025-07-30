"""Grafana 配置管理器

此模組實現了 Grafana 儀表板配置管理功能，整合各個子模組：
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
    from .grafana_modules import (
        GrafanaDashboardManager,
        DatasourceManager,
        TemplateGenerator,
    )
except ImportError:
    # 提供 fallback
    GrafanaDashboardManager = None
    DatasourceManager = None
    TemplateGenerator = None

try:
    from src.config import CACHE_DIR
except ImportError:
    CACHE_DIR = "cache"

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class GrafanaConfigManager:
    """Grafana 配置管理器

    整合各個子模組的 Grafana 配置管理器，提供統一的介面。

    Attributes:
        grafana_api: Grafana API 客戶端
        config_dir: 配置檔案目錄
        dashboard_manager: 儀表板管理器
        datasource_manager: 數據源管理器
        template_generator: 模板生成器
    """

    def __init__(
        self,
        grafana_host: str = "http://localhost:3000",
        grafana_token: Optional[str] = None,
        config_dir: Optional[Path] = None,
    ):
        """初始化 Grafana 配置管理器

        Args:
            grafana_host: Grafana 服務器地址
            grafana_token: Grafana API Token
            config_dir: 配置檔案目錄

        Raises:
            ImportError: 當必要套件未安裝時
        """
        if not GRAFANA_API_AVAILABLE:
            module_logger.warning("grafana-api 套件未安裝，部分功能將不可用")
            self.grafana_api = None
        else:
            self.grafana_api = GrafanaFace(auth=grafana_token, host=grafana_host)

        self.config_dir = config_dir or Path(CACHE_DIR) / "grafana_config"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 初始化子管理器
        self._init_managers()

        module_logger.info("Grafana 配置管理器初始化成功")

    def _init_managers(self) -> None:
        """初始化各個子管理器"""
        try:
            # 初始化儀表板管理器
            if GrafanaDashboardManager is not None:
                self.dashboard_manager = GrafanaDashboardManager(
                    self.grafana_api, self.config_dir
                )
                module_logger.info("儀表板管理器初始化成功")
            else:
                self.dashboard_manager = None

            # 初始化數據源管理器
            if DatasourceManager is not None:
                self.datasource_manager = DatasourceManager(
                    self.grafana_api, self.config_dir
                )
                module_logger.info("數據源管理器初始化成功")
            else:
                self.datasource_manager = None

            # 初始化模板生成器
            if TemplateGenerator is not None:
                self.template_generator = TemplateGenerator()
                module_logger.info("模板生成器初始化成功")
            else:
                self.template_generator = None

        except Exception as e:
            module_logger.error("初始化子管理器失敗: %s", e)
            raise

    def deploy_all_configurations(self) -> Dict[str, Any]:
        """部署所有 Grafana 配置

        Returns:
            Dict[str, Any]: 部署結果字典
        """
        results = {
            "datasources": {},
            "dashboards": {},
            "timestamp": datetime.now().isoformat(),
            "success": False,
        }

        try:
            # 部署數據源
            if self.datasource_manager:
                datasource_results = self.datasource_manager.deploy_all_datasources()
                results["datasources"] = datasource_results
                module_logger.info("數據源部署完成")

            # 部署儀表板
            if self.dashboard_manager:
                dashboard_results = self.dashboard_manager.deploy_all_templates()
                results["dashboards"] = dashboard_results
                module_logger.info("儀表板部署完成")

            # 檢查整體成功狀態
            datasource_success = any(results["datasources"].values())
            dashboard_success = any(
                url is not None for url in results["dashboards"].values()
            )
            results["success"] = datasource_success or dashboard_success

            module_logger.info("Grafana 配置部署完成，成功: %s", results["success"])

        except Exception as e:
            module_logger.error("部署 Grafana 配置失敗: %s", e)
            results["error"] = str(e)

        return results

    def create_custom_dashboard(
        self, title: str, tags: List[str], panel_configs: List[Dict[str, Any]]
    ) -> Optional[str]:
        """創建自定義儀表板

        Args:
            title: 儀表板標題
            tags: 標籤列表
            panel_configs: 面板配置列表

        Returns:
            Optional[str]: 成功返回儀表板 URL，失敗返回 None
        """
        try:
            if not self.template_generator or not self.dashboard_manager:
                module_logger.error("模板生成器或儀表板管理器未初始化")
                return None

            # 生成儀表板配置
            dashboard_config = self.template_generator.generate_custom_dashboard(
                title, tags, panel_configs
            )

            # 部署儀表板
            dashboard_url = self.dashboard_manager.deploy_dashboard(dashboard_config)

            if dashboard_url:
                module_logger.info("自定義儀表板創建成功: %s", dashboard_url)
            else:
                module_logger.error("自定義儀表板創建失敗")

            return dashboard_url

        except Exception as e:
            module_logger.error("創建自定義儀表板失敗: %s", e)
            return None

    def get_system_status(self) -> Dict[str, Any]:
        """獲取系統狀態

        Returns:
            Dict[str, Any]: 系統狀態字典
        """
        status = {
            "grafana_api_available": GRAFANA_API_AVAILABLE,
            "grafana_connected": False,
            "managers": {
                "dashboard_manager": self.dashboard_manager is not None,
                "datasource_manager": self.datasource_manager is not None,
                "template_generator": self.template_generator is not None,
            },
            "config_dir": str(self.config_dir),
            "timestamp": datetime.now().isoformat(),
        }

        # 測試 Grafana 連接
        if self.grafana_api:
            try:
                # 嘗試獲取健康狀態
                health = self.grafana_api.health.check()
                status["grafana_connected"] = health.get("database") == "ok"
            except Exception as e:
                module_logger.error("檢查 Grafana 連接失敗: %s", e)
                status["grafana_error"] = str(e)

        return status

    def export_configuration(self, export_path: Optional[Path] = None) -> bool:
        """匯出配置到檔案

        Args:
            export_path: 匯出路徑

        Returns:
            bool: 匯出成功返回 True，否則返回 False
        """
        try:
            if export_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                export_path = self.config_dir / f"grafana_export_{timestamp}.json"

            export_data = {
                "timestamp": datetime.now().isoformat(),
                "system_status": self.get_system_status(),
                "configuration": {"datasources": [], "dashboards": []},
            }

            # 匯出數據源配置
            if self.datasource_manager:
                datasources = self.datasource_manager.get_datasources()
                if datasources:
                    export_data["configuration"]["datasources"] = datasources

            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            module_logger.info("配置匯出成功: %s", export_path)
            return True

        except Exception as e:
            module_logger.error("匯出配置失敗: %s", e)
            return False

    def is_healthy(self) -> bool:
        """檢查管理器健康狀態

        Returns:
            bool: 健康返回 True，否則返回 False
        """
        try:
            # 檢查基本組件
            if not any(
                [
                    self.dashboard_manager,
                    self.datasource_manager,
                    self.template_generator,
                ]
            ):
                return False

            # 檢查 Grafana 連接（如果可用）
            if self.grafana_api:
                try:
                    health = self.grafana_api.health.check()
                    return health.get("database") == "ok"
                except Exception:
                    return False

            return True

        except Exception as e:
            module_logger.error("健康檢查失敗: %s", e)
            return False
