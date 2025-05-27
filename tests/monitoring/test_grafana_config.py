"""測試 Grafana 配置管理器

此模組包含 GrafanaConfigManager 類別的單元測試。
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
)

from src.monitoring.grafana_config import GrafanaConfigManager


class TestGrafanaConfigManager:
    """測試 GrafanaConfigManager 類別"""

    @pytest.fixture
    def temp_dir(self):
        """創建臨時目錄"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_grafana_modules(self):
        """模擬 Grafana 模組"""
        with patch(
            'src.monitoring.grafana_config.DashboardManager'
        ) as mock_dashboard, patch(
            'src.monitoring.grafana_config.DatasourceManager'
        ) as mock_datasource, patch(
            'src.monitoring.grafana_config.TemplateGenerator'
        ) as mock_template, patch(
            'src.monitoring.grafana_config.GRAFANA_API_AVAILABLE', True
        ):

            # 設置模擬實例
            mock_dashboard.return_value = MagicMock()
            mock_datasource.return_value = MagicMock()
            mock_template.return_value = MagicMock()

            yield {
                'dashboard': mock_dashboard,
                'datasource': mock_datasource,
                'template': mock_template
            }

    @pytest.fixture
    def mock_grafana_api(self):
        """模擬 Grafana API"""
        with patch('src.monitoring.grafana_config.GrafanaFace') as mock_face:
            mock_api = MagicMock()
            mock_face.return_value = mock_api
            yield mock_api

    @pytest.fixture
    def config_manager(self, mock_grafana_modules, mock_grafana_api, temp_dir):
        """創建測試用的 GrafanaConfigManager 實例"""
        return GrafanaConfigManager(
            grafana_host="http://localhost:3000",
            grafana_token="test_token",
            config_dir=temp_dir
        )

    def test_init_success(self, mock_grafana_modules, mock_grafana_api, temp_dir):
        """測試成功初始化"""
        manager = GrafanaConfigManager(
            grafana_host="http://localhost:3000",
            grafana_token="test_token",
            config_dir=temp_dir
        )

        assert manager.grafana_api is not None
        assert manager.config_dir == temp_dir
        assert manager.dashboard_manager is not None
        assert manager.datasource_manager is not None
        assert manager.template_generator is not None

    def test_init_without_grafana_api(self, mock_grafana_modules, temp_dir):
        """測試沒有 Grafana API 時的初始化"""
        with patch('src.monitoring.grafana_config.GRAFANA_API_AVAILABLE', False):
            manager = GrafanaConfigManager(config_dir=temp_dir)

            assert manager.grafana_api is None
            # 子管理器應該仍然被初始化，但可能功能受限

    def test_deploy_all_configurations_success(self, config_manager):
        """測試成功部署所有配置"""
        # 設置子管理器返回成功結果
        config_manager.datasource_manager.deploy_all_datasources.return_value = {
            "prometheus.json": True
        }
        config_manager.dashboard_manager.deploy_all_templates.return_value = {
            "system_overview.json": "http://localhost:3000/d/abc123"
        }

        result = config_manager.deploy_all_configurations()

        assert result['success'] is True
        assert 'datasources' in result
        assert 'dashboards' in result
        assert 'timestamp' in result

    def test_deploy_all_configurations_failure(self, config_manager):
        """測試部署配置失敗"""
        # 設置子管理器返回失敗結果
        config_manager.datasource_manager.deploy_all_datasources.return_value = {
            "prometheus.json": False
        }
        config_manager.dashboard_manager.deploy_all_templates.return_value = {
            "system_overview.json": None
        }

        result = config_manager.deploy_all_configurations()

        assert result['success'] is False

    def test_create_custom_dashboard_success(self, config_manager):
        """測試成功創建自定義儀表板"""
        # 設置模板生成器和儀表板管理器
        mock_config = {"dashboard": {"title": "Test Dashboard"}}
        config_manager.template_generator.generate_custom_dashboard.return_value = (
            mock_config
        )
        config_manager.dashboard_manager.deploy_dashboard.return_value = (
            "http://localhost:3000/d/test123"
        )

        panel_configs = [
            {
                "title": "Test Panel",
                "type": "stat",
                "metric": "test_metric",
                "grid_pos": {"h": 8, "w": 12, "x": 0, "y": 0}
            }
        ]

        result = config_manager.create_custom_dashboard(
            "Test Dashboard",
            ["test"],
            panel_configs
        )

        assert result == "http://localhost:3000/d/test123"
        config_manager.template_generator.generate_custom_dashboard.assert_called_once()
        config_manager.dashboard_manager.deploy_dashboard.assert_called_once()

    def test_create_custom_dashboard_no_managers(self, config_manager):
        """測試沒有管理器時創建自定義儀表板"""
        config_manager.template_generator = None
        config_manager.dashboard_manager = None

        result = config_manager.create_custom_dashboard("Test", ["test"], [])

        assert result is None

    def test_get_system_status_healthy(self, config_manager):
        """測試獲取系統狀態 - 健康"""
        # 設置 Grafana API 健康檢查
        config_manager.grafana_api.health.check.return_value = {"database": "ok"}

        result = config_manager.get_system_status()

        assert result['grafana_api_available'] is True
        assert result['grafana_connected'] is True
        assert result['managers']['dashboard_manager'] is True
        assert result['managers']['datasource_manager'] is True
        assert result['managers']['template_generator'] is True

    def test_get_system_status_unhealthy(self, config_manager):
        """測試獲取系統狀態 - 不健康"""
        # 設置 Grafana API 健康檢查失敗
        config_manager.grafana_api.health.check.side_effect = Exception(
            "Connection failed"
        )

        result = config_manager.get_system_status()

        assert result['grafana_connected'] is False
        assert 'grafana_error' in result

    def test_export_configuration_success(self, config_manager, temp_dir):
        """測試成功匯出配置"""
        # 設置數據源管理器返回數據
        config_manager.datasource_manager.get_datasources.return_value = [
            {"name": "Prometheus", "type": "prometheus"}
        ]

        export_path = temp_dir / "test_export.json"
        result = config_manager.export_configuration(export_path)

        assert result is True
        assert export_path.exists()

        # 驗證匯出的內容
        import json
        with open(export_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert 'timestamp' in data
        assert 'system_status' in data
        assert 'configuration' in data

    def test_export_configuration_failure(self, config_manager):
        """測試匯出配置失敗"""
        # 設置無效路徑
        invalid_path = Path("/invalid/path/export.json")
        result = config_manager.export_configuration(invalid_path)

        assert result is False

    def test_is_healthy_true(self, config_manager):
        """測試健康檢查 - 健康"""
        # 設置 Grafana API 健康
        config_manager.grafana_api.health.check.return_value = {"database": "ok"}

        result = config_manager.is_healthy()

        assert result is True

    def test_is_healthy_false_no_managers(self, config_manager):
        """測試健康檢查 - 沒有管理器"""
        config_manager.dashboard_manager = None
        config_manager.datasource_manager = None
        config_manager.template_generator = None

        result = config_manager.is_healthy()

        assert result is False

    def test_is_healthy_false_api_error(self, config_manager):
        """測試健康檢查 - API 錯誤"""
        config_manager.grafana_api.health.check.side_effect = Exception("API Error")

        result = config_manager.is_healthy()

        assert result is False

    def test_is_healthy_no_api(self, config_manager):
        """測試健康檢查 - 沒有 API"""
        config_manager.grafana_api = None

        result = config_manager.is_healthy()

        assert result is True  # 沒有 API 時只檢查基本組件
