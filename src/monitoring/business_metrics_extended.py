"""擴展業務指標收集器

此模組實現擴展的業務指標收集功能，包括：
- 交易策略效能指標（勝率、夏普比率、最大回撤）
- 風險管理指標（VaR、部位暴露、資金使用率）
- 模型漂移檢測指標
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple

import numpy as np

try:
    from prometheus_client import Counter, Gauge
except ImportError:
    Counter = Gauge = None

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class ExtendedBusinessMetricsCollector:
    """擴展業務指標收集器

    收集詳細的交易和風險管理指標。

    Attributes:
        metrics: 指標字典
        registry: Prometheus 註冊表
        price_history: 價格歷史數據
        position_history: 部位歷史數據
        trade_history: 交易歷史數據
    """

    def __init__(self, registry: Any = None):
        """初始化擴展業務指標收集器

        Args:
            registry: Prometheus 註冊表

        Raises:
            ImportError: 當 prometheus_client 未安裝時
        """
        if Counter is None or Gauge is None:
            raise ImportError("prometheus_client 套件未安裝")

        self.registry = registry
        self.metrics: Dict[str, Any] = {}

        # 歷史數據儲存
        self.price_history: List[Tuple[datetime, str, float]] = []
        self.position_history: List[Tuple[datetime, str, float]] = []
        self.trade_history: List[Dict[str, Any]] = []

        # 初始化指標
        self._init_trading_performance_metrics()
        self._init_risk_management_metrics()
        self._init_model_drift_metrics()

        module_logger.info("擴展業務指標收集器初始化成功")

    def _init_trading_performance_metrics(self) -> None:
        """初始化交易效能指標"""
        # 勝率指標
        self.metrics["win_rate"] = Gauge(
            "trading_win_rate_percent",
            "交易勝率百分比",
            ["strategy", "symbol"],
            registry=self.registry,
        )

        # 夏普比率
        self.metrics["sharpe_ratio"] = Gauge(
            "trading_sharpe_ratio",
            "夏普比率",
            ["strategy", "period"],
            registry=self.registry,
        )

        # 最大回撤
        self.metrics["max_drawdown"] = Gauge(
            "trading_max_drawdown_percent",
            "最大回撤百分比",
            ["strategy", "period"],
            registry=self.registry,
        )

        # 平均持倉時間
        self.metrics["avg_holding_time"] = Gauge(
            "trading_avg_holding_time_hours",
            "平均持倉時間（小時）",
            ["strategy", "symbol"],
            registry=self.registry,
        )

        # 收益波動率
        self.metrics["return_volatility"] = Gauge(
            "trading_return_volatility_percent",
            "收益波動率百分比",
            ["strategy", "period"],
            registry=self.registry,
        )

    def _init_risk_management_metrics(self) -> None:
        """初始化風險管理指標"""
        # VaR (Value at Risk)
        self.metrics["var_95"] = Gauge(
            "risk_var_95_percent",
            "95% 信心水準 VaR",
            ["portfolio", "period"],
            registry=self.registry,
        )

        self.metrics["var_99"] = Gauge(
            "risk_var_99_percent",
            "99% 信心水準 VaR",
            ["portfolio", "period"],
            registry=self.registry,
        )

        # 部位暴露
        self.metrics["position_exposure"] = Gauge(
            "risk_position_exposure_percent",
            "部位暴露百分比",
            ["symbol", "direction"],
            registry=self.registry,
        )

        # 資金使用率
        self.metrics["capital_utilization"] = Gauge(
            "risk_capital_utilization_percent",
            "資金使用率百分比",
            ["account"],
            registry=self.registry,
        )

        # 槓桿比率
        self.metrics["leverage_ratio"] = Gauge(
            "risk_leverage_ratio",
            "槓桿比率",
            ["account"],
            registry=self.registry,
        )

        # 集中度風險
        self.metrics["concentration_risk"] = Gauge(
            "risk_concentration_percent",
            "集中度風險百分比",
            ["symbol"],
            registry=self.registry,
        )

    def _init_model_drift_metrics(self) -> None:
        """初始化模型漂移檢測指標"""
        # 特徵漂移
        self.metrics["feature_drift"] = Gauge(
            "model_feature_drift_score",
            "特徵漂移分數",
            ["model_name", "feature"],
            registry=self.registry,
        )

        # 預測漂移
        self.metrics["prediction_drift"] = Gauge(
            "model_prediction_drift_score",
            "預測漂移分數",
            ["model_name"],
            registry=self.registry,
        )

        # 模型準確率趨勢
        self.metrics["accuracy_trend"] = Gauge(
            "model_accuracy_trend_slope",
            "準確率趨勢斜率",
            ["model_name", "period"],
            registry=self.registry,
        )

        # 數據品質分數
        self.metrics["data_quality"] = Gauge(
            "model_data_quality_score",
            "數據品質分數",
            ["data_source"],
            registry=self.registry,
        )

    def update_trading_performance(
        self,
        strategy: str,
        symbol: str,
        trades: List[Dict[str, Any]]
    ) -> None:
        """更新交易效能指標

        Args:
            strategy: 策略名稱
            symbol: 交易標的
            trades: 交易記錄列表
        """
        try:
            if not trades:
                return

            # 計算勝率
            winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
            win_rate = len(winning_trades) / len(trades) * 100
            self.metrics["win_rate"].labels(
                strategy=strategy, symbol=symbol
            ).set(win_rate)

            # 計算平均持倉時間
            holding_times = []
            for trade in trades:
                if 'entry_time' in trade and 'exit_time' in trade:
                    entry_time = datetime.fromisoformat(trade['entry_time'])
                    exit_time = datetime.fromisoformat(trade['exit_time'])
                    holding_time = (exit_time - entry_time).total_seconds() / 3600  # 小時
                    holding_times.append(holding_time)

            if holding_times:
                avg_holding_time = np.mean(holding_times)
                self.metrics["avg_holding_time"].labels(
                    strategy=strategy, symbol=symbol
                ).set(avg_holding_time)

            module_logger.debug(
                "交易效能指標已更新: %s-%s, 勝率: %.2f%%, 平均持倉: %.2f小時",
                strategy, symbol, win_rate, avg_holding_time if holding_times else 0
            )

        except Exception as e:
            module_logger.error("更新交易效能指標失敗: %s", e)

    def update_portfolio_metrics(
        self,
        strategy: str,
        returns: List[float],
        period: str = "daily"
    ) -> None:
        """更新投資組合指標

        Args:
            strategy: 策略名稱
            returns: 收益率列表
            period: 時間週期
        """
        try:
            if not returns or len(returns) < 2:
                return

            returns_array = np.array(returns)

            # 計算夏普比率
            if len(returns) > 1:
                mean_return = np.mean(returns_array)
                std_return = np.std(returns_array)
                sharpe_ratio = mean_return / std_return if std_return > 0 else 0

                # 年化夏普比率
                if period == "daily":
                    sharpe_ratio *= np.sqrt(252)
                elif period == "hourly":
                    sharpe_ratio *= np.sqrt(252 * 24)

                self.metrics["sharpe_ratio"].labels(
                    strategy=strategy, period=period
                ).set(sharpe_ratio)

            # 計算最大回撤
            cumulative_returns = np.cumprod(1 + returns_array)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = np.min(drawdown) * 100  # 轉換為百分比

            self.metrics["max_drawdown"].labels(
                strategy=strategy, period=period
            ).set(abs(max_drawdown))

            # 計算收益波動率
            volatility = np.std(returns_array) * 100  # 轉換為百分比
            if period == "daily":
                volatility *= np.sqrt(252)
            elif period == "hourly":
                volatility *= np.sqrt(252 * 24)

            self.metrics["return_volatility"].labels(
                strategy=strategy, period=period
            ).set(volatility)

            module_logger.debug(
                "投資組合指標已更新: %s, 夏普比率: %.3f, 最大回撤: %.2f%%, 波動率: %.2f%%",
                strategy, sharpe_ratio, abs(max_drawdown), volatility
            )

        except Exception as e:
            module_logger.error("更新投資組合指標失敗: %s", e)

    def update_risk_metrics(
        self,
        portfolio_returns: List[float],
        positions: Dict[str, float],
        total_capital: float,
        portfolio: str = "main"
    ) -> None:
        """更新風險管理指標

        Args:
            portfolio_returns: 投資組合收益率
            positions: 部位字典 {symbol: value}
            total_capital: 總資本
            portfolio: 投資組合名稱
        """
        try:
            if portfolio_returns and len(portfolio_returns) > 1:
                returns_array = np.array(portfolio_returns)

                # 計算 VaR
                var_95 = np.percentile(returns_array, 5) * 100  # 95% VaR
                var_99 = np.percentile(returns_array, 1) * 100  # 99% VaR

                self.metrics["var_95"].labels(
                    portfolio=portfolio, period="daily"
                ).set(abs(var_95))

                self.metrics["var_99"].labels(
                    portfolio=portfolio, period="daily"
                ).set(abs(var_99))

            # 計算部位暴露和集中度風險
            if positions and total_capital > 0:
                total_exposure = sum(abs(value) for value in positions.values())

                for symbol, value in positions.items():
                    # 部位暴露
                    exposure_pct = abs(value) / total_capital * 100
                    direction = "long" if value > 0 else "short"

                    self.metrics["position_exposure"].labels(
                        symbol=symbol, direction=direction
                    ).set(exposure_pct)

                    # 集中度風險
                    concentration = (
                        abs(value) / total_exposure * 100
                        if total_exposure > 0 else 0
                    )
                    self.metrics["concentration_risk"].labels(
                        symbol=symbol
                    ).set(concentration)

                # 資金使用率
                utilization = total_exposure / total_capital * 100
                self.metrics["capital_utilization"].labels(
                    portfolio=portfolio
                ).set(utilization)

                # 槓桿比率
                leverage = total_exposure / total_capital
                self.metrics["leverage_ratio"].labels(portfolio=portfolio).set(leverage)

            module_logger.debug("風險管理指標已更新: %s", portfolio)

        except Exception as e:
            module_logger.error("更新風險管理指標失敗: %s", e)

    def update_model_drift_metrics(
        self,
        model_name: str,
        feature_data: Dict[str, List[float]],
        predictions: List[float],
        reference_predictions: List[float]
    ) -> None:
        """更新模型漂移指標

        Args:
            model_name: 模型名稱
            feature_data: 特徵數據字典
            predictions: 當前預測
            reference_predictions: 參考預測
        """
        try:
            # 計算特徵漂移
            for feature_name, values in feature_data.items():
                if len(values) > 1:
                    # 使用標準差作為漂移指標
                    drift_score = np.std(values)
                    self.metrics["feature_drift"].labels(
                        model_name=model_name, feature=feature_name
                    ).set(drift_score)

            # 計算預測漂移
            if predictions and reference_predictions:
                if len(predictions) == len(reference_predictions):
                    # 使用均方根誤差作為漂移指標
                    pred_diff = np.array(predictions) - np.array(reference_predictions)
                    mse = np.mean(pred_diff ** 2)
                    drift_score = np.sqrt(mse)

                    self.metrics["prediction_drift"].labels(
                        model_name=model_name
                    ).set(drift_score)

            module_logger.debug("模型漂移指標已更新: %s", model_name)

        except Exception as e:
            module_logger.error("更新模型漂移指標失敗: %s", e)

    def get_metrics_summary(self) -> Dict[str, Any]:
        """獲取指標摘要

        Returns:
            Dict[str, Any]: 指標摘要字典
        """
        try:
            summary = {
                "trading_performance": {
                    "metrics_count": 5,
                    "metrics": [
                        "win_rate", "sharpe_ratio", "max_drawdown",
                        "avg_holding_time", "return_volatility"
                    ]
                },
                "risk_management": {
                    "metrics_count": 6,
                    "metrics": [
                        "var_95", "var_99", "position_exposure",
                        "capital_utilization", "leverage_ratio",
                        "concentration_risk"
                    ]
                },
                "model_drift": {
                    "metrics_count": 4,
                    "metrics": [
                        "feature_drift", "prediction_drift",
                        "accuracy_trend", "data_quality"
                    ]
                },
                "total_metrics": len(self.metrics)
            }

            return summary

        except Exception as e:
            module_logger.error("獲取指標摘要失敗: %s", e)
            return {"error": str(e)}
