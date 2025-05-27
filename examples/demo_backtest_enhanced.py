#!/usr/bin/env python3
"""
增強版回測系統演示腳本

此腳本演示如何使用增強版回測系統的各項功能。
"""

import streamlit as st
import sys
import os
import numpy as np
from datetime import datetime

# 添加 src 目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def main():
    """主函數"""
    st.set_page_config(
        page_title="AI 交易系統 - 增強版回測系統演示",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 導入回測系統模組
    try:
        from src.ui.responsive import apply_responsive_design

        # 應用響應式設計
        apply_responsive_design()

        # 頁面標題
        st.markdown(
            '<h1 class="title-responsive">📊 增強版回測系統演示</h1>',
            unsafe_allow_html=True,
        )

        # 側邊欄配置
        st.sidebar.markdown("## 📊 演示配置")

        # 演示選項
        demo_type = st.sidebar.selectbox(
            "選擇演示類型", ["圖表演示", "報告生成演示", "策略比較演示", "完整工作流程"]
        )

        if demo_type == "圖表演示":
            show_charts_demo()
        elif demo_type == "報告生成演示":
            show_reports_demo()
        elif demo_type == "策略比較演示":
            show_comparison_demo()
        else:
            show_full_workflow_demo()

    except ImportError as e:
        st.error(f"無法導入回測系統模組: {e}")
        st.info("請確保已正確安裝所有依賴項")

    except Exception as e:
        st.error(f"發生錯誤: {e}")
        st.info("請檢查系統配置")


def generate_mock_backtest_results(config):
    """生成模擬回測結果"""
    # 生成模擬數據
    dates = []
    returns = []

    start_date = config["start_date"]
    end_date = config["end_date"]

    current_date = start_date
    while current_date <= end_date:
        dates.append(current_date)
        # 生成隨機收益率
        daily_return = np.random.normal(0.001, 0.02)
        returns.append(daily_return)
        current_date += datetime.timedelta(days=1)

    # 計算累積收益
    cumulative_returns = np.cumprod(1 + np.array(returns))

    # 計算指標
    total_return = cumulative_returns[-1] - 1
    volatility = np.std(returns) * np.sqrt(252)
    sharpe_ratio = (np.mean(returns) * 252) / volatility if volatility > 0 else 0

    # 計算最大回撤
    peak = np.maximum.accumulate(cumulative_returns)
    drawdown = (cumulative_returns - peak) / peak
    max_drawdown = np.min(drawdown)

    # 計算勝率
    win_rate = np.sum(np.array(returns) > 0) / len(returns)

    return {
        "dates": dates,
        "returns": returns,
        "cumulative_returns": cumulative_returns,
        "metrics": {
            "total_return": total_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
        },
    }


def show_charts_demo():
    """顯示圖表演示"""
    st.subheader("📈 圖表功能演示")

    # 生成模擬數據
    st.info("正在生成模擬回測數據...")

    config = {
        "strategy_name": "演示策略",
        "symbols": ["AAPL", "MSFT"],
        "start_date": datetime(2024, 1, 1),
        "end_date": datetime(2024, 12, 31),
        "initial_capital": 1000000,
    }

    backtest_results = generate_mock_backtest_results(config)

    # 顯示基本統計
    st.subheader("📊 基本統計")
    metrics = backtest_results.get("metrics", {})

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("總回報率", f"{metrics.get('total_return', 0):.2%}")

    with col2:
        st.metric("夏普比率", f"{metrics.get('sharpe_ratio', 0):.3f}")

    with col3:
        st.metric("最大回撤", f"{metrics.get('max_drawdown', 0):.2%}")

    with col4:
        st.metric("勝率", f"{metrics.get('win_rate', 0):.2%}")


def show_reports_demo():
    """顯示報告生成演示"""
    st.subheader("📄 報告生成演示")
    st.info("此功能需要完整的回測系統模組支援")


def show_comparison_demo():
    """顯示策略比較演示"""
    st.subheader("⚖️ 策略比較演示")
    st.info("此功能需要完整的回測系統模組支援")


def show_full_workflow_demo():
    """顯示完整工作流程演示"""
    st.subheader("🚀 完整工作流程演示")

    # 步驟1：配置回測
    st.markdown("### 步驟1：配置回測參數")

    col1, col2 = st.columns(2)

    with col1:
        strategy_name = st.selectbox(
            "策略名稱", ["動量策略", "均值回歸策略", "機器學習策略"]
        )
        symbols = st.multiselect(
            "股票代碼", ["AAPL", "MSFT", "GOOGL", "TSLA"], default=["AAPL"]
        )

    with col2:
        start_date = st.date_input("開始日期", datetime(2024, 1, 1))
        end_date = st.date_input("結束日期", datetime(2024, 12, 31))
        initial_capital = st.number_input("初始資金", value=1000000, min_value=10000)

    # 步驟2：執行回測
    if st.button("🚀 執行回測", type="primary"):
        st.markdown("### 步驟2：執行回測")

        config = {
            "strategy_name": strategy_name,
            "symbols": symbols,
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": initial_capital,
        }

        with st.spinner("正在執行回測..."):
            # 模擬進度
            progress_bar = st.progress(0)
            status_text = st.empty()

            import time

            for i in range(101):
                progress_bar.progress(i)
                if i < 30:
                    status_text.text("正在載入數據...")
                elif i < 60:
                    status_text.text("正在執行策略...")
                elif i < 90:
                    status_text.text("正在計算指標...")
                else:
                    status_text.text("正在生成報告...")
                time.sleep(0.01)

            backtest_results = generate_mock_backtest_results(config)
            status_text.text("回測完成！")

        st.success("回測執行成功！")

        # 步驟3：分析結果
        st.markdown("### 步驟3：分析結果")

        # 基本指標
        metrics = backtest_results.get("metrics", {})

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("總回報率", f"{metrics.get('total_return', 0):.2%}")

        with col2:
            st.metric("夏普比率", f"{metrics.get('sharpe_ratio', 0):.3f}")

        with col3:
            st.metric("最大回撤", f"{metrics.get('max_drawdown', 0):.2%}")

        with col4:
            st.metric("勝率", f"{metrics.get('win_rate', 0):.2%}")


if __name__ == "__main__":
    main()
