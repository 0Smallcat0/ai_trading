"""報表視覺化圖表生成模組

此模組負責生成各種類型的圖表，包括：
- 累積報酬圖表
- 回撤圖表
- 績效儀表板
- 月度熱力圖
- 參數敏感度熱力圖
- 資產配置圖表
- 策略比較圖表
"""

import logging
from typing import Dict, List, Optional, Any, Union

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


class ChartGeneratorService:
    """圖表生成服務"""

    def __init__(self):
        """初始化圖表生成服務"""
        self.default_plotly_config = {
            "template": "plotly_white",
            "height": 400,
        }
        self.default_matplotlib_config = {
            "style": "seaborn-v0_8",
            "figsize": (12, 6),
        }

    def generate_cumulative_return_chart(
        self, data: Dict[str, Any], chart_type: str = "plotly"
    ) -> Union[go.Figure, plt.Figure, None]:
        """生成累積報酬圖表

        Args:
            data: 包含交易數據的字典
            chart_type: 圖表類型 ('plotly' 或 'matplotlib')

        Returns:
            圖表對象或 None
        """
        try:
            if "data" not in data or not data["data"]:
                return None

            df = pd.DataFrame(data["data"])
            df["execution_time"] = pd.to_datetime(df["execution_time"])

            if chart_type == "plotly":
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=df["execution_time"],
                        y=df["cumulative_pnl"],
                        mode="lines",
                        name="累積報酬",
                        line={"color": "blue", "width": 2},
                    )
                )

                fig.update_layout(
                    title="累積報酬曲線",
                    xaxis_title="時間",
                    yaxis_title="累積報酬 (元)",
                    **self.default_plotly_config,
                )

                return fig

            else:  # matplotlib
                plt.style.use(self.default_matplotlib_config["style"])
                fig, ax = plt.subplots(
                    figsize=self.default_matplotlib_config["figsize"]
                )

                ax.plot(
                    df["execution_time"],
                    df["cumulative_pnl"],
                    color="blue",
                    linewidth=2,
                    label="累積報酬",
                )

                ax.set_title("累積報酬曲線", fontsize=16, fontweight="bold")
                ax.set_xlabel("時間", fontsize=12)
                ax.set_ylabel("累積報酬 (元)", fontsize=12)
                ax.grid(True, alpha=0.3)
                ax.legend()

                plt.tight_layout()
                return fig

        except Exception as e:
            logger.error("生成累積報酬圖表失敗: %s", e)
            return None

    def generate_drawdown_chart(
        self, data: Dict[str, Any], chart_type: str = "plotly"
    ) -> Union[go.Figure, plt.Figure, None]:
        """生成回撤圖表

        Args:
            data: 包含交易數據的字典
            chart_type: 圖表類型

        Returns:
            圖表對象或 None
        """
        try:
            if "data" not in data or not data["data"]:
                return None

            df = pd.DataFrame(data["data"])
            df["execution_time"] = pd.to_datetime(df["execution_time"])

            # 計算回撤
            cumulative_pnl = df["cumulative_pnl"]
            running_max = cumulative_pnl.expanding().max()
            drawdown = cumulative_pnl - running_max

            if chart_type == "plotly":
                fig = go.Figure()

                # 添加累積報酬線
                fig.add_trace(
                    go.Scatter(
                        x=df["execution_time"],
                        y=cumulative_pnl,
                        mode="lines",
                        name="累積報酬",
                        line={"color": "blue"},
                    )
                )

                # 添加最高水位線
                fig.add_trace(
                    go.Scatter(
                        x=df["execution_time"],
                        y=running_max,
                        mode="lines",
                        name="最高水位",
                        line={"color": "green", "dash": "dash"},
                    )
                )

                # 添加回撤區域
                fig.add_trace(
                    go.Scatter(
                        x=df["execution_time"],
                        y=drawdown,
                        mode="lines",
                        name="回撤",
                        fill="tonexty",
                        fillcolor="rgba(255, 0, 0, 0.3)",
                        line={"color": "red"},
                    )
                )

                fig.update_layout(
                    title="回撤分析圖",
                    xaxis_title="時間",
                    yaxis_title="金額 (元)",
                    **self.default_plotly_config,
                )

                return fig

            else:  # matplotlib
                plt.style.use(self.default_matplotlib_config["style"])
                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

                # 上圖：累積報酬和最高水位
                ax1.plot(
                    df["execution_time"],
                    cumulative_pnl,
                    color="blue",
                    label="累積報酬",
                )
                ax1.plot(
                    df["execution_time"],
                    running_max,
                    color="green",
                    linestyle="--",
                    label="最高水位",
                )
                ax1.set_title("累積報酬與最高水位", fontsize=14, fontweight="bold")
                ax1.set_ylabel("金額 (元)", fontsize=12)
                ax1.grid(True, alpha=0.3)
                ax1.legend()

                # 下圖：回撤
                ax2.fill_between(
                    df["execution_time"],
                    drawdown,
                    0,
                    color="red",
                    alpha=0.3,
                    label="回撤",
                )
                ax2.plot(df["execution_time"], drawdown, color="red")
                ax2.set_title("回撤分析", fontsize=14, fontweight="bold")
                ax2.set_xlabel("時間", fontsize=12)
                ax2.set_ylabel("回撤 (元)", fontsize=12)
                ax2.grid(True, alpha=0.3)
                ax2.legend()

                plt.tight_layout()
                return fig

        except Exception as e:
            logger.error("生成回撤圖表失敗: %s", e)
            return None

    def generate_performance_dashboard(
        self, metrics: Dict[str, Any]
    ) -> Union[go.Figure, None]:
        """生成績效儀表板

        Args:
            metrics: 績效指標字典

        Returns:
            Plotly 儀表板圖表或 None
        """
        try:
            if not metrics:
                # 提供預設指標以避免空圖表
                metrics = {
                    "total_pnl": 0,
                    "win_rate": 0,
                    "profit_factor": 0,
                    "sharpe_ratio": 0,
                    "max_drawdown": 0,
                    "total_trades": 0,
                }

            # 創建子圖
            from plotly.subplots import make_subplots

            fig = make_subplots(
                rows=2,
                cols=3,
                subplot_titles=[
                    "總報酬",
                    "勝率",
                    "獲利因子",
                    "夏普比率",
                    "最大回撤",
                    "總交易次數",
                ],
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

            # 添加指標
            indicators = [
                {
                    "value": metrics.get("total_pnl", 0),
                    "title": "總報酬 (元)",
                    "row": 1,
                    "col": 1,
                },
                {
                    "value": metrics.get("win_rate", 0),
                    "title": "勝率 (%)",
                    "row": 1,
                    "col": 2,
                },
                {
                    "value": metrics.get("profit_factor", 0),
                    "title": "獲利因子",
                    "row": 1,
                    "col": 3,
                },
                {
                    "value": metrics.get("sharpe_ratio", 0),
                    "title": "夏普比率",
                    "row": 2,
                    "col": 1,
                },
                {
                    "value": metrics.get("max_drawdown", 0),
                    "title": "最大回撤 (元)",
                    "row": 2,
                    "col": 2,
                },
                {
                    "value": metrics.get("total_trades", 0),
                    "title": "總交易次數",
                    "row": 2,
                    "col": 3,
                },
            ]

            for indicator in indicators:
                fig.add_trace(
                    go.Indicator(
                        mode="number",
                        value=indicator["value"],
                        title={"text": indicator["title"]},
                        number={"font": {"size": 24}},
                    ),
                    row=indicator["row"],
                    col=indicator["col"],
                )

            fig.update_layout(
                title="交易績效儀表板",
                height=600,
                template="plotly_white",
            )

            return fig

        except Exception as e:
            logger.error("生成績效儀表板失敗: %s", e)
            return None

    def generate_monthly_heatmap(
        self, data: Dict[str, Any], chart_type: str = "plotly"
    ) -> Union[go.Figure, plt.Figure, None]:
        """生成月度績效熱力圖

        Args:
            data: 包含交易數據的字典
            chart_type: 圖表類型

        Returns:
            圖表對象或 None
        """
        try:
            if "data" not in data or not data["data"]:
                return None

            df = pd.DataFrame(data["data"])
            df["execution_time"] = pd.to_datetime(df["execution_time"])

            # 按年月分組計算收益
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
                            j,
                            i,
                            f"{pivot_table.iloc[i, j]:.0f}",
                            ha="center",
                            va="center",
                            color="black",
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
            logger.error("生成月度績效熱力圖失敗: %s", e)
            return None

    def generate_parameter_sensitivity_heatmap(
        self, param_results: Dict[str, Any], chart_type: str = "plotly"
    ) -> Union[go.Figure, plt.Figure, None]:
        """生成參數敏感度熱力圖

        Args:
            param_results: 參數測試結果
            chart_type: 圖表類型

        Returns:
            圖表對象或 None
        """
        try:
            # 從 param_results 中提取參數值，如果沒有則使用預設值
            param1_values = param_results.get("param1_values", [10, 20, 30, 40, 50])
            param2_values = param_results.get(
                "param2_values", [0.1, 0.2, 0.3, 0.4, 0.5]
            )

            # 創建績效矩陣
            if "performance_matrix" in param_results:
                performance_matrix = np.array(param_results["performance_matrix"])
            else:
                # 模擬數據
                matrix_shape = (len(param1_values), len(param2_values))
                performance_matrix = np.random.randn(*matrix_shape) * 1000 + 5000

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
                            j,
                            i,
                            f"{performance_matrix[i, j]:.0f}",
                            ha="center",
                            va="center",
                            color="black",
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
            logger.error("生成參數敏感度熱力圖失敗: %s", e)
            return None

    def generate_asset_allocation_chart(
        self, portfolio_data: Dict[str, Any], chart_type: str = "plotly"
    ) -> Union[go.Figure, plt.Figure, None]:
        """生成資產配置圖表

        Args:
            portfolio_data: 投資組合數據
            chart_type: 圖表類型

        Returns:
            圖表對象或 None
        """
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
            logger.error("生成資產配置圖表失敗: %s", e)
            return None

    def generate_strategy_comparison_chart(
        self,
        comparison_data: Dict[str, Any],
        metric: str = "total_return",
        chart_type: str = "plotly",
    ) -> Union[go.Figure, plt.Figure, None]:
        """生成策略比較圖表

        Args:
            comparison_data: 策略比較數據
            metric: 比較指標
            chart_type: 圖表類型

        Returns:
            圖表對象或 None
        """
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
            logger.error("生成策略比較圖表失敗: %s", e)
            return None
