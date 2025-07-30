# -*- coding: utf-8 -*-
"""
超參數調優模組 (向後兼容)

此模組提供超參數調優功能的向後兼容介面。
新的模組化實現位於 hyperparameter_optimization 子模組中。

Classes:
    HyperparameterTuner: 超參數調優器（向後兼容）

Example:
    >>> from src.models.hyperparameter_tuning import HyperparameterTuner
    >>> tuner = HyperparameterTuner(
    ...     model_type="random_forest",
    ...     param_grid={"n_estimators": [100, 200], "max_depth": [5, 10]}
    ... )
    >>> results = tuner.grid_search(X_train, y_train)

Note:
    建議使用新的模組化介面：
    from src.models.hyperparameter_optimization import GridSearchOptimizer
"""

import logging
from typing import Any, Callable, Dict, Optional, Union

import mlflow
import pandas as pd
from sklearn.model_selection import RandomizedSearchCV

from src.config import LOG_LEVEL
from src.models.model_factory import create_model

# 導入新的模組化實現
from .hyperparameter_optimization.grid_search import GridSearchOptimizer
from .hyperparameter_optimization.utils import (
    validate_param_grid,
    log_tuning_params,
    save_results,
)

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))

# 檢查 Optuna 是否可用
try:
    import optuna

    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    logger.warning("Optuna 未安裝，貝葉斯優化功能將無法使用")

# 向後兼容的別名
_validate_param_grid = validate_param_grid
_log_tuning_params = log_tuning_params
_save_results = save_results


class HyperparameterTuner:
    """
    超參數調優器 (向後兼容版本)

    此類提供向後兼容的超參數調優介面。
    建議使用新的模組化實現以獲得更好的功能和性能。

    Attributes:
        model_type: 模型類型名稱
        param_grid: 參數搜索空間
        experiment_name: MLflow 實驗名稱
        tracking_uri: MLflow 追蹤伺服器 URI
        scoring: 評分函數或指標名稱
        cv: 交叉驗證折數
        n_jobs: 並行任務數
        best_params: 最佳參數組合
        best_score: 最佳評分
        results: 完整調優結果
        run_id: MLflow 運行 ID

    Example:
        >>> tuner = HyperparameterTuner(
        ...     model_type="random_forest",
        ...     param_grid={"n_estimators": [100, 200], "max_depth": [5, 10]}
        ... )
        >>> results = tuner.grid_search(X_train, y_train)

    Note:
        此類已被標記為過時，建議使用：
        from src.models.hyperparameter_optimization import GridSearchOptimizer
    """

    def __init__(
        self,
        model_type: str,
        param_grid: Dict[str, Any],
        experiment_name: str = "hyperparameter_tuning",
        tracking_uri: Optional[str] = None,
        scoring: Optional[Union[str, Callable]] = None,
        cv: int = 5,
        n_jobs: int = -1,
    ) -> None:
        """
        初始化超參數調優器

        Args:
            model_type: 模型類型
            param_grid: 參數網格
            experiment_name: MLflow 實驗名稱
            tracking_uri: MLflow 追蹤伺服器 URI
            scoring: 評分函數或指標名稱
            cv: 交叉驗證折數
            n_jobs: 並行任務數

        Raises:
            ValueError: 當參數格式不正確時
        """
        # 驗證輸入參數
        if not isinstance(model_type, str) or not model_type.strip():
            raise ValueError("model_type 必須是非空字串")

        if cv < 2:
            raise ValueError("cv 必須 >= 2")

        validate_param_grid(param_grid)

        self.model_type = model_type
        self.param_grid = param_grid
        self.experiment_name = experiment_name
        self.tracking_uri = tracking_uri
        self.scoring = scoring
        self.cv = cv
        self.n_jobs = n_jobs

        # 初始化 MLflow
        try:
            if tracking_uri:
                mlflow.set_tracking_uri(tracking_uri)
            mlflow.set_experiment(experiment_name)
        except Exception as e:
            logger.error(f"初始化 MLflow 時發生錯誤: {e}")
            raise RuntimeError(f"MLflow 初始化失敗: {e}") from e

        # 調優結果
        self.best_params: Optional[Dict[str, Any]] = None
        self.best_score: Optional[float] = None
        self.results: Optional[pd.DataFrame] = None
        self.run_id: Optional[str] = None

    def grid_search(
        self, X: pd.DataFrame, y: pd.Series, log_to_mlflow: bool = True, **kwargs: Any
    ) -> Dict[str, Any]:
        """
        執行網格搜索超參數調優 (向後兼容方法)

        此方法委託給新的 GridSearchOptimizer 實現。

        Args:
            X: 特徵資料
            y: 目標變數
            log_to_mlflow: 是否記錄到 MLflow
            **kwargs: 額外參數

        Returns:
            調優結果字典

        Example:
            >>> results = tuner.grid_search(X_train, y_train)
        """
        # 使用新的實現
        optimizer = GridSearchOptimizer(
            model_type=self.model_type,
            param_grid=self.param_grid,
            experiment_name=self.experiment_name,
            tracking_uri=self.tracking_uri,
            scoring=self.scoring,
            cv=self.cv,
            n_jobs=self.n_jobs,
        )

        results = optimizer.optimize(X, y, log_to_mlflow=log_to_mlflow, **kwargs)

        # 更新實例變數以保持向後兼容
        self.best_params = results["best_params"]
        self.best_score = results["best_score"]
        self.results = results["results"]
        self.run_id = results["run_id"]

        return results

    def random_search(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_iter: int = 10,
        log_to_mlflow: bool = True,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        執行隨機搜索超參數調優 (向後兼容方法)

        此方法目前使用簡化的實現，建議使用新的模組化介面。

        Args:
            X: 特徵資料
            y: 目標變數
            n_iter: 迭代次數
            log_to_mlflow: 是否記錄到 MLflow
            **kwargs: 額外參數

        Returns:
            調優結果字典

        Example:
            >>> results = tuner.random_search(X_train, y_train, n_iter=50)
        """
        # 簡化實現，使用 sklearn 的 RandomizedSearchCV
        try:
            base_model = create_model(self.model_type)

            random_search = RandomizedSearchCV(
                base_model.model,
                self.param_grid,
                n_iter=n_iter,
                scoring=self.scoring,
                cv=self.cv,
                n_jobs=self.n_jobs,
                verbose=1,
                **kwargs,
            )

            if log_to_mlflow:
                mlflow.start_run()
                self.run_id = mlflow.active_run().info.run_id
                log_tuning_params(
                    "random_search",
                    self.model_type,
                    self.param_grid,
                    self.cv,
                    self.scoring,
                    n_iter=n_iter,
                )

            random_search.fit(X, y)

            self.best_params = random_search.best_params_
            self.best_score = random_search.best_score_
            self.results = pd.DataFrame(random_search.cv_results_)

            if log_to_mlflow:
                save_results(
                    self.results, self.best_params, self.best_score, "random_search"
                )
                mlflow.end_run()

            return {
                "best_params": self.best_params,
                "best_score": self.best_score,
                "results": self.results,
                "run_id": self.run_id,
            }

        except Exception as e:
            logger.error(f"隨機搜索時發生錯誤: {e}")
            if log_to_mlflow and mlflow.active_run():
                mlflow.end_run()
            raise RuntimeError(f"隨機搜索執行失敗: {e}") from e

    def bayesian_optimization(  # pylint: disable=unused-argument
        self,
        X: pd.DataFrame,  # pylint: disable=unused-argument
        y: pd.Series,  # pylint: disable=unused-argument
        n_trials: int = 100,  # pylint: disable=unused-argument
        log_to_mlflow: bool = True,  # pylint: disable=unused-argument
        **kwargs: Any,  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:
        """
        執行貝葉斯優化 (向後兼容方法)

        此方法需要安裝 optuna 套件。

        Args:
            X: 特徵資料
            y: 目標變數
            n_trials: 試驗次數
            log_to_mlflow: 是否記錄到 MLflow
            **kwargs: 額外參數

        Returns:
            調優結果字典

        Raises:
            ImportError: 當 optuna 未安裝時
            NotImplementedError: 功能已重構

        Example:
            >>> results = tuner.bayesian_optimization(X_train, y_train, n_trials=100)
        """
        if not OPTUNA_AVAILABLE:
            raise ImportError("Optuna 未安裝，無法使用貝葉斯優化")

        logger.warning(
            "貝葉斯優化功能已移至新的模組化實現。"
            "建議使用: from src.models.hyperparameter_optimization import BayesianOptimizer"
        )

        # 簡化的實現提示
        raise NotImplementedError(
            "貝葉斯優化功能已重構。請使用新的模組化介面：\n"
            "from src.models.hyperparameter_optimization import BayesianOptimizer\n"
            "optimizer = BayesianOptimizer(...)\n"
            "results = optimizer.optimize(X, y)"
        )
