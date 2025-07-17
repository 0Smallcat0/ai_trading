# -*- coding: utf-8 -*-
"""
數據源健康監控器

此模組提供數據源的健康監控和自動故障轉移功能，
確保數據獲取的穩定性和可靠性。

主要功能：
- 數據源健康狀態監控
- 自動故障檢測和恢復
- 數據源性能統計
- 智能故障轉移
- 監控告警機制

監控指標：
- 響應時間
- 成功率
- 數據質量
- 可用性
- 錯誤率
"""

import logging
import time
import asyncio
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import statistics
from collections import deque, defaultdict

# 設定日誌
logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """健康狀態枚舉"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"


@dataclass
class HealthMetrics:
    """健康指標數據類"""
    source_name: str
    status: HealthStatus
    response_time: float
    success_rate: float
    error_rate: float
    availability: float
    last_check_time: datetime
    last_success_time: Optional[datetime] = None
    last_error_time: Optional[datetime] = None
    error_count: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    
    # 性能統計
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    recent_errors: deque = field(default_factory=lambda: deque(maxlen=50))
    
    def update_metrics(self, response_time: float, success: bool, error_msg: str = None):
        """更新指標"""
        self.last_check_time = datetime.now()
        self.total_requests += 1
        
        if success:
            self.successful_requests += 1
            self.last_success_time = datetime.now()
            self.response_times.append(response_time)
        else:
            self.error_count += 1
            self.last_error_time = datetime.now()
            if error_msg:
                self.recent_errors.append({
                    'time': datetime.now(),
                    'error': error_msg
                })
        
        # 計算成功率和錯誤率
        self.success_rate = self.successful_requests / self.total_requests if self.total_requests > 0 else 0
        self.error_rate = self.error_count / self.total_requests if self.total_requests > 0 else 0
        
        # 計算平均響應時間
        if self.response_times:
            self.response_time = statistics.mean(self.response_times)
        
        # 計算可用性（基於最近的成功請求）
        recent_window = 24 * 60 * 60  # 24小時
        if self.last_success_time:
            time_since_success = (datetime.now() - self.last_success_time).total_seconds()
            self.availability = max(0, 1 - (time_since_success / recent_window))
        else:
            self.availability = 0
        
        # 更新健康狀態
        self._update_health_status()
    
    def _update_health_status(self):
        """更新健康狀態"""
        if self.availability < 0.5:
            self.status = HealthStatus.OFFLINE
        elif self.success_rate < 0.7 or self.error_rate > 0.3:
            self.status = HealthStatus.CRITICAL
        elif self.success_rate < 0.9 or self.response_time > 10.0:
            self.status = HealthStatus.WARNING
        else:
            self.status = HealthStatus.HEALTHY


@dataclass
class AlertRule:
    """告警規則"""
    name: str
    condition: Callable[[HealthMetrics], bool]
    severity: str
    message_template: str
    cooldown_seconds: int = 300  # 5分鐘冷卻期
    last_triggered: Optional[datetime] = None
    
    def should_trigger(self, metrics: HealthMetrics) -> bool:
        """檢查是否應該觸發告警"""
        if not self.condition(metrics):
            return False
        
        # 檢查冷卻期
        if self.last_triggered:
            time_since_last = (datetime.now() - self.last_triggered).total_seconds()
            if time_since_last < self.cooldown_seconds:
                return False
        
        return True
    
    def trigger(self, metrics: HealthMetrics) -> str:
        """觸發告警"""
        self.last_triggered = datetime.now()
        return self.message_template.format(
            source=metrics.source_name,
            status=metrics.status.value,
            success_rate=metrics.success_rate,
            error_rate=metrics.error_rate,
            response_time=metrics.response_time,
            availability=metrics.availability
        )


class DataSourceHealthMonitor:
    """
    數據源健康監控器
    
    監控數據源的健康狀態並提供自動故障轉移
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化健康監控器
        
        Args:
            config: 監控配置
        """
        self.config = config
        self.monitoring_enabled = config.get('monitoring_enabled', True)
        self.check_interval = config.get('check_interval', 60)  # 檢查間隔（秒）
        self.health_check_timeout = config.get('health_check_timeout', 10)
        
        # 健康指標存儲
        self.health_metrics: Dict[str, HealthMetrics] = {}
        
        # 告警規則
        self.alert_rules = self._setup_alert_rules()
        
        # 告警回調
        self.alert_callbacks: List[Callable[[str, str], None]] = []
        
        # 故障轉移配置
        self.failover_enabled = config.get('failover_enabled', True)
        self.failover_rules = config.get('failover_rules', {})
        
        # 監控線程
        self.monitor_thread = None
        self.monitoring_active = False
        
        logger.info("數據源健康監控器初始化完成")
    
    def _setup_alert_rules(self) -> List[AlertRule]:
        """設置告警規則"""
        rules = []
        
        # 高錯誤率告警
        rules.append(AlertRule(
            name="high_error_rate",
            condition=lambda m: m.error_rate > 0.3,
            severity="critical",
            message_template="數據源 {source} 錯誤率過高: {error_rate:.2%}",
            cooldown_seconds=300
        ))
        
        # 低成功率告警
        rules.append(AlertRule(
            name="low_success_rate",
            condition=lambda m: m.success_rate < 0.7,
            severity="critical",
            message_template="數據源 {source} 成功率過低: {success_rate:.2%}",
            cooldown_seconds=300
        ))
        
        # 響應時間過長告警
        rules.append(AlertRule(
            name="slow_response",
            condition=lambda m: m.response_time > 10.0,
            severity="warning",
            message_template="數據源 {source} 響應時間過長: {response_time:.2f}秒",
            cooldown_seconds=600
        ))
        
        # 可用性低告警
        rules.append(AlertRule(
            name="low_availability",
            condition=lambda m: m.availability < 0.8,
            severity="critical",
            message_template="數據源 {source} 可用性過低: {availability:.2%}",
            cooldown_seconds=300
        ))
        
        # 離線告警
        rules.append(AlertRule(
            name="offline",
            condition=lambda m: m.status == HealthStatus.OFFLINE,
            severity="critical",
            message_template="數據源 {source} 已離線",
            cooldown_seconds=180
        ))
        
        return rules
    
    def register_data_source(self, source_name: str):
        """註冊數據源"""
        if source_name not in self.health_metrics:
            self.health_metrics[source_name] = HealthMetrics(
                source_name=source_name,
                status=HealthStatus.HEALTHY,
                response_time=0.0,
                success_rate=1.0,
                error_rate=0.0,
                availability=1.0,
                last_check_time=datetime.now()
            )
            logger.info(f"註冊數據源: {source_name}")
    
    def record_request(self, source_name: str, response_time: float, success: bool, error_msg: str = None):
        """記錄請求結果"""
        if source_name not in self.health_metrics:
            self.register_data_source(source_name)
        
        metrics = self.health_metrics[source_name]
        metrics.update_metrics(response_time, success, error_msg)
        
        # 檢查告警
        self._check_alerts(metrics)
        
        logger.debug(f"記錄請求: {source_name}, 成功: {success}, 響應時間: {response_time:.2f}s")
    
    def _check_alerts(self, metrics: HealthMetrics):
        """檢查告警條件"""
        for rule in self.alert_rules:
            if rule.should_trigger(metrics):
                alert_message = rule.trigger(metrics)
                self._send_alert(rule.severity, alert_message)
    
    def _send_alert(self, severity: str, message: str):
        """發送告警"""
        logger.warning(f"[{severity.upper()}] {message}")
        
        # 調用註冊的告警回調
        for callback in self.alert_callbacks:
            try:
                callback(severity, message)
            except Exception as e:
                logger.error(f"告警回調執行失敗: {e}")
    
    def add_alert_callback(self, callback: Callable[[str, str], None]):
        """添加告警回調"""
        self.alert_callbacks.append(callback)
    
    def get_health_status(self, source_name: str) -> Optional[HealthMetrics]:
        """獲取數據源健康狀態"""
        return self.health_metrics.get(source_name)
    
    def get_all_health_status(self) -> Dict[str, HealthMetrics]:
        """獲取所有數據源健康狀態"""
        return self.health_metrics.copy()
    
    def get_healthy_sources(self) -> List[str]:
        """獲取健康的數據源列表"""
        healthy_sources = []
        for source_name, metrics in self.health_metrics.items():
            if metrics.status in [HealthStatus.HEALTHY, HealthStatus.WARNING]:
                healthy_sources.append(source_name)
        return healthy_sources
    
    def get_best_source(self, sources: List[str]) -> Optional[str]:
        """從給定源中選擇最佳數據源"""
        if not sources:
            return None
        
        # 過濾可用的源
        available_sources = []
        for source in sources:
            if source in self.health_metrics:
                metrics = self.health_metrics[source]
                if metrics.status != HealthStatus.OFFLINE:
                    available_sources.append((source, metrics))
        
        if not available_sources:
            return sources[0]  # 如果沒有健康狀態信息，返回第一個
        
        # 按綜合評分排序
        def calculate_score(metrics: HealthMetrics) -> float:
            # 綜合評分：成功率 * 可用性 / 響應時間
            response_factor = 1.0 / (1.0 + metrics.response_time)
            return metrics.success_rate * metrics.availability * response_factor
        
        available_sources.sort(key=lambda x: calculate_score(x[1]), reverse=True)
        return available_sources[0][0]
    
    def start_monitoring(self):
        """開始監控"""
        if not self.monitoring_enabled:
            logger.info("健康監控已禁用")
            return
        
        if self.monitoring_active:
            logger.warning("監控已在運行中")
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("健康監控已啟動")
    
    def stop_monitoring(self):
        """停止監控"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("健康監控已停止")
    
    def _monitoring_loop(self):
        """監控循環"""
        while self.monitoring_active:
            try:
                self._perform_health_checks()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"健康檢查執行失敗: {e}")
                time.sleep(self.check_interval)
    
    def _perform_health_checks(self):
        """執行健康檢查"""
        for source_name in self.health_metrics:
            try:
                # 這裡可以實現具體的健康檢查邏輯
                # 例如發送測試請求到數據源
                self._check_source_health(source_name)
            except Exception as e:
                logger.error(f"檢查數據源 {source_name} 健康狀態失敗: {e}")
    
    def _check_source_health(self, source_name: str):
        """檢查單個數據源健康狀態"""
        # 這裡實現具體的健康檢查邏輯
        # 可以發送簡單的測試請求來檢查數據源是否響應
        pass
    
    def get_monitoring_report(self) -> Dict[str, Any]:
        """獲取監控報告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_sources': len(self.health_metrics),
            'healthy_sources': len([m for m in self.health_metrics.values() if m.status == HealthStatus.HEALTHY]),
            'warning_sources': len([m for m in self.health_metrics.values() if m.status == HealthStatus.WARNING]),
            'critical_sources': len([m for m in self.health_metrics.values() if m.status == HealthStatus.CRITICAL]),
            'offline_sources': len([m for m in self.health_metrics.values() if m.status == HealthStatus.OFFLINE]),
            'sources': {}
        }
        
        for source_name, metrics in self.health_metrics.items():
            report['sources'][source_name] = {
                'status': metrics.status.value,
                'success_rate': metrics.success_rate,
                'error_rate': metrics.error_rate,
                'response_time': metrics.response_time,
                'availability': metrics.availability,
                'total_requests': metrics.total_requests,
                'last_check_time': metrics.last_check_time.isoformat() if metrics.last_check_time else None,
                'last_success_time': metrics.last_success_time.isoformat() if metrics.last_success_time else None
            }
        
        return report
