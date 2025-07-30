"""
金融自然語言處理模組 (Financial NLP Module)

此模組提供金融領域的自然語言處理功能，包括：
- 市場情緒分析
- 熱點話題報告生成
- 新聞文本分析
- 金融文檔處理

主要功能：
- 基於大語言模型的金融分析報告生成
- 網絡搜索和信息檢索
- 文本情感分析
- 主題建模和趨勢分析
"""

from .report_generator import FinancialReportGenerator, ReportConfig
from .sentiment_analyzer import SentimentAnalyzer, SentimentResult
from .text_processor import TextProcessor

__version__ = "1.0.0"
__author__ = "AI Trading System Team"

__all__ = [
    "FinancialReportGenerator",
    "ReportConfig", 
    "SentimentAnalyzer",
    "SentimentResult",
    "TextProcessor",
]
