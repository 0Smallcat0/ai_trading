#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pytest: skip-file

"""
MCP服務器連接測試腳本

此腳本用於測試MCP服務器連接，確保MCP服務器正常運行，
並且可以正確調用MCP工具。
"""

import os
import sys
import time
import requests
import argparse
import logging
import subprocess

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("test_mcp_connection.log"), logging.StreamHandler()],
)
logger = logging.getLogger("test_mcp_connection")

# MCP服務器配置
DEFAULT_MCP_SERVER_PATH = os.path.expanduser(
    "~/AppData/Roaming/Roo-Code/MCP/perplexity-crawler/server.js"
)
DEFAULT_MCP_SERVER_URL = "http://localhost:3000"
DEFAULT_MCP_SERVER_PORT = 3000

# 確保路徑正確
if not os.path.exists(DEFAULT_MCP_SERVER_PATH):
    # 嘗試修正路徑
    possible_paths = [
        os.path.expanduser(
            "~/AppData/Roaming/Roo-Code/MCP/perplexity-crawler/server.js"
        ),
        "C:/Users/User/AppData/Roaming/Roo-Code/MCP/perplexity-crawler/server.js",
        "./server.js",
    ]

    for path in possible_paths:
        if os.path.exists(path):
            DEFAULT_MCP_SERVER_PATH = path
            print(f"找到MCP服務器路徑: {DEFAULT_MCP_SERVER_PATH}")
            break
    else:
        print(f"警告: 無法找到MCP服務器路徑: {DEFAULT_MCP_SERVER_PATH}")
        print(f"請確保路徑正確，或使用--mcp-server-path參數指定正確路徑")
DEFAULT_MCP_SERVER_URL = "http://localhost:3000"


def parse_args():
    """解析命令行參數"""
    parser = argparse.ArgumentParser(description="MCP服務器連接測試腳本")

    parser.add_argument(
        "--mcp-server-url",
        type=str,
        default=DEFAULT_MCP_SERVER_URL,
        help="MCP服務器URL",
    )
    parser.add_argument(
        "--mcp-server-path",
        type=str,
        default=DEFAULT_MCP_SERVER_PATH,
        help="MCP服務器路徑",
    )
    parser.add_argument(
        "--mcp-server-port",
        type=int,
        default=DEFAULT_MCP_SERVER_PORT,
        help="MCP服務器端口",
    )
    parser.add_argument("--start-server", action="store_true", help="啟動MCP服務器")
    parser.add_argument("--debug", action="store_true", help="啟用調試模式")
    parser.add_argument("--check-dependencies", action="store_true", help="檢查依賴項")

    return parser.parse_args()


def check_node_js():
    """檢查Node.js是否可用"""
    try:
        node_version = subprocess.check_output(["node", "--version"], text=True).strip()
        logger.info(f"Node.js版本: {node_version}")
        return True
    except Exception as e:
        logger.error(f"無法執行Node.js: {e}")
        return False


def check_mcp_server_path(server_path):
    """檢查MCP服務器路徑是否存在"""
    if os.path.exists(server_path):
        logger.info(f"MCP服務器路徑存在: {server_path}")
        return True
    else:
        logger.error(f"MCP服務器路徑不存在: {server_path}")
        return False


def check_mcp_server_connection(url):
    """檢查MCP服務器連接"""
    try:
        response = requests.post(
            url,
            json={"jsonrpc": "2.0", "method": "list_tools", "params": {}, "id": 1},
            timeout=5,
        )
        if response.status_code == 200:
            result = response.json()
            if "result" in result and "tools" in result["result"]:
                tools = result["result"]["tools"]
                logger.info(f"MCP服務器連接成功，可用工具數量: {len(tools)}")
                return True
        logger.error(f"MCP服務器連接失敗: HTTP狀態碼 {response.status_code}")
        return False
    except Exception as e:
        logger.error(f"檢查MCP服務器連接時出錯: {e}")
        return False


def check_dependencies():
    """檢查依賴項"""
    logger.info("檢查依賴項...")

    # 檢查Node.js
    if not check_node_js():
        return False

    # 檢查npm包
    try:
        # 獲取MCP服務器目錄
        server_dir = os.path.dirname(DEFAULT_MCP_SERVER_PATH)

        # 檢查package.json
        package_json_path = os.path.join(server_dir, "package.json")
        if not os.path.exists(package_json_path):
            logger.error(f"找不到package.json: {package_json_path}")
            return False

        # 檢查node_modules
        node_modules_path = os.path.join(server_dir, "node_modules")
        if not os.path.exists(node_modules_path):
            logger.warning(f"找不到node_modules: {node_modules_path}")
            logger.warning("嘗試安裝依賴項...")

            try:
                subprocess.run(["npm", "install"], cwd=server_dir, check=True)
                logger.info("依賴項安裝成功")
            except Exception as e:
                logger.error(f"安裝依賴項時出錯: {e}")
                return False

        logger.info("依賴項檢查通過")
        return True
    except Exception as e:
        logger.error(f"檢查依賴項時出錯: {e}")
        return False


def start_mcp_server(server_path, port=DEFAULT_MCP_SERVER_PORT):
    """啟動MCP服務器"""
    logger.info(f"啟動MCP服務器: {server_path}, 端口: {port}")

    try:
        # 檢查端口是否被佔用
        import socket

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("localhost", port))
            s.close()
        except socket.error:
            logger.error(f"端口 {port} 已被佔用")
            # 嘗試使用其他端口
            for alt_port in range(3001, 3010):
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.bind(("localhost", alt_port))
                    s.close()
                    port = alt_port
                    logger.info(f"使用替代端口: {port}")
                    break
                except socket.error:
                    continue
            else:
                logger.error("無法找到可用端口")
                return None

        # 使用node執行server.js
        server_dir = os.path.dirname(server_path)

        # 創建命令
        cmd = ["node", server_path]
        if port != DEFAULT_MCP_SERVER_PORT:
            # 如果server.js支持端口參數
            cmd.extend(["--port", str(port)])

        logger.info(f"執行命令: {' '.join(cmd)}")

        # 啟動進程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=server_dir,
        )

        # 等待服務器啟動
        server_url = f"http://localhost:{port}"
        for i in range(10):
            logger.info(f"等待MCP服務器啟動 ({i+1}/10)...")

            # 檢查進程是否還在運行
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                logger.error(f"MCP服務器進程已退出，返回碼: {process.returncode}")
                logger.error(f"標準輸出: {stdout}")
                logger.error(f"標準錯誤: {stderr}")
                return None

            # 檢查服務器是否可連接
            if check_mcp_server_connection(server_url):
                logger.info("MCP服務器已成功啟動")
                return process, server_url

            time.sleep(1)

        # 如果超時，獲取輸出和錯誤
        stdout, stderr = process.communicate(timeout=1)
        logger.error("MCP服務器啟動超時")
        logger.error(f"標準輸出: {stdout}")
        logger.error(f"標準錯誤: {stderr}")

        process.terminate()
        return None
    except Exception as e:
        logger.error(f"啟動MCP服務器時出錯: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return None


def main():
    """主函數"""
    args = parse_args()

    # 如果啟用調試模式，設置日誌級別為DEBUG
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("調試模式已啟用")

    logger.info("開始測試MCP服務器連接...")

    # 檢查Node.js
    if not check_node_js():
        logger.error("請安裝Node.js")
        return 1

    # 檢查MCP服務器路徑
    if not check_mcp_server_path(args.mcp_server_path):
        logger.error("請確保MCP服務器路徑正確")
        return 1

    # 檢查依賴項
    if args.check_dependencies:
        if not check_dependencies():
            logger.error("依賴項檢查失敗")
            return 1

    # 啟動MCP服務器
    mcp_process = None
    server_url = args.mcp_server_url

    if args.start_server:
        result = start_mcp_server(args.mcp_server_path, args.mcp_server_port)
        if not result:
            logger.error("無法啟動MCP服務器")
            return 1

        mcp_process, server_url = result

    try:
        # 檢查MCP服務器連接
        if not check_mcp_server_connection(server_url):
            logger.error(f"無法連接到MCP服務器: {server_url}")
            return 1

        logger.info("MCP服務器連接測試成功")
        return 0
    finally:
        # 停止MCP服務器
        if mcp_process:
            logger.info("停止MCP服務器")
            try:
                mcp_process.terminate()
                mcp_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("MCP服務器未能正常終止，強制終止")
                mcp_process.kill()
            logger.info("MCP服務器已停止")


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("使用者中斷執行")
        sys.exit(1)
    except Exception as e:
        logger.error(f"未處理的異常: {e}")
        sys.exit(1)
