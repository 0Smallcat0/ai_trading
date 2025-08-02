"""貨幣格式化器模組

此模組提供多幣別格式化功能，支援千分位分隔符和小數位數控制。
根據語言設定自動選擇適當的貨幣格式。

主要功能：
- 多幣別格式化 (TWD, USD, CNY 等)
- 千分位分隔符處理
- 小數位數控制
- 語言相關的格式化規則
- 貨幣符號和代碼管理

Example:
    基本使用：
    ```python
    from src.ui.localization.currency_formatter import CurrencyFormatter
    
    # 初始化格式化器
    formatter = CurrencyFormatter()
    
    # 格式化貨幣
    formatted = formatter.format_currency(1234567.89, "TWD")
    # 輸出: "NT$1,234,567.89"
    
    # 格式化為簡潔形式
    compact = formatter.format_currency_compact(1234567.89, "USD")
    # 輸出: "$1.23M"
    ```

Note:
    此模組依賴於語言切換器模組，確保語言設定正確。
"""

import re
from typing import Dict, Any, Optional, Union
from decimal import Decimal, ROUND_HALF_UP
import logging

try:
    from .language_switcher import get_language_switcher
except ImportError:
    # 備用導入
    from src.ui.localization.language_switcher import get_language_switcher


class CurrencyFormatter:
    """貨幣格式化器類
    
    提供多幣別格式化功能，支援不同語言環境下的貨幣顯示格式。
    包含千分位分隔符、小數位數控制、貨幣符號管理等功能。
    
    Attributes:
        currency_configs: 貨幣配置字典
        default_currency: 預設貨幣
        
    Methods:
        format_currency: 格式化貨幣
        format_currency_compact: 格式化為簡潔形式
        parse_currency: 解析貨幣字串
        get_currency_symbol: 獲取貨幣符號
        get_supported_currencies: 獲取支援的貨幣列表
    """
    
    # 貨幣配置
    CURRENCY_CONFIGS = {
        "TWD": {
            "symbol": "NT$",
            "code": "TWD",
            "name_zh": "新台幣",
            "name_en": "Taiwan Dollar",
            "decimal_places": 2,
            "symbol_position": "before",  # before 或 after
            "space_between": False
        },
        "USD": {
            "symbol": "$",
            "code": "USD", 
            "name_zh": "美元",
            "name_en": "US Dollar",
            "decimal_places": 2,
            "symbol_position": "before",
            "space_between": False
        },
        "CNY": {
            "symbol": "¥",
            "code": "CNY",
            "name_zh": "人民幣", 
            "name_en": "Chinese Yuan",
            "decimal_places": 2,
            "symbol_position": "before",
            "space_between": False
        },
        "JPY": {
            "symbol": "¥",
            "code": "JPY",
            "name_zh": "日圓",
            "name_en": "Japanese Yen", 
            "decimal_places": 0,
            "symbol_position": "before",
            "space_between": False
        },
        "EUR": {
            "symbol": "€",
            "code": "EUR",
            "name_zh": "歐元",
            "name_en": "Euro",
            "decimal_places": 2,
            "symbol_position": "before",
            "space_between": False
        },
        "GBP": {
            "symbol": "£",
            "code": "GBP",
            "name_zh": "英鎊",
            "name_en": "British Pound",
            "decimal_places": 2,
            "symbol_position": "before",
            "space_between": False
        }
    }
    
    DEFAULT_CURRENCY = "TWD"
    
    def __init__(self):
        """初始化貨幣格式化器"""
        self.language_switcher = get_language_switcher()
        
    def format_currency(self, 
                       amount: Union[int, float, Decimal, str],
                       currency_code: str = None,
                       decimal_places: Optional[int] = None,
                       show_symbol: bool = True,
                       show_code: bool = False,
                       compact: bool = False) -> str:
        """格式化貨幣
        
        將數值格式化為指定貨幣格式的字串。
        
        Args:
            amount: 金額數值
            currency_code: 貨幣代碼，如果為 None 則使用預設貨幣
            decimal_places: 小數位數，如果為 None 則使用貨幣預設設定
            show_symbol: 是否顯示貨幣符號
            show_code: 是否顯示貨幣代碼
            compact: 是否使用簡潔格式 (K, M, B)
            
        Returns:
            str: 格式化後的貨幣字串
            
        Example:
            >>> formatter.format_currency(1234567.89, "TWD")
            "NT$1,234,567.89"
            >>> formatter.format_currency(1234567.89, "USD", compact=True)
            "$1.23M"
        """
        try:
            # 轉換為 Decimal 以確保精度
            if isinstance(amount, str):
                # 檢查原始字串是否包含數字（空字串特殊處理）
                if amount and not any(c.isdigit() for c in amount):
                    # 如果原始字串沒有數字，返回原始字串
                    return str(amount)

                # 移除非數字字符（除了小數點和負號）
                clean_amount = re.sub(r'[^\d.-]', '', amount)
                if not clean_amount:
                    # 空字串處理為 0
                    amount = Decimal('0')
                else:
                    amount = Decimal(clean_amount)
            else:
                amount = Decimal(str(amount))
                
            # 獲取貨幣配置
            if currency_code is None:
                currency_code = self.DEFAULT_CURRENCY
                
            currency_config = self.CURRENCY_CONFIGS.get(currency_code, self.CURRENCY_CONFIGS[self.DEFAULT_CURRENCY])
            
            # 確定小數位數
            if decimal_places is None:
                decimal_places = currency_config["decimal_places"]
                
            # 簡潔格式處理
            if compact:
                return self._format_compact(amount, currency_config, show_symbol, show_code)
                
            # 四捨五入到指定小數位數
            if decimal_places > 0:
                quantize_exp = Decimal('0.1') ** decimal_places
                amount = amount.quantize(quantize_exp, rounding=ROUND_HALF_UP)
            else:
                amount = amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
                
            # 獲取數字格式設定
            number_format = self.language_switcher.get_number_format()
            decimal_sep = number_format["decimal_separator"]
            thousand_sep = number_format["thousand_separator"]
            
            # 分離整數和小數部分
            amount_str = str(amount)
            if '.' in amount_str:
                integer_part, decimal_part = amount_str.split('.')
            else:
                integer_part = amount_str
                decimal_part = ""
                
            # 處理負數
            is_negative = integer_part.startswith('-')
            if is_negative:
                integer_part = integer_part[1:]
                
            # 添加千分位分隔符
            if len(integer_part) > 3:
                # 從右到左每三位添加分隔符
                formatted_integer = ""
                for i, digit in enumerate(reversed(integer_part)):
                    if i > 0 and i % 3 == 0:
                        formatted_integer = thousand_sep + formatted_integer
                    formatted_integer = digit + formatted_integer
            else:
                formatted_integer = integer_part
                
            # 組合數字部分
            if decimal_places > 0 and decimal_part:
                # 確保小數部分有正確的位數
                decimal_part = decimal_part.ljust(decimal_places, '0')[:decimal_places]
                number_part = formatted_integer + decimal_sep + decimal_part
            elif decimal_places > 0:
                # 添加零小數部分
                number_part = formatted_integer + decimal_sep + '0' * decimal_places
            else:
                number_part = formatted_integer
                
            # 添加負號
            if is_negative:
                number_part = '-' + number_part
                
            # 組合貨幣符號和代碼
            result = self._combine_currency_parts(
                number_part, currency_config, show_symbol, show_code
            )
            
            return result
            
        except Exception as e:
            logging.error("貨幣格式化錯誤: %s", e)
            # 對於無效輸入，返回錯誤格式
            if isinstance(amount, str) and not any(c.isdigit() for c in amount):
                return str(amount)
            return str(amount)
            
    def _format_compact(self, 
                       amount: Decimal,
                       currency_config: Dict[str, Any],
                       show_symbol: bool,
                       show_code: bool) -> str:
        """格式化為簡潔形式
        
        Args:
            amount: 金額
            currency_config: 貨幣配置
            show_symbol: 是否顯示符號
            show_code: 是否顯示代碼
            
        Returns:
            str: 簡潔格式的貨幣字串
        """
        abs_amount = abs(amount)
        is_negative = amount < 0
        
        # 確定縮放單位
        if abs_amount >= 1_000_000_000:
            scaled = abs_amount / 1_000_000_000
            suffix = "B"
        elif abs_amount >= 1_000_000:
            scaled = abs_amount / 1_000_000
            suffix = "M"
        elif abs_amount >= 1_000:
            scaled = abs_amount / 1_000
            suffix = "K"
        else:
            scaled = abs_amount
            suffix = ""
            
        # 格式化縮放後的數值
        if scaled >= 100:
            number_part = f"{scaled:.0f}"
        elif scaled >= 10:
            number_part = f"{scaled:.1f}"
        else:
            number_part = f"{scaled:.2f}"
            
        # 移除不必要的小數零
        if '.' in number_part:
            number_part = number_part.rstrip('0').rstrip('.')
            
        # 添加後綴
        number_part += suffix
        
        # 添加負號
        if is_negative:
            number_part = '-' + number_part
            
        # 組合貨幣符號和代碼
        return self._combine_currency_parts(
            number_part, currency_config, show_symbol, show_code
        )
        
    def _combine_currency_parts(self,
                               number_part: str,
                               currency_config: Dict[str, Any],
                               show_symbol: bool,
                               show_code: bool) -> str:
        """組合貨幣各部分
        
        Args:
            number_part: 數字部分
            currency_config: 貨幣配置
            show_symbol: 是否顯示符號
            show_code: 是否顯示代碼
            
        Returns:
            str: 完整的貨幣字串
        """
        parts = []
        
        # 處理符號位置
        if show_symbol:
            symbol = currency_config["symbol"]
            space = " " if currency_config["space_between"] else ""
            
            if currency_config["symbol_position"] == "before":
                parts.append(symbol + space + number_part)
            else:
                parts.append(number_part + space + symbol)
        else:
            parts.append(number_part)
            
        # 添加貨幣代碼
        if show_code:
            parts.append(currency_config["code"])
            
        return " ".join(parts)
        
    def parse_currency(self, currency_string: str) -> Dict[str, Any]:
        """解析貨幣字串
        
        將格式化的貨幣字串解析為數值和貨幣資訊。
        
        Args:
            currency_string: 貨幣字串
            
        Returns:
            Dict[str, Any]: 包含 amount, currency_code 等資訊的字典
        """
        try:
            # 移除空格
            clean_string = currency_string.strip()
            
            # 檢測貨幣代碼和符號
            detected_currency = None
            for code, config in self.CURRENCY_CONFIGS.items():
                if code in clean_string or config["symbol"] in clean_string:
                    detected_currency = code
                    break
                    
            # 移除貨幣符號和代碼
            number_string = clean_string
            if detected_currency:
                config = self.CURRENCY_CONFIGS[detected_currency]
                number_string = number_string.replace(config["symbol"], "")
                number_string = number_string.replace(config["code"], "")
                
            # 移除千分位分隔符和其他非數字字符
            number_string = re.sub(r'[^\d.-]', '', number_string)

            # 轉換為數值
            if not number_string or not any(c.isdigit() for c in number_string):
                raise ValueError("No valid number found")
            amount = float(number_string)
            
            return {
                "amount": amount,
                "currency_code": detected_currency or self.DEFAULT_CURRENCY,
                "original_string": currency_string
            }
            
        except Exception as e:
            logging.error("貨幣解析錯誤: %s", e)
            return {
                "amount": 0.0,
                "currency_code": self.DEFAULT_CURRENCY,
                "original_string": currency_string,
                "error": str(e)
            }
            
    def get_currency_symbol(self, currency_code: str) -> str:
        """獲取貨幣符號
        
        Args:
            currency_code: 貨幣代碼
            
        Returns:
            str: 貨幣符號
        """
        config = self.CURRENCY_CONFIGS.get(currency_code)
        return config["symbol"] if config else ""
        
    def get_currency_name(self, currency_code: str) -> str:
        """獲取貨幣名稱
        
        Args:
            currency_code: 貨幣代碼
            
        Returns:
            str: 貨幣名稱
        """
        config = self.CURRENCY_CONFIGS.get(currency_code)
        if not config:
            return currency_code
            
        current_lang = self.language_switcher.get_current_language()
        if current_lang.startswith("zh"):
            return config["name_zh"]
        else:
            return config["name_en"]
            
    def get_supported_currencies(self) -> Dict[str, Dict[str, Any]]:
        """獲取支援的貨幣列表
        
        Returns:
            Dict[str, Dict[str, Any]]: 支援的貨幣配置字典
        """
        return self.CURRENCY_CONFIGS.copy()
        
    def format_percentage(self, value: Union[int, float, Decimal], decimal_places: int = 2) -> str:
        """格式化百分比
        
        Args:
            value: 百分比數值 (例如 0.1234 表示 12.34%)
            decimal_places: 小數位數
            
        Returns:
            str: 格式化後的百分比字串
        """
        try:
            percentage = Decimal(str(value)) * 100
            quantize_exp = Decimal('0.1') ** decimal_places
            percentage = percentage.quantize(quantize_exp, rounding=ROUND_HALF_UP)
            
            # 獲取數字格式設定
            number_format = self.language_switcher.get_number_format()
            decimal_sep = number_format["decimal_separator"]
            
            # 格式化數字
            if decimal_places > 0:
                formatted = f"{percentage:.{decimal_places}f}".replace('.', decimal_sep)
            else:
                formatted = f"{percentage:.0f}"
                
            return formatted + "%"
            
        except Exception as e:
            logging.error("百分比格式化錯誤: %s", e)
            return f"{value}%"


# 全域貨幣格式化器實例
_currency_formatter = None


def get_currency_formatter() -> CurrencyFormatter:
    """獲取全域貨幣格式化器實例
    
    Returns:
        CurrencyFormatter: 貨幣格式化器實例
    """
    global _currency_formatter
    if _currency_formatter is None:
        _currency_formatter = CurrencyFormatter()
    return _currency_formatter


def format_currency(amount: Union[int, float, Decimal, str], 
                   currency_code: str = None, 
                   **kwargs) -> str:
    """便捷函數：格式化貨幣
    
    Args:
        amount: 金額
        currency_code: 貨幣代碼
        **kwargs: 其他格式化參數
        
    Returns:
        str: 格式化後的貨幣字串
    """
    return get_currency_formatter().format_currency(amount, currency_code, **kwargs)


def format_percentage(value: Union[int, float, Decimal], decimal_places: int = 2) -> str:
    """便捷函數：格式化百分比
    
    Args:
        value: 百分比數值
        decimal_places: 小數位數
        
    Returns:
        str: 格式化後的百分比字串
    """
    return get_currency_formatter().format_percentage(value, decimal_places)
