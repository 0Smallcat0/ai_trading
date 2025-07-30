# -*- coding: utf-8 -*-
"""統一文本預處理管道

此模組提供統一的文本預處理功能，支援文本清洗、分詞、去停用詞、
詞性標註等多種預處理操作，並支援多種文本格式。

主要功能：
- 文本清洗和標準化
- 中文分詞和詞性標註
- 停用詞過濾
- 文本格式轉換
- 批量處理管道
- 自定義預處理規則

支援的文本格式：
- 純文本 (.txt)
- HTML 格式
- PDF 文檔
- Word 文檔 (.docx)
- JSON 數據

Example:
    >>> from src.nlp.text_processor import TextProcessor
    >>> processor = TextProcessor()
    >>> 
    >>> # 基本文本處理
    >>> processed = processor.process_text("這是一段測試文本。")
    >>> print(processed.tokens)  # ['測試', '文本']
    >>> 
    >>> # 批量處理
    >>> results = processor.batch_process(text_list)
"""

import logging
import re
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class ProcessedText:
    """處理後的文本數據類"""
    original_text: str              # 原始文本
    cleaned_text: str              # 清洗後文本
    tokens: List[str]              # 分詞結果
    pos_tags: List[Tuple[str, str]] # 詞性標註
    filtered_tokens: List[str]      # 過濾後的詞彙
    metadata: Dict[str, Any]       # 元數據
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'original_text': self.original_text,
            'cleaned_text': self.cleaned_text,
            'tokens': self.tokens,
            'pos_tags': self.pos_tags,
            'filtered_tokens': self.filtered_tokens,
            'metadata': self.metadata
        }


class TextCleaner:
    """文本清洗器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 清洗規則配置
        self.remove_html = self.config.get('remove_html', True)
        self.remove_urls = self.config.get('remove_urls', True)
        self.remove_emails = self.config.get('remove_emails', True)
        self.remove_phone = self.config.get('remove_phone', True)
        self.normalize_whitespace = self.config.get('normalize_whitespace', True)
        self.remove_special_chars = self.config.get('remove_special_chars', True)
    
    def clean_text(self, text: str) -> str:
        """清洗文本"""
        if not text:
            return ""
        
        cleaned = text
        
        try:
            # 移除HTML標籤
            if self.remove_html:
                cleaned = re.sub(r'<[^>]+>', '', cleaned)
                cleaned = re.sub(r'&[a-zA-Z]+;', '', cleaned)  # HTML實體
            
            # 移除URL
            if self.remove_urls:
                cleaned = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', cleaned)
                cleaned = re.sub(r'www\.(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', cleaned)
            
            # 移除郵箱
            if self.remove_emails:
                cleaned = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', cleaned)
            
            # 移除電話號碼
            if self.remove_phone:
                cleaned = re.sub(r'1[3-9]\d{9}', '', cleaned)  # 手機號
                cleaned = re.sub(r'\d{3,4}-\d{7,8}', '', cleaned)  # 固定電話
            
            # 移除特殊字符，保留中文、英文、數字和基本標點
            if self.remove_special_chars:
                cleaned = re.sub(r'[^\u4e00-\u9fff\w\s.,!?;:()（）【】""''。，！？；：]', '', cleaned)
            
            # 標準化空白字符
            if self.normalize_whitespace:
                cleaned = re.sub(r'\s+', ' ', cleaned)
                cleaned = cleaned.strip()
            
            return cleaned
            
        except Exception as e:
            logger.error(f"文本清洗失敗: {e}")
            return text


class ChineseTokenizer:
    """中文分詞器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 初始化jieba
        try:
            import jieba
            import jieba.posseg as pseg

            self.jieba = jieba
            self.pseg = pseg
            self.jieba_available = True

            # 設置jieba模式
            self.cut_all = self.config.get('cut_all', False)
            self.use_paddle = self.config.get('use_paddle', False)

            # 載入自定義詞典
            custom_dict = self.config.get('custom_dict')
            if custom_dict and os.path.exists(custom_dict):
                jieba.load_userdict(custom_dict)

            # 添加金融詞彙
            self._add_financial_words()

            logger.info("jieba分詞器初始化完成")

        except ImportError:
            logger.warning("jieba庫未安裝，將使用基本分詞功能")
            self.jieba = None
            self.pseg = None
            self.jieba_available = False
    
    def _add_financial_words(self):
        """添加金融詞彙"""
        if not self.jieba_available:
            return

        financial_words = [
            '股票', '股價', '股市', '漲停', '跌停', '漲幅', '跌幅',
            '市值', '成交量', '換手率', '市盈率', '市淨率',
            '央行', '降準', '降息', '加息', '貨幣政策',
            '上市公司', '財報', '業績', '盈利', '虧損',
            '牛市', '熊市', '震盪', '調整', '反彈'
        ]

        for word in financial_words:
            self.jieba.add_word(word)
    
    def tokenize(self, text: str) -> List[str]:
        """分詞"""
        if not self.jieba_available:
            # 使用基本分詞（按空格和標點符號分割）
            import re
            tokens = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+|\d+', text)
            return [token for token in tokens if len(token) > 1]

        try:
            if self.use_paddle:
                # 使用paddle模式（需要安裝paddlepaddle）
                self.jieba.enable_paddle()
                tokens = list(self.jieba.cut(text, use_paddle=True))
            else:
                tokens = list(self.jieba.cut(text, cut_all=self.cut_all))

            # 過濾空字符串和單字符
            tokens = [token.strip() for token in tokens if len(token.strip()) > 1]

            return tokens
            
        except Exception as e:
            logger.error(f"分詞失敗: {e}")
            return text.split()
    
    def pos_tag(self, text: str) -> List[Tuple[str, str]]:
        """詞性標註"""
        try:
            pos_tags = list(self.pseg.cut(text))
            return [(word, flag) for word, flag in pos_tags if len(word.strip()) > 1]
            
        except Exception as e:
            logger.error(f"詞性標註失敗: {e}")
            tokens = self.tokenize(text)
            return [(token, 'n') for token in tokens]  # 預設為名詞


class StopWordsFilter:
    """停用詞過濾器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 載入停用詞
        self.stop_words = self._load_stop_words()
        
        # 自定義停用詞
        custom_stop_words = self.config.get('custom_stop_words', [])
        self.stop_words.update(custom_stop_words)
        
        logger.info(f"停用詞過濾器初始化完成，共 {len(self.stop_words)} 個停用詞")
    
    def _load_stop_words(self) -> set:
        """載入停用詞表"""
        # 基礎中文停用詞
        basic_stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人',
            '都', '一', '一個', '上', '也', '很', '到', '說', '要', '去',
            '你', '會', '著', '沒有', '看', '好', '自己', '這', '那', '他',
            '她', '它', '我們', '你們', '他們', '這個', '那個', '這些', '那些',
            '什麼', '怎麼', '為什麼', '哪裡', '哪個', '多少', '幾個', '第一',
            '可以', '應該', '能夠', '必須', '需要', '想要', '希望', '覺得',
            '認為', '知道', '明白', '理解', '發現', '看到', '聽到', '感到'
        }
        
        # 金融領域停用詞
        financial_stop_words = {
            '表示', '指出', '認為', '預計', '預期', '估計', '預測',
            '分析師', '專家', '機構', '研究', '報告', '數據', '消息',
            '今日', '昨日', '明日', '本週', '上週', '下週', '本月', '上月',
            '今年', '去年', '明年', '目前', '現在', '將來', '未來'
        }
        
        return basic_stop_words | financial_stop_words
    
    def filter_tokens(self, tokens: List[str]) -> List[str]:
        """過濾停用詞"""
        return [token for token in tokens if token not in self.stop_words]
    
    def add_stop_words(self, words: List[str]):
        """添加停用詞"""
        self.stop_words.update(words)
    
    def remove_stop_words(self, words: List[str]):
        """移除停用詞"""
        self.stop_words -= set(words)


class DocumentParser:
    """文檔解析器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    
    def parse_text_file(self, file_path: str) -> str:
        """解析文本文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"解析文本文件失敗 {file_path}: {e}")
            return ""
    
    def parse_html(self, html_content: str) -> str:
        """解析HTML內容"""
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 移除腳本和樣式
            for script in soup(["script", "style"]):
                script.decompose()
            
            # 提取文本
            text = soup.get_text()
            
            # 清理空行
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except ImportError:
            logger.error("BeautifulSoup庫未安裝，請執行: pip install beautifulsoup4")
            return html_content
        except Exception as e:
            logger.error(f"解析HTML失敗: {e}")
            return html_content
    
    def parse_pdf(self, file_path: str) -> str:
        """解析PDF文件"""
        try:
            import PyPDF2
            
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page in pdf_reader.pages:
                    text += page.extract_text()
            
            return text
            
        except ImportError:
            logger.error("PyPDF2庫未安裝，請執行: pip install PyPDF2")
            return ""
        except Exception as e:
            logger.error(f"解析PDF失敗 {file_path}: {e}")
            return ""
    
    def parse_docx(self, file_path: str) -> str:
        """解析Word文檔"""
        try:
            from docx import Document
            
            doc = Document(file_path)
            text = ""
            
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            return text
            
        except ImportError:
            logger.error("python-docx庫未安裝，請執行: pip install python-docx")
            return ""
        except Exception as e:
            logger.error(f"解析Word文檔失敗 {file_path}: {e}")
            return ""


class TextProcessor:
    """統一文本預處理管道
    
    提供完整的文本預處理功能。
    
    Attributes:
        cleaner: 文本清洗器
        tokenizer: 分詞器
        stop_filter: 停用詞過濾器
        parser: 文檔解析器
        
    Example:
        >>> processor = TextProcessor()
        >>> result = processor.process_text("這是測試文本")
        >>> print(result.tokens)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化文本處理器
        
        Args:
            config: 配置參數
        """
        self.config = config or {}
        
        # 初始化組件
        self.cleaner = TextCleaner(self.config.get('cleaner', {}))
        self.tokenizer = ChineseTokenizer(self.config.get('tokenizer', {}))
        self.stop_filter = StopWordsFilter(self.config.get('stop_filter', {}))
        self.parser = DocumentParser(self.config.get('parser', {}))
        
        # 處理選項
        self.enable_cleaning = self.config.get('enable_cleaning', True)
        self.enable_tokenization = self.config.get('enable_tokenization', True)
        self.enable_pos_tagging = self.config.get('enable_pos_tagging', True)
        self.enable_stop_filtering = self.config.get('enable_stop_filtering', True)
        
        # 統計信息
        self.stats = {
            'total_processed': 0,
            'avg_processing_time': 0.0,
            'total_tokens': 0,
            'avg_tokens_per_text': 0.0
        }
        
        self.lock = threading.Lock()
        
        logger.info("文本處理器初始化完成")
    
    def process_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> ProcessedText:
        """處理單個文本
        
        Args:
            text: 原始文本
            metadata: 元數據
            
        Returns:
            處理結果
        """
        import time
        start_time = time.time()
        
        try:
            if not text:
                return ProcessedText(
                    original_text="",
                    cleaned_text="",
                    tokens=[],
                    pos_tags=[],
                    filtered_tokens=[],
                    metadata=metadata or {}
                )
            
            # 文本清洗
            cleaned_text = text
            if self.enable_cleaning:
                cleaned_text = self.cleaner.clean_text(text)
            
            # 分詞
            tokens = []
            if self.enable_tokenization:
                tokens = self.tokenizer.tokenize(cleaned_text)
            
            # 詞性標註
            pos_tags = []
            if self.enable_pos_tagging:
                pos_tags = self.tokenizer.pos_tag(cleaned_text)
            
            # 停用詞過濾
            filtered_tokens = tokens
            if self.enable_stop_filtering:
                filtered_tokens = self.stop_filter.filter_tokens(tokens)
            
            # 更新統計
            processing_time = time.time() - start_time
            with self.lock:
                self.stats['total_processed'] += 1
                self.stats['total_tokens'] += len(tokens)
                
                # 更新平均處理時間
                total_time = self.stats['avg_processing_time'] * (self.stats['total_processed'] - 1)
                self.stats['avg_processing_time'] = (total_time + processing_time) / self.stats['total_processed']
                
                # 更新平均詞彙數
                self.stats['avg_tokens_per_text'] = self.stats['total_tokens'] / self.stats['total_processed']
            
            return ProcessedText(
                original_text=text,
                cleaned_text=cleaned_text,
                tokens=tokens,
                pos_tags=pos_tags,
                filtered_tokens=filtered_tokens,
                metadata=metadata or {}
            )
            
        except Exception as e:
            logger.error(f"文本處理失敗: {e}")
            return ProcessedText(
                original_text=text,
                cleaned_text=text,
                tokens=[],
                pos_tags=[],
                filtered_tokens=[],
                metadata=metadata or {}
            )
    
    def batch_process(self, texts: List[str], 
                     max_workers: int = 4) -> List[ProcessedText]:
        """批量處理文本
        
        Args:
            texts: 文本列表
            max_workers: 最大工作線程數
            
        Returns:
            處理結果列表
        """
        if not texts:
            return []
        
        try:
            results = [None] * len(texts)
            
            # 小批量直接處理
            if len(texts) <= 10:
                for i, text in enumerate(texts):
                    results[i] = self.process_text(text)
            else:
                # 大批量多線程處理
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_index = {
                        executor.submit(self.process_text, text): i
                        for i, text in enumerate(texts)
                    }
                    
                    for future in as_completed(future_to_index):
                        index = future_to_index[future]
                        try:
                            results[index] = future.result()
                        except Exception as e:
                            logger.error(f"批量處理第{index}個文本失敗: {e}")
                            results[index] = self.process_text("")  # 空結果
            
            logger.info(f"批量處理完成: {len(texts)} 個文本")
            return results
            
        except Exception as e:
            logger.error(f"批量處理失敗: {e}")
            return [self.process_text("") for _ in texts]
    
    def process_file(self, file_path: str) -> ProcessedText:
        """處理文件
        
        Args:
            file_path: 文件路徑
            
        Returns:
            處理結果
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                logger.error(f"文件不存在: {file_path}")
                return self.process_text("")
            
            # 根據文件類型選擇解析器
            suffix = file_path.suffix.lower()
            
            if suffix == '.txt':
                text = self.parser.parse_text_file(str(file_path))
            elif suffix == '.html' or suffix == '.htm':
                with open(file_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                text = self.parser.parse_html(html_content)
            elif suffix == '.pdf':
                text = self.parser.parse_pdf(str(file_path))
            elif suffix == '.docx':
                text = self.parser.parse_docx(str(file_path))
            else:
                logger.warning(f"不支援的文件格式: {suffix}")
                text = self.parser.parse_text_file(str(file_path))
            
            # 添加文件元數據
            metadata = {
                'file_path': str(file_path),
                'file_name': file_path.name,
                'file_size': file_path.stat().st_size,
                'file_type': suffix
            }
            
            return self.process_text(text, metadata)
            
        except Exception as e:
            logger.error(f"處理文件失敗 {file_path}: {e}")
            return self.process_text("")
    
    def get_processor_stats(self) -> Dict[str, Any]:
        """獲取處理器統計信息
        
        Returns:
            統計信息
        """
        with self.lock:
            return self.stats.copy()
    
    def get_processor_info(self) -> Dict[str, Any]:
        """獲取處理器資訊
        
        Returns:
            處理器詳細資訊
        """
        return {
            'processor_name': 'TextProcessor',
            'version': '1.0.0',
            'config': self.config,
            'stats': self.get_processor_stats(),
            'supported_formats': ['.txt', '.html', '.htm', '.pdf', '.docx'],
            'features': [
                'text_cleaning',
                'chinese_tokenization',
                'pos_tagging',
                'stop_words_filtering',
                'batch_processing',
                'multi_format_support'
            ]
        }
