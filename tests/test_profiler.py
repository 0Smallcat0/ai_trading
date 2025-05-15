# -*- coding: utf-8 -*-
"""
測試性能分析工具

此模組用於測試性能分析工具的功能。
"""

import os
import sys
import unittest
import tempfile
import time
import numpy as np
import pandas as pd
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.utils.profiler import FunctionProfiler, MemoryProfiler, IOProfiler


class TestProfiler(unittest.TestCase):
    """測試性能分析工具"""

    def setUp(self):
        """設置測試環境"""
        # 創建臨時目錄
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = self.temp_dir.name

    def tearDown(self):
        """清理測試環境"""
        # 刪除臨時目錄
        self.temp_dir.cleanup()

    def test_function_profiler(self):
        """測試函數性能分析器"""
        # 創建函數性能分析器
        profiler = FunctionProfiler(self.output_dir)

        # 定義測試函數
        @profiler.profile()
        def test_function():
            """測試函數"""
            time.sleep(0.1)
            return sum(range(1000000))

        # 執行測試函數
        result = test_function()

        # 檢查結果
        self.assertEqual(result, sum(range(1000000)))

        # 檢查是否生成了分析結果檔案
        self.assertTrue(len(os.listdir(self.output_dir)) > 0)

        # 檢查分析結果是否包含函數名稱
        for filename in os.listdir(self.output_dir):
            if filename.startswith("test_function_") and filename.endswith(".prof"):
                with open(os.path.join(self.output_dir, filename), "r") as f:
                    content = f.read()
                    self.assertIn("test_function", content)
                break
        else:
            self.fail("未找到分析結果檔案")

    def test_memory_profiler(self):
        """測試記憶體使用分析器"""
        # 創建記憶體使用分析器
        profiler = MemoryProfiler(self.output_dir)

        # 定義測試函數
        @profiler.profile()
        def test_function():
            """測試函數"""
            # 創建大型陣列
            data = np.zeros((1000, 1000))
            return data.sum()

        # 執行測試函數
        result = test_function()

        # 檢查結果
        self.assertEqual(result, 0)

        # 檢查是否生成了分析結果檔案
        self.assertTrue(len(os.listdir(self.output_dir)) > 0)

        # 檢查分析結果是否包含記憶體使用資訊
        for filename in os.listdir(self.output_dir):
            if filename.startswith("test_function_memory_") and filename.endswith(".txt"):
                with open(os.path.join(self.output_dir, filename), "r") as f:
                    content = f.read()
                    self.assertIn("記憶體使用", content)
                break
        else:
            self.fail("未找到分析結果檔案")

    def test_io_profiler(self):
        """測試 I/O 操作分析器"""
        # 創建 I/O 操作分析器
        profiler = IOProfiler(self.output_dir)

        # 定義測試函數
        @profiler.profile()
        def test_function():
            """測試函數"""
            # 創建臨時檔案
            temp_file = os.path.join(self.output_dir, "test.csv")
            
            # 寫入檔案
            df = pd.DataFrame(np.random.random((1000, 10)))
            df.to_csv(temp_file)
            
            # 讀取檔案
            df2 = pd.read_csv(temp_file)
            
            # 刪除檔案
            os.remove(temp_file)
            
            return len(df2)

        # 執行測試函數
        result = test_function()

        # 檢查結果
        self.assertEqual(result, 1000)

        # 檢查是否生成了分析結果檔案
        self.assertTrue(len(os.listdir(self.output_dir)) > 0)

        # 檢查分析結果是否包含 I/O 操作資訊
        for filename in os.listdir(self.output_dir):
            if filename.startswith("test_function_io_") and filename.endswith(".txt"):
                with open(os.path.join(self.output_dir, filename), "r") as f:
                    content = f.read()
                    self.assertIn("I/O 操作分析結果", content)
                    self.assertIn("讀取次數", content)
                    self.assertIn("寫入次數", content)
                break
        else:
            self.fail("未找到分析結果檔案")


if __name__ == "__main__":
    unittest.main()
