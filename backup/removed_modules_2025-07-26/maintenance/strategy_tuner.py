# -*- coding: utf-8 -*-
"""
策略調整模組

此模組負責根據性能結果調整策略參數和邏輯，以提高策略性能。
主要功能：
- 根據性能結果調整策略參數
- 優化策略邏輯
- 記錄和比較調整前後的結果
- 生成策略調整報告
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

from src.config import LOG_LEVEL, RESULTS_DIR
from src.maintenance.strategy_rebacktester import StrategyRebacktester
from src.models.hyperparameter_tuning import HyperparameterTuner
from src.models.model_factory import create_model
from src.utils.utils import ensure_dir

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class StrategyTuner:
    """策略調整器"""

    def __init__(self, output_dir: Optional[str] = None):
        """
        初始化策略調整器

        Args:
            output_dir: 輸出目錄，如果為 None，則使用 RESULTS_DIR/strategy_tuning
        """
        self.output_dir = output_dir or os.path.join(RESULTS_DIR, "strategy_tuning")
        ensure_dir(self.output_dir)

        # 策略重新回測器
        self.rebacktester = StrategyRebacktester(
            os.path.join(self.output_dir, "rebacktest")
        )

        # 調整結果
        self.tuning_results = {}

        # 版本歷史
        self.version_history = {}

    def tune_strategy_parameters(
        self,
        strategy_name: str,
        current_params: Dict[str, Any],
        param_grid: Dict[str, List[Any]],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        optimization_metric: str = "sharpe_ratio",
    ) -> Dict[str, Any]:
        """
        調整策略參數

        Args:
            strategy_name: 策略名稱
            current_params: 當前參數
            param_grid: 參數網格
            start_date: 開始日期
            end_date: 結束日期
            optimization_metric: 優化指標

        Returns:
            Dict[str, Any]: 調整結果
        """
        # 分析市場變化
        self.rebacktester.analyze_market_changes(start_date, end_date)

        # 使用當前參數回測策略
        current_results = self.rebacktester.rebacktest_strategy(
            strategy_name, current_params, start_date, end_date
        )

        # 優化策略參數
        optimization_results = self.rebacktester.optimize_strategy_parameters(
            strategy_name,
            param_grid,
            start_date,
            end_date,
            optimization_metric=optimization_metric,
        )

        # 比較策略版本
        comparison_results = self.rebacktester.compare_strategy_versions(
            strategy_name, current_params, optimization_results["best_params"]
        )

        # 生成優化報告
        report_path = self.rebacktester.generate_optimization_report(strategy_name)

        # 儲存調整結果
        self.tuning_results[strategy_name] = {
            "current_params": current_params,
            "optimized_params": optimization_results["best_params"],
            "current_results": current_results,
            "comparison_results": comparison_results,
            "report_path": report_path,
            "timestamp": datetime.now().isoformat(),
        }

        # 更新版本歷史
        if strategy_name not in self.version_history:
            self.version_history[strategy_name] = []

        self.version_history[strategy_name].append(
            {
                "version": len(self.version_history[strategy_name]) + 1,
                "timestamp": datetime.now().isoformat(),
                "params": optimization_results["best_params"],
                "performance": {
                    optimization_metric: optimization_results["best_score"],
                },
                "market_changes": self.rebacktester.market_change_analysis.get(
                    "market_changes", {}
                ),
                "rationale": f"參數優化，目標指標: {optimization_metric}",
            }
        )

        return {
            "current_params": current_params,
            "optimized_params": optimization_results["best_params"],
            "improvement": comparison_results.get("improvement", {}),
            "report_path": report_path,
        }

    def tune_ml_strategy(
        self,
        strategy_name: str,
        model_type: str,
        current_params: Dict[str, Any],
        param_grid: Dict[str, List[Any]],
        features_df: pd.DataFrame,
        target_df: pd.DataFrame,
        test_size: float = 0.3,
        scoring: str = "f1",
    ) -> Dict[str, Any]:
        """
        調整機器學習策略

        Args:
            strategy_name: 策略名稱
            model_type: 模型類型
            current_params: 當前參數
            param_grid: 參數網格
            features_df: 特徵資料
            target_df: 目標資料
            test_size: 測試集比例
            scoring: 評分指標

        Returns:
            Dict[str, Any]: 調整結果
        """
        # 分割資料
        X_train, X_test, y_train, y_test = train_test_split(
            features_df, target_df, test_size=test_size, shuffle=False
        )

        # 創建超參數調優器
        tuner = HyperparameterTuner(
            model_type=model_type,
            param_grid=param_grid,
            experiment_name=f"{strategy_name}_tuning",
            scoring=scoring,
        )

        # 執行網格搜索
        grid_result = tuner.grid_search(X_train, y_train)

        # 創建當前模型
        current_model = create_model(model_type, **current_params)
        current_model.train(X_train, y_train)
        current_predictions = current_model.predict(X_test)

        # 創建優化後的模型
        optimized_model = create_model(model_type, **grid_result["best_params"])
        optimized_model.train(X_train, y_train)
        optimized_predictions = optimized_model.predict(X_test)

        # 評估模型
        current_metrics = self._evaluate_ml_model(current_predictions, y_test)
        optimized_metrics = self._evaluate_ml_model(optimized_predictions, y_test)

        # 計算改進
        improvement = {}
        for metric in current_metrics:
            if current_metrics[metric] != 0:
                improvement[metric] = (
                    optimized_metrics[metric] / current_metrics[metric] - 1
                ) * 100
            else:
                improvement[metric] = (
                    float("inf") if optimized_metrics[metric] > 0 else 0
                )

        # 生成報告
        report_path = self._generate_ml_tuning_report(
            strategy_name,
            model_type,
            current_params,
            grid_result["best_params"],
            current_metrics,
            optimized_metrics,
            improvement,
        )

        # 儲存調整結果
        self.tuning_results[strategy_name] = {
            "current_params": current_params,
            "optimized_params": grid_result["best_params"],
            "current_metrics": current_metrics,
            "optimized_metrics": optimized_metrics,
            "improvement": improvement,
            "report_path": report_path,
            "timestamp": datetime.now().isoformat(),
        }

        # 更新版本歷史
        if strategy_name not in self.version_history:
            self.version_history[strategy_name] = []

        self.version_history[strategy_name].append(
            {
                "version": len(self.version_history[strategy_name]) + 1,
                "timestamp": datetime.now().isoformat(),
                "params": grid_result["best_params"],
                "performance": optimized_metrics,
                "rationale": f"機器學習模型優化，目標指標: {scoring}",
            }
        )

        return {
            "current_params": current_params,
            "optimized_params": grid_result["best_params"],
            "improvement": improvement,
            "report_path": report_path,
        }

    def _evaluate_ml_model(
        self, predictions: np.ndarray, targets: np.ndarray
    ) -> Dict[str, float]:
        """
        評估機器學習模型

        Args:
            predictions: 預測值
            targets: 目標值

        Returns:
            Dict[str, float]: 評估指標
        """
        return {
            "accuracy": accuracy_score(targets, predictions),
            "precision": precision_score(targets, predictions, average="weighted"),
            "recall": recall_score(targets, predictions, average="weighted"),
            "f1": f1_score(targets, predictions, average="weighted"),
        }

    def _generate_ml_tuning_report(
        self,
        strategy_name: str,
        model_type: str,
        current_params: Dict[str, Any],
        optimized_params: Dict[str, Any],
        current_metrics: Dict[str, float],
        optimized_metrics: Dict[str, float],
        improvement: Dict[str, float],
    ) -> str:
        """
        生成機器學習調整報告

        Args:
            strategy_name: 策略名稱
            model_type: 模型類型
            current_params: 當前參數
            optimized_params: 優化後的參數
            current_metrics: 當前指標
            optimized_metrics: 優化後的指標
            improvement: 改進百分比

        Returns:
            str: 報告檔案路徑
        """
        # 創建報告目錄
        report_dir = os.path.join(self.output_dir, strategy_name)
        ensure_dir(report_dir)

        # 報告檔案路徑
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(report_dir, f"ml_tuning_report_{timestamp}.md")

        # 生成報告內容
        report_content = f"""# 機器學習策略調整報告

## 策略資訊
- 策略名稱: {strategy_name}
- 模型類型: {model_type}
- 調整時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 參數比較

| 參數 | 原始值 | 優化後值 |
|------|--------|----------|
"""

        # 合併所有參數鍵
        all_keys = set(current_params.keys()) | set(optimized_params.keys())

        for key in sorted(all_keys):
            original_value = current_params.get(key, "N/A")
            optimized_value = optimized_params.get(key, "N/A")
            report_content += f"| {key} | {original_value} | {optimized_value} |\n"

        # 添加性能比較
        report_content += f"""
## 性能比較

| 指標 | 原始值 | 優化後值 | 改進百分比 (%) |
|------|--------|----------|----------------|
"""

        for metric in current_metrics:
            report_content += f"| {metric} | {current_metrics[metric]:.4f} | {optimized_metrics[metric]:.4f} | {improvement[metric]:.2f} |\n"

        # 寫入報告檔案
        with open(report_path, "w") as f:
            f.write(report_content)

        return report_path

    def adjust_strategy_logic(
        self,
        strategy_name: str,
        current_logic: Dict[str, Any],
        adjustments: Dict[str, Any],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        調整策略邏輯

        Args:
            strategy_name: 策略名稱
            current_logic: 當前邏輯
            adjustments: 調整項目
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            Dict[str, Any]: 調整結果
        """
        # 合併當前邏輯和調整項目
        adjusted_logic = {**current_logic, **adjustments}

        # 使用當前邏輯回測策略
        current_results = self.rebacktester.rebacktest_strategy(
            strategy_name, current_logic, start_date, end_date
        )

        # 使用調整後的邏輯回測策略
        adjusted_results = self.rebacktester.rebacktest_strategy(
            strategy_name, adjusted_logic, start_date, end_date
        )

        # 比較策略版本
        comparison_results = self.rebacktester.compare_strategy_versions(
            strategy_name, current_logic, adjusted_logic
        )

        # 生成報告
        report_path = self._generate_logic_adjustment_report(
            strategy_name, current_logic, adjusted_logic, comparison_results
        )

        # 儲存調整結果
        self.tuning_results[f"{strategy_name}_logic"] = {
            "current_logic": current_logic,
            "adjusted_logic": adjusted_logic,
            "current_results": current_results,
            "adjusted_results": adjusted_results,
            "comparison_results": comparison_results,
            "report_path": report_path,
            "timestamp": datetime.now().isoformat(),
        }

        # 更新版本歷史
        if strategy_name not in self.version_history:
            self.version_history[strategy_name] = []

        self.version_history[strategy_name].append(
            {
                "version": len(self.version_history[strategy_name]) + 1,
                "timestamp": datetime.now().isoformat(),
                "logic": adjusted_logic,
                "performance": (
                    comparison_results.get("comparison_table", {}).iloc[1].to_dict()
                    if "comparison_table" in comparison_results
                    and len(comparison_results["comparison_table"]) > 1
                    else {}
                ),
                "rationale": f"邏輯調整: {', '.join(adjustments.keys())}",
            }
        )

        return {
            "current_logic": current_logic,
            "adjusted_logic": adjusted_logic,
            "improvement": comparison_results.get("improvement", {}),
            "report_path": report_path,
        }

    def _generate_logic_adjustment_report(
        self,
        strategy_name: str,
        current_logic: Dict[str, Any],
        adjusted_logic: Dict[str, Any],
        comparison_results: Dict[str, Any],
    ) -> str:
        """
        生成邏輯調整報告

        Args:
            strategy_name: 策略名稱
            current_logic: 當前邏輯
            adjusted_logic: 調整後的邏輯
            comparison_results: 比較結果

        Returns:
            str: 報告檔案路徑
        """
        # 創建報告目錄
        report_dir = os.path.join(self.output_dir, strategy_name)
        ensure_dir(report_dir)

        # 報告檔案路徑
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(
            report_dir, f"logic_adjustment_report_{timestamp}.md"
        )

        # 生成報告內容
        report_content = f"""# 策略邏輯調整報告

## 策略資訊
- 策略名稱: {strategy_name}
- 調整時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 邏輯比較

| 參數 | 原始值 | 調整後值 |
|------|--------|----------|
"""

        # 合併所有邏輯參數鍵
        all_keys = set(current_logic.keys()) | set(adjusted_logic.keys())

        for key in sorted(all_keys):
            original_value = current_logic.get(key, "N/A")
            adjusted_value = adjusted_logic.get(key, "N/A")

            # 檢查是否為調整項目
            is_adjusted = key in adjusted_logic and (
                key not in current_logic or current_logic[key] != adjusted_logic[key]
            )

            if is_adjusted:
                report_content += (
                    f"| **{key}** | {original_value} | {adjusted_value} |\n"
                )
            else:
                report_content += f"| {key} | {original_value} | {adjusted_value} |\n"

        # 添加性能比較
        if "comparison_table" in comparison_results:
            report_content += f"""
## 性能比較

{comparison_results["comparison_table"].to_markdown()}

### 改進百分比

| 指標 | 改進百分比 (%) |
|------|----------------|
"""

            for metric, value in comparison_results["improvement"].items():
                report_content += f"| {metric} | {value:.2f} |\n"

        # 寫入報告檔案
        with open(report_path, "w") as f:
            f.write(report_content)

        return report_path

    def get_version_history(self, strategy_name: str) -> List[Dict[str, Any]]:
        """
        獲取版本歷史

        Args:
            strategy_name: 策略名稱

        Returns:
            List[Dict[str, Any]]: 版本歷史
        """
        return self.version_history.get(strategy_name, [])

    def generate_version_history_report(self, strategy_name: str) -> str:
        """
        生成版本歷史報告

        Args:
            strategy_name: 策略名稱

        Returns:
            str: 報告檔案路徑
        """
        # 檢查是否有版本歷史
        if (
            strategy_name not in self.version_history
            or not self.version_history[strategy_name]
        ):
            logger.error(f"找不到策略 {strategy_name} 的版本歷史")
            return ""

        # 創建報告目錄
        report_dir = os.path.join(self.output_dir, strategy_name)
        ensure_dir(report_dir)

        # 報告檔案路徑
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(report_dir, f"version_history_report_{timestamp}.md")

        # 生成報告內容
        report_content = f"""# 策略版本歷史報告

## 策略資訊
- 策略名稱: {strategy_name}
- 報告時間: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- 版本數量: {len(self.version_history[strategy_name])}

## 版本歷史

"""

        # 添加版本歷史
        for version in self.version_history[strategy_name]:
            report_content += f"""### 版本 {version['version']}
- 時間: {version['timestamp']}
- 理由: {version['rationale']}

#### 參數
```
{version.get('params', version.get('logic', {}))}
```

#### 性能
"""

            for metric, value in version.get("performance", {}).items():
                report_content += f"- {metric}: {value}\n"

            report_content += "\n"

        # 寫入報告檔案
        with open(report_path, "w") as f:
            f.write(report_content)

        return report_path
