"""
增強動態停損測試

測試新增的動態停損功能，包括：
- 自適應停損
- 保本停損
- 高級停損策略
- 性能統計
"""

import pytest
import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.risk.live.dynamic_stop_loss import DynamicStopLoss
from src.risk.live.stop_loss_strategies import StopLossStrategy, StopLossCalculator
from src.risk.live.stop_loss_monitor import StopLossMonitor


class TestDynamicStopLossEnhanced(unittest.TestCase):
    """增強動態停損測試類別"""
    
    def setUp(self):
        """設置測試環境"""
        self.mock_broker = Mock()
        self.dynamic_stop_loss = DynamicStopLoss(self.mock_broker)
        
        # 模擬持倉資訊
        self.mock_positions = {
            "AAPL": {
                "quantity": 100,
                "avg_price": 150.0,
                "current_price": 155.0,
                "market_value": 15500,
                "unrealized_pnl": 500,
            }
        }
        
        # 模擬市場條件
        self.market_conditions = {
            "volatility": 0.025,
            "trend_strength": 0.3,
            "volume_ratio": 1.2,
        }
        
        self.mock_broker.get_positions.return_value = self.mock_positions
    
    def test_calculate_adaptive_stop(self):
        """測試自適應停損計算"""
        calculator = StopLossCalculator()
        
        stop_info = {
            "strategy": StopLossStrategy.TRAILING,
            "params": {
                "base_stop_percent": 0.03,
                "volatility_factor": 1.0,
                "trend_factor": 0.5,
                "volume_factor": 0.2,
                "min_stop_percent": 0.01,
                "max_stop_percent": 0.1,
            },
            "entry_price": 150.0,
            "entry_time": datetime.now(),
        }
        
        adaptive_stop = calculator.calculate_adaptive_stop(
            symbol="AAPL",
            stop_info=stop_info,
            current_price=155.0,
            quantity=100,
            market_conditions=self.market_conditions
        )
        
        self.assertIsNotNone(adaptive_stop)
        self.assertLess(adaptive_stop, 155.0)  # 多頭停損應該低於當前價格
        
        # 檢查停損價格在合理範圍內
        expected_min = 155.0 * (1 - 0.1)  # 最大停損10%
        expected_max = 155.0 * (1 - 0.01)  # 最小停損1%
        self.assertGreaterEqual(adaptive_stop, expected_min)
        self.assertLessEqual(adaptive_stop, expected_max)
    
    def test_calculate_breakeven_stop(self):
        """測試保本停損計算"""
        calculator = StopLossCalculator()
        
        # 測試獲利足夠的情況
        stop_info = {
            "entry_price": 150.0,
            "params": {
                "breakeven_trigger_percent": 0.02,  # 2%觸發
                "breakeven_buffer_percent": 0.005,  # 0.5%緩衝
            }
        }
        
        # 當前價格155，獲利3.33% > 2%觸發條件
        breakeven_stop = calculator.calculate_breakeven_stop(
            stop_info=stop_info,
            current_price=155.0,
            quantity=100
        )
        
        self.assertIsNotNone(breakeven_stop)
        expected_stop = 150.0 * (1 + 0.005)  # 入場價 + 緩衝
        self.assertAlmostEqual(breakeven_stop, expected_stop, places=2)
    
    def test_calculate_breakeven_stop_insufficient_profit(self):
        """測試保本停損計算 - 獲利不足"""
        calculator = StopLossCalculator()
        
        stop_info = {
            "entry_price": 150.0,
            "params": {
                "breakeven_trigger_percent": 0.05,  # 5%觸發
                "breakeven_buffer_percent": 0.005,
            }
        }
        
        # 當前價格152，獲利1.33% < 5%觸發條件
        breakeven_stop = calculator.calculate_breakeven_stop(
            stop_info=stop_info,
            current_price=152.0,
            quantity=100
        )
        
        self.assertIsNone(breakeven_stop)
    
    def test_calculate_breakeven_stop_short_position(self):
        """測試保本停損計算 - 空頭持倉"""
        calculator = StopLossCalculator()
        
        stop_info = {
            "entry_price": 150.0,
            "params": {
                "breakeven_trigger_percent": 0.02,
                "breakeven_buffer_percent": 0.005,
            }
        }
        
        # 空頭：入場150，當前145，獲利3.33%
        breakeven_stop = calculator.calculate_breakeven_stop(
            stop_info=stop_info,
            current_price=145.0,
            quantity=-100
        )
        
        self.assertIsNotNone(breakeven_stop)
        expected_stop = 150.0 * (1 - 0.005)  # 入場價 - 緩衝
        self.assertAlmostEqual(breakeven_stop, expected_stop, places=2)
    
    def test_stop_loss_monitor_advanced_calculation(self):
        """測試停損監控器的高級計算"""
        monitor = StopLossMonitor(self.mock_broker)
        
        stop_info = {
            "strategy": StopLossStrategy.TRAILING,
            "params": {
                "breakeven_trigger_percent": 0.02,
                "breakeven_buffer_percent": 0.005,
            },
            "entry_price": 150.0,
            "entry_time": datetime.now(),
        }
        
        position = {
            "current_price": 155.0,
            "quantity": 100,
        }
        
        market_data = {
            "conditions": self.market_conditions
        }
        
        advanced_stop = monitor.calculate_advanced_stop_price(
            symbol="AAPL",
            stop_info=stop_info,
            position=position,
            market_data=market_data
        )
        
        self.assertIsNotNone(advanced_stop)
        # 應該觸發保本停損
        expected_breakeven = 150.0 * (1 + 0.005)
        self.assertAlmostEqual(advanced_stop, expected_breakeven, places=2)
    
    def test_update_market_conditions(self):
        """測試市場條件更新"""
        monitor = StopLossMonitor(self.mock_broker)
        
        conditions = {
            "volatility": 0.03,
            "trend_strength": 0.5,
            "volume_ratio": 1.5,
        }
        
        monitor.update_market_conditions("AAPL", conditions)
        
        self.assertTrue(hasattr(monitor, 'market_conditions'))
        self.assertIn("AAPL", monitor.market_conditions)
        self.assertEqual(monitor.market_conditions["AAPL"]["volatility"], 0.03)
        self.assertIn("timestamp", monitor.market_conditions["AAPL"])
    
    def test_get_stop_loss_performance_empty(self):
        """測試停損性能統計 - 空數據"""
        monitor = StopLossMonitor(self.mock_broker)
        
        performance = monitor.get_stop_loss_performance()
        
        self.assertEqual(performance["total_adjustments"], 0)
        self.assertEqual(performance["avg_adjustment_size"], 0.0)
        self.assertEqual(performance["adjustment_frequency"], 0.0)
        self.assertEqual(performance["strategy_distribution"], {})
    
    def test_get_stop_loss_performance_with_data(self):
        """測試停損性能統計 - 有數據"""
        monitor = StopLossMonitor(self.mock_broker)
        
        # 模擬調整歷史
        base_time = datetime.now()
        monitor.adjustment_history = [
            {
                "timestamp": base_time,
                "symbol": "AAPL",
                "strategy": "trailing",
                "old_stop_price": 150.0,
                "new_stop_price": 152.0,
            },
            {
                "timestamp": base_time + timedelta(hours=1),
                "symbol": "AAPL", 
                "strategy": "trailing",
                "old_stop_price": 152.0,
                "new_stop_price": 154.0,
            },
            {
                "timestamp": base_time + timedelta(hours=2),
                "symbol": "TSLA",
                "strategy": "volatility_based",
                "old_stop_price": 200.0,
                "new_stop_price": 195.0,
            },
        ]
        
        # 測試所有符號的性能
        performance = monitor.get_stop_loss_performance()
        
        self.assertEqual(performance["total_adjustments"], 3)
        self.assertGreater(performance["avg_adjustment_size"], 0)
        self.assertGreater(performance["adjustment_frequency"], 0)
        self.assertEqual(performance["strategy_distribution"]["trailing"], 2)
        self.assertEqual(performance["strategy_distribution"]["volatility_based"], 1)
        
        # 測試特定符號的性能
        aapl_performance = monitor.get_stop_loss_performance("AAPL")
        self.assertEqual(aapl_performance["total_adjustments"], 2)
        self.assertEqual(aapl_performance["strategy_distribution"]["trailing"], 2)
    
    def test_dynamic_stop_loss_integration(self):
        """測試動態停損整合功能"""
        # 設置停損
        result = self.dynamic_stop_loss.set_position_stop_loss(
            symbol="AAPL",
            strategy=StopLossStrategy.TRAILING,
            custom_params={
                "trail_percent": 0.02,
                "breakeven_trigger_percent": 0.03,
            }
        )
        
        # 檢查設置結果
        self.assertIn("success", result)
        
        # 檢查停損設定
        stops = self.dynamic_stop_loss.get_position_stops()
        self.assertIn("AAPL", stops)
        
        # 檢查調整歷史
        history = self.dynamic_stop_loss.get_adjustment_history("AAPL")
        self.assertIsInstance(history, list)


if __name__ == "__main__":
    unittest.main()
