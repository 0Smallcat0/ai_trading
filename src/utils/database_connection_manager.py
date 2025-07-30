#!/usr/bin/env python3
"""
資料庫連接管理器
解決SQLite檔案鎖定問題，確保連接正確關閉
"""

import sqlite3
import time
import os
import logging
from contextlib import contextmanager
from typing import Optional, Generator
import threading

logger = logging.getLogger(__name__)

class DatabaseConnectionManager:
    """資料庫連接管理器，確保連接正確關閉和檔案釋放"""
    
    def __init__(self):
        self._connections = {}
        self._lock = threading.Lock()
    
    @contextmanager
    def get_connection(self, db_path: str, timeout: float = 30.0) -> Generator[sqlite3.Connection, None, None]:
        """
        獲取資料庫連接的上下文管理器
        
        Args:
            db_path: 資料庫檔案路徑
            timeout: 連接超時時間（秒）
            
        Yields:
            sqlite3.Connection: 資料庫連接對象
        """
        conn = None
        try:
            # 設置連接參數以避免鎖定問題
            conn = sqlite3.connect(
                db_path,
                timeout=timeout,
                check_same_thread=False,
                isolation_level=None  # 自動提交模式
            )
            
            # 設置WAL模式以減少鎖定
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=memory")
            
            logger.debug(f"成功連接到資料庫: {db_path}")
            yield conn
            
        except Exception as e:
            logger.error(f"資料庫連接錯誤 {db_path}: {e}")
            raise
        finally:
            if conn:
                try:
                    # 確保所有事務都已提交
                    conn.commit()
                    # 關閉連接
                    conn.close()
                    logger.debug(f"已關閉資料庫連接: {db_path}")
                except Exception as e:
                    logger.warning(f"關閉資料庫連接時發生錯誤 {db_path}: {e}")
    
    def safe_remove_database(self, db_path: str, max_retries: int = 5, retry_delay: float = 1.0) -> bool:
        """
        安全刪除資料庫檔案，處理檔案鎖定問題

        Args:
            db_path: 資料庫檔案路徑
            max_retries: 最大重試次數
            retry_delay: 重試間隔（秒）

        Returns:
            bool: 是否成功刪除
        """
        if not os.path.exists(db_path):
            logger.debug(f"資料庫檔案不存在: {db_path}")
            return True

        # 首先嘗試強制關閉所有連接
        try:
            import gc
            gc.collect()  # 強制垃圾回收
            time.sleep(0.5)
        except:
            pass

        for attempt in range(max_retries):
            try:
                # 先刪除相關的WAL和SHM檔案
                for suffix in ['-wal', '-shm']:
                    related_file = db_path + suffix
                    if os.path.exists(related_file):
                        try:
                            os.remove(related_file)
                            logger.debug(f"刪除相關檔案: {related_file}")
                        except Exception as e:
                            logger.debug(f"無法刪除相關檔案 {related_file}: {e}")

                # 等待檔案釋放
                time.sleep(retry_delay)

                # 嘗試刪除主檔案
                os.remove(db_path)
                logger.info(f"成功刪除資料庫檔案: {db_path}")
                return True

            except PermissionError as e:
                logger.warning(f"第{attempt + 1}次嘗試刪除檔案失敗 {db_path}: {e}")
                if attempt < max_retries - 1:
                    # 嘗試更激進的清理方法
                    try:
                        import gc
                        gc.collect()
                        time.sleep(retry_delay * (attempt + 2))  # 遞增延遲
                    except:
                        time.sleep(retry_delay * (attempt + 2))
                else:
                    # 最後嘗試：重命名檔案而不是刪除
                    try:
                        import uuid
                        temp_name = f"{db_path}.deleted_{uuid.uuid4().hex[:8]}"
                        os.rename(db_path, temp_name)
                        logger.info(f"檔案被重命名為: {temp_name}")
                        return True
                    except Exception as rename_error:
                        logger.error(f"無法刪除或重命名資料庫檔案 {db_path}: {rename_error}")
                        return False
            except Exception as e:
                logger.error(f"刪除資料庫檔案時發生未預期錯誤 {db_path}: {e}")
                return False

        return False
    
    def test_connection(self, db_path: str) -> bool:
        """
        測試資料庫連接是否正常
        
        Args:
            db_path: 資料庫檔案路徑
            
        Returns:
            bool: 連接是否成功
        """
        try:
            with self.get_connection(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"資料庫連接測試失敗 {db_path}: {e}")
            return False
    
    def create_test_database(self, db_path: str, table_schema: Optional[str] = None) -> bool:
        """
        創建測試資料庫
        
        Args:
            db_path: 資料庫檔案路徑
            table_schema: 表格結構SQL（可選）
            
        Returns:
            bool: 是否創建成功
        """
        try:
            # 確保目錄存在
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            with self.get_connection(db_path) as conn:
                cursor = conn.cursor()
                
                if table_schema:
                    cursor.execute(table_schema)
                else:
                    # 默認創建一個測試表
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS test_table (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name TEXT NOT NULL,
                            value REAL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                
                conn.commit()
                logger.info(f"成功創建測試資料庫: {db_path}")
                return True
                
        except Exception as e:
            logger.error(f"創建測試資料庫失敗 {db_path}: {e}")
            return False

# 全域連接管理器實例
db_manager = DatabaseConnectionManager()

@contextmanager
def get_db_connection(db_path: str, timeout: float = 30.0):
    """
    便捷的資料庫連接上下文管理器
    
    Args:
        db_path: 資料庫檔案路徑
        timeout: 連接超時時間
        
    Yields:
        sqlite3.Connection: 資料庫連接
    """
    with db_manager.get_connection(db_path, timeout) as conn:
        yield conn

def safe_remove_db(db_path: str, max_retries: int = 5) -> bool:
    """
    安全刪除資料庫檔案的便捷函數
    
    Args:
        db_path: 資料庫檔案路徑
        max_retries: 最大重試次數
        
    Returns:
        bool: 是否成功刪除
    """
    return db_manager.safe_remove_database(db_path, max_retries)

def test_db_connection(db_path: str) -> bool:
    """
    測試資料庫連接的便捷函數
    
    Args:
        db_path: 資料庫檔案路徑
        
    Returns:
        bool: 連接是否成功
    """
    return db_manager.test_connection(db_path)

# 使用示例
if __name__ == "__main__":
    # 設置日誌
    logging.basicConfig(level=logging.DEBUG)
    
    # 測試資料庫路徑
    test_db = "data/test_connection_manager.db"
    
    try:
        # 創建測試資料庫
        print("創建測試資料庫...")
        if db_manager.create_test_database(test_db):
            print("✅ 資料庫創建成功")
        
        # 測試連接
        print("測試資料庫連接...")
        if test_db_connection(test_db):
            print("✅ 連接測試成功")
        
        # 使用連接管理器
        print("使用連接管理器...")
        with get_db_connection(test_db) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO test_table (name, value) VALUES (?, ?)", ("test", 123.45))
            cursor.execute("SELECT COUNT(*) FROM test_table")
            count = cursor.fetchone()[0]
            print(f"✅ 資料庫操作成功，記錄數: {count}")
        
        # 安全刪除
        print("安全刪除測試資料庫...")
        if safe_remove_db(test_db):
            print("✅ 資料庫刪除成功")
        else:
            print("❌ 資料庫刪除失敗")
            
    except Exception as e:
        print(f"❌ 測試過程中發生錯誤: {e}")
        # 清理
        safe_remove_db(test_db)
