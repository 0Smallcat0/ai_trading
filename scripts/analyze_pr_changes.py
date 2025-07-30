#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PR變更分析工具

此腳本用於分析Pull Request中的變更，識別品質問題和風險。

使用方法:
    python scripts/analyze_pr_changes.py
    python scripts/analyze_pr_changes.py --output reports/pr/changes_analysis.json
"""

import os
import sys
import json
import argparse
import subprocess
from typing import Dict, List, Set
from pathlib import Path


class PRChangeAnalyzer:
    """PR變更分析器"""
    
    def __init__(self):
        """初始化分析器"""
        self.changed_files = []
        self.analysis_result = {
            'changed_files_count': 0,
            'python_files_count': 0,
            'has_large_files': False,
            'large_files': [],
            'quality_score': 10.0,
            'test_coverage': 100.0,
            'security_issues': 0,
            'recommendations': []
        }
    
    def get_changed_files(self) -> List[str]:
        """獲取PR中變更的檔案列表"""
        try:
            # 獲取與main分支的差異
            result = subprocess.run([
                'git', 'diff', '--name-only', 'origin/main...HEAD'
            ], capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode == 0:
                files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
                return files
            else:
                # 如果無法獲取差異，嘗試獲取最近的提交
                result = subprocess.run([
                    'git', 'diff', '--name-only', 'HEAD~1'
                ], capture_output=True, text=True, encoding='utf-8')
                
                if result.returncode == 0:
                    files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
                    return files
                else:
                    print("⚠️  無法獲取變更檔案列表")
                    return []
                    
        except Exception as e:
            print(f"❌ 獲取變更檔案失敗: {e}")
            return []
    
    def analyze_file_sizes(self, files: List[str]) -> None:
        """分析檔案大小"""
        large_files = []
        
        for file_path in files:
            if file_path.endswith('.py') and os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        line_count = len(f.readlines())
                    
                    if line_count > 300:
                        large_files.append({
                            'path': file_path,
                            'lines': line_count
                        })
                        
                except Exception as e:
                    print(f"⚠️  無法讀取檔案 {file_path}: {e}")
        
        self.analysis_result['has_large_files'] = len(large_files) > 0
        self.analysis_result['large_files'] = large_files
        
        if large_files:
            self.analysis_result['recommendations'].append(
                f"重構 {len(large_files)} 個超大檔案，拆分為更小的模組"
            )
    
    def analyze_code_quality(self, files: List[str]) -> None:
        """分析代碼品質"""
        python_files = [f for f in files if f.endswith('.py') and os.path.exists(f)]
        
        if not python_files:
            return
        
        try:
            # 對變更的Python檔案執行Pylint檢查
            result = subprocess.run([
                'poetry', 'run', 'pylint'
            ] + python_files + [
                '--rcfile=config/pylint.ini',
                '--output-format=json'
            ], capture_output=True, text=True, encoding='utf-8')
            
            if result.stdout:
                try:
                    pylint_data = json.loads(result.stdout)
                    if isinstance(pylint_data, list):
                        error_count = len([item for item in pylint_data if item.get('type') == 'error'])
                        warning_count = len([item for item in pylint_data if item.get('type') == 'warning'])
                        
                        # 計算品質分數
                        total_issues = error_count * 2 + warning_count
                        quality_score = max(0, 10 - (total_issues * 0.1))
                        self.analysis_result['quality_score'] = quality_score
                        
                        if quality_score < 8.5:
                            self.analysis_result['recommendations'].append(
                                f"提升代碼品質，修復 {error_count} 個錯誤和 {warning_count} 個警告"
                            )
                            
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            print(f"⚠️  代碼品質分析失敗: {e}")
    
    def analyze_test_coverage(self, files: List[str]) -> None:
        """分析測試覆蓋率"""
        python_files = [f for f in files if f.endswith('.py') and f.startswith('src/')]
        
        if not python_files:
            return
        
        # 檢查是否有對應的測試檔案
        test_files_exist = 0
        for src_file in python_files:
            # 將src/路徑轉換為tests/路徑
            test_path = src_file.replace('src/', 'tests/test_').replace('.py', '.py')
            if os.path.exists(test_path):
                test_files_exist += 1
        
        if python_files:
            coverage_ratio = (test_files_exist / len(python_files)) * 100
            self.analysis_result['test_coverage'] = coverage_ratio
            
            if coverage_ratio < 80:
                missing_tests = len(python_files) - test_files_exist
                self.analysis_result['recommendations'].append(
                    f"為 {missing_tests} 個新增/修改的檔案添加測試"
                )
    
    def analyze_security_issues(self, files: List[str]) -> None:
        """分析安全問題"""
        python_files = [f for f in files if f.endswith('.py') and os.path.exists(f)]
        
        if not python_files:
            return
        
        try:
            # 對變更的Python檔案執行Bandit安全檢查
            result = subprocess.run([
                'poetry', 'run', 'bandit', '-f', 'json'
            ] + python_files, capture_output=True, text=True, encoding='utf-8')
            
            if result.stdout:
                try:
                    bandit_data = json.loads(result.stdout)
                    security_issues = len(bandit_data.get('results', []))
                    self.analysis_result['security_issues'] = security_issues
                    
                    if security_issues > 0:
                        self.analysis_result['recommendations'].append(
                            f"修復 {security_issues} 個安全問題"
                        )
                        
                except json.JSONDecodeError:
                    pass
                    
        except Exception as e:
            print(f"⚠️  安全分析失敗: {e}")
    
    def analyze_changes(self) -> Dict:
        """分析PR變更"""
        print("🔍 分析PR變更...")
        
        # 獲取變更檔案
        self.changed_files = self.get_changed_files()
        python_files = [f for f in self.changed_files if f.endswith('.py')]
        
        self.analysis_result['changed_files_count'] = len(self.changed_files)
        self.analysis_result['python_files_count'] = len(python_files)
        
        print(f"📁 變更檔案: {len(self.changed_files)} 個")
        print(f"🐍 Python檔案: {len(python_files)} 個")
        
        if python_files:
            # 分析檔案大小
            print("📏 分析檔案大小...")
            self.analyze_file_sizes(self.changed_files)
            
            # 分析代碼品質
            print("🔍 分析代碼品質...")
            self.analyze_code_quality(self.changed_files)
            
            # 分析測試覆蓋率
            print("🧪 分析測試覆蓋率...")
            self.analyze_test_coverage(self.changed_files)
            
            # 分析安全問題
            print("🔒 分析安全問題...")
            self.analyze_security_issues(self.changed_files)
        
        return self.analysis_result


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='分析PR變更')
    parser.add_argument('--output', type=str, help='輸出檔案路徑')
    
    args = parser.parse_args()
    
    analyzer = PRChangeAnalyzer()
    result = analyzer.analyze_changes()
    
    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"✅ 分析結果已保存: {args.output}")
    else:
        print("\n📊 分析結果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
