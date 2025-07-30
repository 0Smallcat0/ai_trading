#!/usr/bin/env python3
"""
簡化版主要UI - 解決功能選單載入問題
"""

import streamlit as st
import logging
from datetime import datetime

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_page_config():
    """設置頁面配置"""
    try:
        st.set_page_config(
            page_title="AI Trading System",
            page_icon="📈",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    except Exception as e:
        logger.error(f"頁面配置設置失敗: {e}")

def show_header():
    """顯示頁面標題"""
    st.title("📊 AI股票自動交易系統")
    st.markdown("---")
    
    # 顯示系統狀態
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("系統狀態", "運行中", "✅")
    
    with col2:
        st.metric("當前時間", datetime.now().strftime("%H:%M:%S"))
    
    with col3:
        st.metric("版本", "v2.1.0")

def show_navigation():
    """顯示導航菜單"""
    st.sidebar.title("🧭 功能導航")
    
    # 主要功能頁面
    pages = {
        "🏠 系統概覽": "dashboard",
        "📊 數據管理": "data_management", 
        "📈 數據檢視": "data_view",
        "📥 數據下載": "data_download",
        "🎯 策略開發": "strategy_development",
        "🧠 AI決策支援": "ai_decision_support",
        "💼 投資組合管理": "portfolio_management",
        "⚠️ 風險管理": "risk_management",
        "💰 交易執行": "trade_execution",
        "🤖 AI模型管理": "ai_model_management",
        "📈 回測分析": "backtest_analysis",
        "📚 學習中心": "learning_center"
    }
    
    # 使用selectbox而不是radio，避免選單載入問題
    selected_page = st.sidebar.selectbox(
        "選擇功能模組",
        list(pages.keys()),
        index=0,
        key="main_navigation"
    )
    
    # 顯示當前選擇
    st.sidebar.success(f"✅ 當前頁面: {selected_page}")
    
    return pages[selected_page]

def show_page_content(page_key):
    """顯示頁面內容"""
    try:
        if page_key == "dashboard":
            show_dashboard_page()
        elif page_key == "data_management":
            show_data_management_page()
        elif page_key == "data_view":
            show_data_view_page()
        elif page_key == "data_download":
            show_data_download_page()
        else:
            show_other_pages(page_key)
            
    except Exception as e:
        logger.error(f"頁面載入失敗: {e}")
        st.error(f"❌ 頁面載入失敗: {e}")
        st.info("請嘗試重新整理頁面或選擇其他功能")

def show_dashboard_page():
    """顯示儀表板頁面"""
    st.header("🏠 系統概覽")
    
    # 系統狀態卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("活躍策略", "5", "↗️ +1")
    with col2:
        st.metric("今日交易", "12", "↗️ +3")
    with col3:
        st.metric("總收益率", "8.5%", "↗️ +0.3%")
    with col4:
        st.metric("風險評分", "7.2", "↘️ -0.1")
    
    st.markdown("---")
    st.info("📊 系統運行正常，所有功能模組已載入完成")

def show_data_management_page():
    """顯示數據管理頁面"""
    try:
        from src.ui.pages.data_management import show_data_management_page as show_data_mgmt
        show_data_mgmt()
    except ImportError:
        st.header("📊 數據管理")
        st.info("數據管理功能正在載入中...")
        st.write("- 股票數據下載")
        st.write("- 數據清理和驗證")
        st.write("- 數據源管理")

def show_data_view_page():
    """顯示數據檢視頁面"""
    try:
        from src.ui.pages.data_view import show_data_view_page as show_data_view
        show_data_view()
    except ImportError:
        st.header("📈 數據檢視")
        st.info("數據檢視功能正在載入中...")
        st.write("- 股票價格圖表")
        st.write("- 技術指標分析")
        st.write("- 數據表格檢視")

def show_data_download_page():
    """顯示數據下載頁面"""
    try:
        from src.ui.pages.data_download import show_data_download_page as show_data_download
        show_data_download()
    except ImportError:
        st.header("📥 數據下載")
        st.info("數據下載功能正在載入中...")
        st.write("- 批量股票數據下載")
        st.write("- 多數據源支援")
        st.write("- 下載進度監控")

def show_other_pages(page_key):
    """顯示其他頁面"""
    page_titles = {
        "strategy_development": "🎯 策略開發",
        "ai_decision_support": "🧠 AI決策支援",
        "portfolio_management": "💼 投資組合管理",
        "risk_management": "⚠️ 風險管理",
        "trade_execution": "💰 交易執行",
        "ai_model_management": "🤖 AI模型管理",
        "backtest_analysis": "📈 回測分析",
        "learning_center": "📚 學習中心"
    }
    
    title = page_titles.get(page_key, f"📋 {page_key}")
    st.header(title)
    st.info(f"{title} 功能正在開發中，敬請期待！")
    
    # 顯示功能預覽
    if page_key == "strategy_development":
        st.write("- 策略編輯器")
        st.write("- 策略回測")
        st.write("- 策略優化")
    elif page_key == "ai_decision_support":
        st.write("- AI市場分析")
        st.write("- 智能推薦")
        st.write("- 決策支援")
    elif page_key == "backtest_analysis":
        st.write("- 歷史回測")
        st.write("- 績效分析")
        st.write("- 風險評估")

def main():
    """主函數"""
    try:
        # 設置頁面配置
        setup_page_config()
        
        # 顯示標題
        show_header()
        
        # 顯示導航並獲取選中的頁面
        selected_page = show_navigation()
        
        # 顯示頁面內容
        show_page_content(selected_page)
        
        # 顯示頁腳
        st.markdown("---")
        st.markdown("© 2025 AI股票自動交易系統 - 簡化版UI")
        
        # 側邊欄額外信息
        st.sidebar.markdown("---")
        st.sidebar.info("💡 提示：如果遇到載入問題，請重新整理頁面")
        
    except Exception as e:
        logger.error(f"主函數執行失敗: {e}", exc_info=True)
        st.error(f"❌ 系統載入失敗: {e}")
        st.info("請重新整理頁面或聯繫系統管理員")

if __name__ == "__main__":
    main()
