# -*- coding: utf-8 -*-
"""模型整合模組

此模組提供 AI 模型與交易訊號生成系統的整合功能，包括：
- 模型載入與管理
- 模型推論與訊號生成
- 模型健康檢查與備援機制
- 模型效能優化

Note:
    此檔案大小 (759 行) 超過 300 行標準，建議重構為以下子模組：
    - model_manager.py (模型管理核心)
    - health_checker.py (健康檢查機制)
    - fallback_strategies.py (備援策略)
    - prediction_engine.py (預測引擎)
"""

import logging
import threading
import time
import warnings
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# 嘗試導入 MLflow
try:
    import mlflow  # pylint: disable=unused-import
    import mlflow.sklearn  # pylint: disable=unused-import
    import mlflow.pytorch  # pylint: disable=unused-import
    import mlflow.tensorflow  # pylint: disable=unused-import
    MLFLOW_AVAILABLE = True
except ImportError:
    warnings.warn("無法匯入 MLflow，部分功能將無法使用")
    MLFLOW_AVAILABLE = False

# 嘗試導入 ONNX
try:
    import onnxruntime as ort  # pylint: disable=unused-import
    import onnx  # pylint: disable=unused-import
    ONNX_AVAILABLE = True
except ImportError:
    warnings.warn("無法匯入 ONNX Runtime，部分優化功能將無法使用")
    ONNX_AVAILABLE = False

from src.config import LOG_LEVEL
from src.models.inference_pipeline import InferencePipeline
from src.models.model_governance import ModelRegistry

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


# 自定義異常類別
class ModelIntegrationError(Exception):
    """模型整合相關錯誤的基類"""


class ModelLoadError(ModelIntegrationError):
    """模型載入錯誤"""


class ModelPredictionError(ModelIntegrationError):
    """模型預測錯誤"""


class ModelHealthCheckError(ModelIntegrationError):
    """模型健康檢查錯誤"""


class ModelManager:
    """模型管理器

    負責模型的載入、管理和推論。
    """

    def __init__(
        self,
        model_registry: Optional[ModelRegistry] = None,
        cache_size: int = 10,
        batch_size: int = 32,
        use_onnx: bool = False,
        fallback_strategy: str = "latest",
        model_check_interval: int = 3600,  # 1 小時
    ):
        """初始化模型管理器

        Args:
            model_registry (Optional[ModelRegistry]): 模型註冊表
            cache_size (int): 模型快取大小
            batch_size (int): 批次推論大小
            use_onnx (bool): 是否使用 ONNX 優化
            fallback_strategy (str): 備援策略，可選 'latest', 'previous', 'rule_based'
            model_check_interval (int): 模型健康檢查間隔（秒）
        """
        self.model_registry = model_registry or ModelRegistry()
        self.cache_size = cache_size
        self.batch_size = batch_size
        self.use_onnx = use_onnx and ONNX_AVAILABLE
        self.fallback_strategy = fallback_strategy
        self.model_check_interval = model_check_interval

        # 模型快取
        self.model_cache = {}
        self.inference_pipelines = {}

        # 模型健康狀態
        self.model_health = {}

        # 控制健康檢查執行緒的標誌
        self._shutdown_flag = threading.Event()

        # 啟動模型健康檢查執行緒
        self.health_check_thread = threading.Thread(
            target=self._health_check_loop, daemon=True
        )
        self.health_check_thread.start()

    def _health_check_loop(self):
        """
        模型健康檢查迴圈
        """
        while not self._shutdown_flag.is_set():
            try:
                # 檢查所有已載入的模型
                for model_name in list(self.model_cache.keys()):
                    if self._shutdown_flag.is_set():
                        break
                    self.check_model_health(model_name)

                # 等待下一次檢查，但允許提前中斷
                if self._shutdown_flag.wait(timeout=self.model_check_interval):
                    break

            except Exception as e:
                logger.error("模型健康檢查發生錯誤: %s", e)
                # 發生錯誤時，等待 1 分鐘後重試，但允許提前中斷
                if self._shutdown_flag.wait(timeout=60):
                    break

        logger.info("模型健康檢查執行緒已停止")

    def shutdown(self) -> None:
        """
        優雅地關閉模型管理器
        """
        logger.info("正在關閉模型管理器...")

        # 設置關閉標誌
        self._shutdown_flag.set()

        # 等待健康檢查執行緒結束
        if self.health_check_thread.is_alive():
            self.health_check_thread.join(timeout=5)

        # 清理資源
        self.model_cache.clear()
        self.inference_pipelines.clear()
        self.model_health.clear()

        logger.info("模型管理器已關閉")

    def check_model_health(self, model_name: str) -> bool:
        """
        檢查模型健康狀態

        Args:
            model_name (str): 模型名稱

        Returns:
            bool: 模型是否健康
        """
        if model_name not in self.model_cache:
            logger.warning("模型 %s 未載入，無法檢查健康狀態", model_name)
            return False

        try:
            # 使用簡單的測試資料進行推論
            test_data = pd.DataFrame(
                {
                    feature: [0.0]
                    for feature in self.model_cache[model_name].feature_names
                }
            )

            # 計時推論
            start_time = time.time()
            _ = self.model_cache[model_name].predict(test_data)
            inference_time = time.time() - start_time

            # 更新健康狀態
            self.model_health[model_name] = {
                "status": "healthy",
                "last_check": datetime.now().isoformat(),
                "inference_time": inference_time,
                "error": None,
            }

            return True
        except Exception as e:
            # 更新健康狀態
            self.model_health[model_name] = {
                "status": "unhealthy",
                "last_check": datetime.now().isoformat(),
                "inference_time": None,
                "error": str(e),
            }

            logger.error("模型 %s 健康檢查失敗: %s", model_name, e)

            # 嘗試使用備援策略
            self._apply_fallback_strategy(model_name)

            return False

    def _apply_fallback_strategy(self, model_name: str) -> None:
        """
        應用備援策略

        Args:
            model_name (str): 模型名稱
        """
        if self.fallback_strategy == "latest":
            # 嘗試載入最新版本
            try:
                logger.info("嘗試載入模型 %s 的最新版本", model_name)
                self.load_model(model_name)
            except Exception as e:
                logger.error("載入模型 %s 的最新版本失敗: %s", model_name, e)

        elif self.fallback_strategy == "previous":
            # 嘗試載入前一個版本
            try:
                # 獲取所有版本
                versions = self.model_registry.list_versions(model_name)

                # 如果有多個版本，嘗試載入前一個版本
                if len(versions) > 1:
                    current_version = self.model_registry.get_model_info(model_name)[
                        "version"
                    ]
                    current_idx = versions.index(current_version)

                    if current_idx > 0:
                        previous_version = versions[current_idx - 1]
                        logger.info(
                            "嘗試載入模型 %s 的前一個版本 %s", model_name, previous_version
                        )
                        self.load_model(model_name, version=previous_version)
                    else:
                        logger.warning("模型 %s 沒有前一個版本可用", model_name)
                else:
                    logger.warning(
                        "模型 %s 只有一個版本，無法使用前一個版本", model_name
                    )
            except Exception as e:
                logger.error("載入模型 %s 的前一個版本失敗: %s", model_name, e)

        elif self.fallback_strategy == "rule_based":
            # 標記模型為不可用，後續將使用規則型策略
            logger.info("模型 %s 將使用規則型策略作為備援", model_name)
            self.model_health[model_name]["fallback"] = "rule_based"

    def load_model(
        self,
        model_name: str,
        version: Optional[str] = None,
        environment: str = "production",  # pylint: disable=unused-argument
    ) -> bool:
        """
        載入模型

        Args:
            model_name (str): 模型名稱
            version (Optional[str]): 版本，如果為 None，則使用最新部署版本
            environment (str): 環境，例如 "production", "staging"

        Returns:
            bool: 是否成功載入
        """
        try:
            # 如果模型已在快取中，直接返回
            cache_key = f"{model_name}_{version or 'latest'}"
            if cache_key in self.model_cache:
                logger.info(f"模型 {model_name} 已在快取中")
                return True

            # 從模型註冊表載入模型
            try:
                model = self.model_registry.load_model(model_name, version)
            except Exception as registry_error:
                raise ModelLoadError(f"從註冊表載入模型 {model_name} 失敗") from registry_error

            # 將模型加入快取
            self.model_cache[cache_key] = model

            # 如果快取超過大小限制，移除最舊的模型
            if len(self.model_cache) > self.cache_size:
                oldest_key = next(iter(self.model_cache))
                del self.model_cache[oldest_key]

            # 初始化健康狀態
            self.model_health[model_name] = {
                "status": "healthy",
                "last_check": datetime.now().isoformat(),
                "inference_time": None,
                "error": None,
            }

            # 創建推論管道
            try:
                self.inference_pipelines[model_name] = InferencePipeline(
                    model=model, monitor=True
                )
            except Exception as pipeline_error:
                logger.warning(f"創建推論管道失敗，將使用直接預測: {pipeline_error}")

            logger.info(
                f"成功載入模型 {model_name} {'版本 ' + version if version else '最新版本'}"
            )

            return True
        except ModelLoadError:
            # 重新拋出自定義異常
            raise
        except Exception as e:
            error_msg = f"載入模型 {model_name} 時發生未預期錯誤"
            logger.error(f"{error_msg}: {e}")

            # 更新健康狀態
            self.model_health[model_name] = {
                "status": "unhealthy",
                "last_check": datetime.now().isoformat(),
                "inference_time": None,
                "error": str(e),
            }

            raise ModelLoadError(error_msg) from e

    def unload_model(self, model_name: str, version: Optional[str] = None) -> bool:
        """
        卸載模型

        Args:
            model_name (str): 模型名稱
            version (Optional[str]): 版本，如果為 None，則卸載所有版本

        Returns:
            bool: 是否成功卸載
        """
        try:
            if version is None:
                # 卸載所有版本
                keys_to_remove = [
                    k for k in self.model_cache.keys() if k.startswith(f"{model_name}_")
                ]
                for key in keys_to_remove:
                    del self.model_cache[key]

                # 移除推論管道
                if model_name in self.inference_pipelines:
                    del self.inference_pipelines[model_name]

                # 移除健康狀態
                if model_name in self.model_health:
                    del self.model_health[model_name]

                logger.info(f"成功卸載模型 {model_name} 的所有版本")
            else:
                # 卸載特定版本
                cache_key = f"{model_name}_{version}"
                if cache_key in self.model_cache:
                    del self.model_cache[cache_key]
                    logger.info(f"成功卸載模型 {model_name} 版本 {version}")
                else:
                    logger.warning(f"模型 {model_name} 版本 {version} 未載入，無法卸載")
                    return False

            return True
        except Exception as e:
            logger.error(f"卸載模型 {model_name} 失敗: {e}")
            return False

    def preprocess_features(self, data: pd.DataFrame, model_name: str) -> pd.DataFrame:
        """
        預處理特徵

        Args:
            data (pd.DataFrame): 原始資料
            model_name (str): 模型名稱

        Returns:
            pd.DataFrame: 預處理後的特徵
        """
        if model_name not in self.model_cache:
            logger.warning(f"模型 {model_name} 未載入，無法預處理特徵")
            return data

        model = self.model_cache[model_name]

        # 檢查是否有特徵名稱
        if not hasattr(model, "feature_names") or not model.feature_names:
            logger.warning(f"模型 {model_name} 沒有特徵名稱，無法預處理特徵")
            return data

        # 篩選特徵
        features = pd.DataFrame()
        for feature in model.feature_names:
            if feature in data.columns:
                features[feature] = data[feature]
            else:
                logger.warning(f"特徵 {feature} 不在資料中")
                features[feature] = 0.0  # 使用預設值

        return features

    def predict(
        self,
        data: pd.DataFrame,
        model_name: str,
        version: Optional[str] = None,
        use_pipeline: bool = True,
    ) -> np.ndarray:
        """
        使用模型進行預測

        Args:
            data (pd.DataFrame): 資料
            model_name (str): 模型名稱
            version (Optional[str]): 版本，如果為 None，則使用最新載入的版本
            use_pipeline (bool): 是否使用推論管道

        Returns:
            np.ndarray: 預測結果
        """
        # 檢查並載入模型
        if not self._ensure_model_loaded(model_name, version):
            return np.array([])

        # 檢查模型健康狀態
        if not self._check_model_health_for_prediction(model_name, data):
            return self._rule_based_fallback(data, model_name)

        try:
            return self._perform_prediction(data, model_name, version, use_pipeline)
        except Exception as e:
            return self._handle_prediction_error(e, model_name, data)

    def _ensure_model_loaded(self, model_name: str, version: Optional[str] = None) -> bool:
        """確保模型已載入"""
        cache_key = f"{model_name}_{version or 'latest'}"
        if cache_key not in self.model_cache:
            try:
                return self.load_model(model_name, version)
            except ModelLoadError as e:
                logger.error(f"模型 {model_name} 未載入且無法載入: {e}")
                return False
        return True

    def _check_model_health_for_prediction(
        self,
        model_name: str,
        data: pd.DataFrame  # pylint: disable=unused-argument
    ) -> bool:
        """檢查模型健康狀態是否適合預測"""
        if (
            model_name in self.model_health
            and self.model_health[model_name]["status"] == "unhealthy"
        ):
            if self.fallback_strategy == "rule_based":
                logger.warning(f"模型 {model_name} 不健康，使用規則型策略")
                return False
            else:
                logger.warning(f"模型 {model_name} 不健康，但將嘗試使用")
        return True

    def _perform_prediction(
        self,
        data: pd.DataFrame,
        model_name: str,
        version: Optional[str] = None,
        use_pipeline: bool = True
    ) -> np.ndarray:
        """執行實際預測"""
        # 預處理特徵
        features = self.preprocess_features(data, model_name)

        # 使用推論管道或直接使用模型
        if use_pipeline and model_name in self.inference_pipelines:
            return self.inference_pipelines[model_name].predict(features)
        else:
            return self._batch_predict(features, model_name, version)

    def _batch_predict(self, features: pd.DataFrame, model_name: str, version: Optional[str] = None) -> np.ndarray:
        """批次預測"""
        cache_key = f"{model_name}_{version or 'latest'}"

        if len(features) > self.batch_size:
            predictions = []
            for i in range(0, len(features), self.batch_size):
                batch = features.iloc[i : i + self.batch_size]
                batch_predictions = self.model_cache[cache_key].predict(batch)
                predictions.append(batch_predictions)
            return np.concatenate(predictions)
        else:
            return self.model_cache[cache_key].predict(features)

    def _handle_prediction_error(self, error: Exception, model_name: str, data: pd.DataFrame) -> np.ndarray:
        """處理預測錯誤"""
        logger.error(f"使用模型 {model_name} 預測時發生錯誤: {error}")

        # 更新健康狀態
        self.model_health[model_name] = {
            "status": "unhealthy",
            "last_check": datetime.now().isoformat(),
            "inference_time": None,
            "error": str(error),
        }

        # 使用備援策略
        if self.fallback_strategy == "rule_based":
            logger.warning("使用規則型策略作為備援")
            return self._rule_based_fallback(data, model_name)

        return np.array([])

    def _rule_based_fallback(self, data: pd.DataFrame, model_name: str) -> np.ndarray:
        """
        使用規則型策略作為備援

        Args:
            data (pd.DataFrame): 資料
            model_name (str): 模型名稱

        Returns:
            np.ndarray: 預測結果
        """
        # 根據模型名稱選擇適當的規則型策略
        if "price_direction" in model_name.lower():
            # 價格方向預測模型，使用移動平均線交叉策略
            return self._ma_crossover_strategy(data)
        elif "volatility" in model_name.lower():
            # 波動率預測模型，使用 ATR 策略
            return self._atr_strategy(data)
        elif "return" in model_name.lower():
            # 收益率預測模型，使用動量策略
            return self._momentum_strategy(data)
        else:
            # 預設使用移動平均線交叉策略
            return self._ma_crossover_strategy(data)

    def _ma_crossover_strategy(self, data: pd.DataFrame) -> np.ndarray:
        """
        移動平均線交叉策略

        Args:
            data (pd.DataFrame): 資料

        Returns:
            np.ndarray: 預測結果
        """
        if "close" not in data.columns:
            logger.warning("資料中缺少 'close' 列，無法使用移動平均線交叉策略")
            return np.zeros(len(data))

        # 計算短期和長期移動平均線
        short_ma = data["close"].rolling(window=5).mean()
        long_ma = data["close"].rolling(window=20).mean()

        # 生成訊號
        signals = np.zeros(len(data))
        signals[short_ma > long_ma] = 1  # 買入訊號
        signals[short_ma < long_ma] = 0  # 賣出訊號

        return signals

    def _atr_strategy(self, data: pd.DataFrame) -> np.ndarray:
        """
        ATR 策略

        Args:
            data (pd.DataFrame): 資料

        Returns:
            np.ndarray: 預測結果
        """
        if not all(col in data.columns for col in ["high", "low", "close"]):
            logger.warning("資料中缺少 'high', 'low', 'close' 列，無法使用 ATR 策略")
            return np.zeros(len(data))

        # 計算 ATR
        high_low = data["high"] - data["low"]
        high_close = np.abs(data["high"] - data["close"].shift())
        low_close = np.abs(data["low"] - data["close"].shift())

        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(window=14).mean()

        # 計算波動率（標準化 ATR）
        volatility = atr / data["close"]

        # 生成預測結果
        predictions = volatility.values

        return predictions

    def _momentum_strategy(self, data: pd.DataFrame) -> np.ndarray:
        """
        動量策略

        Args:
            data (pd.DataFrame): 資料

        Returns:
            np.ndarray: 預測結果
        """
        if "close" not in data.columns:
            logger.warning("資料中缺少 'close' 列，無法使用動量策略")
            return np.zeros(len(data))

        # 計算收益率
        returns = data["close"].pct_change(periods=5)

        # 生成預測結果
        predictions = returns.values

        return predictions

    def get_model_info(
        self, model_name: str, version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        獲取模型資訊

        Args:
            model_name (str): 模型名稱
            version (Optional[str]): 版本，如果為 None，則獲取最新版本

        Returns:
            Dict[str, Any]: 模型資訊
        """
        try:
            model_info = self.model_registry.get_model_info(model_name, version)

            # 添加健康狀態
            if model_name in self.model_health:
                model_info["health"] = self.model_health[model_name]

            return model_info
        except Exception as e:
            logger.error(f"獲取模型 {model_name} 資訊失敗: {e}")
            return {}

    def get_all_models(self) -> List[str]:
        """
        獲取所有模型

        Returns:
            List[str]: 模型名稱列表
        """
        return self.model_registry.list_models()

    def get_loaded_models(self) -> List[str]:
        """
        獲取已載入的模型

        Returns:
            List[str]: 已載入的模型名稱列表
        """
        return list(set([k.split("_")[0] for k in self.model_cache.keys()]))

    def list_models(self) -> List[str]:
        """
        獲取所有可用模型列表

        Returns:
            List[str]: 可用模型名稱列表
        """
        return self.model_registry.list_models()

    def get_model_performance(self, model_name: str) -> Dict[str, float]:
        """
        獲取模型性能指標

        Args:
            model_name (str): 模型名稱

        Returns:
            Dict[str, float]: 性能指標字典，包含準確率、精確率等
        """
        try:
            model_info = self.model_registry.get_model_info(model_name)
            performance_metrics = model_info.get('performance_metrics', {})

            # 確保返回基本性能指標
            default_metrics = {
                'accuracy': 0.5,
                'precision': 0.5,
                'recall': 0.5,
                'f1_score': 0.5
            }

            # 合併實際指標和預設值
            default_metrics.update(performance_metrics)
            return default_metrics

        except Exception as e:
            logger.warning(f"無法獲取模型 {model_name} 的性能指標: {e}")
            return {
                'accuracy': 0.5,
                'precision': 0.5,
                'recall': 0.5,
                'f1_score': 0.5
            }

    def predict_single(self, model_name: str, data: pd.DataFrame) -> float:
        """
        單次預測

        Args:
            model_name (str): 模型名稱
            data (pd.DataFrame): 輸入資料

        Returns:
            float: 預測結果
        """
        try:
            predictions = self.predict(data, model_name)
            if isinstance(predictions, np.ndarray) and len(predictions) > 0:
                return float(predictions[0])
            elif isinstance(predictions, (list, tuple)) and len(predictions) > 0:
                return float(predictions[0])
            else:
                logger.warning(f"模型 {model_name} 預測結果為空")
                return 0.0
        except Exception as e:
            logger.error(f"模型 {model_name} 單次預測失敗: {e}")
            return 0.0

    def get_health_status(self) -> Dict[str, Dict[str, Any]]:
        """
        獲取健康狀態

        Returns:
            Dict[str, Dict[str, Any]]: 健康狀態
        """
        return self.model_health
