"""異常值自動標記模組。

此模組實作異常值自動標記系統，包括：
- 多種統計方法檢測價格異常
- 標記可疑的價格跳躍或成交量異常
- 建立異常值處理策略
- 提供異常值審查和確認機制
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

from .data_structures import (
    BackfillConfig,
    OutlierDetectionMethod,
    OutlierDetectionResult,
    OutlierTreatmentStrategy,
)

logger = logging.getLogger(__name__)


class OutlierDetector:
    """異常值檢測器。"""

    def __init__(self, config: BackfillConfig):
        """初始化異常值檢測器。

        Args:
            config: 回填配置
        """
        self.config = config

    def detect_outliers_comprehensive(
        self,
        data: Dict[str, pd.DataFrame],
        methods: Optional[List[OutlierDetectionMethod]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """執行全面的異常值檢測。

        Args:
            data: 股票數據字典
            methods: 檢測方法列表

        Returns:
            Dict[str, Dict[str, Any]]: 每個股票的異常值檢測結果
        """
        if methods is None:
            methods = [self.config.outlier_detection_method]

        logger.info(
            "開始異常值檢測：%d 個股票，使用方法: %s",
            len(data),
            [m.value for m in methods],
        )

        outlier_results = {}

        for symbol, dataframe in data.items():
            if dataframe.empty:
                outlier_results[symbol] = self._create_empty_result()
                continue

            # 對每種方法進行異常值檢測
            symbol_results = self._detect_outliers_multiple_methods(
                symbol, dataframe, methods
            )
            outlier_results[symbol] = symbol_results

        logger.info("異常值檢測完成")
        return outlier_results

    def _create_empty_result(self) -> Dict[str, Any]:
        """創建空的檢測結果。"""
        return {
            "outliers_detected": False,
            "outlier_count": 0,
            "outlier_percentage": 0.0,
            "methods_used": [],
            "outlier_indices": [],
            "outlier_details": {},
            "treatment_applied": False,
        }

    def _detect_outliers_multiple_methods(
        self,
        symbol: str,
        dataframe: pd.DataFrame,
        methods: List[OutlierDetectionMethod],
    ) -> Dict[str, Any]:
        """使用多種方法檢測異常值。

        Args:
            symbol: 股票代碼
            dataframe: 股票數據
            methods: 檢測方法列表

        Returns:
            Dict[str, Any]: 異常值檢測結果
        """
        all_outlier_indices = set()
        outlier_details = {}
        methods_used = []

        for method in methods:
            try:
                result = self._detect_by_method(method, dataframe)

                outlier_details[method.value] = result.__dict__
                all_outlier_indices.update(result.indices)
                methods_used.append(method.value)

            except Exception as exc:
                logger.warning(
                    "使用 %s 方法檢測 %s 異常值失敗: %s", method.value, symbol, exc
                )

        # 統計結果
        outlier_count = len(all_outlier_indices)
        outlier_percentage = (
            (outlier_count / len(dataframe) * 100) if len(dataframe) > 0 else 0.0
        )

        # 應用處理策略
        treatment_applied = False
        if (
            outlier_count > 0
            and self.config.outlier_treatment != OutlierTreatmentStrategy.MARK_ONLY
        ):
            try:
                self._apply_outlier_treatment(dataframe, list(all_outlier_indices))
                treatment_applied = True
            except Exception as exc:
                logger.warning("應用異常值處理策略失敗: %s", exc)

        return {
            "outliers_detected": outlier_count > 0,
            "outlier_count": outlier_count,
            "outlier_percentage": outlier_percentage,
            "methods_used": methods_used,
            "outlier_indices": sorted(list(all_outlier_indices)),
            "outlier_details": outlier_details,
            "treatment_applied": treatment_applied,
        }

    def _detect_by_method(
        self, method: OutlierDetectionMethod, dataframe: pd.DataFrame
    ) -> OutlierDetectionResult:
        """根據指定方法檢測異常值。"""
        if method == OutlierDetectionMethod.Z_SCORE:
            return self._detect_outliers_zscore(dataframe)
        elif method == OutlierDetectionMethod.IQR:
            return self._detect_outliers_iqr(dataframe)
        elif method == OutlierDetectionMethod.MODIFIED_Z_SCORE:
            return self._detect_outliers_modified_zscore(dataframe)
        elif method == OutlierDetectionMethod.ISOLATION_FOREST:
            return self._detect_outliers_isolation_forest(dataframe)
        else:
            raise ValueError(f"不支援的檢測方法: {method}")

    def _detect_outliers_zscore(
        self, dataframe: pd.DataFrame
    ) -> OutlierDetectionResult:
        """使用 Z-score 方法檢測異常值。"""
        outlier_indices = set()
        column_outliers = {}

        # 檢查數值型欄位
        numeric_columns = dataframe.select_dtypes(include=[np.number]).columns

        for col in numeric_columns:
            if col in dataframe.columns:
                values = dataframe[col].dropna()
                if len(values) > 0:
                    mean = values.mean()
                    std = values.std()

                    if std > 0:  # 避免除以零
                        z_scores = np.abs((values - mean) / std)
                        col_outliers = values[
                            z_scores > self.config.z_score_threshold
                        ].index.tolist()
                        column_outliers[col] = col_outliers
                        outlier_indices.update(col_outliers)

        return OutlierDetectionResult(
            method="z_score",
            threshold=self.config.z_score_threshold,
            indices=list(outlier_indices),
            column_details=column_outliers,
        )

    def _detect_outliers_iqr(self, dataframe: pd.DataFrame) -> OutlierDetectionResult:
        """使用 IQR 方法檢測異常值。"""
        outlier_indices = set()
        column_outliers = {}

        # 檢查數值型欄位
        numeric_columns = dataframe.select_dtypes(include=[np.number]).columns

        for col in numeric_columns:
            if col in dataframe.columns:
                values = dataframe[col].dropna()
                if len(values) > 0:
                    q1 = values.quantile(0.25)
                    q3 = values.quantile(0.75)
                    iqr = q3 - q1

                    if iqr > 0:  # 避免除以零
                        lower_bound = q1 - self.config.iqr_threshold * iqr
                        upper_bound = q3 + self.config.iqr_threshold * iqr

                        col_outliers = values[
                            (values < lower_bound) | (values > upper_bound)
                        ].index.tolist()

                        column_outliers[col] = col_outliers
                        outlier_indices.update(col_outliers)

        return OutlierDetectionResult(
            method="iqr",
            threshold=self.config.iqr_threshold,
            indices=list(outlier_indices),
            column_details=column_outliers,
        )

    def _detect_outliers_modified_zscore(
        self, dataframe: pd.DataFrame
    ) -> OutlierDetectionResult:
        """使用修正 Z-score 方法檢測異常值。"""
        outlier_indices = set()
        column_outliers = {}

        # 檢查數值型欄位
        numeric_columns = dataframe.select_dtypes(include=[np.number]).columns

        for col in numeric_columns:
            if col in dataframe.columns:
                values = dataframe[col].dropna()
                if len(values) > 0:
                    median = values.median()
                    mad = np.median(np.abs(values - median))

                    if mad > 0:  # 避免除以零
                        modified_z_scores = 0.6745 * (values - median) / mad
                        col_outliers = values[
                            np.abs(modified_z_scores) > self.config.z_score_threshold
                        ].index.tolist()

                        column_outliers[col] = col_outliers
                        outlier_indices.update(col_outliers)

        return OutlierDetectionResult(
            method="modified_z_score",
            threshold=self.config.z_score_threshold,
            indices=list(outlier_indices),
            column_details=column_outliers,
        )

    def _detect_outliers_isolation_forest(
        self, dataframe: pd.DataFrame
    ) -> OutlierDetectionResult:
        """使用 Isolation Forest 方法檢測異常值。"""
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError:
            logger.warning("sklearn 未安裝，跳過 Isolation Forest 異常值檢測")
            return OutlierDetectionResult(
                method="isolation_forest",
                indices=[],
                column_details={},
                error="sklearn not available",
            )

        # 選擇數值型欄位
        numeric_columns = dataframe.select_dtypes(include=[np.number]).columns
        if len(numeric_columns) == 0:
            return OutlierDetectionResult(
                method="isolation_forest",
                indices=[],
                column_details={},
                error="no numeric columns",
            )

        # 準備數據
        data_for_detection = dataframe[numeric_columns].dropna()
        if len(data_for_detection) < 10:  # 需要足夠的數據點
            return OutlierDetectionResult(
                method="isolation_forest",
                indices=[],
                column_details={},
                error="insufficient data points",
            )

        # 執行 Isolation Forest
        iso_forest = IsolationForest(contamination=0.1, random_state=42)
        outlier_labels = iso_forest.fit_predict(data_for_detection)

        # 找出異常值索引
        outlier_mask = outlier_labels == -1
        outlier_indices = data_for_detection[outlier_mask].index.tolist()

        return OutlierDetectionResult(
            method="isolation_forest",
            indices=outlier_indices,
            column_details={"all_numeric": outlier_indices},
        )

    def _apply_outlier_treatment(
        self, dataframe: pd.DataFrame, outlier_indices: List[Any]
    ) -> None:
        """應用異常值處理策略。

        Args:
            dataframe: 股票數據
            outlier_indices: 異常值索引列表
        """
        if not outlier_indices:
            return

        if self.config.outlier_treatment == OutlierTreatmentStrategy.REMOVE:
            # 移除異常值
            dataframe.drop(outlier_indices, inplace=True)

        elif self.config.outlier_treatment == OutlierTreatmentStrategy.CLIP:
            # 截斷異常值
            self._clip_outliers(dataframe, outlier_indices)

        elif self.config.outlier_treatment == OutlierTreatmentStrategy.INTERPOLATE:
            # 插值替換
            self._interpolate_outliers(dataframe, outlier_indices)

    def _clip_outliers(
        self, dataframe: pd.DataFrame, outlier_indices: List[Any]
    ) -> None:
        """截斷異常值。"""
        numeric_columns = dataframe.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            q1 = dataframe[col].quantile(0.25)
            q3 = dataframe[col].quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            dataframe.loc[outlier_indices, col] = dataframe.loc[
                outlier_indices, col
            ].clip(lower=lower_bound, upper=upper_bound)

    def _interpolate_outliers(
        self, dataframe: pd.DataFrame, outlier_indices: List[Any]
    ) -> None:
        """插值替換異常值。"""
        numeric_columns = dataframe.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            dataframe.loc[outlier_indices, col] = np.nan
            dataframe[col] = dataframe[col].interpolate(method="linear")
