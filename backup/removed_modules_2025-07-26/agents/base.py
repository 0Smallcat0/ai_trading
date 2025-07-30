# -*- coding: utf-8 -*-
"""
交易代理基類模組

此模組定義了所有交易代理的基礎類別和共用功能。

主要功能：
- 定義交易代理基類 TradingAgent
- 提供代理決策生成的通用方法
- 定義代理異常類別
- 提供代理績效追蹤功能
- 整合現有Strategy基類
"""

import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field

import pandas as pd
import numpy as np

# 導入現有策略基類
from ..strategy.base import Strategy, StrategyError

# 設定日誌
logger = logging.getLogger(__name__)


class InvestmentStyle(Enum):
    """投資風格枚舉"""
    VALUE = "value"                    # 價值投資
    TECHNICAL = "technical"            # 技術分析
    MOMENTUM = "momentum"              # 動量交易
    ARBITRAGE = "arbitrage"            # 套利交易
    RISK_PARITY = "risk_parity"        # 風險平價
    GROWTH = "growth"                  # 成長投資
    QUANTITATIVE = "quantitative"      # 量化投資
    MACRO = "macro"                    # 宏觀對沖


class RiskPreference(Enum):
    """風險偏好枚舉"""
    CONSERVATIVE = "conservative"      # 保守型
    MODERATE = "moderate"              # 穩健型
    AGGRESSIVE = "aggressive"          # 積極型
    SPECULATIVE = "speculative"        # 投機型


@dataclass
class AgentDecision:
    """代理決策數據類"""
    agent_id: str
    timestamp: datetime
    symbol: str
    action: int                        # 1=買入, -1=賣出, 0=觀望
    confidence: float                  # 置信度 (0-1)
    reasoning: str                     # 決策推理過程
    expected_return: Optional[float] = None
    risk_assessment: Optional[float] = None
    position_size: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentMessage:
    """代理間通信消息數據類"""
    sender_id: str
    receiver_id: Optional[str]         # None表示廣播消息
    message_type: str                  # 消息類型
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 1                  # 優先級 (1-5, 5最高)


class AgentError(Exception):
    """代理相關錯誤基類"""
    pass


class AgentConfigError(AgentError):
    """代理配置錯誤"""
    pass


class AgentCommunicationError(AgentError):
    """代理通信錯誤"""
    pass


class TradingAgent(Strategy):
    """
    交易代理基類，所有具體交易代理都應該繼承此類。
    
    此類擴展了現有的Strategy基類，添加了代理特有的功能：
    - 投資風格和風險偏好
    - 代理間通信能力
    - 績效追蹤和評估
    - 決策推理和解釋
    
    Attributes:
        agent_id (str): 代理唯一標識符
        investment_style (InvestmentStyle): 投資風格
        risk_preference (RiskPreference): 風險偏好
        max_position_size (float): 最大倉位大小
        performance_history (List[Dict]): 績效歷史記錄
        decision_history (List[AgentDecision]): 決策歷史記錄
    """
    
    def __init__(
        self,
        name: str = "BaseAgent",
        investment_style: InvestmentStyle = InvestmentStyle.VALUE,
        risk_preference: RiskPreference = RiskPreference.MODERATE,
        max_position_size: float = 0.1,
        **parameters: Any
    ) -> None:
        """
        初始化交易代理。
        
        Args:
            name: 代理名稱
            investment_style: 投資風格
            risk_preference: 風險偏好
            max_position_size: 最大倉位大小（佔總資金比例）
            **parameters: 其他策略參數
            
        Raises:
            AgentConfigError: 當配置參數不正確時
        """
        # 調用父類初始化
        super().__init__(name=name, **parameters)
        
        # 代理特有屬性
        self.agent_id = str(uuid.uuid4())
        self.investment_style = investment_style
        self.risk_preference = risk_preference
        self.max_position_size = max_position_size
        
        # 績效和決策追蹤
        self.performance_history: List[Dict[str, Any]] = []
        self.decision_history: List[AgentDecision] = []
        self.message_inbox: List[AgentMessage] = []
        
        # 代理狀態
        self.is_active = True
        self.last_update = datetime.now()
        
        # 驗證配置
        self._validate_agent_config()
        
        logger.info(f"初始化交易代理: {self.name} (ID: {self.agent_id[:8]})")
    
    def _validate_agent_config(self) -> None:
        """驗證代理配置參數"""
        if not 0 < self.max_position_size <= 1:
            raise AgentConfigError("最大倉位大小必須在0和1之間")
        
        if not isinstance(self.investment_style, InvestmentStyle):
            raise AgentConfigError("投資風格必須是InvestmentStyle枚舉值")
        
        if not isinstance(self.risk_preference, RiskPreference):
            raise AgentConfigError("風險偏好必須是RiskPreference枚舉值")
    
    @abstractmethod
    def make_decision(
        self,
        data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]] = None
    ) -> AgentDecision:
        """
        生成投資決策。
        
        Args:
            data: 市場數據
            market_context: 市場上下文信息
            
        Returns:
            AgentDecision: 代理決策
            
        Raises:
            NotImplementedError: 子類必須實現此方法
        """
        pass
    
    @abstractmethod
    def get_investment_philosophy(self) -> str:
        """
        獲取投資哲學描述。
        
        Returns:
            str: 投資哲學描述
            
        Raises:
            NotImplementedError: 子類必須實現此方法
        """
        pass
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易訊號（實現Strategy基類的抽象方法）。
        
        Args:
            data: 輸入資料
            
        Returns:
            包含交易訊號的資料框架
        """
        try:
            # 生成決策
            decision = self.make_decision(data)
            
            # 記錄決策
            self.decision_history.append(decision)
            
            # 轉換為訊號格式
            signals = pd.DataFrame(
                index=data.index,
                columns=['signal', 'buy_signal', 'sell_signal', 'confidence', 'reasoning']
            )
            
            # 填充最新決策
            if len(signals) > 0:
                last_idx = signals.index[-1]
                signals.loc[last_idx, 'signal'] = decision.action
                signals.loc[last_idx, 'buy_signal'] = 1 if decision.action > 0 else 0
                signals.loc[last_idx, 'sell_signal'] = 1 if decision.action < 0 else 0
                signals.loc[last_idx, 'confidence'] = decision.confidence
                signals.loc[last_idx, 'reasoning'] = decision.reasoning
            
            # 填充其他行為0
            signals = signals.fillna(0)
            
            return signals

        except Exception as e:
            logger.error(f"代理 {self.name} 生成訊號失敗: {e}")
            raise AgentError(f"生成訊號失敗: {e}") from e

    def receive_message(self, message: AgentMessage) -> None:
        """
        接收來自其他代理的消息。

        Args:
            message: 代理消息
        """
        self.message_inbox.append(message)
        logger.debug(f"代理 {self.name} 收到來自 {message.sender_id} 的消息")

    def send_message(
        self,
        receiver_id: Optional[str],
        message_type: str,
        content: Dict[str, Any],
        priority: int = 1
    ) -> AgentMessage:
        """
        發送消息給其他代理。

        Args:
            receiver_id: 接收者ID，None表示廣播
            message_type: 消息類型
            content: 消息內容
            priority: 優先級

        Returns:
            AgentMessage: 發送的消息
        """
        message = AgentMessage(
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            message_type=message_type,
            content=content,
            priority=priority
        )

        logger.debug(f"代理 {self.name} 發送消息: {message_type}")
        return message

    def update_performance(
        self,
        returns: float,
        benchmark_returns: float = 0.0,
        risk_metrics: Optional[Dict[str, float]] = None
    ) -> None:
        """
        更新績效記錄。

        Args:
            returns: 收益率
            benchmark_returns: 基準收益率
            risk_metrics: 風險指標
        """
        performance_record = {
            'timestamp': datetime.now(),
            'returns': returns,
            'benchmark_returns': benchmark_returns,
            'excess_returns': returns - benchmark_returns,
            'risk_metrics': risk_metrics or {}
        }

        self.performance_history.append(performance_record)
        self.last_update = datetime.now()

        logger.debug(f"代理 {self.name} 更新績效: 收益率={returns:.4f}")

    def get_performance_summary(self, period_days: int = 30) -> Dict[str, Any]:
        """
        獲取績效摘要。

        Args:
            period_days: 統計期間（天數）

        Returns:
            Dict: 績效摘要
        """
        if not self.performance_history:
            return {
                'total_return': 0.0,
                'avg_return': 0.0,
                'volatility': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'decision_count': len(self.decision_history)
            }

        # 篩選指定期間的數據
        cutoff_date = datetime.now() - timedelta(days=period_days)
        recent_performance = [
            p for p in self.performance_history
            if p['timestamp'] >= cutoff_date
        ]

        if not recent_performance:
            return self.get_performance_summary(period_days * 2)  # 擴大範圍

        # 計算績效指標
        returns = [p['returns'] for p in recent_performance]
        returns_array = np.array(returns)

        total_return = np.prod(1 + returns_array) - 1
        avg_return = np.mean(returns_array)
        volatility = np.std(returns_array) if len(returns_array) > 1 else 0.0

        # 夏普比率（假設無風險利率為0）
        sharpe_ratio = avg_return / volatility if volatility > 0 else 0.0

        # 最大回撤
        cumulative_returns = np.cumprod(1 + returns_array)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else 0.0

        # 勝率
        win_rate = np.mean(returns_array > 0) if len(returns_array) > 0 else 0.0

        return {
            'total_return': total_return,
            'avg_return': avg_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'decision_count': len([d for d in self.decision_history
                                 if d.timestamp >= cutoff_date])
        }

    def get_recent_decisions(self, count: int = 10) -> List[AgentDecision]:
        """
        獲取最近的決策記錄。

        Args:
            count: 返回的決策數量

        Returns:
            List[AgentDecision]: 最近的決策列表
        """
        return sorted(
            self.decision_history,
            key=lambda x: x.timestamp,
            reverse=True
        )[:count]

    def reset_performance(self) -> None:
        """重置績效記錄"""
        self.performance_history.clear()
        self.decision_history.clear()
        logger.info(f"代理 {self.name} 績效記錄已重置")

    def get_agent_info(self) -> Dict[str, Any]:
        """
        獲取代理基本信息。

        Returns:
            Dict: 代理信息
        """
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'investment_style': self.investment_style.value,
            'risk_preference': self.risk_preference.value,
            'max_position_size': self.max_position_size,
            'is_active': self.is_active,
            'last_update': self.last_update,
            'philosophy': self.get_investment_philosophy(),
            'performance_records': len(self.performance_history),
            'decision_records': len(self.decision_history)
        }

    def __str__(self) -> str:
        """字符串表示"""
        return f"TradingAgent(name={self.name}, style={self.investment_style.value})"

    def __repr__(self) -> str:
        """詳細字符串表示"""
        return (f"TradingAgent(id={self.agent_id[:8]}, name={self.name}, "
                f"style={self.investment_style.value}, "
                f"risk={self.risk_preference.value})")
