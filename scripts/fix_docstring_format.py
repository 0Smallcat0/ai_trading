#!/usr/bin/env python3
"""
Docstring 格式修復腳本

自動修復 docstring 第一行空白問題
"""

import os
import re
import sys


def fix_docstring_format(content: str) -> str:
    """修復 docstring 格式"""
    # 修復方法和類別的 docstring 第一行空白
    patterns = [
        # 類別 docstring
        (r'(class [^:]+:\s*\n\s*"""\s*\n\s*)([A-Z\u4e00-\u9fff])', r'\1\2'),
        # 方法 docstring  
        (r'(def [^:]+:\s*\n\s*"""\s*\n\s*)([A-Z\u4e00-\u9fff])', r'\1\2'),
        # 函數 docstring
        (r'(    def [^:]+:\s*\n\s*"""\s*\n\s*)([A-Z\u4e00-\u9fff])', r'\1\2'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    return content


def fix_file(file_path: str) -> None:
    """修復單個文件"""
    print(f"修復文件: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 應用修復
    original_content = content
    content = fix_docstring_format(content)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"已修復: {file_path}")
    else:
        print(f"無需修復: {file_path}")


def main():
    """主函數"""
    if len(sys.argv) < 2:
        print("用法: python fix_docstring_format.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        sys.exit(1)
    
    fix_file(file_path)
    print("修復完成！")


if __name__ == "__main__":
    main()
