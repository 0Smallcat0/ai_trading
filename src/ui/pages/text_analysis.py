# -*- coding: utf-8 -*-
"""文本分析Web界面

此模組提供文本分析功能的Streamlit Web界面，包括情感分析、
新聞分類、股票關聯分析等功能的可視化展示。

主要功能：
- 實時文本分析
- 批量文本處理
- 情感趨勢可視化
- 新聞分類統計
- 股票關聯分析
- 結果導出功能

Example:
    在Streamlit應用中使用：
    >>> from src.ui.pages.text_analysis import render_text_analysis_page
    >>> render_text_analysis_page()
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import time

from src.nlp.text_analysis_adapter import TextAnalysisAdapter
from src.nlp.news_crawler import NewsCrawler, NewsItem
from src.nlp.news_classifier import NewsCategory


def render_text_analysis_page():
    """渲染文本分析頁面"""
    st.title("📝 文本分析系統")
    st.markdown("---")
    
    # 初始化適配器
    if 'text_adapter' not in st.session_state:
        with st.spinner("初始化文本分析系統..."):
            st.session_state.text_adapter = TextAnalysisAdapter()
    
    adapter = st.session_state.text_adapter
    
    # 側邊欄配置
    render_sidebar_config()
    
    # 主要功能標籤頁
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 實時分析", "📊 批量處理", "📈 趨勢分析", 
        "📰 新聞分析", "📋 系統狀態"
    ])
    
    with tab1:
        render_realtime_analysis_tab(adapter)
    
    with tab2:
        render_batch_processing_tab(adapter)
    
    with tab3:
        render_trend_analysis_tab(adapter)
    
    with tab4:
        render_news_analysis_tab(adapter)
    
    with tab5:
        render_system_status_tab(adapter)


def render_sidebar_config():
    """渲染側邊欄配置"""
    st.sidebar.header("⚙️ 系統配置")
    
    # 分析選項
    st.sidebar.subheader("分析選項")
    st.session_state.enable_sentiment = st.sidebar.checkbox("情感分析", value=True)
    st.session_state.enable_classification = st.sidebar.checkbox("新聞分類", value=True)
    st.session_state.enable_stock_analysis = st.sidebar.checkbox("股票關聯", value=True)
    
    # 顯示選項
    st.sidebar.subheader("顯示選項")
    st.session_state.show_keywords = st.sidebar.checkbox("顯示關鍵詞", value=True)
    st.session_state.show_confidence = st.sidebar.checkbox("顯示置信度", value=True)
    st.session_state.show_processing_time = st.sidebar.checkbox("顯示處理時間", value=False)
    
    # 快取控制
    st.sidebar.subheader("快取控制")
    if st.sidebar.button("清空快取"):
        st.session_state.text_adapter.clear_cache()
        st.sidebar.success("快取已清空")


def render_realtime_analysis_tab(adapter: TextAnalysisAdapter):
    """渲染實時分析標籤頁"""
    st.header("🎯 實時文本分析")
    
    # 文本輸入
    col1, col2 = st.columns([3, 1])
    
    with col1:
        input_text = st.text_area(
            "請輸入要分析的文本：",
            height=150,
            placeholder="例如：央行宣布降準0.5個百分點，股市大幅上漲...",
            key="realtime_text_input"
        )
    
    with col2:
        st.write("**快速示例：**")
        example_texts = [
            "股市大漲，投資者信心增強",
            "央行降準，流動性寬鬆",
            "公司業績下滑，股價承壓",
            "新政策利好科技行業發展"
        ]
        
        for i, example in enumerate(example_texts):
            if st.button(f"示例 {i+1}", key=f"example_{i}"):
                st.session_state.example_text = example
    
    # 使用示例文本
    if 'example_text' in st.session_state:
        input_text = st.session_state.example_text
        del st.session_state.example_text
    
    # 分析按鈕
    if st.button("🔍 開始分析", type="primary", key="realtime_analysis_start_btn") and input_text:
        with st.spinner("分析中..."):
            result = adapter.analyze_text(input_text)

            # 顯示分析結果
            render_analysis_result(result)

    elif st.button("🔍 開始分析", type="primary", key="realtime_analysis_warning_btn"):
        st.warning("請輸入要分析的文本")


def render_analysis_result(result):
    """渲染分析結果"""
    # 主要指標
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        sentiment_color = "red" if result.sentiment_score > 0 else "green" if result.sentiment_score < 0 else "gray"
        st.metric(
            "情感分數",
            f"{result.sentiment_score:.3f}",
            delta=None,
            delta_color="normal"
        )
    
    with col2:
        st.metric(
            "新聞分類",
            result.category.value if result.category != NewsCategory.UNKNOWN else "未知",
            delta=None
        )
    
    with col3:
        if st.session_state.show_confidence:
            st.metric(
                "分類置信度",
                f"{result.classification_confidence:.2%}",
                delta=None
            )
    
    with col4:
        if st.session_state.show_processing_time:
            processing_time = result.metadata.get('processing_time', 0)
            st.metric(
                "處理時間",
                f"{processing_time:.3f}s",
                delta=None
            )
    
    # 詳細信息
    if st.session_state.show_keywords and result.keywords:
        st.subheader("🔑 關鍵詞")
        keywords_text = " | ".join([f"`{kw}`" for kw in result.keywords[:10]])
        st.markdown(keywords_text)
    
    # 情感可視化
    if result.sentiment_score != 0:
        st.subheader("📊 情感分析可視化")
        
        fig = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = result.sentiment_score,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "情感分數"},
            delta = {'reference': 0},
            gauge = {
                'axis': {'range': [-1, 1]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [-1, -0.5], 'color': "red"},
                    {'range': [-0.5, 0], 'color': "orange"},
                    {'range': [0, 0.5], 'color': "lightgreen"},
                    {'range': [0.5, 1], 'color': "green"}
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 4},
                    'thickness': 0.75,
                    'value': 0
                }
            }
        ))
        
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)


def render_batch_processing_tab(adapter: TextAnalysisAdapter):
    """渲染批量處理標籤頁"""
    st.header("📊 批量文本處理")
    
    # 文本輸入方式選擇
    input_method = st.radio(
        "選擇輸入方式：",
        ["手動輸入", "文件上傳", "示例數據"],
        key="batch_input_method_radio"
    )
    
    texts = []
    
    if input_method == "手動輸入":
        text_input = st.text_area(
            "請輸入多行文本（每行一個文本）：",
            height=200,
            placeholder="第一條文本\n第二條文本\n第三條文本...",
            key="batch_text_input"
        )
        
        if text_input:
            texts = [line.strip() for line in text_input.split('\n') if line.strip()]
    
    elif input_method == "文件上傳":
        uploaded_file = st.file_uploader(
            "上傳文本文件",
            type=['txt', 'csv'],
            help="支援 .txt 和 .csv 格式"
        )
        
        if uploaded_file:
            if uploaded_file.type == "text/plain":
                content = str(uploaded_file.read(), "utf-8")
                texts = [line.strip() for line in content.split('\n') if line.strip()]
            elif uploaded_file.type == "text/csv":
                df = pd.read_csv(uploaded_file)
                if 'text' in df.columns:
                    texts = df['text'].dropna().tolist()
                else:
                    st.error("CSV文件必須包含 'text' 列")
    
    else:  # 示例數據
        example_texts = [
            "央行宣布降準，市場流動性充裕",
            "科技股大幅上漲，投資者情緒高漲",
            "房地產政策收緊，相關股票下跌",
            "新能源汽車銷量創新高",
            "醫藥行業監管加強，股價承壓",
            "金融科技發展迅速，前景看好",
            "疫情影響消費，零售業面臨挑戰",
            "基建投資加碼，相關板塊受益"
        ]
        
        texts = example_texts
        st.info(f"已載入 {len(texts)} 條示例文本")
    
    # 批量處理
    if texts and st.button("🚀 開始批量處理", type="primary", key="batch_analysis_start_btn"):
        with st.spinner(f"正在處理 {len(texts)} 條文本..."):
            results = adapter.batch_analyze_texts(texts)

            # 顯示處理結果
            render_batch_results(results)

    elif st.button("🚀 開始批量處理", type="primary", key="batch_analysis_warning_btn"):
        st.warning("請先輸入要處理的文本")


def render_batch_results(results):
    """渲染批量處理結果"""
    st.subheader("📋 批量處理結果")
    
    # 統計摘要
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("處理文本數", len(results))
    
    with col2:
        avg_sentiment = np.mean([r.sentiment_score for r in results])
        st.metric("平均情感分數", f"{avg_sentiment:.3f}")
    
    with col3:
        avg_confidence = np.mean([r.classification_confidence for r in results])
        st.metric("平均分類置信度", f"{avg_confidence:.2%}")
    
    with col4:
        positive_count = sum(1 for r in results if r.sentiment_score > 0.1)
        st.metric("正面文本數", positive_count)
    
    # 分類分佈圖
    st.subheader("📊 分類分佈")
    
    category_counts = {}
    for result in results:
        category = result.category.value
        category_counts[category] = category_counts.get(category, 0) + 1
    
    if category_counts:
        fig = px.pie(
            values=list(category_counts.values()),
            names=list(category_counts.keys()),
            title="新聞分類分佈"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # 情感分佈圖
    st.subheader("📈 情感分佈")
    
    sentiment_scores = [r.sentiment_score for r in results]
    
    fig = px.histogram(
        x=sentiment_scores,
        nbins=20,
        title="情感分數分佈",
        labels={'x': '情感分數', 'y': '頻次'}
    )
    fig.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="中性線")
    st.plotly_chart(fig, use_container_width=True)
    
    # 詳細結果表格
    st.subheader("📋 詳細結果")
    
    # 準備表格數據
    table_data = []
    for i, result in enumerate(results):
        table_data.append({
            '序號': i + 1,
            '文本': result.text[:50] + "..." if len(result.text) > 50 else result.text,
            '情感分數': f"{result.sentiment_score:.3f}",
            '分類': result.category.value,
            '置信度': f"{result.classification_confidence:.2%}",
            '關鍵詞': ", ".join(result.keywords[:3])
        })
    
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True)
    
    # 導出功能
    if st.button("📥 導出結果", key="export_results_btn"):
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="下載CSV文件",
            data=csv,
            file_name=f"text_analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )


def render_trend_analysis_tab(adapter: TextAnalysisAdapter):
    """渲染趨勢分析標籤頁"""
    st.header("📈 情感趨勢分析")
    
    st.info("此功能需要時間序列數據，可以結合新聞爬取功能使用")
    
    # 示例趨勢數據
    if st.button("📊 生成示例趨勢", key="generate_trend_example_btn"):
        # 生成模擬數據
        dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='D')
        sentiment_scores = np.random.normal(0, 0.3, len(dates))
        
        # 添加一些趨勢
        trend = np.linspace(-0.2, 0.3, len(dates))
        sentiment_scores += trend
        
        # 創建趨勢圖
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=sentiment_scores,
            mode='lines+markers',
            name='情感分數',
            line=dict(color='blue', width=2)
        ))
        
        fig.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="中性線")
        
        fig.update_layout(
            title="情感趨勢分析",
            xaxis_title="日期",
            yaxis_title="情感分數",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)


def render_news_analysis_tab(adapter: TextAnalysisAdapter):
    """渲染新聞分析標籤頁"""
    st.header("📰 新聞分析")
    
    st.info("此功能整合新聞爬取和分析功能")
    
    # 新聞來源選擇
    news_source = st.selectbox(
        "選擇新聞來源：",
        ["新浪財經", "東方財富", "證券時報", "全部來源"],
        key="news_source_selectbox"
    )
    
    # 爬取數量
    news_count = st.slider("爬取新聞數量：", 10, 100, 50, key="news_count_slider")
    
    if st.button("📡 爬取並分析新聞", key="crawl_news_analysis_btn"):
        with st.spinner("正在爬取新聞..."):
            # 這裡應該調用新聞爬蟲
            st.info("新聞爬取功能開發中...")


def render_system_status_tab(adapter: TextAnalysisAdapter):
    """渲染系統狀態標籤頁"""
    st.header("📋 系統狀態")
    
    # 獲取性能統計
    stats = adapter.get_performance_stats()
    
    # 基本統計
    st.subheader("📊 基本統計")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("總分析次數", stats.get('total_analyzed', 0))
    
    with col2:
        st.metric("快取命中率", f"{stats.get('cache_hit_rate', 0):.1%}")
    
    with col3:
        st.metric("平均處理時間", f"{stats.get('avg_processing_time', 0):.3f}s")
    
    with col4:
        st.metric("快取大小", stats.get('cache_hits', 0) + stats.get('cache_misses', 0))
    
    # 組件狀態
    st.subheader("🔧 組件狀態")
    
    components = [
        ("情感分析器", stats.get('sentiment_analyzer_stats', {})),
        ("實時評分器", stats.get('sentiment_scorer_stats', {})),
        ("新聞分類器", stats.get('news_classifier_stats', {})),
        ("股票分析器", stats.get('stock_analyzer_stats', {})),
        ("文本處理器", stats.get('text_processor_stats', {}))
    ]
    
    for name, component_stats in components:
        with st.expander(f"{name} 狀態"):
            if component_stats:
                st.json(component_stats)
            else:
                st.info("暫無統計數據")
    
    # 系統信息
    st.subheader("ℹ️ 系統信息")
    
    adapter_info = adapter.get_adapter_info()
    st.json(adapter_info)


def show() -> None:
    """顯示文本分析頁面 (Web UI 入口點).

    Returns:
        None
    """
    render_text_analysis_page()


if __name__ == "__main__":
    render_text_analysis_page()
