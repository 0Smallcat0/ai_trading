"""
券商 API 基礎類別

此模組定義了券商 API 的基礎介面，所有具體的券商 API 適配器都應該繼承此類別。
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
import logging
from enum import Enum

# 設定日誌
logger = logging.getLogger("execution.broker")


class OrderStatus(Enum):
    """訂單狀態列舉"""
    PENDING = "pending"           # 等待中
    SUBMITTED = "submitted"       # 已提交
    FILLED = "filled"             # 已成交
    PARTIALLY_FILLED = "partially_filled"  # 部分成交
    CANCELLED = "cancelled"       # 已取消
    REJECTED = "rejected"         # 已拒絕
    EXPIRED = "expired"           # 已過期


class OrderType(Enum):
    """訂單類型列舉"""
    MARKET = "market"             # 市價單
    LIMIT = "limit"               # 限價單
    STOP = "stop"                 # 停損單
    STOP_LIMIT = "stop_limit"     # 停損限價單
    IOC = "ioc"                   # 立即成交否則取消
    FOK = "fok"                   # 全部成交否則取消


class Order:
    """訂單類別，用於表示交易訂單"""

    def __init__(
        self,
        stock_id: str,
        action: str,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "day",
        order_id: Optional[str] = None,
    ):
        """
        初始化訂單

        Args:
            stock_id (str): 股票代號
            action (str): 交易動作，'buy' 或 'sell'
            quantity (int): 交易數量
            order_type (OrderType): 訂單類型
            price (float, optional): 限價
            stop_price (float, optional): 停損價
            time_in_force (str): 訂單有效期，可選 'day', 'gtc' (good till cancel)
            order_id (str, optional): 訂單 ID，如果為 None 則由券商 API 生成
        """
        self.stock_id = stock_id
        self.action = action
        self.quantity = quantity
        self.order_type = order_type
        self.price = price
        self.stop_price = stop_price
        self.time_in_force = time_in_force
        self.order_id = order_id
        self.status = OrderStatus.PENDING
        self.filled_quantity = 0
        self.filled_price = 0
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.error_message = None
        self.exchange_order_id = None  # 券商系統中的訂單 ID
        self.transactions = []  # 成交記錄

    def __str__(self):
        """訂單的字串表示"""
        return (
            f"Order(id={self.order_id}, stock={self.stock_id}, "
            f"action={self.action}, quantity={self.quantity}, "
            f"type={self.order_type.value}, price={self.price}, "
            f"status={self.status.value}, filled={self.filled_quantity})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """將訂單轉換為字典"""
        return {
            "order_id": self.order_id,
            "stock_id": self.stock_id,
            "action": self.action,
            "quantity": self.quantity,
            "order_type": self.order_type.value,
            "price": self.price,
            "stop_price": self.stop_price,
            "time_in_force": self.time_in_force,
            "status": self.status.value,
            "filled_quantity": self.filled_quantity,
            "filled_price": self.filled_price,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "error_message": self.error_message,
            "exchange_order_id": self.exchange_order_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Order':
        """從字典創建訂單"""
        order = cls(
            stock_id=data["stock_id"],
            action=data["action"],
            quantity=data["quantity"],
            order_type=OrderType(data["order_type"]),
            price=data.get("price"),
            stop_price=data.get("stop_price"),
            time_in_force=data.get("time_in_force", "day"),
            order_id=data.get("order_id"),
        )
        order.status = OrderStatus(data["status"])
        order.filled_quantity = data["filled_quantity"]
        order.filled_price = data["filled_price"]
        order.created_at = datetime.fromisoformat(data["created_at"])
        order.updated_at = datetime.fromisoformat(data["updated_at"])
        order.error_message = data.get("error_message")
        order.exchange_order_id = data.get("exchange_order_id")
        return order


class BrokerBase(ABC):
    """券商 API 基礎類別，所有具體的券商 API 適配器都應該繼承此類別"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        account_id: Optional[str] = None,
        **kwargs
    ):
        """
        初始化券商 API

        Args:
            api_key (str, optional): API 金鑰
            api_secret (str, optional): API 密鑰
            account_id (str, optional): 帳戶 ID
            **kwargs: 其他參數
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.account_id = account_id
        self.connected = False
        self.orders = {}  # 訂單字典，key 為訂單 ID
        self.positions = {}  # 持倉字典，key 為股票代號
        self.cash = 0  # 可用資金
        self.total_value = 0  # 總資產價值
        self.logger = logger

    @abstractmethod
    def connect(self) -> bool:
        """
        連接券商 API

        Returns:
            bool: 是否連接成功
        """
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """
        斷開券商 API 連接

        Returns:
            bool: 是否斷開成功
        """
        pass

    @abstractmethod
    def place_order(self, order: Order) -> Optional[str]:
        """
        下單

        Args:
            order (Order): 訂單物件

        Returns:
            str: 訂單 ID 或 None (如果下單失敗)
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        取消訂單

        Args:
            order_id (str): 訂單 ID

        Returns:
            bool: 是否取消成功
        """
        pass

    @abstractmethod
    def get_order(self, order_id: str) -> Optional[Order]:
        """
        獲取訂單資訊

        Args:
            order_id (str): 訂單 ID

        Returns:
            Order: 訂單物件或 None (如果訂單不存在)
        """
        pass

    @abstractmethod
    def get_orders(self, status: Optional[OrderStatus] = None) -> List[Order]:
        """
        獲取訂單列表

        Args:
            status (OrderStatus, optional): 訂單狀態

        Returns:
            List[Order]: 訂單列表
        """
        pass

    @abstractmethod
    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        獲取持倉資訊

        Returns:
            Dict[str, Dict[str, Any]]: 持倉資訊，key 為股票代號
        """
        pass

    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """
        獲取帳戶資訊

        Returns:
            Dict[str, Any]: 帳戶資訊
        """
        pass

    @abstractmethod
    def get_market_data(self, stock_id: str) -> Dict[str, Any]:
        """
        獲取市場資料

        Args:
            stock_id (str): 股票代號

        Returns:
            Dict[str, Any]: 市場資料
        """
        pass

    def place_orders(self, orders: List[Dict[str, Any]]) -> List[str]:
        """
        批量下單

        Args:
            orders (List[Dict[str, Any]]): 訂單列表，每個訂單是一個字典

        Returns:
            List[str]: 訂單 ID 列表
        """
        order_ids = []
        for order_dict in orders:
            # 創建訂單物件
            order = Order(
                stock_id=order_dict["stock_id"],
                action=order_dict["action"],
                quantity=order_dict["quantity"],
                order_type=OrderType(order_dict.get("order_type", "market")),
                price=order_dict.get("price"),
                stop_price=order_dict.get("stop_price"),
                time_in_force=order_dict.get("time_in_force", "day"),
            )

            # 下單
            order_id = self.place_order(order)
            if order_id:
                order_ids.append(order_id)

        return order_ids
