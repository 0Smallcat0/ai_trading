"""
交易次數限制器

此模組提供交易次數限制功能，包括：
- 日內交易次數限制
- 單一股票交易頻率限制
- 交易量限制
- 冷卻期管理
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from collections import defaultdict

from src.execution.broker_base import BrokerBase, Order

# 設定日誌
logger = logging.getLogger("risk.live.trade_limiter")


class TradeLimiter:
    """交易次數限制器"""
    
    def __init__(self, broker: BrokerBase):
        """
        初始化交易次數限制器
        
        Args:
            broker (BrokerBase): 券商適配器
        """
        self.broker = broker
        
        # 限制參數
        self.limit_params = {
            "max_daily_trades": 50,  # 每日最大交易次數
            "max_symbol_trades_per_hour": 5,  # 每小時單一股票最大交易次數
            "max_daily_volume": 1000000,  # 每日最大交易量
            "min_trade_interval": 60,  # 最小交易間隔 (秒)
            "cooling_period_after_loss": 300,  # 虧損後冷卻期 (秒)
            "max_consecutive_losses": 3,  # 最大連續虧損次數
        }
        
        # 交易記錄
        self.daily_trades: Dict[str, List[Dict[str, Any]]] = defaultdict(list)  # 按日期分組
        self.symbol_trades: Dict[str, List[Dict[str, Any]]] = defaultdict(list)  # 按股票分組
        self.last_trade_time: Dict[str, datetime] = {}  # 最後交易時間
        self.consecutive_losses: Dict[str, int] = defaultdict(int)  # 連續虧損次數
        self.cooling_periods: Dict[str, datetime] = {}  # 冷卻期結束時間
        
        # 限制檢查記錄
        self.limit_checks: List[Dict[str, Any]] = []
        self.max_checks_size = 1000
        
        # 回調函數
        self.on_limit_exceeded: Optional[Callable] = None
        self.on_cooling_period_activated: Optional[Callable] = None
        self.on_trade_frequency_warning: Optional[Callable] = None
    
    def check_trade_limits(self, order: Order) -> Dict[str, Any]:
        """
        檢查交易限制
        
        Args:
            order (Order): 訂單物件
            
        Returns:
            Dict[str, Any]: 檢查結果
        """
        try:
            check_result = {
                "allowed": True,
                "warnings": [],
                "violations": [],
                "cooling_time_remaining": 0,
            }
            
            current_time = datetime.now()
            today = current_time.date().isoformat()
            
            # 檢查冷卻期
            cooling_result = self._check_cooling_period(order.stock_id, current_time)
            if not cooling_result["allowed"]:
                check_result["allowed"] = False
                check_result["violations"].extend(cooling_result["violations"])
                check_result["cooling_time_remaining"] = cooling_result["remaining_time"]
            
            # 檢查每日交易次數限制
            daily_result = self._check_daily_trade_limit(today, current_time)
            if not daily_result["allowed"]:
                check_result["allowed"] = False
                check_result["violations"].extend(daily_result["violations"])
            check_result["warnings"].extend(daily_result["warnings"])
            
            # 檢查單一股票交易頻率限制
            symbol_result = self._check_symbol_trade_frequency(order.stock_id, current_time)
            if not symbol_result["allowed"]:
                check_result["allowed"] = False
                check_result["violations"].extend(symbol_result["violations"])
            check_result["warnings"].extend(symbol_result["warnings"])
            
            # 檢查最小交易間隔
            interval_result = self._check_min_trade_interval(order.stock_id, current_time)
            if not interval_result["allowed"]:
                check_result["allowed"] = False
                check_result["violations"].extend(interval_result["violations"])
            
            # 檢查每日交易量限制
            volume_result = self._check_daily_volume_limit(order, today)
            if not volume_result["allowed"]:
                check_result["allowed"] = False
                check_result["violations"].extend(volume_result["violations"])
            check_result["warnings"].extend(volume_result["warnings"])
            
            # 記錄檢查結果
            self._record_limit_check(order, check_result)
            
            # 調用回調函數
            if not check_result["allowed"] and self.on_limit_exceeded:
                self.on_limit_exceeded(order, check_result)
            elif check_result["warnings"] and self.on_trade_frequency_warning:
                self.on_trade_frequency_warning(order, check_result)
            
            return check_result
            
        except Exception as e:
            logger.exception(f"檢查交易限制失敗: {e}")
            return {
                "allowed": False,
                "error": f"檢查交易限制失敗: {e}",
            }
    
    def record_trade_execution(self, order_id: str, symbol: str, action: str,
                             quantity: float, price: float, success: bool,
                             pnl: Optional[float] = None) -> bool:
        """
        記錄交易執行
        
        Args:
            order_id (str): 訂單 ID
            symbol (str): 股票代號
            action (str): 買賣方向
            quantity (float): 數量
            price (float): 價格
            success (bool): 是否成功
            pnl (float, optional): 盈虧
            
        Returns:
            bool: 是否記錄成功
        """
        try:
            current_time = datetime.now()
            today = current_time.date().isoformat()
            
            trade_record = {
                "timestamp": current_time,
                "order_id": order_id,
                "symbol": symbol,
                "action": action,
                "quantity": quantity,
                "price": price,
                "value": quantity * price,
                "success": success,
                "pnl": pnl,
            }
            
            # 記錄到每日交易
            self.daily_trades[today].append(trade_record)
            
            # 記錄到股票交易
            self.symbol_trades[symbol].append(trade_record)
            
            # 更新最後交易時間
            self.last_trade_time[symbol] = current_time
            
            # 處理盈虧和冷卻期
            if success and pnl is not None:
                if pnl < 0:  # 虧損
                    self.consecutive_losses[symbol] += 1
                    
                    # 檢查是否需要啟動冷卻期
                    if self.consecutive_losses[symbol] >= self.limit_params["max_consecutive_losses"]:
                        cooling_end = current_time + timedelta(
                            seconds=self.limit_params["cooling_period_after_loss"]
                        )
                        self.cooling_periods[symbol] = cooling_end
                        
                        logger.warning(f"{symbol} 連續虧損 {self.consecutive_losses[symbol]} 次，啟動冷卻期至 {cooling_end}")
                        
                        if self.on_cooling_period_activated:
                            self.on_cooling_period_activated(symbol, cooling_end)
                else:  # 獲利
                    self.consecutive_losses[symbol] = 0  # 重置連續虧損
            
            # 清理舊記錄
            self._cleanup_old_records()
            
            logger.debug(f"已記錄交易執行: {symbol} {action} {quantity} @ {price}")
            return True
            
        except Exception as e:
            logger.exception(f"記錄交易執行失敗: {e}")
            return False
    
    def get_trade_statistics(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        獲取交易統計
        
        Args:
            date (str, optional): 日期 (YYYY-MM-DD)，None 表示今日
            
        Returns:
            Dict[str, Any]: 交易統計
        """
        try:
            if date is None:
                date = datetime.now().date().isoformat()
            
            daily_trades = self.daily_trades.get(date, [])
            
            if not daily_trades:
                return {
                    "date": date,
                    "total_trades": 0,
                    "successful_trades": 0,
                    "failed_trades": 0,
                    "total_volume": 0,
                    "symbols_traded": 0,
                    "avg_trade_size": 0,
                    "pnl_summary": {"total": 0, "positive": 0, "negative": 0},
                }
            
            successful_trades = [t for t in daily_trades if t["success"]]
            failed_trades = [t for t in daily_trades if not t["success"]]
            
            total_volume = sum(t["value"] for t in daily_trades)
            symbols_traded = len(set(t["symbol"] for t in daily_trades))
            avg_trade_size = total_volume / len(daily_trades) if daily_trades else 0
            
            # 計算盈虧統計
            pnl_trades = [t for t in successful_trades if t.get("pnl") is not None]
            total_pnl = sum(t["pnl"] for t in pnl_trades)
            positive_pnl = sum(t["pnl"] for t in pnl_trades if t["pnl"] > 0)
            negative_pnl = sum(t["pnl"] for t in pnl_trades if t["pnl"] < 0)
            
            return {
                "date": date,
                "total_trades": len(daily_trades),
                "successful_trades": len(successful_trades),
                "failed_trades": len(failed_trades),
                "total_volume": total_volume,
                "symbols_traded": symbols_traded,
                "avg_trade_size": avg_trade_size,
                "pnl_summary": {
                    "total": total_pnl,
                    "positive": positive_pnl,
                    "negative": negative_pnl,
                    "win_rate": len([t for t in pnl_trades if t["pnl"] > 0]) / len(pnl_trades) if pnl_trades else 0,
                },
            }
            
        except Exception as e:
            logger.exception(f"獲取交易統計失敗: {e}")
            return {
                "date": date or datetime.now().date().isoformat(),
                "error": str(e),
                "total_trades": 0,
            }
    
    def get_symbol_trade_history(self, symbol: str, hours: int = 24) -> List[Dict[str, Any]]:
        """
        獲取股票交易歷史
        
        Args:
            symbol (str): 股票代號
            hours (int): 小時數
            
        Returns:
            List[Dict[str, Any]]: 交易歷史
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            symbol_trades = self.symbol_trades.get(symbol, [])
            recent_trades = [
                {
                    "timestamp": t["timestamp"].isoformat(),
                    "order_id": t["order_id"],
                    "action": t["action"],
                    "quantity": t["quantity"],
                    "price": t["price"],
                    "value": t["value"],
                    "success": t["success"],
                    "pnl": t.get("pnl"),
                }
                for t in symbol_trades
                if t["timestamp"] > cutoff_time
            ]
            
            return recent_trades
            
        except Exception as e:
            logger.exception(f"獲取股票交易歷史失敗: {e}")
            return []
    
    def get_cooling_periods(self) -> Dict[str, Dict[str, Any]]:
        """
        獲取冷卻期狀態
        
        Returns:
            Dict[str, Dict[str, Any]]: 冷卻期狀態
        """
        try:
            current_time = datetime.now()
            cooling_status = {}
            
            for symbol, end_time in self.cooling_periods.items():
                if end_time > current_time:
                    remaining_seconds = int((end_time - current_time).total_seconds())
                    cooling_status[symbol] = {
                        "active": True,
                        "end_time": end_time.isoformat(),
                        "remaining_seconds": remaining_seconds,
                        "consecutive_losses": self.consecutive_losses.get(symbol, 0),
                    }
                else:
                    cooling_status[symbol] = {
                        "active": False,
                        "end_time": end_time.isoformat(),
                        "remaining_seconds": 0,
                        "consecutive_losses": self.consecutive_losses.get(symbol, 0),
                    }
            
            return cooling_status
            
        except Exception as e:
            logger.exception(f"獲取冷卻期狀態失敗: {e}")
            return {}
    
    def update_limit_params(self, **kwargs) -> bool:
        """
        更新限制參數
        
        Args:
            **kwargs: 參數
            
        Returns:
            bool: 是否更新成功
        """
        try:
            for key, value in kwargs.items():
                if key in self.limit_params:
                    self.limit_params[key] = value
                    logger.info(f"已更新交易限制參數 {key}: {value}")
            return True
        except Exception as e:
            logger.exception(f"更新交易限制參數失敗: {e}")
            return False

    def _check_cooling_period(self, symbol: str, current_time: datetime) -> Dict[str, Any]:
        """檢查冷卻期"""
        try:
            if symbol in self.cooling_periods:
                end_time = self.cooling_periods[symbol]
                if current_time < end_time:
                    remaining_seconds = int((end_time - current_time).total_seconds())
                    return {
                        "allowed": False,
                        "violations": [f"{symbol} 處於冷卻期，剩餘 {remaining_seconds} 秒"],
                        "remaining_time": remaining_seconds,
                    }
                else:
                    # 冷卻期已結束，清理記錄
                    del self.cooling_periods[symbol]
                    self.consecutive_losses[symbol] = 0

            return {"allowed": True, "violations": [], "remaining_time": 0}

        except Exception as e:
            logger.exception(f"檢查冷卻期失敗: {e}")
            return {"allowed": False, "violations": [f"檢查冷卻期失敗: {e}"], "remaining_time": 0}

    def _check_daily_trade_limit(self, today: str, current_time: datetime) -> Dict[str, Any]:
        """檢查每日交易次數限制"""
        try:
            daily_trades = self.daily_trades.get(today, [])
            trade_count = len(daily_trades)
            max_trades = self.limit_params["max_daily_trades"]

            result = {"allowed": True, "warnings": [], "violations": []}

            if trade_count >= max_trades:
                result["allowed"] = False
                result["violations"].append(f"每日交易次數 {trade_count} 已達到限制 {max_trades}")
            elif trade_count >= max_trades * 0.8:  # 80% 警告
                result["warnings"].append(f"每日交易次數 {trade_count} 接近限制 {max_trades}")

            return result

        except Exception as e:
            logger.exception(f"檢查每日交易次數限制失敗: {e}")
            return {"allowed": False, "violations": [f"檢查每日交易次數限制失敗: {e}"]}

    def _check_symbol_trade_frequency(self, symbol: str, current_time: datetime) -> Dict[str, Any]:
        """檢查單一股票交易頻率限制"""
        try:
            one_hour_ago = current_time - timedelta(hours=1)
            symbol_trades = self.symbol_trades.get(symbol, [])

            # 計算過去一小時的交易次數
            recent_trades = [t for t in symbol_trades if t["timestamp"] > one_hour_ago]
            trade_count = len(recent_trades)
            max_trades = self.limit_params["max_symbol_trades_per_hour"]

            result = {"allowed": True, "warnings": [], "violations": []}

            if trade_count >= max_trades:
                result["allowed"] = False
                result["violations"].append(
                    f"{symbol} 過去一小時交易次數 {trade_count} 已達到限制 {max_trades}"
                )
            elif trade_count >= max_trades * 0.8:  # 80% 警告
                result["warnings"].append(
                    f"{symbol} 過去一小時交易次數 {trade_count} 接近限制 {max_trades}"
                )

            return result

        except Exception as e:
            logger.exception(f"檢查股票交易頻率限制失敗: {e}")
            return {"allowed": False, "violations": [f"檢查股票交易頻率限制失敗: {e}"]}

    def _check_min_trade_interval(self, symbol: str, current_time: datetime) -> Dict[str, Any]:
        """檢查最小交易間隔"""
        try:
            if symbol in self.last_trade_time:
                last_time = self.last_trade_time[symbol]
                elapsed_seconds = (current_time - last_time).total_seconds()
                min_interval = self.limit_params["min_trade_interval"]

                if elapsed_seconds < min_interval:
                    remaining_seconds = int(min_interval - elapsed_seconds)
                    return {
                        "allowed": False,
                        "violations": [f"{symbol} 距離上次交易間隔不足，需等待 {remaining_seconds} 秒"],
                    }

            return {"allowed": True, "violations": []}

        except Exception as e:
            logger.exception(f"檢查最小交易間隔失敗: {e}")
            return {"allowed": False, "violations": [f"檢查最小交易間隔失敗: {e}"]}

    def _check_daily_volume_limit(self, order: Order, today: str) -> Dict[str, Any]:
        """檢查每日交易量限制"""
        try:
            daily_trades = self.daily_trades.get(today, [])
            current_volume = sum(t["value"] for t in daily_trades)

            order_value = 0
            if order.price and order.quantity:
                order_value = order.price * order.quantity

            new_volume = current_volume + order_value
            max_volume = self.limit_params["max_daily_volume"]

            result = {"allowed": True, "warnings": [], "violations": []}

            if new_volume > max_volume:
                result["allowed"] = False
                result["violations"].append(
                    f"每日交易量 {new_volume:,.0f} 將超過限制 {max_volume:,.0f}"
                )
            elif new_volume > max_volume * 0.8:  # 80% 警告
                result["warnings"].append(
                    f"每日交易量 {new_volume:,.0f} 接近限制 {max_volume:,.0f}"
                )

            return result

        except Exception as e:
            logger.exception(f"檢查每日交易量限制失敗: {e}")
            return {"allowed": False, "violations": [f"檢查每日交易量限制失敗: {e}"]}

    def _record_limit_check(self, order: Order, check_result: Dict[str, Any]):
        """記錄限制檢查"""
        try:
            record = {
                "timestamp": datetime.now(),
                "symbol": order.stock_id,
                "action": order.action,
                "quantity": order.quantity,
                "price": order.price,
                "allowed": check_result["allowed"],
                "warnings_count": len(check_result["warnings"]),
                "violations_count": len(check_result["violations"]),
                "cooling_time_remaining": check_result.get("cooling_time_remaining", 0),
            }

            self.limit_checks.append(record)

            # 保持記錄在合理範圍內
            if len(self.limit_checks) > self.max_checks_size:
                self.limit_checks = self.limit_checks[-self.max_checks_size//2:]

        except Exception as e:
            logger.exception(f"記錄限制檢查失敗: {e}")

    def _cleanup_old_records(self):
        """清理舊記錄"""
        try:
            current_time = datetime.now()
            cutoff_date = (current_time - timedelta(days=7)).date().isoformat()

            # 清理舊的每日交易記錄
            dates_to_remove = [date for date in self.daily_trades.keys() if date < cutoff_date]
            for date in dates_to_remove:
                del self.daily_trades[date]

            # 清理舊的股票交易記錄
            one_week_ago = current_time - timedelta(days=7)
            for symbol in list(self.symbol_trades.keys()):
                self.symbol_trades[symbol] = [
                    t for t in self.symbol_trades[symbol]
                    if t["timestamp"] > one_week_ago
                ]

                # 如果沒有記錄了，刪除該股票的記錄
                if not self.symbol_trades[symbol]:
                    del self.symbol_trades[symbol]

            # 清理過期的冷卻期
            expired_symbols = [
                symbol for symbol, end_time in self.cooling_periods.items()
                if end_time < current_time
            ]
            for symbol in expired_symbols:
                del self.cooling_periods[symbol]

        except Exception as e:
            logger.exception(f"清理舊記錄失敗: {e}")

    def get_limit_check_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        獲取限制檢查歷史

        Args:
            limit (int): 限制數量

        Returns:
            List[Dict[str, Any]]: 檢查歷史
        """
        return self.limit_checks[-limit:] if self.limit_checks else []
