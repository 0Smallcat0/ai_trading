#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
台灣證券交易所和櫃買中心爬蟲執行程式

此程式用於執行台灣證券交易所和櫃買中心的各種爬蟲功能，包括：
- 台股指數（大盤指數）
- 上市/上櫃個股每日行情
- 法人買賣超
- 本益比、殖利率、股價淨值比
- 月營收
- 除權息、減資等公司行為
- 股本資料
"""

import argparse
import logging
import os
import sys
import traceback
import warnings
from logging.handlers import RotatingFileHandler


def progress_bar_dummy(x):
"""
progress_bar_dummy

Args:
    x: 
"""
    return x


try:
    from tqdm import tqdm as progress_bar
except ImportError:
    progress_bar = progress_bar_dummy
    print("未安裝 tqdm，進度條功能將停用")


# 集中管理 log 訊息，方便多語系擴充
LOG_MSGS = {
    "import_fail": "無法導入爬蟲模組: {error}",
    "import_path": "請確保 data_sources/twse_crawler.py 檔案存在且可訪問",
    "start": "開始執行台灣證券交易所和櫃買中心爬蟲...",
    "finish": "爬蟲執行完成！",
    "all_saved": "所有資料已儲存至 ./data 目錄",
    "user_interrupt": "使用者中斷執行",
    "unhandled": "未處理的異常: {error}",
}

# 設定日誌
logger = logging.getLogger("run_twse_crawler")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler = RotatingFileHandler(
    "run_twse_crawler.log", maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
file_handler.setFormatter(formatter)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

try:
    from data_sources.twse_crawler import twse_crawler
except ImportError as e:
    logger.error(LOG_MSGS["import_fail"].format(error=e))
    logger.error(LOG_MSGS["import_path"])
    sys.exit(1)

# 忽略警告
warnings.filterwarnings("ignore")

# 設定資料存放路徑
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)


def save_to_csv(df, name):
    """
    將資料框儲存為 CSV 檔案

    Args:
        df (pandas.DataFrame): 要儲存的資料框
        name (str): 檔案名稱（不含副檔名）

    Returns:
        str: 儲存的檔案路徑
    """
    # 確保 data 目錄存在
    data_dir = os.path.join(os.getcwd(), "data")
    os.makedirs(data_dir, exist_ok=True)

    # 設定檔案路徑
    file_path = os.path.join(data_dir, f"{name}.csv")

    # 儲存資料框
    df.to_csv(file_path)
    logger.info(f"已儲存資料至 {file_path}")

    return file_path


def save_to_pickle(df, name):
    """
    將資料框儲存為 pickle 檔案

    Args:
        df (pandas.DataFrame): 要儲存的資料框
        name (str): 檔案名稱（不含副檔名）

    Returns:
        str: 儲存的檔案路徑
    """
    # 確保 data 目錄存在
    data_dir = os.path.join(os.getcwd(), "data")
    os.makedirs(data_dir, exist_ok=True)

    # 設定檔案路徑
    file_path = os.path.join(data_dir, f"{name}.pkl")

    # 儲存資料框
    df.to_pickle(file_path)
    logger.info(f"已儲存資料至 {file_path}")

    return file_path


def crawl_daily_data(date):
    """
    爬取指定日期的每日資料

    Args:
        date (datetime.date): 日期

    Returns:
        dict: 包含各種資料的字典
    """
    result = {}
    date_str = date.strftime("%Y-%m-%d")

    # 1. 爬取大盤指數
    try:
        logger.info(f"爬取大盤指數: {date_str}")
        benchmark_df = twse_crawler.crawl_benchmark(date)
        if not benchmark_df.empty:
            save_to_csv(benchmark_df, f"benchmark_{date_str}")
            save_to_pickle(benchmark_df, f"benchmark_{date_str}")
            result["benchmark"] = benchmark_df
            logger.info(f"大盤指數筆數: {len(benchmark_df)}")
        else:
            logger.warning(f"無大盤指數資料: {date_str}")
    except Exception as e:
        logger.error(f"爬取大盤指數時發生錯誤: {e}")
        logger.error(traceback.format_exc())

    # 2. 爬取上市股價資料
    try:
        logger.info(f"爬取上市股價資料: {date_str}")
        price_twe_df = twse_crawler.price_twe(date)
        if not price_twe_df.empty:
            save_to_csv(price_twe_df, f"price_twe_{date_str}")
            save_to_pickle(price_twe_df, f"price_twe_{date_str}")
            result["price_twe"] = price_twe_df
            logger.info(f"上市股價資料筆數: {len(price_twe_df)}")
        else:
            logger.warning(f"無上市股價資料: {date_str}")
    except Exception as e:
        logger.error(f"爬取上市股價資料時發生錯誤: {e}")
        logger.error(traceback.format_exc())

    # 3. 爬取上櫃股價資料
    try:
        logger.info(f"爬取上櫃股價資料: {date_str}")
        price_otc_df = twse_crawler.price_otc(date)
        if not price_otc_df.empty:
            save_to_csv(price_otc_df, f"price_otc_{date_str}")
            save_to_pickle(price_otc_df, f"price_otc_{date_str}")
            result["price_otc"] = price_otc_df
            logger.info(f"上櫃股價資料筆數: {len(price_otc_df)}")
        else:
            logger.warning(f"無上櫃股價資料: {date_str}")
    except Exception as e:
        logger.error(f"爬取上櫃股價資料時發生錯誤: {e}")
        logger.error(traceback.format_exc())

    # 4. 爬取上市法人買賣超資料
    try:
        logger.info(f"爬取上市法人買賣超資料: {date_str}")
        bargin_twe_df = twse_crawler.bargin_twe(date)
        if not bargin_twe_df.empty:
            save_to_csv(bargin_twe_df, f"bargin_twe_{date_str}")
            save_to_pickle(bargin_twe_df, f"bargin_twe_{date_str}")
            result["bargin_twe"] = bargin_twe_df
            logger.info(f"上市法人買賣超資料筆數: {len(bargin_twe_df)}")
        else:
            logger.warning(f"無上市法人買賣超資料: {date_str}")
    except Exception as e:
        logger.error(f"爬取上市法人買賣超資料時發生錯誤: {e}")
        logger.error(traceback.format_exc())

    # 5. 爬取上櫃法人買賣超資料
    try:
        logger.info(f"爬取上櫃法人買賣超資料: {date_str}")
        bargin_otc_df = twse_crawler.bargin_otc(date)
        if not bargin_otc_df.empty:
            save_to_csv(bargin_otc_df, f"bargin_otc_{date_str}")
            save_to_pickle(bargin_otc_df, f"bargin_otc_{date_str}")
            result["bargin_otc"] = bargin_otc_df
            logger.info(f"上櫃法人買賣超資料筆數: {len(bargin_otc_df)}")
        else:
            logger.warning(f"無上櫃法人買賣超資料: {date_str}")
    except Exception as e:
        logger.error(f"爬取上櫃法人買賣超資料時發生錯誤: {e}")
        logger.error(traceback.format_exc())

    # 6. 爬取上市本益比資料
    try:
        logger.info(f"爬取上市本益比資料: {date_str}")
        pe_twe_df = twse_crawler.pe_twe(date)
        if not pe_twe_df.empty:
            save_to_csv(pe_twe_df, f"pe_twe_{date_str}")
            save_to_pickle(pe_twe_df, f"pe_twe_{date_str}")
            result["pe_twe"] = pe_twe_df
            logger.info(f"上市本益比資料筆數: {len(pe_twe_df)}")
        else:
            logger.warning(f"無上市本益比資料: {date_str}")
    except Exception as e:
        logger.error(f"爬取上市本益比資料時發生錯誤: {e}")
        logger.error(traceback.format_exc())

    # 7. 爬取上櫃本益比資料
    try:
        logger.info(f"爬取上櫃本益比資料: {date_str}")
        pe_otc_df = twse_crawler.pe_otc(date)
        if not pe_otc_df.empty:
            save_to_csv(pe_otc_df, f"pe_otc_{date_str}")
            save_to_pickle(pe_otc_df, f"pe_otc_{date_str}")
            result["pe_otc"] = pe_otc_df
            logger.info(f"上櫃本益比資料筆數: {len(pe_otc_df)}")
        else:
            logger.warning(f"無上櫃本益比資料: {date_str}")
    except Exception as e:
        logger.error(f"爬取上櫃本益比資料時發生錯誤: {e}")
        logger.error(traceback.format_exc())

    return result


def crawl_monthly_data(year, month):
    """
    爬取指定年月的月營收資料

    Args:
        year (int): 年份
        month (int): 月份

    Returns:
        dict: 包含各種資料的字典
    """
    result = {}
    date = datetime.date(year, month, 1)

    # 爬取月營收資料
    try:
        logger.info(f"爬取月營收資料: {year}/{month}")
        monthly_revenue_df = twse_crawler.month_revenue(None, date)
        if not monthly_revenue_df.empty:
            save_to_csv(monthly_revenue_df, f"monthly_revenue_{year}_{month:02d}")
            save_to_pickle(monthly_revenue_df, f"monthly_revenue_{year}_{month:02d}")
            result["monthly_revenue"] = monthly_revenue_df
            logger.info(f"月營收資料筆數: {len(monthly_revenue_df)}")
        else:
            logger.warning(f"無月營收資料: {year}/{month}")
    except Exception as e:
        logger.error(f"爬取月營收資料時發生錯誤: {e}")
        logger.error(traceback.format_exc())

    return result


def crawl_quarterly_data(year, season):
    """
    爬取指定年季的財務報表資料

    Args:
        year (int): 年份
        season (int): 季度 (1-4)

    Returns:
        dict: 包含各種資料的字典
    """
    result = {}

    # 爬取財務報表資料
    try:
        logger.info(f"爬取財務報表資料: {year}Q{season}")
        finance_statement_df = twse_crawler.crawl_finance_statement(year, season)
        if not finance_statement_df.empty:
            save_to_csv(finance_statement_df, f"finance_statement_{year}_Q{season}")
            save_to_pickle(finance_statement_df, f"finance_statement_{year}_Q{season}")
            result["finance_statement"] = finance_statement_df
            logger.info(f"財務報表資料筆數: {len(finance_statement_df)}")
        else:
            logger.warning(f"無財務報表資料: {year}Q{season}")
    except Exception as e:
        logger.error(f"爬取財務報表資料時發生錯誤: {e}")
        logger.error(traceback.format_exc())

    return result


def crawl_yearly_data(year):
    """
    爬取指定年度的資料

    Args:
        year (int): 年份

    Returns:
        dict: 包含各種資料的字典
    """
    result = {}

    # 1. 爬取除權息資料
    try:
        logger.info(f"爬取上市除權息資料: {year}")
        twse_divide_ratio_df = twse_crawler.crawl_twse_divide_ratio()
        if not twse_divide_ratio_df.empty:
            # 過濾指定年度的資料
            twse_divide_ratio_df = twse_divide_ratio_df[
                twse_divide_ratio_df.index.get_level_values("date").year == year
            ]
            if not twse_divide_ratio_df.empty:
                save_to_csv(twse_divide_ratio_df, f"twse_divide_ratio_{year}")
                save_to_pickle(twse_divide_ratio_df, f"twse_divide_ratio_{year}")
                result["twse_divide_ratio"] = twse_divide_ratio_df
                logger.info(f"上市除權息資料筆數: {len(twse_divide_ratio_df)}")
            else:
                logger.warning(f"無上市除權息資料: {year}")
        else:
            logger.warning(f"無上市除權息資料: {year}")
    except Exception as e:
        logger.error(f"爬取上市除權息資料時發生錯誤: {e}")
        logger.error(traceback.format_exc())

    # 2. 爬取上市減資資料
    try:
        logger.info(f"爬取上市減資資料: {year}")
        twse_cap_reduction_df = twse_crawler.crawl_twse_cap_reduction()
        if not twse_cap_reduction_df.empty:
            # 過濾指定年度的資料
            twse_cap_reduction_df = twse_cap_reduction_df[
                twse_cap_reduction_df.index.get_level_values("date").year == year
            ]
            if not twse_cap_reduction_df.empty:
                save_to_csv(twse_cap_reduction_df, f"twse_cap_reduction_{year}")
                save_to_pickle(twse_cap_reduction_df, f"twse_cap_reduction_{year}")
                result["twse_cap_reduction"] = twse_cap_reduction_df
                logger.info(f"上市減資資料筆數: {len(twse_cap_reduction_df)}")
            else:
                logger.warning(f"無上市減資資料: {year}")
        else:
            logger.warning(f"無上市減資資料: {year}")
    except Exception as e:
        logger.error(f"爬取上市減資資料時發生錯誤: {e}")
        logger.error(traceback.format_exc())

    # 3. 爬取上櫃除權息資料
    try:
        logger.info(f"爬取上櫃除權息資料: {year}")
        otc_divide_ratio_df = twse_crawler.crawl_otc_divide_ratio()
        if not otc_divide_ratio_df.empty:
            # 過濾指定年度的資料
            otc_divide_ratio_df = otc_divide_ratio_df[
                otc_divide_ratio_df.index.get_level_values("date").year == year
            ]
            if not otc_divide_ratio_df.empty:
                save_to_csv(otc_divide_ratio_df, f"otc_divide_ratio_{year}")
                save_to_pickle(otc_divide_ratio_df, f"otc_divide_ratio_{year}")
                result["otc_divide_ratio"] = otc_divide_ratio_df
                logger.info(f"上櫃除權息資料筆數: {len(otc_divide_ratio_df)}")
            else:
                logger.warning(f"無上櫃除權息資料: {year}")
        else:
            logger.warning(f"無上櫃除權息資料: {year}")
    except Exception as e:
        logger.error(f"爬取上櫃除權息資料時發生錯誤: {e}")
        logger.error(traceback.format_exc())

    # 4. 爬取上櫃減資資料
    try:
        logger.info(f"爬取上櫃減資資料: {year}")
        otc_cap_reduction_df = twse_crawler.crawl_otc_cap_reduction()
        if not otc_cap_reduction_df.empty:
            # 過濾指定年度的資料
            otc_cap_reduction_df = otc_cap_reduction_df[
                otc_cap_reduction_df.index.get_level_values("date").year == year
            ]
            if not otc_cap_reduction_df.empty:
                save_to_csv(otc_cap_reduction_df, f"otc_cap_reduction_{year}")
                save_to_pickle(otc_cap_reduction_df, f"otc_cap_reduction_{year}")
                result["otc_cap_reduction"] = otc_cap_reduction_df
                logger.info(f"上櫃減資資料筆數: {len(otc_cap_reduction_df)}")
            else:
                logger.warning(f"無上櫃減資資料: {year}")
        else:
            logger.warning(f"無上櫃減資資料: {year}")
    except Exception as e:
        logger.error(f"爬取上櫃減資資料時發生錯誤: {e}")
        logger.error(traceback.format_exc())

    # 5. 爬取股本資料
    try:
        logger.info(f"爬取股本資料: {year}")
        capital_df = twse_crawler.crawl_capital()
        if not capital_df.empty:
            # 過濾指定年度的資料
            capital_df = capital_df[
                capital_df.index.get_level_values("date").year == year
            ]
            if not capital_df.empty:
                save_to_csv(capital_df, f"capital_{year}")
                save_to_pickle(capital_df, f"capital_{year}")
                result["capital"] = capital_df
                logger.info(f"股本資料筆數: {len(capital_df)}")
            else:
                logger.warning(f"無股本資料: {year}")
        else:
            logger.warning(f"無股本資料: {year}")
    except Exception as e:
        logger.error(f"爬取股本資料時發生錯誤: {e}")
        logger.error(traceback.format_exc())

    return result


def main():
    """主程式：執行各種爬蟲並儲存資料"""
    parser = argparse.ArgumentParser(description="台灣證券交易所和櫃買中心爬蟲執行程式")
    parser.add_argument("--daily", action="store_true", help="爬取每日資料")
    parser.add_argument("--monthly", action="store_true", help="爬取月營收資料")
    parser.add_argument("--quarterly", action="store_true", help="爬取財務報表資料")
    parser.add_argument("--yearly", action="store_true", help="爬取年度資料")
    parser.add_argument("--date", type=str, help="指定日期 (YYYY-MM-DD)")
    parser.add_argument("--year", type=int, help="指定年份")
    parser.add_argument("--month", type=int, help="指定月份")
    parser.add_argument("--season", type=int, help="指定季度 (1-4)")
    parser.add_argument("--days", type=int, default=1, help="爬取最近幾天的資料")

    args = parser.parse_args()

    logger.info(LOG_MSGS["start"])

    # 取得今日日期
    today = datetime.datetime.today().date()

    # 爬取每日資料
    if args.daily:
        if args.date:
            date = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
            logger.info(f"爬取指定日期的每日資料: {date}")
            crawl_daily_data(date)
        elif args.days > 1:
            logger.info(f"爬取最近 {args.days} 天的每日資料")
            for i in range(args.days):
                date = today - datetime.timedelta(days=i)
                logger.info(f"爬取日期: {date}")
                crawl_daily_data(date)
        else:
            logger.info(f"爬取今日的每日資料: {today}")
            crawl_daily_data(today)

    # 爬取月營收資料
    if args.monthly:
        if args.year and args.month:
            logger.info(f"爬取指定年月的月營收資料: {args.year}/{args.month}")
            crawl_monthly_data(args.year, args.month)
        else:
            logger.info(f"爬取本月的月營收資料: {today.year}/{today.month}")
            crawl_monthly_data(today.year, today.month)

    # 爬取財務報表資料
    if args.quarterly:
        if args.year and args.season:
            logger.info(f"爬取指定年季的財務報表資料: {args.year}Q{args.season}")
            crawl_quarterly_data(args.year, args.season)
        else:
            # 計算當前季度
            current_season = (today.month - 1) // 3 + 1
            logger.info(f"爬取本季的財務報表資料: {today.year}Q{current_season}")
            crawl_quarterly_data(today.year, current_season)

    # 爬取年度資料
    if args.yearly:
        if args.year:
            logger.info(f"爬取指定年度的資料: {args.year}")
            crawl_yearly_data(args.year)
        else:
            logger.info(f"爬取本年度的資料: {today.year}")
            crawl_yearly_data(today.year)

    # 如果沒有指定任何參數，則爬取今日的每日資料
    if not (args.daily or args.monthly or args.quarterly or args.yearly):
        logger.info(f"爬取今日的每日資料: {today}")
        crawl_daily_data(today)

    logger.info(LOG_MSGS["finish"])
    logger.info(LOG_MSGS["all_saved"])

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info(LOG_MSGS["user_interrupt"])
        sys.exit(1)
    except Exception as e:
        logger.error(LOG_MSGS["unhandled"].format(error=e))
        logger.error(traceback.format_exc())
        sys.exit(1)
