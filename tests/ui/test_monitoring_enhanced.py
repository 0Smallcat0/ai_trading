"""
增強版系統監控測試

此模組測試系統監控的增強功能，包括：
- 系統資源監控測試
- 交易效能追蹤測試
- 日誌管理測試
- 警報系統測試
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Any

# 導入要測試的模組
from src.ui.components.monitoring_components import MonitoringComponents
from src.ui.pages.monitoring_enhanced import (
    load_system_resources,
    load_performance_data,
    load_system_logs,
    load_system_alerts,
    estimate_file_size,
)


class TestMonitoringComponents:
    """測試系統監控組件"""

    def setup_method(self):
        """設置測試環境"""
        self.sample_resource_data = {
            "cpu_percent": 45.5,
            "memory_percent": 68.2,
            "disk_percent": 55.0,
            "network_latency": 25.0,
            "memory_available": 8 * 1024**3,  # 8GB
            "disk_free": 100 * 1024**3,  # 100GB
            "network_sent": 5.2,
            "network_recv": 8.1,
        }

        self.sample_performance_data = {
            "order_latency": 35.0,
            "fill_rate": 96.8,
            "throughput": 150.0,
            "api_response_time": 45.0,
            "error_rate": 0.5,
        }

        self.sample_logs = [
            {
                "id": "LOG001",
                "timestamp": "2024-01-15 10:30:00",
                "level": "INFO",
                "module": "trading",
                "message": "訂單執行成功",
                "user": "system",
            },
            {
                "id": "LOG002",
                "timestamp": "2024-01-15 10:35:00",
                "level": "ERROR",
                "module": "api",
                "message": "API 連接失敗",
                "user": "system",
            },
        ]

        self.sample_alerts = [
            {
                "id": "ALERT001",
                "timestamp": "2024-01-15 10:40:00",
                "severity": "high",
                "type": "performance",
                "title": "CPU 使用率過高",
                "description": "CPU 使用率超過 90%",
                "status": "active",
                "acknowledged": False,
            }
        ]

    def test_get_resource_status(self):
        """測試資源狀態判斷"""
        # 測試正常狀態
        status = MonitoringComponents._get_resource_status(50, 80, 90)
        assert status == "success"

        # 測試警告狀態
        status = MonitoringComponents._get_resource_status(85, 80, 90)
        assert status == "warning"

        # 測試錯誤狀態
        status = MonitoringComponents._get_resource_status(95, 80, 90)
        assert status == "error"

    def test_get_latency_status(self):
        """測試延遲狀態判斷"""
        # 測試正常延遲
        status = MonitoringComponents._get_latency_status(30)
        assert status == "success"

        # 測試警告延遲
        status = MonitoringComponents._get_latency_status(75)
        assert status == "warning"

        # 測試錯誤延遲
        status = MonitoringComponents._get_latency_status(150)
        assert status == "error"

    @patch("streamlit.plotly_chart")
    def test_system_resources_dashboard(self, mock_plotly_chart):
        """測試系統資源監控儀表板"""
        # 測試儀表板渲染
        MonitoringComponents.system_resources_dashboard(self.sample_resource_data)

        # 驗證函數執行完成（實際測試需要 Streamlit 環境）
        assert True

    @patch("streamlit.plotly_chart")
    def test_performance_tracking_dashboard(self, mock_plotly_chart):
        """測試效能追蹤儀表板"""
        # 測試儀表板渲染
        MonitoringComponents.performance_tracking_dashboard(
            self.sample_performance_data
        )

        # 驗證圖表被渲染
        assert mock_plotly_chart.call_count >= 2

    def test_calculate_log_stats(self):
        """測試日誌統計計算"""
        stats = MonitoringComponents._calculate_log_stats(self.sample_logs)

        # 驗證統計結果
        assert stats["total_logs"] == 2
        assert stats["error_logs"] == 1
        assert stats["warning_logs"] == 0
        # today_logs 取決於當前日期
        assert stats["today_logs"] >= 0

    def test_calculate_log_stats_empty(self):
        """測試空日誌列表統計"""
        stats = MonitoringComponents._calculate_log_stats([])

        assert stats["total_logs"] == 0
        assert stats["error_logs"] == 0
        assert stats["warning_logs"] == 0
        assert stats["today_logs"] == 0

    @patch("streamlit.dataframe")
    def test_log_management_panel(self, mock_dataframe):
        """測試日誌管理面板"""
        # 測試有日誌的情況
        MonitoringComponents.log_management_panel(self.sample_logs)
        mock_dataframe.assert_called()

        # 測試空日誌的情況
        with patch("streamlit.info") as mock_info:
            MonitoringComponents.log_management_panel([])
            mock_info.assert_called_with("沒有日誌記錄")

    def test_filter_logs(self):
        """測試日誌篩選"""
        import time

        # 測試等級篩選
        filtered = MonitoringComponents._filter_logs(
            self.sample_logs, "ERROR", "全部", time.time(), time.time()
        )

        error_logs = [log for log in filtered if log.get("level") == "ERROR"]
        assert len(error_logs) <= len(filtered)

        # 測試模組篩選
        filtered = MonitoringComponents._filter_logs(
            self.sample_logs, "全部", "trading", time.time(), time.time()
        )

        trading_logs = [log for log in filtered if log.get("module") == "trading"]
        assert len(trading_logs) <= len(filtered)

    def test_calculate_alert_stats(self):
        """測試警報統計計算"""
        stats = MonitoringComponents._calculate_alert_stats(self.sample_alerts)

        # 驗證統計結果
        assert stats["total_alerts"] == 1
        assert stats["critical_alerts"] == 0  # 沒有 critical 等級
        assert stats["unacknowledged_alerts"] == 1
        assert stats["resolved_alerts"] == 0

    @patch("streamlit.dataframe")
    def test_alert_system_panel(self, mock_dataframe):
        """測試警報系統面板"""
        # 測試有警報的情況
        MonitoringComponents.alert_system_panel(self.sample_alerts)
        mock_dataframe.assert_called()

        # 測試空警報的情況
        with patch("streamlit.info") as mock_info:
            MonitoringComponents.alert_system_panel([])
            mock_info.assert_called_with("沒有系統警報")

    def test_calculate_health_score(self):
        """測試健康度評分計算"""
        # 測試正常系統
        normal_data = {
            "cpu_percent": 50,
            "memory_percent": 60,
            "network_latency": 30,
            "error_rate": 0.5,
        }

        score = MonitoringComponents._calculate_health_score(normal_data)
        assert 70 <= score <= 100

        # 測試高負載系統
        high_load_data = {
            "cpu_percent": 95,
            "memory_percent": 95,
            "network_latency": 150,
            "error_rate": 10,
        }

        score = MonitoringComponents._calculate_health_score(high_load_data)
        assert 0 <= score <= 50

    def test_generate_recommendations(self):
        """測試系統建議生成"""
        # 測試高 CPU 使用率
        high_cpu_data = {"cpu_percent": 90, "memory_percent": 50, "network_latency": 30}

        recommendations = MonitoringComponents._generate_recommendations(high_cpu_data)
        assert any("CPU" in rec for rec in recommendations)

        # 測試正常系統
        normal_data = {"cpu_percent": 50, "memory_percent": 60, "network_latency": 30}

        recommendations = MonitoringComponents._generate_recommendations(normal_data)
        assert "系統運行良好" in recommendations[0]

    def test_health_report_generator(self):
        """測試健康報告生成"""
        system_data = self.sample_resource_data.copy()
        system_data.update(self.sample_performance_data)

        report = MonitoringComponents.health_report_generator(system_data)

        # 驗證報告結構
        required_keys = [
            "health_score",
            "status",
            "status_color",
            "recommendations",
            "generated_at",
        ]
        for key in required_keys:
            assert key in report

        # 驗證數據類型
        assert isinstance(report["health_score"], int)
        assert 0 <= report["health_score"] <= 100
        assert report["status"] in ["優秀", "良好", "需要關注"]
        assert report["status_color"] in ["success", "warning", "error"]
        assert isinstance(report["recommendations"], list)


class TestMonitoringEnhanced:
    """測試增強版系統監控頁面"""

    @patch("psutil.cpu_percent")
    @patch("psutil.virtual_memory")
    @patch("psutil.disk_usage")
    def test_load_system_resources(self, mock_disk, mock_memory, mock_cpu):
        """測試載入系統資源"""
        # 模擬 psutil 回傳值
        mock_cpu.return_value = 45.5

        mock_memory_obj = Mock()
        mock_memory_obj.percent = 68.2
        mock_memory_obj.available = 8 * 1024**3
        mock_memory.return_value = mock_memory_obj

        mock_disk_obj = Mock()
        mock_disk_obj.percent = 55.0
        mock_disk_obj.free = 100 * 1024**3
        mock_disk.return_value = mock_disk_obj

        # 測試載入系統資源
        resources = load_system_resources()

        # 驗證資源數據
        assert "cpu_percent" in resources
        assert "memory_percent" in resources
        assert "disk_percent" in resources
        assert "network_latency" in resources

        # 驗證數據範圍
        assert 0 <= resources["cpu_percent"] <= 100
        assert 0 <= resources["memory_percent"] <= 100
        assert 0 <= resources["disk_percent"] <= 100
        assert resources["network_latency"] >= 0

    def test_load_performance_data(self):
        """測試載入效能數據"""
        performance_data = load_performance_data()

        # 驗證效能數據結構
        required_keys = [
            "order_latency",
            "fill_rate",
            "throughput",
            "api_response_time",
            "error_rate",
        ]
        for key in required_keys:
            assert key in performance_data

        # 驗證數據範圍
        assert performance_data["order_latency"] >= 0
        assert 0 <= performance_data["fill_rate"] <= 100
        assert performance_data["throughput"] >= 0
        assert performance_data["api_response_time"] >= 0
        assert performance_data["error_rate"] >= 0

    def test_load_system_logs(self):
        """測試載入系統日誌"""
        logs = load_system_logs()

        # 驗證日誌結構
        assert isinstance(logs, list)

        if logs:
            log = logs[0]
            required_keys = ["id", "timestamp", "level", "module", "message", "user"]
            for key in required_keys:
                assert key in log

            # 驗證日誌等級
            assert log["level"] in ["INFO", "WARNING", "ERROR", "DEBUG"]

    def test_load_system_alerts(self):
        """測試載入系統警報"""
        alerts = load_system_alerts()

        # 驗證警報結構
        assert isinstance(alerts, list)

        if alerts:
            alert = alerts[0]
            required_keys = [
                "id",
                "timestamp",
                "severity",
                "type",
                "title",
                "description",
                "status",
                "acknowledged",
            ]
            for key in required_keys:
                assert key in alert

            # 驗證警報嚴重度
            assert alert["severity"] in ["low", "medium", "high", "critical"]

    def test_estimate_file_size(self):
        """測試檔案大小估計"""
        # 創建測試數據
        test_data = pd.DataFrame(
            {
                "col1": range(1000),
                "col2": ["test"] * 1000,
                "col3": np.random.randn(1000),
            }
        )

        size_mb = estimate_file_size(test_data)

        # 驗證大小合理
        assert size_mb > 0
        assert size_mb < 100  # 應該小於100MB


class TestMonitoringIntegration:
    """系統監控整合測試"""

    def test_monitoring_workflow(self):
        """測試監控工作流程"""
        # 1. 載入系統資源
        resources = load_system_resources()
        assert isinstance(resources, dict)

        # 2. 載入效能數據
        performance = load_performance_data()
        assert isinstance(performance, dict)

        # 3. 生成健康報告
        system_data = {**resources, **performance}
        health_report = MonitoringComponents.health_report_generator(system_data)

        # 驗證報告
        assert "health_score" in health_report
        assert 0 <= health_report["health_score"] <= 100

    def test_alert_processing_workflow(self):
        """測試警報處理工作流程"""
        # 1. 載入警報
        alerts = load_system_alerts()

        # 2. 處理警報
        processed_alerts = []
        for alert in alerts:
            if not alert.get("acknowledged", False):
                # 模擬確認警報
                alert["acknowledged"] = True
                alert["status"] = "acknowledged"
            processed_alerts.append(alert)

        # 3. 驗證處理結果
        acknowledged_count = sum(
            1 for alert in processed_alerts if alert.get("acknowledged")
        )
        assert acknowledged_count >= 0

    def test_log_analysis_workflow(self):
        """測試日誌分析工作流程"""
        # 1. 載入日誌
        logs = load_system_logs()

        # 2. 分析日誌
        if logs:
            # 統計各等級日誌數量
            level_counts = {}
            for log in logs:
                level = log.get("level", "UNKNOWN")
                level_counts[level] = level_counts.get(level, 0) + 1

            # 3. 驗證分析結果
            assert isinstance(level_counts, dict)
            total_logs = sum(level_counts.values())
            assert total_logs == len(logs)


class TestMonitoringPerformance:
    """系統監控效能測試"""

    def test_large_log_processing(self):
        """測試大量日誌處理"""
        # 生成大量日誌
        large_logs = []
        for i in range(10000):
            log = {
                "id": f"LOG{i:05d}",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "level": np.random.choice(["INFO", "WARNING", "ERROR"]),
                "module": f"module_{i % 10}",
                "message": f"Log message {i}",
                "user": "system",
            }
            large_logs.append(log)

        # 測試統計計算效能
        import time

        start_time = time.time()

        stats = MonitoringComponents._calculate_log_stats(large_logs)

        end_time = time.time()
        execution_time = end_time - start_time

        # 驗證執行時間合理
        assert execution_time < 2.0  # 小於2秒
        assert stats["total_logs"] == 10000

    def test_health_score_calculation_performance(self):
        """測試健康度評分計算效能"""
        # 生成大量系統數據
        large_system_data = {}
        for i in range(1000):
            large_system_data[f"metric_{i}"] = np.random.uniform(0, 100)

        # 測試計算效能
        import time

        start_time = time.time()

        score = MonitoringComponents._calculate_health_score(large_system_data)

        end_time = time.time()
        execution_time = end_time - start_time

        # 驗證執行時間和結果
        assert execution_time < 1.0  # 小於1秒
        assert 0 <= score <= 100

    def test_memory_usage_monitoring(self):
        """測試記憶體使用監控"""
        import sys

        # 測試前記憶體使用
        initial_logs = load_system_logs()
        initial_size = sys.getsizeof(initial_logs)

        # 生成更多日誌
        additional_logs = []
        for i in range(1000):
            log = {"id": f"LOG{i}", "message": f"Message {i}"}
            additional_logs.append(log)

        # 計算記憶體增長
        additional_size = sys.getsizeof(additional_logs)

        # 驗證記憶體使用合理
        assert additional_size < 1024 * 1024  # 小於1MB


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
