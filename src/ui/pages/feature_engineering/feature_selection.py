"""
特徵選擇模組

此模組實現了特徵選擇功能，包括：
- 統計方法特徵選擇
- 機器學習方法特徵選擇
- 特徵重要性分析
- 特徵選擇結果評估
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from .utils import (
    get_feature_service,
    get_stock_list,
    generate_sample_feature_data
)


def show_feature_selection():
    """顯示特徵選擇頁面"""
    st.subheader("特徵選擇")

    # 獲取特徵工程服務
    feature_service = get_feature_service()

    # 獲取股票列表
    stocks = get_stock_list()

    # 創建特徵選擇表單
    with st.form("feature_selection_form"):
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

            # 選擇特徵選擇方法
            selection_method = st.selectbox(
                "特徵選擇方法",
                options=[
                    "方差過濾",
                    "相關性過濾", 
                    "卡方檢驗",
                    "互信息",
                    "遞歸特徵消除",
                    "LASSO正則化",
                    "隨機森林重要性",
                ],
                index=0,
            )

        with col2:
            # 選擇日期範圍
            start_date = st.date_input(
                "開始日期",
                datetime.now() - timedelta(days=180),
            )

            end_date = st.date_input(
                "結束日期",
                datetime.now(),
            )

            # 選擇目標變量
            target_variable = st.selectbox(
                "目標變量",
                options=["未來收益率", "價格方向", "波動率", "成交量"],
                index=0,
                help="選擇用於特徵選擇的目標變量",
            )

            # 選擇保留特徵數量
            n_features = st.slider(
                "保留特徵數量",
                min_value=1,
                max_value=20,
                value=10,
                help="選擇要保留的特徵數量",
            )

        # 高級選項
        with st.expander("高級選項"):
            preprocess = st.checkbox("特徵預處理", value=True)
            if preprocess:
                scaling_method = st.selectbox("標準化方法",
                    ["StandardScaler", "MinMaxScaler", "RobustScaler"])

            use_cv = st.checkbox("使用交叉驗證", value=True)
            if use_cv:
                cv_folds = st.slider("交叉驗證折數", 3, 10, 5)

        # 提交按鈕
        submitted = st.form_submit_button("開始特徵選擇")

    # 處理特徵選擇
    if submitted:
        _handle_feature_selection(
            feature_service, feature_type, selected_symbols, start_date, end_date,
            selection_method, target_variable, n_features, preprocess, use_cv
        )


def _handle_feature_selection(
    feature_service, feature_type, selected_symbols, start_date, end_date,
    selection_method, target_variable, n_features, preprocess, use_cv
):
    """處理特徵選擇"""
    if not selected_symbols:
        st.error("請選擇至少一個股票")
        return

    with st.spinner("正在進行特徵選擇..."):
        # 生成樣本數據
        feature_data = generate_sample_feature_data(
            feature_type, selected_symbols, start_date, end_date
        )

        if feature_data.empty:
            st.warning("未找到符合條件的特徵數據")
            return

        # 生成目標變量
        target_data = _generate_target_variable(feature_data, target_variable)

        # 執行特徵選擇
        selected_features, feature_scores = _perform_feature_selection(
            feature_data, target_data, selection_method, n_features
        )

        # 顯示結果
        _show_selection_results(
            selected_features, feature_scores, selection_method, feature_data
        )


def _generate_target_variable(feature_data, target_variable):
    """生成目標變量"""
    np.random.seed(42)  # 確保結果可重現
    
    if target_variable == "未來收益率":
        # 生成未來收益率（正態分佈）
        target = np.random.normal(0, 0.02, len(feature_data))
    elif target_variable == "價格方向":
        # 生成價格方向（二元分類）
        target = np.random.choice([0, 1], len(feature_data), p=[0.5, 0.5])
    elif target_variable == "波動率":
        # 生成波動率（對數正態分佈）
        target = np.random.lognormal(0, 0.5, len(feature_data))
    elif target_variable == "成交量":
        # 生成成交量（指數分佈）
        target = np.random.exponential(1000000, len(feature_data))
    
    return target


def _perform_feature_selection(feature_data, target_data, selection_method, n_features):
    """執行特徵選擇"""
    # 獲取特徵列（排除日期列）
    feature_cols = [col for col in feature_data.columns if col != "日期"]
    X = feature_data[feature_cols].fillna(0)  # 簡單處理缺失值
    y = target_data

    # 根據選擇方法計算特徵分數
    if selection_method == "方差過濾":
        # 計算方差
        feature_scores = X.var().to_dict()
    elif selection_method == "相關性過濾":
        # 計算與目標變量的相關性
        correlations = []
        for col in feature_cols:
            corr = np.corrcoef(X[col], y)[0, 1]
            correlations.append(abs(corr) if not np.isnan(corr) else 0)
        feature_scores = dict(zip(feature_cols, correlations))
    elif selection_method == "卡方檢驗":
        # 模擬卡方統計量
        chi2_scores = np.random.uniform(0, 100, len(feature_cols))
        feature_scores = dict(zip(feature_cols, chi2_scores))
    elif selection_method == "互信息":
        # 模擬互信息分數
        mi_scores = np.random.uniform(0, 1, len(feature_cols))
        feature_scores = dict(zip(feature_cols, mi_scores))
    elif selection_method == "遞歸特徵消除":
        # 模擬RFE排名（排名越小越重要）
        rfe_rankings = np.random.randint(1, len(feature_cols) + 1, len(feature_cols))
        feature_scores = dict(zip(feature_cols, 1 / rfe_rankings))  # 轉換為分數
    elif selection_method == "LASSO正則化":
        # 模擬LASSO係數
        lasso_coefs = np.random.normal(0, 0.1, len(feature_cols))
        feature_scores = dict(zip(feature_cols, np.abs(lasso_coefs)))
    elif selection_method == "隨機森林重要性":
        # 模擬隨機森林特徵重要性
        rf_importances = np.random.uniform(0, 1, len(feature_cols))
        rf_importances = rf_importances / rf_importances.sum()  # 歸一化
        feature_scores = dict(zip(feature_cols, rf_importances))

    # 選擇前n個特徵
    sorted_features = sorted(feature_scores.items(), key=lambda x: x[1], reverse=True)
    selected_features = [feat[0] for feat in sorted_features[:n_features]]

    return selected_features, feature_scores


def _show_selection_results(selected_features, feature_scores, selection_method, feature_data):
    """顯示特徵選擇結果"""
    st.success(f"特徵選擇完成！使用 {selection_method} 方法選出了 {len(selected_features)} 個特徵。")

    # 顯示選中的特徵
    st.subheader("選中的特徵")
    
    # 創建特徵重要性數據框
    selected_scores = {feat: feature_scores[feat] for feat in selected_features}
    importance_df = pd.DataFrame([
        {"特徵名稱": feat, "重要性分數": score}
        for feat, score in selected_scores.items()
    ]).sort_values("重要性分數", ascending=False)

    # 顯示表格
    st.dataframe(importance_df, use_container_width=True)

    # 創建特徵重要性圖表
    st.subheader("特徵重要性圖表")
    
    fig = px.bar(
        importance_df,
        x="重要性分數",
        y="特徵名稱",
        orientation="h",
        title=f"特徵重要性 ({selection_method})",
        labels={"重要性分數": "重要性分數", "特徵名稱": "特徵名稱"},
    )
    
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        height=max(400, len(selected_features) * 30),
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # 顯示特徵統計信息
    st.subheader("選中特徵統計信息")
    
    selected_data = feature_data[selected_features]
    stats_df = selected_data.describe()
    st.dataframe(stats_df, use_container_width=True)

    # 特徵相關性分析
    if len(selected_features) > 1:
        st.subheader("選中特徵相關性")
        
        correlation_matrix = selected_data.corr()
        
        fig_corr = px.imshow(
            correlation_matrix,
            text_auto=True,
            aspect="auto",
            title="選中特徵相關性熱力圖",
            color_continuous_scale="RdBu_r",
        )
        
        st.plotly_chart(fig_corr, use_container_width=True)

    # 結果導出
    st.subheader("結果導出")
    col1, col2 = st.columns(2)

    # 下載特徵重要性
    importance_csv = importance_df.to_csv(index=False)
    col1.download_button("下載特徵重要性", importance_csv,
                        f"feature_importance_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")

    # 下載選中特徵數據
    selected_csv = selected_data.to_csv(index=False)
    col2.download_button("下載選中特徵數據", selected_csv,
                        f"selected_features_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
