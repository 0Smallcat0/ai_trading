"""風險監控器模組

此模組負責實時監控風險指標和事件處理。
"""

from typing import Any, Dict, Optional

import pandas as pd

from src.core.logger import logger

from .risk_metrics import RiskMetricsCalculator


class RiskMonitor:
    """風險監控器

    負責實時監控風險指標、檢查投資組合限制和處理風險事件。
    """

    def __init__(self):
        """初始化風險監控器"""
        # 風險指標計算器
        self.risk_metrics_calculator: Optional[RiskMetricsCalculator] = None

        # 監控狀態
        self.monitoring_enabled = True

        # 風險閾值
        self.risk_thresholds = {
            "max_drawdown": 0.2,
            "max_daily_loss": 0.02,
            "max_weekly_loss": 0.05,
            "max_monthly_loss": 0.1,
            "min_sharpe_ratio": 0.5,
            "max_volatility": 0.3,
        }

        logger.info("風險監控器已初始化")

    def set_risk_threshold(self, metric: str, threshold: float) -> bool:
        """設定風險閾值

        Args:
            metric: 風險指標名稱
            threshold: 閾值

        Returns:
            bool: 是否成功設定
        """
        try:
            self.risk_thresholds[metric] = threshold
            logger.info("已設定風險閾值: %s = %s", metric, threshold)
            return True
        except Exception as e:
            logger.error("設定風險閾值時發生錯誤: %s", e)
            return False

    def get_risk_threshold(self, metric: str) -> Optional[float]:
        """獲取風險閾值

        Args:
            metric: 風險指標名稱

        Returns:
            Optional[float]: 閾值，如果不存在則返回 None
        """
        return self.risk_thresholds.get(metric)

    def update_risk_metrics(
        self, returns: pd.Series, risk_free_rate: float = 0.0
    ) -> Dict[str, float]:
        """更新風險指標

        Args:
            returns: 收益率序列
            risk_free_rate: 無風險利率

        Returns:
            Dict[str, float]: 風險指標
        """
        try:
            # 創建風險指標計算器
            self.risk_metrics_calculator = RiskMetricsCalculator(
                returns, risk_free_rate
            )

            # 計算所有風險指標
            metrics = self.risk_metrics_calculator.calculate_all_metrics()

            logger.info("已更新風險指標: %d 個指標", len(metrics))
            return metrics

        except Exception as e:
            logger.error("更新風險指標時發生錯誤: %s", e)
            return {}

    def check_risk_thresholds(self, metrics: Dict[str, float]) -> Dict[str, bool]:
        """檢查風險閾值

        Args:
            metrics: 風險指標字典

        Returns:
            Dict[str, bool]: 各指標是否超過閾值
        """
        violations = {}

        for metric, value in metrics.items():
            threshold = self.risk_thresholds.get(metric)
            if threshold is None:
                continue

            # 檢查是否超過閾值
            if metric in [
                "max_drawdown",
                "max_daily_loss",
                "max_weekly_loss",
                "max_monthly_loss",
                "max_volatility",
            ]:
                # 這些指標值越小越好
                violated = value > threshold
            elif metric in ["min_sharpe_ratio"]:
                # 這些指標值越大越好
                violated = value < threshold
            else:
                # 預設情況，值越小越好
                violated = value > threshold

            violations[metric] = violated

            if violated:
                logger.warning(
                    "風險指標 '%s' 超過閾值: 當前值 %s, 閾值 %s",
                    metric,
                    value,
                    threshold,
                )

        return violations

    def check_portfolio_limits(
        self, symbol: str, value: float, sector: Optional[str] = None
    ) -> bool:
        """檢查投資組合限制

        Args:
            symbol: 股票代碼
            value: 倉位價值
            sector: 行業分類

        Returns:
            bool: 是否符合限制
        """
        # 這個方法將在主風險管理器中實現
        # 這裡只是佔位符
        logger.info("檢查投資組合限制: %s, 價值 %s", symbol, value)
        return True

    def calculate_portfolio_risk(
        self,
        positions: Dict[str, Dict[str, Any]],
        market_data: Optional[pd.DataFrame] = None,
    ) -> Dict[str, float]:
        """計算投資組合風險

        Args:
            positions: 持倉資訊
            market_data: 市場數據

        Returns:
            Dict[str, float]: 投資組合風險指標
        """
        try:
            if not positions:
                return {}

            # 計算投資組合總價值
            total_value = sum(pos.get("value", 0) for pos in positions.values())

            # 計算各股票權重
            weights = {}
            for symbol, position in positions.items():
                weights[symbol] = position.get("value", 0) / total_value

            # 計算集中度風險
            concentration_risk = max(weights.values()) if weights else 0

            # 計算分散化指標（赫芬達爾指數）
            herfindahl_index = sum(w**2 for w in weights.values())

            # 計算行業集中度
            sector_weights = {}
            for symbol, position in positions.items():
                sector = position.get("sector", "Unknown")
                sector_weights[sector] = sector_weights.get(sector, 0) + weights.get(
                    symbol, 0
                )

            sector_concentration = max(sector_weights.values()) if sector_weights else 0

            risk_metrics = {
                "total_value": total_value,
                "position_count": len(positions),
                "concentration_risk": concentration_risk,
                "herfindahl_index": herfindahl_index,
                "sector_concentration": sector_concentration,
                "diversification_ratio": 1 - herfindahl_index,
            }

            logger.info("已計算投資組合風險指標: %d 個指標", len(risk_metrics))
            return risk_metrics

        except Exception as e:
            logger.error("計算投資組合風險時發生錯誤: %s", e)
            return {}

    def generate_risk_report(
        self, metrics: Dict[str, float], violations: Dict[str, bool]
    ) -> Dict[str, Any]:
        """生成風險報告

        Args:
            metrics: 風險指標
            violations: 閾值違規情況

        Returns:
            Dict[str, Any]: 風險報告
        """
        try:
            # 計算風險評分
            total_violations = sum(violations.values())
            total_metrics = len(violations)
            risk_score = (
                (total_metrics - total_violations) / total_metrics * 100
                if total_metrics > 0
                else 100
            )

            # 確定風險等級
            if risk_score >= 80:
                risk_level = "低"
            elif risk_score >= 60:
                risk_level = "中"
            elif risk_score >= 40:
                risk_level = "高"
            else:
                risk_level = "極高"

            # 生成建議
            recommendations = []
            for metric, violated in violations.items():
                if violated:
                    if metric == "max_drawdown":
                        recommendations.append("考慮減少倉位或調整停損策略")
                    elif metric in [
                        "max_daily_loss",
                        "max_weekly_loss",
                        "max_monthly_loss",
                    ]:
                        recommendations.append("檢查交易頻率和倉位大小")
                    elif metric == "min_sharpe_ratio":
                        recommendations.append("優化投資組合配置以提高風險調整後收益")
                    elif metric == "max_volatility":
                        recommendations.append("考慮增加低波動性資產")

            report = {
                "timestamp": pd.Timestamp.now().isoformat(),
                "risk_score": risk_score,
                "risk_level": risk_level,
                "metrics": metrics,
                "violations": violations,
                "recommendations": recommendations,
                "summary": {
                    "total_metrics": total_metrics,
                    "violated_metrics": total_violations,
                    "compliance_rate": (
                        (total_metrics - total_violations) / total_metrics * 100
                        if total_metrics > 0
                        else 100
                    ),
                },
            }

            logger.info(
                "已生成風險報告: 風險等級 %s, 評分 %.1f", risk_level, risk_score
            )
            return report

        except Exception as e:
            logger.error("生成風險報告時發生錯誤: %s", e)
            return {}

    def enable_monitoring(self) -> None:
        """啟用監控"""
        self.monitoring_enabled = True
        logger.info("風險監控已啟用")

    def disable_monitoring(self) -> None:
        """停用監控"""
        self.monitoring_enabled = False
        logger.info("風險監控已停用")

    def is_monitoring_enabled(self) -> bool:
        """檢查監控是否啟用

        Returns:
            bool: 監控是否啟用
        """
        return self.monitoring_enabled

    def get_current_metrics(self) -> Dict[str, float]:
        """獲取當前風險指標

        Returns:
            Dict[str, float]: 當前風險指標
        """
        if self.risk_metrics_calculator is None:
            return {}

        try:
            return self.risk_metrics_calculator.calculate_all_metrics()
        except Exception as e:
            logger.error("獲取當前風險指標時發生錯誤: %s", e)
            return {}
