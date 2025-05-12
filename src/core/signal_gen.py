"""
訊號產生模組

此模組負責根據不同的策略生成交易訊號，
包括基本面、動量、均值回歸和新聞情緒等策略。

主要功能：
- 基本面策略訊號生成
- 動量策略訊號生成
- 均值回歸策略訊號生成
- 新聞情緒策略訊號生成
- 多策略訊號合併
"""

import pandas as pd
import logging

# 集中管理 log 訊息，方便多語系擴充
LOG_MSGS = {
    "no_financial": "缺少財務資料，無法生成基本面策略訊號",
    "no_price": "缺少價格資料，無法生成{strategy}策略訊號",
    "no_close": "價格資料缺少 'close' 列",
    "no_news": "缺少新聞資料，無法生成新聞情緒策略訊號",
    "no_sentiment": "新聞資料缺少 'sentiment' 列",
    "no_signal": "沒有可用的訊號，請先生成訊號",
    "unknown_strategy": "權重中包含未知的策略",
    "talib_missing": "未安裝 talib，將使用自定義 RSI 計算，建議安裝 talib 以提升效能與準確度。",
}

# 設定日誌
logger = logging.getLogger("signal_generator")
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class SignalGenerator:
    """訊號產生器類別，用於生成各種交易訊號"""

    def __init__(
        self, price_data=None, volume_data=None, financial_data=None, news_data=None
    ):
        """
        初始化訊號產生器

        Args:
            price_data (pandas.DataFrame, optional): 價格資料，索引為 (股票代號, 日期)
            volume_data (pandas.DataFrame, optional): 成交量資料，索引為 (股票代號, 日期)
            financial_data (pandas.DataFrame, optional): 財務資料，索引為 (股票代號, 日期)
            news_data (pandas.DataFrame, optional): 新聞資料，索引為 (股票代號, 日期)
        """
        self.price_data = price_data
        self.volume_data = volume_data
        self.financial_data = financial_data
        self.news_data = news_data

        # 初始化訊號字典
        self.signals = {}

    def generate_basic(
        self, pe_threshold=15, pb_threshold=1.5, dividend_yield_threshold=3.0
    ):
        """
        生成基本面策略訊號

        基於本益比、股價淨值比和殖利率等基本面指標生成訊號

        Args:
            pe_threshold (float): 本益比閾值，低於此值視為買入訊號
            pb_threshold (float): 股價淨值比閾值，低於此值視為買入訊號
            dividend_yield_threshold (float): 殖利率閾值，高於此值視為買入訊號

        Returns:
            pandas.DataFrame: 訊號資料，包含 'signal' 列，1 表示買入，-1 表示賣出，0 表示持平
        """
        if self.financial_data is None:
            logger.warning(LOG_MSGS["no_financial"])
            return pd.DataFrame()

        # 複製財務資料
        financial_data = self.financial_data.copy()

        # 初始化訊號
        signals = pd.DataFrame(index=financial_data.index)
        signals["signal"] = 0

        # 根據本益比生成訊號
        if "pe_ratio" in financial_data.columns:
            signals.loc[financial_data["pe_ratio"] < pe_threshold, "signal"] += 1
            signals.loc[financial_data["pe_ratio"] > pe_threshold * 2, "signal"] -= 1

        # 根據股價淨值比生成訊號
        if "pb_ratio" in financial_data.columns:
            signals.loc[financial_data["pb_ratio"] < pb_threshold, "signal"] += 1
            signals.loc[financial_data["pb_ratio"] > pb_threshold * 2, "signal"] -= 1

        # 根據殖利率生成訊號
        if "dividend_yield" in financial_data.columns:
            signals.loc[
                financial_data["dividend_yield"] > dividend_yield_threshold, "signal"
            ] += 1
            signals.loc[
                financial_data["dividend_yield"] < dividend_yield_threshold / 2,
                "signal",
            ] -= 1

        # 標準化訊號
        signals["signal"] = signals["signal"].apply(
            lambda x: 1 if x > 0 else (-1 if x < 0 else 0)
        )

        # 儲存訊號
        self.signals["basic"] = signals

        return signals

    def generate_momentum(self, short_window=5, medium_window=20, long_window=60):
        """
        生成動量策略訊號

        基於價格動量、相對強弱指標 (RSI) 和移動平均線等技術指標生成訊號

        Args:
            short_window (int): 短期窗口大小
            medium_window (int): 中期窗口大小
            long_window (int): 長期窗口大小

        Returns:
            pandas.DataFrame: 訊號資料，包含 'signal' 列，1 表示買入，-1 表示賣出，0 表示持平
        """
        if self.price_data is None:
            logger.warning(LOG_MSGS["no_price"].format(strategy="動量"))
            return pd.DataFrame()

        # 確保價格資料有 'close' 列
        if "close" not in self.price_data.columns:
            logger.warning(LOG_MSGS["no_close"])
            return pd.DataFrame()

        # 初始化訊號
        signals = pd.DataFrame(index=self.price_data.index)
        signals["signal"] = 0

        # 計算價格動量
        price_data = self.price_data.copy()

        # 對每個股票分別計算
        for stock_id in price_data.index.get_level_values(0).unique():
            stock_price = price_data.loc[stock_id]["close"]

            # 計算短期、中期和長期移動平均線
            short_ma = stock_price.rolling(window=short_window).mean()
            medium_ma = stock_price.rolling(window=medium_window).mean()
            long_ma = stock_price.rolling(window=long_window).mean()

            # 計算 RSI
            delta = stock_price.diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            # 根據移動平均線交叉生成訊號
            signals.loc[stock_id, "signal"] = 0
            signals.loc[(stock_id, short_ma.index[short_ma > medium_ma]), "signal"] += 1
            signals.loc[(stock_id, short_ma.index[short_ma < medium_ma]), "signal"] -= 1

            # 根據 RSI 生成訊號
            signals.loc[(stock_id, rsi.index[rsi < 30]), "signal"] += 1  # 超賣
            signals.loc[(stock_id, rsi.index[rsi > 70]), "signal"] -= 1  # 超買

        # 標準化訊號
        signals["signal"] = signals["signal"].apply(
            lambda x: 1 if x > 0 else (-1 if x < 0 else 0)
        )

        # 儲存訊號
        self.signals["momentum"] = signals

        return signals

    def generate_reversion(self, window=20, std_dev=2.0):
        """
        生成均值回歸策略訊號

        基於價格偏離移動平均線的程度生成訊號

        Args:
            window (int): 移動平均窗口大小
            std_dev (float): 標準差閾值，價格偏離移動平均線超過此標準差倍數時生成訊號

        Returns:
            pandas.DataFrame: 訊號資料，包含 'signal' 列，1 表示買入，-1 表示賣出，0 表示持平
        """
        if self.price_data is None:
            logger.warning(LOG_MSGS["no_price"].format(strategy="均值回歸"))
            return pd.DataFrame()

        # 確保價格資料有 'close' 列
        if "close" not in self.price_data.columns:
            logger.warning(LOG_MSGS["no_close"])
            return pd.DataFrame()

        # 初始化訊號
        signals = pd.DataFrame(index=self.price_data.index)
        signals["signal"] = 0

        # 計算價格偏離移動平均線的程度
        price_data = self.price_data.copy()

        # 對每個股票分別計算
        for stock_id in price_data.index.get_level_values(0).unique():
            stock_price = price_data.loc[stock_id]["close"]

            # 計算移動平均線
            ma = stock_price.rolling(window=window).mean()

            # 計算價格偏離移動平均線的標準差
            std = stock_price.rolling(window=window).std()

            # 計算 z-score
            z_score = (stock_price - ma) / std

            # 根據 z-score 生成訊號
            signals.loc[(stock_id, z_score.index[z_score < -std_dev]), "signal"] = (
                1  # 價格過低，買入
            )
            signals.loc[(stock_id, z_score.index[z_score > std_dev]), "signal"] = (
                -1
            )  # 價格過高，賣出

        # 儲存訊號
        self.signals["reversion"] = signals

        return signals

    def generate_sentiment(self, sentiment_threshold=0.5):
        """
        生成新聞情緒策略訊號

        基於新聞情緒分析結果生成訊號

        Args:
            sentiment_threshold (float): 情緒閾值，情緒分數高於此值視為正面，低於 -此值 視為負面

        Returns:
            pandas.DataFrame: 訊號資料，包含 'signal' 列，1 表示買入，-1 表示賣出，0 表示持平
        """
        if self.news_data is None:
            logger.warning(LOG_MSGS["no_news"])
            return pd.DataFrame()

        # 確保新聞資料有 'sentiment' 列
        if "sentiment" not in self.news_data.columns:
            logger.warning(LOG_MSGS["no_sentiment"])
            return pd.DataFrame()

        # 初始化訊號
        signals = pd.DataFrame(index=self.news_data.index)
        signals["signal"] = 0

        # 根據情緒分數生成訊號
        signals.loc[self.news_data["sentiment"] > sentiment_threshold, "signal"] = (
            1  # 正面情緒，買入
        )
        signals.loc[self.news_data["sentiment"] < -sentiment_threshold, "signal"] = (
            -1
        )  # 負面情緒，賣出

        # 儲存訊號
        self.signals["sentiment"] = signals

        return signals

    def combine_signals(self, weights=None):
        """
        合併多策略訊號

        Args:
            weights (dict, optional): 各策略權重，如 {'basic': 0.3, 'momentum': 0.3, 'reversion': 0.2, 'sentiment': 0.2}
                                     如果為 None，則使用等權重

        Returns:
            pandas.DataFrame: 合併後的訊號資料，包含 'signal' 列，1 表示買入，-1 表示賣出，0 表示持平
        """
        if not self.signals:
            logger.warning(LOG_MSGS["no_signal"])
            return pd.DataFrame()

        # 如果沒有指定權重，使用等權重
        if weights is None:
            weights = {strategy: 1 / len(self.signals) for strategy in self.signals}

        # 檢查權重是否合法
        if not all(strategy in self.signals for strategy in weights):
            logger.warning(LOG_MSGS["unknown_strategy"])
            return pd.DataFrame()

        # 標準化權重
        total_weight = sum(weights.values())
        weights = {
            strategy: weight / total_weight for strategy, weight in weights.items()
        }

        # 初始化合併訊號
        combined_signals = pd.DataFrame()

        # 合併訊號
        for strategy, weight in weights.items():
            if strategy in self.signals:
                if combined_signals.empty:
                    combined_signals = self.signals[strategy].copy()
                    combined_signals["signal"] *= weight
                else:
                    # 確保索引一致
                    common_index = combined_signals.index.intersection(
                        self.signals[strategy].index
                    )
                    combined_signals = combined_signals.loc[common_index]
                    strategy_signals = self.signals[strategy].loc[common_index]

                    # 加權合併
                    combined_signals["signal"] += strategy_signals["signal"] * weight

        # 標準化訊號
        if not combined_signals.empty:
            # 使用閾值 0.5 和 -0.5 來決定買入和賣出訊號
            combined_signals["signal"] = combined_signals["signal"].apply(
                lambda x: 1 if x > 0.5 else (-1 if x < -0.5 else 0)
            )

        return combined_signals

    def generate_all_signals(self):
        """
        生成所有策略訊號

        Returns:
            dict: 包含所有策略訊號的字典
        """
        self.generate_basic()
        self.generate_momentum()
        self.generate_reversion()
        self.generate_sentiment()

        return self.signals

    def get_signal_stats(self):
        """
        獲取訊號統計資訊

        Returns:
            pandas.DataFrame: 訊號統計資訊
        """
        if not self.signals:
            logger.warning(LOG_MSGS["no_signal"])
            return pd.DataFrame()

        stats = {}

        for strategy, signals in self.signals.items():
            if not signals.empty:
                # 計算買入、賣出和持平訊號的比例
                buy_ratio = (signals["signal"] == 1).mean()
                sell_ratio = (signals["signal"] == -1).mean()
                hold_ratio = (signals["signal"] == 0).mean()

                stats[strategy] = {
                    "buy_ratio": buy_ratio,
                    "sell_ratio": sell_ratio,
                    "hold_ratio": hold_ratio,
                    "signal_count": len(signals),
                }

        return pd.DataFrame(stats).T
