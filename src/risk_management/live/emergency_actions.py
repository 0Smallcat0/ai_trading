"""
緊急行動執行模組

此模組提供具體的緊急行動執行功能，包括：
- 平倉操作
- 訂單取消
- 持倉減少
- 行動執行邏輯
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from src.execution.broker_base import BrokerBase, Order, OrderType

# 設定日誌
logger = logging.getLogger("risk.live.emergency_actions")


class EmergencyActionExecutor:
    """緊急行動執行器"""
    
    def __init__(self, broker: BrokerBase):
        """
        初始化緊急行動執行器
        
        Args:
            broker (BrokerBase): 券商適配器
        """
        self.broker = broker
    
    def close_all_positions(self, reason: str = "緊急平倉") -> Dict[str, Any]:
        """
        一鍵全部平倉
        
        Args:
            reason (str): 平倉原因
            
        Returns:
            Dict[str, Any]: 平倉結果
        """
        try:
            positions = self.broker.get_positions()
            if not positions:
                return {
                    "success": True,
                    "message": "沒有持倉需要平倉",
                    "closed_positions": [],
                }
            
            closed_positions = []
            failed_positions = []
            
            for symbol, position in positions.items():
                try:
                    quantity = position.get("quantity", 0)
                    if quantity == 0:
                        continue
                    
                    # 創建平倉訂單
                    close_order = Order(
                        symbol=symbol,
                        quantity=abs(quantity),
                        order_type=OrderType.MARKET,
                        side="sell" if quantity > 0 else "buy",
                        time_in_force="ioc",  # 立即成交或取消
                    )
                    
                    result = self.broker.place_order(close_order)
                    
                    if result and result.get("success"):
                        closed_positions.append({
                            "symbol": symbol,
                            "quantity": quantity,
                            "order_id": result.get("order_id"),
                        })
                        logger.info(f"已提交 {symbol} 平倉訂單，數量: {quantity}")
                    else:
                        failed_positions.append({
                            "symbol": symbol,
                            "quantity": quantity,
                            "error": result.get("message", "未知錯誤"),
                        })
                        
                except Exception as e:
                    failed_positions.append({
                        "symbol": symbol,
                        "quantity": position.get("quantity", 0),
                        "error": str(e),
                    })
                    logger.exception(f"平倉 {symbol} 失敗: {e}")
            
            success = len(failed_positions) == 0
            message = f"平倉完成 - 成功: {len(closed_positions)}, 失敗: {len(failed_positions)}"
            
            logger.critical(message)
            
            return {
                "success": success,
                "message": message,
                "closed_positions": closed_positions,
                "failed_positions": failed_positions,
                "timestamp": datetime.now(),
            }
            
        except Exception as e:
            logger.exception(f"一鍵全部平倉失敗: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(),
            }
    
    def cancel_all_orders(self) -> Dict[str, Any]:
        """
        取消所有未成交訂單
        
        Returns:
            Dict[str, Any]: 取消結果
        """
        try:
            orders = self.broker.get_orders()
            if not orders:
                return {
                    "success": True,
                    "cancelled_count": 0,
                    "failed_count": 0,
                    "message": "沒有未成交訂單需要取消",
                }
            
            cancelled_count = 0
            failed_count = 0
            cancelled_orders = []
            failed_orders = []
            
            for order in orders:
                if order.get("status") in ["pending", "partial"]:
                    try:
                        result = self.broker.cancel_order(order["order_id"])
                        if result and result.get("success"):
                            cancelled_count += 1
                            cancelled_orders.append({
                                "order_id": order["order_id"],
                                "symbol": order.get("symbol"),
                                "quantity": order.get("quantity"),
                            })
                        else:
                            failed_count += 1
                            failed_orders.append({
                                "order_id": order["order_id"],
                                "error": result.get("message", "未知錯誤"),
                            })
                    except Exception as e:
                        failed_count += 1
                        failed_orders.append({
                            "order_id": order["order_id"],
                            "error": str(e),
                        })
            
            success = failed_count == 0
            message = f"訂單取消完成 - 成功: {cancelled_count}, 失敗: {failed_count}"
            
            logger.info(message)
            
            return {
                "success": success,
                "message": message,
                "cancelled_count": cancelled_count,
                "failed_count": failed_count,
                "cancelled_orders": cancelled_orders,
                "failed_orders": failed_orders,
                "timestamp": datetime.now(),
            }
            
        except Exception as e:
            logger.exception(f"取消所有訂單失敗: {e}")
            return {
                "success": False,
                "error": str(e),
                "cancelled_count": 0,
                "failed_count": 0,
                "timestamp": datetime.now(),
            }
    
    def reduce_position_sizes(self, reduction_ratio: float = 0.5, reason: str = "緊急減倉") -> Dict[str, Any]:
        """
        減少持倉規模
        
        Args:
            reduction_ratio (float): 減倉比例 (0.0-1.0)
            reason (str): 減倉原因
            
        Returns:
            Dict[str, Any]: 減倉結果
        """
        try:
            if not 0 < reduction_ratio <= 1:
                return {
                    "success": False,
                    "error": "減倉比例必須在 0 到 1 之間",
                }
            
            positions = self.broker.get_positions()
            if not positions:
                return {
                    "success": True,
                    "message": "沒有持倉需要減少",
                    "reduced_positions": [],
                }
            
            reduced_positions = []
            failed_positions = []
            
            for symbol, position in positions.items():
                try:
                    quantity = position.get("quantity", 0)
                    if abs(quantity) < 2:  # 數量太小，跳過
                        continue
                    
                    reduce_quantity = int(abs(quantity) * reduction_ratio)
                    if reduce_quantity == 0:
                        continue
                    
                    # 創建減倉訂單
                    reduce_order = Order(
                        symbol=symbol,
                        quantity=reduce_quantity,
                        order_type=OrderType.MARKET,
                        side="sell" if quantity > 0 else "buy",
                    )
                    
                    result = self.broker.place_order(reduce_order)
                    
                    if result and result.get("success"):
                        reduced_positions.append({
                            "symbol": symbol,
                            "original_quantity": quantity,
                            "reduced_quantity": reduce_quantity,
                            "remaining_quantity": quantity - (reduce_quantity if quantity > 0 else -reduce_quantity),
                            "order_id": result.get("order_id"),
                        })
                        logger.info(f"已提交 {symbol} 減倉訂單，減少數量: {reduce_quantity}")
                    else:
                        failed_positions.append({
                            "symbol": symbol,
                            "original_quantity": quantity,
                            "error": result.get("message", "未知錯誤"),
                        })
                        
                except Exception as e:
                    failed_positions.append({
                        "symbol": symbol,
                        "original_quantity": position.get("quantity", 0),
                        "error": str(e),
                    })
                    logger.exception(f"減倉 {symbol} 失敗: {e}")
            
            success = len(failed_positions) == 0
            message = f"減倉完成 - 成功: {len(reduced_positions)}, 失敗: {len(failed_positions)}"
            
            logger.warning(message)
            
            return {
                "success": success,
                "message": message,
                "reduction_ratio": reduction_ratio,
                "reduced_positions": reduced_positions,
                "failed_positions": failed_positions,
                "timestamp": datetime.now(),
            }
            
        except Exception as e:
            logger.exception(f"減少持倉規模失敗: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(),
            }
    
    def close_specific_positions(self, symbols: List[str], reason: str = "指定平倉") -> Dict[str, Any]:
        """
        平倉指定持倉
        
        Args:
            symbols (List[str]): 要平倉的股票代號列表
            reason (str): 平倉原因
            
        Returns:
            Dict[str, Any]: 平倉結果
        """
        try:
            positions = self.broker.get_positions()
            if not positions:
                return {
                    "success": True,
                    "message": "沒有持倉需要平倉",
                    "closed_positions": [],
                }
            
            closed_positions = []
            failed_positions = []
            not_found_symbols = []
            
            for symbol in symbols:
                if symbol not in positions:
                    not_found_symbols.append(symbol)
                    continue
                
                try:
                    position = positions[symbol]
                    quantity = position.get("quantity", 0)
                    
                    if quantity == 0:
                        continue
                    
                    # 創建平倉訂單
                    close_order = Order(
                        symbol=symbol,
                        quantity=abs(quantity),
                        order_type=OrderType.MARKET,
                        side="sell" if quantity > 0 else "buy",
                        time_in_force="ioc",
                    )
                    
                    result = self.broker.place_order(close_order)
                    
                    if result and result.get("success"):
                        closed_positions.append({
                            "symbol": symbol,
                            "quantity": quantity,
                            "order_id": result.get("order_id"),
                        })
                        logger.info(f"已提交 {symbol} 平倉訂單，數量: {quantity}")
                    else:
                        failed_positions.append({
                            "symbol": symbol,
                            "quantity": quantity,
                            "error": result.get("message", "未知錯誤"),
                        })
                        
                except Exception as e:
                    failed_positions.append({
                        "symbol": symbol,
                        "quantity": positions.get(symbol, {}).get("quantity", 0),
                        "error": str(e),
                    })
                    logger.exception(f"平倉 {symbol} 失敗: {e}")
            
            success = len(failed_positions) == 0
            message = f"指定平倉完成 - 成功: {len(closed_positions)}, 失敗: {len(failed_positions)}"
            
            if not_found_symbols:
                message += f", 未找到持倉: {len(not_found_symbols)}"
            
            logger.info(message)
            
            return {
                "success": success,
                "message": message,
                "closed_positions": closed_positions,
                "failed_positions": failed_positions,
                "not_found_symbols": not_found_symbols,
                "timestamp": datetime.now(),
            }
            
        except Exception as e:
            logger.exception(f"平倉指定持倉失敗: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(),
            }
