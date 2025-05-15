"""
Parquet/Arrow 格式工具模組

此模組提供將資料庫資料轉換為 Parquet/Arrow 格式的功能，
用於壓縮歷史資料並提高查詢效能。

主要功能：
- 將 SQLAlchemy 查詢結果轉換為 Pandas DataFrame
- 將 DataFrame 儲存為 Parquet 格式
- 從 Parquet 檔案讀取資料
- 管理 Parquet 檔案的分片和合併
"""

import os
from datetime import date
from typing import List, Optional, Tuple

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from src.config import DATA_DIR
from src.database.schema import Base, DataShard, MarketDaily, create_data_shard


def query_to_dataframe(session: Session, query) -> pd.DataFrame:
    """
    將 SQLAlchemy 查詢結果轉換為 Pandas DataFrame

    Args:
        session: SQLAlchemy 會話
        query: SQLAlchemy 查詢物件

    Returns:
        pd.DataFrame: 查詢結果的 DataFrame
    """
    result = session.execute(query).fetchall()
    if not result:
        return pd.DataFrame()

    # 檢查是否為 ORM 對象
    if hasattr(result[0], "_mapping"):
        # 獲取列名
        columns = list(result[0]._mapping.keys())

        # 檢查是否為單一 ORM 對象
        if len(columns) == 1 and isinstance(result[0][0], Base):
            # 將 ORM 對象轉換為字典列表
            data = []
            for row in result:
                orm_obj = row[0]
                # 獲取 ORM 對象的屬性
                obj_dict = {}
                for c in orm_obj.__table__.columns:
                    value = getattr(orm_obj, c.name)
                    # 處理枚舉類型
                    if hasattr(value, "value"):
                        obj_dict[c.name] = value.value
                    else:
                        obj_dict[c.name] = value
                data.append(obj_dict)

            # 創建 DataFrame
            if data:
                return pd.DataFrame(data)
            else:
                return pd.DataFrame()
        else:
            # 一般情況，直接使用 _mapping
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
    else:
        # 非 ORM 對象，直接轉換
        return pd.DataFrame(result)


def save_to_parquet(
    df: pd.DataFrame,
    file_path: str,
    compression: str = "snappy",
    partition_cols: Optional[List[str]] = None,
) -> str:
    """
    將 DataFrame 儲存為 Parquet 格式

    Args:
        df: 要儲存的 DataFrame
        file_path: 檔案路徑
        compression: 壓縮方式，預設為 "snappy"
        partition_cols: 分區欄位，預設為 None

    Returns:
        str: 儲存的檔案路徑
    """
    # 確保目錄存在
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # 轉換為 PyArrow Table
    table = pa.Table.from_pandas(df)

    # 儲存為 Parquet 格式
    if partition_cols:
        pq.write_to_dataset(
            table,
            root_path=file_path,
            partition_cols=partition_cols,
            compression=compression,
        )
    else:
        pq.write_table(table, file_path, compression=compression)

    return file_path


def read_from_parquet(
    file_path: str, columns: Optional[List[str]] = None, filters: Optional[List] = None
) -> pd.DataFrame:
    """
    從 Parquet 檔案讀取資料

    Args:
        file_path: 檔案路徑
        columns: 要讀取的欄位，預設為 None (讀取所有欄位)
        filters: 過濾條件，預設為 None

    Returns:
        pd.DataFrame: 讀取的 DataFrame
    """
    if os.path.isdir(file_path):
        # 讀取分區資料集
        return pd.read_parquet(file_path, columns=columns, filters=filters)
    else:
        # 讀取單一檔案
        return pd.read_parquet(file_path, columns=columns, filters=filters)


def create_market_data_shard(
    session: Session,
    table_class,
    start_date: date,
    end_date: date,
    symbols: Optional[List[str]] = None,
    compression: str = "snappy",
) -> Tuple[DataShard, str]:
    """
    創建市場資料分片並儲存為 Parquet 格式

    Args:
        session: SQLAlchemy 會話
        table_class: 資料表類別 (MarketDaily, MarketMinute, MarketTick)
        start_date: 開始日期
        end_date: 結束日期
        symbols: 股票代碼列表，預設為 None (所有股票)
        compression: 壓縮方式，預設為 "snappy"

    Returns:
        Tuple[DataShard, str]: 資料分片記錄和檔案路徑
    """
    # 構建查詢
    query = select(table_class)

    # 根據資料表類別選擇日期欄位
    if table_class == MarketDaily:
        date_column = table_class.date
        date_format = "%Y%m%d"
    else:
        date_column = func.date(table_class.timestamp)
        date_format = "%Y%m%d"

    # 添加日期範圍條件
    query = query.where(and_(date_column >= start_date, date_column <= end_date))

    # 添加股票代碼條件
    if symbols:
        query = query.where(table_class.symbol.in_(symbols))

    # 查詢資料
    df = query_to_dataframe(session, query)

    if df.empty:
        raise ValueError(f"沒有找到符合條件的資料: {start_date} - {end_date}")

    # 生成檔案路徑
    table_name = table_class.__tablename__
    date_range = f"{start_date.strftime(date_format)}_{end_date.strftime(date_format)}"

    if symbols and len(symbols) <= 5:
        symbol_str = "_".join(symbols)
        file_name = f"{table_name}_{date_range}_{symbol_str}.parquet"
    else:
        file_name = f"{table_name}_{date_range}.parquet"

    file_path = os.path.join(DATA_DIR, "parquet", table_name, file_name)

    # 儲存為 Parquet 格式
    save_to_parquet(df, file_path, compression=compression)

    # 創建資料分片記錄
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
        shard.shard_id = f"{table_name}_{date_range}_{'_'.join(symbols[:3])}"

    session.commit()

    return shard, file_path


def load_from_shard(
    session: Session,
    shard_id: str,
    columns: Optional[List[str]] = None,
    filters: Optional[List] = None,
) -> pd.DataFrame:
    """
    從資料分片讀取資料

    Args:
        session: SQLAlchemy 會話
        shard_id: 分片 ID
        columns: 要讀取的欄位，預設為 None (讀取所有欄位)
        filters: 過濾條件，預設為 None

    Returns:
        pd.DataFrame: 讀取的 DataFrame
    """
    # 查詢分片記錄
    shard = session.query(DataShard).filter_by(shard_id=shard_id).first()

    if not shard:
        raise ValueError(f"找不到分片記錄: {shard_id}")

    if not shard.file_path or not os.path.exists(shard.file_path):
        raise ValueError(f"找不到分片檔案: {shard.file_path}")

    # 讀取 Parquet 檔案
    return read_from_parquet(shard.file_path, columns=columns, filters=filters)
