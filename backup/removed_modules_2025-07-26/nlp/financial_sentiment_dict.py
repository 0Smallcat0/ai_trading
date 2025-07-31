# -*- coding: utf-8 -*-
"""金融領域情感詞典

此模組提供專業的金融領域情感詞典和標註體系，
包含股市術語、財經詞彙的詳細情感標註。

主要功能：
- 金融專用情感詞典
- 情感強度標註
- 詞彙分類管理
- 動態詞典更新
- 領域特定優化

詞典分類：
- 股價相關詞彙
- 業績財務詞彙
- 政策監管詞彙
- 市場情緒詞彙
- 行業分析詞彙

Example:
    >>> from src.nlp.financial_sentiment_dict import FinancialSentimentDict
    >>> sentiment_dict = FinancialSentimentDict()
    >>> 
    >>> # 獲取詞彙情感分數
    >>> score = sentiment_dict.get_sentiment_score("漲停")
    >>> print(f"漲停的情感分數: {score}")  # 1.0
    >>> 
    >>> # 獲取詞彙分類
    >>> category = sentiment_dict.get_word_category("漲停")
    >>> print(f"漲停的分類: {category}")  # stock_price
"""

import logging
import json
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

# 設定日誌
logger = logging.getLogger(__name__)


class SentimentCategory(Enum):
    """情感分類枚舉"""
    STOCK_PRICE = "stock_price"      # 股價相關
    PERFORMANCE = "performance"      # 業績財務
    POLICY = "policy"               # 政策監管
    MARKET_EMOTION = "market_emotion" # 市場情緒
    INDUSTRY = "industry"           # 行業分析
    TRADING = "trading"             # 交易相關
    RISK = "risk"                   # 風險相關
    GENERAL = "general"             # 一般詞彙


@dataclass
class SentimentWord:
    """情感詞彙數據類"""
    word: str                       # 詞彙
    sentiment_score: float          # 情感分數 (-1.0 到 1.0)
    category: SentimentCategory     # 分類
    intensity: float               # 強度 (0.0 到 1.0)
    frequency: int                 # 使用頻率
    synonyms: List[str]            # 同義詞
    antonyms: List[str]            # 反義詞
    context_words: List[str]       # 上下文詞彙


class FinancialSentimentDict:
    """金融領域情感詞典
    
    提供專業的金融領域情感詞典和標註功能。
    
    Attributes:
        sentiment_dict: 情感詞典
        category_dict: 分類詞典
        
    Example:
        >>> sentiment_dict = FinancialSentimentDict()
        >>> score = sentiment_dict.get_sentiment_score("利好")
        >>> category = sentiment_dict.get_word_category("利好")
    """
    
    def __init__(self, dict_path: Optional[str] = None):
        """初始化金融情感詞典
        
        Args:
            dict_path: 自定義詞典路徑
        """
        self.dict_path = dict_path
        
        # 詞典存儲
        self.sentiment_dict: Dict[str, SentimentWord] = {}
        self.category_dict: Dict[SentimentCategory, Set[str]] = {
            category: set() for category in SentimentCategory
        }
        
        # 統計信息
        self.stats = {
            'total_words': 0,
            'positive_words': 0,
            'negative_words': 0,
            'neutral_words': 0,
            'categories': {}
        }
        
        # 初始化詞典
        self._initialize_dictionary()
        
        logger.info(f"金融情感詞典初始化完成，共 {len(self.sentiment_dict)} 個詞彙")
    
    def _initialize_dictionary(self):
        """初始化詞典數據"""
        # 如果有自定義詞典，先載入
        if self.dict_path and Path(self.dict_path).exists():
            self._load_custom_dictionary()
        
        # 載入預設詞典
        self._load_default_dictionary()
        
        # 更新統計信息
        self._update_statistics()
    
    def _load_default_dictionary(self):
        """載入預設金融情感詞典"""
        # 股價相關詞彙
        stock_price_words = [
            # 強烈正面 (0.8-1.0)
            ("漲停", 1.0, 1.0), ("封漲停", 1.0, 1.0), ("一字漲停", 1.0, 1.0),
            ("創新高", 0.9, 0.9), ("歷史新高", 0.9, 0.9), ("突破", 0.8, 0.8),
            ("大漲", 0.8, 0.8), ("暴漲", 0.9, 0.9), ("飆漲", 0.9, 0.9),
            
            # 中等正面 (0.4-0.7)
            ("上漲", 0.6, 0.7), ("漲幅", 0.5, 0.6), ("上升", 0.5, 0.6),
            ("回升", 0.5, 0.6), ("反彈", 0.6, 0.7), ("走高", 0.5, 0.6),
            ("攀升", 0.6, 0.7), ("拉升", 0.6, 0.7), ("推高", 0.5, 0.6),
            
            # 強烈負面 (-0.8 到 -1.0)
            ("跌停", -1.0, 1.0), ("封跌停", -1.0, 1.0), ("一字跌停", -1.0, 1.0),
            ("暴跌", -0.9, 0.9), ("崩盤", -1.0, 1.0), ("大跌", -0.8, 0.8),
            ("重挫", -0.8, 0.8), ("慘跌", -0.9, 0.9), ("血崩", -1.0, 1.0),
            
            # 中等負面 (-0.4 到 -0.7)
            ("下跌", -0.6, 0.7), ("跌幅", -0.5, 0.6), ("下滑", -0.5, 0.6),
            ("回落", -0.4, 0.5), ("調整", -0.3, 0.4), ("走低", -0.5, 0.6),
            ("下探", -0.5, 0.6), ("破位", -0.7, 0.7), ("跳水", -0.8, 0.8)
        ]
        
        for word, score, intensity in stock_price_words:
            self._add_word(word, score, SentimentCategory.STOCK_PRICE, intensity)
        
        # 業績財務詞彙
        performance_words = [
            # 正面
            ("盈利", 0.7, 0.8), ("獲利", 0.7, 0.8), ("淨利潤", 0.6, 0.7),
            ("營收增長", 0.8, 0.8), ("業績增長", 0.8, 0.8), ("超預期", 0.8, 0.9),
            ("分紅", 0.6, 0.7), ("派息", 0.6, 0.7), ("送股", 0.5, 0.6),
            ("增持", 0.6, 0.7), ("回購", 0.7, 0.7), ("擴股", 0.5, 0.6),
            
            # 負面
            ("虧損", -0.8, 0.8), ("虧本", -0.8, 0.8), ("淨虧損", -0.8, 0.8),
            ("營收下滑", -0.7, 0.7), ("業績下滑", -0.7, 0.7), ("不及預期", -0.6, 0.7),
            ("減持", -0.6, 0.7), ("拋售", -0.7, 0.8), ("清倉", -0.8, 0.8),
            ("債務", -0.5, 0.6), ("負債", -0.5, 0.6), ("資金鏈", -0.6, 0.7)
        ]
        
        for word, score, intensity in performance_words:
            self._add_word(word, score, SentimentCategory.PERFORMANCE, intensity)
        
        # 政策監管詞彙
        policy_words = [
            # 正面
            ("利好政策", 0.8, 0.8), ("政策支持", 0.7, 0.7), ("減稅", 0.6, 0.7),
            ("降準", 0.7, 0.8), ("降息", 0.7, 0.8), ("刺激政策", 0.7, 0.7),
            ("扶持", 0.6, 0.6), ("補貼", 0.5, 0.6), ("優惠", 0.5, 0.6),
            
            # 負面
            ("利空政策", -0.8, 0.8), ("監管", -0.5, 0.6), ("調控", -0.5, 0.6),
            ("加息", -0.6, 0.7), ("緊縮", -0.7, 0.7), ("限制", -0.6, 0.6),
            ("處罰", -0.7, 0.8), ("罰款", -0.6, 0.7), ("調查", -0.6, 0.7),
            ("停牌", -0.8, 0.8), ("退市", -0.9, 0.9), ("摘牌", -0.8, 0.8)
        ]
        
        for word, score, intensity in policy_words:
            self._add_word(word, score, SentimentCategory.POLICY, intensity)
        
        # 市場情緒詞彙
        emotion_words = [
            # 正面
            ("樂觀", 0.7, 0.7), ("看好", 0.7, 0.7), ("信心", 0.6, 0.7),
            ("熱情", 0.6, 0.6), ("積極", 0.6, 0.6), ("強勢", 0.7, 0.7),
            ("活躍", 0.5, 0.6), ("火熱", 0.7, 0.7), ("追捧", 0.6, 0.7),
            
            # 負面
            ("悲觀", -0.7, 0.7), ("看空", -0.7, 0.7), ("恐慌", -0.8, 0.8),
            ("擔憂", -0.6, 0.6), ("焦慮", -0.6, 0.6), ("弱勢", -0.6, 0.6),
            ("低迷", -0.6, 0.6), ("冷淡", -0.5, 0.5), ("拋壓", -0.7, 0.7),
            ("套牢", -0.7, 0.7), ("被套", -0.7, 0.7), ("割肉", -0.8, 0.8)
        ]
        
        for word, score, intensity in emotion_words:
            self._add_word(word, score, SentimentCategory.MARKET_EMOTION, intensity)
        
        # 交易相關詞彙
        trading_words = [
            # 正面
            ("買入", 0.6, 0.7), ("建倉", 0.5, 0.6), ("加倉", 0.6, 0.6),
            ("抄底", 0.7, 0.7), ("逢低買入", 0.7, 0.7), ("做多", 0.6, 0.6),
            ("持有", 0.3, 0.4), ("長期持有", 0.4, 0.5),
            
            # 負面
            ("賣出", -0.6, 0.7), ("清倉", -0.8, 0.8), ("減倉", -0.5, 0.6),
            ("止損", -0.6, 0.7), ("平倉", -0.4, 0.5), ("做空", -0.6, 0.6),
            ("拋售", -0.7, 0.8), ("出貨", -0.6, 0.7)
        ]
        
        for word, score, intensity in trading_words:
            self._add_word(word, score, SentimentCategory.TRADING, intensity)
        
        # 風險相關詞彙
        risk_words = [
            ("風險", -0.5, 0.6), ("危機", -0.8, 0.8), ("警告", -0.6, 0.7),
            ("威脅", -0.7, 0.7), ("困難", -0.5, 0.6), ("問題", -0.4, 0.5),
            ("挑戰", -0.3, 0.4), ("壓力", -0.4, 0.5), ("不確定", -0.4, 0.5),
            ("波動", -0.3, 0.4), ("震盪", -0.3, 0.4), ("動盪", -0.6, 0.6)
        ]
        
        for word, score, intensity in risk_words:
            self._add_word(word, score, SentimentCategory.RISK, intensity)
    
    def _add_word(self, word: str, sentiment_score: float, 
                  category: SentimentCategory, intensity: float,
                  synonyms: List[str] = None, antonyms: List[str] = None,
                  context_words: List[str] = None):
        """添加詞彙到詞典"""
        sentiment_word = SentimentWord(
            word=word,
            sentiment_score=sentiment_score,
            category=category,
            intensity=intensity,
            frequency=0,
            synonyms=synonyms or [],
            antonyms=antonyms or [],
            context_words=context_words or []
        )
        
        self.sentiment_dict[word] = sentiment_word
        self.category_dict[category].add(word)
    
    def get_sentiment_score(self, word: str) -> float:
        """獲取詞彙情感分數
        
        Args:
            word: 詞彙
            
        Returns:
            情感分數 (-1.0 到 1.0)，未找到返回 0.0
        """
        if word in self.sentiment_dict:
            return self.sentiment_dict[word].sentiment_score
        return 0.0
    
    def get_word_category(self, word: str) -> Optional[SentimentCategory]:
        """獲取詞彙分類
        
        Args:
            word: 詞彙
            
        Returns:
            詞彙分類，未找到返回 None
        """
        if word in self.sentiment_dict:
            return self.sentiment_dict[word].category
        return None
    
    def get_word_intensity(self, word: str) -> float:
        """獲取詞彙強度
        
        Args:
            word: 詞彙
            
        Returns:
            詞彙強度 (0.0 到 1.0)，未找到返回 0.0
        """
        if word in self.sentiment_dict:
            return self.sentiment_dict[word].intensity
        return 0.0
    
    def get_words_by_category(self, category: SentimentCategory) -> Set[str]:
        """獲取指定分類的所有詞彙
        
        Args:
            category: 詞彙分類
            
        Returns:
            詞彙集合
        """
        return self.category_dict.get(category, set())
    
    def get_positive_words(self, threshold: float = 0.1) -> List[str]:
        """獲取正面詞彙
        
        Args:
            threshold: 情感分數閾值
            
        Returns:
            正面詞彙列表
        """
        return [
            word for word, data in self.sentiment_dict.items()
            if data.sentiment_score > threshold
        ]
    
    def get_negative_words(self, threshold: float = -0.1) -> List[str]:
        """獲取負面詞彙
        
        Args:
            threshold: 情感分數閾值
            
        Returns:
            負面詞彙列表
        """
        return [
            word for word, data in self.sentiment_dict.items()
            if data.sentiment_score < threshold
        ]
    
    def add_custom_word(self, word: str, sentiment_score: float,
                       category: SentimentCategory, intensity: float = 0.5):
        """添加自定義詞彙
        
        Args:
            word: 詞彙
            sentiment_score: 情感分數
            category: 分類
            intensity: 強度
        """
        self._add_word(word, sentiment_score, category, intensity)
        self._update_statistics()
        logger.info(f"添加自定義詞彙: {word} (分數: {sentiment_score}, 分類: {category.value})")
    
    def update_word_frequency(self, word: str):
        """更新詞彙使用頻率
        
        Args:
            word: 詞彙
        """
        if word in self.sentiment_dict:
            self.sentiment_dict[word].frequency += 1
    
    def get_high_frequency_words(self, top_n: int = 50) -> List[Tuple[str, int]]:
        """獲取高頻詞彙
        
        Args:
            top_n: 返回前N個詞彙
            
        Returns:
            (詞彙, 頻率) 元組列表
        """
        word_freq = [
            (word, data.frequency) 
            for word, data in self.sentiment_dict.items()
        ]
        
        return sorted(word_freq, key=lambda x: x[1], reverse=True)[:top_n]
    
    def _update_statistics(self):
        """更新統計信息"""
        self.stats['total_words'] = len(self.sentiment_dict)
        self.stats['positive_words'] = len(self.get_positive_words())
        self.stats['negative_words'] = len(self.get_negative_words())
        self.stats['neutral_words'] = (
            self.stats['total_words'] - 
            self.stats['positive_words'] - 
            self.stats['negative_words']
        )
        
        # 分類統計
        for category in SentimentCategory:
            self.stats['categories'][category.value] = len(self.category_dict[category])
    
    def _load_custom_dictionary(self):
        """載入自定義詞典"""
        try:
            with open(self.dict_path, 'r', encoding='utf-8') as f:
                custom_dict = json.load(f)
            
            for word_data in custom_dict.get('words', []):
                self._add_word(
                    word_data['word'],
                    word_data['sentiment_score'],
                    SentimentCategory(word_data['category']),
                    word_data.get('intensity', 0.5),
                    word_data.get('synonyms', []),
                    word_data.get('antonyms', []),
                    word_data.get('context_words', [])
                )
            
            logger.info(f"載入自定義詞典: {len(custom_dict.get('words', []))} 個詞彙")
            
        except Exception as e:
            logger.error(f"載入自定義詞典失敗: {e}")
    
    def save_dictionary(self, save_path: str):
        """保存詞典到文件
        
        Args:
            save_path: 保存路徑
        """
        try:
            dict_data = {
                'version': '1.0.0',
                'created_at': str(pd.Timestamp.now()),
                'statistics': self.stats,
                'words': []
            }
            
            for word, data in self.sentiment_dict.items():
                dict_data['words'].append({
                    'word': word,
                    'sentiment_score': data.sentiment_score,
                    'category': data.category.value,
                    'intensity': data.intensity,
                    'frequency': data.frequency,
                    'synonyms': data.synonyms,
                    'antonyms': data.antonyms,
                    'context_words': data.context_words
                })
            
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(dict_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"詞典已保存到: {save_path}")
            
        except Exception as e:
            logger.error(f"保存詞典失敗: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """獲取詞典統計信息
        
        Returns:
            統計信息字典
        """
        return self.stats.copy()
    
    def get_dict_info(self) -> Dict[str, Any]:
        """獲取詞典資訊
        
        Returns:
            詞典詳細資訊
        """
        return {
            'dict_name': 'FinancialSentimentDict',
            'version': '1.0.0',
            'total_words': len(self.sentiment_dict),
            'categories': list(SentimentCategory),
            'statistics': self.stats,
            'features': [
                'financial_domain_optimization',
                'sentiment_scoring',
                'category_classification',
                'intensity_weighting',
                'frequency_tracking',
                'custom_word_support'
            ]
        }
