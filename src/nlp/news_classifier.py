# -*- coding: utf-8 -*-
"""新聞分類和熱度分析器

此模組提供新聞自動分類和熱度分析功能，支援政策類、行業類、
個股類、宏觀經濟類等多種新聞分類，並提供熱度評分算法。

主要功能：
- 新聞自動分類
- 熱度評分算法
- 關鍵詞提取
- 主題挖掘
- 趨勢分析

支援的分類：
- 政策類 (Policy)
- 行業類 (Industry)
- 個股類 (Stock)
- 宏觀經濟類 (Macro)
- 市場情緒類 (Market)

Example:
    >>> from src.nlp.news_classifier import NewsClassifier
    >>> classifier = NewsClassifier()
    >>> 
    >>> # 新聞分類
    >>> category = classifier.classify_news("央行宣布降準0.5個百分點")
    >>> print(f"分類: {category}")  # Policy
    >>> 
    >>> # 熱度分析
    >>> hotness = classifier.analyze_hotness(news_list)
    >>> print(f"熱度分數: {hotness}")
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from collections import Counter, defaultdict
from enum import Enum
import numpy as np
import pandas as pd
from dataclasses import dataclass
import math

from .news_crawler import NewsItem

# 設定日誌
logger = logging.getLogger(__name__)


class NewsCategory(Enum):
    """新聞分類枚舉"""
    POLICY = "policy"           # 政策類
    INDUSTRY = "industry"       # 行業類
    STOCK = "stock"            # 個股類
    MACRO = "macro"            # 宏觀經濟類
    MARKET = "market"          # 市場情緒類
    UNKNOWN = "unknown"        # 未知類別


@dataclass
class ClassificationResult:
    """分類結果數據類"""
    category: NewsCategory      # 分類
    confidence: float          # 置信度
    keywords: List[str]        # 關鍵詞
    score_breakdown: Dict[str, float]  # 分數分解


@dataclass
class HotnessResult:
    """熱度分析結果"""
    hotness_score: float       # 熱度分數 (0-100)
    trend: str                # 趨勢 (上升/下降/穩定)
    key_factors: List[str]     # 關鍵因素
    time_decay: float         # 時間衰減因子
    social_impact: float      # 社會影響力


class NewsClassifier:
    """新聞分類和熱度分析器
    
    提供新聞自動分類和熱度分析功能。
    
    Attributes:
        category_keywords: 分類關鍵詞字典
        hotness_weights: 熱度權重配置
        
    Example:
        >>> classifier = NewsClassifier()
        >>> result = classifier.classify_news("股市大漲")
        >>> hotness = classifier.analyze_hotness([news1, news2])
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化新聞分類器
        
        Args:
            config: 配置參數
        """
        self.config = config or {}
        
        # 分類關鍵詞字典
        self.category_keywords = self._initialize_category_keywords()
        
        # 熱度分析權重
        self.hotness_weights = {
            'keyword_frequency': 0.3,    # 關鍵詞頻率
            'time_decay': 0.2,          # 時間衰減
            'source_authority': 0.2,     # 來源權威性
            'sentiment_impact': 0.15,    # 情感影響
            'social_spread': 0.15       # 社會傳播度
        }
        
        # 來源權威性評分
        self.source_authority = {
            '新華社': 1.0,
            '人民日報': 1.0,
            '央視新聞': 0.95,
            '新浪財經': 0.8,
            '東方財富': 0.8,
            '證券時報': 0.85,
            '財聯社': 0.8,
            '金融界': 0.75,
            '和訊網': 0.7,
            '網易財經': 0.7
        }
        
        # 統計信息
        self.stats = {
            'total_classified': 0,
            'category_counts': {cat.value: 0 for cat in NewsCategory},
            'avg_confidence': 0.0,
            'hotness_analyzed': 0
        }
        
        logger.info("新聞分類器初始化完成")
    
    def _initialize_category_keywords(self) -> Dict[NewsCategory, Dict[str, float]]:
        """初始化分類關鍵詞"""
        return {
            NewsCategory.POLICY: {
                # 政策機構
                '央行': 1.0, '人民銀行': 1.0, '銀保監會': 1.0, '證監會': 1.0,
                '發改委': 0.9, '財政部': 0.9, '國務院': 1.0, '政府': 0.8,
                
                # 政策動作
                '降準': 1.0, '降息': 1.0, '加息': 1.0, '調控': 0.9,
                '監管': 0.9, '政策': 0.8, '法規': 0.8, '規定': 0.7,
                '通知': 0.6, '公告': 0.6, '意見': 0.7, '辦法': 0.7,
                
                # 政策內容
                '減稅': 0.9, '補貼': 0.8, '扶持': 0.8, '刺激': 0.9,
                '限制': 0.8, '禁止': 0.8, '允許': 0.7, '鼓勵': 0.7
            },
            
            NewsCategory.INDUSTRY: {
                # 行業名稱
                '房地產': 0.9, '汽車': 0.8, '醫藥': 0.8, '科技': 0.8,
                '金融': 0.8, '能源': 0.8, '電力': 0.8, '鋼鐵': 0.8,
                '化工': 0.8, '建築': 0.8, '交通': 0.8, '零售': 0.7,
                
                # 行業動態
                '行業': 0.9, '板塊': 0.9, '產業': 0.8, '領域': 0.7,
                '市場': 0.6, '發展': 0.6, '增長': 0.7, '下滑': 0.7,
                '轉型': 0.8, '升級': 0.8, '整合': 0.8, '競爭': 0.7
            },
            
            NewsCategory.STOCK: {
                # 股票相關
                '股票': 1.0, '股價': 1.0, '股市': 0.9, '個股': 1.0,
                '漲停': 1.0, '跌停': 1.0, '漲幅': 0.9, '跌幅': 0.9,
                '成交量': 0.8, '市值': 0.8, '流通': 0.7, '換手': 0.7,
                
                # 公司動態
                '公司': 0.8, '企業': 0.7, '業績': 0.9, '財報': 0.9,
                '盈利': 0.8, '虧損': 0.8, '營收': 0.8, '利潤': 0.8,
                '分紅': 0.8, '送股': 0.8, '增持': 0.8, '減持': 0.8
            },
            
            NewsCategory.MACRO: {
                # 宏觀指標
                'GDP': 1.0, 'CPI': 1.0, 'PPI': 1.0, 'PMI': 1.0,
                '通脹': 0.9, '通縮': 0.9, '就業': 0.8, '失業': 0.8,
                '貿易': 0.8, '進出口': 0.8, '匯率': 0.9, '外匯': 0.8,
                
                # 經濟概念
                '經濟': 0.9, '宏觀': 1.0, '增速': 0.8, '復甦': 0.8,
                '衰退': 0.9, '危機': 0.8, '穩定': 0.7, '波動': 0.7,
                '全球': 0.6, '國際': 0.6, '世界': 0.5, '美國': 0.6
            },
            
            NewsCategory.MARKET: {
                # 市場情緒
                '情緒': 1.0, '信心': 0.9, '恐慌': 0.9, '樂觀': 0.8,
                '悲觀': 0.8, '謹慎': 0.7, '積極': 0.7, '消極': 0.7,
                
                # 市場動態
                '牛市': 1.0, '熊市': 1.0, '震盪': 0.9, '調整': 0.8,
                '反彈': 0.8, '回調': 0.8, '突破': 0.8, '支撐': 0.7,
                '阻力': 0.7, '趨勢': 0.7, '走勢': 0.7, '行情': 0.8
            }
        }
    
    def classify_news(self, text: str, title: str = "") -> ClassificationResult:
        """分類單條新聞
        
        Args:
            text: 新聞內容
            title: 新聞標題
            
        Returns:
            分類結果
        """
        try:
            # 合併標題和內容，標題權重更高
            full_text = (title + " ") * 2 + text
            
            # 計算各分類的分數
            category_scores = {}
            all_keywords = {}
            
            for category, keywords in self.category_keywords.items():
                score = 0.0
                matched_keywords = []
                
                for keyword, weight in keywords.items():
                    count = full_text.count(keyword)
                    if count > 0:
                        # 標題中的關鍵詞權重加倍
                        title_count = title.count(keyword)
                        content_count = count - title_count
                        
                        keyword_score = (title_count * 2 + content_count) * weight
                        score += keyword_score
                        matched_keywords.extend([keyword] * count)
                
                category_scores[category] = score
                all_keywords[category] = matched_keywords
            
            # 找到最高分的分類
            if not category_scores or max(category_scores.values()) == 0:
                best_category = NewsCategory.UNKNOWN
                confidence = 0.0
                keywords = []
            else:
                best_category = max(category_scores, key=category_scores.get)
                
                # 計算置信度
                total_score = sum(category_scores.values())
                confidence = category_scores[best_category] / total_score if total_score > 0 else 0.0
                
                keywords = all_keywords[best_category]
            
            # 更新統計
            self.stats['total_classified'] += 1
            self.stats['category_counts'][best_category.value] += 1
            
            # 更新平均置信度
            total_confidence = self.stats['avg_confidence'] * (self.stats['total_classified'] - 1)
            self.stats['avg_confidence'] = (total_confidence + confidence) / self.stats['total_classified']
            
            return ClassificationResult(
                category=best_category,
                confidence=confidence,
                keywords=list(set(keywords)),
                score_breakdown=category_scores
            )
            
        except Exception as e:
            logger.error(f"新聞分類失敗: {e}")
            return ClassificationResult(
                category=NewsCategory.UNKNOWN,
                confidence=0.0,
                keywords=[],
                score_breakdown={}
            )
    
    def batch_classify(self, news_items: List[NewsItem]) -> List[ClassificationResult]:
        """批量分類新聞
        
        Args:
            news_items: 新聞項目列表
            
        Returns:
            分類結果列表
        """
        results = []
        
        for news_item in news_items:
            result = self.classify_news(news_item.content, news_item.title)
            results.append(result)
        
        logger.info(f"批量分類完成: {len(results)} 條新聞")
        return results
    
    def analyze_hotness(self, news_items: List[NewsItem], 
                       time_window_hours: int = 24) -> HotnessResult:
        """分析新聞熱度
        
        Args:
            news_items: 新聞項目列表
            time_window_hours: 時間窗口（小時）
            
        Returns:
            熱度分析結果
        """
        try:
            if not news_items:
                return HotnessResult(
                    hotness_score=0.0,
                    trend="穩定",
                    key_factors=[],
                    time_decay=1.0,
                    social_impact=0.0
                )
            
            # 過濾時間窗口內的新聞
            cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
            recent_news = [
                news for news in news_items 
                if news.publish_time >= cutoff_time
            ]
            
            if not recent_news:
                return HotnessResult(
                    hotness_score=0.0,
                    trend="穩定",
                    key_factors=[],
                    time_decay=0.0,
                    social_impact=0.0
                )
            
            # 計算各項指標
            keyword_score = self._calculate_keyword_frequency_score(recent_news)
            time_score = self._calculate_time_decay_score(recent_news)
            authority_score = self._calculate_source_authority_score(recent_news)
            sentiment_score = self._calculate_sentiment_impact_score(recent_news)
            social_score = self._calculate_social_spread_score(recent_news)
            
            # 加權計算總熱度
            hotness_score = (
                keyword_score * self.hotness_weights['keyword_frequency'] +
                time_score * self.hotness_weights['time_decay'] +
                authority_score * self.hotness_weights['source_authority'] +
                sentiment_score * self.hotness_weights['sentiment_impact'] +
                social_score * self.hotness_weights['social_spread']
            ) * 100  # 轉換為0-100分
            
            # 分析趨勢
            trend = self._analyze_trend(recent_news)
            
            # 提取關鍵因素
            key_factors = self._extract_key_factors(recent_news)
            
            # 更新統計
            self.stats['hotness_analyzed'] += 1
            
            return HotnessResult(
                hotness_score=min(100.0, hotness_score),
                trend=trend,
                key_factors=key_factors,
                time_decay=time_score,
                social_impact=social_score
            )
            
        except Exception as e:
            logger.error(f"熱度分析失敗: {e}")
            return HotnessResult(
                hotness_score=0.0,
                trend="穩定",
                key_factors=[],
                time_decay=0.0,
                social_impact=0.0
            )
    
    def _calculate_keyword_frequency_score(self, news_items: List[NewsItem]) -> float:
        """計算關鍵詞頻率分數"""
        try:
            all_text = " ".join([news.title + " " + news.content for news in news_items])
            
            # 統計所有分類關鍵詞的出現頻率
            total_frequency = 0
            for category_keywords in self.category_keywords.values():
                for keyword, weight in category_keywords.items():
                    count = all_text.count(keyword)
                    total_frequency += count * weight
            
            # 標準化分數
            max_possible_score = len(news_items) * 50  # 假設每條新聞最多50個關鍵詞
            score = min(1.0, total_frequency / max_possible_score)
            
            return score
            
        except Exception:
            return 0.0
    
    def _calculate_time_decay_score(self, news_items: List[NewsItem]) -> float:
        """計算時間衰減分數"""
        try:
            now = datetime.now()
            total_score = 0.0
            
            for news in news_items:
                # 計算時間差（小時）
                time_diff = (now - news.publish_time).total_seconds() / 3600
                
                # 指數衰減函數
                decay_factor = math.exp(-time_diff / 12)  # 12小時半衰期
                total_score += decay_factor
            
            # 標準化
            return min(1.0, total_score / len(news_items))
            
        except Exception:
            return 0.0
    
    def _calculate_source_authority_score(self, news_items: List[NewsItem]) -> float:
        """計算來源權威性分數"""
        try:
            total_score = 0.0
            
            for news in news_items:
                authority = self.source_authority.get(news.source, 0.5)  # 預設0.5
                total_score += authority
            
            return total_score / len(news_items)
            
        except Exception:
            return 0.5
    
    def _calculate_sentiment_impact_score(self, news_items: List[NewsItem]) -> float:
        """計算情感影響分數"""
        try:
            sentiment_scores = [abs(news.sentiment_score) for news in news_items if news.sentiment_score != 0]
            
            if not sentiment_scores:
                return 0.0
            
            # 平均絕對情感分數
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
            return min(1.0, avg_sentiment)
            
        except Exception:
            return 0.0
    
    def _calculate_social_spread_score(self, news_items: List[NewsItem]) -> float:
        """計算社會傳播度分數"""
        try:
            # 基於新聞數量和來源多樣性
            source_count = len(set(news.source for news in news_items))
            news_count = len(news_items)
            
            # 來源多樣性分數
            diversity_score = min(1.0, source_count / 5)  # 假設5個來源為滿分
            
            # 新聞數量分數
            volume_score = min(1.0, news_count / 20)  # 假設20條新聞為滿分
            
            return (diversity_score + volume_score) / 2
            
        except Exception:
            return 0.0
    
    def _analyze_trend(self, news_items: List[NewsItem]) -> str:
        """分析熱度趨勢"""
        try:
            if len(news_items) < 2:
                return "穩定"
            
            # 按時間排序
            sorted_news = sorted(news_items, key=lambda x: x.publish_time)
            
            # 計算前半段和後半段的新聞數量
            mid_point = len(sorted_news) // 2
            first_half = sorted_news[:mid_point]
            second_half = sorted_news[mid_point:]
            
            first_count = len(first_half)
            second_count = len(second_half)
            
            # 判斷趨勢
            if second_count > first_count * 1.2:
                return "上升"
            elif second_count < first_count * 0.8:
                return "下降"
            else:
                return "穩定"
                
        except Exception:
            return "穩定"
    
    def _extract_key_factors(self, news_items: List[NewsItem]) -> List[str]:
        """提取關鍵因素"""
        try:
            # 統計所有關鍵詞
            keyword_counts = Counter()
            
            for news in news_items:
                text = news.title + " " + news.content
                
                for category_keywords in self.category_keywords.values():
                    for keyword in category_keywords.keys():
                        count = text.count(keyword)
                        if count > 0:
                            keyword_counts[keyword] += count
            
            # 返回前5個最頻繁的關鍵詞
            return [keyword for keyword, _ in keyword_counts.most_common(5)]
            
        except Exception:
            return []
    
    def get_category_distribution(self, news_items: List[NewsItem]) -> Dict[str, int]:
        """獲取新聞分類分佈
        
        Args:
            news_items: 新聞項目列表
            
        Returns:
            分類分佈統計
        """
        results = self.batch_classify(news_items)
        
        distribution = Counter()
        for result in results:
            distribution[result.category.value] += 1
        
        return dict(distribution)
    
    def get_classifier_stats(self) -> Dict[str, Any]:
        """獲取分類器統計信息
        
        Returns:
            統計信息
        """
        return self.stats.copy()
    
    def get_classifier_info(self) -> Dict[str, Any]:
        """獲取分類器資訊
        
        Returns:
            分類器詳細資訊
        """
        return {
            'classifier_name': 'NewsClassifier',
            'version': '1.0.0',
            'supported_categories': [cat.value for cat in NewsCategory],
            'hotness_weights': self.hotness_weights,
            'source_authority': self.source_authority,
            'stats': self.stats,
            'features': [
                'news_classification',
                'hotness_analysis',
                'trend_analysis',
                'keyword_extraction',
                'batch_processing'
            ]
        }
