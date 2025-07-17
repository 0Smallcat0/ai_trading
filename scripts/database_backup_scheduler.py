#!/usr/bin/env python3
"""
AI 交易系統資料庫自動備份排程器
版本: v1.0
最後更新: 2024-12-25

此腳本實現自動化資料庫備份排程，包括：
- 完整備份、增量備份、日誌備份
- 備份驗證和完整性檢查
- 雲端存儲同步
- 備份清理和保留策略
- 監控和告警整合
"""

import os
import sys
import yaml
import logging
import schedule
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import subprocess
import hashlib
import json

# 添加項目根目錄到 Python 路徑
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.data_backup import DataBackupManager
from src.database.checksum_manager import ChecksumManager
from src.monitoring.intelligent_alert_manager import IntelligentAlertManager

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/ai_trading/backup_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DatabaseBackupScheduler:
    """資料庫備份排程器"""
    
    def __init__(self, config_path: str = "config/database_production.yaml"):
        """初始化備份排程器
        
        Args:
            config_path: 配置文件路徑
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.backup_manager = DataBackupManager()
        self.checksum_manager = ChecksumManager()
        self.alert_manager = IntelligentAlertManager()
        
        # 運行狀態
        self.is_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 備份統計
        self.backup_stats = {
            "total_backups": 0,
            "successful_backups": 0,
            "failed_backups": 0,
            "last_backup_time": None,
            "last_backup_status": None,
            "backup_sizes": [],
        }
        
        logger.info("資料庫備份排程器初始化完成")
    
    def _load_config(self) -> Dict[str, Any]:
        """載入配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"配置文件載入成功: {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"載入配置文件失敗: {e}")
            raise
    
    def start_scheduler(self) -> None:
        """啟動備份排程器"""
        if self.is_running:
            logger.warning("備份排程器已在運行中")
            return
        
        try:
            # 設置排程任務
            self._setup_backup_schedules()
            
            # 啟動排程器線程
            self.is_running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.scheduler_thread.start()
            
            logger.info("資料庫備份排程器已啟動")
            
        except Exception as e:
            logger.error(f"啟動備份排程器失敗: {e}")
            self.is_running = False
            raise
    
    def stop_scheduler(self) -> None:
        """停止備份排程器"""
        if not self.is_running:
            logger.warning("備份排程器未在運行")
            return
        
        try:
            self.is_running = False
            self._stop_event.set()
            
            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=30)
            
            schedule.clear()
            logger.info("資料庫備份排程器已停止")
            
        except Exception as e:
            logger.error(f"停止備份排程器失敗: {e}")
    
    def _setup_backup_schedules(self) -> None:
        """設置備份排程"""
        backup_config = self.config.get("backup", {})
        schedules = backup_config.get("automatic", {}).get("schedule", {})
        
        # 完整備份排程
        if "full_backup" in schedules:
            schedule.every().day.at("02:00").do(self._run_full_backup)
            logger.info(f"完整備份排程已設置: {schedules['full_backup']}")
        
        # 增量備份排程
        if "incremental" in schedules:
            schedule.every(6).hours.do(self._run_incremental_backup)
            logger.info(f"增量備份排程已設置: {schedules['incremental']}")
        
        # 日誌備份排程
        if "log_backup" in schedules:
            schedule.every(15).minutes.do(self._run_log_backup)
            logger.info(f"日誌備份排程已設置: {schedules['log_backup']}")
        
        # 備份驗證排程
        verification_config = backup_config.get("verification", {})
        if verification_config.get("enabled", False):
            schedule.every().day.at("04:00").do(self._run_backup_verification)
            logger.info("備份驗證排程已設置")
        
        # 備份清理排程
        schedule.every().day.at("05:00").do(self._run_backup_cleanup)
        logger.info("備份清理排程已設置")
    
    def _run_scheduler(self) -> None:
        """運行排程器主循環"""
        logger.info("備份排程器主循環已啟動")
        
        while self.is_running and not self._stop_event.is_set():
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分鐘檢查一次
                
            except Exception as e:
                logger.error(f"排程器運行錯誤: {e}")
                time.sleep(60)
        
        logger.info("備份排程器主循環已停止")
    
    def _run_full_backup(self) -> None:
        """執行完整備份"""
        logger.info("開始執行完整備份")
        
        try:
            # 生成備份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"/opt/ai_trading/backups/database/full_backup_{timestamp}.sql.gz"
            
            # 執行備份
            result = self.backup_manager.create_full_backup(backup_path)
            
            if result:
                # 更新統計
                self._update_backup_stats("full", True, backup_path)
                
                # 生成校驗和
                checksum = self._generate_checksum(backup_path)
                
                # 同步到雲端
                if self.config.get("backup", {}).get("storage", {}).get("cloud_enabled", False):
                    self._sync_to_cloud(backup_path)
                
                # 發送成功通知
                self._send_backup_notification("full", True, backup_path, checksum)
                
                logger.info(f"完整備份成功: {backup_path}")
            else:
                self._update_backup_stats("full", False)
                self._send_backup_notification("full", False)
                logger.error("完整備份失敗")
                
        except Exception as e:
            logger.error(f"執行完整備份時發生錯誤: {e}")
            self._update_backup_stats("full", False)
            self._send_backup_notification("full", False, error=str(e))
    
    def _run_incremental_backup(self) -> None:
        """執行增量備份"""
        logger.info("開始執行增量備份")
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"/opt/ai_trading/backups/database/incremental_backup_{timestamp}.sql.gz"
            
            result = self.backup_manager.create_incremental_backup(backup_path)
            
            if result:
                self._update_backup_stats("incremental", True, backup_path)
                checksum = self._generate_checksum(backup_path)
                
                if self.config.get("backup", {}).get("storage", {}).get("cloud_enabled", False):
                    self._sync_to_cloud(backup_path)
                
                logger.info(f"增量備份成功: {backup_path}")
            else:
                self._update_backup_stats("incremental", False)
                logger.error("增量備份失敗")
                
        except Exception as e:
            logger.error(f"執行增量備份時發生錯誤: {e}")
            self._update_backup_stats("incremental", False)
    
    def _run_log_backup(self) -> None:
        """執行日誌備份"""
        logger.info("開始執行日誌備份")
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"/opt/ai_trading/backups/database/log_backup_{timestamp}.tar.gz"
            
            # 備份 WAL 日誌文件
            result = self._backup_wal_logs(backup_path)
            
            if result:
                self._update_backup_stats("log", True, backup_path)
                logger.info(f"日誌備份成功: {backup_path}")
            else:
                self._update_backup_stats("log", False)
                logger.error("日誌備份失敗")
                
        except Exception as e:
            logger.error(f"執行日誌備份時發生錯誤: {e}")
            self._update_backup_stats("log", False)
    
    def _run_backup_verification(self) -> None:
        """執行備份驗證"""
        logger.info("開始執行備份驗證")
        
        try:
            # 獲取最新的備份文件
            latest_backup = self._get_latest_backup()
            
            if latest_backup:
                # 驗證備份完整性
                is_valid = self.checksum_manager.verify_backup(latest_backup)
                
                if is_valid:
                    logger.info(f"備份驗證成功: {latest_backup}")
                    
                    # 可選：測試恢復
                    if self.config.get("backup", {}).get("verification", {}).get("test_restore", False):
                        self._test_backup_restore(latest_backup)
                else:
                    logger.error(f"備份驗證失敗: {latest_backup}")
                    self._send_backup_alert("backup_verification_failed", latest_backup)
            else:
                logger.warning("未找到可驗證的備份文件")
                
        except Exception as e:
            logger.error(f"執行備份驗證時發生錯誤: {e}")
    
    def _run_backup_cleanup(self) -> None:
        """執行備份清理"""
        logger.info("開始執行備份清理")
        
        try:
            retention_config = self.config.get("backup", {}).get("retention", {})
            backup_dir = Path("/opt/ai_trading/backups/database")
            
            # 清理過期的日備份
            self._cleanup_old_backups(backup_dir, "full_backup_", retention_config.get("daily_backups", 30))
            
            # 清理過期的增量備份
            self._cleanup_old_backups(backup_dir, "incremental_backup_", 7)  # 保留7天
            
            # 清理過期的日誌備份
            self._cleanup_old_backups(backup_dir, "log_backup_", 3)  # 保留3天
            
            logger.info("備份清理完成")
            
        except Exception as e:
            logger.error(f"執行備份清理時發生錯誤: {e}")
    
    def _generate_checksum(self, file_path: str) -> str:
        """生成文件校驗和"""
        try:
            with open(file_path, 'rb') as f:
                checksum = hashlib.sha256(f.read()).hexdigest()
            
            # 保存校驗和文件
            checksum_file = f"{file_path}.sha256"
            with open(checksum_file, 'w') as f:
                f.write(f"{checksum}  {Path(file_path).name}\n")
            
            return checksum
            
        except Exception as e:
            logger.error(f"生成校驗和失敗: {e}")
            return ""
    
    def _sync_to_cloud(self, file_path: str) -> bool:
        """同步備份到雲端存儲"""
        try:
            cloud_config = self.config.get("backup", {}).get("storage", {})
            provider = cloud_config.get("cloud_provider", "aws_s3")
            bucket = cloud_config.get("cloud_bucket", "ai-trading-backups")
            
            # 這裡應該實現實際的雲端同步邏輯
            # 目前使用模擬實現
            logger.info(f"模擬同步到雲端: {provider}/{bucket}/{Path(file_path).name}")
            return True
            
        except Exception as e:
            logger.error(f"同步到雲端失敗: {e}")
            return False
    
    def _update_backup_stats(self, backup_type: str, success: bool, file_path: str = None) -> None:
        """更新備份統計"""
        self.backup_stats["total_backups"] += 1
        
        if success:
            self.backup_stats["successful_backups"] += 1
            self.backup_stats["last_backup_status"] = "success"
            
            if file_path and os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                self.backup_stats["backup_sizes"].append({
                    "type": backup_type,
                    "size": file_size,
                    "timestamp": datetime.now().isoformat()
                })
        else:
            self.backup_stats["failed_backups"] += 1
            self.backup_stats["last_backup_status"] = "failed"
        
        self.backup_stats["last_backup_time"] = datetime.now().isoformat()
    
    def get_backup_status(self) -> Dict[str, Any]:
        """獲取備份狀態"""
        return {
            "scheduler_running": self.is_running,
            "stats": self.backup_stats,
            "next_scheduled_jobs": [str(job) for job in schedule.jobs],
            "config_loaded": bool(self.config),
        }


def main():
    """主函數"""
    try:
        # 創建備份排程器
        scheduler = DatabaseBackupScheduler()
        
        # 啟動排程器
        scheduler.start_scheduler()
        
        # 保持運行
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("收到中斷信號，正在停止排程器...")
            scheduler.stop_scheduler()
            
    except Exception as e:
        logger.error(f"備份排程器運行失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
