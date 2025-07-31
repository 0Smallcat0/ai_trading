"""
API 版本控制路由

此模組定義了 API 版本控制相關的路由端點，包括版本管理、
相容性檢查、版本協商、遷移管理等功能。
"""

import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, status, Query, Path
from fastapi.security import HTTPBearer

# 導入模型
from src.api.models.versioning import (
    VersionCreateRequest,
    VersionUpdateRequest,
    VersionListRequest,
    VersionResponse,
    VersionListResponse,
    VersionNegotiationRequest,
    VersionNegotiationResponse,
    CompatibilityCheckResponse,
    VersionDetectionRequest,
    APIVersion,
)

# 導入服務
from src.services.version_service import VersionService
from src.tools.migration.migration_manager import MigrationManager

# 導入認證
from src.api.auth import get_current_user, require_permissions

logger = logging.getLogger(__name__)

# 創建路由器
router = APIRouter(prefix="/api/v1/versions", tags=["版本控制"])
security = HTTPBearer()

# 初始化服務
version_service = VersionService()
migration_manager = MigrationManager()


@router.post(
    "/",
    response_model=Dict[str, Any],
    summary="創建新版本",
    description="創建新的 API 版本，包括版本信息、相容性設定等",
)
async def create_version(
    request: VersionCreateRequest, current_user: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    創建新版本

    Args:
        request: 創建版本請求
        current_user: 當前用戶

    Returns:
        Dict[str, Any]: 創建的版本信息

    Raises:
        HTTPException: 創建失敗時拋出異常
    """
    try:
        # 檢查權限
        await require_permissions(current_user, ["version:create"])

        # 創建版本
        version_data = version_service.create_version(request, current_user)

        logger.info(f"用戶 {current_user} 創建版本成功: {request.version}")
        return {"success": True, "message": "版本創建成功", "data": version_data}

    except ValueError as e:
        logger.warning(f"創建版本參數錯誤: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"創建版本失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="創建版本失敗"
        )


@router.get(
    "/",
    response_model=VersionListResponse,
    summary="查詢版本列表",
    description="查詢 API 版本列表，支援分頁、篩選和排序",
)
async def list_versions(
    page: int = Query(1, ge=1, description="頁碼"),
    page_size: int = Query(20, ge=1, le=100, description="每頁數量"),
    status: Optional[str] = Query(None, description="狀態篩選"),
    search: Optional[str] = Query(None, max_length=100, description="搜尋關鍵字"),
    sort_by: str = Query("version", description="排序欄位"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序方向"),
    include_retired: bool = Query(False, description="是否包含已停用版本"),
    current_user: str = Depends(get_current_user),
) -> VersionListResponse:
    """
    查詢版本列表

    Args:
        page: 頁碼
        page_size: 每頁數量
        status: 狀態篩選
        search: 搜尋關鍵字
        sort_by: 排序欄位
        sort_order: 排序方向
        include_retired: 是否包含已停用版本
        current_user: 當前用戶

    Returns:
        VersionListResponse: 版本列表響應

    Raises:
        HTTPException: 查詢失敗時拋出異常
    """
    try:
        # 檢查權限
        await require_permissions(current_user, ["version:read"])

        # 構建查詢請求
        request = VersionListRequest(
            page=page,
            page_size=page_size,
            status=status,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            include_retired=include_retired,
        )

        # 查詢版本列表
        result = version_service.list_versions(request, current_user)

        return VersionListResponse(**result)

    except Exception as e:
        logger.error(f"查詢版本列表失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="查詢版本列表失敗"
        )


@router.get(
    "/{version}",
    response_model=VersionResponse,
    summary="獲取版本詳情",
    description="獲取指定版本的詳細信息",
)
async def get_version(
    version: str = Path(..., description="版本號"),
    current_user: str = Depends(get_current_user),
) -> VersionResponse:
    """
    獲取版本詳情

    Args:
        version: 版本號
        current_user: 當前用戶

    Returns:
        VersionResponse: 版本詳情響應

    Raises:
        HTTPException: 版本不存在或無權限時拋出異常
    """
    try:
        # 檢查權限
        await require_permissions(current_user, ["version:read"])

        # 獲取版本詳情
        version_data = version_service.get_version(version, current_user)

        if not version_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"版本 {version} 不存在"
            )

        # 構建響應
        api_version = APIVersion(**version_data)

        return VersionResponse(
            version=api_version,
            compatibility_info=None,  # 可以添加相容性信息
            migration_info=None,  # 可以添加遷移信息
            permissions={
                "read": True,
                "update": True,  # 實際應該檢查權限
                "delete": True,  # 實際應該檢查權限
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取版本詳情失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="獲取版本詳情失敗"
        )


@router.put(
    "/{version}",
    response_model=Dict[str, Any],
    summary="更新版本",
    description="更新指定版本的信息",
)
async def update_version(
    version: str = Path(..., description="版本號"),
    request: VersionUpdateRequest = ...,
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    更新版本

    Args:
        version: 版本號
        request: 更新請求
        current_user: 當前用戶

    Returns:
        Dict[str, Any]: 更新結果

    Raises:
        HTTPException: 更新失敗時拋出異常
    """
    try:
        # 檢查權限
        await require_permissions(current_user, ["version:update"])

        # 更新版本
        updated_version = version_service.update_version(version, request, current_user)

        if not updated_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"版本 {version} 不存在"
            )

        logger.info(f"用戶 {current_user} 更新版本成功: {version}")
        return {"success": True, "message": "版本更新成功", "data": updated_version}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新版本失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新版本失敗"
        )


@router.delete(
    "/{version}",
    response_model=Dict[str, Any],
    summary="刪除版本",
    description="刪除指定版本（軟刪除）",
)
async def delete_version(
    version: str = Path(..., description="版本號"),
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    刪除版本

    Args:
        version: 版本號
        current_user: 當前用戶

    Returns:
        Dict[str, Any]: 刪除結果

    Raises:
        HTTPException: 刪除失敗時拋出異常
    """
    try:
        # 檢查權限
        await require_permissions(current_user, ["version:delete"])

        # 刪除版本
        success = version_service.delete_version(version, current_user)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"版本 {version} 不存在或無法刪除",
            )

        logger.info(f"用戶 {current_user} 刪除版本成功: {version}")
        return {"success": True, "message": "版本刪除成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刪除版本失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="刪除版本失敗"
        )


@router.post(
    "/negotiate",
    response_model=VersionNegotiationResponse,
    summary="版本協商",
    description="根據客戶端需求協商最適合的 API 版本",
)
async def negotiate_version(
    request: VersionNegotiationRequest, current_user: str = Depends(get_current_user)
) -> VersionNegotiationResponse:
    """
    版本協商

    Args:
        request: 協商請求
        current_user: 當前用戶

    Returns:
        VersionNegotiationResponse: 協商結果

    Raises:
        HTTPException: 協商失敗時拋出異常
    """
    try:
        # 獲取可用版本列表
        available_versions = ["1.0.0", "1.1.0", "2.0.0"]  # 實際應該從服務獲取

        # 執行版本協商
        result = version_service.negotiate_version(request, available_versions)

        return VersionNegotiationResponse(**result)

    except Exception as e:
        logger.error(f"版本協商失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="版本協商失敗"
        )


@router.post(
    "/compatibility/check",
    response_model=CompatibilityCheckResponse,
    summary="相容性檢查",
    description="檢查兩個版本之間的相容性",
)
async def check_compatibility(
    source_version: str = Query(..., description="源版本"),
    target_version: str = Query(..., description="目標版本"),
    current_user: str = Depends(get_current_user),
) -> CompatibilityCheckResponse:
    """
    相容性檢查

    Args:
        source_version: 源版本
        target_version: 目標版本
        current_user: 當前用戶

    Returns:
        CompatibilityCheckResponse: 相容性檢查結果

    Raises:
        HTTPException: 檢查失敗時拋出異常
    """
    try:
        # 檢查權限
        await require_permissions(current_user, ["version:read"])

        # 執行相容性檢查
        result = version_service.check_compatibility(
            source_version, target_version, current_user
        )

        return CompatibilityCheckResponse(**result)

    except ValueError as e:
        logger.warning(f"相容性檢查參數錯誤: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"相容性檢查失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="相容性檢查失敗"
        )


# ==================== 遷移管理端點 ====================


@router.post(
    "/migrations",
    response_model=Dict[str, Any],
    summary="創建遷移計劃",
    description="創建版本遷移計劃",
)
async def create_migration_plan(
    source_version: str = Query(..., description="源版本"),
    target_version: str = Query(..., description="目標版本"),
    name: str = Query(..., description="遷移名稱"),
    description: Optional[str] = Query(None, description="遷移描述"),
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    創建遷移計劃

    Args:
        source_version: 源版本
        target_version: 目標版本
        name: 遷移名稱
        description: 遷移描述
        current_user: 當前用戶

    Returns:
        Dict[str, Any]: 遷移計劃

    Raises:
        HTTPException: 創建失敗時拋出異常
    """
    try:
        # 檢查權限
        await require_permissions(current_user, ["migration:create"])

        # 創建遷移計劃
        migration_plan = await migration_manager.create_migration_plan(
            source_version=source_version,
            target_version=target_version,
            name=name,
            description=description,
            created_by=current_user,
        )

        logger.info(
            f"用戶 {current_user} 創建遷移計劃成功: {migration_plan.migration_id}"
        )
        return {
            "success": True,
            "message": "遷移計劃創建成功",
            "data": migration_plan.model_dump(mode="json"),
        }

    except Exception as e:
        logger.error(f"創建遷移計劃失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="創建遷移計劃失敗"
        )


@router.post(
    "/migrations/{migration_id}/execute",
    response_model=Dict[str, Any],
    summary="執行遷移",
    description="執行指定的遷移計劃",
)
async def execute_migration(
    migration_id: str = Path(..., description="遷移 ID"),
    dry_run: bool = Query(False, description="是否為試運行"),
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    執行遷移

    Args:
        migration_id: 遷移 ID
        dry_run: 是否為試運行
        current_user: 當前用戶

    Returns:
        Dict[str, Any]: 執行結果

    Raises:
        HTTPException: 執行失敗時拋出異常
    """
    try:
        # 檢查權限
        await require_permissions(current_user, ["migration:execute"])

        # 執行遷移
        result = await migration_manager.execute_migration(migration_id, dry_run)

        logger.info(f"用戶 {current_user} 執行遷移: {migration_id}, 試運行: {dry_run}")
        return {
            "success": True,
            "message": "遷移執行完成" if not dry_run else "遷移試運行完成",
            "data": result,
        }

    except ValueError as e:
        logger.warning(f"執行遷移參數錯誤: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"執行遷移失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="執行遷移失敗"
        )


@router.post(
    "/migrations/{migration_id}/rollback",
    response_model=Dict[str, Any],
    summary="回滾遷移",
    description="回滾指定的遷移",
)
async def rollback_migration(
    migration_id: str = Path(..., description="遷移 ID"),
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    回滾遷移

    Args:
        migration_id: 遷移 ID
        current_user: 當前用戶

    Returns:
        Dict[str, Any]: 回滾結果

    Raises:
        HTTPException: 回滾失敗時拋出異常
    """
    try:
        # 檢查權限
        await require_permissions(current_user, ["migration:rollback"])

        # 回滾遷移
        result = await migration_manager.rollback_migration(migration_id)

        logger.info(f"用戶 {current_user} 回滾遷移: {migration_id}")
        return {"success": True, "message": "遷移回滾完成", "data": result}

    except ValueError as e:
        logger.warning(f"回滾遷移參數錯誤: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"回滾遷移失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="回滾遷移失敗"
        )


@router.get(
    "/migrations/{migration_id}/status",
    response_model=Dict[str, Any],
    summary="獲取遷移狀態",
    description="獲取指定遷移的狀態信息",
)
async def get_migration_status(
    migration_id: str = Path(..., description="遷移 ID"),
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    獲取遷移狀態

    Args:
        migration_id: 遷移 ID
        current_user: 當前用戶

    Returns:
        Dict[str, Any]: 遷移狀態

    Raises:
        HTTPException: 獲取失敗時拋出異常
    """
    try:
        # 檢查權限
        await require_permissions(current_user, ["migration:read"])

        # 獲取遷移狀態
        status_info = await migration_manager.get_migration_status(migration_id)

        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"遷移 {migration_id} 不存在",
            )

        return {"success": True, "data": status_info}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取遷移狀態失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="獲取遷移狀態失敗"
        )


@router.get(
    "/migrations",
    response_model=Dict[str, Any],
    summary="列出遷移記錄",
    description="列出遷移記錄，支援狀態篩選",
)
async def list_migrations(
    status_filter: Optional[str] = Query(None, description="狀態篩選"),
    limit: int = Query(50, ge=1, le=100, description="限制數量"),
    current_user: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    列出遷移記錄

    Args:
        status_filter: 狀態篩選
        limit: 限制數量
        current_user: 當前用戶

    Returns:
        Dict[str, Any]: 遷移記錄列表

    Raises:
        HTTPException: 查詢失敗時拋出異常
    """
    try:
        # 檢查權限
        await require_permissions(current_user, ["migration:read"])

        # 列出遷移記錄
        migrations = await migration_manager.list_migrations(
            status=status_filter, limit=limit
        )

        return {
            "success": True,
            "data": {"migrations": migrations, "total": len(migrations)},
        }

    except Exception as e:
        logger.error(f"列出遷移記錄失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="列出遷移記錄失敗"
        )
