# -*- coding: utf-8 -*-
"""
簡化新聞分類器 - MVP版本

提供基本的新聞分類功能存根，用於維持UI兼容性。
此為簡化版本，移除了複雜的分類功能。

Classes:
    NewsCategory: 新聞分類枚舉
    NewsClassifier: 新聞分類器存根

Example:
    >>> from src.nlp.news_classifier import NewsCategory, NewsClassifier
    >>> classifier = NewsClassifier()
    >>> category = classifier.classify_news("新聞內容")
"""

from enum import Enum
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class NewsCategory(Enum):
    """
    新聞分類枚舉
    """
    GENERAL = "general"
    TECHNOLOGY = "technology"
    FINANCE = "finance"
    POLITICS = "politics"
    SPORTS = "sports"
    ENTERTAINMENT = "entertainment"
    HEALTH = "health"
    SCIENCE = "science"
    BUSINESS = "business"
    UNKNOWN = "unknown"


class NewsClassifier:
    """
    新聞分類器存根 - MVP版本
    
    提供基本的新聞分類功能存根，用於維持UI兼容性。
    """
    
    def __init__(self):
        """初始化新聞分類器"""
        self.is_available = False
        self.categories = list(NewsCategory)
        logger.info("新聞分類器已初始化 (MVP存根版本)")
    
    def classify_news(self, text: str) -> NewsCategory:
        """
        分類新聞 (存根實現)
        
        Args:
            text: 新聞文本
            
        Returns:
            NewsCategory: 新聞分類
        """
        return NewsCategory.GENERAL
    
    def classify_with_confidence(self, text: str) -> Dict[str, Any]:
        """
        分類新聞並返回置信度 (存根實現)
        
        Args:
            text: 新聞文本
            
        Returns:
            Dict[str, Any]: 分類結果和置信度
        """
        return {
            'category': NewsCategory.GENERAL.value,
            'confidence': 0.5,
            'all_scores': {category.value: 0.1 for category in NewsCategory}
        }
    
    def get_available_categories(self) -> List[str]:
        """
        獲取可用分類列表
        
        Returns:
            List[str]: 分類列表
        """
        return [category.value for category in NewsCategory]
    
    def batch_classify(self, texts: List[str]) -> List[NewsCategory]:
        """
        批量分類新聞 (存根實現)
        
        Args:
            texts: 新聞文本列表
            
        Returns:
            List[NewsCategory]: 分類結果列表
        """
        return [NewsCategory.GENERAL] * len(texts)
    
    def is_service_available(self) -> bool:
        """
        檢查服務是否可用
        
        Returns:
            bool: 服務可用性
        """
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        獲取分類器狀態
        
        Returns:
            Dict[str, Any]: 分類器狀態信息
        """
        return {
            'available': False,
            'version': 'MVP-1.0',
            'type': 'stub_implementation',
            'categories_count': len(self.categories),
            'message': '新聞分類功能在MVP版本中已簡化'
        }
