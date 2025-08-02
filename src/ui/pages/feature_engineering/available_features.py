"""
可用特徵展示模組

此模組實現了可用特徵列表的展示功能，包括：
- 技術指標展示
- 基本面指標展示
- 情緒指標展示
- 特徵過濾和搜索
"""

import streamlit as st
from src.ui.components.feature_components import show_feature_card
from .utils import get_feature_service


def show_available_features():
    """顯示可用特徵列表"""
    st.subheader("可用特徵列表")

    # 獲取特徵工程服務
    feature_service = get_feature_service()

    # 獲取可用特徵
    available_features = feature_service.get_available_features()

    tech_indicators = available_features.get("technical", [])
    fund_indicators = available_features.get("fundamental", [])
    sent_indicators = available_features.get("sentiment", [])

    # 創建標籤頁
    tabs = st.tabs(["技術指標", "基本面指標", "情緒指標"])

    # 技術指標標籤頁
    with tabs[0]:
        st.subheader("技術指標")

        if tech_indicators:
            # 過濾選項
            categories = list(set([ind["category"] for ind in tech_indicators]))
            selected_categories = st.multiselect(
                "選擇類別",
                options=categories,
                default=categories,
                key="tech_categories",
            )

            # 過濾指標
            filtered_indicators = [
                ind for ind in tech_indicators if ind["category"] in selected_categories
            ]

            # 顯示指標卡片
            for i in range(0, len(filtered_indicators), 2):
                col1, col2 = st.columns(2)

                with col1:
                    if i < len(filtered_indicators):
                        show_feature_card(filtered_indicators[i], f"tech_{i}")

                with col2:
                    if i + 1 < len(filtered_indicators):
                        show_feature_card(filtered_indicators[i + 1], f"tech_{i+1}")
        else:
            st.info("暫無可用的技術指標")

    # 基本面指標標籤頁
    with tabs[1]:
        st.subheader("基本面指標")

        if fund_indicators:
            # 過濾選項
            categories = list(set([ind["category"] for ind in fund_indicators]))
            selected_categories = st.multiselect(
                "選擇類別",
                options=categories,
                default=categories,
                key="fund_categories",
            )

            # 過濾指標
            filtered_indicators = [
                ind for ind in fund_indicators if ind["category"] in selected_categories
            ]

            # 顯示指標卡片
            for i in range(0, len(filtered_indicators), 2):
                col1, col2 = st.columns(2)

                with col1:
                    if i < len(filtered_indicators):
                        show_feature_card(filtered_indicators[i], f"fund_{i}")

                with col2:
                    if i + 1 < len(filtered_indicators):
                        show_feature_card(filtered_indicators[i + 1], f"fund_{i+1}")
        else:
            st.info("暫無可用的基本面指標")

    # 情緒指標標籤頁
    with tabs[2]:
        st.subheader("情緒指標")

        if sent_indicators:
            # 過濾選項
            categories = list(set([ind["category"] for ind in sent_indicators]))
            selected_categories = st.multiselect(
                "選擇類別",
                options=categories,
                default=categories,
                key="sent_categories",
            )

            # 過濾指標
            filtered_indicators = [
                ind for ind in sent_indicators if ind["category"] in selected_categories
            ]

            # 顯示指標卡片
            for i in range(0, len(filtered_indicators), 2):
                col1, col2 = st.columns(2)

                with col1:
                    if i < len(filtered_indicators):
                        show_feature_card(filtered_indicators[i], f"sent_{i}")

                with col2:
                    if i + 1 < len(filtered_indicators):
                        show_feature_card(filtered_indicators[i + 1], f"sent_{i+1}")
        else:
            st.info("暫無可用的情緒指標")
