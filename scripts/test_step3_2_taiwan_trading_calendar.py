#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步驟 3.2 台灣證券交易日曆測試腳本

此腳本用於測試台灣證券交易日曆的功能，包括：
1. 交易日判斷測試
2. 假日識別測試
3. 交易日查詢測試
4. 交易時段管理測試
5. 日曆範圍查詢測試

Usage:
    python scripts/test_step3_2_taiwan_trading_calendar.py
"""

import sys
import os
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/test_step3_2_taiwan_trading_calendar.log')
    ]
)
logger = logging.getLogger(__name__)

# 確保日誌目錄存在
os.makedirs('logs', exist_ok=True)

def test_calendar_initialization():
    """測試日曆初始化"""
    logger.info("=== 測試日曆初始化 ===")
    
    try:
        from src.core.taiwan_trading_calendar import TaiwanTradingCalendar
        
        # 測試基本初始化
        calendar = TaiwanTradingCalendar()
        
        # 檢查基本屬性
        assert hasattr(calendar, 'fixed_holidays')
        assert hasattr(calendar, 'lunar_holidays')
        assert hasattr(calendar, 'special_holidays')
        assert hasattr(calendar, 'makeup_work_days')
        assert hasattr(calendar, 'trading_hours')
        
        # 檢查假日資料
        assert '元旦' in calendar.fixed_holidays
        assert '春節' in calendar.fixed_holidays
        assert '國慶日' in calendar.fixed_holidays
        
        # 檢查農曆節日資料
        assert 2024 in calendar.lunar_holidays
        assert 2025 in calendar.lunar_holidays
        
        logger.info("日曆初始化成功")
        logger.info("固定假日數量: %d", len(calendar.fixed_holidays))
        logger.info("農曆節日年份: %s", list(calendar.lunar_holidays.keys()))
        
        return True, calendar
        
    except Exception as e:
        logger.error("日曆初始化失敗: %s", e)
        return False, None


def test_trading_day_detection(calendar):
    """測試交易日判斷功能"""
    logger.info("=== 測試交易日判斷功能 ===")
    
    try:
        # 測試已知的交易日和非交易日
        test_cases = [
            # (日期, 預期結果, 描述)
            (date(2024, 1, 1), False, "元旦"),
            (date(2024, 1, 2), True, "元旦後第一個工作日"),
            (date(2024, 2, 10), False, "春節"),
            (date(2024, 2, 17), True, "春節補班日"),
            (date(2024, 6, 7), True, "一般工作日（週五）"),
            (date(2024, 6, 8), False, "週六"),
            (date(2024, 6, 9), False, "週日"),
            (date(2024, 6, 10), False, "端午節"),
            (date(2024, 10, 10), False, "國慶日"),
            (date(2024, 12, 25), True, "聖誕節（台灣不放假）")
        ]
        
        passed = 0
        total = len(test_cases)
        
        for test_date, expected, description in test_cases:
            result = calendar.is_trading_day(test_date)
            if result == expected:
                logger.info("✓ %s (%s): %s", test_date, description, 
                           "交易日" if result else "非交易日")
                passed += 1
            else:
                logger.error("✗ %s (%s): 預期 %s，實際 %s", 
                           test_date, description, expected, result)
        
        logger.info("交易日判斷測試: %d/%d 通過", passed, total)
        return passed == total
        
    except Exception as e:
        logger.error("交易日判斷測試失敗: %s", e)
        return False


def test_trading_day_info(calendar):
    """測試交易日詳細資訊功能"""
    logger.info("=== 測試交易日詳細資訊功能 ===")
    
    try:
        # 測試不同類型的日期
        test_dates = [
            date(2024, 1, 1),   # 元旦
            date(2024, 2, 10),  # 春節
            date(2024, 2, 17),  # 補班日
            date(2024, 6, 8),   # 一般工作日
            date(2024, 6, 9),   # 週日
        ]
        
        for test_date in test_dates:
            info = calendar.get_trading_day_info(test_date)
            
            # 驗證資訊結構
            assert hasattr(info, 'date')
            assert hasattr(info, 'is_trading_day')
            assert hasattr(info, 'holiday_type')
            assert hasattr(info, 'holiday_name')
            assert hasattr(info, 'trading_session')
            
            logger.info("%s: %s", test_date, 
                       "交易日" if info.is_trading_day else f"非交易日 ({info.holiday_name})")
            
            if info.special_notes:
                logger.info("  特殊說明: %s", info.special_notes)
        
        logger.info("交易日詳細資訊測試通過")
        return True
        
    except Exception as e:
        logger.error("交易日詳細資訊測試失敗: %s", e)
        return False


def test_next_previous_trading_day(calendar):
    """測試下一個/上一個交易日查詢"""
    logger.info("=== 測試下一個/上一個交易日查詢 ===")
    
    try:
        # 測試從不同日期查找下一個交易日
        test_cases = [
            date(2024, 1, 1),   # 元旦
            date(2024, 2, 9),   # 春節前
            date(2024, 6, 7),   # 週五
            date(2024, 6, 8),   # 週六
            date(2024, 6, 9),   # 週日
        ]
        
        for test_date in test_cases:
            # 測試下一個交易日
            next_day = calendar.get_next_trading_day(test_date)
            assert calendar.is_trading_day(next_day)
            logger.info("%s 的下一個交易日: %s", test_date, next_day)
            
            # 測試上一個交易日
            prev_day = calendar.get_previous_trading_day(test_date)
            assert calendar.is_trading_day(prev_day)
            logger.info("%s 的上一個交易日: %s", test_date, prev_day)
            
            # 測試多天後的交易日
            next_5_days = calendar.get_next_trading_day(test_date, 5)
            assert calendar.is_trading_day(next_5_days)
            logger.info("%s 的第5個交易日: %s", test_date, next_5_days)
        
        logger.info("下一個/上一個交易日查詢測試通過")
        return True
        
    except Exception as e:
        logger.error("下一個/上一個交易日查詢測試失敗: %s", e)
        return False


def test_trading_days_in_range(calendar):
    """測試日期範圍內交易日查詢"""
    logger.info("=== 測試日期範圍內交易日查詢 ===")
    
    try:
        # 測試不同的日期範圍
        test_ranges = [
            (date(2024, 1, 1), date(2024, 1, 31), "2024年1月"),
            (date(2024, 2, 1), date(2024, 2, 29), "2024年2月（含春節）"),
            (date(2024, 6, 1), date(2024, 6, 30), "2024年6月"),
            (date(2024, 10, 1), date(2024, 10, 31), "2024年10月（含國慶日）")
        ]
        
        for start_date, end_date, description in test_ranges:
            trading_days = calendar.get_trading_days_in_range(start_date, end_date)
            trading_count = len(trading_days)
            total_days = (end_date - start_date).days + 1
            
            logger.info("%s: %d 個交易日 / %d 天 (%.1f%%)", 
                       description, trading_count, total_days, 
                       (trading_count / total_days) * 100)
            
            # 驗證所有返回的日期都是交易日
            for trading_day in trading_days:
                assert calendar.is_trading_day(trading_day)
        
        logger.info("日期範圍內交易日查詢測試通過")
        return True
        
    except Exception as e:
        logger.error("日期範圍內交易日查詢測試失敗: %s", e)
        return False


def test_trading_schedule(calendar):
    """測試交易時間表功能"""
    logger.info("=== 測試交易時間表功能 ===")
    
    try:
        # 測試交易日的時間表
        trading_date = date(2024, 6, 10)  # 假設這是一個交易日
        
        # 如果不是交易日，找下一個交易日
        if not calendar.is_trading_day(trading_date):
            trading_date = calendar.get_next_trading_day(trading_date)
        
        schedule = calendar.get_trading_schedule(trading_date)
        
        if schedule:
            logger.info("交易日 %s 的時間表:", trading_date)
            logger.info("  盤前: %s", schedule.pre_market_start.strftime("%H:%M"))
            logger.info("  上午盤: %s - %s", 
                       schedule.morning_start.strftime("%H:%M"),
                       schedule.morning_end.strftime("%H:%M"))
            logger.info("  下午盤: %s - %s", 
                       schedule.afternoon_start.strftime("%H:%M"),
                       schedule.afternoon_end.strftime("%H:%M"))
            logger.info("  盤後: %s", schedule.post_market_end.strftime("%H:%M"))
            logger.info("  是否半日市: %s", schedule.is_half_day)
            
            # 驗證時間表結構
            assert schedule.morning_start < schedule.morning_end
            assert schedule.afternoon_start < schedule.afternoon_end
            assert schedule.morning_end <= schedule.afternoon_start
        
        # 測試非交易日
        non_trading_date = date(2024, 1, 1)  # 元旦
        non_schedule = calendar.get_trading_schedule(non_trading_date)
        assert non_schedule is None
        
        logger.info("交易時間表測試通過")
        return True
        
    except Exception as e:
        logger.error("交易時間表測試失敗: %s", e)
        return False


def test_monthly_yearly_queries(calendar):
    """測試月度和年度查詢功能"""
    logger.info("=== 測試月度和年度查詢功能 ===")
    
    try:
        # 測試月度查詢
        monthly_days = calendar.get_monthly_trading_days(2024, 6)
        logger.info("2024年6月交易日數量: %d", len(monthly_days))
        
        # 驗證所有日期都在6月且都是交易日
        for day in monthly_days:
            assert day.year == 2024
            assert day.month == 6
            assert calendar.is_trading_day(day)
        
        # 測試年度查詢（只測試部分月份以節省時間）
        yearly_days = calendar.get_yearly_trading_days(2024)
        logger.info("2024年交易日數量: %d", len(yearly_days))
        
        # 驗證年度交易日數量合理（大約250天左右）
        assert 240 <= len(yearly_days) <= 260
        
        # 測試交易日計數
        count = calendar.get_trading_days_count(date(2024, 1, 1), date(2024, 1, 31))
        logger.info("2024年1月交易日計數: %d", count)
        
        logger.info("月度和年度查詢測試通過")
        return True
        
    except Exception as e:
        logger.error("月度和年度查詢測試失敗: %s", e)
        return False


def test_trading_session_detection(calendar):
    """測試交易時段檢測功能"""
    logger.info("=== 測試交易時段檢測功能 ===")
    
    try:
        from src.core.taiwan_trading_calendar import TradingSession
        
        # 測試當前交易時段檢測
        today = date.today()
        
        if calendar.is_trading_day(today):
            info = calendar.get_trading_day_info(today)
            logger.info("今日 (%s) 交易時段: %s", today, info.trading_session.value)
            
            # 測試特定時段檢測
            sessions_to_test = [
                TradingSession.PRE_MARKET,
                TradingSession.MORNING,
                TradingSession.AFTERNOON,
                TradingSession.CLOSED
            ]
            
            for session in sessions_to_test:
                is_current = calendar.is_current_trading_session(session)
                logger.info("當前是否為 %s: %s", session.value, is_current)
        else:
            logger.info("今日 (%s) 非交易日", today)
        
        logger.info("交易時段檢測測試通過")
        return True
        
    except Exception as e:
        logger.error("交易時段檢測測試失敗: %s", e)
        return False


def main():
    """主測試函數"""
    logger.info("開始執行步驟 3.2 台灣證券交易日曆測試")
    
    # 初始化日曆
    init_success, calendar = test_calendar_initialization()
    if not init_success:
        logger.error("日曆初始化失敗，終止測試")
        return False
    
    test_results = []
    
    # 執行各項測試
    test_functions = [
        ("交易日判斷功能", lambda: test_trading_day_detection(calendar)),
        ("交易日詳細資訊", lambda: test_trading_day_info(calendar)),
        ("下一個/上一個交易日查詢", lambda: test_next_previous_trading_day(calendar)),
        ("日期範圍內交易日查詢", lambda: test_trading_days_in_range(calendar)),
        ("交易時間表功能", lambda: test_trading_schedule(calendar)),
        ("月度和年度查詢", lambda: test_monthly_yearly_queries(calendar)),
        ("交易時段檢測", lambda: test_trading_session_detection(calendar))
    ]
    
    for test_name, test_func in test_functions:
        logger.info("\n" + "="*50)
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            logger.error("測試 %s 時發生未預期錯誤: %s", test_name, e)
            test_results.append((test_name, False))
    
    # 輸出測試結果摘要
    logger.info("\n" + "="*50)
    logger.info("測試結果摘要:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "通過" if result else "失敗"
        logger.info("  %s: %s", test_name, status)
        if result:
            passed += 1
    
    logger.info("\n總計: %d/%d 測試通過 (%.1f%%)", passed, total, (passed/total)*100)
    
    if passed == total:
        logger.info("所有測試都通過！步驟 3.2 台灣證券交易日曆實現成功")
        return True
    else:
        logger.warning("部分測試失敗，需要進一步檢查和修正")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
