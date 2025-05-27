"""回測策略管理模組

此模組負責管理回測策略的註冊、初始化和執行。
"""

import logging
from typing import Dict, Any
import numpy as np
import pandas as pd

from .backtest_config import BacktestConfig

# 設定日誌
logger = logging.getLogger(__name__)


class BacktestStrategyManager:
    """回測策略管理器"""

    def __init__(self):
        """初始化策略管理器"""
        self.strategy_registry = {}
        self._register_default_strategies()

    def register_strategy(self, strategy_id: str, strategy_factory):
        """註冊策略

        Args:
            strategy_id: 策略ID
            strategy_factory: 策略工廠函數
        """
        self.strategy_registry[strategy_id] = strategy_factory
        logger.info("策略已註冊: %s", strategy_id)

    def get_available_strategies(self) -> Dict[str, str]:
        """獲取可用策略列表

        Returns:
            Dict[str, str]: 策略ID到名稱的映射
        """
        return {
            strategy_id: self._get_strategy_name(strategy_id)
            for strategy_id in self.strategy_registry.keys()
        }

    def initialize_strategy(
        self, strategy_id: str, config: BacktestConfig
    ) -> Dict[str, Any]:
        """初始化策略

        Args:
            strategy_id: 策略ID
            config: 回測配置

        Returns:
            Dict[str, Any]: 策略實例

        Raises:
            ValueError: 當策略ID不存在時
        """
        if strategy_id not in self.strategy_registry:
            raise ValueError(f"未知的策略ID: {strategy_id}")

        strategy_factory = self.strategy_registry[strategy_id]
        strategy = strategy_factory(config)

        logger.info("策略已初始化: %s", strategy_id)
        return strategy

    def generate_signals(
        self, strategy: Dict[str, Any], market_data: pd.DataFrame
    ) -> pd.DataFrame:
        """生成交易信號

        Args:
            strategy: 策略實例
            market_data: 市場資料

        Returns:
            pd.DataFrame: 交易信號
        """
        strategy_type = strategy.get("type", "unknown")

        if strategy_type == "ma_cross":
            return self._generate_ma_cross_signals(strategy, market_data)
        elif strategy_type == "buy_hold":
            return self._generate_buy_hold_signals(strategy, market_data)
        elif strategy_type == "mean_reversion":
            return self._generate_mean_reversion_signals(strategy, market_data)
        else:
            # 預設使用隨機信號
            return self._generate_random_signals(market_data)

    def _register_default_strategies(self):
        """註冊預設策略"""
        self.strategy_registry = {
            "ma_cross": self._create_ma_cross_strategy,
            "buy_hold": self._create_buy_hold_strategy,
            "mean_reversion": self._create_mean_reversion_strategy,
        }

    def _get_strategy_name(self, strategy_id: str) -> str:
        """獲取策略名稱"""
        name_mapping = {
            "ma_cross": "移動平均線交叉策略",
            "buy_hold": "買入持有策略",
            "mean_reversion": "均值回歸策略",
        }
        return name_mapping.get(strategy_id, strategy_id)

    def _create_ma_cross_strategy(self, config: BacktestConfig) -> Dict[str, Any]:
        """創建移動平均線交叉策略"""
        return {
            "name": "移動平均線交叉策略",
            "type": "ma_cross",
            "params": {
                "short_window": 5,
                "long_window": 20,
            },
        }

    def _create_buy_hold_strategy(self, config: BacktestConfig) -> Dict[str, Any]:
        """創建買入持有策略"""
        return {
            "name": "買入持有策略",
            "type": "buy_hold",
            "params": {},
        }

    def _create_mean_reversion_strategy(self, config: BacktestConfig) -> Dict[str, Any]:
        """創建均值回歸策略"""
        return {
            "name": "均值回歸策略",
            "type": "mean_reversion",
            "params": {
                "lookback_window": 20,
                "threshold": 2.0,
            },
        }

    def _generate_ma_cross_signals(
        self, strategy: Dict[str, Any], market_data: pd.DataFrame
    ) -> pd.DataFrame:
        """生成移動平均線交叉信號"""
        params = strategy.get("params", {})
        short_window = params.get("short_window", 5)
        long_window = params.get("long_window", 20)

        signals = market_data.copy()
        signals["signal"] = 0

        # 按股票分組計算移動平均線
        for symbol in signals["symbol"].unique():
            symbol_mask = signals["symbol"] == symbol
            symbol_data = signals[symbol_mask].copy()

            # 計算移動平均線
            symbol_data["ma_short"] = symbol_data["close"].rolling(short_window).mean()
            symbol_data["ma_long"] = symbol_data["close"].rolling(long_window).mean()

            # 生成信號
            symbol_data["signal"] = 0
            symbol_data.loc[
                symbol_data["ma_short"] > symbol_data["ma_long"], "signal"
            ] = 1
            symbol_data.loc[
                symbol_data["ma_short"] < symbol_data["ma_long"], "signal"
            ] = -1

            # 更新原始數據
            signals.loc[symbol_mask, "signal"] = symbol_data["signal"]

        return signals[["symbol", "date", "signal"]]

    def _generate_buy_hold_signals(
        self, strategy: Dict[str, Any], market_data: pd.DataFrame
    ) -> pd.DataFrame:
        """生成買入持有信號"""
        signals = market_data.copy()
        signals["signal"] = 0

        # 在第一天買入，之後持有
        for symbol in signals["symbol"].unique():
            symbol_mask = signals["symbol"] == symbol
            first_idx = signals[symbol_mask].index[0]
            signals.loc[first_idx, "signal"] = 1

        return signals[["symbol", "date", "signal"]]

    def _generate_mean_reversion_signals(
        self, strategy: Dict[str, Any], market_data: pd.DataFrame
    ) -> pd.DataFrame:
        """生成均值回歸信號"""
        params = strategy.get("params", {})
        lookback_window = params.get("lookback_window", 20)
        threshold = params.get("threshold", 2.0)

        signals = market_data.copy()
        signals["signal"] = 0

        # 按股票分組計算均值回歸信號
        for symbol in signals["symbol"].unique():
            symbol_mask = signals["symbol"] == symbol
            symbol_data = signals[symbol_mask].copy()

            # 計算移動平均和標準差
            symbol_data["ma"] = symbol_data["close"].rolling(lookback_window).mean()
            symbol_data["std"] = symbol_data["close"].rolling(lookback_window).std()

            # 計算Z分數
            symbol_data["z_score"] = (
                symbol_data["close"] - symbol_data["ma"]
            ) / symbol_data["std"]

            # 生成信號
            symbol_data["signal"] = 0
            symbol_data.loc[symbol_data["z_score"] < -threshold, "signal"] = 1  # 買入
            symbol_data.loc[symbol_data["z_score"] > threshold, "signal"] = -1  # 賣出

            # 更新原始數據
            signals.loc[symbol_mask, "signal"] = symbol_data["signal"]

        return signals[["symbol", "date", "signal"]]

    def _generate_random_signals(self, market_data: pd.DataFrame) -> pd.DataFrame:
        """生成隨機信號（用於測試）"""
        signals = market_data.copy()
        signals["signal"] = np.random.choice(
            [0, 1, -1], size=len(signals), p=[0.8, 0.1, 0.1]
        )
        return signals[["symbol", "date", "signal"]]
