"""
風險監控模組

此模組實現了風險監控功能，包括：
- 即時風險監控
- 風險事件記錄
- 交易狀態管理
- 監控循環控制

主要功能：
- 提供持續的風險監控服務
- 記錄和管理風險事件
- 控制交易的啟用和停止
- 支援監控參數配置

Example:
    >>> from src.risk_management.risk_monitoring import RiskMonitor
    >>> monitor = RiskMonitor(risk_manager_core)
    >>> monitor.start_monitoring()
"""

import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from src.core.event_monitor import Event, EventSeverity, EventSource, EventType
from src.core.logger import logger


class RiskMonitor:
    """風險監控器.

    提供即時風險監控功能，包括風險事件記錄和交易狀態管理。

    Attributes:
        risk_manager: 風險管理器實例
        trading_enabled: 交易是否啟用
        monitoring_active: 監控是否啟用
        monitoring_thread: 監控線程
        risk_events: 風險事件列表
    """

    def __init__(self, risk_manager):
        """初始化風險監控器.

        Args:
            risk_manager: 風險管理器實例

        Example:
            >>> manager = RiskManager()
            >>> monitor = RiskMonitor(manager)
        """
        self.risk_manager = risk_manager
        self.trading_enabled = True
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.risk_events: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

        logger.debug("風險監控器初始化完成")

    def stop_trading(self, reason: str) -> None:
        """停止交易.

        Args:
            reason: 停止交易的原因

        Example:
            >>> monitor.stop_trading("觸發日損失限制")
        """
        try:
            with self._lock:
                if self.trading_enabled:
                    self.trading_enabled = False
                    
                    # 記錄風險事件
                    self._record_risk_event(
                        event_type="trading_stopped",
                        reason=reason,
                        timestamp=datetime.now(),
                        severity="high"
                    )
                    
                    logger.warning("交易已停止 - 原因: %s", reason)
                else:
                    logger.info("交易已經處於停止狀態")

        except Exception as e:
            logger.error("停止交易失敗: %s", e, exc_info=True)

    def resume_trading(self, reason: str) -> None:
        """恢復交易.

        Args:
            reason: 恢復交易的原因

        Example:
            >>> monitor.resume_trading("風險條件已改善")
        """
        try:
            with self._lock:
                if not self.trading_enabled:
                    self.trading_enabled = True
                    
                    # 記錄風險事件
                    self._record_risk_event(
                        event_type="trading_resumed",
                        reason=reason,
                        timestamp=datetime.now(),
                        severity="medium"
                    )
                    
                    logger.info("交易已恢復 - 原因: %s", reason)
                else:
                    logger.info("交易已經處於啟用狀態")

        except Exception as e:
            logger.error("恢復交易失敗: %s", e, exc_info=True)

    def is_trading_enabled(self) -> bool:
        """檢查交易是否啟用.

        Returns:
            bool: 交易是否啟用

        Example:
            >>> enabled = monitor.is_trading_enabled()
            >>> print(f"交易啟用狀態: {enabled}")
        """
        with self._lock:
            return self.trading_enabled

    def update_risk_metrics(
        self, 
        returns: pd.Series, 
        risk_free_rate: float = 0.0
    ) -> None:
        """更新風險指標.

        Args:
            returns: 收益率序列
            risk_free_rate: 無風險利率

        Example:
            >>> returns = pd.Series([0.01, -0.02, 0.015, 0.005])
            >>> monitor.update_risk_metrics(returns, 0.02)
        """
        try:
            if self.risk_manager.risk_metrics_calculator:
                self.risk_manager.risk_metrics_calculator.update_metrics(returns, risk_free_rate)
            logger.debug("風險指標已更新")

        except Exception as e:
            logger.error("更新風險指標失敗: %s", e, exc_info=True)

    def get_risk_metrics(self) -> Dict[str, float]:
        """獲取當前風險指標.

        Returns:
            Dict[str, float]: 風險指標字典

        Example:
            >>> metrics = monitor.get_risk_metrics()
            >>> print(f"夏普比率: {metrics.get('sharpe_ratio', 0)}")
        """
        try:
            if self.risk_manager.risk_metrics_calculator:
                return self.risk_manager.risk_metrics_calculator.get_metrics()
            return {}

        except Exception as e:
            logger.error("獲取風險指標失敗: %s", e, exc_info=True)
            return {}

    def _record_risk_event(self, event_type: str, **kwargs) -> None:
        """記錄風險事件.

        Args:
            event_type: 事件類型
            **kwargs: 事件詳細資訊

        Example:
            >>> monitor._record_risk_event("stop_loss_triggered", symbol="AAPL", price=150.0)
        """
        try:
            event_data = {
                "event_type": event_type,
                "timestamp": kwargs.get("timestamp", datetime.now()),
                "severity": kwargs.get("severity", "medium"),
                "details": {k: v for k, v in kwargs.items() 
                           if k not in ["timestamp", "severity"]}
            }

            with self._lock:
                self.risk_events.append(event_data)
                
                # 限制事件列表大小
                if len(self.risk_events) > 1000:
                    self.risk_events = self.risk_events[-500:]

            # 創建系統事件
            try:
                severity_map = {
                    "low": EventSeverity.INFO,
                    "medium": EventSeverity.WARNING,
                    "high": EventSeverity.ERROR,
                    "critical": EventSeverity.CRITICAL
                }
                
                event = Event(
                    event_type=EventType.RISK_ALERT,
                    source=EventSource.RISK_MANAGER,
                    severity=severity_map.get(event_data["severity"], EventSeverity.INFO),
                    message=f"風險事件: {event_type}",
                    data=event_data["details"]
                )
                
                # 這裡可以發送事件到事件監控系統
                logger.debug("風險事件已記錄: %s", event_type)
                
            except Exception as e:
                logger.warning("創建系統事件失敗: %s", e)

        except Exception as e:
            logger.error("記錄風險事件失敗: %s", e, exc_info=True)

    def get_risk_events(
        self, 
        event_type: Optional[str] = None, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """獲取風險事件.

        Args:
            event_type: 事件類型過濾器
            limit: 返回事件數量限制

        Returns:
            List[Dict[str, Any]]: 風險事件列表

        Example:
            >>> events = monitor.get_risk_events("stop_loss_triggered", 50)
            >>> print(f"找到 {len(events)} 個停損事件")
        """
        try:
            with self._lock:
                events = self.risk_events.copy()

            # 按事件類型過濾
            if event_type:
                events = [e for e in events if e["event_type"] == event_type]

            # 按時間排序（最新的在前）
            events.sort(key=lambda x: x["timestamp"], reverse=True)

            # 限制返回數量
            return events[:limit]

        except Exception as e:
            logger.error("獲取風險事件失敗: %s", e, exc_info=True)
            return []

    def start_monitoring(self) -> bool:
        """啟動風險監控.

        Returns:
            bool: 是否啟動成功

        Example:
            >>> success = monitor.start_monitoring()
            >>> print(f"監控啟動: {success}")
        """
        try:
            if self.monitoring_active:
                logger.info("風險監控已經在運行")
                return True

            config = self.risk_manager.config
            monitoring_config = config.get("monitoring", {})
            
            if not monitoring_config.get("enabled", True):
                logger.info("風險監控已禁用")
                return False

            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True
            )
            self.monitoring_thread.start()

            logger.info("風險監控已啟動")
            return True

        except Exception as e:
            logger.error("啟動風險監控失敗: %s", e, exc_info=True)
            return False

    def stop_monitoring(self) -> bool:
        """停止風險監控.

        Returns:
            bool: 是否停止成功

        Example:
            >>> success = monitor.stop_monitoring()
            >>> print(f"監控停止: {success}")
        """
        try:
            if not self.monitoring_active:
                logger.info("風險監控已經停止")
                return True

            self.monitoring_active = False
            
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5.0)

            logger.info("風險監控已停止")
            return True

        except Exception as e:
            logger.error("停止風險監控失敗: %s", e, exc_info=True)
            return False

    def _monitoring_loop(self) -> None:
        """監控循環.

        Note:
            此方法在獨立線程中運行，持續監控風險狀況

        Example:
            >>> # 此方法由 start_monitoring() 自動調用
            >>> # monitor._monitoring_loop()
        """
        try:
            config = self.risk_manager.config
            monitoring_config = config.get("monitoring", {})
            interval = monitoring_config.get("interval", 60)

            logger.info("風險監控循環開始，間隔: %d 秒", interval)

            while self.monitoring_active:
                try:
                    # 執行風險檢查
                    self._perform_risk_checks()
                    
                    # 等待下一次檢查
                    time.sleep(interval)

                except Exception as e:
                    logger.error("監控循環中發生錯誤: %s", e, exc_info=True)
                    time.sleep(10)  # 錯誤後短暫等待

            logger.info("風險監控循環結束")

        except Exception as e:
            logger.error("監控循環失敗: %s", e, exc_info=True)

    def _perform_risk_checks(self) -> None:
        """執行風險檢查.

        Note:
            此方法在監控循環中被調用，執行各種風險檢查

        Example:
            >>> # 此方法由監控循環自動調用
            >>> # monitor._perform_risk_checks()
        """
        try:
            # 檢查投資組合風險
            portfolio_metrics = self.risk_manager.portfolio_risk_manager.calculate_risk_metrics()

            # 檢查風險閾值
            config = self.risk_manager.config
            risk_config = config.get("risk_metrics", {})
            
            # 檢查最大回撤
            max_drawdown_threshold = risk_config.get("max_drawdown", 0.2)
            current_drawdown = portfolio_metrics.get("max_drawdown", 0)
            
            if current_drawdown > max_drawdown_threshold:
                self._record_risk_event(
                    event_type="max_drawdown_exceeded",
                    current_drawdown=current_drawdown,
                    threshold=max_drawdown_threshold,
                    severity="high"
                )

            # 檢查波動率
            volatility_threshold = risk_config.get("volatility_threshold", 0.3)
            current_volatility = portfolio_metrics.get("volatility", 0)
            
            if current_volatility > volatility_threshold:
                self._record_risk_event(
                    event_type="high_volatility",
                    current_volatility=current_volatility,
                    threshold=volatility_threshold,
                    severity="medium"
                )

            logger.debug("風險檢查完成")

        except Exception as e:
            logger.error("執行風險檢查失敗: %s", e, exc_info=True)
