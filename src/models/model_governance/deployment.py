# -*- coding: utf-8 -*-
"""
部署管理器

此模組實現模型部署管理功能，包括：
- 模型部署和回滾
- 環境管理
- A/B 測試支援
- 部署狀態追蹤

Classes:
    DeploymentManager: 部署管理器主類
"""

import datetime
import logging
from typing import Any, Dict, List, Optional

from src.config import LOG_LEVEL
from .registry import ModelRegistry

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class DeploymentManager:
    """
    部署管理器
    
    管理模型在不同環境中的部署狀態和版本控制。
    
    Attributes:
        registry: 模型註冊表
        environments: 支援的環境列表
        
    Example:
        >>> deployment_manager = DeploymentManager(registry)
        >>> deployment = deployment_manager.deploy_model(
        ...     "my_model", "v1.0", "production"
        ... )
        >>> deployment_manager.rollback_deployment("my_model", "production")
        
    Note:
        支援多環境部署（development, staging, production）
        提供 A/B 測試和金絲雀部署功能
        自動記錄部署歷史和回滾點
    """

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        environments: Optional[List[str]] = None
    ):
        """
        初始化部署管理器

        Args:
            registry: 模型註冊表實例
            environments: 支援的環境列表
        """
        self.registry = registry or ModelRegistry()
        self.environments = environments or ["development", "staging", "production"]
        
        # 初始化部署狀態
        if "deployments" not in self.registry.registry:
            self.registry.registry["deployments"] = {}
            
        logger.info("部署管理器已初始化")

    def deploy_model(
        self,
        model_name: str,
        version: str,
        environment: str,
        description: Optional[str] = None,
        deployment_config: Optional[Dict[str, Any]] = None,
        replace_existing: bool = True
    ) -> Dict[str, Any]:
        """
        部署模型到指定環境
        
        Args:
            model_name: 模型名稱
            version: 模型版本
            environment: 目標環境
            description: 部署描述
            deployment_config: 部署配置
            replace_existing: 是否替換現有部署
            
        Returns:
            部署資訊字典
            
        Raises:
            ValueError: 當模型或環境無效時
            RuntimeError: 當部署失敗時
            
        Example:
            >>> deployment = deployment_manager.deploy_model(
            ...     "my_model", "v1.0", "production",
            ...     description="Production deployment",
            ...     deployment_config={"replicas": 3}
            ... )
        """
        try:
            # 驗證環境
            if environment not in self.environments:
                raise ValueError(f"不支援的環境: {environment}. 支援的環境: {self.environments}")

            # 驗證模型存在
            model_info = self.registry.get_model_info(model_name, version)

            # 檢查現有部署
            deployment_key = f"{model_name}:{environment}"
            existing_deployment = self.registry.registry["deployments"].get(deployment_key)

            if existing_deployment and not replace_existing:
                raise ValueError(f"環境 {environment} 中已存在模型 {model_name} 的部署")

            # 創建部署記錄
            deployment_info = {
                "model_name": model_name,
                "version": version,
                "environment": environment,
                "description": description or f"Deploy {model_name} v{version} to {environment}",
                "deployment_config": deployment_config or {},
                "deployed_at": datetime.datetime.now().isoformat(),
                "deployed_by": "system",  # 可以擴展為實際用戶
                "status": "active",
                "previous_deployment": existing_deployment,
                "model_info": {
                    "model_type": model_info["model_type"],
                    "feature_names": model_info["feature_names"],
                    "metrics": model_info["metrics"]
                }
            }

            # 更新註冊表
            self.registry.registry["deployments"][deployment_key] = deployment_info

            # 保存註冊表
            self.registry._save_registry()

            logger.info(f"模型已部署: {model_name} v{version} -> {environment}")
            return deployment_info
            
        except Exception as e:
            logger.error(f"部署模型失敗: {e}")
            raise RuntimeError(f"部署失敗: {e}") from e

    def get_deployment_info(
        self,
        model_name: str,
        environment: str
    ) -> Optional[Dict[str, Any]]:
        """
        獲取部署資訊
        
        Args:
            model_name: 模型名稱
            environment: 環境名稱
            
        Returns:
            部署資訊字典，如果不存在則返回 None
            
        Example:
            >>> deployment_info = deployment_manager.get_deployment_info("my_model", "production")
            >>> if deployment_info:
            ...     print(f"Deployed version: {deployment_info['version']}")
        """
        deployment_key = f"{model_name}:{environment}"
        return self.registry.registry["deployments"].get(deployment_key)

    def list_deployments(
        self,
        environment: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        列出部署
        
        Args:
            environment: 篩選特定環境（可選）
            model_name: 篩選特定模型（可選）
            
        Returns:
            部署資訊列表
            
        Example:
            >>> production_deployments = deployment_manager.list_deployments(environment="production")
            >>> model_deployments = deployment_manager.list_deployments(model_name="my_model")
        """
        deployments = []
        
        for deployment_key, deployment_info in self.registry.registry["deployments"].items():
            # 篩選條件
            if environment and deployment_info["environment"] != environment:
                continue
            if model_name and deployment_info["model_name"] != model_name:
                continue
                
            deployments.append(deployment_info)
        
        # 按部署時間排序
        deployments.sort(key=lambda x: x["deployed_at"], reverse=True)
        return deployments

    def rollback_deployment(
        self,
        model_name: str,
        environment: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        回滾部署到前一個版本
        
        Args:
            model_name: 模型名稱
            environment: 環境名稱
            description: 回滾描述
            
        Returns:
            回滾後的部署資訊
            
        Raises:
            ValueError: 當沒有可回滾的版本時
            
        Example:
            >>> rollback_info = deployment_manager.rollback_deployment(
            ...     "my_model", "production", "Rollback due to performance issue"
            ... )
        """
        try:
            # 獲取當前部署
            current_deployment = self.get_deployment_info(model_name, environment)
            if not current_deployment:
                raise ValueError(f"環境 {environment} 中沒有模型 {model_name} 的部署")

            # 檢查是否有前一個部署
            previous_deployment = current_deployment.get("previous_deployment")
            if not previous_deployment:
                raise ValueError(f"沒有可回滾的版本")

            # 執行回滾
            rollback_deployment = previous_deployment.copy()
            rollback_deployment.update({
                "deployed_at": datetime.datetime.now().isoformat(),
                "description": description or f"Rollback {model_name} in {environment}",
                "status": "active",
                "rollback_from": current_deployment["version"],
                "previous_deployment": None  # 清除前一個部署記錄
            })

            # 更新註冊表
            deployment_key = f"{model_name}:{environment}"
            self.registry.registry["deployments"][deployment_key] = rollback_deployment

            # 保存註冊表
            self.registry._save_registry()

            logger.info(f"部署已回滾: {model_name} {environment} -> v{rollback_deployment['version']}")
            return rollback_deployment
            
        except Exception as e:
            logger.error(f"回滾部署失敗: {e}")
            raise RuntimeError(f"回滾失敗: {e}") from e

    def undeploy_model(
        self,
        model_name: str,
        environment: str,
        description: Optional[str] = None
    ) -> bool:
        """
        取消部署模型
        
        Args:
            model_name: 模型名稱
            environment: 環境名稱
            description: 取消部署描述
            
        Returns:
            是否成功取消部署
            
        Example:
            >>> success = deployment_manager.undeploy_model("my_model", "staging")
        """
        try:
            deployment_key = f"{model_name}:{environment}"
            
            if deployment_key not in self.registry.registry["deployments"]:
                logger.warning(f"部署不存在: {deployment_key}")
                return False

            # 標記為已取消部署
            self.registry.registry["deployments"][deployment_key]["status"] = "undeployed"
            self.registry.registry["deployments"][deployment_key]["undeployed_at"] = datetime.datetime.now().isoformat()
            self.registry.registry["deployments"][deployment_key]["undeploy_description"] = description or "Manual undeploy"

            # 保存註冊表
            self.registry._save_registry()

            logger.info(f"模型已取消部署: {model_name} from {environment}")
            return True
            
        except Exception as e:
            logger.error(f"取消部署失敗: {e}")
            return False

    def get_deployment_history(
        self,
        model_name: str,
        environment: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        獲取部署歷史
        
        Args:
            model_name: 模型名稱
            environment: 環境名稱（可選）
            
        Returns:
            部署歷史列表
            
        Example:
            >>> history = deployment_manager.get_deployment_history("my_model")
            >>> for deployment in history:
            ...     print(f"Version {deployment['version']} deployed at {deployment['deployed_at']}")
        """
        history = []
        
        for deployment_key, deployment_info in self.registry.registry["deployments"].items():
            if deployment_info["model_name"] != model_name:
                continue
            if environment and deployment_info["environment"] != environment:
                continue
                
            history.append(deployment_info)
            
            # 遞歸添加前一個部署
            previous = deployment_info.get("previous_deployment")
            while previous:
                history.append(previous)
                previous = previous.get("previous_deployment")
        
        # 按時間排序
        history.sort(key=lambda x: x["deployed_at"], reverse=True)
        return history

    def get_active_deployments(self) -> Dict[str, Dict[str, Any]]:
        """
        獲取所有活躍的部署
        
        Returns:
            活躍部署字典，鍵為 "model_name:environment"
            
        Example:
            >>> active_deployments = deployment_manager.get_active_deployments()
            >>> for key, deployment in active_deployments.items():
            ...     print(f"{key}: v{deployment['version']}")
        """
        active_deployments = {}
        
        for deployment_key, deployment_info in self.registry.registry["deployments"].items():
            if deployment_info.get("status") == "active":
                active_deployments[deployment_key] = deployment_info
        
        return active_deployments
