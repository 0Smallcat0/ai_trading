#!/usr/bin/env python3
"""
過時模組導入檢查工具

此腳本檢查代碼中是否使用了已標記為過時的模組，
並提供推薦的替代方案。

Usage:
    python scripts/check_deprecated_imports.py
    python scripts/check_deprecated_imports.py --path src/
    python scripts/check_deprecated_imports.py --fix
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class DeprecatedImport:
    """過時導入資訊"""
    pattern: str
    replacement: str
    reason: str
    severity: str  # 'error', 'warning', 'info'


class DeprecatedImportChecker:
    """過時導入檢查器"""
    
    def __init__(self):
        self.deprecated_imports = self._load_deprecated_patterns()
        self.issues_found = []
        
    def _load_deprecated_patterns(self) -> List[DeprecatedImport]:
        """載入過時導入模式"""
        return [
            # UI 模組
            DeprecatedImport(
                pattern=r'from\s+src\.ui\.web_ui_production_legacy\s+import',
                replacement='from src.ui.web_ui_production import',
                reason='web_ui_production_legacy.py 已過時，請使用 web_ui_production.py',
                severity='error'
            ),
            
            # 配置管理
            DeprecatedImport(
                pattern=r'from\s+src\.core\.config_manager\s+import',
                replacement='from src.utils.config_manager import create_default_config_manager',
                reason='src.core.config_manager 已過時，請使用 src.utils.config_manager',
                severity='error'
            ),
            
            # 風險管理
            DeprecatedImport(
                pattern=r'from\s+src\.core\.risk_control\s+import',
                replacement='from src.risk_management.risk_manager_refactored import',
                reason='src.core.risk_control 已過時，請使用模組化的 src.risk_management.*',
                severity='error'
            ),
            
            # IB 適配器（排除向後相容的 try-except 塊）
            DeprecatedImport(
                pattern=r'^\s*from\s+src\.execution\.ib_adapter\s+import\s+IBAdapter(?!\s*#.*向後相容)',
                replacement='from src.execution.ib_adapter_refactored import IBAdapterRefactored',
                reason='src.execution.ib_adapter 已過時，請使用 ib_adapter_refactored',
                severity='error'
            ),
            
            # 警告級別的檢查
            DeprecatedImport(
                pattern=r'import\s+src\.ui\.web_ui_production_legacy',
                replacement='import src.ui.web_ui_production',
                reason='建議使用主要的生產版本',
                severity='warning'
            ),
        ]
    
    def check_file(self, file_path: Path) -> List[Dict]:
        """檢查單個檔案"""
        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            # 檢查是否在 try-except 塊中（向後相容模式）
            in_backward_compat_block = False

            for line_num, line in enumerate(lines, 1):
                # 檢查是否進入向後相容塊
                if '# 向後相容' in line or 'backward compatibility' in line.lower():
                    in_backward_compat_block = True
                    continue

                # 檢查是否離開 try-except 塊
                if in_backward_compat_block and (line.strip().startswith('except') or
                                               (line.strip() and not line.startswith(' ') and not line.startswith('\t'))):
                    in_backward_compat_block = False

                # 如果在向後相容塊中，跳過檢查
                if in_backward_compat_block:
                    continue

                for deprecated in self.deprecated_imports:
                    if re.search(deprecated.pattern, line):
                        issues.append({
                            'file': str(file_path),
                            'line': line_num,
                            'content': line.strip(),
                            'pattern': deprecated.pattern,
                            'replacement': deprecated.replacement,
                            'reason': deprecated.reason,
                            'severity': deprecated.severity
                        })

        except Exception as e:
            print(f"❌ 無法讀取檔案 {file_path}: {e}")

        return issues
    
    def check_directory(self, directory: Path) -> List[Dict]:
        """檢查目錄中的所有 Python 檔案"""
        all_issues = []
        
        for py_file in directory.rglob('*.py'):
            # 跳過特定目錄
            if any(part in str(py_file) for part in ['.git', '__pycache__', '.pytest_cache']):
                continue
                
            issues = self.check_file(py_file)
            all_issues.extend(issues)
            
        return all_issues
    
    def fix_file(self, file_path: Path, issues: List[Dict]) -> bool:
        """自動修復檔案中的過時導入"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            original_content = content
            
            for issue in issues:
                if issue['severity'] == 'error':
                    # 簡單的字符串替換（可能需要更複雜的邏輯）
                    old_import = issue['content']
                    # 這裡需要更智能的替換邏輯
                    print(f"⚠️ 自動修復功能需要手動實現: {issue['file']}:{issue['line']}")
                    
            return content != original_content
            
        except Exception as e:
            print(f"❌ 修復檔案失敗 {file_path}: {e}")
            return False
    
    def generate_report(self, issues: List[Dict]) -> str:
        """生成檢查報告"""
        if not issues:
            return "✅ 沒有發現過時的模組導入"
            
        report = []
        report.append("🔍 過時模組導入檢查報告")
        report.append("=" * 50)
        
        # 按嚴重程度分組
        errors = [i for i in issues if i['severity'] == 'error']
        warnings = [i for i in issues if i['severity'] == 'warning']
        
        if errors:
            report.append(f"\n❌ 錯誤 ({len(errors)} 個):")
            for issue in errors:
                report.append(f"  📄 {issue['file']}:{issue['line']}")
                report.append(f"     當前: {issue['content']}")
                report.append(f"     建議: {issue['replacement']}")
                report.append(f"     原因: {issue['reason']}")
                report.append("")
                
        if warnings:
            report.append(f"\n⚠️ 警告 ({len(warnings)} 個):")
            for issue in warnings:
                report.append(f"  📄 {issue['file']}:{issue['line']}")
                report.append(f"     當前: {issue['content']}")
                report.append(f"     建議: {issue['replacement']}")
                report.append(f"     原因: {issue['reason']}")
                report.append("")
        
        # 統計資訊
        report.append("📊 統計資訊:")
        report.append(f"  - 總問題數: {len(issues)}")
        report.append(f"  - 錯誤: {len(errors)}")
        report.append(f"  - 警告: {len(warnings)}")
        
        # 建議行動
        if errors:
            report.append("\n🔧 建議行動:")
            report.append("  1. 修復所有錯誤級別的過時導入")
            report.append("  2. 參考 docs/檔案結構變更說明.md")
            report.append("  3. 運行測試確保修改正確")
            
        return "\n".join(report)


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='檢查過時模組導入')
    parser.add_argument('--path', default='src/', help='檢查路徑 (預設: src/)')
    parser.add_argument('--fix', action='store_true', help='自動修復問題')
    parser.add_argument('--output', help='輸出報告到檔案')
    parser.add_argument('--ci', action='store_true', help='CI 模式（錯誤時退出碼非零）')
    
    args = parser.parse_args()
    
    # 檢查路徑是否存在
    check_path = Path(args.path)
    if not check_path.exists():
        print(f"❌ 路徑不存在: {check_path}")
        sys.exit(1)
        
    # 創建檢查器
    checker = DeprecatedImportChecker()
    
    # 執行檢查
    print(f"🔍 檢查路徑: {check_path}")
    if check_path.is_file():
        issues = checker.check_file(check_path)
    else:
        issues = checker.check_directory(check_path)
    
    # 生成報告
    report = checker.generate_report(issues)
    print(report)
    
    # 輸出到檔案
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n📄 報告已保存到: {args.output}")
    
    # 自動修復
    if args.fix and issues:
        print("\n🔧 開始自動修復...")
        # 這裡需要實現自動修復邏輯
        print("⚠️ 自動修復功能尚未完全實現，請手動修復")
    
    # CI 模式處理
    if args.ci:
        errors = [i for i in issues if i['severity'] == 'error']
        if errors:
            print(f"\n❌ CI 檢查失敗: 發現 {len(errors)} 個錯誤")
            sys.exit(1)
        else:
            print("\n✅ CI 檢查通過")
            sys.exit(0)


if __name__ == '__main__':
    main()
