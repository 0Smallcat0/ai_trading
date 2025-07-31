"""應用生命週期管理模組

此模組負責管理 FastAPI 應用的啟動和關閉流程，包括資料庫連接、
快取系統、監控系統等的初始化和清理。
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI

logger = logging.getLogger(__name__)


class LifespanManager:
    """應用生命週期管理器"""

    def __init__(self):
        """初始化生命週期管理器"""
        self.database_initialized = False
        self.cache_initialized = False
        self.monitoring_initialized = False
        self.scheduler_initialized = False

    async def startup(self) -> None:
        """應用啟動初始化

        執行所有必要的啟動任務，包括：
        - 資料庫連接初始化
        - 快取系統初始化
        - 監控系統初始化
        - 定時任務調度器初始化

        Raises:
            Exception: 當初始化失敗時拋出異常
        """
        logger.info("開始應用啟動初始化...")

        try:
            # 初始化資料庫連接
            await self._initialize_database()

            # 初始化快取系統
            await self._initialize_cache()

            # 初始化監控系統
            await self._initialize_monitoring()

            # 初始化定時任務調度器
            await self._initialize_scheduler()

            logger.info("應用啟動初始化完成")

        except Exception as e:
            logger.error("應用啟動初始化失敗: %s", e, exc_info=True)
            # 清理已初始化的資源
            await self.shutdown()
            raise

    async def shutdown(self) -> None:
        """應用關閉清理

        執行所有必要的清理任務，包括：
        - 關閉資料庫連接
        - 清理快取系統
        - 停止監控系統
        - 停止定時任務調度器
        """
        logger.info("開始應用關閉清理...")

        try:
            # 停止定時任務調度器
            if self.scheduler_initialized:
                await self._cleanup_scheduler()

            # 停止監控系統
            if self.monitoring_initialized:
                await self._cleanup_monitoring()

            # 清理快取系統
            if self.cache_initialized:
                await self._cleanup_cache()

            # 關閉資料庫連接
            if self.database_initialized:
                await self._cleanup_database()

            logger.info("應用關閉清理完成")

        except Exception as e:
            logger.error("應用關閉清理失敗: %s", e, exc_info=True)

    async def _initialize_database(self) -> None:
        """初始化資料庫連接

        建立資料庫連接池，執行必要的資料庫遷移

        Raises:
            Exception: 當資料庫初始化失敗時拋出異常
        """
        try:
            logger.info("初始化資料庫連接...")

            # 這裡應該初始化實際的資料庫連接
            # 例如：SQLAlchemy、Tortoise ORM 等
            # await database.connect()
            # await run_migrations()

            self.database_initialized = True
            logger.info("資料庫連接初始化成功")

        except Exception as e:
            logger.error("資料庫連接初始化失敗: %s", e)
            raise

    async def _initialize_cache(self) -> None:
        """初始化快取系統

        建立 Redis 連接，設定快取配置

        Raises:
            Exception: 當快取系統初始化失敗時拋出異常
        """
        try:
            logger.info("初始化快取系統...")

            # 這裡應該初始化實際的快取系統
            # 例如：Redis、Memcached 等
            # await redis_client.connect()
            # await redis_client.ping()

            self.cache_initialized = True
            logger.info("快取系統初始化成功")

        except Exception as e:
            logger.error("快取系統初始化失敗: %s", e)
            raise

    async def _initialize_monitoring(self) -> None:
        """初始化監控系統

        啟動指標收集、健康檢查等監控功能

        Raises:
            Exception: 當監控系統初始化失敗時拋出異常
        """
        try:
            logger.info("初始化監控系統...")

            # 這裡應該初始化實際的監控系統
            # 例如：Prometheus、Grafana 等
            # await metrics_collector.start()
            # await health_checker.start()

            self.monitoring_initialized = True
            logger.info("監控系統初始化成功")

        except Exception as e:
            logger.error("監控系統初始化失敗: %s", e)
            raise

    async def _initialize_scheduler(self) -> None:
        """初始化定時任務調度器

        啟動定時任務，如資料同步、清理任務等

        Raises:
            Exception: 當調度器初始化失敗時拋出異常
        """
        try:
            logger.info("初始化定時任務調度器...")

            # 這裡應該初始化實際的任務調度器
            # 例如：APScheduler、Celery 等
            # scheduler.start()
            # await schedule_periodic_tasks()

            self.scheduler_initialized = True
            logger.info("定時任務調度器初始化成功")

        except Exception as e:
            logger.error("定時任務調度器初始化失敗: %s", e)
            raise

    async def _cleanup_database(self) -> None:
        """清理資料庫連接"""
        try:
            logger.info("清理資料庫連接...")

            # 這裡應該清理實際的資料庫連接
            # await database.disconnect()

            self.database_initialized = False
            logger.info("資料庫連接清理完成")

        except Exception as e:
            logger.error("資料庫連接清理失敗: %s", e)

    async def _cleanup_cache(self) -> None:
        """清理快取系統"""
        try:
            logger.info("清理快取系統...")

            # 這裡應該清理實際的快取系統
            # await redis_client.close()

            self.cache_initialized = False
            logger.info("快取系統清理完成")

        except Exception as e:
            logger.error("快取系統清理失敗: %s", e)

    async def _cleanup_monitoring(self) -> None:
        """清理監控系統"""
        try:
            logger.info("清理監控系統...")

            # 這裡應該清理實際的監控系統
            # await metrics_collector.stop()
            # await health_checker.stop()

            self.monitoring_initialized = False
            logger.info("監控系統清理完成")

        except Exception as e:
            logger.error("監控系統清理失敗: %s", e)

    async def _cleanup_scheduler(self) -> None:
        """清理定時任務調度器"""
        try:
            logger.info("清理定時任務調度器...")

            # 這裡應該清理實際的任務調度器
            # scheduler.shutdown()

            self.scheduler_initialized = False
            logger.info("定時任務調度器清理完成")

        except Exception as e:
            logger.error("定時任務調度器清理失敗: %s", e)


# 全域生命週期管理器實例
lifespan_manager = LifespanManager()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """應用生命週期管理

    管理 FastAPI 應用的啟動和關閉流程，包括資料庫連接初始化、
    快取系統設定等。

    Args:
        app: FastAPI 應用實例

    Yields:
        None: 應用運行期間的控制權

    Note:
        此函數在應用啟動時執行初始化，在關閉時執行清理
    """
    # 啟動階段
    try:
        await lifespan_manager.startup()
        yield
    finally:
        # 關閉階段
        await lifespan_manager.shutdown()


async def health_check() -> dict:
    """健康檢查

    Returns:
        dict: 健康檢查結果

    Note:
        檢查各個系統組件的健康狀態
    """
    health_status = {
        "status": "healthy",
        "components": {
            "database": (
                "healthy" if lifespan_manager.database_initialized else "unhealthy"
            ),
            "cache": "healthy" if lifespan_manager.cache_initialized else "unhealthy",
            "monitoring": (
                "healthy" if lifespan_manager.monitoring_initialized else "unhealthy"
            ),
            "scheduler": (
                "healthy" if lifespan_manager.scheduler_initialized else "unhealthy"
            ),
        },
    }

    # 如果任何組件不健康，整體狀態為不健康
    if any(status == "unhealthy" for status in health_status["components"].values()):
        health_status["status"] = "unhealthy"

    return health_status
