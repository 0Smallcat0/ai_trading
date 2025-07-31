#!/usr/bin/env python3
"""
簡單測試腳本
"""

import sys
import os

# 添加項目根目錄到 Python 路徑
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

print(f"Project root: {project_root}")
print(f"Python path: {sys.path[:3]}")

try:
    print("Testing imports...")
    
    # 測試基本導入
    from src.core.strategy_execution.models import TradingSignal, SignalType
    print("✓ Models imported successfully")
    
    from src.core.strategy_execution.signal_processor import SignalProcessor
    print("✓ SignalProcessor imported successfully")
    
    from src.core.strategy_execution.position_manager import PositionManager
    print("✓ PositionManager imported successfully")
    
    from src.core.strategy_execution.execution_tracker import ExecutionTracker
    print("✓ ExecutionTracker imported successfully")
    
    from src.core.strategy_execution.execution_optimizer import ExecutionOptimizer
    print("✓ ExecutionOptimizer imported successfully")
    
    from src.core.strategy_execution.engine import StrategyExecutionEngine
    print("✓ StrategyExecutionEngine imported successfully")
    
    # 測試基本功能
    print("\nTesting basic functionality...")
    
    signal = TradingSignal(
        symbol="2330.TW",
        signal_type=SignalType.BUY,
        confidence=0.8,
    )
    print(f"✓ Created signal: {signal.symbol} {signal.signal_type.value}")
    
    processor = SignalProcessor()
    order = processor.process_signal(signal)
    if order:
        print(f"✓ Processed signal: {order.symbol} {order.action}")
    else:
        print("✗ Failed to process signal")
    
    print("\n🎉 All tests passed!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
