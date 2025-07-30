"""日誌中間件

此模組實現了 API 請求日誌記錄功能，提供完整的請求追蹤和審計功能。
包含請求日誌、響應日誌、效能監控、錯誤追蹤等功能。
"""

import time
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging

# 導入敏感資料遮罩功能
from src.log_system.data_masking import mask_sensitive_data

# 設定日誌格式
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """日誌中間件"""

    def __init__(self, app):
        super().__init__(app)

        # 不記錄日誌的路徑
        self.skip_paths = {
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
        }

        # 敏感資料欄位（需要遮罩）
        self.sensitive_fields = {
            "password",
            "token",
            "secret",
            "key",
            "authorization",
            "cookie",
        }

    async def dispatch(self, request: Request, call_next):
        """處理請求日誌記錄"""
        # 生成請求 ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # 檢查是否需要跳過日誌記錄
        if request.url.path in self.skip_paths:
            return await call_next(request)

        # 記錄請求開始時間
        start_time = time.time()

        # 記錄請求資訊
        await self._log_request(request, request_id)

        # 處理請求
        try:
            response = await call_next(request)

            # 計算處理時間
            process_time = time.time() - start_time

            # 記錄響應資訊
            await self._log_response(request, response, request_id, process_time)

            # 添加請求 ID 到響應標頭
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.4f}"

            return response

        except Exception as e:
            # 計算處理時間
            process_time = time.time() - start_time

            # 記錄錯誤
            await self._log_error(request, e, request_id, process_time)

            # 重新拋出異常
            raise

    async def _log_request(self, request: Request, request_id: str):
        """記錄請求資訊"""
        try:
            # 獲取請求基本資訊
            request_data = {
                "request_id": request_id,
                "timestamp": datetime.now().isoformat(),
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "headers": self._mask_sensitive_data(dict(request.headers)),
                "client_ip": self._get_client_ip(request),
                "user_agent": request.headers.get("user-agent", ""),
                "content_type": request.headers.get("content-type", ""),
                "content_length": request.headers.get("content-length", 0),
            }

            # 獲取用戶資訊（如果已認證）
            if hasattr(request.state, "user_id"):
                request_data["user_id"] = request.state.user_id
                request_data["username"] = getattr(request.state, "username", "")
                request_data["user_role"] = getattr(request.state, "role", "")

            # 記錄請求體（僅對特定方法和內容類型）
            if request.method in ["POST", "PUT", "PATCH"]:
                request_data["body"] = await self._get_request_body(request)

            # 記錄日誌
            logger.info(
                "API請求: %s", json.dumps(request_data, ensure_ascii=False, default=str)
            )

        except Exception as e:
            logger.error("記錄請求日誌失敗: %s", e)

    async def _log_response(
        self, request: Request, response: Response, request_id: str, process_time: float
    ):
        """記錄響應資訊"""
        try:
            response_data = {
                "request_id": request_id,
                "timestamp": datetime.now().isoformat(),
                "status_code": response.status_code,
                "process_time": round(process_time, 4),
                "response_headers": self._mask_sensitive_data(dict(response.headers)),
                "content_type": response.headers.get("content-type", ""),
                "content_length": response.headers.get("content-length", 0),
            }

            # 記錄響應體（僅對錯誤響應或特定狀態碼）
            if response.status_code >= 400:
                response_data["response_body"] = await self._get_response_body(response)

            # 根據狀態碼選擇日誌等級
            if response.status_code >= 500:
                logger.error(
                    "API響應: %s",
                    json.dumps(response_data, ensure_ascii=False, default=str),
                )
            elif response.status_code >= 400:
                logger.warning(
                    "API響應: %s",
                    json.dumps(response_data, ensure_ascii=False, default=str),
                )
            else:
                logger.info(
                    "API響應: %s",
                    json.dumps(response_data, ensure_ascii=False, default=str),
                )

            # 記錄效能指標
            self._log_performance_metrics(request, response, process_time)

        except Exception as e:
            logger.error("記錄響應日誌失敗: %s", e)

    async def _log_error(
        self, request: Request, error: Exception, request_id: str, process_time: float
    ):
        """記錄錯誤資訊"""
        try:
            error_data = {
                "request_id": request_id,
                "timestamp": datetime.now().isoformat(),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "process_time": round(process_time, 4),
                "method": request.method,
                "url": str(request.url),
                "client_ip": self._get_client_ip(request),
                "user_agent": request.headers.get("user-agent", ""),
            }

            # 添加用戶資訊
            if hasattr(request.state, "user_id"):
                error_data["user_id"] = request.state.user_id
                error_data["username"] = getattr(request.state, "username", "")

            logger.error(
                "API錯誤: %s", json.dumps(error_data, ensure_ascii=False, default=str)
            )

        except Exception as e:
            logger.error("記錄錯誤日誌失敗: %s", e)

    def _get_client_ip(self, request: Request) -> str:
        """獲取客戶端 IP"""
        # 檢查代理標頭
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    async def _get_request_body(self, request: Request) -> Optional[Dict[str, Any]]:
        """獲取請求體"""
        try:
            content_type = request.headers.get("content-type", "")

            if "application/json" in content_type:
                # 讀取 JSON 請求體
                body = await request.body()
                if body:
                    json_data = json.loads(body.decode())
                    return self._mask_sensitive_data(json_data)

            elif "application/x-www-form-urlencoded" in content_type:
                # 讀取表單資料
                form_data = await request.form()
                return self._mask_sensitive_data(dict(form_data))

            elif "multipart/form-data" in content_type:
                # 處理檔案上傳
                return {
                    "content_type": "multipart/form-data",
                    "note": "檔案上傳內容已省略",
                }

            else:
                return {"content_type": content_type, "note": "非 JSON 內容已省略"}

        except Exception as e:
            logger.warning("讀取請求體失敗: %s", e)
            return {"error": "無法讀取請求體"}

    async def _get_response_body(self, response: Response) -> Optional[Dict[str, Any]]:
        """獲取響應體

        Args:
            response: HTTP 響應物件

        Returns:
            Optional[Dict[str, Any]]: 響應體資料或 None
        """
        try:
            # 注意：這裡只是示例，實際實現需要更複雜的處理
            # 因為響應體可能已經被消費
            return {"note": "響應體內容省略"}
        except Exception as e:
            logger.warning("讀取響應體失敗: %s", e)
            return {"error": "無法讀取響應體"}

    def _mask_sensitive_data(self, data: Any) -> Any:
        """遮罩敏感資料"""
        try:
            # 使用新的敏感資料遮罩功能
            return mask_sensitive_data(data, context="api_logging")
        except Exception as e:
            logger.error("敏感資料遮罩失敗: %s", e)
            # 回退到原有的簡單遮罩方法
            return self._simple_mask_sensitive_data(data)

    def _simple_mask_sensitive_data(self, data: Any) -> Any:
        """簡單的敏感資料遮罩（回退方法）"""
        if isinstance(data, dict):
            masked_data = {}
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                    masked_data[key] = "***MASKED***"
                else:
                    masked_data[key] = self._simple_mask_sensitive_data(value)
            return masked_data

        if isinstance(data, list):
            return [self._simple_mask_sensitive_data(item) for item in data]

        return data

    def _log_performance_metrics(
        self, request: Request, response: Response, process_time: float
    ):
        """記錄效能指標"""
        try:
            # 效能指標
            metrics = {
                "endpoint": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "process_time": process_time,
                "timestamp": datetime.now().isoformat(),
            }

            # 慢請求警告
            if process_time > 5.0:  # 超過 5 秒
                logger.warning(
                    "慢請求警告: %s", json.dumps(metrics, ensure_ascii=False)
                )
            elif process_time > 1.0:  # 超過 1 秒
                logger.info("效能監控: %s", json.dumps(metrics, ensure_ascii=False))

        except Exception as e:
            logger.error("記錄效能指標失敗: %s", e)


class AuditLogger:
    """審計日誌記錄器"""

    def __init__(self):
        self.audit_logger = logging.getLogger("audit")

        # 設定審計日誌處理器
        handler = logging.FileHandler("logs/audit.log", encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        self.audit_logger.addHandler(handler)
        self.audit_logger.setLevel(logging.INFO)

    def log_user_action(
        self,
        user_id: str,
        action: str,
        resource: str,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ):
        """記錄用戶操作

        Args:
            user_id: 用戶 ID
            action: 操作類型
            resource: 資源名稱
            details: 詳細資訊
            request_id: 請求 ID
        """
        audit_data = {
            "type": "user_action",
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "details": details or {},
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
        }

        self.audit_logger.info(json.dumps(audit_data, ensure_ascii=False, default=str))

    def log_system_event(
        self,
        event_type: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """記錄系統事件"""
        audit_data = {
            "type": "system_event",
            "event_type": event_type,
            "description": description,
            "details": details or {},
            "timestamp": datetime.now().isoformat(),
        }

        self.audit_logger.info(json.dumps(audit_data, ensure_ascii=False, default=str))

    def log_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """記錄安全事件

        Args:
            event_type: 事件類型
            severity: 嚴重程度
            description: 事件描述
            user_id: 用戶 ID
            details: 詳細資訊
        """
        audit_data = {
            "type": "security_event",
            "event_type": event_type,
            "severity": severity,
            "description": description,
            "user_id": user_id,
            "details": details or {},
            "timestamp": datetime.now().isoformat(),
        }

        # 根據嚴重程度選擇日誌等級
        if severity == "critical":
            self.audit_logger.critical(
                json.dumps(audit_data, ensure_ascii=False, default=str)
            )
        elif severity == "high":
            self.audit_logger.error(
                json.dumps(audit_data, ensure_ascii=False, default=str)
            )
        elif severity == "medium":
            self.audit_logger.warning(
                json.dumps(audit_data, ensure_ascii=False, default=str)
            )
        else:
            self.audit_logger.info(
                json.dumps(audit_data, ensure_ascii=False, default=str)
            )


# 全域審計日誌記錄器實例
audit_logger = AuditLogger()


class APIMetricsCollector:
    """指標收集器"""

    def __init__(self):
        self.metrics = {
            "request_count": 0,
            "error_count": 0,
            "total_process_time": 0.0,
            "endpoint_stats": {},
            "status_code_stats": {},
        }

    def record_request(
        self, endpoint: str, method: str, status_code: int, process_time: float
    ):
        """記錄請求指標"""
        self.metrics["request_count"] += 1
        self.metrics["total_process_time"] += process_time

        if status_code >= 400:
            self.metrics["error_count"] += 1

        # 端點統計
        endpoint_key = f"{method} {endpoint}"
        if endpoint_key not in self.metrics["endpoint_stats"]:
            self.metrics["endpoint_stats"][endpoint_key] = {
                "count": 0,
                "total_time": 0.0,
                "error_count": 0,
            }

        endpoint_stats = self.metrics["endpoint_stats"][endpoint_key]
        endpoint_stats["count"] += 1
        endpoint_stats["total_time"] += process_time

        if status_code >= 400:
            endpoint_stats["error_count"] += 1

        # 狀態碼統計
        if status_code not in self.metrics["status_code_stats"]:
            self.metrics["status_code_stats"][status_code] = 0
        self.metrics["status_code_stats"][status_code] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """獲取指標"""
        avg_process_time = (
            self.metrics["total_process_time"] / self.metrics["request_count"]
            if self.metrics["request_count"] > 0
            else 0
        )

        return {
            "request_count": self.metrics["request_count"],
            "error_count": self.metrics["error_count"],
            "error_rate": (
                self.metrics["error_count"] / self.metrics["request_count"]
                if self.metrics["request_count"] > 0
                else 0
            ),
            "average_process_time": round(avg_process_time, 4),
            "endpoint_stats": self.metrics["endpoint_stats"],
            "status_code_stats": self.metrics["status_code_stats"],
        }

    def reset_metrics(self):
        """重置指標"""
        self.metrics = {
            "request_count": 0,
            "error_count": 0,
            "total_process_time": 0.0,
            "endpoint_stats": {},
            "status_code_stats": {},
        }


# 全域指標收集器實例
metrics_collector = APIMetricsCollector()
