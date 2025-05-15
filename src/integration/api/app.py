"""
API應用程序

此模組實現了FastAPI應用程序，提供RESTful API服務。
"""

import os
import threading
import time
from datetime import datetime

import uvicorn
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.audit_trail import AuditEventType, audit_trail
from src.core.logger import logger

from .routes import (
    auth_router,
    backtest_router,
    market_data_router,
    portfolio_router,
    signal_router,
    strategy_router,
    system_router,
    trade_router,
    workflow_router,
)
from .tls import tls_config

# 創建API路由器
api_router = APIRouter()

# 添加各個路由
api_router.include_router(auth_router, prefix="/auth", tags=["認證"])
api_router.include_router(trade_router, prefix="/trade", tags=["交易"])
api_router.include_router(portfolio_router, prefix="/portfolio", tags=["投資組合"])
api_router.include_router(strategy_router, prefix="/strategy", tags=["策略"])
api_router.include_router(backtest_router, prefix="/backtest", tags=["回測"])
api_router.include_router(market_data_router, prefix="/market-data", tags=["市場數據"])
api_router.include_router(system_router, prefix="/system", tags=["系統"])
api_router.include_router(workflow_router, prefix="/workflow", tags=["工作流"])
api_router.include_router(signal_router, prefix="/signal", tags=["訊號"])


# 創建速率限制中間件
class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中間件"""

    def __init__(self, app, max_requests: int = 100, window_size: int = 60):
        """
        初始化速率限制中間件

        Args:
            app: FastAPI應用程序
            max_requests: 時間窗口內最大請求數
            window_size: 時間窗口大小（秒）
        """
        super().__init__(app)
        self.max_requests = max_requests
        self.window_size = window_size
        self.requests = {}
        self.lock = threading.Lock()

    async def dispatch(self, request: Request, call_next):
        """
        處理請求

        Args:
            request: 請求
            call_next: 下一個處理器

        Returns:
            Response: 響應
        """
        # 獲取客戶端 IP
        client_ip = request.client.host if request.client else "unknown"

        # 檢查速率限制
        with self.lock:
            # 初始化客戶端請求記錄
            if client_ip not in self.requests:
                self.requests[client_ip] = []

            # 獲取當前時間
            now = time.time()

            # 移除過期的請求
            self.requests[client_ip] = [
                timestamp
                for timestamp in self.requests[client_ip]
                if now - timestamp <= self.window_size
            ]

            # 檢查請求數量
            if len(self.requests[client_ip]) >= self.max_requests:
                # 超過速率限制
                return JSONResponse(
                    status_code=429,
                    content={
                        "status": "error",
                        "code": 429,
                        "message": "請求過於頻繁，請稍後再試",
                    },
                )

            # 記錄請求
            self.requests[client_ip].append(now)

        # 處理請求
        return await call_next(request)


# 創建審計中間件
class AuditMiddleware(BaseHTTPMiddleware):
    """審計中間件"""

    async def dispatch(self, request: Request, call_next):
        """
        處理請求

        Args:
            request: 請求
            call_next: 下一個處理器

        Returns:
            Response: 響應
        """
        # 獲取請求信息
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        method = request.method
        url = str(request.url)

        # 獲取當前用戶
        user_id = "anonymous"

        # 記錄請求開始時間
        start_time = time.time()

        # 處理請求
        response = await call_next(request)

        # 計算請求處理時間
        process_time = time.time() - start_time

        # 記錄審計事件
        if "/api/" in url and not url.endswith(("/docs", "/redoc", "/openapi.json")):
            audit_trail.log_event(
                event_type=AuditEventType.API_REQUEST,
                user_id=user_id,
                details={
                    "method": method,
                    "url": url,
                    "status_code": response.status_code,
                    "process_time": process_time,
                },
                ip_address=client_ip,
                user_agent=user_agent,
            )

        return response


def create_app() -> FastAPI:
    """
    創建FastAPI應用程序

    Returns:
        FastAPI: FastAPI應用程序
    """
    # 創建FastAPI應用程序
    app = FastAPI(
        title="交易系統API",
        description="提供交易系統的RESTful API服務",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # 添加可信主機中間件
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*"],  # 在生產環境中應該限制主機
    )

    # 添加CORS中間件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 在生產環境中應該限制來源
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 添加速率限制中間件
    app.add_middleware(
        RateLimitMiddleware,
        max_requests=100,  # 每分鐘最多 100 個請求
        window_size=60,
    )

    # 添加審計中間件
    app.add_middleware(AuditMiddleware)

    # 添加API路由
    app.include_router(api_router, prefix="/api")

    # 添加根路由
    @app.get("/", tags=["根"])
    async def root():
        """
        根路由

        Returns:
            Dict: 歡迎消息
        """
        return {
            "message": "歡迎使用交易系統API",
            "version": "1.0.0",
            "docs_url": "/docs",
            "redoc_url": "/redoc",
            "openapi_url": "/openapi.json",
        }

    # 添加健康檢查路由
    @app.get("/health", tags=["健康檢查"])
    async def health_check():
        """
        健康檢查

        Returns:
            Dict: 健康狀態
        """
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
        }

    # 添加錯誤處理
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """
        HTTP異常處理器

        Args:
            request: 請求
            exc: 異常

        Returns:
            Dict: 錯誤響應
        """
        return {"status": "error", "code": exc.status_code, "message": exc.detail}

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """
        通用異常處理器

        Args:
            request: 請求
            exc: 異常

        Returns:
            Dict: 錯誤響應
        """
        # 記錄錯誤
        logger.error(f"API錯誤: {exc}")

        return {"status": "error", "code": 500, "message": "內部服務器錯誤"}

    return app


# 如果直接運行此文件，則啟動應用程序
if __name__ == "__main__":
    # 獲取端口
    port = int(os.environ.get("PORT", 8000))

    # 檢查是否使用 TLS
    use_tls = os.environ.get("USE_TLS", "false").lower() == "true"

    # 配置 TLS
    ssl_keyfile = None
    ssl_certfile = None

    if use_tls:
        # 檢查 TLS 配置
        if not tls_config.is_available():
            # 生成自簽名證書
            success, cert_path, key_path = tls_config.generate_self_signed_cert()
            if success:
                ssl_certfile = cert_path
                ssl_keyfile = key_path
                logger.info(f"已生成自簽名證書: {cert_path}")
            else:
                logger.warning("無法生成自簽名證書，將使用 HTTP 而非 HTTPS")
                use_tls = False
        else:
            ssl_certfile = tls_config.cert_file
            ssl_keyfile = tls_config.key_file
            logger.info(f"使用現有 TLS 證書: {ssl_certfile}")

    # 啟動應用程序
    uvicorn.run(
        "app:create_app",
        host="0.0.0.0",
        port=port,
        reload=True,
        factory=True,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
    )

    logger.info(f"API 服務器已啟動: {'https' if use_tls else 'http'}://0.0.0.0:{port}")
