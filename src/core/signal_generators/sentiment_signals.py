"""情緒分析訊號產生器

此模組實現基於新聞情緒和社交媒體情緒的交易訊號生成功能。
"""

import logging
from typing import Optional

import pandas as pd

from .base_signal_generator import BaseSignalGenerator, LOG_MSGS

logger = logging.getLogger(__name__)


class SentimentSignalGenerator(BaseSignalGenerator):
    """情緒分析訊號產生器

    基於新聞情緒和社交媒體情緒生成交易訊號。
    """

    def generate_signals(
        self, sentiment_threshold: float = 0.1, window: int = 7, **kwargs
    ) -> pd.DataFrame:
        """生成新聞情緒策略訊號

        基於新聞情緒分數生成訊號

        Args:
            sentiment_threshold (float): 情緒閾值，超過此值視為正面情緒
            window (int): 移動平均窗口大小
            **kwargs: 其他參數

        Returns:
            pd.DataFrame: 訊號資料，包含 'signal' 列，1 表示買入，-1 表示賣出，0 表示持平
        """
        if not self.validate_data("news"):
            logger.warning(LOG_MSGS["no_news"])
            return pd.DataFrame()

        # 確保新聞資料有 'sentiment' 列
        if "sentiment" not in self.news_data.columns:
            logger.warning(LOG_MSGS["no_sentiment"])
            return pd.DataFrame()

        # 初始化訊號
        signals = pd.DataFrame(index=self.news_data.index)
        signals["signal"] = 0

        # 計算情緒移動平均
        news_data = self.news_data.copy()

        # 對每個股票分別計算
        for stock_id in news_data.index.get_level_values(0).unique():
            stock_sentiment = news_data.loc[stock_id]["sentiment"]

            # 計算移動平均情緒
            sentiment_ma = stock_sentiment.rolling(window=window).mean()

            # 根據情緒生成訊號
            stock_signals = pd.Series(0, index=stock_sentiment.index, dtype=int)

            # 只在有效值時進行比較
            valid_sentiment = ~sentiment_ma.isna()
            buy_condition = valid_sentiment & (sentiment_ma > sentiment_threshold)
            sell_condition = valid_sentiment & (sentiment_ma < -sentiment_threshold)

            stock_signals[buy_condition] = 1  # 正面情緒，買入
            stock_signals[sell_condition] = -1  # 負面情緒，賣出

            # 將股票訊號加入總訊號，使用正確的多層索引
            for date, signal in stock_signals.items():
                if pd.notna(signal):
                    signals.loc[(stock_id, date), "signal"] = int(signal)

        # 儲存訊號
        self.signals["news_sentiment"] = signals

        return signals

    def generate_sentiment_momentum_signals(
        self, short_window: int = 3, long_window: int = 14, **kwargs
    ) -> pd.DataFrame:
        """生成情緒動量訊號

        基於情緒變化趨勢生成訊號

        Args:
            short_window (int): 短期情緒窗口
            long_window (int): 長期情緒窗口
            **kwargs: 其他參數

        Returns:
            pd.DataFrame: 情緒動量訊號
        """
        if not self.validate_data("news"):
            logger.warning(LOG_MSGS["no_news"])
            return pd.DataFrame()

        if "sentiment" not in self.news_data.columns:
            logger.warning(LOG_MSGS["no_sentiment"])
            return pd.DataFrame()

        signals = pd.DataFrame(index=self.news_data.index)
        signals["signal"] = 0

        news_data = self.news_data.copy()

        # 對每個股票分別計算
        for stock_id in news_data.index.get_level_values(0).unique():
            stock_sentiment = news_data.loc[stock_id]["sentiment"]

            # 計算短期和長期情緒移動平均
            short_sentiment_ma = stock_sentiment.rolling(window=short_window).mean()
            long_sentiment_ma = stock_sentiment.rolling(window=long_window).mean()

            # 情緒動量訊號
            stock_signals = pd.Series(0, index=stock_sentiment.index, dtype=int)

            # 只在有效值時進行比較
            valid_short = ~short_sentiment_ma.isna()
            valid_long = ~long_sentiment_ma.isna()
            valid_both = valid_short & valid_long

            # 短期情緒 > 長期情緒，買入訊號
            buy_condition = valid_both & (short_sentiment_ma > long_sentiment_ma)
            stock_signals[buy_condition] = 1

            # 短期情緒 < 長期情緒，賣出訊號
            sell_condition = valid_both & (short_sentiment_ma < long_sentiment_ma)
            stock_signals[sell_condition] = -1

            # 將股票訊號加入總訊號，使用正確的多層索引
            for date, signal in stock_signals.items():
                if pd.notna(signal):
                    signals.loc[(stock_id, date), "signal"] = int(signal)

        # 儲存訊號
        self.signals["sentiment_momentum"] = signals

        return signals

    def generate_sentiment_reversal_signals(
        self, extreme_threshold: float = 0.8, window: int = 5, **kwargs
    ) -> pd.DataFrame:
        """生成情緒反轉訊號

        基於極端情緒的反轉效應生成訊號

        Args:
            extreme_threshold (float): 極端情緒閾值
            window (int): 計算窗口
            **kwargs: 其他參數

        Returns:
            pd.DataFrame: 情緒反轉訊號
        """
        if not self.validate_data("news"):
            logger.warning(LOG_MSGS["no_news"])
            return pd.DataFrame()

        if "sentiment" not in self.news_data.columns:
            logger.warning(LOG_MSGS["no_sentiment"])
            return pd.DataFrame()

        signals = pd.DataFrame(index=self.news_data.index)
        signals["signal"] = 0

        news_data = self.news_data.copy()

        # 對每個股票分別計算
        for stock_id in news_data.index.get_level_values(0).unique():
            stock_sentiment = news_data.loc[stock_id]["sentiment"]

            # 計算情緒移動平均
            sentiment_ma = stock_sentiment.rolling(window=window).mean()

            # 極端情緒反轉訊號
            stock_signals = pd.Series(0, index=stock_sentiment.index)

            # 極端負面情緒，反轉買入
            stock_signals[sentiment_ma < -extreme_threshold] = 1
            # 極端正面情緒，反轉賣出
            stock_signals[sentiment_ma > extreme_threshold] = -1

            signals.loc[stock_id, "signal"] = stock_signals

        # 儲存訊號
        self.signals["sentiment_reversal"] = signals

        return signals

    def generate_news_volume_signals(
        self, volume_threshold: int = 5, sentiment_threshold: float = 0.2, **kwargs
    ) -> pd.DataFrame:
        """生成新聞量情緒訊號

        結合新聞數量和情緒生成訊號

        Args:
            volume_threshold (int): 新聞數量閾值
            sentiment_threshold (float): 情緒閾值
            **kwargs: 其他參數

        Returns:
            pd.DataFrame: 新聞量情緒訊號
        """
        if not self.validate_data("news"):
            logger.warning(LOG_MSGS["no_news"])
            return pd.DataFrame()

        signals = pd.DataFrame(index=self.news_data.index)
        signals["signal"] = 0

        news_data = self.news_data.copy()

        # 對每個股票分別計算
        for stock_id in news_data.index.get_level_values(0).unique():
            stock_news = news_data.loc[stock_id]

            # 按日期分組計算新聞數量和平均情緒
            daily_stats = (
                stock_news.groupby(stock_news.index.date)
                .agg({"sentiment": ["count", "mean"]})
                .fillna(0)
            )

            daily_stats.columns = ["news_count", "avg_sentiment"]

            # 生成訊號條件
            high_volume_positive = (daily_stats["news_count"] >= volume_threshold) & (
                daily_stats["avg_sentiment"] > sentiment_threshold
            )

            high_volume_negative = (daily_stats["news_count"] >= volume_threshold) & (
                daily_stats["avg_sentiment"] < -sentiment_threshold
            )

            # 創建訊號
            stock_signals = pd.Series(0, index=daily_stats.index)
            stock_signals[high_volume_positive] = 1
            stock_signals[high_volume_negative] = -1

            # 將日期索引轉換回原始索引格式
            for date, signal in stock_signals.items():
                mask = stock_news.index.date == date
                if mask.any():
                    signals.loc[(stock_id, stock_news[mask].index[0]), "signal"] = (
                        signal
                    )

        # 儲存訊號
        self.signals["news_volume"] = signals

        return signals

    def generate_topic_sentiment_signals(
        self,
        topic_weights: Optional[dict] = None,
        sentiment_threshold: float = 0.1,
        **kwargs
    ) -> pd.DataFrame:
        """生成主題情緒訊號

        基於不同主題的情緒加權生成訊號

        Args:
            topic_weights (dict, optional): 主題權重字典
            sentiment_threshold (float): 情緒閾值
            **kwargs: 其他參數

        Returns:
            pd.DataFrame: 主題情緒訊號
        """
        if not self.validate_data("news"):
            logger.warning(LOG_MSGS["no_news"])
            return pd.DataFrame()

        # 預設主題權重
        if topic_weights is None:
            topic_weights = {
                "財報": 1.5,
                "併購": 1.2,
                "產品": 1.0,
                "技術": 0.8,
                "市場": 0.9,
                "政策": 1.1,
                "人事": 0.7,
            }

        signals = pd.DataFrame(index=self.news_data.index)
        signals["signal"] = 0

        news_data = self.news_data.copy()

        # 確保有主題和情緒欄位
        required_cols = ["topic", "sentiment"]
        if not all(col in news_data.columns for col in required_cols):
            logger.warning("新聞資料缺少必要欄位: %s", required_cols)
            return signals

        # 對每個股票分別計算
        for stock_id in news_data.index.get_level_values(0).unique():
            stock_news = news_data.loc[stock_id]

            # 計算加權情緒分數
            weighted_sentiment = pd.Series(0.0, index=stock_news.index)

            for topic, weight in topic_weights.items():
                topic_mask = stock_news["topic"] == topic
                if topic_mask.any():
                    weighted_sentiment[topic_mask] = (
                        stock_news.loc[topic_mask, "sentiment"] * weight
                    )

            # 計算移動平均加權情緒
            weighted_sentiment_ma = weighted_sentiment.rolling(window=7).mean()

            # 生成訊號
            stock_signals = pd.Series(0, index=stock_news.index)
            stock_signals[weighted_sentiment_ma > sentiment_threshold] = 1
            stock_signals[weighted_sentiment_ma < -sentiment_threshold] = -1

            signals.loc[stock_id, "signal"] = stock_signals

        # 儲存訊號
        self.signals["topic_sentiment"] = signals

        return signals

    def generate_all_sentiment_signals(self, **kwargs) -> dict:
        """生成所有情緒分析訊號

        Args:
            **kwargs: 各種策略的參數

        Returns:
            dict: 包含所有情緒分析訊號的字典
        """
        signals_dict = {}

        # 生成基本情緒訊號
        signals_dict["news_sentiment"] = self.generate_signals(**kwargs)

        # 生成情緒動量訊號
        signals_dict["sentiment_momentum"] = self.generate_sentiment_momentum_signals(
            **kwargs
        )

        # 生成情緒反轉訊號
        signals_dict["sentiment_reversal"] = self.generate_sentiment_reversal_signals(
            **kwargs
        )

        # 生成新聞量情緒訊號
        signals_dict["news_volume"] = self.generate_news_volume_signals(**kwargs)

        # 生成主題情緒訊號
        signals_dict["topic_sentiment"] = self.generate_topic_sentiment_signals(
            **kwargs
        )

        return signals_dict
