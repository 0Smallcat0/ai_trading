# -*- coding: utf-8 -*-
"""策略基礎模組

此模組定義了所有交易策略的基礎類別和共用功能。

主要功能：
- 定義策略基類 Strategy
- 提供策略評估的通用方法
- 定義策略異常類別
- 提供策略參數驗證功能
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import pandas as pd

from .metrics import (
    calculate_returns,
    calculate_total_return,
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    calculate_win_rate,
    calculate_volatility
)

# 設定日誌
logger = logging.getLogger(__name__)


class StrategyError(Exception):
    """策略相關錯誤基類"""


class ParameterError(StrategyError):
    """參數錯誤"""


class ModelNotTrainedError(StrategyError):
    """模型未訓練錯誤"""


class DataValidationError(StrategyError):
    """資料驗證錯誤"""


class Strategy(ABC):
    """策略基類，所有具體策略都應該繼承此類。

    此類定義了策略的基本介面和通用功能，包括：
    - 訊號生成
    - 參數優化
    - 策略評估
    - 參數驗證

    Attributes:
        name (str): 策略名稱
        parameters (Dict[str, Any]): 策略參數
    """

    def __init__(self, name: str = "BaseStrategy", **parameters: Any) -> None:
        """初始化策略。

        Args:
            name: 策略名稱
            **parameters: 策略參數

        Raises:
            ParameterError: 當參數驗證失敗時
        """
        self.name = name
        self.parameters = parameters
        self._validate_parameters()

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易訊號。

        Args:
            data: 輸入資料，通常包含價格或特徵資料

        Returns:
            包含交易訊號的資料框架，至少包含以下欄位：
            - signal: 主要訊號 (1=買入, -1=賣出, 0=觀望)
            - buy_signal: 買入訊號 (1=買入, 0=無動作)
            - sell_signal: 賣出訊號 (1=賣出, 0=無動作)

        Raises:
            DataValidationError: 當輸入資料格式不正確時
            ParameterError: 當策略參數不正確時
        """

    def optimize_parameters(
        self,
        data: pd.DataFrame,
        target: Optional[pd.Series] = None,
        param_grid: Optional[Dict[str, List[Any]]] = None,
        metric: str = "sharpe_ratio"
    ) -> Dict[str, Any]:
        """優化策略參數。

        Args:
            data: 訓練資料
            target: 目標變數（可選）
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

        # 這裡應該實現參數優化邏輯
        # 子類可以覆寫此方法以實現特定的優化邏輯
        logger.warning(
            "使用預設參數優化實現，建議子類覆寫此方法。參數: data=%s, target=%s, metric=%s",
            type(data).__name__,
            type(target).__name__ if target is not None else "None",
            metric
        )

        return {}

    def evaluate(
        self,
        data: pd.DataFrame,
        signals: Optional[pd.DataFrame] = None
    ) -> Dict[str, float]:
        """評估策略表現。

        Args:
            data: 價格資料
            signals: 訊號資料，如果為None則自動生成

        Returns:
            評估結果字典，包含：
            - total_return: 總收益率
            - sharpe_ratio: 夏普比率
            - max_drawdown: 最大回撤
            - win_rate: 勝率
            - volatility: 波動率

        Raises:
            DataValidationError: 當輸入資料不正確時
        """
        if signals is None:
            signals = self.generate_signals(data)

        # 驗證資料
        self._validate_price_data(data)
        self._validate_signals_data(signals)

        # 計算收益率
        returns = calculate_returns(signals, data)

        # 計算各項指標
        metrics = {
            "total_return": calculate_total_return(returns),
            "sharpe_ratio": calculate_sharpe_ratio(returns),
            "max_drawdown": calculate_max_drawdown(returns),
            "win_rate": calculate_win_rate(returns),
            "volatility": calculate_volatility(returns)
        }

        return metrics

    def _validate_parameters(self) -> None:
        """驗證策略參數。

        子類應該覆寫此方法以實現特定的參數驗證邏輯。

        Raises:
            ParameterError: 當參數不正確時
        """

    def _get_default_param_grid(self) -> Dict[str, List[Any]]:
        """獲取預設參數網格。

        子類應該覆寫此方法以提供特定的參數網格。

        Returns:
            參數網格字典
        """
        return {}

    def _validate_price_data(self, data: pd.DataFrame) -> None:
        """驗證價格資料格式。

        Args:
            data: 價格資料

        Raises:
            DataValidationError: 當資料格式不正確時
        """
        required_columns = ["收盤價"]
        missing_columns = [col for col in required_columns if col not in data.columns]

        if missing_columns:
            raise DataValidationError(
                f"價格資料缺少必要欄位: {missing_columns}"
            )

        if data.empty:
            raise DataValidationError("價格資料不能為空")

    def _validate_signals_data(self, signals: pd.DataFrame) -> None:
        """驗證訊號資料格式。

        Args:
            signals: 訊號資料

        Raises:
            DataValidationError: 當資料格式不正確時
        """
        required_columns = ["signal"]
        missing_columns = [
            col for col in required_columns if col not in signals.columns
        ]

        if missing_columns:
            raise DataValidationError(
                f"訊號資料缺少必要欄位: {missing_columns}"
            )

    def __str__(self) -> str:
        """字串表示"""
        return f"{self.__class__.__name__}(name='{self.name}')"

    def __repr__(self) -> str:
        """詳細字串表示"""
        return (
            f"{self.__class__.__name__}(name='{self.name}', "
            f"parameters={self.parameters})"
        )
