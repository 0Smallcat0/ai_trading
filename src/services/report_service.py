"""報表服務層

此模組實現報表查詢與視覺化的業務邏輯，包括數據聚合、指標計算、
圖表生成等核心功能。
"""

import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 導入配置和模型
try:
    from src.config import DB_URL, CACHE_DIR
    from src.api.models.reports import (
        TradingMetrics,
        PerformanceMetrics,
        RiskMetrics,
        ChartData,
        ReportSummary,
        TimeRangeEnum,
        ChartTypeEnum,
        ChartLibraryEnum,
    )
except ImportError as e:
    logging.warning("無法導入部分模組: %s", e)
    # 設定預設值
    DB_URL = "sqlite:///data/trading.db"
    CACHE_DIR = "cache"

logger = logging.getLogger(__name__)


class ReportServiceError(Exception):
    """報表服務異常類別"""


class ReportService:
    """報表服務

    提供完整的報表查詢與視覺化功能，包括交易摘要、績效分析、
    風險評估、策略回測等各類報表的生成和處理。
    """

    def __init__(self):
        """初始化報表服務"""
        try:
            # 初始化資料庫連接
            self.engine = create_engine(DB_URL)
            self.session_factory = sessionmaker(bind=self.engine)
            logger.info("報表服務資料庫連接初始化成功")

            # 初始化快取設定
            self.cache_enabled = True
            self.cache_ttl = {
                "realtime": 30,  # 即時數據 30秒
                "daily": 300,  # 日度數據 5分鐘
                "historical": 3600,  # 歷史數據 60分鐘
            }

            # 初始化圖表配置
            self.chart_configs = {
                "plotly": {
                    "template": "plotly_white",
                    "height": 400,
                    "showlegend": True,
                    "margin": {"l": 50, "r": 50, "t": 50, "b": 50},
                },
                "chartjs": {
                    "responsive": True,
                    "maintainAspectRatio": False,
                    "plugins": {"legend": {"display": True}},
                },
                "echarts": {
                    "animation": True,
                    "tooltip": {"trigger": "axis"},
                    "legend": {"show": True},
                },
            }

            # 確保快取目錄存在
            Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

            logger.info("報表服務初始化完成")

        except Exception as e:
            logger.error("報表服務初始化失敗: %s", e)
            raise ReportServiceError("報表服務初始化失敗") from e

    def generate_trading_summary(
        self,
        start_date: datetime,
        end_date: datetime,
        time_range: TimeRangeEnum = TimeRangeEnum.DAILY,
        **kwargs,
    ) -> Dict[str, Any]:
        """生成交易摘要報表

        Args:
            start_date: 開始日期
            end_date: 結束日期
            time_range: 時間範圍
            **kwargs: 其他參數 (symbols, strategies, portfolios, group_by等，目前為模擬實作)

        Returns:
            Dict[str, Any]: 交易摘要報表數據
        """
        try:
            # kwargs 參數保留供未來實作使用
            _ = kwargs

            report_id = str(uuid.uuid4())

            # 模擬交易數據（實際應從資料庫查詢）
            trading_data = self._get_mock_trading_data(start_date, end_date)

            # 計算交易指標
            metrics = self._calculate_trading_metrics(trading_data)

            # 生成每日統計
            daily_stats = self._calculate_daily_stats(trading_data, time_range)

            # 生成分解統計
            symbol_breakdown = self._calculate_symbol_breakdown(trading_data)
            strategy_breakdown = self._calculate_strategy_breakdown(trading_data)

            # 生成圖表數據
            charts = self._generate_trading_charts(trading_data)

            # 創建報表摘要
            summary = ReportSummary(
                report_id=report_id,
                report_type="trading_summary",
                name="交易摘要報表",
                description=f"期間: {start_date.date()} 至 {end_date.date()}",
                generated_at=datetime.now(),
                period_start=start_date,
                period_end=end_date,
                status="completed",
            )

            return {
                "summary": summary.dict(),
                "metrics": metrics.dict(),
                "daily_stats": daily_stats,
                "symbol_breakdown": symbol_breakdown,
                "strategy_breakdown": strategy_breakdown,
                "charts": [chart.dict() for chart in charts],
            }

        except Exception as e:
            logger.error("生成交易摘要報表失敗: %s", e)
            raise ReportServiceError("生成交易摘要報表失敗") from e

    def generate_portfolio_performance(
        self,
        start_date: datetime,
        end_date: datetime,
        benchmark_symbol: str = "^TWII",
        include_attribution: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """生成投資組合績效報表

        Args:
            start_date: 開始日期
            end_date: 結束日期
            benchmark_symbol: 基準指標代碼
            include_attribution: 是否包含歸因分析
            **kwargs: 其他參數 (portfolio_ids, include_risk_metrics等，目前為模擬實作)

        Returns:
            Dict[str, Any]: 投資組合績效報表數據
        """
        try:
            # kwargs 參數保留供未來實作使用
            _ = kwargs

            report_id = str(uuid.uuid4())

            # 模擬投資組合數據
            portfolio_data = self._get_mock_portfolio_data(start_date, end_date)

            # 計算績效指標
            performance = self._calculate_performance_metrics(portfolio_data)

            # 基準比較
            benchmark_comparison = self._calculate_benchmark_comparison(
                portfolio_data, benchmark_symbol
            )

            # 資產配置分析
            asset_allocation = self._calculate_asset_allocation(portfolio_data)

            # 歸因分析（如果需要）
            attribution_analysis = None
            if include_attribution:
                attribution_analysis = self._calculate_attribution_analysis(
                    portfolio_data
                )

            # 生成圖表數據
            charts = self._generate_portfolio_charts(portfolio_data)

            summary = ReportSummary(
                report_id=report_id,
                report_type="portfolio_performance",
                name="投資組合績效報表",
                description=f"期間: {start_date.date()} 至 {end_date.date()}",
                generated_at=datetime.now(),
                period_start=start_date,
                period_end=end_date,
                status="completed",
            )

            return {
                "summary": summary.dict(),
                "performance": performance.dict(),
                "benchmark_comparison": benchmark_comparison,
                "asset_allocation": asset_allocation,
                "attribution_analysis": attribution_analysis,
                "charts": [chart.dict() for chart in charts],
            }

        except Exception as e:
            logger.error("生成投資組合績效報表失敗: %s", e)
            raise ReportServiceError("生成投資組合績效報表失敗") from e

    def generate_risk_analysis(
        self,
        start_date: datetime,
        end_date: datetime,
        include_stress_test: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """生成風險分析報表

        Args:
            start_date: 開始日期
            end_date: 結束日期
            include_stress_test: 是否包含壓力測試
            **kwargs: 其他參數 (portfolio_ids, confidence_levels, risk_types等，目前為模擬實作)

        Returns:
            Dict[str, Any]: 風險分析報表數據
        """
        try:
            # 處理預設值
            confidence_levels = kwargs.get("confidence_levels", [0.95, 0.99])
            # risk_types 參數保留供未來使用
            _ = kwargs.get("risk_types", ["market", "credit", "liquidity"])

            report_id = str(uuid.uuid4())

            # 模擬風險數據
            risk_data = self._get_mock_risk_data(start_date, end_date)

            # 計算風險指標
            risk_metrics = self._calculate_risk_metrics(risk_data)

            # VaR 分析
            var_analysis = self._calculate_var_analysis(risk_data, confidence_levels)

            # 相關性矩陣
            correlation_matrix = self._calculate_correlation_matrix(risk_data)

            # 壓力測試（如果需要）
            stress_test = None
            if include_stress_test:
                stress_test = self._perform_stress_test(risk_data)

            # 生成圖表數據
            charts = self._generate_risk_charts(risk_data)

            summary = ReportSummary(
                report_id=report_id,
                report_type="risk_analysis",
                name="風險分析報表",
                description=f"期間: {start_date.date()} 至 {end_date.date()}",
                generated_at=datetime.now(),
                period_start=start_date,
                period_end=end_date,
                status="completed",
            )

            return {
                "summary": summary.dict(),
                "risk_metrics": risk_metrics.dict(),
                "var_analysis": var_analysis,
                "correlation_matrix": correlation_matrix,
                "stress_test": stress_test,
                "charts": [chart.dict() for chart in charts],
            }

        except Exception as e:
            logger.error("生成風險分析報表失敗: %s", e)
            raise ReportServiceError("生成風險分析報表失敗") from e

    def generate_chart_data(
        self,
        chart_type: ChartTypeEnum,
        library: ChartLibraryEnum,
        data_source: str,
        **kwargs,
    ) -> ChartData:
        """生成圖表數據

        Args:
            chart_type: 圖表類型
            library: 圖表庫
            data_source: 數據來源
            **kwargs: 其他參數 (filters, config等)

        Returns:
            ChartData: 圖表數據
        """
        try:
            # 從 kwargs 獲取參數
            filters = kwargs.get("filters", {})
            config = kwargs.get("config", None)

            # 根據數據來源獲取數據
            raw_data = self._get_data_by_source(data_source, filters)

            # 根據圖表類型和庫生成配置
            chart_config = self._generate_chart_config(chart_type, library, config)

            # 轉換數據格式
            chart_data = self._convert_data_for_chart(raw_data, chart_type, library)

            return ChartData(
                chart_type=chart_type.value,
                library=library.value,
                data=chart_data,
                config=chart_config,
            )

        except Exception as e:
            logger.error("生成圖表數據失敗: %s", e)
            raise ReportServiceError("生成圖表數據失敗") from e

    def export_report(
        self, export_format: str, include_charts: bool = True, **kwargs
    ) -> Dict[str, Any]:
        """匯出報表

        Args:
            export_format: 匯出格式
            include_charts: 是否包含圖表
            **kwargs: 其他參數 (report_id, include_raw_data, template_id, custom_settings等)

        Returns:
            Dict[str, Any]: 匯出結果
        """
        try:
            export_id = str(uuid.uuid4())
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 檔案名稱用於內部處理
            _ = f"report_{timestamp}.{export_format}"

            # include_charts 參數保留供未來使用
            _ = include_charts
            # kwargs 參數保留供未來使用
            _ = kwargs

            # 模擬匯出處理
            file_size = 1024 * 1024  # 1MB
            download_url = f"/api/v1/reports/download/{export_id}"

            return {
                "export_id": export_id,
                "status": "completed",
                "format": export_format,
                "file_size": file_size,
                "download_url": download_url,
                "expires_at": datetime.now() + timedelta(hours=24),
                "created_at": datetime.now(),
            }

        except Exception as e:
            logger.error("匯出報表失敗: %s", e)
            raise ReportServiceError("匯出報表失敗") from e

    # ==================== 私有方法 ====================

    def _get_mock_trading_data(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """獲取模擬交易數據"""
        # 生成模擬數據
        dates = pd.date_range(start_date, end_date, freq="D")
        data = []

        for _, date in enumerate(dates):
            data.append(
                {
                    "date": date,
                    "symbol": "2330.TW",
                    "trades": np.random.randint(5, 20),
                    "volume": np.random.randint(1000, 10000),
                    "amount": np.random.uniform(100000, 1000000),
                    "pnl": np.random.uniform(-10000, 15000),
                    "commission": np.random.uniform(100, 1000),
                }
            )

        return data

    def _calculate_trading_metrics(self, data: List[Dict[str, Any]]) -> TradingMetrics:
        """計算交易指標"""
        df = pd.DataFrame(data)

        total_trades = df["trades"].sum()
        total_volume = df["volume"].sum()
        total_amount = df["amount"].sum()
        total_commission = df["commission"].sum()
        total_pnl = df["pnl"].sum()

        # 計算勝率
        winning_trades = len(df[df["pnl"] > 0])
        win_rate = winning_trades / len(df) * 100 if len(df) > 0 else 0

        # 計算獲利因子
        gross_profit = df[df["pnl"] > 0]["pnl"].sum()
        gross_loss = abs(df[df["pnl"] < 0]["pnl"].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        return TradingMetrics(
            total_trades=int(total_trades),
            total_volume=float(total_volume),
            total_amount=float(total_amount),
            total_commission=float(total_commission),
            total_pnl=float(total_pnl),
            realized_pnl=float(total_pnl),
            unrealized_pnl=0.0,
            win_rate=float(win_rate),
            profit_factor=float(profit_factor),
            avg_win=float(gross_profit / winning_trades) if winning_trades > 0 else 0,
            avg_loss=(
                float(gross_loss / (len(df) - winning_trades))
                if (len(df) - winning_trades) > 0
                else 0
            ),
            max_win=float(df["pnl"].max()),
            max_loss=float(df["pnl"].min()),
            avg_holding_period=1.0,
        )

    def _calculate_daily_stats(
        self, data: List[Dict[str, Any]], time_range: TimeRangeEnum
    ) -> List[Dict[str, Any]]:
        """計算每日統計"""
        df = pd.DataFrame(data)

        # 根據時間範圍分組
        if time_range == TimeRangeEnum.DAILY:
            grouped = df.groupby(df["date"].dt.date)
        elif time_range == TimeRangeEnum.WEEKLY:
            grouped = df.groupby(df["date"].dt.to_period("W"))
        elif time_range == TimeRangeEnum.MONTHLY:
            grouped = df.groupby(df["date"].dt.to_period("M"))
        else:
            grouped = df.groupby(df["date"].dt.date)

        stats = []
        for period, group in grouped:
            stats.append(
                {
                    "period": str(period),
                    "trades": int(group["trades"].sum()),
                    "volume": float(group["volume"].sum()),
                    "amount": float(group["amount"].sum()),
                    "pnl": float(group["pnl"].sum()),
                    "commission": float(group["commission"].sum()),
                }
            )

        return stats

    def _calculate_symbol_breakdown(
        self, data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """計算股票分解統計

        Args:
            data: 交易數據 (目前為模擬實作，暫未使用)

        Returns:
            List[Dict[str, Any]]: 股票分解統計
        """
        # 模擬多個股票的數據 (data 參數保留供未來實作使用)
        _ = data  # 避免未使用參數警告
        symbols = ["2330.TW", "2317.TW", "2454.TW", "2412.TW", "1301.TW"]
        breakdown = []

        for symbol in symbols:
            breakdown.append(
                {
                    "symbol": symbol,
                    "trades": np.random.randint(10, 50),
                    "volume": np.random.randint(5000, 50000),
                    "amount": np.random.uniform(500000, 5000000),
                    "pnl": np.random.uniform(-50000, 100000),
                    "win_rate": np.random.uniform(40, 80),
                }
            )

        return breakdown

    def _calculate_strategy_breakdown(
        self, data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """計算策略分解統計

        Args:
            data: 交易數據 (目前為模擬實作，暫未使用)

        Returns:
            List[Dict[str, Any]]: 策略分解統計
        """
        # 模擬策略數據 (data 參數保留供未來實作使用)
        _ = data  # 避免未使用參數警告
        strategies = ["均線策略", "動量策略", "價值策略", "套利策略"]
        breakdown = []

        for strategy in strategies:
            breakdown.append(
                {
                    "strategy": strategy,
                    "trades": np.random.randint(20, 100),
                    "pnl": np.random.uniform(-20000, 50000),
                    "win_rate": np.random.uniform(45, 75),
                    "sharpe_ratio": np.random.uniform(0.5, 2.0),
                    "max_drawdown": np.random.uniform(5, 20),
                }
            )

        return breakdown

    # API 路由需要的方法
    def generate_performance_report(self, start_date, end_date, **kwargs):
        """生成績效報表

        Args:
            start_date (datetime): 開始日期
            end_date (datetime): 結束日期
            **kwargs: 其他參數 (portfolio_ids, benchmark, include_benchmark等)

        Returns:
            Dict[str, Any]: 績效報表生成結果
        """
        try:
            # 參數保留供未來實作使用
            _ = start_date
            _ = end_date

            report_id = str(uuid.uuid4())
            export_format = kwargs.get("format", "json")
            return {
                "success": True,
                "report_id": report_id,
                "file_url": f"/api/reports/download/{report_id}.{export_format}",
                "message": "績效報表生成成功",
            }
        except Exception as e:
            logger.error("生成績效報表失敗: %s", e)
            return {"success": False, "message": str(e)}

    def get_performance_data(self, start_date, end_date, **kwargs):
        """獲取績效數據

        Args:
            start_date (datetime): 開始日期
            end_date (datetime): 結束日期
            **kwargs: 其他參數 (portfolio_ids, benchmark, include_benchmark等)

        Returns:
            Dict[str, Any]: 績效數據
        """
        # 參數保留供未來實作使用
        _ = start_date
        _ = end_date

        # 模擬績效數據
        include_benchmark = kwargs.get("include_benchmark", True)
        return {
            "portfolio_performance": {
                "total_return": 0.15,
                "annualized_return": 0.12,
                "volatility": 0.18,
                "sharpe_ratio": 1.25,
            },
            "benchmark_performance": (
                {"total_return": 0.10, "annualized_return": 0.08}
                if include_benchmark
                else None
            ),
        }

    def compare_portfolio_performance(self, start_date, end_date, **kwargs):
        """比較投資組合績效

        Args:
            start_date (datetime): 開始日期
            end_date (datetime): 結束日期
            **kwargs: 其他參數 (portfolio_ids, metrics等，目前為模擬實作)

        Returns:
            Dict[str, Any]: 投資組合比較結果
        """
        # 參數保留供未來實作使用
        _ = start_date
        _ = end_date
        _ = kwargs

        return {
            "portfolios": {},
            "ranking": {},
            "correlation_matrix": [],
            "summary": {},
        }

    def generate_portfolio_report(self, start_date, end_date, **kwargs):
        """生成投資組合報表

        Args:
            start_date (datetime): 開始日期
            end_date (datetime): 結束日期
            **kwargs: 其他參數 (portfolio_ids, include_positions, include_transactions等)

        Returns:
            Dict[str, Any]: 投資組合報表生成結果
        """
        try:
            # 參數保留供未來實作使用
            _ = start_date
            _ = end_date

            report_id = str(uuid.uuid4())
            export_format = kwargs.get("format", "json")
            return {
                "success": True,
                "report_id": report_id,
                "file_url": f"/api/reports/download/{report_id}.{export_format}",
                "message": "投資組合報表生成成功",
            }
        except Exception as e:
            logger.error("生成投資組合報表失敗: %s", e)
            return {"success": False, "message": str(e)}

    def get_portfolio_data(self, start_date, end_date, **kwargs):
        """獲取投資組合數據

        Args:
            start_date (datetime): 開始日期
            end_date (datetime): 結束日期
            **kwargs: 其他參數 (portfolio_ids, include_positions, include_transactions等)

        Returns:
            Dict[str, Any]: 投資組合數據
        """
        # 參數保留供未來實作使用
        _ = start_date
        _ = end_date
        _ = kwargs

        return {
            "portfolio_summary": {},
            "asset_allocation": {},
            "sector_allocation": {},
            "top_holdings": [],
            "performance_summary": {},
        }

    def get_portfolio_allocation(self, portfolio_id, **kwargs):
        """獲取投資組合配置

        Args:
            portfolio_id (str): 投資組合ID
            **kwargs: 其他參數 (groupby, as_of_date等，目前為模擬實作)

        Returns:
            Dict[str, Any]: 投資組合配置數據
        """
        # kwargs 參數保留供未來實作使用
        _ = kwargs

        return {
            "portfolio_id": portfolio_id,
            "allocation": {},
            "concentration_metrics": {},
            "diversification_ratio": 0.78,
        }

    def _generate_trading_charts(self, data: List[Dict[str, Any]]) -> List[ChartData]:
        """生成交易圖表數據"""
        charts = []
        df = pd.DataFrame(data)

        # 累積損益曲線
        cumulative_pnl = df["pnl"].cumsum()
        charts.append(
            ChartData(
                chart_type="line",
                library="plotly",
                data={
                    "x": [d.isoformat() for d in df["date"]],
                    "y": cumulative_pnl.tolist(),
                    "type": "scatter",
                    "mode": "lines",
                    "name": "累積損益",
                },
                config={
                    "title": "累積損益曲線",
                    "xaxis": {"title": "日期"},
                    "yaxis": {"title": "累積損益"},
                },
            )
        )

        # 每日交易量柱狀圖
        charts.append(
            ChartData(
                chart_type="bar",
                library="plotly",
                data={
                    "x": [d.isoformat() for d in df["date"]],
                    "y": df["volume"].tolist(),
                    "type": "bar",
                    "name": "交易量",
                },
                config={
                    "title": "每日交易量",
                    "xaxis": {"title": "日期"},
                    "yaxis": {"title": "交易量"},
                },
            )
        )

        return charts

    def _get_mock_portfolio_data(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """獲取模擬投資組合數據"""
        dates = pd.date_range(start_date, end_date, freq="D")

        # 生成模擬價格數據
        initial_value = 1000000
        returns = np.random.normal(0.0005, 0.02, len(dates))  # 日報酬率
        values = [initial_value]

        for ret in returns[1:]:
            values.append(values[-1] * (1 + ret))

        return {
            "dates": dates.tolist(),
            "values": values,
            "returns": returns.tolist(),
            "benchmark_returns": np.random.normal(0.0003, 0.015, len(dates)).tolist(),
        }

    def _calculate_performance_metrics(
        self, data: Dict[str, Any]
    ) -> PerformanceMetrics:
        """計算績效指標"""
        returns = np.array(data["returns"])
        values = np.array(data["values"])

        # 基本指標
        total_return = (values[-1] - values[0]) / values[0]
        annualized_return = (1 + total_return) ** (252 / len(returns)) - 1
        volatility = np.std(returns) * np.sqrt(252)

        # 風險調整指標
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0

        # 下行風險指標
        negative_returns = returns[returns < 0]
        downside_deviation = (
            np.std(negative_returns) * np.sqrt(252) if len(negative_returns) > 0 else 0
        )
        sortino_ratio = (
            annualized_return / downside_deviation if downside_deviation > 0 else 0
        )

        # 回撤分析
        cumulative_returns = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = abs(np.min(drawdown))

        # VaR 計算
        var_95 = np.percentile(returns, 5)
        var_99 = np.percentile(returns, 1)
        cvar_95 = np.mean(returns[returns <= var_95])
        cvar_99 = np.mean(returns[returns <= var_99])

        return PerformanceMetrics(
            total_return=float(total_return),
            annualized_return=float(annualized_return),
            volatility=float(volatility),
            sharpe_ratio=float(sharpe_ratio),
            sortino_ratio=float(sortino_ratio),
            calmar_ratio=(
                float(annualized_return / max_drawdown) if max_drawdown > 0 else 0
            ),
            max_drawdown=float(max_drawdown),
            max_drawdown_duration=30,  # 模擬值
            var_95=float(var_95),
            var_99=float(var_99),
            cvar_95=float(cvar_95),
            cvar_99=float(cvar_99),
        )

    def _calculate_benchmark_comparison(
        self, data: Dict[str, Any], benchmark_symbol: str
    ) -> Dict[str, Any]:
        """計算基準比較"""
        portfolio_returns = np.array(data["returns"])
        benchmark_returns = np.array(data["benchmark_returns"])

        # 計算超額報酬
        excess_returns = portfolio_returns - benchmark_returns

        # 計算追蹤誤差
        tracking_error = np.std(excess_returns) * np.sqrt(252)

        # 計算資訊比率
        information_ratio = (
            np.mean(excess_returns) / np.std(excess_returns)
            if np.std(excess_returns) > 0
            else 0
        )

        # 計算貝塔係數
        covariance = np.cov(portfolio_returns, benchmark_returns)[0, 1]
        benchmark_variance = np.var(benchmark_returns)
        beta = covariance / benchmark_variance if benchmark_variance > 0 else 0

        # 計算阿爾法係數
        portfolio_return = np.mean(portfolio_returns) * 252
        benchmark_return = np.mean(benchmark_returns) * 252
        alpha = portfolio_return - beta * benchmark_return

        return {
            "benchmark_symbol": benchmark_symbol,
            "excess_return": float(np.mean(excess_returns) * 252),
            "tracking_error": float(tracking_error),
            "information_ratio": float(information_ratio),
            "beta": float(beta),
            "alpha": float(alpha),
            "correlation": float(
                np.corrcoef(portfolio_returns, benchmark_returns)[0, 1]
            ),
        }

    def _calculate_asset_allocation(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """計算資產配置

        Args:
            data: 投資組合數據 (目前為模擬實作，暫未使用)

        Returns:
            List[Dict[str, Any]]: 資產配置數據
        """
        # 模擬資產配置數據 (data 參數保留供未來實作使用)
        _ = data  # 避免未使用參數警告
        allocations = [
            {"asset_class": "台股", "weight": 60.0, "value": 600000},
            {"asset_class": "美股", "weight": 25.0, "value": 250000},
            {"asset_class": "債券", "weight": 10.0, "value": 100000},
            {"asset_class": "現金", "weight": 5.0, "value": 50000},
        ]

        return allocations

    def _calculate_attribution_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """計算歸因分析

        Args:
            data: 投資組合數據 (目前為模擬實作，暫未使用)

        Returns:
            Dict[str, Any]: 歸因分析數據
        """
        # 模擬歸因分析數據 (data 參數保留供未來實作使用)
        _ = data  # 避免未使用參數警告
        return {
            "asset_allocation_effect": 0.02,
            "security_selection_effect": 0.015,
            "interaction_effect": 0.005,
            "total_active_return": 0.04,
            "sector_attribution": [
                {
                    "sector": "科技",
                    "allocation_effect": 0.01,
                    "selection_effect": 0.008,
                },
                {
                    "sector": "金融",
                    "allocation_effect": 0.005,
                    "selection_effect": 0.003,
                },
                {
                    "sector": "傳產",
                    "allocation_effect": 0.003,
                    "selection_effect": 0.002,
                },
            ],
        }

    def _generate_portfolio_charts(self, data: Dict[str, Any]) -> List[ChartData]:
        """生成投資組合圖表數據"""
        charts = []

        # 淨值曲線
        charts.append(
            ChartData(
                chart_type="line",
                library="plotly",
                data={
                    "x": [d.isoformat() for d in data["dates"]],
                    "y": data["values"],
                    "type": "scatter",
                    "mode": "lines",
                    "name": "投資組合淨值",
                },
                config={
                    "title": "投資組合淨值曲線",
                    "xaxis": {"title": "日期"},
                    "yaxis": {"title": "淨值"},
                },
            )
        )

        # 資產配置圓餅圖
        allocations = self._calculate_asset_allocation(data)
        charts.append(
            ChartData(
                chart_type="pie",
                library="plotly",
                data={
                    "labels": [a["asset_class"] for a in allocations],
                    "values": [a["weight"] for a in allocations],
                    "type": "pie",
                },
                config={"title": "資產配置分布"},
            )
        )

        return charts

    def _get_mock_risk_data(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """獲取模擬風險數據"""
        dates = pd.date_range(start_date, end_date, freq="D")

        # 生成多個資產的報酬率數據
        n_assets = 5
        returns_matrix = np.random.multivariate_normal(
            mean=[0.0005] * n_assets,
            cov=np.random.rand(n_assets, n_assets) * 0.0001,
            size=len(dates),
        )

        return {
            "dates": dates.tolist(),
            "returns_matrix": returns_matrix.tolist(),
            "asset_names": ["2330.TW", "2317.TW", "2454.TW", "2412.TW", "1301.TW"],
        }

    def _calculate_risk_metrics(self, data: Dict[str, Any]) -> RiskMetrics:
        """計算風險指標"""
        returns_matrix = np.array(data["returns_matrix"])

        # 計算投資組合報酬率（等權重）
        portfolio_returns = np.mean(returns_matrix, axis=1)

        # 計算各類風險
        market_risk = np.std(portfolio_returns) * np.sqrt(252)
        credit_risk = market_risk * 0.3  # 模擬值
        liquidity_risk = market_risk * 0.2
        operational_risk = market_risk * 0.1

        # 計算集中度風險
        weights = np.array([0.2] * 5)  # 等權重
        concentration_risk = np.sum(weights**2)

        # 計算相關性風險
        correlation_matrix = np.corrcoef(returns_matrix.T)
        avg_correlation = np.mean(
            correlation_matrix[np.triu_indices_from(correlation_matrix, k=1)]
        )
        correlation_risk = avg_correlation

        return RiskMetrics(
            market_risk=float(market_risk),
            credit_risk=float(credit_risk),
            liquidity_risk=float(liquidity_risk),
            operational_risk=float(operational_risk),
            concentration_risk=float(concentration_risk),
            correlation_risk=float(correlation_risk),
        )

    def _calculate_var_analysis(
        self, data: Dict[str, Any], confidence_levels: List[float]
    ) -> Dict[str, Any]:
        """計算 VaR 分析"""
        returns_matrix = np.array(data["returns_matrix"])
        portfolio_returns = np.mean(returns_matrix, axis=1)

        var_results = {}
        for confidence in confidence_levels:
            percentile = (1 - confidence) * 100
            var_value = np.percentile(portfolio_returns, percentile)
            cvar_value = np.mean(portfolio_returns[portfolio_returns <= var_value])

            var_results[f"var_{int(confidence*100)}"] = float(var_value)
            var_results[f"cvar_{int(confidence*100)}"] = float(cvar_value)

        return var_results

    def _calculate_correlation_matrix(self, data: Dict[str, Any]) -> List[List[float]]:
        """計算相關性矩陣"""
        returns_matrix = np.array(data["returns_matrix"])
        correlation_matrix = np.corrcoef(returns_matrix.T)
        return correlation_matrix.tolist()

    def _perform_stress_test(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """執行壓力測試

        Args:
            data: 投資組合數據 (目前為模擬實作，暫未使用)

        Returns:
            Dict[str, Any]: 壓力測試結果
        """
        # 模擬壓力測試結果 (data 參數保留供未來實作使用)
        _ = data  # 避免未使用參數警告
        scenarios = {
            "market_crash": {"portfolio_loss": -0.25, "probability": 0.05},
            "interest_rate_shock": {"portfolio_loss": -0.15, "probability": 0.10},
            "liquidity_crisis": {"portfolio_loss": -0.20, "probability": 0.03},
            "currency_crisis": {"portfolio_loss": -0.12, "probability": 0.08},
        }

        return scenarios

    def _generate_risk_charts(self, data: Dict[str, Any]) -> List[ChartData]:
        """生成風險圖表數據"""
        charts = []
        returns_matrix = np.array(data["returns_matrix"])
        portfolio_returns = np.mean(returns_matrix, axis=1)

        # 報酬率分布直方圖
        charts.append(
            ChartData(
                chart_type="histogram",
                library="plotly",
                data={
                    "x": portfolio_returns.tolist(),
                    "type": "histogram",
                    "nbinsx": 50,
                },
                config={
                    "title": "投資組合報酬率分布",
                    "xaxis": {"title": "日報酬率"},
                    "yaxis": {"title": "頻率"},
                },
            )
        )

        # 相關性熱力圖
        correlation_matrix = self._calculate_correlation_matrix(data)
        charts.append(
            ChartData(
                chart_type="heatmap",
                library="plotly",
                data={
                    "z": correlation_matrix,
                    "x": data["asset_names"],
                    "y": data["asset_names"],
                    "type": "heatmap",
                    "colorscale": "RdBu",
                },
                config={"title": "資產相關性矩陣"},
            )
        )

        return charts

    def _get_data_by_source(
        self, data_source: str, filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """根據數據來源獲取數據"""
        # 模擬數據獲取
        if data_source == "trading":
            return self._get_mock_trading_data(
                filters.get("start_date", datetime.now() - timedelta(days=30)),
                filters.get("end_date", datetime.now()),
            )
        if data_source == "portfolio":
            return self._get_mock_portfolio_data(
                filters.get("start_date", datetime.now() - timedelta(days=30)),
                filters.get("end_date", datetime.now()),
            )
        return {}

    def _generate_chart_config(
        self,
        chart_type: ChartTypeEnum,
        library: ChartLibraryEnum,
        custom_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """生成圖表配置"""
        base_config = self.chart_configs.get(library.value, {}).copy()

        # 根據圖表類型調整配置
        if chart_type == ChartTypeEnum.LINE:
            base_config.update({"type": "line", "mode": "lines"})
        elif chart_type == ChartTypeEnum.BAR:
            base_config.update({"type": "bar"})
        elif chart_type == ChartTypeEnum.PIE:
            base_config.update({"type": "pie"})

        # 應用自定義配置
        if custom_config:
            base_config.update(custom_config)

        return base_config

    def _convert_data_for_chart(
        self, raw_data: Any, chart_type: ChartTypeEnum, library: ChartLibraryEnum
    ) -> Dict[str, Any]:
        """轉換數據格式以適應圖表庫"""
        if isinstance(raw_data, list) and len(raw_data) > 0:
            df = pd.DataFrame(raw_data)

            if library == ChartLibraryEnum.PLOTLY:
                if chart_type == ChartTypeEnum.LINE:
                    return {
                        "x": df.iloc[:, 0].tolist(),
                        "y": df.iloc[:, 1].tolist(),
                        "type": "scatter",
                        "mode": "lines",
                    }
                if chart_type == ChartTypeEnum.BAR:
                    return {
                        "x": df.iloc[:, 0].tolist(),
                        "y": df.iloc[:, 1].tolist(),
                        "type": "bar",
                    }

            elif library == ChartLibraryEnum.CHARTJS:
                return {
                    "labels": df.iloc[:, 0].tolist(),
                    "datasets": [{"data": df.iloc[:, 1].tolist(), "label": "數據"}],
                }

        return {}
