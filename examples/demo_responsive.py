#!/usr/bin/env python3
"""
響應式設計演示腳本

此腳本演示如何啟動支援響應式設計的 Streamlit 應用程式。
"""

import streamlit as st
import sys
import os

# 添加 src 目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def main():
    """主函數"""
    st.set_page_config(
        page_title="AI 交易系統 - 響應式設計演示",
        page_icon="📱",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 導入響應式設計模組
    try:
        from src.ui.responsive import (
            ResponsiveUtils,
            ResponsiveComponents,
            responsive_manager,
            apply_responsive_design,
        )

        # 應用響應式設計
        apply_responsive_design()

        # 頁面標題
        st.markdown(
            '<h1 class="title-responsive">📱 響應式設計演示</h1>',
            unsafe_allow_html=True,
        )

        # 顯示當前裝置資訊
        st.sidebar.markdown("## 📊 裝置資訊")
        config = ResponsiveUtils.get_responsive_config()

        st.sidebar.json(
            {
                "當前斷點": config["current_breakpoint"],
                "是否手機": config["is_mobile"],
                "是否平板": config["is_tablet"],
                "是否桌面": config["is_desktop"],
            }
        )

        # 響應式指標卡片演示
        st.markdown("## 📊 響應式指標卡片")

        metrics = [
            {
                "title": "總資產",
                "value": "1,000,000",
                "status": "success",
                "icon": "💰",
            },
            {"title": "今日收益", "value": "+5.2%", "status": "success", "icon": "📈"},
            {"title": "持倉數量", "value": "15", "status": "normal", "icon": "📋"},
            {"title": "風險等級", "value": "中等", "status": "warning", "icon": "⚠️"},
        ]

        ResponsiveComponents.responsive_metric_cards(
            metrics, desktop_cols=4, tablet_cols=2, mobile_cols=1
        )

        # 響應式表格演示
        st.markdown("## 📋 響應式表格")

        import pandas as pd
        import numpy as np

        # 生成示例資料
        data = {
            "股票代碼": ["2330.TW", "2317.TW", "AAPL", "MSFT", "GOOGL"],
            "股票名稱": ["台積電", "鴻海", "蘋果", "微軟", "谷歌"],
            "當前價格": [580, 105, 150, 280, 120],
            "漲跌幅": ["+2.1%", "-0.5%", "+1.8%", "+0.9%", "-1.2%"],
            "成交量": ["25,000", "18,500", "45,000", "32,000", "28,000"],
        }

        df = pd.DataFrame(data)
        ResponsiveComponents.responsive_dataframe(df, title="持股明細")

        # 響應式圖表演示
        st.markdown("## 📈 響應式圖表")

        import plotly.express as px

        # 生成示例圖表資料
        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        returns = np.cumsum(np.random.normal(0.001, 0.02, 30))

        chart_data = pd.DataFrame({"date": dates, "returns": returns})

        ResponsiveComponents.responsive_chart(
            chart_func=lambda data, **kwargs: st.plotly_chart(
                px.line(data, x="date", y="returns", title="投資組合收益率", **kwargs),
                use_container_width=True,
            ),
            chart_data=chart_data,
            title="投資組合表現",
        )

        # 響應式表單演示
        st.markdown("## 📝 響應式表單")

        form_config = {
            "title": "交易下單",
            "fields": [
                {
                    "key": "symbol",
                    "label": "股票代碼",
                    "type": "select",
                    "options": ["2330.TW", "2317.TW", "AAPL", "MSFT"],
                },
                {
                    "key": "action",
                    "label": "交易類型",
                    "type": "select",
                    "options": ["買入", "賣出"],
                },
                {"key": "quantity", "label": "數量", "type": "number", "default": 100},
                {"key": "price", "label": "價格", "type": "number", "default": 580.0},
            ],
        }

        form_data = ResponsiveComponents.responsive_form(form_config, "trading_form")

        if form_data:
            st.success("交易訂單已提交！")
            st.json(form_data)

        # 響應式標籤頁演示
        st.markdown("## 📑 響應式標籤頁")

        def show_portfolio():
            st.write("投資組合內容...")
            st.bar_chart(np.random.randn(10))

        def show_trades():
            st.write("交易記錄內容...")
            st.line_chart(np.random.randn(20, 3))

        def show_analysis():
            st.write("分析報告內容...")
            st.area_chart(np.random.randn(30, 2))

        tabs_config = [
            {"name": "投資組合", "content_func": show_portfolio},
            {"name": "交易記錄", "content_func": show_trades},
            {"name": "分析報告", "content_func": show_analysis},
        ]

        ResponsiveComponents.responsive_tabs(tabs_config)

        # 裝置特定提示
        if responsive_manager.is_mobile:
            st.info("📱 您正在使用手機瀏覽，介面已優化為觸控操作")
        elif responsive_manager.is_tablet:
            st.info("📱 您正在使用平板瀏覽，介面已調整為適中佈局")
        else:
            st.info("🖥️ 您正在使用桌面瀏覽，享受完整功能體驗")

    except ImportError as e:
        st.error(f"無法導入響應式設計模組: {e}")
        st.info("請確保已正確安裝所有依賴項")

    except Exception as e:
        st.error(f"發生錯誤: {e}")
        st.info("請檢查系統配置")


if __name__ == "__main__":
    main()
