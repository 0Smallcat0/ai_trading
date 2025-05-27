"""
最大回撤計算模組

此模組實現了最大回撤和回撤期間的計算功能。
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from src.core.logger import logger


class MaximumDrawdown:
    """
    最大回撤計算器

    計算投資組合的最大回撤。
    """

    def __init__(
        self, returns: pd.DataFrame, weights: Optional[Dict[str, float]] = None
    ):
        """
        初始化最大回撤計算器

        Args:
            returns: 收益率 DataFrame，每列為一個資產
            weights: 權重字典，資產代碼到權重的映射
        """
        self.returns = returns

        # 如果沒有提供權重，則使用等權重
        if weights is None:
            self.weights = {col: 1.0 / len(returns.columns) for col in returns.columns}
        else:
            # 確保權重和為 1
            total_weight = sum(weights.values())
            self.weights = (
                {k: v / total_weight for k, v in weights.items()}
                if total_weight > 0
                else weights
            )

        logger.info(
            "初始化最大回撤計算器: 資產數量 %s, 數據點數量 %s",
            len(returns.columns),
            len(returns),
        )

    def calculate_max_drawdown(self) -> float:
        """
        計算最大回撤

        Returns:
            float: 最大回撤
        """
        # 計算投資組合收益率
        portfolio_returns = self._calculate_portfolio_returns()

        # 計算累積收益率
        cumulative_returns = (1 + portfolio_returns).cumprod()

        # 計算歷史最高點
        running_max = cumulative_returns.cummax()

        # 計算回撤
        drawdown = (cumulative_returns / running_max) - 1

        # 計算最大回撤
        max_drawdown = drawdown.min()

        return abs(max_drawdown)

    def calculate_drawdown_periods(self) -> List[Dict[str, Any]]:
        """
        計算回撤期間

        Returns:
            List[Dict[str, Any]]: 回撤期間列表，每個元素包含開始日期、結束日期、回撤幅度和持續天數
        """
        # 計算投資組合收益率
        portfolio_returns = self._calculate_portfolio_returns()

        # 計算累積收益率
        cumulative_returns = (1 + portfolio_returns).cumprod()

        # 計算歷史最高點
        running_max = cumulative_returns.cummax()

        # 計算回撤
        drawdown = (cumulative_returns / running_max) - 1

        # 找出回撤期間
        drawdown_periods = []
        in_drawdown = False
        start_date = None
        peak_value = None

        for date, value in drawdown.items():
            if value < 0 and not in_drawdown:
                # 開始回撤
                in_drawdown = True
                start_date = date
                peak_value = running_max[date]
            elif value == 0 and in_drawdown:
                # 結束回撤
                in_drawdown = False
                end_date = date

                # 計算回撤幅度和持續天數
                trough_value = cumulative_returns.loc[start_date:end_date].min()
                drawdown_amount = (trough_value / peak_value) - 1
                duration = (end_date - start_date).days

                # 添加到回撤期間列表
                drawdown_periods.append(
                    {
                        "start_date": start_date,
                        "end_date": end_date,
                        "drawdown": abs(drawdown_amount),
                        "duration": duration,
                    }
                )

        # 如果仍在回撤中，則添加當前回撤
        if in_drawdown:
            end_date = drawdown.index[-1]
            trough_value = cumulative_returns.loc[start_date:end_date].min()
            drawdown_amount = (trough_value / peak_value) - 1
            duration = (end_date - start_date).days

            drawdown_periods.append(
                {
                    "start_date": start_date,
                    "end_date": end_date,
                    "drawdown": abs(drawdown_amount),
                    "duration": duration,
                }
            )

        # 按回撤幅度降序排序
        drawdown_periods.sort(key=lambda x: x["drawdown"], reverse=True)

        return drawdown_periods

    def get_drawdown_series(self) -> pd.Series:
        """
        獲取回撤序列

        Returns:
            pd.Series: 回撤序列
        """
        # 計算投資組合收益率
        portfolio_returns = self._calculate_portfolio_returns()

        # 計算累積收益率
        cumulative_returns = (1 + portfolio_returns).cumprod()

        # 計算歷史最高點
        running_max = cumulative_returns.cummax()

        # 計算回撤
        drawdown = (cumulative_returns / running_max) - 1

        return drawdown

    def get_underwater_curve(self) -> pd.Series:
        """
        獲取水下曲線（回撤曲線）

        Returns:
            pd.Series: 水下曲線
        """
        return self.get_drawdown_series()

    def calculate_recovery_time(self) -> Dict[str, Any]:
        """
        計算恢復時間統計

        Returns:
            Dict[str, Any]: 恢復時間統計信息
        """
        drawdown_periods = self.calculate_drawdown_periods()

        if not drawdown_periods:
            return {
                "avg_recovery_time": 0,
                "max_recovery_time": 0,
                "min_recovery_time": 0,
                "total_drawdown_periods": 0,
            }

        recovery_times = [period["duration"] for period in drawdown_periods]

        return {
            "avg_recovery_time": sum(recovery_times) / len(recovery_times),
            "max_recovery_time": max(recovery_times),
            "min_recovery_time": min(recovery_times),
            "total_drawdown_periods": len(drawdown_periods),
        }

    def _calculate_portfolio_returns(self) -> pd.Series:
        """
        計算投資組合收益率

        Returns:
            pd.Series: 投資組合收益率
        """
        # 確保所有資產都在收益率 DataFrame 中
        weights = {k: v for k, v in self.weights.items() if k in self.returns.columns}

        # 計算投資組合收益率
        portfolio_returns = pd.Series(0.0, index=self.returns.index)
        for asset, weight in weights.items():
            portfolio_returns += self.returns[asset] * weight

        return portfolio_returns
