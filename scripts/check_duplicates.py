#!/usr/bin/env python3
"""
重複檢查腳本

此腳本用於檢查專案中的重複實現，包括：
- 類別名稱重複檢查
- 函數簽名相似性檢查
- 配置常數重複檢查
- 導入依賴循環檢查

使用方法:
    python scripts/check_duplicates.py --target src/ --report duplicates_report.md --threshold 0.8

Author: AI Trading System
Version: v1.0
"""

import argparse
import ast
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any


class DuplicateChecker:
    """重複檢查器"""
    
    def __init__(self, threshold: float = 0.8):
        """初始化重複檢查器
        
        Args:
            threshold: 相似度閾值，0.8表示80%相似度以上視為重複
        """
        self.threshold = threshold
        self.classes = defaultdict(list)  # 類別名稱 -> [(檔案路徑, 行號)]
        self.functions = defaultdict(list)  # 函數名稱 -> [(檔案路徑, 行號, 參數)]
        self.constants = defaultdict(list)  # 常數名稱 -> [(檔案路徑, 行號, 值)]
        self.imports = defaultdict(set)  # 檔案路徑 -> {導入模組}
        self.duplicates = {
            "classes": [],
            "functions": [],
            "constants": [],
            "circular_imports": []
        }
    
    def check_directory(self, target_dir: str) -> None:
        """檢查目錄中的所有Python檔案
        
        Args:
            target_dir: 目標目錄路徑
        """
        target_path = Path(target_dir)
        if not target_path.exists():
            raise FileNotFoundError(f"目標目錄不存在: {target_dir}")
        
        python_files = list(target_path.rglob("*.py"))
        print(f"找到 {len(python_files)} 個Python檔案")
        
        for file_path in python_files:
            try:
                self._analyze_file(file_path)
            except Exception as e:
                print(f"分析檔案失敗 {file_path}: {e}")
        
        self._find_duplicates()
        self._find_circular_imports()
    
    def _analyze_file(self, file_path: Path) -> None:
        """分析單個Python檔案
        
        Args:
            file_path: 檔案路徑
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析AST
            tree = ast.parse(content)
            
            # 分析類別、函數和常數
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self._check_class_patterns(node, file_path)
                elif isinstance(node, ast.FunctionDef):
                    self._check_function_patterns(node, file_path)
                elif isinstance(node, ast.Assign):
                    self._check_constant_patterns(node, file_path)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    self._check_import_patterns(node, file_path)
                    
        except SyntaxError as e:
            print(f"語法錯誤 {file_path}: {e}")
        except Exception as e:
            print(f"檔案分析錯誤 {file_path}: {e}")
    
    def _check_class_patterns(self, node: ast.ClassDef, file_path: Path) -> None:
        """檢查類別模式
        
        Args:
            node: AST類別節點
            file_path: 檔案路徑
        """
        class_name = node.name
        
        # 檢查特定模式
        patterns = [
            r".*Crawler$", r".*Manager$", r".*Service$", r".*Collector$",
            r".*Handler$", r".*Provider$", r".*Client$", r".*API$"
        ]
        
        for pattern in patterns:
            if re.match(pattern, class_name):
                self.classes[class_name].append((str(file_path), node.lineno))
                break
    
    def _check_function_patterns(self, node: ast.FunctionDef, file_path: Path) -> None:
        """檢查函數模式
        
        Args:
            node: AST函數節點
            file_path: 檔案路徑
        """
        func_name = node.name
        
        # 檢查特定模式
        patterns = [
            r".*retry.*", r".*config.*", r".*process.*data.*", r".*validate.*",
            r"get_.*", r"fetch_.*", r"collect_.*", r"crawl_.*", r"clean_.*"
        ]
        
        for pattern in patterns:
            if re.match(pattern, func_name, re.IGNORECASE):
                # 獲取參數信息
                args = [arg.arg for arg in node.args.args]
                self.functions[func_name].append((str(file_path), node.lineno, args))
                break
    
    def _check_constant_patterns(self, node: ast.Assign, file_path: Path) -> None:
        """檢查常數模式
        
        Args:
            node: AST賦值節點
            file_path: 檔案路徑
        """
        for target in node.targets:
            if isinstance(target, ast.Name):
                const_name = target.id
                
                # 檢查特定模式
                patterns = [
                    r"DEFAULT_.*", r"CONFIG_.*", r".*_SETTINGS$", r".*_CONFIG$"
                ]
                
                for pattern in patterns:
                    if re.match(pattern, const_name):
                        # 嘗試獲取值
                        try:
                            value = ast.literal_eval(node.value)
                            self.constants[const_name].append((str(file_path), node.lineno, value))
                        except:
                            self.constants[const_name].append((str(file_path), node.lineno, "複雜值"))
                        break
    
    def _check_import_patterns(self, node: ast.AST, file_path: Path) -> None:
        """檢查導入模式
        
        Args:
            node: AST導入節點
            file_path: 檔案路徑
        """
        if isinstance(node, ast.Import):
            for alias in node.names:
                self.imports[str(file_path)].add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                self.imports[str(file_path)].add(node.module)
    
    def _find_duplicates(self) -> None:
        """查找重複項目"""
        # 查找重複類別
        for class_name, locations in self.classes.items():
            if len(locations) > 1:
                self.duplicates["classes"].append({
                    "name": class_name,
                    "locations": locations,
                    "count": len(locations)
                })
        
        # 查找重複函數
        for func_name, locations in self.functions.items():
            if len(locations) > 1:
                # 檢查參數相似性
                similar_groups = self._group_similar_functions(locations)
                for group in similar_groups:
                    if len(group) > 1:
                        self.duplicates["functions"].append({
                            "name": func_name,
                            "locations": group,
                            "count": len(group)
                        })
        
        # 查找重複常數
        for const_name, locations in self.constants.items():
            if len(locations) > 1:
                self.duplicates["constants"].append({
                    "name": const_name,
                    "locations": locations,
                    "count": len(locations)
                })
    
    def _group_similar_functions(self, locations: List[Tuple]) -> List[List[Tuple]]:
        """將相似的函數分組
        
        Args:
            locations: 函數位置列表
            
        Returns:
            List[List[Tuple]]: 相似函數分組
        """
        groups = []
        
        for i, (file1, line1, args1) in enumerate(locations):
            group = [(file1, line1, args1)]
            
            for j, (file2, line2, args2) in enumerate(locations[i+1:], i+1):
                # 計算參數相似度
                similarity = self._calculate_similarity(args1, args2)
                if similarity >= self.threshold:
                    group.append((file2, line2, args2))
            
            if len(group) > 1:
                groups.append(group)
        
        return groups
    
    def _calculate_similarity(self, args1: List[str], args2: List[str]) -> float:
        """計算參數相似度
        
        Args:
            args1: 第一個函數的參數列表
            args2: 第二個函數的參數列表
            
        Returns:
            float: 相似度（0-1之間）
        """
        if not args1 and not args2:
            return 1.0
        
        if not args1 or not args2:
            return 0.0
        
        # 簡單的相似度計算：共同參數數量 / 總參數數量
        common_args = set(args1) & set(args2)
        total_args = set(args1) | set(args2)
        
        return len(common_args) / len(total_args) if total_args else 0.0
    
    def _find_circular_imports(self) -> None:
        """查找循環導入"""
        # 簡化的循環導入檢查
        # 實際實現可能需要更複雜的圖算法
        for file_path, imports in self.imports.items():
            for imported_module in imports:
                # 檢查是否存在反向導入
                for other_file, other_imports in self.imports.items():
                    if file_path != other_file:
                        # 簡化檢查：如果A導入B，B也導入A
                        if (imported_module in other_imports and 
                            any(imp in imports for imp in other_imports)):
                            self.duplicates["circular_imports"].append({
                                "file1": file_path,
                                "file2": other_file,
                                "modules": [imported_module]
                            })
    
    def generate_report(self, output_file: str) -> None:
        """生成重複檢查報告
        
        Args:
            output_file: 輸出檔案路徑
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# 重複檢查報告\n\n")
            f.write(f"**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**相似度閾值**: {self.threshold}\n\n")
            
            # 統計摘要
            f.write("## 📊 統計摘要\n\n")
            f.write(f"- 重複類別: {len(self.duplicates['classes'])}\n")
            f.write(f"- 重複函數: {len(self.duplicates['functions'])}\n")
            f.write(f"- 重複常數: {len(self.duplicates['constants'])}\n")
            f.write(f"- 循環導入: {len(self.duplicates['circular_imports'])}\n\n")
            
            # 詳細報告
            self._write_class_duplicates(f)
            self._write_function_duplicates(f)
            self._write_constant_duplicates(f)
            self._write_circular_imports(f)
    
    def _write_class_duplicates(self, f) -> None:
        """寫入類別重複報告"""
        f.write("## 🔍 重複類別\n\n")
        if not self.duplicates["classes"]:
            f.write("✅ 未發現重複類別\n\n")
            return
        
        for dup in self.duplicates["classes"]:
            f.write(f"### {dup['name']} ({dup['count']} 個重複)\n\n")
            for file_path, line_no in dup['locations']:
                f.write(f"- `{file_path}:{line_no}`\n")
            f.write("\n")
    
    def _write_function_duplicates(self, f) -> None:
        """寫入函數重複報告"""
        f.write("## 🔧 重複函數\n\n")
        if not self.duplicates["functions"]:
            f.write("✅ 未發現重複函數\n\n")
            return
        
        for dup in self.duplicates["functions"]:
            f.write(f"### {dup['name']} ({dup['count']} 個重複)\n\n")
            for file_path, line_no, args in dup['locations']:
                f.write(f"- `{file_path}:{line_no}` - 參數: {args}\n")
            f.write("\n")
    
    def _write_constant_duplicates(self, f) -> None:
        """寫入常數重複報告"""
        f.write("## 📋 重複常數\n\n")
        if not self.duplicates["constants"]:
            f.write("✅ 未發現重複常數\n\n")
            return
        
        for dup in self.duplicates["constants"]:
            f.write(f"### {dup['name']} ({dup['count']} 個重複)\n\n")
            for file_path, line_no, value in dup['locations']:
                f.write(f"- `{file_path}:{line_no}` - 值: {value}\n")
            f.write("\n")
    
    def _write_circular_imports(self, f) -> None:
        """寫入循環導入報告"""
        f.write("## 🔄 循環導入\n\n")
        if not self.duplicates["circular_imports"]:
            f.write("✅ 未發現循環導入\n\n")
            return
        
        for dup in self.duplicates["circular_imports"]:
            f.write(f"### 循環導入檢測\n\n")
            f.write(f"- 檔案1: `{dup['file1']}`\n")
            f.write(f"- 檔案2: `{dup['file2']}`\n")
            f.write(f"- 涉及模組: {dup['modules']}\n\n")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="檢查專案中的重複實現")
    parser.add_argument("--target", required=True, help="目標目錄路徑")
    parser.add_argument("--report", required=True, help="報告輸出檔案路徑")
    parser.add_argument("--threshold", type=float, default=0.8, 
                       help="相似度閾值 (0.0-1.0)")
    parser.add_argument("--format", default="markdown", 
                       choices=["markdown"], help="報告格式")
    
    args = parser.parse_args()
    
    print(f"開始檢查重複實現...")
    print(f"目標目錄: {args.target}")
    print(f"相似度閾值: {args.threshold}")
    
    checker = DuplicateChecker(threshold=args.threshold)
    checker.check_directory(args.target)
    checker.generate_report(args.report)
    
    print(f"檢查完成，報告已生成: {args.report}")
    
    # 輸出簡要統計
    total_duplicates = (len(checker.duplicates["classes"]) + 
                       len(checker.duplicates["functions"]) + 
                       len(checker.duplicates["constants"]) + 
                       len(checker.duplicates["circular_imports"]))
    
    if total_duplicates > 0:
        print(f"⚠️ 發現 {total_duplicates} 個重複問題")
        sys.exit(1)
    else:
        print("✅ 未發現重複問題")
        sys.exit(0)


if __name__ == "__main__":
    main()
