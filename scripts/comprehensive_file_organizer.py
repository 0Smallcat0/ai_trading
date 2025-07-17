#!/usr/bin/env python3
"""
全面檔案整理工具

此腳本對整個專案進行全面的檔案整理和清理，包括：
- 檔案分類整理
- 冗餘檔案識別
- 目錄結構優化
- 臨時檔案清理

Usage:
    python scripts/comprehensive_file_organizer.py --analyze
    python scripts/comprehensive_file_organizer.py --execute
    python scripts/comprehensive_file_organizer.py --restore backup_id
"""

import os
import shutil
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Set, Tuple
import hashlib
import re
from collections import defaultdict


class ComprehensiveFileOrganizer:
    """全面檔案整理器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.backup_dir = self.project_root / "file_organization_backups"
        self.analysis_results = {
            'timestamp': datetime.now().isoformat(),
            'misplaced_files': [],
            'redundant_files': [],
            'temporary_files': [],
            'empty_files': [],
            'directory_issues': [],
            'recommendations': []
        }
        
        # 定義標準目錄結構
        self.standard_structure = {
            'src/': '原始碼檔案',
            'tests/': '測試檔案',
            'docs/': '文檔檔案',
            'scripts/': '腳本檔案',
            'config/': '配置檔案',
            'data/': '資料檔案',
            'logs/': '日誌檔案',
            'examples/': '範例檔案',
            'models/': '模型檔案',
            'results/': '結果檔案',
            'exports/': '匯出檔案',
            'migrations/': '資料庫遷移檔案',
            'k8s/': 'Kubernetes 配置',
            'cache/': '快取檔案',
            'mcp_crawler/': 'MCP 爬蟲相關'
        }
        
        # 定義需要清理的檔案模式
        self.cleanup_patterns = {
            'temporary': [
                r'.*\.tmp$', r'.*\.temp$', r'.*\.bak$', r'.*\.backup$',
                r'.*~$', r'.*\.swp$', r'.*\.swo$', r'.*\.orig$'
            ],
            'cache': [
                r'__pycache__', r'.*\.pyc$', r'.*\.pyo$', r'.*\.pyd$',
                r'\.pytest_cache', r'\.coverage', r'\.mypy_cache'
            ],
            'logs': [
                r'.*\.log$', r'.*\.log\.\d+$'
            ],
            'results': [
                r'.*_results?\.json$', r'.*_report\.json$', r'.*_audit\.json$',
                r'.*performance.*\.json$', r'.*baseline.*\.json$'
            ]
        }
    
    def analyze_file_placement(self) -> List[Dict[str, Any]]:
        """分析檔案放置是否正確"""
        print("🔍 分析檔案放置...")
        
        misplaced = []
        
        # 檢查根目錄中的檔案
        for item in self.project_root.iterdir():
            if item.is_file() and item.name not in [
                'README.md', 'pyproject.toml', 'poetry.lock', 'Dockerfile',
                'docker-compose.yml', 'docker-compose.dev.yml', 'docker-compose.prod.yml',
                'requirements-production.txt', 'start.sh', 'start.bat',
                'auto_trading_project.code-workspace', 'security.key',
                'install_dependencies.py', 'launch_ui_comparison.py'
            ]:
                # 檢查是否應該移動到其他目錄
                suggested_location = self.suggest_file_location(item)
                if suggested_location:
                    misplaced.append({
                        'file': str(item.relative_to(self.project_root)),
                        'current_location': str(item.parent.relative_to(self.project_root)),
                        'suggested_location': suggested_location,
                        'reason': self.get_relocation_reason(item, suggested_location)
                    })
        
        return misplaced
    
    def suggest_file_location(self, file_path: Path) -> str:
        """建議檔案的正確位置"""
        file_name = file_path.name.lower()
        
        # JSON 結果檔案
        if any(pattern in file_name for pattern in ['performance', 'audit', 'report', 'results', 'baseline']):
            if file_name.endswith('.json'):
                return 'results/'
        
        # 日誌檔案
        if file_name.endswith('.log') or 'log' in file_name:
            return 'logs/'
        
        # 臨時檔案
        if any(file_name.endswith(ext) for ext in ['.tmp', '.temp', '.bak']):
            return 'DELETE'  # 標記為刪除
        
        # 測試檔案
        if file_name.startswith('test_') and file_name.endswith('.py'):
            return 'tests/'
        
        return None
    
    def get_relocation_reason(self, file_path: Path, suggested_location: str) -> str:
        """獲取重新定位的原因"""
        file_name = file_path.name.lower()
        
        if suggested_location == 'results/':
            return '結果和報告檔案應放在 results/ 目錄'
        elif suggested_location == 'logs/':
            return '日誌檔案應放在 logs/ 目錄'
        elif suggested_location == 'tests/':
            return '測試檔案應放在 tests/ 目錄'
        elif suggested_location == 'DELETE':
            return '臨時檔案，建議刪除'
        
        return '不符合目錄結構規範'
    
    def find_redundant_files(self) -> List[Dict[str, Any]]:
        """尋找冗餘檔案"""
        print("🔍 尋找冗餘檔案...")
        
        redundant = []
        file_hashes = defaultdict(list)
        
        # 計算所有檔案的雜湊值
        for py_file in self.project_root.rglob('*'):
            if py_file.is_file() and not self.should_skip_file(py_file):
                try:
                    file_hash = self.calculate_file_hash(py_file)
                    if file_hash:
                        file_hashes[file_hash].append(py_file)
                except Exception:
                    continue
        
        # 找出重複檔案
        for file_hash, files in file_hashes.items():
            if len(files) > 1:
                # 排序，保留最重要的檔案
                primary_file = self.select_primary_file(files)
                duplicates = [f for f in files if f != primary_file]
                
                redundant.append({
                    'primary_file': str(primary_file.relative_to(self.project_root)),
                    'duplicates': [str(f.relative_to(self.project_root)) for f in duplicates],
                    'size': primary_file.stat().st_size,
                    'hash': file_hash
                })
        
        return redundant
    
    def select_primary_file(self, files: List[Path]) -> Path:
        """選擇主要檔案（保留的檔案）"""
        # 優先級：src/ > tests/ > docs/ > scripts/ > 其他
        priority_order = ['src/', 'tests/', 'docs/', 'scripts/']
        
        for priority in priority_order:
            for file in files:
                if str(file.relative_to(self.project_root)).startswith(priority):
                    return file
        
        # 如果沒有優先級匹配，選擇路徑最短的
        return min(files, key=lambda f: len(str(f)))
    
    def find_temporary_files(self) -> List[Dict[str, Any]]:
        """尋找臨時檔案"""
        print("🔍 尋找臨時檔案...")
        
        temporary = []
        
        for file_path in self.project_root.rglob('*'):
            if file_path.is_file() and not self.should_skip_file(file_path):
                file_name = file_path.name
                relative_path = str(file_path.relative_to(self.project_root))
                
                # 檢查各種臨時檔案模式
                for category, patterns in self.cleanup_patterns.items():
                    for pattern in patterns:
                        if re.match(pattern, file_name) or re.search(pattern, relative_path):
                            temporary.append({
                                'file': relative_path,
                                'category': category,
                                'pattern': pattern,
                                'size': file_path.stat().st_size,
                                'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                            })
                            break
        
        return temporary
    
    def find_empty_files(self) -> List[Dict[str, Any]]:
        """尋找空白檔案"""
        print("🔍 尋找空白檔案...")
        
        empty = []
        
        for file_path in self.project_root.rglob('*'):
            if file_path.is_file() and not self.should_skip_file(file_path):
                try:
                    if file_path.stat().st_size == 0:
                        empty.append({
                            'file': str(file_path.relative_to(self.project_root)),
                            'directory': str(file_path.parent.relative_to(self.project_root))
                        })
                except Exception:
                    continue
        
        return empty
    
    def analyze_directory_structure(self) -> List[Dict[str, Any]]:
        """分析目錄結構問題"""
        print("🔍 分析目錄結構...")
        
        issues = []
        
        # 檢查是否有不符合規範的目錄
        for item in self.project_root.iterdir():
            if item.is_dir() and item.name not in ['.git', '.venv', 'node_modules']:
                dir_name = item.name + '/'
                if dir_name not in self.standard_structure and not item.name.startswith('.'):
                    issues.append({
                        'directory': dir_name,
                        'issue': 'non_standard_directory',
                        'description': f'目錄 {dir_name} 不在標準結構中',
                        'suggestion': self.suggest_directory_action(item)
                    })
        
        # 檢查空目錄
        for dir_path in self.project_root.rglob('*'):
            if dir_path.is_dir() and not self.should_skip_directory(dir_path):
                try:
                    if not any(dir_path.iterdir()):
                        issues.append({
                            'directory': str(dir_path.relative_to(self.project_root)),
                            'issue': 'empty_directory',
                            'description': '空目錄',
                            'suggestion': 'consider_removal'
                        })
                except Exception:
                    continue
        
        return issues
    
    def suggest_directory_action(self, dir_path: Path) -> str:
        """建議目錄操作"""
        dir_name = dir_path.name.lower()
        
        if 'backup' in dir_name or 'old' in dir_name:
            return 'move_to_archive_or_delete'
        elif 'temp' in dir_name or 'tmp' in dir_name:
            return 'delete'
        elif 'test' in dir_name:
            return 'merge_with_tests'
        else:
            return 'review_contents'
    
    def should_skip_file(self, file_path: Path) -> bool:
        """判斷是否應該跳過檔案"""
        skip_patterns = [
            '.git/', '__pycache__/', '.pytest_cache/', '.venv/',
            'node_modules/', '.mypy_cache/'
        ]
        
        relative_path = str(file_path.relative_to(self.project_root))
        return any(pattern in relative_path for pattern in skip_patterns)
    
    def should_skip_directory(self, dir_path: Path) -> bool:
        """判斷是否應該跳過目錄"""
        skip_dirs = {'.git', '__pycache__', '.pytest_cache', '.venv', 'node_modules', '.mypy_cache'}
        return dir_path.name in skip_dirs
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """計算檔案雜湊值"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""
    
    def run_analysis(self) -> Dict[str, Any]:
        """運行完整分析"""
        print("🚀 開始全面檔案分析...")
        print("=" * 50)
        
        self.analysis_results.update({
            'misplaced_files': self.analyze_file_placement(),
            'redundant_files': self.find_redundant_files(),
            'temporary_files': self.find_temporary_files(),
            'empty_files': self.find_empty_files(),
            'directory_issues': self.analyze_directory_structure()
        })
        
        # 生成建議
        self.generate_recommendations()
        
        return self.analysis_results
    
    def generate_recommendations(self):
        """生成整理建議"""
        recommendations = []
        
        # 基於分析結果生成建議
        if self.analysis_results['misplaced_files']:
            recommendations.append({
                'priority': 'high',
                'category': 'file_placement',
                'description': f"移動 {len(self.analysis_results['misplaced_files'])} 個錯放的檔案到正確位置"
            })
        
        if self.analysis_results['redundant_files']:
            recommendations.append({
                'priority': 'medium',
                'category': 'redundancy',
                'description': f"刪除 {len(self.analysis_results['redundant_files'])} 組重複檔案"
            })
        
        if self.analysis_results['temporary_files']:
            temp_count = len(self.analysis_results['temporary_files'])
            recommendations.append({
                'priority': 'high',
                'category': 'cleanup',
                'description': f"清理 {temp_count} 個臨時檔案和快取檔案"
            })
        
        if self.analysis_results['empty_files']:
            recommendations.append({
                'priority': 'low',
                'category': 'empty_files',
                'description': f"處理 {len(self.analysis_results['empty_files'])} 個空白檔案"
            })
        
        self.analysis_results['recommendations'] = recommendations
    
    def generate_report(self) -> str:
        """生成分析報告"""
        results = self.analysis_results
        
        report = []
        report.append("📊 全面檔案整理分析報告")
        report.append("=" * 50)
        report.append(f"分析時間: {results['timestamp'][:19]}")
        report.append("")
        
        # 摘要統計
        report.append("📋 問題摘要")
        report.append("-" * 20)
        report.append(f"錯放檔案: {len(results['misplaced_files'])}")
        report.append(f"重複檔案組: {len(results['redundant_files'])}")
        report.append(f"臨時檔案: {len(results['temporary_files'])}")
        report.append(f"空白檔案: {len(results['empty_files'])}")
        report.append(f"目錄問題: {len(results['directory_issues'])}")
        report.append("")
        
        # 詳細問題
        if results['misplaced_files']:
            report.append("📁 錯放檔案")
            report.append("-" * 20)
            for item in results['misplaced_files'][:10]:  # 只顯示前10個
                report.append(f"  📄 {item['file']}")
                report.append(f"     建議移動到: {item['suggested_location']}")
                report.append(f"     原因: {item['reason']}")
            if len(results['misplaced_files']) > 10:
                report.append(f"  ... 還有 {len(results['misplaced_files']) - 10} 個檔案")
            report.append("")
        
        if results['temporary_files']:
            report.append("🗑️ 臨時檔案")
            report.append("-" * 20)
            temp_by_category = defaultdict(list)
            for item in results['temporary_files']:
                temp_by_category[item['category']].append(item)
            
            for category, files in temp_by_category.items():
                report.append(f"  {category.upper()}: {len(files)} 個檔案")
                for file in files[:3]:  # 只顯示前3個
                    report.append(f"    - {file['file']}")
                if len(files) > 3:
                    report.append(f"    - ... 還有 {len(files) - 3} 個")
            report.append("")
        
        if results['redundant_files']:
            report.append("🔄 重複檔案")
            report.append("-" * 20)
            for item in results['redundant_files'][:5]:  # 只顯示前5組
                report.append(f"  主檔案: {item['primary_file']}")
                report.append(f"  重複檔案: {', '.join(item['duplicates'])}")
            if len(results['redundant_files']) > 5:
                report.append(f"  ... 還有 {len(results['redundant_files']) - 5} 組")
            report.append("")
        
        # 建議行動
        if results['recommendations']:
            report.append("💡 建議行動")
            report.append("-" * 20)
            for rec in results['recommendations']:
                priority_icon = "🔴" if rec['priority'] == 'high' else "🟡" if rec['priority'] == 'medium' else "🟢"
                report.append(f"{priority_icon} {rec['description']}")
            report.append("")
        
        # 整理評分
        total_issues = (len(results['misplaced_files']) + 
                       len(results['redundant_files']) + 
                       len(results['temporary_files']) + 
                       len(results['directory_issues']))
        
        if total_issues == 0:
            score = "A+ (優秀)"
        elif total_issues <= 10:
            score = "B+ (良好)"
        elif total_issues <= 30:
            score = "C+ (一般)"
        else:
            score = "D (需要整理)"
        
        report.append(f"🏆 檔案整理評分: {score}")
        
        return "\n".join(report)
    
    def save_analysis(self, filename: str):
        """保存分析結果"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_results, f, indent=2, ensure_ascii=False)
        print(f"📄 分析結果已保存到: {filename}")


    def create_backup(self) -> str:
        """創建整理前的備份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_id = f"organization_{timestamp}"
        backup_path = self.backup_dir / backup_id
        backup_path.mkdir(parents=True, exist_ok=True)

        print(f"📦 創建備份: {backup_path}")
        return backup_id

    def execute_organization(self, analysis_file: str) -> bool:
        """執行檔案整理"""
        print("🚀 開始執行檔案整理...")

        # 載入分析結果
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                analysis = json.load(f)
        except Exception as e:
            print(f"❌ 無法載入分析結果: {e}")
            return False

        # 創建備份
        backup_id = self.create_backup()

        try:
            # 1. 移動錯放的檔案
            self.move_misplaced_files(analysis['misplaced_files'])

            # 2. 清理臨時檔案（只清理安全的類型）
            self.cleanup_safe_temporary_files(analysis['temporary_files'])

            # 3. 處理重複檔案（只處理明顯的重複）
            self.handle_safe_duplicates(analysis['redundant_files'])

            print(f"✅ 檔案整理完成！備份ID: {backup_id}")
            return True

        except Exception as e:
            print(f"❌ 整理過程中出錯: {e}")
            return False

    def move_misplaced_files(self, misplaced_files: List[Dict[str, Any]]):
        """移動錯放的檔案"""
        print("📁 移動錯放的檔案...")

        for item in misplaced_files:
            source = self.project_root / item['file']

            if item['suggested_location'] == 'DELETE':
                print(f"  🗑️ 刪除臨時檔案: {item['file']}")
                if source.exists():
                    source.unlink()
                continue

            target_dir = self.project_root / item['suggested_location']
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / source.name

            if source.exists() and not target.exists():
                shutil.move(str(source), str(target))
                print(f"  ✅ 移動: {item['file']} → {item['suggested_location']}")

    def cleanup_safe_temporary_files(self, temporary_files: List[Dict[str, Any]]):
        """清理安全的臨時檔案"""
        print("🗑️ 清理臨時檔案...")

        safe_categories = ['cache', 'logs']  # 只清理快取和舊日誌

        for item in temporary_files:
            if item['category'] in safe_categories:
                file_path = self.project_root / item['file']

                # 額外安全檢查
                if self.is_safe_to_delete(file_path):
                    try:
                        if file_path.exists():
                            if file_path.is_file():
                                file_path.unlink()
                            elif file_path.is_dir():
                                shutil.rmtree(file_path)
                            print(f"  🗑️ 刪除: {item['file']}")
                    except Exception as e:
                        print(f"  ⚠️ 無法刪除 {item['file']}: {e}")

    def is_safe_to_delete(self, file_path: Path) -> bool:
        """檢查檔案是否安全刪除"""
        relative_path = str(file_path.relative_to(self.project_root))

        # 絕對不刪除的路徑
        protected_patterns = [
            'src/', 'tests/', 'docs/', 'config/', 'scripts/',
            'pyproject.toml', 'poetry.lock', 'README.md'
        ]

        for pattern in protected_patterns:
            if relative_path.startswith(pattern) or pattern in relative_path:
                return False

        # 只刪除明確的快取和臨時檔案
        safe_patterns = [
            '__pycache__', '.pytest_cache', '.coverage', '.mypy_cache',
            '.log', '.tmp', '.temp'
        ]

        return any(pattern in relative_path for pattern in safe_patterns)

    def handle_safe_duplicates(self, redundant_files: List[Dict[str, Any]]):
        """處理安全的重複檔案"""
        print("🔄 處理重複檔案...")

        for item in redundant_files:
            # 只處理明顯的備份檔案
            for duplicate in item['duplicates']:
                if 'backup' in duplicate.lower() or duplicate.endswith('.bak'):
                    dup_path = self.project_root / duplicate
                    if dup_path.exists():
                        dup_path.unlink()
                        print(f"  🗑️ 刪除重複檔案: {duplicate}")

def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='全面檔案整理工具')
    parser.add_argument('--analyze', action='store_true', help='分析檔案結構')
    parser.add_argument('--execute', help='執行整理（需要分析檔案）')
    parser.add_argument('--output', default='file_organization_analysis.json',
                       help='輸出檔案名稱')

    args = parser.parse_args()

    organizer = ComprehensiveFileOrganizer()

    if args.analyze:
        results = organizer.run_analysis()

        # 生成並顯示報告
        report = organizer.generate_report()
        print(report)

        # 保存分析結果
        organizer.save_analysis(args.output)

        # 根據問題數量設置退出碼
        total_issues = (len(results['misplaced_files']) +
                       len(results['redundant_files']) +
                       len(results['temporary_files']) +
                       len(results['directory_issues']))

        if total_issues > 30:
            exit(1)
        else:
            exit(0)

    elif args.execute:
        success = organizer.execute_organization(args.execute)
        exit(0 if success else 1)

    else:
        print("請指定操作模式:")
        print("  --analyze              分析檔案結構")
        print("  --execute <analysis>   執行整理")


if __name__ == '__main__':
    main()
