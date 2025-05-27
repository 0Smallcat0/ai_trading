"""交易執行回調與事件處理模組

此模組提供事件處理相關的功能，包括：
- 訂單狀態變更回調
- 成交回調處理
- 拒絕訂單回調
- 事件日誌記錄

從主要的 TradeExecutionService 中分離出來以提高代碼可維護性。
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable

from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class TradeExecutionCallbackManager:
    """交易執行回調管理器"""

    def __init__(self, session_factory: sessionmaker):
        """初始化回調管理器
        
        Args:
            session_factory: SQLAlchemy session factory
        """
        self.session_factory = session_factory
        self.callbacks = {
            "order_status_change": [],
            "order_filled": [],
            "order_rejected": [],
            "order_cancelled": [],
            "execution_created": [],
        }

    def register_callback(self, event_type: str, callback: Callable):
        """註冊回調函數
        
        Args:
            event_type: 事件類型
            callback: 回調函數
        """
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
        else:
            logger.warning("未知的事件類型: %s", event_type)

    def unregister_callback(self, event_type: str, callback: Callable):
        """取消註冊回調函數
        
        Args:
            event_type: 事件類型
            callback: 回調函數
        """
        if event_type in self.callbacks and callback in self.callbacks[event_type]:
            self.callbacks[event_type].remove(callback)

    def trigger_callbacks(self, event_type: str, *args, **kwargs):
        """觸發回調函數
        
        Args:
            event_type: 事件類型
            *args: 位置參數
            **kwargs: 關鍵字參數
        """
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error("回調函數執行失敗: %s", e)

    def on_order_status_change(self, order):
        """訂單狀態變更回調
        
        Args:
            order: 訂單對象
        """
        try:
            logger.info(
                "訂單狀態變更: %s -> %s",
                order.order_id,
                order.status,
            )

            # 更新資料庫中的訂單狀態
            self._update_order_in_db(order)

            # 記錄執行日誌
            self._log_execution_event(
                "order_status_change",
                {
                    "order_id": order.order_id,
                    "old_status": getattr(order, "_old_status", None),
                    "new_status": order.status,
                    "timestamp": datetime.now(),
                },
            )

            # 觸發註冊的回調
            self.trigger_callbacks("order_status_change", order)

        except Exception as e:
            logger.error("處理訂單狀態變更失敗: %s", e)

    def on_order_filled(self, order):
        """訂單成交回調
        
        Args:
            order: 訂單對象
        """
        try:
            logger.info(
                "訂單 %s 成交: %s股 @ %s",
                order.order_id,
                order.filled_quantity,
                order.filled_price,
            )

            # 創建成交記錄
            self._create_execution_record(order)

            # 更新訂單狀態
            self._update_order_in_db(order)

            # 記錄執行日誌
            self._log_execution_event(
                "order_filled",
                {
                    "order_id": order.order_id,
                    "filled_quantity": order.filled_quantity,
                    "filled_price": order.filled_price,
                    "timestamp": datetime.now(),
                },
            )

            # 觸發註冊的回調
            self.trigger_callbacks("order_filled", order)

        except Exception as e:
            logger.error("處理訂單成交失敗: %s", e)

    def on_order_rejected(self, order, reason: str):
        """訂單拒絕回調
        
        Args:
            order: 訂單對象
            reason: 拒絕原因
        """
        try:
            logger.warning(
                "訂單 %s 被拒絕: %s",
                order.order_id,
                reason,
            )

            # 更新訂單狀態和錯誤信息
            order.status = "rejected"
            order.error_message = reason
            self._update_order_in_db(order)

            # 記錄執行日誌
            self._log_execution_event(
                "order_rejected",
                {
                    "order_id": order.order_id,
                    "reason": reason,
                    "timestamp": datetime.now(),
                },
            )

            # 觸發註冊的回調
            self.trigger_callbacks("order_rejected", order, reason)

        except Exception as e:
            logger.error("處理訂單拒絕失敗: %s", e)

    def on_order_cancelled(self, order, reason: str = "用戶取消"):
        """訂單取消回調
        
        Args:
            order: 訂單對象
            reason: 取消原因
        """
        try:
            logger.info(
                "訂單 %s 已取消: %s",
                order.order_id,
                reason,
            )

            # 更新訂單狀態
            order.status = "cancelled"
            order.error_message = reason
            self._update_order_in_db(order)

            # 記錄執行日誌
            self._log_execution_event(
                "order_cancelled",
                {
                    "order_id": order.order_id,
                    "reason": reason,
                    "timestamp": datetime.now(),
                },
            )

            # 觸發註冊的回調
            self.trigger_callbacks("order_cancelled", order, reason)

        except Exception as e:
            logger.error("處理訂單取消失敗: %s", e)

    def _update_order_in_db(self, order):
        """更新資料庫中的訂單
        
        Args:
            order: 訂單對象
        """
        try:
            from src.database.schema import TradingOrder
            
            with self.session_factory() as session:
                db_order = (
                    session.query(TradingOrder)
                    .filter_by(order_id=order.order_id)
                    .first()
                )
                if db_order:
                    # 更新訂單欄位
                    db_order.status = order.status
                    db_order.filled_quantity = getattr(order, "filled_quantity", 0)
                    db_order.filled_price = getattr(order, "filled_price", None)
                    db_order.filled_at = getattr(order, "filled_at", None)
                    db_order.error_message = getattr(order, "error_message", None)
                    db_order.commission = getattr(order, "commission", None)
                    db_order.tax = getattr(order, "tax", None)
                    db_order.total_cost = getattr(order, "total_cost", None)

                    session.commit()
                    logger.debug("訂單 %s 資料庫更新成功", order.order_id)
        except Exception as e:
            logger.error("更新訂單資料庫失敗: %s", e)

    def _create_execution_record(self, order):
        """創建成交記錄
        
        Args:
            order: 訂單對象
        """
        try:
            from src.database.schema import TradeExecution
            
            with self.session_factory() as session:
                execution = TradeExecution(
                    execution_id=f"exec_{order.order_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    order_id=order.order_id,
                    symbol=order.symbol,
                    action=order.action,
                    quantity=order.filled_quantity,
                    price=order.filled_price,
                    amount=order.filled_quantity * order.filled_price,
                    commission=getattr(order, "commission", 0),
                    tax=getattr(order, "tax", 0),
                    net_amount=(
                        order.filled_quantity * order.filled_price
                        - getattr(order, "commission", 0)
                        - getattr(order, "tax", 0)
                    ),
                    execution_time=datetime.now(),
                    slippage=getattr(order, "slippage", 0),
                )

                session.add(execution)
                session.commit()
                logger.debug("成交記錄 %s 創建成功", execution.execution_id)

                # 觸發成交記錄創建回調
                self.trigger_callbacks("execution_created", execution)

        except Exception as e:
            logger.error("創建成交記錄失敗: %s", e)

    def _log_execution_event(self, event_type: str, event_data: Dict[str, Any]):
        """記錄執行事件
        
        Args:
            event_type: 事件類型
            event_data: 事件數據
        """
        try:
            from src.database.schema import ExecutionLog
            
            with self.session_factory() as session:
                log_entry = ExecutionLog(
                    log_id=f"log_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                    event_type=event_type,
                    event_data=event_data,
                    timestamp=datetime.now(),
                    level="INFO",
                )

                session.add(log_entry)
                session.commit()
                logger.debug("執行事件日誌記錄成功: %s", event_type)

        except Exception as e:
            logger.error("記錄執行事件失敗: %s", e)

    def get_execution_logs(
        self,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """獲取執行日誌
        
        Args:
            event_type: 事件類型篩選
            start_date: 開始日期
            end_date: 結束日期
            limit: 返回記錄數量限制
            
        Returns:
            List[Dict]: 執行日誌列表
        """
        try:
            from src.database.schema import ExecutionLog
            
            with self.session_factory() as session:
                query = session.query(ExecutionLog)

                # 應用篩選條件
                if event_type:
                    query = query.filter(ExecutionLog.event_type == event_type)
                if start_date:
                    query = query.filter(ExecutionLog.timestamp >= start_date)
                if end_date:
                    query = query.filter(ExecutionLog.timestamp <= end_date)

                # 按時間降序排序並限制數量
                logs = query.order_by(ExecutionLog.timestamp.desc()).limit(limit).all()

                result = []
                for log in logs:
                    result.append(
                        {
                            "log_id": log.log_id,
                            "event_type": log.event_type,
                            "event_data": log.event_data,
                            "timestamp": log.timestamp.isoformat(),
                            "level": log.level,
                        }
                    )

                return result
        except Exception as e:
            logger.error("獲取執行日誌失敗: %s", e)
            return []
