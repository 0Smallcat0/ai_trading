"""
最大虧損警報管理器

此模組提供最大虧損警報功能，包括：
- 實時虧損監控
- 多級警報系統
- 自動停損觸發
- 虧損統計分析
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from src.execution.broker_base import BrokerBase

# 設定日誌
logger = logging.getLogger("risk.live.loss_alert")


class AlertLevel(Enum):
    """警報級別枚舉"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class LossType(Enum):
    """虧損類型枚舉"""
    UNREALIZED = "unrealized"  # 未實現虧損
    REALIZED = "realized"  # 已實現虧損
    TOTAL = "total"  # 總虧損
    DAILY = "daily"  # 日虧損


class LossAlertManager:
    """最大虧損警報管理器"""
    
    def __init__(self, broker: BrokerBase):
        """
        初始化最大虧損警報管理器
        
        Args:
            broker (BrokerBase): 券商適配器
        """
        self.broker = broker
        
        # 警報參數
        self.alert_params = {
            "max_unrealized_loss_percent": 0.05,  # 最大未實現虧損 5%
            "max_realized_loss_percent": 0.03,  # 最大已實現虧損 3%
            "max_total_loss_percent": 0.08,  # 最大總虧損 8%
            "max_daily_loss_amount": 50000,  # 最大日虧損金額
            "warning_threshold_percent": 0.7,  # 警告閾值 70%
            "critical_threshold_percent": 0.85,  # 危險閾值 85%
            "emergency_threshold_percent": 0.95,  # 緊急閾值 95%
        }
        
        # 虧損狀態
        self.loss_status = {
            "unrealized_loss": 0.0,
            "realized_loss": 0.0,
            "total_loss": 0.0,
            "daily_loss": 0.0,
            "account_value": 0.0,
            "last_update": None,
        }
        
        # 警報記錄
        self.alerts: List[Dict[str, Any]] = []
        self.max_alerts_size = 500
        
        # 虧損歷史
        self.loss_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        
        # 監控線程
        self._monitor_thread = None
        self._monitoring = False
        self._monitor_lock = threading.Lock()
        
        # 回調函數
        self.on_loss_alert: Optional[Callable] = None
        self.on_emergency_stop: Optional[Callable] = None
        self.on_loss_threshold_reached: Optional[Callable] = None
        
        # 自動停損設定
        self.auto_stop_enabled = True
        self.emergency_stop_triggered = False
    
    def start_monitoring(self):
        """開始監控"""
        if self._monitoring:
            logger.warning("虧損警報監控已經在運行")
            return
            
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="LossAlertMonitor"
        )
        self._monitor_thread.start()
        logger.info("最大虧損警報監控已啟動")
    
    def stop_monitoring(self):
        """停止監控"""
        self._monitoring = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        logger.info("最大虧損警報監控已停止")
    
    def get_loss_status(self) -> Dict[str, Any]:
        """
        獲取虧損狀態
        
        Returns:
            Dict[str, Any]: 虧損狀態
        """
        with self._monitor_lock:
            status = self.loss_status.copy()
            
            # 計算虧損比例
            account_value = status["account_value"]
            if account_value > 0:
                status["unrealized_loss_percent"] = status["unrealized_loss"] / account_value
                status["realized_loss_percent"] = status["realized_loss"] / account_value
                status["total_loss_percent"] = status["total_loss"] / account_value
            else:
                status["unrealized_loss_percent"] = 0
                status["realized_loss_percent"] = 0
                status["total_loss_percent"] = 0
            
            # 計算警報級別
            status["alert_levels"] = self._calculate_alert_levels(status)
            
            return status
    
    def get_loss_summary(self) -> Dict[str, Any]:
        """
        獲取虧損摘要
        
        Returns:
            Dict[str, Any]: 虧損摘要
        """
        with self._monitor_lock:
            status = self.loss_status.copy()
            account_value = status["account_value"]
            
            # 計算距離警報閾值的安全邊際
            safety_margins = {}
            if account_value > 0:
                for loss_type in ["unrealized", "realized", "total"]:
                    current_percent = status[f"{loss_type}_loss"] / account_value
                    max_percent = self.alert_params[f"max_{loss_type}_loss_percent"]
                    safety_margins[f"{loss_type}_safety_margin"] = max(0, max_percent - current_percent)
            
            return {
                "current_status": status,
                "safety_margins": safety_margins,
                "alert_count_today": len([a for a in self.alerts if a["timestamp"].date() == datetime.now().date()]),
                "emergency_stop_triggered": self.emergency_stop_triggered,
                "auto_stop_enabled": self.auto_stop_enabled,
            }
    
    def get_alerts(self, level: Optional[AlertLevel] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        獲取警報記錄
        
        Args:
            level (AlertLevel, optional): 警報級別過濾
            limit (int): 限制數量
            
        Returns:
            List[Dict[str, Any]]: 警報記錄
        """
        with self._monitor_lock:
            alerts = self.alerts.copy()
            
            if level:
                alerts = [a for a in alerts if a["level"] == level.value]
            
            return alerts[-limit:] if alerts else []
    
    def get_loss_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        獲取虧損歷史
        
        Args:
            hours (int): 小時數
            
        Returns:
            List[Dict[str, Any]]: 虧損歷史
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._monitor_lock:
            filtered_history = []
            for record in self.loss_history:
                if record.get("timestamp") and record["timestamp"] > cutoff_time:
                    filtered_history.append(record)
            
            return filtered_history
    
    def update_alert_params(self, **kwargs) -> bool:
        """
        更新警報參數
        
        Args:
            **kwargs: 參數
            
        Returns:
            bool: 是否更新成功
        """
        try:
            for key, value in kwargs.items():
                if key in self.alert_params:
                    self.alert_params[key] = value
                    logger.info(f"已更新虧損警報參數 {key}: {value}")
            return True
        except Exception as e:
            logger.exception(f"更新虧損警報參數失敗: {e}")
            return False
    
    def reset_emergency_stop(self) -> bool:
        """
        重置緊急停損狀態
        
        Returns:
            bool: 是否重置成功
        """
        try:
            self.emergency_stop_triggered = False
            logger.info("已重置緊急停損狀態")
            return True
        except Exception as e:
            logger.exception(f"重置緊急停損狀態失敗: {e}")
            return False
    
    def force_update(self) -> bool:
        """
        強制更新虧損狀態
        
        Returns:
            bool: 是否更新成功
        """
        try:
            return self._update_loss_status()
        except Exception as e:
            logger.exception(f"強制更新虧損狀態失敗: {e}")
            return False
    
    def _monitor_loop(self):
        """監控循環"""
        while self._monitoring:
            try:
                self._update_loss_status()
                time.sleep(5)  # 每 5 秒檢查一次
                
            except Exception as e:
                logger.exception(f"虧損警報監控循環錯誤: {e}")
                time.sleep(10)
    
    def _update_loss_status(self) -> bool:
        """
        更新虧損狀態
        
        Returns:
            bool: 是否更新成功
        """
        try:
            # 獲取帳戶資訊
            account_info = self.broker.get_account_info()
            if not account_info:
                return False
            
            # 獲取持倉資訊
            positions = self.broker.get_positions()
            
            # 計算未實現虧損
            unrealized_loss = 0.0
            if positions:
                for symbol, position in positions.items():
                    pnl = position.get("unrealized_pnl", 0)
                    if pnl < 0:  # 只計算虧損
                        unrealized_loss += abs(pnl)
            
            # 獲取已實現虧損 (這裡需要從交易記錄中計算)
            realized_loss = self._calculate_realized_loss()
            
            # 計算總虧損
            total_loss = unrealized_loss + realized_loss
            
            # 計算日虧損 (簡化版本)
            daily_loss = self._calculate_daily_loss()
            
            # 更新虧損狀態
            with self._monitor_lock:
                old_status = self.loss_status.copy()
                
                self.loss_status.update({
                    "unrealized_loss": unrealized_loss,
                    "realized_loss": realized_loss,
                    "total_loss": total_loss,
                    "daily_loss": daily_loss,
                    "account_value": account_info.get("total_value", 0),
                    "last_update": datetime.now(),
                })
                
                # 記錄虧損歷史
                self._record_loss_history()
                
                # 檢查警報條件
                self._check_alert_conditions(old_status)
            
            return True
            
        except Exception as e:
            logger.exception(f"更新虧損狀態失敗: {e}")
            return False
    
    def _calculate_realized_loss(self) -> float:
        """計算已實現虧損"""
        # 這裡應該從交易記錄中計算已實現虧損
        # 簡化版本，返回 0
        return 0.0
    
    def _calculate_daily_loss(self) -> float:
        """計算日虧損"""
        # 這裡應該計算今日的總虧損
        # 簡化版本，返回未實現虧損
        return self.loss_status.get("unrealized_loss", 0)
    
    def _record_loss_history(self):
        """記錄虧損歷史"""
        try:
            record = {
                "timestamp": datetime.now(),
                **self.loss_status
            }
            
            self.loss_history.append(record)
            
            # 保持歷史記錄在合理範圍內
            if len(self.loss_history) > self.max_history_size:
                self.loss_history = self.loss_history[-self.max_history_size//2:]
                
        except Exception as e:
            logger.exception(f"記錄虧損歷史失敗: {e}")
    
    def _check_alert_conditions(self, old_status: Dict[str, Any]):
        """
        檢查警報條件
        
        Args:
            old_status (Dict[str, Any]): 舊的虧損狀態
        """
        try:
            current_status = self.loss_status
            account_value = current_status["account_value"]
            
            if account_value <= 0:
                return
            
            # 檢查各種虧損類型
            loss_types = [
                ("unrealized", "未實現虧損"),
                ("realized", "已實現虧損"),
                ("total", "總虧損"),
            ]
            
            for loss_type, loss_name in loss_types:
                current_loss = current_status[f"{loss_type}_loss"]
                old_loss = old_status.get(f"{loss_type}_loss", 0)
                max_loss = self.alert_params[f"max_{loss_type}_loss_percent"] * account_value
                
                loss_percent = current_loss / account_value
                max_percent = self.alert_params[f"max_{loss_type}_loss_percent"]
                
                # 檢查是否觸發緊急停損
                if (loss_percent >= max_percent * self.alert_params["emergency_threshold_percent"] and
                    not self.emergency_stop_triggered):
                    
                    self._trigger_emergency_stop(loss_type, loss_name, loss_percent)
                
                # 檢查是否觸發危險警報
                elif loss_percent >= max_percent * self.alert_params["critical_threshold_percent"]:
                    if old_loss < max_loss * self.alert_params["critical_threshold_percent"]:
                        self._create_alert(
                            AlertLevel.CRITICAL,
                            f"{loss_name}達到危險水平",
                            f"{loss_name}: {current_loss:,.0f} ({loss_percent:.1%})",
                            {"loss_type": loss_type, "loss_amount": current_loss, "loss_percent": loss_percent}
                        )
                
                # 檢查是否觸發警告
                elif loss_percent >= max_percent * self.alert_params["warning_threshold_percent"]:
                    if old_loss < max_loss * self.alert_params["warning_threshold_percent"]:
                        self._create_alert(
                            AlertLevel.WARNING,
                            f"{loss_name}達到警告水平",
                            f"{loss_name}: {current_loss:,.0f} ({loss_percent:.1%})",
                            {"loss_type": loss_type, "loss_amount": current_loss, "loss_percent": loss_percent}
                        )
            
            # 檢查日虧損金額
            daily_loss = current_status["daily_loss"]
            max_daily_loss = self.alert_params["max_daily_loss_amount"]
            
            if daily_loss > max_daily_loss:
                old_daily_loss = old_status.get("daily_loss", 0)
                if old_daily_loss <= max_daily_loss:
                    self._create_alert(
                        AlertLevel.CRITICAL,
                        "日虧損超過限制",
                        f"日虧損: {daily_loss:,.0f}",
                        {"loss_type": "daily", "loss_amount": daily_loss}
                    )
                    
        except Exception as e:
            logger.exception(f"檢查警報條件失敗: {e}")

    def _trigger_emergency_stop(self, loss_type: str, loss_name: str, loss_percent: float):
        """觸發緊急停損"""
        try:
            self.emergency_stop_triggered = True

            alert_data = {
                "loss_type": loss_type,
                "loss_name": loss_name,
                "loss_percent": loss_percent,
                "emergency_stop": True,
            }

            self._create_alert(
                AlertLevel.EMERGENCY,
                f"緊急停損觸發 - {loss_name}",
                f"{loss_name}: {loss_percent:.1%}，已觸發緊急停損",
                alert_data
            )

            logger.critical(f"緊急停損觸發 - {loss_name}: {loss_percent:.1%}")

            # 調用緊急停損回調
            if self.on_emergency_stop:
                self.on_emergency_stop(alert_data)

        except Exception as e:
            logger.exception(f"觸發緊急停損失敗: {e}")

    def _create_alert(self, level: AlertLevel, title: str, message: str, data: Dict[str, Any]):
        """
        創建警報

        Args:
            level (AlertLevel): 警報級別
            title (str): 警報標題
            message (str): 警報訊息
            data (Dict[str, Any]): 警報數據
        """
        try:
            alert = {
                "timestamp": datetime.now(),
                "level": level.value,
                "title": title,
                "message": message,
                "data": data,
            }

            self.alerts.append(alert)

            # 保持警報記錄在合理範圍內
            if len(self.alerts) > self.max_alerts_size:
                self.alerts = self.alerts[-self.max_alerts_size//2:]

            logger.warning(f"虧損警報 [{level.value.upper()}]: {title} - {message}")

            # 調用警報回調
            if self.on_loss_alert:
                self.on_loss_alert(alert)

            # 調用閾值達到回調
            if level in [AlertLevel.WARNING, AlertLevel.CRITICAL, AlertLevel.EMERGENCY]:
                if self.on_loss_threshold_reached:
                    self.on_loss_threshold_reached(alert)

        except Exception as e:
            logger.exception(f"創建警報失敗: {e}")

    def _calculate_alert_levels(self, status: Dict[str, Any]) -> Dict[str, str]:
        """
        計算警報級別

        Args:
            status (Dict[str, Any]): 虧損狀態

        Returns:
            Dict[str, str]: 各類型虧損的警報級別
        """
        try:
            alert_levels = {}
            account_value = status["account_value"]

            if account_value <= 0:
                return {
                    "unrealized": AlertLevel.INFO.value,
                    "realized": AlertLevel.INFO.value,
                    "total": AlertLevel.INFO.value,
                    "daily": AlertLevel.INFO.value,
                }

            # 計算各類型虧損的警報級別
            loss_types = ["unrealized", "realized", "total"]

            for loss_type in loss_types:
                loss_amount = status[f"{loss_type}_loss"]
                loss_percent = loss_amount / account_value
                max_percent = self.alert_params[f"max_{loss_type}_loss_percent"]

                if loss_percent >= max_percent * self.alert_params["emergency_threshold_percent"]:
                    alert_levels[loss_type] = AlertLevel.EMERGENCY.value
                elif loss_percent >= max_percent * self.alert_params["critical_threshold_percent"]:
                    alert_levels[loss_type] = AlertLevel.CRITICAL.value
                elif loss_percent >= max_percent * self.alert_params["warning_threshold_percent"]:
                    alert_levels[loss_type] = AlertLevel.WARNING.value
                else:
                    alert_levels[loss_type] = AlertLevel.INFO.value

            # 計算日虧損警報級別
            daily_loss = status["daily_loss"]
            max_daily_loss = self.alert_params["max_daily_loss_amount"]

            if daily_loss > max_daily_loss:
                alert_levels["daily"] = AlertLevel.CRITICAL.value
            elif daily_loss > max_daily_loss * 0.8:
                alert_levels["daily"] = AlertLevel.WARNING.value
            else:
                alert_levels["daily"] = AlertLevel.INFO.value

            return alert_levels

        except Exception as e:
            logger.exception(f"計算警報級別失敗: {e}")
            return {
                "unrealized": AlertLevel.INFO.value,
                "realized": AlertLevel.INFO.value,
                "total": AlertLevel.INFO.value,
                "daily": AlertLevel.INFO.value,
            }
