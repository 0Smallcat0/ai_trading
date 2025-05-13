"""
MCP 爬蟲模組

此模組負責與 MCP (Model Context Protocol) 爬蟲服務進行通信，
獲取新聞和其他網絡數據。

主要功能：
- 啟動 MCP 爬蟲服務
- 發送爬蟲請求
- 處理爬蟲結果
"""

import os
import json
import time
import logging
import subprocess
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from src.config import ROOT_DIR, LOGS_DIR, REQUEST_TIMEOUT, RETRY_COUNT

# 設定日誌
logger = logging.getLogger("mcp_crawler")

# MCP 爬蟲服務器設定
MCP_SERVER_PORT = 3000
MCP_SERVER_URL = f"http://localhost:{MCP_SERVER_PORT}"
MCP_SERVER_SCRIPT = os.path.join(ROOT_DIR, "mcp_crawler", "server.cjs")


class MCPCrawler:
    """MCP 爬蟲類，用於與 MCP 爬蟲服務進行通信"""

    def __init__(self, auto_start: bool = True):
        """
        初始化 MCP 爬蟲

        Args:
            auto_start (bool): 是否自動啟動 MCP 爬蟲服務
        """
        self.server_process = None
        self.is_running = False

        # 如果自動啟動，則啟動 MCP 爬蟲服務
        if auto_start:
            self.start_server()

    def start_server(self) -> bool:
        """
        啟動 MCP 爬蟲服務

        Returns:
            bool: 是否成功啟動
        """
        if self.is_running:
            logger.warning("MCP 爬蟲服務已經在運行中")
            return True

        try:
            # 檢查 Node.js 是否安裝
            node_version = subprocess.check_output(["node", "--version"], text=True)
            logger.info(f"Node.js 版本: {node_version.strip()}")

            # 檢查 MCP 爬蟲服務器腳本是否存在
            if not os.path.exists(MCP_SERVER_SCRIPT):
                logger.error(f"MCP 爬蟲服務器腳本不存在: {MCP_SERVER_SCRIPT}")
                return False

            # 啟動 MCP 爬蟲服務器
            logger.info(f"啟動 MCP 爬蟲服務器: {MCP_SERVER_SCRIPT}")

            # 使用非阻塞方式啟動服務器
            self.server_process = subprocess.Popen(
                ["node", MCP_SERVER_SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.dirname(MCP_SERVER_SCRIPT),
            )

            # 等待服務器啟動
            time.sleep(2)

            # 檢查服務器是否正常運行
            for _ in range(RETRY_COUNT):
                try:
                    response = requests.get(MCP_SERVER_URL, timeout=REQUEST_TIMEOUT)
                    if response.status_code == 200:
                        self.is_running = True
                        logger.info("MCP 爬蟲服務器已成功啟動")
                        return True
                except requests.RequestException:
                    time.sleep(1)

            logger.error("MCP 爬蟲服務器啟動失敗")
            return False
        except Exception as e:
            logger.error(f"啟動 MCP 爬蟲服務器時發生錯誤: {e}")
            return False

    def stop_server(self) -> bool:
        """
        停止 MCP 爬蟲服務

        Returns:
            bool: 是否成功停止
        """
        if not self.is_running or self.server_process is None:
            logger.warning("MCP 爬蟲服務尚未啟動")
            return True

        try:
            # 終止服務器進程
            self.server_process.terminate()
            self.server_process.wait(timeout=5)
            self.is_running = False
            self.server_process = None
            logger.info("MCP 爬蟲服務器已停止")
            return True
        except Exception as e:
            logger.error(f"停止 MCP 爬蟲服務器時發生錯誤: {e}")
            return False

    def crawl_news(
        self,
        query: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        fulltext: bool = False,
        only_urls: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        爬取新聞

        Args:
            query (str): 查詢關鍵字
            start_date (str, optional): 開始日期，格式為 YYYY-MM-DD
            end_date (str, optional): 結束日期，格式為 YYYY-MM-DD
            fulltext (bool): 是否獲取全文
            only_urls (bool): 是否只返回 URL 列表

        Returns:
            List[Dict[str, Any]]: 新聞列表
        """
        if not self.is_running:
            logger.warning("MCP 爬蟲服務尚未啟動，嘗試啟動...")
            if not self.start_server():
                logger.error("無法啟動 MCP 爬蟲服務，爬取新聞失敗")
                return []

        # 設定日期範圍
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        # 準備請求參數
        params = {
            "query": query,
            "start_date": start_date,
            "end_date": end_date,
            "fulltext": fulltext,
            "only_urls": only_urls,
        }

        # 發送 JSON-RPC 請求
        try:
            response = requests.post(
                MCP_SERVER_URL,
                json={
                    "jsonrpc": "2.0",
                    "method": "crawl_perplexity",
                    "params": params,
                    "id": 1,
                },
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    logger.info(f"成功爬取 {len(result['result'])} 條新聞")
                    return result["result"]
                else:
                    logger.error(f"爬取新聞失敗: {result.get('error')}")
            else:
                logger.error(f"爬取新聞請求失敗: {response.status_code}")
        except Exception as e:
            logger.error(f"爬取新聞時發生錯誤: {e}")

        return []


# 單例模式
_crawler_instance = None


def get_crawler() -> MCPCrawler:
    """
    獲取 MCP 爬蟲實例

    Returns:
        MCPCrawler: MCP 爬蟲實例
    """
    global _crawler_instance
    if _crawler_instance is None:
        _crawler_instance = MCPCrawler()
    return _crawler_instance


def crawl_stock_news(
    stock_id: str, days: int = 7, fulltext: bool = False
) -> List[Dict[str, Any]]:
    """
    爬取股票相關新聞的便捷函數

    Args:
        stock_id (str): 股票代號
        days (int): 往前查詢的天數
        fulltext (bool): 是否獲取全文

    Returns:
        List[Dict[str, Any]]: 新聞列表
    """
    crawler = get_crawler()
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    return crawler.crawl_news(
        query=f"{stock_id} 股票",
        start_date=start_date,
        end_date=end_date,
        fulltext=fulltext,
    )
