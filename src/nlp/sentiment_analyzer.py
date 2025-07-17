# -*- coding: utf-8 -*-
"""中文金融情感分析引擎

此模組提供專業的中文金融文本情感分析功能，支援新聞、公告、
研報等多種文本類型的情感識別和評分。

主要功能：
- 中文金融文本情感分析
- 實時情感評分 (-1 到 +1)
- 批量文本處理
- 金融領域專用詞典
- 多種分析模型支援

支援的文本類型：
- 財經新聞
- 公司公告
- 研究報告
- 社交媒體內容
- 分析師評論

Example:
    >>> from src.nlp.sentiment_analyzer import SentimentAnalyzer
    >>> analyzer = SentimentAnalyzer()
    >>> 
    >>> # 單文本分析
    >>> score = analyzer.analyze_sentiment("股價大幅上漲，投資者信心增強")
    >>> print(f"情感分數: {score}")  # 0.75
    >>> 
    >>> # 批量分析
    >>> texts = ["利好消息", "業績下滑", "市場穩定"]
    >>> scores = analyzer.batch_analyze(texts)
"""

import logging
import re
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
import numpy as np
import pandas as pd
from pathlib import Path
import pickle
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class SentimentResult:
    """情感分析結果類"""
    text: str
    score: float  # -1.0 到 1.0
    confidence: float  # 0.0 到 1.0
    label: str  # "positive", "negative", "neutral"
    keywords: List[str]
    timestamp: Optional[str] = None

    def __post_init__(self):
        """後處理初始化"""
        if self.timestamp is None:
            from datetime import datetime
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'text': self.text,
            'score': self.score,
            'confidence': self.confidence,
            'label': self.label,
            'keywords': self.keywords,
            'timestamp': self.timestamp
        }


class SentimentAnalyzer:
    """中文金融情感分析器
    
    提供專業的中文金融文本情感分析功能。
    
    Attributes:
        config: 分析器配置
        model: 情感分析模型
        tokenizer: 文本分詞器
        
    Example:
        >>> analyzer = SentimentAnalyzer({
        ...     'model_type': 'bert',
        ...     'batch_size': 32,
        ...     'max_length': 512
        ... })
        >>> score = analyzer.analyze_sentiment("股市上漲")
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化情感分析器
        
        Args:
            config: 配置參數
                - model_type: 模型類型 ('bert', 'lstm', 'rule_based')
                - batch_size: 批處理大小
                - max_length: 最大文本長度
                - use_gpu: 是否使用GPU
        """
        self.config = config or {}
        
        # 基本配置
        self.model_type = self.config.get('model_type', 'rule_based')
        self.batch_size = self.config.get('batch_size', 32)
        self.max_length = self.config.get('max_length', 512)
        self.use_gpu = self.config.get('use_gpu', False)
        
        # 模型和分詞器
        self.model = None
        self.tokenizer = None
        
        # 金融情感詞典
        self.positive_words = set()
        self.negative_words = set()
        self.financial_terms = {}
        
        # 性能統計
        self.stats = {
            'total_analyzed': 0,
            'total_time': 0.0,
            'avg_time_per_text': 0.0
        }
        
        # 線程鎖
        self.lock = threading.Lock()
        
        # 初始化組件
        self._initialize_components()
        
        logger.info(f"情感分析器初始化完成，模型類型: {self.model_type}")
    
    def _initialize_components(self):
        """初始化分析組件"""
        try:
            # 載入金融情感詞典
            self._load_financial_sentiment_dict()
            
            # 初始化分詞器
            self._initialize_tokenizer()
            
            # 初始化模型
            if self.model_type == 'bert':
                self._initialize_bert_model()
            elif self.model_type == 'lstm':
                self._initialize_lstm_model()
            else:
                self._initialize_rule_based_model()
                
        except Exception as e:
            logger.error(f"組件初始化失敗: {e}")
            # 降級到規則模型
            self.model_type = 'rule_based'
            self._initialize_rule_based_model()
    
    def _load_financial_sentiment_dict(self):
        """載入金融情感詞典"""
        try:
            # 正面詞彙
            positive_words = [
                '上漲', '漲停', '利好', '盈利', '增長', '突破', '強勢', '看好',
                '買入', '推薦', '優秀', '穩定', '回升', '反彈', '創新高', '超預期',
                '利潤', '收益', '分紅', '派息', '業績', '增持', '重組', '併購',
                '擴張', '發展', '機會', '潛力', '價值', '投資', '收購', '合作'
            ]
            
            # 負面詞彙
            negative_words = [
                '下跌', '跌停', '利空', '虧損', '下滑', '破位', '弱勢', '看空',
                '賣出', '減持', '風險', '危機', '暴跌', '崩盤', '套牢', '被套',
                '虧損', '債務', '違約', '退市', '停牌', '調查', '處罰', '訴訟',
                '裁員', '關閉', '破產', '重整', '困難', '問題', '擔憂', '恐慌'
            ]
            
            # 金融術語權重
            financial_terms = {
                # 強烈正面
                '漲停': 1.0, '創新高': 0.9, '突破': 0.8, '超預期': 0.8,
                '大漲': 0.8, '強勢': 0.7, '利好': 0.7, '買入': 0.6,
                
                # 強烈負面
                '跌停': -1.0, '暴跌': -0.9, '崩盤': -0.9, '破位': -0.8,
                '大跌': -0.8, '弱勢': -0.7, '利空': -0.7, '賣出': -0.6,
                
                # 中性偏正面
                '上漲': 0.5, '回升': 0.4, '反彈': 0.4, '穩定': 0.3,
                '增長': 0.5, '盈利': 0.6, '收益': 0.5, '分紅': 0.4,
                
                # 中性偏負面
                '下跌': -0.5, '下滑': -0.4, '調整': -0.3, '震盪': -0.2,
                '虧損': -0.6, '風險': -0.4, '擔憂': -0.3, '壓力': -0.3
            }
            
            self.positive_words = set(positive_words)
            self.negative_words = set(negative_words)
            self.financial_terms = financial_terms
            
            logger.info(f"載入金融詞典: 正面詞 {len(self.positive_words)} 個, 負面詞 {len(self.negative_words)} 個")
            
        except Exception as e:
            logger.error(f"載入金融情感詞典失敗: {e}")
    
    def _initialize_tokenizer(self):
        """初始化分詞器"""
        try:
            import jieba
            import jieba.posseg as pseg
            
            # 添加金融詞彙到jieba詞典
            for term in self.financial_terms.keys():
                jieba.add_word(term)
            
            # 載入停用詞
            self.stop_words = set([
                '的', '了', '在', '是', '我', '有', '和', '就', '不', '人',
                '都', '一', '一個', '上', '也', '很', '到', '說', '要', '去',
                '你', '會', '著', '沒有', '看', '好', '自己', '這'
            ])
            
            self.tokenizer = jieba
            logger.info("jieba分詞器初始化完成")
            
        except ImportError:
            logger.error("jieba庫未安裝，請執行: pip install jieba")
            raise ImportError("缺少jieba依賴")
    
    def _initialize_bert_model(self):
        """初始化BERT模型"""
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch
            
            # 使用中文金融BERT模型（如果可用）
            model_name = self.config.get('bert_model', 'bert-base-chinese')
            
            self.bert_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            
            if self.use_gpu and torch.cuda.is_available():
                self.model = self.model.cuda()
                logger.info("BERT模型已載入到GPU")
            else:
                logger.info("BERT模型已載入到CPU")
                
        except ImportError:
            logger.warning("transformers庫未安裝，降級到規則模型")
            self.model_type = 'rule_based'
            self._initialize_rule_based_model()
        except Exception as e:
            logger.error(f"BERT模型初始化失敗: {e}")
            self.model_type = 'rule_based'
            self._initialize_rule_based_model()
    
    def _initialize_lstm_model(self):
        """初始化LSTM模型"""
        try:
            # 這裡可以載入預訓練的LSTM模型
            # 暫時降級到規則模型
            logger.warning("LSTM模型尚未實現，降級到規則模型")
            self.model_type = 'rule_based'
            self._initialize_rule_based_model()
            
        except Exception as e:
            logger.error(f"LSTM模型初始化失敗: {e}")
            self.model_type = 'rule_based'
            self._initialize_rule_based_model()
    
    def _initialize_rule_based_model(self):
        """初始化規則模型"""
        self.model = 'rule_based'
        logger.info("規則模型初始化完成")
    
    def analyze_sentiment(self, text: str) -> float:
        """分析單個文本的情感
        
        Args:
            text: 待分析文本
            
        Returns:
            情感分數 (-1.0 到 1.0)
        """
        if not text or not text.strip():
            return 0.0
        
        start_time = time.time()
        
        try:
            if self.model_type == 'bert':
                score = self._analyze_with_bert(text)
            elif self.model_type == 'lstm':
                score = self._analyze_with_lstm(text)
            else:
                score = self._analyze_with_rules(text)
            
            # 更新統計
            with self.lock:
                self.stats['total_analyzed'] += 1
                elapsed_time = time.time() - start_time
                self.stats['total_time'] += elapsed_time
                self.stats['avg_time_per_text'] = self.stats['total_time'] / self.stats['total_analyzed']
            
            return max(-1.0, min(1.0, score))  # 確保在範圍內
            
        except Exception as e:
            logger.error(f"情感分析失敗: {e}")
            return 0.0
    
    def _analyze_with_bert(self, text: str) -> float:
        """使用BERT模型分析情感"""
        try:
            import torch
            
            # 文本預處理
            inputs = self.bert_tokenizer(
                text,
                return_tensors="pt",
                max_length=self.max_length,
                truncation=True,
                padding=True
            )
            
            if self.use_gpu and torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            # 模型推理
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                
                # 轉換為情感分數
                probabilities = torch.softmax(logits, dim=-1)
                
                # 假設模型輸出 [negative, neutral, positive]
                if probabilities.shape[-1] == 3:
                    neg_prob = probabilities[0][0].item()
                    neu_prob = probabilities[0][1].item()
                    pos_prob = probabilities[0][2].item()
                    
                    # 計算情感分數
                    score = pos_prob - neg_prob
                else:
                    # 二分類模型
                    score = probabilities[0][1].item() * 2 - 1
                
                return score
                
        except Exception as e:
            logger.error(f"BERT分析失敗: {e}")
            return self._analyze_with_rules(text)
    
    def _analyze_with_lstm(self, text: str) -> float:
        """使用LSTM模型分析情感"""
        # 暫時使用規則模型
        return self._analyze_with_rules(text)
    
    def _analyze_with_rules(self, text: str) -> float:
        """使用規則模型分析情感"""
        try:
            # 文本預處理
            text = self._preprocess_text(text)
            
            # 分詞
            words = list(self.tokenizer.cut(text))
            
            # 計算情感分數
            total_score = 0.0
            word_count = 0
            
            # 否定詞處理
            negation_words = {'不', '沒', '無', '非', '未', '否', '別', '莫'}
            negation_flag = False
            
            for i, word in enumerate(words):
                if word in self.stop_words:
                    continue
                
                # 檢查否定詞
                if word in negation_words:
                    negation_flag = True
                    continue
                
                # 計算詞彙情感分數
                word_score = 0.0
                
                # 檢查金融術語
                if word in self.financial_terms:
                    word_score = self.financial_terms[word]
                elif word in self.positive_words:
                    word_score = 0.5
                elif word in self.negative_words:
                    word_score = -0.5
                
                # 應用否定詞影響
                if negation_flag:
                    word_score = -word_score
                    negation_flag = False
                
                total_score += word_score
                word_count += 1
            
            # 計算平均分數
            if word_count > 0:
                avg_score = total_score / word_count
            else:
                avg_score = 0.0
            
            # 長度調整
            length_factor = min(1.0, len(text) / 100)
            final_score = avg_score * length_factor
            
            return final_score
            
        except Exception as e:
            logger.error(f"規則分析失敗: {e}")
            return 0.0
    
    def _preprocess_text(self, text: str) -> str:
        """文本預處理"""
        # 移除HTML標籤
        text = re.sub(r'<[^>]+>', '', text)
        
        # 移除URL
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # 移除特殊字符，保留中文、英文、數字
        text = re.sub(r'[^\u4e00-\u9fff\w\s]', '', text)
        
        # 移除多餘空格
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def batch_analyze(self, texts: List[str], max_workers: int = 4) -> List[float]:
        """批量分析文本情感
        
        Args:
            texts: 文本列表
            max_workers: 最大工作線程數
            
        Returns:
            情感分數列表
        """
        if not texts:
            return []
        
        start_time = time.time()
        
        try:
            # 單線程處理小批量
            if len(texts) <= 10:
                results = [self.analyze_sentiment(text) for text in texts]
            else:
                # 多線程處理大批量
                results = [0.0] * len(texts)
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # 提交任務
                    future_to_index = {
                        executor.submit(self.analyze_sentiment, text): i
                        for i, text in enumerate(texts)
                    }
                    
                    # 收集結果
                    for future in as_completed(future_to_index):
                        index = future_to_index[future]
                        try:
                            results[index] = future.result()
                        except Exception as e:
                            logger.error(f"批量分析第{index}個文本失敗: {e}")
                            results[index] = 0.0
            
            elapsed_time = time.time() - start_time
            speed = len(texts) / elapsed_time if elapsed_time > 0 else 0
            
            logger.info(f"批量分析完成: {len(texts)} 條文本, 耗時 {elapsed_time:.2f}秒, 速度 {speed:.0f} 條/秒")
            
            return results
            
        except Exception as e:
            logger.error(f"批量分析失敗: {e}")
            return [0.0] * len(texts)
    
    def get_sentiment_distribution(self, texts: List[str]) -> Dict[str, Any]:
        """獲取文本情感分佈統計
        
        Args:
            texts: 文本列表
            
        Returns:
            情感分佈統計
        """
        scores = self.batch_analyze(texts)
        
        if not scores:
            return {}
        
        scores_array = np.array(scores)
        
        # 分類統計
        positive_count = np.sum(scores_array > 0.1)
        negative_count = np.sum(scores_array < -0.1)
        neutral_count = len(scores) - positive_count - negative_count
        
        return {
            'total_texts': len(texts),
            'positive_count': int(positive_count),
            'negative_count': int(negative_count),
            'neutral_count': int(neutral_count),
            'positive_ratio': positive_count / len(scores),
            'negative_ratio': negative_count / len(scores),
            'neutral_ratio': neutral_count / len(scores),
            'avg_sentiment': float(np.mean(scores_array)),
            'sentiment_std': float(np.std(scores_array)),
            'max_sentiment': float(np.max(scores_array)),
            'min_sentiment': float(np.min(scores_array)),
            'sentiment_scores': scores
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """獲取性能統計
        
        Returns:
            性能統計信息
        """
        with self.lock:
            stats = self.stats.copy()
        
        # 計算處理速度
        if stats['avg_time_per_text'] > 0:
            texts_per_minute = 60 / stats['avg_time_per_text']
        else:
            texts_per_minute = 0
        
        return {
            'model_type': self.model_type,
            'total_analyzed': stats['total_analyzed'],
            'total_time': stats['total_time'],
            'avg_time_per_text': stats['avg_time_per_text'],
            'texts_per_minute': texts_per_minute,
            'dictionary_size': {
                'positive_words': len(self.positive_words),
                'negative_words': len(self.negative_words),
                'financial_terms': len(self.financial_terms)
            }
        }
    
    def get_analyzer_info(self) -> Dict[str, Any]:
        """獲取分析器資訊
        
        Returns:
            分析器詳細資訊
        """
        return {
            'analyzer_name': 'SentimentAnalyzer',
            'version': '1.0.0',
            'model_type': self.model_type,
            'config': self.config,
            'supported_features': [
                'single_text_analysis',
                'batch_analysis',
                'sentiment_distribution',
                'financial_domain_optimization',
                'multi_threading_support'
            ],
            'text_types': [
                'financial_news',
                'company_announcements',
                'research_reports',
                'social_media',
                'analyst_comments'
            ]
        }
