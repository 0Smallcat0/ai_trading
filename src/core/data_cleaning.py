"""資料清理與處理模組

此模組提供全面的資料清理和處理功能，包括：
- 缺失值處理（插補、刪除等）
- 異常值處理（Z-score、IQR、截斷等）
- 價格標準化（調整收盤價邏輯）
- 資料清理工作流

主要功能：
- 提供多種缺失值填補方法
- 提供多種異常值檢測和處理方法
- 標準化不同來源的價格資料
- 設計模組化的資料清理流程
"""

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.impute import KNNImputer

# 導入現有的資料清理功能

# 設定日誌
logger = logging.getLogger(__name__)


class MissingValueHandler:
    """缺失值處理器

    提供多種缺失值填補方法，包括統計方法、插值方法和機器學習方法。
    """

    def __init__(self, method="interpolate", **kwargs):
        """初始化缺失值處理器

        Args:
            method (str): 填補方法，可選 'interpolate', 'mean', 'median',
                'mode', 'knn', 'ffill', 'bfill'
            **kwargs: 填補方法的其他參數
        """
        self.method = method
        self.params = kwargs
        self.imputer = None

        # 如果使用 KNN 填補，初始化 KNNImputer
        if method == "knn":
            n_neighbors = kwargs.get("n_neighbors", 5)
            self.imputer = KNNImputer(n_neighbors=n_neighbors)

    def fit(self, df: pd.DataFrame, columns: Optional[List[str]] = None):
        """擬合填補器（僅適用於需要擬合的方法，如 KNN）

        Args:
            df (pd.DataFrame): 輸入資料
            columns (List[str], optional): 要處理的列，如果為 None 則處理所有數值列
        """
        if df.empty:
            return

        # 如果未指定列，則使用所有數值列
        if columns is None:
            columns = df.select_dtypes(include=np.number).columns.tolist()

        # 僅對需要擬合的方法進行擬合
        if self.method == "knn" and self.imputer is not None:
            self.imputer.fit(df[columns])

    def transform(
        self, df: pd.DataFrame, columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """填補缺失值

        Args:
            df (pd.DataFrame): 輸入資料
            columns (List[str], optional): 要處理的列，如果為 None 則處理所有數值列

        Returns:
            pd.DataFrame: 填補後的資料
        """
        if df.empty:
            return df

        # 複製資料以避免修改原始資料
        result = df.copy()

        # 如果未指定列，則使用所有數值列
        if columns is None:
            columns = result.select_dtypes(include=np.number).columns.tolist()

        # 根據方法填補缺失值
        if self.method == "interpolate":
            method = self.params.get("method", "linear")
            for col in columns:
                if result[col].isna().any():
                    result[col] = result[col].interpolate(method=method)
        elif self.method == "mean":
            for col in columns:
                if result[col].isna().any():
                    result[col] = result[col].fillna(result[col].mean())
        elif self.method == "median":
            for col in columns:
                if result[col].isna().any():
                    result[col] = result[col].fillna(result[col].median())
        elif self.method == "mode":
            for col in columns:
                if result[col].isna().any():
                    result[col] = result[col].fillna(result[col].mode()[0])
        elif self.method == "ffill":
            result[columns] = result[columns].fillna(method="ffill")
        elif self.method == "bfill":
            result[columns] = result[columns].fillna(method="bfill")
        elif self.method == "knn" and self.imputer is not None:
            # 保存原始索引
            original_index = result.index
            # 填補缺失值
            imputed_values = self.imputer.transform(result[columns])
            # 將填補後的值放回原始資料框
            result[columns] = pd.DataFrame(
                imputed_values, index=original_index, columns=columns
            )

        return result

    def fit_transform(
        self, df: pd.DataFrame, columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """擬合並填補缺失值

        Args:
            df (pd.DataFrame): 輸入資料
            columns (List[str], optional): 要處理的列，如果為 None 則處理所有數值列

        Returns:
            pd.DataFrame: 填補後的資料
        """
        self.fit(df, columns)
        return self.transform(df, columns)


class OutlierHandler:
    """異常值處理器

    提供多種異常值檢測和處理方法，包括統計方法和機器學習方法。
    """

    def __init__(self, detection_method="z-score", treatment_method="clip", **kwargs):
        """初始化異常值處理器

        Args:
            detection_method (str): 檢測方法，可選 'z-score', 'iqr', 'isolation-forest'
            treatment_method (str): 處理方法，可選 'clip', 'remove', 'mean',
                'median', 'winsorize'
            **kwargs: 其他參數，如 z_threshold, iqr_multiplier 等
        """
        self.detection_method = detection_method
        self.treatment_method = treatment_method
        self.params = kwargs

        # 設定閾值
        self.z_threshold = kwargs.get("z_threshold", 3.0)
        self.iqr_multiplier = kwargs.get("iqr_multiplier", 1.5)
        self.winsorize_limits = kwargs.get("winsorize_limits", (0.05, 0.05))

    def detect_outliers(
        self, df: pd.DataFrame, columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """檢測異常值

        Args:
            df (pd.DataFrame): 輸入資料
            columns (List[str], optional): 要處理的列，如果為 None 則處理所有數值列

        Returns:
            pd.DataFrame: 異常值標記，布林值資料框，True 表示異常值
        """
        if df.empty:
            return pd.DataFrame()

        # 如果未指定列，則使用所有數值列
        if columns is None:
            columns = df.select_dtypes(include=np.number).columns.tolist()

        # 初始化結果
        outliers = pd.DataFrame(False, index=df.index, columns=columns)

        # 檢測異常值
        for col in columns:
            if self.detection_method == "z-score":
                # Z-score 方法
                z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                outliers[col] = z_scores > self.z_threshold
            elif self.detection_method == "iqr":
                # IQR 方法
                q1 = df[col].quantile(0.25)
                q3 = df[col].quantile(0.75)
                iqr = q3 - q1
                lower_bound = q1 - self.iqr_multiplier * iqr
                upper_bound = q3 + self.iqr_multiplier * iqr
                outliers[col] = (df[col] < lower_bound) | (df[col] > upper_bound)
            elif self.detection_method == "isolation-forest":
                # 如果需要使用 Isolation Forest，需要額外安裝 scikit-learn
                try:
                    from sklearn.ensemble import IsolationForest

                    model = IsolationForest(
                        contamination=self.params.get("contamination", 0.05)
                    )
                    outliers[col] = model.fit_predict(df[[col]]) == -1
                except ImportError:
                    logger.warning("無法使用 Isolation Forest，請安裝 scikit-learn")
                    # 回退到 Z-score 方法
                    z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                    outliers[col] = z_scores > self.z_threshold

        return outliers

    def treat_outliers(
        self,
        df: pd.DataFrame,
        outliers: Optional[pd.DataFrame] = None,
        columns: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """處理異常值

        Args:
            df (pd.DataFrame): 輸入資料
            outliers (pd.DataFrame, optional): 異常值標記，如果為 None 則自動檢測
            columns (List[str], optional): 要處理的列，如果為 None 則處理所有數值列

        Returns:
            pd.DataFrame: 處理後的資料
        """
        if df.empty:
            return df

        # 複製資料以避免修改原始資料
        result = df.copy()

        # 如果未指定列，則使用所有數值列
        if columns is None:
            columns = result.select_dtypes(include=np.number).columns.tolist()

        # 如果未提供異常值標記，則自動檢測
        if outliers is None:
            outliers = self.detect_outliers(result, columns)

        # 處理異常值
        for col in columns:
            if self.treatment_method == "clip":
                # 截斷法
                if self.detection_method == "z-score":
                    mean = result[col].mean()
                    std = result[col].std()
                    lower_bound = mean - self.z_threshold * std
                    upper_bound = mean + self.z_threshold * std
                elif self.detection_method == "iqr":
                    q1 = result[col].quantile(0.25)
                    q3 = result[col].quantile(0.75)
                    iqr = q3 - q1
                    lower_bound = q1 - self.iqr_multiplier * iqr
                    upper_bound = q3 + self.iqr_multiplier * iqr
                else:
                    # 預設使用 Z-score
                    mean = result[col].mean()
                    std = result[col].std()
                    lower_bound = mean - self.z_threshold * std
                    upper_bound = mean + self.z_threshold * std

                result.loc[outliers[col], col] = result.loc[outliers[col], col].clip(
                    lower_bound, upper_bound
                )
            elif self.treatment_method == "remove":
                # 移除法（設為 NaN）
                result.loc[outliers[col], col] = np.nan
            elif self.treatment_method == "mean":
                # 均值替換
                result.loc[outliers[col], col] = result[col].mean()
            elif self.treatment_method == "median":
                # 中位數替換
                result.loc[outliers[col], col] = result[col].median()
            elif self.treatment_method == "winsorize":
                # Winsorize 法
                try:
                    from scipy.stats import mstats

                    result[col] = mstats.winsorize(
                        result[col], limits=self.winsorize_limits
                    )
                except ImportError:
                    logger.warning("無法使用 winsorize，請安裝 scipy")
                    # 回退到截斷法
                    mean = result[col].mean()
                    std = result[col].std()
                    lower_bound = mean - self.z_threshold * std
                    upper_bound = mean + self.z_threshold * std
                    result.loc[outliers[col], col] = result.loc[
                        outliers[col], col
                    ].clip(lower_bound, upper_bound)

        return result


class PriceStandardizer:
    """價格標準化器

    提供價格標準化功能，包括調整收盤價邏輯、處理股票分割和股息等。
    """

    def __init__(self, adjust_method="adj_close"):
        """初始化價格標準化器

        Args:
            adjust_method (str): 調整方法，可選 'adj_close', 'adj_factor'
        """
        self.adjust_method = adjust_method

    def standardize_prices(
        self, df: pd.DataFrame, symbol: Optional[str] = None
    ) -> pd.DataFrame:
        """標準化價格

        Args:
            df (pd.DataFrame): 輸入資料，必須包含 OHLCV 欄位
            symbol (str, optional): 股票代碼，用於日誌記錄

        Returns:
            pd.DataFrame: 標準化後的資料
        """
        if df.empty:
            return df

        # 複製資料以避免修改原始資料
        result = df.copy()

        # 檢查必要的欄位
        required_cols = ["open", "high", "low", "close", "volume"]
        missing_cols = [col for col in required_cols if col not in result.columns]
        if missing_cols:
            logger.warning("缺少必要的欄位: {missing_cols}, 無法進行價格標準化")
            return result

        # 根據調整方法標準化價格
        if self.adjust_method == "adj_close":
            # 使用調整後收盤價邏輯
            if "adj_close" in result.columns:
                # 計算調整因子
                adj_factor = result["adj_close"] / result["close"]

                # 調整 OHLC
                result["open"] = result["open"] * adj_factor
                result["high"] = result["high"] * adj_factor
                result["low"] = result["low"] * adj_factor
                result["close"] = result["adj_close"]

                # 移除 adj_close 欄位，因為現在 close 已經是調整後的價格
                result = result.drop(columns=["adj_close"])

                logger.info(
                    f"使用調整後收盤價邏輯標準化價格 {symbol if symbol else ''}"
                )
            else:
                logger.warning(
                    f"缺少 adj_close 欄位，無法使用調整後收盤價邏輯 {symbol if symbol else ''}"
                )

        elif self.adjust_method == "adj_factor":
            # 使用調整因子邏輯
            if "adj_factor" in result.columns:
                # 調整 OHLC
                result["open"] = result["open"] * result["adj_factor"]
                result["high"] = result["high"] * result["adj_factor"]
                result["low"] = result["low"] * result["adj_factor"]
                result["close"] = result["close"] * result["adj_factor"]

                logger.info("使用調整因子邏輯標準化價格 {symbol if symbol else ''}")
            else:
                logger.warning(
                    f"缺少 adj_factor 欄位，無法使用調整因子邏輯 {symbol if symbol else ''}"
                )

        return result

    def handle_stock_splits(
        self, df: pd.DataFrame, split_events: Dict[date, float]
    ) -> pd.DataFrame:
        """處理股票分割

        Args:
            df (pd.DataFrame): 輸入資料，必須包含 OHLCV 欄位和日期索引
            split_events (Dict[date, float]): 分割事件，鍵為日期，值為分割比例

        Returns:
            pd.DataFrame: 處理後的資料
        """
        if df.empty or not split_events:
            return df

        # 複製資料以避免修改原始資料
        result = df.copy()

        # 確保索引是日期類型
        if not isinstance(result.index, pd.DatetimeIndex):
            logger.warning("索引不是日期類型，無法處理股票分割")
            return result

        # 處理每個分割事件
        for split_date, split_ratio in split_events.items():
            # 找出分割日期之前的所有資料
            mask = result.index < pd.Timestamp(split_date)

            # 調整分割日期之前的價格和成交量
            result.loc[mask, "open"] = result.loc[mask, "open"] / split_ratio
            result.loc[mask, "high"] = result.loc[mask, "high"] / split_ratio
            result.loc[mask, "low"] = result.loc[mask, "low"] / split_ratio
            result.loc[mask, "close"] = result.loc[mask, "close"] / split_ratio
            result.loc[mask, "volume"] = result.loc[mask, "volume"] * split_ratio

            logger.info("處理股票分割: {split_date}, 比例: {split_ratio}")

        return result


class DataCleaningPipeline:
    """資料清理管道

    提供完整的資料清理流程，包括缺失值處理、異常值處理和價格標準化。
    """

    def __init__(
        self,
        missing_value_handler: Optional[MissingValueHandler] = None,
        outlier_handler: Optional[OutlierHandler] = None,
        price_standardizer: Optional[PriceStandardizer] = None,
        **kwargs,
    ):
        """初始化資料清理管道

        Args:
            missing_value_handler (MissingValueHandler, optional): 缺失值處理器
            outlier_handler (OutlierHandler, optional): 異常值處理器
            price_standardizer (PriceStandardizer, optional): 價格標準化器
            **kwargs: 其他參數
        """
        # 如果未提供處理器，則使用預設設定
        self.missing_value_handler = missing_value_handler or MissingValueHandler()
        self.outlier_handler = outlier_handler or OutlierHandler()
        self.price_standardizer = price_standardizer or PriceStandardizer()

        # 設定處理順序和其他參數
        self.process_order = kwargs.get(
            "process_order", ["missing", "outlier", "price"]
        )
        self.report = kwargs.get("report", True)
        self.visualize = kwargs.get("visualize", False)

    def clean(
        self, df: pd.DataFrame, symbol: Optional[str] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """清理資料

        Args:
            df (pd.DataFrame): 輸入資料
            symbol (str, optional): 股票代碼，用於日誌記錄

        Returns:
            Tuple[pd.DataFrame, Dict[str, Any]]: 清理後的資料和清理報告
        """
        if df.empty:
            return df, {"status": "empty", "message": "輸入資料為空"}

        # 複製資料以避免修改原始資料
        result = df.copy()

        # 初始化報告
        report = {
            "original_shape": result.shape,
            "missing_values_before": result.isna().sum().to_dict(),
            "outliers_detected": {},
            "processing_steps": [],
        }

        # 根據處理順序執行清理步驟
        for step in self.process_order:
            if step == "missing":
                # 處理缺失值
                result = self.missing_value_handler.transform(result)
                report["processing_steps"].append("missing_value_handling")
                report["missing_values_after"] = result.isna().sum().to_dict()

            elif step == "outlier":
                # 檢測異常值
                outliers = self.outlier_handler.detect_outliers(result)
                # 計算每列的異常值數量
                for col in outliers.columns:
                    report["outliers_detected"][col] = outliers[col].sum()

                # 處理異常值
                result = self.outlier_handler.treat_outliers(result, outliers)
                report["processing_steps"].append("outlier_handling")

            elif step == "price":
                # 標準化價格
                if any(
                    col in result.columns for col in ["open", "high", "low", "close"]
                ):
                    result = self.price_standardizer.standardize_prices(result, symbol)
                    report["processing_steps"].append("price_standardization")

        # 完成報告
        report["final_shape"] = result.shape
        report["status"] = "success"

        # 如果啟用視覺化，則生成視覺化報告
        if self.visualize:
            self._generate_visualization(df, result, report)

        return result, report

    def _generate_visualization(
        self,
        original_df: pd.DataFrame,
        cleaned_df: pd.DataFrame,
        report: Dict[str, Any],
    ):
        """生成視覺化報告

        Args:
            original_df (pd.DataFrame): 原始資料
            cleaned_df (pd.DataFrame): 清理後的資料
            report (Dict[str, Any]): 清理報告
        """
        # 這裡可以實現視覺化報告的生成邏輯
        # 例如，繪製清理前後的分佈圖、箱線圖等


# 實用函數


def clean_stock_data(
    df: pd.DataFrame,
    handle_missing: bool = True,
    handle_outliers: bool = True,
    standardize_prices: bool = True,
    symbol: Optional[str] = None,
) -> pd.DataFrame:
    """清理股票資料的便捷函數

    Args:
        df (pd.DataFrame): 輸入資料
        handle_missing (bool): 是否處理缺失值
        handle_outliers (bool): 是否處理異常值
        standardize_prices (bool): 是否標準化價格
        symbol (str, optional): 股票代碼，用於日誌記錄

    Returns:
        pd.DataFrame: 清理後的資料
    """
    # 設定處理順序
    process_order = []
    if handle_missing:
        process_order.append("missing")
    if handle_outliers:
        process_order.append("outlier")
    if standardize_prices:
        process_order.append("price")

    # 創建清理管道
    pipeline = DataCleaningPipeline(
        missing_value_handler=MissingValueHandler(method="interpolate"),
        outlier_handler=OutlierHandler(
            detection_method="z-score", treatment_method="clip"
        ),
        price_standardizer=PriceStandardizer(),
        process_order=process_order,
    )

    # 執行清理
    cleaned_df, _ = pipeline.clean(df, symbol)

    return cleaned_df
