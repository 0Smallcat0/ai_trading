"""
訊號執行模組

此模組負責將交易訊號轉換為實際的交易指令，
並透過 OrderManager 執行交易，實現自動化交易。

主要功能：
- 訊號處理與轉換
- 訂單生成與管理
- 交易執行
- 交易狀態監控
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from src.core.logger import get_logger
from src.execution.broker_base import Order
from src.execution.order_manager import OrderManager

# 設定日誌
logger = get_logger("execution.signal_executor")


class SignalExecutor:
    """訊號執行器，負責將交易訊號轉換為訂單並執行"""

    def __init__(
        self,
        order_manager: OrderManager,
        position_limit: float = 0.2,
        sector_limit: float = 0.4,
        max_positions: int = 10,
    ):
        """
        初始化訊號執行器

        Args:
            order_manager (OrderManager): 訂單管理器
            position_limit (float): 單一持倉上限（佔總資產比例）
            sector_limit (float): 單一行業上限（佔總資產比例）
            max_positions (int): 最大持倉數量
        """
        self.order_manager = order_manager
        self.position_limit = position_limit
        self.sector_limit = sector_limit
        self.max_positions = max_positions
        self.pending_orders = {}  # 等待中的訂單，key 為股票代號
        self.signal_history = {}  # 訊號歷史，key 為股票代號

        # 設置訂單回調函數
        self.order_manager.set_order_callbacks(
            on_status_change=self._on_order_status_change,
            on_filled=self._on_order_filled,
            on_rejected=self._on_order_rejected,
        )

    def start(self) -> bool:
        """
        啟動訊號執行器

        Returns:
            bool: 是否成功啟動
        """
        # 啟動訂單管理器
        return self.order_manager.start()

    def stop(self) -> None:
        """停止訊號執行器"""
        # 停止訂單管理器
        self.order_manager.stop()

    def execute_signals(
        self,
        signals: Union[pd.DataFrame, Dict[str, pd.DataFrame]],
        strategy_id: Optional[str] = None,
    ) -> List[str]:
        """
        執行交易訊號

        Args:
            signals (Union[pd.DataFrame, Dict[str, pd.DataFrame]]): 交易訊號，可以是 DataFrame 或 Dict[str, DataFrame]
            strategy_id (str, optional): 策略 ID

        Returns:
            List[str]: 訂單 ID 列表
        """
        # 檢查訊號格式
        if isinstance(signals, dict):
            # 如果是字典，則合併所有訊號
            combined_signals = pd.concat(signals.values())
        else:
            combined_signals = signals

        # 檢查訊號是否為空
        if combined_signals.empty:
            logger.warning("沒有可用的交易訊號")
            return []

        # 獲取當前持倉
        positions = self._get_positions()

        # 創建訂單列表
        orders = []

        # 處理賣出訊號
        sell_orders = self._generate_sell_orders(combined_signals, positions)
        orders.extend(sell_orders)

        # 處理買入訊號
        buy_orders = self._generate_buy_orders(combined_signals, positions)
        orders.extend(buy_orders)

        # 提交訂單
        order_ids = self._submit_orders(orders, strategy_id)

        return order_ids

    def _generate_sell_orders(
        self, signals: pd.DataFrame, positions: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        生成賣出訂單

        Args:
            signals (pd.DataFrame): 交易訊號
            positions (Dict[str, Dict[str, Any]]): 當前持倉

        Returns:
            List[Dict[str, Any]]: 賣出訂單列表
        """
        sell_orders = []

        # 檢查是否有賣出訊號列
        if "sell_signal" not in signals.columns and "signal" not in signals.columns:
            logger.warning("訊號中沒有賣出訊號列")
            return sell_orders

        # 獲取賣出訊號
        if "sell_signal" in signals.columns:
            sell_signals = signals[signals["sell_signal"] == 1]
        else:
            sell_signals = signals[signals["signal"] == -1]

        # 處理賣出訊號
        for index, row in sell_signals.iterrows():
            # 獲取股票代號
            if isinstance(index, tuple):
                stock_id = index[0]  # 多層索引，第一層是股票代號
            else:
                stock_id = index

            # 檢查是否持有該股票
            if stock_id in positions:
                # 檢查是否已有等待中的訂單
                if stock_id in self.pending_orders:
                    logger.info(f"股票 {stock_id} 已有等待中的訂單，跳過賣出訊號")
                    continue

                # 創建賣出訂單
                sell_orders.append(
                    {
                        "stock_id": stock_id,
                        "action": "sell",
                        "quantity": positions[stock_id]["shares"],
                        "order_type": "market",
                    }
                )

                # 記錄訊號
                self.signal_history[stock_id] = {
                    "signal": "sell",
                    "timestamp": datetime.now(),
                }

                logger.info(
                    f"生成賣出訂單: {stock_id}, 數量: {positions[stock_id]['shares']}"
                )

        return sell_orders

    def _generate_buy_orders(
        self, signals: pd.DataFrame, positions: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        生成買入訂單

        Args:
            signals (pd.DataFrame): 交易訊號
            positions (Dict[str, Dict[str, Any]]): 當前持倉

        Returns:
            List[Dict[str, Any]]: 買入訂單列表
        """
        buy_orders = []

        # 檢查是否有買入訊號列
        if "buy_signal" not in signals.columns and "signal" not in signals.columns:
            logger.warning("訊號中沒有買入訊號列")
            return buy_orders

        # 獲取買入訊號
        if "buy_signal" in signals.columns:
            buy_signals = signals[signals["buy_signal"] == 1]
        else:
            buy_signals = signals[signals["signal"] == 1]

        # 獲取帳戶資訊
        account_info = self._get_account_info()
        cash = account_info.get("cash", 0)
        total_value = account_info.get("total_value", cash)

        # 檢查是否有足夠的現金
        if cash <= 0:
            logger.warning("沒有足夠的現金進行買入")
            return buy_orders

        # 檢查持倉數量是否已達上限
        if len(positions) >= self.max_positions:
            logger.warning(f"持倉數量已達上限 {self.max_positions}，無法進行買入")
            return buy_orders

        # 計算可用持倉數量
        available_positions = self.max_positions - len(positions)

        # 計算每個股票的分配金額
        allocation_per_stock = min(
            cash / available_positions if available_positions > 0 else 0,
            total_value * self.position_limit,
        )

        # 處理買入訊號
        for index, row in buy_signals.iterrows():
            # 如果已達可用持倉數量，則停止買入
            if len(buy_orders) >= available_positions:
                break

            # 獲取股票代號
            if isinstance(index, tuple):
                stock_id = index[0]  # 多層索引，第一層是股票代號
            else:
                stock_id = index

            # 檢查是否已持有該股票
            if stock_id in positions:
                logger.info(f"已持有股票 {stock_id}，跳過買入訊號")
                continue

            # 檢查是否已有等待中的訂單
            if stock_id in self.pending_orders:
                logger.info(f"股票 {stock_id} 已有等待中的訂單，跳過買入訊號")
                continue

            # 獲取股票價格
            price = self._get_stock_price(stock_id, row)

            if price and price > 0:
                # 計算買入數量
                quantity = int(allocation_per_stock / price)

                if quantity > 0:
                    # 創建買入訂單
                    buy_orders.append(
                        {
                            "stock_id": stock_id,
                            "action": "buy",
                            "quantity": quantity,
                            "order_type": "market",
                        }
                    )

                    # 記錄訊號
                    self.signal_history[stock_id] = {
                        "signal": "buy",
                        "timestamp": datetime.now(),
                    }

                    logger.info(
                        f"生成買入訂單: {stock_id}, 數量: {quantity}, 價格: {price}"
                    )

        return buy_orders

    def _submit_orders(
        self, orders: List[Dict[str, Any]], strategy_id: Optional[str] = None
    ) -> List[str]:
        """
        提交訂單

        Args:
            orders (List[Dict[str, Any]]): 訂單列表
            strategy_id (str, optional): 策略 ID

        Returns:
            List[str]: 訂單 ID 列表
        """
        order_ids = []

        for order_dict in orders:
            # 添加策略 ID
            if strategy_id:
                order_dict["strategy_id"] = strategy_id

            # 提交訂單
            order_id = self.order_manager.submit_order(order_dict)

            if order_id:
                order_ids.append(order_id)
                # 記錄等待中的訂單
                self.pending_orders[order_dict["stock_id"]] = order_id

        return order_ids

    def _on_order_status_change(self, order: Order) -> None:
        """
        訂單狀態變更回調

        Args:
            order (Order): 訂單物件
        """
        logger.info(f"訂單狀態變更: {order.order_id}, 狀態: {order.status.value}")

    def _on_order_filled(self, order: Order) -> None:
        """
        訂單成交回調

        Args:
            order (Order): 訂單物件
        """
        logger.info(
            f"訂單成交: {order.order_id}, 股票: {order.stock_id}, "
            f"動作: {order.action}, 數量: {order.filled_quantity}, "
            f"價格: {order.filled_price}"
        )

        # 從等待中的訂單中移除
        if order.stock_id in self.pending_orders:
            del self.pending_orders[order.stock_id]

    def _on_order_rejected(self, order: Order) -> None:
        """
        訂單拒絕回調

        Args:
            order (Order): 訂單物件
        """
        logger.error(
            f"訂單拒絕: {order.order_id}, 股票: {order.stock_id}, "
            f"動作: {order.action}, 原因: {order.error_message}"
        )

        # 從等待中的訂單中移除
        if order.stock_id in self.pending_orders:
            del self.pending_orders[order.stock_id]

    def _get_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        獲取當前持倉

        Returns:
            Dict[str, Dict[str, Any]]: 持倉資訊
        """
        # 獲取券商 API 中的持倉
        return self.order_manager.broker.get_positions()

    def _get_account_info(self) -> Dict[str, Any]:
        """
        獲取帳戶資訊

        Returns:
            Dict[str, Any]: 帳戶資訊
        """
        # 獲取券商 API 中的帳戶資訊
        return self.order_manager.broker.get_account_info()

    def _get_stock_price(self, stock_id: str, row: pd.Series) -> Optional[float]:
        """
        獲取股票價格

        Args:
            stock_id (str): 股票代號
            row (pd.Series): 訊號行

        Returns:
            Optional[float]: 股票價格
        """
        # 嘗試從訊號中獲取價格
        if "close" in row:
            return float(row["close"])
        elif "price" in row:
            return float(row["price"])
        elif "last_price" in row:
            return float(row["last_price"])

        # 嘗試從券商 API 獲取價格
        try:
            market_data = self.order_manager.broker.get_market_data(stock_id)
            if market_data and "last_price" in market_data:
                return float(market_data["last_price"])
        except Exception as e:
            logger.error(f"獲取股票 {stock_id} 價格時發生錯誤: {e}")

        return None
