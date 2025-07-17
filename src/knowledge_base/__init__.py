# -*- coding: utf-8 -*-
"""
金融量化知識庫管理模組

此模組提供完整的金融量化知識庫管理功能，包括：
- 知識資源掃描和整合
- 文檔內容解析和索引
- 智能搜索和推薦
- 學習路徑規劃
- 交互式學習支援

主要功能：
- 知識庫構建和維護
- 內容分類和標籤
- 搜索和檢索
- 學習進度追蹤
- 個性化推薦

技術特色：
- 多格式文檔支援
- 智能內容解析
- 語義搜索能力
- 學習分析功能
"""

# 版本信息
__version__ = "1.0.0"
__author__ = "Knowledge Base Team"
__description__ = "金融量化知識庫管理系統"

# 核心組件導入
from .knowledge_manager import KnowledgeManager
from .content_parser import ContentParser
from .search_engine import SearchEngine
from .learning_tracker import LearningTracker

# 學習模組
from .concept_explainer import ConceptExplainer
from .strategy_simulator import StrategySimulator
from .risk_educator import RiskEducator

# 工具組件
from .document_indexer import DocumentIndexer
from .content_classifier import ContentClassifier
from .recommendation_engine import RecommendationEngine

__all__ = [
    # 核心組件
    'KnowledgeManager',
    'ContentParser',
    'SearchEngine',
    'LearningTracker',
    
    # 學習模組
    'ConceptExplainer',
    'StrategySimulator',
    'RiskEducator',
    
    # 工具組件
    'DocumentIndexer',
    'ContentClassifier',
    'RecommendationEngine'
]
