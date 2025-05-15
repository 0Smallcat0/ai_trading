"""
富途證券 API 適配器

此模組提供與富途證券 API (Futu OpenAPI) 的連接和交易功能。
"""

import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import threading
import queue
import os
from pathlib import Path

try:
    from futu import (
        OpenQuoteContext,
        OpenHKTradeContext,
        OpenUSTradeContext,
        OpenCNTradeContext,
        TrdEnv,
        TrdSide,
        OrderType as FutuOrderType,
        OrderStatus as FutuOrderStatus,
        ModifyOrderOp,
        Market,
        RET_OK,
        RET_ERROR,
    )
    FUTU_AVAILABLE = True
except ImportError:
    FUTU_AVAILABLE = False

from .broker_base import BrokerBase, Order, OrderStatus, OrderType
from src.utils.utils import retry

# 設定日誌
logger = logging.getLogger("execution.futu")


class FutuAdapter(BrokerBase):
    """富途證券 API 適配器"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        account_id: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 11111,
        market: str = "HK",
        trade_env: str = "SIMULATE",
        unlock_password: Optional[str] = None,
        log_path: str = "logs/futu.log",
        **kwargs
    ):
        """
        初始化富途證券 API 適配器

        Args:
            api_key (str, optional): API 金鑰
            api_secret (str, optional): API 密鑰
            account_id (str, optional): 帳戶 ID
            host (str): 主機地址
            port (int): 端口
            market (str): 市場，可選 'HK', 'US', 'CN'
            trade_env (str): 交易環境，可選 'SIMULATE', 'REAL'
            unlock_password (str, optional): 解鎖密碼
            log_path (str): 日誌路徑
            **kwargs: 其他參數
        """
        super().__init__(api_key, api_secret, account_id, **kwargs)
        if not FUTU_AVAILABLE:
            raise ImportError("請先安裝 futu-api 套件：pip install futu-api")

        self.host = host
        self.port = port
        self.market = market
        self.trade_env = TrdEnv.SIMULATE if trade_env.upper() == "SIMULATE" else TrdEnv.REAL
        self.unlock_password = unlock_password
        self.log_path = log_path

        # 創建日誌目錄
        log_dir = os.path.dirname(log_path)
        os.makedirs(log_dir, exist_ok=True)

        # 初始化 Futu API
        self.quote_ctx = None
        self.trade_ctx = None
        self.subscribed_symbols = set()  # 已訂閱的股票集合

        # 訂單映射
        self.order_map = {}  # 訂單 ID 到 Futu 訂單 ID 的映射
        self.exchange_order_map = {}  # Futu 訂單 ID 到訂單 ID 的映射

        # 回調函數
        self.on_order_status = None
        self.on_quote_update = None

    def connect(self) -> bool:
        """
        連接富途證券 API

        Returns:
            bool: 是否連接成功
        """
        if self.connected:
            logger.info("已經連接到富途證券 API")
            return True

        try:
            # 創建行情上下文
            self.quote_ctx = OpenQuoteContext(host=self.host, port=self.port)

            # 創建交易上下文
            if self.market == "HK":
                self.trade_ctx = OpenHKTradeContext(host=self.host, port=self.port)
            elif self.market == "US":
                self.trade_ctx = OpenUSTradeContext(host=self.host, port=self.port)
            elif self.market == "CN":
                self.trade_ctx = OpenCNTradeContext(host=self.host, port=self.port)
            else:
                logger.error(f"不支援的市場: {self.market}")
                return False

            # 設置環境
            self.trade_ctx.set_trade_env(self.trade_env)

            # 解鎖交易
            if self.trade_env == TrdEnv.REAL and self.unlock_password:
                ret, data = self.trade_ctx.unlock_trade(password=self.unlock_password)
                if ret != RET_OK:
                    logger.error(f"解鎖交易失敗: {data}")
                    return False

            # 註冊回調函數
            self.trade_ctx.set_handler(self._on_order_status)

            self.connected = True
            logger.info(f"已連接到富途證券 API，市場: {self.market}")
            return True
        except Exception as e:
            logger.exception(f"連接富途證券 API 失敗: {e}")
            return False

    def disconnect(self) -> bool:
        """
        斷開富途證券 API 連接

        Returns:
            bool: 是否斷開成功
        """
        if not self.connected:
            logger.info("未連接到富途證券 API")
            return True

        try:
            # 關閉行情上下文
            if self.quote_ctx:
                self.quote_ctx.close()
                self.quote_ctx = None

            # 關閉交易上下文
            if self.trade_ctx:
                self.trade_ctx.close()
                self.trade_ctx = None

            self.connected = False
            logger.info("已斷開富途證券 API 連接")
            return True
        except Exception as e:
            logger.exception(f"斷開富途證券 API 連接失敗: {e}")
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
            logger.error("未連接到富途證券 API")
            return None

        try:
            # 生成訂單 ID
            if not order.order_id:
                order.order_id = str(uuid.uuid4())

            # 轉換訂單類型
            futu_order_type = self._convert_order_type(order.order_type)

            # 轉換買賣別
            trd_side = TrdSide.BUY if order.action.lower() == "buy" else TrdSide.SELL

            # 下單
            ret, data = self.trade_ctx.place_order(
                price=order.price,
                qty=order.quantity,
                code=order.stock_id,
                trd_side=trd_side,
                order_type=futu_order_type,
                adjust_limit=0,
            )

            if ret != RET_OK:
                logger.error(f"下單失敗: {data}")
                return None

            # 獲取 Futu 訂單 ID
            futu_order_id = data["order_id"][0]

            # 更新訂單狀態
            order.status = OrderStatus.SUBMITTED
            order.updated_at = datetime.now()
            order.exchange_order_id = futu_order_id

            # 儲存訂單映射
            self.orders[order.order_id] = order
            self.order_map[order.order_id] = futu_order_id
            self.exchange_order_map[futu_order_id] = order.order_id

            logger.info(f"訂單已提交: {order.order_id}, 富途訂單 ID: {futu_order_id}")
            return order.order_id
        except Exception as e:
            logger.exception(f"下單失敗: {e}")
            return None

    def cancel_order(self, order_id: str) -> bool:
        """
        取消訂單

        Args:
            order_id (str): 訂單 ID

        Returns:
            bool: 是否取消成功
        """
        if not self.connected:
            logger.error("未連接到富途證券 API")
            return False

        try:
            # 檢查訂單是否存在
            if order_id not in self.order_map:
                logger.error(f"訂單不存在: {order_id}")
                return False

            # 獲取 Futu 訂單 ID
            futu_order_id = self.order_map[order_id]

            # 取消訂單
            ret, data = self.trade_ctx.modify_order(
                modify_order_op=ModifyOrderOp.CANCEL,
                order_id=futu_order_id,
                qty=0,
                price=0,
            )

            if ret != RET_OK:
                logger.error(f"取消訂單失敗: {data}")
                return False

            logger.info(f"訂單已取消: {order_id}")
            return True
        except Exception as e:
            logger.exception(f"取消訂單失敗: {e}")
            return False

    def get_order(self, order_id: str) -> Optional[Order]:
        """
        獲取訂單資訊

        Args:
            order_id (str): 訂單 ID

        Returns:
            Order: 訂單物件或 None (如果訂單不存在)
        """
        # 檢查訂單是否存在
        if order_id not in self.orders:
            return None

        # 獲取訂單
        order = self.orders[order_id]

        # 如果訂單已經完成，直接返回
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED]:
            return order

        # 如果訂單在 Futu 中，更新狀態
        if order_id in self.order_map:
            futu_order_id = self.order_map[order_id]
            self._update_order_status_by_id(futu_order_id)

        return order

    def get_orders(self, status: Optional[OrderStatus] = None) -> List[Order]:
        """
        獲取訂單列表

        Args:
            status (OrderStatus, optional): 訂單狀態

        Returns:
            List[Order]: 訂單列表
        """
        # 更新所有訂單狀態
        self._update_all_orders()

        # 過濾訂單
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
        if not self.connected:
            logger.error("未連接到富途證券 API")
            return {}

        try:
            # 獲取持倉
            ret, data = self.trade_ctx.position_list_query()
            if ret != RET_OK:
                logger.error(f"獲取持倉失敗: {data}")
                return {}

            # 處理持倉資料
            positions = {}
            for _, row in data.iterrows():
                stock_id = row["code"]
                quantity = int(row["qty"])
                avg_price = float(row["cost_price"])
                market_value = float(row["market_val"])
                pl_ratio = float(row["pl_ratio"])
                pl_val = float(row["pl_val"])

                positions[stock_id] = {
                    "stock_id": stock_id,
                    "shares": quantity,
                    "avg_price": avg_price,
                    "cost": avg_price * quantity,
                    "current_price": market_value / quantity if quantity > 0 else 0,
                    "value": market_value,
                    "profit_loss": pl_val,
                    "profit_loss_pct": pl_ratio * 100,
                }

            return positions
        except Exception as e:
            logger.exception(f"獲取持倉資訊失敗: {e}")
            return {}

    def get_account_info(self) -> Dict[str, Any]:
        """
        獲取帳戶資訊

        Returns:
            Dict[str, Any]: 帳戶資訊
        """
        if not self.connected:
            logger.error("未連接到富途證券 API")
            return {}

        try:
            # 獲取帳戶資訊
            ret, data = self.trade_ctx.accinfo_query()
            if ret != RET_OK:
                logger.error(f"獲取帳戶資訊失敗: {data}")
                return {}

            # 處理帳戶資料
            account_info = data.iloc[0].to_dict()
            return {
                "account_id": self.account_id,
                "cash": float(account_info["cash"]),
                "total_assets": float(account_info["total_assets"]),
                "market_value": float(account_info["market_val"]),
                "buying_power": float(account_info["power"]),
                "currency": account_info["currency"],
            }
        except Exception as e:
            logger.exception(f"獲取帳戶資訊失敗: {e}")
            return {}

    def get_market_data(self, stock_id: str) -> Dict[str, Any]:
        """
        獲取市場資料

        Args:
            stock_id (str): 股票代號

        Returns:
            Dict[str, Any]: 市場資料
        """
        if not self.connected:
            logger.error("未連接到富途證券 API")
            return {}

        try:
            # 訂閱股票
            if stock_id not in self.subscribed_symbols:
                ret, data = self.quote_ctx.subscribe(stock_id, ["QUOTE", "TICKER", "ORDER_BOOK"])
                if ret != RET_OK:
                    logger.error(f"訂閱股票失敗: {data}")
                else:
                    self.subscribed_symbols.add(stock_id)

            # 獲取報價
            ret, data = self.quote_ctx.get_market_snapshot([stock_id])
            if ret != RET_OK:
                logger.error(f"獲取市場快照失敗: {data}")
                return {}

            # 處理報價資料
            snapshot = data.iloc[0].to_dict()
            return {
                "stock_id": stock_id,
                "price": float(snapshot["last_price"]),
                "open": float(snapshot["open_price"]),
                "high": float(snapshot["high_price"]),
                "low": float(snapshot["low_price"]),
                "volume": int(snapshot["volume"]),
                "turnover": float(snapshot["turnover"]),
                "timestamp": snapshot["update_time"],
                "bid": float(snapshot["bid_price"]),
                "ask": float(snapshot["ask_price"]),
                "bid_volume": int(snapshot["bid_vol"]),
                "ask_volume": int(snapshot["ask_vol"]),
            }
        except Exception as e:
            logger.exception(f"獲取市場資料失敗: {e}")
            return {}

    def _convert_order_type(self, order_type: OrderType) -> FutuOrderType:
        """
        轉換訂單類型

        Args:
            order_type (OrderType): 訂單類型

        Returns:
            FutuOrderType: Futu 訂單類型
        """
        if order_type == OrderType.MARKET:
            return FutuOrderType.MARKET
        elif order_type == OrderType.LIMIT:
            return FutuOrderType.NORMAL
        elif order_type == OrderType.STOP:
            return FutuOrderType.STOP
        elif order_type == OrderType.STOP_LIMIT:
            return FutuOrderType.STOP_LIMIT
        else:
            return FutuOrderType.NORMAL

    def _convert_order_status(self, status: str) -> OrderStatus:
        """
        轉換訂單狀態

        Args:
            status (str): Futu 訂單狀態

        Returns:
            OrderStatus: 訂單狀態
        """
        status_map = {
            FutuOrderStatus.NONE: OrderStatus.PENDING,
            FutuOrderStatus.WAITING_SUBMIT: OrderStatus.PENDING,
            FutuOrderStatus.SUBMITTING: OrderStatus.PENDING,
            FutuOrderStatus.SUBMITTED: OrderStatus.SUBMITTED,
            FutuOrderStatus.FILLED_PART: OrderStatus.PARTIALLY_FILLED,
            FutuOrderStatus.FILLED_ALL: OrderStatus.FILLED,
            FutuOrderStatus.CANCELLED_PART: OrderStatus.PARTIALLY_FILLED,
            FutuOrderStatus.CANCELLED_ALL: OrderStatus.CANCELLED,
            FutuOrderStatus.FAILED: OrderStatus.REJECTED,
            FutuOrderStatus.DISABLED: OrderStatus.REJECTED,
            FutuOrderStatus.DELETED: OrderStatus.CANCELLED,
        }
        return status_map.get(status, OrderStatus.PENDING)

    def _update_order_status_by_id(self, futu_order_id: str):
        """
        更新訂單狀態

        Args:
            futu_order_id (str): Futu 訂單 ID
        """
        try:
            # 獲取訂單資訊
            ret, data = self.trade_ctx.order_list_query(order_id=futu_order_id)
            if ret != RET_OK:
                logger.error(f"獲取訂單資訊失敗: {data}")
                return

            # 檢查是否有資料
            if data.empty:
                logger.error(f"找不到訂單: {futu_order_id}")
                return

            # 獲取訂單資訊
            order_info = data.iloc[0].to_dict()

            # 檢查是否在映射中
            if futu_order_id in self.exchange_order_map:
                order_id = self.exchange_order_map[futu_order_id]
                order = self.orders.get(order_id)
                if order:
                    # 更新訂單狀態
                    order.status = self._convert_order_status(order_info["status"])
                    order.filled_quantity = int(order_info["dealt_qty"])
                    order.filled_price = float(order_info["dealt_avg_price"]) if order_info["dealt_avg_price"] > 0 else 0
                    order.updated_at = datetime.now()
                    order.exchange_order_id = futu_order_id

                    # 更新錯誤訊息
                    if order.status == OrderStatus.REJECTED:
                        order.error_message = order_info["remark"]
        except Exception as e:
            logger.exception(f"更新訂單狀態失敗: {e}")

    def _update_all_orders(self):
        """更新所有訂單狀態"""
        if not self.connected:
            return

        try:
            # 獲取所有訂單
            ret, data = self.trade_ctx.order_list_query()
            if ret != RET_OK:
                logger.error(f"獲取訂單列表失敗: {data}")
                return

            # 更新訂單狀態
            for _, row in data.iterrows():
                futu_order_id = row["order_id"]
                # 檢查是否在映射中
                if futu_order_id in self.exchange_order_map:
                    order_id = self.exchange_order_map[futu_order_id]
                    order = self.orders.get(order_id)
                    if order:
                        # 更新訂單狀態
                        order.status = self._convert_order_status(row["status"])
                        order.filled_quantity = int(row["dealt_qty"])
                        order.filled_price = float(row["dealt_avg_price"]) if row["dealt_avg_price"] > 0 else 0
                        order.updated_at = datetime.now()
                        order.exchange_order_id = futu_order_id

                        # 更新錯誤訊息
                        if order.status == OrderStatus.REJECTED:
                            order.error_message = row["remark"]
        except Exception as e:
            logger.exception(f"更新訂單狀態失敗: {e}")

    def _on_order_status(self, data):
        """
        訂單狀態變更回調

        Args:
            data: 訂單狀態資料
        """
        try:
            # 獲取訂單 ID
            futu_order_id = data["order_id"]
            if futu_order_id in self.exchange_order_map:
                order_id = self.exchange_order_map[futu_order_id]
                # 更新訂單狀態
                self._update_order_status_by_id(futu_order_id)
                # 獲取訂單
                order = self.orders.get(order_id)
                if order and self.on_order_status:
                    # 調用回調函數
                    self.on_order_status(order)
        except Exception as e:
            logger.exception(f"處理訂單狀態變更失敗: {e}")
