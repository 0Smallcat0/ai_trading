# -*- coding: utf-8 -*-
"""
簡化NLP模組 - MVP版本

此模組提供MVP版本所需的基本文本分析功能。
複雜的NLP功能已移除以簡化系統。

主要功能：
- 基本文本分析適配器
- 新聞爬蟲存根
- 新聞分類存根

版本: MVP 1.0
"""

__version__ = "1.0.0"
__author__ = "AI Trading System MVP Team"

# 導出基本功能
__all__ = [
    "text_analysis_adapter",
    "news_crawler", 
    "news_classifier"
]
