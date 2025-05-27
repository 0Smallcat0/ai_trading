"""AI 模型管理服務核心模組

此模組提供AI模型管理的核心功能，包括：
- 模型CRUD操作
- 模型訓練與推論
- 模型版本控制
- 模型效能監控
- 模型解釋性分析
- 模型匯入匯出
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

# 嘗試導入機器學習相關庫
try:
    import joblib  # pylint: disable=unused-import
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

# 導入子模組
from .ai_model_management import (
    ModelCRUD,
    ModelTraining,
    ModelInference,
    ModelManagementError,
)

logger = logging.getLogger(__name__)


class AIModelManagementService:
    """AI模型管理服務類別"""

    def __init__(self):
        """初始化AI模型管理服務"""
        self.data_dir = Path(DATA_DIR)
        self.logs_dir = Path(LOGS_DIR)
        self.models_dir = Path(MODELS_DIR)

        # 確保目錄存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # 初始化資料庫連接
        self.db_path = self.data_dir / "ai_models.db"
        self._init_database()

        # 模型狀態管理
        self.model_lock = threading.Lock()
        self.active_models = {}

        # 初始化子模組
        self.crud = ModelCRUD(self.db_path, self.models_dir)
        self.training = ModelTraining(self.db_path, self.models_dir)
        self.inference = ModelInference(self.db_path, self.models_dir)

        logger.info("AI模型管理服務初始化完成")

    def _init_database(self):
        """初始化AI模型資料庫"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 創建模型表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ai_models (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        type TEXT NOT NULL,
                        sub_type TEXT,
                        description TEXT,
                        author TEXT,
                        version TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'training',
                        is_active BOOLEAN DEFAULT FALSE,
                        model_path TEXT,
                        config_path TEXT,
                        performance_metrics TEXT,
                        parameters TEXT,
                        features TEXT,
                        target TEXT,
                        file_size INTEGER,
                        training_time INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_inference TIMESTAMP
                    )
                """)

                # 創建模型版本表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS model_versions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        model_id TEXT NOT NULL,
                        version TEXT NOT NULL,
                        parameters TEXT,
                        change_log TEXT,
                        created_by TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (model_id) REFERENCES ai_models (id)
                    )
                """)

                # 創建模型訓練日誌表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS model_training_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        model_id TEXT NOT NULL,
                        training_id TEXT,
                        status TEXT NOT NULL,
                        start_time TIMESTAMP,
                        end_time TIMESTAMP,
                        progress REAL,
                        metrics TEXT,
                        log_message TEXT,
                        FOREIGN KEY (model_id) REFERENCES ai_models (id)
                    )
                """)

                # 創建模型推論日誌表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS model_inference_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        model_id TEXT NOT NULL,
                        input_data TEXT,
                        output_data TEXT,
                        inference_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        execution_time REAL,
                        FOREIGN KEY (model_id) REFERENCES ai_models (id)
                    )
                """)

                # 創建模型解釋性分析表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS model_explanations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        model_id TEXT NOT NULL,
                        explanation_type TEXT NOT NULL,
                        explanation_data TEXT,
                        feature_importance TEXT,
                        sample_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (model_id) REFERENCES ai_models (id)
                    )
                """)

                conn.commit()
                logger.info("AI模型資料庫初始化成功")

        except Exception as e:
            logger.error("初始化AI模型資料庫時發生錯誤: %s", e)
            raise ModelManagementError("資料庫初始化失敗") from e

    # CRUD 操作方法
    def create_model(self, model_data: Dict) -> str:
        """創建新模型

        Args:
            model_data: 模型數據字典

        Returns:
            str: 模型ID
        """
        return self.crud.create_model(model_data)

    def get_model(self, model_id: str) -> Dict:
        """獲取模型詳細信息

        Args:
            model_id: 模型ID

        Returns:
            Dict: 模型信息
        """
        return self.crud.get_model(model_id)

    def list_models(self, filters: Dict = None) -> List[Dict]:
        """列出模型

        Args:
            filters: 過濾條件字典

        Returns:
            List[Dict]: 模型列表
        """
        return self.crud.list_models(filters)

    def delete_model(self, model_id: str) -> bool:
        """刪除模型

        Args:
            model_id: 模型ID

        Returns:
            bool: 是否成功刪除
        """
        return self.crud.delete_model(model_id)

    def update_model_status(self, model_id: str, status: str) -> bool:
        """更新模型狀態

        Args:
            model_id: 模型ID
            status: 新狀態

        Returns:
            bool: 是否成功更新
        """
        return self.crud.update_model_status(model_id, status)

    # 訓練相關方法
    def start_training(self, model_id: str, training_data: Dict) -> str:
        """啟動模型訓練

        Args:
            model_id: 模型ID
            training_data: 訓練數據字典

        Returns:
            str: 訓練ID
        """
        return self.training.start_training(model_id, training_data)

    def get_training_logs(self, model_id: str) -> List[Dict]:
        """獲取訓練日誌

        Args:
            model_id: 模型ID

        Returns:
            List[Dict]: 訓練日誌列表
        """
        return self.training.get_training_logs(model_id)

    # 推論相關方法
    def predict(self, model_id: str, input_data: Dict) -> Dict:
        """執行模型推論

        Args:
            model_id: 模型ID
            input_data: 輸入數據字典

        Returns:
            Dict: 推論結果
        """
        return self.inference.predict(model_id, input_data)

    def get_inference_logs(self, model_id: str, limit: int = 100) -> List[Dict]:
        """獲取推論日誌

        Args:
            model_id: 模型ID
            limit: 返回數量限制

        Returns:
            List[Dict]: 推論日誌列表
        """
        return self.inference.get_inference_logs(model_id, limit)

    # 統計相關方法
    def get_model_statistics(self) -> Dict:
        """獲取模型統計信息

        Returns:
            Dict: 模型統計信息
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 總模型數
                cursor.execute("SELECT COUNT(*) FROM ai_models")
                total_models = cursor.fetchone()[0]

                # 按類型統計
                cursor.execute(
                    "SELECT type, COUNT(*) FROM ai_models GROUP BY type"
                )
                by_type = dict(cursor.fetchall())

                # 按狀態統計
                cursor.execute(
                    "SELECT status, COUNT(*) FROM ai_models GROUP BY status"
                )
                by_status = dict(cursor.fetchall())

                # 活躍模型數
                cursor.execute("SELECT COUNT(*) FROM ai_models WHERE is_active = 1")
                active_models = cursor.fetchone()[0]

                return {
                    "total_models": total_models,
                    "by_type": by_type,
                    "by_status": by_status,
                    "active_models": active_models,
                }

        except Exception as e:
            logger.error("獲取模型統計信息時發生錯誤: %s", e)
            return {}
