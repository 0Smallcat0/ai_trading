#!/usr/bin/env python3
"""
安全測試執行腳本

此腳本執行系統的安全測試，包括 JWT 認證、SQL 注入防護、XSS 防護等。
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
    print("🔒 執行安全測試")
    print("=" * 80)

    success_count = 0
    total_tests = 0

    # 安全測試列表
    security_tests = [
        {
            "command": "poetry run python -m pytest tests/security/ -v",
            "description": "執行安全測試套件",
        },
        {
            "command": "poetry run python -m pytest tests/security/test_jwt_security.py -v",
            "description": "JWT 認證安全測試",
        },
        {
            "command": "poetry run python -m pytest tests/security/test_sql_injection.py -v",
            "description": "SQL 注入防護測試",
        },
        {
            "command": "poetry run python -m pytest tests/security/test_xss_protection.py -v",
            "description": "XSS 攻擊防護測試",
        },
        {
            "command": "poetry run python -m pytest tests/security/test_versioning_security.py -v",
            "description": "版本控制安全測試",
        },
        {
            "command": "poetry run bandit -r src/ -f json -o tests/security/reports/bandit-report.json --config .bandit",
            "description": "Bandit 代碼安全掃描",
        },
        {
            "command": "poetry run safety check --output json --save-json tests/security/reports/safety-report.json",
            "description": "Safety 依賴漏洞掃描",
        },
    ]

    # 執行測試
    for test in security_tests:
        total_tests += 1
        if run_command(test["command"], test["description"]):
            success_count += 1

    # 顯示結果
    print("\n" + "=" * 80)
    print("安全測試結果總結")
    print("=" * 80)
    print(f"總測試數: {total_tests}")
    print(f"成功測試: {success_count}")
    print(f"失敗測試: {total_tests - success_count}")
    print(f"成功率: {(success_count / total_tests * 100):.1f}%")

    if success_count == total_tests:
        print("🎉 所有安全測試都通過了！")
        return 0
    else:
        print("⚠️ 部分安全測試失敗，請檢查相關問題")
        return 1


if __name__ == "__main__":
    sys.exit(main())
