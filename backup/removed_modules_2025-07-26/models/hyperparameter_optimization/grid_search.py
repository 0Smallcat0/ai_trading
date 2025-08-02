# -*- coding: utf-8 -*-
"""
網格搜索優化器

此模組實現網格搜索超參數優化功能，提供：
- 窮舉式參數搜索
- MLflow 實驗追蹤
- 結果視覺化

Classes:
    GridSearchOptimizer: 網格搜索優化器
"""

import logging
from typing import Any, Dict

import mlflow
import pandas as pd
from sklearn.model_selection import GridSearchCV

from src.config import LOG_LEVEL
from src.models.model_factory import create_model
from .base import HyperparameterTuner
from .utils import log_tuning_params, save_results, plot_param_importance

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class GridSearchOptimizer(HyperparameterTuner):
    """
    網格搜索優化器

    使用 sklearn 的 GridSearchCV 進行窮舉式參數搜索，
    找出在給定參數網格中表現最佳的參數組合。

    Example:
        >>> optimizer = GridSearchOptimizer(
        ...     model_type="random_forest",
        ...     param_grid={"n_estimators": [100, 200], "max_depth": [5, 10]}
        ... )
        >>> results = optimizer.optimize(X_train, y_train)
    """

    def optimize(
        self, X: pd.DataFrame, y: pd.Series, log_to_mlflow: bool = True, **kwargs: Any
    ) -> Dict[str, Any]:
        """
        執行網格搜索超參數調優

        使用 sklearn 的 GridSearchCV 進行窮舉式參數搜索，
        找出在給定參數網格中表現最佳的參數組合。

        Args:
            X: 特徵資料，形狀為 (n_samples, n_features)
            y: 目標變數，形狀為 (n_samples,)
            log_to_mlflow: 是否將結果記錄到 MLflow 實驗追蹤
            **kwargs: 傳遞給 GridSearchCV 的額外參數

        Returns:
            包含調優結果的字典，包含以下鍵值：
            - best_params: 最佳參數組合
            - best_score: 最佳交叉驗證分數
            - results: 完整的調優結果 DataFrame
            - run_id: MLflow 運行 ID（如果啟用記錄）

        Raises:
            ValueError: 當輸入資料格式不正確時
            RuntimeError: 當模型創建或訓練失敗時

        Example:
            >>> results = optimizer.optimize(X_train, y_train)
            >>> print(f"Best params: {results['best_params']}")
            >>> print(f"Best score: {results['best_score']:.4f}")
        """
        # 驗證輸入資料
        if X.empty or y.empty:
            raise ValueError("輸入資料不能為空")

        if len(X) != len(y):
            raise ValueError("特徵和目標變數的樣本數必須相同")

        try:
            # 創建基礎模型
            base_model = create_model(self.model_type)
            logger.info(f"創建基礎模型: {self.model_type}")

            # 創建網格搜索器
            grid_search = GridSearchCV(
                base_model.model,
                self.param_grid,
                scoring=self.scoring,
                cv=self.cv,
                n_jobs=self.n_jobs,
                verbose=1,
                **kwargs,
            )

            # 開始 MLflow 追蹤
            if log_to_mlflow:
                mlflow.start_run()
                self.run_id = mlflow.active_run().info.run_id
                log_tuning_params(
                    "grid_search",
                    self.model_type,
                    self.param_grid,
                    self.cv,
                    self.scoring,
                )

            # 執行網格搜索
            logger.info(f"開始網格搜索: {self.model_type}, 參數網格: {self.param_grid}")
            grid_search.fit(X, y)

            # 獲取結果
            self.best_params = grid_search.best_params_
            self.best_score = grid_search.best_score_
            self.results = pd.DataFrame(grid_search.cv_results_)

            logger.info(
                f"網格搜索完成，最佳參數: {self.best_params}, 最佳分數: {self.best_score:.4f}"
            )

            # 記錄結果到 MLflow
            if log_to_mlflow:
                save_results(
                    self.results, self.best_params, self.best_score, "grid_search"
                )
                plot_param_importance(self.results)
                mlflow.end_run()

            return {
                "best_params": self.best_params,
                "best_score": self.best_score,
                "results": self.results,
                "run_id": self.run_id,
            }

        except Exception as e:
            logger.error(f"網格搜索時發生錯誤: {e}")
            if log_to_mlflow and mlflow.active_run():
                mlflow.end_run()
            raise RuntimeError(f"網格搜索執行失敗: {e}") from e

    def get_param_combinations_count(self) -> int:
        """
        計算參數組合總數

        Returns:
            參數組合的總數

        Example:
            >>> count = optimizer.get_param_combinations_count()
            >>> print(f"Total combinations: {count}")
        """
        count = 1
        for values in self.param_grid.values():
            count *= len(values)
        return count

    def estimate_runtime(self, base_time_per_fit: float = 1.0) -> float:
        """
        估算運行時間

        Args:
            base_time_per_fit: 每次模型訓練的基礎時間（秒）

        Returns:
            估算的總運行時間（秒）

        Example:
            >>> estimated_time = optimizer.estimate_runtime(base_time_per_fit=2.0)
            >>> print(f"Estimated runtime: {estimated_time:.1f} seconds")
        """
        total_fits = self.get_param_combinations_count() * self.cv
        return total_fits * base_time_per_fit
