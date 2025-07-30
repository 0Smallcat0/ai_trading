#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步驟 4.3 效能監控系統測試腳本

此腳本用於測試效能監控系統的功能，包括：
1. 監控系統初始化測試
2. 效能指標記錄測試
3. 系統資源監控測試
4. 警報系統測試
5. 優化建議測試

Usage:
    python scripts/test_step4_3_performance_monitoring_system.py
"""

import sys
import os
import logging
import time
import random
from datetime import datetime, timedelta
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/test_step4_3_performance_monitoring_system.log')
    ]
)
logger = logging.getLogger(__name__)

# 確保日誌目錄存在
os.makedirs('logs', exist_ok=True)

def test_monitor_initialization():
    """測試監控系統初始化"""
    logger.info("=== 測試監控系統初始化 ===")
    
    try:
        from src.core.performance_monitoring_system import PerformanceMonitor, MetricType
        
        # 測試預設初始化
        monitor = PerformanceMonitor()
        
        # 檢查基本屬性
        assert hasattr(monitor, 'metrics')
        assert hasattr(monitor, 'alerts')
        assert hasattr(monitor, 'thresholds')
        assert hasattr(monitor, 'system_resources')
        
        # 檢查指標存儲初始化
        assert len(monitor.metrics) == len(MetricType)
        for metric_type in MetricType:
            assert metric_type in monitor.metrics
        
        logger.info("監控系統初始化測試通過")
        logger.info("  支援指標類型: %d 種", len(MetricType))
        logger.info("  預設閾值配置: %d 項", len(monitor.thresholds))
        
        return True, monitor
        
    except Exception as e:
        logger.error("監控系統初始化測試失敗: %s", e)
        return False, None


def test_download_performance_recording(monitor):
    """測試下載效能記錄"""
    logger.info("=== 測試下載效能記錄 ===")
    
    try:
        from src.core.performance_monitoring_system import MetricType
        
        # 模擬多次下載記錄
        test_data = [
            ('daily_price', 1.2, True, 1024),
            ('volume_data', 0.8, True, 2048),
            ('news_feed', 2.5, False, 0),
            ('financial_reports', 1.8, True, 4096),
            ('technical_indicators', 0.5, True, 512)
        ]
        
        for source, duration, success, size in test_data:
            monitor.record_download_performance(source, duration, success, size)
        
        # 檢查指標記錄
        download_speed_metrics = monitor.metrics[MetricType.DOWNLOAD_SPEED]
        response_time_metrics = monitor.metrics[MetricType.RESPONSE_TIME]
        success_rate_metrics = monitor.metrics[MetricType.SUCCESS_RATE]
        
        assert len(download_speed_metrics) > 0
        assert len(response_time_metrics) == len(test_data)
        assert len(success_rate_metrics) > 0
        
        # 檢查指標值的合理性
        for metric in download_speed_metrics:
            assert metric.value > 0  # 下載速度應該大於0
        
        for metric in response_time_metrics:
            assert metric.value >= 0  # 響應時間應該非負
        
        logger.info("下載效能記錄測試通過")
        logger.info("  記錄下載速度指標: %d 個", len(download_speed_metrics))
        logger.info("  記錄響應時間指標: %d 個", len(response_time_metrics))
        logger.info("  記錄成功率指標: %d 個", len(success_rate_metrics))
        
        return True
        
    except Exception as e:
        logger.error("下載效能記錄測試失敗: %s", e)
        return False


def test_system_metrics_recording(monitor):
    """測試系統指標記錄"""
    logger.info("=== 測試系統指標記錄 ===")
    
    try:
        from src.core.performance_monitoring_system import MetricType
        
        # 記錄系統指標
        initial_cpu_count = len(monitor.metrics[MetricType.CPU_USAGE])
        initial_memory_count = len(monitor.metrics[MetricType.MEMORY_USAGE])
        
        monitor.record_system_metrics()
        
        # 檢查指標是否增加
        final_cpu_count = len(monitor.metrics[MetricType.CPU_USAGE])
        final_memory_count = len(monitor.metrics[MetricType.MEMORY_USAGE])
        
        assert final_cpu_count > initial_cpu_count
        assert final_memory_count > initial_memory_count
        
        # 檢查系統資源記錄
        assert len(monitor.system_resources) > 0
        
        latest_resource = monitor.system_resources[-1]
        assert 0 <= latest_resource.cpu_percent <= 100
        assert 0 <= latest_resource.memory_percent <= 100
        assert latest_resource.disk_io_read >= 0
        assert latest_resource.network_io_sent >= 0
        
        logger.info("系統指標記錄測試通過")
        logger.info("  CPU使用率: %.1f%%", latest_resource.cpu_percent)
        logger.info("  記憶體使用率: %.1f%%", latest_resource.memory_percent)
        logger.info("  系統資源記錄: %d 筆", len(monitor.system_resources))
        
        return True
        
    except Exception as e:
        logger.error("系統指標記錄測試失敗: %s", e)
        return False


def test_cache_performance_recording(monitor):
    """測試快取效能記錄"""
    logger.info("=== 測試快取效能記錄 ===")
    
    try:
        from src.core.performance_monitoring_system import MetricType
        
        # 記錄快取效能
        test_cache_data = [
            (0.85, 1000),  # 85% 命中率，1000 請求
            (0.72, 1500),  # 72% 命中率，1500 請求
            (0.91, 800),   # 91% 命中率，800 請求
        ]
        
        for hit_rate, requests in test_cache_data:
            monitor.record_cache_performance(hit_rate, requests)
        
        # 檢查快取指標
        cache_hit_metrics = monitor.metrics[MetricType.CACHE_HIT_RATE]
        throughput_metrics = monitor.metrics[MetricType.THROUGHPUT]
        
        assert len(cache_hit_metrics) == len(test_cache_data)
        assert len(throughput_metrics) == len(test_cache_data)
        
        # 檢查指標值
        for metric in cache_hit_metrics:
            assert 0 <= metric.value <= 1  # 命中率應該在0-1之間
        
        for metric in throughput_metrics:
            assert metric.value > 0  # 吞吐量應該大於0
        
        logger.info("快取效能記錄測試通過")
        logger.info("  快取命中率指標: %d 個", len(cache_hit_metrics))
        logger.info("  吞吐量指標: %d 個", len(throughput_metrics))
        
        return True
        
    except Exception as e:
        logger.error("快取效能記錄測試失敗: %s", e)
        return False


def test_alert_system(monitor):
    """測試警報系統"""
    logger.info("=== 測試警報系統 ===")
    
    try:
        from src.core.performance_monitoring_system import MetricType, AlertLevel
        
        # 設定較低的閾值來觸發警報
        monitor.add_custom_threshold(MetricType.CPU_USAGE, 10.0, 20.0)
        monitor.add_custom_threshold(MetricType.ERROR_RATE, 0.01, 0.05)
        
        # 記錄一些會觸發警報的指標
        monitor.record_download_performance('test_source', 1.0, False, 1024)  # 失敗，會提高錯誤率
        monitor.record_download_performance('test_source', 1.0, False, 1024)  # 再次失敗
        
        # 等待警報檢查
        time.sleep(0.1)
        
        # 檢查是否產生警報
        active_alerts = monitor.get_active_alerts()
        
        # 應該至少有一個警報（錯誤率過高）
        assert len(active_alerts) > 0
        
        # 檢查警報內容
        error_rate_alerts = [
            alert for alert in active_alerts 
            if alert.metric_type == MetricType.ERROR_RATE
        ]
        
        if error_rate_alerts:
            alert = error_rate_alerts[0]
            assert alert.level in [AlertLevel.WARNING, AlertLevel.CRITICAL]
            assert not alert.resolved
            
            # 測試解決警報
            monitor.resolve_alert(alert)
            assert alert.resolved
        
        logger.info("警報系統測試通過")
        logger.info("  產生警報: %d 個", len(active_alerts))
        logger.info("  錯誤率警報: %d 個", len(error_rate_alerts))
        
        return True
        
    except Exception as e:
        logger.error("警報系統測試失敗: %s", e)
        return False


def test_metric_statistics(monitor):
    """測試指標統計功能"""
    logger.info("=== 測試指標統計功能 ===")
    
    try:
        from src.core.performance_monitoring_system import MetricType
        
        # 獲取當前指標
        current_metrics = monitor.get_current_metrics()
        
        # 檢查指標結構
        assert isinstance(current_metrics, dict)
        assert len(current_metrics) == len(MetricType)
        
        for metric_type in MetricType:
            assert metric_type in current_metrics
            assert isinstance(current_metrics[metric_type], (int, float))
        
        # 獲取指標統計
        stats = monitor.get_metric_statistics(MetricType.RESPONSE_TIME)
        
        if stats:  # 如果有資料
            required_keys = ['count', 'mean', 'median', 'min', 'max', 'stdev']
            for key in required_keys:
                assert key in stats
                assert isinstance(stats[key], (int, float))
        
        logger.info("指標統計功能測試通過")
        logger.info("  當前指標數量: %d", len(current_metrics))
        if stats:
            logger.info("  響應時間統計: 平均 %.3f 秒", stats.get('mean', 0))
        
        return True
        
    except Exception as e:
        logger.error("指標統計功能測試失敗: %s", e)
        return False


def test_optimization_suggestions(monitor):
    """測試優化建議功能"""
    logger.info("=== 測試優化建議功能 ===")
    
    try:
        # 執行效能優化
        suggestions = monitor.optimize_performance()
        
        # 檢查建議結構
        assert isinstance(suggestions, list)
        
        for suggestion in suggestions:
            assert hasattr(suggestion, 'action')
            assert hasattr(suggestion, 'reason')
            assert hasattr(suggestion, 'expected_improvement')
            assert hasattr(suggestion, 'priority')
            assert 1 <= suggestion.priority <= 10
        
        logger.info("優化建議功能測試通過")
        logger.info("  執行的優化建議: %d 個", len(suggestions))
        
        for i, suggestion in enumerate(suggestions):
            logger.info("  建議 %d: %s (優先級: %d)", 
                       i+1, suggestion.reason, suggestion.priority)
        
        return True
        
    except Exception as e:
        logger.error("優化建議功能測試失敗: %s", e)
        return False


def test_performance_report(monitor):
    """測試效能報告生成"""
    logger.info("=== 測試效能報告生成 ===")
    
    try:
        # 生成效能報告
        report = monitor.generate_performance_report(timedelta(hours=1))
        
        # 檢查報告結構
        assert hasattr(report, 'start_time')
        assert hasattr(report, 'end_time')
        assert hasattr(report, 'summary')
        assert hasattr(report, 'metrics')
        assert hasattr(report, 'alerts')
        assert hasattr(report, 'suggestions')
        assert hasattr(report, 'system_health')
        
        # 檢查時間範圍
        assert report.start_time < report.end_time
        assert (report.end_time - report.start_time) <= timedelta(hours=1, minutes=1)
        
        # 檢查系統健康度
        valid_health_levels = ['excellent', 'good', 'fair', 'poor', 'critical']
        assert report.system_health in valid_health_levels
        
        logger.info("效能報告生成測試通過")
        logger.info("  報告時間範圍: %s 到 %s", 
                   report.start_time.strftime('%H:%M:%S'),
                   report.end_time.strftime('%H:%M:%S'))
        logger.info("  系統健康度: %s", report.system_health)
        logger.info("  包含警報: %d 個", len(report.alerts))
        logger.info("  包含建議: %d 個", len(report.suggestions))
        
        return True
        
    except Exception as e:
        logger.error("效能報告生成測試失敗: %s", e)
        return False


def main():
    """主測試函數"""
    logger.info("開始執行步驟 4.3 效能監控系統測試")
    
    # 初始化監控系統
    init_success, monitor = test_monitor_initialization()
    if not init_success:
        logger.error("監控系統初始化失敗，終止測試")
        return False
    
    test_results = []
    
    # 執行各項測試
    test_functions = [
        ("下載效能記錄", lambda: test_download_performance_recording(monitor)),
        ("系統指標記錄", lambda: test_system_metrics_recording(monitor)),
        ("快取效能記錄", lambda: test_cache_performance_recording(monitor)),
        ("警報系統", lambda: test_alert_system(monitor)),
        ("指標統計功能", lambda: test_metric_statistics(monitor)),
        ("優化建議功能", lambda: test_optimization_suggestions(monitor)),
        ("效能報告生成", lambda: test_performance_report(monitor))
    ]
    
    for test_name, test_func in test_functions:
        logger.info("\n" + "="*50)
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            logger.error("測試 %s 時發生未預期錯誤: %s", test_name, e)
            test_results.append((test_name, False))
    
    # 關閉監控系統
    monitor.shutdown()
    
    # 輸出測試結果摘要
    logger.info("\n" + "="*50)
    logger.info("測試結果摘要:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "通過" if result else "失敗"
        logger.info("  %s: %s", test_name, status)
        if result:
            passed += 1
    
    logger.info("\n總計: %d/%d 測試通過 (%.1f%%)", passed, total, (passed/total)*100)
    
    if passed == total:
        logger.info("所有測試都通過！步驟 4.3 效能監控系統實現成功")
        return True
    else:
        logger.warning("部分測試失敗，需要進一步檢查和修正")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
