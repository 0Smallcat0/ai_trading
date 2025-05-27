"""回測數據饋送模組

此模組負責為回測提供市場數據饋送功能。
"""

import logging
from datetime import datetime
from typing import List
import numpy as np
import pandas as pd

# 設定日誌
logger = logging.getLogger(__name__)


class BacktestDataFeed:
    """回測數據饋送器"""

    def __init__(self):
        """初始化數據饋送器"""
        self.data_cache = {}

    def load_market_data(
        self, symbols: List[str], start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """載入市場資料

        Args:
            symbols: 股票代碼列表
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            pd.DataFrame: 市場資料
        """
        cache_key = f"{'-'.join(symbols)}_{start_date}_{end_date}"

        if cache_key in self.data_cache:
            logger.info("使用快取的市場資料")
            return self.data_cache[cache_key]

        logger.info("載入市場資料: %s, %s - %s", symbols, start_date, end_date)

        # 生成日期範圍
        dates = pd.date_range(start=start_date, end=end_date, freq="D")
        dates = dates[dates.weekday < 5]  # 只保留工作日

        data = []
        for symbol in symbols:
            symbol_data = self._generate_symbol_data(symbol, dates)
            data.extend(symbol_data)

        df = pd.DataFrame(data)

        # 快取數據
        self.data_cache[cache_key] = df

        logger.info("市場資料載入完成，共 %d 筆記錄", len(df))
        return df

    def _generate_symbol_data(self, symbol: str, dates: pd.DatetimeIndex) -> List[dict]:
        """生成單一股票的模擬數據

        Args:
            symbol: 股票代碼
            dates: 日期範圍

        Returns:
            List[dict]: 股票數據列表
        """
        # 設定隨機種子以確保可重現性
        np.random.seed(hash(symbol) % 10000)

        # 初始價格
        initial_price = np.random.uniform(50, 500)

        # 生成價格序列
        returns = np.random.normal(0.0005, 0.02, len(dates))
        prices = [initial_price]

        for ret in returns:
            prices.append(prices[-1] * (1 + ret))

        prices = prices[1:]  # 移除初始價格

        data = []
        for i, (date, close) in enumerate(zip(dates, prices)):
            # 生成OHLC資料
            volatility = 0.02
            high = close * (1 + np.random.uniform(0, volatility))
            low = close * (1 - np.random.uniform(0, volatility))
            open_price = prices[i - 1] if i > 0 else close

            # 確保價格邏輯正確
            high = max(high, open_price, close)
            low = min(low, open_price, close)

            # 生成成交量
            volume = np.random.randint(100000, 10000000)

            data.append({
                "symbol": symbol,
                "date": date,
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close, 2),
                "volume": volume,
            })

        return data

    def validate_data(self, data: pd.DataFrame) -> bool:
        """驗證數據完整性

        Args:
            data: 市場資料

        Returns:
            bool: 是否通過驗證
        """
        required_columns = ["symbol", "date", "open", "high", "low", "close", "volume"]

        # 檢查必要欄位
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            logger.error("市場資料缺少必要欄位: %s", missing_columns)
            return False

        # 檢查數據完整性
        if data.empty:
            logger.error("市場資料為空")
            return False

        # 檢查價格邏輯
        invalid_prices = data[
            (data["high"] < data["low"])
            | (data["high"] < data["open"])
            | (data["high"] < data["close"])
            | (data["low"] > data["open"])
            | (data["low"] > data["close"])
        ]

        if not invalid_prices.empty:
            logger.warning("發現 %d 筆價格邏輯錯誤的記錄", len(invalid_prices))

        # 檢查缺失值
        missing_data = data.isnull().sum().sum()
        if missing_data > 0:
            logger.warning("發現 %d 個缺失值", missing_data)

        logger.info("數據驗證完成")
        return True

    def get_data_summary(self, data: pd.DataFrame) -> dict:
        """獲取數據摘要

        Args:
            data: 市場資料

        Returns:
            dict: 數據摘要
        """
        if data.empty:
            return {"error": "數據為空"}

        summary = {
            "total_records": len(data),
            "symbols": data["symbol"].nunique(),
            "symbol_list": sorted(data["symbol"].unique().tolist()),
            "date_range": {
                "start": data["date"].min().isoformat() if not data.empty else None,
                "end": data["date"].max().isoformat() if not data.empty else None,
            },
            "price_stats": {
                "min_price": float(data["low"].min()),
                "max_price": float(data["high"].max()),
                "avg_price": float(data["close"].mean()),
            },
            "volume_stats": {
                "min_volume": int(data["volume"].min()),
                "max_volume": int(data["volume"].max()),
                "avg_volume": int(data["volume"].mean()),
            },
        }

        return summary

    def clear_cache(self):
        """清除數據快取"""
        self.data_cache.clear()
        logger.info("數據快取已清除")

    def get_cache_info(self) -> dict:
        """獲取快取資訊

        Returns:
            dict: 快取資訊
        """
        return {
            "cache_size": len(self.data_cache),
            "cache_keys": list(self.data_cache.keys()),
        }


class PandasDataFeed(BacktestDataFeed):
    """Pandas數據饋送器（與backtrader兼容）"""

    def __init__(self):
        """初始化Pandas數據饋送器"""
        super().__init__()

    def to_backtrader_format(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """轉換為backtrader格式

        Args:
            data: 原始數據
            symbol: 股票代碼

        Returns:
            pd.DataFrame: backtrader格式的數據
        """
        # 篩選特定股票的數據
        symbol_data = data[data["symbol"] == symbol].copy()

        if symbol_data.empty:
            logger.warning("沒有找到股票 %s 的數據", symbol)
            return pd.DataFrame()

        # 設定日期為索引
        symbol_data = symbol_data.set_index("date")

        # 重新排序欄位以符合backtrader要求
        bt_data = symbol_data[["open", "high", "low", "close", "volume"]].copy()

        # 確保數據類型正確
        for col in ["open", "high", "low", "close"]:
            bt_data[col] = pd.to_numeric(bt_data[col], errors="coerce")

        bt_data["volume"] = pd.to_numeric(bt_data["volume"], errors="coerce")

        # 移除缺失值
        bt_data = bt_data.dropna()

        logger.info("已轉換股票 %s 的數據為backtrader格式，共 %d 筆記錄", symbol, len(bt_data))
        return bt_data

    def create_data_feeds(self, data: pd.DataFrame) -> dict:
        """為所有股票創建數據饋送

        Args:
            data: 市場資料

        Returns:
            dict: 股票代碼到數據饋送的映射
        """
        data_feeds = {}

        for symbol in data["symbol"].unique():
            bt_data = self.to_backtrader_format(data, symbol)
            if not bt_data.empty:
                data_feeds[symbol] = bt_data

        logger.info("已創建 %d 個數據饋送", len(data_feeds))
        return data_feeds
