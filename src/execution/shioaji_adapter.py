"""
永豐證券 API 適配器

此模組提供與永豐證券 API (Shioaji) 的連接和交易功能。
"""

import logging
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import shioaji as sj
    from shioaji.constant import (
        Action,
        OrderState,
        StockOrderType,
        StockPriceType,
        TFTOrderType,
    )

    SHIOAJI_AVAILABLE = True
except ImportError:
    SHIOAJI_AVAILABLE = False

from src.utils.utils import retry

from .broker_base import BrokerBase, Order, OrderStatus, OrderType

# 設定日誌
logger = logging.getLogger("execution.shioaji")


class ShioajiAdapter(BrokerBase):
    """永豐證券 API 適配器"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        account_id: Optional[str] = None,
        person_id: Optional[str] = None,
        ca_path: Optional[str] = None,
        cache_dir: str = "cache/shioaji",
        log_path: str = "logs/shioaji.log",
        **kwargs,
    ):
        """
        初始化永豐證券 API 適配器

        Args:
            api_key (str, optional): API 金鑰
            api_secret (str, optional): API 密鑰
            account_id (str, optional): 帳戶 ID
            person_id (str, optional): 身分證字號
            ca_path (str, optional): 憑證路徑
            cache_dir (str): 快取目錄
            log_path (str): 日誌路徑
            **kwargs: 其他參數
        """
        super().__init__(api_key, api_secret, account_id, **kwargs)
        if not SHIOAJI_AVAILABLE:
            raise ImportError("請先安裝 shioaji 套件：pip install shioaji")

        self.person_id = person_id or os.getenv("BROKER_PERSON_ID")
        self.ca_path = ca_path
        self.cache_dir = cache_dir
        self.log_path = log_path

        # 創建快取目錄
        os.makedirs(cache_dir, exist_ok=True)

        # 創建日誌目錄
        log_dir = os.path.dirname(log_path)
        os.makedirs(log_dir, exist_ok=True)

        # 初始化 Shioaji API
        self.api = sj.Shioaji(
            simulation=kwargs.get("simulation", False),
            log_path=log_path,
        )
        self.account = None
        self.subscribed_contracts = set()  # 已訂閱的合約集合

        # 訂單映射
        self.order_map = {}  # 訂單 ID 到 Shioaji 訂單的映射
        self.exchange_order_map = {}  # Shioaji 訂單 ID 到訂單 ID 的映射

        # 回調函數
        self.on_order_status = None
        self.on_quote_update = None

    def connect(self) -> bool:
        """
        連接永豐證券 API

        Returns:
            bool: 是否連接成功
        """
        if self.connected:
            logger.info("已經連接到永豐證券 API")
            return True

        try:
            # 檢查 API 金鑰和密鑰
            if not self.api_key or not self.api_secret:
                logger.error("未提供 API 金鑰或密鑰")
                return False

            # 登入
            self.api.login(
                self.api_key,
                self.api_secret,
                fetch_contract=True,
                contracts_cb=self._on_contracts_fetched,
            )

            # 等待合約載入完成
            timeout = 30  # 30 秒超時
            start_time = time.time()
            while (
                not hasattr(self.api, "Contracts")
                and time.time() - start_time < timeout
            ):
                time.sleep(0.5)

            if not hasattr(self.api, "Contracts"):
                logger.error("合約載入超時")
                return False

            # 設置憑證
            if self.ca_path and os.path.exists(self.ca_path):
                self.api.activate_ca(
                    ca_path=self.ca_path,
                    ca_passwd=self.person_id,
                    person_id=self.person_id,
                )

            # 選擇帳戶
            if self.account_id:
                self.account = self.api.get_account(self.account_id)
            else:
                accounts = self.api.list_accounts()
                if accounts:
                    self.account = accounts[0]
                    self.account_id = self.account.account_id
                else:
                    logger.error("找不到可用帳戶")
                    return False

            # 註冊回調函數
            self.api.set_order_callback(self._on_order_status)

            self.connected = True
            logger.info(f"已連接到永豐證券 API，帳戶: {self.account_id}")
            return True
        except Exception as e:
            logger.exception(f"連接永豐證券 API 失敗: {e}")
            return False

    def disconnect(self) -> bool:
        """
        斷開永豐證券 API 連接

        Returns:
            bool: 是否斷開成功
        """
        if not self.connected:
            logger.info("未連接到永豐證券 API")
            return True

        try:
            # 取消所有訂閱
            for contract_id in self.subscribed_contracts:
                try:
                    self.api.unsubscribe(contract_id, quote_type="tick")
                    self.api.unsubscribe(contract_id, quote_type="bidask")
                except Exception as e:
                    logger.warning(f"取消訂閱 {contract_id} 失敗: {e}")

            # 登出
            self.api.logout()

            self.connected = False
            logger.info("已斷開永豐證券 API 連接")
            return True
        except Exception as e:
            logger.exception(f"斷開永豐證券 API 連接失敗: {e}")
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
            logger.error("未連接到永豐證券 API")
            return None

        try:
            # 檢查帳戶
            if not self.account:
                logger.error("未選擇帳戶")
                return None

            # 生成訂單 ID
            if not order.order_id:
                order.order_id = str(uuid.uuid4())

            # 獲取合約
            contract = self._get_contract(order.stock_id)
            if not contract:
                logger.error(f"找不到合約: {order.stock_id}")
                return None

            # 轉換訂單類型
            price_type, order_type, time_in_force = self._convert_order_type(
                order.order_type
            )

            # 轉換買賣別
            action = Action.Buy if order.action.lower() == "buy" else Action.Sell

            # 下單
            sj_order = self.api.place_order(
                self.account,
                contract,
                price=order.price,
                quantity=order.quantity,
                action=action,
                price_type=price_type,
                order_type=order_type,
                order_cond=time_in_force,
            )

            if not sj_order:
                logger.error("下單失敗")
                return None

            # 更新訂單狀態
            order.status = OrderStatus.SUBMITTED
            order.updated_at = datetime.now()
            order.exchange_order_id = sj_order.order.id

            # 儲存訂單映射
            self.orders[order.order_id] = order
            self.order_map[order.order_id] = sj_order
            self.exchange_order_map[sj_order.order.id] = order.order_id

            logger.info(
                f"訂單已提交: {order.order_id}, 券商訂單 ID: {sj_order.order.id}"
            )
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
            logger.error("未連接到永豐證券 API")
            return False

        try:
            # 檢查訂單是否存在
            if order_id not in self.order_map:
                logger.error(f"訂單不存在: {order_id}")
                return False

            # 獲取 Shioaji 訂單
            sj_order = self.order_map[order_id]

            # 取消訂單
            self.api.cancel_order(self.account, sj_order)

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
        if order.status in [
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED,
        ]:
            return order

        # 如果訂單在 Shioaji 中，更新狀態
        if order_id in self.order_map:
            sj_order = self.order_map[order_id]
            self._update_order_status(order, sj_order)

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
            logger.error("未連接到永豐證券 API")
            return {}

        try:
            # 獲取庫存
            positions = {}
            inventory = self.api.list_positions(self.account)

            for position in inventory:
                stock_id = position.code
                quantity = int(position.quantity)
                avg_price = float(position.price)
                last_price = self._get_latest_price(stock_id)

                positions[stock_id] = {
                    "stock_id": stock_id,
                    "shares": quantity,
                    "avg_price": avg_price,
                    "cost": avg_price * quantity,
                    "current_price": last_price,
                    "value": (
                        last_price * quantity if last_price else avg_price * quantity
                    ),
                    "profit_loss": (
                        (last_price - avg_price) * quantity if last_price else 0
                    ),
                    "profit_loss_pct": (
                        (last_price / avg_price - 1) * 100
                        if last_price and avg_price
                        else 0
                    ),
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
            logger.error("未連接到永豐證券 API")
            return {}

        try:
            # 獲取帳戶餘額
            balance = self.api.account_balance(self.account)

            # 獲取持倉
            positions = self.get_positions()
            positions_value = sum(
                position.get("value", 0) for position in positions.values()
            )

            return {
                "account_id": self.account_id,
                "cash": float(balance.acc_balance),
                "buying_power": float(balance.buying_power),
                "positions_value": positions_value,
                "total_value": float(balance.acc_balance) + positions_value,
                "margin_used": float(balance.used_margin),
                "margin_available": float(balance.available_margin),
                "risk_level": balance.risk_level,
                "positions_count": len(positions),
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
            logger.error("未連接到永豐證券 API")
            return {}

        try:
            # 獲取合約
            contract = self._get_contract(stock_id)
            if not contract:
                logger.error(f"找不到合約: {stock_id}")
                return {}

            # 訂閱報價
            if stock_id not in self.subscribed_contracts:
                self.api.subscribe(
                    contract,
                    quote_type="tick",
                    version=sj.constant.QuoteVersion.v1,
                    intraday_odd=True,
                )
                self.api.subscribe(
                    contract,
                    quote_type="bidask",
                    version=sj.constant.QuoteVersion.v1,
                    intraday_odd=True,
                )
                self.subscribed_contracts.add(stock_id)

            # 獲取報價
            ticks = self.api.ticks(contract, timeout=0.5)
            if not ticks.empty:
                latest_tick = ticks.iloc[-1]
                return {
                    "stock_id": stock_id,
                    "price": float(latest_tick.close),
                    "change": float(latest_tick.close - latest_tick.open),
                    "change_pct": float(
                        (latest_tick.close / latest_tick.open - 1) * 100
                    ),
                    "volume": int(latest_tick.volume),
                    "total_volume": int(latest_tick.total_volume),
                    "tick_type": latest_tick.tick_type,
                    "timestamp": latest_tick.datetime.isoformat(),
                }

            # 如果沒有 tick 資料，嘗試獲取 bidask
            bidasks = self.api.bidask(contract, timeout=0.5)
            if not bidasks.empty:
                latest_bidask = bidasks.iloc[-1]
                return {
                    "stock_id": stock_id,
                    "bid": float(latest_bidask.bid_price),
                    "ask": float(latest_bidask.ask_price),
                    "bid_volume": int(latest_bidask.bid_volume),
                    "ask_volume": int(latest_bidask.ask_volume),
                    "timestamp": latest_bidask.datetime.isoformat(),
                }

            # 如果都沒有，嘗試獲取基本資料
            snapshots = self.api.snapshots([contract])
            if snapshots:
                snapshot = snapshots[0]
                return {
                    "stock_id": stock_id,
                    "price": float(snapshot.close),
                    "change": float(snapshot.change),
                    "change_pct": float(snapshot.change_rate),
                    "open": float(snapshot.open),
                    "high": float(snapshot.high),
                    "low": float(snapshot.low),
                    "volume": int(snapshot.total_volume),
                    "timestamp": snapshot.datetime.isoformat(),
                }

            return {}
        except Exception as e:
            logger.exception(f"獲取市場資料失敗: {e}")
            return {}

    def _get_contract(self, stock_id: str):
        """
        獲取合約

        Args:
            stock_id (str): 股票代號

        Returns:
            Contract: 合約物件或 None (如果找不到)
        """
        try:
            # 檢查是否為台股
            if stock_id.isdigit() or (len(stock_id) >= 4 and stock_id[:4].isdigit()):
                return self.api.Contracts.Stocks[stock_id]
            # 檢查是否為美股
            elif stock_id.upper() in self.api.Contracts.Stocks.US:
                return self.api.Contracts.Stocks.US[stock_id.upper()]
            # 檢查是否為港股
            elif stock_id.upper() in self.api.Contracts.Stocks.HK:
                return self.api.Contracts.Stocks.HK[stock_id.upper()]
            else:
                logger.error(f"找不到合約: {stock_id}")
                return None
        except Exception as e:
            logger.error(f"獲取合約失敗: {stock_id}, {e}")
            return None

    def _convert_order_type(self, order_type: OrderType):
        """
        轉換訂單類型

        Args:
            order_type (OrderType): 訂單類型

        Returns:
            tuple: (price_type, order_type, time_in_force)
        """
        if order_type == OrderType.MARKET:
            return StockPriceType.MKT, StockOrderType.ROD, TFTOrderType.ROD
        elif order_type == OrderType.LIMIT:
            return StockPriceType.LMT, StockOrderType.ROD, TFTOrderType.ROD
        elif order_type == OrderType.IOC:
            return StockPriceType.LMT, StockOrderType.IOC, TFTOrderType.IOC
        elif order_type == OrderType.FOK:
            return StockPriceType.LMT, StockOrderType.FOK, TFTOrderType.FOK
        else:
            return StockPriceType.LMT, StockOrderType.ROD, TFTOrderType.ROD

    def _convert_order_status(self, status: str) -> OrderStatus:
        """
        轉換訂單狀態

        Args:
            status (str): Shioaji 訂單狀態

        Returns:
            OrderStatus: 訂單狀態
        """
        status_map = {
            OrderState.PendingSubmit: OrderStatus.PENDING,
            OrderState.PreSubmitted: OrderStatus.PENDING,
            OrderState.Submitted: OrderStatus.SUBMITTED,
            OrderState.Filled: OrderStatus.FILLED,
            OrderState.Rejected: OrderStatus.REJECTED,
            OrderState.Cancelled: OrderStatus.CANCELLED,
            OrderState.Inactive: OrderStatus.EXPIRED,
            OrderState.PartFilled: OrderStatus.PARTIALLY_FILLED,
        }
        return status_map.get(status, OrderStatus.PENDING)

    def _update_order_status(self, order: Order, sj_order):
        """
        更新訂單狀態

        Args:
            order (Order): 訂單物件
            sj_order: Shioaji 訂單物件
        """
        # 更新狀態
        order.status = self._convert_order_status(sj_order.status.status)
        order.filled_quantity = int(sj_order.status.deal_quantity)
        order.filled_price = (
            float(sj_order.status.avg_price) if sj_order.status.avg_price else 0
        )
        order.updated_at = datetime.now()
        order.exchange_order_id = sj_order.order.id

        # 更新錯誤訊息
        if order.status == OrderStatus.REJECTED:
            order.error_message = sj_order.status.msg

    def _update_all_orders(self):
        """更新所有訂單狀態"""
        if not self.connected:
            return

        try:
            # 獲取所有訂單
            sj_orders = self.api.list_orders(self.account)

            # 更新訂單狀態
            for sj_order in sj_orders:
                # 檢查是否在映射中
                if sj_order.order.id in self.exchange_order_map:
                    order_id = self.exchange_order_map[sj_order.order.id]
                    order = self.orders.get(order_id)
                    if order:
                        self._update_order_status(order, sj_order)
        except Exception as e:
            logger.exception(f"更新訂單狀態失敗: {e}")

    def _get_latest_price(self, stock_id: str) -> Optional[float]:
        """
        獲取最新價格

        Args:
            stock_id (str): 股票代號

        Returns:
            float: 最新價格或 None (如果無法獲取)
        """
        try:
            # 獲取合約
            contract = self._get_contract(stock_id)
            if not contract:
                return None

            # 獲取快照
            snapshots = self.api.snapshots([contract])
            if snapshots:
                return float(snapshots[0].close)

            return None
        except Exception as e:
            logger.error(f"獲取最新價格失敗: {stock_id}, {e}")
            return None

    def _on_contracts_fetched(self, contracts):
        """
        合約載入完成回調

        Args:
            contracts: 合約物件
        """
        logger.info("合約載入完成")

    def _on_order_status(self, order_status):
        """
        訂單狀態變更回調

        Args:
            order_status: 訂單狀態物件
        """
        try:
            # 獲取訂單 ID
            exchange_order_id = order_status.order.id
            if exchange_order_id in self.exchange_order_map:
                order_id = self.exchange_order_map[exchange_order_id]
                order = self.orders.get(order_id)
                if order:
                    # 更新訂單狀態
                    old_status = order.status
                    self._update_order_status(order, order_status)

                    # 記錄狀態變更
                    logger.info(
                        f"訂單狀態變更: {order_id} {old_status.value} -> {order.status.value}"
                    )

                    # 調用回調函數
                    if self.on_order_status:
                        self.on_order_status(order)
        except Exception as e:
            logger.exception(f"處理訂單狀態變更失敗: {e}")
