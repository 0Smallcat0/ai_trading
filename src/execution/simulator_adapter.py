"""
模擬交易適配器

此模組提供模擬交易功能，用於回測和紙上交易。
模擬真實市場環境，包括訂單執行、滑價、部分成交等。
"""

import json
import logging
import os
import queue
import random
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from src.utils.utils import retry

from .broker_base import BrokerBase, Order, OrderStatus, OrderType

# 設定日誌
logger = logging.getLogger("execution.simulator")


class SimulatorAdapter(BrokerBase):
    """模擬交易適配器，用於回測和紙上交易"""

    def __init__(
        self,
        initial_cash: float = 1000000.0,
        slippage: float = 0.001,
        commission_rate: float = 0.001425,
        tax_rate: float = 0.003,
        data_source: Optional[str] = None,
        delay_ms: int = 500,
        partial_fill_probability: float = 0.2,
        rejection_probability: float = 0.05,
        market_data_dir: str = "data/market",
        state_file: str = "data/simulator_state.json",
        realistic_simulation: bool = True,
        **kwargs,
    ):
        """
        初始化模擬交易適配器

        Args:
            initial_cash (float): 初始資金
            slippage (float): 滑價比例
            commission_rate (float): 手續費率
            tax_rate (float): 交易稅率
            data_source (str, optional): 市場資料來源
            delay_ms (int): 模擬延遲（毫秒）
            partial_fill_probability (float): 部分成交概率
            rejection_probability (float): 拒絕概率
            market_data_dir (str): 市場資料目錄
            state_file (str): 狀態檔案路徑
            realistic_simulation (bool): 是否進行真實模擬
            **kwargs: 其他參數
        """
        super().__init__(**kwargs)
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.slippage = slippage
        self.commission_rate = commission_rate
        self.tax_rate = tax_rate
        self.data_source = data_source
        self.delay_ms = delay_ms
        self.partial_fill_probability = partial_fill_probability
        self.rejection_probability = rejection_probability
        self.market_data_dir = market_data_dir
        self.state_file = state_file
        self.realistic_simulation = realistic_simulation

        # 模擬狀態
        self.positions = {}  # 持倉字典，key 為股票代號
        self.orders = {}  # 訂單字典，key 為訂單 ID
        self.order_history = []  # 訂單歷史
        self.transaction_history = []  # 交易歷史
        self.next_order_id = 1  # 下一個訂單 ID
        self.connected = False  # 連接狀態

        # 市場資料
        self.market_data = {}  # 市場資料字典，key 為股票代號
        self.latest_prices = {}  # 最新價格字典，key 為股票代號

        # 訂單處理線程
        self.order_queue = queue.Queue()  # 訂單隊列
        self.order_thread = None  # 訂單處理線程
        self.running = False  # 執行狀態

        # 創建市場資料目錄
        os.makedirs(market_data_dir, exist_ok=True)

        # 載入狀態
        self._load_state()

    def connect(self) -> bool:
        """
        連接模擬交易系統

        Returns:
            bool: 是否連接成功
        """
        if self.connected:
            logger.info("已經連接到模擬交易系統")
            return True

        try:
            # 載入市場資料
            self._load_market_data()

            # 啟動訂單處理線程
            self.running = True
            self.order_thread = threading.Thread(target=self._process_orders)
            self.order_thread.daemon = True
            self.order_thread.start()

            self.connected = True
            logger.info("已連接到模擬交易系統")
            return True
        except Exception as e:
            logger.error(f"連接模擬交易系統失敗: {e}")
            return False

    def disconnect(self) -> bool:
        """
        斷開模擬交易系統連接

        Returns:
            bool: 是否斷開成功
        """
        if not self.connected:
            logger.info("未連接到模擬交易系統")
            return True

        try:
            # 停止訂單處理線程
            self.running = False
            if self.order_thread:
                self.order_thread.join(timeout=5)

            # 保存狀態
            self._save_state()

            self.connected = False
            logger.info("已斷開模擬交易系統連接")
            return True
        except Exception as e:
            logger.error(f"斷開模擬交易系統連接失敗: {e}")
            return False

    @retry(max_retries=3)
    def place_order(self, order: Order) -> Optional[str]:
        """
        下單

        Args:
            order (Order): 訂單物件

        Returns:
            str: 訂單 ID 或 None (如果下單失敗)
        """
        if not self.connected:
            logger.error("未連接到模擬交易系統")
            return None

        # 生成訂單 ID
        if not order.order_id:
            order.order_id = str(uuid.uuid4())

        # 更新訂單狀態
        order.status = OrderStatus.PENDING
        order.created_at = datetime.now()
        order.updated_at = datetime.now()

        # 將訂單加入隊列
        self.order_queue.put(order)
        logger.info(f"訂單已加入隊列: {order}")

        # 儲存訂單
        self.orders[order.order_id] = order

        return order.order_id

    def cancel_order(self, order_id: str) -> bool:
        """
        取消訂單

        Args:
            order_id (str): 訂單 ID

        Returns:
            bool: 是否取消成功
        """
        if not self.connected:
            logger.error("未連接到模擬交易系統")
            return False

        # 檢查訂單是否存在
        if order_id not in self.orders:
            logger.error(f"訂單不存在: {order_id}")
            return False

        # 獲取訂單
        order = self.orders[order_id]

        # 檢查訂單狀態
        if order.status not in [
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.PARTIALLY_FILLED,
        ]:
            logger.error(f"訂單狀態不允許取消: {order.status.value}")
            return False

        # 更新訂單狀態
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now()
        logger.info(f"訂單已取消: {order_id}")

        return True

    def get_order(self, order_id: str) -> Optional[Order]:
        """
        獲取訂單資訊

        Args:
            order_id (str): 訂單 ID

        Returns:
            Order: 訂單物件或 None (如果訂單不存在)
        """
        return self.orders.get(order_id)

    def get_orders(self, status: Optional[OrderStatus] = None) -> List[Order]:
        """
        獲取訂單列表

        Args:
            status (OrderStatus, optional): 訂單狀態

        Returns:
            List[Order]: 訂單列表
        """
        if status is None:
            return list(self.orders.values())
        else:
            return [order for order in self.orders.values() if order.status == status]

    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        獲取持倉資訊

        Returns:
            Dict[str, Dict[str, Any]]: 持倉資訊，key 為股票代號
        """
        # 更新持倉價值
        for stock_id, position in self.positions.items():
            latest_price = self._get_latest_price(stock_id)
            if latest_price:
                position["current_price"] = latest_price
                position["value"] = position["shares"] * latest_price
                position["profit_loss"] = position["value"] - position["cost"]
                position["profit_loss_pct"] = (
                    (position["profit_loss"] / position["cost"])
                    if position["cost"] > 0
                    else 0
                )

        return self.positions

    def get_account_info(self) -> Dict[str, Any]:
        """
        獲取帳戶資訊

        Returns:
            Dict[str, Any]: 帳戶資訊
        """
        # 計算總資產價值
        positions_value = sum(
            position.get("value", 0) for position in self.positions.values()
        )
        total_value = self.cash + positions_value

        return {
            "cash": self.cash,
            "positions_value": positions_value,
            "total_value": total_value,
            "initial_cash": self.initial_cash,
            "profit_loss": total_value - self.initial_cash,
            "profit_loss_pct": (
                (total_value - self.initial_cash) / self.initial_cash
                if self.initial_cash > 0
                else 0
            ),
            "positions_count": len(self.positions),
            "orders_count": len(self.orders),
        }

    def get_market_data(self, stock_id: str) -> Dict[str, Any]:
        """
        獲取市場資料

        Args:
            stock_id (str): 股票代號

        Returns:
            Dict[str, Any]: 市場資料
        """
        # 獲取最新價格
        latest_price = self._get_latest_price(stock_id)

        # 模擬市場資料
        return {
            "stock_id": stock_id,
            "price": latest_price,
            "bid": latest_price * 0.999 if latest_price else None,
            "ask": latest_price * 1.001 if latest_price else None,
            "volume": random.randint(1000, 10000),
            "timestamp": datetime.now().isoformat(),
        }

    def _process_orders(self):
        """處理訂單隊列"""
        while self.running:
            try:
                # 從隊列中獲取訂單
                try:
                    order = self.order_queue.get(timeout=1)
                except queue.Empty:
                    continue

                # 模擬網絡延遲
                if self.delay_ms > 0:
                    time.sleep(self.delay_ms / 1000)

                # 更新訂單狀態
                order.status = OrderStatus.SUBMITTED
                order.updated_at = datetime.now()
                logger.info(f"訂單已提交: {order}")

                # 模擬訂單拒絕
                if (
                    self.realistic_simulation
                    and random.random() < self.rejection_probability
                ):
                    order.status = OrderStatus.REJECTED
                    order.error_message = "訂單被拒絕 (模擬)"
                    order.updated_at = datetime.now()
                    logger.info(f"訂單被拒絕: {order}")
                    self.order_queue.task_done()
                    continue

                # 獲取最新價格
                latest_price = self._get_latest_price(order.stock_id)
                if not latest_price:
                    order.status = OrderStatus.REJECTED
                    order.error_message = f"無法獲取 {order.stock_id} 的價格資料"
                    order.updated_at = datetime.now()
                    logger.error(f"無法獲取價格資料: {order.stock_id}")
                    self.order_queue.task_done()
                    continue

                # 執行訂單
                self._execute_order(order, latest_price)

                self.order_queue.task_done()
            except Exception as e:
                logger.exception(f"處理訂單時發生錯誤: {e}")

    def _execute_order(self, order: Order, latest_price: float):
        """
        執行訂單

        Args:
            order (Order): 訂單物件
            latest_price (float): 最新價格
        """
        # 計算成交價格（考慮滑價）
        if order.action == "buy":
            execution_price = latest_price * (1 + self.slippage)
        else:  # sell
            execution_price = latest_price * (1 - self.slippage)

        # 根據訂單類型計算成交價格
        if order.order_type == OrderType.MARKET:
            # 市價單
            pass  # 已經計算過了
        elif order.order_type == OrderType.LIMIT:
            # 限價單
            if order.action == "buy" and execution_price > order.price:
                # 買入限價單，價格高於限價，不成交
                return
            elif order.action == "sell" and execution_price < order.price:
                # 賣出限價單，價格低於限價，不成交
                return
            execution_price = order.price
        elif order.order_type == OrderType.STOP:
            # 停損單
            if order.action == "buy" and latest_price < order.stop_price:
                # 買入停損單，價格低於停損價，不成交
                return
            elif order.action == "sell" and latest_price > order.stop_price:
                # 賣出停損單，價格高於停損價，不成交
                return
        elif order.order_type == OrderType.STOP_LIMIT:
            # 停損限價單
            if order.action == "buy" and latest_price < order.stop_price:
                # 買入停損限價單，價格低於停損價，不成交
                return
            elif order.action == "sell" and latest_price > order.stop_price:
                # 賣出停損限價單，價格高於停損價，不成交
                return

            # 檢查限價
            if order.action == "buy" and execution_price > order.price:
                # 買入限價單，價格高於限價，不成交
                return
            elif order.action == "sell" and execution_price < order.price:
                # 賣出限價單，價格低於限價，不成交
                return
            execution_price = order.price

        # 模擬部分成交
        fill_quantity = order.quantity
        if (
            self.realistic_simulation
            and random.random() < self.partial_fill_probability
        ):
            # 隨機部分成交 (50%-99%)
            fill_ratio = random.uniform(0.5, 0.99)
            fill_quantity = int(order.quantity * fill_ratio)
            if fill_quantity <= 0:
                fill_quantity = 1

        # 計算成交金額
        execution_amount = fill_quantity * execution_price

        # 計算手續費和稅金
        commission = execution_amount * self.commission_rate
        tax = execution_amount * self.tax_rate if order.action == "sell" else 0

        # 執行交易
        if order.action == "buy":
            # 檢查資金是否足夠
            total_cost = execution_amount + commission
            if self.cash < total_cost:
                order.status = OrderStatus.REJECTED
                order.error_message = "資金不足"
                order.updated_at = datetime.now()
                logger.error(f"資金不足，無法執行買入訂單 {order.order_id}")
                return

            # 更新現金
            self.cash -= total_cost

            # 更新持倉
            if order.stock_id not in self.positions:
                self.positions[order.stock_id] = {
                    "stock_id": order.stock_id,
                    "shares": fill_quantity,
                    "cost": execution_amount,
                    "avg_price": execution_price,
                    "current_price": latest_price,
                    "value": fill_quantity * latest_price,
                }
            else:
                position = self.positions[order.stock_id]
                total_shares = position["shares"] + fill_quantity
                total_cost = position["cost"] + execution_amount
                position["shares"] = total_shares
                position["cost"] = total_cost
                position["avg_price"] = total_cost / total_shares
                position["current_price"] = latest_price
                position["value"] = total_shares * latest_price
        elif order.action == "sell":
            # 檢查持倉是否足夠
            if (
                order.stock_id not in self.positions
                or self.positions[order.stock_id]["shares"] < fill_quantity
            ):
                order.status = OrderStatus.REJECTED
                order.error_message = "持倉不足"
                order.updated_at = datetime.now()
                logger.error(f"持倉不足，無法執行賣出訂單 {order.order_id}")
                return

            # 更新現金
            self.cash += execution_amount - commission - tax

            # 更新持倉
            position = self.positions[order.stock_id]
            position["shares"] -= fill_quantity
            if position["shares"] <= 0:
                # 清倉
                del self.positions[order.stock_id]
            else:
                # 更新持倉成本和價值
                position["cost"] = position["cost"] * (
                    1 - fill_quantity / (position["shares"] + fill_quantity)
                )
                position["current_price"] = latest_price
                position["value"] = position["shares"] * latest_price

        # 更新訂單狀態
        order.filled_quantity = fill_quantity
        order.filled_price = execution_price
        if fill_quantity == order.quantity:
            order.status = OrderStatus.FILLED
        else:
            order.status = OrderStatus.PARTIALLY_FILLED
        order.updated_at = datetime.now()

        # 記錄交易
        transaction = {
            "order_id": order.order_id,
            "stock_id": order.stock_id,
            "action": order.action,
            "quantity": fill_quantity,
            "price": execution_price,
            "amount": execution_amount,
            "commission": commission,
            "tax": tax,
            "timestamp": datetime.now().isoformat(),
        }
        self.transaction_history.append(transaction)

        logger.info(
            f"訂單執行: {order}, 成交價格: {execution_price}, 成交數量: {fill_quantity}"
        )

    def _get_latest_price(self, stock_id: str) -> Optional[float]:
        """
        獲取最新價格

        Args:
            stock_id (str): 股票代號

        Returns:
            float: 最新價格或 None (如果無法獲取)
        """
        # 檢查是否有快取
        if stock_id in self.latest_prices:
            # 模擬價格波動 (±0.5%)
            if self.realistic_simulation:
                price = self.latest_prices[stock_id]
                price *= 1 + random.uniform(-0.005, 0.005)
                self.latest_prices[stock_id] = price
            return self.latest_prices[stock_id]

        # 從市場資料中獲取
        if stock_id in self.market_data:
            data = self.market_data[stock_id]
            if not data.empty:
                # 獲取最新價格
                latest_price = data["close"].iloc[-1]
                self.latest_prices[stock_id] = latest_price
                return latest_price

        # 模擬價格
        if self.realistic_simulation:
            # 生成隨機價格 (50-200)
            price = random.uniform(50, 200)
            self.latest_prices[stock_id] = price
            return price

        return None

    def _load_market_data(self):
        """載入市場資料"""
        try:
            # 檢查市場資料目錄
            market_data_dir = Path(self.market_data_dir)
            if not market_data_dir.exists():
                logger.warning(f"市場資料目錄不存在: {self.market_data_dir}")
                return

            # 載入市場資料
            for file_path in market_data_dir.glob("*.csv"):
                try:
                    # 從檔名獲取股票代號
                    stock_id = file_path.stem

                    # 讀取 CSV 檔案
                    data = pd.read_csv(file_path, index_col=0, parse_dates=True)
                    if not data.empty:
                        self.market_data[stock_id] = data
                        self.latest_prices[stock_id] = data["close"].iloc[-1]
                        logger.debug(f"已載入 {stock_id} 的市場資料，共 {len(data)} 筆")
                except Exception as e:
                    logger.error(f"載入 {file_path} 時發生錯誤: {e}")
        except Exception as e:
            logger.error(f"載入市場資料時發生錯誤: {e}")

    def _save_state(self):
        """保存模擬器狀態"""
        try:
            # 創建狀態字典
            state = {
                "cash": self.cash,
                "positions": self.positions,
                "orders": {
                    order_id: order.to_dict() for order_id, order in self.orders.items()
                },
                "transaction_history": self.transaction_history,
                "latest_prices": self.latest_prices,
                "timestamp": datetime.now().isoformat(),
            }

            # 保存狀態
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

            logger.info(f"已保存模擬器狀態: {self.state_file}")
        except Exception as e:
            logger.error(f"保存模擬器狀態時發生錯誤: {e}")

    def _load_state(self):
        """載入模擬器狀態"""
        try:
            # 檢查狀態檔案是否存在
            if not os.path.exists(self.state_file):
                logger.info(f"模擬器狀態檔案不存在: {self.state_file}")
                return

            # 載入狀態
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            # 更新狀態
            self.cash = state.get("cash", self.initial_cash)
            self.positions = state.get("positions", {})
            self.transaction_history = state.get("transaction_history", [])
            self.latest_prices = state.get("latest_prices", {})

            # 載入訂單
            for order_id, order_dict in state.get("orders", {}).items():
                self.orders[order_id] = Order.from_dict(order_dict)

            logger.info(f"已載入模擬器狀態: {self.state_file}")
        except Exception as e:
            logger.error(f"載入模擬器狀態時發生錯誤: {e}")
