"""模擬回測引擎模組

此模組提供模擬回測引擎功能，用於在沒有真實回測引擎時進行測試。
"""

import logging
from typing import Dict, List
import pandas as pd
import numpy as np

# 設定日誌
logger = logging.getLogger(__name__)


class MockBacktest:
    """模擬回測引擎"""

    def __init__(self, price_df, initial_capital, commission, slippage):
        """初始化模擬回測引擎

        Args:
            price_df: 價格數據
            initial_capital: 初始資金
            commission: 手續費率
            slippage: 滑價率
        """
        self.price_df = price_df
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage

    def run(self, signals) -> Dict:
        """運行模擬回測

        Args:
            signals: 交易訊號（暫未使用）

        Returns:
            Dict: 回測結果
        """
        _ = signals  # 標記為已使用，避免 pylint 警告
        logger.info("開始運行模擬回測")

        # 生成模擬結果
        dates = pd.date_range(start="2023-01-01", end="2023-12-31", freq="D")
        dates = dates[dates.weekday < 5]  # 只保留工作日

        # 生成模擬權益曲線
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.02, len(dates))
        equity_curve = [self.initial_capital]

        for ret in returns:
            equity_curve.append(equity_curve[-1] * (1 + ret))

        equity_curve = equity_curve[1:]  # 移除初始值

        # 生成模擬交易記錄
        trades = self._generate_mock_trades(dates)

        logger.info("模擬回測完成，生成 %d 筆交易", len(trades))

        return {"equity_curve": equity_curve, "dates": dates.tolist(), "trades": trades}

    def _generate_mock_trades(self, dates: pd.DatetimeIndex) -> List[Dict]:
        """生成模擬交易記錄

        Args:
            dates: 日期範圍

        Returns:
            List[Dict]: 交易記錄列表
        """
        trades = []
        symbols = ["2330.TW", "2317.TW"]

        for _ in range(10):  # 生成10筆交易
            symbol = np.random.choice(symbols)
            entry_date = np.random.choice(dates[:200])
            exit_date = entry_date + pd.Timedelta(days=np.random.randint(1, 30))

            entry_price = np.random.uniform(100, 500)
            exit_price = entry_price * (1 + np.random.normal(0, 0.05))
            quantity = np.random.randint(100, 1000)

            profit = (exit_price - entry_price) * quantity
            profit_pct = (exit_price / entry_price - 1) * 100

            trades.append(
                {
                    "symbol": symbol,
                    "entry_date": pd.Timestamp(entry_date).strftime("%Y-%m-%d"),
                    "exit_date": pd.Timestamp(exit_date).strftime("%Y-%m-%d"),
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "quantity": quantity,
                    "position_size": entry_price * quantity,
                    "trade_type": "多頭",
                    "profit": profit,
                    "profit_pct": profit_pct,
                    "commission_paid": entry_price * quantity * self.commission,
                    "slippage_cost": entry_price * quantity * self.slippage,
                    "tax_paid": 0,
                    "hold_days": (
                        pd.Timestamp(exit_date) - pd.Timestamp(entry_date)
                    ).days,
                    "signal_strength": np.random.uniform(0.5, 1.0),
                }
            )

        return trades
