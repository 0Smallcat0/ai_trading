# -*- coding: utf-8 -*-
"""
移動平均線交叉策略模組

此模組實現基於移動平均線交叉的交易策略。

主要功能：
- 短期和長期移動平均線計算
- 交叉訊號生成
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


class MovingAverageCrossStrategy(Strategy):
    """
    移動平均線交叉策略。

    當短期移動平均線向上穿越長期移動平均線時產生買入訊號，
    當短期移動平均線向下穿越長期移動平均線時產生賣出訊號。

    Attributes:
        short_window (int): 短期移動平均線窗口大小
        long_window (int): 長期移動平均線窗口大小

    Example:
        >>> strategy = MovingAverageCrossStrategy(short_window=5, long_window=20)
        >>> signals = strategy.generate_signals(price_data)
        >>> metrics = strategy.evaluate(price_data, signals)
    """

    def __init__(
        self, short_window: int = 5, long_window: int = 20, **kwargs: Any
    ) -> None:
        """
        初始化移動平均線交叉策略。

        Args:
            short_window: 短期移動平均線窗口大小，必須大於0且小於long_window
            long_window: 長期移動平均線窗口大小，必須大於short_window
            **kwargs: 其他參數

        Raises:
            ParameterError: 當參數不符合要求時
        """
        super().__init__(
            name="MovingAverageCross",
            short_window=short_window,
            long_window=long_window,
            **kwargs,
        )
        self.short_window = short_window
        self.long_window = long_window

    def _validate_parameters(self) -> None:
        """
        驗證策略參數。

        Raises:
            ParameterError: 當參數不符合要求時
        """
        if not isinstance(self.short_window, int) or self.short_window <= 0:
            raise ParameterError(
                f"short_window 必須是正整數，得到: {self.short_window}"
            )

        if not isinstance(self.long_window, int) or self.long_window <= 0:
            raise ParameterError(f"long_window 必須是正整數，得到: {self.long_window}")

        if self.short_window >= self.long_window:
            raise ParameterError(
                f"short_window ({self.short_window}) 必須小於 long_window ({self.long_window})"
            )

    def generate_signals(self, price_data: pd.DataFrame) -> pd.DataFrame:
        """
        生成移動平均線交叉訊號。

        Args:
            price_data: 價格資料，必須包含 '收盤價' 欄位

        Returns:
            包含交易訊號的資料框架，包含以下欄位：
            - signal: 主要訊號 (1=持有, 0=空倉)
            - position_change: 倉位變化 (1=買入, -1=賣出, 0=無變化)
            - buy_signal: 買入訊號 (1=買入, 0=無動作)
            - sell_signal: 賣出訊號 (1=賣出, 0=無動作)
            - short_ma: 短期移動平均線
            - long_ma: 長期移動平均線

        Raises:
            DataValidationError: 當輸入資料格式不正確時
        """
        # 驗證輸入資料
        self._validate_price_data(price_data)

        # 計算移動平均線
        price_series = price_data["收盤價"].astype(float)
        short_ma = price_series.rolling(window=self.short_window).mean()
        long_ma = price_series.rolling(window=self.long_window).mean()

        # 生成訊號
        signals = pd.DataFrame(index=price_data.index)

        # 當短期移動平均線高於長期移動平均線時，持有倉位 (1)
        signals["signal"] = np.where(short_ma > long_ma, 1.0, 0.0)

        # 計算倉位變化
        signals["position_change"] = signals["signal"].diff()

        # 買入訊號：從0變為1
        signals["buy_signal"] = np.where(signals["position_change"] > 0, 1, 0)

        # 賣出訊號：從1變為0
        signals["sell_signal"] = np.where(signals["position_change"] < 0, 1, 0)

        # 保存移動平均線數據以供分析
        signals["short_ma"] = short_ma
        signals["long_ma"] = long_ma

        # 填充NaN值
        signals = signals.fillna(0)

        logger.info(
            "生成移動平均線交叉訊號完成，參數: short_window=%d, long_window=%d",
            self.short_window,
            self.long_window,
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
        優化移動平均線交叉策略參數。

        Args:
            data: 價格資料
            target: 目標變數（此策略中不使用）
            param_grid: 參數網格，如果為None則使用預設網格
            metric: 優化指標，支援 'sharpe_ratio', 'total_return', 'max_drawdown'

        Returns:
            最佳參數字典，包含：
            - short_window: 最佳短期窗口
            - long_window: 最佳長期窗口
            - best_score: 最佳評分
            - optimization_metric: 使用的優化指標

        Raises:
            ParameterError: 當參數網格不正確時
            DataValidationError: 當輸入資料不正確時
        """
        if param_grid is None:
            param_grid = self._get_default_param_grid()

        # 驗證參數網格
        required_params = ["short_window", "long_window"]
        missing_params = [p for p in required_params if p not in param_grid]
        if missing_params:
            raise ParameterError(f"參數網格缺少必要參數: {missing_params}")

        best_score = -np.inf if metric != "max_drawdown" else 0
        best_params = {}

        logger.info("開始參數優化，使用指標: %s", metric)

        total_combinations = len(param_grid["short_window"]) * len(
            param_grid["long_window"]
        )
        current_combination = 0

        for short_window in param_grid["short_window"]:
            for long_window in param_grid["long_window"]:
                current_combination += 1

                # 跳過無效的參數組合
                if short_window >= long_window:
                    continue

                try:
                    # 創建臨時策略實例
                    temp_strategy = MovingAverageCrossStrategy(
                        short_window=short_window, long_window=long_window
                    )

                    # 評估策略
                    metrics = temp_strategy.evaluate(data)
                    score = metrics.get(metric, -np.inf)

                    # 更新最佳參數
                    is_better = (
                        score > best_score
                        if metric != "max_drawdown"
                        else score > best_score  # max_drawdown是負值，越大越好
                    )

                    if is_better:
                        best_score = score
                        best_params = {
                            "short_window": short_window,
                            "long_window": long_window,
                            "best_score": best_score,
                            "optimization_metric": metric,
                        }

                    if current_combination % 10 == 0:
                        logger.info(
                            "參數優化進度: %d/%d (%.1f%%)",
                            current_combination,
                            total_combinations,
                            100 * current_combination / total_combinations,
                        )

                except Exception as e:
                    logger.warning(
                        "參數組合 (short=%d, long=%d) 評估失敗: %s",
                        short_window,
                        long_window,
                        str(e),
                    )
                    continue

        if not best_params:
            raise ParameterError("未找到有效的參數組合")

        logger.info(
            "參數優化完成，最佳參數: short_window=%d, long_window=%d, %s=%.4f",
            best_params["short_window"],
            best_params["long_window"],
            metric,
            best_params["best_score"],
        )

        return best_params

    def _get_default_param_grid(self) -> Dict[str, List[int]]:
        """
        獲取預設參數網格。

        Returns:
            預設參數網格，包含常用的移動平均線窗口組合
        """
        return {"short_window": [5, 10, 15, 20], "long_window": [20, 30, 50, 100, 200]}

    def get_signal_summary(self, signals: pd.DataFrame) -> Dict[str, Any]:
        """
        獲取訊號統計摘要。

        Args:
            signals: 訊號資料

        Returns:
            訊號統計摘要，包含：
            - total_signals: 總訊號數
            - buy_signals: 買入訊號數
            - sell_signals: 賣出訊號數
            - holding_periods: 平均持有期間
            - signal_frequency: 訊號頻率
        """
        total_periods = len(signals)
        buy_signals = signals["buy_signal"].sum()
        sell_signals = signals["sell_signal"].sum()
        holding_periods = signals["signal"].sum()

        return {
            "total_signals": int(buy_signals + sell_signals),
            "buy_signals": int(buy_signals),
            "sell_signals": int(sell_signals),
            "holding_periods": int(holding_periods),
            "signal_frequency": (
                float(buy_signals / total_periods) if total_periods > 0 else 0.0
            ),
            "average_holding_period": (
                float(holding_periods / buy_signals) if buy_signals > 0 else 0.0
            ),
        }
