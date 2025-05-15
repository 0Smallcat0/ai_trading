# -*- coding: utf-8 -*-
"""
資料集處理模組

此模組提供資料集的處理功能，包括：
- 資料集分割
- 特徵處理
- 資料集載入
- 時間序列資料處理
"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from src.config import LOG_LEVEL
from src.core.features import (
    calculate_fundamental_indicators,
    calculate_technical_indicators,
)

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class TimeSeriesSplit:
    """
    時間序列資料分割

    用於將時間序列資料分割為訓練集、驗證集和測試集，
    確保時間順序，避免前瞻偏差。
    """

    def __init__(
        self, test_size: float = 0.2, val_size: float = 0.2, date_column: str = "date"
    ):
        """
        初始化時間序列分割器

        Args:
            test_size (float): 測試集比例
            val_size (float): 驗證集比例
            date_column (str): 日期欄位名稱
        """
        self.test_size = test_size
        self.val_size = val_size
        self.date_column = date_column

    def split(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        分割資料集

        Args:
            df (pd.DataFrame): 資料集

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]: 訓練集、驗證集、測試集
        """
        # 確保資料按日期排序
        if self.date_column in df.columns:
            df = df.sort_values(by=self.date_column)

        # 計算分割點
        n = len(df)
        test_idx = int(n * (1 - self.test_size))
        val_idx = int(test_idx * (1 - self.val_size))

        # 分割資料
        train = df.iloc[:val_idx].copy()
        val = df.iloc[val_idx:test_idx].copy()
        test = df.iloc[test_idx:].copy()

        logger.info(
            f"資料集分割完成: 訓練集 {len(train)} 筆, 驗證集 {len(val)} 筆, 測試集 {len(test)} 筆"
        )

        return train, val, test

    def split_by_date(
        self,
        df: pd.DataFrame,
        train_end_date: Union[str, datetime],
        val_end_date: Union[str, datetime],
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        按日期分割資料集

        Args:
            df (pd.DataFrame): 資料集
            train_end_date (Union[str, datetime]): 訓練集結束日期
            val_end_date (Union[str, datetime]): 驗證集結束日期

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]: 訓練集、驗證集、測試集
        """
        if self.date_column not in df.columns:
            logger.error(f"資料集中缺少日期欄位: {self.date_column}")
            raise ValueError(f"資料集中缺少日期欄位: {self.date_column}")

        # 確保日期格式正確
        if isinstance(train_end_date, str):
            train_end_date = pd.to_datetime(train_end_date)
        if isinstance(val_end_date, str):
            val_end_date = pd.to_datetime(val_end_date)

        # 確保資料按日期排序
        df = df.sort_values(by=self.date_column)

        # 分割資料
        train = df[df[self.date_column] <= train_end_date].copy()
        val = df[
            (df[self.date_column] > train_end_date)
            & (df[self.date_column] <= val_end_date)
        ].copy()
        test = df[df[self.date_column] > val_end_date].copy()

        logger.info(
            f"資料集分割完成: 訓練集 {len(train)} 筆 (截至 {train_end_date}), "
            f"驗證集 {len(val)} 筆 (截至 {val_end_date}), 測試集 {len(test)} 筆"
        )

        return train, val, test


class FeatureProcessor:
    """
    特徵處理器

    用於處理特徵，包括標準化、歸一化、特徵選擇等。
    """

    def __init__(
        self,
        scaler_type: str = "standard",
        feature_columns: Optional[List[str]] = None,
        target_column: Optional[str] = None,
    ):
        """
        初始化特徵處理器

        Args:
            scaler_type (str): 縮放器類型，可選 "standard" 或 "minmax"
            feature_columns (Optional[List[str]]): 特徵欄位列表
            target_column (Optional[str]): 目標欄位
        """
        self.scaler_type = scaler_type
        self.feature_columns = feature_columns
        self.target_column = target_column

        # 初始化縮放器
        if scaler_type == "standard":
            self.scaler = StandardScaler()
        elif scaler_type == "minmax":
            self.scaler = MinMaxScaler()
        else:
            logger.error(f"未知的縮放器類型: {scaler_type}")
            raise ValueError(
                f"未知的縮放器類型: {scaler_type}，可用類型: standard, minmax"
            )

        self.fitted = False

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        擬合並轉換資料

        Args:
            df (pd.DataFrame): 資料集

        Returns:
            pd.DataFrame: 轉換後的資料集
        """
        # 如果沒有指定特徵欄位，則使用所有數值欄位
        if self.feature_columns is None:
            self.feature_columns = df.select_dtypes(include=np.number).columns.tolist()

            # 如果有目標欄位，則從特徵欄位中移除
            if (
                self.target_column is not None
                and self.target_column in self.feature_columns
            ):
                self.feature_columns.remove(self.target_column)

        # 檢查特徵欄位是否存在
        missing_columns = [col for col in self.feature_columns if col not in df.columns]
        if missing_columns:
            logger.warning(f"資料集中缺少以下特徵欄位: {missing_columns}")
            self.feature_columns = [
                col for col in self.feature_columns if col in df.columns
            ]

        # 擬合並轉換特徵
        if self.feature_columns:
            df_scaled = df.copy()
            df_scaled[self.feature_columns] = self.scaler.fit_transform(
                df[self.feature_columns]
            )
            self.fitted = True
            return df_scaled
        else:
            logger.warning("沒有可用的特徵欄位進行縮放")
            return df.copy()

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        轉換資料

        Args:
            df (pd.DataFrame): 資料集

        Returns:
            pd.DataFrame: 轉換後的資料集
        """
        if not self.fitted:
            logger.warning("縮放器尚未擬合，將進行擬合並轉換")
            return self.fit_transform(df)

        # 檢查特徵欄位是否存在
        missing_columns = [col for col in self.feature_columns if col not in df.columns]
        if missing_columns:
            logger.warning(f"資料集中缺少以下特徵欄位: {missing_columns}")
            available_columns = [
                col for col in self.feature_columns if col in df.columns
            ]

            if not available_columns:
                logger.warning("沒有可用的特徵欄位進行縮放")
                return df.copy()

            # 創建一個臨時 DataFrame，包含所有特徵欄位
            temp_df = pd.DataFrame(0, index=df.index, columns=self.feature_columns)
            temp_df[available_columns] = df[available_columns]

            # 轉換特徵
            df_scaled = df.copy()
            df_scaled[available_columns] = self.scaler.transform(
                temp_df[self.feature_columns]
            )[:, [self.feature_columns.index(col) for col in available_columns]]
            return df_scaled

        # 轉換特徵
        df_scaled = df.copy()
        df_scaled[self.feature_columns] = self.scaler.transform(
            df[self.feature_columns]
        )
        return df_scaled


class DatasetLoader:
    """
    資料集載入器

    用於載入和準備資料集。
    """

    def __init__(
        self,
        price_data: Optional[pd.DataFrame] = None,
        fundamental_data: Optional[pd.DataFrame] = None,
        sentiment_data: Optional[pd.DataFrame] = None,
        date_column: str = "date",
        symbol_column: str = "symbol",
        price_column: str = "close",
    ):
        """
        初始化資料集載入器

        Args:
            price_data (Optional[pd.DataFrame]): 價格資料
            fundamental_data (Optional[pd.DataFrame]): 基本面資料
            sentiment_data (Optional[pd.DataFrame]): 情緒資料
            date_column (str): 日期欄位名稱
            symbol_column (str): 股票代碼欄位名稱
            price_column (str): 價格欄位名稱
        """
        self.price_data = price_data
        self.fundamental_data = fundamental_data
        self.sentiment_data = sentiment_data
        self.date_column = date_column
        self.symbol_column = symbol_column
        self.price_column = price_column

    def load_from_database(
        self,
        symbols: List[str],
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
    ) -> None:
        """
        從資料庫載入資料

        Args:
            symbols (List[str]): 股票代碼列表
            start_date (Union[str, datetime]): 開始日期
            end_date (Union[str, datetime]): 結束日期
        """
        # 這裡應該實現從資料庫載入資料的邏輯
        # 由於需要與資料庫模組整合，這裡只提供一個框架
        logger.info(f"從資料庫載入資料: {symbols}, {start_date} - {end_date}")

        # 載入價格資料
        # self.price_data = ...

        # 載入基本面資料
        # self.fundamental_data = ...

        # 載入情緒資料
        # self.sentiment_data = ...

    def prepare_features(
        self,
        technical_indicators: bool = True,
        fundamental_indicators: bool = True,
        sentiment_indicators: bool = True,
        target_type: str = "return",
        target_horizon: int = 5,
        additional_features: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        準備特徵資料集

        Args:
            technical_indicators (bool): 是否包含技術指標
            fundamental_indicators (bool): 是否包含基本面指標
            sentiment_indicators (bool): 是否包含情緒指標
            target_type (str): 目標類型，可選 "return", "direction", "volatility"
            target_horizon (int): 目標預測期限（天數）
            additional_features (Optional[List[str]]): 額外特徵列表

        Returns:
            pd.DataFrame: 特徵資料集
        """
        if self.price_data is None:
            logger.error("尚未載入價格資料")
            raise ValueError("尚未載入價格資料")

        # 創建特徵資料集
        features = self.price_data.copy()

        # 計算技術指標
        if technical_indicators:
            tech_indicators = calculate_technical_indicators(
                self.price_data, price_column=self.price_column
            )
            features = pd.merge(
                features,
                tech_indicators,
                on=[self.date_column, self.symbol_column],
                how="left",
            )

        # 合併基本面指標
        if fundamental_indicators and self.fundamental_data is not None:
            fund_indicators = calculate_fundamental_indicators(self.fundamental_data)
            features = pd.merge(
                features,
                fund_indicators,
                on=[self.date_column, self.symbol_column],
                how="left",
            )

        # 合併情緒指標
        if sentiment_indicators and self.sentiment_data is not None:
            features = pd.merge(
                features,
                self.sentiment_data,
                on=[self.date_column, self.symbol_column],
                how="left",
            )

        # 計算目標變數
        if target_type == "return":
            # 計算未來 n 天的收益率
            features["target"] = (
                features.groupby(self.symbol_column)[self.price_column].shift(
                    -target_horizon
                )
                / features[self.price_column]
                - 1
            )
        elif target_type == "direction":
            # 計算未來 n 天的價格方向（上漲=1，下跌=0）
            future_price = features.groupby(self.symbol_column)[
                self.price_column
            ].shift(-target_horizon)
            features["target"] = (future_price > features[self.price_column]).astype(
                int
            )
        elif target_type == "volatility":
            # 計算未來 n 天的波動率
            future_prices = [
                features.groupby(self.symbol_column)[self.price_column].shift(-i)
                for i in range(1, target_horizon + 1)
            ]
            future_returns = [
                (p / features[self.price_column] - 1) for p in future_prices
            ]
            features["target"] = pd.concat(future_returns, axis=1).std(axis=1)
        else:
            logger.error(f"未知的目標類型: {target_type}")
            raise ValueError(
                f"未知的目標類型: {target_type}，可用類型: return, direction, volatility"
            )

        # 處理缺失值
        features = features.dropna()

        logger.info(
            f"特徵資料集準備完成: {len(features)} 筆, {len(features.columns)} 個特徵"
        )

        return features
