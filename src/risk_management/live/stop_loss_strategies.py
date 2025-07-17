"""
停損策略計算模組

此模組提供各種停損策略的計算邏輯，包括：
- 追蹤停損計算
- 波動率停損計算
- 時間衰減停損計算
- ATR 停損計算
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

# 設定日誌
logger = logging.getLogger("risk.live.stop_loss_strategies")


class StopLossStrategy(Enum):
    """停損策略枚舉"""
    FIXED = "fixed"  # 固定停損
    TRAILING = "trailing"  # 追蹤停損
    VOLATILITY_BASED = "volatility_based"  # 波動率停損
    TIME_DECAY = "time_decay"  # 時間衰減停損
    ATR_BASED = "atr_based"  # ATR 停損


class StopLossCalculator:
    """停損價格計算器"""
    
    def __init__(self):
        """初始化停損計算器"""
        # 預設策略參數
        self.default_params = {
            StopLossStrategy.TRAILING: {
                "trail_percent": 0.02,  # 追蹤停損 2%
                "min_profit_percent": 0.01,  # 最小獲利 1%
                "max_trail_percent": 0.05,  # 最大追蹤停損 5%
            },
            StopLossStrategy.VOLATILITY_BASED: {
                "volatility_multiplier": 2.0,  # 波動率倍數
                "min_stop_percent": 0.01,  # 最小停損 1%
                "max_stop_percent": 0.1,  # 最大停損 10%
                "lookback_periods": 20,  # 回看期間
            },
            StopLossStrategy.TIME_DECAY: {
                "initial_stop_percent": 0.05,  # 初始停損 5%
                "final_stop_percent": 0.02,  # 最終停損 2%
                "decay_hours": 24,  # 衰減時間 24 小時
            },
            StopLossStrategy.ATR_BASED: {
                "atr_multiplier": 2.0,  # ATR 倍數
                "atr_periods": 14,  # ATR 期間
                "min_stop_percent": 0.01,  # 最小停損 1%
                "max_stop_percent": 0.08,  # 最大停損 8%
            },
        }
    
    def calculate_initial_stop_price(
        self, 
        symbol: str, 
        position: Dict[str, Any],
        strategy: StopLossStrategy, 
        params: Dict[str, Any],
        price_history: Optional[Dict[str, List[Dict[str, Any]]]] = None
    ) -> float:
        """
        計算初始停損價格
        
        Args:
            symbol (str): 股票代號
            position (Dict[str, Any]): 持倉資訊
            strategy (StopLossStrategy): 停損策略
            params (Dict[str, Any]): 策略參數
            price_history (Dict, optional): 價格歷史數據
            
        Returns:
            float: 初始停損價格
        """
        try:
            current_price = position.get("current_price", 0)
            quantity = position.get("quantity", 0)
            
            if current_price <= 0 or quantity == 0:
                raise ValueError(f"無效的持倉資訊: price={current_price}, quantity={quantity}")
            
            if strategy == StopLossStrategy.FIXED:
                # 固定停損
                stop_percent = params.get("stop_percent", 0.05)
                if quantity > 0:  # 多頭
                    return current_price * (1 - stop_percent)
                else:  # 空頭
                    return current_price * (1 + stop_percent)
            
            elif strategy == StopLossStrategy.TRAILING:
                # 追蹤停損
                trail_percent = params.get("trail_percent", 0.02)
                if quantity > 0:  # 多頭
                    return current_price * (1 - trail_percent)
                else:  # 空頭
                    return current_price * (1 + trail_percent)
            
            elif strategy == StopLossStrategy.VOLATILITY_BASED:
                # 波動率停損
                volatility = self._calculate_volatility(symbol, params.get("lookback_periods", 20), price_history)
                multiplier = params.get("volatility_multiplier", 2.0)
                min_stop = params.get("min_stop_percent", 0.01)
                max_stop = params.get("max_stop_percent", 0.1)
                
                stop_percent = max(min_stop, min(max_stop, volatility * multiplier))
                
                if quantity > 0:  # 多頭
                    return current_price * (1 - stop_percent)
                else:  # 空頭
                    return current_price * (1 + stop_percent)
            
            elif strategy == StopLossStrategy.TIME_DECAY:
                # 時間衰減停損
                initial_stop = params.get("initial_stop_percent", 0.05)
                if quantity > 0:  # 多頭
                    return current_price * (1 - initial_stop)
                else:  # 空頭
                    return current_price * (1 + initial_stop)
            
            elif strategy == StopLossStrategy.ATR_BASED:
                # ATR 停損
                atr = self._calculate_atr(symbol, params.get("atr_periods", 14), price_history)
                multiplier = params.get("atr_multiplier", 2.0)
                min_stop = params.get("min_stop_percent", 0.01)
                max_stop = params.get("max_stop_percent", 0.08)
                
                if atr > 0:
                    stop_distance = atr * multiplier
                    stop_percent = stop_distance / current_price
                    stop_percent = max(min_stop, min(max_stop, stop_percent))
                else:
                    stop_percent = min_stop
                
                if quantity > 0:  # 多頭
                    return current_price * (1 - stop_percent)
                else:  # 空頭
                    return current_price * (1 + stop_percent)
            
            else:
                raise ValueError(f"不支援的停損策略: {strategy}")
                
        except Exception as e:
            logger.exception(f"計算初始停損價格失敗 [{symbol}]: {e}")
            # 回退到固定停損
            stop_percent = 0.05
            if quantity > 0:
                return current_price * (1 - stop_percent)
            else:
                return current_price * (1 + stop_percent)
    
    def calculate_trailing_stop(
        self, 
        stop_info: Dict[str, Any],
        current_price: float, 
        quantity: float
    ) -> Optional[float]:
        """
        計算追蹤停損價格
        
        Args:
            stop_info (Dict[str, Any]): 停損資訊
            current_price (float): 當前價格
            quantity (float): 持倉數量
            
        Returns:
            Optional[float]: 新的停損價格，None 表示不需要調整
        """
        try:
            params = stop_info["params"]
            current_stop = stop_info["stop_price"]
            highest_price = stop_info.get("highest_price", stop_info["entry_price"])
            lowest_price = stop_info.get("lowest_price", stop_info["entry_price"])
            
            trail_percent = params.get("trail_percent", 0.02)
            min_profit_percent = params.get("min_profit_percent", 0.01)
            
            if quantity > 0:  # 多頭
                # 更新最高價
                if current_price > highest_price:
                    stop_info["highest_price"] = current_price
                    highest_price = current_price
                
                # 檢查是否有足夠獲利才開始追蹤
                entry_price = stop_info["entry_price"]
                profit_percent = (current_price - entry_price) / entry_price
                
                if profit_percent >= min_profit_percent:
                    new_stop = highest_price * (1 - trail_percent)
                    if new_stop > current_stop:
                        return new_stop
            
            else:  # 空頭
                # 更新最低價
                if current_price < lowest_price:
                    stop_info["lowest_price"] = current_price
                    lowest_price = current_price
                
                # 檢查是否有足夠獲利才開始追蹤
                entry_price = stop_info["entry_price"]
                profit_percent = (entry_price - current_price) / entry_price
                
                if profit_percent >= min_profit_percent:
                    new_stop = lowest_price * (1 + trail_percent)
                    if new_stop < current_stop:
                        return new_stop
            
            return None
            
        except Exception as e:
            logger.exception(f"計算追蹤停損失敗: {e}")
            return None
    
    def calculate_volatility_stop(
        self, 
        symbol: str, 
        stop_info: Dict[str, Any],
        current_price: float, 
        quantity: float,
        price_history: Optional[Dict[str, List[Dict[str, Any]]]] = None
    ) -> Optional[float]:
        """
        計算波動率停損價格
        
        Args:
            symbol (str): 股票代號
            stop_info (Dict[str, Any]): 停損資訊
            current_price (float): 當前價格
            quantity (float): 持倉數量
            price_history (Dict, optional): 價格歷史數據
            
        Returns:
            Optional[float]: 新的停損價格，None 表示不需要調整
        """
        try:
            params = stop_info["params"]
            
            volatility = self._calculate_volatility(symbol, params.get("lookback_periods", 20), price_history)
            multiplier = params.get("volatility_multiplier", 2.0)
            min_stop = params.get("min_stop_percent", 0.01)
            max_stop = params.get("max_stop_percent", 0.1)
            
            stop_percent = max(min_stop, min(max_stop, volatility * multiplier))
            
            if quantity > 0:  # 多頭
                return current_price * (1 - stop_percent)
            else:  # 空頭
                return current_price * (1 + stop_percent)
                
        except Exception as e:
            logger.exception(f"計算波動率停損失敗: {e}")
            return None
    
    def calculate_time_decay_stop(
        self, 
        stop_info: Dict[str, Any],
        current_price: float, 
        quantity: float
    ) -> Optional[float]:
        """
        計算時間衰減停損價格
        
        Args:
            stop_info (Dict[str, Any]): 停損資訊
            current_price (float): 當前價格
            quantity (float): 持倉數量
            
        Returns:
            Optional[float]: 新的停損價格，None 表示不需要調整
        """
        try:
            params = stop_info["params"]
            entry_time = stop_info["entry_time"]
            
            initial_stop = params.get("initial_stop_percent", 0.05)
            final_stop = params.get("final_stop_percent", 0.02)
            decay_hours = params.get("decay_hours", 24)
            
            # 計算時間衰減比例
            elapsed_hours = (datetime.now() - entry_time).total_seconds() / 3600
            decay_ratio = min(1.0, elapsed_hours / decay_hours)
            
            # 線性衰減
            current_stop_percent = initial_stop - (initial_stop - final_stop) * decay_ratio
            
            if quantity > 0:  # 多頭
                return current_price * (1 - current_stop_percent)
            else:  # 空頭
                return current_price * (1 + current_stop_percent)
                
        except Exception as e:
            logger.exception(f"計算時間衰減停損失敗: {e}")
            return None
    
    def _calculate_volatility(
        self, 
        symbol: str, 
        periods: int,
        price_history: Optional[Dict[str, List[Dict[str, Any]]]] = None
    ) -> float:
        """
        計算波動率
        
        Args:
            symbol (str): 股票代號
            periods (int): 計算期間
            price_history (Dict, optional): 價格歷史數據
            
        Returns:
            float: 波動率
        """
        try:
            if not price_history or symbol not in price_history:
                return 0.02  # 預設波動率 2%
            
            history = price_history[symbol]
            if len(history) < periods:
                return 0.02
            
            # 計算收益率
            returns = []
            for i in range(1, min(periods + 1, len(history))):
                prev_price = history[-(i+1)]["close"]
                curr_price = history[-i]["close"]
                if prev_price > 0:
                    returns.append((curr_price - prev_price) / prev_price)
            
            if not returns:
                return 0.02
            
            # 計算標準差
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            volatility = math.sqrt(variance)
            
            return volatility
            
        except Exception as e:
            logger.exception(f"計算波動率失敗 [{symbol}]: {e}")
            return 0.02
    
    def calculate_atr_stop(
        self,
        symbol: str,
        stop_info: Dict[str, Any],
        current_price: float,
        quantity: float,
        price_history: Optional[Dict[str, List[Dict[str, Any]]]] = None
    ) -> Optional[float]:
        """
        計算 ATR 停損價格

        Args:
            symbol (str): 股票代號
            stop_info (Dict[str, Any]): 停損資訊
            current_price (float): 當前價格
            quantity (float): 持倉數量
            price_history (Dict, optional): 價格歷史數據

        Returns:
            Optional[float]: 新的停損價格，None 表示不需要調整
        """
        try:
            params = stop_info["params"]

            atr = self._calculate_atr(symbol, params.get("atr_periods", 14), price_history)
            multiplier = params.get("atr_multiplier", 2.0)
            min_stop = params.get("min_stop_percent", 0.01)
            max_stop = params.get("max_stop_percent", 0.08)

            if atr > 0:
                stop_distance = atr * multiplier
                stop_percent = stop_distance / current_price
                stop_percent = max(min_stop, min(max_stop, stop_percent))
            else:
                stop_percent = min_stop

            if quantity > 0:  # 多頭
                return current_price * (1 - stop_percent)
            else:  # 空頭
                return current_price * (1 + stop_percent)

        except Exception as e:
            logger.exception(f"計算 ATR 停損失敗: {e}")
            return None

    def _calculate_atr(
        self,
        symbol: str,
        periods: int,
        price_history: Optional[Dict[str, List[Dict[str, Any]]]] = None
    ) -> float:
        """
        計算 ATR (Average True Range)

        Args:
            symbol (str): 股票代號
            periods (int): 計算期間
            price_history (Dict, optional): 價格歷史數據

        Returns:
            float: ATR 值
        """
        try:
            if not price_history or symbol not in price_history:
                return 0.0

            history = price_history[symbol]
            if len(history) < periods + 1:
                return 0.0

            true_ranges = []
            for i in range(1, min(periods + 1, len(history))):
                high = history[-i]["high"]
                low = history[-i]["low"]
                prev_close = history[-(i+1)]["close"]

                tr = max(
                    high - low,
                    abs(high - prev_close),
                    abs(low - prev_close)
                )
                true_ranges.append(tr)

            if not true_ranges:
                return 0.0

            return sum(true_ranges) / len(true_ranges)

        except Exception as e:
            logger.exception(f"計算 ATR 失敗 [{symbol}]: {e}")
            return 0.0

    def calculate_adaptive_stop(
        self,
        symbol: str,
        stop_info: Dict[str, Any],
        current_price: float,
        quantity: float,
        market_conditions: Dict[str, Any],
        price_history: Optional[Dict[str, List[Dict[str, Any]]]] = None
    ) -> Optional[float]:
        """
        計算自適應停損價格（根據市場條件動態調整）

        Args:
            symbol (str): 股票代號
            stop_info (Dict[str, Any]): 停損資訊
            current_price (float): 當前價格
            quantity (float): 持倉數量
            market_conditions (Dict[str, Any]): 市場條件
            price_history (Dict, optional): 價格歷史數據

        Returns:
            Optional[float]: 新的停損價格，None 表示不需要調整
        """
        try:
            params = stop_info["params"]

            # 獲取市場條件指標
            volatility = market_conditions.get("volatility", 0.02)
            trend_strength = market_conditions.get("trend_strength", 0.0)  # -1 到 1
            volume_ratio = market_conditions.get("volume_ratio", 1.0)  # 相對於平均成交量

            # 基礎停損比例
            base_stop_percent = params.get("base_stop_percent", 0.03)

            # 根據波動率調整
            volatility_adjustment = volatility * params.get("volatility_factor", 1.0)

            # 根據趨勢強度調整
            if quantity > 0:  # 多頭
                trend_adjustment = max(0, trend_strength) * params.get("trend_factor", 0.5)
            else:  # 空頭
                trend_adjustment = max(0, -trend_strength) * params.get("trend_factor", 0.5)

            # 根據成交量調整
            volume_adjustment = (volume_ratio - 1.0) * params.get("volume_factor", 0.2)

            # 計算調整後的停損比例
            adjusted_stop_percent = base_stop_percent + volatility_adjustment + trend_adjustment + volume_adjustment

            # 限制在合理範圍內
            min_stop = params.get("min_stop_percent", 0.01)
            max_stop = params.get("max_stop_percent", 0.1)
            adjusted_stop_percent = max(min_stop, min(max_stop, adjusted_stop_percent))

            if quantity > 0:  # 多頭
                return current_price * (1 - adjusted_stop_percent)
            else:  # 空頭
                return current_price * (1 + adjusted_stop_percent)

        except Exception as e:
            logger.exception(f"計算自適應停損失敗: {e}")
            return None

    def calculate_breakeven_stop(
        self,
        stop_info: Dict[str, Any],
        current_price: float,
        quantity: float
    ) -> Optional[float]:
        """
        計算保本停損價格

        Args:
            stop_info (Dict[str, Any]): 停損資訊
            current_price (float): 當前價格
            quantity (float): 持倉數量

        Returns:
            Optional[float]: 保本停損價格，None 表示尚未達到保本條件
        """
        try:
            entry_price = stop_info["entry_price"]
            params = stop_info["params"]

            # 保本觸發條件
            breakeven_trigger = params.get("breakeven_trigger_percent", 0.02)  # 獲利2%後啟動保本
            breakeven_buffer = params.get("breakeven_buffer_percent", 0.005)  # 保本緩衝0.5%

            if quantity > 0:  # 多頭
                profit_percent = (current_price - entry_price) / entry_price
                if profit_percent >= breakeven_trigger:
                    return entry_price * (1 + breakeven_buffer)
            else:  # 空頭
                profit_percent = (entry_price - current_price) / entry_price
                if profit_percent >= breakeven_trigger:
                    return entry_price * (1 - breakeven_buffer)

            return None

        except Exception as e:
            logger.exception(f"計算保本停損失敗: {e}")
            return None
