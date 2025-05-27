"""日誌管理 API 路由

此模組提供日誌管理相關的 API 端點，包括：
- 日誌查詢和過濾
- 日誌分析報告
- 合規性日誌管理
- 敏感資料遮罩配置
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from src.logging.analyzer import LogAnalyzer
from src.logging.compliance import (
    ComplianceLogger,
    ComplianceEventType,
    ComplianceLevel,
)
from src.logging.data_masking import DataMasker, SensitiveDataType, MaskingStrategy


# 模擬依賴項（實際使用時需要實現）
def get_current_user():
    """模擬用戶認證依賴項"""
    return {"user_id": "demo_user", "username": "demo"}


class BaseResponse(BaseModel):
    """基礎響應模型"""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# 創建路由器
router = APIRouter(prefix="/api/v1/logging", tags=["日誌管理"])

# 初始化服務
log_analyzer = LogAnalyzer()
compliance_logger = ComplianceLogger()
data_masker = DataMasker()


# 請求模型
class LogQueryRequest(BaseModel):
    """日誌查詢請求"""

    category: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    level: Optional[str] = None
    keyword: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=1000)


class ComplianceEventRequest(BaseModel):
    """合規事件記錄請求"""

    event_type: ComplianceEventType
    level: ComplianceLevel
    description: str
    details: Optional[Dict[str, Any]] = None
    business_context: Optional[Dict[str, Any]] = None
    regulatory_context: Optional[Dict[str, Any]] = None


class MaskingRuleRequest(BaseModel):
    """遮罩規則請求"""

    name: str
    data_type: SensitiveDataType
    pattern: str
    strategy: MaskingStrategy
    field_names: List[str]
    description: str = ""


class MaskingTestRequest(BaseModel):
    """遮罩測試請求"""

    test_data: str
    rule_name: Optional[str] = None


# 響應模型
class LogQueryResponse(BaseResponse):
    """日誌查詢響應"""

    data: Dict[str, Any]


class AnalysisReportResponse(BaseResponse):
    """分析報告響應"""

    data: Dict[str, Any]


class ComplianceReportResponse(BaseResponse):
    """合規報告響應"""

    data: Dict[str, Any]


class MaskingRulesResponse(BaseResponse):
    """遮罩規則響應"""

    data: List[Dict[str, Any]]


class MaskingTestResponse(BaseResponse):
    """遮罩測試響應"""

    data: Dict[str, Any]


# API 端點
@router.get("/logs", response_model=LogQueryResponse)
async def query_logs(
    category: Optional[str] = Query(None, description="日誌類別"),
    start_time: Optional[datetime] = Query(None, description="開始時間"),
    end_time: Optional[datetime] = Query(None, description="結束時間"),
    level: Optional[str] = Query(None, description="日誌級別"),
    limit: int = Query(100, ge=1, le=1000, description="限制數量"),
    current_user: dict = Depends(get_current_user),
):
    """查詢日誌

    查詢系統日誌，支援多種過濾條件。
    """
    _ = current_user  # 用於權限驗證
    try:
        # 載入日誌
        logs_df = log_analyzer.load_logs(
            category=category,
            start_time=start_time,
            end_time=end_time,
            level=level,
            limit=limit,
        )

        # 轉換為字典列表
        logs = logs_df.to_dict("records") if not logs_df.empty else []

        # 統計信息
        stats = {
            "total_count": len(logs),
            "by_level": log_analyzer.count_logs_by_level(
                category, start_time, end_time
            ),
            "query_params": {
                "category": category,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
                "level": level,
                "limit": limit,
            },
        }

        return LogQueryResponse(
            success=True,
            message="日誌查詢成功",
            data={"logs": logs, "statistics": stats},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"日誌查詢失敗: {str(e)}") from e


@router.get("/analysis", response_model=AnalysisReportResponse)
async def generate_analysis_report(
    category: Optional[str] = Query(None, description="日誌類別"),
    start_time: Optional[datetime] = Query(None, description="開始時間"),
    end_time: Optional[datetime] = Query(None, description="結束時間"),
    current_user: dict = Depends(get_current_user),
):
    """生成日誌分析報告

    分析日誌數據並生成詳細的分析報告，包括異常檢測和建議。
    """
    _ = current_user  # 用於權限驗證
    try:
        # 設置預設時間範圍（最近24小時）
        if not end_time:
            end_time = datetime.now()
        if not start_time:
            start_time = end_time - timedelta(hours=24)

        # 生成分析報告
        report = log_analyzer.generate_analysis_report(
            category=category, start_time=start_time, end_time=end_time
        )

        return AnalysisReportResponse(
            success=True, message="分析報告生成成功", data=report
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"分析報告生成失敗: {str(e)}"
        ) from e


@router.post("/compliance/events")
async def log_compliance_event(
    request: ComplianceEventRequest, current_user: dict = Depends(get_current_user)
):
    """記錄合規事件。

    記錄符合法規要求的業務事件。
    """
    try:
        # 記錄合規事件
        event = compliance_logger.log_event(
            event_type=request.event_type,
            level=request.level,
            user_id=current_user.get("user_id", "unknown"),
            description=request.description,
            details=request.details,
            business_context=request.business_context,
            regulatory_context=request.regulatory_context,
        )

        return BaseResponse(
            success=True, message="合規事件記錄成功", data={"event_id": event.event_id}
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"合規事件記錄失敗: {str(e)}"
        ) from e


@router.get("/compliance/report", response_model=ComplianceReportResponse)
async def generate_compliance_report(
    start_date: datetime = Query(..., description="開始日期"),
    end_date: datetime = Query(..., description="結束日期"),
    report_type: str = Query("summary", description="報告類型"),
    current_user: dict = Depends(get_current_user),
):
    """生成合規報告。

    生成指定時間範圍內的合規性報告。
    """
    _ = current_user  # 用於權限驗證
    try:
        # 生成合規報告
        report = compliance_logger.generate_compliance_report(
            start_date=start_date, end_date=end_date, report_type=report_type
        )

        return ComplianceReportResponse(
            success=True, message="合規報告生成成功", data=report
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"合規報告生成失敗: {str(e)}"
        ) from e


@router.get("/masking/rules", response_model=MaskingRulesResponse)
async def get_masking_rules(current_user: dict = Depends(get_current_user)):
    """獲取遮罩規則

    獲取當前配置的所有敏感資料遮罩規則。
    """
    _ = current_user  # 用於權限驗證
    try:
        rules = data_masker.get_rules()
        statistics = data_masker.get_statistics()

        return MaskingRulesResponse(
            success=True,
            message="遮罩規則獲取成功",
            data={"rules": rules, "statistics": statistics},
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"遮罩規則獲取失敗: {str(e)}"
        ) from e


@router.post("/masking/rules")
async def add_masking_rule(
    request: MaskingRuleRequest, current_user: dict = Depends(get_current_user)
):
    """添加遮罩規則。

    添加新的敏感資料遮罩規則。
    """
    _ = current_user  # 用於權限驗證
    try:
        data_masker.add_custom_rule(
            name=request.name,
            data_type=request.data_type,
            pattern=request.pattern,
            strategy=request.strategy,
            field_names=request.field_names,
            description=request.description,
        )

        return BaseResponse(success=True, message="遮罩規則添加成功")

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"遮罩規則添加失敗: {str(e)}"
        ) from e


@router.post("/masking/test", response_model=MaskingTestResponse)
async def test_masking(
    request: MaskingTestRequest, current_user: dict = Depends(get_current_user)
):
    """測試遮罩效果

    測試敏感資料遮罩的效果。
    """
    _ = current_user  # 用於權限驗證
    try:
        result = data_masker.test_masking(
            test_data=request.test_data, rule_name=request.rule_name
        )

        return MaskingTestResponse(success=True, message="遮罩測試完成", data=result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"遮罩測試失敗: {str(e)}") from e


@router.delete("/masking/rules/{rule_name}")
async def remove_masking_rule(
    rule_name: str, current_user: dict = Depends(get_current_user)
):
    """移除遮罩規則。

    移除指定的敏感資料遮罩規則。
    """
    _ = current_user  # 用於權限驗證
    try:
        data_masker.remove_rule(rule_name)

        return BaseResponse(success=True, message="遮罩規則移除成功")

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"遮罩規則移除失敗: {str(e)}"
        ) from e


@router.put("/masking/rules/{rule_name}/toggle")
async def toggle_masking_rule(
    rule_name: str,
    enable: bool = Query(..., description="是否啟用"),
    current_user: dict = Depends(get_current_user),
):
    """切換遮罩規則狀態。

    啟用或停用指定的遮罩規則。
    """
    _ = current_user  # 用於權限驗證
    try:
        if enable:
            data_masker.enable_rule(rule_name)
            message = "遮罩規則已啟用"
        else:
            data_masker.disable_rule(rule_name)
            message = "遮罩規則已停用"

        return BaseResponse(success=True, message=message)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"遮罩規則狀態切換失敗: {str(e)}"
        ) from e
