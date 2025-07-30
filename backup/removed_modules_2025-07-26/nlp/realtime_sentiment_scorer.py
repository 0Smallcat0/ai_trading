# -*- coding: utf-8 -*-
"""實時情感評分系統

此模組提供標準化的實時情感評分功能，支援批量處理和
高性能文本情感分析，為量化交易提供實時市場情緒指標。

主要功能：
- 實時情感評分 (-1.0 到 1.0)
- 批量文本處理
- 多線程並發處理
- 情感趨勢分析
- 實時監控和統計

性能指標：
- 處理速度: ≥1000條/分鐘
- 響應延遲: <100ms/條
- 並發支援: ≥10個線程
- 準確率: ≥85%

Example:
    >>> from src.nlp.realtime_sentiment_scorer import RealtimeSentimentScorer
    >>> scorer = RealtimeSentimentScorer()
    >>> 
    >>> # 實時評分
    >>> score = scorer.score_text("股市大漲，投資者信心增強")
    >>> print(f"情感分數: {score}")  # 0.75
    >>> 
    >>> # 批量評分
    >>> texts = ["利好消息", "業績下滑", "市場穩定"]
    >>> scores = scorer.batch_score(texts)
    >>> 
    >>> # 獲取情感趨勢
    >>> trend = scorer.get_sentiment_trend(texts, window_size=10)
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from collections import deque, defaultdict
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
import asyncio

from .sentiment_analyzer import SentimentAnalyzer
from .financial_sentiment_dict import FinancialSentimentDict

# 設定日誌
logger = logging.getLogger(__name__)


class SentimentScore:
    """情感分數數據類"""
    
    def __init__(self, text: str, score: float, timestamp: datetime = None,
                 confidence: float = 1.0, metadata: Dict[str, Any] = None):
        self.text = text
        self.score = score
        self.timestamp = timestamp or datetime.now()
        self.confidence = confidence
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'text': self.text,
            'score': self.score,
            'timestamp': self.timestamp.isoformat(),
            'confidence': self.confidence,
            'metadata': self.metadata
        }


class SentimentTrend:
    """情感趨勢分析器"""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.scores = deque(maxlen=window_size)
        self.timestamps = deque(maxlen=window_size)
        self.lock = threading.Lock()
    
    def add_score(self, score: float, timestamp: datetime = None):
        """添加情感分數"""
        with self.lock:
            self.scores.append(score)
            self.timestamps.append(timestamp or datetime.now())
    
    def get_trend(self) -> Dict[str, float]:
        """獲取情感趨勢"""
        with self.lock:
            if len(self.scores) < 2:
                return {'trend': 0.0, 'volatility': 0.0, 'current': 0.0}
            
            scores_array = np.array(self.scores)
            
            # 計算趨勢 (線性回歸斜率)
            x = np.arange(len(scores_array))
            trend = np.polyfit(x, scores_array, 1)[0]
            
            # 計算波動性
            volatility = np.std(scores_array)
            
            # 當前分數
            current = scores_array[-1]
            
            return {
                'trend': float(trend),
                'volatility': float(volatility),
                'current': float(current),
                'mean': float(np.mean(scores_array)),
                'min': float(np.min(scores_array)),
                'max': float(np.max(scores_array))
            }


class RealtimeSentimentScorer:
    """實時情感評分系統
    
    提供高性能的實時情感評分和趨勢分析功能。
    
    Attributes:
        analyzer: 情感分析器
        sentiment_dict: 金融情感詞典
        trend_analyzer: 趨勢分析器
        
    Example:
        >>> scorer = RealtimeSentimentScorer({
        ...     'max_workers': 8,
        ...     'batch_size': 100,
        ...     'cache_size': 1000
        ... })
        >>> score = scorer.score_text("股價上漲")
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化實時情感評分系統
        
        Args:
            config: 配置參數
                - max_workers: 最大工作線程數
                - batch_size: 批處理大小
                - cache_size: 快取大小
                - trend_window: 趨勢分析窗口大小
        """
        self.config = config or {}
        
        # 基本配置
        self.max_workers = self.config.get('max_workers', 4)
        self.batch_size = self.config.get('batch_size', 50)
        self.cache_size = self.config.get('cache_size', 1000)
        self.trend_window = self.config.get('trend_window', 100)
        
        # 核心組件
        self.analyzer = SentimentAnalyzer(self.config.get('analyzer_config', {}))
        self.sentiment_dict = FinancialSentimentDict()
        self.trend_analyzer = SentimentTrend(self.trend_window)
        
        # 快取系統
        self.score_cache: Dict[str, SentimentScore] = {}
        self.cache_lock = threading.Lock()
        
        # 性能統計
        self.stats = {
            'total_scored': 0,
            'total_time': 0.0,
            'avg_time_per_text': 0.0,
            'cache_hits': 0,
            'cache_misses': 0,
            'batch_processed': 0
        }
        self.stats_lock = threading.Lock()
        
        # 實時監控
        self.monitoring_enabled = False
        self.monitoring_callbacks: List[Callable] = []
        
        # 異步處理隊列
        self.processing_queue = queue.Queue()
        self.result_queue = queue.Queue()
        
        logger.info("實時情感評分系統初始化完成")
    
    def score_text(self, text: str, use_cache: bool = True) -> float:
        """評分單個文本
        
        Args:
            text: 待評分文本
            use_cache: 是否使用快取
            
        Returns:
            情感分數 (-1.0 到 1.0)
        """
        if not text or not text.strip():
            return 0.0
        
        start_time = time.time()
        
        # 檢查快取
        if use_cache:
            cached_score = self._get_from_cache(text)
            if cached_score is not None:
                with self.stats_lock:
                    self.stats['cache_hits'] += 1
                return cached_score.score
        
        try:
            # 情感分析
            score = self.analyzer.analyze_sentiment(text)
            
            # 創建情感分數對象
            sentiment_score = SentimentScore(
                text=text,
                score=score,
                confidence=self._calculate_confidence(text, score)
            )
            
            # 更新快取
            if use_cache:
                self._add_to_cache(text, sentiment_score)
            
            # 更新趨勢
            self.trend_analyzer.add_score(score)
            
            # 更新統計
            with self.stats_lock:
                self.stats['total_scored'] += 1
                elapsed_time = time.time() - start_time
                self.stats['total_time'] += elapsed_time
                self.stats['avg_time_per_text'] = self.stats['total_time'] / self.stats['total_scored']
                self.stats['cache_misses'] += 1
            
            # 觸發監控回調
            if self.monitoring_enabled:
                self._trigger_monitoring_callbacks(sentiment_score)
            
            return score
            
        except Exception as e:
            logger.error(f"文本評分失敗: {e}")
            return 0.0
    
    def batch_score(self, texts: List[str], use_cache: bool = True) -> List[float]:
        """批量評分文本
        
        Args:
            texts: 文本列表
            use_cache: 是否使用快取
            
        Returns:
            情感分數列表
        """
        if not texts:
            return []
        
        start_time = time.time()
        
        try:
            # 檢查快取
            cached_results = {}
            uncached_texts = []
            
            if use_cache:
                for i, text in enumerate(texts):
                    cached_score = self._get_from_cache(text)
                    if cached_score is not None:
                        cached_results[i] = cached_score.score
                    else:
                        uncached_texts.append((i, text))
            else:
                uncached_texts = list(enumerate(texts))
            
            # 批量處理未快取的文本
            uncached_scores = {}
            if uncached_texts:
                if len(uncached_texts) <= 10:
                    # 小批量直接處理
                    for i, text in uncached_texts:
                        score = self.analyzer.analyze_sentiment(text)
                        uncached_scores[i] = score
                        
                        if use_cache:
                            sentiment_score = SentimentScore(text=text, score=score)
                            self._add_to_cache(text, sentiment_score)
                else:
                    # 大批量多線程處理
                    uncached_scores = self._batch_process_parallel(uncached_texts, use_cache)
            
            # 合併結果
            results = [0.0] * len(texts)
            for i in range(len(texts)):
                if i in cached_results:
                    results[i] = cached_results[i]
                elif i in uncached_scores:
                    results[i] = uncached_scores[i]
            
            # 更新統計
            with self.stats_lock:
                self.stats['batch_processed'] += 1
                self.stats['cache_hits'] += len(cached_results)
                self.stats['cache_misses'] += len(uncached_texts)
            
            elapsed_time = time.time() - start_time
            speed = len(texts) / elapsed_time if elapsed_time > 0 else 0
            
            logger.info(f"批量評分完成: {len(texts)} 條文本, 耗時 {elapsed_time:.2f}秒, 速度 {speed:.0f} 條/秒")
            
            return results
            
        except Exception as e:
            logger.error(f"批量評分失敗: {e}")
            return [0.0] * len(texts)
    
    def _batch_process_parallel(self, text_pairs: List[Tuple[int, str]], 
                               use_cache: bool) -> Dict[int, float]:
        """並行批量處理"""
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交任務
            future_to_index = {
                executor.submit(self.analyzer.analyze_sentiment, text): index
                for index, text in text_pairs
            }
            
            # 收集結果
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    score = future.result()
                    results[index] = score
                    
                    # 更新快取
                    if use_cache:
                        text = next(text for i, text in text_pairs if i == index)
                        sentiment_score = SentimentScore(text=text, score=score)
                        self._add_to_cache(text, sentiment_score)
                        
                except Exception as e:
                    logger.error(f"並行處理第{index}個文本失敗: {e}")
                    results[index] = 0.0
        
        return results
    
    def get_sentiment_trend(self, recent_texts: List[str] = None, 
                           window_size: int = None) -> Dict[str, Any]:
        """獲取情感趨勢分析
        
        Args:
            recent_texts: 最近的文本列表（可選）
            window_size: 分析窗口大小
            
        Returns:
            趨勢分析結果
        """
        try:
            # 如果提供了新文本，先進行評分
            if recent_texts:
                scores = self.batch_score(recent_texts)
                for score in scores:
                    self.trend_analyzer.add_score(score)
            
            # 獲取趨勢分析
            trend_data = self.trend_analyzer.get_trend()
            
            # 添加額外分析
            trend_data.update({
                'sentiment_level': self._classify_sentiment_level(trend_data['current']),
                'trend_direction': self._classify_trend_direction(trend_data['trend']),
                'volatility_level': self._classify_volatility_level(trend_data['volatility']),
                'analysis_time': datetime.now().isoformat(),
                'sample_size': len(self.trend_analyzer.scores)
            })
            
            return trend_data
            
        except Exception as e:
            logger.error(f"趨勢分析失敗: {e}")
            return {}
    
    def _classify_sentiment_level(self, score: float) -> str:
        """分類情感水平"""
        if score > 0.6:
            return "非常正面"
        elif score > 0.2:
            return "正面"
        elif score > -0.2:
            return "中性"
        elif score > -0.6:
            return "負面"
        else:
            return "非常負面"
    
    def _classify_trend_direction(self, trend: float) -> str:
        """分類趨勢方向"""
        if trend > 0.01:
            return "上升"
        elif trend < -0.01:
            return "下降"
        else:
            return "穩定"
    
    def _classify_volatility_level(self, volatility: float) -> str:
        """分類波動水平"""
        if volatility > 0.4:
            return "高波動"
        elif volatility > 0.2:
            return "中波動"
        else:
            return "低波動"
    
    def _get_from_cache(self, text: str) -> Optional[SentimentScore]:
        """從快取獲取結果"""
        with self.cache_lock:
            return self.score_cache.get(text)
    
    def _add_to_cache(self, text: str, sentiment_score: SentimentScore):
        """添加到快取"""
        with self.cache_lock:
            # 如果快取已滿，移除最舊的條目
            if len(self.score_cache) >= self.cache_size:
                # 簡單的FIFO策略
                oldest_key = next(iter(self.score_cache))
                del self.score_cache[oldest_key]
            
            self.score_cache[text] = sentiment_score
    
    def _calculate_confidence(self, text: str, score: float) -> float:
        """計算置信度"""
        try:
            # 基於文本長度的置信度
            length_factor = min(1.0, len(text) / 50)
            
            # 基於分數絕對值的置信度
            score_factor = abs(score)
            
            # 基於金融詞彙密度的置信度
            words = text.split()
            financial_words = sum(
                1 for word in words 
                if self.sentiment_dict.get_sentiment_score(word) != 0.0
            )
            
            financial_factor = min(1.0, financial_words / len(words)) if words else 0.0
            
            # 綜合置信度
            confidence = (length_factor * 0.3 + score_factor * 0.4 + financial_factor * 0.3)
            
            return max(0.1, min(1.0, confidence))
            
        except Exception:
            return 0.5
    
    def start_monitoring(self, callback: Callable[[SentimentScore], None]):
        """開始實時監控
        
        Args:
            callback: 監控回調函數
        """
        self.monitoring_enabled = True
        self.monitoring_callbacks.append(callback)
        logger.info("實時監控已啟動")
    
    def stop_monitoring(self):
        """停止實時監控"""
        self.monitoring_enabled = False
        self.monitoring_callbacks.clear()
        logger.info("實時監控已停止")
    
    def _trigger_monitoring_callbacks(self, sentiment_score: SentimentScore):
        """觸發監控回調"""
        for callback in self.monitoring_callbacks:
            try:
                callback(sentiment_score)
            except Exception as e:
                logger.error(f"監控回調執行失敗: {e}")
    
    def clear_cache(self):
        """清空快取"""
        with self.cache_lock:
            self.score_cache.clear()
        logger.info("快取已清空")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """獲取性能統計
        
        Returns:
            性能統計信息
        """
        with self.stats_lock:
            stats = self.stats.copy()
        
        # 計算快取命中率
        total_requests = stats['cache_hits'] + stats['cache_misses']
        cache_hit_rate = stats['cache_hits'] / total_requests if total_requests > 0 else 0
        
        # 計算處理速度
        texts_per_minute = 60 / stats['avg_time_per_text'] if stats['avg_time_per_text'] > 0 else 0
        
        return {
            'total_scored': stats['total_scored'],
            'batch_processed': stats['batch_processed'],
            'avg_time_per_text': stats['avg_time_per_text'],
            'texts_per_minute': texts_per_minute,
            'cache_hit_rate': cache_hit_rate,
            'cache_size': len(self.score_cache),
            'trend_window_size': len(self.trend_analyzer.scores),
            'monitoring_enabled': self.monitoring_enabled
        }
    
    def get_scorer_info(self) -> Dict[str, Any]:
        """獲取評分器資訊
        
        Returns:
            評分器詳細資訊
        """
        return {
            'scorer_name': 'RealtimeSentimentScorer',
            'version': '1.0.0',
            'config': self.config,
            'analyzer_info': self.analyzer.get_analyzer_info(),
            'dictionary_info': self.sentiment_dict.get_dict_info(),
            'performance_stats': self.get_performance_stats(),
            'features': [
                'realtime_scoring',
                'batch_processing',
                'trend_analysis',
                'caching_system',
                'parallel_processing',
                'monitoring_support'
            ]
        }
