"""
統一資料存取 API 模組

⚠️ 重要通知：此模組中的部分函數已棄用 ⚠️

遷移指南：
- clean_data() → 使用 DataManagementService.clean_data()
- get_stock_data() → 使用 DataManagementService 的相應方法
- export_data_to_csv() → 使用 DataManagementService 的相應方法

新架構位置：src.core.data_management_service.DataManagementService

此模組提供統一的資料存取介面，整合了結構化數據和非結構化數據的存取功能。
所有其他模組都應該通過此模組獲取資料，而不是直接調用資料來源模組。
"""

import warnings

import datetime
import logging
from typing import Any, Dict, List, Optional

import pandas as pd

# 設定日誌
logger = logging.getLogger(__name__)

# 導入資料來源模組
try:
    from src.data_sources.structured_data import (
        crawl_bargin_otc,
        crawl_bargin_twe,
        crawl_benchmark,
        crawl_monthly_report,
        crawl_pe_otc,
        crawl_pe_twe,
        crawl_price_otc,
        crawl_price_twe,
    )
except ImportError as e:
    logger.warning("無法導入結構化資料模組: %s", e)
    # 提供備用函數
    def crawl_bargin_otc(*args, **kwargs):
        return pd.DataFrame()
    def crawl_bargin_twe(*args, **kwargs):
        return pd.DataFrame()
    def crawl_benchmark(*args, **kwargs):
        return pd.DataFrame()
    def crawl_monthly_report(*args, **kwargs):
        return pd.DataFrame()
    def crawl_pe_otc(*args, **kwargs):
        return pd.DataFrame()
    def crawl_pe_twe(*args, **kwargs):
        return pd.DataFrame()
    def crawl_price_otc(*args, **kwargs):
        return pd.DataFrame()
    def crawl_price_twe(*args, **kwargs):
        return pd.DataFrame()

try:
    from src.data_sources.unstructured_data import (
        analyze_market_sentiment,
        crawl_market_info,
        get_market_info,
        get_market_overview,
        get_news_for_stock,
    )
except ImportError as e:
    logger.warning("無法導入非結構化資料模組: %s", e)
    # 提供備用函數
    def analyze_market_sentiment(*args, **kwargs):
        return {"sentiment": "neutral", "score": 0.0}
    def crawl_market_info(*args, **kwargs):
        return []
    def get_market_info(*args, **kwargs):
        return {}
    def get_market_overview(*args, **kwargs):
        return {}
    def get_news_for_stock(*args, **kwargs):
        return []

# 導入真實數據整合服務
try:
    from src.core.real_data_integration import real_data_service
    logger.info("成功導入真實數據整合服務")
except ImportError as e:
    logger.error("無法導入真實數據整合服務: %s", e)
    # 提供基本的錯誤處理
    class BasicDataService:
        def get_stock_data(self, *args, **kwargs):
            logger.error("真實數據服務不可用")
            return pd.DataFrame()
        def update_data(self, *args, **kwargs):
            logger.error("真實數據服務不可用")
            return {"success": False, "message": "數據服務不可用"}
        def get_market_info(self, *args, **kwargs):
            logger.error("真實數據服務不可用")
            return {"status": "服務不可用"}

    real_data_service = BasicDataService()

# 導入資料庫模組（保持向後兼容）
try:
    from src.database.db_manager import db_manager
except ImportError as e:
    logger.warning("無法導入資料庫管理模組: %s", e)
    db_manager = None

# 資料類型常數
DATA_TYPES = {
    "price": "stock_price",
    "bargin": "institutional_investors",
    "pe": "pe_ratio",
    "monthly_report": "monthly_revenue",
    "finance": "financial_statement",
    "benchmark": "benchmark",
    "market_info": "market_info",
}

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
        from FinMind.data import DataLoader

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

        return df
    except Exception as e:
        print(f"獲取 FinMind 資料時發生錯誤: {e}")
        return pd.DataFrame()


# 資料清洗函數
def clean_data(df, method="ffill"):
    """
    清洗資料，包括缺值填補、日期格式統一、欄位標準化

    ⚠️ 已棄用：請使用 DataManagementService.clean_data()

    Args:
        df (pandas.DataFrame): 要清洗的資料
        method (str): 缺值填補方法，'ffill' 為前向填補，'bfill' 為後向填補

    Returns:
        pandas.DataFrame: 清洗後的資料
    """
    warnings.warn(
        "clean_data() 已棄用，請使用新的 DataManagementService：\n"
        "from src.core.data_management_service import DataManagementService\n"
        "service = DataManagementService()\n"
        "cleaned_df = service.clean_data(df, method)",
        DeprecationWarning,
        stacklevel=2
    )
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


def get_stock_data(
    stock_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    data_type: str = "price",
) -> pd.DataFrame:
    """
    獲取股票資料 - 使用真實數據源

    Args:
        stock_id: 股票代號，如果為 None 則獲取所有股票
        start_date: 開始日期，格式為 'YYYY-MM-DD'
        end_date: 結束日期，格式為 'YYYY-MM-DD'
        data_type: 資料類型，目前主要支援 'price'

    Returns:
        pandas.DataFrame: 股票資料
    """
    try:
        # 轉換日期格式
        start_dt = None
        end_dt = None

        if start_date:
            start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date:
            end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()

        # 如果指定了股票代號，直接獲取該股票數據
        if stock_id:
            # 確保股票代號格式正確
            symbol = stock_id if stock_id.endswith('.TW') else f"{stock_id}.TW"
            df = real_data_service.get_stock_data(symbol, start_dt, end_dt)

            if not df.empty:
                # 重命名欄位以保持兼容性
                df = df.rename(columns={
                    'symbol': 'stock_id',
                    'date': 'date',
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'volume': 'volume'
                })
                logger.info(f"✅ 獲取 {symbol} 真實數據: {len(df)} 筆記錄")
            else:
                logger.warning(f"⚠️ 未找到 {symbol} 的數據")

            return df
        else:
            # 如果沒有指定股票，獲取所有可用股票的數據
            available_symbols = real_data_service.get_available_symbols()
            all_data = []

            for symbol in available_symbols[:10]:  # 限制數量避免過載
                df = real_data_service.get_stock_data(symbol, start_dt, end_dt)
                if not df.empty:
                    df = df.rename(columns={'symbol': 'stock_id'})
                    all_data.append(df)

            if all_data:
                result_df = pd.concat(all_data, ignore_index=True)
                logger.info(f"✅ 獲取多股票真實數據: {len(result_df)} 筆記錄")
                return result_df
            else:
                logger.warning("⚠️ 未找到任何股票數據")
                return pd.DataFrame()

    except Exception as e:
        logger.error(f"❌ 獲取股票數據失敗: {e}")
        return pd.DataFrame()


def update_stock_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    data_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    更新股票資料 - 使用真實數據源

    Args:
        start_date: 開始日期，格式為 'YYYY-MM-DD'
        end_date: 結束日期，格式為 'YYYY-MM-DD'
        data_types: 資料類型列表（保持兼容性，實際使用真實數據）

    Returns:
        Dict[str, Any]: 更新結果
    """
    if start_date is None:
        start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime(
            "%Y-%m-%d"
        )

    if end_date is None:
        end_date = datetime.datetime.now().strftime("%Y-%m-%d")

    if data_types is None:
        data_types = ["price", "bargin", "pe", "monthly_report", "benchmark"]

    # 將日期字符串轉換為 datetime 對象
    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()

    # 生成日期範圍
    date_range = pd.date_range(start=start_dt, end=end_dt, freq="B")

    # 初始化結果字典
    result: dict[str, pd.DataFrame] = {}

    # 更新各種資料
    for date in date_range:
        date = pd.Timestamp(date.date())

        if "price" in data_types:
            # 爬取股價資料
            twe_price = crawl_price_twe(date)
            otc_price = crawl_price_otc(date)

            if not twe_price.empty or not otc_price.empty:
                # 合併上市和上櫃資料
                price_df = (
                    pd.concat([twe_price, otc_price])
                    if not twe_price.empty and not otc_price.empty
                    else (twe_price if not twe_price.empty else otc_price)
                )

                # 將資料寫入資料庫
                db_manager.dataframe_to_sql(
                    price_df.reset_index(), "stock_price", "append"
                )

                # 更新結果字典
                if "price" in result:
                    result["price"] = pd.concat([result["price"], price_df])
                else:
                    result["price"] = price_df

        if "bargin" in data_types:
            # 爬取三大法人買賣超資料
            twe_bargin = crawl_bargin_twe(date)
            otc_bargin = crawl_bargin_otc(date)

            if not twe_bargin.empty or not otc_bargin.empty:
                # 合併上市和上櫃資料
                bargin_df = (
                    pd.concat([twe_bargin, otc_bargin])
                    if not twe_bargin.empty and not otc_bargin.empty
                    else (twe_bargin if not twe_bargin.empty else otc_bargin)
                )

                # 將資料寫入資料庫
                db_manager.dataframe_to_sql(
                    bargin_df.reset_index(), "institutional_investors", "append"
                )

                # 更新結果字典
                if "bargin" in result:
                    result["bargin"] = pd.concat([result["bargin"], bargin_df])
                else:
                    result["bargin"] = bargin_df

        if "pe" in data_types:
            # 爬取本益比資料
            twe_pe = crawl_pe_twe(date)
            otc_pe = crawl_pe_otc(date)

            if not twe_pe.empty or not otc_pe.empty:
                # 合併上市和上櫃資料
                pe_df = (
                    pd.concat([twe_pe, otc_pe])
                    if not twe_pe.empty and not otc_pe.empty
                    else (twe_pe if not twe_pe.empty else otc_pe)
                )

                # 將資料寫入資料庫
                db_manager.dataframe_to_sql(pe_df.reset_index(), "pe_ratio", "append")

                # 更新結果字典
                if "pe" in result:
                    result["pe"] = pd.concat([result["pe"], pe_df])
                else:
                    result["pe"] = pe_df

        if "monthly_report" in data_types and date.day <= 10:
            # 爬取月營收資料
            monthly_report = crawl_monthly_report(date)

            if not monthly_report.empty:
                # 將資料寫入資料庫
                db_manager.dataframe_to_sql(
                    monthly_report.reset_index(), "monthly_revenue", "append"
                )

                # 更新結果字典
                if "monthly_report" in result:
                    result["monthly_report"] = pd.concat(
                        [result["monthly_report"], monthly_report]
                    )
                else:
                    result["monthly_report"] = monthly_report

        if "benchmark" in data_types:
            # 爬取大盤指數資料
            benchmark = crawl_benchmark(date)

            if not benchmark.empty:
                # 將資料寫入資料庫
                db_manager.dataframe_to_sql(
                    benchmark.reset_index(), "benchmark", "append"
                )

                # 更新結果字典
                if "benchmark" in result:
                    result["benchmark"] = pd.concat([result["benchmark"], benchmark])
                else:
                    result["benchmark"] = benchmark

    return result


# 向後相容性別名
update_data = update_stock_data


def get_market_news(
    query: str = "台灣股市",
    limit: int = 50,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    獲取市場新聞

    Args:
        query: 查詢關鍵詞
        limit: 返回結果數量限制
        start_date: 開始日期，格式為 'YYYY-MM-DD'
        end_date: 結束日期，格式為 'YYYY-MM-DD'

    Returns:
        List[Dict[str, Any]]: 市場新聞列表
    """
    # 如果指定了日期範圍，則先爬取新聞
    if start_date and end_date:
        crawl_market_info(query, start_date, end_date)

    # 從資料庫獲取新聞
    news = get_market_info(query, limit)

    return news


def analyze_news_sentiment(query: str = "台灣股市", limit: int = 50) -> Dict[str, Any]:
    """
    分析新聞情緒

    Args:
        query: 查詢關鍵詞
        limit: 分析的新聞數量

    Returns:
        Dict[str, Any]: 情緒分析結果
    """
    # 從資料庫獲取新聞
    news = get_market_info(query, limit)

    # 分析情緒
    sentiment = analyze_market_sentiment(news)

    return sentiment


def get_stock_news(
    stock_id: str, days: int = 30, limit: int = 20
) -> List[Dict[str, Any]]:
    """
    獲取特定股票的相關新聞

    Args:
        stock_id: 股票代號
        days: 獲取最近幾天的新聞
        limit: 返回結果數量限制

    Returns:
        List[Dict[str, Any]]: 新聞列表
    """
    return get_news_for_stock(stock_id, days, limit)


def get_market_sentiment_overview(days: int = 7) -> Dict[str, Dict[str, Any]]:
    """
    獲取市場情緒概況

    Args:
        days: 獲取最近幾天的市場情緒

    Returns:
        Dict[str, Dict[str, Any]]: 市場情緒概況
    """
    return get_market_overview(days)


def get_financial_statement(stock_id: str, year: int, season: int) -> pd.DataFrame:
    """
    獲取財務報表

    Args:
        stock_id: 股票代號
        year: 年份
        season: 季度 (1-4)

    Returns:
        pandas.DataFrame: 財務報表
    """
    # 從資料庫獲取財務報表
    condition = "stock_id = ? AND year = ? AND season = ?"
    params = (stock_id, year, season)

    df = db_manager.get_table_as_dataframe("financial_statement", condition, params)

    # 如果資料庫中沒有資料，自動補抓 FinMind 財報
    if df.empty:
        logger.warning(f"資料庫無 {stock_id} {year}Q{season} 財報，嘗試自動補抓...")
        try:
            # 轉換季為日期範圍
            start_date = f"{year}-{(season-1)*3+1:02d}-01"
            end_month = season * 3
            if end_month > 12:
                end_month = 12
            end_date = f"{year}-{end_month:02d}-28"
            finmind_df = fetch_finmind_data(
                "TaiwanStockFinancialStatement", stock_id, start_date, end_date
            )
            if not finmind_df.empty:
                finmind_df = clean_data(finmind_df)
                # 補齊 year/season 欄位
                finmind_df["year"] = year
                finmind_df["season"] = season
                db_manager.dataframe_to_sql(finmind_df, "financial_statement", "append")
                # 再查一次
                df = db_manager.get_table_as_dataframe(
                    "financial_statement", condition, params
                )
        except Exception as e:
            logger.error(f"自動補抓 FinMind 財報失敗: {e}")

    return df


def export_data_to_csv(
    data_type: str,
    file_path: str,
    stock_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> bool:
    """
    將資料匯出為 CSV 檔案

    Args:
        data_type: 資料類型，可選 'price', 'bargin', 'pe', 'monthly_report', 'finance', 'benchmark', 'market_info'
        file_path: CSV 檔案路徑
        stock_id: 股票代號，如果為 None 則匯出所有股票
        start_date: 開始日期，格式為 'YYYY-MM-DD'
        end_date: 結束日期，格式為 'YYYY-MM-DD'

    Returns:
        bool: 是否成功匯出
    """
    # 檢查資料類型是否有效
    if data_type not in DATA_TYPES:
        logger.error(f"無效的資料類型: {data_type}")
        return False

    # 獲取資料表名稱
    table_name = DATA_TYPES[data_type]

    # 構建查詢條件
    conditions = []
    params = []

    if stock_id:
        conditions.append("stock_id = ?")
        params.append(stock_id)

    if start_date:
        conditions.append("date >= ?")
        params.append(start_date)

    if end_date:
        conditions.append("date <= ?")
        params.append(end_date)

    condition = " AND ".join(conditions) if conditions else None

    # 匯出資料
    return db_manager.export_table_to_csv(
        table_name, file_path, condition, tuple(params)
    )


def import_csv_to_data(
    data_type: str, file_path: str, if_exists: str = "append"
) -> bool:
    """
    將 CSV 檔案匯入資料

    Args:
        data_type: 資料類型，可選 'price', 'bargin', 'pe', 'monthly_report', 'finance', 'benchmark', 'market_info'
        file_path: CSV 檔案路徑
        if_exists: 如果資料表已存在，如何處理，可選 'fail', 'replace', 'append'

    Returns:
        bool: 是否成功匯入
    """
    # 檢查資料類型是否有效
    if data_type not in DATA_TYPES:
        logger.error(f"無效的資料類型: {data_type}")
        return False

    # 獲取資料表名稱
    table_name = DATA_TYPES[data_type]

    # 匯入資料
    return db_manager.import_csv_to_table(file_path, table_name, if_exists)
