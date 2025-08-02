"""資料庫 Schema 定義模組

此模組為向後相容性而保留，所有新的模型定義已移至 models 子模組。

此模組重新導出所有模型以確保現有程式碼繼續正常運作。

Note:
    新的程式碼建議直接從 src.database.models 導入模型。
    
Example:
    >>> # 舊的導入方式（仍然支援）
    >>> from src.database.schema import MarketDaily, TradeRecord
    >>> 
    >>> # 新的導入方式（推薦）
    >>> from src.database.models import MarketDaily, TradeRecord
"""

from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import Session

# 從新的模組結構導入所有模型以保持向後相容性
from .models import *  # noqa: F401, F403

# 為了向後相容性，創建一些簡單的類別
try:
    # 嘗試從 models 導入，如果成功就不需要創建備用類
    from .models import RiskParameter, RiskControlStatus

    # 創建一些簡單的備用類別
    class ReportCache:
        """報表快取類（向後相容性）"""
        def __init__(self, cache_key=None, cache_data=None, expires_at=None, created_at=None):
            self.cache_key = cache_key
            self.cache_data = cache_data
            self.expires_at = expires_at
            self.created_at = created_at

except ImportError:
    # 如果導入失敗，創建簡單的 SQLAlchemy 替代類
    class RiskParameter(Base):
        """風險參數表（向後相容性）"""
        __tablename__ = "risk_parameters"

        id = Column(Integer, primary_key=True, autoincrement=True)
        parameter_name = Column(String(50), nullable=False)
        parameter_value = Column(String(100), nullable=False)
        parameter_type = Column(String(20), default="string")
        category = Column(String(50), default="general")
        description = Column(Text, default="")
        is_system = Column(Boolean, default=False)
        is_active = Column(Boolean, default=True)
        min_value = Column(String(50), nullable=True)
        max_value = Column(String(50), nullable=True)
        default_value = Column(String(100), nullable=True)
        updated_at = Column(DateTime, nullable=True)
        created_at = Column(
            DateTime,
            default=lambda: datetime.now(timezone.utc)
        )

    class RiskControlStatus(Base):
        """風險控制狀態表（向後相容性）"""
        __tablename__ = "risk_control_status"

        id = Column(Integer, primary_key=True, autoincrement=True)
        control_name = Column(String(50), nullable=False)
        control_type = Column(String(50), default="general")
        is_enabled = Column(Boolean, default=True)
        is_master_enabled = Column(Boolean, default=True)
        emergency_stop = Column(Boolean, default=False)
        status_name = Column(String(50), nullable=True)  # 保持向後兼容
        is_active = Column(Boolean, default=True)  # 保持向後兼容
        created_at = Column(
            DateTime,
            default=lambda: datetime.now(timezone.utc)
        )


class TradingOrder(Base):
        """交易訂單表（向後相容性）"""
        __tablename__ = "trading_orders"

        id = Column(Integer, primary_key=True, autoincrement=True)
        order_id = Column(String(50), nullable=False, unique=True)
        symbol = Column(String(20), nullable=False)
        order_type = Column(String(20), nullable=False)
        quantity = Column(Integer, nullable=False)
        price = Column(String(20), nullable=True)
        status = Column(String(20), default="pending")
        created_at = Column(
            DateTime,
            default=lambda: datetime.now(timezone.utc)
        )


class TradeExecution(Base):
        """交易執行表（向後相容性）"""
        __tablename__ = "trade_executions"

        id = Column(Integer, primary_key=True, autoincrement=True)
        execution_id = Column(String(50), nullable=False, unique=True)
        order_id = Column(String(50), nullable=False)
        symbol = Column(String(20), nullable=False)
        action = Column(String(20), nullable=False)
        quantity = Column(Integer, nullable=False)
        price = Column(String(20), nullable=True)
        amount = Column(String(20), nullable=True)
        commission = Column(String(20), nullable=True)
        tax = Column(String(20), nullable=True)
        net_amount = Column(String(20), nullable=True)
        execution_time = Column(DateTime, nullable=True)
        broker = Column(String(50), nullable=True)
        execution_venue = Column(String(50), nullable=True)
        created_at = Column(
            DateTime,
            default=lambda: datetime.now(timezone.utc)
        )


# 創建報表相關的 SQLAlchemy 替代類
class ReportTemplate(Base):
        """報表模板表（向後相容性）"""
        __tablename__ = "report_templates"

        id = Column(Integer, primary_key=True, autoincrement=True)
        template_id = Column(String(50), nullable=False, unique=True)
        name = Column(String(100), nullable=False)
        description = Column(Text, nullable=True)
        report_type = Column(String(50), nullable=False)
        template_config = Column(Text, nullable=False)
        created_at = Column(
            DateTime,
            default=lambda: datetime.now(timezone.utc)
        )


class ChartConfig(Base):
        """圖表配置表（向後相容性）"""
        __tablename__ = "chart_configs"

        id = Column(Integer, primary_key=True, autoincrement=True)
        config_name = Column(String(100), nullable=False)
        chart_type = Column(String(50), nullable=False)
        config_data = Column(Text, nullable=False)
        description = Column(Text, nullable=True)
        created_by = Column(String(50), nullable=False)
        created_at = Column(
            DateTime,
            default=lambda: datetime.now(timezone.utc)
        )


class ExportLog(Base):
        """匯出日誌表（向後相容性）"""
        __tablename__ = "export_logs"

        id = Column(Integer, primary_key=True, autoincrement=True)
        export_id = Column(String(50), nullable=False, unique=True)
        export_format = Column(String(20), nullable=False)
        user_id = Column(String(50), nullable=False)
        status = Column(String(20), default="processing")
        file_path = Column(String(255), nullable=True)
        created_at = Column(
            DateTime,
            default=lambda: datetime.now(timezone.utc)
        )
        completed_at = Column(DateTime, nullable=True)


class ReportCache(Base):
        """報表快取表（向後相容性）"""
        __tablename__ = "report_cache"

        id = Column(Integer, primary_key=True, autoincrement=True)
        cache_key = Column(String(100), nullable=False, unique=True)
        cache_data = Column(Text, nullable=False)
        expires_at = Column(DateTime, nullable=False)
        created_at = Column(
            DateTime,
            default=lambda: datetime.now(timezone.utc)
        )
        updated_at = Column(DateTime, nullable=True)


# 為了向後相容性，添加一些舊的模型定義
class DataChecksum(Base):
    """資料校驗碼表（向後相容性）"""
    __tablename__ = "data_checksum"

    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(50), nullable=False, comment="資料表名稱")
    record_id = Column(String(50), nullable=False, comment="記錄ID")
    checksum = Column(String(64), nullable=False, comment="校驗碼")
    checksum_fields = Column(Text, comment="校驗欄位列表（JSON格式）")
    is_valid = Column(Boolean, default=True, comment="是否有效")
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment="建立時間"
    )


class DataShard(Base):
    """資料分片表（向後相容性）"""
    __tablename__ = "data_shard"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shard_key = Column(String(50), nullable=False, comment="分片鍵")
    table_name = Column(String(50), nullable=False, comment="資料表名稱")
    start_date = Column(String(20), comment="開始日期")
    end_date = Column(String(20), comment="結束日期")
    description = Column(Text, comment="描述")
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment="建立時間"
    )


def init_db(engine):
    """初始化資料庫

    創建所有資料表並設置初始資料。

    Args:
        engine: SQLAlchemy 引擎

    Example:
        >>> from sqlalchemy import create_engine
        >>> from src.database.schema import init_db
        >>> engine = create_engine("sqlite:///test.db")
        >>> init_db(engine)
    """
    # 創建所有資料表
    Base.metadata.create_all(engine)

    # 可以在這裡添加初始資料設置
    with Session(engine) as session:
        # 檢查是否需要初始化資料
        # 例如：創建預設的股票資訊等
        session.commit()


def create_data_shard(
    table_name: str,
    start_date: str,
    end_date: str,
    shard_key: str,
    session: Session
) -> DataShard:
    """創建資料分片

    為指定時間範圍的資料創建分片記錄。

    Args:
        table_name: 資料表名稱
        start_date: 開始日期
        end_date: 結束日期
        shard_key: 分片鍵
        session: 資料庫會話

    Returns:
        DataShard: 創建的分片記錄

    Example:
        >>> shard = create_data_shard(
        ...     "market_daily",
        ...     "2023-01-01",
        ...     "2023-12-31",
        ...     "2023",
        ...     session
        ... )
    """
    shard = DataShard(
        table_name=table_name,
        start_date=start_date,
        end_date=end_date,
        shard_key=shard_key,
        description=f"分片 {shard_key} for {table_name}"
    )
    session.add(shard)
    return shard


# 保留舊的函數名稱以向後相容
create_market_data_shard = create_data_shard
