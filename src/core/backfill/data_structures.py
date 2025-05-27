"""數據結構定義模組。

此模組定義了歷史資料回填與驗證機制中使用的所有數據結構，
包括枚舉類型、數據類別和配置類別。
"""

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class OutlierDetectionMethod(Enum):
    """異常值檢測方法枚舉。"""
    Z_SCORE = "z_score"
    IQR = "iqr"
    ISOLATION_FOREST = "isolation_forest"
    MODIFIED_Z_SCORE = "modified_z_score"


class OutlierTreatmentStrategy(Enum):
    """異常值處理策略枚舉。"""
    MARK_ONLY = "mark_only"  # 僅標記，不處理
    CLIP = "clip"  # 截斷到閾值
    REMOVE = "remove"  # 移除異常值
    INTERPOLATE = "interpolate"  # 插值替換


class DataQualityStatus(Enum):
    """數據品質狀態枚舉。"""
    EXCELLENT = "excellent"  # 優秀：無缺失，無異常
    GOOD = "good"  # 良好：少量缺失或異常
    FAIR = "fair"  # 一般：中等缺失或異常
    POOR = "poor"  # 差：大量缺失或異常


@dataclass
class DownloadProgress:
    """下載進度追蹤數據類別。"""
    total_symbols: int = 0
    completed_symbols: int = 0
    total_chunks: int = 0
    completed_chunks: int = 0
    failed_chunks: int = 0
    start_time: Optional[datetime.datetime] = None
    estimated_completion: Optional[datetime.datetime] = None
    current_symbol: str = ""
    current_chunk: str = ""
    
    @property
    def symbol_progress(self) -> float:
        """計算股票進度百分比。
        
        Returns:
            float: 股票進度百分比 (0-100)
        """
        if self.total_symbols <= 0:
            return 0.0
        return (self.completed_symbols / self.total_symbols * 100)
    
    @property
    def chunk_progress(self) -> float:
        """計算分塊進度百分比。
        
        Returns:
            float: 分塊進度百分比 (0-100)
        """
        if self.total_chunks <= 0:
            return 0.0
        return (self.completed_chunks / self.total_chunks * 100)


@dataclass
class DataQualityReport:
    """數據品質報告數據類別。"""
    symbol: str
    start_date: datetime.date
    end_date: datetime.date
    total_records: int = 0
    missing_dates: List[datetime.date] = field(default_factory=list)
    continuity_score: float = 0.0
    outliers_detected: Dict[str, int] = field(default_factory=dict)
    outlier_percentage: float = 0.0
    quality_status: DataQualityStatus = DataQualityStatus.POOR
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式。
        
        Returns:
            Dict[str, Any]: 字典格式的報告數據
        """
        return {
            "symbol": self.symbol,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "total_records": self.total_records,
            "missing_dates": [d.isoformat() for d in self.missing_dates],
            "continuity_score": self.continuity_score,
            "outliers_detected": self.outliers_detected,
            "outlier_percentage": self.outlier_percentage,
            "quality_status": self.quality_status.value,
            "issues": self.issues,
            "recommendations": self.recommendations
        }


@dataclass
class IncrementalUpdateInfo:
    """增量更新資訊數據類別。"""
    symbol: str
    last_update: Optional[datetime.datetime] = None
    local_checksum: Optional[str] = None
    remote_checksum: Optional[str] = None
    needs_update: bool = True
    update_ranges: List[Tuple[datetime.date, datetime.date]] = field(
        default_factory=list
    )
    conflict_resolution: str = "remote_wins"  # remote_wins, local_wins, merge


@dataclass
class BackfillConfig:
    """回填配置數據類別。"""
    max_workers: int = 5
    chunk_size: int = 30
    retry_attempts: int = 3
    retry_delay: int = 5
    z_score_threshold: float = 3.0
    iqr_threshold: float = 1.5
    outlier_detection_method: OutlierDetectionMethod = OutlierDetectionMethod.Z_SCORE
    outlier_treatment: OutlierTreatmentStrategy = OutlierTreatmentStrategy.MARK_ONLY
    enable_progress_tracking: bool = True
    cache_dir: Optional[str] = None
    
    def validate(self) -> None:
        """驗證配置參數的有效性。
        
        Raises:
            ValueError: 當配置參數無效時
        """
        if self.max_workers <= 0:
            raise ValueError("max_workers must be positive")
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if self.retry_attempts < 0:
            raise ValueError("retry_attempts must be non-negative")
        if self.retry_delay < 0:
            raise ValueError("retry_delay must be non-negative")
        if self.z_score_threshold <= 0:
            raise ValueError("z_score_threshold must be positive")
        if self.iqr_threshold <= 0:
            raise ValueError("iqr_threshold must be positive")


@dataclass
class OutlierDetectionResult:
    """異常值檢測結果數據類別。"""
    method: str
    threshold: Optional[float] = None
    indices: List[Any] = field(default_factory=list)
    column_details: Dict[str, List[Any]] = field(default_factory=dict)
    error: Optional[str] = None
    
    @property
    def has_outliers(self) -> bool:
        """檢查是否檢測到異常值。
        
        Returns:
            bool: 如果檢測到異常值則返回True
        """
        return len(self.indices) > 0


@dataclass
class ComprehensiveBackfillResult:
    """綜合回填結果數據類別。"""
    symbols: List[str]
    start_date: datetime.date
    end_date: datetime.date
    data: Dict[str, Any] = field(default_factory=dict)
    incremental_info: Dict[str, IncrementalUpdateInfo] = field(
        default_factory=dict
    )
    quality_reports: Dict[str, DataQualityReport] = field(default_factory=dict)
    outlier_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    statistics: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    success: bool = False
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式。
        
        Returns:
            Dict[str, Any]: 字典格式的結果數據
        """
        return {
            "symbols": self.symbols,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "statistics": self.statistics,
            "execution_time": self.execution_time,
            "success": self.success,
            "error": self.error,
            "quality_reports": {
                symbol: report.to_dict() 
                for symbol, report in self.quality_reports.items()
            },
            "outlier_results": self.outlier_results,
            "incremental_info": {
                symbol: {
                    "symbol": info.symbol,
                    "needs_update": info.needs_update,
                    "update_ranges": [
                        (r[0].isoformat(), r[1].isoformat()) 
                        for r in info.update_ranges
                    ],
                    "last_update": (
                        info.last_update.isoformat() 
                        if info.last_update else None
                    )
                }
                for symbol, info in self.incremental_info.items()
            }
        }
