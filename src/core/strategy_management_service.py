"""策略管理服務核心模組

此模組提供策略管理的核心功能，包括：
- 策略CRUD操作
- 策略版本控制
- 策略參數管理
- 策略匯入匯出
- 策略執行狀態管理
- 策略效能追蹤
"""

import logging
import sqlite3
import threading
from pathlib import Path
from typing import Dict, List

# 導入專案配置
try:
    from src.config import DATA_DIR, LOGS_DIR, MODELS_DIR
except ImportError:
    # 如果配置不存在，使用預設值
    DATA_DIR = "data"
    LOGS_DIR = "logs"
    MODELS_DIR = "models"

# 導入子模組
from .strategy_management import (
    StrategyCRUD,
    StrategyVersion,
    StrategyTemplate,
    StrategyManagementError,
)

logger = logging.getLogger(__name__)


class StrategyManagementService:
    """策略管理服務類別"""

    def __init__(self):
        """初始化策略管理服務"""
        self.data_dir = Path(DATA_DIR)
        self.logs_dir = Path(LOGS_DIR)
        self.models_dir = Path(MODELS_DIR)
        self.strategies_dir = self.data_dir / "strategies"

        # 確保目錄存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.strategies_dir.mkdir(parents=True, exist_ok=True)

        # 初始化資料庫連接
        self.db_path = self.data_dir / "strategies.db"
        self._init_database()

        # 策略狀態管理
        self.strategy_lock = threading.Lock()

        # 初始化子模組
        self.crud = StrategyCRUD(self.db_path, self.strategies_dir)
        self.version = StrategyVersion(self.db_path, self.strategies_dir)
        self.template = StrategyTemplate()

        logger.info("策略管理服務初始化完成")

    def _init_database(self):
        """初始化策略資料庫"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 創建策略表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS strategies (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        type TEXT NOT NULL,
                        category TEXT,
                        description TEXT,
                        author TEXT,
                        version TEXT,
                        status TEXT DEFAULT 'draft',
                        code TEXT,
                        parameters TEXT,
                        risk_parameters TEXT,
                        performance_metrics TEXT,
                        tags TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # 創建策略版本表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS strategy_versions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        strategy_id TEXT NOT NULL,
                        version TEXT NOT NULL,
                        code TEXT,
                        parameters TEXT,
                        risk_parameters TEXT,
                        change_log TEXT,
                        created_by TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (strategy_id) REFERENCES strategies (id)
                    )
                """
                )

                conn.commit()
                logger.info("策略資料庫初始化完成")

        except Exception as e:
            logger.error("初始化策略資料庫時發生錯誤: %s", e)
            raise StrategyManagementError("資料庫初始化失敗") from e

    # 策略類型和模板方法
    def get_strategy_types(self) -> Dict[str, List[str]]:
        """獲取策略類型定義

        Returns:
            Dict[str, List[str]]: 策略類型字典
        """
        return self.template.get_strategy_types()

    def get_strategy_templates(self) -> Dict[str, Dict]:
        """獲取策略模板

        Returns:
            Dict[str, Dict]: 策略模板字典
        """
        return self.template.get_strategy_templates()

    # CRUD 操作方法
    def create_strategy(self, strategy_data: Dict) -> str:
        """創建新策略

        Args:
            strategy_data: 策略數據字典，包含 name, strategy_type, category,
                          description, author, code, parameters, risk_parameters, tags

        Returns:
            str: 策略ID
        """
        return self.crud.create_strategy(
            name=strategy_data.get("name"),
            strategy_type=strategy_data.get("strategy_type"),
            category=strategy_data.get("category"),
            description=strategy_data.get("description", ""),
            author=strategy_data.get("author", "系統"),
            code=strategy_data.get("code", ""),
            parameters=strategy_data.get("parameters"),
            risk_parameters=strategy_data.get("risk_parameters"),
            tags=strategy_data.get("tags"),
        )

    def get_strategy(self, strategy_id: str) -> Dict:
        """獲取策略詳細信息

        Args:
            strategy_id: 策略ID

        Returns:
            Dict: 策略信息
        """
        return self.crud.get_strategy(strategy_id)

    def list_strategies(self, filters: Dict = None) -> List[Dict]:
        """列出策略

        Args:
            filters: 過濾條件字典，包含 strategy_type, status, author, search_query, limit

        Returns:
            List[Dict]: 策略列表
        """
        if filters is None:
            filters = {}

        return self.crud.list_strategies(
            strategy_type=filters.get("strategy_type"),
            status=filters.get("status"),
            author=filters.get("author"),
            search_query=filters.get("search_query"),
            limit=filters.get("limit", 100),
        )

    def delete_strategy(self, strategy_id: str) -> bool:
        """刪除策略

        Args:
            strategy_id: 策略ID

        Returns:
            bool: 是否成功刪除
        """
        return self.crud.delete_strategy(strategy_id)

    def update_strategy_status(self, strategy_id: str, status: str) -> bool:
        """更新策略狀態

        Args:
            strategy_id: 策略ID
            status: 新狀態

        Returns:
            bool: 是否成功更新
        """
        return self.crud.update_strategy_status(strategy_id, status)

    # 版本控制方法
    def create_version(self, strategy_id: str, version_data: Dict = None) -> str:
        """創建新版本

        Args:
            strategy_id: 策略ID
            version_data: 版本數據字典，包含 code, parameters, risk_parameters,
                         change_log, author

        Returns:
            str: 新版本號
        """
        if version_data is None:
            version_data = {}

        return self.version.create_version(
            strategy_id=strategy_id,
            code=version_data.get("code"),
            parameters=version_data.get("parameters"),
            risk_parameters=version_data.get("risk_parameters"),
            change_log=version_data.get("change_log", ""),
            author=version_data.get("author", "系統"),
        )

    def get_versions(self, strategy_id: str) -> List[Dict]:
        """獲取策略所有版本

        Args:
            strategy_id: 策略ID

        Returns:
            List[Dict]: 版本列表
        """
        return self.version.get_versions(strategy_id)

    def rollback_version(self, strategy_id: str, target_version: str) -> bool:
        """回滾到指定版本

        Args:
            strategy_id: 策略ID
            target_version: 目標版本號

        Returns:
            bool: 是否成功回滾
        """
        return self.version.rollback_version(strategy_id, target_version)

    # 模板相關方法
    def get_template(self, template_name: str) -> Dict:
        """獲取特定模板

        Args:
            template_name: 模板名稱

        Returns:
            Dict: 模板信息
        """
        return self.template.get_template(template_name)

    def validate_strategy_data(self, strategy_dict: Dict) -> bool:
        """驗證策略數據格式

        Args:
            strategy_dict: 策略數據字典

        Returns:
            bool: 是否有效
        """
        return self.template.validate_strategy_data(strategy_dict)

    def export_strategy_template(self, strategy_data: Dict) -> str:
        """匯出策略為模板格式

        Args:
            strategy_data: 策略數據

        Returns:
            str: JSON 格式的模板字符串
        """
        return self.template.export_strategy_template(strategy_data)
