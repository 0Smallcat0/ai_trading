"""
回測驗證模組

此模組包含回測配置和數據的驗證功能。
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple
import pandas as pd

from .backtest_config import BacktestConfig

logger = logging.getLogger(__name__)


def validate_backtest_config(config: BacktestConfig) -> Tuple[bool, str]:
    """
    驗證回測配置

    Args:
        config: 回測配置對象

    Returns:
        Tuple[bool, str]: (是否有效, 錯誤訊息)
    """
    try:
        # 基本配置驗證
        is_valid, error_msg = config.validate()
        if not is_valid:
            return False, error_msg

        # 策略ID格式驗證
        if not _validate_strategy_id(config.strategy_id):
            return False, "策略ID格式無效，只能包含字母、數字和下劃線"

        # 股票代碼驗證
        is_valid, error_msg = _validate_symbols(config.symbols)
        if not is_valid:
            return False, error_msg

        # 日期範圍驗證
        is_valid, error_msg = _validate_date_range(config.start_date, config.end_date)
        if not is_valid:
            return False, error_msg

        # 交易成本參數驗證
        is_valid, error_msg = _validate_trading_costs(
            config.commission, config.slippage, config.tax
        )
        if not is_valid:
            return False, error_msg

        # 策略參數驗證
        if config.strategy_params:
            is_valid, error_msg = _validate_strategy_params(config.strategy_params)
            if not is_valid:
                return False, error_msg

        return True, ""

    except Exception as e:
        logger.error("驗證回測配置時發生錯誤: %s", e)
        return False, f"配置驗證失敗: {str(e)}"


def validate_market_data(
    data: pd.DataFrame, symbols: List[str], start_date: datetime, end_date: datetime
) -> Tuple[bool, str]:
    """
    驗證市場數據

    Args:
        data: 市場數據DataFrame
        symbols: 股票代碼列表
        start_date: 開始日期
        end_date: 結束日期

    Returns:
        Tuple[bool, str]: (是否有效, 錯誤訊息)
    """
    try:
        if data.empty:
            return False, "市場數據為空"

        # 檢查必要欄位
        required_columns = ["open", "high", "low", "close", "volume"]
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            return False, f"缺少必要欄位: {missing_columns}"

        # 檢查數據類型
        numeric_columns = ["open", "high", "low", "close", "volume"]
        for col in numeric_columns:
            if not pd.api.types.is_numeric_dtype(data[col]):
                return False, f"欄位 {col} 必須為數值類型"

        # 檢查數據完整性
        if data.isnull().any().any():
            null_counts = data.isnull().sum()
            null_columns = null_counts[null_counts > 0].index.tolist()
            return False, f"數據包含空值，欄位: {null_columns}"

        # 檢查價格邏輯
        invalid_prices = (
            (data["high"] < data["low"])
            | (data["high"] < data["open"])
            | (data["high"] < data["close"])
            | (data["low"] > data["open"])
            | (data["low"] > data["close"])
            | (data["open"] <= 0)
            | (data["high"] <= 0)
            | (data["low"] <= 0)
            | (data["close"] <= 0)
        )

        if invalid_prices.any():
            invalid_count = invalid_prices.sum()
            return False, f"發現 {invalid_count} 筆無效價格數據"

        # 檢查成交量
        if (data["volume"] < 0).any():
            return False, "成交量不能為負數"

        # 檢查日期範圍
        if hasattr(data.index, "min") and hasattr(data.index, "max"):
            data_start = data.index.min()
            data_end = data.index.max()

            if data_start > start_date:
                return (
                    False,
                    f"數據開始日期 {data_start} 晚於要求的開始日期 {start_date}",
                )

            if data_end < end_date:
                return False, f"數據結束日期 {data_end} 早於要求的結束日期 {end_date}"

        return True, ""

    except Exception as e:
        logger.error("驗證市場數據時發生錯誤: %s", e)
        return False, f"數據驗證失敗: {str(e)}"


def validate_signals(signals: pd.DataFrame) -> Tuple[bool, str]:
    """
    驗證交易信號

    Args:
        signals: 交易信號DataFrame

    Returns:
        Tuple[bool, str]: (是否有效, 錯誤訊息)
    """
    try:
        if signals.empty:
            return False, "交易信號為空"

        # 檢查必要欄位
        required_columns = ["signal"]
        missing_columns = [
            col for col in required_columns if col not in signals.columns
        ]
        if missing_columns:
            return False, f"缺少必要欄位: {missing_columns}"

        # 檢查信號值
        valid_signals = [-1, 0, 1]  # -1: 賣出, 0: 持有, 1: 買入
        invalid_signals = ~signals["signal"].isin(valid_signals)

        if invalid_signals.any():
            invalid_count = invalid_signals.sum()
            return (
                False,
                f"發現 {invalid_count} 筆無效信號值，有效值為: {valid_signals}",
            )

        return True, ""

    except Exception as e:
        logger.error("驗證交易信號時發生錯誤: %s", e)
        return False, f"信號驗證失敗: {str(e)}"


def _validate_strategy_id(strategy_id: str) -> bool:
    """驗證策略ID格式"""
    if not strategy_id:
        return False

    # 只允許字母、數字和下劃線
    import re

    pattern = r"^[a-zA-Z0-9_]+$"
    return bool(re.match(pattern, strategy_id))


def _validate_symbols(symbols: List[str]) -> Tuple[bool, str]:
    """驗證股票代碼"""
    if not symbols:
        return False, "股票代碼列表不能為空"

    for symbol in symbols:
        if not symbol or not isinstance(symbol, str):
            return False, f"無效的股票代碼: {symbol}"

        # 基本格式檢查
        if len(symbol.strip()) < 4:
            return False, f"股票代碼長度不足: {symbol}"

        # 檢查是否包含非法字符
        import re

        if not re.match(r"^[A-Za-z0-9.]+$", symbol):
            return False, f"股票代碼包含非法字符: {symbol}"

    return True, ""


def _validate_date_range(start_date: datetime, end_date: datetime) -> Tuple[bool, str]:
    """驗證日期範圍"""
    if not start_date or not end_date:
        return False, "開始日期和結束日期不能為空"

    if start_date >= end_date:
        return False, "開始日期必須早於結束日期"

    # 檢查日期範圍是否合理
    date_diff = end_date - start_date

    # 最少需要1天
    if date_diff.days < 1:
        return False, "日期範圍至少需要1天"

    # 最多不超過10年
    max_days = 365 * 10
    if date_diff.days > max_days:
        return False, f"日期範圍過長，最多支援{max_days}天"

    # 檢查是否為未來日期
    now = datetime.now()
    if start_date > now:
        return False, "開始日期不能為未來日期"

    if end_date > now:
        return False, "結束日期不能為未來日期"

    return True, ""


def _validate_trading_costs(
    commission: float, slippage: float, tax: float
) -> Tuple[bool, str]:
    """驗證交易成本參數"""
    if commission < 0:
        return False, "手續費率不能為負數"

    if commission > 0.1:  # 10%
        return False, "手續費率過高，不能超過10%"

    if slippage < 0:
        return False, "滑價不能為負數"

    if slippage > 0.1:  # 10%
        return False, "滑價過高，不能超過10%"

    if tax < 0:
        return False, "稅率不能為負數"

    if tax > 0.1:  # 10%
        return False, "稅率過高，不能超過10%"

    return True, ""


def _validate_strategy_params(params: Dict[str, Any]) -> Tuple[bool, str]:
    """驗證策略參數"""
    if not isinstance(params, dict):
        return False, "策略參數必須為字典格式"

    # 檢查參數值類型
    for key, value in params.items():
        if not isinstance(key, str):
            return False, f"參數名稱必須為字符串: {key}"

        # 檢查值是否為支援的類型
        supported_types = (int, float, str, bool, list, dict)
        if not isinstance(value, supported_types):
            return False, f"不支援的參數類型: {key} = {type(value)}"

    return True, ""
