# -*- coding: utf-8 -*-
"""
超參數調優模組

此模組提供模型超參數調優功能，包括：
- 網格搜索
- 隨機搜索
- 貝葉斯優化
"""

import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
from sklearn.metrics import make_scorer
import mlflow
import mlflow.sklearn
import mlflow.tensorflow
import mlflow.xgboost
import mlflow.lightgbm
import optuna
from optuna.integration.mlflow import MLflowCallback

from src.config import LOG_LEVEL, MODELS_DIR
from src.models.model_base import ModelBase
from src.models.model_factory import create_model
from src.models.performance_metrics import (
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_calmar_ratio,
    calculate_max_drawdown,
    calculate_win_rate,
    calculate_pnl_ratio
)

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class HyperparameterTuner:
    """
    超參數調優器

    提供多種超參數調優方法。
    """

    def __init__(
        self,
        model_type: str,
        param_grid: Dict[str, Any],
        experiment_name: str = "hyperparameter_tuning",
        tracking_uri: Optional[str] = None,
        scoring: Optional[Union[str, Callable]] = None,
        cv: int = 5,
        n_jobs: int = -1
    ):
        """
        初始化超參數調優器

        Args:
            model_type (str): 模型類型
            param_grid (Dict[str, Any]): 參數網格
            experiment_name (str): MLflow 實驗名稱
            tracking_uri (Optional[str]): MLflow 追蹤伺服器 URI
            scoring (Optional[Union[str, Callable]]): 評分函數
            cv (int): 交叉驗證折數
            n_jobs (int): 並行任務數
        """
        self.model_type = model_type
        self.param_grid = param_grid
        self.experiment_name = experiment_name
        self.tracking_uri = tracking_uri
        self.scoring = scoring
        self.cv = cv
        self.n_jobs = n_jobs
        
        # 初始化 MLflow
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)
        
        # 調優結果
        self.best_params = None
        self.best_score = None
        self.results = None
        self.run_id = None

    def grid_search(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        log_to_mlflow: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        網格搜索

        Args:
            X (pd.DataFrame): 特徵
            y (pd.Series): 目標
            log_to_mlflow (bool): 是否記錄到 MLflow
            **kwargs: 其他參數

        Returns:
            Dict[str, Any]: 調優結果
        """
        # 創建基礎模型
        base_model = create_model(self.model_type)
        
        # 創建網格搜索器
        grid_search = GridSearchCV(
            base_model.model,
            self.param_grid,
            scoring=self.scoring,
            cv=self.cv,
            n_jobs=self.n_jobs,
            verbose=1,
            **kwargs
        )
        
        # 開始 MLflow 追蹤
        if log_to_mlflow:
            mlflow.start_run()
            self.run_id = mlflow.active_run().info.run_id
            
            # 記錄參數
            mlflow.log_param("tuning_method", "grid_search")
            mlflow.log_param("model_type", self.model_type)
            mlflow.log_param("cv", self.cv)
            mlflow.log_param("scoring", str(self.scoring))
            
            # 記錄參數網格
            for param, values in self.param_grid.items():
                mlflow.log_param(f"param_grid_{param}", str(values))
        
        try:
            # 執行網格搜索
            logger.info(f"開始網格搜索: {self.model_type}, 參數網格: {self.param_grid}")
            grid_search.fit(X, y)
            
            # 獲取結果
            self.best_params = grid_search.best_params_
            self.best_score = grid_search.best_score_
            self.results = pd.DataFrame(grid_search.cv_results_)
            
            logger.info(f"網格搜索完成，最佳參數: {self.best_params}, 最佳分數: {self.best_score}")
            
            # 記錄結果到 MLflow
            if log_to_mlflow:
                # 記錄最佳參數
                for param, value in self.best_params.items():
                    mlflow.log_param(f"best_{param}", value)
                
                # 記錄最佳分數
                mlflow.log_metric("best_score", self.best_score)
                
                # 記錄結果表格
                self.results.to_csv("grid_search_results.csv", index=False)
                mlflow.log_artifact("grid_search_results.csv")
                
                # 繪製參數重要性圖
                self._plot_param_importance()
                
                mlflow.end_run()
            
            return {
                "best_params": self.best_params,
                "best_score": self.best_score,
                "results": self.results,
                "run_id": self.run_id
            }
        
        except Exception as e:
            logger.error(f"網格搜索時發生錯誤: {e}")
            if log_to_mlflow:
                mlflow.end_run()
            raise

    def random_search(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_iter: int = 10,
        log_to_mlflow: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        隨機搜索

        Args:
            X (pd.DataFrame): 特徵
            y (pd.Series): 目標
            n_iter (int): 迭代次數
            log_to_mlflow (bool): 是否記錄到 MLflow
            **kwargs: 其他參數

        Returns:
            Dict[str, Any]: 調優結果
        """
        # 創建基礎模型
        base_model = create_model(self.model_type)
        
        # 創建隨機搜索器
        random_search = RandomizedSearchCV(
            base_model.model,
            self.param_grid,
            n_iter=n_iter,
            scoring=self.scoring,
            cv=self.cv,
            n_jobs=self.n_jobs,
            verbose=1,
            **kwargs
        )
        
        # 開始 MLflow 追蹤
        if log_to_mlflow:
            mlflow.start_run()
            self.run_id = mlflow.active_run().info.run_id
            
            # 記錄參數
            mlflow.log_param("tuning_method", "random_search")
            mlflow.log_param("model_type", self.model_type)
            mlflow.log_param("cv", self.cv)
            mlflow.log_param("scoring", str(self.scoring))
            mlflow.log_param("n_iter", n_iter)
            
            # 記錄參數網格
            for param, values in self.param_grid.items():
                mlflow.log_param(f"param_grid_{param}", str(values))
        
        try:
            # 執行隨機搜索
            logger.info(f"開始隨機搜索: {self.model_type}, 參數網格: {self.param_grid}, 迭代次數: {n_iter}")
            random_search.fit(X, y)
            
            # 獲取結果
            self.best_params = random_search.best_params_
            self.best_score = random_search.best_score_
            self.results = pd.DataFrame(random_search.cv_results_)
            
            logger.info(f"隨機搜索完成，最佳參數: {self.best_params}, 最佳分數: {self.best_score}")
            
            # 記錄結果到 MLflow
            if log_to_mlflow:
                # 記錄最佳參數
                for param, value in self.best_params.items():
                    mlflow.log_param(f"best_{param}", value)
                
                # 記錄最佳分數
                mlflow.log_metric("best_score", self.best_score)
                
                # 記錄結果表格
                self.results.to_csv("random_search_results.csv", index=False)
                mlflow.log_artifact("random_search_results.csv")
                
                # 繪製參數重要性圖
                self._plot_param_importance()
                
                mlflow.end_run()
            
            return {
                "best_params": self.best_params,
                "best_score": self.best_score,
                "results": self.results,
                "run_id": self.run_id
            }
        
        except Exception as e:
            logger.error(f"隨機搜索時發生錯誤: {e}")
            if log_to_mlflow:
                mlflow.end_run()
            raise

    def bayesian_optimization(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_trials: int = 100,
        log_to_mlflow: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        貝葉斯優化

        Args:
            X (pd.DataFrame): 特徵
            y (pd.Series): 目標
            n_trials (int): 試驗次數
            log_to_mlflow (bool): 是否記錄到 MLflow
            **kwargs: 其他參數

        Returns:
            Dict[str, Any]: 調優結果
        """
        # 定義目標函數
        def objective(trial):
            # 從參數網格中採樣
            params = {}
            for param, values in self.param_grid.items():
                if isinstance(values, list):
                    if all(isinstance(v, int) for v in values):
                        params[param] = trial.suggest_int(param, min(values), max(values))
                    elif all(isinstance(v, float) for v in values):
                        params[param] = trial.suggest_float(param, min(values), max(values))
                    else:
                        params[param] = trial.suggest_categorical(param, values)
                elif isinstance(values, tuple) and len(values) == 2:
                    if all(isinstance(v, int) for v in values):
                        params[param] = trial.suggest_int(param, values[0], values[1])
                    elif all(isinstance(v, float) for v in values):
                        params[param] = trial.suggest_float(param, values[0], values[1])
            
            # 創建模型
            model = create_model(self.model_type, **params)
            
            # 使用交叉驗證評估模型
            scores = []
            for train_idx, val_idx in KFold(n_splits=self.cv, shuffle=True, random_state=42).split(X):
                X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
                y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
                
                # 訓練模型
                model.train(X_train, y_train)
                
                # 評估模型
                if callable(self.scoring):
                    y_pred = model.predict(X_val)
                    score = self.scoring(y_val, y_pred)
                else:
                    metrics = model.evaluate(X_val, y_val)
                    score = metrics.get("accuracy", 0.0)
                
                scores.append(score)
            
            return np.mean(scores)
        
        # 創建 MLflow 回調
        mlflow_callback = MLflowCallback(
            tracking_uri=self.tracking_uri,
            metric_name="score",
            mlflow_kwargs={"experiment_name": self.experiment_name}
        )
        
        # 開始 MLflow 追蹤
        if log_to_mlflow:
            mlflow.start_run()
            self.run_id = mlflow.active_run().info.run_id
            
            # 記錄參數
            mlflow.log_param("tuning_method", "bayesian_optimization")
            mlflow.log_param("model_type", self.model_type)
            mlflow.log_param("cv", self.cv)
            mlflow.log_param("scoring", str(self.scoring))
            mlflow.log_param("n_trials", n_trials)
            
            # 記錄參數網格
            for param, values in self.param_grid.items():
                mlflow.log_param(f"param_grid_{param}", str(values))
        
        try:
            # 創建 Optuna 研究
            study = optuna.create_study(direction="maximize")
            
            # 執行優化
            logger.info(f"開始貝葉斯優化: {self.model_type}, 參數網格: {self.param_grid}, 試驗次數: {n_trials}")
            study.optimize(objective, n_trials=n_trials, callbacks=[mlflow_callback])
            
            # 獲取結果
            self.best_params = study.best_params
            self.best_score = study.best_value
            self.results = study.trials_dataframe()
            
            logger.info(f"貝葉斯優化完成，最佳參數: {self.best_params}, 最佳分數: {self.best_score}")
            
            # 記錄結果到 MLflow
            if log_to_mlflow:
                # 記錄最佳參數
                for param, value in self.best_params.items():
                    mlflow.log_param(f"best_{param}", value)
                
                # 記錄最佳分數
                mlflow.log_metric("best_score", self.best_score)
                
                # 記錄結果表格
                self.results.to_csv("bayesian_optimization_results.csv", index=False)
                mlflow.log_artifact("bayesian_optimization_results.csv")
                
                # 繪製參數重要性圖
                fig = optuna.visualization.plot_param_importances(study)
                fig.write_image("param_importance.png")
                mlflow.log_artifact("param_importance.png")
                
                # 繪製優化歷史圖
                fig = optuna.visualization.plot_optimization_history(study)
                fig.write_image("optimization_history.png")
                mlflow.log_artifact("optimization_history.png")
                
                mlflow.end_run()
            
            return {
                "best_params": self.best_params,
                "best_score": self.best_score,
                "results": self.results,
                "run_id": self.run_id,
                "study": study
            }
        
        except Exception as e:
            logger.error(f"貝葉斯優化時發生錯誤: {e}")
            if log_to_mlflow:
                mlflow.end_run()
            raise

    def _plot_param_importance(self):
        """
        繪製參數重要性圖
        """
        if self.results is None:
            return
        
        # 計算每個參數的重要性
        param_names = [col for col in self.results.columns if col.startswith("param_")]
        importance_df = pd.DataFrame(columns=["parameter", "importance"])
        
        for param in param_names:
            # 計算參數與分數的相關性
            param_values = self.results[param].astype(str)
            mean_scores = self.results.groupby(param)["mean_test_score"].mean()
            
            # 計算參數的重要性（最大分數 - 最小分數）
            importance = mean_scores.max() - mean_scores.min()
            
            # 添加到資料框
            importance_df = importance_df.append({
                "parameter": param.replace("param_", ""),
                "importance": importance
            }, ignore_index=True)
        
        # 繪製參數重要性圖
        plt.figure(figsize=(10, 6))
        sns.barplot(x="importance", y="parameter", data=importance_df.sort_values("importance", ascending=False))
        plt.title("Parameter Importance")
        plt.tight_layout()
        plt.savefig("param_importance.png")
        plt.close()
        
        # 記錄到 MLflow
        mlflow.log_artifact("param_importance.png")
