"""AI 模型訓練模組

此模組提供 AI 模型的訓練功能，包括訓練啟動、監控和日誌記錄。
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class ModelTrainingError(Exception):
    """模型訓練異常類別"""


class ModelTraining:
    """AI 模型訓練類別"""

    def __init__(self, db_path: Path, models_dir: Path):
        """初始化模型訓練

        Args:
            db_path: 資料庫路徑
            models_dir: 模型檔案目錄
        """
        self.db_path = db_path
        self.models_dir = models_dir

    def start_training(self, model_id: str, training_data: Dict) -> str:
        """啟動模型訓練

        Args:
            model_id: 模型ID
            training_data: 訓練數據字典，包含 training_params 等

        Returns:
            str: 訓練ID

        Raises:
            ModelTrainingError: 訓練啟動失敗時拋出
        """
        try:
            training_id = str(uuid.uuid4())
            training_params = training_data.get("training_params", {})

            # 更新模型狀態為訓練中
            self._update_model_status(model_id, "training")

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
                        "開始訓練，參數: %s" % json.dumps(training_params),
                    ),
                )
                conn.commit()

            # 這裡可以啟動實際的訓練過程（異步）
            # 目前返回訓練ID用於追蹤

            logger.info("模型訓練啟動成功: %s, 訓練ID: %s", model_id, training_id)
            return training_id

        except Exception as e:
            logger.error("啟動模型訓練時發生錯誤: %s", e)
            raise ModelTrainingError("啟動訓練失敗") from e

    def get_training_logs(self, model_id: str) -> List[Dict]:
        """獲取訓練日誌

        Args:
            model_id: 模型ID

        Returns:
            List[Dict]: 訓練日誌列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT * FROM model_training_logs
                    WHERE model_id = ?
                    ORDER BY start_time DESC
                    """,
                    (model_id,),
                )

                logs = cursor.fetchall()
                return [dict(log) for log in logs]

        except Exception as e:
            logger.error("獲取訓練日誌時發生錯誤: %s", e)
            return []

    def update_training_progress(self, training_id: str, progress_data: Dict) -> bool:
        """更新訓練進度

        Args:
            training_id: 訓練ID
            progress_data: 進度數據字典，包含 status, progress, metrics 等

        Returns:
            bool: 是否成功更新
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 更新訓練日誌
                update_fields = []
                update_values = []

                if "status" in progress_data:
                    update_fields.append("status = ?")
                    update_values.append(progress_data["status"])

                if "progress" in progress_data:
                    update_fields.append("progress = ?")
                    update_values.append(progress_data["progress"])

                if "metrics" in progress_data:
                    update_fields.append("metrics = ?")
                    update_values.append(json.dumps(progress_data["metrics"]))

                if "log_message" in progress_data:
                    update_fields.append("log_message = ?")
                    update_values.append(progress_data["log_message"])

                if progress_data.get("status") == "completed":
                    update_fields.append("end_time = ?")
                    update_values.append(datetime.now())

                if update_fields:
                    update_values.append(training_id)
                    set_clause = ", ".join(update_fields)
                    query = f"""
                        UPDATE model_training_logs
                        SET {set_clause}
                        WHERE training_id = ?
                    """

                    cursor.execute(query, update_values)
                    conn.commit()

                    logger.info("訓練進度更新成功: %s", training_id)
                    return True

                return False

        except Exception as e:
            logger.error("更新訓練進度時發生錯誤: %s", e)
            return False

    def complete_training(
        self, training_id: str, model_id: str, performance_metrics: Dict
    ) -> bool:
        """完成模型訓練

        Args:
            training_id: 訓練ID
            model_id: 模型ID
            performance_metrics: 效能指標

        Returns:
            bool: 是否成功完成
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 更新模型狀態和效能指標
                cursor.execute(
                    """
                    UPDATE ai_models
                    SET status = ?, performance_metrics = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        "trained",
                        json.dumps(performance_metrics),
                        datetime.now(),
                        model_id,
                    ),
                )

                # 更新訓練日誌
                cursor.execute(
                    """
                    UPDATE model_training_logs
                    SET status = ?, end_time = ?, metrics = ?
                    WHERE training_id = ?
                    """,
                    (
                        "completed",
                        datetime.now(),
                        json.dumps(performance_metrics),
                        training_id,
                    ),
                )

                conn.commit()

                logger.info("模型訓練完成: %s", model_id)
                return True

        except Exception as e:
            logger.error("完成模型訓練時發生錯誤: %s", e)
            return False

    def fail_training(
        self, training_id: str, model_id: str, error_message: str
    ) -> bool:
        """標記訓練失敗

        Args:
            training_id: 訓練ID
            model_id: 模型ID
            error_message: 錯誤訊息

        Returns:
            bool: 是否成功標記
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 更新模型狀態
                cursor.execute(
                    "UPDATE ai_models SET status = ?, updated_at = ? WHERE id = ?",
                    ("failed", datetime.now(), model_id),
                )

                # 更新訓練日誌
                cursor.execute(
                    """
                    UPDATE model_training_logs
                    SET status = ?, end_time = ?, log_message = ?
                    WHERE training_id = ?
                    """,
                    ("failed", datetime.now(), error_message, training_id),
                )

                conn.commit()

                logger.info("模型訓練失敗標記: %s", model_id)
                return True

        except Exception as e:
            logger.error("標記訓練失敗時發生錯誤: %s", e)
            return False

    def get_training_statistics(self) -> Dict:
        """獲取訓練統計信息

        Returns:
            Dict: 訓練統計信息
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 總訓練次數
                cursor.execute("SELECT COUNT(*) FROM model_training_logs")
                total_trainings = cursor.fetchone()[0]

                # 按狀態統計
                cursor.execute(
                    """
                    SELECT status, COUNT(*)
                    FROM model_training_logs
                    GROUP BY status
                    """
                )
                by_status = dict(cursor.fetchall())

                # 最近7天的訓練
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM model_training_logs
                    WHERE start_time >= datetime('now', '-7 days')
                    """
                )
                recent_trainings = cursor.fetchone()[0]

                return {
                    "total_trainings": total_trainings,
                    "by_status": by_status,
                    "recent_trainings": recent_trainings,
                }

        except Exception as e:
            logger.error("獲取訓練統計信息時發生錯誤: %s", e)
            return {}

    def _update_model_status(self, model_id: str, status: str):
        """更新模型狀態（內部方法）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE ai_models SET status = ?, updated_at = ? WHERE id = ?",
                    (status, datetime.now(), model_id),
                )
                conn.commit()

        except Exception as e:
            logger.error("更新模型狀態時發生錯誤: %s", e)
