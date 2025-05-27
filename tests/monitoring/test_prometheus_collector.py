"""測試 Prometheus 指標收集器

此模組包含 PrometheusCollector 類別的單元測試。
"""

import pytest
import unittest.mock as mock
from unittest.mock import MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.monitoring.prometheus_collector import PrometheusCollector


class TestPrometheusCollector:
    """測試 PrometheusCollector 類別"""

    @pytest.fixture
    def mock_prometheus_modules(self):
        """模擬 Prometheus 模組"""
        with patch('src.monitoring.prometheus_collector.SystemMetricsCollector') as mock_system, \
             patch('src.monitoring.prometheus_collector.TradingMetricsCollector') as mock_trading, \
             patch('src.monitoring.prometheus_collector.APIMetricsCollector') as mock_api, \
             patch('src.monitoring.prometheus_collector.BusinessMetricsCollector') as mock_business:

            # 設置模擬實例
            mock_system.return_value = MagicMock()
            mock_trading.return_value = MagicMock()
            mock_api.return_value = MagicMock()
            mock_business.return_value = MagicMock()

            yield {
                'system': mock_system,
                'trading': mock_trading,
                'api': mock_api,
                'business': mock_business
            }

    @pytest.fixture
    def collector(self, mock_prometheus_modules):
        """創建測試用的 PrometheusCollector 實例"""
        return PrometheusCollector(collection_interval=15)

    def test_init_success(self, mock_prometheus_modules):
        """測試成功初始化"""
        collector = PrometheusCollector(collection_interval=10)

        assert collector.collection_interval == 10
        assert collector.is_collecting is False
        assert len(collector.collectors) == 4
        assert 'system' in collector.collectors
        assert 'trading' in collector.collectors
        assert 'api' in collector.collectors
        assert 'business' in collector.collectors

    def test_init_without_prometheus_client(self):
        """測試沒有 prometheus_client 時的初始化"""
        with patch('src.monitoring.prometheus_collector.CollectorRegistry', None):
            with pytest.raises(ImportError, match="prometheus_client 套件未安裝"):
                PrometheusCollector()

    def test_start_collection_success(self, collector):
        """測試成功啟動指標收集"""
        # 設置所有子收集器返回成功
        for sub_collector in collector.collectors.values():
            sub_collector.start_collection.return_value = True

        result = collector.start_collection()

        assert result is True
        assert collector.is_collecting is True

        # 驗證所有子收集器都被調用
        for sub_collector in collector.collectors.values():
            sub_collector.start_collection.assert_called_once()

    def test_start_collection_partial_failure(self, collector):
        """測試部分子收集器啟動失敗"""
        # 設置部分子收集器失敗
        collector.collectors['system'].start_collection.return_value = True
        collector.collectors['trading'].start_collection.return_value = False
        collector.collectors['api'].start_collection.return_value = True
        collector.collectors['business'].start_collection.return_value = True

        result = collector.start_collection()

        assert result is True  # 只要有一個成功就返回 True
        assert collector.is_collecting is True

    def test_start_collection_all_failure(self, collector):
        """測試所有子收集器啟動失敗"""
        # 設置所有子收集器失敗
        for sub_collector in collector.collectors.values():
            sub_collector.start_collection.return_value = False

        result = collector.start_collection()

        assert result is False
        assert collector.is_collecting is False

    def test_start_collection_already_running(self, collector):
        """測試已在運行時啟動收集"""
        collector.is_collecting = True

        result = collector.start_collection()

        assert result is True
        # 驗證子收集器沒有被調用
        for sub_collector in collector.collectors.values():
            sub_collector.start_collection.assert_not_called()

    def test_stop_collection_success(self, collector):
        """測試成功停止指標收集"""
        collector.is_collecting = True

        # 設置所有子收集器返回成功
        for sub_collector in collector.collectors.values():
            sub_collector.stop_collection.return_value = True

        result = collector.stop_collection()

        assert result is True
        assert collector.is_collecting is False

        # 驗證所有子收集器都被調用
        for sub_collector in collector.collectors.values():
            sub_collector.stop_collection.assert_called_once()

    def test_stop_collection_not_running(self, collector):
        """測試未運行時停止收集"""
        collector.is_collecting = False

        result = collector.stop_collection()

        assert result is True
        # 驗證子收集器沒有被調用
        for sub_collector in collector.collectors.values():
            sub_collector.stop_collection.assert_not_called()

    def test_get_metrics_success(self, collector):
        """測試成功獲取指標"""
        # 模擬 generate_latest 函數
        with patch('src.monitoring.prometheus_collector.generate_latest') as mock_generate:
            mock_generate.return_value = b"# HELP test_metric Test metric\ntest_metric 1.0\n"

            # 設置子收集器有註冊表
            for sub_collector in collector.collectors.values():
                sub_collector.registry = MagicMock()

            result = collector.get_metrics()

            assert isinstance(result, str)
            assert "test_metric" in result

    def test_get_metrics_no_generate_latest(self, collector):
        """測試沒有 generate_latest 函數時獲取指標"""
        with patch('src.monitoring.prometheus_collector.generate_latest', None):
            result = collector.get_metrics()
            assert result == ""

    def test_get_content_type(self, collector):
        """測試獲取內容類型"""
        result = collector.get_content_type()
        assert "text/plain" in result  # 檢查包含基本類型

    def test_is_healthy_true(self, collector):
        """測試健康狀態檢查 - 健康"""
        collector.is_collecting = True

        # 設置所有子收集器健康
        for sub_collector in collector.collectors.values():
            sub_collector.is_healthy.return_value = True

        result = collector.is_healthy()
        assert result is True

    def test_is_healthy_false_not_collecting(self, collector):
        """測試健康狀態檢查 - 未收集"""
        collector.is_collecting = False

        result = collector.is_healthy()
        assert result is False

    def test_is_healthy_false_unhealthy_collectors(self, collector):
        """測試健康狀態檢查 - 子收集器不健康"""
        collector.is_collecting = True

        # 設置所有子收集器不健康
        for sub_collector in collector.collectors.values():
            sub_collector.is_healthy.return_value = False

        result = collector.is_healthy()
        assert result is False

    def test_get_collector_status(self, collector):
        """測試獲取收集器狀態"""
        collector.is_collecting = True
        collector.collection_interval = 15

        # 設置子收集器狀態
        for name, sub_collector in collector.collectors.items():
            sub_collector.is_healthy.return_value = True
            sub_collector.is_collecting = True
            sub_collector.metrics = {'test_metric': 'value'}

        result = collector.get_collector_status()

        assert result['is_collecting'] is True
        assert result['collection_interval'] == 15
        assert 'collectors' in result
        assert len(result['collectors']) == 4

    def test_get_collector(self, collector):
        """測試獲取指定子收集器"""
        result = collector.get_collector('system')
        assert result is not None

        result = collector.get_collector('nonexistent')
        assert result is None

    def test_get_metric_names(self, collector):
        """測試獲取指標名稱列表"""
        # 設置子收集器返回指標名稱
        collector.collectors['system'].get_metric_names.return_value = ['cpu_usage', 'memory_usage']
        collector.collectors['trading'].get_metric_names.return_value = ['order_count']

        # 其他收集器沒有 get_metric_names 方法
        del collector.collectors['api'].get_metric_names
        del collector.collectors['business'].get_metric_names

        result = collector.get_metric_names()

        assert 'cpu_usage' in result
        assert 'memory_usage' in result
        assert 'order_count' in result
