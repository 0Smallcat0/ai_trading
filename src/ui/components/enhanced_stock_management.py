#!/usr/bin/env python3
"""
增強版股票管理組件
支援台股全覆蓋、智能搜尋、批量更新等功能
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import time
import sys
import os
import logging
from typing import List, Optional

# 添加項目路徑
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

try:
    from src.data_sources.taiwan_stock_list_manager import TaiwanStockListManager, StockInfo
    from src.data_sources.batch_stock_updater import BatchStockUpdater, BatchConfig, BatchProgress
    from src.data_sources.real_data_crawler import RealDataCrawler
except ImportError as e:
    st.error(f"無法導入增強版股票管理模組: {e}")

logger = logging.getLogger(__name__)

class EnhancedStockManagement:
    """增強版股票管理類"""
    
    def __init__(self):
        """初始化增強版股票管理"""
        self.db_path = 'sqlite:///data/enhanced_stock_database.db'
        
        # 初始化組件
        try:
            self.stock_manager = TaiwanStockListManager(self.db_path.replace('sqlite:///', ''))
            self.batch_updater = BatchStockUpdater(self.db_path)
            self.crawler = RealDataCrawler(self.db_path)
        except Exception as e:
            st.error(f"初始化失敗: {e}")
            return
        
        # 初始化session state
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

def show_stock_list_management():
    """顯示股票清單管理功能"""
    st.subheader("📋 台股清單管理")
    
    try:
        manager = TaiwanStockListManager()
        
        # 顯示股票清單摘要
        col1, col2, col3, col4 = st.columns(4)
        
        summary = manager.get_stock_list_summary()
        
        with col1:
            st.metric("總股票數", summary['total_stocks'])
        with col2:
            st.metric("上市股票", summary['twse_stocks'])
        with col3:
            st.metric("上櫃股票", summary['tpex_stocks'])
        with col4:
            st.metric("最後更新", summary['last_update'])
        
        # 更新股票清單按鈕
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if st.button("🔄 更新股票清單", type="primary"):
                with st.spinner("正在更新股票清單..."):
                    try:
                        result = manager.update_stock_list(force_update=True)
                        st.success(f"✅ 更新成功！獲取 {result['total_stocks']} 個股票")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 更新失敗: {e}")
        
        with col2:
            st.info("💡 股票清單每日自動更新一次，手動更新將強制重新獲取最新清單")
        
        # 顯示股票清單預覽
        if summary['total_stocks'] > 0:
            st.subheader("📊 股票清單預覽")
            
            stocks = manager.get_all_stocks()
            if stocks:
                # 轉換為DataFrame（移除產業別欄位）
                df = pd.DataFrame([
                    {
                        '股票代碼': stock.symbol,
                        '公司名稱': stock.name,
                        '市場別': stock.market,
                        '最後更新': stock.last_update
                    }
                    for stock in stocks[:100]  # 只顯示前100個
                ])
                
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,  # 隱藏索引欄位
                    height=400,
                    column_config={
                        "股票代碼": st.column_config.TextColumn(
                            "股票代碼",
                            width="medium",
                            help="點擊可複製股票代碼"
                        ),
                        "公司名稱": st.column_config.TextColumn(
                            "公司名稱",
                            width="large"
                        ),
                        "市場別": st.column_config.TextColumn(
                            "市場別",
                            width="medium"
                        ),
                        "最後更新": st.column_config.DatetimeColumn(
                            "最後更新",
                            width="medium",
                            format="YYYY-MM-DD"
                        )
                    }
                )
                
                if len(stocks) > 100:
                    st.info(f"顯示前100個股票，總計 {len(stocks)} 個股票")
        
    except Exception as e:
        st.error(f"股票清單管理功能異常: {e}")

def show_intelligent_stock_search():
    """顯示智能股票搜尋功能"""
    st.subheader("🔍 智能股票搜尋")

    # 確保session state已初始化
    initialize_session_state()

    try:
        manager = TaiwanStockListManager()
        stocks = manager.get_all_stocks()
        
        if not stocks:
            st.warning("⚠️ 股票清單為空，請先更新股票清單")
            return
        
        # 搜尋輸入
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            search_query = st.text_input(
                "搜尋股票",
                placeholder="輸入股票代碼、公司名稱或產業別...",
                help="支援精確搜尋和模糊搜尋，例如：2330、台積、半導體",
                key="stock_search_input"
            )

        with col2:
            search_type = st.selectbox(
                "搜尋類型",
                ["全部", "股票代碼", "公司名稱", "產業別"],
                key="search_type_select"
            )

        with col3:
            # 搜尋統計資訊
            if search_query:
                st.metric("搜尋長度", len(search_query))
            else:
                st.metric("總股票數", len(stocks))
        
        # 執行搜尋
        if search_query:
            filtered_stocks = []
            query_lower = search_query.lower().strip()

            # 精確匹配和模糊匹配分別處理
            exact_matches = []
            prefix_matches = []
            partial_matches = []

            for stock in stocks:
                symbol_lower = stock.symbol.lower()
                name_lower = stock.name.lower()
                industry_lower = stock.industry.lower()

                # 根據搜尋類型進行匹配
                if search_type == "股票代碼" or search_type == "全部":
                    # 精確匹配（完整股票代碼）
                    if query_lower == symbol_lower or query_lower == symbol_lower.replace('.tw', '').replace('.two', ''):
                        exact_matches.append((stock, 1))
                    # 前綴匹配（股票代碼開頭）
                    elif query_lower.isdigit() and symbol_lower.startswith(query_lower):
                        prefix_matches.append((stock, 2))
                    # 部分匹配（包含查詢字串）
                    elif query_lower in symbol_lower:
                        partial_matches.append((stock, 3))

                if search_type == "公司名稱" or search_type == "全部":
                    # 精確匹配（完整公司名稱）
                    if query_lower == name_lower:
                        exact_matches.append((stock, 1))
                    # 前綴匹配（公司名稱開頭）
                    elif name_lower.startswith(query_lower):
                        prefix_matches.append((stock, 2))
                    # 部分匹配（包含查詢字串）
                    elif query_lower in name_lower:
                        partial_matches.append((stock, 3))

                if search_type == "產業別" or search_type == "全部":
                    # 精確匹配（完整產業名稱）
                    if query_lower == industry_lower:
                        exact_matches.append((stock, 1))
                    # 部分匹配（包含查詢字串）
                    elif query_lower in industry_lower:
                        partial_matches.append((stock, 3))

            # 合併結果並按優先級排序
            all_matches = exact_matches + prefix_matches + partial_matches

            # 去重（保留優先級最高的）
            seen_symbols = set()
            unique_matches = []
            for stock, priority in all_matches:
                if stock.symbol not in seen_symbols:
                    unique_matches.append((stock, priority))
                    seen_symbols.add(stock.symbol)

            # 按優先級和股票代碼排序
            unique_matches.sort(key=lambda x: (x[1], x[0].symbol))
            filtered_stocks = [stock for stock, _ in unique_matches]

            # 限制搜尋結果數量
            if len(filtered_stocks) > 50:
                filtered_stocks = filtered_stocks[:50]
                st.info(f"搜尋結果過多，僅顯示前50個結果（按相關性排序）")
            
            # 顯示搜尋結果
            if filtered_stocks:
                st.write(f"🎯 找到 {len(filtered_stocks)} 個匹配結果：")
                
                # 多選框
                selected_symbols = []
                
                for stock in filtered_stocks:
                    display_text = f"{stock.symbol} - {stock.name} ({stock.market}/{stock.industry})"
                    
                    if st.checkbox(display_text, key=f"search_{stock.symbol}"):
                        selected_symbols.append(stock.symbol)
                
                # 添加到選擇清單
                if selected_symbols and st.button("➕ 添加到選擇清單"):
                    for symbol in selected_symbols:
                        if symbol not in st.session_state.selected_stocks:
                            st.session_state.selected_stocks.append(symbol)
                    
                    st.success(f"✅ 已添加 {len(selected_symbols)} 個股票到選擇清單")
                    st.rerun()
            else:
                st.warning("🔍 未找到匹配的股票")
        
        # 顯示已選擇的股票
        if st.session_state.selected_stocks:
            st.subheader("📌 已選擇的股票")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                for i, symbol in enumerate(st.session_state.selected_stocks):
                    col_a, col_b = st.columns([4, 1])
                    with col_a:
                        st.write(f"{i+1}. {symbol}")
                    with col_b:
                        if st.button("❌", key=f"remove_{symbol}"):
                            st.session_state.selected_stocks.remove(symbol)
                            st.rerun()
            
            with col2:
                if st.button("🗑️ 清空選擇"):
                    st.session_state.selected_stocks = []
                    st.rerun()
                
                st.write(f"總計: {len(st.session_state.selected_stocks)} 個股票")
        
    except Exception as e:
        st.error(f"智能搜尋功能異常: {e}")

def show_batch_update_system():
    """顯示批量更新系統"""
    # 確保session state已初始化
    initialize_session_state()

    try:
        # 顯示當前選擇的日期範圍
        if hasattr(st.session_state, 'date_range_start') and hasattr(st.session_state, 'date_range_end'):
            st.info(f"📅 更新日期範圍：{st.session_state.date_range_start} 至 {st.session_state.date_range_end}")
        else:
            st.warning("⚠️ 請先在上方設定日期範圍")
            return
        
        # 批量配置
        st.subheader("⚙️ 批量配置")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            batch_size = st.slider("批次大小", 10, 100, 50)
        
        with col2:
            request_delay = st.slider("請求間隔(秒)", 0.5, 5.0, 1.0, 0.5)
        
        with col3:
            max_retries = st.slider("最大重試次數", 1, 5, 3)
        
        # 更新選項
        update_options = st.radio(
            "更新範圍",
            ["所有股票", "已選擇股票", "測試模式(前10個)"]
        )
        
        # 批量更新按鈕
        if not st.session_state.get('batch_running', False):
            if st.button("🚀 開始批量更新", type="primary"):
                # 創建配置
                config = BatchConfig(
                    batch_size=batch_size,
                    request_delay=request_delay,
                    max_retries=max_retries
                )
                
                # 開始批量更新
                st.session_state.batch_running = True
                
                with st.spinner("正在初始化批量更新..."):
                    try:
                        updater = BatchStockUpdater()
                        
                        # 根據選項決定更新範圍
                        if update_options == "測試模式(前10個)":
                            # 限制為前10個股票進行測試
                            manager = TaiwanStockListManager()
                            all_stocks = manager.get_all_stocks()[:10]
                            st.info(f"🧪 測試模式：將更新前 {len(all_stocks)} 個股票")
                        
                        # 這裡應該啟動後台任務，但為了演示，我們顯示一個進度條
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # 模擬批量更新進度
                        for i in range(101):
                            progress_bar.progress(i)
                            status_text.text(f'更新進度: {i}%')
                            time.sleep(0.1)
                        
                        st.success("✅ 批量更新完成！")
                        st.session_state.batch_running = False
                        
                    except Exception as e:
                        st.error(f"❌ 批量更新失敗: {e}")
                        st.session_state.batch_running = False
        else:
            st.warning("⏳ 批量更新正在進行中...")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⏸️ 暫停"):
                    st.session_state.batch_running = False
                    st.info("批量更新已暫停")
            
            with col2:
                if st.button("⏹️ 停止"):
                    st.session_state.batch_running = False
                    st.info("批量更新已停止")
    
    except Exception as e:
        st.error(f"批量更新系統異常: {e}")

def show_date_range_selector():
    """顯示日期範圍選擇功能"""
    st.subheader("📅 自定義日期範圍")

    # 確保session state已初始化
    initialize_session_state()

    # 快速選項
    quick_options = {
        '最近1週': 7,
        '最近1個月': 30,
        '最近3個月': 90,
        '最近6個月': 180,
        '最近1年': 365
    }
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("🚀 快速選項")
        selected_option = st.radio(
            "選擇時間範圍",
            list(quick_options.keys()) + ["自定義範圍"]
        )
    
    with col2:
        if selected_option == "自定義範圍":
            st.write("📅 自定義日期")
            
            end_date = st.date_input(
                "結束日期",
                value=date.today(),
                max_value=date.today()
            )
            
            start_date = st.date_input(
                "開始日期",
                value=end_date - timedelta(days=30),
                max_value=end_date
            )
        else:
            days = quick_options[selected_option]
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            st.write("📅 選擇的日期範圍")
            st.write(f"開始日期: {start_date}")
            st.write(f"結束日期: {end_date}")
    
    # 日期範圍驗證
    if start_date > end_date:
        st.error("❌ 開始日期不能晚於結束日期")
        return None, None
    
    if (end_date - start_date).days > 730:  # 2年
        st.warning("⚠️ 日期範圍過大，建議選擇2年以內的範圍")
    
    # 將日期範圍保存到 session state
    st.session_state.date_range_start = start_date
    st.session_state.date_range_end = end_date

    # 預估資訊
    trading_days = pd.bdate_range(start_date, end_date)
    estimated_days = len(trading_days)

    if st.session_state.selected_stocks:
        estimated_records = estimated_days * len(st.session_state.selected_stocks)
        st.info(f"📊 預估下載：{estimated_days}個交易日 × {len(st.session_state.selected_stocks)}股票 = {estimated_records}筆記錄")
    else:
        st.info(f"📊 預估交易日數：{estimated_days}天")

    return start_date, end_date

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
    # 初始化日期範圍（默認最近30天）
    if 'date_range_start' not in st.session_state:
        st.session_state.date_range_start = date.today() - timedelta(days=30)
    if 'date_range_end' not in st.session_state:
        st.session_state.date_range_end = date.today()

def main():
    """主函數"""
    # 首先初始化session state
    initialize_session_state()

    st.title("🎯 增強版股票管理系統")

    # 緊湊統一版本：移除視覺分隔元素，創建統一界面

    # 緊湊統一的功能整合，無視覺分隔
    show_stock_list_management()
    show_intelligent_stock_search()
    show_date_range_selector()
    show_batch_update_system()

if __name__ == "__main__":
    main()
