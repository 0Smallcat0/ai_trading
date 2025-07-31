#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修復版進階技術分析頁面

提供完整的技術指標分析功能，包括：
- Williams %R、Stochastic、CCI、ATR 等進階指標
- 互動式圖表顯示
- 深色主題支持
- 錯誤處理和回退機制
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.subplots as sp
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def apply_dark_theme():
    """應用深色主題"""
    st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    .stSelectbox > div > div {
        background-color: #262730;
        color: #fafafa;
    }
    .stMultiSelect > div > div {
        background-color: #262730;
        color: #fafafa;
    }
    .stSlider > div > div > div {
        background-color: #262730;
    }
    .metric-card {
        background-color: #262730;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #404040;
    }
    </style>
    """, unsafe_allow_html=True)

def generate_sample_data(symbol: str = "2330.TW", days: int = 100) -> pd.DataFrame:
    """生成示例股票數據"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        np.random.seed(hash(symbol) % 10000)
        base_price = 100 + (hash(symbol) % 500)
        returns = np.random.normal(0.001, 0.02, len(date_range))
        prices = [base_price]
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        prices = np.array(prices)
        high = prices * (1 + np.random.uniform(0, 0.03, len(prices)))
        low = prices * (1 - np.random.uniform(0, 0.03, len(prices)))
        open_prices = np.roll(prices, 1)
        open_prices[0] = prices[0]
        volume = np.random.randint(1000000, 50000000, len(prices))
        
        df = pd.DataFrame({
            'date': date_range,
            'open': open_prices,
            'high': high,
            'low': low,
            'close': prices,
            'volume': volume
        })
        
        df.set_index('date', inplace=True)
        return df
        
    except Exception as e:
        logger.error(f"生成示例數據失敗: {e}")
        return pd.DataFrame()

def calculate_williams_r(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """計算 Williams %R"""
    try:
        highest_high = data['high'].rolling(window=period).max()
        lowest_low = data['low'].rolling(window=period).min()
        willr = ((highest_high - data['close']) / (highest_high - lowest_low)) * (-100)
        return willr
    except Exception as e:
        logger.error(f"Williams %R 計算失敗: {e}")
        return pd.Series(dtype=float)

def calculate_stochastic(data: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> tuple:
    """計算 Stochastic"""
    try:
        lowest_low = data['low'].rolling(window=k_period).min()
        highest_high = data['high'].rolling(window=k_period).max()
        k_percent = ((data['close'] - lowest_low) / (highest_high - lowest_low)) * 100
        k_series = k_percent.rolling(window=3).mean()
        d_series = k_series.rolling(window=d_period).mean()
        return k_series, d_series
    except Exception as e:
        logger.error(f"Stochastic 計算失敗: {e}")
        return pd.Series(dtype=float), pd.Series(dtype=float)

def calculate_cci(data: pd.DataFrame, period: int = 20) -> pd.Series:
    """計算 CCI"""
    try:
        typical_price = (data['high'] + data['low'] + data['close']) / 3
        sma_tp = typical_price.rolling(window=period).mean()
        mad = typical_price.rolling(window=period).apply(
            lambda x: np.mean(np.abs(x - x.mean()))
        )
        cci = (typical_price - sma_tp) / (0.015 * mad)
        return cci
    except Exception as e:
        logger.error(f"CCI 計算失敗: {e}")
        return pd.Series(dtype=float)

def calculate_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """計算 ATR"""
    try:
        high_low = data['high'] - data['low']
        high_close_prev = np.abs(data['high'] - data['close'].shift(1))
        low_close_prev = np.abs(data['low'] - data['close'].shift(1))
        true_range = np.maximum(high_low, np.maximum(high_close_prev, low_close_prev))
        atr = pd.Series(true_range).rolling(window=period).mean()
        atr.index = data.index
        return atr
    except Exception as e:
        logger.error(f"ATR 計算失敗: {e}")
        return pd.Series(dtype=float)

def create_indicator_chart(data: pd.DataFrame, indicator_data: pd.Series, 
                          indicator_name: str, overbought: float = None, 
                          oversold: float = None) -> go.Figure:
    """創建技術指標圖表"""
    try:
        fig = sp.make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=['價格走勢', f'{indicator_name}'],
            row_heights=[0.7, 0.3]
        )
        
        # 價格 K 線圖
        fig.add_trace(
            go.Candlestick(
                x=data.index,
                open=data['open'],
                high=data['high'],
                low=data['low'],
                close=data['close'],
                name='價格',
                increasing_line_color='#00ff88',
                decreasing_line_color='#ff4444'
            ),
            row=1, col=1
        )
        
        # 指標線圖
        fig.add_trace(
            go.Scatter(
                x=indicator_data.index,
                y=indicator_data,
                mode='lines',
                name=indicator_name,
                line=dict(color='#1f77b4', width=2)
            ),
            row=2, col=1
        )
        
        # 添加超買超賣線
        if overbought is not None:
            fig.add_hline(y=overbought, line_dash="dash", line_color='#ff6b6b', 
                         annotation_text=f"超買 ({overbought})", row=2, col=1)
        if oversold is not None:
            fig.add_hline(y=oversold, line_dash="dash", line_color='#4ecdc4', 
                         annotation_text=f"超賣 ({oversold})", row=2, col=1)
        
        fig.update_layout(
            title=f"{indicator_name} 技術指標分析",
            template="plotly_dark",
            height=600,
            showlegend=True,
            xaxis_rangeslider_visible=False
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"創建 {indicator_name} 圖表失敗: {e}")
        return go.Figure()

def create_indicator_tooltip(indicator_name: str) -> str:
    """創建指標懸停提示"""
    tooltips = {
        "Williams %R": "威廉指標：動量指標，範圍 -100 到 0。超買 -20 以上，超賣 -80 以下。",
        "Stochastic": "隨機指標：%K 和 %D 雙線，範圍 0-100。超買 80 以上，超賣 20 以下。",
        "CCI": "商品通道指數：測量價格偏離程度。超買 +100 以上，超賣 -100 以下。",
        "ATR": "平均真實範圍：波動性指標，用於設置止損和倉位管理。"
    }
    return tooltips.get(indicator_name, "技術指標")

def show():
    """主顯示函數"""
    # 應用深色主題
    apply_dark_theme()
    
    st.title("📈 進階技術指標分析")
    st.markdown("---")
    
    # 側邊欄設置
    with st.sidebar:
        st.subheader("⚙️ 分析設置")
        
        symbol = st.selectbox(
            "選擇股票",
            ["2330.TW", "2317.TW", "2454.TW", "AAPL", "TSLA"],
            help="選擇要分析的股票"
        )
        
        days = st.slider("數據天數", 50, 300, 150, help="選擇分析的數據天數")
        
        st.subheader("📈 指標選擇")

        # 創建指標選項，每個都有懸停提示
        indicator_options = {
            "Williams %R": "威廉指標：動量指標，範圍 -100 到 0。超買 -20 以上，超賣 -80 以下。",
            "Stochastic": "隨機指標：%K 和 %D 雙線，範圍 0-100。超買 80 以上，超賣 20 以下。",
            "CCI": "商品通道指數：測量價格偏離程度。超買 +100 以上，超賣 -100 以下。",
            "ATR": "平均真實範圍：波動性指標，用於設置止損和倉位管理。"
        }

        selected_indicators = st.multiselect(
            "選擇要分析的指標",
            options=list(indicator_options.keys()),
            default=["Williams %R", "Stochastic"],
            help="選擇一個或多個技術指標進行分析。將鼠標懸停在指標名稱上查看說明。"
        )

        # 顯示選中指標的簡要說明
        if selected_indicators:
            st.markdown("**已選指標說明：**")
            for indicator in selected_indicators:
                st.markdown(f"• **{indicator}**: {indicator_options[indicator]}")

        # 參數設置
        if selected_indicators:
            st.subheader("⚙️ 參數設置")

            params = {}

            # 使用 expander 來組織參數設置
            if "Williams %R" in selected_indicators:
                with st.expander("📊 Williams %R 參數", expanded=True):
                    params['willr_period'] = st.slider(
                        "計算週期", 5, 50, 14,
                        help="用於計算 Williams %R 的週期數。較短週期更敏感，較長週期更穩定。"
                    )
                    st.info(f"當前設置：{params['willr_period']} 天週期")

            if "Stochastic" in selected_indicators:
                with st.expander("📈 Stochastic 參數", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        params['stoch_k'] = st.slider(
                            "K 週期", 5, 30, 14,
                            help="%K 線的計算週期"
                        )
                    with col2:
                        params['stoch_d'] = st.slider(
                            "D 週期", 2, 10, 3,
                            help="%D 線的平滑週期"
                        )
                    st.info(f"當前設置：K={params['stoch_k']} 天，D={params['stoch_d']} 天")

            if "CCI" in selected_indicators:
                with st.expander("📉 CCI 參數", expanded=True):
                    params['cci_period'] = st.slider(
                        "計算週期", 10, 50, 20,
                        help="CCI 的計算週期。標準設置為 20 天。"
                    )
                    st.info(f"當前設置：{params['cci_period']} 天週期")

            if "ATR" in selected_indicators:
                with st.expander("📊 ATR 參數", expanded=True):
                    params['atr_period'] = st.slider(
                        "計算週期", 5, 30, 14,
                        help="ATR 的計算週期。標準設置為 14 天。"
                    )
                    # ATR 倍數設置
                    params['atr_multiplier'] = st.slider(
                        "止損倍數", 1.0, 4.0, 2.0, 0.5,
                        help="用於計算止損距離的 ATR 倍數"
                    )
                    st.info(f"當前設置：{params['atr_period']} 天週期，{params['atr_multiplier']}x 止損倍數")
        else:
            params = {}
    
    # 主要內容
    if not selected_indicators:
        st.info("👈 請在左側選擇要分析的技術指標")
        st.subheader("📊 可用指標")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**動量指標:**\n- Williams %R\n- Stochastic\n- CCI")
        with col2:
            st.markdown("**波動性指標:**\n- ATR")
        return
    
    # 生成數據
    with st.spinner("📊 生成股票數據..."):
        data = generate_sample_data(symbol, days)
        if data.empty:
            st.error("❌ 數據生成失敗")
            return
    
    # 創建標籤頁
    tab1, tab2 = st.tabs(["📈 指標圖表", "📚 使用說明"])
    
    with tab1:
        st.subheader(f"📈 {symbol} 技術指標分析")
        
        for indicator in selected_indicators:
            with st.expander(f"📊 {indicator} 分析", expanded=True):

                try:
                    if indicator == "Williams %R":
                        with st.spinner(f"計算 {indicator}..."):
                            willr = calculate_williams_r(data, params.get('willr_period', 14))
                            if not willr.empty:
                                fig = create_indicator_chart(data, willr, "Williams %R", -20, -80)
                                st.plotly_chart(fig, use_container_width=True)

                                # 指標數值和信號分析
                                current_value = willr.iloc[-1]
                                col1, col2, col3, col4 = st.columns(4)

                                with col1:
                                    st.metric("當前值", f"{current_value:.2f}")

                                with col2:
                                    if current_value > -20:
                                        signal = "超買"
                                        signal_color = "🔴"
                                    elif current_value < -80:
                                        signal = "超賣"
                                        signal_color = "🟢"
                                    else:
                                        signal = "中性"
                                        signal_color = "🟡"
                                    st.metric("信號", f"{signal_color} {signal}")

                                with col3:
                                    trend = "看跌" if current_value > -20 else "看漲" if current_value < -80 else "觀望"
                                    st.metric("建議", trend)

                                with col4:
                                    # 計算信號強度
                                    if current_value > -20:
                                        strength = min(100, abs(current_value + 20) * 5)
                                    elif current_value < -80:
                                        strength = min(100, abs(current_value + 80) * 5)
                                    else:
                                        strength = 0
                                    st.metric("信號強度", f"{strength:.0f}%")
                            else:
                                st.warning("⚠️ Williams %R 計算失敗，數據不足")
                    
                    elif indicator == "Stochastic":
                        with st.spinner(f"計算 {indicator}..."):
                            k_values, d_values = calculate_stochastic(
                                data, params.get('stoch_k', 14), params.get('stoch_d', 3)
                            )
                            if not k_values.empty and not d_values.empty:
                                # 創建 Stochastic 圖表
                                fig = sp.make_subplots(
                                    rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                                    subplot_titles=['價格走勢', 'Stochastic Oscillator'],
                                    row_heights=[0.7, 0.3]
                                )

                                # 價格 K 線圖
                                fig.add_trace(
                                    go.Candlestick(
                                        x=data.index, open=data['open'], high=data['high'],
                                        low=data['low'], close=data['close'], name='價格',
                                        increasing_line_color='#00ff88',
                                        decreasing_line_color='#ff4444'
                                    ), row=1, col=1
                                )

                                # %K 和 %D 線
                                fig.add_trace(
                                    go.Scatter(
                                        x=k_values.index, y=k_values, name='%K',
                                        line=dict(color='#1f77b4', width=2)
                                    ), row=2, col=1
                                )
                                fig.add_trace(
                                    go.Scatter(
                                        x=d_values.index, y=d_values, name='%D',
                                        line=dict(color='#ff7f0e', width=2)
                                    ), row=2, col=1
                                )

                                # 超買超賣線
                                fig.add_hline(
                                    y=80, line_dash="dash", line_color='#ff6b6b',
                                    annotation_text="超買 (80)", row=2, col=1
                                )
                                fig.add_hline(
                                    y=20, line_dash="dash", line_color='#4ecdc4',
                                    annotation_text="超賣 (20)", row=2, col=1
                                )
                                fig.add_hline(
                                    y=50, line_dash="dot", line_color='#888888',
                                    annotation_text="中線 (50)", row=2, col=1
                                )

                                fig.update_layout(
                                    title="Stochastic Oscillator 分析",
                                    template="plotly_dark", height=600,
                                    xaxis_rangeslider_visible=False
                                )
                                st.plotly_chart(fig, use_container_width=True)

                                # 指標數值和信號分析
                                current_k = k_values.iloc[-1]
                                current_d = d_values.iloc[-1]

                                col1, col2, col3, col4 = st.columns(4)

                                with col1:
                                    st.metric("當前 %K", f"{current_k:.2f}")

                                with col2:
                                    st.metric("當前 %D", f"{current_d:.2f}")

                                with col3:
                                    if current_k > current_d:
                                        cross_signal = "🟢 金叉"
                                    else:
                                        cross_signal = "🔴 死叉"
                                    st.metric("K/D 關係", cross_signal)

                                with col4:
                                    if current_k > 80 or current_d > 80:
                                        zone = "🔴 超買"
                                    elif current_k < 20 or current_d < 20:
                                        zone = "🟢 超賣"
                                    else:
                                        zone = "🟡 中性"
                                    st.metric("區域", zone)
                            else:
                                st.warning("⚠️ Stochastic 計算失敗，數據不足")
                    
                    elif indicator == "CCI":
                        cci = calculate_cci(data, params.get('cci_period', 20))
                        if not cci.empty:
                            fig = create_indicator_chart(data, cci, "CCI", 100, -100)
                            st.plotly_chart(fig, use_container_width=True)
                    
                    elif indicator == "ATR":
                        atr = calculate_atr(data, params.get('atr_period', 14))
                        if not atr.empty:
                            fig = create_indicator_chart(data, atr, "ATR")
                            st.plotly_chart(fig, use_container_width=True)
                
                except Exception as e:
                    st.error(f"❌ {indicator} 分析失敗: {e}")
    
    with tab2:
        st.subheader("📚 技術指標使用說明")
        st.info("指標說明功能已移除")

if __name__ == "__main__":
    show()
