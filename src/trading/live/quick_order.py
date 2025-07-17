"""
快速下單面板

此模組提供快速下單功能，包括：
- 預設參數快速下單
- 常用股票快速選擇
- 批量下單功能
- 下單模板管理
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from src.execution.broker_base import BrokerBase, Order, OrderType, OrderStatus

# 設定日誌
logger = logging.getLogger("trading.live.quick_order")


class QuickOrderTemplate:
    """快速下單模板"""
    
    def __init__(
        self,
        name: str,
        symbol: str,
        action: str,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "day",
    ):
        """
        初始化快速下單模板
        
        Args:
            name (str): 模板名稱
            symbol (str): 股票代號
            action (str): 買賣方向 (buy/sell)
            quantity (float): 數量
            order_type (OrderType): 訂單類型
            price (float, optional): 價格
            stop_price (float, optional): 停損價格
            time_in_force (str): 時效
        """
        self.name = name
        self.symbol = symbol
        self.action = action
        self.quantity = quantity
        self.order_type = order_type
        self.price = price
        self.stop_price = stop_price
        self.time_in_force = time_in_force
        self.created_time = datetime.now()
        self.usage_count = 0
    
    def to_order(self) -> Order:
        """轉換為訂單物件"""
        return Order(
            stock_id=self.symbol,
            action=self.action,
            quantity=self.quantity,
            order_type=self.order_type,
            price=self.price,
            stop_price=self.stop_price,
            time_in_force=self.time_in_force,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "name": self.name,
            "symbol": self.symbol,
            "action": self.action,
            "quantity": self.quantity,
            "order_type": self.order_type.value,
            "price": self.price,
            "stop_price": self.stop_price,
            "time_in_force": self.time_in_force,
            "created_time": self.created_time.isoformat(),
            "usage_count": self.usage_count,
        }


class QuickOrderPanel:
    """快速下單面板"""
    
    def __init__(self, broker: BrokerBase):
        """
        初始化快速下單面板
        
        Args:
            broker (BrokerBase): 券商適配器
        """
        self.broker = broker
        
        # 下單模板
        self.templates: Dict[str, QuickOrderTemplate] = {}
        
        # 常用股票
        self.favorite_symbols: List[str] = []
        
        # 預設參數
        self.default_params = {
            "quantity": 1000,
            "order_type": OrderType.MARKET,
            "time_in_force": "day",
        }
        
        # 下單記錄
        self.order_history: List[Dict[str, Any]] = []
        
        # 回調函數
        self.on_order_submitted: Optional[Callable] = None
        self.on_order_error: Optional[Callable] = None
    
    def add_template(self, template: QuickOrderTemplate) -> bool:
        """
        添加下單模板
        
        Args:
            template (QuickOrderTemplate): 下單模板
            
        Returns:
            bool: 是否添加成功
        """
        try:
            self.templates[template.name] = template
            logger.info(f"已添加下單模板: {template.name}")
            return True
        except Exception as e:
            logger.exception(f"添加下單模板失敗: {e}")
            return False
    
    def remove_template(self, name: str) -> bool:
        """
        移除下單模板
        
        Args:
            name (str): 模板名稱
            
        Returns:
            bool: 是否移除成功
        """
        try:
            if name in self.templates:
                del self.templates[name]
                logger.info(f"已移除下單模板: {name}")
                return True
            else:
                logger.warning(f"找不到下單模板: {name}")
                return False
        except Exception as e:
            logger.exception(f"移除下單模板失敗: {e}")
            return False
    
    def get_templates(self) -> List[Dict[str, Any]]:
        """
        獲取所有下單模板
        
        Returns:
            List[Dict[str, Any]]: 下單模板列表
        """
        return [template.to_dict() for template in self.templates.values()]
    
    def quick_order_from_template(self, template_name: str, 
                                 quantity_override: Optional[float] = None,
                                 price_override: Optional[float] = None) -> Dict[str, Any]:
        """
        使用模板快速下單
        
        Args:
            template_name (str): 模板名稱
            quantity_override (float, optional): 覆蓋數量
            price_override (float, optional): 覆蓋價格
            
        Returns:
            Dict[str, Any]: 下單結果
        """
        try:
            if template_name not in self.templates:
                return {
                    "success": False,
                    "message": f"找不到下單模板: {template_name}",
                }
            
            template = self.templates[template_name]
            order = template.to_order()
            
            # 覆蓋參數
            if quantity_override is not None:
                order.quantity = quantity_override
            if price_override is not None:
                order.price = price_override
            
            # 提交訂單
            result = self._submit_order(order, f"模板下單: {template_name}")
            
            # 更新模板使用次數
            if result["success"]:
                template.usage_count += 1
            
            return result
            
        except Exception as e:
            logger.exception(f"模板下單失敗: {e}")
            return {
                "success": False,
                "message": f"模板下單失敗: {e}",
                "error": str(e),
            }
    
    def quick_buy(self, symbol: str, quantity: float, 
                  order_type: OrderType = OrderType.MARKET,
                  price: Optional[float] = None) -> Dict[str, Any]:
        """
        快速買入
        
        Args:
            symbol (str): 股票代號
            quantity (float): 數量
            order_type (OrderType): 訂單類型
            price (float, optional): 價格
            
        Returns:
            Dict[str, Any]: 下單結果
        """
        try:
            order = Order(
                stock_id=symbol,
                action="buy",
                quantity=quantity,
                order_type=order_type,
                price=price,
                time_in_force=self.default_params["time_in_force"],
            )
            
            return self._submit_order(order, "快速買入")
            
        except Exception as e:
            logger.exception(f"快速買入失敗: {e}")
            return {
                "success": False,
                "message": f"快速買入失敗: {e}",
                "error": str(e),
            }
    
    def quick_sell(self, symbol: str, quantity: float,
                   order_type: OrderType = OrderType.MARKET,
                   price: Optional[float] = None) -> Dict[str, Any]:
        """
        快速賣出
        
        Args:
            symbol (str): 股票代號
            quantity (float): 數量
            order_type (OrderType): 訂單類型
            price (float, optional): 價格
            
        Returns:
            Dict[str, Any]: 下單結果
        """
        try:
            order = Order(
                stock_id=symbol,
                action="sell",
                quantity=quantity,
                order_type=order_type,
                price=price,
                time_in_force=self.default_params["time_in_force"],
            )
            
            return self._submit_order(order, "快速賣出")
            
        except Exception as e:
            logger.exception(f"快速賣出失敗: {e}")
            return {
                "success": False,
                "message": f"快速賣出失敗: {e}",
                "error": str(e),
            }
    
    def batch_order(self, orders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量下單
        
        Args:
            orders (List[Dict[str, Any]]): 訂單列表
            
        Returns:
            Dict[str, Any]: 批量下單結果
        """
        try:
            successful_orders = []
            failed_orders = []
            
            for order_data in orders:
                try:
                    order = Order(
                        stock_id=order_data["symbol"],
                        action=order_data["action"],
                        quantity=order_data["quantity"],
                        order_type=OrderType(order_data.get("order_type", "market")),
                        price=order_data.get("price"),
                        stop_price=order_data.get("stop_price"),
                        time_in_force=order_data.get("time_in_force", "day"),
                    )
                    
                    result = self._submit_order(order, "批量下單")
                    
                    if result["success"]:
                        successful_orders.append(result)
                    else:
                        failed_orders.append({
                            "order_data": order_data,
                            "error": result.get("message", "未知錯誤"),
                        })
                        
                except Exception as e:
                    logger.exception(f"批量下單中的單個訂單失敗: {e}")
                    failed_orders.append({
                        "order_data": order_data,
                        "error": str(e),
                    })
            
            success = len(failed_orders) == 0
            message = f"批量下單完成，成功 {len(successful_orders)} 個，失敗 {len(failed_orders)} 個"
            
            logger.info(message)
            
            return {
                "success": success,
                "message": message,
                "total_orders": len(orders),
                "successful_orders": successful_orders,
                "failed_orders": failed_orders,
            }
            
        except Exception as e:
            logger.exception(f"批量下單失敗: {e}")
            return {
                "success": False,
                "message": f"批量下單失敗: {e}",
                "error": str(e),
            }

    def add_favorite_symbol(self, symbol: str) -> bool:
        """
        添加常用股票

        Args:
            symbol (str): 股票代號

        Returns:
            bool: 是否添加成功
        """
        try:
            if symbol not in self.favorite_symbols:
                self.favorite_symbols.append(symbol)
                logger.info(f"已添加常用股票: {symbol}")
                return True
            else:
                logger.info(f"股票 {symbol} 已在常用列表中")
                return True
        except Exception as e:
            logger.exception(f"添加常用股票失敗: {e}")
            return False

    def remove_favorite_symbol(self, symbol: str) -> bool:
        """
        移除常用股票

        Args:
            symbol (str): 股票代號

        Returns:
            bool: 是否移除成功
        """
        try:
            if symbol in self.favorite_symbols:
                self.favorite_symbols.remove(symbol)
                logger.info(f"已移除常用股票: {symbol}")
                return True
            else:
                logger.warning(f"常用股票列表中找不到: {symbol}")
                return False
        except Exception as e:
            logger.exception(f"移除常用股票失敗: {e}")
            return False

    def get_favorite_symbols(self) -> List[str]:
        """
        獲取常用股票列表

        Returns:
            List[str]: 常用股票列表
        """
        return self.favorite_symbols.copy()

    def update_default_params(self, **kwargs) -> bool:
        """
        更新預設參數

        Args:
            **kwargs: 參數

        Returns:
            bool: 是否更新成功
        """
        try:
            for key, value in kwargs.items():
                if key in self.default_params:
                    self.default_params[key] = value
                    logger.info(f"已更新預設參數 {key}: {value}")
            return True
        except Exception as e:
            logger.exception(f"更新預設參數失敗: {e}")
            return False

    def get_default_params(self) -> Dict[str, Any]:
        """
        獲取預設參數

        Returns:
            Dict[str, Any]: 預設參數
        """
        return self.default_params.copy()

    def get_order_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        獲取下單歷史

        Args:
            limit (int): 限制數量

        Returns:
            List[Dict[str, Any]]: 下單歷史
        """
        return self.order_history[-limit:] if self.order_history else []

    def clear_order_history(self) -> bool:
        """
        清空下單歷史

        Returns:
            bool: 是否清空成功
        """
        try:
            self.order_history.clear()
            logger.info("已清空下單歷史")
            return True
        except Exception as e:
            logger.exception(f"清空下單歷史失敗: {e}")
            return False

    def _submit_order(self, order: Order, source: str) -> Dict[str, Any]:
        """
        提交訂單

        Args:
            order (Order): 訂單物件
            source (str): 下單來源

        Returns:
            Dict[str, Any]: 提交結果
        """
        try:
            # 檢查券商連接
            if not self.broker.connected:
                return {
                    "success": False,
                    "message": "券商未連接",
                }

            # 提交訂單
            order_id = self.broker.place_order(order)

            if order_id:
                # 記錄下單歷史
                order_record = {
                    "order_id": order_id,
                    "symbol": order.stock_id,
                    "action": order.action,
                    "quantity": order.quantity,
                    "order_type": order.order_type.value,
                    "price": order.price,
                    "stop_price": order.stop_price,
                    "time_in_force": order.time_in_force,
                    "source": source,
                    "timestamp": datetime.now().isoformat(),
                }
                self.order_history.append(order_record)

                # 保持歷史記錄在合理範圍內
                if len(self.order_history) > 1000:
                    self.order_history = self.order_history[-500:]

                logger.info(f"訂單提交成功: {order_id} ({source})")

                result = {
                    "success": True,
                    "message": "訂單提交成功",
                    "order_id": order_id,
                    "order_record": order_record,
                }

                # 調用回調函數
                if self.on_order_submitted:
                    self.on_order_submitted(result)

                return result
            else:
                error_msg = "訂單提交失敗"
                logger.error(error_msg)

                if self.on_order_error:
                    self.on_order_error(order, error_msg)

                return {
                    "success": False,
                    "message": error_msg,
                }

        except Exception as e:
            error_msg = f"提交訂單時發生錯誤: {e}"
            logger.exception(error_msg)

            if self.on_order_error:
                self.on_order_error(order, error_msg)

            return {
                "success": False,
                "message": error_msg,
                "error": str(e),
            }
