# -*- coding: utf-8 -*-
"""
交易代理基類測試套件

此模組包含TradingAgent基類的單元測試。

測試範圍：
- 代理初始化和配置
- 決策生成和記錄
- 績效追蹤和評估
- 代理間通信
- 異常處理
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# 導入被測試的模組
from src.agents.base import (
    TradingAgent,
    AgentError,
    AgentConfigError,
    AgentCommunicationError,
    InvestmentStyle,
    RiskPreference,
    AgentDecision,
    AgentMessage,
)


class TestTradingAgent(TradingAgent):
    """測試用的具體代理實現"""
    
    def make_decision(self, data, market_context=None):
        """簡單的測試決策邏輯"""
        symbol = "TEST"
        if len(data) == 0:
            action = 0
            confidence = 0.5
            reasoning = "無數據"
        else:
            # 簡單的移動平均策略
            if 'close' in data.columns and len(data) >= 2:
                current_price = data['close'].iloc[-1]
                prev_price = data['close'].iloc[-2]
                if current_price > prev_price:
                    action = 1
                    confidence = 0.7
                    reasoning = "價格上漲，買入"
                elif current_price < prev_price:
                    action = -1
                    confidence = 0.6
                    reasoning = "價格下跌，賣出"
                else:
                    action = 0
                    confidence = 0.5
                    reasoning = "價格持平，觀望"
            else:
                action = 0
                confidence = 0.5
                reasoning = "數據不足"
        
        return AgentDecision(
            agent_id=self.agent_id,
            timestamp=datetime.now(),
            symbol=symbol,
            action=action,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def get_investment_philosophy(self):
        """測試投資哲學"""
        return "測試代理：基於簡單移動平均的決策邏輯"


class TestTradingAgentBase:
    """TradingAgent基類測試"""
    
    def setup_method(self):
        """測試前設置"""
        self.agent = TestTradingAgent(
            name="TestAgent",
            investment_style=InvestmentStyle.TECHNICAL,
            risk_preference=RiskPreference.MODERATE,
            max_position_size=0.1
        )
        
        # 創建測試數據
        self.test_data = pd.DataFrame({
            'close': [100, 101, 102, 101, 103],
            'volume': [1000, 1100, 1200, 1050, 1300]
        })
    
    def test_agent_initialization(self):
        """測試代理初始化"""
        assert self.agent.name == "TestAgent"
        assert self.agent.investment_style == InvestmentStyle.TECHNICAL
        assert self.agent.risk_preference == RiskPreference.MODERATE
        assert self.agent.max_position_size == 0.1
        assert self.agent.is_active is True
        assert len(self.agent.agent_id) > 0
        assert len(self.agent.performance_history) == 0
        assert len(self.agent.decision_history) == 0
    
    def test_agent_config_validation(self):
        """測試代理配置驗證"""
        # 測試無效的最大倉位大小
        with pytest.raises(AgentConfigError):
            TestTradingAgent(max_position_size=1.5)
        
        with pytest.raises(AgentConfigError):
            TestTradingAgent(max_position_size=0)
    
    def test_make_decision(self):
        """測試決策生成"""
        decision = self.agent.make_decision(self.test_data)
        
        assert isinstance(decision, AgentDecision)
        assert decision.agent_id == self.agent.agent_id
        assert decision.action in [-1, 0, 1]
        assert 0 <= decision.confidence <= 1
        assert len(decision.reasoning) > 0
        assert isinstance(decision.timestamp, datetime)
    
    def test_generate_signals(self):
        """測試訊號生成"""
        signals = self.agent.generate_signals(self.test_data)
        
        assert isinstance(signals, pd.DataFrame)
        assert len(signals) == len(self.test_data)
        assert 'signal' in signals.columns
        assert 'buy_signal' in signals.columns
        assert 'sell_signal' in signals.columns
        assert 'confidence' in signals.columns
        assert 'reasoning' in signals.columns
        
        # 檢查決策是否被記錄
        assert len(self.agent.decision_history) == 1
    
    def test_message_communication(self):
        """測試代理間通信"""
        # 創建另一個代理
        other_agent = TestTradingAgent(name="OtherAgent")
        
        # 發送消息
        message = self.agent.send_message(
            receiver_id=other_agent.agent_id,
            message_type="test_message",
            content={"data": "test"},
            priority=2
        )
        
        assert isinstance(message, AgentMessage)
        assert message.sender_id == self.agent.agent_id
        assert message.receiver_id == other_agent.agent_id
        assert message.message_type == "test_message"
        assert message.content["data"] == "test"
        assert message.priority == 2
        
        # 接收消息
        other_agent.receive_message(message)
        assert len(other_agent.message_inbox) == 1
        assert other_agent.message_inbox[0] == message
    
    def test_performance_tracking(self):
        """測試績效追蹤"""
        # 更新績效
        self.agent.update_performance(
            returns=0.05,
            benchmark_returns=0.03,
            risk_metrics={'volatility': 0.15}
        )
        
        assert len(self.agent.performance_history) == 1
        record = self.agent.performance_history[0]
        assert record['returns'] == 0.05
        assert record['benchmark_returns'] == 0.03
        assert record['excess_returns'] == 0.02
        assert record['risk_metrics']['volatility'] == 0.15
    
    def test_performance_summary(self):
        """測試績效摘要"""
        # 添加多個績效記錄
        returns = [0.02, -0.01, 0.03, 0.01, -0.005]
        for ret in returns:
            self.agent.update_performance(ret, 0.01)
        
        summary = self.agent.get_performance_summary()
        
        assert 'total_return' in summary
        assert 'avg_return' in summary
        assert 'volatility' in summary
        assert 'sharpe_ratio' in summary
        assert 'max_drawdown' in summary
        assert 'win_rate' in summary
        assert 'decision_count' in summary
        
        # 檢查勝率計算
        expected_win_rate = sum(1 for r in returns if r > 0) / len(returns)
        assert abs(summary['win_rate'] - expected_win_rate) < 0.01
    
    def test_recent_decisions(self):
        """測試最近決策獲取"""
        # 生成多個決策
        for _ in range(5):
            self.agent.generate_signals(self.test_data)
        
        recent_decisions = self.agent.get_recent_decisions(3)
        assert len(recent_decisions) == 3
        
        # 檢查是否按時間倒序排列
        for i in range(len(recent_decisions) - 1):
            assert recent_decisions[i].timestamp >= recent_decisions[i + 1].timestamp
    
    def test_agent_info(self):
        """測試代理信息獲取"""
        info = self.agent.get_agent_info()
        
        assert info['agent_id'] == self.agent.agent_id
        assert info['name'] == self.agent.name
        assert info['investment_style'] == self.agent.investment_style.value
        assert info['risk_preference'] == self.agent.risk_preference.value
        assert info['max_position_size'] == self.agent.max_position_size
        assert info['is_active'] == self.agent.is_active
        assert 'philosophy' in info
        assert 'performance_records' in info
        assert 'decision_records' in info
    
    def test_reset_performance(self):
        """測試績效重置"""
        # 添加一些數據
        self.agent.update_performance(0.05, 0.03)
        self.agent.generate_signals(self.test_data)
        
        assert len(self.agent.performance_history) > 0
        assert len(self.agent.decision_history) > 0
        
        # 重置
        self.agent.reset_performance()
        
        assert len(self.agent.performance_history) == 0
        assert len(self.agent.decision_history) == 0
    
    def test_string_representations(self):
        """測試字符串表示"""
        str_repr = str(self.agent)
        assert "TradingAgent" in str_repr
        assert self.agent.name in str_repr
        
        repr_str = repr(self.agent)
        assert "TradingAgent" in repr_str
        assert self.agent.agent_id[:8] in repr_str


class TestEnums:
    """測試枚舉類"""
    
    def test_investment_style_enum(self):
        """測試投資風格枚舉"""
        assert InvestmentStyle.VALUE.value == "value"
        assert InvestmentStyle.TECHNICAL.value == "technical"
        assert InvestmentStyle.MOMENTUM.value == "momentum"
        assert InvestmentStyle.ARBITRAGE.value == "arbitrage"
        assert InvestmentStyle.RISK_PARITY.value == "risk_parity"
    
    def test_risk_preference_enum(self):
        """測試風險偏好枚舉"""
        assert RiskPreference.CONSERVATIVE.value == "conservative"
        assert RiskPreference.MODERATE.value == "moderate"
        assert RiskPreference.AGGRESSIVE.value == "aggressive"
        assert RiskPreference.SPECULATIVE.value == "speculative"


class TestDataClasses:
    """測試數據類"""
    
    def test_agent_decision(self):
        """測試代理決策數據類"""
        decision = AgentDecision(
            agent_id="test_agent",
            timestamp=datetime.now(),
            symbol="AAPL",
            action=1,
            confidence=0.8,
            reasoning="測試決策"
        )
        
        assert decision.agent_id == "test_agent"
        assert decision.symbol == "AAPL"
        assert decision.action == 1
        assert decision.confidence == 0.8
        assert decision.reasoning == "測試決策"
    
    def test_agent_message(self):
        """測試代理消息數據類"""
        message = AgentMessage(
            sender_id="sender",
            receiver_id="receiver",
            message_type="test",
            content={"key": "value"}
        )
        
        assert message.sender_id == "sender"
        assert message.receiver_id == "receiver"
        assert message.message_type == "test"
        assert message.content["key"] == "value"
        assert message.priority == 1  # 默認值
