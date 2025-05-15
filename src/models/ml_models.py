# -*- coding: utf-8 -*-
"""
機器學習模型模組

此模組實現了各種機器學習模型，包括：
- RandomForest
- XGBoost
- LightGBM
- SVM
"""

import logging
from typing import Any, Dict

import lightgbm as lgb
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
from sklearn.svm import SVC, SVR

from src.config import LOG_LEVEL

from .model_base import ModelBase

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class RandomForestModel(ModelBase):
    """
    隨機森林模型
    """

    def __init__(
        self, name: str = "random_forest", is_classifier: bool = True, **kwargs
    ):
        """
        初始化隨機森林模型

        Args:
            name (str): 模型名稱
            is_classifier (bool): 是否為分類模型
            **kwargs: 其他參數，將傳遞給 RandomForestClassifier 或 RandomForestRegressor
        """
        super().__init__(name=name, is_classifier=is_classifier, **kwargs)
        self.is_classifier = is_classifier

        # 創建模型
        if is_classifier:
            self.model = RandomForestClassifier(**kwargs)
        else:
            self.model = RandomForestRegressor(**kwargs)

    def train(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """
        訓練模型

        Args:
            X (pd.DataFrame): 特徵資料
            y (pd.Series): 目標資料

        Returns:
            Dict[str, Any]: 訓練結果，包含各種指標
        """
        # 保存特徵名稱和目標名稱
        self.feature_names = X.columns.tolist()
        self.target_name = y.name

        # 訓練模型
        self.model.fit(X, y)
        self.trained = True

        # 評估模型
        metrics = self.evaluate(X, y)
        self.metrics = metrics

        return metrics

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        使用模型進行預測

        Args:
            X (pd.DataFrame): 特徵資料

        Returns:
            np.ndarray: 預測結果
        """
        if not self.trained:
            logger.warning("模型尚未訓練，無法進行預測")
            return np.array([])

        return self.model.predict(X)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        使用模型進行概率預測

        Args:
            X (pd.DataFrame): 特徵資料

        Returns:
            np.ndarray: 預測概率
        """
        if not self.trained or not self.is_classifier:
            logger.warning("模型尚未訓練或不是分類模型，無法進行概率預測")
            return np.array([])

        return self.model.predict_proba(X)

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """
        評估模型表現

        Args:
            X (pd.DataFrame): 特徵資料
            y (pd.Series): 目標資料

        Returns:
            Dict[str, float]: 評估結果，包含各種指標
        """
        if not self.trained:
            logger.warning("模型尚未訓練，無法進行評估")
            return {}

        # 進行預測
        y_pred = self.predict(X)

        # 計算指標
        metrics = {}

        if self.is_classifier:
            # 分類指標
            metrics["accuracy"] = accuracy_score(y, y_pred)
            metrics["precision"] = precision_score(y, y_pred, average="weighted")
            metrics["recall"] = recall_score(y, y_pred, average="weighted")
            metrics["f1"] = f1_score(y, y_pred, average="weighted")
        else:
            # 回歸指標
            metrics["mse"] = mean_squared_error(y, y_pred)
            metrics["rmse"] = np.sqrt(metrics["mse"])
            metrics["mae"] = mean_absolute_error(y, y_pred)
            metrics["r2"] = r2_score(y, y_pred)

        return metrics

    def tune_hyperparameters(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        param_grid: Dict[str, Any],
        cv: int = 5,
        method: str = "grid",
        n_iter: int = 10,
    ) -> Dict[str, Any]:
        """
        調優超參數

        Args:
            X (pd.DataFrame): 特徵資料
            y (pd.Series): 目標資料
            param_grid (Dict[str, Any]): 參數網格
            cv (int): 交叉驗證折數
            method (str): 調優方法，可選 "grid" 或 "random"
            n_iter (int): 隨機搜索的迭代次數

        Returns:
            Dict[str, Any]: 調優結果，包含最佳參數和最佳分數
        """
        # 選擇調優方法
        if method == "grid":
            search = GridSearchCV(self.model, param_grid, cv=cv)
        elif method == "random":
            search = RandomizedSearchCV(self.model, param_grid, n_iter=n_iter, cv=cv)
        else:
            logger.error(f"未知的調優方法: {method}")
            raise ValueError(f"未知的調優方法: {method}，可用方法: grid, random")

        # 執行調優
        search.fit(X, y)

        # 更新模型參數
        self.model.set_params(**search.best_params_)
        self.model_params.update(search.best_params_)

        # 重新訓練模型
        self.train(X, y)

        return {
            "best_params": search.best_params_,
            "best_score": search.best_score_,
            "cv_results": search.cv_results_,
        }


class XGBoostModel(ModelBase):
    """
    XGBoost 模型
    """

    def __init__(self, name: str = "xgboost", is_classifier: bool = True, **kwargs):
        """
        初始化 XGBoost 模型

        Args:
            name (str): 模型名稱
            is_classifier (bool): 是否為分類模型
            **kwargs: 其他參數，將傳遞給 XGBClassifier 或 XGBRegressor
        """
        super().__init__(name=name, is_classifier=is_classifier, **kwargs)
        self.is_classifier = is_classifier

        # 創建模型
        if is_classifier:
            self.model = xgb.XGBClassifier(**kwargs)
        else:
            self.model = xgb.XGBRegressor(**kwargs)

    def train(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """
        訓練模型

        Args:
            X (pd.DataFrame): 特徵資料
            y (pd.Series): 目標資料

        Returns:
            Dict[str, Any]: 訓練結果，包含各種指標
        """
        # 保存特徵名稱和目標名稱
        self.feature_names = X.columns.tolist()
        self.target_name = y.name

        # 訓練模型
        self.model.fit(X, y)
        self.trained = True

        # 評估模型
        metrics = self.evaluate(X, y)
        self.metrics = metrics

        return metrics

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        使用模型進行預測

        Args:
            X (pd.DataFrame): 特徵資料

        Returns:
            np.ndarray: 預測結果
        """
        if not self.trained:
            logger.warning("模型尚未訓練，無法進行預測")
            return np.array([])

        return self.model.predict(X)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        使用模型進行概率預測

        Args:
            X (pd.DataFrame): 特徵資料

        Returns:
            np.ndarray: 預測概率
        """
        if not self.trained or not self.is_classifier:
            logger.warning("模型尚未訓練或不是分類模型，無法進行概率預測")
            return np.array([])

        return self.model.predict_proba(X)

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """
        評估模型表現

        Args:
            X (pd.DataFrame): 特徵資料
            y (pd.Series): 目標資料

        Returns:
            Dict[str, float]: 評估結果，包含各種指標
        """
        if not self.trained:
            logger.warning("模型尚未訓練，無法進行評估")
            return {}

        # 進行預測
        y_pred = self.predict(X)

        # 計算指標
        metrics = {}

        if self.is_classifier:
            # 分類指標
            metrics["accuracy"] = accuracy_score(y, y_pred)
            metrics["precision"] = precision_score(y, y_pred, average="weighted")
            metrics["recall"] = recall_score(y, y_pred, average="weighted")
            metrics["f1"] = f1_score(y, y_pred, average="weighted")
        else:
            # 回歸指標
            metrics["mse"] = mean_squared_error(y, y_pred)
            metrics["rmse"] = np.sqrt(metrics["mse"])
            metrics["mae"] = mean_absolute_error(y, y_pred)
            metrics["r2"] = r2_score(y, y_pred)

        return metrics


class LightGBMModel(ModelBase):
    """
    LightGBM 模型
    """

    def __init__(self, name: str = "lightgbm", is_classifier: bool = True, **kwargs):
        """
        初始化 LightGBM 模型

        Args:
            name (str): 模型名稱
            is_classifier (bool): 是否為分類模型
            **kwargs: 其他參數，將傳遞給 LGBMClassifier 或 LGBMRegressor
        """
        super().__init__(name=name, is_classifier=is_classifier, **kwargs)
        self.is_classifier = is_classifier

        # 創建模型
        if is_classifier:
            self.model = lgb.LGBMClassifier(**kwargs)
        else:
            self.model = lgb.LGBMRegressor(**kwargs)

    def train(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """
        訓練模型

        Args:
            X (pd.DataFrame): 特徵資料
            y (pd.Series): 目標資料

        Returns:
            Dict[str, Any]: 訓練結果，包含各種指標
        """
        # 保存特徵名稱和目標名稱
        self.feature_names = X.columns.tolist()
        self.target_name = y.name

        # 訓練模型
        self.model.fit(X, y)
        self.trained = True

        # 評估模型
        metrics = self.evaluate(X, y)
        self.metrics = metrics

        return metrics

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        使用模型進行預測

        Args:
            X (pd.DataFrame): 特徵資料

        Returns:
            np.ndarray: 預測結果
        """
        if not self.trained:
            logger.warning("模型尚未訓練，無法進行預測")
            return np.array([])

        return self.model.predict(X)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        使用模型進行概率預測

        Args:
            X (pd.DataFrame): 特徵資料

        Returns:
            np.ndarray: 預測概率
        """
        if not self.trained or not self.is_classifier:
            logger.warning("模型尚未訓練或不是分類模型，無法進行概率預測")
            return np.array([])

        return self.model.predict_proba(X)

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """
        評估模型表現

        Args:
            X (pd.DataFrame): 特徵資料
            y (pd.Series): 目標資料

        Returns:
            Dict[str, float]: 評估結果，包含各種指標
        """
        if not self.trained:
            logger.warning("模型尚未訓練，無法進行評估")
            return {}

        # 進行預測
        y_pred = self.predict(X)

        # 計算指標
        metrics = {}

        if self.is_classifier:
            # 分類指標
            metrics["accuracy"] = accuracy_score(y, y_pred)
            metrics["precision"] = precision_score(y, y_pred, average="weighted")
            metrics["recall"] = recall_score(y, y_pred, average="weighted")
            metrics["f1"] = f1_score(y, y_pred, average="weighted")
        else:
            # 回歸指標
            metrics["mse"] = mean_squared_error(y, y_pred)
            metrics["rmse"] = np.sqrt(metrics["mse"])
            metrics["mae"] = mean_absolute_error(y, y_pred)
            metrics["r2"] = r2_score(y, y_pred)

        return metrics


class SVMModel(ModelBase):
    """
    SVM 模型
    """

    def __init__(self, name: str = "svm", is_classifier: bool = True, **kwargs):
        """
        初始化 SVM 模型

        Args:
            name (str): 模型名稱
            is_classifier (bool): 是否為分類模型
            **kwargs: 其他參數，將傳遞給 SVC 或 SVR
        """
        super().__init__(name=name, is_classifier=is_classifier, **kwargs)
        self.is_classifier = is_classifier

        # 創建模型
        if is_classifier:
            self.model = SVC(**kwargs)
        else:
            self.model = SVR(**kwargs)

    def train(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """
        訓練模型

        Args:
            X (pd.DataFrame): 特徵資料
            y (pd.Series): 目標資料

        Returns:
            Dict[str, Any]: 訓練結果，包含各種指標
        """
        # 保存特徵名稱和目標名稱
        self.feature_names = X.columns.tolist()
        self.target_name = y.name

        # 訓練模型
        self.model.fit(X, y)
        self.trained = True

        # 評估模型
        metrics = self.evaluate(X, y)
        self.metrics = metrics

        return metrics

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        使用模型進行預測

        Args:
            X (pd.DataFrame): 特徵資料

        Returns:
            np.ndarray: 預測結果
        """
        if not self.trained:
            logger.warning("模型尚未訓練，無法進行預測")
            return np.array([])

        return self.model.predict(X)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        使用模型進行概率預測

        Args:
            X (pd.DataFrame): 特徵資料

        Returns:
            np.ndarray: 預測概率
        """
        if not self.trained or not self.is_classifier:
            logger.warning("模型尚未訓練或不是分類模型，無法進行概率預測")
            return np.array([])

        if hasattr(self.model, "predict_proba"):
            return self.model.predict_proba(X)
        else:
            logger.warning("SVM 模型沒有 predict_proba 方法，請設置 probability=True")
            return np.array([])

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """
        評估模型表現

        Args:
            X (pd.DataFrame): 特徵資料
            y (pd.Series): 目標資料

        Returns:
            Dict[str, float]: 評估結果，包含各種指標
        """
        if not self.trained:
            logger.warning("模型尚未訓練，無法進行評估")
            return {}

        # 進行預測
        y_pred = self.predict(X)

        # 計算指標
        metrics = {}

        if self.is_classifier:
            # 分類指標
            metrics["accuracy"] = accuracy_score(y, y_pred)
            metrics["precision"] = precision_score(y, y_pred, average="weighted")
            metrics["recall"] = recall_score(y, y_pred, average="weighted")
            metrics["f1"] = f1_score(y, y_pred, average="weighted")
        else:
            # 回歸指標
            metrics["mse"] = mean_squared_error(y, y_pred)
            metrics["rmse"] = np.sqrt(metrics["mse"])
            metrics["mae"] = mean_absolute_error(y, y_pred)
            metrics["r2"] = r2_score(y, y_pred)

        return metrics
