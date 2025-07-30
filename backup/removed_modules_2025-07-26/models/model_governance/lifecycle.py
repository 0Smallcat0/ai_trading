# -*- coding: utf-8 -*-
"""
模型生命週期管理器

此模組實現模型生命週期管理功能，包括：
- 模型狀態管理
- 自動化工作流程
- 模型退役和清理
- 生命週期事件追蹤

Classes:
    ModelLifecycleManager: 模型生命週期管理器主類
"""

import datetime
import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from src.config import LOG_LEVEL
from .registry import ModelRegistry
from .monitor import ModelMonitor

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class ModelStatus(Enum):
    """模型狀態枚舉"""

    REGISTERED = "registered"
    VALIDATED = "validated"
    DEPLOYED = "deployed"
    MONITORING = "monitoring"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class ModelLifecycleManager:
    """
    模型生命週期管理器

    管理模型從註冊到退役的完整生命週期。

    Attributes:
        registry: 模型註冊表
        monitors: 模型監控器字典

    Example:
        >>> lifecycle_manager = ModelLifecycleManager(registry)
        >>> lifecycle_manager.transition_model_status("my_model", "v1.0", ModelStatus.DEPLOYED)
        >>> lifecycle_manager.retire_model("old_model", reason="Performance degradation")

    Note:
        自動化模型生命週期管理
        支援狀態轉換驗證和事件記錄
        提供模型清理和資源回收功能
    """

    def __init__(self, registry: Optional[ModelRegistry] = None):
        """
        初始化生命週期管理器

        Args:
            registry: 模型註冊表實例
        """
        self.registry = registry or ModelRegistry()
        self.monitors: Dict[str, ModelMonitor] = {}

        # 初始化生命週期事件記錄
        if "lifecycle_events" not in self.registry.registry:
            self.registry.registry["lifecycle_events"] = {}

        logger.info("模型生命週期管理器已初始化")

    def transition_model_status(
        self,
        model_name: str,
        version: str,
        new_status: ModelStatus,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        轉換模型狀態

        Args:
            model_name: 模型名稱
            version: 模型版本
            new_status: 新狀態
            reason: 轉換原因
            metadata: 額外元數據

        Returns:
            是否成功轉換狀態

        Raises:
            ValueError: 當狀態轉換無效時

        Example:
            >>> success = lifecycle_manager.transition_model_status(
            ...     "my_model", "v1.0", ModelStatus.DEPLOYED,
            ...     reason="Passed validation tests"
            ... )
        """
        try:
            # 獲取模型資訊
            model_info = self.registry.get_model_info(model_name, version)
            current_status = ModelStatus(model_info.get("status", "registered"))

            # 驗證狀態轉換
            if not self._is_valid_transition(current_status, new_status):
                raise ValueError(
                    f"無效的狀態轉換: {current_status.value} -> {new_status.value}"
                )

            # 更新模型狀態
            self.registry.registry["models"][model_name][version][
                "status"
            ] = new_status.value
            self.registry.registry["models"][model_name][version][
                "status_updated_at"
            ] = datetime.datetime.now().isoformat()

            # 記錄生命週期事件
            self._log_lifecycle_event(
                model_name=model_name,
                version=version,
                event_type="status_transition",
                from_status=current_status.value,
                to_status=new_status.value,
                reason=reason,
                metadata=metadata,
            )

            # 執行狀態特定的操作
            self._handle_status_transition(model_name, version, new_status)

            # 保存註冊表
            self.registry._save_registry()

            logger.info(
                f"模型狀態已轉換: {model_name} v{version} {current_status.value} -> {new_status.value}"
            )
            return True

        except Exception as e:
            logger.error(f"轉換模型狀態失敗: {e}")
            return False

    def _is_valid_transition(
        self, current_status: ModelStatus, new_status: ModelStatus
    ) -> bool:
        """
        驗證狀態轉換是否有效

        Args:
            current_status: 當前狀態
            new_status: 新狀態

        Returns:
            是否為有效轉換
        """
        # 定義有效的狀態轉換
        valid_transitions = {
            ModelStatus.REGISTERED: [ModelStatus.VALIDATED, ModelStatus.DEPRECATED],
            ModelStatus.VALIDATED: [ModelStatus.DEPLOYED, ModelStatus.DEPRECATED],
            ModelStatus.DEPLOYED: [ModelStatus.MONITORING, ModelStatus.DEPRECATED],
            ModelStatus.MONITORING: [ModelStatus.DEPRECATED, ModelStatus.RETIRED],
            ModelStatus.DEPRECATED: [ModelStatus.RETIRED],
            ModelStatus.RETIRED: [],  # 退役狀態不能轉換
        }

        return new_status in valid_transitions.get(current_status, [])

    def _handle_status_transition(
        self, model_name: str, version: str, new_status: ModelStatus
    ) -> None:
        """
        處理狀態轉換的特定操作

        Args:
            model_name: 模型名稱
            version: 模型版本
            new_status: 新狀態
        """
        if new_status == ModelStatus.MONITORING:
            # 啟動監控
            self._start_monitoring(model_name, version)
        elif new_status == ModelStatus.DEPRECATED:
            # 停止監控
            self._stop_monitoring(model_name, version)
        elif new_status == ModelStatus.RETIRED:
            # 清理資源
            self._cleanup_model_resources(model_name, version)

    def _start_monitoring(self, model_name: str, version: str) -> None:
        """
        啟動模型監控

        Args:
            model_name: 模型名稱
            version: 模型版本
        """
        try:
            monitor_key = f"{model_name}:{version}"
            if monitor_key not in self.monitors:
                monitor = ModelMonitor(model_name, version, self.registry)
                self.monitors[monitor_key] = monitor
                logger.info(f"已啟動監控: {model_name} v{version}")
        except Exception as e:
            logger.error(f"啟動監控失敗: {e}")

    def _stop_monitoring(self, model_name: str, version: str) -> None:
        """
        停止模型監控

        Args:
            model_name: 模型名稱
            version: 模型版本
        """
        monitor_key = f"{model_name}:{version}"
        if monitor_key in self.monitors:
            del self.monitors[monitor_key]
            logger.info(f"已停止監控: {model_name} v{version}")

    def _cleanup_model_resources(self, model_name: str, version: str) -> None:
        """
        清理模型資源

        Args:
            model_name: 模型名稱
            version: 模型版本
        """
        try:
            # 停止監控
            self._stop_monitoring(model_name, version)

            # 可以添加其他清理操作，如刪除模型檔案等
            logger.info(f"已清理模型資源: {model_name} v{version}")
        except Exception as e:
            logger.error(f"清理模型資源失敗: {e}")

    def _log_lifecycle_event(
        self, model_name: str, version: str, event_type: str, **kwargs: Any
    ) -> None:
        """
        記錄生命週期事件

        Args:
            model_name: 模型名稱
            version: 模型版本
            event_type: 事件類型
            **kwargs: 其他事件資料
        """
        event_key = f"{model_name}:{version}"

        if event_key not in self.registry.registry["lifecycle_events"]:
            self.registry.registry["lifecycle_events"][event_key] = []

        event = {
            "timestamp": datetime.datetime.now().isoformat(),
            "event_type": event_type,
            "model_name": model_name,
            "version": version,
            **kwargs,
        }

        self.registry.registry["lifecycle_events"][event_key].append(event)

    def retire_model(
        self,
        model_name: str,
        version: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> bool:
        """
        退役模型

        Args:
            model_name: 模型名稱
            version: 模型版本，如果為 None 則退役所有版本
            reason: 退役原因

        Returns:
            是否成功退役

        Example:
            >>> success = lifecycle_manager.retire_model(
            ...     "old_model", reason="Replaced by new version"
            ... )
        """
        try:
            if version:
                versions = [version]
            else:
                versions = self.registry.list_versions(model_name)

            success_count = 0
            for ver in versions:
                if self.transition_model_status(
                    model_name, ver, ModelStatus.RETIRED, reason
                ):
                    success_count += 1

            logger.info(
                f"已退役 {success_count}/{len(versions)} 個模型版本: {model_name}"
            )
            return success_count == len(versions)

        except Exception as e:
            logger.error(f"退役模型失敗: {e}")
            return False

    def get_model_lifecycle_status(
        self, model_name: str, version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        獲取模型生命週期狀態

        Args:
            model_name: 模型名稱
            version: 模型版本

        Returns:
            生命週期狀態資訊

        Example:
            >>> status = lifecycle_manager.get_model_lifecycle_status("my_model", "v1.0")
            >>> print(f"Current status: {status['current_status']}")
        """
        try:
            model_info = self.registry.get_model_info(model_name, version)

            status_info = {
                "model_name": model_name,
                "version": model_info["version"],
                "current_status": model_info.get("status", "registered"),
                "status_updated_at": model_info.get("status_updated_at"),
                "created_at": model_info["created_at"],
                "is_monitoring": f"{model_name}:{model_info['version']}"
                in self.monitors,
            }

            return status_info

        except Exception as e:
            logger.error(f"獲取生命週期狀態失敗: {e}")
            return {}

    def get_lifecycle_events(
        self, model_name: str, version: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        獲取生命週期事件

        Args:
            model_name: 模型名稱
            version: 模型版本

        Returns:
            生命週期事件列表

        Example:
            >>> events = lifecycle_manager.get_lifecycle_events("my_model", "v1.0")
            >>> for event in events:
            ...     print(f"{event['timestamp']}: {event['event_type']}")
        """
        if version:
            event_key = f"{model_name}:{version}"
            return self.registry.registry["lifecycle_events"].get(event_key, [])
        else:
            # 獲取所有版本的事件
            all_events = []
            for event_key, events in self.registry.registry["lifecycle_events"].items():
                if event_key.startswith(f"{model_name}:"):
                    all_events.extend(events)

            # 按時間排序
            all_events.sort(key=lambda x: x["timestamp"], reverse=True)
            return all_events

    def get_models_by_status(self, status: ModelStatus) -> List[Dict[str, Any]]:
        """
        根據狀態獲取模型列表

        Args:
            status: 模型狀態

        Returns:
            符合狀態的模型列表

        Example:
            >>> deployed_models = lifecycle_manager.get_models_by_status(ModelStatus.DEPLOYED)
            >>> for model in deployed_models:
            ...     print(f"{model['name']} v{model['version']}")
        """
        models = []

        for model_name in self.registry.list_models():
            for version in self.registry.list_versions(model_name):
                model_info = self.registry.get_model_info(model_name, version)
                if model_info.get("status") == status.value:
                    models.append(
                        {
                            "name": model_name,
                            "version": version,
                            "status": status.value,
                            "created_at": model_info["created_at"],
                            "status_updated_at": model_info.get("status_updated_at"),
                        }
                    )

        return models
