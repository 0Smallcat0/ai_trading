# -*- coding: utf-8 -*-
"""
策略重新回測模組

此模組負責根據市場變化重新回測策略，並提供參數調整和優化功能。
主要功能：
- 根據市場變化重新回測策略
- 調整策略參數以提高性能
- 記錄和比較優化前後的結果
- 生成策略優化報告
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
from sklearn.model_selection import ParameterGrid

from src.config import LOG_LEVEL, RESULTS_DIR
from src.core.backtest import Backtest, MultiStrategyBacktest
from src.core.data_ingest import load_data
from src.models.strategy_research import StrategyResearcher
from src.strategy.strategy import Strategy
from src.utils.utils import ensure_dir

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class StrategyRebacktester:
    """策略重新回測器"""

    def __init__(self, output_dir: Optional[str] = None):
        """
        初始化策略重新回測器

        Args:
            output_dir: 輸出目錄，如果為 None，則使用 RESULTS_DIR/strategy_rebacktest
        """
        self.output_dir = output_dir or os.path.join(RESULTS_DIR, "strategy_rebacktest")
        ensure_dir(self.output_dir)

        # 策略研究器
        self.strategy_researcher = StrategyResearcher()

        # 回測結果
        self.backtest_results = {}

        # 優化結果
        self.optimization_results = {}

        # 市場變化分析結果
        self.market_change_analysis = {}

    def analyze_market_changes(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        reference_period: int = 90,
    ) -> Dict[str, Any]:
        """
        分析市場變化

        Args:
            start_date: 開始日期，如果為 None，則使用當前日期減去 reference_period
            end_date: 結束日期，如果為 None，則使用當前日期
            reference_period: 參考期間（天數）

        Returns:
            Dict[str, Any]: 市場變化分析結果
        """
        # 設定日期範圍
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=reference_period)

        # 載入資料
        data = load_data(start_date, end_date)
        if "price" not in data:
            logger.error("無法載入價格資料")
            return {}

        price_df = data["price"]

        # 計算市場指標
        market_indicators = self._calculate_market_indicators(price_df)

        # 分析市場變化
        market_changes = self._detect_market_changes(
            market_indicators, reference_period
        )

        # 儲存分析結果
        self.market_change_analysis = {
            "start_date": start_date,
            "end_date": end_date,
            "reference_period": reference_period,
            "market_indicators": market_indicators,
            "market_changes": market_changes,
        }

        return self.market_change_analysis

    def _calculate_market_indicators(
        self, price_df: pd.DataFrame
    ) -> Dict[str, pd.DataFrame]:
        """
        計算市場指標

        Args:
            price_df: 價格資料

        Returns:
            Dict[str, pd.DataFrame]: 市場指標
        """
        # 計算收益率
        returns = price_df.pct_change().dropna()

        # 計算波動率（20日滾動標準差）
        volatility = returns.rolling(window=20).std().dropna()

        # 計算趨勢（50日移動平均線與20日移動平均線的差異）
        ma_20 = price_df.rolling(window=20).mean()
        ma_50 = price_df.rolling(window=50).mean()
        trend = (ma_20 / ma_50 - 1).dropna()

        # 計算相關性（20日滾動相關性）
        correlation = returns.rolling(window=20).corr().dropna()

        return {
            "returns": returns,
            "volatility": volatility,
            "trend": trend,
            "correlation": correlation,
        }

    def _detect_market_changes(
        self, market_indicators: Dict[str, pd.DataFrame], reference_period: int
    ) -> Dict[str, Any]:
        """
        檢測市場變化

        Args:
            market_indicators: 市場指標
            reference_period: 參考期間（天數）

        Returns:
            Dict[str, Any]: 市場變化
        """
        changes = {}

        # 檢測波動率變化
        if "volatility" in market_indicators:
            volatility = market_indicators["volatility"]
            recent_volatility = volatility.iloc[-20:].mean()
            reference_volatility = volatility.iloc[-reference_period:-20].mean()
            volatility_change = (
                (recent_volatility / reference_volatility - 1)
                if reference_volatility.any()
                else 0
            )
            changes["volatility_change"] = volatility_change

        # 檢測趨勢變化
        if "trend" in market_indicators:
            trend = market_indicators["trend"]
            recent_trend = trend.iloc[-20:].mean()
            reference_trend = trend.iloc[-reference_period:-20].mean()
            trend_change = recent_trend - reference_trend
            changes["trend_change"] = trend_change

        # 檢測相關性變化
        if "correlation" in market_indicators:
            correlation = market_indicators["correlation"]
            recent_correlation = correlation.iloc[-20:].mean()
            reference_correlation = correlation.iloc[-reference_period:-20].mean()
            correlation_change = recent_correlation - reference_correlation
            changes["correlation_change"] = correlation_change

        return changes

    def rebacktest_strategy(
        self,
        strategy_name: str,
        strategy_params: Dict[str, Any],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        initial_capital: float = 1000000,
        transaction_cost: float = 0.001425,
        slippage: float = 0.001,
        tax: float = 0.003,
    ) -> Dict[str, Any]:
        """
        重新回測策略

        Args:
            strategy_name: 策略名稱
            strategy_params: 策略參數
            start_date: 開始日期
            end_date: 結束日期
            initial_capital: 初始資金
            transaction_cost: 交易成本
            slippage: 滑價
            tax: 稅率

        Returns:
            Dict[str, Any]: 回測結果
        """
        # 載入資料
        data = load_data(start_date, end_date)
        if "price" not in data:
            logger.error("無法載入價格資料")
            return {}

        price_df = data["price"]

        # 創建策略
        strategy = self._create_strategy(strategy_name, strategy_params)
        if strategy is None:
            logger.error(f"無法創建策略: {strategy_name}")
            return {}

        # 生成訊號
        signals = strategy.generate_signals(price_df)

        # 執行回測
        backtest = Backtest(
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            transaction_cost=transaction_cost,
            slippage=slippage,
            tax=tax,
        )

        # 執行回測
        results = backtest.run(signals)

        # 儲存回測結果
        self.backtest_results[strategy_name] = {
            "strategy_params": strategy_params,
            "start_date": start_date,
            "end_date": end_date,
            "results": results,
        }

        return results

    def _create_strategy(
        self, strategy_name: str, strategy_params: Dict[str, Any]
    ) -> Optional[Strategy]:
        """
        創建策略

        Args:
            strategy_name: 策略名稱
            strategy_params: 策略參數

        Returns:
            Optional[Strategy]: 策略實例
        """
        try:
            # 根據策略名稱創建策略
            if strategy_name == "moving_average_crossover":
                from src.strategy.momentum import MovingAverageCrossStrategy

                return MovingAverageCrossStrategy(**strategy_params)
            elif strategy_name == "rsi":
                from src.strategy.mean_reversion import RSIStrategy

                return RSIStrategy(**strategy_params)
            elif strategy_name == "bollinger_bands":
                from src.strategy.mean_reversion import BollingerBandsStrategy

                return BollingerBandsStrategy(**strategy_params)
            elif strategy_name == "ml_strategy":
                from src.strategy.ml_strategy import MLStrategy

                return MLStrategy(**strategy_params)
            else:
                logger.error(f"未知的策略名稱: {strategy_name}")
                return None
        except Exception as e:
            logger.error(f"創建策略時發生錯誤: {e}")
            return None

    def optimize_strategy_parameters(
        self,
        strategy_name: str,
        param_grid: Dict[str, List[Any]],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        initial_capital: float = 1000000,
        transaction_cost: float = 0.001425,
        slippage: float = 0.001,
        tax: float = 0.003,
        optimization_metric: str = "sharpe_ratio",
    ) -> Dict[str, Any]:
        """
        優化策略參數

        Args:
            strategy_name: 策略名稱
            param_grid: 參數網格
            start_date: 開始日期
            end_date: 結束日期
            initial_capital: 初始資金
            transaction_cost: 交易成本
            slippage: 滑價
            tax: 稅率
            optimization_metric: 優化指標

        Returns:
            Dict[str, Any]: 優化結果
        """
        # 載入資料
        data = load_data(start_date, end_date)
        if "price" not in data:
            logger.error("無法載入價格資料")
            return {}

        price_df = data["price"]

        # 創建參數網格
        grid = ParameterGrid(param_grid)

        # 初始化最佳參數和最佳分數
        best_params = None
        best_score = -float("inf")
        all_results = []

        # 遍歷參數網格
        for params in grid:
            # 創建策略
            strategy = self._create_strategy(strategy_name, params)
            if strategy is None:
                continue

            # 生成訊號
            signals = strategy.generate_signals(price_df)

            # 執行回測
            backtest = Backtest(
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                transaction_cost=transaction_cost,
                slippage=slippage,
                tax=tax,
            )

            # 執行回測
            results = backtest.run(signals)

            # 獲取優化指標
            score = results.get(optimization_metric, -float("inf"))

            # 記錄結果
            all_results.append(
                {
                    "params": params,
                    "score": score,
                    "results": results,
                }
            )

            # 更新最佳參數和最佳分數
            if score > best_score:
                best_score = score
                best_params = params

        # 儲存優化結果
        self.optimization_results[strategy_name] = {
            "best_params": best_params,
            "best_score": best_score,
            "all_results": all_results,
            "param_grid": param_grid,
            "optimization_metric": optimization_metric,
        }

        return {
            "best_params": best_params,
            "best_score": best_score,
        }

    def compare_strategy_versions(
        self,
        strategy_name: str,
        original_params: Dict[str, Any],
        optimized_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        比較策略版本

        Args:
            strategy_name: 策略名稱
            original_params: 原始參數
            optimized_params: 優化後的參數

        Returns:
            Dict[str, Any]: 比較結果
        """
        # 載入資料
        data = load_data()
        if "price" not in data:
            logger.error("無法載入價格資料")
            return {}

        price_df = data["price"]

        # 創建多策略回測
        multi_backtest = MultiStrategyBacktest()

        # 添加原始策略
        original_strategy = self._create_strategy(strategy_name, original_params)
        if original_strategy is not None:
            original_signals = original_strategy.generate_signals(price_df)
            multi_backtest.add_strategy(f"{strategy_name}_original", original_signals)

        # 添加優化後的策略
        optimized_strategy = self._create_strategy(strategy_name, optimized_params)
        if optimized_strategy is not None:
            optimized_signals = optimized_strategy.generate_signals(price_df)
            multi_backtest.add_strategy(f"{strategy_name}_optimized", optimized_signals)

        # 執行回測
        multi_backtest.run_all()

        # 獲取比較表
        comparison_table = multi_backtest.get_comparison_table()

        # 計算改進百分比
        improvement = {}
        if len(comparison_table) >= 2:
            original_row = comparison_table.iloc[0]
            optimized_row = comparison_table.iloc[1]

            for column in comparison_table.columns:
                if column != "策略" and pd.api.types.is_numeric_dtype(
                    comparison_table[column]
                ):
                    original_value = original_row[column]
                    optimized_value = optimized_row[column]

                    if original_value != 0:
                        improvement[column] = (
                            optimized_value / original_value - 1
                        ) * 100
                    else:
                        improvement[column] = float("inf") if optimized_value > 0 else 0

        return {
            "comparison_table": comparison_table,
            "improvement": improvement,
            "original_params": original_params,
            "optimized_params": optimized_params,
        }

    def generate_optimization_report(self, strategy_name: str) -> str:
        """
        生成優化報告

        Args:
            strategy_name: 策略名稱

        Returns:
            str: 報告檔案路徑
        """
        # 檢查是否有優化結果
        if strategy_name not in self.optimization_results:
            logger.error(f"找不到策略 {strategy_name} 的優化結果")
            return ""

        # 獲取優化結果
        optimization_result = self.optimization_results[strategy_name]

        # 創建報告目錄
        report_dir = os.path.join(self.output_dir, strategy_name)
        ensure_dir(report_dir)

        # 報告檔案路徑
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(report_dir, f"optimization_report_{timestamp}.md")

        # 生成報告內容
        report_content = f"""# 策略優化報告

## 策略資訊
- 策略名稱: {strategy_name}
- 優化時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 優化結果
- 最佳參數: {optimization_result['best_params']}
- 最佳分數 ({optimization_result['optimization_metric']}): {optimization_result['best_score']}

## 參數網格
```
{optimization_result['param_grid']}
```

## 市場變化分析
"""

        # 添加市場變化分析
        if self.market_change_analysis:
            report_content += f"""
- 分析期間: {self.market_change_analysis['start_date']} 至 {self.market_change_analysis['end_date']}
- 參考期間: {self.market_change_analysis['reference_period']} 天

### 市場變化
- 波動率變化: {self.market_change_analysis['market_changes'].get('volatility_change', 'N/A')}
- 趨勢變化: {self.market_change_analysis['market_changes'].get('trend_change', 'N/A')}
- 相關性變化: {self.market_change_analysis['market_changes'].get('correlation_change', 'N/A')}
"""

        # 添加參數比較
        if (
            "best_params" in optimization_result
            and strategy_name in self.backtest_results
        ):
            original_params = self.backtest_results[strategy_name]["strategy_params"]
            optimized_params = optimization_result["best_params"]

            report_content += f"""
## 參數比較

| 參數 | 原始值 | 優化後值 |
|------|--------|----------|
"""

            # 合併所有參數鍵
            all_keys = set(original_params.keys()) | set(optimized_params.keys())

            for key in sorted(all_keys):
                original_value = original_params.get(key, "N/A")
                optimized_value = optimized_params.get(key, "N/A")
                report_content += f"| {key} | {original_value} | {optimized_value} |\n"

        # 添加性能比較
        comparison_result = self.compare_strategy_versions(
            strategy_name,
            (
                self.backtest_results[strategy_name]["strategy_params"]
                if strategy_name in self.backtest_results
                else {}
            ),
            optimization_result["best_params"],
        )

        if comparison_result and "comparison_table" in comparison_result:
            report_content += f"""
## 性能比較

{comparison_result["comparison_table"].to_markdown()}

### 改進百分比

| 指標 | 改進百分比 (%) |
|------|----------------|
"""

            for metric, value in comparison_result["improvement"].items():
                report_content += f"| {metric} | {value:.2f} |\n"

        # 寫入報告檔案
        with open(report_path, "w") as f:
            f.write(report_content)

        return report_path
