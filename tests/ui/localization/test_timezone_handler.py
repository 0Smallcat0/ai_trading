"""時區處理器測試模組

測試時區處理器的各項功能，包括時區轉換、時間格式化、交易時間判斷等。
"""

import pytest
from datetime import datetime, time, timedelta
from unittest.mock import patch, MagicMock
import sys
import os

# 添加專案根目錄到 Python 路徑
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 模擬 pytz 模組
from datetime import timezone, timedelta, tzinfo

class MockTimezone(tzinfo):
    def __init__(self, name):
        self.zone = name
        # 創建一個簡單的時區偏移
        if "Taipei" in name or "Shanghai" in name:
            self._offset = timedelta(hours=8)
        elif "Tokyo" in name:
            self._offset = timedelta(hours=9)
        elif "New_York" in name:
            self._offset = timedelta(hours=-5)
        elif "London" in name:
            self._offset = timedelta(hours=0)
        else:
            self._offset = timedelta(hours=0)

    def utcoffset(self, dt):
        return self._offset

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return self.zone

    def localize(self, dt):
        return dt.replace(tzinfo=self)

    def __str__(self):
        return self.zone

mock_pytz = MagicMock()
mock_pytz.UTC = MockTimezone("UTC")
mock_pytz.timezone = lambda name: MockTimezone(name)

# 在導入前設定模擬
sys.modules['pytz'] = mock_pytz

from src.ui.localization.timezone_handler import TimezoneHandler, convert_timezone, get_timezone_handler


class TestTimezoneHandler:
    """時區處理器測試類"""
    
    def setup_method(self):
        """測試前設定"""
        # 模擬語言切換器
        self.mock_language_switcher = MagicMock()
        self.mock_language_switcher.get_current_language.return_value = "zh_TW"
        
        with patch('src.ui.localization.timezone_handler.get_language_switcher', 
                  return_value=self.mock_language_switcher):
            self.handler = TimezoneHandler()
    
    def test_convert_timezone_basic(self):
        """測試基本時區轉換"""
        dt = datetime(2023, 1, 1, 12, 0, 0)
        
        with patch('src.ui.localization.timezone_handler.PYTZ_AVAILABLE', True):
            result = self.handler.convert_timezone(dt, "Asia/Taipei")
            
            # 檢查是否有時區資訊
            assert result.tzinfo is not None
    
    def test_convert_timezone_without_pytz(self):
        """測試沒有 pytz 時的時區轉換"""
        dt = datetime(2023, 1, 1, 12, 0, 0)
        
        with patch('src.ui.localization.timezone_handler.PYTZ_AVAILABLE', False):
            result = self.handler.convert_timezone(dt, "Asia/Taipei")
            
            # 應該返回原始時間
            assert result == dt
    
    def test_format_datetime_chinese(self):
        """測試中文日期時間格式化"""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        self.mock_language_switcher.get_current_language.return_value = "zh_TW"
        
        result = self.handler.format_datetime(dt, "default", include_timezone=False)
        assert "2023/01/01 12:30:45" == result
    
    def test_format_datetime_english(self):
        """測試英文日期時間格式化"""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        self.mock_language_switcher.get_current_language.return_value = "en_US"
        
        result = self.handler.format_datetime(dt, "default", include_timezone=False)
        assert "01/01/2023 12:30:45" == result
    
    def test_format_datetime_short(self):
        """測試短格式日期時間"""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        
        result = self.handler.format_datetime(dt, "short", include_timezone=False)
        assert "01/01 12:30" == result
    
    def test_format_datetime_long_chinese(self):
        """測試中文長格式日期時間"""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        self.mock_language_switcher.get_current_language.return_value = "zh_TW"
        
        result = self.handler.format_datetime(dt, "long", include_timezone=False)
        assert "2023年01月01日 12時30分45秒" == result
    
    def test_format_datetime_time_only(self):
        """測試僅時間格式化"""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        
        result = self.handler.format_datetime(dt, "time_only", include_timezone=False)
        assert "12:30:45" == result
    
    def test_format_datetime_date_only(self):
        """測試僅日期格式化"""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        self.mock_language_switcher.get_current_language.return_value = "zh_TW"
        
        result = self.handler.format_datetime(dt, "date_only", include_timezone=False)
        assert "2023/01/01" == result
    
    def test_format_time_basic(self):
        """測試基本時間格式化"""
        t = time(12, 30, 45)
        
        result = self.handler.format_time(t, "default")
        assert result == "12:30:45"
    
    def test_format_time_short(self):
        """測試短時間格式化"""
        t = time(12, 30, 45)
        
        result = self.handler.format_time(t, "short")
        assert result == "12:30"
    
    def test_is_trading_hours_tse_weekday_morning(self):
        """測試台股交易時間 - 工作日上午"""
        # 週一上午 10:00 (台北時間)
        dt = datetime(2023, 1, 2, 10, 0, 0)  # 2023-01-02 是週一
        dt = MockTimezone("Asia/Taipei").localize(dt)
        
        with patch('src.ui.localization.timezone_handler.PYTZ_AVAILABLE', True):
            result = self.handler.is_trading_hours(dt, "TSE")
            assert result is True
    
    def test_is_trading_hours_tse_weekend(self):
        """測試台股交易時間 - 週末"""
        # 週六上午 10:00 (台北時間)
        dt = datetime(2023, 1, 7, 10, 0, 0)  # 2023-01-07 是週六
        dt = MockTimezone("Asia/Taipei").localize(dt)
        
        with patch('src.ui.localization.timezone_handler.PYTZ_AVAILABLE', True):
            result = self.handler.is_trading_hours(dt, "TSE")
            assert result is False
    
    def test_is_trading_hours_tse_after_hours(self):
        """測試台股交易時間 - 收盤後"""
        # 週一下午 15:00 (台北時間)
        dt = datetime(2023, 1, 2, 15, 0, 0)
        dt = MockTimezone("Asia/Taipei").localize(dt)
        
        with patch('src.ui.localization.timezone_handler.PYTZ_AVAILABLE', True):
            result = self.handler.is_trading_hours(dt, "TSE")
            assert result is False
    
    def test_is_trading_hours_nyse(self):
        """測試紐交所交易時間"""
        # 週一上午 10:00 (紐約時間)
        dt = datetime(2023, 1, 2, 10, 0, 0)
        dt = MockTimezone("America/New_York").localize(dt)
        
        with patch('src.ui.localization.timezone_handler.PYTZ_AVAILABLE', True):
            result = self.handler.is_trading_hours(dt, "NYSE")
            assert result is True
    
    def test_is_trading_hours_unknown_market(self):
        """測試未知市場"""
        dt = datetime(2023, 1, 2, 10, 0, 0)
        
        result = self.handler.is_trading_hours(dt, "UNKNOWN")
        assert result is False
    
    def test_get_market_status_open(self):
        """測試獲取開市狀態"""
        with patch.object(self.handler, 'is_trading_hours', return_value=True):
            with patch('src.ui.localization.timezone_handler.PYTZ_AVAILABLE', True):
                status = self.handler.get_market_status("TSE")
                
                assert status["market"] == "TSE"
                assert status["is_open"] is True
                assert status["status"] == "開市"
    
    def test_get_market_status_closed(self):
        """測試獲取休市狀態"""
        with patch.object(self.handler, 'is_trading_hours', return_value=False):
            with patch('src.ui.localization.timezone_handler.PYTZ_AVAILABLE', True):
                status = self.handler.get_market_status("TSE")
                
                assert status["market"] == "TSE"
                assert status["is_open"] is False
                assert status["status"] == "休市"
    
    def test_get_supported_timezones(self):
        """測試獲取支援的時區列表"""
        timezones = self.handler.get_supported_timezones()
        
        assert "UTC" in timezones
        assert "Asia/Taipei" in timezones
        assert "America/New_York" in timezones
        assert timezones["Asia/Taipei"]["name_zh"] == "台北時間"
    
    def test_get_supported_markets(self):
        """測試獲取支援的市場列表"""
        markets = self.handler.get_supported_markets()
        
        assert "TSE" in markets
        assert "NYSE" in markets
        assert "LSE" in markets
        assert markets["TSE"]["name_zh"] == "台灣證券交易所"
    
    def test_calculate_next_trading_time_same_day(self):
        """測試計算同日下次交易時間"""
        # 週一上午 8:00，下次交易時間應該是 9:00
        current_time = datetime(2023, 1, 2, 8, 0, 0)
        current_time = MockTimezone("Asia/Taipei").localize(current_time)
        
        with patch('src.ui.localization.timezone_handler.PYTZ_AVAILABLE', True):
            next_time = self.handler._calculate_next_trading_time(current_time, "TSE")
            
            assert next_time is not None
            assert next_time.hour == 9
            assert next_time.minute == 0
    
    def test_calculate_next_trading_time_next_day(self):
        """測試計算次日交易時間"""
        # 週五下午 15:00，下次交易時間應該是下週一 9:00
        current_time = datetime(2023, 1, 6, 15, 0, 0)  # 2023-01-06 是週五
        current_time = MockTimezone("Asia/Taipei").localize(current_time)
        
        with patch('src.ui.localization.timezone_handler.PYTZ_AVAILABLE', True):
            next_time = self.handler._calculate_next_trading_time(current_time, "TSE")
            
            assert next_time is not None
            assert next_time.weekday() == 0  # 週一
            assert next_time.hour == 9
            assert next_time.minute == 0


class TestTimezoneHandlerEdgeCases:
    """時區處理器邊界情況測試"""
    
    def setup_method(self):
        """測試前設定"""
        mock_language_switcher = MagicMock()
        mock_language_switcher.get_current_language.return_value = "zh_TW"
        
        with patch('src.ui.localization.timezone_handler.get_language_switcher', 
                  return_value=mock_language_switcher):
            self.handler = TimezoneHandler()
    
    def test_format_datetime_invalid_format(self):
        """測試無效格式類型"""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        
        result = self.handler.format_datetime(dt, "invalid_format", include_timezone=False)
        # 應該使用預設格式
        assert "2023/01/01 12:30:45" == result
    
    def test_format_datetime_with_timezone_info(self):
        """測試帶時區資訊的格式化"""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        dt = MockTimezone("Asia/Taipei").localize(dt)
        
        result = self.handler.format_datetime(dt, "default", include_timezone=True)
        assert "台北時間" in result or "Asia/Taipei" in result
    
    def test_get_timezone_display_name(self):
        """測試獲取時區顯示名稱"""
        tz = MockTimezone("Asia/Taipei")
        
        display_name = self.handler._get_timezone_display_name(tz)
        assert display_name == "台北時間"
    
    def test_get_timezone_display_name_unknown(self):
        """測試獲取未知時區顯示名稱"""
        tz = MockTimezone("Unknown/Timezone")
        
        display_name = self.handler._get_timezone_display_name(tz)
        assert "Unknown/Timezone" in display_name


class TestGlobalFunctions:
    """全域函數測試類"""
    
    @patch('src.ui.localization.timezone_handler.get_timezone_handler')
    def test_convert_timezone_function(self, mock_get_handler):
        """測試全域 convert_timezone 函數"""
        mock_handler = MagicMock()
        mock_dt = datetime(2023, 1, 1, 12, 0, 0)
        mock_handler.convert_timezone.return_value = mock_dt
        mock_get_handler.return_value = mock_handler
        
        dt = datetime(2023, 1, 1, 12, 0, 0)
        result = convert_timezone(dt, "Asia/Taipei")
        
        assert result == mock_dt
        mock_handler.convert_timezone.assert_called_once_with(dt, "Asia/Taipei", None)
    
    def test_get_timezone_handler_singleton(self):
        """測試時區處理器單例模式"""
        handler1 = get_timezone_handler()
        handler2 = get_timezone_handler()
        
        assert handler1 is handler2


class TestErrorHandling:
    """錯誤處理測試類"""
    
    def setup_method(self):
        """測試前設定"""
        mock_language_switcher = MagicMock()
        mock_language_switcher.get_current_language.return_value = "zh_TW"
        
        with patch('src.ui.localization.timezone_handler.get_language_switcher', 
                  return_value=mock_language_switcher):
            self.handler = TimezoneHandler()
    
    def test_convert_timezone_error(self):
        """測試時區轉換錯誤處理"""
        dt = datetime(2023, 1, 1, 12, 0, 0)
        
        with patch('src.ui.localization.timezone_handler.PYTZ_AVAILABLE', True):
            with patch('src.ui.localization.timezone_handler.pytz.timezone',
                      side_effect=Exception("Timezone error")):
                result = self.handler.convert_timezone(dt, "Invalid/Timezone")

                # 應該返回原始時間
                assert result == dt
    
    def test_format_datetime_error(self):
        """測試日期時間格式化錯誤處理"""
        # 使用無效的日期時間對象
        invalid_dt = "not a datetime"
        
        result = self.handler.format_datetime(invalid_dt)
        
        # 應該返回字串表示
        assert result == str(invalid_dt)
    
    def test_is_trading_hours_error(self):
        """測試交易時間檢查錯誤處理"""
        # 使用無效的日期時間對象
        invalid_dt = "not a datetime"
        
        result = self.handler.is_trading_hours(invalid_dt, "TSE")
        
        # 應該返回 False
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__])
