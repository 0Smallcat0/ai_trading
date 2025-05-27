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

Example:
    >>> researcher = StrategyResearcher(price_data)
    >>> trend_results = researcher.evaluate_trend_following_strategies()
    >>> best_strategy = researcher.get_best_strategy()

Note:
    此模組需要配合回測引擎和模型工廠使用
"""

import logging
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.model_selection import ParameterGrid

from src.config import LOG_LEVEL, RESULTS_DIR
from src.core.backtest import Backtest
from src.models.model_factory import create_model
from src.models.rule_based_models import (
    bollinger_bands_strategy,
    moving_average_crossover,
    rsi_strategy,
)

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class StrategyResearchError(Exception):
    """策略研究相關錯誤"""
    pass


class ParameterValidationError(StrategyResearchError):
    """參數驗證錯誤"""
    pass


class StrategyResearcher:
    """
    策略研究器

    用於研究和分析不同的交易策略。

    Attributes:
        price_data: 價格資料
        date_column: 日期欄位名稱
        symbol_column: 股票代碼欄位名稱
        results: 策略評估結果

    Example:
        >>> data = pd.DataFrame({'date': [...], 'close': [...], 'symbol': [...]})
        >>> researcher = StrategyResearcher(data)
        >>> results = researcher.evaluate_trend_following_strategies()
    """

    def __init__(
        self,
        price_data: pd.DataFrame,
        date_column: str = "date",
        symbol_column: str = "symbol",
    ) -> None:
        """
        初始化策略研究器

        Args:
            price_data: 價格資料，必須包含日期、價格和股票代碼欄位
            date_column: 日期欄位名稱
            symbol_column: 股票代碼欄位名稱

        Raises:
            ParameterValidationError: 當輸入參數無效時
        """
        self._validate_input_data(price_data, date_column, symbol_column)

        self.price_data = price_data
        self.date_column = date_column
        self.symbol_column = symbol_column
        self.results: Dict[str, pd.DataFrame] = {}

    def _validate_input_data(
        self,
        price_data: pd.DataFrame,
        date_column: str,
        symbol_column: str
    ) -> None:
        """
        驗證輸入資料

        Args:
            price_data: 價格資料
            date_column: 日期欄位名稱
            symbol_column: 股票代碼欄位名稱

        Raises:
            ParameterValidationError: 當輸入參數無效時
        """
        if price_data.empty:
            raise ParameterValidationError("價格資料不能為空")

        required_columns = [date_column, symbol_column, "close"]
        missing_columns = [col for col in required_columns if col not in price_data.columns]
        if missing_columns:
            raise ParameterValidationError(
                f"價格資料缺少必要欄位: {missing_columns}"
            )

    def evaluate_trend_following_strategies(
        self, param_grid: Optional[Dict[str, List[Any]]] = None
    ) -> pd.DataFrame:
        """
        評估趨勢跟蹤策略

        Args:
            param_grid: 參數網格，包含短期和長期窗口參數

        Returns:
            評估結果資料框，包含各種績效指標

        Raises:
            StrategyResearchError: 當策略評估失敗時

        Example:
            >>> param_grid = {"short_window": [5, 10], "long_window": [20, 50]}
            >>> results = researcher.evaluate_trend_following_strategies(param_grid)
        """
        try:
            if param_grid is None:
                param_grid = {"short_window": [5, 10, 20], "long_window": [20, 50, 100]}

            param_combinations = self._create_valid_param_combinations(param_grid)
            results = self._evaluate_strategy_combinations(
                param_combinations,
                "trend_following",
                "moving_average_crossover",
                moving_average_crossover
            )

            results_df = pd.DataFrame(results)
            self.results["trend_following"] = results_df

            logger.info(f"趨勢跟蹤策略評估完成，共評估 {len(results)} 個參數組合")
            return results_df

        except Exception as e:
            logger.error(f"趨勢跟蹤策略評估失敗: {e}")
            raise StrategyResearchError(f"趨勢跟蹤策略評估失敗: {e}") from e

    def _create_valid_param_combinations(
        self, param_grid: Dict[str, List[Any]]
    ) -> List[Dict[str, Any]]:
        """
        創建有效的參數組合

        Args:
            param_grid: 參數網格

        Returns:
            有效的參數組合列表
        """
        param_combinations = list(ParameterGrid(param_grid))

        # 過濾無效組合（短期窗口必須小於長期窗口）
        valid_combinations = []
        for params in param_combinations:
            if "short_window" in params and "long_window" in params:
                if params["short_window"] < params["long_window"]:
                    valid_combinations.append(params)
            else:
                valid_combinations.append(params)

        return valid_combinations

    def _evaluate_strategy_combinations(
        self,
        param_combinations: List[Dict[str, Any]],
        strategy_type: str,
        model_name: str,
        rule_func: callable
    ) -> List[Dict[str, Any]]:
        """
        評估策略參數組合

        Args:
            param_combinations: 參數組合列表
            strategy_type: 策略類型
            model_name: 模型名稱
            rule_func: 規則函數

        Returns:
            評估結果列表
        """
        results = []
        for params in param_combinations:
            try:
                result = self._evaluate_single_strategy(
                    params, strategy_type, model_name, rule_func
                )
                results.append(result)
            except Exception as e:
                logger.warning(f"參數組合 {params} 評估失敗: {e}")
                continue

        return results

    def _evaluate_single_strategy(
        self,
        params: Dict[str, Any],
        strategy_type: str,
        model_name: str,
        rule_func: callable
    ) -> Dict[str, Any]:
        """
        評估單個策略

        Args:
            params: 策略參數
            strategy_type: 策略類型
            model_name: 模型名稱
            rule_func: 規則函數

        Returns:
            評估結果字典
        """
        # 創建模型名稱
        param_str = "_".join([f"{k}_{v}" for k, v in params.items()])
        model_full_name = f"{model_name}_{param_str}"

        # 創建規則型模型
        model = create_model(
            "rule_based",
            name=model_full_name,
            rule_func=rule_func,
            rule_params=params,
        )

        # 生成訊號
        signals = model.predict(self.price_data)

        # 創建回測器
        backtest = Backtest(
            price_data=self.price_data,
            signals=signals,
            date_column=self.date_column,
            symbol_column=self.symbol_column,
        )

        # 執行回測
        performance = backtest.run()

        # 記錄結果
        result = {
            "strategy": strategy_type,
            "model": model_name,
            **params,
            **performance,
        }

        return result

    def evaluate_mean_reversion_strategies(
        self, param_grid: Optional[Dict[str, List[Any]]] = None
    ) -> pd.DataFrame:
        """
        評估均值回歸策略

        Args:
            param_grid: 參數網格，包含窗口大小和標準差倍數

        Returns:
            評估結果資料框，包含各種績效指標

        Raises:
            StrategyResearchError: 當策略評估失敗時

        Example:
            >>> param_grid = {"window": [10, 20], "num_std": [1.5, 2.0]}
            >>> results = researcher.evaluate_mean_reversion_strategies(param_grid)
        """
        try:
            if param_grid is None:
                param_grid = {"window": [10, 20, 30], "num_std": [1.5, 2.0, 2.5]}

            param_combinations = list(ParameterGrid(param_grid))
            results = self._evaluate_strategy_combinations(
                param_combinations,
                "mean_reversion",
                "bollinger_bands",
                bollinger_bands_strategy
            )

            results_df = pd.DataFrame(results)
            self.results["mean_reversion"] = results_df

            logger.info(f"均值回歸策略評估完成，共評估 {len(results)} 個參數組合")
            return results_df

        except Exception as e:
            logger.error(f"均值回歸策略評估失敗: {e}")
            raise StrategyResearchError(f"均值回歸策略評估失敗: {e}") from e

    def evaluate_oscillator_strategies(
        self, param_grid: Optional[Dict[str, List[Any]]] = None
    ) -> pd.DataFrame:
        """
        評估震盪指標策略

        Args:
            param_grid: 參數網格，包含RSI窗口、超買和超賣閾值

        Returns:
            評估結果資料框，包含各種績效指標

        Raises:
            StrategyResearchError: 當策略評估失敗時

        Example:
            >>> param_grid = {"window": [14, 21], "overbought": [70, 80], "oversold": [20, 30]}
            >>> results = researcher.evaluate_oscillator_strategies(param_grid)
        """
        try:
            if param_grid is None:
                param_grid = {
                    "window": [9, 14, 21],
                    "overbought": [70, 75, 80],
                    "oversold": [20, 25, 30],
                }

            param_combinations = list(ParameterGrid(param_grid))
            results = self._evaluate_strategy_combinations(
                param_combinations,
                "oscillator",
                "rsi",
                rsi_strategy
            )

            results_df = pd.DataFrame(results)
            self.results["oscillator"] = results_df

            logger.info(f"震盪指標策略評估完成，共評估 {len(results)} 個參數組合")
            return results_df

        except Exception as e:
            logger.error(f"震盪指標策略評估失敗: {e}")
            raise StrategyResearchError(f"震盪指標策略評估失敗: {e}") from e

    def compare_strategies(self) -> pd.DataFrame:
        """
        比較不同策略的表現

        Returns:
            比較結果資料框，按夏普比率降序排列

        Raises:
            StrategyResearchError: 當沒有評估結果時

        Example:
            >>> comparison = researcher.compare_strategies()
            >>> print(comparison.head())
        """
        if not self.results:
            raise StrategyResearchError("尚未評估任何策略，請先執行策略評估")

        try:
            # 合併所有結果
            all_results = pd.concat(self.results.values(), ignore_index=True)

            # 按夏普比率排序
            if "sharpe_ratio" in all_results.columns:
                all_results = all_results.sort_values("sharpe_ratio", ascending=False)

            logger.info(f"策略比較完成，共比較 {len(all_results)} 個策略")
            return all_results

        except Exception as e:
            logger.error(f"策略比較失敗: {e}")
            raise StrategyResearchError(f"策略比較失敗: {e}") from e

    def plot_strategy_comparison(
        self, metric: str = "sharpe_ratio", top_n: int = 10
    ) -> None:
        """
        繪製策略比較圖

        Args:
            metric: 比較指標名稱
            top_n: 顯示前N個策略

        Raises:
            StrategyResearchError: 當沒有評估結果或繪圖失敗時

        Example:
            >>> researcher.plot_strategy_comparison("sharpe_ratio", 5)
        """
        if not self.results:
            raise StrategyResearchError("尚未評估任何策略，請先執行策略評估")

        try:
            # 合併所有結果
            all_results = pd.concat(self.results.values(), ignore_index=True)

            # 檢查指標是否存在
            if metric not in all_results.columns:
                available_metrics = [col for col in all_results.columns
                                   if col not in ["strategy", "model"]]
                raise ParameterValidationError(
                    f"指標 '{metric}' 不存在，可用指標: {available_metrics}"
                )

            # 按指標排序並取前N個
            top_results = all_results.sort_values(metric, ascending=False).head(top_n)

            # 創建策略名稱
            top_results = self._create_strategy_names(top_results, metric)

            # 繪製比較圖
            self._plot_comparison_chart(top_results, metric, top_n)

            logger.info(f"策略比較圖已保存: {RESULTS_DIR}/strategy_comparison_{metric}.png")

        except Exception as e:
            logger.error(f"繪製策略比較圖失敗: {e}")
            raise StrategyResearchError(f"繪製策略比較圖失敗: {e}") from e

    def _create_strategy_names(
        self, results_df: pd.DataFrame, exclude_metric: str
    ) -> pd.DataFrame:
        """
        創建策略名稱

        Args:
            results_df: 結果資料框
            exclude_metric: 要排除的指標名稱

        Returns:
            包含策略名稱的資料框
        """
        results_df = results_df.copy()

        def create_name(row):
            base_name = f"{row['strategy']}_{row['model']}"
            param_parts = []
            for k, v in row.items():
                if k not in ["strategy", "model", exclude_metric, "strategy_name"]:
                    if isinstance(v, (int, float)) and not pd.isna(v):
                        param_parts.append(f"{k}={v}")

            if param_parts:
                return f"{base_name}_{'_'.join(param_parts[:3])}"  # 限制參數數量
            return base_name

        results_df["strategy_name"] = results_df.apply(create_name, axis=1)
        return results_df

    def _plot_comparison_chart(
        self, data: pd.DataFrame, metric: str, top_n: int
    ) -> None:
        """
        繪製比較圖表

        Args:
            data: 資料
            metric: 指標名稱
            top_n: 顯示數量
        """
        plt.figure(figsize=(12, 8))
        sns.barplot(x=metric, y="strategy_name", data=data)
        plt.title(f"Top {top_n} Strategies by {metric.replace('_', ' ').title()}")
        plt.xlabel(metric.replace('_', ' ').title())
        plt.ylabel("Strategy")
        plt.tight_layout()

        # 儲存圖表
        output_path = f"{RESULTS_DIR}/strategy_comparison_{metric}.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

    def get_best_strategy(self, metric: str = "sharpe_ratio") -> Dict[str, Any]:
        """
        獲取最佳策略

        Args:
            metric: 比較指標名稱

        Returns:
            最佳策略資訊字典

        Raises:
            StrategyResearchError: 當沒有評估結果時

        Example:
            >>> best = researcher.get_best_strategy("sharpe_ratio")
            >>> print(f"最佳策略: {best['strategy']}_{best['model']}")
        """
        if not self.results:
            raise StrategyResearchError("尚未評估任何策略，請先執行策略評估")

        try:
            # 合併所有結果
            all_results = pd.concat(self.results.values(), ignore_index=True)

            # 檢查指標是否存在
            if metric not in all_results.columns:
                available_metrics = [col for col in all_results.columns
                                   if col not in ["strategy", "model"]]
                raise ParameterValidationError(
                    f"指標 '{metric}' 不存在，可用指標: {available_metrics}"
                )

            # 按指標排序
            all_results = all_results.sort_values(metric, ascending=False)

            # 獲取最佳策略
            best_strategy = all_results.iloc[0].to_dict()

            logger.info(f"最佳策略 (按 {metric}): {best_strategy['strategy']}_{best_strategy['model']}")
            return best_strategy

        except Exception as e:
            logger.error(f"獲取最佳策略失敗: {e}")
            raise StrategyResearchError(f"獲取最佳策略失敗: {e}") from e
