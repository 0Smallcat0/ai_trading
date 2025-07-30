"""
特徵查詢模組

此模組實現了特徵查詢功能，包括：
- 特徵數據查詢
- 特徵統計分析
- 特徵可視化
- 特徵導出
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from .utils import (
    get_feature_service, 
    get_stock_list, 
    generate_sample_feature_data
)


def show_feature_query():
    """顯示特徵查詢頁面"""
    st.subheader("特徵查詢")

    # 獲取特徵工程服務
    feature_service = get_feature_service()

    # 獲取股票列表
    stocks = get_stock_list()

    # 創建查詢表單
    with st.form("feature_query_form"):
        col1, col2 = st.columns(2)

        with col1:
            # 選擇特徵類型
            feature_type = st.selectbox(
                "特徵類型",
                options=["技術指標", "基本面指標", "情緒指標"],
                index=0,
            )

            # 選擇股票
            stock_options = [f"{s['symbol']} - {s['name']}" for s in stocks]
            selected_stocks = st.multiselect(
                "選擇股票",
                options=stock_options,
                default=[stock_options[0]],
            )

            # 從選擇中提取股票代碼
            selected_symbols = [s.split(" - ")[0] for s in selected_stocks]

        with col2:
            # 選擇日期範圍
            start_date = st.date_input(
                "開始日期",
                datetime.now() - timedelta(days=90),
            )

            end_date = st.date_input(
                "結束日期",
                datetime.now(),
            )

            # 選擇查詢模式
            query_mode = st.selectbox(
                "查詢模式",
                options=["最新數據", "歷史數據", "統計分析"],
                index=0,
            )

        # 提交按鈕
        submitted = st.form_submit_button("查詢特徵")

    # 處理查詢
    if submitted:
        _handle_feature_query(
            feature_service, feature_type, selected_symbols, 
            start_date, end_date, query_mode
        )


def _handle_feature_query(feature_service, feature_type, selected_symbols, start_date, end_date, query_mode):
    """處理特徵查詢"""
    if not selected_symbols:
        st.error("請選擇至少一個股票")
        return

    with st.spinner("正在查詢特徵數據..."):
        # 生成樣本數據（實際應用中應該從數據庫查詢）
        feature_data = generate_sample_feature_data(
            feature_type, selected_symbols, start_date, end_date
        )

        if feature_data.empty:
            st.warning("未找到符合條件的特徵數據")
            return

        # 根據查詢模式顯示不同的結果
        if query_mode == "最新數據":
            _show_latest_data(feature_data, feature_type)
        elif query_mode == "歷史數據":
            _show_historical_data(feature_data, feature_type, selected_symbols)
        elif query_mode == "統計分析":
            _show_statistical_analysis(feature_data, feature_type)


def _show_latest_data(feature_data, feature_type):
    """顯示最新數據"""
    st.subheader("最新特徵數據")

    # 獲取最新一行數據
    latest_data = feature_data.iloc[-1:].copy()

    # 轉置數據以便更好地顯示
    display_data = latest_data.T
    display_data.columns = ["最新值"]
    display_data = display_data[display_data.index != "日期"]

    # 顯示數據表格
    st.dataframe(display_data, use_container_width=True)

    # 顯示關鍵指標卡片
    st.subheader("關鍵指標")
    
    # 選擇前幾個特徵顯示為指標卡片
    feature_cols = [col for col in feature_data.columns if col != "日期"]
    
    if len(feature_cols) >= 3:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label=feature_cols[0],
                value=f"{latest_data[feature_cols[0]].iloc[0]:.4f}",
            )
        
        with col2:
            st.metric(
                label=feature_cols[1],
                value=f"{latest_data[feature_cols[1]].iloc[0]:.4f}",
            )
        
        with col3:
            st.metric(
                label=feature_cols[2],
                value=f"{latest_data[feature_cols[2]].iloc[0]:.4f}",
            )


def _show_historical_data(feature_data, feature_type, selected_symbols):
    """顯示歷史數據"""
    st.subheader("歷史特徵數據")

    # 顯示數據表格
    st.dataframe(feature_data, use_container_width=True)

    # 創建時間序列圖表
    st.subheader("特徵趨勢圖")

    # 選擇要顯示的特徵
    feature_cols = [col for col in feature_data.columns if col != "日期"]
    selected_features = st.multiselect(
        "選擇要顯示的特徵",
        options=feature_cols,
        default=feature_cols[:3],
        key="chart_features",
    )

    if selected_features:
        # 創建子圖
        for feature in selected_features:
            fig = px.line(
                feature_data,
                x="日期",
                y=feature,
                title=f"{feature} 趨勢",
                labels={"日期": "日期", feature: "數值"},
            )
            
            fig.update_layout(
                xaxis_title="日期",
                yaxis_title="數值",
                hovermode="x unified",
            )
            
            st.plotly_chart(fig, use_container_width=True)

    # 提供數據下載
    st.subheader("數據導出")
    
    # 轉換為CSV格式
    csv_data = feature_data.to_csv(index=False)
    
    st.download_button(
        label="下載CSV文件",
        data=csv_data,
        file_name=f"feature_data_{feature_type}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )


def _show_statistical_analysis(feature_data, feature_type):
    """顯示統計分析"""
    st.subheader("特徵統計分析")

    # 獲取數值列
    numeric_cols = feature_data.select_dtypes(include=['float64', 'int64']).columns

    if len(numeric_cols) == 0:
        st.warning("沒有數值型特徵可以進行統計分析")
        return

    # 基本統計信息
    st.subheader("基本統計信息")
    stats_data = feature_data[numeric_cols].describe()
    st.dataframe(stats_data, use_container_width=True)

    # 相關性分析
    st.subheader("特徵相關性分析")
    
    if len(numeric_cols) > 1:
        correlation_matrix = feature_data[numeric_cols].corr()
        
        # 創建熱力圖
        fig = px.imshow(
            correlation_matrix,
            text_auto=True,
            aspect="auto",
            title="特徵相關性熱力圖",
            color_continuous_scale="RdBu_r",
        )
        
        fig.update_layout(
            width=800,
            height=600,
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # 顯示高相關性特徵對
        st.subheader("高相關性特徵對")
        
        # 找出相關性大於0.7的特徵對
        high_corr_pairs = []
        for i in range(len(correlation_matrix.columns)):
            for j in range(i+1, len(correlation_matrix.columns)):
                corr_value = correlation_matrix.iloc[i, j]
                if abs(corr_value) > 0.7:
                    high_corr_pairs.append({
                        "特徵1": correlation_matrix.columns[i],
                        "特徵2": correlation_matrix.columns[j],
                        "相關係數": f"{corr_value:.4f}",
                    })
        
        if high_corr_pairs:
            high_corr_df = pd.DataFrame(high_corr_pairs)
            st.dataframe(high_corr_df, use_container_width=True)
        else:
            st.info("沒有發現高相關性的特徵對（|相關係數| > 0.7）")

    # 分佈分析
    st.subheader("特徵分佈分析")
    
    # 選擇要分析的特徵
    selected_feature = st.selectbox(
        "選擇特徵",
        options=numeric_cols,
        key="dist_feature",
    )
    
    if selected_feature:
        col1, col2 = st.columns(2)
        
        with col1:
            # 直方圖
            fig_hist = px.histogram(
                feature_data,
                x=selected_feature,
                title=f"{selected_feature} 分佈直方圖",
                nbins=30,
            )
            st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            # 箱線圖
            fig_box = px.box(
                feature_data,
                y=selected_feature,
                title=f"{selected_feature} 箱線圖",
            )
            st.plotly_chart(fig_box, use_container_width=True)
