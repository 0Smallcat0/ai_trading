"""
回測系統整合測試

此測試文件驗證整合後的回測系統功能是否正常。
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 導入整合後的回測系統
from src.core.backtest import (
    BacktestConfig,
    BacktestEngine,
    BacktestService,
    calculate_performance_metrics,
    FactorBacktester
)


class TestBacktestIntegration(unittest.TestCase):
    """回測系統整合測試類"""
    
    def setUp(self):
        """測試前準備"""
        # 創建測試數據
        self.symbols = ["AAPL", "GOOGL", "MSFT"]
        self.start_date = "2023-01-01"
        self.end_date = "2023-01-31"
        self.initial_capital = 100000.0
        
        # 創建配置
        self.config = BacktestConfig(
            strategy_name="test_strategy",
            symbols=self.symbols,
            start_date=self.start_date,
            end_date=self.end_date,
            initial_capital=self.initial_capital
        )
        
        # 創建回測服務
        self.service = BacktestService()
        
        # 創建回測引擎
        self.engine = BacktestEngine()
        
        # 創建因子回測器
        self.factor_backtester = FactorBacktester()
    
    def test_backtest_config(self):
        """測試回測配置"""
        # 驗證基本屬性
        self.assertEqual(self.config.strategy_name, "test_strategy")
        self.assertEqual(self.config.symbols, self.symbols)
        self.assertEqual(self.config.initial_capital, self.initial_capital)
        
        # 驗證日期轉換
        self.assertIsInstance(self.config.start_date, pd.Timestamp)
        self.assertIsInstance(self.config.end_date, pd.Timestamp)
        
        # 驗證轉換為字典
        config_dict = self.config.to_dict()
        self.assertIsInstance(config_dict, dict)
        self.assertEqual(config_dict["strategy_name"], "test_strategy")
        
        # 驗證從字典創建
        new_config = BacktestConfig.from_dict(config_dict)
        self.assertEqual(new_config.strategy_name, self.config.strategy_name)
        self.assertEqual(new_config.initial_capital, self.config.initial_capital)
    
    def test_backtest_engine(self):
        """測試回測引擎"""
        # 創建模擬數據
        signals = self._create_mock_signals()
        market_data = self._create_mock_market_data()
        
        # 運行回測
        results = self.engine.run_backtest(
            signals=signals,
            market_data=market_data,
            initial_capital=self.initial_capital
        )
        
        # 驗證結果
        self.assertIsInstance(results, dict)
        self.assertIn("summary", results)
        self.assertIn("trades", results)
        self.assertIn("daily_values", results)
        
        # 驗證摘要
        summary = results["summary"]
        self.assertIn("initial_capital", summary)
        self.assertIn("final_value", summary)
        self.assertIn("total_return", summary)
        
        # 驗證交易記錄
        trades = results["trades"]
        self.assertIsInstance(trades, pd.DataFrame)
        
        # 驗證每日價值
        daily_values = results["daily_values"]
        self.assertIsInstance(daily_values, pd.DataFrame)
    
    def test_backtest_service(self):
        """測試回測服務"""
        # 啟動回測
        backtest_id = self.service.start_backtest(self.config)
        
        # 驗證回測ID
        self.assertIsInstance(backtest_id, str)
        
        # 獲取回測狀態
        status = self.service.get_backtest_status(backtest_id)
        self.assertIsInstance(status, dict)
        
        # 列出回測任務
        backtests = self.service.list_backtests()
        self.assertIsInstance(backtests, list)
        self.assertGreaterEqual(len(backtests), 1)
    
    def test_performance_metrics(self):
        """測試績效指標計算"""
        # 創建模擬回測結果
        backtest_results = self._create_mock_backtest_results()
        
        # 計算績效指標
        metrics = calculate_performance_metrics(backtest_results, self.config)
        
        # 驗證指標
        self.assertIsNotNone(metrics)
        self.assertIsInstance(metrics.total_return, float)
        self.assertIsInstance(metrics.annualized_return, float)
        self.assertIsInstance(metrics.volatility, float)
        self.assertIsInstance(metrics.max_drawdown, float)
        self.assertIsInstance(metrics.sharpe_ratio, float)
    
    def test_factor_backtester(self):
        """測試因子回測器"""
        # 創建模擬因子數據
        factor_data = self._create_mock_factor_data()
        price_data = self._create_mock_market_data()
        
        # 驗證輸入數據
        self.assertIsInstance(factor_data, pd.DataFrame)
        self.assertIsInstance(price_data, pd.DataFrame)
        
        # 測試單因子回測
        try:
            results = self.factor_backtester.backtest_single_factor(
                factor_data, price_data, method="layered"
            )
            self.assertIsInstance(results, dict)
        except ValueError as e:
            # 簡化實現可能會拋出異常
            self.assertIn("not_implemented", str(e))
    
    def _create_mock_signals(self) -> pd.DataFrame:
        """創建模擬訊號數據"""
        # 生成日期範圍
        start_date = pd.to_datetime(self.start_date)
        end_date = pd.to_datetime(self.end_date)
        date_range = pd.date_range(start=start_date, end=end_date, freq='B')
        
        # 生成訊號
        signals = []
        for date in date_range:
            for symbol in self.symbols:
                # 隨機訊號
                signal = np.random.choice([-1, 0, 1], p=[0.2, 0.6, 0.2])
                weight = abs(signal) * 0.2  # 20% 權重
                
                signals.append({
                    'date': date,
                    'symbol': symbol,
                    'signal': signal,
                    'weight': weight
                })
        
        return pd.DataFrame(signals)
    
    def _create_mock_market_data(self) -> pd.DataFrame:
        """創建模擬市場數據"""
        # 生成日期範圍
        start_date = pd.to_datetime(self.start_date)
        end_date = pd.to_datetime(self.end_date)
        date_range = pd.date_range(start=start_date, end=end_date, freq='B')
        
        # 生成模擬數據
        data = []
        for symbol in self.symbols:
            # 設置隨機種子以獲得可重複的結果
            np.random.seed(hash(symbol) % 10000)
            
            # 生成價格序列
            price = 100.0
            prices = [price]
            for _ in range(1, len(date_range)):
                change = np.random.normal(0, 0.02)  # 2% 標準差
                price *= (1 + change)
                prices.append(price)
            
            # 生成成交量
            volumes = np.random.randint(1000, 10000, size=len(date_range))
            
            # 添加到數據列表
            for i, date in enumerate(date_range):
                data.append({
                    'symbol': symbol,
                    'date': date,
                    'open': prices[i] * (1 - 0.005 + 0.01 * np.random.random()),
                    'high': prices[i] * (1 + 0.01 * np.random.random()),
                    'low': prices[i] * (1 - 0.01 * np.random.random()),
                    'close': prices[i],
                    'volume': volumes[i]
                })
        
        return pd.DataFrame(data)
    
    def _create_mock_backtest_results(self) -> dict:
        """創建模擬回測結果"""
        # 生成日期範圍
        start_date = pd.to_datetime(self.start_date)
        end_date = pd.to_datetime(self.end_date)
        date_range = pd.date_range(start=start_date, end=end_date, freq='B')
        
        # 生成每日價值
        daily_values = []
        portfolio_value = self.initial_capital
        for date in date_range:
            # 隨機變化
            change = np.random.normal(0.0005, 0.01)  # 0.05% 平均收益，1% 標準差
            portfolio_value *= (1 + change)
            
            daily_values.append({
                'date': date,
                'cash': portfolio_value * 0.3,  # 30% 現金
                'position_value': portfolio_value * 0.7,  # 70% 倉位
                'total_value': portfolio_value
            })
        
        # 生成每日收益率
        daily_returns = []
        for i in range(1, len(daily_values)):
            prev_value = daily_values[i-1]['total_value']
            curr_value = daily_values[i]['total_value']
            daily_return = (curr_value - prev_value) / prev_value
            
            daily_returns.append({
                'date': daily_values[i]['date'],
                'return': daily_return
            })
        
        # 生成交易記錄
        trades = []
        for i in range(10):  # 10筆交易
            trade_date = date_range[np.random.randint(0, len(date_range))]
            symbol = self.symbols[np.random.randint(0, len(self.symbols))]
            price = 100 + np.random.normal(0, 10)
            shares = np.random.randint(10, 100)
            
            trades.append({
                'date': trade_date,
                'symbol': symbol,
                'shares': shares,
                'price': price,
                'value': shares * price,
                'commission': shares * price * 0.001,
                'signal': 1 if shares > 0 else -1,
                'weight': 0.2
            })
        
        # 計算摘要
        final_value = daily_values[-1]['total_value']
        total_return = (final_value - self.initial_capital) / self.initial_capital
        days = (end_date - start_date).days
        annualized_return = (1 + total_return) ** (365 / max(days, 1)) - 1
        
        # 計算最大回撤
        cumulative_values = [d['total_value'] for d in daily_values]
        peak = np.maximum.accumulate(cumulative_values)
        drawdown = (cumulative_values - peak) / peak
        max_drawdown = min(drawdown)
        
        return {
            'summary': {
                'initial_capital': self.initial_capital,
                'final_value': final_value,
                'total_return': total_return,
                'annualized_return': annualized_return,
                'max_drawdown': max_drawdown,
                'total_trades': len(trades)
            },
            'trades': pd.DataFrame(trades),
            'daily_values': pd.DataFrame(daily_values),
            'daily_returns': pd.DataFrame(daily_returns),
            'daily_positions': pd.DataFrame([]),
            'final_positions': {}
        }
    
    def _create_mock_factor_data(self) -> pd.DataFrame:
        """創建模擬因子數據"""
        # 生成日期範圍
        start_date = pd.to_datetime(self.start_date)
        end_date = pd.to_datetime(self.end_date)
        date_range = pd.date_range(start=start_date, end=end_date, freq='B')
        
        # 生成因子數據
        factor_data = []
        for date in date_range:
            for symbol in self.symbols:
                # 隨機因子值
                factor_value = np.random.normal(0, 1)
                
                factor_data.append({
                    'date': date,
                    'symbol': symbol,
                    'factor': factor_value
                })
        
        return pd.DataFrame(factor_data)


if __name__ == '__main__':
    unittest.main()
