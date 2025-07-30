# -*- coding: utf-8 -*-
"""統一資料庫連接工具模組

此模組提供統一的資料庫連接和初始化功能，避免在各個服務中重複實現。
整合了最佳實踐的資料庫連接管理、會話工廠創建和錯誤處理。

主要功能：
- 統一的資料庫引擎創建
- 會話工廠管理
- 資料庫初始化
- 連接池配置
- 錯誤處理和重試機制

Example:
    基本使用：
    ```python
    from src.utils.database_utils import get_database_session

    # 使用便捷函數獲取會話
    with get_database_session() as session:
        # 執行資料庫操作
        result = session.query(SomeModel).all()
    ```

Note:
    此模組整合了原本分散在各個服務中的資料庫連接邏輯，
    提供統一的介面和最佳實踐。
"""

import logging
import threading
from contextlib import contextmanager
from typing import Optional, Generator, Dict, Any, List
from datetime import datetime

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

# 導入配置和初始化函數
try:
    from src.config import DB_URL
    from src.database.schema import init_db
except ImportError as e:
    logging.warning("無法導入部分模組: %s", e)
    DB_URL = "sqlite:///data/market_data.db"

    def init_db(engine: Engine) -> None:
        """備用資料庫初始化函數

        Args:
            engine: SQLAlchemy 引擎

        Note:
            這是一個備用函數，當無法導入正式的 init_db 時使用。
        """
        logger.debug("使用備用 init_db 函數，引擎: %s", engine)

# 設定日誌
logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """資料庫操作錯誤"""
    pass


class DatabaseConnectionError(Exception):
    """資料庫連接錯誤

    當資料庫連接失敗時拋出此異常。
    """

    def __init__(self, message: str = "資料庫連接失敗"):
        """初始化異常

        Args:
            message: 錯誤訊息
        """
        self.message = message
        super().__init__(self.message)


class DatabaseConnectionManager:
    """統一資料庫連接管理器
    
    提供統一的資料庫連接管理功能，包括引擎創建、會話管理、
    連接池配置等。支援線程安全的操作。
    
    Attributes:
        engine: SQLAlchemy 引擎
        session_factory: 會話工廠
        lock: 線程鎖
        
    Example:
        >>> manager = DatabaseConnectionManager()
        >>> with manager.get_session() as session:
        ...     result = session.query(SomeModel).all()
    """
    
    _instance: Optional['DatabaseConnectionManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls, db_url: Optional[str] = None) -> 'DatabaseConnectionManager':
        """單例模式實現
        
        Args:
            db_url: 資料庫連接 URL
            
        Returns:
            DatabaseConnectionManager: 資料庫連接管理器實例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, db_url: Optional[str] = None):
        """初始化資料庫連接管理器
        
        Args:
            db_url: 資料庫連接 URL，如果為 None 則使用預設配置
            
        Raises:
            DatabaseConnectionError: 當資料庫初始化失敗時拋出
        """
        # 避免重複初始化
        if hasattr(self, '_initialized'):
            return
            
        self.db_url = db_url or DB_URL
        self.engine: Optional[Engine] = None
        self.session_factory: Optional[sessionmaker] = None
        self.lock = threading.Lock()
        
        # 初始化資料庫連接
        self._init_database()
        self._initialized = True
        
        logger.info("資料庫連接管理器初始化完成")
    
    def _init_database(self) -> None:
        """初始化資料庫連接
        
        建立資料庫引擎和會話工廠，並初始化資料庫結構。
        
        Raises:
            DatabaseConnectionError: 當資料庫初始化失敗時拋出
        """
        try:
            # 創建引擎，配置連接池
            self.engine = create_engine(
                self.db_url,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=3600,
                echo=False
            )
            
            # 創建會話工廠
            self.session_factory = sessionmaker(bind=self.engine)
            
            # 初始化資料庫結構
            init_db(self.engine)
            
            logger.info("資料庫連接初始化成功")
            
        except Exception as e:
            logger.error("資料庫連接初始化失敗: %s", e)
            raise DatabaseConnectionError("資料庫連接初始化失敗") from e
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """獲取資料庫會話（上下文管理器）
        
        提供線程安全的會話管理，自動處理會話的創建、提交和關閉。
        
        Yields:
            Session: SQLAlchemy 會話
            
        Raises:
            DatabaseConnectionError: 當會話創建失敗時拋出
            
        Example:
            >>> with manager.get_session() as session:
            ...     result = session.query(SomeModel).all()
        """
        if not self.session_factory:
            raise DatabaseConnectionError("會話工廠未初始化")
            
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error("資料庫操作失敗: %s", e)
            raise DatabaseConnectionError(f"資料庫操作失敗: {e}") from e
        except Exception as e:
            session.rollback()
            logger.error("未預期的錯誤: %s", e)
            raise
        finally:
            session.close()
    
    def get_engine(self) -> Engine:
        """獲取資料庫引擎
        
        Returns:
            Engine: SQLAlchemy 引擎
            
        Raises:
            DatabaseConnectionError: 當引擎未初始化時拋出
        """
        if not self.engine:
            raise DatabaseConnectionError("資料庫引擎未初始化")
        return self.engine
    
    def test_connection(self) -> bool:
        """測試資料庫連接
        
        Returns:
            bool: 連接是否正常
        """
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error("資料庫連接測試失敗: %s", e)
            return False
    
    def close(self) -> None:
        """關閉資料庫連接
        
        清理資源，關閉連接池。
        """
        if self.engine:
            self.engine.dispose()
            logger.info("資料庫連接已關閉")


# 全域資料庫連接管理器實例
_db_manager: Optional[DatabaseConnectionManager] = None


def get_database_manager(db_url: Optional[str] = None) -> DatabaseConnectionManager:
    """獲取全域資料庫連接管理器
    
    Args:
        db_url: 資料庫連接 URL
        
    Returns:
        DatabaseConnectionManager: 資料庫連接管理器實例
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseConnectionManager(db_url)
    return _db_manager


def get_database_session() -> Generator[Session, None, None]:
    """獲取資料庫會話的便捷函數
    
    Returns:
        Generator[Session, None, None]: 資料庫會話生成器
        
    Example:
        >>> with get_database_session() as session:
        ...     result = session.query(SomeModel).all()
    """
    manager = get_database_manager()
    return manager.get_session()


def upsert_chip_data(chip_data_list: List[Dict[str, Any]]) -> int:
    """批量 UPSERT 籌碼面資料

    使用 PostgreSQL 的 ON CONFLICT DO UPDATE 語法進行高效能的批量 UPSERT 操作。
    對於非 PostgreSQL 資料庫，會回退到傳統的查詢-更新模式。

    Args:
        chip_data_list: 籌碼面資料列表

    Returns:
        int: 成功處理的記錄數

    Raises:
        DatabaseError: 資料庫操作失敗
    """
    if not chip_data_list:
        return 0

    try:
        from src.database.models.integration_models import ChipData
        from sqlalchemy.dialects.postgresql import insert
        from sqlalchemy import text

        with get_database_session() as session:
            # 檢查資料庫類型
            db_dialect = session.bind.dialect.name

            if db_dialect == 'postgresql':
                # 使用 PostgreSQL 的高效能 UPSERT
                return _upsert_chip_data_postgresql(session, chip_data_list)
            else:
                # 使用通用的 UPSERT 邏輯
                return _upsert_chip_data_generic(session, chip_data_list)

    except Exception as e:
        logger.error("UPSERT 籌碼面資料失敗: %s", e)
        raise DatabaseError(f"UPSERT 籌碼面資料失敗: {e}")


def _upsert_chip_data_postgresql(session: Session, chip_data_list: List[Dict[str, Any]]) -> int:
    """PostgreSQL 專用的高效能 UPSERT 實現

    Args:
        session: 資料庫會話
        chip_data_list: 籌碼面資料列表

    Returns:
        int: 成功處理的記錄數
    """
    from src.database.models.integration_models import ChipData
    from sqlalchemy.dialects.postgresql import insert

    try:
        # 準備資料，確保所有必要欄位都存在
        prepared_data = []
        for chip_data in chip_data_list:
            # 設定預設值
            prepared_item = {
                'symbol': chip_data.get('symbol'),
                'date': chip_data.get('date'),
                'source': chip_data.get('source', 'TWSE'),
                'created_at': chip_data.get('created_at', datetime.now())
            }

            # 添加其他欄位
            optional_fields = [
                'foreign_buy', 'foreign_sell', 'investment_trust_buy', 'investment_trust_sell',
                'dealer_buy', 'dealer_sell', 'margin_balance', 'short_balance',
                'margin_quota', 'short_quota', 'margin_buy', 'margin_sell',
                'short_sell', 'short_cover', 'foreign_holding_ratio', 'foreign_holding_shares',
                'broker_id', 'broker_name', 'buy_amount', 'sell_amount', 'net_amount'
            ]

            for field in optional_fields:
                if field in chip_data:
                    prepared_item[field] = chip_data[field]

            prepared_data.append(prepared_item)

        # 執行 PostgreSQL UPSERT
        stmt = insert(ChipData).values(prepared_data)

        # 定義衝突時的更新欄位（排除主鍵和創建時間）
        update_fields = {
            field: stmt.excluded[field]
            for field in optional_fields
            if field in stmt.excluded
        }

        # ON CONFLICT DO UPDATE
        stmt = stmt.on_conflict_do_update(
            constraint='uq_chip_symbol_date_broker',
            set_=update_fields
        )

        result = session.execute(stmt)
        session.commit()

        processed_count = len(prepared_data)
        logger.info("PostgreSQL UPSERT 籌碼面資料成功: %d 筆", processed_count)
        return processed_count

    except Exception as e:
        logger.error("PostgreSQL UPSERT 籌碼面資料失敗: %s", e)
        raise


def _upsert_chip_data_generic(session: Session, chip_data_list: List[Dict[str, Any]]) -> int:
    """通用的 UPSERT 實現（適用於非 PostgreSQL 資料庫）

    Args:
        session: 資料庫會話
        chip_data_list: 籌碼面資料列表

    Returns:
        int: 成功處理的記錄數
    """
    from src.database.models.integration_models import ChipData

    processed_count = 0

    for chip_data in chip_data_list:
        try:
            # 檢查是否已存在
            existing = session.query(ChipData).filter(
                ChipData.symbol == chip_data.get('symbol'),
                ChipData.date == chip_data.get('date'),
                ChipData.broker_id == chip_data.get('broker_id')
            ).first()

            if existing:
                # 更新現有記錄
                for key, value in chip_data.items():
                    if hasattr(existing, key) and key not in ['id', 'created_at']:
                        setattr(existing, key, value)
            else:
                # 創建新記錄
                chip_data.setdefault('source', 'TWSE')
                chip_data.setdefault('created_at', datetime.now())
                new_record = ChipData(**chip_data)
                session.add(new_record)

            processed_count += 1

        except Exception as e:
            logger.warning("處理籌碼面資料記錄失敗: %s", e)
            continue

    session.commit()
    logger.info("通用 UPSERT 籌碼面資料成功: %d 筆", processed_count)
    return processed_count


def upsert_important_news(news_data_list: List[Dict[str, Any]]) -> int:
    """批量 UPSERT 重要新聞資料

    使用 PostgreSQL 的 ON CONFLICT DO UPDATE 語法進行高效能的批量 UPSERT 操作。
    對於非 PostgreSQL 資料庫，會回退到傳統的查詢-更新模式。

    Args:
        news_data_list: 重要新聞資料列表

    Returns:
        int: 成功處理的記錄數

    Raises:
        DatabaseError: 資料庫操作失敗
    """
    if not news_data_list:
        return 0

    try:
        from src.database.models.integration_models import ImportantNews

        with get_database_session() as session:
            # 檢查資料庫類型
            db_dialect = session.bind.dialect.name

            if db_dialect == 'postgresql':
                # 使用 PostgreSQL 的高效能 UPSERT
                return _upsert_important_news_postgresql(session, news_data_list)
            else:
                # 使用通用的 UPSERT 邏輯
                return _upsert_important_news_generic(session, news_data_list)

    except Exception as e:
        logger.error("UPSERT 重要新聞資料失敗: %s", e)
        raise DatabaseError(f"UPSERT 重要新聞資料失敗: {e}")


def _upsert_important_news_postgresql(session: Session, news_data_list: List[Dict[str, Any]]) -> int:
    """PostgreSQL 專用的高效能 UPSERT 實現

    Args:
        session: 資料庫會話
        news_data_list: 重要新聞資料列表

    Returns:
        int: 成功處理的記錄數
    """
    from src.database.models.integration_models import ImportantNews
    from sqlalchemy.dialects.postgresql import insert

    try:
        # 準備資料，確保所有必要欄位都存在
        prepared_data = []
        for news_data in news_data_list:
            # 設定必要欄位
            prepared_item = {
                'title': news_data.get('title'),
                'announce_date': news_data.get('announce_date'),
                'category': news_data.get('category', 'general'),
                'source': news_data.get('source'),
                'importance_level': news_data.get('importance_level', 3),
                'is_processed': news_data.get('is_processed', False),
                'created_at': news_data.get('created_at', datetime.now())
            }

            # 添加其他欄位
            optional_fields = [
                'symbol', 'content', 'subcategory', 'source_url', 'event_type',
                'publish_date', 'publish_time', 'location', 'stock_symbols', 'summary'
            ]

            for field in optional_fields:
                if field in news_data:
                    prepared_item[field] = news_data[field]

            prepared_data.append(prepared_item)

        # 執行 PostgreSQL UPSERT
        stmt = insert(ImportantNews).values(prepared_data)

        # 定義衝突時的更新欄位（排除主鍵和創建時間）
        update_fields = {
            'content': stmt.excluded.content,
            'subcategory': stmt.excluded.subcategory,
            'source_url': stmt.excluded.source_url,
            'importance_level': stmt.excluded.importance_level,
            'is_processed': stmt.excluded.is_processed,
            'event_type': stmt.excluded.event_type,
            'publish_date': stmt.excluded.publish_date,
            'publish_time': stmt.excluded.publish_time,
            'location': stmt.excluded.location,
            'stock_symbols': stmt.excluded.stock_symbols,
            'summary': stmt.excluded.summary
        }

        # ON CONFLICT DO UPDATE（基於標題、日期和來源的組合）
        stmt = stmt.on_conflict_do_update(
            index_elements=['title', 'announce_date', 'source'],
            set_=update_fields
        )

        result = session.execute(stmt)
        session.commit()

        processed_count = len(prepared_data)
        logger.info("PostgreSQL UPSERT 重要新聞資料成功: %d 筆", processed_count)
        return processed_count

    except Exception as e:
        logger.error("PostgreSQL UPSERT 重要新聞資料失敗: %s", e)
        raise


def _upsert_important_news_generic(session: Session, news_data_list: List[Dict[str, Any]]) -> int:
    """通用的 UPSERT 實現（適用於非 PostgreSQL 資料庫）

    Args:
        session: 資料庫會話
        news_data_list: 重要新聞資料列表

    Returns:
        int: 成功處理的記錄數
    """
    from src.database.models.integration_models import ImportantNews

    processed_count = 0

    for news_data in news_data_list:
        try:
            # 檢查是否已存在（基於標題、日期和來源）
            existing = session.query(ImportantNews).filter(
                ImportantNews.title == news_data.get('title'),
                ImportantNews.announce_date == news_data.get('announce_date'),
                ImportantNews.source == news_data.get('source')
            ).first()

            if existing:
                # 更新現有記錄
                for key, value in news_data.items():
                    if hasattr(existing, key) and key not in ['id', 'created_at']:
                        setattr(existing, key, value)
            else:
                # 創建新記錄，設定預設值
                news_data.setdefault('category', 'general')
                news_data.setdefault('importance_level', 3)
                news_data.setdefault('is_processed', False)
                news_data.setdefault('created_at', datetime.now())
                new_record = ImportantNews(**news_data)
                session.add(new_record)

            processed_count += 1

        except Exception as e:
            logger.warning("處理重要新聞記錄失敗: %s", e)
            continue

    session.commit()
    logger.info("通用 UPSERT 重要新聞資料成功: %d 筆", processed_count)
    return processed_count
