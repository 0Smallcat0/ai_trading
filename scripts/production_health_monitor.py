#!/usr/bin/env python3
"""
AI 交易系統生產環境健康監控器
版本: v1.0
最後更新: 2024-12-25

此腳本實現生產環境健康監控，包括：
- 實時健康檢查
- 性能指標監控
- 自動告警機制
- 監控數據收集
- 健康報告生成
"""

import os
import sys
import time
import logging
import threading
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests
import psutil

# 添加項目根目錄到 Python 路徑
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.monitoring.health_checker import HealthChecker
from src.monitoring.service_checker import ServiceChecker
from src.monitoring.intelligent_alert_manager import IntelligentAlertManager

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/ai_trading/production_health.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ProductionHealthMonitor:
    """生產環境健康監控器"""
    
    def __init__(self, config_path: str = "config/monitoring_production.json"):
        """初始化健康監控器
        
        Args:
            config_path: 監控配置文件路徑
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # 初始化組件
        self.health_checker = HealthChecker()
        self.service_checker = ServiceChecker()
        self.alert_manager = IntelligentAlertManager()
        
        # 監控配置
        self.check_interval = self.config.get("health_checks", {}).get("interval", 30)
        self.alert_thresholds = self.config.get("alert_thresholds", {})
        
        # 監控狀態
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 健康數據
        self.health_history = []
        self.performance_metrics = {}
        self.alert_history = []
        
        # 服務端點配置
        self.service_endpoints = {
            "web_ui": "http://localhost:8501/health",
            "api_server": "http://localhost:8000/health",
            "prometheus": "http://localhost:9090/-/healthy",
            "grafana": "http://localhost:3000/api/health",
        }
        
        logger.info("生產環境健康監控器初始化完成")
    
    def _load_config(self) -> Dict[str, Any]:
        """載入配置文件"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"配置文件載入成功: {self.config_path}")
                return config
            else:
                logger.warning(f"配置文件不存在，使用預設配置: {self.config_path}")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"載入配置文件失敗: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """獲取預設配置"""
        return {
            "health_checks": {
                "interval": 30,
                "timeout": 10,
                "enabled": True
            },
            "alert_thresholds": {
                "cpu_usage": 80,
                "memory_usage": 85,
                "disk_usage": 90,
                "response_time": 5000,
                "error_rate": 5
            },
            "performance_monitoring": {
                "enabled": True,
                "metrics_retention_hours": 24
            }
        }
    
    def start_monitoring(self) -> None:
        """啟動健康監控"""
        if self.is_monitoring:
            logger.warning("健康監控已在運行中")
            return
        
        try:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            
            logger.info("生產環境健康監控已啟動")
            
        except Exception as e:
            logger.error(f"啟動健康監控失敗: {e}")
            self.is_monitoring = False
            raise
    
    def stop_monitoring(self) -> None:
        """停止健康監控"""
        if not self.is_monitoring:
            logger.warning("健康監控未在運行")
            return
        
        try:
            self.is_monitoring = False
            self._stop_event.set()
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=30)
            
            logger.info("生產環境健康監控已停止")
            
        except Exception as e:
            logger.error(f"停止健康監控失敗: {e}")
    
    def _monitor_loop(self) -> None:
        """監控主循環"""
        logger.info("健康監控主循環已啟動")
        
        while self.is_monitoring and not self._stop_event.is_set():
            try:
                # 執行健康檢查
                health_status = self._perform_comprehensive_health_check()
                
                # 收集性能指標
                performance_data = self._collect_performance_metrics()
                
                # 檢查告警條件
                self._check_alert_conditions(health_status, performance_data)
                
                # 保存監控數據
                self._save_monitoring_data(health_status, performance_data)
                
                # 等待下次檢查
                self._stop_event.wait(self.check_interval)
                
            except Exception as e:
                logger.error(f"健康監控循環錯誤: {e}")
                self._stop_event.wait(self.check_interval)
        
        logger.info("健康監控主循環已停止")
    
    def _perform_comprehensive_health_check(self) -> Dict[str, Any]:
        """執行綜合健康檢查"""
        try:
            health_status = {
                "timestamp": datetime.now().isoformat(),
                "overall_healthy": True,
                "services": {},
                "endpoints": {},
                "system": {},
            }
            
            # 1. 檢查核心服務
            service_results = self.health_checker.run_all_checks()
            for service_name, result in service_results.items():
                is_healthy = hasattr(result, 'status') and result.status.value == "healthy"
                health_status["services"][service_name] = {
                    "healthy": is_healthy,
                    "status": result.status.value if hasattr(result, 'status') else "unknown",
                    "message": result.message if hasattr(result, 'message') else "",
                    "duration": result.duration if hasattr(result, 'duration') else 0,
                }
                
                if not is_healthy:
                    health_status["overall_healthy"] = False
            
            # 2. 檢查服務端點
            for endpoint_name, url in self.service_endpoints.items():
                endpoint_health = self._check_endpoint_health(url)
                health_status["endpoints"][endpoint_name] = endpoint_health
                
                if not endpoint_health["healthy"]:
                    health_status["overall_healthy"] = False
            
            # 3. 檢查系統資源
            system_health = self._check_system_resources()
            health_status["system"] = system_health
            
            if not system_health["healthy"]:
                health_status["overall_healthy"] = False
            
            return health_status
            
        except Exception as e:
            logger.error(f"執行綜合健康檢查失敗: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "overall_healthy": False,
                "error": str(e),
            }
    
    def _check_endpoint_health(self, url: str) -> Dict[str, Any]:
        """檢查端點健康狀態"""
        try:
            start_time = time.time()
            response = requests.get(url, timeout=10)
            response_time = (time.time() - start_time) * 1000  # 毫秒
            
            is_healthy = response.status_code == 200
            
            return {
                "healthy": is_healthy,
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "url": url,
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "url": url,
            }
    
    def _check_system_resources(self) -> Dict[str, Any]:
        """檢查系統資源"""
        try:
            # CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 記憶體使用率
            memory = psutil.virtual_memory()
            
            # 磁碟使用率
            disk = psutil.disk_usage('/')
            
            # 網路統計
            network = psutil.net_io_counters()
            
            # 進程數量
            process_count = len(psutil.pids())
            
            # 判斷系統是否健康
            cpu_threshold = self.alert_thresholds.get("cpu_usage", 80)
            memory_threshold = self.alert_thresholds.get("memory_usage", 85)
            disk_threshold = self.alert_thresholds.get("disk_usage", 90)
            
            is_healthy = (
                cpu_percent < cpu_threshold and
                memory.percent < memory_threshold and
                disk.percent < disk_threshold
            )
            
            return {
                "healthy": is_healthy,
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3),
                "network_bytes_sent": network.bytes_sent,
                "network_bytes_recv": network.bytes_recv,
                "process_count": process_count,
                "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None,
            }
            
        except Exception as e:
            logger.error(f"檢查系統資源失敗: {e}")
            return {
                "healthy": False,
                "error": str(e),
            }
    
    def _collect_performance_metrics(self) -> Dict[str, Any]:
        """收集性能指標"""
        try:
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "application": {},
                "database": {},
                "cache": {},
            }
            
            # 應用程式指標
            metrics["application"] = self._collect_application_metrics()
            
            # 資料庫指標
            metrics["database"] = self._collect_database_metrics()
            
            # 快取指標
            metrics["cache"] = self._collect_cache_metrics()
            
            return metrics
            
        except Exception as e:
            logger.error(f"收集性能指標失敗: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            }
    
    def _collect_application_metrics(self) -> Dict[str, Any]:
        """收集應用程式指標"""
        try:
            # 這裡應該從應用程式獲取實際指標
            # 例如：請求數量、響應時間、錯誤率等
            
            return {
                "requests_per_second": 25.5,
                "average_response_time_ms": 150,
                "error_rate_percent": 0.5,
                "active_connections": 45,
            }
            
        except Exception as e:
            logger.error(f"收集應用程式指標失敗: {e}")
            return {}
    
    def _collect_database_metrics(self) -> Dict[str, Any]:
        """收集資料庫指標"""
        try:
            # 這裡應該從資料庫獲取實際指標
            # 例如：連接數、查詢時間、鎖等待等
            
            return {
                "active_connections": 12,
                "max_connections": 100,
                "average_query_time_ms": 25,
                "slow_queries_count": 2,
                "cache_hit_ratio_percent": 95.5,
            }
            
        except Exception as e:
            logger.error(f"收集資料庫指標失敗: {e}")
            return {}
    
    def _collect_cache_metrics(self) -> Dict[str, Any]:
        """收集快取指標"""
        try:
            # 這裡應該從 Redis 等快取系統獲取實際指標
            
            return {
                "hit_ratio_percent": 88.5,
                "memory_usage_mb": 256,
                "connected_clients": 8,
                "operations_per_second": 150,
            }
            
        except Exception as e:
            logger.error(f"收集快取指標失敗: {e}")
            return {}
    
    def _check_alert_conditions(self, health_status: Dict[str, Any], performance_data: Dict[str, Any]) -> None:
        """檢查告警條件"""
        try:
            alerts = []
            
            # 檢查整體健康狀態
            if not health_status.get("overall_healthy", True):
                alerts.append({
                    "type": "system_unhealthy",
                    "severity": "critical",
                    "message": "系統整體健康狀態異常",
                    "data": health_status,
                })
            
            # 檢查系統資源
            system_data = health_status.get("system", {})
            
            cpu_usage = system_data.get("cpu_percent", 0)
            if cpu_usage > self.alert_thresholds.get("cpu_usage", 80):
                alerts.append({
                    "type": "high_cpu_usage",
                    "severity": "warning",
                    "message": f"CPU 使用率過高: {cpu_usage}%",
                    "data": {"cpu_usage": cpu_usage},
                })
            
            memory_usage = system_data.get("memory_percent", 0)
            if memory_usage > self.alert_thresholds.get("memory_usage", 85):
                alerts.append({
                    "type": "high_memory_usage",
                    "severity": "warning",
                    "message": f"記憶體使用率過高: {memory_usage}%",
                    "data": {"memory_usage": memory_usage},
                })
            
            disk_usage = system_data.get("disk_percent", 0)
            if disk_usage > self.alert_thresholds.get("disk_usage", 90):
                alerts.append({
                    "type": "high_disk_usage",
                    "severity": "critical",
                    "message": f"磁碟使用率過高: {disk_usage}%",
                    "data": {"disk_usage": disk_usage},
                })
            
            # 檢查應用程式性能
            app_metrics = performance_data.get("application", {})
            
            response_time = app_metrics.get("average_response_time_ms", 0)
            if response_time > self.alert_thresholds.get("response_time", 5000):
                alerts.append({
                    "type": "slow_response_time",
                    "severity": "warning",
                    "message": f"響應時間過慢: {response_time}ms",
                    "data": {"response_time": response_time},
                })
            
            error_rate = app_metrics.get("error_rate_percent", 0)
            if error_rate > self.alert_thresholds.get("error_rate", 5):
                alerts.append({
                    "type": "high_error_rate",
                    "severity": "critical",
                    "message": f"錯誤率過高: {error_rate}%",
                    "data": {"error_rate": error_rate},
                })
            
            # 發送告警
            for alert in alerts:
                self._send_alert(alert)
            
        except Exception as e:
            logger.error(f"檢查告警條件失敗: {e}")
    
    def _send_alert(self, alert: Dict[str, Any]) -> None:
        """發送告警"""
        try:
            self.alert_manager.create_alert(
                title=f"生產環境告警: {alert['type']}",
                message=alert["message"],
                severity=alert["severity"],
                source="production_health_monitor"
            )
            
            # 記錄告警歷史
            alert["timestamp"] = datetime.now().isoformat()
            self.alert_history.append(alert)
            
            # 保留最近100個告警
            self.alert_history = self.alert_history[-100:]
            
            logger.warning(f"發送告警: {alert['type']} - {alert['message']}")
            
        except Exception as e:
            logger.error(f"發送告警失敗: {e}")
    
    def _save_monitoring_data(self, health_status: Dict[str, Any], performance_data: Dict[str, Any]) -> None:
        """保存監控數據"""
        try:
            monitoring_record = {
                "timestamp": datetime.now().isoformat(),
                "health_status": health_status,
                "performance_data": performance_data,
            }
            
            # 添加到歷史記錄
            self.health_history.append(monitoring_record)
            
            # 保留最近24小時的數據
            retention_hours = self.config.get("performance_monitoring", {}).get("metrics_retention_hours", 24)
            cutoff_time = datetime.now() - timedelta(hours=retention_hours)
            
            self.health_history = [
                record for record in self.health_history
                if datetime.fromisoformat(record["timestamp"]) > cutoff_time
            ]
            
            # 保存到文件
            self._export_monitoring_data()
            
        except Exception as e:
            logger.error(f"保存監控數據失敗: {e}")
    
    def _export_monitoring_data(self) -> None:
        """導出監控數據"""
        try:
            # 每小時導出一次數據
            now = datetime.now()
            if now.minute == 0:
                timestamp = now.strftime("%Y%m%d_%H")
                export_file = f"/var/log/ai_trading/health_monitoring_{timestamp}.json"
                
                export_data = {
                    "export_timestamp": now.isoformat(),
                    "health_history": self.health_history[-60:],  # 最近60條記錄
                    "alert_history": self.alert_history[-20:],    # 最近20個告警
                    "summary": self._generate_health_summary(),
                }
                
                os.makedirs(os.path.dirname(export_file), exist_ok=True)
                with open(export_file, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"監控數據已導出: {export_file}")
            
        except Exception as e:
            logger.error(f"導出監控數據失敗: {e}")
    
    def _generate_health_summary(self) -> Dict[str, Any]:
        """生成健康摘要"""
        try:
            if not self.health_history:
                return {}
            
            recent_records = self.health_history[-60:]  # 最近60條記錄
            
            # 計算健康率
            healthy_count = sum(1 for record in recent_records if record["health_status"].get("overall_healthy", False))
            health_rate = (healthy_count / len(recent_records)) * 100 if recent_records else 0
            
            # 計算平均響應時間
            response_times = []
            for record in recent_records:
                app_metrics = record.get("performance_data", {}).get("application", {})
                if "average_response_time_ms" in app_metrics:
                    response_times.append(app_metrics["average_response_time_ms"])
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            # 計算資源使用率
            cpu_usages = []
            memory_usages = []
            for record in recent_records:
                system_data = record["health_status"].get("system", {})
                if "cpu_percent" in system_data:
                    cpu_usages.append(system_data["cpu_percent"])
                if "memory_percent" in system_data:
                    memory_usages.append(system_data["memory_percent"])
            
            avg_cpu_usage = sum(cpu_usages) / len(cpu_usages) if cpu_usages else 0
            avg_memory_usage = sum(memory_usages) / len(memory_usages) if memory_usages else 0
            
            return {
                "health_rate_percent": round(health_rate, 2),
                "average_response_time_ms": round(avg_response_time, 2),
                "average_cpu_usage_percent": round(avg_cpu_usage, 2),
                "average_memory_usage_percent": round(avg_memory_usage, 2),
                "total_alerts": len(self.alert_history),
                "monitoring_period_hours": len(recent_records) * (self.check_interval / 3600),
            }
            
        except Exception as e:
            logger.error(f"生成健康摘要失敗: {e}")
            return {}
    
    def get_current_status(self) -> Dict[str, Any]:
        """獲取當前狀態"""
        return {
            "monitoring_active": self.is_monitoring,
            "last_check": self.health_history[-1]["timestamp"] if self.health_history else None,
            "health_summary": self._generate_health_summary(),
            "recent_alerts": self.alert_history[-5:],
            "config": self.config,
        }


def main():
    """主函數"""
    try:
        # 創建健康監控器
        monitor = ProductionHealthMonitor()
        
        # 啟動監控
        monitor.start_monitoring()
        
        # 保持運行
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("收到中斷信號，正在停止健康監控...")
            monitor.stop_monitoring()
            
    except Exception as e:
        logger.error(f"健康監控器運行失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
