"""
遷移管理器

此模組實現 API 版本遷移的核心管理功能，包括遷移計劃的創建、
執行、監控和回滾等操作。
"""

import logging
import uuid
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from enum import Enum

from src.api.models.versioning import (
    MigrationPlan,
    MigrationStatusEnum,
    SemanticVersion,
)

logger = logging.getLogger(__name__)


class MigrationStepType(str, Enum):
    """遷移步驟類型"""

    DATABASE_SCHEMA = "database_schema"
    API_ENDPOINT = "api_endpoint"
    DATA_TRANSFORMATION = "data_transformation"
    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    CLEANUP = "cleanup"


class MigrationManager:
    """遷移管理器類"""

    def __init__(self, migration_dir: Optional[Path] = None):
        """
        初始化遷移管理器

        Args:
            migration_dir: 遷移文件目錄
        """
        self.migration_dir = migration_dir or Path("migrations")
        self.migration_dir.mkdir(exist_ok=True)

        # 遷移狀態快取
        self.active_migrations: Dict[str, MigrationPlan] = {}

        # 遷移步驟處理器
        self.step_handlers: Dict[MigrationStepType, Callable] = {
            MigrationStepType.DATABASE_SCHEMA: self._handle_database_schema,
            MigrationStepType.API_ENDPOINT: self._handle_api_endpoint,
            MigrationStepType.DATA_TRANSFORMATION: self._handle_data_transformation,
            MigrationStepType.CONFIGURATION: self._handle_configuration,
            MigrationStepType.VALIDATION: self._handle_validation,
            MigrationStepType.CLEANUP: self._handle_cleanup,
        }

    async def create_migration_plan(
        self,
        source_version: str,
        target_version: str,
        name: str,
        description: Optional[str] = None,
        created_by: str = "system",
    ) -> MigrationPlan:
        """
        創建遷移計劃

        Args:
            source_version: 源版本
            target_version: 目標版本
            name: 遷移名稱
            description: 遷移描述
            created_by: 創建者

        Returns:
            MigrationPlan: 遷移計劃
        """
        try:
            # 生成遷移 ID
            migration_id = str(uuid.uuid4())

            # 解析版本
            source_semantic = SemanticVersion.parse(source_version)
            target_semantic = SemanticVersion.parse(target_version)

            # 生成遷移步驟
            steps = await self._generate_migration_steps(
                source_semantic, target_semantic
            )
            rollback_steps = await self._generate_rollback_steps(steps)

            # 估算遷移時間
            estimated_duration = self._estimate_migration_duration(steps)

            # 創建遷移計劃
            migration_plan = MigrationPlan(
                migration_id=migration_id,
                name=name,
                description=description,
                source_version=source_version,
                target_version=target_version,
                steps=steps,
                rollback_steps=rollback_steps,
                estimated_duration=estimated_duration,
                created_by=created_by,
            )

            # 保存遷移計劃
            await self._save_migration_plan(migration_plan)

            logger.info(f"遷移計劃創建成功: {migration_id}")
            return migration_plan

        except Exception as e:
            logger.error(f"創建遷移計劃失敗: {e}")
            raise

    async def execute_migration(
        self, migration_id: str, dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        執行遷移

        Args:
            migration_id: 遷移 ID
            dry_run: 是否為試運行

        Returns:
            Dict[str, Any]: 執行結果
        """
        try:
            # 載入遷移計劃
            migration_plan = await self._load_migration_plan(migration_id)
            if not migration_plan:
                raise ValueError(f"遷移計劃不存在: {migration_id}")

            # 檢查遷移狀態
            if migration_plan.status == MigrationStatusEnum.IN_PROGRESS:
                raise ValueError("遷移正在進行中")
            elif migration_plan.status == MigrationStatusEnum.COMPLETED:
                raise ValueError("遷移已完成")

            # 更新狀態
            migration_plan.status = MigrationStatusEnum.IN_PROGRESS
            migration_plan.started_at = datetime.now()
            migration_plan.progress = 0.0

            # 添加到活躍遷移
            self.active_migrations[migration_id] = migration_plan

            # 執行遷移步驟
            execution_result = await self._execute_migration_steps(
                migration_plan, dry_run
            )

            # 更新最終狀態
            if execution_result["success"]:
                migration_plan.status = MigrationStatusEnum.COMPLETED
                migration_plan.progress = 100.0
            else:
                migration_plan.status = MigrationStatusEnum.FAILED

            migration_plan.completed_at = datetime.now()

            # 保存更新
            await self._save_migration_plan(migration_plan)

            # 從活躍遷移中移除
            self.active_migrations.pop(migration_id, None)

            logger.info(
                f"遷移執行完成: {migration_id}, 成功: {execution_result['success']}"
            )
            return execution_result

        except Exception as e:
            logger.error(f"執行遷移失敗: {e}")
            # 更新失敗狀態
            if migration_id in self.active_migrations:
                self.active_migrations[migration_id].status = MigrationStatusEnum.FAILED
                await self._save_migration_plan(self.active_migrations[migration_id])
                self.active_migrations.pop(migration_id, None)
            raise

    async def rollback_migration(self, migration_id: str) -> Dict[str, Any]:
        """
        回滾遷移

        Args:
            migration_id: 遷移 ID

        Returns:
            Dict[str, Any]: 回滾結果
        """
        try:
            # 載入遷移計劃
            migration_plan = await self._load_migration_plan(migration_id)
            if not migration_plan:
                raise ValueError(f"遷移計劃不存在: {migration_id}")

            # 檢查是否可以回滾
            if migration_plan.status != MigrationStatusEnum.COMPLETED:
                raise ValueError("只能回滾已完成的遷移")

            # 執行回滾步驟
            rollback_result = await self._execute_rollback_steps(migration_plan)

            # 更新狀態
            if rollback_result["success"]:
                migration_plan.status = MigrationStatusEnum.ROLLED_BACK
            else:
                migration_plan.status = MigrationStatusEnum.FAILED

            await self._save_migration_plan(migration_plan)

            logger.info(
                f"遷移回滾完成: {migration_id}, 成功: {rollback_result['success']}"
            )
            return rollback_result

        except Exception as e:
            logger.error(f"回滾遷移失敗: {e}")
            raise

    async def get_migration_status(self, migration_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取遷移狀態

        Args:
            migration_id: 遷移 ID

        Returns:
            Optional[Dict[str, Any]]: 遷移狀態
        """
        try:
            # 先檢查活躍遷移
            if migration_id in self.active_migrations:
                migration_plan = self.active_migrations[migration_id]
            else:
                # 從文件載入
                migration_plan = await self._load_migration_plan(migration_id)
                if not migration_plan:
                    return None

            return {
                "migration_id": migration_plan.migration_id,
                "name": migration_plan.name,
                "status": migration_plan.status.value,
                "progress": migration_plan.progress,
                "source_version": migration_plan.source_version,
                "target_version": migration_plan.target_version,
                "started_at": (
                    migration_plan.started_at.isoformat()
                    if migration_plan.started_at
                    else None
                ),
                "completed_at": (
                    migration_plan.completed_at.isoformat()
                    if migration_plan.completed_at
                    else None
                ),
                "success_count": migration_plan.success_count,
                "failure_count": migration_plan.failure_count,
                "error_messages": migration_plan.error_messages,
            }

        except Exception as e:
            logger.error(f"獲取遷移狀態失敗: {e}")
            return None

    async def list_migrations(
        self, status: Optional[MigrationStatusEnum] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        列出遷移記錄

        Args:
            status: 狀態篩選
            limit: 限制數量

        Returns:
            List[Dict[str, Any]]: 遷移記錄列表
        """
        try:
            migrations = []

            # 掃描遷移文件
            for migration_file in self.migration_dir.glob("*.json"):
                try:
                    migration_plan = await self._load_migration_plan_from_file(
                        migration_file
                    )
                    if migration_plan:
                        if status is None or migration_plan.status == status:
                            migrations.append(
                                {
                                    "migration_id": migration_plan.migration_id,
                                    "name": migration_plan.name,
                                    "status": migration_plan.status.value,
                                    "source_version": migration_plan.source_version,
                                    "target_version": migration_plan.target_version,
                                    "created_at": migration_plan.created_at.isoformat(),
                                    "started_at": (
                                        migration_plan.started_at.isoformat()
                                        if migration_plan.started_at
                                        else None
                                    ),
                                    "completed_at": (
                                        migration_plan.completed_at.isoformat()
                                        if migration_plan.completed_at
                                        else None
                                    ),
                                }
                            )
                except Exception as e:
                    logger.warning(f"載入遷移文件失敗 {migration_file}: {e}")

            # 按創建時間排序
            migrations.sort(key=lambda x: x["created_at"], reverse=True)

            return migrations[:limit]

        except Exception as e:
            logger.error(f"列出遷移記錄失敗: {e}")
            return []

    # ==================== 私有方法 ====================

    async def _generate_migration_steps(
        self, source: SemanticVersion, target: SemanticVersion
    ) -> List[Dict[str, Any]]:
        """生成遷移步驟"""
        steps = []

        # 主版本升級
        if target.major > source.major:
            steps.extend(
                [
                    {
                        "id": str(uuid.uuid4()),
                        "type": MigrationStepType.VALIDATION.value,
                        "name": "驗證主版本升級前置條件",
                        "description": "檢查主版本升級的前置條件",
                        "parameters": {"check_breaking_changes": True},
                        "estimated_duration": 5,
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "type": MigrationStepType.DATABASE_SCHEMA.value,
                        "name": "更新資料庫 Schema",
                        "description": "執行主版本資料庫 Schema 更新",
                        "parameters": {"major_upgrade": True},
                        "estimated_duration": 30,
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "type": MigrationStepType.API_ENDPOINT.value,
                        "name": "更新 API 端點",
                        "description": "更新 API 端點映射和路由",
                        "parameters": {"version_change": "major"},
                        "estimated_duration": 15,
                    },
                ]
            )

        # 次版本升級
        elif target.minor > source.minor:
            steps.extend(
                [
                    {
                        "id": str(uuid.uuid4()),
                        "type": MigrationStepType.API_ENDPOINT.value,
                        "name": "添加新 API 端點",
                        "description": "添加次版本新增的 API 端點",
                        "parameters": {"version_change": "minor"},
                        "estimated_duration": 10,
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "type": MigrationStepType.CONFIGURATION.value,
                        "name": "更新配置",
                        "description": "更新應用配置以支援新功能",
                        "parameters": {"minor_upgrade": True},
                        "estimated_duration": 5,
                    },
                ]
            )

        # 修訂版本升級
        elif target.patch > source.patch:
            steps.append(
                {
                    "id": str(uuid.uuid4()),
                    "type": MigrationStepType.VALIDATION.value,
                    "name": "驗證修訂版本更新",
                    "description": "驗證修訂版本的相容性",
                    "parameters": {"patch_upgrade": True},
                    "estimated_duration": 3,
                }
            )

        # 通用清理步驟
        steps.append(
            {
                "id": str(uuid.uuid4()),
                "type": MigrationStepType.CLEANUP.value,
                "name": "清理暫存資料",
                "description": "清理遷移過程中的暫存資料",
                "parameters": {},
                "estimated_duration": 2,
            }
        )

        return steps

    async def _generate_rollback_steps(
        self, steps: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """生成回滾步驟"""
        rollback_steps = []

        # 反向生成回滾步驟
        for step in reversed(steps):
            rollback_step = {
                "id": str(uuid.uuid4()),
                "type": step["type"],
                "name": f"回滾: {step['name']}",
                "description": f"回滾操作: {step['description']}",
                "parameters": {**step["parameters"], "rollback": True},
                "estimated_duration": step["estimated_duration"],
            }
            rollback_steps.append(rollback_step)

        return rollback_steps

    def _estimate_migration_duration(self, steps: List[Dict[str, Any]]) -> int:
        """估算遷移時間（分鐘）"""
        total_duration = sum(step.get("estimated_duration", 5) for step in steps)
        # 添加 20% 的緩衝時間
        return int(total_duration * 1.2)

    async def _save_migration_plan(self, migration_plan: MigrationPlan) -> None:
        """保存遷移計劃"""
        migration_file = self.migration_dir / f"{migration_plan.migration_id}.json"

        # 轉換為可序列化的格式
        plan_data = migration_plan.model_dump(mode="json")

        with open(migration_file, "w", encoding="utf-8") as f:
            json.dump(plan_data, f, ensure_ascii=False, indent=2, default=str)

    async def _load_migration_plan(self, migration_id: str) -> Optional[MigrationPlan]:
        """載入遷移計劃"""
        migration_file = self.migration_dir / f"{migration_id}.json"
        return await self._load_migration_plan_from_file(migration_file)

    async def _load_migration_plan_from_file(
        self, migration_file: Path
    ) -> Optional[MigrationPlan]:
        """從文件載入遷移計劃"""
        if not migration_file.exists():
            return None

        try:
            with open(migration_file, "r", encoding="utf-8") as f:
                plan_data = json.load(f)

            return MigrationPlan(**plan_data)
        except Exception as e:
            logger.error(f"載入遷移計劃失敗 {migration_file}: {e}")
            return None

    async def _execute_migration_steps(
        self, migration_plan: MigrationPlan, dry_run: bool = False
    ) -> Dict[str, Any]:
        """執行遷移步驟"""
        results = []
        success_count = 0
        failure_count = 0
        error_messages = []

        total_steps = len(migration_plan.steps)

        for i, step in enumerate(migration_plan.steps):
            try:
                logger.info(f"執行遷移步驟 {i+1}/{total_steps}: {step['name']}")

                # 更新進度
                migration_plan.progress = (i / total_steps) * 100
                await self._save_migration_plan(migration_plan)

                # 執行步驟
                step_result = await self._execute_migration_step(step, dry_run)
                results.append(step_result)

                if step_result["success"]:
                    success_count += 1
                else:
                    failure_count += 1
                    error_messages.append(
                        f"步驟 {step['name']} 失敗: {step_result.get('error', '未知錯誤')}"
                    )

            except Exception as e:
                failure_count += 1
                error_message = f"步驟 {step['name']} 執行異常: {e}"
                error_messages.append(error_message)
                logger.error(error_message)

                results.append(
                    {"step_id": step["id"], "success": False, "error": str(e)}
                )

        # 更新統計信息
        migration_plan.success_count = success_count
        migration_plan.failure_count = failure_count
        migration_plan.error_messages = error_messages

        return {
            "success": failure_count == 0,
            "total_steps": total_steps,
            "success_count": success_count,
            "failure_count": failure_count,
            "error_messages": error_messages,
            "step_results": results,
        }

    async def _execute_migration_step(
        self, step: Dict[str, Any], dry_run: bool = False
    ) -> Dict[str, Any]:
        """執行單個遷移步驟"""
        step_type = MigrationStepType(step["type"])
        handler = self.step_handlers.get(step_type)

        if not handler:
            return {
                "step_id": step["id"],
                "success": False,
                "error": f"未知的步驟類型: {step_type}",
            }

        try:
            result = await handler(step, dry_run)
            return {"step_id": step["id"], "success": True, "result": result}
        except Exception as e:
            return {"step_id": step["id"], "success": False, "error": str(e)}

    async def _execute_rollback_steps(
        self, migration_plan: MigrationPlan
    ) -> Dict[str, Any]:
        """執行回滾步驟"""
        results = []
        success_count = 0
        failure_count = 0
        error_messages = []

        for step in migration_plan.rollback_steps:
            try:
                step_result = await self._execute_migration_step(step, dry_run=False)
                results.append(step_result)

                if step_result["success"]:
                    success_count += 1
                else:
                    failure_count += 1
                    error_messages.append(
                        f"回滾步驟失敗: {step_result.get('error', '未知錯誤')}"
                    )

            except Exception as e:
                failure_count += 1
                error_message = f"回滾步驟執行異常: {e}"
                error_messages.append(error_message)
                logger.error(error_message)

        return {
            "success": failure_count == 0,
            "success_count": success_count,
            "failure_count": failure_count,
            "error_messages": error_messages,
            "step_results": results,
        }

    # ==================== 步驟處理器 ====================

    async def _handle_database_schema(self, step: Dict[str, Any], dry_run: bool) -> str:
        """處理資料庫 Schema 遷移"""
        if dry_run:
            return "資料庫 Schema 遷移（試運行）"

        # 實際實作中應該執行真實的資料庫遷移
        await asyncio.sleep(0.1)  # 模擬執行時間
        return "資料庫 Schema 遷移完成"

    async def _handle_api_endpoint(self, step: Dict[str, Any], dry_run: bool) -> str:
        """處理 API 端點遷移"""
        if dry_run:
            return "API 端點遷移（試運行）"

        await asyncio.sleep(0.1)
        return "API 端點遷移完成"

    async def _handle_data_transformation(
        self, step: Dict[str, Any], dry_run: bool
    ) -> str:
        """處理資料轉換"""
        if dry_run:
            return "資料轉換（試運行）"

        await asyncio.sleep(0.1)
        return "資料轉換完成"

    async def _handle_configuration(self, step: Dict[str, Any], dry_run: bool) -> str:
        """處理配置更新"""
        if dry_run:
            return "配置更新（試運行）"

        await asyncio.sleep(0.1)
        return "配置更新完成"

    async def _handle_validation(self, step: Dict[str, Any], dry_run: bool) -> str:
        """處理驗證步驟"""
        if dry_run:
            return "驗證步驟（試運行）"

        await asyncio.sleep(0.1)
        return "驗證步驟完成"

    async def _handle_cleanup(self, step: Dict[str, Any], dry_run: bool) -> str:
        """處理清理步驟"""
        if dry_run:
            return "清理步驟（試運行）"

        await asyncio.sleep(0.1)
        return "清理步驟完成"
