"""永豐證券 API 適配器

此模組提供與永豐證券 API (Shioaji) 的連接和交易功能。
"""

import logging
import os
import threading
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
        **kwargs,
    ):
        """初始化永豐證券 API 適配器

        Args:
            api_key (str, optional): API 金鑰
            api_secret (str, optional): API 密鑰
            account_id (str, optional): 帳戶 ID
            person_id (str, optional): 身分證字號
            ca_path (str, optional): 憑證路徑
            **kwargs: 其他參數，包含 cache_dir 和 log_path
        """
        super().__init__(api_key, api_secret, account_id, **kwargs)
        if not SHIOAJI_AVAILABLE:
            raise ImportError("請先安裝 shioaji 套件：pip install shioaji")

        self.person_id = person_id or os.getenv("BROKER_PERSON_ID")
        self.ca_path = ca_path
        self.cache_dir = kwargs.get("cache_dir", "cache/shioaji")
        self.log_path = kwargs.get("log_path", "logs/shioaji.log")

        # 創建快取目錄
        os.makedirs(self.cache_dir, exist_ok=True)

        # 創建日誌目錄
        log_dir = os.path.dirname(self.log_path)
        os.makedirs(log_dir, exist_ok=True)

        # 初始化 Shioaji API
        self.api = sj.Shioaji(
            simulation=kwargs.get("simulation", False),
            log_path=self.log_path,
        )
        self.account = None
        self.subscribed_contracts = set()  # 已訂閱的合約集合

        # 訂單映射
        self.order_map = {}  # 訂單 ID 到 Shioaji 訂單的映射
        self.exchange_order_map = {}  # Shioaji 訂單 ID 到訂單 ID 的映射

        # 回調函數
        self.on_order_status = None
        self.on_quote_update = None
        self.on_connection_status = None

        # 連接監控
        self.last_heartbeat = None
        self.connection_errors = 0
        self.max_connection_errors = 5
        self.reconnect_delay = 5  # 秒

        # 心跳檢測
        self._heartbeat_thread = None
        self._heartbeat_running = False

    def connect(self) -> bool:
        """連接永豐證券 API

        Returns:
            bool: 是否連接成功
        """
        if self.connected:
            logger.info("已經連接到永豐證券 API")
            return True

        try:
            if not self._validate_credentials():
                return False

            if not self._perform_login():
                return False

            if not self._setup_account():
                return False

            self._finalize_connection()
            return True

        except Exception as e:
            logger.exception("連接永豐證券 API 失敗: %s", e)
            self.connection_errors += 1
            self._notify_connection_status("error", f"連接失敗: {e}")
            return False

    def _validate_credentials(self) -> bool:
        """驗證 API 憑證"""
        if not self.api_key or not self.api_secret:
            logger.error("未提供 API 金鑰或密鑰")
            return False
        return True

    def _perform_login(self) -> bool:
        """執行登入並等待合約載入"""
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
        return True

    def _setup_account(self) -> bool:
        """設置帳戶"""
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
        return True

    def _finalize_connection(self):
        """完成連接設置"""
        # 註冊回調函數
        self.api.set_order_callback(self._on_order_status)

        self.connected = True
        self.connection_errors = 0
        self.last_heartbeat = datetime.now()

        # 啟動心跳檢測
        self._start_heartbeat()

        logger.info("已連接到永豐證券 API，帳戶: %s", self.account_id)
        self._notify_connection_status("connected", "連接成功")

    def _notify_connection_status(self, status: str, message: str):
        """通知連接狀態變更"""
        if self.on_connection_status and callable(self.on_connection_status):
            self.on_connection_status(status, message)

    def disconnect(self) -> bool:
        """斷開永豐證券 API 連接

        Returns:
            bool: 是否斷開成功
        """
        if not self.connected:
            logger.info("未連接到永豐證券 API")
            return True

        try:
            # 停止心跳檢測
            self._stop_heartbeat()

            # 取消所有訂閱
            for contract_id in self.subscribed_contracts:
                try:
                    self.api.unsubscribe(contract_id, quote_type="tick")
                    self.api.unsubscribe(contract_id, quote_type="bidask")
                except Exception as e:
                    logger.warning("取消訂閱 %s 失敗: %s", contract_id, e)

            # 登出
            self.api.logout()

            self.connected = False
            logger.info("已斷開永豐證券 API 連接")

            # 通知連接狀態變更
            if self.on_connection_status and callable(self.on_connection_status):
                self.on_connection_status("disconnected", "連接已斷開")

            return True
        except Exception as e:
            logger.exception("斷開永豐證券 API 連接失敗: %s", e)
            return False

    @retry(max_retries=3)
    def place_order(self, order: Order) -> Optional[str]:
        """下單

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
                logger.error("找不到合約: %s", order.stock_id)
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
                "訂單已提交: %s, 券商訂單 ID: %s", order.order_id, sj_order.order.id
            )
            return order.order_id
        except Exception as e:
            logger.exception("下單失敗: %s", e)
            return None

    def cancel_order(self, order_id: str) -> bool:
        """取消訂單

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
                logger.error("訂單不存在: %s", order_id)
                return False

            # 獲取 Shioaji 訂單
            sj_order = self.order_map[order_id]

            # 取消訂單
            self.api.cancel_order(self.account, sj_order)

            logger.info("訂單已取消: %s", order_id)
            return True
        except Exception as e:
            logger.exception("取消訂單失敗: %s", e)
            return False

    def get_order(self, order_id: str) -> Optional[Order]:
        """獲取訂單資訊

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
        """獲取訂單列表

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

        return [order for order in self.orders.values() if order.status == status]

    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """獲取持倉資訊

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
            logger.exception("獲取持倉資訊失敗: %s", e)
            return {}

    def get_account_info(self) -> Dict[str, Any]:
        """獲取帳戶資訊

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
            logger.exception("獲取帳戶資訊失敗: %s", e)
            return {}

    def get_market_data(self, stock_id: str) -> Dict[str, Any]:
        """獲取市場資料

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
                logger.error("找不到合約: %s", stock_id)
                return {}

            # 訂閱報價
            self._subscribe_market_data(stock_id, contract)

            # 嘗試獲取不同類型的市場資料
            market_data = (
                self._get_tick_data(stock_id, contract) or
                self._get_bidask_data(stock_id, contract) or
                self._get_snapshot_data(stock_id, contract)
            )

            return market_data or {}

        except Exception as e:
            logger.exception("獲取市場資料失敗: %s", e)
            return {}

    def _subscribe_market_data(self, stock_id: str, contract):
        """訂閱市場資料"""
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

    def _get_tick_data(self, stock_id: str, contract) -> Optional[Dict[str, Any]]:
        """獲取 tick 資料"""
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
        return None

    def _get_bidask_data(self, stock_id: str, contract) -> Optional[Dict[str, Any]]:
        """獲取買賣報價資料"""
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
        return None

    def _get_snapshot_data(self, stock_id: str, contract) -> Optional[Dict[str, Any]]:
        """獲取快照資料"""
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
        return None

    def _get_contract(self, stock_id: str):
        """獲取合約

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
            if stock_id.upper() in self.api.Contracts.Stocks.US:
                return self.api.Contracts.Stocks.US[stock_id.upper()]
            # 檢查是否為港股
            if stock_id.upper() in self.api.Contracts.Stocks.HK:
                return self.api.Contracts.Stocks.HK[stock_id.upper()]

            logger.error("找不到合約: %s", stock_id)
            return None
        except Exception as e:
            logger.error("獲取合約失敗: %s, %s", stock_id, e)
            return None

    def _convert_order_type(self, order_type: OrderType):
        """轉換訂單類型

        Args:
            order_type (OrderType): 訂單類型

        Returns:
            tuple: (price_type, order_type, time_in_force)
        """
        if order_type == OrderType.MARKET:
            return StockPriceType.MKT, StockOrderType.ROD, TFTOrderType.ROD
        if order_type == OrderType.LIMIT:
            return StockPriceType.LMT, StockOrderType.ROD, TFTOrderType.ROD
        if order_type == OrderType.IOC:
            return StockPriceType.LMT, StockOrderType.IOC, TFTOrderType.IOC
        if order_type == OrderType.FOK:
            return StockPriceType.LMT, StockOrderType.FOK, TFTOrderType.FOK

        return StockPriceType.LMT, StockOrderType.ROD, TFTOrderType.ROD

    def _convert_order_status(self, status: str) -> OrderStatus:
        """轉換訂單狀態

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
        """更新訂單狀態

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
            logger.exception("更新訂單狀態失敗: %s", e)

    def _get_latest_price(self, stock_id: str) -> Optional[float]:
        """獲取最新價格

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
            logger.error("獲取最新價格失敗: %s, %s", stock_id, e)
            return None

    def _on_contracts_fetched(self, contracts):  # pylint: disable=unused-argument
        """合約載入完成回調

        Args:
            contracts: 合約物件
        """
        logger.info("合約載入完成")

    def _on_order_status(self, order_status):
        """訂單狀態變更回調

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
                        "訂單狀態變更: %s %s -> %s",
                        order_id, old_status.value, order.status.value
                    )

                    # 調用回調函數
                    if self.on_order_status and callable(self.on_order_status):
                        self.on_order_status(order)
        except Exception as e:
            logger.exception("處理訂單狀態變更失敗: %s", e)

    def _start_heartbeat(self):
        """啟動心跳檢測"""
        if self._heartbeat_running:
            return

        self._heartbeat_running = True
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name="ShioajiHeartbeat"
        )
        self._heartbeat_thread.start()
        logger.info("永豐證券心跳檢測已啟動")

    def _stop_heartbeat(self):
        """停止心跳檢測"""
        self._heartbeat_running = False
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=5)
        logger.info("永豐證券心跳檢測已停止")

    def _heartbeat_loop(self):
        """心跳檢測循環"""
        while self._heartbeat_running:
            try:
                if self.connected:
                    # 嘗試獲取帳戶資訊作為心跳檢測
                    try:
                        if self.account:
                            self.api.account_balance(self.account)
                            self.last_heartbeat = datetime.now()
                            self.connection_errors = 0
                    except Exception as e:
                        logger.warning("心跳檢測失敗: %s", e)
                        self.connection_errors += 1

                        # 如果連續錯誤次數過多，嘗試重連
                        if self.connection_errors >= self.max_connection_errors:
                            logger.error("連續心跳檢測失敗，嘗試重連")
                            self._attempt_reconnect()

                time.sleep(30)  # 30 秒檢測一次

            except Exception as e:
                logger.exception("心跳檢測循環錯誤: %s", e)
                time.sleep(5)

    def _attempt_reconnect(self):
        """嘗試重連"""
        try:
            logger.info("開始嘗試重連永豐證券 API")

            # 通知連接狀態變更
            if self.on_connection_status and callable(self.on_connection_status):
                self.on_connection_status("reconnecting", "正在重連")

            # 先斷開連接
            try:
                self.disconnect()
            except Exception as e:
                logger.warning("斷開連接時發生錯誤: %s", e)

            # 等待一段時間
            time.sleep(self.reconnect_delay)

            # 嘗試重新連接
            if self.connect():
                logger.info("永豐證券 API 重連成功")
                return True

            logger.error("永豐證券 API 重連失敗")
            return False

        except Exception as e:
            logger.exception("重連過程中發生錯誤: %s", e)
            return False

    def get_connection_info(self) -> Dict[str, Any]:
        """獲取連接資訊

        Returns:
            Dict[str, Any]: 連接資訊
        """
        return {
            "connected": self.connected,
            "last_heartbeat": (
                self.last_heartbeat.isoformat() if self.last_heartbeat else None
            ),
            "connection_errors": self.connection_errors,
            "max_connection_errors": self.max_connection_errors,
            "account_id": self.account_id,
            "subscribed_contracts": len(self.subscribed_contracts),
        }

    def force_reconnect(self) -> bool:
        """強制重連

        Returns:
            bool: 是否重連成功
        """
        logger.info("強制重連永豐證券 API")
        return self._attempt_reconnect()
