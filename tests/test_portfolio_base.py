"""
測試投資組合基礎模組

此模組測試投資組合基類的功能，包括初始化、模擬、再平衡和績效計算。
"""

import os
import sys
import unittest
import numpy as np
import pandas as pd
import pytest

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.portfolio.base import Portfolio, PortfolioOptimizationError, DependencyError


class ConcretePortfolio(Portfolio):
    """測試用的具體投資組合實現"""

    def optimize(self, signals: pd.DataFrame, price_df=None) -> dict:
        """簡單的等權重最佳化"""
        if signals.empty:
            return {}

        # 獲取有訊號的股票
        stocks = signals.index.get_level_values("stock_id").unique()
        weight = 1.0 / len(stocks) if len(stocks) > 0 else 0.0

        return {stock: weight for stock in stocks}

    def evaluate(self, weights: dict, price_df: pd.DataFrame) -> dict:
        """簡單的評估實現"""
        return {"total_return": 0.1, "sharpe_ratio": 1.5, "max_drawdown": -0.05}

    def rebalance(
        self, weights: dict, price_df: pd.DataFrame, frequency: str = "M"
    ) -> dict:
        """簡單的再平衡實現"""
        return weights


class TestPortfolioExceptions(unittest.TestCase):
    """測試投資組合異常類別"""

    def test_portfolio_optimization_error(self):
        """測試投資組合最佳化錯誤"""
        with pytest.raises(PortfolioOptimizationError):
            raise PortfolioOptimizationError("最佳化失敗")

    def test_dependency_error(self):
        """測試依賴套件錯誤"""
        with pytest.raises(DependencyError):
            raise DependencyError("缺少依賴套件")


class TestPortfolioBase(unittest.TestCase):
    """測試投資組合基類"""

    def setUp(self):
        """設置測試環境"""
        # 創建測試投資組合
        self.portfolio = ConcretePortfolio(
            name="測試投資組合",
            initial_capital=1000000,
            transaction_cost=0.001425,
            tax=0.003,
            slippage=0.001,
        )

        # 創建測試資料
        dates = pd.date_range("2023-01-01", periods=10, freq="D")
        stocks = ["AAPL", "GOOGL", "MSFT"]

        # 創建多層索引的價格資料（日期在前，股票在後）
        index = pd.MultiIndex.from_product([dates, stocks], names=["date", "stock_id"])

        self.price_df = pd.DataFrame(
            {
                "收盤價": np.random.uniform(100, 200, len(index)),
                "volume": np.random.randint(1000, 10000, len(index)),
            },
            index=index,
        )

        # 創建訊號資料
        self.signals = pd.DataFrame(
            {
                "signal": np.random.choice([-1, 0, 1], len(index)),
                "buy_signal": np.random.choice([0, 1], len(index)),
                "sell_signal": np.random.choice([0, 1], len(index)),
            },
            index=index,
        )

    def test_initialization(self):
        """測試投資組合初始化"""
        portfolio = ConcretePortfolio(
            name="測試",
            initial_capital=500000,
            transaction_cost=0.002,
            tax=0.004,
            slippage=0.0015,
        )

        # 檢查基本屬性
        self.assertEqual(portfolio.name, "測試")
        self.assertEqual(portfolio.initial_capital, 500000)
        self.assertEqual(portfolio.transaction_cost, 0.002)
        self.assertEqual(portfolio.tax, 0.004)
        self.assertEqual(portfolio.slippage, 0.0015)

        # 檢查初始狀態
        self.assertEqual(portfolio.cash, 500000)
        self.assertEqual(portfolio.positions, {})
        self.assertEqual(portfolio.history, [])
        self.assertEqual(portfolio.transactions, [])

    def test_default_initialization(self):
        """測試預設參數初始化"""
        portfolio = ConcretePortfolio()

        self.assertEqual(portfolio.name, "BasePortfolio")
        self.assertEqual(portfolio.initial_capital, 1000000)
        self.assertEqual(portfolio.transaction_cost, 0.001425)
        self.assertEqual(portfolio.tax, 0.003)
        self.assertEqual(portfolio.slippage, 0.001)

    def test_simulate_basic(self):
        """測試基本模擬功能"""
        result = self.portfolio.simulate(
            self.signals, self.price_df, rebalance_freq="D"
        )

        # 檢查返回結果結構
        self.assertIn("history", result)
        self.assertIn("transactions", result)
        self.assertIn("performance", result)

        # 檢查歷史記錄
        self.assertIsInstance(result["history"], list)
        self.assertGreater(len(result["history"]), 0)

        # 檢查交易記錄
        self.assertIsInstance(result["transactions"], list)

        # 檢查績效指標
        self.assertIsInstance(result["performance"], dict)

    def test_simulate_with_date_range(self):
        """測試指定日期範圍的模擬"""
        start_date = self.price_df.index.get_level_values("date")[2]
        end_date = self.price_df.index.get_level_values("date")[7]

        result = self.portfolio.simulate(
            self.signals,
            self.price_df,
            start_date=start_date,
            end_date=end_date,
            rebalance_freq="D",
        )

        # 檢查結果
        self.assertIn("history", result)
        self.assertGreater(len(result["history"]), 0)

        # 檢查日期範圍
        if result["history"]:
            history_dates = [state["date"] for state in result["history"]]
            self.assertGreaterEqual(min(history_dates), start_date)
            self.assertLessEqual(max(history_dates), end_date)

    def test_price_data_validation(self):
        """測試價格資料驗證"""
        # 測試缺少收盤價欄位
        invalid_price_df = self.price_df.drop("收盤價", axis=1)

        with pytest.raises(ValueError, match="價格資料必須包含"):
            self.portfolio.simulate(self.signals, invalid_price_df)

    def test_update_positions_value(self):
        """測試持倉價值更新"""
        # 設置初始持倉
        self.portfolio.positions = {
            "AAPL": {"shares": 100, "cost": 150.0, "value": 15000.0}
        }

        # 獲取測試日期的價格資料
        test_date = self.price_df.index.get_level_values("date")[0]
        day_prices = self.price_df.xs(test_date, level="date", drop_level=False)

        # 更新持倉價值
        self.portfolio._update_positions_value(day_prices, "收盤價")

        # 檢查持倉價值是否更新
        if "AAPL" in self.portfolio.positions:
            aapl_price = day_prices.loc[(test_date, "AAPL"), "收盤價"]
            expected_value = 100 * aapl_price
            self.assertEqual(self.portfolio.positions["AAPL"]["value"], expected_value)

    def test_record_state(self):
        """測試狀態記錄"""
        # 設置測試狀態
        self.portfolio.cash = 500000
        self.portfolio.positions = {
            "AAPL": {"shares": 100, "cost": 150.0, "value": 15000.0}
        }

        test_date = pd.Timestamp("2023-01-01")

        # 記錄狀態
        self.portfolio._record_state(test_date)

        # 檢查歷史記錄
        self.assertEqual(len(self.portfolio.history), 1)

        state = self.portfolio.history[0]
        self.assertEqual(state["date"], test_date)
        self.assertEqual(state["cash"], 500000)
        self.assertEqual(state["total_value"], 515000)  # 500000 + 15000
        self.assertIn("AAPL", state["positions"])

    def test_buy_stock(self):
        """測試買入股票"""
        # 獲取測試價格資料
        test_date = self.price_df.index.get_level_values("date")[0]
        day_prices = self.price_df.xs(test_date, level="date", drop_level=False)

        initial_cash = self.portfolio.cash

        # 買入股票
        self.portfolio._buy_stock("AAPL", 100, day_prices, "收盤價")

        # 檢查持倉
        self.assertIn("AAPL", self.portfolio.positions)
        self.assertEqual(self.portfolio.positions["AAPL"]["shares"], 100)

        # 檢查現金減少
        self.assertLess(self.portfolio.cash, initial_cash)

        # 檢查交易記錄
        self.assertEqual(len(self.portfolio.transactions), 1)
        transaction = self.portfolio.transactions[0]
        self.assertEqual(transaction["action"], "buy")
        self.assertEqual(transaction["stock_id"], "AAPL")
        self.assertEqual(transaction["shares"], 100)

    def test_sell_stock(self):
        """測試賣出股票"""
        # 先設置持倉
        test_date = self.price_df.index.get_level_values("date")[0]
        day_prices = self.price_df.xs(test_date, level="date", drop_level=False)

        self.portfolio.positions["AAPL"] = {
            "shares": 100,
            "cost": 150.0,
            "value": 15000.0,
        }

        initial_cash = self.portfolio.cash

        # 賣出股票
        self.portfolio._sell_stock("AAPL", 50, day_prices, "收盤價")

        # 檢查持倉減少
        self.assertEqual(self.portfolio.positions["AAPL"]["shares"], 50)

        # 檢查現金增加
        self.assertGreater(self.portfolio.cash, initial_cash)

        # 檢查交易記錄
        self.assertEqual(len(self.portfolio.transactions), 1)
        transaction = self.portfolio.transactions[0]
        self.assertEqual(transaction["action"], "sell")
        self.assertEqual(transaction["stock_id"], "AAPL")
        self.assertEqual(transaction["shares"], 50)

    def test_sell_all_stock(self):
        """測試賣出全部股票"""
        # 先設置持倉
        test_date = self.price_df.index.get_level_values("date")[0]
        day_prices = self.price_df.xs(test_date, level="date", drop_level=False)

        self.portfolio.positions["AAPL"] = {
            "shares": 100,
            "cost": 150.0,
            "value": 15000.0,
        }

        # 賣出全部股票
        self.portfolio._sell_stock("AAPL", None, day_prices, "收盤價")

        # 檢查持倉被刪除
        self.assertNotIn("AAPL", self.portfolio.positions)

    def test_calculate_performance_empty_history(self):
        """測試空歷史記錄的績效計算"""
        performance = self.portfolio._calculate_performance()
        self.assertEqual(performance, {})

    def test_calculate_performance_with_history(self):
        """測試有歷史記錄的績效計算"""
        # 創建測試歷史記錄
        dates = pd.date_range("2023-01-01", periods=5, freq="D")
        values = [1000000, 1010000, 1005000, 1020000, 1015000]

        for date, value in zip(dates, values):
            self.portfolio.history.append(
                {
                    "date": date,
                    "cash": value * 0.1,
                    "positions": {},
                    "total_value": value,
                }
            )

        performance = self.portfolio._calculate_performance()

        # 檢查績效指標
        expected_keys = [
            "total_return",
            "annual_return",
            "annual_volatility",
            "sharpe_ratio",
            "max_drawdown",
            "win_rate",
            "total_trades",
            "equity_curve",
            "daily_returns",
            "cumulative_returns",
        ]

        for key in expected_keys:
            self.assertIn(key, performance)

        # 檢查總收益率
        expected_total_return = (1015000 / 1000000) - 1
        self.assertAlmostEqual(
            performance["total_return"], expected_total_return, places=6
        )


if __name__ == "__main__":
    unittest.main()
