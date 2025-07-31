"""
實時風險監控服務 (Risk Monitor Service)

此模組提供實時風險監控的核心服務功能，包括：
- 實時風險指標計算
- 風險閾值監控
- 風險事件檢測
- 風險警報觸發
- 風險報告生成

符合 Phase 7.2 程式碼品質標準：
- Pylint ≥8.5/10
- 100% Google Style Docstring 覆蓋率
- 完整型別標註
- 統一錯誤處理模式
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable

from src.core.risk_management_service import RiskManagementService


logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """風險等級枚舉"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskMetric(Enum):
    """風險指標枚舉"""
    PORTFOLIO_VAR = "portfolio_var"
    POSITION_CONCENTRATION = "position_concentration"
    LEVERAGE_RATIO = "leverage_ratio"
    DRAWDOWN = "drawdown"
    VOLATILITY = "volatility"
    CORRELATION_RISK = "correlation_risk"
    LIQUIDITY_RISK = "liquidity_risk"


class RiskEvent:
    """
    風險事件類別
    
    Attributes:
        event_id: 事件唯一識別碼
        metric: 風險指標
        level: 風險等級
        value: 當前值
        threshold: 閾值
        message: 事件描述
        timestamp: 發生時間
        portfolio_id: 投資組合ID
        symbol: 相關股票代號
        metadata: 額外資訊
    """

    def __init__(
        self,
        metric: RiskMetric,
        level: RiskLevel,
        value: float,
        threshold: float,
        message: str,
        portfolio_id: Optional[str] = None,
        symbol: Optional[str] = None,
        **metadata
    ):
        """
        初始化風險事件
        
        Args:
            metric: 風險指標
            level: 風險等級
            value: 當前值
            threshold: 閾值
            message: 事件描述
            portfolio_id: 投資組合ID
            symbol: 相關股票代號
            **metadata: 額外資訊
        """
        self.event_id = f"risk_{int(time.time() * 1000)}"
        self.metric = metric
        self.level = level
        self.value = value
        self.threshold = threshold
        self.message = message
        self.timestamp = datetime.now()
        self.portfolio_id = portfolio_id
        self.symbol = symbol
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典格式
        
        Returns:
            Dict[str, Any]: 風險事件資訊字典
        """
        return {
            "event_id": self.event_id,
            "metric": self.metric.value,
            "level": self.level.value,
            "value": self.value,
            "threshold": self.threshold,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "portfolio_id": self.portfolio_id,
            "symbol": self.symbol,
            "metadata": self.metadata
        }


class RiskMonitorError(Exception):
    """風險監控錯誤"""
    pass


class RiskMonitorService:
    """
    實時風險監控服務
    
    提供實時風險監控功能，包括風險指標計算、閾值監控、
    事件檢測和警報觸發等。
    
    Attributes:
        _risk_service: 風險管理服務
        _monitor_thread: 監控執行緒
        _is_monitoring: 監控狀態標誌
        _monitor_interval: 監控間隔時間(秒)
        _risk_thresholds: 風險閾值配置
        _risk_events: 風險事件歷史
        _event_callbacks: 事件回調函數列表
        _lock: 執行緒鎖
    """

    def __init__(
        self,
        risk_service: Optional[RiskManagementService] = None,
        monitor_interval: int = 10
    ):
        """
        初始化風險監控服務
        
        Args:
            risk_service: 風險管理服務實例
            monitor_interval: 監控間隔時間(秒)
        """
        self._risk_service = risk_service or RiskManagementService()
        self._monitor_thread: Optional[threading.Thread] = None
        self._is_monitoring = False
        self._monitor_interval = monitor_interval
        self._risk_thresholds = self._get_default_thresholds()
        self._risk_events: List[RiskEvent] = []
        self._event_callbacks: List[Callable[[RiskEvent], None]] = []
        self._lock = threading.Lock()
        
        logger.info("風險監控服務初始化成功")

    def start_monitoring(self) -> None:
        """
        開始風險監控
        
        啟動背景執行緒進行實時風險監控。
        
        Raises:
            RiskMonitorError: 監控啟動失敗時拋出
        """
        if self._is_monitoring:
            logger.warning("風險監控已在運行中")
            return
            
        try:
            self._is_monitoring = True
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                daemon=True
            )
            self._monitor_thread.start()
            logger.info("風險監控已啟動")
        except Exception as e:
            self._is_monitoring = False
            logger.error("啟動風險監控失敗: %s", e)
            raise RiskMonitorError("監控啟動失敗") from e

    def stop_monitoring(self) -> None:
        """
        停止風險監控
        
        停止背景監控執行緒，清理資源。
        """
        self._is_monitoring = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        logger.info("風險監控已停止")

    def set_risk_threshold(
        self,
        metric: RiskMetric,
        level: RiskLevel,
        threshold: float
    ) -> None:
        """
        設定風險閾值
        
        Args:
            metric: 風險指標
            level: 風險等級
            threshold: 閾值
        """
        with self._lock:
            if metric not in self._risk_thresholds:
                self._risk_thresholds[metric] = {}
            self._risk_thresholds[metric][level] = threshold
        
        logger.info("設定風險閾值: %s %s = %f", metric.value, level.value, threshold)

    def get_risk_thresholds(self) -> Dict[RiskMetric, Dict[RiskLevel, float]]:
        """
        獲取風險閾值配置
        
        Returns:
            Dict[RiskMetric, Dict[RiskLevel, float]]: 風險閾值配置
        """
        with self._lock:
            return self._risk_thresholds.copy()

    def calculate_risk_metrics(
        self,
        portfolio_id: Optional[str] = None
    ) -> Dict[RiskMetric, float]:
        """
        計算風險指標
        
        Args:
            portfolio_id: 投資組合ID，為 None 時計算所有投資組合
            
        Returns:
            Dict[RiskMetric, float]: 風險指標值
            
        Raises:
            RiskMonitorError: 計算失敗時拋出
        """
        try:
            metrics = {}
            
            # 計算 VaR (風險價值)
            var_result = self._calculate_var(portfolio_id)
            metrics[RiskMetric.PORTFOLIO_VAR] = var_result
            
            # 計算持倉集中度
            concentration = self._calculate_concentration(portfolio_id)
            metrics[RiskMetric.POSITION_CONCENTRATION] = concentration
            
            # 計算槓桿比率
            leverage = self._calculate_leverage(portfolio_id)
            metrics[RiskMetric.LEVERAGE_RATIO] = leverage
            
            # 計算最大回撤
            drawdown = self._calculate_drawdown(portfolio_id)
            metrics[RiskMetric.DRAWDOWN] = drawdown
            
            # 計算波動率
            volatility = self._calculate_volatility(portfolio_id)
            metrics[RiskMetric.VOLATILITY] = volatility
            
            return metrics
            
        except Exception as e:
            logger.error("計算風險指標失敗: %s", e)
            raise RiskMonitorError("風險指標計算失敗") from e

    def check_risk_violations(
        self,
        metrics: Dict[RiskMetric, float],
        portfolio_id: Optional[str] = None
    ) -> List[RiskEvent]:
        """
        檢查風險違規
        
        Args:
            metrics: 風險指標值
            portfolio_id: 投資組合ID
            
        Returns:
            List[RiskEvent]: 風險事件列表
        """
        violations = []
        
        with self._lock:
            for metric, value in metrics.items():
                if metric in self._risk_thresholds:
                    thresholds = self._risk_thresholds[metric]
                    
                    # 檢查各等級閾值
                    for level in [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM]:
                        if level in thresholds and value >= thresholds[level]:
                            event = RiskEvent(
                                metric=metric,
                                level=level,
                                value=value,
                                threshold=thresholds[level],
                                message=f"{metric.value} 超過 {level.value} 閾值",
                                portfolio_id=portfolio_id
                            )
                            violations.append(event)
                            break  # 只觸發最高等級的違規
        
        return violations

    def get_recent_events(
        self,
        hours: int = 24,
        level: Optional[RiskLevel] = None
    ) -> List[RiskEvent]:
        """
        獲取最近的風險事件
        
        Args:
            hours: 時間範圍(小時)
            level: 篩選風險等級
            
        Returns:
            List[RiskEvent]: 風險事件列表
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            events = []
            for event in self._risk_events:
                if event.timestamp >= cutoff_time:
                    if level is None or event.level == level:
                        events.append(event)
            
            return sorted(events, key=lambda x: x.timestamp, reverse=True)

    def add_event_callback(self, callback: Callable[[RiskEvent], None]) -> None:
        """
        添加事件回調函數
        
        Args:
            callback: 回調函數，接收風險事件
        """
        self._event_callbacks.append(callback)

    def _monitor_loop(self) -> None:
        """
        監控迴圈的背景執行緒
        
        定期計算風險指標並檢查違規情況。
        """
        while self._is_monitoring:
            try:
                # 計算風險指標
                metrics = self.calculate_risk_metrics()
                
                # 檢查風險違規
                violations = self.check_risk_violations(metrics)
                
                # 處理風險事件
                for event in violations:
                    self._handle_risk_event(event)
                
                time.sleep(self._monitor_interval)
                
            except Exception as e:
                logger.error("風險監控迴圈發生錯誤: %s", e)
                time.sleep(60)  # 錯誤時等待更長時間

    def _handle_risk_event(self, event: RiskEvent) -> None:
        """
        處理風險事件
        
        Args:
            event: 風險事件
        """
        with self._lock:
            # 記錄事件
            self._risk_events.append(event)
            
            # 限制事件歷史數量
            if len(self._risk_events) > 1000:
                self._risk_events = self._risk_events[-1000:]
        
        # 觸發回調
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error("執行風險事件回調時發生錯誤: %s", e)
        
        logger.warning("風險事件: %s", event.message)

    def _get_default_thresholds(self) -> Dict[RiskMetric, Dict[RiskLevel, float]]:
        """
        獲取預設風險閾值
        
        Returns:
            Dict[RiskMetric, Dict[RiskLevel, float]]: 預設閾值配置
        """
        return {
            RiskMetric.PORTFOLIO_VAR: {
                RiskLevel.MEDIUM: 0.05,    # 5% VaR
                RiskLevel.HIGH: 0.10,      # 10% VaR
                RiskLevel.CRITICAL: 0.20   # 20% VaR
            },
            RiskMetric.POSITION_CONCENTRATION: {
                RiskLevel.MEDIUM: 0.20,    # 20% 集中度
                RiskLevel.HIGH: 0.30,      # 30% 集中度
                RiskLevel.CRITICAL: 0.50   # 50% 集中度
            },
            RiskMetric.LEVERAGE_RATIO: {
                RiskLevel.MEDIUM: 2.0,     # 2倍槓桿
                RiskLevel.HIGH: 3.0,       # 3倍槓桿
                RiskLevel.CRITICAL: 5.0    # 5倍槓桿
            },
            RiskMetric.DRAWDOWN: {
                RiskLevel.MEDIUM: 0.10,    # 10% 回撤
                RiskLevel.HIGH: 0.20,      # 20% 回撤
                RiskLevel.CRITICAL: 0.30   # 30% 回撤
            },
            RiskMetric.VOLATILITY: {
                RiskLevel.MEDIUM: 0.20,    # 20% 波動率
                RiskLevel.HIGH: 0.30,      # 30% 波動率
                RiskLevel.CRITICAL: 0.50   # 50% 波動率
            }
        }

    def _calculate_var(self, portfolio_id: Optional[str] = None) -> float:
        """
        計算風險價值 (VaR)
        
        Args:
            portfolio_id: 投資組合ID
            
        Returns:
            float: VaR 值
        """
        try:
            # 簡化的 VaR 計算 (實際應使用歷史模擬或蒙地卡羅方法)
            return 0.05  # 暫時返回固定值
        except Exception as e:
            logger.error("計算 VaR 失敗: %s", e)
            return 0.0

    def _calculate_concentration(self, portfolio_id: Optional[str] = None) -> float:
        """
        計算持倉集中度
        
        Args:
            portfolio_id: 投資組合ID
            
        Returns:
            float: 集中度值 (0-1)
        """
        try:
            # 簡化的集中度計算
            return 0.15  # 暫時返回固定值
        except Exception as e:
            logger.error("計算持倉集中度失敗: %s", e)
            return 0.0

    def _calculate_leverage(self, portfolio_id: Optional[str] = None) -> float:
        """
        計算槓桿比率
        
        Args:
            portfolio_id: 投資組合ID
            
        Returns:
            float: 槓桿比率
        """
        try:
            # 簡化的槓桿計算
            return 1.0  # 暫時返回固定值
        except Exception as e:
            logger.error("計算槓桿比率失敗: %s", e)
            return 0.0

    def _calculate_drawdown(self, portfolio_id: Optional[str] = None) -> float:
        """
        計算最大回撤
        
        Args:
            portfolio_id: 投資組合ID
            
        Returns:
            float: 最大回撤值
        """
        try:
            # 簡化的回撤計算
            return 0.08  # 暫時返回固定值
        except Exception as e:
            logger.error("計算最大回撤失敗: %s", e)
            return 0.0

    def _calculate_volatility(self, portfolio_id: Optional[str] = None) -> float:
        """
        計算波動率
        
        Args:
            portfolio_id: 投資組合ID
            
        Returns:
            float: 波動率值
        """
        try:
            # 簡化的波動率計算
            return 0.18  # 暫時返回固定值
        except Exception as e:
            logger.error("計算波動率失敗: %s", e)
            return 0.0
