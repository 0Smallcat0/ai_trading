"""
策略實盤執行引擎模組

此模組提供完整的策略實盤執行功能，包括：
- 策略訊號到訂單的轉換
- 部位大小計算和風險控制
- 執行監控和狀態追蹤
- 執行優化和市場衝擊最小化

主要組件：
- StrategyExecutionEngine: 主執行引擎
- SignalProcessor: 訊號處理器
- PositionManager: 部位管理器
- ExecutionTracker: 執行追蹤器
- ExecutionOptimizer: 執行優化器

使用範例：
    >>> from src.core.strategy_execution import StrategyExecutionEngine
    >>> engine = StrategyExecutionEngine()
    >>> result = engine.execute_strategy_signal(signal_data)
"""

from .engine import StrategyExecutionEngine
from .models import (
    TradingSignal,
    ExecutionOrder,
    ExecutionResult,
    SlippageAnalysis,
    ExecutionConfig,
)
from .signal_processor import SignalProcessor
from .position_manager import PositionManager
from .execution_tracker import ExecutionTracker
from .execution_optimizer import ExecutionOptimizer

__all__ = [
    "StrategyExecutionEngine",
    "TradingSignal",
    "ExecutionOrder", 
    "ExecutionResult",
    "SlippageAnalysis",
    "ExecutionConfig",
    "SignalProcessor",
    "PositionManager",
    "ExecutionTracker",
    "ExecutionOptimizer",
]

__version__ = "1.0.0"
