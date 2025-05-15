"""
日誌配置模組

此模組提供日誌系統的配置。
"""

import logging
import os
from typing import Any, Dict, List, Optional, Union

# 導入配置
from src.config import LOG_FORMAT, LOG_LEVEL, LOGS_DIR

# 導入格式化器和處理器
from src.logging.formatters import (
    EnhancedJsonFormatter,
    LogCategory,
    LogstashFormatter,
    LokiFormatter,
)
from src.logging.handlers import (
    ElasticsearchHandler,
    EnhancedRotatingFileHandler,
    LogstashHandler,
    LokiHandler,
)

# 定義常量
DEFAULT_LOG_LEVEL = getattr(logging, LOG_LEVEL, logging.INFO)
DEFAULT_LOG_FORMAT = LOG_FORMAT
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
DEFAULT_BACKUP_COUNT = 5
DEFAULT_ENCODING = "utf-8"

# 日誌目錄
LOG_DIRS = {
    LogCategory.SYSTEM: os.path.join(LOGS_DIR, "system"),
    LogCategory.DATA: os.path.join(LOGS_DIR, "data"),
    LogCategory.MODEL: os.path.join(LOGS_DIR, "model"),
    LogCategory.TRADE: os.path.join(LOGS_DIR, "trade"),
    LogCategory.ERROR: os.path.join(LOGS_DIR, "error"),
    LogCategory.SECURITY: os.path.join(LOGS_DIR, "security"),
    LogCategory.PERFORMANCE: os.path.join(LOGS_DIR, "performance"),
    LogCategory.API: os.path.join(LOGS_DIR, "api"),
    LogCategory.DATABASE: os.path.join(LOGS_DIR, "database"),
    LogCategory.NETWORK: os.path.join(LOGS_DIR, "network"),
    LogCategory.USER: os.path.join(LOGS_DIR, "user"),
    LogCategory.AUDIT: os.path.join(LOGS_DIR, "audit"),
}

# 確保日誌目錄存在
for log_dir in LOG_DIRS.values():
    os.makedirs(log_dir, exist_ok=True)

# ELK配置
ELK_CONFIG = {
    "enabled": os.getenv("ELK_ENABLED", "False").lower() == "true",
    "elasticsearch_url": os.getenv("ELASTICSEARCH_URL", "http://localhost:9200"),
    "elasticsearch_index": os.getenv("ELASTICSEARCH_INDEX", "trading-logs"),
    "elasticsearch_auth": None,  # 格式為(username, password)
    "logstash_url": os.getenv("LOGSTASH_URL", "http://localhost:5044"),
    "kibana_url": os.getenv("KIBANA_URL", "http://localhost:5601"),
}

# Loki配置
LOKI_CONFIG = {
    "enabled": os.getenv("LOKI_ENABLED", "False").lower() == "true",
    "loki_url": os.getenv("LOKI_URL", "http://localhost:3100/loki/api/v1/push"),
    "batch_size": int(os.getenv("LOKI_BATCH_SIZE", "100")),
    "batch_interval": float(os.getenv("LOKI_BATCH_INTERVAL", "1.0")),
}

# 應用配置
APP_CONFIG = {
    "name": os.getenv("APP_NAME", "trading_system"),
    "version": os.getenv("APP_VERSION", "1.0.0"),
    "environment": os.getenv("APP_ENVIRONMENT", "production"),
}


def get_logger(
    name: str,
    level: int = DEFAULT_LOG_LEVEL,
    log_file: Optional[str] = None,
    category: Optional[str] = None,
    use_json: bool = True,
    use_elk: Optional[bool] = None,
    use_loki: Optional[bool] = None,
    include_stack_info: bool = False,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    compress: bool = True,
) -> logging.Logger:
    """
    獲取日誌記錄器

    Args:
        name: 日誌記錄器名稱
        level: 日誌級別
        log_file: 日誌文件路徑
        category: 日誌類別
        use_json: 是否使用JSON格式
        use_elk: 是否使用ELK
        use_loki: 是否使用Loki
        include_stack_info: 是否包含堆棧信息
        max_bytes: 最大字節數
        backup_count: 備份數量
        compress: 是否壓縮

    Returns:
        logging.Logger: 日誌記錄器
    """
    # 獲取日誌記錄器
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 清除現有處理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 推斷類別
    if category is None:
        if "system" in name.lower():
            category = LogCategory.SYSTEM
        elif "data" in name.lower():
            category = LogCategory.DATA
        elif "model" in name.lower():
            category = LogCategory.MODEL
        elif "trade" in name.lower():
            category = LogCategory.TRADE
        elif "error" in name.lower():
            category = LogCategory.ERROR
        elif "security" in name.lower() or "audit" in name.lower():
            category = LogCategory.SECURITY
        elif "performance" in name.lower():
            category = LogCategory.PERFORMANCE
        elif "api" in name.lower():
            category = LogCategory.API
        elif "database" in name.lower() or "db" in name.lower():
            category = LogCategory.DATABASE
        elif "network" in name.lower():
            category = LogCategory.NETWORK
        elif "user" in name.lower():
            category = LogCategory.USER
        else:
            category = LogCategory.SYSTEM

    # 設置日誌文件
    if log_file is None:
        log_dir = LOG_DIRS.get(category, LOGS_DIR)
        log_file = os.path.join(log_dir, f"{name}.log")

    # 創建控制台處理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # 創建文件處理器
    file_handler = EnhancedRotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding=DEFAULT_ENCODING,
        compress=compress,
    )
    file_handler.setLevel(level)

    # 設置格式化器
    if use_json:
        formatter = EnhancedJsonFormatter(include_stack_info=include_stack_info)
    else:
        formatter = logging.Formatter(DEFAULT_LOG_FORMAT)

    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # 添加處理器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # 添加ELK處理器
    if (use_elk is None and ELK_CONFIG["enabled"]) or use_elk:
        # 創建Logstash處理器
        logstash_handler = LogstashHandler(
            host=ELK_CONFIG["logstash_url"],
            level=level,
        )
        logstash_formatter = LogstashFormatter(
            include_stack_info=include_stack_info,
            app_name=APP_CONFIG["name"],
            app_version=APP_CONFIG["version"],
        )
        logstash_handler.setFormatter(logstash_formatter)
        logger.addHandler(logstash_handler)

        # 創建Elasticsearch處理器
        elasticsearch_handler = ElasticsearchHandler(
            host=ELK_CONFIG["elasticsearch_url"],
            index_name=ELK_CONFIG["elasticsearch_index"],
            level=level,
            auth=ELK_CONFIG["elasticsearch_auth"],
        )
        elasticsearch_handler.setFormatter(formatter)
        logger.addHandler(elasticsearch_handler)

    # 添加Loki處理器
    if (use_loki is None and LOKI_CONFIG["enabled"]) or use_loki:
        loki_handler = LokiHandler(
            host=LOKI_CONFIG["loki_url"],
            level=level,
            batch_size=LOKI_CONFIG["batch_size"],
            batch_interval=LOKI_CONFIG["batch_interval"],
        )
        loki_formatter = LokiFormatter(
            include_stack_info=include_stack_info,
            labels={
                "app": APP_CONFIG["name"],
                "environment": APP_CONFIG["environment"],
                "category": category,
            },
        )
        loki_handler.setFormatter(loki_formatter)
        logger.addHandler(loki_handler)

    return logger


def log_with_context(
    logger: logging.Logger,
    level: int,
    msg: str,
    category: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
    context: Optional[Dict[str, Any]] = None,
    request: Optional[Dict[str, Any]] = None,
    response: Optional[Dict[str, Any]] = None,
    user: Optional[Dict[str, Any]] = None,
    performance: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    exc_info: Optional[Union[bool, BaseException, tuple]] = None,
) -> None:
    """
    記錄帶有上下文的日誌

    Args:
        logger: 日誌記錄器
        level: 日誌級別
        msg: 日誌消息
        category: 日誌類別
        data: 數據
        tags: 標籤
        context: 上下文
        request: 請求信息
        response: 響應信息
        user: 用戶信息
        performance: 性能指標
        metadata: 元數據
        exc_info: 異常信息
    """
    # 創建自定義記錄
    record = logging.LogRecord(
        name=logger.name,
        level=level,
        pathname=logger.findCaller()[0],
        lineno=logger.findCaller()[1],
        msg=msg,
        args=(),
        exc_info=exc_info,
    )

    # 添加額外數據
    if category:
        record.category = category
    if data:
        record.data = data
    if tags:
        record.tags = tags
    if context:
        record.context = context
    if request:
        record.request = request
    if response:
        record.response = response
    if user:
        record.user = user
    if performance:
        record.performance = performance
    if metadata:
        record.metadata = metadata

    # 處理記錄
    for handler in logger.handlers:
        if record.levelno >= handler.level:
            handler.handle(record)


# 創建主日誌記錄器
logger = get_logger("trading_system", log_file=os.path.join(LOGS_DIR, "trading.log"))

# 創建類別日誌記錄器
system_logger = get_logger(
    "system",
    category=LogCategory.SYSTEM,
    log_file=os.path.join(LOG_DIRS[LogCategory.SYSTEM], "system.log"),
)
data_logger = get_logger(
    "data",
    category=LogCategory.DATA,
    log_file=os.path.join(LOG_DIRS[LogCategory.DATA], "data.log"),
)
model_logger = get_logger(
    "model",
    category=LogCategory.MODEL,
    log_file=os.path.join(LOG_DIRS[LogCategory.MODEL], "model.log"),
)
trade_logger = get_logger(
    "trade",
    category=LogCategory.TRADE,
    log_file=os.path.join(LOG_DIRS[LogCategory.TRADE], "trade.log"),
)
error_logger = get_logger(
    "error",
    category=LogCategory.ERROR,
    log_file=os.path.join(LOG_DIRS[LogCategory.ERROR], "error.log"),
)
security_logger = get_logger(
    "security",
    category=LogCategory.SECURITY,
    log_file=os.path.join(LOG_DIRS[LogCategory.SECURITY], "security.log"),
)
performance_logger = get_logger(
    "performance",
    category=LogCategory.PERFORMANCE,
    log_file=os.path.join(LOG_DIRS[LogCategory.PERFORMANCE], "performance.log"),
)
api_logger = get_logger(
    "api",
    category=LogCategory.API,
    log_file=os.path.join(LOG_DIRS[LogCategory.API], "api.log"),
)
database_logger = get_logger(
    "database",
    category=LogCategory.DATABASE,
    log_file=os.path.join(LOG_DIRS[LogCategory.DATABASE], "database.log"),
)
network_logger = get_logger(
    "network",
    category=LogCategory.NETWORK,
    log_file=os.path.join(LOG_DIRS[LogCategory.NETWORK], "network.log"),
)
user_logger = get_logger(
    "user",
    category=LogCategory.USER,
    log_file=os.path.join(LOG_DIRS[LogCategory.USER], "user.log"),
)
audit_logger = get_logger(
    "audit",
    category=LogCategory.AUDIT,
    log_file=os.path.join(LOG_DIRS[LogCategory.AUDIT], "audit.log"),
)
