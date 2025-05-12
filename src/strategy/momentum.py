# -*- coding: utf-8 -*-
"""
動量策略模組
"""

import pandas as pd


class MomentumStrategy:
    """
    動量策略：根據價格動能產生買賣訊號
    """

    def __init__(self, window: int = 20):
        self.window = window

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        根據收盤價與移動平均產生買賣訊號（1=買進, -1=賣出, 0=觀望）
        :param df: 包含'Close'欄位的DataFrame
        :return: 訊號序列
        """
        ma = df["Close"].rolling(window=self.window).mean()
        signal = (df["Close"] > ma).astype(int) - (df["Close"] < ma).astype(int)
        return signal
