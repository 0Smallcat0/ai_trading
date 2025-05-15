"""
自動下單與執行模組

此模組負責將交易訊號轉換為實際的交易指令，
並透過券商 API 執行交易，實現自動化交易。

主要功能：
- 連接券商 API
- 訂單生成與管理
- 交易執行
- 交易狀態監控
"""

import asyncio
import logging
import os
from datetime import datetime

import numpy as np
import shioaji
from dotenv import load_dotenv

from src.utils.utils import retry

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("trading.log"), logging.StreamHandler()],
)
logger = logging.getLogger("executor")


class OrderStatus:
    """訂單狀態常數"""

    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class OrderType:
    """訂單類型常數"""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class Order:
    """訂單類，用於表示交易訂單"""

    def __init__(
        self,
        stock_id,
        action,
        quantity,
        order_type=OrderType.MARKET,
        price=None,
        stop_price=None,
        time_in_force="day",
    ):
        """
        初始化訂單

        Args:
            stock_id (str): 股票代號
            action (str): 交易動作，'buy' 或 'sell'
            quantity (int): 交易數量
            order_type (str): 訂單類型
            price (float, optional): 限價
            stop_price (float, optional): 停損價
            time_in_force (str): 訂單有效期
        """
        self.stock_id = stock_id
        self.action = action
        self.quantity = quantity
        self.order_type = order_type
        self.price = price
        self.stop_price = stop_price
        self.time_in_force = time_in_force
        self.status = OrderStatus.PENDING
        self.filled_quantity = 0
        self.filled_price = 0
        self.order_id = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self):
        """
        將訂單轉換為字典

        Returns:
            dict: 訂單字典
        """
        return {
            "stock_id": self.stock_id,
            "action": self.action,
            "quantity": self.quantity,
            "order_type": self.order_type,
            "price": self.price,
            "stop_price": self.stop_price,
            "time_in_force": self.time_in_force,
            "status": self.status,
            "filled_quantity": self.filled_quantity,
            "filled_price": self.filled_price,
            "order_id": self.order_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, order_dict):
        """
        從字典創建訂單

        Args:
            order_dict (dict): 訂單字典

        Returns:
            Order: 訂單物件
        """
        order = cls(
            stock_id=order_dict["stock_id"],
            action=order_dict["action"],
            quantity=order_dict["quantity"],
            order_type=order_dict["order_type"],
            price=order_dict["price"],
            stop_price=order_dict["stop_price"],
            time_in_force=order_dict["time_in_force"],
        )
        order.status = order_dict["status"]
        order.filled_quantity = order_dict["filled_quantity"]
        order.filled_price = order_dict["filled_price"]
        order.order_id = order_dict["order_id"]
        order.created_at = order_dict["created_at"]
        order.updated_at = order_dict["updated_at"]
        return order


class BrokerAPI:
    """券商 API 基類，所有具體券商 API 都應該繼承此類"""

    def __init__(self, api_key=None, api_secret=None, account_id=None):
        """
        初始化券商 API

        Args:
            api_key (str, optional): API 金鑰
            api_secret (str, optional): API 密鑰
            account_id (str, optional): 帳戶 ID
        """
        self.api_key = api_key or os.getenv("BROKER_API_KEY")
        self.api_secret = api_secret or os.getenv("BROKER_API_SECRET")
        self.account_id = account_id or os.getenv("BROKER_ACCOUNT_ID")
        self.connected = False

    def connect(self):
        """
        連接券商 API

        Returns:
            bool: 是否連接成功
        """
        # 基類不實現具體的連接邏輯
        # 子類應該覆寫此方法
        raise NotImplementedError("子類必須實現 connect 方法")

    def disconnect(self):
        """
        斷開券商 API 連接

        Returns:
            bool: 是否斷開成功
        """
        # 基類不實現具體的斷開邏輯
        # 子類應該覆寫此方法
        raise NotImplementedError("子類必須實現 disconnect 方法")

    def get_account_info(self):
        """
        獲取帳戶資訊

        Returns:
            dict: 帳戶資訊
        """
        # 基類不實現具體的獲取帳戶資訊邏輯
        # 子類應該覆寫此方法
        raise NotImplementedError("子類必須實現 get_account_info 方法")

    def get_positions(self):
        """
        獲取持倉資訊

        Returns:
            dict: 持倉資訊
        """
        # 基類不實現具體的獲取持倉資訊邏輯
        # 子類應該覆寫此方法
        raise NotImplementedError("子類必須實現 get_positions 方法")

    def get_orders(self, status=None):
        """
        獲取訂單資訊

        Args:
            status (str, optional): 訂單狀態

        Returns:
            list: 訂單列表
        """
        # 基類不實現具體的獲取訂單資訊邏輯
        # 子類應該覆寫此方法
        raise NotImplementedError("子類必須實現 get_orders 方法")

    @retry(max_retries=3)
    def place_order(self, order):
        """
        下單

        Args:
            order (Order): 訂單物件

        Returns:
            str: 訂單 ID 或 None (如果下單失敗)
        """
        # 基類不實現具體的下單邏輯
        # 子類應該覆寫此方法
        raise NotImplementedError("子類必須實現 place_order 方法")

    def cancel_order(self, order_id):
        """
        取消訂單

        Args:
            order_id (str): 訂單 ID

        Returns:
            bool: 是否取消成功
        """
        # 基類不實現具體的取消訂單邏輯
        # 子類應該覆寫此方法
        raise NotImplementedError("子類必須實現 cancel_order 方法")

    def get_order_status(self, order_id):
        """
        獲取訂單狀態

        Args:
            order_id (str): 訂單 ID

        Returns:
            str: 訂單狀態
        """
        # 基類不實現具體的獲取訂單狀態邏輯
        # 子類應該覆寫此方法
        raise NotImplementedError("子類必須實現 get_order_status 方法")


class SimulatedBrokerAPI(BrokerAPI):
    """模擬券商 API，用於測試和模擬交易"""

    def __init__(
        self,
        api_key=None,
        api_secret=None,
        account_id=None,
        initial_capital=1000000,
        price_df=None,
    ):
        """
        初始化模擬券商 API

        Args:
            api_key (str, optional): API 金鑰
            api_secret (str, optional): API 密鑰
            account_id (str, optional): 帳戶 ID
            initial_capital (float): 初始資金
            price_df (pandas.DataFrame, optional): 價格資料
        """
        super().__init__(api_key, api_secret, account_id)
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        self.orders = {}
        self.next_order_id = 1
        self.price_df = price_df
        self.current_date = datetime.now().date()

    def connect(self):
        """
        連接模擬券商 API

        Returns:
            bool: 是否連接成功
        """
        self.connected = True
        logger.info("已連接模擬券商 API")
        return True

    def disconnect(self):
        """
        斷開模擬券商 API 連接

        Returns:
            bool: 是否斷開成功
        """
        self.connected = False
        logger.info("已斷開模擬券商 API 連接")
        return True

    def get_account_info(self):
        """
        獲取帳戶資訊

        Returns:
            dict: 帳戶資訊
        """
        # 計算持倉價值
        positions_value = sum(position["value"] for position in self.positions.values())

        return {
            "account_id": self.account_id,
            "cash": self.cash,
            "positions_value": positions_value,
            "total_value": self.cash + positions_value,
        }

    def get_positions(self):
        """
        獲取持倉資訊

        Returns:
            dict: 持倉資訊
        """
        # 更新持倉價值
        for stock_id, position in self.positions.items():
            # 獲取最新價格
            latest_price = self._get_latest_price(stock_id)

            # 更新持倉價值
            position["value"] = position["shares"] * latest_price
            position["current_price"] = latest_price
            position["profit_loss"] = position["value"] - position["cost"]
            position["profit_loss_pct"] = (
                position["profit_loss"] / position["cost"] * 100
                if position["cost"] > 0
                else 0
            )

        return self.positions

    def get_orders(self, status=None):
        """
        獲取訂單資訊

        Args:
            status (str, optional): 訂單狀態

        Returns:
            list: 訂單列表
        """
        if status is None:
            return list(self.orders.values())
        else:
            return [order for order in self.orders.values() if order.status == status]

    @retry(max_retries=3)
    def place_order(self, order):
        """
        下單

        Args:
            order (Order): 訂單物件

        Returns:
            str: 訂單 ID 或 None (如果下單失敗)
        """
        # 檢查是否連接
        if not self.connected:
            logger.error("未連接券商 API")
            order.status = OrderStatus.REJECTED
            return None

        # 生成訂單 ID
        order_id = str(self.next_order_id)
        self.next_order_id += 1
        order.order_id = order_id

        # 更新訂單狀態
        order.status = OrderStatus.SUBMITTED

        # 儲存訂單
        self.orders[order_id] = order

        # 模擬訂單執行
        self._execute_order(order)

        return order_id

    def cancel_order(self, order_id):
        """
        取消訂單

        Args:
            order_id (str): 訂單 ID

        Returns:
            bool: 是否取消成功
        """
        # 檢查是否連接
        if not self.connected:
            logger.error("未連接券商 API")
            return False

        # 檢查訂單是否存在
        if order_id not in self.orders:
            logger.error(f"訂單 {order_id} 不存在")
            return False

        # 獲取訂單
        order = self.orders[order_id]

        # 檢查訂單狀態
        if order.status in [
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
        ]:
            logger.error(f"訂單 {order_id} 狀態為 {order.status}，無法取消")
            return False

        # 更新訂單狀態
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now()

        return True

    def get_order_status(self, order_id):
        """
        獲取訂單狀態

        Args:
            order_id (str): 訂單 ID

        Returns:
            str: 訂單狀態
        """
        # 檢查是否連接
        if not self.connected:
            logger.error("未連接券商 API")
            return None

        # 檢查訂單是否存在
        if order_id not in self.orders:
            logger.error(f"訂單 {order_id} 不存在")
            return None

        # 獲取訂單
        order = self.orders[order_id]

        return order.status

    def _execute_order(self, order):
        """
        執行訂單

        Args:
            order (Order): 訂單物件
        """
        # 獲取最新價格
        latest_price = self._get_latest_price(order.stock_id)

        if latest_price is None:
            logger.error(f"無法獲取股票 {order.stock_id} 的價格")
            order.status = OrderStatus.REJECTED
            order.updated_at = datetime.now()
            return

        # 根據訂單類型計算成交價格
        if order.order_type == OrderType.MARKET:
            # 市價單
            execution_price = latest_price
        elif order.order_type == OrderType.LIMIT:
            # 限價單
            if order.action == "buy" and latest_price > order.price:
                # 買入限價單，價格高於限價，不成交
                return
            elif order.action == "sell" and latest_price < order.price:
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
            execution_price = latest_price
        elif order.order_type == OrderType.STOP_LIMIT:
            # 停損限價單
            if order.action == "buy" and latest_price < order.stop_price:
                # 買入停損限價單，價格低於停損價，不成交
                return
            elif order.action == "sell" and latest_price > order.stop_price:
                # 賣出停損限價單，價格高於停損價，不成交
                return

            # 檢查限價
            if order.action == "buy" and latest_price > order.price:
                # 買入限價單，價格高於限價，不成交
                return
            elif order.action == "sell" and latest_price < order.price:
                # 賣出限價單，價格低於限價，不成交
                return
            execution_price = order.price

        # 計算成交金額
        execution_amount = order.quantity * execution_price

        # 執行交易
        if order.action == "buy":
            # 檢查資金是否足夠
            if self.cash < execution_amount:
                logger.error(f"資金不足，無法執行買入訂單 {order.order_id}")
                order.status = OrderStatus.REJECTED
                order.updated_at = datetime.now()
                return

            # 更新現金
            self.cash -= execution_amount

            # 更新持倉
            if order.stock_id in self.positions:
                # 已有持倉，更新持倉
                position = self.positions[order.stock_id]
                position["shares"] += order.quantity
                position["cost"] += execution_amount
                position["value"] = position["shares"] * latest_price
                position["current_price"] = latest_price
                position["profit_loss"] = position["value"] - position["cost"]
                position["profit_loss_pct"] = (
                    position["profit_loss"] / position["cost"] * 100
                    if position["cost"] > 0
                    else 0
                )
            else:
                # 新建持倉
                self.positions[order.stock_id] = {
                    "stock_id": order.stock_id,
                    "shares": order.quantity,
                    "cost": execution_amount,
                    "value": order.quantity * latest_price,
                    "current_price": latest_price,
                    "profit_loss": 0,
                    "profit_loss_pct": 0,
                }
        elif order.action == "sell":
            # 檢查持倉是否足夠
            if (
                order.stock_id not in self.positions
                or self.positions[order.stock_id]["shares"] < order.quantity
            ):
                logger.error(f"持倉不足，無法執行賣出訂單 {order.order_id}")
                order.status = OrderStatus.REJECTED
                order.updated_at = datetime.now()
                return

            # 更新現金
            self.cash += execution_amount

            # 更新持倉
            position = self.positions[order.stock_id]
            position["shares"] -= order.quantity

            # 計算賣出成本
            sell_cost = position["cost"] * (
                order.quantity / (position["shares"] + order.quantity)
            )
            position["cost"] -= sell_cost

            # 更新持倉價值
            position["value"] = position["shares"] * latest_price
            position["current_price"] = latest_price
            position["profit_loss"] = position["value"] - position["cost"]
            position["profit_loss_pct"] = (
                position["profit_loss"] / position["cost"] * 100
                if position["cost"] > 0
                else 0
            )

            # 如果持倉為 0，則刪除持倉
            if position["shares"] == 0:
                del self.positions[order.stock_id]

        # 更新訂單狀態
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.filled_price = execution_price
        order.updated_at = datetime.now()

        logger.info(
            f"訂單 {order.order_id} 已成交，股票 {order.stock_id}，動作 {order.action}，數量 {order.quantity}，價格 {execution_price}"
        )

    def _get_latest_price(self, stock_id):
        """
        獲取最新價格

        Args:
            stock_id (str): 股票代號

        Returns:
            float: 最新價格
        """
        if self.price_df is None:
            # 如果沒有提供價格資料，則返回隨機價格
            return np.random.uniform(50, 200)

        # 獲取該股票的所有價格
        stock_prices = self.price_df.xs(stock_id, level="stock_id")["收盤價"].astype(
            float
        )

        # 獲取最新價格
        latest_price = stock_prices.iloc[-1] if not stock_prices.empty else None

        return latest_price


class ShioajiBrokerAPI(BrokerAPI):
    """永豐證券 API，使用 shioaji 套件實現"""

    def __init__(self, api_key=None, api_secret=None, account_id=None, person_id=None):
        """
        初始化永豐證券 API

        Args:
            api_key (str, optional): API 金鑰
            api_secret (str, optional): API 密鑰
            account_id (str, optional): 帳戶 ID
            person_id (str, optional): 身分證字號
        """
        super().__init__(api_key, api_secret, account_id)
        self.person_id = person_id or os.getenv("BROKER_PERSON_ID")
        self.api = shioaji.Shioaji()
        self.account = None

    def connect(self):
        """
        連接永豐證券 API

        Returns:
            bool: 是否連接成功
        """
        try:
            self.api.login(
                api_key=self.api_key,
                secret_key=self.api_secret,
                person_id=self.person_id,
            )

            # 選擇帳戶
            self.account = self.api.get_accounts()[0]
            self.api.set_default_account(self.account)

            self.connected = True
            logger.info("已連接永豐證券 API")
            return True
        except Exception as e:
            logger.error(f"連接永豐證券 API 失敗: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """
        斷開永豐證券 API 連接

        Returns:
            bool: 是否斷開成功
        """
        try:
            self.api.logout()
            self.connected = False
            logger.info("已斷開永豐證券 API 連接")
            return True
        except Exception as e:
            logger.error(f"斷開永豐證券 API 連接失敗: {e}")
            return False

    def get_account_info(self):
        """
        獲取帳戶資訊

        Returns:
            dict: 帳戶資訊
        """
        if not self.connected:
            logger.error("未連接永豐證券 API")
            return {}

        try:
            # 獲取帳戶餘額
            balance = self.api.account_balance()

            # 獲取持倉價值
            positions = self.get_positions()
            positions_value = sum(position["value"] for position in positions.values())

            return {
                "account_id": self.account_id,
                "cash": balance.acc_balance,
                "positions_value": positions_value,
                "total_value": balance.acc_balance + positions_value,
            }
        except Exception as e:
            logger.error(f"獲取帳戶資訊失敗: {e}")
            return {}

    def get_positions(self):
        """
        獲取持倉資訊

        Returns:
            dict: 持倉資訊
        """
        if not self.connected:
            logger.error("未連接永豐證券 API")
            return {}

        try:
            # 獲取持倉
            positions = {}
            stock_positions = self.api.list_positions(self.account)

            for position in stock_positions:
                stock_id = position.code
                shares = position.quantity
                cost = position.price * shares
                current_price = self.api.snapshots(
                    [self.api.Contracts.Stocks[stock_id]]
                )[0].close
                value = current_price * shares
                profit_loss = value - cost
                profit_loss_pct = profit_loss / cost * 100 if cost > 0 else 0

                positions[stock_id] = {
                    "stock_id": stock_id,
                    "shares": shares,
                    "cost": cost,
                    "value": value,
                    "current_price": current_price,
                    "profit_loss": profit_loss,
                    "profit_loss_pct": profit_loss_pct,
                }

            return positions
        except Exception as e:
            logger.error(f"獲取持倉資訊失敗: {e}")
            return {}

    def get_orders(self, status=None):
        """
        獲取訂單資訊

        Args:
            status (str, optional): 訂單狀態

        Returns:
            list: 訂單列表
        """
        if not self.connected:
            logger.error("未連接永豐證券 API")
            return []

        try:
            # 獲取訂單
            orders = []
            api_orders = self.api.list_orders()

            for api_order in api_orders:
                # 轉換訂單狀態
                if api_order.status.status == "Filled":
                    order_status = OrderStatus.FILLED
                elif api_order.status.status == "PartFilled":
                    order_status = OrderStatus.PARTIALLY_FILLED
                elif api_order.status.status == "Cancelled":
                    order_status = OrderStatus.CANCELLED
                elif api_order.status.status == "Rejected":
                    order_status = OrderStatus.REJECTED
                else:
                    order_status = OrderStatus.SUBMITTED

                # 轉換訂單類型
                if api_order.price == 0:
                    order_type = OrderType.MARKET
                else:
                    order_type = OrderType.LIMIT

                # 創建訂單物件
                order = Order(
                    stock_id=api_order.contract.code,
                    action="buy" if api_order.action == "Buy" else "sell",
                    quantity=api_order.quantity,
                    order_type=order_type,
                    price=api_order.price if api_order.price > 0 else None,
                    stop_price=None,
                    time_in_force="day",
                )

                order.status = order_status
                order.filled_quantity = api_order.filled
                order.filled_price = api_order.price
                order.order_id = api_order.id
                order.created_at = api_order.create_time
                order.updated_at = api_order.status.time

                # 根據狀態過濾
                if status is None or order.status == status:
                    orders.append(order)

            return orders
        except Exception as e:
            logger.error(f"獲取訂單資訊失敗: {e}")
            return []

    @retry(max_retries=3)
    def place_order(self, order):
        """
        下單

        Args:
            order (Order): 訂單物件

        Returns:
            str: 訂單 ID 或 None (如果下單失敗)
        """
        if not self.connected:
            logger.error("未連接永豐證券 API")
            order.status = OrderStatus.REJECTED
            return None

        try:
            # 獲取合約
            contract = self.api.Contracts.Stocks[order.stock_id]

            # 設定訂單參數
            action = (
                shioaji.constant.Action.Buy
                if order.action == "buy"
                else shioaji.constant.Action.Sell
            )
            price_type = (
                shioaji.constant.StockPriceType.LMT
                if order.order_type == OrderType.LIMIT
                else shioaji.constant.StockPriceType.MKT
            )
            order_type = shioaji.constant.OrderType.ROD  # 當日有效

            # 下單
            api_order = self.api.place_order(
                contract=contract,
                price=order.price if order.price is not None else 0,
                quantity=order.quantity,
                action=action,
                price_type=price_type,
                order_type=order_type,
            )

            # 更新訂單狀態
            order.order_id = api_order.id
            order.status = OrderStatus.SUBMITTED
            order.updated_at = datetime.now()

            logger.info(f"訂單已提交: {order.order_id}")

            return order.order_id
        except Exception as e:
            logger.error(f"下單失敗: {e}")
            order.status = OrderStatus.REJECTED
            return None

    @retry(max_retries=3)
    def cancel_order(self, order_id):
        """
        取消訂單

        Args:
            order_id (str): 訂單 ID

        Returns:
            bool: 是否取消成功
        """
        if not self.connected:
            logger.error("未連接永豐證券 API")
            return False

        try:
            # 獲取訂單
            api_orders = self.api.list_orders()
            api_order = next((o for o in api_orders if o.id == order_id), None)

            if api_order is None:
                logger.error(f"訂單 {order_id} 不存在")
                return False

            # 取消訂單
            self.api.cancel_order(api_order)

            logger.info(f"訂單 {order_id} 已取消")

            return True
        except Exception as e:
            logger.error(f"取消訂單失敗: {e}")
            return False

    def get_order_status(self, order_id):
        """
        獲取訂單狀態

        Args:
            order_id (str): 訂單 ID

        Returns:
            str: 訂單狀態
        """
        if not self.connected:
            logger.error("未連接永豐證券 API")
            return None

        try:
            # 獲取訂單
            api_orders = self.api.list_orders()
            api_order = next((o for o in api_orders if o.id == order_id), None)

            if api_order is None:
                logger.error(f"訂單 {order_id} 不存在")
                return None

            # 轉換訂單狀態
            if api_order.status.status == "Filled":
                return OrderStatus.FILLED
            elif api_order.status.status == "PartFilled":
                return OrderStatus.PARTIALLY_FILLED
            elif api_order.status.status == "Cancelled":
                return OrderStatus.CANCELLED
            elif api_order.status.status == "Rejected":
                return OrderStatus.REJECTED
            else:
                return OrderStatus.SUBMITTED
        except Exception as e:
            logger.error(f"獲取訂單狀態失敗: {e}")
            return None

    @retry(max_retries=3)
    def query_position(self, stock_id=None):
        """
        查詢持倉

        Args:
            stock_id (str, optional): 股票代號，如果為 None 則查詢所有持倉

        Returns:
            dict: 持倉資訊
        """
        if not self.connected:
            logger.error("未連接永豐證券 API")
            return {}

        try:
            positions = self.get_positions()

            if stock_id is not None:
                return positions.get(stock_id, {})
            else:
                return positions
        except Exception as e:
            logger.error(f"查詢持倉失敗: {e}")
            return {}


class Executor:
    """執行器類，用於執行交易訂單"""

    def __init__(
        self,
        broker_type="simulated",
        api_key=None,
        api_secret=None,
        account_id=None,
        person_id=None,
    ):
        """
        初始化執行器

        Args:
            broker_type (str): 券商類型，可選 'simulated', 'shioaji'
            api_key (str, optional): API 金鑰
            api_secret (str, optional): API 密鑰
            account_id (str, optional): 帳戶 ID
            person_id (str, optional): 身分證字號
        """
        self.broker_type = broker_type

        # 創建券商 API
        if broker_type == "simulated":
            self.broker = SimulatedBrokerAPI(api_key, api_secret, account_id)
        elif broker_type == "shioaji":
            self.broker = ShioajiBrokerAPI(api_key, api_secret, account_id, person_id)
        else:
            raise ValueError(f"不支援的券商類型: {broker_type}")

        # 初始化訂單記錄
        self.order_log = []

        # 初始化事件循環
        self.loop = None
        self.market_data_task = None
        self.order_execution_task = None
        self.running = False

    def connect(self):
        """
        連接券商 API

        Returns:
            bool: 是否連接成功
        """
        return self.broker.connect()

    def disconnect(self):
        """
        斷開券商 API 連接

        Returns:
            bool: 是否斷開成功
        """
        return self.broker.disconnect()

    def place_orders(self, orders):
        """
        批量下單

        Args:
            orders (list): 訂單列表，每個訂單是一個字典，包含以下欄位：
                - stock_id (str): 股票代號
                - action (str): 交易動作，'buy' 或 'sell'
                - quantity (int): 交易數量
                - order_type (str, optional): 訂單類型，預設為 'market'
                - price (float, optional): 限價
                - stop_price (float, optional): 停損價
                - time_in_force (str, optional): 訂單有效期，預設為 'day'

        Returns:
            list: 訂單 ID 列表
        """
        order_ids = []

        for order_dict in orders:
            # 創建訂單物件
            order = Order(
                stock_id=order_dict["stock_id"],
                action=order_dict["action"],
                quantity=order_dict["quantity"],
                order_type=order_dict.get("order_type", OrderType.MARKET),
                price=order_dict.get("price"),
                stop_price=order_dict.get("stop_price"),
                time_in_force=order_dict.get("time_in_force", "day"),
            )

            # 下單
            order_id = self.broker.place_order(order)

            if order_id:
                order_ids.append(order_id)

                # 記錄訂單
                self.order_log.append(
                    {
                        "order_id": order_id,
                        "stock_id": order.stock_id,
                        "action": order.action,
                        "quantity": order.quantity,
                        "order_type": order.order_type,
                        "price": order.price,
                        "status": order.status,
                        "timestamp": datetime.now(),
                    }
                )

        return order_ids

    def cancel_orders(self, order_ids):
        """
        批量取消訂單

        Args:
            order_ids (list): 訂單 ID 列表

        Returns:
            list: 成功取消的訂單 ID 列表
        """
        cancelled_order_ids = []

        for order_id in order_ids:
            if self.broker.cancel_order(order_id):
                cancelled_order_ids.append(order_id)

        return cancelled_order_ids

    def get_positions(self):
        """
        獲取持倉資訊

        Returns:
            dict: 持倉資訊
        """
        return self.broker.get_positions()

    def get_account_info(self):
        """
        獲取帳戶資訊

        Returns:
            dict: 帳戶資訊
        """
        return self.broker.get_account_info()

    def get_orders(self, status=None):
        """
        獲取訂單資訊

        Args:
            status (str, optional): 訂單狀態

        Returns:
            list: 訂單列表
        """
        return self.broker.get_orders(status)

    def query_position(self, stock_id=None):
        """
        查詢持倉

        Args:
            stock_id (str, optional): 股票代號，如果為 None 則查詢所有持倉

        Returns:
            dict: 持倉資訊
        """
        if hasattr(self.broker, "query_position"):
            return self.broker.query_position(stock_id)
        else:
            return (
                self.broker.get_positions().get(stock_id, {})
                if stock_id
                else self.broker.get_positions()
            )

    async def start_market_data_loop(self, callback=None, interval=1):
        """
        啟動市場資料循環

        Args:
            callback (function, optional): 回調函數，接收市場資料
            interval (int): 更新間隔（秒）
        """
        self.running = True

        while self.running:
            try:
                # 獲取市場資料
                positions = self.broker.get_positions()

                # 如果有回調函數，則調用
                if callback:
                    callback(positions)

                # 等待下一次更新
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"市場資料循環發生錯誤: {e}")
                await asyncio.sleep(10)

    async def start_order_execution_loop(self, callback=None, interval=1):
        """
        啟動訂單執行循環

        Args:
            callback (function, optional): 回調函數，接收訂單執行結果
            interval (int): 更新間隔（秒）
        """
        self.running = True

        while self.running:
            try:
                # 獲取訂單資訊
                orders = self.broker.get_orders()

                # 如果有回調函數，則調用
                if callback:
                    callback(orders)

                # 等待下一次更新
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"訂單執行循環發生錯誤: {e}")
                await asyncio.sleep(10)

    def start_async_loops(
        self, market_data_callback=None, order_execution_callback=None
    ):
        """
        啟動非同步循環

        Args:
            market_data_callback (function, optional): 市場資料回調函數
            order_execution_callback (function, optional): 訂單執行回調函數
        """
        # 創建事件循環
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # 創建任務
        self.market_data_task = self.loop.create_task(
            self.start_market_data_loop(market_data_callback)
        )

        self.order_execution_task = self.loop.create_task(
            self.start_order_execution_loop(order_execution_callback)
        )

        # 啟動事件循環
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_async_loops()

    def stop_async_loops(self):
        """停止非同步循環"""
        self.running = False

        if self.market_data_task:
            self.market_data_task.cancel()

        if self.order_execution_task:
            self.order_execution_task.cancel()

        if self.loop:
            self.loop.stop()
            self.loop.close()

    def adjust_orders(self, signals):
        """
        根據訊號調整訂單

        Args:
            signals (pandas.DataFrame): 交易訊號

        Returns:
            list: 訂單 ID 列表
        """
        # 獲取持倉
        positions = self.broker.get_positions()

        # 創建訂單列表
        orders = []

        # 處理賣出訊號
        if "sell_signal" in signals.columns:
            sell_signals = signals[signals["sell_signal"] == 1]

            for (stock_id, _), _ in sell_signals.iterrows():
                # 檢查是否持有該股票
                if stock_id in positions:
                    # 創建賣出訂單
                    orders.append(
                        {
                            "stock_id": stock_id,
                            "action": "sell",
                            "quantity": positions[stock_id]["shares"],
                            "order_type": OrderType.MARKET,
                        }
                    )

        # 處理買入訊號
        if "buy_signal" in signals.columns:
            buy_signals = signals[signals["buy_signal"] == 1]

            # 獲取帳戶資訊
            account_info = self.broker.get_account_info()
            cash = account_info.get("cash", 0)

            # 計算每個股票的分配金額
            allocation_per_stock = (
                cash / len(buy_signals) if len(buy_signals) > 0 else 0
            )

            for (stock_id, _), _ in buy_signals.iterrows():
                # 檢查是否已經持有該股票
                if stock_id not in positions:
                    # 獲取股票價格
                    price = self.broker._get_latest_price(stock_id)

                    if price:
                        # 計算買入數量
                        quantity = int(allocation_per_stock / price)

                        if quantity > 0:
                            # 創建買入訂單
                            orders.append(
                                {
                                    "stock_id": stock_id,
                                    "action": "buy",
                                    "quantity": quantity,
                                    "order_type": OrderType.MARKET,
                                }
                            )

        # 下單
        return self.place_orders(orders)


async def execute(
    signals,
    broker_type="simulated",
    api_key=None,
    api_secret=None,
    account_id=None,
    person_id=None,
):
    """
    非同步執行交易訊號

    Args:
        signals (pandas.DataFrame): 交易訊號
        broker_type (str): 券商類型，可選 'simulated', 'shioaji'
        api_key (str, optional): API 金鑰
        api_secret (str, optional): API 密鑰
        account_id (str, optional): 帳戶 ID
        person_id (str, optional): 身分證字號

    Returns:
        list: 訂單 ID 列表
    """
    # 創建執行器
    executor = Executor(broker_type, api_key, api_secret, account_id, person_id)

    # 連接券商 API
    if not executor.connect():
        logger.error("連接券商 API 失敗")
        return []

    try:
        # 調整訂單
        order_ids = executor.adjust_orders(signals)

        # 啟動市場資料循環和訂單執行循環
        market_data_task = asyncio.create_task(executor.start_market_data_loop())

        order_execution_task = asyncio.create_task(
            executor.start_order_execution_loop()
        )

        # 等待一段時間
        await asyncio.sleep(10)

        # 取消任務
        market_data_task.cancel()
        order_execution_task.cancel()

        return order_ids
    finally:
        # 斷開連接
        executor.disconnect()


def place_orders(orders):
    """
    執行交易訂單的主函數

    Args:
        orders (list): 訂單列表，每個訂單是一個字典，包含以下欄位：
            - stock_id (str): 股票代號
            - action (str): 交易動作，'buy' 或 'sell'
            - quantity (int): 交易數量
            - order_type (str, optional): 訂單類型，預設為 'market'
            - price (float, optional): 限價
            - stop_price (float, optional): 停損價
            - time_in_force (str, optional): 訂單有效期，預設為 'day'

    Returns:
        list: 訂單 ID 列表
    """
    # 創建執行器
    executor = Executor()

    # 連接券商 API
    executor.connect()

    try:
        # 下單
        order_ids = executor.place_orders(orders)
        return order_ids
    finally:
        # 斷開連接
        executor.disconnect()
