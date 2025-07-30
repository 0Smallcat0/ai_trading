#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增強版數據查看器
==============

使用增強版資料庫的股票數據查看器組件。
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta
import io
from sqlalchemy import text

def show_enhanced_stock_data_viewer():
    """顯示增強版股票資料檢視頁面"""
    st.subheader("📊 增強版股票資料檢視")

    try:
        from src.database.unified_storage_fixed import UnifiedStorageFixed
        # 使用正確的資料庫路徑
        enhanced_storage = UnifiedStorageFixed("sqlite:///data/enhanced_stock_database.db")
    except Exception as e:
        st.error(f"❌ 無法連接增強版資料庫: {e}")
        return

    # 獲取可用的股票代碼
    try:
        with enhanced_storage.engine.connect() as conn:
            # 首先嘗試 stock_daily_prices 表
            try:
                query = text("SELECT DISTINCT symbol FROM stock_daily_prices ORDER BY symbol")
                result = conn.execute(query)
                available_symbols = [row[0] for row in result.fetchall()]
            except:
                # 如果失敗，嘗試 real_stock_data 表
                query = text("SELECT DISTINCT symbol FROM real_stock_data ORDER BY symbol")
                result = conn.execute(query)
                available_symbols = [row[0] for row in result.fetchall()]
    except Exception as e:
        st.error(f"❌ 無法獲取股票代碼列表: {e}")
        return

    if not available_symbols:
        st.warning("⚠️ 資料庫中沒有股票數據")
        return

    # 獲取股票名稱映射
    try:
        from src.data_sources.taiwan_stock_list_manager import TaiwanStockListManager
        stock_manager = TaiwanStockListManager()
        all_stocks = stock_manager.get_all_stocks()

        # 建立股票代號到名稱的映射
        symbol_to_name = {}
        for stock in all_stocks:
            symbol_to_name[stock.symbol] = stock.name

        # 創建顯示選項：「股票代號 - 公司名稱」格式
        display_options = []
        symbol_mapping = {}  # 顯示文字到股票代號的映射

        for symbol in available_symbols:
            company_name = symbol_to_name.get(symbol, "未知公司")
            display_text = f"{symbol} - {company_name}"
            display_options.append(display_text)
            symbol_mapping[display_text] = symbol

    except Exception as e:
        st.warning(f"⚠️ 無法獲取股票名稱資訊: {e}")
        # 如果無法獲取股票名稱，則使用原始的股票代號
        display_options = available_symbols
        symbol_mapping = {symbol: symbol for symbol in available_symbols}

    # 股票選擇和時間範圍設置
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        selected_display = st.selectbox(
            "選擇股票",
            display_options,
            index=0,
            help="選擇要查看的股票（代碼 - 公司名稱）"
        )

        # 獲取實際的股票代號
        selected_symbol = symbol_mapping.get(selected_display, available_symbols[0] if available_symbols else None)
    
    with col2:
        time_range = st.selectbox(
            "時間範圍",
            ["最近7天", "最近30天", "最近90天", "全部資料"],
            index=1
        )
    
    with col3:
        if st.button("🔍 查詢資料", type="primary"):
            st.rerun()
    
    if selected_symbol:
        try:
            # 查詢股票數據 - 適應不同的表結構
            with enhanced_storage.engine.connect() as conn:
                # 首先嘗試 stock_daily_prices 表
                try:
                    query = text("""
                        SELECT symbol, date, open_price as open, high_price as high,
                               low_price as low, close_price as close, volume,
                               data_source, created_at
                        FROM stock_daily_prices
                        WHERE symbol = :symbol
                        ORDER BY date ASC
                    """)
                    result = conn.execute(query, {"symbol": selected_symbol})
                    rows = result.fetchall()
                except:
                    # 如果失敗，嘗試 real_stock_data 表
                    query = text("""
                        SELECT symbol, date, open, high, low, close, volume,
                               source as data_source, created_at
                        FROM real_stock_data
                        WHERE symbol = :symbol
                        ORDER BY date ASC
                    """)
                    result = conn.execute(query, {"symbol": selected_symbol})
                    rows = result.fetchall()
                
                if rows:
                    # 轉換為DataFrame
                    stock_data = pd.DataFrame(rows, columns=[
                        'symbol', 'date', 'open', 'high', 'low', 'close', 
                        'volume', 'adjusted_close', 'data_source', 'created_at'
                    ])
                    
                    # 確保數據類型正確
                    stock_data['date'] = pd.to_datetime(stock_data['date'])
                    for col in ['open', 'high', 'low', 'close', 'adjusted_close']:
                        stock_data[col] = pd.to_numeric(stock_data[col], errors='coerce')
                    stock_data['volume'] = pd.to_numeric(stock_data['volume'], errors='coerce')
                    
                    # 根據時間範圍過濾數據
                    if time_range == "最近7天":
                        filtered_data = stock_data.tail(7)
                    elif time_range == "最近30天":
                        filtered_data = stock_data.tail(30)
                    elif time_range == "最近90天":
                        filtered_data = stock_data.tail(90)
                    else:
                        filtered_data = stock_data
                    
                    if not filtered_data.empty:
                        # 顯示基本資訊
                        show_stock_metrics(filtered_data, selected_symbol)

                        # 顯示圖表
                        show_stock_chart(filtered_data, selected_symbol)

                        # 移除詳細資料表格以簡化頁面
                        # show_data_table(filtered_data)  # 已註釋移除

                        # 顯示資料匯出選項
                        show_export_options(filtered_data, selected_symbol, time_range)
                    
                    else:
                        st.warning(f"⚠️ 沒有找到 {selected_symbol} 的資料")
                
                else:
                    st.warning(f"⚠️ 資料庫中沒有 {selected_symbol} 的資料")
                    
                    # 顯示可用的股票代碼
                    st.info(f"可用的股票代碼: {', '.join(available_symbols[:10])}")
                    if len(available_symbols) > 10:
                        st.info(f"...等共 {len(available_symbols)} 個股票代碼")
                
        except Exception as e:
            st.error(f"❌ 載入股票資料時發生錯誤: {e}")
            st.error(f"錯誤詳情: {str(e)}")

def show_stock_metrics(data, symbol):
    """顯示股票基本指標"""
    latest_data = data.iloc[-1]
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("股票代碼", symbol)
    
    with col2:
        st.metric("最新收盤價", f"{latest_data['close']:.2f}")
    
    with col3:
        if len(data) > 1:
            prev_close = data.iloc[-2]['close']
            change = latest_data['close'] - prev_close
            change_pct = (change / prev_close) * 100
            st.metric("漲跌", f"{change:+.2f}", f"{change_pct:+.2f}%")
        else:
            st.metric("漲跌", "N/A")
    
    with col4:
        st.metric("成交量", f"{int(latest_data['volume']):,}")
    
    with col5:
        st.metric("資料筆數", len(data))

def show_stock_chart(data, symbol):
    """顯示股票圖表"""
    st.subheader("📈 股價走勢圖")
    
    # 創建子圖
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=(f'{symbol} 股價走勢', '成交量'),
        row_heights=[0.7, 0.3]
    )
    
    # K線圖
    fig.add_trace(
        go.Candlestick(
            x=data['date'],
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            name="股價"
        ),
        row=1, col=1
    )
    
    # 成交量圖
    fig.add_trace(
        go.Bar(
            x=data['date'],
            y=data['volume'],
            name="成交量",
            marker_color='rgba(158,202,225,0.8)'
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        title=f"{symbol} 股價分析圖表",
        xaxis_rangeslider_visible=False,
        height=600,
        showlegend=False
    )
    
    fig.update_xaxes(title_text="日期", row=2, col=1)
    fig.update_yaxes(title_text="價格 (TWD)", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)

# show_data_table 函數已移除以簡化頁面結構

def show_export_options(data, symbol, time_range):
    """顯示資料匯出選項"""
    st.subheader("💾 資料匯出")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # CSV匯出
        csv_data = data.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📄 下載 CSV",
            data=csv_data,
            file_name=f"{symbol}_{time_range}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    with col2:
        # Excel匯出
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            data.to_excel(writer, sheet_name='股價資料', index=False)
        excel_data = excel_buffer.getvalue()
        
        st.download_button(
            label="📊 下載 Excel",
            data=excel_data,
            file_name=f"{symbol}_{time_range}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with col3:
        # JSON匯出
        json_data = data.to_json(orient='records', date_format='iso', indent=2)
        st.download_button(
            label="🔗 下載 JSON",
            data=json_data,
            file_name=f"{symbol}_{time_range}_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json"
        )

def show_database_status():
    """顯示資料庫狀態"""
    st.subheader("🗄️ 資料庫狀態")
    
    try:
        from src.database.unified_storage_fixed import UnifiedStorageFixed
        enhanced_storage = UnifiedStorageFixed("sqlite:///enhanced_stock_database.db")
        
        with enhanced_storage.engine.connect() as conn:
            # 獲取總記錄數
            total_query = text("SELECT COUNT(*) FROM stock_daily_prices")
            total_records = conn.execute(total_query).scalar()
            
            # 獲取股票數量
            symbols_query = text("SELECT COUNT(DISTINCT symbol) FROM stock_daily_prices")
            total_symbols = conn.execute(symbols_query).scalar()
            
            # 獲取日期範圍
            date_range_query = text("""
                SELECT MIN(date) as min_date, MAX(date) as max_date 
                FROM stock_daily_prices
            """)
            date_result = conn.execute(date_range_query).fetchone()
            
            # 獲取數據來源統計
            source_query = text("""
                SELECT data_source, COUNT(*) as count 
                FROM stock_daily_prices 
                GROUP BY data_source 
                ORDER BY count DESC
            """)
            source_result = conn.execute(source_query).fetchall()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("總記錄數", f"{total_records:,}")
            
            with col2:
                st.metric("股票數量", total_symbols)
            
            with col3:
                if date_result and date_result[0]:
                    st.metric("最早日期", date_result[0])
                else:
                    st.metric("最早日期", "N/A")
            
            with col4:
                if date_result and date_result[1]:
                    st.metric("最新日期", date_result[1])
                else:
                    st.metric("最新日期", "N/A")
            
            # 顯示數據來源統計
            if source_result:
                st.subheader("📊 數據來源統計")
                source_df = pd.DataFrame(source_result, columns=['數據來源', '記錄數'])
                source_df['記錄數'] = source_df['記錄數'].apply(lambda x: f"{x:,}")
                st.dataframe(source_df, use_container_width=True, hide_index=True)
            
    except Exception as e:
        st.error(f"❌ 無法獲取資料庫狀態: {e}")

def main():
    """主函數"""
    st.title("🔍 增強版股票數據查看器")
    
    tab1, tab2 = st.tabs(["📈 股票資料檢視", "🗄️ 資料庫狀態"])
    
    with tab1:
        show_enhanced_stock_data_viewer()
    
    with tab2:
        show_database_status()

if __name__ == "__main__":
    main()
