"""
訂單管理模組

此模組負責管理訂單的生命週期，包括：
- 訂單創建與提交
- 訂單狀態追蹤
- 部分成交處理
- 訂單取消與修改
- 訂單重試機制
"""

import logging
import time
import threading
import queue
from typing import Dict, List, Optional, Callable, Any, Union
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

from .broker_base import BrokerBase, Order, OrderStatus, OrderType
from src.utils.utils import retry

# 設定日誌
logger = logging.getLogger("execution.order_manager")


class OrderManager:
    """訂單管理器，負責管理訂單的生命週期"""

    def __init__(
        self,
        broker: BrokerBase,
        order_log_dir: str = "logs/orders",
        max_retry: int = 3,
        retry_interval: int = 5,
        auto_reconnect: bool = True,
    ):
        """
        初始化訂單管理器

        Args:
            broker (BrokerBase): 券商 API 適配器
            order_log_dir (str): 訂單日誌目錄
            max_retry (int): 最大重試次數
            retry_interval (int): 重試間隔（秒）
            auto_reconnect (bool): 是否自動重連
        """
        self.broker = broker
        self.order_log_dir = order_log_dir
        self.max_retry = max_retry
        self.retry_interval = retry_interval
        self.auto_reconnect = auto_reconnect

        # 創建訂單日誌目錄
        os.makedirs(order_log_dir, exist_ok=True)

        # 訂單隊列
        self.order_queue = queue.Queue()
        self.pending_orders = {}  # 等待中的訂單，key 為訂單 ID
        self.completed_orders = {}  # 已完成的訂單，key 為訂單 ID

        # 訂單處理線程
        self.order_thread = None
        self.running = False

        # 訂單狀態更新線程
        self.status_thread = None

        # 回調函數
        self.on_order_status_change = None
        self.on_order_filled = None
        self.on_order_rejected = None

    def start(self):
        """啟動訂單管理器"""
        if self.running:
            logger.warning("訂單管理器已經在運行中")
            return

        # 連接券商 API
        if not self.broker.connected:
            if not self.broker.connect():
                logger.error("無法連接券商 API，訂單管理器啟動失敗")
                return False

        # 啟動訂單處理線程
        self.running = True
        self.order_thread = threading.Thread(target=self._process_orders)
        self.order_thread.daemon = True
        self.order_thread.start()

        # 啟動訂單狀態更新線程
        self.status_thread = threading.Thread(target=self._update_order_status)
        self.status_thread.daemon = True
        self.status_thread.start()

        logger.info("訂單管理器已啟動")
        return True

    def stop(self):
        """停止訂單管理器"""
        if not self.running:
            logger.warning("訂單管理器未運行")
            return

        self.running = False
        if self.order_thread:
            self.order_thread.join(timeout=5)
        if self.status_thread:
            self.status_thread.join(timeout=5)

        # 斷開券商 API 連接
        if self.broker.connected:
            self.broker.disconnect()

        logger.info("訂單管理器已停止")

    def submit_order(self, order: Union[Order, Dict[str, Any]]) -> Optional[str]:
        """
        提交訂單

        Args:
            order (Union[Order, Dict[str, Any]]): 訂單物件或訂單字典

        Returns:
            str: 訂單 ID 或 None (如果提交失敗)
        """
        # 如果是字典，則創建訂單物件
        if isinstance(order, dict):
            order = Order(
                stock_id=order["stock_id"],
                action=order["action"],
                quantity=order["quantity"],
                order_type=OrderType(order.get("order_type", "market")),
                price=order.get("price"),
                stop_price=order.get("stop_price"),
                time_in_force=order.get("time_in_force", "day"),
            )

        # 將訂單加入隊列
        self.order_queue.put(order)
        logger.info(f"訂單已加入隊列: {order}")

        return order.order_id

    def cancel_order(self, order_id: str) -> bool:
        """
        取消訂單

        Args:
            order_id (str): 訂單 ID

        Returns:
            bool: 是否取消成功
        """
        # 檢查訂單是否在等待中
        if order_id in self.pending_orders:
            order = self.pending_orders[order_id]
            # 如果訂單尚未提交，則直接從隊列中移除
            if order.status == OrderStatus.PENDING:
                self.pending_orders.pop(order_id)
                logger.info(f"訂單已從隊列中移除: {order_id}")
                return True

        # 嘗試通過券商 API 取消訂單
        result = self.broker.cancel_order(order_id)
        if result:
            logger.info(f"訂單已取消: {order_id}")
        else:
            logger.error(f"取消訂單失敗: {order_id}")
        return result

    def get_order(self, order_id: str) -> Optional[Order]:
        """
        獲取訂單資訊

        Args:
            order_id (str): 訂單 ID

        Returns:
            Order: 訂單物件或 None (如果訂單不存在)
        """
        # 檢查訂單是否在等待中
        if order_id in self.pending_orders:
            return self.pending_orders[order_id]

        # 檢查訂單是否已完成
        if order_id in self.completed_orders:
            return self.completed_orders[order_id]

        # 嘗試通過券商 API 獲取訂單
        return self.broker.get_order(order_id)

    def get_orders(self, status: Optional[OrderStatus] = None) -> List[Order]:
        """
        獲取訂單列表

        Args:
            status (OrderStatus, optional): 訂單狀態

        Returns:
            List[Order]: 訂單列表
        """
        orders = []

        # 獲取等待中的訂單
        for order in self.pending_orders.values():
            if status is None or order.status == status:
                orders.append(order)

        # 獲取已完成的訂單
        for order in self.completed_orders.values():
            if status is None or order.status == status:
                orders.append(order)

        # 獲取券商 API 中的訂單
        broker_orders = self.broker.get_orders(status)
        for order in broker_orders:
            if (
                order.order_id not in self.pending_orders
                and order.order_id not in self.completed_orders
            ):
                orders.append(order)

        return orders

    def set_order_callbacks(
        self,
        on_status_change: Optional[Callable[[Order], None]] = None,
        on_filled: Optional[Callable[[Order], None]] = None,
        on_rejected: Optional[Callable[[Order], None]] = None,
    ):
        """
        設置訂單回調函數

        Args:
            on_status_change (Callable[[Order], None], optional): 訂單狀態變更回調
            on_filled (Callable[[Order], None], optional): 訂單成交回調
            on_rejected (Callable[[Order], None], optional): 訂單拒絕回調
        """
        self.on_order_status_change = on_status_change
        self.on_order_filled = on_filled
        self.on_order_rejected = on_rejected

    def _process_orders(self):
        """處理訂單隊列"""
        while self.running:
            try:
                # 從隊列中獲取訂單
                try:
                    order = self.order_queue.get(timeout=1)
                except queue.Empty:
                    continue

                # 檢查券商 API 連接狀態
                if not self.broker.connected:
                    if self.auto_reconnect:
                        logger.warning("券商 API 未連接，嘗試重新連接")
                        if not self.broker.connect():
                            logger.error("重新連接券商 API 失敗，訂單將重新加入隊列")
                            self.order_queue.put(order)
                            time.sleep(self.retry_interval)
                            continue
                    else:
                        logger.error("券商 API 未連接，訂單將被拒絕")
                        order.status = OrderStatus.REJECTED
                        order.error_message = "券商 API 未連接"
                        self._log_order(order)
                        if self.on_order_rejected:
                            self.on_order_rejected(order)
                        self.order_queue.task_done()
                        continue

                # 提交訂單
                logger.info(f"正在提交訂單: {order}")
                order_id = self._submit_order_with_retry(order)

                if order_id:
                    # 訂單提交成功
                    order.order_id = order_id
                    order.status = OrderStatus.SUBMITTED
                    self.pending_orders[order_id] = order
                    logger.info(f"訂單提交成功: {order_id}")
                    self._log_order(order)
                    if self.on_order_status_change:
                        self.on_order_status_change(order)
                else:
                    # 訂單提交失敗
                    order.status = OrderStatus.REJECTED
                    order.error_message = "訂單提交失敗"
                    logger.error(f"訂單提交失敗: {order}")
                    self._log_order(order)
                    if self.on_order_rejected:
                        self.on_order_rejected(order)

                self.order_queue.task_done()
            except Exception as e:
                logger.exception(f"處理訂單時發生錯誤: {e}")

    @retry(max_retries=3)
    def _submit_order_with_retry(self, order: Order) -> Optional[str]:
        """
        使用重試機制提交訂單

        Args:
            order (Order): 訂單物件

        Returns:
            str: 訂單 ID 或 None (如果提交失敗)
        """
        return self.broker.place_order(order)

    def _update_order_status(self):
        """更新訂單狀態"""
        while self.running:
            try:
                # 獲取所有等待中的訂單
                pending_order_ids = list(self.pending_orders.keys())
                for order_id in pending_order_ids:
                    # 獲取訂單最新狀態
                    updated_order = self.broker.get_order(order_id)
                    if updated_order is None:
                        continue

                    # 獲取原始訂單
                    original_order = self.pending_orders[order_id]

                    # 檢查狀態是否變更
                    if updated_order.status != original_order.status:
                        # 更新訂單狀態
                        original_order.status = updated_order.status
                        original_order.filled_quantity = updated_order.filled_quantity
                        original_order.filled_price = updated_order.filled_price
                        original_order.updated_at = datetime.now()
                        original_order.error_message = updated_order.error_message
                        original_order.exchange_order_id = (
                            updated_order.exchange_order_id
                        )

                        # 記錄訂單狀態變更
                        logger.info(
                            f"訂單狀態變更: {order_id} -> {original_order.status.value}"
                        )
                        self._log_order(original_order)

                        # 調用回調函數
                        if self.on_order_status_change:
                            self.on_order_status_change(original_order)

                        # 處理已完成的訂單
                        if original_order.status in [
                            OrderStatus.FILLED,
                            OrderStatus.CANCELLED,
                            OrderStatus.REJECTED,
                            OrderStatus.EXPIRED,
                        ]:
                            # 從等待中的訂單移除
                            self.pending_orders.pop(order_id)
                            # 加入已完成的訂單
                            self.completed_orders[order_id] = original_order

                            # 調用特定回調函數
                            if (
                                original_order.status == OrderStatus.FILLED
                                and self.on_order_filled
                            ):
                                self.on_order_filled(original_order)
                            elif (
                                original_order.status == OrderStatus.REJECTED
                                and self.on_order_rejected
                            ):
                                self.on_order_rejected(original_order)

                # 等待一段時間再更新
                time.sleep(1)
            except Exception as e:
                logger.exception(f"更新訂單狀態時發生錯誤: {e}")
                time.sleep(5)

    def _log_order(self, order: Order):
        """
        記錄訂單日誌

        Args:
            order (Order): 訂單物件
        """
        try:
            # 創建日誌檔案路徑
            log_file = (
                Path(self.order_log_dir) / f"{datetime.now().strftime('%Y%m%d')}.json"
            )

            # 將訂單轉換為字典
            order_dict = order.to_dict()
            order_dict["log_time"] = datetime.now().isoformat()

            # 寫入日誌
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(order_dict, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.exception(f"記錄訂單日誌時發生錯誤: {e}")
