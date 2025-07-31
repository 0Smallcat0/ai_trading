# -*- coding: utf-8 -*-
"""
LLM API連接器模組

此模組提供統一的大語言模型API接口，支持多種LLM服務商。

主要功能：
- 統一的LLM API接口
- 多種模型支持 (OpenAI, Claude, 本地模型等)
- API金鑰安全管理
- 錯誤處理和重試機制
- 速率限制和成本控制
"""

import logging
import time
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum
import json
import os
from datetime import datetime, timedelta

# 設定日誌
logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """LLM服務提供商枚舉"""
    OPENAI = "openai"
    CLAUDE = "claude"
    QWEN = "qwen"
    LOCAL = "local"
    CUSTOM = "custom"


@dataclass
class LLMRequest:
    """LLM請求數據結構"""
    prompt: str
    model: str
    max_tokens: int = 2000
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: Optional[List[str]] = None
    stream: bool = False
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LLMResponse:
    """LLM響應數據結構"""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    response_time: float
    provider: str
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class LLMConnectorError(Exception):
    """LLM連接器錯誤基類"""


class LLMAuthenticationError(LLMConnectorError):
    """LLM認證錯誤"""


class LLMRateLimitError(LLMConnectorError):
    """LLM速率限制錯誤"""


class LLMQuotaExceededError(LLMConnectorError):
    """LLM配額超限錯誤"""


class BaseLLMConnector(ABC):
    """LLM連接器基類"""

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **kwargs
    ):
        """初始化LLM連接器。

        Args:
            api_key: API金鑰
            base_url: API基礎URL
            timeout: 請求超時時間（秒）
            max_retries: 最大重試次數
            retry_delay: 重試延遲時間（秒）
            **kwargs: 其他配置參數
        """
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.config = kwargs

        # 初始化統計信息
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
            'last_request_time': None
        }

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成LLM響應。

        Args:
            request: LLM請求

        Returns:
            LLM響應

        Raises:
            LLMConnectorError: 當請求失敗時
        """

    @abstractmethod
    def get_provider(self) -> LLMProvider:
        """獲取提供商類型。

        Returns:
            提供商枚舉值
        """

    @abstractmethod
    def validate_config(self) -> bool:
        """驗證配置。

        Returns:
            配置是否有效
        """

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計信息。

        Returns:
            統計信息字典
        """
        return self.stats.copy()

    def reset_stats(self) -> None:
        """重置統計信息。"""
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
            'last_request_time': None
        }

    async def _retry_request(self, request_func, *args, **kwargs) -> Any:
        """重試請求機制。

        Args:
            request_func: 請求函數
            *args: 位置參數
            **kwargs: 關鍵字參數

        Returns:
            請求結果

        Raises:
            LLMConnectorError: 當所有重試都失敗時
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await request_func(*args, **kwargs)
            except LLMRateLimitError as e:
                # 速率限制錯誤，使用指數退避
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"速率限制，等待 {delay} 秒後重試 (嘗試 {attempt + 1}/{self.max_retries + 1})")
                    await asyncio.sleep(delay)
                    last_exception = e
                else:
                    raise e
            except LLMAuthenticationError as e:
                # 認證錯誤不重試
                raise e
            except Exception as e:
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"請求失敗，等待 {delay} 秒後重試: {e}")
                    await asyncio.sleep(delay)
                    last_exception = e
                else:
                    last_exception = e
        
        # 所有重試都失敗
        raise LLMConnectorError(f"請求失敗，已重試 {self.max_retries} 次: {last_exception}")

    def _update_stats(self, response: LLMResponse, success: bool = True) -> None:
        """更新統計信息。

        Args:
            response: LLM響應
            success: 是否成功
        """
        self.stats['total_requests'] += 1
        self.stats['last_request_time'] = datetime.now()
        
        if success:
            self.stats['successful_requests'] += 1
            if response.usage:
                self.stats['total_tokens'] += response.usage.get('total_tokens', 0)
        else:
            self.stats['failed_requests'] += 1


class OpenAIConnector(BaseLLMConnector):
    """OpenAI API連接器"""

    def __init__(self, api_key: str, **kwargs):
        """初始化OpenAI連接器。

        Args:
            api_key: OpenAI API金鑰
            **kwargs: 其他配置參數
        """
        super().__init__(
            api_key=api_key,
            base_url=kwargs.get('base_url', 'https://api.openai.com/v1'),
            **kwargs
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成OpenAI響應。

        Args:
            request: LLM請求

        Returns:
            LLM響應

        Raises:
            LLMConnectorError: 當請求失敗時
        """
        start_time = time.time()
        
        try:
            # 這裡將實現實際的OpenAI API調用
            # 暫時返回模擬響應
            await asyncio.sleep(0.1)  # 模擬網路延遲
            
            response = LLMResponse(
                content=f"OpenAI模擬響應: {request.prompt[:50]}...",
                model=request.model,
                usage={'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
                finish_reason='stop',
                response_time=time.time() - start_time,
                provider=self.get_provider().value,
                metadata={'request_id': f"openai_{int(time.time())}"}
            )
            
            self._update_stats(response, success=True)
            return response
            
        except Exception as e:
            error_response = LLMResponse(
                content="",
                model=request.model,
                usage={},
                finish_reason='error',
                response_time=time.time() - start_time,
                provider=self.get_provider().value,
                error=str(e)
            )
            self._update_stats(error_response, success=False)
            raise LLMConnectorError(f"OpenAI API調用失敗: {e}") from e

    def get_provider(self) -> LLMProvider:
        """獲取提供商類型。

        Returns:
            OpenAI提供商
        """
        return LLMProvider.OPENAI

    def validate_config(self) -> bool:
        """驗證OpenAI配置。

        Returns:
            配置是否有效
        """
        return bool(self.api_key and self.api_key.startswith('sk-'))


class ClaudeConnector(BaseLLMConnector):
    """Claude API連接器"""

    def __init__(self, api_key: str, **kwargs):
        """初始化Claude連接器。

        Args:
            api_key: Claude API金鑰
            **kwargs: 其他配置參數
        """
        super().__init__(
            api_key=api_key,
            base_url=kwargs.get('base_url', 'https://api.anthropic.com'),
            **kwargs
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成Claude響應。

        Args:
            request: LLM請求

        Returns:
            LLM響應

        Raises:
            LLMConnectorError: 當請求失敗時
        """
        start_time = time.time()
        
        try:
            # 這裡將實現實際的Claude API調用
            # 暫時返回模擬響應
            await asyncio.sleep(0.15)  # 模擬網路延遲
            
            response = LLMResponse(
                content=f"Claude模擬響應: {request.prompt[:50]}...",
                model=request.model,
                usage={'input_tokens': 100, 'output_tokens': 50, 'total_tokens': 150},
                finish_reason='end_turn',
                response_time=time.time() - start_time,
                provider=self.get_provider().value,
                metadata={'request_id': f"claude_{int(time.time())}"}
            )
            
            self._update_stats(response, success=True)
            return response
            
        except Exception as e:
            error_response = LLMResponse(
                content="",
                model=request.model,
                usage={},
                finish_reason='error',
                response_time=time.time() - start_time,
                provider=self.get_provider().value,
                error=str(e)
            )
            self._update_stats(error_response, success=False)
            raise LLMConnectorError(f"Claude API調用失敗: {e}") from e

    def get_provider(self) -> LLMProvider:
        """獲取提供商類型。

        Returns:
            Claude提供商
        """
        return LLMProvider.CLAUDE

    def validate_config(self) -> bool:
        """驗證Claude配置。

        Returns:
            配置是否有效
        """
        return bool(self.api_key)


class LocalLLMConnector(BaseLLMConnector):
    """本地LLM連接器"""

    def __init__(self, api_key: str = "local", **kwargs):
        """初始化本地LLM連接器。

        Args:
            api_key: 本地API金鑰（可選）
            **kwargs: 其他配置參數
        """
        super().__init__(
            api_key=api_key,
            base_url=kwargs.get('base_url', 'http://localhost:8000'),
            **kwargs
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """生成本地LLM響應。

        Args:
            request: LLM請求

        Returns:
            LLM響應

        Raises:
            LLMConnectorError: 當請求失敗時
        """
        start_time = time.time()
        
        try:
            # 這裡將實現實際的本地LLM API調用
            # 暫時返回模擬響應
            await asyncio.sleep(0.2)  # 模擬處理時間
            
            response = LLMResponse(
                content=f"本地LLM模擬響應: {request.prompt[:50]}...",
                model=request.model,
                usage={'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
                finish_reason='stop',
                response_time=time.time() - start_time,
                provider=self.get_provider().value,
                metadata={'request_id': f"local_{int(time.time())}"}
            )
            
            self._update_stats(response, success=True)
            return response
            
        except Exception as e:
            error_response = LLMResponse(
                content="",
                model=request.model,
                usage={},
                finish_reason='error',
                response_time=time.time() - start_time,
                provider=self.get_provider().value,
                error=str(e)
            )
            self._update_stats(error_response, success=False)
            raise LLMConnectorError(f"本地LLM調用失敗: {e}") from e

    def get_provider(self) -> LLMProvider:
        """獲取提供商類型。

        Returns:
            本地提供商
        """
        return LLMProvider.LOCAL

    def validate_config(self) -> bool:
        """驗證本地LLM配置。

        Returns:
            配置是否有效
        """
        return bool(self.base_url)


class LLMConnectorFactory:
    """LLM連接器工廠類"""

    @staticmethod
    def create_connector(
        provider: Union[str, LLMProvider],
        api_key: str,
        **kwargs
    ) -> BaseLLMConnector:
        """創建LLM連接器。

        Args:
            provider: 提供商類型
            api_key: API金鑰
            **kwargs: 其他配置參數

        Returns:
            LLM連接器實例

        Raises:
            ValueError: 當提供商類型不支持時
        """
        if isinstance(provider, str):
            try:
                provider = LLMProvider(provider.lower())
            except ValueError:
                raise ValueError(f"不支持的LLM提供商: {provider}")

        connector_map = {
            LLMProvider.OPENAI: OpenAIConnector,
            LLMProvider.CLAUDE: ClaudeConnector,
            LLMProvider.LOCAL: LocalLLMConnector,
            LLMProvider.QWEN: LocalLLMConnector,  # Qwen使用本地連接器
        }

        if provider not in connector_map:
            raise ValueError(f"不支持的LLM提供商: {provider}")

        connector_class = connector_map[provider]
        return connector_class(api_key=api_key, **kwargs)


class RateLimiter:
    """速率限制器"""

    def __init__(self, max_requests: int = 60, time_window: int = 60):
        """初始化速率限制器。

        Args:
            max_requests: 時間窗口內最大請求數
            time_window: 時間窗口（秒）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []

    async def acquire(self) -> None:
        """獲取請求許可。

        Raises:
            LLMRateLimitError: 當超過速率限制時
        """
        now = time.time()

        # 清理過期的請求記錄
        self.requests = [req_time for req_time in self.requests
                        if now - req_time < self.time_window]

        # 檢查是否超過限制
        if len(self.requests) >= self.max_requests:
            oldest_request = min(self.requests)
            wait_time = self.time_window - (now - oldest_request)
            raise LLMRateLimitError(f"速率限制，需等待 {wait_time:.2f} 秒")

        # 記錄當前請求
        self.requests.append(now)


class CostTracker:
    """成本追蹤器"""

    def __init__(self):
        """初始化成本追蹤器。"""
        self.costs = {
            'total_cost': 0.0,
            'daily_cost': 0.0,
            'monthly_cost': 0.0,
            'last_reset_date': datetime.now().date(),
            'provider_costs': {}
        }

        # 定義各提供商的定價（每1000 tokens）
        self.pricing = {
            LLMProvider.OPENAI: {
                'gpt-3.5-turbo': {'input': 0.0015, 'output': 0.002},
                'gpt-4': {'input': 0.03, 'output': 0.06},
                'gpt-4-turbo': {'input': 0.01, 'output': 0.03}
            },
            LLMProvider.CLAUDE: {
                'claude-3-haiku': {'input': 0.00025, 'output': 0.00125},
                'claude-3-sonnet': {'input': 0.003, 'output': 0.015},
                'claude-3-opus': {'input': 0.015, 'output': 0.075}
            },
            LLMProvider.LOCAL: {
                'default': {'input': 0.0, 'output': 0.0}  # 本地模型免費
            }
        }

    def calculate_cost(self, response: LLMResponse) -> float:
        """計算請求成本。

        Args:
            response: LLM響應

        Returns:
            請求成本
        """
        provider = LLMProvider(response.provider)
        model = response.model
        usage = response.usage

        if provider not in self.pricing:
            return 0.0

        model_pricing = self.pricing[provider].get(model)
        if not model_pricing:
            # 使用默認定價
            model_pricing = list(self.pricing[provider].values())[0]

        input_tokens = usage.get('prompt_tokens', 0)
        output_tokens = usage.get('completion_tokens', 0)

        input_cost = (input_tokens / 1000) * model_pricing['input']
        output_cost = (output_tokens / 1000) * model_pricing['output']

        return input_cost + output_cost

    def track_cost(self, response: LLMResponse) -> None:
        """追蹤成本。

        Args:
            response: LLM響應
        """
        cost = self.calculate_cost(response)

        # 檢查是否需要重置日期
        today = datetime.now().date()
        if today != self.costs['last_reset_date']:
            self.costs['daily_cost'] = 0.0
            self.costs['last_reset_date'] = today

        # 更新成本
        self.costs['total_cost'] += cost
        self.costs['daily_cost'] += cost

        # 更新提供商成本
        provider = response.provider
        if provider not in self.costs['provider_costs']:
            self.costs['provider_costs'][provider] = 0.0
        self.costs['provider_costs'][provider] += cost

    def get_costs(self) -> Dict[str, Any]:
        """獲取成本信息。

        Returns:
            成本信息字典
        """
        return self.costs.copy()

    def set_daily_limit(self, limit: float) -> None:
        """設置日成本限制。

        Args:
            limit: 日成本限制
        """
        self.daily_limit = limit

    def check_daily_limit(self) -> bool:
        """檢查是否超過日成本限制。

        Returns:
            是否超過限制
        """
        return hasattr(self, 'daily_limit') and self.costs['daily_cost'] >= self.daily_limit


class LLMManager:
    """LLM管理器"""

    def __init__(self, config: Dict[str, Any]):
        """初始化LLM管理器。

        Args:
            config: 配置字典
        """
        self.config = config
        self.connectors = {}
        self.rate_limiter = RateLimiter(
            max_requests=config.get('rate_limit', {}).get('max_requests', 60),
            time_window=config.get('rate_limit', {}).get('time_window', 60)
        )
        self.cost_tracker = CostTracker()

        # 設置日成本限制
        daily_limit = config.get('cost_control', {}).get('daily_limit')
        if daily_limit:
            self.cost_tracker.set_daily_limit(daily_limit)

        # 初始化連接器
        self._initialize_connectors()

    def _initialize_connectors(self) -> None:
        """初始化連接器。"""
        providers_config = self.config.get('providers', {})

        for provider_name, provider_config in providers_config.items():
            if provider_config.get('enabled', False):
                try:
                    connector = LLMConnectorFactory.create_connector(
                        provider=provider_name,
                        **provider_config
                    )
                    if connector.validate_config():
                        self.connectors[provider_name] = connector
                        logger.info(f"初始化LLM連接器成功: {provider_name}")
                    else:
                        logger.warning(f"LLM連接器配置無效: {provider_name}")
                except Exception as e:
                    logger.error(f"初始化LLM連接器失敗 {provider_name}: {e}")

    async def generate(
        self,
        prompt: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """生成LLM響應。

        Args:
            prompt: 提示詞
            provider: 指定的提供商
            model: 指定的模型
            **kwargs: 其他參數

        Returns:
            LLM響應

        Raises:
            LLMConnectorError: 當生成失敗時
        """
        # 檢查成本限制
        if self.cost_tracker.check_daily_limit():
            raise LLMQuotaExceededError("已達到日成本限制")

        # 檢查速率限制
        await self.rate_limiter.acquire()

        # 選擇連接器
        connector = self._select_connector(provider)

        # 構建請求
        request = LLMRequest(
            prompt=prompt,
            model=model or self._get_default_model(connector.get_provider()),
            **kwargs
        )

        # 生成響應
        response = await connector.generate(request)

        # 追蹤成本
        self.cost_tracker.track_cost(response)

        return response

    def _select_connector(self, provider: Optional[str] = None) -> BaseLLMConnector:
        """選擇連接器。

        Args:
            provider: 指定的提供商

        Returns:
            選中的連接器

        Raises:
            LLMConnectorError: 當沒有可用連接器時
        """
        if provider and provider in self.connectors:
            return self.connectors[provider]

        # 使用默認連接器
        if not self.connectors:
            raise LLMConnectorError("沒有可用的LLM連接器")

        # 返回第一個可用的連接器
        return next(iter(self.connectors.values()))

    def _get_default_model(self, provider: LLMProvider) -> str:
        """獲取默認模型。

        Args:
            provider: 提供商

        Returns:
            默認模型名稱
        """
        default_models = {
            LLMProvider.OPENAI: 'gpt-3.5-turbo',
            LLMProvider.CLAUDE: 'claude-3-haiku',
            LLMProvider.LOCAL: 'qwen-7b',
            LLMProvider.QWEN: 'qwen-7b'
        }

        return default_models.get(provider, 'default')

    def get_status(self) -> Dict[str, Any]:
        """獲取管理器狀態。

        Returns:
            狀態信息字典
        """
        status = {
            'connectors': {},
            'costs': self.cost_tracker.get_costs(),
            'rate_limit': {
                'current_requests': len(self.rate_limiter.requests),
                'max_requests': self.rate_limiter.max_requests,
                'time_window': self.rate_limiter.time_window
            }
        }

        for name, connector in self.connectors.items():
            status['connectors'][name] = {
                'provider': connector.get_provider().value,
                'stats': connector.get_stats()
            }

        return status
