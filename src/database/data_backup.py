"""
資料備份與還原模組

此模組提供資料庫的備份和還原功能，確保資料的安全性和可恢復性。
支援定期自動備份、增量備份和完整備份。

主要功能：
- 資料庫完整備份
- 增量備份
- 備份壓縮和加密
- 備份還原
- 備份排程管理
"""

import os
import shutil
import logging
import sqlite3
import zipfile
import hashlib
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple, Set
import subprocess
import threading
import schedule
import time

from src.config import DATA_DIR, DB_URL, MARKET_INFO_DB, LOG_LEVEL

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))

# 備份目錄
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)


class DatabaseBackup:
    """
    資料庫備份類

    提供資料庫的備份和還原功能。
    """

    def __init__(self, db_url: str = DB_URL, backup_dir: str = BACKUP_DIR):
        """
        初始化資料庫備份類

        Args:
            db_url: 資料庫連接 URL
            backup_dir: 備份目錄
        """
        self.db_url = db_url
        self.backup_dir = backup_dir
        self.is_sqlite = "sqlite" in db_url.lower()
        
        # 從 db_url 解析資料庫路徑（僅適用於 SQLite）
        if self.is_sqlite:
            self.db_path = db_url.replace("sqlite:///", "")
        else:
            # 對於其他資料庫類型，需要解析連接字串
            # 這裡僅作為示例，實際使用時需要根據具體的資料庫類型進行調整
            self.db_path = None
        
        # 確保備份目錄存在
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # 備份排程器
        self.scheduler = None
        self.scheduler_thread = None
        self.is_running = False

    def backup_sqlite(self, backup_path: str) -> bool:
        """
        備份 SQLite 資料庫

        使用 SQLite 的備份 API 進行備份。

        Args:
            backup_path: 備份檔案路徑

        Returns:
            bool: 是否成功
        """
        try:
            # 確保目錄存在
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            # 連接來源資料庫
            source_conn = sqlite3.connect(self.db_path)
            
            # 連接目標資料庫
            backup_conn = sqlite3.connect(backup_path)
            
            # 執行備份
            source_conn.backup(backup_conn)
            
            # 關閉連接
            source_conn.close()
            backup_conn.close()
            
            logger.info(f"成功備份 SQLite 資料庫到 {backup_path}")
            return True
        except Exception as e:
            logger.error(f"備份 SQLite 資料庫時發生錯誤: {e}")
            return False

    def backup_postgres(self, backup_path: str) -> bool:
        """
        備份 PostgreSQL 資料庫

        使用 pg_dump 工具進行備份。

        Args:
            backup_path: 備份檔案路徑

        Returns:
            bool: 是否成功
        """
        try:
            # 從 db_url 解析連接資訊
            # 格式: postgresql://username:password@host:port/dbname
            import re
            match = re.match(
                r"postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", self.db_url
            )
            if not match:
                logger.error(f"無法解析 PostgreSQL 連接字串: {self.db_url}")
                return False
            
            username, password, host, port, dbname = match.groups()
            
            # 設置環境變數
            env = os.environ.copy()
            env["PGPASSWORD"] = password
            
            # 執行 pg_dump 命令
            cmd = [
                "pg_dump",
                "-h", host,
                "-p", port,
                "-U", username,
                "-F", "c",  # 自定義格式
                "-f", backup_path,
                dbname
            ]
            
            result = subprocess.run(cmd, env=env, check=True, capture_output=True)
            
            if result.returncode == 0:
                logger.info(f"成功備份 PostgreSQL 資料庫到 {backup_path}")
                return True
            else:
                logger.error(f"備份 PostgreSQL 資料庫失敗: {result.stderr.decode()}")
                return False
        except Exception as e:
            logger.error(f"備份 PostgreSQL 資料庫時發生錯誤: {e}")
            return False

    def backup_influxdb(self, backup_path: str) -> bool:
        """
        備份 InfluxDB 資料庫

        使用 influxd backup 命令進行備份。

        Args:
            backup_path: 備份目錄路徑

        Returns:
            bool: 是否成功
        """
        try:
            # 從 db_url 解析連接資訊
            # 格式: influxdb://username:password@host:port/dbname
            import re
            match = re.match(
                r"influxdb://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", self.db_url
            )
            if not match:
                logger.error(f"無法解析 InfluxDB 連接字串: {self.db_url}")
                return False
            
            username, password, host, port, dbname = match.groups()
            
            # 執行 influxd backup 命令
            cmd = [
                "influxd", "backup",
                "-host", f"{host}:{port}",
                "-database", dbname,
                backup_path
            ]
            
            result = subprocess.run(cmd, check=True, capture_output=True)
            
            if result.returncode == 0:
                logger.info(f"成功備份 InfluxDB 資料庫到 {backup_path}")
                return True
            else:
                logger.error(f"備份 InfluxDB 資料庫失敗: {result.stderr.decode()}")
                return False
        except Exception as e:
            logger.error(f"備份 InfluxDB 資料庫時發生錯誤: {e}")
            return False

    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """
        創建資料庫備份

        根據資料庫類型選擇適當的備份方法。

        Args:
            backup_name: 備份名稱，如果未提供則使用時間戳

        Returns:
            str: 備份檔案路徑
        """
        # 生成備份名稱
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"
        
        # 生成備份路徑
        if self.is_sqlite:
            backup_path = os.path.join(self.backup_dir, f"{backup_name}.db")
            success = self.backup_sqlite(backup_path)
        elif "postgresql" in self.db_url.lower():
            backup_path = os.path.join(self.backup_dir, f"{backup_name}.dump")
            success = self.backup_postgres(backup_path)
        elif "influxdb" in self.db_url.lower():
            backup_path = os.path.join(self.backup_dir, backup_name)
            os.makedirs(backup_path, exist_ok=True)
            success = self.backup_influxdb(backup_path)
        else:
            logger.error(f"不支援的資料庫類型: {self.db_url}")
            return ""
        
        if success:
            # 壓縮備份
            compressed_path = self.compress_backup(backup_path)
            
            # 計算校驗碼
            checksum = self.calculate_checksum(compressed_path)
            
            # 記錄備份資訊
            self.record_backup_info(backup_name, compressed_path, checksum)
            
            return compressed_path
        else:
            return ""

    def compress_backup(self, backup_path: str) -> str:
        """
        壓縮備份檔案

        Args:
            backup_path: 備份檔案路徑

        Returns:
            str: 壓縮後的檔案路徑
        """
        try:
            # 生成壓縮檔案路徑
            zip_path = f"{backup_path}.zip"
            
            # 創建壓縮檔案
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                if os.path.isdir(backup_path):
                    # 如果是目錄，壓縮整個目錄
                    for root, _, files in os.walk(backup_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, os.path.dirname(backup_path))
                            zipf.write(file_path, arcname)
                else:
                    # 如果是檔案，直接壓縮
                    arcname = os.path.basename(backup_path)
                    zipf.write(backup_path, arcname)
            
            # 刪除原始備份檔案
            if os.path.isdir(backup_path):
                shutil.rmtree(backup_path)
            else:
                os.remove(backup_path)
            
            logger.info(f"成功壓縮備份檔案: {zip_path}")
            return zip_path
        except Exception as e:
            logger.error(f"壓縮備份檔案時發生錯誤: {e}")
            return backup_path

    def calculate_checksum(self, file_path: str) -> str:
        """
        計算檔案的校驗碼

        Args:
            file_path: 檔案路徑

        Returns:
            str: 校驗碼
        """
        try:
            # 計算 SHA-256 校驗碼
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"計算校驗碼時發生錯誤: {e}")
            return ""

    def record_backup_info(self, backup_name: str, backup_path: str, checksum: str) -> None:
        """
        記錄備份資訊

        Args:
            backup_name: 備份名稱
            backup_path: 備份檔案路徑
            checksum: 校驗碼
        """
        try:
            # 備份資訊檔案路徑
            info_path = os.path.join(self.backup_dir, "backup_info.json")
            
            # 讀取現有資訊
            if os.path.exists(info_path):
                with open(info_path, "r", encoding="utf-8") as f:
                    backup_info = json.load(f)
            else:
                backup_info = {"backups": []}
            
            # 添加新的備份資訊
            backup_info["backups"].append({
                "name": backup_name,
                "path": backup_path,
                "checksum": checksum,
                "timestamp": datetime.now().isoformat(),
                "size": os.path.getsize(backup_path),
                "db_url": self.db_url,
            })
            
            # 寫入資訊檔案
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump(backup_info, f, indent=2, ensure_ascii=False)
            
            logger.info(f"成功記錄備份資訊: {backup_name}")
        except Exception as e:
            logger.error(f"記錄備份資訊時發生錯誤: {e}")

    def restore_backup(self, backup_path: str) -> bool:
        """
        還原資料庫備份

        Args:
            backup_path: 備份檔案路徑

        Returns:
            bool: 是否成功
        """
        try:
            # 檢查備份檔案是否存在
            if not os.path.exists(backup_path):
                logger.error(f"備份檔案不存在: {backup_path}")
                return False
            
            # 如果是壓縮檔案，先解壓
            if backup_path.endswith(".zip"):
                # 創建臨時目錄
                temp_dir = os.path.join(self.backup_dir, "temp_restore")
                os.makedirs(temp_dir, exist_ok=True)
                
                # 解壓檔案
                with zipfile.ZipFile(backup_path, "r") as zipf:
                    zipf.extractall(temp_dir)
                
                # 找出解壓後的檔案
                extracted_files = os.listdir(temp_dir)
                if not extracted_files:
                    logger.error(f"解壓後沒有找到檔案: {backup_path}")
                    return False
                
                # 對於 SQLite，找出 .db 檔案
                if self.is_sqlite:
                    db_files = [f for f in extracted_files if f.endswith(".db")]
                    if db_files:
                        backup_path = os.path.join(temp_dir, db_files[0])
                    else:
                        # 如果沒有 .db 檔案，使用第一個檔案
                        backup_path = os.path.join(temp_dir, extracted_files[0])
                else:
                    # 對於其他資料庫類型，使用解壓目錄
                    backup_path = temp_dir
            
            # 根據資料庫類型選擇還原方法
            if self.is_sqlite:
                return self.restore_sqlite(backup_path)
            elif "postgresql" in self.db_url.lower():
                return self.restore_postgres(backup_path)
            elif "influxdb" in self.db_url.lower():
                return self.restore_influxdb(backup_path)
            else:
                logger.error(f"不支援的資料庫類型: {self.db_url}")
                return False
        except Exception as e:
            logger.error(f"還原備份時發生錯誤: {e}")
            return False
        finally:
            # 清理臨時目錄
            if "temp_dir" in locals() and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def restore_sqlite(self, backup_path: str) -> bool:
        """
        還原 SQLite 資料庫

        Args:
            backup_path: 備份檔案路徑

        Returns:
            bool: 是否成功
        """
        try:
            # 備份當前資料庫
            current_backup = os.path.join(
                self.backup_dir, 
                f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            )
            shutil.copy2(self.db_path, current_backup)
            
            # 還原資料庫
            shutil.copy2(backup_path, self.db_path)
            
            logger.info(f"成功還原 SQLite 資料庫從 {backup_path}")
            return True
        except Exception as e:
            logger.error(f"還原 SQLite 資料庫時發生錯誤: {e}")
            return False

    def restore_postgres(self, backup_path: str) -> bool:
        """
        還原 PostgreSQL 資料庫

        Args:
            backup_path: 備份檔案路徑

        Returns:
            bool: 是否成功
        """
        try:
            # 從 db_url 解析連接資訊
            import re
            match = re.match(
                r"postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", self.db_url
            )
            if not match:
                logger.error(f"無法解析 PostgreSQL 連接字串: {self.db_url}")
                return False
            
            username, password, host, port, dbname = match.groups()
            
            # 設置環境變數
            env = os.environ.copy()
            env["PGPASSWORD"] = password
            
            # 執行 pg_restore 命令
            cmd = [
                "pg_restore",
                "-h", host,
                "-p", port,
                "-U", username,
                "-d", dbname,
                "-c",  # 清除現有資料
                backup_path
            ]
            
            result = subprocess.run(cmd, env=env, check=True, capture_output=True)
            
            if result.returncode == 0:
                logger.info(f"成功還原 PostgreSQL 資料庫從 {backup_path}")
                return True
            else:
                logger.error(f"還原 PostgreSQL 資料庫失敗: {result.stderr.decode()}")
                return False
        except Exception as e:
            logger.error(f"還原 PostgreSQL 資料庫時發生錯誤: {e}")
            return False

    def restore_influxdb(self, backup_path: str) -> bool:
        """
        還原 InfluxDB 資料庫

        Args:
            backup_path: 備份目錄路徑

        Returns:
            bool: 是否成功
        """
        try:
            # 從 db_url 解析連接資訊
            import re
            match = re.match(
                r"influxdb://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", self.db_url
            )
            if not match:
                logger.error(f"無法解析 InfluxDB 連接字串: {self.db_url}")
                return False
            
            username, password, host, port, dbname = match.groups()
            
            # 執行 influxd restore 命令
            cmd = [
                "influxd", "restore",
                "-host", f"{host}:{port}",
                "-database", dbname,
                backup_path
            ]
            
            result = subprocess.run(cmd, check=True, capture_output=True)
            
            if result.returncode == 0:
                logger.info(f"成功還原 InfluxDB 資料庫從 {backup_path}")
                return True
            else:
                logger.error(f"還原 InfluxDB 資料庫失敗: {result.stderr.decode()}")
                return False
        except Exception as e:
            logger.error(f"還原 InfluxDB 資料庫時發生錯誤: {e}")
            return False

    def schedule_backup(self, interval: str = "daily") -> None:
        """
        排程備份

        Args:
            interval: 備份間隔，可選 "hourly"、"daily"、"weekly"
        """
        if self.is_running:
            logger.warning("備份排程已在運行中")
            return
        
        # 設定排程
        if interval == "hourly":
            schedule.every().hour.do(self.create_backup)
        elif interval == "daily":
            schedule.every().day.at("01:00").do(self.create_backup)
        elif interval == "weekly":
            schedule.every().monday.at("01:00").do(self.create_backup)
        else:
            logger.error(f"不支援的備份間隔: {interval}")
            return
        
        # 啟動排程執行緒
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        logger.info(f"已啟動 {interval} 備份排程")

    def _run_scheduler(self) -> None:
        """
        執行排程器
        """
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)

    def stop_scheduler(self) -> None:
        """
        停止排程器
        """
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        # 清除所有排程
        schedule.clear()
        
        logger.info("已停止備份排程")
