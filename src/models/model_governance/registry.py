# -*- coding: utf-8 -*-
"""
模型註冊表

此模組實現模型註冊表功能，包括：
- 模型版本管理
- 模型元數據存儲
- 模型載入和保存
- 版本控制和追蹤

Classes:
    ModelRegistry: 模型註冊表主類
"""

import datetime
import json
import logging
import os
from typing import Any, Dict, List, Optional

from src.config import LOG_LEVEL, MODELS_DIR
from src.models.model_base import ModelBase
from src.models.model_factory import create_model
from .utils import validate_model_metadata, create_model_signature

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class ModelRegistry:
    """
    模型註冊表
    
    管理模型版本、元數據和部署狀態的中央註冊表。
    
    Attributes:
        registry_path: 註冊表檔案路徑
        registry: 註冊表資料字典
        
    Example:
        >>> registry = ModelRegistry("./models/registry.json")
        >>> version = registry.register_model(trained_model, description="Production model")
        >>> model = registry.load_model("my_model", version)
        
    Note:
        註冊表使用 JSON 格式存儲，支援版本控制和回滾
        所有操作都會自動保存到檔案系統
    """

    def __init__(self, registry_path: Optional[str] = None):
        """
        初始化模型註冊表

        Args:
            registry_path: 註冊表路徑，預設為 MODELS_DIR/registry.json
            
        Raises:
            IOError: 當無法讀取或創建註冊表檔案時
        """
        self.registry_path = registry_path or os.path.join(MODELS_DIR, "registry.json")
        self.registry = self._load_registry()
        
        # 確保模型目錄存在
        os.makedirs(MODELS_DIR, exist_ok=True)

    def _load_registry(self) -> Dict[str, Any]:
        """
        載入註冊表
        
        Returns:
            註冊表資料字典
            
        Raises:
            IOError: 當檔案讀取失敗時
        """
        if os.path.exists(self.registry_path):
            try:
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    registry_data = json.load(f)
                    logger.info(f"已載入註冊表: {self.registry_path}")
                    return registry_data
            except (IOError, json.JSONDecodeError) as e:
                logger.error(f"載入註冊表時發生錯誤: {e}")
                return self._create_empty_registry()
        else:
            logger.info("註冊表檔案不存在，創建新的註冊表")
            return self._create_empty_registry()

    def _create_empty_registry(self) -> Dict[str, Any]:
        """
        創建空註冊表
        
        Returns:
            空註冊表結構
        """
        return {
            "models": {},
            "deployments": {},
            "metadata": {
                "created_at": datetime.datetime.now().isoformat(),
                "version": "1.0.0"
            },
            "last_updated": datetime.datetime.now().isoformat(),
        }

    def _save_registry(self) -> None:
        """
        保存註冊表到檔案
        
        Raises:
            IOError: 當檔案寫入失敗時
        """
        try:
            # 確保目錄存在
            os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
            
            # 更新最後修改時間
            self.registry["last_updated"] = datetime.datetime.now().isoformat()
            
            # 保存到檔案
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(self.registry, f, indent=4, ensure_ascii=False)
                
            logger.debug(f"註冊表已保存: {self.registry_path}")
            
        except IOError as e:
            logger.error(f"保存註冊表時發生錯誤: {e}")
            raise IOError(f"無法保存註冊表: {e}") from e

    def register_model(
        self,
        model: ModelBase,
        version: Optional[str] = None,
        description: Optional[str] = None,
        metrics: Optional[Dict[str, float]] = None,
        run_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> str:
        """
        註冊模型
        
        Args:
            model: 要註冊的模型實例
            version: 版本號，如果為 None 則自動生成
            description: 模型描述
            metrics: 模型指標
            run_id: MLflow 運行 ID
            tags: 模型標籤
            **kwargs: 其他元數據
            
        Returns:
            模型版本號
            
        Raises:
            ValueError: 當模型未訓練或參數無效時
            IOError: 當模型保存失敗時
            
        Example:
            >>> version = registry.register_model(
            ...     model=trained_model,
            ...     description="Production model v1",
            ...     metrics={"accuracy": 0.95},
            ...     tags={"environment": "production"}
            ... )
        """
        # 驗證模型狀態
        if not model.trained:
            raise ValueError("模型尚未訓練，無法註冊")
            
        # 驗證模型元數據
        validate_model_metadata(model)

        # 生成版本號
        if version is None:
            version = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

        try:
            # 創建模型簽名
            model_signature = create_model_signature(model)
            
            # 構建模型資訊
            model_info = {
                "name": model.name,
                "version": version,
                "description": description or "",
                "model_type": model.__class__.__name__,
                "model_params": model.model_params,
                "feature_names": model.feature_names,
                "target_name": model.target_name,
                "metrics": metrics or model.metrics,
                "signature": model_signature,
                "tags": tags or {},
                "created_at": datetime.datetime.now().isoformat(),
                "run_id": run_id,
                "path": os.path.join(MODELS_DIR, model.name, version),
                "status": "registered",
                **kwargs
            }

            # 更新註冊表
            if model.name not in self.registry["models"]:
                self.registry["models"][model.name] = {}

            self.registry["models"][model.name][version] = model_info

            # 保存模型檔案
            model_dir = os.path.join(MODELS_DIR, model.name, version)
            os.makedirs(model_dir, exist_ok=True)
            
            model_path = os.path.join(model_dir, f"{model.name}.joblib")
            model.save(model_path)

            # 保存註冊表
            self._save_registry()

            logger.info(f"模型已註冊: {model.name} v{version}")
            return version
            
        except Exception as e:
            logger.error(f"註冊模型時發生錯誤: {e}")
            raise RuntimeError(f"模型註冊失敗: {e}") from e

    def get_model_info(
        self, 
        model_name: str, 
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        獲取模型資訊
        
        Args:
            model_name: 模型名稱
            version: 版本號，如果為 None 則獲取最新版本
            
        Returns:
            模型資訊字典
            
        Raises:
            ValueError: 當模型或版本不存在時
            
        Example:
            >>> info = registry.get_model_info("my_model", "v1.0")
            >>> print(f"Model type: {info['model_type']}")
        """
        if model_name not in self.registry["models"]:
            raise ValueError(f"模型不存在: {model_name}")

        model_versions = self.registry["models"][model_name]
        
        if version is None:
            # 獲取最新版本
            if not model_versions:
                raise ValueError(f"模型沒有版本: {model_name}")
            version = max(model_versions.keys())

        if version not in model_versions:
            available_versions = list(model_versions.keys())
            raise ValueError(
                f"版本不存在: {model_name} v{version}. "
                f"可用版本: {available_versions}"
            )

        return model_versions[version]

    def list_models(self) -> List[str]:
        """
        列出所有模型名稱
        
        Returns:
            模型名稱列表
            
        Example:
            >>> models = registry.list_models()
            >>> print(f"Available models: {models}")
        """
        return list(self.registry["models"].keys())

    def list_versions(self, model_name: str) -> List[str]:
        """
        列出模型的所有版本
        
        Args:
            model_name: 模型名稱
            
        Returns:
            版本號列表，按時間排序
            
        Raises:
            ValueError: 當模型不存在時
            
        Example:
            >>> versions = registry.list_versions("my_model")
            >>> print(f"Available versions: {versions}")
        """
        if model_name not in self.registry["models"]:
            raise ValueError(f"模型不存在: {model_name}")

        versions = list(self.registry["models"][model_name].keys())
        return sorted(versions)

    def load_model(
        self, 
        model_name: str, 
        version: Optional[str] = None
    ) -> ModelBase:
        """
        載入模型
        
        Args:
            model_name: 模型名稱
            version: 版本號，如果為 None 則載入最新版本
            
        Returns:
            載入的模型實例
            
        Raises:
            ValueError: 當模型或版本不存在時
            IOError: 當模型檔案載入失敗時
            
        Example:
            >>> model = registry.load_model("my_model", "v1.0")
            >>> predictions = model.predict(X_test)
        """
        # 獲取模型資訊
        model_info = self.get_model_info(model_name, version)

        try:
            # 創建模型實例
            model_type = model_info["model_type"].lower().replace("model", "")
            model = create_model(
                model_type=model_type,
                name=model_info["name"],
                **model_info["model_params"]
            )

            # 載入模型檔案
            model_path = os.path.join(model_info["path"], f"{model_name}.joblib")
            if not os.path.exists(model_path):
                raise IOError(f"模型檔案不存在: {model_path}")
                
            model.load(model_path)

            # 設定模型屬性
            model.feature_names = model_info["feature_names"]
            model.target_name = model_info["target_name"]
            model.metrics = model_info["metrics"]
            model.version = model_info["version"]

            logger.info(f"模型已載入: {model_name} v{model_info['version']}")
            return model
            
        except Exception as e:
            logger.error(f"載入模型時發生錯誤: {e}")
            raise RuntimeError(f"模型載入失敗: {e}") from e
