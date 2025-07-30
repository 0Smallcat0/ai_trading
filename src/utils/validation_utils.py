# -*- coding: utf-8 -*-
"""
統一資料驗證工具模組

此模組提供統一的資料驗證功能，避免在各個模組中重複實現相同的驗證邏輯。
整合了股票代碼驗證、日期驗證、數值驗證等常用驗證功能。

主要功能：
- 股票代碼格式驗證
- 日期時間格式驗證
- 數值範圍驗證
- 交易參數驗證
- 業務邏輯驗證

Example:
    基本使用：
    ```python
    from src.utils.validation_utils import validate_symbol, validate_date_range
    
    # 驗證股票代碼
    is_valid = validate_symbol("2330.TW")
    
    # 驗證日期範圍
    is_valid, error_msg = validate_date_range("2023-01-01", "2023-12-31")
    ```

Note:
    此模組整合了原本分散在各個模組中的驗證邏輯，
    提供統一的介面和最佳實踐。
"""

import re
import logging
from datetime import datetime, date
from typing import List, Tuple, Optional, Union, Any
from decimal import Decimal, InvalidOperation

# 設定日誌
logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """資料驗證錯誤
    
    當資料驗證失敗時拋出此異常。
    """
    
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        """初始化驗證錯誤
        
        Args:
            message: 錯誤訊息
            field: 驗證失敗的欄位名稱
            value: 驗證失敗的值
        """
        self.message = message
        self.field = field
        self.value = value
        super().__init__(self.message)


# 股票代碼驗證
def validate_symbol(symbol: str, strict: bool = False) -> bool:
    """驗證股票代碼格式
    
    Args:
        symbol: 股票代碼
        strict: 是否使用嚴格模式（要求包含市場後綴）
        
    Returns:
        bool: 是否為有效的股票代碼
        
    Example:
        >>> validate_symbol("2330.TW")
        True
        >>> validate_symbol("AAPL")
        True
        >>> validate_symbol("", strict=True)
        False
    """
    if not symbol or not isinstance(symbol, str):
        return False
    
    symbol = symbol.strip().upper()
    
    if len(symbol) < 1:
        return False
    
    if strict:
        # 嚴格模式：要求台股格式 (數字.TW) 或美股格式 (字母)
        taiwan_pattern = r"^[0-9]{4,6}\.TW$"
        us_pattern = r"^[A-Z]{1,5}$"
        return bool(re.match(taiwan_pattern, symbol) or re.match(us_pattern, symbol))
    else:
        # 寬鬆模式：允許字母、數字、點號
        pattern = r"^[A-Za-z0-9.]+$"
        return bool(re.match(pattern, symbol)) and len(symbol) >= 1


def validate_symbols(symbols: List[str], strict: bool = False) -> Tuple[bool, str]:
    """驗證股票代碼列表
    
    Args:
        symbols: 股票代碼列表
        strict: 是否使用嚴格模式
        
    Returns:
        Tuple[bool, str]: (是否全部有效, 錯誤訊息)
        
    Example:
        >>> validate_symbols(["2330.TW", "2317.TW"])
        (True, "")
        >>> validate_symbols(["", "invalid"])
        (False, "無效的股票代碼: ")
    """
    if not symbols:
        return False, "股票代碼列表不能為空"
    
    for symbol in symbols:
        if not validate_symbol(symbol, strict):
            return False, f"無效的股票代碼: {symbol}"
    
    return True, ""


# 日期時間驗證
def validate_date_format(date_str: Optional[str], format_str: str = "%Y-%m-%d") -> bool:
    """驗證日期格式
    
    Args:
        date_str: 日期字符串
        format_str: 日期格式
        
    Returns:
        bool: 日期格式是否正確
        
    Example:
        >>> validate_date_format("2023-01-01")
        True
        >>> validate_date_format("2023/01/01")
        False
    """
    if date_str is None:
        return True
    
    try:
        datetime.strptime(date_str, format_str)
        return True
    except ValueError:
        return False


def validate_date_range(
    start_date: Union[str, datetime, date], 
    end_date: Union[str, datetime, date],
    max_days: int = 365 * 10
) -> Tuple[bool, str]:
    """驗證日期範圍
    
    Args:
        start_date: 開始日期
        end_date: 結束日期
        max_days: 最大天數限制
        
    Returns:
        Tuple[bool, str]: (是否有效, 錯誤訊息)
        
    Example:
        >>> validate_date_range("2023-01-01", "2023-12-31")
        (True, "")
        >>> validate_date_range("2023-12-31", "2023-01-01")
        (False, "開始日期必須早於結束日期")
    """
    try:
        # 轉換為 datetime 對象
        if isinstance(start_date, str):
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        elif isinstance(start_date, date):
            start_dt = datetime.combine(start_date, datetime.min.time())
        else:
            start_dt = start_date
            
        if isinstance(end_date, str):
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        elif isinstance(end_date, date):
            end_dt = datetime.combine(end_date, datetime.min.time())
        else:
            end_dt = end_date
            
    except (ValueError, TypeError) as e:
        return False, f"日期格式錯誤: {e}"
    
    if start_dt >= end_dt:
        return False, "開始日期必須早於結束日期"
    
    # 檢查日期範圍
    date_diff = end_dt - start_dt
    if date_diff.days > max_days:
        return False, f"日期範圍過長，最多支援{max_days}天"
    
    # 檢查是否為未來日期
    now = datetime.now()
    if start_dt > now:
        return False, "開始日期不能為未來日期"
    
    if end_dt > now:
        return False, "結束日期不能為未來日期"
    
    return True, ""


# 數值驗證
def validate_price(price: Union[float, int, str], min_value: float = 0.01, max_value: float = 1000000.0) -> bool:
    """驗證價格
    
    Args:
        price: 價格值
        min_value: 最小值
        max_value: 最大值
        
    Returns:
        bool: 價格是否有效
        
    Example:
        >>> validate_price(100.5)
        True
        >>> validate_price(-10)
        False
    """
    try:
        price_decimal = Decimal(str(price))
        return min_value <= float(price_decimal) <= max_value
    except (ValueError, InvalidOperation):
        return False


def validate_quantity(quantity: Union[int, str], min_value: int = 1, max_value: int = 1000000) -> bool:
    """驗證數量
    
    Args:
        quantity: 數量值
        min_value: 最小值
        max_value: 最大值
        
    Returns:
        bool: 數量是否有效
        
    Example:
        >>> validate_quantity(100)
        True
        >>> validate_quantity(0)
        False
    """
    try:
        qty = int(quantity)
        return min_value <= qty <= max_value
    except (ValueError, TypeError):
        return False


def validate_percentage(value: Union[float, int, str], min_value: float = 0.0, max_value: float = 1.0) -> bool:
    """驗證百分比值
    
    Args:
        value: 百分比值
        min_value: 最小值
        max_value: 最大值
        
    Returns:
        bool: 百分比是否有效
        
    Example:
        >>> validate_percentage(0.5)
        True
        >>> validate_percentage(1.5)
        False
    """
    try:
        pct = float(value)
        return min_value <= pct <= max_value
    except (ValueError, TypeError):
        return False


# 交易參數驗證
def validate_time_in_force(tif: str) -> bool:
    """驗證有效期限
    
    Args:
        tif: 有效期限
        
    Returns:
        bool: 有效期限是否有效
        
    Example:
        >>> validate_time_in_force("day")
        True
        >>> validate_time_in_force("invalid")
        False
    """
    allowed_tif = ["day", "gtc", "ioc", "fok"]
    return tif.lower() in allowed_tif if tif else False


def validate_order_type(order_type: str) -> bool:
    """驗證訂單類型
    
    Args:
        order_type: 訂單類型
        
    Returns:
        bool: 訂單類型是否有效
        
    Example:
        >>> validate_order_type("market")
        True
        >>> validate_order_type("invalid")
        False
    """
    allowed_types = ["market", "limit", "stop", "stop_limit"]
    return order_type.lower() in allowed_types if order_type else False


# 業務邏輯驗證
def validate_trading_params(
    symbol: str,
    quantity: int,
    price: Optional[float] = None,
    order_type: str = "market",
    time_in_force: str = "day"
) -> Tuple[bool, str]:
    """驗證交易參數
    
    Args:
        symbol: 股票代碼
        quantity: 數量
        price: 價格（限價單必須）
        order_type: 訂單類型
        time_in_force: 有效期限
        
    Returns:
        Tuple[bool, str]: (是否有效, 錯誤訊息)
        
    Example:
        >>> validate_trading_params("2330.TW", 1000, 100.0, "limit")
        (True, "")
    """
    # 驗證股票代碼
    if not validate_symbol(symbol):
        return False, f"無效的股票代碼: {symbol}"
    
    # 驗證數量
    if not validate_quantity(quantity):
        return False, f"無效的數量: {quantity}"
    
    # 驗證訂單類型
    if not validate_order_type(order_type):
        return False, f"無效的訂單類型: {order_type}"
    
    # 驗證有效期限
    if not validate_time_in_force(time_in_force):
        return False, f"無效的有效期限: {time_in_force}"
    
    # 限價單必須有價格
    if order_type.lower() in ["limit", "stop_limit"] and price is None:
        return False, "限價單和停損限價單必須指定價格"
    
    # 驗證價格（如果提供）
    if price is not None and not validate_price(price):
        return False, f"無效的價格: {price}"
    
    return True, ""


# 策略ID驗證
def validate_strategy_id(strategy_id: str) -> bool:
    """驗證策略ID格式
    
    Args:
        strategy_id: 策略ID
        
    Returns:
        bool: 策略ID是否有效
        
    Example:
        >>> validate_strategy_id("ma_cross_strategy")
        True
        >>> validate_strategy_id("invalid-id!")
        False
    """
    if not strategy_id:
        return False
    
    # 只允許字母、數字和下劃線
    pattern = r"^[a-zA-Z0-9_]+$"
    return bool(re.match(pattern, strategy_id))


# 清理規則驗證
def validate_cleaning_rules(rules: List[str]) -> Tuple[bool, str]:
    """驗證清理規則列表
    
    Args:
        rules: 清理規則列表
        
    Returns:
        Tuple[bool, str]: (是否有效, 錯誤訊息)
        
    Example:
        >>> validate_cleaning_rules(["remove_duplicates", "fill_missing_values"])
        (True, "")
    """
    allowed_rules = [
        "remove_duplicates",
        "fill_missing_values", 
        "remove_outliers",
        "normalize_prices",
        "validate_volumes",
        "fix_splits"
    ]
    
    for rule in rules:
        if rule not in allowed_rules:
            return False, f'清理規則必須是: {", ".join(allowed_rules)}'
    
    return True, ""
