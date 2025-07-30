"""
資料管道模組

此模組整合了資料擷取、驗證、儲存和備份等功能，
提供完整的資料處理流程。

主要功能：
- 資料擷取和轉換
- 資料驗證和清洗
- 資料儲存和備份
- 資料版本控制
"""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from src.utils.database_utils import get_database_manager


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
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient="records")
        elif hasattr(obj, "to_dict"):
            return obj.to_dict()
        return super().default(obj)


from src.config import DB_URL, LOG_LEVEL
from src.database.data_backup import DatabaseBackup
from src.database.data_validation import DataValidator
from src.database.data_versioning import DataVersionManager
from src.database.parquet_utils import create_market_data_shard, load_from_shard
from src.database.schema import DataChecksum, DataShard

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class DataPipeline:
    """
    資料管道類

    整合資料擷取、驗證、儲存和備份等功能，提供完整的資料處理流程。
    """

    def __init__(self, db_url: str = DB_URL):
        """
        初始化資料管道

        Args:
            db_url: 資料庫連接 URL
        """
        self.db_url = db_url

        # 使用統一的資料庫連接管理器
        self.db_manager = get_database_manager(db_url)
        self.engine = self.db_manager.get_engine()
        self.Session = self.db_manager.session_factory

        # 初始化資料驗證器、備份器和版本管理器
        self.session = self.Session()
        self.validator = DataValidator(self.session)
        self.backup = DatabaseBackup(db_url)
        self.version_manager = DataVersionManager(self.session)

        logger.info("資料管道初始化完成")

    def close(self):
        """
        關閉資料管道
        """
        if self.session:
            self.session.close()

        logger.info("資料管道已關閉")

    def ingest_data(
        self,
        data: pd.DataFrame,
        table_class,
        validate: bool = True,
        create_checksum: bool = True,
        backup: bool = False,
    ) -> Tuple[bool, List[int]]:
        """
        擷取資料

        將資料擷取到資料庫中，並進行驗證和備份。

        Args:
            data: 要擷取的資料
            table_class: 資料表類別
            validate: 是否驗證資料
            create_checksum: 是否創建校驗碼
            backup: 是否備份資料庫

        Returns:
            Tuple[bool, List[int]]: 是否成功和新增記錄的 ID 列表
        """
        if data.empty:
            logger.warning("擷取的資料為空")
            return False, []

        try:
            # 驗證資料
            if validate:
                # 檢查必要欄位
                required_fields = self._get_required_fields(table_class)
                missing_fields = [
                    field for field in required_fields if field not in data.columns
                ]
                if missing_fields:
                    logger.error(f"資料缺少必要欄位: {missing_fields}")
                    return False, []

                # 檢查資料類型
                invalid_types = self._check_data_types(data, table_class)
                if invalid_types:
                    logger.error(f"資料類型不正確: {invalid_types}")
                    return False, []

            # 轉換資料為記錄
            records = []
            for _, row in data.iterrows():
                record = table_class()
                for column in data.columns:
                    if hasattr(record, column):
                        setattr(record, column, row[column])

                # 設置校驗碼
                if create_checksum and hasattr(record, "checksum"):
                    checksum_fields = [
                        col.name
                        for col in table_class.__table__.columns
                        if col.name
                        not in ["id", "created_at", "updated_at", "checksum"]
                    ]
                    record_data = {
                        field: getattr(record, field)
                        for field in checksum_fields
                        if hasattr(record, field)
                    }
                    import hashlib
                    import json

                    json_str = json.dumps(record_data, sort_keys=True, default=str)
                    record.checksum = hashlib.sha256(json_str.encode()).hexdigest()

                records.append(record)

            # 添加到資料庫
            self.session.add_all(records)
            self.session.commit()

            # 獲取新增記錄的 ID
            record_ids = [record.id for record in records]

            # 創建校驗記錄
            if create_checksum:
                self._create_checksum_records(table_class.__tablename__, records)

            # 備份資料庫
            if backup:
                self.backup.create_backup()

            logger.info(f"成功擷取 {len(records)} 筆資料到 {table_class.__tablename__}")
            return True, record_ids
        except Exception as e:
            self.session.rollback()
            logger.error(f"擷取資料時發生錯誤: {e}")
            return False, []

    def validate_data_quality(
        self, table_class, symbol: str, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """
        驗證資料品質

        對指定時間範圍內的資料進行品質驗證。

        Args:
            table_class: 資料表類別
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            Dict[str, Any]: 驗證結果
        """
        # 驗證時間序列連續性
        continuity_result = self.validator.validate_time_series_continuity(
            table_class, symbol, start_date, end_date
        )

        # 檢查缺失值
        missing_result = self.validator.check_missing_values(
            table_class, symbol, start_date, end_date
        )

        # 檢測異常值
        outlier_result = self.validator.detect_outliers(
            table_class, symbol, start_date, end_date
        )

        # 綜合結果
        result = {
            "continuity": continuity_result,
            "missing_values": missing_result,
            "outliers": outlier_result,
            "overall_quality": self._calculate_overall_quality(
                continuity_result, missing_result, outlier_result
            ),
        }

        # 記錄驗證結果
        self.validator.log_validation_result("data_quality", result)

        return result

    def backup_data(self, backup_name: Optional[str] = None) -> str:
        """
        備份資料

        Args:
            backup_name: 備份名稱，如果未提供則使用時間戳

        Returns:
            str: 備份檔案路徑
        """
        return self.backup.create_backup(backup_name)

    def restore_data(self, backup_path: str) -> bool:
        """
        還原資料

        Args:
            backup_path: 備份檔案路徑

        Returns:
            bool: 是否成功
        """
        return self.backup.restore_backup(backup_path)

    def schedule_backup(self, interval: str = "daily") -> None:
        """
        排程備份

        Args:
            interval: 備份間隔，可選 "hourly"、"daily"、"weekly"
        """
        self.backup.schedule_backup(interval)

    def update_schema_version(
        self, version: str, description: str, changes: Dict[str, Any]
    ) -> None:
        """
        更新資料庫結構版本

        Args:
            version: 新版本號
            description: 版本描述
            changes: 變更內容
        """
        # 計算結構雜湊值
        schema_hash = self.version_manager.calculate_schema_hash()

        # 添加結構雜湊值到變更內容
        changes["schema_hash"] = schema_hash

        # 更新版本
        self.version_manager.update_version(version, description, changes)

    def check_schema_consistency(self) -> Dict[str, Any]:
        """
        檢查資料庫結構一致性

        檢查資料庫中的表結構是否與模型定義一致。

        Returns:
            Dict[str, Any]: 檢查結果
        """
        return self.version_manager.compare_schema_with_models()

    def track_data_change(
        self,
        table_name: str,
        record_id: int,
        changes: Dict[str, Any],
        user: str = "system",
    ) -> None:
        """
        追蹤資料變更

        Args:
            table_name: 資料表名稱
            record_id: 記錄 ID
            changes: 變更內容
            user: 變更者
        """
        self.version_manager.track_data_change(table_name, record_id, changes, user)

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
            table_name: 資料表名稱
            record_id: 記錄 ID
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            List[Dict[str, Any]]: 變更歷史記錄列表
        """
        return self.version_manager.get_change_history(
            table_name, record_id, start_date, end_date
        )

    def create_data_shard(
        self,
        table_class,
        start_date: date,
        end_date: date,
        symbols: Optional[List[str]] = None,
    ) -> Tuple[DataShard, str]:
        """
        創建資料分片

        將指定時間範圍內的資料分片並儲存為 Parquet 格式。

        Args:
            table_class: 資料表類別
            start_date: 開始日期
            end_date: 結束日期
            symbols: 股票代碼列表

        Returns:
            Tuple[DataShard, str]: 資料分片記錄和檔案路徑
        """
        return create_market_data_shard(
            self.session, table_class, start_date, end_date, symbols
        )

    def load_from_shard(
        self,
        shard_id: str,
        columns: Optional[List[str]] = None,
        filters: Optional[List] = None,
    ) -> pd.DataFrame:
        """
        從資料分片讀取資料

        Args:
            shard_id: 分片 ID
            columns: 要讀取的欄位
            filters: 過濾條件

        Returns:
            pd.DataFrame: 讀取的 DataFrame
        """
        return load_from_shard(self.session, shard_id, columns, filters)

    def _get_required_fields(self, table_class) -> List[str]:
        """
        獲取必要欄位

        Args:
            table_class: 資料表類別

        Returns:
            List[str]: 必要欄位列表
        """
        required_fields = []
        for column in table_class.__table__.columns:
            if (
                not column.nullable
                and not column.primary_key
                and column.default is None
            ):
                required_fields.append(column.name)
        return required_fields

    def _check_data_types(self, data: pd.DataFrame, table_class) -> Dict[str, str]:
        """
        檢查資料類型

        Args:
            data: 要檢查的資料
            table_class: 資料表類別

        Returns:
            Dict[str, str]: 類型不正確的欄位和預期類型
        """
        invalid_types = {}
        for column in table_class.__table__.columns:
            if column.name in data.columns:
                # 獲取列類型名稱
                type_name = column.type.__class__.__name__
                actual_type = data[column.name].dtype

                # 簡單類型檢查
                if type_name in [
                    "Integer",
                    "Float",
                    "Numeric",
                ] and not pd.api.types.is_numeric_dtype(actual_type):
                    invalid_types[column.name] = type_name
                elif type_name in [
                    "String",
                    "Text",
                    "Unicode",
                ] and not pd.api.types.is_string_dtype(actual_type):
                    invalid_types[column.name] = type_name
                elif type_name in [
                    "Date",
                    "DateTime",
                ] and not pd.api.types.is_datetime64_dtype(actual_type):
                    invalid_types[column.name] = type_name
                elif type_name == "Boolean" and not pd.api.types.is_bool_dtype(
                    actual_type
                ):
                    invalid_types[column.name] = type_name

        return invalid_types

    def _create_checksum_records(self, table_name: str, records: List[Any]) -> None:
        """
        創建校驗記錄

        Args:
            table_name: 資料表名稱
            records: 記錄列表
        """
        checksum_records = []
        for record in records:
            # 獲取參與校驗的欄位
            checksum_fields = [
                col.name
                for col in record.__table__.columns
                if col.name not in ["id", "created_at", "updated_at", "checksum"]
            ]

            # 創建校驗記錄
            checksum_record = DataChecksum(
                table_name=table_name,
                record_id=record.id,
                checksum=record.checksum if hasattr(record, "checksum") else "",
                checksum_fields=checksum_fields,
                is_valid=True,
            )

            checksum_records.append(checksum_record)

        # 添加到資料庫
        self.session.add_all(checksum_records)
        self.session.commit()

    def _calculate_overall_quality(
        self,
        continuity_result: Dict[str, Any],
        missing_result: Dict[str, Any],
        outlier_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        計算整體資料品質

        Args:
            continuity_result: 連續性驗證結果
            missing_result: 缺失值檢查結果
            outlier_result: 異常值檢測結果

        Returns:
            Dict[str, Any]: 整體品質評估
        """
        # 連續性分數
        continuity_score = continuity_result.get("continuity_score", 0.0)

        # 缺失值分數
        missing_percentage = (
            sum(missing_result.get("missing_percentages", {}).values())
            / len(missing_result.get("missing_percentages", {}))
            if missing_result.get("missing_percentages")
            else 0.0
        )
        missing_score = 1.0 - (missing_percentage / 100.0)

        # 異常值分數
        outlier_percentage = (
            sum(outlier_result.get("outlier_percentages", {}).values())
            / len(outlier_result.get("outlier_percentages", {}))
            if outlier_result.get("outlier_percentages")
            else 0.0
        )
        outlier_score = 1.0 - (outlier_percentage / 100.0)

        # 計算加權平均分數
        weights = {
            "continuity": 0.4,
            "missing": 0.3,
            "outlier": 0.3,
        }

        overall_score = (
            weights["continuity"] * continuity_score
            + weights["missing"] * missing_score
            + weights["outlier"] * outlier_score
        )

        # 品質等級
        if overall_score >= 0.9:
            quality_level = "優"
        elif overall_score >= 0.8:
            quality_level = "良"
        elif overall_score >= 0.7:
            quality_level = "中"
        elif overall_score >= 0.6:
            quality_level = "可"
        else:
            quality_level = "差"

        return {
            "overall_score": overall_score,
            "quality_level": quality_level,
            "component_scores": {
                "continuity": continuity_score,
                "missing": missing_score,
                "outlier": outlier_score,
            },
            "weights": weights,
        }
