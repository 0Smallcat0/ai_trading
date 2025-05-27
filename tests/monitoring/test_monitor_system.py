"""測試監控系統

此模組包含 MonitorSystem 類別的單元測試。
"""

import pytest
import unittest.mock as mock
from unittest.mock import MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.monitoring.monitor_system import MonitorSystem


class TestMonitorSystem:
    """測試 MonitorSystem 類別"""

    @pytest.fixture
    def mock_monitor_modules(self):
        """模擬監控模組"""
        with patch('src.monitoring.monitor_system.AlertHandler') as mock_alert, \
             patch('src.monitoring.monitor_system.SystemMonitor') as mock_system, \
             patch('src.monitoring.monitor_system.ThresholdChecker') as mock_threshold:
            
            # 設置模擬實例
            mock_alert.return_value = MagicMock()
            mock_system.return_value = MagicMock()
            mock_threshold.return_value = MagicMock()
            
            yield {
                'alert': mock_alert,
                'system': mock_system,
                'threshold': mock_threshold
            }

    @pytest.fixture
    def mock_external_components(self):
        """模擬外部組件"""
        with patch('src.monitoring.monitor_system.prometheus_exporter') as mock_prometheus, \
             patch('src.monitoring.monitor_system.alert_manager') as mock_alert_mgr:
            
            mock_prometheus.configure = MagicMock()
            mock_alert_mgr.configure = MagicMock()
            mock_alert_mgr.start = MagicMock()
            mock_alert_mgr.stop = MagicMock()
            
            yield {
                'prometheus': mock_prometheus,
                'alert_manager': mock_alert_mgr
            }

    @pytest.fixture
    def monitor_system(self, mock_monitor_modules, mock_external_components):
        """創建測試用的 MonitorSystem 實例"""
        config = {
            "prometheus_port": 9090,
            "grafana_port": 3000,
            "alert_check_interval": 60,
            "thresholds": {
                "system": {"cpu_usage": 80},
                "api": {"latency": 1.0},
                "model": {"accuracy": 0.8},
                "trade": {"success_rate": 0.7}
            }
        }
        return MonitorSystem(config)

    def test_init_success(self, mock_monitor_modules, mock_external_components):
        """測試成功初始化"""
        config = {
            "prometheus_port": 9090,
            "alert_check_interval": 60,
            "thresholds": {"system": {"cpu_usage": 80}}
        }
        
        system = MonitorSystem(config)
        
        assert system.config == config
        assert system.prometheus_exporter is not None
        assert system.alert_handler is not None
        assert system.threshold_checker is not None
        assert system.system_monitor is not None

    def test_init_without_modules(self):
        """測試沒有必要模組時的初始化"""
        with patch('src.monitoring.monitor_system.AlertHandler', None):
            with pytest.raises(ImportError, match="監控模組未正確安裝"):
                MonitorSystem()

    def test_get_default_config(self, mock_monitor_modules, mock_external_components):
        """測試獲取預設配置"""
        system = MonitorSystem()
        
        config = system._get_default_config()
        
        assert 'prometheus_port' in config
        assert 'alert_check_interval' in config
        assert 'thresholds' in config
        assert config['thresholds']['system']['cpu_usage'] == 80

    def test_start_success(self, monitor_system):
        """測試成功啟動監控系統"""
        # 設置系統監控器返回成功
        monitor_system.system_monitor.start.return_value = True
        
        result = monitor_system.start()
        
        assert result is True
        monitor_system.system_monitor.start.assert_called_once()

    def test_start_no_system_monitor(self, monitor_system):
        """測試沒有系統監控器時啟動"""
        monitor_system.system_monitor = None
        
        result = monitor_system.start()
        
        assert result is False

    def test_start_system_monitor_failure(self, monitor_system):
        """測試系統監控器啟動失敗"""
        monitor_system.system_monitor.start.return_value = False
        
        result = monitor_system.start()
        
        assert result is False

    def test_stop_success(self, monitor_system):
        """測試成功停止監控系統"""
        # 設置系統監控器返回成功
        monitor_system.system_monitor.stop.return_value = True
        
        result = monitor_system.stop()
        
        assert result is True
        monitor_system.system_monitor.stop.assert_called_once()

    def test_stop_system_monitor_failure(self, monitor_system):
        """測試系統監控器停止失敗"""
        monitor_system.system_monitor.stop.return_value = False
        
        result = monitor_system.stop()
        
        assert result is False

    def test_stop_no_system_monitor(self, monitor_system):
        """測試沒有系統監控器時停止"""
        monitor_system.system_monitor = None
        
        result = monitor_system.stop()
        
        assert result is True

    def test_get_status_complete(self, monitor_system):
        """測試獲取完整系統狀態"""
        # 設置系統監控器狀態
        monitor_system.system_monitor.get_status.return_value = {
            "running": True,
            "check_interval": 60
        }
        monitor_system.system_monitor.is_healthy.return_value = True
        
        # 設置警報處理器狀態
        monitor_system.alert_handler.get_alert_stats.return_value = {
            "total_alerts": 5,
            "active_alerts": 2
        }
        monitor_system.alert_handler.is_healthy.return_value = True
        
        result = monitor_system.get_status()
        
        assert result['components']['system_monitor'] is True
        assert result['components']['alert_handler'] is True
        assert result['health']['overall'] is True
        assert 'system_monitor' in result
        assert 'alert_handler' in result

    def test_get_status_partial(self, monitor_system):
        """測試獲取部分系統狀態"""
        # 設置部分組件不可用
        monitor_system.alert_handler = None
        
        monitor_system.system_monitor.get_status.return_value = {"running": True}
        monitor_system.system_monitor.is_healthy.return_value = True
        
        result = monitor_system.get_status()
        
        assert result['components']['system_monitor'] is True
        assert result['components']['alert_handler'] is False
        assert result['health']['overall'] is True  # 只要有一個健康就是 True

    def test_force_check_success(self, monitor_system):
        """測試成功強制檢查"""
        monitor_system.system_monitor.force_check.return_value = True
        
        result = monitor_system.force_check()
        
        assert result is True
        monitor_system.system_monitor.force_check.assert_called_once()

    def test_force_check_no_system_monitor(self, monitor_system):
        """測試沒有系統監控器時強制檢查"""
        monitor_system.system_monitor = None
        
        result = monitor_system.force_check()
        
        assert result is False

    def test_force_check_failure(self, monitor_system):
        """測試強制檢查失敗"""
        monitor_system.system_monitor.force_check.return_value = False
        
        result = monitor_system.force_check()
        
        assert result is False

    def test_is_healthy_true(self, monitor_system):
        """測試健康檢查 - 健康"""
        monitor_system.system_monitor.is_healthy.return_value = True
        
        result = monitor_system.is_healthy()
        
        assert result is True

    def test_is_healthy_false_no_system_monitor(self, monitor_system):
        """測試健康檢查 - 沒有系統監控器"""
        monitor_system.system_monitor = None
        
        result = monitor_system.is_healthy()
        
        assert result is False

    def test_is_healthy_false_unhealthy_monitor(self, monitor_system):
        """測試健康檢查 - 系統監控器不健康"""
        monitor_system.system_monitor.is_healthy.return_value = False
        
        result = monitor_system.is_healthy()
        
        assert result is False

    def test_init_components_prometheus_configure(self, mock_monitor_modules, mock_external_components):
        """測試初始化組件時配置 Prometheus"""
        config = {
            "prometheus_port": 9090,
            "prometheus_collection_interval": 15,
            "api_endpoints": ["http://localhost:8000"]
        }
        
        # 設置 prometheus_exporter 有 configure 方法
        mock_external_components['prometheus'].configure = MagicMock()
        
        system = MonitorSystem(config)
        
        # 驗證 configure 被調用
        mock_external_components['prometheus'].configure.assert_called_once_with(
            port=9090,
            collection_interval=15,
            api_endpoints=["http://localhost:8000"]
        )

    def test_init_components_alert_manager_configure(self, mock_monitor_modules, mock_external_components):
        """測試初始化組件時配置警報管理器"""
        config = {
            "alert_log_dir": "logs/alerts",
            "alert_check_interval": 60,
            "email_config": {"smtp_server": "localhost"},
            "slack_webhook_url": "https://hooks.slack.com/test",
            "sms_config": {"provider": "test"}
        }
        
        # 設置 alert_manager 有 configure 方法
        mock_external_components['alert_manager'].configure = MagicMock()
        
        system = MonitorSystem(config)
        
        # 驗證 configure 被調用
        mock_external_components['alert_manager'].configure.assert_called_once_with(
            alert_log_dir="logs/alerts",
            check_interval=60,
            email_config={"smtp_server": "localhost"},
            slack_webhook_url="https://hooks.slack.com/test",
            sms_config={"provider": "test"}
        )
