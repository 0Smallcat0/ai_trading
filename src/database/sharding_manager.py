# -*- coding: utf-8 -*-
"""
資料分片管理模組

此模組提供完整的資料分片管理功能，包括：
- 自動分片策略實施
- 分片查詢優化
- 分片維護和管理
- 跨分片查詢支援

主要功能：
- 基於時間範圍的自動分片
- 基於股票代碼的分片策略
- 分片元數據管理
- 查詢路由優化

Example:
    >>> from src.database.sharding_manager import ShardingManager
    >>> manager = ShardingManager(session)
    >>> shard, path = manager.create_shard_if_needed(MarketDaily, "time_based")
"""

import logging
import threading
from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple, Type, Union

import pandas as pd
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from src.database.parquet_utils import create_market_data_shard, load_from_shard
from src.database.schema import DataShard, MarketDaily, MarketMinute, MarketTick

logger = logging.getLogger(__name__)


class ShardingError(Exception):
    """分片操作相關的異常類別."""
    pass


class ShardingConfigError(ShardingError):
    """分片配置錯誤."""
    pass


class ShardingOperationError(ShardingError):
    """分片操作錯誤."""
    pass


class ShardingStrategy(ABC):
    """分片策略抽象基類.

    定義分片策略的通用介面，所有具體的分片策略都必須實現此介面。

    Attributes:
        name: 策略名稱
    """

    def __init__(self, name: str) -> None:
        """初始化分片策略.

        Args:
            name: 策略名稱

        Raises:
            ShardingConfigError: 當策略名稱為空時
        """
        if not name or not name.strip():
            raise ShardingConfigError("策略名稱不能為空")
        self.name = name.strip()

    @abstractmethod
    def should_create_shard(self, table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
                          session: Session) -> bool:
        """判斷是否需要創建新分片.

        Args:
            table_class: 資料表類別
            session: SQLAlchemy 會話

        Returns:
            bool: 是否需要創建分片

        Raises:
            ShardingOperationError: 當檢查過程中發生錯誤時
        """
        pass

    @abstractmethod
    def get_shard_parameters(self, table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
                           session: Session) -> Dict[str, Any]:
        """獲取分片參數.

        Args:
            table_class: 資料表類別
            session: SQLAlchemy 會話

        Returns:
            Dict[str, Any]: 分片參數，包含 start_date, end_date, shard_key

        Raises:
            ShardingOperationError: 當獲取參數過程中發生錯誤時
        """
        pass


class TimeBasedShardingStrategy(ShardingStrategy):
    """基於時間的分片策略.

    根據時間間隔自動創建分片，適用於時間序列資料的管理。

    Attributes:
        shard_interval_days: 分片時間間隔（天）
    """

    def __init__(self, shard_interval_days: int = 30) -> None:
        """初始化時間分片策略.

        Args:
            shard_interval_days: 分片時間間隔（天），必須大於 0

        Raises:
            ShardingConfigError: 當時間間隔無效時
        """
        super().__init__("time_based")
        if shard_interval_days <= 0:
            raise ShardingConfigError("分片時間間隔必須大於 0")
        self.shard_interval_days = shard_interval_days

    def should_create_shard(self, table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
                          session: Session) -> bool:
        """判斷是否需要創建新的時間分片.

        Args:
            table_class: 資料表類別
            session: SQLAlchemy 會話

        Returns:
            bool: 是否需要創建分片

        Raises:
            ShardingOperationError: 當查詢過程中發生錯誤時
        """
        try:
            # 查詢最新的分片
            latest_shard = (
                session.query(DataShard)
                .filter_by(table_name=table_class.__tablename__)
                .order_by(DataShard.end_date.desc())
                .first()
            )

            if not latest_shard:
                return True

            # 檢查是否超過分片間隔
            if latest_shard.end_date is None:
                return True

            days_since_last_shard = (date.today() - latest_shard.end_date).days
            return days_since_last_shard >= self.shard_interval_days

        except Exception as e:
            raise ShardingOperationError(f"檢查分片需求時發生錯誤: {e}") from e

    def get_shard_parameters(self, table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
                           session: Session) -> Dict[str, Any]:
        """獲取時間分片參數.

        Args:
            table_class: 資料表類別
            session: SQLAlchemy 會話

        Returns:
            Dict[str, Any]: 分片參數，包含 start_date, end_date, shard_key

        Raises:
            ShardingOperationError: 當獲取參數過程中發生錯誤時
        """
        try:
            # 查詢最新的分片
            latest_shard = (
                session.query(DataShard)
                .filter_by(table_name=table_class.__tablename__)
                .order_by(DataShard.end_date.desc())
                .first()
            )

            if latest_shard and latest_shard.end_date:
                start_date = latest_shard.end_date + timedelta(days=1)
            else:
                # 如果沒有分片，從最早的資料開始
                start_date = self._get_earliest_date(table_class, session)

            end_date = start_date + timedelta(days=self.shard_interval_days - 1)

            return {
                "start_date": start_date,
                "end_date": end_date,
                "shard_key": "date" if table_class == MarketDaily else "timestamp"
            }

        except Exception as e:
            raise ShardingOperationError(f"獲取分片參數時發生錯誤: {e}") from e

    def _get_earliest_date(self, table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
                          session: Session) -> date:
        """獲取表中最早的日期.

        Args:
            table_class: 資料表類別
            session: SQLAlchemy 會話

        Returns:
            date: 最早的日期，如果沒有資料則返回今天
        """
        try:
            if table_class == MarketDaily:
                date_column = table_class.date
            else:
                date_column = func.date(table_class.timestamp)

            earliest_date = session.query(func.min(date_column)).scalar()
            return earliest_date or date.today()

        except Exception:
            # 如果查詢失敗，返回今天的日期
            return date.today()


class SizeBasedShardingStrategy(ShardingStrategy):
    """基於大小的分片策略.

    根據資料行數自動創建分片，適用於大量資料的管理。

    Attributes:
        max_rows_per_shard: 每個分片的最大行數
    """

    def __init__(self, max_rows_per_shard: int = 1000000) -> None:
        """初始化大小分片策略.

        Args:
            max_rows_per_shard: 每個分片的最大行數，必須大於 0

        Raises:
            ShardingConfigError: 當最大行數無效時
        """
        super().__init__("size_based")
        if max_rows_per_shard <= 0:
            raise ShardingConfigError("每個分片的最大行數必須大於 0")
        self.max_rows_per_shard = max_rows_per_shard

    def should_create_shard(self, table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
                          session: Session) -> bool:
        """判斷是否需要創建新的大小分片.

        Args:
            table_class: 資料表類別
            session: SQLAlchemy 會話

        Returns:
            bool: 是否需要創建分片

        Raises:
            ShardingOperationError: 當查詢過程中發生錯誤時
        """
        try:
            # 查詢當前表的行數
            row_count = session.query(func.count(table_class.id)).scalar() or 0

            # 查詢已分片的行數
            sharded_rows = (
                session.query(func.sum(DataShard.row_count))
                .filter_by(table_name=table_class.__tablename__)
                .scalar() or 0
            )

            unsharded_rows = row_count - sharded_rows
            return unsharded_rows >= self.max_rows_per_shard

        except Exception as e:
            raise ShardingOperationError(f"檢查分片需求時發生錯誤: {e}") from e

    def get_shard_parameters(self, table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
                           session: Session) -> Dict[str, Any]:
        """獲取大小分片參數.

        Args:
            table_class: 資料表類別
            session: SQLAlchemy 會話

        Returns:
            Dict[str, Any]: 分片參數，包含 start_date, end_date, shard_key

        Raises:
            ShardingOperationError: 當獲取參數過程中發生錯誤時
        """
        try:
            start_date = self._get_start_date(table_class, session)
            end_date = self._calculate_end_date(table_class, session, start_date)

            return {
                "start_date": start_date,
                "end_date": end_date,
                "shard_key": "date" if table_class == MarketDaily else "timestamp"
            }

        except Exception as e:
            raise ShardingOperationError(f"獲取分片參數時發生錯誤: {e}") from e

    def _get_start_date(self, table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
                       session: Session) -> date:
        """獲取分片開始日期."""
        latest_shard = (
            session.query(DataShard)
            .filter_by(table_name=table_class.__tablename__)
            .order_by(DataShard.end_date.desc())
            .first()
        )

        if latest_shard and latest_shard.end_date:
            return latest_shard.end_date + timedelta(days=1)

        # 獲取最早的日期
        if table_class == MarketDaily:
            date_column = table_class.date
        else:
            date_column = func.date(table_class.timestamp)

        earliest_date = session.query(func.min(date_column)).scalar()
        return earliest_date or date.today()

    def _calculate_end_date(self, table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
                          session: Session, start_date: date) -> date:
        """計算分片結束日期."""
        if table_class == MarketDaily:
            date_column = table_class.date
        else:
            date_column = func.date(table_class.timestamp)

        # 計算需要分片的日期範圍
        query = select(date_column).where(date_column >= start_date).order_by(date_column)
        dates = [row[0] for row in session.execute(query).fetchall()]

        if len(dates) >= self.max_rows_per_shard:
            return dates[self.max_rows_per_shard - 1]
        elif dates:
            return dates[-1]
        else:
            return start_date


class ShardingManager:
    """分片管理器.

    提供完整的資料分片管理功能，包括自動分片、查詢路由、維護等。

    Attributes:
        session: SQLAlchemy 會話
        strategies: 已註冊的分片策略
        shard_cache: 分片快取
        lock: 執行緒鎖
    """

    def __init__(self, session: Session) -> None:
        """初始化分片管理器.

        Args:
            session: SQLAlchemy 會話

        Raises:
            ShardingConfigError: 當會話無效時
        """
        if session is None:
            raise ShardingConfigError("SQLAlchemy 會話不能為 None")

        self.session = session
        self.strategies: Dict[str, ShardingStrategy] = {}
        self.shard_cache: Dict[str, List[DataShard]] = {}
        self.lock = threading.Lock()

        # 註冊預設分片策略
        self._register_default_strategies()

        logger.info("分片管理器初始化完成")

    def _register_default_strategies(self) -> None:
        """註冊預設分片策略."""
        try:
            self.register_strategy("time_based", TimeBasedShardingStrategy())
            self.register_strategy("size_based", SizeBasedShardingStrategy())
        except Exception as e:
            logger.error(f"註冊預設策略失敗: {e}")
            raise ShardingConfigError(f"註冊預設策略失敗: {e}") from e

    def register_strategy(self, name: str, strategy: ShardingStrategy) -> None:
        """註冊分片策略.

        Args:
            name: 策略名稱
            strategy: 分片策略實例

        Raises:
            ShardingConfigError: 當策略名稱或實例無效時
        """
        if not name or not name.strip():
            raise ShardingConfigError("策略名稱不能為空")
        if not isinstance(strategy, ShardingStrategy):
            raise ShardingConfigError("策略必須是 ShardingStrategy 的實例")

        with self.lock:
            self.strategies[name.strip()] = strategy
            logger.info(f"註冊分片策略: {name}")

    def create_shard_if_needed(
        self,
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
        strategy_name: str = "time_based",
        symbols: Optional[List[str]] = None
    ) -> Optional[Tuple[DataShard, str]]:
        """根據策略自動創建分片.

        Args:
            table_class: 資料表類別
            strategy_name: 分片策略名稱
            symbols: 股票代碼列表

        Returns:
            Optional[Tuple[DataShard, str]]: 創建的分片記錄和檔案路徑，如果不需要創建則返回 None

        Raises:
            ShardingConfigError: 當策略不存在時
            ShardingOperationError: 當創建分片過程中發生錯誤時
        """
        if strategy_name not in self.strategies:
            raise ShardingConfigError(f"未知的分片策略: {strategy_name}")

        try:
            strategy = self.strategies[strategy_name]

            # 檢查是否需要創建分片
            if not strategy.should_create_shard(table_class, self.session):
                return None

            # 獲取分片參數
            params = strategy.get_shard_parameters(table_class, self.session)

            # 創建分片
            shard, file_path = create_market_data_shard(
                self.session,
                table_class,
                params["start_date"],
                params["end_date"],
                symbols
            )

            # 更新快取
            self._update_shard_cache(table_class.__tablename__)

            logger.info(f"創建新分片: {shard.shard_id}, 檔案路徑: {file_path}")
            return shard, file_path

        except (ShardingConfigError, ShardingOperationError):
            raise
        except Exception as e:
            raise ShardingOperationError(f"創建分片時發生未預期錯誤: {e}") from e

    def get_shards_for_query(
        self,
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
        start_date: date,
        end_date: date,
        symbols: Optional[List[str]] = None
    ) -> List[DataShard]:
        """獲取查詢所需的分片列表.

        Args:
            table_class: 資料表類別
            start_date: 查詢開始日期
            end_date: 查詢結束日期
            symbols: 股票代碼列表

        Returns:
            List[DataShard]: 相關的分片列表

        Raises:
            ShardingOperationError: 當查詢過程中發生錯誤時
        """
        if start_date > end_date:
            raise ShardingOperationError("開始日期不能大於結束日期")

        try:
            query = (
                self.session.query(DataShard)
                .filter_by(table_name=table_class.__tablename__)
                .filter(
                    and_(
                        DataShard.start_date <= end_date,
                        DataShard.end_date >= start_date
                    )
                )
                .order_by(DataShard.start_date)
            )

            shards = query.all()

            # 如果指定了股票代碼，進一步過濾
            if symbols:
                # 目前簡單返回所有分片，未來可以實現更複雜的過濾邏輯
                # 例如根據分片的元數據來判斷是否包含特定股票代碼
                return shards

            return shards

        except Exception as e:
            raise ShardingOperationError(f"查詢分片時發生錯誤: {e}") from e

    def query_across_shards(
        self,
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
        start_date: date,
        end_date: date,
        symbols: Optional[List[str]] = None,
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """跨分片查詢資料.

        Args:
            table_class: 資料表類別
            start_date: 查詢開始日期
            end_date: 查詢結束日期
            symbols: 股票代碼列表
            columns: 要查詢的欄位

        Returns:
            pd.DataFrame: 查詢結果

        Raises:
            ShardingOperationError: 當查詢過程中發生錯誤時
        """
        try:
            # 獲取相關分片
            shards = self.get_shards_for_query(table_class, start_date, end_date, symbols)

            if not shards:
                logger.warning(f"未找到相關分片: {table_class.__tablename__}")
                return pd.DataFrame()

            # 從各個分片讀取資料
            dataframes = []
            for shard in shards:
                try:
                    df = load_from_shard(self.session, shard.shard_id, columns)

                    if df.empty:
                        continue

                    # 根據日期範圍過濾
                    df = self._filter_by_date_range(df, table_class, start_date, end_date)

                    # 根據股票代碼過濾
                    if symbols and 'symbol' in df.columns:
                        df = df[df['symbol'].isin(symbols)]

                    if not df.empty:
                        dataframes.append(df)

                except Exception as e:
                    logger.error(f"讀取分片 {shard.shard_id} 時發生錯誤: {e}")
                    continue

            # 合併所有資料
            return self._merge_dataframes(dataframes, table_class)

        except Exception as e:
            raise ShardingOperationError(f"跨分片查詢時發生錯誤: {e}") from e

    def _filter_by_date_range(
        self,
        df: pd.DataFrame,
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
        start_date: date,
        end_date: date
    ) -> pd.DataFrame:
        """根據日期範圍過濾資料."""
        if table_class == MarketDaily:
            date_col = 'date'
        else:
            date_col = 'timestamp'

        if date_col in df.columns:
            df = df[
                (pd.to_datetime(df[date_col]).dt.date >= start_date) &
                (pd.to_datetime(df[date_col]).dt.date <= end_date)
            ]

        return df

    def _merge_dataframes(
        self,
        dataframes: List[pd.DataFrame],
        table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]]
    ) -> pd.DataFrame:
        """合併多個 DataFrame."""
        if not dataframes:
            return pd.DataFrame()

        result = pd.concat(dataframes, ignore_index=True)

        # 根據時間排序
        if table_class == MarketDaily and 'date' in result.columns:
            result = result.sort_values('date')
        elif 'timestamp' in result.columns:
            result = result.sort_values('timestamp')

        return result

    def _update_shard_cache(self, table_name: str) -> None:
        """更新分片快取.

        Args:
            table_name: 資料表名稱
        """
        try:
            with self.lock:
                shards = (
                    self.session.query(DataShard)
                    .filter_by(table_name=table_name)
                    .order_by(DataShard.start_date)
                    .all()
                )
                self.shard_cache[table_name] = shards
                logger.debug(f"更新分片快取: {table_name}, 共 {len(shards)} 個分片")
        except Exception as e:
            logger.error(f"更新分片快取失敗: {e}")

    def get_shard_statistics(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """獲取分片統計資訊.

        Args:
            table_name: 資料表名稱，如果為 None 則返回所有表的統計

        Returns:
            Dict[str, Any]: 分片統計資訊

        Raises:
            ShardingOperationError: 當獲取統計資訊時發生錯誤
        """
        try:
            if table_name:
                return self._get_table_statistics(table_name)
            else:
                return self._get_all_tables_statistics()
        except Exception as e:
            raise ShardingOperationError(f"獲取分片統計時發生錯誤: {e}") from e

    def _get_table_statistics(self, table_name: str) -> Dict[str, Any]:
        """獲取單個表的統計資訊."""
        shards = (
            self.session.query(DataShard)
            .filter_by(table_name=table_name)
            .all()
        )

        total_rows = sum(shard.row_count or 0 for shard in shards)
        total_size = sum(shard.file_size_bytes or 0 for shard in shards)

        return {
            "table_name": table_name,
            "shard_count": len(shards),
            "total_rows": total_rows,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024) if total_size > 0 else 0,
            "shards": [
                {
                    "shard_id": shard.shard_id,
                    "start_date": shard.start_date,
                    "end_date": shard.end_date,
                    "row_count": shard.row_count,
                    "file_size_bytes": shard.file_size_bytes
                }
                for shard in shards
            ]
        }

    def _get_all_tables_statistics(self) -> Dict[str, Any]:
        """獲取所有表的統計資訊."""
        all_shards = self.session.query(DataShard).all()
        stats_by_table: Dict[str, Dict[str, Any]] = {}

        for shard in all_shards:
            table = shard.table_name
            if table not in stats_by_table:
                stats_by_table[table] = {
                    "shard_count": 0,
                    "total_rows": 0,
                    "total_size_bytes": 0
                }

            stats_by_table[table]["shard_count"] += 1
            stats_by_table[table]["total_rows"] += shard.row_count or 0
            stats_by_table[table]["total_size_bytes"] += shard.file_size_bytes or 0

        # 計算 MB
        for table_stats in stats_by_table.values():
            total_size = table_stats["total_size_bytes"]
            table_stats["total_size_mb"] = total_size / (1024 * 1024) if total_size > 0 else 0

        return stats_by_table
