"""風險管理器基礎類別

此模組定義了風險管理器的基礎功能和介面。
"""

import json
import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.logger import logger

from .portfolio_risk import PortfolioRiskManager


class RiskManagerBase:
    """風險管理器基礎類別

    提供風險管理器的基礎功能和配置管理。
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):  # pylint: disable=unused-argument
        """實現單例模式"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化風險管理器基礎功能"""
        if hasattr(self, "_initialized"):
            return

        # 初始化標誌
        self._initialized = True

        # 交易狀態
        self.trading_enabled = True

        # 風險參數
        self.risk_parameters: Dict[str, Any] = {}

        # 風險指標
        self.risk_metrics: Dict[str, float] = {}

        # 風險事件記錄
        self.risk_events: List[Dict[str, Any]] = []

        # 投資組合風險管理器
        self.portfolio_risk_manager = PortfolioRiskManager()

        # 載入預設配置
        self._load_default_config()

        logger.info("風險管理器基礎功能已初始化")

    def _load_default_config(self) -> None:
        """載入預設配置"""
        self.risk_parameters = {
            "max_position_percent": 0.2,
            "max_sector_percent": 0.4,
            "max_drawdown": 0.2,
            "max_daily_loss": 0.02,
            "max_weekly_loss": 0.05,
            "max_monthly_loss": 0.1,
            "monitoring_interval": 60,
            "log_level": "INFO",
        }

    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """載入配置

        Args:
            config_path: 配置文件路徑

        Returns:
            Dict[str, Any]: 配置字典
        """
        default_config = {
            "max_position_percent": 0.2,
            "max_sector_percent": 0.4,
            "max_drawdown": 0.2,
            "max_daily_loss": 0.02,
            "max_weekly_loss": 0.05,
            "max_monthly_loss": 0.1,
            "monitoring_interval": 60,
            "log_level": "INFO",
        }

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # 合併默認配置
                    return {**default_config, **config}
            except Exception as e:
                logger.error("載入配置文件時發生錯誤: %s", e)

        return default_config

    def save_config(self, config_path: str) -> bool:
        """儲存配置

        Args:
            config_path: 配置文件路徑

        Returns:
            bool: 是否成功儲存
        """
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.risk_parameters, f, ensure_ascii=False, indent=2)
            logger.info("配置已儲存至: %s", config_path)
            return True
        except Exception as e:
            logger.error("儲存配置文件時發生錯誤: %s", e)
            return False

    def update_risk_parameter(self, key: str, value: Any) -> bool:
        """更新風險參數

        Args:
            key: 參數鍵
            value: 參數值

        Returns:
            bool: 是否成功更新
        """
        try:
            self.risk_parameters[key] = value
            logger.info("已更新風險參數: %s = %s", key, value)
            return True
        except Exception as e:
            logger.error("更新風險參數時發生錯誤: %s", e)
            return False

    def get_risk_parameter(self, key: str, default: Any = None) -> Any:
        """獲取風險參數

        Args:
            key: 參數鍵
            default: 預設值

        Returns:
            Any: 參數值
        """
        return self.risk_parameters.get(key, default)

    def get_all_risk_parameters(self) -> Dict[str, Any]:
        """獲取所有風險參數

        Returns:
            Dict[str, Any]: 所有風險參數
        """
        return self.risk_parameters.copy()

    def is_trading_enabled(self) -> bool:
        """檢查交易是否啟用

        Returns:
            bool: 交易是否啟用
        """
        return self.trading_enabled

    def stop_trading(self, reason: str) -> None:
        """停止交易

        Args:
            reason: 停止原因
        """
        self.trading_enabled = False
        logger.warning("交易已停止: %s", reason)

        # 記錄風險事件
        self._record_risk_event(event_type="trading_stopped", reason=reason)

    def resume_trading(self, reason: str) -> None:
        """恢復交易

        Args:
            reason: 恢復原因
        """
        self.trading_enabled = True
        logger.info("交易已恢復: %s", reason)

        # 記錄風險事件
        self._record_risk_event(event_type="trading_resumed", reason=reason)

    def _record_risk_event(self, event_type: str, **kwargs) -> None:
        """記錄風險事件

        Args:
            event_type: 事件類型
            **kwargs: 其他參數
        """
        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": kwargs,
        }

        self.risk_events.append(event)
        logger.info("已記錄風險事件: %s", event_type)

    def get_risk_events(
        self, event_type: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """獲取風險事件

        Args:
            event_type: 事件類型，如果為 None 則獲取所有事件
            limit: 最大事件數量

        Returns:
            List[Dict[str, Any]]: 風險事件列表
        """
        if event_type:
            events = [
                event for event in self.risk_events if event["type"] == event_type
            ]
        else:
            events = self.risk_events.copy()

        # 按時間降序排序
        events.sort(key=lambda x: x["timestamp"], reverse=True)

        # 限制數量
        return events[:limit]

    def clear_risk_events(self) -> None:
        """清除風險事件記錄"""
        self.risk_events.clear()
        logger.info("已清除風險事件記錄")

    def get_risk_metrics(self) -> Dict[str, float]:
        """獲取風險指標

        Returns:
            Dict[str, float]: 風險指標
        """
        return self.risk_metrics.copy()

    def update_risk_metrics(self, metrics: Dict[str, float]) -> None:
        """更新風險指標

        Args:
            metrics: 風險指標字典
        """
        self.risk_metrics.update(metrics)
        logger.info("已更新風險指標: %d 個指標", len(metrics))
