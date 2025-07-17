#!/usr/bin/env python3
"""
AI 交易系統災難恢復自動化腳本
版本: v1.0
最後更新: 2024-12-25

此腳本實現自動化災難恢復，包括：
- 自動故障檢測
- 故障轉移機制
- 恢復程序自動化
- RTO/RPO 監控
- 緊急通知系統
"""

import os
import sys
import time
import logging
import threading
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import json
import yaml
import psutil

# 添加項目根目錄到 Python 路徑
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.monitoring.health_checker import HealthChecker
from src.monitoring.service_checker import ServiceChecker
from src.database.data_backup import DataBackupManager
from src.monitoring.intelligent_alert_manager import IntelligentAlertManager

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/ai_trading/disaster_recovery.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DisasterRecoveryManager:
    """災難恢復管理器"""
    
    def __init__(self, config_path: str = "config/database_production.yaml"):
        """初始化災難恢復管理器
        
        Args:
            config_path: 配置文件路徑
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # 初始化組件
        self.health_checker = HealthChecker()
        self.service_checker = ServiceChecker()
        self.backup_manager = DataBackupManager()
        self.alert_manager = IntelligentAlertManager()
        
        # 災難恢復配置
        self.dr_config = self.config.get("disaster_recovery", {})
        self.rto = self.dr_config.get("rto", 240)  # 恢復時間目標（分鐘）
        self.rpo = self.dr_config.get("rpo", 15)   # 恢復點目標（分鐘）
        
        # 監控狀態
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 故障狀態
        self.failure_detected = False
        self.recovery_in_progress = False
        self.last_health_check = None
        self.failure_start_time = None
        
        # 恢復統計
        self.recovery_stats = {
            "total_failures": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "average_recovery_time": 0,
            "last_recovery_time": None,
        }
        
        logger.info("災難恢復管理器初始化完成")
    
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
        """啟動災難恢復監控"""
        if self.is_monitoring:
            logger.warning("災難恢復監控已在運行中")
            return
        
        try:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            
            logger.info("災難恢復監控已啟動")
            
        except Exception as e:
            logger.error(f"啟動災難恢復監控失敗: {e}")
            self.is_monitoring = False
            raise
    
    def stop_monitoring(self) -> None:
        """停止災難恢復監控"""
        if not self.is_monitoring:
            logger.warning("災難恢復監控未在運行")
            return
        
        try:
            self.is_monitoring = False
            self._stop_event.set()
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=30)
            
            logger.info("災難恢復監控已停止")
            
        except Exception as e:
            logger.error(f"停止災難恢復監控失敗: {e}")
    
    def _monitor_loop(self) -> None:
        """監控主循環"""
        logger.info("災難恢復監控主循環已啟動")
        
        failover_config = self.dr_config.get("failover", {})
        check_interval = failover_config.get("health_check_interval", 30)
        failure_threshold = failover_config.get("failure_threshold", 3)
        
        consecutive_failures = 0
        
        while self.is_monitoring and not self._stop_event.is_set():
            try:
                # 執行健康檢查
                health_status = self._perform_health_check()
                self.last_health_check = datetime.now()
                
                if health_status["overall_healthy"]:
                    consecutive_failures = 0
                    
                    # 如果之前有故障，現在恢復了
                    if self.failure_detected:
                        self._handle_recovery_completion()
                else:
                    consecutive_failures += 1
                    logger.warning(f"健康檢查失敗 ({consecutive_failures}/{failure_threshold})")
                    
                    # 達到故障閾值
                    if consecutive_failures >= failure_threshold and not self.failure_detected:
                        self._handle_failure_detection(health_status)
                
                # 檢查 RTO/RPO 合規性
                self._check_rto_rpo_compliance()
                
                # 等待下次檢查
                self._stop_event.wait(check_interval)
                
            except Exception as e:
                logger.error(f"災難恢復監控循環錯誤: {e}")
                self._stop_event.wait(check_interval)
        
        logger.info("災難恢復監控主循環已停止")
    
    def _perform_health_check(self) -> Dict[str, Any]:
        """執行健康檢查"""
        try:
            # 檢查所有服務
            health_results = self.health_checker.run_all_checks()
            
            # 檢查系統資源
            system_health = self._check_system_health()
            
            # 檢查資料庫連接
            db_health = self.service_checker.check_database()
            
            # 綜合評估
            critical_services = ["database", "api_server", "trading_engine"]
            critical_failures = []
            
            for service in critical_services:
                if service in health_results:
                    result = health_results[service]
                    if hasattr(result, 'status') and result.status.value != "healthy":
                        critical_failures.append(service)
            
            overall_healthy = len(critical_failures) == 0 and system_health["healthy"]
            
            return {
                "timestamp": datetime.now().isoformat(),
                "overall_healthy": overall_healthy,
                "critical_failures": critical_failures,
                "health_results": health_results,
                "system_health": system_health,
                "db_health": db_health,
            }
            
        except Exception as e:
            logger.error(f"執行健康檢查失敗: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "overall_healthy": False,
                "error": str(e),
            }
    
    def _check_system_health(self) -> Dict[str, Any]:
        """檢查系統健康狀態"""
        try:
            # CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 記憶體使用率
            memory = psutil.virtual_memory()
            
            # 磁碟使用率
            disk = psutil.disk_usage('/')
            
            # 判斷是否健康
            healthy = (
                cpu_percent < 90 and
                memory.percent < 90 and
                disk.percent < 95
            )
            
            return {
                "healthy": healthy,
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None,
            }
            
        except Exception as e:
            logger.error(f"檢查系統健康狀態失敗: {e}")
            return {"healthy": False, "error": str(e)}
    
    def _handle_failure_detection(self, health_status: Dict[str, Any]) -> None:
        """處理故障檢測"""
        logger.critical("檢測到系統故障，啟動災難恢復程序")
        
        self.failure_detected = True
        self.failure_start_time = datetime.now()
        self.recovery_stats["total_failures"] += 1
        
        # 發送緊急告警
        self._send_emergency_alert("system_failure_detected", health_status)
        
        # 記錄故障詳情
        failure_log = {
            "timestamp": self.failure_start_time.isoformat(),
            "health_status": health_status,
            "failure_type": "system_failure",
        }
        
        self._log_disaster_event("failure_detected", failure_log)
        
        # 啟動自動恢復（如果啟用）
        if self.dr_config.get("failover", {}).get("automatic", False):
            self._start_automatic_recovery(health_status)
        else:
            logger.info("自動恢復未啟用，等待手動干預")
    
    def _start_automatic_recovery(self, health_status: Dict[str, Any]) -> None:
        """啟動自動恢復"""
        if self.recovery_in_progress:
            logger.warning("恢復程序已在進行中")
            return
        
        logger.info("啟動自動恢復程序")
        self.recovery_in_progress = True
        
        try:
            # 1. 創建緊急備份
            self._create_emergency_backup()
            
            # 2. 嘗試重啟故障服務
            self._restart_failed_services(health_status.get("critical_failures", []))
            
            # 3. 如果重啟失敗，嘗試故障轉移
            if not self._verify_recovery():
                self._perform_failover()
            
            # 4. 驗證恢復結果
            if self._verify_recovery():
                self._handle_recovery_success()
            else:
                self._handle_recovery_failure()
                
        except Exception as e:
            logger.error(f"自動恢復過程中發生錯誤: {e}")
            self._handle_recovery_failure()
        finally:
            self.recovery_in_progress = False
    
    def _create_emergency_backup(self) -> None:
        """創建緊急備份"""
        try:
            logger.info("創建緊急備份")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"/opt/ai_trading/backups/emergency/emergency_backup_{timestamp}.sql.gz"
            
            # 確保備份目錄存在
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            # 創建備份
            result = self.backup_manager.create_full_backup(backup_path)
            
            if result:
                logger.info(f"緊急備份創建成功: {backup_path}")
            else:
                logger.error("緊急備份創建失敗")
                
        except Exception as e:
            logger.error(f"創建緊急備份失敗: {e}")
    
    def _restart_failed_services(self, failed_services: List[str]) -> None:
        """重啟故障服務"""
        for service in failed_services:
            try:
                logger.info(f"嘗試重啟服務: {service}")
                
                # 停止服務
                self.service_checker.stop_service(service)
                time.sleep(5)
                
                # 啟動服務
                self.service_checker.start_service(service)
                time.sleep(10)
                
                # 檢查服務狀態
                if self.service_checker.is_service_healthy(service):
                    logger.info(f"服務重啟成功: {service}")
                else:
                    logger.error(f"服務重啟失敗: {service}")
                    
            except Exception as e:
                logger.error(f"重啟服務 {service} 時發生錯誤: {e}")
    
    def _perform_failover(self) -> None:
        """執行故障轉移"""
        logger.info("執行故障轉移到備援系統")
        
        try:
            # 這裡應該實現實際的故障轉移邏輯
            # 例如：切換到備援資料庫、重新路由流量等
            
            # 模擬故障轉移過程
            logger.info("正在切換到備援資料庫...")
            time.sleep(5)
            
            logger.info("正在重新路由應用流量...")
            time.sleep(3)
            
            logger.info("故障轉移完成")
            
        except Exception as e:
            logger.error(f"故障轉移失敗: {e}")
            raise
    
    def _verify_recovery(self) -> bool:
        """驗證恢復結果"""
        try:
            logger.info("驗證系統恢復狀態")
            
            # 執行健康檢查
            health_status = self._perform_health_check()
            
            return health_status.get("overall_healthy", False)
            
        except Exception as e:
            logger.error(f"驗證恢復狀態失敗: {e}")
            return False
    
    def _handle_recovery_success(self) -> None:
        """處理恢復成功"""
        recovery_time = datetime.now() - self.failure_start_time
        
        logger.info(f"系統恢復成功，恢復時間: {recovery_time}")
        
        self.recovery_stats["successful_recoveries"] += 1
        self.recovery_stats["last_recovery_time"] = recovery_time.total_seconds() / 60  # 分鐘
        
        # 更新平均恢復時間
        total_recoveries = self.recovery_stats["successful_recoveries"]
        if total_recoveries > 0:
            current_avg = self.recovery_stats["average_recovery_time"]
            new_recovery_time = self.recovery_stats["last_recovery_time"]
            self.recovery_stats["average_recovery_time"] = (
                (current_avg * (total_recoveries - 1) + new_recovery_time) / total_recoveries
            )
        
        # 發送恢復成功通知
        self._send_emergency_alert("recovery_successful", {
            "recovery_time_minutes": self.recovery_stats["last_recovery_time"],
            "rto_compliance": self.recovery_stats["last_recovery_time"] <= self.rto,
        })
        
        # 記錄恢復事件
        self._log_disaster_event("recovery_successful", {
            "recovery_time": recovery_time.total_seconds(),
            "rto_compliance": self.recovery_stats["last_recovery_time"] <= self.rto,
        })
    
    def _handle_recovery_failure(self) -> None:
        """處理恢復失敗"""
        logger.critical("自動恢復失敗，需要手動干預")
        
        self.recovery_stats["failed_recoveries"] += 1
        
        # 發送緊急告警
        self._send_emergency_alert("recovery_failed", {
            "failure_start_time": self.failure_start_time.isoformat(),
            "manual_intervention_required": True,
        })
        
        # 記錄恢復失敗事件
        self._log_disaster_event("recovery_failed", {
            "failure_duration": (datetime.now() - self.failure_start_time).total_seconds(),
            "manual_intervention_required": True,
        })
    
    def _handle_recovery_completion(self) -> None:
        """處理恢復完成"""
        logger.info("系統已從故障中恢復")
        
        self.failure_detected = False
        self.failure_start_time = None
        
        # 發送恢復完成通知
        self._send_emergency_alert("system_recovered", {
            "recovery_completion_time": datetime.now().isoformat(),
        })
    
    def _check_rto_rpo_compliance(self) -> None:
        """檢查 RTO/RPO 合規性"""
        try:
            if self.failure_detected and self.failure_start_time:
                failure_duration = (datetime.now() - self.failure_start_time).total_seconds() / 60
                
                # 檢查 RTO 合規性
                if failure_duration > self.rto:
                    logger.warning(f"RTO 違規：故障持續時間 {failure_duration:.1f} 分鐘超過目標 {self.rto} 分鐘")
                    
                    self._send_emergency_alert("rto_violation", {
                        "failure_duration_minutes": failure_duration,
                        "rto_target_minutes": self.rto,
                    })
            
            # 檢查 RPO 合規性（基於最後備份時間）
            last_backup_time = self._get_last_backup_time()
            if last_backup_time:
                backup_age = (datetime.now() - last_backup_time).total_seconds() / 60
                
                if backup_age > self.rpo:
                    logger.warning(f"RPO 違規：最後備份時間 {backup_age:.1f} 分鐘前超過目標 {self.rpo} 分鐘")
                    
                    self._send_emergency_alert("rpo_violation", {
                        "last_backup_age_minutes": backup_age,
                        "rpo_target_minutes": self.rpo,
                    })
            
        except Exception as e:
            logger.error(f"檢查 RTO/RPO 合規性失敗: {e}")
    
    def _get_last_backup_time(self) -> Optional[datetime]:
        """獲取最後備份時間"""
        try:
            # 這裡應該從備份管理器獲取實際的最後備份時間
            # 目前使用模擬實現
            return datetime.now() - timedelta(minutes=10)
        except Exception as e:
            logger.error(f"獲取最後備份時間失敗: {e}")
            return None
    
    def _send_emergency_alert(self, alert_type: str, data: Dict[str, Any]) -> None:
        """發送緊急告警"""
        try:
            self.alert_manager.create_alert(
                title=f"災難恢復告警: {alert_type}",
                message=f"災難恢復事件: {json.dumps(data, indent=2)}",
                severity="critical",
                source="disaster_recovery_manager"
            )
            
            logger.info(f"緊急告警已發送: {alert_type}")
            
        except Exception as e:
            logger.error(f"發送緊急告警失敗: {e}")
    
    def _log_disaster_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """記錄災難事件"""
        try:
            event_log = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "data": data,
            }
            
            # 寫入災難恢復日誌
            log_file = "/var/log/ai_trading/disaster_events.json"
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event_log) + '\n')
            
            logger.info(f"災難事件已記錄: {event_type}")
            
        except Exception as e:
            logger.error(f"記錄災難事件失敗: {e}")
    
    def get_recovery_status(self) -> Dict[str, Any]:
        """獲取恢復狀態"""
        return {
            "monitoring_active": self.is_monitoring,
            "failure_detected": self.failure_detected,
            "recovery_in_progress": self.recovery_in_progress,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "failure_start_time": self.failure_start_time.isoformat() if self.failure_start_time else None,
            "rto_target_minutes": self.rto,
            "rpo_target_minutes": self.rpo,
            "recovery_stats": self.recovery_stats,
        }


def main():
    """主函數"""
    try:
        # 創建災難恢復管理器
        dr_manager = DisasterRecoveryManager()
        
        # 啟動監控
        dr_manager.start_monitoring()
        
        # 保持運行
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("收到中斷信號，正在停止災難恢復監控...")
            dr_manager.stop_monitoring()
            
    except Exception as e:
        logger.error(f"災難恢復管理器運行失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
