#!/usr/bin/env python3
"""修復 flake8 格式問題的腳本"""

import os
import re
from pathlib import Path


def fix_whitespace_issues(file_path):
    """修復空行和行尾空格問題"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fixed_lines = []
    for line in lines:
        # 修復行尾空格 (W291)
        line = line.rstrip() + '\n'

        # 修復空行包含空格 (W293)
        if line.strip() == '':
            line = '\n'

        fixed_lines.append(line)

    # 移除文件末尾的多餘空行
    while fixed_lines and fixed_lines[-1].strip() == '':
        fixed_lines.pop()

    # 確保文件以換行符結尾
    if fixed_lines and not fixed_lines[-1].endswith('\n'):
        fixed_lines[-1] += '\n'

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)


def fix_binary_operator_issues(file_path):
    """修復二元運算符換行問題"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # 檢查是否有多行的二元運算符表達式
        if ('|' in line or '&' in line) and line.rstrip().endswith(('|', '&')):
            # 將運算符移到下一行的開頭
            operator = line.rstrip()[-1]
            line_without_op = line.rstrip()[:-1].rstrip()

            # 收集後續的行
            continuation_lines = [line_without_op + '\n']
            i += 1

            while i < len(lines) and (lines[i].strip().startswith(('|', '&', '(')) or
                                      lines[i].strip() == '' or
                                      '|' in lines[i] or '&' in lines[i]):
                next_line = lines[i].strip()
                if next_line and not next_line.startswith(('|', '&')):
                    continuation_lines.append(f"            {operator} {next_line}\n")
                elif next_line.startswith(('|', '&')):
                    continuation_lines.append(f"            {next_line}\n")
                else:
                    continuation_lines.append(lines[i])
                i += 1

            # 添加修復後的行
            fixed_lines.extend(continuation_lines)
            i -= 1  # 回退一步，因為外層循環會增加
        else:
            fixed_lines.append(line)

        i += 1

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)


def main():
    """主函數"""
    backtest_module_dir = Path('src/core/backtest_module')

    if not backtest_module_dir.exists():
        print(f"目錄不存在: {backtest_module_dir}")
        return

    python_files = list(backtest_module_dir.glob('*.py'))

    print(f"找到 {len(python_files)} 個 Python 文件")

    for file_path in python_files:
        print(f"修復文件: {file_path}")
        try:
            fix_whitespace_issues(file_path)
            # fix_binary_operator_issues(file_path)  # 暫時註釋，需要更仔細的處理
            print(f"✅ 已修復: {file_path}")
        except Exception as e:
            print(f"❌ 修復失敗 {file_path}: {e}")

    print("修復完成！")


if __name__ == '__main__':
    main()
