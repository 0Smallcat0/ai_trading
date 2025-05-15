"""
日誌格式化器模組

此模組提供各種日誌格式化器，用於格式化日誌記錄。
"""

import json
import logging
import socket
import sys
import traceback
import uuid
from datetime import datetime
from typing import Any, Dict, Optional


# 定義日誌類別
class LogCategory:
    """日誌類別"""

    SYSTEM = "system"  # 系統操作
    DATA = "data"  # 數據處理
    MODEL = "model"  # 模型推理
    TRADE = "trade"  # 交易執行
    ERROR = "error"  # 錯誤
    SECURITY = "security"  # 安全審計
    PERFORMANCE = "performance"  # 性能
    API = "api"  # API
    DATABASE = "database"  # 數據庫
    NETWORK = "network"  # 網絡
    USER = "user"  # 用戶操作
    AUDIT = "audit"  # 審計


class EnhancedJsonFormatter(logging.Formatter):
    """增強的JSON格式化器"""

    def __init__(
        self,
        fmt_dict: Optional[Dict[str, Any]] = None,
        time_format: str = "%Y-%m-%dT%H:%M:%S.%fZ",
        include_stack_info: bool = False,
    ):
        """
        初始化格式化器

        Args:
            fmt_dict: 格式字典
            time_format: 時間格式
            include_stack_info: 是否包含堆棧信息
        """
        super().__init__()
        self.fmt_dict = fmt_dict or {
            "timestamp": "%(asctime)s",
            "level": "%(levelname)s",
            "logger": "%(name)s",
            "message": "%(message)s",
            "module": "%(module)s",
            "function": "%(funcName)s",
            "line": "%(lineno)d",
            "thread": "%(threadName)s",
            "process": "%(process)d",
        }
        self.time_format = time_format
        self.hostname = socket.gethostname()
        self.include_stack_info = include_stack_info

    def format(self, record: logging.LogRecord) -> str:
        """
        格式化記錄

        Args:
            record: 日誌記錄

        Returns:
            str: 格式化後的記錄
        """
        # 創建記錄字典
        record_dict = self.fmt_dict.copy()

        # 格式化時間
        record.asctime = datetime.fromtimestamp(record.created).strftime(
            self.time_format
        )

        # 填充記錄字典
        for key, value in record_dict.items():
            if (
                isinstance(value, str)
                and value.startswith("%(")
                and value.endswith(")s")
            ):
                attr_name = value[2:-2]
                if hasattr(record, attr_name):
                    record_dict[key] = getattr(record, attr_name)

        # 添加異常信息
        if record.exc_info:
            record_dict["exception"] = {
                "type": str(record.exc_info[0].__name__),
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # 添加堆棧信息
        if self.include_stack_info and record.stack_info:
            record_dict["stack_info"] = record.stack_info

        # 添加額外數據
        if hasattr(record, "data") and record.data:
            record_dict["data"] = record.data

        # 添加日誌類別
        if hasattr(record, "category"):
            record_dict["category"] = record.category
        else:
            # 根據記錄器名稱推斷類別
            if "trade" in record.name.lower():
                record_dict["category"] = LogCategory.TRADE
            elif "model" in record.name.lower():
                record_dict["category"] = LogCategory.MODEL
            elif "data" in record.name.lower():
                record_dict["category"] = LogCategory.DATA
            elif "error" in record.name.lower():
                record_dict["category"] = LogCategory.ERROR
            elif "security" in record.name.lower() or "audit" in record.name.lower():
                record_dict["category"] = LogCategory.SECURITY
            else:
                record_dict["category"] = LogCategory.SYSTEM

        # 添加主機名
        record_dict["hostname"] = self.hostname

        # 添加唯一ID
        record_dict["id"] = str(uuid.uuid4())

        # 添加環境信息
        record_dict["environment"] = {
            "python_version": sys.version,
            "platform": sys.platform,
        }

        # 添加標籤
        if hasattr(record, "tags") and record.tags:
            record_dict["tags"] = record.tags

        # 添加上下文
        if hasattr(record, "context") and record.context:
            record_dict["context"] = record.context

        # 添加請求信息
        if hasattr(record, "request") and record.request:
            record_dict["request"] = record.request

        # 添加響應信息
        if hasattr(record, "response") and record.response:
            record_dict["response"] = record.response

        # 添加用戶信息
        if hasattr(record, "user") and record.user:
            record_dict["user"] = record.user

        # 添加性能指標
        if hasattr(record, "performance") and record.performance:
            record_dict["performance"] = record.performance

        # 添加元數據
        if hasattr(record, "metadata") and record.metadata:
            record_dict["metadata"] = record.metadata

        # 添加時間戳（毫秒）
        record_dict["timestamp_ms"] = int(record.created * 1000)

        return json.dumps(record_dict, ensure_ascii=False)


class LogstashFormatter(EnhancedJsonFormatter):
    """Logstash格式化器"""

    def __init__(
        self,
        fmt_dict: Optional[Dict[str, Any]] = None,
        time_format: str = "%Y-%m-%dT%H:%M:%S.%fZ",
        include_stack_info: bool = False,
        app_name: str = "trading_system",
        app_version: str = "1.0.0",
    ):
        """
        初始化格式化器

        Args:
            fmt_dict: 格式字典
            time_format: 時間格式
            include_stack_info: 是否包含堆棧信息
            app_name: 應用名稱
            app_version: 應用版本
        """
        super().__init__(fmt_dict, time_format, include_stack_info)
        self.app_name = app_name
        self.app_version = app_version

    def format(self, record: logging.LogRecord) -> str:
        """
        格式化記錄

        Args:
            record: 日誌記錄

        Returns:
            str: 格式化後的記錄
        """
        # 獲取基本格式化記錄
        formatted_record = json.loads(super().format(record))

        # 添加Logstash特定字段
        formatted_record["@timestamp"] = formatted_record.pop("timestamp")
        formatted_record["@version"] = "1"
        formatted_record["app"] = {
            "name": self.app_name,
            "version": self.app_version,
        }

        # 重命名字段以符合ELK約定
        if "level" in formatted_record:
            formatted_record["log_level"] = formatted_record.pop("level")

        if "logger" in formatted_record:
            formatted_record["logger_name"] = formatted_record.pop("logger")

        return json.dumps(formatted_record, ensure_ascii=False)


class LokiFormatter(EnhancedJsonFormatter):
    """Loki格式化器"""

    def __init__(
        self,
        fmt_dict: Optional[Dict[str, Any]] = None,
        time_format: str = "%Y-%m-%dT%H:%M:%S.%fZ",
        include_stack_info: bool = False,
        labels: Optional[Dict[str, str]] = None,
    ):
        """
        初始化格式化器

        Args:
            fmt_dict: 格式字典
            time_format: 時間格式
            include_stack_info: 是否包含堆棧信息
            labels: 標籤
        """
        super().__init__(fmt_dict, time_format, include_stack_info)
        self.labels = labels or {
            "app": "trading_system",
            "environment": "production",
        }

    def format(self, record: logging.LogRecord) -> str:
        """
        格式化記錄

        Args:
            record: 日誌記錄

        Returns:
            str: 格式化後的記錄
        """
        # 獲取基本格式化記錄
        formatted_record = json.loads(super().format(record))

        # 添加Loki特定字段
        loki_record = {
            "streams": [
                {
                    "stream": self.get_labels(record),
                    "values": [
                        [str(int(record.created * 1e9)), json.dumps(formatted_record)]
                    ],
                }
            ]
        }

        return json.dumps(loki_record, ensure_ascii=False)

    def get_labels(self, record: logging.LogRecord) -> Dict[str, str]:
        """
        獲取標籤

        Args:
            record: 日誌記錄

        Returns:
            Dict[str, str]: 標籤
        """
        labels = self.labels.copy()

        # 添加記錄特定標籤
        labels["level"] = record.levelname
        labels["logger"] = record.name

        # 添加類別標籤
        if hasattr(record, "category"):
            labels["category"] = record.category
        elif "category" in getattr(record, "data", {}):
            labels["category"] = record.data["category"]

        # 添加自定義標籤
        if hasattr(record, "tags") and isinstance(record.tags, dict):
            for key, value in record.tags.items():
                if isinstance(value, str):
                    labels[key] = value

        return labels
