"""
實用工具小工具

提供文字說明、警報面板、交易活動等實用功能的小工具。
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging

from .base_widget import BaseWidget, WidgetSize

logger = logging.getLogger(__name__)


class TextWidget(BaseWidget):
    """文字說明小工具"""

    def get_widget_type(self) -> str:
        return "text_widget"

    def get_default_title(self) -> str:
        return "文字說明"

    def get_default_size(self) -> Dict[str, int]:
        return WidgetSize.MEDIUM

    def render_content(self) -> None:
        """渲染文字內容"""
        content = self.config.get("content", "請在設定中編輯文字內容...")
        content_type = self.config.get("content_type", "markdown")

        if content_type == "markdown":
            st.markdown(content)
        elif content_type == "html":
            st.markdown(content, unsafe_allow_html=True)
        else:
            st.text(content)

    def render_widget_settings(self) -> None:
        """渲染文字小工具特定設定"""
        # 內容類型選擇
        content_type_options = {
            "markdown": "Markdown",
            "html": "HTML",
            "plain": "純文字",
        }

        current_type = self.config.get("content_type", "markdown")

        new_type = st.selectbox(
            "內容類型",
            list(content_type_options.keys()),
            format_func=lambda x: content_type_options[x],
            index=list(content_type_options.keys()).index(current_type),
            key=f"{self.widget_id}_content_type",
        )
        self.config["content_type"] = new_type

        # 文字內容編輯
        content = st.text_area(
            "內容",
            value=self.config.get("content", ""),
            height=150,
            key=f"{self.widget_id}_content",
        )
        self.config["content"] = content


class AlertsPanelWidget(BaseWidget):
    """警報面板小工具"""

    def get_widget_type(self) -> str:
        return "alerts_panel"

    def get_default_title(self) -> str:
        return "系統警報"

    def get_default_size(self) -> Dict[str, int]:
        return WidgetSize.FULL_WIDTH

    def render_content(self) -> None:
        """渲染警報面板內容"""
        max_alerts = self.config.get("max_alerts", 5)
        show_resolved = self.config.get("show_resolved", False)

        # 生成模擬警報數據
        alerts = self._generate_alerts_data(max_alerts, show_resolved)

        if alerts:
            for alert in alerts:
                self._render_alert_item(alert)
        else:
            st.info("目前沒有警報")

    def _generate_alerts_data(
        self, max_alerts: int, show_resolved: bool
    ) -> List[Dict[str, Any]]:
        """生成模擬警報數據"""
        np.random.seed(42)

        alert_types = [
            {"type": "price", "icon": "📈", "color": "warning"},
            {"type": "volume", "icon": "📊", "color": "info"},
            {"type": "risk", "icon": "⚠️", "color": "danger"},
            {"type": "system", "icon": "🔧", "color": "secondary"},
        ]

        alerts = []
        for i in range(max_alerts):
            alert_type = np.random.choice(alert_types)
            status = (
                "resolved" if show_resolved and np.random.random() > 0.7 else "active"
            )

            alert = {
                "id": f"alert_{i}",
                "type": alert_type["type"],
                "icon": alert_type["icon"],
                "color": alert_type["color"],
                "status": status,
                "title": self._get_alert_title(alert_type["type"]),
                "message": self._get_alert_message(alert_type["type"]),
                "timestamp": datetime.now()
                - timedelta(minutes=np.random.randint(1, 1440)),
                "severity": np.random.choice(["low", "medium", "high"]),
            }
            alerts.append(alert)

        # 按時間排序
        alerts.sort(key=lambda x: x["timestamp"], reverse=True)
        return alerts

    def _get_alert_title(self, alert_type: str) -> str:
        """獲取警報標題"""
        titles = {
            "price": "價格突破警報",
            "volume": "成交量異常",
            "risk": "風險控制警報",
            "system": "系統狀態警報",
        }
        return titles.get(alert_type, "未知警報")

    def _get_alert_message(self, alert_type: str) -> str:
        """獲取警報訊息"""
        messages = {
            "price": "2330.TW 突破阻力位 $590",
            "volume": "2317.TW 成交量異常放大 (+150%)",
            "risk": "投資組合風險值超過設定閾值",
            "system": "數據連接延遲，正在重新連接",
        }
        return messages.get(alert_type, "未知警報訊息")

    def _render_alert_item(self, alert: Dict[str, Any]) -> None:
        """渲染單個警報項目"""
        # 設定顏色
        color_map = {
            "danger": self.theme["danger"],
            "warning": self.theme["warning"],
            "info": self.theme["primary"],
            "secondary": self.theme["secondary"],
        }

        severity_colors = {
            "high": self.theme["danger"],
            "medium": self.theme["warning"],
            "low": self.theme["success"],
        }

        alert_color = color_map.get(alert["color"], self.theme["text"])
        severity_color = severity_colors.get(alert["severity"], self.theme["text"])

        # 狀態樣式
        opacity = "0.6" if alert["status"] == "resolved" else "1.0"

        # 渲染警報
        st.markdown(
            f"""
        <div style="
            border-left: 4px solid {alert_color};
            background-color: {self.theme['background']};
            padding: 12px;
            margin: 8px 0;
            border-radius: 4px;
            opacity: {opacity};
            box-shadow: {self.theme['shadow']};
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="display: flex; align-items: center;">
                    <span style="font-size: 20px; margin-right: 8px;">{alert['icon']}</span>
                    <div>
                        <strong style="color: {self.theme['text']};">{alert['title']}</strong>
                        <div style="color: {severity_color}; font-size: 12px; font-weight: bold;">
                            {alert['severity'].upper()}
                        </div>
                    </div>
                </div>
                <div style="text-align: right; font-size: 12px; color: {self.theme['text']};">
                    {alert['timestamp'].strftime('%H:%M')}
                    <div style="color: {alert_color};">
                        {alert['status'].upper()}
                    </div>
                </div>
            </div>
            <div style="margin-top: 8px; color: {self.theme['text']};">
                {alert['message']}
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    def render_widget_settings(self) -> None:
        """渲染警報面板特定設定"""
        # 最大警報數量
        max_alerts = st.slider(
            "最大顯示警報數",
            min_value=3,
            max_value=20,
            value=self.config.get("max_alerts", 5),
            key=f"{self.widget_id}_max_alerts",
        )
        self.config["max_alerts"] = max_alerts

        # 顯示已解決警報
        show_resolved = st.checkbox(
            "顯示已解決警報",
            value=self.config.get("show_resolved", False),
            key=f"{self.widget_id}_show_resolved",
        )
        self.config["show_resolved"] = show_resolved


class TradingActivityWidget(BaseWidget):
    """交易活動小工具"""

    def get_widget_type(self) -> str:
        return "trading_activity"

    def get_default_title(self) -> str:
        return "交易活動"

    def get_default_size(self) -> Dict[str, int]:
        return WidgetSize.MEDIUM

    def render_content(self) -> None:
        """渲染交易活動內容"""
        activity_type = self.config.get("activity_type", "recent_trades")
        max_items = self.config.get("max_items", 10)

        if activity_type == "recent_trades":
            self._render_recent_trades(max_items)
        elif activity_type == "pending_orders":
            self._render_pending_orders(max_items)
        else:
            self._render_trade_summary()

    def _render_recent_trades(self, max_items: int) -> None:
        """渲染最近交易"""
        trades = self._generate_recent_trades(max_items)

        if trades:
            for trade in trades:
                col1, col2, col3 = st.columns([2, 1, 1])

                with col1:
                    action_color = (
                        self.theme["success"]
                        if trade["action"] == "買入"
                        else self.theme["danger"]
                    )
                    st.markdown(
                        f"""
                    <div style="color: {action_color}; font-weight: bold;">
                        {trade['action']} {trade['symbol']}
                    </div>
                    <div style="font-size: 12px; color: {self.theme['text']};">
                        {trade['timestamp'].strftime('%H:%M:%S')}
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                with col2:
                    st.text(f"{trade['quantity']} 股")

                with col3:
                    st.text(f"${trade['price']:.2f}")
        else:
            st.info("暫無交易記錄")

    def _render_pending_orders(self, max_items: int) -> None:
        """渲染待執行訂單"""
        orders = self._generate_pending_orders(max_items)

        if orders:
            for order in orders:
                col1, col2, col3 = st.columns([2, 1, 1])

                with col1:
                    order_color = (
                        self.theme["primary"]
                        if order["type"] == "限價"
                        else self.theme["secondary"]
                    )
                    st.markdown(
                        f"""
                    <div style="color: {order_color}; font-weight: bold;">
                        {order['action']} {order['symbol']}
                    </div>
                    <div style="font-size: 12px; color: {self.theme['text']};">
                        {order['type']}單
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                with col2:
                    st.text(f"{order['quantity']} 股")

                with col3:
                    st.text(f"${order['price']:.2f}")
        else:
            st.info("暫無待執行訂單")

    def _render_trade_summary(self) -> None:
        """渲染交易摘要"""
        summary = self._generate_trade_summary()

        col1, col2 = st.columns(2)

        with col1:
            st.metric("今日交易", f"{summary['today_trades']} 筆")
            st.metric("買入金額", f"${summary['buy_amount']:,.0f}")

        with col2:
            st.metric("成功率", f"{summary['success_rate']:.1f}%")
            st.metric("賣出金額", f"${summary['sell_amount']:,.0f}")

    def _generate_recent_trades(self, max_items: int) -> List[Dict[str, Any]]:
        """生成最近交易數據"""
        np.random.seed(42)

        symbols = ["2330.TW", "2317.TW", "2454.TW", "2412.TW"]
        actions = ["買入", "賣出"]

        trades = []
        for i in range(max_items):
            trade = {
                "symbol": np.random.choice(symbols),
                "action": np.random.choice(actions),
                "quantity": np.random.randint(100, 2000),
                "price": np.random.uniform(50, 600),
                "timestamp": datetime.now()
                - timedelta(minutes=np.random.randint(1, 480)),
            }
            trades.append(trade)

        trades.sort(key=lambda x: x["timestamp"], reverse=True)
        return trades

    def _generate_pending_orders(self, max_items: int) -> List[Dict[str, Any]]:
        """生成待執行訂單數據"""
        np.random.seed(43)

        symbols = ["2330.TW", "2317.TW", "2454.TW"]
        actions = ["買入", "賣出"]
        order_types = ["限價", "市價"]

        orders = []
        for i in range(max_items):
            order = {
                "symbol": np.random.choice(symbols),
                "action": np.random.choice(actions),
                "type": np.random.choice(order_types),
                "quantity": np.random.randint(100, 1000),
                "price": np.random.uniform(50, 600),
            }
            orders.append(order)

        return orders

    def _generate_trade_summary(self) -> Dict[str, Any]:
        """生成交易摘要數據"""
        np.random.seed(44)

        return {
            "today_trades": np.random.randint(5, 25),
            "success_rate": np.random.uniform(60, 85),
            "buy_amount": np.random.uniform(100000, 500000),
            "sell_amount": np.random.uniform(80000, 450000),
        }

    def render_widget_settings(self) -> None:
        """渲染交易活動特定設定"""
        # 活動類型選擇
        activity_options = {
            "recent_trades": "最近交易",
            "pending_orders": "待執行訂單",
            "trade_summary": "交易摘要",
        }

        current_activity = self.config.get("activity_type", "recent_trades")

        new_activity = st.selectbox(
            "活動類型",
            list(activity_options.keys()),
            format_func=lambda x: activity_options[x],
            index=list(activity_options.keys()).index(current_activity),
            key=f"{self.widget_id}_activity_type",
        )
        self.config["activity_type"] = new_activity

        # 最大項目數（僅對列表類型有效）
        if new_activity in ["recent_trades", "pending_orders"]:
            max_items = st.slider(
                "最大顯示項目數",
                min_value=5,
                max_value=20,
                value=self.config.get("max_items", 10),
                key=f"{self.widget_id}_max_items",
            )
            self.config["max_items"] = max_items


class VolumeChartWidget(BaseWidget):
    """成交量圖表小工具"""

    def get_widget_type(self) -> str:
        return "volume_chart"

    def get_default_title(self) -> str:
        return "成交量分析"

    def get_default_size(self) -> Dict[str, int]:
        return WidgetSize.MEDIUM

    def render_content(self) -> None:
        """渲染成交量圖表內容"""
        symbol = self.config.get("symbol", "2330.TW")
        days = self.config.get("days", 30)

        # 生成成交量數據
        volume_data = self._generate_volume_data(symbol, days)

        # 創建成交量圖表
        import plotly.graph_objects as go

        fig = go.Figure()

        # 成交量柱狀圖
        colors = [
            self.theme["primary"] if i % 2 == 0 else self.theme["secondary"]
            for i in range(len(volume_data))
        ]

        fig.add_trace(
            go.Bar(
                x=volume_data.index,
                y=volume_data["volume"],
                name="成交量",
                marker_color=colors,
                opacity=0.7,
            )
        )

        # 成交量移動平均
        volume_ma = volume_data["volume"].rolling(window=5).mean()
        fig.add_trace(
            go.Scatter(
                x=volume_data.index,
                y=volume_ma,
                mode="lines",
                name="5日均量",
                line=dict(color=self.theme["danger"], width=2),
            )
        )

        fig.update_layout(
            height=250,
            xaxis_title="日期",
            yaxis_title="成交量",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False,
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False, "displaylogo": False},
        )

        # 顯示成交量統計
        self._show_volume_stats(volume_data["volume"])

    def _generate_volume_data(self, symbol: str, days: int) -> pd.DataFrame:
        """生成成交量數據"""
        np.random.seed(hash(symbol) % 2**32)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days - 1)
        dates = pd.date_range(start=start_date, end=end_date, freq="D")

        # 生成成交量數據
        base_volume = (
            1000000 if symbol == "2330.TW" else np.random.randint(100000, 2000000)
        )
        volumes = []

        for _ in dates:
            volume = int(base_volume * np.random.lognormal(0, 0.3))
            volumes.append(volume)

        return pd.DataFrame({"volume": volumes}, index=dates)

    def _show_volume_stats(self, volume_data: pd.Series) -> None:
        """顯示成交量統計"""
        col1, col2, col3 = st.columns(3)

        with col1:
            avg_volume = volume_data.mean()
            st.metric("平均成交量", f"{avg_volume:,.0f}")

        with col2:
            max_volume = volume_data.max()
            st.metric("最大成交量", f"{max_volume:,.0f}")

        with col3:
            current_volume = volume_data.iloc[-1]
            volume_ratio = (current_volume / avg_volume - 1) * 100
            st.metric("今日vs平均", f"{volume_ratio:+.1f}%")

    def render_widget_settings(self) -> None:
        """渲染成交量圖表特定設定"""
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
            min_value=7,
            max_value=90,
            value=self.config.get("days", 30),
            key=f"{self.widget_id}_days",
        )
        self.config["days"] = days
