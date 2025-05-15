#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MCP自動交易系統啟動腳本

此腳本用於啟動MCP服務器並執行自動交易系統。
它會先檢查MCP服務器是否已啟動，如果沒有則啟動它，
然後執行自動交易系統的主程式。
"""

import os
import subprocess
import sys
import time

try:
    import requests
except ImportError:
    print("請先安裝 requests 套件：pip install requests")
    raise
import argparse
import logging
import signal
from logging.handlers import RotatingFileHandler

# 設定日誌
logger = logging.getLogger("start_mcp_trading")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler = RotatingFileHandler(
    "start_mcp_trading.log", maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
file_handler.setFormatter(formatter)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

# 集中管理 log 訊息，方便多語系擴充
LOG_MSGS = {
    "start_mcp": "啟動MCP服務器: {path}",
    "mcp_path_not_exist": "MCP服務器路徑不存在: {path}",
    "node_version": "Node.js版本: {version}",
    "node_fail": "無法執行Node.js: {error}",
    "run_cmd": "執行命令: {cmd}",
    "wait_mcp": "等待MCP服務器啟動 ({i}/10)...",
    "mcp_started": "MCP服務器已成功啟動",
    "mcp_timeout": "MCP服務器啟動超時",
    "mcp_output": "MCP服務器輸出: {stdout}",
    "mcp_error": "MCP服務器錯誤: {stderr}",
    "mcp_exit": "MCP服務器進程已退出，返回碼: {code}",
    "mcp_stopped": "MCP服務器已停止",
    "mcp_stop_force": "MCP服務器未能正常終止，強制終止",
    "crawler_start": "執行爬蟲",
    "crawler_finish": "爬蟲執行完成",
    "crawler_fail": "執行爬蟲時出錯: {error}",
    "trading_start": "執行交易系統",
    "trading_finish": "交易系統執行完成",
    "trading_fail": "執行交易系統時出錯: {error}",
    "user_interrupt": "使用者中斷執行",
    "main_fail": "執行過程中發生錯誤: {error}",
    "mcp_not_start": "無法啟動MCP服務器，退出",
    "crawler_only": "只執行爬蟲，不執行交易系統",
    "mcp_running": "MCP服務器已啟動",
    "mcp_not_running": "MCP服務器未啟動或無法連接",
    "debug_on": "調試模式已啟用",
}

# MCP服務器配置
MCP_SERVER_PATH = os.path.expanduser(
    "~/AppData/Roaming/Roo-Code/MCP/perplexity-crawler/server.js"
)
MCP_SERVER_URL = "http://localhost:3000"
MCP_SERVER_PROCESS = None


def parse_args():
    """解析命令行參數"""
    parser = argparse.ArgumentParser(description="MCP自動交易系統啟動腳本")

    # 模式參數
    parser.add_argument(
        "--mode",
        type=str,
        default="backtest",
        choices=["backtest", "paper", "live"],
        help="交易模式：backtest（回測）、paper（模擬交易）、live（實盤交易）",
    )

    # 資料參數
    parser.add_argument(
        "--start-date", type=str, default=None, help="開始日期，格式：YYYY-MM-DD"
    )
    parser.add_argument(
        "--end-date", type=str, default=None, help="結束日期，格式：YYYY-MM-DD"
    )
    parser.add_argument("--update-data", action="store_true", help="是否更新資料")

    # MCP參數
    parser.add_argument(
        "--mcp-server-url", type=str, default=MCP_SERVER_URL, help="MCP服務器URL"
    )
    parser.add_argument(
        "--mcp-server-path", type=str, default=MCP_SERVER_PATH, help="MCP服務器路徑"
    )
    parser.add_argument(
        "--no-start-mcp", action="store_true", help="不啟動MCP服務器（假設已經啟動）"
    )
    parser.add_argument("--debug", action="store_true", help="啟用調試模式")

    # 其他參數
    parser.add_argument(
        "--only-crawler", action="store_true", help="只執行爬蟲，不執行交易系統"
    )

    return parser.parse_args()


def check_mcp_server(url=MCP_SERVER_URL):
    """檢查MCP服務器是否已啟動"""
    try:
        response = requests.post(
            url,
            json={"jsonrpc": "2.0", "method": "list_tools", "params": {}, "id": 1},
            timeout=5,
        )

        if response.status_code == 200:
            result = response.json()
            if "result" in result and "tools" in result["result"]:
                logger.info(LOG_MSGS["mcp_running"])
                return True
    except Exception as e:
        logger.debug(f"檢查MCP服務器時出錯: {e}")

    logger.info(LOG_MSGS["mcp_not_running"])
    return False


def start_mcp_server(server_path=MCP_SERVER_PATH, debug=False):
    """啟動MCP服務器"""
    global MCP_SERVER_PROCESS

    logger.info(LOG_MSGS["start_mcp"].format(path=server_path))

    # 檢查服務器路徑是否存在
    if not os.path.exists(server_path):
        logger.error(LOG_MSGS["mcp_path_not_exist"].format(path=server_path))
        return False

    try:
        # 檢查node是否可用
        try:
            node_version = subprocess.check_output(
                ["node", "--version"], text=True
            ).strip()
            logger.info(LOG_MSGS["node_version"].format(version=node_version))
        except Exception as e:
            logger.error(LOG_MSGS["node_fail"].format(error=e))
            return False

        # 使用node執行server.js
        cmd = ["node", server_path]
        logger.info(LOG_MSGS["run_cmd"].format(cmd=" ".join(cmd)))

        if debug:
            # 在調試模式下，直接在前台運行，顯示所有輸出
            process = subprocess.run(cmd, check=True)
            return True
        else:
            # 在後台運行
            MCP_SERVER_PROCESS = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            # 等待服務器啟動
            for i in range(10):
                logger.info(LOG_MSGS["wait_mcp"].format(i=i + 1))
                if check_mcp_server():
                    logger.info(LOG_MSGS["mcp_started"])
                    return True
                time.sleep(3)

            # 如果超時，檢查進程是否還在運行
            if MCP_SERVER_PROCESS.poll() is None:
                logger.error(LOG_MSGS["mcp_timeout"])
                # 獲取輸出和錯誤
                stdout, stderr = MCP_SERVER_PROCESS.communicate(timeout=1)
                logger.error(LOG_MSGS["mcp_output"].format(stdout=stdout))
                logger.error(LOG_MSGS["mcp_error"].format(stderr=stderr))
            else:
                logger.error(
                    LOG_MSGS["mcp_exit"].format(code=MCP_SERVER_PROCESS.returncode)
                )
                # 獲取輸出和錯誤
                stdout, stderr = MCP_SERVER_PROCESS.communicate()
                logger.error(LOG_MSGS["mcp_output"].format(stdout=stdout))
                logger.error(LOG_MSGS["mcp_error"].format(stderr=stderr))

            return False
    except Exception as e:
        logger.error(LOG_MSGS["main_fail"].format(error=e))
        return False


def stop_mcp_server():
    """停止MCP服務器"""
    global MCP_SERVER_PROCESS

    if MCP_SERVER_PROCESS:
        logger.info(LOG_MSGS["mcp_stopped"])
        try:
            MCP_SERVER_PROCESS.terminate()
            MCP_SERVER_PROCESS.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning(LOG_MSGS["mcp_stop_force"])
            MCP_SERVER_PROCESS.kill()
        MCP_SERVER_PROCESS = None
        logger.info(LOG_MSGS["mcp_stopped"])


def run_crawler(args):
    """執行爬蟲"""
    logger.info(LOG_MSGS["crawler_start"])

    try:
        # 構建命令
        cmd = ["python", "auto_trading_project/run_crawler_mcp.py"]

        # 執行命令
        logger.info(LOG_MSGS["run_cmd"].format(cmd=" ".join(cmd)))
        process = subprocess.run(cmd, check=True)

        logger.info(LOG_MSGS["crawler_finish"])
        return True
    except Exception as e:
        logger.error(LOG_MSGS["crawler_fail"].format(error=e))
        return False


def run_trading_system(args):
    """執行交易系統"""
    logger.info(LOG_MSGS["trading_start"])

    try:
        # 構建命令
        cmd = ["python", "auto_trading_project/main_mcp.py"]

        # 添加參數
        if args.mode:
            cmd.extend(["--mode", args.mode])
        if args.start_date:
            cmd.extend(["--start-date", args.start_date])
        if args.end_date:
            cmd.extend(["--end-date", args.end_date])
        if args.update_data:
            cmd.append("--update-data")
        if args.mcp_server_url:
            cmd.extend(["--mcp-server-url", args.mcp_server_url])

        # 執行命令
        logger.info(LOG_MSGS["run_cmd"].format(cmd=" ".join(cmd)))
        process = subprocess.run(cmd, check=True)

        logger.info(LOG_MSGS["trading_finish"])
        return True
    except Exception as e:
        logger.error(LOG_MSGS["trading_fail"].format(error=e))
        return False


def signal_handler(sig, frame):
    """處理信號"""
    logger.info(LOG_MSGS["user_interrupt"])
    stop_mcp_server()
    sys.exit(0)


def main():
    """主函數"""
    # 解析命令行參數
    args = parse_args()

    # 如果啟用調試模式，設置日誌級別為DEBUG
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug(LOG_MSGS["debug_on"])

    # 註冊信號處理器
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # 檢查並啟動MCP服務器
        if not args.no_start_mcp:
            if not check_mcp_server(args.mcp_server_url):
                if not start_mcp_server(args.mcp_server_path, args.debug):
                    logger.error(LOG_MSGS["mcp_not_start"])
                    return 1

        # 執行爬蟲
        if not run_crawler(args):
            logger.error(LOG_MSGS["crawler_fail"].format(error="爬蟲執行失敗"))
            return 1

        # 如果只執行爬蟲，則退出
        if args.only_crawler:
            logger.info(LOG_MSGS["crawler_only"])
            return 0

        # 執行交易系統
        if not run_trading_system(args):
            logger.error(LOG_MSGS["trading_fail"].format(error="交易系統執行失敗"))
            return 1

        return 0
    except KeyboardInterrupt:
        logger.info(LOG_MSGS["user_interrupt"])
    except Exception as e:
        logger.error(LOG_MSGS["main_fail"].format(error=e), exc_info=True)
        return 1
    finally:
        # 停止MCP服務器
        if not args.no_start_mcp:
            stop_mcp_server()

    return 0


if __name__ == "__main__":
    sys.exit(main())
