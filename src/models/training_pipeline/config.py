# -*- coding: utf-8 -*-
"""
訓練配置管理

此模組實現訓練配置管理功能，包括：
- 訓練參數配置
- MLflow 實驗配置
- 模型接受標準配置
- 配置驗證和序列化

Classes:
    TrainingConfig: 訓練配置管理器
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from src.config import LOG_LEVEL

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


@dataclass
class TrainingConfig:
    """
    訓練配置管理器
    
    管理模型訓練過程中的所有配置參數。
    
    Attributes:
        experiment_name: MLflow 實驗名稱
        tracking_uri: MLflow 追蹤伺服器 URI
        metrics_threshold: 模型接受標準閾值
        early_stopping: 是否啟用早停
        early_stopping_patience: 早停耐心值
        save_best_only: 是否只保存最佳模型
        model_checkpoint_dir: 模型檢查點目錄
        log_level: 日誌級別
        random_seed: 隨機種子
        
    Example:
        >>> config = TrainingConfig(
        ...     experiment_name="production_training",
        ...     metrics_threshold={"accuracy": 0.9, "f1": 0.85},
        ...     early_stopping=True,
        ...     early_stopping_patience=10
        ... )
        >>> trainer = ModelTrainer(model, config)
        
    Note:
        所有配置都有合理的預設值
        支援配置驗證和序列化
        可以從字典或檔案載入配置
    """
    
    # MLflow 配置
    experiment_name: str = "default"
    tracking_uri: Optional[str] = None
    
    # 模型接受標準
    metrics_threshold: Dict[str, float] = field(default_factory=lambda: {
        "sharpe_ratio": 1.2,
        "max_drawdown": -0.2,
        "win_rate": 0.55,
        "accuracy": 0.8,
        "f1": 0.7
    })
    
    # 訓練控制
    early_stopping: bool = False
    early_stopping_patience: int = 10
    early_stopping_metric: str = "val_loss"
    early_stopping_mode: str = "min"  # "min" 或 "max"
    
    # 模型保存
    save_best_only: bool = True
    model_checkpoint_dir: Optional[str] = None
    save_frequency: int = 1  # 每幾個 epoch 保存一次
    
    # 日誌和調試
    log_level: str = "INFO"
    verbose: bool = True
    
    # 隨機性控制
    random_seed: Optional[int] = 42
    
    # 資源配置
    use_gpu: bool = False
    gpu_memory_limit: Optional[int] = None
    n_jobs: int = -1  # 並行處理數量
    
    # 驗證配置
    validation_split: float = 0.2
    shuffle_validation: bool = True
    
    def __post_init__(self):
        """初始化後驗證配置"""
        self.validate()

    def validate(self) -> None:
        """
        驗證配置參數
        
        Raises:
            ValueError: 當配置參數無效時
        """
        # 驗證實驗名稱
        if not self.experiment_name or not isinstance(self.experiment_name, str):
            raise ValueError("experiment_name 必須是非空字串")
        
        # 驗證指標閾值
        if not isinstance(self.metrics_threshold, dict):
            raise ValueError("metrics_threshold 必須是字典")
        
        for metric, threshold in self.metrics_threshold.items():
            if not isinstance(metric, str):
                raise ValueError("指標名稱必須是字串")
            if not isinstance(threshold, (int, float)):
                raise ValueError("指標閾值必須是數值")
        
        # 驗證早停參數
        if self.early_stopping:
            if self.early_stopping_patience <= 0:
                raise ValueError("early_stopping_patience 必須大於 0")
            
            if self.early_stopping_mode not in ["min", "max"]:
                raise ValueError("early_stopping_mode 必須是 'min' 或 'max'")
        
        # 驗證驗證集分割比例
        if not 0 < self.validation_split < 1:
            raise ValueError("validation_split 必須在 0 和 1 之間")
        
        # 驗證隨機種子
        if self.random_seed is not None and self.random_seed < 0:
            raise ValueError("random_seed 必須是非負整數")
        
        # 驗證並行處理數量
        if self.n_jobs == 0:
            raise ValueError("n_jobs 不能為 0")
        
        logger.debug("訓練配置驗證通過")

    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典
        
        Returns:
            配置字典
            
        Example:
            >>> config_dict = config.to_dict()
            >>> print(config_dict["experiment_name"])
        """
        return {
            "experiment_name": self.experiment_name,
            "tracking_uri": self.tracking_uri,
            "metrics_threshold": self.metrics_threshold,
            "early_stopping": self.early_stopping,
            "early_stopping_patience": self.early_stopping_patience,
            "early_stopping_metric": self.early_stopping_metric,
            "early_stopping_mode": self.early_stopping_mode,
            "save_best_only": self.save_best_only,
            "model_checkpoint_dir": self.model_checkpoint_dir,
            "save_frequency": self.save_frequency,
            "log_level": self.log_level,
            "verbose": self.verbose,
            "random_seed": self.random_seed,
            "use_gpu": self.use_gpu,
            "gpu_memory_limit": self.gpu_memory_limit,
            "n_jobs": self.n_jobs,
            "validation_split": self.validation_split,
            "shuffle_validation": self.shuffle_validation
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "TrainingConfig":
        """
        從字典創建配置
        
        Args:
            config_dict: 配置字典
            
        Returns:
            TrainingConfig 實例
            
        Example:
            >>> config_dict = {"experiment_name": "test", "early_stopping": True}
            >>> config = TrainingConfig.from_dict(config_dict)
        """
        return cls(**config_dict)

    def update(self, **kwargs: Any) -> None:
        """
        更新配置參數
        
        Args:
            **kwargs: 要更新的參數
            
        Example:
            >>> config.update(early_stopping=True, early_stopping_patience=5)
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                logger.warning(f"未知的配置參數: {key}")
        
        # 重新驗證配置
        self.validate()

    def get_mlflow_config(self) -> Dict[str, Any]:
        """
        獲取 MLflow 相關配置
        
        Returns:
            MLflow 配置字典
            
        Example:
            >>> mlflow_config = config.get_mlflow_config()
            >>> mlflow.set_experiment(mlflow_config["experiment_name"])
        """
        return {
            "experiment_name": self.experiment_name,
            "tracking_uri": self.tracking_uri
        }

    def get_early_stopping_config(self) -> Dict[str, Any]:
        """
        獲取早停相關配置
        
        Returns:
            早停配置字典
            
        Example:
            >>> early_stopping_config = config.get_early_stopping_config()
            >>> if early_stopping_config["enabled"]:
            ...     setup_early_stopping(**early_stopping_config)
        """
        return {
            "enabled": self.early_stopping,
            "patience": self.early_stopping_patience,
            "metric": self.early_stopping_metric,
            "mode": self.early_stopping_mode
        }

    def get_model_checkpoint_config(self) -> Dict[str, Any]:
        """
        獲取模型檢查點相關配置
        
        Returns:
            檢查點配置字典
            
        Example:
            >>> checkpoint_config = config.get_model_checkpoint_config()
            >>> setup_model_checkpoint(**checkpoint_config)
        """
        return {
            "save_best_only": self.save_best_only,
            "checkpoint_dir": self.model_checkpoint_dir,
            "save_frequency": self.save_frequency
        }

    def copy(self) -> "TrainingConfig":
        """
        創建配置副本
        
        Returns:
            配置副本
            
        Example:
            >>> config_copy = config.copy()
            >>> config_copy.update(experiment_name="new_experiment")
        """
        return TrainingConfig.from_dict(self.to_dict())

    def __str__(self) -> str:
        """字串表示"""
        return f"TrainingConfig(experiment_name='{self.experiment_name}', early_stopping={self.early_stopping})"

    def __repr__(self) -> str:
        """詳細字串表示"""
        return f"TrainingConfig({self.to_dict()})"
