"""投資組合核心類別模組

此模組定義了投資組合的核心抽象基類。
所有具體的投資組合策略都應該繼承 Portfolio 基類。

主要功能：
- 定義投資組合基礎介面
- 提供通用的投資組合操作方法
- 管理投資組合狀態和歷史記錄
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List, Tuple
import logging
from datetime import datetime

import numpy as np
import pandas as pd

from .exceptions import (
    PortfolioOptimizationError,
    ValidationError,
    InsufficientFundsError,
    InvalidWeightsError,
)

# 設定日誌
logger = logging.getLogger(__name__)


class Portfolio(ABC):
    """投資組合基類，所有具體投資組合策略都應該繼承此類"""

    def __init__(
        self,
        name: str = "BasePortfolio",
        initial_capital: float = 1000000,
        transaction_cost: float = 0.001425,
        tax: float = 0.003,
        slippage: float = 0.001,
    ):
        """初始化投資組合

        Args:
            name: 投資組合名稱
            initial_capital: 初始資金
            transaction_cost: 交易成本比例
            tax: 交易稅比例
            slippage: 滑價比例
        """
        self.name = name
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.tax = tax
        self.slippage = slippage

        # 投資組合狀態
        self.cash = initial_capital
        # {stock_id: {'shares': 100, 'cost': 50.0, 'value': 5000.0}}
        self.positions = {}
        self.history = []  # 歷史狀態記錄
        self.transactions = []  # 交易記錄

    @abstractmethod
    def optimize(
        self, signals: pd.DataFrame, price_df: Optional[pd.DataFrame] = None
    ) -> Dict[str, float]:
        """最佳化投資組合

        Args:
            signals: 交易訊號
            price_df: 價格資料

        Returns:
            最佳化後的權重

        Raises:
            NotImplementedError: 子類必須實現此方法
        """
        raise NotImplementedError("子類必須實現 optimize 方法")

    @abstractmethod
    def evaluate(
        self, weights: Dict[str, float], price_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """評估投資組合表現

        Args:
            weights: 投資組合權重
            price_df: 價格資料

        Returns:
            評估結果

        Raises:
            NotImplementedError: 子類必須實現此方法
        """
        raise NotImplementedError("子類必須實現 evaluate 方法")

    def get_total_value(self, current_prices: Dict[str, float]) -> float:
        """計算投資組合總價值

        Args:
            current_prices: 當前價格字典

        Returns:
            投資組合總價值
        """
        total_value = self.cash

        for stock_id, position in self.positions.items():
            if stock_id in current_prices:
                total_value += position["shares"] * current_prices[stock_id]
            else:
                logger.warning("無法找到 %s 的當前價格", stock_id)

        return total_value

    def get_weights(self, current_prices: Dict[str, float]) -> Dict[str, float]:
        """計算當前投資組合權重

        Args:
            current_prices: 當前價格字典

        Returns:
            投資組合權重字典
        """
        total_value = self.get_total_value(current_prices)
        weights = {}

        if total_value > 0:
            for stock_id, position in self.positions.items():
                if stock_id in current_prices:
                    position_value = position["shares"] * current_prices[stock_id]
                    weights[stock_id] = position_value / total_value

        return weights

    def rebalance(
        self, target_weights: Dict[str, float], current_prices: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """重新平衡投資組合

        Args:
            target_weights: 目標權重
            current_prices: 當前價格

        Returns:
            交易指令列表

        Raises:
            ValidationError: 當權重無效時
        """
        # 驗證權重
        self._validate_weights(target_weights)

        total_value = self.get_total_value(current_prices)
        current_weights = self.get_weights(current_prices)
        orders = []

        for stock_id, target_weight in target_weights.items():
            if stock_id not in current_prices:
                logger.warning("無法找到 %s 的當前價格，跳過", stock_id)
                continue

            current_weight = current_weights.get(stock_id, 0.0)
            weight_diff = target_weight - current_weight
            target_value = target_weight * total_value
            current_shares = self.positions.get(stock_id, {}).get("shares", 0)
            target_shares = int(target_value / current_prices[stock_id])
            shares_diff = target_shares - current_shares

            if abs(shares_diff) > 0:
                order = {
                    "stock_id": stock_id,
                    "action": "buy" if shares_diff > 0 else "sell",
                    "shares": abs(shares_diff),
                    "price": current_prices[stock_id],
                    "timestamp": datetime.now(),
                }
                orders.append(order)

        return orders

    def execute_order(self, order: Dict[str, Any]) -> bool:
        """執行交易指令

        Args:
            order: 交易指令

        Returns:
            是否執行成功

        Raises:
            InsufficientFundsError: 當資金不足時
        """
        stock_id = order["stock_id"]
        action = order["action"]
        shares = order["shares"]
        price = order["price"]

        # 計算交易成本
        trade_value = shares * price
        total_cost = trade_value * (1 + self.transaction_cost + self.tax + self.slippage)

        if action == "buy":
            if self.cash < total_cost:
                raise InsufficientFundsError(total_cost, self.cash)

            self.cash -= total_cost
            if stock_id in self.positions:
                self.positions[stock_id]["shares"] += shares
            else:
                self.positions[stock_id] = {"shares": shares, "cost": price}

        elif action == "sell":
            if stock_id not in self.positions or self.positions[stock_id]["shares"] < shares:
                return False

            self.positions[stock_id]["shares"] -= shares
            if self.positions[stock_id]["shares"] == 0:
                del self.positions[stock_id]

            net_proceeds = trade_value * (1 - self.transaction_cost - self.tax - self.slippage)
            self.cash += net_proceeds

        # 記錄交易
        self.transactions.append({
            **order,
            "executed_at": datetime.now(),
            "total_cost": total_cost if action == "buy" else -net_proceeds,
        })

        return True

    def _validate_weights(self, weights: Dict[str, float]) -> None:
        """驗證權重有效性

        Args:
            weights: 權重字典

        Raises:
            InvalidWeightsError: 當權重無效時
        """
        if not weights:
            raise InvalidWeightsError("權重字典不能為空")

        total_weight = sum(weights.values())
        if abs(total_weight - 1.0) > 1e-6:
            raise InvalidWeightsError(f"權重總和必須為 1.0，當前為 {total_weight:.6f}")

        for stock_id, weight in weights.items():
            if weight < 0:
                raise InvalidWeightsError(f"權重不能為負數: {stock_id} = {weight}")
            if weight > 1:
                raise InvalidWeightsError(f"單一權重不能超過 1.0: {stock_id} = {weight}")

    def save_state(self) -> None:
        """保存當前狀態到歷史記錄"""
        state = {
            "timestamp": datetime.now(),
            "cash": self.cash,
            "positions": self.positions.copy(),
            "total_value": self.cash + sum(
                pos["shares"] * pos.get("cost", 0) for pos in self.positions.values()
            ),
        }
        self.history.append(state)

    def get_performance_summary(self) -> Dict[str, Any]:
        """獲取績效摘要

        Returns:
            績效摘要字典
        """
        if not self.history:
            return {"error": "無歷史資料"}

        initial_value = self.initial_capital
        current_value = self.history[-1]["total_value"] if self.history else initial_value
        total_return = (current_value - initial_value) / initial_value

        return {
            "initial_capital": initial_value,
            "current_value": current_value,
            "total_return": total_return,
            "total_return_pct": total_return * 100,
            "num_transactions": len(self.transactions),
            "num_positions": len(self.positions),
        }
