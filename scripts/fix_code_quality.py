#!/usr/bin/env python3
"""
代碼品質修復腳本

自動修復常見的代碼品質問題：
- 移除尾隨空白
- 修復 docstring 格式
- 修復行長度問題
- 移除不必要的 else
"""

import os
import re
import sys


def fix_trailing_whitespace(content: str) -> str:
    """移除尾隨空白"""
    lines = content.split('\n')
    fixed_lines = [line.rstrip() for line in lines]
    return '\n'.join(fixed_lines)


def fix_docstring_format(content: str) -> str:
    """修復 docstring 格式"""
    # 修復空的第一行
    content = re.sub(
        r'(def [^:]+:\s*\n\s*""")\s*\n\s*([A-Z])',
        r'\1\2',
        content,
        flags=re.MULTILINE
    )
    return content


def fix_line_length(content: str) -> str:
    """修復過長的行"""
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        if len(line) > 88 and 'logger.' in line:
            # 分割長的 logger 行
            indent = len(line) - len(line.lstrip())
            if 'logger.info(' in line or 'logger.error(' in line or 'logger.warning(' in line:
                parts = line.split('", ')
                if len(parts) == 2:
                    fixed_lines.append(parts[0] + '",')
                    fixed_lines.append(' ' * (indent + 4) + parts[1])
                    continue
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_no_else_return(content: str) -> str:
    """修復不必要的 else after return"""
    # 這個比較複雜，暫時跳過自動修復
    return content


def fix_file(file_path: str) -> None:
    """修復單個文件"""
    print(f"修復文件: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 應用修復
    content = fix_trailing_whitespace(content)
    content = fix_docstring_format(content)
    content = fix_line_length(content)
    content = fix_no_else_return(content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"已修復: {file_path}")


def main():
    """主函數"""
    if len(sys.argv) < 2:
        print("用法: python fix_code_quality.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        sys.exit(1)
    
    fix_file(file_path)
    print("修復完成！")


if __name__ == "__main__":
    main()
