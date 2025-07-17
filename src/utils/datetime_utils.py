#!/usr/bin/env python3
"""
統一的 datetime 處理工具模組

此模組提供安全的日期時間處理函數，解決不同類型日期對象的格式化問題。
支援 Python datetime、pandas.Timestamp、numpy.datetime64 等多種類型。

Version: v1.0
Author: AI Trading System
"""

from datetime import datetime, timedelta
from typing import Union, Optional
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def safe_strftime(
    date_obj: Union[datetime, pd.Timestamp, np.datetime64, str, None], 
    format_str: str = "%Y-%m-%d"
) -> str:
    """安全的日期格式化函數
    
    此函數可以處理多種類型的日期對象，並安全地將其格式化為字符串。
    支援的類型包括：
    - Python datetime.datetime
    - pandas.Timestamp
    - numpy.datetime64
    - 字符串（會嘗試解析）
    - None（返回空字符串）
    
    Args:
        date_obj: 日期對象，可以是多種類型
        format_str: 格式化字符串，默認為 "%Y-%m-%d"
    
    Returns:
        str: 格式化後的日期字符串
    
    Examples:
        >>> safe_strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")
        '2025-01-16 10:30:45'
        
        >>> safe_strftime(pd.Timestamp.now(), "%Y/%m/%d")
        '2025/01/16'
        
        >>> safe_strftime(np.datetime64('2025-01-16'), "%Y-%m-%d")
        '2025-01-16'
    """
    try:
        # 處理 None 值
        if date_obj is None:
            return ""
        
        # 如果已經是字符串，嘗試解析
        if isinstance(date_obj, str):
            if not date_obj.strip():  # 空字符串
                return ""
            date_obj = pd.to_datetime(date_obj)
        
        # 如果是 numpy.datetime64，轉換為 pandas.Timestamp
        elif isinstance(date_obj, np.datetime64):
            date_obj = pd.to_datetime(date_obj)
        
        # 如果是 pandas.Timestamp，直接使用
        elif isinstance(date_obj, pd.Timestamp):
            pass
        
        # 如果是 datetime，直接使用
        elif isinstance(date_obj, datetime):
            pass
        
        else:
            # 嘗試使用 pandas 轉換其他類型
            date_obj = pd.to_datetime(date_obj)
        
        # 統一轉換為 datetime 對象進行格式化
        if hasattr(date_obj, 'to_pydatetime'):
            # pandas.Timestamp 轉換為 datetime
            return date_obj.to_pydatetime().strftime(format_str)
        else:
            # 直接使用 strftime
            return date_obj.strftime(format_str)
            
    except Exception as e:
        logger.warning(f"日期格式化失敗: {e}, 輸入: {date_obj}, 格式: {format_str}")
        # 如果所有轉換都失敗，返回字符串表示
        return str(date_obj) if date_obj is not None else ""


def safe_datetime_convert(
    date_obj: Union[datetime, pd.Timestamp, np.datetime64, str, None]
) -> Optional[datetime]:
    """安全的日期轉換函數，統一轉換為 datetime 對象
    
    Args:
        date_obj: 日期對象
    
    Returns:
        datetime: Python datetime 對象，如果轉換失敗返回 None
    
    Examples:
        >>> safe_datetime_convert("2025-01-16")
        datetime.datetime(2025, 1, 16, 0, 0)
        
        >>> safe_datetime_convert(pd.Timestamp.now())
        datetime.datetime(2025, 1, 16, 10, 30, 45, 123456)
    """
    try:
        if date_obj is None:
            return None
            
        if isinstance(date_obj, datetime):
            return date_obj
        elif isinstance(date_obj, pd.Timestamp):
            return date_obj.to_pydatetime()
        elif isinstance(date_obj, np.datetime64):
            return pd.to_datetime(date_obj).to_pydatetime()
        elif isinstance(date_obj, str):
            if not date_obj.strip():
                return None
            return pd.to_datetime(date_obj).to_pydatetime()
        else:
            return pd.to_datetime(date_obj).to_pydatetime()
    except Exception as e:
        logger.warning(f"日期轉換失敗: {e}, 輸入: {date_obj}")
        return None


def format_datetime_for_display(
    date_obj: Union[datetime, pd.Timestamp, np.datetime64, str, None],
    include_time: bool = True,
    include_seconds: bool = False,
    chinese_format: bool = False
) -> str:
    """為顯示格式化日期時間
    
    Args:
        date_obj: 日期對象
        include_time: 是否包含時間
        include_seconds: 是否包含秒數
        chinese_format: 是否使用中文格式
    
    Returns:
        str: 格式化後的日期時間字符串
    
    Examples:
        >>> format_datetime_for_display(datetime.now())
        '2025-01-16 10:30'
        
        >>> format_datetime_for_display(datetime.now(), chinese_format=True)
        '2025年01月16日 10時30分'
    """
    if chinese_format:
        if include_time:
            if include_seconds:
                format_str = "%Y年%m月%d日 %H時%M分%S秒"
            else:
                format_str = "%Y年%m月%d日 %H時%M分"
        else:
            format_str = "%Y年%m月%d日"
    else:
        if include_time:
            if include_seconds:
                format_str = "%Y-%m-%d %H:%M:%S"
            else:
                format_str = "%Y-%m-%d %H:%M"
        else:
            format_str = "%Y-%m-%d"
    
    return safe_strftime(date_obj, format_str)


def format_datetime_for_filename(
    date_obj: Union[datetime, pd.Timestamp, np.datetime64, str, None] = None
) -> str:
    """為文件名格式化日期時間
    
    Args:
        date_obj: 日期對象，如果為 None 則使用當前時間
    
    Returns:
        str: 適合用於文件名的日期時間字符串
    
    Examples:
        >>> format_datetime_for_filename()
        '20250116_103045'
    """
    if date_obj is None:
        date_obj = datetime.now()
    
    return safe_strftime(date_obj, "%Y%m%d_%H%M%S")


def is_valid_datetime(date_obj: Union[datetime, pd.Timestamp, np.datetime64, str]) -> bool:
    """檢查是否為有效的日期時間對象
    
    Args:
        date_obj: 要檢查的日期對象
    
    Returns:
        bool: 如果是有效的日期時間對象返回 True
    
    Examples:
        >>> is_valid_datetime("2025-01-16")
        True
        
        >>> is_valid_datetime("invalid-date")
        False
    """
    try:
        result = safe_datetime_convert(date_obj)
        return result is not None
    except Exception:
        return False


def get_date_range_display(
    start_date: Union[datetime, pd.Timestamp, np.datetime64, str],
    end_date: Union[datetime, pd.Timestamp, np.datetime64, str],
    separator: str = " ~ "
) -> str:
    """格式化日期範圍顯示
    
    Args:
        start_date: 開始日期
        end_date: 結束日期
        separator: 分隔符
    
    Returns:
        str: 格式化後的日期範圍字符串
    
    Examples:
        >>> get_date_range_display("2025-01-01", "2025-01-16")
        '2025-01-01 ~ 2025-01-16'
    """
    start_str = safe_strftime(start_date, "%Y-%m-%d")
    end_str = safe_strftime(end_date, "%Y-%m-%d")
    return f"{start_str}{separator}{end_str}"


def calculate_duration_display(
    start_date: Union[datetime, pd.Timestamp, np.datetime64, str],
    end_date: Union[datetime, pd.Timestamp, np.datetime64, str]
) -> str:
    """計算並顯示時間間隔
    
    Args:
        start_date: 開始日期
        end_date: 結束日期
    
    Returns:
        str: 時間間隔的描述字符串
    
    Examples:
        >>> calculate_duration_display("2025-01-01", "2025-01-16")
        '15 天'
    """
    try:
        start_dt = safe_datetime_convert(start_date)
        end_dt = safe_datetime_convert(end_date)
        
        if start_dt is None or end_dt is None:
            return "無法計算"
        
        duration = end_dt - start_dt
        days = duration.days
        
        if days == 0:
            hours = duration.seconds // 3600
            if hours == 0:
                minutes = duration.seconds // 60
                return f"{minutes} 分鐘"
            else:
                return f"{hours} 小時"
        else:
            return f"{days} 天"
    
    except Exception as e:
        logger.warning(f"時間間隔計算失敗: {e}")
        return "無法計算"


# 常用的日期格式常量
DATE_FORMAT_ISO = "%Y-%m-%d"
DATE_FORMAT_DISPLAY = "%Y-%m-%d"
DATETIME_FORMAT_DISPLAY = "%Y-%m-%d %H:%M:%S"
DATETIME_FORMAT_SHORT = "%Y-%m-%d %H:%M"
DATETIME_FORMAT_FILENAME = "%Y%m%d_%H%M%S"
DATE_FORMAT_CHINESE = "%Y年%m月%d日"
DATETIME_FORMAT_CHINESE = "%Y年%m月%d日 %H時%M分%S秒"
