"""策略管理器模組

此模組負責管理各種風險管理策略，包括停損、停利、倉位大小和熔斷機制。
"""

from typing import Dict, Optional

from src.core.logger import logger

from .circuit_breakers import CircuitBreaker
from .position_sizing import PositionSizingStrategy
from .stop_loss import StopLossStrategy
from .take_profit import TakeProfitStrategy


class StrategyManager:
    """策略管理器

    管理各種風險管理策略的註冊、檢查和執行。
    """

    def __init__(self):
        """初始化策略管理器"""
        # 停損策略
        self.stop_loss_strategies: Dict[str, StopLossStrategy] = {}

        # 停利策略
        self.take_profit_strategies: Dict[str, TakeProfitStrategy] = {}

        # 倉位大小策略
        self.position_sizing_strategies: Dict[str, PositionSizingStrategy] = {}

        # 熔斷機制
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        logger.info("策略管理器已初始化")

    def register_stop_loss_strategy(
        self, name: str, strategy: StopLossStrategy
    ) -> bool:
        """註冊停損策略

        Args:
            name: 策略名稱
            strategy: 停損策略

        Returns:
            bool: 是否成功註冊
        """
        if name in self.stop_loss_strategies:
            logger.warning("停損策略 '%s' 已存在", name)
            return False

        self.stop_loss_strategies[name] = strategy
        logger.info("已註冊停損策略: %s", name)
        return True

    def register_take_profit_strategy(
        self, name: str, strategy: TakeProfitStrategy
    ) -> bool:
        """註冊停利策略

        Args:
            name: 策略名稱
            strategy: 停利策略

        Returns:
            bool: 是否成功註冊
        """
        if name in self.take_profit_strategies:
            logger.warning("停利策略 '%s' 已存在", name)
            return False

        self.take_profit_strategies[name] = strategy
        logger.info("已註冊停利策略: %s", name)
        return True

    def register_position_sizing_strategy(
        self, name: str, strategy: PositionSizingStrategy
    ) -> bool:
        """註冊倉位大小策略

        Args:
            name: 策略名稱
            strategy: 倉位大小策略

        Returns:
            bool: 是否成功註冊
        """
        if name in self.position_sizing_strategies:
            logger.warning("倉位大小策略 '%s' 已存在", name)
            return False

        self.position_sizing_strategies[name] = strategy
        logger.info("已註冊倉位大小策略: %s", name)
        return True

    def register_circuit_breaker(self, name: str, breaker: CircuitBreaker) -> bool:
        """註冊熔斷機制

        Args:
            name: 熔斷機制名稱
            breaker: 熔斷機制

        Returns:
            bool: 是否成功註冊
        """
        if name in self.circuit_breakers:
            logger.warning("熔斷機制 '%s' 已存在", name)
            return False

        self.circuit_breakers[name] = breaker
        logger.info("已註冊熔斷機制: %s", name)
        return True

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
        if strategy_name not in self.stop_loss_strategies:
            logger.warning("停損策略 '%s' 不存在", strategy_name)
            return False

        strategy = self.stop_loss_strategies[strategy_name]

        # 更新策略
        strategy.update(current_price, **kwargs)

        # 檢查是否應該停損
        should_stop = strategy.should_stop_out(entry_price, current_price, **kwargs)

        if should_stop:
            logger.info(
                "觸發停損策略 '%s': 進場價格 %s, 當前價格 %s",
                strategy_name,
                entry_price,
                current_price,
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
        if strategy_name not in self.take_profit_strategies:
            logger.warning("停利策略 '%s' 不存在", strategy_name)
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
                "觸發停利策略 '%s': 進場價格 %s, 當前價格 %s",
                strategy_name,
                entry_price,
                current_price,
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
        if strategy_name not in self.position_sizing_strategies:
            logger.warning("倉位大小策略 '%s' 不存在", strategy_name)
            return 0.0

        strategy = self.position_sizing_strategies[strategy_name]

        # 計算倉位大小
        position_size = strategy.calculate_position_size(portfolio_value, **kwargs)

        logger.info(
            "計算倉位大小: 策略 '%s', 投資組合價值 %s, 倉位大小 %s",
            strategy_name,
            portfolio_value,
            position_size,
        )

        return position_size

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
        if strategy_name not in self.position_sizing_strategies:
            logger.warning("倉位大小策略 '%s' 不存在", strategy_name)
            return 0

        strategy = self.position_sizing_strategies[strategy_name]

        # 計算股數
        shares = strategy.calculate_shares(portfolio_value, price, **kwargs)

        logger.info(
            "計算股數: 策略 '%s', 投資組合價值 %s, 價格 %s, 股數 %s",
            strategy_name,
            portfolio_value,
            price,
            shares,
        )

        return shares

    def check_circuit_breakers(self, **kwargs) -> Optional[str]:
        """檢查熔斷機制

        Args:
            **kwargs: 其他參數

        Returns:
            Optional[str]: 觸發的熔斷機制名稱，如果沒有觸發則返回 None
        """
        # 檢查所有熔斷機制
        for name, breaker in self.circuit_breakers.items():
            try:
                if breaker.check(**kwargs):
                    logger.warning("熔斷機制 '%s' 已觸發", name)
                    return name
            except Exception as e:
                logger.error("檢查熔斷機制 '%s' 時發生錯誤: %s", name, e)

        return None

    def reset_circuit_breakers(self) -> None:
        """重置所有熔斷機制"""
        for breaker in self.circuit_breakers.values():
            breaker.reset()
        logger.info("已重置所有熔斷機制")

    def get_strategy_names(self, strategy_type: str) -> list:
        """獲取策略名稱列表

        Args:
            strategy_type: 策略類型 ('stop_loss', 'take_profit', 'position_sizing', 'circuit_breaker')

        Returns:
            list: 策略名稱列表
        """
        if strategy_type == "stop_loss":
            return list(self.stop_loss_strategies.keys())
        elif strategy_type == "take_profit":
            return list(self.take_profit_strategies.keys())
        elif strategy_type == "position_sizing":
            return list(self.position_sizing_strategies.keys())
        elif strategy_type == "circuit_breaker":
            return list(self.circuit_breakers.keys())
        else:
            logger.warning("未知的策略類型: %s", strategy_type)
            return []

    def remove_strategy(self, strategy_type: str, name: str) -> bool:
        """移除策略

        Args:
            strategy_type: 策略類型
            name: 策略名稱

        Returns:
            bool: 是否成功移除
        """
        try:
            if strategy_type == "stop_loss" and name in self.stop_loss_strategies:
                del self.stop_loss_strategies[name]
            elif strategy_type == "take_profit" and name in self.take_profit_strategies:
                del self.take_profit_strategies[name]
            elif (
                strategy_type == "position_sizing"
                and name in self.position_sizing_strategies
            ):
                del self.position_sizing_strategies[name]
            elif strategy_type == "circuit_breaker" and name in self.circuit_breakers:
                del self.circuit_breakers[name]
            else:
                logger.warning("策略 '%s' 不存在於類型 '%s'", name, strategy_type)
                return False

            logger.info("已移除策略: %s (%s)", name, strategy_type)
            return True
        except Exception as e:
            logger.error("移除策略時發生錯誤: %s", e)
            return False
