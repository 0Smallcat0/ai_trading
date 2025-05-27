"""回測數據管理模組

此模組負責管理回測相關的數據操作，包括：
- 策略列表管理
- 股票列表管理
- 市場數據載入
- 策略初始化
"""

import logging
from datetime import datetime
from typing import Dict, List

import pandas as pd
import numpy as np

from .backtest_config import BacktestConfig

# 設定日誌
logger = logging.getLogger(__name__)


class BacktestDataManager:
    """回測數據管理器"""

    def __init__(self):
        """初始化數據管理器"""
        self._strategies_cache = None
        self._stocks_cache = None

    def get_available_strategies(self) -> List[Dict]:
        """獲取可用策略列表

        Returns:
            List[Dict]: 策略列表
        """
        if self._strategies_cache is None:
            self._strategies_cache = self._load_strategies()
        return self._strategies_cache

    def get_available_stocks(self) -> List[Dict]:
        """獲取可用股票列表

        Returns:
            List[Dict]: 股票列表
        """
        if self._stocks_cache is None:
            self._stocks_cache = self._load_stocks()
        return self._stocks_cache

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
        # 這裡應該從資料管理服務載入真實資料
        # 目前生成模擬資料
        logger.info("載入市場資料: %s, %s - %s", symbols, start_date, end_date)

        date_range = pd.date_range(start=start_date, end=end_date, freq="D")
        # 只保留工作日
        date_range = date_range[date_range.weekday < 5]

        data_list = []

        for symbol in symbols:
            # 生成模擬價格資料
            np.random.seed(hash(symbol) % 10000)

            # 初始價格
            initial_price = np.random.uniform(50, 500)

            # 生成價格序列
            returns = np.random.normal(0.0005, 0.02, len(date_range))
            prices = [initial_price]

            for ret in returns:
                prices.append(prices[-1] * (1 + ret))

            prices = prices[1:]  # 移除初始價格

            # 生成OHLC資料
            for i, (date, close) in enumerate(zip(date_range, prices)):
                # 生成開高低價
                volatility = 0.02
                high = close * (1 + np.random.uniform(0, volatility))
                low = close * (1 - np.random.uniform(0, volatility))
                open_price = prices[i - 1] if i > 0 else close

                # 生成成交量
                volume = np.random.randint(100000, 10000000)

                data_list.append(
                    {
                        "symbol": symbol,
                        "date": date,
                        "open": open_price,
                        "high": high,
                        "low": low,
                        "close": close,
                        "volume": volume,
                    }
                )

        df = pd.DataFrame(data_list)
        df = df.set_index(["symbol", "date"])

        return df

    def initialize_strategy(self, strategy_id: str, config: BacktestConfig):
        """初始化策略

        Args:
            strategy_id: 策略ID
            config: 回測配置

        Returns:
            策略實例
        """
        logger.info("初始化策略: %s", strategy_id)

        # 這裡應該從策略管理服務載入策略
        # 目前返回模擬策略
        class MockStrategy:
            def __init__(self, strategy_id, config):
                self.strategy_id = strategy_id
                self.config = config

            def generate_signals(self, data):
                # 生成模擬交易信號
                signals_list = []

                for symbol in data.index.get_level_values("symbol").unique():
                    symbol_data = data.xs(symbol, level="symbol")

                    # 簡單的移動平均線交叉策略
                    symbol_data["sma_5"] = symbol_data["close"].rolling(5).mean()
                    symbol_data["sma_20"] = symbol_data["close"].rolling(20).mean()

                    # 生成信號
                    symbol_data["signal"] = 0
                    symbol_data.loc[
                        symbol_data["sma_5"] > symbol_data["sma_20"], "signal"
                    ] = 1
                    symbol_data.loc[
                        symbol_data["sma_5"] < symbol_data["sma_20"], "signal"
                    ] = -1

                    # 添加symbol列
                    symbol_data["symbol"] = symbol
                    symbol_data = symbol_data.reset_index().set_index(
                        ["symbol", "date"]
                    )

                    signals_list.append(symbol_data[["signal"]])

                return pd.concat(signals_list)

        return MockStrategy(strategy_id, config)

    def generate_signals(self, strategy, market_data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信號

        Args:
            strategy: 策略實例
            market_data: 市場資料

        Returns:
            pd.DataFrame: 交易信號
        """
        logger.info("生成交易信號")
        return strategy.generate_signals(market_data)

    def _load_strategies(self) -> List[Dict]:
        """載入策略列表

        Returns:
            List[Dict]: 策略列表
        """
        # 這裡應該從策略管理服務獲取策略列表
        # 目前返回模擬數據
        strategies = [
            {
                "id": "ma_cross",
                "name": "移動平均線交叉策略",
                "type": "技術分析策略",
                "description": "使用短期和長期移動平均線交叉產生交易訊號",
                "parameters": {
                    "short_window": {"type": "int", "default": 5, "min": 1, "max": 50},
                    "long_window": {
                        "type": "int",
                        "default": 20,
                        "min": 10,
                        "max": 200,
                    },
                },
            },
            {
                "id": "rsi_strategy",
                "name": "RSI策略",
                "type": "技術分析策略",
                "description": "使用相對強弱指標(RSI)產生交易訊號",
                "parameters": {
                    "window": {"type": "int", "default": 14, "min": 5, "max": 30},
                    "overbought": {
                        "type": "float",
                        "default": 70,
                        "min": 60,
                        "max": 90,
                    },
                    "oversold": {"type": "float", "default": 30, "min": 10, "max": 40},
                },
            },
            {
                "id": "bollinger_bands",
                "name": "布林通道策略",
                "type": "技術分析策略",
                "description": "使用布林通道產生交易訊號",
                "parameters": {
                    "window": {"type": "int", "default": 20, "min": 10, "max": 50},
                    "num_std": {
                        "type": "float",
                        "default": 2.0,
                        "min": 1.0,
                        "max": 3.0,
                    },
                },
            },
            {
                "id": "macd_strategy",
                "name": "MACD策略",
                "type": "技術分析策略",
                "description": "使用MACD指標產生交易訊號",
                "parameters": {
                    "fast_period": {"type": "int", "default": 12, "min": 5, "max": 20},
                    "slow_period": {"type": "int", "default": 26, "min": 20, "max": 50},
                    "signal_period": {"type": "int", "default": 9, "min": 5, "max": 15},
                },
            },
            {
                "id": "ml_random_forest",
                "name": "隨機森林策略",
                "type": "機器學習策略",
                "description": "使用隨機森林算法預測市場走勢",
                "parameters": {
                    "n_estimators": {
                        "type": "int",
                        "default": 100,
                        "min": 50,
                        "max": 500,
                    },
                    "max_depth": {"type": "int", "default": 5, "min": 3, "max": 20},
                    "min_samples_split": {
                        "type": "int",
                        "default": 2,
                        "min": 2,
                        "max": 10,
                    },
                },
            },
        ]
        return strategies

    def _load_stocks(self) -> List[Dict]:
        """載入股票列表

        Returns:
            List[Dict]: 股票列表
        """
        # 這裡應該從資料管理服務獲取股票列表
        # 目前返回模擬數據
        stocks = [
            {
                "symbol": "2330.TW",
                "name": "台積電",
                "exchange": "TWSE",
                "sector": "半導體",
            },
            {
                "symbol": "2317.TW",
                "name": "鴻海",
                "exchange": "TWSE",
                "sector": "電子零組件",
            },
            {
                "symbol": "2454.TW",
                "name": "聯發科",
                "exchange": "TWSE",
                "sector": "半導體",
            },
            {
                "symbol": "2308.TW",
                "name": "台達電",
                "exchange": "TWSE",
                "sector": "電子零組件",
            },
            {
                "symbol": "2412.TW",
                "name": "中華電",
                "exchange": "TWSE",
                "sector": "電信服務",
            },
            {
                "symbol": "2882.TW",
                "name": "國泰金",
                "exchange": "TWSE",
                "sector": "金融業",
            },
            {
                "symbol": "1301.TW",
                "name": "台塑",
                "exchange": "TWSE",
                "sector": "塑膠工業",
            },
            {
                "symbol": "2881.TW",
                "name": "富邦金",
                "exchange": "TWSE",
                "sector": "金融業",
            },
            {
                "symbol": "2303.TW",
                "name": "聯電",
                "exchange": "TWSE",
                "sector": "半導體",
            },
            {
                "symbol": "1303.TW",
                "name": "南亞",
                "exchange": "TWSE",
                "sector": "塑膠工業",
            },
            {"symbol": "AAPL", "name": "蘋果", "exchange": "NASDAQ", "sector": "科技"},
            {"symbol": "MSFT", "name": "微軟", "exchange": "NASDAQ", "sector": "科技"},
            {
                "symbol": "GOOGL",
                "name": "Alphabet",
                "exchange": "NASDAQ",
                "sector": "科技",
            },
            {
                "symbol": "AMZN",
                "name": "亞馬遜",
                "exchange": "NASDAQ",
                "sector": "電子商務",
            },
            {
                "symbol": "TSLA",
                "name": "特斯拉",
                "exchange": "NASDAQ",
                "sector": "汽車製造",
            },
        ]
        return stocks
