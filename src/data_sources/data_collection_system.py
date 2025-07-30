"""資料收集系統模組

此模組整合了所有資料收集器，提供統一的介面來管理資料收集任務，包括：
- 排程管理
- 資料收集任務協調
- 錯誤處理與通知
- 資料驗證與儲存

支援多種資料類型和來源的收集，並提供靈活的配置選項。
"""

import logging
from typing import Any, Dict, List, Optional

from src.data_sources.collection_config import CollectionConfigManager
from src.data_sources.collection_executor import CollectionExecutor
from src.data_sources.collector_manager import CollectorManager

# 設定日誌
logger = logging.getLogger(__name__)


class DataCollectionSystem:
    """資料收集系統

    整合所有資料收集器，提供統一的介面來管理資料收集任務。
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        symbols: Optional[List[str]] = None,
    ):
        """初始化資料收集系統

        Args:
            config_path: 配置檔案路徑，如果為 None 則使用預設配置
            symbols: 股票代碼列表，如果為 None 則從配置檔案讀取
        """
        # 初始化配置管理器
        self.config_manager = CollectionConfigManager()
        self.config = self.config_manager.load_config(config_path)
        self.symbols = symbols or self.config.get("symbols", [])

        # 初始化收集器管理器
        self.collector_manager = CollectorManager(self.config, self.symbols)
        self.collector_manager.initialize_collectors()

        # 初始化執行器
        self.executor = CollectionExecutor(
            self.config,
            self.collector_manager.collectors,
            self.symbols
        )

    def setup_schedules(self) -> None:
        """設定所有收集器的排程"""
        self.collector_manager.setup_schedules()

    def start(self) -> None:
        """啟動資料收集系統"""
        self.collector_manager.start_all()

    def stop(self) -> None:
        """停止資料收集系統"""
        self.collector_manager.stop_all()

    def collect_all(self) -> None:
        """立即收集所有資料"""
        self.executor.collect_all_data()

    def get_status(self) -> Dict[str, Any]:
        """獲取資料收集系統狀態

        Returns:
            Dict[str, Any]: 系統狀態
        """
        return self.collector_manager.get_status()

    def save_config(self, config_path: str) -> bool:
        """儲存配置到檔案

        Args:
            config_path: 配置檔案路徑

        Returns:
            bool: 是否儲存成功
        """
        return self.config_manager.save_config(self.config, config_path)

    def update_symbols(self, symbols: List[str]) -> None:
        """更新股票代碼列表

        Args:
            symbols: 新的股票代碼列表
        """
        self.symbols = symbols
        # 更新收集器管理器的股票列表
        self.collector_manager.symbols = symbols
        # 更新執行器的股票列表
        self.executor.symbols = symbols
        logger.info("已更新股票代碼列表，共 %d 檔股票", len(symbols))
