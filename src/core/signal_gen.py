"""
訊號產生模組

此模組負責根據不同的策略生成交易訊號，
包括基本面、動量、均值回歸和新聞情緒等策略。

主要功能：
- 基本面策略訊號生成
- 動量策略訊號生成
- 均值回歸策略訊號生成
- 新聞情緒策略訊號生成
- AI 模型策略訊號生成
- 多策略訊號合併
- 訊號輸出與回測整合
- 技術指標整合
"""

import logging
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 嘗試導入 indicators 模組
try:
    from src.core.indicators import (
        FundamentalIndicators,
        SentimentIndicators,
        TechnicalIndicators,
    )

    INDICATORS_AVAILABLE = True
except ImportError as e:
    warnings.warn(f"無法匯入 indicators 模組，部分功能將無法使用: {e}")
    INDICATORS_AVAILABLE = False

# 嘗試導入 model_integration 模組
try:
    from src.core.model_integration import ModelManager

    MODEL_INTEGRATION_AVAILABLE = True
except ImportError as e:
    warnings.warn(f"無法匯入 model_integration 模組，AI 模型整合功能將無法使用: {e}")
    MODEL_INTEGRATION_AVAILABLE = False

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
    "indicators_missing": "未安裝 indicators 模組，部分功能將無法使用",
    "no_indicators": "缺少指標資料，無法生成訊號",
    "export_error": "匯出訊號時發生錯誤: {error}",
    "model_integration_missing": "未安裝 model_integration 模組，AI 模型整合功能將無法使用",
    "no_model": "缺少模型，無法生成 AI 模型策略訊號",
    "model_error": "使用模型生成訊號時發生錯誤: {error}",
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
        self,
        price_data=None,
        volume_data=None,
        financial_data=None,
        news_data=None,
        model_manager=None,
    ):
        """
        初始化訊號產生器

        Args:
            price_data (pandas.DataFrame, optional): 價格資料，索引為 (股票代號, 日期)
            volume_data (pandas.DataFrame, optional): 成交量資料，索引為 (股票代號, 日期)
            financial_data (pandas.DataFrame, optional): 財務資料，索引為 (股票代號, 日期)
            news_data (pandas.DataFrame, optional): 新聞資料，索引為 (股票代號, 日期)
            model_manager (ModelManager, optional): 模型管理器，用於 AI 模型整合
        """
        self.price_data = price_data
        self.volume_data = volume_data
        self.financial_data = financial_data
        self.news_data = news_data
        self.model_manager = model_manager

        # 初始化訊號字典
        self.signals = {}

        # 初始化技術指標
        self.tech_indicators = None
        self.fund_indicators = None
        self.sent_indicators = None

        # 初始化指標資料
        self.indicators_data = {}

        # 如果沒有提供模型管理器且模型整合模組可用，則創建一個
        if self.model_manager is None and MODEL_INTEGRATION_AVAILABLE:
            try:
                self.model_manager = ModelManager()
                logger.info("已創建模型管理器")
            except Exception as e:
                logger.warning(f"創建模型管理器失敗: {e}")
                self.model_manager = None

        # 如果有價格資料且 indicators 模組可用，初始化技術指標
        if INDICATORS_AVAILABLE:
            if self.price_data is not None:
                try:
                    self.tech_indicators = TechnicalIndicators(self.price_data)
                except Exception as e:
                    logger.warning(f"初始化技術指標時發生錯誤: {e}")
                    self.tech_indicators = None

            # 如果有財務資料，初始化基本面指標
            if self.financial_data is not None:
                try:
                    self.fund_indicators = FundamentalIndicators(self.financial_data)
                except Exception as e:
                    logger.warning(f"初始化基本面指標時發生錯誤: {e}")
                    self.fund_indicators = None

            # 如果有新聞資料，初始化情緒指標
            if self.news_data is not None:
                try:
                    self.sent_indicators = SentimentIndicators(self.news_data)
                except Exception as e:
                    logger.warning(f"初始化情緒指標時發生錯誤: {e}")
                    self.sent_indicators = None

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

    def generate_ai_model_signals(self, model_name, version=None, signal_threshold=0.5):
        """
        使用 AI 模型生成訊號

        Args:
            model_name (str): 模型名稱
            version (str, optional): 模型版本，如果為 None，則使用最新版本
            signal_threshold (float): 訊號閾值，預測值高於此閾值視為買入訊號，低於 -此閾值 視為賣出訊號

        Returns:
            pandas.DataFrame: 訊號資料，包含 'signal' 列，1 表示買入，-1 表示賣出，0 表示持平
        """
        if self.price_data is None:
            logger.warning(LOG_MSGS["no_price"].format(strategy="AI 模型"))
            return pd.DataFrame()

        if self.model_manager is None:
            if MODEL_INTEGRATION_AVAILABLE:
                try:
                    self.model_manager = ModelManager()
                    logger.info("已創建模型管理器")
                except Exception as e:
                    logger.warning(f"創建模型管理器失敗: {e}")
                    logger.warning(LOG_MSGS["no_model"])
                    return pd.DataFrame()
            else:
                logger.warning(LOG_MSGS["model_integration_missing"])
                return pd.DataFrame()

        try:
            # 準備特徵資料
            features = self._prepare_model_features()

            # 使用模型進行預測
            predictions = self.model_manager.predict(features, model_name, version)

            # 初始化訊號
            signals = pd.DataFrame(index=self.price_data.index)
            signals["signal"] = 0

            # 根據預測結果生成訊號
            if len(predictions) > 0:
                # 對每個股票分別處理
                for stock_id in self.price_data.index.get_level_values(0).unique():
                    stock_indices = (
                        self.price_data.index.get_level_values(0) == stock_id
                    )
                    stock_predictions = (
                        predictions[stock_indices]
                        if len(predictions) == len(self.price_data)
                        else []
                    )

                    if len(stock_predictions) > 0:
                        # 根據預測值生成訊號
                        signals.loc[stock_id, "signal"] = 0

                        # 檢查模型類型
                        model_info = self.model_manager.get_model_info(
                            model_name, version
                        )
                        is_classifier = (
                            model_info.get("model_type", "").lower().find("classifier")
                            >= 0
                        )

                        if is_classifier:
                            # 分類模型，直接使用類別作為訊號
                            signals.loc[
                                (stock_id, self.price_data.loc[stock_id].index),
                                "signal",
                            ] = stock_predictions
                        else:
                            # 回歸模型，使用閾值
                            buy_indices = stock_predictions > signal_threshold
                            sell_indices = stock_predictions < -signal_threshold

                            if any(buy_indices):
                                signals.loc[
                                    (
                                        stock_id,
                                        self.price_data.loc[stock_id].index[
                                            buy_indices
                                        ],
                                    ),
                                    "signal",
                                ] = 1
                            if any(sell_indices):
                                signals.loc[
                                    (
                                        stock_id,
                                        self.price_data.loc[stock_id].index[
                                            sell_indices
                                        ],
                                    ),
                                    "signal",
                                ] = -1

            # 儲存訊號
            self.signals[f"ai_{model_name}"] = signals

            return signals
        except Exception as e:
            logger.error(LOG_MSGS["model_error"].format(error=str(e)))
            return pd.DataFrame()

    def _prepare_model_features(self):
        """
        準備模型特徵

        Returns:
            pandas.DataFrame: 特徵資料
        """
        # 合併所有可用資料
        features = pd.DataFrame(index=self.price_data.index)

        # 添加價格資料
        if self.price_data is not None:
            for col in self.price_data.columns:
                features[f"price_{col}"] = self.price_data[col]

        # 添加成交量資料
        if self.volume_data is not None:
            for col in self.volume_data.columns:
                features[f"volume_{col}"] = self.volume_data[col]

        # 添加財務資料
        if self.financial_data is not None:
            for col in self.financial_data.columns:
                features[f"financial_{col}"] = self.financial_data[col]

        # 添加新聞情緒資料
        if self.news_data is not None and "sentiment" in self.news_data.columns:
            features["news_sentiment"] = self.news_data["sentiment"]

        # 添加技術指標
        if self.tech_indicators is not None:
            indicators_data = self.tech_indicators.calculate_all()
            for col in indicators_data.columns:
                features[f"tech_{col}"] = indicators_data[col]

        # 添加基本面指標
        if self.fund_indicators is not None:
            indicators_data = self.fund_indicators.calculate_all()
            for col in indicators_data.columns:
                features[f"fund_{col}"] = indicators_data[col]

        # 添加情緒指標
        if self.sent_indicators is not None:
            indicators_data = self.sent_indicators.calculate_all()
            for col in indicators_data.columns:
                features[f"sent_{col}"] = indicators_data[col]

        return features

    def generate_all_signals(
        self, include_advanced=True, include_ai=True, ai_models=None
    ):
        """
        生成所有策略訊號

        Args:
            include_advanced (bool): 是否包含進階策略訊號（突破、交叉、背離）
            include_ai (bool): 是否包含 AI 模型策略訊號
            ai_models (list, optional): AI 模型列表，如果為 None，則使用所有可用模型

        Returns:
            dict: 包含所有策略訊號的字典
        """
        # 生成基本策略訊號
        self.generate_basic()
        self.generate_momentum()
        self.generate_reversion()
        self.generate_sentiment()

        # 生成進階策略訊號
        if include_advanced:
            self.generate_breakout_signals()
            self.generate_crossover_signals()
            self.generate_divergence_signals()

            # 如果 indicators 模組可用，使用它生成訊號
            if INDICATORS_AVAILABLE and self.tech_indicators is not None:
                self.generate_with_indicators()

        # 生成 AI 模型策略訊號
        if include_ai and self.model_manager is not None:
            if ai_models is None:
                # 使用所有可用模型
                ai_models = self.model_manager.get_all_models()

            for model_name in ai_models:
                self.generate_ai_model_signals(model_name)

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

    def generate_breakout_signals(self, window=20, threshold_pct=0.02):
        """
        生成突破策略訊號

        基於價格突破前期高點或跌破前期低點生成訊號

        Args:
            window (int): 尋找前期高低點的窗口大小
            threshold_pct (float): 突破閾值百分比，價格超過前期高點或低點此百分比視為有效突破

        Returns:
            pandas.DataFrame: 訊號資料，包含 'signal' 列，1 表示買入，-1 表示賣出，0 表示持平
        """
        if self.price_data is None:
            logger.warning(LOG_MSGS["no_price"].format(strategy="突破"))
            return pd.DataFrame()

        # 確保價格資料有 'close' 列
        if "close" not in self.price_data.columns:
            logger.warning(LOG_MSGS["no_close"])
            return pd.DataFrame()

        # 初始化訊號
        signals = pd.DataFrame(index=self.price_data.index)
        signals["signal"] = 0

        # 計算突破訊號
        price_data = self.price_data.copy()

        # 對每個股票分別計算
        for stock_id in price_data.index.get_level_values(0).unique():
            stock_price = price_data.loc[stock_id]["close"]

            # 計算前期高點和低點
            high_point = stock_price.rolling(window=window).max()
            low_point = stock_price.rolling(window=window).min()

            # 計算突破閾值
            high_threshold = high_point * (1 + threshold_pct)
            low_threshold = low_point * (1 - threshold_pct)

            # 生成突破訊號
            # 價格突破前期高點，買入
            signals.loc[
                (stock_id, stock_price.index[stock_price > high_threshold]), "signal"
            ] = 1
            # 價格跌破前期低點，賣出
            signals.loc[
                (stock_id, stock_price.index[stock_price < low_threshold]), "signal"
            ] = -1

        # 儲存訊號
        self.signals["breakout"] = signals

        return signals

    def generate_crossover_signals(
        self, fast_period=5, slow_period=20, signal_type="ma"
    ):
        """
        生成交叉策略訊號

        基於快線與慢線交叉生成訊號

        Args:
            fast_period (int): 快線週期
            slow_period (int): 慢線週期
            signal_type (str): 訊號類型，可選 'ma'（移動平均線）, 'ema'（指數移動平均線）, 'macd'（MACD）

        Returns:
            pandas.DataFrame: 訊號資料，包含 'signal' 列，1 表示買入，-1 表示賣出，0 表示持平
        """
        if self.price_data is None:
            logger.warning(LOG_MSGS["no_price"].format(strategy="交叉"))
            return pd.DataFrame()

        # 確保價格資料有 'close' 列
        if "close" not in self.price_data.columns:
            logger.warning(LOG_MSGS["no_close"])
            return pd.DataFrame()

        # 初始化訊號
        signals = pd.DataFrame(index=self.price_data.index)
        signals["signal"] = 0

        # 計算交叉訊號
        price_data = self.price_data.copy()

        # 對每個股票分別計算
        for stock_id in price_data.index.get_level_values(0).unique():
            stock_price = price_data.loc[stock_id]["close"]

            if signal_type == "ma":
                # 計算移動平均線
                fast_line = stock_price.rolling(window=fast_period).mean()
                slow_line = stock_price.rolling(window=slow_period).mean()
            elif signal_type == "ema":
                # 計算指數移動平均線
                fast_line = stock_price.ewm(span=fast_period, adjust=False).mean()
                slow_line = stock_price.ewm(span=slow_period, adjust=False).mean()
            elif signal_type == "macd":
                # 計算 MACD
                fast_ema = stock_price.ewm(span=fast_period, adjust=False).mean()
                slow_ema = stock_price.ewm(span=slow_period, adjust=False).mean()
                macd = fast_ema - slow_ema
                signal_line = macd.ewm(span=9, adjust=False).mean()
                fast_line = macd
                slow_line = signal_line
            else:
                logger.warning(f"未知的訊號類型: {signal_type}")
                return pd.DataFrame()

            # 計算交叉
            crossover = (fast_line.shift(1) < slow_line.shift(1)) & (
                fast_line > slow_line
            )
            crossunder = (fast_line.shift(1) > slow_line.shift(1)) & (
                fast_line < slow_line
            )

            # 生成交叉訊號
            signals.loc[(stock_id, stock_price.index[crossover]), "signal"] = (
                1  # 金叉，買入
            )
            signals.loc[(stock_id, stock_price.index[crossunder]), "signal"] = (
                -1
            )  # 死叉，賣出

        # 儲存訊號
        self.signals["crossover"] = signals

        return signals

    def generate_divergence_signals(self, period=14, divergence_window=5):
        """
        生成背離策略訊號

        基於價格與技術指標（如 RSI）之間的背離生成訊號

        Args:
            period (int): RSI 計算週期
            divergence_window (int): 尋找背離的窗口大小

        Returns:
            pandas.DataFrame: 訊號資料，包含 'signal' 列，1 表示買入，-1 表示賣出，0 表示持平
        """
        if self.price_data is None:
            logger.warning(LOG_MSGS["no_price"].format(strategy="背離"))
            return pd.DataFrame()

        # 確保價格資料有 'close' 列
        if "close" not in self.price_data.columns:
            logger.warning(LOG_MSGS["no_close"])
            return pd.DataFrame()

        # 初始化訊號
        signals = pd.DataFrame(index=self.price_data.index)
        signals["signal"] = 0

        # 計算背離訊號
        price_data = self.price_data.copy()

        # 對每個股票分別計算
        for stock_id in price_data.index.get_level_values(0).unique():
            stock_price = price_data.loc[stock_id]["close"]

            # 計算 RSI
            delta = stock_price.diff()
            gain = delta.where(delta > 0, 0).rolling(window=period).mean()
            loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            # 尋找價格高點和低點
            price_highs = pd.Series(False, index=stock_price.index)
            price_lows = pd.Series(False, index=stock_price.index)

            # 尋找 RSI 高點和低點
            rsi_highs = pd.Series(False, index=rsi.index)
            rsi_lows = pd.Series(False, index=rsi.index)

            # 計算價格和 RSI 的高點和低點
            for i in range(divergence_window, len(stock_price)):
                window_price = stock_price.iloc[i - divergence_window : i]
                window_rsi = rsi.iloc[i - divergence_window : i]

                # 檢查是否為價格高點或低點
                if np.argmax(window_price.values) == divergence_window - 1:
                    price_highs.iloc[i] = True
                if np.argmin(window_price.values) == divergence_window - 1:
                    price_lows.iloc[i] = True

                # 檢查是否為 RSI 高點或低點
                if np.argmax(window_rsi.values) == divergence_window - 1:
                    rsi_highs.iloc[i] = True
                if np.argmin(window_rsi.values) == divergence_window - 1:
                    rsi_lows.iloc[i] = True

            # 檢測頂背離（價格創新高但 RSI 未創新高）
            bearish_divergence = price_highs & ~rsi_highs

            # 檢測底背離（價格創新低但 RSI 未創新低）
            bullish_divergence = price_lows & ~rsi_lows

            # 生成背離訊號
            signals.loc[(stock_id, stock_price.index[bullish_divergence]), "signal"] = (
                1  # 底背離，買入
            )
            signals.loc[(stock_id, stock_price.index[bearish_divergence]), "signal"] = (
                -1
            )  # 頂背離，賣出

        # 儲存訊號
        self.signals["divergence"] = signals

        return signals

    def generate_with_indicators(self, signal_rules=None):
        """
        使用 indicators 模組生成訊號

        Args:
            signal_rules (dict, optional): 訊號規則，如果為 None，則使用預設規則

        Returns:
            pandas.DataFrame: 訊號資料，包含 'signal' 列，1 表示買入，-1 表示賣出，0 表示持平
        """
        if not INDICATORS_AVAILABLE:
            logger.warning(LOG_MSGS["indicators_missing"])
            return pd.DataFrame()

        if self.price_data is None:
            logger.warning(LOG_MSGS["no_price"].format(strategy="指標"))
            return pd.DataFrame()

        if self.tech_indicators is None:
            logger.warning("技術指標未初始化，無法生成訊號")
            return pd.DataFrame()

        # 初始化訊號
        signals = pd.DataFrame(index=self.price_data.index)
        signals["signal"] = 0

        # 對每個股票分別計算
        for stock_id in self.price_data.index.get_level_values(0).unique():
            stock_price = self.price_data.loc[stock_id]["close"]

            # 計算 RSI
            delta = stock_price.diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            # 計算 SMA
            sma_20 = stock_price.rolling(window=20).mean()
            sma_50 = stock_price.rolling(window=50).mean()

            # 計算 MACD
            ema_12 = stock_price.ewm(span=12, adjust=False).mean()
            ema_26 = stock_price.ewm(span=26, adjust=False).mean()
            macd = ema_12 - ema_26
            signal_line = macd.ewm(span=9, adjust=False).mean()

            # 生成 RSI 訊號
            signals.loc[(stock_id, rsi.index[rsi < 30]), "signal"] += 1  # 超賣，買入
            signals.loc[(stock_id, rsi.index[rsi > 70]), "signal"] -= 1  # 超買，賣出

            # 生成 SMA 交叉訊號
            crossover = (sma_20.shift(1) < sma_50.shift(1)) & (sma_20 > sma_50)
            crossunder = (sma_20.shift(1) > sma_50.shift(1)) & (sma_20 < sma_50)
            signals.loc[
                (stock_id, sma_20.index[crossover]), "signal"
            ] += 1  # 金叉，買入
            signals.loc[
                (stock_id, sma_20.index[crossunder]), "signal"
            ] -= 1  # 死叉，賣出

            # 生成 MACD 訊號
            macd_crossover = (macd.shift(1) < signal_line.shift(1)) & (
                macd > signal_line
            )
            macd_crossunder = (macd.shift(1) > signal_line.shift(1)) & (
                macd < signal_line
            )
            signals.loc[
                (stock_id, macd.index[macd_crossover]), "signal"
            ] += 1  # 金叉，買入
            signals.loc[
                (stock_id, macd.index[macd_crossunder]), "signal"
            ] -= 1  # 死叉，賣出

        # 標準化訊號
        signals["signal"] = signals["signal"].apply(
            lambda x: 1 if x > 0 else (-1 if x < 0 else 0)
        )

        # 儲存訊號
        self.signals["indicators"] = signals

        return signals

    def export_signals_for_backtest(self, strategy=None, output_format="dataframe"):
        """
        匯出訊號以供回測使用

        Args:
            strategy (str, optional): 要匯出的策略，如果為 None，則匯出合併訊號
            output_format (str): 輸出格式，可選 'dataframe', 'csv', 'json'

        Returns:
            pandas.DataFrame 或 str: 訊號資料或檔案路徑
        """
        if not self.signals:
            logger.warning(LOG_MSGS["no_signal"])
            return pd.DataFrame()

        # 如果沒有指定策略，使用合併訊號
        if strategy is None:
            signals = self.combine_signals()
        elif strategy in self.signals:
            signals = self.signals[strategy]
        else:
            logger.warning(f"未知的策略: {strategy}")
            return pd.DataFrame()

        # 確保訊號資料有正確的格式
        if "signal" not in signals.columns:
            logger.warning("訊號資料缺少 'signal' 列")
            return pd.DataFrame()

        # 轉換訊號格式以符合回測引擎要求
        backtest_signals = signals.copy()

        # 將訊號轉換為 buy_signal 和 sell_signal
        backtest_signals["buy_signal"] = (backtest_signals["signal"] == 1).astype(int)
        backtest_signals["sell_signal"] = (backtest_signals["signal"] == -1).astype(int)

        # 根據輸出格式匯出
        try:
            if output_format == "dataframe":
                return backtest_signals
            elif output_format == "csv":
                file_path = f"signals_{strategy or 'combined'}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
                backtest_signals.to_csv(file_path)
                return file_path
            elif output_format == "json":
                file_path = f"signals_{strategy or 'combined'}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json"
                backtest_signals.to_json(file_path)
                return file_path
            else:
                logger.warning(f"未知的輸出格式: {output_format}")
                return backtest_signals
        except Exception as e:
            logger.error(LOG_MSGS["export_error"].format(error=str(e)))
            return pd.DataFrame()

    def plot_signals(
        self, strategy=None, start_date=None, end_date=None, figsize=(12, 8)
    ):
        """
        繪製訊號圖表

        Args:
            strategy (str, optional): 要繪製的策略，如果為 None，則繪製合併訊號
            start_date (str, optional): 開始日期
            end_date (str, optional): 結束日期
            figsize (tuple): 圖表大小

        Returns:
            matplotlib.figure.Figure: 圖表物件
        """
        if not self.signals:
            logger.warning(LOG_MSGS["no_signal"])
            return None

        # 如果沒有指定策略，使用合併訊號
        if strategy is None:
            signals = self.combine_signals()
            strategy_name = "Combined"
        elif strategy in self.signals:
            signals = self.signals[strategy]
            strategy_name = strategy
        else:
            logger.warning(f"未知的策略: {strategy}")
            return None

        # 確保訊號資料有正確的格式
        if "signal" not in signals.columns:
            logger.warning("訊號資料缺少 'signal' 列")
            return None

        # 如果沒有價格資料，無法繪製圖表
        if self.price_data is None:
            logger.warning(LOG_MSGS["no_price"].format(strategy="圖表"))
            return None

        # 確保價格資料有 'close' 列
        if "close" not in self.price_data.columns:
            logger.warning(LOG_MSGS["no_close"])
            return None

        # 篩選日期範圍
        if start_date is not None or end_date is not None:
            mask = pd.Series(True, index=signals.index)
            if start_date is not None:
                start_date = pd.Timestamp(start_date)
                mask = mask & (signals.index.get_level_values("date") >= start_date)
            if end_date is not None:
                end_date = pd.Timestamp(end_date)
                mask = mask & (signals.index.get_level_values("date") <= end_date)
            signals = signals[mask]

        # 創建圖表
        fig, axes = plt.subplots(
            len(signals.index.get_level_values(0).unique()), 1, figsize=figsize
        )

        # 如果只有一支股票，將 axes 轉換為列表
        if len(signals.index.get_level_values(0).unique()) == 1:
            axes = [axes]

        # 繪製每支股票的訊號
        for i, stock_id in enumerate(signals.index.get_level_values(0).unique()):
            ax = axes[i]

            # 獲取股票價格和訊號
            stock_price = self.price_data.loc[stock_id]["close"]
            stock_signals = signals.loc[stock_id]

            # 繪製價格
            ax.plot(stock_price.index, stock_price.values, label="Price")

            # 繪製買入訊號
            buy_signals = stock_signals[stock_signals["signal"] == 1]
            if not buy_signals.empty:
                ax.scatter(
                    buy_signals.index,
                    stock_price.loc[buy_signals.index],
                    marker="^",
                    color="green",
                    s=100,
                    label="Buy Signal",
                )

            # 繪製賣出訊號
            sell_signals = stock_signals[stock_signals["signal"] == -1]
            if not sell_signals.empty:
                ax.scatter(
                    sell_signals.index,
                    stock_price.loc[sell_signals.index],
                    marker="v",
                    color="red",
                    s=100,
                    label="Sell Signal",
                )

            # 設置圖表標題和標籤
            ax.set_title(f"{stock_id} - {strategy_name} Strategy")
            ax.set_xlabel("Date")
            ax.set_ylabel("Price")
            ax.legend()
            ax.grid(True)

        # 調整佈局
        plt.tight_layout()

        return fig
