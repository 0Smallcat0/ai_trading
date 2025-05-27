"""環境配置管理模組.

此模組負責載入和管理不同環境的配置設定。
支援開發、測試、生產三種環境，並提供配置驗證功能。
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Config:
    """配置類別，包含所有環境變數設定."""

    # 基本環境設定
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 應用設定
    APP_NAME: str = "ai_trading_system"
    APP_VERSION: str = "1.0.0"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8501

    # 資料庫設定
    DATABASE_URL: str = "sqlite:///data/market_data.db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False

    # SQLite 設定
    SQLITE_DB_PATH: str = "data/market_data.db"
    MARKET_INFO_DB: str = "data/market_info.db"

    # Redis 設定
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_MAX_CONNECTIONS: int = 10

    # API 設定
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    API_WORKERS: int = 1
    API_RELOAD: bool = True
    API_PREFIX: str = "/api/v1"

    # JWT 設定
    JWT_SECRET_KEY: str = "your-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS 設定
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8501"
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: str = "GET,POST,PUT,DELETE,OPTIONS"
    CORS_ALLOW_HEADERS: str = "*"

    # 速率限制
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10

    # 外部 API 金鑰
    TWSE_API_KEY: str = ""
    TPEX_API_KEY: str = ""
    YAHOO_FINANCE_API_KEY: str = ""
    ALPHA_VANTAGE_API_KEY: str = ""
    FINNHUB_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    HUGGINGFACE_API_KEY: str = ""

    # 交易設定
    TRADING_HOURS_START: str = "09:00:00"
    TRADING_HOURS_END: str = "13:30:00"
    TRADING_TIMEZONE: str = "Asia/Taipei"
    MAX_POSITION_SIZE: float = 0.2
    STOP_LOSS_THRESHOLD: float = 0.05
    MAX_DAILY_LOSS: float = 5000.0
    RISK_FREE_RATE: float = 0.02

    # 券商設定
    BROKER_NAME: str = "simulator"
    BROKER_API_KEY: str = ""
    BROKER_SECRET_KEY: str = ""
    BROKER_ENVIRONMENT: str = "sandbox"

    # 爬蟲設定
    REQUEST_TIMEOUT: int = 30
    RETRY_COUNT: int = 3
    RETRY_DELAY: float = 1.0
    USER_AGENT: str = "Mozilla/5.0 (Trading System)"

    # 監控設定
    MONITORING_ENABLED: bool = True
    MONITORING_INTERVAL: int = 60
    HEALTH_CHECK_INTERVAL: int = 30
    PRICE_ANOMALY_THRESHOLD: float = 0.05
    VOLUME_ANOMALY_THRESHOLD: float = 3.0
    PERFORMANCE_THRESHOLD: int = 100

    # Prometheus 設定
    PROMETHEUS_HOST: str = "localhost"
    PROMETHEUS_PORT: int = 9090
    PROMETHEUS_METRICS_PATH: str = "/metrics"

    # Grafana 設定
    GRAFANA_HOST: str = "localhost"
    GRAFANA_PORT: int = 3000
    GRAFANA_USERNAME: str = "admin"
    GRAFANA_PASSWORD: str = "admin"

    # 通知設定
    ALERT_ENABLED: bool = True
    ALERT_LOG_DIR: str = "logs/alerts"
    ALERT_CHECK_INTERVAL: int = 60

    # 電子郵件設定
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    ALERT_EMAIL_FROM: str = "alerts@example.com"
    ALERT_EMAIL_TO: str = "admin@example.com"

    # 通知服務
    LINE_NOTIFY_TOKEN: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # 安全設定
    ENCRYPTION_KEY: str = ""
    FERNET_KEY: str = ""
    SESSION_SECRET_KEY: str = ""
    SESSION_TIMEOUT: int = 3600

    # 檔案儲存
    UPLOAD_DIR: str = "uploads"
    DATA_DIR: str = "data"
    LOG_DIR: str = "logs"
    BACKUP_DIR: str = "backups"
    MAX_FILE_SIZE: str = "10MB"

    # AWS S3 設定
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-west-2"
    S3_BUCKET_NAME: str = ""

    # 快取設定
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 3600
    CACHE_MAX_SIZE: int = 1000
    CACHE_CLEANUP_INTERVAL: int = 300

    # 測試設定
    TEST_DATABASE_URL: str = ""
    TEST_REDIS_URL: str = ""
    TEST_MODE: bool = False
    MOCK_EXTERNAL_APIS: bool = False
    TEST_DATA_PATH: str = "tests/data"

    # 開發工具
    PYLINT_THRESHOLD: float = 8.5
    FLAKE8_MAX_LINE_LENGTH: int = 88
    COVERAGE_THRESHOLD: int = 80
    PERFORMANCE_MONITORING: bool = True
    MEMORY_PROFILING: bool = False
    PROFILING_OUTPUT_DIR: str = "profiling"
    DEBUG_MODE: bool = False
    VERBOSE_LOGGING: bool = False
    SQL_ECHO: bool = False

    # 其他設定
    TIMEZONE: str = "Asia/Taipei"
    DATE_FORMAT: str = "%Y-%m-%d"
    DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    LANGUAGE: str = "zh-TW"
    LOCALE: str = "zh_TW.UTF-8"

    def __post_init__(self):
        """初始化後處理，進行類型轉換和驗證."""
        self._convert_types()
        self._validate_config()

    def _convert_types(self):
        """轉換環境變數的類型."""
        # 布林值轉換
        bool_fields = [
            'DEBUG', 'DATABASE_ECHO', 'API_RELOAD', 'CORS_ALLOW_CREDENTIALS',
            'SMTP_USE_TLS', 'MONITORING_ENABLED', 'ALERT_ENABLED',
            'CACHE_ENABLED', 'TEST_MODE', 'MOCK_EXTERNAL_APIS',
            'PERFORMANCE_MONITORING', 'MEMORY_PROFILING', 'DEBUG_MODE',
            'VERBOSE_LOGGING', 'SQL_ECHO'
        ]

        for field_name in bool_fields:
            value = getattr(self, field_name)
            if isinstance(value, str):
                setattr(self, field_name,
                        value.lower() in ('true', '1', 'yes', 'on'))

        # 數值轉換
        int_fields = [
            'APP_PORT', 'DATABASE_POOL_SIZE', 'DATABASE_MAX_OVERFLOW',
            'REDIS_DB', 'REDIS_MAX_CONNECTIONS', 'API_PORT', 'API_WORKERS',
            'JWT_ACCESS_TOKEN_EXPIRE_MINUTES', 'JWT_REFRESH_TOKEN_EXPIRE_DAYS',
            'RATE_LIMIT_PER_MINUTE', 'RATE_LIMIT_BURST', 'REQUEST_TIMEOUT',
            'RETRY_COUNT', 'MONITORING_INTERVAL', 'HEALTH_CHECK_INTERVAL',
            'PERFORMANCE_THRESHOLD', 'PROMETHEUS_PORT', 'GRAFANA_PORT',
            'ALERT_CHECK_INTERVAL', 'SMTP_PORT', 'SESSION_TIMEOUT',
            'CACHE_TTL', 'CACHE_MAX_SIZE', 'CACHE_CLEANUP_INTERVAL',
            'FLAKE8_MAX_LINE_LENGTH', 'COVERAGE_THRESHOLD'
        ]

        for field_name in int_fields:
            value = getattr(self, field_name)
            if isinstance(value, str) and str(value).isdigit():
                setattr(self, field_name, int(value))

        # 浮點數轉換
        float_fields = [
            'MAX_POSITION_SIZE', 'STOP_LOSS_THRESHOLD', 'MAX_DAILY_LOSS',
            'RISK_FREE_RATE', 'RETRY_DELAY', 'PRICE_ANOMALY_THRESHOLD',
            'VOLUME_ANOMALY_THRESHOLD', 'PYLINT_THRESHOLD'
        ]

        for field_name in float_fields:
            value = getattr(self, field_name)
            if isinstance(value, str):
                try:
                    setattr(self, field_name, float(value))
                except ValueError:
                    pass

    def _validate_config(self):
        """驗證配置的有效性."""
        errors = []

        # 驗證環境
        valid_envs = ['development', 'testing', 'production']
        if self.ENVIRONMENT not in valid_envs:
            errors.append(f"Invalid ENVIRONMENT: {self.ENVIRONMENT}")

        # 驗證埠號
        if not 1 <= self.APP_PORT <= 65535:
            errors.append(f"Invalid APP_PORT: {self.APP_PORT}")

        if not 1 <= self.API_PORT <= 65535:
            errors.append(f"Invalid API_PORT: {self.API_PORT}")

        # 驗證風險管理參數
        if not 0 < self.MAX_POSITION_SIZE <= 1:
            errors.append(f"Invalid MAX_POSITION_SIZE: {self.MAX_POSITION_SIZE}")

        if not 0 < self.STOP_LOSS_THRESHOLD <= 1:
            errors.append(
                f"Invalid STOP_LOSS_THRESHOLD: {self.STOP_LOSS_THRESHOLD}")

        # 生產環境額外驗證
        if self.ENVIRONMENT == 'production':
            insecure_keys = ['your-secret-key',
                             'dev-jwt-secret-key-not-for-production']
            if self.JWT_SECRET_KEY in insecure_keys:
                errors.append(
                    "Production environment requires a secure JWT_SECRET_KEY")

            if self.DEBUG:
                errors.append("DEBUG should be False in production")

        if errors:
            error_msg = f"Configuration validation failed: {'; '.join(errors)}"
            raise ValueError(error_msg)

    @property
    def cors_origins_list(self) -> list:
        """將 CORS_ORIGINS 字串轉換為列表."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(',')
                if origin.strip()]

    @property
    def is_development(self) -> bool:
        """是否為開發環境."""
        return self.ENVIRONMENT == 'development'

    @property
    def is_testing(self) -> bool:
        """是否為測試環境."""
        return self.ENVIRONMENT == 'testing'

    @property
    def is_production(self) -> bool:
        """是否為生產環境."""
        return self.ENVIRONMENT == 'production'


def load_environment_config(env: Optional[str] = None) -> Config:
    """載入環境配置.

    Args:
        env: 環境名稱 ('development', 'testing', 'production')
             如果為 None，則從 ENVIRONMENT 環境變數讀取

    Returns:
        Config: 配置物件
    """
    # 確定環境
    if env is None:
        env = os.getenv('ENVIRONMENT', 'development')

    # 專案根目錄
    project_root = Path(__file__).parent.parent

    # 載入對應的 .env 檔案
    env_file = project_root / f".env.{env}"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded configuration from {env_file}")
    else:
        # 嘗試載入通用 .env 檔案
        default_env_file = project_root / ".env"
        if default_env_file.exists():
            load_dotenv(default_env_file)
            print(f"Loaded configuration from {default_env_file}")
        else:
            print("No .env file found, using default configuration")

    # 創建配置物件
    config_data = {}
    # 使用 __annotations__ 替代 __dataclass_fields__
    for field_name in Config.__annotations__:
        env_value = os.getenv(field_name)
        if env_value is not None:
            config_data[field_name] = env_value

    return Config(**config_data)


# 全域配置實例
_config: Optional[Config] = None


def get_config(env: Optional[str] = None, reload: bool = False) -> Config:
    """獲取配置實例（單例模式）.

    Args:
        env: 環境名稱
        reload: 是否重新載入配置

    Returns:
        Config: 配置物件
    """
    global _config

    if _config is None or reload:
        _config = load_environment_config(env)

    return _config


def set_config(config: Config):
    """設定配置實例（主要用於測試）.

    Args:
        config: 配置物件
    """
    global _config
    _config = config
