"""
資料管理路由

此模組實現資料管理相關的 API 端點，包括資料來源管理、資料更新、
資料品質監控和資料清理等功能。
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, validator

from src.api.models.responses import APIResponse, COMMON_RESPONSES

logger = logging.getLogger(__name__)
router = APIRouter()


# 請求模型
class DataSourceConfig(BaseModel):
    """資料來源配置模型

    此模型定義了資料來源的配置參數，包括名稱、類型、配置參數等。

    Attributes:
        name: 資料來源名稱，長度限制 1-100 字符
        type: 資料來源類型，必須是預定義的類型之一
        config: 配置參數字典，包含連接和認證信息
        enabled: 是否啟用此資料來源
        update_frequency: 資料更新頻率

    Example:
        >>> config = DataSourceConfig(
        ...     name="Yahoo Finance",
        ...     type="yahoo",
        ...     config={"api_key": "xxx", "timeout": 30},
        ...     enabled=True,
        ...     update_frequency="daily"
        ... )
    """

    name: str = Field(..., min_length=1, max_length=100, description="資料來源名稱")
    type: str = Field(..., description="資料來源類型")
    config: Dict[str, Any] = Field(..., description="配置參數")
    enabled: bool = Field(default=True, description="是否啟用")
    update_frequency: str = Field(default="daily", description="更新頻率")

    @validator("type")
    def validate_type(cls, v):  # pylint: disable=no-self-argument
        """驗證資料來源類型

        Args:
            v: 待驗證的類型值

        Returns:
            str: 驗證通過的類型值

        Raises:
            ValueError: 當類型不在允許列表中時
        """
        allowed_types = ["yahoo", "twse", "mcp", "csv", "database"]
        if v not in allowed_types:
            raise ValueError(f'資料來源類型必須是: {", ".join(allowed_types)}')
        return v

    @validator("update_frequency")
    def validate_frequency(cls, v):  # pylint: disable=no-self-argument
        """驗證更新頻率

        Args:
            v: 待驗證的頻率值

        Returns:
            str: 驗證通過的頻率值

        Raises:
            ValueError: 當頻率不在允許列表中時
        """
        allowed_frequencies = ["realtime", "minute", "hourly", "daily", "weekly"]
        if v not in allowed_frequencies:
            raise ValueError(f'更新頻率必須是: {", ".join(allowed_frequencies)}')
        return v


class DataUpdateRequest(BaseModel):
    """資料更新請求模型

    此模型定義了資料更新請求的參數，支援指定資料來源、股票代碼和時間範圍。

    Attributes:
        source_names: 指定的資料來源名稱列表，為空時更新所有來源
        symbols: 指定的股票代碼列表，為空時更新所有股票
        start_date: 更新的開始日期
        end_date: 更新的結束日期
        force_update: 是否強制更新，忽略快取

    Example:
        >>> request = DataUpdateRequest(
        ...     source_names=["yahoo", "twse"],
        ...     symbols=["2330", "2317"],
        ...     start_date=datetime(2024, 1, 1),
        ...     force_update=True
        ... )
    """

    source_names: Optional[List[str]] = Field(
        default=None, description="指定更新的資料來源"
    )
    symbols: Optional[List[str]] = Field(default=None, description="指定更新的股票代碼")
    start_date: Optional[datetime] = Field(default=None, description="開始日期")
    end_date: Optional[datetime] = Field(default=None, description="結束日期")
    force_update: bool = Field(default=False, description="是否強制更新")

    @validator("symbols")
    def validate_symbols(cls, v):  # pylint: disable=no-self-argument
        """驗證股票代碼列表

        Args:
            v: 待驗證的股票代碼列表

        Returns:
            List[str]: 驗證通過的股票代碼列表

        Raises:
            ValueError: 當股票代碼格式無效時
        """
        if v is not None:
            for symbol in v:
                if not symbol or len(symbol.strip()) < 2:
                    raise ValueError(f"無效的股票代碼: {symbol}")
        return v


class DataCleaningRequest(BaseModel):
    """資料清理請求模型

    此模型定義了資料清理請求的參數，包括清理規則和目標資料範圍。

    Attributes:
        symbols: 需要清理的股票代碼列表
        cleaning_rules: 清理規則列表，定義要執行的清理操作
        start_date: 清理的開始日期
        end_date: 清理的結束日期

    Example:
        >>> request = DataCleaningRequest(
        ...     symbols=["2330", "2317"],
        ...     cleaning_rules=["remove_duplicates", "fill_missing_values"],
        ...     start_date=datetime(2024, 1, 1)
        ... )
    """

    symbols: List[str] = Field(..., description="股票代碼列表")
    cleaning_rules: List[str] = Field(..., description="清理規則")
    start_date: Optional[datetime] = Field(default=None, description="開始日期")
    end_date: Optional[datetime] = Field(default=None, description="結束日期")

    @validator("cleaning_rules")
    def validate_cleaning_rules(cls, v):  # pylint: disable=no-self-argument
        """驗證清理規則列表

        Args:
            v: 待驗證的清理規則列表

        Returns:
            List[str]: 驗證通過的清理規則列表

        Raises:
            ValueError: 當清理規則不在允許列表中時
        """
        allowed_rules = [
            "remove_duplicates",
            "fill_missing_values",
            "remove_outliers",
            "normalize_prices",
            "validate_volumes",
            "fix_splits",
        ]
        for rule in v:
            if rule not in allowed_rules:
                raise ValueError(f'清理規則必須是: {", ".join(allowed_rules)}')
        return v


# 響應模型
class DataSourceInfo(BaseModel):
    """資料來源資訊模型

    此模型定義了資料來源的詳細資訊，用於 API 回應。

    Attributes:
        id: 資料來源的唯一識別碼
        name: 資料來源名稱
        type: 資料來源類型
        status: 當前狀態（active, inactive, error）
        last_update: 最後更新時間
        record_count: 記錄總數
        enabled: 是否啟用
        config: 配置參數（敏感信息已遮蔽）
    """

    id: str = Field(..., description="資料來源 ID")
    name: str = Field(..., description="資料來源名稱")
    type: str = Field(..., description="資料來源類型")
    status: str = Field(..., description="狀態")
    last_update: Optional[datetime] = Field(default=None, description="最後更新時間")
    record_count: int = Field(default=0, description="記錄數量")
    enabled: bool = Field(..., description="是否啟用")
    config: Dict[str, Any] = Field(..., description="配置參數")


class DataQualityReport(BaseModel):
    """資料品質報告模型

    此模型定義了資料品質分析的結果，包含各種品質指標和問題列表。

    Attributes:
        symbol: 股票代碼
        total_records: 總記錄數
        missing_data_count: 缺失資料數量
        duplicate_count: 重複資料數量
        outlier_count: 異常值數量
        quality_score: 品質評分（0-100）
        issues: 發現的問題列表

    Example:
        >>> report = DataQualityReport(
        ...     symbol="2330",
        ...     total_records=1000,
        ...     missing_data_count=5,
        ...     quality_score=95.5,
        ...     issues=["少量缺失值"]
        ... )
    """

    symbol: str = Field(..., description="股票代碼")
    total_records: int = Field(..., description="總記錄數")
    missing_data_count: int = Field(..., description="缺失資料數量")
    duplicate_count: int = Field(..., description="重複資料數量")
    outlier_count: int = Field(..., description="異常值數量")
    quality_score: float = Field(..., description="品質評分")
    issues: List[str] = Field(..., description="問題列表")


# 模擬資料服務（實際應用中應該連接真實的資料庫和服務）
class MockDataService:
    """模擬資料管理服務

    此類別提供模擬的資料管理功能，用於開發和測試階段。
    在生產環境中應該替換為真實的資料庫和服務連接。

    Attributes:
        data_sources: 資料來源列表，包含各種資料來源的配置信息

    Note:
        這是一個模擬服務，不應在生產環境中使用
    """

    def __init__(self):
        """初始化模擬資料服務

        設定預設的資料來源列表，包含 Yahoo Finance 和台灣證券交易所。
        """
        self.data_sources = [
            {
                "id": "yahoo_finance",
                "name": "Yahoo Finance",
                "type": "yahoo",
                "status": "active",
                "last_update": datetime.now(),
                "record_count": 15000,
                "enabled": True,
                "config": {"api_key": "***", "rate_limit": 100},
            },
            {
                "id": "twse_data",
                "name": "台灣證券交易所",
                "type": "twse",
                "status": "active",
                "last_update": datetime.now(),
                "record_count": 8500,
                "enabled": True,
                "config": {"endpoint": "https://www.twse.com.tw/", "timeout": 30},
            },
        ]

    async def get_data_sources(self, enabled_only: bool = False):
        """獲取資料來源列表

        Args:
            enabled_only: 是否只返回啟用的資料來源

        Returns:
            List[Dict]: 資料來源列表
        """
        if enabled_only:
            return [source for source in self.data_sources if source["enabled"]]
        return self.data_sources

    async def get_data_source(self, source_id: str):
        """獲取單個資料來源

        Args:
            source_id: 資料來源 ID

        Returns:
            Dict: 資料來源資訊，如果不存在則返回 None
        """
        for source in self.data_sources:
            if source["id"] == source_id:
                return source
        return None

    async def create_data_source(self, source_config: dict):
        """創建資料來源

        Args:
            source_config: 資料來源配置字典，包含所有必要參數

        Returns:
            str: 新創建的資料來源 ID
        """
        source_type = source_config["type"]
        source_id = f"{source_type}_{len(self.data_sources) + 1}"
        new_source = {
            "id": source_id,
            "name": source_config["name"],
            "type": source_type,
            "status": "inactive",
            "last_update": None,
            "record_count": 0,
            "enabled": source_config.get("enabled", True),
            "config": source_config["config"],
            "update_frequency": source_config.get("update_frequency", "daily"),
        }
        self.data_sources.append(new_source)
        return source_id


# 初始化服務
data_service = MockDataService()


@router.get(
    "/sources",
    response_model=APIResponse[List[DataSourceInfo]],
    responses=COMMON_RESPONSES,
    summary="獲取資料來源列表",
    description="獲取所有已配置的資料來源及其狀態資訊",
)
async def get_data_sources(
    enabled_only: bool = Query(default=False, description="僅顯示啟用的資料來源")
):
    """獲取資料來源列表

    此端點返回系統中所有已配置的資料來源列表，包含其狀態和配置資訊。

    Args:
        enabled_only: 是否只返回啟用的資料來源

    Returns:
        APIResponse[List[DataSourceInfo]]: 包含資料來源列表的 API 回應

    Raises:
        HTTPException: 當獲取資料來源列表失敗時

    Example:
        GET /api/data/sources?enabled_only=true
    """
    try:
        sources = await data_service.get_data_sources(enabled_only=enabled_only)

        source_list = [
            DataSourceInfo(
                id=source["id"],
                name=source["name"],
                type=source["type"],
                status=source["status"],
                last_update=source.get("last_update"),
                record_count=source.get("record_count", 0),
                enabled=source["enabled"],
                config=source["config"],
            )
            for source in sources
        ]

        return APIResponse(
            success=True, message="資料來源列表獲取成功", data=source_list
        )

    except Exception as e:
        logger.error("獲取資料來源列表失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="獲取資料來源列表失敗",
        ) from e


@router.post(
    "/sources",
    response_model=APIResponse[DataSourceInfo],
    responses=COMMON_RESPONSES,
    summary="創建資料來源",
    description="創建新的資料來源配置",
)
async def create_data_source(source_config: DataSourceConfig):
    """創建資料來源"""
    try:
        # 檢查資料來源名稱是否已存在
        existing_sources = await data_service.get_data_sources()
        if any(source["name"] == source_config.name for source in existing_sources):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="資料來源名稱已存在"
            )

        # 創建資料來源
        config_dict = {
            "name": source_config.name,
            "type": source_config.type,
            "config": source_config.config,
            "enabled": source_config.enabled,
            "update_frequency": source_config.update_frequency,
        }
        source_id = await data_service.create_data_source(config_dict)

        # 獲取創建的資料來源資訊
        source_info = await data_service.get_data_source(source_id)

        return APIResponse(
            success=True, message="資料來源創建成功", data=DataSourceInfo(**source_info)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("創建資料來源失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="創建資料來源失敗"
        ) from e


@router.get(
    "/sources/{source_id}",
    response_model=APIResponse[DataSourceInfo],
    responses=COMMON_RESPONSES,
    summary="獲取資料來源詳情",
    description="根據 ID 獲取特定資料來源的詳細資訊",
)
async def get_data_source(source_id: str):
    """獲取資料來源詳情"""
    try:
        source_info = await data_service.get_data_source(source_id)

        if not source_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="資料來源不存在"
            )

        return APIResponse(
            success=True,
            message="資料來源詳情獲取成功",
            data=DataSourceInfo(**source_info),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取資料來源詳情失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="獲取資料來源詳情失敗",
        ) from e


@router.post(
    "/update",
    response_model=APIResponse[Dict[str, Any]],
    responses=COMMON_RESPONSES,
    summary="更新資料",
    description="手動觸發資料更新任務",
)
async def update_data(update_request: DataUpdateRequest):
    """更新資料"""
    try:
        # 模擬資料更新過程
        update_result = {
            "task_id": f"update_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "status": "started",
            "sources": update_request.source_names or ["all"],
            "symbols": update_request.symbols or ["all"],
            "start_date": update_request.start_date,
            "end_date": update_request.end_date,
            "force_update": update_request.force_update,
            "estimated_duration": "5-10 分鐘",
        }

        return APIResponse(
            success=True, message="資料更新任務已啟動", data=update_result
        )

    except Exception as e:
        logger.error("啟動資料更新失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="啟動資料更新失敗"
        ) from e


@router.get(
    "/quality-report",
    response_model=APIResponse[List[DataQualityReport]],
    responses=COMMON_RESPONSES,
    summary="獲取資料品質報告",
    description="獲取資料品質分析報告",
)
async def get_data_quality_report(
    symbols: Optional[str] = Query(
        default=None, description="股票代碼，多個用逗號分隔"
    ),
    start_date: Optional[datetime] = Query(default=None, description="開始日期"),
    end_date: Optional[datetime] = Query(default=None, description="結束日期"),
):
    """獲取資料品質報告

    此端點返回指定股票代碼的資料品質分析報告，包含缺失值、重複值、異常值等統計。

    Args:
        symbols: 股票代碼列表，用逗號分隔，為空時使用預設股票
        start_date: 分析的開始日期，用於限制分析範圍
        end_date: 分析的結束日期，用於限制分析範圍

    Returns:
        APIResponse[List[DataQualityReport]]: 包含品質報告列表的 API 回應

    Raises:
        HTTPException: 當獲取品質報告失敗時

    Example:
        GET /api/data/quality-report?symbols=2330,2317&start_date=2024-01-01
    """
    try:
        # 模擬資料品質報告
        symbol_list = symbols.split(",") if symbols else ["2330", "2317", "2454"]

        # 記錄查詢參數（用於日誌和未來實作）
        logger.info(
            "生成品質報告 - 股票: %s, 期間: %s 至 %s", symbol_list, start_date, end_date
        )

        quality_reports = []
        for symbol in symbol_list:
            # 根據日期範圍調整記錄數（模擬實際邏輯）
            base_records = 1000
            if start_date and end_date:
                days_diff = (end_date - start_date).days
                base_records = max(100, min(days_diff * 10, 2000))

            report = DataQualityReport(
                symbol=symbol.strip(),
                total_records=base_records,
                missing_data_count=5,
                duplicate_count=2,
                outlier_count=8,
                quality_score=95.5,
                issues=(
                    ["少量缺失值", "檢測到異常值"] if symbol.strip() == "2330" else []
                ),
            )
            quality_reports.append(report)

        return APIResponse(
            success=True, message="資料品質報告獲取成功", data=quality_reports
        )

    except Exception as e:
        logger.error("獲取資料品質報告失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="獲取資料品質報告失敗",
        ) from e


@router.post(
    "/clean",
    response_model=APIResponse[Dict[str, Any]],
    responses=COMMON_RESPONSES,
    summary="清理資料",
    description="執行資料清理任務",
)
async def clean_data(cleaning_request: DataCleaningRequest):
    """清理資料"""
    try:
        # 模擬資料清理過程
        cleaning_result = {
            "task_id": f"clean_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "status": "started",
            "symbols": cleaning_request.symbols,
            "cleaning_rules": cleaning_request.cleaning_rules,
            "start_date": cleaning_request.start_date,
            "end_date": cleaning_request.end_date,
            "estimated_duration": "3-5 分鐘",
        }

        return APIResponse(
            success=True, message="資料清理任務已啟動", data=cleaning_result
        )

    except Exception as e:
        logger.error("啟動資料清理失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="啟動資料清理失敗"
        ) from e
