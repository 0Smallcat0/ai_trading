"""分時段平行下載模組。

此模組實作分時段平行下載機制，包括：
- 智能時間切片
- 多線程並行下載
- 進度追蹤
- 錯誤重試機制
"""

import datetime
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
from tqdm import tqdm

from .data_structures import BackfillConfig, DownloadProgress

logger = logging.getLogger(__name__)


class ParallelDownloader:
    """分時段平行下載器。"""

    def __init__(self, config: BackfillConfig, data_manager=None):
        """初始化分時段平行下載器。

        Args:
            config: 回填配置
            data_manager: 數據管理器實例
        """
        self.config = config
        self.data_manager = data_manager
        self.progress = DownloadProgress()
        self.progress_lock = threading.Lock()

        # 初始化速率限制器
        try:
            from src.core.rate_limiter import AdaptiveRateLimiter
            self.rate_limiter = AdaptiveRateLimiter(
                max_calls=60,
                period=60,
                retry_count=config.retry_attempts,
                retry_backoff=2.0,
                jitter=0.1
            )
        except ImportError:
            logger.warning("Rate limiter not available, proceeding without it")
            self.rate_limiter = None

    def download_with_time_segments(
        self,
        symbols: Union[str, List[str]],
        start_date: Union[str, datetime.date],
        end_date: Union[str, datetime.date],
        show_progress: bool = True,
    ) -> Dict[str, pd.DataFrame]:
        """執行分時段平行下載。

        Args:
            symbols: 股票代碼或代碼列表
            start_date: 開始日期
            end_date: 結束日期
            show_progress: 是否顯示進度條

        Returns:
            Dict[str, pd.DataFrame]: 下載的資料
        """
        # 轉換輸入參數
        symbols = self._normalize_symbols(symbols)
        start_date = self._normalize_date(start_date)
        end_date = self._normalize_date(end_date)

        # 初始化進度追蹤
        self._initialize_progress(symbols, start_date, end_date)

        # 分割時間範圍
        time_chunks = self._split_date_range_optimized(start_date, end_date)

        logger.info(
            "開始分時段平行下載：%d 個股票，%d 個時間段",
            len(symbols), len(time_chunks)
        )

        # 創建下載任務
        download_tasks = self._create_download_tasks(symbols, time_chunks)

        # 並行下載
        return self._execute_parallel_download(
            download_tasks, show_progress
        )

    def _normalize_symbols(self, symbols: Union[str, List[str]]) -> List[str]:
        """標準化股票代碼列表。"""
        if isinstance(symbols, str):
            return [symbols]
        return symbols

    def _normalize_date(
        self, date: Union[str, datetime.date]
    ) -> datetime.date:
        """標準化日期格式。"""
        if isinstance(date, str):
            return datetime.datetime.strptime(date, "%Y-%m-%d").date()
        return date

    def _initialize_progress(
        self,
        symbols: List[str],
        start_date: datetime.date,
        end_date: datetime.date
    ) -> None:
        """初始化進度追蹤。"""
        if not self.config.enable_progress_tracking:
            return

        with self.progress_lock:
            self.progress = DownloadProgress(
                total_symbols=len(symbols),
                start_time=datetime.datetime.now()
            )

    def _split_date_range_optimized(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> List[Tuple[datetime.date, datetime.date]]:
        """優化的時間範圍分割方法。

        Args:
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            List[Tuple[datetime.date, datetime.date]]: 時間分塊列表
        """
        chunks = []
        current_date = start_date

        # 計算總天數
        total_days = (end_date - start_date).days

        # 根據總天數動態調整分塊大小
        chunk_size = self._calculate_optimal_chunk_size(total_days)

        while current_date <= end_date:
            chunk_end = min(
                current_date + datetime.timedelta(days=chunk_size - 1),
                end_date
            )
            chunks.append((current_date, chunk_end))
            current_date = chunk_end + datetime.timedelta(days=1)

        logger.debug(
            "時間範圍 %s 到 %s 分割為 %d 個分塊",
            start_date, end_date, len(chunks)
        )
        return chunks

    def _calculate_optimal_chunk_size(self, total_days: int) -> int:
        """計算最佳分塊大小。"""
        if total_days <= 30:
            # 短期：不分塊
            chunk_size = total_days
        elif total_days <= 365:
            # 中期：按月分塊
            chunk_size = 30
        else:
            # 長期：按季度分塊
            chunk_size = 90

        # 確保分塊大小不超過設定的最大值
        return min(chunk_size, self.config.chunk_size)

    def _create_download_tasks(
        self,
        symbols: List[str],
        time_chunks: List[Tuple[datetime.date, datetime.date]]
    ) -> List[Tuple[str, datetime.date, datetime.date]]:
        """創建下載任務列表。"""
        download_tasks = []
        for symbol in symbols:
            for chunk_start, chunk_end in time_chunks:
                download_tasks.append((symbol, chunk_start, chunk_end))

        # 更新總分塊數
        if self.config.enable_progress_tracking:
            with self.progress_lock:
                self.progress.total_chunks = len(download_tasks)

        return download_tasks

    def _execute_parallel_download(
        self,
        download_tasks: List[Tuple[str, datetime.date, datetime.date]],
        show_progress: bool
    ) -> Dict[str, pd.DataFrame]:
        """執行並行下載。"""
        results = {}
        failed_tasks = []

        # 使用進度條
        progress_bar = None
        if show_progress and self.config.enable_progress_tracking:
            progress_bar = tqdm(
                total=len(download_tasks),
                desc="下載歷史資料",
                unit="chunk"
            )

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # 提交所有任務
            future_to_task = {
                executor.submit(
                    self._download_chunk_with_retry,
                    symbol,
                    chunk_start,
                    chunk_end
                ): (symbol, chunk_start, chunk_end)
                for symbol, chunk_start, chunk_end in download_tasks
            }

            # 收集結果
            for future in as_completed(future_to_task):
                symbol, chunk_start, chunk_end = future_to_task[future]

                try:
                    chunk_data = future.result()

                    if chunk_data is not None and not chunk_data.empty:
                        # 合併數據
                        results = self._merge_chunk_data(
                            results, symbol, chunk_data
                        )

                    # 更新進度
                    self._update_progress(progress_bar)

                except Exception as exc:
                    logger.error(
                        "下載 %s 時間段 %s-%s 失敗: %s",
                        symbol, chunk_start, chunk_end, exc
                    )
                    failed_tasks.append((symbol, chunk_start, chunk_end))
                    self._update_progress(progress_bar, failed=True)

        if progress_bar:
            progress_bar.close()

        # 處理失敗的任務
        if failed_tasks:
            logger.warning("有 %d 個下載任務失敗", len(failed_tasks))

        total_records = sum(len(df) for df in results.values())
        logger.info(
            "分時段平行下載完成：成功下載 %d 個股票，共 %d 筆記錄",
            len(results), total_records
        )

        return results

    def _merge_chunk_data(
        self,
        results: Dict[str, pd.DataFrame],
        symbol: str,
        chunk_data: pd.DataFrame
    ) -> Dict[str, pd.DataFrame]:
        """合併分塊數據。"""
        if symbol not in results:
            results[symbol] = chunk_data
        else:
            results[symbol] = pd.concat([results[symbol], chunk_data])
            results[symbol] = results[symbol].sort_index()
            # 移除重複的索引
            results[symbol] = results[symbol][
                ~results[symbol].index.duplicated(keep='first')
            ]
        return results

    def _update_progress(
        self, progress_bar: Optional[tqdm], failed: bool = False
    ) -> None:
        """更新進度。"""
        if not self.config.enable_progress_tracking:
            return

        with self.progress_lock:
            if failed:
                self.progress.failed_chunks += 1
            else:
                self.progress.completed_chunks += 1

            if progress_bar:
                progress_bar.update(1)

    def _download_chunk_with_retry(
        self,
        symbol: str,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> Optional[pd.DataFrame]:
        """帶重試機制的分塊下載方法。

        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            Optional[pd.DataFrame]: 下載的數據，失敗時返回 None
        """
        # 更新當前處理的分塊信息
        if self.config.enable_progress_tracking:
            with self.progress_lock:
                self.progress.current_symbol = symbol
                self.progress.current_chunk = f"{start_date} to {end_date}"

        # 使用速率限制器
        if self.rate_limiter:
            with self.rate_limiter:
                return self._download_with_retry(symbol, start_date, end_date)

        return self._download_with_retry(symbol, start_date, end_date)

    def _download_with_retry(
        self,
        symbol: str,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> Optional[pd.DataFrame]:
        """執行帶重試的下載。"""
        for attempt in range(self.config.retry_attempts):
            try:
                # 下載數據
                data = self.data_manager.get_historical_data(
                    symbols=symbol,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    interval="1d",
                )

                if symbol in data and not data[symbol].empty:
                    logger.debug(
                        "成功下載 %s 的數據：%s 到 %s",
                        symbol, start_date, end_date
                    )
                    return data[symbol]

                logger.warning(
                    "下載 %s 的數據為空：%s 到 %s",
                    symbol, start_date, end_date
                )
                return pd.DataFrame()

            except Exception as exc:
                logger.warning(
                    "下載 %s 數據失敗 (嘗試 %d/%d): %s",
                    symbol, attempt + 1, self.config.retry_attempts, exc
                )
                if attempt < self.config.retry_attempts - 1:
                    # 指數退避
                    wait_time = self.config.retry_delay * (2 ** attempt)
                    time.sleep(wait_time)
                else:
                    logger.error(
                        "下載 %s 數據最終失敗：%s 到 %s",
                        symbol, start_date, end_date
                    )

        return None

    def get_progress_info(self) -> Dict[str, Any]:
        """獲取當前進度資訊。

        Returns:
            Dict[str, any]: 進度資訊
        """
        with self.progress_lock:
            return {
                "symbol_progress": self.progress.symbol_progress,
                "chunk_progress": self.progress.chunk_progress,
                "current_symbol": self.progress.current_symbol,
                "current_chunk": self.progress.current_chunk,
                "completed_symbols": self.progress.completed_symbols,
                "total_symbols": self.progress.total_symbols,
                "completed_chunks": self.progress.completed_chunks,
                "total_chunks": self.progress.total_chunks,
                "failed_chunks": self.progress.failed_chunks,
                "estimated_completion": self.progress.estimated_completion,
            }
