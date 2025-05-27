"""報表視覺化服務

此模組實現了報表查詢與視覺化的核心功能，包括：
- 交易績效圖表與分析
- 交易明細與資產變化追蹤
- 策略績效比較與分析
- 參數敏感度分析與優化
- 多種圖表呈現與報表導出

遵循與其他服務層相同的架構模式，提供完整的報表視覺化功能。
"""

import logging
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib
from sqlalchemy import create_engine, desc, and_, or_
from sqlalchemy.orm import sessionmaker
from src.config import DB_URL, CACHE_DIR
from src.database.schema import (
    ChartConfig,
    ExportLog,
    ReportCache,
    TradingOrder,
    TradeExecution,
)

# 設置 matplotlib 後端
matplotlib.use("Agg")

# 設置日誌
logger = logging.getLogger(__name__)


class ReportVisualizationService:
    """
    報表視覺化服務

    提供完整的報表查詢與視覺化功能，包括交易績效分析、
    策略比較、參數優化和多種圖表呈現。
    """

    def __init__(self):
        """初始化報表視覺化服務"""
        try:
            # 初始化資料庫連接
            self.engine = create_engine(DB_URL)
            self.session_factory = sessionmaker(bind=self.engine)
            logger.info("報表視覺化服務資料庫連接初始化成功")

            # 初始化快取設定
            self.cache_enabled = True
            self.default_cache_duration = 300  # 5分鐘

            # 初始化圖表設定
            self.default_chart_config = {
                "plotly": {
                    "template": "plotly_white",
                    "height": 400,
                    "showlegend": True,
                },
                "matplotlib": {"style": "seaborn-v0_8", "figsize": (12, 6), "dpi": 100},
            }

            # 確保快取目錄存在
            Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

            logger.info("報表視覺化服務初始化完成")

        except Exception as e:
            logger.error(f"報表視覺化服務初始化失敗: {e}")
            raise

    def get_trading_performance_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        strategy_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """獲取交易績效數據"""
        try:
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=365)  # 預設一年

            with self.session_factory() as session:
                # 獲取交易執行記錄
                query = session.query(TradeExecution).filter(
                    and_(
                        TradeExecution.execution_time >= start_date,
                        TradeExecution.execution_time <= end_date,
                    )
                )

                if strategy_name:
                    # 通過訂單關聯策略
                    query = query.join(TradingOrder).filter(
                        TradingOrder.strategy_name == strategy_name
                    )

                executions = query.order_by(TradeExecution.execution_time).all()

                if not executions:
                    return {"message": "無交易數據"}

                # 轉換為 DataFrame
                data = []
                for execution in executions:
                    data.append(
                        {
                            "execution_time": execution.execution_time,
                            "symbol": execution.symbol,
                            "action": execution.action,
                            "quantity": execution.quantity,
                            "price": execution.price,
                            "amount": execution.amount,
                            "commission": execution.commission or 0,
                            "tax": execution.tax or 0,
                            "net_amount": execution.net_amount or execution.amount,
                        }
                    )

                df = pd.DataFrame(data)

                # 計算累積報酬
                df["cumulative_pnl"] = df["net_amount"].cumsum()
                df["daily_return"] = df.groupby(df["execution_time"].dt.date)[
                    "net_amount"
                ].sum()

                # 計算績效指標
                performance_metrics = self._calculate_performance_metrics(df)

                return {
                    "data": df.to_dict("records"),
                    "metrics": performance_metrics,
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                    },
                }

        except Exception as e:
            logger.error(f"獲取交易績效數據失敗: {e}")
            return {"error": str(e)}

    def _calculate_performance_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """計算績效指標"""
        try:
            if df.empty:
                return {}

            # 基本統計
            total_trades = len(df)
            total_pnl = df["net_amount"].sum()

            # 勝率計算
            winning_trades = len(df[df["net_amount"] > 0])
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            # 平均獲利/虧損
            avg_win = (
                df[df["net_amount"] > 0]["net_amount"].mean()
                if winning_trades > 0
                else 0
            )
            avg_loss = (
                df[df["net_amount"] < 0]["net_amount"].mean()
                if (total_trades - winning_trades) > 0
                else 0
            )

            # 獲利因子
            total_wins = df[df["net_amount"] > 0]["net_amount"].sum()
            total_losses = abs(df[df["net_amount"] < 0]["net_amount"].sum())
            profit_factor = (
                (total_wins / total_losses) if total_losses > 0 else float("inf")
            )

            # 最大回撤計算
            cumulative_pnl = df["net_amount"].cumsum()
            running_max = cumulative_pnl.expanding().max()
            drawdown = cumulative_pnl - running_max
            max_drawdown = drawdown.min()

            # 夏普比率計算（簡化版）
            daily_returns = df.groupby(df["execution_time"].dt.date)["net_amount"].sum()
            if len(daily_returns) > 1:
                sharpe_ratio = (
                    daily_returns.mean() / daily_returns.std() * np.sqrt(252)
                    if daily_returns.std() > 0
                    else 0
                )
            else:
                sharpe_ratio = 0

            return {
                "total_trades": total_trades,
                "total_pnl": round(total_pnl, 2),
                "win_rate": round(win_rate, 2),
                "avg_win": round(avg_win, 2),
                "avg_loss": round(avg_loss, 2),
                "profit_factor": (
                    round(profit_factor, 2) if profit_factor != float("inf") else "∞"
                ),
                "max_drawdown": round(max_drawdown, 2),
                "sharpe_ratio": round(sharpe_ratio, 2),
                "total_commission": round(df["commission"].sum(), 2),
                "total_tax": round(df["tax"].sum(), 2),
            }

        except Exception as e:
            logger.error(f"計算績效指標失敗: {e}")
            return {}

    def generate_cumulative_return_chart(
        self, data: Dict[str, Any], chart_type: str = "plotly"
    ) -> Union[go.Figure, plt.Figure]:
        """生成累積報酬曲線圖"""
        try:
            if "data" not in data or not data["data"]:
                raise ValueError("無有效數據")

            df = pd.DataFrame(data["data"])
            df["execution_time"] = pd.to_datetime(df["execution_time"])

            if chart_type == "plotly":
                fig = go.Figure()

                fig.add_trace(
                    go.Scatter(
                        x=df["execution_time"],
                        y=df["cumulative_pnl"],
                        mode="lines",
                        name="累積損益",
                        line=dict(color="blue", width=2),
                    )
                )

                fig.update_layout(
                    title="累積報酬曲線",
                    xaxis_title="時間",
                    yaxis_title="累積損益",
                    template="plotly_white",
                    height=500,
                )

                return fig

            else:  # matplotlib
                plt.style.use("seaborn-v0_8")
                fig, ax = plt.subplots(figsize=(12, 6))

                ax.plot(
                    df["execution_time"],
                    df["cumulative_pnl"],
                    color="blue",
                    linewidth=2,
                    label="累積損益",
                )

                ax.set_title("累積報酬曲線", fontsize=16, fontweight="bold")
                ax.set_xlabel("時間", fontsize=12)
                ax.set_ylabel("累積損益", fontsize=12)
                ax.legend()
                ax.grid(True, alpha=0.3)

                plt.tight_layout()
                return fig

        except Exception as e:
            logger.error(f"生成累積報酬曲線圖失敗: {e}")
            return None

    def generate_drawdown_chart(
        self, data: Dict[str, Any], chart_type: str = "plotly"
    ) -> Union[go.Figure, plt.Figure]:
        """生成回撤分析圖表"""
        try:
            if "data" not in data or not data["data"]:
                raise ValueError("無有效數據")

            df = pd.DataFrame(data["data"])
            df["execution_time"] = pd.to_datetime(df["execution_time"])

            # 計算回撤
            cumulative_pnl = df["cumulative_pnl"]
            running_max = cumulative_pnl.expanding().max()
            drawdown = cumulative_pnl - running_max
            drawdown_pct = (drawdown / running_max * 100).fillna(0)

            if chart_type == "plotly":
                fig = go.Figure()

                # 添加回撤曲線
                fig.add_trace(
                    go.Scatter(
                        x=df["execution_time"],
                        y=drawdown_pct,
                        mode="lines",
                        name="回撤 (%)",
                        fill="tonexty",
                        fillcolor="rgba(255, 0, 0, 0.3)",
                        line=dict(color="red", width=2),
                    )
                )

                # 添加零線
                fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5)

                fig.update_layout(
                    title="回撤分析圖",
                    xaxis_title="時間",
                    yaxis_title="回撤 (%)",
                    template="plotly_white",
                    height=400,
                )

                return fig

            else:  # matplotlib
                plt.style.use("seaborn-v0_8")
                fig, ax = plt.subplots(figsize=(12, 6))

                ax.fill_between(
                    df["execution_time"],
                    drawdown_pct,
                    0,
                    color="red",
                    alpha=0.3,
                    label="回撤",
                )
                ax.plot(df["execution_time"], drawdown_pct, color="red", linewidth=2)

                ax.axhline(y=0, color="black", linestyle="--", alpha=0.5)
                ax.set_title("回撤分析圖", fontsize=16, fontweight="bold")
                ax.set_xlabel("時間", fontsize=12)
                ax.set_ylabel("回撤 (%)", fontsize=12)
                ax.legend()
                ax.grid(True, alpha=0.3)

                plt.tight_layout()
                return fig

        except Exception as e:
            logger.error(f"生成回撤分析圖表失敗: {e}")
            return None

    def generate_performance_dashboard(self, metrics: Dict[str, Any]) -> go.Figure:
        """生成績效指標儀表板"""
        try:
            # 創建子圖
            from plotly.subplots import make_subplots

            fig = make_subplots(
                rows=2,
                cols=3,
                subplot_titles=(
                    "總損益",
                    "勝率",
                    "獲利因子",
                    "夏普比率",
                    "最大回撤",
                    "交易次數",
                ),
                specs=[
                    [
                        {"type": "indicator"},
                        {"type": "indicator"},
                        {"type": "indicator"},
                    ],
                    [
                        {"type": "indicator"},
                        {"type": "indicator"},
                        {"type": "indicator"},
                    ],
                ],
            )

            # 總損益
            fig.add_trace(
                go.Indicator(
                    mode="number+delta",
                    value=metrics.get("total_pnl", 0),
                    title={"text": "總損益"},
                    number={"prefix": "$"},
                    delta={"reference": 0},
                ),
                row=1,
                col=1,
            )

            # 勝率
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number",
                    value=metrics.get("win_rate", 0),
                    title={"text": "勝率 (%)"},
                    gauge={
                        "axis": {"range": [None, 100]},
                        "bar": {"color": "green"},
                        "steps": [
                            {"range": [0, 50], "color": "lightgray"},
                            {"range": [50, 80], "color": "yellow"},
                        ],
                        "threshold": {
                            "line": {"color": "red", "width": 4},
                            "thickness": 0.75,
                            "value": 90,
                        },
                    },
                ),
                row=1,
                col=2,
            )

            # 獲利因子
            profit_factor = metrics.get("profit_factor", 0)
            if profit_factor == "∞":
                profit_factor = 999

            fig.add_trace(
                go.Indicator(
                    mode="number+delta",
                    value=profit_factor,
                    title={"text": "獲利因子"},
                    delta={"reference": 1},
                ),
                row=1,
                col=3,
            )

            # 夏普比率
            fig.add_trace(
                go.Indicator(
                    mode="number+delta",
                    value=metrics.get("sharpe_ratio", 0),
                    title={"text": "夏普比率"},
                    delta={"reference": 1},
                ),
                row=2,
                col=1,
            )

            # 最大回撤
            fig.add_trace(
                go.Indicator(
                    mode="number",
                    value=abs(metrics.get("max_drawdown", 0)),
                    title={"text": "最大回撤"},
                    number={"prefix": "$"},
                ),
                row=2,
                col=2,
            )

            # 交易次數
            fig.add_trace(
                go.Indicator(
                    mode="number",
                    value=metrics.get("total_trades", 0),
                    title={"text": "交易次數"},
                ),
                row=2,
                col=3,
            )

            fig.update_layout(
                title="績效指標儀表板", height=600, template="plotly_white"
            )

            return fig

        except Exception as e:
            logger.error(f"生成績效指標儀表板失敗: {e}")
            return None

    def generate_monthly_heatmap(
        self, data: Dict[str, Any], chart_type: str = "plotly"
    ) -> Union[go.Figure, plt.Figure]:
        """生成月度績效熱力圖"""
        try:
            if "data" not in data or not data["data"]:
                raise ValueError("無有效數據")

            df = pd.DataFrame(data["data"])
            df["execution_time"] = pd.to_datetime(df["execution_time"])

            # 按月份聚合數據
            df["year"] = df["execution_time"].dt.year
            df["month"] = df["execution_time"].dt.month
            monthly_returns = (
                df.groupby(["year", "month"])["net_amount"].sum().reset_index()
            )

            # 創建透視表
            pivot_table = monthly_returns.pivot(
                index="year", columns="month", values="net_amount"
            )
            pivot_table = pivot_table.fillna(0)

            # 確保有12個月的欄位
            for month in range(1, 13):
                if month not in pivot_table.columns:
                    pivot_table[month] = 0

            pivot_table = pivot_table.reindex(columns=range(1, 13))

            if chart_type == "plotly":
                fig = go.Figure(
                    data=go.Heatmap(
                        z=pivot_table.values,
                        x=[f"{i}月" for i in range(1, 13)],
                        y=pivot_table.index,
                        colorscale="RdYlGn",
                        text=pivot_table.values,
                        texttemplate="%{text:.0f}",
                        textfont={"size": 10},
                        hoverongaps=False,
                    )
                )

                fig.update_layout(
                    title="月度績效熱力圖",
                    xaxis_title="月份",
                    yaxis_title="年份",
                    template="plotly_white",
                    height=400,
                )

                return fig

            else:  # matplotlib
                plt.style.use("seaborn-v0_8")
                fig, ax = plt.subplots(figsize=(12, 6))

                # 使用 matplotlib 的 imshow 替代 seaborn heatmap
                im = ax.imshow(pivot_table, cmap="RdYlGn", aspect="auto")

                # 添加數值標註
                for i in range(len(pivot_table.index)):
                    for j in range(len(pivot_table.columns)):
                        ax.text(
                            j, i, f"{pivot_table.iloc[i, j]:.0f}",
                            ha="center", va="center", color="black"
                        )

                # 添加顏色條
                cbar = plt.colorbar(im, ax=ax)
                cbar.set_label("月度收益")

                ax.set_title("月度績效熱力圖", fontsize=16, fontweight="bold")
                ax.set_xlabel("月份", fontsize=12)
                ax.set_ylabel("年份", fontsize=12)

                # 設置月份標籤
                ax.set_xticklabels([f"{i}月" for i in range(1, 13)])

                plt.tight_layout()
                return fig

        except Exception as e:
            logger.error(f"生成月度績效熱力圖失敗: {e}")
            return None

    def get_trade_details_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        symbol: Optional[str] = None,
        limit: int = 1000,
    ) -> Dict[str, Any]:
        """獲取交易明細數據"""
        try:
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=90)  # 預設三個月

            with self.session_factory() as session:
                # 獲取交易訂單和執行記錄
                query = (
                    session.query(TradingOrder, TradeExecution)
                    .join(
                        TradeExecution, TradingOrder.order_id == TradeExecution.order_id
                    )
                    .filter(
                        and_(
                            TradingOrder.created_at >= start_date,
                            TradingOrder.created_at <= end_date,
                        )
                    )
                )

                if symbol:
                    query = query.filter(TradingOrder.symbol == symbol)

                results = (
                    query.order_by(desc(TradingOrder.created_at)).limit(limit).all()
                )

                if not results:
                    return {"message": "無交易明細數據"}

                # 轉換為詳細記錄
                details = []
                for order, execution in results:
                    holding_period = None
                    if order.filled_at and order.created_at:
                        holding_period = (
                            order.filled_at - order.created_at
                        ).total_seconds() / 3600  # 小時

                    details.append(
                        {
                            "order_id": order.order_id,
                            "symbol": order.symbol,
                            "action": order.action,
                            "order_time": order.created_at.isoformat(),
                            "execution_time": execution.execution_time.isoformat(),
                            "order_price": order.price,
                            "execution_price": execution.price,
                            "quantity": execution.quantity,
                            "amount": execution.amount,
                            "commission": execution.commission or 0,
                            "tax": execution.tax or 0,
                            "net_amount": execution.net_amount or execution.amount,
                            "holding_period_hours": (
                                round(holding_period, 2) if holding_period else None
                            ),
                            "strategy_name": order.strategy_name,
                            "signal_id": order.signal_id,
                        }
                    )

                # 計算統計資訊
                df = pd.DataFrame(details)
                statistics = self._calculate_trade_statistics(df)

                return {
                    "details": details,
                    "statistics": statistics,
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                    },
                }

        except Exception as e:
            logger.error(f"獲取交易明細數據失敗: {e}")
            return {"error": str(e)}

    def _calculate_trade_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """計算交易統計資訊"""
        try:
            if df.empty:
                return {}

            # 基本統計
            total_trades = len(df)
            total_volume = df["amount"].sum()
            total_commission = df["commission"].sum()
            total_tax = df["tax"].sum()

            # 持有期間統計
            holding_periods = df["holding_period_hours"].dropna()
            avg_holding_period = (
                holding_periods.mean() if not holding_periods.empty else 0
            )

            # 交易頻率（每日平均交易次數）
            if not df.empty:
                date_range = pd.to_datetime(df["execution_time"]).dt.date
                unique_days = len(date_range.unique())
                daily_trade_frequency = (
                    total_trades / unique_days if unique_days > 0 else 0
                )
            else:
                daily_trade_frequency = 0

            # 按股票分組統計
            symbol_stats = (
                df.groupby("symbol")
                .agg({"amount": "sum", "net_amount": "sum", "quantity": "sum"})
                .to_dict("index")
            )

            # 按策略分組統計
            strategy_stats = (
                df.groupby("strategy_name")
                .agg({"amount": "sum", "net_amount": "sum", "order_id": "count"})
                .rename(columns={"order_id": "trade_count"})
                .to_dict("index")
            )

            return {
                "total_trades": total_trades,
                "total_volume": round(total_volume, 2),
                "total_commission": round(total_commission, 2),
                "total_tax": round(total_tax, 2),
                "avg_holding_period_hours": round(avg_holding_period, 2),
                "daily_trade_frequency": round(daily_trade_frequency, 2),
                "symbol_statistics": symbol_stats,
                "strategy_statistics": strategy_stats,
            }

        except Exception as e:
            logger.error(f"計算交易統計資訊失敗: {e}")
            return {}

    def generate_asset_allocation_chart(
        self, portfolio_data: Dict[str, Any], chart_type: str = "plotly"
    ) -> Union[go.Figure, plt.Figure]:
        """生成資產配置圖表"""
        try:
            if not portfolio_data:
                raise ValueError("無投資組合數據")

            # 模擬投資組合數據（實際應從資料庫獲取）
            holdings = [
                {"symbol": "2330.TW", "value": 500000, "weight": 50.0},
                {"symbol": "2317.TW", "value": 200000, "weight": 20.0},
                {"symbol": "2454.TW", "value": 150000, "weight": 15.0},
                {"symbol": "現金", "value": 150000, "weight": 15.0},
            ]

            df = pd.DataFrame(holdings)

            if chart_type == "plotly":
                fig = go.Figure(
                    data=[
                        go.Pie(
                            labels=df["symbol"],
                            values=df["value"],
                            hole=0.3,
                            textinfo="label+percent",
                            textposition="outside",
                        )
                    ]
                )

                fig.update_layout(
                    title="資產配置分布",
                    template="plotly_white",
                    height=500,
                    showlegend=True,
                )

                return fig

            else:  # matplotlib
                plt.style.use("seaborn-v0_8")
                fig, ax = plt.subplots(figsize=(10, 8))

                colors = plt.cm.Set3(np.linspace(0, 1, len(df)))
                ax.pie(
                    df["value"],
                    labels=df["symbol"],
                    autopct="%1.1f%%",
                    colors=colors,
                    startangle=90,
                )

                ax.set_title("資產配置分布", fontsize=16, fontweight="bold")

                plt.tight_layout()
                return fig

        except Exception as e:
            logger.error(f"生成資產配置圖表失敗: {e}")
            return None

    def compare_strategies_performance(
        self,
        strategy_names: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """比較策略績效"""
        try:
            if not strategy_names:
                return {"error": "未指定策略名稱"}

            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=365)

            strategies_data = {}

            for strategy_name in strategy_names:
                # 獲取策略績效數據
                strategy_data = self.get_trading_performance_data(
                    start_date=start_date,
                    end_date=end_date,
                    strategy_name=strategy_name,
                )

                if "error" not in strategy_data and "data" in strategy_data:
                    strategies_data[strategy_name] = strategy_data

            if not strategies_data:
                return {"message": "無策略數據可比較"}

            # 計算比較指標
            comparison_metrics = {}
            for strategy_name, data in strategies_data.items():
                metrics = data.get("metrics", {})
                comparison_metrics[strategy_name] = {
                    "total_return": metrics.get("total_pnl", 0),
                    "win_rate": metrics.get("win_rate", 0),
                    "sharpe_ratio": metrics.get("sharpe_ratio", 0),
                    "max_drawdown": metrics.get("max_drawdown", 0),
                    "profit_factor": metrics.get("profit_factor", 0),
                    "total_trades": metrics.get("total_trades", 0),
                }

            return {
                "strategies_data": strategies_data,
                "comparison_metrics": comparison_metrics,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            }

        except Exception as e:
            logger.error(f"比較策略績效失敗: {e}")
            return {"error": str(e)}

    def generate_strategy_comparison_chart(
        self,
        comparison_data: Dict[str, Any],
        metric: str = "total_return",
        chart_type: str = "plotly",
    ) -> Union[go.Figure, plt.Figure]:
        """生成策略比較圖表"""
        try:
            if "comparison_metrics" not in comparison_data:
                raise ValueError("無比較數據")

            metrics_data = comparison_data["comparison_metrics"]
            strategies = list(metrics_data.keys())
            values = [metrics_data[strategy].get(metric, 0) for strategy in strategies]

            if chart_type == "plotly":
                fig = go.Figure(data=[go.Bar(x=strategies, y=values, name=metric)])

                metric_names = {
                    "total_return": "總報酬",
                    "win_rate": "勝率 (%)",
                    "sharpe_ratio": "夏普比率",
                    "max_drawdown": "最大回撤",
                    "profit_factor": "獲利因子",
                }

                fig.update_layout(
                    title=f"策略{metric_names.get(metric, metric)}比較",
                    xaxis_title="策略",
                    yaxis_title=metric_names.get(metric, metric),
                    template="plotly_white",
                    height=400,
                )

                return fig

            else:  # matplotlib
                plt.style.use("seaborn-v0_8")
                fig, ax = plt.subplots(figsize=(10, 6))

                bars = ax.bar(strategies, values, color="skyblue", alpha=0.7)

                # 添加數值標籤
                for bar, value in zip(bars, values):
                    height = bar.get_height()
                    ax.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height,
                        f"{value:.2f}",
                        ha="center",
                        va="bottom",
                    )

                ax.set_title(f"策略{metric}比較", fontsize=16, fontweight="bold")
                ax.set_xlabel("策略", fontsize=12)
                ax.set_ylabel(metric, fontsize=12)
                ax.grid(True, alpha=0.3)

                plt.xticks(rotation=45)
                plt.tight_layout()
                return fig

        except Exception as e:
            logger.error(f"生成策略比較圖表失敗: {e}")
            return None

    def generate_parameter_sensitivity_heatmap(
        self, param_results: Dict[str, Any], chart_type: str = "plotly"
    ) -> Union[go.Figure, plt.Figure]:
        """生成參數敏感度熱力圖"""
        try:
            # 從 param_results 中提取參數值，如果沒有則使用預設值
            param1_values = param_results.get(
                "param1_values", [10, 20, 30, 40, 50]
            )
            param2_values = param_results.get(
                "param2_values", [0.1, 0.2, 0.3, 0.4, 0.5]
            )

            # 創建績效矩陣
            if "performance_matrix" in param_results:
                performance_matrix = np.array(param_results["performance_matrix"])
            else:
                # 模擬數據
                matrix_shape = (len(param1_values), len(param2_values))
                performance_matrix = (
                    np.random.randn(*matrix_shape) * 1000 + 5000
                )

            if chart_type == "plotly":
                fig = go.Figure(
                    data=go.Heatmap(
                        z=performance_matrix,
                        x=[f"參數2={v}" for v in param2_values],
                        y=[f"參數1={v}" for v in param1_values],
                        colorscale="RdYlGn",
                        text=performance_matrix,
                        texttemplate="%{text:.0f}",
                        textfont={"size": 10},
                        hoverongaps=False,
                    )
                )

                fig.update_layout(
                    title="參數敏感度分析熱力圖",
                    xaxis_title="參數2",
                    yaxis_title="參數1",
                    template="plotly_white",
                    height=500,
                )

                return fig

            else:  # matplotlib
                plt.style.use("seaborn-v0_8")
                fig, ax = plt.subplots(figsize=(10, 8))

                # 使用 matplotlib 的 imshow 替代 seaborn heatmap
                im = ax.imshow(performance_matrix, cmap="RdYlGn", aspect="auto")

                # 設置標籤
                ax.set_xticks(range(len(param2_values)))
                ax.set_yticks(range(len(param1_values)))
                ax.set_xticklabels([f"參數2={v}" for v in param2_values])
                ax.set_yticklabels([f"參數1={v}" for v in param1_values])

                # 添加數值標註
                for i in range(len(param1_values)):
                    for j in range(len(param2_values)):
                        ax.text(
                            j, i, f"{performance_matrix[i, j]:.0f}",
                            ha="center", va="center", color="black"
                        )

                # 添加顏色條
                cbar = plt.colorbar(im, ax=ax)
                cbar.set_label("績效指標")

                ax.set_title("參數敏感度分析熱力圖", fontsize=16, fontweight="bold")
                ax.set_xlabel("參數2", fontsize=12)
                ax.set_ylabel("參數1", fontsize=12)

                plt.tight_layout()
                return fig

        except Exception as e:
            logger.error(f"生成參數敏感度熱力圖失敗: {e}")
            return None

    def export_report(
        self,
        report_data: Dict[str, Any],
        export_format: str = "pdf",
        template_id: Optional[str] = None,
        user_id: str = "system",
    ) -> Tuple[bool, str, Optional[str]]:
        """匯出報表"""
        try:
            export_id = str(uuid.uuid4())
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{timestamp}.{export_format}"
            filepath = Path(CACHE_DIR) / filename

            # 確保目錄存在
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # 記錄匯出開始
            with self.session_factory() as session:
                export_log = ExportLog(
                    export_id=export_id,
                    export_type="report",
                    export_format=export_format,
                    export_name=filename,
                    template_id=template_id,
                    export_parameters=report_data,
                    status="pending",
                    started_at=datetime.now(),
                    user_id=user_id,
                    user_name=user_id,
                )
                session.add(export_log)
                session.commit()

            # 根據格式匯出
            if export_format.lower() == "json":
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)

            elif export_format.lower() == "csv":
                # 將報表數據轉換為 CSV
                if "data" in report_data and report_data["data"]:
                    df = pd.DataFrame(report_data["data"])
                    df.to_csv(filepath, index=False, encoding="utf-8-sig")
                else:
                    return False, "無數據可匯出為CSV", None

            elif export_format.lower() == "excel":
                # 將報表數據轉換為 Excel
                if "data" in report_data and report_data["data"]:
                    df = pd.DataFrame(report_data["data"])
                    df.to_excel(filepath, index=False)
                else:
                    return False, "無數據可匯出為Excel", None

            elif export_format.lower() == "html":
                # 生成 HTML 報表
                html_content = self._generate_html_report(report_data)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(html_content)

            else:
                return False, f"不支援的匯出格式: {export_format}", None

            # 更新匯出狀態
            file_size = filepath.stat().st_size
            with self.session_factory() as session:
                export_log = (
                    session.query(ExportLog).filter_by(export_id=export_id).first()
                )
                if export_log:
                    export_log.status = "completed"
                    export_log.completed_at = datetime.now()
                    export_log.file_path = str(filepath)
                    export_log.file_size = file_size
                    export_log.duration_seconds = (
                        datetime.now() - export_log.started_at
                    ).total_seconds()
                    session.commit()

            return True, f"報表已匯出到 {filename}", str(filepath)

        except Exception as e:
            logger.error(f"匯出報表失敗: {e}")

            # 更新匯出狀態為失敗
            try:
                with self.session_factory() as session:
                    export_log = (
                        session.query(ExportLog).filter_by(export_id=export_id).first()
                    )
                    if export_log:
                        export_log.status = "failed"
                        export_log.error_message = str(e)
                        session.commit()
            except Exception as update_error:
                logging.error("更新匯出狀態失敗: %s", update_error)

            return False, f"匯出失敗: {e}", None

    def _generate_html_report(self, report_data: Dict[str, Any]) -> str:
        """生成 HTML 報表"""
        try:
            html_template = """
            <!DOCTYPE html>
            <html lang="zh-TW">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>交易績效報表</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ text-align: center; margin-bottom: 30px; }}
                    .metrics {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 20px;
                        margin-bottom: 30px;
                    }}
                    .metric-card {{
                        border: 1px solid #ddd;
                        padding: 15px;
                        border-radius: 5px;
                        text-align: center;
                    }}
                    .metric-value {{
                        font-size: 24px;
                        font-weight: bold;
                        color: #333;
                    }}
                    .metric-label {{
                        font-size: 14px;
                        color: #666;
                        margin-top: 5px;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 20px;
                    }}
                    th, td {{
                        border: 1px solid #ddd;
                        padding: 8px;
                        text-align: left;
                    }}
                    th {{ background-color: #f2f2f2; }}
                    .footer {{
                        margin-top: 30px;
                        text-align: center;
                        color: #666;
                        font-size: 12px;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>交易績效報表</h1>
                    <p>生成時間: {generated_time}</p>
                </div>

                <div class="metrics">
                    {metrics_html}
                </div>

                {data_table}

                <div class="footer">
                    <p>此報表由 AI Trading System 自動生成</p>
                </div>
            </body>
            </html>
            """

            # 生成指標卡片
            metrics_html = ""
            if "metrics" in report_data:
                metrics = report_data["metrics"]
                for key, value in metrics.items():
                    metric_name = {
                        "total_pnl": "總損益",
                        "win_rate": "勝率 (%)",
                        "total_trades": "總交易次數",
                        "sharpe_ratio": "夏普比率",
                        "max_drawdown": "最大回撤",
                    }.get(key, key)

                    metrics_html += f"""
                    <div class="metric-card">
                        <div class="metric-value">{value}</div>
                        <div class="metric-label">{metric_name}</div>
                    </div>
                    """

            # 生成數據表格
            data_table = ""
            if "data" in report_data and report_data["data"]:
                df = pd.DataFrame(report_data["data"])
                html_table = df.to_html(
                    index=False, classes='data-table'
                )
                data_table = f"<h2>交易明細</h2>{html_table}"

            return html_template.format(
                generated_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                metrics_html=metrics_html,
                data_table=data_table,
            )

        except Exception as e:
            logger.error(f"生成HTML報表失敗: {e}")
            return "<html><body><h1>報表生成失敗</h1></body></html>"

    def save_chart_config(
        self,
        config_name: str,
        chart_type: str,
        config_data: Dict[str, Any],
        user_id: str = "system",
    ) -> Tuple[bool, str]:
        """保存圖表配置"""
        try:
            config_id = str(uuid.uuid4())

            with self.session_factory() as session:
                chart_config = ChartConfig(
                    config_id=config_id,
                    config_name=config_name,
                    chart_type=chart_type,
                    chart_style=config_data.get("style", {}),
                    axis_config=config_data.get("axis", {}),
                    legend_config=config_data.get("legend", {}),
                    color_scheme=config_data.get("colors", {}),
                    interactive_features=config_data.get("interactive", {}),
                    width=config_data.get("width"),
                    height=config_data.get("height"),
                    created_by=user_id,
                    is_active=True,
                )
                session.add(chart_config)
                session.commit()

            return True, f"圖表配置已保存: {config_name}"

        except Exception as e:
            logger.error(f"保存圖表配置失敗: {e}")
            return False, f"保存失敗: {e}"

    def get_chart_configs(
        self, chart_type: Optional[str] = None, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """獲取圖表配置列表"""
        try:
            with self.session_factory() as session:
                query = session.query(ChartConfig).filter(
                    ChartConfig.is_active.is_(True)
                )

                if chart_type:
                    query = query.filter(ChartConfig.chart_type == chart_type)

                if user_id:
                    query = query.filter(ChartConfig.created_by == user_id)

                configs = query.order_by(desc(ChartConfig.created_at)).all()

                result = []
                for config in configs:
                    result.append(
                        {
                            "config_id": config.config_id,
                            "config_name": config.config_name,
                            "chart_type": config.chart_type,
                            "created_by": config.created_by,
                            "created_at": config.created_at.isoformat(),
                            "usage_count": config.usage_count,
                        }
                    )

                return result

        except Exception as e:
            logger.error(f"獲取圖表配置失敗: {e}")
            return []

    def get_export_logs(
        self,
        user_id: Optional[str] = None,
        export_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """獲取匯出日誌"""
        try:
            with self.session_factory() as session:
                query = session.query(ExportLog)

                if user_id:
                    query = query.filter(ExportLog.user_id == user_id)

                if export_type:
                    query = query.filter(ExportLog.export_type == export_type)

                logs = query.order_by(desc(ExportLog.created_at)).limit(limit).all()

                result = []
                for log in logs:
                    result.append(
                        {
                            "export_id": log.export_id,
                            "export_type": log.export_type,
                            "export_format": log.export_format,
                            "export_name": log.export_name,
                            "status": log.status,
                            "file_size": log.file_size,
                            "duration_seconds": log.duration_seconds,
                            "created_at": log.created_at.isoformat(),
                            "download_count": log.download_count,
                        }
                    )

                return result

        except Exception as e:
            logger.error(f"獲取匯出日誌失敗: {e}")
            return []

    def cleanup_cache(self, max_age_hours: int = 24) -> Tuple[bool, str]:
        """清理過期快取"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

            with self.session_factory() as session:
                # 清理過期快取記錄
                deleted_count = (
                    session.query(ReportCache)
                    .filter(
                        or_(
                            ReportCache.expires_at < datetime.now(),
                            ReportCache.created_at < cutoff_time,
                        )
                    )
                    .delete()
                )

                session.commit()

                message = f"已清理 {deleted_count} 個過期快取記錄"
                logger.info(message)

                return True, message

        except Exception as e:
            logger.error(f"清理快取失敗: {e}")
            return False, f"清理失敗: {e}"
