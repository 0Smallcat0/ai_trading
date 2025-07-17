"""
風險管理器模組（重構版）

此模組實現了完整的風險管理系統，整合各個風險管理組件：
- 停損和停利策略管理
- 倉位大小控制
- 投資組合風險監控
- 熔斷器機制
- 風險指標計算和監控

主要功能：
- 提供統一的風險管理介面
- 整合各個風險管理子模組
- 支援多種風險控制策略
- 實現即時風險監控

Example:
    >>> from src.risk_management.risk_manager_refactored import RiskManager
    >>> risk_manager = RiskManager()
    >>> risk_manager.register_stop_loss_strategy("trailing", TrailingStopLoss(0.05))
    >>> should_stop = risk_manager.check_stop_loss("trailing", 100.0, 95.0)
"""

import json
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.core.logger import logger
from .circuit_breakers import CircuitBreaker
from .portfolio_risk import PortfolioRiskManager
from .position_sizing import PositionSizingStrategy
from .risk_checker import RiskChecker
from .risk_metrics import RiskMetricsCalculator
from .risk_monitoring import RiskMonitor
from .stop_loss import StopLossStrategy
from .take_profit import TakeProfitStrategy


class RiskManager:
    """風險管理器.
    
    提供完整的風險管理功能，整合各個風險管理組件。
    實現單例模式確保全局唯一性。

    Attributes:
        core: 風險管理器核心
        checker: 風險檢查器
        monitor: 風險監控器
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """實現單例模式.

        Returns:
            RiskManager: 風險管理器實例

        Example:
            >>> manager1 = RiskManager()
            >>> manager2 = RiskManager()
            >>> print(manager1 is manager2)
            True
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(RiskManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, config_path: Optional[str] = None):
        """初始化風險管理器.
        
        Args:
            config_path: 配置文件路徑

        Example:
            >>> manager = RiskManager("config/risk_config.json")
        """
        # 避免重複初始化
        if self._initialized:
            return

        try:
            # 載入配置
            self.config = self._load_config(config_path)

            # 初始化策略字典
            self.stop_loss_strategies: Dict[str, StopLossStrategy] = {}
            self.take_profit_strategies: Dict[str, TakeProfitStrategy] = {}
            self.position_sizing_strategies: Dict[str, PositionSizingStrategy] = {}
            self.circuit_breakers: Dict[str, CircuitBreaker] = {}

            # 初始化風險管理組件
            self.portfolio_risk_manager = PortfolioRiskManager()
            self.risk_metrics_calculator = None  # 將在需要時初始化

            # 初始化檢查器和監控器
            self.checker = RiskChecker(self)
            self.monitor = RiskMonitor(self)

            # 標記為已初始化
            self._initialized = True

            logger.info("風險管理器初始化完成")

        except Exception as e:
            logger.error("風險管理器初始化失敗: %s", e, exc_info=True)
            raise RuntimeError(f"風險管理器初始化失敗: {e}") from e

    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """載入配置文件.

        Args:
            config_path: 配置文件路徑

        Returns:
            Dict[str, Any]: 配置字典

        Example:
            >>> config = manager._load_config("config/risk_config.json")
        """
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info("載入配置文件: %s", config_path)
                return config
            except Exception as e:
                logger.warning("載入配置文件失敗: %s，使用預設配置", e)

        # 使用預設配置
        return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """獲取預設配置.

        Returns:
            Dict[str, Any]: 預設配置字典

        Example:
            >>> config = manager._get_default_config()
        """
        return {
            "portfolio_limits": {
                "max_position_size": 0.1,  # 單一持倉最大比例
                "max_sector_exposure": 0.3,  # 單一行業最大曝險
                "max_correlation": 0.8,  # 最大相關性
                "min_diversification": 10,  # 最小分散化持倉數
            },
            "risk_metrics": {
                "var_confidence": 0.95,  # VaR 信心水準
                "max_drawdown": 0.2,  # 最大回撤
                "sharpe_threshold": 1.0,  # 夏普比率閾值
                "volatility_threshold": 0.3,  # 波動率閾值
            },
            "circuit_breakers": {
                "daily_loss_limit": 0.05,  # 日損失限制
                "portfolio_drawdown_limit": 0.15,  # 投資組合回撤限制
                "volatility_spike_threshold": 2.0,  # 波動率激增閾值
            },
            "monitoring": {
                "enabled": True,
                "interval": 60,  # 監控間隔（秒）
                "alert_threshold": 0.8,  # 警報閾值
            }
        }

    # 策略註冊方法（委託給核心）
    def register_stop_loss_strategy(self, name: str, strategy: StopLossStrategy) -> bool:
        """註冊停損策略.

        Args:
            name: 策略名稱
            strategy: 停損策略實例

        Returns:
            bool: 是否註冊成功

        Example:
            >>> from .stop_loss import TrailingStopLoss
            >>> strategy = TrailingStopLoss(0.05)
            >>> success = manager.register_stop_loss_strategy("trailing", strategy)
        """
        return self.core.register_stop_loss_strategy(name, strategy)

    def register_take_profit_strategy(self, name: str, strategy: TakeProfitStrategy) -> bool:
        """註冊停利策略.

        Args:
            name: 策略名稱
            strategy: 停利策略實例

        Returns:
            bool: 是否註冊成功

        Example:
            >>> from .take_profit import FixedTakeProfit
            >>> strategy = FixedTakeProfit(0.1)
            >>> success = manager.register_take_profit_strategy("fixed", strategy)
        """
        return self.core.register_take_profit_strategy(name, strategy)

    def register_position_sizing_strategy(self, name: str, strategy: PositionSizingStrategy) -> bool:
        """註冊倉位大小策略.

        Args:
            name: 策略名稱
            strategy: 倉位大小策略實例

        Returns:
            bool: 是否註冊成功

        Example:
            >>> from .position_sizing import FixedPercentage
            >>> strategy = FixedPercentage(0.02)
            >>> success = manager.register_position_sizing_strategy("fixed", strategy)
        """
        return self.core.register_position_sizing_strategy(name, strategy)

    def register_circuit_breaker(self, name: str, breaker: CircuitBreaker) -> bool:
        """註冊熔斷器.

        Args:
            name: 熔斷器名稱
            breaker: 熔斷器實例

        Returns:
            bool: 是否註冊成功

        Example:
            >>> from .circuit_breakers import DailyLossBreaker
            >>> breaker = DailyLossBreaker(0.05)
            >>> success = manager.register_circuit_breaker("daily_loss", breaker)
        """
        return self.core.register_circuit_breaker(name, breaker)

    # 風險檢查方法（委託給檢查器）
    def check_stop_loss(
        self, strategy_name: str, entry_price: float, current_price: float, **kwargs
    ) -> Tuple[bool, Optional[str]]:
        """檢查停損條件.

        Args:
            strategy_name: 停損策略名稱
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數

        Returns:
            Tuple[bool, Optional[str]]: (是否觸發停損, 停損原因)

        Example:
            >>> should_stop, reason = manager.check_stop_loss("trailing", 100.0, 95.0)
        """
        return self.checker.check_stop_loss(strategy_name, entry_price, current_price, **kwargs)

    def check_take_profit(
        self, strategy_name: str, entry_price: float, current_price: float, **kwargs
    ) -> Tuple[bool, Optional[str]]:
        """檢查停利條件.

        Args:
            strategy_name: 停利策略名稱
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數

        Returns:
            Tuple[bool, Optional[str]]: (是否觸發停利, 停利原因)

        Example:
            >>> should_profit, reason = manager.check_take_profit("fixed", 100.0, 110.0)
        """
        return self.checker.check_take_profit(strategy_name, entry_price, current_price, **kwargs)

    def calculate_position_size(self, strategy_name: str, portfolio_value: float, **kwargs) -> float:
        """計算倉位大小.

        Args:
            strategy_name: 倉位大小策略名稱
            portfolio_value: 投資組合價值
            **kwargs: 其他參數

        Returns:
            float: 建議的倉位大小

        Example:
            >>> position_size = manager.calculate_position_size("fixed", 100000.0)
        """
        return self.checker.calculate_position_size(strategy_name, portfolio_value, **kwargs)

    def calculate_shares(
        self, strategy_name: str, portfolio_value: float, price: float, **kwargs
    ) -> int:
        """計算股票數量.

        Args:
            strategy_name: 倉位大小策略名稱
            portfolio_value: 投資組合價值
            price: 股票價格
            **kwargs: 其他參數

        Returns:
            int: 建議的股票數量

        Example:
            >>> shares = manager.calculate_shares("fixed", 100000.0, 50.0)
        """
        return self.checker.calculate_shares(strategy_name, portfolio_value, price, **kwargs)

    def check_portfolio_limits(
        self, symbol: str, value: float, sector: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """檢查投資組合限制.

        Args:
            symbol: 股票代碼
            value: 投資價值
            sector: 行業分類

        Returns:
            Tuple[bool, Optional[str]]: (是否通過檢查, 錯誤訊息)

        Example:
            >>> passed, error = manager.check_portfolio_limits("AAPL", 10000.0, "Technology")
        """
        return self.checker.check_portfolio_limits(symbol, value, sector)

    def check_circuit_breakers(self, **kwargs) -> Tuple[bool, Optional[str]]:
        """檢查熔斷器.

        Args:
            **kwargs: 檢查參數

        Returns:
            Tuple[bool, Optional[str]]: (是否觸發熔斷, 熔斷原因)

        Example:
            >>> triggered, reason = manager.check_circuit_breakers(daily_loss=0.06)
        """
        return self.checker.check_circuit_breakers(**kwargs)

    # 監控方法（委託給監控器）
    def start_monitoring(self) -> bool:
        """啟動風險監控.

        Returns:
            bool: 是否啟動成功

        Example:
            >>> success = manager.start_monitoring()
        """
        return self.monitor.start_monitoring()

    def stop_monitoring(self) -> bool:
        """停止風險監控.

        Returns:
            bool: 是否停止成功

        Example:
            >>> success = manager.stop_monitoring()
        """
        return self.monitor.stop_monitoring()

    def stop_trading(self, reason: str) -> None:
        """停止交易.

        Args:
            reason: 停止交易的原因

        Example:
            >>> manager.stop_trading("觸發日損失限制")
        """
        self.monitor.stop_trading(reason)

    def resume_trading(self, reason: str) -> None:
        """恢復交易.

        Args:
            reason: 恢復交易的原因

        Example:
            >>> manager.resume_trading("風險條件已改善")
        """
        self.monitor.resume_trading(reason)

    def is_trading_enabled(self) -> bool:
        """檢查交易是否啟用.

        Returns:
            bool: 交易是否啟用

        Example:
            >>> enabled = manager.is_trading_enabled()
        """
        return self.monitor.is_trading_enabled()

    def update_risk_metrics(self, returns: pd.Series, risk_free_rate: float = 0.0) -> None:
        """更新風險指標.

        Args:
            returns: 收益率序列
            risk_free_rate: 無風險利率

        Example:
            >>> returns = pd.Series([0.01, -0.02, 0.015, 0.005])
            >>> manager.update_risk_metrics(returns, 0.02)
        """
        self.monitor.update_risk_metrics(returns, risk_free_rate)

    def get_risk_metrics(self) -> Dict[str, float]:
        """獲取當前風險指標.

        Returns:
            Dict[str, float]: 風險指標字典

        Example:
            >>> metrics = manager.get_risk_metrics()
        """
        return self.monitor.get_risk_metrics()

    def get_risk_events(
        self, event_type: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """獲取風險事件.

        Args:
            event_type: 事件類型過濾器
            limit: 返回事件數量限制

        Returns:
            List[Dict[str, Any]]: 風險事件列表

        Example:
            >>> events = manager.get_risk_events("stop_loss_triggered", 50)
        """
        return self.monitor.get_risk_events(event_type, limit)

    # 配置管理方法
    def get_config(self) -> Dict[str, Any]:
        """獲取當前配置.

        Returns:
            Dict[str, Any]: 當前配置字典

        Example:
            >>> config = manager.get_config()
        """
        return self.core.get_config()

    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """更新配置.

        Args:
            new_config: 新配置字典

        Returns:
            bool: 是否更新成功

        Example:
            >>> new_config = {"portfolio_limits": {"max_position_size": 0.15}}
            >>> success = manager.update_config(new_config)
        """
        return self.core.update_config(new_config)
