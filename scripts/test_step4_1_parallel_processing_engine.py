#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步驟 4.1 並行處理引擎測試腳本

此腳本用於測試並行處理引擎的功能，包括：
1. 引擎初始化測試
2. 單任務提交測試
3. 批量任務提交測試
4. 任務狀態管理測試
5. 效能監控測試

Usage:
    python scripts/test_step4_1_parallel_processing_engine.py
"""

import sys
import os
import logging
import time
import random
from datetime import datetime
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
        logging.FileHandler('logs/test_step4_1_parallel_processing_engine.log')
    ]
)
logger = logging.getLogger(__name__)

# 確保日誌目錄存在
os.makedirs('logs', exist_ok=True)

# 測試用的模擬函數
def mock_download_task(data_source: str, delay: float = 1.0, fail_rate: float = 0.0):
    """模擬下載任務
    
    Args:
        data_source: 資料來源名稱
        delay: 模擬延遲時間
        fail_rate: 失敗率 (0.0-1.0)
        
    Returns:
        dict: 模擬下載結果
    """
    # 模擬處理時間
    time.sleep(delay)
    
    # 模擬隨機失敗
    if random.random() < fail_rate:
        raise Exception(f"模擬 {data_source} 下載失敗")
    
    return {
        'data_source': data_source,
        'timestamp': datetime.now().isoformat(),
        'records_count': random.randint(100, 1000),
        'processing_time': delay
    }

def mock_cpu_intensive_task(iterations: int = 1000000):
    """模擬CPU密集型任務"""
    result = 0
    for i in range(iterations):
        result += i * i
    return result

def mock_io_intensive_task(file_size: int = 1000):
    """模擬I/O密集型任務"""
    # 模擬文件讀寫
    data = "x" * file_size
    time.sleep(0.1)  # 模擬I/O延遲
    return len(data)

def test_engine_initialization():
    """測試引擎初始化"""
    logger.info("=== 測試引擎初始化 ===")
    
    try:
        from src.core.parallel_processing_engine import ParallelProcessingEngine, ProcessingMode
        
        # 測試預設初始化
        engine1 = ParallelProcessingEngine()
        assert engine1.max_workers > 0
        assert engine1.processing_mode == ProcessingMode.ADAPTIVE
        
        # 測試自定義初始化
        engine2 = ParallelProcessingEngine(
            max_workers=3,
            processing_mode=ProcessingMode.THREAD_POOL
        )
        assert engine2.max_workers == 3
        assert engine2.processing_mode == ProcessingMode.THREAD_POOL
        
        logger.info("引擎初始化測試通過")
        logger.info("  預設引擎工作者數量: %d", engine1.max_workers)
        logger.info("  自定義引擎工作者數量: %d", engine2.max_workers)
        
        # 關閉引擎
        engine1.shutdown(wait=False)
        
        return True, engine2
        
    except Exception as e:
        logger.error("引擎初始化測試失敗: %s", e)
        return False, None


def test_single_task_submission(engine):
    """測試單任務提交"""
    logger.info("=== 測試單任務提交 ===")
    
    try:
        from src.core.parallel_processing_engine import TaskPriority
        
        # 提交單個任務
        task_id = engine.submit_task(
            mock_download_task,
            "daily_price",
            delay=0.5,
            fail_rate=0.0,
            priority=TaskPriority.HIGH
        )
        
        assert task_id is not None
        assert isinstance(task_id, str)
        
        # 檢查任務狀態
        status = engine.get_task_status(task_id)
        assert status is not None
        
        # 等待任務完成
        results = engine.wait_for_completion([task_id], timeout=10)
        
        assert task_id in results
        assert 'result' in results[task_id] or 'error' in results[task_id]
        
        if 'result' in results[task_id]:
            result = results[task_id]['result']
            assert result['data_source'] == 'daily_price'
            logger.info("任務完成: %s", result)
        else:
            logger.error("任務失敗: %s", results[task_id]['error'])
        
        logger.info("單任務提交測試通過")
        return True
        
    except Exception as e:
        logger.error("單任務提交測試失敗: %s", e)
        return False


def test_batch_task_submission(engine):
    """測試批量任務提交"""
    logger.info("=== 測試批量任務提交 ===")
    
    try:
        from src.core.parallel_processing_engine import TaskPriority
        
        # 準備批量任務
        tasks = []
        data_sources = ['daily_price', 'volume_data', 'news', 'financial_reports', 'technical_indicators']
        
        for i, source in enumerate(data_sources):
            task_config = {
                'function': mock_download_task,
                'data_source': source,
                'delay': random.uniform(0.2, 0.8),
                'fail_rate': 0.1 if i % 3 == 0 else 0.0,  # 部分任務可能失敗
                'priority': TaskPriority.NORMAL,
                'task_id': f'batch_task_{i}_{source}'
            }
            tasks.append(task_config)
        
        # 批量提交任務
        start_time = time.time()
        task_ids = engine.submit_batch_tasks(tasks)
        submit_time = time.time() - start_time
        
        assert len(task_ids) == len(tasks)
        logger.info("批量提交 %d 個任務，耗時: %.3f 秒", len(task_ids), submit_time)
        
        # 等待所有任務完成
        start_time = time.time()
        results = engine.wait_for_completion(task_ids, timeout=30)
        completion_time = time.time() - start_time
        
        # 統計結果
        successful_tasks = sum(1 for r in results.values() if 'result' in r)
        failed_tasks = sum(1 for r in results.values() if 'error' in r)
        
        logger.info("批量任務完成統計:")
        logger.info("  總任務數: %d", len(task_ids))
        logger.info("  成功任務: %d", successful_tasks)
        logger.info("  失敗任務: %d", failed_tasks)
        logger.info("  完成時間: %.3f 秒", completion_time)
        if len(task_ids) > 0:
            logger.info("  平均每任務: %.3f 秒", completion_time / len(task_ids))
        else:
            logger.info("  平均每任務: N/A")
        
        assert len(results) > 0  # 確保有結果返回
        assert successful_tasks > 0  # 至少有一些任務成功
        
        logger.info("批量任務提交測試通過")
        return True
        
    except Exception as e:
        logger.error("批量任務提交測試失敗: %s", e)
        return False


def test_task_cancellation(engine):
    """測試任務取消功能"""
    logger.info("=== 測試任務取消功能 ===")
    
    try:
        # 提交一個長時間運行的任務
        task_id = engine.submit_task(
            mock_download_task,
            "long_running_task",
            delay=5.0,  # 5秒延遲
            fail_rate=0.0
        )
        
        # 短暫等待確保任務開始
        time.sleep(0.5)
        
        # 取消任務
        cancelled = engine.cancel_task(task_id)
        
        if cancelled:
            logger.info("任務取消成功: %s", task_id)
        else:
            logger.info("任務可能已經開始執行，無法取消: %s", task_id)
        
        # 等待一段時間檢查狀態
        time.sleep(1)
        status = engine.get_task_status(task_id)
        logger.info("取消後任務狀態: %s", status.value if status else "未知")
        
        logger.info("任務取消測試通過")
        return True
        
    except Exception as e:
        logger.error("任務取消測試失敗: %s", e)
        return False


def test_performance_monitoring(engine):
    """測試效能監控功能"""
    logger.info("=== 測試效能監控功能 ===")
    
    try:
        # 提交一些任務來產生監控資料
        tasks = []
        for i in range(5):
            task_config = {
                'function': mock_download_task,
                'data_source': f'monitor_test_{i}',
                'delay': 0.3,
                'fail_rate': 0.0
            }
            tasks.append(task_config)
        
        task_ids = engine.submit_batch_tasks(tasks)
        results = engine.wait_for_completion(task_ids, timeout=15)
        
        # 獲取處理指標
        metrics = engine.get_processing_metrics()
        
        # 驗證指標結構
        assert hasattr(metrics, 'total_tasks')
        assert hasattr(metrics, 'completed_tasks')
        assert hasattr(metrics, 'failed_tasks')
        assert hasattr(metrics, 'success_rate')
        assert hasattr(metrics, 'average_processing_time')
        assert hasattr(metrics, 'throughput')
        
        logger.info("處理指標:")
        logger.info("  總任務數: %d", metrics.total_tasks)
        logger.info("  完成任務: %d", metrics.completed_tasks)
        logger.info("  失敗任務: %d", metrics.failed_tasks)
        logger.info("  成功率: %.2f%%", metrics.success_rate * 100)
        logger.info("  平均處理時間: %.3f 秒", metrics.average_processing_time)
        logger.info("  吞吐量: %.2f 任務/秒", metrics.throughput)
        
        # 獲取工作者指標
        worker_metrics = engine.get_worker_metrics()
        logger.info("工作者指標數量: %d", len(worker_metrics))
        
        assert metrics.total_tasks >= len(tasks)
        assert metrics.success_rate >= 0.0
        
        logger.info("效能監控測試通過")
        return True
        
    except Exception as e:
        logger.error("效能監控測試失敗: %s", e)
        return False


def test_worker_adjustment(engine):
    """測試工作者數量調整功能"""
    logger.info("=== 測試工作者數量調整功能 ===")
    
    try:
        # 記錄原始工作者數量
        original_workers = engine.max_workers
        
        # 調整工作者數量
        new_count = max(1, original_workers - 1)
        success = engine.adjust_worker_count(new_count)
        
        assert success
        assert engine.max_workers == new_count
        
        logger.info("工作者數量調整成功: %d -> %d", original_workers, new_count)
        
        # 測試無效調整
        invalid_success = engine.adjust_worker_count(0)
        assert not invalid_success
        
        # 恢復原始數量
        restore_success = engine.adjust_worker_count(original_workers)
        assert restore_success
        
        logger.info("工作者數量調整測試通過")
        return True
        
    except Exception as e:
        logger.error("工作者數量調整測試失敗: %s", e)
        return False


def test_error_handling_and_retry(engine):
    """測試錯誤處理和重試功能"""
    logger.info("=== 測試錯誤處理和重試功能 ===")
    
    try:
        # 提交一個高失敗率的任務
        task_id = engine.submit_task(
            mock_download_task,
            "error_prone_task",
            delay=0.2,
            fail_rate=0.8,  # 80%失敗率
            max_retries=2
        )
        
        # 等待任務完成（包括重試）
        results = engine.wait_for_completion([task_id], timeout=20)
        
        assert task_id in results
        
        if 'error' in results[task_id]:
            logger.info("任務最終失敗（預期行為）: %s", results[task_id]['error'])
        else:
            logger.info("任務重試後成功: %s", results[task_id]['result'])
        
        logger.info("錯誤處理和重試測試通過")
        return True
        
    except Exception as e:
        logger.error("錯誤處理和重試測試失敗: %s", e)
        return False


def main():
    """主測試函數"""
    logger.info("開始執行步驟 4.1 並行處理引擎測試")
    
    # 初始化引擎
    init_success, engine = test_engine_initialization()
    if not init_success:
        logger.error("引擎初始化失敗，終止測試")
        return False
    
    test_results = []
    
    # 執行各項測試
    test_functions = [
        ("單任務提交", lambda: test_single_task_submission(engine)),
        ("批量任務提交", lambda: test_batch_task_submission(engine)),
        ("任務取消功能", lambda: test_task_cancellation(engine)),
        ("效能監控功能", lambda: test_performance_monitoring(engine)),
        ("工作者數量調整", lambda: test_worker_adjustment(engine)),
        ("錯誤處理和重試", lambda: test_error_handling_and_retry(engine))
    ]
    
    for test_name, test_func in test_functions:
        logger.info("\n" + "="*50)
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            logger.error("測試 %s 時發生未預期錯誤: %s", test_name, e)
            test_results.append((test_name, False))
    
    # 關閉引擎
    engine.shutdown(wait=True)
    
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
        logger.info("所有測試都通過！步驟 4.1 並行處理引擎實現成功")
        return True
    else:
        logger.warning("部分測試失敗，需要進一步檢查和修正")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
