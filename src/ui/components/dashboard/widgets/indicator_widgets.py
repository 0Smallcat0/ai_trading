"""
技術指標小工具

提供 RSI、MACD、布林通道等技術指標的儀表板小工具。
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging

from .base_widget import BaseWidget, WidgetSize

logger = logging.getLogger(__name__)


class RSIIndicatorWidget(BaseWidget):
    """RSI 指標小工具"""

    def get_widget_type(self) -> str:
        return "rsi_indicator"

    def get_default_title(self) -> str:
        return "RSI 相對強弱指標"

    def get_default_size(self) -> Dict[str, int]:
        return WidgetSize.MEDIUM

    def render_content(self) -> None:
        """渲染 RSI 指標內容"""
        symbol = self.config.get("symbol", "2330.TW")
        period = self.config.get("period", 14)
        days = self.config.get("days", 30)

        # 生成股價數據並計算 RSI
        price_data = self._generate_price_data(symbol, days + period)
        rsi_data = self._calculate_rsi(price_data["close"], period)

        # 創建 RSI 圖表
        fig = self._create_rsi_chart(price_data.index[-days:], rsi_data[-days:])

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False, "displaylogo": False},
        )

        # 顯示當前 RSI 值和信號
        self._show_rsi_signal(rsi_data.iloc[-1] if not rsi_data.empty else 50)

    def _generate_price_data(self, symbol: str, days: int) -> pd.DataFrame:
        """生成股價數據"""
        np.random.seed(hash(symbol) % 2**32)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days - 1)
        dates = pd.date_range(start=start_date, end=end_date, freq="D")

        # 生成價格序列
        base_price = 580.0 if symbol == "2330.TW" else np.random.uniform(100, 600)
        returns = np.random.normal(0.001, 0.02, len(dates))

        prices = [base_price]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))

        return pd.DataFrame({"close": prices}, index=dates)

    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """計算 RSI 指標"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _create_rsi_chart(self, dates: pd.DatetimeIndex, rsi: pd.Series) -> go.Figure:
        """創建 RSI 圖表"""
        fig = go.Figure()

        # RSI 線
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=rsi,
                mode="lines",
                name="RSI",
                line=dict(color=self.theme["primary"], width=2),
            )
        )

        # 超買線 (70)
        fig.add_hline(
            y=70,
            line_dash="dash",
            line_color=self.theme["danger"],
            annotation_text="超買 (70)",
        )

        # 超賣線 (30)
        fig.add_hline(
            y=30,
            line_dash="dash",
            line_color=self.theme["success"],
            annotation_text="超賣 (30)",
        )

        # 中線 (50)
        fig.add_hline(y=50, line_dash="dot", line_color=self.theme["text"], opacity=0.5)

        fig.update_layout(
            height=250,
            xaxis_title="日期",
            yaxis_title="RSI",
            yaxis=dict(range=[0, 100]),
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False,
        )

        return fig

    def _show_rsi_signal(self, current_rsi: float) -> None:
        """顯示 RSI 信號"""
        col1, col2 = st.columns(2)

        with col1:
            st.metric("當前 RSI", f"{current_rsi:.1f}")

        with col2:
            if current_rsi >= 70:
                signal = "🔴 超買"
                color = self.theme["danger"]
            elif current_rsi <= 30:
                signal = "🟢 超賣"
                color = self.theme["success"]
            else:
                signal = "⚪ 中性"
                color = self.theme["text"]

            st.markdown(
                f"""
            <div style="text-align: center; color: {color}; font-weight: bold;">
                {signal}
            </div>
            """,
                unsafe_allow_html=True,
            )

    def render_widget_settings(self) -> None:
        """渲染 RSI 特定設定"""
        # 股票代碼
        symbol_options = ["2330.TW", "2317.TW", "2454.TW"]
        current_symbol = self.config.get("symbol", "2330.TW")

        new_symbol = st.selectbox(
            "股票代碼",
            symbol_options,
            index=(
                symbol_options.index(current_symbol)
                if current_symbol in symbol_options
                else 0
            ),
            key=f"{self.widget_id}_symbol",
        )
        self.config["symbol"] = new_symbol

        # RSI 週期
        period = st.slider(
            "RSI 週期",
            min_value=5,
            max_value=30,
            value=self.config.get("period", 14),
            key=f"{self.widget_id}_period",
        )
        self.config["period"] = period

        # 顯示天數
        days = st.slider(
            "顯示天數",
            min_value=10,
            max_value=60,
            value=self.config.get("days", 30),
            key=f"{self.widget_id}_days",
        )
        self.config["days"] = days


class MACDIndicatorWidget(BaseWidget):
    """MACD 指標小工具"""

    def get_widget_type(self) -> str:
        return "macd_indicator"

    def get_default_title(self) -> str:
        return "MACD 指標"

    def get_default_size(self) -> Dict[str, int]:
        return WidgetSize.LARGE

    def render_content(self) -> None:
        """渲染 MACD 指標內容"""
        symbol = self.config.get("symbol", "2330.TW")
        days = self.config.get("days", 60)

        # 生成股價數據並計算 MACD
        price_data = self._generate_price_data(symbol, days + 50)
        macd_data = self._calculate_macd(price_data["close"])

        # 創建 MACD 圖表
        fig = self._create_macd_chart(
            price_data.index[-days:],
            macd_data["macd"][-days:],
            macd_data["signal"][-days:],
            macd_data["histogram"][-days:],
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False, "displaylogo": False},
        )

        # 顯示 MACD 信號
        self._show_macd_signal(macd_data)

    def _generate_price_data(self, symbol: str, days: int) -> pd.DataFrame:
        """生成股價數據"""
        np.random.seed(hash(symbol) % 2**32)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days - 1)
        dates = pd.date_range(start=start_date, end=end_date, freq="D")

        base_price = 580.0 if symbol == "2330.TW" else np.random.uniform(100, 600)
        returns = np.random.normal(0.001, 0.02, len(dates))

        prices = [base_price]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))

        return pd.DataFrame({"close": prices}, index=dates)

    def _calculate_macd(
        self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Dict[str, pd.Series]:
        """計算 MACD 指標"""
        exp1 = prices.ewm(span=fast).mean()
        exp2 = prices.ewm(span=slow).mean()

        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal).mean()
        histogram = macd - signal_line

        return {"macd": macd, "signal": signal_line, "histogram": histogram}

    def _create_macd_chart(
        self,
        dates: pd.DatetimeIndex,
        macd: pd.Series,
        signal: pd.Series,
        histogram: pd.Series,
    ) -> go.Figure:
        """創建 MACD 圖表"""
        from plotly.subplots import make_subplots

        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            row_heights=[0.6, 0.4],
        )

        # MACD 線
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=macd,
                mode="lines",
                name="MACD",
                line=dict(color=self.theme["primary"], width=2),
            ),
            row=1,
            col=1,
        )

        # 信號線
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=signal,
                mode="lines",
                name="信號線",
                line=dict(color=self.theme["secondary"], width=2),
            ),
            row=1,
            col=1,
        )

        # 柱狀圖
        colors = [
            self.theme["success"] if x >= 0 else self.theme["danger"] for x in histogram
        ]

        fig.add_trace(
            go.Bar(
                x=dates,
                y=histogram,
                name="MACD 柱狀圖",
                marker_color=colors,
                opacity=0.7,
            ),
            row=2,
            col=1,
        )

        fig.update_layout(
            height=300,
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False,
        )

        return fig

    def _show_macd_signal(self, macd_data: Dict[str, pd.Series]) -> None:
        """顯示 MACD 信號"""
        if len(macd_data["macd"]) < 2:
            return

        current_macd = macd_data["macd"].iloc[-1]
        current_signal = macd_data["signal"].iloc[-1]
        prev_macd = macd_data["macd"].iloc[-2]
        prev_signal = macd_data["signal"].iloc[-2]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("MACD", f"{current_macd:.3f}")

        with col2:
            st.metric("信號線", f"{current_signal:.3f}")

        with col3:
            # 判斷交叉信號
            if prev_macd <= prev_signal and current_macd > current_signal:
                signal_text = "🟢 金叉"
                color = self.theme["success"]
            elif prev_macd >= prev_signal and current_macd < current_signal:
                signal_text = "🔴 死叉"
                color = self.theme["danger"]
            else:
                signal_text = "⚪ 無信號"
                color = self.theme["text"]

            st.markdown(
                f"""
            <div style="text-align: center; color: {color}; font-weight: bold;">
                {signal_text}
            </div>
            """,
                unsafe_allow_html=True,
            )

    def render_widget_settings(self) -> None:
        """渲染 MACD 特定設定"""
        # 股票代碼
        symbol_options = ["2330.TW", "2317.TW", "2454.TW"]
        current_symbol = self.config.get("symbol", "2330.TW")

        new_symbol = st.selectbox(
            "股票代碼",
            symbol_options,
            index=(
                symbol_options.index(current_symbol)
                if current_symbol in symbol_options
                else 0
            ),
            key=f"{self.widget_id}_symbol",
        )
        self.config["symbol"] = new_symbol

        # 顯示天數
        days = st.slider(
            "顯示天數",
            min_value=30,
            max_value=120,
            value=self.config.get("days", 60),
            key=f"{self.widget_id}_days",
        )
        self.config["days"] = days


class BollingerBandsWidget(BaseWidget):
    """布林通道小工具"""

    def get_widget_type(self) -> str:
        return "bollinger_bands"

    def get_default_title(self) -> str:
        return "布林通道"

    def get_default_size(self) -> Dict[str, int]:
        return WidgetSize.LARGE

    def render_content(self) -> None:
        """渲染布林通道內容"""
        symbol = self.config.get("symbol", "2330.TW")
        period = self.config.get("period", 20)
        std_dev = self.config.get("std_dev", 2)
        days = self.config.get("days", 60)

        # 生成股價數據並計算布林通道
        price_data = self._generate_price_data(symbol, days + period)
        bb_data = self._calculate_bollinger_bands(price_data["close"], period, std_dev)

        # 創建布林通道圖表
        fig = self._create_bb_chart(
            price_data.index[-days:],
            price_data["close"][-days:],
            bb_data["upper"][-days:],
            bb_data["middle"][-days:],
            bb_data["lower"][-days:],
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False, "displaylogo": False},
        )

        # 顯示布林通道信號
        self._show_bb_signal(price_data["close"].iloc[-1], bb_data)

    def _generate_price_data(self, symbol: str, days: int) -> pd.DataFrame:
        """生成股價數據"""
        np.random.seed(hash(symbol) % 2**32)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days - 1)
        dates = pd.date_range(start=start_date, end=end_date, freq="D")

        base_price = 580.0 if symbol == "2330.TW" else np.random.uniform(100, 600)
        returns = np.random.normal(0.001, 0.02, len(dates))

        prices = [base_price]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))

        return pd.DataFrame({"close": prices}, index=dates)

    def _calculate_bollinger_bands(
        self, prices: pd.Series, period: int = 20, std_dev: float = 2
    ) -> Dict[str, pd.Series]:
        """計算布林通道"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()

        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)

        return {"upper": upper, "middle": sma, "lower": lower}

    def _create_bb_chart(
        self,
        dates: pd.DatetimeIndex,
        prices: pd.Series,
        upper: pd.Series,
        middle: pd.Series,
        lower: pd.Series,
    ) -> go.Figure:
        """創建布林通道圖表"""
        fig = go.Figure()

        # 上軌
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=upper,
                mode="lines",
                name="上軌",
                line=dict(color=self.theme["danger"], dash="dash"),
            )
        )

        # 中軌
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=middle,
                mode="lines",
                name="中軌",
                line=dict(color=self.theme["primary"]),
            )
        )

        # 下軌
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=lower,
                mode="lines",
                name="下軌",
                line=dict(color=self.theme["success"], dash="dash"),
                fill="tonexty",
                fillcolor=f"rgba(0,100,80,0.1)",
            )
        )

        # 價格線
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=prices,
                mode="lines",
                name="收盤價",
                line=dict(color=self.theme["text"], width=2),
            )
        )

        fig.update_layout(
            height=300,
            xaxis_title="日期",
            yaxis_title="價格",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False,
        )

        return fig

    def _show_bb_signal(
        self, current_price: float, bb_data: Dict[str, pd.Series]
    ) -> None:
        """顯示布林通道信號"""
        if len(bb_data["upper"]) == 0:
            return

        upper = bb_data["upper"].iloc[-1]
        middle = bb_data["middle"].iloc[-1]
        lower = bb_data["lower"].iloc[-1]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("當前價格", f"${current_price:.2f}")

        with col2:
            bb_position = (current_price - lower) / (upper - lower) * 100
            st.metric("通道位置", f"{bb_position:.1f}%")

        with col3:
            if current_price >= upper:
                signal_text = "🔴 觸及上軌"
                color = self.theme["danger"]
            elif current_price <= lower:
                signal_text = "🟢 觸及下軌"
                color = self.theme["success"]
            else:
                signal_text = "⚪ 通道內"
                color = self.theme["text"]

            st.markdown(
                f"""
            <div style="text-align: center; color: {color}; font-weight: bold;">
                {signal_text}
            </div>
            """,
                unsafe_allow_html=True,
            )

    def render_widget_settings(self) -> None:
        """渲染布林通道特定設定"""
        # 股票代碼
        symbol_options = ["2330.TW", "2317.TW", "2454.TW"]
        current_symbol = self.config.get("symbol", "2330.TW")

        new_symbol = st.selectbox(
            "股票代碼",
            symbol_options,
            index=(
                symbol_options.index(current_symbol)
                if current_symbol in symbol_options
                else 0
            ),
            key=f"{self.widget_id}_symbol",
        )
        self.config["symbol"] = new_symbol

        # 移動平均週期
        period = st.slider(
            "移動平均週期",
            min_value=10,
            max_value=50,
            value=self.config.get("period", 20),
            key=f"{self.widget_id}_period",
        )
        self.config["period"] = period

        # 標準差倍數
        std_dev = st.slider(
            "標準差倍數",
            min_value=1.0,
            max_value=3.0,
            value=self.config.get("std_dev", 2.0),
            step=0.1,
            key=f"{self.widget_id}_std_dev",
        )
        self.config["std_dev"] = std_dev

        # 顯示天數
        days = st.slider(
            "顯示天數",
            min_value=30,
            max_value=120,
            value=self.config.get("days", 60),
            key=f"{self.widget_id}_days",
        )
        self.config["days"] = days
