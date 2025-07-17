"""
持倉管理器

此模組提供持倉管理功能，包括：
- 一鍵平倉功能
- 部分平倉功能
- 持倉監控
- 風險控制
"""

import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from src.execution.broker_base import BrokerBase, Order, OrderType, OrderStatus

# 設定日誌
logger = logging.getLogger("trading.live.position_manager")


class ClosePositionMode(Enum):
    """平倉模式枚舉"""
    ALL = "all"  # 全部平倉
    PARTIAL = "partial"  # 部分平倉
    BY_SYMBOL = "by_symbol"  # 按股票平倉
    BY_PROFIT_LOSS = "by_profit_loss"  # 按盈虧平倉


class PositionManager:
    """持倉管理器"""
    
    def __init__(self, broker: BrokerBase):
        """
        初始化持倉管理器
        
        Args:
            broker (BrokerBase): 券商適配器
        """
        self.broker = broker
        
        # 持倉資訊
        self.positions = {}
        self.position_lock = threading.Lock()
        
        # 平倉記錄
        self.close_orders = {}
        
        # 回調函數
        self.on_position_closed: Optional[Callable] = None
        self.on_close_order_update: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # 風險控制參數
        self.max_loss_percent = 0.1  # 最大虧損比例 10%
        self.enable_risk_control = True
    
    def update_positions(self, positions: Dict[str, Dict[str, Any]]):
        """
        更新持倉資訊
        
        Args:
            positions (Dict[str, Dict[str, Any]]): 持倉資訊
        """
        with self.position_lock:
            self.positions = positions.copy()
            
        logger.debug(f"持倉資訊已更新，共 {len(positions)} 個持倉")
    
    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        獲取持倉資訊
        
        Returns:
            Dict[str, Dict[str, Any]]: 持倉資訊
        """
        with self.position_lock:
            return self.positions.copy()
    
    def close_all_positions(self, confirm: bool = False) -> Dict[str, Any]:
        """
        一鍵平倉所有持倉
        
        Args:
            confirm (bool): 是否確認執行
            
        Returns:
            Dict[str, Any]: 執行結果
        """
        if not confirm:
            return {
                "success": False,
                "message": "需要確認才能執行一鍵平倉",
                "positions_count": len(self.positions),
            }
        
        try:
            with self.position_lock:
                positions_to_close = self.positions.copy()
            
            if not positions_to_close:
                return {
                    "success": True,
                    "message": "沒有持倉需要平倉",
                    "closed_orders": [],
                }
            
            logger.info(f"開始一鍵平倉，共 {len(positions_to_close)} 個持倉")
            
            closed_orders = []
            failed_orders = []
            
            for symbol, position in positions_to_close.items():
                try:
                    result = self._close_position(symbol, position, ClosePositionMode.ALL)
                    if result["success"]:
                        closed_orders.append(result)
                    else:
                        failed_orders.append(result)
                        
                except Exception as e:
                    logger.exception(f"平倉 {symbol} 時發生錯誤: {e}")
                    failed_orders.append({
                        "symbol": symbol,
                        "success": False,
                        "error": str(e),
                    })
            
            # 記錄平倉操作
            close_operation = {
                "timestamp": datetime.now(),
                "mode": ClosePositionMode.ALL,
                "total_positions": len(positions_to_close),
                "successful_orders": len(closed_orders),
                "failed_orders": len(failed_orders),
                "orders": closed_orders + failed_orders,
            }
            
            operation_id = f"close_all_{int(datetime.now().timestamp())}"
            self.close_orders[operation_id] = close_operation
            
            success = len(failed_orders) == 0
            message = f"一鍵平倉完成，成功 {len(closed_orders)} 個，失敗 {len(failed_orders)} 個"
            
            logger.info(message)
            
            return {
                "success": success,
                "message": message,
                "operation_id": operation_id,
                "closed_orders": closed_orders,
                "failed_orders": failed_orders,
            }
            
        except Exception as e:
            logger.exception(f"一鍵平倉失敗: {e}")
            if self.on_error:
                self.on_error("close_all_positions", str(e))
            return {
                "success": False,
                "message": f"一鍵平倉失敗: {e}",
                "error": str(e),
            }
    
    def close_position_by_symbol(self, symbol: str, quantity: Optional[float] = None, 
                                confirm: bool = False) -> Dict[str, Any]:
        """
        平倉指定股票
        
        Args:
            symbol (str): 股票代號
            quantity (float, optional): 平倉數量，None 表示全部平倉
            confirm (bool): 是否確認執行
            
        Returns:
            Dict[str, Any]: 執行結果
        """
        if not confirm:
            return {
                "success": False,
                "message": "需要確認才能執行平倉操作",
                "symbol": symbol,
            }
        
        try:
            with self.position_lock:
                if symbol not in self.positions:
                    return {
                        "success": False,
                        "message": f"沒有找到 {symbol} 的持倉",
                        "symbol": symbol,
                    }
                
                position = self.positions[symbol].copy()
            
            # 檢查平倉數量
            current_quantity = position.get("quantity", 0)
            if quantity is None:
                quantity = current_quantity
                mode = ClosePositionMode.ALL
            else:
                if quantity > current_quantity:
                    return {
                        "success": False,
                        "message": f"平倉數量 {quantity} 超過持倉數量 {current_quantity}",
                        "symbol": symbol,
                    }
                mode = ClosePositionMode.PARTIAL
            
            logger.info(f"開始平倉 {symbol}，數量: {quantity}")
            
            # 執行平倉
            result = self._close_position(symbol, position, mode, quantity)
            
            # 記錄平倉操作
            if result["success"]:
                operation_id = f"close_{symbol}_{int(datetime.now().timestamp())}"
                self.close_orders[operation_id] = {
                    "timestamp": datetime.now(),
                    "symbol": symbol,
                    "mode": mode,
                    "quantity": quantity,
                    "order_id": result.get("order_id"),
                }
                result["operation_id"] = operation_id
            
            return result
            
        except Exception as e:
            logger.exception(f"平倉 {symbol} 失敗: {e}")
            if self.on_error:
                self.on_error("close_position_by_symbol", str(e))
            return {
                "success": False,
                "message": f"平倉 {symbol} 失敗: {e}",
                "symbol": symbol,
                "error": str(e),
            }
    
    def close_losing_positions(self, max_loss_percent: Optional[float] = None,
                              confirm: bool = False) -> Dict[str, Any]:
        """
        平倉虧損持倉
        
        Args:
            max_loss_percent (float, optional): 最大虧損比例，None 使用預設值
            confirm (bool): 是否確認執行
            
        Returns:
            Dict[str, Any]: 執行結果
        """
        if not confirm:
            return {
                "success": False,
                "message": "需要確認才能執行平倉虧損持倉操作",
            }
        
        if max_loss_percent is None:
            max_loss_percent = self.max_loss_percent
        
        try:
            with self.position_lock:
                positions_to_close = {}
                
                for symbol, position in self.positions.items():
                    # 計算盈虧比例
                    avg_price = position.get("avg_price", 0)
                    current_price = position.get("current_price", 0)
                    
                    if avg_price > 0 and current_price > 0:
                        loss_percent = (current_price - avg_price) / avg_price
                        
                        # 如果虧損超過閾值，加入平倉列表
                        if loss_percent < -max_loss_percent:
                            positions_to_close[symbol] = position.copy()
                            positions_to_close[symbol]["loss_percent"] = loss_percent
            
            if not positions_to_close:
                return {
                    "success": True,
                    "message": f"沒有虧損超過 {max_loss_percent*100:.1f}% 的持倉",
                    "closed_orders": [],
                }
            
            logger.info(f"開始平倉虧損持倉，共 {len(positions_to_close)} 個")
            
            closed_orders = []
            failed_orders = []
            
            for symbol, position in positions_to_close.items():
                try:
                    result = self._close_position(symbol, position, ClosePositionMode.BY_PROFIT_LOSS)
                    if result["success"]:
                        closed_orders.append(result)
                    else:
                        failed_orders.append(result)
                        
                except Exception as e:
                    logger.exception(f"平倉虧損持倉 {symbol} 時發生錯誤: {e}")
                    failed_orders.append({
                        "symbol": symbol,
                        "success": False,
                        "error": str(e),
                    })
            
            success = len(failed_orders) == 0
            message = f"平倉虧損持倉完成，成功 {len(closed_orders)} 個，失敗 {len(failed_orders)} 個"
            
            logger.info(message)
            
            return {
                "success": success,
                "message": message,
                "max_loss_percent": max_loss_percent,
                "closed_orders": closed_orders,
                "failed_orders": failed_orders,
            }
            
        except Exception as e:
            logger.exception(f"平倉虧損持倉失敗: {e}")
            if self.on_error:
                self.on_error("close_losing_positions", str(e))
            return {
                "success": False,
                "message": f"平倉虧損持倉失敗: {e}",
                "error": str(e),
            }

    def _close_position(self, symbol: str, position: Dict[str, Any],
                       mode: ClosePositionMode, quantity: Optional[float] = None) -> Dict[str, Any]:
        """
        執行平倉操作

        Args:
            symbol (str): 股票代號
            position (Dict[str, Any]): 持倉資訊
            mode (ClosePositionMode): 平倉模式
            quantity (float, optional): 平倉數量

        Returns:
            Dict[str, Any]: 執行結果
        """
        try:
            # 獲取持倉資訊
            current_quantity = position.get("quantity", 0)
            avg_price = position.get("avg_price", 0)
            current_price = position.get("current_price", 0)

            if current_quantity <= 0:
                return {
                    "success": False,
                    "message": f"{symbol} 持倉數量為 0",
                    "symbol": symbol,
                }

            # 確定平倉數量
            if quantity is None:
                close_quantity = current_quantity
            else:
                close_quantity = min(quantity, current_quantity)

            # 確定平倉方向
            action = "sell" if current_quantity > 0 else "buy"
            close_quantity = abs(close_quantity)

            # 創建平倉訂單
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
                logger.info(f"平倉訂單已提交: {symbol} {action} {close_quantity}, 訂單ID: {order_id}")

                # 計算預期盈虧
                if current_price > 0 and avg_price > 0:
                    expected_pnl = (current_price - avg_price) * close_quantity
                    if current_quantity < 0:  # 空頭持倉
                        expected_pnl = -expected_pnl
                else:
                    expected_pnl = 0

                result = {
                    "success": True,
                    "message": f"平倉訂單已提交",
                    "symbol": symbol,
                    "order_id": order_id,
                    "action": action,
                    "quantity": close_quantity,
                    "mode": mode.value,
                    "expected_pnl": expected_pnl,
                }

                # 調用回調函數
                if self.on_close_order_update:
                    self.on_close_order_update(result)

                return result
            else:
                return {
                    "success": False,
                    "message": f"提交平倉訂單失敗",
                    "symbol": symbol,
                }

        except Exception as e:
            logger.exception(f"執行平倉操作失敗 ({symbol}): {e}")
            return {
                "success": False,
                "message": f"執行平倉操作失敗: {e}",
                "symbol": symbol,
                "error": str(e),
            }

    def get_close_orders(self) -> Dict[str, Dict[str, Any]]:
        """
        獲取平倉訂單記錄

        Returns:
            Dict[str, Dict[str, Any]]: 平倉訂單記錄
        """
        return self.close_orders.copy()

    def cancel_close_order(self, order_id: str) -> bool:
        """
        取消平倉訂單

        Args:
            order_id (str): 訂單 ID

        Returns:
            bool: 是否取消成功
        """
        try:
            return self.broker.cancel_order(order_id)
        except Exception as e:
            logger.exception(f"取消平倉訂單失敗 ({order_id}): {e}")
            return False

    def get_position_summary(self) -> Dict[str, Any]:
        """
        獲取持倉摘要

        Returns:
            Dict[str, Any]: 持倉摘要
        """
        try:
            with self.position_lock:
                positions = self.positions.copy()

            if not positions:
                return {
                    "total_positions": 0,
                    "total_value": 0.0,
                    "total_pnl": 0.0,
                    "profitable_positions": 0,
                    "losing_positions": 0,
                }

            total_value = 0.0
            total_pnl = 0.0
            profitable_count = 0
            losing_count = 0

            for symbol, position in positions.items():
                quantity = position.get("quantity", 0)
                avg_price = position.get("avg_price", 0)
                current_price = position.get("current_price", 0)

                if current_price > 0:
                    market_value = abs(quantity) * current_price
                    total_value += market_value

                    if avg_price > 0:
                        pnl = (current_price - avg_price) * quantity
                        total_pnl += pnl

                        if pnl > 0:
                            profitable_count += 1
                        elif pnl < 0:
                            losing_count += 1

            return {
                "total_positions": len(positions),
                "total_value": total_value,
                "total_pnl": total_pnl,
                "total_pnl_percent": (total_pnl / total_value * 100) if total_value > 0 else 0,
                "profitable_positions": profitable_count,
                "losing_positions": losing_count,
                "neutral_positions": len(positions) - profitable_count - losing_count,
            }

        except Exception as e:
            logger.exception(f"獲取持倉摘要失敗: {e}")
            return {
                "error": str(e),
                "total_positions": 0,
                "total_value": 0.0,
                "total_pnl": 0.0,
            }
