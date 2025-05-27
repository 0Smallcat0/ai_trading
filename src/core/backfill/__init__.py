"""歷史資料回填與驗證模組。

此模組提供歷史資料回填與驗證的核心功能，包括：
- 分時段平行下載機制
- 增量更新識別模式  
- 時間序列連續性檢查
- 異常值自動標記系統
"""

from .data_structures import (
    BackfillConfig,
    ComprehensiveBackfillResult,
    DataQualityReport,
    DataQualityStatus,
    DownloadProgress,
    IncrementalUpdateInfo,
    OutlierDetectionMethod,
    OutlierDetectionResult,
    OutlierTreatmentStrategy,
)
from .parallel_downloader import ParallelDownloader
from .incremental_updater import IncrementalUpdater
from .continuity_checker import ContinuityChecker
from .outlier_detector import OutlierDetector
from .backfill_manager import BackfillManager

__all__ = [
    # Data structures
    "BackfillConfig",
    "ComprehensiveBackfillResult",
    "DataQualityReport",
    "DataQualityStatus",
    "DownloadProgress",
    "IncrementalUpdateInfo",
    "OutlierDetectionMethod",
    "OutlierDetectionResult",
    "OutlierTreatmentStrategy",
    # Core classes
    "ParallelDownloader",
    "IncrementalUpdater",
    "ContinuityChecker",
    "OutlierDetector",
    "BackfillManager",
]
