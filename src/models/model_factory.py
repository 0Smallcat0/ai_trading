# -*- coding: utf-8 -*-
"""
模型工廠模組

此模組提供創建各種模型的工廠函數，簡化模型的實例化過程。
"""

import logging
from typing import Dict, Optional, Type

from src.config import LOG_LEVEL

from .dl_models import GRUModel, LSTMModel, TransformerModel
from .ml_models import LightGBMModel, RandomForestModel, SVMModel, XGBoostModel
from .model_base import ModelBase
from .rule_based_models import RuleBasedModel

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))

# 模型類型映射
MODEL_TYPES = {
    # 機器學習模型
    "random_forest": RandomForestModel,
    "xgboost": XGBoostModel,
    "lightgbm": LightGBMModel,
    "svm": SVMModel,
    # 深度學習模型
    "lstm": LSTMModel,
    "gru": GRUModel,
    "transformer": TransformerModel,
    # 規則型模型
    "rule_based": RuleBasedModel,
}


def create_model(model_type: str, name: Optional[str] = None, **kwargs) -> ModelBase:
    """
    創建模型

    Args:
        model_type (str): 模型類型，可選值見 MODEL_TYPES
        name (Optional[str]): 模型名稱，如果為 None，則使用模型類型作為名稱
        **kwargs: 模型參數

    Returns:
        ModelBase: 創建的模型實例

    Raises:
        ValueError: 如果指定的模型類型不存在
    """
    if model_type not in MODEL_TYPES:
        logger.error(f"未知的模型類型: {model_type}")
        raise ValueError(
            f"未知的模型類型: {model_type}，可用類型: {list(MODEL_TYPES.keys())}"
        )

    # 獲取模型類
    model_class = MODEL_TYPES[model_type]

    # 如果沒有指定名稱，則使用模型類型作為名稱
    if name is None:
        name = model_type

    # 創建模型實例
    model = model_class(name=name, **kwargs)

    logger.info(f"已創建 {model_type} 模型: {name}")
    return model


def register_model(model_type: str, model_class: Type[ModelBase]) -> None:
    """
    註冊自定義模型

    Args:
        model_type (str): 模型類型名稱
        model_class (Type[ModelBase]): 模型類

    Raises:
        TypeError: 如果模型類不是 ModelBase 的子類
    """
    if not issubclass(model_class, ModelBase):
        logger.error(f"模型類 {model_class.__name__} 不是 ModelBase 的子類")
        raise TypeError(f"模型類必須是 ModelBase 的子類")

    MODEL_TYPES[model_type] = model_class
    logger.info(f"已註冊模型類型: {model_type}")


def get_available_models() -> Dict[str, Type[ModelBase]]:
    """
    獲取所有可用的模型類型

    Returns:
        Dict[str, Type[ModelBase]]: 模型類型映射
    """
    return MODEL_TYPES.copy()
