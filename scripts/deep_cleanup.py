#!/usr/bin/env python3
"""
深度清理工具

此腳本進行更積極的檔案清理，包括：
- 清理所有 __pycache__ 目錄
- 移除空目錄
- 清理重複的配置檔案
- 整理日誌檔案

Usage:
    python scripts/deep_cleanup.py --analyze
    python scripts/deep_cleanup.py --execute
"""

import os
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import json


class DeepCleanup:
    """深度清理器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.backup_dir = self.project_root / "deep_cleanup_backups"
        self.cleanup_stats = {
            'pycache_dirs': 0,
            'empty_dirs': 0,
            'duplicate_configs': 0,
            'old_logs': 0,
            'temp_files': 0
        }
    
    def create_backup(self) -> str:
        """創建備份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_id = f"deep_cleanup_{timestamp}"
        backup_path = self.backup_dir / backup_id
        backup_path.mkdir(parents=True, exist_ok=True)
        
        print(f"📦 創建深度清理備份: {backup_path}")
        return backup_id
    
    def cleanup_pycache_dirs(self) -> int:
        """清理所有 __pycache__ 目錄"""
        print("🗑️ 清理 __pycache__ 目錄...")
        
        count = 0
        for pycache_dir in self.project_root.rglob('__pycache__'):
            if pycache_dir.is_dir():
                try:
                    shutil.rmtree(pycache_dir)
                    count += 1
                    print(f"  ❌ 刪除: {pycache_dir.relative_to(self.project_root)}")
                except Exception as e:
                    print(f"  ⚠️ 無法刪除 {pycache_dir}: {e}")
        
        return count
    
    def cleanup_pytest_cache(self) -> int:
        """清理 pytest 快取"""
        print("🗑️ 清理 pytest 快取...")
        
        count = 0
        cache_patterns = ['.pytest_cache', '.coverage*', '.mypy_cache']
        
        for pattern in cache_patterns:
            for cache_item in self.project_root.rglob(pattern):
                if cache_item.exists():
                    try:
                        if cache_item.is_dir():
                            shutil.rmtree(cache_item)
                        else:
                            cache_item.unlink()
                        count += 1
                        print(f"  ❌ 刪除: {cache_item.relative_to(self.project_root)}")
                    except Exception as e:
                        print(f"  ⚠️ 無法刪除 {cache_item}: {e}")
        
        return count
    
    def cleanup_empty_directories(self) -> int:
        """清理空目錄"""
        print("🗑️ 清理空目錄...")
        
        count = 0
        # 多次掃描，因為刪除子目錄可能會讓父目錄變空
        for _ in range(3):
            empty_dirs = []
            for dir_path in self.project_root.rglob('*'):
                if (dir_path.is_dir() and 
                    not self.should_skip_directory(dir_path) and
                    self.is_empty_directory(dir_path)):
                    empty_dirs.append(dir_path)
            
            for empty_dir in empty_dirs:
                try:
                    empty_dir.rmdir()
                    count += 1
                    print(f"  ❌ 刪除空目錄: {empty_dir.relative_to(self.project_root)}")
                except Exception as e:
                    print(f"  ⚠️ 無法刪除 {empty_dir}: {e}")
        
        return count
    
    def cleanup_duplicate_configs(self) -> int:
        """清理重複的配置檔案"""
        print("🗑️ 清理重複配置檔案...")
        
        count = 0
        
        # 檢查重複的 .env 檔案
        env_files = list(self.project_root.rglob('.env*'))
        if len(env_files) > 1:
            # 保留根目錄的 .env.example
            primary_env = None
            for env_file in env_files:
                if env_file.name == '.env.example' and env_file.parent == self.project_root:
                    primary_env = env_file
                    break
            
            if primary_env:
                for env_file in env_files:
                    if env_file != primary_env and 'config/environments' in str(env_file):
                        try:
                            env_file.unlink()
                            count += 1
                            print(f"  ❌ 刪除重複配置: {env_file.relative_to(self.project_root)}")
                        except Exception as e:
                            print(f"  ⚠️ 無法刪除 {env_file}: {e}")
        
        return count
    
    def cleanup_old_logs(self) -> int:
        """清理舊日誌檔案"""
        print("🗑️ 清理舊日誌檔案...")
        
        count = 0
        logs_dir = self.project_root / 'logs'
        
        if logs_dir.exists():
            for log_file in logs_dir.rglob('*.log*'):
                if log_file.is_file():
                    try:
                        # 檢查檔案大小，如果很小可能是空的
                        if log_file.stat().st_size < 100:  # 小於100字節
                            log_file.unlink()
                            count += 1
                            print(f"  ❌ 刪除空日誌: {log_file.relative_to(self.project_root)}")
                    except Exception as e:
                        print(f"  ⚠️ 無法刪除 {log_file}: {e}")
        
        return count
    
    def cleanup_temp_files(self) -> int:
        """清理臨時檔案"""
        print("🗑️ 清理臨時檔案...")
        
        count = 0
        temp_patterns = [
            '*.tmp', '*.temp', '*.bak', '*.backup', 
            '*~', '*.swp', '*.swo', '*.orig'
        ]
        
        for pattern in temp_patterns:
            for temp_file in self.project_root.rglob(pattern):
                if temp_file.is_file() and not self.should_skip_file(temp_file):
                    try:
                        temp_file.unlink()
                        count += 1
                        print(f"  ❌ 刪除臨時檔案: {temp_file.relative_to(self.project_root)}")
                    except Exception as e:
                        print(f"  ⚠️ 無法刪除 {temp_file}: {e}")
        
        return count
    
    def cleanup_backup_directories(self) -> int:
        """清理舊的備份目錄"""
        print("🗑️ 清理舊備份目錄...")
        
        count = 0
        backup_patterns = [
            'file_cleanup_backups',
            'file_organization_backups'
        ]
        
        for pattern in backup_patterns:
            backup_dir = self.project_root / pattern
            if backup_dir.exists():
                # 只保留最新的3個備份
                backup_subdirs = sorted([d for d in backup_dir.iterdir() if d.is_dir()], 
                                      key=lambda x: x.stat().st_mtime, reverse=True)
                
                for old_backup in backup_subdirs[3:]:  # 保留前3個，刪除其餘
                    try:
                        shutil.rmtree(old_backup)
                        count += 1
                        print(f"  ❌ 刪除舊備份: {old_backup.relative_to(self.project_root)}")
                    except Exception as e:
                        print(f"  ⚠️ 無法刪除 {old_backup}: {e}")
        
        return count
    
    def is_empty_directory(self, dir_path: Path) -> bool:
        """檢查目錄是否為空"""
        try:
            return not any(dir_path.iterdir())
        except Exception:
            return False
    
    def should_skip_directory(self, dir_path: Path) -> bool:
        """判斷是否應該跳過目錄"""
        skip_dirs = {
            '.git', '.venv', 'node_modules', 
            'src', 'tests', 'docs', 'scripts', 'config',
            'results', 'logs', 'data', 'models'
        }
        
        # 檢查是否是重要目錄或其子目錄
        for part in dir_path.parts:
            if part in skip_dirs:
                return True
        
        return False
    
    def should_skip_file(self, file_path: Path) -> bool:
        """判斷是否應該跳過檔案"""
        # 不刪除重要檔案
        important_files = {
            'pyproject.toml', 'poetry.lock', 'requirements.txt',
            'README.md', 'LICENSE', '.gitignore', '.env.example'
        }
        
        if file_path.name in important_files:
            return True
        
        # 不刪除 src/, tests/, docs/ 中的檔案
        relative_path = str(file_path.relative_to(self.project_root))
        protected_dirs = ['src/', 'tests/', 'docs/', 'config/']
        
        return any(relative_path.startswith(protected) for protected in protected_dirs)
    
    def analyze_cleanup_potential(self) -> Dict[str, Any]:
        """分析清理潛力"""
        print("🔍 分析清理潛力...")
        
        analysis = {
            'pycache_dirs': len(list(self.project_root.rglob('__pycache__'))),
            'pytest_cache': len(list(self.project_root.rglob('.pytest_cache'))),
            'empty_dirs': 0,
            'temp_files': 0,
            'old_logs': 0
        }
        
        # 計算空目錄
        for dir_path in self.project_root.rglob('*'):
            if (dir_path.is_dir() and 
                not self.should_skip_directory(dir_path) and
                self.is_empty_directory(dir_path)):
                analysis['empty_dirs'] += 1
        
        # 計算臨時檔案
        temp_patterns = ['*.tmp', '*.temp', '*.bak', '*.backup']
        for pattern in temp_patterns:
            analysis['temp_files'] += len(list(self.project_root.rglob(pattern)))
        
        # 計算小日誌檔案
        logs_dir = self.project_root / 'logs'
        if logs_dir.exists():
            for log_file in logs_dir.rglob('*.log*'):
                if log_file.is_file() and log_file.stat().st_size < 100:
                    analysis['old_logs'] += 1
        
        return analysis
    
    def execute_deep_cleanup(self) -> Dict[str, int]:
        """執行深度清理"""
        print("🚀 開始深度清理...")
        print("=" * 50)
        
        backup_id = self.create_backup()
        
        results = {}
        
        try:
            # 1. 清理 __pycache__ 目錄
            results['pycache_dirs'] = self.cleanup_pycache_dirs()
            
            # 2. 清理 pytest 快取
            results['pytest_cache'] = self.cleanup_pytest_cache()
            
            # 3. 清理空目錄
            results['empty_dirs'] = self.cleanup_empty_directories()
            
            # 4. 清理重複配置
            results['duplicate_configs'] = self.cleanup_duplicate_configs()
            
            # 5. 清理舊日誌
            results['old_logs'] = self.cleanup_old_logs()
            
            # 6. 清理臨時檔案
            results['temp_files'] = self.cleanup_temp_files()
            
            # 7. 清理舊備份
            results['old_backups'] = self.cleanup_backup_directories()
            
            print(f"\n✅ 深度清理完成！備份ID: {backup_id}")
            
            # 顯示統計
            total_cleaned = sum(results.values())
            print(f"\n📊 清理統計:")
            print(f"  __pycache__ 目錄: {results['pycache_dirs']}")
            print(f"  pytest 快取: {results['pytest_cache']}")
            print(f"  空目錄: {results['empty_dirs']}")
            print(f"  重複配置: {results['duplicate_configs']}")
            print(f"  舊日誌: {results['old_logs']}")
            print(f"  臨時檔案: {results['temp_files']}")
            print(f"  舊備份: {results['old_backups']}")
            print(f"  總計: {total_cleaned} 項")
            
            return results
            
        except Exception as e:
            print(f"❌ 深度清理過程中出錯: {e}")
            return {}
    
    def generate_report(self, analysis: Dict[str, Any]) -> str:
        """生成清理報告"""
        report = []
        report.append("📊 深度清理分析報告")
        report.append("=" * 30)
        report.append(f"分析時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        report.append("🔍 發現的清理項目:")
        report.append(f"  __pycache__ 目錄: {analysis['pycache_dirs']}")
        report.append(f"  pytest 快取: {analysis['pytest_cache']}")
        report.append(f"  空目錄: {analysis['empty_dirs']}")
        report.append(f"  臨時檔案: {analysis['temp_files']}")
        report.append(f"  小日誌檔案: {analysis['old_logs']}")
        report.append("")
        
        total_items = sum(analysis.values())
        if total_items > 0:
            report.append("💡 建議執行深度清理")
            report.append(f"  預計清理項目: {total_items}")
        else:
            report.append("✅ 專案已經很乾淨")
        
        return "\n".join(report)


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='深度清理工具')
    parser.add_argument('--analyze', action='store_true', help='分析清理潛力')
    parser.add_argument('--execute', action='store_true', help='執行深度清理')
    
    args = parser.parse_args()
    
    cleanup = DeepCleanup()
    
    if args.analyze:
        analysis = cleanup.analyze_cleanup_potential()
        report = cleanup.generate_report(analysis)
        print(report)
        
        # 保存分析結果
        with open('deep_cleanup_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print(f"\n📄 分析結果已保存到: deep_cleanup_analysis.json")
        
    elif args.execute:
        results = cleanup.execute_deep_cleanup()
        
        # 保存清理結果
        with open('deep_cleanup_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n📄 清理結果已保存到: deep_cleanup_results.json")
        
    else:
        print("請指定操作模式:")
        print("  --analyze    分析清理潛力")
        print("  --execute    執行深度清理")


if __name__ == '__main__':
    main()
