"""
事件存儲模組

此模組實現了事件存儲，用於持久化和查詢事件。
"""

import json
import logging
import os
import sqlite3
import threading
from datetime import datetime
from typing import List, Optional

from .event import Event, EventSeverity, EventSource, EventType
from .event_bus import SubscriptionType, event_bus

# 設定日誌
logger = logging.getLogger("events.event_store")


class EventStore:
    """
    事件存儲類，用於持久化和查詢事件

    事件存儲負責：
    1. 將事件持久化到存儲介質
    2. 提供事件查詢功能
    3. 管理事件生命週期
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """實現單例模式"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EventStore, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, db_path: str = "data/events.db", max_events: int = 100000):
        """
        初始化事件存儲

        Args:
            db_path: 數據庫路徑
            max_events: 最大事件數量
        """
        # 避免重複初始化
        if self._initialized:
            return

        self.db_path = db_path
        self.max_events = max_events
        self.subscription = None
        self.running = False
        self.stored_count = 0
        self.error_count = 0

        # 確保目錄存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # 初始化數據庫
        self._init_db()

        self._initialized = True
        logger.info(f"事件存儲已初始化，數據庫路徑: {db_path}")

    def _init_db(self):
        """初始化數據庫"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 創建事件表
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                source TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                severity TEXT NOT NULL,
                subject TEXT,
                message TEXT,
                data TEXT,
                tags TEXT,
                related_events TEXT,
                processed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
            )

            # 創建索引
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (timestamp)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_type ON events (event_type)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_source ON events (source)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_subject ON events (subject)"
            )

            conn.commit()
            conn.close()

            logger.info("數據庫初始化成功")
        except Exception as e:
            logger.exception(f"初始化數據庫時發生錯誤: {e}")

    def start(self):
        """啟動事件存儲"""
        if self.running:
            logger.warning("事件存儲已經在運行中")
            return

        self.running = True

        # 訂閱所有事件
        self.subscription = event_bus.subscribe(
            None, self._store_event, SubscriptionType.ASYNC
        )

        logger.info("事件存儲已啟動")

    def stop(self):
        """停止事件存儲"""
        if not self.running:
            logger.warning("事件存儲尚未啟動")
            return

        self.running = False

        # 取消訂閱
        if self.subscription:
            event_bus.unsubscribe(self.subscription)
            self.subscription = None

        logger.info("事件存儲已停止")

    def _store_event(self, event: Event):
        """
        存儲事件

        Args:
            event: 要存儲的事件
        """
        if not self.running:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 將事件轉換為字典
            event_dict = event.to_dict()

            # 將字典和列表轉換為JSON字符串
            data = (
                json.dumps(event_dict["data"], ensure_ascii=False)
                if event_dict["data"]
                else None
            )
            tags = (
                json.dumps(event_dict["tags"], ensure_ascii=False)
                if event_dict["tags"]
                else None
            )
            related_events = (
                json.dumps(event_dict["related_events"], ensure_ascii=False)
                if event_dict["related_events"]
                else None
            )

            # 插入事件
            cursor.execute(
                """
            INSERT OR REPLACE INTO events (
                id, event_type, source, timestamp, severity, subject, message,
                data, tags, related_events, processed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    event_dict["id"],
                    event_dict["event_type"],
                    event_dict["source"],
                    event_dict["timestamp"],
                    event_dict["severity"],
                    event_dict["subject"],
                    event_dict["message"],
                    data,
                    tags,
                    related_events,
                    1 if event_dict["processed"] else 0,
                ),
            )

            # 清理舊事件
            if self.stored_count % 1000 == 0:
                self._cleanup_old_events(cursor)

            conn.commit()
            conn.close()

            self.stored_count += 1
            logger.debug(f"事件已存儲: {event.id}")
        except Exception as e:
            self.error_count += 1
            logger.exception(f"存儲事件時發生錯誤: {e}")

    def _cleanup_old_events(self, cursor):
        """
        清理舊事件

        Args:
            cursor: 數據庫游標
        """
        try:
            # 獲取事件總數
            cursor.execute("SELECT COUNT(*) FROM events")
            count = cursor.fetchone()[0]

            # 如果超過最大事件數量，則刪除最舊的事件
            if count > self.max_events:
                delete_count = count - self.max_events
                cursor.execute(
                    """
                DELETE FROM events
                WHERE id IN (
                    SELECT id FROM events
                    ORDER BY timestamp ASC
                    LIMIT ?
                )
                """,
                    (delete_count,),
                )

                logger.info(f"已清理 {delete_count} 個舊事件")
        except Exception as e:
            logger.exception(f"清理舊事件時發生錯誤: {e}")

    def get_event(self, event_id: str) -> Optional[Event]:
        """
        獲取事件

        Args:
            event_id: 事件ID

        Returns:
            Optional[Event]: 事件或None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 查詢事件
            cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
            row = cursor.fetchone()

            conn.close()

            if not row:
                return None

            # 將行轉換為字典
            columns = [col[0] for col in cursor.description]
            event_data = dict(zip(columns, row))

            # 將JSON字符串轉換為字典和列表
            event_data["data"] = (
                json.loads(event_data["data"]) if event_data["data"] else {}
            )
            event_data["tags"] = (
                json.loads(event_data["tags"]) if event_data["tags"] else []
            )
            event_data["related_events"] = (
                json.loads(event_data["related_events"])
                if event_data["related_events"]
                else []
            )

            # 創建事件
            return Event.from_dict(event_data)
        except Exception as e:
            logger.exception(f"獲取事件時發生錯誤: {e}")
            return None

    def query_events(
        self,
        event_types: Optional[List[EventType]] = None,
        sources: Optional[List[EventSource]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[EventSeverity] = None,
        subject: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Event]:
        """
        查詢事件

        Args:
            event_types: 事件類型列表
            sources: 事件來源列表
            start_time: 開始時間
            end_time: 結束時間
            severity: 事件嚴重程度
            subject: 事件主題
            limit: 返回結果數量限制
            offset: 返回結果偏移量

        Returns:
            List[Event]: 事件列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 構建查詢條件
            conditions = []
            params = []

            if event_types:
                placeholders = ", ".join(["?"] * len(event_types))
                conditions.append(f"event_type IN ({placeholders})")
                params.extend([et.name for et in event_types])

            if sources:
                placeholders = ", ".join(["?"] * len(sources))
                conditions.append(f"source IN ({placeholders})")
                params.extend([s.name for s in sources])

            if start_time:
                conditions.append("timestamp >= ?")
                params.append(start_time.isoformat())

            if end_time:
                conditions.append("timestamp <= ?")
                params.append(end_time.isoformat())

            if severity:
                conditions.append("severity = ?")
                params.append(severity.name)

            if subject:
                conditions.append("subject = ?")
                params.append(subject)

            # 構建SQL查詢
            sql = "SELECT * FROM events"
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

            sql += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            # 執行查詢
            cursor.execute(sql, params)
            rows = cursor.fetchall()

            # 將行轉換為事件
            events = []
            columns = [col[0] for col in cursor.description]

            for row in rows:
                event_data = dict(zip(columns, row))

                # 將JSON字符串轉換為字典和列表
                event_data["data"] = (
                    json.loads(event_data["data"]) if event_data["data"] else {}
                )
                event_data["tags"] = (
                    json.loads(event_data["tags"]) if event_data["tags"] else []
                )
                event_data["related_events"] = (
                    json.loads(event_data["related_events"])
                    if event_data["related_events"]
                    else []
                )

                # 創建事件
                events.append(Event.from_dict(event_data))

            conn.close()

            return events
        except Exception as e:
            logger.exception(f"查詢事件時發生錯誤: {e}")
            return []

    def get_stats(self):
        """
        獲取存儲統計信息

        Returns:
            dict: 統計信息
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 獲取事件總數
            cursor.execute("SELECT COUNT(*) FROM events")
            total_count = cursor.fetchone()[0]

            # 獲取各類型事件數量
            cursor.execute(
                "SELECT event_type, COUNT(*) FROM events GROUP BY event_type"
            )
            type_counts = {row[0]: row[1] for row in cursor.fetchall()}

            # 獲取各來源事件數量
            cursor.execute("SELECT source, COUNT(*) FROM events GROUP BY source")
            source_counts = {row[0]: row[1] for row in cursor.fetchall()}

            # 獲取各嚴重程度事件數量
            cursor.execute("SELECT severity, COUNT(*) FROM events GROUP BY severity")
            severity_counts = {row[0]: row[1] for row in cursor.fetchall()}

            # 獲取最新事件時間
            cursor.execute("SELECT MAX(timestamp) FROM events")
            latest_time = cursor.fetchone()[0]

            conn.close()

            return {
                "total_count": total_count,
                "type_counts": type_counts,
                "source_counts": source_counts,
                "severity_counts": severity_counts,
                "latest_time": latest_time,
                "stored_count": self.stored_count,
                "error_count": self.error_count,
                "running": self.running,
            }
        except Exception as e:
            logger.exception(f"獲取存儲統計信息時發生錯誤: {e}")
            return {
                "error": str(e),
                "stored_count": self.stored_count,
                "error_count": self.error_count,
                "running": self.running,
            }


# 創建全局事件存儲實例
event_store = EventStore()
