"""
技術與基本面指標計算模組

此模組負責計算各種技術指標和基本面指標，為策略研究提供必要的特徵。

主要功能：
- 計算技術指標（如 RSI、MACD、KD 等）
- 計算基本面指標（如 ROE、ROA、EPS 等）
- 特徵工程和資料轉換
- 資料清理與預處理
- 分散式處理支援
"""

import pandas as pd
import numpy as np
import copy
import logging
import warnings
from typing import Dict, List, Union, Optional, Callable, Tuple
from functools import partial
import datetime
from scipy import stats
from sklearn.impute import KNNImputer, SimpleImputer
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest, f_regression, RFE
from sklearn.linear_model import LinearRegression, Lasso
from sklearn.ensemble import RandomForestRegressor
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import os
import json
from datetime import datetime

# 導入相關模組
try:
    from src.core.data_ingest import load_data
    import talib
    from talib import abstract
except ImportError as e:
    # 只在非測試環境中顯示警告
    import sys

    if not any("pytest" in arg for arg in sys.argv):
        warnings.warn(f"無法匯入 TA-Lib，部分技術指標功能將無法使用: {e}")

    # 創建空的 abstract 模組以避免錯誤
    class DummyAbstract:
        def __getattr__(self, name):
            return None

    abstract = DummyAbstract()

# 嘗試導入分散式處理庫
try:
    import dask
    import dask.dataframe as dd
    import dask.array as da

    DASK_AVAILABLE = True
except ImportError:
    DASK_AVAILABLE = False
    # 只在非測試環境中顯示警告
    import sys

    if not any("pytest" in arg for arg in sys.argv):
        warnings.warn("無法匯入 Dask，分散式處理功能將無法使用")

try:
    import ray

    RAY_AVAILABLE = True
except ImportError:
    RAY_AVAILABLE = False
    # 只在非測試環境中顯示警告
    import sys

    if not any("pytest" in arg for arg in sys.argv):
        warnings.warn("無法匯入 Ray，分散式處理功能將無法使用")


class RollingWindowFeatureGenerator:
    """
    滾動視窗特徵生成器

    用於生成基於滾動視窗的特徵，如移動平均、標準差等。
    支援自定義視窗大小和函數。
    """

    def __init__(self, window_sizes=None, functions=None):
        """
        初始化滾動視窗特徵生成器

        Args:
            window_sizes (list, optional): 視窗大小列表，如果為 None 則使用預設值 [5, 10, 20, 60]
            functions (dict, optional): 函數字典，鍵為函數名稱，值為函數，如果為 None 則使用預設函數
        """
        self.window_sizes = window_sizes or [5, 10, 20, 60]

        # 預設函數
        default_functions = {
            "mean": lambda x: x.mean(),
            "std": lambda x: x.std(),
            "min": lambda x: x.min(),
            "max": lambda x: x.max(),
            "median": lambda x: x.median(),
            "sum": lambda x: x.sum(),
            "skew": lambda x: x.skew(),
            "kurt": lambda x: x.kurt(),
            "q25": lambda x: x.quantile(0.25),
            "q75": lambda x: x.quantile(0.75),
        }

        self.functions = functions or default_functions

    def generate(self, df, columns=None):
        """
        生成滾動視窗特徵

        Args:
            df (pandas.DataFrame): 輸入資料
            columns (list, optional): 要處理的列名列表，如果為 None 則處理所有數值列

        Returns:
            pandas.DataFrame: 生成的特徵
        """
        if df.empty:
            return pd.DataFrame()

        # 如果未指定列名，則使用所有數值列
        if columns is None:
            columns = df.select_dtypes(include=["number"]).columns.tolist()

        # 生成特徵
        features = {}
        for col in columns:
            for window in self.window_sizes:
                rolling = df[col].rolling(window=window)
                for func_name, func in self.functions.items():
                    try:
                        feature_name = f"{col}_{func_name}_{window}"
                        features[feature_name] = func(rolling)
                    except Exception as e:
                        logging.warning(f"計算特徵 {feature_name} 時發生錯誤: {e}")

        return pd.DataFrame(features, index=df.index)


class DataCleaner:
    """
    資料清理器

    用於清理和預處理資料，包括異常值處理和缺失值填補。
    """

    def __init__(
        self,
        outlier_method="z-score",
        outlier_threshold=3.0,
        imputation_method="interpolate",
        imputation_params=None,
    ):
        """
        初始化資料清理器

        Args:
            outlier_method (str): 異常值檢測方法，可選 'z-score', 'iqr'
            outlier_threshold (float): 異常值閾值，z-score 方法使用標準差倍數，iqr 方法使用四分位距倍數
            imputation_method (str): 缺失值填補方法，可選 'interpolate', 'mean', 'median', 'knn', 'forward', 'backward'
            imputation_params (dict, optional): 填補方法的參數
        """
        self.outlier_method = outlier_method
        self.outlier_threshold = outlier_threshold
        self.imputation_method = imputation_method
        self.imputation_params = imputation_params or {}

    def detect_outliers(self, df, columns=None):
        """
        檢測異常值

        Args:
            df (pandas.DataFrame): 輸入資料
            columns (list, optional): 要處理的列名列表，如果為 None 則處理所有數值列

        Returns:
            pandas.DataFrame: 異常值標記，True 表示異常值
        """
        if df.empty:
            return pd.DataFrame()

        # 如果未指定列名，則使用所有數值列
        if columns is None:
            columns = df.select_dtypes(include=["number"]).columns.tolist()

        # 初始化結果
        outliers = pd.DataFrame(False, index=df.index, columns=columns)

        # 檢測異常值
        for col in columns:
            if self.outlier_method == "z-score":
                # Z-score 方法
                z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                outliers[col] = z_scores > self.outlier_threshold
            elif self.outlier_method == "iqr":
                # IQR 方法
                q1 = df[col].quantile(0.25)
                q3 = df[col].quantile(0.75)
                iqr = q3 - q1
                lower_bound = q1 - self.outlier_threshold * iqr
                upper_bound = q3 + self.outlier_threshold * iqr
                outliers[col] = (df[col] < lower_bound) | (df[col] > upper_bound)
            else:
                raise ValueError(f"不支援的異常值檢測方法: {self.outlier_method}")

        return outliers

    def treat_outliers(self, df, outliers=None, method="clip", columns=None):
        """
        處理異常值

        Args:
            df (pandas.DataFrame): 輸入資料
            outliers (pandas.DataFrame, optional): 異常值標記，如果為 None 則自動檢測
            method (str): 處理方法，可選 'clip', 'remove', 'mean', 'median', 'interpolate'
            columns (list, optional): 要處理的列名列表，如果為 None 則處理所有數值列

        Returns:
            pandas.DataFrame: 處理後的資料
        """
        if df.empty:
            return df

        # 如果未指定列名，則使用所有數值列
        if columns is None:
            columns = df.select_dtypes(include=["number"]).columns.tolist()

        # 如果未提供異常值標記，則自動檢測
        if outliers is None:
            outliers = self.detect_outliers(df, columns)

        # 複製資料以避免修改原始資料
        result = df.copy()

        # 處理異常值
        for col in columns:
            if method == "clip":
                # 截斷法
                if self.outlier_method == "z-score":
                    mean = df[col].mean()
                    std = df[col].std()
                    lower_bound = mean - self.outlier_threshold * std
                    upper_bound = mean + self.outlier_threshold * std
                elif self.outlier_method == "iqr":
                    q1 = df[col].quantile(0.25)
                    q3 = df[col].quantile(0.75)
                    iqr = q3 - q1
                    lower_bound = q1 - self.outlier_threshold * iqr
                    upper_bound = q3 + self.outlier_threshold * iqr
                else:
                    continue

                result[col] = result[col].clip(lower=lower_bound, upper=upper_bound)
            elif method == "remove":
                # 移除法
                result.loc[outliers[col], col] = np.nan
            elif method == "mean":
                # 均值替換法
                result.loc[outliers[col], col] = df[col].mean()
            elif method == "median":
                # 中位數替換法
                result.loc[outliers[col], col] = df[col].median()
            elif method == "interpolate":
                # 插值法
                result.loc[outliers[col], col] = np.nan
                result[col] = result[col].interpolate(method="linear")
            else:
                raise ValueError(f"不支援的異常值處理方法: {method}")

        return result

    def impute_missing_values(self, df, columns=None):
        """
        填補缺失值

        Args:
            df (pandas.DataFrame): 輸入資料
            columns (list, optional): 要處理的列名列表，如果為 None 則處理所有數值列

        Returns:
            pandas.DataFrame: 填補後的資料
        """
        if df.empty:
            return df

        # 如果未指定列名，則使用所有數值列
        if columns is None:
            columns = df.select_dtypes(include=["number"]).columns.tolist()

        # 複製資料以避免修改原始資料
        result = df.copy()

        # 填補缺失值
        if self.imputation_method == "interpolate":
            # 插值法
            method = self.imputation_params.get("method", "linear")
            result[columns] = result[columns].interpolate(method=method)
        elif self.imputation_method == "mean":
            # 均值填補
            for col in columns:
                result[col] = result[col].fillna(result[col].mean())
        elif self.imputation_method == "median":
            # 中位數填補
            for col in columns:
                result[col] = result[col].fillna(result[col].median())
        elif self.imputation_method == "knn":
            # KNN 填補
            n_neighbors = self.imputation_params.get("n_neighbors", 5)
            imputer = KNNImputer(n_neighbors=n_neighbors)
            result[columns] = imputer.fit_transform(result[columns])
        elif self.imputation_method == "forward":
            # 前向填補
            result[columns] = result[columns].fillna(method="ffill")
        elif self.imputation_method == "backward":
            # 後向填補
            result[columns] = result[columns].fillna(method="bfill")
        else:
            raise ValueError(f"不支援的缺失值填補方法: {self.imputation_method}")

        return result

    def clean_data(
        self,
        df,
        detect_outliers=True,
        treat_outliers=True,
        impute_missing=True,
        columns=None,
    ):
        """
        清理資料

        Args:
            df (pandas.DataFrame): 輸入資料
            detect_outliers (bool): 是否檢測異常值
            treat_outliers (bool): 是否處理異常值
            impute_missing (bool): 是否填補缺失值
            columns (list, optional): 要處理的列名列表，如果為 None 則處理所有數值列

        Returns:
            tuple: (pandas.DataFrame, pandas.DataFrame) 清理後的資料和異常值標記
        """
        if df.empty:
            return df, pd.DataFrame()

        # 如果未指定列名，則使用所有數值列
        if columns is None:
            columns = df.select_dtypes(include=["number"]).columns.tolist()

        # 複製資料以避免修改原始資料
        result = df.copy()
        outliers = None

        # 檢測異常值
        if detect_outliers:
            outliers = self.detect_outliers(result, columns)

        # 處理異常值
        if treat_outliers and outliers is not None:
            result = self.treat_outliers(
                result, outliers, method="clip", columns=columns
            )

        # 填補缺失值
        if impute_missing:
            result = self.impute_missing_values(result, columns)

        return result, outliers


class FeatureCalculator:
    """特徵計算器類別，用於計算各種技術和基本面指標"""

    def __init__(self, data_dict=None, use_distributed=False, chunk_size=10000):
        """
        初始化特徵計算器

        Args:
            data_dict (dict, optional): 包含各種資料的字典，如果為 None 則自動載入
            use_distributed (bool): 是否使用分散式處理
            chunk_size (int): 記憶體分塊大小
        """
        if data_dict is None:
            self.data_dict = load_data()
        else:
            self.data_dict = data_dict

        # 確保必要的資料存在
        if "price" not in self.data_dict:
            raise ValueError("必須提供價格資料")

        # 分散式處理設定
        self.use_distributed = use_distributed
        self.chunk_size = chunk_size

        # 初始化滾動視窗特徵生成器
        self.rolling_generator = RollingWindowFeatureGenerator()

        # 初始化資料清理器
        self.data_cleaner = DataCleaner()

    def calculate_technical_indicators(
        self, stock_id=None, indicators=None, multipliers=None, custom_params=None
    ):
        """
        計算技術指標

        Args:
            stock_id (str, optional): 股票代號，如果為 None 則計算所有股票
            indicators (list, optional): 指標列表，如果為 None 則計算所有支援的指標
            multipliers (list, optional): 參數倍數列表，用於調整指標參數
            custom_params (dict, optional): 自定義參數，鍵為指標名稱，值為參數字典

        Returns:
            pandas.DataFrame: 包含技術指標的資料框架
        """
        # 預設指標列表
        if indicators is None:
            indicators = [
                "RSI",  # 相對強弱指標
                "MACD",  # 移動平均收斂散度
                "SMA",  # 簡單移動平均
                "EMA",  # 指數移動平均
                "WMA",  # 加權移動平均
                "BBANDS",  # 布林帶
                "STOCH",  # 隨機指標
                "CCI",  # 商品通道指數
                "MOM",  # 動量指標
                "ROC",  # 變動率
                "ATR",  # 平均真實範圍
                "OBV",  # 能量潮
                "ADX",  # 平均趨向指數
                "WILLR",  # 威廉指標
                "AROON",  # 阿隆指標
                "MFI",  # 資金流量指標
                "TRIX",  # 三重指數平滑移動平均
                "ULTOSC",  # 終極震盪指標
            ]

        # 預設參數倍數
        if multipliers is None:
            multipliers = [0.5, 1, 2]

        # 預設自定義參數
        if custom_params is None:
            custom_params = {}

        # 獲取價格資料
        price_df = self.data_dict["price"]

        # 加強 index 結構檢查
        if (
            not isinstance(price_df.index, pd.MultiIndex)
            or "stock_id" not in price_df.index.names
        ):
            raise ValueError(
                "價格資料必須為 MultiIndex 且包含 'stock_id' 層級，請確認資料格式。"
            )

        # 如果指定了股票代號，則只計算該股票的指標
        if stock_id is not None:
            price_df = price_df.xs(stock_id, level="stock_id")

        # 準備 OHLCV 資料
        ohlcv_dict = self._prepare_ohlcv_data(price_df)

        # 如果缺少必要的欄位，則返回空的資料框架
        if len(ohlcv_dict) < 4 or "close" not in ohlcv_dict:
            logging.warning("缺少必要的 OHLCV 欄位，無法計算技術指標")
            return pd.DataFrame()

        # 計算技術指標
        features = {}

        # 使用分散式處理
        if self.use_distributed and DASK_AVAILABLE:
            try:
                return self._calculate_indicators_with_dask(
                    ohlcv_dict, indicators, multipliers, custom_params
                )
            except Exception as e:
                logging.error(f"使用 Dask 計算技術指標時發生錯誤: {e}")
                logging.info("回退到標準處理方式")

        # 標準處理方式
        for name in indicators:
            indicator_features = self._calculate_single_indicator(
                name, ohlcv_dict, multipliers, custom_params.get(name, {})
            )
            features.update(indicator_features)

        return pd.DataFrame(features)

    def _prepare_ohlcv_data(self, price_df):
        """
        準備 OHLCV 資料

        Args:
            price_df (pandas.DataFrame): 價格資料

        Returns:
            dict: OHLCV 資料字典
        """
        # 準備 OHLCV 資料
        ohlcv_dict = {}

        # 處理中文欄位名稱
        for col in ["開盤價", "最高價", "最低價", "收盤價", "成交股數"]:
            if col in price_df.columns:
                ohlcv_dict[col.replace("價", "")] = pd.to_numeric(
                    price_df[col], errors="coerce"
                )

        # 處理英文欄位名稱
        for col, key in [
            ("open", "開盤"),
            ("high", "最高"),
            ("low", "最低"),
            ("close", "收盤"),
            ("volume", "成交股數"),
        ]:
            if col in price_df.columns:
                ohlcv_dict[key] = pd.to_numeric(price_df[col], errors="coerce")

        # 關鍵：為 talib 指標補上 'close', 'high', 'low', 'open' 鍵
        if "收盤" in ohlcv_dict:
            ohlcv_dict["close"] = ohlcv_dict["收盤"]
        elif "收盤價" in price_df.columns:
            ohlcv_dict["close"] = pd.to_numeric(price_df["收盤價"], errors="coerce")

        if "最高" in ohlcv_dict:
            ohlcv_dict["high"] = ohlcv_dict["最高"]
        elif "最高價" in price_df.columns:
            ohlcv_dict["high"] = pd.to_numeric(price_df["最高價"], errors="coerce")

        if "最低" in ohlcv_dict:
            ohlcv_dict["low"] = ohlcv_dict["最低"]
        elif "最低價" in price_df.columns:
            ohlcv_dict["low"] = pd.to_numeric(price_df["最低價"], errors="coerce")

        if "開盤" in ohlcv_dict:
            ohlcv_dict["open"] = ohlcv_dict["開盤"]
        elif "開盤價" in price_df.columns:
            ohlcv_dict["open"] = pd.to_numeric(price_df["開盤價"], errors="coerce")

        if "成交股數" in ohlcv_dict:
            ohlcv_dict["volume"] = ohlcv_dict["成交股數"]
        elif "volume" in price_df.columns:
            ohlcv_dict["volume"] = pd.to_numeric(price_df["volume"], errors="coerce")

        return ohlcv_dict

    def _calculate_single_indicator(
        self, name, ohlcv_dict, multipliers, custom_params=None
    ):
        """
        計算單一技術指標

        Args:
            name (str): 指標名稱
            ohlcv_dict (dict): OHLCV 資料字典
            multipliers (list): 參數倍數列表
            custom_params (dict, optional): 自定義參數

        Returns:
            dict: 指標特徵字典
        """
        features = {}

        # 檢查是否需要 high/low 欄位
        need_high_low = name.upper() in [
            "STOCH",
            "CCI",
            "STOCHF",
            "WILLR",
            "AROON",
            "AROONOSC",
            "ULTOSC",
            "DX",
            "MINUS_DI",
            "PLUS_DI",
            "MINUS_DM",
            "PLUS_DM",
            "TRIX",
            "AD",
            "ADOSC",
            "MFI",
            "ATR",
            "NATR",
            "BBANDS",
        ]

        if need_high_low and (("high" not in ohlcv_dict) or ("low" not in ohlcv_dict)):
            logging.warning(f"跳過 {name} 指標，因為缺少 high/low 欄位")
            return features

        # 檢查是否需要 volume 欄位
        need_volume = name.upper() in ["OBV", "AD", "ADOSC", "MFI"]

        if need_volume and "volume" not in ohlcv_dict:
            logging.warning(f"跳過 {name} 指標，因為缺少 volume 欄位")
            return features

        # 檢查 TA-Lib 是否支援該指標
        if not hasattr(abstract, name):
            logging.warning(f"TA-Lib 不支援 {name} 指標")
            return features

        # 獲取指標函數
        f = getattr(abstract, name)

        # 獲取原始參數
        org_params = dict(f.parameters)

        # 如果有自定義參數，則使用自定義參數
        if custom_params:
            try:
                values = f(ohlcv_dict, **custom_params)
                if isinstance(values, pd.Series):
                    features[f"{name}_custom"] = values
                elif isinstance(values, pd.DataFrame):
                    for output_name, series in values.items():
                        features[f"{name}_{output_name}_custom"] = series
            except Exception as e:
                logging.warning(f"使用自定義參數計算 {name} 指標時發生錯誤: {e}")

        # 使用參數倍數計算
        for m in multipliers:
            params = copy.copy(org_params)
            # 只對 int/float 參數做倍數運算
            for k, v in params.items():
                if isinstance(v, (int, float)):
                    params[k] = int(v * m) if isinstance(v, int) else v * m
            try:
                values = f(ohlcv_dict, **params)
                if isinstance(values, pd.Series):
                    features[f"{name}_{m}x"] = values
                elif isinstance(values, pd.DataFrame):
                    for output_name, series in values.items():
                        features[f"{name}_{output_name}_{m}x"] = series
            except Exception as e:
                logging.warning(f"計算 {name} 指標時發生錯誤: {e}")
                continue
            # 重置參數
            f.parameters = org_params

        return features

    def _calculate_indicators_with_dask(
        self, ohlcv_dict, indicators, multipliers, custom_params
    ):
        """
        使用 Dask 計算技術指標

        Args:
            ohlcv_dict (dict): OHLCV 資料字典
            indicators (list): 指標列表
            multipliers (list): 參數倍數列表
            custom_params (dict): 自定義參數

        Returns:
            pandas.DataFrame: 技術指標資料框架
        """
        # 將 OHLCV 資料轉換為 Dask DataFrame
        dask_dict = {}
        for k, v in ohlcv_dict.items():
            dask_dict[k] = dd.from_pandas(
                v, npartitions=max(1, len(v) // self.chunk_size)
            )

        # 定義計算單一指標的函數
        def calculate_indicator(name, ohlcv_dict, multipliers, custom_params):
            # 將 Dask DataFrame 轉換為 pandas DataFrame
            pandas_dict = {}
            for k, v in ohlcv_dict.items():
                pandas_dict[k] = v.compute()

            # 計算指標
            return self._calculate_single_indicator(
                name, pandas_dict, multipliers, custom_params.get(name, {})
            )

        # 使用 Dask 並行計算指標
        futures = []
        for name in indicators:
            futures.append(
                dask.delayed(calculate_indicator)(
                    name, dask_dict, multipliers, custom_params
                )
            )

        # 計算結果
        results = dask.compute(*futures)

        # 合併結果
        features = {}
        for result in results:
            features.update(result)

        return pd.DataFrame(features)

    def calculate_fundamental_indicators(self):
        """
        計算基本面指標

        Returns:
            pandas.DataFrame: 包含基本面指標的資料框架
        """
        # 檢查是否有必要的資料
        required_tables = ["income_sheet", "balance_sheet", "cash_flows"]
        for table in required_tables:
            if table not in self.data_dict:
                logging.warning(f"缺少 {table} 資料，無法計算完整的基本面指標")

        # 取得必要的資料
        收盤價 = (
            self.data_dict["price"]["收盤價"]
            if "收盤價" in self.data_dict["price"].columns
            else None
        )

        # 如果沒有收盤價資料，則返回空的資料框架
        if 收盤價 is None:
            return pd.DataFrame()

        # 以下是簡化的基本面指標計算，實際實現可能需要更複雜的邏輯
        # 這裡假設 income_sheet, balance_sheet, cash_flows 都存在於 data_dict 中

        # 計算 ROE
        if "income_sheet" in self.data_dict and "balance_sheet" in self.data_dict:
            淨利 = self.data_dict["income_sheet"].get(
                "本期淨利（淨損）", pd.DataFrame()
            )
            權益總計 = self.data_dict["balance_sheet"].get("權益總計", pd.DataFrame())

            if not 淨利.empty and not 權益總計.empty:
                # 只保留同時存在於收盤價和淨利中的股票
                common_stocks = 淨利.columns.intersection(收盤價.columns)
                淨利 = 淨利[common_stocks]
                權益總計 = 權益總計[common_stocks]

                # 計算 ROE
                ROE = (淨利 / ((權益總計 + 權益總計.shift(1)) / 2)) * 100

                # 返回計算結果
                return pd.DataFrame({"ROE": ROE.unstack()})

        # 如果無法計算 ROE，則返回空的資料框架
        return pd.DataFrame()

    def calculate_custom_features(self):
        """
        計算自定義特徵

        Returns:
            pandas.DataFrame: 包含自定義特徵的資料框架
        """
        # 這裡可以實現自定義的特徵計算邏輯
        # 例如，計算價格動量、波動率等

        price_df = self.data_dict["price"]

        if "收盤價" not in price_df.columns:
            return pd.DataFrame()
        收盤價 = pd.to_numeric(price_df["收盤價"], errors="coerce").fillna(
            method="ffill"
        )

        # 計算價格動量（過去 N 天的價格變化）
        try:
            momentum_5 = 收盤價 / 收盤價.shift(5) - 1
            momentum_5 = momentum_5.unstack()
        except Exception as e:
            logging.warning(f"momentum_5 unstack 失敗: {e}")
            momentum_5 = 收盤價 / 收盤價.shift(5) - 1
        try:
            momentum_10 = 收盤價 / 收盤價.shift(10) - 1
            momentum_10 = momentum_10.unstack()
        except Exception as e:
            logging.warning(f"momentum_10 unstack 失敗: {e}")
            momentum_10 = 收盤價 / 收盤價.shift(10) - 1
        try:
            momentum_20 = 收盤價 / 收盤價.shift(20) - 1
            momentum_20 = momentum_20.unstack()
        except Exception as e:
            logging.warning(f"momentum_20 unstack 失敗: {e}")
            momentum_20 = 收盤價 / 收盤價.shift(20) - 1
        # 計算波動率（過去 N 天收盤價的標準差）
        try:
            volatility_5 = 收盤價.rolling(5).std() / 收盤價
            volatility_5 = volatility_5.unstack()
        except Exception as e:
            logging.warning(f"volatility_5 unstack 失敗: {e}")
            volatility_5 = 收盤價.rolling(5).std() / 收盤價
        try:
            volatility_10 = 收盤價.rolling(10).std() / 收盤價
            volatility_10 = volatility_10.unstack()
        except Exception as e:
            logging.warning(f"volatility_10 unstack 失敗: {e}")
            volatility_10 = 收盤價.rolling(10).std() / 收盤價
        try:
            volatility_20 = 收盤價.rolling(20).std() / 收盤價
            volatility_20 = volatility_20.unstack()
        except Exception as e:
            logging.warning(f"volatility_20 unstack 失敗: {e}")
            volatility_20 = 收盤價.rolling(20).std() / 收盤價
        # 統一為 DataFrame 並合併
        features = [
            momentum_5,
            momentum_10,
            momentum_20,
            volatility_5,
            volatility_10,
            volatility_20,
        ]
        features = [
            f if isinstance(f, pd.DataFrame) else f.to_frame() for f in features
        ]
        feature_names = [
            "momentum_5",
            "momentum_10",
            "momentum_20",
            "volatility_5",
            "volatility_10",
            "volatility_20",
        ]
        for f, name in zip(features, feature_names):
            f.columns = [name]
        return pd.concat(features, axis=1)

    def combine_features(self, technical=True, fundamental=True, custom=True):
        """
        組合各種特徵

        Args:
            technical (bool): 是否包含技術指標
            fundamental (bool): 是否包含基本面指標
            custom (bool): 是否包含自定義特徵

        Returns:
            pandas.DataFrame: 包含所有特徵的資料框架
        """
        features_list = []

        if technical:
            tech_features = self.calculate_technical_indicators()
            if not tech_features.empty:
                features_list.append(tech_features)

        if fundamental:
            fund_features = self.calculate_fundamental_indicators()
            if not fund_features.empty:
                features_list.append(fund_features)

        if custom:
            cust_features = self.calculate_custom_features()
            if not cust_features.empty:
                features_list.append(cust_features)

        if not features_list:
            return pd.DataFrame()

        # 合併所有特徵
        combined_features = pd.concat(features_list, axis=1)

        return combined_features

    def normalize_features(self, features_df, method="standard"):
        """
        標準化特徵

        Args:
            features_df (pandas.DataFrame): 特徵資料框架
            method (str): 標準化方法，可選 'standard', 'minmax', 'robust'

        Returns:
            tuple: (Scaler, pandas.DataFrame) 標準化器和標準化後的資料
        """
        if features_df.empty:
            return None, features_df

        # 選擇標準化方法
        if method == "standard":
            scaler = StandardScaler()
        elif method == "minmax":
            scaler = MinMaxScaler()
        elif method == "robust":
            scaler = RobustScaler()
        else:
            raise ValueError(f"不支援的標準化方法: {method}")

        # 保存列名和索引
        columns = features_df.columns
        index = features_df.index

        # 標準化
        try:
            scaled_data = scaler.fit_transform(features_df)
            scaled_df = pd.DataFrame(scaled_data, index=index, columns=columns)
            return scaler, scaled_df
        except Exception as e:
            logging.warning(f"標準化特徵時發生錯誤: {e}")
            return None, features_df

    def drop_extreme_values(self, features_df, threshold=0.01):
        """
        刪除極端值

        Args:
            features_df (pandas.DataFrame): 特徵資料框架
            threshold (float): 閾值，預設為 0.01（1%）

        Returns:
            pandas.DataFrame: 刪除極端值後的資料框架
        """
        extreme_cases = pd.Series(False, index=features_df.index)

        for col in features_df.columns:
            col_data = features_df[col]
            extreme_cases = (
                extreme_cases
                | (col_data < col_data.quantile(threshold))
                | (col_data > col_data.quantile(1 - threshold))
            )

        return features_df[~extreme_cases]

    def select_features(self, features_df, target_df=None, method="f_regression", k=10):
        """
        特徵選擇

        使用不同的特徵選擇方法選擇最重要的特徵。

        Args:
            features_df (pandas.DataFrame): 特徵資料框架
            target_df (pandas.Series, optional): 目標變數，如果為 None 則使用未來收益率
            method (str): 特徵選擇方法，可選 'f_regression', 'rfe', 'lasso'
            k (int): 要選擇的特徵數量

        Returns:
            tuple: (pandas.DataFrame, object) 選擇後的特徵和選擇器
        """
        if features_df.empty:
            return features_df, None

        # 如果沒有提供目標變數，則使用未來收益率
        if target_df is None:
            if "price" in self.data_dict:
                price_df = self.data_dict["price"]
                if "收盤價" in price_df.columns:
                    # 計算未來 1 天收益率
                    target_df = price_df["收盤價"].pct_change(1).shift(-1)
                else:
                    logging.warning("無法找到收盤價欄位，無法計算未來收益率")
                    return features_df, None
            else:
                logging.warning("無法找到價格資料，無法計算未來收益率")
                return features_df, None

        # 確保 features_df 和 target_df 有相同的索引
        common_index = features_df.index.intersection(target_df.index)
        if len(common_index) == 0:
            logging.warning("特徵和目標變數沒有共同的索引")
            return features_df, None

        features_df = features_df.loc[common_index]
        target_df = target_df.loc[common_index]

        # 移除包含 NaN 的行
        mask = ~features_df.isna().any(axis=1) & ~target_df.isna()
        features_df = features_df[mask]
        target_df = target_df[mask]

        if len(features_df) == 0:
            logging.warning("清理 NaN 後沒有剩餘資料")
            return pd.DataFrame(), None

        # 選擇特徵
        if method == "f_regression":
            # 使用 F 檢定選擇特徵
            selector = SelectKBest(f_regression, k=min(k, features_df.shape[1]))
            X_new = selector.fit_transform(features_df, target_df)

            # 獲取選擇的特徵名稱
            selected_features = features_df.columns[selector.get_support()]

        elif method == "rfe":
            # 使用遞迴特徵消除
            estimator = LinearRegression()
            selector = RFE(estimator, n_features_to_select=min(k, features_df.shape[1]))
            X_new = selector.fit_transform(features_df, target_df)

            # 獲取選擇的特徵名稱
            selected_features = features_df.columns[selector.get_support()]

        elif method == "lasso":
            # 使用 Lasso 正則化選擇特徵
            selector = Lasso(alpha=0.01)
            selector.fit(features_df, target_df)

            # 獲取非零係數的特徵
            selected_features = features_df.columns[selector.coef_ != 0]

            # 如果選擇的特徵太多，則只保留係數絕對值最大的 k 個
            if len(selected_features) > k:
                coef_abs = np.abs(selector.coef_)
                top_k_idx = np.argsort(coef_abs)[-k:]
                selected_features = features_df.columns[top_k_idx]

            X_new = features_df[selected_features].values

        else:
            logging.warning(f"不支援的特徵選擇方法: {method}")
            return features_df, None

        # 創建包含選擇特徵的資料框架
        selected_df = pd.DataFrame(X_new, index=features_df.index, columns=selected_features)

        return selected_df, selector

    def reduce_dimensions(self, features_df, n_components=None, method="pca", variance_ratio=0.95):
        """
        降維

        使用不同的降維方法減少特徵維度。

        Args:
            features_df (pandas.DataFrame): 特徵資料框架
            n_components (int, optional): 要保留的組件數量，如果為 None 則自動決定
            method (str): 降維方法，目前只支援 'pca'
            variance_ratio (float): 要保留的方差比例，只在 n_components 為 None 時使用

        Returns:
            tuple: (pandas.DataFrame, object) 降維後的特徵和降維器
        """
        if features_df.empty:
            return features_df, None

        # 移除包含 NaN 的行
        features_df = features_df.dropna()

        if len(features_df) == 0:
            logging.warning("清理 NaN 後沒有剩餘資料")
            return pd.DataFrame(), None

        # 如果沒有指定組件數量，則自動決定
        if n_components is None:
            n_components = min(features_df.shape[1], features_df.shape[0])

        # 降維
        if method == "pca":
            # 使用 PCA 降維
            reducer = PCA(n_components=n_components)
            X_reduced = reducer.fit_transform(features_df)

            # 如果指定了方差比例，則選擇能解釋該比例方差的最小組件數量
            if n_components is None and variance_ratio < 1.0:
                cumulative_variance = np.cumsum(reducer.explained_variance_ratio_)
                n_components = np.argmax(cumulative_variance >= variance_ratio) + 1

                # 重新擬合 PCA
                reducer = PCA(n_components=n_components)
                X_reduced = reducer.fit_transform(features_df)

            # 創建降維後的資料框架
            columns = [f"PC{i+1}" for i in range(X_reduced.shape[1])]
            reduced_df = pd.DataFrame(X_reduced, index=features_df.index, columns=columns)

        else:
            logging.warning(f"不支援的降維方法: {method}")
            return features_df, None

        return reduced_df, reducer

    def calculate_feature_importance(self, features_df, target_df=None, method="random_forest"):
        """
        計算特徵重要性

        使用不同的方法計算特徵的重要性。

        Args:
            features_df (pandas.DataFrame): 特徵資料框架
            target_df (pandas.Series, optional): 目標變數，如果為 None 則使用未來收益率
            method (str): 計算方法，可選 'random_forest', 'linear', 'correlation'

        Returns:
            pandas.Series: 特徵重要性
        """
        if features_df.empty:
            return pd.Series()

        # 如果沒有提供目標變數，則使用未來收益率
        if target_df is None:
            if "price" in self.data_dict:
                price_df = self.data_dict["price"]
                if "收盤價" in price_df.columns:
                    # 計算未來 1 天收益率
                    target_df = price_df["收盤價"].pct_change(1).shift(-1)
                else:
                    logging.warning("無法找到收盤價欄位，無法計算未來收益率")
                    return pd.Series()
            else:
                logging.warning("無法找到價格資料，無法計算未來收益率")
                return pd.Series()

        # 確保 features_df 和 target_df 有相同的索引
        common_index = features_df.index.intersection(target_df.index)
        if len(common_index) == 0:
            logging.warning("特徵和目標變數沒有共同的索引")
            return pd.Series()

        features_df = features_df.loc[common_index]
        target_df = target_df.loc[common_index]

        # 移除包含 NaN 的行
        mask = ~features_df.isna().any(axis=1) & ~target_df.isna()
        features_df = features_df[mask]
        target_df = target_df[mask]

        if len(features_df) == 0:
            logging.warning("清理 NaN 後沒有剩餘資料")
            return pd.Series()

        # 計算特徵重要性
        if method == "random_forest":
            # 使用隨機森林計算特徵重要性
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(features_df, target_df)
            importance = pd.Series(model.feature_importances_, index=features_df.columns)

        elif method == "linear":
            # 使用線性回歸係數的絕對值作為特徵重要性
            model = LinearRegression()
            model.fit(features_df, target_df)
            importance = pd.Series(np.abs(model.coef_), index=features_df.columns)

        elif method == "correlation":
            # 使用與目標變數的相關性絕對值作為特徵重要性
            importance = features_df.corrwith(target_df).abs()

        else:
            logging.warning(f"不支援的特徵重要性計算方法: {method}")
            return pd.Series()

        # 標準化重要性，使其總和為 1
        importance = importance / importance.sum()

        return importance.sort_values(ascending=False)

    def plot_feature_importance(self, importance, top_n=20, figsize=(12, 8), save_path=None):
        """
        繪製特徵重要性圖

        Args:
            importance (pandas.Series): 特徵重要性
            top_n (int): 顯示前幾個重要的特徵
            figsize (tuple): 圖形大小
            save_path (str, optional): 保存圖形的路徑，如果為 None 則不保存

        Returns:
            matplotlib.figure.Figure: 圖形物件
        """
        if len(importance) == 0:
            logging.warning("沒有特徵重要性資料可供繪圖")
            return None

        # 只顯示前 top_n 個特徵
        if len(importance) > top_n:
            importance = importance.iloc[:top_n]

        # 創建圖形
        fig, ax = plt.subplots(figsize=figsize)

        # 繪製水平條形圖
        importance.sort_values().plot(kind='barh', ax=ax)

        # 設置標題和標籤
        ax.set_title(f'Top {top_n} Feature Importance', fontsize=16)
        ax.set_xlabel('Importance', fontsize=14)
        ax.set_ylabel('Feature', fontsize=14)

        # 調整佈局
        plt.tight_layout()

        # 保存圖形
        if save_path is not None:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        return fig


def process_chunk(
    chunk, calculator, normalize=True, remove_extremes=True, clean_data=True
):
    """
    處理資料分塊

    Args:
        chunk (pandas.DataFrame): 資料分塊
        calculator (FeatureCalculator): 特徵計算器
        normalize (bool): 是否標準化特徵
        remove_extremes (bool): 是否刪除極端值
        clean_data (bool): 是否清理資料

    Returns:
        pandas.DataFrame: 處理後的特徵
    """
    # 計算特徵
    features = calculator.combine_features()

    # 清理資料
    if clean_data and not features.empty:
        features, _ = calculator.data_cleaner.clean_data(features)

    # 標準化特徵
    if normalize and not features.empty:
        _, features = calculator.normalize_features(features)

    # 刪除極端值
    if remove_extremes and not features.empty:
        features = calculator.drop_extreme_values(features)

    return features


def compute_features(
    start_date=None,
    end_date=None,
    normalize=True,
    remove_extremes=True,
    clean_data=True,
    use_distributed=False,
    chunk_size=10000,
    feature_selection=False,
    feature_selection_method="f_regression",
    feature_selection_k=10,
    dimensionality_reduction=False,
    dimensionality_reduction_method="pca",
    n_components=None,
    variance_ratio=0.95,
    save_to_feature_store=False,
    feature_name="combined_features",
    feature_tags=None,
):
    """
    計算特徵的主函數

    Args:
        start_date (datetime.date, optional): 開始日期
        end_date (datetime.date, optional): 結束日期
        normalize (bool): 是否標準化特徵
        remove_extremes (bool): 是否刪除極端值
        clean_data (bool): 是否清理資料
        use_distributed (bool): 是否使用分散式處理
        chunk_size (int): 記憶體分塊大小
        feature_selection (bool): 是否進行特徵選擇
        feature_selection_method (str): 特徵選擇方法，可選 'f_regression', 'rfe', 'lasso'
        feature_selection_k (int): 要選擇的特徵數量
        dimensionality_reduction (bool): 是否進行降維
        dimensionality_reduction_method (str): 降維方法，目前只支援 'pca'
        n_components (int, optional): 要保留的組件數量，如果為 None 則自動決定
        variance_ratio (float): 要保留的方差比例，只在 n_components 為 None 時使用
        save_to_feature_store (bool): 是否保存到特徵存儲
        feature_name (str): 特徵名稱，只在 save_to_feature_store 為 True 時使用
        feature_tags (List[str], optional): 特徵標籤，只在 save_to_feature_store 為 True 時使用

    Returns:
        pandas.DataFrame: 計算好的特徵資料框架
    """
    # 載入資料
    data_dict = load_data(start_date, end_date)

    # 創建特徵計算器
    calculator = FeatureCalculator(
        data_dict, use_distributed=use_distributed, chunk_size=chunk_size
    )

    # 檢查是否使用分散式處理
    if use_distributed:
        if DASK_AVAILABLE:
            features = _compute_features_with_dask(
                calculator, normalize, remove_extremes, clean_data, chunk_size
            )
        elif RAY_AVAILABLE:
            features = _compute_features_with_ray(
                calculator, normalize, remove_extremes, clean_data, chunk_size
            )
        else:
            logging.warning("無法使用分散式處理，將使用標準處理方式")
            # 使用標準處理方式
            features = calculator.combine_features()

            # 清理資料
            if clean_data and not features.empty:
                features, _ = calculator.data_cleaner.clean_data(features)

            # 標準化特徵
            if normalize and not features.empty:
                _, features = calculator.normalize_features(features)

            # 刪除極端值
            if remove_extremes and not features.empty:
                features = calculator.drop_extreme_values(features)
    else:
        # 使用標準處理方式
        features = calculator.combine_features()

        # 清理資料
        if clean_data and not features.empty:
            features, _ = calculator.data_cleaner.clean_data(features)

        # 標準化特徵
        if normalize and not features.empty:
            _, features = calculator.normalize_features(features)

        # 刪除極端值
        if remove_extremes and not features.empty:
            features = calculator.drop_extreme_values(features)

    # 特徵選擇
    if feature_selection and not features.empty:
        selected_features, selector = calculator.select_features(
            features, method=feature_selection_method, k=feature_selection_k
        )
        if not selected_features.empty:
            features = selected_features
            logging.info(f"已選擇 {len(selected_features.columns)} 個特徵")
        else:
            logging.warning("特徵選擇失敗，將使用原始特徵")

    # 降維
    if dimensionality_reduction and not features.empty:
        reduced_features, reducer = calculator.reduce_dimensions(
            features, n_components=n_components, method=dimensionality_reduction_method,
            variance_ratio=variance_ratio
        )
        if not reduced_features.empty:
            features = reduced_features
            if hasattr(reducer, 'explained_variance_ratio_'):
                explained_variance = sum(reducer.explained_variance_ratio_)
                logging.info(f"降維後保留了 {explained_variance:.2%} 的方差")
            logging.info(f"降維後特徵維度: {features.shape}")
        else:
            logging.warning("降維失敗，將使用原始特徵")

    # 保存到特徵存儲
    if save_to_feature_store and not features.empty:
        try:
            from src.core.feature_store import FeatureStore
            feature_store = FeatureStore()
            metadata = {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "normalize": normalize,
                "remove_extremes": remove_extremes,
                "clean_data": clean_data,
                "feature_selection": feature_selection,
                "feature_selection_method": feature_selection_method if feature_selection else None,
                "dimensionality_reduction": dimensionality_reduction,
                "dimensionality_reduction_method": dimensionality_reduction_method if dimensionality_reduction else None,
                "n_components": n_components,
                "variance_ratio": variance_ratio,
            }
            version = feature_store.save_features(
                features, feature_name, metadata=metadata, tags=feature_tags
            )
            logging.info(f"特徵已保存到特徵存儲，版本: {version}")
        except Exception as e:
            logging.error(f"保存到特徵存儲時發生錯誤: {e}")

    return features


def _compute_features_with_dask(
    calculator, normalize, remove_extremes, clean_data, chunk_size
):
    """
    使用 Dask 進行分散式特徵計算

    Args:
        calculator (FeatureCalculator): 特徵計算器
        normalize (bool): 是否標準化特徵
        remove_extremes (bool): 是否刪除極端值
        clean_data (bool): 是否清理資料
        chunk_size (int): 記憶體分塊大小

    Returns:
        pandas.DataFrame: 計算好的特徵資料框架
    """
    try:
        # 獲取價格資料
        price_df = calculator.data_dict["price"]

        # 轉換為 Dask DataFrame
        ddf = dd.from_pandas(price_df, npartitions=max(1, len(price_df) // chunk_size))

        # 定義 map_partitions 函數
        def process_partition(partition):
            # 創建臨時資料字典
            temp_dict = calculator.data_dict.copy()
            temp_dict["price"] = partition

            # 創建臨時計算器
            temp_calculator = FeatureCalculator(temp_dict)

            # 處理分區
            return process_chunk(
                partition, temp_calculator, normalize, remove_extremes, clean_data
            )

        # 應用函數到每個分區
        result_ddf = ddf.map_partitions(process_partition)

        # 計算結果
        return result_ddf.compute()

    except Exception as e:
        logging.error(f"使用 Dask 計算特徵時發生錯誤: {e}")
        logging.info("回退到標準處理方式")

        # 回退到標準處理方式
        features = calculator.combine_features()

        # 清理資料
        if clean_data and not features.empty:
            features, _ = calculator.data_cleaner.clean_data(features)

        # 標準化特徵
        if normalize and not features.empty:
            _, features = calculator.normalize_features(features)

        # 刪除極端值
        if remove_extremes and not features.empty:
            features = calculator.drop_extreme_values(features)

        return features


def _compute_features_with_ray(
    calculator, normalize, remove_extremes, clean_data, chunk_size
):
    """
    使用 Ray 進行分散式特徵計算

    Args:
        calculator (FeatureCalculator): 特徵計算器
        normalize (bool): 是否標準化特徵
        remove_extremes (bool): 是否刪除極端值
        clean_data (bool): 是否清理資料
        chunk_size (int): 記憶體分塊大小

    Returns:
        pandas.DataFrame: 計算好的特徵資料框架
    """
    try:
        # 初始化 Ray
        if not ray.is_initialized():
            ray.init()

        # 獲取價格資料
        price_df = calculator.data_dict["price"]

        # 分割資料
        chunks = []
        for i in range(0, len(price_df), chunk_size):
            chunks.append(price_df.iloc[i : i + chunk_size])

        # 定義 Ray 任務
        @ray.remote
        def process_chunk_ray(
            chunk, data_dict_copy, normalize, remove_extremes, clean_data
        ):
            # 創建臨時資料字典
            temp_dict = data_dict_copy.copy()
            temp_dict["price"] = chunk

            # 創建臨時計算器
            temp_calculator = FeatureCalculator(temp_dict)

            # 處理分塊
            return process_chunk(
                chunk, temp_calculator, normalize, remove_extremes, clean_data
            )

        # 提交任務
        futures = []
        data_dict_copy = {k: v for k, v in calculator.data_dict.items() if k != "price"}

        for chunk in chunks:
            futures.append(
                process_chunk_ray.remote(
                    chunk, data_dict_copy, normalize, remove_extremes, clean_data
                )
            )

        # 獲取結果
        results = ray.get(futures)

        # 合併結果
        if results:
            return pd.concat(results)
        else:
            return pd.DataFrame()

    except Exception as e:
        logging.error(f"使用 Ray 計算特徵時發生錯誤: {e}")
        logging.info("回退到標準處理方式")

        # 回退到標準處理方式
        features = calculator.combine_features()

        # 清理資料
        if clean_data and not features.empty:
            features, _ = calculator.data_cleaner.clean_data(features)

        # 標準化特徵
        if normalize and not features.empty:
            _, features = calculator.normalize_features(features)

        # 刪除極端值
        if remove_extremes and not features.empty:
            features = calculator.drop_extreme_values(features)

        return features
