"""歷史資料回填與驗證模組。

此模組提供歷史資料回填與驗證的統一接口，整合了四個核心功能：
- 分時段平行下載機制
- 增量更新識別模式
- 時間序列連續性檢查
- 異常值自動標記系統

主要功能：
- 高效率分時段並行下載歷史資料
- 智能識別並僅下載增量更新的資料
- 全面檢查時間序列的連續性和完整性
- 自動檢測、標記和處理異常值
- 提供詳細的數據品質報告和審查機制

此模組已重構為模組化架構，提供向後兼容的接口。
"""

import datetime
import logging
from typing import Any, Dict, List, Optional, Union

import pandas as pd

# 導入重構後的模組
try:
    from src.core.backfill import (
        BackfillConfig,
        BackfillManager,
        DataQualityReport,
        IncrementalUpdateInfo,
        OutlierDetectionMethod,
        OutlierTreatmentStrategy,
    )
    from src.core.data_ingest import DataIngestionManager
except ImportError as exc:
    raise ImportError(f"無法匯入必要模組，請確認模組結構正確。錯誤：{exc}") from exc

# 設定日誌
logger = logging.getLogger(__name__)


class HistoricalBackfill:
    """歷史資料回填與驗證類（向後兼容包裝器）。

    此類提供向後兼容的接口，內部使用重構後的模組化架構。
    支援分時段並行下載、增量更新識別、時間序列連續性檢查和自動異常值標記。

    主要功能：
    1. 分時段平行下載機制
    2. 增量更新識別模式
    3. 時間序列連續性檢查
    4. 異常值自動標記系統
    """

    def __init__(
        self,
        data_manager: Optional[DataIngestionManager] = None,
        max_workers: int = 5,
        chunk_size: int = 30,
        retry_attempts: int = 3,
        retry_delay: int = 5,
        z_score_threshold: float = 3.0,
        iqr_threshold: float = 1.5,
        outlier_detection_method: OutlierDetectionMethod = (
            OutlierDetectionMethod.Z_SCORE
        ),
        outlier_treatment: OutlierTreatmentStrategy = (
            OutlierTreatmentStrategy.MARK_ONLY
        ),
        enable_progress_tracking: bool = True,
        cache_dir: Optional[str] = None,
    ):
        """初始化歷史資料回填與驗證類。

        Args:
            data_manager: 資料擷取管理器
            max_workers: 最大工作執行緒數
            chunk_size: 每個時間切片的天數
            retry_attempts: 重試次數
            retry_delay: 重試延遲（秒）
            z_score_threshold: 異常值 Z 分數閾值
            iqr_threshold: IQR 異常值閾值
            outlier_detection_method: 異常值檢測方法
            outlier_treatment: 異常值處理策略
            enable_progress_tracking: 是否啟用進度追蹤
            cache_dir: 快取目錄路徑
        """
        # 創建配置
        self.config = BackfillConfig(
            max_workers=max_workers,
            chunk_size=chunk_size,
            retry_attempts=retry_attempts,
            retry_delay=retry_delay,
            z_score_threshold=z_score_threshold,
            iqr_threshold=iqr_threshold,
            outlier_detection_method=outlier_detection_method,
            outlier_treatment=outlier_treatment,
            enable_progress_tracking=enable_progress_tracking,
            cache_dir=cache_dir,
        )

        # 驗證配置
        self.config.validate()

        # 初始化數據管理器
        self.data_manager = data_manager or DataIngestionManager(use_cache=True)

        # 創建回填管理器
        self.manager = BackfillManager(self.config, self.data_manager)

        # 向後兼容的屬性
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.z_score_threshold = z_score_threshold
        self.iqr_threshold = iqr_threshold
        self.outlier_detection_method = outlier_detection_method
        self.outlier_treatment = outlier_treatment
        self.enable_progress_tracking = enable_progress_tracking

        # 統計信息（向後兼容）
        self.stats = {
            "total_symbols": 0,
            "data_points_downloaded": 0,
            "data_points_skipped": 0,
            "continuity_issues": 0,
            "outliers_detected": 0,
            "download_time": 0.0,
            "validation_time": 0.0,
        }

        # 增量更新追蹤（向後兼容）
        self.incremental_info: Dict[str, IncrementalUpdateInfo] = {}

        # 數據品質報告（向後兼容）
        self.quality_reports: Dict[str, DataQualityReport] = {}

    def parallel_download_with_time_segments(
        self,
        symbols: Union[str, List[str]],
        start_date: Union[str, datetime.date],
        end_date: Union[str, datetime.date],
        show_progress: bool = True,
    ) -> Dict[str, pd.DataFrame]:
        """分時段平行下載機制（向後兼容方法）。

        Args:
            symbols: 股票代碼或代碼列表
            start_date: 開始日期
            end_date: 結束日期
            show_progress: 是否顯示進度條

        Returns:
            Dict[str, pd.DataFrame]: 下載的資料
        """
        return self.manager.downloader.download_with_time_segments(
            symbols, start_date, end_date, show_progress
        )

    def incremental_update_detection(
        self,
        symbols: Union[str, List[str]],
        start_date: Union[str, datetime.date],
        end_date: Union[str, datetime.date],
    ) -> Dict[str, IncrementalUpdateInfo]:
        """增量更新識別模式（向後兼容方法）。

        Args:
            symbols: 股票代碼或代碼列表
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            Dict[str, IncrementalUpdateInfo]: 每個股票的增量更新資訊
        """
        result = self.manager.updater.detect_incremental_updates(
            symbols, start_date, end_date
        )
        self.incremental_info.update(result)
        return result

    def comprehensive_continuity_check(
        self,
        data: Dict[str, pd.DataFrame],
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> Dict[str, DataQualityReport]:
        """時間序列連續性檢查（向後兼容方法）。

        Args:
            data: 股票數據字典
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            Dict[str, DataQualityReport]: 每個股票的數據品質報告
        """
        result = self.manager.checker.check_comprehensive_continuity(
            data, start_date, end_date
        )
        self.quality_reports.update(result)
        return result

    def automated_outlier_detection_system(
        self,
        data: Dict[str, pd.DataFrame],
        methods: Optional[List[OutlierDetectionMethod]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """異常值自動標記系統（向後兼容方法）。

        Args:
            data: 股票數據字典
            methods: 檢測方法列表

        Returns:
            Dict[str, Dict[str, Any]]: 每個股票的異常值檢測結果
        """
        return self.manager.detector.detect_outliers_comprehensive(data, methods)

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
    ) -> Dict[str, Any]:
        """綜合的歷史資料回填與驗證（向後兼容方法）。

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
            Dict[str, Any]: 綜合回填結果
        """
        result = self.manager.comprehensive_backfill_with_validation(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            enable_incremental=enable_incremental,
            enable_validation=enable_validation,
            enable_outlier_detection=enable_outlier_detection,
            save_result=save_result,
            generate_report=generate_report,
        )

        # 更新向後兼容的屬性
        if result.incremental_info:
            self.incremental_info.update(result.incremental_info)
        if result.quality_reports:
            self.quality_reports.update(result.quality_reports)
        if result.statistics:
            self.stats.update(result.statistics)

        # 轉換為舊格式
        return result.to_dict()

    def get_progress_info(self) -> Dict[str, Any]:
        """獲取當前進度資訊（向後兼容方法）。

        Returns:
            Dict[str, Any]: 進度資訊
        """
        return self.manager.get_progress_info()


# 向後兼容的便捷函數
def backfill_historical_data(
    symbols: Union[str, List[str]],
    start_date: Union[str, datetime.date],
    end_date: Union[str, datetime.date],
    max_workers: int = 5,
    chunk_size: int = 30,
    validate: bool = True,
    save_result: bool = True,
    enable_incremental: bool = True,
    enable_outlier_detection: bool = True,
) -> Dict[str, Any]:
    """歷史資料回填的便捷函數（增強版）。

    整合了所有四個子功能的便捷接口。

    Args:
        symbols: 股票代碼或代碼列表
        start_date: 開始日期
        end_date: 結束日期
        max_workers: 最大工作執行緒數
        chunk_size: 每個時間切片的天數
        validate: 是否進行資料驗證
        save_result: 是否儲存結果
        enable_incremental: 是否啟用增量更新檢測
        enable_outlier_detection: 是否啟用異常值檢測

    Returns:
        Dict[str, Any]: 綜合回填結果
    """
    backfiller = HistoricalBackfill(
        max_workers=max_workers, chunk_size=chunk_size, enable_progress_tracking=True
    )

    return backfiller.comprehensive_backfill_with_validation(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        enable_incremental=enable_incremental,
        enable_validation=validate,
        enable_outlier_detection=enable_outlier_detection,
        save_result=save_result,
        generate_report=True,
    )
