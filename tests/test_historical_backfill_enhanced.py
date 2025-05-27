"""
測試歷史資料回填與驗證模組的增強功能

測試四個主要子功能：
1. 分時段平行下載機制
2. 增量更新識別模式
3. 時間序列連續性檢查
4. 異常值自動標記系統
"""

import datetime
import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np

from src.core.historical_backfill import (
    HistoricalBackfill,
    OutlierDetectionMethod,
    OutlierTreatmentStrategy,
    backfill_historical_data,
)
from src.core.backfill import (
    DataQualityStatus,
    DataQualityReport,
    IncrementalUpdateInfo,
)


class TestHistoricalBackfillEnhanced(unittest.TestCase):
    """測試歷史資料回填增強功能"""

    def setUp(self):
        """設置測試環境"""
        self.mock_data_manager = Mock()
        self.backfiller = HistoricalBackfill(
            data_manager=self.mock_data_manager,
            max_workers=2,
            chunk_size=10,
            enable_progress_tracking=True,
        )

        # 創建測試數據
        self.test_dates = pd.date_range('2023-01-01', '2023-01-31', freq='D')
        self.test_data = pd.DataFrame({
            'open': np.random.uniform(100, 110, len(self.test_dates)),
            'high': np.random.uniform(110, 120, len(self.test_dates)),
            'low': np.random.uniform(90, 100, len(self.test_dates)),
            'close': np.random.uniform(95, 115, len(self.test_dates)),
            'volume': np.random.randint(1000, 10000, len(self.test_dates)),
        }, index=self.test_dates)

    def test_parallel_download_with_time_segments(self):
        """測試分時段平行下載機制"""
        # 模擬數據管理器返回數據
        self.mock_data_manager.get_historical_data.return_value = {
            'AAPL': self.test_data
        }

        # 執行分時段下載
        result = self.backfiller.parallel_download_with_time_segments(
            symbols=['AAPL'],
            start_date='2023-01-01',
            end_date='2023-01-31',
            show_progress=False
        )

        # 驗證結果
        self.assertIn('AAPL', result)
        self.assertIsInstance(result['AAPL'], pd.DataFrame)
        self.assertGreater(len(result['AAPL']), 0)

        # 驗證數據管理器被調用
        self.mock_data_manager.get_historical_data.assert_called()

    def test_incremental_update_detection(self):
        """測試增量更新識別模式"""
        with patch('src.core.data_ingest.load_data') as mock_load_data:
            # 模擬本地數據（部分數據）
            local_data = self.test_data.iloc[:15]  # 只有前15天的數據
            mock_load_data.return_value = local_data

            # 執行增量更新檢測
            update_info = self.backfiller.incremental_update_detection(
                symbols=['AAPL'],
                start_date='2023-01-01',
                end_date='2023-01-31'
            )

            # 驗證結果
            self.assertIn('AAPL', update_info)
            self.assertIsInstance(update_info['AAPL'], IncrementalUpdateInfo)
            # 應該需要更新（因為本地數據不完整）
            self.assertTrue(update_info['AAPL'].needs_update)

    def test_comprehensive_continuity_check(self):
        """測試時間序列連續性檢查"""
        # 創建有缺失日期的測試數據
        incomplete_data = self.test_data.drop(self.test_data.index[10:15])  # 移除中間5天
        test_data_dict = {'AAPL': incomplete_data}

        with patch('src.utils.utils.get_trading_dates') as mock_trading_dates:
            # 模擬交易日期
            mock_trading_dates.return_value = [d.date() for d in self.test_dates]

            # 執行連續性檢查
            reports = self.backfiller.comprehensive_continuity_check(
                data=test_data_dict,
                start_date=datetime.date(2023, 1, 1),
                end_date=datetime.date(2023, 1, 31)
            )

            # 驗證結果
            self.assertIn('AAPL', reports)
            report = reports['AAPL']
            self.assertIsInstance(report, DataQualityReport)
            self.assertGreater(len(report.missing_dates), 0)  # 應該檢測到缺失日期
            self.assertLess(report.continuity_score, 1.0)  # 連續性分數應該小於1

    def test_automated_outlier_detection_system(self):
        """測試異常值自動標記系統"""
        # 創建包含異常值的測試數據
        outlier_data = self.test_data.copy()
        # 添加明顯的異常值
        outlier_data.iloc[10, outlier_data.columns.get_loc('close')] = 1000  # 異常高價
        outlier_data.iloc[20, outlier_data.columns.get_loc('close')] = 1  # 異常低價

        test_data_dict = {'AAPL': outlier_data}

        # 執行異常值檢測
        outlier_results = self.backfiller.automated_outlier_detection_system(
            data=test_data_dict,
            methods=[OutlierDetectionMethod.Z_SCORE, OutlierDetectionMethod.IQR]
        )

        # 驗證結果
        self.assertIn('AAPL', outlier_results)
        result = outlier_results['AAPL']
        self.assertTrue(result['outliers_detected'])  # 應該檢測到異常值
        self.assertGreater(result['outlier_count'], 0)  # 異常值數量應該大於0
        self.assertGreater(result['outlier_percentage'], 0)  # 異常值百分比應該大於0

    def test_z_score_outlier_detection(self):
        """測試Z-score異常值檢測方法"""
        # 創建包含異常值的數據
        outlier_data = self.test_data.copy()
        outlier_data.iloc[10, outlier_data.columns.get_loc('close')] = 1000

        # 執行Z-score檢測（通過異常值檢測系統）
        result = self.backfiller.automated_outlier_detection_system(
            {'AAPL': outlier_data},
            methods=[OutlierDetectionMethod.Z_SCORE]
        )

        # 驗證結果
        self.assertIn('AAPL', result)
        self.assertTrue(result['AAPL']['outliers_detected'])
        self.assertGreater(result['AAPL']['outlier_count'], 0)

    def test_iqr_outlier_detection(self):
        """測試IQR異常值檢測方法"""
        # 創建包含異常值的數據
        outlier_data = self.test_data.copy()
        outlier_data.iloc[10, outlier_data.columns.get_loc('close')] = 1000

        # 執行IQR檢測（通過異常值檢測系統）
        result = self.backfiller.automated_outlier_detection_system(
            {'AAPL': outlier_data},
            methods=[OutlierDetectionMethod.IQR]
        )

        # 驗證結果
        self.assertIn('AAPL', result)
        self.assertTrue(result['AAPL']['outliers_detected'])
        self.assertGreater(result['AAPL']['outlier_count'], 0)

    def test_comprehensive_backfill_with_validation(self):
        """測試綜合回填與驗證功能"""
        # 模擬數據管理器返回數據
        self.mock_data_manager.get_historical_data.return_value = {
            'AAPL': self.test_data
        }

        with patch('src.utils.utils.get_trading_dates') as mock_trading_dates:
            # 模擬交易日期
            mock_trading_dates.return_value = [d.date() for d in self.test_dates]

            # 執行綜合回填
            result = self.backfiller.comprehensive_backfill_with_validation(
                symbols=['AAPL'],
                start_date='2023-01-01',
                end_date='2023-01-31',
                enable_incremental=False,  # 跳過增量檢測以簡化測試
                enable_validation=True,
                enable_outlier_detection=True,
                save_result=False,
                generate_report=True
            )

            # 驗證結果
            self.assertTrue(result['success'])
            # 新的返回格式可能不包含 'data' 鍵，檢查其他關鍵字段
            self.assertIn('symbols', result)
            self.assertIn('statistics', result)
            self.assertIn('execution_time', result)

    def test_data_quality_report_creation(self):
        """測試數據品質報告創建"""
        report = DataQualityReport(
            symbol='AAPL',
            start_date=datetime.date(2023, 1, 1),
            end_date=datetime.date(2023, 1, 31),
            total_records=100,
            continuity_score=0.95,
            quality_status=DataQualityStatus.GOOD
        )

        # 測試轉換為字典
        report_dict = report.to_dict()
        self.assertEqual(report_dict['symbol'], 'AAPL')
        self.assertEqual(report_dict['quality_status'], 'good')
        self.assertEqual(report_dict['continuity_score'], 0.95)

    def test_progress_tracking(self):
        """測試進度追蹤功能"""
        # 獲取初始進度
        progress = self.backfiller.get_progress_info()
        self.assertEqual(progress['completed_symbols'], 0)
        self.assertEqual(progress['total_symbols'], 0)

        # 進度追蹤功能已經整合到新的模組化架構中
        # 這裡只測試接口是否正常工作
        self.assertIsInstance(progress, dict)
        self.assertIn('symbol_progress', progress)
        self.assertIn('chunk_progress', progress)

    def test_convenience_function(self):
        """測試便捷函數"""
        with patch('src.core.historical_backfill.HistoricalBackfill') as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            mock_instance.comprehensive_backfill_with_validation.return_value = {
                'success': True,
                'data': {'AAPL': self.test_data}
            }

            # 調用便捷函數
            result = backfill_historical_data(
                symbols='AAPL',
                start_date='2023-01-01',
                end_date='2023-01-31'
            )

            # 驗證結果
            self.assertTrue(result['success'])
            mock_class.assert_called_once()
            mock_instance.comprehensive_backfill_with_validation.assert_called_once()


if __name__ == '__main__':
    unittest.main()
