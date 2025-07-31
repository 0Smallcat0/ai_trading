# -*- coding: utf-8 -*-
"""
LLM決策頁面

此模組提供LLM決策的完整頁面界面。

主要功能：
- LLM決策中心
- 實時決策生成
- 策略配置管理
- 決策歷史分析
- 性能監控
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from src.ui.components.llm_decision_components import (
    render_llm_decision_dashboard,
    render_realtime_decision,
    render_batch_analysis,
    render_decision_history
)
from src.services.decision_service import DecisionService
from src.api.llm_connector import LLMManager
from src.data.market_data import MarketDataProvider
from src.risk.risk_manager import RiskManager


def show():
    """顯示LLM決策頁面（Web UI 入口點）"""
    render_llm_decision_page()


def render_llm_decision_page() -> None:
    """渲染LLM決策頁面。"""
    
    # 頁面配置
    st.set_page_config(
        page_title="AI大模型交易決策",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 自定義CSS
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .decision-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    
    .signal-positive {
        color: #28a745;
        font-weight: bold;
    }
    
    .signal-negative {
        color: #dc3545;
        font-weight: bold;
    }
    
    .signal-neutral {
        color: #6c757d;
        font-weight: bold;
    }
    
    .confidence-high {
        background-color: #d4edda;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        color: #155724;
    }
    
    .confidence-medium {
        background-color: #fff3cd;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        color: #856404;
    }
    
    .confidence-low {
        background-color: #f8d7da;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        color: #721c24;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 主標題
    st.markdown("""
    <div class="main-header">
        <h1>🤖 AI大模型交易決策中心</h1>
        <p>基於先進的大語言模型，提供智能化的交易決策輔助</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 初始化服務（實際實現中需要從配置或依賴注入獲取）
    decision_service = initialize_decision_service()
    
    if decision_service is None:
        st.error("❌ 無法初始化決策服務，請檢查配置")
        return
    
    # 主要功能標籤頁
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 實時決策",
        "📊 批量分析", 
        "📚 決策歷史",
        "⚙️ 策略配置",
        "📈 性能監控"
    ])
    
    with tab1:
        render_realtime_decision_tab(decision_service)
    
    with tab2:
        render_batch_analysis_tab(decision_service)
    
    with tab3:
        render_decision_history_tab(decision_service)
    
    with tab4:
        render_strategy_config_tab(decision_service)
    
    with tab5:
        render_performance_monitoring_tab(decision_service)


def initialize_decision_service() -> Optional[DecisionService]:
    """初始化決策服務。

    Returns:
        決策服務實例或None
    """
    try:
        # 這裡應該從配置文件或環境變數讀取配置
        # 暫時使用模擬配置
        
        # 檢查session state中是否已有服務實例
        if 'decision_service' not in st.session_state:
            # 創建模擬服務實例
            st.session_state['decision_service'] = create_mock_decision_service()
        
        return st.session_state['decision_service']
        
    except Exception as e:
        st.error(f"初始化決策服務失敗: {e}")
        return None


def create_mock_decision_service() -> DecisionService:
    """創建模擬決策服務（用於演示）。

    Returns:
        模擬決策服務實例
    """
    # 這是一個簡化的模擬實現
    # 實際實現中需要正確初始化所有依賴
    
    class MockDecisionService:
        def __init__(self):
            self.performance_stats = {
                'total_requests': 156,
                'successful_requests': 148,
                'failed_requests': 8,
                'average_processing_time': 2.3,
                'cache_hits': 45,
                'success_rate': 0.949,
                'cache_hit_rate': 0.288
            }
            
            self.decision_history = []
        
        def get_performance_stats(self):
            return self.performance_stats
        
        def get_decision_history(self, symbol=None, limit=100):
            # 返回模擬歷史數據
            import random
            history = []
            for i in range(min(limit, 20)):
                history.append({
                    'timestamp': (datetime.now() - timedelta(hours=i)).isoformat(),
                    'stock_symbol': symbol or 'AAPL',
                    'decision': {
                        'final_signal': random.choice([-1, 0, 1]),
                        'confidence': random.uniform(0.5, 0.9),
                        'execution_recommendation': f"建議{random.choice(['買入', '賣出', '觀望'])}"
                    },
                    'processing_time': random.uniform(1.0, 4.0)
                })
            return history
    
    return MockDecisionService()


def render_realtime_decision_tab(decision_service: DecisionService) -> None:
    """渲染實時決策標籤頁。

    Args:
        decision_service: 決策服務
    """
    st.header("🎯 實時AI決策")
    
    # 快速決策區域
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        stock_symbol = st.text_input(
            "股票代碼",
            value="AAPL",
            placeholder="輸入股票代碼，如 AAPL, TSLA",
            help="輸入要分析的股票代碼"
        )
    
    with col2:
        decision_type = st.selectbox(
            "決策類型",
            ["快速決策", "深度分析", "風險評估"],
            help="選擇決策分析的深度"
        )
    
    with col3:
        st.write("")  # 空白行對齊
        generate_button = st.button(
            "🚀 生成AI決策",
            type="primary",
            use_container_width=True
        )
    
    if generate_button and stock_symbol:
        render_realtime_decision(decision_service, stock_symbol, 0.6)
    
    # 快捷股票按鈕
    st.subheader("📈 熱門股票快速分析")
    
    popular_stocks = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "NVDA", "META", "NFLX"]
    
    cols = st.columns(4)
    for i, stock in enumerate(popular_stocks):
        with cols[i % 4]:
            if st.button(f"📊 {stock}", key=f"quick_{stock}"):
                st.session_state['selected_stock'] = stock
                render_realtime_decision(decision_service, stock, 0.6)


def render_batch_analysis_tab(decision_service: DecisionService) -> None:
    """渲染批量分析標籤頁。

    Args:
        decision_service: 決策服務
    """
    st.header("📊 批量決策分析")
    
    # 批量分析配置
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📝 股票列表配置")
        
        # 預設股票組合
        preset_portfolios = {
            "科技股": "AAPL,GOOGL,MSFT,TSLA,AMZN,NVDA,META",
            "金融股": "JPM,BAC,WFC,GS,MS,C,USB",
            "醫療股": "JNJ,PFE,UNH,ABBV,MRK,TMO,DHR",
            "自定義": ""
        }
        
        selected_preset = st.selectbox(
            "選擇預設組合",
            list(preset_portfolios.keys()),
            help="選擇預設的股票組合或自定義"
        )
        
        if selected_preset == "自定義":
            symbols_input = st.text_area(
                "股票代碼列表",
                placeholder="輸入股票代碼，用逗號分隔\n例如: AAPL,GOOGL,MSFT",
                height=100
            )
        else:
            symbols_input = st.text_area(
                "股票代碼列表",
                value=preset_portfolios[selected_preset],
                height=100
            )
    
    with col2:
        st.subheader("⚙️ 分析配置")
        
        analysis_depth = st.selectbox(
            "分析深度",
            ["快速掃描", "標準分析", "深度分析"],
            index=1,
            help="選擇分析的詳細程度"
        )
        
        include_risk = st.checkbox(
            "包含風險評估",
            value=True,
            help="是否包含詳細的風險評估"
        )
        
        include_news = st.checkbox(
            "包含新聞分析",
            value=True,
            help="是否包含新聞情緒分析"
        )
        
        max_concurrent = st.slider(
            "並發分析數",
            min_value=1,
            max_value=10,
            value=5,
            help="同時分析的股票數量"
        )
    
    # 開始批量分析
    if st.button("🚀 開始批量分析", type="primary"):
        if symbols_input.strip():
            render_batch_analysis(decision_service)
        else:
            st.error("請輸入至少一個股票代碼")


def render_decision_history_tab(decision_service: DecisionService) -> None:
    """渲染決策歷史標籤頁。

    Args:
        decision_service: 決策服務
    """
    st.header("📚 決策歷史分析")
    
    # 歷史查詢配置
    col1, col2, col3 = st.columns(3)
    
    with col1:
        stock_symbol = st.text_input(
            "股票代碼",
            value="",
            placeholder="留空查看所有股票",
            help="輸入特定股票代碼或留空查看全部"
        )
    
    with col2:
        time_range = st.selectbox(
            "時間範圍",
            ["最近7天", "最近30天", "最近90天", "自定義"],
            index=1
        )
    
    with col3:
        max_records = st.number_input(
            "最大記錄數",
            min_value=10,
            max_value=1000,
            value=100,
            step=10
        )
    
    # 自定義時間範圍
    if time_range == "自定義":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "開始日期",
                value=datetime.now().date() - timedelta(days=30)
            )
        with col2:
            end_date = st.date_input(
                "結束日期",
                value=datetime.now().date()
            )
    
    # 查詢按鈕
    if st.button("🔍 查詢歷史記錄"):
        render_decision_history(decision_service, stock_symbol or "ALL")


def render_strategy_config_tab(decision_service: DecisionService) -> None:
    """渲染策略配置標籤頁。

    Args:
        decision_service: 決策服務
    """
    st.header("⚙️ 策略配置管理")
    
    # LLM配置
    st.subheader("🤖 LLM模型配置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**主要LLM提供商**")
        
        openai_enabled = st.checkbox("OpenAI GPT", value=True)
        if openai_enabled:
            openai_model = st.selectbox(
                "OpenAI模型",
                ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
                index=1
            )
            openai_api_key = st.text_input(
                "OpenAI API Key",
                type="password",
                placeholder="sk-..."
            )
        
        claude_enabled = st.checkbox("Anthropic Claude", value=False)
        if claude_enabled:
            claude_model = st.selectbox(
                "Claude模型",
                ["claude-3-haiku", "claude-3-sonnet", "claude-3-opus"],
                index=1
            )
    
    with col2:
        st.write("**本地模型配置**")
        
        local_enabled = st.checkbox("本地模型", value=False)
        if local_enabled:
            local_model_path = st.text_input(
                "模型路徑",
                placeholder="/path/to/model"
            )
            local_api_url = st.text_input(
                "API地址",
                value="http://localhost:8000",
                placeholder="http://localhost:8000"
            )
    
    # 策略權重配置
    st.subheader("⚖️ 策略權重配置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        llm_weight = st.slider(
            "LLM策略權重",
            min_value=0.0,
            max_value=1.0,
            value=0.5,
            step=0.1,
            help="LLM策略在最終決策中的權重"
        )
        
        technical_weight = st.slider(
            "技術分析權重",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.1,
            help="技術分析策略的權重"
        )
    
    with col2:
        fundamental_weight = st.slider(
            "基本面權重",
            min_value=0.0,
            max_value=1.0,
            value=0.2,
            step=0.1,
            help="基本面分析的權重"
        )
        
        # 權重總和檢查
        total_weight = llm_weight + technical_weight + fundamental_weight
        if abs(total_weight - 1.0) > 0.01:
            st.warning(f"⚠️ 權重總和為 {total_weight:.2f}，建議調整為1.0")
    
    # 風險控制配置
    st.subheader("🛡️ 風險控制配置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        max_position_size = st.slider(
            "最大倉位比例",
            min_value=0.01,
            max_value=0.5,
            value=0.1,
            step=0.01,
            format="%.2f",
            help="單個股票的最大倉位比例"
        )
        
        confidence_threshold = st.slider(
            "置信度閾值",
            min_value=0.0,
            max_value=1.0,
            value=0.6,
            step=0.05,
            help="執行交易的最低置信度要求"
        )
    
    with col2:
        stop_loss_threshold = st.slider(
            "止損閾值",
            min_value=0.01,
            max_value=0.2,
            value=0.05,
            step=0.01,
            format="%.2f",
            help="自動止損的閾值"
        )
        
        volatility_adjustment = st.checkbox(
            "波動率調整",
            value=True,
            help="是否根據波動率調整倉位大小"
        )
    
    # 保存配置
    if st.button("💾 保存配置", type="primary"):
        config = {
            'llm_config': {
                'openai_enabled': openai_enabled,
                'claude_enabled': claude_enabled,
                'local_enabled': local_enabled
            },
            'strategy_weights': {
                'llm_weight': llm_weight,
                'technical_weight': technical_weight,
                'fundamental_weight': fundamental_weight
            },
            'risk_control': {
                'max_position_size': max_position_size,
                'confidence_threshold': confidence_threshold,
                'stop_loss_threshold': stop_loss_threshold,
                'volatility_adjustment': volatility_adjustment
            }
        }
        
        # 保存到session state
        st.session_state['llm_config'] = config
        st.success("✅ 配置已保存！")


def render_performance_monitoring_tab(decision_service: DecisionService) -> None:
    """渲染性能監控標籤頁。

    Args:
        decision_service: 決策服務
    """
    st.header("📈 性能監控")
    
    # 實時統計
    st.subheader("📊 實時統計")
    
    try:
        stats = decision_service.get_performance_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="總請求數",
                value=stats.get('total_requests', 0),
                delta=None
            )
        
        with col2:
            success_rate = stats.get('success_rate', 0)
            st.metric(
                label="成功率",
                value=f"{success_rate:.1%}",
                delta=None
            )
        
        with col3:
            avg_time = stats.get('average_processing_time', 0)
            st.metric(
                label="平均處理時間",
                value=f"{avg_time:.2f}s",
                delta=None
            )
        
        with col4:
            cache_rate = stats.get('cache_hit_rate', 0)
            st.metric(
                label="快取命中率",
                value=f"{cache_rate:.1%}",
                delta=None
            )
        
        # 詳細統計圖表
        render_performance_charts(stats)
        
    except Exception as e:
        st.error(f"獲取性能統計失敗: {e}")


def render_performance_charts(stats: Dict[str, Any]) -> None:
    """渲染性能圖表。

    Args:
        stats: 性能統計數據
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    # 成功率餅圖
    col1, col2 = st.columns(2)
    
    with col1:
        fig1 = go.Figure(data=go.Pie(
            labels=['成功', '失敗'],
            values=[
                stats.get('successful_requests', 0),
                stats.get('failed_requests', 0)
            ],
            hole=0.3,
            marker_colors=['#28a745', '#dc3545']
        ))
        
        fig1.update_layout(
            title="請求成功率分佈",
            height=300
        )
        
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # 快取效果圖
        cache_hits = stats.get('cache_hits', 0)
        total_requests = stats.get('total_requests', 1)
        cache_misses = total_requests - cache_hits
        
        fig2 = go.Figure(data=go.Pie(
            labels=['快取命中', '快取未命中'],
            values=[cache_hits, cache_misses],
            hole=0.3,
            marker_colors=['#17a2b8', '#ffc107']
        ))
        
        fig2.update_layout(
            title="快取效果分佈",
            height=300
        )
        
        st.plotly_chart(fig2, use_container_width=True)


# 主函數
def main():
    """主函數。"""
    render_llm_decision_page()


if __name__ == "__main__":
    main()
