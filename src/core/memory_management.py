"""記憶體分塊處理機制模組

此模組提供記憶體高效的數據分塊處理功能，避免大數據集載入時的記憶體溢出。

主要功能：
- 智能數據分塊策略
- 記憶體使用監控
- 動態分塊大小調整
- 進度追蹤和性能監控
"""

import gc
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import pandas as pd
import psutil

# 設置日誌
logger = logging.getLogger(__name__)


class MemoryMonitor:
    """記憶體監控器

    監控系統和進程的記憶體使用情況。
    """

    def __init__(self):
        """初始化記憶體監控器"""
        self.process = psutil.Process(os.getpid())
        self.initial_memory = self.get_memory_usage()

    def get_memory_usage(self) -> Dict[str, float]:
        """獲取當前記憶體使用情況

        Returns:
            Dict[str, float]: 記憶體使用信息（MB）
        """
        # 進程記憶體使用
        process_memory = self.process.memory_info()

        # 系統記憶體使用
        system_memory = psutil.virtual_memory()

        return {
            "process_rss": process_memory.rss / 1024 / 1024,  # MB
            "process_vms": process_memory.vms / 1024 / 1024,  # MB
            "system_total": system_memory.total / 1024 / 1024,  # MB
            "system_available": system_memory.available / 1024 / 1024,  # MB
            "system_used": system_memory.used / 1024 / 1024,  # MB
            "system_percent": system_memory.percent,
        }

    def get_memory_growth(self) -> float:
        """獲取記憶體增長量

        Returns:
            float: 記憶體增長量（MB）
        """
        current_memory = self.get_memory_usage()
        return current_memory["process_rss"] - self.initial_memory["process_rss"]

    def is_memory_available(self, required_mb: float) -> bool:
        """檢查是否有足夠的可用記憶體

        Args:
            required_mb: 需要的記憶體量（MB）

        Returns:
            bool: 是否有足夠記憶體
        """
        memory_info = self.get_memory_usage()
        available_mb = memory_info["system_available"]

        # 保留 20% 的緩衝區
        safe_available = available_mb * 0.8

        return required_mb <= safe_available


class ChunkProcessor:
    """數據分塊處理器

    提供智能的數據分塊和處理功能。
    """

    def __init__(
        self,
        max_memory_mb: float = 1024,
        min_chunk_size: int = 1000,
        max_chunk_size: int = 100000,
        memory_safety_factor: float = 0.8,
    ):
        """初始化分塊處理器

        Args:
            max_memory_mb: 最大記憶體使用量（MB）
            min_chunk_size: 最小分塊大小
            max_chunk_size: 最大分塊大小
            memory_safety_factor: 記憶體安全係數
        """
        self.max_memory_mb = max_memory_mb
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.memory_safety_factor = memory_safety_factor
        self.memory_monitor = MemoryMonitor()

    def estimate_dataframe_memory(self, df: pd.DataFrame) -> float:
        """估算 DataFrame 的記憶體使用量

        Args:
            df: DataFrame

        Returns:
            float: 記憶體使用量（MB）
        """
        return df.memory_usage(deep=True).sum() / 1024 / 1024

    def calculate_optimal_chunk_size(
        self,
        total_rows: int,
        sample_df: Optional[pd.DataFrame] = None,
        estimated_row_size_bytes: Optional[float] = None,
    ) -> int:
        """計算最佳分塊大小

        Args:
            total_rows: 總行數
            sample_df: 樣本 DataFrame（用於估算行大小）
            estimated_row_size_bytes: 估算的行大小（字節）

        Returns:
            int: 最佳分塊大小
        """
        # 估算每行的記憶體使用量
        if sample_df is not None:
            sample_memory_mb = self.estimate_dataframe_memory(sample_df)
            if len(sample_df) > 0:
                row_size_mb = sample_memory_mb / len(sample_df)
            else:
                row_size_mb = 0.001
        elif estimated_row_size_bytes is not None:
            row_size_mb = estimated_row_size_bytes / 1024 / 1024
        else:
            # 預設估算：每行約 1KB
            row_size_mb = 0.001

        # 計算可用記憶體
        available_memory = self.max_memory_mb * self.memory_safety_factor

        # 計算理論最佳分塊大小
        theoretical_chunk_size = int(available_memory / row_size_mb)

        # 應用限制
        chunk_size = max(
            self.min_chunk_size, min(theoretical_chunk_size, self.max_chunk_size)
        )

        # 確保不超過總行數
        chunk_size = min(chunk_size, total_rows)

        logger.info(
            "計算最佳分塊大小: %s (總行數: %s, 行大小: %.4fMB)",
            chunk_size,
            total_rows,
            row_size_mb,
        )

        return chunk_size

    def create_chunks(
        self, data: Union[pd.DataFrame, int], chunk_size: Optional[int] = None
    ) -> List[Tuple[int, int]]:
        """創建數據分塊索引

        Args:
            data: DataFrame 或總行數
            chunk_size: 分塊大小（如果為 None 則自動計算）

        Returns:
            List[Tuple[int, int]]: 分塊索引列表 [(start, end), ...]
        """
        if isinstance(data, pd.DataFrame):
            total_rows = len(data)
            if len(data) > 0:
                sample_df = data.head(min(1000, len(data)))
            else:
                sample_df = data
        else:
            total_rows = data
            sample_df = None

        if chunk_size is None:
            chunk_size = self.calculate_optimal_chunk_size(total_rows, sample_df)

        chunks = []
        for start in range(0, total_rows, chunk_size):
            end = min(start + chunk_size, total_rows)
            chunks.append((start, end))

        logger.info("創建 %s 個分塊，總行數: %s", len(chunks), total_rows)
        return chunks

    def process_dataframe_chunks(
        self,
        df: pd.DataFrame,
        process_func: Callable[[pd.DataFrame], Any],
        chunk_size: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        **kwargs,
    ) -> List[Any]:
        """分塊處理 DataFrame

        Args:
            df: 輸入 DataFrame
            process_func: 處理函數
            chunk_size: 分塊大小
            progress_callback: 進度回調函數
            **kwargs: 傳遞給處理函數的額外參數

        Returns:
            List[Any]: 處理結果列表
        """
        if df.empty:
            return []

        # 創建分塊
        chunks = self.create_chunks(df, chunk_size)
        results = []

        logger.info("開始分塊處理，共 %s 個分塊", len(chunks))

        for i, (start, end) in enumerate(chunks):
            try:
                # 記錄處理前的記憶體使用
                memory_before = self.memory_monitor.get_memory_usage()

                # 提取分塊數據
                chunk_df = df.iloc[start:end].copy()

                # 處理分塊
                result = process_func(chunk_df, **kwargs)
                results.append(result)

                # 清理記憶體
                del chunk_df
                gc.collect()

                # 記錄處理後的記憶體使用
                memory_after = self.memory_monitor.get_memory_usage()
                memory_growth = (
                    memory_after["process_rss"] - memory_before["process_rss"]
                )

                logger.debug(
                    "分塊 %s/%s 處理完成 (行 %s-%s), 記憶體增長: %.2fMB",
                    i + 1,
                    len(chunks),
                    start,
                    end,
                    memory_growth,
                )

                # 調用進度回調
                if progress_callback:
                    progress_callback(i + 1, len(chunks))

                # 檢查記憶體使用
                if not self.memory_monitor.is_memory_available(self.max_memory_mb):
                    logger.warning("記憶體使用量過高，強制垃圾回收")
                    gc.collect()

            except Exception as e:
                logger.error("處理分塊 %s 時發生錯誤: %s", i + 1, e)
                raise

        logger.info("分塊處理完成，共處理 %s 個分塊", len(chunks))
        return results

    def process_file_chunks(
        self,
        file_path: str,
        process_func: Callable[[pd.DataFrame], Any],
        read_func: Callable[[str, int, int], pd.DataFrame],
        total_rows: int,
        chunk_size: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        **kwargs,
    ) -> List[Any]:
        """分塊處理文件

        Args:
            file_path: 文件路徑
            process_func: 處理函數
            read_func: 讀取函數，接受 (file_path, start, end) 參數
            total_rows: 總行數
            chunk_size: 分塊大小
            progress_callback: 進度回調函數
            **kwargs: 傳遞給處理函數的額外參數

        Returns:
            List[Any]: 處理結果列表
        """
        # 創建分塊
        chunks = self.create_chunks(total_rows, chunk_size)
        results = []

        logger.info("開始分塊處理文件 %s，共 %s 個分塊", file_path, len(chunks))

        for i, (start, end) in enumerate(chunks):
            try:
                # 記錄處理前的記憶體使用
                memory_before = self.memory_monitor.get_memory_usage()

                # 讀取分塊數據
                chunk_df = read_func(file_path, start, end)

                # 處理分塊
                result = process_func(chunk_df, **kwargs)
                results.append(result)

                # 清理記憶體
                del chunk_df
                gc.collect()

                # 記錄處理後的記憶體使用
                memory_after = self.memory_monitor.get_memory_usage()
                memory_growth = (
                    memory_after["process_rss"] - memory_before["process_rss"]
                )

                logger.debug(
                    "文件分塊 %s/%s 處理完成 (行 %s-%s), 記憶體增長: %.2fMB",
                    i + 1,
                    len(chunks),
                    start,
                    end,
                    memory_growth,
                )

                # 調用進度回調
                if progress_callback:
                    progress_callback(i + 1, len(chunks))

            except Exception as e:
                logger.error("處理文件分塊 %s 時發生錯誤: %s", i + 1, e)
                raise

        logger.info("文件分塊處理完成，共處理 %s 個分塊", len(chunks))
        return results


class MemoryEfficientProcessor:
    """記憶體高效處理器

    結合記憶體監控和分塊處理，提供記憶體高效的數據處理功能。
    """

    def __init__(
        self,
        max_memory_mb: float = 1024,
        auto_gc: bool = True,
        gc_threshold: float = 0.8,
    ):
        """初始化記憶體高效處理器

        Args:
            max_memory_mb: 最大記憶體使用量（MB）
            auto_gc: 是否自動垃圾回收
            gc_threshold: 垃圾回收閾值（記憶體使用率）
        """
        self.max_memory_mb = max_memory_mb
        self.auto_gc = auto_gc
        self.gc_threshold = gc_threshold
        self.memory_monitor = MemoryMonitor()
        self.chunk_processor = ChunkProcessor(max_memory_mb)

    def process_with_memory_management(
        self,
        data: Union[pd.DataFrame, str, List[pd.DataFrame]],
        process_func: Callable,
        **kwargs,
    ) -> Any:
        """使用記憶體管理進行數據處理

        Args:
            data: 輸入數據（DataFrame、文件路徑或 DataFrame 列表）
            process_func: 處理函數
            **kwargs: 額外參數

        Returns:
            Any: 處理結果
        """
        initial_memory = self.memory_monitor.get_memory_usage()
        logger.info(
            "開始記憶體管理處理，初始記憶體: %.2fMB", initial_memory["process_rss"]
        )

        try:
            if isinstance(data, pd.DataFrame):
                return self._process_dataframe(data, process_func, **kwargs)
            elif isinstance(data, str):
                return self._process_file(data, process_func, **kwargs)
            elif isinstance(data, list):
                return self._process_dataframe_list(data, process_func, **kwargs)
            else:
                raise ValueError(f"不支援的數據類型: {type(data)}")

        finally:
            # 最終清理
            if self.auto_gc:
                gc.collect()

            final_memory = self.memory_monitor.get_memory_usage()
            memory_growth = final_memory["process_rss"] - initial_memory["process_rss"]
            logger.info(
                "記憶體管理處理完成，記憶體增長: %.2fMB, 最終記憶體: %.2fMB",
                memory_growth,
                final_memory["process_rss"],
            )

    def _process_dataframe(
        self, data: pd.DataFrame, process_func: Callable, **kwargs
    ) -> Any:
        """處理單個 DataFrame

        Args:
            data: DataFrame
            process_func: 處理函數
            **kwargs: 額外參數

        Returns:
            Any: 處理結果
        """
        estimated_memory = self.chunk_processor.estimate_dataframe_memory(data)

        if estimated_memory > self.max_memory_mb:
            logger.info("數據過大 (%.2fMB)，使用分塊處理", estimated_memory)
            results = self.chunk_processor.process_dataframe_chunks(
                data, process_func, **kwargs
            )
            return self._combine_results(results)
        else:
            logger.info("數據適中 (%.2fMB)，直接處理", estimated_memory)
            return process_func(data, **kwargs)

    def _process_file(self, data: str, process_func: Callable, **kwargs) -> Any:
        """處理文件路徑

        Args:
            data: 文件路徑
            process_func: 處理函數
            **kwargs: 額外參數

        Returns:
            Any: 處理結果

        Raises:
            NotImplementedError: 文件處理功能需要具體實現
        """
        logger.info("處理文件: %s", data)
        # 這裡需要根據具體的文件類型實現讀取邏輯
        raise NotImplementedError("文件處理功能需要具體實現")

    def _process_dataframe_list(
        self, data: List[pd.DataFrame], process_func: Callable, **kwargs
    ) -> Any:
        """處理 DataFrame 列表

        Args:
            data: DataFrame 列表
            process_func: 處理函數
            **kwargs: 額外參數

        Returns:
            Any: 處理結果
        """
        logger.info("處理 DataFrame 列表，共 %s 個", len(data))
        results = []

        for i, df in enumerate(data):
            logger.debug("處理第 %s/%s 個 DataFrame", i + 1, len(data))

            # 檢查記憶體使用
            if self.auto_gc:
                memory_info = self.memory_monitor.get_memory_usage()
                if memory_info["system_percent"] > self.gc_threshold * 100:
                    logger.info("記憶體使用率過高，執行垃圾回收")
                    gc.collect()

            # 處理單個 DataFrame
            result = self.process_with_memory_management(df, process_func, **kwargs)
            results.append(result)

        return self._combine_results(results)

    def _combine_results(self, results: List[Any]) -> Any:
        """合併處理結果

        Args:
            results: 結果列表

        Returns:
            Any: 合併後的結果
        """
        if not results:
            return None

        # 如果所有結果都是 DataFrame，則合併
        if all(isinstance(r, pd.DataFrame) for r in results):
            return pd.concat(results, ignore_index=True)

        # 如果所有結果都是列表，則展平
        if all(isinstance(r, list) for r in results):
            combined = []
            for r in results:
                combined.extend(r)
            return combined

        # 否則返回原始列表
        return results
