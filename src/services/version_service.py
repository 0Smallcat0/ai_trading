"""
版本管理服務層

此模組實現版本管理的業務邏輯，包括版本的創建、查詢、更新、刪除、
相容性檢查、版本協商等核心功能。
"""

import logging
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

# 導入資料庫相關模組
from sqlalchemy import create_engine, desc, func, and_, or_, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

# 導入配置
from src.config import DB_URL, CACHE_DIR

# 導入模型
from src.api.models.versioning import (
    APIVersion,
    SemanticVersion,
    VersionStatusEnum,
    VersionTypeEnum,
    CompatibilityLevelEnum,
    CompatibilityCheck,
    MigrationPlan,
    VersionCreateRequest,
    VersionUpdateRequest,
    VersionListRequest,
    VersionNegotiationRequest,
    VersionDetectionMethodEnum,
)

logger = logging.getLogger(__name__)


class VersionService:
    """版本管理服務類"""

    def __init__(self):
        """初始化服務"""
        self.engine = create_engine(DB_URL) if DB_URL else None
        self.session_factory = sessionmaker(bind=self.engine) if self.engine else None
        self.cache_dir = Path(CACHE_DIR) if CACHE_DIR else Path("cache")
        self.cache_dir.mkdir(exist_ok=True)

        # 版本快取目錄
        self.versions_cache_dir = self.cache_dir / "versions"
        self.versions_cache_dir.mkdir(exist_ok=True)

    def create_version(
        self, request: VersionCreateRequest, current_user: str
    ) -> Dict[str, Any]:
        """
        創建新版本

        Args:
            request: 創建版本請求
            current_user: 當前用戶

        Returns:
            Dict[str, Any]: 創建的版本信息

        Raises:
            ValueError: 參數驗證失敗
            Exception: 創建失敗
        """
        try:
            # 解析和驗證版本號
            semantic_version = SemanticVersion.parse(request.version)
            version_str = str(semantic_version)

            # 檢查版本是否已存在
            if self._version_exists(version_str):
                raise ValueError(f"版本 {version_str} 已存在")

            # 創建 API 版本對象
            api_version = APIVersion(
                version=semantic_version,
                status=request.status,
                release_date=request.release_date or datetime.now(),
                deprecation_date=request.deprecation_date,
                retirement_date=request.retirement_date,
                title=request.title,
                description=request.description,
                changelog=request.changelog or [],
                compatible_versions=request.compatible_versions or [],
                breaking_changes=request.breaking_changes or [],
                maintainer=request.maintainer or current_user,
                documentation_url=request.documentation_url,
                migration_guide_url=request.migration_guide_url,
            )

            # 保存版本信息
            version_data = api_version.model_dump(mode="json")
            self._save_version_to_cache(version_str, version_data)

            logger.info(f"版本創建成功: {version_str}")
            return version_data

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"創建版本失敗: {e}")
            raise

    def get_version(self, version: str, current_user: str) -> Optional[Dict[str, Any]]:
        """
        獲取版本詳情

        Args:
            version: 版本號
            current_user: 當前用戶

        Returns:
            Optional[Dict[str, Any]]: 版本詳情
        """
        try:
            # 標準化版本號
            semantic_version = SemanticVersion.parse(version)
            version_str = str(semantic_version)

            # 從快取載入版本信息
            version_data = self._load_version_from_cache(version_str)

            if not version_data:
                return None

            # 檢查權限（簡化版本）
            if not self._check_version_permission(version_data, current_user, "read"):
                return None

            return version_data

        except Exception as e:
            logger.error(f"獲取版本詳情失敗: {e}")
            return None

    def list_versions(
        self, request: VersionListRequest, current_user: str
    ) -> Dict[str, Any]:
        """
        查詢版本列表

        Args:
            request: 查詢請求
            current_user: 當前用戶

        Returns:
            Dict[str, Any]: 版本列表和分頁信息
        """
        try:
            # 獲取所有版本
            all_versions = self._get_all_versions_from_cache()

            # 權限過濾
            accessible_versions = [
                version
                for version in all_versions
                if self._check_version_permission(version, current_user, "read")
            ]

            # 應用篩選條件
            filtered_versions = self._apply_filters(accessible_versions, request)

            # 排序
            sorted_versions = self._apply_sorting(
                filtered_versions, request.sort_by, request.sort_order
            )

            # 分頁
            total = len(sorted_versions)
            start_idx = (request.page - 1) * request.page_size
            end_idx = start_idx + request.page_size
            page_versions = sorted_versions[start_idx:end_idx]

            # 計算分頁信息
            total_pages = (total + request.page_size - 1) // request.page_size
            has_next = request.page < total_pages
            has_prev = request.page > 1

            return {
                "versions": page_versions,
                "total": total,
                "page": request.page,
                "page_size": request.page_size,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev,
            }

        except Exception as e:
            logger.error(f"查詢版本列表失敗: {e}")
            raise

    def update_version(
        self, version: str, request: VersionUpdateRequest, current_user: str
    ) -> Optional[Dict[str, Any]]:
        """
        更新版本

        Args:
            version: 版本號
            request: 更新請求
            current_user: 當前用戶

        Returns:
            Optional[Dict[str, Any]]: 更新後的版本信息
        """
        try:
            # 標準化版本號
            semantic_version = SemanticVersion.parse(version)
            version_str = str(semantic_version)

            # 獲取現有版本
            version_data = self._load_version_from_cache(version_str)
            if not version_data:
                return None

            # 檢查權限
            if not self._check_version_permission(version_data, current_user, "update"):
                return None

            # 更新欄位
            update_fields = {}
            if request.title is not None:
                update_fields["title"] = request.title
            if request.description is not None:
                update_fields["description"] = request.description
            if request.status is not None:
                update_fields["status"] = request.status.value
            if request.deprecation_date is not None:
                update_fields["deprecation_date"] = request.deprecation_date.isoformat()
            if request.retirement_date is not None:
                update_fields["retirement_date"] = request.retirement_date.isoformat()
            if request.changelog is not None:
                update_fields["changelog"] = request.changelog
            if request.breaking_changes is not None:
                update_fields["breaking_changes"] = request.breaking_changes
            if request.compatible_versions is not None:
                update_fields["compatible_versions"] = request.compatible_versions
            if request.maintainer is not None:
                update_fields["maintainer"] = request.maintainer
            if request.documentation_url is not None:
                update_fields["documentation_url"] = request.documentation_url
            if request.migration_guide_url is not None:
                update_fields["migration_guide_url"] = request.migration_guide_url

            # 更新時間戳
            update_fields["updated_at"] = datetime.now().isoformat()

            # 應用更新
            version_data.update(update_fields)

            # 保存更新
            self._save_version_to_cache(version_str, version_data)

            logger.info(f"版本更新成功: {version_str}")
            return version_data

        except Exception as e:
            logger.error(f"更新版本失敗: {e}")
            raise

    def delete_version(self, version: str, current_user: str) -> bool:
        """
        刪除版本

        Args:
            version: 版本號
            current_user: 當前用戶

        Returns:
            bool: 是否刪除成功
        """
        try:
            # 標準化版本號
            semantic_version = SemanticVersion.parse(version)
            version_str = str(semantic_version)

            # 獲取版本
            version_data = self._load_version_from_cache(version_str)
            if not version_data:
                return False

            # 檢查權限
            if not self._check_version_permission(version_data, current_user, "delete"):
                return False

            # 軟刪除：更新狀態為已停用
            version_data["status"] = VersionStatusEnum.RETIRED.value
            version_data["retirement_date"] = datetime.now().isoformat()
            version_data["updated_at"] = datetime.now().isoformat()

            # 保存更新
            self._save_version_to_cache(version_str, version_data)

            logger.info(f"版本刪除成功: {version_str}")
            return True

        except Exception as e:
            logger.error(f"刪除版本失敗: {e}")
            return False

    def negotiate_version(
        self, request: VersionNegotiationRequest, available_versions: List[str]
    ) -> Dict[str, Any]:
        """
        版本協商

        Args:
            request: 協商請求
            available_versions: 可用版本列表

        Returns:
            Dict[str, Any]: 協商結果
        """
        try:
            selected_version = None
            compatibility_warnings = []
            migration_required = False

            # 1. 檢查偏好版本
            if (
                request.preferred_version
                and request.preferred_version in available_versions
            ):
                selected_version = request.preferred_version

            # 2. 檢查客戶端版本
            elif (
                request.client_version and request.client_version in available_versions
            ):
                selected_version = request.client_version

            # 3. 檢查支援版本列表
            elif request.supported_versions:
                for version in request.supported_versions:
                    if version in available_versions:
                        selected_version = version
                        break

            # 4. 使用備用版本
            elif (
                request.fallback_version
                and request.fallback_version in available_versions
            ):
                selected_version = request.fallback_version
                compatibility_warnings.append(
                    f"使用備用版本 {request.fallback_version}"
                )

            # 5. 使用最新穩定版本
            else:
                stable_versions = [
                    v for v in available_versions if self._is_stable_version(v)
                ]
                if stable_versions:
                    selected_version = max(
                        stable_versions, key=lambda v: SemanticVersion.parse(v)
                    )
                    compatibility_warnings.append("使用最新穩定版本")
                else:
                    selected_version = (
                        available_versions[0] if available_versions else "1.0.0"
                    )
                    compatibility_warnings.append("使用預設版本")

            # 檢查是否需要遷移
            if request.client_version and selected_version != request.client_version:
                migration_required = True

            return {
                "selected_version": selected_version,
                "available_versions": available_versions,
                "compatibility_warnings": compatibility_warnings,
                "migration_required": migration_required,
                "migration_url": (
                    f"/docs/migration/{request.client_version}-to-{selected_version}"
                    if migration_required
                    else None
                ),
            }

        except Exception as e:
            logger.error(f"版本協商失敗: {e}")
            raise

    def check_compatibility(
        self, source_version: str, target_version: str, current_user: str
    ) -> Dict[str, Any]:
        """
        檢查版本相容性

        Args:
            source_version: 源版本
            target_version: 目標版本
            current_user: 當前用戶

        Returns:
            Dict[str, Any]: 相容性檢查結果
        """
        try:
            # 解析版本
            source_semantic = SemanticVersion.parse(source_version)
            target_semantic = SemanticVersion.parse(target_version)

            # 獲取版本詳情
            source_data = self._load_version_from_cache(str(source_semantic))
            target_data = self._load_version_from_cache(str(target_semantic))

            if not source_data or not target_data:
                raise ValueError("版本不存在")

            # 執行相容性檢查
            compatibility_level = self._determine_compatibility_level(
                source_semantic, target_semantic
            )
            is_compatible = compatibility_level != CompatibilityLevelEnum.BREAKING

            breaking_changes = []
            warnings = []
            recommendations = []

            # 分析破壞性變更
            if target_semantic.major > source_semantic.major:
                breaking_changes.extend(target_data.get("breaking_changes", []))
                recommendations.append("建議進行完整的遷移測試")
            elif target_semantic.minor > source_semantic.minor:
                warnings.append("次版本升級可能包含新功能")
                recommendations.append("檢查新功能的相容性")
            elif target_semantic.patch > source_semantic.patch:
                recommendations.append("修訂版本通常向後相容")

            # 創建相容性檢查結果
            compatibility_check = CompatibilityCheck(
                source_version=str(source_semantic),
                target_version=str(target_semantic),
                compatibility_level=compatibility_level,
                is_compatible=is_compatible,
                breaking_changes=breaking_changes,
                warnings=warnings,
                recommendations=recommendations,
                endpoint_changes={},  # 實際實作中應該比較 API 端點
                schema_changes={},  # 實際實作中應該比較 Schema
                parameter_changes={},  # 實際實作中應該比較參數
                checked_by=current_user,
            )

            return {
                "check_result": compatibility_check.model_dump(mode="json"),
                "recommendations": recommendations,
                "migration_plan": None,  # 可以根據需要生成遷移計劃
            }

        except Exception as e:
            logger.error(f"相容性檢查失敗: {e}")
            raise

    # ==================== 私有方法 ====================

    def _version_exists(self, version: str) -> bool:
        """檢查版本是否存在"""
        cache_file = self.versions_cache_dir / f"{version}.json"
        return cache_file.exists()

    def _save_version_to_cache(self, version: str, data: Dict[str, Any]) -> None:
        """保存版本到快取"""
        cache_file = self.versions_cache_dir / f"{version}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def _load_version_from_cache(self, version: str) -> Optional[Dict[str, Any]]:
        """從快取載入版本"""
        cache_file = self.versions_cache_dir / f"{version}.json"
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"載入版本快取失敗: {e}")
            return None

    def _get_all_versions_from_cache(self) -> List[Dict[str, Any]]:
        """獲取所有版本"""
        versions = []
        for cache_file in self.versions_cache_dir.glob("*.json"):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    version_data = json.load(f)
                    versions.append(version_data)
            except Exception as e:
                logger.error(f"載入版本檔案失敗 {cache_file}: {e}")

        return versions

    def _check_version_permission(
        self, version_data: Dict[str, Any], user: str, action: str
    ) -> bool:
        """檢查版本權限（簡化版本）"""
        # 實際實作中應該整合完整的權限系統
        return True

    def _apply_filters(
        self, versions: List[Dict[str, Any]], request: VersionListRequest
    ) -> List[Dict[str, Any]]:
        """應用篩選條件"""
        filtered = versions

        # 狀態篩選
        if request.status:
            filtered = [v for v in filtered if v.get("status") == request.status.value]

        # 搜尋篩選
        if request.search:
            search_lower = request.search.lower()
            filtered = [
                v
                for v in filtered
                if (
                    search_lower in v.get("title", "").lower()
                    or search_lower in v.get("description", "").lower()
                    or search_lower in str(v.get("version", {})).lower()
                )
            ]

        # 是否包含已停用版本
        if not request.include_retired:
            filtered = [
                v
                for v in filtered
                if v.get("status") != VersionStatusEnum.RETIRED.value
            ]

        return filtered

    def _apply_sorting(
        self, versions: List[Dict[str, Any]], sort_by: str, sort_order: str
    ) -> List[Dict[str, Any]]:
        """應用排序"""
        reverse = sort_order == "desc"

        if sort_by == "version":
            # 按版本號排序
            return sorted(
                versions,
                key=lambda v: SemanticVersion.parse(
                    str(v.get("version", {}).get("major", 0))
                    + "."
                    + str(v.get("version", {}).get("minor", 0))
                    + "."
                    + str(v.get("version", {}).get("patch", 0))
                ),
                reverse=reverse,
            )
        elif sort_by in [
            "release_date",
            "deprecation_date",
            "retirement_date",
            "created_at",
            "updated_at",
        ]:
            # 按日期排序
            return sorted(
                versions,
                key=lambda v: (
                    datetime.fromisoformat(v.get(sort_by, "1970-01-01T00:00:00"))
                    if v.get(sort_by)
                    else datetime.min
                ),
                reverse=reverse,
            )
        else:
            # 按字符串欄位排序
            return sorted(
                versions, key=lambda v: str(v.get(sort_by, "")), reverse=reverse
            )

    def _is_stable_version(self, version: str) -> bool:
        """檢查是否為穩定版本"""
        try:
            semantic_version = SemanticVersion.parse(version)
            return semantic_version.prerelease is None and semantic_version.major > 0
        except ValueError:
            return False

    def _determine_compatibility_level(
        self, source: SemanticVersion, target: SemanticVersion
    ) -> CompatibilityLevelEnum:
        """確定相容性級別"""
        if source == target:
            return CompatibilityLevelEnum.FULL

        if target.major > source.major:
            return CompatibilityLevelEnum.BREAKING
        elif target.major < source.major:
            return CompatibilityLevelEnum.NONE

        if target.minor > source.minor:
            return CompatibilityLevelEnum.BACKWARD
        elif target.minor < source.minor:
            return CompatibilityLevelEnum.FORWARD

        if target.patch > source.patch:
            return CompatibilityLevelEnum.BACKWARD
        elif target.patch < source.patch:
            return CompatibilityLevelEnum.FORWARD

        return CompatibilityLevelEnum.FULL
