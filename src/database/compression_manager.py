# -*- coding: utf-8 -*-
"""
資料壓縮管理模組

此模組提供完整的歷史資料壓縮管理功能，包括：
- Parquet 格式壓縮
- Apache Arrow 格式支援
- 壓縮格式轉換
- 壓縮效能監控

主要功能：
- 多種壓縮演算法支援 (Snappy, GZIP, LZ4, ZSTD)
- 自動壓縮策略
- 壓縮效能分析
- 歷史資料遷移

Example:
    >>> from src.database.compression_manager import CompressionManager
    >>> manager = CompressionManager(session)
    >>> file_path, stats = manager.compress_table_data(MarketDaily, start_date, end_date)
"""

import logging
import os
import threading
import time
from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Dict, List, Optional, Tuple, Type, Union

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from src.config import DATA_DIR
from src.database.schema import DataShard, MarketDaily, MarketMinute, MarketTick

logger = logging.getLogger(__name__)


class CompressionError(Exception):
    """壓縮操作相關的異常類別."""

    pass


class CompressionConfigError(CompressionError):
    """壓縮配置錯誤."""

    pass


class CompressionOperationError(CompressionError):
    """壓縮操作錯誤."""

    pass


class CompressionStrategy(ABC):
    """壓縮策略抽象基類.

    定義壓縮策略的通用介面，所有具體的壓縮策略都必須實現此介面。

    Attributes:
        name: 策略名稱
        compression_type: 壓縮類型
    """

    SUPPORTED_COMPRESSION_TYPES = {"snappy", "gzip", "lz4", "zstd"}

    def __init__(self, name: str, compression_type: str) -> None:
        """初始化壓縮策略.

        Args:
            name: 策略名稱
            compression_type: 壓縮類型 (snappy, gzip, lz4, zstd)

        Raises:
            CompressionConfigError: 當策略名稱或壓縮類型無效時
        """
        if not name or not name.strip():
            raise CompressionConfigError("策略名稱不能為空")
        if compression_type not in self.SUPPORTED_COMPRESSION_TYPES:
            raise CompressionConfigError(
                f"不支援的壓縮類型: {compression_type}. "
                f"支援的類型: {', '.join(self.SUPPORTED_COMPRESSION_TYPES)}"
            )

        self.name = name.strip()
        self.compression_type = compression_type

    @abstractmethod
    def should_compress(self, data_size: int, age_days: int) -> bool:
        """判斷是否需要壓縮.

        Args:
            data_size: 資料大小（位元組）
            age_days: 資料年齡（天）

        Returns:
            bool: 是否需要壓縮

        Raises:
            CompressionOperationError: 當判斷過程中發生錯誤時
        """
        pass

    def get_compression_params(self) -> Dict[str, str]:
        """獲取壓縮參數.

        Returns:
            Dict[str, str]: 壓縮參數
        """
        return {"compression": self.compression_type}


class TimeBasedCompressionStrategy(CompressionStrategy):
    """基於時間的壓縮策略.

    根據資料年齡決定是否需要壓縮，適用於歷史資料的自動壓縮。

    Attributes:
        min_age_days: 最小壓縮年齡（天）
    """

    def __init__(
        self, compression_type: str = "snappy", min_age_days: int = 30
    ) -> None:
        """初始化時間壓縮策略.

        Args:
            compression_type: 壓縮類型
            min_age_days: 最小壓縮年齡（天），必須大於等於 0

        Raises:
            CompressionConfigError: 當最小年齡無效時
        """
        super().__init__("time_based", compression_type)
        if min_age_days < 0:
            raise CompressionConfigError("最小壓縮年齡不能小於 0")
        self.min_age_days = min_age_days

    def should_compress(self, data_size: int, age_days: int) -> bool:
        """判斷是否需要基於時間壓縮.

        Args:
            data_size: 資料大小（位元組）- 此策略不使用此參數
            age_days: 資料年齡（天）

        Returns:
            bool: 是否需要壓縮
        """
        # 忽略 data_size 參數，僅基於時間判斷
        return age_days >= self.min_age_days


class SizeBasedCompressionStrategy(CompressionStrategy):
    """基於大小的壓縮策略.

    根據資料大小決定是否需要壓縮，適用於大檔案的自動壓縮。

    Attributes:
        min_size_mb: 最小壓縮大小（MB）
    """

    def __init__(
        self, compression_type: str = "snappy", min_size_mb: int = 100
    ) -> None:
        """初始化大小壓縮策略.

        Args:
            compression_type: 壓縮類型
            min_size_mb: 最小壓縮大小（MB），必須大於 0

        Raises:
            CompressionConfigError: 當最小大小無效時
        """
        super().__init__("size_based", compression_type)
        if min_size_mb <= 0:
            raise CompressionConfigError("最小壓縮大小必須大於 0")
        self.min_size_mb = min_size_mb

    def should_compress(self, data_size: int, age_days: int) -> bool:
        """判斷是否需要基於大小壓縮.

        Args:
            data_size: 資料大小（位元組）
            age_days: 資料年齡（天）- 此策略不使用此參數

        Returns:
            bool: 是否需要壓縮
        """
        # 忽略 age_days 參數，僅基於大小判斷
        size_mb = data_size / (1024 * 1024)
        return size_mb >= self.min_size_mb


class CompressionManager:
    """壓縮管理器.

    提供完整的資料壓縮管理功能，包括自動壓縮、格式轉換、效能監控等。

    Attributes:
        session: SQLAlchemy 會話
        strategies: 已註冊的壓縮策略
        compression_stats: 壓縮統計資訊
        lock: 執行緒鎖
    """

    def __init__(self, session: Session) -> None:
        """初始化壓縮管理器.

        Args:
            session: SQLAlchemy 會話

        Raises:
            CompressionConfigError: 當會話無效時
        """
        if session is None:
            raise CompressionConfigError("SQLAlchemy 會話不能為 None")

        self.session = session
        self.strategies: Dict[str, CompressionStrategy] = {}
        self.compression_stats: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

        # 註冊預設壓縮策略
        self._register_default_strategies()

        logger.info("壓縮管理器初始化完成")

    def _register_default_strategies(self) -> None:
        """註冊預設壓縮策略."""
        try:
            self.register_strategy(
                "time_based_snappy", TimeBasedCompressionStrategy("snappy")
            )
            self.register_strategy(
                "time_based_gzip", TimeBasedCompressionStrategy("gzip")
            )
            self.register_strategy(
                "size_based_lz4", SizeBasedCompressionStrategy("lz4")
            )
            self.register_strategy(
                "size_based_zstd", SizeBasedCompressionStrategy("zstd")
            )
        except Exception as e:
            logger.error(f"註冊預設策略失敗: {e}")
            raise CompressionConfigError(f"註冊預設策略失敗: {e}") from e

    def register_strategy(self, name: str, strategy: CompressionStrategy) -> None:
        """註冊壓縮策略.

        Args:
            name: 策略名稱
            strategy: 壓縮策略實例

        Raises:
            CompressionConfigError: 當策略名稱或實例無效時
        """
        if not name or not name.strip():
            raise CompressionConfigError("策略名稱不能為空")
        if not isinstance(strategy, CompressionStrategy):
            raise CompressionConfigError("策略必須是 CompressionStrategy 的實例")

        with self.lock:
            self.strategies[name.strip()] = strategy
            logger.info(f"註冊壓縮策略: {name}")

    def compress_table_data(
        self,
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
        start_date: date,
        end_date: date,
        compression_type: str = "snappy",
        symbols: Optional[List[str]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """壓縮表格資料.

        Args:
            table_class: 資料表類別
            start_date: 開始日期
            end_date: 結束日期
            compression_type: 壓縮類型
            symbols: 股票代碼列表

        Returns:
            Tuple[str, Dict[str, Any]]: 壓縮檔案路徑和壓縮統計

        Raises:
            CompressionConfigError: 當壓縮類型無效時
            CompressionOperationError: 當壓縮過程中發生錯誤時
        """
        if compression_type not in CompressionStrategy.SUPPORTED_COMPRESSION_TYPES:
            raise CompressionConfigError(f"不支援的壓縮類型: {compression_type}")

        if start_date > end_date:
            raise CompressionConfigError("開始日期不能大於結束日期")

        try:
            start_time = time.time()

            # 構建查詢
            df = self._query_table_data(table_class, start_date, end_date, symbols)

            if df.empty:
                logger.warning(f"沒有找到符合條件的資料: {table_class.__tablename__}")
                return "", {}

            # 生成檔案路徑
            file_path = self._generate_file_path(
                table_class, start_date, end_date, symbols
            )

            # 確保目錄存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # 記錄原始大小
            original_size = df.memory_usage(deep=True).sum()

            # 壓縮並儲存
            self._save_compressed_parquet(df, file_path, compression_type)

            # 計算壓縮統計
            compressed_size = os.path.getsize(file_path)
            compression_time = time.time() - start_time
            compression_ratio = (
                original_size / compressed_size if compressed_size > 0 else 0
            )

            stats = {
                "original_size_bytes": int(original_size),
                "compressed_size_bytes": compressed_size,
                "compression_ratio": compression_ratio,
                "compression_time_seconds": compression_time,
                "compression_type": compression_type,
                "row_count": len(df),
                "file_path": file_path,
            }

            logger.info(f"壓縮完成: {file_path}, 壓縮比: {compression_ratio:.2f}")
            return file_path, stats

        except (CompressionConfigError, CompressionOperationError):
            raise
        except Exception as e:
            raise CompressionOperationError(f"壓縮表格資料時發生錯誤: {e}") from e

    def _query_table_data(
        self,
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
        start_date: date,
        end_date: date,
        symbols: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """查詢表格資料."""
        query = select(table_class)

        # 根據資料表類別選擇日期欄位
        if table_class == MarketDaily:
            date_column = table_class.date
        else:
            date_column = func.date(table_class.timestamp)

        query = query.where(and_(date_column >= start_date, date_column <= end_date))

        # 如果指定了股票代碼，添加過濾條件
        if symbols:
            query = query.where(table_class.symbol.in_(symbols))

        # 執行查詢並轉換為 DataFrame
        result = self.session.execute(query)
        return pd.DataFrame(result.fetchall(), columns=result.keys())

    def _generate_file_path(
        self,
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
        start_date: date,
        end_date: date,
        symbols: Optional[List[str]] = None,
    ) -> str:
        """生成壓縮檔案路徑."""
        table_name = table_class.__tablename__
        date_range = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"

        if symbols:
            symbol_suffix = "_".join(symbols[:3])
            file_name = f"{table_name}_{date_range}_{symbol_suffix}.parquet"
        else:
            file_name = f"{table_name}_{date_range}.parquet"

        return os.path.join(DATA_DIR, "compressed", table_name, file_name)

    def _save_compressed_parquet(
        self, df: pd.DataFrame, file_path: str, compression_type: str
    ) -> None:
        """儲存壓縮的 Parquet 檔案.

        Args:
            df: 要儲存的 DataFrame
            file_path: 檔案路徑
            compression_type: 壓縮類型

        Raises:
            CompressionOperationError: 當儲存過程中發生錯誤時
        """
        try:
            # 轉換為 PyArrow Table
            table = pa.Table.from_pandas(df)

            # 設定壓縮參數
            compression_options = self._get_compression_options(compression_type)

            # 儲存為 Parquet 格式
            pq.write_table(
                table, file_path, compression=compression_type, **compression_options
            )
        except Exception as e:
            raise CompressionOperationError(f"儲存壓縮檔案時發生錯誤: {e}") from e

    def _get_compression_options(self, compression_type: str) -> Dict[str, Any]:
        """獲取壓縮選項.

        Args:
            compression_type: 壓縮類型

        Returns:
            Dict[str, Any]: 壓縮選項
        """
        options: Dict[str, Any] = {}

        if compression_type == "gzip":
            options["compression_level"] = 6
        elif compression_type == "zstd":
            options["compression_level"] = 3
        elif compression_type == "lz4":
            options["use_dictionary"] = True

        return options

    def convert_compression_format(
        self, source_path: str, target_path: str, target_compression: str
    ) -> Dict[str, Any]:
        """轉換壓縮格式.

        Args:
            source_path: 來源檔案路徑
            target_path: 目標檔案路徑
            target_compression: 目標壓縮類型

        Returns:
            Dict[str, Any]: 轉換統計

        Raises:
            CompressionConfigError: 當參數無效時
            CompressionOperationError: 當轉換過程中發生錯誤時
        """
        if not os.path.exists(source_path):
            raise CompressionConfigError(f"來源檔案不存在: {source_path}")

        if target_compression not in CompressionStrategy.SUPPORTED_COMPRESSION_TYPES:
            raise CompressionConfigError(f"不支援的目標壓縮類型: {target_compression}")

        try:
            start_time = time.time()

            # 讀取來源檔案
            df = pd.read_parquet(source_path)

            # 記錄原始大小
            original_size = os.path.getsize(source_path)

            # 確保目標目錄存在
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            # 儲存為新格式
            self._save_compressed_parquet(df, target_path, target_compression)

            # 計算轉換統計
            new_size = os.path.getsize(target_path)
            conversion_time = time.time() - start_time
            size_ratio = original_size / new_size if new_size > 0 else 0

            stats = {
                "original_size_bytes": original_size,
                "new_size_bytes": new_size,
                "size_ratio": size_ratio,
                "conversion_time_seconds": conversion_time,
                "target_compression": target_compression,
                "row_count": len(df),
            }

            logger.info(f"格式轉換完成: {source_path} -> {target_path}")
            return stats

        except (CompressionConfigError, CompressionOperationError):
            raise
        except Exception as e:
            raise CompressionOperationError(f"轉換壓縮格式時發生錯誤: {e}") from e

    def auto_compress_old_data(
        self, strategy_name: str = "time_based_snappy", dry_run: bool = False
    ) -> List[Dict[str, Any]]:
        """自動壓縮舊資料.

        Args:
            strategy_name: 壓縮策略名稱
            dry_run: 是否為試運行

        Returns:
            List[Dict[str, Any]]: 壓縮結果列表

        Raises:
            CompressionConfigError: 當策略不存在時
            CompressionOperationError: 當壓縮過程中發生錯誤時
        """
        if strategy_name not in self.strategies:
            raise CompressionConfigError(f"未知的壓縮策略: {strategy_name}")

        try:
            strategy = self.strategies[strategy_name]
            results: List[Dict[str, Any]] = []

            # 查詢所有未壓縮的分片
            uncompressed_shards = (
                self.session.query(DataShard).filter_by(is_compressed=False).all()
            )

            for shard in uncompressed_shards:
                result = self._process_shard_compression(shard, strategy, dry_run)
                if result:
                    results.append(result)

            logger.info(f"自動壓縮完成，處理了 {len(results)} 個分片")
            return results

        except CompressionConfigError:
            raise
        except Exception as e:
            raise CompressionOperationError(f"自動壓縮時發生錯誤: {e}") from e

    def _process_shard_compression(
        self, shard: DataShard, strategy: CompressionStrategy, dry_run: bool
    ) -> Optional[Dict[str, Any]]:
        """處理單個分片的壓縮."""
        # 計算資料年齡
        if shard.end_date:
            age_days = (date.today() - shard.end_date).days
        else:
            age_days = 0

        # 獲取檔案大小
        file_size = shard.file_size_bytes or 0

        # 檢查是否需要壓縮
        if not strategy.should_compress(file_size, age_days):
            return None

        if dry_run:
            return {
                "shard_id": shard.shard_id,
                "status": "would_compress",
                "age_days": age_days,
                "file_size_bytes": file_size,
            }

        try:
            # 執行壓縮
            table_class = self._get_table_class(shard.table_name)
            file_path, stats = self.compress_table_data(
                table_class, shard.start_date, shard.end_date, strategy.compression_type
            )

            # 更新分片記錄
            shard.file_path = file_path
            shard.compression = strategy.compression_type
            shard.is_compressed = True
            shard.file_size_bytes = stats["compressed_size_bytes"]

            self.session.commit()

            return {"shard_id": shard.shard_id, "status": "compressed", "stats": stats}

        except Exception as e:
            logger.error(f"壓縮分片 {shard.shard_id} 時發生錯誤: {e}")
            return {"shard_id": shard.shard_id, "status": "error", "error": str(e)}

    def _get_table_class(
        self, table_name: str
    ) -> Type[Union[MarketDaily, MarketMinute, MarketTick]]:
        """根據表名獲取表類別.

        Args:
            table_name: 表名

        Returns:
            Type[Union[MarketDaily, MarketMinute, MarketTick]]: 表類別

        Raises:
            CompressionConfigError: 當表名未知時
        """
        table_mapping = {
            "market_daily": MarketDaily,
            "market_minute": MarketMinute,
            "market_tick": MarketTick,
        }

        if table_name not in table_mapping:
            raise CompressionConfigError(f"未知的表名: {table_name}")

        return table_mapping[table_name]

    def get_compression_statistics(self) -> Dict[str, Any]:
        """獲取壓縮統計資訊.

        Returns:
            Dict[str, Any]: 壓縮統計

        Raises:
            CompressionOperationError: 當獲取統計時發生錯誤
        """
        try:
            # 查詢所有分片
            all_shards = self.session.query(DataShard).all()

            stats: Dict[str, Any] = {
                "total_shards": len(all_shards),
                "compressed_shards": 0,
                "uncompressed_shards": 0,
                "total_original_size": 0,
                "total_compressed_size": 0,
                "compression_by_type": {},
                "compression_by_table": {},
            }

            for shard in all_shards:
                if shard.is_compressed:
                    self._update_compressed_stats(stats, shard)
                else:
                    self._update_uncompressed_stats(stats, shard)

            # 計算總體壓縮比
            if stats["total_compressed_size"] > 0:
                stats["overall_compression_ratio"] = (
                    stats["total_original_size"] / stats["total_compressed_size"]
                )
            else:
                stats["overall_compression_ratio"] = 0

            return stats

        except Exception as e:
            raise CompressionOperationError(f"獲取壓縮統計時發生錯誤: {e}") from e

    def _update_compressed_stats(self, stats: Dict[str, Any], shard: DataShard) -> None:
        """更新壓縮分片統計."""
        stats["compressed_shards"] += 1

        # 按壓縮類型統計
        compression_type = shard.compression or "unknown"
        if compression_type not in stats["compression_by_type"]:
            stats["compression_by_type"][compression_type] = {
                "count": 0,
                "total_size": 0,
            }
        stats["compression_by_type"][compression_type]["count"] += 1
        stats["compression_by_type"][compression_type]["total_size"] += (
            shard.file_size_bytes or 0
        )

        # 按表統計
        table_name = shard.table_name
        if table_name not in stats["compression_by_table"]:
            stats["compression_by_table"][table_name] = {
                "compressed": 0,
                "uncompressed": 0,
                "total_size": 0,
            }
        stats["compression_by_table"][table_name]["compressed"] += 1
        stats["compression_by_table"][table_name]["total_size"] += (
            shard.file_size_bytes or 0
        )

        stats["total_compressed_size"] += shard.file_size_bytes or 0

    def _update_uncompressed_stats(
        self, stats: Dict[str, Any], shard: DataShard
    ) -> None:
        """更新未壓縮分片統計."""
        stats["uncompressed_shards"] += 1

        # 按表統計未壓縮
        table_name = shard.table_name
        if table_name not in stats["compression_by_table"]:
            stats["compression_by_table"][table_name] = {
                "compressed": 0,
                "uncompressed": 0,
                "total_size": 0,
            }
        stats["compression_by_table"][table_name]["uncompressed"] += 1
