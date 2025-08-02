"""貨幣格式化器測試模組

測試貨幣格式化器的各項功能，包括貨幣格式化、解析、百分比格式化等。
"""

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
import sys
import os

# 添加專案根目錄到 Python 路徑
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ui.localization.currency_formatter import CurrencyFormatter, format_currency, get_currency_formatter


class TestCurrencyFormatter:
    """貨幣格式化器測試類"""
    
    def setup_method(self):
        """測試前設定"""
        # 模擬語言切換器
        self.mock_language_switcher = MagicMock()
        self.mock_language_switcher.get_current_language.return_value = "zh_TW"
        self.mock_language_switcher.get_number_format.return_value = {
            "decimal_separator": ".",
            "thousand_separator": ","
        }
        
        with patch('src.ui.localization.currency_formatter.get_language_switcher', 
                  return_value=self.mock_language_switcher):
            self.formatter = CurrencyFormatter()
    
    def test_format_currency_basic_twd(self):
        """測試基本 TWD 貨幣格式化"""
        result = self.formatter.format_currency(1234.56, "TWD")
        assert result == "NT$1,234.56"
    
    def test_format_currency_basic_usd(self):
        """測試基本 USD 貨幣格式化"""
        result = self.formatter.format_currency(1234.56, "USD")
        assert result == "$1,234.56"
    
    def test_format_currency_large_amount(self):
        """測試大金額格式化"""
        result = self.formatter.format_currency(1234567.89, "TWD")
        assert result == "NT$1,234,567.89"
    
    def test_format_currency_zero_decimals(self):
        """測試零小數位數格式化"""
        result = self.formatter.format_currency(1234.56, "JPY")
        assert result == "¥1,235"  # JPY 預設 0 小數位數，會四捨五入
    
    def test_format_currency_custom_decimals(self):
        """測試自訂小數位數"""
        result = self.formatter.format_currency(1234.56789, "USD", decimal_places=3)
        assert result == "$1,234.568"
    
    def test_format_currency_no_symbol(self):
        """測試不顯示符號"""
        result = self.formatter.format_currency(1234.56, "USD", show_symbol=False)
        assert result == "1,234.56"
    
    def test_format_currency_with_code(self):
        """測試顯示貨幣代碼"""
        result = self.formatter.format_currency(1234.56, "USD", show_code=True)
        assert result == "$1,234.56 USD"
    
    def test_format_currency_compact_millions(self):
        """測試簡潔格式 - 百萬"""
        result = self.formatter.format_currency(1234567, "USD", compact=True)
        assert result == "$1.23M"
    
    def test_format_currency_compact_thousands(self):
        """測試簡潔格式 - 千"""
        result = self.formatter.format_currency(1234, "USD", compact=True)
        assert result == "$1.23K"
    
    def test_format_currency_compact_billions(self):
        """測試簡潔格式 - 十億"""
        result = self.formatter.format_currency(1234567890, "USD", compact=True)
        assert result == "$1.23B"
    
    def test_format_currency_negative(self):
        """測試負數格式化"""
        result = self.formatter.format_currency(-1234.56, "USD")
        assert result == "$-1,234.56"
    
    def test_format_currency_string_input(self):
        """測試字串輸入"""
        result = self.formatter.format_currency("1234.56", "USD")
        assert result == "$1,234.56"
    
    def test_format_currency_decimal_input(self):
        """測試 Decimal 輸入"""
        result = self.formatter.format_currency(Decimal("1234.56"), "USD")
        assert result == "$1,234.56"
    
    def test_format_currency_default_currency(self):
        """測試預設貨幣"""
        result = self.formatter.format_currency(1234.56)
        assert result == "NT$1,234.56"  # 預設為 TWD
    
    def test_parse_currency_basic(self):
        """測試基本貨幣解析"""
        result = self.formatter.parse_currency("$1,234.56")
        
        assert result["amount"] == 1234.56
        assert result["currency_code"] == "USD"
        assert result["original_string"] == "$1,234.56"
    
    def test_parse_currency_with_code(self):
        """測試帶代碼的貨幣解析"""
        result = self.formatter.parse_currency("NT$1,234.56 TWD")
        
        assert result["amount"] == 1234.56
        assert result["currency_code"] == "TWD"
    
    def test_parse_currency_no_symbol(self):
        """測試無符號貨幣解析"""
        result = self.formatter.parse_currency("1,234.56")
        
        assert result["amount"] == 1234.56
        assert result["currency_code"] == "TWD"  # 預設貨幣
    
    def test_get_currency_symbol(self):
        """測試獲取貨幣符號"""
        assert self.formatter.get_currency_symbol("USD") == "$"
        assert self.formatter.get_currency_symbol("TWD") == "NT$"
        assert self.formatter.get_currency_symbol("EUR") == "€"
        assert self.formatter.get_currency_symbol("INVALID") == ""
    
    def test_get_currency_name_chinese(self):
        """測試獲取中文貨幣名稱"""
        self.mock_language_switcher.get_current_language.return_value = "zh_TW"
        
        assert self.formatter.get_currency_name("USD") == "美元"
        assert self.formatter.get_currency_name("TWD") == "新台幣"
        assert self.formatter.get_currency_name("CNY") == "人民幣"
    
    def test_get_currency_name_english(self):
        """測試獲取英文貨幣名稱"""
        self.mock_language_switcher.get_current_language.return_value = "en_US"
        
        assert self.formatter.get_currency_name("USD") == "US Dollar"
        assert self.formatter.get_currency_name("TWD") == "Taiwan Dollar"
        assert self.formatter.get_currency_name("CNY") == "Chinese Yuan"
    
    def test_get_supported_currencies(self):
        """測試獲取支援的貨幣列表"""
        currencies = self.formatter.get_supported_currencies()
        
        assert "USD" in currencies
        assert "TWD" in currencies
        assert "EUR" in currencies
        assert "JPY" in currencies
        assert currencies["USD"]["symbol"] == "$"
    
    def test_format_percentage_basic(self):
        """測試基本百分比格式化"""
        result = self.formatter.format_percentage(0.1234)
        assert result == "12.34%"
    
    def test_format_percentage_custom_decimals(self):
        """測試自訂小數位數的百分比格式化"""
        result = self.formatter.format_percentage(0.123456, decimal_places=3)
        assert result == "12.346%"
    
    def test_format_percentage_zero_decimals(self):
        """測試零小數位數的百分比格式化"""
        result = self.formatter.format_percentage(0.1234, decimal_places=0)
        assert result == "12%"
    
    def test_format_percentage_negative(self):
        """測試負百分比格式化"""
        result = self.formatter.format_percentage(-0.1234)
        assert result == "-12.34%"


class TestCurrencyFormatterEdgeCases:
    """貨幣格式化器邊界情況測試"""
    
    def setup_method(self):
        """測試前設定"""
        mock_language_switcher = MagicMock()
        mock_language_switcher.get_current_language.return_value = "zh_TW"
        mock_language_switcher.get_number_format.return_value = {
            "decimal_separator": ".",
            "thousand_separator": ","
        }
        
        with patch('src.ui.localization.currency_formatter.get_language_switcher', 
                  return_value=mock_language_switcher):
            self.formatter = CurrencyFormatter()
    
    def test_format_currency_zero(self):
        """測試零值格式化"""
        result = self.formatter.format_currency(0, "USD")
        assert result == "$0.00"
    
    def test_format_currency_very_small(self):
        """測試極小值格式化"""
        result = self.formatter.format_currency(0.01, "USD")
        assert result == "$0.01"
    
    def test_format_currency_very_large(self):
        """測試極大值格式化"""
        result = self.formatter.format_currency(999999999999.99, "USD")
        assert result == "$999,999,999,999.99"
    
    def test_format_currency_invalid_string(self):
        """測試無效字串輸入"""
        result = self.formatter.format_currency("invalid", "USD")
        assert result == "invalid"  # 應該返回原始輸入
    
    def test_format_currency_empty_string(self):
        """測試空字串輸入"""
        result = self.formatter.format_currency("", "USD")
        assert result == "$0.00"
    
    def test_parse_currency_invalid_input(self):
        """測試解析無效輸入"""
        result = self.formatter.parse_currency("invalid input")
        
        assert result["amount"] == 0.0
        assert result["currency_code"] == "TWD"
        assert "error" in result
    
    def test_format_currency_unknown_currency(self):
        """測試未知貨幣代碼"""
        result = self.formatter.format_currency(1234.56, "UNKNOWN")
        # 應該回退到預設貨幣
        assert result == "NT$1,234.56"


class TestGlobalFunctions:
    """全域函數測試類"""
    
    @patch('src.ui.localization.currency_formatter.get_currency_formatter')
    def test_format_currency_function(self, mock_get_formatter):
        """測試全域 format_currency 函數"""
        mock_formatter = MagicMock()
        mock_formatter.format_currency.return_value = "$1,234.56"
        mock_get_formatter.return_value = mock_formatter
        
        result = format_currency(1234.56, "USD")
        
        assert result == "$1,234.56"
        mock_formatter.format_currency.assert_called_once_with(1234.56, "USD")
    
    def test_get_currency_formatter_singleton(self):
        """測試貨幣格式化器單例模式"""
        formatter1 = get_currency_formatter()
        formatter2 = get_currency_formatter()
        
        assert formatter1 is formatter2


class TestNumberFormatLocalization:
    """數字格式本地化測試"""
    
    def test_european_number_format(self):
        """測試歐洲數字格式"""
        mock_language_switcher = MagicMock()
        mock_language_switcher.get_current_language.return_value = "de_DE"
        mock_language_switcher.get_number_format.return_value = {
            "decimal_separator": ",",
            "thousand_separator": "."
        }
        
        with patch('src.ui.localization.currency_formatter.get_language_switcher', 
                  return_value=mock_language_switcher):
            formatter = CurrencyFormatter()
            result = formatter.format_currency(1234.56, "EUR")
            
            # 應該使用歐洲格式：千分位用點，小數用逗號
            assert "1.234,56" in result


if __name__ == "__main__":
    pytest.main([__file__])
