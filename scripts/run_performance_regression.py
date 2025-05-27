#!/usr/bin/env python3
"""
效能回歸測試腳本

此腳本執行效能回歸測試，比較當前效能與基準效能，檢測效能退化。
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.performance.benchmark_config import (
    API_BENCHMARKS,
    REGRESSION_THRESHOLDS,
    CI_PERFORMANCE_CONFIG
)


class PerformanceRegressionTester:
    """效能回歸測試器"""
    
    def __init__(self, project_root: str = "."):
        """
        初始化效能回歸測試器
        
        Args:
            project_root: 項目根目錄路徑
        """
        self.project_root = Path(project_root).resolve()
        self.reports_dir = self.project_root / "tests" / "performance" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        self.baseline_file = self.reports_dir / CI_PERFORMANCE_CONFIG["baseline_file"]
        self.results_file = self.reports_dir / CI_PERFORMANCE_CONFIG["results_file"]
        self.comparison_file = self.reports_dir / CI_PERFORMANCE_CONFIG["comparison_file"]
        
        self.regression_results = {
            "timestamp": datetime.now().isoformat(),
            "baseline_exists": self.baseline_file.exists(),
            "tests": {},
            "regressions": [],
            "summary": {
                "total_tests": 0,
                "regression_count": 0,
                "improvement_count": 0,
                "stable_count": 0
            }
        }
    
    def run_performance_tests(self) -> bool:
        """
        執行效能測試
        
        Returns:
            bool: 測試是否成功執行
        """
        print("🚀 執行效能基準測試...")
        
        try:
            # 執行 pytest-benchmark 測試
            cmd = [
                sys.executable, "-m", "pytest",
                "tests/performance/test_api_benchmarks.py",
                "--benchmark-only",
                "--benchmark-json=" + str(self.results_file),
                "--benchmark-sort=mean",
                "--benchmark-columns=min,max,mean,stddev,rounds,iterations",
                "-v"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5分鐘超時
            )
            
            print(f"效能測試完成，返回碼: {result.returncode}")
            
            if result.returncode != 0:
                print(f"效能測試失敗: {result.stderr}")
                return False
            
            return True
            
        except subprocess.TimeoutExpired:
            print("❌ 效能測試超時")
            return False
        except Exception as e:
            print(f"❌ 效能測試執行失敗: {e}")
            return False
    
    def load_baseline(self) -> Optional[Dict[str, Any]]:
        """
        載入基準效能數據
        
        Returns:
            Optional[Dict[str, Any]]: 基準數據，如果不存在則返回 None
        """
        if not self.baseline_file.exists():
            print("⚠️ 基準文件不存在，將創建新的基準")
            return None
        
        try:
            with open(self.baseline_file, 'r', encoding='utf-8') as f:
                baseline = json.load(f)
            print(f"✅ 載入基準文件: {self.baseline_file}")
            return baseline
        except Exception as e:
            print(f"❌ 載入基準文件失敗: {e}")
            return None
    
    def load_current_results(self) -> Optional[Dict[str, Any]]:
        """
        載入當前測試結果
        
        Returns:
            Optional[Dict[str, Any]]: 當前測試結果，如果不存在則返回 None
        """
        if not self.results_file.exists():
            print("❌ 測試結果文件不存在")
            return None
        
        try:
            with open(self.results_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            print(f"✅ 載入測試結果: {self.results_file}")
            return results
        except Exception as e:
            print(f"❌ 載入測試結果失敗: {e}")
            return None
    
    def compare_performance(
        self, 
        baseline: Dict[str, Any], 
        current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        比較效能數據
        
        Args:
            baseline: 基準效能數據
            current: 當前效能數據
            
        Returns:
            Dict[str, Any]: 比較結果
        """
        comparison = {
            "timestamp": datetime.now().isoformat(),
            "baseline_timestamp": baseline.get("datetime", "unknown"),
            "current_timestamp": current.get("datetime", "unknown"),
            "comparisons": {},
            "regressions": [],
            "improvements": [],
            "summary": {
                "total_benchmarks": 0,
                "regressions": 0,
                "improvements": 0,
                "stable": 0
            }
        }
        
        baseline_benchmarks = {
            bench["name"]: bench 
            for bench in baseline.get("benchmarks", [])
        }
        
        current_benchmarks = {
            bench["name"]: bench 
            for bench in current.get("benchmarks", [])
        }
        
        # 比較共同的基準測試
        common_benchmarks = set(baseline_benchmarks.keys()) & set(current_benchmarks.keys())
        
        for bench_name in common_benchmarks:
            baseline_bench = baseline_benchmarks[bench_name]
            current_bench = current_benchmarks[bench_name]
            
            baseline_mean = baseline_bench["stats"]["mean"]
            current_mean = current_bench["stats"]["mean"]
            
            # 計算變化百分比
            change_percent = ((current_mean - baseline_mean) / baseline_mean) * 100
            
            bench_comparison = {
                "name": bench_name,
                "baseline_mean": baseline_mean,
                "current_mean": current_mean,
                "change_percent": change_percent,
                "change_ms": (current_mean - baseline_mean) * 1000,
                "status": "stable"
            }
            
            # 判斷是否為回歸
            if change_percent > REGRESSION_THRESHOLDS["response_time_increase_percent"]:
                bench_comparison["status"] = "regression"
                comparison["regressions"].append(bench_comparison)
                comparison["summary"]["regressions"] += 1
            elif change_percent < -10:  # 改善超過 10%
                bench_comparison["status"] = "improvement"
                comparison["improvements"].append(bench_comparison)
                comparison["summary"]["improvements"] += 1
            else:
                comparison["summary"]["stable"] += 1
            
            comparison["comparisons"][bench_name] = bench_comparison
            comparison["summary"]["total_benchmarks"] += 1
        
        return comparison
    
    def create_baseline(self, current_results: Dict[str, Any]) -> bool:
        """
        創建新的效能基準
        
        Args:
            current_results: 當前測試結果
            
        Returns:
            bool: 是否成功創建基準
        """
        try:
            with open(self.baseline_file, 'w', encoding='utf-8') as f:
                json.dump(current_results, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 創建新的效能基準: {self.baseline_file}")
            return True
            
        except Exception as e:
            print(f"❌ 創建基準失敗: {e}")
            return False
    
    def save_comparison_results(self, comparison: Dict[str, Any]) -> bool:
        """
        保存比較結果
        
        Args:
            comparison: 比較結果
            
        Returns:
            bool: 是否成功保存
        """
        try:
            with open(self.comparison_file, 'w', encoding='utf-8') as f:
                json.dump(comparison, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 保存比較結果: {self.comparison_file}")
            return True
            
        except Exception as e:
            print(f"❌ 保存比較結果失敗: {e}")
            return False
    
    def generate_report(self, comparison: Optional[Dict[str, Any]] = None) -> None:
        """
        生成效能回歸報告
        
        Args:
            comparison: 比較結果，如果為 None 則只生成當前結果報告
        """
        print("\n" + "="*60)
        print("效能回歸測試報告")
        print("="*60)
        
        if comparison is None:
            print("📊 當前效能測試結果（無基準比較）")
            current_results = self.load_current_results()
            if current_results and "benchmarks" in current_results:
                for bench in current_results["benchmarks"]:
                    mean_ms = bench["stats"]["mean"] * 1000
                    print(f"   {bench['name']}: {mean_ms:.2f}ms")
            return
        
        summary = comparison["summary"]
        print(f"📊 效能比較摘要:")
        print(f"   總基準測試數: {summary['total_benchmarks']}")
        print(f"   效能回歸: {summary['regressions']}")
        print(f"   效能改善: {summary['improvements']}")
        print(f"   效能穩定: {summary['stable']}")
        
        if comparison["regressions"]:
            print(f"\n❌ 效能回歸 ({len(comparison['regressions'])} 個):")
            for regression in comparison["regressions"]:
                print(f"   {regression['name']}: "
                      f"{regression['change_percent']:+.1f}% "
                      f"({regression['change_ms']:+.2f}ms)")
        
        if comparison["improvements"]:
            print(f"\n✅ 效能改善 ({len(comparison['improvements'])} 個):")
            for improvement in comparison["improvements"]:
                print(f"   {improvement['name']}: "
                      f"{improvement['change_percent']:+.1f}% "
                      f"({improvement['change_ms']:+.2f}ms)")
        
        print("="*60)
    
    def run_regression_test(self, update_baseline: bool = False) -> bool:
        """
        執行完整的效能回歸測試
        
        Args:
            update_baseline: 是否更新基準
            
        Returns:
            bool: 測試是否通過（無回歸）
        """
        print("🔍 開始效能回歸測試...")
        
        # 1. 執行效能測試
        if not self.run_performance_tests():
            return False
        
        # 2. 載入當前結果
        current_results = self.load_current_results()
        if current_results is None:
            return False
        
        # 3. 載入基準
        baseline = self.load_baseline()
        
        if baseline is None or update_baseline:
            # 創建新基準
            self.create_baseline(current_results)
            self.generate_report()
            return True
        
        # 4. 比較效能
        comparison = self.compare_performance(baseline, current_results)
        
        # 5. 保存比較結果
        self.save_comparison_results(comparison)
        
        # 6. 生成報告
        self.generate_report(comparison)
        
        # 7. 判斷是否有回歸
        has_regression = comparison["summary"]["regressions"] > 0
        
        if has_regression and CI_PERFORMANCE_CONFIG["fail_on_regression"]:
            print(f"\n❌ 檢測到 {comparison['summary']['regressions']} 個效能回歸")
            return False
        
        print(f"\n✅ 效能回歸測試通過")
        return True


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="效能回歸測試腳本")
    parser.add_argument(
        "--project-root",
        default=".",
        help="項目根目錄路徑"
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="更新效能基準"
    )
    parser.add_argument(
        "--no-fail-on-regression",
        action="store_true",
        help="即使有回歸也不失敗"
    )
    
    args = parser.parse_args()
    
    # 創建測試器
    tester = PerformanceRegressionTester(args.project_root)
    
    # 設置失敗策略
    if args.no_fail_on_regression:
        CI_PERFORMANCE_CONFIG["fail_on_regression"] = False
    
    try:
        # 執行回歸測試
        success = tester.run_regression_test(args.update_baseline)
        
        # 設置退出碼
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n測試被用戶中斷")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 測試執行失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
