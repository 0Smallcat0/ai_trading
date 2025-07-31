"""訂單執行服務 (Order Execution Service)

此模組提供訂單執行的統一管理服務，包括：
- 訂單生成與驗證
- 訂單執行與追蹤
- 執行狀態監控
- 錯誤處理與重試
- 執行報告生成

符合 Phase 7.2 程式碼品質標準：
- Pylint ≥8.5/10
- 100% Google Style Docstring 覆蓋率
- 完整型別標註
- 統一錯誤處理模式
"""

import logging
import threading
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable

try:
    from src.core.trade_execution_brokers import TradeExecutionBrokerManager
    from src.execution.broker_base import OrderStatus, OrderType
except ImportError:
    # 測試環境下的 Mock 類別
    TradeExecutionBrokerManager = None
    OrderStatus = None
    OrderType = None

from .broker_connection_service import BrokerConnectionService


logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """執行狀態枚舉"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    ERROR = "error"


class OrderExecutionError(Exception):
    """訂單執行錯誤"""
    pass


class OrderRequest:
    """訂單請求類別

    Attributes:
        order_id: 訂單唯一識別碼
        symbol: 股票代號
        action: 交易動作 (buy/sell)
        quantity: 交易數量
        order_type: 訂單類型
        price: 價格 (限價單使用)
        stop_price: 停損價格 (停損單使用)
        time_in_force: 有效期限
        broker_name: 指定券商
        created_at: 創建時間
        metadata: 額外資訊
    """

    def __init__(
        self,
        symbol: str,
        action: str,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "DAY",
        broker_name: Optional[str] = None,
        **metadata
    ):
        """初始化訂單請求

        Args:
            symbol: 股票代號
            action: 交易動作 (buy/sell)
            quantity: 交易數量
            order_type: 訂單類型
            price: 價格 (限價單使用)
            stop_price: 停損價格 (停損單使用)
            time_in_force: 有效期限
            broker_name: 指定券商
            **metadata: 額外資訊
        """
        self.order_id = str(uuid.uuid4())
        self.symbol = symbol
        self.action = action.lower()
        self.quantity = quantity
        self.order_type = order_type
        self.price = price
        self.stop_price = stop_price
        self.time_in_force = time_in_force
        self.broker_name = broker_name
        self.created_at = datetime.now()
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式

        Returns:
            Dict[str, Any]: 訂單資訊字典
        """
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "action": self.action,
            "quantity": self.quantity,
            "order_type": self.order_type.value if isinstance(self.order_type, OrderType) else self.order_type,
            "price": self.price,
            "stop_price": self.stop_price,
            "time_in_force": self.time_in_force,
            "broker_name": self.broker_name,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }


class OrderExecutionService:
    """訂單執行服務

    提供統一的訂單執行管理介面，包括訂單驗證、執行、
    追蹤和狀態管理等功能。

    Attributes:
        _connection_service: 券商連接服務
        _trade_executor: 交易執行器
        _orders: 訂單記錄
        _execution_callbacks: 執行狀態回調函數列表
        _lock: 執行緒鎖
    """

    def __init__(self, connection_service: Optional[BrokerConnectionService] = None):
        """初始化訂單執行服務

        Args:
            connection_service: 券商連接服務實例
        """
        self._connection_service = connection_service or BrokerConnectionService()
        self._trade_executor = self._connection_service._trade_executor
        self._orders: Dict[str, Dict[str, Any]] = {}
        self._execution_callbacks: List[Callable[[str, ExecutionStatus, Dict[str, Any]], None]] = []
        self._lock = threading.Lock()

        logger.info("訂單執行服務初始化成功")

    def submit_order(self, order_request: OrderRequest) -> str:
        """提交訂單

        Args:
            order_request: 訂單請求

        Returns:
            str: 訂單ID

        Raises:
            OrderExecutionError: 訂單提交失敗時拋出
        """
        try:
            # 驗證訂單
            self._validate_order(order_request)

            # 選擇券商
            broker_name = order_request.broker_name or self._get_default_broker()

            # 檢查券商連接
            if not self._is_broker_available(broker_name):
                raise OrderExecutionError(f"券商 {broker_name} 不可用")

            # 記錄訂單
            order_info = {
                "request": order_request.to_dict(),
                "status": ExecutionStatus.PENDING,
                "broker_name": broker_name,
                "broker_order_id": None,
                "filled_quantity": 0,
                "avg_fill_price": 0.0,
                "commission": 0.0,
                "error_message": None,
                "submitted_at": None,
                "filled_at": None,
                "updates": []
            }

            with self._lock:
                self._orders[order_request.order_id] = order_info

            # 提交到券商
            self._submit_to_broker(order_request, broker_name)

            logger.info("訂單 %s 已提交", order_request.order_id)
            return order_request.order_id

        except Exception as e:
            logger.error("提交訂單失敗: %s", e)
            raise OrderExecutionError("訂單提交失敗") from e

    def cancel_order(self, order_id: str) -> bool:
        """
        取消訂單

        Args:
            order_id: 訂單ID

        Returns:
            bool: 取消是否成功

        Raises:
            OrderExecutionError: 取消失敗時拋出
        """
        try:
            with self._lock:
                if order_id not in self._orders:
                    raise OrderExecutionError(f"訂單 {order_id} 不存在")

                order_info = self._orders[order_id]

                # 檢查訂單狀態
                if order_info["status"] in [ExecutionStatus.FILLED, ExecutionStatus.CANCELLED]:
                    logger.warning("訂單 %s 已完成或已取消，無法取消", order_id)
                    return False

                broker_name = order_info["broker_name"]
                broker_order_id = order_info["broker_order_id"]

                if not broker_order_id:
                    # 訂單尚未提交到券商，直接標記為取消
                    self._update_order_status(order_id, ExecutionStatus.CANCELLED)
                    return True

            # 向券商發送取消請求
            broker = self._trade_executor.brokers.get(broker_name)
            if broker and hasattr(broker, 'cancel_order'):
                success = broker.cancel_order(broker_order_id)
                if success:
                    self._update_order_status(order_id, ExecutionStatus.CANCELLED)
                    logger.info("訂單 %s 已取消", order_id)
                else:
                    logger.error("取消訂單 %s 失敗", order_id)
                return success
            else:
                logger.error("券商 %s 不支援取消訂單功能", broker_name)
                return False

        except Exception as e:
            logger.error("取消訂單時發生錯誤: %s", e)
            raise OrderExecutionError("取消訂單失敗") from e

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        獲取訂單狀態

        Args:
            order_id: 訂單ID

        Returns:
            Dict[str, Any]: 訂單狀態資訊

        Raises:
            OrderExecutionError: 訂單不存在時拋出
        """
        with self._lock:
            if order_id not in self._orders:
                raise OrderExecutionError(f"訂單 {order_id} 不存在")

            return self._orders[order_id].copy()

    def get_orders(
        self,
        status: Optional[ExecutionStatus] = None,
        broker_name: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        獲取訂單列表

        Args:
            status: 篩選狀態
            broker_name: 篩選券商
            symbol: 篩選股票代號

        Returns:
            List[Dict[str, Any]]: 訂單列表
        """
        with self._lock:
            orders = []
            for order_info in self._orders.values():
                # 應用篩選條件
                if status and order_info["status"] != status:
                    continue
                if broker_name and order_info["broker_name"] != broker_name:
                    continue
                if symbol and order_info["request"]["symbol"] != symbol:
                    continue

                orders.append(order_info.copy())

            return orders

    def add_execution_callback(
        self,
        callback: Callable[[str, ExecutionStatus, Dict[str, Any]], None]
    ) -> None:
        """
        添加執行狀態回調函數

        Args:
            callback: 回調函數，接收訂單ID、狀態和訂單資訊
        """
        self._execution_callbacks.append(callback)

    def _validate_order(self, order_request: OrderRequest) -> None:
        """
        驗證訂單請求

        Args:
            order_request: 訂單請求

        Raises:
            OrderExecutionError: 驗證失敗時拋出
        """
        if not order_request.symbol:
            raise OrderExecutionError("股票代號不能為空")

        if order_request.action not in ["buy", "sell"]:
            raise OrderExecutionError("交易動作必須是 buy 或 sell")

        if order_request.quantity <= 0:
            raise OrderExecutionError("交易數量必須大於 0")

        if order_request.order_type == OrderType.LIMIT and not order_request.price:
            raise OrderExecutionError("限價單必須指定價格")

        if order_request.order_type == OrderType.STOP and not order_request.stop_price:
            raise OrderExecutionError("停損單必須指定停損價格")

    def _get_default_broker(self) -> str:
        """
        獲取預設券商

        Returns:
            str: 預設券商名稱
        """
        # 優先使用當前券商
        if hasattr(self._trade_executor, 'current_broker') and self._trade_executor.current_broker:
            for name, broker in self._trade_executor.brokers.items():
                if broker == self._trade_executor.current_broker:
                    return name

        # 否則使用模擬券商
        return "simulator"

    def _is_broker_available(self, broker_name: str) -> bool:
        """
        檢查券商是否可用

        Args:
            broker_name: 券商名稱

        Returns:
            bool: 是否可用
        """
        if broker_name not in self._trade_executor.brokers:
            return False

        # 檢查連接狀態
        status = self._connection_service.get_connection_status(broker_name)
        return status.get("status") == "connected"

    def _submit_to_broker(self, order_request: OrderRequest, broker_name: str) -> None:
        """
        提交訂單到券商

        Args:
            order_request: 訂單請求
            broker_name: 券商名稱
        """
        try:
            broker = self._trade_executor.brokers[broker_name]

            # 構建券商訂單
            broker_order = {
                "stock_id": order_request.symbol,
                "action": order_request.action,
                "quantity": order_request.quantity,
                "order_type": order_request.order_type,
                "price": order_request.price,
                "stop_price": order_request.stop_price,
                "time_in_force": order_request.time_in_force
            }

            # 提交訂單
            if hasattr(broker, 'place_order'):
                broker_order_id = broker.place_order(broker_order)

                # 更新訂單資訊
                with self._lock:
                    order_info = self._orders[order_request.order_id]
                    order_info["broker_order_id"] = broker_order_id
                    order_info["submitted_at"] = datetime.now()

                self._update_order_status(order_request.order_id, ExecutionStatus.SUBMITTED)

            else:
                raise OrderExecutionError(f"券商 {broker_name} 不支援下單功能")

        except Exception as e:
            self._update_order_status(
                order_request.order_id,
                ExecutionStatus.ERROR,
                error_message=str(e)
            )
            raise

    def _update_order_status(
        self,
        order_id: str,
        status: ExecutionStatus,
        **kwargs
    ) -> None:
        """
        更新訂單狀態

        Args:
            order_id: 訂單ID
            status: 新狀態
            **kwargs: 額外更新資訊
        """
        with self._lock:
            if order_id in self._orders:
                order_info = self._orders[order_id]
                old_status = order_info["status"]
                order_info["status"] = status

                # 更新額外資訊
                for key, value in kwargs.items():
                    order_info[key] = value

                # 記錄狀態變更
                order_info["updates"].append({
                    "timestamp": datetime.now().isoformat(),
                    "old_status": old_status.value if isinstance(old_status, ExecutionStatus) else old_status,
                    "new_status": status.value,
                    "details": kwargs
                })

                # 觸發回調
                for callback in self._execution_callbacks:
                    try:
                        callback(order_id, status, order_info.copy())
                    except Exception as e:
                        logger.error("執行狀態回調時發生錯誤: %s", e)
