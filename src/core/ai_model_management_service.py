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

        # 初始化示例數據
        self._init_sample_data()

        logger.info("AI模型管理服務初始化完成")

    def _init_database(self):
        """初始化AI模型資料庫"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 創建模型表
                cursor.execute(
                    """
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
                """
                )

                # 創建模型版本表
                cursor.execute(
                    """
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
                """
                )

                # 創建模型訓練日誌表
                cursor.execute(
                    """
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
                """
                )

                # 創建模型推論日誌表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS model_inference_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        model_id TEXT NOT NULL,
                        input_data TEXT,
                        output_data TEXT,
                        inference_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        execution_time REAL,
                        FOREIGN KEY (model_id) REFERENCES ai_models (id)
                    )
                """
                )

                # 創建模型解釋性分析表
                cursor.execute(
                    """
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
                """
                )

                conn.commit()
                logger.info("AI模型資料庫初始化成功")

        except Exception as e:
            logger.error("初始化AI模型資料庫時發生錯誤: %s", e)
            raise ModelManagementError("資料庫初始化失敗") from e

    def _init_sample_data(self):
        """初始化示例模型數據"""
        try:
            # 檢查是否已有模型數據
            existing_models = self.list_models()
            if existing_models:
                return  # 已有數據，不需要初始化

            # 創建示例模型
            sample_models = [
                {
                    "name": "股價預測LSTM模型",
                    "model_type": "時間序列模型",
                    "sub_type": "LSTM",
                    "description": "基於LSTM神經網路的股價預測模型，能夠分析歷史價格數據並預測未來趨勢",
                    "author": "AI交易系統",
                    "parameters": {"epochs": 100, "batch_size": 32, "learning_rate": 0.001},
                    "features": ["開盤價", "收盤價", "最高價", "最低價", "成交量"],
                    "target": "下一日收盤價"
                },
                {
                    "name": "情感分析模型",
                    "model_type": "自然語言處理",
                    "sub_type": "情感分析",
                    "description": "分析財經新聞和社交媒體情感，輔助投資決策",
                    "author": "AI交易系統",
                    "parameters": {"model_type": "BERT", "max_length": 512},
                    "features": ["新聞標題", "新聞內容", "發布時間"],
                    "target": "情感分數"
                },
                {
                    "name": "風險評估模型",
                    "model_type": "機器學習模型",
                    "sub_type": "隨機森林",
                    "description": "評估投資組合風險，提供風險等級建議",
                    "author": "AI交易系統",
                    "parameters": {"n_estimators": 100, "max_depth": 10},
                    "features": ["波動率", "夏普比率", "最大回撤", "相關性"],
                    "target": "風險等級"
                }
            ]

            for model_data in sample_models:
                try:
                    model_id = self.create_model(model_data)
                    # 設置一些模型為已訓練狀態
                    if "LSTM" in model_data["name"]:
                        self.update_model_status(model_id, "trained")
                    elif "情感分析" in model_data["name"]:
                        self.update_model_status(model_id, "deployed")
                    logger.info("創建示例模型: %s", model_data["name"])
                except Exception as e:
                    logger.warning("創建示例模型失敗: %s - %s", model_data["name"], e)

        except Exception as e:
            logger.warning("初始化示例數據失敗: %s", e)

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

    def get_models(self) -> List[Dict]:
        """獲取所有模型（向後相容方法）

        Returns:
            List[Dict]: 模型列表
        """
        return self.list_models()

    def get_model_types(self) -> Dict[str, List[str]]:
        """獲取支援的模型類型

        Returns:
            Dict[str, List[str]]: 模型類型字典，鍵為主類型，值為子類型列表
        """
        return {
            "機器學習模型": [
                "線性回歸",
                "邏輯回歸",
                "決策樹",
                "隨機森林",
                "支持向量機",
                "神經網路",
                "深度學習"
            ],
            "時間序列模型": [
                "ARIMA",
                "LSTM",
                "GRU",
                "Transformer",
                "Prophet"
            ],
            "強化學習模型": [
                "Q-Learning",
                "DQN",
                "PPO",
                "A3C",
                "DDPG"
            ],
            "自然語言處理": [
                "BERT",
                "GPT",
                "Word2Vec",
                "情感分析",
                "文本分類"
            ]
        }

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
                cursor.execute("SELECT type, COUNT(*) FROM ai_models GROUP BY type")
                by_type = dict(cursor.fetchall())

                # 按狀態統計
                cursor.execute("SELECT status, COUNT(*) FROM ai_models GROUP BY status")
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
