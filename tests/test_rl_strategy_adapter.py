# -*- coding: utf-8 -*-
"""RL 策略適配器測試模組

此模組測試強化學習策略適配器的功能，包括：
- RLStrategyAdapter 基本功能測試
- 環境適配器測試
- 模型適配器測試
- RL 策略執行測試
- 錯誤處理測試

測試覆蓋：
- 單元測試：測試各個組件的獨立功能
- 整合測試：測試適配器與系統的整合
- 性能測試：測試 RL 策略的執行性能
- 錯誤測試：測試異常情況的處理
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.strategies.adapters import (
    RLStrategyAdapter,
    AdapterError,
)
from src.strategies.adapters.rl_strategy_adapter import (
    RLEnvironmentAdapter,
    RLModelAdapter,
)


class TestRLEnvironmentAdapter:
    """測試 RL 環境適配器"""
    
    def test_initialization(self):
        """測試初始化"""
        config = {
            'initial_balance': 100000,
            'max_steps': 1000
        }
        
        adapter = RLEnvironmentAdapter(config)
        
        assert adapter.config == config
        assert adapter.initial_balance == 100000
        assert adapter.max_steps == 1000
        assert adapter.env is None
    
    def test_create_environment(self):
        """測試環境創建"""
        config = {'initial_balance': 50000}
        adapter = RLEnvironmentAdapter(config)
        
        # 創建測試數據
        data = pd.DataFrame({
            'open': [100, 101, 102, 103, 104],
            'high': [102, 103, 104, 105, 106],
            'low': [99, 100, 101, 102, 103],
            'close': [101, 102, 103, 104, 105],
            'volume': [1000, 1100, 1200, 1300, 1400],
            'amount': [100000, 110000, 120000, 130000, 140000],
            'adjustflag': [1, 1, 1, 1, 1],
            'tradestatus': [1, 1, 1, 1, 1],
            'pctChg': [1.0, 1.0, 1.0, 1.0, 1.0],
            'peTTM': [15.0, 15.0, 15.0, 15.0, 15.0],
            'pbMRQ': [2.0, 2.0, 2.0, 2.0, 2.0],
            'psTTM': [3.0, 3.0, 3.0, 3.0, 3.0]
        })
        
        env = adapter.create_environment(data)
        
        assert env is not None
        assert adapter.observation_space is not None
        assert adapter.action_space is not None
        assert hasattr(env, 'reset')
        assert hasattr(env, 'step')


class TestRLModelAdapter:
    """測試 RL 模型適配器"""
    
    def test_initialization(self):
        """測試初始化"""
        adapter = RLModelAdapter('PPO')
        
        assert adapter.algorithm == 'PPO'
        assert adapter.model_path is None
        assert adapter.model is None
        assert adapter.is_trained is False
    
    def test_initialization_with_path(self):
        """測試帶模型路徑的初始化"""
        model_path = 'test_model.zip'
        adapter = RLModelAdapter('DQN', model_path)
        
        assert adapter.algorithm == 'DQN'
        assert adapter.model_path == model_path
    
    def test_load_model_mock(self):
        """測試模型載入（模擬版本）"""
        adapter = RLModelAdapter('PPO')
        
        # 創建模擬環境
        class MockEnv:
            def __init__(self):
                self.observation_space = None
                self.action_space = None
        
        env = MockEnv()
        model = adapter.load_model(env)
        
        assert model is not None
        assert adapter.model is not None
        assert hasattr(model, 'predict')
    
    def test_predict(self):
        """測試預測功能"""
        adapter = RLModelAdapter('PPO')
        
        # 載入模擬模型
        class MockEnv:
            pass
        
        model = adapter.load_model(MockEnv())
        
        # 測試預測
        observation = np.random.random(19).astype(np.float32)
        action, states = adapter.predict(observation)
        
        assert action is not None
        assert len(action) == 2
        assert isinstance(action, np.ndarray)


class TestRLStrategyAdapter:
    """測試 RL 策略適配器"""
    
    @pytest.fixture
    def sample_data(self):
        """創建測試數據"""
        dates = pd.date_range('2023-01-01', periods=50)
        prices = 100 + np.cumsum(np.random.randn(50) * 0.01)
        
        return pd.DataFrame({
            'date': dates,
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.randint(1000, 5000, 50),
            'amount': np.random.randint(100000, 500000, 50),
            'adjustflag': [1] * 50,
            'tradestatus': [1] * 50,
            'pctChg': np.random.randn(50),
            'peTTM': np.random.uniform(10, 20, 50),
            'pbMRQ': np.random.uniform(1, 3, 50),
            'psTTM': np.random.uniform(2, 4, 50)
        })
    
    def test_initialization(self):
        """測試初始化"""
        adapter = RLStrategyAdapter(
            algorithm='PPO',
            environment_config={'initial_balance': 100000}
        )
        
        assert adapter.name == "RLStrategy_PPO"
        assert adapter.algorithm == 'PPO'
        assert adapter.environment_config['initial_balance'] == 100000
        assert adapter.env_adapter is None
        assert adapter.model_adapter is None
    
    def test_parameter_validation(self):
        """測試參數驗證"""
        # 測試無效算法
        with pytest.raises(Exception):  # ParameterError
            RLStrategyAdapter(algorithm='INVALID_ALGO')
        
        # 測試無效環境配置
        with pytest.raises(Exception):  # ParameterError
            RLStrategyAdapter(environment_config="invalid_config")
    
    def test_load_legacy_strategy(self):
        """測試載入原始策略"""
        adapter = RLStrategyAdapter(algorithm='PPO')
        adapter._load_legacy_strategy()
        
        assert adapter.env_adapter is not None
        assert adapter.model_adapter is not None
        assert isinstance(adapter.env_adapter, RLEnvironmentAdapter)
        assert isinstance(adapter.model_adapter, RLModelAdapter)
    
    def test_generate_signals(self, sample_data):
        """測試訊號生成"""
        adapter = RLStrategyAdapter(
            algorithm='PPO',
            environment_config={'initial_balance': 100000}
        )
        
        signals = adapter.generate_signals(sample_data)
        
        # 驗證結果格式
        assert isinstance(signals, pd.DataFrame)
        assert 'signal' in signals.columns
        assert 'buy_signal' in signals.columns
        assert 'sell_signal' in signals.columns
        assert len(signals) == len(sample_data)
        
        # 驗證訊號值
        assert signals['buy_signal'].isin([0, 1]).all()
        assert signals['sell_signal'].isin([0, 1]).all()
    
    def test_train_model(self, sample_data):
        """測試模型訓練"""
        adapter = RLStrategyAdapter(
            algorithm='PPO',
            environment_config={'initial_balance': 100000}
        )
        
        # 測試訓練
        training_stats = adapter.train_model(sample_data, total_timesteps=100)
        
        assert isinstance(training_stats, dict)
        assert 'algorithm' in training_stats
        assert 'total_timesteps' in training_stats
        assert 'training_data_length' in training_stats
        assert training_stats['algorithm'] == 'PPO'
        assert training_stats['total_timesteps'] == 100
        assert training_stats['training_data_length'] == len(sample_data)
    
    def test_strategy_info(self):
        """測試策略資訊"""
        adapter = RLStrategyAdapter(
            algorithm='DQN',
            model_path='test_model.zip',
            environment_config={'initial_balance': 50000}
        )
        
        info = adapter.get_strategy_info()
        
        assert info['name'] == "RLStrategy_DQN"
        assert info['type'] == 'Reinforcement Learning'
        assert info['category'] == 'RL'
        assert info['algorithm'] == 'DQN'
        assert info['parameters']['model_path'] == 'test_model.zip'
        assert info['parameters']['environment_config']['initial_balance'] == 50000
    
    def test_convert_parameters(self):
        """測試參數轉換"""
        adapter = RLStrategyAdapter(algorithm='SAC')
        
        converted = adapter._convert_parameters(
            algorithm='PPO',
            environment_config={'initial_balance': 200000}
        )
        
        assert converted['algorithm'] == 'PPO'
        assert converted['environment_config']['initial_balance'] == 200000
    
    def test_multiple_algorithms(self, sample_data):
        """測試多種算法"""
        algorithms = ['PPO', 'DQN', 'SAC']
        
        for algo in algorithms:
            adapter = RLStrategyAdapter(algorithm=algo)
            
            # 測試基本功能
            assert adapter.algorithm == algo
            assert adapter.name == f"RLStrategy_{algo}"
            
            # 測試訊號生成
            signals = adapter.generate_signals(sample_data)
            assert isinstance(signals, pd.DataFrame)
            assert len(signals) == len(sample_data)


class TestRLIntegration:
    """RL 整合測試"""
    
    @pytest.fixture
    def sample_data(self):
        """創建測試數據"""
        dates = pd.date_range('2023-01-01', periods=100)
        prices = 100 + np.cumsum(np.random.randn(100) * 0.01)
        
        return pd.DataFrame({
            'date': dates,
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.randint(1000, 5000, 100),
            'amount': np.random.randint(100000, 500000, 100),
            'adjustflag': [1] * 100,
            'tradestatus': [1] * 100,
            'pctChg': np.random.randn(100),
            'peTTM': np.random.uniform(10, 20, 100),
            'pbMRQ': np.random.uniform(1, 3, 100),
            'psTTM': np.random.uniform(2, 4, 100)
        })
    
    def test_multiple_rl_strategies(self, sample_data):
        """測試多個 RL 策略同時使用"""
        # 創建多個 RL 適配器
        ppo_adapter = RLStrategyAdapter(algorithm='PPO')
        dqn_adapter = RLStrategyAdapter(algorithm='DQN')
        
        # 生成訊號
        ppo_signals = ppo_adapter.generate_signals(sample_data)
        dqn_signals = dqn_adapter.generate_signals(sample_data)
        
        # 驗證結果
        assert len(ppo_signals) == len(sample_data)
        assert len(dqn_signals) == len(sample_data)
        assert 'signal' in ppo_signals.columns
        assert 'signal' in dqn_signals.columns
    
    def test_rl_with_other_strategies(self, sample_data):
        """測試 RL 策略與其他策略的協作"""
        from src.strategies.adapters import DoubleMaAdapter
        
        # 創建不同類型的策略
        rl_adapter = RLStrategyAdapter(algorithm='PPO')
        ma_adapter = DoubleMaAdapter(short_window=5, long_window=20)
        
        # 生成訊號
        rl_signals = rl_adapter.generate_signals(sample_data)
        ma_signals = ma_adapter.generate_signals(sample_data)
        
        # 驗證結果
        assert len(rl_signals) == len(ma_signals)
        assert 'signal' in rl_signals.columns
        assert 'signal' in ma_signals.columns
    
    def test_performance_comparison(self, sample_data):
        """測試性能比較"""
        adapters = [
            ('PPO', RLStrategyAdapter(algorithm='PPO')),
            ('DQN', RLStrategyAdapter(algorithm='DQN')),
        ]
        
        results = {}
        for name, adapter in adapters:
            signals = adapter.generate_signals(sample_data)
            metrics = adapter.evaluate(sample_data, signals)
            results[name] = metrics
        
        # 驗證所有適配器都能正常執行
        assert len(results) == 2
        for name, metrics in results.items():
            assert isinstance(metrics, dict)
            assert 'total_return' in metrics


if __name__ == '__main__':
    # 運行測試
    pytest.main([__file__, '-v'])
