"""
資料版本控制模組

此模組提供資料庫結構和資料的版本控制功能，
用於追蹤資料庫結構的變更和重要資料的修改歷史。

主要功能：
- 資料庫結構版本管理
- 資料變更追蹤
- 資料庫遷移
- 變更歷史記錄
"""

import hashlib
import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, inspect, text
from sqlalchemy.orm import Session


# 自定義 JSON 編碼器，處理日期、時間和 DataFrame 類型
class CustomJSONEncoder(json.JSONEncoder):
"""
CustomJSONEncoder

"""
    def default(self, obj):
    """
    default
    
    Args:
        obj: 
    """
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        elif hasattr(obj, "to_dict"):
            return obj.to_dict()
        return super().default(obj)


from src.config import LOG_LEVEL
from src.database.schema import Base, DatabaseVersion, SystemLog

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class DataVersionManager:
    """
    資料版本管理器

    提供資料庫結構和資料的版本控制功能。
    """

    def __init__(self, session: Session):
        """
        初始化資料版本管理器

        Args:
            session: SQLAlchemy 會話
        """
        self.session = session

    def get_current_version(self) -> Optional[str]:
        """
        獲取當前資料庫版本

        Returns:
            Optional[str]: 當前版本號，如果沒有版本記錄則返回 None
        """
        version_record = (
            self.session.query(DatabaseVersion)
            .order_by(DatabaseVersion.id.desc())
            .first()
        )

        if version_record:
            return version_record.version
        else:
            return None

    def update_version(
        self,
        version: str,
        description: str,
        changes: Dict[str, Any],
        applied_by: str = "system",
    ) -> DatabaseVersion:
        """
        更新資料庫版本

        Args:
            version: 新版本號
            description: 版本描述
            changes: 變更內容
            applied_by: 應用者

        Returns:
            DatabaseVersion: 新的版本記錄
        """
        # 將變更內容轉換為 JSON 字串，使用自定義編碼器處理日期和時間
        changes_json = json.dumps(changes, cls=CustomJSONEncoder)
        changes_dict = json.loads(changes_json)

        # 創建新的版本記錄
        version_record = DatabaseVersion(
            version=version,
            description=description,
            changes=changes_dict,
            applied_by=applied_by,
            applied_at=datetime.now(),
        )

        # 添加到資料庫
        self.session.add(version_record)
        self.session.commit()

        logger.info(f"已更新資料庫版本到 {version}")

        return version_record

    def get_version_history(self) -> List[Dict[str, Any]]:
        """
        獲取版本歷史

        Returns:
            List[Dict[str, Any]]: 版本歷史記錄列表
        """
        version_records = (
            self.session.query(DatabaseVersion).order_by(DatabaseVersion.id).all()
        )

        history = []
        for record in version_records:
            history.append(
                {
                    "id": record.id,
                    "version": record.version,
                    "description": record.description,
                    "changes": record.changes,
                    "applied_by": record.applied_by,
                    "applied_at": (
                        record.applied_at.isoformat() if record.applied_at else None
                    ),
                }
            )

        return history

    def compare_schema_with_models(self) -> Dict[str, Any]:
        """
        比較資料庫結構與模型定義

        檢查資料庫中的表結構是否與模型定義一致。

        Returns:
            Dict[str, Any]: 比較結果
        """
        inspector = inspect(self.session.bind)

        # 獲取資料庫中的表
        db_tables = inspector.get_table_names()

        # 獲取模型定義的表
        model_tables = [table.name for table in Base.metadata.sorted_tables]

        # 比較表
        missing_tables = [table for table in model_tables if table not in db_tables]
        extra_tables = [table for table in db_tables if table not in model_tables]

        # 檢查每個表的列
        column_diffs = {}
        for table_name in [t for t in model_tables if t in db_tables]:
            # 獲取資料庫中的列
            db_columns = {col["name"]: col for col in inspector.get_columns(table_name)}

            # 獲取模型定義的列
            model_columns = {
                col.name: col for col in Base.metadata.tables[table_name].columns
            }

            # 比較列
            missing_columns = [
                col_name for col_name in model_columns if col_name not in db_columns
            ]
            extra_columns = [
                col_name for col_name in db_columns if col_name not in model_columns
            ]

            if missing_columns or extra_columns:
                column_diffs[table_name] = {
                    "missing_columns": missing_columns,
                    "extra_columns": extra_columns,
                }

        return {
            "missing_tables": missing_tables,
            "extra_tables": extra_tables,
            "column_diffs": column_diffs,
            "is_consistent": not (missing_tables or extra_tables or column_diffs),
        }

    def apply_migration(self, migration_script: str) -> bool:
        """
        應用資料庫遷移腳本

        Args:
            migration_script: SQL 遷移腳本

        Returns:
            bool: 是否成功
        """
        try:
            # 執行遷移腳本
            self.session.execute(text(migration_script))
            self.session.commit()

            logger.info("成功應用資料庫遷移腳本")
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"應用資料庫遷移腳本時發生錯誤: {e}")
            return False

    def generate_migration_script(self, comparison_result: Dict[str, Any]) -> str:
        """
        生成遷移腳本

        根據比較結果生成 SQL 遷移腳本。

        Args:
            comparison_result: 比較結果

        Returns:
            str: SQL 遷移腳本
        """
        migration_script = []

        # 添加缺失的表
        for table_name in comparison_result.get("missing_tables", []):
            table = Base.metadata.tables[table_name]
            create_table_stmt = (
                str(table.create(bind=self.session.bind).compile()).strip() + ";"
            )
            migration_script.append(create_table_stmt)

        # 添加缺失的列
        for table_name, diffs in comparison_result.get("column_diffs", {}).items():
            for col_name in diffs.get("missing_columns", []):
                col = Base.metadata.tables[table_name].columns[col_name]
                col_type = col.type.compile(dialect=self.session.bind.dialect)
                nullable = "NULL" if col.nullable else "NOT NULL"
                default = f"DEFAULT {col.default.arg}" if col.default else ""

                alter_table_stmt = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} {nullable} {default};"
                migration_script.append(alter_table_stmt)

        return "\n".join(migration_script)

    def track_data_change(
        self,
        table_name: str,
        record_id: int,
        changes: Dict[str, Any],
        user: str = "system",
    ) -> None:
        """
        追蹤資料變更

        記錄重要資料的變更歷史。

        Args:
            table_name: 資料表名稱
            record_id: 記錄 ID
            changes: 變更內容
            user: 變更者
        """
        # 將變更內容轉換為 JSON 字串，使用自定義編碼器處理日期和時間
        details_json = json.dumps(
            {
                "table": table_name,
                "record_id": record_id,
                "changes": changes,
                "user": user,
            },
            cls=CustomJSONEncoder,
        )
        details_dict = json.loads(details_json)

        # 創建日誌記錄
        log_entry = SystemLog(
            timestamp=datetime.now(),
            level="INFO",
            module="data_versioning",
            message=f"資料變更: {table_name} ID={record_id}",
            details=details_dict,
        )

        # 添加到資料庫
        self.session.add(log_entry)
        self.session.commit()

        logger.info(f"已記錄資料變更: {table_name} ID={record_id}")

    def get_change_history(
        self,
        table_name: Optional[str] = None,
        record_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        獲取變更歷史

        Args:
            table_name: 資料表名稱，如果為 None 則獲取所有表的變更
            record_id: 記錄 ID，如果為 None 則獲取所有記錄的變更
            start_date: 開始日期，如果為 None 則不限制開始日期
            end_date: 結束日期，如果為 None 則不限制結束日期

        Returns:
            List[Dict[str, Any]]: 變更歷史記錄列表
        """
        # 構建查詢
        query = self.session.query(SystemLog).filter(
            SystemLog.module == "data_versioning"
        )

        # 添加過濾條件
        if table_name:
            # 對於 SQLite，我們需要使用 JSON 字串匹配
            # 這裡使用簡單的 LIKE 查詢來模擬 JSON 查詢
            query = query.filter(SystemLog.message.like(f"資料變更: {table_name} ID=%"))

        if record_id:
            query = query.filter(SystemLog.message.like(f"資料變更: % ID={record_id}"))

        if start_date:
            query = query.filter(func.date(SystemLog.timestamp) >= start_date)

        if end_date:
            query = query.filter(func.date(SystemLog.timestamp) <= end_date)

        # 執行查詢
        logs = query.order_by(SystemLog.timestamp).all()

        # 格式化結果
        history = []
        for log in logs:
            history.append(
                {
                    "id": log.id,
                    "timestamp": log.timestamp.isoformat(),
                    "table": log.details.get("table"),
                    "record_id": log.details.get("record_id"),
                    "changes": log.details.get("changes"),
                    "user": log.details.get("user"),
                }
            )

        return history

    def calculate_schema_hash(self) -> str:
        """
        計算資料庫結構的雜湊值

        用於快速比較資料庫結構是否有變化。

        Returns:
            str: 資料庫結構的雜湊值
        """
        inspector = inspect(self.session.bind)

        # 獲取資料庫中的表
        db_tables = inspector.get_table_names()

        # 構建結構描述
        schema_desc = {}
        for table_name in db_tables:
            # 獲取列
            columns = inspector.get_columns(table_name)
            col_desc = {
                col["name"]: {
                    "type": str(col["type"]),
                    "nullable": col["nullable"],
                    "default": str(col["default"]) if col["default"] else None,
                }
                for col in columns
            }

            # 獲取索引
            indexes = inspector.get_indexes(table_name)
            idx_desc = {
                idx["name"]: {
                    "columns": idx["column_names"],
                    "unique": idx["unique"],
                }
                for idx in indexes
            }

            # 獲取主鍵
            pk = inspector.get_pk_constraint(table_name)

            # 獲取外鍵
            fks = inspector.get_foreign_keys(table_name)

            schema_desc[table_name] = {
                "columns": col_desc,
                "indexes": idx_desc,
                "primary_key": pk,
                "foreign_keys": fks,
            }

        # 計算雜湊值
        schema_json = json.dumps(schema_desc, sort_keys=True)
        return hashlib.sha256(schema_json.encode()).hexdigest()

    def is_schema_changed(self) -> bool:
        """
        檢查資料庫結構是否有變化

        Returns:
            bool: 是否有變化
        """
        # 計算當前結構的雜湊值
        current_hash = self.calculate_schema_hash()

        # 獲取最新的版本記錄
        version_record = (
            self.session.query(DatabaseVersion)
            .order_by(DatabaseVersion.id.desc())
            .first()
        )

        if not version_record or "schema_hash" not in version_record.changes:
            # 如果沒有版本記錄或沒有結構雜湊值，則視為有變化
            return True

        # 比較雜湊值
        return current_hash != version_record.changes["schema_hash"]
