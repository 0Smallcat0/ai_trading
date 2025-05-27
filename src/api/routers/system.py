"""系統管理路由 - 佔位符"""

from fastapi import APIRouter
from src.api.models.responses import APIResponse

router = APIRouter()


@router.get("/config", response_model=APIResponse)
async def get_system_config():
    return APIResponse(success=True, message="系統配置", data={"config": {}})
