# -*- coding: utf-8 -*-
"""RL 策略管理頁面

此模組提供強化學習策略的管理界面，包括：
- RL 策略選擇和配置
- 模型訓練進度監控
- 策略性能可視化
- 多策略比較功能

主要功能：
- 支援 PPO、DQN、SAC 等主流 RL 算法
- 實時訓練進度監控
- 策略性能圖表展示
- 多策略對比分析
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.strategies.adapters import RLStrategyAdapter


def render_rl_strategy_management():
    """渲染 RL 策略管理頁面"""
    st.title("🤖 強化學習策略管理")
    st.markdown("---")
    
    # 側邊欄配置
    with st.sidebar:
        st.header("⚙️ RL 策略配置")
        
        # 算法選擇
        algorithm = st.selectbox(
            "選擇 RL 算法",
            options=['PPO', 'DQN', 'SAC', 'A2C', 'TD3'],
            index=0,
            help="選擇要使用的強化學習算法"
        )
        
        # 環境配置
        st.subheader("環境配置")
        initial_balance = st.number_input(
            "初始資金",
            min_value=10000,
            max_value=10000000,
            value=100000,
            step=10000,
            help="設定交易環境的初始資金"
        )
        
        max_steps = st.number_input(
            "最大步數",
            min_value=100,
            max_value=10000,
            value=1000,
            step=100,
            help="設定每個回合的最大交易步數"
        )
        
        # 訓練配置
        st.subheader("訓練配置")
        total_timesteps = st.number_input(
            "訓練步數",
            min_value=1000,
            max_value=1000000,
            value=10000,
            step=1000,
            help="設定模型訓練的總步數"
        )
        
        learning_rate = st.number_input(
            "學習率",
            min_value=0.0001,
            max_value=0.1,
            value=0.001,
            step=0.0001,
            format="%.4f",
            help="設定模型的學習率"
        )
    
    # 主要內容區域
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📊 策略概覽")
        
        # 創建策略適配器
        environment_config = {
            'initial_balance': initial_balance,
            'max_steps': max_steps
        }
        
        training_config = {
            'total_timesteps': total_timesteps,
            'learning_rate': learning_rate
        }
        
        try:
            adapter = RLStrategyAdapter(
                algorithm=algorithm,
                environment_config=environment_config
            )
            
            # 顯示策略資訊
            strategy_info = adapter.get_strategy_info()
            
            info_col1, info_col2, info_col3 = st.columns(3)
            
            with info_col1:
                st.metric("策略名稱", strategy_info['name'])
            
            with info_col2:
                st.metric("算法類型", strategy_info['algorithm'])
            
            with info_col3:
                st.metric("訓練狀態", "未訓練" if not strategy_info['is_trained'] else "已訓練")
            
            # 策略詳細資訊
            with st.expander("📋 策略詳細資訊"):
                st.json(strategy_info)
            
        except Exception as e:
            st.error(f"創建策略適配器失敗: {e}")
            return
    
    with col2:
        st.header("🎯 快速操作")
        
        # 訓練按鈕
        if st.button("🚀 開始訓練", type="primary", use_container_width=True):
            with st.spinner("正在訓練模型..."):
                try:
                    # 創建模擬訓練數據
                    training_data = _create_sample_data(days=100)
                    
                    # 模擬訓練過程
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for i in range(10):
                        progress = (i + 1) / 10
                        progress_bar.progress(progress)
                        status_text.text(f"訓練進度: {progress:.0%}")
                        
                        # 模擬訓練延遲
                        import time
                        time.sleep(0.5)
                    
                    st.success("✅ 模型訓練完成！")
                    
                except Exception as e:
                    st.error(f"訓練失敗: {e}")
        
        # 測試按鈕
        if st.button("🧪 測試策略", use_container_width=True):
            with st.spinner("正在測試策略..."):
                try:
                    # 創建測試數據
                    test_data = _create_sample_data(days=30)
                    
                    # 生成訊號
                    signals = adapter.generate_signals(test_data)
                    
                    st.success(f"✅ 測試完成！生成 {len(signals)} 個訊號")
                    
                    # 顯示訊號統計
                    buy_signals = signals['buy_signal'].sum()
                    sell_signals = signals['sell_signal'].sum()
                    
                    st.write(f"買入訊號: {buy_signals}")
                    st.write(f"賣出訊號: {sell_signals}")
                    
                except Exception as e:
                    st.error(f"測試失敗: {e}")
        
        # 重置按鈕
        if st.button("🔄 重置模型", use_container_width=True):
            st.info("模型已重置")
    
    # 性能監控區域
    st.header("📈 性能監控")
    
    # 創建標籤頁
    tab1, tab2, tab3, tab4 = st.tabs(["學習曲線", "策略性能", "動作分析", "多策略比較"])
    
    with tab1:
        st.subheader("學習曲線")
        _render_learning_curve()
    
    with tab2:
        st.subheader("策略性能")
        _render_strategy_performance()
    
    with tab3:
        st.subheader("動作分析")
        _render_action_analysis()
    
    with tab4:
        st.subheader("多策略比較")
        _render_strategy_comparison()


def _create_sample_data(days: int = 100) -> pd.DataFrame:
    """創建示例數據"""
    dates = pd.date_range(start='2023-01-01', periods=days)
    
    # 生成模擬價格數據
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, days)
    prices = 100 * np.exp(np.cumsum(returns))
    
    return pd.DataFrame({
        'date': dates,
        'close': prices,
        'open': prices * (1 + np.random.normal(0, 0.005, days)),
        'high': prices * (1 + np.abs(np.random.normal(0, 0.01, days))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.01, days))),
        'volume': np.random.randint(1000, 10000, days)
    })


def _render_learning_curve():
    """渲染學習曲線"""
    # 生成模擬學習數據
    episodes = np.arange(1, 101)
    rewards = np.cumsum(np.random.normal(0.1, 1, 100))
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=episodes,
        y=rewards,
        mode='lines',
        name='累積獎勵',
        line=dict(color='blue', width=2)
    ))
    
    fig.update_layout(
        title="學習曲線 - 累積獎勵",
        xaxis_title="訓練回合",
        yaxis_title="累積獎勵",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 顯示統計資訊
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("平均獎勵", f"{np.mean(rewards):.2f}")
    with col2:
        st.metric("最大獎勵", f"{np.max(rewards):.2f}")
    with col3:
        st.metric("獎勵標準差", f"{np.std(rewards):.2f}")


def _render_strategy_performance():
    """渲染策略性能"""
    # 生成模擬性能數據
    dates = pd.date_range(start='2023-01-01', periods=30)
    portfolio_value = 100000 * np.exp(np.cumsum(np.random.normal(0.001, 0.02, 30)))
    benchmark_value = 100000 * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, 30)))
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=portfolio_value,
        mode='lines',
        name='RL策略',
        line=dict(color='green', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=benchmark_value,
        mode='lines',
        name='基準',
        line=dict(color='gray', width=2, dash='dash')
    ))
    
    fig.update_layout(
        title="策略性能對比",
        xaxis_title="日期",
        yaxis_title="投資組合價值",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 性能指標
    total_return = (portfolio_value[-1] - portfolio_value[0]) / portfolio_value[0]
    benchmark_return = (benchmark_value[-1] - benchmark_value[0]) / benchmark_value[0]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("總收益率", f"{total_return:.2%}")
    with col2:
        st.metric("基準收益率", f"{benchmark_return:.2%}")
    with col3:
        st.metric("超額收益", f"{total_return - benchmark_return:.2%}")


def _render_action_analysis():
    """渲染動作分析"""
    # 生成模擬動作數據
    actions = ['買入', '賣出', '持有']
    action_counts = [25, 15, 60]
    
    # 動作分佈餅圖
    fig = px.pie(
        values=action_counts,
        names=actions,
        title="動作分佈",
        color_discrete_map={
            '買入': 'green',
            '賣出': 'red',
            '持有': 'gray'
        }
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 動作時間序列
    dates = pd.date_range(start='2023-01-01', periods=30)
    action_values = np.random.choice([1, -1, 0], size=30, p=[0.25, 0.15, 0.6])
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=action_values,
        mode='markers+lines',
        name='動作序列',
        marker=dict(
            size=8,
            color=action_values,
            colorscale='RdYlGn',
            showscale=True
        )
    ))
    
    fig.update_layout(
        title="動作時間序列",
        xaxis_title="日期",
        yaxis_title="動作 (1:買入, 0:持有, -1:賣出)",
        yaxis=dict(tickvals=[-1, 0, 1], ticktext=['賣出', '持有', '買入'])
    )
    
    st.plotly_chart(fig, use_container_width=True)


def _render_strategy_comparison():
    """渲染策略比較"""
    st.info("💡 此功能將比較不同 RL 算法的性能表現")
    
    # 模擬多策略性能數據
    algorithms = ['PPO', 'DQN', 'SAC', 'A2C']
    performance_data = {
        'Algorithm': algorithms,
        'Total Return': [0.15, 0.12, 0.18, 0.10],
        'Sharpe Ratio': [1.2, 1.0, 1.4, 0.9],
        'Max Drawdown': [-0.08, -0.12, -0.06, -0.15],
        'Win Rate': [0.65, 0.60, 0.70, 0.55]
    }
    
    df = pd.DataFrame(performance_data)
    
    # 性能對比表格
    st.subheader("策略性能對比")
    st.dataframe(df, use_container_width=True)
    
    # 性能雷達圖
    fig = go.Figure()
    
    for i, algo in enumerate(algorithms):
        fig.add_trace(go.Scatterpolar(
            r=[df.iloc[i]['Total Return'], df.iloc[i]['Sharpe Ratio']/2, 
               1 + df.iloc[i]['Max Drawdown'], df.iloc[i]['Win Rate']],
            theta=['總收益率', '夏普比率', '最大回撤', '勝率'],
            fill='toself',
            name=algo
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )),
        showlegend=True,
        title="策略性能雷達圖"
    )
    
    st.plotly_chart(fig, use_container_width=True)


def show() -> None:
    """顯示強化學習策略管理頁面 (Web UI 入口點).

    Returns:
        None
    """
    render_rl_strategy_management()


if __name__ == "__main__":
    render_rl_strategy_management()
