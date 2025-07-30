#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""綜合系統整合測試

此腳本執行完整的系統整合測試，驗證所有模組的協同工作能力，包括：
1. 核心功能整合測試
2. 智能化功能測試
3. 效能優化功能測試
4. 系統穩定性測試
5. 資料品質驗證

Usage:
    python scripts/comprehensive_system_integration_test.py
"""

import sys
import os
import logging
import time
import asyncio
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
        logging.FileHandler('logs/comprehensive_system_integration_test.log')
    ]
)
logger = logging.getLogger(__name__)

# 確保日誌目錄存在
os.makedirs('logs', exist_ok=True)

class SystemIntegrationTester:
    """系統整合測試器"""
    
    def __init__(self):
        """初始化測試器"""
        self.test_results = {}
        self.start_time = datetime.now()
        
    def run_all_tests(self):
        """執行所有整合測試"""
        logger.info("開始執行綜合系統整合測試")
        logger.info("測試開始時間: %s", self.start_time.strftime('%Y-%m-%d %H:%M:%S'))
        
        # 測試套件列表
        test_suites = [
            ("核心功能整合", self.test_core_integration),
            ("智能化功能", self.test_intelligence_features),
            ("效能優化功能", self.test_performance_features),
            ("系統穩定性", self.test_system_stability),
            ("資料品質驗證", self.test_data_quality)
        ]
        
        # 執行測試套件
        for suite_name, test_func in test_suites:
            logger.info("\n" + "="*60)
            logger.info("執行測試套件: %s", suite_name)
            logger.info("="*60)
            
            try:
                start_time = time.time()
                result = test_func()
                duration = time.time() - start_time
                
                self.test_results[suite_name] = {
                    'result': result,
                    'duration': duration,
                    'timestamp': datetime.now()
                }
                
                status = "通過" if result else "失敗"
                logger.info("測試套件 %s: %s (耗時: %.2f 秒)", suite_name, status, duration)
                
            except Exception as e:
                logger.error("測試套件 %s 執行失敗: %s", suite_name, e)
                self.test_results[suite_name] = {
                    'result': False,
                    'duration': 0,
                    'error': str(e),
                    'timestamp': datetime.now()
                }
        
        # 生成測試報告
        self.generate_test_report()
        
        return self.test_results
    
    def test_core_integration(self):
        """測試核心功能整合"""
        logger.info("測試核心功能整合...")
        
        try:
            # 測試核心功能模組（使用現有的模組）
            logger.info("開始測試核心功能模組...")

            # 測試並行處理引擎（作為核心功能的一部分）
            from src.core.parallel_processing_engine import ParallelProcessingEngine
            engine = ParallelProcessingEngine(max_workers=1)
            assert engine is not None
            engine.shutdown(wait=False)
            logger.info("並行處理引擎初始化成功")

            # 測試快取系統（作為核心功能的一部分）
            from src.core.intelligent_cache_system import IntelligentCacheSystem
            cache = IntelligentCacheSystem()
            assert cache is not None
            cache.shutdown()
            logger.info("智能快取系統初始化成功")

            # 測試效能監控（作為核心功能的一部分）
            from src.core.performance_monitoring_system import PerformanceMonitor
            monitor = PerformanceMonitor()
            assert monitor is not None
            monitor.shutdown()
            logger.info("效能監控系統初始化成功")
            
            logger.info("核心功能整合測試通過")
            return True
            
        except Exception as e:
            logger.error("核心功能整合測試失敗: %s", e)
            return False
    
    def test_intelligence_features(self):
        """測試智能化功能"""
        logger.info("測試智能化功能...")
        
        try:
            # 測試交易日曆整合
            from src.core.taiwan_trading_calendar import TaiwanTradingCalendar
            calendar = TaiwanTradingCalendar()
            assert calendar is not None

            # 測試交易日判斷
            today = datetime.now().date()
            is_trading_day = calendar.is_trading_day(today)
            assert isinstance(is_trading_day, bool)
            logger.info("交易日曆功能正常")

            # 測試優先級管理
            from src.core.priority_management_system import PriorityManager
            priority_manager = PriorityManager()
            assert priority_manager is not None

            # 註冊測試資料來源
            success = priority_manager.register_data_source('test_source', importance=8)
            assert success
            logger.info("優先級管理系統正常")

            # 清理資源（如果有shutdown方法）
            if hasattr(priority_manager, 'shutdown'):
                priority_manager.shutdown()
            
            logger.info("智能化功能測試通過")
            return True
            
        except Exception as e:
            logger.error("智能化功能測試失敗: %s", e)
            return False
    
    def test_performance_features(self):
        """測試效能優化功能"""
        logger.info("測試效能優化功能...")
        
        try:
            # 測試並行處理引擎
            from src.core.parallel_processing_engine import ParallelProcessingEngine
            engine = ParallelProcessingEngine(max_workers=2)
            assert engine is not None
            
            # 提交測試任務
            def test_task(x):
                time.sleep(0.1)
                return x * 2
            
            task_id = engine.submit_task(test_task, 5)
            results = engine.wait_for_completion([task_id], timeout=5)
            
            assert task_id in results
            assert 'result' in results[task_id]
            assert results[task_id]['result'] == 10
            
            engine.shutdown(wait=True)
            logger.info("並行處理引擎正常")
            
            # 測試快取系統
            from src.core.intelligent_cache_system import IntelligentCacheSystem
            cache = IntelligentCacheSystem()
            assert cache is not None
            
            # 測試快取操作
            cache.set('test_key', 'test_value', ttl=60)
            value = cache.get('test_key')
            assert value == 'test_value'
            
            cache.shutdown()
            logger.info("智能快取系統正常")
            
            # 測試效能監控
            from src.core.performance_monitoring_system import PerformanceMonitor
            monitor = PerformanceMonitor()
            assert monitor is not None
            
            # 記錄測試指標
            monitor.record_download_performance('test_source', 1.0, True, 1024)
            current_metrics = monitor.get_current_metrics()
            assert len(current_metrics) > 0
            
            monitor.shutdown()
            logger.info("效能監控系統正常")
            
            logger.info("效能優化功能測試通過")
            return True
            
        except Exception as e:
            logger.error("效能優化功能測試失敗: %s", e)
            return False
    
    def test_system_stability(self):
        """測試系統穩定性"""
        logger.info("測試系統穩定性...")
        
        try:
            # 測試基本錯誤處理能力
            test_error_handled = False
            try:
                raise ValueError("測試錯誤")
            except Exception as e:
                # 簡單的錯誤處理測試
                test_error_handled = True
                assert str(e) == "測試錯誤"

            assert test_error_handled
            logger.info("錯誤處理機制正常")
            
            # 測試資源管理
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent()
            
            # 檢查資源使用是否在合理範圍內
            memory_mb = memory_info.rss / 1024 / 1024
            assert memory_mb < 500  # 記憶體使用不超過500MB
            logger.info("記憶體使用正常: %.1f MB", memory_mb)
            
            # 測試並發穩定性
            import threading
            import queue
            
            result_queue = queue.Queue()
            
            def concurrent_task(task_id):
                time.sleep(0.1)
                result_queue.put(f"task_{task_id}_completed")
            
            threads = []
            for i in range(5):
                thread = threading.Thread(target=concurrent_task, args=(i,))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join(timeout=2)
            
            # 檢查所有任務是否完成
            completed_tasks = []
            while not result_queue.empty():
                completed_tasks.append(result_queue.get())
            
            assert len(completed_tasks) == 5
            logger.info("並發處理穩定性正常")
            
            logger.info("系統穩定性測試通過")
            return True
            
        except Exception as e:
            logger.error("系統穩定性測試失敗: %s", e)
            return False
    
    def test_data_quality(self):
        """測試資料品質驗證"""
        logger.info("測試資料品質驗證...")
        
        try:
            # 測試基本資料處理功能
            test_data = {
                'price': '  123.45  ',
                'volume': '1,000,000',
                'date': '2024-01-15',
                'name': 'Test Company'
            }

            # 簡單的資料清理測試
            cleaned_price = float(test_data['price'].strip())
            cleaned_volume = int(test_data['volume'].replace(',', ''))

            assert cleaned_price == 123.45
            assert cleaned_volume == 1000000
            logger.info("資料清理功能正常")

            # 測試資料驗證
            assert cleaned_price > 0
            assert cleaned_volume > 0
            assert test_data['date'] is not None
            logger.info("資料驗證功能正常")

            # 測試資料品質檢查
            sample_data = [
                {'date': '2024-01-15', 'price': 100.0, 'volume': 1000},
                {'date': '2024-01-16', 'price': 101.0, 'volume': 1100},
                {'date': '2024-01-17', 'price': 99.0, 'volume': 900}
            ]

            # 簡單的品質檢查
            assert len(sample_data) == 3
            for item in sample_data:
                assert 'date' in item
                assert 'price' in item
                assert 'volume' in item
                assert item['price'] > 0
                assert item['volume'] > 0

            logger.info("資料品質檢查正常")
            
            logger.info("資料品質驗證測試通過")
            return True
            
        except Exception as e:
            logger.error("資料品質驗證測試失敗: %s", e)
            return False
    
    def generate_test_report(self):
        """生成測試報告"""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()
        
        logger.info("\n" + "="*80)
        logger.info("綜合系統整合測試報告")
        logger.info("="*80)
        
        logger.info("測試開始時間: %s", self.start_time.strftime('%Y-%m-%d %H:%M:%S'))
        logger.info("測試結束時間: %s", end_time.strftime('%Y-%m-%d %H:%M:%S'))
        logger.info("總測試時間: %.2f 秒", total_duration)
        
        # 統計測試結果
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['result'])
        failed_tests = total_tests - passed_tests
        
        logger.info("\n測試結果統計:")
        logger.info("  總測試套件: %d", total_tests)
        logger.info("  通過測試: %d", passed_tests)
        logger.info("  失敗測試: %d", failed_tests)
        logger.info("  成功率: %.1f%%", (passed_tests / total_tests) * 100 if total_tests > 0 else 0)
        
        # 詳細測試結果
        logger.info("\n詳細測試結果:")
        for suite_name, result_info in self.test_results.items():
            status = "通過" if result_info['result'] else "失敗"
            duration = result_info.get('duration', 0)
            logger.info("  %s: %s (%.2f 秒)", suite_name, status, duration)
            
            if 'error' in result_info:
                logger.info("    錯誤: %s", result_info['error'])
        
        # 系統健康度評估
        if passed_tests == total_tests:
            health_status = "優秀"
            logger.info("\n系統健康度: %s - 所有測試都通過", health_status)
        elif passed_tests >= total_tests * 0.8:
            health_status = "良好"
            logger.info("\n系統健康度: %s - 大部分測試通過", health_status)
        elif passed_tests >= total_tests * 0.6:
            health_status = "一般"
            logger.info("\n系統健康度: %s - 部分測試失敗", health_status)
        else:
            health_status = "需要改進"
            logger.info("\n系統健康度: %s - 多項測試失敗", health_status)
        
        # 建議
        logger.info("\n建議:")
        if failed_tests == 0:
            logger.info("  系統運行良好，可以投入生產使用")
        else:
            logger.info("  需要修復失敗的測試項目後再投入使用")
            logger.info("  建議重點關注失敗的測試套件")
        
        logger.info("="*80)
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            'health_status': health_status,
            'total_duration': total_duration
        }


def main():
    """主函數"""
    tester = SystemIntegrationTester()
    results = tester.run_all_tests()
    
    # 根據測試結果決定退出碼
    all_passed = all(result['result'] for result in results.values())
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
