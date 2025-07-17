"""
策略執行引擎測試模組

此模組包含策略執行引擎的完整測試套件，包括：
- 單元測試
- 整合測試
- 性能測試
- 錯誤處理測試
"""

import pytest
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# 導入測試目標
from src.core.strategy_execution import (
    StrategyExecutionEngine,
    SignalProcessor,
    PositionManager,
    ExecutionTracker,
    ExecutionOptimizer,
    TradingSignal,
    ExecutionOrder,
    ExecutionConfig,
    SignalType,
    ExecutionMode,
)


class TestTradingSignal(unittest.TestCase):
    """交易訊號模型測試"""
    
    def test_valid_signal_creation(self):
        """測試有效訊號創建"""
        signal = TradingSignal(
            symbol="2330.TW",
            signal_type=SignalType.BUY,
            confidence=0.8,
            price=500.0,
            quantity=1000,
        )
        
        self.assertEqual(signal.symbol, "2330.TW")
        self.assertEqual(signal.signal_type, SignalType.BUY)
        self.assertEqual(signal.confidence, 0.8)
        self.assertEqual(signal.price, 500.0)
        self.assertEqual(signal.quantity, 1000)
    
    def test_invalid_confidence(self):
        """測試無效信心度"""
        with self.assertRaises(ValueError):
            TradingSignal(
                symbol="2330.TW",
                signal_type=SignalType.BUY,
                confidence=1.5,  # 超過1.0
            )
    
    def test_invalid_quantity(self):
        """測試無效數量"""
        with self.assertRaises(ValueError):
            TradingSignal(
                symbol="2330.TW",
                signal_type=SignalType.BUY,
                confidence=0.8,
                quantity=-100,  # 負數
            )


class TestSignalProcessor(unittest.TestCase):
    """訊號處理器測試"""
    
    def setUp(self):
        """設置測試環境"""
        self.processor = SignalProcessor()
    
    def test_process_valid_signal(self):
        """測試處理有效訊號"""
        signal = TradingSignal(
            symbol="2330.TW",
            signal_type=SignalType.BUY,
            confidence=0.8,
            price=500.0,
            quantity=1000,
        )
        
        order = self.processor.process_signal(signal)
        
        self.assertIsNotNone(order)
        self.assertEqual(order.symbol, "2330.TW")
        self.assertEqual(order.action, "buy")
        self.assertEqual(order.quantity, 1000)
    
    def test_process_hold_signal(self):
        """測試處理持有訊號"""
        signal = TradingSignal(
            symbol="2330.TW",
            signal_type=SignalType.HOLD,
            confidence=0.8,
        )
        
        order = self.processor.process_signal(signal)
        
        self.assertIsNone(order)  # 持有訊號不應產生訂單
    
    def test_process_low_confidence_signal(self):
        """測試處理低信心度訊號"""
        config = {"min_confidence": 0.7}
        processor = SignalProcessor(config)
        
        signal = TradingSignal(
            symbol="2330.TW",
            signal_type=SignalType.BUY,
            confidence=0.6,  # 低於閾值
        )
        
        order = processor.process_signal(signal)
        
        self.assertIsNone(order)  # 低信心度訊號應被過濾
    
    def test_process_dict_signal(self):
        """測試處理字典格式訊號"""
        signal_dict = {
            "symbol": "2330.TW",
            "signal_type": "buy",
            "confidence": 0.8,
            "price": 500.0,
            "quantity": 1000,
        }
        
        order = self.processor.process_signal(signal_dict)
        
        self.assertIsNotNone(order)
        self.assertEqual(order.symbol, "2330.TW")
        self.assertEqual(order.action, "buy")
    
    def test_batch_processing(self):
        """測試批量處理"""
        signals = [
            TradingSignal("2330.TW", SignalType.BUY, 0.8),
            TradingSignal("2317.TW", SignalType.SELL, 0.7),
            TradingSignal("2454.TW", SignalType.HOLD, 0.6),  # 應被過濾
        ]
        
        orders = self.processor.process_signals_batch(signals)
        
        self.assertEqual(len(orders), 2)  # 只有2個有效訂單


class TestPositionManager(unittest.TestCase):
    """部位管理器測試"""
    
    def setUp(self):
        """設置測試環境"""
        config = ExecutionConfig(max_position_size=100000, risk_limit=0.1)
        self.manager = PositionManager(config, portfolio_value=1000000)
    
    def test_calculate_position_size(self):
        """測試部位大小計算"""
        order = ExecutionOrder(
            order_id="test_order",
            symbol="2330.TW",
            action="buy",
            quantity=0,  # 需要計算
        )
        
        quantity, details = self.manager.calculate_position_size(
            order, current_price=500.0
        )
        
        self.assertGreater(quantity, 0)
        self.assertIn("method", details)
    
    def test_risk_limit_check(self):
        """測試風險限制檢查"""
        order = ExecutionOrder(
            order_id="test_order",
            symbol="2330.TW",
            action="buy",
            quantity=1000000,  # 過大的數量
        )
        
        quantity, details = self.manager.calculate_position_size(
            order, current_price=500.0
        )
        
        # 應該被風險控制限制
        self.assertEqual(quantity, 0)
        self.assertFalse(details.get("passed", True))
    
    def test_position_update(self):
        """測試持倉更新"""
        self.manager.update_position("2330.TW", 1000, 500.0, "buy")
        
        position = self.manager.get_current_position("2330.TW")
        self.assertEqual(position, 500000.0)  # 1000 * 500
        
        # 賣出部分
        self.manager.update_position("2330.TW", 500, 510.0, "sell")
        
        position = self.manager.get_current_position("2330.TW")
        self.assertEqual(position, 245000.0)  # 500000 - 255000


class TestExecutionOptimizer(unittest.TestCase):
    """執行優化器測試"""
    
    def setUp(self):
        """設置測試環境"""
        config = ExecutionConfig(
            enable_optimization=True,
            batch_size=1000,
            twap_duration=30,
        )
        self.optimizer = ExecutionOptimizer(config)
    
    def test_immediate_execution(self):
        """測試立即執行"""
        order = ExecutionOrder(
            order_id="test_order",
            symbol="2330.TW",
            action="buy",
            quantity=500,  # 小於批次大小
            execution_mode=ExecutionMode.IMMEDIATE,
        )
        
        sub_orders = self.optimizer.optimize_execution(order)
        
        self.assertEqual(len(sub_orders), 1)
        self.assertEqual(sub_orders[0].quantity, 500)
    
    def test_twap_execution(self):
        """測試TWAP執行"""
        order = ExecutionOrder(
            order_id="test_order",
            symbol="2330.TW",
            action="buy",
            quantity=3000,
            execution_mode=ExecutionMode.TWAP,
        )
        
        sub_orders = self.optimizer.optimize_execution(order)
        
        self.assertGreater(len(sub_orders), 1)
        total_quantity = sum(o.quantity for o in sub_orders)
        self.assertEqual(total_quantity, 3000)
    
    def test_large_order_splitting(self):
        """測試大額訂單分割"""
        order = ExecutionOrder(
            order_id="test_order",
            symbol="2330.TW",
            action="buy",
            quantity=5000,  # 大於批次大小
            execution_mode=ExecutionMode.IMMEDIATE,
        )
        
        sub_orders = self.optimizer.optimize_execution(order)
        
        self.assertGreater(len(sub_orders), 1)
        total_quantity = sum(o.quantity for o in sub_orders)
        self.assertEqual(total_quantity, 5000)


class TestExecutionTracker(unittest.TestCase):
    """執行追蹤器測試"""
    
    def setUp(self):
        """設置測試環境"""
        self.tracker = ExecutionTracker()
    
    def test_track_order(self):
        """測試訂單追蹤"""
        order = ExecutionOrder(
            order_id="test_order",
            symbol="2330.TW",
            action="buy",
            quantity=1000,
        )
        
        tracking_id = self.tracker.track_order(order)
        
        self.assertEqual(tracking_id, "test_order")
        
        status = self.tracker.get_order_status("test_order")
        self.assertIsNotNone(status)
        self.assertEqual(status["status"], "active")
    
    def test_slippage_analysis(self):
        """測試滑點分析"""
        analysis = self.tracker.analyze_slippage(
            symbol="2330.TW",
            expected_price=500.0,
            actual_price=501.0,
            execution_time_ms=100.0,
            volume_ratio=0.01,
        )
        
        self.assertEqual(analysis.symbol, "2330.TW")
        self.assertGreater(analysis.slippage_bps, 0)


class TestStrategyExecutionEngine(unittest.TestCase):
    """策略執行引擎整合測試"""
    
    def setUp(self):
        """設置測試環境"""
        config = ExecutionConfig(dry_run=True)  # 使用模擬模式
        self.engine = StrategyExecutionEngine(config=config)
    
    def test_execute_strategy_signal(self):
        """測試執行策略訊號"""
        signal = TradingSignal(
            symbol="2330.TW",
            signal_type=SignalType.BUY,
            confidence=0.8,
            price=500.0,
            quantity=1000,
        )
        
        result = self.engine.execute_strategy_signal(signal)
        
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        self.assertIn("execution_id", result)
    
    def test_batch_execution(self):
        """測試批量執行"""
        signals = [
            TradingSignal("2330.TW", SignalType.BUY, 0.8, quantity=1000),
            TradingSignal("2317.TW", SignalType.SELL, 0.7, quantity=500),
        ]
        
        results = self.engine.execute_signals_batch(signals)
        
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertIn("success", result)
    
    def test_execution_statistics(self):
        """測試執行統計"""
        # 執行一些訊號
        signal = TradingSignal("2330.TW", SignalType.BUY, 0.8, quantity=1000)
        self.engine.execute_strategy_signal(signal)
        
        stats = self.engine.get_execution_statistics()
        
        self.assertIn("engine_stats", stats)
        self.assertIn("tracker_stats", stats)
        self.assertGreater(stats["engine_stats"]["total_signals"], 0)
    
    @patch('src.core.strategy_execution.engine.TradeExecutionService')
    def test_with_trade_service(self, mock_trade_service):
        """測試與交易服務整合"""
        # 模擬交易服務
        mock_service = Mock()
        mock_service.submit_order.return_value = (True, "成功", "order_123")
        
        config = ExecutionConfig(dry_run=False)
        engine = StrategyExecutionEngine(
            config=config,
            trade_service=mock_service
        )
        
        signal = TradingSignal("2330.TW", SignalType.BUY, 0.8, quantity=1000)
        result = engine.execute_strategy_signal(signal)
        
        self.assertTrue(result["success"])


class TestErrorHandling(unittest.TestCase):
    """錯誤處理測試"""
    
    def test_invalid_signal_data(self):
        """測試無效訊號數據處理"""
        processor = SignalProcessor()
        
        # 測試無效數據類型
        result = processor.process_signal("invalid_data")
        self.assertIsNone(result)
        
        # 測試缺少必要欄位的字典
        invalid_dict = {"symbol": "2330.TW"}  # 缺少signal_type和confidence
        result = processor.process_signal(invalid_dict)
        self.assertIsNone(result)
    
    def test_engine_error_recovery(self):
        """測試引擎錯誤恢復"""
        engine = StrategyExecutionEngine()
        
        # 測試處理無效訊號
        result = engine.execute_strategy_signal("invalid_signal")
        
        self.assertFalse(result["success"])
        self.assertIn("error", result["message"].lower())


if __name__ == "__main__":
    # 運行測試
    unittest.main(verbosity=2)
