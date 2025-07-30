"""交易執行服務模組 (重構版)

此模組提供交易執行的核心服務功能，包括：
- 交易下單管理
- 訂單狀態追蹤
- 歷史記錄查詢
- 模擬/實盤切換
- 異常處理與通知
- 券商API整合

使用模組化設計，將功能分散到專門的管理器中以提高可維護性。
"""

import logging
import threading
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from src.utils.database_utils import get_database_manager

# 導入專案模組
try:
    from src.config import DB_URL
    from src.database.schema import TradingOrder, init_db
    from src.execution.order_manager import OrderManager
    from src.execution.broker_base import Order, OrderType
    from src.core.risk_management_service import RiskManagementService
    from src.core.trade_execution_orders import TradeExecutionOrderManager
    from src.core.trade_execution_stats import TradeExecutionStatsManager
    from src.core.trade_execution_brokers import TradeExecutionBrokerManager
    from src.core.trade_execution_callbacks import TradeExecutionCallbackManager
except ImportError as e:
    logging.warning("無法導入部分模組: %s", e)

    # 定義一個簡單的 init_db 函數作為備用
    def init_db(engine):
        """簡單的資料庫初始化函數

        Args:
            engine: 資料庫引擎
        """
        pass


logger = logging.getLogger(__name__)


class TradeExecutionService:
    """交易執行服務 (重構版)

    提供統一的交易執行介面，使用模組化設計整合各種功能。
    """

    def __init__(self, db_url: str = None):
        """初始化交易執行服務

        Args:
            db_url: 資料庫連接字串，如果為None則使用預設配置
        """
        self.db_url = db_url or DB_URL
        self.engine = None
        self.session_factory = None
        self.lock = threading.Lock()

        # 服務組件
        self.risk_service = None
        self.order_manager = None

        # 模組化管理器
        self.order_mgr = None
        self.stats_mgr = None
        self.broker_mgr = None
        self.callback_mgr = None

        # 初始化各組件
        self._init_database()
        self._init_risk_service()
        self._init_managers()

    def _init_database(self):
        """初始化資料庫連接"""
        try:
            # 使用統一的資料庫連接管理器
            self.db_manager = get_database_manager(self.db_url)
            self.engine = self.db_manager.get_engine()
            self.session_factory = self.db_manager.session_factory

            logger.info("交易執行服務資料庫連接初始化成功")
        except Exception as e:
            logger.error("交易執行服務資料庫連接初始化失敗: %s", e)
            raise e from e

    def _init_risk_service(self):
        """初始化風險管理服務"""
        try:
            self.risk_service = RiskManagementService()
            logger.info("風險管理服務初始化成功")
        except Exception as e:
            logger.warning("風險管理服務初始化失敗: %s", e)
            self.risk_service = None

    def _init_managers(self):
        """初始化模組化管理器"""
        try:
            # 初始化各個管理器
            self.order_mgr = TradeExecutionOrderManager(
                self.session_factory, self.risk_service
            )
            self.stats_mgr = TradeExecutionStatsManager(self.session_factory)
            self.broker_mgr = TradeExecutionBrokerManager(self.session_factory)
            self.callback_mgr = TradeExecutionCallbackManager(self.session_factory)

            # 初始化券商
            self.broker_mgr.init_brokers()

            # 初始化訂單管理器
            self._init_order_manager()

            logger.info("模組化管理器初始化成功")
        except Exception as e:
            logger.error("模組化管理器初始化失敗: %s", e)

    def _init_order_manager(self):
        """初始化訂單管理器"""
        try:
            if self.broker_mgr and self.broker_mgr.current_broker:
                self.order_manager = OrderManager(self.broker_mgr.current_broker)
                # 設置訂單回調
                self.order_manager.set_order_callbacks(
                    on_status_change=self.callback_mgr.on_order_status_change,
                    on_filled=self.callback_mgr.on_order_filled,
                    on_rejected=self.callback_mgr.on_order_rejected,
                )
                logger.info("訂單管理器初始化成功")
        except Exception as e:
            logger.error("訂單管理器初始化失敗: %s", e)

    # 委託給訂單管理器的方法
    def validate_order(
        self, order_data: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """驗證訂單"""
        return self.order_mgr.validate_order(order_data)

    def get_order_history(
        self,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """獲取訂單歷史記錄"""
        return self.order_mgr.get_order_history(
            symbol, status, start_date, end_date, limit
        )

    def get_order_details(self, order_id: str) -> Optional[Dict[str, Any]]:
        """獲取訂單詳情"""
        return self.order_mgr.get_order_details(order_id)

    def get_orders_list(
        self, page: int = 1, page_size: int = 20, filters: Dict = None
    ) -> Dict[str, Any]:
        """獲取訂單列表"""
        return self.order_mgr.get_orders_list(page, page_size, filters)

    def export_order_history(
        self, format_type: str = "csv", **kwargs
    ) -> Tuple[bool, str, Optional[str]]:
        """匯出訂單歷史"""
        return self.order_mgr.export_order_history(format_type, **kwargs)

    # 委託給統計管理器的方法
    def get_trade_executions(
        self,
        order_id: Optional[str] = None,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """獲取成交記錄"""
        return self.stats_mgr.get_trade_executions(
            order_id, symbol, start_date, end_date, limit
        )

    def get_execution_history(
        self, page: int = 1, page_size: int = 20, filters: Dict = None
    ) -> Dict[str, Any]:
        """獲取執行歷史"""
        return self.stats_mgr.get_execution_history(page, page_size, filters)

    def get_order_statistics(self, filters: Dict = None) -> Dict[str, Any]:
        """獲取訂單統計"""
        return self.stats_mgr.get_order_statistics(filters)

    def get_trading_statistics(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """獲取交易統計"""
        return self.stats_mgr.get_trading_statistics(start_date, end_date)

    def get_trading_performance(self) -> Dict[str, Any]:
        """獲取交易績效"""
        return self.stats_mgr.get_trading_performance()

    # 委託給券商管理器的方法
    def get_broker_status(self) -> Dict[str, Any]:
        """獲取券商狀態"""
        return self.broker_mgr.get_broker_status()

    def switch_trading_mode(self, is_simulation: bool) -> Tuple[bool, str]:
        """切換交易模式"""
        result = self.broker_mgr.switch_trading_mode(is_simulation)
        if result[0]:  # 如果切換成功，重新初始化訂單管理器
            self._init_order_manager()
        return result

    def get_available_symbols(self, broker_name: Optional[str] = None) -> List[str]:
        """獲取可交易標的"""
        return self.broker_mgr.get_available_symbols(broker_name)

    def get_market_status(self, broker_name: Optional[str] = None) -> Dict[str, Any]:
        """獲取市場狀態"""
        return self.broker_mgr.get_market_status(broker_name)

    def get_account_info(self, broker_name: Optional[str] = None) -> Dict[str, Any]:
        """獲取帳戶信息"""
        return self.broker_mgr.get_account_info(broker_name)

    def get_positions(self, broker_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """獲取持倉信息"""
        return self.broker_mgr.get_positions(broker_name)

    # 委託給回調管理器的方法
    def get_execution_logs(
        self,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """獲取執行日誌"""
        return self.callback_mgr.get_execution_logs(
            event_type, start_date, end_date, limit
        )

    # 額外的便利方法
    def get_favorite_symbols(self) -> List[str]:
        """獲取收藏股票列表"""
        # 這裡可以從用戶設定或資料庫獲取收藏列表
        # 暫時返回一些常見股票
        return ["2330.TW", "2317.TW", "2454.TW", "2412.TW", "6505.TW"]

    def get_recent_symbols(self, limit: int = 10) -> List[str]:
        """獲取最近交易股票列表"""
        try:
            from sqlalchemy import text

            with self.session_factory() as session:
                query = text(
                    """
                    SELECT DISTINCT symbol
                    FROM trading_order
                    ORDER BY created_at DESC
                    LIMIT :limit
                """
                )

                result = session.execute(query, {"limit": limit}).fetchall()
                return [row.symbol for row in result]
        except Exception as e:
            logger.error("獲取最近交易股票失敗: %s", e)
            return []

    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """獲取待處理訂單"""
        return self.get_order_history(status="pending")

    def get_trading_exceptions(
        self, limit: int = 100, severity: str = None, status: str = None
    ) -> List[Dict[str, Any]]:
        """獲取交易異常事件

        Args:
            limit: 返回記錄數量限制
            severity: 嚴重程度篩選
            status: 狀態篩選

        Returns:
            List[Dict]: 交易異常事件列表
        """
        try:
            # 這裡可以從資料庫查詢異常記錄
            # 暫時返回空列表，避免未使用參數警告
            _ = limit, severity, status
            return []
        except Exception as e:
            logger.error("獲取交易異常失敗: %s", e)
            return []

    @property
    def is_simulation_mode(self) -> bool:
        """獲取當前是否為模擬交易模式"""
        return self.broker_mgr.is_simulation_mode if self.broker_mgr else True

    # 核心交易方法
    def submit_order(
        self, order_data: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[str]]:
        """提交訂單"""
        try:
            # 驗證訂單
            is_valid, message, risk_check = self.validate_order(order_data)
            if not is_valid:
                return False, message, None

            # 創建訂單ID
            order_id = str(uuid.uuid4())

            # 創建訂單記錄
            order_record = TradingOrder(
                order_id=order_id,
                symbol=order_data["symbol"],
                action=order_data["action"],
                order_type=order_data["order_type"],
                time_in_force=order_data.get("time_in_force", "ROD"),
                quantity=order_data["quantity"],
                price=order_data.get("price"),
                stop_price=order_data.get("stop_price"),
                strategy_name=order_data.get("strategy_name"),
                signal_id=order_data.get("signal_id"),
                is_simulation=self.broker_mgr.is_simulation_mode,
                broker_name=(
                    self.broker_mgr.current_broker.__class__.__name__
                    if self.broker_mgr.current_broker
                    else "Unknown"
                ),
                risk_check_passed=risk_check["passed"],
                risk_check_details=risk_check,
                status="pending",
            )

            # 保存到資料庫
            with self.session_factory() as session:
                session.add(order_record)
                session.commit()

            # 提交到訂單管理器
            if self.order_manager:
                # 創建訂單物件
                order = Order(
                    stock_id=order_data["symbol"],
                    action=order_data["action"],
                    quantity=order_data["quantity"],
                    order_type=OrderType(order_data["order_type"]),
                    price=order_data.get("price"),
                    stop_price=order_data.get("stop_price"),
                    time_in_force=order_data.get("time_in_force", "day"),
                )
                order.order_id = order_id

                submitted_order_id = self.order_manager.submit_order(order)
                if submitted_order_id:
                    return True, "訂單提交成功", order_id
                else:
                    return False, "訂單提交失敗", order_id
            else:
                return False, "訂單管理器未初始化", order_id

        except Exception as e:
            logger.error("提交訂單失敗: %s", e)
            return False, f"提交訂單失敗: {e}", None

    def cancel_order(self, order_id: str) -> Tuple[bool, str]:
        """取消訂單"""
        try:
            # 檢查訂單是否存在
            with self.session_factory() as session:
                order = session.query(TradingOrder).filter_by(order_id=order_id).first()
                if not order:
                    return False, "訂單不存在"

                if order.status in ["filled", "cancelled", "rejected"]:
                    return False, f"訂單已{order.status}，無法取消"

            # 通過訂單管理器取消訂單
            if self.order_manager:
                success = self.order_manager.cancel_order(order_id)
                if success:
                    return True, "訂單取消成功"
                else:
                    return False, "訂單取消失敗"
            else:
                return False, "訂單管理器未初始化"

        except Exception as e:
            logger.error("取消訂單失敗: %s", e)
            return False, f"取消訂單失敗: {e}"
