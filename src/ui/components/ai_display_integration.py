# -*- coding: utf-8 -*-
"""
AI顯示邏輯整合組件

此模組整合AI顯示邏輯改進說明中的所有功能到數據檢視模組中，
提供統一的AI增強數據視覺化界面。

主要功能：
- 整合特徵計算器的多倍數參數調整
- 進階互動圖表功能
- AI自學擴充框架
- 自動交易訊號生成
- 用戶偏好學習和智能建議

Example:
    基本使用：
    ```python
    from src.ui.components.ai_display_integration import AIDisplayIntegration
    
    ai_display = AIDisplayIntegration()
    ai_display.show_enhanced_data_view(df, symbol)
    ```

Note:
    此模組專門整合AI顯示邏輯改進說明中的功能，
    確保與現有數據檢視模組的無縫整合和一致性。
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 設定日誌
logger = logging.getLogger(__name__)


class AIDisplayIntegration:
    """
    AI顯示邏輯整合組件
    
    整合AI顯示邏輯改進說明中的所有功能，提供統一的增強數據視覺化界面。
    """
    
    def __init__(self):
        """初始化AI顯示邏輯整合組件"""
        self.feature_calculator = None
        self.self_learning_agent = None
        self.interactive_charts = None
        
        # 初始化組件
        self._initialize_components()
        
        # 用戶偏好設定
        self.user_preferences = {
            'preferred_indicators': ['RSI', 'MACD'],
            'preferred_multipliers': [1.0],
            'preferred_timeframe': '最近90天',
            'enable_ai_signals': True,
            'chart_theme': 'plotly_white'
        }
        
        logger.info("✅ AI顯示邏輯整合組件初始化完成")
        
    def _initialize_components(self) -> None:
        """初始化相關組件"""
        try:
            # 導入整合特徵計算器
            from src.core.integrated_feature_calculator import IntegratedFeatureCalculator
            self.feature_calculator = IntegratedFeatureCalculator()
            logger.info("✅ 整合特徵計算器載入成功")
            
        except ImportError as e:
            logger.warning(f"整合特徵計算器載入失敗: {e}")
            
        try:
            # 導入AI自學代理
            from src.ai.self_learning_agent import SelfLearningAgent
            self.self_learning_agent = SelfLearningAgent
            logger.info("✅ AI自學代理載入成功")
            
        except ImportError as e:
            logger.warning(f"AI自學代理載入失敗: {e}")
            
        try:
            # 導入互動圖表組件
            from src.ui.components.interactive_charts import (
                agent_integrated_display, generate_trading_signals
            )
            self.interactive_charts = {
                'agent_integrated_display': agent_integrated_display,
                'generate_trading_signals': generate_trading_signals
            }
            logger.info("✅ 互動圖表組件載入成功")
            
        except ImportError as e:
            logger.warning(f"互動圖表組件載入失敗: {e}")
            
    def show_enhanced_data_view(self, df: pd.DataFrame, symbol: str) -> None:
        """
        顯示增強版數據檢視
        
        Args:
            df: 股票數據
            symbol: 股票代碼
        """
        if df.empty:
            st.warning("⚠️ 無可用數據")
            return
            
        st.write("### 🤖 AI增強數據檢視")
        
        # 功能選擇標籤頁
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 基礎圖表", 
            "🔧 技術分析", 
            "🤖 AI整合", 
            "⚙️ 個人化設定"
        ])
        
        with tab1:
            self._show_basic_enhanced_chart(df, symbol)
            
        with tab2:
            self._show_technical_analysis(df, symbol)
            
        with tab3:
            self._show_ai_integrated_features(df, symbol)
            
        with tab4:
            self._show_personalization_settings(df, symbol)
            
    def _show_basic_enhanced_chart(self, df: pd.DataFrame, symbol: str) -> None:
        """顯示基礎增強圖表"""
        st.write("#### 📈 增強版基礎圖表")
        
        # 圖表配置
        col1, col2, col3 = st.columns(3)
        
        with col1:
            time_frame = st.selectbox(
                "時間範圍",
                ["全部", "最近30天", "最近90天", "最近180天", "最近365天"],
                index=2,  # 默認90天
                key="basic_timeframe"
            )
            
        with col2:
            chart_style = st.selectbox(
                "圖表風格",
                ["蠟燭圖", "線圖", "面積圖"],
                index=0,
                key="basic_style"
            )
            
        with col3:
            show_volume = st.checkbox("顯示成交量", value=True, key="basic_volume")
            
        # 過濾數據
        filtered_df = self._filter_data_by_timeframe(df, time_frame)
        
        # 生成圖表
        fig = self._create_basic_chart(filtered_df, symbol, chart_style, show_volume)
        
        # 顯示圖表
        st.plotly_chart(fig, use_container_width=True)
        
        # 顯示基本統計信息
        self._show_basic_statistics(filtered_df, symbol)
        
    def _show_technical_analysis(self, df: pd.DataFrame, symbol: str) -> None:
        """顯示技術分析"""
        st.write("#### 🔧 進階技術分析")
        
        if not self.feature_calculator:
            st.warning("⚠️ 技術分析功能不可用")
            return
            
        # 技術指標配置
        col1, col2 = st.columns(2)
        
        with col1:
            selected_indicators = st.multiselect(
                "選擇技術指標",
                ["RSI", "MACD", "SMA", "EMA", "BBANDS", "STOCH"],
                default=self.user_preferences['preferred_indicators'],
                key="tech_indicators"
            )
            
        with col2:
            multipliers = st.multiselect(
                "參數倍數",
                [0.5, 1.0, 1.5, 2.0],
                default=self.user_preferences['preferred_multipliers'],
                key="tech_multipliers"
            )
            
        if selected_indicators and multipliers:
            # 計算技術指標
            try:
                indicators_data = self._calculate_enhanced_indicators(
                    df, selected_indicators, multipliers
                )
                
                # 顯示技術分析圖表
                fig = self._create_technical_chart(df, symbol, indicators_data)
                st.plotly_chart(fig, use_container_width=True)
                
                # 顯示指標解釋
                self._show_indicator_explanations(selected_indicators)
                
            except Exception as e:
                st.error(f"❌ 技術指標計算失敗: {e}")
                
    def _show_ai_integrated_features(self, df: pd.DataFrame, symbol: str) -> None:
        """顯示AI整合功能"""
        st.write("#### 🤖 AI智能分析")
        
        if not self.interactive_charts:
            st.warning("⚠️ AI功能不可用")
            return
            
        # AI功能配置
        col1, col2 = st.columns(2)
        
        with col1:
            enable_signals = st.checkbox(
                "啟用交易訊號", 
                value=self.user_preferences['enable_ai_signals'],
                key="ai_signals"
            )
            
            ai_indicators = st.multiselect(
                "AI分析指標",
                ["RSI", "MACD", "SMA", "EMA", "BBANDS"],
                default=["RSI", "MACD"],
                key="ai_indicators"
            )
            
        with col2:
            analysis_period = st.slider(
                "分析週期 (天)", 
                30, 365, 180,
                key="ai_period"
            )
            
            confidence_threshold = st.slider(
                "訊號信心閾值", 
                0.5, 1.0, 0.7,
                key="ai_confidence"
            )
            
        if st.button("🎯 生成AI分析", type="primary", key="generate_ai"):
            try:
                # 準備數據
                data_dict = {symbol: df.set_index('date')}
                
                # 設定日期範圍
                end_date = df['date'].max().strftime('%Y-%m-%d')
                start_date = (df['date'].max() - pd.Timedelta(days=analysis_period)).strftime('%Y-%m-%d')
                date_range = [start_date, end_date]
                
                # 生成AI整合圖表
                fig = self.interactive_charts['agent_integrated_display'](
                    stock_id=symbol,
                    data_dict=data_dict,
                    indicators=ai_indicators,
                    multipliers=[1.0],
                    date_range=date_range,
                    enable_ai_signals=enable_signals
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # 生成交易訊號
                if enable_signals:
                    signals = self._generate_ai_signals(df, ai_indicators, confidence_threshold)
                    self._display_trading_signals(signals)
                    
                # AI學習記錄
                self._record_ai_interaction(symbol, ai_indicators, analysis_period)
                
            except Exception as e:
                st.error(f"❌ AI分析生成失敗: {e}")
                logger.error(f"AI分析失敗: {e}")
                
    def _show_personalization_settings(self, df: pd.DataFrame, symbol: str) -> None:
        """顯示個人化設定"""
        st.write("#### ⚙️ 個人化設定")
        
        # 偏好設定
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**預設偏好**")
            
            default_indicators = st.multiselect(
                "預設技術指標",
                ["RSI", "MACD", "SMA", "EMA", "BBANDS", "STOCH"],
                default=self.user_preferences['preferred_indicators'],
                key="pref_indicators"
            )
            
            default_timeframe = st.selectbox(
                "預設時間範圍",
                ["最近30天", "最近90天", "最近180天", "最近365天"],
                index=1,
                key="pref_timeframe"
            )
            
        with col2:
            st.write("**顯示設定**")
            
            chart_theme = st.selectbox(
                "圖表主題",
                ["plotly", "plotly_white", "plotly_dark", "ggplot2"],
                index=1,
                key="pref_theme"
            )
            
            auto_ai_analysis = st.checkbox(
                "自動AI分析", 
                value=False,
                key="pref_auto_ai"
            )
            
        # 保存設定按鈕
        if st.button("💾 保存設定", key="save_preferences"):
            self.user_preferences.update({
                'preferred_indicators': default_indicators,
                'preferred_timeframe': default_timeframe,
                'chart_theme': chart_theme,
                'auto_ai_analysis': auto_ai_analysis
            })
            st.success("✅ 設定已保存")
            
        # AI學習狀態
        if self.self_learning_agent:
            self._show_ai_learning_status(symbol)
            
    def _filter_data_by_timeframe(self, df: pd.DataFrame, time_frame: str) -> pd.DataFrame:
        """根據時間框架過濾數據"""
        if time_frame == "全部":
            return df
            
        days_map = {
            "最近30天": 30,
            "最近90天": 90,
            "最近180天": 180,
            "最近365天": 365
        }
        
        days = days_map.get(time_frame, 90)
        cutoff_date = df['date'].max() - pd.Timedelta(days=days)
        return df[df['date'] >= cutoff_date]
        
    def _create_basic_chart(self, df: pd.DataFrame, symbol: str, 
                           chart_style: str, show_volume: bool) -> go.Figure:
        """創建基礎圖表"""
        rows = 2 if show_volume else 1
        subplot_titles = [f'{symbol} 股價走勢']
        if show_volume:
            subplot_titles.append('成交量')
            
        fig = make_subplots(
            rows=rows, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=subplot_titles,
            row_heights=[0.7, 0.3] if show_volume else [1.0]
        )
        
        # 根據圖表風格添加價格數據
        if chart_style == "蠟燭圖":
            fig.add_trace(
                go.Candlestick(
                    x=df['date'],
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name="股價"
                ),
                row=1, col=1
            )
        elif chart_style == "線圖":
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['close'],
                    mode='lines',
                    name='收盤價',
                    line=dict(color='blue', width=2)
                ),
                row=1, col=1
            )
        else:  # 面積圖
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['close'],
                    mode='lines',
                    fill='tonexty',
                    name='收盤價',
                    line=dict(color='blue', width=1)
                ),
                row=1, col=1
            )
            
        # 成交量圖
        if show_volume:
            fig.add_trace(
                go.Bar(
                    x=df['date'],
                    y=df['volume'],
                    name="成交量",
                    marker_color='rgba(158,202,225,0.8)'
                ),
                row=2, col=1
            )
            
        # 更新佈局
        fig.update_layout(
            title=f"{symbol} 股價分析圖表",
            xaxis_rangeslider_visible=False,
            height=600,
            template=self.user_preferences.get('chart_theme', 'plotly_white')
        )
        
        return fig

    def _calculate_enhanced_indicators(self, df: pd.DataFrame,
                                     indicators: List[str],
                                     multipliers: List[float]) -> Dict[str, pd.DataFrame]:
        """計算增強技術指標"""
        try:
            if not self.feature_calculator:
                raise ValueError("特徵計算器不可用")

            # 準備數據格式
            price_data = df.set_index('date')
            results = {}

            for indicator in indicators:
                for multiplier in multipliers:
                    key = f"{indicator}_{multiplier}x"

                    # 使用整合特徵計算器計算指標
                    if indicator == 'RSI':
                        period = int(14 * multiplier)
                        results[key] = self._calculate_rsi(price_data, period)
                    elif indicator == 'MACD':
                        fast = int(12 * multiplier)
                        slow = int(26 * multiplier)
                        signal = int(9 * multiplier)
                        results[key] = self._calculate_macd(price_data, fast, slow, signal)
                    elif indicator == 'SMA':
                        period = int(20 * multiplier)
                        results[key] = self._calculate_sma(price_data, period)
                    elif indicator == 'EMA':
                        period = int(20 * multiplier)
                        results[key] = self._calculate_ema(price_data, period)

            return results

        except Exception as e:
            logger.error(f"技術指標計算失敗: {e}")
            return {}

    def _calculate_rsi(self, price_data: pd.DataFrame, period: int = 14) -> pd.Series:
        """計算RSI指標"""
        if len(price_data) < period:
            return pd.Series(index=price_data.index)

        delta = price_data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_macd(self, price_data: pd.DataFrame,
                       fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """計算MACD指標"""
        if len(price_data) < slow:
            return pd.DataFrame(index=price_data.index)

        ema_fast = price_data['close'].ewm(span=fast).mean()
        ema_slow = price_data['close'].ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line

        return pd.DataFrame({
            'MACD': macd_line,
            'Signal': signal_line,
            'Histogram': histogram
        }, index=price_data.index)

    def _calculate_sma(self, price_data: pd.DataFrame, period: int = 20) -> pd.Series:
        """計算簡單移動平均線"""
        if len(price_data) < period:
            return pd.Series(index=price_data.index)
        return price_data['close'].rolling(window=period).mean()

    def _calculate_ema(self, price_data: pd.DataFrame, period: int = 20) -> pd.Series:
        """計算指數移動平均線"""
        return price_data['close'].ewm(span=period).mean()

    def _create_technical_chart(self, df: pd.DataFrame, symbol: str,
                               indicators_data: Dict[str, Any]) -> go.Figure:
        """創建技術分析圖表"""
        # 創建多子圖
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=[f'{symbol} 股價與移動平均線', 'RSI指標', 'MACD指標'],
            row_heights=[0.5, 0.25, 0.25]
        )

        # 主圖：K線圖
        fig.add_trace(
            go.Candlestick(
                x=df['date'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name="股價"
            ),
            row=1, col=1
        )

        # 添加移動平均線
        for key, data in indicators_data.items():
            if 'SMA' in key or 'EMA' in key:
                if isinstance(data, pd.Series):
                    fig.add_trace(
                        go.Scatter(
                            x=df['date'],
                            y=data,
                            mode='lines',
                            name=key,
                            line=dict(width=1)
                        ),
                        row=1, col=1
                    )

        # RSI指標
        for key, data in indicators_data.items():
            if 'RSI' in key and isinstance(data, pd.Series):
                fig.add_trace(
                    go.Scatter(
                        x=df['date'],
                        y=data,
                        mode='lines',
                        name=key,
                        line=dict(color='purple')
                    ),
                    row=2, col=1
                )

        # RSI超買超賣線
        fig.add_hline(y=70, line_dash="dash", line_color="red",
                     annotation_text="超買", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green",
                     annotation_text="超賣", row=2, col=1)

        # MACD指標
        for key, data in indicators_data.items():
            if 'MACD' in key and isinstance(data, pd.DataFrame):
                if 'MACD' in data.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df['date'],
                            y=data['MACD'],
                            mode='lines',
                            name=f'{key}_MACD',
                            line=dict(color='blue')
                        ),
                        row=3, col=1
                    )
                if 'Signal' in data.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df['date'],
                            y=data['Signal'],
                            mode='lines',
                            name=f'{key}_Signal',
                            line=dict(color='red')
                        ),
                        row=3, col=1
                    )

        # 更新佈局
        fig.update_layout(
            title=f"{symbol} 技術分析圖表",
            xaxis_rangeslider_visible=False,
            height=800,
            template=self.user_preferences.get('chart_theme', 'plotly_white')
        )

        # 更新軸標籤
        fig.update_yaxes(title_text="價格 (TWD)", row=1, col=1)
        fig.update_yaxes(title_text="RSI", row=2, col=1, range=[0, 100])
        fig.update_yaxes(title_text="MACD", row=3, col=1)
        fig.update_xaxes(title_text="日期", row=3, col=1)

        return fig

    def _show_basic_statistics(self, df: pd.DataFrame, symbol: str) -> None:
        """顯示基本統計信息"""
        if df.empty:
            return

        with st.expander("📊 基本統計信息"):
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("最新價格", f"{df['close'].iloc[-1]:.2f}")
                st.metric("最高價", f"{df['high'].max():.2f}")

            with col2:
                price_change = df['close'].iloc[-1] - df['close'].iloc[-2] if len(df) > 1 else 0
                change_pct = (price_change / df['close'].iloc[-2] * 100) if len(df) > 1 and df['close'].iloc[-2] != 0 else 0
                st.metric("價格變化", f"{price_change:.2f}", f"{change_pct:.2f}%")
                st.metric("最低價", f"{df['low'].min():.2f}")

            with col3:
                st.metric("平均成交量", f"{df['volume'].mean():.0f}")
                st.metric("總成交量", f"{df['volume'].sum():.0f}")

            with col4:
                volatility = df['close'].pct_change().std() * 100
                st.metric("波動率", f"{volatility:.2f}%")
                st.metric("數據天數", f"{len(df)}")

    def _show_indicator_explanations(self, indicators: List[str]) -> None:
        """顯示技術指標說明"""
        with st.expander("📚 技術指標說明"):
            for indicator in indicators:
                if indicator == 'RSI':
                    st.markdown("""
                    **RSI (相對強弱指標)**:
                    - RSI > 70: 超買區域，可能面臨回調
                    - RSI < 30: 超賣區域，可能出現反彈
                    - RSI 在 30-70 之間: 正常波動區間
                    """)
                elif indicator == 'MACD':
                    st.markdown("""
                    **MACD (指數平滑移動平均收斂發散)**:
                    - MACD線上穿信號線: 買入訊號
                    - MACD線下穿信號線: 賣出訊號
                    - 柱狀圖正值: 上升動能
                    - 柱狀圖負值: 下降動能
                    """)
                elif indicator in ['SMA', 'EMA']:
                    st.markdown(f"""
                    **{indicator} (移動平均線)**:
                    - 價格在移動平均線之上: 上升趨勢
                    - 價格在移動平均線之下: 下降趨勢
                    - 移動平均線斜率: 趨勢強度指標
                    """)

    def _generate_ai_signals(self, df: pd.DataFrame, indicators: List[str],
                           confidence_threshold: float) -> List[Dict[str, Any]]:
        """生成AI交易訊號"""
        signals = []

        try:
            if not self.interactive_charts:
                return signals

            # 使用互動圖表組件生成訊號
            trading_signals = self.interactive_charts['generate_trading_signals'](
                df.set_index('date'), indicators, confidence_threshold
            )

            # 轉換為顯示格式
            for signal in trading_signals:
                signals.append({
                    'date': signal.get('date', ''),
                    'type': signal.get('type', ''),
                    'confidence': signal.get('confidence', 0),
                    'reason': signal.get('reason', ''),
                    'price': signal.get('price', 0)
                })

        except Exception as e:
            logger.error(f"AI訊號生成失敗: {e}")

        return signals

    def _display_trading_signals(self, signals: List[Dict[str, Any]]) -> None:
        """顯示交易訊號"""
        if not signals:
            st.info("📊 當前無交易訊號")
            return

        st.write("#### 🎯 AI交易訊號")

        # 訊號統計
        buy_signals = [s for s in signals if s['type'] == 'buy']
        sell_signals = [s for s in signals if s['type'] == 'sell']

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("買入訊號", len(buy_signals))
        with col2:
            st.metric("賣出訊號", len(sell_signals))
        with col3:
            avg_confidence = sum(s['confidence'] for s in signals) / len(signals)
            st.metric("平均信心度", f"{avg_confidence:.2f}")

        # 訊號詳情
        for signal in signals[-5:]:  # 顯示最近5個訊號
            signal_type = "🟢 買入" if signal['type'] == 'buy' else "🔴 賣出"
            confidence_color = "green" if signal['confidence'] > 0.7 else "orange"

            st.markdown(f"""
            **{signal_type}訊號** - {signal['date']}
            - 價格: {signal['price']:.2f}
            - 信心度: <span style="color:{confidence_color}">{signal['confidence']:.2f}</span>
            - 原因: {signal['reason']}
            """, unsafe_allow_html=True)

    def _record_ai_interaction(self, symbol: str, indicators: List[str],
                             analysis_period: int) -> None:
        """記錄AI互動"""
        try:
            if not self.self_learning_agent:
                return

            agent = self.self_learning_agent(f"user_{symbol}")

            agent.record_user_interaction(
                interaction_type="ai_analysis",
                parameters={
                    "indicators": indicators,
                    "analysis_period": analysis_period,
                    "timestamp": datetime.now().isoformat()
                },
                result_quality=0.8  # 假設品質評分
            )

        except Exception as e:
            logger.error(f"AI互動記錄失敗: {e}")

    def _show_ai_learning_status(self, symbol: str) -> None:
        """顯示AI學習狀態"""
        try:
            if not self.self_learning_agent:
                return

            with st.expander("🧠 AI學習狀態"):
                agent = self.self_learning_agent(f"user_{symbol}")

                interaction_count = len(agent.user_interactions)
                st.write(f"互動記錄數: {interaction_count}")

                if interaction_count >= 5:
                    st.success("✅ AI已開始學習您的偏好")

                    # 顯示學習到的偏好
                    if hasattr(agent, 'learned_preferences'):
                        st.write("**學習到的偏好**:")
                        for key, value in agent.learned_preferences.items():
                            st.write(f"- {key}: {value}")
                else:
                    remaining = 5 - interaction_count
                    st.info(f"需要 {remaining} 次更多互動來啟動學習")

        except Exception as e:
            logger.warning(f"AI學習狀態顯示失敗: {e}")

    def get_user_preferences(self) -> Dict[str, Any]:
        """獲取用戶偏好設定"""
        return self.user_preferences.copy()

    def update_user_preferences(self, preferences: Dict[str, Any]) -> None:
        """更新用戶偏好設定"""
        self.user_preferences.update(preferences)
        logger.info("用戶偏好設定已更新")
