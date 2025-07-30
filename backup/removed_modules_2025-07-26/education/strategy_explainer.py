# -*- coding: utf-8 -*-
"""
策略邏輯解釋器

此模組提供策略邏輯的詳細解釋功能，包括：
- 策略原理說明
- 視覺化策略邏輯
- 參數影響分析
- 實例演示
- 策略比較分析

Author: AI Trading System
Version: 1.0.0
"""

from typing import Dict, List, Optional, Any, Tuple
import logging

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


class StrategyExplainer:
    """
    策略邏輯解釋器

    提供策略邏輯的詳細解釋和視覺化功能，包括原理說明、
    參數影響分析、實例演示和比較分析。

    Attributes:
        strategy_explanations (Dict): 策略解釋庫
        visualization_templates (Dict): 視覺化模板
        parameter_effects (Dict): 參數影響分析

    Example:
        >>> explainer = StrategyExplainer()
        >>> explanation = explainer.explain_strategy('moving_average')
        >>> explainer.visualize_strategy_logic('moving_average', data)
    """

    def __init__(self):
        """初始化策略邏輯解釋器"""
        self.strategy_explanations = self._initialize_strategy_explanations()
        self.visualization_templates = self._initialize_visualization_templates()
        self.parameter_effects = self._initialize_parameter_effects()

    def _initialize_strategy_explanations(self) -> Dict[str, Dict[str, Any]]:
        """
        初始化策略解釋庫

        Returns:
            Dict[str, Dict[str, Any]]: 策略解釋字典
        """
        return {
            'moving_average': {
                'name': '移動平均線策略',
                'category': '趨勢跟隨',
                'difficulty': '初級',
                'principle': """
                ## 📈 移動平均線策略原理

                移動平均線策略是最經典的趨勢跟隨策略之一。它基於以下核心理念：

                ### 基本概念
                - **移動平均線**：一定期間內價格的平均值
                - **趨勢識別**：通過平均線的方向判斷趨勢
                - **信號生成**：通過價格與平均線或平均線之間的交叉產生信號

                ### 策略邏輯
                1. **買入信號**：短期均線上穿長期均線（金叉）
                2. **賣出信號**：短期均線下穿長期均線（死叉）
                3. **持有期間**：在信號之間保持部位
                """,
                'advantages': [
                    '邏輯簡單易懂，適合新手',
                    '在明確趨勢市場中表現良好',
                    '可以有效過濾市場噪音',
                    '風險相對可控'
                ],
                'disadvantages': [
                    '在震盪市場中容易產生假信號',
                    '存在滞後性，可能錯過最佳進出點',
                    '頻繁交叉可能增加交易成本'
                ],
                'parameters': {
                    'fast_period': {
                        'name': '短期週期',
                        'description': '短期移動平均線的計算週期',
                        'typical_range': '5-20天',
                        'effect': '週期越短，對價格變化越敏感，但也越容易產生假信號'
                    },
                    'slow_period': {
                        'name': '長期週期',
                        'description': '長期移動平均線的計算週期',
                        'typical_range': '20-100天',
                        'effect': '週期越長，趨勢越穩定，但反應越遲鈍'
                    }
                },
                'best_conditions': [
                    '明確的上升或下降趨勢',
                    '較低的市場波動率',
                    '流動性良好的股票'
                ]
            },
            'rsi_strategy': {
                'name': 'RSI 超買超賣策略',
                'category': '均值回歸',
                'difficulty': '初級',
                'principle': """
                ## 📊 RSI 策略原理

                RSI（相對強弱指標）策略基於市場超買超賣的概念，
                認為價格在極端水平後會回歸正常。

                ### RSI 指標說明
                - **計算方式**：基於一定期間內上漲和下跌的平均幅度
                - **數值範圍**：0-100
                - **超買區域**：通常 > 70
                - **超賣區域**：通常 < 30

                ### 策略邏輯
                1. **買入信號**：RSI 從超賣區域（<30）回升
                2. **賣出信號**：RSI 從超買區域（>70）回落
                3. **風險控制**：設定停損和止盈點
                """,
                'advantages': [
                    '在震盪市場中表現較好',
                    '能夠識別短期反轉機會',
                    '提供明確的進出場信號',
                    '可以與其他指標結合使用'
                ],
                'disadvantages': [
                    '在強趨勢市場中可能失效',
                    '可能在超買超賣區域停留較長時間',
                    '需要適當的參數調整'
                ],
                'parameters': {
                    'period': {
                        'name': 'RSI 週期',
                        'description': 'RSI 指標的計算週期',
                        'typical_range': '14天（標準）',
                        'effect': '週期越短越敏感，週期越長越穩定'
                    },
                    'oversold': {
                        'name': '超賣閾值',
                        'description': '判定超賣的 RSI 數值',
                        'typical_range': '20-30',
                        'effect': '數值越低，信號越少但越可靠'
                    },
                    'overbought': {
                        'name': '超買閾值',
                        'description': '判定超買的 RSI 數值',
                        'typical_range': '70-80',
                        'effect': '數值越高，信號越少但越可靠'
                    }
                },
                'best_conditions': [
                    '橫盤整理的市場環境',
                    '中等波動率的股票',
                    '有明確支撐阻力位的股票'
                ]
            },
            'momentum_strategy': {
                'name': '動量策略',
                'category': '趨勢跟隨',
                'difficulty': '中級',
                'principle': """
                ## 🚀 動量策略原理

                動量策略基於「強者恆強」的市場現象，
                認為表現好的股票會繼續表現好。

                ### 核心理念
                - **價格動量**：價格變化的持續性
                - **相對強度**：與市場或其他股票的比較
                - **趨勢延續**：短期趨勢會延續一段時間

                ### 策略邏輯
                1. **動量計算**：計算一定期間的價格變化率
                2. **排序選股**：選擇動量最強的股票
                3. **定期調整**：根據最新動量重新排序
                4. **風險控制**：設定停損和部位限制
                """,
                'advantages': [
                    '能夠捕捉強勢股票',
                    '在趨勢市場中表現優異',
                    '可以應用於多個市場',
                    '有良好的理論基礎'
                ],
                'disadvantages': [
                    '在市場轉向時風險較大',
                    '需要頻繁調整部位',
                    '交易成本可能較高',
                    '容易追高殺低'
                ],
                'parameters': {
                    'lookback_period': {
                        'name': '回望期間',
                        'description': '計算動量的時間窗口',
                        'typical_range': '1-12個月',
                        'effect': '期間越短越敏感，期間越長越穩定'
                    },
                    'rebalance_frequency': {
                        'name': '調整頻率',
                        'description': '重新選股和調整部位的頻率',
                        'typical_range': '每週到每月',
                        'effect': '頻率越高越能跟上市場變化，但交易成本越高'
                    }
                },
                'best_conditions': [
                    '明確的市場趨勢',
                    '較高的市場波動率',
                    '流動性充足的市場'
                ]
            }
        }

    def _initialize_visualization_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        初始化視覺化模板

        Returns:
            Dict[str, Dict[str, Any]]: 視覺化模板字典
        """
        return {
            'moving_average': {
                'chart_type': 'line_with_signals',
                'indicators': ['MA_fast', 'MA_slow'],
                'signals': ['buy', 'sell'],
                'colors': {'price': 'blue', 'MA_fast': 'red', 'MA_slow': 'green'}
            },
            'rsi_strategy': {
                'chart_type': 'subplot_with_oscillator',
                'main_chart': 'price',
                'oscillator': 'RSI',
                'threshold_lines': [30, 70],
                'colors': {'price': 'blue', 'RSI': 'purple'}
            },
            'momentum_strategy': {
                'chart_type': 'momentum_ranking',
                'indicators': ['momentum', 'ranking'],
                'colors': {'momentum': 'orange', 'ranking': 'green'}
            }
        }

    def _initialize_parameter_effects(self) -> Dict[str, Dict[str, Any]]:
        """
        初始化參數影響分析

        Returns:
            Dict[str, Dict[str, Any]]: 參數影響字典
        """
        return {
            'moving_average': {
                'fast_period': {
                    'increase_effect': '減少信號數量，降低敏感度',
                    'decrease_effect': '增加信號數量，提高敏感度',
                    'optimal_range': '5-20天'
                },
                'slow_period': {
                    'increase_effect': '增加趨勢穩定性，減少假信號',
                    'decrease_effect': '降低趨勢穩定性，增加假信號',
                    'optimal_range': '20-50天'
                }
            },
            'rsi_strategy': {
                'period': {
                    'increase_effect': '平滑RSI曲線，減少信號',
                    'decrease_effect': '增加RSI敏感度，增加信號',
                    'optimal_range': '14天（標準）'
                },
                'oversold': {
                    'increase_effect': '減少買入信號，提高信號品質',
                    'decrease_effect': '增加買入信號，可能增加假信號',
                    'optimal_range': '20-30'
                }
            }
        }

    def explain_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """
        解釋策略邏輯

        Args:
            strategy_id: 策略ID

        Returns:
            Optional[Dict[str, Any]]: 策略解釋
        """
        return self.strategy_explanations.get(strategy_id)

    def generate_strategy_demo_data(self, strategy_id: str,
                                  days: int = 100) -> pd.DataFrame:
        """
        生成策略演示資料

        Args:
            strategy_id: 策略ID
            days: 天數

        Returns:
            pd.DataFrame: 演示資料
        """
        np.random.seed(42)

        dates = pd.date_range(start='2023-01-01', periods=days, freq='D')

        # 根據策略類型生成不同的價格模式
        if strategy_id == 'moving_average':
            # 生成趨勢性價格
            trend = np.linspace(0, 0.3, days)
            noise = np.random.normal(0, 0.02, days)
            returns = trend / days + noise
        elif strategy_id == 'rsi_strategy':
            # 生成震盪性價格
            returns = np.random.normal(0, 0.025, days)
            # 添加週期性波動
            cycle = np.sin(np.linspace(0, 4*np.pi, days)) * 0.01
            returns += cycle
        else:
            # 預設隨機遊走
            returns = np.random.normal(0.001, 0.02, days)

        prices = 100 * np.exp(np.cumsum(returns))
        volumes = np.random.randint(1000000, 5000000, days)

        df = pd.DataFrame({
            'Date': dates,
            'Close': prices,
            'Volume': volumes,
            'Returns': returns
        })

        # 根據策略添加指標
        if strategy_id == 'moving_average':
            df['MA_10'] = df['Close'].rolling(10).mean()
            df['MA_30'] = df['Close'].rolling(30).mean()

            # 生成交易信號
            df['Signal'] = 0
            df.loc[df['MA_10'] > df['MA_30'], 'Signal'] = 1
            df.loc[df['MA_10'] < df['MA_30'], 'Signal'] = -1

        elif strategy_id == 'rsi_strategy':
            # 計算 RSI
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            # 生成交易信號
            df['Signal'] = 0
            df.loc[df['RSI'] < 30, 'Signal'] = 1
            df.loc[df['RSI'] > 70, 'Signal'] = -1

        return df

    def visualize_strategy_logic(self, strategy_id: str,
                               data: pd.DataFrame) -> go.Figure:
        """
        視覺化策略邏輯

        Args:
            strategy_id: 策略ID
            data: 資料

        Returns:
            go.Figure: Plotly 圖表
        """
        template = self.visualization_templates.get(strategy_id, {})

        if strategy_id == 'moving_average':
            return self._create_ma_visualization(data, template)
        elif strategy_id == 'rsi_strategy':
            return self._create_rsi_visualization(data, template)
        elif strategy_id == 'momentum_strategy':
            return self._create_momentum_visualization(data, template)
        else:
            # 預設簡單價格圖
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=data['Date'],
                y=data['Close'],
                mode='lines',
                name='價格'
            ))
            return fig

    def _create_ma_visualization(self, data: pd.DataFrame,
                               template: Dict[str, Any]) -> go.Figure:
        """創建移動平均線視覺化"""
        fig = go.Figure()

        # 價格線
        fig.add_trace(go.Scatter(
            x=data['Date'],
            y=data['Close'],
            mode='lines',
            name='股價',
            line=dict(color='blue', width=2)
        ))

        # 移動平均線
        if 'MA_10' in data.columns:
            fig.add_trace(go.Scatter(
                x=data['Date'],
                y=data['MA_10'],
                mode='lines',
                name='MA10',
                line=dict(color='red', dash='dash')
            ))

        if 'MA_30' in data.columns:
            fig.add_trace(go.Scatter(
                x=data['Date'],
                y=data['MA_30'],
                mode='lines',
                name='MA30',
                line=dict(color='green', dash='dash')
            ))

        # 交易信號
        if 'Signal' in data.columns:
            buy_signals = data[data['Signal'] == 1]
            sell_signals = data[data['Signal'] == -1]

            if not buy_signals.empty:
                fig.add_trace(go.Scatter(
                    x=buy_signals['Date'],
                    y=buy_signals['Close'],
                    mode='markers',
                    name='買入信號',
                    marker=dict(color='green', size=10, symbol='triangle-up')
                ))

            if not sell_signals.empty:
                fig.add_trace(go.Scatter(
                    x=sell_signals['Date'],
                    y=sell_signals['Close'],
                    mode='markers',
                    name='賣出信號',
                    marker=dict(color='red', size=10, symbol='triangle-down')
                ))

        fig.update_layout(
            title='移動平均線策略示範',
            xaxis_title='日期',
            yaxis_title='價格',
            height=500
        )

        return fig

    def _create_rsi_visualization(self, data: pd.DataFrame,
                                template: Dict[str, Any]) -> go.Figure:
        """創建 RSI 視覺化"""
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=('股價', 'RSI 指標'),
            row_heights=[0.7, 0.3]
        )

        # 價格圖
        fig.add_trace(
            go.Scatter(
                x=data['Date'],
                y=data['Close'],
                mode='lines',
                name='股價',
                line=dict(color='blue')
            ),
            row=1, col=1
        )

        # 交易信號
        if 'Signal' in data.columns:
            buy_signals = data[data['Signal'] == 1]
            sell_signals = data[data['Signal'] == -1]

            if not buy_signals.empty:
                fig.add_trace(
                    go.Scatter(
                        x=buy_signals['Date'],
                        y=buy_signals['Close'],
                        mode='markers',
                        name='買入信號',
                        marker=dict(color='green', size=8, symbol='triangle-up')
                    ),
                    row=1, col=1
                )

            if not sell_signals.empty:
                fig.add_trace(
                    go.Scatter(
                        x=sell_signals['Date'],
                        y=sell_signals['Close'],
                        mode='markers',
                        name='賣出信號',
                        marker=dict(color='red', size=8, symbol='triangle-down')
                    ),
                    row=1, col=1
                )

        # RSI 圖
        if 'RSI' in data.columns:
            fig.add_trace(
                go.Scatter(
                    x=data['Date'],
                    y=data['RSI'],
                    mode='lines',
                    name='RSI',
                    line=dict(color='purple')
                ),
                row=2, col=1
            )

            # 超買超賣線
            fig.add_hline(y=70, line_dash="dash", line_color="red",
                         annotation_text="超買線", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green",
                         annotation_text="超賣線", row=2, col=1)

        fig.update_layout(
            title='RSI 策略示範',
            height=600,
            showlegend=True
        )

        return fig

    def _create_momentum_visualization(self, data: pd.DataFrame,
                                     template: Dict[str, Any]) -> go.Figure:
        """創建動量策略視覺化"""
        # 計算動量指標
        data['Momentum'] = data['Close'].pct_change(20) * 100

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=('股價', '20日動量 (%)'),
            row_heights=[0.7, 0.3]
        )

        # 價格圖
        fig.add_trace(
            go.Scatter(
                x=data['Date'],
                y=data['Close'],
                mode='lines',
                name='股價',
                line=dict(color='blue')
            ),
            row=1, col=1
        )

        # 動量圖
        fig.add_trace(
            go.Scatter(
                x=data['Date'],
                y=data['Momentum'],
                mode='lines',
                name='動量',
                line=dict(color='orange')
            ),
            row=2, col=1
        )

        # 零軸線
        fig.add_hline(y=0, line_dash="dash", line_color="gray", row=2, col=1)

        fig.update_layout(
            title='動量策略示範',
            height=600,
            showlegend=True
        )

        return fig


def show_strategy_explainer() -> None:
    """
    顯示策略邏輯解釋器頁面

    提供策略邏輯的詳細解釋和視覺化功能，包括原理說明、
    參數影響分析、實例演示和比較分析。

    Side Effects:
        - 在 Streamlit 界面顯示策略解釋內容
        - 提供互動式策略學習體驗
    """
    st.title("🧠 策略邏輯解釋器")
    st.markdown("深入理解交易策略的運作原理，掌握策略的精髓！")

    # 初始化策略解釋器
    if 'strategy_explainer' not in st.session_state:
        st.session_state.strategy_explainer = StrategyExplainer()

    explainer = st.session_state.strategy_explainer

    # 策略選擇
    st.subheader("🎯 選擇策略")

    strategies = explainer.strategy_explanations
    strategy_names = {k: v['name'] for k, v in strategies.items()}

    selected_strategy = st.selectbox(
        "選擇要學習的策略",
        list(strategies.keys()),
        format_func=lambda x: strategy_names[x]
    )

    strategy_info = strategies[selected_strategy]

    # 策略基本資訊
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("策略類別", strategy_info['category'])
    with col2:
        st.metric("難度等級", strategy_info['difficulty'])
    with col3:
        st.metric("適用市場", "多種市場")

    # 策略原理說明
    st.subheader("📖 策略原理")
    st.markdown(strategy_info['principle'])

    # 優缺點分析
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("✅ 策略優勢")
        for advantage in strategy_info['advantages']:
            st.write(f"• {advantage}")

    with col2:
        st.subheader("⚠️ 策略限制")
        for disadvantage in strategy_info['disadvantages']:
            st.write(f"• {disadvantage}")

    # 參數說明
    st.subheader("⚙️ 關鍵參數")

    for param_name, param_info in strategy_info['parameters'].items():
        with st.expander(f"📊 {param_info['name']}", expanded=False):
            st.write(f"**說明**: {param_info['description']}")
            st.write(f"**典型範圍**: {param_info['typical_range']}")
            st.write(f"**影響**: {param_info['effect']}")

    # 策略視覺化演示
    st.subheader("📈 策略演示")

    # 生成演示資料
    demo_data = explainer.generate_strategy_demo_data(selected_strategy)

    # 參數調整（如果適用）
    if selected_strategy == 'moving_average':
        col1, col2 = st.columns(2)
        with col1:
            fast_period = st.slider("短期週期", 5, 30, 10)
        with col2:
            slow_period = st.slider("長期週期", 20, 100, 30)

        # 重新計算指標
        demo_data[f'MA_{fast_period}'] = demo_data['Close'].rolling(fast_period).mean()
        demo_data[f'MA_{slow_period}'] = demo_data['Close'].rolling(slow_period).mean()

        # 重新生成信號
        demo_data['Signal'] = 0
        demo_data.loc[demo_data[f'MA_{fast_period}'] > demo_data[f'MA_{slow_period}'], 'Signal'] = 1
        demo_data.loc[demo_data[f'MA_{fast_period}'] < demo_data[f'MA_{slow_period}'], 'Signal'] = -1

        # 更新列名以匹配視覺化函數
        demo_data['MA_10'] = demo_data[f'MA_{fast_period}']
        demo_data['MA_30'] = demo_data[f'MA_{slow_period}']

    elif selected_strategy == 'rsi_strategy':
        col1, col2, col3 = st.columns(3)
        with col1:
            rsi_period = st.slider("RSI 週期", 5, 30, 14)
        with col2:
            oversold = st.slider("超賣閾值", 10, 40, 30)
        with col3:
            overbought = st.slider("超買閾值", 60, 90, 70)

        # 重新計算 RSI
        delta = demo_data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / loss
        demo_data['RSI'] = 100 - (100 / (1 + rs))

        # 重新生成信號
        demo_data['Signal'] = 0
        demo_data.loc[demo_data['RSI'] < oversold, 'Signal'] = 1
        demo_data.loc[demo_data['RSI'] > overbought, 'Signal'] = -1

    # 顯示視覺化圖表
    fig = explainer.visualize_strategy_logic(selected_strategy, demo_data)
    st.plotly_chart(fig, use_container_width=True)

    # 信號統計
    if 'Signal' in demo_data.columns:
        st.subheader("📊 信號統計")

        signal_stats = demo_data['Signal'].value_counts()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("買入信號", signal_stats.get(1, 0))
        with col2:
            st.metric("賣出信號", signal_stats.get(-1, 0))
        with col3:
            st.metric("持有期間", signal_stats.get(0, 0))

        # 信號頻率分析
        total_signals = signal_stats.get(1, 0) + signal_stats.get(-1, 0)
        if total_signals > 0:
            signal_frequency = total_signals / len(demo_data) * 100
            st.write(f"**信號頻率**: {signal_frequency:.1f}% (每100個交易日約{signal_frequency:.0f}個信號)")

    # 適用條件
    st.subheader("🎯 最佳適用條件")

    for condition in strategy_info['best_conditions']:
        st.write(f"✓ {condition}")

    # 參數影響分析
    if selected_strategy in explainer.parameter_effects:
        st.subheader("🔧 參數影響分析")

        effects = explainer.parameter_effects[selected_strategy]

        for param_name, effect_info in effects.items():
            param_display_name = strategy_info['parameters'][param_name]['name']

            with st.expander(f"📈 {param_display_name} 的影響", expanded=False):
                col1, col2 = st.columns(2)

                with col1:
                    st.write("**增加參數值的效果:**")
                    st.write(effect_info['increase_effect'])

                with col2:
                    st.write("**減少參數值的效果:**")
                    st.write(effect_info['decrease_effect'])

                st.info(f"💡 **建議範圍**: {effect_info['optimal_range']}")

    # 策略比較
    st.subheader("⚖️ 策略比較")

    if st.checkbox("顯示策略比較表"):
        comparison_data = []

        for strategy_id, strategy_data in strategies.items():
            comparison_data.append({
                '策略名稱': strategy_data['name'],
                '類別': strategy_data['category'],
                '難度': strategy_data['difficulty'],
                '主要優勢': strategy_data['advantages'][0] if strategy_data['advantages'] else '',
                '主要限制': strategy_data['disadvantages'][0] if strategy_data['disadvantages'] else ''
            })

        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, use_container_width=True)

    # 實戰建議
    st.subheader("💡 實戰建議")

    with st.expander("📚 如何在實際交易中應用", expanded=False):
        if selected_strategy == 'moving_average':
            st.markdown("""
            ### 移動平均線策略實戰要點：

            1. **參數選擇**
               - 短期：5-20天，常用10天
               - 長期：20-50天，常用30天
               - 避免參數過於接近

            2. **信號確認**
               - 等待明確的交叉信號
               - 結合成交量確認
               - 避免在震盪區間頻繁交易

            3. **風險控制**
               - 設定3-5%的停損點
               - 控制單一部位不超過10%
               - 在趨勢不明時減少部位

            4. **市場選擇**
               - 選擇趨勢性較強的股票
               - 避免在橫盤整理時使用
               - 注意大盤環境影響
            """)

        elif selected_strategy == 'rsi_strategy':
            st.markdown("""
            ### RSI 策略實戰要點：

            1. **參數設定**
               - RSI週期：14天（標準）
               - 超賣：20-30
               - 超買：70-80

            2. **信號判斷**
               - 等待RSI從極值區域回歸
               - 結合價格行為確認
               - 注意背離信號

            3. **風險管理**
               - 在強趨勢中謹慎使用
               - 設定合理的停損點
               - 避免在單邊市場逆勢操作

            4. **最佳時機**
               - 震盪市場效果最佳
               - 結合支撐阻力位使用
               - 注意市場情緒指標
            """)

        elif selected_strategy == 'momentum_strategy':
            st.markdown("""
            ### 動量策略實戰要點：

            1. **選股標準**
               - 選擇流動性好的股票
               - 關注相對強度排名
               - 避免基本面惡化的股票

            2. **時機把握**
               - 在趨勢初期介入
               - 定期檢視持股表現
               - 及時汰換弱勢股票

            3. **風險控制**
               - 分散投資多檔股票
               - 設定較寬的停損點
               - 控制總體部位風險

            4. **市場環境**
               - 適合多頭市場
               - 注意市場轉向風險
               - 結合總體經濟指標
            """)

    # 學習測驗
    st.subheader("🎓 學習測驗")

    if st.button("開始測驗"):
        # 根據選擇的策略生成相應的測驗題目
        if selected_strategy == 'moving_average':
            st.write("**問題 1**: 移動平均線策略的買入信號是什麼？")
            answer1 = st.radio(
                "選擇答案",
                ["短期均線下穿長期均線", "短期均線上穿長期均線", "價格突破均線", "成交量放大"],
                key="q1"
            )

            if answer1 == "短期均線上穿長期均線":
                st.success("✅ 正確！短期均線上穿長期均線（金叉）是買入信號。")
            else:
                st.error("❌ 錯誤。正確答案是：短期均線上穿長期均線。")

        elif selected_strategy == 'rsi_strategy':
            st.write("**問題 1**: RSI 指標的數值範圍是多少？")
            answer1 = st.radio(
                "選擇答案",
                ["0-50", "0-100", "-100到100", "0-1"],
                key="q1"
            )

            if answer1 == "0-100":
                st.success("✅ 正確！RSI 指標的數值範圍是 0-100。")
            else:
                st.error("❌ 錯誤。正確答案是：0-100。")

    # 側邊欄：策略快速導航
    with st.sidebar:
        st.subheader("🧭 策略導航")

        for strategy_id, strategy_data in strategies.items():
            is_current = strategy_id == selected_strategy
            status = "👉" if is_current else "📊"

            if st.button(f"{status} {strategy_data['name']}", key=f"nav_{strategy_id}"):
                # 這裡可以添加跳轉邏輯
                st.info(f"切換到：{strategy_data['name']}")

        # 學習進度
        st.subheader("📈 學習進度")

        if 'strategy_learning_progress' not in st.session_state:
            st.session_state.strategy_learning_progress = set()

        total_strategies = len(strategies)
        learned_count = len(st.session_state.strategy_learning_progress)
        progress = learned_count / total_strategies

        st.progress(progress)
        st.write(f"已學習: {learned_count}/{total_strategies}")

        if st.button("標記為已學習"):
            st.session_state.strategy_learning_progress.add(selected_strategy)
            st.success("✅ 已標記為學習完成！")

        # 相關資源
        st.subheader("📚 相關資源")

        if st.button("📖 策略模板"):
            st.info("前往策略模板頁面...")

        if st.button("🎮 模擬交易"):
            st.info("前往模擬交易頁面...")

        if st.button("🔬 回測驗證"):
            st.info("前往回測頁面...")