# -*- coding: utf-8 -*-
"""
策略優化模組

此模組負責評估和優化交易策略。
主要功能：
- 評估策略性能
- 識別不同市場條件下的弱點
- 優化策略參數
- 測試策略穩健性
- 實施策略更新
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.backtest.backtest import Backtest
from src.backtest.performance_analysis import PerformanceAnalyzer
from src.config import RESULTS_DIR
from src.core.logger import get_logger
from src.models.performance_metrics import calculate_all_metrics
from src.strategy.strategy import Strategy

# 設定日誌
logger = get_logger("strategy_refiner")


class StrategyRefiner:
    """策略優化類"""

    def __init__(
        self,
        performance_analyzer: Optional[PerformanceAnalyzer] = None,
    ):
        """
        初始化策略優化類

        Args:
            performance_analyzer: 性能分析器
        """
        # 初始化性能分析器
        self.performance_analyzer = performance_analyzer or PerformanceAnalyzer()

        # 初始化策略性能歷史
        self.performance_history = self._load_performance_history()

        logger.info("策略優化器初始化完成")

    def _load_performance_history(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        載入策略性能歷史

        Returns:
            Dict[str, List[Dict[str, Any]]]: 策略性能歷史
        """
        history_path = os.path.join(RESULTS_DIR, "strategy_performance_history.json")
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"載入策略性能歷史時發生錯誤: {e}")
                return {}
        else:
            return {}

    def _save_performance_history(self):
        """保存策略性能歷史"""
        history_path = os.path.join(RESULTS_DIR, "strategy_performance_history.json")
        try:
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(self.performance_history, f, indent=2)
            logger.info(f"策略性能歷史已保存至: {history_path}")
        except Exception as e:
            logger.error(f"保存策略性能歷史時發生錯誤: {e}")

    def check_strategy_performance(
        self,
        strategies: Optional[List[str]] = None,
        sharpe_threshold: float = 0.8,
        drawdown_threshold: float = 0.2,
        win_rate_threshold: float = 0.45,
    ) -> List[str]:
        """
        檢查策略性能

        Args:
            strategies: 要檢查的策略列表，如果為 None，則檢查所有策略
            sharpe_threshold: 夏普比率閾值
            drawdown_threshold: 最大回撤閾值
            win_rate_threshold: 勝率閾值

        Returns:
            List[str]: 需要優化的策略列表
        """
        # 如果未指定策略，則獲取所有策略
        if strategies is None:
            strategies = self._get_all_strategies()

        # 需要優化的策略列表
        strategies_to_refine = []

        # 檢查每個策略的性能
        for strategy_name in strategies:
            try:
                # 獲取策略
                strategy = self._load_strategy(strategy_name)
                if strategy is None:
                    logger.warning(f"找不到策略: {strategy_name}")
                    continue

                # 評估策略性能
                metrics = self._evaluate_strategy(strategy)

                # 檢查是否需要優化
                if self._needs_refinement(
                    strategy_name,
                    metrics,
                    sharpe_threshold,
                    drawdown_threshold,
                    win_rate_threshold,
                ):
                    strategies_to_refine.append(strategy_name)
                    logger.info(f"策略 {strategy_name} 需要優化")
                else:
                    logger.info(f"策略 {strategy_name} 性能良好，無需優化")

                # 更新性能歷史
                if strategy_name not in self.performance_history:
                    self.performance_history[strategy_name] = []
                self.performance_history[strategy_name].append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "metrics": metrics,
                    }
                )

                # 保存性能歷史
                self._save_performance_history()
            except Exception as e:
                logger.error(f"檢查策略 {strategy_name} 性能時發生錯誤: {e}")

        return strategies_to_refine

    def _get_all_strategies(self) -> List[str]:
        """
        獲取所有策略

        Returns:
            List[str]: 策略列表
        """
        # 從策略目錄獲取所有策略
        strategy_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "strategy"
        )
        strategy_files = [
            f
            for f in os.listdir(strategy_dir)
            if f.endswith(".py") and f != "__init__.py"
        ]
        strategy_names = [f.replace(".py", "") for f in strategy_files]
        return strategy_names

    def _load_strategy(self, strategy_name: str) -> Optional[Strategy]:
        """
        載入策略

        Args:
            strategy_name: 策略名稱

        Returns:
            Optional[Strategy]: 策略
        """
        try:
            # 動態導入策略模組
            module_path = f"src.strategy.{strategy_name}"
            module = __import__(module_path, fromlist=[""])

            # 獲取策略類
            strategy_class = getattr(module, f"{strategy_name.capitalize()}Strategy")

            # 創建策略實例
            strategy = strategy_class()

            return strategy
        except Exception as e:
            logger.error(f"載入策略 {strategy_name} 時發生錯誤: {e}")
            return None

    def _evaluate_strategy(self, strategy: Strategy) -> Dict[str, float]:
        """
        評估策略性能

        Args:
            strategy: 策略

        Returns:
            Dict[str, float]: 性能指標
        """
        try:
            # 準備回測資料
            price_data = self._prepare_backtest_data(strategy.symbols)
            if price_data is None or price_data.empty:
                logger.error(f"無法準備策略 {strategy.name} 的回測資料")
                return {}

            # 生成訊號
            signals = strategy.generate_signals(price_data)

            # 創建回測器
            backtest = Backtest(
                price_data=price_data,
                signals=signals,
                initial_capital=100000,
                commission=0.001,
            )

            # 執行回測
            backtest_result = backtest.run()

            # 獲取性能指標
            metrics = backtest_result["metrics"]

            # 分析不同市場條件下的表現
            market_condition_metrics = self._analyze_market_conditions(backtest_result)
            metrics.update(market_condition_metrics)

            return metrics
        except Exception as e:
            logger.error(f"評估策略 {strategy.name} 時發生錯誤: {e}")
            return {}

    def _prepare_backtest_data(self, symbols: List[str]) -> Optional[pd.DataFrame]:
        """
        準備回測資料

        Args:
            symbols: 股票代號列表

        Returns:
            Optional[pd.DataFrame]: 回測資料
        """
        try:
            # 獲取最近一年的資料
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

            # 從資料庫載入資料
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            from src.config import DB_URL
            from src.database.schema import MarketDaily

            engine = create_engine(DB_URL)
            Session = sessionmaker(bind=engine)
            session = Session()

            # 查詢資料
            query = session.query(MarketDaily).filter(
                MarketDaily.symbol.in_(symbols),
                MarketDaily.date >= start_date,
                MarketDaily.date <= end_date,
            )

            # 轉換為 DataFrame
            from src.database.parquet_utils import query_to_dataframe

            price_data = query_to_dataframe(query)

            session.close()

            return price_data
        except Exception as e:
            logger.error(f"準備回測資料時發生錯誤: {e}")
            return None

    def _analyze_market_conditions(
        self, backtest_result: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        分析不同市場條件下的表現

        Args:
            backtest_result: 回測結果

        Returns:
            Dict[str, float]: 不同市場條件下的性能指標
        """
        try:
            # 獲取回測資料
            equity_curve = backtest_result.get("equity_curve")
            if equity_curve is None or equity_curve.empty:
                return {}

            # 計算市場趨勢
            price_data = backtest_result.get("price_data")
            if price_data is None or price_data.empty:
                return {}

            # 計算市場趨勢（使用 200 日移動平均線）
            price_data["ma200"] = price_data.groupby("symbol")["close"].transform(
                lambda x: x.rolling(window=200, min_periods=1).mean()
            )
            price_data["trend"] = np.where(
                price_data["close"] > price_data["ma200"], "uptrend", "downtrend"
            )

            # 計算市場波動性（使用 20 日波動率）
            price_data["returns"] = price_data.groupby("symbol")["close"].pct_change()
            price_data["volatility"] = price_data.groupby("symbol")[
                "returns"
            ].transform(lambda x: x.rolling(window=20, min_periods=1).std())
            price_data["volatility_regime"] = np.where(
                price_data["volatility"] > price_data["volatility"].median(),
                "high",
                "low",
            )

            # 合併市場條件和回測結果
            merged_data = pd.merge(
                equity_curve,
                price_data[["date", "symbol", "trend", "volatility_regime"]],
                on=["date", "symbol"],
            )

            # 計算不同市場條件下的性能
            metrics = {}

            # 上升趨勢下的性能
            uptrend_data = merged_data[merged_data["trend"] == "uptrend"]
            if not uptrend_data.empty:
                uptrend_returns = uptrend_data["returns"]
                uptrend_metrics = calculate_all_metrics(uptrend_returns)
                metrics.update({f"uptrend_{k}": v for k, v in uptrend_metrics.items()})

            # 下降趨勢下的性能
            downtrend_data = merged_data[merged_data["trend"] == "downtrend"]
            if not downtrend_data.empty:
                downtrend_returns = downtrend_data["returns"]
                downtrend_metrics = calculate_all_metrics(downtrend_returns)
                metrics.update(
                    {f"downtrend_{k}": v for k, v in downtrend_metrics.items()}
                )

            # 高波動性下的性能
            high_vol_data = merged_data[merged_data["volatility_regime"] == "high"]
            if not high_vol_data.empty:
                high_vol_returns = high_vol_data["returns"]
                high_vol_metrics = calculate_all_metrics(high_vol_returns)
                metrics.update(
                    {f"high_volatility_{k}": v for k, v in high_vol_metrics.items()}
                )

            # 低波動性下的性能
            low_vol_data = merged_data[merged_data["volatility_regime"] == "low"]
            if not low_vol_data.empty:
                low_vol_returns = low_vol_data["returns"]
                low_vol_metrics = calculate_all_metrics(low_vol_returns)
                metrics.update(
                    {f"low_volatility_{k}": v for k, v in low_vol_metrics.items()}
                )

            return metrics
        except Exception as e:
            logger.error(f"分析不同市場條件下的表現時發生錯誤: {e}")
            return {}

    def _needs_refinement(
        self,
        strategy_name: str,
        current_metrics: Dict[str, float],
        sharpe_threshold: float,
        drawdown_threshold: float,
        win_rate_threshold: float,
    ) -> bool:
        """
        判斷策略是否需要優化

        Args:
            strategy_name: 策略名稱
            current_metrics: 當前性能指標
            sharpe_threshold: 夏普比率閾值
            drawdown_threshold: 最大回撤閾值
            win_rate_threshold: 勝率閾值

        Returns:
            bool: 是否需要優化
        """
        # 檢查夏普比率
        if (
            "sharpe_ratio" in current_metrics
            and current_metrics["sharpe_ratio"] < sharpe_threshold
        ):
            logger.info(
                f"策略 {strategy_name} 的夏普比率 {current_metrics['sharpe_ratio']:.4f} 低於閾值 {sharpe_threshold}"
            )
            return True

        # 檢查最大回撤
        if (
            "max_drawdown" in current_metrics
            and current_metrics["max_drawdown"] > drawdown_threshold
        ):
            logger.info(
                f"策略 {strategy_name} 的最大回撤 {current_metrics['max_drawdown']:.4f} 高於閾值 {drawdown_threshold}"
            )
            return True

        # 檢查勝率
        if (
            "win_rate" in current_metrics
            and current_metrics["win_rate"] < win_rate_threshold
        ):
            logger.info(
                f"策略 {strategy_name} 的勝率 {current_metrics['win_rate']:.4f} 低於閾值 {win_rate_threshold}"
            )
            return True

        # 檢查不同市場條件下的表現
        if (
            "downtrend_sharpe_ratio" in current_metrics
            and current_metrics["downtrend_sharpe_ratio"] < 0
        ):
            logger.info(
                f"策略 {strategy_name} 在下降趨勢中表現不佳，夏普比率為 {current_metrics['downtrend_sharpe_ratio']:.4f}"
            )
            return True

        if (
            "high_volatility_sharpe_ratio" in current_metrics
            and current_metrics["high_volatility_sharpe_ratio"] < 0
        ):
            logger.info(
                f"策略 {strategy_name} 在高波動性環境中表現不佳，夏普比率為 {current_metrics['high_volatility_sharpe_ratio']:.4f}"
            )
            return True

        return False

    def refine_strategies(self, strategies: List[str]) -> Dict[str, Any]:
        """
        優化策略

        Args:
            strategies: 要優化的策略列表

        Returns:
            Dict[str, Any]: 優化結果
        """
        results = {}

        for strategy_name in strategies:
            try:
                logger.info(f"開始優化策略: {strategy_name}")

                # 載入策略
                strategy = self._load_strategy(strategy_name)
                if strategy is None:
                    logger.error(f"找不到策略: {strategy_name}")
                    results[strategy_name] = {"status": "failed", "error": "找不到策略"}
                    continue

                # 準備回測資料
                price_data = self._prepare_backtest_data(strategy.symbols)
                if price_data is None or price_data.empty:
                    logger.error(f"無法準備策略 {strategy_name} 的回測資料")
                    results[strategy_name] = {
                        "status": "failed",
                        "error": "無法準備回測資料",
                    }
                    continue

                # 優化策略參數
                optimized_params = self._optimize_parameters(strategy, price_data)
                if not optimized_params:
                    logger.error(f"優化策略 {strategy_name} 參數失敗")
                    results[strategy_name] = {
                        "status": "failed",
                        "error": "優化參數失敗",
                    }
                    continue

                # 更新策略參數
                for param, value in optimized_params.items():
                    setattr(strategy, param, value)

                # 保存策略
                self._save_strategy(strategy)

                # 評估優化後的策略
                metrics = self._evaluate_strategy(strategy)

                results[strategy_name] = {
                    "status": "success",
                    "optimized_params": optimized_params,
                    "metrics": metrics,
                }
                logger.info(
                    f"策略 {strategy_name} 優化成功，新參數: {optimized_params}"
                )
            except Exception as e:
                logger.error(f"優化策略 {strategy_name} 時發生錯誤: {e}")
                results[strategy_name] = {"status": "failed", "error": str(e)}

        return results

    def _optimize_parameters(
        self, strategy: Strategy, price_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        優化策略參數

        Args:
            strategy: 策略
            price_data: 價格資料

        Returns:
            Dict[str, Any]: 優化後的參數
        """
        try:
            # 獲取可優化的參數
            param_grid = strategy.get_param_grid()
            if not param_grid:
                logger.warning(f"策略 {strategy.name} 沒有可優化的參數")
                return {}

            # 使用網格搜索優化參數
            best_params = strategy.optimize_parameters(price_data, param_grid)

            return best_params
        except Exception as e:
            logger.error(f"優化策略 {strategy.name} 參數時發生錯誤: {e}")
            return {}

    def _save_strategy(self, strategy: Strategy) -> bool:
        """
        保存策略

        Args:
            strategy: 策略

        Returns:
            bool: 是否保存成功
        """
        try:
            # 保存策略參數
            strategy_path = os.path.join(
                RESULTS_DIR, f"strategy_{strategy.name}_params.json"
            )
            with open(strategy_path, "w", encoding="utf-8") as f:
                json.dump(strategy.get_params(), f, indent=2)
            logger.info(f"策略 {strategy.name} 參數已保存至: {strategy_path}")
            return True
        except Exception as e:
            logger.error(f"保存策略 {strategy.name} 時發生錯誤: {e}")
            return False


if __name__ == "__main__":
    # 創建策略優化器
    refiner = StrategyRefiner()
    # 檢查策略性能
    strategies_to_refine = refiner.check_strategy_performance()
    # 優化策略
    if strategies_to_refine:
        results = refiner.refine_strategies(strategies_to_refine)
        print(f"優化結果: {results}")
    else:
        print("所有策略性能良好，無需優化")
