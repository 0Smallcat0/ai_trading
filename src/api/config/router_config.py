"""路由配置模組

此模組負責配置和註冊所有 API 路由，包括路由前綴、標籤、
依賴項等設定。
"""

from typing import List, Dict, Any
from fastapi import FastAPI, Depends

# 導入所有路由模組
from src.api.routers import (
    data_management,
    strategy_management,
    ai_models,
    backtest,
    portfolio,
    risk_management,
    trading,
    monitoring,
    reports,
    auth,
    system,
)
from src.api.utils.security import get_current_user


def get_router_configs() -> List[Dict[str, Any]]:
    """獲取路由配置列表

    Returns:
        List[Dict[str, Any]]: 路由配置列表

    Note:
        包含所有路由的配置資訊，如前綴、標籤、依賴項等
    """
    return [
        {
            "router": auth.router,
            "prefix": "/api/v1/auth",
            "tags": ["🔐 身份認證"],
            "dependencies": [],  # 認證路由不需要認證依賴
        },
        {
            "router": data_management.router,
            "prefix": "/api/v1/data",
            "tags": ["📊 資料管理"],
            "dependencies": [Depends(get_current_user)],
        },
        {
            "router": strategy_management.router,
            "prefix": "/api/v1/strategies",
            "tags": ["🎯 策略管理"],
            "dependencies": [Depends(get_current_user)],
        },
        {
            "router": ai_models.router,
            "prefix": "/api/v1/models",
            "tags": ["🤖 AI 模型"],
            "dependencies": [Depends(get_current_user)],
        },
        {
            "router": backtest.router,
            "prefix": "/api/v1/backtest",
            "tags": ["📈 回測系統"],
            "dependencies": [Depends(get_current_user)],
        },
        {
            "router": portfolio.router,
            "prefix": "/api/v1/portfolio",
            "tags": ["💼 投資組合"],
            "dependencies": [Depends(get_current_user)],
        },
        {
            "router": risk_management.router,
            "prefix": "/api/v1/risk",
            "tags": ["🛡️ 風險管理"],
            "dependencies": [Depends(get_current_user)],
        },
        {
            "router": trading.router,
            "prefix": "/api/v1/trading",
            "tags": ["⚡ 交易執行"],
            "dependencies": [Depends(get_current_user)],
        },
        {
            "router": monitoring.router,
            "prefix": "/api/v1/monitoring",
            "tags": ["📡 系統監控"],
            "dependencies": [Depends(get_current_user)],
        },
        {
            "router": reports.router,
            "prefix": "/api/v1/reports",
            "tags": ["📋 報表分析"],
            "dependencies": [Depends(get_current_user)],
        },
        {
            "router": system.router,
            "prefix": "/api/v1/system",
            "tags": ["⚙️ 系統管理"],
            "dependencies": [Depends(get_current_user)],
        },
    ]


def register_routers(app: FastAPI) -> None:
    """註冊所有路由

    Args:
        app: FastAPI 應用實例

    Note:
        根據配置註冊所有 API 路由
    """
    router_configs = get_router_configs()

    for config in router_configs:
        app.include_router(
            config["router"],
            prefix=config["prefix"],
            tags=config["tags"],
            dependencies=config.get("dependencies", []),
        )


def get_public_routes() -> List[str]:
    """獲取公開路由列表

    Returns:
        List[str]: 不需要認證的路由路徑列表

    Note:
        這些路由不需要 JWT Token 認證
    """
    return [
        "/",
        "/health",
        "/api/info",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
    ]


def get_admin_routes() -> List[str]:
    """獲取管理員路由列表

    Returns:
        List[str]: 需要管理員權限的路由路徑列表

    Note:
        這些路由需要管理員角色才能訪問
    """
    return [
        "/api/v1/system/users",
        "/api/v1/system/roles",
        "/api/v1/system/permissions",
        "/api/v1/system/config",
        "/api/v1/system/logs",
        "/api/v1/monitoring/system",
        "/api/v1/monitoring/performance",
    ]


def get_rate_limit_config() -> Dict[str, Dict[str, Any]]:
    """獲取路由速率限制配置

    Returns:
        Dict[str, Dict[str, Any]]: 路由速率限制配置

    Note:
        不同路由可以有不同的速率限制
    """
    return {
        "/api/v1/auth/login": {
            "limit": "10/minute",
            "burst": "5/minute",
        },
        "/api/v1/auth/register": {
            "limit": "5/minute",
            "burst": "2/minute",
        },
        "/api/v1/trading/orders": {
            "limit": "100/minute",
            "burst": "20/minute",
        },
        "/api/v1/data/market": {
            "limit": "500/minute",
            "burst": "100/minute",
        },
        "default": {
            "limit": "1000/minute",
            "burst": "200/minute",
        },
    }


def get_cache_config() -> Dict[str, Dict[str, Any]]:
    """獲取路由快取配置

    Returns:
        Dict[str, Dict[str, Any]]: 路由快取配置

    Note:
        配置哪些路由需要快取以及快取時間
    """
    return {
        "/api/v1/data/market": {
            "enabled": True,
            "ttl": 60,  # 1 分鐘
            "key_prefix": "market_data",
        },
        "/api/v1/data/historical": {
            "enabled": True,
            "ttl": 300,  # 5 分鐘
            "key_prefix": "historical_data",
        },
        "/api/v1/portfolio/performance": {
            "enabled": True,
            "ttl": 180,  # 3 分鐘
            "key_prefix": "portfolio_perf",
        },
        "/api/v1/reports/analytics": {
            "enabled": True,
            "ttl": 600,  # 10 分鐘
            "key_prefix": "analytics",
        },
    }


def get_validation_config() -> Dict[str, Dict[str, Any]]:
    """獲取路由驗證配置

    Returns:
        Dict[str, Dict[str, Any]]: 路由驗證配置

    Note:
        配置路由的輸入驗證規則
    """
    return {
        "/api/v1/trading/orders": {
            "max_quantity": 10000,
            "min_price": 0.01,
            "max_price": 1000000,
            "allowed_symbols": ["AAPL", "GOOGL", "MSFT", "TSLA"],
        },
        "/api/v1/portfolio/rebalance": {
            "max_positions": 50,
            "min_weight": 0.01,
            "max_weight": 0.5,
        },
        "/api/v1/strategies/create": {
            "max_name_length": 100,
            "max_description_length": 1000,
            "allowed_types": ["momentum", "mean_reversion", "arbitrage"],
        },
    }


def get_response_config() -> Dict[str, Dict[str, Any]]:
    """獲取路由響應配置

    Returns:
        Dict[str, Dict[str, Any]]: 路由響應配置

    Note:
        配置路由的響應格式和壓縮設定
    """
    return {
        "compression": {
            "enabled": True,
            "min_size": 1024,  # 1KB
            "algorithms": ["gzip", "deflate"],
        },
        "headers": {
            "X-API-Version": "1.0.0",
            "X-Rate-Limit-Remaining": "dynamic",
            "X-Request-ID": "dynamic",
        },
        "pagination": {
            "default_page_size": 20,
            "max_page_size": 100,
            "page_size_param": "page_size",
            "page_param": "page",
        },
    }


def get_monitoring_config() -> Dict[str, Dict[str, Any]]:
    """獲取路由監控配置

    Returns:
        Dict[str, Dict[str, Any]]: 路由監控配置

    Note:
        配置路由的監控和指標收集
    """
    return {
        "metrics": {
            "enabled": True,
            "collect_request_duration": True,
            "collect_response_size": True,
            "collect_error_rate": True,
        },
        "logging": {
            "log_requests": True,
            "log_responses": False,  # 避免記錄敏感資料
            "log_errors": True,
            "exclude_paths": ["/health", "/metrics"],
        },
        "alerts": {
            "error_rate_threshold": 0.05,  # 5%
            "response_time_threshold": 2.0,  # 2 秒
            "check_interval": 60,  # 1 分鐘
        },
    }
