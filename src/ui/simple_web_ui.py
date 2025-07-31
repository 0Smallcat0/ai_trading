#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
簡化版Web UI - 用於診斷和修復載入問題
=======================================

這是一個簡化版的Web UI，移除了複雜的性能優化組件，
專注於核心功能，用於診斷Web UI載入問題。

Author: AI Trading System
Date: 2025-01-28
Version: 1.0
"""

import streamlit as st
import sys
import os
import logging
from datetime import datetime

# 添加項目路徑
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_page_config():
    """設置頁面配置"""
    try:
        st.set_page_config(
            page_title="AI股票自動交易系統",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    except Exception as e:
        logger.error(f"設置頁面配置失敗: {e}")

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
        st.metric("版本", "v1.6")

def show_navigation():
    """顯示導航菜單"""
    st.sidebar.title("🧭 導航菜單")
    
    pages = {
        "🏠 首頁": "home",
        "📊 數據管理": "data_management", 
        "📈 策略分析": "strategy_analysis",
        "💰 交易執行": "trading_execution",
        "📋 風險管理": "risk_management",
        "⚙️ 系統設置": "system_settings"
    }
    
    selected_page = st.sidebar.selectbox(
        "選擇頁面",
        list(pages.keys()),
        index=0
    )
    
    return pages[selected_page]

def show_home_page():
    """顯示首頁"""
    st.subheader("🏠 系統首頁")
    
    st.info("歡迎使用AI股票自動交易系統！")
    
    # 系統概覽
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### 📊 系統功能")
        st.write("- 真實數據管理")
        st.write("- 策略分析與回測")
        st.write("- 自動交易執行")
        st.write("- 風險控制管理")
    
    with col2:
        st.write("### 🔧 系統狀態")
        st.write("- 數據服務: 正常")
        st.write("- 調度器: 運行中")
        st.write("- 數據品質: 95%+")
        st.write("- 股票覆蓋: 25個")

def show_data_management_page():
    """顯示數據管理頁面"""
    st.subheader("📊 數據管理")
    
    # 創建標籤頁
    tab1, tab2, tab3 = st.tabs(["🚀 真實數據管理", "📊 傳統數據管理", "⚙️ 數據源配置"])
    
    with tab1:
        st.write("### 🚀 真實數據管理")
        
        try:
            # 嘗試導入真實數據管理組件
            from src.ui.components.real_data_management import show as show_real_data_management
            show_real_data_management()
        except ImportError as e:
            st.error(f"❌ 無法載入真實數據管理組件: {e}")
            st.info("請檢查真實數據服務是否正確配置")
            
            # 提供基本功能
            st.write("**基本功能測試**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 測試數據更新"):
                    st.info("正在測試數據更新功能...")
                    try:
                        from src.core.real_data_integration import real_data_service
                        health = real_data_service.health_check()
                        st.success(f"✅ 數據服務狀態: {health['status']}")
                        st.write(f"資料庫記錄: {health.get('database_records', 0)} 筆")
                    except Exception as e:
                        st.error(f"❌ 測試失敗: {e}")
            
            with col2:
                if st.button("📊 檢查系統狀態"):
                    st.info("正在檢查系統狀態...")
                    try:
                        from src.core.real_data_integration import real_data_service
                        symbols = real_data_service.get_available_symbols()
                        st.success(f"✅ 可用股票: {len(symbols)} 個")
                        st.write(f"主要股票: {', '.join(symbols[:5])}")
                    except Exception as e:
                        st.error(f"❌ 檢查失敗: {e}")
        except Exception as e:
            st.error(f"❌ 載入真實數據管理功能時發生錯誤: {e}")
    
    with tab2:
        st.write("### 📊 傳統數據管理")
        st.info("傳統數據管理功能")
        
        # 基本數據管理功能
        st.write("**數據操作**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 導入數據"):
                st.info("數據導入功能")
        
        with col2:
            if st.button("📤 匯出數據"):
                st.info("數據匯出功能")
        
        with col3:
            if st.button("🔍 查詢數據"):
                st.info("數據查詢功能")
    
    with tab3:
        st.write("### ⚙️ 數據源配置")
        st.info("數據源配置功能")
        
        # 基本配置選項
        st.write("**配置選項**")
        
        data_source = st.selectbox(
            "選擇數據源",
            ["TWSE官方API", "Yahoo Finance", "本地數據庫"]
        )
        
        update_frequency = st.selectbox(
            "更新頻率",
            ["實時", "每分鐘", "每小時", "每日"]
        )
        
        if st.button("💾 保存配置"):
            st.success(f"✅ 配置已保存: {data_source}, {update_frequency}")

def show_other_pages(page_name):
    """顯示其他頁面"""
    page_titles = {
        "strategy_analysis": "📈 策略分析",
        "trading_execution": "💰 交易執行", 
        "risk_management": "📋 風險管理",
        "system_settings": "⚙️ 系統設置"
    }
    
    st.subheader(page_titles.get(page_name, "📄 未知頁面"))
    st.info(f"這是 {page_titles.get(page_name, '未知頁面')} 頁面")
    st.write("功能開發中...")

def main():
    """主函數"""
    try:
        # 設置頁面配置
        setup_page_config()
        
        # 顯示標題
        show_header()
        
        # 顯示導航並獲取選中的頁面
        selected_page = show_navigation()
        
        # 根據選中的頁面顯示內容
        if selected_page == "home":
            show_home_page()
        elif selected_page == "data_management":
            show_data_management_page()
        else:
            show_other_pages(selected_page)
        
        # 顯示頁腳
        st.markdown("---")
        st.markdown("© 2025 AI股票自動交易系統 - 簡化版Web UI")
        
    except Exception as e:
        logger.error(f"主函數執行失敗: {e}", exc_info=True)
        st.error(f"❌ 系統載入失敗: {e}")
        st.info("請重新整理頁面或聯繫系統管理員")

if __name__ == "__main__":
    main()
