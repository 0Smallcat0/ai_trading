"""
資料管理增強功能測試

測試資料品質監控、資料清理工具和資料匯出功能。
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加專案根目錄到 Python 路徑
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ui.pages.data_management import (
    show_data_quality_monitoring,
    show_data_cleaning_tools,
    show_data_export,
)


class TestDataQualityMonitoring(unittest.TestCase):
    """測試資料品質監控功能"""

    def setUp(self):
        """設置測試環境"""
        self.mock_st = Mock()

    @patch("src.ui.pages.data_management.st")
    @patch("src.ui.pages.data_management.pd")
    @patch("src.ui.pages.data_management.px")
    def test_show_data_quality_monitoring(self, mock_px, mock_pd, mock_st):
        """測試資料品質監控顯示"""
        # 設置模擬
        mock_st.subheader = Mock()
        mock_st.columns = Mock(return_value=[Mock(), Mock(), Mock(), Mock()])
        mock_st.metric = Mock()
        mock_st.plotly_chart = Mock()
        mock_st.dataframe = Mock()

        # 模擬 pandas 和 plotly
        mock_pd.date_range = Mock(return_value=pd.date_range("2024-01-01", periods=30))
        mock_pd.DataFrame = Mock(return_value=pd.DataFrame())
        mock_px.line = Mock(return_value=Mock())

        # 執行函數
        show_data_quality_monitoring()

        # 驗證調用
        mock_st.subheader.assert_called()
        mock_st.columns.assert_called_with(4)
        mock_st.metric.assert_called()
        mock_st.plotly_chart.assert_called()
        mock_st.dataframe.assert_called()

    def test_quality_metrics_calculation(self):
        """測試品質指標計算"""
        # 創建測試資料
        test_data = pd.DataFrame({"value": [1, 2, None, 4, 5, None, 7, 8, 9, 10]})

        # 計算完整性
        completeness = (len(test_data) - test_data.isnull().sum().sum()) / len(
            test_data
        )
        expected_completeness = 0.8  # 8/10

        self.assertAlmostEqual(completeness, expected_completeness, places=2)

    def test_outlier_detection(self):
        """測試異常值檢測"""
        # 創建包含異常值的測試資料
        np.random.seed(42)
        normal_data = np.random.normal(100, 10, 100)
        outliers = [200, -50, 300]  # 明顯的異常值
        test_data = np.concatenate([normal_data, outliers])

        # 使用 Z-Score 方法檢測異常值
        z_scores = np.abs((test_data - np.mean(test_data)) / np.std(test_data))
        outlier_indices = np.where(z_scores > 3)[0]

        # 驗證檢測到異常值
        self.assertGreater(len(outlier_indices), 0)


class TestDataCleaningTools(unittest.TestCase):
    """測試資料清理工具功能"""

    @patch("src.ui.pages.data_management.st")
    def test_show_data_cleaning_tools(self, mock_st):
        """測試資料清理工具顯示"""
        # 設置模擬
        mock_st.subheader = Mock()
        mock_st.selectbox = Mock(return_value="缺失值處理")
        mock_st.markdown = Mock()
        mock_st.columns = Mock(return_value=[Mock(), Mock()])
        mock_st.text_input = Mock(return_value="2330.TW")
        mock_st.date_input = Mock(
            return_value=[datetime.now() - timedelta(days=30), datetime.now()]
        )
        mock_st.slider = Mock(return_value=20)
        mock_st.button = Mock(return_value=False)

        # 執行函數
        show_data_cleaning_tools()

        # 驗證調用
        mock_st.subheader.assert_called()
        mock_st.selectbox.assert_called()

    def test_missing_value_handling(self):
        """測試缺失值處理"""
        # 創建包含缺失值的測試資料
        test_data = pd.DataFrame(
            {"A": [1, 2, None, 4, 5], "B": [None, 2, 3, 4, None], "C": [1, 2, 3, 4, 5]}
        )

        # 測試前向填充
        forward_filled = test_data.fillna(method="ffill")
        self.assertFalse(forward_filled.isnull().any().any())

        # 測試後向填充
        backward_filled = test_data.fillna(method="bfill")
        self.assertFalse(backward_filled.isnull().any().any())

        # 測試均值填充
        mean_filled = test_data.fillna(test_data.mean())
        numeric_columns = test_data.select_dtypes(include=[np.number]).columns
        self.assertFalse(mean_filled[numeric_columns].isnull().any().any())

    def test_outlier_detection_methods(self):
        """測試不同的異常值檢測方法"""
        # 創建測試資料
        np.random.seed(42)
        data = np.random.normal(100, 10, 1000)
        data = np.append(data, [200, -50])  # 添加異常值

        # Z-Score 方法
        z_scores = np.abs((data - np.mean(data)) / np.std(data))
        z_outliers = data[z_scores > 3]
        self.assertGreater(len(z_outliers), 0)

        # IQR 方法
        Q1 = np.percentile(data, 25)
        Q3 = np.percentile(data, 75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        iqr_outliers = data[(data < lower_bound) | (data > upper_bound)]
        self.assertGreater(len(iqr_outliers), 0)


class TestDataExport(unittest.TestCase):
    """測試資料匯出功能"""

    @patch("src.ui.pages.data_management.st")
    @patch("src.ui.pages.data_management.pd")
    def test_show_data_export(self, mock_pd, mock_st):
        """測試資料匯出顯示"""
        # 設置模擬
        mock_st.subheader = Mock()
        mock_st.columns = Mock(return_value=[Mock(), Mock()])
        mock_st.selectbox = Mock(side_effect=["股價資料", "CSV"])
        mock_st.multiselect = Mock(return_value=["2330.TW"])
        mock_st.date_input = Mock(
            return_value=[datetime.now() - timedelta(days=30), datetime.now()]
        )
        mock_st.checkbox = Mock(return_value=True)
        mock_st.button = Mock(return_value=False)

        # 執行函數
        show_data_export()

        # 驗證調用
        mock_st.subheader.assert_called()
        mock_st.columns.assert_called()
        mock_st.selectbox.assert_called()

    def test_data_export_formats(self):
        """測試不同的資料匯出格式"""
        # 創建測試資料
        test_data = pd.DataFrame(
            {
                "Date": pd.date_range("2024-01-01", periods=10),
                "Symbol": "2330.TW",
                "Open": np.random.uniform(500, 600, 10),
                "High": np.random.uniform(600, 650, 10),
                "Low": np.random.uniform(480, 520, 10),
                "Close": np.random.uniform(520, 580, 10),
                "Volume": np.random.randint(10000000, 50000000, 10),
            }
        )

        # 測試 CSV 匯出
        csv_data = test_data.to_csv(index=False)
        self.assertIsInstance(csv_data, str)
        self.assertIn("Date,Symbol,Open", csv_data)

        # 測試 JSON 匯出
        json_data = test_data.to_json(orient="records")
        self.assertIsInstance(json_data, str)

        # 測試 Excel 匯出（模擬）
        # 在實際環境中需要安裝 openpyxl
        try:
            excel_buffer = test_data.to_excel(index=False)
            self.assertIsNotNone(excel_buffer)
        except ImportError:
            # 如果沒有安裝 openpyxl，跳過此測試
            pass

    def test_data_compression(self):
        """測試資料壓縮功能"""
        import gzip

        # 創建測試資料
        test_string = "This is a test string for compression"

        # 壓縮資料
        compressed_data = gzip.compress(test_string.encode("utf-8"))

        # 解壓縮資料
        decompressed_data = gzip.decompress(compressed_data).decode("utf-8")

        # 驗證壓縮和解壓縮
        self.assertEqual(test_string, decompressed_data)
        self.assertLess(len(compressed_data), len(test_string.encode("utf-8")))


class TestPerformanceOptimization(unittest.TestCase):
    """測試效能優化功能"""

    def test_dataframe_optimization(self):
        """測試 DataFrame 記憶體優化"""
        # 創建測試資料
        test_data = pd.DataFrame(
            {
                "int_col": [1, 2, 3, 4, 5],
                "float_col": [1.1, 2.2, 3.3, 4.4, 5.5],
                "string_col": ["A", "B", "A", "B", "A"],
            }
        )

        # 記錄原始記憶體使用
        original_memory = test_data.memory_usage(deep=True).sum()

        # 優化資料類型
        optimized_data = test_data.copy()

        # 優化整數欄位
        for col in optimized_data.select_dtypes(include=["int64"]).columns:
            col_min = optimized_data[col].min()
            col_max = optimized_data[col].max()
            if col_min >= -128 and col_max <= 127:
                optimized_data[col] = optimized_data[col].astype("int8")

        # 優化字串欄位為類別
        for col in optimized_data.select_dtypes(include=["object"]).columns:
            if optimized_data[col].nunique() / len(optimized_data) < 0.5:
                optimized_data[col] = optimized_data[col].astype("category")

        # 記錄優化後記憶體使用
        optimized_memory = optimized_data.memory_usage(deep=True).sum()

        # 驗證記憶體使用減少
        self.assertLessEqual(optimized_memory, original_memory)


if __name__ == "__main__":
    unittest.main()
