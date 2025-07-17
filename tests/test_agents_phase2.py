# -*- coding: utf-8 -*-
"""
多代理系統Phase 2測試套件

此模組包含Phase 2投資風格代理的測試。

測試範圍：
- 價值投資代理
- 技術分析代理
- 動量交易代理
- 套利交易代理
- 風險平價代理
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# 導入被測試的模組
from src.agents.styles import (
    ValueInvestor,
    TechnicalTrader,
    MomentumTrader,
    ArbitrageTrader,
    RiskParityAgent,
)
from src.agents import InvestmentStyle, RiskPreference, AgentDecision


class TestValueInvestor:
    """價值投資代理測試"""
    
    def setup_method(self):
        """測試前設置"""
        self.agent = ValueInvestor(
            name="TestValueInvestor",
            pe_threshold=15.0,
            pb_threshold=1.5,
            roe_threshold=0.15
        )
        
        # 創建測試數據
        self.test_data = pd.DataFrame({
            'close': [100, 101, 102, 101, 103],
            'pe_ratio': [12.0, 12.1, 12.2, 12.0, 12.3],
            'pb_ratio': [1.2, 1.21, 1.22, 1.20, 1.23],
            'roe': [0.18, 0.18, 0.19, 0.18, 0.19],
            'debt_ratio': [0.3, 0.31, 0.30, 0.29, 0.30],
            'dividend_yield': [0.03, 0.03, 0.03, 0.03, 0.03],
            'revenue_growth': [0.1, 0.1, 0.11, 0.1, 0.11],
            'earnings_growth': [0.12, 0.12, 0.13, 0.12, 0.13]
        })
    
    def test_agent_initialization(self):
        """測試代理初始化"""
        assert self.agent.name == "TestValueInvestor"
        assert self.agent.investment_style == InvestmentStyle.VALUE
        assert self.agent.risk_preference == RiskPreference.CONSERVATIVE
        assert self.agent.pe_threshold == 15.0
        assert self.agent.pb_threshold == 1.5
        assert self.agent.roe_threshold == 0.15
    
    def test_make_decision(self):
        """測試決策生成"""
        decision = self.agent.make_decision(
            self.test_data,
            market_context={'symbol': 'TEST'}
        )
        
        assert isinstance(decision, AgentDecision)
        assert decision.symbol == 'TEST'
        assert decision.action in [-1, 0, 1]
        assert 0 <= decision.confidence <= 1
        assert len(decision.reasoning) > 0
    
    def test_investment_philosophy(self):
        """測試投資哲學"""
        philosophy = self.agent.get_investment_philosophy()
        assert "價值投資" in philosophy
        assert "P/E" in philosophy
        assert "ROE" in philosophy


class TestTechnicalTrader:
    """技術分析代理測試"""
    
    def setup_method(self):
        """測試前設置"""
        self.agent = TechnicalTrader(
            name="TestTechnicalTrader",
            ma_short_period=5,
            ma_long_period=10,
            rsi_period=14
        )
        
        # 創建足夠的測試數據
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=50, freq='D')
        prices = 100 + np.cumsum(np.random.randn(50) * 0.02)
        volumes = 1000 + np.random.randint(-200, 200, 50)
        
        self.test_data = pd.DataFrame({
            'open': prices * 0.99,
            'high': prices * 1.02,
            'low': prices * 0.98,
            'close': prices,
            'volume': volumes
        }, index=dates)
    
    def test_agent_initialization(self):
        """測試代理初始化"""
        assert self.agent.name == "TestTechnicalTrader"
        assert self.agent.investment_style == InvestmentStyle.TECHNICAL
        assert self.agent.risk_preference == RiskPreference.MODERATE
        assert self.agent.ma_short_period == 5
        assert self.agent.ma_long_period == 10
    
    def test_make_decision(self):
        """測試決策生成"""
        decision = self.agent.make_decision(
            self.test_data,
            market_context={'symbol': 'TEST'}
        )
        
        assert isinstance(decision, AgentDecision)
        assert decision.symbol == 'TEST'
        assert decision.action in [-1, 0, 1]
        assert 0 <= decision.confidence <= 1
    
    def test_technical_indicators(self):
        """測試技術指標計算"""
        indicators = self.agent._calculate_technical_indicators(self.test_data)
        
        assert 'ma_short' in indicators
        assert 'ma_long' in indicators
        assert 'rsi' in indicators
        assert 'macd_line' in indicators
        assert 'bb_upper' in indicators


class TestMomentumTrader:
    """動量交易代理測試"""
    
    def setup_method(self):
        """測試前設置"""
        self.agent = MomentumTrader(
            name="TestMomentumTrader",
            momentum_periods=[5, 10, 20],
            momentum_threshold=0.02
        )
        
        # 創建動量測試數據
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=80, freq='D')
        
        # 創建有明顯動量的價格序列
        trend = np.linspace(0, 0.3, 80)  # 上升趨勢
        noise = np.random.randn(80) * 0.01
        prices = 100 * np.exp(trend + noise)
        volumes = 1000 + np.random.randint(-200, 500, 80)
        
        self.test_data = pd.DataFrame({
            'open': prices * 0.99,
            'high': prices * 1.02,
            'low': prices * 0.98,
            'close': prices,
            'volume': volumes
        }, index=dates)
    
    def test_agent_initialization(self):
        """測試代理初始化"""
        assert self.agent.name == "TestMomentumTrader"
        assert self.agent.investment_style == InvestmentStyle.MOMENTUM
        assert self.agent.risk_preference == RiskPreference.AGGRESSIVE
        assert self.agent.momentum_periods == [5, 10, 20]
    
    def test_make_decision(self):
        """測試決策生成"""
        decision = self.agent.make_decision(
            self.test_data,
            market_context={'symbol': 'TEST'}
        )
        
        assert isinstance(decision, AgentDecision)
        assert decision.symbol == 'TEST'
        assert decision.action in [-1, 0, 1]
    
    def test_momentum_calculation(self):
        """測試動量計算"""
        metrics = self.agent._calculate_momentum_metrics(self.test_data)
        
        for period in self.agent.momentum_periods:
            assert f'price_momentum_{period}' in metrics
        assert 'volume_momentum' in metrics
        assert 'relative_strength' in metrics


class TestArbitrageTrader:
    """套利交易代理測試"""
    
    def setup_method(self):
        """測試前設置"""
        self.agent = ArbitrageTrader(
            name="TestArbitrageTrader",
            correlation_threshold=0.7,
            spread_entry_threshold=2.0
        )
        
        # 創建配對交易測試數據
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=80, freq='D')
        
        # 創建兩個相關的價格序列
        common_factor = np.cumsum(np.random.randn(80) * 0.01)
        prices1 = 100 + common_factor + np.random.randn(80) * 0.005
        prices2 = 50 + 0.5 * common_factor + np.random.randn(80) * 0.003
        
        self.test_data = pd.DataFrame({
            'STOCK1_close': prices1,
            'STOCK2_close': prices2,
        }, index=dates)
    
    def test_agent_initialization(self):
        """測試代理初始化"""
        assert self.agent.name == "TestArbitrageTrader"
        assert self.agent.investment_style == InvestmentStyle.ARBITRAGE
        assert self.agent.risk_preference == RiskPreference.CONSERVATIVE
        assert self.agent.correlation_threshold == 0.7
    
    def test_make_decision(self):
        """測試決策生成"""
        decision = self.agent.make_decision(
            self.test_data,
            market_context={'symbol': 'STOCK1', 'pair_symbol': 'STOCK2'}
        )
        
        assert isinstance(decision, AgentDecision)
        assert decision.symbol == 'STOCK1'
        assert decision.action in [-1, 0, 1]
    
    def test_pair_analysis(self):
        """測試配對分析"""
        analysis = self.agent._analyze_pair_relationship('STOCK1', 'STOCK2', self.test_data)
        
        assert 'correlation' in analysis
        assert 'hedge_ratio' in analysis
        assert 'spread_zscore' in analysis


class TestRiskParityAgent:
    """風險平價代理測試"""
    
    def setup_method(self):
        """測試前設置"""
        self.agent = RiskParityAgent(
            name="TestRiskParityAgent",
            lookback_period=30,
            min_weight=0.1,
            max_weight=0.4
        )
        
        # 創建多資產測試數據
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=80, freq='D')
        
        # 創建三個資產的價格數據
        returns1 = np.random.randn(80) * 0.01
        returns2 = np.random.randn(80) * 0.015
        returns3 = np.random.randn(80) * 0.008
        
        prices1 = 100 * np.exp(np.cumsum(returns1))
        prices2 = 200 * np.exp(np.cumsum(returns2))
        prices3 = 50 * np.exp(np.cumsum(returns3))
        
        self.test_data = pd.DataFrame({
            'ASSET1_close': prices1,
            'ASSET2_close': prices2,
            'ASSET3_close': prices3,
        }, index=dates)
        
        self.portfolio_assets = ['ASSET1', 'ASSET2', 'ASSET3']
    
    def test_agent_initialization(self):
        """測試代理初始化"""
        assert self.agent.name == "TestRiskParityAgent"
        assert self.agent.investment_style == InvestmentStyle.RISK_PARITY
        assert self.agent.risk_preference == RiskPreference.MODERATE
        assert self.agent.min_weight == 0.1
        assert self.agent.max_weight == 0.4
    
    def test_make_decision(self):
        """測試決策生成"""
        decision = self.agent.make_decision(
            self.test_data,
            market_context={
                'symbol': 'ASSET1',
                'portfolio_assets': self.portfolio_assets
            }
        )
        
        assert isinstance(decision, AgentDecision)
        assert decision.symbol == 'ASSET1'
        assert decision.action in [-1, 0, 1]
    
    def test_risk_model_estimation(self):
        """測試風險模型估計"""
        returns = self.agent._prepare_asset_data(self.test_data, self.portfolio_assets)
        risk_model = self.agent._estimate_risk_model(returns)
        
        assert 'covariance_matrix' in risk_model
        assert 'correlation_matrix' in risk_model
        assert 'volatilities' in risk_model
        assert 'expected_returns' in risk_model
    
    def test_weight_calculation(self):
        """測試權重計算"""
        returns = self.agent._prepare_asset_data(self.test_data, self.portfolio_assets)
        risk_model = self.agent._estimate_risk_model(returns)
        weights = self.agent._calculate_risk_parity_weights(risk_model)
        
        # 檢查權重約束
        for asset, weight in weights.items():
            assert self.agent.min_weight <= weight <= self.agent.max_weight
        
        # 檢查權重總和
        assert abs(sum(weights.values()) - 1.0) < 0.01


class TestIntegration:
    """投資風格代理整合測試"""
    
    def test_all_agents_creation(self):
        """測試所有代理創建"""
        agents = [
            ValueInvestor(),
            TechnicalTrader(),
            MomentumTrader(),
            ArbitrageTrader(),
            RiskParityAgent()
        ]
        
        assert len(agents) == 5
        
        # 檢查投資風格
        styles = [agent.investment_style for agent in agents]
        expected_styles = [
            InvestmentStyle.VALUE,
            InvestmentStyle.TECHNICAL,
            InvestmentStyle.MOMENTUM,
            InvestmentStyle.ARBITRAGE,
            InvestmentStyle.RISK_PARITY
        ]
        
        assert styles == expected_styles
    
    def test_agents_with_manager(self):
        """測試代理與管理器整合"""
        from src.agents import AgentManager
        
        manager = AgentManager()
        
        agents = [
            ValueInvestor(name="Value1"),
            TechnicalTrader(name="Tech1"),
            MomentumTrader(name="Momentum1")
        ]
        
        # 註冊代理
        for agent in agents:
            success = manager.register_agent(agent)
            assert success is True
        
        assert len(manager.agents) == 3
        assert manager.get_manager_status()['total_agents'] == 3
