"""
初始化工作流腳本

此腳本用於初始化n8n工作流，包括創建默認工作流和啟動監控。
"""

import argparse
import os
import sys
import time
from typing import Dict, Optional

from src.core.logger import logger
from src.integration.workflows.manager import workflow_manager

# 添加項目根目錄到路徑
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
)


def init_workflows(
    n8n_url: Optional[str] = None,
    api_key: Optional[str] = None,
    activate: bool = False,
    monitor: bool = False,
) -> Dict[str, str]:
    """
    初始化工作流

    Args:
        n8n_url: n8n URL
        api_key: API密鑰
        activate: 是否激活工作流
        monitor: 是否啟動監控

    Returns:
        Dict[str, str]: 工作流ID字典
    """
    # 初始化工作流管理器
    if n8n_url or api_key:
        workflow_manager.__init__(n8n_url, api_key)

    # 設置默認工作流
    workflow_ids = workflow_manager.setup_default_workflows()

    # 激活工作流
    if activate:
        for workflow_id in workflow_ids.values():
            workflow_manager.activate_workflow(workflow_id)
            logger.info("已激活工作流: %s", workflow_id)

    # 啟動監控
    if monitor:
        workflow_manager.start_monitoring()

    return workflow_ids


def main():
    """主函數"""
    # 解析命令行參數
    parser = argparse.ArgumentParser(description="初始化n8n工作流")
    parser.add_argument("--n8n-url", help="n8n URL")
    parser.add_argument("--api-key", help="API密鑰")
    parser.add_argument("--activate", action="store_true", help="激活工作流")
    parser.add_argument("--monitor", action="store_true", help="啟動監控")
    args = parser.parse_args()

    # 初始化工作流
    workflow_ids = init_workflows(
        n8n_url=args.n8n_url,
        api_key=args.api_key,
        activate=args.activate,
        monitor=args.monitor,
    )

    # 輸出工作流ID
    logger.info("已創建工作流: %s", workflow_ids)

    # 如果啟動了監控，則保持腳本運行
    if args.monitor:
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            workflow_manager.stop_monitoring()
            logger.info("已停止監控")


if __name__ == "__main__":
    main()
