# -*- coding: utf-8 -*-
"""
學習中心頁面

此模組提供交互式量化交易學習界面，
整合交互式學習系統的所有功能。

主要功能：
- 概念學習界面
- 策略模擬器
- 風險教育模組
- 學習進度追蹤
- 個性化學習建議

界面特色：
- 中文友好界面
- 互動式學習體驗
- 實時反饋和指導
- 循序漸進的學習路徑
"""

import logging
import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime

# 學習系統在MVP版本中已移除，使用存根實現
LEARNING_SYSTEM_AVAILABLE = False
logging.info("學習系統在MVP版本中已簡化")

# 設定日誌
logger = logging.getLogger(__name__)


def show_learning_center():
    """顯示學習中心主頁面"""
    try:
        st.title("🎓 量化交易學習中心")
        st.markdown("歡迎來到量化交易學習中心！這裡提供完整的交互式學習體驗。")
        
        # 檢查學習系統可用性
        if not LEARNING_SYSTEM_AVAILABLE:
            st.info("📚 學習中心在MVP版本中已簡化")
            st.markdown("""
            ### 🎯 MVP版本功能說明

            學習中心的完整功能將在正式版本中提供，包括：
            - 📖 交互式量化交易教程
            - 🎮 策略模擬器和練習環境
            - 📊 個性化學習進度追蹤
            - 🧠 AI輔助學習建議
            - 💡 實戰案例分析

            ### 🚀 當前可用功能
            您可以通過以下方式開始學習：
            - 使用**回測分析**頁面練習策略開發
            - 在**風險管理**頁面了解風險控制
            - 通過**數據管理**頁面熟悉數據處理
            """)
            return
        
        # 初始化學習系統
        if 'learning_system' not in st.session_state:
            st.session_state.learning_system = InteractiveLearningSystem()
        
        learning_system = st.session_state.learning_system
        
        # 顯示學習儀表板
        learning_system.show_learning_dashboard()
        
    except Exception as e:
        logger.error(f"顯示學習中心失敗: {e}")
        st.error("❌ 學習中心載入失敗，請重新整理頁面")


def show_concept_learning():
    """顯示概念學習頁面"""
    try:
        st.header("📖 概念學習")
        st.markdown("深入學習量化交易的核心概念和理論知識。")
        
        if not LEARNING_SYSTEM_AVAILABLE:
            st.error("❌ 學習系統不可用")
            return
        
        # 概念選擇
        concept_categories = {
            "基礎概念": {
                "sharpe_ratio": "夏普比率",
                "max_drawdown": "最大回撤",
                "beta": "貝塔係數"
            },
            "技術指標": {
                "moving_average": "移動平均線",
                "rsi": "相對強弱指標",
                "macd": "MACD指標"
            },
            "風險管理": {
                "var": "風險價值",
                "volatility": "波動率",
                "correlation": "相關性"
            }
        }
        
        # 分類選擇
        selected_category = st.selectbox(
            "選擇學習分類",
            options=list(concept_categories.keys())
        )
        
        if selected_category:
            concepts = concept_categories[selected_category]
            
            # 概念選擇
            selected_concept = st.selectbox(
                "選擇要學習的概念",
                options=list(concepts.keys()),
                format_func=lambda x: concepts[x]
            )
            
            if selected_concept:
                # 顯示概念解釋
                learning_system = st.session_state.get('learning_system')
                if learning_system:
                    learning_system.concept_explainer.explain_concept(selected_concept)
        
    except Exception as e:
        logger.error(f"顯示概念學習失敗: {e}")
        st.error("❌ 概念學習載入失敗")


def show_strategy_simulation():
    """顯示策略模擬頁面"""
    try:
        st.header("🎯 策略模擬")
        st.markdown("通過互動式模擬學習不同的交易策略。")
        
        if not LEARNING_SYSTEM_AVAILABLE:
            st.error("❌ 學習系統不可用")
            return
        
        learning_system = st.session_state.get('learning_system')
        if not learning_system:
            st.error("❌ 學習系統未初始化")
            return
        
        # 策略選擇
        strategy_options = {
            "ma_crossover": "移動平均交叉策略",
            "rsi_reversal": "RSI反轉策略",
            "bollinger_bands": "布林帶策略"
        }
        
        selected_strategy = st.selectbox(
            "選擇策略類型",
            options=list(strategy_options.keys()),
            format_func=lambda x: strategy_options[x]
        )
        
        if selected_strategy:
            strategy_info = learning_system.strategy_simulator.strategies.get(selected_strategy)
            
            if strategy_info:
                st.subheader(f"📋 {strategy_info['name']}")
                st.write(f"**描述**: {strategy_info['description']}")
                st.write(f"**難度**: {'⭐' * strategy_info['difficulty']}")
                
                # 參數設置區域
                with st.expander("⚙️ 策略參數設置", expanded=True):
                    params = {}
                    
                    for param_name, param_info in strategy_info['parameters'].items():
                        params[param_name] = st.slider(
                            f"{param_name}",
                            min_value=param_info['min'],
                            max_value=param_info['max'],
                            value=param_info['default'],
                            help=f"調整{param_name}參數"
                        )
                
                # 模擬控制
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("🚀 開始策略模擬", type="primary"):
                        with st.spinner("正在運行策略模擬..."):
                            # 生成示例數據
                            np.random.seed(42)
                            dates = pd.date_range(start='2023-01-01', periods=252, freq='D')
                            prices = 100 + np.cumsum(np.random.normal(0.001, 0.02, 252))
                            data = pd.DataFrame({'close': prices}, index=dates)
                            
                            # 運行模擬
                            result = learning_system.strategy_simulator.simulate_strategy(
                                selected_strategy, params, data
                            )
                            
                            if 'error' not in result:
                                # 顯示結果
                                st.success("✅ 策略模擬完成！")
                                
                                # 績效指標
                                metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
                                
                                with metrics_col1:
                                    st.metric(
                                        "總收益率",
                                        f"{result['total_return']:.2%}",
                                        delta=f"{result['total_return']:.2%}"
                                    )
                                
                                with metrics_col2:
                                    st.metric(
                                        "年化波動率",
                                        f"{result['volatility']:.2%}"
                                    )
                                
                                with metrics_col3:
                                    st.metric(
                                        "夏普比率",
                                        f"{result['sharpe_ratio']:.2f}"
                                    )
                                
                                # 圖表顯示
                                st.subheader("📈 策略表現圖表")
                                
                                import plotly.graph_objects as go
                                
                                fig = go.Figure()
                                
                                # 價格線
                                fig.add_trace(go.Scatter(
                                    x=result['data'].index,
                                    y=result['data']['close'],
                                    name="價格",
                                    line=dict(color='blue')
                                ))
                                
                                # 移動平均線（如果有）
                                if 'MA_short' in result['data'].columns:
                                    fig.add_trace(go.Scatter(
                                        x=result['data'].index,
                                        y=result['data']['MA_short'],
                                        name="短期均線",
                                        line=dict(color='orange')
                                    ))
                                    
                                    fig.add_trace(go.Scatter(
                                        x=result['data'].index,
                                        y=result['data']['MA_long'],
                                        name="長期均線",
                                        line=dict(color='red')
                                    ))
                                
                                # 買賣信號
                                buy_signals = result['data'][result['data']['positions'] == 1]
                                sell_signals = result['data'][result['data']['positions'] == -1]
                                
                                if not buy_signals.empty:
                                    fig.add_trace(go.Scatter(
                                        x=buy_signals.index,
                                        y=buy_signals['close'],
                                        mode='markers',
                                        name="買入信號",
                                        marker=dict(color='green', size=10, symbol='triangle-up')
                                    ))
                                
                                if not sell_signals.empty:
                                    fig.add_trace(go.Scatter(
                                        x=sell_signals.index,
                                        y=sell_signals['close'],
                                        mode='markers',
                                        name="賣出信號",
                                        marker=dict(color='red', size=10, symbol='triangle-down')
                                    ))
                                
                                fig.update_layout(
                                    title=f"{strategy_info['name']} - 策略模擬結果",
                                    xaxis_title="日期",
                                    yaxis_title="價格",
                                    hovermode='x unified'
                                )
                                
                                st.plotly_chart(fig, use_container_width=True)
                                
                                # 學習要點
                                st.subheader("💡 學習要點")
                                
                                if selected_strategy == "ma_crossover":
                                    st.info("""
                                    **移動平均交叉策略學習要點：**
                                    - 短期均線上穿長期均線時產生買入信號
                                    - 短期均線下穿長期均線時產生賣出信號
                                    - 適用於趨勢明顯的市場環境
                                    - 在震盪市場中可能產生較多假信號
                                    """)
                                elif selected_strategy == "rsi_reversal":
                                    st.info("""
                                    **RSI反轉策略學習要點：**
                                    - RSI低於30時市場可能超賣，考慮買入
                                    - RSI高於70時市場可能超買，考慮賣出
                                    - 適用於震盪市場環境
                                    - 在強趨勢市場中可能過早進出場
                                    """)
                            else:
                                st.error(f"❌ 策略模擬失敗: {result.get('error', '未知錯誤')}")
                
                with col2:
                    if st.button("📊 查看策略詳情"):
                        st.info(f"""
                        **策略類型**: {strategy_info['name']}
                        
                        **策略描述**: {strategy_info['description']}
                        
                        **適用市場**: 根據策略特性選擇合適的市場環境
                        
                        **風險提示**: 所有策略都有其適用條件和風險，請謹慎使用
                        """)
        
    except Exception as e:
        logger.error(f"顯示策略模擬失敗: {e}")
        st.error("❌ 策略模擬載入失敗")


def show_risk_education():
    """顯示風險教育頁面"""
    try:
        st.header("⚠️ 風險教育")
        st.markdown("通過模擬不同的市場風險場景，學習風險管理的重要性。")
        
        if not LEARNING_SYSTEM_AVAILABLE:
            st.error("❌ 學習系統不可用")
            return
        
        learning_system = st.session_state.get('learning_system')
        if not learning_system:
            st.error("❌ 學習系統未初始化")
            return
        
        # 風險場景選擇
        scenario_options = {
            "market_crash": "市場崩盤",
            "high_volatility": "高波動期",
            "sector_rotation": "板塊輪動"
        }
        
        selected_scenario = st.selectbox(
            "選擇風險場景",
            options=list(scenario_options.keys()),
            format_func=lambda x: scenario_options[x]
        )
        
        if selected_scenario:
            scenario_info = learning_system.risk_educator.risk_scenarios.get(selected_scenario)
            
            if scenario_info:
                st.subheader(f"📋 {scenario_info['name']}")
                st.write(f"**場景描述**: {scenario_info['description']}")
                
                if st.button("🎭 模擬風險場景", type="primary"):
                    with st.spinner("正在模擬風險場景..."):
                        # 生成示例投資組合數據
                        np.random.seed(42)
                        dates = pd.date_range(start='2023-01-01', periods=252, freq='D')
                        prices = 100 + np.cumsum(np.random.normal(0.001, 0.015, 252))
                        portfolio_data = pd.DataFrame({'close': prices}, index=dates)
                        
                        # 運行風險模擬
                        result = learning_system.risk_educator.simulate_risk_scenario(
                            selected_scenario, portfolio_data
                        )
                        
                        if 'error' not in result:
                            st.success("✅ 風險場景模擬完成！")
                            
                            # 風險指標
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.metric(
                                    "最大回撤",
                                    f"{result['max_drawdown']:.2%}",
                                    delta=f"{result['max_drawdown']:.2%}",
                                    delta_color="inverse"
                                )
                            
                            with col2:
                                st.metric(
                                    "恢復時間",
                                    f"{result.get('recovery_time', 0)}天"
                                )
                            
                            # 對比圖表
                            st.subheader("📉 風險場景對比")
                            
                            import plotly.graph_objects as go
                            
                            fig = go.Figure()
                            
                            fig.add_trace(go.Scatter(
                                y=result['normal_portfolio'],
                                name="正常情況",
                                line=dict(color='blue')
                            ))
                            
                            fig.add_trace(go.Scatter(
                                y=result['scenario_portfolio'],
                                name="風險場景",
                                line=dict(color='red')
                            ))
                            
                            fig.update_layout(
                                title=f"{scenario_info['name']} - 風險場景對比",
                                xaxis_title="時間",
                                yaxis_title="投資組合價值",
                                hovermode='x unified'
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # 風險教育要點
                            st.subheader("🎯 風險管理要點")
                            
                            if selected_scenario == "market_crash":
                                st.warning("""
                                **市場崩盤風險管理要點：**
                                - 分散投資，不要把雞蛋放在同一個籃子裡
                                - 設置止損點，控制最大損失
                                - 保持適當的現金比例
                                - 避免過度槓桿
                                - 定期檢視和調整投資組合
                                """)
                            elif selected_scenario == "high_volatility":
                                st.warning("""
                                **高波動期風險管理要點：**
                                - 降低倉位，減少風險暴露
                                - 增加對沖工具的使用
                                - 縮短持倉週期
                                - 提高現金比例
                                - 密切監控市場動態
                                """)
                        else:
                            st.error(f"❌ 風險場景模擬失敗: {result.get('error', '未知錯誤')}")
        
    except Exception as e:
        logger.error(f"顯示風險教育失敗: {e}")
        st.error("❌ 風險教育載入失敗")


def show_learning_progress():
    """顯示學習進度頁面"""
    try:
        st.header("📈 學習進度")
        st.markdown("追蹤您的學習進度和成就。")
        
        # 模擬學習進度數據
        progress_data = {
            "量化交易基礎": 85,
            "技術指標分析": 70,
            "策略開發": 45,
            "風險管理": 30,
            "高級技術": 10
        }
        
        # 進度顯示
        st.subheader("📊 學習進度概覽")
        
        for topic, progress in progress_data.items():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**{topic}**")
                st.progress(progress / 100)
            
            with col2:
                st.metric("完成度", f"{progress}%")
        
        # 學習統計
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 學習統計")
            
            stats_data = {
                "總學習時間": "12.5小時",
                "完成練習": "23個",
                "掌握概念": "18個",
                "策略模擬": "8次"
            }
            
            for metric, value in stats_data.items():
                st.metric(metric, value)
        
        with col2:
            st.subheader("🏆 學習成就")
            
            achievements = [
                "🥉 量化新手 - 完成基礎學習",
                "🥈 策略探索者 - 完成5次策略模擬",
                "🥇 風險管理師 - 掌握風險控制"
            ]
            
            for achievement in achievements:
                st.success(achievement)
        
        # 學習建議
        st.subheader("💡 個性化學習建議")
        st.info("""
        **下一步學習建議：**
        
        1. **策略開發模組** - 您在這個領域還有提升空間，建議深入學習策略構建方法
        2. **風險管理實踐** - 通過更多風險場景模擬來提升風險意識
        3. **高級技術學習** - 準備好挑戰更高級的量化技術了
        
        **推薦學習路徑：** 策略開發 → 風險管理 → 高級技術
        """)
        
    except Exception as e:
        logger.error(f"顯示學習進度失敗: {e}")
        st.error("❌ 學習進度載入失敗")


def show() -> None:
    """顯示學習中心頁面 (Web UI 入口點).

    Returns:
        None
    """
    show_learning_center()


# 主函數
def main():
    """學習中心主函數"""
    show_learning_center()


if __name__ == "__main__":
    main()
