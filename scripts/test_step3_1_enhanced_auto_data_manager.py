#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步驟 3.1 增強版自動資料管理器測試腳本

此腳本用於測試增強版自動資料管理器的功能，包括：
1. 智能排程系統測試
2. 資料品質檢查測試
3. 異常檢測和自動修復測試
4. 系統健康度監控測試
5. 學習洞察功能測試

Usage:
    python scripts/test_step3_1_enhanced_auto_data_manager.py
"""

import sys
import os
import logging
import time
from datetime import datetime, date, timedelta
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
        logging.FileHandler('logs/test_step3_1_enhanced_auto_data_manager.log')
    ]
)
logger = logging.getLogger(__name__)

# 確保日誌目錄存在
os.makedirs('logs', exist_ok=True)

def test_manager_initialization():
    """測試管理器初始化"""
    logger.info("=== 測試管理器初始化 ===")
    
    try:
        from src.core.enhanced_auto_data_manager import EnhancedAutoDataManager
        
        # 測試基本初始化
        manager = EnhancedAutoDataManager()
        
        # 檢查基本屬性
        assert hasattr(manager, 'config')
        assert hasattr(manager, 'quality_history')
        assert hasattr(manager, 'anomaly_history')
        assert hasattr(manager, 'schedule_queue')
        assert hasattr(manager, 'health_metrics')
        
        logger.info("✅ 管理器初始化成功")
        return True, manager
        
    except Exception as e:
        logger.error("❌ 管理器初始化失敗: %s", e)
        return False, None


def test_intelligent_scheduling(manager):
    """測試智能排程功能"""
    logger.info("=== 測試智能排程功能 ===")
    
    try:
        # 測試基本排程創建
        data_types = ['daily_price', 'volume', 'news', 'financial_reports']
        schedule = manager.create_intelligent_schedule(data_types)
        
        # 驗證排程結果
        assert len(schedule) == len(data_types)
        assert all(task.data_type in data_types for task in schedule)
        assert all(hasattr(task, 'task_id') for task in schedule)
        assert all(hasattr(task, 'scheduled_time') for task in schedule)
        assert all(hasattr(task, 'priority') for task in schedule)
        
        logger.info("✅ 智能排程創建成功: %d 個任務", len(schedule))
        
        # 測試時間窗口排程
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=6)
        windowed_schedule = manager.create_intelligent_schedule(
            data_types[:2], 
            (start_time, end_time)
        )
        
        assert len(windowed_schedule) == 2
        assert all(start_time <= task.scheduled_time <= end_time for task in windowed_schedule)
        
        logger.info("✅ 時間窗口排程測試通過")
        return True
        
    except Exception as e:
        logger.error("❌ 智能排程測試失敗: %s", e)
        return False


def test_quality_check(manager):
    """測試資料品質檢查功能"""
    logger.info("=== 測試資料品質檢查功能 ===")
    
    try:
        # 測試品質檢查
        data_types = ['daily_price', 'volume']
        quality_results = manager.comprehensive_quality_check(data_types)
        
        # 驗證結果
        assert len(quality_results) == len(data_types)
        
        for data_type, metrics in quality_results.items():
            assert data_type in data_types
            assert hasattr(metrics, 'completeness')
            assert hasattr(metrics, 'accuracy')
            assert hasattr(metrics, 'consistency')
            assert hasattr(metrics, 'overall_score')
            assert hasattr(metrics, 'quality_level')
            assert 0 <= metrics.overall_score <= 1
            
            logger.info("%s 品質分數: %.3f (%s)", 
                       data_type, metrics.overall_score, metrics.quality_level.value)
        
        logger.info("✅ 資料品質檢查測試通過")
        
        # 測試指定期間的品質檢查
        check_period = (date.today() - timedelta(days=7), date.today())
        period_results = manager.comprehensive_quality_check(['daily_price'], check_period)
        
        assert 'daily_price' in period_results
        logger.info("✅ 指定期間品質檢查測試通過")
        
        return True
        
    except Exception as e:
        logger.error("❌ 資料品質檢查測試失敗: %s", e)
        return False


def test_anomaly_detection(manager):
    """測試異常檢測功能"""
    logger.info("=== 測試異常檢測功能 ===")
    
    try:
        # 測試異常檢測
        data_types = ['daily_price', 'volume']
        anomalies = manager.detect_and_fix_anomalies(data_types, auto_fix=True)
        
        # 驗證結果（可能沒有異常，這是正常的）
        assert isinstance(anomalies, list)
        
        for anomaly in anomalies:
            assert hasattr(anomaly, 'anomaly_type')
            assert hasattr(anomaly, 'severity')
            assert hasattr(anomaly, 'description')
            assert hasattr(anomaly, 'detection_time')
            assert hasattr(anomaly, 'auto_fixable')
            
            logger.info("檢測到異常: %s (嚴重程度: %s)", 
                       anomaly.description, anomaly.severity)
        
        logger.info("✅ 異常檢測測試通過，檢測到 %d 個異常", len(anomalies))
        
        # 測試不自動修復的異常檢測
        no_fix_anomalies = manager.detect_and_fix_anomalies(['news'], auto_fix=False)
        assert isinstance(no_fix_anomalies, list)
        
        logger.info("✅ 非自動修復異常檢測測試通過")
        return True
        
    except Exception as e:
        logger.error("❌ 異常檢測測試失敗: %s", e)
        return False


def test_health_monitoring(manager):
    """測試系統健康度監控功能"""
    logger.info("=== 測試系統健康度監控功能 ===")
    
    try:
        # 等待一段時間讓背景監控收集資料
        logger.info("等待背景監控收集資料...")
        time.sleep(3)
        
        # 獲取健康度報告
        health_report = manager.get_system_health_report()
        
        # 驗證報告結構
        if health_report.get('status') == 'no_data':
            logger.info("⚠️ 尚無健康度資料，這是正常的")
            return True
        
        assert 'timestamp' in health_report
        assert 'current_status' in health_report
        assert 'recommendations' in health_report
        assert 'overall_health' in health_report
        
        current_status = health_report['current_status']
        assert 'cpu_usage' in current_status
        assert 'memory_usage' in current_status
        assert 'error_rate' in current_status
        
        logger.info("當前系統狀態:")
        logger.info("  CPU使用率: %.1f%%", current_status['cpu_usage'])
        logger.info("  記憶體使用率: %.1f%%", current_status['memory_usage'])
        logger.info("  錯誤率: %.1f%%", current_status['error_rate'] * 100)
        logger.info("  整體健康度: %s", health_report['overall_health'])
        
        logger.info("系統建議:")
        for recommendation in health_report['recommendations']:
            logger.info("  - %s", recommendation)
        
        logger.info("✅ 系統健康度監控測試通過")
        return True
        
    except Exception as e:
        logger.error("❌ 系統健康度監控測試失敗: %s", e)
        return False


def test_download_strategy_optimization(manager):
    """測試下載策略優化功能"""
    logger.info("=== 測試下載策略優化功能 ===")
    
    try:
        # 測試策略優化
        data_type = 'daily_price'
        strategy = manager.optimize_download_strategy(data_type)
        
        # 驗證策略結構
        assert 'data_type' in strategy
        assert 'optimal_download_times' in strategy
        assert 'retry_strategy' in strategy
        assert 'optimal_concurrency' in strategy
        assert 'request_interval' in strategy
        assert 'confidence_score' in strategy
        
        assert strategy['data_type'] == data_type
        assert isinstance(strategy['optimal_download_times'], list)
        assert isinstance(strategy['retry_strategy'], dict)
        assert isinstance(strategy['optimal_concurrency'], int)
        assert isinstance(strategy['request_interval'], int)
        assert 0 <= strategy['confidence_score'] <= 1
        
        logger.info("優化策略:")
        logger.info("  最佳下載時間: %s", strategy['optimal_download_times'])
        logger.info("  最佳並行度: %d", strategy['optimal_concurrency'])
        logger.info("  請求間隔: %d 秒", strategy['request_interval'])
        logger.info("  信心度: %.3f", strategy['confidence_score'])
        
        logger.info("✅ 下載策略優化測試通過")
        return True
        
    except Exception as e:
        logger.error("❌ 下載策略優化測試失敗: %s", e)
        return False


def test_learning_insights(manager):
    """測試學習洞察功能"""
    logger.info("=== 測試學習洞察功能 ===")
    
    try:
        # 先執行一些操作來產生學習資料
        manager.comprehensive_quality_check(['daily_price'])
        manager.detect_and_fix_anomalies(['volume'])
        
        # 獲取學習洞察
        insights = manager.get_learning_insights()
        
        # 驗證洞察結構
        assert 'timestamp' in insights
        assert 'total_anomalies_detected' in insights
        assert 'quality_trends' in insights
        assert 'optimization_suggestions' in insights
        
        logger.info("學習洞察:")
        logger.info("  檢測異常總數: %d", insights['total_anomalies_detected'])
        logger.info("  品質趨勢: %s", insights['quality_trends'])
        logger.info("  優化建議數量: %d", len(insights['optimization_suggestions']))
        
        for suggestion in insights['optimization_suggestions']:
            logger.info("  - %s", suggestion)
        
        logger.info("✅ 學習洞察測試通過")
        return True
        
    except Exception as e:
        logger.error("❌ 學習洞察測試失敗: %s", e)
        return False


def test_configuration_management(manager):
    """測試配置管理功能"""
    logger.info("=== 測試配置管理功能 ===")
    
    try:
        # 測試配置匯出
        config = manager.export_configuration()
        
        # 驗證配置結構
        assert 'version' in config
        assert 'timestamp' in config
        assert 'config' in config
        assert 'learning_data' in config
        
        logger.info("配置匯出成功，版本: %s", config['version'])
        
        # 測試配置匯入
        success = manager.import_configuration(config)
        assert success
        
        logger.info("✅ 配置管理測試通過")
        return True
        
    except Exception as e:
        logger.error("❌ 配置管理測試失敗: %s", e)
        return False


def main():
    """主測試函數"""
    logger.info("開始執行步驟 3.1 增強版自動資料管理器測試")
    
    # 初始化管理器
    init_success, manager = test_manager_initialization()
    if not init_success:
        logger.error("管理器初始化失敗，終止測試")
        return False
    
    test_results = []
    
    # 執行各項測試
    test_functions = [
        ("智能排程功能", lambda: test_intelligent_scheduling(manager)),
        ("資料品質檢查", lambda: test_quality_check(manager)),
        ("異常檢測功能", lambda: test_anomaly_detection(manager)),
        ("系統健康度監控", lambda: test_health_monitoring(manager)),
        ("下載策略優化", lambda: test_download_strategy_optimization(manager)),
        ("學習洞察功能", lambda: test_learning_insights(manager)),
        ("配置管理功能", lambda: test_configuration_management(manager))
    ]
    
    for test_name, test_func in test_functions:
        logger.info("\n" + "="*50)
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            logger.error("測試 %s 時發生未預期錯誤: %s", test_name, e)
            test_results.append((test_name, False))
    
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
        logger.info("🎉 所有測試都通過！步驟 3.1 增強版自動資料管理器實現成功")
        return True
    else:
        logger.warning("⚠️ 部分測試失敗，需要進一步檢查和修正")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
