"""
資金監控基礎模組

此模組提供資金監控的基礎功能，包括：
- 監控線程管理
- 資金狀態更新
- 歷史記錄管理
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable

from src.execution.broker_base import BrokerBase

# 設定日誌
logger = logging.getLogger("risk.live.fund_monitor_base")


class FundMonitorBase:
    """資金監控基礎類別"""
    
    def __init__(self, broker: BrokerBase):
        """
        初始化資金監控基礎
        
        Args:
            broker (BrokerBase): 券商適配器
        """
        self.broker = broker
        
        # 資金狀態
        self.fund_status = {
            "cash": 0.0,
            "buying_power": 0.0,
            "total_value": 0.0,
            "margin_used": 0.0,
            "margin_available": 0.0,
            "margin_usage_rate": 0.0,
            "positions_value": 0.0,
            "unrealized_pnl": 0.0,
            "last_update": None,
        }
        
        # 歷史記錄
        self.fund_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
        
        # 警報記錄
        self.alerts: List[Dict[str, Any]] = []
        self.max_alerts_size = 100
        
        # 監控線程
        self._monitor_thread = None
        self._monitoring = False
        self._monitor_lock = threading.Lock()
        
        # 回調函數
        self.on_fund_update: Optional[Callable] = None
        self.on_alert: Optional[Callable] = None
        self.on_margin_warning: Optional[Callable] = None
        self.on_cash_warning: Optional[Callable] = None
    
    def start_monitoring(self, update_interval: int = 5):
        """
        開始監控
        
        Args:
            update_interval (int): 更新間隔（秒）
        """
        if self._monitoring:
            logger.warning("資金監控已經在運行")
            return
            
        self._monitoring = True
        self.update_interval = update_interval
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="FundMonitor"
        )
        self._monitor_thread.start()
        logger.info("實時資金監控已啟動")
    
    def stop_monitoring(self):
        """停止監控"""
        self._monitoring = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        logger.info("實時資金監控已停止")
    
    def get_fund_status(self) -> Dict[str, Any]:
        """
        獲取資金狀態
        
        Returns:
            Dict[str, Any]: 資金狀態
        """
        with self._monitor_lock:
            return self.fund_status.copy()
    
    def get_fund_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        獲取資金歷史
        
        Args:
            hours (int): 小時數
            
        Returns:
            List[Dict[str, Any]]: 資金歷史
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._monitor_lock:
            filtered_history = []
            for record in self.fund_history:
                if record.get("timestamp") and record["timestamp"] > cutoff_time:
                    filtered_history.append(record)
            
            return filtered_history
    
    def get_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        獲取警報記錄
        
        Args:
            limit (int): 限制數量
            
        Returns:
            List[Dict[str, Any]]: 警報記錄
        """
        with self._monitor_lock:
            return self.alerts[-limit:] if self.alerts else []
    
    def force_update(self) -> bool:
        """
        強制更新資金狀態
        
        Returns:
            bool: 是否更新成功
        """
        try:
            return self._update_fund_status()
        except Exception as e:
            logger.exception(f"強制更新資金狀態失敗: {e}")
            return False
    
    def _monitor_loop(self):
        """監控循環"""
        while self._monitoring:
            try:
                self._update_fund_status()
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.exception(f"資金監控循環錯誤: {e}")
                time.sleep(5)
    
    def _update_fund_status(self) -> bool:
        """
        更新資金狀態
        
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
            
            # 計算持倉價值和未實現盈虧
            positions_value = 0.0
            unrealized_pnl = 0.0
            
            if positions:
                for symbol, position in positions.items():
                    market_value = position.get("market_value", 0)
                    pnl = position.get("unrealized_pnl", 0)
                    
                    positions_value += market_value
                    unrealized_pnl += pnl
            
            # 更新資金狀態
            with self._monitor_lock:
                old_status = self.fund_status.copy()
                
                self.fund_status.update({
                    "cash": account_info.get("cash", 0),
                    "buying_power": account_info.get("buying_power", 0),
                    "total_value": account_info.get("total_value", 0),
                    "margin_used": account_info.get("margin_used", 0),
                    "margin_available": account_info.get("margin_available", 0),
                    "positions_value": positions_value,
                    "unrealized_pnl": unrealized_pnl,
                    "last_update": datetime.now(),
                })
                
                # 計算保證金使用率
                total_margin = self.fund_status["margin_used"] + self.fund_status["margin_available"]
                if total_margin > 0:
                    self.fund_status["margin_usage_rate"] = self.fund_status["margin_used"] / total_margin
                else:
                    self.fund_status["margin_usage_rate"] = 0.0
                
                # 記錄歷史
                self._record_fund_history()
                
                # 檢查警報條件（由子類實現）
                self._check_alert_conditions(old_status)
            
            # 調用回調函數
            if self.on_fund_update:
                self.on_fund_update(self.fund_status.copy())
            
            return True
            
        except Exception as e:
            logger.exception(f"更新資金狀態失敗: {e}")
            return False
    
    def _record_fund_history(self):
        """記錄資金歷史"""
        try:
            record = {
                "timestamp": datetime.now(),
                **self.fund_status
            }
            
            self.fund_history.append(record)
            
            # 保持歷史記錄在合理範圍內
            if len(self.fund_history) > self.max_history_size:
                self.fund_history = self.fund_history[-self.max_history_size//2:]
                
        except Exception as e:
            logger.exception(f"記錄資金歷史失敗: {e}")
    
    def _check_alert_conditions(self, old_status: Dict[str, Any]):
        """
        檢查警報條件（由子類實現）
        
        Args:
            old_status (Dict[str, Any]): 舊的資金狀態
        """
        pass  # 由子類實現具體的警報邏輯
