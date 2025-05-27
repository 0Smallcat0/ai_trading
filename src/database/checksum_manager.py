# -*- coding: utf-8 -*-
"""
校驗碼管理模組

此模組提供完整的資料完整性驗證功能，包括：
- 自動校驗碼生成
- 定期完整性檢查
- 資料損壞檢測
- 修復建議

主要功能：
- SHA-256 校驗碼計算
- 批量完整性驗證
- 自動修復機制
- 完整性報告生成

Example:
    >>> from src.database.checksum_manager import ChecksumManager
    >>> manager = ChecksumManager(session)
    >>> checksum_record = manager.create_checksum_record(MarketDaily, record_id, "market_daily_standard")
"""

import hashlib
import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from src.database.schema import (
    DataChecksum,
    MarketDaily,
    MarketMinute,
    MarketTick,
    DataShard,
)

logger = logging.getLogger(__name__)


class ChecksumError(Exception):
    """校驗碼操作相關的異常類別."""

    pass


class ChecksumConfigError(ChecksumError):
    """校驗碼配置錯誤."""

    pass


class ChecksumOperationError(ChecksumError):
    """校驗碼操作錯誤."""

    pass


class ChecksumStrategy(ABC):
    """校驗策略抽象基類.

    定義校驗策略的通用介面，所有具體的校驗策略都必須實現此介面。

    Attributes:
        name: 策略名稱
        fields: 參與校驗的欄位列表
    """

    def __init__(self, name: str, fields: List[str]) -> None:
        """初始化校驗策略.

        Args:
            name: 策略名稱
            fields: 參與校驗的欄位列表

        Raises:
            ChecksumConfigError: 當策略名稱或欄位列表無效時
        """
        if not name or not name.strip():
            raise ChecksumConfigError("策略名稱不能為空")
        if not fields or not isinstance(fields, list):
            raise ChecksumConfigError("欄位列表不能為空且必須是列表類型")
        if not all(isinstance(field, str) and field.strip() for field in fields):
            raise ChecksumConfigError("所有欄位名稱必須是非空字串")

        self.name = name.strip()
        self.fields = [field.strip() for field in fields]

    @abstractmethod
    def should_verify(self, record_age_days: int, last_verified_days: int) -> bool:
        """判斷是否需要驗證.

        Args:
            record_age_days: 記錄年齡（天）
            last_verified_days: 上次驗證距今天數

        Returns:
            bool: 是否需要驗證

        Raises:
            ChecksumOperationError: 當判斷過程中發生錯誤時
        """
        pass


class TimeBasedChecksumStrategy(ChecksumStrategy):
    """基於時間的校驗策略.

    根據驗證間隔決定是否需要重新驗證，適用於定期校驗的場景。

    Attributes:
        verify_interval_days: 驗證間隔（天）
    """

    def __init__(self, fields: List[str], verify_interval_days: int = 7) -> None:
        """初始化時間校驗策略.

        Args:
            fields: 參與校驗的欄位列表
            verify_interval_days: 驗證間隔（天），必須大於 0

        Raises:
            ChecksumConfigError: 當驗證間隔無效時
        """
        super().__init__("time_based", fields)
        if verify_interval_days <= 0:
            raise ChecksumConfigError("驗證間隔必須大於 0")
        self.verify_interval_days = verify_interval_days

    def should_verify(self, record_age_days: int, last_verified_days: int) -> bool:
        """判斷是否需要基於時間驗證.

        Args:
            record_age_days: 記錄年齡（天）- 此策略不使用此參數
            last_verified_days: 上次驗證距今天數

        Returns:
            bool: 是否需要驗證
        """
        # 忽略 record_age_days 參數，僅基於驗證間隔判斷
        return last_verified_days >= self.verify_interval_days


class CriticalDataChecksumStrategy(ChecksumStrategy):
    """關鍵資料校驗策略.

    針對關鍵資料提供更頻繁的驗證，確保重要資料的完整性。

    Attributes:
        verify_interval_days: 驗證間隔（天）
    """

    def __init__(self, fields: List[str], verify_interval_days: int = 1) -> None:
        """初始化關鍵資料校驗策略.

        Args:
            fields: 參與校驗的欄位列表
            verify_interval_days: 驗證間隔（天），必須大於 0

        Raises:
            ChecksumConfigError: 當驗證間隔無效時
        """
        super().__init__("critical_data", fields)
        if verify_interval_days <= 0:
            raise ChecksumConfigError("驗證間隔必須大於 0")
        self.verify_interval_days = verify_interval_days

    def should_verify(self, record_age_days: int, last_verified_days: int) -> bool:
        """判斷關鍵資料是否需要驗證.

        Args:
            record_age_days: 記錄年齡（天）- 此策略不使用此參數
            last_verified_days: 上次驗證距今天數

        Returns:
            bool: 是否需要驗證
        """
        # 忽略 record_age_days 參數，僅基於驗證間隔判斷
        return last_verified_days >= self.verify_interval_days


class ChecksumManager:
    """校驗碼管理器.

    提供完整的資料完整性管理功能，包括自動校驗、定期檢查、損壞檢測等。

    Attributes:
        session: SQLAlchemy 會話
        strategies: 已註冊的校驗策略
        verification_stats: 驗證統計資訊
        lock: 執行緒鎖
    """

    def __init__(self, session: Session) -> None:
        """初始化校驗碼管理器.

        Args:
            session: SQLAlchemy 會話

        Raises:
            ChecksumConfigError: 當會話無效時
        """
        if session is None:
            raise ChecksumConfigError("SQLAlchemy 會話不能為 None")

        self.session = session
        self.strategies: Dict[str, ChecksumStrategy] = {}
        self.verification_stats: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

        # 註冊預設校驗策略
        self._register_default_strategies()

        logger.info("校驗碼管理器初始化完成")

    def _register_default_strategies(self) -> None:
        """註冊預設校驗策略."""
        try:
            # 市場資料校驗策略
            market_fields = ["symbol", "open", "high", "low", "close", "volume"]

            self.register_strategy(
                "market_daily_standard",
                TimeBasedChecksumStrategy(market_fields + ["date"], 7),
            )

            self.register_strategy(
                "market_minute_standard",
                TimeBasedChecksumStrategy(market_fields + ["timestamp"], 3),
            )

            self.register_strategy(
                "market_tick_critical",
                CriticalDataChecksumStrategy(market_fields + ["timestamp"], 1),
            )
        except Exception as e:
            logger.error(f"註冊預設策略失敗: {e}")
            raise ChecksumConfigError(f"註冊預設策略失敗: {e}") from e

    def register_strategy(self, name: str, strategy: ChecksumStrategy) -> None:
        """註冊校驗策略.

        Args:
            name: 策略名稱
            strategy: 校驗策略實例

        Raises:
            ChecksumConfigError: 當策略名稱或實例無效時
        """
        if not name or not name.strip():
            raise ChecksumConfigError("策略名稱不能為空")
        if not isinstance(strategy, ChecksumStrategy):
            raise ChecksumConfigError("策略必須是 ChecksumStrategy 的實例")

        with self.lock:
            self.strategies[name.strip()] = strategy
            logger.info(f"註冊校驗策略: {name}")

    def generate_checksum_for_record(self, record: Any, fields: List[str]) -> str:
        """為記錄生成校驗碼.

        Args:
            record: 資料記錄
            fields: 參與校驗的欄位

        Returns:
            str: SHA-256 校驗碼

        Raises:
            ChecksumConfigError: 當欄位列表無效時
            ChecksumOperationError: 當生成校驗碼過程中發生錯誤時
        """
        if not fields:
            raise ChecksumConfigError("欄位列表不能為空")
        if record is None:
            raise ChecksumConfigError("記錄不能為 None")

        try:
            # 構建用於校驗的資料字典
            data = self._extract_record_data(record, fields)

            # 將資料轉換為 JSON 字串並計算 SHA-256 校驗碼
            json_str = json.dumps(data, sort_keys=True)
            return hashlib.sha256(json_str.encode()).hexdigest()

        except (ChecksumConfigError, ChecksumOperationError):
            raise
        except Exception as e:
            raise ChecksumOperationError(f"生成校驗碼時發生錯誤: {e}") from e

    def _extract_record_data(self, record: Any, fields: List[str]) -> Dict[str, Any]:
        """從記錄中提取指定欄位的資料."""
        data: Dict[str, Any] = {}

        for field in fields:
            if not hasattr(record, field):
                logger.warning(f"記錄缺少欄位: {field}")
                continue

            value = getattr(record, field)

            # 處理日期和時間類型
            if isinstance(value, (date, datetime)):
                value = value.isoformat()
            # 處理浮點數精度問題
            elif isinstance(value, float):
                value = round(value, 8)
            # 處理 None 值
            elif value is None:
                value = "NULL"

            data[field] = value

        return data

    def create_checksum_record(
        self,
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
        record_id: int,
        strategy_name: str,
    ) -> DataChecksum:
        """創建校驗記錄.

        Args:
            table_class: 資料表類別
            record_id: 記錄 ID
            strategy_name: 校驗策略名稱

        Returns:
            DataChecksum: 校驗記錄

        Raises:
            ChecksumConfigError: 當策略不存在或參數無效時
            ChecksumOperationError: 當創建過程中發生錯誤時
        """
        if strategy_name not in self.strategies:
            raise ChecksumConfigError(f"未知的校驗策略: {strategy_name}")

        if record_id <= 0:
            raise ChecksumConfigError("記錄 ID 必須大於 0")

        try:
            strategy = self.strategies[strategy_name]

            # 查詢記錄
            record = self.session.query(table_class).filter_by(id=record_id).first()
            if not record:
                raise ChecksumOperationError(
                    f"找不到記錄: {table_class.__tablename__} ID={record_id}"
                )

            # 生成校驗碼
            checksum = self.generate_checksum_for_record(record, strategy.fields)

            # 創建校驗記錄
            checksum_record = DataChecksum(
                table_name=table_class.__tablename__,
                record_id=record_id,
                checksum=checksum,
                checksum_fields=strategy.fields,
                is_valid=True,
                verified_at=datetime.now(timezone.utc),
            )

            self.session.add(checksum_record)
            self.session.commit()

            logger.debug(f"創建校驗記錄: {table_class.__tablename__} ID={record_id}")
            return checksum_record

        except (ChecksumConfigError, ChecksumOperationError):
            raise
        except Exception as e:
            raise ChecksumOperationError(f"創建校驗記錄時發生錯誤: {e}") from e

    def verify_record_integrity(
        self,
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
        record_id: int,
    ) -> Dict[str, Any]:
        """驗證記錄完整性.

        Args:
            table_class: 資料表類別
            record_id: 記錄 ID

        Returns:
            Dict[str, Any]: 驗證結果

        Raises:
            ChecksumConfigError: 當參數無效時
            ChecksumOperationError: 當驗證過程中發生錯誤時
        """
        if record_id <= 0:
            raise ChecksumConfigError("記錄 ID 必須大於 0")

        try:
            # 查詢記錄
            record = self.session.query(table_class).filter_by(id=record_id).first()
            if not record:
                return {
                    "is_valid": False,
                    "error": f"找不到記錄: {table_class.__tablename__} ID={record_id}",
                    "record_id": record_id,
                }

            # 查詢校驗記錄
            checksum_record = self._get_checksum_record(table_class, record_id)
            if not checksum_record:
                return {
                    "is_valid": False,
                    "error": f"找不到校驗記錄: {table_class.__tablename__} ID={record_id}",
                    "record_id": record_id,
                }

            # 計算當前校驗碼
            current_checksum = self.generate_checksum_for_record(
                record, checksum_record.checksum_fields
            )

            # 比較校驗碼
            is_valid = current_checksum == checksum_record.checksum

            result = {
                "is_valid": is_valid,
                "record_id": record_id,
                "table_name": table_class.__tablename__,
                "stored_checksum": checksum_record.checksum,
                "current_checksum": current_checksum,
                "checksum_fields": checksum_record.checksum_fields,
                "verified_at": datetime.now(timezone.utc),
            }

            # 更新校驗記錄
            self._update_checksum_record(
                checksum_record, result["verified_at"], is_valid
            )

            if not is_valid:
                logger.warning(
                    f"資料完整性驗證失敗: {table_class.__tablename__} ID={record_id}"
                )

            return result

        except (ChecksumConfigError, ChecksumOperationError):
            raise
        except Exception as e:
            raise ChecksumOperationError(f"驗證記錄完整性時發生錯誤: {e}") from e

    def _get_checksum_record(
        self,
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
        record_id: int,
    ) -> Optional[DataChecksum]:
        """獲取校驗記錄."""
        return (
            self.session.query(DataChecksum)
            .filter_by(table_name=table_class.__tablename__, record_id=record_id)
            .first()
        )

    def _update_checksum_record(
        self, checksum_record: DataChecksum, verified_at: datetime, is_valid: bool
    ) -> None:
        """更新校驗記錄."""
        checksum_record.verified_at = verified_at
        checksum_record.is_valid = is_valid
        self.session.commit()

    def batch_verify_integrity(
        self,
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
        strategy_name: str,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """批量驗證完整性.

        Args:
            table_class: 資料表類別
            strategy_name: 校驗策略名稱
            limit: 限制驗證數量

        Returns:
            Dict[str, Any]: 批量驗證結果

        Raises:
            ChecksumConfigError: 當策略不存在或參數無效時
            ChecksumOperationError: 當批量驗證過程中發生錯誤時
        """
        if strategy_name not in self.strategies:
            raise ChecksumConfigError(f"未知的校驗策略: {strategy_name}")

        if limit is not None and limit <= 0:
            raise ChecksumConfigError("限制數量必須大於 0")

        try:
            strategy = self.strategies[strategy_name]
            start_time = time.time()

            # 獲取需要驗證的記錄 ID 列表
            records_to_verify = self._get_records_to_verify(
                table_class, strategy, limit
            )

            # 執行批量驗證
            results = self._execute_batch_verification(table_class, records_to_verify)
            results["verification_time"] = time.time() - start_time

            logger.info(
                f"批量驗證完成: {table_class.__tablename__}, "
                f"檢查 {results['total_checked']} 筆記錄, "
                f"有效 {results['valid_records']} 筆, "
                f"無效 {results['invalid_records']} 筆"
            )

            return results

        except (ChecksumConfigError, ChecksumOperationError):
            raise
        except Exception as e:
            raise ChecksumOperationError(f"批量驗證完整性時發生錯誤: {e}") from e

    def _get_records_to_verify(
        self,
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
        strategy: ChecksumStrategy,
        limit: Optional[int],
    ) -> List[int]:
        """獲取需要驗證的記錄 ID 列表."""
        query = self.session.query(DataChecksum).filter_by(
            table_name=table_class.__tablename__
        )

        now = datetime.now(timezone.utc)
        records_to_verify = []

        for checksum_record in query.all():
            # 計算記錄年齡和上次驗證時間
            if checksum_record.verified_at:
                last_verified_days = (now - checksum_record.verified_at).days
            else:
                last_verified_days = float("inf")

            # 假設記錄年齡為創建時間到現在的天數
            if checksum_record.created_at:
                record_age_days = (now - checksum_record.created_at).days
            else:
                record_age_days = 0

            if strategy.should_verify(record_age_days, last_verified_days):
                records_to_verify.append(checksum_record.record_id)

                if limit and len(records_to_verify) >= limit:
                    break

        return records_to_verify

    def _execute_batch_verification(
        self,
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
        records_to_verify: List[int],
    ) -> Dict[str, Any]:
        """執行批量驗證."""
        results: Dict[str, Any] = {
            "total_checked": 0,
            "valid_records": 0,
            "invalid_records": 0,
            "errors": 0,
            "verification_time": 0,
            "invalid_record_ids": [],
            "error_details": [],
        }

        for record_id in records_to_verify:
            try:
                result = self.verify_record_integrity(table_class, record_id)
                results["total_checked"] += 1

                if result["is_valid"]:
                    results["valid_records"] += 1
                else:
                    results["invalid_records"] += 1
                    results["invalid_record_ids"].append(record_id)

            except Exception as e:
                results["errors"] += 1
                results["error_details"].append(
                    {"record_id": record_id, "error": str(e)}
                )
                logger.error(f"驗證記錄 {record_id} 時發生錯誤: {e}")

        return results

    def auto_create_checksums(
        self,
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
        strategy_name: str,
        batch_size: int = 1000,
    ) -> Dict[str, Any]:
        """自動為記錄創建校驗碼.

        Args:
            table_class: 資料表類別
            strategy_name: 校驗策略名稱
            batch_size: 批次大小

        Returns:
            Dict[str, Any]: 創建結果統計

        Raises:
            ChecksumConfigError: 當策略不存在或參數無效時
            ChecksumOperationError: 當創建過程中發生錯誤時
        """
        if strategy_name not in self.strategies:
            raise ChecksumConfigError(f"未知的校驗策略: {strategy_name}")

        if batch_size <= 0:
            raise ChecksumConfigError("批次大小必須大於 0")

        try:
            start_time = time.time()

            # 查詢沒有校驗記錄的資料
            records_without_checksum = self._get_records_without_checksum(
                table_class, batch_size
            )

            # 執行批量創建
            results = self._execute_batch_creation(
                table_class, strategy_name, records_without_checksum
            )
            results["processing_time"] = time.time() - start_time

            logger.info(
                f"自動創建校驗碼完成: {table_class.__tablename__}, "
                f"處理 {results['total_processed']} 筆記錄, "
                f"成功 {results['successful_creates']} 筆"
            )

            return results

        except (ChecksumConfigError, ChecksumOperationError):
            raise
        except Exception as e:
            raise ChecksumOperationError(f"自動創建校驗碼時發生錯誤: {e}") from e

    def _get_records_without_checksum(
        self,
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
        batch_size: int,
    ) -> List[Tuple[int]]:
        """獲取沒有校驗記錄的資料."""
        existing_checksums = (
            self.session.query(DataChecksum.record_id)
            .filter_by(table_name=table_class.__tablename__)
            .subquery()
        )

        return (
            self.session.query(table_class.id)
            .filter(~table_class.id.in_(select(existing_checksums.c.record_id)))
            .limit(batch_size)
            .all()
        )

    def _execute_batch_creation(
        self,
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
        strategy_name: str,
        records_without_checksum: List[Tuple[int]],
    ) -> Dict[str, Any]:
        """執行批量創建校驗碼."""
        results: Dict[str, Any] = {
            "total_processed": 0,
            "successful_creates": 0,
            "errors": 0,
            "processing_time": 0,
            "error_details": [],
        }

        for (record_id,) in records_without_checksum:
            try:
                self.create_checksum_record(table_class, record_id, strategy_name)
                results["successful_creates"] += 1
            except Exception as e:
                results["errors"] += 1
                results["error_details"].append(
                    {"record_id": record_id, "error": str(e)}
                )
                logger.error(f"為記錄 {record_id} 創建校驗碼時發生錯誤: {e}")

            results["total_processed"] += 1

        return results

    def get_integrity_report(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """獲取完整性報告.

        Args:
            table_name: 資料表名稱，如果為 None 則返回所有表的報告

        Returns:
            Dict[str, Any]: 完整性報告

        Raises:
            ChecksumOperationError: 當獲取報告過程中發生錯誤時
        """
        try:
            query = self.session.query(DataChecksum)

            if table_name:
                query = query.filter_by(table_name=table_name)

            all_checksums = query.all()

            report = self._initialize_report(len(all_checksums))
            now = datetime.now(timezone.utc)

            for checksum in all_checksums:
                self._update_report_statistics(report, checksum, now)

            # 計算完整性百分比
            self._calculate_integrity_percentage(report)

            return report

        except Exception as e:
            raise ChecksumOperationError(f"獲取完整性報告時發生錯誤: {e}") from e

    def _initialize_report(self, total_records: int) -> Dict[str, Any]:
        """初始化報告結構."""
        return {
            "total_records": total_records,
            "valid_records": 0,
            "invalid_records": 0,
            "unverified_records": 0,
            "by_table": {},
            "verification_age_distribution": {
                "within_1_day": 0,
                "within_1_week": 0,
                "within_1_month": 0,
                "older_than_1_month": 0,
                "never_verified": 0,
            },
        }

    def _update_report_statistics(
        self, report: Dict[str, Any], checksum: DataChecksum, now: datetime
    ) -> None:
        """更新報告統計資訊."""
        table = checksum.table_name

        # 初始化表統計
        if table not in report["by_table"]:
            report["by_table"][table] = {
                "total": 0,
                "valid": 0,
                "invalid": 0,
                "unverified": 0,
            }

        report["by_table"][table]["total"] += 1

        # 統計驗證狀態
        if checksum.is_valid is None:
            report["unverified_records"] += 1
            report["by_table"][table]["unverified"] += 1
        elif checksum.is_valid:
            report["valid_records"] += 1
            report["by_table"][table]["valid"] += 1
        else:
            report["invalid_records"] += 1
            report["by_table"][table]["invalid"] += 1

        # 統計驗證年齡分佈
        self._update_age_distribution(report, checksum, now)

    def _update_age_distribution(
        self, report: Dict[str, Any], checksum: DataChecksum, now: datetime
    ) -> None:
        """更新驗證年齡分佈統計."""
        if checksum.verified_at:
            days_since_verification = (now - checksum.verified_at).days

            if days_since_verification <= 1:
                report["verification_age_distribution"]["within_1_day"] += 1
            elif days_since_verification <= 7:
                report["verification_age_distribution"]["within_1_week"] += 1
            elif days_since_verification <= 30:
                report["verification_age_distribution"]["within_1_month"] += 1
            else:
                report["verification_age_distribution"]["older_than_1_month"] += 1
        else:
            report["verification_age_distribution"]["never_verified"] += 1

    def _calculate_integrity_percentage(self, report: Dict[str, Any]) -> None:
        """計算完整性百分比."""
        if report["total_records"] > 0:
            report["integrity_percentage"] = (
                report["valid_records"] / report["total_records"] * 100
            )
        else:
            report["integrity_percentage"] = 100.0

    def schedule_integrity_check(
        self,
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
        strategy_name: str,
        check_interval_hours: int = 24,
    ) -> Dict[str, Any]:
        """排程完整性檢查.

        Args:
            table_class: 資料表類別
            strategy_name: 校驗策略名稱
            check_interval_hours: 檢查間隔（小時）

        Returns:
            Dict[str, Any]: 檢查配置資訊

        Raises:
            ChecksumConfigError: 當參數無效時

        Note:
            此方法僅返回檢查配置，實際的排程執行需要外部排程系統實現
        """
        if strategy_name not in self.strategies:
            raise ChecksumConfigError(f"未知的校驗策略: {strategy_name}")

        if check_interval_hours <= 0:
            raise ChecksumConfigError("檢查間隔必須大於 0")

        config = {
            "table_name": table_class.__tablename__,
            "strategy_name": strategy_name,
            "check_interval_hours": check_interval_hours,
            "next_check_time": datetime.now(timezone.utc),
            "status": "configured",
        }

        logger.info(
            f"配置完整性檢查排程: {table_class.__tablename__}, "
            f"策略: {strategy_name}, 間隔: {check_interval_hours} 小時"
        )

        return config
