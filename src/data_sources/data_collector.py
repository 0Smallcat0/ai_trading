"""資料收集器基礎模組

此模組提供資料收集的基礎類別和功能，包括：
- 資料收集器基礎類別
- 重試機制
- 錯誤處理
- 資料驗證

所有特定類型的資料收集器都應該繼承自基礎類別。
"""

import logging

from src.data_sources.base_collector import BaseDataCollector
from src.data_sources.scheduler_mixin import SchedulerMixin

# 設定日誌
logger = logging.getLogger(__name__)


class DataCollector(BaseDataCollector, SchedulerMixin):
    """資料收集器基礎類別

    提供資料收集的通用功能，包括重試機制、錯誤處理、資料驗證等。
    結合了基礎收集器和排程功能。
    """

    def __init__(
        self,
        name: str,
        source: str,
        **kwargs
    ):
        """初始化資料收集器

        Args:
            name: 收集器名稱
            source: 資料來源名稱
            **kwargs: 其他參數，傳遞給基礎類別
        """
        super().__init__(name=name, source=source, **kwargs)
