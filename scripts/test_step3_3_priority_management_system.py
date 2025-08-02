#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步驟 3.3 優先級管理系統測試腳本

此腳本用於測試優先級管理系統的功能，包括：
1. 資料來源註冊測試
2. 優先級分數計算測試
3. 下載順序優化測試
4. 動態優先級調整測試
5. 資源分配管理測試

Usage:
    python scripts/test_step3_3_priority_management_system.py
"""

import sys
import os
import logging
import time
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
        logging.FileHandler('logs/test_step3_3_priority_management_system.log')
    ]
)
logger = logging.getLogger(__name__)

# 確保日誌目錄存在
os.makedirs('logs', exist_ok=True)

def test_manager_initialization():
    """測試管理器初始化"""
    logger.info("=== 測試管理器初始化 ===")
    
    try:
        from src.core.priority_management_system import PriorityManager
        
        # 測試基本初始化
        manager = PriorityManager()
        
        # 檢查基本屬性
        assert hasattr(manager, 'data_sources')
        assert hasattr(manager, 'priority_history')
        assert hasattr(manager, 'resource_monitor')
        assert hasattr(manager, 'performance_metrics')
        assert hasattr(manager, 'adjustment_history')
        
        logger.info("管理器初始化成功")
        return True, manager
        
    except Exception as e:
        logger.error("管理器初始化失敗: %s", e)
        return False, None


def test_data_source_registration(manager):
    """測試資料來源註冊功能"""
    logger.info("=== 測試資料來源註冊功能 ===")
    
    try:
        from src.core.priority_management_system import PriorityLevel, ResourceType
        
        # 測試基本註冊
        success1 = manager.register_data_source(
            'daily_price',
            base_priority=PriorityLevel.HIGH,
            importance=9,
            urgency=8
        )
        assert success1
        
        # 測試帶資源需求的註冊
        success2 = manager.register_data_source(
            'volume_data',
            base_priority=PriorityLevel.NORMAL,
            importance=7,
            urgency=6,
            resource_requirements={
                ResourceType.CPU: 0.2,
                ResourceType.MEMORY: 0.1,
                ResourceType.NETWORK: 0.3
            }
        )
        assert success2
        
        # 測試帶依賴關係的註冊
        success3 = manager.register_data_source(
            'technical_indicators',
            base_priority=PriorityLevel.LOW,
            importance=5,
            urgency=4,
            dependencies=['daily_price', 'volume_data']
        )
        assert success3
        
        # 驗證註冊結果
        assert 'daily_price' in manager.data_sources
        assert 'volume_data' in manager.data_sources
        assert 'technical_indicators' in manager.data_sources
        
        # 檢查配置
        daily_config = manager.data_sources['daily_price']
        assert daily_config.importance == 9
        assert daily_config.urgency == 8
        assert daily_config.base_priority == PriorityLevel.HIGH
        
        tech_config = manager.data_sources['technical_indicators']
        assert 'daily_price' in tech_config.dependencies
        assert 'volume_data' in tech_config.dependencies
        
        logger.info("資料來源註冊測試通過，共註冊 %d 個來源", len(manager.data_sources))
        return True
        
    except Exception as e:
        logger.error("資料來源註冊測試失敗: %s", e)
        return False


def test_priority_score_calculation(manager):
    """測試優先級分數計算功能"""
    logger.info("=== 測試優先級分數計算功能 ===")
    
    try:
        # 計算各資料來源的優先級分數
        sources = ['daily_price', 'volume_data', 'technical_indicators']
        scores = {}
        
        for source in sources:
            score = manager.calculate_priority_score(source)
            assert score is not None
            assert 0 <= score.total_score <= 1
            assert 0 <= score.importance_score <= 1
            assert 0 <= score.urgency_score <= 1
            assert 0 <= score.performance_score <= 1
            assert 0 <= score.resource_score <= 1
            assert 0 <= score.time_score <= 1
            
            scores[source] = score
            logger.info("%s 優先級分數: %.3f (重要性: %.3f, 緊急性: %.3f, 效能: %.3f)", 
                       source, score.total_score, score.importance_score, 
                       score.urgency_score, score.performance_score)
        
        # 驗證高重要性的資料來源分數較高
        assert scores['daily_price'].total_score > scores['technical_indicators'].total_score
        
        logger.info("優先級分數計算測試通過")
        return True
        
    except Exception as e:
        logger.error("優先級分數計算測試失敗: %s", e)
        return False


def test_download_order_optimization(manager):
    """測試下載順序優化功能"""
    logger.info("=== 測試下載順序優化功能 ===")
    
    try:
        # 獲取優化後的下載順序
        download_order = manager.get_optimized_download_order()
        
        # 驗證結果
        assert len(download_order) == len(manager.data_sources)
        
        # 檢查任務結構
        for task in download_order:
            assert hasattr(task, 'task_id')
            assert hasattr(task, 'data_source')
            assert hasattr(task, 'priority_score')
            assert hasattr(task, 'estimated_duration')
            assert hasattr(task, 'resource_requirements')
            assert hasattr(task, 'dependencies')
            assert task.data_source in manager.data_sources
        
        # 驗證依賴關係（technical_indicators 應該在其依賴之後）
        source_positions = {task.data_source: i for i, task in enumerate(download_order)}
        tech_pos = source_positions['technical_indicators']
        daily_pos = source_positions['daily_price']
        volume_pos = source_positions['volume_data']
        
        # technical_indicators 應該在其依賴項之後
        assert tech_pos > daily_pos or tech_pos > volume_pos
        
        logger.info("下載順序優化測試通過:")
        for i, task in enumerate(download_order):
            logger.info("  %d. %s (分數: %.3f, 預估時間: %ds)", 
                       i+1, task.data_source, task.priority_score, task.estimated_duration)
        
        return True
        
    except Exception as e:
        logger.error("下載順序優化測試失敗: %s", e)
        return False


def test_priority_adjustment(manager):
    """測試動態優先級調整功能"""
    logger.info("=== 測試動態優先級調整功能 ===")
    
    try:
        from src.core.priority_management_system import PriorityLevel, AdjustmentReason
        
        # 記錄調整前的優先級
        original_priority = manager.data_sources['volume_data'].base_priority
        
        # 測試手動調整
        success = manager.adjust_priority(
            'volume_data',
            PriorityLevel.CRITICAL,
            AdjustmentReason.USER_REQUEST,
            "測試手動調整"
        )
        assert success
        
        # 驗證調整結果
        new_priority = manager.data_sources['volume_data'].base_priority
        assert new_priority == PriorityLevel.CRITICAL
        
        # 檢查調整歷史
        assert len(manager.adjustment_history) > 0
        latest_adjustment = manager.adjustment_history[-1]
        assert latest_adjustment.data_source == 'volume_data'
        assert latest_adjustment.old_priority == original_priority
        assert latest_adjustment.new_priority == PriorityLevel.CRITICAL
        assert latest_adjustment.reason == AdjustmentReason.USER_REQUEST
        
        logger.info("優先級調整測試通過: %s -> %s", 
                   original_priority.name, new_priority.name)
        
        # 測試無效調整
        invalid_success = manager.adjust_priority(
            'non_existent_source',
            PriorityLevel.HIGH,
            AdjustmentReason.USER_REQUEST
        )
        assert not invalid_success
        
        return True
        
    except Exception as e:
        logger.error("動態優先級調整測試失敗: %s", e)
        return False


def test_performance_metrics_update(manager):
    """測試效能指標更新功能"""
    logger.info("=== 測試效能指標更新功能 ===")
    
    try:
        # 模擬效能資料更新
        test_data = [
            ('daily_price', True, 120.5, None),
            ('daily_price', True, 98.2, None),
            ('daily_price', False, 300.0, "網路超時"),
            ('volume_data', True, 85.3, None),
            ('volume_data', True, 92.1, None),
        ]
        
        for source, success, duration, error in test_data:
            manager.update_performance_metrics(source, success, duration, error)
        
        # 驗證指標記錄
        assert 'daily_price' in manager.performance_metrics
        assert 'volume_data' in manager.performance_metrics
        
        daily_metrics = list(manager.performance_metrics['daily_price'])
        assert len(daily_metrics) == 3
        
        # 檢查指標內容
        for metric in daily_metrics:
            assert 'timestamp' in metric
            assert 'success' in metric
            assert 'duration' in metric
            assert 'error_message' in metric
        
        logger.info("效能指標更新測試通過")
        logger.info("  daily_price: %d 筆記錄", len(daily_metrics))
        logger.info("  volume_data: %d 筆記錄", len(list(manager.performance_metrics['volume_data'])))
        
        return True
        
    except Exception as e:
        logger.error("效能指標更新測試失敗: %s", e)
        return False


def test_resource_allocation(manager):
    """測試資源分配管理功能"""
    logger.info("=== 測試資源分配管理功能 ===")
    
    try:
        # 獲取資源分配情況
        allocation = manager.get_resource_allocation()
        
        # 驗證分配結果
        assert isinstance(allocation, dict)
        assert len(allocation) > 0
        
        for source, resources in allocation.items():
            assert source in manager.data_sources
            assert isinstance(resources, dict)
            
            for resource_type, amount in resources.items():
                assert isinstance(amount, (int, float))
                assert amount >= 0
        
        logger.info("資源分配測試通過:")
        for source, resources in allocation.items():
            logger.info("  %s: %s", source, resources)
        
        return True
        
    except Exception as e:
        logger.error("資源分配管理測試失敗: %s", e)
        return False


def test_priority_statistics(manager):
    """測試優先級統計功能"""
    logger.info("=== 測試優先級統計功能 ===")
    
    try:
        # 獲取統計資訊
        stats = manager.get_priority_statistics()
        
        # 驗證統計結構
        required_keys = [
            'total_sources', 'enabled_sources', 'priority_distribution',
            'recent_adjustments', 'average_scores', 'resource_utilization'
        ]
        
        for key in required_keys:
            assert key in stats
        
        # 驗證統計內容
        assert stats['total_sources'] == len(manager.data_sources)
        assert stats['enabled_sources'] <= stats['total_sources']
        assert isinstance(stats['priority_distribution'], dict)
        assert isinstance(stats['average_scores'], dict)
        assert isinstance(stats['resource_utilization'], dict)
        
        logger.info("優先級統計測試通過:")
        logger.info("  總資料來源: %d", stats['total_sources'])
        logger.info("  啟用來源: %d", stats['enabled_sources'])
        logger.info("  最近24小時調整: %d", stats['recent_adjustments'])
        logger.info("  優先級分佈: %s", dict(stats['priority_distribution']))
        
        return True
        
    except Exception as e:
        logger.error("優先級統計測試失敗: %s", e)
        return False


def main():
    """主測試函數"""
    logger.info("開始執行步驟 3.3 優先級管理系統測試")
    
    # 初始化管理器
    init_success, manager = test_manager_initialization()
    if not init_success:
        logger.error("管理器初始化失敗，終止測試")
        return False
    
    test_results = []
    
    # 執行各項測試
    test_functions = [
        ("資料來源註冊功能", lambda: test_data_source_registration(manager)),
        ("優先級分數計算", lambda: test_priority_score_calculation(manager)),
        ("下載順序優化", lambda: test_download_order_optimization(manager)),
        ("動態優先級調整", lambda: test_priority_adjustment(manager)),
        ("效能指標更新", lambda: test_performance_metrics_update(manager)),
        ("資源分配管理", lambda: test_resource_allocation(manager)),
        ("優先級統計", lambda: test_priority_statistics(manager))
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
        logger.info("所有測試都通過！步驟 3.3 優先級管理系統實現成功")
        return True
    else:
        logger.warning("部分測試失敗，需要進一步檢查和修正")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
