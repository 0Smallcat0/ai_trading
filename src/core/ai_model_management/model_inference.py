"""AI 模型推論模組

此模組提供 AI 模型的推論功能，包括模型載入、預測和結果記錄。
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np

logger = logging.getLogger(__name__)


class ModelInferenceError(Exception):
    """模型推論異常類別"""


class ModelInference:
    """AI 模型推論類別"""

    def __init__(self, db_path: Path, models_dir: Path):
        """初始化模型推論

        Args:
            db_path: 資料庫路徑
            models_dir: 模型檔案目錄
        """
        self.db_path = db_path
        self.models_dir = models_dir
        self.active_models = {}

    def predict(self, model_id: str, input_data: Dict) -> Dict:
        """執行模型推論

        Args:
            model_id: 模型ID
            input_data: 輸入數據字典

        Returns:
            Dict: 推論結果

        Raises:
            ModelInferenceError: 推論失敗時拋出
        """
        try:
            # 獲取模型信息
            model = self._get_model_info(model_id)
            if not model:
                raise ModelInferenceError("模型不存在: %s" % model_id)

            if model["status"] != "trained" and model["status"] != "deployed":
                raise ModelInferenceError(
                    "模型狀態不正確，無法進行推論: %s" % model["status"]
                )

            # 記錄推論開始
            inference_start = datetime.now()

            # 模擬推論過程（實際實作時會載入真實模型）
            output_data = self._simulate_inference(model, input_data)

            # 記錄推論日誌
            self._log_inference(model_id, input_data, output_data, inference_start)

            # 更新最後推論時間
            self._update_last_inference(model_id)

            logger.info("模型推論完成: %s", model_id)
            return output_data

        except Exception as e:
            logger.error("模型推論時發生錯誤: %s", e)
            raise ModelInferenceError("推論失敗") from e

    def batch_predict(self, model_id: str, batch_data: List[Dict]) -> List[Dict]:
        """批量推論

        Args:
            model_id: 模型ID
            batch_data: 批量輸入數據列表

        Returns:
            List[Dict]: 批量推論結果
        """
        try:
            results = []
            for input_data in batch_data:
                result = self.predict(model_id, input_data)
                results.append(result)

            logger.info("批量推論完成: %s, 數量: %d", model_id, len(batch_data))
            return results

        except Exception as e:
            logger.error("批量推論時發生錯誤: %s", e)
            return []

    def get_inference_logs(self, model_id: str, limit: int = 100) -> List[Dict]:
        """獲取推論日誌

        Args:
            model_id: 模型ID
            limit: 返回數量限制

        Returns:
            List[Dict]: 推論日誌列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT * FROM model_inference_logs
                    WHERE model_id = ?
                    ORDER BY inference_time DESC
                    LIMIT ?
                    """,
                    (model_id, limit),
                )

                logs = cursor.fetchall()
                result = []
                for log in logs:
                    log_dict = dict(log)
                    log_dict["input_data"] = json.loads(log_dict["input_data"] or "{}")
                    log_dict["output_data"] = json.loads(
                        log_dict["output_data"] or "{}"
                    )
                    result.append(log_dict)

                return result

        except Exception as e:
            logger.error("獲取推論日誌時發生錯誤: %s", e)
            return []

    def get_inference_statistics(self, model_id: str = None) -> Dict:
        """獲取推論統計信息

        Args:
            model_id: 模型ID，如果為 None 則獲取所有模型的統計

        Returns:
            Dict: 推論統計信息
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if model_id:
                    # 特定模型的統計
                    cursor.execute(
                        "SELECT COUNT(*) FROM model_inference_logs WHERE model_id = ?",
                        (model_id,),
                    )
                    total_inferences = cursor.fetchone()[0]

                    cursor.execute(
                        """
                        SELECT COUNT(*) FROM model_inference_logs
                        WHERE model_id = ? AND inference_time >= datetime('now', '-24 hours')
                        """,
                        (model_id,),
                    )
                    recent_inferences = cursor.fetchone()[0]

                    return {
                        "model_id": model_id,
                        "total_inferences": total_inferences,
                        "recent_inferences": recent_inferences,
                    }
                else:
                    # 所有模型的統計
                    cursor.execute("SELECT COUNT(*) FROM model_inference_logs")
                    total_inferences = cursor.fetchone()[0]

                    cursor.execute(
                        """
                        SELECT model_id, COUNT(*)
                        FROM model_inference_logs
                        GROUP BY model_id
                        """
                    )
                    by_model = dict(cursor.fetchall())

                    cursor.execute(
                        """
                        SELECT COUNT(*) FROM model_inference_logs
                        WHERE inference_time >= datetime('now', '-24 hours')
                        """
                    )
                    recent_inferences = cursor.fetchone()[0]

                    return {
                        "total_inferences": total_inferences,
                        "by_model": by_model,
                        "recent_inferences": recent_inferences,
                    }

        except Exception as e:
            logger.error("獲取推論統計信息時發生錯誤: %s", e)
            return {}

    def _get_model_info(self, model_id: str) -> Dict:
        """獲取模型信息（內部方法）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("SELECT * FROM ai_models WHERE id = ?", (model_id,))
                model = cursor.fetchone()

                if model:
                    model_dict = dict(model)
                    model_dict["performance_metrics"] = json.loads(
                        model_dict["performance_metrics"] or "{}"
                    )
                    return model_dict

                return None

        except Exception as e:
            logger.error("獲取模型信息時發生錯誤: %s", e)
            return None

    def _simulate_inference(self, model: Dict, input_data: Dict) -> Dict:
        """模擬推論過程（內部方法）"""
        # 模擬推論過程（實際實作時會載入真實模型）
        if model["type"] == "機器學習模型":
            performance_metrics = model.get("performance_metrics", {})
            if "accuracy" in performance_metrics:
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

        return output_data

    def _log_inference(
        self, model_id: str, input_data: Dict, output_data: Dict, start_time: datetime
    ):
        """記錄推論日誌（內部方法）"""
        try:
            end_time = datetime.now()
            inference_time = (end_time - start_time).total_seconds()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO model_inference_logs
                    (model_id, input_data, output_data, inference_time, execution_time)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        model_id,
                        json.dumps(input_data),
                        json.dumps(output_data),
                        start_time,
                        inference_time,
                    ),
                )
                conn.commit()

        except Exception as e:
            logger.error("記錄推論日誌時發生錯誤: %s", e)

    def _update_last_inference(self, model_id: str):
        """更新最後推論時間（內部方法）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE ai_models SET last_inference = ? WHERE id = ?",
                    (datetime.now(), model_id),
                )
                conn.commit()

        except Exception as e:
            logger.error("更新最後推論時間時發生錯誤: %s", e)
