"""本地化模組

此模組提供完整的本地化支援功能，包括語言切換、貨幣格式化、時區處理等。
支援中英文切換和多種貨幣、時區的本地化顯示。

主要組件：
- LanguageSwitcher: 語言切換器
- CurrencyFormatter: 貨幣格式化器  
- TimezoneHandler: 時區處理器

Example:
    基本使用：
    ```python
    from src.ui.localization import (
        get_text, 
        format_currency, 
        format_datetime,
        show_language_selector
    )
    
    # 顯示語言選擇器
    show_language_selector()
    
    # 獲取本地化文字
    title = get_text("app.title")
    
    # 格式化貨幣
    price = format_currency(1234.56, "TWD")
    
    # 格式化時間
    time_str = format_datetime(datetime.now())
    ```

Note:
    此模組整合了所有本地化功能，提供統一的介面供其他模組使用。
"""

# 導入主要類別
from .language_switcher import (
    LanguageSwitcher,
    get_language_switcher,
    get_text,
    show_language_selector
)

from .currency_formatter import (
    CurrencyFormatter,
    get_currency_formatter,
    format_currency,
    format_percentage
)

from .timezone_handler import (
    TimezoneHandler,
    get_timezone_handler,
    convert_timezone,
    format_datetime,
    is_trading_hours
)

# 版本資訊
__version__ = "1.0.0"
__author__ = "AI Trading System Team"

# 匯出的公共介面
__all__ = [
    # 語言切換相關
    "LanguageSwitcher",
    "get_language_switcher", 
    "get_text",
    "show_language_selector",
    
    # 貨幣格式化相關
    "CurrencyFormatter",
    "get_currency_formatter",
    "format_currency", 
    "format_percentage",
    
    # 時區處理相關
    "TimezoneHandler",
    "get_timezone_handler",
    "convert_timezone",
    "format_datetime",
    "is_trading_hours",
    
    # 便捷函數
    "setup_localization",
    "get_localization_status"
]


def setup_localization(default_language: str = "zh_TW", 
                      default_currency: str = "TWD",
                      default_timezone: str = "Asia/Taipei") -> dict:
    """設定本地化環境
    
    初始化本地化設定，包括預設語言、貨幣和時區。
    
    Args:
        default_language: 預設語言代碼
        default_currency: 預設貨幣代碼
        default_timezone: 預設時區
        
    Returns:
        dict: 設定結果
    """
    try:
        # 初始化各個組件
        language_switcher = get_language_switcher()
        currency_formatter = get_currency_formatter()
        timezone_handler = get_timezone_handler()
        
        # 設定預設值
        if default_language in language_switcher.SUPPORTED_LANGUAGES:
            language_switcher.set_language(default_language)
            
        # 更新預設貨幣（如果需要）
        if default_currency in currency_formatter.CURRENCY_CONFIGS:
            currency_formatter.DEFAULT_CURRENCY = default_currency
            
        # 更新預設時區（如果需要）
        if default_timezone in timezone_handler.TIMEZONE_CONFIGS:
            timezone_handler.DEFAULT_TIMEZONE = default_timezone
            
        return {
            "status": "success",
            "language": default_language,
            "currency": default_currency,
            "timezone": default_timezone,
            "message": "本地化設定完成"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "本地化設定失敗"
        }


def get_localization_status() -> dict:
    """獲取本地化狀態
    
    Returns:
        dict: 本地化狀態資訊
    """
    try:
        language_switcher = get_language_switcher()
        currency_formatter = get_currency_formatter()
        timezone_handler = get_timezone_handler()
        
        return {
            "language": {
                "current": language_switcher.get_current_language(),
                "supported": list(language_switcher.SUPPORTED_LANGUAGES.keys()),
                "resources_loaded": len(language_switcher.language_resources)
            },
            "currency": {
                "default": currency_formatter.DEFAULT_CURRENCY,
                "supported": list(currency_formatter.CURRENCY_CONFIGS.keys())
            },
            "timezone": {
                "default": timezone_handler.DEFAULT_TIMEZONE,
                "supported": list(timezone_handler.TIMEZONE_CONFIGS.keys()),
                "markets": list(timezone_handler.MARKET_CONFIGS.keys())
            },
            "status": "ready"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
