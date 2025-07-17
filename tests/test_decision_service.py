# -*- coding: utf-8 -*-
"""
決策服務測試套件

此模組包含決策服務的單元測試和整合測試。

測試範圍：
- 決策服務基本功能測試
- 決策請求和響應測試
- 決策上下文測試
- 批量決策測試
- 快取機制測試
- 性能統計測試
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

# 導入被測試的模組
from src.services.decision_service import (
    DecisionService,
    DecisionRequest,
    DecisionResponse
)
from src.strategy.llm_integration import (
    LLMStrategyIntegrator,
    DecisionContext,
    AggregatedDecision,
    StrategySignal
)
from src.api.llm_connector import LLMManager
from src.data.market_data import MarketDataProvider
from src.risk.risk_manager import RiskManager


class TestDecisionRequest:
    """決策請求測試"""

    def test_decision_request_creation(self):
        """測試決策請求創建"""
        request = DecisionRequest(
            stock_symbol="AAPL",
            request_time=datetime.now(),
            user_id="test_user",
            request_type="real_time"
        )
        
        assert request.stock_symbol == "AAPL"
        assert request.user_id == "test_user"
        assert request.request_type == "real_time"
        assert isinstance(request.request_time, datetime)

    def test_decision_request_defaults(self):
        """測試決策請求默認值"""
        request = DecisionRequest(
            stock_symbol="TSLA",
            request_time=datetime.now()
        )
        
        assert request.user_id is None
        assert request.request_type == "real_time"
        assert request.parameters is None


class TestDecisionResponse:
    """決策響應測試"""

    def test_decision_response_creation(self):
        """測試決策響應創建"""
        # 創建模擬決策
        mock_decision = AggregatedDecision(
            final_signal=1,
            confidence=0.8,
            contributing_strategies=[],
            risk_assessment={},
            execution_recommendation="建議買入"
        )
        
        response = DecisionResponse(
            request_id="test_123",
            stock_symbol="AAPL",
            decision=mock_decision,
            processing_time=2.5,
            timestamp=datetime.now()
        )
        
        assert response.request_id == "test_123"
        assert response.stock_symbol == "AAPL"
        assert response.decision.final_signal == 1
        assert response.processing_time == 2.5


class TestDecisionService:
    """決策服務測試"""

    def setup_method(self):
        """測試前置設定"""
        # 創建模擬依賴
        self.mock_llm_manager = Mock(spec=LLMManager)
        self.mock_market_data_provider = Mock(spec=MarketDataProvider)
        self.mock_risk_manager = Mock(spec=RiskManager)
        
        # 創建決策服務
        self.decision_service = DecisionService(
            llm_manager=self.mock_llm_manager,
            market_data_provider=self.mock_market_data_provider,
            risk_manager=self.mock_risk_manager,
            config={
                'cache_ttl': 300,
                'max_history_size': 100
            }
        )

    def test_decision_service_initialization(self):
        """測試決策服務初始化"""
        assert self.decision_service.llm_manager is not None
        assert self.decision_service.market_data_provider is not None
        assert self.decision_service.risk_manager is not None
        assert self.decision_service.config['cache_ttl'] == 300

    @pytest.mark.asyncio
    async def test_collect_decision_context(self):
        """測試決策上下文收集"""
        # 設定模擬數據
        mock_market_data = pd.DataFrame({
            '收盤價': [100, 102, 105],
            '成交量': [1000000, 1200000, 1100000]
        })
        
        mock_news_data = pd.DataFrame({
            'news': ['利好消息', '市場分析', '業績預期']
        })
        
        mock_risk_metrics = {
            'volatility': 0.2,
            'beta': 1.1,
            'var': 0.05
        }
        
        # 配置模擬方法
        self.mock_market_data_provider.get_stock_data = AsyncMock(return_value=mock_market_data)
        self.mock_market_data_provider.get_news_data = AsyncMock(return_value=mock_news_data)
        self.mock_risk_manager.calculate_risk_metrics = AsyncMock(return_value=mock_risk_metrics)
        
        # 創建請求
        request = DecisionRequest(
            stock_symbol="AAPL",
            request_time=datetime.now()
        )
        
        # 收集上下文
        context = await self.decision_service._collect_decision_context(request)
        
        assert isinstance(context, DecisionContext)
        assert context.market_data is not None
        assert context.news_data is not None
        assert context.risk_metrics is not None
        assert context.volatility is not None

    def test_calculate_technical_indicators(self):
        """測試技術指標計算"""
        # 創建測試數據
        data = pd.DataFrame({
            '收盤價': [100, 102, 105, 103, 107, 110, 108, 112, 115, 118,
                     120, 118, 122, 125, 123, 127, 130, 128, 132, 135]
        })
        
        indicators = self.decision_service._calculate_technical_indicators(data)
        
        assert 'MA5' in indicators
        assert 'MA10' in indicators
        assert 'MA20' in indicators
        assert 'RSI' in indicators
        assert 'MACD' in indicators
        
        # 檢查指標值的合理性
        assert len(indicators['MA5']) == len(data)
        assert not indicators['RSI'].isna().all()

    def test_analyze_market_sentiment(self):
        """測試市場情緒分析"""
        # 測試上漲趨勢
        upward_data = pd.DataFrame({
            '收盤價': [100, 103, 106, 109, 112]
        })
        sentiment = self.decision_service._analyze_market_sentiment(upward_data, None)
        assert sentiment == "樂觀"
        
        # 測試下跌趨勢
        downward_data = pd.DataFrame({
            '收盤價': [112, 109, 106, 103, 100]
        })
        sentiment = self.decision_service._analyze_market_sentiment(downward_data, None)
        assert sentiment == "悲觀"
        
        # 測試橫盤趨勢
        sideways_data = pd.DataFrame({
            '收盤價': [100, 101, 100, 102, 101]
        })
        sentiment = self.decision_service._analyze_market_sentiment(sideways_data, None)
        assert sentiment == "中性"

    def test_calculate_volatility(self):
        """測試波動率計算"""
        # 創建測試數據
        data = pd.DataFrame({
            '收盤價': np.random.normal(100, 5, 30)  # 平均100，標準差5
        })
        
        volatility = self.decision_service._calculate_volatility(data)
        
        assert isinstance(volatility, float)
        assert volatility > 0
        assert volatility < 2  # 合理的波動率範圍

    def test_apply_risk_control(self):
        """測試風險控制應用"""
        # 創建模擬決策
        decision = AggregatedDecision(
            final_signal=1,
            confidence=0.9,
            contributing_strategies=[],
            risk_assessment={'position_size_recommendation': 0.15},
            execution_recommendation="建議買入"
        )
        
        # 創建高波動率上下文
        context = DecisionContext(
            market_data=pd.DataFrame(),
            volatility=0.5  # 高波動率
        )
        
        # 應用風險控制
        adjusted_decision = self.decision_service._apply_risk_control(decision, context)
        
        # 檢查風險調整
        assert adjusted_decision.confidence < 0.9  # 置信度應該降低
        assert "高波動率" in adjusted_decision.execution_recommendation
        assert adjusted_decision.risk_assessment['position_size_recommendation'] <= 0.1

    def test_cache_mechanism(self):
        """測試快取機制"""
        # 創建模擬響應
        mock_response = DecisionResponse(
            request_id="test_123",
            stock_symbol="AAPL",
            decision=Mock(),
            processing_time=1.0,
            timestamp=datetime.now()
        )
        
        # 測試快取更新
        self.decision_service._update_cache("AAPL", mock_response)
        
        # 測試快取檢查
        cached_response = self.decision_service._check_cache("AAPL")
        assert cached_response is not None
        assert cached_response.stock_symbol == "AAPL"
        
        # 測試快取過期
        # 修改快取時間使其過期
        self.decision_service.decision_cache["AAPL"] = (
            mock_response, 
            datetime.now() - timedelta(seconds=400)  # 超過TTL
        )
        
        expired_response = self.decision_service._check_cache("AAPL")
        assert expired_response is None

    def test_history_management(self):
        """測試歷史管理"""
        # 添加多個響應到歷史
        for i in range(5):
            response = DecisionResponse(
                request_id=f"test_{i}",
                stock_symbol="AAPL",
                decision=Mock(),
                processing_time=1.0,
                timestamp=datetime.now() - timedelta(minutes=i)
            )
            self.decision_service._update_history(response)
        
        # 檢查歷史記錄
        assert len(self.decision_service.decision_history) == 5
        
        # 測試歷史查詢
        history = self.decision_service.get_decision_history(symbol="AAPL", limit=3)
        assert len(history) == 3
        
        # 測試歷史大小限制
        self.decision_service.config['max_history_size'] = 3
        for i in range(5, 10):
            response = DecisionResponse(
                request_id=f"test_{i}",
                stock_symbol="AAPL",
                decision=Mock(),
                processing_time=1.0,
                timestamp=datetime.now()
            )
            self.decision_service._update_history(response)
        
        # 歷史應該被截斷
        assert len(self.decision_service.decision_history) <= 3

    def test_performance_stats_tracking(self):
        """測試性能統計追蹤"""
        initial_stats = self.decision_service.get_performance_stats()
        assert initial_stats['total_requests'] == 0
        assert initial_stats['successful_requests'] == 0
        
        # 模擬處理時間更新
        self.decision_service.performance_stats['total_requests'] = 1
        self.decision_service._update_average_processing_time(2.5)
        
        stats = self.decision_service.get_performance_stats()
        assert stats['average_processing_time'] == 2.5
        
        # 測試多次更新的平均值
        self.decision_service.performance_stats['total_requests'] = 2
        self.decision_service._update_average_processing_time(1.5)
        
        stats = self.decision_service.get_performance_stats()
        assert stats['average_processing_time'] == 2.0  # (2.5 + 1.5) / 2

    def test_generate_request_id(self):
        """測試請求ID生成"""
        request = DecisionRequest(
            stock_symbol="AAPL",
            request_time=datetime(2024, 1, 15, 10, 30, 0)
        )
        
        request_id = self.decision_service._generate_request_id(request)
        
        assert "AAPL" in request_id
        assert "20240115103000" in request_id
        assert len(request_id.split('_')) == 3

    def test_summarize_context(self):
        """測試上下文摘要"""
        context = DecisionContext(
            market_data=pd.DataFrame({'price': [100, 102, 105]}),
            news_data=pd.DataFrame({'news': ['news1', 'news2']}),
            technical_indicators={'RSI': [50, 55, 60]},
            market_sentiment="樂觀",
            volatility=0.2
        )
        
        summary = self.decision_service._summarize_context(context)
        
        assert summary['market_data_points'] == 3
        assert summary['news_data_available'] is True
        assert summary['technical_indicators_count'] == 1
        assert summary['market_sentiment'] == "樂觀"
        assert summary['volatility'] == 0.2

    @pytest.mark.asyncio
    async def test_batch_generate_decisions(self):
        """測試批量決策生成"""
        symbols = ["AAPL", "GOOGL", "MSFT"]
        
        # 模擬generate_decision方法
        async def mock_generate_decision(request):
            return DecisionResponse(
                request_id=f"batch_{request.stock_symbol}",
                stock_symbol=request.stock_symbol,
                decision=Mock(),
                processing_time=1.0,
                timestamp=datetime.now()
            )
        
        with patch.object(self.decision_service, 'generate_decision', side_effect=mock_generate_decision):
            responses = await self.decision_service.batch_generate_decisions(symbols)
        
        assert len(responses) == 3
        assert all(isinstance(r, DecisionResponse) for r in responses)
        assert {r.stock_symbol for r in responses} == set(symbols)


class TestDecisionServiceIntegration:
    """決策服務整合測試"""

    @pytest.mark.asyncio
    async def test_end_to_end_decision_generation(self):
        """測試端到端決策生成"""
        # 創建完整的模擬環境
        mock_llm_manager = Mock(spec=LLMManager)
        mock_market_data_provider = Mock(spec=MarketDataProvider)
        mock_risk_manager = Mock(spec=RiskManager)
        
        # 配置模擬數據
        mock_market_data = pd.DataFrame({
            '收盤價': [100, 102, 105, 103, 107],
            '成交量': [1000000, 1200000, 1100000, 1300000, 1150000]
        })
        
        mock_risk_metrics = {
            'volatility': 0.15,
            'beta': 1.05,
            'var': 0.03
        }
        
        mock_market_data_provider.get_stock_data = AsyncMock(return_value=mock_market_data)
        mock_market_data_provider.get_news_data = AsyncMock(return_value=None)
        mock_risk_manager.calculate_risk_metrics = AsyncMock(return_value=mock_risk_metrics)
        
        # 創建決策服務
        service = DecisionService(
            llm_manager=mock_llm_manager,
            market_data_provider=mock_market_data_provider,
            risk_manager=mock_risk_manager
        )
        
        # 模擬策略整合器
        mock_decision = AggregatedDecision(
            final_signal=1,
            confidence=0.75,
            contributing_strategies=[],
            risk_assessment={'overall_risk': 'medium'},
            execution_recommendation="建議謹慎買入"
        )
        
        with patch.object(service.integrator, 'generate_integrated_decision', return_value=mock_decision):
            request = DecisionRequest(
                stock_symbol="AAPL",
                request_time=datetime.now()
            )
            
            response = await service.generate_decision(request)
        
        assert isinstance(response, DecisionResponse)
        assert response.stock_symbol == "AAPL"
        assert response.decision.final_signal == 1
        assert response.processing_time > 0


class TestDecisionServicePerformance:
    """決策服務性能測試"""

    def setup_method(self):
        """測試前置設定"""
        self.mock_llm_manager = Mock(spec=LLMManager)
        self.mock_market_data_provider = Mock(spec=MarketDataProvider)
        self.mock_risk_manager = Mock(spec=RiskManager)
        
        self.decision_service = DecisionService(
            llm_manager=self.mock_llm_manager,
            market_data_provider=self.mock_market_data_provider,
            risk_manager=self.mock_risk_manager
        )

    def test_cache_performance(self):
        """測試快取性能"""
        import time
        
        # 創建大量快取項目
        start_time = time.time()
        
        for i in range(1000):
            response = DecisionResponse(
                request_id=f"perf_test_{i}",
                stock_symbol=f"STOCK_{i % 100}",  # 100個不同股票
                decision=Mock(),
                processing_time=1.0,
                timestamp=datetime.now()
            )
            self.decision_service._update_cache(f"STOCK_{i % 100}", response)
        
        cache_time = time.time() - start_time
        
        # 測試快取查詢性能
        start_time = time.time()
        
        for i in range(100):
            self.decision_service._check_cache(f"STOCK_{i}")
        
        query_time = time.time() - start_time
        
        # 性能應該在合理範圍內
        assert cache_time < 1.0  # 快取更新應該很快
        assert query_time < 0.1  # 快取查詢應該很快

    def test_memory_usage(self):
        """測試記憶體使用"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # 創建大量歷史記錄
        for i in range(1000):
            response = DecisionResponse(
                request_id=f"memory_test_{i}",
                stock_symbol="AAPL",
                decision=Mock(),
                processing_time=1.0,
                timestamp=datetime.now()
            )
            self.decision_service._update_history(response)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # 記憶體增長應該在合理範圍內
        assert memory_increase < 50 * 1024 * 1024  # 小於50MB


class TestDecisionServiceErrorHandling:
    """決策服務錯誤處理測試"""

    def setup_method(self):
        """測試前置設定"""
        self.mock_llm_manager = Mock(spec=LLMManager)
        self.mock_market_data_provider = Mock(spec=MarketDataProvider)
        self.mock_risk_manager = Mock(spec=RiskManager)
        
        self.decision_service = DecisionService(
            llm_manager=self.mock_llm_manager,
            market_data_provider=self.mock_market_data_provider,
            risk_manager=self.mock_risk_manager
        )

    @pytest.mark.asyncio
    async def test_market_data_error_handling(self):
        """測試市場數據錯誤處理"""
        # 模擬市場數據獲取失敗
        self.mock_market_data_provider.get_stock_data = AsyncMock(
            side_effect=Exception("Market data unavailable")
        )
        
        request = DecisionRequest(
            stock_symbol="AAPL",
            request_time=datetime.now()
        )
        
        with pytest.raises(Exception):
            await self.decision_service.generate_decision(request)

    @pytest.mark.asyncio
    async def test_risk_manager_error_handling(self):
        """測試風險管理器錯誤處理"""
        # 配置正常的市場數據
        self.mock_market_data_provider.get_stock_data = AsyncMock(
            return_value=pd.DataFrame({'收盤價': [100, 102, 105]})
        )
        self.mock_market_data_provider.get_news_data = AsyncMock(return_value=None)
        
        # 模擬風險計算失敗
        self.mock_risk_manager.calculate_risk_metrics = AsyncMock(
            side_effect=Exception("Risk calculation failed")
        )
        
        request = DecisionRequest(
            stock_symbol="AAPL",
            request_time=datetime.now()
        )
        
        with pytest.raises(Exception):
            await self.decision_service.generate_decision(request)

    def test_invalid_request_handling(self):
        """測試無效請求處理"""
        # 測試空股票代碼
        with pytest.raises(Exception):
            request = DecisionRequest(
                stock_symbol="",
                request_time=datetime.now()
            )


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v", "--tb=short"])
