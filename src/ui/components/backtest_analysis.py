"""
回測分析工具組件

此模組提供回測系統的進階分析功能，包括：
- 參數敏感性分析
- 多策略比較分析
- 優化建議生成
- 統計顯著性檢驗
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from itertools import product
from scipy import stats
import warnings

warnings.filterwarnings("ignore")

# 導入響應式設計組件
from ..responsive import ResponsiveComponents, responsive_manager


class BacktestAnalysis:
    """回測分析工具類"""

    @staticmethod
    def parameter_sensitivity_analysis(
        strategy_func: callable,
        base_params: Dict[str, Any],
        param_ranges: Dict[str, List[Any]],
        metric: str = "total_return",
    ) -> Dict[str, Any]:
        """
        參數敏感性分析

        Args:
            strategy_func: 策略函數
            base_params: 基礎參數
            param_ranges: 參數範圍字典
            metric: 評估指標

        Returns:
            分析結果字典
        """
        results = []
        param_names = list(param_ranges.keys())

        # 網格搜尋
        if len(param_names) <= 3:
            # 完整網格搜尋
            param_combinations = list(product(*param_ranges.values()))

            for combination in param_combinations:
                params = base_params.copy()
                for i, param_name in enumerate(param_names):
                    params[param_name] = combination[i]

                try:
                    # 執行回測（這裡需要實際的策略函數）
                    result = strategy_func(**params)

                    result_dict = {
                        "params": params.copy(),
                        metric: result.get(metric, 0),
                    }

                    # 添加個別參數值
                    for param_name, value in params.items():
                        if param_name in param_names:
                            result_dict[param_name] = value

                    results.append(result_dict)

                except Exception as e:
                    st.warning(f"參數組合 {params} 執行失敗: {e}")
                    continue
        else:
            # 隨機搜尋
            n_samples = min(1000, np.prod([len(v) for v in param_ranges.values()]))

            for _ in range(n_samples):
                params = base_params.copy()
                for param_name, param_range in param_ranges.items():
                    params[param_name] = np.random.choice(param_range)

                try:
                    result = strategy_func(**params)

                    result_dict = {
                        "params": params.copy(),
                        metric: result.get(metric, 0),
                    }

                    for param_name, value in params.items():
                        if param_name in param_names:
                            result_dict[param_name] = value

                    results.append(result_dict)

                except Exception as e:
                    continue

        # 分析結果
        df = pd.DataFrame(results)

        analysis_results = {
            "results_df": df,
            "best_params": (
                df.loc[df[metric].idxmax(), "params"] if not df.empty else {}
            ),
            "best_score": df[metric].max() if not df.empty else 0,
            "param_importance": BacktestAnalysis._calculate_param_importance(
                df, param_names, metric
            ),
            "param_correlations": BacktestAnalysis._calculate_param_correlations(
                df, param_names, metric
            ),
        }

        return analysis_results

    @staticmethod
    def _calculate_param_importance(
        df: pd.DataFrame, param_names: List[str], metric: str
    ) -> Dict[str, float]:
        """計算參數重要性"""
        importance = {}

        for param_name in param_names:
            if param_name in df.columns:
                # 使用相關係數作為重要性指標
                correlation = abs(df[param_name].corr(df[metric]))
                importance[param_name] = correlation if not np.isnan(correlation) else 0

        return importance

    @staticmethod
    def _calculate_param_correlations(
        df: pd.DataFrame, param_names: List[str], metric: str
    ) -> Dict[str, float]:
        """計算參數與指標的相關性"""
        correlations = {}

        for param_name in param_names:
            if param_name in df.columns:
                correlation = df[param_name].corr(df[metric])
                correlations[param_name] = (
                    correlation if not np.isnan(correlation) else 0
                )

        return correlations

    @staticmethod
    def render_sensitivity_heatmap(
        analysis_results: Dict[str, Any],
        param1: str,
        param2: str,
        metric: str = "total_return",
    ) -> go.Figure:
        """
        渲染參數敏感性熱力圖（2D）

        Args:
            analysis_results: 分析結果
            param1: 第一個參數名稱
            param2: 第二個參數名稱
            metric: 評估指標

        Returns:
            Plotly 圖表物件
        """
        df = analysis_results["results_df"]

        # 創建透視表
        pivot_table = df.pivot_table(
            values=metric, index=param1, columns=param2, aggfunc="mean"
        )

        fig = go.Figure(
            data=go.Heatmap(
                z=pivot_table.values,
                x=pivot_table.columns,
                y=pivot_table.index,
                colorscale="RdYlGn",
                hovertemplate=f"{param1}: %{{y}}<br>{param2}: %{{x}}<br>{metric}: %{{z:.4f}}<extra></extra>",
                colorbar=dict(title=metric),
            )
        )

        height = responsive_manager.get_chart_height(500)
        fig.update_layout(
            title=f"參數敏感性分析：{param1} vs {param2}",
            xaxis_title=param2,
            yaxis_title=param1,
            height=height,
        )

        return fig

    @staticmethod
    def render_3d_surface(
        analysis_results: Dict[str, Any],
        param1: str,
        param2: str,
        metric: str = "total_return",
    ) -> go.Figure:
        """
        渲染 3D 表面圖

        Args:
            analysis_results: 分析結果
            param1: 第一個參數名稱
            param2: 第二個參數名稱
            metric: 評估指標

        Returns:
            Plotly 圖表物件
        """
        df = analysis_results["results_df"]

        # 創建透視表
        pivot_table = df.pivot_table(
            values=metric, index=param1, columns=param2, aggfunc="mean"
        )

        fig = go.Figure(
            data=[
                go.Surface(
                    z=pivot_table.values,
                    x=pivot_table.columns,
                    y=pivot_table.index,
                    colorscale="RdYlGn",
                    hovertemplate=f"{param1}: %{{y}}<br>{param2}: %{{x}}<br>{metric}: %{{z:.4f}}<extra></extra>",
                )
            ]
        )

        height = responsive_manager.get_chart_height(600)
        fig.update_layout(
            title=f"3D 參數敏感性分析：{param1} vs {param2}",
            scene=dict(xaxis_title=param2, yaxis_title=param1, zaxis_title=metric),
            height=height,
        )

        return fig

    @staticmethod
    def render_parallel_coordinates(
        analysis_results: Dict[str, Any],
        param_names: List[str],
        metric: str = "total_return",
        top_n: int = 50,
    ) -> go.Figure:
        """
        渲染平行座標圖

        Args:
            analysis_results: 分析結果
            param_names: 參數名稱列表
            metric: 評估指標
            top_n: 顯示前 N 個結果

        Returns:
            Plotly 圖表物件
        """
        df = analysis_results["results_df"]

        # 選擇前 N 個最佳結果
        top_df = df.nlargest(top_n, metric)

        # 準備平行座標圖數據
        dimensions = []

        for param_name in param_names:
            if param_name in top_df.columns:
                dimensions.append(
                    dict(
                        range=[top_df[param_name].min(), top_df[param_name].max()],
                        label=param_name,
                        values=top_df[param_name],
                    )
                )

        # 添加目標指標
        dimensions.append(
            dict(
                range=[top_df[metric].min(), top_df[metric].max()],
                label=metric,
                values=top_df[metric],
            )
        )

        fig = go.Figure(
            data=go.Parcoords(
                line=dict(
                    color=top_df[metric],
                    colorscale="RdYlGn",
                    showscale=True,
                    colorbar=dict(title=metric),
                ),
                dimensions=dimensions,
            )
        )

        height = responsive_manager.get_chart_height(500)
        fig.update_layout(title=f"參數空間分析（前 {top_n} 個結果）", height=height)

        return fig

    @staticmethod
    def compare_strategies(strategies_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        多策略比較分析

        Args:
            strategies_results: 策略結果列表

        Returns:
            比較分析結果
        """
        if not strategies_results:
            return {}

        # 準備比較數據
        comparison_data = []

        for strategy in strategies_results:
            metrics = strategy.get("metrics", {})
            comparison_data.append(
                {
                    "strategy_name": strategy.get("strategy_name", "Unknown"),
                    "total_return": metrics.get("total_return", 0),
                    "annual_return": metrics.get("annual_return", 0),
                    "sharpe_ratio": metrics.get("sharpe_ratio", 0),
                    "max_drawdown": metrics.get("max_drawdown", 0),
                    "win_rate": metrics.get("win_rate", 0),
                    "profit_factor": metrics.get("profit_factor", 0),
                    "volatility": metrics.get("volatility", 0),
                    "total_trades": metrics.get("total_trades", 0),
                }
            )

        df = pd.DataFrame(comparison_data)

        # 計算排名
        ranking_metrics = [
            "total_return",
            "annual_return",
            "sharpe_ratio",
            "win_rate",
            "profit_factor",
        ]
        penalty_metrics = ["max_drawdown", "volatility"]

        for metric in ranking_metrics:
            df[f"{metric}_rank"] = df[metric].rank(ascending=False)

        for metric in penalty_metrics:
            df[f"{metric}_rank"] = df[metric].rank(ascending=True)  # 越小越好

        # 計算綜合評分
        rank_columns = [col for col in df.columns if col.endswith("_rank")]
        df["composite_score"] = df[rank_columns].mean(axis=1)
        df["overall_rank"] = df["composite_score"].rank(ascending=True)

        # 策略相關性分析
        correlation_matrix = df[ranking_metrics + penalty_metrics].corr()

        return {
            "comparison_df": df,
            "correlation_matrix": correlation_matrix,
            "best_strategy": df.loc[df["overall_rank"].idxmin(), "strategy_name"],
            "rankings": df[
                ["strategy_name", "overall_rank"] + rank_columns
            ].sort_values("overall_rank"),
        }

    @staticmethod
    def render_strategy_comparison_radar(
        comparison_results: Dict[str, Any]
    ) -> go.Figure:
        """
        渲染策略比較雷達圖

        Args:
            comparison_results: 比較結果

        Returns:
            Plotly 圖表物件
        """
        df = comparison_results["comparison_df"]

        # 標準化指標（0-1 範圍）
        metrics_to_plot = ["total_return", "sharpe_ratio", "win_rate", "profit_factor"]
        penalty_metrics = ["max_drawdown", "volatility"]

        fig = go.Figure()

        for _, strategy in df.iterrows():
            # 正向指標（越大越好）
            values = []
            labels = []

            for metric in metrics_to_plot:
                normalized_value = (strategy[metric] - df[metric].min()) / (
                    df[metric].max() - df[metric].min()
                )
                values.append(normalized_value)
                labels.append(metric.replace("_", " ").title())

            # 負向指標（越小越好，需要反轉）
            for metric in penalty_metrics:
                normalized_value = 1 - (strategy[metric] - df[metric].min()) / (
                    df[metric].max() - df[metric].min()
                )
                values.append(normalized_value)
                labels.append(f"{metric.replace('_', ' ').title()} (反轉)")

            # 閉合雷達圖
            values.append(values[0])
            labels.append(labels[0])

            fig.add_trace(
                go.Scatterpolar(
                    r=values,
                    theta=labels,
                    fill="toself",
                    name=strategy["strategy_name"],
                    hovertemplate="%{theta}<br>標準化分數: %{r:.3f}<extra></extra>",
                )
            )

        height = responsive_manager.get_chart_height(500)
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            title="策略比較雷達圖",
            height=height,
            showlegend=True,
        )

        return fig

    @staticmethod
    def render_strategy_ranking_table(comparison_results: Dict[str, Any]) -> None:
        """
        渲染策略排名表格

        Args:
            comparison_results: 比較結果
        """
        df = comparison_results["comparison_df"]

        # 準備顯示數據
        display_df = df[
            [
                "strategy_name",
                "total_return",
                "annual_return",
                "sharpe_ratio",
                "max_drawdown",
                "win_rate",
                "profit_factor",
                "overall_rank",
            ]
        ].copy()

        # 格式化數值
        display_df["total_return"] = display_df["total_return"].apply(
            lambda x: f"{x:.2%}"
        )
        display_df["annual_return"] = display_df["annual_return"].apply(
            lambda x: f"{x:.2%}"
        )
        display_df["sharpe_ratio"] = display_df["sharpe_ratio"].apply(
            lambda x: f"{x:.3f}"
        )
        display_df["max_drawdown"] = display_df["max_drawdown"].apply(
            lambda x: f"{x:.2%}"
        )
        display_df["win_rate"] = display_df["win_rate"].apply(lambda x: f"{x:.2%}")
        display_df["profit_factor"] = display_df["profit_factor"].apply(
            lambda x: f"{x:.3f}"
        )
        display_df["overall_rank"] = display_df["overall_rank"].apply(
            lambda x: f"{int(x)}"
        )

        # 重命名列
        display_df.columns = [
            "策略名稱",
            "總回報率",
            "年化回報率",
            "夏普比率",
            "最大回撤",
            "勝率",
            "獲利因子",
            "綜合排名",
        ]

        # 按排名排序
        display_df = display_df.sort_values("綜合排名")

        # 使用響應式表格
        ResponsiveComponents.responsive_dataframe(display_df, title="策略績效排名")
