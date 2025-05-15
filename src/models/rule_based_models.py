# -*- coding: utf-8 -*-
"""
規則型模型模組

此模組實現了各種規則型模型，用於生成交易訊號。
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    mean_squared_error, mean_absolute_error, r2_score
)

from src.config import LOG_LEVEL
from .model_base import ModelBase

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class RuleBasedModel(ModelBase):
    """
    規則型模型
    """

    def __init__(
        self, 
        name: str = "rule_based", 
        rule_func: Optional[Callable] = None,
        rule_params: Dict[str, Any] = None,
        is_classifier: bool = True,
        **kwargs
    ):
        """
        初始化規則型模型

        Args:
            name (str): 模型名稱
            rule_func (Optional[Callable]): 規則函數，接受特徵資料和參數，返回預測結果
            rule_params (Dict[str, Any]): 規則參數
            is_classifier (bool): 是否為分類模型
            **kwargs: 其他參數
        """
        super().__init__(
            name=name, 
            rule_func=rule_func,
            rule_params=rule_params or {},
            is_classifier=is_classifier,
            **kwargs
        )
        self.rule_func = rule_func
        self.rule_params = rule_params or {}
        self.is_classifier = is_classifier
        self.trained = True  # 規則型模型不需要訓練

    def train(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """
        訓練模型

        規則型模型不需要訓練，但可以用於評估規則的效能。

        Args:
            X (pd.DataFrame): 特徵資料
            y (pd.Series): 目標資料

        Returns:
            Dict[str, Any]: 訓練結果，包含各種指標
        """
        # 保存特徵名稱和目標名稱
        self.feature_names = X.columns.tolist()
        self.target_name = y.name
        
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
        if self.rule_func is None:
            logger.error("未設定規則函數，無法進行預測")
            raise ValueError("未設定規則函數，無法進行預測")
        
        # 使用規則函數進行預測
        predictions = self.rule_func(X, **self.rule_params)
        
        return predictions

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """
        評估模型表現

        Args:
            X (pd.DataFrame): 特徵資料
            y (pd.Series): 目標資料

        Returns:
            Dict[str, float]: 評估結果，包含各種指標
        """
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

    def set_rule(self, rule_func: Callable, rule_params: Dict[str, Any] = None) -> None:
        """
        設定規則函數和參數

        Args:
            rule_func (Callable): 規則函數
            rule_params (Dict[str, Any], optional): 規則參數
        """
        self.rule_func = rule_func
        self.rule_params = rule_params or {}


# 預定義的規則函數

def moving_average_crossover(
    X: pd.DataFrame, 
    short_window: int = 5, 
    long_window: int = 20,
    price_col: str = "close"
) -> np.ndarray:
    """
    移動平均線交叉規則

    當短期移動平均線上穿長期移動平均線時，產生買入訊號 (1)；
    當短期移動平均線下穿長期移動平均線時，產生賣出訊號 (0)。

    Args:
        X (pd.DataFrame): 特徵資料，必須包含價格欄位
        short_window (int): 短期窗口大小
        long_window (int): 長期窗口大小
        price_col (str): 價格欄位名稱

    Returns:
        np.ndarray: 訊號陣列
    """
    if price_col not in X.columns:
        logger.error(f"特徵資料中缺少價格欄位: {price_col}")
        raise ValueError(f"特徵資料中缺少價格欄位: {price_col}")
    
    # 計算移動平均線
    short_ma = X[price_col].rolling(window=short_window).mean()
    long_ma = X[price_col].rolling(window=long_window).mean()
    
    # 生成訊號
    signals = np.zeros(len(X))
    signals[short_ma > long_ma] = 1
    
    return signals


def rsi_strategy(
    X: pd.DataFrame, 
    window: int = 14,
    overbought: float = 70,
    oversold: float = 30,
    price_col: str = "close"
) -> np.ndarray:
    """
    RSI 策略規則

    當 RSI 低於超賣閾值時，產生買入訊號 (1)；
    當 RSI 高於超買閾值時，產生賣出訊號 (0)。

    Args:
        X (pd.DataFrame): 特徵資料，必須包含價格欄位
        window (int): RSI 窗口大小
        overbought (float): 超買閾值
        oversold (float): 超賣閾值
        price_col (str): 價格欄位名稱

    Returns:
        np.ndarray: 訊號陣列
    """
    if price_col not in X.columns:
        logger.error(f"特徵資料中缺少價格欄位: {price_col}")
        raise ValueError(f"特徵資料中缺少價格欄位: {price_col}")
    
    # 計算價格變化
    delta = X[price_col].diff()
    
    # 分離上漲和下跌
    gain = delta.copy()
    loss = delta.copy()
    gain[gain < 0] = 0
    loss[loss > 0] = 0
    loss = -loss
    
    # 計算平均上漲和下跌
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    
    # 計算相對強弱
    rs = avg_gain / avg_loss
    
    # 計算 RSI
    rsi = 100 - (100 / (1 + rs))
    
    # 生成訊號
    signals = np.zeros(len(X))
    signals[rsi < oversold] = 1  # 買入訊號
    signals[rsi > overbought] = 0  # 賣出訊號
    
    return signals


def bollinger_bands_strategy(
    X: pd.DataFrame, 
    window: int = 20,
    num_std: float = 2.0,
    price_col: str = "close"
) -> np.ndarray:
    """
    布林通道策略規則

    當價格觸及下軌時，產生買入訊號 (1)；
    當價格觸及上軌時，產生賣出訊號 (0)。

    Args:
        X (pd.DataFrame): 特徵資料，必須包含價格欄位
        window (int): 移動平均窗口大小
        num_std (float): 標準差倍數
        price_col (str): 價格欄位名稱

    Returns:
        np.ndarray: 訊號陣列
    """
    if price_col not in X.columns:
        logger.error(f"特徵資料中缺少價格欄位: {price_col}")
        raise ValueError(f"特徵資料中缺少價格欄位: {price_col}")
    
    # 計算移動平均線
    ma = X[price_col].rolling(window=window).mean()
    
    # 計算標準差
    std = X[price_col].rolling(window=window).std()
    
    # 計算上下軌
    upper_band = ma + (std * num_std)
    lower_band = ma - (std * num_std)
    
    # 生成訊號
    signals = np.zeros(len(X))
    signals[X[price_col] <= lower_band] = 1  # 買入訊號
    signals[X[price_col] >= upper_band] = 0  # 賣出訊號
    
    return signals
