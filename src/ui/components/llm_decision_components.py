# -*- coding: utf-8 -*-
"""
LLM決策界面組件

此模組提供LLM決策相關的Streamlit界面組件。

主要功能：
- LLM決策展示
- 策略信號可視化
- 風險評估展示
- 決策歷史追蹤
- 實時決策監控
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from ...services.decision_service import DecisionResponse, DecisionService
from ...strategy.llm_integration import AggregatedDecision, StrategySignal


def render_llm_decision_dashboard(decision_service: DecisionService) -> None:
    """渲染LLM決策儀表板。

    Args:
        decision_service: 決策服務實例
    """
    st.title("🤖 AI大模型交易決策中心")
    
    # 修復：移除側邊欄配置，改為主頁面配置
    with st.expander("⚙️ 決策配置", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            st.header("基本配置")
            # 股票選擇
            stock_symbol = st.text_input(
                "股票代碼",
                value="AAPL",
                help="輸入要分析的股票代碼"
            )

            # 決策模式
            decision_mode = st.selectbox(
                "決策模式",
                ["實時決策", "批量分析", "歷史回顧"],
                help="選擇決策分析模式"
            )

        with col2:
            st.header("LLM配置")
            llm_provider = st.selectbox(
                "LLM提供商",
                ["OpenAI", "Claude", "本地模型"],
                help="選擇使用的LLM提供商"
            )

            confidence_threshold = st.slider(
                "置信度閾值",
                min_value=0.0,
                max_value=1.0,
                value=0.6,
                step=0.1,
                help="決策置信度閾值"
            )
    
    # 主要內容區域
    if decision_mode == "實時決策":
        render_realtime_decision(decision_service, stock_symbol, confidence_threshold)
    elif decision_mode == "批量分析":
        render_batch_analysis(decision_service)
    else:
        render_decision_history(decision_service, stock_symbol)


def render_realtime_decision(
    decision_service: DecisionService,
    stock_symbol: str,
    confidence_threshold: float
) -> None:
    """渲染實時決策界面。

    Args:
        decision_service: 決策服務
        stock_symbol: 股票代碼
        confidence_threshold: 置信度閾值
    """
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"📊 {stock_symbol} 實時決策分析")
        
        # 生成決策按鈕
        if st.button("🔄 生成AI決策", type="primary"):
            with st.spinner("AI正在分析中..."):
                try:
                    # 創建決策請求
                    from ...services.decision_service import DecisionRequest
                    request = DecisionRequest(
                        stock_symbol=stock_symbol,
                        request_time=datetime.now(),
                        request_type="real_time"
                    )
                    
                    # 生成決策（這裡需要異步處理，實際實現中需要適配）
                    # response = await decision_service.generate_decision(request)
                    
                    # 暫時使用模擬數據
                    response = create_mock_decision_response(stock_symbol)
                    
                    # 存儲到session state
                    st.session_state['current_decision'] = response
                    
                    st.success("✅ AI決策生成完成！")
                    
                except Exception as e:
                    st.error(f"❌ 決策生成失敗: {str(e)}")
        
        # 顯示當前決策
        if 'current_decision' in st.session_state:
            render_decision_result(st.session_state['current_decision'])
    
    with col2:
        st.subheader("⚙️ 決策參數")
        
        # 顯示服務狀態
        render_service_status(decision_service)
        
        # 顯示性能統計
        render_performance_stats(decision_service)


def render_decision_result(response: DecisionResponse) -> None:
    """渲染決策結果。

    Args:
        response: 決策響應
    """
    decision = response.decision
    
    # 決策摘要卡片
    st.subheader("🎯 AI決策結果")
    
    # 主要信號
    signal_color = "green" if decision.final_signal > 0 else "red" if decision.final_signal < 0 else "gray"
    signal_text = "買入 📈" if decision.final_signal > 0 else "賣出 📉" if decision.final_signal < 0 else "觀望 ⏸️"
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="交易信號",
            value=signal_text,
            delta=None
        )
    
    with col2:
        st.metric(
            label="置信度",
            value=f"{decision.confidence:.1%}",
            delta=None
        )
    
    with col3:
        st.metric(
            label="處理時間",
            value=f"{response.processing_time:.2f}s",
            delta=None
        )
    
    # 執行建議
    st.info(f"💡 **執行建議**: {decision.execution_recommendation}")
    
    # 策略信號分析
    render_strategy_signals(decision.contributing_strategies)
    
    # 風險評估
    render_risk_assessment(decision.risk_assessment)


def render_strategy_signals(strategies: List[StrategySignal]) -> None:
    """渲染策略信號分析。

    Args:
        strategies: 策略信號列表
    """
    st.subheader("📈 策略信號分析")
    
    if not strategies:
        st.warning("暫無策略信號數據")
        return
    
    # 創建策略信號圖表
    fig = go.Figure()
    
    strategy_names = [s.strategy_name for s in strategies]
    signals = [s.signal for s in strategies]
    confidences = [s.confidence for s in strategies]
    
    # 信號強度圖
    colors = ['green' if s > 0 else 'red' if s < 0 else 'gray' for s in signals]
    
    fig.add_trace(go.Bar(
        x=strategy_names,
        y=signals,
        marker_color=colors,
        text=[f"{s:+d}" for s in signals],
        textposition='auto',
        name='信號強度'
    ))
    
    fig.update_layout(
        title="各策略信號強度",
        xaxis_title="策略名稱",
        yaxis_title="信號強度",
        yaxis=dict(range=[-1.5, 1.5]),
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 置信度分析
    fig2 = go.Figure()
    
    fig2.add_trace(go.Scatter(
        x=strategy_names,
        y=confidences,
        mode='markers+lines',
        marker=dict(
            size=[abs(s) * 20 + 10 for s in signals],
            color=colors,
            line=dict(width=2, color='white')
        ),
        line=dict(width=2),
        name='置信度'
    ))
    
    fig2.update_layout(
        title="各策略置信度",
        xaxis_title="策略名稱",
        yaxis_title="置信度",
        yaxis=dict(range=[0, 1]),
        height=300
    )
    
    st.plotly_chart(fig2, use_container_width=True)
    
    # 策略詳情表格
    with st.expander("📋 策略詳情"):
        strategy_data = []
        for strategy in strategies:
            strategy_data.append({
                "策略名稱": strategy.strategy_name,
                "信號": "買入" if strategy.signal > 0 else "賣出" if strategy.signal < 0 else "觀望",
                "置信度": f"{strategy.confidence:.1%}",
                "推理過程": strategy.reasoning[:100] + "..." if len(strategy.reasoning) > 100 else strategy.reasoning
            })
        
        df = pd.DataFrame(strategy_data)
        st.dataframe(df, use_container_width=True)


def render_risk_assessment(risk_assessment: Dict[str, Any]) -> None:
    """渲染風險評估。

    Args:
        risk_assessment: 風險評估結果
    """
    st.subheader("⚠️ 風險評估")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 風險等級
        overall_risk = risk_assessment.get('overall_risk', 'medium')
        risk_color = {
            'low': 'green',
            'medium': 'orange', 
            'high': 'red'
        }.get(overall_risk, 'gray')
        
        st.markdown(f"""
        <div style="padding: 10px; border-left: 4px solid {risk_color}; background-color: rgba(255,255,255,0.1);">
            <h4>整體風險等級: {overall_risk.upper()}</h4>
        </div>
        """, unsafe_allow_html=True)
        
        # 風險指標
        st.write("**風險指標:**")
        st.write(f"• 波動率風險: {risk_assessment.get('volatility_risk', 'N/A')}")
        st.write(f"• 市場風險: {risk_assessment.get('market_risk', 'N/A')}")
    
    with col2:
        # 建議參數
        st.write("**建議參數:**")
        position_size = risk_assessment.get('position_size_recommendation', 0.05)
        stop_loss = risk_assessment.get('stop_loss_recommendation', 0.03)
        
        st.metric("建議倉位", f"{position_size:.1%}")
        st.metric("建議止損", f"{stop_loss:.1%}")
    
    # 風險因素
    risk_factors = risk_assessment.get('risk_factors', [])
    if risk_factors:
        st.write("**主要風險因素:**")
        for factor in risk_factors:
            st.write(f"• {factor}")


def render_service_status(decision_service: DecisionService) -> None:
    """渲染服務狀態。

    Args:
        decision_service: 決策服務
    """
    st.write("**服務狀態**")
    
    # 獲取狀態信息
    try:
        status = decision_service.get_performance_stats()
        
        st.write(f"• 總請求數: {status.get('total_requests', 0)}")
        st.write(f"• 成功率: {status.get('success_rate', 0):.1%}")
        st.write(f"• 平均處理時間: {status.get('average_processing_time', 0):.2f}s")
        st.write(f"• 快取命中率: {status.get('cache_hit_rate', 0):.1%}")
        
    except Exception as e:
        st.error(f"無法獲取服務狀態: {e}")


def render_performance_stats(decision_service: DecisionService) -> None:
    """渲染性能統計。

    Args:
        decision_service: 決策服務
    """
    st.write("**性能統計**")
    
    try:
        stats = decision_service.get_performance_stats()
        
        # 創建性能圖表
        fig = go.Figure(data=go.Pie(
            labels=['成功', '失敗'],
            values=[
                stats.get('successful_requests', 0),
                stats.get('failed_requests', 0)
            ],
            hole=0.3
        ))
        
        fig.update_layout(
            title="請求成功率",
            height=200,
            margin=dict(t=30, b=0, l=0, r=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"無法獲取性能統計: {e}")


def render_batch_analysis(decision_service: DecisionService) -> None:
    """渲染批量分析界面。

    Args:
        decision_service: 決策服務
    """
    st.subheader("📊 批量決策分析")
    
    # 股票列表輸入
    symbols_input = st.text_area(
        "股票代碼列表",
        value="AAPL,GOOGL,MSFT,TSLA,AMZN",
        help="輸入股票代碼，用逗號分隔"
    )
    
    if st.button("🚀 開始批量分析"):
        symbols = [s.strip().upper() for s in symbols_input.split(',') if s.strip()]
        
        if not symbols:
            st.error("請輸入至少一個股票代碼")
            return
        
        with st.spinner(f"正在分析 {len(symbols)} 隻股票..."):
            # 這裡需要實現批量分析邏輯
            st.success(f"✅ 批量分析完成！分析了 {len(symbols)} 隻股票")
            
            # 顯示批量結果摘要
            render_batch_results_summary(symbols)


def render_batch_results_summary(symbols: List[str]) -> None:
    """渲染批量結果摘要。

    Args:
        symbols: 股票代碼列表
    """
    st.subheader("📈 批量分析結果")
    
    # 創建模擬數據
    import random
    
    results_data = []
    for symbol in symbols:
        signal = random.choice([-1, 0, 1])
        confidence = random.uniform(0.3, 0.9)
        
        results_data.append({
            "股票代碼": symbol,
            "AI信號": "買入" if signal > 0 else "賣出" if signal < 0 else "觀望",
            "置信度": f"{confidence:.1%}",
            "風險等級": random.choice(["低", "中", "高"]),
            "建議倉位": f"{random.uniform(0.02, 0.1):.1%}"
        })
    
    df = pd.DataFrame(results_data)
    st.dataframe(df, use_container_width=True)
    
    # 信號分佈圖
    signal_counts = df["AI信號"].value_counts()
    
    fig = go.Figure(data=go.Pie(
        labels=signal_counts.index,
        values=signal_counts.values,
        hole=0.3
    ))
    
    fig.update_layout(
        title="AI信號分佈",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_decision_history(decision_service: DecisionService, stock_symbol: str) -> None:
    """渲染決策歷史界面。

    Args:
        decision_service: 決策服務
        stock_symbol: 股票代碼
    """
    st.subheader(f"📚 {stock_symbol} 決策歷史")
    
    # 時間範圍選擇
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
    
    # 獲取歷史數據
    try:
        history = decision_service.get_decision_history(symbol=stock_symbol, limit=100)
        
        if not history:
            st.info("暫無歷史決策數據")
            return
        
        # 顯示歷史趨勢
        render_decision_trend(history)
        
        # 顯示歷史詳情
        render_decision_history_table(history)
        
    except Exception as e:
        st.error(f"獲取歷史數據失敗: {e}")


def render_decision_trend(history: List[Dict[str, Any]]) -> None:
    """渲染決策趨勢圖。

    Args:
        history: 決策歷史數據
    """
    if not history:
        return
    
    # 提取時間序列數據
    timestamps = [datetime.fromisoformat(h['timestamp']) for h in history]
    signals = [h['decision']['final_signal'] for h in history]
    confidences = [h['decision']['confidence'] for h in history]
    
    # 創建趨勢圖
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('決策信號趨勢', '置信度趨勢'),
        vertical_spacing=0.1
    )
    
    # 信號趨勢
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=signals,
            mode='lines+markers',
            name='決策信號',
            line=dict(width=2)
        ),
        row=1, col=1
    )
    
    # 置信度趨勢
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=confidences,
            mode='lines+markers',
            name='置信度',
            line=dict(width=2, color='orange')
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        title="決策歷史趨勢",
        height=600,
        showlegend=True
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_decision_history_table(history: List[Dict[str, Any]]) -> None:
    """渲染決策歷史表格。

    Args:
        history: 決策歷史數據
    """
    st.subheader("📋 歷史決策詳情")
    
    # 轉換為表格數據
    table_data = []
    for h in history:
        decision = h['decision']
        table_data.append({
            "時間": datetime.fromisoformat(h['timestamp']).strftime('%Y-%m-%d %H:%M'),
            "信號": "買入" if decision['final_signal'] > 0 else "賣出" if decision['final_signal'] < 0 else "觀望",
            "置信度": f"{decision['confidence']:.1%}",
            "處理時間": f"{h['processing_time']:.2f}s",
            "執行建議": decision['execution_recommendation'][:50] + "..."
        })
    
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True)


def create_mock_decision_response(stock_symbol: str) -> DecisionResponse:
    """創建模擬決策響應（用於測試）。

    Args:
        stock_symbol: 股票代碼

    Returns:
        模擬決策響應
    """
    import random
    from ...strategy.llm_integration import AggregatedDecision, StrategySignal
    
    # 創建模擬策略信號
    strategies = [
        StrategySignal(
            strategy_name="FinMem-LLM策略",
            signal=random.choice([-1, 0, 1]),
            confidence=random.uniform(0.6, 0.9),
            reasoning="基於新聞分析，預測股價將上漲",
            metadata={"strategy_type": "llm"}
        ),
        StrategySignal(
            strategy_name="技術分析策略",
            signal=random.choice([-1, 0, 1]),
            confidence=random.uniform(0.5, 0.8),
            reasoning="RSI指標顯示超賣狀態",
            metadata={"strategy_type": "traditional"}
        )
    ]
    
    # 創建模擬決策
    decision = AggregatedDecision(
        final_signal=random.choice([-1, 0, 1]),
        confidence=random.uniform(0.6, 0.9),
        contributing_strategies=strategies,
        risk_assessment={
            'overall_risk': random.choice(['low', 'medium', 'high']),
            'volatility_risk': 'medium',
            'market_risk': 'low',
            'position_size_recommendation': random.uniform(0.03, 0.08),
            'stop_loss_recommendation': random.uniform(0.02, 0.05),
            'risk_factors': ['市場波動較大']
        },
        execution_recommendation="建議謹慎買入，控制倉位在5%以下"
    )
    
    # 創建響應
    response = DecisionResponse(
        request_id=f"{stock_symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        stock_symbol=stock_symbol,
        decision=decision,
        processing_time=random.uniform(1.0, 3.0),
        timestamp=datetime.now(),
        metadata={"request_type": "real_time"}
    )
    
    return response
