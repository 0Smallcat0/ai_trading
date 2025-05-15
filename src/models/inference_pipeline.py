# -*- coding: utf-8 -*-
"""
推論管道模組

此模組提供模型推論功能，包括：
- 批次推論
- 即時推論
- 推論結果後處理
- 推論結果記錄
"""

import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from datetime import datetime
import mlflow

from src.config import LOG_LEVEL, MODELS_DIR, RESULTS_DIR
from src.models.model_base import ModelBase
from src.models.model_governance import ModelRegistry, ModelMonitor
from src.models.dataset import FeatureProcessor

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class InferencePipeline:
    """
    推論管道

    提供模型推論功能。
    """

    def __init__(
        self,
        model: Optional[ModelBase] = None,
        model_name: Optional[str] = None,
        version: Optional[str] = None,
        environment: str = "production",
        feature_processor: Optional[FeatureProcessor] = None,
        post_processor: Optional[Callable] = None,
        registry: Optional[ModelRegistry] = None,
        monitor: bool = True
    ):
        """
        初始化推論管道

        Args:
            model (Optional[ModelBase]): 模型，如果提供則直接使用
            model_name (Optional[str]): 模型名稱，如果提供則從註冊表載入
            version (Optional[str]): 版本，如果為 None，則使用最新版本
            environment (str): 環境，例如 "production", "staging"
            feature_processor (Optional[FeatureProcessor]): 特徵處理器
            post_processor (Optional[Callable]): 後處理函數
            registry (Optional[ModelRegistry]): 模型註冊表
            monitor (bool): 是否監控模型
        """
        self.registry = registry or ModelRegistry()
        
        # 載入模型
        if model is not None:
            self.model = model
            self.model_name = model.name
            self.version = model.version
        elif model_name is not None:
            # 從註冊表載入模型
            if version is not None:
                self.model = self.registry.load_model(model_name, version)
                self.model_name = model_name
                self.version = version
            else:
                # 從部署載入模型
                deployment = self.registry.get_deployment_info(model_name, environment)
                self.model = self.registry.load_model(model_name, deployment["version"])
                self.model_name = model_name
                self.version = deployment["version"]
        else:
            logger.error("必須提供 model 或 model_name")
            raise ValueError("必須提供 model 或 model_name")
        
        # 特徵處理器
        self.feature_processor = feature_processor
        
        # 後處理函數
        self.post_processor = post_processor
        
        # 監控器
        self.monitor = ModelMonitor(self.model_name, self.version, self.registry) if monitor else None
        
        # 推論結果
        self.results = []

    def preprocess(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        預處理資料

        Args:
            data (pd.DataFrame): 原始資料

        Returns:
            pd.DataFrame: 預處理後的資料
        """
        # 如果有特徵處理器，則使用特徵處理器處理資料
        if self.feature_processor is not None:
            return self.feature_processor.transform(data)
        else:
            return data

    def postprocess(self, predictions: np.ndarray, data: pd.DataFrame) -> Any:
        """
        後處理預測結果

        Args:
            predictions (np.ndarray): 預測結果
            data (pd.DataFrame): 原始資料

        Returns:
            Any: 後處理後的結果
        """
        # 如果有後處理函數，則使用後處理函數處理預測結果
        if self.post_processor is not None:
            return self.post_processor(predictions, data)
        else:
            return predictions

    def predict(
        self,
        data: pd.DataFrame,
        preprocess: bool = True,
        postprocess: bool = True,
        log_prediction: bool = True,
        actual: Optional[Union[pd.Series, np.ndarray]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        進行預測

        Args:
            data (pd.DataFrame): 資料
            preprocess (bool): 是否預處理
            postprocess (bool): 是否後處理
            log_prediction (bool): 是否記錄預測
            actual (Optional[Union[pd.Series, np.ndarray]]): 實際值
            metadata (Optional[Dict[str, Any]]): 元數據

        Returns:
            Any: 預測結果
        """
        # 預處理
        if preprocess:
            processed_data = self.preprocess(data)
        else:
            processed_data = data
        
        # 預測
        predictions = self.model.predict(processed_data)
        
        # 後處理
        if postprocess:
            results = self.postprocess(predictions, data)
        else:
            results = predictions
        
        # 記錄預測
        if log_prediction and self.monitor is not None:
            self.monitor.log_prediction(processed_data, predictions, actual, metadata)
        
        # 添加到結果
        self.results.append({
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "processed_data": processed_data,
            "predictions": predictions,
            "results": results,
            "actual": actual,
            "metadata": metadata or {}
        })
        
        return results

    def batch_predict(
        self,
        data: pd.DataFrame,
        batch_size: int = 1000,
        preprocess: bool = True,
        postprocess: bool = True,
        log_prediction: bool = True,
        actual: Optional[Union[pd.Series, np.ndarray]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        批次預測

        Args:
            data (pd.DataFrame): 資料
            batch_size (int): 批次大小
            preprocess (bool): 是否預處理
            postprocess (bool): 是否後處理
            log_prediction (bool): 是否記錄預測
            actual (Optional[Union[pd.Series, np.ndarray]]): 實際值
            metadata (Optional[Dict[str, Any]]): 元數據

        Returns:
            List[Any]: 預測結果列表
        """
        # 分批處理
        results = []
        
        for i in range(0, len(data), batch_size):
            # 獲取批次資料
            batch_data = data.iloc[i:i+batch_size]
            
            # 獲取批次實際值
            batch_actual = None
            if actual is not None:
                if isinstance(actual, pd.Series):
                    batch_actual = actual.iloc[i:i+batch_size]
                else:
                    batch_actual = actual[i:i+batch_size]
            
            # 預測
            batch_results = self.predict(
                batch_data,
                preprocess=preprocess,
                postprocess=postprocess,
                log_prediction=log_prediction,
                actual=batch_actual,
                metadata=metadata
            )
            
            # 添加到結果
            results.extend(batch_results if isinstance(batch_results, list) else [batch_results])
        
        return results

    def save_results(
        self,
        output_path: Optional[str] = None,
        format: str = "csv"
    ) -> str:
        """
        保存結果

        Args:
            output_path (Optional[str]): 輸出路徑
            format (str): 格式，可選 "csv", "json", "pickle"

        Returns:
            str: 輸出路徑
        """
        if not self.results:
            logger.warning("沒有結果可保存")
            return ""
        
        # 創建結果資料框
        results_df = pd.DataFrame([
            {
                "timestamp": r["timestamp"],
                "prediction": r["predictions"].tolist() if isinstance(r["predictions"], np.ndarray) else r["predictions"],
                "actual": r["actual"].tolist() if isinstance(r["actual"], np.ndarray) and r["actual"] is not None else r["actual"],
                **r["metadata"]
            }
            for r in self.results
        ])
        
        # 設定輸出路徑
        if output_path is None:
            output_dir = os.path.join(RESULTS_DIR, "predictions", self.model_name, self.version)
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            output_path = os.path.join(output_dir, f"predictions_{timestamp}.{format}")
        
        # 保存結果
        if format == "csv":
            results_df.to_csv(output_path, index=False)
        elif format == "json":
            results_df.to_json(output_path, orient="records", indent=4)
        elif format == "pickle":
            results_df.to_pickle(output_path)
        else:
            logger.error(f"未知的格式: {format}")
            raise ValueError(f"未知的格式: {format}")
        
        logger.info(f"結果已保存至: {output_path}")
        
        return output_path

    def calculate_metrics(self) -> Dict[str, float]:
        """
        計算指標

        Returns:
            Dict[str, float]: 指標
        """
        if self.monitor is not None:
            return self.monitor.calculate_metrics()
        else:
            logger.warning("沒有監控器，無法計算指標")
            return {}
