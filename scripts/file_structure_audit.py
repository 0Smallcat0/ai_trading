#!/usr/bin/env python3
"""
檔案結構審查工具

此腳本定期審查專案檔案結構，檢測潛在的重複檔案、
過時模組和結構問題，並生成審查報告。

Usage:
    python scripts/file_structure_audit.py
    python scripts/file_structure_audit.py --output audit_report.json
    python scripts/file_structure_audit.py --schedule weekly
"""

import os
import json
import argparse
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict
import ast
import re


class FileStructureAuditor:
    """檔案結構審查器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.audit_results = {
            'timestamp': datetime.now().isoformat(),
            'summary': {},
            'issues': [],
            'recommendations': [],
            'metrics': {}
        }
        
    def calculate_file_hash(self, file_path: Path) -> str:
        """計算檔案雜湊值"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def find_duplicate_files(self) -> List[Dict[str, Any]]:
        """尋找重複檔案"""
        print("🔍 檢查重複檔案...")
        
        file_hashes = defaultdict(list)
        duplicates = []
        
        # 掃描 Python 檔案
        for py_file in self.project_root.rglob('*.py'):
            # 跳過特定目錄
            if any(part in str(py_file) for part in ['.git', '__pycache__', '.pytest_cache', '.venv']):
                continue
                
            file_hash = self.calculate_file_hash(py_file)
            if file_hash:
                file_hashes[file_hash].append(py_file)
        
        # 找出重複檔案
        for file_hash, files in file_hashes.items():
            if len(files) > 1:
                duplicates.append({
                    'hash': file_hash,
                    'files': [str(f.relative_to(self.project_root)) for f in files],
                    'size': files[0].stat().st_size if files[0].exists() else 0
                })
        
        return duplicates
    
    def find_similar_functions(self) -> List[Dict[str, Any]]:
        """尋找相似功能的檔案"""
        print("🔍 檢查相似功能...")
        
        similar_functions = []
        function_patterns = {
            'config_management': [
                r'def.*config.*manager',
                r'def.*parse.*args',
                r'def.*validate.*config',
                r'class.*Config.*Manager'
            ],
            'risk_management': [
                r'def.*risk.*manager',
                r'def.*calculate.*var',
                r'def.*stop.*loss',
                r'class.*Risk.*Manager'
            ],
            'data_processing': [
                r'def.*process.*data',
                r'def.*clean.*data',
                r'def.*transform.*data',
                r'class.*Data.*Processor'
            ],
            'ui_components': [
                r'def.*render.*page',
                r'def.*show.*sidebar',
                r'def.*display.*chart',
                r'st\.'  # Streamlit 相關
            ]
        }
        
        file_functions = defaultdict(list)
        
        # 掃描 Python 檔案中的函數
        for py_file in self.project_root.rglob('*.py'):
            if any(part in str(py_file) for part in ['.git', '__pycache__', '.pytest_cache', '.venv']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for category, patterns in function_patterns.items():
                    matches = []
                    for pattern in patterns:
                        matches.extend(re.findall(pattern, content, re.IGNORECASE))
                    
                    if matches:
                        file_functions[category].append({
                            'file': str(py_file.relative_to(self.project_root)),
                            'matches': len(matches),
                            'patterns': matches[:5]  # 只保留前5個匹配
                        })
                        
            except Exception as e:
                continue
        
        # 找出每個類別中有多個檔案的情況
        for category, files in file_functions.items():
            if len(files) > 1:
                similar_functions.append({
                    'category': category,
                    'files': files,
                    'potential_duplication': len(files) > 2
                })
        
        return similar_functions
    
    def check_file_sizes(self) -> List[Dict[str, Any]]:
        """檢查檔案大小"""
        print("🔍 檢查檔案大小...")
        
        large_files = []
        max_lines = 300  # 根據專案標準
        
        for py_file in self.project_root.rglob('*.py'):
            if any(part in str(py_file) for part in ['.git', '__pycache__', '.pytest_cache', '.venv']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    line_count = len(lines)
                    
                if line_count > max_lines:
                    large_files.append({
                        'file': str(py_file.relative_to(self.project_root)),
                        'lines': line_count,
                        'excess_lines': line_count - max_lines,
                        'severity': 'high' if line_count > max_lines * 2 else 'medium'
                    })
                    
            except Exception:
                continue
        
        return large_files
    
    def check_import_patterns(self) -> List[Dict[str, Any]]:
        """檢查導入模式"""
        print("🔍 檢查導入模式...")
        
        import_issues = []
        
        # 檢查是否有新的過時導入模式
        deprecated_patterns = [
            r'from\s+src\.ui\.web_ui_production_legacy\s+import',
            r'from\s+src\.core\.config_manager\s+import',
            r'from\s+src\.core\.risk_control\s+import',
            r'from\s+src\.execution\.ib_adapter\s+import\s+IBAdapter(?!\s*#.*向後相容)',
        ]
        
        for py_file in self.project_root.rglob('*.py'):
            if any(part in str(py_file) for part in ['.git', '__pycache__', '.pytest_cache', '.venv']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                for line_num, line in enumerate(lines, 1):
                    for pattern in deprecated_patterns:
                        if re.search(pattern, line):
                            import_issues.append({
                                'file': str(py_file.relative_to(self.project_root)),
                                'line': line_num,
                                'content': line.strip(),
                                'issue': 'deprecated_import',
                                'severity': 'high'
                            })
                            
            except Exception:
                continue
        
        return import_issues
    
    def check_naming_conventions(self) -> List[Dict[str, Any]]:
        """檢查命名規範"""
        print("🔍 檢查命名規範...")
        
        naming_issues = []
        
        # 檢查檔案命名
        for py_file in self.project_root.rglob('*.py'):
            if any(part in str(py_file) for part in ['.git', '__pycache__', '.pytest_cache', '.venv']):
                continue
                
            file_name = py_file.stem
            
            # 檢查是否符合 snake_case
            if not re.match(r'^[a-z][a-z0-9_]*$', file_name) and file_name != '__init__':
                naming_issues.append({
                    'file': str(py_file.relative_to(self.project_root)),
                    'issue': 'non_snake_case_filename',
                    'current_name': file_name,
                    'severity': 'medium'
                })
            
            # 檢查是否有可疑的命名模式
            suspicious_patterns = [
                r'.*_legacy$',
                r'.*_old$',
                r'.*_backup$',
                r'.*_temp$',
                r'.*_test$',
                r'.*_debug$'
            ]
            
            for pattern in suspicious_patterns:
                if re.match(pattern, file_name):
                    naming_issues.append({
                        'file': str(py_file.relative_to(self.project_root)),
                        'issue': 'suspicious_naming',
                        'pattern': pattern,
                        'severity': 'medium'
                    })
        
        return naming_issues
    
    def generate_metrics(self) -> Dict[str, Any]:
        """生成專案指標"""
        print("📊 生成專案指標...")
        
        metrics = {
            'total_python_files': 0,
            'total_lines_of_code': 0,
            'average_file_size': 0,
            'files_over_300_lines': 0,
            'directory_structure': {},
            'module_distribution': {}
        }
        
        total_lines = 0
        file_count = 0
        directory_counts = defaultdict(int)
        
        for py_file in self.project_root.rglob('*.py'):
            if any(part in str(py_file) for part in ['.git', '__pycache__', '.pytest_cache', '.venv']):
                continue
                
            file_count += 1
            
            # 計算目錄分佈
            relative_path = py_file.relative_to(self.project_root)
            if len(relative_path.parts) > 1:
                directory_counts[relative_path.parts[0]] += 1
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = len(f.readlines())
                    total_lines += lines
                    
                    if lines > 300:
                        metrics['files_over_300_lines'] += 1
                        
            except Exception:
                continue
        
        metrics['total_python_files'] = file_count
        metrics['total_lines_of_code'] = total_lines
        metrics['average_file_size'] = total_lines / file_count if file_count > 0 else 0
        metrics['directory_structure'] = dict(directory_counts)
        
        return metrics
    
    def run_audit(self) -> Dict[str, Any]:
        """運行完整審查"""
        print("🚀 開始檔案結構審查...")
        print("=" * 50)
        
        # 執行各項檢查
        duplicates = self.find_duplicate_files()
        similar_functions = self.find_similar_functions()
        large_files = self.check_file_sizes()
        import_issues = self.check_import_patterns()
        naming_issues = self.check_naming_conventions()
        metrics = self.generate_metrics()
        
        # 彙總結果
        self.audit_results.update({
            'summary': {
                'duplicate_files': len(duplicates),
                'similar_function_groups': len(similar_functions),
                'large_files': len(large_files),
                'import_issues': len(import_issues),
                'naming_issues': len(naming_issues)
            },
            'issues': {
                'duplicates': duplicates,
                'similar_functions': similar_functions,
                'large_files': large_files,
                'import_issues': import_issues,
                'naming_issues': naming_issues
            },
            'metrics': metrics
        })
        
        # 生成建議
        self.generate_recommendations()
        
        return self.audit_results
    
    def generate_recommendations(self):
        """生成改進建議"""
        recommendations = []
        
        # 基於發現的問題生成建議
        if self.audit_results['summary']['duplicate_files'] > 0:
            recommendations.append({
                'priority': 'high',
                'category': 'duplication',
                'description': f"發現 {self.audit_results['summary']['duplicate_files']} 組重複檔案，建議合併或移除"
            })
        
        if self.audit_results['summary']['large_files'] > 0:
            recommendations.append({
                'priority': 'medium',
                'category': 'file_size',
                'description': f"發現 {self.audit_results['summary']['large_files']} 個大型檔案（>300行），建議拆分"
            })
        
        if self.audit_results['summary']['import_issues'] > 0:
            recommendations.append({
                'priority': 'high',
                'category': 'imports',
                'description': f"發現 {self.audit_results['summary']['import_issues']} 個導入問題，需要立即修復"
            })
        
        # 基於指標生成建議
        if self.audit_results['metrics']['files_over_300_lines'] > 5:
            recommendations.append({
                'priority': 'medium',
                'category': 'code_organization',
                'description': "建議建立檔案大小監控機制，防止檔案過大"
            })
        
        self.audit_results['recommendations'] = recommendations
    
    def generate_report(self) -> str:
        """生成審查報告"""
        results = self.audit_results
        
        report = []
        report.append("📊 檔案結構審查報告")
        report.append("=" * 50)
        report.append(f"審查時間: {results['timestamp'][:19]}")
        report.append("")
        
        # 摘要
        report.append("📋 審查摘要")
        report.append("-" * 20)
        summary = results['summary']
        report.append(f"重複檔案組: {summary['duplicate_files']}")
        report.append(f"相似功能組: {summary['similar_function_groups']}")
        report.append(f"大型檔案: {summary['large_files']}")
        report.append(f"導入問題: {summary['import_issues']}")
        report.append(f"命名問題: {summary['naming_issues']}")
        report.append("")
        
        # 專案指標
        report.append("📊 專案指標")
        report.append("-" * 20)
        metrics = results['metrics']
        report.append(f"Python 檔案總數: {metrics['total_python_files']}")
        report.append(f"代碼總行數: {metrics['total_lines_of_code']:,}")
        report.append(f"平均檔案大小: {metrics['average_file_size']:.1f} 行")
        report.append(f"超過300行的檔案: {metrics['files_over_300_lines']}")
        report.append("")
        
        # 目錄分佈
        if metrics['directory_structure']:
            report.append("📁 目錄分佈")
            report.append("-" * 20)
            for directory, count in sorted(metrics['directory_structure'].items()):
                report.append(f"{directory}: {count} 個檔案")
            report.append("")
        
        # 重要問題
        if summary['import_issues'] > 0 or summary['duplicate_files'] > 0:
            report.append("🚨 需要立即處理的問題")
            report.append("-" * 20)
            
            if summary['import_issues'] > 0:
                report.append(f"❌ {summary['import_issues']} 個導入問題")
                for issue in results['issues']['import_issues'][:3]:
                    report.append(f"   - {issue['file']}:{issue['line']}")
            
            if summary['duplicate_files'] > 0:
                report.append(f"❌ {summary['duplicate_files']} 組重複檔案")
                for dup in results['issues']['duplicates'][:3]:
                    report.append(f"   - {', '.join(dup['files'])}")
            
            report.append("")
        
        # 建議
        if results['recommendations']:
            report.append("💡 改進建議")
            report.append("-" * 20)
            for rec in results['recommendations']:
                priority_icon = "🔴" if rec['priority'] == 'high' else "🟡"
                report.append(f"{priority_icon} {rec['description']}")
            report.append("")
        
        # 健康評分
        total_issues = sum(summary.values())
        if total_issues == 0:
            health_score = "A+ (優秀)"
        elif total_issues <= 5:
            health_score = "B+ (良好)"
        elif total_issues <= 10:
            health_score = "C+ (一般)"
        else:
            health_score = "D (需要改進)"
        
        report.append(f"🏆 檔案結構健康評分: {health_score}")
        
        return "\n".join(report)
    
    def save_results(self, filename: str):
        """保存審查結果"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.audit_results, f, indent=2, ensure_ascii=False)
        print(f"📄 審查結果已保存到: {filename}")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='檔案結構審查工具')
    parser.add_argument('--output', default='file_structure_audit.json', 
                       help='輸出檔案名稱')
    parser.add_argument('--report', action='store_true', 
                       help='顯示詳細報告')
    
    args = parser.parse_args()
    
    auditor = FileStructureAuditor()
    results = auditor.run_audit()
    
    # 生成並顯示報告
    report = auditor.generate_report()
    print(report)
    
    # 保存結果
    auditor.save_results(args.output)
    
    # 根據問題數量設置退出碼
    total_issues = sum(results['summary'].values())
    if total_issues > 10:
        exit(1)  # 問題太多，退出碼為1
    else:
        exit(0)  # 正常退出


if __name__ == '__main__':
    main()
