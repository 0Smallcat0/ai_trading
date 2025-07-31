"""
交易模式處理器模組

此模組負責處理不同的交易模式執行邏輯，整合各個模式處理器：
- 回測模式處理
- 模擬交易模式處理
- 實盤交易模式處理

主要功能：
- 提供統一的模式處理介面
- 整合各個專門的處理器模組
- 向後相容性支援

Example:
    >>> from src.core.mode_handlers import run_backtest_mode
    >>> config = {"mode": "backtest", ...}
    >>> results, report = run_backtest_mode(config)
"""

import logging
from typing import Dict, Any, Tuple

from .backtest_handler import run_backtest_mode as _run_backtest_mode
from .live_trading_handler import run_paper_mode as _run_paper_mode, run_live_mode as _run_live_mode

logger = logging.getLogger(__name__)


def run_backtest_mode(config: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """執行回測模式.

    Args:
        config: 系統配置字典，包含回測所需的所有參數

    Returns:
        Tuple[Dict[str, Any], Dict[str, Any]]: 回測結果和報告

    Raises:
        ValueError: 當配置參數不正確時
        RuntimeError: 當回測執行失敗時

    Example:
        >>> config = {"start_date": "2023-01-01", "end_date": "2023-12-31", ...}
        >>> results, report = run_backtest_mode(config)
        >>> print(f"總收益率: {report['returns']['total_return']:.2%}")
    """
    return _run_backtest_mode(config)


def run_paper_mode(config: Dict[str, Any]) -> None:
    """執行模擬交易模式.

    Args:
        config: 系統配置字典

    Raises:
        ValueError: 當配置參數不正確時
        RuntimeError: 當模擬交易執行失敗時

    Example:
        >>> config = {"mode": "paper", "execution": {"interval": 60}, ...}
        >>> run_paper_mode(config)
    """
    _run_paper_mode(config)


def run_live_mode(config: Dict[str, Any]) -> None:
    """執行實盤交易模式.

    Args:
        config: 系統配置字典

    Raises:
        ValueError: 當配置參數不正確時
        RuntimeError: 當實盤交易執行失敗時

    Warning:
        實盤交易涉及真實資金，請確保充分測試後再使用

    Example:
        >>> config = {"mode": "live", "execution": {"broker": "ib"}, ...}
        >>> run_live_mode(config)
    """
    _run_live_mode(config)


# 向後相容性函數
__all__ = [
    'run_backtest_mode',
    'run_paper_mode',
    'run_live_mode'
]
