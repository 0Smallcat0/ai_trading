#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台灣證券交易日曆模組

此模組提供台灣證券交易所的交易日曆功能，包括：
1. 交易日判斷
2. 假日識別和跳過
3. 智能排程功能
4. 交易時段管理
5. 特殊交易日處理

主要功能：
- 準確判斷台灣證券交易日
- 支援國定假日和證交所特殊休市日
- 提供下一個/上一個交易日查詢
- 整合農曆節日計算
- 支援交易時段劃分

Example:
    基本使用：
    ```python
    from src.core.taiwan_trading_calendar import TaiwanTradingCalendar
    
    # 創建日曆實例
    calendar = TaiwanTradingCalendar()
    
    # 檢查是否為交易日
    is_trading = calendar.is_trading_day(date.today())
    
    # 獲取下一個交易日
    next_trading_day = calendar.get_next_trading_day(date.today())
    ```

Note:
    此模組整合了台灣的國定假日、農曆節日和證交所特殊規定，
    提供準確的交易日曆服務。
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any, Set
from dataclasses import dataclass
from enum import Enum
import json
import calendar as cal

# 設定日誌
logger = logging.getLogger(__name__)


class TradingSession(Enum):
    """交易時段"""
    PRE_MARKET = "pre_market"      # 盤前 (08:30-09:00)
    MORNING = "morning"            # 上午盤 (09:00-12:00)
    LUNCH_BREAK = "lunch_break"    # 午休 (12:00-13:30)
    AFTERNOON = "afternoon"        # 下午盤 (13:30-14:30)
    POST_MARKET = "post_market"    # 盤後 (14:30-15:00)
    CLOSED = "closed"              # 休市


class HolidayType(Enum):
    """假日類型"""
    WEEKEND = "weekend"            # 週末
    NATIONAL = "national"          # 國定假日
    LUNAR = "lunar"               # 農曆節日
    EXCHANGE_SPECIAL = "exchange_special"  # 證交所特殊休市
    TYPHOON = "typhoon"           # 颱風假
    MAKEUP_WORK = "makeup_work"   # 補班日


@dataclass
class TradingDayInfo:
    """交易日資訊"""
    date: date
    is_trading_day: bool
    holiday_type: Optional[HolidayType] = None
    holiday_name: Optional[str] = None
    trading_session: TradingSession = TradingSession.CLOSED
    special_notes: Optional[str] = None


@dataclass
class TradingSchedule:
    """交易排程"""
    date: date
    pre_market_start: datetime
    morning_start: datetime
    morning_end: datetime
    afternoon_start: datetime
    afternoon_end: datetime
    post_market_end: datetime
    is_half_day: bool = False
    special_hours: Optional[Dict[str, datetime]] = None


class TaiwanTradingCalendar:
    """台灣證券交易日曆
    
    提供台灣證券交易所的完整日曆服務，包括交易日判斷、
    假日識別、交易時段管理等功能。
    
    Attributes:
        fixed_holidays: 固定國定假日
        lunar_holidays: 農曆節日
        special_holidays: 特殊休市日
        makeup_work_days: 補班日
        
    Example:
        >>> calendar = TaiwanTradingCalendar()
        >>> is_trading = calendar.is_trading_day(date.today())
        >>> next_day = calendar.get_next_trading_day(date.today())
    """
    
    def __init__(self):
        """初始化台灣證券交易日曆"""
        self.fixed_holidays = self._load_fixed_holidays()
        self.lunar_holidays = self._load_lunar_holidays()
        self.special_holidays = self._load_special_holidays()
        self.makeup_work_days = self._load_makeup_work_days()
        
        # 交易時段設定
        self.trading_hours = {
            'pre_market_start': (8, 30),
            'morning_start': (9, 0),
            'morning_end': (12, 0),
            'afternoon_start': (13, 30),
            'afternoon_end': (14, 30),
            'post_market_end': (15, 0)
        }
        
        logger.info("台灣證券交易日曆初始化完成")
    
    def is_trading_day(self, check_date: date) -> bool:
        """檢查是否為交易日

        Args:
            check_date: 要檢查的日期

        Returns:
            bool: 是否為交易日

        Note:
            考慮週末、國定假日、農曆節日、證交所特殊休市日等因素。
        """
        # 檢查是否為補班日（補班日優先，即使是週末也要交易）
        if self._is_makeup_work_day(check_date):
            return True

        # 週末不是交易日（除非是補班日）
        if check_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
            return False

        # 檢查是否為國定假日
        if self._is_national_holiday(check_date):
            return False

        # 檢查是否為農曆節日
        if self._is_lunar_holiday(check_date):
            return False

        # 檢查是否為證交所特殊休市日
        if self._is_special_holiday(check_date):
            return False

        return True
    
    def get_trading_day_info(self, check_date: date) -> TradingDayInfo:
        """獲取交易日詳細資訊
        
        Args:
            check_date: 要檢查的日期
            
        Returns:
            TradingDayInfo: 交易日詳細資訊
            
        Note:
            包含是否為交易日、假日類型、假日名稱等詳細資訊。
        """
        is_trading = self.is_trading_day(check_date)
        holiday_type = None
        holiday_name = None
        trading_session = TradingSession.CLOSED
        special_notes = None
        
        if not is_trading:
            if check_date.weekday() >= 5:
                holiday_type = HolidayType.WEEKEND
                holiday_name = "週末"
            elif self._is_national_holiday(check_date):
                holiday_type = HolidayType.NATIONAL
                holiday_name = self._get_national_holiday_name(check_date)
            elif self._is_lunar_holiday(check_date):
                holiday_type = HolidayType.LUNAR
                holiday_name = self._get_lunar_holiday_name(check_date)
            elif self._is_special_holiday(check_date):
                holiday_type = HolidayType.EXCHANGE_SPECIAL
                holiday_name = self._get_special_holiday_name(check_date)
        else:
            # 交易日，確定當前交易時段
            trading_session = self._get_current_trading_session(check_date)
            
            if self._is_makeup_work_day(check_date):
                special_notes = "補班日"
        
        return TradingDayInfo(
            date=check_date,
            is_trading_day=is_trading,
            holiday_type=holiday_type,
            holiday_name=holiday_name,
            trading_session=trading_session,
            special_notes=special_notes
        )
    
    def get_next_trading_day(
        self, 
        start_date: date, 
        days_ahead: int = 1
    ) -> date:
        """獲取下一個交易日
        
        Args:
            start_date: 起始日期
            days_ahead: 向前查找的交易日數量
            
        Returns:
            date: 下一個交易日
            
        Note:
            如果days_ahead=1，返回下一個交易日；
            如果days_ahead=5，返回第5個交易日。
        """
        current_date = start_date + timedelta(days=1)
        found_days = 0
        
        # 最多查找100天，避免無限迴圈
        for _ in range(100):
            if self.is_trading_day(current_date):
                found_days += 1
                if found_days >= days_ahead:
                    return current_date
            current_date += timedelta(days=1)
        
        # 如果找不到，返回起始日期後100天（應該不會發生）
        logger.warning("無法找到下一個交易日，返回預設日期")
        return start_date + timedelta(days=100)
    
    def get_previous_trading_day(
        self, 
        start_date: date, 
        days_back: int = 1
    ) -> date:
        """獲取上一個交易日
        
        Args:
            start_date: 起始日期
            days_back: 向後查找的交易日數量
            
        Returns:
            date: 上一個交易日
            
        Note:
            如果days_back=1，返回上一個交易日；
            如果days_back=5，返回第5個交易日前。
        """
        current_date = start_date - timedelta(days=1)
        found_days = 0
        
        # 最多查找100天，避免無限迴圈
        for _ in range(100):
            if self.is_trading_day(current_date):
                found_days += 1
                if found_days >= days_back:
                    return current_date
            current_date -= timedelta(days=1)
        
        # 如果找不到，返回起始日期前100天（應該不會發生）
        logger.warning("無法找到上一個交易日，返回預設日期")
        return start_date - timedelta(days=100)
    
    def get_trading_days_in_range(
        self, 
        start_date: date, 
        end_date: date
    ) -> List[date]:
        """獲取日期範圍內的所有交易日
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            
        Returns:
            List[date]: 交易日列表
            
        Note:
            包含start_date和end_date（如果它們是交易日）。
        """
        trading_days = []
        current_date = start_date
        
        while current_date <= end_date:
            if self.is_trading_day(current_date):
                trading_days.append(current_date)
            current_date += timedelta(days=1)
        
        return trading_days
    
    def get_trading_schedule(self, trading_date: date) -> Optional[TradingSchedule]:
        """獲取交易日的詳細時間表
        
        Args:
            trading_date: 交易日期
            
        Returns:
            Optional[TradingSchedule]: 交易時間表，非交易日返回None
            
        Note:
            包含各個交易時段的開始和結束時間。
        """
        if not self.is_trading_day(trading_date):
            return None
        
        # 檢查是否為半日市
        is_half_day = self._is_half_day_trading(trading_date)
        
        # 建立基本時間表
        schedule = TradingSchedule(
            date=trading_date,
            pre_market_start=datetime.combine(
                trading_date, 
                datetime.min.time().replace(
                    hour=self.trading_hours['pre_market_start'][0],
                    minute=self.trading_hours['pre_market_start'][1]
                )
            ),
            morning_start=datetime.combine(
                trading_date,
                datetime.min.time().replace(
                    hour=self.trading_hours['morning_start'][0],
                    minute=self.trading_hours['morning_start'][1]
                )
            ),
            morning_end=datetime.combine(
                trading_date,
                datetime.min.time().replace(
                    hour=self.trading_hours['morning_end'][0],
                    minute=self.trading_hours['morning_end'][1]
                )
            ),
            afternoon_start=datetime.combine(
                trading_date,
                datetime.min.time().replace(
                    hour=self.trading_hours['afternoon_start'][0],
                    minute=self.trading_hours['afternoon_start'][1]
                )
            ),
            afternoon_end=datetime.combine(
                trading_date,
                datetime.min.time().replace(
                    hour=self.trading_hours['afternoon_end'][0],
                    minute=self.trading_hours['afternoon_end'][1]
                )
            ),
            post_market_end=datetime.combine(
                trading_date,
                datetime.min.time().replace(
                    hour=self.trading_hours['post_market_end'][0],
                    minute=self.trading_hours['post_market_end'][1]
                )
            ),
            is_half_day=is_half_day
        )
        
        # 如果是半日市，調整下午時段
        if is_half_day:
            schedule.afternoon_start = schedule.morning_end
            schedule.afternoon_end = schedule.morning_end
            schedule.post_market_end = datetime.combine(
                trading_date,
                datetime.min.time().replace(hour=12, minute=30)
            )
        
        return schedule

    # ==================== 私有輔助方法 ====================

    def _load_fixed_holidays(self) -> Dict[str, List[Tuple[int, int]]]:
        """載入固定國定假日

        Returns:
            Dict[str, List[Tuple[int, int]]]: {假日名稱: [(月, 日), ...]}
        """
        return {
            '元旦': [(1, 1)],
            '和平紀念日': [(2, 28)],
            '兒童節': [(4, 4)],
            '民族掃墓節': [(4, 5)],  # 清明節，有時會調整
            '勞動節': [(5, 1)],
            '端午節': [],  # 農曆節日，在lunar_holidays中處理
            '中秋節': [],  # 農曆節日，在lunar_holidays中處理
            '國慶日': [(10, 10)],
            '春節': []     # 農曆節日，在lunar_holidays中處理
        }

    def _load_lunar_holidays(self) -> Dict[int, Dict[str, List[Tuple[int, int]]]]:
        """載入農曆節日

        Returns:
            Dict[int, Dict[str, List[Tuple[int, int]]]]: {年份: {假日名稱: [(月, 日), ...]}}

        Note:
            農曆節日需要每年計算，這裡提供2024-2026年的資料。
        """
        return {
            2024: {
                '春節': [(2, 8), (2, 9), (2, 10), (2, 11), (2, 12), (2, 13), (2, 14)],
                '端午節': [(6, 10)],
                '中秋節': [(9, 17)]
            },
            2025: {
                '春節': [(1, 28), (1, 29), (1, 30), (1, 31), (2, 1), (2, 2), (2, 3)],
                '端午節': [(5, 31)],
                '中秋節': [(10, 6)]
            },
            2026: {
                '春節': [(2, 16), (2, 17), (2, 18), (2, 19), (2, 20), (2, 21), (2, 22)],
                '端午節': [(6, 19)],
                '中秋節': [(9, 25)]
            }
        }

    def _load_special_holidays(self) -> Dict[int, List[Tuple[int, int, str]]]:
        """載入證交所特殊休市日

        Returns:
            Dict[int, List[Tuple[int, int, str]]]: {年份: [(月, 日, 原因), ...]}
        """
        return {
            2024: [
                # 例如：系統維護日、特殊事件等
            ],
            2025: [
                # 2025年的特殊休市日
            ],
            2026: [
                # 2026年的特殊休市日
            ]
        }

    def _load_makeup_work_days(self) -> Dict[int, List[Tuple[int, int]]]:
        """載入補班日

        Returns:
            Dict[int, List[Tuple[int, int]]]: {年份: [(月, 日), ...]}
        """
        return {
            2024: [
                (2, 17),  # 春節補班
                (9, 14),  # 中秋節補班
            ],
            2025: [
                (2, 8),   # 春節補班
                (10, 4),  # 中秋節補班
            ],
            2026: [
                (2, 7),   # 春節補班
                (9, 26),  # 中秋節補班
            ]
        }

    def _is_national_holiday(self, check_date: date) -> bool:
        """檢查是否為國定假日"""
        month_day = (check_date.month, check_date.day)

        for holiday_name, dates in self.fixed_holidays.items():
            if month_day in dates:
                return True

        return False

    def _is_lunar_holiday(self, check_date: date) -> bool:
        """檢查是否為農曆節日"""
        year = check_date.year
        month_day = (check_date.month, check_date.day)

        if year in self.lunar_holidays:
            for holiday_name, dates in self.lunar_holidays[year].items():
                if month_day in dates:
                    return True

        return False

    def _is_special_holiday(self, check_date: date) -> bool:
        """檢查是否為證交所特殊休市日"""
        year = check_date.year
        month_day = (check_date.month, check_date.day)

        if year in self.special_holidays:
            for month, day, reason in self.special_holidays[year]:
                if (month, day) == month_day:
                    return True

        return False

    def _is_makeup_work_day(self, check_date: date) -> bool:
        """檢查是否為補班日"""
        year = check_date.year
        month_day = (check_date.month, check_date.day)

        if year in self.makeup_work_days:
            return month_day in self.makeup_work_days[year]

        return False

    def _get_national_holiday_name(self, check_date: date) -> Optional[str]:
        """獲取國定假日名稱"""
        month_day = (check_date.month, check_date.day)

        for holiday_name, dates in self.fixed_holidays.items():
            if month_day in dates:
                return holiday_name

        return None

    def _get_lunar_holiday_name(self, check_date: date) -> Optional[str]:
        """獲取農曆節日名稱"""
        year = check_date.year
        month_day = (check_date.month, check_date.day)

        if year in self.lunar_holidays:
            for holiday_name, dates in self.lunar_holidays[year].items():
                if month_day in dates:
                    return holiday_name

        return None

    def _get_special_holiday_name(self, check_date: date) -> Optional[str]:
        """獲取特殊休市日名稱"""
        year = check_date.year
        month_day = (check_date.month, check_date.day)

        if year in self.special_holidays:
            for month, day, reason in self.special_holidays[year]:
                if (month, day) == month_day:
                    return reason

        return None

    def _get_current_trading_session(self, check_date: date) -> TradingSession:
        """獲取當前交易時段"""
        now = datetime.now()

        # 如果不是今天，返回CLOSED
        if check_date != now.date():
            return TradingSession.CLOSED

        current_time = now.time()

        # 盤前時段 (08:30-09:00)
        if (8, 30) <= (current_time.hour, current_time.minute) < (9, 0):
            return TradingSession.PRE_MARKET

        # 上午盤 (09:00-12:00)
        elif (9, 0) <= (current_time.hour, current_time.minute) < (12, 0):
            return TradingSession.MORNING

        # 午休 (12:00-13:30)
        elif (12, 0) <= (current_time.hour, current_time.minute) < (13, 30):
            return TradingSession.LUNCH_BREAK

        # 下午盤 (13:30-14:30)
        elif (13, 30) <= (current_time.hour, current_time.minute) < (14, 30):
            return TradingSession.AFTERNOON

        # 盤後 (14:30-15:00)
        elif (14, 30) <= (current_time.hour, current_time.minute) < (15, 0):
            return TradingSession.POST_MARKET

        # 其他時間為休市
        else:
            return TradingSession.CLOSED

    def _is_half_day_trading(self, check_date: date) -> bool:
        """檢查是否為半日市

        Args:
            check_date: 檢查日期

        Returns:
            bool: 是否為半日市

        Note:
            通常在農曆新年前最後一個交易日為半日市。
        """
        # 檢查是否為農曆新年前最後一個交易日
        year = check_date.year
        if year in self.lunar_holidays:
            spring_festival_dates = self.lunar_holidays[year].get('春節', [])
            if spring_festival_dates:
                # 春節第一天的前一個交易日通常是半日市
                first_spring_day = date(year, spring_festival_dates[0][0], spring_festival_dates[0][1])
                last_trading_day = self.get_previous_trading_day(first_spring_day)
                return check_date == last_trading_day

        return False

    def get_monthly_trading_days(self, year: int, month: int) -> List[date]:
        """獲取指定月份的所有交易日

        Args:
            year: 年份
            month: 月份

        Returns:
            List[date]: 該月份的所有交易日
        """
        # 獲取該月份的第一天和最後一天
        first_day = date(year, month, 1)
        last_day_num = cal.monthrange(year, month)[1]
        last_day = date(year, month, last_day_num)

        return self.get_trading_days_in_range(first_day, last_day)

    def get_yearly_trading_days(self, year: int) -> List[date]:
        """獲取指定年份的所有交易日

        Args:
            year: 年份

        Returns:
            List[date]: 該年份的所有交易日
        """
        first_day = date(year, 1, 1)
        last_day = date(year, 12, 31)

        return self.get_trading_days_in_range(first_day, last_day)

    def get_trading_days_count(self, start_date: date, end_date: date) -> int:
        """計算日期範圍內的交易日數量

        Args:
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            int: 交易日數量
        """
        return len(self.get_trading_days_in_range(start_date, end_date))

    def is_current_trading_session(self, session: TradingSession) -> bool:
        """檢查當前是否為指定的交易時段

        Args:
            session: 要檢查的交易時段

        Returns:
            bool: 是否為指定的交易時段
        """
        current_session = self._get_current_trading_session(date.today())
        return current_session == session
