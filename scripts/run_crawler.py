#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
每日股市資料爬蟲執行程式

⚠️ 重要通知：此檔案中的爬蟲函數已棄用 ⚠️

遷移指南：請使用新的模組化架構
- 舊: crawl_price_twe(date)
- 新: from src.data_sources import TWSECrawler; TWSECrawler().price_twe(date)
- 舊: crawl_price_otc(date)
- 新: from src.data_sources import TWSECrawler; TWSECrawler().price_otc(date)

新架構優勢：
- 更好的錯誤處理和重試機制
- 統一的配置管理
- 完整的測試覆蓋
- 模組化設計，易於維護

此程式用於手動執行每日股市資料爬蟲，包括：
- 上市股價資料 (TWSE) [已棄用，請使用新API]
- 上櫃股價資料 (OTC) [已棄用，請使用新API]
- 財務報表資料
- 月營收資料

所有資料將儲存在 ./data 目錄下
"""

import logging
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    import pandas as pd
except ImportError:
    print("請先安裝 pandas 套件：pip install pandas")
    raise
try:
    import numpy as np
except ImportError:
    print("請先安裝 numpy 套件：pip install numpy")
    raise
try:
    import requests
except ImportError:
    print("請先安裝 requests 套件：pip install requests")
    raise
import datetime
import os
import time
import warnings
from io import StringIO

# 忽略警告
warnings.filterwarnings("ignore")

# 設定資料存放路徑
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# 全局 session 變數
ses = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("run_crawler.log"), logging.StreamHandler()],
)
logger = logging.getLogger("run_crawler")


def generate_random_header():
    """產生隨機 Header 避免被擋"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    ]
    return {"User-Agent": user_agents[np.random.randint(0, len(user_agents))]}


def find_best_session():
    """嘗試建立一個可用的 session，用於爬取資料"""
    global ses
    for i in range(5):
        try:
            headers = generate_random_header()
            ses = requests.Session()
            ses.get("https://www.twse.com.tw/zh/", headers=headers, timeout=10)
            ses.headers.update(headers)
            return ses
        except (requests.ConnectionError, requests.ReadTimeout):
            time.sleep(5)
    print("網路連線問題，請檢查您的網路連線")
    return None


def requests_get(*args1, **args2):
    """使用 session 發送 GET 請求，自動處理連接錯誤和超時"""
    global ses
    if ses is None:
        ses = find_best_session()

    i = 3
    while i >= 0:
        try:
            return ses.get(*args1, timeout=10, **args2)
        except (requests.ConnectionError, requests.ReadTimeout):
            time.sleep(5)
            ses = find_best_session()

        i -= 1
    return pd.DataFrame()


def otc_date_str(date):
    """將日期轉換為櫃買中心使用的格式"""
    year = date.year - 1911
    month = date.month
    day = date.day
    return f"{year}/{month:02d}/{day:02d}"


def combine_index(df, n1, n2):
    """合併 dataframe 的兩個欄位為索引"""
    try:
        df = df.set_index([n1, n2])
        return df
    except Exception as e:
        logger.error(f"combine_index 發生錯誤: {e}")
        return df


def preprocess(df, date):
    """資料預處理"""
    try:
        df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
        df.columns = df.columns.str.replace(" ", "")
        df.index = pd.MultiIndex.from_tuples([(i, date) for i in df.index])
        return df
    except Exception as e:
        logger.error(f"preprocess 發生錯誤: {e}")
        return df


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
    # 若 df 為空則不儲存
    if df is None or df.empty:
        logger.warning(f"{name} 資料為空，未儲存檔案。")
        return None
    try:
        df.to_csv(file_path)
        logger.info(f"已儲存資料至 {file_path}")
    except Exception as e:
        logger.error(f"儲存 {file_path} 時發生錯誤: {e}")
    return file_path


def crawl_price_twe(date):
    """爬取台灣證券交易所的股票價格資料

    ⚠️ 已棄用：請使用 src.data_sources.TWSECrawler().price_twe(date)
    """
    warnings.warn(
        "crawl_price_twe() 已棄用，請使用新的模組化API：\n"
        "from src.data_sources import TWSECrawler\n"
        "crawler = TWSECrawler()\n"
        "data = crawler.price_twe(date)",
        DeprecationWarning,
        stacklevel=2
    )
    date_str = date.strftime("%Y%m%d")
    res = requests_get(
        "https://www.twse.com.tw/exchangeReport/MI_INDEX?response=csv&date="
        + date_str
        + "&type=ALLBUT0999"
    )

    if res.text == "":
        return pd.DataFrame()

    header = np.where(list(map(lambda l: "證券代號" in l, res.text.split("\n")[:500])))[
        0
    ][0]
    df = pd.read_csv(StringIO(res.text.replace("=", "")), header=header - 1)
    df.columns = df.columns.str.replace(" ", "")

    if "證券代號" in df.columns:
        df = combine_index(df, "證券代號", "證券名稱")
    else:
        df = combine_index(df, "證券代碼", "證券名稱")

    df = preprocess(df, date)
    return df


def crawl_price_otc(date):
    """爬取櫃買中心的股票價格資料

    ⚠️ 已棄用：請使用 src.data_sources.TWSECrawler().price_otc(date)
    """
    warnings.warn(
        "crawl_price_otc() 已棄用，請使用新的模組化API：\n"
        "from src.data_sources import TWSECrawler\n"
        "crawler = TWSECrawler()\n"
        "data = crawler.price_otc(date)",
        DeprecationWarning,
        stacklevel=2
    )
    datestr = otc_date_str(date)

    url = (
        "https://www.tpex.org.tw/web/stock/aftertrading/daily_close_quotes/stk_quote_download.php?l=zh-tw&d="
        + datestr
        + "&s=0,asc,0"
    )
    res = requests_get(url)

    if len(res.text) < 10:
        return pd.DataFrame()

    # 自動偵測 header 行數
    lines = res.text.split("\n")
    header_line = None
    for i, line in enumerate(lines[:10]):
        if ("代號" in line or "股票代號" in line) and (
            "名稱" in line or "公司名稱" in line
        ):
            header_line = i
            break
    if header_line is not None:
        try:
            df = pd.read_csv(StringIO(res.text), header=header_line)
        except Exception:
            return pd.DataFrame()
    else:
        # 不是正確表格，回傳空
        return pd.DataFrame()
    df.columns = df.columns.str.replace(" ", "")
    # 兼容不同欄位名稱
    if "代號" in df.columns and "名稱" in df.columns:
        df = combine_index(df, "代號", "名稱")
    elif "股票代號" in df.columns and "公司名稱" in df.columns:
        df = combine_index(df, "股票代號", "公司名稱")
    else:
        return pd.DataFrame()
    df = preprocess(df, date)
    return df


def crawl_finance_statement(year, season):
    """爬取財務報表資料（簡化版）"""
    logger.warning("注意：財務報表爬取功能已簡化，僅返回空的 DataFrame")
    logger.warning("如需完整功能，請參考 data_ingest.py 中的實現")
    return pd.DataFrame()


def crawl_monthly_report(date):
    """爬取月營收資料"""
    year = date.year - 1911
    month = date.month

    url = f"https://mops.twse.com.tw/nas/t21/sii/t21sc03_{year}_{month}_0.html"
    res = requests_get(url)
    res.encoding = "big5"

    try:
        dfs = pd.read_html(StringIO(res.text))
    except BaseException:
        return pd.DataFrame()

    df = pd.concat([df for df in dfs if df.shape[1] > 10])
    df = df.iloc[:, :10]
    df.columns = df.columns.droplevel(0)
    df.columns = [
        "公司代號",
        "公司名稱",
        "當月營收",
        "上月營收",
        "去年當月營收",
        "上月比較增減(%)",
        "去年同月增減(%)",
        "當月累計營收",
        "去年累計營收",
        "前期比較增減(%)",
    ]

    df = combine_index(df, "公司代號", "公司名稱")
    df = preprocess(df, date)
    return df


def main():
    """主程式：執行各種爬蟲並儲存資料"""
    logger.info("開始執行每日股市資料爬蟲...")

    # 取得今日日期
    today = datetime.datetime.today()
    date_str = today.strftime("%Y-%m-%d")
    year = today.year
    month = today.month

    # 計算當前季度
    season = (month - 1) // 3 + 1

    logger.info(f"目標日期: {date_str}")
    logger.info(f"目標年份: {year}, 季度: {season}, 月份: {month}")

    try:
        # 1. 爬取上市股價資料
        logger.info("爬取上市股價資料...")
        twse_price_df = crawl_price_twe(today.date())
        if not twse_price_df.empty:
            save_to_csv(twse_price_df, f"twse_price_{date_str}")
            logger.info(f"上市股價資料筆數: {len(twse_price_df)}")
        else:
            logger.warning("無上市股價資料")

        # 2. 爬取上櫃股價資料
        logger.info("爬取上櫃股價資料...")
        otc_price_df = crawl_price_otc(today.date())
        if not otc_price_df.empty:
            save_to_csv(otc_price_df, f"otc_price_{date_str}")
            logger.info(f"上櫃股價資料筆數: {len(otc_price_df)}")
        else:
            logger.warning("無上櫃股價資料")

        # 3. 爬取財務報表資料
        logger.info("爬取財務報表資料...")
        finance_df = crawl_finance_statement(year, season)
        if not finance_df.empty:
            save_to_csv(finance_df, f"finance_{year}_Q{season}")
            logger.info(f"財務報表資料筆數: {len(finance_df)}")
        else:
            logger.warning("無財務報表資料")

        # 4. 爬取月營收資料
        logger.info("爬取月營收資料...")
        monthly_report_df = crawl_monthly_report(today.date())
        if not monthly_report_df.empty:
            save_to_csv(monthly_report_df, f"monthly_report_{year}_{month:02d}")
            logger.info(f"月營收資料筆數: {len(monthly_report_df)}")
        else:
            logger.warning("無月營收資料")

        logger.info("爬蟲執行完成！所有資料已儲存至 ./data 目錄")

    except Exception as e:
        logger.error(f"執行過程中發生錯誤: {e}")
        logger.error(
            "請確認網路連線正常，並安裝所有必要的套件 (pip install -r requirements.txt)"
        )


if __name__ == "__main__":
    main()
