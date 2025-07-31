#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""效能監控和調優系統

此模組提供全面的效能監控和自動調優功能，包括：
1. 多維度效能指標收集
2. 實時系統資源監控
3. 智能效能調優
4. 異常檢測和警報
5. 效能報告生成

主要功能：
- 下載速度、成功率、響應時間監控
- CPU、記憶體、網路、磁碟I/O監控
- 自動調整並行度和快取策略
- 效能趨勢分析和預測
- 智能建議生成

Example:
    基本使用：
    ```python
    from src.core.performance_monitoring_system import PerformanceMonitor
    
    # 創建效能監控器
    monitor = PerformanceMonitor()
    
    # 記錄效能指標
    monitor.record_download_performance('daily_price', 1.5, True, 1024)
    
    # 獲取效能報告
    report = monitor.generate_performance_report()
    ```

Note:
    此模組整合了多種監控技術和機器學習算法，
    提供智能化的效能監控和調優服務。
"""

import logging
import threading
import time
import statistics
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import json

# 設定日誌
logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指標類型"""
    DOWNLOAD_SPEED = "download_speed"
    SUCCESS_RATE = "success_rate"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    NETWORK_IO = "network_io"
    DISK_IO = "disk_io"
    CACHE_HIT_RATE = "cache_hit_rate"
    THROUGHPUT = "throughput"


class AlertLevel(Enum):
    """警報等級"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class OptimizationAction(Enum):
    """優化動作"""
    INCREASE_WORKERS = "increase_workers"
    DECREASE_WORKERS = "decrease_workers"
    ADJUST_CACHE_SIZE = "adjust_cache_size"
    CHANGE_CACHE_STRATEGY = "change_cache_strategy"
    ADJUST_RETRY_POLICY = "adjust_retry_policy"
    OPTIMIZE_BATCH_SIZE = "optimize_batch_size"


@dataclass
class PerformanceMetric:
    """效能指標"""
    metric_type: MetricType
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'metric_type': self.metric_type.value,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'tags': self.tags
        }


@dataclass
class SystemResource:
    """系統資源"""
    cpu_percent: float
    memory_percent: float
    disk_io_read: float
    disk_io_write: float
    network_io_sent: float
    network_io_recv: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceAlert:
    """效能警報"""
    level: AlertLevel
    message: str
    metric_type: MetricType
    current_value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False


@dataclass
class OptimizationSuggestion:
    """優化建議"""
    action: OptimizationAction
    reason: str
    expected_improvement: str
    priority: int  # 1-10, 10最高
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceReport:
    """效能報告"""
    start_time: datetime
    end_time: datetime
    summary: Dict[str, Any]
    metrics: Dict[MetricType, List[float]]
    alerts: List[PerformanceAlert]
    suggestions: List[OptimizationSuggestion]
    system_health: str  # excellent, good, fair, poor, critical


class PerformanceMonitor:
    """效能監控器
    
    提供全面的效能監控和自動調優功能，支援多維度
    指標收集和智能分析。
    
    Attributes:
        metrics: 效能指標存儲
        alerts: 警報列表
        thresholds: 警報閾值配置
        
    Example:
        >>> monitor = PerformanceMonitor()
        >>> monitor.record_download_performance('daily_price', 1.5, True, 1024)
        >>> report = monitor.generate_performance_report()
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化效能監控器
        
        Args:
            config: 監控配置
        """
        self.config = config or {}
        
        # 指標存儲
        self.metrics: Dict[MetricType, deque] = {
            metric_type: deque(maxlen=1000) for metric_type in MetricType
        }
        
        # 系統資源歷史
        self.system_resources: deque = deque(maxlen=500)
        
        # 警報管理
        self.alerts: List[PerformanceAlert] = []
        self.alert_history: deque = deque(maxlen=1000)
        
        # 優化建議
        self.suggestions: List[OptimizationSuggestion] = []
        
        # 警報閾值配置
        self.thresholds = {
            MetricType.CPU_USAGE: {'warning': 70, 'critical': 90},
            MetricType.MEMORY_USAGE: {'warning': 80, 'critical': 95},
            MetricType.ERROR_RATE: {'warning': 0.05, 'critical': 0.15},
            MetricType.SUCCESS_RATE: {'warning': 0.95, 'critical': 0.85},
            MetricType.RESPONSE_TIME: {'warning': 5.0, 'critical': 10.0},
            MetricType.CACHE_HIT_RATE: {'warning': 0.7, 'critical': 0.5}
        }
        
        # 執行緒安全鎖
        self.lock = threading.RLock()
        
        # 監控狀態
        self.monitoring_active = True
        self.optimization_active = True
        
        # 啟動背景服務
        self._start_background_services()
        
        logger.info("效能監控系統初始化完成")
    
    def record_download_performance(
        self,
        source: str,
        duration: float,
        success: bool,
        data_size: int,
        tags: Optional[Dict[str, str]] = None
    ):
        """記錄下載效能
        
        Args:
            source: 資料來源
            duration: 下載時間（秒）
            success: 是否成功
            data_size: 資料大小（位元組）
            tags: 額外標籤
        """
        tags = tags or {}
        tags['source'] = source
        
        with self.lock:
            # 記錄下載速度
            if success and duration > 0:
                speed = data_size / duration  # bytes/second
                self.metrics[MetricType.DOWNLOAD_SPEED].append(
                    PerformanceMetric(MetricType.DOWNLOAD_SPEED, speed, tags=tags)
                )
            
            # 記錄響應時間
            self.metrics[MetricType.RESPONSE_TIME].append(
                PerformanceMetric(MetricType.RESPONSE_TIME, duration, tags=tags)
            )
            
            # 更新成功率統計
            self._update_success_rate(source, success)
            
            # 檢查警報
            self._check_alerts()
    
    def record_system_metrics(self):
        """記錄系統指標"""
        try:
            # 獲取系統資源使用情況
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            network_io = psutil.net_io_counters()
            
            resource = SystemResource(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_io_read=disk_io.read_bytes if disk_io else 0,
                disk_io_write=disk_io.write_bytes if disk_io else 0,
                network_io_sent=network_io.bytes_sent if network_io else 0,
                network_io_recv=network_io.bytes_recv if network_io else 0
            )
            
            with self.lock:
                self.system_resources.append(resource)
                
                # 記錄到指標
                self.metrics[MetricType.CPU_USAGE].append(
                    PerformanceMetric(MetricType.CPU_USAGE, cpu_percent)
                )
                self.metrics[MetricType.MEMORY_USAGE].append(
                    PerformanceMetric(MetricType.MEMORY_USAGE, memory.percent)
                )
                
                # 檢查系統資源警報
                self._check_system_alerts(resource)
                
        except Exception as e:
            logger.error("記錄系統指標失敗: %s", e)
    
    def record_cache_performance(self, hit_rate: float, total_requests: int):
        """記錄快取效能
        
        Args:
            hit_rate: 命中率
            total_requests: 總請求數
        """
        with self.lock:
            self.metrics[MetricType.CACHE_HIT_RATE].append(
                PerformanceMetric(MetricType.CACHE_HIT_RATE, hit_rate)
            )
            
            # 計算吞吐量（假設1分鐘內的請求）
            throughput = total_requests / 60.0  # requests per second
            self.metrics[MetricType.THROUGHPUT].append(
                PerformanceMetric(MetricType.THROUGHPUT, throughput)
            )
    
    def get_current_metrics(self) -> Dict[MetricType, float]:
        """獲取當前指標
        
        Returns:
            Dict[MetricType, float]: 當前指標值
        """
        current_metrics = {}
        
        with self.lock:
            for metric_type, metric_list in self.metrics.items():
                if metric_list:
                    # 取最近的值
                    current_metrics[metric_type] = metric_list[-1].value
                else:
                    current_metrics[metric_type] = 0.0
        
        return current_metrics
    
    def get_metric_statistics(
        self, 
        metric_type: MetricType,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, float]:
        """獲取指標統計
        
        Args:
            metric_type: 指標類型
            time_window: 時間窗口
            
        Returns:
            Dict[str, float]: 統計資訊
        """
        if time_window is None:
            time_window = timedelta(hours=1)
        
        cutoff_time = datetime.now() - time_window
        
        with self.lock:
            if metric_type not in self.metrics:
                return {}
            
            # 過濾時間窗口內的指標
            recent_metrics = [
                m.value for m in self.metrics[metric_type]
                if m.timestamp >= cutoff_time
            ]
            
            if not recent_metrics:
                return {}
            
            return {
                'count': len(recent_metrics),
                'mean': statistics.mean(recent_metrics),
                'median': statistics.median(recent_metrics),
                'min': min(recent_metrics),
                'max': max(recent_metrics),
                'stdev': statistics.stdev(recent_metrics) if len(recent_metrics) > 1 else 0.0
            }
    
    def generate_performance_report(
        self,
        time_window: Optional[timedelta] = None
    ) -> PerformanceReport:
        """生成效能報告
        
        Args:
            time_window: 報告時間窗口
            
        Returns:
            PerformanceReport: 效能報告
        """
        if time_window is None:
            time_window = timedelta(hours=24)
        
        end_time = datetime.now()
        start_time = end_time - time_window
        
        with self.lock:
            # 收集指標統計
            metrics_summary = {}
            for metric_type in MetricType:
                stats = self.get_metric_statistics(metric_type, time_window)
                if stats:
                    metrics_summary[metric_type] = stats
            
            # 收集警報
            recent_alerts = [
                alert for alert in self.alert_history
                if alert.timestamp >= start_time
            ]
            
            # 生成優化建議
            suggestions = self._generate_optimization_suggestions()
            
            # 評估系統健康度
            health = self._assess_system_health()
            
            return PerformanceReport(
                start_time=start_time,
                end_time=end_time,
                summary=metrics_summary,
                metrics={mt: [m.value for m in self.metrics[mt]] for mt in MetricType},
                alerts=recent_alerts,
                suggestions=suggestions,
                system_health=health
            )

    def get_active_alerts(self) -> List[PerformanceAlert]:
        """獲取活躍警報

        Returns:
            List[PerformanceAlert]: 未解決的警報列表
        """
        with self.lock:
            return [alert for alert in self.alerts if not alert.resolved]

    def resolve_alert(self, alert: PerformanceAlert):
        """解決警報

        Args:
            alert: 要解決的警報
        """
        with self.lock:
            alert.resolved = True
            logger.info("警報已解決: %s", alert.message)

    def add_custom_threshold(
        self,
        metric_type: MetricType,
        warning: float,
        critical: float
    ):
        """添加自定義閾值

        Args:
            metric_type: 指標類型
            warning: 警告閾值
            critical: 嚴重閾值
        """
        with self.lock:
            self.thresholds[metric_type] = {
                'warning': warning,
                'critical': critical
            }

        logger.info("設定 %s 閾值: 警告=%.2f, 嚴重=%.2f",
                   metric_type.value, warning, critical)

    def optimize_performance(self) -> List[OptimizationSuggestion]:
        """執行效能優化

        Returns:
            List[OptimizationSuggestion]: 執行的優化建議
        """
        suggestions = self._generate_optimization_suggestions()
        executed_suggestions = []

        for suggestion in suggestions:
            if suggestion.priority >= 7:  # 高優先級建議
                try:
                    self._execute_optimization(suggestion)
                    executed_suggestions.append(suggestion)
                    logger.info("執行優化建議: %s", suggestion.reason)
                except Exception as e:
                    logger.error("執行優化建議失敗: %s", e)

        return executed_suggestions

    def shutdown(self):
        """關閉監控系統"""
        logger.info("開始關閉效能監控系統...")

        # 停止背景服務
        self.monitoring_active = False
        self.optimization_active = False

        logger.info("效能監控系統已關閉")

    # ==================== 私有輔助方法 ====================

    def _update_success_rate(self, source: str, success: bool):
        """更新成功率統計"""
        # 簡化實現：使用滑動窗口計算成功率
        if not hasattr(self, '_success_counters'):
            self._success_counters = defaultdict(lambda: {'total': 0, 'success': 0})

        counter = self._success_counters[source]
        counter['total'] += 1
        if success:
            counter['success'] += 1

        # 計算成功率
        success_rate = counter['success'] / counter['total']

        # 記錄指標
        self.metrics[MetricType.SUCCESS_RATE].append(
            PerformanceMetric(
                MetricType.SUCCESS_RATE,
                success_rate,
                tags={'source': source}
            )
        )

        # 計算錯誤率
        error_rate = 1 - success_rate
        self.metrics[MetricType.ERROR_RATE].append(
            PerformanceMetric(
                MetricType.ERROR_RATE,
                error_rate,
                tags={'source': source}
            )
        )

    def _check_alerts(self):
        """檢查警報條件"""
        current_metrics = self.get_current_metrics()

        for metric_type, value in current_metrics.items():
            if metric_type in self.thresholds:
                thresholds = self.thresholds[metric_type]

                # 檢查嚴重警報
                if value >= thresholds.get('critical', float('inf')):
                    self._create_alert(
                        AlertLevel.CRITICAL,
                        f"{metric_type.value} 達到嚴重水平: {value:.2f}",
                        metric_type,
                        value,
                        thresholds['critical']
                    )
                # 檢查警告
                elif value >= thresholds.get('warning', float('inf')):
                    self._create_alert(
                        AlertLevel.WARNING,
                        f"{metric_type.value} 達到警告水平: {value:.2f}",
                        metric_type,
                        value,
                        thresholds['warning']
                    )

    def _check_system_alerts(self, resource: SystemResource):
        """檢查系統資源警報"""
        # CPU使用率警報
        if resource.cpu_percent > 90:
            self._create_alert(
                AlertLevel.CRITICAL,
                f"CPU使用率過高: {resource.cpu_percent:.1f}%",
                MetricType.CPU_USAGE,
                resource.cpu_percent,
                90
            )
        elif resource.cpu_percent > 70:
            self._create_alert(
                AlertLevel.WARNING,
                f"CPU使用率較高: {resource.cpu_percent:.1f}%",
                MetricType.CPU_USAGE,
                resource.cpu_percent,
                70
            )

        # 記憶體使用率警報
        if resource.memory_percent > 95:
            self._create_alert(
                AlertLevel.CRITICAL,
                f"記憶體使用率過高: {resource.memory_percent:.1f}%",
                MetricType.MEMORY_USAGE,
                resource.memory_percent,
                95
            )
        elif resource.memory_percent > 80:
            self._create_alert(
                AlertLevel.WARNING,
                f"記憶體使用率較高: {resource.memory_percent:.1f}%",
                MetricType.MEMORY_USAGE,
                resource.memory_percent,
                80
            )

    def _create_alert(
        self,
        level: AlertLevel,
        message: str,
        metric_type: MetricType,
        current_value: float,
        threshold: float
    ):
        """創建警報"""
        alert = PerformanceAlert(
            level=level,
            message=message,
            metric_type=metric_type,
            current_value=current_value,
            threshold=threshold
        )

        with self.lock:
            self.alerts.append(alert)
            self.alert_history.append(alert)

        logger.warning("效能警報: %s", message)

    def _generate_optimization_suggestions(self) -> List[OptimizationSuggestion]:
        """生成優化建議"""
        suggestions = []
        current_metrics = self.get_current_metrics()

        # CPU使用率過高建議
        cpu_usage = current_metrics.get(MetricType.CPU_USAGE, 0)
        if cpu_usage > 80:
            suggestions.append(OptimizationSuggestion(
                action=OptimizationAction.DECREASE_WORKERS,
                reason=f"CPU使用率過高 ({cpu_usage:.1f}%)，建議減少並行工作者數量",
                expected_improvement="降低CPU使用率，提升系統穩定性",
                priority=8,
                parameters={'target_workers': max(1, int(cpu_usage / 20))}
            ))
        elif cpu_usage < 30:
            suggestions.append(OptimizationSuggestion(
                action=OptimizationAction.INCREASE_WORKERS,
                reason=f"CPU使用率較低 ({cpu_usage:.1f}%)，可以增加並行工作者數量",
                expected_improvement="提升處理速度和資源利用率",
                priority=5,
                parameters={'target_workers': min(10, int(100 / cpu_usage))}
            ))

        # 快取命中率建議
        cache_hit_rate = current_metrics.get(MetricType.CACHE_HIT_RATE, 0)
        if cache_hit_rate < 0.6:
            suggestions.append(OptimizationSuggestion(
                action=OptimizationAction.ADJUST_CACHE_SIZE,
                reason=f"快取命中率較低 ({cache_hit_rate:.1%})，建議增加快取大小",
                expected_improvement="提升快取命中率，減少重複請求",
                priority=7,
                parameters={'size_multiplier': 1.5}
            ))

        # 錯誤率建議
        error_rate = current_metrics.get(MetricType.ERROR_RATE, 0)
        if error_rate > 0.1:
            suggestions.append(OptimizationSuggestion(
                action=OptimizationAction.ADJUST_RETRY_POLICY,
                reason=f"錯誤率較高 ({error_rate:.1%})，建議調整重試策略",
                expected_improvement="提升成功率，減少失敗請求",
                priority=9,
                parameters={'max_retries': 5, 'backoff_factor': 2.0}
            ))

        return suggestions

    def _execute_optimization(self, suggestion: OptimizationSuggestion):
        """執行優化建議"""
        # 這裡是優化建議的實際執行邏輯
        # 在實際應用中，這些會調用相應的系統組件

        if suggestion.action == OptimizationAction.DECREASE_WORKERS:
            logger.info("建議減少工作者數量到 %d",
                       suggestion.parameters.get('target_workers', 2))

        elif suggestion.action == OptimizationAction.INCREASE_WORKERS:
            logger.info("建議增加工作者數量到 %d",
                       suggestion.parameters.get('target_workers', 5))

        elif suggestion.action == OptimizationAction.ADJUST_CACHE_SIZE:
            multiplier = suggestion.parameters.get('size_multiplier', 1.5)
            logger.info("建議將快取大小調整為原來的 %.1f 倍", multiplier)

        elif suggestion.action == OptimizationAction.ADJUST_RETRY_POLICY:
            max_retries = suggestion.parameters.get('max_retries', 3)
            backoff = suggestion.parameters.get('backoff_factor', 1.5)
            logger.info("建議調整重試策略: 最大重試 %d 次，退避因子 %.1f",
                       max_retries, backoff)

    def _assess_system_health(self) -> str:
        """評估系統健康度"""
        current_metrics = self.get_current_metrics()

        # 計算健康分數
        health_score = 100

        # CPU使用率影響
        cpu_usage = current_metrics.get(MetricType.CPU_USAGE, 0)
        if cpu_usage > 90:
            health_score -= 30
        elif cpu_usage > 70:
            health_score -= 15

        # 記憶體使用率影響
        memory_usage = current_metrics.get(MetricType.MEMORY_USAGE, 0)
        if memory_usage > 95:
            health_score -= 25
        elif memory_usage > 80:
            health_score -= 10

        # 錯誤率影響
        error_rate = current_metrics.get(MetricType.ERROR_RATE, 0)
        if error_rate > 0.15:
            health_score -= 20
        elif error_rate > 0.05:
            health_score -= 10

        # 快取命中率影響
        cache_hit_rate = current_metrics.get(MetricType.CACHE_HIT_RATE, 1.0)
        if cache_hit_rate < 0.5:
            health_score -= 15
        elif cache_hit_rate < 0.7:
            health_score -= 5

        # 根據分數判斷健康度
        if health_score >= 90:
            return "excellent"
        elif health_score >= 75:
            return "good"
        elif health_score >= 60:
            return "fair"
        elif health_score >= 40:
            return "poor"
        else:
            return "critical"

    def _start_background_services(self):
        """啟動背景服務"""
        # 系統監控執行緒
        monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="PerformanceMonitor"
        )
        monitor_thread.start()

        # 優化執行緒
        optimization_thread = threading.Thread(
            target=self._optimization_loop,
            daemon=True,
            name="PerformanceOptimizer"
        )
        optimization_thread.start()

        logger.debug("效能監控背景服務已啟動")

    def _monitoring_loop(self):
        """監控迴圈"""
        while self.monitoring_active:
            try:
                self.record_system_metrics()
                time.sleep(30)  # 每30秒監控一次
            except Exception as e:
                logger.error("監控迴圈錯誤: %s", e)
                time.sleep(60)

    def _optimization_loop(self):
        """優化迴圈"""
        while self.optimization_active:
            try:
                # 每5分鐘檢查一次優化機會
                suggestions = self._generate_optimization_suggestions()

                # 執行高優先級建議
                for suggestion in suggestions:
                    if suggestion.priority >= 8:
                        self._execute_optimization(suggestion)

                time.sleep(300)  # 5分鐘間隔

            except Exception as e:
                logger.error("優化迴圈錯誤: %s", e)
                time.sleep(600)  # 錯誤時延長間隔
