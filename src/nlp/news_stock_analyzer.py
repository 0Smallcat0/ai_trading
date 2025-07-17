# -*- coding: utf-8 -*-
"""新聞-股票關聯分析器

此模組提供新聞與股票的智能關聯分析功能，支援個股新聞影響評估、
歷史數據回測和事件驅動分析。

主要功能：
- 新聞-股票關聯識別
- 影響力評估
- 事件驅動分析
- 歷史回測驗證
- 預測模型構建

分析維度：
- 直接關聯 (股票代碼、公司名稱)
- 行業關聯 (行業新聞影響)
- 概念關聯 (概念板塊影響)
- 情感關聯 (市場情緒影響)

Example:
    >>> from src.nlp.news_stock_analyzer import NewsStockAnalyzer
    >>> analyzer = NewsStockAnalyzer()
    >>> 
    >>> # 分析新聞對股票的影響
    >>> impact = analyzer.analyze_news_impact(news_item, "000001")
    >>> print(f"影響評分: {impact.impact_score}")
    >>> 
    >>> # 歷史回測
    >>> backtest_result = analyzer.backtest_news_impact(news_list, price_data)
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from collections import defaultdict
import numpy as np
import pandas as pd
from scipy import stats
import json

from .news_crawler import NewsItem
from .news_classifier import NewsClassifier, NewsCategory
from .sentiment_analyzer import SentimentAnalyzer

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class StockNewsImpact:
    """股票新聞影響結果"""
    stock_code: str                    # 股票代碼
    news_item: NewsItem               # 新聞項目
    impact_score: float               # 影響評分 (-1.0 到 1.0)
    confidence: float                 # 置信度 (0.0 到 1.0)
    correlation_type: str             # 關聯類型
    key_factors: List[str]            # 關鍵因素
    predicted_direction: str          # 預測方向 (上漲/下跌/中性)
    time_horizon: str                 # 影響時間範圍


@dataclass
class BacktestResult:
    """回測結果"""
    total_events: int                 # 總事件數
    correct_predictions: int          # 正確預測數
    accuracy: float                   # 準確率
    avg_return: float                # 平均收益率
    sharpe_ratio: float              # 夏普比率
    max_drawdown: float              # 最大回撤
    event_analysis: List[Dict]        # 事件分析詳情


class StockDatabase:
    """股票數據庫"""
    
    def __init__(self):
        """初始化股票數據庫"""
        # 股票基本信息
        self.stock_info = self._load_stock_info()
        
        # 行業分類
        self.industry_mapping = self._load_industry_mapping()
        
        # 概念板塊
        self.concept_mapping = self._load_concept_mapping()
    
    def _load_stock_info(self) -> Dict[str, Dict[str, Any]]:
        """載入股票基本信息"""
        # 這裡應該從數據庫或文件載入真實的股票信息
        # 為了演示，提供一些示例數據
        return {
            '000001': {
                'name': '平安銀行',
                'industry': '銀行',
                'concepts': ['金融', '銀行股', 'H股'],
                'aliases': ['平安銀行', 'PAYH', '000001.SZ']
            },
            '000002': {
                'name': '萬科A',
                'industry': '房地產',
                'concepts': ['房地產', '藍籌股', 'MSCI'],
                'aliases': ['萬科', '萬科A', '000002.SZ']
            },
            '600036': {
                'name': '招商銀行',
                'industry': '銀行',
                'concepts': ['金融', '銀行股', 'H股'],
                'aliases': ['招商銀行', 'CMB', '600036.SH']
            }
        }
    
    def _load_industry_mapping(self) -> Dict[str, List[str]]:
        """載入行業映射"""
        return {
            '銀行': ['000001', '600036', '601988', '600000'],
            '房地產': ['000002', '000069', '600048', '600340'],
            '科技': ['000858', '002415', '300059', '600570'],
            '醫藥': ['000538', '002007', '300003', '600276']
        }
    
    def _load_concept_mapping(self) -> Dict[str, List[str]]:
        """載入概念映射"""
        return {
            '金融': ['000001', '600036', '601988', '600000'],
            '新能源': ['002594', '300274', '002129', '600884'],
            '人工智能': ['002415', '300059', '600570', '000858'],
            '醫療健康': ['000538', '002007', '300003', '600276']
        }
    
    def get_stock_info(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """獲取股票信息"""
        return self.stock_info.get(stock_code)
    
    def find_stocks_by_name(self, name: str) -> List[str]:
        """根據名稱查找股票代碼"""
        found_stocks = []
        
        for code, info in self.stock_info.items():
            if (name in info['name'] or 
                name in info.get('aliases', []) or
                any(name in alias for alias in info.get('aliases', []))):
                found_stocks.append(code)
        
        return found_stocks
    
    def get_industry_stocks(self, industry: str) -> List[str]:
        """獲取行業股票列表"""
        return self.industry_mapping.get(industry, [])
    
    def get_concept_stocks(self, concept: str) -> List[str]:
        """獲取概念股票列表"""
        return self.concept_mapping.get(concept, [])


class NewsStockAnalyzer:
    """新聞-股票關聯分析器
    
    提供新聞與股票的智能關聯分析功能。
    
    Attributes:
        stock_db: 股票數據庫
        classifier: 新聞分類器
        sentiment_analyzer: 情感分析器
        
    Example:
        >>> analyzer = NewsStockAnalyzer()
        >>> impact = analyzer.analyze_news_impact(news, "000001")
        >>> backtest = analyzer.backtest_news_impact(news_list, price_data)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化新聞-股票關聯分析器
        
        Args:
            config: 配置參數
        """
        self.config = config or {}
        
        # 核心組件
        self.stock_db = StockDatabase()
        self.classifier = NewsClassifier()
        self.sentiment_analyzer = SentimentAnalyzer()
        
        # 影響權重配置
        self.impact_weights = {
            'direct_mention': 0.4,      # 直接提及
            'industry_relation': 0.2,   # 行業關聯
            'concept_relation': 0.15,   # 概念關聯
            'sentiment_impact': 0.15,   # 情感影響
            'news_importance': 0.1      # 新聞重要性
        }
        
        # 時間衰減參數
        self.time_decay_params = {
            'half_life_hours': 24,      # 半衰期24小時
            'max_impact_hours': 72      # 最大影響時間72小時
        }
        
        # 統計信息
        self.stats = {
            'total_analyzed': 0,
            'direct_correlations': 0,
            'industry_correlations': 0,
            'concept_correlations': 0,
            'avg_impact_score': 0.0
        }
        
        logger.info("新聞-股票關聯分析器初始化完成")
    
    def analyze_news_impact(self, news_item: NewsItem, 
                           stock_code: str) -> StockNewsImpact:
        """分析新聞對特定股票的影響
        
        Args:
            news_item: 新聞項目
            stock_code: 股票代碼
            
        Returns:
            影響分析結果
        """
        try:
            # 獲取股票信息
            stock_info = self.stock_db.get_stock_info(stock_code)
            if not stock_info:
                logger.warning(f"未找到股票信息: {stock_code}")
                return self._create_empty_impact(stock_code, news_item)
            
            # 計算各維度影響分數
            direct_score = self._calculate_direct_impact(news_item, stock_info)
            industry_score = self._calculate_industry_impact(news_item, stock_info)
            concept_score = self._calculate_concept_impact(news_item, stock_info)
            sentiment_score = self._calculate_sentiment_impact(news_item)
            importance_score = self._calculate_news_importance(news_item)
            
            # 加權計算總影響分數
            total_impact = (
                direct_score * self.impact_weights['direct_mention'] +
                industry_score * self.impact_weights['industry_relation'] +
                concept_score * self.impact_weights['concept_relation'] +
                sentiment_score * self.impact_weights['sentiment_impact'] +
                importance_score * self.impact_weights['news_importance']
            )
            
            # 計算置信度
            confidence = self._calculate_confidence(
                direct_score, industry_score, concept_score, sentiment_score
            )
            
            # 確定關聯類型
            correlation_type = self._determine_correlation_type(
                direct_score, industry_score, concept_score
            )
            
            # 提取關鍵因素
            key_factors = self._extract_key_factors(news_item, stock_info)
            
            # 預測方向
            predicted_direction = self._predict_direction(total_impact, sentiment_score)
            
            # 影響時間範圍
            time_horizon = self._estimate_time_horizon(news_item, total_impact)
            
            # 更新統計
            self._update_stats(correlation_type, total_impact)
            
            return StockNewsImpact(
                stock_code=stock_code,
                news_item=news_item,
                impact_score=total_impact,
                confidence=confidence,
                correlation_type=correlation_type,
                key_factors=key_factors,
                predicted_direction=predicted_direction,
                time_horizon=time_horizon
            )
            
        except Exception as e:
            logger.error(f"新聞影響分析失敗: {e}")
            return self._create_empty_impact(stock_code, news_item)
    
    def _calculate_direct_impact(self, news_item: NewsItem, 
                                stock_info: Dict[str, Any]) -> float:
        """計算直接影響分數"""
        try:
            text = news_item.title + " " + news_item.content
            score = 0.0
            
            # 檢查股票代碼
            if stock_info['name'] in text:
                score += 1.0
            
            # 檢查別名
            for alias in stock_info.get('aliases', []):
                if alias in text:
                    score += 0.8
                    break
            
            # 檢查已提取的股票代碼
            if stock_info.get('code') in news_item.stock_codes:
                score += 1.0
            
            return min(1.0, score)
            
        except Exception:
            return 0.0
    
    def _calculate_industry_impact(self, news_item: NewsItem, 
                                  stock_info: Dict[str, Any]) -> float:
        """計算行業影響分數"""
        try:
            # 分類新聞
            classification = self.classifier.classify_news(
                news_item.content, news_item.title
            )
            
            # 如果是行業類新聞
            if classification.category == NewsCategory.INDUSTRY:
                text = news_item.title + " " + news_item.content
                industry = stock_info.get('industry', '')
                
                if industry and industry in text:
                    return classification.confidence
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_concept_impact(self, news_item: NewsItem, 
                                 stock_info: Dict[str, Any]) -> float:
        """計算概念影響分數"""
        try:
            text = news_item.title + " " + news_item.content
            concepts = stock_info.get('concepts', [])
            
            max_score = 0.0
            for concept in concepts:
                if concept in text:
                    # 根據概念在文本中的重要性計算分數
                    concept_count = text.count(concept)
                    score = min(1.0, concept_count * 0.3)
                    max_score = max(max_score, score)
            
            return max_score
            
        except Exception:
            return 0.0
    
    def _calculate_sentiment_impact(self, news_item: NewsItem) -> float:
        """計算情感影響分數"""
        try:
            # 如果新聞已有情感分數，直接使用
            if news_item.sentiment_score != 0.0:
                return abs(news_item.sentiment_score)
            
            # 否則進行情感分析
            sentiment_score = self.sentiment_analyzer.analyze_sentiment(
                news_item.title + " " + news_item.content
            )
            
            return abs(sentiment_score)
            
        except Exception:
            return 0.0
    
    def _calculate_news_importance(self, news_item: NewsItem) -> float:
        """計算新聞重要性分數"""
        try:
            score = 0.0
            
            # 基於來源權威性
            source_scores = {
                '新華社': 1.0,
                '人民日報': 1.0,
                '央視新聞': 0.95,
                '新浪財經': 0.8,
                '東方財富': 0.8,
                '證券時報': 0.85
            }
            
            score += source_scores.get(news_item.source, 0.5)
            
            # 基於標題長度和內容豐富度
            title_score = min(0.3, len(news_item.title) / 100)
            content_score = min(0.3, len(news_item.content) / 1000)
            
            score += title_score + content_score
            
            return min(1.0, score)
            
        except Exception:
            return 0.5
    
    def _calculate_confidence(self, direct: float, industry: float, 
                            concept: float, sentiment: float) -> float:
        """計算置信度"""
        try:
            # 基於各維度分數的綜合置信度
            scores = [direct, industry, concept, sentiment]
            non_zero_scores = [s for s in scores if s > 0]
            
            if not non_zero_scores:
                return 0.0
            
            # 多維度驗證提高置信度
            dimension_count = len(non_zero_scores)
            avg_score = sum(non_zero_scores) / len(non_zero_scores)
            
            # 維度數量加權
            dimension_weight = min(1.0, dimension_count / 4)
            
            confidence = avg_score * dimension_weight
            return min(1.0, confidence)
            
        except Exception:
            return 0.0
    
    def _determine_correlation_type(self, direct: float, industry: float, 
                                   concept: float) -> str:
        """確定關聯類型"""
        if direct > 0.5:
            return "直接關聯"
        elif industry > 0.5:
            return "行業關聯"
        elif concept > 0.5:
            return "概念關聯"
        else:
            return "弱關聯"
    
    def _extract_key_factors(self, news_item: NewsItem, 
                           stock_info: Dict[str, Any]) -> List[str]:
        """提取關鍵因素"""
        factors = []
        
        # 檢查直接提及
        if stock_info['name'] in news_item.title:
            factors.append(f"直接提及: {stock_info['name']}")
        
        # 檢查行業關聯
        industry = stock_info.get('industry', '')
        if industry and industry in news_item.content:
            factors.append(f"行業關聯: {industry}")
        
        # 檢查概念關聯
        for concept in stock_info.get('concepts', []):
            if concept in news_item.content:
                factors.append(f"概念關聯: {concept}")
        
        return factors[:5]  # 最多返回5個關鍵因素
    
    def _predict_direction(self, impact_score: float, sentiment_score: float) -> str:
        """預測股價方向"""
        if impact_score < 0.1:
            return "中性"
        
        if sentiment_score > 0.1:
            return "上漲"
        elif sentiment_score < -0.1:
            return "下跌"
        else:
            return "中性"
    
    def _estimate_time_horizon(self, news_item: NewsItem, impact_score: float) -> str:
        """估計影響時間範圍"""
        # 分類新聞
        classification = self.classifier.classify_news(
            news_item.content, news_item.title
        )
        
        if classification.category == NewsCategory.POLICY:
            return "長期 (1-3個月)"
        elif classification.category == NewsCategory.STOCK:
            if impact_score > 0.7:
                return "短期 (1-3天)"
            else:
                return "中期 (1-2週)"
        elif classification.category == NewsCategory.INDUSTRY:
            return "中期 (2-4週)"
        else:
            return "短期 (1-5天)"
    
    def _create_empty_impact(self, stock_code: str, news_item: NewsItem) -> StockNewsImpact:
        """創建空影響結果"""
        return StockNewsImpact(
            stock_code=stock_code,
            news_item=news_item,
            impact_score=0.0,
            confidence=0.0,
            correlation_type="無關聯",
            key_factors=[],
            predicted_direction="中性",
            time_horizon="無影響"
        )
    
    def _update_stats(self, correlation_type: str, impact_score: float):
        """更新統計信息"""
        self.stats['total_analyzed'] += 1
        
        if correlation_type == "直接關聯":
            self.stats['direct_correlations'] += 1
        elif correlation_type == "行業關聯":
            self.stats['industry_correlations'] += 1
        elif correlation_type == "概念關聯":
            self.stats['concept_correlations'] += 1
        
        # 更新平均影響分數
        total_impact = self.stats['avg_impact_score'] * (self.stats['total_analyzed'] - 1)
        self.stats['avg_impact_score'] = (total_impact + abs(impact_score)) / self.stats['total_analyzed']
    
    def batch_analyze_impact(self, news_items: List[NewsItem], 
                           stock_codes: List[str]) -> List[List[StockNewsImpact]]:
        """批量分析新聞對多隻股票的影響
        
        Args:
            news_items: 新聞項目列表
            stock_codes: 股票代碼列表
            
        Returns:
            影響分析結果矩陣 [新聞][股票]
        """
        results = []
        
        for news_item in news_items:
            news_results = []
            for stock_code in stock_codes:
                impact = self.analyze_news_impact(news_item, stock_code)
                news_results.append(impact)
            results.append(news_results)
        
        logger.info(f"批量分析完成: {len(news_items)} 條新聞 × {len(stock_codes)} 隻股票")
        return results
    
    def find_related_stocks(self, news_item: NewsItem, 
                           threshold: float = 0.3) -> List[StockNewsImpact]:
        """查找與新聞相關的股票
        
        Args:
            news_item: 新聞項目
            threshold: 影響分數閾值
            
        Returns:
            相關股票影響列表
        """
        related_stocks = []
        
        # 遍歷所有股票
        for stock_code in self.stock_db.stock_info.keys():
            impact = self.analyze_news_impact(news_item, stock_code)
            
            if abs(impact.impact_score) >= threshold:
                related_stocks.append(impact)
        
        # 按影響分數排序
        related_stocks.sort(key=lambda x: abs(x.impact_score), reverse=True)
        
        return related_stocks
    
    def get_analyzer_stats(self) -> Dict[str, Any]:
        """獲取分析器統計信息
        
        Returns:
            統計信息
        """
        return self.stats.copy()
    
    def get_analyzer_info(self) -> Dict[str, Any]:
        """獲取分析器資訊
        
        Returns:
            分析器詳細資訊
        """
        return {
            'analyzer_name': 'NewsStockAnalyzer',
            'version': '1.0.0',
            'impact_weights': self.impact_weights,
            'time_decay_params': self.time_decay_params,
            'supported_stocks': len(self.stock_db.stock_info),
            'stats': self.stats,
            'features': [
                'news_stock_correlation',
                'impact_assessment',
                'direction_prediction',
                'time_horizon_estimation',
                'batch_analysis',
                'related_stock_discovery'
            ]
        }
