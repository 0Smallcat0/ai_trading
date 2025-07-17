# -*- coding: utf-8 -*-
"""
LLM策略測試套件

此模組包含所有LLM策略的單元測試和整合測試。

測試範圍：
- LLM策略基類測試
- FinMem-LLM策略測試
- Stock-chain策略測試
- 新聞分析策略測試
- 策略整合測試
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

# 導入被測試的模組
from src.strategy.llm.base import LLMStrategy, LLMStrategyError, LLMConfigError
from src.strategy.llm.finmem_llm import FinMemLLMStrategy
from src.strategy.llm.stock_chain import StockChainStrategy
from src.strategy.llm.news_analysis import NewsAnalysisStrategy
from src.strategy.llm_integration import LLMStrategyIntegrator, DecisionContext
from src.api.llm_connector import LLMManager, LLMRequest, LLMResponse


class TestLLMStrategyBase:
    """LLM策略基類測試"""

    def setup_method(self):
        """測試前置設定"""
        self.llm_config = {
            'model_name': 'gpt-3.5-turbo',
            'api_key': 'test-api-key'
        }
        self.test_data = self._create_test_data()

    def _create_test_data(self) -> pd.DataFrame:
        """創建測試數據"""
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        data = pd.DataFrame({
            '收盤價': np.random.uniform(100, 200, 30),
            '成交量': np.random.uniform(1000000, 5000000, 30),
            'news': ['測試新聞內容'] * 30
        }, index=dates)
        return data

    def test_llm_strategy_initialization(self):
        """測試LLM策略初始化"""
        # 測試正常初始化
        strategy = FinMemLLMStrategy(
            llm_config=self.llm_config,
            confidence_threshold=0.6
        )
        
        assert strategy.name == "FinMem-LLM策略"
        assert strategy.confidence_threshold == 0.6
        assert strategy.llm_config == self.llm_config

    def test_llm_config_validation(self):
        """測試LLM配置驗證"""
        # 測試缺少必要配置
        with pytest.raises(LLMConfigError):
            FinMemLLMStrategy(llm_config={})
        
        # 測試缺少API金鑰
        with pytest.raises(LLMConfigError):
            FinMemLLMStrategy(llm_config={'model_name': 'gpt-3.5-turbo'})

    def test_price_data_validation(self):
        """測試價格數據驗證"""
        strategy = FinMemLLMStrategy(llm_config=self.llm_config)
        
        # 測試空數據
        empty_data = pd.DataFrame()
        with pytest.raises(LLMStrategyError):
            strategy.generate_signals(empty_data)
        
        # 測試缺少必要欄位的數據
        invalid_data = pd.DataFrame({'volume': [1000, 2000]})
        with pytest.raises(LLMStrategyError):
            strategy.generate_signals(invalid_data)


class TestFinMemLLMStrategy:
    """FinMem-LLM策略測試"""

    def setup_method(self):
        """測試前置設定"""
        self.llm_config = {
            'model_name': 'gpt-3.5-turbo',
            'api_key': 'test-api-key'
        }
        self.strategy = FinMemLLMStrategy(
            llm_config=self.llm_config,
            news_days=5,
            enable_thinking=True
        )
        self.test_data = self._create_test_data_with_news()

    def _create_test_data_with_news(self) -> pd.DataFrame:
        """創建包含新聞的測試數據"""
        dates = pd.date_range(start='2024-01-01', periods=10, freq='D')
        data = pd.DataFrame({
            '收盤價': [100, 102, 105, 103, 107, 110, 108, 112, 115, 118],
            '成交量': np.random.uniform(1000000, 5000000, 10),
            'news': [
                '公司發布利好消息，預期業績增長',
                '市場分析師看好該股票前景',
                '公司簽署重要合作協議',
                '行業政策利好，股價可能上漲',
                '公司財報超預期，營收大幅增長',
                '新產品發布會成功舉行',
                '分析師上調目標價格',
                '公司獲得重要獎項認可',
                '市場情緒樂觀，投資者信心增強',
                '技術突破帶來新的增長機會'
            ],
            'stock_code': ['AAPL'] * 10
        }, index=dates)
        return data

    def test_prepare_llm_input(self):
        """測試LLM輸入準備"""
        llm_input = self.strategy._prepare_llm_input(self.test_data)
        
        assert isinstance(llm_input, str)
        assert '###新聞###' in llm_input
        assert '###任務###' in llm_input
        assert 'AAPL' in llm_input

    def test_format_news_data(self):
        """測試新聞數據格式化"""
        news_section = self.strategy._format_news_data(
            self.test_data, 'AAPL', '2024-01-10'
        )
        
        assert isinstance(news_section, str)
        assert 'AAPL' in news_section
        assert '2024-01-10' in news_section

    def test_extract_prediction(self):
        """測試預測結果提取"""
        # 測試上漲預測
        output_up = "根據分析，我認為股價會[上漲]"
        prediction = self.strategy._extract_prediction(output_up)
        assert prediction == '上漲'
        
        # 測試下跌預測
        output_down = "基於新聞分析，預測[下跌]"
        prediction = self.strategy._extract_prediction(output_down)
        assert prediction == '下跌'
        
        # 測試持平預測
        output_neutral = "市場不確定，建議觀望"
        prediction = self.strategy._extract_prediction(output_neutral)
        assert prediction == '持平'

    def test_calculate_confidence(self):
        """測試置信度計算"""
        # 測試高置信度輸出
        high_conf_output = "明顯的利好消息，確定會上漲"
        thinking = "詳細分析了多個因素，包括財報數據、市場趨勢等"
        confidence = self.strategy._calculate_confidence(high_conf_output, thinking)
        assert confidence > 0.6
        
        # 測試低置信度輸出
        low_conf_output = "可能會上漲，但不確定"
        confidence = self.strategy._calculate_confidence(low_conf_output, "")
        assert confidence < 0.7

    @patch('src.strategy.llm.base.LLMStrategy._call_llm')
    def test_generate_signals(self, mock_llm_call):
        """測試信號生成"""
        # 模擬LLM響應
        mock_llm_call.return_value = "基於新聞分析，預測股價[上漲]，置信度較高"
        
        signals = self.strategy.generate_signals(self.test_data)
        
        assert not signals.empty
        assert 'signal' in signals.columns
        assert 'confidence' in signals.columns
        assert 'reasoning' in signals.columns
        
        # 檢查信號值
        latest_signal = signals.iloc[-1]
        assert latest_signal['signal'] in [-1, 0, 1]
        assert 0 <= latest_signal['confidence'] <= 1


class TestStockChainStrategy:
    """Stock-chain策略測試"""

    def setup_method(self):
        """測試前置設定"""
        self.llm_config = {
            'model_name': 'gpt-4',
            'api_key': 'test-api-key'
        }
        self.strategy = StockChainStrategy(
            llm_config=self.llm_config,
            enable_web_search=True,
            search_topics=['人工智能', '新能源']
        )
        self.test_data = self._create_test_data()

    def _create_test_data(self) -> pd.DataFrame:
        """創建測試數據"""
        dates = pd.date_range(start='2024-01-01', periods=20, freq='D')
        data = pd.DataFrame({
            '收盤價': np.random.uniform(100, 200, 20),
            '成交量': np.random.uniform(1000000, 5000000, 20),
            'MA5': np.random.uniform(95, 205, 20),
            'MA20': np.random.uniform(90, 210, 20),
            'RSI': np.random.uniform(30, 70, 20),
            'news': ['相關新聞內容'] * 20,
            'stock_code': ['TSLA'] * 20
        }, index=dates)
        return data

    def test_format_hot_topics(self):
        """測試熱點話題格式化"""
        topics = self.strategy._format_hot_topics('TSLA')
        
        assert isinstance(topics, str)
        assert '人工智能' in topics
        assert '新能源' in topics

    def test_format_technical_analysis(self):
        """測試技術分析格式化"""
        tech_analysis = self.strategy._format_technical_analysis(self.test_data)
        
        assert isinstance(tech_analysis, str)
        assert '技術指標分析' in tech_analysis
        assert 'RSI' in tech_analysis or 'MA' in tech_analysis

    def test_analyze_sentiment(self):
        """測試情緒分析"""
        # 測試正面新聞
        positive_news = "公司業績大幅增長，股價創新高"
        sentiment = self.strategy._analyze_sentiment(positive_news)
        assert sentiment == '正面'
        
        # 測試負面新聞
        negative_news = "公司面臨調查，股價大幅下跌"
        sentiment = self.strategy._analyze_sentiment(negative_news)
        assert sentiment == '負面'
        
        # 測試中性新聞
        neutral_news = "公司召開例行會議"
        sentiment = self.strategy._analyze_sentiment(neutral_news)
        assert sentiment == '中性'

    def test_extract_stock_chain_prediction(self):
        """測試Stock-chain預測提取"""
        # 測試買入建議
        buy_output = "綜合分析建議[買入]該股票"
        prediction = self.strategy._extract_stock_chain_prediction(buy_output)
        assert prediction == '上漲'
        
        # 測試賣出建議
        sell_output = "風險較高，建議[賣出]"
        prediction = self.strategy._extract_stock_chain_prediction(sell_output)
        assert prediction == '下跌'
        
        # 測試持有建議
        hold_output = "市場不明朗，建議[持有]"
        prediction = self.strategy._extract_stock_chain_prediction(hold_output)
        assert prediction == '持平'


class TestNewsAnalysisStrategy:
    """新聞分析策略測試"""

    def setup_method(self):
        """測試前置設定"""
        self.llm_config = {
            'model_name': 'gpt-3.5-turbo',
            'api_key': 'test-api-key'
        }
        self.strategy = NewsAnalysisStrategy(
            llm_config=self.llm_config,
            max_news_count=10
        )
        self.test_data = self._create_news_data()

    def _create_news_data(self) -> pd.DataFrame:
        """創建新聞測試數據"""
        dates = pd.date_range(start='2024-01-01', periods=5, freq='D')
        news_data = [
            "公司發布Q4財報，營收超預期增長25%",
            "新產品獲得市場積極反響，訂單大幅增加",
            "分析師上調目標價至150美元",
            "公司與知名企業簽署戰略合作協議",
            "CEO在會議上表示對未來發展充滿信心"
        ]
        
        data = pd.DataFrame({
            '收盤價': [100, 105, 108, 112, 115],
            'news': news_data,
            'stock_code': ['AAPL'] * 5
        }, index=dates)
        return data

    def test_analyze_news_sentiment(self):
        """測試新聞情緒分析"""
        # 測試正面新聞
        positive_news = "公司業績大幅增長，利好消息不斷"
        sentiment = self.strategy._analyze_news_sentiment(positive_news)
        assert sentiment > 0
        
        # 測試負面新聞
        negative_news = "公司面臨虧損風險，股價下跌"
        sentiment = self.strategy._analyze_news_sentiment(negative_news)
        assert sentiment < 0
        
        # 測試中性新聞
        neutral_news = "公司召開股東大會"
        sentiment = self.strategy._analyze_news_sentiment(neutral_news)
        assert sentiment == 0

    def test_analyze_news_importance(self):
        """測試新聞重要性分析"""
        # 測試高重要性新聞
        important_news = "AAPL公司發布財報，業績超預期"
        importance = self.strategy._analyze_news_importance(important_news, 'AAPL')
        assert importance > 0.5
        
        # 測試低重要性新聞
        unimportant_news = "公司員工參加慈善活動"
        importance = self.strategy._analyze_news_importance(unimportant_news, 'AAPL')
        assert importance < 0.8

    def test_calculate_time_weight(self):
        """測試時間權重計算"""
        # 測試最新新聞
        recent_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        weight = self.strategy._calculate_time_weight(recent_timestamp)
        assert weight > 0.8
        
        # 測試較舊新聞
        old_timestamp = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S')
        weight = self.strategy._calculate_time_weight(old_timestamp)
        assert weight < 0.8


class TestLLMStrategyIntegrator:
    """LLM策略整合器測試"""

    def setup_method(self):
        """測試前置設定"""
        self.mock_llm_manager = Mock(spec=LLMManager)
        self.integrator = LLMStrategyIntegrator(
            llm_manager=self.mock_llm_manager,
            integration_config={
                'strategy_weights': {
                    'llm_weight': 0.5,
                    'technical_weight': 0.3,
                    'fundamental_weight': 0.2
                },
                'decision_threshold': 0.6
            }
        )

    def test_weighted_average_aggregation(self):
        """測試加權平均聚合"""
        from src.strategy.llm_integration import StrategySignal
        
        signals = [
            StrategySignal("策略1", 1, 0.8, "買入信號", {"strategy_type": "llm"}),
            StrategySignal("策略2", -1, 0.6, "賣出信號", {"strategy_type": "technical"}),
            StrategySignal("策略3", 1, 0.7, "買入信號", {"strategy_type": "llm"})
        ]
        
        result = self.integrator._weighted_average_aggregation(signals)
        assert result in [-1, 0, 1]

    def test_majority_vote_aggregation(self):
        """測試多數投票聚合"""
        from src.strategy.llm_integration import StrategySignal
        
        signals = [
            StrategySignal("策略1", 1, 0.8, "買入信號"),
            StrategySignal("策略2", 1, 0.6, "買入信號"),
            StrategySignal("策略3", -1, 0.7, "賣出信號")
        ]
        
        result = self.integrator._majority_vote_aggregation(signals)
        assert result == 1  # 多數買入

    def test_calculate_overall_confidence(self):
        """測試整體置信度計算"""
        from src.strategy.llm_integration import StrategySignal
        
        signals = [
            StrategySignal("策略1", 1, 0.8, "買入信號"),
            StrategySignal("策略2", 1, 0.6, "買入信號"),
            StrategySignal("策略3", 1, 0.9, "買入信號")
        ]
        
        confidence = self.integrator._calculate_overall_confidence(signals)
        assert 0 <= confidence <= 1
        assert confidence > 0.6  # 應該是高置信度


class TestLLMIntegration:
    """LLM整合測試"""

    @pytest.fixture
    def mock_llm_manager(self):
        """模擬LLM管理器"""
        manager = Mock(spec=LLMManager)
        manager.generate = AsyncMock(return_value=LLMResponse(
            content="測試響應",
            model="gpt-3.5-turbo",
            usage={'total_tokens': 100},
            finish_reason='stop',
            response_time=1.0,
            provider='openai'
        ))
        return manager

    @pytest.mark.asyncio
    async def test_decision_context_creation(self):
        """測試決策上下文創建"""
        # 創建測試數據
        market_data = pd.DataFrame({
            '收盤價': [100, 102, 105],
            '成交量': [1000000, 1200000, 1100000]
        })
        
        context = DecisionContext(
            market_data=market_data,
            market_sentiment="樂觀",
            volatility=0.2
        )
        
        assert context.market_data is not None
        assert context.market_sentiment == "樂觀"
        assert context.volatility == 0.2

    def test_strategy_signal_creation(self):
        """測試策略信號創建"""
        from src.strategy.llm_integration import StrategySignal
        
        signal = StrategySignal(
            strategy_name="測試策略",
            signal=1,
            confidence=0.8,
            reasoning="測試推理",
            metadata={"test": "data"}
        )
        
        assert signal.strategy_name == "測試策略"
        assert signal.signal == 1
        assert signal.confidence == 0.8
        assert signal.reasoning == "測試推理"
        assert signal.metadata["test"] == "data"


# 性能測試
class TestLLMPerformance:
    """LLM性能測試"""

    def test_strategy_execution_time(self):
        """測試策略執行時間"""
        import time
        
        llm_config = {
            'model_name': 'gpt-3.5-turbo',
            'api_key': 'test-api-key'
        }
        strategy = FinMemLLMStrategy(llm_config=llm_config)
        
        # 創建大量測試數據
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        data = pd.DataFrame({
            '收盤價': np.random.uniform(100, 200, 100),
            'news': ['測試新聞'] * 100
        }, index=dates)
        
        start_time = time.time()
        
        # 模擬LLM調用
        with patch.object(strategy, '_call_llm', return_value="測試響應[上漲]"):
            signals = strategy.generate_signals(data)
        
        execution_time = time.time() - start_time
        
        # 執行時間應該在合理範圍內（小於5秒）
        assert execution_time < 5.0
        assert not signals.empty

    def test_memory_usage(self):
        """測試記憶體使用"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # 創建多個策略實例
        strategies = []
        for i in range(10):
            llm_config = {
                'model_name': 'gpt-3.5-turbo',
                'api_key': f'test-api-key-{i}'
            }
            strategy = FinMemLLMStrategy(llm_config=llm_config)
            strategies.append(strategy)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # 記憶體增長應該在合理範圍內（小於100MB）
        assert memory_increase < 100 * 1024 * 1024


# 錯誤處理測試
class TestLLMErrorHandling:
    """LLM錯誤處理測試"""

    def test_invalid_llm_response(self):
        """測試無效LLM響應處理"""
        llm_config = {
            'model_name': 'gpt-3.5-turbo',
            'api_key': 'test-api-key'
        }
        strategy = FinMemLLMStrategy(llm_config=llm_config)
        
        # 測試空響應
        with patch.object(strategy, '_call_llm', return_value=""):
            result = strategy._parse_llm_output("")
            assert result['prediction'] == '持平'
            assert result['confidence'] == 0.0

    def test_network_error_handling(self):
        """測試網路錯誤處理"""
        llm_config = {
            'model_name': 'gpt-3.5-turbo',
            'api_key': 'test-api-key'
        }
        strategy = FinMemLLMStrategy(llm_config=llm_config)
        
        # 模擬網路錯誤
        with patch.object(strategy, '_call_llm', side_effect=Exception("Network error")):
            data = pd.DataFrame({
                '收盤價': [100, 102],
                'news': ['測試新聞'] * 2
            })
            
            with pytest.raises(LLMStrategyError):
                strategy.generate_signals(data)


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v", "--tb=short"])
