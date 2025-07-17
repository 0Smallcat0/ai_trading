# -*- coding: utf-8 -*-
"""
實時決策輔助服務

此模組提供實時的交易決策輔助功能。

主要功能：
- 實時市場數據分析
- LLM決策生成
- 多策略信號聚合
- 風險評估和建議
- 決策歷史追蹤
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from ..strategy.llm_integration import (
    LLMStrategyIntegrator,
    DecisionContext,
    AggregatedDecision
)
from ..api.llm_connector import LLMManager
from ..data.market_data import MarketDataProvider
from ..risk.risk_manager import RiskManager

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class DecisionRequest:
    """決策請求"""
    stock_symbol: str
    request_time: datetime
    user_id: Optional[str] = None
    request_type: str = "real_time"  # real_time, batch, scheduled
    parameters: Optional[Dict[str, Any]] = None


@dataclass
class DecisionResponse:
    """決策響應"""
    request_id: str
    stock_symbol: str
    decision: AggregatedDecision
    processing_time: float
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class DecisionService:
    """決策服務"""

    def __init__(
        self,
        llm_manager: LLMManager,
        market_data_provider: MarketDataProvider,
        risk_manager: RiskManager,
        config: Optional[Dict[str, Any]] = None
    ):
        """初始化決策服務。

        Args:
            llm_manager: LLM管理器
            market_data_provider: 市場數據提供者
            risk_manager: 風險管理器
            config: 服務配置
        """
        self.llm_manager = llm_manager
        self.market_data_provider = market_data_provider
        self.risk_manager = risk_manager
        self.config = config or self._get_default_config()
        
        # 初始化策略整合器
        self.integrator = LLMStrategyIntegrator(
            llm_manager=llm_manager,
            integration_config=self.config.get('integration', {})
        )
        
        # 決策歷史
        self.decision_history: List[DecisionResponse] = []
        
        # 性能統計
        self.performance_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_processing_time': 0.0,
            'cache_hits': 0
        }
        
        # 決策快取
        self.decision_cache = {}
        self.cache_ttl = self.config.get('cache_ttl', 300)  # 5分鐘

    def _get_default_config(self) -> Dict[str, Any]:
        """獲取默認配置。

        Returns:
            默認配置字典
        """
        return {
            'cache_ttl': 300,
            'max_history_size': 1000,
            'data_lookback_days': 30,
            'news_lookback_days': 7,
            'integration': {
                'strategy_weights': {
                    'llm_weight': 0.5,
                    'technical_weight': 0.3,
                    'fundamental_weight': 0.2
                },
                'decision_threshold': 0.6
            },
            'risk_control': {
                'max_position_size': 0.1,
                'volatility_adjustment': True
            }
        }

    async def generate_decision(self, request: DecisionRequest) -> DecisionResponse:
        """生成交易決策。

        Args:
            request: 決策請求

        Returns:
            決策響應

        Raises:
            Exception: 當決策生成失敗時
        """
        start_time = datetime.now()
        request_id = self._generate_request_id(request)
        
        try:
            logger.info(f"開始處理決策請求: {request_id} - {request.stock_symbol}")
            
            # 檢查快取
            cached_decision = self._check_cache(request.stock_symbol)
            if cached_decision:
                self.performance_stats['cache_hits'] += 1
                logger.info(f"使用快取決策: {request_id}")
                return cached_decision
            
            # 收集決策上下文
            context = await self._collect_decision_context(request)
            
            # 生成整合決策
            decision = await self.integrator.generate_integrated_decision(
                context, request.stock_symbol
            )
            
            # 應用風險控制
            decision = self._apply_risk_control(decision, context)
            
            # 計算處理時間
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 構建響應
            response = DecisionResponse(
                request_id=request_id,
                stock_symbol=request.stock_symbol,
                decision=decision,
                processing_time=processing_time,
                timestamp=datetime.now(),
                metadata={
                    'request_type': request.request_type,
                    'user_id': request.user_id,
                    'context_summary': self._summarize_context(context)
                }
            )
            
            # 更新快取和歷史
            self._update_cache(request.stock_symbol, response)
            self._update_history(response)
            
            # 更新統計
            self.performance_stats['total_requests'] += 1
            self.performance_stats['successful_requests'] += 1
            self._update_average_processing_time(processing_time)
            
            logger.info(f"決策生成完成: {request_id}, 處理時間: {processing_time:.2f}s")
            return response
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self.performance_stats['total_requests'] += 1
            self.performance_stats['failed_requests'] += 1
            
            logger.error(f"決策生成失敗: {request_id} - {e}")
            raise

    async def _collect_decision_context(self, request: DecisionRequest) -> DecisionContext:
        """收集決策上下文。

        Args:
            request: 決策請求

        Returns:
            決策上下文

        Raises:
            Exception: 當數據收集失敗時
        """
        try:
            # 獲取市場數據
            end_date = request.request_time
            start_date = end_date - timedelta(days=self.config['data_lookback_days'])
            
            market_data = await self.market_data_provider.get_stock_data(
                symbol=request.stock_symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            # 獲取新聞數據
            news_data = None
            try:
                news_start_date = end_date - timedelta(days=self.config['news_lookback_days'])
                news_data = await self.market_data_provider.get_news_data(
                    symbol=request.stock_symbol,
                    start_date=news_start_date,
                    end_date=end_date
                )
            except Exception as e:
                logger.warning(f"獲取新聞數據失敗: {e}")
            
            # 計算技術指標
            technical_indicators = self._calculate_technical_indicators(market_data)
            
            # 獲取風險指標
            risk_metrics = await self.risk_manager.calculate_risk_metrics(
                symbol=request.stock_symbol,
                data=market_data
            )
            
            # 計算市場情緒
            market_sentiment = self._analyze_market_sentiment(market_data, news_data)
            
            # 計算波動率
            volatility = self._calculate_volatility(market_data)
            
            return DecisionContext(
                market_data=market_data,
                news_data=news_data,
                technical_indicators=technical_indicators,
                risk_metrics=risk_metrics,
                market_sentiment=market_sentiment,
                volatility=volatility
            )
            
        except Exception as e:
            logger.error(f"收集決策上下文失敗: {e}")
            raise

    def _calculate_technical_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """計算技術指標。

        Args:
            data: 市場數據

        Returns:
            技術指標字典
        """
        indicators = {}
        
        if '收盤價' in data.columns and len(data) >= 20:
            # 移動平均線
            indicators['MA5'] = data['收盤價'].rolling(window=5).mean()
            indicators['MA10'] = data['收盤價'].rolling(window=10).mean()
            indicators['MA20'] = data['收盤價'].rolling(window=20).mean()
            
            # RSI
            delta = data['收盤價'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            indicators['RSI'] = 100 - (100 / (1 + rs))
            
            # MACD
            exp1 = data['收盤價'].ewm(span=12).mean()
            exp2 = data['收盤價'].ewm(span=26).mean()
            indicators['MACD'] = exp1 - exp2
            indicators['MACD_signal'] = indicators['MACD'].ewm(span=9).mean()
        
        return indicators

    def _analyze_market_sentiment(
        self,
        market_data: pd.DataFrame,
        news_data: Optional[pd.DataFrame]
    ) -> str:
        """分析市場情緒。

        Args:
            market_data: 市場數據
            news_data: 新聞數據

        Returns:
            市場情緒描述
        """
        # 基於價格變化分析情緒
        if '收盤價' in market_data.columns and len(market_data) >= 5:
            recent_returns = market_data['收盤價'].pct_change().tail(5)
            avg_return = recent_returns.mean()
            
            if avg_return > 0.02:
                return "樂觀"
            elif avg_return < -0.02:
                return "悲觀"
            else:
                return "中性"
        
        return "中性"

    def _calculate_volatility(self, data: pd.DataFrame) -> float:
        """計算波動率。

        Args:
            data: 市場數據

        Returns:
            波動率
        """
        if '收盤價' in data.columns and len(data) >= 20:
            returns = data['收盤價'].pct_change().dropna()
            return returns.std() * (252 ** 0.5)  # 年化波動率
        
        return 0.2  # 默認波動率

    def _apply_risk_control(
        self,
        decision: AggregatedDecision,
        context: DecisionContext
    ) -> AggregatedDecision:
        """應用風險控制。

        Args:
            decision: 原始決策
            context: 決策上下文

        Returns:
            風險調整後的決策
        """
        # 檢查風險限制
        risk_config = self.config.get('risk_control', {})
        
        # 波動率調整
        if risk_config.get('volatility_adjustment', True) and context.volatility:
            if context.volatility > 0.4:  # 高波動率
                # 降低置信度
                decision.confidence *= 0.7
                # 調整執行建議
                if "高風險" not in decision.execution_recommendation:
                    decision.execution_recommendation = f"高波動率環境，{decision.execution_recommendation}"
        
        # 最大倉位限制
        max_position = risk_config.get('max_position_size', 0.1)
        if 'position_size_recommendation' in decision.risk_assessment:
            current_size = decision.risk_assessment['position_size_recommendation']
            decision.risk_assessment['position_size_recommendation'] = min(current_size, max_position)
        
        return decision

    def _check_cache(self, symbol: str) -> Optional[DecisionResponse]:
        """檢查決策快取。

        Args:
            symbol: 股票代碼

        Returns:
            快取的決策響應或None
        """
        if symbol in self.decision_cache:
            cached_response, cache_time = self.decision_cache[symbol]
            
            # 檢查是否過期
            if (datetime.now() - cache_time).total_seconds() < self.cache_ttl:
                return cached_response
            else:
                # 清理過期快取
                del self.decision_cache[symbol]
        
        return None

    def _update_cache(self, symbol: str, response: DecisionResponse) -> None:
        """更新決策快取。

        Args:
            symbol: 股票代碼
            response: 決策響應
        """
        self.decision_cache[symbol] = (response, datetime.now())
        
        # 限制快取大小
        if len(self.decision_cache) > 100:
            # 移除最舊的快取項目
            oldest_symbol = min(
                self.decision_cache.keys(),
                key=lambda k: self.decision_cache[k][1]
            )
            del self.decision_cache[oldest_symbol]

    def _update_history(self, response: DecisionResponse) -> None:
        """更新決策歷史。

        Args:
            response: 決策響應
        """
        self.decision_history.append(response)
        
        # 限制歷史大小
        max_size = self.config.get('max_history_size', 1000)
        if len(self.decision_history) > max_size:
            self.decision_history = self.decision_history[-max_size//2:]

    def _update_average_processing_time(self, processing_time: float) -> None:
        """更新平均處理時間。

        Args:
            processing_time: 處理時間
        """
        current_avg = self.performance_stats['average_processing_time']
        total_requests = self.performance_stats['total_requests']
        
        if total_requests == 1:
            self.performance_stats['average_processing_time'] = processing_time
        else:
            # 計算移動平均
            self.performance_stats['average_processing_time'] = (
                (current_avg * (total_requests - 1) + processing_time) / total_requests
            )

    def _generate_request_id(self, request: DecisionRequest) -> str:
        """生成請求ID。

        Args:
            request: 決策請求

        Returns:
            請求ID
        """
        timestamp = request.request_time.strftime('%Y%m%d%H%M%S')
        return f"{request.stock_symbol}_{timestamp}_{hash(str(request)) % 10000:04d}"

    def _summarize_context(self, context: DecisionContext) -> Dict[str, Any]:
        """總結決策上下文。

        Args:
            context: 決策上下文

        Returns:
            上下文摘要
        """
        return {
            'market_data_points': len(context.market_data),
            'news_data_available': context.news_data is not None,
            'technical_indicators_count': len(context.technical_indicators or {}),
            'market_sentiment': context.market_sentiment,
            'volatility': context.volatility
        }

    def get_decision_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """獲取決策歷史。

        Args:
            symbol: 股票代碼過濾
            limit: 返回數量限制

        Returns:
            決策歷史列表
        """
        history = self.decision_history
        
        # 按股票代碼過濾
        if symbol:
            history = [h for h in history if h.stock_symbol == symbol]
        
        # 按時間排序並限制數量
        history = sorted(history, key=lambda x: x.timestamp, reverse=True)[:limit]
        
        # 轉換為字典格式
        return [asdict(response) for response in history]

    def get_performance_stats(self) -> Dict[str, Any]:
        """獲取性能統計。

        Returns:
            性能統計字典
        """
        stats = self.performance_stats.copy()
        
        # 計算成功率
        if stats['total_requests'] > 0:
            stats['success_rate'] = stats['successful_requests'] / stats['total_requests']
        else:
            stats['success_rate'] = 0.0
        
        # 添加快取統計
        stats['cache_hit_rate'] = (
            stats['cache_hits'] / stats['total_requests']
            if stats['total_requests'] > 0 else 0.0
        )
        
        return stats

    async def batch_generate_decisions(
        self,
        symbols: List[str],
        request_time: Optional[datetime] = None
    ) -> List[DecisionResponse]:
        """批量生成決策。

        Args:
            symbols: 股票代碼列表
            request_time: 請求時間

        Returns:
            決策響應列表
        """
        if request_time is None:
            request_time = datetime.now()
        
        # 創建批量請求
        requests = [
            DecisionRequest(
                stock_symbol=symbol,
                request_time=request_time,
                request_type="batch"
            )
            for symbol in symbols
        ]
        
        # 並行處理
        tasks = [self.generate_decision(request) for request in requests]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 過濾異常
        valid_responses = [
            response for response in responses
            if isinstance(response, DecisionResponse)
        ]
        
        return valid_responses
