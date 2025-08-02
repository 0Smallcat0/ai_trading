"""
特徵工程頁面

此模組實現了特徵工程頁面，提供特徵計算、特徵選擇、特徵查詢和特徵工程日誌功能。
"""

import os
import json
import time
import sqlite3
import numpy as np
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from pathlib import Path
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest, f_regression, mutual_info_regression
from sklearn.ensemble import RandomForestRegressor

# 導入自定義元件
from src.ui.components.tables import data_table, filterable_table
from src.ui.components.charts import line_chart, bar_chart, heatmap
from src.ui.components.notifications import show_notification
from src.ui.components.feature_components import (
    show_feature_card,
    show_calculation_progress,
    show_feature_statistics_chart,
    show_feature_distribution_chart,
    show_outlier_detection_chart,
    show_correlation_heatmap,
    show_feature_importance_chart,
    show_pca_explained_variance_chart,
)

# 導入特徵工程服務
from src.core.feature_engineering_service import FeatureEngineeringService


# 初始化服務
@st.cache_resource
def get_feature_service():
    """獲取特徵工程服務實例"""
    return FeatureEngineeringService()


def get_available_technical_indicators():
    """獲取可用的技術指標"""
    # 實際應用中，這裡應該從系統中獲取真實的技術指標列表
    # 這裡使用模擬數據進行演示

    technical_indicators = [
        {
            "name": "RSI",
            "full_name": "相對強弱指標 (Relative Strength Index)",
            "category": "動量指標",
            "description": "測量價格變動的速度和幅度，用於判斷市場是否超買或超賣。",
            "parameters": {"window": 14},
            "value_range": "0-100",
            "interpretation": "RSI > 70 表示超買，RSI < 30 表示超賣。",
            "calculation_cost": "低",
            "data_requirements": ["close"],
            "example_code": "calculator.calculate_technical_indicators(indicators=['RSI'])",
        },
        {
            "name": "MACD",
            "full_name": "移動平均收斂散度 (Moving Average Convergence Divergence)",
            "category": "趨勢指標",
            "description": "通過比較兩條不同週期的指數移動平均線來判斷趨勢的強度和方向。",
            "parameters": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
            "value_range": "無固定範圍",
            "interpretation": "MACD 線穿越信號線向上表示買入信號，向下表示賣出信號。",
            "calculation_cost": "中",
            "data_requirements": ["close"],
            "example_code": "calculator.calculate_technical_indicators(indicators=['MACD'])",
        },
        {
            "name": "SMA",
            "full_name": "簡單移動平均線 (Simple Moving Average)",
            "category": "趨勢指標",
            "description": "計算過去 N 個週期的價格平均值，用於平滑價格數據和識別趨勢。",
            "parameters": {"window": 20},
            "value_range": "與價格相同",
            "interpretation": "價格穿越 SMA 向上表示上升趨勢，向下表示下降趨勢。",
            "calculation_cost": "低",
            "data_requirements": ["close"],
            "example_code": "calculator.calculate_technical_indicators(indicators=['SMA'])",
        },
        {
            "name": "EMA",
            "full_name": "指數移動平均線 (Exponential Moving Average)",
            "category": "趨勢指標",
            "description": "與 SMA 類似，但給予最近的價格更高的權重，對價格變化反應更敏感。",
            "parameters": {"window": 20},
            "value_range": "與價格相同",
            "interpretation": "價格穿越 EMA 向上表示上升趨勢，向下表示下降趨勢。",
            "calculation_cost": "低",
            "data_requirements": ["close"],
            "example_code": "calculator.calculate_technical_indicators(indicators=['EMA'])",
        },
        {
            "name": "BBANDS",
            "full_name": "布林帶 (Bollinger Bands)",
            "category": "波動指標",
            "description": "由移動平均線加減標準差構成的上下通道，用於判斷價格波動性和可能的反轉點。",
            "parameters": {"window": 20, "std_dev": 2},
            "value_range": "與價格相同",
            "interpretation": "價格接近上軌表示可能超買，接近下軌表示可能超賣。",
            "calculation_cost": "中",
            "data_requirements": ["close"],
            "example_code": "calculator.calculate_technical_indicators(indicators=['BBANDS'])",
        },
        {
            "name": "STOCH",
            "full_name": "隨機指標 (Stochastic Oscillator)",
            "category": "動量指標",
            "description": "比較收盤價與特定時期內的價格範圍，用於判斷市場是否超買或超賣。",
            "parameters": {"fastk_period": 5, "slowk_period": 3, "slowd_period": 3},
            "value_range": "0-100",
            "interpretation": "K 線穿越 D 線向上表示買入信號，向下表示賣出信號。",
            "calculation_cost": "中",
            "data_requirements": ["high", "low", "close"],
            "example_code": "calculator.calculate_technical_indicators(indicators=['STOCH'])",
        },
        {
            "name": "CCI",
            "full_name": "商品通道指數 (Commodity Channel Index)",
            "category": "動量指標",
            "description": "測量當前價格相對於過去一段時間內平均價格的偏離程度。",
            "parameters": {"window": 20},
            "value_range": "通常在 -100 到 +100 之間",
            "interpretation": "CCI > 100 表示超買，CCI < -100 表示超賣。",
            "calculation_cost": "中",
            "data_requirements": ["high", "low", "close"],
            "example_code": "calculator.calculate_technical_indicators(indicators=['CCI'])",
        },
        {
            "name": "ATR",
            "full_name": "平均真實範圍 (Average True Range)",
            "category": "波動指標",
            "description": "測量市場波動性，不考慮價格方向。",
            "parameters": {"window": 14},
            "value_range": "非負數",
            "interpretation": "ATR 值越高表示波動性越大，可用於設置止損點。",
            "calculation_cost": "低",
            "data_requirements": ["high", "low", "close"],
            "example_code": "calculator.calculate_technical_indicators(indicators=['ATR'])",
        },
        {
            "name": "OBV",
            "full_name": "能量潮 (On-Balance Volume)",
            "category": "成交量指標",
            "description": "將成交量與價格變動結合，用於確認價格趨勢。",
            "parameters": {},
            "value_range": "無固定範圍",
            "interpretation": "OBV 與價格同向變動表示趨勢強勁，反向變動表示可能反轉。",
            "calculation_cost": "低",
            "data_requirements": ["close", "volume"],
            "example_code": "calculator.calculate_technical_indicators(indicators=['OBV'])",
        },
        {
            "name": "ADX",
            "full_name": "平均趨向指數 (Average Directional Index)",
            "category": "趨勢指標",
            "description": "測量趨勢的強度，不考慮趨勢方向。",
            "parameters": {"window": 14},
            "value_range": "0-100",
            "interpretation": "ADX > 25 表示強趨勢，ADX < 20 表示弱趨勢。",
            "calculation_cost": "高",
            "data_requirements": ["high", "low", "close"],
            "example_code": "calculator.calculate_technical_indicators(indicators=['ADX'])",
        },
    ]

    return technical_indicators


def get_available_fundamental_indicators():
    """獲取可用的基本面指標"""
    # 實際應用中，這裡應該從系統中獲取真實的基本面指標列表
    # 這裡使用模擬數據進行演示

    fundamental_indicators = [
        {
            "name": "PE",
            "full_name": "本益比 (Price-to-Earnings Ratio)",
            "category": "估值指標",
            "description": "股價與每股盈餘的比率，用於評估股票的估值水平。",
            "calculation": "股價 / 每股盈餘",
            "interpretation": "PE 值越低表示估值越低，但需要與行業平均和歷史水平比較。",
            "data_source": "財務報表",
            "update_frequency": "季度",
            "example_code": "calculator.calculate_fundamental_indicators(indicators=['PE'])",
        },
        {
            "name": "PB",
            "full_name": "股價淨值比 (Price-to-Book Ratio)",
            "category": "估值指標",
            "description": "股價與每股淨資產的比率，用於評估股票的估值水平。",
            "calculation": "股價 / 每股淨資產",
            "interpretation": "PB 值越低表示估值越低，適合評估資產密集型企業。",
            "data_source": "財務報表",
            "update_frequency": "季度",
            "example_code": "calculator.calculate_fundamental_indicators(indicators=['PB'])",
        },
        {
            "name": "ROE",
            "full_name": "股東權益報酬率 (Return on Equity)",
            "category": "獲利能力指標",
            "description": "淨利潤與股東權益的比率，用於評估公司運用股東資金的效率。",
            "calculation": "淨利潤 / 股東權益",
            "interpretation": "ROE 越高表示公司運用股東資金的效率越高。",
            "data_source": "財務報表",
            "update_frequency": "季度",
            "example_code": "calculator.calculate_fundamental_indicators(indicators=['ROE'])",
        },
        {
            "name": "ROA",
            "full_name": "資產報酬率 (Return on Assets)",
            "category": "獲利能力指標",
            "description": "淨利潤與總資產的比率，用於評估公司運用資產的效率。",
            "calculation": "淨利潤 / 總資產",
            "interpretation": "ROA 越高表示公司運用資產的效率越高。",
            "data_source": "財務報表",
            "update_frequency": "季度",
            "example_code": "calculator.calculate_fundamental_indicators(indicators=['ROA'])",
        },
        {
            "name": "DY",
            "full_name": "股息殖利率 (Dividend Yield)",
            "category": "收益指標",
            "description": "年度股息與股價的比率，用於評估股票的收益水平。",
            "calculation": "年度股息 / 股價",
            "interpretation": "DY 越高表示股票的收益水平越高，適合收益型投資者。",
            "data_source": "財務報表",
            "update_frequency": "年度",
            "example_code": "calculator.calculate_fundamental_indicators(indicators=['DY'])",
        },
        {
            "name": "DE",
            "full_name": "負債權益比 (Debt-to-Equity Ratio)",
            "category": "財務結構指標",
            "description": "總負債與股東權益的比率，用於評估公司的財務槓桿。",
            "calculation": "總負債 / 股東權益",
            "interpretation": "DE 越高表示公司的財務槓桿越高，風險也越高。",
            "data_source": "財務報表",
            "update_frequency": "季度",
            "example_code": "calculator.calculate_fundamental_indicators(indicators=['DE'])",
        },
        {
            "name": "CR",
            "full_name": "流動比率 (Current Ratio)",
            "category": "流動性指標",
            "description": "流動資產與流動負債的比率，用於評估公司的短期償債能力。",
            "calculation": "流動資產 / 流動負債",
            "interpretation": "CR > 1 表示公司有足夠的流動資產償還短期債務。",
            "data_source": "財務報表",
            "update_frequency": "季度",
            "example_code": "calculator.calculate_fundamental_indicators(indicators=['CR'])",
        },
        {
            "name": "EPS_G",
            "full_name": "每股盈餘成長率 (EPS Growth Rate)",
            "category": "成長指標",
            "description": "每股盈餘的年度成長率，用於評估公司的盈利成長性。",
            "calculation": "(本期 EPS - 上期 EPS) / 上期 EPS",
            "interpretation": "EPS_G 越高表示公司的盈利成長性越好。",
            "data_source": "財務報表",
            "update_frequency": "季度",
            "example_code": "calculator.calculate_fundamental_indicators(indicators=['EPS_G'])",
        },
    ]

    return fundamental_indicators


def get_available_sentiment_indicators():
    """獲取可用的情緒指標"""
    # 實際應用中，這裡應該從系統中獲取真實的情緒指標列表
    # 這裡使用模擬數據進行演示

    sentiment_indicators = [
        {
            "name": "NEWS_SENT",
            "full_name": "新聞情緒指標 (News Sentiment)",
            "category": "媒體情緒",
            "description": "基於新聞報導的情緒分析，用於評估市場對特定股票或行業的情緒。",
            "calculation": "使用 NLP 模型分析新聞文本，計算情緒分數。",
            "value_range": "-1 到 1",
            "interpretation": "值越接近 1 表示正面情緒越強，越接近 -1 表示負面情緒越強。",
            "data_source": "新聞 API",
            "update_frequency": "每日",
            "example_code": "calculator.calculate_sentiment_indicators(indicators=['NEWS_SENT'])",
        },
        {
            "name": "SOCIAL_SENT",
            "full_name": "社交媒體情緒指標 (Social Media Sentiment)",
            "category": "社交媒體情緒",
            "description": "基於社交媒體的情緒分析，用於評估散戶投資者對特定股票的情緒。",
            "calculation": "使用 NLP 模型分析社交媒體文本，計算情緒分數。",
            "value_range": "-1 到 1",
            "interpretation": "值越接近 1 表示正面情緒越強，越接近 -1 表示負面情緒越強。",
            "data_source": "社交媒體 API",
            "update_frequency": "每小時",
            "example_code": "calculator.calculate_sentiment_indicators(indicators=['SOCIAL_SENT'])",
        },
        {
            "name": "SENT_VOL",
            "full_name": "情緒波動指標 (Sentiment Volatility)",
            "category": "情緒波動",
            "description": "測量情緒分數的波動性，用於評估市場情緒的穩定性。",
            "calculation": "情緒分數的標準差",
            "value_range": "非負數",
            "interpretation": "值越高表示情緒波動越大，市場不確定性越高。",
            "data_source": "新聞和社交媒體 API",
            "update_frequency": "每日",
            "example_code": "calculator.calculate_sentiment_indicators(indicators=['SENT_VOL'])",
        },
        {
            "name": "SENT_DIFF",
            "full_name": "情緒差異指標 (Sentiment Differential)",
            "category": "情緒差異",
            "description": "測量不同來源情緒分數的差異，用於評估市場情緒的一致性。",
            "calculation": "新聞情緒分數 - 社交媒體情緒分數",
            "value_range": "-2 到 2",
            "interpretation": "值接近 0 表示不同來源的情緒一致，絕對值越大表示差異越大。",
            "data_source": "新聞和社交媒體 API",
            "update_frequency": "每日",
            "example_code": "calculator.calculate_sentiment_indicators(indicators=['SENT_DIFF'])",
        },
        {
            "name": "TOPIC_SENT",
            "full_name": "主題情緒指標 (Topic Sentiment)",
            "category": "主題情緒",
            "description": "針對特定主題的情緒分析，如產品發布、財報、管理層變動等。",
            "calculation": "使用 NLP 模型分析特定主題的文本，計算情緒分數。",
            "value_range": "-1 到 1",
            "interpretation": "值越接近 1 表示對特定主題的正面情緒越強。",
            "data_source": "新聞和社交媒體 API",
            "update_frequency": "事件驅動",
            "example_code": "calculator.calculate_sentiment_indicators(indicators=['TOPIC_SENT'], topics=['earnings'])",
        },
    ]

    return sentiment_indicators


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


def get_stock_list():
    """獲取股票列表"""
    # 實際應用中，這裡應該從系統中獲取真實的股票列表
    # 這裡使用模擬數據進行演示
    return [
        {"symbol": "2330.TW", "name": "台積電", "market": "台股"},
        {"symbol": "2317.TW", "name": "鴻海", "market": "台股"},
        {"symbol": "2454.TW", "name": "聯發科", "market": "台股"},
        {"symbol": "2308.TW", "name": "台達電", "market": "台股"},
        {"symbol": "2412.TW", "name": "中華電", "market": "台股"},
        {"symbol": "AAPL", "name": "蘋果", "market": "美股"},
        {"symbol": "MSFT", "name": "微軟", "market": "美股"},
        {"symbol": "GOOGL", "name": "Alphabet", "market": "美股"},
        {"symbol": "AMZN", "name": "亞馬遜", "market": "美股"},
        {"symbol": "TSLA", "name": "特斯拉", "market": "美股"},
    ]


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
            with st.expander("高級參數設置"):
                # 為每個選定的指標提供參數設置
                custom_params = {}
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
                        for param_name, param_value in ind.get(
                            "parameters", {}
                        ).items():
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

        elif feature_type == "基本面指標":
            # 選擇基本面指標
            fund_indicator_names = [ind["name"] for ind in fund_indicators]
            selected_indicators = st.multiselect(
                "選擇基本面指標",
                options=fund_indicator_names,
                default=fund_indicator_names[:3],
            )

        elif feature_type == "情緒指標":
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

        elif feature_type == "自定義特徵":
            # 自定義特徵代碼
            custom_code = st.text_area(
                "自定義特徵代碼",
                value="""def calculate_custom_feature(data):
    # 自定義特徵計算邏輯
    # 例如：計算價格與成交量的比率
    price_volume_ratio = data['close'] / data['volume']
    return price_volume_ratio""",
                height=200,
            )

            # 自定義特徵名稱
            custom_name = st.text_input("自定義特徵名稱", "price_volume_ratio")

        # 選擇股票
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

            # 也允許手動輸入
            custom_symbols = st.text_input(
                "其他股票代碼 (多個代碼請用逗號分隔)",
                "",
                help="輸入其他未列出的股票代碼",
            )

            if custom_symbols:
                # 合併手動輸入的股票代碼
                additional_symbols = [s.strip() for s in custom_symbols.split(",")]
                selected_symbols.extend(additional_symbols)

        with col2:
            # 選擇日期範圍
            start_date = st.date_input(
                "開始日期",
                datetime.now() - timedelta(days=365),
                help="選擇特徵計算的開始日期",
            )

            end_date = st.date_input(
                "結束日期", datetime.now(), help="選擇特徵計算的結束日期"
            )

            # 選擇時間框架
            time_frame = st.selectbox(
                "時間框架",
                options=["日線", "小時線", "分鐘線", "Tick"],
                index=0,
                help="選擇特徵計算的時間粒度",
            )

        # 特徵處理選項
        with st.expander("特徵處理選項"):
            # 標準化選項
            normalize = st.checkbox(
                "標準化特徵", value=True, help="將特徵標準化到相同的尺度"
            )

            if normalize:
                normalize_method = st.selectbox(
                    "標準化方法",
                    options=["Z-Score", "Min-Max", "Robust"],
                    index=0,
                    help="選擇標準化方法",
                )

            # 清理數據選項
            clean_data = st.checkbox("清理數據", value=True, help="清理缺失值和異常值")

            if clean_data:
                fill_method = st.selectbox(
                    "缺失值填充方法",
                    options=[
                        "前值填充",
                        "後值填充",
                        "線性插值",
                        "均值填充",
                        "中位數填充",
                    ],
                    index=0,
                    help="選擇缺失值填充方法",
                )

                remove_outliers = st.checkbox(
                    "移除極端值", value=True, help="移除超出正常範圍的極端值"
                )

                if remove_outliers:
                    outlier_method = st.selectbox(
                        "極端值檢測方法",
                        options=["Z-Score", "IQR", "百分位數"],
                        index=1,
                        help="選擇極端值檢測方法",
                    )

            # 特徵選擇選項
            feature_selection = st.checkbox(
                "特徵選擇", value=False, help="選擇最重要的特徵"
            )

            if feature_selection:
                selection_method = st.selectbox(
                    "特徵選擇方法",
                    options=["F 檢定", "互信息", "隨機森林", "Lasso"],
                    index=0,
                    help="選擇特徵選擇方法",
                )

                k_features = st.slider(
                    "選擇特徵數量",
                    min_value=1,
                    max_value=50,
                    value=10,
                    help="選擇要保留的特徵數量",
                )

            # 降維選項
            dimensionality_reduction = st.checkbox(
                "降維", value=False, help="降低特徵維度"
            )

            if dimensionality_reduction:
                reduction_method = st.selectbox(
                    "降維方法",
                    options=["PCA", "t-SNE", "UMAP"],
                    index=0,
                    help="選擇降維方法",
                )

                n_components = st.slider(
                    "組件數量",
                    min_value=2,
                    max_value=20,
                    value=5,
                    help="選擇要保留的組件數量",
                )

        # 計算選項
        with st.expander("計算選項"):
            # 分散式處理
            use_distributed = st.checkbox(
                "使用分散式處理", value=False, help="使用分散式處理加速計算"
            )

            if use_distributed:
                parallel_jobs = st.slider(
                    "並行任務數",
                    min_value=1,
                    max_value=10,
                    value=4,
                    help="同時執行的計算任務數量",
                )

            # 記憶體選項
            memory_efficient = st.checkbox(
                "記憶體高效模式", value=False, help="使用記憶體高效的計算方式"
            )

            if memory_efficient:
                chunk_size = st.number_input(
                    "分塊大小",
                    min_value=1000,
                    max_value=100000,
                    value=10000,
                    step=1000,
                    help="每個計算分塊的大小",
                )

            # 儲存選項
            save_to_feature_store = st.checkbox(
                "儲存到特徵存儲", value=True, help="將計算結果儲存到特徵存儲"
            )

            if save_to_feature_store:
                feature_name = st.text_input("特徵名稱", "combined_features")

                feature_tags = st.text_input(
                    "特徵標籤 (多個標籤請用逗號分隔)", "技術指標, 基本面, 情緒"
                )

        # 提交按鈕
        submitted = st.form_submit_button("開始計算")

    # 處理表單提交
    if submitted:
        # 顯示計算參數摘要
        st.info("計算參數摘要")

        # 準備參數摘要
        summary_data = {
            "特徵類型": feature_type,
            "選擇的指標": ", ".join(selected_indicators),
            "選擇的股票": ", ".join(selected_symbols),
            "日期範圍": f"{start_date} 至 {end_date}",
            "時間框架": time_frame,
        }

        # 根據特徵類型添加特定參數
        if feature_type == "技術指標":
            summary_data["參數倍數"] = ", ".join(multipliers)
        elif feature_type == "情緒指標":
            summary_data["情緒來源"] = ", ".join(sentiment_sources)
            summary_data["情緒主題"] = ", ".join(sentiment_topics)

        # 添加處理選項
        processing_options = []
        if normalize:
            processing_options.append(f"標準化 ({normalize_method})")
        if clean_data:
            processing_options.append(f"清理數據 ({fill_method})")
            if remove_outliers:
                processing_options.append(f"移除極端值 ({outlier_method})")
        if feature_selection:
            processing_options.append(f"特徵選擇 ({selection_method}, k={k_features})")
        if dimensionality_reduction:
            processing_options.append(f"降維 ({reduction_method}, n={n_components})")

        summary_data["處理選項"] = ", ".join(processing_options)

        # 添加計算選項
        computation_options = []
        if use_distributed:
            computation_options.append(f"分散式處理 (並行任務數={parallel_jobs})")
        if memory_efficient:
            computation_options.append(f"記憶體高效模式 (分塊大小={chunk_size})")
        if save_to_feature_store:
            computation_options.append(f"儲存到特徵存儲 (名稱={feature_name})")

        summary_data["計算選項"] = ", ".join(computation_options)

        # 顯示參數摘要
        for key, value in summary_data.items():
            st.write(f"**{key}**: {value}")

        # 確認計算
        if st.button("確認並執行計算"):
            if not selected_indicators:
                st.error("請選擇至少一個特徵指標")
                return

            if not selected_symbols:
                st.error("請選擇至少一個股票")
                return

            # 啟動特徵計算任務
            feature_service = get_feature_service()

            # 準備參數
            feature_type_map = {
                "技術指標": "technical",
                "基本面指標": "fundamental",
                "情緒指標": "sentiment",
            }

            task_id = feature_service.start_feature_calculation(
                feature_type=feature_type_map[feature_type],
                stock_ids=selected_symbols,
                start_date=start_date,
                end_date=end_date,
                indicators=selected_indicators,
                parameters={},
            )

            st.success(f"特徵計算任務已啟動！任務ID: {task_id}")

            # 顯示進度追蹤
            st.subheader("計算進度")

            # 創建進度顯示容器
            progress_container = st.container()

            # 輪詢任務狀態
            max_polls = 60  # 最多輪詢60次
            poll_count = 0

            while poll_count < max_polls:
                task_status = feature_service.get_task_status(task_id)

                with progress_container:
                    st.empty()  # 清空容器
                    show_calculation_progress(task_status)

                if task_status.get("status") in ["completed", "failed"]:
                    break

                time.sleep(1)  # 等待1秒後再次檢查
                poll_count += 1

            # 最終狀態檢查
            final_status = feature_service.get_task_status(task_id)

            if final_status.get("status") == "completed":
                st.success("特徵計算已成功完成！")
            elif final_status.get("status") == "failed":
                st.error(f"特徵計算失敗: {final_status.get('message', '未知錯誤')}")
            else:
                st.warning("特徵計算仍在進行中，請稍後查看任務狀態")

                # 顯示計算結果摘要
                st.subheader("計算結果摘要")

                # 模擬計算結果
                result_data = {
                    "計算的特徵數量": len(selected_indicators) * len(selected_symbols),
                    "生成的特徵列數": (
                        len(selected_indicators) * len(multipliers)
                        if feature_type == "技術指標"
                        else len(selected_indicators)
                    ),
                    "資料點數量": (end_date - start_date).days * len(selected_symbols),
                    "特徵矩陣形狀": f"{(end_date - start_date).days * len(selected_symbols)} x {len(selected_indicators) * 3}",
                    "計算時間": f"{len(selected_indicators) * len(selected_symbols) * 0.5:.1f} 秒",
                    "記憶體使用": f"{len(selected_indicators) * len(selected_symbols) * 0.5:.1f} MB",
                }

                # 顯示結果摘要
                col1, col2 = st.columns(2)

                with col1:
                    for key, value in list(result_data.items())[:3]:
                        st.metric(key, value)

                with col2:
                    for key, value in list(result_data.items())[3:]:
                        st.metric(key, value)

                # 顯示特徵預覽
                st.subheader("特徵預覽")

                # 模擬特徵數據
                feature_preview = {}
                feature_preview["日期"] = pd.date_range(
                    start=start_date, end=start_date + timedelta(days=5)
                )

                for symbol in selected_symbols[:2]:  # 只顯示前兩個股票
                    for ind in selected_indicators[:3]:  # 只顯示前三個指標
                        # 生成隨機數據
                        np.random.seed(hash(symbol + ind) % 10000)
                        feature_preview[f"{symbol}_{ind}"] = (
                            np.random.randn(6) * 10 + 50
                        )

                # 創建 DataFrame
                preview_df = pd.DataFrame(feature_preview)

                # 顯示預覽
                st.dataframe(preview_df, use_container_width=True)

                # 提供下載選項
                st.download_button(
                    label="下載特徵數據 (CSV)",
                    data=preview_df.to_csv(index=False).encode("utf-8"),
                    file_name=f"features_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                )


def get_mock_feature_data(feature_type, symbols, start_date, end_date):
    """獲取模擬特徵數據"""
    # 創建日期範圍
    date_range = pd.date_range(start=start_date, end=end_date, freq="B")  # 只包含工作日

    # 創建基本數據框
    data = {"日期": date_range}

    # 根據特徵類型生成不同的特徵
    if feature_type == "技術指標":
        # 獲取技術指標列表
        tech_indicators = get_available_technical_indicators()
        tech_indicator_names = [ind["name"] for ind in tech_indicators]

        # 為每個股票生成技術指標
        for symbol in symbols:
            # 使用股票代碼作為隨機種子，確保同一股票每次生成相同數據
            np.random.seed(hash(symbol) % 10000)

            # 為每個技術指標生成數據
            for ind_name in tech_indicator_names[:5]:  # 只使用前 5 個指標
                # 生成隨機數據
                if ind_name in ["RSI", "STOCH", "CCI", "ADX"]:  # 有範圍限制的指標
                    values = np.random.uniform(0, 100, len(date_range))
                else:  # 無範圍限制的指標
                    base_value = 100 + hash(symbol + ind_name) % 900
                    values = np.random.normal(
                        base_value, base_value * 0.1, len(date_range)
                    )

                # 添加到數據框
                data[f"{symbol}_{ind_name}"] = values

    elif feature_type == "基本面指標":
        # 獲取基本面指標列表
        fund_indicators = get_available_fundamental_indicators()
        fund_indicator_names = [ind["name"] for ind in fund_indicators]

        # 為每個股票生成基本面指標
        for symbol in symbols:
            # 使用股票代碼作為隨機種子，確保同一股票每次生成相同數據
            np.random.seed(hash(symbol) % 10000)

            # 為每個基本面指標生成數據
            for ind_name in fund_indicator_names[:5]:  # 只使用前 5 個指標
                # 生成隨機數據
                if ind_name in ["PE", "PB"]:  # 估值指標
                    values = np.random.uniform(5, 50, len(date_range))
                elif ind_name in ["ROE", "ROA", "DY"]:  # 收益率指標
                    values = (
                        np.random.uniform(0, 0.3, len(date_range)) * 100
                    )  # 轉換為百分比
                else:  # 其他指標
                    values = np.random.uniform(0.5, 2.0, len(date_range))

                # 添加到數據框
                data[f"{symbol}_{ind_name}"] = values

    elif feature_type == "情緒指標":
        # 獲取情緒指標列表
        sent_indicators = get_available_sentiment_indicators()
        sent_indicator_names = [ind["name"] for ind in sent_indicators]

        # 為每個股票生成情緒指標
        for symbol in symbols:
            # 使用股票代碼作為隨機種子，確保同一股票每次生成相同數據
            np.random.seed(hash(symbol) % 10000)

            # 為每個情緒指標生成數據
            for ind_name in sent_indicator_names:  # 使用所有情緒指標
                # 生成隨機數據
                if ind_name in ["NEWS_SENT", "SOCIAL_SENT", "TOPIC_SENT"]:  # 情緒分數
                    values = np.random.uniform(-1, 1, len(date_range))
                elif ind_name == "SENT_VOL":  # 波動性
                    values = np.random.uniform(0, 0.5, len(date_range))
                else:  # 其他指標
                    values = np.random.uniform(-2, 2, len(date_range))

                # 添加到數據框
                data[f"{symbol}_{ind_name}"] = values

    # 創建 DataFrame
    df = pd.DataFrame(data)

    return df


def show_feature_query():
    """顯示特徵查詢頁面"""
    st.subheader("特徵查詢")

    # 獲取可用的技術指標、基本面指標和情緒指標
    tech_indicators = get_available_technical_indicators()
    fund_indicators = get_available_fundamental_indicators()
    sent_indicators = get_available_sentiment_indicators()

    # 獲取股票列表
    stocks = get_stock_list()

    # 創建查詢表單
    with st.form("feature_query_form"):
        # 選擇特徵類型
        feature_type = st.radio(
            "特徵類型",
            ["技術指標", "基本面指標", "情緒指標", "所有特徵"],
            horizontal=True,
        )

        # 根據特徵類型顯示不同的選項
        if feature_type == "技術指標":
            # 選擇技術指標
            tech_indicator_names = [ind["name"] for ind in tech_indicators]
            selected_indicators = st.multiselect(
                "選擇技術指標",
                options=tech_indicator_names,
                default=tech_indicator_names[:3],
            )
        elif feature_type == "基本面指標":
            # 選擇基本面指標
            fund_indicator_names = [ind["name"] for ind in fund_indicators]
            selected_indicators = st.multiselect(
                "選擇基本面指標",
                options=fund_indicator_names,
                default=fund_indicator_names[:3],
            )
        elif feature_type == "情緒指標":
            # 選擇情緒指標
            sent_indicator_names = [ind["name"] for ind in sent_indicators]
            selected_indicators = st.multiselect(
                "選擇情緒指標",
                options=sent_indicator_names,
                default=sent_indicator_names[:2],
            )
        else:  # 所有特徵
            # 選擇所有類型的指標
            all_indicator_names = (
                [f"技術_{ind['name']}" for ind in tech_indicators]
                + [f"基本面_{ind['name']}" for ind in fund_indicators]
                + [f"情緒_{ind['name']}" for ind in sent_indicators]
            )
            selected_indicators = st.multiselect(
                "選擇特徵", options=all_indicator_names, default=all_indicator_names[:5]
            )

        # 選擇股票
        col1, col2 = st.columns(2)

        with col1:
            # 選擇市場
            markets = list(set([s["market"] for s in stocks]))
            selected_markets = st.multiselect(
                "選擇市場", options=markets, default=markets, key="query_markets"
            )

            # 根據選擇的市場過濾股票
            filtered_stocks = [s for s in stocks if s["market"] in selected_markets]
            stock_options = [f"{s['symbol']} - {s['name']}" for s in filtered_stocks]

            # 選擇股票
            selected_stocks = st.multiselect(
                "選擇股票",
                options=stock_options,
                default=[stock_options[0]],
                key="query_stocks",
            )

            # 從選擇中提取股票代碼
            selected_symbols = [s.split(" - ")[0] for s in selected_stocks]

            # 也允許手動輸入
            custom_symbols = st.text_input(
                "其他股票代碼 (多個代碼請用逗號分隔)",
                "",
                help="輸入其他未列出的股票代碼",
                key="query_custom_symbols",
            )

            if custom_symbols:
                # 合併手動輸入的股票代碼
                additional_symbols = [s.strip() for s in custom_symbols.split(",")]
                selected_symbols.extend(additional_symbols)

        with col2:
            # 選擇日期範圍
            start_date = st.date_input(
                "開始日期",
                datetime.now() - timedelta(days=90),
                help="選擇特徵查詢的開始日期",
                key="query_start_date",
            )

            end_date = st.date_input(
                "結束日期",
                datetime.now(),
                help="選擇特徵查詢的結束日期",
                key="query_end_date",
            )

            # 選擇時間框架
            time_frame = st.selectbox(
                "時間框架",
                options=["日線", "小時線", "分鐘線", "Tick"],
                index=0,
                help="選擇特徵查詢的時間粒度",
                key="query_time_frame",
            )

        # 查詢選項
        with st.expander("查詢選項"):
            # 過濾選項
            filter_options = st.checkbox("啟用過濾", value=False, help="啟用特徵值過濾")

            if filter_options:
                filter_type = st.selectbox(
                    "過濾類型",
                    options=["數值範圍", "百分位數", "標準差"],
                    index=0,
                    help="選擇過濾類型",
                )

                if filter_type == "數值範圍":
                    min_value = st.number_input("最小值", value=0.0, format="%.2f")
                    max_value = st.number_input("最大值", value=100.0, format="%.2f")
                elif filter_type == "百分位數":
                    lower_percentile = st.slider("下限百分位數", 0, 100, 5)
                    upper_percentile = st.slider("上限百分位數", 0, 100, 95)
                elif filter_type == "標準差":
                    std_multiplier = st.slider("標準差倍數", 1.0, 5.0, 2.0, 0.1)

            # 排序選項
            sort_options = st.checkbox("啟用排序", value=False, help="啟用特徵值排序")

            if sort_options:
                sort_by = st.selectbox(
                    "排序依據", options=["日期", "特徵值"], index=0, help="選擇排序依據"
                )

                sort_order = st.radio(
                    "排序順序",
                    options=["升序", "降序"],
                    index=0,
                    horizontal=True,
                    help="選擇排序順序",
                )

            # 分組選項
            group_options = st.checkbox("啟用分組", value=False, help="啟用特徵值分組")

            if group_options:
                group_by = st.selectbox(
                    "分組依據",
                    options=["股票", "日期", "特徵"],
                    index=0,
                    help="選擇分組依據",
                )

                agg_function = st.selectbox(
                    "聚合函數",
                    options=["平均值", "最大值", "最小值", "總和", "計數"],
                    index=0,
                    help="選擇聚合函數",
                )

        # 提交按鈕
        submitted = st.form_submit_button("查詢")

    # 處理表單提交
    if submitted and selected_symbols:
        with st.spinner("正在查詢特徵..."):
            # 模擬查詢過程
            time.sleep(1)

            # 獲取模擬特徵數據
            if feature_type == "所有特徵":
                # 獲取所有類型的特徵數據
                tech_data = get_mock_feature_data(
                    "技術指標", selected_symbols, start_date, end_date
                )
                fund_data = get_mock_feature_data(
                    "基本面指標", selected_symbols, start_date, end_date
                )
                sent_data = get_mock_feature_data(
                    "情緒指標", selected_symbols, start_date, end_date
                )

                # 合併數據
                feature_data = tech_data.merge(fund_data, on="日期").merge(
                    sent_data, on="日期"
                )
            else:
                # 獲取指定類型的特徵數據
                feature_data = get_mock_feature_data(
                    feature_type, selected_symbols, start_date, end_date
                )

            # 應用過濾
            if filter_options:
                if filter_type == "數值範圍":
                    # 過濾數值範圍
                    for col in feature_data.columns:
                        if col != "日期":
                            feature_data = feature_data[
                                (feature_data[col] >= min_value)
                                & (feature_data[col] <= max_value)
                            ]
                elif filter_type == "百分位數":
                    # 過濾百分位數
                    for col in feature_data.columns:
                        if col != "日期":
                            lower = np.percentile(feature_data[col], lower_percentile)
                            upper = np.percentile(feature_data[col], upper_percentile)
                            feature_data = feature_data[
                                (feature_data[col] >= lower)
                                & (feature_data[col] <= upper)
                            ]
                elif filter_type == "標準差":
                    # 過濾標準差
                    for col in feature_data.columns:
                        if col != "日期":
                            mean = feature_data[col].mean()
                            std = feature_data[col].std()
                            feature_data = feature_data[
                                (feature_data[col] >= mean - std_multiplier * std)
                                & (feature_data[col] <= mean + std_multiplier * std)
                            ]

            # 應用排序
            if sort_options:
                if sort_by == "日期":
                    feature_data = feature_data.sort_values(
                        by="日期", ascending=(sort_order == "升序")
                    )
                elif sort_by == "特徵值":
                    # 選擇第一個非日期列進行排序
                    sort_col = next(
                        (col for col in feature_data.columns if col != "日期"), None
                    )
                    if sort_col:
                        feature_data = feature_data.sort_values(
                            by=sort_col, ascending=(sort_order == "升序")
                        )

            # 應用分組
            if group_options:
                if group_by == "股票":
                    # 按股票分組
                    # 提取股票代碼
                    stock_pattern = "|".join(selected_symbols)
                    feature_cols = [
                        col for col in feature_data.columns if col != "日期"
                    ]

                    # 創建分組數據
                    grouped_data = pd.DataFrame({"日期": feature_data["日期"].unique()})

                    for symbol in selected_symbols:
                        # 選擇該股票的列
                        symbol_cols = [col for col in feature_cols if symbol in col]

                        if symbol_cols:
                            # 計算聚合值
                            if agg_function == "平均值":
                                grouped_data[symbol] = feature_data[symbol_cols].mean(
                                    axis=1
                                )
                            elif agg_function == "最大值":
                                grouped_data[symbol] = feature_data[symbol_cols].max(
                                    axis=1
                                )
                            elif agg_function == "最小值":
                                grouped_data[symbol] = feature_data[symbol_cols].min(
                                    axis=1
                                )
                            elif agg_function == "總和":
                                grouped_data[symbol] = feature_data[symbol_cols].sum(
                                    axis=1
                                )
                            elif agg_function == "計數":
                                grouped_data[symbol] = feature_data[symbol_cols].count(
                                    axis=1
                                )

                    feature_data = grouped_data

                elif group_by == "日期":
                    # 按日期分組
                    # 設置日期為索引
                    feature_data = feature_data.set_index("日期")

                    # 按週、月或季度重採樣
                    resample_rule = st.selectbox(
                        "重採樣規則", options=["週", "月", "季度"], index=1
                    )

                    if resample_rule == "週":
                        rule = "W"
                    elif resample_rule == "月":
                        rule = "M"
                    else:  # 季度
                        rule = "Q"

                    # 應用聚合函數
                    if agg_function == "平均值":
                        feature_data = feature_data.resample(rule).mean()
                    elif agg_function == "最大值":
                        feature_data = feature_data.resample(rule).max()
                    elif agg_function == "最小值":
                        feature_data = feature_data.resample(rule).min()
                    elif agg_function == "總和":
                        feature_data = feature_data.resample(rule).sum()
                    elif agg_function == "計數":
                        feature_data = feature_data.resample(rule).count()

                    # 重置索引
                    feature_data = feature_data.reset_index()

                elif group_by == "特徵":
                    # 按特徵類型分組
                    # 提取特徵類型
                    feature_types = []
                    if feature_type == "技術指標":
                        feature_types = [ind["category"] for ind in tech_indicators]
                    elif feature_type == "基本面指標":
                        feature_types = [ind["category"] for ind in fund_indicators]
                    elif feature_type == "情緒指標":
                        feature_types = [ind["category"] for ind in sent_indicators]
                    else:  # 所有特徵
                        feature_types = (
                            [ind["category"] for ind in tech_indicators]
                            + [ind["category"] for ind in fund_indicators]
                            + [ind["category"] for ind in sent_indicators]
                        )

                    # 創建分組數據
                    grouped_data = pd.DataFrame({"日期": feature_data["日期"].unique()})

                    for feature_type in set(feature_types):
                        # 選擇該類型的列
                        type_cols = []
                        for col in feature_data.columns:
                            if col != "日期":
                                # 這裡簡化處理，實際應用中需要更精確的映射
                                if "RSI" in col or "STOCH" in col or "CCI" in col:
                                    if feature_type == "動量指標":
                                        type_cols.append(col)
                                elif (
                                    "SMA" in col
                                    or "EMA" in col
                                    or "MACD" in col
                                    or "ADX" in col
                                ):
                                    if feature_type == "趨勢指標":
                                        type_cols.append(col)
                                elif "BBANDS" in col or "ATR" in col:
                                    if feature_type == "波動指標":
                                        type_cols.append(col)
                                elif "OBV" in col:
                                    if feature_type == "成交量指標":
                                        type_cols.append(col)
                                elif "PE" in col or "PB" in col:
                                    if feature_type == "估值指標":
                                        type_cols.append(col)
                                elif "ROE" in col or "ROA" in col:
                                    if feature_type == "獲利能力指標":
                                        type_cols.append(col)
                                elif "NEWS_SENT" in col or "SOCIAL_SENT" in col:
                                    if (
                                        feature_type == "媒體情緒"
                                        or feature_type == "社交媒體情緒"
                                    ):
                                        type_cols.append(col)

                        if type_cols:
                            # 計算聚合值
                            if agg_function == "平均值":
                                grouped_data[feature_type] = feature_data[
                                    type_cols
                                ].mean(axis=1)
                            elif agg_function == "最大值":
                                grouped_data[feature_type] = feature_data[
                                    type_cols
                                ].max(axis=1)
                            elif agg_function == "最小值":
                                grouped_data[feature_type] = feature_data[
                                    type_cols
                                ].min(axis=1)
                            elif agg_function == "總和":
                                grouped_data[feature_type] = feature_data[
                                    type_cols
                                ].sum(axis=1)
                            elif agg_function == "計數":
                                grouped_data[feature_type] = feature_data[
                                    type_cols
                                ].count(axis=1)

                    feature_data = grouped_data

            # 顯示查詢結果
            st.subheader("查詢結果")
            st.write(f"共找到 {len(feature_data)} 條記錄")

            # 顯示數據表格
            st.dataframe(feature_data, use_container_width=True)

            # 提供下載選項
            st.download_button(
                label="下載查詢結果 (CSV)",
                data=feature_data.to_csv(index=False).encode("utf-8"),
                file_name=f"feature_query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )

            # 顯示特徵分布
            st.subheader("特徵分布")

            # 選擇要顯示的特徵
            feature_cols = [col for col in feature_data.columns if col != "日期"]
            if feature_cols:
                selected_feature = st.selectbox("選擇特徵", options=feature_cols)

                # 顯示統計摘要
                st.subheader(f"{selected_feature} 統計摘要")

                # 計算統計量
                stats = feature_data[selected_feature].describe()

                # 顯示統計量
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("平均值", f"{stats['mean']:.2f}")

                with col2:
                    st.metric("標準差", f"{stats['std']:.2f}")

                with col3:
                    st.metric("最小值", f"{stats['min']:.2f}")

                with col4:
                    st.metric("最大值", f"{stats['max']:.2f}")

                # 顯示分布圖
                st.subheader(f"{selected_feature} 分布圖")

                # 創建直方圖
                fig = px.histogram(
                    feature_data,
                    x=selected_feature,
                    nbins=50,
                    marginal="box",
                    title=f"{selected_feature} 分布",
                )

                st.plotly_chart(fig, use_container_width=True)

                # 顯示時間序列圖
                st.subheader(f"{selected_feature} 時間序列圖")

                # 創建時間序列圖
                fig = px.line(
                    feature_data,
                    x="日期",
                    y=selected_feature,
                    title=f"{selected_feature} 時間序列",
                )

                st.plotly_chart(fig, use_container_width=True)

                # 顯示異常值檢測
                st.subheader("異常值檢測")

                # 選擇異常值檢測方法
                outlier_method = st.selectbox(
                    "異常值檢測方法", options=["Z-Score", "IQR", "百分位數"], index=1
                )

                # 檢測異常值
                if outlier_method == "Z-Score":
                    z_scores = np.abs(
                        (feature_data[selected_feature] - stats["mean"]) / stats["std"]
                    )
                    threshold = 3
                    outliers = feature_data[z_scores > threshold]
                    st.write(
                        f"使用 Z-Score 方法 (閾值 = {threshold}) 檢測到 {len(outliers)} 個異常值"
                    )

                elif outlier_method == "IQR":
                    q1 = np.percentile(feature_data[selected_feature], 25)
                    q3 = np.percentile(feature_data[selected_feature], 75)
                    iqr = q3 - q1
                    lower_bound = q1 - 1.5 * iqr
                    upper_bound = q3 + 1.5 * iqr
                    outliers = feature_data[
                        (feature_data[selected_feature] < lower_bound)
                        | (feature_data[selected_feature] > upper_bound)
                    ]
                    st.write(f"使用 IQR 方法檢測到 {len(outliers)} 個異常值")
                    st.write(f"下界: {lower_bound:.2f}, 上界: {upper_bound:.2f}")

                elif outlier_method == "百分位數":
                    lower_percentile = 1
                    upper_percentile = 99
                    lower_bound = np.percentile(
                        feature_data[selected_feature], lower_percentile
                    )
                    upper_bound = np.percentile(
                        feature_data[selected_feature], upper_percentile
                    )
                    outliers = feature_data[
                        (feature_data[selected_feature] < lower_bound)
                        | (feature_data[selected_feature] > upper_bound)
                    ]
                    st.write(
                        f"使用百分位數方法 ({lower_percentile}% - {upper_percentile}%) 檢測到 {len(outliers)} 個異常值"
                    )
                    st.write(f"下界: {lower_bound:.2f}, 上界: {upper_bound:.2f}")

                # 顯示異常值
                if not outliers.empty:
                    st.dataframe(outliers, use_container_width=True)

                    # 在時間序列圖上標記異常值
                    fig = px.line(
                        feature_data,
                        x="日期",
                        y=selected_feature,
                        title=f"{selected_feature} 時間序列 (含異常值標記)",
                    )

                    # 添加異常值散點
                    fig.add_scatter(
                        x=outliers["日期"],
                        y=outliers[selected_feature],
                        mode="markers",
                        marker=dict(color="red", size=10),
                        name="異常值",
                    )

                    st.plotly_chart(fig, use_container_width=True)


def show_feature_selection():
    """顯示特徵選擇頁面"""
    st.subheader("特徵選擇")

    # 獲取股票列表
    stocks = get_stock_list()

    # 創建表單
    with st.form("feature_selection_form"):
        # 選擇特徵來源
        feature_source = st.radio(
            "特徵來源", ["從特徵庫選擇", "上傳特徵數據"], horizontal=True
        )

        if feature_source == "從特徵庫選擇":
            # 選擇特徵類型
            feature_type = st.multiselect(
                "特徵類型",
                ["技術指標", "基本面指標", "情緒指標"],
                default=["技術指標", "基本面指標"],
            )

            # 選擇股票
            col1, col2 = st.columns(2)

            with col1:
                # 選擇市場
                markets = list(set([s["market"] for s in stocks]))
                selected_markets = st.multiselect(
                    "選擇市場",
                    options=markets,
                    default=markets,
                    key="selection_markets",
                )

                # 根據選擇的市場過濾股票
                filtered_stocks = [s for s in stocks if s["market"] in selected_markets]
                stock_options = [
                    f"{s['symbol']} - {s['name']}" for s in filtered_stocks
                ]

                # 選擇股票
                selected_stocks = st.multiselect(
                    "選擇股票",
                    options=stock_options,
                    default=[stock_options[0]],
                    key="selection_stocks",
                )

                # 從選擇中提取股票代碼
                selected_symbols = [s.split(" - ")[0] for s in selected_stocks]

            with col2:
                # 選擇日期範圍
                start_date = st.date_input(
                    "開始日期",
                    datetime.now() - timedelta(days=365),
                    help="選擇特徵數據的開始日期",
                    key="selection_start_date",
                )

                end_date = st.date_input(
                    "結束日期",
                    datetime.now(),
                    help="選擇特徵數據的結束日期",
                    key="selection_end_date",
                )
        else:  # 上傳特徵數據
            # 上傳文件
            uploaded_file = st.file_uploader(
                "上傳特徵數據 (CSV 格式)",
                type=["csv"],
                help="上傳包含特徵數據的 CSV 文件",
            )

        # 選擇目標變量
        target_type = st.radio(
            "目標變量類型", ["收益率", "漲跌", "波動率", "自定義"], horizontal=True
        )

        if target_type == "收益率":
            # 收益率設置
            return_period = st.selectbox(
                "收益率週期",
                options=["1天", "3天", "5天", "10天", "20天", "30天"],
                index=2,
            )

            return_type = st.radio(
                "收益率類型", ["簡單收益率", "對數收益率"], horizontal=True
            )

        elif target_type == "漲跌":
            # 漲跌設置
            threshold = st.slider(
                "漲跌閾值 (%)", min_value=0.0, max_value=10.0, value=1.0, step=0.1
            )

            period = st.selectbox(
                "預測週期", options=["1天", "3天", "5天", "10天", "20天"], index=2
            )

        elif target_type == "波動率":
            # 波動率設置
            volatility_window = st.selectbox(
                "波動率窗口", options=["5天", "10天", "20天", "30天"], index=1
            )

            volatility_type = st.radio(
                "波動率類型", ["標準差", "平均絕對偏差", "範圍"], horizontal=True
            )

        elif target_type == "自定義":
            # 自定義目標變量
            target_column = st.text_input("目標變量列名", "target")

        # 特徵選擇方法
        selection_method = st.selectbox(
            "特徵選擇方法",
            options=[
                "F 檢定 (F-test)",
                "互信息 (Mutual Information)",
                "隨機森林特徵重要性 (Random Forest)",
                "Lasso 正則化 (Lasso Regularization)",
                "遞歸特徵消除 (RFE)",
                "主成分分析 (PCA)",
            ],
            index=2,
        )

        # 特徵數量
        if selection_method != "主成分分析 (PCA)":
            k_features = st.slider("選擇特徵數量", min_value=1, max_value=50, value=10)
        else:
            explained_variance = st.slider(
                "解釋方差比例", min_value=0.5, max_value=0.99, value=0.95, step=0.01
            )

        # 特徵預處理選項
        with st.expander("特徵預處理選項"):
            # 標準化選項
            normalize = st.checkbox(
                "標準化特徵", value=True, help="將特徵標準化到相同的尺度"
            )

            if normalize:
                normalize_method = st.selectbox(
                    "標準化方法",
                    options=["Z-Score", "Min-Max", "Robust"],
                    index=0,
                    help="選擇標準化方法",
                )

            # 缺失值處理
            handle_missing = st.checkbox(
                "處理缺失值", value=True, help="處理特徵數據中的缺失值"
            )

            if handle_missing:
                missing_method = st.selectbox(
                    "缺失值處理方法",
                    options=[
                        "刪除",
                        "均值填充",
                        "中位數填充",
                        "眾數填充",
                        "前值填充",
                        "插值",
                    ],
                    index=1,
                    help="選擇缺失值處理方法",
                )

            # 異常值處理
            handle_outliers = st.checkbox(
                "處理異常值", value=True, help="處理特徵數據中的異常值"
            )

            if handle_outliers:
                outlier_method = st.selectbox(
                    "異常值處理方法",
                    options=["截斷", "刪除", "替換"],
                    index=0,
                    help="選擇異常值處理方法",
                )

                if outlier_method == "截斷":
                    outlier_threshold = st.slider(
                        "異常值閾值 (標準差倍數)",
                        min_value=1.0,
                        max_value=5.0,
                        value=3.0,
                        step=0.1,
                    )

        # 交叉驗證選項
        with st.expander("交叉驗證選項"):
            use_cv = st.checkbox(
                "使用交叉驗證", value=True, help="使用交叉驗證評估特徵選擇效果"
            )

            if use_cv:
                cv_folds = st.slider("交叉驗證折數", min_value=2, max_value=10, value=5)

                scoring = st.selectbox(
                    "評分標準",
                    options=[
                        "準確率",
                        "精確率",
                        "召回率",
                        "F1分數",
                        "AUC",
                        "均方誤差",
                        "平均絕對誤差",
                    ],
                    index=0,
                )

        # 提交按鈕
        submitted = st.form_submit_button("開始特徵選擇")

    # 處理表單提交
    if submitted:
        with st.spinner("正在進行特徵選擇..."):
            # 模擬特徵選擇過程
            time.sleep(2)

            # 獲取模擬特徵數據
            if feature_source == "從特徵庫選擇":
                # 獲取特徵數據
                feature_data = pd.DataFrame()

                if "技術指標" in feature_type:
                    tech_data = get_mock_feature_data(
                        "技術指標", selected_symbols, start_date, end_date
                    )
                    if feature_data.empty:
                        feature_data = tech_data
                    else:
                        feature_data = feature_data.merge(tech_data, on="日期")

                if "基本面指標" in feature_type:
                    fund_data = get_mock_feature_data(
                        "基本面指標", selected_symbols, start_date, end_date
                    )
                    if feature_data.empty:
                        feature_data = fund_data
                    else:
                        feature_data = feature_data.merge(fund_data, on="日期")

                if "情緒指標" in feature_type:
                    sent_data = get_mock_feature_data(
                        "情緒指標", selected_symbols, start_date, end_date
                    )
                    if feature_data.empty:
                        feature_data = sent_data
                    else:
                        feature_data = feature_data.merge(sent_data, on="日期")
            else:  # 上傳特徵數據
                if uploaded_file is not None:
                    feature_data = pd.read_csv(uploaded_file)
                else:
                    st.error("請上傳特徵數據文件")
                    return

            # 生成目標變量
            if target_type == "收益率":
                # 選擇第一個股票的收盤價作為目標變量的基礎
                symbol = selected_symbols[0]
                price_col = next(
                    (
                        col
                        for col in feature_data.columns
                        if symbol in col and "收盤價" in col
                    ),
                    None,
                )

                if price_col is None:
                    # 如果找不到收盤價列，使用第一個包含股票代碼的列
                    price_col = next(
                        (col for col in feature_data.columns if symbol in col), None
                    )

                if price_col is not None:
                    # 解析收益率週期
                    period = int(return_period.replace("天", ""))

                    # 計算收益率
                    if return_type == "簡單收益率":
                        feature_data["target"] = (
                            feature_data[price_col].pct_change(period).shift(-period)
                        )
                    else:  # 對數收益率
                        feature_data["target"] = np.log(
                            feature_data[price_col]
                            / feature_data[price_col].shift(period)
                        ).shift(-period)
                else:
                    # 如果找不到適合的列，生成隨機目標變量
                    feature_data["target"] = np.random.normal(
                        0, 0.02, len(feature_data)
                    )

            elif target_type == "漲跌":
                # 選擇第一個股票的收盤價作為目標變量的基礎
                symbol = selected_symbols[0]
                price_col = next(
                    (
                        col
                        for col in feature_data.columns
                        if symbol in col and "收盤價" in col
                    ),
                    None,
                )

                if price_col is None:
                    # 如果找不到收盤價列，使用第一個包含股票代碼的列
                    price_col = next(
                        (col for col in feature_data.columns if symbol in col), None
                    )

                if price_col is not None:
                    # 解析預測週期
                    period = int(period.replace("天", ""))

                    # 計算未來收益率
                    future_return = (
                        feature_data[price_col].pct_change(period).shift(-period)
                    )

                    # 根據閾值生成漲跌標籤
                    feature_data["target"] = (future_return > threshold / 100).astype(
                        int
                    )
                else:
                    # 如果找不到適合的列，生成隨機目標變量
                    feature_data["target"] = np.random.choice(
                        [0, 1], size=len(feature_data)
                    )

            elif target_type == "波動率":
                # 選擇第一個股票的收盤價作為目標變量的基礎
                symbol = selected_symbols[0]
                price_col = next(
                    (
                        col
                        for col in feature_data.columns
                        if symbol in col and "收盤價" in col
                    ),
                    None,
                )

                if price_col is None:
                    # 如果找不到收盤價列，使用第一個包含股票代碼的列
                    price_col = next(
                        (col for col in feature_data.columns if symbol in col), None
                    )

                if price_col is not None:
                    # 解析波動率窗口
                    window = int(volatility_window.replace("天", ""))

                    # 計算收益率
                    returns = feature_data[price_col].pct_change()

                    # 計算波動率
                    if volatility_type == "標準差":
                        feature_data["target"] = returns.rolling(window).std().shift(-1)
                    elif volatility_type == "平均絕對偏差":
                        feature_data["target"] = (
                            returns.rolling(window)
                            .apply(lambda x: np.mean(np.abs(x - np.mean(x))))
                            .shift(-1)
                        )
                    else:  # 範圍
                        feature_data["target"] = (
                            feature_data[price_col]
                            .rolling(window)
                            .apply(lambda x: (x.max() - x.min()) / x.min())
                            .shift(-1)
                        )
                else:
                    # 如果找不到適合的列，生成隨機目標變量
                    feature_data["target"] = np.random.uniform(
                        0.01, 0.05, len(feature_data)
                    )

            # 移除日期列和目標變量，獲取特徵矩陣
            X = feature_data.drop(columns=["日期", "target"])
            y = feature_data["target"]

            # 處理缺失值
            if handle_missing:
                # 移除包含缺失值的行
                if missing_method == "刪除":
                    mask = X.notna().all(axis=1)
                    X = X[mask]
                    y = y[mask]
                # 使用均值填充缺失值
                elif missing_method == "均值填充":
                    X = X.fillna(X.mean())
                # 使用中位數填充缺失值
                elif missing_method == "中位數填充":
                    X = X.fillna(X.median())
                # 使用眾數填充缺失值
                elif missing_method == "眾數填充":
                    for col in X.columns:
                        X[col] = X[col].fillna(X[col].mode()[0])
                # 使用前值填充缺失值
                elif missing_method == "前值填充":
                    X = X.fillna(method="ffill")
                # 使用插值填充缺失值
                elif missing_method == "插值":
                    X = X.interpolate()

            # 標準化特徵
            if normalize:
                if normalize_method == "Z-Score":
                    scaler = StandardScaler()
                    X_scaled = scaler.fit_transform(X)
                elif normalize_method == "Min-Max":
                    scaler = MinMaxScaler()
                    X_scaled = scaler.fit_transform(X)
                elif normalize_method == "Robust":
                    scaler = RobustScaler()
                    X_scaled = scaler.fit_transform(X)

                # 轉換回 DataFrame
                X = pd.DataFrame(X_scaled, columns=X.columns)

            # 處理異常值
            if handle_outliers:
                if outlier_method == "截斷":
                    for col in X.columns:
                        mean = X[col].mean()
                        std = X[col].std()
                        X[col] = X[col].clip(
                            lower=mean - outlier_threshold * std,
                            upper=mean + outlier_threshold * std,
                        )
                elif outlier_method == "刪除":
                    for col in X.columns:
                        mean = X[col].mean()
                        std = X[col].std()
                        mask = (X[col] >= mean - outlier_threshold * std) & (
                            X[col] <= mean + outlier_threshold * std
                        )
                        X = X[mask]
                        y = y[mask]
                elif outlier_method == "替換":
                    for col in X.columns:
                        mean = X[col].mean()
                        std = X[col].std()
                        mask_lower = X[col] < mean - outlier_threshold * std
                        mask_upper = X[col] > mean + outlier_threshold * std
                        X.loc[mask_lower, col] = mean - outlier_threshold * std
                        X.loc[mask_upper, col] = mean + outlier_threshold * std

            # 特徵選擇
            selected_features = []
            feature_importance = []

            if selection_method == "F 檢定 (F-test)":
                # 使用 F 檢定進行特徵選擇
                selector = SelectKBest(score_func=f_regression, k=k_features)
                X_new = selector.fit_transform(X, y)

                # 獲取特徵重要性
                scores = selector.scores_
                feature_importance = [
                    (X.columns[i], scores[i]) for i in range(len(X.columns))
                ]
                feature_importance.sort(key=lambda x: x[1], reverse=True)

                # 獲取選中的特徵
                selected_features = [
                    X.columns[i] for i in selector.get_support(indices=True)
                ]

            elif selection_method == "互信息 (Mutual Information)":
                # 使用互信息進行特徵選擇
                selector = SelectKBest(score_func=mutual_info_regression, k=k_features)
                X_new = selector.fit_transform(X, y)

                # 獲取特徵重要性
                scores = selector.scores_
                feature_importance = [
                    (X.columns[i], scores[i]) for i in range(len(X.columns))
                ]
                feature_importance.sort(key=lambda x: x[1], reverse=True)

                # 獲取選中的特徵
                selected_features = [
                    X.columns[i] for i in selector.get_support(indices=True)
                ]

            elif selection_method == "隨機森林特徵重要性 (Random Forest)":
                # 使用隨機森林進行特徵選擇
                model = RandomForestRegressor(n_estimators=100, random_state=42)
                model.fit(X, y)

                # 獲取特徵重要性
                importances = model.feature_importances_
                feature_importance = [
                    (X.columns[i], importances[i]) for i in range(len(X.columns))
                ]
                feature_importance.sort(key=lambda x: x[1], reverse=True)

                # 獲取選中的特徵
                selected_features = [
                    feature for feature, importance in feature_importance[:k_features]
                ]

            elif selection_method == "主成分分析 (PCA)":
                # 使用 PCA 進行特徵選擇
                pca = PCA(n_components=explained_variance, svd_solver="full")
                X_new = pca.fit_transform(X)

                # 獲取解釋方差比例
                explained_variance_ratio = pca.explained_variance_ratio_

                # 創建 PCA 特徵名稱
                selected_features = [f"PC{i+1}" for i in range(pca.n_components_)]

                # 獲取特徵重要性（解釋方差比例）
                feature_importance = [
                    (selected_features[i], explained_variance_ratio[i])
                    for i in range(len(selected_features))
                ]

            else:  # 其他方法，使用隨機森林作為默認
                # 使用隨機森林進行特徵選擇
                model = RandomForestRegressor(n_estimators=100, random_state=42)
                model.fit(X, y)

                # 獲取特徵重要性
                importances = model.feature_importances_
                feature_importance = [
                    (X.columns[i], importances[i]) for i in range(len(X.columns))
                ]
                feature_importance.sort(key=lambda x: x[1], reverse=True)

                # 獲取選中的特徵
                selected_features = [
                    feature for feature, importance in feature_importance[:k_features]
                ]

            # 顯示特徵選擇結果
            st.success(f"特徵選擇完成！已選擇 {len(selected_features)} 個特徵。")

            # 顯示選中的特徵
            st.subheader("選中的特徵")

            # 創建特徵重要性表格
            importance_df = pd.DataFrame(feature_importance, columns=["特徵", "重要性"])

            # 顯示特徵重要性表格
            st.dataframe(importance_df, use_container_width=True)

            # 繪製特徵重要性條形圖
            fig = px.bar(
                importance_df.head(20),  # 只顯示前 20 個特徵
                x="重要性",
                y="特徵",
                orientation="h",
                title="特徵重要性 (Top 20)",
            )

            st.plotly_chart(fig, use_container_width=True)

            # 顯示特徵相關性熱力圖
            st.subheader("特徵相關性熱力圖")

            # 計算相關性矩陣
            if selection_method != "主成分分析 (PCA)":
                # 使用選中的特徵
                selected_X = X[selected_features]
                corr_matrix = selected_X.corr()

                # 繪製熱力圖
                fig = px.imshow(
                    corr_matrix,
                    title="特徵相關性熱力圖",
                    color_continuous_scale="RdBu_r",
                    zmin=-1,
                    zmax=1,
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("PCA 特徵之間沒有相關性，因為它們是正交的。")

            # 提供下載選項
            if selection_method != "主成分分析 (PCA)":
                # 準備下載數據
                download_data = X[selected_features].copy()
                download_data["target"] = y

                # 提供下載按鈕
                st.download_button(
                    label="下載選中特徵數據 (CSV)",
                    data=download_data.to_csv(index=False).encode("utf-8"),
                    file_name=f"selected_features_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                )
            else:
                # 準備下載數據
                download_data = pd.DataFrame(X_new, columns=selected_features)
                download_data["target"] = y

                # 提供下載按鈕
                st.download_button(
                    label="下載 PCA 特徵數據 (CSV)",
                    data=download_data.to_csv(index=False).encode("utf-8"),
                    file_name=f"pca_features_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                )


def show_feature_engineering_log():
    """顯示特徵工程日誌頁面"""
    st.subheader("特徵工程日誌")

    # 創建模擬日誌數據
    log_data = generate_mock_feature_engineering_logs()

    # 過濾選項
    col1, col2, col3 = st.columns(3)

    with col1:
        # 選擇操作類型
        operation_types = ["所有操作"] + sorted(list(set(log_data["操作類型"])))
        selected_operation = st.selectbox("操作類型", options=operation_types, index=0)

    with col2:
        # 選擇特徵類型
        feature_types = ["所有特徵"] + sorted(list(set(log_data["特徵類型"])))
        selected_feature_type = st.selectbox("特徵類型", options=feature_types, index=0)

    with col3:
        # 選擇狀態
        statuses = ["所有狀態"] + sorted(list(set(log_data["狀態"])))
        selected_status = st.selectbox("狀態", options=statuses, index=0)

    # 日期範圍選擇
    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input(
            "開始日期", datetime.now() - timedelta(days=30), key="log_start_date"
        )

    with col2:
        end_date = st.date_input("結束日期", datetime.now(), key="log_end_date")

    # 過濾日誌
    filtered_logs = log_data.copy()

    # 過濾操作類型
    if selected_operation != "所有操作":
        filtered_logs = filtered_logs[filtered_logs["操作類型"] == selected_operation]

    # 過濾特徵類型
    if selected_feature_type != "所有特徵":
        filtered_logs = filtered_logs[
            filtered_logs["特徵類型"] == selected_feature_type
        ]

    # 過濾狀態
    if selected_status != "所有狀態":
        filtered_logs = filtered_logs[filtered_logs["狀態"] == selected_status]

    # 過濾日期範圍
    filtered_logs = filtered_logs[
        (pd.to_datetime(filtered_logs["時間"]).dt.date >= start_date)
        & (pd.to_datetime(filtered_logs["時間"]).dt.date <= end_date)
    ]

    # 顯示過濾後的日誌
    st.subheader("日誌列表")
    st.write(f"共找到 {len(filtered_logs)} 條日誌記錄")

    # 顯示日誌表格
    st.dataframe(filtered_logs, use_container_width=True)

    # 提供下載選項
    st.download_button(
        label="下載日誌 (CSV)",
        data=filtered_logs.to_csv(index=False).encode("utf-8"),
        file_name=f"feature_engineering_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )

    # 顯示日誌統計
    st.subheader("日誌統計")

    # 創建標籤頁
    tabs = st.tabs(["操作類型統計", "特徵類型統計", "狀態統計", "時間趨勢"])

    # 操作類型統計
    with tabs[0]:
        operation_counts = log_data["操作類型"].value_counts().reset_index()
        operation_counts.columns = ["操作類型", "數量"]

        # 繪製條形圖
        fig = px.bar(
            operation_counts,
            x="操作類型",
            y="數量",
            title="操作類型統計",
            color="操作類型",
        )

        st.plotly_chart(fig, use_container_width=True)

    # 特徵類型統計
    with tabs[1]:
        feature_counts = log_data["特徵類型"].value_counts().reset_index()
        feature_counts.columns = ["特徵類型", "數量"]

        # 繪製餅圖
        fig = px.pie(
            feature_counts, names="特徵類型", values="數量", title="特徵類型統計"
        )

        st.plotly_chart(fig, use_container_width=True)

    # 狀態統計
    with tabs[2]:
        status_counts = log_data["狀態"].value_counts().reset_index()
        status_counts.columns = ["狀態", "數量"]

        # 繪製條形圖
        fig = px.bar(
            status_counts,
            x="狀態",
            y="數量",
            title="狀態統計",
            color="狀態",
            color_discrete_map={
                "成功": "green",
                "失敗": "red",
                "警告": "orange",
                "進行中": "blue",
            },
        )

        st.plotly_chart(fig, use_container_width=True)

    # 時間趨勢
    with tabs[3]:
        # 將時間轉換為日期
        log_data["日期"] = pd.to_datetime(log_data["時間"]).dt.date

        # 按日期分組計數
        time_trend = log_data.groupby("日期").size().reset_index()
        time_trend.columns = ["日期", "數量"]

        # 繪製時間趨勢圖
        fig = px.line(time_trend, x="日期", y="數量", title="特徵工程操作時間趨勢")

        st.plotly_chart(fig, use_container_width=True)

    # 顯示最近的錯誤和警告
    st.subheader("最近的錯誤和警告")

    # 過濾錯誤和警告
    errors_warnings = (
        log_data[log_data["狀態"].isin(["失敗", "警告"])]
        .sort_values("時間", ascending=False)
        .head(5)
    )

    if not errors_warnings.empty:
        for _, row in errors_warnings.iterrows():
            with st.expander(f"{row['時間']} - {row['操作類型']} - {row['狀態']}"):
                st.write(f"**特徵類型**: {row['特徵類型']}")
                st.write(f"**操作者**: {row['操作者']}")
                st.write(f"**詳細信息**: {row['詳細信息']}")
    else:
        st.info("沒有最近的錯誤和警告")


def generate_mock_feature_engineering_logs():
    """生成模擬特徵工程日誌數據"""
    # 創建日期範圍
    date_range = pd.date_range(end=datetime.now(), periods=100, freq="D")

    # 操作類型
    operation_types = [
        "特徵計算",
        "特徵選擇",
        "特徵標準化",
        "特徵降維",
        "特徵存儲",
        "特徵更新",
        "特徵刪除",
        "特徵合併",
        "特徵轉換",
        "特徵驗證",
    ]

    # 特徵類型
    feature_types = [
        "技術指標",
        "基本面指標",
        "情緒指標",
        "自定義特徵",
        "PCA特徵",
        "因子特徵",
        "時間特徵",
        "類別特徵",
    ]

    # 狀態
    statuses = ["成功", "失敗", "警告", "進行中"]

    # 操作者
    operators = ["系統", "用戶", "排程任務", "API"]

    # 詳細信息模板
    detail_templates = {
        "特徵計算": [
            "計算 {symbol} 的 {indicator} 特徵，共 {count} 條記錄",
            "使用 {method} 方法計算 {feature_type} 特徵",
            "特徵計算耗時 {time} 秒，生成 {count} 個特徵",
        ],
        "特徵選擇": [
            "使用 {method} 方法選擇 {count} 個特徵",
            "特徵選擇完成，從 {total} 個特徵中選出 {count} 個",
            "特徵重要性排序完成，前 {count} 個特徵被選中",
        ],
        "特徵標準化": [
            "使用 {method} 方法標準化 {feature_type} 特徵",
            "標準化 {count} 個特徵，耗時 {time} 秒",
            "特徵標準化完成，均值為 0，標準差為 1",
        ],
        "特徵降維": [
            "使用 {method} 方法將特徵維度從 {old_dim} 降至 {new_dim}",
            "降維完成，解釋方差比例為 {var_ratio}",
            "降維後特徵數量減少 {percent}%",
        ],
        "特徵存儲": [
            "將 {feature_type} 特徵存儲到特徵庫，共 {count} 條記錄",
            "特徵存儲完成，特徵名稱為 {name}",
            "特徵存儲耗時 {time} 秒，存儲大小為 {size} MB",
        ],
        "特徵更新": [
            "更新 {feature_type} 特徵，共 {count} 條記錄",
            "特徵更新完成，更新了 {count} 個特徵",
            "特徵更新耗時 {time} 秒",
        ],
        "特徵刪除": [
            "刪除 {feature_type} 特徵，共 {count} 個特徵",
            "特徵刪除完成，釋放了 {size} MB 空間",
            "刪除過期特徵，共 {count} 個",
        ],
        "特徵合併": [
            "合併 {type1} 和 {type2} 特徵，共 {count} 條記錄",
            "特徵合併完成，生成 {count} 個新特徵",
            "特徵合併耗時 {time} 秒",
        ],
        "特徵轉換": [
            "將 {feature_type} 特徵轉換為 {new_type} 格式",
            "特徵轉換完成，轉換了 {count} 個特徵",
            "特徵轉換耗時 {time} 秒",
        ],
        "特徵驗證": [
            "驗證 {feature_type} 特徵，共 {count} 條記錄",
            "特徵驗證完成，發現 {error_count} 個異常值",
            "特徵驗證耗時 {time} 秒",
        ],
    }

    # 錯誤信息模板
    error_templates = [
        "計算 {indicator} 時發生錯誤: {error}",
        "特徵 {feature} 包含 {count} 個缺失值",
        "特徵 {feature} 存在異常值，超出正常範圍",
        "特徵 {feature} 與目標變量相關性過低",
        "特徵 {feature} 與其他特徵高度相關，可能存在多重共線性",
        "特徵存儲失敗: {error}",
        "特徵更新失敗: {error}",
        "特徵轉換失敗: {error}",
        "特徵驗證失敗: {error}",
    ]

    # 生成隨機日誌數據
    np.random.seed(42)

    logs = []

    for date in date_range:
        # 每天生成 1-5 條日誌
        n_logs = np.random.randint(1, 6)

        for _ in range(n_logs):
            # 隨機選擇操作類型
            operation_type = np.random.choice(operation_types)

            # 隨機選擇特徵類型
            feature_type = np.random.choice(feature_types)

            # 隨機選擇狀態，成功概率較高
            status = np.random.choice(statuses, p=[0.7, 0.1, 0.1, 0.1])

            # 隨機選擇操作者
            operator = np.random.choice(operators)

            # 生成詳細信息
            if status in ["失敗", "警告"]:
                # 生成錯誤信息
                error_template = np.random.choice(error_templates)
                details = error_template.format(
                    indicator=np.random.choice(["RSI", "MACD", "SMA", "EMA", "BBANDS"]),
                    feature=f"{np.random.choice(['RSI', 'MACD', 'SMA', 'EMA', 'BBANDS'])}_{np.random.randint(5, 50)}",
                    count=np.random.randint(1, 100),
                    error=np.random.choice(
                        ["除以零", "數據類型不匹配", "內存不足", "超時", "API 錯誤"]
                    ),
                )
            else:
                # 生成正常信息
                detail_template = np.random.choice(detail_templates[operation_type])
                details = detail_template.format(
                    symbol=np.random.choice(
                        ["2330.TW", "2317.TW", "2454.TW", "AAPL", "MSFT", "GOOGL"]
                    ),
                    indicator=np.random.choice(["RSI", "MACD", "SMA", "EMA", "BBANDS"]),
                    count=np.random.randint(10, 1000),
                    method=np.random.choice(
                        ["F 檢定", "互信息", "隨機森林", "PCA", "Lasso", "RFE"]
                    ),
                    feature_type=feature_type,
                    time=np.random.randint(1, 100),
                    total=np.random.randint(50, 200),
                    old_dim=np.random.randint(50, 200),
                    new_dim=np.random.randint(5, 50),
                    var_ratio=f"{np.random.uniform(0.7, 0.99):.2f}",
                    percent=np.random.randint(50, 90),
                    name=f"{feature_type}_{np.random.randint(1, 100)}",
                    size=np.random.randint(1, 100),
                    type1=np.random.choice(feature_types),
                    type2=np.random.choice(feature_types),
                    new_type=np.random.choice(["CSV", "Parquet", "HDF5", "JSON"]),
                    error_count=np.random.randint(0, 50),
                )

            # 生成隨機時間
            hour = np.random.randint(8, 18)
            minute = np.random.randint(0, 60)
            second = np.random.randint(0, 60)
            timestamp = date.replace(hour=hour, minute=minute, second=second)

            # 添加日誌
            logs.append(
                {
                    "時間": timestamp,
                    "操作類型": operation_type,
                    "特徵類型": feature_type,
                    "狀態": status,
                    "操作者": operator,
                    "詳細信息": details,
                }
            )

    # 創建 DataFrame
    logs_df = pd.DataFrame(logs)

    # 按時間排序
    logs_df = logs_df.sort_values("時間", ascending=False)

    return logs_df


def show():
    """顯示特徵工程頁面"""
    # 頁面標籤
    tabs = st.tabs(["可用特徵", "特徵計算", "特徵查詢", "特徵選擇", "特徵工程日誌"])

    with tabs[0]:
        show_available_features()

    with tabs[1]:
        show_feature_calculation()

    with tabs[2]:
        show_feature_query()

    with tabs[3]:
        show_feature_selection()

    with tabs[4]:
        show_feature_engineering_log()
