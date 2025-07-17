#!/usr/bin/env python3
"""
策略執行引擎驗證腳本

此腳本用於驗證策略執行引擎的功能是否正常工作。
"""

import sys
import os
import logging
from datetime import datetime

# 添加項目根目錄到 Python 路徑
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_basic_functionality():
    """測試基本功能"""
    try:
        # 導入模組
        from src.core.strategy_execution import (
            StrategyExecutionEngine,
            TradingSignal,
            ExecutionConfig,
            SignalType,
        )
        
        logger.info("✓ 模組導入成功")
        
        # 創建執行配置
        config = ExecutionConfig(
            dry_run=True,  # 使用模擬模式
            max_position_size=100000,
            risk_limit=0.1,
        )
        logger.info("✓ 執行配置創建成功")
        
        # 創建執行引擎
        engine = StrategyExecutionEngine(config=config, portfolio_value=1000000)
        logger.info("✓ 執行引擎創建成功")
        
        # 創建測試訊號
        signal = TradingSignal(
            symbol="2330.TW",
            signal_type=SignalType.BUY,
            confidence=0.8,
            price=500.0,
            quantity=1000,
            strategy_name="TestStrategy",
        )
        logger.info("✓ 交易訊號創建成功")
        
        # 執行訊號
        result = engine.execute_strategy_signal(signal)
        logger.info("✓ 訊號執行完成")
        
        # 檢查結果
        if result["success"]:
            logger.info("✓ 執行成功: %s", result["message"])
        else:
            logger.error("✗ 執行失敗: %s", result["message"])
            return False
        
        # 獲取執行統計
        stats = engine.get_execution_statistics()
        logger.info("✓ 執行統計獲取成功")
        logger.info("  - 總訊號數: %d", stats["engine_stats"]["total_signals"])
        logger.info("  - 處理訊號數: %d", stats["engine_stats"]["processed_signals"])
        logger.info("  - 執行訂單數: %d", stats["engine_stats"]["executed_orders"])
        
        return True
        
    except Exception as e:
        logger.error("✗ 基本功能測試失敗: %s", e, exc_info=True)
        return False


def test_signal_processor():
    """測試訊號處理器"""
    try:
        from src.core.strategy_execution import SignalProcessor, TradingSignal, SignalType
        
        processor = SignalProcessor()
        logger.info("✓ 訊號處理器創建成功")
        
        # 測試有效訊號
        signal = TradingSignal(
            symbol="2317.TW",
            signal_type=SignalType.SELL,
            confidence=0.7,
            price=100.0,
        )
        
        order = processor.process_signal(signal)
        if order:
            logger.info("✓ 訊號處理成功: %s %s %d", order.symbol, order.action, order.quantity)
        else:
            logger.error("✗ 訊號處理失敗")
            return False
        
        # 測試字典格式訊號
        signal_dict = {
            "symbol": "2454.TW",
            "signal_type": "buy",
            "confidence": 0.9,
            "price": 200.0,
            "quantity": 500,
        }
        
        order = processor.process_signal(signal_dict)
        if order:
            logger.info("✓ 字典訊號處理成功: %s %s %d", order.symbol, order.action, order.quantity)
        else:
            logger.error("✗ 字典訊號處理失敗")
            return False
        
        return True
        
    except Exception as e:
        logger.error("✗ 訊號處理器測試失敗: %s", e, exc_info=True)
        return False


def test_position_manager():
    """測試部位管理器"""
    try:
        from src.core.strategy_execution import (
            PositionManager,
            ExecutionConfig,
            ExecutionOrder,
        )
        
        config = ExecutionConfig(max_position_size=50000, risk_limit=0.05)
        manager = PositionManager(config, portfolio_value=1000000)
        logger.info("✓ 部位管理器創建成功")
        
        # 測試部位計算
        order = ExecutionOrder(
            order_id="test_order",
            symbol="2330.TW",
            action="buy",
            quantity=0,  # 需要計算
        )
        
        quantity, details = manager.calculate_position_size(order, current_price=500.0)
        
        if quantity > 0:
            logger.info("✓ 部位計算成功: %d 股", quantity)
            logger.info("  - 計算方法: %s", details.get("method"))
        else:
            logger.warning("⚠ 部位計算結果為 0: %s", details)
        
        # 測試持倉更新
        manager.update_position("2330.TW", 1000, 500.0, "buy")
        position = manager.get_current_position("2330.TW")
        logger.info("✓ 持倉更新成功: %f", position)
        
        return True
        
    except Exception as e:
        logger.error("✗ 部位管理器測試失敗: %s", e, exc_info=True)
        return False


def test_execution_optimizer():
    """測試執行優化器"""
    try:
        from src.core.strategy_execution import (
            ExecutionOptimizer,
            ExecutionConfig,
            ExecutionOrder,
            ExecutionMode,
        )
        
        config = ExecutionConfig(
            enable_optimization=True,
            batch_size=1000,
            twap_duration=30,
        )
        optimizer = ExecutionOptimizer(config)
        logger.info("✓ 執行優化器創建成功")
        
        # 測試立即執行
        order = ExecutionOrder(
            order_id="test_order",
            symbol="2330.TW",
            action="buy",
            quantity=500,
            execution_mode=ExecutionMode.IMMEDIATE,
        )
        
        sub_orders = optimizer.optimize_execution(order)
        logger.info("✓ 立即執行優化: %d 個子訂單", len(sub_orders))
        
        # 測試 TWAP 執行
        order.quantity = 3000
        order.execution_mode = ExecutionMode.TWAP
        
        sub_orders = optimizer.optimize_execution(order)
        logger.info("✓ TWAP 執行優化: %d 個子訂單", len(sub_orders))
        
        total_quantity = sum(o.quantity for o in sub_orders)
        if total_quantity == 3000:
            logger.info("✓ 數量分配正確")
        else:
            logger.error("✗ 數量分配錯誤: %d != 3000", total_quantity)
            return False
        
        return True
        
    except Exception as e:
        logger.error("✗ 執行優化器測試失敗: %s", e, exc_info=True)
        return False


def test_batch_execution():
    """測試批量執行"""
    try:
        from src.core.strategy_execution import (
            StrategyExecutionEngine,
            TradingSignal,
            ExecutionConfig,
            SignalType,
        )
        
        config = ExecutionConfig(dry_run=True)
        engine = StrategyExecutionEngine(config=config)
        
        # 創建多個測試訊號
        signals = [
            TradingSignal("2330.TW", SignalType.BUY, 0.8, quantity=1000),
            TradingSignal("2317.TW", SignalType.SELL, 0.7, quantity=500),
            TradingSignal("2454.TW", SignalType.BUY, 0.9, quantity=800),
        ]
        
        # 批量執行
        results = engine.execute_signals_batch(signals)
        
        success_count = sum(1 for r in results if r["success"])
        logger.info("✓ 批量執行完成: %d/%d 成功", success_count, len(signals))
        
        if success_count == len(signals):
            logger.info("✓ 所有訊號執行成功")
            return True
        else:
            logger.warning("⚠ 部分訊號執行失敗")
            return False
        
    except Exception as e:
        logger.error("✗ 批量執行測試失敗: %s", e, exc_info=True)
        return False


def main():
    """主函數"""
    logger.info("開始策略執行引擎驗證測試")
    logger.info("=" * 50)
    
    tests = [
        ("基本功能", test_basic_functionality),
        ("訊號處理器", test_signal_processor),
        ("部位管理器", test_position_manager),
        ("執行優化器", test_execution_optimizer),
        ("批量執行", test_batch_execution),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info("\n測試: %s", test_name)
        logger.info("-" * 30)
        
        if test_func():
            passed += 1
            logger.info("✓ %s 測試通過", test_name)
        else:
            logger.error("✗ %s 測試失敗", test_name)
    
    logger.info("\n" + "=" * 50)
    logger.info("測試結果: %d/%d 通過", passed, total)
    
    if passed == total:
        logger.info("🎉 所有測試通過！策略執行引擎功能正常")
        return 0
    else:
        logger.error("❌ 部分測試失敗，請檢查問題")
        return 1


if __name__ == "__main__":
    sys.exit(main())
