"""
訂單確認機制

此模組提供訂單確認功能，包括：
- 二次確認機制
- 風險檢查
- 訂單驗證
- 確認記錄
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from src.execution.broker_base import BrokerBase, Order, OrderType, OrderStatus

# 設定日誌
logger = logging.getLogger("trading.live.order_confirmation")


class ConfirmationLevel(Enum):
    """確認級別枚舉"""
    NONE = "none"  # 無需確認
    BASIC = "basic"  # 基本確認
    ENHANCED = "enhanced"  # 增強確認
    STRICT = "strict"  # 嚴格確認


class RiskLevel(Enum):
    """風險級別枚舉"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OrderConfirmationManager:
    """訂單確認管理器"""
    
    def __init__(self, broker: BrokerBase):
        """
        初始化訂單確認管理器
        
        Args:
            broker (BrokerBase): 券商適配器
        """
        self.broker = broker
        
        # 確認設定
        self.confirmation_settings = {
            "default_level": ConfirmationLevel.BASIC,
            "high_value_threshold": 100000,  # 高價值訂單閾值
            "large_quantity_threshold": 10000,  # 大數量訂單閾值
            "require_double_confirmation": True,  # 需要二次確認
            "confirmation_timeout": 300,  # 確認超時時間 (秒)
        }
        
        # 風險檢查規則
        self.risk_rules = {
            "max_single_order_value": 500000,  # 單筆訂單最大價值
            "max_daily_order_count": 100,  # 每日最大訂單數
            "max_daily_volume": 1000000,  # 每日最大交易量
            "position_concentration_limit": 0.3,  # 持倉集中度限制 30%
            "margin_usage_limit": 0.8,  # 保證金使用率限制 80%
        }
        
        # 待確認訂單
        self.pending_confirmations: Dict[str, Dict[str, Any]] = {}
        
        # 確認記錄
        self.confirmation_history: List[Dict[str, Any]] = []
        
        # 今日統計
        self.daily_stats = {
            "date": datetime.now().date(),
            "order_count": 0,
            "total_volume": 0.0,
            "confirmed_orders": 0,
            "rejected_orders": 0,
        }
        
        # 回調函數
        self.on_confirmation_required: Optional[Callable] = None
        self.on_order_confirmed: Optional[Callable] = None
        self.on_order_rejected: Optional[Callable] = None
        self.on_risk_warning: Optional[Callable] = None
    
    def request_order_confirmation(self, order: Order, 
                                 user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        請求訂單確認
        
        Args:
            order (Order): 訂單物件
            user_id (str, optional): 用戶 ID
            
        Returns:
            Dict[str, Any]: 確認請求結果
        """
        try:
            # 更新每日統計
            self._update_daily_stats()
            
            # 風險檢查
            risk_result = self._check_order_risk(order)
            
            if risk_result["risk_level"] == RiskLevel.CRITICAL:
                logger.error(f"訂單風險過高，拒絕執行: {risk_result['message']}")
                return {
                    "success": False,
                    "message": f"訂單風險過高: {risk_result['message']}",
                    "risk_level": risk_result["risk_level"].value,
                    "risk_details": risk_result,
                }
            
            # 確定確認級別
            confirmation_level = self._determine_confirmation_level(order, risk_result)
            
            # 如果不需要確認，直接執行
            if confirmation_level == ConfirmationLevel.NONE:
                return self._execute_order_directly(order, user_id)
            
            # 生成確認 ID
            confirmation_id = f"confirm_{int(datetime.now().timestamp())}_{order.stock_id}"
            
            # 創建確認請求
            confirmation_request = {
                "confirmation_id": confirmation_id,
                "order": order,
                "user_id": user_id,
                "confirmation_level": confirmation_level,
                "risk_result": risk_result,
                "created_time": datetime.now(),
                "expires_at": datetime.now() + timedelta(seconds=self.confirmation_settings["confirmation_timeout"]),
                "status": "pending",
            }
            
            self.pending_confirmations[confirmation_id] = confirmation_request
            
            logger.info(f"訂單確認請求已創建: {confirmation_id}")
            
            # 調用回調函數
            if self.on_confirmation_required:
                self.on_confirmation_required(confirmation_request)
            
            return {
                "success": True,
                "message": "需要確認才能執行訂單",
                "confirmation_id": confirmation_id,
                "confirmation_level": confirmation_level.value,
                "risk_level": risk_result["risk_level"].value,
                "risk_details": risk_result,
                "expires_at": confirmation_request["expires_at"].isoformat(),
                "order_summary": self._get_order_summary(order),
            }
            
        except Exception as e:
            logger.exception(f"請求訂單確認失敗: {e}")
            return {
                "success": False,
                "message": f"請求訂單確認失敗: {e}",
                "error": str(e),
            }
    
    def confirm_order(self, confirmation_id: str, confirmed: bool, 
                     user_id: Optional[str] = None, 
                     confirmation_code: Optional[str] = None) -> Dict[str, Any]:
        """
        確認訂單
        
        Args:
            confirmation_id (str): 確認 ID
            confirmed (bool): 是否確認
            user_id (str, optional): 用戶 ID
            confirmation_code (str, optional): 確認碼
            
        Returns:
            Dict[str, Any]: 確認結果
        """
        try:
            if confirmation_id not in self.pending_confirmations:
                return {
                    "success": False,
                    "message": "找不到待確認的訂單",
                }
            
            confirmation_request = self.pending_confirmations[confirmation_id]
            
            # 檢查是否過期
            if datetime.now() > confirmation_request["expires_at"]:
                del self.pending_confirmations[confirmation_id]
                return {
                    "success": False,
                    "message": "確認請求已過期",
                }
            
            # 檢查用戶權限
            if user_id and confirmation_request.get("user_id") != user_id:
                return {
                    "success": False,
                    "message": "用戶權限不足",
                }
            
            # 檢查確認碼 (如果需要)
            if (confirmation_request["confirmation_level"] == ConfirmationLevel.STRICT and 
                not self._verify_confirmation_code(confirmation_code)):
                return {
                    "success": False,
                    "message": "確認碼錯誤",
                }
            
            order = confirmation_request["order"]
            
            if confirmed:
                # 確認執行訂單
                result = self._execute_confirmed_order(order, confirmation_request)
                
                # 記錄確認
                self._record_confirmation(confirmation_request, True, result)
                
                # 更新統計
                self.daily_stats["confirmed_orders"] += 1
                
                # 調用回調函數
                if self.on_order_confirmed:
                    self.on_order_confirmed(confirmation_request, result)
                
                return result
            else:
                # 拒絕訂單
                result = {
                    "success": False,
                    "message": "用戶拒絕執行訂單",
                    "confirmation_id": confirmation_id,
                }
                
                # 記錄拒絕
                self._record_confirmation(confirmation_request, False, result)
                
                # 更新統計
                self.daily_stats["rejected_orders"] += 1
                
                # 調用回調函數
                if self.on_order_rejected:
                    self.on_order_rejected(confirmation_request, result)
                
                return result
            
        except Exception as e:
            logger.exception(f"確認訂單失敗: {e}")
            return {
                "success": False,
                "message": f"確認訂單失敗: {e}",
                "error": str(e),
            }
        finally:
            # 清理待確認訂單
            if confirmation_id in self.pending_confirmations:
                del self.pending_confirmations[confirmation_id]
    
    def get_pending_confirmations(self) -> List[Dict[str, Any]]:
        """
        獲取待確認訂單列表
        
        Returns:
            List[Dict[str, Any]]: 待確認訂單列表
        """
        try:
            # 清理過期的確認請求
            current_time = datetime.now()
            expired_ids = []
            
            for confirmation_id, request in self.pending_confirmations.items():
                if current_time > request["expires_at"]:
                    expired_ids.append(confirmation_id)
            
            for confirmation_id in expired_ids:
                del self.pending_confirmations[confirmation_id]
                logger.info(f"清理過期確認請求: {confirmation_id}")
            
            # 返回待確認列表
            pending_list = []
            for confirmation_id, request in self.pending_confirmations.items():
                pending_list.append({
                    "confirmation_id": confirmation_id,
                    "order_summary": self._get_order_summary(request["order"]),
                    "confirmation_level": request["confirmation_level"].value,
                    "risk_level": request["risk_result"]["risk_level"].value,
                    "created_time": request["created_time"].isoformat(),
                    "expires_at": request["expires_at"].isoformat(),
                    "time_remaining": int((request["expires_at"] - current_time).total_seconds()),
                })
            
            return pending_list
            
        except Exception as e:
            logger.exception(f"獲取待確認訂單列表失敗: {e}")
            return []
    
    def cancel_confirmation(self, confirmation_id: str) -> bool:
        """
        取消確認請求
        
        Args:
            confirmation_id (str): 確認 ID
            
        Returns:
            bool: 是否取消成功
        """
        try:
            if confirmation_id in self.pending_confirmations:
                del self.pending_confirmations[confirmation_id]
                logger.info(f"已取消確認請求: {confirmation_id}")
                return True
            else:
                logger.warning(f"找不到確認請求: {confirmation_id}")
                return False
        except Exception as e:
            logger.exception(f"取消確認請求失敗: {e}")
            return False

    def update_confirmation_settings(self, **kwargs) -> bool:
        """
        更新確認設定

        Args:
            **kwargs: 設定參數

        Returns:
            bool: 是否更新成功
        """
        try:
            for key, value in kwargs.items():
                if key in self.confirmation_settings:
                    self.confirmation_settings[key] = value
                    logger.info(f"已更新確認設定 {key}: {value}")
            return True
        except Exception as e:
            logger.exception(f"更新確認設定失敗: {e}")
            return False

    def update_risk_rules(self, **kwargs) -> bool:
        """
        更新風險規則

        Args:
            **kwargs: 風險規則參數

        Returns:
            bool: 是否更新成功
        """
        try:
            for key, value in kwargs.items():
                if key in self.risk_rules:
                    self.risk_rules[key] = value
                    logger.info(f"已更新風險規則 {key}: {value}")
            return True
        except Exception as e:
            logger.exception(f"更新風險規則失敗: {e}")
            return False

    def get_confirmation_statistics(self) -> Dict[str, Any]:
        """
        獲取確認統計資訊

        Returns:
            Dict[str, Any]: 統計資訊
        """
        self._update_daily_stats()

        return {
            "daily_stats": self.daily_stats.copy(),
            "pending_confirmations": len(self.pending_confirmations),
            "confirmation_history_count": len(self.confirmation_history),
            "settings": self.confirmation_settings.copy(),
            "risk_rules": self.risk_rules.copy(),
        }

    def _check_order_risk(self, order: Order) -> Dict[str, Any]:
        """
        檢查訂單風險

        Args:
            order (Order): 訂單物件

        Returns:
            Dict[str, Any]: 風險檢查結果
        """
        try:
            risk_factors = []
            risk_level = RiskLevel.LOW

            # 計算訂單價值
            order_value = 0
            if order.price and order.quantity:
                order_value = order.price * order.quantity

            # 檢查單筆訂單價值
            if order_value > self.risk_rules["max_single_order_value"]:
                risk_factors.append(f"單筆訂單價值 {order_value:,.0f} 超過限制 {self.risk_rules['max_single_order_value']:,.0f}")
                risk_level = RiskLevel.CRITICAL
            elif order_value > self.confirmation_settings["high_value_threshold"]:
                risk_factors.append(f"高價值訂單: {order_value:,.0f}")
                risk_level = max(risk_level, RiskLevel.HIGH)

            # 檢查訂單數量
            if order.quantity > self.confirmation_settings["large_quantity_threshold"]:
                risk_factors.append(f"大數量訂單: {order.quantity:,.0f}")
                risk_level = max(risk_level, RiskLevel.MEDIUM)

            # 檢查每日訂單數
            if self.daily_stats["order_count"] >= self.risk_rules["max_daily_order_count"]:
                risk_factors.append(f"每日訂單數達到限制: {self.daily_stats['order_count']}")
                risk_level = RiskLevel.CRITICAL

            # 檢查每日交易量
            if self.daily_stats["total_volume"] + order_value > self.risk_rules["max_daily_volume"]:
                risk_factors.append(f"每日交易量將超過限制")
                risk_level = max(risk_level, RiskLevel.HIGH)

            # 檢查持倉集中度
            positions = self.broker.get_positions()
            if positions:
                total_value = sum(pos.get("market_value", 0) for pos in positions.values())
                if total_value > 0:
                    current_position = positions.get(order.stock_id, {})
                    current_value = current_position.get("market_value", 0)

                    # 計算執行後的持倉價值
                    if order.action.lower() == "buy":
                        new_value = current_value + order_value
                    else:
                        new_value = max(0, current_value - order_value)

                    concentration = new_value / (total_value + order_value)

                    if concentration > self.risk_rules["position_concentration_limit"]:
                        risk_factors.append(f"持倉集中度 {concentration:.1%} 超過限制 {self.risk_rules['position_concentration_limit']:.1%}")
                        risk_level = max(risk_level, RiskLevel.HIGH)

            # 檢查保證金使用率
            account_info = self.broker.get_account_info()
            if account_info:
                margin_used = account_info.get("margin_used", 0)
                margin_available = account_info.get("margin_available", 0)
                total_margin = margin_used + margin_available

                if total_margin > 0:
                    margin_usage = margin_used / total_margin

                    if margin_usage > self.risk_rules["margin_usage_limit"]:
                        risk_factors.append(f"保證金使用率 {margin_usage:.1%} 超過限制 {self.risk_rules['margin_usage_limit']:.1%}")
                        risk_level = max(risk_level, RiskLevel.HIGH)

            return {
                "risk_level": risk_level,
                "risk_factors": risk_factors,
                "order_value": order_value,
                "message": "; ".join(risk_factors) if risk_factors else "風險檢查通過",
            }

        except Exception as e:
            logger.exception(f"風險檢查失敗: {e}")
            return {
                "risk_level": RiskLevel.MEDIUM,
                "risk_factors": [f"風險檢查失敗: {e}"],
                "order_value": 0,
                "message": f"風險檢查失敗: {e}",
            }

    def _determine_confirmation_level(self, order: Order,
                                    risk_result: Dict[str, Any]) -> ConfirmationLevel:
        """
        確定確認級別

        Args:
            order (Order): 訂單物件
            risk_result (Dict[str, Any]): 風險檢查結果

        Returns:
            ConfirmationLevel: 確認級別
        """
        risk_level = risk_result["risk_level"]

        if risk_level == RiskLevel.CRITICAL:
            return ConfirmationLevel.STRICT
        elif risk_level == RiskLevel.HIGH:
            return ConfirmationLevel.ENHANCED
        elif risk_level == RiskLevel.MEDIUM:
            return ConfirmationLevel.BASIC
        else:
            # 低風險訂單根據設定決定
            return self.confirmation_settings["default_level"]

    def _execute_order_directly(self, order: Order, user_id: Optional[str]) -> Dict[str, Any]:
        """
        直接執行訂單 (無需確認)

        Args:
            order (Order): 訂單物件
            user_id (str, optional): 用戶 ID

        Returns:
            Dict[str, Any]: 執行結果
        """
        try:
            order_id = self.broker.place_order(order)

            if order_id:
                self.daily_stats["order_count"] += 1
                if order.price and order.quantity:
                    self.daily_stats["total_volume"] += order.price * order.quantity

                return {
                    "success": True,
                    "message": "訂單已直接執行",
                    "order_id": order_id,
                    "confirmation_required": False,
                }
            else:
                return {
                    "success": False,
                    "message": "訂單執行失敗",
                }

        except Exception as e:
            logger.exception(f"直接執行訂單失敗: {e}")
            return {
                "success": False,
                "message": f"直接執行訂單失敗: {e}",
                "error": str(e),
            }

    def _execute_confirmed_order(self, order: Order,
                               confirmation_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        執行已確認的訂單

        Args:
            order (Order): 訂單物件
            confirmation_request (Dict[str, Any]): 確認請求

        Returns:
            Dict[str, Any]: 執行結果
        """
        try:
            order_id = self.broker.place_order(order)

            if order_id:
                self.daily_stats["order_count"] += 1
                if order.price and order.quantity:
                    self.daily_stats["total_volume"] += order.price * order.quantity

                return {
                    "success": True,
                    "message": "已確認訂單執行成功",
                    "order_id": order_id,
                    "confirmation_id": confirmation_request["confirmation_id"],
                    "confirmation_level": confirmation_request["confirmation_level"].value,
                }
            else:
                return {
                    "success": False,
                    "message": "已確認訂單執行失敗",
                    "confirmation_id": confirmation_request["confirmation_id"],
                }

        except Exception as e:
            logger.exception(f"執行已確認訂單失敗: {e}")
            return {
                "success": False,
                "message": f"執行已確認訂單失敗: {e}",
                "confirmation_id": confirmation_request["confirmation_id"],
                "error": str(e),
            }

    def _get_order_summary(self, order: Order) -> Dict[str, Any]:
        """
        獲取訂單摘要

        Args:
            order (Order): 訂單物件

        Returns:
            Dict[str, Any]: 訂單摘要
        """
        return {
            "symbol": order.stock_id,
            "action": order.action,
            "quantity": order.quantity,
            "order_type": order.order_type.value,
            "price": order.price,
            "stop_price": order.stop_price,
            "time_in_force": order.time_in_force,
            "estimated_value": (order.price * order.quantity) if order.price else None,
        }

    def _record_confirmation(self, confirmation_request: Dict[str, Any],
                           confirmed: bool, result: Dict[str, Any]):
        """
        記錄確認結果

        Args:
            confirmation_request (Dict[str, Any]): 確認請求
            confirmed (bool): 是否確認
            result (Dict[str, Any]): 執行結果
        """
        try:
            record = {
                "confirmation_id": confirmation_request["confirmation_id"],
                "order_summary": self._get_order_summary(confirmation_request["order"]),
                "user_id": confirmation_request.get("user_id"),
                "confirmation_level": confirmation_request["confirmation_level"].value,
                "risk_level": confirmation_request["risk_result"]["risk_level"].value,
                "confirmed": confirmed,
                "result": result,
                "created_time": confirmation_request["created_time"].isoformat(),
                "confirmed_time": datetime.now().isoformat(),
            }

            self.confirmation_history.append(record)

            # 保持歷史記錄在合理範圍內
            if len(self.confirmation_history) > 1000:
                self.confirmation_history = self.confirmation_history[-500:]

        except Exception as e:
            logger.exception(f"記錄確認結果失敗: {e}")

    def _verify_confirmation_code(self, confirmation_code: Optional[str]) -> bool:
        """
        驗證確認碼

        Args:
            confirmation_code (str, optional): 確認碼

        Returns:
            bool: 是否驗證通過
        """
        # 這裡可以實現更複雜的確認碼驗證邏輯
        # 例如：時間戳驗證、數字簽名等
        if not confirmation_code:
            return False

        # 簡單的確認碼驗證 (實際應用中應該更安全)
        expected_code = "CONFIRM123"  # 這應該是動態生成的
        return confirmation_code == expected_code

    def _update_daily_stats(self):
        """更新每日統計"""
        current_date = datetime.now().date()

        # 如果日期變更，重置統計
        if self.daily_stats["date"] != current_date:
            self.daily_stats = {
                "date": current_date,
                "order_count": 0,
                "total_volume": 0.0,
                "confirmed_orders": 0,
                "rejected_orders": 0,
            }

    def get_confirmation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        獲取確認歷史

        Args:
            limit (int): 限制數量

        Returns:
            List[Dict[str, Any]]: 確認歷史
        """
        return self.confirmation_history[-limit:] if self.confirmation_history else []
