"""回測績效計算模組

此模組負責計算回測的各種績效指標。
"""

import logging
from typing import Dict, List
import numpy as np

# 設定日誌
logger = logging.getLogger(__name__)


class BacktestPerformanceCalculator:
    """回測績效計算器"""

    def __init__(self):
        """初始化績效計算器"""
        pass

    def calculate_performance_metrics(self, results: Dict, config) -> Dict:
        """計算績效指標

        Args:
            results: 回測結果
            config: 回測配置

        Returns:
            Dict: 績效指標
        """
        try:
            logger.info("開始計算績效指標")

            # 從結果中提取資料
            equity_curve = results.get("equity_curve", [])
            trades = results.get("trades", [])

            if not equity_curve:
                logger.warning("權益曲線為空，返回空指標")
                return {}

            # 基本指標
            initial_capital = config.initial_capital
            final_capital = equity_curve[-1] if equity_curve else initial_capital
            total_return = (final_capital / initial_capital - 1) * 100

            # 計算年化報酬率
            days = (config.end_date - config.start_date).days
            annual_return = (
                ((final_capital / initial_capital) ** (365 / days) - 1) * 100
                if days > 0
                else 0
            )

            # 計算日收益率
            daily_returns = self._calculate_daily_returns(equity_curve)

            # 夏普比率
            sharpe_ratio = self._calculate_sharpe_ratio(daily_returns)

            # 最大回撤
            max_drawdown = self._calculate_max_drawdown(equity_curve)

            # 交易統計
            trade_stats = self._calculate_trade_statistics(trades)

            # 風險指標
            risk_metrics = self._calculate_risk_metrics(daily_returns, annual_return)

            # 合併所有指標
            metrics = {
                "initial_capital": initial_capital,
                "final_capital": final_capital,
                "total_return": total_return,
                "annual_return": annual_return,
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": max_drawdown,
                **trade_stats,
                **risk_metrics,
            }

            logger.info("績效指標計算完成")
            return metrics

        except Exception as e:
            logger.error("計算績效指標失敗: %s", e)
            return {}

    def _calculate_daily_returns(self, equity_curve: List[float]) -> List[float]:
        """計算日收益率

        Args:
            equity_curve: 權益曲線

        Returns:
            List[float]: 日收益率列表
        """
        daily_returns = []
        for i in range(1, len(equity_curve)):
            daily_return = equity_curve[i] / equity_curve[i - 1] - 1
            daily_returns.append(daily_return)
        return daily_returns

    def _calculate_sharpe_ratio(self, daily_returns: List[float]) -> float:
        """計算夏普比率

        Args:
            daily_returns: 日收益率

        Returns:
            float: 夏普比率
        """
        if not daily_returns:
            return 0

        mean_return = np.mean(daily_returns)
        std_return = np.std(daily_returns)
        sharpe_ratio = (
            (mean_return / std_return * np.sqrt(252)) if std_return > 0 else 0
        )
        return sharpe_ratio

    def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """計算最大回撤

        Args:
            equity_curve: 權益曲線

        Returns:
            float: 最大回撤百分比
        """
        max_drawdown = 0
        peak = equity_curve[0]
        for value in equity_curve:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        return max_drawdown * 100

    def _calculate_trade_statistics(self, trades: List[Dict]) -> Dict:
        """計算交易統計

        Args:
            trades: 交易列表

        Returns:
            Dict: 交易統計指標
        """
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.get("profit", 0) > 0])
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        # 盈虧比
        wins = [t["profit"] for t in trades if t.get("profit", 0) > 0]
        losses = [abs(t["profit"]) for t in trades if t.get("profit", 0) < 0]
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 1
        profit_ratio = avg_win / avg_loss if avg_loss > 0 else 0

        # 平均持倉天數
        hold_days = [t.get("hold_days", 0) for t in trades if "hold_days" in t]
        avg_trade_duration = np.mean(hold_days) if hold_days else 0

        # 最大連續勝負次數
        consecutive_stats = self._calculate_consecutive_stats(trades)

        return {
            "win_rate": win_rate,
            "profit_ratio": profit_ratio,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "avg_trade_duration": avg_trade_duration,
            **consecutive_stats,
        }

    def _calculate_consecutive_stats(self, trades: List[Dict]) -> Dict:
        """計算連續勝負統計

        Args:
            trades: 交易列表

        Returns:
            Dict: 連續勝負統計
        """
        consecutive_wins = 0
        consecutive_losses = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0

        for trade in trades:
            if trade.get("profit", 0) > 0:
                consecutive_wins += 1
                consecutive_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
            else:
                consecutive_losses += 1
                consecutive_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)

        return {
            "max_consecutive_wins": max_consecutive_wins,
            "max_consecutive_losses": max_consecutive_losses,
        }

    def _calculate_risk_metrics(
        self, daily_returns: List[float], annual_return: float
    ) -> Dict:
        """計算風險指標

        Args:
            daily_returns: 日收益率
            annual_return: 年化報酬率

        Returns:
            Dict: 風險指標
        """
        if not daily_returns:
            return {
                "calmar_ratio": 0,
                "sortino_ratio": 0,
                "var_95": 0,
                "beta": 1.0,
                "alpha": 0,
                "information_ratio": 0,
            }

        mean_return = np.mean(daily_returns)
        std_return = np.std(daily_returns)

        # 卡瑪比率 (Calmar Ratio)
        max_drawdown = self._calculate_max_drawdown(
            [1] + [1 + r for r in daily_returns]
        )
        calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0

        # 索提諾比率 (Sortino Ratio)
        negative_returns = [r for r in daily_returns if r < 0]
        downside_std = np.std(negative_returns) if negative_returns else 0
        sortino_ratio = (
            (mean_return / downside_std * np.sqrt(252)) if downside_std > 0 else 0
        )

        # VaR (95% 信心水準)
        var_95 = np.percentile(daily_returns, 5) * 100 if daily_returns else 0

        # Beta 和 Alpha (相對於基準)
        # 這裡使用簡化計算，實際應該與市場基準比較
        beta = 1.0  # 簡化假設
        alpha = annual_return - (beta * 8.0)  # 假設市場報酬率為8%

        # 資訊比率
        tracking_error = std_return * np.sqrt(252) * 100 if std_return > 0 else 1
        information_ratio = alpha / tracking_error if tracking_error > 0 else 0

        return {
            "calmar_ratio": calmar_ratio,
            "sortino_ratio": sortino_ratio,
            "var_95": var_95,
            "beta": beta,
            "alpha": alpha,
            "information_ratio": information_ratio,
        }
