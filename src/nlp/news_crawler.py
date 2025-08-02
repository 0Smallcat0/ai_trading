# -*- coding: utf-8 -*-
"""
簡化新聞爬蟲 - MVP版本

提供基本的新聞爬蟲功能存根，用於維持UI兼容性。
此為簡化版本，移除了複雜的爬蟲功能。

Classes:
    NewsItem: 新聞項目數據類
    NewsCrawler: 新聞爬蟲存根

Example:
    >>> from src.nlp.news_crawler import NewsCrawler, NewsItem
    >>> crawler = NewsCrawler()
    >>> news = crawler.get_latest_news()
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """
    新聞項目數據類
    """
    title: str
    content: str
    url: str
    published_date: datetime
    source: str
    category: str = "general"
    sentiment: str = "neutral"
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'title': self.title,
            'content': self.content,
            'url': self.url,
            'published_date': self.published_date.isoformat(),
            'source': self.source,
            'category': self.category,
            'sentiment': self.sentiment
        }


class NewsCrawler:
    """
    新聞爬蟲存根 - MVP版本
    
    提供基本的新聞爬蟲功能存根，用於維持UI兼容性。
    """
    
    def __init__(self):
        """初始化新聞爬蟲"""
        self.is_available = False
        logger.info("新聞爬蟲已初始化 (MVP存根版本)")
    
    def get_latest_news(self, limit: int = 10) -> List[NewsItem]:
        """
        獲取最新新聞 (存根實現)
        
        Args:
            limit: 新聞數量限制
            
        Returns:
            List[NewsItem]: 新聞列表
        """
        # 返回示例新聞項目
        sample_news = NewsItem(
            title="MVP版本示例新聞",
            content="這是MVP版本的示例新聞內容。實際新聞爬蟲功能在完整版本中提供。",
            url="https://example.com/news/1",
            published_date=datetime.now(),
            source="MVP示例源",
            category="technology",
            sentiment="neutral"
        )
        
        return [sample_news]
    
    def search_news(self, keyword: str, limit: int = 10) -> List[NewsItem]:
        """
        搜索新聞 (存根實現)
        
        Args:
            keyword: 搜索關鍵詞
            limit: 結果數量限制
            
        Returns:
            List[NewsItem]: 搜索結果
        """
        return []
    
    def get_news_by_category(self, category: str, limit: int = 10) -> List[NewsItem]:
        """
        按分類獲取新聞 (存根實現)
        
        Args:
            category: 新聞分類
            limit: 新聞數量限制
            
        Returns:
            List[NewsItem]: 新聞列表
        """
        return []
    
    def is_service_available(self) -> bool:
        """
        檢查服務是否可用
        
        Returns:
            bool: 服務可用性
        """
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        獲取爬蟲狀態
        
        Returns:
            Dict[str, Any]: 爬蟲狀態信息
        """
        return {
            'available': False,
            'version': 'MVP-1.0',
            'type': 'stub_implementation',
            'message': '新聞爬蟲功能在MVP版本中已簡化'
        }
