"""
股票相關小工具

提供股價、市場狀態、K線圖等股票相關的儀表板小工具。
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging

from .base_widget import BaseWidget, WidgetSize

try:
    from src.ui.utils.websocket_manager import websocket_manager, DataType
except ImportError:
    # 如果導入失敗，創建模擬對象
    class MockWebSocketManager:
        def get_latest_data(self, data_type):
            return None

    class MockDataType:
        STOCK_PRICE = "stock_price"
        TRADING_STATUS = "trading_status"

    websocket_manager = MockWebSocketManager()
    DataType = MockDataType()

logger = logging.getLogger(__name__)


class StockPriceCard(BaseWidget):
    """股價卡片小工具"""

    def get_widget_type(self) -> str:
        return "stock_price_card"

    def get_default_title(self) -> str:
        return "股價監控"

    def get_default_size(self) -> Dict[str, int]:
        return WidgetSize.MEDIUM

    def render_content(self) -> None:
        """渲染股價卡片內容"""
        symbol = self.config.get("symbol", "2330.TW")

        # 獲取即時股價數據
        stock_data = websocket_manager.get_latest_data(DataType.STOCK_PRICE)

        if stock_data and symbol in stock_data:
            price_info = stock_data[symbol]

            # 顯示股價資訊
            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    label=symbol,
                    value=f"${price_info.get('price', 0):.2f}",
                    delta=f"{price_info.get('change_percent', 0):+.2f}%",
                )

            with col2:
                change = price_info.get("change", 0)
                change_color = (
                    self.theme["success"] if change >= 0 else self.theme["danger"]
                )

                st.markdown(
                    f"""
                <div style="text-align: center; padding: 10px;">
                    <div style="font-size: 24px; color: {change_color}; font-weight: bold;">
                        {change:+.2f}
                    </div>
                    <div style="font-size: 12px; color: {self.theme['text']};">
                        成交量: {price_info.get('volume', 0):,}
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )
        else:
            st.info(f"正在載入 {symbol} 股價數據...")

    def render_widget_settings(self) -> None:
        """渲染股價卡片特定設定"""
        # 股票代碼選擇
        symbol_options = ["2330.TW", "2317.TW", "2454.TW", "AAPL", "MSFT", "GOOGL"]
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

        if new_symbol != current_symbol:
            self.config["symbol"] = new_symbol

    def get_data_requirements(self) -> List[str]:
        return ["stock_price"]


class MarketStatusWidget(BaseWidget):
    """市場狀態小工具"""

    def get_widget_type(self) -> str:
        return "market_status"

    def get_default_title(self) -> str:
        return "市場狀態"

    def get_default_size(self) -> Dict[str, int]:
        return WidgetSize.SMALL

    def render_content(self) -> None:
        """渲染市場狀態內容"""
        # 獲取交易狀態數據
        trading_data = websocket_manager.get_latest_data(DataType.TRADING_STATUS)

        if trading_data:
            market_status = trading_data.get("market_status", "unknown")

            # 狀態圖標和顏色
            status_config = {
                "open": {"icon": "🟢", "text": "開盤", "color": self.theme["success"]},
                "closed": {"icon": "🔴", "text": "收盤", "color": self.theme["danger"]},
                "pre_market": {
                    "icon": "🟡",
                    "text": "盤前",
                    "color": self.theme["warning"],
                },
                "after_hours": {
                    "icon": "🟠",
                    "text": "盤後",
                    "color": self.theme["secondary"],
                },
            }

            config = status_config.get(
                market_status,
                {"icon": "⚪", "text": "未知", "color": self.theme["text"]},
            )

            # 顯示市場狀態
            st.markdown(
                f"""
            <div style="text-align: center; padding: 20px;">
                <div style="font-size: 48px; margin-bottom: 10px;">
                    {config['icon']}
                </div>
                <div style="font-size: 18px; color: {config['color']}; font-weight: bold;">
                    {config['text']}
                </div>
                <div style="font-size: 12px; color: {self.theme['text']}; margin-top: 5px;">
                    {datetime.now().strftime('%H:%M:%S')}
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            # 顯示其他交易資訊
            col1, col2 = st.columns(2)

            with col1:
                st.metric("活躍訂單", trading_data.get("active_orders", 0))

            with col2:
                st.metric("已執行", trading_data.get("executed_orders", 0))
        else:
            st.info("正在載入市場狀態...")

    def get_data_requirements(self) -> List[str]:
        return ["trading_status"]


class CandlestickWidget(BaseWidget):
    """K線圖小工具"""

    def get_widget_type(self) -> str:
        return "candlestick_chart"

    def get_default_title(self) -> str:
        return "K線圖"

    def get_default_size(self) -> Dict[str, int]:
        return WidgetSize.LARGE

    def render_content(self) -> None:
        """渲染K線圖內容"""
        symbol = self.config.get("symbol", "2330.TW")
        days = self.config.get("days", 30)
        show_volume = self.config.get("show_volume", True)

        # 生成模擬K線數據
        data = self._generate_candlestick_data(symbol, days)

        if not data.empty:
            # 創建K線圖
            fig = self._create_candlestick_chart(data, symbol, show_volume)

            # 顯示圖表
            st.plotly_chart(
                fig,
                use_container_width=True,
                config={"displayModeBar": False, "displaylogo": False},
            )
        else:
            st.error("無法載入K線數據")

    def _generate_candlestick_data(self, symbol: str, days: int) -> pd.DataFrame:
        """生成模擬K線數據

        Args:
            symbol: 股票代碼
            days: 天數

        Returns:
            K線數據 DataFrame
        """
        try:
            # 生成日期範圍
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days - 1)
            dates = pd.date_range(start=start_date, end=end_date, freq="D")

            # 生成價格數據
            np.random.seed(hash(symbol) % 2**32)
            base_price = 580.0 if symbol == "2330.TW" else np.random.uniform(100, 600)

            data = []
            current_price = base_price

            for date in dates:
                # 生成日內價格變動
                daily_return = np.random.normal(0, 0.02)
                open_price = current_price
                close_price = open_price * (1 + daily_return)

                # 生成高低價
                high_price = max(open_price, close_price) * (
                    1 + abs(np.random.normal(0, 0.01))
                )
                low_price = min(open_price, close_price) * (
                    1 - abs(np.random.normal(0, 0.01))
                )

                # 生成成交量
                volume = int(np.random.lognormal(15, 0.5))

                data.append(
                    {
                        "date": date,
                        "open": open_price,
                        "high": high_price,
                        "low": low_price,
                        "close": close_price,
                        "volume": volume,
                    }
                )

                current_price = close_price

            df = pd.DataFrame(data)
            df.set_index("date", inplace=True)
            return df

        except Exception as e:
            logger.error(f"生成K線數據失敗: {e}")
            return pd.DataFrame()

    def _create_candlestick_chart(
        self, data: pd.DataFrame, symbol: str, show_volume: bool
    ) -> go.Figure:
        """創建K線圖

        Args:
            data: K線數據
            symbol: 股票代碼
            show_volume: 是否顯示成交量

        Returns:
            Plotly 圖表
        """
        from plotly.subplots import make_subplots

        # 創建子圖
        rows = 2 if show_volume else 1
        fig = make_subplots(
            rows=rows,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            row_heights=[0.7, 0.3] if show_volume else [1.0],
        )

        # K線圖
        fig.add_trace(
            go.Candlestick(
                x=data.index,
                open=data["open"],
                high=data["high"],
                low=data["low"],
                close=data["close"],
                name=symbol,
                increasing_line_color=self.theme["success"],
                decreasing_line_color=self.theme["danger"],
            ),
            row=1,
            col=1,
        )

        # 成交量圖
        if show_volume:
            colors = [
                self.theme["success"] if close >= open else self.theme["danger"]
                for close, open in zip(data["close"], data["open"])
            ]

            fig.add_trace(
                go.Bar(
                    x=data.index,
                    y=data["volume"],
                    name="成交量",
                    marker_color=colors,
                    opacity=0.7,
                ),
                row=2,
                col=1,
            )

        # 更新佈局
        fig.update_layout(
            height=300,
            showlegend=False,
            xaxis_rangeslider_visible=False,
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            margin=dict(l=0, r=0, t=0, b=0),
        )

        # 更新軸
        fig.update_xaxes(gridcolor=self.theme["border"], showgrid=True, zeroline=False)

        fig.update_yaxes(gridcolor=self.theme["border"], showgrid=True, zeroline=False)

        return fig

    def render_widget_settings(self) -> None:
        """渲染K線圖特定設定"""
        # 股票代碼選擇
        symbol_options = ["2330.TW", "2317.TW", "2454.TW", "AAPL", "MSFT"]
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

        if new_symbol != current_symbol:
            self.config["symbol"] = new_symbol

        # 天數選擇
        days = st.slider(
            "顯示天數",
            min_value=7,
            max_value=90,
            value=self.config.get("days", 30),
            key=f"{self.widget_id}_days",
        )
        self.config["days"] = days

        # 成交量顯示
        show_volume = st.checkbox(
            "顯示成交量",
            value=self.config.get("show_volume", True),
            key=f"{self.widget_id}_volume",
        )
        self.config["show_volume"] = show_volume

    def get_data_requirements(self) -> List[str]:
        return ["stock_data"]
