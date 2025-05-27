"""策略 CRUD 操作模組

此模組提供策略的基本 CRUD (Create, Read, Update, Delete) 操作功能。
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class StrategyManagementError(Exception):
    """策略管理異常類別"""


class StrategyCRUD:
    """策略 CRUD 操作類別"""

    def __init__(self, db_path: Path, strategies_dir: Path):
        """初始化策略 CRUD 操作
        
        Args:
            db_path: 資料庫路徑
            strategies_dir: 策略檔案目錄
        """
        self.db_path = db_path
        self.strategies_dir = strategies_dir

    def create_strategy(
        self,
        name: str,
        strategy_type: str,
        category: str = None,
        description: str = "",
        author: str = "系統",
        code: str = "",
        parameters: Dict = None,
        risk_parameters: Dict = None,
        tags: List[str] = None,
    ) -> str:
        """創建新策略
        
        Args:
            name: 策略名稱
            strategy_type: 策略類型
            category: 策略分類
            description: 策略描述
            author: 作者
            code: 策略代碼
            parameters: 策略參數
            risk_parameters: 風險參數
            tags: 標籤列表
            
        Returns:
            str: 策略ID
            
        Raises:
            StrategyManagementError: 創建失敗時拋出
        """
        try:
            strategy_id = str(uuid.uuid4())
            version = "1.0.0"

            # 準備數據
            parameters_json = json.dumps(parameters) if parameters else "{}"
            risk_parameters_json = (
                json.dumps(risk_parameters) if risk_parameters else "{}"
            )
            tags_json = json.dumps(tags) if tags else "[]"

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 檢查策略名稱是否已存在
                cursor.execute("SELECT id FROM strategies WHERE name = ?", (name,))
                if cursor.fetchone():
                    raise StrategyManagementError(f"策略名稱 '{name}' 已存在")

                # 插入策略
                cursor.execute(
                    """
                    INSERT INTO strategies
                    (id, name, type, category, description, author, version, status,
                     code, parameters, risk_parameters, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        strategy_id,
                        name,
                        strategy_type,
                        category,
                        description,
                        author,
                        version,
                        "draft",
                        code,
                        parameters_json,
                        risk_parameters_json,
                        tags_json,
                    ),
                )

                # 創建初始版本記錄
                cursor.execute(
                    """
                    INSERT INTO strategy_versions
                    (strategy_id, version, code, parameters, risk_parameters,
                     change_log, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        strategy_id,
                        version,
                        code,
                        parameters_json,
                        risk_parameters_json,
                        "初始版本",
                        author,
                    ),
                )

                conn.commit()

                # 保存策略代碼文件
                self._save_strategy_file(strategy_id, version, code)

                logger.info("策略創建成功: %s (ID: %s)", name, strategy_id)
                return strategy_id

        except Exception as e:
            logger.error("創建策略時發生錯誤: %s", e)
            raise StrategyManagementError("創建策略失敗") from e

    def get_strategy(self, strategy_id: str) -> Dict:
        """獲取策略詳細信息
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            Dict: 策略信息
            
        Raises:
            StrategyManagementError: 獲取失敗時拋出
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("SELECT * FROM strategies WHERE id = ?", (strategy_id,))
                strategy = cursor.fetchone()

                if not strategy:
                    raise StrategyManagementError(f"策略不存在: {strategy_id}")

                # 轉換為字典並解析 JSON 字段
                strategy_dict = dict(strategy)
                strategy_dict["parameters"] = json.loads(strategy_dict["parameters"])
                strategy_dict["risk_parameters"] = json.loads(
                    strategy_dict["risk_parameters"]
                )
                strategy_dict["tags"] = json.loads(strategy_dict["tags"])

                return strategy_dict

        except Exception as e:
            logger.error("獲取策略時發生錯誤: %s", e)
            raise StrategyManagementError("獲取策略失敗") from e

    def list_strategies(
        self,
        strategy_type: str = None,
        status: str = None,
        author: str = None,
        search_query: str = None,
        limit: int = 100,
    ) -> List[Dict]:
        """列出策略
        
        Args:
            strategy_type: 策略類型過濾
            status: 狀態過濾
            author: 作者過濾
            search_query: 搜尋關鍵字
            limit: 返回數量限制
            
        Returns:
            List[Dict]: 策略列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # 構建查詢條件
                conditions = []
                params = []

                if strategy_type:
                    conditions.append("type = ?")
                    params.append(strategy_type)

                if status:
                    conditions.append("status = ?")
                    params.append(status)

                if author:
                    conditions.append("author = ?")
                    params.append(author)

                if search_query:
                    conditions.append("(name LIKE ? OR description LIKE ?)")
                    params.extend([f"%{search_query}%", f"%{search_query}%"])

                # 構建查詢
                where_clause = " AND ".join(conditions) if conditions else "1=1"
                query = f"""
                    SELECT * FROM strategies
                    WHERE {where_clause}
                    ORDER BY updated_at DESC
                    LIMIT ?
                """
                params.append(limit)

                cursor.execute(query, params)
                strategies = cursor.fetchall()

                # 轉換為字典列表
                result = []
                for strategy in strategies:
                    strategy_dict = dict(strategy)
                    strategy_dict["parameters"] = json.loads(strategy_dict["parameters"])
                    strategy_dict["risk_parameters"] = json.loads(
                        strategy_dict["risk_parameters"]
                    )
                    strategy_dict["tags"] = json.loads(strategy_dict["tags"])
                    result.append(strategy_dict)

                return result

        except Exception as e:
            logger.error("列出策略時發生錯誤: %s", e)
            return []

    def delete_strategy(self, strategy_id: str) -> bool:
        """刪除策略
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            bool: 是否成功刪除
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 刪除策略版本
                cursor.execute(
                    "DELETE FROM strategy_versions WHERE strategy_id = ?", (strategy_id,)
                )

                # 刪除策略
                cursor.execute("DELETE FROM strategies WHERE id = ?", (strategy_id,))

                if not cursor.rowcount:
                    raise StrategyManagementError(f"策略不存在: {strategy_id}")

                conn.commit()

                # 刪除策略文件
                self._delete_strategy_files(strategy_id)

                logger.info("策略刪除成功: %s", strategy_id)
                return True

        except Exception as e:
            logger.error("刪除策略時發生錯誤: %s", e)
            return False

    def update_strategy_status(self, strategy_id: str, status: str) -> bool:
        """更新策略狀態
        
        Args:
            strategy_id: 策略ID
            status: 新狀態
            
        Returns:
            bool: 是否成功更新
        """
        try:
            valid_statuses = ["draft", "active", "testing", "disabled", "archived"]
            if status not in valid_statuses:
                raise StrategyManagementError(f"無效的狀態: {status}")

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE strategies SET status = ?, updated_at = ? WHERE id = ?",
                    (status, datetime.now(), strategy_id),
                )

                if not cursor.rowcount:
                    raise StrategyManagementError(f"策略不存在: {strategy_id}")

                conn.commit()

                logger.info("策略狀態更新成功: %s -> %s", strategy_id, status)
                return True

        except Exception as e:
            logger.error("更新策略狀態時發生錯誤: %s", e)
            return False

    def _save_strategy_file(self, strategy_id: str, version: str, code: str):
        """保存策略代碼文件"""
        try:
            strategy_dir = self.strategies_dir / strategy_id
            strategy_dir.mkdir(exist_ok=True)

            file_path = strategy_dir / f"strategy_{version}.py"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)

        except Exception as e:
            logger.error("保存策略文件時發生錯誤: %s", e)

    def _delete_strategy_files(self, strategy_id: str):
        """刪除策略文件"""
        try:
            strategy_dir = self.strategies_dir / strategy_id
            if strategy_dir.exists():
                import shutil
                shutil.rmtree(strategy_dir)

        except Exception as e:
            logger.error("刪除策略文件時發生錯誤: %s", e)
