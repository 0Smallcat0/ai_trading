# -*- coding: utf-8 -*-
"""
資料庫管理器整合模組

此模組整合所有資料庫管理功能，包括：
- 分片管理
- 壓縮管理
- 校驗碼管理
- 統一的資料庫操作介面

主要功能：
- 提供統一的資料庫管理介面
- 協調各個管理器之間的操作
- 自動化資料庫維護任務
- 效能監控和報告

Example:
    >>> from src.database.database_manager import DatabaseManager
    >>> manager = DatabaseManager(session)
    >>> status = manager.get_database_status()
    >>> maintenance_result = manager.perform_maintenance()
"""

import logging
import threading
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from sqlalchemy.orm import Session

from src.database.checksum_manager import ChecksumManager
from src.database.compression_manager import CompressionManager
from src.database.sharding_manager import ShardingManager
from src.database.schema import MarketDaily, MarketMinute, MarketTick

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """資料庫操作相關的異常類別."""

    pass


class DatabaseConfigError(DatabaseError):
    """資料庫配置錯誤."""

    pass


class DatabaseOperationError(DatabaseError):
    """資料庫操作錯誤."""

    pass


class DatabaseManager:
    """資料庫管理器.

    整合分片、壓縮、校驗等功能，提供統一的資料庫管理介面。

    Attributes:
        session: SQLAlchemy 會話
        sharding_manager: 分片管理器
        compression_manager: 壓縮管理器
        checksum_manager: 校驗碼管理器
        lock: 執行緒鎖
        maintenance_running: 維護任務運行狀態
        maintenance_thread: 維護任務執行緒
    """

    def __init__(self, session: Session) -> None:
        """初始化資料庫管理器.

        Args:
            session: SQLAlchemy 會話

        Raises:
            DatabaseConfigError: 當會話無效時
        """
        if session is None:
            raise DatabaseConfigError("SQLAlchemy 會話不能為 None")

        self.session = session
        self.lock = threading.Lock()

        # 初始化各個管理器
        try:
            self.sharding_manager = ShardingManager(session)
            self.compression_manager = CompressionManager(session)
            self.checksum_manager = ChecksumManager(session)
        except Exception as e:
            raise DatabaseConfigError(f"初始化子管理器失敗: {e}") from e

        # 維護任務狀態
        self.maintenance_running = False
        self.maintenance_thread: Optional[threading.Thread] = None

        logger.info("資料庫管理器初始化完成")

    def create_and_compress_shard(
        self,
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
        start_date: date,
        end_date: date,
        compression_type: str = "snappy",
        symbols: Optional[List[str]] = None,
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """創建分片並立即壓縮.

        Args:
            table_class: 資料表類別
            start_date: 開始日期
            end_date: 結束日期
            compression_type: 壓縮類型
            symbols: 股票代碼列表

        Returns:
            Tuple[Optional[str], Dict[str, Any]]: 分片檔案路徑和操作統計

        Raises:
            DatabaseConfigError: 當參數無效時
            DatabaseOperationError: 當操作過程中發生錯誤時
        """
        if start_date > end_date:
            raise DatabaseConfigError("開始日期不能大於結束日期")

        with self.lock:
            try:
                # 創建分片
                shard_result = self.sharding_manager.create_shard_if_needed(
                    table_class, "time_based", symbols
                )

                if not shard_result:
                    return None, {"status": "no_shard_needed"}

                shard, shard_path = shard_result

                # 壓縮資料
                compressed_path, compression_stats = self._compress_shard_data(
                    table_class, start_date, end_date, compression_type, symbols
                )

                # 更新分片記錄
                if compressed_path:
                    self._update_shard_record(
                        shard, compressed_path, compression_type, compression_stats
                    )

                # 為新分片的資料創建校驗碼
                self._create_checksums_for_date_range(
                    table_class, start_date, end_date, symbols
                )

                result_stats = {
                    "status": "success",
                    "shard_id": shard.shard_id,
                    "shard_path": shard_path,
                    "compressed_path": compressed_path,
                    "compression_stats": compression_stats,
                }

                logger.info(f"成功創建並壓縮分片: {shard.shard_id}")
                return compressed_path, result_stats

            except (DatabaseConfigError, DatabaseOperationError):
                raise
            except Exception as e:
                raise DatabaseOperationError(f"創建並壓縮分片時發生錯誤: {e}") from e

    def _compress_shard_data(
        self,
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
        start_date: date,
        end_date: date,
        compression_type: str,
        symbols: Optional[List[str]],
    ) -> Tuple[str, Dict[str, Any]]:
        """壓縮分片資料."""
        return self.compression_manager.compress_table_data(
            table_class, start_date, end_date, compression_type, symbols
        )

    def _update_shard_record(
        self,
        shard: Any,
        compressed_path: str,
        compression_type: str,
        compression_stats: Dict[str, Any],
    ) -> None:
        """更新分片記錄."""
        shard.file_path = compressed_path
        shard.compression = compression_type
        shard.is_compressed = True
        shard.file_size_bytes = compression_stats.get("compressed_size_bytes", 0)
        self.session.commit()

    def _create_checksums_for_date_range(
        self,
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
        start_date: date,
        end_date: date,
        symbols: Optional[List[str]] = None,
    ) -> None:
        """為指定日期範圍的資料創建校驗碼.

        Args:
            table_class: 資料表類別
            start_date: 開始日期 (目前未使用，保留供未來擴展)
            end_date: 結束日期 (目前未使用，保留供未來擴展)
            symbols: 股票代碼列表 (目前未使用，保留供未來擴展)

        Note:
            目前實現為批量創建校驗碼，未來可擴展為針對特定日期範圍
        """
        try:
            # 根據表類別選擇校驗策略
            strategy_name = self._get_checksum_strategy_name(table_class)

            # 自動創建校驗碼
            result = self.checksum_manager.auto_create_checksums(
                table_class, strategy_name, batch_size=1000
            )

            logger.info(
                f"為 {table_class.__tablename__} 創建校驗碼: "
                f"成功 {result['successful_creates']} 筆"
            )

        except Exception as e:
            logger.error(f"創建校驗碼時發生錯誤: {e}")

    def _get_checksum_strategy_name(
        self, table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]]
    ) -> str:
        """根據表類別獲取校驗策略名稱."""
        strategy_mapping = {
            MarketDaily: "market_daily_standard",
            MarketMinute: "market_minute_standard",
            MarketTick: "market_tick_critical",
        }

        strategy_name = strategy_mapping.get(table_class)
        if not strategy_name:
            raise DatabaseConfigError(f"未知的表類別: {table_class}")

        return strategy_name

    def perform_maintenance(
        self,
        auto_shard: bool = True,
        auto_compress: bool = True,
        verify_integrity: bool = True,
    ) -> Dict[str, Any]:
        """執行資料庫維護任務.

        Args:
            auto_shard: 是否自動創建分片
            auto_compress: 是否自動壓縮
            verify_integrity: 是否驗證完整性

        Returns:
            Dict[str, Any]: 維護結果統計

        Raises:
            DatabaseOperationError: 當維護過程中發生嚴重錯誤時
        """
        maintenance_stats = self._initialize_maintenance_stats()

        try:
            # 自動分片
            if auto_shard:
                self._perform_auto_sharding(maintenance_stats)

            # 自動壓縮
            if auto_compress:
                self._perform_auto_compression(maintenance_stats)

            # 完整性檢查
            if verify_integrity:
                self._perform_integrity_check(maintenance_stats)

            # 完成維護統計
            self._finalize_maintenance_stats(maintenance_stats)

        except Exception as e:
            error_msg = f"資料庫維護時發生未預期錯誤: {e}"
            maintenance_stats["errors"].append(error_msg)
            logger.error(error_msg)

        return maintenance_stats

    def _initialize_maintenance_stats(self) -> Dict[str, Any]:
        """初始化維護統計."""
        return {
            "start_time": datetime.now(),
            "auto_shard_results": {},
            "auto_compress_results": {},
            "integrity_check_results": {},
            "errors": [],
        }

    def _perform_auto_sharding(self, maintenance_stats: Dict[str, Any]) -> None:
        """執行自動分片任務."""
        logger.info("開始自動分片任務")
        for table_class in [MarketDaily, MarketMinute, MarketTick]:
            try:
                result = self.sharding_manager.create_shard_if_needed(
                    table_class, "time_based"
                )
                maintenance_stats["auto_shard_results"][table_class.__tablename__] = {
                    "created": result is not None,
                    "shard_id": result[0].shard_id if result else None,
                }
            except Exception as e:
                error_msg = f"自動分片失敗 {table_class.__tablename__}: {e}"
                maintenance_stats["errors"].append(error_msg)
                logger.error(error_msg)

    def _perform_auto_compression(self, maintenance_stats: Dict[str, Any]) -> None:
        """執行自動壓縮任務."""
        logger.info("開始自動壓縮任務")
        try:
            compress_results = self.compression_manager.auto_compress_old_data(
                "time_based_snappy", dry_run=False
            )
            maintenance_stats["auto_compress_results"] = {
                "processed_shards": len(compress_results),
                "compressed_count": len(
                    [r for r in compress_results if r["status"] == "compressed"]
                ),
                "error_count": len(
                    [r for r in compress_results if r["status"] == "error"]
                ),
            }
        except Exception as e:
            error_msg = f"自動壓縮失敗: {e}"
            maintenance_stats["errors"].append(error_msg)
            logger.error(error_msg)

    def _perform_integrity_check(self, maintenance_stats: Dict[str, Any]) -> None:
        """執行完整性檢查任務."""
        logger.info("開始完整性檢查任務")
        for table_class in [MarketDaily, MarketMinute, MarketTick]:
            try:
                strategy_name = self._get_checksum_strategy_name(table_class)
                result = self.checksum_manager.batch_verify_integrity(
                    table_class, strategy_name, limit=100
                )
                maintenance_stats["integrity_check_results"][
                    table_class.__tablename__
                ] = result

            except Exception as e:
                error_msg = f"完整性檢查失敗 {table_class.__tablename__}: {e}"
                maintenance_stats["errors"].append(error_msg)
                logger.error(error_msg)

    def _finalize_maintenance_stats(self, maintenance_stats: Dict[str, Any]) -> None:
        """完成維護統計."""
        maintenance_stats["end_time"] = datetime.now()
        maintenance_stats["duration_seconds"] = (
            maintenance_stats["end_time"] - maintenance_stats["start_time"]
        ).total_seconds()

        logger.info(
            f"資料庫維護完成，耗時 {maintenance_stats['duration_seconds']:.2f} 秒"
        )

    def start_scheduled_maintenance(
        self,
        interval_hours: int = 24,
        auto_shard: bool = True,
        auto_compress: bool = True,
        verify_integrity: bool = True,
    ) -> Dict[str, Any]:
        """啟動排程維護任務.

        Args:
            interval_hours: 維護間隔（小時）
            auto_shard: 是否自動創建分片
            auto_compress: 是否自動壓縮
            verify_integrity: 是否驗證完整性

        Returns:
            Dict[str, Any]: 排程配置資訊

        Raises:
            DatabaseConfigError: 當參數無效或任務已在運行時

        Note:
            此方法僅返回排程配置，實際的排程執行需要外部排程系統實現
        """
        if interval_hours <= 0:
            raise DatabaseConfigError("維護間隔必須大於 0")

        if self.maintenance_running:
            raise DatabaseConfigError("排程維護任務已在運行中")

        config = {
            "interval_hours": interval_hours,
            "auto_shard": auto_shard,
            "auto_compress": auto_compress,
            "verify_integrity": verify_integrity,
            "next_maintenance_time": datetime.now(),
            "status": "configured",
        }

        logger.info(
            f"配置排程維護任務: 間隔 {interval_hours} 小時, "
            f"分片: {auto_shard}, 壓縮: {auto_compress}, 校驗: {verify_integrity}"
        )

        return config

    def stop_scheduled_maintenance(self) -> Dict[str, Any]:
        """停止排程維護任務.

        Returns:
            Dict[str, Any]: 停止操作結果
        """
        if self.maintenance_running:
            self.maintenance_running = False
            logger.info("正在停止排程維護任務...")

            if self.maintenance_thread and self.maintenance_thread.is_alive():
                self.maintenance_thread.join(timeout=10)

            logger.info("排程維護任務已停止")
            return {"status": "stopped", "message": "排程維護任務已停止"}
        else:
            logger.info("排程維護任務未在運行")
            return {"status": "not_running", "message": "排程維護任務未在運行"}

    def get_database_status(self) -> Dict[str, Any]:
        """獲取資料庫狀態報告.

        Returns:
            Dict[str, Any]: 資料庫狀態報告

        Raises:
            DatabaseOperationError: 當獲取狀態過程中發生錯誤時
        """
        try:
            status = self._initialize_status_report()

            # 獲取各管理器統計
            status["sharding_stats"] = self.sharding_manager.get_shard_statistics()
            status["compression_stats"] = (
                self.compression_manager.get_compression_statistics()
            )
            status["integrity_stats"] = self.checksum_manager.get_integrity_report()

            return status

        except Exception as e:
            raise DatabaseOperationError(f"獲取資料庫狀態時發生錯誤: {e}") from e

    def _initialize_status_report(self) -> Dict[str, Any]:
        """初始化狀態報告."""
        return {
            "timestamp": datetime.now(),
            "sharding_stats": {},
            "compression_stats": {},
            "integrity_stats": {},
            "maintenance_status": {
                "is_running": self.maintenance_running,
                "thread_alive": (
                    self.maintenance_thread.is_alive()
                    if self.maintenance_thread
                    else False
                ),
            },
        }

    def optimize_query_performance(
        self,
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
        start_date: date,
        end_date: date,
        symbols: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """優化查詢效能.

        根據查詢條件選擇最佳的資料來源（分片或原始表）。

        Args:
            table_class: 資料表類別
            start_date: 查詢開始日期
            end_date: 查詢結束日期
            symbols: 股票代碼列表

        Returns:
            Dict[str, Any]: 查詢優化建議

        Raises:
            DatabaseConfigError: 當參數無效時
            DatabaseOperationError: 當優化過程中發生錯誤時
        """
        if start_date > end_date:
            raise DatabaseConfigError("開始日期不能大於結束日期")

        try:
            # 獲取相關分片
            shards = self.sharding_manager.get_shards_for_query(
                table_class, start_date, end_date, symbols
            )

            # 計算查詢範圍
            date_range_days = (end_date - start_date).days + 1

            optimization = self._initialize_optimization_result(
                date_range_days, len(shards)
            )

            if shards:
                self._analyze_shard_coverage(
                    optimization, shards, start_date, end_date, date_range_days
                )

            return optimization

        except (DatabaseConfigError, DatabaseOperationError):
            raise
        except Exception as e:
            raise DatabaseOperationError(f"優化查詢效能時發生錯誤: {e}") from e

    def _initialize_optimization_result(
        self, date_range_days: int, shard_count: int
    ) -> Dict[str, Any]:
        """初始化優化結果."""
        return {
            "query_date_range_days": date_range_days,
            "available_shards": shard_count,
            "recommendation": "use_database",  # 預設使用資料庫
            "estimated_performance": "medium",
            "shards_info": [],
        }

    def _analyze_shard_coverage(
        self,
        optimization: Dict[str, Any],
        shards: List[Any],
        start_date: date,
        end_date: date,
        date_range_days: int,
    ) -> None:
        """分析分片覆蓋率."""
        shard_coverage_days = 0

        for shard in shards:
            shard_start = max(shard.start_date, start_date)
            shard_end = min(shard.end_date, end_date)
            if shard_start <= shard_end:
                shard_coverage_days += (shard_end - shard_start).days + 1

            optimization["shards_info"].append(
                {
                    "shard_id": shard.shard_id,
                    "start_date": shard.start_date,
                    "end_date": shard.end_date,
                    "is_compressed": shard.is_compressed,
                    "file_size_mb": (shard.file_size_bytes or 0) / (1024 * 1024),
                }
            )

        coverage_ratio = shard_coverage_days / date_range_days
        optimization["shard_coverage_ratio"] = coverage_ratio

        # 根據覆蓋率決定查詢策略
        if coverage_ratio >= 0.8:  # 80% 以上覆蓋率
            optimization["recommendation"] = "use_shards"
            optimization["estimated_performance"] = "high"
        elif coverage_ratio >= 0.5:  # 50-80% 覆蓋率
            optimization["recommendation"] = "use_hybrid"
            optimization["estimated_performance"] = "medium"

    def close(self) -> None:
        """關閉資料庫管理器.

        Raises:
            DatabaseOperationError: 當關閉過程中發生錯誤時
        """
        try:
            # 停止排程維護
            self.stop_scheduled_maintenance()

            logger.info("資料庫管理器已關閉")

        except Exception as e:
            raise DatabaseOperationError(f"關閉資料庫管理器時發生錯誤: {e}") from e
