"""警報處理器

此模組實現統一的警報處理功能。
"""

import logging
from typing import Any, Dict, Optional

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class AlertHandler:
    """警報處理器

    統一處理各種類型的警報創建和發送。

    Attributes:
        alert_manager: 警報管理器實例
    """

    def __init__(self, alert_manager: Any):
        """初始化警報處理器

        Args:
            alert_manager: 警報管理器實例

        Raises:
            ValueError: 當警報管理器為空時
        """
        if not alert_manager:
            raise ValueError("警報管理器不能為空")

        self.alert_manager = alert_manager

        module_logger.info("警報處理器初始化成功")

    def create_system_alert(
        self,
        title: str,
        description: str,
        details: Dict[str, Any],
        severity: str = "warning",
    ) -> None:
        """創建系統警報

        Args:
            title: 警報標題
            description: 警報描述
            details: 警報詳細資訊
            severity: 警報嚴重程度
        """
        try:
            self.alert_manager.create_alert(
                alert_type="system",
                severity=severity,
                title=title,
                description=description,
                source="monitor_system",
                details=details,
            )
            module_logger.info("系統警報已創建: %s", title)

        except Exception as e:
            module_logger.error("創建系統警報失敗: %s", e)

    def create_api_alert(
        self,
        title: str,
        description: str,
        details: Dict[str, Any],
        severity: str = "warning",
    ) -> None:
        """創建 API 警報

        Args:
            title: 警報標題
            description: 警報描述
            details: 警報詳細資訊
            severity: 警報嚴重程度
        """
        try:
            self.alert_manager.create_alert(
                alert_type="api",
                severity=severity,
                title=title,
                description=description,
                source="monitor_system",
                details=details,
            )
            module_logger.info("API 警報已創建: %s", title)

        except Exception as e:
            module_logger.error("創建 API 警報失敗: %s", e)

    def create_model_alert(
        self,
        title: str,
        description: str,
        details: Dict[str, Any],
        severity: str = "warning",
    ) -> None:
        """創建模型警報

        Args:
            title: 警報標題
            description: 警報描述
            details: 警報詳細資訊
            severity: 警報嚴重程度
        """
        try:
            self.alert_manager.create_alert(
                alert_type="model",
                severity=severity,
                title=title,
                description=description,
                source="monitor_system",
                details=details,
            )
            module_logger.info("模型警報已創建: %s", title)

        except Exception as e:
            module_logger.error("創建模型警報失敗: %s", e)

    def create_trade_alert(
        self,
        title: str,
        description: str,
        details: Dict[str, Any],
        severity: str = "warning",
    ) -> None:
        """創建交易警報

        Args:
            title: 警報標題
            description: 警報描述
            details: 警報詳細資訊
            severity: 警報嚴重程度
        """
        try:
            self.alert_manager.create_alert(
                alert_type="trade",
                severity=severity,
                title=title,
                description=description,
                source="monitor_system",
                details=details,
            )
            module_logger.info("交易警報已創建: %s", title)

        except Exception as e:
            module_logger.error("創建交易警報失敗: %s", e)

    def create_custom_alert(
        self,
        alert_type: str,
        title: str,
        description: str,
        details: Dict[str, Any],
        severity: str = "warning",
        source: str = "monitor_system",
    ) -> None:
        """創建自定義警報

        Args:
            alert_type: 警報類型
            title: 警報標題
            description: 警報描述
            details: 警報詳細資訊
            severity: 警報嚴重程度
            source: 警報來源
        """
        try:
            self.alert_manager.create_alert(
                alert_type=alert_type,
                severity=severity,
                title=title,
                description=description,
                source=source,
                details=details,
            )
            module_logger.info("自定義警報已創建: %s", title)

        except Exception as e:
            module_logger.error("創建自定義警報失敗: %s", e)

    def get_alert_stats(self) -> Dict[str, Any]:
        """獲取警報統計資訊

        Returns:
            Dict[str, Any]: 警報統計資訊
        """
        try:
            if hasattr(self.alert_manager, "get_alert_stats"):
                return self.alert_manager.get_alert_stats()
            else:
                return {
                    "total_alerts": 0,
                    "active_alerts": 0,
                    "resolved_alerts": 0,
                    "error": "警報管理器不支援統計功能",
                }

        except Exception as e:
            module_logger.error("獲取警報統計失敗: %s", e)
            return {
                "total_alerts": 0,
                "active_alerts": 0,
                "resolved_alerts": 0,
                "error": str(e),
            }

    def is_healthy(self) -> bool:
        """檢查警報處理器健康狀態

        Returns:
            bool: 健康返回 True，否則返回 False
        """
        try:
            # 檢查警報管理器是否可用
            if not self.alert_manager:
                return False

            # 檢查警報管理器是否有必要的方法
            required_methods = ["create_alert"]
            for method in required_methods:
                if not hasattr(self.alert_manager, method):
                    return False

            return True

        except Exception as e:
            module_logger.error("健康檢查失敗: %s", e)
            return False
