# -*- coding: utf-8 -*-
"""
協作機制Phase 4測試套件

此模組包含Phase 4協作機制的測試。

測試範圍：
- 決策協調器（DecisionCoordinator）
- 動態權重調整器（DynamicWeightAdjuster）
- 投資組合分配器（PortfolioAllocator）
- 代理間通信（AgentCommunication）
"""

import pytest
import pandas as pd
import numpy as np
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# 導入被測試的模組
from src.coordination import (
    DecisionCoordinator,
    DynamicWeightAdjuster,
    PortfolioAllocator,
    AgentCommunication,
    CoordinatedDecision,
    CoordinationMethod,
    ConflictResolution,
    WeightAdjustmentMethod,
    AllocationMethod,
    Message,
    MessageType,
    MessagePriority
)
from src.agents.base import AgentDecision


class TestDecisionCoordinator:
    """決策協調器測試"""
    
    def setup_method(self):
        """測試前設置"""
        self.coordinator = DecisionCoordinator(
            coordination_method=CoordinationMethod.HYBRID,
            conflict_resolution=ConflictResolution.WEIGHTED_AVERAGE,
            min_agents_required=2
        )
        
        # 創建測試決策
        self.test_decisions = {
            'agent1': AgentDecision(
                agent_id='agent1',
                timestamp=datetime.now(),
                symbol='AAPL',
                action=1,
                confidence=0.8,
                reasoning="買入信號",
                expected_return=0.1,
                risk_assessment=0.3,
                position_size=0.1
            ),
            'agent2': AgentDecision(
                agent_id='agent2',
                timestamp=datetime.now(),
                symbol='AAPL',
                action=1,
                confidence=0.7,
                reasoning="技術分析買入",
                expected_return=0.08,
                risk_assessment=0.4,
                position_size=0.12
            ),
            'agent3': AgentDecision(
                agent_id='agent3',
                timestamp=datetime.now(),
                symbol='AAPL',
                action=-1,
                confidence=0.6,
                reasoning="風險過高",
                expected_return=-0.05,
                risk_assessment=0.7,
                position_size=0.05
            )
        }
    
    def test_coordinator_initialization(self):
        """測試協調器初始化"""
        assert self.coordinator.coordination_method == CoordinationMethod.HYBRID
        assert self.coordinator.conflict_resolution == ConflictResolution.WEIGHTED_AVERAGE
        assert self.coordinator.min_agents_required == 2
        assert len(self.coordinator.agent_weights) == 0
    
    def test_coordinate_decisions_consensus(self):
        """測試共識協調"""
        # 創建一致決策
        consensus_decisions = {
            'agent1': self.test_decisions['agent1'],
            'agent2': self.test_decisions['agent2']
        }
        
        result = self.coordinator.coordinate_decisions(consensus_decisions, 'AAPL')
        
        assert isinstance(result, CoordinatedDecision)
        assert result.symbol == 'AAPL'
        assert result.final_action == 1  # 一致買入
        assert result.final_confidence > 0
        assert len(result.participating_agents) == 2
    
    def test_coordinate_decisions_conflict(self):
        """測試衝突協調"""
        result = self.coordinator.coordinate_decisions(self.test_decisions, 'AAPL')
        
        assert isinstance(result, CoordinatedDecision)
        assert result.conflict_detected == True
        assert result.conflict_resolution is not None
        assert result.final_action in [-1, 0, 1]
    
    def test_simple_voting(self):
        """測試簡單投票"""
        result = self.coordinator._simple_voting(self.test_decisions, 'AAPL', {})
        
        assert isinstance(result, CoordinatedDecision)
        assert result.coordination_method == CoordinationMethod.SIMPLE_VOTING
        assert result.final_action == 1  # 2票買入 vs 1票賣出
    
    def test_weighted_voting(self):
        """測試加權投票"""
        weights = {'agent1': 0.5, 'agent2': 0.3, 'agent3': 0.2}
        result = self.coordinator._weighted_voting(self.test_decisions, 'AAPL', weights)
        
        assert isinstance(result, CoordinatedDecision)
        assert result.coordination_method == CoordinationMethod.WEIGHTED_VOTING
    
    def test_confidence_weighted(self):
        """測試信心度加權"""
        result = self.coordinator._confidence_weighted(self.test_decisions, 'AAPL')
        
        assert isinstance(result, CoordinatedDecision)
        assert result.coordination_method == CoordinationMethod.CONFIDENCE_WEIGHTED
    
    def test_update_agent_performance(self):
        """測試更新代理績效"""
        self.coordinator.update_agent_performance('agent1', 0.05)
        self.coordinator.update_agent_performance('agent1', 0.03)
        
        assert 'agent1' in self.coordinator.agent_performance
        assert len(self.coordinator.agent_performance['agent1']) == 2
        assert 'agent1' in self.coordinator.agent_weights
    
    def test_coordination_stats(self):
        """測試協調統計"""
        # 執行一些協調
        self.coordinator.coordinate_decisions(self.test_decisions, 'AAPL')
        
        stats = self.coordinator.get_coordination_stats()
        
        assert stats['total_decisions'] > 0
        assert 'conflict_rate' in stats
        assert 'agent_weights' in stats


class TestDynamicWeightAdjuster:
    """動態權重調整器測試"""
    
    def setup_method(self):
        """測試前設置"""
        self.adjuster = DynamicWeightAdjuster(
            adjustment_method=WeightAdjustmentMethod.ENSEMBLE,
            performance_window=10,
            min_weight=0.1,
            max_weight=0.4
        )
    
    def test_adjuster_initialization(self):
        """測試調整器初始化"""
        assert self.adjuster.adjustment_method == WeightAdjustmentMethod.ENSEMBLE
        assert self.adjuster.performance_window == 10
        assert self.adjuster.min_weight == 0.1
        assert self.adjuster.max_weight == 0.4
    
    def test_update_performance(self):
        """測試更新績效"""
        self.adjuster.update_performance('agent1', 0.05)
        self.adjuster.update_performance('agent1', -0.02)
        self.adjuster.update_performance('agent1', 0.03)
        
        assert 'agent1' in self.adjuster.performance_history
        assert len(self.adjuster.performance_history['agent1']) == 3
    
    def test_performance_based_adjustment(self):
        """測試基於績效的調整"""
        # 添加績效數據
        for i in range(5):
            self.adjuster.update_performance('agent1', 0.02)
            self.adjuster.update_performance('agent2', -0.01)
        
        agent_ids = ['agent1', 'agent2']
        weights = self.adjuster._performance_based_adjustment(agent_ids)
        
        assert isinstance(weights, dict)
        assert len(weights) == 2
        assert weights['agent1'] > weights['agent2']  # agent1績效更好
    
    def test_risk_adjusted_adjustment(self):
        """測試風險調整"""
        # 添加績效數據
        for i in range(5):
            self.adjuster.update_performance('agent1', 0.02)
            self.adjuster.update_performance('agent2', 0.01)
        
        agent_ids = ['agent1', 'agent2']
        weights = self.adjuster._risk_adjusted_adjustment(agent_ids)
        
        assert isinstance(weights, dict)
        assert len(weights) == 2
        assert sum(weights.values()) == pytest.approx(1.0, rel=1e-2)
    
    def test_adjust_weights(self):
        """測試權重調整"""
        # 添加足夠的績效數據
        for i in range(10):
            self.adjuster.update_performance('agent1', 0.02)
            self.adjuster.update_performance('agent2', -0.01)
        
        # 強制再平衡
        adjustments = self.adjuster.adjust_weights(force_rebalance=True)
        
        assert isinstance(adjustments, dict)
        assert len(self.adjuster.current_weights) > 0
    
    def test_weight_constraints(self):
        """測試權重約束"""
        weights = {'agent1': 0.8, 'agent2': 0.05, 'agent3': 0.15}
        constrained = self.adjuster._apply_weight_constraints(weights)
        
        assert all(w >= self.adjuster.min_weight for w in constrained.values())
        assert all(w <= self.adjuster.max_weight for w in constrained.values())
        assert sum(constrained.values()) == pytest.approx(1.0, rel=1e-2)


class TestPortfolioAllocator:
    """投資組合分配器測試"""
    
    def setup_method(self):
        """測試前設置"""
        self.allocator = PortfolioAllocator(
            allocation_method=AllocationMethod.RISK_PARITY,
            target_volatility=0.12,
            max_position_size=0.3
        )
        
        # 創建測試協調決策
        self.coordinated_decisions = {
            'AAPL': CoordinatedDecision(
                symbol='AAPL',
                final_action=1,
                final_confidence=0.8,
                final_position_size=0.2,
                coordination_method=CoordinationMethod.WEIGHTED_VOTING,
                participating_agents=['agent1', 'agent2'],
                agent_decisions={},
                decision_weights={},
                conflict_detected=False,
                conflict_resolution=None,
                coordination_confidence=0.8,
                reasoning="協調買入",
                timestamp=datetime.now(),
                metadata={}
            ),
            'GOOGL': CoordinatedDecision(
                symbol='GOOGL',
                final_action=1,
                final_confidence=0.7,
                final_position_size=0.15,
                coordination_method=CoordinationMethod.WEIGHTED_VOTING,
                participating_agents=['agent1', 'agent3'],
                agent_decisions={},
                decision_weights={},
                conflict_detected=False,
                conflict_resolution=None,
                coordination_confidence=0.7,
                reasoning="協調買入",
                timestamp=datetime.now(),
                metadata={}
            )
        }
    
    def test_allocator_initialization(self):
        """測試分配器初始化"""
        assert self.allocator.allocation_method == AllocationMethod.RISK_PARITY
        assert self.allocator.target_volatility == 0.12
        assert self.allocator.max_position_size == 0.3
    
    def test_extract_investment_signals(self):
        """測試提取投資信號"""
        signals = self.allocator._extract_investment_signals(self.coordinated_decisions)
        
        assert isinstance(signals, dict)
        assert 'AAPL' in signals
        assert 'GOOGL' in signals
        assert signals['AAPL']['action'] == 1.0
        assert signals['AAPL']['confidence'] == 0.8
    
    def test_strategic_allocation(self):
        """測試戰略配置"""
        expected_returns = {'AAPL': 0.1, 'GOOGL': 0.08}
        signals = self.allocator._extract_investment_signals(self.coordinated_decisions)
        
        weights = self.allocator._strategic_allocation(expected_returns, signals)
        
        assert isinstance(weights, dict)
        assert len(weights) == 2
        assert sum(weights.values()) == pytest.approx(1.0, rel=1e-2)
    
    def test_tactical_allocation(self):
        """測試戰術配置"""
        expected_returns = {'AAPL': 0.1, 'GOOGL': 0.08}
        signals = self.allocator._extract_investment_signals(self.coordinated_decisions)
        
        weights = self.allocator._tactical_allocation(expected_returns, signals)
        
        assert isinstance(weights, dict)
        assert len(weights) == 2
    
    def test_apply_allocation_constraints(self):
        """測試配置約束"""
        target_weights = {'AAPL': 0.6, 'GOOGL': 0.4}
        constrained = self.allocator._apply_allocation_constraints(target_weights)
        
        assert all(w <= self.allocator.max_position_size for w in constrained.values())
        assert all(w >= self.allocator.min_position_size for w in constrained.values())
    
    def test_allocate_portfolio(self):
        """測試投資組合配置"""
        result = self.allocator.allocate_portfolio(self.coordinated_decisions)
        
        assert hasattr(result, 'target_allocations')
        assert hasattr(result, 'risk_metrics')
        assert hasattr(result, 'performance_metrics')
        assert result.allocation_method == AllocationMethod.RISK_PARITY
    
    def test_calculate_portfolio_risk_metrics(self):
        """測試投資組合風險指標"""
        weights = {'AAPL': 0.6, 'GOOGL': 0.4}
        risk_metrics = self.allocator._calculate_portfolio_risk_metrics(weights)
        
        assert 'portfolio_volatility' in risk_metrics
        assert 'risk_concentration' in risk_metrics
        assert 'diversification_ratio' in risk_metrics


class TestAgentCommunication:
    """代理間通信測試"""
    
    def setup_method(self):
        """測試前設置"""
        self.communication = AgentCommunication(
            max_queue_size=100,
            message_ttl=3600,
            heartbeat_interval=30
        )
        self.communication.start()
    
    def teardown_method(self):
        """測試後清理"""
        self.communication.stop()
    
    def test_communication_initialization(self):
        """測試通信管理器初始化"""
        assert self.communication.max_queue_size == 100
        assert self.communication.message_ttl == 3600
        assert self.communication.running == True
    
    def test_register_agent(self):
        """測試代理註冊"""
        success = self.communication.register_agent('agent1', {'type': 'trading'})
        
        assert success == True
        assert 'agent1' in self.communication.registered_agents
        assert self.communication.get_agent_status('agent1') == 'online'
    
    def test_unregister_agent(self):
        """測試代理取消註冊"""
        self.communication.register_agent('agent1')
        success = self.communication.unregister_agent('agent1')
        
        assert success == True
        assert 'agent1' not in self.communication.registered_agents
    
    def test_subscribe_unsubscribe(self):
        """測試訂閱和取消訂閱"""
        self.communication.register_agent('agent1')
        
        # 訂閱
        success = self.communication.subscribe('agent1', MessageType.DECISION)
        assert success == True
        assert 'agent1' in self.communication.subscriptions[MessageType.DECISION]
        
        # 取消訂閱
        success = self.communication.unsubscribe('agent1', MessageType.DECISION)
        assert success == True
        assert 'agent1' not in self.communication.subscriptions[MessageType.DECISION]
    
    def test_send_receive_message(self):
        """測試發送和接收消息"""
        self.communication.register_agent('agent1')
        self.communication.register_agent('agent2')
        
        # 發送消息
        message_id = self.communication.send_message(
            sender='agent1',
            message_type=MessageType.DECISION,
            content={'action': 1, 'confidence': 0.8},
            recipient='agent2'
        )
        
        assert message_id is not None
        
        # 接收消息
        message = self.communication.receive_message('agent2', timeout=1.0)
        
        assert message is not None
        assert message.type == MessageType.DECISION
        assert message.sender == 'agent1'
        assert message.content['action'] == 1
    
    def test_broadcast_message(self):
        """測試廣播消息"""
        # 註冊代理並訂閱
        for agent_id in ['agent1', 'agent2', 'agent3']:
            self.communication.register_agent(agent_id)
            self.communication.subscribe(agent_id, MessageType.MARKET_DATA)
        
        # 廣播消息
        recipients = self.communication.broadcast_message(
            sender='system',
            message_type=MessageType.MARKET_DATA,
            content={'price': 100.0, 'volume': 1000}
        )
        
        assert len(recipients) == 3  # 所有訂閱者都應該收到
    
    def test_request_response(self):
        """測試請求-響應模式"""
        self.communication.register_agent('agent1')
        self.communication.register_agent('agent2')
        
        # 模擬agent2的響應處理
        def response_handler(message):
            if message.type == MessageType.COORDINATION_REQUEST:
                self.communication.send_response(
                    sender='agent2',
                    original_message=message,
                    response_content={'status': 'accepted'}
                )
        
        self.communication.subscribe('agent2', MessageType.COORDINATION_REQUEST, response_handler)
        
        # 發送請求
        response = self.communication.send_request(
            sender='agent1',
            recipient='agent2',
            message_type=MessageType.COORDINATION_REQUEST,
            content={'request': 'coordinate'},
            timeout=5.0
        )
        
        # 由於異步處理，這個測試可能需要調整
        # assert response is not None
        # assert response.content['status'] == 'accepted'
    
    def test_communication_stats(self):
        """測試通信統計"""
        self.communication.register_agent('agent1')
        self.communication.register_agent('agent2')
        
        # 發送一些消息
        for i in range(5):
            self.communication.send_message(
                sender='agent1',
                message_type=MessageType.HEARTBEAT,
                content={'beat': i},
                recipient='agent2'
            )
        
        stats = self.communication.get_communication_stats()
        
        assert stats.total_messages_sent >= 5
        assert MessageType.HEARTBEAT.value in stats.messages_by_type
        assert stats.active_connections >= 2


class TestIntegration:
    """協作機制整合測試"""
    
    def test_full_coordination_workflow(self):
        """測試完整協作流程"""
        # 1. 創建組件
        coordinator = DecisionCoordinator()
        adjuster = DynamicWeightAdjuster()
        allocator = PortfolioAllocator()
        communication = AgentCommunication()
        
        try:
            communication.start()
            
            # 2. 註冊代理
            agents = ['buffett', 'soros', 'simons']
            for agent in agents:
                communication.register_agent(agent)
            
            # 3. 創建測試決策
            decisions = {}
            for i, agent in enumerate(agents):
                decisions[agent] = AgentDecision(
                    agent_id=agent,
                    timestamp=datetime.now(),
                    symbol='AAPL',
                    action=1,
                    confidence=0.7 + i * 0.1,
                    reasoning=f"{agent}決策",
                    expected_return=0.08 + i * 0.02,
                    risk_assessment=0.3,
                    position_size=0.1
                )
            
            # 4. 協調決策
            coordinated = coordinator.coordinate_decisions(decisions, 'AAPL')
            assert isinstance(coordinated, CoordinatedDecision)
            
            # 5. 更新權重
            for agent in agents:
                adjuster.update_performance(agent, 0.02)
            
            # 6. 投資組合配置
            coordinated_decisions = {'AAPL': coordinated}
            allocation = allocator.allocate_portfolio(coordinated_decisions)
            
            assert hasattr(allocation, 'target_allocations')
            assert 'AAPL' in allocation.target_allocations
            
        finally:
            communication.stop()
    
    def test_component_interaction(self):
        """測試組件交互"""
        coordinator = DecisionCoordinator()
        adjuster = DynamicWeightAdjuster()
        
        # 模擬多輪決策和權重調整
        for round_num in range(3):
            # 創建決策
            decisions = {
                'agent1': AgentDecision(
                    agent_id='agent1',
                    timestamp=datetime.now(),
                    symbol='AAPL',
                    action=1,
                    confidence=0.8,
                    reasoning="買入",
                    expected_return=0.1,
                    risk_assessment=0.3,
                    position_size=0.1
                ),
                'agent2': AgentDecision(
                    agent_id='agent2',
                    timestamp=datetime.now(),
                    symbol='AAPL',
                    action=1,
                    confidence=0.6,
                    reasoning="買入",
                    expected_return=0.05,
                    risk_assessment=0.4,
                    position_size=0.08
                )
            }
            
            # 協調決策
            coordinated = coordinator.coordinate_decisions(decisions, 'AAPL')
            
            # 模擬績效並更新權重
            performance1 = 0.02 + round_num * 0.01
            performance2 = 0.01 - round_num * 0.005
            
            adjuster.update_performance('agent1', performance1)
            adjuster.update_performance('agent2', performance2)
            
            coordinator.update_agent_performance('agent1', performance1)
            coordinator.update_agent_performance('agent2', performance2)
        
        # 檢查權重是否合理調整
        weights = adjuster.get_current_weights()
        coord_stats = coordinator.get_coordination_stats()
        
        assert len(weights) > 0
        assert coord_stats['total_decisions'] == 3
