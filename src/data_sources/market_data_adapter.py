# -*- coding: utf-8 -*-
"""
市場數據適配器模組
"""

import pandas as pd


class MarketDataAdapter:
    """
    市場數據適配器基礎類別，負責連接數據源並取得市場資料。
    """

    def __init__(self, source: str):
        """
        初始化，指定數據來源（如'yahoo', 'twse'等）
        """
        self.source = source
        self.connection = None

    def connect(self):
        """
        連接到指定的數據來源。
        """
        # TODO: 根據source實作不同連接方式

    def get_price(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """
        取得指定股票代碼在指定期間的歷史價格資料。
        :param symbol: 股票代碼
        :param start: 起始日期（YYYY-MM-DD）
        :param end: 結束日期（YYYY-MM-DD）
        :return: 價格資料DataFrame
        """
        # TODO: 根據source實作資料取得
        return pd.DataFrame()
