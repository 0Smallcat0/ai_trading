"""Grafana 數據源管理器

此模組實現 Grafana 數據源的管理功能，包括創建、更新、刪除數據源配置。
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class DatasourceManager:
    """Grafana 數據源管理器

    管理 Grafana 數據源的創建、配置和部署。

    Attributes:
        grafana_api: Grafana API 客戶端
        datasources_dir: 數據源配置目錄
    """

    def __init__(self, grafana_api: Any, config_dir: Path):
        """初始化數據源管理器

        Args:
            grafana_api: Grafana API 客戶端
            config_dir: 配置檔案根目錄

        Raises:
            Exception: 初始化失敗時拋出異常
        """
        self.grafana_api = grafana_api
        self.datasources_dir = config_dir / "grafana_datasources"

        # 確保目錄存在
        self.datasources_dir.mkdir(parents=True, exist_ok=True)

        # 初始化預設數據源配置
        self._init_default_datasources()

        module_logger.info("數據源管理器初始化成功")

    def _init_default_datasources(self) -> None:
        """初始化預設數據源配置"""
        try:
            # 創建預設 Prometheus 數據源配置
            self._create_prometheus_config()

            module_logger.info("預設數據源配置初始化完成")

        except Exception as e:
            module_logger.error("初始化預設數據源配置失敗: %s", e)

    def _create_prometheus_config(self) -> None:
        """創建預設 Prometheus 數據源配置"""
        prometheus_config = {
            "name": "Prometheus",
            "type": "prometheus",
            "url": "http://localhost:9090",
            "access": "proxy",
            "isDefault": True,
            "basicAuth": False,
            "jsonData": {
                "httpMethod": "POST",
                "timeInterval": "15s",
                "queryTimeout": "60s",
                "httpHeaderName1": "X-Custom-Header",
            },
            "secureJsonData": {"httpHeaderValue1": "custom-value"},
        }

        config_file = self.datasources_dir / "prometheus.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(prometheus_config, f, indent=2, ensure_ascii=False)

    def create_datasource(self, datasource_config: Dict[str, Any]) -> bool:
        """創建數據源

        Args:
            datasource_config: 數據源配置

        Returns:
            bool: 創建成功返回 True，否則返回 False
        """
        try:
            result = self.grafana_api.datasource.create_datasource(datasource_config)
            module_logger.info("數據源創建成功: %s", result)
            return True

        except Exception as e:
            module_logger.error("創建數據源失敗: %s", e)
            return False

    def update_datasource(
        self, datasource_id: int, datasource_config: Dict[str, Any]
    ) -> bool:
        """更新數據源

        Args:
            datasource_id: 數據源 ID
            datasource_config: 數據源配置

        Returns:
            bool: 更新成功返回 True，否則返回 False
        """
        try:
            result = self.grafana_api.datasource.update_datasource(
                datasource_id, datasource_config
            )
            module_logger.info("數據源更新成功: %s", result)
            return True

        except Exception as e:
            module_logger.error("更新數據源失敗: %s", e)
            return False

    def delete_datasource(self, datasource_id: int) -> bool:
        """刪除數據源

        Args:
            datasource_id: 數據源 ID

        Returns:
            bool: 刪除成功返回 True，否則返回 False
        """
        try:
            result = self.grafana_api.datasource.delete_datasource(datasource_id)
            module_logger.info("數據源刪除成功: %s", result)
            return True

        except Exception as e:
            module_logger.error("刪除數據源失敗: %s", e)
            return False

    def get_datasources(self) -> Optional[List[Dict[str, Any]]]:
        """獲取所有數據源

        Returns:
            Optional[List[Dict[str, Any]]]: 數據源列表，失敗返回 None
        """
        try:
            datasources = self.grafana_api.datasource.get_datasources()
            module_logger.info("獲取數據源列表成功，共 %d 個", len(datasources))
            return datasources

        except Exception as e:
            module_logger.error("獲取數據源列表失敗: %s", e)
            return None

    def get_datasource_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根據名稱獲取數據源

        Args:
            name: 數據源名稱

        Returns:
            Optional[Dict[str, Any]]: 數據源配置，失敗返回 None
        """
        try:
            datasource = self.grafana_api.datasource.get_datasource_by_name(name)
            module_logger.info("獲取數據源成功: %s", name)
            return datasource

        except Exception as e:
            module_logger.error("獲取數據源失敗: %s", e)
            return None

    def test_datasource(self, datasource_id: int) -> bool:
        """測試數據源連接

        Args:
            datasource_id: 數據源 ID

        Returns:
            bool: 測試成功返回 True，否則返回 False
        """
        try:
            result = self.grafana_api.datasource.test_datasource(datasource_id)
            if result.get("status") == "success":
                module_logger.info("數據源測試成功: %s", datasource_id)
                return True
            else:
                module_logger.warning("數據源測試失敗: %s", result)
                return False

        except Exception as e:
            module_logger.error("測試數據源失敗: %s", e)
            return False

    def load_datasource_config(self, filename: str) -> Optional[Dict[str, Any]]:
        """從檔案載入數據源配置

        Args:
            filename: 配置檔案名稱

        Returns:
            Optional[Dict[str, Any]]: 數據源配置，失敗返回 None
        """
        try:
            config_file = self.datasources_dir / filename
            if not config_file.exists():
                module_logger.error("配置檔案不存在: %s", config_file)
                return None

            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            module_logger.info("載入數據源配置成功: %s", filename)
            return config

        except Exception as e:
            module_logger.error("載入數據源配置失敗: %s", e)
            return None

    def save_datasource_config(self, filename: str, config: Dict[str, Any]) -> bool:
        """儲存數據源配置到檔案

        Args:
            filename: 配置檔案名稱
            config: 數據源配置

        Returns:
            bool: 儲存成功返回 True，否則返回 False
        """
        try:
            config_file = self.datasources_dir / filename
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            module_logger.info("儲存數據源配置成功: %s", filename)
            return True

        except Exception as e:
            module_logger.error("儲存數據源配置失敗: %s", e)
            return False

    def deploy_all_datasources(self) -> Dict[str, bool]:
        """部署所有數據源配置

        Returns:
            Dict[str, bool]: 部署結果字典，鍵為檔案名，值為部署結果
        """
        results = {}

        try:
            # 獲取所有配置檔案
            config_files = list(self.datasources_dir.glob("*.json"))

            for config_file in config_files:
                try:
                    config = self.load_datasource_config(config_file.name)
                    if config:
                        success = self.create_datasource(config)
                        results[config_file.name] = success
                    else:
                        results[config_file.name] = False

                except Exception as e:
                    module_logger.error(
                        "部署數據源配置失敗 %s: %s", config_file.name, e
                    )
                    results[config_file.name] = False

            success_count = sum(results.values())
            total_count = len(results)
            module_logger.info("數據源部署完成，成功 %d/%d", success_count, total_count)

        except Exception as e:
            module_logger.error("部署所有數據源失敗: %s", e)

        return results
