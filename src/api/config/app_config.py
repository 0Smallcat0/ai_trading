"""FastAPI 應用配置模組

此模組包含 FastAPI 應用的配置設定，包括中間件配置、
CORS 設定、OpenAPI 配置等。
"""

from typing import Dict, Any, List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.openapi.utils import get_openapi


def configure_cors(app: FastAPI) -> None:
    """配置 CORS 中間件

    Args:
        app: FastAPI 應用實例

    Note:
        配置跨域資源共享，允許前端應用訪問 API
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # React 開發伺服器
            "http://localhost:8501",  # Streamlit 應用
            "http://localhost:8502",  # Streamlit 備用端口
            "http://127.0.0.1:8501",
            "http://127.0.0.1:8502",
            "https://trading-system.com",  # 生產環境域名
            "https://*.trading-system.com",  # 子域名
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Rate-Limit-Remaining"],
    )


def configure_trusted_hosts(app: FastAPI) -> None:
    """配置信任主機中間件

    Args:
        app: FastAPI 應用實例

    Note:
        防止 Host header 攻擊
    """
    import os

    # 基本的受信任主機
    allowed_hosts = [
        "localhost",
        "127.0.0.1",
        "*.trading-system.com",
        "trading-system.com",
        "testserver",  # 總是允許測試服務器
        "test",
    ]

    # 如果是測試環境，允許所有主機
    if os.getenv("TESTING") == "true" or os.getenv("PYTEST_CURRENT_TEST"):
        allowed_hosts.append("*")

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=allowed_hosts,
    )


def configure_openapi(app: FastAPI) -> None:
    """配置 OpenAPI 文檔

    Args:
        app: FastAPI 應用實例

    Note:
        自定義 OpenAPI 規範，包括安全配置和標籤
    """
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title="AI 交易系統 API",
            version="1.0.0",
            description="""
            ## AI 交易系統 RESTful API

            這是一個完整的 AI 驅動交易系統 API，提供以下功能：

            ### 🔐 身份認證與授權
            - JWT Token 認證
            - RBAC 權限控制
            - 用戶管理

            ### 📊 資料管理
            - 市場資料獲取
            - 歷史資料查詢
            - 資料清理與處理

            ### 🎯 策略管理
            - 交易策略創建
            - 策略參數調整
            - 策略回測

            ### 🤖 AI 模型
            - 模型訓練與部署
            - 預測與推理
            - 模型版本管理

            ### 💼 投資組合管理
            - 持倉管理
            - 風險評估
            - 績效分析

            ### ⚡ 交易執行
            - 訂單管理
            - 實時交易
            - 交易歷史

            ### 📡 系統監控
            - 系統狀態監控
            - 性能指標
            - 告警管理

            ---

            **認證方式**: Bearer Token (JWT)
            **API 版本**: v1
            **速率限制**: 1000 requests/minute
            """,
            routes=app.routes,
        )

        # 添加安全配置
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT Token 認證，格式：Bearer <token>",
            }
        }

        # 設定全域安全要求
        openapi_schema["security"] = [{"BearerAuth": []}]

        # 添加標籤描述
        openapi_schema["tags"] = [
            {
                "name": "🔐 身份認證",
                "description": "用戶認證與授權相關操作",
            },
            {
                "name": "📊 資料管理",
                "description": "市場資料獲取、處理與管理",
            },
            {
                "name": "🎯 策略管理",
                "description": "交易策略創建、管理與優化",
            },
            {
                "name": "🤖 AI 模型",
                "description": "機器學習模型管理與預測",
            },
            {
                "name": "📈 回測系統",
                "description": "策略回測與性能評估",
            },
            {
                "name": "💼 投資組合",
                "description": "投資組合管理與風險控制",
            },
            {
                "name": "🛡️ 風險管理",
                "description": "風險評估與控制機制",
            },
            {
                "name": "⚡ 交易執行",
                "description": "訂單執行與交易管理",
            },
            {
                "name": "📡 系統監控",
                "description": "系統狀態監控與告警",
            },
            {
                "name": "📋 報表分析",
                "description": "數據分析與報表生成",
            },
            {
                "name": "⚙️ 系統管理",
                "description": "系統配置與管理功能",
            },
        ]

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi


def get_app_settings() -> Dict[str, Any]:
    """獲取應用設定

    Returns:
        Dict[str, Any]: 應用配置字典

    Note:
        包含應用的基本配置資訊
    """
    return {
        "title": "AI 交易系統 API",
        "version": "1.0.0",
        "description": "AI 驅動的智能交易系統 RESTful API",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json",
        "debug": False,  # 生產環境設為 False
    }


def get_uvicorn_config() -> Dict[str, Any]:
    """獲取 Uvicorn 配置

    Returns:
        Dict[str, Any]: Uvicorn 配置字典

    Note:
        包含 ASGI 伺服器的配置參數
    """
    return {
        "host": "127.0.0.1",
        "port": 8000,
        "reload": True,  # 開發環境設為 True
        "log_level": "info",
        "access_log": True,
        "reload_dirs": ["src/api"],
        "reload_includes": ["*.py"],
        "workers": 1,  # 開發環境使用單進程
    }


def get_middleware_config() -> Dict[str, Any]:
    """獲取中間件配置

    Returns:
        Dict[str, Any]: 中間件配置字典

    Note:
        包含所有中間件的配置參數
    """
    return {
        "auth": {
            "enabled": True,
            "exclude_paths": ["/", "/health", "/docs", "/redoc", "/openapi.json"],
        },
        "rate_limit": {
            "enabled": True,
            "default_limit": "1000/minute",
            "burst_limit": "100/minute",
        },
        "logging": {
            "enabled": True,
            "log_requests": True,
            "log_responses": True,
            "exclude_paths": ["/health"],
        },
    }


def get_security_config() -> Dict[str, Any]:
    """獲取安全配置

    Returns:
        Dict[str, Any]: 安全配置字典

    Note:
        包含 JWT、加密等安全相關配置
    """
    return {
        "jwt": {
            "secret_key": "your-secret-key-here",  # 生產環境從環境變數讀取
            "algorithm": "HS256",
            "access_token_expire_minutes": 30,
            "refresh_token_expire_days": 7,
        },
        "password": {
            "min_length": 8,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_numbers": True,
            "require_special_chars": True,
        },
        "session": {
            "max_sessions_per_user": 5,
            "session_timeout_minutes": 60,
        },
    }


def get_database_config() -> Dict[str, Any]:
    """獲取資料庫配置

    Returns:
        Dict[str, Any]: 資料庫配置字典

    Note:
        包含資料庫連接和池化配置
    """
    return {
        "url": "sqlite:///./trading_system.db",  # 開發環境使用 SQLite
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 3600,
        "echo": False,  # 生產環境設為 False
    }


def get_cache_config() -> Dict[str, Any]:
    """獲取快取配置

    Returns:
        Dict[str, Any]: 快取配置字典

    Note:
        包含 Redis 等快取系統配置
    """
    return {
        "redis": {
            "host": "localhost",
            "port": 6379,
            "db": 0,
            "password": None,
            "max_connections": 10,
        },
        "ttl": {
            "default": 300,  # 5 分鐘
            "market_data": 60,  # 1 分鐘
            "user_session": 1800,  # 30 分鐘
        },
    }
