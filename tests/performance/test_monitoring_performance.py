"""監控系統效能測試

此模組包含監控系統各組件的效能基準測試。
"""

import time
import threading
import psutil
import gc
from typing import Dict, List, Any
from unittest.mock import MagicMock, patch
import sys
import os
from pathlib import Path

# 添加 src 目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class PerformanceTestBase:
    """效能測試基礎類別"""
    
    def __init__(self):
        self.results: Dict[str, Any] = {}
        self.process = psutil.Process()
    
    def measure_time(self, func, *args, **kwargs):
        """測量函數執行時間"""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = (end_time - start_time) * 1000  # 轉換為毫秒
        return result, execution_time
    
    def measure_memory(self, func, *args, **kwargs):
        """測量函數記憶體使用量"""
        gc.collect()  # 強制垃圾回收
        
        memory_before = self.process.memory_info().rss / 1024 / 1024  # MB
        result = func(*args, **kwargs)
        memory_after = self.process.memory_info().rss / 1024 / 1024  # MB
        
        memory_used = memory_after - memory_before
        return result, memory_used
    
    def run_concurrent_test(self, func, num_threads=10, iterations=100):
        """執行並發測試"""
        results = []
        threads = []
        
        def worker():
            for _ in range(iterations):
                start_time = time.perf_counter()
                try:
                    func()
                    end_time = time.perf_counter()
                    results.append((end_time - start_time) * 1000)
                except Exception as e:
                    results.append(f"Error: {e}")
        
        # 啟動線程
        start_time = time.perf_counter()
        for _ in range(num_threads):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # 等待所有線程完成
        for thread in threads:
            thread.join()
        
        total_time = time.perf_counter() - start_time
        
        # 計算統計數據
        valid_results = [r for r in results if isinstance(r, (int, float))]
        error_count = len(results) - len(valid_results)
        
        if valid_results:
            avg_time = sum(valid_results) / len(valid_results)
            max_time = max(valid_results)
            min_time = min(valid_results)
            throughput = len(valid_results) / total_time
        else:
            avg_time = max_time = min_time = throughput = 0
        
        return {
            'total_requests': len(results),
            'successful_requests': len(valid_results),
            'error_count': error_count,
            'total_time': total_time,
            'avg_response_time': avg_time,
            'max_response_time': max_time,
            'min_response_time': min_time,
            'throughput': throughput,
            'requests_per_second': throughput
        }


class PrometheusCollectorPerformanceTest(PerformanceTestBase):
    """Prometheus 收集器效能測試"""
    
    def setUp(self):
        """設置測試環境"""
        # 模擬依賴
        with patch('src.monitoring.prometheus_collector.CollectorRegistry'), \
             patch('src.monitoring.prometheus_collector.generate_latest'), \
             patch('src.monitoring.prometheus_collector.SystemMetricsCollector'), \
             patch('src.monitoring.prometheus_collector.TradingMetricsCollector'), \
             patch('src.monitoring.prometheus_collector.APIMetricsCollector'), \
             patch('src.monitoring.prometheus_collector.BusinessMetricsCollector'):
            
            from src.monitoring.prometheus_collector import PrometheusCollector
            self.collector = PrometheusCollector(collection_interval=1)
    
    def test_initialization_performance(self):
        """測試初始化效能"""
        def init_collector():
            with patch('src.monitoring.prometheus_collector.CollectorRegistry'), \
                 patch('src.monitoring.prometheus_collector.SystemMetricsCollector'), \
                 patch('src.monitoring.prometheus_collector.TradingMetricsCollector'), \
                 patch('src.monitoring.prometheus_collector.APIMetricsCollector'), \
                 patch('src.monitoring.prometheus_collector.BusinessMetricsCollector'):
                
                from src.monitoring.prometheus_collector import PrometheusCollector
                return PrometheusCollector(collection_interval=1)
        
        # 測量初始化時間
        _, init_time = self.measure_time(init_collector)
        
        # 測量初始化記憶體使用
        _, memory_used = self.measure_memory(init_collector)
        
        return {
            'initialization_time_ms': init_time,
            'memory_used_mb': memory_used,
            'target_init_time_ms': 100,  # 目標 <100ms
            'target_memory_mb': 50,      # 目標 <50MB
            'init_time_ok': init_time < 100,
            'memory_ok': memory_used < 50
        }
    
    def test_metrics_collection_performance(self):
        """測試指標收集效能"""
        self.setUp()
        
        # 模擬指標收集
        def collect_metrics():
            return self.collector.get_metrics()
        
        # 測量單次收集時間
        _, collection_time = self.measure_time(collect_metrics)
        
        # 測量並發收集效能
        concurrent_results = self.run_concurrent_test(
            collect_metrics, 
            num_threads=5, 
            iterations=20
        )
        
        return {
            'single_collection_time_ms': collection_time,
            'concurrent_results': concurrent_results,
            'target_collection_time_ms': 50,  # 目標 <50ms
            'target_throughput_rps': 100,     # 目標 >100 RPS
            'collection_time_ok': collection_time < 50,
            'throughput_ok': concurrent_results['requests_per_second'] > 100
        }


class GrafanaConfigPerformanceTest(PerformanceTestBase):
    """Grafana 配置管理器效能測試"""
    
    def setUp(self):
        """設置測試環境"""
        with patch('src.monitoring.grafana_config.GrafanaFace'), \
             patch('src.monitoring.grafana_config.DashboardManager'), \
             patch('src.monitoring.grafana_config.DatasourceManager'), \
             patch('src.monitoring.grafana_config.TemplateGenerator'):
            
            from src.monitoring.grafana_config import GrafanaConfigManager
            self.manager = GrafanaConfigManager()
    
    def test_dashboard_creation_performance(self):
        """測試儀表板創建效能"""
        self.setUp()
        
        def create_dashboard():
            panel_configs = [
                {
                    "title": f"Test Panel {i}",
                    "type": "stat",
                    "metric": f"test_metric_{i}",
                    "grid_pos": {"h": 8, "w": 6, "x": 0, "y": i*8}
                }
                for i in range(10)
            ]
            
            return self.manager.create_custom_dashboard(
                "Performance Test Dashboard",
                ["test", "performance"],
                panel_configs
            )
        
        # 測量創建時間
        _, creation_time = self.measure_time(create_dashboard)
        
        # 測量記憶體使用
        _, memory_used = self.measure_memory(create_dashboard)
        
        return {
            'dashboard_creation_time_ms': creation_time,
            'memory_used_mb': memory_used,
            'target_creation_time_ms': 200,  # 目標 <200ms
            'target_memory_mb': 100,         # 目標 <100MB
            'creation_time_ok': creation_time < 200,
            'memory_ok': memory_used < 100
        }
    
    def test_configuration_export_performance(self):
        """測試配置匯出效能"""
        self.setUp()
        
        def export_config():
            return self.manager.export_configuration()
        
        # 測量匯出時間
        _, export_time = self.measure_time(export_config)
        
        return {
            'export_time_ms': export_time,
            'target_export_time_ms': 500,  # 目標 <500ms
            'export_time_ok': export_time < 500
        }


class MonitorSystemPerformanceTest(PerformanceTestBase):
    """監控系統效能測試"""
    
    def setUp(self):
        """設置測試環境"""
        # 模擬所有依賴
        with patch('src.monitoring.monitor_system.AlertHandler'), \
             patch('src.monitoring.monitor_system.SystemMonitor'), \
             patch('src.monitoring.monitor_system.ThresholdChecker'), \
             patch('src.monitoring.monitor_system.prometheus_exporter'), \
             patch('src.monitoring.monitor_system.alert_manager'), \
             patch('src.monitoring.monitor_system.get_logger'):
            
            from src.monitoring.monitor_system import MonitorSystem
            self.system = MonitorSystem()
    
    def test_system_startup_performance(self):
        """測試系統啟動效能"""
        def startup_system():
            self.setUp()
            return self.system.start()
        
        # 測量啟動時間
        _, startup_time = self.measure_time(startup_system)
        
        # 測量啟動記憶體使用
        _, memory_used = self.measure_memory(startup_system)
        
        return {
            'startup_time_ms': startup_time,
            'memory_used_mb': memory_used,
            'target_startup_time_ms': 1000,  # 目標 <1000ms
            'target_memory_mb': 200,         # 目標 <200MB
            'startup_time_ok': startup_time < 1000,
            'memory_ok': memory_used < 200
        }
    
    def test_status_check_performance(self):
        """測試狀態檢查效能"""
        self.setUp()
        
        def check_status():
            return self.system.get_status()
        
        # 測量狀態檢查時間
        _, check_time = self.measure_time(check_status)
        
        # 測量並發狀態檢查
        concurrent_results = self.run_concurrent_test(
            check_status,
            num_threads=10,
            iterations=50
        )
        
        return {
            'status_check_time_ms': check_time,
            'concurrent_results': concurrent_results,
            'target_check_time_ms': 100,  # 目標 <100ms
            'target_throughput_rps': 50,  # 目標 >50 RPS
            'check_time_ok': check_time < 100,
            'throughput_ok': concurrent_results['requests_per_second'] > 50
        }


def run_performance_tests():
    """執行所有效能測試"""
    print("🚀 開始監控系統效能測試\n")
    
    # 測試類別列表
    test_classes = [
        ("Prometheus 收集器", PrometheusCollectorPerformanceTest),
        ("Grafana 配置管理器", GrafanaConfigPerformanceTest),
        ("監控系統", MonitorSystemPerformanceTest),
    ]
    
    all_results = {}
    
    for test_name, test_class in test_classes:
        print(f"📊 執行 {test_name} 效能測試:")
        
        try:
            tester = test_class()
            test_methods = [method for method in dir(tester) 
                          if method.startswith('test_') and callable(getattr(tester, method))]
            
            class_results = {}
            
            for method_name in test_methods:
                method = getattr(tester, method_name)
                print(f"  🔍 {method_name}...")
                
                try:
                    result = method()
                    class_results[method_name] = result
                    
                    # 顯示關鍵指標
                    if 'time_ms' in str(result):
                        for key, value in result.items():
                            if 'time_ms' in key and isinstance(value, (int, float)):
                                print(f"    ⏱️  {key}: {value:.2f} ms")
                            elif 'memory_mb' in key and isinstance(value, (int, float)):
                                print(f"    💾 {key}: {value:.2f} MB")
                            elif 'throughput' in key and isinstance(value, (int, float)):
                                print(f"    🚀 {key}: {value:.2f} RPS")
                    
                except Exception as e:
                    print(f"    ❌ 測試失敗: {e}")
                    class_results[method_name] = {"error": str(e)}
            
            all_results[test_name] = class_results
            
        except Exception as e:
            print(f"  ❌ {test_name} 測試類別初始化失敗: {e}")
            all_results[test_name] = {"error": str(e)}
        
        print()
    
    # 生成效能報告
    print("="*60)
    print("📋 效能測試總結報告")
    print("="*60)
    
    for test_name, results in all_results.items():
        print(f"\n🔧 {test_name}:")
        
        if "error" in results:
            print(f"  ❌ 測試失敗: {results['error']}")
            continue
        
        for method_name, result in results.items():
            if "error" in result:
                print(f"  ❌ {method_name}: {result['error']}")
            else:
                # 檢查是否達到效能目標
                passed_checks = []
                failed_checks = []
                
                for key, value in result.items():
                    if key.endswith('_ok') and isinstance(value, bool):
                        if value:
                            passed_checks.append(key.replace('_ok', ''))
                        else:
                            failed_checks.append(key.replace('_ok', ''))
                
                status = "✅" if not failed_checks else "⚠️"
                print(f"  {status} {method_name}")
                
                if passed_checks:
                    print(f"    ✅ 通過: {', '.join(passed_checks)}")
                if failed_checks:
                    print(f"    ❌ 未達標: {', '.join(failed_checks)}")
    
    return all_results


if __name__ == "__main__":
    results = run_performance_tests()
    
    # 儲存結果到檔案
    import json
    with open("performance_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 效能測試結果已儲存到 performance_results.json")
    print("🎯 效能基準測試完成！")
