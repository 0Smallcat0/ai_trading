# -*- coding: utf-8 -*-
"""
LLM連接器測試套件

此模組包含LLM API連接器的單元測試和整合測試。

測試範圍：
- LLM連接器基類測試
- OpenAI連接器測試
- Claude連接器測試
- 本地LLM連接器測試
- LLM管理器測試
- 錯誤處理測試
- 速率限制測試
- 成本控制測試
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# 導入被測試的模組
from src.api.llm_connector import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    LLMConnectorError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMQuotaExceededError,
    OpenAIConnector,
    ClaudeConnector,
    LocalLLMConnector,
    LLMConnectorFactory,
    LLMManager
)
from src.api.rate_limiting import (
    RateLimiter,
    CostController,
    TokenBucket,
    SlidingWindowCounter,
    RateLimit,
    CostBudget,
    LimitType,
    PriorityLevel
)
from src.api.error_handling import (
    ErrorClassifier,
    RetryHandler,
    CircuitBreaker,
    ErrorTracker,
    RetryConfig,
    CircuitBreakerConfig
)


class TestLLMRequest:
    """LLM請求測試"""

    def test_llm_request_creation(self):
        """測試LLM請求創建"""
        request = LLMRequest(
            prompt="測試提示詞",
            model="gpt-3.5-turbo",
            max_tokens=1000,
            temperature=0.7
        )
        
        assert request.prompt == "測試提示詞"
        assert request.model == "gpt-3.5-turbo"
        assert request.max_tokens == 1000
        assert request.temperature == 0.7

    def test_llm_request_defaults(self):
        """測試LLM請求默認值"""
        request = LLMRequest(
            prompt="測試提示詞",
            model="gpt-3.5-turbo"
        )
        
        assert request.max_tokens == 2000
        assert request.temperature == 0.7
        assert request.top_p == 1.0
        assert request.stream is False


class TestLLMResponse:
    """LLM響應測試"""

    def test_llm_response_creation(self):
        """測試LLM響應創建"""
        response = LLMResponse(
            content="測試響應內容",
            model="gpt-3.5-turbo",
            usage={'total_tokens': 100},
            finish_reason='stop',
            response_time=1.5,
            provider='openai'
        )
        
        assert response.content == "測試響應內容"
        assert response.model == "gpt-3.5-turbo"
        assert response.usage['total_tokens'] == 100
        assert response.finish_reason == 'stop'
        assert response.response_time == 1.5
        assert response.provider == 'openai'


class TestOpenAIConnector:
    """OpenAI連接器測試"""

    def setup_method(self):
        """測試前置設定"""
        self.connector = OpenAIConnector(
            api_key="sk-test-key",
            timeout=30,
            max_retries=3
        )

    def test_openai_connector_initialization(self):
        """測試OpenAI連接器初始化"""
        assert self.connector.api_key == "sk-test-key"
        assert self.connector.timeout == 30
        assert self.connector.max_retries == 3
        assert self.connector.get_provider() == LLMProvider.OPENAI

    def test_openai_config_validation(self):
        """測試OpenAI配置驗證"""
        # 有效配置
        assert self.connector.validate_config() is True
        
        # 無效API金鑰
        invalid_connector = OpenAIConnector(api_key="invalid-key")
        assert invalid_connector.validate_config() is False

    @pytest.mark.asyncio
    async def test_openai_generate_mock(self):
        """測試OpenAI生成（模擬）"""
        request = LLMRequest(
            prompt="測試提示詞",
            model="gpt-3.5-turbo"
        )
        
        response = await self.connector.generate(request)
        
        assert isinstance(response, LLMResponse)
        assert response.provider == "openai"
        assert response.model == "gpt-3.5-turbo"
        assert response.content is not None

    def test_openai_stats_tracking(self):
        """測試OpenAI統計追蹤"""
        initial_stats = self.connector.get_stats()
        assert initial_stats['total_requests'] == 0
        assert initial_stats['successful_requests'] == 0
        
        # 重置統計
        self.connector.reset_stats()
        stats = self.connector.get_stats()
        assert stats['total_requests'] == 0


class TestClaudeConnector:
    """Claude連接器測試"""

    def setup_method(self):
        """測試前置設定"""
        self.connector = ClaudeConnector(
            api_key="claude-test-key",
            timeout=30
        )

    def test_claude_connector_initialization(self):
        """測試Claude連接器初始化"""
        assert self.connector.api_key == "claude-test-key"
        assert self.connector.get_provider() == LLMProvider.CLAUDE

    def test_claude_config_validation(self):
        """測試Claude配置驗證"""
        assert self.connector.validate_config() is True
        
        # 空API金鑰
        empty_connector = ClaudeConnector(api_key="")
        assert empty_connector.validate_config() is False

    @pytest.mark.asyncio
    async def test_claude_generate_mock(self):
        """測試Claude生成（模擬）"""
        request = LLMRequest(
            prompt="測試提示詞",
            model="claude-3-haiku"
        )
        
        response = await self.connector.generate(request)
        
        assert isinstance(response, LLMResponse)
        assert response.provider == "claude"
        assert response.model == "claude-3-haiku"


class TestLocalLLMConnector:
    """本地LLM連接器測試"""

    def setup_method(self):
        """測試前置設定"""
        self.connector = LocalLLMConnector(
            base_url="http://localhost:8000"
        )

    def test_local_connector_initialization(self):
        """測試本地連接器初始化"""
        assert self.connector.base_url == "http://localhost:8000"
        assert self.connector.get_provider() == LLMProvider.LOCAL

    def test_local_config_validation(self):
        """測試本地配置驗證"""
        assert self.connector.validate_config() is True
        
        # 無效URL
        invalid_connector = LocalLLMConnector(base_url="")
        assert invalid_connector.validate_config() is False

    @pytest.mark.asyncio
    async def test_local_generate_mock(self):
        """測試本地生成（模擬）"""
        request = LLMRequest(
            prompt="測試提示詞",
            model="qwen-7b"
        )
        
        response = await self.connector.generate(request)
        
        assert isinstance(response, LLMResponse)
        assert response.provider == "local"


class TestLLMConnectorFactory:
    """LLM連接器工廠測試"""

    def test_create_openai_connector(self):
        """測試創建OpenAI連接器"""
        connector = LLMConnectorFactory.create_connector(
            provider="openai",
            api_key="sk-test-key"
        )
        
        assert isinstance(connector, OpenAIConnector)
        assert connector.get_provider() == LLMProvider.OPENAI

    def test_create_claude_connector(self):
        """測試創建Claude連接器"""
        connector = LLMConnectorFactory.create_connector(
            provider="claude",
            api_key="claude-test-key"
        )
        
        assert isinstance(connector, ClaudeConnector)
        assert connector.get_provider() == LLMProvider.CLAUDE

    def test_create_local_connector(self):
        """測試創建本地連接器"""
        connector = LLMConnectorFactory.create_connector(
            provider="local",
            api_key="local"
        )
        
        assert isinstance(connector, LocalLLMConnector)
        assert connector.get_provider() == LLMProvider.LOCAL

    def test_invalid_provider(self):
        """測試無效提供商"""
        with pytest.raises(ValueError):
            LLMConnectorFactory.create_connector(
                provider="invalid",
                api_key="test-key"
            )


class TestLLMManager:
    """LLM管理器測試"""

    def setup_method(self):
        """測試前置設定"""
        self.config = {
            'providers': {
                'openai': {
                    'enabled': True,
                    'api_key': 'sk-test-key',
                    'timeout': 30
                },
                'claude': {
                    'enabled': False,
                    'api_key': 'claude-test-key'
                }
            },
            'rate_limit': {
                'max_requests': 60,
                'time_window': 60
            },
            'cost_control': {
                'daily_limit': 50.0
            }
        }
        self.manager = LLMManager(self.config)

    def test_llm_manager_initialization(self):
        """測試LLM管理器初始化"""
        assert len(self.manager.connectors) >= 1  # 至少有OpenAI連接器
        assert 'openai' in self.manager.connectors

    @pytest.mark.asyncio
    async def test_llm_manager_generate(self):
        """測試LLM管理器生成"""
        response = await self.manager.generate(
            prompt="測試提示詞",
            provider="openai",
            model="gpt-3.5-turbo"
        )
        
        assert isinstance(response, LLMResponse)
        assert response.provider == "openai"

    def test_llm_manager_status(self):
        """測試LLM管理器狀態"""
        status = self.manager.get_status()
        
        assert 'connectors' in status
        assert 'costs' in status
        assert 'rate_limit' in status


class TestRateLimiting:
    """速率限制測試"""

    def test_token_bucket(self):
        """測試令牌桶"""
        bucket = TokenBucket(capacity=10, refill_rate=1)
        
        # 測試消費令牌
        assert bucket.consume(5) is True
        assert bucket.consume(6) is False  # 超過容量
        
        # 測試等待時間
        wait_time = bucket.wait_time(6)
        assert wait_time > 0

    def test_sliding_window_counter(self):
        """測試滑動窗口計數器"""
        window = SlidingWindowCounter(window_size=60, bucket_count=6)
        
        # 添加計數
        window.add(5)
        window.add(3)
        
        # 獲取總計數
        count = window.get_count()
        assert count == 8
        
        # 獲取速率
        rate = window.get_rate()
        assert rate > 0

    @pytest.mark.asyncio
    async def test_rate_limiter(self):
        """測試速率限制器"""
        limits = [
            RateLimit(
                limit_type=LimitType.REQUESTS_PER_SECOND,
                limit_value=2,
                window_size=1
            )
        ]
        
        limiter = RateLimiter(limits)
        
        # 正常請求
        await limiter.acquire(request_count=1)
        
        # 超過限制的請求
        with pytest.raises(Exception):  # 可能是RateLimitExceededError或等待
            await limiter.acquire(request_count=5)

    def test_cost_controller(self):
        """測試成本控制器"""
        budget = CostBudget(
            daily_budget=10.0,
            monthly_budget=100.0
        )
        
        controller = CostController(budget)
        
        # 正常成本檢查
        controller.check_budget(5.0)
        
        # 記錄使用
        controller.record_usage(5.0)
        
        # 超出預算檢查
        with pytest.raises(Exception):  # BudgetExceededError
            controller.check_budget(10.0)


class TestErrorHandling:
    """錯誤處理測試"""

    def test_error_classifier(self):
        """測試錯誤分類器"""
        # 網路錯誤
        network_error = Exception("Connection timeout")
        error_type = ErrorClassifier.classify_error(network_error)
        assert error_type.value == "network_error"
        
        # 認證錯誤
        auth_error = Exception("Invalid API key")
        error_type = ErrorClassifier.classify_error(auth_error)
        assert error_type.value == "authentication_error"
        
        # 速率限制錯誤
        rate_error = Exception("Rate limit exceeded")
        error_type = ErrorClassifier.classify_error(rate_error)
        assert error_type.value == "rate_limit_error"

    def test_error_retryability(self):
        """測試錯誤可重試性"""
        from src.api.error_handling import ErrorType
        
        # 可重試錯誤
        assert ErrorClassifier.is_retryable(ErrorType.NETWORK_ERROR) is True
        assert ErrorClassifier.is_retryable(ErrorType.SERVER_ERROR) is True
        
        # 不可重試錯誤
        assert ErrorClassifier.is_retryable(ErrorType.AUTHENTICATION_ERROR) is False

    @pytest.mark.asyncio
    async def test_retry_handler(self):
        """測試重試處理器"""
        config = RetryConfig(
            max_retries=3,
            base_delay=0.1,
            max_delay=1.0
        )
        
        handler = RetryHandler(config)
        
        # 模擬成功的函數
        async def success_func():
            return "success"
        
        result = await handler.execute_with_retry(success_func)
        assert result == "success"
        
        # 模擬失敗的函數
        call_count = 0
        async def fail_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success after retries"
        
        result = await handler.execute_with_retry(fail_func)
        assert result == "success after retries"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker(self):
        """測試熔斷器"""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=1.0,
            success_threshold=1
        )
        
        breaker = CircuitBreaker(config)
        
        # 模擬失敗的函數
        async def fail_func():
            raise Exception("Service unavailable")
        
        # 觸發熔斷器
        for _ in range(3):
            try:
                await breaker.call(fail_func)
            except:
                pass
        
        # 檢查熔斷器狀態
        state = breaker.get_state()
        assert state['failure_count'] >= 2

    def test_error_tracker(self):
        """測試錯誤追蹤器"""
        from src.api.error_handling import ErrorType
        
        tracker = ErrorTracker(max_records=100)
        
        # 記錄錯誤
        tracker.record_error(
            error_type=ErrorType.NETWORK_ERROR,
            error_message="Connection failed",
            retry_count=2,
            response_time=1.5
        )
        
        # 獲取錯誤摘要
        summary = tracker.get_error_summary(hours=24)
        assert summary['total_errors'] == 1
        assert 'network_error' in summary['most_common_errors']


class TestLLMIntegration:
    """LLM整合測試"""

    @pytest.mark.asyncio
    async def test_end_to_end_llm_call(self):
        """測試端到端LLM調用"""
        # 創建配置
        config = {
            'providers': {
                'openai': {
                    'enabled': True,
                    'api_key': 'sk-test-key'
                }
            }
        }
        
        # 創建管理器
        manager = LLMManager(config)
        
        # 執行調用
        response = await manager.generate(
            prompt="測試提示詞",
            provider="openai"
        )
        
        assert isinstance(response, LLMResponse)
        assert response.content is not None

    def test_llm_configuration_loading(self):
        """測試LLM配置載入"""
        # 測試有效配置
        valid_config = {
            'providers': {
                'openai': {
                    'enabled': True,
                    'api_key': 'sk-test-key'
                }
            }
        }
        
        manager = LLMManager(valid_config)
        assert len(manager.connectors) > 0
        
        # 測試無效配置
        invalid_config = {
            'providers': {}
        }
        
        manager = LLMManager(invalid_config)
        assert len(manager.connectors) == 0


class TestLLMPerformance:
    """LLM性能測試"""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """測試並發請求"""
        config = {
            'providers': {
                'openai': {
                    'enabled': True,
                    'api_key': 'sk-test-key'
                }
            }
        }
        
        manager = LLMManager(config)
        
        # 創建多個並發請求
        tasks = []
        for i in range(5):
            task = manager.generate(
                prompt=f"測試提示詞 {i}",
                provider="openai"
            )
            tasks.append(task)
        
        # 等待所有請求完成
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 檢查響應
        successful_responses = [r for r in responses if isinstance(r, LLMResponse)]
        assert len(successful_responses) > 0

    def test_memory_efficiency(self):
        """測試記憶體效率"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # 創建多個管理器實例
        managers = []
        for i in range(10):
            config = {
                'providers': {
                    'openai': {
                        'enabled': True,
                        'api_key': f'sk-test-key-{i}'
                    }
                }
            }
            manager = LLMManager(config)
            managers.append(manager)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # 記憶體增長應該在合理範圍內
        assert memory_increase < 50 * 1024 * 1024  # 小於50MB


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v", "--tb=short"])
