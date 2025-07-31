"""
資料查詢介面模組

此模組提供靈活的資料查詢和篩選功能，包括多種查詢條件設定、
結果顯示和資料匯出等功能。

主要功能：
- 多條件資料查詢設定
- 查詢結果表格顯示
- 資料視覺化圖表
- 查詢結果匯出
- 查詢歷史記錄

Example:
    ```python
    from src.ui.pages.data_management.data_query import show_data_query_interface
    show_data_query_interface()
    ```

Note:
    此模組依賴於 DataManagementService 來執行實際的資料查詢邏輯。
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List, Tuple

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 導入自定義元件
try:
    from src.ui.components.tables import data_table
    from src.ui.components.charts import candlestick_chart
except ImportError as e:
    st.warning(f"無法導入 UI 組件: {e}")

    # 提供簡化的替代函數
    def data_table(df: pd.DataFrame, **kwargs) -> None:
        """簡化的資料表格顯示"""
        st.dataframe(df, use_container_width=True)

    def candlestick_chart(df: pd.DataFrame, **kwargs) -> None:
        """簡化的 K 線圖顯示"""
        if not df.empty and all(
            col in df.columns for col in ["Open", "High", "Low", "Close"]
        ):
            fig = go.Figure(
                data=go.Candlestick(
                    x=df.index,
                    open=df["Open"],
                    high=df["High"],
                    low=df["Low"],
                    close=df["Close"],
                )
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("無法顯示 K 線圖：資料格式不正確")


def get_query_options() -> Dict[str, List[str]]:
    """
    獲取查詢選項

    提供資料查詢所需的各種選項，包括資料類型、股票代碼、
    時間範圍等。

    Returns:
        Dict[str, List[str]]: 查詢選項字典，包含以下鍵值：
            - data_types: 可查詢的資料類型
            - symbols: 可查詢的股票代碼
            - time_ranges: 預設時間範圍選項

    Example:
        ```python
        options = get_query_options()
        data_types = options['data_types']
        ```
    """
    # 嘗試從資料服務獲取
    data_service = st.session_state.get("data_service")
    if data_service:
        try:
            return {
                "data_types": [dt["name"] for dt in data_service.get_data_types()],
                "symbols": data_service.get_available_symbols(),
                "time_ranges": [
                    "最近1週",
                    "最近1個月",
                    "最近3個月",
                    "最近1年",
                    "自定義範圍",
                ],
            }
        except Exception as e:
            st.warning(f"無法從資料服務獲取查詢選項: {e}")

    # 返回模擬數據
    return {
        "data_types": ["股價資料", "基本面資料", "技術指標", "新聞資料", "財報資料"],
        "symbols": ["2330.TW", "2317.TW", "2454.TW", "AAPL", "MSFT", "GOOGL"],
        "time_ranges": ["最近1週", "最近1個月", "最近3個月", "最近1年", "自定義範圍"],
    }


def parse_time_range(
    time_range: str, start_date: Optional[date] = None, end_date: Optional[date] = None
) -> Tuple[date, date]:
    """
    解析時間範圍

    將時間範圍字串或自定義日期轉換為具體的開始和結束日期。

    Args:
        time_range: 時間範圍字串
        start_date: 自定義開始日期（當 time_range 為 '自定義範圍' 時使用）
        end_date: 自定義結束日期（當 time_range 為 '自定義範圍' 時使用）

    Returns:
        Tuple[date, date]: (開始日期, 結束日期)

    Example:
        ```python
        start, end = parse_time_range('最近1個月')
        print(f"查詢範圍: {start} 到 {end}")
        ```
    """
    today = date.today()

    if time_range == "最近1週":
        return today - timedelta(weeks=1), today
    elif time_range == "最近1個月":
        return today - timedelta(days=30), today
    elif time_range == "最近3個月":
        return today - timedelta(days=90), today
    elif time_range == "最近1年":
        return today - timedelta(days=365), today
    elif time_range == "自定義範圍":
        if start_date and end_date:
            return start_date, end_date
        else:
            # 如果沒有提供自定義日期，默認為最近1個月
            return today - timedelta(days=30), today
    else:
        # 默認為最近1個月
        return today - timedelta(days=30), today


def execute_data_query(query_config: Dict[str, Any]) -> Optional[pd.DataFrame]:
    """
    執行資料查詢

    根據查詢配置執行實際的資料查詢操作。

    Args:
        query_config: 查詢配置字典，包含查詢條件

    Returns:
        Optional[pd.DataFrame]: 查詢結果 DataFrame，如果查詢失敗則返回 None

    Example:
        ```python
        config = {
            'data_type': '股價資料',
            'symbols': ['2330.TW'],
            'start_date': date(2024, 1, 1),
            'end_date': date(2024, 1, 31)
        }
        result = execute_data_query(config)
        ```
    """
    # 嘗試從資料服務查詢
    data_service = st.session_state.get("data_service")
    if data_service:
        try:
            return data_service.query_data(query_config)
        except Exception as e:
            st.error(f"資料查詢失敗: {e}")
            return None

    # 生成模擬數據
    try:
        symbols = query_config.get("symbols", ["2330.TW"])
        start_date = query_config.get("start_date", date.today() - timedelta(days=30))
        end_date = query_config.get("end_date", date.today())

        # 生成日期範圍
        date_range = pd.date_range(start=start_date, end=end_date, freq="D")

        # 為每個股票生成模擬數據
        all_data = []
        for symbol in symbols:
            # 生成模擬股價數據
            base_price = 100 + hash(symbol) % 500
            prices = []
            current_price = base_price

            for _ in date_range:
                # 隨機價格變動
                change = (hash(str(current_price)) % 21 - 10) / 100  # -10% to +10%
                current_price *= 1 + change
                prices.append(current_price)

            # 創建 DataFrame
            symbol_data = pd.DataFrame(
                {
                    "Date": date_range,
                    "Symbol": symbol,
                    "Open": [p * 0.99 for p in prices],
                    "High": [p * 1.02 for p in prices],
                    "Low": [p * 0.98 for p in prices],
                    "Close": prices,
                    "Volume": [1000000 + hash(str(p)) % 5000000 for p in prices],
                }
            )

            all_data.append(symbol_data)

        # 合併所有數據
        result_df = pd.concat(all_data, ignore_index=True)
        return result_df

    except Exception as e:
        st.error(f"生成模擬數據失敗: {e}")
        return None


def show_query_form() -> Optional[Dict[str, Any]]:
    """
    顯示查詢表單

    提供使用者介面來設定查詢條件，包括資料類型、
    股票代碼、時間範圍等。

    Returns:
        Optional[Dict[str, Any]]: 查詢配置字典，如果配置不完整則返回 None

    Side Effects:
        渲染 Streamlit 表單組件
    """
    st.subheader("🔍 查詢條件設定")

    # 獲取查詢選項
    options = get_query_options()

    # 資料類型選擇
    data_type = st.selectbox(
        "選擇資料類型", options["data_types"], help="選擇要查詢的資料類型"
    )

    # 股票代碼選擇
    symbols = st.multiselect(
        "選擇股票代碼",
        options["symbols"],
        default=options["symbols"][:3],
        help="可選擇多個股票代碼進行查詢",
    )

    # 時間範圍選擇
    col1, col2 = st.columns([1, 2])

    with col1:
        time_range = st.selectbox(
            "時間範圍", options["time_ranges"], help="選擇查詢的時間範圍"
        )

    with col2:
        start_date = None
        end_date = None

        if time_range == "自定義範圍":
            col2_1, col2_2 = st.columns(2)
            with col2_1:
                start_date = st.date_input(
                    "開始日期",
                    value=date.today() - timedelta(days=30),
                    help="選擇查詢開始日期",
                )
            with col2_2:
                end_date = st.date_input(
                    "結束日期", value=date.today(), help="選擇查詢結束日期"
                )

    # 其他查詢選項
    with st.expander("進階選項", expanded=False):
        limit = st.number_input(
            "結果數量限制",
            min_value=10,
            max_value=10000,
            value=1000,
            step=10,
            help="限制查詢結果的最大數量",
        )

        sort_by = st.selectbox(
            "排序方式",
            ["日期 (新到舊)", "日期 (舊到新)", "股票代碼", "價格"],
            help="選擇結果排序方式",
        )

    # 驗證查詢條件
    if not symbols:
        st.warning("請至少選擇一個股票代碼")
        return None

    if time_range == "自定義範圍" and (not start_date or not end_date):
        st.warning("請選擇開始和結束日期")
        return None

    if time_range == "自定義範圍" and start_date > end_date:
        st.error("開始日期不能晚於結束日期")
        return None

    # 解析時間範圍
    parsed_start, parsed_end = parse_time_range(time_range, start_date, end_date)

    return {
        "data_type": data_type,
        "symbols": symbols,
        "start_date": parsed_start,
        "end_date": parsed_end,
        "limit": limit,
        "sort_by": sort_by,
        "time_range": time_range,
    }


def show_query_results(df: pd.DataFrame, query_config: Dict[str, Any]) -> None:
    """
    顯示查詢結果

    以表格和圖表形式顯示查詢結果，並提供匯出功能。

    Args:
        df: 查詢結果 DataFrame
        query_config: 查詢配置字典

    Returns:
        None

    Side Effects:
        渲染查詢結果表格和圖表
    """
    if df is None or df.empty:
        st.warning("查詢無結果")
        return

    st.subheader("📊 查詢結果")

    # 顯示結果統計
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("總記錄數", len(df))
    with col2:
        st.metric("股票數量", df["Symbol"].nunique() if "Symbol" in df.columns else 0)
    with col3:
        if "Date" in df.columns:
            date_range = (df["Date"].max() - df["Date"].min()).days
            st.metric("日期範圍", f"{date_range} 天")
    with col4:
        if "Close" in df.columns:
            avg_price = df["Close"].mean()
            st.metric("平均價格", f"{avg_price:.2f}")

    # 顯示資料表格
    st.subheader("📋 詳細資料")

    # 使用自定義表格組件或簡化版本
    data_table(df)

    # 提供資料下載
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 下載查詢結果 (CSV)",
        data=csv,
        file_name=f"query_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )

    # 顯示圖表（如果是股價資料）
    if query_config.get("data_type") == "股價資料" and all(
        col in df.columns for col in ["Open", "High", "Low", "Close", "Date"]
    ):
        st.subheader("📈 價格走勢圖")

        # 如果有多個股票，讓使用者選擇
        if "Symbol" in df.columns and df["Symbol"].nunique() > 1:
            selected_symbol = st.selectbox(
                "選擇股票", df["Symbol"].unique(), help="選擇要顯示圖表的股票"
            )
            chart_df = df[df["Symbol"] == selected_symbol].copy()
        else:
            chart_df = df.copy()

        if not chart_df.empty:
            # 設定日期為索引
            chart_df = chart_df.set_index("Date")
            candlestick_chart(chart_df)


def show_data_query_interface() -> None:
    """
    顯示資料查詢介面主頁面

    這是資料查詢功能的主要入口點，整合了查詢表單、
    結果顯示和資料視覺化等功能。

    Returns:
        None

    Side Effects:
        渲染完整的資料查詢界面
        可能執行資料查詢操作

    Example:
        ```python
        show_data_query_interface()
        ```

    Note:
        包含完整的錯誤處理和使用者友善的操作流程。
    """
    st.subheader("🔍 資料查詢介面")

    try:
        # 顯示查詢表單
        query_config = show_query_form()

        if query_config:
            # 顯示查詢按鈕
            col1, col2, col3 = st.columns([1, 1, 2])

            with col1:
                if st.button("🔍 執行查詢", type="primary"):
                    with st.spinner("正在查詢資料..."):
                        # 執行查詢
                        result_df = execute_data_query(query_config)

                        if result_df is not None:
                            # 儲存查詢結果到 session state
                            st.session_state.query_result = result_df
                            st.session_state.query_config = query_config
                            st.success(f"查詢完成！找到 {len(result_df)} 筆記錄")
                        else:
                            st.error("查詢失敗，請檢查查詢條件")

            with col2:
                if st.button("🔄 重設條件"):
                    # 清除 session state 中的查詢結果
                    if "query_result" in st.session_state:
                        del st.session_state.query_result
                    if "query_config" in st.session_state:
                        del st.session_state.query_config
                    st.rerun()

        # 顯示查詢結果
        if "query_result" in st.session_state and "query_config" in st.session_state:
            st.markdown("---")
            show_query_results(
                st.session_state.query_result, st.session_state.query_config
            )

    except Exception as e:
        st.error(f"資料查詢功能發生錯誤: {e}")
        with st.expander("錯誤詳情"):
            st.code(str(e))
