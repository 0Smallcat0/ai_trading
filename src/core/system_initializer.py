"""
系統初始化模組

此模組負責處理系統的初始化配置，包括：
- 配置字典構建
- 日誌系統設定
- 環境變數處理

主要功能：
- 將命令行參數轉換為系統配置
- 設定日誌級別和格式
- 處理環境變數和預設值

Example:
    >>> from src.core.system_initializer import init_system, build_config
    >>> args = parse_args()
    >>> config = init_system(args)
    >>> print(config['mode'])
"""

import argparse
import logging
from typing import Dict, Any

from .config_validator import (
    validate_date_format, 
    parse_json_params, 
    validate_config
)

logger = logging.getLogger(__name__)


def setup_logging(log_level: str) -> None:
    """設定日誌系統.

    Args:
        log_level: 日誌級別字符串

    Example:
        >>> setup_logging("INFO")
        >>> logger.info("日誌系統已設定")
    """
    # 設定日誌級別
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.getLogger().setLevel(numeric_level)
    
    logger.info("日誌級別設定為: %s", log_level)


def build_strategy_config(args: argparse.Namespace) -> Dict[str, Any]:
    """構建策略配置.

    Args:
        args: 命令行參數物件

    Returns:
        Dict[str, Any]: 策略配置字典

    Raises:
        ValueError: 當策略參數解析失敗時

    Example:
        >>> args = argparse.Namespace(strategy="ma_cross", strategy_params="{}")
        >>> config = build_strategy_config(args)
        >>> print(config['name'])
        'ma_cross'
    """
    try:
        strategy_params = parse_json_params(args.strategy_params)
    except ValueError as e:
        raise ValueError(f"策略參數解析失敗: {e}") from e

    return {
        "name": args.strategy,
        "params": strategy_params,
    }


def build_portfolio_config(args: argparse.Namespace) -> Dict[str, Any]:
    """構建投資組合配置.

    Args:
        args: 命令行參數物件

    Returns:
        Dict[str, Any]: 投資組合配置字典

    Raises:
        ValueError: 當投資組合參數解析失敗時

    Example:
        >>> args = argparse.Namespace(portfolio="equal_weight", portfolio_params="{}")
        >>> config = build_portfolio_config(args)
        >>> print(config['name'])
        'equal_weight'
    """
    try:
        portfolio_params = parse_json_params(args.portfolio_params)
    except ValueError as e:
        raise ValueError(f"投資組合參數解析失敗: {e}") from e

    return {
        "name": args.portfolio,
        "params": portfolio_params,
    }


def build_backtest_config(args: argparse.Namespace) -> Dict[str, Any]:
    """構建回測配置.

    Args:
        args: 命令行參數物件

    Returns:
        Dict[str, Any]: 回測配置字典

    Example:
        >>> args = argparse.Namespace(
        ...     initial_capital=1000000.0,
        ...     transaction_cost=0.001425,
        ...     slippage=0.0005,
        ...     tax=0.003
        ... )
        >>> config = build_backtest_config(args)
        >>> print(config['initial_capital'])
        1000000.0
    """
    return {
        "initial_capital": args.initial_capital,
        "transaction_cost": args.transaction_cost,
        "slippage": args.slippage,
        "tax": args.tax,
    }


def build_risk_control_config(args: argparse.Namespace) -> Dict[str, Any]:
    """構建風險控制配置.

    Args:
        args: 命令行參數物件

    Returns:
        Dict[str, Any]: 風險控制配置字典

    Example:
        >>> args = argparse.Namespace(
        ...     max_position_size=0.1,
        ...     max_portfolio_risk=0.02,
        ...     stop_loss=0.05,
        ...     stop_profit=0.15
        ... )
        >>> config = build_risk_control_config(args)
        >>> print(config['max_position_size'])
        0.1
    """
    return {
        "max_position_size": args.max_position_size,
        "max_portfolio_risk": args.max_portfolio_risk,
        "stop_loss": args.stop_loss,
        "stop_profit": args.stop_profit,
    }


def build_execution_config(args: argparse.Namespace) -> Dict[str, Any]:
    """構建執行配置.

    Args:
        args: 命令行參數物件

    Returns:
        Dict[str, Any]: 執行配置字典

    Example:
        >>> args = argparse.Namespace(interval=60, broker="simulator")
        >>> config = build_execution_config(args)
        >>> print(config['broker'])
        'simulator'
    """
    return {
        "interval": args.interval,
        "broker": args.broker,
    }


def build_logging_config(args: argparse.Namespace) -> Dict[str, Any]:
    """構建日誌配置.

    Args:
        args: 命令行參數物件

    Returns:
        Dict[str, Any]: 日誌配置字典

    Example:
        >>> args = argparse.Namespace(log_level="INFO")
        >>> config = build_logging_config(args)
        >>> print(config['level'])
        'INFO'
    """
    return {
        "level": args.log_level,
    }


def validate_dates(args: argparse.Namespace) -> None:
    """驗證日期參數.

    Args:
        args: 命令行參數物件

    Raises:
        ValueError: 當日期格式不正確時

    Example:
        >>> args = argparse.Namespace(start_date="2023-01-01", end_date="2023-12-31")
        >>> validate_dates(args)  # 不會拋出異常
    """
    if not validate_date_format(args.start_date):
        raise ValueError(f"開始日期格式錯誤: {args.start_date}")
    
    if not validate_date_format(args.end_date):
        raise ValueError(f"結束日期格式錯誤: {args.end_date}")


def build_config(args: argparse.Namespace) -> Dict[str, Any]:
    """構建系統配置字典.

    Args:
        args: 命令行參數物件

    Returns:
        Dict[str, Any]: 系統配置字典

    Raises:
        ValueError: 當配置構建失敗時

    Example:
        >>> args = parse_args()
        >>> config = build_config(args)
        >>> print(config['mode'])
    """
    # 驗證日期格式
    validate_dates(args)

    # 構建各個配置區塊
    strategy_config = build_strategy_config(args)
    portfolio_config = build_portfolio_config(args)
    backtest_config = build_backtest_config(args)
    risk_control_config = build_risk_control_config(args)
    execution_config = build_execution_config(args)
    logging_config = build_logging_config(args)

    # 構建完整配置字典
    config = {
        "mode": args.mode,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "update_data": args.update_data,
        "strategy": strategy_config,
        "portfolio": portfolio_config,
        "backtest": backtest_config,
        "risk_control": risk_control_config,
        "execution": execution_config,
        "logging": logging_config,
    }

    logger.debug("系統配置構建完成: %s", config)
    return config


def init_system(args: argparse.Namespace) -> Dict[str, Any]:
    """初始化系統配置.

    Args:
        args: 命令行參數物件

    Returns:
        Dict[str, Any]: 系統配置字典

    Raises:
        ValueError: 當配置參數不正確時

    Example:
        >>> args = parse_args()
        >>> config = init_system(args)
        >>> print(config['mode'])
    """
    logger.info("初始化系統配置...")

    # 設定日誌系統
    setup_logging(args.log_level)

    # 構建配置字典
    config = build_config(args)

    # 驗證配置
    validate_config(config)

    logger.info("系統配置初始化完成")
    return config


def get_default_config() -> Dict[str, Any]:
    """獲取預設配置.

    Returns:
        Dict[str, Any]: 預設系統配置

    Example:
        >>> config = get_default_config()
        >>> print(config['mode'])
        'backtest'
    """
    return {
        "mode": "backtest",
        "start_date": None,
        "end_date": None,
        "update_data": False,
        "strategy": {
            "name": "ma_cross",
            "params": {},
        },
        "portfolio": {
            "name": "equal_weight",
            "params": {},
        },
        "backtest": {
            "initial_capital": 1000000.0,
            "transaction_cost": 0.001425,
            "slippage": 0.0005,
            "tax": 0.003,
        },
        "risk_control": {
            "max_position_size": 0.1,
            "max_portfolio_risk": 0.02,
            "stop_loss": 0.05,
            "stop_profit": 0.15,
        },
        "execution": {
            "interval": 60,
            "broker": "simulator",
        },
        "logging": {
            "level": "INFO",
        },
    }


def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
    """合併配置字典.

    Args:
        base_config: 基礎配置字典
        override_config: 覆蓋配置字典

    Returns:
        Dict[str, Any]: 合併後的配置字典

    Example:
        >>> base = get_default_config()
        >>> override = {"mode": "paper"}
        >>> merged = merge_configs(base, override)
        >>> print(merged['mode'])
        'paper'
    """
    merged = base_config.copy()
    
    for key, value in override_config.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = merge_configs(merged[key], value)
        else:
            merged[key] = value
    
    return merged
