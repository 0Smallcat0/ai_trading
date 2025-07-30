# -*- coding: utf-8 -*-
"""
簡化文本分析適配器 - MVP版本

提供基本的文本分析功能存根，用於維持UI兼容性。
此為簡化版本，移除了複雜的NLP功能。

Classes:
    TextAnalysisAdapter: 文本分析適配器存根

Example:
    >>> from src.nlp.text_analysis_adapter import TextAnalysisAdapter
    >>> adapter = TextAnalysisAdapter()
    >>> result = adapter.analyze_text("測試文本")
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TextAnalysisAdapter:
    """
    文本分析適配器存根 - MVP版本
    
    提供基本的文本分析功能存根，用於維持UI兼容性。
    """
    
    def __init__(self):
        """初始化文本分析適配器"""
        self.is_available = False
        logger.info("文本分析適配器已初始化 (MVP存根版本)")
    
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        分析文本 (存根實現)
        
        Args:
            text: 要分析的文本
            
        Returns:
            Dict[str, Any]: 分析結果
        """
        return {
            'sentiment': 'neutral',
            'confidence': 0.5,
            'keywords': [],
            'summary': '文本分析功能在MVP版本中暫不可用',
            'status': 'stub_implementation'
        }
    
    def get_sentiment(self, text: str) -> str:
        """
        獲取文本情感 (存根實現)
        
        Args:
            text: 要分析的文本
            
        Returns:
            str: 情感分析結果
        """
        return 'neutral'
    
    def extract_keywords(self, text: str) -> List[str]:
        """
        提取關鍵詞 (存根實現)
        
        Args:
            text: 要分析的文本
            
        Returns:
            List[str]: 關鍵詞列表
        """
        return []
    
    def summarize_text(self, text: str) -> str:
        """
        文本摘要 (存根實現)
        
        Args:
            text: 要摘要的文本
            
        Returns:
            str: 文本摘要
        """
        return "文本摘要功能在MVP版本中暫不可用"
    
    def is_service_available(self) -> bool:
        """
        檢查服務是否可用
        
        Returns:
            bool: 服務可用性
        """
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        獲取服務狀態
        
        Returns:
            Dict[str, Any]: 服務狀態信息
        """
        return {
            'available': False,
            'version': 'MVP-1.0',
            'type': 'stub_implementation',
            'message': 'NLP功能在MVP版本中已簡化'
        }
