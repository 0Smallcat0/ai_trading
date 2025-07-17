"""Interactive Brokers 訂單管理模組

此模組提供 IB API 訂單的創建和管理功能，支援多種訂單類型和時效設定。
包括市價單、限價單、停損單、停利單等。

版本: v1.0
作者: AI Trading System
"""

import logging
from typing import Optional, Dict, Any
from enum import Enum

try:
    from ibapi.order import Order as IBOrder
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False
    # 定義模擬類型以避免 NameError
    class IBOrder:
        """模擬 IBOrder 類"""
        def __init__(self):
            self.action = ""
            self.totalQuantity = 0
            self.orderType = ""
            self.lmtPrice = 0.0
            self.auxPrice = 0.0
            self.tif = ""
            self.outsideRth = False
            self.hidden = False
            self.discretionaryAmt = 0.0

from .broker_base import Order, OrderType

# 設定日誌
logger = logging.getLogger("execution.ib.orders")


class IBOrderType(Enum):
    """IB 訂單類型枚舉"""
    MARKET = "MKT"
    LIMIT = "LMT"
    STOP = "STP"
    STOP_LIMIT = "STP LMT"
    MARKET_ON_CLOSE = "MOC"
    LIMIT_ON_CLOSE = "LOC"
    PEGGED_TO_MARKET = "PEG MKT"
    RELATIVE = "REL"
    BRACKET = "BRACKET"
    ONE_CANCELS_ALL = "OCA"


class TimeInForce(Enum):
    """訂單時效枚舉"""
    DAY = "DAY"
    GOOD_TILL_CANCELLED = "GTC"
    IMMEDIATE_OR_CANCEL = "IOC"
    FILL_OR_KILL = "FOK"
    GOOD_TILL_DATE = "GTD"
    MARKET_ON_OPEN = "OPG"
    MARKET_ON_CLOSE = "MOC"


class IBOrderManager:
    """IB 訂單管理器
    
    提供創建和管理各種 IB 訂單的功能，包括基本訂單類型和高級訂單策略。
    """

    def __init__(self):
        """初始化訂單管理器"""
        self._order_defaults = {
            'tif': TimeInForce.DAY.value,
            'outsideRth': False,
            'hidden': False,
            'discretionaryAmt': 0.0
        }

    def create_market_order(
        self,
        action: str,
        quantity: int,
        **kwargs
    ) -> Optional[IBOrder]:
        """創建市價單
        
        Args:
            action: 買賣方向 ('BUY' 或 'SELL')
            quantity: 數量
            **kwargs: 其他訂單參數
            
        Returns:
            IBOrder: IB 市價單或 None
            
        Example:
            >>> manager = IBOrderManager()
            >>> order = manager.create_market_order("BUY", 100)
            >>> order.orderType
            'MKT'
        """
        try:
            if not self._validate_basic_params(action, quantity):
                return None

            ib_order = IBOrder()
            ib_order.action = action.upper()
            ib_order.totalQuantity = quantity
            ib_order.orderType = IBOrderType.MARKET.value
            
            # 應用預設值和自定義參數
            self._apply_order_params(ib_order, kwargs)
            
            logger.debug(
                "創建市價單 - 方向: %s, 數量: %d",
                ib_order.action, ib_order.totalQuantity
            )
            
            return ib_order

        except Exception as e:
            logger.exception("創建市價單失敗: %s", e)
            return None

    def create_limit_order(
        self,
        action: str,
        quantity: int,
        limit_price: float,
        **kwargs
    ) -> Optional[IBOrder]:
        """創建限價單
        
        Args:
            action: 買賣方向 ('BUY' 或 'SELL')
            quantity: 數量
            limit_price: 限價
            **kwargs: 其他訂單參數
            
        Returns:
            IBOrder: IB 限價單或 None
        """
        try:
            if not self._validate_basic_params(action, quantity):
                return None
            
            if limit_price <= 0:
                logger.error("無效的限價: %.2f", limit_price)
                return None

            ib_order = IBOrder()
            ib_order.action = action.upper()
            ib_order.totalQuantity = quantity
            ib_order.orderType = IBOrderType.LIMIT.value
            ib_order.lmtPrice = limit_price
            
            # 應用預設值和自定義參數
            self._apply_order_params(ib_order, kwargs)
            
            logger.debug(
                "創建限價單 - 方向: %s, 數量: %d, 限價: %.2f",
                ib_order.action, ib_order.totalQuantity, ib_order.lmtPrice
            )
            
            return ib_order

        except Exception as e:
            logger.exception("創建限價單失敗: %s", e)
            return None

    def create_stop_order(
        self,
        action: str,
        quantity: int,
        stop_price: float,
        **kwargs
    ) -> Optional[IBOrder]:
        """創建停損單
        
        Args:
            action: 買賣方向 ('BUY' 或 'SELL')
            quantity: 數量
            stop_price: 停損價
            **kwargs: 其他訂單參數
            
        Returns:
            IBOrder: IB 停損單或 None
        """
        try:
            if not self._validate_basic_params(action, quantity):
                return None
            
            if stop_price <= 0:
                logger.error("無效的停損價: %.2f", stop_price)
                return None

            ib_order = IBOrder()
            ib_order.action = action.upper()
            ib_order.totalQuantity = quantity
            ib_order.orderType = IBOrderType.STOP.value
            ib_order.auxPrice = stop_price
            
            # 應用預設值和自定義參數
            self._apply_order_params(ib_order, kwargs)
            
            logger.debug(
                "創建停損單 - 方向: %s, 數量: %d, 停損價: %.2f",
                ib_order.action, ib_order.totalQuantity, ib_order.auxPrice
            )
            
            return ib_order

        except Exception as e:
            logger.exception("創建停損單失敗: %s", e)
            return None

    def create_stop_limit_order(
        self,
        action: str,
        quantity: int,
        stop_price: float,
        limit_price: float,
        **kwargs
    ) -> Optional[IBOrder]:
        """創建停損限價單
        
        Args:
            action: 買賣方向 ('BUY' 或 'SELL')
            quantity: 數量
            stop_price: 停損價
            limit_price: 限價
            **kwargs: 其他訂單參數
            
        Returns:
            IBOrder: IB 停損限價單或 None
        """
        try:
            if not self._validate_basic_params(action, quantity):
                return None
            
            if stop_price <= 0 or limit_price <= 0:
                logger.error("無效的價格 - 停損價: %.2f, 限價: %.2f", stop_price, limit_price)
                return None

            ib_order = IBOrder()
            ib_order.action = action.upper()
            ib_order.totalQuantity = quantity
            ib_order.orderType = IBOrderType.STOP_LIMIT.value
            ib_order.auxPrice = stop_price
            ib_order.lmtPrice = limit_price
            
            # 應用預設值和自定義參數
            self._apply_order_params(ib_order, kwargs)
            
            logger.debug(
                "創建停損限價單 - 方向: %s, 數量: %d, 停損價: %.2f, 限價: %.2f",
                ib_order.action, ib_order.totalQuantity, ib_order.auxPrice, ib_order.lmtPrice
            )
            
            return ib_order

        except Exception as e:
            logger.exception("創建停損限價單失敗: %s", e)
            return None

    def create_order_from_base(self, order: Order) -> Optional[IBOrder]:
        """從基礎訂單物件創建 IB 訂單
        
        Args:
            order: 基礎訂單物件
            
        Returns:
            IBOrder: IB 訂單或 None
        """
        try:
            if not order:
                logger.error("訂單物件不能為 None")
                return None

            action = "BUY" if order.action.lower() == "buy" else "SELL"
            
            # 根據訂單類型創建對應的 IB 訂單
            if order.order_type == OrderType.MARKET:
                return self.create_market_order(
                    action, order.quantity,
                    tif=self._convert_time_in_force(order.time_in_force)
                )
            elif order.order_type == OrderType.LIMIT:
                return self.create_limit_order(
                    action, order.quantity, order.price,
                    tif=self._convert_time_in_force(order.time_in_force)
                )
            elif order.order_type == OrderType.STOP:
                return self.create_stop_order(
                    action, order.quantity, order.stop_price,
                    tif=self._convert_time_in_force(order.time_in_force)
                )
            elif order.order_type == OrderType.STOP_LIMIT:
                return self.create_stop_limit_order(
                    action, order.quantity, order.stop_price, order.price,
                    tif=self._convert_time_in_force(order.time_in_force)
                )
            else:
                logger.error("不支援的訂單類型: %s", order.order_type)
                return None

        except Exception as e:
            logger.exception("從基礎訂單創建 IB 訂單失敗: %s", e)
            return None

    def _validate_basic_params(self, action: str, quantity: int) -> bool:
        """驗證基本訂單參數
        
        Args:
            action: 買賣方向
            quantity: 數量
            
        Returns:
            bool: 參數是否有效
        """
        try:
            if not action or action.upper() not in ['BUY', 'SELL']:
                logger.error("無效的買賣方向: %s", action)
                return False

            if quantity <= 0:
                logger.error("無效的數量: %d", quantity)
                return False

            return True

        except Exception as e:
            logger.exception("驗證基本參數時發生異常: %s", e)
            return False

    def _apply_order_params(self, ib_order: IBOrder, params: Dict[str, Any]) -> None:
        """應用訂單參數
        
        Args:
            ib_order: IB 訂單物件
            params: 參數字典
        """
        try:
            # 應用預設值
            for key, value in self._order_defaults.items():
                if hasattr(ib_order, key):
                    setattr(ib_order, key, value)

            # 應用自定義參數
            for key, value in params.items():
                if hasattr(ib_order, key):
                    setattr(ib_order, key, value)

        except Exception as e:
            logger.exception("應用訂單參數時發生異常: %s", e)

    def _convert_time_in_force(self, time_in_force: Optional[str]) -> str:
        """轉換時效設定
        
        Args:
            time_in_force: 時效設定
            
        Returns:
            str: IB 時效設定
        """
        try:
            if not time_in_force:
                return TimeInForce.DAY.value

            tif_mapping = {
                'day': TimeInForce.DAY.value,
                'gtc': TimeInForce.GOOD_TILL_CANCELLED.value,
                'ioc': TimeInForce.IMMEDIATE_OR_CANCEL.value,
                'fok': TimeInForce.FILL_OR_KILL.value,
            }

            return tif_mapping.get(time_in_force.lower(), TimeInForce.DAY.value)

        except Exception as e:
            logger.exception("轉換時效設定時發生異常: %s", e)
            return TimeInForce.DAY.value
