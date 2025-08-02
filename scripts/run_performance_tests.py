#!/usr/bin/env python3
"""
效能測試執行腳本

此腳本執行系統的效能測試，包括 API 回應時間、負載測試等。
"""

import sys
import subprocess
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_command(command: str, description: str = "") -> bool:
    """執行命令並顯示結果"""
    if description:
        print(f"\n🔄 {description}")
        print("-" * 60)

    try:
        subprocess.run(command, shell=True, check=True, cwd=project_root)
        print(f"✅ {description} - 成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - 失敗: {e}")
        return False


def main():
    """主函數"""
    print("🚀 執行效能測試")
    print("=" * 80)

    success_count = 0
    total_tests = 0

    # 效能測試列表
    performance_tests = [
        {
            "command": "poetry run python -m pytest tests/performance/ -v",
            "description": "執行效能測試套件",
        },
        {
            "command": "poetry run python -m pytest tests/performance/test_api_performance.py -v",
            "description": "API 效能測試",
        },
        {
            "command": "poetry run python -m pytest tests/performance/test_load_testing.py -v",
            "description": "負載測試",
        },
        {
            "command": "poetry run python -m pytest tests/performance/test_memory_profiling.py -v",
            "description": "記憶體分析測試",
        },
        {
            "command": "poetry run python -m pytest tests/performance/ --benchmark-only --benchmark-json=tests/performance/reports/benchmark-report.json",
            "description": "基準效能測試（僅 benchmark）",
        },
        {
            "command": "poetry run python -m pytest tests/performance/test_stress_testing.py -v",
            "description": "壓力測試",
        },
    ]

    # 執行測試
    for test in performance_tests:
        total_tests += 1
        if run_command(test["command"], test["description"]):
            success_count += 1

    # 顯示結果
    print("\n" + "=" * 80)
    print("效能測試結果總結")
    print("=" * 80)
    print(f"總測試數: {total_tests}")
    print(f"成功測試: {success_count}")
    print(f"失敗測試: {total_tests - success_count}")
    print(f"成功率: {(success_count / total_tests * 100):.1f}%")

    if success_count == total_tests:
        print("🎉 所有效能測試都通過了！")
        return 0
    else:
        print("⚠️ 部分效能測試失敗，請檢查相關問題")
        return 1


if __name__ == "__main__":
    sys.exit(main())
