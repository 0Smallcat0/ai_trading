# -*- coding: utf-8 -*-
"""
數據管理 UI 組件

此模組提供數據管理的 Streamlit 界面組件，包括：
- 數據下載功能
- 數據查詢和檢視
- 數據匯出功能
- 系統狀態監控

Author: AI Trading System
Version: 1.0.0
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta
import sys
import os
import io

# 添加項目路徑
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

try:
    from src.data_sources.core_data_downloader import CoreDataDownloader
    from src.data_sources.data_query_service import DataQueryService
    
    # 初始化核心數據服務
    data_downloader = CoreDataDownloader()
    data_query_service = DataQueryService()

except ImportError as e:
    st.error(f"無法導入數據管理服務: {e}")
    data_downloader = None
    data_query_service = None


def show():
    """組件標準入口函數"""
    show_data_management()


def initialize_session_state():
    """初始化 session state 變數"""
    if 'download_progress' not in st.session_state:
        st.session_state.download_progress = {}
    if 'query_results' not in st.session_state:
        st.session_state.query_results = pd.DataFrame()


def show_data_management():
    """顯示數據管理主界面"""
    # 創建子頁面導航
    tab1, tab2 = st.tabs(["📥 數據下載", "📊 數據檢視"])

    with tab1:
        show_data_download_tab()

    with tab2:
        show_data_view_tab()


def show_data_download_tab():
    """顯示數據下載標籤頁"""
    try:
        from src.ui.pages.data_download import show_data_download_page
        show_data_download_page()
    except ImportError as e:
        st.error(f"❌ 無法載入數據下載頁面: {e}")
        st.info("請確保 data_download.py 模組已正確安裝")


def show_data_view_tab():
    """顯示數據檢視標籤頁"""
    try:
        from src.ui.pages.data_view import show_data_view_page
        show_data_view_page()
    except ImportError as e:
        st.error(f"❌ 無法載入數據檢視頁面: {e}")
        st.info("請確保 data_view.py 模組已正確安裝")


def show_data_management_legacy():
    """顯示數據管理主界面 (舊版實現)"""
    st.title("📊 數據管理")
    
    if not data_downloader or not data_query_service:
        st.error("❌ 數據管理服務不可用，請檢查系統配置")
        return
    
    # 初始化 session state
    initialize_session_state()
    
    # 創建標籤頁
    tab1, tab2, tab3 = st.tabs(["📥 資料更新", "📈 資料檢視", "📊 系統狀態"])
    
    with tab1:
        show_data_download_section()
    
    with tab2:
        show_data_query_section()
    
    with tab3:
        show_system_status()


def show_data_download_section():
    """顯示數據下載功能"""
    st.subheader("📥 股票數據下載")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 股票代碼輸入
        symbol = st.text_input(
            "股票代碼",
            placeholder="例如: 2330.TW",
            help="請輸入完整的股票代碼，台股請加上 .TW 後綴"
        )
        
        # 日期範圍選擇
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            start_date = st.date_input(
                "開始日期",
                value=date.today() - timedelta(days=30),
                max_value=date.today()
            )
        
        with col_date2:
            end_date = st.date_input(
                "結束日期",
                value=date.today(),
                max_value=date.today()
            )
        
        # 數據源選擇
        data_sources = st.multiselect(
            "數據源",
            options=['yahoo', 'twse'],
            default=['yahoo', 'twse'],
            help="選擇要使用的數據源"
        )
    
    with col2:
        st.info("""
        **使用說明：**
        
        1. 輸入股票代碼（如 2330.TW）
        2. 選擇日期範圍
        3. 選擇數據源
        4. 點擊下載按鈕
        
        **支援的數據源：**
        - Yahoo Finance
        - TWSE 台灣證交所
        """)
    
    # 下載按鈕
    if st.button("🚀 開始下載", type="primary"):
        if not symbol:
            st.error("請輸入股票代碼")
        elif start_date > end_date:
            st.error("開始日期不能晚於結束日期")
        else:
            download_stock_data(symbol, str(start_date), str(end_date), data_sources)


def download_stock_data(symbol: str, start_date: str, end_date: str, sources: list):
    """執行股票數據下載"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("🔄 開始下載數據...")
        progress_bar.progress(10)
        
        # 下載數據
        df = data_downloader.download_stock_data(symbol, start_date, end_date, sources)
        progress_bar.progress(60)
        
        if df.empty:
            st.error(f"❌ 無法獲取 {symbol} 的數據")
            return
        
        status_text.text("🔄 驗證數據品質...")
        progress_bar.progress(80)
        
        # 驗證數據
        df = data_downloader.validate_data(df)
        
        status_text.text("🔄 保存到數據庫...")
        progress_bar.progress(90)
        
        # 保存到數據庫
        success = data_downloader.save_to_database(df)
        progress_bar.progress(100)
        
        if success:
            status_text.text("✅ 下載完成！")
            st.success(f"✅ 成功下載 {symbol} 數據：{len(df)} 筆記錄")
            
            # 顯示數據預覽
            st.subheader("📊 數據預覽")
            st.dataframe(df.head(10))
            
            # 顯示基本統計
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("記錄數", len(df))
            with col2:
                st.metric("最新收盤價", f"{df['close'].iloc[-1]:.2f}")
            with col3:
                st.metric("期間最高", f"{df['high'].max():.2f}")
            with col4:
                st.metric("期間最低", f"{df['low'].min():.2f}")
        else:
            status_text.text("❌ 保存失敗")
            st.error("❌ 數據保存失敗，請檢查數據庫連接")
    
    except Exception as e:
        status_text.text("❌ 下載失敗")
        st.error(f"❌ 下載失敗：{e}")
    
    finally:
        progress_bar.empty()


def show_data_query_section():
    """顯示數據查詢功能"""
    st.subheader("📈 股票數據查詢")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 獲取可用股票列表
        available_symbols = data_query_service.get_available_symbols()
        
        if not available_symbols:
            st.warning("⚠️ 數據庫中沒有股票數據，請先下載數據")
            return
        
        # 股票選擇
        selected_symbol = st.selectbox(
            "選擇股票",
            options=[''] + available_symbols,
            help="選擇要查詢的股票代碼"
        )
        
        # 日期範圍
        if selected_symbol:
            date_range = data_query_service.get_date_range(selected_symbol)
            if date_range:
                min_date = pd.to_datetime(date_range['min_date']).date()
                max_date = pd.to_datetime(date_range['max_date']).date()
            else:
                min_date = date.today() - timedelta(days=365)
                max_date = date.today()
        else:
            min_date = date.today() - timedelta(days=365)
            max_date = date.today()
        
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            query_start_date = st.date_input(
                "查詢開始日期",
                value=min_date,
                min_value=min_date,
                max_value=max_date
            )
        
        with col_date2:
            query_end_date = st.date_input(
                "查詢結束日期",
                value=max_date,
                min_value=min_date,
                max_value=max_date
            )
        
        # 記錄數限制
        limit = st.number_input(
            "最大記錄數",
            min_value=10,
            max_value=10000,
            value=1000,
            step=100
        )
    
    with col2:
        # 顯示數據摘要
        summary = data_query_service.get_data_summary()
        if summary:
            st.info(f"""
            **數據庫摘要：**
            
            📊 總記錄數：{summary.get('total_records', 0):,}
            🏢 股票數量：{summary.get('unique_symbols', 0)}
            🔄 最新更新：{summary.get('latest_update', 'N/A')}
            """)
    
    # 查詢按鈕
    if st.button("🔍 查詢數據", type="primary"):
        if not selected_symbol:
            st.error("請選擇股票代碼")
        else:
            query_stock_data(selected_symbol, str(query_start_date), str(query_end_date), limit)


def query_stock_data(symbol: str, start_date: str, end_date: str, limit: int):
    """執行股票數據查詢"""
    try:
        # 查詢數據
        df = data_query_service.query_stock_data(symbol, start_date, end_date, limit)
        
        if df.empty:
            st.warning("⚠️ 未找到符合條件的數據")
            return
        
        # 保存查詢結果到 session state
        st.session_state.query_results = df
        
        st.success(f"✅ 查詢完成：找到 {len(df)} 筆記錄")
        
        # 顯示數據表格
        st.subheader("📊 查詢結果")
        st.dataframe(df)
        
        # 顯示圖表
        if len(df) > 1:
            show_stock_chart(df, symbol)
        
        # 匯出功能
        show_export_options(df)
    
    except Exception as e:
        st.error(f"❌ 查詢失敗：{e}")


def show_stock_chart(df: pd.DataFrame, symbol: str):
    """顯示股票圖表"""
    st.subheader("📈 價格走勢圖")
    
    # 創建 K 線圖
    fig = go.Figure(data=go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name=symbol
    ))
    
    fig.update_layout(
        title=f"{symbol} 股價走勢",
        yaxis_title="價格",
        xaxis_title="日期",
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)


def show_export_options(df: pd.DataFrame):
    """顯示匯出選項"""
    st.subheader("📤 數據匯出")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📄 匯出 CSV"):
            csv_content = data_query_service.export_to_csv(df)
            if csv_content:
                st.download_button(
                    label="⬇️ 下載 CSV 檔案",
                    data=csv_content,
                    file_name=f"stock_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
    
    with col2:
        if st.button("📋 匯出 JSON"):
            json_content = data_query_service.export_to_json(df)
            if json_content:
                st.download_button(
                    label="⬇️ 下載 JSON 檔案",
                    data=json_content,
                    file_name=f"stock_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )


def show_system_status():
    """顯示系統狀態"""
    st.subheader("📊 系統狀態")
    
    try:
        # 獲取數據摘要
        summary = data_query_service.get_data_summary()
        
        if summary:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    label="📊 總記錄數",
                    value=f"{summary.get('total_records', 0):,}"
                )
            
            with col2:
                st.metric(
                    label="🏢 股票數量",
                    value=summary.get('unique_symbols', 0)
                )
            
            with col3:
                latest_update = summary.get('latest_update')
                if latest_update:
                    update_time = pd.to_datetime(latest_update).strftime('%Y-%m-%d %H:%M')
                else:
                    update_time = "無數據"
                st.metric(
                    label="🔄 最新更新",
                    value=update_time
                )
            
            # 數據源統計
            if summary.get('data_sources'):
                st.subheader("📈 數據源統計")
                source_df = pd.DataFrame(
                    list(summary['data_sources'].items()),
                    columns=['數據源', '記錄數']
                )
                st.dataframe(source_df, use_container_width=True)
        else:
            st.info("📊 數據庫中暫無數據")
    
    except Exception as e:
        st.error(f"❌ 獲取系統狀態失敗：{e}")


# 主函數
def main():
    """主函數"""
    show_data_management()


if __name__ == "__main__":
    main()
