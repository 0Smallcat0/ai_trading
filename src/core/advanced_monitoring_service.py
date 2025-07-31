#!/usr/bin/env python3
"""
高級監控服務
實現詳細日誌記錄、性能監控、異常追蹤系統
"""

import logging
import os
import sys
import time
import psutil
import threading
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from collections import deque, defaultdict
from dataclasses import dataclass
from enum import Enum
import json

# 添加項目根目錄到路徑
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

class LogLevel(Enum):
    """日誌級別"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class AlertType(Enum):
    """警報類型"""
    PERFORMANCE = "performance"
    ERROR = "error"
    SECURITY = "security"
    RESOURCE = "resource"
    BUSINESS = "business"

@dataclass
class PerformanceMetric:
    """性能指標數據類"""
    timestamp: datetime
    metric_name: str
    value: float
    unit: str
    tags: Dict[str, str] = None

@dataclass
class LogEntry:
    """日誌條目數據類"""
    timestamp: datetime
    level: LogLevel
    module: str
    message: str
    context: Dict[str, Any] = None
    exception: str = None

@dataclass
class Alert:
    """警報數據類"""
    id: str
    timestamp: datetime
    type: AlertType
    severity: str
    title: str
    message: str
    source: str
    resolved: bool = False
    resolution_time: Optional[datetime] = None

class AdvancedMonitoringService:
    """高級監控服務"""
    
    def __init__(self, max_log_entries: int = 10000, max_metrics: int = 5000):
        """初始化監控服務"""
        self.max_log_entries = max_log_entries
        self.max_metrics = max_metrics
        
        # 數據存儲
        self.log_entries = deque(maxlen=max_log_entries)
        self.performance_metrics = defaultdict(lambda: deque(maxlen=max_metrics))
        self.alerts = {}
        self.alert_rules = {}
        
        # 監控狀態
        self.monitoring_active = False
        self.monitoring_thread = None
        self.last_health_check = None
        
        # 性能統計
        self.performance_stats = {
            "cpu_usage": deque(maxlen=100),
            "memory_usage": deque(maxlen=100),
            "disk_usage": deque(maxlen=100),
            "network_io": deque(maxlen=100)
        }
        
        # 異常追蹤
        self.exception_tracker = defaultdict(int)
        self.error_patterns = {}
        
        # 初始化日誌系統
        self._setup_logging()
        
        # 初始化警報規則
        self._setup_alert_rules()
        
        logger = logging.getLogger(__name__)
        logger.info("高級監控服務初始化完成")
    
    def _setup_logging(self):
        """設置日誌系統"""
        # 創建日誌目錄
        log_dir = os.path.join(project_root, "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        # 配置日誌格式
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # 創建文件處理器
        log_file = os.path.join(log_dir, f"monitoring_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format))
        
        # 創建控制台處理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(log_format))
        
        # 配置根日誌記錄器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        # 添加自定義處理器
        custom_handler = self.CustomLogHandler(self)
        custom_handler.setLevel(logging.WARNING)
        root_logger.addHandler(custom_handler)
    
    class CustomLogHandler(logging.Handler):
        """自定義日誌處理器"""
        
        def __init__(self, monitoring_service):
            super().__init__()
            self.monitoring_service = monitoring_service
        
        def emit(self, record):
            """處理日誌記錄"""
            try:
                log_entry = LogEntry(
                    timestamp=datetime.fromtimestamp(record.created),
                    level=LogLevel(record.levelname),
                    module=record.name,
                    message=record.getMessage(),
                    context=getattr(record, 'context', None),
                    exception=record.exc_text if record.exc_info else None
                )
                
                self.monitoring_service.add_log_entry(log_entry)
                
                # 檢查是否需要觸發警報
                if record.levelname in ['ERROR', 'CRITICAL']:
                    self.monitoring_service._check_error_patterns(log_entry)
                    
            except Exception:
                # 避免日誌處理器本身出錯
                pass
    
    def _setup_alert_rules(self):
        """設置警報規則"""
        self.alert_rules = {
            "high_cpu_usage": {
                "condition": lambda metrics: metrics.get("cpu_usage", 0) > 80,
                "type": AlertType.PERFORMANCE,
                "severity": "high",
                "title": "CPU使用率過高",
                "cooldown": 300  # 5分鐘冷卻期
            },
            "high_memory_usage": {
                "condition": lambda metrics: metrics.get("memory_usage", 0) > 85,
                "type": AlertType.RESOURCE,
                "severity": "high",
                "title": "內存使用率過高",
                "cooldown": 300
            },
            "disk_space_low": {
                "condition": lambda metrics: metrics.get("disk_usage", 0) > 90,
                "type": AlertType.RESOURCE,
                "severity": "critical",
                "title": "磁盤空間不足",
                "cooldown": 600
            },
            "frequent_errors": {
                "condition": lambda metrics: metrics.get("error_rate", 0) > 10,
                "type": AlertType.ERROR,
                "severity": "medium",
                "title": "錯誤率過高",
                "cooldown": 180
            }
        }
    
    def start_monitoring(self):
        """開始監控"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger = logging.getLogger(__name__)
        logger.info("監控服務已啟動")
    
    def stop_monitoring(self):
        """停止監控"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        logger = logging.getLogger(__name__)
        logger.info("監控服務已停止")
    
    def _monitoring_loop(self):
        """監控主循環"""
        while self.monitoring_active:
            try:
                # 收集系統性能指標
                self._collect_system_metrics()
                
                # 檢查警報條件
                self._check_alert_conditions()
                
                # 更新健康檢查
                self.last_health_check = datetime.now()
                
                # 等待下一次檢查
                time.sleep(10)  # 每10秒檢查一次
                
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"監控循環異常: {e}")
                time.sleep(30)  # 異常時等待更長時間
    
    def _collect_system_metrics(self):
        """收集系統性能指標"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            self.add_performance_metric("cpu_usage", cpu_percent, "%")
            self.performance_stats["cpu_usage"].append(cpu_percent)
            
            # 內存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            self.add_performance_metric("memory_usage", memory_percent, "%")
            self.performance_stats["memory_usage"].append(memory_percent)
            
            # 磁盤使用率
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.add_performance_metric("disk_usage", disk_percent, "%")
            self.performance_stats["disk_usage"].append(disk_percent)
            
            # 網絡IO
            network = psutil.net_io_counters()
            network_total = network.bytes_sent + network.bytes_recv
            self.add_performance_metric("network_io", network_total, "bytes")
            self.performance_stats["network_io"].append(network_total)
            
            # 進程數量
            process_count = len(psutil.pids())
            self.add_performance_metric("process_count", process_count, "count")
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"收集系統指標失敗: {e}")
    
    def add_log_entry(self, log_entry: LogEntry):
        """添加日誌條目"""
        self.log_entries.append(log_entry)
        
        # 更新異常統計
        if log_entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            self.exception_tracker[log_entry.module] += 1
    
    def add_performance_metric(self, metric_name: str, value: float, unit: str, tags: Dict[str, str] = None):
        """添加性能指標"""
        metric = PerformanceMetric(
            timestamp=datetime.now(),
            metric_name=metric_name,
            value=value,
            unit=unit,
            tags=tags or {}
        )
        
        self.performance_metrics[metric_name].append(metric)
    
    def _check_alert_conditions(self):
        """檢查警報條件"""
        current_metrics = self._get_current_metrics()
        
        for rule_name, rule in self.alert_rules.items():
            try:
                if rule["condition"](current_metrics):
                    self._trigger_alert(rule_name, rule, current_metrics)
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"檢查警報條件失敗 {rule_name}: {e}")
    
    def _get_current_metrics(self) -> Dict[str, float]:
        """獲取當前指標值"""
        metrics = {}
        
        # 系統性能指標
        if self.performance_stats["cpu_usage"]:
            metrics["cpu_usage"] = self.performance_stats["cpu_usage"][-1]
        
        if self.performance_stats["memory_usage"]:
            metrics["memory_usage"] = self.performance_stats["memory_usage"][-1]
        
        if self.performance_stats["disk_usage"]:
            metrics["disk_usage"] = self.performance_stats["disk_usage"][-1]
        
        # 錯誤率計算
        recent_logs = [log for log in list(self.log_entries)[-100:] 
                      if log.level in [LogLevel.ERROR, LogLevel.CRITICAL]]
        metrics["error_rate"] = len(recent_logs)
        
        return metrics
    
    def _trigger_alert(self, rule_name: str, rule: Dict[str, Any], metrics: Dict[str, float]):
        """觸發警報"""
        alert_id = f"{rule_name}_{int(time.time())}"
        
        # 檢查冷卻期
        if self._is_in_cooldown(rule_name, rule.get("cooldown", 300)):
            return
        
        alert = Alert(
            id=alert_id,
            timestamp=datetime.now(),
            type=rule["type"],
            severity=rule["severity"],
            title=rule["title"],
            message=self._generate_alert_message(rule_name, rule, metrics),
            source="monitoring_service"
        )
        
        self.alerts[alert_id] = alert
        
        logger = logging.getLogger(__name__)
        logger.warning(f"觸發警報: {alert.title} - {alert.message}")
    
    def _is_in_cooldown(self, rule_name: str, cooldown_seconds: int) -> bool:
        """檢查是否在冷卻期內"""
        now = datetime.now()
        
        for alert in self.alerts.values():
            if (alert.source == "monitoring_service" and 
                rule_name in alert.id and 
                not alert.resolved and
                (now - alert.timestamp).total_seconds() < cooldown_seconds):
                return True
        
        return False
    
    def _generate_alert_message(self, rule_name: str, rule: Dict[str, Any], metrics: Dict[str, float]) -> str:
        """生成警報消息"""
        if rule_name == "high_cpu_usage":
            return f"CPU使用率達到 {metrics.get('cpu_usage', 0):.1f}%，超過警戒線80%"
        elif rule_name == "high_memory_usage":
            return f"內存使用率達到 {metrics.get('memory_usage', 0):.1f}%，超過警戒線85%"
        elif rule_name == "disk_space_low":
            return f"磁盤使用率達到 {metrics.get('disk_usage', 0):.1f}%，超過警戒線90%"
        elif rule_name == "frequent_errors":
            return f"最近100條日誌中有 {metrics.get('error_rate', 0)} 條錯誤記錄"
        else:
            return f"監控規則 {rule_name} 被觸發"
    
    def _check_error_patterns(self, log_entry: LogEntry):
        """檢查錯誤模式"""
        # 簡化的錯誤模式檢測
        error_key = f"{log_entry.module}:{log_entry.message[:50]}"
        
        if error_key not in self.error_patterns:
            self.error_patterns[error_key] = {
                "count": 0,
                "first_seen": log_entry.timestamp,
                "last_seen": log_entry.timestamp
            }
        
        pattern = self.error_patterns[error_key]
        pattern["count"] += 1
        pattern["last_seen"] = log_entry.timestamp
        
        # 如果同一錯誤在短時間內重複出現多次，觸發警報
        if (pattern["count"] >= 5 and 
            (log_entry.timestamp - pattern["first_seen"]).total_seconds() < 300):
            
            alert_id = f"error_pattern_{hash(error_key)}_{int(time.time())}"
            
            alert = Alert(
                id=alert_id,
                timestamp=datetime.now(),
                type=AlertType.ERROR,
                severity="high",
                title="重複錯誤模式",
                message=f"錯誤 '{log_entry.message[:50]}...' 在5分鐘內重複出現{pattern['count']}次",
                source="error_pattern_detector"
            )
            
            self.alerts[alert_id] = alert
    
    def get_system_health(self) -> Dict[str, Any]:
        """獲取系統健康狀態"""
        current_metrics = self._get_current_metrics()
        
        # 計算健康分數
        health_score = 100
        
        if current_metrics.get("cpu_usage", 0) > 80:
            health_score -= 20
        elif current_metrics.get("cpu_usage", 0) > 60:
            health_score -= 10
        
        if current_metrics.get("memory_usage", 0) > 85:
            health_score -= 25
        elif current_metrics.get("memory_usage", 0) > 70:
            health_score -= 10
        
        if current_metrics.get("disk_usage", 0) > 90:
            health_score -= 30
        elif current_metrics.get("disk_usage", 0) > 80:
            health_score -= 15
        
        # 活躍警報影響健康分數
        active_alerts = [a for a in self.alerts.values() if not a.resolved]
        health_score -= len(active_alerts) * 5
        
        health_score = max(0, health_score)
        
        return {
            "health_score": health_score,
            "status": "healthy" if health_score >= 80 else "warning" if health_score >= 60 else "critical",
            "metrics": current_metrics,
            "active_alerts": len(active_alerts),
            "last_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "monitoring_active": self.monitoring_active
        }
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """獲取性能摘要"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        summary = {}
        
        for metric_name, metrics in self.performance_metrics.items():
            recent_metrics = [m for m in metrics if m.timestamp >= cutoff_time]
            
            if recent_metrics:
                values = [m.value for m in recent_metrics]
                summary[metric_name] = {
                    "current": values[-1] if values else 0,
                    "average": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values),
                    "unit": recent_metrics[0].unit
                }
        
        return summary
    
    def resolve_alert(self, alert_id: str) -> bool:
        """解決警報"""
        if alert_id in self.alerts:
            self.alerts[alert_id].resolved = True
            self.alerts[alert_id].resolution_time = datetime.now()
            
            logger = logging.getLogger(__name__)
            logger.info(f"警報已解決: {alert_id}")
            return True
        
        return False
    
    def get_log_entries(self, level: Optional[LogLevel] = None, 
                       module: Optional[str] = None, 
                       limit: int = 100) -> List[LogEntry]:
        """獲取日誌條目"""
        entries = list(self.log_entries)
        
        # 過濾條件
        if level:
            entries = [e for e in entries if e.level == level]
        
        if module:
            entries = [e for e in entries if module in e.module]
        
        # 按時間倒序排列
        entries.sort(key=lambda x: x.timestamp, reverse=True)
        
        return entries[:limit]
