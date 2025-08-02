"""
緊急風控措施模組

此模組提供緊急風控措施功能，包括：
- 一鍵全部平倉
- 異常交易暫停
- 風險警報系統
- 緊急措施統一管理

重構後的模組，具體行動執行邏輯分離到 emergency_actions.py
"""

import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from src.execution.broker_base import BrokerBase
from .emergency_actions import EmergencyActionExecutor
from .emergency_event_manager import EmergencyEventManager, EmergencyLevel

# 設定日誌
logger = logging.getLogger("risk.live.emergency_risk_control")


class EmergencyAction(Enum):
    """緊急行動枚舉"""
    CLOSE_ALL_POSITIONS = "close_all_positions"
    SUSPEND_TRADING = "suspend_trading"
    REDUCE_POSITION_SIZE = "reduce_position_size"
    CANCEL_ALL_ORDERS = "cancel_all_orders"
    ALERT_ONLY = "alert_only"


class EmergencyRiskControl:
    """緊急風控措施管理器"""
    
    def __init__(self, broker: BrokerBase):
        """
        初始化緊急風控措施管理器

        Args:
            broker (BrokerBase): 券商適配器
        """
        self.broker = broker
        self.action_executor = EmergencyActionExecutor(broker)
        self.event_manager = EmergencyEventManager()

        # 緊急狀態
        self.emergency_active = False
        self.trading_suspended = False
        self.emergency_level = EmergencyLevel.LOW

        # 緊急措施配置
        self.emergency_config = {
            EmergencyLevel.LOW: [EmergencyAction.ALERT_ONLY],
            EmergencyLevel.MEDIUM: [EmergencyAction.ALERT_ONLY, EmergencyAction.REDUCE_POSITION_SIZE],
            EmergencyLevel.HIGH: [EmergencyAction.SUSPEND_TRADING, EmergencyAction.CANCEL_ALL_ORDERS],
            EmergencyLevel.CRITICAL: [EmergencyAction.CLOSE_ALL_POSITIONS, EmergencyAction.SUSPEND_TRADING],
        }
        
        # 線程安全
        self._emergency_lock = threading.Lock()
        
        # 回調函數
        self.on_emergency_triggered: Optional[Callable] = None
        self.on_positions_closed: Optional[Callable] = None
        self.on_trading_suspended: Optional[Callable] = None
        self.on_emergency_resolved: Optional[Callable] = None
    
    def trigger_emergency(
        self, 
        level: EmergencyLevel, 
        reason: str,
        custom_actions: Optional[List[EmergencyAction]] = None
    ) -> Dict[str, Any]:
        """
        觸發緊急措施
        
        Args:
            level (EmergencyLevel): 緊急級別
            reason (str): 觸發原因
            custom_actions (List[EmergencyAction], optional): 自定義行動
            
        Returns:
            Dict[str, Any]: 執行結果
        """
        try:
            with self._emergency_lock:
                self.emergency_active = True
                self.emergency_level = level
                
                # 記錄緊急事件
                event = self.event_manager.create_event(
                    "emergency_triggered",
                    level,
                    reason,
                    {"custom_actions": custom_actions}
                )
                
                # 確定要執行的行動
                actions = custom_actions if custom_actions else self.emergency_config[level]
                
                # 執行緊急措施
                results = {}
                for action in actions:
                    result = self._execute_emergency_action(action, reason)
                    results[action.value] = result
                
                # 調用回調函數
                if self.on_emergency_triggered:
                    self.on_emergency_triggered({
                        "level": level,
                        "reason": reason,
                        "actions": actions,
                        "results": results,
                        "timestamp": datetime.now(),
                    })
                
                logger.critical(f"緊急風控措施已觸發 - 級別: {level.value}, 原因: {reason}")
                
                return {
                    "success": True,
                    "level": level.value,
                    "reason": reason,
                    "actions_executed": [action.value for action in actions],
                    "results": results,
                    "timestamp": datetime.now(),
                }
                
        except Exception as e:
            logger.exception(f"觸發緊急措施失敗: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(),
            }
    
    def close_all_positions(self, reason: str = "緊急平倉") -> Dict[str, Any]:
        """
        一鍵全部平倉

        Args:
            reason (str): 平倉原因

        Returns:
            Dict[str, Any]: 平倉結果
        """
        try:
            result = self.action_executor.close_all_positions(reason)

            # 記錄事件
            self.event_manager.create_event(
                "positions_closed",
                self.emergency_level,
                reason,
                {
                    "closed_count": len(result.get("closed_positions", [])),
                    "failed_count": len(result.get("failed_positions", [])),
                    "result": result,
                }
            )

            # 調用回調函數
            if self.on_positions_closed and result.get("success"):
                self.on_positions_closed({
                    "closed_positions": result.get("closed_positions", []),
                    "failed_positions": result.get("failed_positions", []),
                    "reason": reason,
                    "timestamp": datetime.now(),
                })

            return result

        except Exception as e:
            logger.exception(f"一鍵全部平倉失敗: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(),
            }
    
    def suspend_trading(self, reason: str = "緊急暫停交易") -> Dict[str, Any]:
        """
        暫停交易

        Args:
            reason (str): 暫停原因

        Returns:
            Dict[str, Any]: 暫停結果
        """
        try:
            with self._emergency_lock:
                self.trading_suspended = True

                # 取消所有未成交訂單
                cancel_result = self.action_executor.cancel_all_orders()

                # 記錄事件
                self.event_manager.create_event(
                    "trading_suspended",
                    self.emergency_level,
                    reason,
                    {"cancelled_orders": cancel_result}
                )

                # 調用回調函數
                if self.on_trading_suspended:
                    self.on_trading_suspended({
                        "reason": reason,
                        "cancelled_orders": cancel_result,
                        "timestamp": datetime.now(),
                    })

                logger.critical(f"交易已暫停 - 原因: {reason}")

                return {
                    "success": True,
                    "message": f"交易已暫停 - {reason}",
                    "cancelled_orders": cancel_result,
                    "timestamp": datetime.now(),
                }

        except Exception as e:
            logger.exception(f"暫停交易失敗: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(),
            }
    
    def resume_trading(self, reason: str = "恢復交易") -> Dict[str, Any]:
        """
        恢復交易
        
        Args:
            reason (str): 恢復原因
            
        Returns:
            Dict[str, Any]: 恢復結果
        """
        try:
            with self._emergency_lock:
                self.trading_suspended = False
                self.emergency_active = False
                self.emergency_level = EmergencyLevel.LOW
                
                # 記錄事件
                self.event_manager.create_event(
                    "trading_resumed",
                    EmergencyLevel.LOW,
                    reason,
                    {}
                )
                
                # 調用回調函數
                if self.on_emergency_resolved:
                    self.on_emergency_resolved({
                        "reason": reason,
                        "timestamp": datetime.now(),
                    })
                
                logger.info(f"交易已恢復 - 原因: {reason}")
                
                return {
                    "success": True,
                    "message": f"交易已恢復 - {reason}",
                    "timestamp": datetime.now(),
                }
                
        except Exception as e:
            logger.exception(f"恢復交易失敗: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(),
            }

    def get_emergency_status(self) -> Dict[str, Any]:
        """
        獲取緊急狀態

        Returns:
            Dict[str, Any]: 緊急狀態
        """
        with self._emergency_lock:
            return {
                "emergency_active": self.emergency_active,
                "trading_suspended": self.trading_suspended,
                "emergency_level": self.emergency_level.value,
                "last_event": self.event_manager.get_latest_event(),
            }

    def get_emergency_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        獲取緊急事件記錄

        Args:
            limit (int): 限制數量

        Returns:
            List[Dict[str, Any]]: 緊急事件記錄
        """
        return self.event_manager.get_events(limit)

    def _execute_emergency_action(self, action: EmergencyAction, reason: str) -> Dict[str, Any]:
        """
        執行緊急行動

        Args:
            action (EmergencyAction): 緊急行動
            reason (str): 執行原因

        Returns:
            Dict[str, Any]: 執行結果
        """
        try:
            if action == EmergencyAction.CLOSE_ALL_POSITIONS:
                return self.close_all_positions(reason)

            elif action == EmergencyAction.SUSPEND_TRADING:
                return self.suspend_trading(reason)

            elif action == EmergencyAction.CANCEL_ALL_ORDERS:
                return self.action_executor.cancel_all_orders()

            elif action == EmergencyAction.REDUCE_POSITION_SIZE:
                return self.action_executor.reduce_position_sizes(0.5, reason)

            elif action == EmergencyAction.ALERT_ONLY:
                return {"success": True, "message": "僅警報，無需執行行動"}

            else:
                return {"success": False, "error": f"不支援的緊急行動: {action}"}

        except Exception as e:
            logger.exception(f"執行緊急行動失敗 [{action.value}]: {e}")
            return {"success": False, "error": str(e)}

    def get_event_statistics(self) -> Dict[str, Any]:
        """
        獲取事件統計

        Returns:
            Dict[str, Any]: 事件統計信息
        """
        return self.event_manager.get_event_statistics()
