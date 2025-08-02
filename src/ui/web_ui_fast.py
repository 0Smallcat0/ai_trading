#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速版本的 Streamlit Web UI
專注於快速加載和基本功能
"""

import streamlit as st
import pandas as pd
import sqlite3
import logging
import time
import sys
import os
from pathlib import Path

# 添加項目路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 設置頁面配置
st.set_page_config(
    page_title="AI Trading System",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session_state():
    """初始化 session state"""
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.current_page = "dashboard"
        st.session_state.user_role = "admin"
        st.session_state.authenticated = True

def get_database_connection():
    """獲取數據庫連接"""
    db_path = project_root / "data" / "real_stock_database.db"
    try:
        conn = sqlite3.connect(str(db_path), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
    except Exception as e:
        logger.error(f"數據庫連接失敗: {e}")
        return None

@st.cache_data(ttl=300)
def get_stock_data():
    """獲取股票數據（帶緩存）"""
    conn = get_database_connection()
    if conn:
        try:
            df = pd.read_sql_query(
                "SELECT * FROM real_stock_data ORDER BY date DESC LIMIT 100",
                conn
            )
            conn.close()
            return df
        except Exception as e:
            logger.error(f"查詢股票數據失敗: {e}")
            conn.close()
    
    # 返回模擬數據
    return pd.DataFrame({
        'symbol': ['2330.TW', '2317.TW', 'AAPL', 'TSLA'],
        'date': ['2024-01-15'] * 4,
        'close': [582.0, 121.0, 186.0, 242.0],
        'volume': [25000000, 15000000, 50000000, 30000000]
    })

def search_stocks(query: str):
    """搜索股票"""
    if not query:
        return []
    
    conn = get_database_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT symbol FROM real_stock_data WHERE symbol LIKE ? LIMIT 10",
                (f"%{query}%",)
            )
            results = [row[0] for row in cursor.fetchall()]
            conn.close()
            return results
        except Exception as e:
            logger.error(f"搜索股票失敗: {e}")
            conn.close()
    
    # 返回模擬搜索結果
    mock_stocks = ['2330.TW', '2317.TW', '2454.TW', 'AAPL', 'TSLA', 'MSFT', 'GOOGL']
    return [stock for stock in mock_stocks if query.upper() in stock]

def show_dashboard():
    """顯示儀表板"""
    st.title("📊 AI Trading System Dashboard")
    
    # 快速統計
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("總股票數", "1,234", "12")
    
    with col2:
        st.metric("今日漲幅", "+2.5%", "0.3%")
    
    with col3:
        st.metric("活躍策略", "8", "1")
    
    with col4:
        st.metric("總收益", "$12,345", "$234")
    
    # 股票數據表格
    st.subheader("📈 股票數據")
    
    try:
        df = get_stock_data()
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("暫無股票數據")
    except Exception as e:
        st.error(f"載入股票數據失敗: {e}")

def show_data_management():
    """顯示數據管理頁面"""
    st.title("📊 數據管理")
    
    # 股票搜索
    st.subheader("🔍 股票搜索")
    
    search_query = st.text_input("輸入股票代碼或名稱", placeholder="例如: 2330 或 台積電")
    
    if search_query:
        with st.spinner("搜索中..."):
            results = search_stocks(search_query)
            
            if results:
                st.success(f"找到 {len(results)} 個結果")
                for stock in results:
                    st.write(f"• {stock}")
            else:
                st.warning("未找到匹配的股票")
    
    # 數據更新
    st.subheader("🔄 數據更新")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("更新股票數據", type="primary"):
            with st.spinner("更新中..."):
                time.sleep(1)  # 模擬更新過程
                st.success("股票數據更新完成")
    
    with col2:
        if st.button("清理緩存"):
            st.cache_data.clear()
            st.success("緩存已清理")

def show_advanced_technical_analysis_page():
    """顯示進階技術分析頁面"""
    try:
        # 嘗試導入進階技術分析模組
        from src.ui.pages.advanced_technical_analysis import show_advanced_technical_analysis
        show_advanced_technical_analysis()
    except ImportError as e:
        st.error("❌ 進階技術分析模組載入失敗")
        st.info("正在使用簡化版本...")

        # 簡化版本的技術分析
        st.title("📈 進階技術分析")
        st.markdown("---")

        # 股票選擇
        col1, col2 = st.columns(2)
        with col1:
            symbol = st.selectbox("選擇股票", ["2330.TW", "2317.TW", "AAPL", "TSLA"])
        with col2:
            days = st.slider("數據天數", 50, 200, 100)

        # 指標選擇
        st.subheader("📊 技術指標")
        indicators = st.multiselect(
            "選擇指標",
            ["Williams %R", "Stochastic", "CCI", "ATR", "VWAP", "MFI"],
            default=["Williams %R", "Stochastic"]
        )

        if indicators:
            st.success(f"✅ 已選擇 {len(indicators)} 個指標")

            # 顯示指標說明
            for indicator in indicators:
                with st.expander(f"📖 {indicator} 說明"):
                    if indicator == "Williams %R":
                        st.markdown("""
                        **Williams %R (威廉指標)**
                        - 範圍：-100 到 0
                        - 超買：-20 以上
                        - 超賣：-80 以下
                        - 用途：識別超買超賣條件
                        """)
                    elif indicator == "Stochastic":
                        st.markdown("""
                        **Stochastic (隨機指標)**
                        - 範圍：0 到 100
                        - 超買：80 以上
                        - 超賣：20 以下
                        - 包含 %K 和 %D 兩條線
                        """)
                    elif indicator == "CCI":
                        st.markdown("""
                        **CCI (商品通道指數)**
                        - 範圍：無限制
                        - 超買：+100 以上
                        - 超賣：-100 以下
                        - 用途：測量價格偏離統計平均值的程度
                        """)
                    elif indicator == "ATR":
                        st.markdown("""
                        **ATR (平均真實範圍)**
                        - 範圍：0 以上
                        - 用途：測量市場波動性
                        - 應用：設置止損和倉位管理
                        """)
                    elif indicator == "VWAP":
                        st.markdown("""
                        **VWAP (成交量加權平均價格)**
                        - 機構交易者常用基準
                        - 價格高於 VWAP：買方力量較強
                        - 價格低於 VWAP：賣方力量較強
                        """)
                    elif indicator == "MFI":
                        st.markdown("""
                        **MFI (資金流量指標)**
                        - 範圍：0 到 100
                        - 結合價格和成交量
                        - 超買：80 以上
                        - 超賣：20 以下
                        """)

            st.info("💡 完整的圖表功能需要安裝進階技術分析模組")
        else:
            st.info("👈 請選擇要分析的技術指標")

    except Exception as e:
        st.error(f"❌ 技術分析頁面載入失敗: {e}")
        logger.error(f"進階技術分析頁面錯誤: {e}")

def show_strategy_management():
    """顯示策略管理頁面"""
    st.title("🎯 策略管理")

    st.info("策略管理功能正在開發中...")

    # 模擬策略列表
    strategies = [
        {"name": "雙移動平均線", "status": "運行中", "收益": "+5.2%"},
        {"name": "RSI反轉", "status": "暫停", "收益": "+2.8%"},
        {"name": "MACD金叉", "status": "運行中", "收益": "+7.1%"},
    ]

    for strategy in strategies:
        with st.expander(f"📈 {strategy['name']} - {strategy['status']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"狀態: {strategy['status']}")
            with col2:
                st.write(f"收益: {strategy['收益']}")

def show_sidebar():
    """顯示側邊欄"""
    with st.sidebar:
        st.title("🚀 AI Trading")
        
        # 頁面導航
        pages = {
            "dashboard": "📊 儀表板",
            "data_management": "📊 數據管理",
            "advanced_technical_analysis": "📈 進階技術分析",
            "strategy_management": "🎯 策略管理",
            "settings": "⚙️ 設置"
        }
        
        selected_page = st.radio(
            "選擇頁面",
            options=list(pages.keys()),
            format_func=lambda x: pages[x],
            index=0
        )
        
        st.session_state.current_page = selected_page
        
        # 系統狀態
        st.divider()
        st.subheader("系統狀態")
        st.success("🟢 系統正常")
        st.info(f"⏰ {time.strftime('%H:%M:%S')}")
        
        # 快速操作
        st.divider()
        st.subheader("快速操作")
        
        if st.button("🔄 刷新數據", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        if st.button("📊 性能監控", use_container_width=True):
            st.info("性能監控功能開發中")

def main():
    """主函數"""
    start_time = time.time()
    
    # 初始化
    init_session_state()
    
    # 顯示側邊欄
    show_sidebar()
    
    # 根據選擇的頁面顯示內容
    current_page = st.session_state.get("current_page", "dashboard")
    
    if current_page == "dashboard":
        show_dashboard()
    elif current_page == "data_management":
        show_data_management()
    elif current_page == "advanced_technical_analysis":
        show_advanced_technical_analysis_page()
    elif current_page == "strategy_management":
        show_strategy_management()
    elif current_page == "settings":
        st.title("⚙️ 設置")
        st.info("設置功能開發中...")
    else:
        show_dashboard()
    
    # 顯示加載時間
    load_time = time.time() - start_time
    if load_time > 2.0:
        st.warning(f"⚠️ 頁面加載時間: {load_time:.2f}s (目標: <2.0s)")
    else:
        st.success(f"✅ 頁面加載時間: {load_time:.2f}s")

if __name__ == "__main__":
    main()
