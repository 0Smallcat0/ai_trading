# -*- coding: utf-8 -*-
"""
多代理系統Phase 1綜合測試套件

此模組包含Phase 1基礎架構的整合測試。

測試範圍：
- 代理管理器功能
- 代理間通信機制
- 績效評估器功能
- 系統整合測試
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# 導入被測試的模組
from src.agents import (
    TradingAgent,
    AgentManager,
    AgentCommunication,
    PerformanceEvaluator,
    InvestmentStyle,
    RiskPreference,
    AgentDecision,
    AgentMessage,
    PerformanceMetric,
)


class MockTradingAgent(TradingAgent):
    """測試用的模擬代理"""
    
    def __init__(self, name, return_rate=0.01, **kwargs):
        super().__init__(name=name, **kwargs)
        self.return_rate = return_rate
        self.decision_count = 0
    
    def make_decision(self, data, market_context=None):
        """模擬決策邏輯"""
        self.decision_count += 1
        
        # 模擬不同的決策結果
        if self.decision_count % 3 == 0:
            action = 1  # 買入
            confidence = 0.8
            reasoning = "模擬買入信號"
        elif self.decision_count % 3 == 1:
            action = -1  # 賣出
            confidence = 0.7
            reasoning = "模擬賣出信號"
        else:
            action = 0  # 觀望
            confidence = 0.5
            reasoning = "模擬觀望信號"
        
        return AgentDecision(
            agent_id=self.agent_id,
            timestamp=datetime.now(),
            symbol="TEST",
            action=action,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def get_investment_philosophy(self):
        return f"模擬代理 {self.name}：固定收益率 {self.return_rate}"


class TestAgentManager:
    """代理管理器測試"""
    
    def setup_method(self):
        """測試前設置"""
        self.manager = AgentManager(max_agents=5)
        self.agents = [
            MockTradingAgent(f"Agent{i}", return_rate=0.01 * (i + 1))
            for i in range(3)
        ]
    
    def test_agent_registration(self):
        """測試代理註冊"""
        agent = self.agents[0]
        
        # 註冊代理
        success = self.manager.register_agent(agent)
        assert success is True
        assert agent.agent_id in self.manager.agents
        assert self.manager.agent_weights[agent.agent_id] == self.manager.default_weight
        assert self.manager.agent_status[agent.agent_id] == "active"
        
        # 重複註冊應該失敗
        success = self.manager.register_agent(agent)
        assert success is False
    
    def test_agent_lifecycle(self):
        """測試代理生命週期管理"""
        agent = self.agents[0]
        self.manager.register_agent(agent)
        
        # 停止代理
        success = self.manager.stop_agent(agent.agent_id)
        assert success is True
        assert self.manager.agent_status[agent.agent_id] == "inactive"
        assert agent.is_active is False
        
        # 重新啟動代理
        success = self.manager.start_agent(agent.agent_id)
        assert success is True
        assert self.manager.agent_status[agent.agent_id] == "active"
        assert agent.is_active is True
        
        # 註銷代理
        success = self.manager.unregister_agent(agent.agent_id)
        assert success is True
        assert agent.agent_id not in self.manager.agents
    
    def test_weight_management(self):
        """測試權重管理"""
        # 註冊多個代理
        for agent in self.agents:
            self.manager.register_agent(agent)
        
        # 更新權重
        agent_id = self.agents[0].agent_id
        new_weight = 0.5
        success = self.manager.update_agent_weight(agent_id, new_weight)
        assert success is True
        assert self.manager.agent_weights[agent_id] == new_weight
        
        # 標準化權重
        self.manager.normalize_weights()
        total_weight = sum(self.manager.agent_weights.values())
        assert abs(total_weight - 1.0) < 1e-6
    
    def test_decision_collection(self):
        """測試決策收集"""
        # 註冊代理
        for agent in self.agents:
            self.manager.register_agent(agent)
        
        # 創建測試數據
        test_data = pd.DataFrame({
            'close': [100, 101, 102],
            'volume': [1000, 1100, 1200]
        })
        
        # 收集決策
        decisions = self.manager.collect_decisions(test_data)
        
        assert len(decisions) == len(self.agents)
        for decision in decisions:
            assert isinstance(decision, AgentDecision)
            assert decision.action in [-1, 0, 1]
            assert 0 <= decision.confidence <= 1
    
    def test_manager_status(self):
        """測試管理器狀態"""
        # 註冊代理
        for agent in self.agents:
            self.manager.register_agent(agent)
        
        status = self.manager.get_manager_status()
        
        assert status['total_agents'] == len(self.agents)
        assert status['active_agents'] == len(self.agents)
        assert status['inactive_agents'] == 0
        assert 'performance_summary' in status
        assert 'agent_weights' in status


class TestAgentCommunication:
    """代理通信測試"""
    
    def setup_method(self):
        """測試前設置"""
        self.communication = AgentCommunication()
        self.agents = [
            MockTradingAgent(f"Agent{i}")
            for i in range(3)
        ]
        
        # 註冊代理到通信系統
        for agent in self.agents:
            self.communication.register_agent(agent.agent_id)
    
    def test_message_sending(self):
        """測試消息發送"""
        sender = self.agents[0]
        receiver = self.agents[1]
        
        # 創建消息
        message = AgentMessage(
            sender_id=sender.agent_id,
            receiver_id=receiver.agent_id,
            message_type="test_message",
            content={"data": "test"}
        )
        
        # 發送消息
        success = self.communication.send_message(message)
        assert success is True
        
        # 接收消息
        received_message = self.communication.receive_message(receiver.agent_id)
        assert received_message is not None
        assert received_message.sender_id == sender.agent_id
        assert received_message.content["data"] == "test"
    
    def test_broadcast_message(self):
        """測試廣播消息"""
        sender = self.agents[0]
        
        # 創建廣播消息
        message = AgentMessage(
            sender_id=sender.agent_id,
            receiver_id=None,  # 廣播
            message_type="broadcast_test",
            content={"announcement": "test broadcast"}
        )
        
        # 發送廣播
        success = self.communication.send_message(message)
        assert success is True
        
        # 檢查其他代理是否收到消息
        for agent in self.agents[1:]:  # 排除發送者
            received_message = self.communication.receive_message(agent.agent_id)
            assert received_message is not None
            assert received_message.message_type == "broadcast_test"
    
    def test_message_priority(self):
        """測試消息優先級"""
        sender = self.agents[0]
        receiver = self.agents[1]
        
        # 發送不同優先級的消息
        low_priority_msg = AgentMessage(
            sender_id=sender.agent_id,
            receiver_id=receiver.agent_id,
            message_type="low_priority",
            content={"priority": "low"},
            priority=1
        )
        
        high_priority_msg = AgentMessage(
            sender_id=sender.agent_id,
            receiver_id=receiver.agent_id,
            message_type="high_priority",
            content={"priority": "high"},
            priority=5
        )
        
        # 先發送低優先級，再發送高優先級
        self.communication.send_message(low_priority_msg)
        self.communication.send_message(high_priority_msg)
        
        # 接收消息，應該先收到高優先級消息
        first_msg = self.communication.receive_message(receiver.agent_id)
        assert first_msg.message_type == "high_priority"
        
        second_msg = self.communication.receive_message(receiver.agent_id)
        assert second_msg.message_type == "low_priority"
    
    def test_communication_stats(self):
        """測試通信統計"""
        stats = self.communication.get_communication_stats()
        
        assert stats['registered_agents'] == len(self.agents)
        assert 'message_stats' in stats
        assert 'queue_stats' in stats
        assert 'is_running' in stats


class TestPerformanceEvaluator:
    """績效評估器測試"""
    
    def setup_method(self):
        """測試前設置"""
        self.evaluator = PerformanceEvaluator()
        self.agent = MockTradingAgent("TestAgent")
        
        # 添加模擬績效數據
        returns = [0.02, -0.01, 0.03, 0.01, -0.005]
        for i, ret in enumerate(returns):
            self.agent.update_performance(ret, 0.01)
            # 模擬決策記錄
            decision = AgentDecision(
                agent_id=self.agent.agent_id,
                timestamp=datetime.now() - timedelta(days=len(returns) - i),
                symbol="TEST",
                action=1 if ret > 0 else -1,
                confidence=0.7,
                reasoning="測試決策"
            )
            self.agent.decision_history.append(decision)
    
    def test_single_agent_evaluation(self):
        """測試單個代理評估"""
        report = self.evaluator.evaluate_agent(self.agent)
        
        assert report.agent_id == self.agent.agent_id
        assert report.agent_name == self.agent.name
        assert report.total_trades > 0
        assert 0 <= report.win_rate <= 1
        assert 0 <= report.overall_score <= 100
    
    def test_multiple_agents_evaluation(self):
        """測試多代理評估"""
        agents = [
            MockTradingAgent(f"Agent{i}", return_rate=0.01 * (i + 1))
            for i in range(3)
        ]
        
        # 為每個代理添加績效數據
        for agent in agents:
            for _ in range(5):
                agent.update_performance(agent.return_rate, 0.01)
        
        reports = self.evaluator.evaluate_multiple_agents(agents)
        
        assert len(reports) == len(agents)
        # 檢查排名是否正確設置
        for i, report in enumerate(reports):
            assert report.rank == i + 1
    
    def test_weight_calculation(self):
        """測試權重計算"""
        agents = [
            MockTradingAgent(f"Agent{i}", return_rate=0.01 * (i + 1))
            for i in range(3)
        ]
        
        # 為每個代理添加績效數據
        for agent in agents:
            for _ in range(5):
                agent.update_performance(agent.return_rate, 0.01)
        
        # 測試不同權重計算方法
        equal_weights = self.evaluator.calculate_portfolio_weights(agents, "equal_weighted")
        score_weights = self.evaluator.calculate_portfolio_weights(agents, "score_weighted")
        
        # 檢查權重總和
        assert abs(sum(equal_weights.values()) - 1.0) < 1e-6
        assert abs(sum(score_weights.values()) - 1.0) < 1e-6
        
        # 等權重應該相等
        expected_equal_weight = 1.0 / len(agents)
        for weight in equal_weights.values():
            assert abs(weight - expected_equal_weight) < 1e-6


class TestSystemIntegration:
    """系統整合測試"""
    
    def setup_method(self):
        """測試前設置"""
        self.manager = AgentManager()
        self.communication = AgentCommunication()
        self.evaluator = PerformanceEvaluator()
        
        self.agents = [
            MockTradingAgent(f"Agent{i}", return_rate=0.01 * (i + 1))
            for i in range(3)
        ]
    
    def test_full_system_workflow(self):
        """測試完整系統工作流程"""
        # 1. 註冊代理
        for agent in self.agents:
            success = self.manager.register_agent(agent)
            assert success is True
            
            success = self.communication.register_agent(agent.agent_id)
            assert success is True
        
        # 2. 收集決策
        test_data = pd.DataFrame({
            'close': [100, 101, 102],
            'volume': [1000, 1100, 1200]
        })
        
        decisions = self.manager.collect_decisions(test_data)
        assert len(decisions) == len(self.agents)
        
        # 3. 模擬績效更新
        for agent in self.agents:
            for _ in range(10):
                agent.update_performance(agent.return_rate, 0.01)
        
        # 4. 評估績效
        reports = self.evaluator.evaluate_multiple_agents(self.agents)
        assert len(reports) == len(self.agents)
        
        # 5. 基於績效重新平衡權重
        success = self.manager.rebalance_weights()
        assert success is True
        
        # 6. 檢查系統狀態
        manager_status = self.manager.get_manager_status()
        comm_stats = self.communication.get_communication_stats()
        
        assert manager_status['total_agents'] == len(self.agents)
        assert comm_stats['registered_agents'] == len(self.agents)
    
    def teardown_method(self):
        """測試後清理"""
        self.manager.stop_manager()
        self.communication.stop_communication()
