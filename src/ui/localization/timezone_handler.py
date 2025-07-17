"""時區處理器模組

此模組提供時區轉換功能和時間格式化方法，支援交易時間顯示的本地化。
包含多時區支援、交易時間判斷、時間格式化等功能。

主要功能：
- 時區轉換 (UTC, Asia/Taipei, America/New_York 等)
- 時間格式化方法
- 交易時間判斷
- 市場開放時間檢查
- 本地化時間顯示

Example:
    基本使用：
    ```python
    from src.ui.localization.timezone_handler import TimezoneHandler
    
    # 初始化時區處理器
    handler = TimezoneHandler()
    
    # 轉換時區
    local_time = handler.convert_timezone(utc_time, "Asia/Taipei")
    
    # 格式化時間
    formatted = handler.format_datetime(local_time)
    
    # 檢查是否為交易時間
    is_trading = handler.is_trading_hours(local_time, "TSE")
    ```

Note:
    此模組依賴於 pytz 和 datetime 庫，確保所有依賴已正確安裝。
"""

from datetime import datetime, time, timedelta
from typing import Dict, Any, Optional, Union, Tuple
import logging

try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False
    logging.warning("pytz 不可用，時區功能將受限")

try:
    from .language_switcher import get_language_switcher
except ImportError:
    # 備用導入
    from src.ui.localization.language_switcher import get_language_switcher


class TimezoneHandler:
    """時區處理器類
    
    提供時區轉換和時間格式化功能，支援多時區環境下的時間處理。
    包含交易時間判斷、市場開放時間檢查等交易相關功能。
    
    Attributes:
        timezone_configs: 時區配置字典
        market_configs: 市場配置字典
        default_timezone: 預設時區
        
    Methods:
        convert_timezone: 轉換時區
        format_datetime: 格式化日期時間
        format_time: 格式化時間
        is_trading_hours: 檢查是否為交易時間
        get_market_status: 獲取市場狀態
        get_timezone_offset: 獲取時區偏移
    """
    
    # 時區配置
    TIMEZONE_CONFIGS = {
        "UTC": {
            "name_zh": "世界協調時間",
            "name_en": "Coordinated Universal Time",
            "pytz_name": "UTC",
            "offset": "+00:00",
            "abbreviation": "UTC"
        },
        "Asia/Taipei": {
            "name_zh": "台北時間",
            "name_en": "Taipei Time", 
            "pytz_name": "Asia/Taipei",
            "offset": "+08:00",
            "abbreviation": "CST"
        },
        "America/New_York": {
            "name_zh": "紐約時間",
            "name_en": "New York Time",
            "pytz_name": "America/New_York", 
            "offset": "-05:00/-04:00",  # EST/EDT
            "abbreviation": "EST/EDT"
        },
        "Europe/London": {
            "name_zh": "倫敦時間",
            "name_en": "London Time",
            "pytz_name": "Europe/London",
            "offset": "+00:00/+01:00",  # GMT/BST
            "abbreviation": "GMT/BST"
        },
        "Asia/Tokyo": {
            "name_zh": "東京時間", 
            "name_en": "Tokyo Time",
            "pytz_name": "Asia/Tokyo",
            "offset": "+09:00",
            "abbreviation": "JST"
        },
        "Asia/Shanghai": {
            "name_zh": "上海時間",
            "name_en": "Shanghai Time",
            "pytz_name": "Asia/Shanghai",
            "offset": "+08:00",
            "abbreviation": "CST"
        }
    }
    
    # 市場配置
    MARKET_CONFIGS = {
        "TSE": {  # 台灣證券交易所
            "name_zh": "台灣證券交易所",
            "name_en": "Taiwan Stock Exchange",
            "timezone": "Asia/Taipei",
            "trading_hours": {
                "morning": {"start": "09:00", "end": "12:00"},
                "afternoon": {"start": "13:30", "end": "13:30"}
            },
            "trading_days": [0, 1, 2, 3, 4],  # 週一到週五
            "holidays": []  # 可擴展節假日列表
        },
        "NYSE": {  # 紐約證券交易所
            "name_zh": "紐約證券交易所",
            "name_en": "New York Stock Exchange",
            "timezone": "America/New_York",
            "trading_hours": {
                "regular": {"start": "09:30", "end": "16:00"}
            },
            "trading_days": [0, 1, 2, 3, 4],
            "holidays": []
        },
        "LSE": {  # 倫敦證券交易所
            "name_zh": "倫敦證券交易所",
            "name_en": "London Stock Exchange",
            "timezone": "Europe/London",
            "trading_hours": {
                "regular": {"start": "08:00", "end": "16:30"}
            },
            "trading_days": [0, 1, 2, 3, 4],
            "holidays": []
        },
        "TSE_JP": {  # 東京證券交易所
            "name_zh": "東京證券交易所",
            "name_en": "Tokyo Stock Exchange",
            "timezone": "Asia/Tokyo",
            "trading_hours": {
                "morning": {"start": "09:00", "end": "11:30"},
                "afternoon": {"start": "12:30", "end": "15:00"}
            },
            "trading_days": [0, 1, 2, 3, 4],
            "holidays": []
        }
    }
    
    DEFAULT_TIMEZONE = "Asia/Taipei"
    
    def __init__(self):
        """初始化時區處理器"""
        self.language_switcher = get_language_switcher()
        
    def convert_timezone(self, 
                        dt: datetime,
                        target_timezone: str,
                        source_timezone: Optional[str] = None) -> datetime:
        """轉換時區
        
        將日期時間從源時區轉換到目標時區。
        
        Args:
            dt: 日期時間對象
            target_timezone: 目標時區
            source_timezone: 源時區，如果為 None 則假設為 UTC
            
        Returns:
            datetime: 轉換後的日期時間
            
        Example:
            >>> utc_time = datetime.now(pytz.UTC)
            >>> taipei_time = handler.convert_timezone(utc_time, "Asia/Taipei")
        """
        if not PYTZ_AVAILABLE:
            logging.warning("pytz 不可用，無法進行時區轉換")
            return dt
            
        try:
            # 獲取時區對象
            target_tz = pytz.timezone(target_timezone)
            
            # 處理源時區
            if source_timezone:
                source_tz = pytz.timezone(source_timezone)
                if dt.tzinfo is None:
                    dt = source_tz.localize(dt)
                else:
                    dt = dt.astimezone(source_tz)
            else:
                # 如果沒有時區資訊，假設為 UTC
                if dt.tzinfo is None:
                    dt = pytz.UTC.localize(dt)
                    
            # 轉換到目標時區
            return dt.astimezone(target_tz)
            
        except Exception as e:
            logging.error("時區轉換錯誤: %s", e)
            return dt
            
    def format_datetime(self, 
                       dt: datetime,
                       format_type: str = "default",
                       include_timezone: bool = True) -> str:
        """格式化日期時間
        
        根據當前語言設定格式化日期時間。
        
        Args:
            dt: 日期時間對象
            format_type: 格式類型 ("default", "short", "long", "time_only", "date_only")
            include_timezone: 是否包含時區資訊
            
        Returns:
            str: 格式化後的日期時間字串
        """
        try:
            current_lang = self.language_switcher.get_current_language()
            
            # 根據語言選擇格式
            if current_lang.startswith("zh"):
                formats = {
                    "default": "%Y/%m/%d %H:%M:%S",
                    "short": "%m/%d %H:%M",
                    "long": "%Y年%m月%d日 %H時%M分%S秒",
                    "time_only": "%H:%M:%S",
                    "date_only": "%Y/%m/%d"
                }
            else:
                formats = {
                    "default": "%m/%d/%Y %H:%M:%S",
                    "short": "%m/%d %H:%M",
                    "long": "%B %d, %Y %H:%M:%S",
                    "time_only": "%H:%M:%S",
                    "date_only": "%m/%d/%Y"
                }
                
            format_string = formats.get(format_type, formats["default"])
            formatted = dt.strftime(format_string)
            
            # 添加時區資訊
            if include_timezone and dt.tzinfo:
                tz_name = self._get_timezone_display_name(dt.tzinfo)
                formatted += f" ({tz_name})"
                
            return formatted
            
        except Exception as e:
            logging.error("日期時間格式化錯誤: %s", e)
            return str(dt)
            
    def format_time(self, t: time, format_type: str = "default") -> str:
        """格式化時間
        
        Args:
            t: 時間對象
            format_type: 格式類型
            
        Returns:
            str: 格式化後的時間字串
        """
        try:
            current_lang = self.language_switcher.get_current_language()
            
            if current_lang.startswith("zh"):
                formats = {
                    "default": "%H:%M:%S",
                    "short": "%H:%M",
                    "12hour": "%I:%M %p"
                }
            else:
                formats = {
                    "default": "%H:%M:%S",
                    "short": "%H:%M", 
                    "12hour": "%I:%M %p"
                }
                
            format_string = formats.get(format_type, formats["default"])
            return t.strftime(format_string)
            
        except Exception as e:
            logging.error("時間格式化錯誤: %s", e)
            return str(t)
            
    def is_trading_hours(self, 
                        dt: datetime,
                        market: str = "TSE") -> bool:
        """檢查是否為交易時間
        
        Args:
            dt: 日期時間對象
            market: 市場代碼
            
        Returns:
            bool: 是否為交易時間
        """
        try:
            market_config = self.MARKET_CONFIGS.get(market)
            if not market_config:
                logging.warning("未知的市場代碼: %s", market)
                return False
                
            # 轉換到市場時區
            market_timezone = market_config["timezone"]
            market_time = self.convert_timezone(dt, market_timezone)
            
            # 檢查是否為交易日
            weekday = market_time.weekday()
            if weekday not in market_config["trading_days"]:
                return False
                
            # 檢查交易時間
            current_time = market_time.time()
            trading_hours = market_config["trading_hours"]
            
            for session_name, session_hours in trading_hours.items():
                start_time = time.fromisoformat(session_hours["start"])
                end_time = time.fromisoformat(session_hours["end"])
                
                if start_time <= current_time <= end_time:
                    return True
                    
            return False
            
        except Exception as e:
            logging.error("交易時間檢查錯誤: %s", e)
            return False
            
    def get_market_status(self, market: str = "TSE") -> Dict[str, Any]:
        """獲取市場狀態
        
        Args:
            market: 市場代碼
            
        Returns:
            Dict[str, Any]: 市場狀態資訊
        """
        try:
            now = datetime.now(pytz.UTC) if PYTZ_AVAILABLE else datetime.now()
            is_open = self.is_trading_hours(now, market)
            
            market_config = self.MARKET_CONFIGS.get(market, {})
            market_timezone = market_config.get("timezone", self.DEFAULT_TIMEZONE)
            market_time = self.convert_timezone(now, market_timezone)
            
            # 計算下次開市時間
            next_open = self._calculate_next_trading_time(market_time, market)
            
            return {
                "market": market,
                "is_open": is_open,
                "current_time": market_time,
                "next_open": next_open,
                "timezone": market_timezone,
                "status": "開市" if is_open else "休市"
            }
            
        except Exception as e:
            logging.error("獲取市場狀態錯誤: %s", e)
            return {
                "market": market,
                "is_open": False,
                "error": str(e)
            }
            
    def _calculate_next_trading_time(self, current_time: datetime, market: str) -> Optional[datetime]:
        """計算下次交易時間
        
        Args:
            current_time: 當前時間
            market: 市場代碼
            
        Returns:
            Optional[datetime]: 下次交易時間
        """
        try:
            market_config = self.MARKET_CONFIGS.get(market)
            if not market_config:
                return None
                
            trading_hours = market_config["trading_hours"]
            trading_days = market_config["trading_days"]
            
            # 檢查今天剩餘的交易時段
            current_date = current_time.date()
            current_weekday = current_time.weekday()
            
            if current_weekday in trading_days:
                for session_hours in trading_hours.values():
                    start_time = time.fromisoformat(session_hours["start"])
                    session_datetime = datetime.combine(current_date, start_time)
                    
                    if PYTZ_AVAILABLE and current_time.tzinfo:
                        session_datetime = current_time.tzinfo.localize(session_datetime)
                        
                    if session_datetime > current_time:
                        return session_datetime
                        
            # 找下一個交易日
            for i in range(1, 8):  # 最多查找一週
                next_date = current_date + timedelta(days=i)
                next_weekday = next_date.weekday()
                
                if next_weekday in trading_days:
                    # 返回第一個交易時段的開始時間
                    first_session = list(trading_hours.values())[0]
                    start_time = time.fromisoformat(first_session["start"])
                    next_datetime = datetime.combine(next_date, start_time)
                    
                    if PYTZ_AVAILABLE and current_time.tzinfo:
                        next_datetime = current_time.tzinfo.localize(next_datetime)
                        
                    return next_datetime
                    
            return None
            
        except Exception as e:
            logging.error("計算下次交易時間錯誤: %s", e)
            return None
            
    def _get_timezone_display_name(self, tz) -> str:
        """獲取時區顯示名稱
        
        Args:
            tz: 時區對象
            
        Returns:
            str: 時區顯示名稱
        """
        try:
            if hasattr(tz, 'zone'):
                tz_name = tz.zone
                config = self.TIMEZONE_CONFIGS.get(tz_name)
                if config:
                    current_lang = self.language_switcher.get_current_language()
                    if current_lang.startswith("zh"):
                        return config["name_zh"]
                    else:
                        return config["name_en"]
                        
            return str(tz)
            
        except Exception:
            return str(tz)
            
    def get_supported_timezones(self) -> Dict[str, Dict[str, Any]]:
        """獲取支援的時區列表
        
        Returns:
            Dict[str, Dict[str, Any]]: 支援的時區配置字典
        """
        return self.TIMEZONE_CONFIGS.copy()
        
    def get_supported_markets(self) -> Dict[str, Dict[str, Any]]:
        """獲取支援的市場列表
        
        Returns:
            Dict[str, Dict[str, Any]]: 支援的市場配置字典
        """
        return self.MARKET_CONFIGS.copy()


# 全域時區處理器實例
_timezone_handler = None


def get_timezone_handler() -> TimezoneHandler:
    """獲取全域時區處理器實例
    
    Returns:
        TimezoneHandler: 時區處理器實例
    """
    global _timezone_handler
    if _timezone_handler is None:
        _timezone_handler = TimezoneHandler()
    return _timezone_handler


def convert_timezone(dt: datetime, target_timezone: str, source_timezone: Optional[str] = None) -> datetime:
    """便捷函數：轉換時區
    
    Args:
        dt: 日期時間對象
        target_timezone: 目標時區
        source_timezone: 源時區
        
    Returns:
        datetime: 轉換後的日期時間
    """
    return get_timezone_handler().convert_timezone(dt, target_timezone, source_timezone)


def format_datetime(dt: datetime, format_type: str = "default", include_timezone: bool = True) -> str:
    """便捷函數：格式化日期時間
    
    Args:
        dt: 日期時間對象
        format_type: 格式類型
        include_timezone: 是否包含時區資訊
        
    Returns:
        str: 格式化後的日期時間字串
    """
    return get_timezone_handler().format_datetime(dt, format_type, include_timezone)


def is_trading_hours(dt: datetime, market: str = "TSE") -> bool:
    """便捷函數：檢查是否為交易時間
    
    Args:
        dt: 日期時間對象
        market: 市場代碼
        
    Returns:
        bool: 是否為交易時間
    """
    return get_timezone_handler().is_trading_hours(dt, market)
