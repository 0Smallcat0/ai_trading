# -*- coding: utf-8 -*-
"""
均值回歸策略模組

此模組實現基於均值回歸的交易策略。
"""

from typing import Dict, Any, List
import pandas as pd

from .base import Strategy, ParameterError, DataValidationError


class MeanReversionStrategy(Strategy):
    """
    均值回歸策略：價格偏離均線時產生反向操作訊號。

    當價格顯著低於移動平均線時產生買入訊號（預期回歸），
    當價格顯著高於移動平均線時產生賣出訊號（預期回歸）。

    Attributes:
        window (int): 移動平均線窗口大小
        threshold (float): 偏離閾值（百分比）

    Example:
        >>> strategy = MeanReversionStrategy(window=20, threshold=0.02)
        >>> signals = strategy.generate_signals(price_data)
    """

    def __init__(self, window: int = 20, threshold: float = 0.02, **kwargs: Any) -> None:
        """
        初始化均值回歸策略。

        Args:
            window: 移動平均線窗口大小，必須大於0
            threshold: 偏離閾值（百分比），必須大於0
            **kwargs: 其他參數

        Raises:
            ParameterError: 當參數不符合要求時
        """
        super().__init__(name="MeanReversion", window=window, threshold=threshold, **kwargs)
        self.window = window
        self.threshold = threshold

    def _validate_parameters(self) -> None:
        """
        驗證策略參數。

        Raises:
            ParameterError: 當參數不符合要求時
        """
        if not isinstance(self.window, int) or self.window <= 0:
            raise ParameterError(f"window 必須是正整數，得到: {self.window}")

        if not isinstance(self.threshold, (int, float)) or self.threshold <= 0:
            raise ParameterError(f"threshold 必須是正數，得到: {self.threshold}")

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        根據收盤價與移動平均產生均值回歸訊號。

        Args:
            data: 價格資料，必須包含 'Close' 或 '收盤價' 欄位

        Returns:
            包含交易訊號的資料框架，包含以下欄位：
            - signal: 主要訊號 (1=買入, -1=賣出, 0=觀望)
            - buy_signal: 買入訊號 (1=買入, 0=無動作)
            - sell_signal: 賣出訊號 (1=賣出, 0=無動作)
            - mean_reversion_ma: 均值回歸移動平均線
            - deviation: 價格偏離度（百分比）

        Raises:
            DataValidationError: 當輸入資料格式不正確時
        """
        # 檢查必要欄位
        price_col = None
        if "Close" in data.columns:
            price_col = "Close"
        elif "收盤價" in data.columns:
            price_col = "收盤價"
        else:
            raise DataValidationError("資料必須包含 'Close' 或 '收盤價' 欄位")

        if data.empty:
            raise DataValidationError("輸入資料不能為空")

        # 計算移動平均線
        price_series = data[price_col].astype(float)
        ma = price_series.rolling(window=self.window).mean()

        # 計算偏離度
        deviation = (price_series - ma) / ma

        # 生成訊號
        signals = pd.DataFrame(index=data.index)
        signals["mean_reversion_ma"] = ma
        signals["deviation"] = deviation

        # 均值回歸訊號：
        # 當偏離度小於負閾值時買入（價格被低估）
        # 當偏離度大於正閾值時賣出（價格被高估）
        signals["signal"] = (
            (deviation < -self.threshold).astype(int) -
            (deviation > self.threshold).astype(int)
        )

        # 計算訊號變化
        signals["position_change"] = signals["signal"].diff()

        # 買入訊號：從非正變為正
        signals["buy_signal"] = (
            (signals["signal"] > 0) & (signals["position_change"] > 0)
        ).astype(int)

        # 賣出訊號：從非負變為負
        signals["sell_signal"] = (
            (signals["signal"] < 0) & (signals["position_change"] < 0)
        ).astype(int)

        # 填充NaN值
        signals = signals.fillna(0)

        return signals

    def _get_default_param_grid(self) -> Dict[str, List[Any]]:
        """
        獲取預設參數網格。

        Returns:
            預設參數網格
        """
        return {
            "window": [10, 15, 20, 25, 30],
            "threshold": [0.01, 0.02, 0.03, 0.05]
        }
