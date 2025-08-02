"""測試訊號產生器模組

此測試文件針對重構後的訊號產生器模組進行全面測試。
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.core.signal_generators import (
    BaseSignalGenerator,
    FundamentalSignalGenerator,
    TechnicalSignalGenerator,
    SentimentSignalGenerator,
    AIModelSignalGenerator,
    SignalCombiner,
    SignalGenerator,
)


class TestBaseSignalGenerator:
    """基礎訊號產生器測試類"""

    @pytest.fixture
    def sample_price_data(self):
        """生成示例價格資料"""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        np.random.seed(42)

        # 創建多層索引 (股票代號, 日期)
        symbols = ["AAPL", "GOOGL", "MSFT"]
        multi_index = pd.MultiIndex.from_product(
            [symbols, dates], names=["symbol", "date"]
        )

        # 生成模擬股價數據
        n_rows = len(multi_index)
        base_prices = {"AAPL": 150, "GOOGL": 2500, "MSFT": 300}

        data = []
        for symbol in symbols:
            base_price = base_prices[symbol]
            returns = np.random.normal(0.001, 0.02, 100)
            prices = [base_price]

            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))

            for i, price in enumerate(prices):
                data.append(
                    {
                        "open": price * (1 + np.random.normal(0, 0.005)),
                        "high": price * (1 + abs(np.random.normal(0, 0.01))),
                        "low": price * (1 - abs(np.random.normal(0, 0.01))),
                        "close": price,
                        "volume": np.random.randint(1000000, 10000000),
                    }
                )

        return pd.DataFrame(data, index=multi_index)

    def test_base_signal_generator_initialization(self, sample_price_data):
        """測試基礎訊號產生器初始化"""

        # 創建一個具體的子類來測試
        class TestSignalGenerator(BaseSignalGenerator):
            def generate_signals(self, **kwargs):
                return pd.DataFrame()

        generator = TestSignalGenerator(price_data=sample_price_data)

        assert generator.price_data is not None
        assert len(generator.signals) == 0
        assert generator.validate_data("price") is True
        assert generator.validate_data("financial") is False

    def test_data_validation(self, sample_price_data):
        """測試數據驗證功能"""

        class TestSignalGenerator(BaseSignalGenerator):
            def generate_signals(self, **kwargs):
                return pd.DataFrame()

        generator = TestSignalGenerator(price_data=sample_price_data)

        assert generator.validate_data("price") is True
        assert generator.validate_data("volume") is False
        assert generator.validate_data("financial") is False
        assert generator.validate_data("news") is False


class TestFundamentalSignalGenerator:
    """基本面訊號產生器測試類"""

    @pytest.fixture
    def sample_financial_data(self):
        """生成示例財務資料"""
        dates = pd.date_range(start="2023-01-01", periods=12, freq="QE")
        symbols = ["AAPL", "GOOGL", "MSFT"]
        multi_index = pd.MultiIndex.from_product(
            [symbols, dates], names=["symbol", "date"]
        )

        data = []
        for _ in range(len(multi_index)):
            data.append(
                {
                    "pe_ratio": np.random.uniform(10, 30),
                    "pb_ratio": np.random.uniform(0.5, 3.0),
                    "dividend_yield": np.random.uniform(0.01, 0.05),
                    "roe": np.random.uniform(0.05, 0.25),
                    "eps_growth": np.random.uniform(-0.1, 0.3),
                    "revenue_growth": np.random.uniform(-0.05, 0.2),
                    "debt_ratio": np.random.uniform(0.1, 0.6),
                    "payout_ratio": np.random.uniform(0.2, 0.8),
                }
            )

        return pd.DataFrame(data, index=multi_index)

    def test_fundamental_signal_generation(self, sample_financial_data):
        """測試基本面訊號生成"""
        generator = FundamentalSignalGenerator(financial_data=sample_financial_data)
        signals = generator.generate_signals()

        assert isinstance(signals, pd.DataFrame)
        assert "signal" in signals.columns
        assert len(signals) > 0
        assert signals["signal"].isin([-1, 0, 1]).all()

    def test_value_signals(self, sample_financial_data):
        """測試價值投資訊號"""
        generator = FundamentalSignalGenerator(financial_data=sample_financial_data)
        signals = generator.generate_value_signals()

        assert isinstance(signals, pd.DataFrame)
        assert "signal" in signals.columns

    def test_growth_signals(self, sample_financial_data):
        """測試成長投資訊號"""
        generator = FundamentalSignalGenerator(financial_data=sample_financial_data)
        signals = generator.generate_growth_signals()

        assert isinstance(signals, pd.DataFrame)
        assert "signal" in signals.columns

    def test_dividend_signals(self, sample_financial_data):
        """測試股息投資訊號"""
        generator = FundamentalSignalGenerator(financial_data=sample_financial_data)
        signals = generator.generate_dividend_signals()

        assert isinstance(signals, pd.DataFrame)
        assert "signal" in signals.columns


class TestTechnicalSignalGenerator:
    """技術分析訊號產生器測試類"""

    @pytest.fixture
    def sample_price_data(self):
        """生成示例價格資料"""
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
        symbols = ["AAPL", "GOOGL"]
        multi_index = pd.MultiIndex.from_product(
            [symbols, dates], names=["symbol", "date"]
        )

        data = []
        for symbol in symbols:
            base_price = 100
            returns = np.random.normal(0.001, 0.02, 100)
            prices = [base_price]

            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))

            for price in prices:
                data.append(
                    {
                        "open": price * (1 + np.random.normal(0, 0.005)),
                        "high": price * (1 + abs(np.random.normal(0, 0.01))),
                        "low": price * (1 - abs(np.random.normal(0, 0.01))),
                        "close": price,
                        "volume": np.random.randint(1000000, 10000000),
                    }
                )

        return pd.DataFrame(data, index=multi_index)

    def test_momentum_signals(self, sample_price_data):
        """測試動量訊號生成"""
        generator = TechnicalSignalGenerator(price_data=sample_price_data)
        signals = generator.generate_signals()

        assert isinstance(signals, pd.DataFrame)
        assert "signal" in signals.columns
        assert signals["signal"].isin([-1, 0, 1]).all()

    def test_mean_reversion_signals(self, sample_price_data):
        """測試均值回歸訊號"""
        generator = TechnicalSignalGenerator(price_data=sample_price_data)
        signals = generator.generate_mean_reversion_signals()

        assert isinstance(signals, pd.DataFrame)
        assert "signal" in signals.columns

    def test_breakout_signals(self, sample_price_data):
        """測試突破訊號"""
        generator = TechnicalSignalGenerator(price_data=sample_price_data)
        signals = generator.generate_breakout_signals()

        assert isinstance(signals, pd.DataFrame)
        assert "signal" in signals.columns

    def test_crossover_signals(self, sample_price_data):
        """測試交叉訊號"""
        generator = TechnicalSignalGenerator(price_data=sample_price_data)
        signals = generator.generate_crossover_signals()

        assert isinstance(signals, pd.DataFrame)
        assert "signal" in signals.columns


class TestSentimentSignalGenerator:
    """情緒分析訊號產生器測試類"""

    @pytest.fixture
    def sample_news_data(self):
        """生成示例新聞資料"""
        dates = pd.date_range(start="2023-01-01", periods=50, freq="D")
        symbols = ["AAPL", "GOOGL"]
        multi_index = pd.MultiIndex.from_product(
            [symbols, dates], names=["symbol", "date"]
        )

        data = []
        topics = ["財報", "產品", "市場", "技術"]

        for _ in range(len(multi_index)):
            data.append(
                {
                    "sentiment": np.random.uniform(-1, 1),
                    "topic": np.random.choice(topics),
                    "title": "測試新聞標題",
                    "content": "測試新聞內容",
                }
            )

        return pd.DataFrame(data, index=multi_index)

    def test_sentiment_signals(self, sample_news_data):
        """測試情緒訊號生成"""
        generator = SentimentSignalGenerator(news_data=sample_news_data)
        signals = generator.generate_signals()

        assert isinstance(signals, pd.DataFrame)
        assert "signal" in signals.columns

    def test_sentiment_momentum_signals(self, sample_news_data):
        """測試情緒動量訊號"""
        generator = SentimentSignalGenerator(news_data=sample_news_data)
        signals = generator.generate_sentiment_momentum_signals()

        assert isinstance(signals, pd.DataFrame)
        assert "signal" in signals.columns

    def test_topic_sentiment_signals(self, sample_news_data):
        """測試主題情緒訊號"""
        generator = SentimentSignalGenerator(news_data=sample_news_data)
        signals = generator.generate_topic_sentiment_signals()

        assert isinstance(signals, pd.DataFrame)
        assert "signal" in signals.columns


class TestSignalCombiner:
    """訊號合併器測試類"""

    @pytest.fixture
    def sample_signals(self):
        """生成示例訊號"""
        dates = pd.date_range(start="2023-01-01", periods=30, freq="D")

        signals1 = pd.DataFrame(
            {
                "signal": np.random.choice([-1, 0, 1], 30),
                "confidence": np.random.uniform(0.5, 1.0, 30),
            },
            index=dates,
        )

        signals2 = pd.DataFrame(
            {
                "signal": np.random.choice([-1, 0, 1], 30),
                "confidence": np.random.uniform(0.5, 1.0, 30),
            },
            index=dates,
        )

        return {"strategy1": signals1, "strategy2": signals2}

    def test_signal_combiner_initialization(self):
        """測試訊號合併器初始化"""
        combiner = SignalCombiner()
        assert len(combiner.signals) == 0
        assert combiner.combined_signals is None

    def test_add_signals(self, sample_signals):
        """測試添加訊號"""
        combiner = SignalCombiner()

        for name, signals in sample_signals.items():
            combiner.add_signals(name, signals)

        assert len(combiner.signals) == 2
        assert "strategy1" in combiner.signals
        assert "strategy2" in combiner.signals

    def test_weighted_average_combination(self, sample_signals):
        """測試加權平均合併"""
        combiner = SignalCombiner()

        for name, signals in sample_signals.items():
            combiner.add_signals(name, signals)

        weights = {"strategy1": 0.6, "strategy2": 0.4}
        combined = combiner.combine_signals(weights=weights, method="weighted_average")

        assert isinstance(combined, pd.DataFrame)
        assert "signal" in combined.columns
        assert "confidence" in combined.columns

    def test_majority_vote_combination(self, sample_signals):
        """測試多數投票合併"""
        combiner = SignalCombiner()

        for name, signals in sample_signals.items():
            combiner.add_signals(name, signals)

        combined = combiner.combine_signals(method="majority_vote")

        assert isinstance(combined, pd.DataFrame)
        assert "signal" in combined.columns

    def test_consensus_combination(self, sample_signals):
        """測試共識合併"""
        combiner = SignalCombiner()

        for name, signals in sample_signals.items():
            combiner.add_signals(name, signals)

        combined = combiner.combine_signals(method="consensus", threshold=0.7)

        assert isinstance(combined, pd.DataFrame)
        assert "signal" in combined.columns


class TestMainSignalGenerator:
    """主要訊號產生器測試類"""

    @pytest.fixture
    def sample_data(self):
        """生成完整的示例數據"""
        dates = pd.date_range(start="2023-01-01", periods=50, freq="D")
        symbols = ["AAPL"]
        multi_index = pd.MultiIndex.from_product(
            [symbols, dates], names=["symbol", "date"]
        )

        # 價格數據
        price_data = pd.DataFrame(
            {
                "open": np.random.uniform(90, 110, len(multi_index)),
                "high": np.random.uniform(95, 115, len(multi_index)),
                "low": np.random.uniform(85, 105, len(multi_index)),
                "close": np.random.uniform(90, 110, len(multi_index)),
                "volume": np.random.randint(1000000, 10000000, len(multi_index)),
            },
            index=multi_index,
        )

        # 財務數據
        financial_data = pd.DataFrame(
            {
                "pe_ratio": np.random.uniform(10, 30, len(multi_index)),
                "pb_ratio": np.random.uniform(0.5, 3.0, len(multi_index)),
                "dividend_yield": np.random.uniform(0.01, 0.05, len(multi_index)),
            },
            index=multi_index,
        )

        # 新聞數據
        news_data = pd.DataFrame(
            {
                "sentiment": np.random.uniform(-1, 1, len(multi_index)),
                "topic": np.random.choice(["財報", "產品"], len(multi_index)),
            },
            index=multi_index,
        )

        return price_data, financial_data, news_data

    def test_main_signal_generator_initialization(self, sample_data):
        """測試主要訊號產生器初始化"""
        price_data, financial_data, news_data = sample_data

        generator = SignalGenerator(
            price_data=price_data, financial_data=financial_data, news_data=news_data
        )

        assert generator.price_data is not None
        assert generator.financial_data is not None
        assert generator.news_data is not None
        assert generator.fundamental_generator is not None
        assert generator.technical_generator is not None
        assert generator.sentiment_generator is not None

    def test_generate_all_signals(self, sample_data):
        """測試生成所有訊號"""
        price_data, financial_data, news_data = sample_data

        generator = SignalGenerator(
            price_data=price_data, financial_data=financial_data, news_data=news_data
        )

        all_signals = generator.generate_all_signals()

        assert isinstance(all_signals, dict)
        assert len(all_signals) > 0

    def test_combine_signals(self, sample_data):
        """測試合併訊號"""
        price_data, financial_data, news_data = sample_data

        generator = SignalGenerator(
            price_data=price_data, financial_data=financial_data, news_data=news_data
        )

        # 先生成一些訊號
        generator.generate_all_signals()

        # 合併訊號
        combined = generator.combine_signals()

        assert isinstance(combined, pd.DataFrame)
        assert "signal" in combined.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
