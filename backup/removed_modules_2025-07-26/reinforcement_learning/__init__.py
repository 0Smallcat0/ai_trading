# -*- coding: utf-8 -*-
"""
強化學習模組

此模組提供完整的強化學習交易解決方案，包括：
- TradeMaster框架整合
- 多種RL算法支持
- 自適應學習能力
- 與多代理系統整合

主要功能：
- 環境管理：多種交易環境
- 代理管理：多種RL算法
- 訓練管理：完整訓練流程
- 部署管理：模型服務化
- 自適應學習：在線學習和概念漂移檢測

技術特色：
- 基於TradeMaster專業框架
- 支援Stable-Baselines3算法庫
- 模組化和可擴展設計
- 與現有系統無縫整合
"""

# 版本信息
__version__ = "1.0.0"
__author__ = "RL Integration Team"
__description__ = "強化學習交易系統整合模組"

# 核心組件導入
from .core.base_env import BaseEnvironment
from .core.base_agent import BaseRLAgent
from .core.base_trainer import BaseTrainer

# 環境組件
from .environments.stock_trading_env import StockTradingEnvironment
from .environments.portfolio_env import PortfolioEnvironment

# 代理組件
from .agents.ppo_agent import PPOAgent
from .agents.dqn_agent import DQNAgent

# 訓練組件
from .training.trainer import RLTrainer
from .training.evaluator import RLEvaluator

# 部署組件
from .deployment.model_server import ModelServer
from .deployment.inference_engine import InferenceEngine

# 自適應學習組件
from .adaptive.online_learner import OnlineLearner
from .adaptive.drift_detector import ConceptDriftDetector

# 整合組件
from .trademaster_integration import TradeMasterIntegration
from .rl_training_pipeline import RLTrainingPipeline
from .rl_deployment import RLDeploymentManager
from .adaptive_learning import AdaptiveLearningManager

__all__ = [
    # 核心組件
    'BaseEnvironment',
    'BaseRLAgent', 
    'BaseTrainer',
    
    # 環境組件
    'StockTradingEnvironment',
    'PortfolioEnvironment',
    
    # 代理組件
    'PPOAgent',
    'DQNAgent',
    
    # 訓練組件
    'RLTrainer',
    'RLEvaluator',
    
    # 部署組件
    'ModelServer',
    'InferenceEngine',
    
    # 自適應學習組件
    'OnlineLearner',
    'ConceptDriftDetector',
    
    # 整合組件
    'TradeMasterIntegration',
    'RLTrainingPipeline',
    'RLDeploymentManager',
    'AdaptiveLearningManager'
]
