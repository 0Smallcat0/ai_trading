# -*- coding: utf-8 -*-
"""
深度學習模型模組

此模組實現了各種深度學習模型，包括：
- LSTM
- GRU
- Transformer
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.layers import GRU, LSTM, Dense, Dropout
from tensorflow.keras.models import Sequential
from tensorflow.keras.optimizers import Adam

from src.config import LOG_LEVEL, MODELS_DIR

from .model_base import ModelBase

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class LSTMModel(ModelBase):
    """
    LSTM 模型
    """

    def __init__(
        self,
        name: str = "lstm",
        is_classifier: bool = False,
        input_shape: Tuple[int, int] = None,
        units: List[int] = [64, 32],
        dropout: float = 0.2,
        learning_rate: float = 0.001,
        **kwargs,
    ):
        """
        初始化 LSTM 模型

        Args:
            name (str): 模型名稱
            is_classifier (bool): 是否為分類模型
            input_shape (Tuple[int, int]): 輸入形狀 (時間步長, 特徵數)
            units (List[int]): LSTM 層的單元數列表
            dropout (float): Dropout 比例
            learning_rate (float): 學習率
            **kwargs: 其他參數
        """
        super().__init__(
            name=name,
            is_classifier=is_classifier,
            input_shape=input_shape,
            units=units,
            dropout=dropout,
            learning_rate=learning_rate,
            **kwargs,
        )
        self.is_classifier = is_classifier
        self.input_shape = input_shape
        self.units = units
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.scaler = StandardScaler()

        # 如果提供了輸入形狀，則創建模型
        if input_shape is not None:
            self._build_model()

    def _build_model(self):
        """
        構建 LSTM 模型
        """
        model = Sequential()

        # 添加 LSTM 層
        for i, unit in enumerate(self.units):
            return_sequences = i < len(self.units) - 1
            if i == 0:
                model.add(
                    LSTM(
                        unit,
                        return_sequences=return_sequences,
                        input_shape=self.input_shape,
                    )
                )
            else:
                model.add(LSTM(unit, return_sequences=return_sequences))

            # 添加 Dropout 層
            model.add(Dropout(self.dropout))

        # 添加輸出層
        if self.is_classifier:
            model.add(Dense(1, activation="sigmoid"))
            loss = "binary_crossentropy"
            metrics = ["accuracy"]
        else:
            model.add(Dense(1))
            loss = "mse"
            metrics = ["mae"]

        # 編譯模型
        model.compile(
            optimizer=Adam(learning_rate=self.learning_rate), loss=loss, metrics=metrics
        )

        self.model = model

    def _prepare_data(self, X: pd.DataFrame, y: Optional[pd.Series] = None) -> Tuple:
        """
        準備資料

        Args:
            X (pd.DataFrame): 特徵資料
            y (Optional[pd.Series]): 目標資料

        Returns:
            Tuple: 準備好的資料
        """
        # 標準化特徵
        X_scaled = (
            self.scaler.fit_transform(X) if y is not None else self.scaler.transform(X)
        )

        # 如果沒有設定輸入形狀，則根據資料設定
        if self.input_shape is None:
            # 假設每個樣本是一個時間步長
            self.input_shape = (1, X.shape[1])
            self._build_model()

        # 重塑資料以符合 LSTM 輸入要求
        X_reshaped = X_scaled.reshape(-1, self.input_shape[0], self.input_shape[1])

        if y is not None:
            return X_reshaped, y.values
        else:
            return X_reshaped

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

        # 準備資料
        X_train, y_train = self._prepare_data(X, y)

        # 設定回調函數
        callbacks = [
            EarlyStopping(patience=10, restore_best_weights=True),
            ModelCheckpoint(
                filepath=f"{MODELS_DIR}/{self.name}/best_model.h5", save_best_only=True
            ),
        ]

        # 訓練模型
        history = self.model.fit(
            X_train,
            y_train,
            epochs=100,
            batch_size=32,
            validation_split=0.2,
            callbacks=callbacks,
            verbose=1,
        )

        self.trained = True

        # 評估模型
        metrics = self.evaluate(X, y)
        self.metrics = metrics

        # 添加訓練歷史
        metrics["history"] = {
            "loss": history.history["loss"],
            "val_loss": history.history["val_loss"],
        }

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

        # 準備資料
        X_test = self._prepare_data(X)

        # 進行預測
        predictions = self.model.predict(X_test)

        # 如果是分類問題，則將概率轉換為類別
        if self.is_classifier:
            predictions = (predictions > 0.5).astype(int)

        return predictions.flatten()

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


class GRUModel(ModelBase):
    """
    GRU 模型
    """

    def __init__(
        self,
        name: str = "gru",
        is_classifier: bool = False,
        input_shape: Tuple[int, int] = None,
        units: List[int] = [64, 32],
        dropout: float = 0.2,
        learning_rate: float = 0.001,
        **kwargs,
    ):
        """
        初始化 GRU 模型

        Args:
            name (str): 模型名稱
            is_classifier (bool): 是否為分類模型
            input_shape (Tuple[int, int]): 輸入形狀 (時間步長, 特徵數)
            units (List[int]): GRU 層的單元數列表
            dropout (float): Dropout 比例
            learning_rate (float): 學習率
            **kwargs: 其他參數
        """
        super().__init__(
            name=name,
            is_classifier=is_classifier,
            input_shape=input_shape,
            units=units,
            dropout=dropout,
            learning_rate=learning_rate,
            **kwargs,
        )
        self.is_classifier = is_classifier
        self.input_shape = input_shape
        self.units = units
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.scaler = StandardScaler()

        # 如果提供了輸入形狀，則創建模型
        if input_shape is not None:
            self._build_model()

    def _build_model(self):
        """
        構建 GRU 模型
        """
        model = Sequential()

        # 添加 GRU 層
        for i, unit in enumerate(self.units):
            return_sequences = i < len(self.units) - 1
            if i == 0:
                model.add(
                    GRU(
                        unit,
                        return_sequences=return_sequences,
                        input_shape=self.input_shape,
                    )
                )
            else:
                model.add(GRU(unit, return_sequences=return_sequences))

            # 添加 Dropout 層
            model.add(Dropout(self.dropout))

        # 添加輸出層
        if self.is_classifier:
            model.add(Dense(1, activation="sigmoid"))
            loss = "binary_crossentropy"
            metrics = ["accuracy"]
        else:
            model.add(Dense(1))
            loss = "mse"
            metrics = ["mae"]

        # 編譯模型
        model.compile(
            optimizer=Adam(learning_rate=self.learning_rate), loss=loss, metrics=metrics
        )

        self.model = model
