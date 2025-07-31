"""
配置驗證模組

此模組負責處理系統配置的驗證，包括：
- 配置完整性檢查
- 參數格式驗證
- 業務邏輯驗證

主要功能：
- 驗證配置字典的完整性
- 檢查參數格式和範圍
- 提供詳細的錯誤信息

Example:
    >>> from src.core.config_validator import validate_config, validate_date_format
    >>> config = {"mode": "backtest", ...}
    >>> is_valid = validate_config(config)
    >>> print(f"配置有效: {is_valid}")
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)


def validate_date_format(date_str: Optional[str]) -> bool:
    """驗證日期格式.

    Args:
        date_str: 日期字符串，格式應為 YYYY-MM-DD

    Returns:
        bool: 日期格式是否正確

    Example:
        >>> validate_date_format("2023-01-01")
        True
        >>> validate_date_format("2023/01/01")
        False
        >>> validate_date_format(None)
        True
    """
    if date_str is None:
        return True
    
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def parse_json_params(params_str: str) -> Dict[str, Any]:
    """解析 JSON 參數字符串.

    Args:
        params_str: JSON 格式的參數字符串

    Returns:
        Dict[str, Any]: 解析後的參數字典

    Raises:
        ValueError: 當 JSON 格式不正確時

    Example:
        >>> parse_json_params('{"key": "value"}')
        {'key': 'value'}
        >>> parse_json_params('{}')
        {}
    """
    try:
        return json.loads(params_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"參數格式錯誤: {params_str}") from e


def validate_trading_mode(mode: str) -> bool:
    """驗證交易模式.

    Args:
        mode: 交易模式字符串

    Returns:
        bool: 交易模式是否有效

    Example:
        >>> validate_trading_mode("backtest")
        True
        >>> validate_trading_mode("invalid")
        False
    """
    valid_modes = ["backtest", "paper", "live"]
    return mode in valid_modes


def validate_broker_choice(broker: str, mode: str) -> Tuple[bool, str]:
    """驗證券商選擇.

    Args:
        broker: 券商名稱
        mode: 交易模式

    Returns:
        Tuple[bool, str]: (是否有效, 錯誤信息)

    Example:
        >>> validate_broker_choice("ib", "live")
        (True, "")
        >>> validate_broker_choice("simulator", "live")
        (False, "實盤交易模式不能使用模擬券商")
    """
    valid_brokers = ["simulator", "ib", "shioaji", "futu"]
    
    if broker not in valid_brokers:
        return False, f"不支援的券商: {broker}"
    
    if mode == "live" and broker == "simulator":
        return False, "實盤交易模式不能使用模擬券商"
    
    return True, ""


def validate_numeric_range(
    value: float, 
    min_val: float, 
    max_val: float, 
    name: str
) -> Tuple[bool, str]:
    """驗證數值範圍.

    Args:
        value: 要驗證的數值
        min_val: 最小值
        max_val: 最大值
        name: 參數名稱

    Returns:
        Tuple[bool, str]: (是否有效, 錯誤信息)

    Example:
        >>> validate_numeric_range(0.5, 0.0, 1.0, "比例")
        (True, "")
        >>> validate_numeric_range(1.5, 0.0, 1.0, "比例")
        (False, "比例必須在 0.0-1.0 之間")
    """
    if not min_val <= value <= max_val:
        return False, f"{name}必須在 {min_val}-{max_val} 之間"
    return True, ""


def validate_positive_number(value: float, name: str) -> Tuple[bool, str]:
    """驗證正數.

    Args:
        value: 要驗證的數值
        name: 參數名稱

    Returns:
        Tuple[bool, str]: (是否有效, 錯誤信息)

    Example:
        >>> validate_positive_number(1000.0, "初始資金")
        (True, "")
        >>> validate_positive_number(-100.0, "初始資金")
        (False, "初始資金必須大於 0")
    """
    if value <= 0:
        return False, f"{name}必須大於 0"
    return True, ""


def validate_date_range(start_date: Optional[str], end_date: Optional[str]) -> Tuple[bool, str]:
    """驗證日期範圍.

    Args:
        start_date: 開始日期字符串
        end_date: 結束日期字符串

    Returns:
        Tuple[bool, str]: (是否有效, 錯誤信息)

    Example:
        >>> validate_date_range("2023-01-01", "2023-12-31")
        (True, "")
        >>> validate_date_range("2023-12-31", "2023-01-01")
        (False, "開始日期不能大於結束日期")
    """
    if start_date is None or end_date is None:
        return True, ""
    
    if not validate_date_format(start_date):
        return False, f"開始日期格式錯誤: {start_date}"
    
    if not validate_date_format(end_date):
        return False, f"結束日期格式錯誤: {end_date}"
    
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        if start > end:
            return False, "開始日期不能大於結束日期"
        
        return True, ""
    except ValueError as e:
        return False, f"日期解析錯誤: {e}"


def validate_config_completeness(config: Dict[str, Any]) -> List[str]:
    """驗證配置完整性.

    Args:
        config: 系統配置字典

    Returns:
        List[str]: 缺少的配置項列表

    Example:
        >>> config = {"mode": "backtest"}
        >>> missing = validate_config_completeness(config)
        >>> print(f"缺少配置: {missing}")
    """
    required_keys = [
        "mode", "strategy", "portfolio", "backtest", 
        "risk_control", "execution"
    ]
    
    missing_keys = []
    for key in required_keys:
        if key not in config:
            missing_keys.append(key)
    
    return missing_keys


def validate_strategy_config(strategy_config: Dict[str, Any]) -> Tuple[bool, str]:
    """驗證策略配置.

    Args:
        strategy_config: 策略配置字典

    Returns:
        Tuple[bool, str]: (是否有效, 錯誤信息)

    Example:
        >>> strategy_config = {"name": "ma_cross", "params": {}}
        >>> is_valid, error = validate_strategy_config(strategy_config)
        >>> print(f"策略配置有效: {is_valid}")
    """
    if "name" not in strategy_config:
        return False, "策略配置缺少名稱"
    
    if "params" not in strategy_config:
        return False, "策略配置缺少參數"
    
    if not isinstance(strategy_config["params"], dict):
        return False, "策略參數必須是字典格式"
    
    return True, ""


def validate_portfolio_config(portfolio_config: Dict[str, Any]) -> Tuple[bool, str]:
    """驗證投資組合配置.

    Args:
        portfolio_config: 投資組合配置字典

    Returns:
        Tuple[bool, str]: (是否有效, 錯誤信息)

    Example:
        >>> portfolio_config = {"name": "equal_weight", "params": {}}
        >>> is_valid, error = validate_portfolio_config(portfolio_config)
        >>> print(f"投資組合配置有效: {is_valid}")
    """
    if "name" not in portfolio_config:
        return False, "投資組合配置缺少名稱"
    
    if "params" not in portfolio_config:
        return False, "投資組合配置缺少參數"
    
    if not isinstance(portfolio_config["params"], dict):
        return False, "投資組合參數必須是字典格式"
    
    return True, ""


def validate_config(config: Dict[str, Any]) -> bool:
    """驗證配置的完整性和正確性.

    Args:
        config: 系統配置字典

    Returns:
        bool: 配置是否有效

    Raises:
        ValueError: 當配置不正確時

    Example:
        >>> config = {"mode": "backtest", ...}
        >>> validate_config(config)
        True
    """
    # 檢查配置完整性
    missing_keys = validate_config_completeness(config)
    if missing_keys:
        raise ValueError(f"缺少必要配置項: {', '.join(missing_keys)}")
    
    # 驗證交易模式
    if not validate_trading_mode(config["mode"]):
        raise ValueError(f"不支援的交易模式: {config['mode']}")
    
    # 驗證券商選擇
    broker = config.get("execution", {}).get("broker", "simulator")
    is_valid, error_msg = validate_broker_choice(broker, config["mode"])
    if not is_valid:
        raise ValueError(error_msg)
    
    # 驗證數值範圍
    backtest_config = config.get("backtest", {})
    if "initial_capital" in backtest_config:
        is_valid, error_msg = validate_positive_number(
            backtest_config["initial_capital"], "初始資金"
        )
        if not is_valid:
            raise ValueError(error_msg)
    
    risk_config = config.get("risk_control", {})
    if "max_position_size" in risk_config:
        is_valid, error_msg = validate_numeric_range(
            risk_config["max_position_size"], 0.0, 1.0, "最大持倉比例"
        )
        if not is_valid:
            raise ValueError(error_msg)
    
    if "max_portfolio_risk" in risk_config:
        is_valid, error_msg = validate_numeric_range(
            risk_config["max_portfolio_risk"], 0.0, 1.0, "最大投資組合風險"
        )
        if not is_valid:
            raise ValueError(error_msg)
    
    # 驗證策略配置
    if "strategy" in config:
        is_valid, error_msg = validate_strategy_config(config["strategy"])
        if not is_valid:
            raise ValueError(error_msg)
    
    # 驗證投資組合配置
    if "portfolio" in config:
        is_valid, error_msg = validate_portfolio_config(config["portfolio"])
        if not is_valid:
            raise ValueError(error_msg)
    
    # 驗證日期範圍
    start_date = config.get("start_date")
    end_date = config.get("end_date")
    is_valid, error_msg = validate_date_range(start_date, end_date)
    if not is_valid:
        raise ValueError(error_msg)
    
    logger.info("配置驗證通過")
    return True
