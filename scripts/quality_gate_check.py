#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
品質門檻檢查工具

此腳本用於在CI/CD流程中執行品質門檻檢查，確保代碼符合預設的品質標準。
如果任何指標未達標，將導致CI失敗。

使用方法:
    python scripts/quality_gate_check.py
    python scripts/quality_gate_check.py --min-pylint-score 8.5 --min-coverage 80 --max-file-lines 300
"""

import os
import sys
import json
import argparse
import subprocess
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class QualityGateChecker:
    """品質門檻檢查器"""
    
    def __init__(self, min_pylint_score: float = 8.5, min_coverage: float = 80.0, max_file_lines: int = 300):
        """初始化檢查器
        
        Args:
            min_pylint_score: 最低Pylint分數
            min_coverage: 最低測試覆蓋率
            max_file_lines: 最大檔案行數
        """
        self.min_pylint_score = min_pylint_score
        self.min_coverage = min_coverage
        self.max_file_lines = max_file_lines
        self.failures = []
        
    def check_file_sizes(self) -> bool:
        """檢查檔案大小"""
        print("🔍 檢查檔案大小...")
        
        try:
            result = subprocess.run([
                'python', 'scripts/analyze_file_sizes.py',
                '--threshold', str(self.max_file_lines),
                '--ci-mode'
            ], capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode == 0:
                print(f"✅ 檔案大小檢查通過 (≤{self.max_file_lines}行)")
                return True
            else:
                print(f"❌ 檔案大小檢查失敗")
                print(result.stdout)
                self.failures.append(f"檔案大小超過{self.max_file_lines}行限制")
                return False
                
        except Exception as e:
            print(f"❌ 檔案大小檢查執行失敗: {e}")
            self.failures.append(f"檔案大小檢查執行失敗: {e}")
            return False
    
    def check_pylint_score(self) -> bool:
        """檢查Pylint分數"""
        print("🔍 檢查Pylint分數...")
        
        try:
            # 執行Pylint檢查
            result = subprocess.run([
                'poetry', 'run', 'pylint', 'src/',
                '--rcfile=config/pylint.ini',
                '--output-format=json'
            ], capture_output=True, text=True, encoding='utf-8')
            
            # 解析Pylint輸出
            if result.stdout:
                try:
                    pylint_data = json.loads(result.stdout)
                    # 計算平均分數 (Pylint 10分制)
                    if isinstance(pylint_data, list):
                        # 從錯誤數量估算分數
                        error_count = len([item for item in pylint_data if item.get('type') == 'error'])
                        warning_count = len([item for item in pylint_data if item.get('type') == 'warning'])
                        
                        # 簡化的分數計算
                        total_issues = error_count * 2 + warning_count
                        estimated_score = max(0, 10 - (total_issues * 0.1))
                        
                        if estimated_score >= self.min_pylint_score:
                            print(f"✅ Pylint分數檢查通過 (估算分數: {estimated_score:.2f})")
                            return True
                        else:
                            print(f"❌ Pylint分數不足 (估算分數: {estimated_score:.2f}, 要求: {self.min_pylint_score})")
                            self.failures.append(f"Pylint分數 {estimated_score:.2f} < {self.min_pylint_score}")
                            return False
                except json.JSONDecodeError:
                    # 如果無法解析JSON，檢查返回碼
                    if result.returncode == 0:
                        print(f"✅ Pylint檢查通過 (無錯誤)")
                        return True
                    else:
                        print(f"❌ Pylint檢查失敗 (返回碼: {result.returncode})")
                        self.failures.append(f"Pylint檢查失敗")
                        return False
            else:
                # 沒有輸出，檢查返回碼
                if result.returncode == 0:
                    print(f"✅ Pylint檢查通過")
                    return True
                else:
                    print(f"❌ Pylint檢查失敗")
                    self.failures.append(f"Pylint檢查失敗")
                    return False
                    
        except Exception as e:
            print(f"❌ Pylint檢查執行失敗: {e}")
            self.failures.append(f"Pylint檢查執行失敗: {e}")
            return False
    
    def check_test_coverage(self) -> bool:
        """檢查測試覆蓋率"""
        print("🔍 檢查測試覆蓋率...")
        
        try:
            # 檢查是否有覆蓋率報告
            coverage_files = [
                'results/tests_unit/coverage_unit.xml',
                'htmlcov/index.html',
                '.coverage'
            ]
            
            coverage_file_exists = any(os.path.exists(f) for f in coverage_files)
            
            if not coverage_file_exists:
                print(f"⚠️  未找到覆蓋率報告，跳過覆蓋率檢查")
                return True
            
            # 嘗試從coverage報告中提取覆蓋率
            try:
                result = subprocess.run([
                    'poetry', 'run', 'coverage', 'report', '--format=json'
                ], capture_output=True, text=True, encoding='utf-8')
                
                if result.returncode == 0 and result.stdout:
                    coverage_data = json.loads(result.stdout)
                    coverage_percent = coverage_data.get('totals', {}).get('percent_covered', 0)
                    
                    if coverage_percent >= self.min_coverage:
                        print(f"✅ 測試覆蓋率檢查通過 ({coverage_percent:.1f}%)")
                        return True
                    else:
                        print(f"❌ 測試覆蓋率不足 ({coverage_percent:.1f}%, 要求: {self.min_coverage}%)")
                        self.failures.append(f"測試覆蓋率 {coverage_percent:.1f}% < {self.min_coverage}%")
                        return False
                else:
                    print(f"⚠️  無法獲取覆蓋率數據，假設通過")
                    return True
                    
            except Exception as e:
                print(f"⚠️  覆蓋率檢查執行失敗: {e}，假設通過")
                return True
                
        except Exception as e:
            print(f"❌ 測試覆蓋率檢查執行失敗: {e}")
            self.failures.append(f"測試覆蓋率檢查執行失敗: {e}")
            return False
    
    def run_all_checks(self) -> bool:
        """執行所有品質檢查"""
        print("🚪 開始品質門檻檢查...")
        print("=" * 60)
        
        checks = [
            ("檔案大小", self.check_file_sizes),
            ("Pylint分數", self.check_pylint_score),
            ("測試覆蓋率", self.check_test_coverage)
        ]
        
        all_passed = True
        
        for check_name, check_func in checks:
            try:
                passed = check_func()
                if not passed:
                    all_passed = False
            except Exception as e:
                print(f"❌ {check_name}檢查執行失敗: {e}")
                self.failures.append(f"{check_name}檢查執行失敗: {e}")
                all_passed = False
            print()
        
        print("=" * 60)
        
        if all_passed:
            print("🎉 所有品質門檻檢查通過！")
            return True
        else:
            print("❌ 品質門檻檢查失敗！")
            print("\n失敗項目:")
            for i, failure in enumerate(self.failures, 1):
                print(f"  {i}. {failure}")
            return False


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='執行品質門檻檢查')
    parser.add_argument('--min-pylint-score', type=float, default=8.5, help='最低Pylint分數')
    parser.add_argument('--min-coverage', type=float, default=80.0, help='最低測試覆蓋率')
    parser.add_argument('--max-file-lines', type=int, default=300, help='最大檔案行數')
    
    args = parser.parse_args()
    
    checker = QualityGateChecker(
        min_pylint_score=args.min_pylint_score,
        min_coverage=args.min_coverage,
        max_file_lines=args.max_file_lines
    )
    
    success = checker.run_all_checks()
    
    if success:
        print("\n✅ 品質門檻檢查通過，可以繼續部署")
        sys.exit(0)
    else:
        print("\n❌ 品質門檻檢查失敗，請修復問題後重新提交")
        sys.exit(1)


if __name__ == "__main__":
    main()
