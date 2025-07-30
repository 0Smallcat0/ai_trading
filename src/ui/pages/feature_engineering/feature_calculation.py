"""
特徵計算與更新模組

此模組實現了特徵計算與更新功能，包括：
- 技術指標計算
- 基本面指標計算
- 情緒指標計算
- 自定義特徵計算
- 特徵處理選項
"""

import time
import streamlit as st
from datetime import datetime, timedelta
from src.ui.components.feature_components import show_calculation_progress
from .utils import get_feature_service, get_stock_list


def show_feature_calculation():
    """顯示特徵計算與更新頁面"""
    st.subheader("特徵計算與更新")

    # 獲取特徵工程服務
    feature_service = get_feature_service()

    # 獲取可用特徵
    available_features = feature_service.get_available_features()
    tech_indicators = available_features.get("technical", [])
    fund_indicators = available_features.get("fundamental", [])
    sent_indicators = available_features.get("sentiment", [])

    # 獲取股票列表
    stocks = get_stock_list()

    # 創建表單
    with st.form("feature_calculation_form"):
        # 選擇特徵類型
        feature_type = st.radio(
            "特徵類型", ["技術指標", "基本面指標", "情緒指標"], horizontal=True
        )

        # 根據特徵類型顯示不同的選項
        if feature_type == "技術指標":
            selected_indicators, custom_params, multipliers = _show_technical_options(tech_indicators)
        elif feature_type == "基本面指標":
            selected_indicators = _show_fundamental_options(fund_indicators)
            custom_params = {}
            multipliers = ["1x"]
        elif feature_type == "情緒指標":
            selected_indicators, sentiment_sources, sentiment_topics = _show_sentiment_options(sent_indicators)
            custom_params = {}
            multipliers = ["1x"]

        # 選擇股票和日期
        selected_symbols, start_date, end_date, time_frame = _show_stock_date_options(stocks)

        # 特徵處理選項
        processing_options = _show_processing_options()

        # 提交按鈕
        submitted = st.form_submit_button("開始計算特徵")

    # 處理表單提交
    if submitted:
        _handle_calculation_submission(
            feature_service, feature_type, selected_indicators, selected_symbols,
            start_date, end_date, time_frame, processing_options, custom_params
        )


def _show_technical_options(tech_indicators):
    """顯示技術指標選項"""
    # 選擇技術指標
    tech_indicator_names = [ind["name"] for ind in tech_indicators]
    selected_indicators = st.multiselect(
        "選擇技術指標",
        options=tech_indicator_names,
        default=tech_indicator_names[:3],
    )

    # 選擇參數倍數
    multipliers = st.multiselect(
        "參數倍數",
        options=["0.5x", "1x", "1.5x", "2x", "3x"],
        default=["1x"],
        help="用於生成不同參數的指標變體，例如 SMA 的窗口大小",
    )

    # 高級參數設置
    custom_params = {}
    with st.expander("高級參數設置"):
        for ind_name in selected_indicators:
            # 找到對應的指標
            ind = next(
                (ind for ind in tech_indicators if ind["name"] == ind_name),
                None,
            )
            if ind:
                st.subheader(f"{ind_name} 參數")
                # 為每個參數提供輸入
                params = {}
                for param_name, param_value in ind.get("parameters", {}).items():
                    if isinstance(param_value, int):
                        params[param_name] = st.number_input(
                            f"{param_name}",
                            min_value=1,
                            value=param_value,
                            key=f"{ind_name}_{param_name}",
                        )
                    elif isinstance(param_value, float):
                        params[param_name] = st.number_input(
                            f"{param_name}",
                            min_value=0.0,
                            value=param_value,
                            format="%.2f",
                            key=f"{ind_name}_{param_name}",
                        )
                custom_params[ind_name] = params

    return selected_indicators, custom_params, multipliers


def _show_fundamental_options(fund_indicators):
    """顯示基本面指標選項"""
    # 選擇基本面指標
    fund_indicator_names = [ind["name"] for ind in fund_indicators]
    selected_indicators = st.multiselect(
        "選擇基本面指標",
        options=fund_indicator_names,
        default=fund_indicator_names[:3],
    )
    return selected_indicators


def _show_sentiment_options(sent_indicators):
    """顯示情緒指標選項"""
    # 選擇情緒指標
    sent_indicator_names = [ind["name"] for ind in sent_indicators]
    selected_indicators = st.multiselect(
        "選擇情緒指標",
        options=sent_indicator_names,
        default=sent_indicator_names[:2],
    )

    # 選擇情緒來源
    sentiment_sources = st.multiselect(
        "情緒來源",
        options=["新聞", "社交媒體", "論壇", "分析師報告"],
        default=["新聞", "社交媒體"],
    )

    # 選擇情緒主題
    sentiment_topics = st.multiselect(
        "情緒主題",
        options=["財報", "產品", "管理層", "市場", "競爭", "監管"],
        default=["財報", "產品"],
    )

    return selected_indicators, sentiment_sources, sentiment_topics


def _show_stock_date_options(stocks):
    """顯示股票和日期選項"""
    col1, col2 = st.columns(2)

    with col1:
        # 選擇市場
        markets = list(set([s["market"] for s in stocks]))
        selected_markets = st.multiselect(
            "選擇市場", options=markets, default=markets
        )

        # 根據選擇的市場過濾股票
        filtered_stocks = [s for s in stocks if s["market"] in selected_markets]
        stock_options = [f"{s['symbol']} - {s['name']}" for s in filtered_stocks]

        # 選擇股票
        selected_stocks = st.multiselect(
            "選擇股票", options=stock_options, default=[stock_options[0]]
        )

        # 從選擇中提取股票代碼
        selected_symbols = [s.split(" - ")[0] for s in selected_stocks]

        # 手動輸入股票代碼
        custom_symbols = st.text_input("其他股票代碼 (逗號分隔)", "")
        if custom_symbols:
            additional_symbols = [s.strip() for s in custom_symbols.split(",")]
            selected_symbols.extend(additional_symbols)

    with col2:
        # 選擇日期範圍
        start_date = st.date_input("開始日期", datetime.now() - timedelta(days=365))
        end_date = st.date_input("結束日期", datetime.now())

        # 選擇時間框架
        time_frame = st.selectbox("時間框架", ["日線", "小時線", "分鐘線", "Tick"])

    return selected_symbols, start_date, end_date, time_frame


def _show_processing_options():
    """顯示特徵處理選項"""
    processing_options = {}

    with st.expander("特徵處理選項"):
        # 標準化選項
        normalize = st.checkbox("標準化特徵", value=True)
        processing_options["normalize"] = normalize
        if normalize:
            processing_options["normalize_method"] = st.selectbox(
                "標準化方法", ["Z-Score", "Min-Max", "Robust"])

        # 清理數據選項
        clean_data = st.checkbox("清理數據", value=True)
        processing_options["clean_data"] = clean_data
        if clean_data:
            processing_options["fill_method"] = st.selectbox(
                "缺失值填充", ["前值填充", "後值填充", "線性插值"])

            remove_outliers = st.checkbox("移除極端值", value=True)
            processing_options["remove_outliers"] = remove_outliers
            if remove_outliers:
                processing_options["outlier_method"] = st.selectbox(
                    "極端值檢測", ["Z-Score", "IQR", "百分位數"], index=1)

        # 特徵選擇選項
        feature_selection = st.checkbox("特徵選擇", value=False)
        processing_options["feature_selection"] = feature_selection
        if feature_selection:
            processing_options["selection_method"] = st.selectbox(
                "特徵選擇方法", ["方差過濾", "相關性過濾", "統計檢驗"])
            processing_options["selection_k"] = st.slider(
                "保留特徵數量", 1, 50, 10)

    return processing_options


def _handle_calculation_submission(
    feature_service, feature_type, selected_indicators, selected_symbols,
    start_date, end_date, time_frame, processing_options, custom_params
):
    """處理計算提交"""
    if not selected_indicators:
        st.error("請選擇至少一個指標")
        return

    if not selected_symbols:
        st.error("請選擇至少一個股票")
        return

    with st.spinner("正在計算特徵..."):
        # 顯示進度條
        progress_bar = st.progress(0)
        status_text = st.empty()

        # 模擬特徵計算過程
        total_steps = len(selected_symbols) * len(selected_indicators)
        current_step = 0

        for symbol in selected_symbols:
            for indicator in selected_indicators:
                current_step += 1
                progress = current_step / total_steps
                progress_bar.progress(progress)
                status_text.text(f"正在計算 {symbol} 的 {indicator}...")
                
                # 模擬計算時間
                time.sleep(0.5)

        # 完成計算
        progress_bar.progress(1.0)
        status_text.text("特徵計算完成！")

        # 顯示結果
        st.success(f"成功計算了 {len(selected_symbols)} 個股票的 {len(selected_indicators)} 個{feature_type}")

        # 顯示統計
        col1, col2, col3 = st.columns(3)
        col1.metric("處理股票數", len(selected_symbols))
        col2.metric("計算指標數", len(selected_indicators))
        col3.metric("生成特徵數", len(selected_symbols) * len(selected_indicators))

        # 清理顯示
        progress_bar.empty()
        status_text.empty()
