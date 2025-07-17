"""
停損監控模組

此模組提供停損監控和調整功能，包括：
- 價格監控
- 停損調整
- 訂單管理
"""

import logging
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

from src.execution.broker_base import BrokerBase, Order, OrderType, OrderStatus
from .stop_loss_strategies import StopLossStrategy, StopLossCalculator

# 設定日誌
logger = logging.getLogger("risk.live.stop_loss_monitor")


class StopLossMonitor:
    """停損監控器"""
    
    def __init__(self, broker: BrokerBase):
        """
        初始化停損監控器
        
        Args:
            broker (BrokerBase): 券商適配器
        """
        self.broker = broker
        self.calculator = StopLossCalculator()
        
        # 持倉停損管理
        self.position_stops: Dict[str, Dict[str, Any]] = {}
        
        # 價格歷史 (用於計算波動率和 ATR)
        self.price_history: Dict[str, List[Dict[str, Any]]] = {}
        self.max_history_size = 100
        
        # 停損調整記錄
        self.adjustment_history: List[Dict[str, Any]] = []
        
        # 監控線程
        self._monitor_thread = None
        self._monitoring = False
        self._monitor_lock = threading.Lock()
        
        # 回調函數
        self.on_stop_loss_adjusted: Optional[Callable] = None
        self.on_stop_loss_triggered: Optional[Callable] = None
        self.on_adjustment_error: Optional[Callable] = None
    
    def start_monitoring(self):
        """開始監控"""
        if self._monitoring:
            logger.warning("停損監控已經在運行")
            return
            
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="StopLossMonitor"
        )
        self._monitor_thread.start()
        logger.info("停損監控已啟動")
    
    def stop_monitoring(self):
        """停止監控"""
        self._monitoring = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        logger.info("停損監控已停止")
    
    def add_position_stop(
        self, 
        symbol: str, 
        strategy: StopLossStrategy,
        initial_stop_price: Optional[float] = None,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        添加持倉停損
        
        Args:
            symbol (str): 股票代號
            strategy (StopLossStrategy): 停損策略
            initial_stop_price (float, optional): 初始停損價格
            custom_params (Dict[str, Any], optional): 自定義參數
            
        Returns:
            Dict[str, Any]: 設定結果
        """
        try:
            # 獲取持倉資訊
            positions = self.broker.get_positions()
            if symbol not in positions:
                return {
                    "success": False,
                    "message": f"沒有找到 {symbol} 的持倉",
                }
            
            position = positions[symbol]
            quantity = position.get("quantity", 0)
            avg_price = position.get("avg_price", 0)
            current_price = position.get("current_price", 0)
            
            if quantity == 0:
                return {
                    "success": False,
                    "message": f"{symbol} 持倉數量為 0",
                }
            
            # 合併參數
            params = self.calculator.default_params[strategy].copy()
            if custom_params:
                params.update(custom_params)
            
            # 計算初始停損價格
            if initial_stop_price is None:
                initial_stop_price = self.calculator.calculate_initial_stop_price(
                    symbol, position, strategy, params, self.price_history
                )
            
            # 創建停損訂單
            order_result = self._create_stop_loss_order(symbol, quantity, initial_stop_price)
            if not order_result["success"]:
                return order_result
            
            # 記錄停損設定
            with self._monitor_lock:
                self.position_stops[symbol] = {
                    "strategy": strategy,
                    "params": params,
                    "stop_price": initial_stop_price,
                    "entry_price": avg_price,
                    "entry_time": datetime.now(),
                    "current_price": current_price,
                    "quantity": quantity,
                    "order_id": order_result["order_id"],
                    "highest_price": current_price if quantity > 0 else None,
                    "lowest_price": current_price if quantity < 0 else None,
                    "last_adjustment": datetime.now(),
                }
            
            logger.info(f"已設定 {symbol} 停損: {strategy.value}, 停損價格: {initial_stop_price:.4f}")
            
            return {
                "success": True,
                "message": f"已設定 {symbol} 停損",
                "stop_price": initial_stop_price,
                "order_id": order_result["order_id"],
            }
            
        except Exception as e:
            logger.exception(f"設定停損失敗 [{symbol}]: {e}")
            return {
                "success": False,
                "message": f"設定停損失敗: {str(e)}",
            }
    
    def remove_position_stop(self, symbol: str) -> bool:
        """
        移除持倉停損
        
        Args:
            symbol (str): 股票代號
            
        Returns:
            bool: 是否移除成功
        """
        try:
            with self._monitor_lock:
                if symbol not in self.position_stops:
                    logger.warning(f"沒有找到 {symbol} 的停損設定")
                    return False
                
                stop_info = self.position_stops[symbol]
                order_id = stop_info.get("order_id")
                
                # 取消停損訂單
                if order_id:
                    try:
                        self.broker.cancel_order(order_id)
                    except Exception as e:
                        logger.warning(f"取消停損訂單失敗 [{symbol}]: {e}")
                
                # 移除停損設定
                del self.position_stops[symbol]
                
            logger.info(f"已移除 {symbol} 停損設定")
            return True
            
        except Exception as e:
            logger.exception(f"移除停損設定失敗 [{symbol}]: {e}")
            return False
    
    def get_position_stops(self) -> Dict[str, Dict[str, Any]]:
        """
        獲取所有持倉停損設定
        
        Returns:
            Dict[str, Dict[str, Any]]: 停損設定
        """
        with self._monitor_lock:
            return {k: v.copy() for k, v in self.position_stops.items()}
    
    def get_adjustment_history(
        self, 
        symbol: Optional[str] = None, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        獲取調整歷史
        
        Args:
            symbol (str, optional): 股票代號
            limit (int): 限制數量
            
        Returns:
            List[Dict[str, Any]]: 調整歷史
        """
        with self._monitor_lock:
            history = self.adjustment_history.copy()
            
            if symbol:
                history = [h for h in history if h.get("symbol") == symbol]
            
            return history[-limit:] if history else []
    
    def _monitor_loop(self):
        """監控循環"""
        while self._monitoring:
            try:
                self._update_price_history()
                self._adjust_stop_losses()
                time.sleep(5)  # 每5秒檢查一次
                
            except Exception as e:
                logger.exception(f"停損監控循環錯誤: {e}")
                time.sleep(5)
    
    def _update_price_history(self):
        """更新價格歷史"""
        try:
            positions = self.broker.get_positions()
            
            for symbol in self.position_stops.keys():
                if symbol in positions:
                    position = positions[symbol]
                    current_price = position.get("current_price", 0)
                    
                    if current_price > 0:
                        # 模擬價格數據（實際應該從市場數據獲取）
                        price_data = {
                            "timestamp": datetime.now(),
                            "open": current_price,
                            "high": current_price,
                            "low": current_price,
                            "close": current_price,
                            "volume": 0,
                        }
                        
                        if symbol not in self.price_history:
                            self.price_history[symbol] = []
                        
                        self.price_history[symbol].append(price_data)
                        
                        # 保持歷史記錄在合理範圍內
                        if len(self.price_history[symbol]) > self.max_history_size:
                            self.price_history[symbol] = self.price_history[symbol][-self.max_history_size//2:]
                            
        except Exception as e:
            logger.exception(f"更新價格歷史失敗: {e}")
    
    def _adjust_stop_losses(self):
        """調整停損"""
        try:
            positions = self.broker.get_positions()
            
            with self._monitor_lock:
                for symbol, stop_info in list(self.position_stops.items()):
                    if symbol not in positions:
                        # 持倉已平倉，移除停損設定
                        del self.position_stops[symbol]
                        continue
                    
                    position = positions[symbol]
                    current_price = position.get("current_price", 0)
                    
                    if current_price <= 0:
                        continue
                    
                    # 更新當前價格
                    stop_info["current_price"] = current_price
                    
                    # 根據策略調整停損
                    new_stop_price = self._calculate_new_stop_price(symbol, stop_info, position)
                    
                    if new_stop_price and new_stop_price != stop_info["stop_price"]:
                        self._update_stop_loss_order(symbol, stop_info, new_stop_price)
                        
        except Exception as e:
            logger.exception(f"調整停損失敗: {e}")
    
    def _calculate_new_stop_price(
        self, 
        symbol: str, 
        stop_info: Dict[str, Any],
        position: Dict[str, Any]
    ) -> Optional[float]:
        """
        計算新的停損價格
        
        Args:
            symbol (str): 股票代號
            stop_info (Dict[str, Any]): 停損資訊
            position (Dict[str, Any]): 持倉資訊
            
        Returns:
            Optional[float]: 新的停損價格或 None
        """
        try:
            strategy = stop_info["strategy"]
            current_price = position.get("current_price", 0)
            quantity = position.get("quantity", 0)
            
            if strategy == StopLossStrategy.TRAILING:
                return self.calculator.calculate_trailing_stop(stop_info, current_price, quantity)
            
            elif strategy == StopLossStrategy.VOLATILITY_BASED:
                return self.calculator.calculate_volatility_stop(
                    symbol, stop_info, current_price, quantity, self.price_history
                )
            
            elif strategy == StopLossStrategy.TIME_DECAY:
                return self.calculator.calculate_time_decay_stop(stop_info, current_price, quantity)
            
            elif strategy == StopLossStrategy.ATR_BASED:
                return self.calculator.calculate_atr_stop(
                    symbol, stop_info, current_price, quantity, self.price_history
                )

            # 固定停損不需要調整
            return None

        except Exception as e:
            logger.error(f"計算停損價格失敗 {symbol}: {e}")
            return None

    def calculate_advanced_stop_price(
        self,
        symbol: str,
        stop_info: Dict[str, Any],
        position: Dict[str, Any],
        market_data: Optional[Dict[str, Any]] = None
    ) -> Optional[float]:
        """
        計算高級停損價格（包含新的策略）

        Args:
            symbol (str): 股票代號
            stop_info (Dict[str, Any]): 停損資訊
            position (Dict[str, Any]): 持倉資訊
            market_data (Dict[str, Any], optional): 市場數據

        Returns:
            Optional[float]: 新的停損價格或 None
        """
        try:
            current_price = position.get("current_price", 0)
            quantity = position.get("quantity", 0)

            if current_price <= 0 or quantity == 0:
                return None

            # 檢查保本停損
            breakeven_stop = self.calculator.calculate_breakeven_stop(stop_info, current_price, quantity)
            if breakeven_stop is not None:
                return breakeven_stop

            # 檢查自適應停損（如果有市場數據）
            if market_data:
                market_conditions = market_data.get("conditions", {})
                adaptive_stop = self.calculator.calculate_adaptive_stop(
                    symbol, stop_info, current_price, quantity, market_conditions, self.price_history
                )
                if adaptive_stop is not None:
                    return adaptive_stop

            # 回退到原有策略
            return self._calculate_new_stop_price(symbol, stop_info, position)

        except Exception as e:
            logger.exception(f"計算高級停損價格失敗 [{symbol}]: {e}")
            return None

    def update_market_conditions(self, symbol: str, conditions: Dict[str, Any]):
        """
        更新市場條件數據

        Args:
            symbol (str): 股票代號
            conditions (Dict[str, Any]): 市場條件
        """
        try:
            if not hasattr(self, 'market_conditions'):
                self.market_conditions = {}

            self.market_conditions[symbol] = {
                **conditions,
                "timestamp": datetime.now(),
            }

        except Exception as e:
            logger.exception(f"更新市場條件失敗 [{symbol}]: {e}")

    def get_stop_loss_performance(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        獲取停損性能統計

        Args:
            symbol (str, optional): 股票代號

        Returns:
            Dict[str, Any]: 停損性能統計
        """
        try:
            with self._monitor_lock:
                # 過濾調整歷史
                if symbol:
                    adjustments = [adj for adj in self.adjustment_history if adj.get("symbol") == symbol]
                else:
                    adjustments = self.adjustment_history

                if not adjustments:
                    return {
                        "total_adjustments": 0,
                        "avg_adjustment_size": 0.0,
                        "adjustment_frequency": 0.0,
                        "strategy_distribution": {},
                    }

                # 計算統計
                total_adjustments = len(adjustments)

                # 計算平均調整幅度
                adjustment_sizes = []
                for adj in adjustments:
                    old_price = adj.get("old_stop_price", 0)
                    new_price = adj.get("new_stop_price", 0)
                    if old_price > 0:
                        adjustment_sizes.append(abs(new_price - old_price) / old_price)

                avg_adjustment_size = sum(adjustment_sizes) / len(adjustment_sizes) if adjustment_sizes else 0.0

                # 策略分佈
                strategy_distribution = {}
                for adj in adjustments:
                    strategy = adj.get("strategy", "unknown")
                    strategy_distribution[strategy] = strategy_distribution.get(strategy, 0) + 1

                # 調整頻率（每小時）
                if len(adjustments) >= 2:
                    time_span = (adjustments[-1]["timestamp"] - adjustments[0]["timestamp"]).total_seconds() / 3600
                    adjustment_frequency = total_adjustments / time_span if time_span > 0 else 0.0
                else:
                    adjustment_frequency = 0.0

                return {
                    "total_adjustments": total_adjustments,
                    "avg_adjustment_size": avg_adjustment_size,
                    "adjustment_frequency": adjustment_frequency,
                    "strategy_distribution": strategy_distribution,
                    "latest_adjustment": adjustments[-1] if adjustments else None,
                }

        except Exception as e:
            logger.exception(f"獲取停損性能統計失敗: {e}")
            return {
                "total_adjustments": 0,
                "avg_adjustment_size": 0.0,
                "adjustment_frequency": 0.0,
                "strategy_distribution": {},
                "error": str(e),
            }
            
        except Exception as e:
            logger.exception(f"計算新停損價格失敗 [{symbol}]: {e}")
            return None
    
    def _create_stop_loss_order(self, symbol: str, quantity: float, stop_price: float) -> Dict[str, Any]:
        """
        創建停損訂單
        
        Args:
            symbol (str): 股票代號
            quantity (float): 數量
            stop_price (float): 停損價格
            
        Returns:
            Dict[str, Any]: 訂單結果
        """
        try:
            # 創建停損訂單
            order = Order(
                symbol=symbol,
                quantity=abs(quantity),
                order_type=OrderType.STOP_LOSS,
                price=stop_price,
                side="sell" if quantity > 0 else "buy",
            )
            
            result = self.broker.place_order(order)
            
            if result and result.get("success"):
                return {
                    "success": True,
                    "order_id": result.get("order_id"),
                }
            else:
                return {
                    "success": False,
                    "message": f"創建停損訂單失敗: {result.get('message', '未知錯誤')}",
                }
                
        except Exception as e:
            logger.exception(f"創建停損訂單失敗 [{symbol}]: {e}")
            return {
                "success": False,
                "message": f"創建停損訂單失敗: {str(e)}",
            }
    
    def _update_stop_loss_order(self, symbol: str, stop_info: Dict[str, Any], new_stop_price: float):
        """
        更新停損訂單
        
        Args:
            symbol (str): 股票代號
            stop_info (Dict[str, Any]): 停損資訊
            new_stop_price (float): 新停損價格
        """
        try:
            old_stop_price = stop_info["stop_price"]
            old_order_id = stop_info.get("order_id")
            
            # 取消舊訂單
            if old_order_id:
                try:
                    self.broker.cancel_order(old_order_id)
                except Exception as e:
                    logger.warning(f"取消舊停損訂單失敗 [{symbol}]: {e}")
            
            # 創建新訂單
            quantity = stop_info["quantity"]
            order_result = self._create_stop_loss_order(symbol, quantity, new_stop_price)
            
            if order_result["success"]:
                # 更新停損資訊
                stop_info["stop_price"] = new_stop_price
                stop_info["order_id"] = order_result["order_id"]
                stop_info["last_adjustment"] = datetime.now()
                
                # 記錄調整歷史
                adjustment_record = {
                    "timestamp": datetime.now(),
                    "symbol": symbol,
                    "strategy": stop_info["strategy"].value,
                    "old_stop_price": old_stop_price,
                    "new_stop_price": new_stop_price,
                    "current_price": stop_info["current_price"],
                    "reason": self._get_adjustment_reason(stop_info),
                }
                
                self.adjustment_history.append(adjustment_record)
                
                # 保持調整歷史在合理範圍內
                if len(self.adjustment_history) > 1000:
                    self.adjustment_history = self.adjustment_history[-500:]
                
                logger.info(f"已調整 {symbol} 停損: {old_stop_price:.4f} -> {new_stop_price:.4f}")
                
                # 調用回調函數
                if self.on_stop_loss_adjusted:
                    self.on_stop_loss_adjusted(adjustment_record)
            else:
                logger.error(f"更新停損訂單失敗 [{symbol}]: {order_result.get('message')}")
                if self.on_adjustment_error:
                    self.on_adjustment_error({
                        "symbol": symbol,
                        "error": order_result.get("message"),
                        "timestamp": datetime.now(),
                    })
                    
        except Exception as e:
            logger.exception(f"更新停損訂單失敗 [{symbol}]: {e}")
            if self.on_adjustment_error:
                self.on_adjustment_error({
                    "symbol": symbol,
                    "error": str(e),
                    "timestamp": datetime.now(),
                })
    
    def _get_adjustment_reason(self, stop_info: Dict[str, Any]) -> str:
        """
        獲取調整原因
        
        Args:
            stop_info (Dict[str, Any]): 停損資訊
            
        Returns:
            str: 調整原因
        """
        strategy = stop_info["strategy"]
        
        if strategy == StopLossStrategy.TRAILING:
            return "追蹤停損調整"
        elif strategy == StopLossStrategy.VOLATILITY_BASED:
            return "波動率變化調整"
        elif strategy == StopLossStrategy.TIME_DECAY:
            return "時間衰減調整"
        elif strategy == StopLossStrategy.ATR_BASED:
            return "ATR 變化調整"
        else:
            return "策略調整"
