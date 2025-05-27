"""
測試交易指標模組

此測試文件針對 src/core/indicators.py 模組進行全面測試，
包括技術指標、基本面指標和情緒指標的功能測試。

測試覆蓋：
- TechnicalIndicators 類的所有方法
- FundamentalIndicators 類的所有方法
- SentimentIndicators 類的所有方法
- 指標評估和訊號生成功能
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.core.indicators import (
    TechnicalIndicators,
    FundamentalIndicators,
    SentimentIndicators,
    evaluate_indicator_efficacy,
    generate_trading_signals,
)


class TestTechnicalIndicators:
    """技術指標測試類"""

    @pytest.fixture
    def sample_price_data(self):
        """生成示例價格資料"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        np.random.seed(42)

        # 生成模擬股價數據
        base_price = 100
        returns = np.random.normal(0.001, 0.02, 100)
        prices = [base_price]

        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))

        data = pd.DataFrame({
            'open': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, 100)
        }, index=dates)

        return data

    @pytest.fixture
    def tech_indicators(self, sample_price_data):
        """創建技術指標實例"""
        return TechnicalIndicators(sample_price_data)

    def test_calculate_sma(self, tech_indicators):
        """測試簡單移動平均線計算"""
        sma = tech_indicators.calculate_sma(period=20)

        assert isinstance(sma, pd.Series)
        assert len(sma) == len(tech_indicators.price_data)
        assert not sma.isna().all()
        assert "SMA_20" in tech_indicators.indicators_data

    def test_calculate_ema(self, tech_indicators):
        """測試指數移動平均線計算"""
        ema = tech_indicators.calculate_ema(period=20)

        assert isinstance(ema, pd.Series)
        assert len(ema) == len(tech_indicators.price_data)
        assert not ema.isna().all()
        assert "EMA_20" in tech_indicators.indicators_data

    def test_calculate_rsi(self, tech_indicators):
        """測試RSI指標計算"""
        rsi = tech_indicators.calculate_rsi(period=14)

        assert isinstance(rsi, pd.Series)
        assert len(rsi) == len(tech_indicators.price_data)
        assert rsi.min() >= 0
        assert rsi.max() <= 100
        assert "RSI_14" in tech_indicators.indicators_data

    def test_calculate_macd(self, tech_indicators):
        """測試MACD指標計算"""
        macd, signal, hist = tech_indicators.calculate_macd()

        assert isinstance(macd, pd.Series)
        assert isinstance(signal, pd.Series)
        assert isinstance(hist, pd.Series)
        assert len(macd) == len(tech_indicators.price_data)

        # 檢查指標是否已儲存
        assert any("MACD" in key for key in tech_indicators.indicators_data.keys())

    def test_calculate_bollinger_bands(self, tech_indicators):
        """測試布林帶計算"""
        upper, middle, lower = tech_indicators.calculate_bollinger_bands()

        assert isinstance(upper, pd.Series)
        assert isinstance(middle, pd.Series)
        assert isinstance(lower, pd.Series)

        # 檢查布林帶的邏輯關係（排除NaN值）
        valid_mask = ~(upper.isna() | middle.isna() | lower.isna())
        if valid_mask.any():
            assert (upper[valid_mask] >= middle[valid_mask]).all()
            assert (middle[valid_mask] >= lower[valid_mask]).all()

    def test_calculate_obv(self, tech_indicators):
        """測試OBV指標計算"""
        obv = tech_indicators.calculate_obv()

        assert isinstance(obv, pd.Series)
        assert len(obv) == len(tech_indicators.price_data)
        assert "OBV" in tech_indicators.indicators_data

    def test_calculate_atr(self, tech_indicators):
        """測試ATR指標計算"""
        atr = tech_indicators.calculate_atr()

        assert isinstance(atr, pd.Series)
        assert len(atr) == len(tech_indicators.price_data)

        # ATR應該總是非負數（排除NaN值）
        valid_atr = atr.dropna()
        if len(valid_atr) > 0:
            assert (valid_atr >= 0).all()
        assert "ATR_14" in tech_indicators.indicators_data

    def test_standardize_indicators(self, tech_indicators):
        """測試指標標準化"""
        # 先計算一些指標
        tech_indicators.calculate_sma(20)
        tech_indicators.calculate_rsi(14)

        # 測試不同的標準化方法
        for method in ["zscore", "minmax", "robust"]:
            standardized = tech_indicators.standardize_indicators(method=method)
            assert isinstance(standardized, pd.DataFrame)
            assert len(standardized.columns) >= 2

    def test_compare_indicators(self, tech_indicators, sample_price_data):
        """測試指標比較功能"""
        # 先計算一些指標
        tech_indicators.calculate_sma(20)
        tech_indicators.calculate_rsi(14)

        comparison = tech_indicators.compare_indicators(sample_price_data['close'])
        assert isinstance(comparison, pd.DataFrame)

    def test_invalid_data_handling(self):
        """測試無效數據處理"""
        # 測試空數據
        empty_data = pd.DataFrame()
        tech_indicators = TechnicalIndicators(empty_data)

        with pytest.raises(ValueError):
            tech_indicators.calculate_sma()

    def test_missing_columns(self):
        """測試缺少必要欄位的情況"""
        # 創建缺少必要欄位的數據
        incomplete_data = pd.DataFrame({
            'price': [100, 101, 102, 103, 104]
        })

        tech_indicators = TechnicalIndicators(incomplete_data)

        with pytest.raises(ValueError):
            tech_indicators.calculate_sma()


class TestFundamentalIndicators:
    """基本面指標測試類"""

    @pytest.fixture
    def sample_financial_data(self):
        """生成示例財務資料"""
        dates = pd.date_range(start='2023-01-01', periods=12, freq='QE')

        financial_data = {
            'income_statement': pd.DataFrame({
                'EPS': np.random.uniform(1, 5, 12),
                'net_income': np.random.uniform(1000000, 5000000, 12),
            }, index=dates),
            'balance_sheet': pd.DataFrame({
                'BPS': np.random.uniform(10, 50, 12),
                'shareholders_equity': np.random.uniform(10000000, 50000000, 12),
                'total_assets': np.random.uniform(20000000, 100000000, 12),
                'total_liabilities': np.random.uniform(5000000, 30000000, 12),
            }, index=dates),
            'price': pd.DataFrame({
                'close': np.random.uniform(50, 200, 12),
            }, index=dates)
        }

        return financial_data

    @pytest.fixture
    def fund_indicators(self, sample_financial_data):
        """創建基本面指標實例"""
        return FundamentalIndicators(sample_financial_data)

    def test_calculate_eps_growth(self, fund_indicators):
        """測試EPS成長率計算"""
        eps_growth = fund_indicators.calculate_eps_growth()

        assert isinstance(eps_growth, pd.DataFrame)
        assert len(eps_growth.columns) >= 1

        # 檢查是否包含預期的欄位
        expected_cols = ['EPS_growth_1', 'EPS_growth_4', 'EPS_growth_12']
        for col in expected_cols:
            assert col in eps_growth.columns

    def test_calculate_pe_ratio(self, fund_indicators, sample_financial_data):
        """測試P/E比率計算"""
        pe_ratio = fund_indicators.calculate_pe_ratio(sample_financial_data['price'])

        assert isinstance(pe_ratio, pd.Series)
        assert len(pe_ratio) > 0
        assert "PE_ratio" in fund_indicators.indicators_data

    def test_calculate_pb_ratio(self, fund_indicators, sample_financial_data):
        """測試P/B比率計算"""
        pb_ratio = fund_indicators.calculate_pb_ratio(sample_financial_data['price'])

        assert isinstance(pb_ratio, pd.Series)
        assert len(pb_ratio) > 0
        assert "PB_ratio" in fund_indicators.indicators_data

    def test_calculate_roe(self, fund_indicators):
        """測試ROE計算"""
        roe = fund_indicators.calculate_roe()

        assert isinstance(roe, pd.DataFrame)
        assert len(roe.columns) >= 1

        # 檢查ROE值的合理性（ROE可能超過100%，特別是在高槓桿情況下）
        for col in roe.columns:
            valid_values = roe[col].dropna()
            if len(valid_values) > 0:
                # ROE通常在-200%到200%之間是合理的
                assert valid_values.min() >= -2
                assert valid_values.max() <= 2

    def test_calculate_roa(self, fund_indicators):
        """測試ROA計算"""
        roa = fund_indicators.calculate_roa()

        assert isinstance(roa, pd.DataFrame)
        assert len(roa.columns) >= 1

    def test_calculate_debt_ratio(self, fund_indicators):
        """測試負債比率計算"""
        debt_ratio = fund_indicators.calculate_debt_ratio()

        assert isinstance(debt_ratio, pd.Series)
        assert len(debt_ratio) > 0

        # 負債比率通常在0到1之間，但在某些情況下可能超過1（負債超過資產）
        valid_values = debt_ratio.dropna()
        if len(valid_values) > 0:
            assert valid_values.min() >= 0
            # 允許負債比率超過1，但通常不會超過2
            assert valid_values.max() <= 2

    def test_missing_financial_data(self):
        """測試缺少財務資料的情況"""
        incomplete_data = {
            'income_statement': pd.DataFrame({'revenue': [1000, 2000, 3000]})
        }

        fund_indicators = FundamentalIndicators(incomplete_data)

        with pytest.raises(ValueError):
            fund_indicators.calculate_eps_growth()

    def test_empty_financial_data(self):
        """測試空財務資料"""
        empty_data = {
            'income_statement': pd.DataFrame(),
            'balance_sheet': pd.DataFrame()
        }

        fund_indicators = FundamentalIndicators(empty_data)
        result = fund_indicators.calculate_eps_growth()

        assert isinstance(result, pd.DataFrame)
        assert result.empty


class TestSentimentIndicators:
    """情緒指標測試類"""

    @pytest.fixture
    def sample_sentiment_data(self):
        """生成示例情緒資料"""
        dates = pd.date_range(start='2023-01-01', periods=30, freq='D')

        sentiment_data = {
            'news': pd.DataFrame({
                'title': [f'新聞標題 {i}' for i in range(30)],
                'content': [f'新聞內容 {i}' for i in range(30)],
                'sentiment_score': np.random.uniform(-1, 1, 30),
                'topic': np.random.choice(['財報', '產品', '市場', '技術'], 30),
            }, index=dates),
            'social': pd.DataFrame({
                'sentiment_score': np.random.uniform(-1, 1, 30),
            }, index=dates)
        }

        return sentiment_data

    @pytest.fixture
    def sent_indicators(self, sample_sentiment_data):
        """創建情緒指標實例"""
        return SentimentIndicators(sample_sentiment_data)

    def test_calculate_news_sentiment(self, sent_indicators):
        """測試新聞情緒指標計算"""
        news_sentiment = sent_indicators.calculate_news_sentiment()

        assert isinstance(news_sentiment, pd.Series)
        assert len(news_sentiment) > 0
        assert "news_sentiment" in sent_indicators.indicators_data

    def test_calculate_social_sentiment(self, sent_indicators):
        """測試社交媒體情緒指標計算"""
        social_sentiment = sent_indicators.calculate_social_sentiment()

        assert isinstance(social_sentiment, pd.Series)
        assert len(social_sentiment) > 0
        assert "social_sentiment" in sent_indicators.indicators_data

    def test_calculate_topic_sentiment(self, sent_indicators):
        """測試主題情緒指標計算"""
        topic_sentiment = sent_indicators.calculate_topic_sentiment()

        assert isinstance(topic_sentiment, pd.DataFrame)
        assert len(topic_sentiment.columns) > 0

    def test_text_sentiment_calculation(self, sent_indicators):
        """測試從文本計算情緒分數"""
        # 創建沒有情緒分數但有文本的數據
        text_data = {
            'news': pd.DataFrame({
                'title': ['好消息！股價上漲', '壞消息，公司虧損'],
                'content': ['公司獲利創新高', '面臨嚴重財務危機'],
            })
        }

        text_indicators = SentimentIndicators(text_data)
        news_sentiment = text_indicators.calculate_news_sentiment()

        assert isinstance(news_sentiment, pd.Series)
        assert len(news_sentiment) == 2

    def test_topic_extraction(self, sent_indicators):
        """測試主題提取功能"""
        # 創建包含特定主題關鍵字的文本數據
        topic_data = {
            'news': pd.DataFrame({
                'title': ['公司發布財報', '推出新產品', '技術創新突破'],
                'content': ['季報顯示營收成長', '新品上市銷售', '研發專利技術'],
            })
        }

        topic_indicators = SentimentIndicators(topic_data)
        topic_sentiment = topic_indicators.calculate_topic_sentiment()

        assert isinstance(topic_sentiment, pd.DataFrame)

    def test_missing_sentiment_data(self):
        """測試缺少情緒資料的情況"""
        empty_data = {}
        sent_indicators = SentimentIndicators(empty_data)

        with pytest.raises(ValueError):
            sent_indicators.calculate_news_sentiment()

    def test_empty_sentiment_data(self):
        """測試空情緒資料"""
        empty_data = {
            'news': pd.DataFrame()
        }

        sent_indicators = SentimentIndicators(empty_data)
        result = sent_indicators.calculate_news_sentiment()

        assert isinstance(result, pd.Series)
        assert result.empty


class TestIndicatorUtilities:
    """指標工具函數測試類"""

    @pytest.fixture
    def sample_data_for_evaluation(self):
        """生成評估用的示例數據"""
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')

        price_data = pd.DataFrame({
            'close': np.random.uniform(90, 110, 100)
        }, index=dates)

        indicator_data = pd.DataFrame({
            'RSI': np.random.uniform(20, 80, 100),
            'MACD': np.random.uniform(-2, 2, 100),
        }, index=dates)

        return price_data, indicator_data

    def test_evaluate_indicator_efficacy(self, sample_data_for_evaluation):
        """測試指標有效性評估"""
        price_data, indicator_data = sample_data_for_evaluation

        correlation_matrix = evaluate_indicator_efficacy(price_data, indicator_data)

        assert isinstance(correlation_matrix, pd.DataFrame)
        assert correlation_matrix.shape[0] == len(indicator_data.columns)
        assert correlation_matrix.shape[1] >= 1

    def test_generate_trading_signals(self, sample_data_for_evaluation):
        """測試交易訊號生成"""
        price_data, indicator_data = sample_data_for_evaluation

        signal_rules = {
            'RSI': {
                'type': 'threshold',
                'buy_threshold': 30,
                'sell_threshold': 70
            }
        }

        signals = generate_trading_signals(price_data, indicator_data, signal_rules)

        assert isinstance(signals, pd.DataFrame)
        assert 'signal' in signals.columns
        assert signals['signal'].isin([-1, 0, 1]).all()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
