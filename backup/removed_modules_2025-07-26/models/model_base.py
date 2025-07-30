# -*- coding: utf-8 -*-
"""
模型基類模組

此模組定義了所有模型的基類，提供統一的介面和共用功能。
所有具體的模型實現都應該繼承此基類。
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

import joblib
import numpy as np
import pandas as pd

from src.config import LOG_LEVEL, MODELS_DIR

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class ModelBase(ABC):
    """
    模型基類

    所有模型都應該繼承此類，並實現其抽象方法。
    """

    def __init__(self, name: str, **kwargs):
        """
        初始化模型

        Args:
            name (str): 模型名稱
            **kwargs: 其他參數
        """
        self.name = name
        self.model = None
        self.model_params = kwargs
        self.feature_names = None
        self.target_name = None
        self.trained = False
        self.version = datetime.now().strftime("%Y%m%d%H%M%S")
        self.metrics: Dict[str, Any] = {}
        self.model_dir = os.path.join(MODELS_DIR, self.name, self.version)

        # 創建模型目錄
        os.makedirs(self.model_dir, exist_ok=True)

    @abstractmethod
    def train(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """
        訓練模型

        Args:
            X (pd.DataFrame): 特徵資料
            y (pd.Series): 目標資料

        Returns:
            Dict[str, Any]: 訓練結果，包含各種指標
        """

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        使用模型進行預測

        Args:
            X (pd.DataFrame): 特徵資料

        Returns:
            np.ndarray: 預測結果
        """

    @abstractmethod
    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """
        評估模型表現

        Args:
            X (pd.DataFrame): 特徵資料
            y (pd.Series): 目標資料

        Returns:
            Dict[str, float]: 評估結果，包含各種指標
        """

    def save(self, path: Optional[str] = None) -> str:
        """
        保存模型

        Args:
            path (Optional[str]): 保存路徑，如果為 None，則使用預設路徑

        Returns:
            str: 模型保存路徑
        """
        if path is None:
            path = os.path.join(self.model_dir, f"{self.name}.joblib")

        # 保存模型
        joblib.dump(self.model, path)

        # 保存模型元數據
        metadata = {
            "name": self.name,
            "version": self.version,
            "feature_names": self.feature_names,
            "target_name": self.target_name,
            "model_params": self.model_params,
            "metrics": self.metrics,
            "trained": self.trained,
            "created_at": datetime.now().isoformat(),
        }

        metadata_path = os.path.join(self.model_dir, "metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4)

        logger.info("模型已保存至 %s", path)
        return path

    def load(self, path: str) -> None:
        """
        載入模型

        Args:
            path (str): 模型路徑
        """
        # 載入模型
        self.model = joblib.load(path)
        self.trained = True

        # 載入模型元數據
        model_dir = os.path.dirname(path)
        metadata_path = os.path.join(model_dir, "metadata.json")

        if os.path.exists(metadata_path):
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            self.name = metadata.get("name", self.name)
            self.version = metadata.get("version", self.version)
            self.feature_names = metadata.get("feature_names", self.feature_names)
            self.target_name = metadata.get("target_name", self.target_name)
            self.model_params = metadata.get("model_params", self.model_params)
            self.metrics = metadata.get("metrics", self.metrics)

        logger.info("模型已從 %s 載入", path)

    def feature_importance(self) -> pd.DataFrame:
        """
        獲取特徵重要性

        Returns:
            pd.DataFrame: 特徵重要性資料框
        """
        if not self.trained or self.model is None:
            logger.warning("模型尚未訓練，無法獲取特徵重要性")
            return pd.DataFrame()

        try:
            # 嘗試獲取特徵重要性
            if hasattr(self.model, "feature_importances_"):
                importances = self.model.feature_importances_
            elif hasattr(self.model, "coef_"):
                importances = np.abs(self.model.coef_).flatten()
            else:
                logger.warning("模型不支援特徵重要性")
                return pd.DataFrame()

            # 創建特徵重要性資料框
            feature_names = self.feature_names or [
                f"feature_{i}" for i in range(len(importances))
            ]
            importance_df = pd.DataFrame(
                {
                    "feature": feature_names[: len(importances)],
                    "importance": importances,
                }
            )

            # 按重要性排序
            importance_df = importance_df.sort_values("importance", ascending=False)

            return importance_df
        except Exception as e:
            logger.error("獲取特徵重要性時發生錯誤: %s", e)
            return pd.DataFrame()

    def get_params(self) -> Dict[str, Any]:
        """
        獲取模型參數

        Returns:
            Dict[str, Any]: 模型參數
        """
        return self.model_params

    def set_params(self, **params) -> None:
        """
        設定模型參數

        Args:
            **params: 模型參數
        """
        self.model_params.update(params)

        # 如果模型已經初始化，則更新模型參數
        if self.model is not None and hasattr(self.model, "set_params"):
            self.model.set_params(**params)
