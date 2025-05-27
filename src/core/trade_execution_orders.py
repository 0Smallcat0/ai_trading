"""交易執行訂單管理模組

此模組提供訂單相關的功能，包括：
- 訂單驗證與提交
- 訂單查詢與更新
- 訂單歷史記錄
- 訂單取消操作

從主要的 TradeExecutionService 中分離出來以提高代碼可維護性。
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class TradeExecutionOrderManager:
    """交易執行訂單管理器"""

    def __init__(self, session_factory: sessionmaker, risk_service=None):
        """初始化訂單管理器
        
        Args:
            session_factory: SQLAlchemy session factory
            risk_service: 風險管理服務實例
        """
        self.session_factory = session_factory
        self.risk_service = risk_service

    def validate_order(
        self, order_data: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """驗證訂單
        
        Args:
            order_data: 訂單數據字典
            
        Returns:
            Tuple[bool, str, Dict]: (是否有效, 訊息, 風險檢查結果)
        """
        try:
            # 基本參數驗證
            required_fields = ["symbol", "action", "quantity", "order_type"]
            for field in required_fields:
                if field not in order_data or order_data[field] is None:
                    return False, f"缺少必要參數: {field}", {}

            # 數量驗證
            quantity = order_data["quantity"]
            if not isinstance(quantity, (int, float)) or quantity <= 0:
                return False, "數量必須為正數", {}

            # 價格驗證（限價單需要價格）
            if order_data["order_type"] in [
                "limit",
                "stop_limit",
            ] and not order_data.get("price"):
                return False, "限價單必須指定價格", {}

            # 風險檢查
            risk_check_result = self._perform_risk_check(order_data)

            return True, "訂單驗證通過", risk_check_result
        except Exception as e:
            logger.error("訂單驗證失敗: %s", e)
            return False, f"訂單驗證失敗: {e}", {}

    def _perform_risk_check(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """執行風險檢查
        
        Args:
            order_data: 訂單數據
            
        Returns:
            Dict: 風險檢查結果
        """
        risk_result = {"passed": True, "warnings": [], "errors": [], "details": {}}

        try:
            if self.risk_service:
                # 獲取風險參數
                risk_params = self.risk_service.get_risk_parameters()

                # 檢查單筆交易限額
                max_position = risk_params.get("max_position_size", {}).get(
                    "value", 10.0
                )
                order_amount = order_data["quantity"] * order_data.get(
                    "price", 100
                )  # 估算金額

                if order_amount > max_position * 10000:  # 假設投資組合為100萬
                    risk_result["warnings"].append("訂單金額超過單筆限額建議值")

                # 檢查資金充足性（模擬檢查）
                if order_data["action"] == "buy":
                    available_cash = 500000  # 模擬可用資金
                    if order_amount > available_cash:
                        risk_result["passed"] = False
                        risk_result["errors"].append("資金不足")

                risk_result["details"] = {
                    "order_amount": order_amount,
                    "max_position_limit": max_position * 10000,
                    "available_cash": 500000,
                }
        except Exception as e:
            logger.warning("風險檢查失敗: %s", e)
            risk_result["warnings"].append("風險檢查服務不可用")

        return risk_result

    def get_order_history(
        self,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """獲取訂單歷史記錄
        
        Args:
            symbol: 股票代碼篩選
            status: 訂單狀態篩選
            start_date: 開始日期
            end_date: 結束日期
            limit: 返回記錄數量限制
            
        Returns:
            List[Dict]: 訂單歷史記錄列表
        """
        try:
            from src.database.schema import TradingOrder
            
            with self.session_factory() as session:
                query = session.query(TradingOrder)

                # 應用篩選條件
                if symbol:
                    query = query.filter(TradingOrder.symbol == symbol)
                if status:
                    query = query.filter(TradingOrder.status == status)
                if start_date:
                    query = query.filter(TradingOrder.created_at >= start_date)
                if end_date:
                    query = query.filter(TradingOrder.created_at <= end_date)

                # 按創建時間降序排序並限制數量
                orders = (
                    query.order_by(TradingOrder.created_at.desc()).limit(limit).all()
                )

                result = []
                for order in orders:
                    result.append(
                        {
                            "order_id": order.order_id,
                            "symbol": order.symbol,
                            "action": order.action,
                            "order_type": order.order_type,
                            "quantity": order.quantity,
                            "price": order.price,
                            "filled_quantity": order.filled_quantity,
                            "filled_price": order.filled_price,
                            "status": order.status,
                            "created_at": order.created_at.isoformat(),
                            "submitted_at": (
                                order.submitted_at.isoformat()
                                if order.submitted_at
                                else None
                            ),
                            "filled_at": (
                                order.filled_at.isoformat() if order.filled_at else None
                            ),
                            "commission": order.commission,
                            "tax": order.tax,
                            "total_cost": order.total_cost,
                            "strategy_name": order.strategy_name,
                            "is_simulation": order.is_simulation,
                            "error_message": order.error_message,
                        }
                    )

                return result
        except Exception as e:
            logger.error("獲取訂單歷史失敗: %s", e)
            return []

    def get_order_details(self, order_id: str) -> Optional[Dict[str, Any]]:
        """獲取訂單詳情
        
        Args:
            order_id: 訂單ID
            
        Returns:
            Optional[Dict]: 訂單詳情字典，如果不存在則返回None
        """
        try:
            from src.database.schema import TradingOrder
            
            with self.session_factory() as session:
                order = session.query(TradingOrder).filter_by(order_id=order_id).first()
                if not order:
                    return None

                return {
                    "order_id": order.order_id,
                    "symbol": order.symbol,
                    "action": order.action,
                    "order_type": order.order_type,
                    "quantity": order.quantity,
                    "price": order.price,
                    "filled_quantity": order.filled_quantity or 0,
                    "filled_price": order.filled_price,
                    "time_in_force": order.time_in_force,
                    "status": order.status,
                    "portfolio_id": getattr(order, "portfolio_id", None),
                    "created_at": order.created_at,
                    "updated_at": getattr(order, "updated_at", None),
                    "filled_at": order.filled_at,
                    "error_message": order.error_message,
                    "commission": order.commission,
                    "tax": order.tax,
                    "net_amount": getattr(order, "net_amount", None),
                    "notes": getattr(order, "notes", None),
                }
        except Exception as e:
            logger.error("獲取訂單詳情失敗: %s", e)
            return None

    def get_orders_list(
        self, page: int = 1, page_size: int = 20, filters: Dict = None
    ) -> Dict[str, Any]:
        """獲取訂單列表
        
        Args:
            page: 頁碼
            page_size: 每頁大小
            filters: 篩選條件字典
            
        Returns:
            Dict: 包含訂單列表和總數的字典
        """
        try:
            from src.database.schema import TradingOrder
            
            with self.session_factory() as session:
                query = session.query(TradingOrder)

                # 應用篩選條件
                if filters:
                    if filters.get("status"):
                        query = query.filter(TradingOrder.status == filters["status"])
                    if filters.get("symbol"):
                        query = query.filter(TradingOrder.symbol == filters["symbol"])
                    if filters.get("action"):
                        query = query.filter(TradingOrder.action == filters["action"])
                    if filters.get("order_type"):
                        query = query.filter(
                            TradingOrder.order_type == filters["order_type"]
                        )
                    if filters.get("start_date"):
                        query = query.filter(
                            TradingOrder.created_at >= filters["start_date"]
                        )
                    if filters.get("end_date"):
                        query = query.filter(
                            TradingOrder.created_at <= filters["end_date"]
                        )

                # 分頁
                offset = (page - 1) * page_size
                orders = (
                    query.order_by(TradingOrder.created_at.desc())
                    .offset(offset)
                    .limit(page_size)
                    .all()
                )

                orders_list = []
                for order in orders:
                    orders_list.append(
                        {
                            "order_id": order.order_id,
                            "symbol": order.symbol,
                            "action": order.action,
                            "order_type": order.order_type,
                            "quantity": order.quantity,
                            "price": order.price,
                            "filled_quantity": order.filled_quantity or 0,
                            "filled_price": order.filled_price,
                            "time_in_force": order.time_in_force,
                            "status": order.status,
                            "created_at": order.created_at,
                            "commission": order.commission,
                            "tax": order.tax,
                        }
                    )

                return {"orders": orders_list, "total": len(orders_list)}
        except Exception as e:
            logger.error("獲取訂單列表失敗: %s", e)
            return {"orders": [], "total": 0}

    def update_order(
        self, order_id: str, update_data: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """更新訂單
        
        Args:
            order_id: 訂單ID
            update_data: 更新數據字典
            
        Returns:
            Tuple[bool, str]: (是否成功, 訊息)
        """
        try:
            from src.database.schema import TradingOrder
            
            with self.session_factory() as session:
                order = session.query(TradingOrder).filter_by(order_id=order_id).first()
                if not order:
                    return False, "訂單不存在"

                # 更新訂單欄位
                for key, value in update_data.items():
                    if hasattr(order, key):
                        setattr(order, key, value)

                session.commit()
                return True, "訂單更新成功"
        except Exception as e:
            logger.error("更新訂單失敗: %s", e)
            return False, f"更新訂單失敗: {e}"

    def export_order_history(
        self, format_type: str = "csv", **kwargs
    ) -> Tuple[bool, str, Optional[str]]:
        """匯出訂單歷史
        
        Args:
            format_type: 匯出格式 ('csv' 或 'excel')
            **kwargs: 其他參數傳遞給 get_order_history
            
        Returns:
            Tuple[bool, str, Optional[str]]: (是否成功, 訊息, 檔案路徑)
        """
        try:
            from src.config import CACHE_DIR
            
            # 獲取訂單歷史
            orders = self.get_order_history(**kwargs)
            if not orders:
                return False, "沒有訂單記錄可匯出", None

            # 轉換為 DataFrame
            df = pd.DataFrame(orders)

            # 生成檔案名稱
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"order_history_{timestamp}.{format_type}"
            filepath = Path(CACHE_DIR) / filename

            # 確保目錄存在
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # 匯出檔案
            if format_type.lower() == "csv":
                df.to_csv(filepath, index=False, encoding="utf-8-sig")
            elif format_type.lower() == "excel":
                df.to_excel(filepath, index=False)
            else:
                return False, f"不支援的格式: {format_type}", None

            return True, f"訂單歷史已匯出到 {filename}", str(filepath)
        except Exception as e:
            logger.error("匯出訂單歷史失敗: %s", e)
            return False, f"匯出失敗: {e}", None
