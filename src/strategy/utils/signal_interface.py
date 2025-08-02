# -*- coding: utf-8 -*-
"""
統一訊號生成介面模組

此模組提供統一的訊號生成介面，整合各種訊號生成器。

主要功能：
- 統一的訊號生成介面
- 多股票支援
- 參數驗證
"""

import logging
from typing import Any
import pandas as pd

from .signal_generators import (
    trade_point_decision,
    continuous_trading_signal,
    triple_barrier,
    fixed_time_horizon,
)

# 設定日誌
logger = logging.getLogger(__name__)

# 多語系訊息
LOG_MSGS = {
    "zh_tw": {
        "no_close": "價格資料框架必須包含 '收盤價' 欄位",
        "no_rsi": "特徵資料框架必須包含 RSI 特徵",
        "no_model": "必須先訓練模型",
        "unknown_model": "不支援的模型類型: {model_type}",
        "unknown_strategy": "不支援的策略名稱: {strategy_name}",
        "index_structure_error": "價格資料 index 結構需包含 'stock_id' 層級，請確認資料格式。",
        "target_type_error": "target_df 必須為 pandas.Series 型別，請確認資料格式。",
    },
}
LOG_LANG = "zh_tw"


def generate_signals(
    features: pd.DataFrame,
    strategy_name: str = "moving_average_cross",
    **strategy_params: Any
) -> pd.DataFrame:
    """
    生成交易訊號的統一介面函數。

    此函數提供了一個統一的介面來生成各種類型的交易訊號。

    Args:
        features: 特徵資料框架
        strategy_name: 策略名稱，支援：
            - "trade_point_decision": 交易點決策
            - "continuous_trading_signal": 連續交易訊號
            - "triple_barrier": 三重障礙法
            - "fixed_time_horizon": 固定時間範圍
        **strategy_params: 策略參數

    Returns:
        包含交易訊號的資料框架

    Raises:
        ValueError: 當策略名稱不支援或資料格式不正確時

    Example:
        >>> signals = generate_signals(
        ...     price_data,
        ...     strategy_name="trade_point_decision",
        ...     threshold=100
        ... )
    """
    # 導入資料載入函數
    try:
        from src.core.data_ingest import load_data

        data_dict = load_data()
        price_df = data_dict["price"]
    except ImportError:
        logger.warning("無法載入資料，使用輸入的features作為價格資料")
        price_df = features

    # 多股票 index 結構檢查
    multi_stock_strategies = [
        "trade_point_decision",
        "continuous_trading_signal",
        "triple_barrier",
        "fixed_time_horizon",
    ]

    if strategy_name in multi_stock_strategies:
        if not (
            isinstance(price_df.index, pd.MultiIndex)
            and "stock_id" in price_df.index.names
        ):
            logger.error(LOG_MSGS[LOG_LANG]["index_structure_error"])
            raise ValueError(LOG_MSGS[LOG_LANG]["index_structure_error"])

    # 生成訊號
    if strategy_name == "trade_point_decision":
        return _generate_trade_point_signals(price_df, **strategy_params)
    elif strategy_name == "continuous_trading_signal":
        return _generate_continuous_signals(price_df, **strategy_params)
    elif strategy_name == "triple_barrier":
        return _generate_triple_barrier_signals(price_df, **strategy_params)
    elif strategy_name == "fixed_time_horizon":
        return _generate_fixed_horizon_signals(price_df, **strategy_params)
    else:
        logger.error(
            LOG_MSGS[LOG_LANG]["unknown_strategy"].format(strategy_name=strategy_name)
        )
        raise ValueError(
            LOG_MSGS[LOG_LANG]["unknown_strategy"].format(strategy_name=strategy_name)
        )


def _generate_trade_point_signals(price_df: pd.DataFrame, **params) -> pd.DataFrame:
    """生成交易點決策訊號"""
    threshold = params.get("threshold", 200)
    signals = pd.DataFrame()

    for stock_id in price_df.index.get_level_values("stock_id").unique():
        stock_price = price_df.xs(stock_id, level="stock_id")["收盤價"].astype(float)
        stock_signals = trade_point_decision(stock_price, threshold)
        stock_signals = pd.DataFrame(stock_signals)
        stock_signals["stock_id"] = stock_id
        stock_signals.set_index("stock_id", append=True, inplace=True)
        stock_signals = stock_signals.reorder_levels(
            ["stock_id", stock_signals.index.names[0]]
        )
        signals = pd.concat([signals, stock_signals])
    return signals


def _generate_continuous_signals(price_df: pd.DataFrame, **params) -> pd.DataFrame:
    """生成連續交易訊號"""
    window = params.get("window", 20)
    signals = pd.DataFrame()

    for stock_id in price_df.index.get_level_values("stock_id").unique():
        stock_price = price_df.xs(stock_id, level="stock_id")["收盤價"].astype(float)
        stock_signals = continuous_trading_signal(stock_price, window)
        stock_signals = pd.DataFrame(stock_signals)
        stock_signals["stock_id"] = stock_id
        stock_signals.set_index("stock_id", append=True, inplace=True)
        stock_signals = stock_signals.reorder_levels(
            ["stock_id", stock_signals.index.names[0]]
        )
        signals = pd.concat([signals, stock_signals])
    return signals


def _generate_triple_barrier_signals(price_df: pd.DataFrame, **params) -> pd.DataFrame:
    """生成三重障礙訊號"""
    upper_barrier = params.get("upper_barrier", 1.1)
    lower_barrier = params.get("lower_barrier", 0.9)
    max_period = params.get("max_period", 20)
    signals = pd.DataFrame()

    for stock_id in price_df.index.get_level_values("stock_id").unique():
        stock_price = price_df.xs(stock_id, level="stock_id")["收盤價"].astype(float)
        stock_signals = triple_barrier(
            stock_price, upper_barrier, lower_barrier, max_period
        )
        stock_signals["stock_id"] = stock_id
        stock_signals.set_index("stock_id", append=True, inplace=True)
        stock_signals = stock_signals.reorder_levels(
            ["stock_id", stock_signals.index.names[0]]
        )
        signals = pd.concat([signals, stock_signals])
    return signals


def _generate_fixed_horizon_signals(price_df: pd.DataFrame, **params) -> pd.DataFrame:
    """生成固定時間範圍訊號"""
    window = params.get("window", 20)
    signals = pd.DataFrame()

    for stock_id in price_df.index.get_level_values("stock_id").unique():
        stock_price = price_df.xs(stock_id, level="stock_id")["收盤價"].astype(float)
        stock_signals = fixed_time_horizon(stock_price, window)
        stock_signals = pd.DataFrame(stock_signals)
        stock_signals["stock_id"] = stock_id
        stock_signals.set_index("stock_id", append=True, inplace=True)
        stock_signals = stock_signals.reorder_levels(
            ["stock_id", stock_signals.index.names[0]]
        )
        signals = pd.concat([signals, stock_signals])
    return signals
