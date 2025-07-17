"""
風險檢查模組

此模組實現了各種風險檢查功能，包括：
- 停損檢查
- 停利檢查
- 倉位大小計算
- 投資組合限制檢查

主要功能：
- 提供統一的風險檢查介面
- 實現各種風險控制策略
- 支援動態風險參數調整
- 提供詳細的風險檢查結果

Example:
    >>> from src.risk_management.risk_checker import RiskChecker
    >>> checker = RiskChecker(risk_manager_core)
    >>> should_stop = checker.check_stop_loss("trailing", 100.0, 95.0)
"""

import logging
from typing import Any, Dict, Optional, Tuple

from src.core.logger import logger


class RiskChecker:
    """風險檢查器.

    提供各種風險檢查功能，包括停損、停利、倉位大小等檢查。

    Attributes:
        risk_manager: 風險管理器實例
    """

    def __init__(self, risk_manager):
        """初始化風險檢查器.

        Args:
            risk_manager: 風險管理器實例

        Example:
            >>> manager = RiskManager()
            >>> checker = RiskChecker(manager)
        """
        self.risk_manager = risk_manager
        logger.debug("風險檢查器初始化完成")

    def check_stop_loss(
        self, 
        strategy_name: str, 
        entry_price: float, 
        current_price: float, 
        **kwargs
    ) -> Tuple[bool, Optional[str]]:
        """檢查停損條件.

        Args:
            strategy_name: 停損策略名稱
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數

        Returns:
            Tuple[bool, Optional[str]]: (是否觸發停損, 停損原因)

        Raises:
            ValueError: 當策略不存在或參數無效時

        Example:
            >>> should_stop, reason = checker.check_stop_loss("trailing", 100.0, 95.0)
            >>> if should_stop:
            ...     print(f"觸發停損: {reason}")
        """
        try:
            if strategy_name not in self.risk_manager.stop_loss_strategies:
                raise ValueError(f"停損策略不存在: {strategy_name}")

            if entry_price <= 0 or current_price <= 0:
                raise ValueError("價格必須大於 0")

            strategy = self.risk_manager.stop_loss_strategies[strategy_name]
            should_stop = strategy.should_stop_loss(entry_price, current_price, **kwargs)

            if should_stop:
                reason = f"觸發 {strategy_name} 停損策略"
                logger.info(
                    "停損觸發 - 策略: %s, 進場價: %.2f, 當前價: %.2f",
                    strategy_name, entry_price, current_price
                )
                return True, reason
            else:
                return False, None

        except Exception as e:
            logger.error("停損檢查失敗: %s", e, exc_info=True)
            raise RuntimeError(f"停損檢查失敗: {e}") from e

    def check_take_profit(
        self, 
        strategy_name: str, 
        entry_price: float, 
        current_price: float, 
        **kwargs
    ) -> Tuple[bool, Optional[str]]:
        """檢查停利條件.

        Args:
            strategy_name: 停利策略名稱
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數

        Returns:
            Tuple[bool, Optional[str]]: (是否觸發停利, 停利原因)

        Raises:
            ValueError: 當策略不存在或參數無效時

        Example:
            >>> should_profit, reason = checker.check_take_profit("fixed", 100.0, 110.0)
            >>> if should_profit:
            ...     print(f"觸發停利: {reason}")
        """
        try:
            if strategy_name not in self.risk_manager.take_profit_strategies:
                raise ValueError(f"停利策略不存在: {strategy_name}")

            if entry_price <= 0 or current_price <= 0:
                raise ValueError("價格必須大於 0")

            strategy = self.risk_manager.take_profit_strategies[strategy_name]
            should_profit = strategy.should_take_profit(entry_price, current_price, **kwargs)

            if should_profit:
                reason = f"觸發 {strategy_name} 停利策略"
                logger.info(
                    "停利觸發 - 策略: %s, 進場價: %.2f, 當前價: %.2f",
                    strategy_name, entry_price, current_price
                )
                return True, reason
            else:
                return False, None

        except Exception as e:
            logger.error("停利檢查失敗: %s", e, exc_info=True)
            raise RuntimeError(f"停利檢查失敗: {e}") from e

    def calculate_position_size(
        self, 
        strategy_name: str, 
        portfolio_value: float, 
        **kwargs
    ) -> float:
        """計算倉位大小.

        Args:
            strategy_name: 倉位大小策略名稱
            portfolio_value: 投資組合價值
            **kwargs: 其他參數

        Returns:
            float: 建議的倉位大小

        Raises:
            ValueError: 當策略不存在或參數無效時

        Example:
            >>> position_size = checker.calculate_position_size("fixed", 100000.0)
            >>> print(f"建議倉位大小: {position_size}")
        """
        try:
            if strategy_name not in self.risk_manager.position_sizing_strategies:
                raise ValueError(f"倉位大小策略不存在: {strategy_name}")

            if portfolio_value <= 0:
                raise ValueError("投資組合價值必須大於 0")

            strategy = self.risk_manager.position_sizing_strategies[strategy_name]
            position_size = strategy.calculate_position_size(portfolio_value, **kwargs)

            logger.debug(
                "倉位大小計算 - 策略: %s, 組合價值: %.2f, 倉位大小: %.2f",
                strategy_name, portfolio_value, position_size
            )

            return position_size

        except Exception as e:
            logger.error("倉位大小計算失敗: %s", e, exc_info=True)
            raise RuntimeError(f"倉位大小計算失敗: {e}") from e

    def calculate_shares(
        self, 
        strategy_name: str, 
        portfolio_value: float, 
        price: float, 
        **kwargs
    ) -> int:
        """計算股票數量.

        Args:
            strategy_name: 倉位大小策略名稱
            portfolio_value: 投資組合價值
            price: 股票價格
            **kwargs: 其他參數

        Returns:
            int: 建議的股票數量

        Raises:
            ValueError: 當策略不存在或參數無效時

        Example:
            >>> shares = checker.calculate_shares("fixed", 100000.0, 50.0)
            >>> print(f"建議股票數量: {shares}")
        """
        try:
            if price <= 0:
                raise ValueError("股票價格必須大於 0")

            position_size = self.calculate_position_size(strategy_name, portfolio_value, **kwargs)
            shares = int(position_size / price)

            logger.debug(
                "股票數量計算 - 倉位大小: %.2f, 價格: %.2f, 股數: %d",
                position_size, price, shares
            )

            return shares

        except Exception as e:
            logger.error("股票數量計算失敗: %s", e, exc_info=True)
            raise RuntimeError(f"股票數量計算失敗: {e}") from e

    def check_portfolio_limits(
        self, 
        symbol: str, 
        value: float, 
        sector: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """檢查投資組合限制.

        Args:
            symbol: 股票代碼
            value: 投資價值
            sector: 行業分類

        Returns:
            Tuple[bool, Optional[str]]: (是否通過檢查, 錯誤訊息)

        Example:
            >>> passed, error = checker.check_portfolio_limits("AAPL", 10000.0, "Technology")
            >>> if not passed:
            ...     print(f"投資組合限制檢查失敗: {error}")
        """
        try:
            config = self.risk_manager.config
            portfolio_limits = config.get("portfolio_limits", {})

            # 檢查單一持倉限制
            max_position_size = portfolio_limits.get("max_position_size", 0.1)
            portfolio_value = self.risk_manager.portfolio_risk_manager.get_portfolio_value()
            
            if portfolio_value > 0:
                position_ratio = value / portfolio_value
                if position_ratio > max_position_size:
                    error_msg = f"單一持倉比例 {position_ratio:.2%} 超過限制 {max_position_size:.2%}"
                    logger.warning("投資組合限制檢查失敗: %s", error_msg)
                    return False, error_msg

            # 檢查行業曝險限制
            if sector:
                max_sector_exposure = portfolio_limits.get("max_sector_exposure", 0.3)
                current_sector_exposure = self.risk_manager.portfolio_risk_manager.get_sector_exposure(sector)
                new_sector_exposure = (current_sector_exposure + value) / portfolio_value
                
                if new_sector_exposure > max_sector_exposure:
                    error_msg = f"行業 {sector} 曝險 {new_sector_exposure:.2%} 超過限制 {max_sector_exposure:.2%}"
                    logger.warning("投資組合限制檢查失敗: %s", error_msg)
                    return False, error_msg

            return True, None

        except Exception as e:
            logger.error("投資組合限制檢查失敗: %s", e, exc_info=True)
            return False, f"檢查失敗: {e}"

    def check_circuit_breakers(self, **kwargs) -> Tuple[bool, Optional[str]]:
        """檢查熔斷器.

        Args:
            **kwargs: 檢查參數

        Returns:
            Tuple[bool, Optional[str]]: (是否觸發熔斷, 熔斷原因)

        Example:
            >>> triggered, reason = checker.check_circuit_breakers(daily_loss=0.06)
            >>> if triggered:
            ...     print(f"觸發熔斷: {reason}")
        """
        try:
            for name, breaker in self.risk_manager.circuit_breakers.items():
                if breaker.should_trigger(**kwargs):
                    reason = f"觸發 {name} 熔斷器"
                    logger.warning("熔斷器觸發: %s", reason)
                    return True, reason

            return False, None

        except Exception as e:
            logger.error("熔斷器檢查失敗: %s", e, exc_info=True)
            return False, f"檢查失敗: {e}"

    def validate_trade_parameters(
        self, 
        symbol: str, 
        quantity: int, 
        price: float, 
        trade_type: str
    ) -> Tuple[bool, Optional[str]]:
        """驗證交易參數.

        Args:
            symbol: 股票代碼
            quantity: 交易數量
            price: 交易價格
            trade_type: 交易類型 ("buy" 或 "sell")

        Returns:
            Tuple[bool, Optional[str]]: (是否有效, 錯誤訊息)

        Example:
            >>> valid, error = checker.validate_trade_parameters("AAPL", 100, 150.0, "buy")
            >>> if not valid:
            ...     print(f"交易參數無效: {error}")
        """
        try:
            # 基本參數驗證
            if not symbol or not symbol.strip():
                return False, "股票代碼不能為空"

            if quantity <= 0:
                return False, "交易數量必須大於 0"

            if price <= 0:
                return False, "交易價格必須大於 0"

            if trade_type not in ["buy", "sell"]:
                return False, "交易類型必須是 'buy' 或 'sell'"

            # 檢查投資組合限制（僅對買入交易）
            if trade_type == "buy":
                trade_value = quantity * price
                passed, error = self.check_portfolio_limits(symbol, trade_value)
                if not passed:
                    return False, error

            return True, None

        except Exception as e:
            logger.error("交易參數驗證失敗: %s", e, exc_info=True)
            return False, f"驗證失敗: {e}"
