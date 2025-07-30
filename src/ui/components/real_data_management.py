#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真實數據管理組件
==============

整合到現有Web UI中的真實數據管理功能，包括：
- 手動資料更新功能
- 即時更新進度顯示
- 股票資料檢視頁面

Author: AI Trading System
Date: 2025-01-28
Version: 1.0
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

def initialize_session_state():
    """初始化session state變數"""
    if 'stock_search_results' not in st.session_state:
        st.session_state.stock_search_results = []
    if 'selected_stocks' not in st.session_state:
        st.session_state.selected_stocks = []
    if 'recent_selections' not in st.session_state:
        st.session_state.recent_selections = []
    if 'batch_progress' not in st.session_state:
        st.session_state.batch_progress = None
    if 'batch_running' not in st.session_state:
        st.session_state.batch_running = False


def show_enhanced_stock_management():
    """顯示增強版股票管理功能"""
    # 確保session state已初始化
    initialize_session_state()

    try:
        from src.ui.components.enhanced_stock_management import (
            show_stock_list_management,
            show_intelligent_stock_search,
            show_batch_update_system,
            show_date_range_selector
        )

        # 選項卡
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 台股全覆蓋",
            "🔍 智能搜尋",
            "🚀 批量更新",
            "📅 日期範圍"
        ])

        with tab1:
            show_stock_list_management()

        with tab2:
            show_intelligent_stock_search()

        with tab3:
            show_batch_update_system()

        with tab4:
            show_date_range_selector()

    except ImportError as e:
        st.error(f"無法載入增強版股票管理功能: {e}")
        st.warning("⚠️ 請檢查增強版股票管理模組是否正確安裝")

def show_manual_update_section():
    """顯示手動資料更新功能 - 使用增強版功能"""
    # 使用增強版股票管理功能
    show_enhanced_stock_management()

# execute_manual_update 函數已移除，因為已改用增強版股票管理功能

def show_system_status():
    """顯示系統狀態"""
    if not real_data_service:
        st.error("❌ 真實數據服務不可用")
        return
    
    with st.expander("📊 系統狀態詳情", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            # 系統健康狀態
            health = real_data_service.health_check()
            st.write("🏥 **系統健康狀態**")
            st.write(f"狀態: {health['status']}")
            st.write(f"資料庫記錄: {health.get('database_records', 0):,} 筆")
            st.write(f"股票覆蓋: {health.get('stock_coverage', 0)} 個")
        
        with col2:
            # 數據品質指標
            quality_metrics = real_data_service.get_quality_metrics()
            st.write("📊 **數據品質指標**")
            st.write(f"完整性: {quality_metrics.get('completeness', 0):.1f}%")
            st.write(f"準確性: {quality_metrics.get('accuracy', 0):.1f}%")
            st.write(f"最後更新: {quality_metrics.get('last_update', 'N/A')}")

def show_stock_data_viewer():
    """顯示股票資料檢視頁面"""
    st.subheader("📈 股票資料檢視")
    
    if not real_data_service:
        st.error("❌ 真實數據服務不可用")
        return
    
    # 股票選擇
    available_symbols = real_data_service.get_available_symbols()
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        selected_symbol = st.selectbox(
            "選擇股票代碼",
            available_symbols,
            index=0 if available_symbols else None,
            help="選擇要檢視的股票代碼"
        )
    
    with col2:
        date_range = st.selectbox(
            "時間範圍",
            ["最近7天", "最近30天", "最近90天", "自定義"],
            index=1
        )
    
    with col3:
        if st.button("🔍 查詢資料", type="primary"):
            st.rerun()
    
    # 自定義日期範圍
    if date_range == "自定義":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("開始日期", value=date.today() - timedelta(days=30))
        with col2:
            end_date = st.date_input("結束日期", value=date.today())
    else:
        # 根據選擇設置日期範圍
        days_map = {"最近7天": 7, "最近30天": 30, "最近90天": 90}
        days = days_map.get(date_range, 30)
        start_date = date.today() - timedelta(days=days)
        end_date = date.today()
    
    if selected_symbol:
        # 獲取股票數據
        with st.spinner(f"正在載入 {selected_symbol} 的資料..."):
            df = real_data_service.get_stock_data(selected_symbol, start_date, end_date)
        
        if not df.empty:
            # 顯示基本信息
            latest_data = df.iloc[-1]
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("最新收盤價", f"{latest_data['close']:.2f}")
            with col2:
                if len(df) > 1:
                    prev_close = df.iloc[-2]['close']
                    change = latest_data['close'] - prev_close
                    change_pct = (change / prev_close) * 100
                    st.metric("漲跌", f"{change:+.2f}", f"{change_pct:+.2f}%")
                else:
                    st.metric("漲跌", "N/A")
            with col3:
                st.metric("成交量", f"{latest_data['volume']:,}")
            with col4:
                st.metric("資料筆數", len(df))
            
            # 創建圖表
            fig = create_stock_chart(df, selected_symbol)
            st.plotly_chart(fig, use_container_width=True)
            
            # 顯示詳細數據表格
            st.subheader("📋 詳細資料")
            
            # 格式化數據顯示
            display_df = df.copy()
            display_df['date'] = pd.to_datetime(display_df['date']).dt.strftime('%Y-%m-%d')
            display_df = display_df[['date', 'open', 'high', 'low', 'close', 'volume']].round(2)
            display_df.columns = ['日期', '開盤價', '最高價', '最低價', '收盤價', '成交量']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # 資料匯出功能
            show_export_options(df, selected_symbol)
            
        else:
            st.warning(f"⚠️ 未找到 {selected_symbol} 在指定時間範圍內的資料")

def create_stock_chart(df, symbol):
    """創建股票圖表"""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(f'{symbol} 股價走勢', '成交量'),
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3]
    )
    
    # K線圖
    fig.add_trace(
        go.Candlestick(
            x=df['date'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='K線'
        ),
        row=1, col=1
    )
    
    # 成交量
    fig.add_trace(
        go.Bar(
            x=df['date'],
            y=df['volume'],
            name='成交量',
            marker_color='rgba(158,202,225,0.8)'
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        title=f'{symbol} 股票資料分析',
        xaxis_rangeslider_visible=False,
        height=600,
        showlegend=False
    )
    
    fig.update_xaxes(title_text="日期", row=2, col=1)
    fig.update_yaxes(title_text="價格 (TWD)", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)
    
    return fig

def show_export_options(df, symbol):
    """顯示資料匯出選項"""
    st.subheader("📤 資料匯出")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # CSV匯出
        csv_data = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📄 匯出為 CSV",
            data=csv_data,
            file_name=f"{symbol}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    with col2:
        # Excel匯出
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=symbol, index=False)
        excel_data = excel_buffer.getvalue()
        
        st.download_button(
            label="📊 匯出為 Excel",
            data=excel_data,
            file_name=f"{symbol}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with col3:
        # JSON匯出
        json_data = df.to_json(orient='records', date_format='iso', indent=2)
        st.download_button(
            label="🔧 匯出為 JSON",
            data=json_data,
            file_name=f"{symbol}_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json"
        )

def show():
    """主要顯示函數 - 整合所有功能"""
    st.title("📊 真實數據管理")
    st.markdown("---")
    
    # 創建標籤頁
    tab1, tab2 = st.tabs(["🔄 資料更新", "📈 資料檢視"])
    
    with tab1:
        show_manual_update_section()
        st.markdown("---")
        show_system_status()
    
    with tab2:
        show_stock_data_viewer()

if __name__ == "__main__":
    show()
