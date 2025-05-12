# -*- coding: utf-8 -*-
"""
均值回歸策略模組
"""

import pandas as pd


class MeanReversionStrategy:
    """
    均值回歸策略：價格偏離均線時產生反向操作訊號
    """

    def __init__(self, window: int = 20, threshold: float = 0.02):
        self.window = window
        self.threshold = threshold

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        根據收盤價與移動平均產生買賣訊號（1=買進, -1=賣出, 0=觀望）
        :param df: 包含'Close'欄位的DataFrame
        :return: 訊號序列
        """
        ma = df["Close"].rolling(window=self.window).mean()
        diff = (df["Close"] - ma) / ma
        signal = (diff < -self.threshold).astype(int) - (diff > self.threshold).astype(
            int
        )
        return signal
