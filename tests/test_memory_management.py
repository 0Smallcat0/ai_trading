"""記憶體管理模組測試

測試記憶體監控、分塊處理和記憶體高效處理功能。
"""

import os
import sys
import unittest
import pandas as pd
from unittest.mock import patch, MagicMock

# 添加專案根目錄到 Python 路徑
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.memory_management import (
    MemoryMonitor,
    ChunkProcessor,
    MemoryEfficientProcessor
)


class TestMemoryMonitor(unittest.TestCase):
    """測試記憶體監控器"""def setUp(self):
        """設置測試環境"""self.monitor = MemoryMonitor()

    def test_get_memory_usage(self):
        """測試獲取記憶體使用情況"""memory_info = self.monitor.get_memory_usage()

        # 檢查返回的字典包含必要的鍵
        required_keys = [
            "process_rss", "process_vms", "system_total",
            "system_available", "system_used", "system_percent"
        ]
        for key in required_keys:
            self.assertIn(key, memory_info)
            self.assertIsInstance(memory_info[key], (int, float))
            self.assertGreaterEqual(memory_info[key], 0)

    def test_get_memory_growth(self):
        """測試獲取記憶體增長量"""# 創建一些數據來增加記憶體使用
        data = [np.random.randn(1000, 100) for _ in range(10)]

        growth = self.monitor.get_memory_growth()
        self.assertIsInstance(growth, (int, float))

        # 清理數據
        del data

    def test_is_memory_available(self):
        """測試檢查記憶體可用性"""# 測試小量記憶體需求
        result = self.monitor.is_memory_available(10)  # 10MB
        self.assertIsInstance(result, bool)

        # 測試大量記憶體需求（應該返回 False）
        result = self.monitor.is_memory_available(999999)  # 999GB
        self.assertFalse(result)


class TestChunkProcessor(unittest.TestCase):
    """測試分塊處理器"""def setUp(self):
        """設置測試環境"""self.processor = ChunkProcessor(max_memory_mb=100)
        self.test_data = pd.DataFrame({
            'A': np.random.randn(1000),
            'B': np.random.randn(1000),
            'C': np.random.randn(1000),
            'D': np.random.randn(1000)
        })

    def test_estimate_dataframe_memory(self):
        """測試估算 DataFrame 記憶體使用量"""memory_mb = self.processor.estimate_dataframe_memory(self.test_data)

        self.assertIsInstance(memory_mb, float)
        self.assertGreater(memory_mb, 0)

    def test_calculate_optimal_chunk_size(self):
        """測試計算最佳分塊大小"""total_rows = 10000

        # 使用樣本 DataFrame
        chunk_size = self.processor.calculate_optimal_chunk_size(
            total_rows, self.test_data
        )

        self.assertIsInstance(chunk_size, int)
        self.assertGreaterEqual(chunk_size, self.processor.min_chunk_size)
        self.assertLessEqual(chunk_size, self.processor.max_chunk_size)
        self.assertLessEqual(chunk_size, total_rows)

        # 使用估算行大小
        chunk_size = self.processor.calculate_optimal_chunk_size(
            total_rows, estimated_row_size_bytes=1024
        )

        self.assertIsInstance(chunk_size, int)
        self.assertGreaterEqual(chunk_size, self.processor.min_chunk_size)

    def test_create_chunks(self):
        """測試創建數據分塊索引"""# 使用 DataFrame
        chunks = self.processor.create_chunks(self.test_data, chunk_size=200)

        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 0)

        # 檢查分塊覆蓋所有數據
        total_covered = 0
        for start, end in chunks:
            self.assertIsInstance(start, int)
            self.assertIsInstance(end, int)
            self.assertLessEqual(start, end)
            total_covered += (end - start)

        self.assertEqual(total_covered, len(self.test_data))

        # 使用總行數
        chunks = self.processor.create_chunks(1000, chunk_size=200)
        self.assertEqual(len(chunks), 5)  # 1000 / 200 = 5

    def test_process_dataframe_chunks(self):
        """測試分塊處理 DataFrame"""def sum_func(df):
            return df.sum()

        results = self.processor.process_dataframe_chunks(
            self.test_data, sum_func, chunk_size=200
        )

        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

        # 驗證結果
        total_sum = pd.concat(results, axis=1).sum(axis=1)
        expected_sum = self.test_data.sum()

        pd.testing.assert_series_equal(total_sum, expected_sum)

    def test_process_dataframe_chunks_with_progress(self):
        """測試帶進度回調的分塊處理"""progress_calls = []

        def progress_callback(current, total):
            progress_calls.append((current, total))

        def simple_func(df):
            return len(df)

        results = self.processor.process_dataframe_chunks(
            self.test_data,
            simple_func,
            chunk_size=200,
            progress_callback=progress_callback
        )

        # 檢查進度回調被調用
        self.assertGreater(len(progress_calls), 0)

        # 檢查最後一次調用
        last_call = progress_calls[-1]
        self.assertEqual(last_call[0], last_call[1])  # current == total

        # 檢查結果
        total_rows = sum(results)
        self.assertEqual(total_rows, len(self.test_data))

    def test_process_empty_dataframe(self):
        """測試處理空 DataFrame"""empty_df = pd.DataFrame()

        def dummy_func(df):
            return df

        results = self.processor.process_dataframe_chunks(empty_df, dummy_func)
        self.assertEqual(results, [])


class TestMemoryEfficientProcessor(unittest.TestCase):
    """測試記憶體高效處理器"""def setUp(self):
        """設置測試環境"""self.processor = MemoryEfficientProcessor(max_memory_mb=50)
        self.small_data = pd.DataFrame({
            'A': np.random.randn(100),
            'B': np.random.randn(100)
        })
        self.large_data = pd.DataFrame({
            'A': np.random.randn(10000),
            'B': np.random.randn(10000),
            'C': np.random.randn(10000),
            'D': np.random.randn(10000)
        })

    def test_process_small_dataframe(self):
        """測試處理小型 DataFrame"""def mean_func(df):
            return df.mean()

        result = self.processor.process_with_memory_management(
            self.small_data, mean_func
        )

        expected = self.small_data.mean()
        pd.testing.assert_series_equal(result, expected)

    def test_process_large_dataframe(self):
        """測試處理大型 DataFrame"""def sum_func(df):
            return df.sum()

        # 模擬大數據處理
        with patch.object(
            self.processor.chunk_processor,
            'estimate_dataframe_memory',
            return_value=100  # 模擬超過限制
        ):
            result = self.processor.process_with_memory_management(
                self.large_data, sum_func
            )

            # 結果應該是 Series（合併後的結果）
            self.assertIsInstance(result, pd.Series)

    def test_process_dataframe_list(self):
        """測試處理 DataFrame 列表"""data_list = [self.small_data, self.small_data.copy()]

        def mean_func(df):
            return df.mean()

        result = self.processor.process_with_memory_management(
            data_list, mean_func
        )

        # 結果應該是合併的 DataFrame
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)  # 兩個結果行

    def test_process_unsupported_type(self):
        """測試處理不支援的數據類型"""def dummy_func(data):
            return data

        with self.assertRaises(ValueError):
            self.processor.process_with_memory_management(
                "unsupported", dummy_func
            )

    def test_combine_results_dataframes(self):
        """測試合併 DataFrame 結果"""df1 = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        df2 = pd.DataFrame({'A': [5, 6], 'B': [7, 8]})

        result = self.processor._combine_results([df1, df2])

        expected = pd.concat([df1, df2], ignore_index=True)
        pd.testing.assert_frame_equal(result, expected)

    def test_combine_results_lists(self):
        """測試合併列表結果"""list1 = [1, 2, 3]
        list2 = [4, 5, 6]

        result = self.processor._combine_results([list1, list2])

        expected = [1, 2, 3, 4, 5, 6]
        self.assertEqual(result, expected)

    def test_combine_results_mixed(self):
        """測試合併混合類型結果"""mixed_results = [1, "string", [1, 2, 3]]

        result = self.processor._combine_results(mixed_results)

        # 應該返回原始列表
        self.assertEqual(result, mixed_results)

    def test_combine_empty_results(self):
        """測試合併空結果"""
        result = self.processor._combine_results([])
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
