# -*- coding: utf-8 -*-
"""
RSI策略模組

此模組實現基於相對強弱指標(RSI)的交易策略。

主要功能：
- RSI指標計算
- 超買超賣訊號生成
- 參數優化
- 策略評估
"""

import logging
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from ..base import Strategy, ParameterError, DataValidationError

# 設定日誌
logger = logging.getLogger(__name__)


class RSIStrategy(Strategy):
    """
    RSI (相對強弱指標) 策略。

    當RSI低於超賣閾值時產生買入訊號，
    當RSI高於超買閾值時產生賣出訊號。

    Attributes:
        rsi_window (int): RSI計算窗口大小
        overbought (float): 超買閾值
        oversold (float): 超賣閾值

    Example:
        >>> strategy = RSIStrategy(rsi_window=14, overbought=70, oversold=30)
        >>> signals = strategy.generate_signals(price_data)
        >>> metrics = strategy.evaluate(price_data, signals)
    """

    def __init__(
        self,
        rsi_window: int = 14,
        overbought: float = 70.0,
        oversold: float = 30.0,
        **kwargs: Any,
    ) -> None:
        """
        初始化RSI策略。

        Args:
            rsi_window: RSI計算窗口大小，通常為14
            overbought: 超買閾值，通常為70
            oversold: 超賣閾值，通常為30
            **kwargs: 其他參數

        Raises:
            ParameterError: 當參數不符合要求時
        """
        super().__init__(
            name="RSI",
            rsi_window=rsi_window,
            overbought=overbought,
            oversold=oversold,
            **kwargs,
        )
        self.rsi_window = rsi_window
        self.overbought = overbought
        self.oversold = oversold

    def _validate_parameters(self) -> None:
        """
        驗證策略參數。

        Raises:
            ParameterError: 當參數不符合要求時
        """
        if not isinstance(self.rsi_window, int) or self.rsi_window <= 0:
            raise ParameterError(f"rsi_window 必須是正整數，得到: {self.rsi_window}")

        if not (0 <= self.oversold <= 100):
            raise ParameterError(f"oversold 必須在0-100之間，得到: {self.oversold}")

        if not (0 <= self.overbought <= 100):
            raise ParameterError(f"overbought 必須在0-100之間，得到: {self.overbought}")

        if self.oversold >= self.overbought:
            raise ParameterError(
                f"oversold ({self.oversold}) 必須小於 overbought ({self.overbought})"
            )

    def _calculate_rsi(self, price_series: pd.Series) -> pd.Series:
        """
        計算RSI指標。

        Args:
            price_series: 價格序列

        Returns:
            RSI值序列 (0-100)
        """
        # 計算價格變化
        delta = price_series.diff()

        # 分離上漲和下跌
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # 計算平均收益和平均損失
        avg_gain = gain.rolling(window=self.rsi_window).mean()
        avg_loss = loss.rolling(window=self.rsi_window).mean()

        # 計算相對強度
        rs = avg_gain / avg_loss

        # 計算RSI
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def generate_signals(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """
        生成RSI策略訊號。

        Args:
            price_data: 價格資料，必須包含 '收盤價' 欄位

        Returns:
            包含交易訊號的資料框架，包含以下欄位：
            - signal: 主要訊號 (1=買入, -1=賣出, 0=觀望)
            - buy_signal: 買入訊號 (1=買入, 0=無動作)
            - sell_signal: 賣出訊號 (1=賣出, 0=無動作)
            - rsi: RSI值
            - position: 當前倉位 (1=持有, 0=空倉)

        Raises:
            DataValidationError: 當輸入資料格式不正確時
        """
        # 驗證輸入資料
        self._validate_price_data(price_data)

        # 計算RSI
        price_series = price_data["收盤價"].astype(float)
        rsi = self._calculate_rsi(price_series)

        # 生成訊號
        signals = pd.DataFrame(index=price_data.index)
        signals["rsi"] = rsi

        # 初始化訊號
        signals["signal"] = 0
        signals["position"] = 0

        # RSI策略邏輯：
        # 當RSI < oversold時，產生買入訊號
        # 當RSI > overbought時，產生賣出訊號
        # 使用狀態機來管理倉位

        current_position = 0
        buy_signals = []
        sell_signals = []
        positions = []

        for i, rsi_value in enumerate(rsi):
            if pd.isna(rsi_value):
                buy_signals.append(0)
                sell_signals.append(0)
                positions.append(current_position)
                continue

            buy_signal = 0
            sell_signal = 0

            # 買入條件：RSI低於超賣線且當前無倉位
            if rsi_value < self.oversold and current_position == 0:
                buy_signal = 1
                current_position = 1

            # 賣出條件：RSI高於超買線且當前有倉位
            elif rsi_value > self.overbought and current_position == 1:
                sell_signal = 1
                current_position = 0

            buy_signals.append(buy_signal)
            sell_signals.append(sell_signal)
            positions.append(current_position)

        signals["buy_signal"] = buy_signals
        signals["sell_signal"] = sell_signals
        signals["position"] = positions

        # 生成主要訊號：買入=1, 賣出=-1, 觀望=0
        signals["signal"] = signals["buy_signal"] - signals["sell_signal"]

        logger.info(
            "生成RSI策略訊號完成，參數: rsi_window=%d, overbought=%.1f, oversold=%.1f",
            self.rsi_window,
            self.overbought,
            self.oversold,
        )

        return signals

    def optimize_parameters(
        self,
        data: pd.DataFrame,
        target: Optional[pd.Series] = None,
        param_grid: Optional[Dict[str, List[Any]]] = None,
        metric: str = "sharpe_ratio",
    ) -> Dict[str, Any]:
        """
        優化RSI策略參數。

        Args:
            data: 價格資料
            target: 目標變數（此策略中不使用）
            param_grid: 參數網格，如果為None則使用預設網格
            metric: 優化指標

        Returns:
            最佳參數字典

        Raises:
            ParameterError: 當參數網格不正確時
            DataValidationError: 當輸入資料不正確時
        """
        if param_grid is None:
            param_grid = self._get_default_param_grid()

        # 驗證參數網格
        required_params = ["rsi_window", "overbought", "oversold"]
        missing_params = [p for p in required_params if p not in param_grid]
        if missing_params:
            raise ParameterError(f"參數網格缺少必要參數: {missing_params}")

        best_score = -np.inf if metric != "max_drawdown" else 0
        best_params = {}

        logger.info("開始RSI策略參數優化，使用指標: %s", metric)

        total_combinations = (
            len(param_grid["rsi_window"])
            * len(param_grid["overbought"])
            * len(param_grid["oversold"])
        )
        current_combination = 0

        for rsi_window in param_grid["rsi_window"]:
            for overbought in param_grid["overbought"]:
                for oversold in param_grid["oversold"]:
                    current_combination += 1

                    # 跳過無效的參數組合
                    if oversold >= overbought:
                        continue

                    try:
                        # 創建臨時策略實例
                        temp_strategy = RSIStrategy(
                            rsi_window=rsi_window,
                            overbought=overbought,
                            oversold=oversold,
                        )

                        # 評估策略
                        metrics = temp_strategy.evaluate(data)
                        score = metrics.get(metric, -np.inf)

                        # 更新最佳參數
                        is_better = (
                            score > best_score
                            if metric != "max_drawdown"
                            else score > best_score
                        )

                        if is_better:
                            best_score = score
                            best_params = {
                                "rsi_window": rsi_window,
                                "overbought": overbought,
                                "oversold": oversold,
                                "best_score": best_score,
                                "optimization_metric": metric,
                            }

                        if current_combination % 20 == 0:
                            logger.info(
                                "參數優化進度: %d/%d (%.1f%%)",
                                current_combination,
                                total_combinations,
                                100 * current_combination / total_combinations,
                            )

                    except Exception as e:
                        logger.warning(
                            "參數組合 (window=%d, overbought=%.1f, oversold=%.1f) 評估失敗: %s",
                            rsi_window,
                            overbought,
                            oversold,
                            str(e),
                        )
                        continue

        if not best_params:
            raise ParameterError("未找到有效的參數組合")

        logger.info(
            "RSI策略參數優化完成，最佳參數: window=%d, overbought=%.1f, oversold=%.1f, %s=%.4f",
            best_params["rsi_window"],
            best_params["overbought"],
            best_params["oversold"],
            metric,
            best_params["best_score"],
        )

        return best_params

    def _get_default_param_grid(self) -> Dict[str, List[Any]]:
        """
        獲取預設參數網格。

        Returns:
            預設參數網格
        """
        return {
            "rsi_window": [10, 14, 20, 25],
            "overbought": [70.0, 75.0, 80.0],
            "oversold": [20.0, 25.0, 30.0],
        }

    def get_signal_summary(self, signals: pd.DataFrame) -> Dict[str, Any]:
        """
        獲取RSI策略訊號統計摘要。

        Args:
            signals: 訊號資料

        Returns:
            訊號統計摘要
        """
        total_periods = len(signals)
        buy_signals = signals["buy_signal"].sum()
        sell_signals = signals["sell_signal"].sum()

        # RSI統計
        rsi_values = signals["rsi"].dropna()
        overbought_periods = (rsi_values > self.overbought).sum()
        oversold_periods = (rsi_values < self.oversold).sum()

        return {
            "total_signals": int(buy_signals + sell_signals),
            "buy_signals": int(buy_signals),
            "sell_signals": int(sell_signals),
            "overbought_periods": int(overbought_periods),
            "oversold_periods": int(oversold_periods),
            "avg_rsi": float(rsi_values.mean()) if not rsi_values.empty else 0.0,
            "rsi_volatility": float(rsi_values.std()) if not rsi_values.empty else 0.0,
            "signal_frequency": (
                float(buy_signals / total_periods) if total_periods > 0 else 0.0
            ),
        }
