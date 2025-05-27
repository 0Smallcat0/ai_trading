"""訊號產生器模組

此模組包含各種交易訊號產生器的實現，
將原本的大型 signal_gen.py 文件拆分為多個專門的模組。

模組結構：
- base_signal_generator.py: 基礎訊號產生器類別
- fundamental_signals.py: 基本面策略訊號產生器
- technical_signals.py: 技術分析訊號產生器
- sentiment_signals.py: 情緒分析訊號產生器
- ai_model_signals.py: AI 模型訊號產生器
- signal_combiner.py: 訊號合併器
"""

from .base_signal_generator import BaseSignalGenerator
from .fundamental_signals import FundamentalSignalGenerator
from .technical_signals import TechnicalSignalGenerator
from .sentiment_signals import SentimentSignalGenerator
from .ai_model_signals import AIModelSignalGenerator
from .signal_combiner import SignalCombiner

# 主要的訊號產生器類別，整合所有功能
from .main_signal_generator import SignalGenerator

__all__ = [
    "BaseSignalGenerator",
    "FundamentalSignalGenerator",
    "TechnicalSignalGenerator",
    "SentimentSignalGenerator",
    "AIModelSignalGenerator",
    "SignalCombiner",
    "SignalGenerator",
]
