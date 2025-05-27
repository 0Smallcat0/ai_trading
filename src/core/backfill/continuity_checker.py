"""時間序列連續性檢查模組。

此模組實作時間序列連續性檢查，包括：
- 檢測歷史數據中的時間間隙
- 識別缺失的交易日數據
- 驗證數據時間順序的正確性
- 生成數據完整性報告
"""

import datetime
import logging
from typing import Dict, List

import pandas as pd

from .data_structures import DataQualityReport, DataQualityStatus

logger = logging.getLogger(__name__)


class ContinuityChecker:
    """時間序列連續性檢查器。"""

    def __init__(self):
        """初始化連續性檢查器。"""
        pass

    def check_comprehensive_continuity(
        self,
        data: Dict[str, pd.DataFrame],
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> Dict[str, DataQualityReport]:
        """執行全面的連續性檢查。

        Args:
            data: 股票數據字典
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            Dict[str, DataQualityReport]: 每個股票的數據品質報告
        """
        logger.info("開始時間序列連續性檢查：%d 個股票", len(data))

        reports = {}

        for symbol, dataframe in data.items():
            if dataframe.empty:
                # 創建空數據的報告
                report = self._create_empty_data_report(symbol, start_date, end_date)
            else:
                # 執行詳細的連續性檢查
                report = self._perform_detailed_continuity_check(
                    symbol, dataframe, start_date, end_date
                )

            reports[symbol] = report

        logger.info("時間序列連續性檢查完成")
        return reports

    def _create_empty_data_report(
        self, symbol: str, start_date: datetime.date, end_date: datetime.date
    ) -> DataQualityReport:
        """創建空數據的品質報告。"""
        return DataQualityReport(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            quality_status=DataQualityStatus.POOR,
            issues=["數據為空"],
            recommendations=["重新下載數據"],
        )

    def _perform_detailed_continuity_check(
        self,
        symbol: str,
        dataframe: pd.DataFrame,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> DataQualityReport:
        """執行詳細的連續性檢查。

        Args:
            symbol: 股票代碼
            dataframe: 股票數據
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            DataQualityReport: 數據品質報告
        """
        report = DataQualityReport(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            total_records=len(dataframe),
        )

        # 確保索引是日期時間類型
        dataframe = self._ensure_datetime_index(dataframe, report)
        if not dataframe.index.dtype.name.startswith("datetime"):
            return report

        # 檢查數據是否已排序
        self._check_data_sorting(dataframe, report)

        # 獲取預期的交易日期並檢查連續性
        self._check_trading_date_continuity(dataframe, report, start_date, end_date)

        # 檢查重複日期
        self._check_duplicate_dates(dataframe, report)

        # 檢查數據間隔
        self._check_data_intervals(dataframe, report)

        # 評估數據品質狀態
        self._assess_quality_status(report)

        # 生成建議
        self._generate_recommendations(report)

        return report

    def _ensure_datetime_index(
        self, dataframe: pd.DataFrame, report: DataQualityReport
    ) -> pd.DataFrame:
        """確保索引是日期時間類型。"""
        if not isinstance(dataframe.index, pd.DatetimeIndex):
            try:
                dataframe.index = pd.to_datetime(dataframe.index)
            except Exception as exc:
                report.issues.append(f"無法轉換索引為日期時間格式: {exc}")
                report.quality_status = DataQualityStatus.POOR
        return dataframe

    def _check_data_sorting(
        self, dataframe: pd.DataFrame, report: DataQualityReport
    ) -> None:
        """檢查數據是否已排序。"""
        if not dataframe.index.is_monotonic_increasing:
            report.issues.append("數據時間順序不正確")

    def _check_trading_date_continuity(
        self,
        dataframe: pd.DataFrame,
        report: DataQualityReport,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> None:
        """檢查交易日期連續性。"""
        try:
            from src.utils.utils import get_trading_dates

            expected_dates = set(get_trading_dates(start_date, end_date))
        except Exception as exc:
            report.issues.append(f"無法獲取交易日期: {exc}")
            expected_dates = set()

        # 獲取實際的日期
        actual_dates = set(dataframe.index.date)

        # 找出缺失的日期
        missing_dates = sorted(expected_dates - actual_dates)
        report.missing_dates = missing_dates

        # 計算連續性分數
        if expected_dates:
            report.continuity_score = 1.0 - (len(missing_dates) / len(expected_dates))
        else:
            report.continuity_score = 1.0

    def _check_duplicate_dates(
        self, dataframe: pd.DataFrame, report: DataQualityReport
    ) -> None:
        """檢查重複日期。"""
        duplicate_dates = dataframe.index[dataframe.index.duplicated()].tolist()
        if duplicate_dates:
            report.issues.append(f"發現重複日期: {len(duplicate_dates)} 個")

    def _check_data_intervals(
        self, dataframe: pd.DataFrame, report: DataQualityReport
    ) -> None:
        """檢查數據時間間隔。

        Args:
            dataframe: 股票數據
            report: 數據品質報告
        """
        if len(dataframe) < 2:
            return

        # 計算時間間隔
        intervals = dataframe.index[1:] - dataframe.index[:-1]

        # 檢查異常間隔（超過5天的間隔）
        long_intervals = intervals[intervals > pd.Timedelta(days=5)]

        if len(long_intervals) > 0:
            report.issues.append(f"發現 {len(long_intervals)} 個異常長的時間間隔")

        # 檢查週末和假日
        weekend_data = dataframe[dataframe.index.weekday >= 5]
        if len(weekend_data) > 0:
            report.issues.append(f"發現 {len(weekend_data)} 個週末數據點")

    def _assess_quality_status(self, report: DataQualityReport) -> None:
        """評估數據品質狀態。

        Args:
            report: 數據品質報告
        """
        # 根據連續性分數和問題數量評估品質
        issue_count = len(report.issues)

        if report.continuity_score >= 0.95 and issue_count == 0:
            report.quality_status = DataQualityStatus.EXCELLENT
        elif report.continuity_score >= 0.90 and issue_count <= 2:
            report.quality_status = DataQualityStatus.GOOD
        elif report.continuity_score >= 0.80 and issue_count <= 5:
            report.quality_status = DataQualityStatus.FAIR
        else:
            report.quality_status = DataQualityStatus.POOR

    def _generate_recommendations(self, report: DataQualityReport) -> None:
        """生成改進建議。

        Args:
            report: 數據品質報告
        """
        if report.missing_dates:
            if len(report.missing_dates) <= 5:
                report.recommendations.append("下載缺失的特定日期數據")
            else:
                report.recommendations.append("重新下載整個時間範圍的數據")

        if any("重複日期" in issue for issue in report.issues):
            report.recommendations.append("移除重複的日期記錄")

        if any("時間順序不正確" in issue for issue in report.issues):
            report.recommendations.append("對數據按日期排序")

        if any("週末數據" in issue for issue in report.issues):
            report.recommendations.append("移除週末和假日的數據點")

        if report.continuity_score < 0.8:
            report.recommendations.append("考慮重新收集數據以提高完整性")

    def validate_single_series(
        self, dataframe: pd.DataFrame, symbol: str = "Unknown"
    ) -> DataQualityReport:
        """驗證單個時間序列。

        Args:
            dataframe: 時間序列數據
            symbol: 股票代碼

        Returns:
            DataQualityReport: 數據品質報告
        """
        if dataframe.empty:
            return DataQualityReport(
                symbol=symbol,
                start_date=datetime.date.today(),
                end_date=datetime.date.today(),
                quality_status=DataQualityStatus.POOR,
                issues=["數據為空"],
            )

        # 確保索引是日期時間類型
        if not isinstance(dataframe.index, pd.DatetimeIndex):
            dataframe.index = pd.to_datetime(dataframe.index)

        # 獲取日期範圍
        start_date = dataframe.index.min().date()
        end_date = dataframe.index.max().date()

        # 執行檢查
        return self._perform_detailed_continuity_check(
            symbol, dataframe, start_date, end_date
        )

    def fix_continuity_issues(
        self, dataframe: pd.DataFrame, report: DataQualityReport
    ) -> pd.DataFrame:
        """修復連續性問題。

        Args:
            dataframe: 原始數據
            report: 品質報告

        Returns:
            pd.DataFrame: 修復後的數據
        """
        fixed_data = dataframe.copy()

        # 排序索引
        if not fixed_data.index.is_monotonic_increasing:
            fixed_data = fixed_data.sort_index()

        # 移除重複項
        if fixed_data.index.duplicated().any():
            fixed_data = fixed_data[~fixed_data.index.duplicated(keep="first")]

        # 移除週末數據
        if any("週末數據" in issue for issue in report.issues):
            fixed_data = fixed_data[fixed_data.index.weekday < 5]

        return fixed_data
