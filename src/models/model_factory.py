# -*- coding: utf-8 -*-
"""
模型工廠模組

此模組提供創建各種模型的工廠函數，簡化模型的實例化過程。
"""

import logging
from typing import Dict, Optional, Type

# 設定日誌
logger = logging.getLogger(__name__)

# 模型類型映射 - 簡化版本
MODEL_TYPES = {
    # 基本模型類型
    "mock": "MockModel",
    "simple": "SimpleModel",
}


class MockModel:
    """模擬模型類 - 用於測試和開發"""
    
    def __init__(self, name: str = "mock_model", **kwargs):
        self.name = name
        self.params = kwargs
        self.is_trained = False
        
    def train(self, X, y):
        """模擬訓練過程"""
        logger.info(f"模擬訓練模型: {self.name}")
        self.is_trained = True
        return {"status": "success", "model": self.name}
        
    def predict(self, X):
        """模擬預測過程"""
        if not self.is_trained:
            logger.warning("模型尚未訓練")
            return None
        logger.info(f"模擬預測: {self.name}")
        return [0.5] * len(X) if hasattr(X, '__len__') else [0.5]
        
    def evaluate(self, X, y):
        """模擬評估過程"""
        return {"accuracy": 0.85, "precision": 0.80, "recall": 0.90}


class SimpleModel:
    """簡單模型類"""
    
    def __init__(self, name: str = "simple_model", **kwargs):
        self.name = name
        self.params = kwargs
        self.is_trained = False
        
    def train(self, X, y):
        """簡單訓練過程"""
        logger.info(f"訓練簡單模型: {self.name}")
        self.is_trained = True
        return {"status": "success", "model": self.name}
        
    def predict(self, X):
        """簡單預測過程"""
        if not self.is_trained:
            logger.warning("模型尚未訓練")
            return None
        logger.info(f"預測: {self.name}")
        return [0.6] * len(X) if hasattr(X, '__len__') else [0.6]
        
    def evaluate(self, X, y):
        """簡單評估過程"""
        return {"accuracy": 0.75, "precision": 0.70, "recall": 0.80}


def create_model(model_type: str, name: Optional[str] = None, **kwargs):
    """
    創建模型

    Args:
        model_type (str): 模型類型，可選值見 MODEL_TYPES
        name (Optional[str]): 模型名稱，如果為 None，則使用模型類型作為名稱
        **kwargs: 模型參數

    Returns:
        模型實例

    Raises:
        ValueError: 如果指定的模型類型不存在
    """
    if model_type not in MODEL_TYPES:
        logger.error("未知的模型類型: %s", model_type)
        raise ValueError(
            f"未知的模型類型: {model_type}，可用類型: {list(MODEL_TYPES.keys())}"
        )

    # 如果沒有指定名稱，則使用模型類型作為名稱
    if name is None:
        name = model_type

    # 創建模型實例
    if model_type == "mock":
        model = MockModel(name=name, **kwargs)
    elif model_type == "simple":
        model = SimpleModel(name=name, **kwargs)
    else:
        raise ValueError(f"未實現的模型類型: {model_type}")

    logger.info("已創建 %s 模型: %s", model_type, name)
    return model


def register_model(model_type: str, model_class_name: str) -> None:
    """
    註冊自定義模型

    Args:
        model_type (str): 模型類型名稱
        model_class_name (str): 模型類名稱
    """
    MODEL_TYPES[model_type] = model_class_name
    logger.info("已註冊模型類型: %s", model_type)


def get_available_models() -> Dict[str, str]:
    """
    獲取所有可用的模型類型

    Returns:
        Dict[str, str]: 模型類型映射
    """
    return MODEL_TYPES.copy()
