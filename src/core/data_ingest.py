"""
資料蒐集與預處理模組

此模組負責從各種來源獲取股票資料，包括價格、成交量、財務報表等，
並進行必要的預處理，為後續的特徵計算和策略研究提供基礎資料。

主要功能：
- 從台灣證券交易所和櫃買中心爬取股票資料
- 爬取財務報表資料
- 爬取除權息資料
- 爬取月營收資料
- 資料預處理和清洗
"""

from src.data_sources.twse_crawler import twse_crawler
# from use_perplexity_crawler import init_database, crawl_market_info
import datetime
import pandas as pd
import os
import sqlite3
from tqdm import tqdm
import yfinance as yf
from FinMind.data import DataLoader
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.techindicators import TechIndicators
from alpha_vantage.fundamentaldata import FundamentalData
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import sys

sys.path.append("..")

# 移除自引用的導入語句

# 設定資料存放路徑
DATA_DIR = os.getenv("DATA_DIR", "data")
HISTORY_DIR = os.path.join(DATA_DIR, "history")
ITEMS_DIR = os.path.join(HISTORY_DIR, "items")
TABLES_DIR = os.path.join(HISTORY_DIR, "tables")
FINANCIAL_STATEMENT_DIR = os.path.join(HISTORY_DIR, "financial_statement")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
DB_PATH = os.path.join(DATA_DIR, "market_data.db")

# 確保目錄存在
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(ITEMS_DIR, exist_ok=True)
os.makedirs(TABLES_DIR, exist_ok=True)
os.makedirs(FINANCIAL_STATEMENT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# API 金鑰
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")

# 記錄日期範圍的檔案
date_range_record_file = os.path.join(HISTORY_DIR, "date_range.pickle")


def import_or_install(package):
    """
    檢查並安裝必要的套件

    Args:
        package (str): 套件名稱
    """
    try:
        __import__(package)
    except ImportError:
        print(f"Please install {package} (pip install {package})")


# 確保 lxml 已安裝
import_or_install("lxml")


def load_data(start_date=None, end_date=None, data_types=None):
    """
    載入指定日期範圍和類型的資料

    Args:
        start_date (datetime.date, optional): 開始日期，如果為 None 則使用最早的資料
        end_date (datetime.date, optional): 結束日期，如果為 None 則使用最新的資料
        data_types (list, optional): 資料類型列表，如果為 None 則載入所有類型

    Returns:
        dict: 包含各種資料的字典
    """
    if start_date is None:
        start_date = datetime.date(2010, 1, 1)
    if end_date is None:
        end_date = datetime.date.today()
    if data_types is None:
        data_types = ["price", "bargin", "pe", "monthly_report", "benchmark"]

    result = {}

    if "price" in data_types:
        price_file = os.path.join(TABLES_DIR, "price.pkl")
        if os.path.exists(price_file):
            result["price"] = pd.read_pickle(price_file)
            df = result["price"]
            if isinstance(df.index, pd.MultiIndex) and "date" in df.index.names:
                mask = (
                    df.index.get_level_values("date") >= pd.to_datetime(start_date)
                ) & (df.index.get_level_values("date") <= pd.to_datetime(end_date))
                result["price"] = df[mask]
            elif isinstance(df.index, pd.DatetimeIndex):
                result["price"] = df[
                    (df.index >= pd.to_datetime(start_date))
                    & (df.index <= pd.to_datetime(end_date))
                ]
            else:
                result["price"] = df

    if "bargin" in data_types:
        bargin_file = os.path.join(TABLES_DIR, "bargin_report.pkl")
        if os.path.exists(bargin_file):
            result["bargin"] = pd.read_pickle(bargin_file)
            df = result["bargin"]
            if isinstance(df.index, pd.MultiIndex) and "date" in df.index.names:
                mask = (
                    df.index.get_level_values("date") >= pd.to_datetime(start_date)
                ) & (df.index.get_level_values("date") <= pd.to_datetime(end_date))
                result["bargin"] = df[mask]
            elif isinstance(df.index, pd.DatetimeIndex):
                result["bargin"] = df[
                    (df.index >= pd.to_datetime(start_date))
                    & (df.index <= pd.to_datetime(end_date))
                ]
            else:
                result["bargin"] = df

    if "pe" in data_types:
        pe_file = os.path.join(TABLES_DIR, "pe.pkl")
        if os.path.exists(pe_file):
            result["pe"] = pd.read_pickle(pe_file)
            df = result["pe"]
            if isinstance(df.index, pd.MultiIndex) and "date" in df.index.names:
                mask = (
                    df.index.get_level_values("date") >= pd.to_datetime(start_date)
                ) & (df.index.get_level_values("date") <= pd.to_datetime(end_date))
                result["pe"] = df[mask]
            elif isinstance(df.index, pd.DatetimeIndex):
                result["pe"] = df[
                    (df.index >= pd.to_datetime(start_date))
                    & (df.index <= pd.to_datetime(end_date))
                ]
            else:
                result["pe"] = df

    if "monthly_report" in data_types:
        monthly_report_file = os.path.join(TABLES_DIR, "monthly_report.pkl")
        if os.path.exists(monthly_report_file):
            result["monthly_report"] = pd.read_pickle(monthly_report_file)
            df = result["monthly_report"]
            if isinstance(df.index, pd.MultiIndex) and "date" in df.index.names:
                mask = (
                    df.index.get_level_values("date") >= pd.to_datetime(start_date)
                ) & (df.index.get_level_values("date") <= pd.to_datetime(end_date))
                result["monthly_report"] = df[mask]
            elif isinstance(df.index, pd.DatetimeIndex):
                result["monthly_report"] = df[
                    (df.index >= pd.to_datetime(start_date))
                    & (df.index <= pd.to_datetime(end_date))
                ]
            else:
                result["monthly_report"] = df

    if "benchmark" in data_types:
        benchmark_file = os.path.join(TABLES_DIR, "benchmark.pkl")
        if os.path.exists(benchmark_file):
            result["benchmark"] = pd.read_pickle(benchmark_file)
            df = result["benchmark"]
            if isinstance(df.index, pd.MultiIndex) and "date" in df.index.names:
                mask = (
                    df.index.get_level_values("date") >= pd.to_datetime(start_date)
                ) & (df.index.get_level_values("date") <= pd.to_datetime(end_date))
                result["benchmark"] = df[mask]
            elif isinstance(df.index, pd.DatetimeIndex):
                result["benchmark"] = df[
                    (df.index >= pd.to_datetime(start_date))
                    & (df.index <= pd.to_datetime(end_date))
                ]
            else:
                result["benchmark"] = df

    return result


def update_data(start_date=None, end_date=None, data_types=None):
    """
    更新指定日期範圍和類型的資料

    Args:
        start_date (datetime.date, optional): 開始日期，如果為 None 則使用最早的資料
        end_date (datetime.date, optional): 結束日期，如果為 None 則使用最新的資料
        data_types (list, optional): 資料類型列表，如果為 None 則更新所有類型

    Returns:
        dict: 包含各種資料的字典
    """
    if start_date is None:
        start_date = datetime.date(2010, 1, 1)
    if end_date is None:
        end_date = datetime.date.today()
    if data_types is None:
        data_types = ["price", "bargin", "pe", "monthly_report", "benchmark"]

    # 生成日期範圍
    date_range = pd.date_range(start=start_date, end=end_date, freq="B")

    # 更新各種資料
    for date in tqdm(date_range, desc="更新資料"):
        date = date.date()

        if "price" in data_types:
            twe_price = twse_crawler.price_twe(date)
            otc_price = twse_crawler.price_otc(date)
            if not twe_price.empty or not otc_price.empty:
                price = pd.concat([twe_price, otc_price])
                price_file = os.path.join(TABLES_DIR, "price.pkl")
                if os.path.exists(price_file):
                    old_price = pd.read_pickle(price_file)
                    price = pd.concat([old_price, price])
                    price = price[~price.index.duplicated(keep="last")]
                price.to_pickle(price_file)

        if "bargin" in data_types:
            twe_bargin = twse_crawler.bargin_twe(date)
            otc_bargin = twse_crawler.bargin_otc(date)
            if not twe_bargin.empty or not otc_bargin.empty:
                bargin = pd.concat([twe_bargin, otc_bargin])
                bargin_file = os.path.join(TABLES_DIR, "bargin_report.pkl")
                if os.path.exists(bargin_file):
                    old_bargin = pd.read_pickle(bargin_file)
                    bargin = pd.concat([old_bargin, bargin])
                    bargin = bargin[~bargin.index.duplicated(keep="last")]
                bargin.to_pickle(bargin_file)

        if "pe" in data_types:
            twe_pe = twse_crawler.pe_twe(date)
            otc_pe = twse_crawler.pe_otc(date)
            # 防呆：檢查是否有 'stock_id' 欄位
            if (not twe_pe.empty and "stock_id" in twe_pe.columns) or (
                not otc_pe.empty and "stock_id" in otc_pe.columns
            ):
                # 只合併有 stock_id 欄位的 DataFrame
                pe_list = []
                if not twe_pe.empty and "stock_id" in twe_pe.columns:
                    pe_list.append(twe_pe)
                if not otc_pe.empty and "stock_id" in otc_pe.columns:
                    pe_list.append(otc_pe)
                if pe_list:
                    pe = pd.concat(pe_list)
                pe_file = os.path.join(TABLES_DIR, "pe.pkl")
                if os.path.exists(pe_file):
                    old_pe = pd.read_pickle(pe_file)
                    pe = pd.concat([old_pe, pe])
                    pe = pe[~pe.index.duplicated(keep="last")]
                pe.to_pickle(pe_file)
            else:
                print(
                    f"警告: {date} pe 資料缺少 stock_id 欄位，twe_pe columns: {twe_pe.columns}, otc_pe columns: {otc_pe.columns}"
                )

        if "monthly_report" in data_types and date.day <= 10:
            monthly_report = twse_crawler.month_revenue(None, date)
            if not monthly_report.empty:
                monthly_report_file = os.path.join(TABLES_DIR, "monthly_report.pkl")
                if os.path.exists(monthly_report_file):
                    old_monthly_report = pd.read_pickle(monthly_report_file)
                    monthly_report = pd.concat([old_monthly_report, monthly_report])
                    monthly_report = monthly_report[
                        ~monthly_report.index.duplicated(keep="last")
                    ]
                monthly_report.to_pickle(monthly_report_file)

        if "benchmark" in data_types:
            benchmark = twse_crawler.crawl_benchmark(date)
            if not benchmark.empty:
                benchmark_file = os.path.join(TABLES_DIR, "benchmark.pkl")
                if os.path.exists(benchmark_file):
                    old_benchmark = pd.read_pickle(benchmark_file)
                    benchmark = pd.concat([old_benchmark, benchmark])
                    benchmark = benchmark[~benchmark.index.duplicated(keep="last")]
                benchmark.to_pickle(benchmark_file)

    # 返回更新後的資料
    return load_data(start_date, end_date, data_types)


# FinMind API 相關函數
def fetch_finmind_data(data_type, stock_id=None, start_date=None, end_date=None):
    """
    使用 FinMind API 獲取資料

    Args:
        data_type (str): 資料類型，如 'TaiwanStockPrice', 'TaiwanStockFinancialStatement'
        stock_id (str, optional): 股票代號，如果為 None 則獲取所有股票
        start_date (str, optional): 開始日期，格式為 'YYYY-MM-DD'
        end_date (str, optional): 結束日期，格式為 'YYYY-MM-DD'

    Returns:
        pandas.DataFrame: 獲取的資料
    """
    try:
        # 初始化 FinMind API
        api = DataLoader()

        # 設定參數
        params = {}
        if stock_id:
            params["stock_id"] = stock_id
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        # 獲取資料
        if data_type == "TaiwanStockPrice":
            df = api.taiwan_stock_daily(**params)
        elif data_type == "TaiwanStockFinancialStatement":
            df = api.taiwan_stock_financial_statement(**params)
        elif data_type == "TaiwanStockBalanceSheet":
            df = api.taiwan_stock_balance_sheet(**params)
        elif data_type == "TaiwanStockCashFlowsStatement":
            df = api.taiwan_stock_cash_flows_statement(**params)
        elif data_type == "TaiwanStockNews":
            df = api.taiwan_stock_news(**params)
        else:
            df = pd.DataFrame()

        # 快取資料
        if not df.empty:
            cache_file = os.path.join(
                CACHE_DIR, f"finmind_{data_type}_{start_date}_{end_date}.csv"
            )
            df.to_csv(cache_file, index=False)

        return df
    except Exception as e:
        print(f"獲取 FinMind 資料時發生錯誤: {e}")
        return pd.DataFrame()


# Yahoo Finance API 相關函數
def fetch_yahoo_finance_data(stock_ids, start_date=None, end_date=None):
    """
    使用 Yahoo Finance API 獲取資料

    Args:
        stock_ids (list): 股票代號列表，如 ['2330.TW', '2317.TW']
        start_date (str, optional): 開始日期，格式為 'YYYY-MM-DD'
        end_date (str, optional): 結束日期，格式為 'YYYY-MM-DD'

    Returns:
        dict: 包含各股票資料的字典
    """
    try:
        result = {}

        for stock_id in stock_ids:
            # 獲取股票資料
            stock = yf.Ticker(stock_id)

            # 獲取歷史價格
            hist = stock.history(start=start_date, end=end_date)

            # 獲取基本面資料
            info = stock.info

            # 獲取財務報表
            financials = stock.financials
            balance_sheet = stock.balance_sheet
            cash_flow = stock.cashflow

            # 合併資料
            result[stock_id] = {
                "history": hist,
                "info": info,
                "financials": financials,
                "balance_sheet": balance_sheet,
                "cash_flow": cash_flow,
            }

            # 快取資料
            cache_dir = os.path.join(CACHE_DIR, f"yahoo_{stock_id}")
            os.makedirs(cache_dir, exist_ok=True)

            hist.to_csv(os.path.join(cache_dir, "history.csv"))
            pd.DataFrame([info]).to_csv(os.path.join(cache_dir, "info.csv"))
            financials.to_csv(os.path.join(cache_dir, "financials.csv"))
            balance_sheet.to_csv(os.path.join(cache_dir, "balance_sheet.csv"))
            cash_flow.to_csv(os.path.join(cache_dir, "cash_flow.csv"))

        return result
    except Exception as e:
        print(f"獲取 Yahoo Finance 資料時發生錯誤: {e}")
        return {}


# Alpha Vantage API 相關函數
def fetch_alpha_vantage_data(function, symbol, **kwargs):
    """
    使用 Alpha Vantage API 獲取資料

    Args:
        function (str): API 函數，如 'TIME_SERIES_DAILY', 'SMA', 'OVERVIEW'
        symbol (str): 股票代號，如 '2330.TW'
        **kwargs: 其他參數

    Returns:
        pandas.DataFrame: 獲取的資料
    """
    try:
        if not ALPHA_VANTAGE_API_KEY:
            print("未設定 Alpha Vantage API 金鑰")
            return pd.DataFrame()

        # 根據函數類型選擇適當的 API
        if function in [
            "TIME_SERIES_DAILY",
            "TIME_SERIES_WEEKLY",
            "TIME_SERIES_MONTHLY",
        ]:
            ts = TimeSeries(key=ALPHA_VANTAGE_API_KEY, output_format="pandas")
            data, meta_data = ts.get_daily(symbol=symbol, outputsize="full")
        elif function in ["SMA", "EMA", "RSI", "MACD"]:
            ti = TechIndicators(key=ALPHA_VANTAGE_API_KEY, output_format="pandas")
            if function == "SMA":
                data, meta_data = ti.get_sma(symbol=symbol, **kwargs)
            elif function == "EMA":
                data, meta_data = ti.get_ema(symbol=symbol, **kwargs)
            elif function == "RSI":
                data, meta_data = ti.get_rsi(symbol=symbol, **kwargs)
            elif function == "MACD":
                data, meta_data = ti.get_macd(symbol=symbol, **kwargs)
        elif function in ["OVERVIEW", "INCOME_STATEMENT", "BALANCE_SHEET", "CASH_FLOW"]:
            fd = FundamentalData(key=ALPHA_VANTAGE_API_KEY, output_format="pandas")
            if function == "OVERVIEW":
                data, meta_data = fd.get_company_overview(symbol=symbol)
            elif function == "INCOME_STATEMENT":
                data, meta_data = fd.get_income_statement_annual(symbol=symbol)
            elif function == "BALANCE_SHEET":
                data, meta_data = fd.get_balance_sheet_annual(symbol=symbol)
            elif function == "CASH_FLOW":
                data, meta_data = fd.get_cash_flow_annual(symbol=symbol)
        else:
            return pd.DataFrame()

        # 快取資料
        cache_file = os.path.join(CACHE_DIR, f"alpha_vantage_{function}_{symbol}.csv")
        data.to_csv(cache_file)

        return data
    except Exception as e:
        print(f"獲取 Alpha Vantage 資料時發生錯誤: {e}")
        return pd.DataFrame()


# 資料清洗函數
def clean_data(df, method="ffill"):
    """
    清洗資料，包括缺值填補、日期格式統一、欄位標準化

    Args:
        df (pandas.DataFrame): 要清洗的資料
        method (str): 缺值填補方法，'ffill' 為前向填補，'bfill' 為後向填補

    Returns:
        pandas.DataFrame: 清洗後的資料
    """
    if df.empty:
        return df

    # 複製資料，避免修改原始資料
    df = df.copy()

    # 處理日期欄位
    date_columns = [
        col for col in df.columns if "date" in col.lower() or "time" in col.lower()
    ]
    for col in date_columns:
        if df[col].dtype == "object":
            try:
                df[col] = pd.to_datetime(df[col])
            except BaseException:
                pass

    # 處理缺值
    if method == "ffill":
        df = df.fillna(method="ffill")
    elif method == "bfill":
        df = df.fillna(method="bfill")

    # 標準化欄位名稱
    df.columns = df.columns.str.lower().str.replace(" ", "_")

    return df


# 資料庫相關函數
def save_to_database(df, table_name):
    """
    將資料儲存到 SQLite 資料庫

    Args:
        df (pandas.DataFrame): 要儲存的資料
        table_name (str): 資料表名稱

    Returns:
        bool: 是否成功儲存
    """
    # 若 table_name 為 news，自動轉為 market_info
    if table_name == "news":
        table_name = "market_info"
        # 補齊必要欄位
        if "sentiment" not in df.columns:
            df["sentiment"] = 0.0
        if "data_source" not in df.columns:
            df["data_source"] = "perplexity"
        if "query" not in df.columns:
            df["query"] = ""
        if "url" not in df.columns:
            df["url"] = ""
        if "title" not in df.columns:
            df["title"] = ""
        if "crawl_date" not in df.columns:
            df["crawl_date"] = datetime.datetime.now().strftime("%Y-%m-%d")
        if "source" not in df.columns:
            df["source"] = ""
    try:
        conn = sqlite3.connect(DB_PATH)
        df.to_sql(table_name, conn, if_exists="append", index=False)
        conn.close()
        return True
    except Exception as e:
        print(f"儲存資料到資料庫時發生錯誤: {e}")
        return False


# 定時更新函數
def schedule_fetch(
    stock_ids=None, interval="daily", start_time="08:00", end_time="16:00"
):
    """
    使用 APScheduler 實現每日定時更新，並將資料快取至 CSV/SQLite

    Args:
        stock_ids (list, optional): 股票代號列表，如果為 None 則更新所有股票
        interval (str): 更新間隔，'daily', 'hourly', 'minute'
        start_time (str): 開始時間，格式為 'HH:MM'
        end_time (str): 結束時間，格式為 'HH:MM'

    Returns:
        apscheduler.schedulers.background.BackgroundScheduler: 排程器
    """
    # 初始化排程器
    scheduler = BackgroundScheduler()

    # 定義更新函數
    def update_job():
        try:
            # 更新日期
            today = datetime.datetime.now().date()
            yesterday = today - datetime.timedelta(days=1)

            # 更新台股資料
            print(f"更新台股資料: {today}")
            update_data(yesterday, today)

            # 更新 FinMind 資料
            if stock_ids:
                for stock_id in stock_ids:
                    print(f"更新 FinMind 資料: {stock_id}")
                    df = fetch_finmind_data(
                        "TaiwanStockPrice",
                        stock_id,
                        yesterday.strftime("%Y-%m-%d"),
                        today.strftime("%Y-%m-%d"),
                    )
                    if not df.empty:
                        df = clean_data(df)
                        save_to_database(df, "stock_price")

            # 更新 Yahoo Finance 資料
            if stock_ids:
                print(f"更新 Yahoo Finance 資料")
                yahoo_data = fetch_yahoo_finance_data(
                    [f"{s}.TW" for s in stock_ids],
                    yesterday.strftime("%Y-%m-%d"),
                    today.strftime("%Y-%m-%d"),
                )

                for stock_id, data in yahoo_data.items():
                    history = data["history"]
                    if not history.empty:
                        history = clean_data(history)
                        history["stock_id"] = stock_id.replace(".TW", "")
                        history = history.reset_index()
                        save_to_database(history, "stock_price")

            # 更新 Alpha Vantage 資料
            if stock_ids and ALPHA_VANTAGE_API_KEY:
                for stock_id in stock_ids:
                    print(f"更新 Alpha Vantage 資料: {stock_id}")
                    # 獲取技術指標
                    for indicator in ["SMA", "RSI", "MACD"]:
                        df = fetch_alpha_vantage_data(
                            indicator, f"{stock_id}.TW", time_period=14
                        )
                        if not df.empty:
                            df = clean_data(df)
                            df["stock_id"] = stock_id
                            df["indicator_name"] = indicator
                            df = df.reset_index()
                            save_to_database(df, "technical_indicator")

                    # 獲取基本面資料
                    df = fetch_alpha_vantage_data("OVERVIEW", f"{stock_id}.TW")
                    if not df.empty:
                        df = clean_data(df)
                        df["stock_id"] = stock_id
                        save_to_database(df, "financial_statement")

            print("資料更新完成")
        except Exception as e:
            print(f"更新資料時發生錯誤: {e}")

    # 設定排程
    if interval == "daily":
        scheduler.add_job(
            update_job,
            CronTrigger(hour=start_time.split(":")[0], minute=start_time.split(":")[1]),
        )
    elif interval == "hourly":
        scheduler.add_job(
            update_job,
            "interval",
            hours=1,
            start_date=f"{datetime.datetime.now().date()} {start_time}",
            end_date=f"{datetime.datetime.now().date()} {end_time}",
        )
    elif interval == "minute":
        scheduler.add_job(
            update_job,
            "interval",
            minutes=1,
            start_date=f"{datetime.datetime.now().date()} {start_time}",
            end_date=f"{datetime.datetime.now().date()} {end_time}",
        )

    # 啟動排程器
    scheduler.start()

    return scheduler


# 儲存資料框到 CSV 檔案
def save_dataframe(df, name):
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
    print(f"已儲存資料至 {file_path}")

    return file_path
