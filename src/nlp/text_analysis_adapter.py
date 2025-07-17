# -*- coding: utf-8 -*-
"""文本分析功能統一適配器

此模組提供文本分析功能的統一接口，整合情感分析、新聞分類、
股票關聯分析等多種NLP功能。

主要功能：
- 統一文本分析接口
- 情感分析服務
- 新聞分類服務
- 股票關聯分析
- 批量處理支援
- 結果快取管理

Example:
    >>> from src.nlp.text_analysis_adapter import TextAnalysisAdapter
    >>> adapter = TextAnalysisAdapter()
    >>> 
    >>> # 綜合文本分析
    >>> result = adapter.analyze_text("央行宣布降準，股市大漲")
    >>> print(result.sentiment_score)  # 0.75
    >>> print(result.category)         # Policy
    >>> 
    >>> # 新聞股票影響分析
    >>> impact = adapter.analyze_news_impact(news_item, "000001")
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import threading

from .sentiment_analyzer import SentimentAnalyzer
from .realtime_sentiment_scorer import RealtimeSentimentScorer
from .news_classifier import NewsClassifier, NewsCategory
from .news_stock_analyzer import NewsStockAnalyzer
from .text_processor import TextProcessor
from .news_crawler import NewsItem

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class TextAnalysisResult:
    """文本分析結果"""
    text: str                          # 原始文本
    sentiment_score: float             # 情感分數
    category: NewsCategory             # 新聞分類
    classification_confidence: float   # 分類置信度
    keywords: List[str]               # 關鍵詞
    processed_tokens: List[str]       # 處理後的詞彙
    analysis_time: datetime           # 分析時間
    metadata: Dict[str, Any]          # 元數據


class TextAnalysisAdapter:
    """文本分析功能統一適配器
    
    整合多種NLP功能的統一接口。
    
    Attributes:
        sentiment_analyzer: 情感分析器
        sentiment_scorer: 實時情感評分器
        news_classifier: 新聞分類器
        stock_analyzer: 股票關聯分析器
        text_processor: 文本處理器
        
    Example:
        >>> adapter = TextAnalysisAdapter()
        >>> result = adapter.analyze_text("股市上漲")
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化文本分析適配器
        
        Args:
            config: 配置參數
        """
        self.config = config or {}
        
        # 初始化核心組件
        try:
            self.sentiment_analyzer = SentimentAnalyzer(
                self.config.get('sentiment_analyzer', {})
            )
            
            self.sentiment_scorer = RealtimeSentimentScorer(
                self.config.get('sentiment_scorer', {})
            )
            
            self.news_classifier = NewsClassifier(
                self.config.get('news_classifier', {})
            )
            
            self.stock_analyzer = NewsStockAnalyzer(
                self.config.get('stock_analyzer', {})
            )
            
            self.text_processor = TextProcessor(
                self.config.get('text_processor', {})
            )
            
        except Exception as e:
            logger.error(f"組件初始化失敗: {e}")
            raise RuntimeError(f"文本分析適配器初始化失敗: {e}")
        
        # 快取配置
        self.enable_cache = self.config.get('enable_cache', True)
        self.cache_size = self.config.get('cache_size', 1000)
        self.analysis_cache = {}
        self.cache_lock = threading.Lock()
        
        # 統計信息
        self.stats = {
            'total_analyzed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_processing_time': 0.0
        }
        
        logger.info("文本分析適配器初始化完成")
    
    def analyze_text(self, text: str, 
                    include_processing: bool = True) -> TextAnalysisResult:
        """綜合文本分析
        
        Args:
            text: 待分析文本
            include_processing: 是否包含文本預處理
            
        Returns:
            分析結果
        """
        import time
        start_time = time.time()
        
        try:
            # 檢查快取
            if self.enable_cache:
                cached_result = self._get_from_cache(text)
                if cached_result:
                    self.stats['cache_hits'] += 1
                    return cached_result
            
            # 文本預處理
            processed_tokens = []
            if include_processing:
                processed_result = self.text_processor.process_text(text)
                processed_tokens = processed_result.filtered_tokens
            
            # 情感分析
            sentiment_score = self.sentiment_scorer.score_text(text)
            
            # 新聞分類
            classification_result = self.news_classifier.classify_news(text)
            
            # 創建分析結果
            result = TextAnalysisResult(
                text=text,
                sentiment_score=sentiment_score,
                category=classification_result.category,
                classification_confidence=classification_result.confidence,
                keywords=classification_result.keywords,
                processed_tokens=processed_tokens,
                analysis_time=datetime.now(),
                metadata={
                    'processing_time': time.time() - start_time,
                    'score_breakdown': classification_result.score_breakdown
                }
            )
            
            # 更新快取
            if self.enable_cache:
                self._add_to_cache(text, result)
            
            # 更新統計
            self.stats['total_analyzed'] += 1
            self.stats['cache_misses'] += 1
            
            processing_time = time.time() - start_time
            total_time = self.stats['avg_processing_time'] * (self.stats['total_analyzed'] - 1)
            self.stats['avg_processing_time'] = (total_time + processing_time) / self.stats['total_analyzed']
            
            return result
            
        except Exception as e:
            logger.error(f"文本分析失敗: {e}")
            return TextAnalysisResult(
                text=text,
                sentiment_score=0.0,
                category=NewsCategory.UNKNOWN,
                classification_confidence=0.0,
                keywords=[],
                processed_tokens=[],
                analysis_time=datetime.now(),
                metadata={'error': str(e)}
            )
    
    def batch_analyze_texts(self, texts: List[str]) -> List[TextAnalysisResult]:
        """批量文本分析
        
        Args:
            texts: 文本列表
            
        Returns:
            分析結果列表
        """
        results = []
        
        for text in texts:
            result = self.analyze_text(text)
            results.append(result)
        
        logger.info(f"批量文本分析完成: {len(results)} 個文本")
        return results
    
    def analyze_news_impact(self, news_item: NewsItem, 
                           stock_code: str):
        """分析新聞對股票的影響
        
        Args:
            news_item: 新聞項目
            stock_code: 股票代碼
            
        Returns:
            影響分析結果
        """
        try:
            # 先進行情感分析
            if news_item.sentiment_score == 0.0:
                news_item.sentiment_score = self.sentiment_scorer.score_text(
                    news_item.title + " " + news_item.content
                )
            
            # 股票影響分析
            impact_result = self.stock_analyzer.analyze_news_impact(
                news_item, stock_code
            )
            
            return impact_result
            
        except Exception as e:
            logger.error(f"新聞影響分析失敗: {e}")
            return None
    
    def get_sentiment_trend(self, texts: List[str], 
                           window_size: int = 50) -> Dict[str, Any]:
        """獲取情感趨勢分析
        
        Args:
            texts: 文本列表
            window_size: 分析窗口大小
            
        Returns:
            趨勢分析結果
        """
        try:
            return self.sentiment_scorer.get_sentiment_trend(texts, window_size)
        except Exception as e:
            logger.error(f"情感趨勢分析失敗: {e}")
            return {}
    
    def get_category_distribution(self, texts: List[str]) -> Dict[str, int]:
        """獲取文本分類分佈
        
        Args:
            texts: 文本列表
            
        Returns:
            分類分佈統計
        """
        try:
            # 創建臨時新聞項目
            news_items = [
                NewsItem(
                    title="",
                    content=text,
                    url="",
                    source="",
                    publish_time=datetime.now()
                )
                for text in texts
            ]
            
            return self.news_classifier.get_category_distribution(news_items)
            
        except Exception as e:
            logger.error(f"分類分佈分析失敗: {e}")
            return {}
    
    def find_related_stocks(self, text: str, 
                           threshold: float = 0.3) -> List[Any]:
        """查找與文本相關的股票
        
        Args:
            text: 文本內容
            threshold: 相關性閾值
            
        Returns:
            相關股票列表
        """
        try:
            # 創建臨時新聞項目
            news_item = NewsItem(
                title="",
                content=text,
                url="",
                source="",
                publish_time=datetime.now()
            )
            
            return self.stock_analyzer.find_related_stocks(news_item, threshold)
            
        except Exception as e:
            logger.error(f"相關股票查找失敗: {e}")
            return []
    
    def _get_from_cache(self, text: str) -> Optional[TextAnalysisResult]:
        """從快取獲取結果"""
        with self.cache_lock:
            return self.analysis_cache.get(text)
    
    def _add_to_cache(self, text: str, result: TextAnalysisResult):
        """添加到快取"""
        with self.cache_lock:
            # 如果快取已滿，移除最舊的條目
            if len(self.analysis_cache) >= self.cache_size:
                oldest_key = next(iter(self.analysis_cache))
                del self.analysis_cache[oldest_key]
            
            self.analysis_cache[text] = result
    
    def clear_cache(self):
        """清空快取"""
        with self.cache_lock:
            self.analysis_cache.clear()
        logger.info("分析快取已清空")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """獲取性能統計
        
        Returns:
            性能統計信息
        """
        stats = self.stats.copy()
        
        # 添加組件統計
        stats.update({
            'sentiment_analyzer_stats': self.sentiment_analyzer.get_performance_stats(),
            'sentiment_scorer_stats': self.sentiment_scorer.get_performance_stats(),
            'news_classifier_stats': self.news_classifier.get_classifier_stats(),
            'stock_analyzer_stats': self.stock_analyzer.get_analyzer_stats(),
            'text_processor_stats': self.text_processor.get_processor_stats()
        })
        
        # 計算快取命中率
        total_requests = stats['cache_hits'] + stats['cache_misses']
        stats['cache_hit_rate'] = stats['cache_hits'] / total_requests if total_requests > 0 else 0
        
        return stats
    
    def get_adapter_info(self) -> Dict[str, Any]:
        """獲取適配器資訊
        
        Returns:
            適配器詳細資訊
        """
        return {
            'adapter_name': 'TextAnalysisAdapter',
            'version': '1.0.0',
            'config': self.config,
            'components': {
                'sentiment_analyzer': self.sentiment_analyzer.get_analyzer_info(),
                'sentiment_scorer': self.sentiment_scorer.get_scorer_info(),
                'news_classifier': self.news_classifier.get_classifier_info(),
                'stock_analyzer': self.stock_analyzer.get_analyzer_info(),
                'text_processor': self.text_processor.get_processor_info()
            },
            'performance_stats': self.get_performance_stats(),
            'features': [
                'comprehensive_text_analysis',
                'sentiment_analysis',
                'news_classification',
                'stock_correlation_analysis',
                'batch_processing',
                'caching_system',
                'trend_analysis'
            ]
        }
