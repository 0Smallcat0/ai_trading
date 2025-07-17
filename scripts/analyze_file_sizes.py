#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
檔案大小分析工具

此腳本用於分析專案中的Python檔案大小，識別需要重構的超大檔案，
並按照優先級生成重構計劃。

使用方法:
    python scripts/analyze_file_sizes.py
    python scripts/analyze_file_sizes.py --threshold 300
    python scripts/analyze_file_sizes.py --output results/file_analysis.json
"""

import os
import sys
import json
import argparse
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from datetime import datetime


class FileAnalyzer:
    """檔案大小分析器"""
    
    def __init__(self, threshold: int = 300):
        """初始化分析器
        
        Args:
            threshold: 檔案行數閾值，超過此值視為需要重構
        """
        self.threshold = threshold
        self.priority_mapping = {
            # 第一優先級：核心業務邏輯
            'src/core/': 1,
            'src/api/': 1, 
            'src/risk_management/': 1,
            
            # 第二優先級：用戶界面和執行
            'src/ui/': 2,
            'src/strategies/': 2,
            'src/execution/': 2,
            
            # 第三優先級：工具和測試
            'scripts/': 3,
            'tests/': 3,
            'src/utils/': 3,
            
            # 其他模組
            'src/': 2  # 默認第二優先級
        }
    
    def count_lines(self, filepath: str) -> int:
        """計算檔案行數
        
        Args:
            filepath: 檔案路徑
            
        Returns:
            檔案行數
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return len(f.readlines())
        except (UnicodeDecodeError, IOError):
            try:
                with open(filepath, 'r', encoding='gbk') as f:
                    return len(f.readlines())
            except (UnicodeDecodeError, IOError):
                return 0
    
    def get_priority(self, filepath: str) -> int:
        """獲取檔案重構優先級

        Args:
            filepath: 檔案路徑

        Returns:
            優先級 (1=最高, 2=中等, 3=最低)
        """
        # 標準化路徑分隔符
        normalized_path = filepath.replace('\\', '/').replace('./', '')

        # 按照最具體的路徑匹配
        for path_prefix, priority in sorted(self.priority_mapping.items(), key=len, reverse=True):
            if normalized_path.startswith(path_prefix):
                return priority
        return 3  # 默認最低優先級
    
    def analyze_directory(self, directory: str = '.') -> Dict:
        """分析目錄中的所有Python檔案
        
        Args:
            directory: 要分析的目錄路徑
            
        Returns:
            分析結果字典
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'threshold': self.threshold,
            'total_files': 0,
            'oversized_files': 0,
            'files_by_priority': {1: [], 2: [], 3: []},
            'statistics': {
                'priority_1_count': 0,
                'priority_2_count': 0, 
                'priority_3_count': 0,
                'max_lines': 0,
                'avg_lines': 0
            }
        }
        
        all_files = []
        total_lines = 0
        
        # 掃描所有Python檔案
        for root, dirs, files in os.walk(directory):
            # 跳過隱藏目錄和__pycache__
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file).replace('\\', '/')
                    line_count = self.count_lines(filepath)
                    priority = self.get_priority(filepath)
                    
                    file_info = {
                        'path': filepath,
                        'lines': line_count,
                        'priority': priority,
                        'oversized': line_count > self.threshold,
                        'severity': 'error' if line_count > self.threshold else 'warning' if line_count > 250 else 'ok'
                    }
                    
                    all_files.append(file_info)
                    total_lines += line_count
                    results['total_files'] += 1
                    
                    if line_count > self.threshold:
                        results['oversized_files'] += 1
                        results['files_by_priority'][priority].append(file_info)
                        results['statistics'][f'priority_{priority}_count'] += 1
                    
                    if line_count > results['statistics']['max_lines']:
                        results['statistics']['max_lines'] = line_count
        
        # 計算平均行數
        if results['total_files'] > 0:
            results['statistics']['avg_lines'] = total_lines / results['total_files']
        
        # 按行數排序每個優先級的檔案
        for priority in results['files_by_priority']:
            results['files_by_priority'][priority].sort(key=lambda x: x['lines'], reverse=True)
        
        return results
    
    def generate_refactor_plan(self, analysis_results: Dict) -> List[Dict]:
        """生成重構計劃
        
        Args:
            analysis_results: 分析結果
            
        Returns:
            重構計劃列表
        """
        refactor_plan = []
        
        # 按優先級處理
        for priority in [1, 2, 3]:
            files = analysis_results['files_by_priority'][priority]
            
            for file_info in files:
                plan_item = {
                    'file': file_info['path'],
                    'lines': file_info['lines'],
                    'priority': priority,
                    'estimated_effort': self._estimate_effort(file_info['lines']),
                    'refactor_strategy': self._suggest_strategy(file_info),
                    'target_files': self._suggest_split(file_info)
                }
                refactor_plan.append(plan_item)
        
        return refactor_plan
    
    def _estimate_effort(self, lines: int) -> str:
        """估算重構工作量
        
        Args:
            lines: 檔案行數
            
        Returns:
            工作量估算 (small/medium/large/huge)
        """
        if lines <= 400:
            return 'small'
        elif lines <= 600:
            return 'medium'
        elif lines <= 1000:
            return 'large'
        else:
            return 'huge'
    
    def _suggest_strategy(self, file_info: Dict) -> List[str]:
        """建議重構策略
        
        Args:
            file_info: 檔案資訊
            
        Returns:
            重構策略列表
        """
        strategies = []
        lines = file_info['lines']
        
        if lines > 300:
            strategies.append('split_into_modules')
        if lines > 500:
            strategies.append('extract_classes')
        if lines > 800:
            strategies.append('separate_concerns')
        if lines > 1000:
            strategies.append('major_refactoring')
            
        strategies.extend([
            'add_docstrings',
            'improve_error_handling',
            'reduce_complexity'
        ])
        
        return strategies
    
    def _suggest_split(self, file_info: Dict) -> List[str]:
        """建議檔案拆分方案
        
        Args:
            file_info: 檔案資訊
            
        Returns:
            建議的目標檔案列表
        """
        filepath = file_info['path']
        lines = file_info['lines']
        
        if lines <= 400:
            return [filepath]  # 不需要拆分
        
        # 根據檔案類型和大小建議拆分
        base_name = os.path.splitext(filepath)[0]
        
        if 'service' in filepath:
            return [
                f"{base_name}_core.py",
                f"{base_name}_utils.py",
                f"{base_name}_models.py"
            ]
        elif 'adapter' in filepath:
            return [
                f"{base_name}_base.py", 
                f"{base_name}_impl.py"
            ]
        else:
            # 通用拆分方案
            num_files = min(4, max(2, lines // 300))
            return [f"{base_name}_part{i+1}.py" for i in range(num_files)]


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='分析Python檔案大小並生成重構計劃')
    parser.add_argument('--threshold', type=int, default=300, help='檔案行數閾值')
    parser.add_argument('--output', type=str, help='輸出檔案路徑')
    parser.add_argument('--directory', type=str, default='.', help='要分析的目錄')
    
    args = parser.parse_args()
    
    analyzer = FileAnalyzer(threshold=args.threshold)
    
    print(f"🔍 分析目錄: {args.directory}")
    print(f"📏 行數閾值: {args.threshold}")
    print("=" * 60)
    
    # 執行分析
    results = analyzer.analyze_directory(args.directory)
    
    # 顯示統計結果
    print(f"📊 分析結果:")
    print(f"  總檔案數: {results['total_files']}")
    print(f"  超大檔案數: {results['oversized_files']}")
    print(f"  最大檔案行數: {results['statistics']['max_lines']}")
    print(f"  平均檔案行數: {results['statistics']['avg_lines']:.1f}")
    print()
    
    print("📋 按優先級分類:")
    for priority in [1, 2, 3]:
        count = results['statistics'][f'priority_{priority}_count']
        priority_name = ['', '核心模組', '界面執行', '工具測試'][priority]
        print(f"  優先級 {priority} ({priority_name}): {count} 個檔案")
    print()
    
    # 顯示前10個最大的檔案
    all_oversized = []
    for priority in [1, 2, 3]:
        all_oversized.extend(results['files_by_priority'][priority])
    
    all_oversized.sort(key=lambda x: x['lines'], reverse=True)
    
    print("🔥 前10個最大檔案:")
    for i, file_info in enumerate(all_oversized[:10], 1):
        priority_name = ['', '核心', '界面', '工具'][file_info['priority']]
        print(f"  {i:2d}. {file_info['path']}: {file_info['lines']} 行 ({priority_name})")
    
    # 生成重構計劃
    refactor_plan = analyzer.generate_refactor_plan(results)
    
    # 輸出結果
    output_data = {
        'analysis': results,
        'refactor_plan': refactor_plan
    }
    
    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 結果已保存到: {args.output}")
    
    print(f"\n🎯 建議優先處理 {len(refactor_plan)} 個檔案")
    print("   使用 --output 參數保存詳細的重構計劃")


if __name__ == "__main__":
    main()
