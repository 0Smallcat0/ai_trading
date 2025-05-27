"""
增強版回測系統測試 - 完整合併版本

此模組測試回測系統的所有功能，包括：
- 回測圖表組件測試（基礎和詳細）
- 報告生成測試（基礎和驗證）
- 分析工具測試（基礎和算法）
- 響應式整合測試
- 效能和記憶體測試

合併自：
- test_backtest_enhanced.py（基礎測試）
- test_backtest_components.py（詳細測試）
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import io
from typing import Dict, List, Any

# 導入要測試的模組
from src.ui.components.backtest_charts import BacktestCharts
from src.ui.components.backtest_reports import BacktestReports
from src.ui.components.backtest_analysis import BacktestAnalysis
from src.ui.pages.backtest_enhanced import generate_mock_backtest_results


class TestBacktestCharts:
    """測試回測圖表組件"""

    def setup_method(self):
        """設置測試環境"""
        # 創建模擬數據
        dates = pd.date_range(start="2024-01-01", end="2024-01-31", freq="D")
        self.portfolio_data = pd.DataFrame(
            {
                "date": dates,
                "portfolio_value": 1000000
                + np.cumsum(np.random.randn(len(dates)) * 1000),
                "daily_return": np.random.randn(len(dates)) * 0.01,
                "cumulative_return": np.cumsum(np.random.randn(len(dates)) * 0.01),
                "drawdown": -np.abs(np.random.randn(len(dates)) * 0.05),
            }
        )

        self.transactions_data = pd.DataFrame(
            {
                "date": pd.date_range(start="2024-01-01", periods=20, freq="D"),
                "action": ["buy", "sell"] * 10,
                "symbol": ["AAPL"] * 20,
                "quantity": [100] * 20,
                "price": np.random.uniform(150, 200, 20),
            }
        )

        self.positions_data = pd.DataFrame(
            {"symbol": ["AAPL", "MSFT", "GOOGL"], "holding_days": [10, 25, 45]}
        )

    def test_cumulative_returns_chart(self):
        """測試累積收益率圖表"""
        fig = BacktestCharts.cumulative_returns_chart(self.portfolio_data)

        assert fig is not None
        assert len(fig.data) >= 1  # 至少有一條線
        assert fig.layout.title.text == "累積收益率曲線"
        assert fig.layout.xaxis.title.text == "日期"
        assert fig.layout.yaxis.title.text == "累積收益率 (%)"

    def test_cumulative_returns_chart_with_benchmark(self):
        """測試帶基準的累積收益率圖表"""
        benchmark_data = self.portfolio_data.copy()
        benchmark_data["cumulative_return"] *= 0.8  # 模擬基準表現較差

        fig = BacktestCharts.cumulative_returns_chart(
            self.portfolio_data, benchmark_data
        )

        assert fig is not None
        assert len(fig.data) == 2  # 投資組合 + 基準

    def test_drawdown_chart(self):
        """測試回撤分析圖表"""
        fig = BacktestCharts.drawdown_chart(self.portfolio_data)

        assert fig is not None
        assert len(fig.data) == 2  # 投資組合價值 + 回撤
        assert fig.layout.title.text == "回撤分析圖"

    def test_rolling_sharpe_chart(self):
        """測試滾動夏普比率圖表"""
        fig = BacktestCharts.rolling_sharpe_chart(self.portfolio_data, window=10)

        assert fig is not None
        assert len(fig.data) >= 1
        assert fig.layout.title.text == "滾動夏普比率"

    def test_monthly_returns_heatmap(self):
        """測試月度收益熱力圖"""
        # 創建更長的數據以包含多個月份
        dates = pd.date_range(start="2024-01-01", end="2024-06-30", freq="D")
        extended_data = pd.DataFrame(
            {"date": dates, "daily_return": np.random.randn(len(dates)) * 0.01}
        )

        fig = BacktestCharts.monthly_returns_heatmap(extended_data)

        assert fig is not None
        assert fig.layout.title.text == "月度收益熱力圖"

    def test_returns_distribution_chart(self):
        """測試收益分佈直方圖"""
        fig = BacktestCharts.returns_distribution_chart(self.portfolio_data)

        assert fig is not None
        assert len(fig.data) >= 1
        assert fig.layout.title.text == "收益分佈直方圖"

    def test_risk_return_scatter(self):
        """測試風險收益散點圖"""
        strategies_data = [
            {"name": "策略A", "annual_return": 0.15, "volatility": 0.12},
            {"name": "策略B", "annual_return": 0.10, "volatility": 0.08},
            {"name": "策略C", "annual_return": 0.20, "volatility": 0.18},
        ]

        fig = BacktestCharts.risk_return_scatter(strategies_data)

        assert fig is not None
        assert len(fig.data) == len(strategies_data)
        assert fig.layout.title.text == "風險收益散點圖"

    def test_trading_frequency_chart(self):
        """測試交易頻率分析圖"""
        fig = BacktestCharts.trading_frequency_chart(self.transactions_data)

        assert fig is not None
        assert fig.layout.title.text == "交易頻率分析"

    def test_holding_period_chart(self):
        """測試持倉時間分析圖"""
        fig = BacktestCharts.holding_period_chart(self.positions_data)

        assert fig is not None
        assert fig.layout.title.text == "持倉時間分析"

    @patch("streamlit.plotly_chart")
    @patch("streamlit.columns")
    def test_render_performance_charts(self, mock_columns, mock_plotly_chart):
        """測試渲染效能分析圖表"""
        mock_columns.return_value = [Mock(), Mock()]

        backtest_results = {
            "portfolio_data": self.portfolio_data.to_dict("records"),
            "transactions": self.transactions_data.to_dict("records"),
            "positions": self.positions_data.to_dict("records"),
        }

        BacktestCharts.render_performance_charts(backtest_results)

        # 驗證圖表被渲染
        assert mock_plotly_chart.call_count > 0


class TestBacktestReports:
    """測試回測報告組件"""

    def setup_method(self):
        """設置測試環境"""
        self.reports = BacktestReports()
        self.backtest_results = {
            "strategy_name": "測試策略",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "initial_capital": 1000000,
            "final_capital": 1100000,
            "metrics": {
                "total_return": 0.10,
                "annual_return": 0.12,
                "sharpe_ratio": 1.5,
                "max_drawdown": -0.05,
                "win_rate": 0.65,
                "profit_factor": 1.8,
                "total_trades": 50,
                "avg_trade_return": 0.002,
                "volatility": 0.08,
            },
            "transactions": [
                {
                    "date": "2024-01-15",
                    "symbol": "AAPL",
                    "action": "buy",
                    "quantity": 100,
                    "price": 150.0,
                    "amount": 15000,
                }
            ],
        }

    def test_check_dependencies(self):
        """測試依賴項檢查"""
        dependencies = BacktestReports.check_dependencies()

        assert isinstance(dependencies, dict)
        assert "reportlab" in dependencies
        assert "xlsxwriter" in dependencies
        assert "jinja2" in dependencies
        assert all(isinstance(v, bool) for v in dependencies.values())

    @patch("src.ui.components.backtest_reports.REPORTLAB_AVAILABLE", True)
    def test_generate_pdf_report(self):
        """測試 PDF 報告生成"""
        try:
            pdf_data = self.reports.generate_pdf_report(self.backtest_results)

            assert isinstance(pdf_data, bytes)
            assert len(pdf_data) > 0
            assert pdf_data.startswith(b"%PDF")  # PDF 文件標識
        except ImportError:
            pytest.skip("reportlab 未安裝")

    @patch("src.ui.components.backtest_reports.XLSXWRITER_AVAILABLE", True)
    def test_generate_excel_report(self):
        """測試 Excel 報告生成"""
        try:
            excel_data = self.reports.generate_excel_report(self.backtest_results)

            assert isinstance(excel_data, bytes)
            assert len(excel_data) > 0
        except ImportError:
            pytest.skip("xlsxwriter 未安裝")

    @patch("src.ui.components.backtest_reports.JINJA2_AVAILABLE", True)
    def test_generate_html_report(self):
        """測試 HTML 報告生成"""
        try:
            html_data = self.reports.generate_html_report(self.backtest_results)

            assert isinstance(html_data, str)
            assert len(html_data) > 0
            assert "<!DOCTYPE html>" in html_data
            assert "測試策略" in html_data
        except ImportError:
            pytest.skip("jinja2 未安裝")


class TestBacktestAnalysis:
    """測試回測分析工具"""

    def setup_method(self):
        """設置測試環境"""
        self.strategies_results = [
            {
                "strategy_name": "策略A",
                "metrics": {
                    "total_return": 0.15,
                    "annual_return": 0.18,
                    "sharpe_ratio": 1.8,
                    "max_drawdown": -0.08,
                    "win_rate": 0.70,
                    "profit_factor": 2.1,
                    "volatility": 0.10,
                    "total_trades": 100,
                },
            },
            {
                "strategy_name": "策略B",
                "metrics": {
                    "total_return": 0.12,
                    "annual_return": 0.14,
                    "sharpe_ratio": 1.5,
                    "max_drawdown": -0.06,
                    "win_rate": 0.65,
                    "profit_factor": 1.8,
                    "volatility": 0.09,
                    "total_trades": 80,
                },
            },
        ]

    def test_compare_strategies(self):
        """測試策略比較分析"""
        comparison_results = BacktestAnalysis.compare_strategies(
            self.strategies_results
        )

        assert isinstance(comparison_results, dict)
        assert "comparison_df" in comparison_results
        assert "correlation_matrix" in comparison_results
        assert "best_strategy" in comparison_results
        assert "rankings" in comparison_results

        # 檢查比較數據框
        df = comparison_results["comparison_df"]
        assert len(df) == 2
        assert "strategy_name" in df.columns
        assert "overall_rank" in df.columns

    def test_compare_strategies_empty(self):
        """測試空策略列表的比較"""
        comparison_results = BacktestAnalysis.compare_strategies([])

        assert comparison_results == {}

    def test_render_strategy_comparison_radar(self):
        """測試策略比較雷達圖"""
        comparison_results = BacktestAnalysis.compare_strategies(
            self.strategies_results
        )

        fig = BacktestAnalysis.render_strategy_comparison_radar(comparison_results)

        assert fig is not None
        assert len(fig.data) == 2  # 兩個策略
        assert fig.layout.title.text == "策略比較雷達圖"

    @patch("streamlit.dataframe")
    def test_render_strategy_ranking_table(self, mock_dataframe):
        """測試策略排名表格渲染"""
        comparison_results = BacktestAnalysis.compare_strategies(
            self.strategies_results
        )

        BacktestAnalysis.render_strategy_ranking_table(comparison_results)

        # 驗證表格被渲染
        mock_dataframe.assert_called()


class TestBacktestEnhanced:
    """測試增強版回測頁面"""

    def test_generate_mock_backtest_results(self):
        """測試模擬回測結果生成"""
        config = {
            "strategy_name": "測試策略",
            "symbols": ["AAPL", "MSFT"],
            "start_date": datetime(2024, 1, 1),
            "end_date": datetime(2024, 1, 31),
            "initial_capital": 1000000,
        }

        results = generate_mock_backtest_results(config)

        assert isinstance(results, dict)
        assert "strategy_name" in results
        assert "portfolio_data" in results
        assert "transactions" in results
        assert "metrics" in results

        # 檢查投資組合數據
        portfolio_data = results["portfolio_data"]
        assert len(portfolio_data) > 0
        assert all("date" in item for item in portfolio_data)
        assert all("portfolio_value" in item for item in portfolio_data)

        # 檢查指標
        metrics = results["metrics"]
        assert "total_return" in metrics
        assert "sharpe_ratio" in metrics
        assert "max_drawdown" in metrics

        # 檢查交易記錄
        transactions = results["transactions"]
        assert len(transactions) > 0
        assert all("date" in trans for trans in transactions)
        assert all("symbol" in trans for trans in transactions)


class TestIntegration:
    """整合測試"""

    @patch(
        "streamlit.session_state", {"backtest_results": {}, "strategies_results": []}
    )
    def test_backtest_workflow(self):
        """測試完整的回測工作流程"""
        # 模擬回測配置
        config = {
            "strategy_name": "整合測試策略",
            "symbols": ["AAPL"],
            "start_date": datetime(2024, 1, 1),
            "end_date": datetime(2024, 1, 31),
            "initial_capital": 1000000,
        }

        # 生成回測結果
        results = generate_mock_backtest_results(config)

        # 測試圖表生成
        portfolio_data = pd.DataFrame(results["portfolio_data"])
        fig = BacktestCharts.cumulative_returns_chart(portfolio_data)
        assert fig is not None

        # 測試報告生成
        reports = BacktestReports()
        try:
            html_report = reports.generate_html_report(results)
            assert isinstance(html_report, str)
            assert len(html_report) > 0
        except ImportError:
            pass  # 跳過如果依賴項未安裝

        # 測試策略比較
        strategies_list = [results]
        comparison_results = BacktestAnalysis.compare_strategies(strategies_list)
        # 單個策略無法比較，應該返回有效結果但比較功能有限
        assert isinstance(comparison_results, dict)


# ===== 以下是從 test_backtest_components.py 合併的詳細測試 =====


class TestBacktestChartsDetailed:
    """詳細測試回測圖表組件"""

    def setup_method(self):
        """設置測試數據"""
        # 創建更真實的測試數據
        np.random.seed(42)  # 確保測試結果可重現

        dates = pd.date_range(start="2024-01-01", end="2024-12-31", freq="D")
        n_days = len(dates)

        # 模擬股價走勢
        daily_returns = np.random.normal(0.0008, 0.015, n_days)  # 年化8%收益，15%波動
        cumulative_returns = np.cumprod(1 + daily_returns) - 1
        portfolio_values = 1000000 * (1 + cumulative_returns)

        # 計算回撤
        peak = np.maximum.accumulate(portfolio_values)
        drawdown = (portfolio_values - peak) / peak

        self.portfolio_data = pd.DataFrame(
            {
                "date": dates,
                "portfolio_value": portfolio_values,
                "daily_return": daily_returns,
                "cumulative_return": cumulative_returns,
                "drawdown": drawdown,
            }
        )

        # 創建交易數據
        n_trades = 100
        trade_dates = np.random.choice(dates, n_trades)
        self.transactions_data = pd.DataFrame(
            {
                "date": trade_dates,
                "action": np.random.choice(["buy", "sell"], n_trades),
                "symbol": np.random.choice(["AAPL", "MSFT", "GOOGL"], n_trades),
                "quantity": np.random.randint(50, 500, n_trades),
                "price": np.random.uniform(100, 300, n_trades),
            }
        )

        # 創建持倉數據
        self.positions_data = pd.DataFrame(
            {
                "symbol": ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"],
                "holding_days": [5, 15, 45, 120, 300],
            }
        )

    def test_chart_data_validation(self):
        """測試圖表數據驗證"""
        # 測試空數據
        empty_df = pd.DataFrame()

        # 應該能處理空數據而不崩潰
        try:
            fig = BacktestCharts.cumulative_returns_chart(empty_df)
            # 如果沒有拋出異常，檢查圖表是否有效
            assert fig is not None
        except (KeyError, IndexError):
            # 預期的錯誤，因為缺少必要的列
            pass

    def test_chart_responsiveness(self):
        """測試圖表響應式特性"""
        with patch(
            "src.ui.components.backtest_charts.responsive_manager"
        ) as mock_manager:
            mock_manager.get_chart_height.return_value = 300

            fig = BacktestCharts.cumulative_returns_chart(self.portfolio_data)

            # 驗證響應式高度被應用
            mock_manager.get_chart_height.assert_called()
            assert fig.layout.height == 300

    def test_heatmap_data_structure(self):
        """測試熱力圖數據結構"""
        fig = BacktestCharts.monthly_returns_heatmap(self.portfolio_data)

        # 檢查熱力圖數據
        assert len(fig.data) == 1
        heatmap_data = fig.data[0]
        assert hasattr(heatmap_data, "z")  # 熱力圖數據
        assert hasattr(heatmap_data, "x")  # x軸（月份）
        assert hasattr(heatmap_data, "y")  # y軸（年份）

    def test_distribution_statistics(self):
        """測試收益分佈統計"""
        fig = BacktestCharts.returns_distribution_chart(self.portfolio_data)

        # 檢查是否包含統計線
        assert len(fig.layout.shapes) >= 3  # 平均值 + 標準差線

        # 檢查註釋
        annotations = fig.layout.annotations
        assert len(annotations) >= 3  # 平均值、+1σ、-1σ標註

    def test_risk_return_scatter_calculations(self):
        """測試風險收益散點圖計算"""
        strategies_data = [
            {"name": "低風險策略", "annual_return": 0.08, "volatility": 0.05},
            {"name": "中風險策略", "annual_return": 0.12, "volatility": 0.10},
            {"name": "高風險策略", "annual_return": 0.18, "volatility": 0.20},
        ]

        fig = BacktestCharts.risk_return_scatter(strategies_data)

        # 檢查每個策略都有對應的點
        assert len(fig.data) == len(strategies_data)

        # 檢查數據點的位置
        for i, strategy in enumerate(strategies_data):
            trace = fig.data[i]
            assert trace.x[0] == strategy["volatility"] * 100  # 轉換為百分比
            assert trace.y[0] == strategy["annual_return"] * 100


class TestBacktestReportsValidation:
    """測試回測報告驗證"""

    def setup_method(self):
        """設置測試環境"""
        self.reports = BacktestReports()
        self.sample_results = {
            "strategy_name": "測試策略",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "initial_capital": 1000000,
            "final_capital": 1150000,
            "metrics": {
                "total_return": 0.15,
                "annual_return": 0.15,
                "sharpe_ratio": 1.8,
                "max_drawdown": -0.08,
                "win_rate": 0.68,
                "profit_factor": 2.2,
                "total_trades": 150,
                "avg_trade_return": 0.001,
                "volatility": 0.12,
            },
            "transactions": [
                {
                    "date": "2024-01-15",
                    "symbol": "AAPL",
                    "action": "buy",
                    "quantity": 100,
                    "price": 150.0,
                    "amount": 15000,
                },
                {
                    "date": "2024-01-20",
                    "symbol": "AAPL",
                    "action": "sell",
                    "quantity": 100,
                    "price": 155.0,
                    "amount": 15500,
                },
            ],
        }

    @patch("src.ui.components.backtest_reports.JINJA2_AVAILABLE", True)
    def test_html_report_structure(self):
        """測試 HTML 報告結構"""
        try:
            html_content = self.reports.generate_html_report(self.sample_results)

            # 檢查 HTML 基本結構
            assert "<!DOCTYPE html>" in html_content
            assert '<html lang="zh-TW">' in html_content
            assert "<head>" in html_content
            assert "<body>" in html_content

            # 檢查內容
            assert "測試策略" in html_content
            assert "2024-01-01" in html_content
            assert "1,000,000" in html_content

            # 檢查響應式設計
            assert "@media (max-width: 768px)" in html_content

        except ImportError:
            pytest.skip("jinja2 未安裝")

    @patch("src.ui.components.backtest_reports.XLSXWRITER_AVAILABLE", True)
    def test_excel_report_worksheets(self):
        """測試 Excel 報告工作表"""
        try:
            excel_data = self.reports.generate_excel_report(self.sample_results)

            # 檢查是否生成了有效的 Excel 數據
            assert isinstance(excel_data, bytes)
            assert len(excel_data) > 1000  # 應該有一定的文件大小

            # 可以進一步使用 openpyxl 檢查工作表內容
            # 但這需要額外的依賴項

        except ImportError:
            pytest.skip("xlsxwriter 未安裝")

    def test_report_error_handling(self):
        """測試報告生成錯誤處理"""
        # 測試缺少必要數據的情況
        incomplete_results = {
            "strategy_name": "不完整策略"
            # 缺少其他必要字段
        }

        try:
            html_content = self.reports.generate_html_report(incomplete_results)
            # 應該能處理缺少的字段，使用默認值
            assert "N/A" in html_content or "不完整策略" in html_content
        except ImportError:
            pytest.skip("jinja2 未安裝")


class TestBacktestAnalysisAlgorithms:
    """測試回測分析算法"""

    def setup_method(self):
        """設置測試數據"""
        self.strategies_data = [
            {
                "strategy_name": "策略A",
                "metrics": {
                    "total_return": 0.20,
                    "annual_return": 0.18,
                    "sharpe_ratio": 2.1,
                    "max_drawdown": -0.10,
                    "win_rate": 0.75,
                    "profit_factor": 2.5,
                    "volatility": 0.08,
                    "total_trades": 120,
                },
            },
            {
                "strategy_name": "策略B",
                "metrics": {
                    "total_return": 0.15,
                    "annual_return": 0.14,
                    "sharpe_ratio": 1.8,
                    "max_drawdown": -0.06,
                    "win_rate": 0.70,
                    "profit_factor": 2.0,
                    "volatility": 0.07,
                    "total_trades": 100,
                },
            },
            {
                "strategy_name": "策略C",
                "metrics": {
                    "total_return": 0.25,
                    "annual_return": 0.22,
                    "sharpe_ratio": 1.5,
                    "max_drawdown": -0.15,
                    "win_rate": 0.65,
                    "profit_factor": 1.8,
                    "volatility": 0.15,
                    "total_trades": 80,
                },
            },
        ]

    def test_strategy_ranking_algorithm(self):
        """測試策略排名算法"""
        comparison_results = BacktestAnalysis.compare_strategies(self.strategies_data)

        df = comparison_results["comparison_df"]

        # 檢查排名列是否存在
        rank_columns = [col for col in df.columns if col.endswith("_rank")]
        assert len(rank_columns) > 0

        # 檢查綜合評分
        assert "composite_score" in df.columns
        assert "overall_rank" in df.columns

        # 檢查排名的合理性（排名應該在1到策略數量之間）
        assert df["overall_rank"].min() >= 1
        assert df["overall_rank"].max() <= len(self.strategies_data)

        # 檢查最佳策略
        best_strategy = comparison_results["best_strategy"]
        assert best_strategy in [s["strategy_name"] for s in self.strategies_data]

    def test_correlation_calculation(self):
        """測試相關性計算"""
        comparison_results = BacktestAnalysis.compare_strategies(self.strategies_data)

        correlation_matrix = comparison_results["correlation_matrix"]

        # 檢查相關性矩陣的屬性
        assert isinstance(correlation_matrix, pd.DataFrame)
        assert correlation_matrix.shape[0] == correlation_matrix.shape[1]  # 方陣

        # 檢查對角線元素為1（自相關）
        diagonal_values = np.diag(correlation_matrix.values)
        assert np.allclose(diagonal_values, 1.0, atol=1e-10)

        # 檢查矩陣對稱性
        assert np.allclose(
            correlation_matrix.values, correlation_matrix.values.T, atol=1e-10
        )

    def test_parameter_importance_calculation(self):
        """測試參數重要性計算"""
        # 創建模擬的參數分析數據
        np.random.seed(42)
        n_samples = 100

        df = pd.DataFrame(
            {
                "param1": np.random.uniform(5, 20, n_samples),
                "param2": np.random.uniform(0.01, 0.1, n_samples),
                "param3": np.random.uniform(0.5, 2.0, n_samples),
                "total_return": np.random.uniform(-0.1, 0.3, n_samples),
            }
        )

        # 添加一些相關性
        df["total_return"] += 0.01 * df["param1"]  # param1 與收益正相關
        df["total_return"] -= 0.5 * df["param2"]  # param2 與收益負相關

        param_names = ["param1", "param2", "param3"]
        importance = BacktestAnalysis._calculate_param_importance(
            df, param_names, "total_return"
        )

        # 檢查重要性計算結果
        assert isinstance(importance, dict)
        assert len(importance) == len(param_names)

        # 檢查重要性值在合理範圍內
        for param, imp in importance.items():
            assert 0 <= imp <= 1

        # param1 應該比 param3 更重要（因為我們添加了相關性）
        assert importance["param1"] > importance["param3"]

    def test_radar_chart_normalization(self):
        """測試雷達圖數據標準化"""
        comparison_results = BacktestAnalysis.compare_strategies(self.strategies_data)

        fig = BacktestAnalysis.render_strategy_comparison_radar(comparison_results)

        # 檢查雷達圖數據
        assert len(fig.data) == len(self.strategies_data)

        # 檢查數據標準化（所有值應該在0-1之間）
        for trace in fig.data:
            values = trace.r[:-1]  # 排除最後一個重複值（用於閉合圖形）
            assert all(0 <= v <= 1 for v in values)


class TestResponsiveIntegration:
    """測試響應式整合"""

    @patch("src.ui.components.backtest_charts.responsive_manager")
    def test_responsive_chart_heights(self, mock_manager):
        """測試響應式圖表高度"""
        # 模擬不同設備的高度
        test_heights = [300, 350, 400]  # 手機、平板、桌面

        for height in test_heights:
            mock_manager.get_chart_height.return_value = height

            portfolio_data = pd.DataFrame(
                {
                    "date": pd.date_range("2024-01-01", periods=10),
                    "cumulative_return": np.random.randn(10) * 0.01,
                }
            )

            fig = BacktestCharts.cumulative_returns_chart(portfolio_data)

            assert fig.layout.height == height

    @patch("src.ui.components.backtest_charts.responsive_manager")
    def test_responsive_column_layout(self, mock_manager):
        """測試響應式列佈局"""
        mock_columns = [Mock(), Mock()]
        mock_manager.create_responsive_columns.return_value = mock_columns

        backtest_results = {"portfolio_data": [], "transactions": [], "positions": []}

        with patch("streamlit.plotly_chart"):
            BacktestCharts.render_performance_charts(backtest_results)

            # 驗證響應式列被創建
            mock_manager.create_responsive_columns.assert_called()


class TestPerformanceAndMemory:
    """測試效能和記憶體使用"""

    def test_large_dataset_handling(self):
        """測試大數據集處理"""
        # 創建大數據集（模擬1年的分鐘級數據）
        n_points = 365 * 24 * 60  # 約50萬個數據點

        large_data = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=n_points, freq="T"),
                "daily_return": np.random.randn(n_points) * 0.001,
                "cumulative_return": np.cumsum(np.random.randn(n_points) * 0.001),
            }
        )

        # 測試圖表生成是否能處理大數據集
        try:
            fig = BacktestCharts.cumulative_returns_chart(large_data)
            assert fig is not None
            assert len(fig.data) > 0
        except MemoryError:
            pytest.skip("記憶體不足以處理大數據集")

    def test_memory_cleanup(self):
        """測試記憶體清理"""
        import gc

        # 創建多個圖表並檢查記憶體使用
        initial_objects = len(gc.get_objects())

        for i in range(10):
            data = pd.DataFrame(
                {
                    "date": pd.date_range("2024-01-01", periods=100),
                    "cumulative_return": np.random.randn(100) * 0.01,
                }
            )

            fig = BacktestCharts.cumulative_returns_chart(data)
            del fig  # 明確刪除圖表對象

        gc.collect()  # 強制垃圾回收

        final_objects = len(gc.get_objects())

        # 檢查記憶體洩漏（對象數量不應該大幅增加）
        assert final_objects - initial_objects < 1000  # 允許一些合理的增長


if __name__ == "__main__":
    pytest.main([__file__])
