# -*- coding: utf-8 -*-
"""
角色扮演代理Phase 3測試套件

此模組包含Phase 3角色扮演代理的測試。

測試範圍：
- 巴菲特代理（BuffettAgent）
- 索羅斯代理（SorosAgent）
- 西蒙斯代理（SimonsAgent）
- 達里奧代理（DalioAgent）
- 格雷厄姆代理（GrahamAgent）
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# 導入被測試的模組
from src.agents.personas import (
    BuffettAgent,
    SorosAgent,
    SimonsAgent,
    DalioAgent,
    GrahamAgent,
)
from src.agents import InvestmentStyle, RiskPreference, AgentDecision


class TestBuffettAgent:
    """巴菲特代理測試"""
    
    def setup_method(self):
        """測試前設置"""
        self.agent = BuffettAgent(
            name="TestBuffett",
            min_holding_years=2,
            concentration_threshold=0.2
        )
        
        # 創建測試數據
        self.test_data = pd.DataFrame({
            'close': [100, 101, 102, 101, 103],
            'pe_ratio': [12.0, 12.1, 12.2, 12.0, 12.3],
            'pb_ratio': [1.2, 1.21, 1.22, 1.20, 1.23],
            'roe': [0.18, 0.18, 0.19, 0.18, 0.19],
            'debt_ratio': [0.3, 0.31, 0.30, 0.29, 0.30],
            'dividend_yield': [0.03, 0.03, 0.03, 0.03, 0.03],
            'market_cap': [50_000_000_000] * 5,
            'free_cash_flow': [5_000_000_000] * 5,
            'revenue': [20_000_000_000] * 5,
            'revenue_stability': [0.9] * 5
        })
    
    def test_agent_initialization(self):
        """測試代理初始化"""
        assert self.agent.name == "TestBuffett"
        assert self.agent.investment_style == InvestmentStyle.VALUE
        assert self.agent.risk_preference == RiskPreference.CONSERVATIVE
        assert self.agent.min_holding_years == 2
        assert self.agent.concentration_threshold == 0.2
    
    def test_make_decision(self):
        """測試決策生成"""
        decision = self.agent.make_decision(
            self.test_data,
            market_context={'symbol': 'BRK.A', 'sector': 'financial_services'}
        )
        
        assert isinstance(decision, AgentDecision)
        assert decision.symbol == 'BRK.A'
        assert decision.action in [-1, 0, 1]
        assert 0 <= decision.confidence <= 1
        assert "巴菲特" in decision.reasoning
    
    def test_investment_philosophy(self):
        """測試投資哲學"""
        philosophy = self.agent.get_investment_philosophy()
        assert "巴菲特" in philosophy
        assert "護城河" in philosophy
        assert "長期" in philosophy
    
    def test_buffett_insights(self):
        """測試巴菲特智慧"""
        insights = self.agent.get_buffett_insights()
        assert len(insights) > 0
        assert any("規則一" in insight for insight in insights)


class TestSorosAgent:
    """索羅斯代理測試"""
    
    def setup_method(self):
        """測試前設置"""
        self.agent = SorosAgent(
            name="TestSoros",
            reflexivity_sensitivity=0.7,
            max_leverage=2.0
        )
        
        # 創建測試數據
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=50, freq='D')
        prices = 100 + np.cumsum(np.random.randn(50) * 0.02)
        volumes = 1000 + np.random.randint(-200, 200, 50)
        
        self.test_data = pd.DataFrame({
            'open': prices * 0.99,
            'high': prices * 1.02,
            'low': prices * 0.98,
            'close': prices,
            'volume': volumes,
            'pe_ratio': [15.0] * 50
        }, index=dates)
    
    def test_agent_initialization(self):
        """測試代理初始化"""
        assert self.agent.name == "TestSoros"
        assert self.agent.investment_style == InvestmentStyle.ARBITRAGE
        assert self.agent.risk_preference == RiskPreference.AGGRESSIVE
        assert self.agent.reflexivity_sensitivity == 0.7
        assert self.agent.max_leverage == 2.0
    
    def test_make_decision(self):
        """測試決策生成"""
        decision = self.agent.make_decision(
            self.test_data,
            market_context={
                'symbol': 'GBP/USD',
                'gdp_growth': 0.02,
                'inflation_rate': 0.03,
                'interest_rates': 0.05
            }
        )
        
        assert isinstance(decision, AgentDecision)
        assert decision.symbol == 'GBP/USD'
        assert decision.action in [-1, 0, 1]
        assert "索羅斯" in decision.reasoning
    
    def test_soros_insights(self):
        """測試索羅斯智慧"""
        insights = self.agent.get_soros_insights()
        assert len(insights) > 0
        assert any("市場總是錯的" in insight for insight in insights)


class TestSimonsAgent:
    """西蒙斯代理測試"""
    
    def setup_method(self):
        """測試前設置"""
        self.agent = SimonsAgent(
            name="TestSimons",
            model_complexity=50,
            feature_count=20
        )
        
        # 創建足夠的測試數據
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=150, freq='D')
        prices = 100 + np.cumsum(np.random.randn(150) * 0.01)
        volumes = 1000 + np.random.randint(-200, 200, 150)
        
        self.test_data = pd.DataFrame({
            'open': prices * 0.995,
            'high': prices * 1.01,
            'low': prices * 0.99,
            'close': prices,
            'volume': volumes
        }, index=dates)
    
    def test_agent_initialization(self):
        """測試代理初始化"""
        assert self.agent.name == "TestSimons"
        assert self.agent.investment_style == InvestmentStyle.TECHNICAL
        assert self.agent.risk_preference == RiskPreference.MODERATE
        assert self.agent.model_complexity == 50
        assert self.agent.feature_count == 20
    
    def test_make_decision(self):
        """測試決策生成"""
        decision = self.agent.make_decision(
            self.test_data,
            market_context={'symbol': 'RENFX'}
        )
        
        assert isinstance(decision, AgentDecision)
        assert decision.symbol == 'RENFX'
        assert decision.action in [-1, 0, 1]
        assert "西蒙斯" in decision.reasoning
    
    def test_feature_engineering(self):
        """測試特徵工程"""
        features = self.agent._engineer_features(self.test_data)
        assert len(features.columns) <= self.agent.feature_count
        assert 'returns_1d' in features.columns
        assert 'rsi_14' in features.columns
    
    def test_simons_insights(self):
        """測試西蒙斯智慧"""
        insights = self.agent.get_simons_insights()
        assert len(insights) > 0
        assert any("數學" in insight for insight in insights)


class TestDalioAgent:
    """達里奧代理測試"""
    
    def setup_method(self):
        """測試前設置"""
        self.agent = DalioAgent(
            name="TestDalio",
            economic_cycle_analysis=True,
            transparency_level=0.8
        )
        
        # 創建測試數據
        self.test_data = pd.DataFrame({
            'close': [100, 101, 102, 101, 103],
            'volume': [1000, 1100, 1200, 1050, 1150]
        })
        
        self.portfolio_assets = ['stocks', 'bonds', 'commodities', 'tips']
    
    def test_agent_initialization(self):
        """測試代理初始化"""
        assert self.agent.name == "TestDalio"
        assert self.agent.investment_style == InvestmentStyle.RISK_PARITY
        assert self.agent.risk_preference == RiskPreference.MODERATE
        assert self.agent.economic_cycle_analysis == True
        assert self.agent.transparency_level == 0.8
    
    def test_make_decision(self):
        """測試決策生成"""
        decision = self.agent.make_decision(
            self.test_data,
            market_context={
                'symbol': 'stocks',
                'portfolio_assets': self.portfolio_assets,
                'gdp_growth': 0.025,
                'inflation_rate': 0.02,
                'interest_rates': 0.03
            }
        )
        
        assert isinstance(decision, AgentDecision)
        assert decision.symbol == 'stocks'
        assert decision.action in [-1, 0, 1]
        assert "達里奧" in decision.reasoning
    
    def test_economic_season_identification(self):
        """測試經濟季節識別"""
        economic_analysis = {
            'gdp_growth': 0.03,
            'inflation_rate': 0.02
        }
        season_analysis = self.agent._identify_economic_season(economic_analysis)
        
        assert 'season' in season_analysis
        assert season_analysis['season'] in ['spring', 'summer', 'autumn', 'winter']
    
    def test_dalio_principles(self):
        """測試達里奧原則"""
        principles = self.agent.get_dalio_principles()
        assert len(principles) > 0
        assert any("透明度" in principle for principle in principles)


class TestGrahamAgent:
    """格雷厄姆代理測試"""
    
    def setup_method(self):
        """測試前設置"""
        self.agent = GrahamAgent(
            name="TestGraham",
            margin_of_safety_min=0.4,
            current_ratio_min=1.8
        )
        
        # 創建測試數據
        self.test_data = pd.DataFrame({
            'close': [100, 101, 102, 101, 103],
            'pe_ratio': [10.0, 10.1, 10.2, 10.0, 10.3],
            'pb_ratio': [1.0, 1.01, 1.02, 1.00, 1.03],
            'roe': [0.15, 0.15, 0.16, 0.15, 0.16],
            'debt_ratio': [0.2, 0.21, 0.20, 0.19, 0.20],
            'dividend_yield': [0.04, 0.04, 0.04, 0.04, 0.04],
            'current_assets': [2_000_000_000] * 5,
            'current_liabilities': [800_000_000] * 5,
            'total_debt': [1_000_000_000] * 5,
            'shareholders_equity': [4_000_000_000] * 5,
            'revenue': [10_000_000_000] * 5,
            'eps': [10.0] * 5,
            'book_value_per_share': [100.0] * 5,
            'shares_outstanding': [40_000_000] * 5,
            'price': [100, 101, 102, 101, 103]
        })
    
    def test_agent_initialization(self):
        """測試代理初始化"""
        assert self.agent.name == "TestGraham"
        assert self.agent.investment_style == InvestmentStyle.VALUE
        assert self.agent.risk_preference == RiskPreference.CONSERVATIVE
        assert self.agent.margin_of_safety_min == 0.4
        assert self.agent.current_ratio_min == 1.8
    
    def test_make_decision(self):
        """測試決策生成"""
        decision = self.agent.make_decision(
            self.test_data,
            market_context={'symbol': 'VALUE_STOCK'}
        )
        
        assert isinstance(decision, AgentDecision)
        assert decision.symbol == 'VALUE_STOCK'
        assert decision.action in [-1, 0, 1]
        assert "格雷厄姆" in decision.reasoning
    
    def test_graham_screening(self):
        """測試格雷厄姆篩選"""
        fundamentals = self.agent._extract_fundamentals(self.test_data)
        screening_result = self.agent._apply_graham_screening(fundamentals, None)
        
        assert 'passed' in screening_result
        assert 'screening_results' in screening_result
        assert isinstance(screening_result['passed'], bool)
    
    def test_graham_number_calculation(self):
        """測試格雷厄姆數字計算"""
        fundamentals = {
            'eps': 10.0,
            'book_value_per_share': 100.0
        }
        graham_number = self.agent._calculate_graham_number_value(fundamentals)
        
        expected = np.sqrt(22.5 * 10.0 * 100.0)
        assert abs(graham_number - expected) < 0.01
    
    def test_graham_insights(self):
        """測試格雷厄姆智慧"""
        insights = self.agent.get_graham_insights()
        assert len(insights) > 0
        assert any("本金" in insight for insight in insights)


class TestIntegration:
    """角色扮演代理整合測試"""
    
    def test_all_personas_creation(self):
        """測試所有角色代理創建"""
        agents = [
            BuffettAgent(name="Buffett"),
            SorosAgent(name="Soros"),
            SimonsAgent(name="Simons"),
            DalioAgent(name="Dalio"),
            GrahamAgent(name="Graham")
        ]
        
        assert len(agents) == 5
        
        # 檢查投資風格多樣性
        styles = [agent.investment_style for agent in agents]
        assert InvestmentStyle.VALUE in styles
        assert InvestmentStyle.ARBITRAGE in styles
        assert InvestmentStyle.TECHNICAL in styles
        assert InvestmentStyle.RISK_PARITY in styles
    
    def test_personas_with_manager(self):
        """測試角色代理與管理器整合"""
        from src.agents import AgentManager
        
        manager = AgentManager()
        
        agents = [
            BuffettAgent(name="Buffett1"),
            SorosAgent(name="Soros1"),
            SimonsAgent(name="Simons1"),
            DalioAgent(name="Dalio1"),
            GrahamAgent(name="Graham1")
        ]
        
        # 註冊代理
        for agent in agents:
            success = manager.register_agent(agent)
            assert success is True
        
        assert len(manager.agents) == 5
        assert manager.get_manager_status()['total_agents'] == 5
    
    def test_investment_philosophies(self):
        """測試投資哲學"""
        agents = [
            BuffettAgent(),
            SorosAgent(),
            SimonsAgent(),
            DalioAgent(),
            GrahamAgent()
        ]
        
        for agent in agents:
            philosophy = agent.get_investment_philosophy()
            assert len(philosophy) > 0
            assert isinstance(philosophy, str)
    
    def test_decision_consistency(self):
        """測試決策一致性"""
        # 創建標準測試數據
        test_data = pd.DataFrame({
            'open': [100] * 5,
            'high': [105] * 5,
            'low': [95] * 5,
            'close': [102] * 5,
            'volume': [1000] * 5,
            'pe_ratio': [15.0] * 5,
            'pb_ratio': [1.5] * 5,
            'roe': [0.15] * 5
        })
        
        agents = [
            BuffettAgent(),
            SorosAgent(),
            GrahamAgent()
        ]
        
        for agent in agents:
            decision = agent.make_decision(
                test_data,
                market_context={'symbol': 'TEST'}
            )
            
            # 檢查決策格式一致性
            assert hasattr(decision, 'action')
            assert hasattr(decision, 'confidence')
            assert hasattr(decision, 'reasoning')
            assert decision.symbol == 'TEST'
