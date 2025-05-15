"""
資料收集系統命令列介面

此模組提供資料收集系統的命令列介面，方便使用者透過命令列操作資料收集系統。
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.config import CONFIG_DIR
from src.data_sources.data_collection_system import DataCollectionSystem

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(CONFIG_DIR, "data_collection.log")),
    ],
)
logger = logging.getLogger(__name__)


def parse_args():
    """解析命令列參數"""
    parser = argparse.ArgumentParser(description="資料收集系統命令列介面")
    
    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # start 命令
    start_parser = subparsers.add_parser("start", help="啟動資料收集系統")
    start_parser.add_argument("--config", "-c", help="配置檔案路徑")
    start_parser.add_argument("--symbols", "-s", nargs="+", help="股票代碼列表")
    
    # stop 命令
    stop_parser = subparsers.add_parser("stop", help="停止資料收集系統")
    
    # status 命令
    status_parser = subparsers.add_parser("status", help="查詢資料收集系統狀態")
    
    # collect 命令
    collect_parser = subparsers.add_parser("collect", help="立即收集資料")
    collect_parser.add_argument("--type", "-t", choices=["all", "market", "financial", "news"], default="all", help="收集資料類型")
    collect_parser.add_argument("--symbols", "-s", nargs="+", help="股票代碼列表")
    
    # config 命令
    config_parser = subparsers.add_parser("config", help="管理配置")
    config_parser.add_argument("--show", action="store_true", help="顯示當前配置")
    config_parser.add_argument("--save", help="儲存配置到檔案")
    config_parser.add_argument("--update", help="更新配置，格式為 JSON 字串")
    
    return parser.parse_args()


def main():
    """主函數"""
    args = parse_args()
    
    # 預設配置檔案路徑
    default_config_path = os.path.join(CONFIG_DIR, "data_collection_config.json")
    
    # 根據命令執行對應操作
    if args.command == "start":
        # 啟動資料收集系統
        config_path = args.config or default_config_path
        symbols = args.symbols
        
        system = DataCollectionSystem(config_path=config_path, symbols=symbols)
        system.setup_schedules()
        system.start()
        
        # 保持程式運行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("接收到中斷信號，停止資料收集系統")
            system.stop()
            
    elif args.command == "stop":
        # 停止資料收集系統
        # 這裡需要一個方法來找到正在運行的系統實例
        # 由於這是一個簡單的 CLI，我們可以使用一個 PID 檔案來記錄
        pid_file = os.path.join(CONFIG_DIR, "data_collection.pid")
        if os.path.exists(pid_file):
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
            
            # 在 Windows 上使用 taskkill 命令
            if sys.platform == "win32":
                os.system(f"taskkill /PID {pid} /F")
            # 在 Unix 上使用 kill 命令
            else:
                os.system(f"kill {pid}")
                
            os.remove(pid_file)
            logger.info(f"已停止 PID 為 {pid} 的資料收集系統")
        else:
            logger.warning("找不到正在運行的資料收集系統")
            
    elif args.command == "status":
        # 查詢資料收集系統狀態
        # 這裡需要一個方法來找到正在運行的系統實例
        # 由於這是一個簡單的 CLI，我們可以使用一個狀態檔案來記錄
        status_file = os.path.join(CONFIG_DIR, "data_collection_status.json")
        if os.path.exists(status_file):
            with open(status_file, "r") as f:
                status = json.load(f)
            
            # 格式化輸出
            print("資料收集系統狀態:")
            print(f"運行中: {status['running']}")
            print(f"股票數量: {status['symbol_count']}")
            print("收集器狀態:")
            for name, collector_status in status["collectors"].items():
                print(f"  {name}:")
                print(f"    最後執行時間: {collector_status['last_run_time']}")
                print(f"    最後執行狀態: {collector_status['last_run_status']}")
                print(f"    錯誤次數: {collector_status['error_count']}")
                print(f"    成功次數: {collector_status['success_count']}")
        else:
            logger.warning("找不到資料收集系統狀態檔案")
            
    elif args.command == "collect":
        # 立即收集資料
        config_path = default_config_path
        symbols = args.symbols
        
        system = DataCollectionSystem(config_path=config_path, symbols=symbols)
        
        if args.type == "all":
            system.collect_all()
        elif args.type == "market":
            if "market_data" in system.collectors:
                system.collectors["market_data"].trigger_now(system.symbols, data_type="daily")
                logger.info("已觸發市場日線資料收集")
        elif args.type == "financial":
            if "financial_statement" in system.collectors:
                system.collectors["financial_statement"].trigger_now(system.symbols, data_type="company_info")
                logger.info("已觸發財務報表資料收集")
        elif args.type == "news":
            if "news_sentiment" in system.collectors:
                system.collectors["news_sentiment"].trigger_now(system.symbols, days=1)
                logger.info("已觸發新聞情緒資料收集")
                
    elif args.command == "config":
        # 管理配置
        config_path = default_config_path
        
        if args.show:
            # 顯示當前配置
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
                print(json.dumps(config, indent=4, ensure_ascii=False))
            else:
                logger.warning(f"找不到配置檔案: {config_path}")
                
        elif args.save:
            # 儲存配置到檔案
            system = DataCollectionSystem(config_path=config_path)
            system.save_config(args.save)
            
        elif args.update:
            # 更新配置
            try:
                update_config = json.loads(args.update)
                
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        config = json.load(f)
                else:
                    config = {}
                
                # 更新配置
                for key, value in update_config.items():
                    config[key] = value
                
                # 儲存配置
                with open(config_path, "w") as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                    
                logger.info(f"已更新配置並儲存到 {config_path}")
            except json.JSONDecodeError:
                logger.error(f"無效的 JSON 字串: {args.update}")
    else:
        # 顯示幫助
        parse_args()


if __name__ == "__main__":
    # 記錄 PID
    pid_file = os.path.join(CONFIG_DIR, "data_collection.pid")
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))
    
    try:
        main()
    finally:
        # 清理 PID 檔案
        if os.path.exists(pid_file):
            os.remove(pid_file)
"""
