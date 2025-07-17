"""
資料庫維護操作模組

此模組負責處理資料庫的維護操作，包括：
- 自動分片維護
- 自動壓縮維護
- 完整性檢查
- 排程維護任務

主要功能：
- 執行各種維護任務
- 維護統計和報告
- 排程維護管理
- 錯誤處理和恢復

Example:
    >>> from src.database.maintenance_operations import MaintenanceOperations
    >>> maintenance = MaintenanceOperations(session, managers)
    >>> result = maintenance.perform_maintenance()
"""

import logging
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, Type, Union

from src.database.schema import MarketDaily, MarketMinute, MarketTick

logger = logging.getLogger(__name__)


class MaintenanceOperations:
    """資料庫維護操作管理器.
    
    負責協調各種維護任務的執行，包括分片、壓縮和完整性檢查。
    
    Attributes:
        session: SQLAlchemy 會話
        sharding_manager: 分片管理器
        compression_manager: 壓縮管理器
        checksum_manager: 校驗碼管理器
        lock: 執行緒鎖
        maintenance_running: 維護任務運行狀態
    """
    
    def __init__(
        self, 
        session, 
        sharding_manager, 
        compression_manager, 
        checksum_manager
    ) -> None:
        """初始化維護操作管理器.
        
        Args:
            session: SQLAlchemy 會話
            sharding_manager: 分片管理器
            compression_manager: 壓縮管理器
            checksum_manager: 校驗碼管理器
        """
        self.session = session
        self.sharding_manager = sharding_manager
        self.compression_manager = compression_manager
        self.checksum_manager = checksum_manager
        self.lock = threading.Lock()
        self.maintenance_running = False
        self.maintenance_thread: Optional[threading.Thread] = None
        
        logger.info("維護操作管理器初始化完成")

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
            RuntimeError: 當維護過程中發生嚴重錯誤時
        """
        maintenance_stats = self._initialize_maintenance_stats()

        try:
            logger.info("開始執行資料庫維護任務")
            
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
            
            logger.info("資料庫維護任務執行完成")

        except Exception as e:
            error_msg = f"資料庫維護時發生未預期錯誤: {e}"
            maintenance_stats["errors"].append(error_msg)
            logger.error(error_msg, exc_info=True)

        return maintenance_stats

    def _initialize_maintenance_stats(self) -> Dict[str, Any]:
        """初始化維護統計.
        
        Returns:
            Dict[str, Any]: 初始化的維護統計字典
        """
        return {
            "start_time": datetime.now(),
            "auto_shard_results": {},
            "auto_compress_results": {},
            "integrity_check_results": {},
            "errors": [],
        }

    def _perform_auto_sharding(self, maintenance_stats: Dict[str, Any]) -> None:
        """執行自動分片任務.
        
        Args:
            maintenance_stats: 維護統計字典
        """
        logger.info("開始自動分片任務")
        
        for table_class in [MarketDaily, MarketMinute, MarketTick]:
            try:
                result = self.sharding_manager.auto_create_shards(
                    table_class, "size_based"
                )
                maintenance_stats["auto_shard_results"][
                    table_class.__tablename__
                ] = result
                
                logger.info(
                    "自動分片完成 %s: 創建 %d 個分片", 
                    table_class.__tablename__, 
                    result.get("shards_created", 0)
                )

            except Exception as e:
                error_msg = f"自動分片失敗 {table_class.__tablename__}: {e}"
                maintenance_stats["errors"].append(error_msg)
                logger.error(error_msg, exc_info=True)

    def _perform_auto_compression(self, maintenance_stats: Dict[str, Any]) -> None:
        """執行自動壓縮任務.
        
        Args:
            maintenance_stats: 維護統計字典
        """
        logger.info("開始自動壓縮任務")
        
        for table_class in [MarketDaily, MarketMinute, MarketTick]:
            try:
                result = self.compression_manager.auto_compress_old_data(
                    table_class, days_threshold=30
                )
                maintenance_stats["auto_compress_results"][
                    table_class.__tablename__
                ] = result
                
                logger.info(
                    "自動壓縮完成 %s: 壓縮 %d 個檔案", 
                    table_class.__tablename__, 
                    result.get("files_compressed", 0)
                )

            except Exception as e:
                error_msg = f"自動壓縮失敗 {table_class.__tablename__}: {e}"
                maintenance_stats["errors"].append(error_msg)
                logger.error(error_msg, exc_info=True)

    def _perform_integrity_check(self, maintenance_stats: Dict[str, Any]) -> None:
        """執行完整性檢查任務.
        
        Args:
            maintenance_stats: 維護統計字典
        """
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
                
                logger.info(
                    "完整性檢查完成 %s: 驗證 %d 筆記錄", 
                    table_class.__tablename__, 
                    result.get("verified_count", 0)
                )

            except Exception as e:
                error_msg = f"完整性檢查失敗 {table_class.__tablename__}: {e}"
                maintenance_stats["errors"].append(error_msg)
                logger.error(error_msg, exc_info=True)

    def _get_checksum_strategy_name(
        self, 
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]]
    ) -> str:
        """根據表類別獲取校驗策略名稱.
        
        Args:
            table_class: 資料表類別
            
        Returns:
            str: 校驗策略名稱
        """
        strategy_mapping = {
            MarketDaily: "daily_checksum",
            MarketMinute: "minute_checksum", 
            MarketTick: "tick_checksum"
        }
        return strategy_mapping.get(table_class, "default_checksum")

    def _finalize_maintenance_stats(self, maintenance_stats: Dict[str, Any]) -> None:
        """完成維護統計.
        
        Args:
            maintenance_stats: 維護統計字典
        """
        maintenance_stats["end_time"] = datetime.now()
        maintenance_stats["duration"] = (
            maintenance_stats["end_time"] - maintenance_stats["start_time"]
        ).total_seconds()
        
        # 計算總體統計
        total_errors = len(maintenance_stats["errors"])
        maintenance_stats["total_errors"] = total_errors
        maintenance_stats["success"] = total_errors == 0
        
        logger.info(
            "維護任務統計: 耗時 %.2f 秒, 錯誤 %d 個", 
            maintenance_stats["duration"], 
            total_errors
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
            ValueError: 當參數無效或任務已在運行時

        Note:
            此方法僅返回排程配置，實際的排程執行需要外部排程系統實現
        """
        if interval_hours <= 0:
            raise ValueError("維護間隔必須大於 0")

        if self.maintenance_running:
            raise ValueError("排程維護任務已在運行中")

        config = {
            "interval_hours": interval_hours,
            "auto_shard": auto_shard,
            "auto_compress": auto_compress,
            "verify_integrity": verify_integrity,
            "next_maintenance_time": datetime.now(),
            "status": "configured",
        }

        logger.info(
            "配置排程維護任務: 間隔 %d 小時, 分片: %s, 壓縮: %s, 校驗: %s",
            interval_hours, auto_shard, auto_compress, verify_integrity
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

    def get_maintenance_status(self) -> Dict[str, Any]:
        """獲取維護任務狀態.
        
        Returns:
            Dict[str, Any]: 維護任務狀態資訊
        """
        return {
            "maintenance_running": self.maintenance_running,
            "thread_active": (
                self.maintenance_thread.is_alive() 
                if self.maintenance_thread else False
            ),
            "last_check": datetime.now(),
        }
