# -*- coding: utf-8 -*-
"""
回測分析模組

此模組提供回測結果的分析功能，包括：
- 績效指標計算
- 結果視覺化
- 敏感性分析
- 穩健性分析
"""

import logging
import os
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from src.config import LOG_LEVEL, RESULTS_DIR
from src.models.performance_metrics import calculate_all_metrics

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class BacktestAnalyzer:
    """
    回測分析器

    提供回測結果的分析功能。
    """

    def __init__(
        self,
        results: Dict[str, Any],
        equity_curve: Optional[pd.DataFrame] = None,
        trades: Optional[pd.DataFrame] = None,
        benchmark: Optional[pd.DataFrame] = None,
        output_dir: Optional[str] = None,
    ):
        """
        初始化回測分析器

        Args:
            results (Dict[str, Any]): 回測結果
            equity_curve (Optional[pd.DataFrame]): 權益曲線
            trades (Optional[pd.DataFrame]): 交易記錄
            benchmark (Optional[pd.DataFrame]): 基準指數
            output_dir (Optional[str]): 輸出目錄
        """
        self.results = results
        self.equity_curve = equity_curve
        self.trades = trades
        self.benchmark = benchmark
        self.output_dir = output_dir or os.path.join(
            RESULTS_DIR, "backtest_analysis", datetime.now().strftime("%Y%m%d%H%M%S")
        )

        # 創建輸出目錄
        os.makedirs(self.output_dir, exist_ok=True)

        # 計算績效指標
        self.metrics = self._calculate_metrics()

    def _calculate_metrics(self) -> Dict[str, float]:
        """
        計算績效指標

        Returns:
            Dict[str, float]: 績效指標
        """
        metrics = {}

        # 從結果中獲取基本指標
        metrics["initial_cash"] = self.results.get("initial_cash", 0.0)
        metrics["final_value"] = self.results.get("final_value", 0.0)
        metrics["total_return"] = self.results.get("total_return", 0.0)
        metrics["annual_return"] = self.results.get("annual_return", 0.0)
        metrics["sharpe_ratio"] = self.results.get("sharpe_ratio", 0.0)
        metrics["max_drawdown"] = self.results.get("max_drawdown", 0.0)
        metrics["max_drawdown_length"] = self.results.get("max_drawdown_length", 0)

        # 從交易記錄中獲取交易統計
        if "trades" in self.results:
            trades_info = self.results["trades"]
            metrics["total_trades"] = trades_info.get("total", 0)
            metrics["won_trades"] = trades_info.get("won", 0)
            metrics["lost_trades"] = trades_info.get("lost", 0)
            metrics["win_rate"] = trades_info.get("win_rate", 0.0)

            if "pnl" in trades_info:
                pnl_info = trades_info["pnl"]
                metrics["total_pnl"] = pnl_info.get("total", 0.0)
                metrics["average_pnl"] = pnl_info.get("average", 0.0)
                metrics["max_win"] = pnl_info.get("max_win", 0.0)
                metrics["max_loss"] = pnl_info.get("max_loss", 0.0)

        # 從權益曲線中計算其他指標
        if self.equity_curve is not None and "equity" in self.equity_curve.columns:
            # 計算收益率
            self.equity_curve["return"] = self.equity_curve["equity"].pct_change()

            # 計算累積收益率
            self.equity_curve["cum_return"] = (
                1 + self.equity_curve["return"]
            ).cumprod() - 1

            # 計算其他指標
            returns = self.equity_curve["return"].dropna().values

            # 使用性能指標模組計算指標
            additional_metrics = calculate_all_metrics(returns)
            metrics.update(additional_metrics)

        # 計算基準指數相對指標
        if self.benchmark is not None and "close" in self.benchmark.columns:
            # 計算基準收益率
            self.benchmark["return"] = self.benchmark["close"].pct_change()

            # 計算累積收益率
            self.benchmark["cum_return"] = (1 + self.benchmark["return"]).cumprod() - 1

            # 計算相對指標
            if self.equity_curve is not None and "return" in self.equity_curve.columns:
                # 確保日期對齊
                if (
                    "date" in self.equity_curve.columns
                    and "date" in self.benchmark.columns
                ):
                    # 合併資料
                    merged = pd.merge(
                        self.equity_curve[["date", "return"]],
                        self.benchmark[["date", "return"]],
                        on="date",
                        how="inner",
                        suffixes=("_strategy", "_benchmark"),
                    )

                    # 計算超額收益
                    merged["excess_return"] = (
                        merged["return_strategy"] - merged["return_benchmark"]
                    )

                    # 計算資訊比率
                    metrics["information_ratio"] = (
                        merged["excess_return"].mean()
                        / merged["excess_return"].std()
                        * np.sqrt(252)
                    )

                    # 計算 Beta
                    metrics["beta"] = np.cov(
                        merged["return_strategy"], merged["return_benchmark"]
                    )[0, 1] / np.var(merged["return_benchmark"])

                    # 計算 Alpha
                    metrics["alpha"] = (
                        metrics["annual_return"]
                        - 0.02
                        - metrics["beta"]
                        * (self.benchmark["return"].mean() * 252 - 0.02)
                    )

                    # 計算相關係數
                    metrics["correlation"] = np.corrcoef(
                        merged["return_strategy"], merged["return_benchmark"]
                    )[0, 1]

                    # 計算上行捕獲率和下行捕獲率
                    up_market = merged[merged["return_benchmark"] > 0]
                    down_market = merged[merged["return_benchmark"] < 0]

                    if len(up_market) > 0:
                        metrics["up_capture"] = (
                            up_market["return_strategy"].mean()
                            / up_market["return_benchmark"].mean()
                        )
                    else:
                        metrics["up_capture"] = 0.0

                    if len(down_market) > 0:
                        metrics["down_capture"] = (
                            down_market["return_strategy"].mean()
                            / down_market["return_benchmark"].mean()
                        )
                    else:
                        metrics["down_capture"] = 0.0

        return metrics

    def generate_report(self, filename: Optional[str] = None) -> str:
        """
        生成回測報告

        Args:
            filename (Optional[str]): 檔案名稱

        Returns:
            str: 報告路徑
        """
        # 設定檔案名稱
        if filename is None:
            filename = os.path.join(self.output_dir, "backtest_report.html")

        # 生成報告
        import jinja2

        # 載入模板
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))
        template = env.get_template("backtest_report.html")

        # 準備資料
        data = {
            "title": "回測報告",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "metrics": self.metrics,
            "results": self.results,
        }

        # 渲染模板
        html = template.render(**data)

        # 保存報告
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"回測報告已生成: {filename}")

        return filename

    def plot_equity_curve(self, filename: Optional[str] = None) -> str:
        """
        繪製權益曲線

        Args:
            filename (Optional[str]): 檔案名稱

        Returns:
            str: 圖表路徑
        """
        if self.equity_curve is None:
            logger.error("沒有權益曲線資料")
            raise ValueError("沒有權益曲線資料")

        # 設定檔案名稱
        if filename is None:
            filename = os.path.join(self.output_dir, "equity_curve.png")

        # 繪製權益曲線
        plt.figure(figsize=(12, 6))

        # 繪製策略權益曲線
        plt.plot(self.equity_curve["date"], self.equity_curve["equity"], label="策略")

        # 繪製基準指數
        if (
            self.benchmark is not None
            and "close" in self.benchmark.columns
            and "date" in self.benchmark.columns
        ):
            # 將基準指數標準化為與策略起始資金相同
            benchmark_equity = (
                self.benchmark["close"]
                / self.benchmark["close"].iloc[0]
                * self.metrics["initial_cash"]
            )
            plt.plot(
                self.benchmark["date"], benchmark_equity, label="基準指數", alpha=0.7
            )

        # 設定圖表
        plt.title("權益曲線")
        plt.xlabel("日期")
        plt.ylabel("權益")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()

        # 保存圖表
        plt.savefig(filename)
        plt.close()

        logger.info(f"權益曲線已繪製: {filename}")

        return filename

    def plot_drawdown(self, filename: Optional[str] = None) -> str:
        """
        繪製回撤圖

        Args:
            filename (Optional[str]): 檔案名稱

        Returns:
            str: 圖表路徑
        """
        if self.equity_curve is None:
            logger.error("沒有權益曲線資料")
            raise ValueError("沒有權益曲線資料")

        # 設定檔案名稱
        if filename is None:
            filename = os.path.join(self.output_dir, "drawdown.png")

        # 計算回撤
        equity = self.equity_curve["equity"].values
        max_equity = np.maximum.accumulate(equity)
        drawdown = (equity - max_equity) / max_equity

        # 添加回撤到權益曲線
        self.equity_curve["drawdown"] = drawdown

        # 繪製回撤圖
        plt.figure(figsize=(12, 6))
        plt.plot(self.equity_curve["date"], self.equity_curve["drawdown"] * 100)
        plt.fill_between(
            self.equity_curve["date"],
            self.equity_curve["drawdown"] * 100,
            0,
            alpha=0.3,
            color="red",
        )

        # 設定圖表
        plt.title("回撤圖")
        plt.xlabel("日期")
        plt.ylabel("回撤 (%)")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        # 保存圖表
        plt.savefig(filename)
        plt.close()

        logger.info(f"回撤圖已繪製: {filename}")

        return filename

    def plot_monthly_returns(self, filename: Optional[str] = None) -> str:
        """
        繪製月度收益熱圖

        Args:
            filename (Optional[str]): 檔案名稱

        Returns:
            str: 圖表路徑
        """
        if self.equity_curve is None:
            logger.error("沒有權益曲線資料")
            raise ValueError("沒有權益曲線資料")

        # 設定檔案名稱
        if filename is None:
            filename = os.path.join(self.output_dir, "monthly_returns.png")

        # 確保日期欄位為 datetime 類型
        if "date" in self.equity_curve.columns:
            self.equity_curve["date"] = pd.to_datetime(self.equity_curve["date"])

        # 計算月度收益
        self.equity_curve["year"] = self.equity_curve["date"].dt.year
        self.equity_curve["month"] = self.equity_curve["date"].dt.month

        # 計算每月最後一天的權益
        monthly_equity = (
            self.equity_curve.groupby(["year", "month"])["equity"].last().reset_index()
        )

        # 計算月度收益率
        monthly_equity["monthly_return"] = monthly_equity["equity"].pct_change()

        # 創建月度收益熱圖資料
        heatmap_data = monthly_equity.pivot_table(
            index="month", columns="year", values="monthly_return"
        )

        # 繪製月度收益熱圖
        plt.figure(figsize=(12, 8))
        sns.heatmap(
            heatmap_data * 100,
            annot=True,
            fmt=".2f",
            cmap="RdYlGn",
            center=0,
            linewidths=1,
            cbar_kws={"label": "月度收益率 (%)"},
        )

        # 設定圖表
        plt.title("月度收益熱圖")
        plt.xlabel("年份")
        plt.ylabel("月份")
        plt.tight_layout()

        # 保存圖表
        plt.savefig(filename)
        plt.close()

        logger.info(f"月度收益熱圖已繪製: {filename}")

        return filename

    def plot_trade_analysis(self, filename: Optional[str] = None) -> str:
        """
        繪製交易分析圖

        Args:
            filename (Optional[str]): 檔案名稱

        Returns:
            str: 圖表路徑
        """
        if self.trades is None:
            logger.error("沒有交易記錄資料")
            raise ValueError("沒有交易記錄資料")

        # 設定檔案名稱
        if filename is None:
            filename = os.path.join(self.output_dir, "trade_analysis.png")

        # 繪製交易分析圖
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # 繪製交易盈虧分佈
        if "pnl" in self.trades.columns:
            sns.histplot(self.trades["pnl"], kde=True, ax=axes[0, 0])
            axes[0, 0].set_title("交易盈虧分佈")
            axes[0, 0].set_xlabel("盈虧")
            axes[0, 0].set_ylabel("頻率")
            axes[0, 0].axvline(0, color="red", linestyle="--")

        # 繪製交易持倉時間分佈
        if "duration" in self.trades.columns:
            sns.histplot(self.trades["duration"], kde=True, ax=axes[0, 1])
            axes[0, 1].set_title("交易持倉時間分佈")
            axes[0, 1].set_xlabel("持倉時間（天）")
            axes[0, 1].set_ylabel("頻率")

        # 繪製交易盈虧與持倉時間關係
        if "pnl" in self.trades.columns and "duration" in self.trades.columns:
            sns.scatterplot(x="duration", y="pnl", data=self.trades, ax=axes[1, 0])
            axes[1, 0].set_title("交易盈虧與持倉時間關係")
            axes[1, 0].set_xlabel("持倉時間（天）")
            axes[1, 0].set_ylabel("盈虧")
            axes[1, 0].axhline(0, color="red", linestyle="--")

        # 繪製交易盈虧累積曲線
        if "pnl" in self.trades.columns and "exit_date" in self.trades.columns:
            # 確保日期欄位為 datetime 類型
            self.trades["exit_date"] = pd.to_datetime(self.trades["exit_date"])

            # 按日期排序
            sorted_trades = self.trades.sort_values("exit_date")

            # 計算累積盈虧
            sorted_trades["cum_pnl"] = sorted_trades["pnl"].cumsum()

            # 繪製累積盈虧曲線
            axes[1, 1].plot(sorted_trades["exit_date"], sorted_trades["cum_pnl"])
            axes[1, 1].set_title("交易盈虧累積曲線")
            axes[1, 1].set_xlabel("日期")
            axes[1, 1].set_ylabel("累積盈虧")
            axes[1, 1].grid(True, alpha=0.3)

        # 設定圖表
        plt.tight_layout()

        # 保存圖表
        plt.savefig(filename)
        plt.close()

        logger.info(f"交易分析圖已繪製: {filename}")

        return filename

    def perform_sensitivity_analysis(
        self,
        parameter_name: str,
        parameter_values: List[Any],
        backtest_func: Callable,
        metric_name: str = "sharpe_ratio",
        filename: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, str]:
        """
        執行敏感性分析

        Args:
            parameter_name (str): 參數名稱
            parameter_values (List[Any]): 參數值列表
            backtest_func (Callable): 回測函數，接受參數值，返回回測結果
            metric_name (str): 指標名稱
            filename (Optional[str]): 檔案名稱

        Returns:
            Tuple[pd.DataFrame, str]: 敏感性分析結果和圖表路徑
        """
        # 設定檔案名稱
        if filename is None:
            filename = os.path.join(
                self.output_dir, f"sensitivity_{parameter_name}.png"
            )

        # 執行敏感性分析
        results = []

        for value in parameter_values:
            # 執行回測
            result = backtest_func(value)

            # 獲取指標值
            metric_value = result.get(metric_name, 0.0)

            # 記錄結果
            results.append({"parameter_value": value, "metric_value": metric_value})

        # 創建結果資料框
        sensitivity_df = pd.DataFrame(results)

        # 繪製敏感性分析圖
        plt.figure(figsize=(10, 6))
        plt.plot(
            sensitivity_df["parameter_value"],
            sensitivity_df["metric_value"],
            marker="o",
        )

        # 設定圖表
        plt.title(f"{parameter_name} 敏感性分析")
        plt.xlabel(parameter_name)
        plt.ylabel(metric_name)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        # 保存圖表
        plt.savefig(filename)
        plt.close()

        logger.info(f"敏感性分析已完成: {filename}")

        return sensitivity_df, filename

    def perform_robustness_analysis(
        self,
        backtest_func: Callable,
        num_simulations: int = 100,
        metric_name: str = "sharpe_ratio",
        filename: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, str]:
        """
        執行穩健性分析

        Args:
            backtest_func (Callable): 回測函數，返回回測結果
            num_simulations (int): 模擬次數
            metric_name (str): 指標名稱
            filename (Optional[str]): 檔案名稱

        Returns:
            Tuple[pd.DataFrame, str]: 穩健性分析結果和圖表路徑
        """
        # 設定檔案名稱
        if filename is None:
            filename = os.path.join(self.output_dir, f"robustness_{metric_name}.png")

        # 執行穩健性分析
        results = []

        for i in range(num_simulations):
            # 執行回測
            result = backtest_func()

            # 獲取指標值
            metric_value = result.get(metric_name, 0.0)

            # 記錄結果
            results.append({"simulation": i + 1, "metric_value": metric_value})

        # 創建結果資料框
        robustness_df = pd.DataFrame(results)

        # 計算統計量
        mean = robustness_df["metric_value"].mean()
        std = robustness_df["metric_value"].std()
        median = robustness_df["metric_value"].median()
        min_value = robustness_df["metric_value"].min()
        max_value = robustness_df["metric_value"].max()

        # 繪製穩健性分析圖
        plt.figure(figsize=(10, 6))
        sns.histplot(robustness_df["metric_value"], kde=True)

        # 添加統計量
        plt.axvline(mean, color="red", linestyle="--", label=f"平均值: {mean:.4f}")
        plt.axvline(
            median, color="green", linestyle="-.", label=f"中位數: {median:.4f}"
        )
        plt.axvline(
            mean - std,
            color="orange",
            linestyle=":",
            label=f"平均值 - 標準差: {mean - std:.4f}",
        )
        plt.axvline(
            mean + std,
            color="orange",
            linestyle=":",
            label=f"平均值 + 標準差: {mean + std:.4f}",
        )

        # 設定圖表
        plt.title(f"{metric_name} 穩健性分析")
        plt.xlabel(metric_name)
        plt.ylabel("頻率")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        # 保存圖表
        plt.savefig(filename)
        plt.close()

        logger.info(f"穩健性分析已完成: {filename}")

        # 添加統計量到結果
        robustness_df.attrs["mean"] = mean
        robustness_df.attrs["std"] = std
        robustness_df.attrs["median"] = median
        robustness_df.attrs["min"] = min_value
        robustness_df.attrs["max"] = max_value

        return robustness_df, filename
