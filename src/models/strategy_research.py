# -*- coding: utf-8 -*-
"""
策略研究模組

此模組用於研究和分析不同的交易策略，包括：
- 趨勢跟蹤策略
- 均值回歸策略
- 套利策略
- 事件驅動策略

主要功能：
- 策略回測和評估
- 策略參數優化
- 策略比較和選擇
- 策略組合和權重分配
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import ParameterGrid

from src.config import LOG_LEVEL, RESULTS_DIR
from src.core.backtest import Backtest
from src.models.model_factory import create_model
from src.models.rule_based_models import (
    moving_average_crossover,
    rsi_strategy,
    bollinger_bands_strategy
)

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class StrategyResearcher:
    """
    策略研究器

    用於研究和分析不同的交易策略。
    """

    def __init__(self, price_data: pd.DataFrame, date_column: str = "date", symbol_column: str = "symbol"):
        """
        初始化策略研究器

        Args:
            price_data (pd.DataFrame): 價格資料
            date_column (str): 日期欄位名稱
            symbol_column (str): 股票代碼欄位名稱
        """
        self.price_data = price_data
        self.date_column = date_column
        self.symbol_column = symbol_column
        self.results = {}

    def evaluate_trend_following_strategies(
        self, 
        param_grid: Optional[Dict[str, List[Any]]] = None
    ) -> pd.DataFrame:
        """
        評估趨勢跟蹤策略

        Args:
            param_grid (Optional[Dict[str, List[Any]]]): 參數網格

        Returns:
            pd.DataFrame: 評估結果
        """
        if param_grid is None:
            param_grid = {
                "short_window": [5, 10, 20],
                "long_window": [20, 50, 100]
            }
        
        # 創建參數組合
        param_combinations = list(ParameterGrid(param_grid))
        
        # 評估每個參數組合
        results = []
        for params in param_combinations:
            # 確保短期窗口小於長期窗口
            if params["short_window"] >= params["long_window"]:
                continue
            
            # 創建規則型模型
            model = create_model(
                "rule_based",
                name=f"ma_cross_{params['short_window']}_{params['long_window']}",
                rule_func=moving_average_crossover,
                rule_params=params
            )
            
            # 生成訊號
            signals = model.predict(self.price_data)
            
            # 創建回測器
            backtest = Backtest(
                price_data=self.price_data,
                signals=signals,
                date_column=self.date_column,
                symbol_column=self.symbol_column
            )
            
            # 執行回測
            performance = backtest.run()
            
            # 記錄結果
            result = {
                "strategy": "trend_following",
                "model": "moving_average_crossover",
                **params,
                **performance
            }
            results.append(result)
        
        # 創建結果資料框
        results_df = pd.DataFrame(results)
        
        # 儲存結果
        self.results["trend_following"] = results_df
        
        return results_df

    def evaluate_mean_reversion_strategies(
        self, 
        param_grid: Optional[Dict[str, List[Any]]] = None
    ) -> pd.DataFrame:
        """
        評估均值回歸策略

        Args:
            param_grid (Optional[Dict[str, List[Any]]]): 參數網格

        Returns:
            pd.DataFrame: 評估結果
        """
        if param_grid is None:
            param_grid = {
                "window": [10, 20, 30],
                "num_std": [1.5, 2.0, 2.5]
            }
        
        # 創建參數組合
        param_combinations = list(ParameterGrid(param_grid))
        
        # 評估每個參數組合
        results = []
        for params in param_combinations:
            # 創建規則型模型
            model = create_model(
                "rule_based",
                name=f"bollinger_{params['window']}_{params['num_std']}",
                rule_func=bollinger_bands_strategy,
                rule_params=params
            )
            
            # 生成訊號
            signals = model.predict(self.price_data)
            
            # 創建回測器
            backtest = Backtest(
                price_data=self.price_data,
                signals=signals,
                date_column=self.date_column,
                symbol_column=self.symbol_column
            )
            
            # 執行回測
            performance = backtest.run()
            
            # 記錄結果
            result = {
                "strategy": "mean_reversion",
                "model": "bollinger_bands",
                **params,
                **performance
            }
            results.append(result)
        
        # 創建結果資料框
        results_df = pd.DataFrame(results)
        
        # 儲存結果
        self.results["mean_reversion"] = results_df
        
        return results_df

    def evaluate_oscillator_strategies(
        self, 
        param_grid: Optional[Dict[str, List[Any]]] = None
    ) -> pd.DataFrame:
        """
        評估震盪指標策略

        Args:
            param_grid (Optional[Dict[str, List[Any]]]): 參數網格

        Returns:
            pd.DataFrame: 評估結果
        """
        if param_grid is None:
            param_grid = {
                "window": [9, 14, 21],
                "overbought": [70, 75, 80],
                "oversold": [20, 25, 30]
            }
        
        # 創建參數組合
        param_combinations = list(ParameterGrid(param_grid))
        
        # 評估每個參數組合
        results = []
        for params in param_combinations:
            # 創建規則型模型
            model = create_model(
                "rule_based",
                name=f"rsi_{params['window']}_{params['oversold']}_{params['overbought']}",
                rule_func=rsi_strategy,
                rule_params=params
            )
            
            # 生成訊號
            signals = model.predict(self.price_data)
            
            # 創建回測器
            backtest = Backtest(
                price_data=self.price_data,
                signals=signals,
                date_column=self.date_column,
                symbol_column=self.symbol_column
            )
            
            # 執行回測
            performance = backtest.run()
            
            # 記錄結果
            result = {
                "strategy": "oscillator",
                "model": "rsi",
                **params,
                **performance
            }
            results.append(result)
        
        # 創建結果資料框
        results_df = pd.DataFrame(results)
        
        # 儲存結果
        self.results["oscillator"] = results_df
        
        return results_df

    def compare_strategies(self) -> pd.DataFrame:
        """
        比較不同策略的表現

        Returns:
            pd.DataFrame: 比較結果
        """
        if not self.results:
            logger.warning("尚未評估任何策略")
            return pd.DataFrame()
        
        # 合併所有結果
        all_results = pd.concat(self.results.values())
        
        # 按夏普比率排序
        all_results = all_results.sort_values("sharpe_ratio", ascending=False)
        
        return all_results

    def plot_strategy_comparison(self, metric: str = "sharpe_ratio", top_n: int = 10) -> None:
        """
        繪製策略比較圖

        Args:
            metric (str): 比較指標
            top_n (int): 顯示前 N 個策略
        """
        if not self.results:
            logger.warning("尚未評估任何策略")
            return
        
        # 合併所有結果
        all_results = pd.concat(self.results.values())
        
        # 按指標排序
        all_results = all_results.sort_values(metric, ascending=False).head(top_n)
        
        # 創建策略名稱
        all_results["strategy_name"] = all_results.apply(
            lambda row: f"{row['strategy']}_{row['model']}_" + "_".join([f"{k}={v}" for k, v in row.items() 
                                                                        if k not in ["strategy", "model", metric]]),
            axis=1
        )
        
        # 繪製比較圖
        plt.figure(figsize=(12, 8))
        sns.barplot(x=metric, y="strategy_name", data=all_results)
        plt.title(f"Top {top_n} Strategies by {metric}")
        plt.tight_layout()
        
        # 儲存圖表
        plt.savefig(f"{RESULTS_DIR}/strategy_comparison_{metric}.png")
        plt.close()

    def get_best_strategy(self, metric: str = "sharpe_ratio") -> Dict[str, Any]:
        """
        獲取最佳策略

        Args:
            metric (str): 比較指標

        Returns:
            Dict[str, Any]: 最佳策略資訊
        """
        if not self.results:
            logger.warning("尚未評估任何策略")
            return {}
        
        # 合併所有結果
        all_results = pd.concat(self.results.values())
        
        # 按指標排序
        all_results = all_results.sort_values(metric, ascending=False)
        
        # 獲取最佳策略
        best_strategy = all_results.iloc[0].to_dict()
        
        return best_strategy
