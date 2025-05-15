"""
風險管理器模組

此模組實現了風險管理器，整合了各種風險管理策略和機制。
"""

import json
import os
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from src.core.event_monitor import Event, EventSeverity, EventSource, EventType
from src.core.logger import logger

from .circuit_breakers import CircuitBreaker
from .portfolio_risk import PortfolioRiskManager
from .position_sizing import PositionSizingStrategy
from .risk_metrics import RiskMetricsCalculator
from .stop_loss import StopLossStrategy
from .take_profit import TakeProfitStrategy


class RiskManager:
    """
    風險管理器

    整合各種風險管理策略和機制，提供全面的風險管理功能。
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """實現單例模式"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(RiskManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化風險管理器

        Args:
            config_path: 配置文件路徑
        """
        # 避免重複初始化
        if self._initialized:
            return

        # 加載配置
        self.config = self._load_config(config_path)

        # 停損策略
        self.stop_loss_strategies: Dict[str, StopLossStrategy] = {}

        # 停利策略
        self.take_profit_strategies: Dict[str, TakeProfitStrategy] = {}

        # 倉位大小策略
        self.position_sizing_strategies: Dict[str, PositionSizingStrategy] = {}

        # 投資組合風險管理器
        self.portfolio_risk_manager = PortfolioRiskManager(
            max_position_percent=self.config.get("max_position_percent", 0.2),
            max_sector_percent=self.config.get("max_sector_percent", 0.4),
        )

        # 熔斷機制
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # 交易狀態
        self.trading_enabled = True

        # 風險事件
        self.risk_events: List[Dict[str, Any]] = []

        # 風險指標
        self.risk_metrics = {}

        # 監控線程
        self.monitoring_thread = None
        self.running = False

        # 標記為已初始化
        self._initialized = True

        logger.info("風險管理器已初始化")

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        加載配置

        Args:
            config_path: 配置文件路徑

        Returns:
            Dict[str, Any]: 配置字典
        """
        default_config = {
            "max_position_percent": 0.2,
            "max_sector_percent": 0.4,
            "max_drawdown": 0.2,
            "max_daily_loss": 0.02,
            "max_weekly_loss": 0.05,
            "max_monthly_loss": 0.1,
            "monitoring_interval": 60,
            "log_level": "INFO",
        }

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # 合併默認配置
                    return {**default_config, **config}
            except Exception as e:
                logger.error(f"加載配置文件時發生錯誤: {e}")

        return default_config

    def register_stop_loss_strategy(
        self, name: str, strategy: StopLossStrategy
    ) -> bool:
        """
        註冊停損策略

        Args:
            name: 策略名稱
            strategy: 停損策略

        Returns:
            bool: 是否成功註冊
        """
        if name in self.stop_loss_strategies:
            logger.warning(f"停損策略 '{name}' 已存在")
            return False

        self.stop_loss_strategies[name] = strategy
        logger.info(f"已註冊停損策略: {name}")
        return True

    def register_take_profit_strategy(
        self, name: str, strategy: TakeProfitStrategy
    ) -> bool:
        """
        註冊停利策略

        Args:
            name: 策略名稱
            strategy: 停利策略

        Returns:
            bool: 是否成功註冊
        """
        if name in self.take_profit_strategies:
            logger.warning(f"停利策略 '{name}' 已存在")
            return False

        self.take_profit_strategies[name] = strategy
        logger.info(f"已註冊停利策略: {name}")
        return True

    def register_position_sizing_strategy(
        self, name: str, strategy: PositionSizingStrategy
    ) -> bool:
        """
        註冊倉位大小策略

        Args:
            name: 策略名稱
            strategy: 倉位大小策略

        Returns:
            bool: 是否成功註冊
        """
        if name in self.position_sizing_strategies:
            logger.warning(f"倉位大小策略 '{name}' 已存在")
            return False

        self.position_sizing_strategies[name] = strategy
        logger.info(f"已註冊倉位大小策略: {name}")
        return True

    def register_circuit_breaker(self, name: str, breaker: CircuitBreaker) -> bool:
        """
        註冊熔斷機制

        Args:
            name: 熔斷機制名稱
            breaker: 熔斷機制

        Returns:
            bool: 是否成功註冊
        """
        if name in self.circuit_breakers:
            logger.warning(f"熔斷機制 '{name}' 已存在")
            return False

        self.circuit_breakers[name] = breaker
        logger.info(f"已註冊熔斷機制: {name}")
        return True

    def check_stop_loss(
        self, strategy_name: str, entry_price: float, current_price: float, **kwargs
    ) -> bool:
        """
        檢查停損

        Args:
            strategy_name: 策略名稱
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數

        Returns:
            bool: 是否應該停損
        """
        if strategy_name not in self.stop_loss_strategies:
            logger.warning(f"停損策略 '{strategy_name}' 不存在")
            return False

        strategy = self.stop_loss_strategies[strategy_name]

        # 更新策略
        strategy.update(current_price, **kwargs)

        # 檢查是否應該停損
        should_stop = strategy.should_stop_out(entry_price, current_price, **kwargs)

        if should_stop:
            logger.info(
                f"觸發停損策略 '{strategy_name}': 進場價格 {entry_price}, 當前價格 {current_price}"
            )

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
        """
        檢查停利

        Args:
            strategy_name: 策略名稱
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數

        Returns:
            bool: 是否應該停利
        """
        if strategy_name not in self.take_profit_strategies:
            logger.warning(f"停利策略 '{strategy_name}' 不存在")
            return False

        strategy = self.take_profit_strategies[strategy_name]

        # 更新策略
        strategy.update(current_price, **kwargs)

        # 檢查是否應該停利
        should_take_profit = strategy.should_take_profit(
            entry_price, current_price, **kwargs
        )

        if should_take_profit:
            logger.info(
                f"觸發停利策略 '{strategy_name}': 進場價格 {entry_price}, 當前價格 {current_price}"
            )

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
        """
        計算倉位大小

        Args:
            strategy_name: 策略名稱
            portfolio_value: 投資組合價值
            **kwargs: 其他參數

        Returns:
            float: 倉位大小（金額）
        """
        if strategy_name not in self.position_sizing_strategies:
            logger.warning(f"倉位大小策略 '{strategy_name}' 不存在")
            return 0.0

        strategy = self.position_sizing_strategies[strategy_name]

        # 計算倉位大小
        position_size = strategy.calculate_position_size(portfolio_value, **kwargs)

        logger.info(
            f"計算倉位大小: 策略 '{strategy_name}', 投資組合價值 {portfolio_value}, 倉位大小 {position_size}"
        )

        return position_size

    def calculate_shares(
        self, strategy_name: str, portfolio_value: float, price: float, **kwargs
    ) -> int:
        """
        計算股數

        Args:
            strategy_name: 策略名稱
            portfolio_value: 投資組合價值
            price: 股票價格
            **kwargs: 其他參數

        Returns:
            int: 股數
        """
        if strategy_name not in self.position_sizing_strategies:
            logger.warning(f"倉位大小策略 '{strategy_name}' 不存在")
            return 0

        strategy = self.position_sizing_strategies[strategy_name]

        # 計算股數
        shares = strategy.calculate_shares(portfolio_value, price, **kwargs)

        logger.info(
            f"計算股數: 策略 '{strategy_name}', 投資組合價值 {portfolio_value}, 價格 {price}, 股數 {shares}"
        )

        return shares

    def check_portfolio_limits(
        self, symbol: str, value: float, sector: Optional[str] = None
    ) -> bool:
        """
        檢查投資組合限制

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
            logger.warning(f"倉位 {symbol} 不符合投資組合限制")

            # 記錄風險事件
            self._record_risk_event(
                event_type="portfolio_limit", symbol=symbol, value=value, sector=sector
            )

        return result

    def check_circuit_breakers(self, **kwargs) -> bool:
        """
        檢查熔斷機制

        Args:
            **kwargs: 其他參數

        Returns:
            bool: 是否觸發熔斷
        """
        # 如果交易已停止，則直接返回 True
        if not self.trading_enabled:
            return True

        # 檢查所有熔斷機制
        for name, breaker in self.circuit_breakers.items():
            try:
                if breaker.check(**kwargs):
                    logger.warning(f"熔斷機制 '{name}' 已觸發")

                    # 停止交易
                    self.stop_trading(
                        f"熔斷機制 '{name}' 已觸發: {breaker.trigger_reason}"
                    )

                    # 記錄風險事件
                    self._record_risk_event(
                        event_type="circuit_breaker",
                        breaker_name=name,
                        trigger_reason=breaker.trigger_reason,
                    )

                    return True
            except Exception as e:
                logger.error(f"檢查熔斷機制 '{name}' 時發生錯誤: {e}")

        return False

    def stop_trading(self, reason: str) -> None:
        """
        停止交易

        Args:
            reason: 停止原因
        """
        self.trading_enabled = False
        logger.warning(f"交易已停止: {reason}")

        # 記錄風險事件
        self._record_risk_event(event_type="trading_stopped", reason=reason)

        # 發送事件
        try:
            from src.core.event_monitor import event_bus

            event = Event(
                event_type=EventType.RISK,
                source=EventSource.RISK_MANAGER,
                subject="trading_stopped",
                severity=EventSeverity.ERROR,
                message=f"交易已停止: {reason}",
                data={"reason": reason},
                tags=["risk", "trading_stopped"],
            )

            event_bus.publish(event)
        except Exception as e:
            logger.error(f"發送事件時發生錯誤: {e}")

    def resume_trading(self, reason: str) -> None:
        """
        恢復交易

        Args:
            reason: 恢復原因
        """
        self.trading_enabled = True
        logger.info(f"交易已恢復: {reason}")

        # 重置所有熔斷機制
        for breaker in self.circuit_breakers.values():
            breaker.reset()

        # 記錄風險事件
        self._record_risk_event(event_type="trading_resumed", reason=reason)

        # 發送事件
        try:
            from src.core.event_monitor import event_bus

            event = Event(
                event_type=EventType.RISK,
                source=EventSource.RISK_MANAGER,
                subject="trading_resumed",
                severity=EventSeverity.INFO,
                message=f"交易已恢復: {reason}",
                data={"reason": reason},
                tags=["risk", "trading_resumed"],
            )

            event_bus.publish(event)
        except Exception as e:
            logger.error(f"發送事件時發生錯誤: {e}")

    def is_trading_enabled(self) -> bool:
        """
        檢查交易是否啟用

        Returns:
            bool: 交易是否啟用
        """
        return self.trading_enabled

    def update_risk_metrics(
        self, returns: pd.Series, risk_free_rate: float = 0.0
    ) -> Dict[str, float]:
        """
        更新風險指標

        Args:
            returns: 收益率序列
            risk_free_rate: 無風險利率

        Returns:
            Dict[str, float]: 風險指標
        """
        # 創建風險指標計算器
        calculator = RiskMetricsCalculator(returns, risk_free_rate)

        # 計算所有風險指標
        self.risk_metrics = calculator.calculate_all_metrics()

        logger.info(f"更新風險指標: {self.risk_metrics}")

        return self.risk_metrics

    def get_risk_metrics(self) -> Dict[str, float]:
        """
        獲取風險指標

        Returns:
            Dict[str, float]: 風險指標
        """
        return self.risk_metrics

    def _record_risk_event(self, event_type: str, **kwargs) -> None:
        """
        記錄風險事件

        Args:
            event_type: 事件類型
            **kwargs: 其他參數
        """
        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": kwargs,
        }

        self.risk_events.append(event)

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
            logger.error(f"發送事件時發生錯誤: {e}")

    def get_risk_events(
        self, event_type: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        獲取風險事件

        Args:
            event_type: 事件類型，如果為 None 則獲取所有事件
            limit: 最大事件數量

        Returns:
            List[Dict[str, Any]]: 風險事件列表
        """
        if event_type:
            events = [
                event for event in self.risk_events if event["type"] == event_type
            ]
        else:
            events = self.risk_events.copy()

        # 按時間降序排序
        events.sort(key=lambda x: x["timestamp"], reverse=True)

        # 限制數量
        return events[:limit]

    def start_monitoring(self) -> bool:
        """
        啟動監控

        Returns:
            bool: 是否成功啟動
        """
        if self.running:
            logger.warning("風險監控已經在運行中")
            return False

        self.running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()

        logger.info("風險監控已啟動")
        return True

    def stop_monitoring(self) -> bool:
        """
        停止監控

        Returns:
            bool: 是否成功停止
        """
        if not self.running:
            logger.warning("風險監控未運行")
            return False

        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)

        logger.info("風險監控已停止")
        return True

    def _monitoring_loop(self) -> None:
        """監控循環"""
        while self.running:
            try:
                # 檢查熔斷機制
                self.check_circuit_breakers()

                # 等待下一個監控間隔
                time.sleep(self.config.get("monitoring_interval", 60))
            except Exception as e:
                logger.error(f"風險監控循環發生錯誤: {e}")
                time.sleep(10)  # 發生錯誤時等待較長時間


# 創建全局風險管理器實例
risk_manager = RiskManager()
