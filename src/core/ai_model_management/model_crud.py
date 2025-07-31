"""AI 模型 CRUD 操作模組

此模組提供 AI 模型的基本 CRUD (Create, Read, Update, Delete) 操作功能。
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class ModelManagementError(Exception):
    """模型管理異常類別"""


class ModelCRUD:
    """AI 模型 CRUD 操作類別"""

    def __init__(self, db_path: Path, models_dir: Path):
        """初始化模型 CRUD 操作

        Args:
            db_path: 資料庫路徑
            models_dir: 模型檔案目錄
        """
        self.db_path = db_path
        self.models_dir = models_dir

    def create_model(self, model_data: Dict) -> str:
        """創建新模型

        Args:
            model_data: 模型數據字典，包含 name, model_type, sub_type,
                       description, author, parameters, features, target

        Returns:
            str: 模型ID

        Raises:
            ModelManagementError: 創建失敗時拋出
        """
        try:
            model_id = str(uuid.uuid4())
            version = "1.0.0"

            # 準備數據
            parameters_json = json.dumps(model_data.get("parameters", {}))
            features_json = json.dumps(model_data.get("features", []))

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 檢查模型名稱是否已存在
                cursor.execute(
                    "SELECT id FROM ai_models WHERE name = ?", (model_data.get("name"),)
                )
                if cursor.fetchone():
                    raise ModelManagementError(
                        "模型名稱 '%s' 已存在" % model_data.get("name")
                    )

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
                        model_data.get("name"),
                        model_data.get("model_type"),
                        model_data.get("sub_type"),
                        model_data.get("description", ""),
                        model_data.get("author", "系統"),
                        version,
                        "created",
                        parameters_json,
                        features_json,
                        model_data.get("target"),
                    ),
                )

                # 創建初始版本記錄
                cursor.execute(
                    """
                    INSERT INTO model_versions
                    (model_id, version, parameters, change_log, created_by)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        model_id,
                        version,
                        parameters_json,
                        "初始版本",
                        model_data.get("author", "系統"),
                    ),
                )

                conn.commit()

                logger.info(
                    "模型創建成功: %s (ID: %s)", model_data.get("name"), model_id
                )
                return model_id

        except Exception as e:
            logger.error("創建模型時發生錯誤: %s", e)
            raise ModelManagementError("創建模型失敗") from e

    def get_model(self, model_id: str) -> Dict:
        """獲取模型詳細信息

        Args:
            model_id: 模型ID

        Returns:
            Dict: 模型信息

        Raises:
            ModelManagementError: 獲取失敗時拋出
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("SELECT * FROM ai_models WHERE id = ?", (model_id,))
                model = cursor.fetchone()

                if not model:
                    raise ModelManagementError("模型不存在: %s" % model_id)

                # 轉換為字典並解析 JSON 字段
                model_dict = dict(model)
                model_dict["parameters"] = json.loads(model_dict["parameters"] or "{}")
                model_dict["features"] = json.loads(model_dict["features"] or "[]")
                model_dict["performance_metrics"] = json.loads(
                    model_dict["performance_metrics"] or "{}"
                )

                return model_dict

        except Exception as e:
            logger.error("獲取模型時發生錯誤: %s", e)
            raise ModelManagementError("獲取模型失敗") from e

    def list_models(self, filters: Dict = None) -> List[Dict]:
        """列出模型

        Args:
            filters: 過濾條件字典，包含 model_type, status, author, search_query, limit

        Returns:
            List[Dict]: 模型列表
        """
        try:
            if filters is None:
                filters = {}

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # 構建查詢條件
                conditions = []
                params = []

                if filters.get("model_type"):
                    conditions.append("type = ?")
                    params.append(filters["model_type"])

                if filters.get("status"):
                    conditions.append("status = ?")
                    params.append(filters["status"])

                if filters.get("author"):
                    conditions.append("author = ?")
                    params.append(filters["author"])

                if filters.get("search_query"):
                    conditions.append("(name LIKE ? OR description LIKE ?)")
                    search_term = "%" + filters["search_query"] + "%"
                    params.extend([search_term, search_term])

                # 構建查詢
                if conditions:
                    where_clause = " AND ".join(conditions)
                    query = f"""
                        SELECT * FROM ai_models
                        WHERE {where_clause}
                        ORDER BY updated_at DESC
                        LIMIT ?
                    """
                else:
                    query = """
                        SELECT * FROM ai_models
                        ORDER BY updated_at DESC
                        LIMIT ?
                    """
                params.append(filters.get("limit", 100))

                cursor.execute(query, params)
                models = cursor.fetchall()

                # 轉換為字典列表
                result = []
                for model in models:
                    model_dict = dict(model)
                    model_dict["parameters"] = json.loads(
                        model_dict["parameters"] or "{}"
                    )
                    model_dict["features"] = json.loads(model_dict["features"] or "[]")
                    model_dict["performance_metrics"] = json.loads(
                        model_dict["performance_metrics"] or "{}"
                    )
                    result.append(model_dict)

                return result

        except Exception as e:
            logger.error("列出模型時發生錯誤: %s", e)
            return []

    def delete_model(self, model_id: str) -> bool:
        """刪除模型

        Args:
            model_id: 模型ID

        Returns:
            bool: 是否成功刪除
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 刪除相關記錄
                cursor.execute(
                    "DELETE FROM model_versions WHERE model_id = ?", (model_id,)
                )
                cursor.execute(
                    "DELETE FROM model_training_logs WHERE model_id = ?", (model_id,)
                )
                cursor.execute(
                    "DELETE FROM model_inference_logs WHERE model_id = ?", (model_id,)
                )
                cursor.execute(
                    "DELETE FROM model_explanations WHERE model_id = ?", (model_id,)
                )

                # 刪除模型
                cursor.execute("DELETE FROM ai_models WHERE id = ?", (model_id,))

                if not cursor.rowcount:
                    raise ModelManagementError("模型不存在: %s" % model_id)

                conn.commit()

                # 刪除模型文件
                self._delete_model_files(model_id)

                logger.info("模型刪除成功: %s", model_id)
                return True

        except Exception as e:
            logger.error("刪除模型時發生錯誤: %s", e)
            return False

    def update_model_status(self, model_id: str, status: str) -> bool:
        """更新模型狀態

        Args:
            model_id: 模型ID
            status: 新狀態

        Returns:
            bool: 是否成功更新
        """
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
                raise ModelManagementError("無效的狀態: %s" % status)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE ai_models SET status = ?, updated_at = ? WHERE id = ?",
                    (status, datetime.now(), model_id),
                )

                if not cursor.rowcount:
                    raise ModelManagementError("模型不存在: %s" % model_id)

                conn.commit()

                logger.info("模型狀態更新成功: %s -> %s", model_id, status)
                return True

        except Exception as e:
            logger.error("更新模型狀態時發生錯誤: %s", e)
            return False

    def _delete_model_files(self, model_id: str):
        """刪除模型文件"""
        try:
            model_dir = self.models_dir / model_id
            if model_dir.exists():
                import shutil

                shutil.rmtree(model_dir)

        except Exception as e:
            logger.error("刪除模型文件時發生錯誤: %s", e)
