"""業務指標收集器

此模組實現業務相關指標的收集，包括策略績效、風險暴露、資金使用率等。
"""

import logging
from typing import Dict, Any, Optional

try:
    from prometheus_client import Counter, Gauge, Histogram
except ImportError:
    Counter = None
    Gauge = None
    Histogram = None

from .base import PrometheusCollectorBase

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class BusinessMetricsCollector(PrometheusCollectorBase):
    """業務指標收集器

    收集業務相關的關鍵指標，包括策略績效、風險管理、資金使用等。

    Attributes:
        strategy_return: 策略收益率
        portfolio_value: 投資組合價值
        risk_exposure: 風險暴露
        capital_utilization: 資金使用率
    """

    def __init__(self, collection_interval: int = 15):
        """初始化業務指標收集器

        Args:
            collection_interval: 指標收集間隔，預設 15 秒

        Raises:
            ImportError: 當 prometheus_client 套件未安裝時
        """
        if Counter is None or Gauge is None or Histogram is None:
            raise ImportError("prometheus_client 套件未安裝")

        super().__init__(collection_interval)
        self._init_metrics()

    def _init_metrics(self) -> None:
        """初始化業務指標"""
        try:
            # 策略收益率
            self.metrics["strategy_return"] = Gauge(
                "business_strategy_return_percent",
                "策略收益率百分比",
                ["strategy_name", "period"],
                registry=self.registry
            )

            # 投資組合總價值
            self.metrics["portfolio_value"] = Gauge(
                "business_portfolio_value_total",
                "投資組合總價值",
                ["currency"],
                registry=self.registry
            )

            # 可用資金
            self.metrics["available_capital"] = Gauge(
                "business_available_capital",
                "可用資金",
                ["currency"],
                registry=self.registry
            )

            # 資金使用率
            self.metrics["capital_utilization"] = Gauge(
                "business_capital_utilization_percent",
                "資金使用率百分比",
                registry=self.registry
            )

            # 風險暴露（VaR）
            self.metrics["var_exposure"] = Gauge(
                "business_var_exposure",
                "風險價值暴露",
                ["confidence_level", "time_horizon"],
                registry=self.registry
            )

            # 最大回撤
            self.metrics["max_drawdown"] = Gauge(
                "business_max_drawdown_percent",
                "最大回撤百分比",
                ["strategy_name"],
                registry=self.registry
            )

            # 夏普比率
            self.metrics["sharpe_ratio"] = Gauge(
                "business_sharpe_ratio",
                "夏普比率",
                ["strategy_name", "period"],
                registry=self.registry
            )

            # 勝率
            self.metrics["win_rate"] = Gauge(
                "business_win_rate_percent",
                "交易勝率百分比",
                ["strategy_name"],
                registry=self.registry
            )

            # 平均盈利
            self.metrics["avg_profit"] = Gauge(
                "business_avg_profit",
                "平均盈利",
                ["strategy_name", "currency"],
                registry=self.registry
            )

            # 平均虧損
            self.metrics["avg_loss"] = Gauge(
                "business_avg_loss",
                "平均虧損",
                ["strategy_name", "currency"],
                registry=self.registry
            )

            # 盈虧比
            self.metrics["profit_loss_ratio"] = Gauge(
                "business_profit_loss_ratio",
                "盈虧比",
                ["strategy_name"],
                registry=self.registry
            )

            # 交易頻率
            self.metrics["trade_frequency"] = Gauge(
                "business_trade_frequency_per_day",
                "每日交易頻率",
                ["strategy_name"],
                registry=self.registry
            )

            # 持倉集中度
            self.metrics["position_concentration"] = Gauge(
                "business_position_concentration_percent",
                "持倉集中度百分比",
                ["symbol"],
                registry=self.registry
            )

            # 槓桿倍數
            self.metrics["leverage_ratio"] = Gauge(
                "business_leverage_ratio",
                "槓桿倍數",
                registry=self.registry
            )

            # 策略活躍度
            self.metrics["strategy_activity"] = Counter(
                "business_strategy_signals_total",
                "策略信號總數",
                ["strategy_name", "signal_type"],
                registry=self.registry
            )

            # 風險限額使用率
            self.metrics["risk_limit_usage"] = Gauge(
                "business_risk_limit_usage_percent",
                "風險限額使用率百分比",
                ["limit_type"],
                registry=self.registry
            )

            module_logger.info("業務指標初始化完成")

        except Exception as e:
            module_logger.error("業務指標初始化失敗: %s", e)
            raise

    def _collect_metrics(self) -> None:
        """收集業務指標

        Note:
            此方法需要與業務系統整合來獲取實際數據。
            當前實現為示例，實際使用時需要連接到業務數據源。
        """
        try:
            # 這裡應該從業務系統獲取實際數據
            # 當前為示例實現
            self._collect_portfolio_metrics()
            self._collect_strategy_metrics()
            self._collect_risk_metrics()

        except Exception as e:
            module_logger.error("收集業務指標時發生錯誤: %s", e)

    def _collect_portfolio_metrics(self) -> None:
        """收集投資組合指標

        Note:
            需要與投資組合管理系統整合
        """
        try:
            # 示例：這裡應該從投資組合系統獲取數據
            # 實際實現時需要替換為真實的數據源
            pass

        except Exception as e:
            module_logger.error("收集投資組合指標失敗: %s", e)

    def _collect_strategy_metrics(self) -> None:
        """收集策略績效指標

        Note:
            需要與策略管理系統整合
        """
        try:
            # 示例：這裡應該從策略系統獲取數據
            # 實際實現時需要替換為真實的數據源
            pass

        except Exception as e:
            module_logger.error("收集策略績效指標失敗: %s", e)

    def _collect_risk_metrics(self) -> None:
        """收集風險管理指標

        Note:
            需要與風險管理系統整合
        """
        try:
            # 示例：這裡應該從風險管理系統獲取數據
            # 實際實現時需要替換為真實的數據源
            pass

        except Exception as e:
            module_logger.error("收集風險管理指標失敗: %s", e)

    def update_portfolio_value(self, value: float, currency: str = "USD") -> None:
        """更新投資組合價值

        Args:
            value: 投資組合價值
            currency: 貨幣單位
        """
        try:
            self.metrics["portfolio_value"].labels(currency=currency).set(value)
        except Exception as e:
            module_logger.error("更新投資組合價值失敗: %s", e)

    def update_strategy_return(
        self,
        strategy_name: str,
        return_pct: float,
        period: str = "daily"
    ) -> None:
        """更新策略收益率

        Args:
            strategy_name: 策略名稱
            return_pct: 收益率百分比
            period: 時間週期
        """
        try:
            self.metrics["strategy_return"].labels(
                strategy_name=strategy_name,
                period=period
            ).set(return_pct)
        except Exception as e:
            module_logger.error("更新策略收益率失敗: %s", e)

    def update_risk_exposure(
        self,
        var_value: float,
        confidence_level: str = "95%",
        time_horizon: str = "1d"
    ) -> None:
        """更新風險暴露

        Args:
            var_value: VaR 值
            confidence_level: 信心水準
            time_horizon: 時間範圍
        """
        try:
            self.metrics["var_exposure"].labels(
                confidence_level=confidence_level,
                time_horizon=time_horizon
            ).set(var_value)
        except Exception as e:
            module_logger.error("更新風險暴露失敗: %s", e)

    def update_capital_utilization(self, utilization_pct: float) -> None:
        """更新資金使用率

        Args:
            utilization_pct: 使用率百分比
        """
        try:
            self.metrics["capital_utilization"].set(utilization_pct)
        except Exception as e:
            module_logger.error("更新資金使用率失敗: %s", e)

    def record_strategy_signal(self, strategy_name: str, signal_type: str) -> None:
        """記錄策略信號

        Args:
            strategy_name: 策略名稱
            signal_type: 信號類型（buy/sell/hold）
        """
        try:
            self.metrics["strategy_activity"].labels(
                strategy_name=strategy_name,
                signal_type=signal_type
            ).inc()
        except Exception as e:
            module_logger.error("記錄策略信號失敗: %s", e)

    def update_performance_metrics(
        self,
        strategy_name: str,
        sharpe_ratio: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        win_rate: Optional[float] = None
    ) -> None:
        """更新績效指標

        Args:
            strategy_name: 策略名稱
            sharpe_ratio: 夏普比率
            max_drawdown: 最大回撤百分比
            win_rate: 勝率百分比
        """
        try:
            if sharpe_ratio is not None:
                self.metrics["sharpe_ratio"].labels(
                    strategy_name=strategy_name,
                    period="daily"
                ).set(sharpe_ratio)

            if max_drawdown is not None:
                self.metrics["max_drawdown"].labels(
                    strategy_name=strategy_name
                ).set(max_drawdown)

            if win_rate is not None:
                self.metrics["win_rate"].labels(
                    strategy_name=strategy_name
                ).set(win_rate)

        except Exception as e:
            module_logger.error("更新績效指標失敗: %s", e)
