"""
API 版本控制中間件

此模組實現了 API 版本控制中間件，提供多種版本檢測方法，
包括 URL 路徑、Header、查詢參數等方式的版本控制。

支援功能：
- URL 路徑版本控制 (/api/v1/, /api/v2/)
- Header 版本控制 (Accept-Version)
- 查詢參數版本控制 (?version=1.0)
- SemVer 格式版本管理
- 向後相容性檢查
- 版本狀態管理
"""

import re
import logging
from typing import Optional, Dict, List, Tuple
from urllib.parse import parse_qs
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.api.models.versioning import (
    VersionDetectionMethodEnum,
    SemanticVersion,
    VersionStatusEnum,
)

logger = logging.getLogger(__name__)


class VersioningMiddleware(BaseHTTPMiddleware):
    """API 版本控制中間件"""

    def __init__(
        self,
        app,
        default_version: str = "1.0.0",
        supported_versions: Optional[List[str]] = None,
        version_header: str = "Accept-Version",
        version_param: str = "version",
        strict_mode: bool = False,
    ):
        """
        初始化版本控制中間件

        Args:
            app: FastAPI 應用實例
            default_version: 預設版本
            supported_versions: 支援的版本列表
            version_header: 版本標頭名稱
            version_param: 版本查詢參數名稱
            strict_mode: 嚴格模式（不支援的版本會返回錯誤）
        """
        super().__init__(app)
        self.default_version = default_version
        self.supported_versions = supported_versions or ["1.0.0"]
        self.version_header = version_header
        self.version_param = version_param
        self.strict_mode = strict_mode

        # 版本檢測優先級
        self.detection_priority = [
            VersionDetectionMethodEnum.URL_PATH,
            VersionDetectionMethodEnum.HEADER,
            VersionDetectionMethodEnum.QUERY_PARAM,
            VersionDetectionMethodEnum.CONTENT_TYPE,
        ]

        # 不需要版本控制的路徑
        self.excluded_paths = {
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/info",
        }

        logger.info(f"版本控制中間件初始化完成，預設版本: {default_version}")

    async def dispatch(self, request: Request, call_next):
        """處理請求版本控制"""
        # 檢查是否為排除路徑
        if self._is_excluded_path(request.url.path):
            return await call_next(request)

        try:
            # 檢測 API 版本
            detected_version, detection_method = self._detect_version(request)

            # 驗證版本
            validated_version = self._validate_version(detected_version)

            # 檢查版本狀態
            version_status = self._get_version_status(validated_version)

            # 將版本信息添加到請求狀態
            request.state.api_version = validated_version
            request.state.version_detection_method = detection_method
            request.state.version_status = version_status

            # 添加版本相關的響應標頭
            response = await call_next(request)

            # 添加版本信息到響應標頭
            response.headers["API-Version"] = validated_version
            response.headers["API-Version-Status"] = version_status.value
            response.headers["API-Supported-Versions"] = ",".join(
                self.supported_versions
            )

            # 如果版本已棄用，添加警告標頭
            if version_status == VersionStatusEnum.DEPRECATED:
                response.headers["Warning"] = (
                    f'299 - "API version {validated_version} is deprecated"'
                )

            return response

        except HTTPException as e:
            logger.warning("版本控制錯誤: %s", e.detail)
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "success": False,
                    "error_code": e.status_code,
                    "message": e.detail,
                    "supported_versions": self.supported_versions,
                    "default_version": self.default_version,
                },
            )
        except Exception as e:
            logger.error("版本控制中間件錯誤: %s", e)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "error_code": 500,
                    "message": "版本控制處理失敗",
                    "supported_versions": self.supported_versions,
                },
            )

    def _is_excluded_path(self, path: str) -> bool:
        """檢查是否為排除路徑"""
        # 檢查完全匹配
        if path in self.excluded_paths:
            return True

        # 檢查靜態資源路徑
        if path.startswith("/static/"):
            return True

        # 檢查文檔相關路徑
        if any(doc_path in path for doc_path in ["/docs", "/redoc", "/openapi"]):
            return True

        return False

    def _detect_version(
        self, request: Request
    ) -> Tuple[str, VersionDetectionMethodEnum]:
        """
        檢測 API 版本

        Returns:
            Tuple[str, VersionDetectionMethodEnum]: (版本號, 檢測方法)
        """
        for method in self.detection_priority:
            version = None

            if method == VersionDetectionMethodEnum.URL_PATH:
                version = self._detect_version_from_url(request.url.path)
            elif method == VersionDetectionMethodEnum.HEADER:
                version = self._detect_version_from_header(request.headers)
            elif method == VersionDetectionMethodEnum.QUERY_PARAM:
                version = self._detect_version_from_query(request.url.query)
            elif method == VersionDetectionMethodEnum.CONTENT_TYPE:
                version = self._detect_version_from_content_type(
                    request.headers.get("content-type")
                )

            if version:
                logger.debug(f"檢測到版本 {version}，方法: {method.value}")
                return version, method

        # 如果沒有檢測到版本，使用預設版本
        logger.debug(f"未檢測到版本，使用預設版本: {self.default_version}")
        return self.default_version, VersionDetectionMethodEnum.URL_PATH

    def _detect_version_from_url(self, path: str) -> Optional[str]:
        """從 URL 路徑檢測版本"""
        # 匹配 /api/v1.0.0/ 或 /api/v1/ 格式
        patterns = [r"/api/v(\d+\.\d+\.\d+)/", r"/api/v(\d+\.\d+)/", r"/api/v(\d+)/"]

        for pattern in patterns:
            match = re.search(pattern, path)
            if match:
                version_str = match.group(1)
                # 標準化版本格式
                if version_str.count(".") == 0:
                    return f"{version_str}.0.0"
                elif version_str.count(".") == 1:
                    return f"{version_str}.0"
                return version_str

        return None

    def _detect_version_from_header(self, headers: Dict[str, str]) -> Optional[str]:
        """從 Header 檢測版本"""
        # 檢查自定義版本標頭
        version = headers.get(self.version_header)
        if version:
            return version

        # 檢查 Accept 標頭中的版本信息
        accept_header = headers.get("accept", "")
        if "application/vnd.api" in accept_header:
            # 匹配 application/vnd.api+json;version=1.0 格式
            match = re.search(r"version=([0-9\.]+)", accept_header)
            if match:
                return match.group(1)

        return None

    def _detect_version_from_query(self, query_string: str) -> Optional[str]:
        """從查詢參數檢測版本"""
        if not query_string:
            return None

        # 解析查詢參數
        params = parse_qs(query_string)
        version_values = params.get(self.version_param, [])

        if version_values:
            return version_values[0]

        return None

    def _detect_version_from_content_type(
        self, content_type: Optional[str]
    ) -> Optional[str]:
        """從 Content-Type 檢測版本"""
        if not content_type:
            return None

        # 匹配 application/vnd.api.v1+json 格式
        match = re.search(r"application/vnd\.api\.v([0-9\.]+)", content_type)
        if match:
            return match.group(1)

        return None

    def _validate_version(self, version: str) -> str:
        """驗證版本號"""
        try:
            # 解析語義化版本
            semantic_version = SemanticVersion.parse(version)
            version_str = str(semantic_version)

            # 檢查是否為支援的版本
            if version_str not in self.supported_versions:
                if self.strict_mode:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"不支援的 API 版本: {version_str}",
                    )
                else:
                    # 非嚴格模式下，尋找最接近的支援版本
                    closest_version = self._find_closest_version(semantic_version)
                    logger.warning(
                        f"版本 {version_str} 不支援，使用最接近的版本: {closest_version}"
                    )
                    return closest_version

            return version_str

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"無效的版本格式: {version}",
            )

    def _find_closest_version(self, target_version: SemanticVersion) -> str:
        """尋找最接近的支援版本"""
        supported_semantic_versions = []

        for version_str in self.supported_versions:
            try:
                supported_semantic_versions.append(SemanticVersion.parse(version_str))
            except ValueError:
                continue

        if not supported_semantic_versions:
            return self.default_version

        # 尋找最接近的版本（優先選擇較新的版本）
        closest = min(
            supported_semantic_versions,
            key=lambda v: (
                abs(v.major - target_version.major) * 10000
                + abs(v.minor - target_version.minor) * 100
                + abs(v.patch - target_version.patch)
            ),
        )

        return str(closest)

    def _get_version_status(self, version: str) -> VersionStatusEnum:
        """
        獲取版本狀態

        Args:
            version: 版本號

        Returns:
            VersionStatusEnum: 版本狀態
        """
        # 這裡可以從資料庫或配置文件獲取版本狀態
        # 目前使用簡單的邏輯判斷
        try:
            semantic_version = SemanticVersion.parse(version)

            # 簡單的狀態判斷邏輯
            if semantic_version.major == 0:
                return VersionStatusEnum.DEVELOPMENT
            elif semantic_version.prerelease:
                return VersionStatusEnum.BETA
            else:
                return VersionStatusEnum.STABLE

        except ValueError:
            return VersionStatusEnum.STABLE

    def get_supported_versions(self) -> List[str]:
        """
        獲取支援的版本列表

        Returns:
            List[str]: 支援的版本列表
        """
        return self.supported_versions.copy()

    def add_supported_version(self, version: str) -> bool:
        """
        添加支援的版本

        Args:
            version: 版本號

        Returns:
            bool: 是否添加成功
        """
        try:
            # 驗證版本格式
            SemanticVersion.parse(version)

            if version not in self.supported_versions:
                self.supported_versions.append(version)
                self.supported_versions.sort(key=lambda v: SemanticVersion.parse(v))
                logger.info(f"添加支援版本: {version}")
                return True
            return False

        except ValueError as e:
            logger.error(f"無效的版本格式: {version}, 錯誤: {e}")
            return False

    def remove_supported_version(self, version: str) -> bool:
        """
        移除支援的版本

        Args:
            version: 版本號

        Returns:
            bool: 是否移除成功
        """
        if version in self.supported_versions:
            # 不能移除預設版本
            if version == self.default_version:
                logger.warning(f"無法移除預設版本: {version}")
                return False

            self.supported_versions.remove(version)
            logger.info(f"移除支援版本: {version}")
            return True
        return False

    def is_version_deprecated(self, version: str) -> bool:
        """
        檢查版本是否已棄用

        Args:
            version: 版本號

        Returns:
            bool: 是否已棄用
        """
        status = self._get_version_status(version)
        return status == VersionStatusEnum.DEPRECATED
