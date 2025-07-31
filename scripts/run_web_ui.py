#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Web UI 啟動腳本

此腳本用於啟動 Web UI。
"""

import os
import sys
import argparse

# 添加項目根目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui import run_web_ui


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="啟動 Web UI")
    parser.add_argument("--port", type=int, default=8501, help="Web UI 端口")
    args = parser.parse_args()

    # 設置環境變數
    os.environ["STREAMLIT_SERVER_PORT"] = str(args.port)

    # 啟動 Web UI
    run_web_ui()


if __name__ == "__main__":
    main()
