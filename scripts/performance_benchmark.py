#!/usr/bin/env python3
"""
性能基準測試工具

此腳本用於測試和比較整合前後的系統性能，
監控推薦模組的記憶體使用和執行時間。

Usage:
    python scripts/performance_benchmark.py
    python scripts/performance_benchmark.py --module risk_management
    python scripts/performance_benchmark.py --compare --baseline baseline.json
"""

import time
import psutil
import json
import argparse
import tracemalloc
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class PerformanceMetrics:
    """性能指標"""
    module_name: str
    execution_time: float  # 秒
    memory_usage: float    # MB
    cpu_usage: float       # 百分比
    import_time: float     # 導入時間（秒）
    timestamp: str
    version: str = "unknown"


class PerformanceBenchmark:
    """性能基準測試器"""
    
    def __init__(self):
        self.results = []
        self.baseline_data = None
        
    def measure_import_time(self, module_path: str) -> float:
        """測量模組導入時間"""
        start_time = time.perf_counter()
        try:
            # 動態導入模組
            parts = module_path.split('.')
            module = __import__(module_path)
            for part in parts[1:]:
                module = getattr(module, part)
            end_time = time.perf_counter()
            return end_time - start_time
        except ImportError as e:
            print(f"⚠️ 無法導入模組 {module_path}: {e}")
            return -1
    
    def measure_memory_usage(self, func, *args, **kwargs) -> tuple:
        """測量函數執行的記憶體使用"""
        tracemalloc.start()
        
        # 記錄初始記憶體
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 執行函數
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            success = True
        except Exception as e:
            print(f"⚠️ 函數執行失敗: {e}")
            result = None
            success = False
        end_time = time.perf_counter()
        
        # 記錄最終記憶體
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_diff = final_memory - initial_memory
        
        # 獲取詳細記憶體統計
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        execution_time = end_time - start_time
        
        return {
            'execution_time': execution_time,
            'memory_diff': memory_diff,
            'peak_memory': peak / 1024 / 1024,  # MB
            'success': success,
            'result': result
        }
    
    def benchmark_ui_modules(self) -> List[PerformanceMetrics]:
        """基準測試 UI 模組"""
        ui_modules = [
            ('src.ui.web_ui_production', '推薦版本'),
            ('src.ui.web_ui_production_legacy', '過時版本'),
            ('src.ui.web_ui_redesigned', '設計版本'),
        ]
        
        results = []
        
        for module_path, description in ui_modules:
            print(f"🔍 測試 UI 模組: {description}")
            
            # 測量導入時間
            import_time = self.measure_import_time(module_path)
            
            if import_time >= 0:
                # 測量基本功能（如果有的話）
                try:
                    module = __import__(module_path, fromlist=[''])
                    
                    # 測量記憶體使用
                    def dummy_function():
                        # 模擬基本操作
                        return hasattr(module, 'main')
                    
                    metrics = self.measure_memory_usage(dummy_function)
                    
                    result = PerformanceMetrics(
                        module_name=f"{module_path} ({description})",
                        execution_time=metrics['execution_time'],
                        memory_usage=metrics['memory_diff'],
                        cpu_usage=psutil.cpu_percent(interval=0.1),
                        import_time=import_time,
                        timestamp=datetime.now().isoformat()
                    )
                    
                    results.append(result)
                    
                except Exception as e:
                    print(f"⚠️ 測試失敗 {module_path}: {e}")
        
        return results
    
    def benchmark_config_modules(self) -> List[PerformanceMetrics]:
        """基準測試配置管理模組"""
        config_modules = [
            ('src.utils.config_manager', '推薦版本'),
            ('src.core.config_manager', '過時版本'),
            ('src.core.config_validator', '驗證器'),
        ]
        
        results = []
        
        for module_path, description in config_modules:
            print(f"🔍 測試配置模組: {description}")
            
            import_time = self.measure_import_time(module_path)
            
            if import_time >= 0:
                try:
                    # 測量配置創建性能
                    def test_config_creation():
                        module = __import__(module_path, fromlist=[''])
                        
                        # 嘗試創建配置管理器
                        if hasattr(module, 'create_default_config_manager'):
                            return module.create_default_config_manager()
                        elif hasattr(module, 'ConfigValidator'):
                            return module.ConfigValidator()
                        else:
                            return True
                    
                    metrics = self.measure_memory_usage(test_config_creation)
                    
                    result = PerformanceMetrics(
                        module_name=f"{module_path} ({description})",
                        execution_time=metrics['execution_time'],
                        memory_usage=metrics['memory_diff'],
                        cpu_usage=psutil.cpu_percent(interval=0.1),
                        import_time=import_time,
                        timestamp=datetime.now().isoformat()
                    )
                    
                    results.append(result)
                    
                except Exception as e:
                    print(f"⚠️ 測試失敗 {module_path}: {e}")
        
        return results
    
    def benchmark_risk_modules(self) -> List[PerformanceMetrics]:
        """基準測試風險管理模組"""
        risk_modules = [
            ('src.risk_management.risk_manager_refactored', '推薦版本'),
            ('src.core.risk_control', '過時版本'),
        ]
        
        results = []
        
        for module_path, description in risk_modules:
            print(f"🔍 測試風險管理模組: {description}")
            
            import_time = self.measure_import_time(module_path)
            
            if import_time >= 0:
                try:
                    def test_risk_calculation():
                        module = __import__(module_path, fromlist=[''])
                        
                        # 嘗試創建風險管理器
                        if hasattr(module, 'RiskManager'):
                            risk_manager = module.RiskManager()
                            # 模擬基本風險計算
                            return True
                        return False
                    
                    metrics = self.measure_memory_usage(test_risk_calculation)
                    
                    result = PerformanceMetrics(
                        module_name=f"{module_path} ({description})",
                        execution_time=metrics['execution_time'],
                        memory_usage=metrics['memory_diff'],
                        cpu_usage=psutil.cpu_percent(interval=0.1),
                        import_time=import_time,
                        timestamp=datetime.now().isoformat()
                    )
                    
                    results.append(result)
                    
                except Exception as e:
                    print(f"⚠️ 測試失敗 {module_path}: {e}")
        
        return results
    
    def benchmark_ib_modules(self) -> List[PerformanceMetrics]:
        """基準測試 IB 適配器模組"""
        ib_modules = [
            ('src.execution.ib_adapter_refactored', '推薦版本'),
            ('src.execution.ib_adapter', '過時版本'),
        ]
        
        results = []
        
        for module_path, description in ib_modules:
            print(f"🔍 測試 IB 適配器模組: {description}")
            
            import_time = self.measure_import_time(module_path)
            
            if import_time >= 0:
                try:
                    def test_ib_adapter():
                        module = __import__(module_path, fromlist=[''])
                        
                        # 檢查是否有適配器類別
                        if hasattr(module, 'IBAdapterRefactored'):
                            return True
                        elif hasattr(module, 'IBAdapter'):
                            return True
                        return False
                    
                    metrics = self.measure_memory_usage(test_ib_adapter)
                    
                    result = PerformanceMetrics(
                        module_name=f"{module_path} ({description})",
                        execution_time=metrics['execution_time'],
                        memory_usage=metrics['memory_diff'],
                        cpu_usage=psutil.cpu_percent(interval=0.1),
                        import_time=import_time,
                        timestamp=datetime.now().isoformat()
                    )
                    
                    results.append(result)
                    
                except Exception as e:
                    print(f"⚠️ 測試失敗 {module_path}: {e}")
                    # 即使測試失敗，也記錄基本的導入時間
                    result = PerformanceMetrics(
                        module_name=f"{module_path} ({description}) - 測試失敗",
                        execution_time=0.0,
                        memory_usage=0.0,
                        cpu_usage=psutil.cpu_percent(interval=0.1),
                        import_time=import_time,
                        timestamp=datetime.now().isoformat()
                    )
                    results.append(result)
            else:
                print(f"⚠️ 導入失敗 {module_path}")

        return results
    
    def run_full_benchmark(self) -> List[PerformanceMetrics]:
        """運行完整的基準測試"""
        all_results = []
        
        print("🚀 開始性能基準測試...")
        print("=" * 50)
        
        # 測試各個模組類別
        all_results.extend(self.benchmark_ui_modules())
        all_results.extend(self.benchmark_config_modules())
        all_results.extend(self.benchmark_risk_modules())
        all_results.extend(self.benchmark_ib_modules())
        
        self.results = all_results
        return all_results
    
    def save_results(self, filename: str):
        """保存測試結果"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total / 1024 / 1024 / 1024,  # GB
                'python_version': sys.version,
            },
            'results': [asdict(result) for result in self.results]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"📄 結果已保存到: {filename}")
    
    def load_baseline(self, filename: str):
        """載入基準數據"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.baseline_data = json.load(f)
            print(f"📊 基準數據已載入: {filename}")
        except FileNotFoundError:
            print(f"⚠️ 基準文件不存在: {filename}")
    
    def compare_with_baseline(self) -> str:
        """與基準數據比較"""
        if not self.baseline_data or not self.results:
            return "❌ 缺少基準數據或當前結果"
        
        report = []
        report.append("📊 性能比較報告")
        report.append("=" * 50)
        
        # 按模組類型分組比較
        current_by_name = {r.module_name: r for r in self.results}
        baseline_by_name = {r['module_name']: r for r in self.baseline_data['results']}
        
        for module_name, current in current_by_name.items():
            if module_name in baseline_by_name:
                baseline = baseline_by_name[module_name]
                
                report.append(f"\n🔍 {module_name}:")
                
                # 執行時間比較
                time_diff = current.execution_time - baseline['execution_time']
                time_percent = (time_diff / baseline['execution_time']) * 100 if baseline['execution_time'] > 0 else 0
                
                if time_percent > 10:
                    report.append(f"  ⚠️ 執行時間: {current.execution_time:.4f}s (↑{time_percent:.1f}%)")
                elif time_percent < -10:
                    report.append(f"  ✅ 執行時間: {current.execution_time:.4f}s (↓{abs(time_percent):.1f}%)")
                else:
                    report.append(f"  ➡️ 執行時間: {current.execution_time:.4f}s (~{time_percent:.1f}%)")
                
                # 記憶體使用比較
                memory_diff = current.memory_usage - baseline['memory_usage']
                if abs(memory_diff) > 1:  # 超過 1MB 差異
                    if memory_diff > 0:
                        report.append(f"  ⚠️ 記憶體使用: {current.memory_usage:.2f}MB (↑{memory_diff:.2f}MB)")
                    else:
                        report.append(f"  ✅ 記憶體使用: {current.memory_usage:.2f}MB (↓{abs(memory_diff):.2f}MB)")
                else:
                    report.append(f"  ➡️ 記憶體使用: {current.memory_usage:.2f}MB (~{memory_diff:.2f}MB)")
        
        return "\n".join(report)
    
    def generate_report(self) -> str:
        """生成性能報告"""
        if not self.results:
            return "❌ 沒有測試結果"
        
        report = []
        report.append("📊 性能基準測試報告")
        report.append("=" * 50)
        report.append(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"測試模組數: {len(self.results)}")
        report.append("")
        
        # 按類別分組顯示
        ui_results = [r for r in self.results if 'ui' in r.module_name.lower()]
        config_results = [r for r in self.results if 'config' in r.module_name.lower()]
        risk_results = [r for r in self.results if 'risk' in r.module_name.lower()]
        ib_results = [r for r in self.results if 'ib_adapter' in r.module_name.lower()]
        
        for category, results in [
            ("UI 模組", ui_results),
            ("配置管理模組", config_results),
            ("風險管理模組", risk_results),
            ("IB 適配器模組", ib_results)
        ]:
            if results:
                report.append(f"### {category}")
                for result in results:
                    report.append(f"  📦 {result.module_name}")
                    report.append(f"     導入時間: {result.import_time:.4f}s")
                    report.append(f"     執行時間: {result.execution_time:.4f}s")
                    report.append(f"     記憶體使用: {result.memory_usage:.2f}MB")
                    report.append(f"     CPU 使用: {result.cpu_usage:.1f}%")
                    report.append("")
        
        # 性能建議
        report.append("🔧 性能建議:")
        
        # 找出最慢的模組
        slowest = max(self.results, key=lambda x: x.execution_time)
        report.append(f"  - 最慢模組: {slowest.module_name} ({slowest.execution_time:.4f}s)")
        
        # 找出記憶體使用最多的模組
        memory_heavy = max(self.results, key=lambda x: x.memory_usage)
        report.append(f"  - 記憶體使用最多: {memory_heavy.module_name} ({memory_heavy.memory_usage:.2f}MB)")
        
        return "\n".join(report)


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='性能基準測試')
    parser.add_argument('--module', choices=['ui', 'config', 'risk', 'ib'], 
                       help='測試特定模組類型')
    parser.add_argument('--output', default='performance_results.json', 
                       help='輸出檔案名稱')
    parser.add_argument('--baseline', help='基準數據檔案')
    parser.add_argument('--compare', action='store_true', help='與基準數據比較')
    
    args = parser.parse_args()
    
    benchmark = PerformanceBenchmark()
    
    # 載入基準數據（如果提供）
    if args.baseline:
        benchmark.load_baseline(args.baseline)
    
    # 運行測試
    if args.module:
        if args.module == 'ui':
            results = benchmark.benchmark_ui_modules()
        elif args.module == 'config':
            results = benchmark.benchmark_config_modules()
        elif args.module == 'risk':
            results = benchmark.benchmark_risk_modules()
        elif args.module == 'ib':
            results = benchmark.benchmark_ib_modules()
        # 設置結果到 benchmark 實例中
        benchmark.results = results
    else:
        results = benchmark.run_full_benchmark()
    
    # 生成報告
    report = benchmark.generate_report()
    print(report)
    
    # 比較基準（如果要求）
    if args.compare and args.baseline:
        comparison = benchmark.compare_with_baseline()
        print("\n" + comparison)
    
    # 保存結果
    benchmark.save_results(args.output)


if __name__ == '__main__':
    main()
