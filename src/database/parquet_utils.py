# -*- coding: utf-8 -*-
"""
Parquet/Arrow 格式工具模組

此模組提供將資料庫資料轉換為 Parquet/Arrow 格式的功能，
用於壓縮歷史資料並提高查詢效能。

主要功能：
- 將 SQLAlchemy 查詢結果轉換為 Pandas DataFrame
- 將 DataFrame 儲存為 Parquet 格式
- 從 Parquet 檔案讀取資料
- 管理 Parquet 檔案的分片和合併
- 增強 Apache Arrow 格式支援
- 優化檔案 I/O 操作效能

Example:
    >>> from src.database.parquet_utils import save_to_parquet, read_from_parquet
    >>> df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
    >>> file_path = save_to_parquet(df, 'test.parquet')
    >>> loaded_df = read_from_parquet(file_path)
"""

import logging
import os
from datetime import date
from typing import Any, Dict, List, Optional, Tuple, Type, Union

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.feather as feather
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from src.config import DATA_DIR
from src.database.schema import Base, DataShard, MarketDaily, MarketMinute, MarketTick, create_data_shard

logger = logging.getLogger(__name__)


class ParquetError(Exception):
    """Parquet 操作相關的異常類別."""
    pass


class ParquetConfigError(ParquetError):
    """Parquet 配置錯誤."""
    pass


class ParquetOperationError(ParquetError):
    """Parquet 操作錯誤."""
    pass


def query_to_dataframe(session: Session, query: Any) -> pd.DataFrame:
    """將 SQLAlchemy 查詢結果轉換為 Pandas DataFrame.

    Args:
        session: SQLAlchemy 會話
        query: SQLAlchemy 查詢物件

    Returns:
        pd.DataFrame: 查詢結果的 DataFrame

    Raises:
        ParquetConfigError: 當會話或查詢無效時
        ParquetOperationError: 當轉換過程中發生錯誤時
    """
    if session is None:
        raise ParquetConfigError("SQLAlchemy 會話不能為 None")
    if query is None:
        raise ParquetConfigError("查詢物件不能為 None")

    try:
        result = session.execute(query).fetchall()
        if not result:
            return pd.DataFrame()

        # 檢查是否為 ORM 對象
        if hasattr(result[0], "_mapping"):
            return _process_mapping_result(result)
        else:
            # 非 ORM 對象，直接轉換
            return pd.DataFrame(result)

    except (ParquetConfigError, ParquetOperationError):
        raise
    except Exception as e:
        raise ParquetOperationError(f"查詢轉換 DataFrame 時發生錯誤: {e}") from e


def _process_mapping_result(result: List[Any]) -> pd.DataFrame:
    """處理具有 _mapping 屬性的查詢結果."""
    # 獲取列名
    columns = list(result[0]._mapping.keys())

    # 檢查是否為單一 ORM 對象
    if len(columns) == 1 and isinstance(result[0][0], Base):
        return _convert_orm_objects_to_dataframe(result)
    else:
        # 一般情況，直接使用 _mapping
        return _convert_mapping_to_dataframe(result)


def _convert_orm_objects_to_dataframe(result: List[Any]) -> pd.DataFrame:
    """將 ORM 對象轉換為 DataFrame."""
    data = []
    for row in result:
        orm_obj = row[0]
        obj_dict = _extract_orm_attributes(orm_obj)
        data.append(obj_dict)

    return pd.DataFrame(data) if data else pd.DataFrame()


def _extract_orm_attributes(orm_obj: Any) -> Dict[str, Any]:
    """提取 ORM 對象的屬性."""
    obj_dict = {}
    for c in orm_obj.__table__.columns:
        value = getattr(orm_obj, c.name)
        # 處理枚舉類型
        if hasattr(value, "value"):
            obj_dict[c.name] = value.value
        else:
            obj_dict[c.name] = value
    return obj_dict


def _convert_mapping_to_dataframe(result: List[Any]) -> pd.DataFrame:
    """將 _mapping 結果轉換為 DataFrame."""
    data = []
    for row in result:
        row_dict = {}
        for key, value in row._mapping.items():
            # 處理枚舉類型
            if hasattr(value, "value"):
                row_dict[key] = value.value
            else:
                row_dict[key] = value
        data.append(row_dict)
    return pd.DataFrame(data)


def save_to_parquet(
    df: pd.DataFrame,
    file_path: str,
    compression: str = "snappy",
    partition_cols: Optional[List[str]] = None,
) -> str:
    """將 DataFrame 儲存為 Parquet 格式.

    Args:
        df: 要儲存的 DataFrame
        file_path: 檔案路徑
        compression: 壓縮方式，預設為 "snappy"
        partition_cols: 分區欄位，預設為 None

    Returns:
        str: 儲存的檔案路徑

    Raises:
        ParquetConfigError: 當參數無效時
        ParquetOperationError: 當儲存過程中發生錯誤時
    """
    if df is None:
        raise ParquetConfigError("DataFrame 不能為 None")
    if not file_path or not file_path.strip():
        raise ParquetConfigError("檔案路徑不能為空")
    if compression not in {"snappy", "gzip", "lz4", "zstd", "brotli", "none"}:
        raise ParquetConfigError(f"不支援的壓縮格式: {compression}")

    try:
        # 確保目錄存在
        _ensure_directory_exists(file_path)

        # 轉換為 PyArrow Table
        table = pa.Table.from_pandas(df)

        # 儲存為 Parquet 格式
        if partition_cols:
            _save_partitioned_parquet(table, file_path, partition_cols, compression)
        else:
            _save_single_parquet(table, file_path, compression)

        logger.info(f"成功儲存 Parquet 檔案: {file_path}")
        return file_path

    except (ParquetConfigError, ParquetOperationError):
        raise
    except Exception as e:
        raise ParquetOperationError(f"儲存 Parquet 檔案時發生錯誤: {e}") from e


def _ensure_directory_exists(file_path: str) -> None:
    """確保目錄存在."""
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def _save_partitioned_parquet(
    table: pa.Table,
    file_path: str,
    partition_cols: List[str],
    compression: str
) -> None:
    """儲存分區 Parquet 檔案."""
    pq.write_to_dataset(
        table,
        root_path=file_path,
        partition_cols=partition_cols,
        compression=compression,
    )


def _save_single_parquet(table: pa.Table, file_path: str, compression: str) -> None:
    """儲存單一 Parquet 檔案."""
    pq.write_table(table, file_path, compression=compression)


def read_from_parquet(
    file_path: str,
    columns: Optional[List[str]] = None,
    filters: Optional[List[Any]] = None
) -> pd.DataFrame:
    """從 Parquet 檔案讀取資料.

    Args:
        file_path: 檔案路徑
        columns: 要讀取的欄位，預設為 None (讀取所有欄位)
        filters: 過濾條件，預設為 None

    Returns:
        pd.DataFrame: 讀取的 DataFrame

    Raises:
        ParquetConfigError: 當檔案路徑無效時
        ParquetOperationError: 當讀取過程中發生錯誤時
    """
    if not file_path or not file_path.strip():
        raise ParquetConfigError("檔案路徑不能為空")
    if not os.path.exists(file_path):
        raise ParquetConfigError(f"檔案或目錄不存在: {file_path}")

    try:
        if os.path.isdir(file_path):
            # 讀取分區資料集
            df = pd.read_parquet(file_path, columns=columns, filters=filters)
        else:
            # 讀取單一檔案
            df = pd.read_parquet(file_path, columns=columns, filters=filters)

        logger.info(f"成功讀取 Parquet 檔案: {file_path}, 行數: {len(df)}")
        return df

    except (ParquetConfigError, ParquetOperationError):
        raise
    except Exception as e:
        raise ParquetOperationError(f"讀取 Parquet 檔案時發生錯誤: {e}") from e


def save_to_arrow(
    df: pd.DataFrame,
    file_path: str,
    compression: str = "lz4"
) -> str:
    """將 DataFrame 儲存為 Arrow (Feather) 格式.

    Args:
        df: 要儲存的 DataFrame
        file_path: 檔案路徑
        compression: 壓縮方式，預設為 "lz4"

    Returns:
        str: 儲存的檔案路徑

    Raises:
        ParquetConfigError: 當參數無效時
        ParquetOperationError: 當儲存過程中發生錯誤時
    """
    if df is None:
        raise ParquetConfigError("DataFrame 不能為 None")
    if not file_path or not file_path.strip():
        raise ParquetConfigError("檔案路徑不能為空")
    if compression not in {"lz4", "zstd", "uncompressed"}:
        raise ParquetConfigError(f"Arrow 格式不支援的壓縮格式: {compression}")

    try:
        # 確保目錄存在
        _ensure_directory_exists(file_path)

        # 轉換為 PyArrow Table
        table = pa.Table.from_pandas(df)

        # 儲存為 Arrow 格式
        feather.write_feather(table, file_path, compression=compression)

        logger.info(f"成功儲存 Arrow 檔案: {file_path}")
        return file_path

    except (ParquetConfigError, ParquetOperationError):
        raise
    except Exception as e:
        raise ParquetOperationError(f"儲存 Arrow 檔案時發生錯誤: {e}") from e


def read_from_arrow(
    file_path: str,
    columns: Optional[List[str]] = None
) -> pd.DataFrame:
    """從 Arrow (Feather) 檔案讀取資料.

    Args:
        file_path: 檔案路徑
        columns: 要讀取的欄位，預設為 None (讀取所有欄位)

    Returns:
        pd.DataFrame: 讀取的 DataFrame

    Raises:
        ParquetConfigError: 當檔案路徑無效時
        ParquetOperationError: 當讀取過程中發生錯誤時
    """
    if not file_path or not file_path.strip():
        raise ParquetConfigError("檔案路徑不能為空")
    if not os.path.exists(file_path):
        raise ParquetConfigError(f"檔案不存在: {file_path}")

    try:
        df = feather.read_feather(file_path, columns=columns)
        logger.info(f"成功讀取 Arrow 檔案: {file_path}, 行數: {len(df)}")
        return df

    except (ParquetConfigError, ParquetOperationError):
        raise
    except Exception as e:
        raise ParquetOperationError(f"讀取 Arrow 檔案時發生錯誤: {e}") from e


def create_market_data_shard(
    session: Session,
    table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
    start_date: date,
    end_date: date,
    symbols: Optional[List[str]] = None,
    compression: str = "snappy",
) -> Tuple[DataShard, str]:
    """創建市場資料分片並儲存為 Parquet 格式.

    Args:
        session: SQLAlchemy 會話
        table_class: 資料表類別 (MarketDaily, MarketMinute, MarketTick)
        start_date: 開始日期
        end_date: 結束日期
        symbols: 股票代碼列表，預設為 None (所有股票)
        compression: 壓縮方式，預設為 "snappy"

    Returns:
        Tuple[DataShard, str]: 資料分片記錄和檔案路徑

    Raises:
        ParquetConfigError: 當參數無效時
        ParquetOperationError: 當創建過程中發生錯誤時
    """
    if session is None:
        raise ParquetConfigError("SQLAlchemy 會話不能為 None")
    if start_date > end_date:
        raise ParquetConfigError("開始日期不能大於結束日期")

    try:
        # 構建查詢
        query = _build_market_data_query(table_class, start_date, end_date, symbols)

        # 查詢資料
        df = query_to_dataframe(session, query)

        if df.empty:
            raise ParquetOperationError(f"沒有找到符合條件的資料: {start_date} - {end_date}")

        # 生成檔案路徑
        file_path = _generate_shard_file_path(table_class, start_date, end_date, symbols)

        # 儲存為 Parquet 格式
        save_to_parquet(df, file_path, compression=compression)

        # 創建資料分片記錄
        shard = _create_shard_record(session, table_class, start_date, end_date, file_path, compression, df, symbols)

        logger.info(f"成功創建市場資料分片: {shard.shard_id}")
        return shard, file_path

    except (ParquetConfigError, ParquetOperationError):
        raise
    except Exception as e:
        raise ParquetOperationError(f"創建市場資料分片時發生錯誤: {e}") from e


def _build_market_data_query(
    table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
    start_date: date,
    end_date: date,
    symbols: Optional[List[str]]
) -> Any:
    """構建市場資料查詢."""
    query = select(table_class)

    # 根據資料表類別選擇日期欄位
    if table_class == MarketDaily:
        date_column = table_class.date
    else:
        date_column = func.date(table_class.timestamp)

    # 添加日期範圍條件
    query = query.where(and_(date_column >= start_date, date_column <= end_date))

    # 添加股票代碼條件
    if symbols:
        query = query.where(table_class.symbol.in_(symbols))

    return query


def _generate_shard_file_path(
    table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
    start_date: date,
    end_date: date,
    symbols: Optional[List[str]]
) -> str:
    """生成分片檔案路徑."""
    table_name = table_class.__tablename__
    date_format = "%Y%m%d"
    date_range = f"{start_date.strftime(date_format)}_{end_date.strftime(date_format)}"

    if symbols and len(symbols) <= 5:
        symbol_str = "_".join(symbols)
        file_name = f"{table_name}_{date_range}_{symbol_str}.parquet"
    else:
        file_name = f"{table_name}_{date_range}.parquet"

    return os.path.join(DATA_DIR, "parquet", table_name, file_name)


def _create_shard_record(
    session: Session,
    table_class: Type[Union[MarketDaily, MarketMinute, MarketTick]],
    start_date: date,
    end_date: date,
    file_path: str,
    compression: str,
    df: pd.DataFrame,
    symbols: Optional[List[str]]
) -> DataShard:
    """創建分片記錄."""
    table_name = table_class.__tablename__
    shard_key = "date" if table_class == MarketDaily else "timestamp"

    shard = create_data_shard(
        session, table_name, start_date, end_date, shard_key=shard_key
    )

    # 更新分片記錄
    shard.file_path = file_path
    shard.file_format = "parquet"
    shard.compression = compression
    shard.row_count = len(df)
    shard.file_size_bytes = os.path.getsize(file_path)
    shard.is_compressed = True

    # 如果有股票代碼條件，記錄在分片記錄中
    if symbols:
        date_format = "%Y%m%d"
        date_range = f"{start_date.strftime(date_format)}_{end_date.strftime(date_format)}"
        shard.shard_id = f"{table_name}_{date_range}_{'_'.join(symbols[:3])}"

    session.commit()
    return shard


def load_from_shard(
    session: Session,
    shard_id: str,
    columns: Optional[List[str]] = None,
    filters: Optional[List[Any]] = None,
) -> pd.DataFrame:
    """從資料分片讀取資料.

    Args:
        session: SQLAlchemy 會話
        shard_id: 分片 ID
        columns: 要讀取的欄位，預設為 None (讀取所有欄位)
        filters: 過濾條件，預設為 None

    Returns:
        pd.DataFrame: 讀取的 DataFrame

    Raises:
        ParquetConfigError: 當參數無效時
        ParquetOperationError: 當讀取過程中發生錯誤時
    """
    if session is None:
        raise ParquetConfigError("SQLAlchemy 會話不能為 None")
    if not shard_id or not shard_id.strip():
        raise ParquetConfigError("分片 ID 不能為空")

    try:
        # 查詢分片記錄
        shard = session.query(DataShard).filter_by(shard_id=shard_id.strip()).first()

        if not shard:
            raise ParquetOperationError(f"找不到分片記錄: {shard_id}")

        if not shard.file_path or not os.path.exists(shard.file_path):
            raise ParquetOperationError(f"找不到分片檔案: {shard.file_path}")

        # 根據檔案格式選擇讀取方法
        if shard.file_format == "arrow" or shard.file_path.endswith('.feather'):
            df = read_from_arrow(shard.file_path, columns=columns)
        else:
            # 預設使用 Parquet 格式
            df = read_from_parquet(shard.file_path, columns=columns, filters=filters)

        logger.info(f"成功從分片讀取資料: {shard_id}, 行數: {len(df)}")
        return df

    except (ParquetConfigError, ParquetOperationError):
        raise
    except Exception as e:
        raise ParquetOperationError(f"從分片讀取資料時發生錯誤: {e}") from e
