"""策略版本控制模組

此模組提供策略版本管理功能，包括版本創建、查詢、比較等操作。
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class StrategyVersionError(Exception):
    """策略版本異常類別"""


class StrategyVersion:
    """策略版本控制類別"""

    def __init__(self, db_path: Path, strategies_dir: Path):
        """初始化策略版本控制
        
        Args:
            db_path: 資料庫路徑
            strategies_dir: 策略檔案目錄
        """
        self.db_path = db_path
        self.strategies_dir = strategies_dir

    def create_version(
        self,
        strategy_id: str,
        code: str = None,
        parameters: Dict = None,
        risk_parameters: Dict = None,
        change_log: str = "",
        author: str = "系統",
    ) -> str:
        """創建新版本
        
        Args:
            strategy_id: 策略ID
            code: 策略代碼
            parameters: 策略參數
            risk_parameters: 風險參數
            change_log: 變更日誌
            author: 作者
            
        Returns:
            str: 新版本號
            
        Raises:
            StrategyVersionError: 創建失敗時拋出
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 獲取當前策略信息
                cursor.execute("SELECT * FROM strategies WHERE id = ?", (strategy_id,))
                current_strategy = cursor.fetchone()

                if not current_strategy:
                    raise StrategyVersionError(f"策略不存在: {strategy_id}")

                # 獲取當前版本號並遞增
                current_version = current_strategy[6]  # version 欄位
                new_version = self._increment_version(current_version)

                # 準備更新數據
                update_data = {}
                if code is not None:
                    update_data["code"] = code
                if parameters is not None:
                    update_data["parameters"] = json.dumps(parameters)
                if risk_parameters is not None:
                    update_data["risk_parameters"] = json.dumps(risk_parameters)

                # 更新策略主表
                if update_data:
                    update_fields = ", ".join([f"{k} = ?" for k in update_data.keys()])
                    update_values = list(update_data.values())
                    update_values.extend([new_version, datetime.now(), strategy_id])

                    cursor.execute(
                        f"""
                        UPDATE strategies 
                        SET {update_fields}, version = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        update_values,
                    )

                # 創建版本記錄
                cursor.execute(
                    """
                    INSERT INTO strategy_versions
                    (strategy_id, version, code, parameters, risk_parameters,
                     change_log, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        strategy_id,
                        new_version,
                        code or current_strategy[8],  # code 欄位
                        json.dumps(parameters) if parameters else current_strategy[9],
                        json.dumps(risk_parameters) if risk_parameters else current_strategy[10],
                        change_log,
                        author,
                    ),
                )

                conn.commit()

                # 保存策略代碼文件
                if code is not None:
                    self._save_strategy_file(strategy_id, new_version, code)

                logger.info("策略版本創建成功: %s -> %s", strategy_id, new_version)
                return new_version

        except Exception as e:
            logger.error("創建策略版本時發生錯誤: %s", e)
            raise StrategyVersionError("創建版本失敗") from e

    def get_versions(self, strategy_id: str) -> List[Dict]:
        """獲取策略所有版本
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            List[Dict]: 版本列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT * FROM strategy_versions 
                    WHERE strategy_id = ? 
                    ORDER BY created_at DESC
                    """,
                    (strategy_id,),
                )

                versions = cursor.fetchall()
                result = []

                for version in versions:
                    version_dict = dict(version)
                    version_dict["parameters"] = json.loads(version_dict["parameters"])
                    version_dict["risk_parameters"] = json.loads(
                        version_dict["risk_parameters"]
                    )
                    result.append(version_dict)

                return result

        except Exception as e:
            logger.error("獲取策略版本時發生錯誤: %s", e)
            return []

    def get_version(self, strategy_id: str, version: str) -> Dict:
        """獲取特定版本信息
        
        Args:
            strategy_id: 策略ID
            version: 版本號
            
        Returns:
            Dict: 版本信息
            
        Raises:
            StrategyVersionError: 獲取失敗時拋出
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT * FROM strategy_versions 
                    WHERE strategy_id = ? AND version = ?
                    """,
                    (strategy_id, version),
                )

                version_data = cursor.fetchone()

                if not version_data:
                    raise StrategyVersionError(f"版本不存在: {strategy_id}@{version}")

                version_dict = dict(version_data)
                version_dict["parameters"] = json.loads(version_dict["parameters"])
                version_dict["risk_parameters"] = json.loads(
                    version_dict["risk_parameters"]
                )

                return version_dict

        except Exception as e:
            logger.error("獲取策略版本時發生錯誤: %s", e)
            raise StrategyVersionError("獲取版本失敗") from e

    def rollback_version(self, strategy_id: str, target_version: str) -> bool:
        """回滾到指定版本
        
        Args:
            strategy_id: 策略ID
            target_version: 目標版本號
            
        Returns:
            bool: 是否成功回滾
        """
        try:
            # 獲取目標版本信息
            target_version_data = self.get_version(strategy_id, target_version)

            # 創建新版本（基於目標版本）
            new_version = self.create_version(
                strategy_id=strategy_id,
                code=target_version_data["code"],
                parameters=target_version_data["parameters"],
                risk_parameters=target_version_data["risk_parameters"],
                change_log=f"回滾到版本 {target_version}",
                author="系統",
            )

            logger.info("策略回滾成功: %s 回滾到 %s (新版本: %s)", 
                       strategy_id, target_version, new_version)
            return True

        except Exception as e:
            logger.error("回滾策略版本時發生錯誤: %s", e)
            return False

    def compare_versions(self, strategy_id: str, version1: str, version2: str) -> Dict:
        """比較兩個版本的差異
        
        Args:
            strategy_id: 策略ID
            version1: 版本1
            version2: 版本2
            
        Returns:
            Dict: 比較結果
        """
        try:
            v1_data = self.get_version(strategy_id, version1)
            v2_data = self.get_version(strategy_id, version2)

            comparison = {
                "strategy_id": strategy_id,
                "version1": version1,
                "version2": version2,
                "differences": {
                    "code_changed": v1_data["code"] != v2_data["code"],
                    "parameters_changed": v1_data["parameters"] != v2_data["parameters"],
                    "risk_parameters_changed": v1_data["risk_parameters"] != v2_data["risk_parameters"],
                },
                "version1_data": v1_data,
                "version2_data": v2_data,
            }

            return comparison

        except Exception as e:
            logger.error("比較策略版本時發生錯誤: %s", e)
            return {}

    def _increment_version(self, current_version: str) -> str:
        """遞增版本號
        
        Args:
            current_version: 當前版本號
            
        Returns:
            str: 新版本號
        """
        try:
            parts = current_version.split(".")
            if len(parts) != 3:
                return "1.0.1"

            major, minor, patch = map(int, parts)
            patch += 1

            return f"{major}.{minor}.{patch}"

        except Exception:
            return "1.0.1"

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
