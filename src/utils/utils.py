"""
共用工具函數模組

此模組包含整個交易系統中共用的工具函數，如數值處理、日期轉換等。
"""

import numpy as np
import pandas as pd
import functools
from pathlib import Path
from dotenv import load_dotenv


def load_env():
    """
    自動載入環境變數

    使用 python-dotenv 的 load_dotenv() 函式載入 .env 檔案中的環境變數

    Returns:
        bool: 如果成功載入 .env 檔案則返回 True，否則返回 False
    """
    return load_dotenv()


# 載入環境變數
load_env()


def neg(s):
    """
    將字符串轉換為數字，特別處理括號表示的負數（例如 "(100)" 轉換為 -100）

    Args:
        s: 要轉換的字符串或數值

    Returns:
        float: 轉換後的數值
    """
    if isinstance(s, float):
        return s
    if s is None or str(s).strip() == "":
        return np.nan
    if str(s) == "nan":
        return np.nan
    s = str(s).replace(",", "")
    if s and s[0] == "(":  # 防止空字串
        return -float(s[1:-1])
    else:
        return float(s)


def generate_random_header():
    """
    生成隨機的 HTTP 請求頭，用於爬蟲

    Returns:
        dict: 包含隨機 User-Agent 的請求頭
    """
    import random
    import copy

    random_headers = [
        {
            "Accept": "*/*",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (X11; Linux i686 on x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.67 Safari/537.36 OPR/56.0.3051.104",
        },
        {
            "Accept": "*/*",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.62 Safari/537.36 OPR/54.0.2952.64",
        },
        {
            "Accept": "*/*",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:58.0.2) Gecko/20100101 Firefox/58.0.2",
        },
        {
            "Accept": "*/*",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.67 Safari/537.36 OPR/56.0.3051.104",
        },
        {
            "Accept": "*/*",
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (X11; Linux i686 on x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.80 Safari/537.36 OPR/57.0.3098.116",
        },
    ]

    return copy.copy(random.choice(random_headers))


def otc_date_str(date):
    """
    將 datetime.date 轉換成民國曆

    Args:
        date (datetime.date): 西元曆的日期

    Returns:
        str: 民國曆日期 ex: 109/01/01
    """
    return str(date.year - 1911) + date.strftime("%Y/%m/%d")[4:]


def combine_index(df, n1, n2):
    """
    將 dataframe df 中的股票代號與股票名稱合併

    Args:
        df (pandas.DataFrame): 此 dataframe 含有 column n1, n2
        n1 (str): 股票代號
        n2 (str): 股票名稱

    Returns:
        df (pandas.DataFrame): 此 dataframe 的 index 為「股票代號+股票名稱」
    """
    return df.set_index(
        df[n1].astype(str).str.replace(" ", "")
        + " "
        + df[n2].astype(str).str.replace(" ", "")
    ).drop([n1, n2], axis=1)


def preprocess(df, date):
    """
    預處理資料框架

    Args:
        df (pandas.DataFrame): 要處理的資料框架
        date (datetime.date): 日期

    Returns:
        pandas.DataFrame: 處理後的資料框架
    """
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
    df.columns = df.columns.str.replace(" ", "")
    df.columns.name = ""
    if "stock_id" not in df.columns:
        raise ValueError("資料缺少 'stock_id' 欄位，請確認原始資料格式。")
    df.index.name = "stock_id"
    df["date"] = pd.to_datetime(date)
    df = df.reset_index().set_index(["stock_id", "date"])
    df = df.apply(lambda s: s.astype(str).str.replace(",", ""))

    return df


def to_seasonal(df):
    """
    將季度資料轉換為季節性資料

    Args:
        df (pandas.DataFrame): 季度資料

    Returns:
        pandas.DataFrame: 季節性資料
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("to_seasonal: 輸入的 DataFrame index 必須為 DatetimeIndex")
    season4 = df[df.index.month == 3]
    season1 = df[df.index.month == 5]
    season2 = df[df.index.month == 8]
    season3 = df[df.index.month == 11]
    season1.index = season1.index.year
    season2.index = season2.index.year
    season3.index = season3.index.year
    season4.index = season4.index.year - 1
    newseason1 = season1
    newseason2 = season2 - season1.reindex_like(season2)
    newseason3 = season3 - season2.reindex_like(season3)
    newseason4 = season4 - season3.reindex_like(season4)
    newseason1.index = pd.to_datetime(newseason1.index.astype(str) + "-05-15")
    newseason2.index = pd.to_datetime(newseason2.index.astype(str) + "-08-14")
    newseason3.index = pd.to_datetime(newseason3.index.astype(str) + "-11-14")
    newseason4.index = pd.to_datetime((newseason4.index + 1).astype(str) + "-03-31")
    return (
        newseason1.append(newseason2).append(newseason3).append(newseason4).sort_index()
    )


def scale(dataset):
    """
    標準化資料

    Args:
        dataset (pandas.DataFrame): 要標準化的資料

    Returns:
        tuple: (StandardScaler, pandas.DataFrame) 標準化器和標準化後的資料
    """
    from sklearn.preprocessing import StandardScaler

    ss = StandardScaler()
    dataset_scaled = ss.fit_transform(dataset)
    return ss, pd.DataFrame(
        dataset_scaled, columns=dataset.columns, index=dataset.index
    )


def dropna(x, y):
    """
    刪除 x 和 y 中的缺失值

    Args:
        x (pandas.DataFrame): 特徵資料
        y (pandas.Series): 標籤資料

    Returns:
        tuple: (pandas.DataFrame, pandas.Series) 刪除缺失值後的資料
    """
    isna = (x.isnull().sum(axis=1) != 0) | y.isnull()
    return x[~isna], y[~isna]


def check_stationary(s):
    """
    檢查時間序列是否平穩

    Args:
        s (pandas.Series): 時間序列

    Returns:
        float: p 值，小於 0.05 表示平穩
    """
    from statsmodels.tsa.stattools import adfuller

    X = s.dropna()[:: max(1, int(len(s) / 10000))]
    if len(X) < 10:
        raise ValueError("check_stationary: 輸入序列長度過短，無法進行檢定。")
    result = adfuller(X)
    return result[1]


def retry(max_retries=3):
    """
    錯誤重試裝飾器

    當函式執行失敗時，自動重試指定次數

    Args:
        max_retries (int): 最大重試次數，預設為 3

    Returns:
        function: 裝飾後的函式

    Example:
        @retry(max_retries=5)
        def unstable_function():
            # 可能失敗的函式
            pass
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        # 最後一次重試仍失敗，記錄錯誤並回傳 None
                        import logging

                        logger = logging.getLogger(func.__module__)
                        logger.error(
                            f"函式 {func.__name__} 執行失敗 {max_retries} 次，放棄重試: {str(e)}"
                        )
                        return None
                    print(
                        f"函式 {func.__name__} 執行失敗，正在進行第 {retries} 次重試..."
                    )
                    # 等待 1 秒後重試
                    import time

                    time.sleep(1)

        return wrapper

    return decorator


def cache_dataframe(fn):
    """
    DataFrame 快取裝飾器

    將函式返回的 DataFrame 快取為 CSV 檔案，下次調用時優先讀取快取

    Args:
        fn (function): 返回 DataFrame 的函式

    Returns:
        function: 裝飾後的函式

    Example:
        @cache_dataframe
        def get_stock_data():
            # 獲取股票數據的函式
            return pd.DataFrame(...)
    """
    import hashlib
    import pickle

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        # 創建快取目錄
        cache_dir = Path("cache")
        cache_dir.mkdir(exist_ok=True)
        # 生成快取檔案名稱（用 hash 處理參數）
        try:
            key_bytes = pickle.dumps((args, kwargs))
            cache_key = hashlib.md5(key_bytes).hexdigest()
        except Exception:
            cache_key = fn.__name__
        cache_file = cache_dir / f"{fn.__name__}_{cache_key}.csv"
        # 檢查快取是否存在
        if cache_file.exists():
            print(f"從快取讀取: {cache_file}")
            return pd.read_csv(cache_file, index_col=0, parse_dates=True)
        # 執行原函式
        result = fn(*args, **kwargs)
        # 將結果快取為 CSV
        if isinstance(result, pd.DataFrame):
            result.to_csv(cache_file)
            print(f"已快取至: {cache_file}")
        return result

    return wrapper


def align_timeseries(df, start=None, end=None):
    """
    按日期切片並補齊缺值

    將時間序列數據按照指定的開始和結束日期切片，並補齊缺失值

    Args:
        df (pandas.DataFrame): 時間序列數據，索引為日期
        start (str or datetime, optional): 開始日期，如果為 None 則使用數據的第一個日期
        end (str or datetime, optional): 結束日期，如果為 None 則使用數據的最後一個日期

    Returns:
        pandas.DataFrame: 處理後的時間序列數據

    Example:
        aligned_df = align_timeseries(stock_data, '2020-01-01', '2020-12-31')
    """
    # 確保索引是日期類型
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # 如果未指定開始或結束日期，使用數據的第一個或最後一個日期
    if start is None:
        start = df.index.min()
    else:
        start = pd.to_datetime(start)

    if end is None:
        end = df.index.max()
    else:
        end = pd.to_datetime(end)

    # 創建完整的日期範圍
    date_range = pd.date_range(start=start, end=end, freq="D")

    # 重新索引並補齊缺失值
    aligned_df = df.reindex(date_range)

    return aligned_df


def clean_data(df, remove_outliers=True, fill_na=True, method="ffill"):
    """
    清理數據框架，包括移除異常值和填充缺失值

    Args:
        df (pandas.DataFrame): 要清理的數據框架
        remove_outliers (bool, optional): 是否移除異常值，預設為 True
        fill_na (bool, optional): 是否填充缺失值，預設為 True
        method (str, optional): 填充缺失值的方法，可選 'ffill'（向前填充）、'bfill'（向後填充）或 'interpolate'（插值），預設為 'ffill'

    Returns:
        pandas.DataFrame: 清理後的數據框架
    """
    if df is None or df.empty:
        return df

    # 複製數據框架，避免修改原始數據
    cleaned_df = df.copy()

    # 移除異常值
    if remove_outliers:
        # 對每一列分別處理
        for col in cleaned_df.select_dtypes(include=[np.number]).columns:
            # 計算 Q1, Q3 和 IQR
            Q1 = cleaned_df[col].quantile(0.25)
            Q3 = cleaned_df[col].quantile(0.75)
            IQR = Q3 - Q1

            # 定義異常值範圍
            lower_bound = Q1 - 3 * IQR
            upper_bound = Q3 + 3 * IQR

            # 將異常值設為 NaN
            cleaned_df.loc[
                (cleaned_df[col] < lower_bound) | (cleaned_df[col] > upper_bound), col
            ] = np.nan

    # 填充缺失值
    if fill_na:
        if method == "ffill":
            cleaned_df = cleaned_df.fillna(method="ffill")
        elif method == "bfill":
            cleaned_df = cleaned_df.fillna(method="bfill")
        elif method == "interpolate":
            cleaned_df = cleaned_df.interpolate(method="linear")

    return cleaned_df
