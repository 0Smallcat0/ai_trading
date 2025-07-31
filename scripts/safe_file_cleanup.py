#!/usr/bin/env python3
"""
安全檔案清理工具

此腳本安全地移除已標記為過時的檔案，
在移除前進行最終的依賴檢查和備份。

Usage:
    python scripts/safe_file_cleanup.py --dry-run
    python scripts/safe_file_cleanup.py --execute
    python scripts/safe_file_cleanup.py --restore backup_id
"""

import os
import shutil
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import subprocess
import sys


class SafeFileCleanup:
    """安全檔案清理器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.backup_dir = self.project_root / "file_cleanup_backups"
        self.deprecated_files = [
            "src/ui/web_ui_production_legacy.py",
            "src/core/config_manager.py",
            "src/core/risk_control.py",
            "src/execution/ib_adapter.py"
        ]
        
    def create_backup(self) -> str:
        """創建備份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_id = f"cleanup_{timestamp}"
        backup_path = self.backup_dir / backup_id
        backup_path.mkdir(parents=True, exist_ok=True)
        
        backup_info = {
            'backup_id': backup_id,
            'timestamp': timestamp,
            'files': [],
            'pyproject_backup': None
        }
        
        print(f"📦 創建備份: {backup_path}")
        
        # 備份要刪除的檔案
        for file_path in self.deprecated_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                backup_file_path = backup_path / file_path
                backup_file_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(full_path, backup_file_path)
                backup_info['files'].append(file_path)
                print(f"  ✅ 備份: {file_path}")
        
        # 備份 pyproject.toml
        pyproject_path = self.project_root / "pyproject.toml"
        if pyproject_path.exists():
            backup_pyproject = backup_path / "pyproject.toml"
            shutil.copy2(pyproject_path, backup_pyproject)
            backup_info['pyproject_backup'] = "pyproject.toml"
            print(f"  ✅ 備份: pyproject.toml")
        
        # 保存備份資訊
        info_file = backup_path / "backup_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, indent=2, ensure_ascii=False)
        
        print(f"📄 備份資訊保存到: {info_file}")
        return backup_id
    
    def final_dependency_check(self) -> Dict[str, List[str]]:
        """最終依賴檢查"""
        print("🔍 執行最終依賴檢查...")
        
        dependencies = {}
        
        for file_path in self.deprecated_files:
            dependencies[file_path] = []
            
            # 檢查 Python 檔案中的導入
            module_name = file_path.replace('/', '.').replace('.py', '')
            
            try:
                # 使用 grep 搜尋導入語句（排除備份目錄）
                result = subprocess.run([
                    'powershell', '-Command',
                    f'Select-String -Path "src\\**\\*.py","tests\\**\\*.py" -Pattern "from {module_name} import|import {module_name}" -SimpleMatch'
                ], capture_output=True, text=True, cwd=self.project_root)
                
                if result.stdout.strip():
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            dependencies[file_path].append(line.strip())
                            
            except Exception as e:
                print(f"⚠️ 檢查 {file_path} 依賴時出錯: {e}")
        
        return dependencies
    
    def check_pyproject_references(self) -> List[str]:
        """檢查 pyproject.toml 中的引用"""
        print("🔍 檢查 pyproject.toml 中的引用...")
        
        references = []
        pyproject_path = self.project_root / "pyproject.toml"
        
        if pyproject_path.exists():
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 檢查腳本入口點
            for file_path in self.deprecated_files:
                module_name = file_path.replace('/', '.').replace('.py', '')
                if module_name in content:
                    references.append(f"pyproject.toml 中引用了 {module_name}")
        
        return references
    
    def update_pyproject_toml(self) -> bool:
        """更新 pyproject.toml，移除過時檔案的入口點"""
        print("🔧 更新 pyproject.toml...")
        
        pyproject_path = self.project_root / "pyproject.toml"
        if not pyproject_path.exists():
            return True
        
        with open(pyproject_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        updated_lines = []
        skip_line = False
        
        for line in lines:
            # 檢查是否是要移除的入口點
            if 'web-legacy = "src.ui.web_ui_production_legacy:main"' in line:
                print("  ❌ 移除: web-legacy 入口點")
                skip_line = True
            elif skip_line and line.strip() == '':
                skip_line = False
                continue
            else:
                skip_line = False
                updated_lines.append(line)
        
        # 寫回檔案
        with open(pyproject_path, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)
        
        print("  ✅ pyproject.toml 更新完成")
        return True
    
    def remove_deprecated_files(self) -> bool:
        """移除過時檔案"""
        print("🗑️ 移除過時檔案...")
        
        removed_files = []
        
        for file_path in self.deprecated_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                try:
                    os.remove(full_path)
                    removed_files.append(file_path)
                    print(f"  ❌ 已移除: {file_path}")
                except Exception as e:
                    print(f"  ⚠️ 移除失敗 {file_path}: {e}")
                    return False
        
        print(f"✅ 成功移除 {len(removed_files)} 個檔案")
        return True
    
    def run_tests(self) -> bool:
        """運行測試確保系統正常"""
        print("🧪 運行測試驗證...")
        
        try:
            # 運行過時導入檢查
            result = subprocess.run([
                sys.executable, "scripts/check_deprecated_imports.py", "--path", "src/", "--ci"
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                print("  ✅ 過時導入檢查通過")
            else:
                print(f"  ❌ 過時導入檢查失敗: {result.stdout}")
                return False
            
            # 測試關鍵模組導入
            test_imports = [
                "from src.ui.web_ui_production import main",
                "from src.utils.config_manager import create_default_config_manager",
                "from src.execution.ib_adapter_refactored import IBAdapterRefactored"
            ]
            
            for import_stmt in test_imports:
                result = subprocess.run([
                    sys.executable, "-c", f"import sys; sys.path.insert(0, '.'); {import_stmt}; print('✅ 導入成功')"
                ], capture_output=True, text=True, cwd=self.project_root)
                
                if result.returncode == 0:
                    print(f"  ✅ {import_stmt}")
                else:
                    print(f"  ❌ {import_stmt} 失敗: {result.stderr}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"❌ 測試執行失敗: {e}")
            return False
    
    def restore_backup(self, backup_id: str) -> bool:
        """恢復備份"""
        backup_path = self.backup_dir / backup_id
        
        if not backup_path.exists():
            print(f"❌ 備份不存在: {backup_id}")
            return False
        
        info_file = backup_path / "backup_info.json"
        if not info_file.exists():
            print(f"❌ 備份資訊檔案不存在: {info_file}")
            return False
        
        with open(info_file, 'r', encoding='utf-8') as f:
            backup_info = json.load(f)
        
        print(f"🔄 恢復備份: {backup_id}")
        
        # 恢復檔案
        for file_path in backup_info['files']:
            backup_file = backup_path / file_path
            target_file = self.project_root / file_path
            
            if backup_file.exists():
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_file, target_file)
                print(f"  ✅ 恢復: {file_path}")
        
        # 恢復 pyproject.toml
        if backup_info['pyproject_backup']:
            backup_pyproject = backup_path / backup_info['pyproject_backup']
            target_pyproject = self.project_root / "pyproject.toml"
            
            if backup_pyproject.exists():
                shutil.copy2(backup_pyproject, target_pyproject)
                print(f"  ✅ 恢復: pyproject.toml")
        
        print("✅ 備份恢復完成")
        return True
    
    def dry_run(self):
        """乾運行，顯示將要執行的操作"""
        print("🔍 乾運行模式 - 檢查將要執行的操作")
        print("=" * 50)
        
        # 檢查依賴
        dependencies = self.final_dependency_check()
        pyproject_refs = self.check_pyproject_references()
        
        print("\n📋 將要移除的檔案:")
        for file_path in self.deprecated_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                print(f"  ❌ {file_path}")
                
                # 顯示依賴情況
                if dependencies.get(file_path):
                    print(f"    ⚠️ 發現依賴:")
                    for dep in dependencies[file_path][:3]:  # 只顯示前3個
                        print(f"      - {dep}")
                    if len(dependencies[file_path]) > 3:
                        print(f"      - ... 還有 {len(dependencies[file_path]) - 3} 個")
                else:
                    print(f"    ✅ 無依賴")
            else:
                print(f"  ⚠️ {file_path} (檔案不存在)")
        
        print("\n📋 pyproject.toml 更新:")
        if pyproject_refs:
            for ref in pyproject_refs:
                print(f"  🔧 {ref}")
        else:
            print("  ✅ 無需更新")
        
        # 安全性評估
        print("\n🛡️ 安全性評估:")
        total_deps = sum(len(deps) for deps in dependencies.values())
        if total_deps == 0:
            print("  ✅ 安全：沒有發現依賴關係")
        else:
            print(f"  ⚠️ 警告：發現 {total_deps} 個依賴關係")
            print("  建議：檢查這些依賴是否為向後相容的導入")
    
    def execute(self):
        """執行清理操作"""
        print("🚀 執行檔案清理操作")
        print("=" * 50)
        
        # 創建備份
        backup_id = self.create_backup()
        
        try:
            # 最終依賴檢查
            dependencies = self.final_dependency_check()
            total_deps = sum(len(deps) for deps in dependencies.values())
            
            if total_deps > 0:
                print(f"⚠️ 發現 {total_deps} 個依賴關係")
                response = input("是否繼續？這些可能是向後相容的導入 (y/N): ")
                if response.lower() != 'y':
                    print("❌ 操作已取消")
                    return False
            
            # 更新 pyproject.toml
            if not self.update_pyproject_toml():
                print("❌ 更新 pyproject.toml 失敗")
                return False
            
            # 移除過時檔案
            if not self.remove_deprecated_files():
                print("❌ 移除檔案失敗")
                return False
            
            # 運行測試
            if not self.run_tests():
                print("❌ 測試失敗，正在恢復備份...")
                self.restore_backup(backup_id)
                return False
            
            print(f"✅ 檔案清理完成！備份ID: {backup_id}")
            return True
            
        except Exception as e:
            print(f"❌ 清理過程中出錯: {e}")
            print("正在恢復備份...")
            self.restore_backup(backup_id)
            return False


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='安全檔案清理工具')
    parser.add_argument('--dry-run', action='store_true', help='乾運行，不執行實際操作')
    parser.add_argument('--execute', action='store_true', help='執行清理操作')
    parser.add_argument('--restore', help='恢復指定的備份')
    
    args = parser.parse_args()
    
    cleanup = SafeFileCleanup()
    
    if args.restore:
        cleanup.restore_backup(args.restore)
    elif args.dry_run:
        cleanup.dry_run()
    elif args.execute:
        cleanup.execute()
    else:
        print("請指定操作模式:")
        print("  --dry-run    乾運行模式")
        print("  --execute    執行清理")
        print("  --restore ID 恢復備份")


if __name__ == '__main__':
    main()
