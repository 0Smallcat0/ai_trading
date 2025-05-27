# -*- coding: utf-8 -*-
"""
機器學習策略基類模組

此模組定義了基於機器學習的交易策略基類。

主要功能：
- 機器學習模型整合
- 特徵工程
- 模型訓練和預測
- 策略評估
"""

import logging
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from ..base import Strategy, ParameterError, DataValidationError, ModelNotTrainedError

# 可選導入 sklearn
try:
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.svm import SVC
    from sklearn.metrics import accuracy_score, precision_score, recall_score

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    # 創建模擬類別

    class RandomForestClassifier:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def fit(self, X, y):
            """模擬訓練方法"""
            pass

        def predict(self, X):
            """模擬預測方法"""
            return np.zeros(len(X))

        def predict_proba(self, X):
            """模擬概率預測方法"""
            return np.column_stack([np.ones(len(X)) * 0.5, np.ones(len(X)) * 0.5])

    class GradientBoostingClassifier:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def fit(self, X, y):
            """模擬訓練方法"""
            pass

        def predict(self, X):
            """模擬預測方法"""
            return np.zeros(len(X))

        def predict_proba(self, X):
            """模擬概率預測方法"""
            return np.column_stack([np.ones(len(X)) * 0.5, np.ones(len(X)) * 0.5])

    class SVC:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def fit(self, X, y):
            """模擬訓練方法"""
            pass

        def predict(self, X):
            """模擬預測方法"""
            return np.zeros(len(X))

        def predict_proba(self, X):
            """模擬概率預測方法"""
            return np.column_stack([np.ones(len(X)) * 0.5, np.ones(len(X)) * 0.5])

    def accuracy_score(y_true, y_pred):
        """模擬準確率計算"""
        return 0.5

    def precision_score(y_true, y_pred):
        """模擬精確率計算"""
        return 0.5

    def recall_score(y_true, y_pred):
        """模擬召回率計算"""
        return 0.5


# 設定日誌
logger = logging.getLogger(__name__)


class MachineLearningStrategy(Strategy):
    """
    機器學習策略基類。

    支援多種機器學習模型進行交易訊號預測，包括：
    - Random Forest
    - Gradient Boosting
    - Support Vector Machine

    Attributes:
        model_type (str): 模型類型
        model_params (Dict): 模型參數
        model: 訓練好的模型實例
        threshold (float): 預測閾值

    Example:
        >>> strategy = MachineLearningStrategy(model_type="random_forest")
        >>> strategy.train(features_data, target_data)
        >>> signals = strategy.generate_signals(features_data)
    """

    def __init__(
        self,
        model_type: str = "random_forest",
        threshold: float = 0.5,
        **model_params: Any,
    ) -> None:
        """
        初始化機器學習策略。

        Args:
            model_type: 模型類型，支援 'random_forest', 'gradient_boosting', 'svm'
            threshold: 預測閾值，用於將概率轉換為訊號
            **model_params: 模型參數

        Raises:
            ParameterError: 當參數不符合要求時
        """
        super().__init__(
            name=f"ML_{model_type}",
            model_type=model_type,
            threshold=threshold,
            **model_params,
        )
        self.model_type = model_type
        self.threshold = threshold
        self.model_params = model_params
        self.model = None
        self._is_trained = False

    def _validate_parameters(self) -> None:
        """
        驗證策略參數。

        Raises:
            ParameterError: 當參數不符合要求時
        """
        supported_models = ["random_forest", "gradient_boosting", "svm"]
        if self.model_type not in supported_models:
            raise ParameterError(
                f"不支援的模型類型: {self.model_type}，支援的類型: {supported_models}"
            )

        if not (0 <= self.threshold <= 1):
            raise ParameterError(f"threshold 必須在0-1之間，得到: {self.threshold}")

    def _create_model(self):
        """
        創建機器學習模型。

        Returns:
            機器學習模型實例

        Raises:
            ParameterError: 當模型類型不支援時
        """
        if not SKLEARN_AVAILABLE:
            logger.warning("sklearn 不可用，使用模擬模型")

        if self.model_type == "random_forest":
            default_params = {"n_estimators": 100, "random_state": 42}
            default_params.update(self.model_params)
            return RandomForestClassifier(**default_params)

        elif self.model_type == "gradient_boosting":
            default_params = {"n_estimators": 100, "random_state": 42}
            default_params.update(self.model_params)
            return GradientBoostingClassifier(**default_params)

        elif self.model_type == "svm":
            default_params = {"probability": True, "random_state": 42}
            default_params.update(self.model_params)
            return SVC(**default_params)

        else:
            raise ParameterError(f"不支援的模型類型: {self.model_type}")

    def train(
        self, features: pd.DataFrame, target: pd.Series, validation_split: float = 0.2
    ) -> Dict[str, float]:
        """
        訓練機器學習模型。

        Args:
            features: 特徵資料
            target: 目標變數（0或1）
            validation_split: 驗證集比例

        Returns:
            訓練結果字典，包含準確率、精確率、召回率等指標

        Raises:
            DataValidationError: 當輸入資料格式不正確時
            ModelNotTrainedError: 當模型訓練失敗時
        """
        # 驗證輸入資料
        if features.empty:
            raise DataValidationError("特徵資料不能為空")

        if not isinstance(target, pd.Series):
            raise DataValidationError("目標變數必須是 pandas.Series")

        if len(features) != len(target):
            raise DataValidationError("特徵資料和目標變數長度不一致")

        # 檢查目標變數值
        unique_targets = target.unique()
        if not all(val in [0, 1] for val in unique_targets):
            raise DataValidationError("目標變數必須只包含0和1")

        try:
            # 創建模型
            self.model = self._create_model()

            # 分割訓練和驗證集
            split_idx = int(len(features) * (1 - validation_split))

            X_train = features.iloc[:split_idx]
            y_train = target.iloc[:split_idx]
            X_val = features.iloc[split_idx:]
            y_val = target.iloc[split_idx:]

            # 訓練模型
            logger.info("開始訓練 %s 模型...", self.model_type)
            self.model.fit(X_train, y_train)

            # 驗證模型
            if len(X_val) > 0:
                y_pred = self.model.predict(X_val)

                metrics = {
                    "accuracy": accuracy_score(y_val, y_pred),
                    "precision": precision_score(y_val, y_pred, zero_division=0),
                    "recall": recall_score(y_val, y_pred, zero_division=0),
                }

                logger.info(
                    "模型訓練完成 - 準確率: %.3f, 精確率: %.3f, 召回率: %.3f",
                    metrics["accuracy"],
                    metrics["precision"],
                    metrics["recall"],
                )
            else:
                metrics = {"accuracy": 0.0, "precision": 0.0, "recall": 0.0}
                logger.warning("驗證集為空，無法計算驗證指標")

            self._is_trained = True
            return metrics

        except Exception as e:
            raise ModelNotTrainedError(f"模型訓練失敗: {str(e)}") from e

    def generate_signals(self, features: pd.DataFrame) -> pd.DataFrame:
        """
        生成機器學習策略訊號。

        Args:
            features: 特徵資料

        Returns:
            包含交易訊號的資料框架，包含以下欄位：
            - signal: 主要訊號 (1=買入, 0=觀望)
            - buy_signal: 買入訊號 (1=買入, 0=無動作)
            - sell_signal: 賣出訊號 (1=賣出, 0=無動作)
            - prediction_proba: 預測概率
            - confidence: 預測信心度

        Raises:
            ModelNotTrainedError: 當模型未訓練時
            DataValidationError: 當輸入資料格式不正確時
        """
        if not self._is_trained or self.model is None:
            raise ModelNotTrainedError("模型尚未訓練，請先調用 train() 方法")

        if features.empty:
            raise DataValidationError("特徵資料不能為空")

        try:
            # 預測概率
            if hasattr(self.model, "predict_proba"):
                proba = self.model.predict_proba(features)
                # 取得正類（買入）的概率
                buy_proba = proba[:, 1] if proba.shape[1] > 1 else proba[:, 0]
            else:
                # 如果模型不支援 predict_proba，則使用 predict
                predictions = self.model.predict(features)
                buy_proba = predictions.astype(float)

            # 生成訊號
            signals = pd.DataFrame(index=features.index)
            signals["prediction_proba"] = buy_proba

            # 計算信心度（距離閾值的距離）
            signals["confidence"] = np.abs(buy_proba - self.threshold)

            # 生成買入訊號
            signals["signal"] = (buy_proba > self.threshold).astype(int)

            # 計算訊號變化
            signals["position_change"] = signals["signal"].diff()

            # 買入訊號：從0變為1
            signals["buy_signal"] = (signals["position_change"] > 0).astype(int)

            # 賣出訊號：從1變為0
            signals["sell_signal"] = (signals["position_change"] < 0).astype(int)

            # 填充NaN值
            signals = signals.fillna(0)

            logger.info(
                "生成機器學習策略訊號完成，模型: %s, 閾值: %.3f",
                self.model_type,
                self.threshold,
            )

            return signals

        except Exception as e:
            raise DataValidationError(f"訊號生成失敗: {str(e)}") from e

    def _get_default_param_grid(self) -> Dict[str, List[Any]]:
        """
        獲取預設參數網格。

        Returns:
            預設參數網格
        """
        if self.model_type == "random_forest":
            return {
                "n_estimators": [50, 100, 200],
                "max_depth": [None, 5, 10, 20],
                "min_samples_split": [2, 5, 10],
                "threshold": [0.4, 0.5, 0.6],
            }
        elif self.model_type == "gradient_boosting":
            return {
                "n_estimators": [50, 100, 200],
                "learning_rate": [0.01, 0.1, 0.2],
                "max_depth": [3, 5, 10],
                "threshold": [0.4, 0.5, 0.6],
            }
        elif self.model_type == "svm":
            return {
                "C": [0.1, 1.0, 10.0],
                "kernel": ["rbf", "linear"],
                "threshold": [0.4, 0.5, 0.6],
            }
        else:
            return {"threshold": [0.4, 0.5, 0.6]}

    def get_feature_importance(self) -> Optional[pd.Series]:
        """
        獲取特徵重要性。

        Returns:
            特徵重要性序列，如果模型不支援則返回None
        """
        if not self._is_trained or self.model is None:
            logger.warning("模型尚未訓練，無法獲取特徵重要性")
            return None

        if hasattr(self.model, "feature_importances_"):
            return pd.Series(self.model.feature_importances_, name="importance")
        else:
            logger.warning("模型 %s 不支援特徵重要性", self.model_type)
            return None

    def get_model_info(self) -> Dict[str, Any]:
        """
        獲取模型資訊。

        Returns:
            模型資訊字典
        """
        return {
            "model_type": self.model_type,
            "threshold": self.threshold,
            "is_trained": self._is_trained,
            "model_params": self.model_params,
            "sklearn_available": SKLEARN_AVAILABLE,
        }
