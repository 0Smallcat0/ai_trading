"""
AI 模型管理服務核心模組

此模組提供AI模型管理的核心功能，包括：
- 模型CRUD操作
- 模型訓練與推論
- 模型版本控制
- 模型效能監控
- 模型解釋性分析
- 模型匯入匯出
"""

import os
import json
import logging
import sqlite3
import threading
import time
import uuid
import hashlib
import pickle
import joblib
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import shutil
import tempfile

import pandas as pd
import numpy as np

# 嘗試導入機器學習相關庫
try:
    from sklearn.metrics import (
        accuracy_score,
        precision_score,
        recall_score,
        f1_score,
        mean_squared_error,
        r2_score,
    )
    from sklearn.model_selection import train_test_split

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# 嘗試導入解釋性分析庫
try:
    import shap

    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

try:
    import lime
    import lime.lime_tabular

    LIME_AVAILABLE = True
except ImportError:
    LIME_AVAILABLE = False

# 導入專案配置
try:
    from src.config import DATA_DIR, LOGS_DIR, MODELS_DIR
except ImportError:
    # 如果配置不存在，使用預設值
    DATA_DIR = "data"
    LOGS_DIR = "logs"
    MODELS_DIR = "models"

# 設置日誌
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

                # 創建模型訓練日誌表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS model_training_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        model_id TEXT NOT NULL,
                        training_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        start_time TIMESTAMP,
                        end_time TIMESTAMP,
                        epoch INTEGER,
                        loss REAL,
                        accuracy REAL,
                        val_loss REAL,
                        val_accuracy REAL,
                        log_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
                        inference_id TEXT NOT NULL,
                        input_data TEXT,
                        output_data TEXT,
                        inference_time REAL,
                        status TEXT NOT NULL,
                        error_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (model_id) REFERENCES ai_models (id)
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
                        model_path TEXT,
                        config_path TEXT,
                        performance_metrics TEXT,
                        parameters TEXT,
                        change_log TEXT,
                        created_by TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
            logger.error(f"初始化AI模型資料庫時發生錯誤: {e}")
            raise

    def get_model_types(self) -> Dict[str, List[str]]:
        """獲取模型類型定義"""
        return {
            "機器學習模型": [
                "隨機森林 (Random Forest)",
                "XGBoost",
                "LightGBM",
                "SVM (Support Vector Machine)",
                "邏輯回歸 (Logistic Regression)",
                "線性回歸 (Linear Regression)",
                "決策樹 (Decision Tree)",
                "K近鄰 (KNN)",
                "樸素貝葉斯 (Naive Bayes)",
            ],
            "深度學習模型": [
                "LSTM (Long Short-Term Memory)",
                "GRU (Gated Recurrent Unit)",
                "Transformer",
                "CNN (Convolutional Neural Network)",
                "RNN (Recurrent Neural Network)",
                "AutoEncoder",
                "GAN (Generative Adversarial Network)",
            ],
            "規則型模型": [
                "移動平均線交叉策略",
                "RSI策略",
                "MACD策略",
                "布林通道策略",
                "KD指標策略",
                "技術分析組合策略",
            ],
            "集成模型": [
                "投票集成 (Voting Ensemble)",
                "堆疊集成 (Stacking Ensemble)",
                "加權集成 (Weighted Ensemble)",
                "Bagging集成",
                "Boosting集成",
            ],
        }

    def create_model(
        self,
        name: str,
        model_type: str,
        sub_type: str = None,
        description: str = "",
        author: str = "系統",
        parameters: Dict = None,
        features: List[str] = None,
        target: str = None,
    ) -> str:
        """創建新模型"""
        try:
            model_id = str(uuid.uuid4())
            version = "1.0.0"

            # 準備數據
            parameters_json = json.dumps(parameters) if parameters else "{}"
            features_json = json.dumps(features) if features else "[]"

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 檢查模型名稱是否已存在
                cursor.execute("SELECT id FROM ai_models WHERE name = ?", (name,))
                if cursor.fetchone():
                    raise ValueError(f"模型名稱 '{name}' 已存在")

                # 插入模型
                cursor.execute(
                    """
                    INSERT INTO ai_models
                    (id, name, type, sub_type, description, author, version, status,
                     parameters, features, target)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        model_id,
                        name,
                        model_type,
                        sub_type,
                        description,
                        author,
                        version,
                        "created",
                        parameters_json,
                        features_json,
                        target,
                    ),
                )

                # 創建初始版本記錄
                cursor.execute(
                    """
                    INSERT INTO model_versions
                    (model_id, version, parameters, change_log, created_by)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (model_id, version, parameters_json, "初始版本", author),
                )

                conn.commit()

                logger.info(f"模型創建成功: {name} (ID: {model_id})")
                return model_id

        except Exception as e:
            logger.error(f"創建模型時發生錯誤: {e}")
            raise

    def get_model(self, model_id: str) -> Dict:
        """獲取模型詳細信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM ai_models WHERE id = ?", (model_id,))
                row = cursor.fetchone()

                if not row:
                    raise ValueError(f"模型不存在: {model_id}")

                # 解析模型數據
                model = {
                    "id": row[0],
                    "name": row[1],
                    "type": row[2],
                    "sub_type": row[3],
                    "description": row[4],
                    "author": row[5],
                    "version": row[6],
                    "status": row[7],
                    "is_active": bool(row[8]),
                    "model_path": row[9],
                    "config_path": row[10],
                    "performance_metrics": json.loads(row[11]) if row[11] else {},
                    "parameters": json.loads(row[12]) if row[12] else {},
                    "features": json.loads(row[13]) if row[13] else [],
                    "target": row[14],
                    "file_size": row[15],
                    "training_time": row[16],
                    "created_at": row[17],
                    "updated_at": row[18],
                    "last_inference": row[19],
                }

                return model

        except Exception as e:
            logger.error(f"獲取模型時發生錯誤: {e}")
            raise

    def list_models(
        self,
        model_type: str = None,
        status: str = None,
        author: str = None,
        search_query: str = None,
        limit: int = 100,
    ) -> List[Dict]:
        """列出模型"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 構建查詢條件
                conditions = []
                params = []

                if model_type:
                    conditions.append("type = ?")
                    params.append(model_type)

                if status:
                    conditions.append("status = ?")
                    params.append(status)

                if author:
                    conditions.append("author = ?")
                    params.append(author)

                if search_query:
                    conditions.append("(name LIKE ? OR description LIKE ?)")
                    params.extend([f"%{search_query}%", f"%{search_query}%"])

                # 構建完整查詢
                query = "SELECT * FROM ai_models"
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                query += " ORDER BY updated_at DESC"
                query += f" LIMIT {limit}"

                # 執行查詢
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()

                # 解析結果
                models = []
                for row in rows:
                    model = {
                        "id": row[0],
                        "name": row[1],
                        "type": row[2],
                        "sub_type": row[3],
                        "description": row[4],
                        "author": row[5],
                        "version": row[6],
                        "status": row[7],
                        "is_active": bool(row[8]),
                        "model_path": row[9],
                        "config_path": row[10],
                        "performance_metrics": json.loads(row[11]) if row[11] else {},
                        "parameters": json.loads(row[12]) if row[12] else {},
                        "features": json.loads(row[13]) if row[13] else [],
                        "target": row[14],
                        "file_size": row[15],
                        "training_time": row[16],
                        "created_at": row[17],
                        "updated_at": row[18],
                        "last_inference": row[19],
                    }
                    models.append(model)

                return models

        except Exception as e:
            logger.error(f"列出模型時發生錯誤: {e}")
            return []

    def update_model_status(self, model_id: str, status: str) -> bool:
        """更新模型狀態"""
        try:
            valid_statuses = [
                "created",
                "training",
                "trained",
                "deployed",
                "testing",
                "failed",
                "archived",
            ]
            if status not in valid_statuses:
                raise ValueError(f"無效的狀態: {status}")

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE ai_models SET status = ?, updated_at = ? WHERE id = ?",
                    (status, datetime.now(), model_id),
                )

                if cursor.rowcount == 0:
                    raise ValueError(f"模型不存在: {model_id}")

                conn.commit()

                logger.info(f"模型狀態更新成功: {model_id} -> {status}")
                return True

        except Exception as e:
            logger.error(f"更新模型狀態時發生錯誤: {e}")
            return False

    def set_active_model(self, model_id: str) -> bool:
        """設置活躍模型"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 檢查模型是否存在且已部署
                cursor.execute("SELECT status FROM ai_models WHERE id = ?", (model_id,))
                result = cursor.fetchone()

                if not result:
                    raise ValueError(f"模型不存在: {model_id}")

                if result[0] != "deployed":
                    raise ValueError(f"模型未部署，無法設為活躍: {model_id}")

                # 取消其他模型的活躍狀態
                cursor.execute("UPDATE ai_models SET is_active = FALSE")

                # 設置當前模型為活躍
                cursor.execute(
                    "UPDATE ai_models SET is_active = TRUE, updated_at = ? WHERE id = ?",
                    (datetime.now(), model_id),
                )

                conn.commit()

                logger.info(f"活躍模型設置成功: {model_id}")
                return True

        except Exception as e:
            logger.error(f"設置活躍模型時發生錯誤: {e}")
            return False

    def start_training(
        self, model_id: str, training_data: Dict, training_params: Dict = None
    ) -> str:
        """啟動模型訓練"""
        try:
            training_id = str(uuid.uuid4())

            # 更新模型狀態為訓練中
            self.update_model_status(model_id, "training")

            # 記錄訓練開始日誌
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO model_training_logs
                    (model_id, training_id, status, start_time, log_message)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        model_id,
                        training_id,
                        "started",
                        datetime.now(),
                        f"開始訓練，參數: {json.dumps(training_params) if training_params else '{}'}",
                    ),
                )
                conn.commit()

            # 這裡可以啟動實際的訓練過程（異步）
            # 目前返回訓練ID用於追蹤

            logger.info(f"模型訓練啟動成功: {model_id}, 訓練ID: {training_id}")
            return training_id

        except Exception as e:
            logger.error(f"啟動模型訓練時發生錯誤: {e}")
            raise

    def get_training_logs(self, model_id: str, training_id: str = None) -> List[Dict]:
        """獲取訓練日誌"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if training_id:
                    cursor.execute(
                        """
                        SELECT * FROM model_training_logs
                        WHERE model_id = ? AND training_id = ?
                        ORDER BY created_at DESC
                    """,
                        (model_id, training_id),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT * FROM model_training_logs
                        WHERE model_id = ?
                        ORDER BY created_at DESC
                    """,
                        (model_id,),
                    )

                rows = cursor.fetchall()

                logs = []
                for row in rows:
                    log = {
                        "id": row[0],
                        "model_id": row[1],
                        "training_id": row[2],
                        "status": row[3],
                        "start_time": row[4],
                        "end_time": row[5],
                        "epoch": row[6],
                        "loss": row[7],
                        "accuracy": row[8],
                        "val_loss": row[9],
                        "val_accuracy": row[10],
                        "log_message": row[11],
                        "created_at": row[12],
                    }
                    logs.append(log)

                return logs

        except Exception as e:
            logger.error(f"獲取訓練日誌時發生錯誤: {e}")
            return []

    def run_inference(
        self, model_id: str, input_data: Dict, return_explanation: bool = False
    ) -> Dict:
        """執行模型推論"""
        try:
            inference_id = str(uuid.uuid4())
            start_time = time.time()

            # 檢查模型是否存在且已部署
            model = self.get_model(model_id)
            if model["status"] != "deployed":
                raise ValueError(f"模型未部署，無法執行推論: {model_id}")

            # 模擬推論過程（實際實作時會載入真實模型）
            # 這裡返回模擬結果
            if model["type"] == "機器學習模型":
                if "accuracy" in model.get("performance_metrics", {}):
                    # 分類模型
                    prediction = np.random.choice([0, 1], p=[0.4, 0.6])
                    confidence = np.random.uniform(0.6, 0.95)
                    output_data = {
                        "prediction": int(prediction),
                        "confidence": float(confidence),
                        "probabilities": [1 - confidence, confidence],
                    }
                else:
                    # 回歸模型
                    prediction = np.random.normal(0.05, 0.02)
                    output_data = {
                        "prediction": float(prediction),
                        "confidence": np.random.uniform(0.7, 0.9),
                    }
            else:
                # 其他類型模型
                output_data = {
                    "prediction": np.random.normal(0.02, 0.01),
                    "signal": np.random.choice(["buy", "sell", "hold"]),
                }

            inference_time = time.time() - start_time

            # 記錄推論日誌
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO model_inference_logs
                    (model_id, inference_id, input_data, output_data,
                     inference_time, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        model_id,
                        inference_id,
                        json.dumps(input_data),
                        json.dumps(output_data),
                        inference_time,
                        "success",
                    ),
                )

                # 更新模型最後推論時間
                cursor.execute(
                    "UPDATE ai_models SET last_inference = ? WHERE id = ?",
                    (datetime.now(), model_id),
                )

                conn.commit()

            result = {
                "inference_id": inference_id,
                "model_id": model_id,
                "output": output_data,
                "inference_time": inference_time,
                "status": "success",
            }

            # 如果需要解釋性分析
            if return_explanation and (SHAP_AVAILABLE or LIME_AVAILABLE):
                explanation = self._generate_explanation(
                    model_id, input_data, output_data
                )
                result["explanation"] = explanation

            logger.info(f"模型推論完成: {model_id}, 推論ID: {inference_id}")
            return result

        except Exception as e:
            # 記錄錯誤日誌
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO model_inference_logs
                    (model_id, inference_id, input_data, inference_time,
                     status, error_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        model_id,
                        inference_id,
                        json.dumps(input_data),
                        time.time() - start_time,
                        "failed",
                        str(e),
                    ),
                )
                conn.commit()

            logger.error(f"模型推論失敗: {e}")
            raise

    def _generate_explanation(
        self, model_id: str, input_data: Dict, output_data: Dict
    ) -> Dict:
        """生成模型解釋性分析"""
        try:
            explanation = {
                "method": "simulated",
                "feature_importance": {},
                "local_explanation": {},
                "global_explanation": {},
            }

            # 模擬特徵重要性
            model = self.get_model(model_id)
            features = model.get("features", [])

            if features:
                # 生成模擬的特徵重要性
                importance_scores = np.random.dirichlet(np.ones(len(features)))
                explanation["feature_importance"] = dict(
                    zip(features, importance_scores.tolist())
                )

                # 生成模擬的局部解釋
                explanation["local_explanation"] = {
                    "feature_contributions": dict(
                        zip(features, np.random.randn(len(features)).tolist())
                    ),
                    "base_value": np.random.uniform(-0.1, 0.1),
                    "prediction_value": output_data.get("prediction", 0),
                }

            # 保存解釋性分析結果
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO model_explanations
                    (model_id, explanation_type, explanation_data,
                     feature_importance, sample_data)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        model_id,
                        "inference",
                        json.dumps(explanation),
                        json.dumps(explanation["feature_importance"]),
                        json.dumps(input_data),
                    ),
                )
                conn.commit()

            return explanation

        except Exception as e:
            logger.error(f"生成解釋性分析時發生錯誤: {e}")
            return {"error": str(e)}

    def get_model_explanation(
        self, model_id: str, explanation_type: str = "global"
    ) -> Dict:
        """獲取模型解釋性分析"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM model_explanations
                    WHERE model_id = ? AND explanation_type = ?
                    ORDER BY created_at DESC LIMIT 1
                """,
                    (model_id, explanation_type),
                )

                row = cursor.fetchone()

                if not row:
                    # 如果沒有現有的解釋，生成一個新的
                    return self._generate_global_explanation(model_id)

                explanation = {
                    "id": row[0],
                    "model_id": row[1],
                    "explanation_type": row[2],
                    "explanation_data": json.loads(row[3]) if row[3] else {},
                    "feature_importance": json.loads(row[4]) if row[4] else {},
                    "sample_data": json.loads(row[5]) if row[5] else {},
                    "created_at": row[6],
                }

                return explanation

        except Exception as e:
            logger.error(f"獲取模型解釋性分析時發生錯誤: {e}")
            return {}

    def _generate_global_explanation(self, model_id: str) -> Dict:
        """生成全局解釋性分析"""
        try:
            model = self.get_model(model_id)
            features = model.get("features", [])

            if not features:
                return {"error": "模型沒有特徵信息"}

            # 生成模擬的全局解釋
            explanation = {
                "model_id": model_id,
                "explanation_type": "global",
                "feature_importance": {},
                "feature_interactions": {},
                "model_behavior": {},
            }

            # 特徵重要性
            importance_scores = np.random.dirichlet(np.ones(len(features)))
            explanation["feature_importance"] = dict(
                zip(features, importance_scores.tolist())
            )

            # 特徵交互作用（模擬）
            if len(features) >= 2:
                interaction_pairs = [
                    (features[i], features[j])
                    for i in range(len(features))
                    for j in range(i + 1, min(i + 3, len(features)))
                ]
                interaction_scores = np.random.uniform(0, 0.1, len(interaction_pairs))
                explanation["feature_interactions"] = {
                    f"{pair[0]}_x_{pair[1]}": score
                    for pair, score in zip(interaction_pairs, interaction_scores)
                }

            # 模型行為分析
            explanation["model_behavior"] = {
                "prediction_range": [
                    float(np.random.uniform(-0.1, 0)),
                    float(np.random.uniform(0, 0.1)),
                ],
                "confidence_distribution": {
                    "mean": float(np.random.uniform(0.7, 0.9)),
                    "std": float(np.random.uniform(0.05, 0.15)),
                },
                "feature_sensitivity": dict(
                    zip(features, np.random.uniform(0.1, 1.0, len(features)).tolist())
                ),
            }

            # 保存解釋性分析結果
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO model_explanations
                    (model_id, explanation_type, explanation_data, feature_importance)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        model_id,
                        "global",
                        json.dumps(explanation),
                        json.dumps(explanation["feature_importance"]),
                    ),
                )
                conn.commit()

            return explanation

        except Exception as e:
            logger.error(f"生成全局解釋性分析時發生錯誤: {e}")
            return {"error": str(e)}

    def upload_model(
        self,
        model_file: bytes,
        model_name: str,
        model_type: str,
        sub_type: str = None,
        description: str = "",
        author: str = "使用者",
        parameters: Dict = None,
        features: List[str] = None,
        target: str = None,
    ) -> str:
        """上傳模型檔案"""
        try:
            # 創建模型記錄
            model_id = self.create_model(
                name=model_name,
                model_type=model_type,
                sub_type=sub_type,
                description=description,
                author=author,
                parameters=parameters,
                features=features,
                target=target,
            )

            # 創建模型目錄
            model_dir = self.models_dir / model_id
            model_dir.mkdir(parents=True, exist_ok=True)

            # 保存模型檔案
            model_path = model_dir / f"{model_name}.model"
            with open(model_path, "wb") as f:
                f.write(model_file)

            # 計算檔案大小
            file_size = len(model_file)

            # 更新模型路徑和檔案大小
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE ai_models
                    SET model_path = ?, file_size = ?, status = ?, updated_at = ?
                    WHERE id = ?
                """,
                    (str(model_path), file_size, "uploaded", datetime.now(), model_id),
                )
                conn.commit()

            logger.info(f"模型上傳成功: {model_name} (ID: {model_id})")
            return model_id

        except Exception as e:
            logger.error(f"上傳模型時發生錯誤: {e}")
            raise

    def download_model(self, model_id: str) -> Tuple[bytes, str]:
        """下載模型檔案"""
        try:
            model = self.get_model(model_id)
            model_path = model.get("model_path")

            if not model_path or not os.path.exists(model_path):
                raise ValueError(f"模型檔案不存在: {model_id}")

            # 讀取模型檔案
            with open(model_path, "rb") as f:
                model_data = f.read()

            # 生成檔案名
            filename = f"{model['name']}_v{model['version']}.model"

            logger.info(f"模型下載成功: {model['name']}")
            return model_data, filename

        except Exception as e:
            logger.error(f"下載模型時發生錯誤: {e}")
            raise

    def export_model(self, model_id: str, export_format: str = "json") -> str:
        """匯出模型配置"""
        try:
            model = self.get_model(model_id)

            if export_format == "json":
                # 匯出為JSON格式
                export_data = {
                    "model_info": {
                        "name": model["name"],
                        "type": model["type"],
                        "sub_type": model["sub_type"],
                        "description": model["description"],
                        "author": model["author"],
                        "version": model["version"],
                        "features": model["features"],
                        "target": model["target"],
                    },
                    "parameters": model["parameters"],
                    "performance_metrics": model["performance_metrics"],
                    "export_time": datetime.now().isoformat(),
                    "export_format": "json",
                }

                return json.dumps(export_data, indent=2, ensure_ascii=False)

            elif export_format == "yaml":
                # 匯出為YAML格式（需要安裝pyyaml）
                try:
                    import yaml

                    export_data = {
                        "model_info": {
                            "name": model["name"],
                            "type": model["type"],
                            "sub_type": model["sub_type"],
                            "description": model["description"],
                            "author": model["author"],
                            "version": model["version"],
                            "features": model["features"],
                            "target": model["target"],
                        },
                        "parameters": model["parameters"],
                        "performance_metrics": model["performance_metrics"],
                        "export_time": datetime.now().isoformat(),
                        "export_format": "yaml",
                    }

                    return yaml.dump(
                        export_data, default_flow_style=False, allow_unicode=True
                    )

                except ImportError:
                    raise ValueError("YAML格式需要安裝pyyaml庫")

            else:
                raise ValueError(f"不支援的匯出格式: {export_format}")

        except Exception as e:
            logger.error(f"匯出模型時發生錯誤: {e}")
            raise

    def import_model(
        self, import_data: str, import_format: str = "json", author: str = "使用者"
    ) -> str:
        """匯入模型配置"""
        try:
            if import_format == "json":
                data = json.loads(import_data)
            elif import_format == "yaml":
                try:
                    import yaml

                    data = yaml.safe_load(import_data)
                except ImportError:
                    raise ValueError("YAML格式需要安裝pyyaml庫")
            else:
                raise ValueError(f"不支援的匯入格式: {import_format}")

            # 解析模型資訊
            model_info = data.get("model_info", {})
            parameters = data.get("parameters", {})

            # 創建模型
            model_id = self.create_model(
                name=model_info.get("name", "匯入模型"),
                model_type=model_info.get("type", "機器學習模型"),
                sub_type=model_info.get("sub_type"),
                description=model_info.get("description", "從配置檔案匯入的模型"),
                author=author,
                parameters=parameters,
                features=model_info.get("features", []),
                target=model_info.get("target"),
            )

            # 如果有效能指標，更新模型
            performance_metrics = data.get("performance_metrics", {})
            if performance_metrics:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        UPDATE ai_models
                        SET performance_metrics = ?, updated_at = ?
                        WHERE id = ?
                    """,
                        (json.dumps(performance_metrics), datetime.now(), model_id),
                    )
                    conn.commit()

            logger.info(
                f"模型匯入成功: {model_info.get('name', '匯入模型')} (ID: {model_id})"
            )
            return model_id

        except Exception as e:
            logger.error(f"匯入模型時發生錯誤: {e}")
            raise

    def delete_model(self, model_id: str) -> bool:
        """刪除模型"""
        try:
            model = self.get_model(model_id)

            # 刪除模型檔案
            if model.get("model_path") and os.path.exists(model["model_path"]):
                model_dir = Path(model["model_path"]).parent
                if model_dir.exists():
                    shutil.rmtree(model_dir)

            # 刪除資料庫記錄
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 刪除相關日誌
                cursor.execute(
                    "DELETE FROM model_training_logs WHERE model_id = ?", (model_id,)
                )
                cursor.execute(
                    "DELETE FROM model_inference_logs WHERE model_id = ?", (model_id,)
                )
                cursor.execute(
                    "DELETE FROM model_versions WHERE model_id = ?", (model_id,)
                )
                cursor.execute(
                    "DELETE FROM model_explanations WHERE model_id = ?", (model_id,)
                )

                # 刪除模型記錄
                cursor.execute("DELETE FROM ai_models WHERE id = ?", (model_id,))

                conn.commit()

            logger.info(f"模型刪除成功: {model['name']} (ID: {model_id})")
            return True

        except Exception as e:
            logger.error(f"刪除模型時發生錯誤: {e}")
            return False

    def get_model_statistics(self) -> Dict:
        """獲取模型統計信息"""
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

                # 按作者統計
                cursor.execute("SELECT author, COUNT(*) FROM ai_models GROUP BY author")
                by_author = dict(cursor.fetchall())

                # 活躍模型數
                cursor.execute("SELECT COUNT(*) FROM ai_models WHERE is_active = 1")
                active_models = cursor.fetchone()[0]

                # 最近訓練的模型
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM ai_models
                    WHERE updated_at >= datetime('now', '-7 days')
                """
                )
                recent_trained = cursor.fetchone()[0]

                return {
                    "total_models": total_models,
                    "by_type": by_type,
                    "by_status": by_status,
                    "by_author": by_author,
                    "active_models": active_models,
                    "recent_trained": recent_trained,
                }

        except Exception as e:
            logger.error(f"獲取模型統計信息時發生錯誤: {e}")
            return {}

    def search_models(self, query: str, filters: Dict = None) -> List[Dict]:
        """搜尋模型"""
        try:
            filters = filters or {}

            # 構建搜尋條件
            conditions = ["(name LIKE ? OR description LIKE ?)"]
            params = [f"%{query}%", f"%{query}%"]

            # 添加篩選條件
            if filters.get("type"):
                conditions.append("type = ?")
                params.append(filters["type"])

            if filters.get("status"):
                conditions.append("status = ?")
                params.append(filters["status"])

            if filters.get("author"):
                conditions.append("author = ?")
                params.append(filters["author"])

            # 執行搜尋
            return self.list_models(
                model_type=filters.get("type"),
                status=filters.get("status"),
                author=filters.get("author"),
                search_query=query,
            )

        except Exception as e:
            logger.error(f"搜尋模型時發生錯誤: {e}")
            return []
