#!/usr/bin/env python3
"""
根目錄清理工具

此腳本專門清理專案根目錄，將錯放的檔案移動到正確位置，
並確保根目錄只保留必要的專案檔案。

Usage:
    python scripts/root_directory_cleaner.py --analyze
    python scripts/root_directory_cleaner.py --execute
    python scripts/root_directory_cleaner.py --restore backup_id
"""

import os
import shutil
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Set
import re


class RootDirectoryCleaner:
    """根目錄清理器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.backup_dir = self.project_root / "root_cleanup_backups"
        
        # 定義應該保留在根目錄的檔案
        self.allowed_root_files = {
            # 專案配置檔案
            'README.md', 'pyproject.toml', 'poetry.lock',
            'requirements-production.txt',
            
            # Docker 相關
            'Dockerfile', 'docker-compose.yml', 'docker-compose.dev.yml', 
            'docker-compose.prod.yml',
            
            # 啟動腳本
            'start.sh', 'start.bat',
            
            # 安裝和啟動工具
            'install_dependencies.py', 'launch_ui_comparison.py',
            
            # 安全檔案
            'security.key',
            
            # VS Code 工作區
            'auto_trading_project.code-workspace',
            
            # Git 和開發工具配置
            '.gitignore', '.gitattributes', '.env', '.env.example',
            '.pylintrc', '.flake8', '.bandit', '.pre-commit-config.yaml'
        }
        
        # 定義檔案類型和目標目錄的映射
        self.file_type_mapping = {
            'json_results': {
                'patterns': [r'.*analysis\.json$', r'.*results?\.json$', r'.*audit\.json$', 
                           r'.*performance.*\.json$', r'.*baseline.*\.json$', r'.*report\.json$'],
                'target': 'results/',
                'description': 'JSON 分析和結果檔案'
            },
            'log_files': {
                'patterns': [r'.*\.log$', r'.*\.log\.\d+$'],
                'target': 'logs/',
                'description': '日誌檔案'
            },
            'temp_files': {
                'patterns': [r'.*\.tmp$', r'.*\.temp$', r'.*\.bak$', r'.*\.backup$', 
                           r'.*~$', r'.*\.swp$', r'.*\.swo$'],
                'target': 'DELETE',
                'description': '臨時檔案'
            },
            'text_reports': {
                'patterns': [r'.*_report\.txt$', r'.*_scan.*\.txt$'],
                'target': 'results/',
                'description': '文字報告檔案'
            }
        }
        
        self.analysis_results = {
            'timestamp': datetime.now().isoformat(),
            'files_to_move': [],
            'files_to_delete': [],
            'files_to_keep': [],
            'workspace_config_issues': []
        }
    
    def analyze_root_files(self) -> Dict[str, Any]:
        """分析根目錄檔案"""
        print("🔍 分析根目錄檔案...")
        
        files_to_move = []
        files_to_delete = []
        files_to_keep = []
        
        # 掃描根目錄中的所有檔案
        for file_path in self.project_root.iterdir():
            if file_path.is_file():
                file_name = file_path.name
                
                # 檢查是否應該保留在根目錄
                if file_name in self.allowed_root_files:
                    files_to_keep.append({
                        'file': file_name,
                        'size': file_path.stat().st_size,
                        'reason': '標準根目錄檔案'
                    })
                else:
                    # 檢查檔案類型並決定處理方式
                    action = self.determine_file_action(file_path)
                    
                    if action['action'] == 'move':
                        files_to_move.append({
                            'file': file_name,
                            'target': action['target'],
                            'reason': action['reason'],
                            'size': file_path.stat().st_size
                        })
                    elif action['action'] == 'delete':
                        files_to_delete.append({
                            'file': file_name,
                            'reason': action['reason'],
                            'size': file_path.stat().st_size
                        })
                    else:
                        # 未知檔案類型，需要手動檢查
                        files_to_move.append({
                            'file': file_name,
                            'target': 'MANUAL_REVIEW',
                            'reason': '未知檔案類型，需要手動檢查',
                            'size': file_path.stat().st_size
                        })
        
        self.analysis_results.update({
            'files_to_move': files_to_move,
            'files_to_delete': files_to_delete,
            'files_to_keep': files_to_keep
        })
        
        return self.analysis_results
    
    def determine_file_action(self, file_path: Path) -> Dict[str, str]:
        """決定檔案的處理動作"""
        file_name = file_path.name
        
        # 檢查各種檔案類型
        for file_type, config in self.file_type_mapping.items():
            for pattern in config['patterns']:
                if re.match(pattern, file_name, re.IGNORECASE):
                    if config['target'] == 'DELETE':
                        return {
                            'action': 'delete',
                            'target': '',
                            'reason': config['description']
                        }
                    else:
                        return {
                            'action': 'move',
                            'target': config['target'],
                            'reason': config['description']
                        }
        
        # 預設動作
        return {
            'action': 'review',
            'target': 'MANUAL_REVIEW',
            'reason': '未知檔案類型'
        }
    
    def check_workspace_config(self) -> List[Dict[str, Any]]:
        """檢查 VS Code 工作區配置"""
        print("🔍 檢查 VS Code 工作區配置...")
        
        issues = []
        workspace_file = self.project_root / 'auto_trading_project.code-workspace'
        
        if workspace_file.exists():
            try:
                with open(workspace_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 檢查是否包含過時的路徑
                if len(content.strip()) < 100:  # 檔案太小，可能配置不完整
                    issues.append({
                        'issue': 'incomplete_config',
                        'description': '工作區配置檔案內容過少，可能需要更新',
                        'suggestion': '檢查並更新工作區配置'
                    })
                
                # 檢查是否包含絕對路徑
                if 'D:\\' in content or 'C:\\' in content:
                    issues.append({
                        'issue': 'absolute_paths',
                        'description': '工作區配置包含絕對路徑',
                        'suggestion': '使用相對路徑以提高可移植性'
                    })
                
            except Exception as e:
                issues.append({
                    'issue': 'read_error',
                    'description': f'無法讀取工作區配置: {e}',
                    'suggestion': '檢查檔案權限和格式'
                })
        
        self.analysis_results['workspace_config_issues'] = issues
        return issues
    
    def create_backup(self) -> str:
        """創建備份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_id = f"root_cleanup_{timestamp}"
        backup_path = self.backup_dir / backup_id
        backup_path.mkdir(parents=True, exist_ok=True)
        
        print(f"📦 創建根目錄清理備份: {backup_path}")
        
        # 備份要移動或刪除的檔案
        backup_info = {
            'backup_id': backup_id,
            'timestamp': timestamp,
            'moved_files': [],
            'deleted_files': []
        }
        
        for item in self.analysis_results['files_to_move']:
            if item['target'] != 'MANUAL_REVIEW':
                source_file = self.project_root / item['file']
                if source_file.exists():
                    backup_file = backup_path / item['file']
                    shutil.copy2(source_file, backup_file)
                    backup_info['moved_files'].append(item['file'])
        
        for item in self.analysis_results['files_to_delete']:
            source_file = self.project_root / item['file']
            if source_file.exists():
                backup_file = backup_path / item['file']
                shutil.copy2(source_file, backup_file)
                backup_info['deleted_files'].append(item['file'])
        
        # 保存備份資訊
        info_file = backup_path / "backup_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, indent=2, ensure_ascii=False)
        
        return backup_id
    
    def execute_cleanup(self) -> bool:
        """執行清理操作"""
        print("🚀 開始執行根目錄清理...")
        print("=" * 50)
        
        # 創建備份
        backup_id = self.create_backup()
        
        try:
            moved_count = 0
            deleted_count = 0
            
            # 移動檔案
            for item in self.analysis_results['files_to_move']:
                if item['target'] == 'MANUAL_REVIEW':
                    print(f"⚠️ 跳過需要手動檢查的檔案: {item['file']}")
                    continue
                
                source = self.project_root / item['file']
                target_dir = self.project_root / item['target']
                
                if source.exists():
                    # 確保目標目錄存在
                    target_dir.mkdir(parents=True, exist_ok=True)
                    target = target_dir / item['file']
                    
                    # 如果目標檔案已存在，添加時間戳
                    if target.exists():
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        name_parts = item['file'].rsplit('.', 1)
                        if len(name_parts) == 2:
                            new_name = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
                        else:
                            new_name = f"{item['file']}_{timestamp}"
                        target = target_dir / new_name
                    
                    shutil.move(str(source), str(target))
                    moved_count += 1
                    print(f"  ✅ 移動: {item['file']} → {item['target']}")
            
            # 刪除檔案
            for item in self.analysis_results['files_to_delete']:
                source = self.project_root / item['file']
                if source.exists():
                    source.unlink()
                    deleted_count += 1
                    print(f"  🗑️ 刪除: {item['file']}")
            
            print(f"\n✅ 根目錄清理完成！")
            print(f"  移動檔案: {moved_count} 個")
            print(f"  刪除檔案: {deleted_count} 個")
            print(f"  備份ID: {backup_id}")
            
            return True
            
        except Exception as e:
            print(f"❌ 清理過程中出錯: {e}")
            return False
    
    def generate_report(self) -> str:
        """生成清理報告"""
        results = self.analysis_results
        
        report = []
        report.append("📊 根目錄清理分析報告")
        report.append("=" * 40)
        report.append(f"分析時間: {results['timestamp'][:19]}")
        report.append("")
        
        # 統計摘要
        report.append("📋 清理摘要")
        report.append("-" * 20)
        report.append(f"需要移動的檔案: {len(results['files_to_move'])}")
        report.append(f"需要刪除的檔案: {len(results['files_to_delete'])}")
        report.append(f"保留在根目錄的檔案: {len(results['files_to_keep'])}")
        report.append("")
        
        # 需要移動的檔案
        if results['files_to_move']:
            report.append("📁 需要移動的檔案")
            report.append("-" * 20)
            for item in results['files_to_move']:
                size_mb = item['size'] / (1024 * 1024)
                if item['target'] == 'MANUAL_REVIEW':
                    report.append(f"  ⚠️ {item['file']} ({size_mb:.2f}MB) - {item['reason']}")
                else:
                    report.append(f"  📄 {item['file']} → {item['target']} ({size_mb:.2f}MB)")
                    report.append(f"     理由: {item['reason']}")
            report.append("")
        
        # 需要刪除的檔案
        if results['files_to_delete']:
            report.append("🗑️ 需要刪除的檔案")
            report.append("-" * 20)
            for item in results['files_to_delete']:
                size_mb = item['size'] / (1024 * 1024)
                report.append(f"  ❌ {item['file']} ({size_mb:.2f}MB) - {item['reason']}")
            report.append("")
        
        # 保留的檔案
        if results['files_to_keep']:
            report.append("✅ 保留在根目錄的檔案")
            report.append("-" * 20)
            for item in results['files_to_keep'][:10]:  # 只顯示前10個
                size_mb = item['size'] / (1024 * 1024)
                report.append(f"  📄 {item['file']} ({size_mb:.2f}MB)")
            if len(results['files_to_keep']) > 10:
                report.append(f"  ... 還有 {len(results['files_to_keep']) - 10} 個檔案")
            report.append("")
        
        # 工作區配置問題
        if results['workspace_config_issues']:
            report.append("⚙️ VS Code 工作區配置問題")
            report.append("-" * 20)
            for issue in results['workspace_config_issues']:
                report.append(f"  ⚠️ {issue['description']}")
                report.append(f"     建議: {issue['suggestion']}")
            report.append("")
        
        # 清理建議
        total_files_to_process = len(results['files_to_move']) + len(results['files_to_delete'])
        if total_files_to_process > 0:
            report.append("💡 建議執行清理")
            report.append(f"  預計處理檔案: {total_files_to_process} 個")
        else:
            report.append("✅ 根目錄結構良好")
        
        return "\n".join(report)
    
    def save_analysis(self, filename: str):
        """保存分析結果"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_results, f, indent=2, ensure_ascii=False)
        print(f"📄 分析結果已保存到: {filename}")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='根目錄清理工具')
    parser.add_argument('--analyze', action='store_true', help='分析根目錄檔案')
    parser.add_argument('--execute', action='store_true', help='執行清理操作')
    parser.add_argument('--output', default='root_cleanup_analysis.json', 
                       help='輸出檔案名稱')
    
    args = parser.parse_args()
    
    cleaner = RootDirectoryCleaner()
    
    if args.analyze:
        # 執行分析
        results = cleaner.analyze_root_files()
        cleaner.check_workspace_config()
        
        # 生成並顯示報告
        report = cleaner.generate_report()
        print(report)
        
        # 保存分析結果
        cleaner.save_analysis(args.output)
        
    elif args.execute:
        # 先執行分析
        cleaner.analyze_root_files()
        cleaner.check_workspace_config()
        
        # 執行清理
        success = cleaner.execute_cleanup()
        exit(0 if success else 1)
        
    else:
        print("請指定操作模式:")
        print("  --analyze    分析根目錄檔案")
        print("  --execute    執行清理操作")


if __name__ == '__main__':
    main()
