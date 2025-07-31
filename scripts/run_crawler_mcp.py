#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MCP 資料爬蟲執行腳本

此腳本用於執行 MCP (Model Context Protocol) 資料爬蟲，
包括市場新聞抓取和情緒分析。
"""

import argparse
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    from src.data_sources.mcp_data_ingest import (
        analyze_market_sentiment,
        fetch_market_news,
    )
except ImportError:
    print("無法導入 MCP 資料模組，請確認相關檔案存在")
    sys.exit(1)


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="MCP 資料爬蟲執行腳本")
    parser.add_argument("--query", type=str, default="台積電", help="查詢關鍵字")
    parser.add_argument("--days", type=int, default=7, help="查詢天數")
    parser.add_argument(
        "--server-url", type=str, default="http://localhost:3000", help="MCP 伺服器 URL"
    )

    args = parser.parse_args()

    print(f"開始執行 MCP 資料爬蟲...")
    print(f"查詢關鍵字: {args.query}")
    print(f"查詢天數: {args.days}")
    print(f"伺服器 URL: {args.server_url}")

    try:
        # 抓取市場新聞
        print("正在抓取市場新聞...")
        news_df = fetch_market_news(args.query, args.days, args.server_url)

        if not news_df.empty:
            print(f"成功抓取 {len(news_df)} 筆新聞")
            print("新聞資料預覽:")
            print(news_df.head())

            # 進行情緒分析
            print("正在進行情緒分析...")
            sentiment = analyze_market_sentiment(news_df)
            print(f"情緒分析結果: {sentiment}")
        else:
            print("未抓取到任何新聞資料")

    except Exception as e:
        print(f"執行過程中發生錯誤: {e}")
        sys.exit(1)

    print("MCP 資料爬蟲執行完成")


if __name__ == "__main__":
    main()
