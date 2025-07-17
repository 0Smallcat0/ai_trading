"""
操作記錄服務 (Operation Log Service)

此模組提供操作記錄的核心服務功能，包括：
- 用戶操作記錄
- 操作歷史查詢
- 操作統計分析
- 異常操作檢測
- 操作審計追蹤

符合 Phase 7.2 程式碼品質標準：
- Pylint ≥8.5/10
- 100% Google Style Docstring 覆蓋率
- 完整型別標註
- 統一錯誤處理模式
"""

import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """操作類型枚舉"""
    LOGIN = "login"
    LOGOUT = "logout"
    VIEW_PAGE = "view_page"
    CREATE_STRATEGY = "create_strategy"
    EDIT_STRATEGY = "edit_strategy"
    DELETE_STRATEGY = "delete_strategy"
    RUN_BACKTEST = "run_backtest"
    PLACE_ORDER = "place_order"
    CANCEL_ORDER = "cancel_order"
    MODIFY_SETTINGS = "modify_settings"
    EXPORT_DATA = "export_data"
    IMPORT_DATA = "import_data"
    ERROR_OCCURRED = "error_occurred"


class OperationResult(Enum):
    """操作結果枚舉"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class OperationLog:
    """
    操作記錄類別
    
    Attributes:
        log_id: 記錄唯一識別碼
        user_id: 用戶ID
        operation_type: 操作類型
        operation_name: 操作名稱
        result: 操作結果
        timestamp: 操作時間
        duration_ms: 執行時間(毫秒)
        ip_address: IP 地址
        user_agent: 用戶代理
        details: 操作詳細資訊
        error_message: 錯誤訊息
        metadata: 額外資訊
    """

    def __init__(
        self,
        user_id: str,
        operation_type: OperationType,
        operation_name: str,
        result: OperationResult = OperationResult.SUCCESS,
        duration_ms: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        **metadata
    ):
        """
        初始化操作記錄
        
        Args:
            user_id: 用戶ID
            operation_type: 操作類型
            operation_name: 操作名稱
            result: 操作結果
            duration_ms: 執行時間(毫秒)
            ip_address: IP 地址
            user_agent: 用戶代理
            details: 操作詳細資訊
            error_message: 錯誤訊息
            **metadata: 額外資訊
        """
        self.log_id = f"op_log_{int(datetime.now().timestamp() * 1000)}"
        self.user_id = user_id
        self.operation_type = operation_type
        self.operation_name = operation_name
        self.result = result
        self.timestamp = datetime.now()
        self.duration_ms = duration_ms
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.details = details or {}
        self.error_message = error_message
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典格式
        
        Returns:
            Dict[str, Any]: 操作記錄資訊字典
        """
        return {
            "log_id": self.log_id,
            "user_id": self.user_id,
            "operation_type": self.operation_type.value,
            "operation_name": self.operation_name,
            "result": self.result.value,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "details": self.details,
            "error_message": self.error_message,
            "metadata": self.metadata
        }


class OperationLogError(Exception):
    """操作記錄錯誤"""
    pass


class OperationLogService:
    """
    操作記錄服務
    
    提供用戶操作記錄功能，包括記錄管理、查詢分析、
    異常檢測等。
    
    Attributes:
        _operation_logs: 操作記錄列表
        _log_callbacks: 記錄回調函數列表
        _max_logs: 最大記錄數量
        _retention_days: 記錄保留天數
    """

    def __init__(self, max_logs: int = 10000, retention_days: int = 90):
        """
        初始化操作記錄服務
        
        Args:
            max_logs: 最大記錄數量
            retention_days: 記錄保留天數
        """
        self._operation_logs: List[OperationLog] = []
        self._log_callbacks: List[Callable[[OperationLog], None]] = []
        self._max_logs = max_logs
        self._retention_days = retention_days
        
        logger.info("操作記錄服務初始化成功")

    def log_operation(
        self,
        user_id: str,
        operation_type: OperationType,
        operation_name: str,
        result: OperationResult = OperationResult.SUCCESS,
        duration_ms: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        **metadata
    ) -> str:
        """
        記錄操作
        
        Args:
            user_id: 用戶ID
            operation_type: 操作類型
            operation_name: 操作名稱
            result: 操作結果
            duration_ms: 執行時間(毫秒)
            ip_address: IP 地址
            user_agent: 用戶代理
            details: 操作詳細資訊
            error_message: 錯誤訊息
            **metadata: 額外資訊
            
        Returns:
            str: 記錄ID
        """
        try:
            operation_log = OperationLog(
                user_id=user_id,
                operation_type=operation_type,
                operation_name=operation_name,
                result=result,
                duration_ms=duration_ms,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details,
                error_message=error_message,
                **metadata
            )
            
            # 添加記錄
            self._operation_logs.append(operation_log)
            
            # 清理舊記錄
            self._cleanup_old_logs()
            
            # 觸發回調
            for callback in self._log_callbacks:
                try:
                    callback(operation_log)
                except Exception as e:
                    logger.error("執行記錄回調時發生錯誤: %s", e)
            
            # 記錄到系統日誌
            if result == OperationResult.FAILED:
                logger.warning(
                    "操作失敗 - 用戶: %s, 操作: %s, 錯誤: %s",
                    user_id,
                    operation_name,
                    error_message
                )
            else:
                logger.info(
                    "操作記錄 - 用戶: %s, 操作: %s, 結果: %s",
                    user_id,
                    operation_name,
                    result.value
                )
            
            return operation_log.log_id
            
        except Exception as e:
            logger.error("記錄操作失敗: %s", e)
            raise OperationLogError("操作記錄失敗") from e

    def get_user_operations(
        self,
        user_id: str,
        operation_type: Optional[OperationType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        獲取用戶操作記錄
        
        Args:
            user_id: 用戶ID
            operation_type: 操作類型篩選
            start_time: 開始時間
            end_time: 結束時間
            limit: 限制數量
            
        Returns:
            List[Dict[str, Any]]: 操作記錄列表
        """
        filtered_logs = []
        
        for log in reversed(self._operation_logs):  # 最新的在前
            # 用戶篩選
            if log.user_id != user_id:
                continue
            
            # 操作類型篩選
            if operation_type and log.operation_type != operation_type:
                continue
            
            # 時間範圍篩選
            if start_time and log.timestamp < start_time:
                continue
            if end_time and log.timestamp > end_time:
                continue
            
            filtered_logs.append(log.to_dict())
            
            # 限制數量
            if len(filtered_logs) >= limit:
                break
        
        return filtered_logs

    def get_operation_statistics(
        self,
        user_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        獲取操作統計
        
        Args:
            user_id: 用戶ID，為 None 時統計所有用戶
            days: 統計天數
            
        Returns:
            Dict[str, Any]: 操作統計資訊
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            # 篩選記錄
            filtered_logs = []
            for log in self._operation_logs:
                if log.timestamp < cutoff_time:
                    continue
                if user_id and log.user_id != user_id:
                    continue
                filtered_logs.append(log)
            
            # 統計分析
            total_operations = len(filtered_logs)
            
            # 按操作類型統計
            by_type = {}
            for log in filtered_logs:
                op_type = log.operation_type.value
                by_type[op_type] = by_type.get(op_type, 0) + 1
            
            # 按結果統計
            by_result = {}
            for log in filtered_logs:
                result = log.result.value
                by_result[result] = by_result.get(result, 0) + 1
            
            # 按日期統計
            by_date = {}
            for log in filtered_logs:
                date_str = log.timestamp.strftime('%Y-%m-%d')
                by_date[date_str] = by_date.get(date_str, 0) + 1
            
            # 計算成功率
            success_count = by_result.get('success', 0)
            success_rate = (success_count / total_operations * 100) if total_operations > 0 else 0
            
            # 計算平均執行時間
            durations = [log.duration_ms for log in filtered_logs if log.duration_ms]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            return {
                "period_days": days,
                "total_operations": total_operations,
                "success_rate": round(success_rate, 2),
                "avg_duration_ms": round(avg_duration, 2),
                "by_operation_type": by_type,
                "by_result": by_result,
                "by_date": by_date,
                "user_id": user_id,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("獲取操作統計失敗: %s", e)
            raise OperationLogError("統計獲取失敗") from e

    def detect_anomalies(self, user_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """
        檢測異常操作
        
        Args:
            user_id: 用戶ID
            hours: 檢測時間範圍(小時)
            
        Returns:
            List[Dict[str, Any]]: 異常操作列表
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # 獲取用戶最近操作
            recent_logs = [
                log for log in self._operation_logs
                if log.user_id == user_id and log.timestamp >= cutoff_time
            ]
            
            anomalies = []
            
            # 檢測高頻操作
            operation_counts = {}
            for log in recent_logs:
                op_type = log.operation_type.value
                operation_counts[op_type] = operation_counts.get(op_type, 0) + 1
            
            for op_type, count in operation_counts.items():
                if count > 100:  # 閾值可調整
                    anomalies.append({
                        "type": "high_frequency",
                        "operation_type": op_type,
                        "count": count,
                        "threshold": 100,
                        "description": f"高頻操作: {op_type} 在 {hours} 小時內執行了 {count} 次"
                    })
            
            # 檢測連續失敗
            consecutive_failures = 0
            max_consecutive_failures = 0
            
            for log in sorted(recent_logs, key=lambda x: x.timestamp):
                if log.result == OperationResult.FAILED:
                    consecutive_failures += 1
                    max_consecutive_failures = max(max_consecutive_failures, consecutive_failures)
                else:
                    consecutive_failures = 0
            
            if max_consecutive_failures >= 5:  # 閾值可調整
                anomalies.append({
                    "type": "consecutive_failures",
                    "count": max_consecutive_failures,
                    "threshold": 5,
                    "description": f"連續失敗: 最多連續 {max_consecutive_failures} 次操作失敗"
                })
            
            # 檢測異常時間操作
            night_operations = [
                log for log in recent_logs
                if log.timestamp.hour < 6 or log.timestamp.hour > 23
            ]
            
            if len(night_operations) > 10:  # 閾值可調整
                anomalies.append({
                    "type": "unusual_hours",
                    "count": len(night_operations),
                    "threshold": 10,
                    "description": f"異常時間操作: 在深夜/凌晨時段執行了 {len(night_operations)} 次操作"
                })
            
            return anomalies
            
        except Exception as e:
            logger.error("檢測異常操作失敗: %s", e)
            return []

    def export_logs(
        self,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        format_type: str = "json"
    ) -> str:
        """
        匯出操作記錄
        
        Args:
            user_id: 用戶ID篩選
            start_time: 開始時間
            end_time: 結束時間
            format_type: 格式類型 (json/csv)
            
        Returns:
            str: 匯出的資料字串
            
        Raises:
            OperationLogError: 匯出失敗時拋出
        """
        try:
            # 篩選記錄
            filtered_logs = []
            for log in self._operation_logs:
                if user_id and log.user_id != user_id:
                    continue
                if start_time and log.timestamp < start_time:
                    continue
                if end_time and log.timestamp > end_time:
                    continue
                filtered_logs.append(log.to_dict())
            
            if format_type.lower() == "json":
                return json.dumps(filtered_logs, indent=2, ensure_ascii=False)
            elif format_type.lower() == "csv":
                # 簡化的 CSV 實作
                if not filtered_logs:
                    return ""
                
                headers = list(filtered_logs[0].keys())
                csv_lines = [",".join(headers)]
                
                for log in filtered_logs:
                    values = [str(log.get(header, "")) for header in headers]
                    csv_lines.append(",".join(values))
                
                return "\n".join(csv_lines)
            else:
                raise OperationLogError(f"不支援的格式: {format_type}")
                
        except Exception as e:
            logger.error("匯出操作記錄失敗: %s", e)
            raise OperationLogError("記錄匯出失敗") from e

    def add_log_callback(self, callback: Callable[[OperationLog], None]) -> None:
        """
        添加記錄回調函數
        
        Args:
            callback: 回調函數，接收操作記錄
        """
        self._log_callbacks.append(callback)

    def get_recent_errors(
        self,
        user_id: Optional[str] = None,
        hours: int = 24,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        獲取最近的錯誤記錄
        
        Args:
            user_id: 用戶ID篩選
            hours: 時間範圍(小時)
            limit: 限制數量
            
        Returns:
            List[Dict[str, Any]]: 錯誤記錄列表
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        error_logs = []
        for log in reversed(self._operation_logs):
            if log.timestamp < cutoff_time:
                break
            
            if user_id and log.user_id != user_id:
                continue
            
            if log.result == OperationResult.FAILED:
                error_logs.append(log.to_dict())
                
                if len(error_logs) >= limit:
                    break
        
        return error_logs

    def _cleanup_old_logs(self) -> None:
        """
        清理舊記錄
        
        根據最大記錄數量和保留天數清理舊的操作記錄。
        """
        try:
            # 按保留天數清理
            cutoff_time = datetime.now() - timedelta(days=self._retention_days)
            self._operation_logs = [
                log for log in self._operation_logs
                if log.timestamp >= cutoff_time
            ]
            
            # 按最大數量清理
            if len(self._operation_logs) > self._max_logs:
                # 保留最新的記錄
                self._operation_logs = self._operation_logs[-self._max_logs:]
                
        except Exception as e:
            logger.error("清理舊記錄失敗: %s", e)
