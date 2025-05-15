# -*- coding: utf-8 -*-
"""
模型訊號優化模組

此模組提供 AI 模型訊號的優化功能，包括：
- 訊號平滑處理
- 訊號延遲修正
- 訊號噪聲過濾
- 訊號衝突解決
- 訊號組合優化
"""

import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from datetime import datetime, timedelta
import warnings
from scipy import stats
from scipy.signal import savgol_filter

from src.config import LOG_LEVEL

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class ModelSignalOptimizer:
    """
    模型訊號優化器

    提供 AI 模型訊號的優化功能。
    """

    def __init__(
        self,
        signals: Optional[pd.DataFrame] = None,
        price_data: Optional[pd.DataFrame] = None,
        volume_data: Optional[pd.DataFrame] = None
    ):
        """
        初始化模型訊號優化器

        Args:
            signals (Optional[pd.DataFrame]): 訊號資料
            price_data (Optional[pd.DataFrame]): 價格資料
            volume_data (Optional[pd.DataFrame]): 成交量資料
        """
        self.signals = signals
        self.price_data = price_data
        self.volume_data = volume_data
        self.optimized_signals = None

    def smooth_signals(
        self,
        signals: Optional[pd.DataFrame] = None,
        method: str = "moving_average",
        window: int = 3
    ) -> pd.DataFrame:
        """
        平滑訊號

        Args:
            signals (Optional[pd.DataFrame]): 訊號資料，如果為 None，則使用類的訊號資料
            method (str): 平滑方法，可選 'moving_average', 'exponential', 'savitzky_golay'
            window (int): 窗口大小

        Returns:
            pd.DataFrame: 平滑後的訊號資料
        """
        signals = signals if signals is not None else self.signals
        
        if signals is None:
            logger.warning("沒有訊號資料，無法平滑")
            return pd.DataFrame()
        
        # 複製訊號
        smoothed_signals = signals.copy()
        
        # 對每個股票分別處理
        for stock_id in signals.index.get_level_values(0).unique():
            stock_signals = signals.loc[stock_id]["signal"].astype(float)
            
            # 根據平滑方法處理
            if method == "moving_average":
                # 移動平均
                smoothed = stock_signals.rolling(window=window, center=True).mean()
            elif method == "exponential":
                # 指數平滑
                smoothed = stock_signals.ewm(span=window).mean()
            elif method == "savitzky_golay":
                # Savitzky-Golay 濾波
                if len(stock_signals) >= window:
                    try:
                        smoothed = pd.Series(
                            savgol_filter(stock_signals, window, 2),
                            index=stock_signals.index
                        )
                    except Exception as e:
                        logger.warning(f"Savitzky-Golay 濾波失敗: {e}，使用移動平均替代")
                        smoothed = stock_signals.rolling(window=window, center=True).mean()
                else:
                    smoothed = stock_signals
            else:
                logger.warning(f"未知的平滑方法: {method}，使用移動平均替代")
                smoothed = stock_signals.rolling(window=window, center=True).mean()
            
            # 將平滑後的值轉換為訊號
            smoothed_signals.loc[stock_id, "signal"] = smoothed.apply(
                lambda x: 1 if x > 0.5 else (-1 if x < -0.5 else 0)
            )
        
        # 儲存平滑後的訊號
        self.optimized_signals = smoothed_signals
        
        return smoothed_signals

    def filter_noise(
        self,
        signals: Optional[pd.DataFrame] = None,
        threshold: float = 0.5,
        min_consecutive: int = 2
    ) -> pd.DataFrame:
        """
        過濾訊號噪聲

        Args:
            signals (Optional[pd.DataFrame]): 訊號資料，如果為 None，則使用類的訊號資料
            threshold (float): 閾值，訊號強度低於此值視為噪聲
            min_consecutive (int): 最小連續訊號數，少於此數視為噪聲

        Returns:
            pd.DataFrame: 過濾後的訊號資料
        """
        signals = signals if signals is not None else self.signals
        
        if signals is None:
            logger.warning("沒有訊號資料，無法過濾噪聲")
            return pd.DataFrame()
        
        # 複製訊號
        filtered_signals = signals.copy()
        
        # 對每個股票分別處理
        for stock_id in signals.index.get_level_values(0).unique():
            stock_signals = signals.loc[stock_id]["signal"]
            
            # 初始化過濾後的訊號
            filtered = pd.Series(0, index=stock_signals.index)
            
            # 計算連續訊號
            consecutive_count = 0
            last_signal = 0
            
            for i, signal in enumerate(stock_signals):
                if signal == last_signal and signal != 0:
                    consecutive_count += 1
                else:
                    consecutive_count = 1 if signal != 0 else 0
                
                # 如果連續訊號數達到閾值，則保留訊號
                if consecutive_count >= min_consecutive:
                    filtered.iloc[i] = signal
                
                last_signal = signal
            
            # 更新過濾後的訊號
            filtered_signals.loc[stock_id, "signal"] = filtered
        
        # 儲存過濾後的訊號
        self.optimized_signals = filtered_signals
        
        return filtered_signals

    def correct_delay(
        self,
        signals: Optional[pd.DataFrame] = None,
        price_data: Optional[pd.DataFrame] = None,
        delay: int = 1
    ) -> pd.DataFrame:
        """
        修正訊號延遲

        Args:
            signals (Optional[pd.DataFrame]): 訊號資料，如果為 None，則使用類的訊號資料
            price_data (Optional[pd.DataFrame]): 價格資料，如果為 None，則使用類的價格資料
            delay (int): 延遲天數

        Returns:
            pd.DataFrame: 修正後的訊號資料
        """
        signals = signals if signals is not None else self.signals
        price_data = price_data if price_data is not None else self.price_data
        
        if signals is None:
            logger.warning("沒有訊號資料，無法修正延遲")
            return pd.DataFrame()
        
        if price_data is None:
            logger.warning("沒有價格資料，無法修正延遲")
            return signals
        
        # 複製訊號
        corrected_signals = signals.copy()
        
        # 對每個股票分別處理
        for stock_id in signals.index.get_level_values(0).unique():
            stock_signals = signals.loc[stock_id]["signal"]
            
            # 前移訊號
            corrected_signals.loc[stock_id, "signal"] = stock_signals.shift(-delay)
        
        # 填充 NaN
        corrected_signals.fillna(0, inplace=True)
        
        # 儲存修正後的訊號
        self.optimized_signals = corrected_signals
        
        return corrected_signals

    def resolve_conflicts(
        self,
        signals_dict: Dict[str, pd.DataFrame],
        method: str = "majority_vote",
        weights: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        """
        解決訊號衝突

        Args:
            signals_dict (Dict[str, pd.DataFrame]): 訊號字典，鍵為訊號名稱，值為訊號資料
            method (str): 解決方法，可選 'majority_vote', 'weighted_average', 'priority'
            weights (Optional[Dict[str, float]]): 權重字典，鍵為訊號名稱，值為權重

        Returns:
            pd.DataFrame: 解決衝突後的訊號資料
        """
        if not signals_dict:
            logger.warning("沒有訊號資料，無法解決衝突")
            return pd.DataFrame()
        
        # 獲取所有訊號的共同索引
        common_index = None
        for signals in signals_dict.values():
            if common_index is None:
                common_index = signals.index
            else:
                common_index = common_index.intersection(signals.index)
        
        if common_index.empty:
            logger.warning("訊號資料沒有共同索引，無法解決衝突")
            return pd.DataFrame()
        
        # 初始化解決衝突後的訊號
        resolved_signals = pd.DataFrame(index=common_index)
        resolved_signals["signal"] = 0
        
        # 根據解決方法處理
        if method == "majority_vote":
            # 多數投票
            for idx in common_index:
                votes = [signals.loc[idx, "signal"] for signals in signals_dict.values()]
                buy_votes = sum(1 for vote in votes if vote > 0)
                sell_votes = sum(1 for vote in votes if vote < 0)
                
                if buy_votes > sell_votes:
                    resolved_signals.loc[idx, "signal"] = 1
                elif sell_votes > buy_votes:
                    resolved_signals.loc[idx, "signal"] = -1
        
        elif method == "weighted_average":
            # 加權平均
            if weights is None:
                # 使用等權重
                weights = {name: 1.0 / len(signals_dict) for name in signals_dict}
            
            # 標準化權重
            total_weight = sum(weights.values())
            weights = {name: weight / total_weight for name, weight in weights.items()}
            
            # 計算加權平均
            for idx in common_index:
                weighted_sum = sum(
                    signals.loc[idx, "signal"] * weights.get(name, 0)
                    for name, signals in signals_dict.items()
                )
                
                resolved_signals.loc[idx, "signal"] = (
                    1 if weighted_sum > 0.5 else (-1 if weighted_sum < -0.5 else 0)
                )
        
        elif method == "priority":
            # 優先級
            if weights is None:
                # 使用訊號名稱作為優先級
                priority_list = sorted(signals_dict.keys())
            else:
                # 使用權重作為優先級
                priority_list = sorted(weights.keys(), key=lambda x: weights.get(x, 0), reverse=True)
            
            # 根據優先級解決衝突
            for idx in common_index:
                for name in priority_list:
                    if name in signals_dict and idx in signals_dict[name].index:
                        signal = signals_dict[name].loc[idx, "signal"]
                        if signal != 0:
                            resolved_signals.loc[idx, "signal"] = signal
                            break
        
        else:
            logger.warning(f"未知的解決方法: {method}，使用多數投票替代")
            # 使用多數投票
            for idx in common_index:
                votes = [signals.loc[idx, "signal"] for signals in signals_dict.values()]
                buy_votes = sum(1 for vote in votes if vote > 0)
                sell_votes = sum(1 for vote in votes if vote < 0)
                
                if buy_votes > sell_votes:
                    resolved_signals.loc[idx, "signal"] = 1
                elif sell_votes > buy_votes:
                    resolved_signals.loc[idx, "signal"] = -1
        
        # 儲存解決衝突後的訊號
        self.optimized_signals = resolved_signals
        
        return resolved_signals

    def optimize_combination(
        self,
        signals_dict: Dict[str, pd.DataFrame],
        price_data: Optional[pd.DataFrame] = None,
        optimization_metric: str = "sharpe_ratio",
        lookback_period: int = 252
    ) -> Tuple[pd.DataFrame, Dict[str, float]]:
        """
        優化訊號組合

        Args:
            signals_dict (Dict[str, pd.DataFrame]): 訊號字典，鍵為訊號名稱，值為訊號資料
            price_data (Optional[pd.DataFrame]): 價格資料，如果為 None，則使用類的價格資料
            optimization_metric (str): 優化指標，可選 'sharpe_ratio', 'sortino_ratio', 'calmar_ratio', 'win_rate'
            lookback_period (int): 回顧期間

        Returns:
            Tuple[pd.DataFrame, Dict[str, float]]: 優化後的訊號資料和最佳權重
        """
        price_data = price_data if price_data is not None else self.price_data
        
        if not signals_dict:
            logger.warning("沒有訊號資料，無法優化組合")
            return pd.DataFrame(), {}
        
        if price_data is None:
            logger.warning("沒有價格資料，無法優化組合")
            return pd.DataFrame(), {}
        
        # 獲取所有訊號的共同索引
        common_index = None
        for signals in signals_dict.values():
            if common_index is None:
                common_index = signals.index
            else:
                common_index = common_index.intersection(signals.index)
        
        if common_index.empty:
            logger.warning("訊號資料沒有共同索引，無法優化組合")
            return pd.DataFrame(), {}
        
        # 計算每個訊號的績效
        performance = {}
        
        for name, signals in signals_dict.items():
            # 計算訊號的收益率
            returns = self._calculate_signal_returns(signals.loc[common_index], price_data.loc[common_index])
            
            # 計算績效指標
            if optimization_metric == "sharpe_ratio":
                performance[name] = self._calculate_sharpe_ratio(returns)
            elif optimization_metric == "sortino_ratio":
                performance[name] = self._calculate_sortino_ratio(returns)
            elif optimization_metric == "calmar_ratio":
                performance[name] = self._calculate_calmar_ratio(returns)
            elif optimization_metric == "win_rate":
                performance[name] = self._calculate_win_rate(returns)
            else:
                logger.warning(f"未知的優化指標: {optimization_metric}，使用夏普比率替代")
                performance[name] = self._calculate_sharpe_ratio(returns)
        
        # 計算最佳權重
        total_performance = sum(max(0.1, perf) for perf in performance.values())
        weights = {name: max(0.1, perf) / total_performance for name, perf in performance.items()}
        
        # 使用最佳權重組合訊號
        optimized_signals = self.resolve_conflicts(signals_dict, method="weighted_average", weights=weights)
        
        # 儲存優化後的訊號
        self.optimized_signals = optimized_signals
        
        return optimized_signals, weights

    def _calculate_signal_returns(
        self,
        signals: pd.DataFrame,
        price_data: pd.DataFrame
    ) -> pd.Series:
        """
        計算訊號收益率

        Args:
            signals (pd.DataFrame): 訊號資料
            price_data (pd.DataFrame): 價格資料

        Returns:
            pd.Series: 收益率
        """
        # 確保價格資料有 'close' 列
        if "close" not in price_data.columns:
            logger.warning("價格資料缺少 'close' 列，無法計算收益率")
            return pd.Series()
        
        # 初始化收益率
        returns = pd.Series(0.0, index=signals.index)
        
        # 對每個股票分別處理
        for stock_id in signals.index.get_level_values(0).unique():
            stock_signals = signals.loc[stock_id]["signal"]
            stock_prices = price_data.loc[stock_id]["close"]
            
            # 計算價格變化
            price_changes = stock_prices.pct_change()
            
            # 計算訊號收益率
            stock_returns = stock_signals.shift(1) * price_changes
            
            # 更新收益率
            returns.loc[stock_id] = stock_returns
        
        return returns

    def _calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.0) -> float:
        """
        計算夏普比率

        Args:
            returns (pd.Series): 收益率
            risk_free_rate (float): 無風險利率

        Returns:
            float: 夏普比率
        """
        if returns.empty:
            return 0.0
        
        # 計算年化收益率
        annual_return = returns.mean() * 252
        
        # 計算年化波動率
        annual_volatility = returns.std() * np.sqrt(252)
        
        # 避免除以零
        if annual_volatility == 0:
            return 0.0
        
        # 計算夏普比率
        sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility
        
        return sharpe_ratio

    def _calculate_sortino_ratio(self, returns: pd.Series, risk_free_rate: float = 0.0) -> float:
        """
        計算索提諾比率

        Args:
            returns (pd.Series): 收益率
            risk_free_rate (float): 無風險利率

        Returns:
            float: 索提諾比率
        """
        if returns.empty:
            return 0.0
        
        # 計算年化收益率
        annual_return = returns.mean() * 252
        
        # 計算下行風險
        downside_returns = returns[returns < 0]
        downside_risk = downside_returns.std() * np.sqrt(252) if not downside_returns.empty else 0.0
        
        # 避免除以零
        if downside_risk == 0:
            return 0.0
        
        # 計算索提諾比率
        sortino_ratio = (annual_return - risk_free_rate) / downside_risk
        
        return sortino_ratio

    def _calculate_calmar_ratio(self, returns: pd.Series) -> float:
        """
        計算卡爾馬比率

        Args:
            returns (pd.Series): 收益率

        Returns:
            float: 卡爾馬比率
        """
        if returns.empty:
            return 0.0
        
        # 計算年化收益率
        annual_return = returns.mean() * 252
        
        # 計算最大回撤
        cumulative_returns = (1 + returns).cumprod()
        max_drawdown = (cumulative_returns / cumulative_returns.cummax() - 1).min()
        
        # 避免除以零
        if max_drawdown == 0:
            return 0.0
        
        # 計算卡爾馬比率
        calmar_ratio = annual_return / abs(max_drawdown)
        
        return calmar_ratio

    def _calculate_win_rate(self, returns: pd.Series) -> float:
        """
        計算勝率

        Args:
            returns (pd.Series): 收益率

        Returns:
            float: 勝率
        """
        if returns.empty:
            return 0.0
        
        # 計算勝率
        win_rate = (returns > 0).mean()
        
        return win_rate
