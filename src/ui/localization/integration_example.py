"""本地化整合示例

此文件展示如何將本地化功能整合到現有的 Streamlit Web UI 中。
提供完整的使用範例和最佳實踐。

Example:
    在 Web UI 中使用本地化功能：
    ```python
    from src.ui.localization.integration_example import LocalizedWebUI
    
    # 創建本地化 Web UI
    ui = LocalizedWebUI()
    ui.run()
    ```

Note:
    此文件僅作為示例，實際整合時需要根據具體需求調整。
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Any

from .language_switcher import get_language_switcher, get_text
from .currency_formatter import get_currency_formatter, format_currency
from .timezone_handler import get_timezone_handler, format_datetime


class LocalizedWebUI:
    """本地化 Web UI 示例類
    
    展示如何在 Streamlit 應用中整合本地化功能。
    包含語言切換、貨幣格式化、時間顯示等功能的完整示例。
    """
    
    def __init__(self):
        """初始化本地化 Web UI"""
        self.language_switcher = get_language_switcher()
        self.currency_formatter = get_currency_formatter()
        self.timezone_handler = get_timezone_handler()
        
    def run(self):
        """運行本地化 Web UI 示例"""
        # 設定頁面配置
        st.set_page_config(
            page_title=get_text("app.title", "AI 股票自動交易系統"),
            page_icon="📈",
            layout="wide"
        )
        
        # 顯示語言選擇器
        self._show_language_selector()
        
        # 顯示主要內容
        self._show_main_content()
        
        # 顯示側邊欄
        self._show_sidebar()
        
    def _show_language_selector(self):
        """顯示語言選擇器"""
        with st.container():
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col2:
                self.language_switcher.show_language_selector(
                    key="main_language_selector",
                    show_in_sidebar=False
                )
                
    def _show_main_content(self):
        """顯示主要內容"""
        # 標題
        st.title(get_text("app.title", "AI 股票自動交易系統"))
        st.markdown(get_text("app.subtitle", "智能投資，精準交易"))
        
        # 儀表板指標
        self._show_dashboard_metrics()
        
        # 交易資訊
        self._show_trading_info()
        
        # 圖表展示
        self._show_charts()
        
    def _show_dashboard_metrics(self):
        """顯示儀表板指標"""
        st.subheader(get_text("dashboard.system_status", "系統狀態"))
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label=get_text("dashboard.portfolio_value", "投資組合價值"),
                value=format_currency(1234567.89, "TWD"),
                delta=format_currency(12345.67, "TWD")
            )
            
        with col2:
            st.metric(
                label=get_text("dashboard.daily_pnl", "當日損益"),
                value=format_currency(5432.10, "TWD"),
                delta="2.34%"
            )
            
        with col3:
            st.metric(
                label=get_text("dashboard.total_return", "總回報"),
                value="15.67%",
                delta="1.23%"
            )
            
        with col4:
            st.metric(
                label=get_text("dashboard.win_rate", "勝率"),
                value="68.5%",
                delta="2.1%"
            )
            
    def _show_trading_info(self):
        """顯示交易資訊"""
        st.subheader(get_text("dashboard.recent_trades", "最近交易"))
        
        # 模擬交易數據
        trades_data = [
            {
                "symbol": "2330.TW",
                "type": get_text("trading.buy", "買入"),
                "quantity": 1000,
                "price": format_currency(587.50, "TWD"),
                "time": format_datetime(datetime.now(), "short"),
                "profit_loss": format_currency(2500.00, "TWD")
            },
            {
                "symbol": "0050.TW", 
                "type": get_text("trading.sell", "賣出"),
                "quantity": 500,
                "price": format_currency(142.30, "TWD"),
                "time": format_datetime(datetime.now(), "short"),
                "profit_loss": format_currency(-800.00, "TWD")
            }
        ]
        
        # 創建表格
        for trade in trades_data:
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            
            with col1:
                st.write(trade["symbol"])
            with col2:
                st.write(trade["type"])
            with col3:
                st.write(trade["quantity"])
            with col4:
                st.write(trade["price"])
            with col5:
                st.write(trade["time"])
            with col6:
                color = "green" if "+" in trade["profit_loss"] else "red"
                st.markdown(f":{color}[{trade['profit_loss']}]")
                
    def _show_charts(self):
        """顯示圖表"""
        st.subheader(get_text("dashboard.market_overview", "市場概覽"))
        
        # 模擬圖表數據
        import pandas as pd
        import numpy as np
        
        # 生成模擬數據
        dates = pd.date_range(start="2023-01-01", end="2023-12-31", freq="D")
        prices = 100 + np.cumsum(np.random.randn(len(dates)) * 0.5)
        
        chart_data = pd.DataFrame({
            get_text("common.date", "日期"): dates,
            get_text("common.price", "價格"): prices
        })
        
        st.line_chart(chart_data.set_index(get_text("common.date", "日期")))
        
    def _show_sidebar(self):
        """顯示側邊欄"""
        with st.sidebar:
            st.header(get_text("settings.general", "一般設定"))
            
            # 貨幣設定
            st.subheader(get_text("settings.currency", "貨幣"))
            currencies = self.currency_formatter.get_supported_currencies()
            currency_options = [
                f"{code} - {self.currency_formatter.get_currency_name(code)}"
                for code in currencies.keys()
            ]
            
            selected_currency = st.selectbox(
                get_text("settings.currency", "貨幣"),
                currency_options,
                key="currency_selector"
            )
            
            # 時區設定
            st.subheader(get_text("settings.timezone", "時區"))
            timezones = self.timezone_handler.get_supported_timezones()
            timezone_options = [
                f"{tz} - {config['name_zh'] if self.language_switcher.get_current_language().startswith('zh') else config['name_en']}"
                for tz, config in timezones.items()
            ]
            
            selected_timezone = st.selectbox(
                get_text("settings.timezone", "時區"),
                timezone_options,
                key="timezone_selector"
            )
            
            # 市場狀態
            st.subheader(get_text("dashboard.market_overview", "市場概覽"))
            
            markets = ["TSE", "NYSE", "LSE"]
            for market in markets:
                status = self.timezone_handler.get_market_status(market)
                market_config = self.timezone_handler.get_supported_markets()[market]
                
                market_name = (
                    market_config["name_zh"] 
                    if self.language_switcher.get_current_language().startswith("zh")
                    else market_config["name_en"]
                )
                
                status_text = get_text("dashboard.running", "開市") if status["is_open"] else get_text("dashboard.stopped", "休市")
                status_color = "green" if status["is_open"] else "red"
                
                st.markdown(f"**{market_name}**: :{status_color}[{status_text}]")
                
            # 快速操作
            st.subheader(get_text("dashboard.quick_actions", "快速操作"))
            
            if st.button(get_text("common.refresh", "重新整理")):
                st.rerun()
                
            if st.button(get_text("common.export", "匯出")):
                st.success(get_text("messages.operation_successful", "操作成功"))
                
    def show_localization_demo(self):
        """顯示本地化功能演示"""
        st.header("本地化功能演示")
        
        # 語言切換演示
        st.subheader("1. 語言切換")
        current_lang = self.language_switcher.get_current_language()
        lang_info = self.language_switcher.get_language_info(current_lang)
        st.write(f"當前語言: {lang_info['name']} {lang_info['flag']}")
        
        # 貨幣格式化演示
        st.subheader("2. 貨幣格式化")
        test_amount = 1234567.89
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**標準格式:**")
            for currency in ["TWD", "USD", "CNY", "JPY"]:
                formatted = format_currency(test_amount, currency)
                st.write(f"{currency}: {formatted}")
                
        with col2:
            st.write("**簡潔格式:**")
            for currency in ["TWD", "USD", "CNY", "JPY"]:
                formatted = format_currency(test_amount, currency, compact=True)
                st.write(f"{currency}: {formatted}")
                
        # 時間格式化演示
        st.subheader("3. 時間格式化")
        now = datetime.now()
        
        formats = ["default", "short", "long", "time_only", "date_only"]
        for fmt in formats:
            formatted = format_datetime(now, fmt, include_timezone=False)
            st.write(f"{fmt}: {formatted}")
            
        # 交易時間檢查演示
        st.subheader("4. 交易時間檢查")
        for market in ["TSE", "NYSE", "LSE"]:
            is_open = self.timezone_handler.is_trading_hours(now, market)
            status = "開市" if is_open else "休市"
            color = "green" if is_open else "red"
            st.markdown(f"**{market}**: :{color}[{status}]")


def main():
    """主函數 - 運行本地化 Web UI 示例"""
    ui = LocalizedWebUI()
    
    # 創建標籤頁
    tab1, tab2 = st.tabs([
        get_text("navigation.dashboard", "儀表板"),
        "本地化演示"
    ])
    
    with tab1:
        ui.run()
        
    with tab2:
        ui.show_localization_demo()


if __name__ == "__main__":
    main()
