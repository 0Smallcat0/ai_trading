#!/usr/bin/env python3
"""
風險管理模組演示啟動腳本

此腳本用於啟動 Streamlit 應用並直接導航到風險管理頁面進行演示。

使用方法：
    python scripts/start_risk_management_demo.py
"""

import sys
import os
import time
import webbrowser
import subprocess
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    """主函數"""
    print("🚀 啟動風險管理模組演示...")

    # 檢查是否在專案根目錄
    if not (project_root / "pyproject.toml").exists():
        print("❌ 錯誤：請在專案根目錄執行此腳本")
        return

    # 啟動 Streamlit 應用
    print("📊 啟動 Streamlit 應用...")

    try:
        # 使用 poetry 運行 streamlit
        cmd = [
            "poetry",
            "run",
            "python",
            "-m",
            "streamlit",
            "run",
            "src/ui/web_ui.py",
            "--server.address=127.0.0.1",
            "--server.port=8501",
            "--server.headless=false",
        ]

        # 在專案根目錄執行命令
        process = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        print("⏳ 等待應用啟動...")
        time.sleep(5)

        # 檢查應用是否成功啟動
        if process.poll() is None:
            print("✅ Streamlit 應用已啟動")
            print("🌐 應用地址: http://localhost:8501")
            print("🛡️ 請在側邊欄選擇「風險管理」頁面進行測試")
            print("\n📋 測試建議：")
            print("1. 測試風險參數設定功能")
            print("2. 查看風險指標監控面板")
            print("3. 測試風控機制控制")
            print("4. 查看風險警報記錄")
            print("\n按 Ctrl+C 停止應用")

            # 自動開啟瀏覽器
            try:
                webbrowser.open("http://localhost:8501")
            except Exception as e:
                print(f"⚠️ 無法自動開啟瀏覽器: {e}")
                print("請手動開啟 http://localhost:8501")

            # 等待用戶中斷
            try:
                process.wait()
            except KeyboardInterrupt:
                print("\n🛑 正在停止應用...")
                process.terminate()
                process.wait()
                print("✅ 應用已停止")
        else:
            # 獲取錯誤信息
            stdout, stderr = process.communicate()
            print("❌ 應用啟動失敗")
            if stderr:
                print(f"錯誤信息: {stderr}")
            if stdout:
                print(f"輸出信息: {stdout}")

    except FileNotFoundError:
        print("❌ 錯誤：找不到 poetry 命令")
        print("請確保已安裝 poetry 並且在 PATH 中")
        print("安裝方法: https://python-poetry.org/docs/#installation")
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")


if __name__ == "__main__":
    main()
