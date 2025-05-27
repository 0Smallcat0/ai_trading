"""風險管理器模組

此模組實現了風險管理器，整合了各種風險管理策略和機制。
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from src.core.event_monitor import Event, EventSeverity, EventSource, EventType
from src.core.logger import logger

from .risk_manager_base import RiskManagerBase
from .strategy_manager import StrategyManager
from .risk_monitor import RiskMonitor


class RiskManager(RiskManagerBase):
    """風險管理器

    整合各種風險管理策略和機制，提供全面的風險管理功能。
    """

    def __init__(self):
        """初始化風險管理器"""
        # 初始化基礎功能
        super().__init__()

        # 策略管理器
        self.strategy_manager = StrategyManager()

        # 風險監控器
        self.risk_monitor = RiskMonitor()

        logger.info("風險管理器已完全初始化")

    # 策略管理相關方法
    def register_stop_loss_strategy(self, name: str, strategy) -> bool:
        """註冊停損策略

        Args:
            name: 策略名稱
            strategy: 停損策略

        Returns:
            bool: 是否成功註冊
        """
        return self.strategy_manager.register_stop_loss_strategy(name, strategy)

    def register_take_profit_strategy(self, name: str, strategy) -> bool:
        """註冊停利策略

        Args:
            name: 策略名稱
            strategy: 停利策略

        Returns:
            bool: 是否成功註冊
        """
        return self.strategy_manager.register_take_profit_strategy(name, strategy)

    def register_position_sizing_strategy(self, name: str, strategy) -> bool:
        """註冊倉位大小策略

        Args:
            name: 策略名稱
            strategy: 倉位大小策略

        Returns:
            bool: 是否成功註冊
        """
        return self.strategy_manager.register_position_sizing_strategy(name, strategy)

    def register_circuit_breaker(self, name: str, breaker) -> bool:
        """註冊熔斷機制

        Args:
            name: 熔斷機制名稱
            breaker: 熔斷機制

        Returns:
            bool: 是否成功註冊
        """
        return self.strategy_manager.register_circuit_breaker(name, breaker)

    # 風險檢查相關方法
    def check_stop_loss(
        self, strategy_name: str, entry_price: float, current_price: float, **kwargs
    ) -> bool:
        """檢查停損

        Args:
            strategy_name: 策略名稱
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數

        Returns:
            bool: 是否應該停損
        """
        should_stop = self.strategy_manager.check_stop_loss(
            strategy_name, entry_price, current_price, **kwargs
        )

        if should_stop:
            # 記錄風險事件
            self._record_risk_event(
                event_type="stop_loss",
                strategy_name=strategy_name,
                entry_price=entry_price,
                current_price=current_price,
                **kwargs,
            )

        return should_stop

    def check_take_profit(
        self, strategy_name: str, entry_price: float, current_price: float, **kwargs
    ) -> bool:
        """檢查停利

        Args:
            strategy_name: 策略名稱
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數

        Returns:
            bool: 是否應該停利
        """
        should_take_profit = self.strategy_manager.check_take_profit(
            strategy_name, entry_price, current_price, **kwargs
        )

        if should_take_profit:
            # 記錄風險事件
            self._record_risk_event(
                event_type="take_profit",
                strategy_name=strategy_name,
                entry_price=entry_price,
                current_price=current_price,
                **kwargs,
            )

        return should_take_profit

    def calculate_position_size(
        self, strategy_name: str, portfolio_value: float, **kwargs
    ) -> float:
        """計算倉位大小

        Args:
            strategy_name: 策略名稱
            portfolio_value: 投資組合價值
            **kwargs: 其他參數

        Returns:
            float: 倉位大小（金額）
        """
        return self.strategy_manager.calculate_position_size(
            strategy_name, portfolio_value, **kwargs
        )

    def calculate_shares(
        self, strategy_name: str, portfolio_value: float, price: float, **kwargs
    ) -> int:
        """計算股數

        Args:
            strategy_name: 策略名稱
            portfolio_value: 投資組合價值
            price: 股票價格
            **kwargs: 其他參數

        Returns:
            int: 股數
        """
        return self.strategy_manager.calculate_shares(
            strategy_name, portfolio_value, price, **kwargs
        )

    def check_portfolio_limits(
        self, symbol: str, value: float, sector: Optional[str] = None
    ) -> bool:
        """檢查投資組合限制

        Args:
            symbol: 股票代碼
            value: 倉位價值
            sector: 行業分類

        Returns:
            bool: 是否符合限制
        """
        # 檢查所有限制
        result = self.portfolio_risk_manager.check_all_limits(symbol, value, sector)

        if not result:
            logger.warning("倉位 %s 不符合投資組合限制", symbol)

            # 記錄風險事件
            self._record_risk_event(
                event_type="portfolio_limit", symbol=symbol, value=value, sector=sector
            )

        return result

    def check_circuit_breakers(self, **kwargs) -> bool:
        """檢查熔斷機制

        Args:
            **kwargs: 其他參數

        Returns:
            bool: 是否觸發熔斷
        """
        # 如果交易已停止，則直接返回 True
        if not self.trading_enabled:
            return True

        # 檢查熔斷機制
        triggered_breaker = self.strategy_manager.check_circuit_breakers(**kwargs)

        if triggered_breaker:
            # 停止交易
            self.stop_trading(f"熔斷機制 '{triggered_breaker}' 已觸發")

            # 記錄風險事件
            self._record_risk_event(
                event_type="circuit_breaker",
                breaker_name=triggered_breaker,
            )

            return True

        return False

    def update_risk_metrics(
        self, returns: pd.Series, risk_free_rate: float = 0.0
    ) -> Dict[str, float]:
        """更新風險指標

        Args:
            returns: 收益率序列
            risk_free_rate: 無風險利率

        Returns:
            Dict[str, float]: 風險指標
        """
        # 使用風險監控器更新指標
        metrics = self.risk_monitor.update_risk_metrics(returns, risk_free_rate)

        # 更新基礎類別的風險指標
        super().update_risk_metrics(metrics)

        # 檢查風險閾值
        violations = self.risk_monitor.check_risk_thresholds(metrics)

        # 如果有違規，記錄事件
        for metric, violated in violations.items():
            if violated:
                self._record_risk_event(
                    event_type="risk_threshold_violation",
                    metric=metric,
                    value=metrics.get(metric),
                    threshold=self.risk_monitor.get_risk_threshold(metric),
                )

        return metrics

    def generate_risk_report(self) -> Dict[str, Any]:
        """生成風險報告

        Returns:
            Dict[str, Any]: 風險報告
        """
        # 獲取當前風險指標
        metrics = self.get_risk_metrics()

        # 檢查閾值違規
        violations = self.risk_monitor.check_risk_thresholds(metrics)

        # 生成報告
        return self.risk_monitor.generate_risk_report(metrics, violations)

    def _record_risk_event(self, event_type: str, **kwargs) -> None:
        """記錄風險事件

        Args:
            event_type: 事件類型
            **kwargs: 其他參數
        """
        # 調用基礎類別的方法
        super()._record_risk_event(event_type, **kwargs)

        # 發送事件
        try:
            from src.core.event_monitor import event_bus

            severity = (
                EventSeverity.ERROR
                if event_type in ["circuit_breaker", "trading_stopped"]
                else EventSeverity.WARNING
            )

            event_obj = Event(
                event_type=EventType.RISK,
                source=EventSource.RISK_MANAGER,
                subject=event_type,
                severity=severity,
                message=f"風險事件: {event_type}",
                data=kwargs,
                tags=["risk", event_type],
            )

            event_bus.publish(event_obj)
        except Exception as e:
            logger.error("發送事件時發生錯誤: %s", e)
