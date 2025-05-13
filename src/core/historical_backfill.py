"""
歷史資料回填與驗證模組

此模組負責歷史資料的回填與驗證，包括：
- 批次處理優化：時間切片並行下載、增量更新識別
- 資料驗證：時間序列連續性檢查、自動異常值標記系統

主要功能：
- 高效率批次下載歷史資料
- 識別並僅下載增量更新的資料
- 檢查時間序列的連續性
- 自動標記和處理異常值
"""

import os
import logging
import datetime
import pandas as pd
import numpy as np
from typing import List, Dict, Union, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from functools import partial
import warnings
from scipy import stats

# 導入相關模組
try:
    from src.core.data_ingest import DataIngestionManager, load_data
    from src.database.parquet_utils import save_to_parquet, read_from_parquet
    from src.utils.utils import get_trading_dates, is_trading_day
except ImportError as e:
    raise ImportError(
        "無法匯入必要模組，請確認你在 package 結構下執行，或設置 PYTHONPATH。錯誤："
        + str(e)
    )

# 設定日誌
logger = logging.getLogger(__name__)


class HistoricalBackfill:
    """
    歷史資料回填與驗證類

    負責高效率地回填歷史資料，並進行資料驗證。
    支援時間切片並行下載、增量更新識別、時間序列連續性檢查和自動異常值標記。
    """

    def __init__(
        self,
        data_manager: Optional[DataIngestionManager] = None,
        max_workers: int = 5,
        chunk_size: int = 30,  # 每個時間切片的天數
        retry_attempts: int = 3,
        retry_delay: int = 5,
        z_score_threshold: float = 3.0,  # 異常值 Z 分數閾值
    ):
        """
        初始化歷史資料回填與驗證類

        Args:
            data_manager: 資料擷取管理器，如果為 None 則創建新的實例
            max_workers: 最大工作執行緒數
            chunk_size: 每個時間切片的天數
            retry_attempts: 重試次數
            retry_delay: 重試延遲（秒）
            z_score_threshold: 異常值 Z 分數閾值
        """
        self.data_manager = data_manager or DataIngestionManager(use_cache=True)
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.z_score_threshold = z_score_threshold

        # 統計信息
        self.stats = {
            "total_symbols": 0,
            "total_dates": 0,
            "chunks_processed": 0,
            "data_points_downloaded": 0,
            "data_points_skipped": 0,
            "continuity_issues": 0,
            "outliers_detected": 0,
            "download_time": 0,
        }

    def _split_date_range(
        self, start_date: Union[str, datetime.date], end_date: Union[str, datetime.date]
    ) -> List[Tuple[datetime.date, datetime.date]]:
        """
        將日期範圍分割為多個時間切片

        Args:
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            List[Tuple[datetime.date, datetime.date]]: 時間切片列表，每個元素為 (切片開始日期, 切片結束日期)
        """
        # 轉換日期格式
        if isinstance(start_date, str):
            start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        if isinstance(end_date, str):
            end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()

        # 獲取交易日期
        trading_dates = get_trading_dates(start_date, end_date)

        # 更新統計信息
        self.stats["total_dates"] = len(trading_dates)

        # 分割為時間切片
        chunks = []
        for i in range(0, len(trading_dates), self.chunk_size):
            chunk_start = trading_dates[i]
            chunk_end = trading_dates[
                min(i + self.chunk_size - 1, len(trading_dates) - 1)
            ]
            chunks.append((chunk_start, chunk_end))

        return chunks

    def _get_existing_data(
        self, symbols: List[str], start_date: datetime.date, end_date: datetime.date
    ) -> Dict[str, pd.DataFrame]:
        """
        獲取已存在的資料，用於增量更新識別

        Args:
            symbols: 股票代碼列表
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            Dict[str, pd.DataFrame]: 股票代碼到現有資料的映射
        """
        try:
            existing_data = load_data(start_date, end_date)
            if "price" not in existing_data:
                return {}

            price_df = existing_data["price"]
            if price_df.empty:
                return {}

            # 如果是 MultiIndex DataFrame，轉換為字典
            if isinstance(price_df.index, pd.MultiIndex):
                result = {}
                for symbol in symbols:
                    if symbol in price_df.index.get_level_values(0):
                        result[symbol] = price_df.xs(symbol, level=0)
                return result
            else:
                # 假設是單一股票的 DataFrame
                if len(symbols) == 1:
                    return {symbols[0]: price_df}
                else:
                    return {}
        except Exception as e:
            logger.warning(f"獲取現有資料時發生錯誤: {e}")
            return {}

    def _identify_missing_dates(
        self,
        symbol: str,
        existing_data: Dict[str, pd.DataFrame],
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> List[Tuple[datetime.date, datetime.date]]:
        """
        識別缺失的日期範圍，用於增量更新

        Args:
            symbol: 股票代碼
            existing_data: 現有資料
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            List[Tuple[datetime.date, datetime.date]]: 缺失日期範圍列表
        """
        # 獲取交易日期
        all_trading_dates = set(get_trading_dates(start_date, end_date))

        # 獲取現有資料的日期
        existing_dates = set()
        if symbol in existing_data and not existing_data[symbol].empty:
            df = existing_data[symbol]
            if isinstance(df.index, pd.DatetimeIndex):
                existing_dates = set(df.index.date)
            else:
                # 嘗試將索引轉換為日期
                try:
                    existing_dates = set(pd.to_datetime(df.index).date)
                except:
                    logger.warning(f"無法將 {symbol} 的索引轉換為日期")

        # 計算缺失的日期
        missing_dates = sorted(all_trading_dates - existing_dates)

        # 更新統計信息
        self.stats["data_points_skipped"] += len(existing_dates)

        # 如果沒有缺失日期，返回空列表
        if not missing_dates:
            return []

        # 將連續的日期合併為範圍
        date_ranges = []
        range_start = missing_dates[0]
        prev_date = missing_dates[0]

        for date in missing_dates[1:]:
            # 如果日期不連續，結束當前範圍並開始新範圍
            if (date - prev_date).days > 1:
                date_ranges.append((range_start, prev_date))
                range_start = date
            prev_date = date

        # 添加最後一個範圍
        date_ranges.append((range_start, prev_date))

        return date_ranges

    def _download_chunk(
        self,
        symbols: List[str],
        start_date: datetime.date,
        end_date: datetime.date,
        existing_data: Dict[str, pd.DataFrame],
    ) -> Dict[str, pd.DataFrame]:
        """
        下載一個時間切片的資料

        Args:
            symbols: 股票代碼列表
            start_date: 開始日期
            end_date: 結束日期
            existing_data: 現有資料

        Returns:
            Dict[str, pd.DataFrame]: 下載的資料
        """
        result = {}

        for symbol in symbols:
            # 識別缺失的日期範圍
            missing_ranges = self._identify_missing_dates(
                symbol, existing_data, start_date, end_date
            )

            # 如果沒有缺失的日期範圍，跳過
            if not missing_ranges:
                continue

            # 下載缺失的資料
            symbol_data = pd.DataFrame()
            for range_start, range_end in missing_ranges:
                for attempt in range(self.retry_attempts):
                    try:
                        data = self.data_manager.get_historical_data(
                            symbols=symbol,
                            start_date=range_start.strftime("%Y-%m-%d"),
                            end_date=range_end.strftime("%Y-%m-%d"),
                            interval="1d",
                        )

                        if symbol in data and not data[symbol].empty:
                            # 合併資料
                            if symbol_data.empty:
                                symbol_data = data[symbol]
                            else:
                                symbol_data = pd.concat([symbol_data, data[symbol]])

                            # 更新統計信息
                            self.stats["data_points_downloaded"] += len(data[symbol])

                            break
                    except Exception as e:
                        logger.warning(
                            f"下載 {symbol} 的資料時發生錯誤 (嘗試 {attempt+1}/{self.retry_attempts}): {e}"
                        )
                        if attempt < self.retry_attempts - 1:
                            time.sleep(self.retry_delay)

            # 如果下載到資料，添加到結果
            if not symbol_data.empty:
                result[symbol] = symbol_data

        return result

    def backfill(
        self,
        symbols: Union[str, List[str]],
        start_date: Union[str, datetime.date],
        end_date: Union[str, datetime.date],
        validate: bool = True,
        save_result: bool = True,
    ) -> Dict[str, pd.DataFrame]:
        """
        回填歷史資料

        Args:
            symbols: 股票代碼或代碼列表
            start_date: 開始日期
            end_date: 結束日期
            validate: 是否進行資料驗證
            save_result: 是否儲存結果

        Returns:
            Dict[str, pd.DataFrame]: 回填的資料
        """
        start_time = time.time()

        # 轉換單一股票代碼為列表
        if isinstance(symbols, str):
            symbols = [symbols]

        # 更新統計信息
        self.stats["total_symbols"] = len(symbols)

        # 分割日期範圍
        chunks = self._split_date_range(start_date, end_date)

        # 獲取現有資料
        existing_data = self._get_existing_data(symbols, start_date, end_date)

        # 使用執行緒池並行下載資料
        all_data = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 為每個時間切片創建下載任務
            future_to_chunk = {
                executor.submit(
                    self._download_chunk, symbols, chunk_start, chunk_end, existing_data
                ): (chunk_start, chunk_end)
                for chunk_start, chunk_end in chunks
            }

            # 處理完成的任務
            for future in as_completed(future_to_chunk):
                chunk_start, chunk_end = future_to_chunk[future]
                try:
                    chunk_data = future.result()

                    # 合併資料
                    for symbol, data in chunk_data.items():
                        if symbol not in all_data:
                            all_data[symbol] = data
                        else:
                            all_data[symbol] = pd.concat([all_data[symbol], data])

                    # 更新統計信息
                    self.stats["chunks_processed"] += 1

                    logger.info(f"完成時間切片 {chunk_start} 到 {chunk_end} 的下載")
                except Exception as e:
                    logger.error(
                        f"處理時間切片 {chunk_start} 到 {chunk_end} 時發生錯誤: {e}"
                    )

        # 合併現有資料和新下載的資料
        result = {}
        for symbol in symbols:
            # 合併現有資料
            if symbol in existing_data and not existing_data[symbol].empty:
                result[symbol] = existing_data[symbol]

            # 合併新下載的資料
            if symbol in all_data and not all_data[symbol].empty:
                if symbol in result:
                    # 確保索引是日期時間類型
                    if not isinstance(all_data[symbol].index, pd.DatetimeIndex):
                        all_data[symbol].index = pd.to_datetime(all_data[symbol].index)
                    if not isinstance(result[symbol].index, pd.DatetimeIndex):
                        result[symbol].index = pd.to_datetime(result[symbol].index)

                    # 合併並移除重複項
                    result[symbol] = pd.concat([result[symbol], all_data[symbol]])
                    result[symbol] = result[symbol][
                        ~result[symbol].index.duplicated(keep="last")
                    ]
                    result[symbol] = result[symbol].sort_index()
                else:
                    result[symbol] = all_data[symbol]

        # 進行資料驗證
        if validate:
            for symbol in result:
                result[symbol] = self.validate_data(result[symbol])

        # 儲存結果
        if save_result:
            self._save_result(result)

        # 更新統計信息
        self.stats["download_time"] = time.time() - start_time

        logger.info(
            f"歷史資料回填完成，共處理 {self.stats['total_symbols']} 個股票，"
            f"{self.stats['chunks_processed']} 個時間切片，"
            f"下載 {self.stats['data_points_downloaded']} 個資料點，"
            f"跳過 {self.stats['data_points_skipped']} 個現有資料點，"
            f"耗時 {self.stats['download_time']:.2f} 秒"
        )

        return result

    def validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        驗證資料，包括時間序列連續性檢查和異常值標記

        Args:
            df: 資料 DataFrame

        Returns:
            pd.DataFrame: 驗證後的資料
        """
        if df.empty:
            return df

        # 確保索引是日期時間類型
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        # 排序索引
        df = df.sort_index()

        # 檢查時間序列連續性
        self._check_continuity(df)

        # 標記異常值
        df = self._tag_outliers(df)

        return df

    def _check_continuity(self, df: pd.DataFrame) -> None:
        """
        檢查時間序列連續性

        Args:
            df: 資料 DataFrame
        """
        if df.empty or len(df) < 2:
            return

        # 獲取所有交易日期
        start_date = df.index.min().date()
        end_date = df.index.max().date()
        trading_dates = get_trading_dates(start_date, end_date)

        # 檢查是否有缺失的交易日期
        df_dates = set(df.index.date)
        missing_dates = [date for date in trading_dates if date not in df_dates]

        if missing_dates:
            self.stats["continuity_issues"] += len(missing_dates)
            logger.warning(
                f"時間序列連續性檢查：發現 {len(missing_dates)} 個缺失的交易日期"
            )
            logger.debug(
                f"缺失的交易日期：{missing_dates[:5]}{'...' if len(missing_dates) > 5 else ''}"
            )

    def _tag_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        標記異常值

        Args:
            df: 資料 DataFrame

        Returns:
            pd.DataFrame: 標記異常值後的資料
        """
        if df.empty:
            return df

        # 尋找價格欄位
        price_cols = []
        for col in df.columns:
            if col.lower() in ["close", "收盤價", "adj close", "調整後收盤價"]:
                price_cols.append(col)

        if not price_cols:
            logger.warning("找不到價格欄位，無法標記異常值")
            return df

        # 為每個價格欄位標記異常值
        for col in price_cols:
            # 計算 Z 分數
            z_scores = stats.zscore(df[col], nan_policy="omit")

            # 標記異常值
            outliers = np.abs(z_scores) > self.z_score_threshold
            outlier_count = np.sum(outliers)

            if outlier_count > 0:
                # 添加異常值標記欄位
                outlier_col = f"{col}_outlier"
                df[outlier_col] = outliers

                # 更新統計信息
                self.stats["outliers_detected"] += outlier_count

                logger.info(f"異常值標記：在 {col} 欄位中發現 {outlier_count} 個異常值")

        return df

    def _save_result(self, data: Dict[str, pd.DataFrame]) -> None:
        """
        儲存回填的資料

        Args:
            data: 回填的資料
        """
        if not data:
            return

        try:
            # 將資料轉換為 MultiIndex DataFrame
            dfs = []
            for symbol, df in data.items():
                if not df.empty:
                    # 添加股票代碼層級
                    df = df.copy()
                    df["symbol"] = symbol
                    df.set_index("symbol", append=True, inplace=True)
                    # 調整層級順序
                    df = df.swaplevel()
                    dfs.append(df)

            if dfs:
                # 合併所有資料
                combined_df = pd.concat(dfs)

                # 儲存為 Parquet 檔案
                save_to_parquet(combined_df, "price_backfill")

                logger.info(f"已儲存回填的資料，共 {len(combined_df)} 筆")
        except Exception as e:
            logger.error(f"儲存回填的資料時發生錯誤: {e}")


def backfill_historical_data(
    symbols: Union[str, List[str]],
    start_date: Union[str, datetime.date],
    end_date: Union[str, datetime.date],
    max_workers: int = 5,
    chunk_size: int = 30,
    validate: bool = True,
    save_result: bool = True,
) -> Dict[str, pd.DataFrame]:
    """
    回填歷史資料的便捷函數

    Args:
        symbols: 股票代碼或代碼列表
        start_date: 開始日期
        end_date: 結束日期
        max_workers: 最大工作執行緒數
        chunk_size: 每個時間切片的天數
        validate: 是否進行資料驗證
        save_result: 是否儲存結果

    Returns:
        Dict[str, pd.DataFrame]: 回填的資料
    """
    backfiller = HistoricalBackfill(max_workers=max_workers, chunk_size=chunk_size)
    return backfiller.backfill(symbols, start_date, end_date, validate, save_result)
