"""
動態停損調整主模組

此模組提供動態停損調整功能的主要介面，包括：
- 停損策略管理
- 持倉停損設定
- 監控協調

這是一個重構後的模組，將原本的大型類別拆分為多個專門的子模組：
- stop_loss_strategies.py: 停損策略計算邏輯
- stop_loss_monitor.py: 監控和調整邏輯
"""

import logging
from typing import Any, Dict, List, Optional, Callable

from src.execution.broker_base import BrokerBase
from .stop_loss_strategies import StopLossStrategy, StopLossCalculator
from .stop_loss_monitor import StopLossMonitor

# 設定日誌
logger = logging.getLogger("risk.live.dynamic_stop_loss")


class DynamicStopLoss:
    """動態停損調整器 - 主要介面類別"""

    def __init__(self, broker: BrokerBase):
        """
        初始化動態停損調整器

        Args:
            broker (BrokerBase): 券商適配器
        """
        self.broker = broker
        self.monitor = StopLossMonitor(broker)
        self.calculator = StopLossCalculator()

        # 向後兼容性屬性
        self.strategy_params = self.calculator.default_params
        self.position_stops = self.monitor.position_stops
        self.price_history = self.monitor.price_history
        self.adjustment_history = self.monitor.adjustment_history

        # 回調函數代理
        self._on_stop_loss_adjusted = None
        self._on_stop_loss_triggered = None
        self._on_adjustment_error = None

    @property
    def on_stop_loss_adjusted(self) -> Optional[Callable]:
        """停損調整回調函數"""
        return self._on_stop_loss_adjusted

    @on_stop_loss_adjusted.setter
    def on_stop_loss_adjusted(self, callback: Optional[Callable]):
        """設定停損調整回調函數"""
        self._on_stop_loss_adjusted = callback
        self.monitor.on_stop_loss_adjusted = callback

    @property
    def on_stop_loss_triggered(self) -> Optional[Callable]:
        """停損觸發回調函數"""
        return self._on_stop_loss_triggered

    @on_stop_loss_triggered.setter
    def on_stop_loss_triggered(self, callback: Optional[Callable]):
        """設定停損觸發回調函數"""
        self._on_stop_loss_triggered = callback
        self.monitor.on_stop_loss_triggered = callback

    @property
    def on_adjustment_error(self) -> Optional[Callable]:
        """調整錯誤回調函數"""
        return self._on_adjustment_error

    @on_adjustment_error.setter
    def on_adjustment_error(self, callback: Optional[Callable]):
        """設定調整錯誤回調函數"""
        self._on_adjustment_error = callback
        self.monitor.on_adjustment_error = callback

    def start_monitoring(self):
        """開始監控"""
        self.monitor.start_monitoring()

    def stop_monitoring(self):
        """停止監控"""
        self.monitor.stop_monitoring()

    def set_position_stop_loss(
        self,
        symbol: str,
        strategy: StopLossStrategy,
        initial_stop_price: Optional[float] = None,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        設定持倉停損

        Args:
            symbol (str): 股票代號
            strategy (StopLossStrategy): 停損策略
            initial_stop_price (float, optional): 初始停損價格
            custom_params (Dict[str, Any], optional): 自定義參數

        Returns:
            Dict[str, Any]: 設定結果
        """
        return self.monitor.add_position_stop(symbol, strategy, initial_stop_price, custom_params)

    def remove_position_stop_loss(self, symbol: str) -> bool:
        """
        移除持倉停損

        Args:
            symbol (str): 股票代號

        Returns:
            bool: 是否移除成功
        """
        return self.monitor.remove_position_stop(symbol)

    def get_position_stops(self) -> Dict[str, Dict[str, Any]]:
        """
        獲取所有持倉停損設定

        Returns:
            Dict[str, Dict[str, Any]]: 停損設定
        """
        return self.monitor.get_position_stops()

    def update_strategy_params(self, strategy: StopLossStrategy, **kwargs) -> bool:
        """
        更新策略參數

        Args:
            strategy (StopLossStrategy): 停損策略
            **kwargs: 參數

        Returns:
            bool: 是否更新成功
        """
        try:
            if strategy in self.calculator.default_params:
                self.calculator.default_params[strategy].update(kwargs)
                logger.info(f"已更新 {strategy.value} 策略參數: {kwargs}")
                return True
            else:
                logger.error(f"不支援的停損策略: {strategy}")
                return False
        except Exception as e:
            logger.exception(f"更新策略參數失敗: {e}")
            return False

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
        return self.monitor.get_adjustment_history(symbol, limit)