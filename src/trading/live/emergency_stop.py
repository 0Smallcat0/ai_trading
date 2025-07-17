"""
緊急停損管理器

此模組提供緊急停損功能，包括：
- 緊急停損按鈕
- 自動停損觸發
- 停損策略管理
- 風險監控
"""

import logging
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from src.execution.broker_base import BrokerBase, Order, OrderType, OrderStatus

# 設定日誌
logger = logging.getLogger("trading.live.emergency_stop")


class StopLossType(Enum):
    """停損類型枚舉"""
    EMERGENCY = "emergency"  # 緊急停損
    AUTO = "auto"  # 自動停損
    MANUAL = "manual"  # 手動停損
    TRAILING = "trailing"  # 追蹤停損


class EmergencyStopManager:
    """緊急停損管理器"""
    
    def __init__(self, broker: BrokerBase):
        """
        初始化緊急停損管理器
        
        Args:
            broker (BrokerBase): 券商適配器
        """
        self.broker = broker
        
        # 停損狀態
        self.emergency_stop_active = False
        self.auto_stop_enabled = True
        
        # 停損參數
        self.emergency_stop_params = {
            "max_loss_percent": 0.05,  # 最大虧損 5%
            "max_daily_loss": 50000,   # 最大日虧損
            "position_loss_percent": 0.1,  # 單一持倉最大虧損 10%
        }
        
        # 追蹤停損參數
        self.trailing_stop_params = {
            "enabled": False,
            "trail_percent": 0.02,  # 追蹤停損 2%
            "min_profit_percent": 0.01,  # 最小獲利 1% 才啟動追蹤
        }
        
        # 停損記錄
        self.stop_loss_history: List[Dict[str, Any]] = []
        
        # 監控線程
        self._monitor_thread = None
        self._monitoring = False
        self._monitor_lock = threading.Lock()
        
        # 回調函數
        self.on_emergency_stop: Optional[Callable] = None
        self.on_auto_stop_triggered: Optional[Callable] = None
        self.on_trailing_stop_triggered: Optional[Callable] = None
        self.on_stop_loss_error: Optional[Callable] = None
    
    def start_monitoring(self):
        """開始監控"""
        if self._monitoring:
            logger.warning("停損監控已經在運行")
            return
            
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="EmergencyStopMonitor"
        )
        self._monitor_thread.start()
        logger.info("緊急停損監控已啟動")
    
    def stop_monitoring(self):
        """停止監控"""
        self._monitoring = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        logger.info("緊急停損監控已停止")
    
    def emergency_stop_all(self, reason: str = "手動觸發緊急停損") -> Dict[str, Any]:
        """
        緊急停損所有持倉
        
        Args:
            reason (str): 停損原因
            
        Returns:
            Dict[str, Any]: 執行結果
        """
        try:
            with self._monitor_lock:
                if self.emergency_stop_active:
                    return {
                        "success": False,
                        "message": "緊急停損已經在執行中",
                    }
                
                self.emergency_stop_active = True
            
            logger.critical(f"觸發緊急停損: {reason}")
            
            # 獲取所有持倉
            positions = self.broker.get_positions()
            
            if not positions:
                self.emergency_stop_active = False
                return {
                    "success": True,
                    "message": "沒有持倉需要停損",
                    "positions_closed": 0,
                }
            
            # 執行緊急平倉
            closed_positions = []
            failed_positions = []
            
            for symbol, position in positions.items():
                try:
                    result = self._execute_stop_loss(
                        symbol, position, StopLossType.EMERGENCY, reason
                    )
                    
                    if result["success"]:
                        closed_positions.append(result)
                    else:
                        failed_positions.append(result)
                        
                except Exception as e:
                    logger.exception(f"緊急停損 {symbol} 時發生錯誤: {e}")
                    failed_positions.append({
                        "symbol": symbol,
                        "success": False,
                        "error": str(e),
                    })
            
            # 記錄停損操作
            stop_record = {
                "timestamp": datetime.now(),
                "type": StopLossType.EMERGENCY,
                "reason": reason,
                "total_positions": len(positions),
                "closed_positions": len(closed_positions),
                "failed_positions": len(failed_positions),
                "details": closed_positions + failed_positions,
            }
            self.stop_loss_history.append(stop_record)
            
            self.emergency_stop_active = False
            
            success = len(failed_positions) == 0
            message = f"緊急停損完成，成功 {len(closed_positions)} 個，失敗 {len(failed_positions)} 個"
            
            logger.info(message)
            
            # 調用回調函數
            if self.on_emergency_stop:
                self.on_emergency_stop(stop_record)
            
            return {
                "success": success,
                "message": message,
                "positions_closed": len(closed_positions),
                "positions_failed": len(failed_positions),
                "closed_positions": closed_positions,
                "failed_positions": failed_positions,
            }
            
        except Exception as e:
            self.emergency_stop_active = False
            logger.exception(f"緊急停損失敗: {e}")
            
            if self.on_stop_loss_error:
                self.on_stop_loss_error("emergency_stop_all", str(e))
            
            return {
                "success": False,
                "message": f"緊急停損失敗: {e}",
                "error": str(e),
            }
    
    def set_auto_stop_loss(self, symbol: str, stop_price: float, 
                          stop_type: StopLossType = StopLossType.AUTO) -> Dict[str, Any]:
        """
        設定自動停損
        
        Args:
            symbol (str): 股票代號
            stop_price (float): 停損價格
            stop_type (StopLossType): 停損類型
            
        Returns:
            Dict[str, Any]: 設定結果
        """
        try:
            # 獲取當前持倉
            positions = self.broker.get_positions()
            
            if symbol not in positions:
                return {
                    "success": False,
                    "message": f"沒有找到 {symbol} 的持倉",
                }
            
            position = positions[symbol]
            current_quantity = position.get("quantity", 0)
            current_price = position.get("current_price", 0)
            
            if current_quantity == 0:
                return {
                    "success": False,
                    "message": f"{symbol} 持倉數量為 0",
                }
            
            # 創建停損訂單
            action = "sell" if current_quantity > 0 else "buy"
            
            order = Order(
                stock_id=symbol,
                action=action,
                quantity=abs(current_quantity),
                order_type=OrderType.STOP,
                stop_price=stop_price,
                time_in_force="gtc",  # 有效直到取消
            )
            
            # 提交停損訂單
            order_id = self.broker.place_order(order)
            
            if order_id:
                logger.info(f"自動停損訂單已設定: {symbol} 停損價 {stop_price}, 訂單ID: {order_id}")
                
                return {
                    "success": True,
                    "message": "自動停損訂單已設定",
                    "symbol": symbol,
                    "stop_price": stop_price,
                    "order_id": order_id,
                    "stop_type": stop_type.value,
                }
            else:
                return {
                    "success": False,
                    "message": "設定自動停損訂單失敗",
                }
                
        except Exception as e:
            logger.exception(f"設定自動停損失敗 ({symbol}): {e}")
            return {
                "success": False,
                "message": f"設定自動停損失敗: {e}",
                "error": str(e),
            }
    
    def update_emergency_params(self, **kwargs) -> bool:
        """
        更新緊急停損參數
        
        Args:
            **kwargs: 參數
            
        Returns:
            bool: 是否更新成功
        """
        try:
            for key, value in kwargs.items():
                if key in self.emergency_stop_params:
                    self.emergency_stop_params[key] = value
                    logger.info(f"已更新緊急停損參數 {key}: {value}")
            return True
        except Exception as e:
            logger.exception(f"更新緊急停損參數失敗: {e}")
            return False
    
    def update_trailing_params(self, **kwargs) -> bool:
        """
        更新追蹤停損參數
        
        Args:
            **kwargs: 參數
            
        Returns:
            bool: 是否更新成功
        """
        try:
            for key, value in kwargs.items():
                if key in self.trailing_stop_params:
                    self.trailing_stop_params[key] = value
                    logger.info(f"已更新追蹤停損參數 {key}: {value}")
            return True
        except Exception as e:
            logger.exception(f"更新追蹤停損參數失敗: {e}")
            return False
    
    def get_stop_loss_status(self) -> Dict[str, Any]:
        """
        獲取停損狀態
        
        Returns:
            Dict[str, Any]: 停損狀態
        """
        return {
            "emergency_stop_active": self.emergency_stop_active,
            "auto_stop_enabled": self.auto_stop_enabled,
            "monitoring": self._monitoring,
            "emergency_params": self.emergency_stop_params.copy(),
            "trailing_params": self.trailing_stop_params.copy(),
            "stop_loss_count": len(self.stop_loss_history),
        }
    
    def get_stop_loss_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        獲取停損歷史
        
        Args:
            limit (int): 限制數量
            
        Returns:
            List[Dict[str, Any]]: 停損歷史
        """
        return self.stop_loss_history[-limit:] if self.stop_loss_history else []

    def _monitor_loop(self):
        """監控循環"""
        while self._monitoring:
            try:
                if self.auto_stop_enabled and not self.emergency_stop_active:
                    self._check_auto_stop_conditions()

                    if self.trailing_stop_params["enabled"]:
                        self._check_trailing_stop()

                time.sleep(1)  # 每秒檢查一次

            except Exception as e:
                logger.exception(f"停損監控循環錯誤: {e}")
                time.sleep(5)

    def _check_auto_stop_conditions(self):
        """檢查自動停損條件"""
        try:
            # 獲取帳戶資訊
            account_info = self.broker.get_account_info()
            positions = self.broker.get_positions()

            if not account_info or not positions:
                return

            # 檢查總虧損
            total_pnl = 0
            for symbol, position in positions.items():
                quantity = position.get("quantity", 0)
                avg_price = position.get("avg_price", 0)
                current_price = position.get("current_price", 0)

                if avg_price > 0 and current_price > 0:
                    pnl = (current_price - avg_price) * quantity
                    total_pnl += pnl

            # 檢查總虧損比例
            total_value = account_info.get("total_value", 0)
            if total_value > 0:
                loss_percent = -total_pnl / total_value

                if loss_percent > self.emergency_stop_params["max_loss_percent"]:
                    logger.warning(f"總虧損比例 {loss_percent:.2%} 超過閾值，觸發緊急停損")
                    self.emergency_stop_all(f"總虧損比例超過 {self.emergency_stop_params['max_loss_percent']:.2%}")
                    return

            # 檢查日虧損
            if -total_pnl > self.emergency_stop_params["max_daily_loss"]:
                logger.warning(f"日虧損 {-total_pnl:.2f} 超過閾值，觸發緊急停損")
                self.emergency_stop_all(f"日虧損超過 {self.emergency_stop_params['max_daily_loss']}")
                return

            # 檢查單一持倉虧損
            for symbol, position in positions.items():
                quantity = position.get("quantity", 0)
                avg_price = position.get("avg_price", 0)
                current_price = position.get("current_price", 0)

                if avg_price > 0 and current_price > 0 and quantity != 0:
                    loss_percent = (current_price - avg_price) / avg_price
                    if quantity < 0:  # 空頭持倉
                        loss_percent = -loss_percent

                    if loss_percent < -self.emergency_stop_params["position_loss_percent"]:
                        logger.warning(f"{symbol} 虧損比例 {loss_percent:.2%} 超過閾值，觸發停損")
                        self._execute_stop_loss(
                            symbol, position, StopLossType.AUTO,
                            f"單一持倉虧損超過 {self.emergency_stop_params['position_loss_percent']:.2%}"
                        )

        except Exception as e:
            logger.exception(f"檢查自動停損條件失敗: {e}")

    def _check_trailing_stop(self):
        """檢查追蹤停損"""
        try:
            positions = self.broker.get_positions()

            for symbol, position in positions.items():
                quantity = position.get("quantity", 0)
                avg_price = position.get("avg_price", 0)
                current_price = position.get("current_price", 0)
                high_price = position.get("high_price", current_price)  # 需要追蹤最高價

                if avg_price > 0 and current_price > 0 and quantity != 0:
                    # 計算獲利比例
                    profit_percent = (current_price - avg_price) / avg_price
                    if quantity < 0:  # 空頭持倉
                        profit_percent = -profit_percent

                    # 只有獲利超過最小獲利比例才啟動追蹤停損
                    if profit_percent > self.trailing_stop_params["min_profit_percent"]:
                        # 計算追蹤停損價格
                        if quantity > 0:  # 多頭持倉
                            trail_stop_price = high_price * (1 - self.trailing_stop_params["trail_percent"])
                            if current_price <= trail_stop_price:
                                logger.info(f"{symbol} 觸發追蹤停損，當前價 {current_price}, 停損價 {trail_stop_price}")
                                self._execute_stop_loss(
                                    symbol, position, StopLossType.TRAILING,
                                    f"追蹤停損觸發，停損價 {trail_stop_price}"
                                )
                        else:  # 空頭持倉
                            trail_stop_price = high_price * (1 + self.trailing_stop_params["trail_percent"])
                            if current_price >= trail_stop_price:
                                logger.info(f"{symbol} 觸發追蹤停損，當前價 {current_price}, 停損價 {trail_stop_price}")
                                self._execute_stop_loss(
                                    symbol, position, StopLossType.TRAILING,
                                    f"追蹤停損觸發，停損價 {trail_stop_price}"
                                )

        except Exception as e:
            logger.exception(f"檢查追蹤停損失敗: {e}")

    def _execute_stop_loss(self, symbol: str, position: Dict[str, Any],
                          stop_type: StopLossType, reason: str) -> Dict[str, Any]:
        """
        執行停損

        Args:
            symbol (str): 股票代號
            position (Dict[str, Any]): 持倉資訊
            stop_type (StopLossType): 停損類型
            reason (str): 停損原因

        Returns:
            Dict[str, Any]: 執行結果
        """
        try:
            quantity = position.get("quantity", 0)
            current_price = position.get("current_price", 0)

            if quantity == 0:
                return {
                    "success": False,
                    "message": f"{symbol} 持倉數量為 0",
                    "symbol": symbol,
                }

            # 確定平倉方向
            action = "sell" if quantity > 0 else "buy"
            close_quantity = abs(quantity)

            # 創建市價停損訂單
            order = Order(
                stock_id=symbol,
                action=action,
                quantity=close_quantity,
                order_type=OrderType.MARKET,  # 使用市價單確保成交
                time_in_force="day",
            )

            # 提交訂單
            order_id = self.broker.place_order(order)

            if order_id:
                logger.info(f"停損訂單已提交: {symbol} {action} {close_quantity}, 訂單ID: {order_id}")

                result = {
                    "success": True,
                    "message": "停損訂單已提交",
                    "symbol": symbol,
                    "order_id": order_id,
                    "action": action,
                    "quantity": close_quantity,
                    "stop_type": stop_type.value,
                    "reason": reason,
                    "timestamp": datetime.now().isoformat(),
                }

                # 調用相應的回調函數
                if stop_type == StopLossType.AUTO and self.on_auto_stop_triggered:
                    self.on_auto_stop_triggered(result)
                elif stop_type == StopLossType.TRAILING and self.on_trailing_stop_triggered:
                    self.on_trailing_stop_triggered(result)

                return result
            else:
                return {
                    "success": False,
                    "message": "提交停損訂單失敗",
                    "symbol": symbol,
                }

        except Exception as e:
            logger.exception(f"執行停損失敗 ({symbol}): {e}")
            return {
                "success": False,
                "message": f"執行停損失敗: {e}",
                "symbol": symbol,
                "error": str(e),
            }
