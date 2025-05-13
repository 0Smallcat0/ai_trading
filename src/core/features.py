"""
技術與基本面指標計算模組

此模組負責計算各種技術指標和基本面指標，為策略研究提供必要的特徵。

主要功能：
- 計算技術指標（如 RSI、MACD、KD 等）
- 計算基本面指標（如 ROE、ROA、EPS 等）
- 特徵工程和資料轉換
"""

import pandas as pd
import copy
from src.core.data_ingest import load_data
import logging


class FeatureCalculator:
    """特徵計算器類別，用於計算各種技術和基本面指標"""

    def __init__(self, data_dict=None):
        """
        初始化特徵計算器

        Args:
            data_dict (dict, optional): 包含各種資料的字典，如果為 None 則自動載入
        """
        if data_dict is None:
            self.data_dict = load_data()
        else:
            self.data_dict = data_dict

        # 確保必要的資料存在
        if "price" not in self.data_dict:
            raise ValueError("必須提供價格資料")

    def calculate_technical_indicators(
        self, stock_id=None, indicators=None, multipliers=None
    ):
        """
        計算技術指標

        Args:
            stock_id (str, optional): 股票代號，如果為 None 則計算所有股票
            indicators (list, optional): 指標列表，如果為 None 則計算所有支援的指標
            multipliers (list, optional): 參數倍數列表，用於調整指標參數

        Returns:
            pandas.DataFrame: 包含技術指標的資料框架
        """
        if indicators is None:
            indicators = [
                "RSI",
                "MACD",
                "SMA",
                "EMA",
                "WMA",
                "BBANDS",
                "STOCH",
                "CCI",
                "MOM",
                "ROC",
            ]

        if multipliers is None:
            multipliers = [0.5, 1, 2]

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
        ohlcv_dict = {}
        for col in ["開盤價", "最高價", "最低價", "收盤價", "成交股數"]:
            if col in price_df.columns:
                ohlcv_dict[col.replace("價", "")] = pd.to_numeric(
                    price_df[col], errors="coerce"
                )
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

        # 如果缺少必要的欄位，則返回空的資料框架
        if len(ohlcv_dict) < 4:
            return pd.DataFrame()

        # 計算技術指標
        features = {}
        for name in indicators:
            # 需要 high/low 的指標，若缺少則跳過
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
            ]
            if need_high_low and (
                ("high" not in ohlcv_dict) or ("low" not in ohlcv_dict)
            ):
                logging.warning(f"跳過 {name} 指標，因為缺少 high/low 欄位")
                continue
            if not hasattr(abstract, name):
                continue
            f = getattr(abstract, name)
            org_params = dict(f.parameters)
            for m in multipliers:
                params = copy.copy(org_params)
                # 只對 int/float 參數做倍數運算
                for k, v in params.items():
                    if isinstance(v, (int, float)):
                        params[k] = int(v * m) if isinstance(v, int) else v * m
                try:
                    values = f(ohlcv_dict, **params)
                    if isinstance(values, pd.Series):
                        features[f"{name}_{str(params)}"] = values
                    elif isinstance(values, pd.DataFrame):
                        for output_name, series in values.items():
                            features[f"{name}_{output_name}_{str(params)}"] = series
                except Exception as e:
                    logging.warning(f"計算 {name} 指標時發生錯誤: {e}")
                    continue
                # 重置參數
                f.parameters = org_params

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

    def normalize_features(self, features_df):
        """
        標準化特徵

        Args:
            features_df (pandas.DataFrame): 特徵資料框架

        Returns:
            tuple: (StandardScaler, pandas.DataFrame) 標準化器和標準化後的資料
        """
        return scale(features_df)

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


def compute_features(
    start_date=None, end_date=None, normalize=True, remove_extremes=True
):
    """
    計算特徵的主函數

    Args:
        start_date (datetime.date, optional): 開始日期
        end_date (datetime.date, optional): 結束日期
        normalize (bool): 是否標準化特徵
        remove_extremes (bool): 是否刪除極端值

    Returns:
        pandas.DataFrame: 計算好的特徵資料框架
    """
    # 載入資料
    data_dict = load_data(start_date, end_date)

    # 創建特徵計算器
    calculator = FeatureCalculator(data_dict)

    # 計算特徵
    features = calculator.combine_features()

    # 標準化特徵
    if normalize and not features.empty:
        _, features = calculator.normalize_features(features)

    # 刪除極端值
    if remove_extremes and not features.empty:
        features = calculator.drop_extreme_values(features)

    return features
