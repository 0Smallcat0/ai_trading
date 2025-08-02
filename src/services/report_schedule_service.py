"""
報表排程服務層

此模組實現報表排程管理的業務邏輯，包括排程的創建、查詢、更新、刪除、
執行管理和狀態監控等核心功能。
"""

import logging
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import asyncio
import croniter

# 導入資料庫相關模組
from sqlalchemy import create_engine, desc, func, and_, or_, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

# 導入配置
from src.config import DB_URL, CACHE_DIR

# 導入模型
from src.api.models.reports import (
    ReportSchedule,
    ReportScheduleCreateRequest,
    ReportScheduleUpdateRequest,
    ReportScheduleListRequest,
    ScheduleFrequencyEnum,
    ScheduleStatusEnum,
    ExecutionStatusEnum,
    ScheduleExecution,
    ScheduleExecutionResponse,
)

logger = logging.getLogger(__name__)


class ReportScheduleService:
    """報表排程服務類"""

    def __init__(self):
        """初始化服務"""
        self.engine = create_engine(DB_URL) if DB_URL else None
        self.session_factory = sessionmaker(bind=self.engine) if self.engine else None
        self.cache_dir = Path(CACHE_DIR) if CACHE_DIR else Path("cache")
        self.cache_dir.mkdir(exist_ok=True)

    def create_schedule(
        self, request: ReportScheduleCreateRequest, current_user: str
    ) -> Dict[str, Any]:
        """
        創建報表排程

        Args:
            request: 創建排程請求
            current_user: 當前用戶

        Returns:
            Dict[str, Any]: 創建的排程信息

        Raises:
            ValueError: 參數驗證失敗
            Exception: 創建失敗
        """
        try:
            # 生成排程ID
            schedule_id = str(uuid.uuid4())

            # 驗證 Cron 表達式
            if request.frequency == ScheduleFrequencyEnum.CUSTOM:
                if not request.cron_expression:
                    raise ValueError("自定義頻率時必須提供 Cron 表達式")
                try:
                    croniter.croniter(request.cron_expression)
                except ValueError as e:
                    raise ValueError(f"無效的 Cron 表達式: {e}")

            # 計算下次執行時間
            next_execution_time = self._calculate_next_execution_time(
                request.frequency, request.cron_expression, request.start_time
            )

            # 創建排程數據
            schedule_data = {
                "schedule_id": schedule_id,
                "name": request.name,
                "description": request.description,
                "report_type": request.report_type.value,
                "template_id": request.template_id,
                "frequency": request.frequency.value,
                "cron_expression": request.cron_expression,
                "start_time": request.start_time,
                "end_time": request.end_time,
                "timezone": request.timezone,
                "parameters": request.parameters,
                "notification_settings": request.notification_settings,
                "output_format": request.output_format.value,
                "status": ScheduleStatusEnum.ACTIVE.value,
                "is_enabled": request.is_enabled,
                "tags": request.tags,
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "next_execution_time": next_execution_time,
                "created_by": current_user,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

            # 模擬保存到資料庫（實際應該使用 SQLAlchemy）
            self._save_schedule_to_cache(schedule_id, schedule_data)

            logger.info(f"報表排程創建成功: {schedule_id}")
            return schedule_data

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"創建報表排程失敗: {e}")
            raise

    def get_schedule(
        self, schedule_id: str, current_user: str
    ) -> Optional[Dict[str, Any]]:
        """
        獲取單個排程詳情

        Args:
            schedule_id: 排程ID
            current_user: 當前用戶

        Returns:
            Optional[Dict[str, Any]]: 排程詳情
        """
        try:
            # 模擬從資料庫查詢（實際應該使用 SQLAlchemy）
            schedule_data = self._load_schedule_from_cache(schedule_id)

            if not schedule_data:
                return None

            # 檢查權限（簡化版本）
            if not self._check_schedule_permission(schedule_data, current_user, "read"):
                return None

            return schedule_data

        except Exception as e:
            logger.error(f"獲取排程詳情失敗: {e}")
            return None

    def list_schedules(
        self, request: ReportScheduleListRequest, current_user: str
    ) -> Dict[str, Any]:
        """
        查詢排程列表

        Args:
            request: 查詢請求
            current_user: 當前用戶

        Returns:
            Dict[str, Any]: 排程列表和分頁信息
        """
        try:
            # 模擬查詢邏輯（實際應該使用 SQLAlchemy）
            all_schedules = self._get_all_schedules_from_cache()

            # 權限過濾
            accessible_schedules = [
                schedule
                for schedule in all_schedules
                if self._check_schedule_permission(schedule, current_user, "read")
            ]

            # 應用篩選條件
            filtered_schedules = self._apply_filters(accessible_schedules, request)

            # 排序
            sorted_schedules = self._apply_sorting(
                filtered_schedules, request.sort_by, request.sort_order
            )

            # 分頁
            total = len(sorted_schedules)
            start_idx = (request.page - 1) * request.page_size
            end_idx = start_idx + request.page_size
            page_schedules = sorted_schedules[start_idx:end_idx]

            # 計算分頁信息
            total_pages = (total + request.page_size - 1) // request.page_size
            has_next = request.page < total_pages
            has_prev = request.page > 1

            return {
                "schedules": page_schedules,
                "total": total,
                "page": request.page,
                "page_size": request.page_size,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev,
            }

        except Exception as e:
            logger.error(f"查詢排程列表失敗: {e}")
            raise

    def update_schedule(
        self, schedule_id: str, request: ReportScheduleUpdateRequest, current_user: str
    ) -> Optional[Dict[str, Any]]:
        """
        更新排程

        Args:
            schedule_id: 排程ID
            request: 更新請求
            current_user: 當前用戶

        Returns:
            Optional[Dict[str, Any]]: 更新後的排程信息
        """
        try:
            # 獲取現有排程
            schedule_data = self._load_schedule_from_cache(schedule_id)
            if not schedule_data:
                return None

            # 檢查權限
            if not self._check_schedule_permission(
                schedule_data, current_user, "update"
            ):
                return None

            # 更新欄位
            update_fields = {}
            if request.name is not None:
                update_fields["name"] = request.name
            if request.description is not None:
                update_fields["description"] = request.description
            if request.template_id is not None:
                update_fields["template_id"] = request.template_id
            if request.frequency is not None:
                update_fields["frequency"] = request.frequency.value
            if request.cron_expression is not None:
                update_fields["cron_expression"] = request.cron_expression
            if request.start_time is not None:
                update_fields["start_time"] = request.start_time
            if request.end_time is not None:
                update_fields["end_time"] = request.end_time
            if request.timezone is not None:
                update_fields["timezone"] = request.timezone
            if request.parameters is not None:
                update_fields["parameters"] = request.parameters
            if request.notification_settings is not None:
                update_fields["notification_settings"] = request.notification_settings
            if request.output_format is not None:
                update_fields["output_format"] = request.output_format.value
            if request.status is not None:
                update_fields["status"] = request.status.value
            if request.is_enabled is not None:
                update_fields["is_enabled"] = request.is_enabled
            if request.tags is not None:
                update_fields["tags"] = request.tags

            # 如果頻率或時間發生變化，重新計算下次執行時間
            if any(
                field in update_fields
                for field in ["frequency", "cron_expression", "start_time"]
            ):
                frequency = update_fields.get("frequency", schedule_data["frequency"])
                cron_expr = update_fields.get(
                    "cron_expression", schedule_data.get("cron_expression")
                )
                start_time = update_fields.get(
                    "start_time", schedule_data["start_time"]
                )

                update_fields["next_execution_time"] = (
                    self._calculate_next_execution_time(
                        ScheduleFrequencyEnum(frequency), cron_expr, start_time
                    )
                )

            # 更新時間戳
            update_fields["updated_at"] = datetime.now()

            # 應用更新
            schedule_data.update(update_fields)

            # 保存更新
            self._save_schedule_to_cache(schedule_id, schedule_data)

            logger.info(f"排程更新成功: {schedule_id}")
            return schedule_data

        except Exception as e:
            logger.error(f"更新排程失敗: {e}")
            raise

    def delete_schedule(self, schedule_id: str, current_user: str) -> bool:
        """
        刪除排程

        Args:
            schedule_id: 排程ID
            current_user: 當前用戶

        Returns:
            bool: 是否刪除成功
        """
        try:
            # 獲取排程
            schedule_data = self._load_schedule_from_cache(schedule_id)
            if not schedule_data:
                return False

            # 檢查權限
            if not self._check_schedule_permission(
                schedule_data, current_user, "delete"
            ):
                return False

            # 軟刪除：更新狀態為已取消
            schedule_data["status"] = ScheduleStatusEnum.CANCELLED.value
            schedule_data["is_enabled"] = False
            schedule_data["updated_at"] = datetime.now()

            # 保存更新
            self._save_schedule_to_cache(schedule_id, schedule_data)

            logger.info(f"排程刪除成功: {schedule_id}")
            return True

        except Exception as e:
            logger.error(f"刪除排程失敗: {e}")
            return False

    def execute_schedule(self, schedule_id: str, current_user: str) -> Dict[str, Any]:
        """
        手動執行排程

        Args:
            schedule_id: 排程ID
            current_user: 當前用戶

        Returns:
            Dict[str, Any]: 執行結果
        """
        try:
            # 獲取排程
            schedule_data = self._load_schedule_from_cache(schedule_id)
            if not schedule_data:
                raise ValueError("排程不存在")

            # 檢查權限
            if not self._check_schedule_permission(
                schedule_data, current_user, "execute"
            ):
                raise ValueError("無權限執行此排程")

            # 檢查排程狀態
            if schedule_data["status"] != ScheduleStatusEnum.ACTIVE.value:
                raise ValueError("排程狀態不允許執行")

            if not schedule_data["is_enabled"]:
                raise ValueError("排程已停用")

            # 生成執行ID
            execution_id = str(uuid.uuid4())

            # 創建執行記錄
            execution_data = {
                "execution_id": execution_id,
                "schedule_id": schedule_id,
                "schedule_name": schedule_data["name"],
                "report_type": schedule_data["report_type"],
                "status": ExecutionStatusEnum.PENDING.value,
                "start_time": datetime.now(),
                "created_at": datetime.now(),
            }

            # 保存執行記錄
            self._save_execution_to_cache(execution_id, execution_data)

            # 異步執行報表生成（實際應該使用 Celery 或其他任務隊列）
            asyncio.create_task(
                self._execute_report_generation(execution_id, schedule_data)
            )

            # 更新排程統計
            schedule_data["total_executions"] += 1
            schedule_data["last_execution_time"] = datetime.now()
            schedule_data["updated_at"] = datetime.now()
            self._save_schedule_to_cache(schedule_id, schedule_data)

            logger.info(f"排程執行啟動成功: {schedule_id}, 執行ID: {execution_id}")

            return {
                "execution_id": execution_id,
                "schedule_id": schedule_id,
                "status": ExecutionStatusEnum.PENDING.value,
                "message": "排程執行已啟動",
                "estimated_completion_time": datetime.now() + timedelta(minutes=5),
                "progress_url": f"/api/v1/reports/schedules/{schedule_id}/executions/{execution_id}",
                "created_at": datetime.now(),
            }

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"執行排程失敗: {e}")
            raise

    def get_execution_history(
        self,
        schedule_id: str,
        page: int = 1,
        page_size: int = 20,
        current_user: str = None,
    ) -> Dict[str, Any]:
        """
        獲取排程執行歷史

        Args:
            schedule_id: 排程ID
            page: 頁碼
            page_size: 每頁數量
            current_user: 當前用戶

        Returns:
            Dict[str, Any]: 執行歷史列表
        """
        try:
            # 檢查排程是否存在和權限
            schedule_data = self._load_schedule_from_cache(schedule_id)
            if not schedule_data:
                return {
                    "executions": [],
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                }

            if current_user and not self._check_schedule_permission(
                schedule_data, current_user, "read"
            ):
                return {
                    "executions": [],
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                }

            # 模擬獲取執行歷史
            all_executions = self._get_executions_by_schedule(schedule_id)

            # 排序（最新的在前）
            sorted_executions = sorted(
                all_executions, key=lambda x: x["start_time"], reverse=True
            )

            # 分頁
            total = len(sorted_executions)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_executions = sorted_executions[start_idx:end_idx]

            # 計算分頁信息
            total_pages = (total + page_size - 1) // page_size
            has_next = page < total_pages
            has_prev = page > 1

            return {
                "executions": page_executions,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev,
            }

        except Exception as e:
            logger.error(f"獲取執行歷史失敗: {e}")
            raise

    # ==================== 私有方法 ====================

    def _calculate_next_execution_time(
        self,
        frequency: ScheduleFrequencyEnum,
        cron_expression: Optional[str],
        start_time: datetime,
    ) -> Optional[datetime]:
        """計算下次執行時間"""
        try:
            now = datetime.now()

            if frequency == ScheduleFrequencyEnum.ONCE:
                return start_time if start_time > now else None

            elif frequency == ScheduleFrequencyEnum.DAILY:
                next_time = start_time
                while next_time <= now:
                    next_time += timedelta(days=1)
                return next_time

            elif frequency == ScheduleFrequencyEnum.WEEKLY:
                next_time = start_time
                while next_time <= now:
                    next_time += timedelta(weeks=1)
                return next_time

            elif frequency == ScheduleFrequencyEnum.MONTHLY:
                next_time = start_time
                while next_time <= now:
                    if next_time.month == 12:
                        next_time = next_time.replace(year=next_time.year + 1, month=1)
                    else:
                        next_time = next_time.replace(month=next_time.month + 1)
                return next_time

            elif frequency == ScheduleFrequencyEnum.CUSTOM and cron_expression:
                cron = croniter.croniter(cron_expression, now)
                return cron.get_next(datetime)

            return None

        except Exception as e:
            logger.error(f"計算下次執行時間失敗: {e}")
            return None

    def _check_schedule_permission(
        self, schedule_data: Dict[str, Any], current_user: str, action: str
    ) -> bool:
        """檢查排程權限"""
        # 簡化版本的權限檢查
        # 實際應該根據用戶角色和排程所有者進行檢查
        if current_user == "admin":
            return True

        if schedule_data.get("created_by") == current_user:
            return True

        # 其他權限邏輯...
        return False

    def _save_schedule_to_cache(self, schedule_id: str, schedule_data: Dict[str, Any]):
        """保存排程到快取"""
        cache_file = self.cache_dir / f"schedule_{schedule_id}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            # 處理 datetime 序列化
            serializable_data = self._make_serializable(schedule_data)
            json.dump(serializable_data, f, ensure_ascii=False, indent=2)

    def _load_schedule_from_cache(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """從快取載入排程"""
        cache_file = self.cache_dir / f"schedule_{schedule_id}.json"
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return self._deserialize_datetime_fields(data)
        except Exception as e:
            logger.error(f"載入排程快取失敗: {e}")
            return None

    def _get_all_schedules_from_cache(self) -> List[Dict[str, Any]]:
        """獲取所有排程"""
        schedules = []
        for cache_file in self.cache_dir.glob("schedule_*.json"):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    schedules.append(self._deserialize_datetime_fields(data))
            except Exception as e:
                logger.error(f"載入排程快取失敗 {cache_file}: {e}")
        return schedules

    def _apply_filters(
        self, schedules: List[Dict[str, Any]], request: ReportScheduleListRequest
    ) -> List[Dict[str, Any]]:
        """應用篩選條件"""
        filtered = schedules

        # 搜尋關鍵字
        if request.search:
            search_lower = request.search.lower()
            filtered = [
                s
                for s in filtered
                if search_lower in s["name"].lower()
                or (s.get("description") and search_lower in s["description"].lower())
            ]

        # 報表類型篩選
        if request.report_type:
            filtered = [
                s for s in filtered if s["report_type"] == request.report_type.value
            ]

        # 狀態篩選
        if request.status:
            filtered = [s for s in filtered if s["status"] == request.status.value]

        # 頻率篩選
        if request.frequency:
            filtered = [
                s for s in filtered if s["frequency"] == request.frequency.value
            ]

        # 啟用狀態篩選
        if request.is_enabled is not None:
            filtered = [s for s in filtered if s["is_enabled"] == request.is_enabled]

        # 標籤篩選
        if request.tags:
            filtered = [
                s
                for s in filtered
                if s.get("tags") and any(tag in s["tags"] for tag in request.tags)
            ]

        return filtered

    def _apply_sorting(
        self, schedules: List[Dict[str, Any]], sort_by: str, sort_order: str
    ) -> List[Dict[str, Any]]:
        """應用排序"""
        reverse = sort_order == "desc"

        try:
            if sort_by == "name":
                return sorted(schedules, key=lambda x: x["name"], reverse=reverse)
            elif sort_by == "created_at":
                return sorted(schedules, key=lambda x: x["created_at"], reverse=reverse)
            elif sort_by == "updated_at":
                return sorted(schedules, key=lambda x: x["updated_at"], reverse=reverse)
            elif sort_by == "report_type":
                return sorted(
                    schedules, key=lambda x: x["report_type"], reverse=reverse
                )
            elif sort_by == "status":
                return sorted(schedules, key=lambda x: x["status"], reverse=reverse)
            elif sort_by == "frequency":
                return sorted(schedules, key=lambda x: x["frequency"], reverse=reverse)
            elif sort_by == "next_run_time":
                return sorted(
                    schedules,
                    key=lambda x: x.get("next_execution_time") or datetime.min,
                    reverse=reverse,
                )
            elif sort_by == "last_run_time":
                return sorted(
                    schedules,
                    key=lambda x: x.get("last_execution_time") or datetime.min,
                    reverse=reverse,
                )
            else:
                return schedules
        except Exception as e:
            logger.error(f"排序失敗: {e}")
            return schedules

    def _save_execution_to_cache(
        self, execution_id: str, execution_data: Dict[str, Any]
    ):
        """保存執行記錄到快取"""
        cache_file = self.cache_dir / f"execution_{execution_id}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            serializable_data = self._make_serializable(execution_data)
            json.dump(serializable_data, f, ensure_ascii=False, indent=2)

    def _get_executions_by_schedule(self, schedule_id: str) -> List[Dict[str, Any]]:
        """獲取指定排程的執行記錄"""
        executions = []
        for cache_file in self.cache_dir.glob("execution_*.json"):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    execution_data = self._deserialize_datetime_fields(data)
                    if execution_data.get("schedule_id") == schedule_id:
                        executions.append(execution_data)
            except Exception as e:
                logger.error(f"載入執行記錄快取失敗 {cache_file}: {e}")
        return executions

    async def _execute_report_generation(
        self, execution_id: str, schedule_data: Dict[str, Any]
    ):
        """異步執行報表生成"""
        try:
            # 更新執行狀態為運行中
            execution_data = self._load_execution_from_cache(execution_id)
            if not execution_data:
                return

            execution_data["status"] = ExecutionStatusEnum.RUNNING.value
            self._save_execution_to_cache(execution_id, execution_data)

            # 模擬報表生成過程
            await asyncio.sleep(2)  # 模擬處理時間

            # 模擬生成結果
            report_id = str(uuid.uuid4())
            output_file_path = f"/reports/{report_id}.{schedule_data['output_format']}"
            file_size = 1024 * 1024  # 1MB

            # 更新執行結果
            execution_data.update(
                {
                    "status": ExecutionStatusEnum.COMPLETED.value,
                    "end_time": datetime.now(),
                    "duration": 2.0,
                    "report_id": report_id,
                    "output_file_path": output_file_path,
                    "file_size": file_size,
                    "download_url": f"/api/v1/reports/download/{report_id}",
                    "notification_sent": True,
                    "notification_status": "sent",
                }
            )

            self._save_execution_to_cache(execution_id, execution_data)

            # 更新排程統計
            schedule_data["successful_executions"] += 1
            schedule_data["last_execution_status"] = ExecutionStatusEnum.COMPLETED.value
            self._save_schedule_to_cache(schedule_data["schedule_id"], schedule_data)

            logger.info(f"報表生成完成: {execution_id}")

        except Exception as e:
            logger.error(f"報表生成失敗: {e}")

            # 更新執行狀態為失敗
            execution_data = self._load_execution_from_cache(execution_id)
            if execution_data:
                execution_data.update(
                    {
                        "status": ExecutionStatusEnum.FAILED.value,
                        "end_time": datetime.now(),
                        "error_message": str(e),
                        "error_details": {"exception_type": type(e).__name__},
                    }
                )
                self._save_execution_to_cache(execution_id, execution_data)

                # 更新排程統計
                schedule_data["failed_executions"] += 1
                schedule_data["last_execution_status"] = (
                    ExecutionStatusEnum.FAILED.value
                )
                self._save_schedule_to_cache(
                    schedule_data["schedule_id"], schedule_data
                )

    def _load_execution_from_cache(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """從快取載入執行記錄"""
        cache_file = self.cache_dir / f"execution_{execution_id}.json"
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return self._deserialize_datetime_fields(data)
        except Exception as e:
            logger.error(f"載入執行記錄快取失敗: {e}")
            return None

    def _make_serializable(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """將數據轉換為可序列化格式"""
        serializable = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                serializable[key] = value.isoformat()
            elif isinstance(value, dict):
                serializable[key] = self._make_serializable(value)
            elif isinstance(value, list):
                serializable[key] = [
                    (
                        self._make_serializable(item)
                        if isinstance(item, dict)
                        else item.isoformat() if isinstance(item, datetime) else item
                    )
                    for item in value
                ]
            else:
                serializable[key] = value
        return serializable

    def _deserialize_datetime_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """反序列化 datetime 欄位"""
        datetime_fields = [
            "start_time",
            "end_time",
            "created_at",
            "updated_at",
            "last_execution_time",
            "next_execution_time",
        ]

        for field in datetime_fields:
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = datetime.fromisoformat(data[field])
                except ValueError:
                    pass

        return data
