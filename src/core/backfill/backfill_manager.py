"""歷史資料回填管理器。

此模組整合所有回填功能，提供統一的接口：
- 綜合回填與驗證
- 統計報告生成
- 結果儲存
"""

import datetime
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Union

import pandas as pd

from .continuity_checker import ContinuityChecker
from .data_structures import (
    BackfillConfig,
    ComprehensiveBackfillResult,
    DataQualityReport,
    OutlierDetectionMethod,
)
from .incremental_updater import IncrementalUpdater
from .outlier_detector import OutlierDetector
from .parallel_downloader import ParallelDownloader

logger = logging.getLogger(__name__)


class BackfillManager:
    """歷史資料回填管理器。"""

    def __init__(self, config: BackfillConfig, data_manager=None):
        """初始化回填管理器。

        Args:
            config: 回填配置
            data_manager: 數據管理器實例
        """
        self.config = config
        self.data_manager = data_manager

        # 初始化各個組件
        self.downloader = ParallelDownloader(config, data_manager)
        self.updater = IncrementalUpdater(data_manager)
        self.checker = ContinuityChecker()
        self.detector = OutlierDetector(config)

        # 設定快取目錄
        self.cache_dir = (
            Path(config.cache_dir) if config.cache_dir else Path("data/cache/backfill")
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def comprehensive_backfill_with_validation(
        self,
        symbols: Union[str, List[str]],
        start_date: Union[str, datetime.date],
        end_date: Union[str, datetime.date],
        enable_incremental: bool = True,
        enable_validation: bool = True,
        enable_outlier_detection: bool = True,
        save_result: bool = True,
        generate_report: bool = True,
    ) -> ComprehensiveBackfillResult:
        """執行綜合的歷史資料回填與驗證。

        Args:
            symbols: 股票代碼或代碼列表
            start_date: 開始日期
            end_date: 結束日期
            enable_incremental: 是否啟用增量更新檢測
            enable_validation: 是否啟用數據驗證
            enable_outlier_detection: 是否啟用異常值檢測
            save_result: 是否儲存結果
            generate_report: 是否生成報告

        Returns:
            ComprehensiveBackfillResult: 綜合回填結果
        """
        start_time = time.time()

        # 標準化輸入參數
        symbols = self._normalize_symbols(symbols)
        start_date = self._normalize_date(start_date)
        end_date = self._normalize_date(end_date)

        logger.info(
            "開始綜合歷史資料回填：%d 個股票，時間範圍 %s 到 %s",
            len(symbols),
            start_date,
            end_date,
        )

        result = ComprehensiveBackfillResult(
            symbols=symbols, start_date=start_date, end_date=end_date
        )

        try:
            # 步驟 1: 增量更新檢測
            if enable_incremental:
                result = self._perform_incremental_detection(
                    result, symbols, start_date, end_date
                )
                symbols_to_update = self._filter_symbols_for_update(result)

                if not symbols_to_update:
                    logger.info("所有股票數據都是最新的，無需下載")
                    result.success = True
                    result.execution_time = time.time() - start_time
                    return result
            else:
                symbols_to_update = symbols

            # 步驟 2: 分時段平行下載
            result = self._perform_parallel_download(
                result, symbols_to_update, start_date, end_date
            )

            if not result.data:
                logger.warning("沒有成功下載任何數據")
                result.success = False
                result.execution_time = time.time() - start_time
                return result

            # 步驟 3: 時間序列連續性檢查
            if enable_validation:
                result = self._perform_continuity_check(result, start_date, end_date)

            # 步驟 4: 異常值自動檢測
            if enable_outlier_detection:
                result = self._perform_outlier_detection(result)

            # 步驟 5: 儲存結果
            if save_result:
                self._save_result(result.data)

            # 步驟 6: 生成統計報告
            result.statistics = self._generate_comprehensive_statistics(result)

            # 步驟 7: 生成綜合報告
            if generate_report:
                self._save_comprehensive_report(result)

            result.success = True
            result.execution_time = time.time() - start_time

            logger.info("綜合歷史資料回填完成，耗時 %.2f 秒", result.execution_time)

        except Exception as exc:
            logger.error("綜合歷史資料回填失敗: %s", exc, exc_info=True)
            result.success = False
            result.error = str(exc)
            result.execution_time = time.time() - start_time

        return result

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

    def _perform_incremental_detection(
        self,
        result: ComprehensiveBackfillResult,
        symbols: List[str],
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> ComprehensiveBackfillResult:
        """執行增量更新檢測。"""
        logger.info("步驟 1: 執行增量更新檢測")
        incremental_info = self.updater.detect_incremental_updates(
            symbols, start_date, end_date
        )
        result.incremental_info = incremental_info
        return result

    def _filter_symbols_for_update(
        self, result: ComprehensiveBackfillResult
    ) -> List[str]:
        """過濾出需要更新的股票。"""
        symbols_to_update = [
            symbol
            for symbol, info in result.incremental_info.items()
            if info.needs_update
        ]
        logger.info("需要更新的股票：%d 個", len(symbols_to_update))
        return symbols_to_update

    def _perform_parallel_download(
        self,
        result: ComprehensiveBackfillResult,
        symbols: List[str],
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> ComprehensiveBackfillResult:
        """執行分時段平行下載。"""
        logger.info("步驟 2: 執行分時段平行下載")
        downloaded_data = self.downloader.download_with_time_segments(
            symbols, start_date, end_date
        )
        result.data = downloaded_data
        return result

    def _perform_continuity_check(
        self,
        result: ComprehensiveBackfillResult,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> ComprehensiveBackfillResult:
        """執行時間序列連續性檢查。"""
        logger.info("步驟 3: 執行時間序列連續性檢查")
        quality_reports = self.checker.check_comprehensive_continuity(
            result.data, start_date, end_date
        )
        result.quality_reports = quality_reports
        return result

    def _perform_outlier_detection(
        self, result: ComprehensiveBackfillResult
    ) -> ComprehensiveBackfillResult:
        """執行異常值自動檢測。"""
        logger.info("步驟 4: 執行異常值自動檢測")
        outlier_results = self.detector.detect_outliers_comprehensive(result.data)
        result.outlier_results = outlier_results
        return result

    def _generate_comprehensive_statistics(
        self, result: ComprehensiveBackfillResult
    ) -> Dict[str, Any]:
        """生成綜合統計資訊。"""
        stats = {
            "total_symbols": len(result.data),
            "total_records": sum(len(df) for df in result.data.values()),
            "data_quality": {"excellent": 0, "good": 0, "fair": 0, "poor": 0},
            "outlier_summary": {
                "symbols_with_outliers": 0,
                "total_outliers": 0,
                "average_outlier_percentage": 0.0,
            },
            "continuity_summary": {
                "average_continuity_score": 0.0,
                "symbols_with_missing_data": 0,
                "total_missing_dates": 0,
            },
        }

        # 統計數據品質
        for report in result.quality_reports.values():
            stats["data_quality"][report.quality_status.value] += 1
            stats["continuity_summary"]["total_missing_dates"] += len(
                report.missing_dates
            )
            if report.missing_dates:
                stats["continuity_summary"]["symbols_with_missing_data"] += 1

        # 計算平均連續性分數
        if result.quality_reports:
            avg_continuity = sum(
                r.continuity_score for r in result.quality_reports.values()
            ) / len(result.quality_reports)
            stats["continuity_summary"]["average_continuity_score"] = avg_continuity

        # 統計異常值
        outlier_percentages = []
        for outlier_result in result.outlier_results.values():
            if outlier_result["outliers_detected"]:
                stats["outlier_summary"]["symbols_with_outliers"] += 1
                stats["outlier_summary"]["total_outliers"] += outlier_result[
                    "outlier_count"
                ]
                outlier_percentages.append(outlier_result["outlier_percentage"])

        # 計算平均異常值百分比
        if outlier_percentages:
            stats["outlier_summary"]["average_outlier_percentage"] = sum(
                outlier_percentages
            ) / len(outlier_percentages)

        return stats

    def _save_comprehensive_report(self, result: ComprehensiveBackfillResult) -> None:
        """儲存綜合報告。"""
        try:
            report_dir = self.cache_dir / "reports"
            report_dir.mkdir(exist_ok=True)

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = report_dir / f"backfill_report_{timestamp}.json"

            # 儲存報告
            with open(report_file, "w", encoding="utf-8") as file:
                json.dump(result.to_dict(), file, indent=2, ensure_ascii=False)

            logger.info("綜合報告已儲存至: %s", report_file)

        except Exception as exc:
            logger.error("儲存綜合報告失敗: %s", exc)

    def _save_result(self, data: Dict[str, pd.DataFrame]) -> None:
        """儲存回填的資料。"""
        if not data:
            return

        try:
            # 將資料轉換為 MultiIndex DataFrame
            dfs = []
            for symbol, dataframe in data.items():
                if not dataframe.empty:
                    # 添加股票代碼層級
                    dataframe = dataframe.copy()
                    dataframe["symbol"] = symbol
                    dataframe.set_index("symbol", append=True, inplace=True)
                    # 調整層級順序
                    dataframe = dataframe.swaplevel()
                    dfs.append(dataframe)

            if dfs:
                # 合併所有資料
                combined_df = pd.concat(dfs)

                # 儲存為 Parquet 檔案
                try:
                    from src.database.parquet_utils import save_to_parquet

                    save_to_parquet(combined_df, "price_backfill")
                except ImportError:
                    # 如果沒有 parquet_utils，使用 pandas 直接儲存
                    output_file = self.cache_dir / "backfill_data.parquet"
                    combined_df.to_parquet(output_file)

                logger.info("已儲存回填的資料，共 %d 筆", len(combined_df))
        except Exception as exc:
            logger.error("儲存回填的資料時發生錯誤: %s", exc)

    def get_progress_info(self) -> Dict[str, Any]:
        """獲取當前進度資訊。"""
        return self.downloader.get_progress_info()
