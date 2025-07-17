#!/usr/bin/env python3
"""
檔案重複防護工具

此腳本作為 Git pre-commit hook 運行，檢測並防止檔案重複、
過時模組使用和結構問題。

Usage:
    python scripts/prevent_file_duplication.py
    python scripts/prevent_file_duplication.py --install-hook
    python scripts/prevent_file_duplication.py --check-commit
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Set
import hashlib
import re


class DuplicationPreventer:
    """檔案重複防護器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.issues = []
        
    def get_staged_files(self) -> List[str]:
        """獲取暫存的檔案"""
        try:
            result = subprocess.run(
                ['git', 'diff', '--cached', '--name-only', '--diff-filter=A'],
                capture_output=True, text=True, cwd=self.project_root
            )
            if result.returncode == 0:
                return [f for f in result.stdout.strip().split('\n') if f.endswith('.py')]
            return []
        except Exception:
            return []
    
    def check_deprecated_imports(self, file_path: str) -> List[Dict[str, Any]]:
        """檢查過時導入"""
        issues = []
        
        deprecated_patterns = [
            (r'from\s+src\.ui\.web_ui_production_legacy\s+import', 'UI模組已過時'),
            (r'from\s+src\.core\.config_manager\s+import', '配置管理模組已過時'),
            (r'from\s+src\.core\.risk_control\s+import', '風險管理模組已過時'),
            (r'from\s+src\.execution\.ib_adapter\s+import\s+IBAdapter(?!\s*#.*向後相容)', 'IB適配器已過時'),
        ]
        
        try:
            full_path = self.project_root / file_path
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
            for line_num, line in enumerate(lines, 1):
                for pattern, message in deprecated_patterns:
                    if re.search(pattern, line):
                        issues.append({
                            'type': 'deprecated_import',
                            'file': file_path,
                            'line': line_num,
                            'message': message,
                            'content': line.strip()
                        })
                        
        except Exception as e:
            issues.append({
                'type': 'file_error',
                'file': file_path,
                'message': f'無法讀取檔案: {e}'
            })
            
        return issues
    
    def check_file_naming(self, file_path: str) -> List[Dict[str, Any]]:
        """檢查檔案命名規範"""
        issues = []
        
        file_name = Path(file_path).stem
        
        # 檢查 snake_case
        if not re.match(r'^[a-z][a-z0-9_]*$', file_name) and file_name != '__init__':
            issues.append({
                'type': 'naming_violation',
                'file': file_path,
                'message': f'檔案名稱不符合 snake_case 規範: {file_name}'
            })
        
        # 檢查可疑命名模式
        suspicious_patterns = [
            (r'.*_legacy$', '包含 legacy 後綴'),
            (r'.*_old$', '包含 old 後綴'),
            (r'.*_backup$', '包含 backup 後綴'),
            (r'.*_temp$', '包含 temp 後綴'),
            (r'.*_test$', '測試檔案應在 tests/ 目錄'),
            (r'.*_debug$', '包含 debug 後綴')
        ]
        
        for pattern, message in suspicious_patterns:
            if re.match(pattern, file_name):
                issues.append({
                    'type': 'suspicious_naming',
                    'file': file_path,
                    'message': message
                })
        
        return issues
    
    def check_file_size(self, file_path: str) -> List[Dict[str, Any]]:
        """檢查檔案大小"""
        issues = []
        max_lines = 300
        
        try:
            full_path = self.project_root / file_path
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                line_count = len(lines)
                
            if line_count > max_lines:
                severity = 'error' if line_count > max_lines * 2 else 'warning'
                issues.append({
                    'type': 'file_too_large',
                    'file': file_path,
                    'message': f'檔案過大: {line_count} 行 (限制: {max_lines} 行)',
                    'severity': severity,
                    'lines': line_count
                })
                
        except Exception as e:
            issues.append({
                'type': 'file_error',
                'file': file_path,
                'message': f'無法檢查檔案大小: {e}'
            })
            
        return issues
    
    def check_duplicate_content(self, staged_files: List[str]) -> List[Dict[str, Any]]:
        """檢查重複內容"""
        issues = []
        file_hashes = {}
        
        for file_path in staged_files:
            try:
                full_path = self.project_root / file_path
                with open(full_path, 'rb') as f:
                    content_hash = hashlib.md5(f.read()).hexdigest()
                    
                if content_hash in file_hashes:
                    issues.append({
                        'type': 'duplicate_content',
                        'file': file_path,
                        'message': f'檔案內容與 {file_hashes[content_hash]} 重複',
                        'duplicate_of': file_hashes[content_hash]
                    })
                else:
                    file_hashes[content_hash] = file_path
                    
            except Exception as e:
                issues.append({
                    'type': 'file_error',
                    'file': file_path,
                    'message': f'無法檢查重複內容: {e}'
                })
        
        return issues
    
    def check_directory_structure(self, file_path: str) -> List[Dict[str, Any]]:
        """檢查目錄結構規範"""
        issues = []
        
        # 定義允許的目錄結構
        allowed_patterns = [
            r'^src/',
            r'^tests/',
            r'^docs/',
            r'^scripts/',
            r'^config/',
            r'^examples/',
            r'^[^/]+\.py$'  # 根目錄的 Python 檔案
        ]
        
        # 檢查是否符合允許的模式
        if not any(re.match(pattern, file_path) for pattern in allowed_patterns):
            issues.append({
                'type': 'structure_violation',
                'file': file_path,
                'message': '檔案位置不符合專案結構規範'
            })
        
        # 檢查特定目錄的檔案類型
        if file_path.startswith('src/') and file_path.endswith('_test.py'):
            issues.append({
                'type': 'misplaced_test',
                'file': file_path,
                'message': '測試檔案應放在 tests/ 目錄中'
            })
        
        return issues
    
    def run_checks(self) -> bool:
        """運行所有檢查"""
        print("🔍 檢查暫存的檔案...")
        
        staged_files = self.get_staged_files()
        if not staged_files:
            print("✅ 沒有暫存的 Python 檔案")
            return True
        
        print(f"📄 檢查 {len(staged_files)} 個檔案...")
        
        all_issues = []
        
        # 檢查重複內容
        all_issues.extend(self.check_duplicate_content(staged_files))
        
        # 檢查每個檔案
        for file_path in staged_files:
            all_issues.extend(self.check_deprecated_imports(file_path))
            all_issues.extend(self.check_file_naming(file_path))
            all_issues.extend(self.check_file_size(file_path))
            all_issues.extend(self.check_directory_structure(file_path))
        
        # 分類問題
        errors = [issue for issue in all_issues if issue.get('severity') == 'error' or issue['type'] in ['deprecated_import', 'duplicate_content']]
        warnings = [issue for issue in all_issues if issue.get('severity') == 'warning' or issue['type'] in ['suspicious_naming', 'structure_violation']]
        
        # 顯示結果
        if errors:
            print(f"\n❌ 發現 {len(errors)} 個錯誤:")
            for error in errors:
                print(f"  📄 {error['file']}: {error['message']}")
                if 'content' in error:
                    print(f"     內容: {error['content']}")
        
        if warnings:
            print(f"\n⚠️ 發現 {len(warnings)} 個警告:")
            for warning in warnings:
                print(f"  📄 {warning['file']}: {warning['message']}")
        
        if not errors and not warnings:
            print("✅ 所有檢查通過")
            return True
        
        if errors:
            print(f"\n🚫 提交被拒絕：發現 {len(errors)} 個錯誤")
            print("請修復錯誤後重新提交")
            return False
        
        if warnings:
            print(f"\n⚠️ 發現 {len(warnings)} 個警告，但允許提交")
            print("建議修復這些警告以提高代碼品質")
        
        return True
    
    def install_git_hook(self) -> bool:
        """安裝 Git pre-commit hook"""
        hooks_dir = self.project_root / '.git' / 'hooks'
        hook_file = hooks_dir / 'pre-commit'
        
        if not hooks_dir.exists():
            print("❌ Git hooks 目錄不存在")
            return False
        
        hook_content = f'''#!/bin/sh
# AI Trading System - File Duplication Prevention Hook
# Auto-generated by prevent_file_duplication.py

python "{Path(__file__).absolute()}" --check-commit
exit $?
'''
        
        try:
            with open(hook_file, 'w', encoding='utf-8') as f:
                f.write(hook_content)
            
            # 設置執行權限 (Unix/Linux)
            if os.name != 'nt':
                os.chmod(hook_file, 0o755)
            
            print(f"✅ Git pre-commit hook 已安裝: {hook_file}")
            return True
            
        except Exception as e:
            print(f"❌ 安裝 Git hook 失敗: {e}")
            return False
    
    def generate_prevention_config(self) -> Dict[str, Any]:
        """生成防護配置"""
        return {
            'version': '1.0',
            'rules': {
                'deprecated_imports': {
                    'enabled': True,
                    'patterns': [
                        'src.ui.web_ui_production_legacy',
                        'src.core.config_manager',
                        'src.core.risk_control',
                        'src.execution.ib_adapter'
                    ]
                },
                'file_naming': {
                    'enabled': True,
                    'require_snake_case': True,
                    'forbidden_suffixes': ['_legacy', '_old', '_backup', '_temp', '_debug']
                },
                'file_size': {
                    'enabled': True,
                    'max_lines': 300,
                    'error_threshold': 600
                },
                'duplicate_detection': {
                    'enabled': True,
                    'check_content_hash': True
                },
                'directory_structure': {
                    'enabled': True,
                    'enforce_structure': True
                }
            },
            'exclusions': {
                'directories': ['.git', '__pycache__', '.pytest_cache', '.venv'],
                'files': ['__init__.py']
            }
        }


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='檔案重複防護工具')
    parser.add_argument('--install-hook', action='store_true', help='安裝 Git pre-commit hook')
    parser.add_argument('--check-commit', action='store_true', help='檢查提交（用於 Git hook）')
    parser.add_argument('--config', help='生成配置檔案')
    
    args = parser.parse_args()
    
    preventer = DuplicationPreventer()
    
    if args.install_hook:
        success = preventer.install_git_hook()
        sys.exit(0 if success else 1)
    
    elif args.check_commit:
        success = preventer.run_checks()
        sys.exit(0 if success else 1)
    
    elif args.config:
        config = preventer.generate_prevention_config()
        with open(args.config, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"📄 配置檔案已生成: {args.config}")
    
    else:
        # 預設運行檢查
        success = preventer.run_checks()
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
