"""主要訊號產生器

此模組整合所有訊號產生器，提供統一的介面。
"""

import logging
from typing import Dict, Optional

import pandas as pd

from .base_signal_generator import BaseSignalGenerator
from .fundamental_signals import FundamentalSignalGenerator
from .technical_signals import TechnicalSignalGenerator
from .sentiment_signals import SentimentSignalGenerator
from .ai_model_signals import AIModelSignalGenerator
from .signal_combiner import SignalCombiner

logger = logging.getLogger(__name__)


class SignalGenerator(BaseSignalGenerator):
    """主要訊號產生器

    整合所有類型的訊號產生器，提供統一的介面。
    """

    def __init__(
        self,
        price_data: Optional[pd.DataFrame] = None,
        volume_data: Optional[pd.DataFrame] = None,
        financial_data: Optional[pd.DataFrame] = None,
        news_data: Optional[pd.DataFrame] = None,
        model_manager=None,
    ):
        """初始化主要訊號產生器

        Args:
            price_data (pd.DataFrame, optional): 價格資料
            volume_data (pd.DataFrame, optional): 成交量資料
            financial_data (pd.DataFrame, optional): 財務資料
            news_data (pd.DataFrame, optional): 新聞資料
            model_manager (ModelManager, optional): 模型管理器
        """
        super().__init__(
            price_data, volume_data, financial_data, news_data, model_manager
        )

        # 初始化各種訊號產生器
        self.fundamental_generator = FundamentalSignalGenerator(
            price_data, volume_data, financial_data, news_data, model_manager
        )

        self.technical_generator = TechnicalSignalGenerator(
            price_data, volume_data, financial_data, news_data, model_manager
        )

        self.sentiment_generator = SentimentSignalGenerator(
            price_data, volume_data, financial_data, news_data, model_manager
        )

        self.ai_model_generator = AIModelSignalGenerator(
            price_data, volume_data, financial_data, news_data, model_manager
        )

        # 初始化訊號合併器
        self.signal_combiner = SignalCombiner()

    def generate_signals(self, strategy_type: str = "all", **kwargs) -> pd.DataFrame:
        """生成指定類型的訊號

        Args:
            strategy_type (str): 策略類型 ('fundamental', 'technical', 'sentiment', 'ai', 'all')
            **kwargs: 策略特定的參數

        Returns:
            pd.DataFrame: 生成的訊號

        Raises:
            ValueError: 當策略類型未知時
        """
        if strategy_type == "fundamental":
            return self.fundamental_generator.generate_signals(**kwargs)
        if strategy_type == "technical":
            return self.technical_generator.generate_signals(**kwargs)
        if strategy_type == "sentiment":
            return self.sentiment_generator.generate_signals(**kwargs)
        if strategy_type == "ai":
            return self.ai_model_generator.generate_signals(**kwargs)
        if strategy_type == "all":
            return self.generate_all_signals(**kwargs)
        else:
            raise ValueError(f"未知的策略類型: {strategy_type}")

    def generate_all_signals(self, **kwargs) -> Dict[str, pd.DataFrame]:
        """生成所有類型的訊號

        Args:
            **kwargs: 各種策略的參數

        Returns:
            Dict[str, pd.DataFrame]: 包含所有訊號的字典
        """
        all_signals = {}

        # 生成基本面訊號
        try:
            fundamental_signals = (
                self.fundamental_generator.generate_all_fundamental_signals(**kwargs)
            )
            all_signals.update(fundamental_signals)
            logger.info("基本面訊號生成完成")
        except Exception as e:
            logger.warning("基本面訊號生成失敗: %s", e)

        # 生成技術分析訊號
        try:
            technical_signals = self.technical_generator.generate_all_technical_signals(
                **kwargs
            )
            all_signals.update(technical_signals)
            logger.info("技術分析訊號生成完成")
        except Exception as e:
            logger.warning("技術分析訊號生成失敗: %s", e)

        # 生成情緒分析訊號
        try:
            sentiment_signals = self.sentiment_generator.generate_all_sentiment_signals(
                **kwargs
            )
            all_signals.update(sentiment_signals)
            logger.info("情緒分析訊號生成完成")
        except Exception as e:
            logger.warning("情緒分析訊號生成失敗: %s", e)

        # 生成AI模型訊號
        try:
            ai_signals = self.ai_model_generator.generate_all_ai_signals(**kwargs)
            all_signals.update(ai_signals)
            logger.info("AI模型訊號生成完成")
        except Exception as e:
            logger.warning("AI模型訊號生成失敗: %s", e)

        # 更新內部訊號儲存
        self.signals.update(all_signals)

        return all_signals

    def combine_signals(
        self,
        strategy_weights: Optional[Dict[str, float]] = None,
        combination_method: str = "weighted_average",
        threshold: float = 0.5,
    ) -> pd.DataFrame:
        """合併多種策略訊號

        Args:
            strategy_weights (Dict[str, float], optional): 策略權重
            combination_method (str): 合併方法
            threshold (float): 訊號閾值

        Returns:
            pd.DataFrame: 合併後的訊號
        """
        # 清除之前的訊號
        self.signal_combiner.clear_signals()

        # 添加所有可用的訊號到合併器
        for strategy_name, signals in self.signals.items():
            if not signals.empty:
                self.signal_combiner.add_signals(strategy_name, signals)

        # 合併訊號
        combined_signals = self.signal_combiner.combine_signals(
            weights=strategy_weights, method=combination_method, threshold=threshold
        )

        # 儲存合併後的訊號
        self.signals["combined"] = combined_signals

        return combined_signals

    def generate_fundamental_signals(self, **kwargs) -> Dict[str, pd.DataFrame]:
        """生成基本面訊號

        Args:
            **kwargs: 基本面策略參數

        Returns:
            Dict[str, pd.DataFrame]: 基本面訊號字典
        """
        return self.fundamental_generator.generate_all_fundamental_signals(**kwargs)

    def generate_technical_signals(self, **kwargs) -> Dict[str, pd.DataFrame]:
        """生成技術分析訊號

        Args:
            **kwargs: 技術分析策略參數

        Returns:
            Dict[str, pd.DataFrame]: 技術分析訊號字典
        """
        return self.technical_generator.generate_all_technical_signals(**kwargs)

    def generate_sentiment_signals(self, **kwargs) -> Dict[str, pd.DataFrame]:
        """生成情緒分析訊號

        Args:
            **kwargs: 情緒分析策略參數

        Returns:
            Dict[str, pd.DataFrame]: 情緒分析訊號字典
        """
        return self.sentiment_generator.generate_all_sentiment_signals(**kwargs)

    def generate_ai_model_signals(self, **kwargs) -> Dict[str, pd.DataFrame]:
        """生成AI模型訊號

        Args:
            **kwargs: AI模型策略參數

        Returns:
            Dict[str, pd.DataFrame]: AI模型訊號字典
        """
        return self.ai_model_generator.generate_all_ai_signals(**kwargs)

    def get_signal_statistics(self) -> Dict[str, Dict]:
        """獲取所有訊號的統計資訊

        Returns:
            Dict[str, Dict]: 訊號統計資訊
        """
        statistics = {}

        # 獲取各個產生器的統計資訊
        for strategy_name, signals in self.signals.items():
            if not signals.empty and "signal" in signals.columns:
                signal_counts = signals["signal"].value_counts()

                statistics[strategy_name] = {
                    "total_signals": len(signals),
                    "buy_signals": signal_counts.get(1, 0),
                    "sell_signals": signal_counts.get(-1, 0),
                    "hold_signals": signal_counts.get(0, 0),
                    "buy_ratio": (
                        signal_counts.get(1, 0) / len(signals)
                        if len(signals) > 0
                        else 0
                    ),
                    "sell_ratio": (
                        signal_counts.get(-1, 0) / len(signals)
                        if len(signals) > 0
                        else 0
                    ),
                    "hold_ratio": (
                        signal_counts.get(0, 0) / len(signals)
                        if len(signals) > 0
                        else 0
                    ),
                }

                # 如果有信心度資訊
                if "confidence" in signals.columns:
                    statistics[strategy_name]["avg_confidence"] = signals[
                        "confidence"
                    ].mean()
                    statistics[strategy_name]["max_confidence"] = signals[
                        "confidence"
                    ].max()
                    statistics[strategy_name]["min_confidence"] = signals[
                        "confidence"
                    ].min()

        return statistics

    def export_all_signals(self, base_path: str):
        """匯出所有訊號到檔案

        Args:
            base_path (str): 基礎檔案路徑
        """
        for strategy_name, signals in self.signals.items():
            if not signals.empty:
                file_path = f"{base_path}_{strategy_name}.csv"
                try:
                    signals.to_csv(file_path)
                    logger.info("訊號已匯出: %s -> %s", strategy_name, file_path)
                except Exception as e:
                    logger.error("匯出訊號失敗 %s: %s", strategy_name, e)

    def update_data(
        self,
        price_data: Optional[pd.DataFrame] = None,
        volume_data: Optional[pd.DataFrame] = None,
        financial_data: Optional[pd.DataFrame] = None,
        news_data: Optional[pd.DataFrame] = None,
    ):
        """更新資料

        Args:
            price_data (pd.DataFrame, optional): 新的價格資料
            volume_data (pd.DataFrame, optional): 新的成交量資料
            financial_data (pd.DataFrame, optional): 新的財務資料
            news_data (pd.DataFrame, optional): 新的新聞資料
        """
        if price_data is not None:
            self.price_data = price_data
        if volume_data is not None:
            self.volume_data = volume_data
        if financial_data is not None:
            self.financial_data = financial_data
        if news_data is not None:
            self.news_data = news_data

        # 更新所有子產生器的資料
        for generator in [
            self.fundamental_generator,
            self.technical_generator,
            self.sentiment_generator,
            self.ai_model_generator,
        ]:
            generator.price_data = self.price_data
            generator.volume_data = self.volume_data
            generator.financial_data = self.financial_data
            generator.news_data = self.news_data

        # 重新初始化指標計算器
        self._initialize_indicators()

        logger.info("資料更新完成")

    def get_available_strategies(self) -> list:
        """獲取所有可用的策略名稱

        Returns:
            list: 策略名稱列表
        """
        return list(self.signals.keys())
