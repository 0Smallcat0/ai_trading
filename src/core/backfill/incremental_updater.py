"""增量更新識別模組。

此模組實作增量更新識別模式，包括：
- 智能識別需要更新的數據
- 比較本地與遠端數據時間戳
- 支援部分更新
- 處理數據版本控制和衝突解決
"""

import datetime
import hashlib
import logging
from typing import Any, Dict, List, Tuple, Union

import pandas as pd

from .data_structures import IncrementalUpdateInfo

logger = logging.getLogger(__name__)


class IncrementalUpdater:
    """增量更新識別器。"""

    def __init__(self, data_manager=None):
        """初始化增量更新識別器。

        Args:
            data_manager: 數據管理器實例
        """
        self.data_manager = data_manager

    def detect_incremental_updates(
        self,
        symbols: Union[str, List[str]],
        start_date: Union[str, datetime.date],
        end_date: Union[str, datetime.date],
    ) -> Dict[str, IncrementalUpdateInfo]:
        """執行增量更新檢測。

        Args:
            symbols: 股票代碼或代碼列表
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            Dict[str, IncrementalUpdateInfo]: 每個股票的增量更新資訊
        """
        # 標準化輸入
        symbols = self._normalize_symbols(symbols)
        start_date = self._normalize_date(start_date)
        end_date = self._normalize_date(end_date)

        logger.info("開始增量更新檢測：%d 個股票", len(symbols))

        update_info = {}

        for symbol in symbols:
            # 獲取本地數據資訊
            local_info = self._get_local_data_info(symbol, start_date, end_date)

            # 獲取遠端數據資訊
            remote_info = self._get_remote_data_info(symbol, start_date, end_date)

            # 比較並決定更新策略
            incremental_info = self._compare_and_decide_update(
                symbol, local_info, remote_info, start_date, end_date
            )

            update_info[symbol] = incremental_info

            logger.debug(
                "%s: 需要更新=%s, 更新範圍=%d",
                symbol,
                incremental_info.needs_update,
                len(incremental_info.update_ranges),
            )

        needs_update_count = sum(
            1 for info in update_info.values() if info.needs_update
        )
        logger.info("增量更新檢測完成，%d 個股票需要更新", needs_update_count)

        return update_info

    def _normalize_symbols(self, symbols: Union[str, List[str]]) -> List[str]:
        """標準化股票代碼列表。"""
        if isinstance(symbols, str):
            return [symbols]
        return symbols

    def _normalize_date(self, date: Union[str, datetime.date]) -> datetime.date:
        """標準化日期格式。"""
        if isinstance(date, str):
            return datetime.datetime.strptime(date, "%Y-%m-%d").date()
        return date

    def _get_local_data_info(
        self, symbol: str, start_date: datetime.date, end_date: datetime.date
    ) -> Dict[str, Any]:
        """獲取本地數據資訊。

        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            Dict[str, Any]: 本地數據資訊
        """
        try:
            # 嘗試從快取或數據庫載入現有數據
            from src.core.data_ingest import load_data

            existing_data = load_data(symbol, start_date, end_date)

            if existing_data is not None and not existing_data.empty:
                return self._extract_data_info(existing_data, True)

            return self._create_empty_data_info()

        except Exception as exc:
            logger.warning("獲取 %s 本地數據資訊失敗: %s", symbol, exc)
            return self._create_empty_data_info()

    def _extract_data_info(
        self, data: pd.DataFrame, is_local: bool = True
    ) -> Dict[str, Any]:
        """從數據中提取資訊。"""
        # 計算數據校驗碼
        data_str = data.to_string()
        checksum = hashlib.md5(data_str.encode(), usedforsecurity=False).hexdigest()

        # 獲取最後更新時間
        last_date = data.index.max()
        if isinstance(last_date, str):
            last_date = pd.to_datetime(last_date)

        return {
            "exists": True,
            "last_date": (
                last_date.date() if hasattr(last_date, "date") else last_date
            ),
            "record_count": len(data),
            "checksum": checksum,
            "data_range": (
                (data.index.min().date(), data.index.max().date()) if is_local else None
            ),
        }

    def _create_empty_data_info(self) -> Dict[str, Any]:
        """創建空數據資訊。"""
        return {
            "exists": False,
            "last_date": None,
            "record_count": 0,
            "checksum": None,
            "data_range": None,
        }

    def _get_remote_data_info(
        self, symbol: str, start_date: datetime.date, end_date: datetime.date
    ) -> Dict[str, Any]:
        """獲取遠端數據資訊。

        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            Dict[str, Any]: 遠端數據資訊
        """
        try:
            # 獲取最新的交易日期
            from src.utils.utils import get_trading_dates

            trading_dates = get_trading_dates(start_date, end_date)
            latest_trading_date = max(trading_dates) if trading_dates else end_date

            return {
                "available": True,
                "latest_date": latest_trading_date,
                "estimated_records": len(trading_dates),
                "last_modified": datetime.datetime.now(),
            }

        except Exception as exc:
            logger.warning("獲取 %s 遠端數據資訊失敗: %s", symbol, exc)
            return {
                "available": False,
                "latest_date": None,
                "estimated_records": 0,
                "last_modified": None,
            }

    def _compare_and_decide_update(
        self,
        symbol: str,
        local_info: Dict[str, Any],
        remote_info: Dict[str, Any],
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> IncrementalUpdateInfo:
        """比較本地和遠端數據，決定更新策略。

        Args:
            symbol: 股票代碼
            local_info: 本地數據資訊
            remote_info: 遠端數據資訊
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            IncrementalUpdateInfo: 增量更新資訊
        """
        update_info = IncrementalUpdateInfo(symbol=symbol)

        # 如果本地沒有數據，需要全量下載
        if not local_info["exists"]:
            update_info.needs_update = True
            update_info.update_ranges = [(start_date, end_date)]
            logger.debug("%s: 本地無數據，需要全量下載", symbol)
            return update_info

        # 如果遠端沒有數據，不需要更新
        if not remote_info["available"]:
            update_info.needs_update = False
            logger.debug("%s: 遠端無數據，不需要更新", symbol)
            return update_info

        # 比較日期範圍，找出缺失的部分
        update_ranges = self._calculate_missing_ranges(
            local_info, remote_info, start_date, end_date
        )

        if update_ranges:
            update_info.needs_update = True
            update_info.update_ranges = update_ranges
            update_info.last_update = datetime.datetime.now()
            logger.debug("%s: 需要增量更新，範圍: %s", symbol, update_ranges)
        else:
            update_info.needs_update = False
            logger.debug("%s: 數據已是最新，無需更新", symbol)

        return update_info

    def _calculate_missing_ranges(
        self,
        local_info: Dict[str, Any],
        remote_info: Dict[str, Any],
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> List[Tuple[datetime.date, datetime.date]]:
        """計算缺失的日期範圍。"""
        update_ranges = []

        if not local_info.get("data_range"):
            return [(start_date, end_date)]

        local_start, local_end = local_info["data_range"]
        remote_latest = remote_info["latest_date"]

        # 檢查開始日期之前的缺失
        if start_date < local_start:
            update_ranges.append((start_date, local_start - datetime.timedelta(days=1)))

        # 檢查結束日期之後的缺失
        if local_end < remote_latest and local_end < end_date:
            range_start = local_end + datetime.timedelta(days=1)
            range_end = min(remote_latest, end_date)
            if range_start <= range_end:
                update_ranges.append((range_start, range_end))

        return update_ranges

    def resolve_conflicts(
        self,
        symbol: str,
        local_data: pd.DataFrame,
        remote_data: pd.DataFrame,
        strategy: str = "remote_wins",
    ) -> pd.DataFrame:
        """解決數據衝突。

        Args:
            symbol: 股票代碼
            local_data: 本地數據
            remote_data: 遠端數據
            strategy: 衝突解決策略

        Returns:
            pd.DataFrame: 解決衝突後的數據
        """
        if strategy == "remote_wins":
            return remote_data
        elif strategy == "local_wins":
            return local_data
        elif strategy == "merge":
            return self._merge_data(local_data, remote_data)
        else:
            logger.warning("未知的衝突解決策略: %s，使用 remote_wins", strategy)
            return remote_data

    def _merge_data(
        self, local_data: pd.DataFrame, remote_data: pd.DataFrame
    ) -> pd.DataFrame:
        """合併本地和遠端數據。"""
        # 簡單的合併策略：遠端數據優先，但保留本地獨有的數據
        combined = pd.concat([local_data, remote_data])
        # 移除重複項，保留最後的（遠端的）
        combined = combined[~combined.index.duplicated(keep="last")]
        return combined.sort_index()
