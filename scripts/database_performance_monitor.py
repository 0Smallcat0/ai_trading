#!/usr/bin/env python3
"""
AI 交易系統資料庫性能監控器
版本: v1.0
最後更新: 2024-12-25

此腳本實現資料庫性能監控，包括：
- 連接池監控
- 慢查詢檢測
- 資源使用監控
- 性能指標收集
- 自動優化建議
"""

import os
import sys
import time
import psutil
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import yaml

# 添加項目根目錄到 Python 路徑
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.database_manager import DatabaseManager
from src.monitoring.intelligent_alert_manager import IntelligentAlertManager

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/ai_trading/db_performance.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DatabasePerformanceMonitor:
    """資料庫性能監控器"""
    
    def __init__(self, config_path: str = "config/database_production.yaml"):
        """初始化性能監控器
        
        Args:
            config_path: 配置文件路徑
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.db_manager = DatabaseManager()
        self.alert_manager = IntelligentAlertManager()
        
        # 監控狀態
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 性能指標
        self.metrics = {
            "connection_pool": {},
            "query_performance": {},
            "resource_usage": {},
            "slow_queries": [],
            "alerts": [],
        }
        
        # 監控配置
        self.monitor_config = self.config.get("monitoring", {})
        self.performance_config = self.monitor_config.get("performance", {})
        
        logger.info("資料庫性能監控器初始化完成")
    
    def _load_config(self) -> Dict[str, Any]:
        """載入配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"配置文件載入成功: {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"載入配置文件失敗: {e}")
            return {}
    
    def start_monitoring(self) -> None:
        """啟動性能監控"""
        if self.is_monitoring:
            logger.warning("性能監控已在運行中")
            return
        
        try:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            
            logger.info("資料庫性能監控已啟動")
            
        except Exception as e:
            logger.error(f"啟動性能監控失敗: {e}")
            self.is_monitoring = False
            raise
    
    def stop_monitoring(self) -> None:
        """停止性能監控"""
        if not self.is_monitoring:
            logger.warning("性能監控未在運行")
            return
        
        try:
            self.is_monitoring = False
            self._stop_event.set()
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=30)
            
            logger.info("資料庫性能監控已停止")
            
        except Exception as e:
            logger.error(f"停止性能監控失敗: {e}")
    
    def _monitor_loop(self) -> None:
        """監控主循環"""
        logger.info("性能監控主循環已啟動")
        
        interval = self.performance_config.get("metrics_collection_interval", 60)
        
        while self.is_monitoring and not self._stop_event.is_set():
            try:
                # 收集性能指標
                self._collect_connection_pool_metrics()
                self._collect_query_performance_metrics()
                self._collect_resource_usage_metrics()
                self._detect_slow_queries()
                
                # 檢查告警條件
                self._check_alert_conditions()
                
                # 生成優化建議
                self._generate_optimization_suggestions()
                
                # 等待下次收集
                self._stop_event.wait(interval)
                
            except Exception as e:
                logger.error(f"性能監控循環錯誤: {e}")
                self._stop_event.wait(interval)
        
        logger.info("性能監控主循環已停止")
    
    def _collect_connection_pool_metrics(self) -> None:
        """收集連接池指標"""
        try:
            # 模擬連接池指標收集
            # 在實際實現中，這裡應該從資料庫管理器獲取真實指標
            
            pool_metrics = {
                "timestamp": datetime.now().isoformat(),
                "total_connections": 20,
                "active_connections": 8,
                "idle_connections": 12,
                "pool_usage_percent": 40.0,
                "connection_wait_time": 0.05,  # 秒
                "connection_errors": 0,
            }
            
            self.metrics["connection_pool"] = pool_metrics
            
            # 檢查連接池使用率
            usage_threshold = self.monitor_config.get("alerts", {}).get("connection_pool_usage", 80)
            if pool_metrics["pool_usage_percent"] > usage_threshold:
                self._add_alert("high_connection_pool_usage", pool_metrics)
            
        except Exception as e:
            logger.error(f"收集連接池指標失敗: {e}")
    
    def _collect_query_performance_metrics(self) -> None:
        """收集查詢性能指標"""
        try:
            # 模擬查詢性能指標
            query_metrics = {
                "timestamp": datetime.now().isoformat(),
                "total_queries": 1250,
                "queries_per_second": 20.8,
                "average_query_time": 0.15,  # 秒
                "slow_query_count": 2,
                "cache_hit_ratio": 95.5,  # %
                "index_usage_ratio": 88.2,  # %
            }
            
            self.metrics["query_performance"] = query_metrics
            
            # 檢查慢查詢數量
            slow_query_threshold = self.monitor_config.get("alerts", {}).get("slow_query_count", 10)
            if query_metrics["slow_query_count"] > slow_query_threshold:
                self._add_alert("high_slow_query_count", query_metrics)
            
        except Exception as e:
            logger.error(f"收集查詢性能指標失敗: {e}")
    
    def _collect_resource_usage_metrics(self) -> None:
        """收集資源使用指標"""
        try:
            # 獲取系統資源使用情況
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            resource_metrics = {
                "timestamp": datetime.now().isoformat(),
                "cpu_usage_percent": cpu_percent,
                "memory_usage_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_usage_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3),
            }
            
            self.metrics["resource_usage"] = resource_metrics
            
            # 檢查磁碟使用率
            disk_threshold = self.monitor_config.get("alerts", {}).get("disk_usage", 85)
            if resource_metrics["disk_usage_percent"] > disk_threshold:
                self._add_alert("high_disk_usage", resource_metrics)
            
        except Exception as e:
            logger.error(f"收集資源使用指標失敗: {e}")
    
    def _detect_slow_queries(self) -> None:
        """檢測慢查詢"""
        try:
            # 模擬慢查詢檢測
            # 在實際實現中，這裡應該查詢資料庫的慢查詢日誌
            
            slow_query_threshold = self.performance_config.get("slow_query_threshold", 5000)  # 毫秒
            
            # 模擬發現的慢查詢
            slow_queries = [
                {
                    "query_id": "q001",
                    "query": "SELECT * FROM market_data WHERE date > '2024-01-01'",
                    "execution_time": 6500,  # 毫秒
                    "timestamp": datetime.now().isoformat(),
                    "database": "ai_trading_prod",
                    "user": "trading_app",
                },
            ]
            
            # 更新慢查詢列表（保留最近100條）
            self.metrics["slow_queries"].extend(slow_queries)
            self.metrics["slow_queries"] = self.metrics["slow_queries"][-100:]
            
            # 為每個慢查詢生成告警
            for query in slow_queries:
                if query["execution_time"] > slow_query_threshold:
                    self._add_alert("slow_query_detected", query)
            
        except Exception as e:
            logger.error(f"檢測慢查詢失敗: {e}")
    
    def _check_alert_conditions(self) -> None:
        """檢查告警條件"""
        try:
            alerts_config = self.monitor_config.get("alerts", {})
            
            # 檢查複製延遲（如果有複製配置）
            if "replica_database" in self.config:
                # 模擬複製延遲檢查
                replication_lag = 30  # 秒
                lag_threshold = alerts_config.get("replication_lag", 60)
                
                if replication_lag > lag_threshold:
                    self._add_alert("high_replication_lag", {
                        "lag_seconds": replication_lag,
                        "threshold": lag_threshold
                    })
            
        except Exception as e:
            logger.error(f"檢查告警條件失敗: {e}")
    
    def _generate_optimization_suggestions(self) -> None:
        """生成優化建議"""
        try:
            suggestions = []
            
            # 基於連接池使用率的建議
            pool_usage = self.metrics.get("connection_pool", {}).get("pool_usage_percent", 0)
            if pool_usage > 80:
                suggestions.append({
                    "type": "connection_pool",
                    "priority": "high",
                    "suggestion": "考慮增加連接池大小或優化連接使用",
                    "current_usage": f"{pool_usage}%"
                })
            
            # 基於慢查詢的建議
            slow_query_count = len(self.metrics.get("slow_queries", []))
            if slow_query_count > 5:
                suggestions.append({
                    "type": "query_optimization",
                    "priority": "medium",
                    "suggestion": "檢查並優化慢查詢，考慮添加索引",
                    "slow_query_count": slow_query_count
                })
            
            # 基於快取命中率的建議
            cache_hit_ratio = self.metrics.get("query_performance", {}).get("cache_hit_ratio", 100)
            if cache_hit_ratio < 90:
                suggestions.append({
                    "type": "cache_optimization",
                    "priority": "medium",
                    "suggestion": "考慮增加資料庫快取大小或優化查詢模式",
                    "current_hit_ratio": f"{cache_hit_ratio}%"
                })
            
            # 保存建議
            if suggestions:
                self.metrics["optimization_suggestions"] = {
                    "timestamp": datetime.now().isoformat(),
                    "suggestions": suggestions
                }
                
                logger.info(f"生成了 {len(suggestions)} 個優化建議")
            
        except Exception as e:
            logger.error(f"生成優化建議失敗: {e}")
    
    def _add_alert(self, alert_type: str, data: Dict[str, Any]) -> None:
        """添加告警"""
        alert = {
            "type": alert_type,
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "severity": self._get_alert_severity(alert_type),
        }
        
        self.metrics["alerts"].append(alert)
        
        # 保留最近50個告警
        self.metrics["alerts"] = self.metrics["alerts"][-50:]
        
        # 發送告警通知
        try:
            self.alert_manager.create_alert(
                title=f"資料庫性能告警: {alert_type}",
                message=f"檢測到資料庫性能問題: {json.dumps(data, indent=2)}",
                severity=alert["severity"],
                source="database_performance_monitor"
            )
        except Exception as e:
            logger.error(f"發送告警通知失敗: {e}")
        
        logger.warning(f"資料庫性能告警: {alert_type} - {data}")
    
    def _get_alert_severity(self, alert_type: str) -> str:
        """獲取告警嚴重程度"""
        severity_map = {
            "high_connection_pool_usage": "warning",
            "high_slow_query_count": "warning",
            "high_disk_usage": "critical",
            "slow_query_detected": "info",
            "high_replication_lag": "warning",
        }
        return severity_map.get(alert_type, "info")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """獲取性能報告"""
        return {
            "monitoring_status": self.is_monitoring,
            "last_update": datetime.now().isoformat(),
            "metrics": self.metrics,
            "config": {
                "collection_interval": self.performance_config.get("metrics_collection_interval", 60),
                "slow_query_threshold": self.performance_config.get("slow_query_threshold", 5000),
            }
        }
    
    def export_metrics(self, file_path: str) -> None:
        """導出指標到文件"""
        try:
            report = self.get_performance_report()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info(f"性能指標已導出到: {file_path}")
            
        except Exception as e:
            logger.error(f"導出指標失敗: {e}")


def main():
    """主函數"""
    try:
        # 創建性能監控器
        monitor = DatabasePerformanceMonitor()
        
        # 啟動監控
        monitor.start_monitoring()
        
        # 保持運行
        try:
            while True:
                time.sleep(60)
                
                # 每小時導出一次指標
                if datetime.now().minute == 0:
                    timestamp = datetime.now().strftime("%Y%m%d_%H")
                    monitor.export_metrics(f"/var/log/ai_trading/db_metrics_{timestamp}.json")
                    
        except KeyboardInterrupt:
            logger.info("收到中斷信號，正在停止監控...")
            monitor.stop_monitoring()
            
    except Exception as e:
        logger.error(f"性能監控器運行失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
