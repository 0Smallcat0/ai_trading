"""
報表相關的 Pydantic 模型

此模組定義了報表查詢與視覺化 API 的請求和響應模型。
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum

from pydantic import BaseModel, Field, validator


class TimeRangeEnum(str, Enum):
    """時間範圍枚舉"""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class ReportTypeEnum(str, Enum):
    """報表類型枚舉"""

    TRADING_SUMMARY = "trading_summary"
    PORTFOLIO_PERFORMANCE = "portfolio_performance"
    RISK_ANALYSIS = "risk_analysis"
    STRATEGY_BACKTEST = "strategy_backtest"
    SYSTEM_MONITORING = "system_monitoring"
    CUSTOM = "custom"


class TemplateStatusEnum(str, Enum):
    """模板狀態枚舉"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    ARCHIVED = "archived"


class TemplateVisibilityEnum(str, Enum):
    """模板可見性枚舉"""

    PUBLIC = "public"
    PRIVATE = "private"
    SHARED = "shared"


class ScheduleFrequencyEnum(str, Enum):
    """排程頻率枚舉"""

    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class ScheduleStatusEnum(str, Enum):
    """排程狀態枚舉"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionStatusEnum(str, Enum):
    """執行狀態枚舉"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ExportFormatEnum(str, Enum):
    """匯出格式枚舉"""

    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"


class ChartTypeEnum(str, Enum):
    """圖表類型枚舉"""

    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    CANDLESTICK = "candlestick"
    HISTOGRAM = "histogram"
    BOX = "box"


class ChartLibraryEnum(str, Enum):
    """圖表庫枚舉"""

    PLOTLY = "plotly"
    CHARTJS = "chartjs"
    ECHARTS = "echarts"
    D3JS = "d3js"


# ==================== 請求模型 ====================


class BaseReportRequest(BaseModel):
    """基礎報表請求模型"""

    start_date: datetime = Field(..., description="開始日期")
    end_date: datetime = Field(..., description="結束日期")
    time_range: TimeRangeEnum = Field(
        default=TimeRangeEnum.DAILY, description="時間範圍"
    )

    @validator("end_date")
    @classmethod
    def validate_date_range(cls, v, values):
        """驗證日期範圍"""
        if "start_date" in values and v <= values["start_date"]:
            raise ValueError("結束日期必須大於開始日期")
        return v


class TradingSummaryRequest(BaseReportRequest):
    """交易摘要報表請求模型"""

    symbols: Optional[List[str]] = Field(default=None, description="股票代碼篩選")
    strategies: Optional[List[str]] = Field(default=None, description="策略篩選")
    portfolios: Optional[List[str]] = Field(default=None, description="投資組合篩選")
    group_by: Optional[str] = Field(default=None, description="分組方式")

    @validator("symbols")
    @classmethod
    def validate_symbols(cls, v):
        """驗證股票代碼"""
        if v is not None and len(v) > 50:
            raise ValueError("股票代碼數量不能超過50個")
        return v


class PortfolioPerformanceRequest(BaseReportRequest):
    """投資組合績效報表請求模型"""

    portfolio_ids: Optional[List[str]] = Field(
        default=None, description="投資組合ID列表"
    )
    benchmark_symbol: str = Field(default="^TWII", description="基準指數代碼")
    include_risk_metrics: bool = Field(default=True, description="是否包含風險指標")
    include_attribution: bool = Field(default=False, description="是否包含績效歸因")


class RiskAnalysisRequest(BaseReportRequest):
    """風險分析報表請求模型"""

    portfolio_ids: Optional[List[str]] = Field(
        default=None, description="投資組合ID列表"
    )
    confidence_levels: List[float] = Field(default=[0.95, 0.99], description="信賴區間")
    risk_types: List[str] = Field(
        default=["market", "credit", "liquidity", "operational"], description="風險類型"
    )
    include_stress_test: bool = Field(default=False, description="是否包含壓力測試")

    @validator("confidence_levels")
    @classmethod
    def validate_confidence_levels(cls, v):
        """驗證信賴區間"""
        for level in v:
            if not 0 < level < 1:
                raise ValueError("信賴區間必須在0和1之間")
        return v


class StrategyBacktestRequest(BaseReportRequest):
    """策略回測報表請求模型"""

    strategy_ids: Optional[List[str]] = Field(default=None, description="策略ID列表")
    include_sensitivity: bool = Field(default=False, description="是否包含敏感性分析")
    include_optimization: bool = Field(default=False, description="是否包含最佳化結果")
    benchmark_strategy: Optional[str] = Field(default=None, description="基準策略")


class SystemMonitoringRequest(BaseReportRequest):
    """系統監控報表請求模型"""

    metric_types: List[str] = Field(
        default=["system", "trading", "api"], description="指標類型"
    )
    include_alerts: bool = Field(default=True, description="是否包含警報統計")
    include_performance: bool = Field(default=True, description="是否包含效能分析")


class CustomReportRequest(BaseModel):
    """自定義報表請求模型"""

    name: str = Field(..., min_length=1, max_length=100, description="報表名稱")
    description: Optional[str] = Field(
        default=None, max_length=500, description="報表描述"
    )
    data_sources: List[str] = Field(..., min_items=1, description="數據來源")
    metrics: List[str] = Field(..., min_items=1, description="指標列表")
    filters: Dict[str, Any] = Field(default_factory=dict, description="篩選條件")
    grouping: Optional[Dict[str, Any]] = Field(default=None, description="分組設定")
    time_range: TimeRangeEnum = Field(
        default=TimeRangeEnum.DAILY, description="時間範圍"
    )
    chart_configs: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="圖表配置"
    )
    schedule: Optional[Dict[str, Any]] = Field(default=None, description="排程設定")


class ExportRequest(BaseModel):
    """報表匯出請求模型"""

    report_id: str = Field(..., description="報表ID")
    format: ExportFormatEnum = Field(..., description="匯出格式")
    include_charts: bool = Field(default=True, description="是否包含圖表")
    include_raw_data: bool = Field(default=False, description="是否包含原始數據")
    template_id: Optional[str] = Field(default=None, description="模板ID")
    custom_settings: Optional[Dict[str, Any]] = Field(
        default=None, description="自定義設定"
    )


class ChartDataRequest(BaseModel):
    """圖表數據請求模型"""

    chart_type: ChartTypeEnum = Field(..., description="圖表類型")
    library: ChartLibraryEnum = Field(
        default=ChartLibraryEnum.PLOTLY, description="圖表庫"
    )
    data_source: str = Field(..., description="數據來源")
    filters: Dict[str, Any] = Field(default_factory=dict, description="篩選條件")
    config: Optional[Dict[str, Any]] = Field(default=None, description="圖表配置")


# ==================== 報表模板請求模型 ====================


class ReportTemplateCreateRequest(BaseModel):
    """創建報表模板請求模型"""

    name: str = Field(..., min_length=1, max_length=100, description="模板名稱")
    description: Optional[str] = Field(
        default=None, max_length=500, description="模板描述"
    )
    report_type: ReportTypeEnum = Field(..., description="報表類型")
    template_config: Dict[str, Any] = Field(..., description="模板配置")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="模板參數")
    chart_configs: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="圖表配置"
    )
    layout_config: Optional[Dict[str, Any]] = Field(
        default=None, description="佈局配置"
    )
    visibility: TemplateVisibilityEnum = Field(
        default=TemplateVisibilityEnum.PRIVATE, description="可見性"
    )
    tags: Optional[List[str]] = Field(default=None, description="標籤")

    @validator("name")
    @classmethod
    def validate_name(cls, v):
        """驗證模板名稱"""
        if not v.strip():
            raise ValueError("模板名稱不能為空")
        return v.strip()

    @validator("tags")
    @classmethod
    def validate_tags(cls, v):
        """驗證標籤"""
        if v is not None and len(v) > 10:
            raise ValueError("標籤數量不能超過10個")
        return v


class ReportTemplateUpdateRequest(BaseModel):
    """更新報表模板請求模型"""

    name: Optional[str] = Field(
        default=None, min_length=1, max_length=100, description="模板名稱"
    )
    description: Optional[str] = Field(
        default=None, max_length=500, description="模板描述"
    )
    template_config: Optional[Dict[str, Any]] = Field(
        default=None, description="模板配置"
    )
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="模板參數")
    chart_configs: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="圖表配置"
    )
    layout_config: Optional[Dict[str, Any]] = Field(
        default=None, description="佈局配置"
    )
    status: Optional[TemplateStatusEnum] = Field(default=None, description="模板狀態")
    visibility: Optional[TemplateVisibilityEnum] = Field(
        default=None, description="可見性"
    )
    tags: Optional[List[str]] = Field(default=None, description="標籤")

    @validator("name")
    @classmethod
    def validate_name(cls, v):
        """驗證模板名稱"""
        if v is not None and not v.strip():
            raise ValueError("模板名稱不能為空")
        return v.strip() if v else v

    @validator("tags")
    @classmethod
    def validate_tags(cls, v):
        """驗證標籤"""
        if v is not None and len(v) > 10:
            raise ValueError("標籤數量不能超過10個")
        return v


class ReportTemplateListRequest(BaseModel):
    """查詢報表模板列表請求模型"""

    page: int = Field(default=1, ge=1, description="頁碼")
    page_size: int = Field(default=20, ge=1, le=100, description="每頁數量")
    search: Optional[str] = Field(
        default=None, max_length=100, description="搜尋關鍵字"
    )
    report_type: Optional[ReportTypeEnum] = Field(
        default=None, description="報表類型篩選"
    )
    status: Optional[TemplateStatusEnum] = Field(default=None, description="狀態篩選")
    visibility: Optional[TemplateVisibilityEnum] = Field(
        default=None, description="可見性篩選"
    )
    tags: Optional[List[str]] = Field(default=None, description="標籤篩選")
    sort_by: str = Field(default="created_at", description="排序欄位")
    sort_order: str = Field(
        default="desc", pattern="^(asc|desc)$", description="排序方向"
    )

    @validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v):
        """驗證排序欄位"""
        allowed_fields = [
            "name",
            "created_at",
            "updated_at",
            "report_type",
            "status",
            "visibility",
            "usage_count",
        ]
        if v not in allowed_fields:
            raise ValueError(f'排序欄位必須是: {", ".join(allowed_fields)}')
        return v


# ==================== 響應模型 ====================


class TradingMetrics(BaseModel):
    """交易指標響應模型"""

    total_trades: int = Field(..., description="總交易次數")
    total_volume: float = Field(..., description="總交易量")
    total_amount: float = Field(..., description="總成交金額")
    total_commission: float = Field(..., description="總手續費")
    total_pnl: float = Field(..., description="總損益")
    realized_pnl: float = Field(..., description="已實現損益")
    unrealized_pnl: float = Field(..., description="未實現損益")
    win_rate: float = Field(..., description="勝率")
    profit_factor: float = Field(..., description="獲利因子")
    avg_win: float = Field(..., description="平均獲利")
    avg_loss: float = Field(..., description="平均虧損")
    max_win: float = Field(..., description="最大獲利")
    max_loss: float = Field(..., description="最大虧損")
    avg_holding_period: float = Field(..., description="平均持倉天數")


class PerformanceMetrics(BaseModel):
    """績效指標響應模型"""

    total_return: float = Field(..., description="總報酬率")
    annualized_return: float = Field(..., description="年化報酬率")
    volatility: float = Field(..., description="波動率")
    sharpe_ratio: float = Field(..., description="夏普比率")
    sortino_ratio: float = Field(..., description="索提諾比率")
    calmar_ratio: float = Field(..., description="卡瑪比率")
    max_drawdown: float = Field(..., description="最大回撤")
    max_drawdown_duration: int = Field(..., description="最大回撤持續天數")
    var_95: float = Field(..., description="95% VaR")
    var_99: float = Field(..., description="99% VaR")
    cvar_95: float = Field(..., description="95% CVaR")
    cvar_99: float = Field(..., description="99% CVaR")
    beta: Optional[float] = Field(default=None, description="貝塔係數")
    alpha: Optional[float] = Field(default=None, description="阿爾法係數")
    information_ratio: Optional[float] = Field(default=None, description="資訊比率")
    tracking_error: Optional[float] = Field(default=None, description="追蹤誤差")


class RiskMetrics(BaseModel):
    """風險指標響應模型"""

    market_risk: float = Field(..., description="市場風險")
    credit_risk: float = Field(..., description="信用風險")
    liquidity_risk: float = Field(..., description="流動性風險")
    operational_risk: float = Field(..., description="操作風險")
    concentration_risk: float = Field(..., description="集中度風險")
    correlation_risk: float = Field(..., description="相關性風險")
    stress_test_results: Optional[Dict[str, float]] = Field(
        default=None, description="壓力測試結果"
    )


class ChartData(BaseModel):
    """圖表數據響應模型"""

    chart_type: str = Field(..., description="圖表類型")
    library: str = Field(..., description="圖表庫")
    data: Dict[str, Any] = Field(..., description="圖表數據")
    config: Dict[str, Any] = Field(..., description="圖表配置")
    layout: Optional[Dict[str, Any]] = Field(default=None, description="佈局配置")


class ReportSummary(BaseModel):
    """報表摘要響應模型"""

    report_id: str = Field(..., description="報表ID")
    report_type: str = Field(..., description="報表類型")
    name: str = Field(..., description="報表名稱")
    description: Optional[str] = Field(default=None, description="報表描述")
    generated_at: datetime = Field(..., description="生成時間")
    period_start: datetime = Field(..., description="統計期間開始")
    period_end: datetime = Field(..., description="統計期間結束")
    status: str = Field(..., description="報表狀態")
    file_size: Optional[int] = Field(default=None, description="檔案大小（bytes）")
    download_url: Optional[str] = Field(default=None, description="下載連結")


class TradingSummaryResponse(BaseModel):
    """交易摘要報表響應模型"""

    summary: ReportSummary = Field(..., description="報表摘要")
    metrics: TradingMetrics = Field(..., description="交易指標")
    daily_stats: List[Dict[str, Any]] = Field(..., description="每日統計")
    symbol_breakdown: List[Dict[str, Any]] = Field(..., description="股票分解")
    strategy_breakdown: List[Dict[str, Any]] = Field(..., description="策略分解")
    charts: List[ChartData] = Field(..., description="圖表數據")


class PortfolioPerformanceResponse(BaseModel):
    """投資組合績效報表響應模型"""

    summary: ReportSummary = Field(..., description="報表摘要")
    performance: PerformanceMetrics = Field(..., description="績效指標")
    benchmark_comparison: Dict[str, Any] = Field(..., description="基準比較")
    asset_allocation: List[Dict[str, Any]] = Field(..., description="資產配置")
    attribution_analysis: Optional[Dict[str, Any]] = Field(
        default=None, description="歸因分析"
    )
    charts: List[ChartData] = Field(..., description="圖表數據")


class RiskAnalysisResponse(BaseModel):
    """風險分析報表響應模型"""

    summary: ReportSummary = Field(..., description="報表摘要")
    risk_metrics: RiskMetrics = Field(..., description="風險指標")
    var_analysis: Dict[str, Any] = Field(..., description="VaR 分析")
    correlation_matrix: List[List[float]] = Field(..., description="相關性矩陣")
    stress_test: Optional[Dict[str, Any]] = Field(default=None, description="壓力測試")
    charts: List[ChartData] = Field(..., description="圖表數據")


class StrategyBacktestResponse(BaseModel):
    """策略回測報表響應模型"""

    summary: ReportSummary = Field(..., description="報表摘要")
    strategy_performance: List[Dict[str, Any]] = Field(..., description="策略績效")
    comparison_analysis: Dict[str, Any] = Field(..., description="比較分析")
    sensitivity_analysis: Optional[Dict[str, Any]] = Field(
        default=None, description="敏感性分析"
    )
    optimization_results: Optional[Dict[str, Any]] = Field(
        default=None, description="最佳化結果"
    )
    charts: List[ChartData] = Field(..., description="圖表數據")


class SystemMonitoringResponse(BaseModel):
    """系統監控報表響應模型"""

    summary: ReportSummary = Field(..., description="報表摘要")
    resource_usage: Dict[str, Any] = Field(..., description="資源使用統計")
    performance_metrics: Dict[str, Any] = Field(..., description="效能指標")
    error_analysis: Dict[str, Any] = Field(..., description="錯誤分析")
    availability_report: Dict[str, Any] = Field(..., description="可用性報告")
    alert_statistics: Optional[Dict[str, Any]] = Field(
        default=None, description="警報統計"
    )
    charts: List[ChartData] = Field(..., description="圖表數據")


class CustomReportResponse(BaseModel):
    """自定義報表響應模型"""

    summary: ReportSummary = Field(..., description="報表摘要")
    data: List[Dict[str, Any]] = Field(..., description="報表數據")
    aggregations: Dict[str, Any] = Field(..., description="聚合統計")
    charts: List[ChartData] = Field(..., description="圖表數據")
    metadata: Dict[str, Any] = Field(..., description="元數據")


class ExportResponse(BaseModel):
    """報表匯出響應模型"""

    export_id: str = Field(..., description="匯出ID")
    status: str = Field(..., description="匯出狀態")
    format: str = Field(..., description="匯出格式")
    file_size: Optional[int] = Field(default=None, description="檔案大小")
    download_url: Optional[str] = Field(default=None, description="下載連結")
    expires_at: Optional[datetime] = Field(default=None, description="過期時間")
    created_at: datetime = Field(..., description="創建時間")


# ==================== 報表模板響應模型 ====================


class ReportTemplate(BaseModel):
    """報表模板響應模型"""

    template_id: str = Field(..., description="模板ID")
    name: str = Field(..., description="模板名稱")
    description: Optional[str] = Field(default=None, description="模板描述")
    report_type: str = Field(..., description="報表類型")
    template_config: Dict[str, Any] = Field(..., description="模板配置")
    parameters: Dict[str, Any] = Field(..., description="模板參數")
    chart_configs: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="圖表配置"
    )
    layout_config: Optional[Dict[str, Any]] = Field(
        default=None, description="佈局配置"
    )
    status: str = Field(..., description="模板狀態")
    visibility: str = Field(..., description="可見性")
    tags: Optional[List[str]] = Field(default=None, description="標籤")
    version: str = Field(..., description="版本號")
    usage_count: int = Field(default=0, description="使用次數")
    created_by: str = Field(..., description="創建者")
    created_at: datetime = Field(..., description="創建時間")
    updated_at: datetime = Field(..., description="更新時間")
    last_used_at: Optional[datetime] = Field(default=None, description="最後使用時間")


class ReportTemplateResponse(BaseModel):
    """單個報表模板響應模型"""

    template: ReportTemplate = Field(..., description="模板詳情")
    preview_data: Optional[Dict[str, Any]] = Field(default=None, description="預覽數據")
    permissions: Dict[str, bool] = Field(..., description="權限信息")


class ReportTemplateListResponse(BaseModel):
    """報表模板列表響應模型"""

    templates: List[ReportTemplate] = Field(..., description="模板列表")
    total: int = Field(..., description="總數量")
    page: int = Field(..., description="當前頁碼")
    page_size: int = Field(..., description="每頁數量")
    total_pages: int = Field(..., description="總頁數")
    has_next: bool = Field(..., description="是否有下一頁")
    has_prev: bool = Field(..., description="是否有上一頁")


class TemplatePreviewRequest(BaseModel):
    """模板預覽請求模型"""

    template_id: str = Field(..., description="模板ID")
    preview_data: Optional[Dict[str, Any]] = Field(default=None, description="預覽數據")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="參數覆蓋")


class TemplatePreviewResponse(BaseModel):
    """模板預覽響應模型"""

    template_id: str = Field(..., description="模板ID")
    preview_html: str = Field(..., description="預覽HTML")
    charts: List[ChartData] = Field(..., description="圖表數據")
    metadata: Dict[str, Any] = Field(..., description="元數據")


# ==================== 報表排程請求模型 ====================


class ReportScheduleCreateRequest(BaseModel):
    """創建報表排程請求模型"""

    name: str = Field(..., min_length=1, max_length=100, description="排程名稱")
    description: Optional[str] = Field(
        default=None, max_length=500, description="排程描述"
    )
    report_type: ReportTypeEnum = Field(..., description="報表類型")
    template_id: Optional[str] = Field(default=None, description="報表模板ID")
    frequency: ScheduleFrequencyEnum = Field(..., description="執行頻率")
    cron_expression: Optional[str] = Field(
        default=None, description="Cron 表達式（自定義頻率時使用）"
    )
    start_time: datetime = Field(..., description="開始時間")
    end_time: Optional[datetime] = Field(default=None, description="結束時間")
    timezone: str = Field(default="Asia/Taipei", description="時區")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="報表參數")
    notification_settings: Optional[Dict[str, Any]] = Field(
        default=None, description="通知設定"
    )
    output_format: ExportFormatEnum = Field(
        default=ExportFormatEnum.PDF, description="輸出格式"
    )
    is_enabled: bool = Field(default=True, description="是否啟用")
    tags: Optional[List[str]] = Field(default=None, description="標籤")

    @validator("name")
    @classmethod
    def validate_name(cls, v):
        """驗證排程名稱"""
        if not v.strip():
            raise ValueError("排程名稱不能為空")
        return v.strip()

    @validator("cron_expression")
    @classmethod
    def validate_cron_expression(cls, v, values):
        """驗證 Cron 表達式"""
        if values.get("frequency") == ScheduleFrequencyEnum.CUSTOM and not v:
            raise ValueError("自定義頻率時必須提供 Cron 表達式")
        return v

    @validator("end_time")
    @classmethod
    def validate_end_time(cls, v, values):
        """驗證結束時間"""
        if v and "start_time" in values and v <= values["start_time"]:
            raise ValueError("結束時間必須大於開始時間")
        return v

    @validator("tags")
    @classmethod
    def validate_tags(cls, v):
        """驗證標籤"""
        if v is not None and len(v) > 10:
            raise ValueError("標籤數量不能超過10個")
        return v


class ReportScheduleUpdateRequest(BaseModel):
    """更新報表排程請求模型"""

    name: Optional[str] = Field(
        default=None, min_length=1, max_length=100, description="排程名稱"
    )
    description: Optional[str] = Field(
        default=None, max_length=500, description="排程描述"
    )
    template_id: Optional[str] = Field(default=None, description="報表模板ID")
    frequency: Optional[ScheduleFrequencyEnum] = Field(
        default=None, description="執行頻率"
    )
    cron_expression: Optional[str] = Field(default=None, description="Cron 表達式")
    start_time: Optional[datetime] = Field(default=None, description="開始時間")
    end_time: Optional[datetime] = Field(default=None, description="結束時間")
    timezone: Optional[str] = Field(default=None, description="時區")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="報表參數")
    notification_settings: Optional[Dict[str, Any]] = Field(
        default=None, description="通知設定"
    )
    output_format: Optional[ExportFormatEnum] = Field(
        default=None, description="輸出格式"
    )
    status: Optional[ScheduleStatusEnum] = Field(default=None, description="排程狀態")
    is_enabled: Optional[bool] = Field(default=None, description="是否啟用")
    tags: Optional[List[str]] = Field(default=None, description="標籤")

    @validator("name")
    @classmethod
    def validate_name(cls, v):
        """驗證排程名稱"""
        if v is not None and not v.strip():
            raise ValueError("排程名稱不能為空")
        return v.strip() if v else v

    @validator("end_time")
    @classmethod
    def validate_end_time(cls, v, values):
        """驗證結束時間"""
        if (
            v
            and "start_time" in values
            and values["start_time"]
            and v <= values["start_time"]
        ):
            raise ValueError("結束時間必須大於開始時間")
        return v

    @validator("tags")
    @classmethod
    def validate_tags(cls, v):
        """驗證標籤"""
        if v is not None and len(v) > 10:
            raise ValueError("標籤數量不能超過10個")
        return v


class ReportScheduleListRequest(BaseModel):
    """查詢報表排程列表請求模型"""

    page: int = Field(default=1, ge=1, description="頁碼")
    page_size: int = Field(default=20, ge=1, le=100, description="每頁數量")
    search: Optional[str] = Field(
        default=None, max_length=100, description="搜尋關鍵字"
    )
    report_type: Optional[ReportTypeEnum] = Field(
        default=None, description="報表類型篩選"
    )
    status: Optional[ScheduleStatusEnum] = Field(default=None, description="狀態篩選")
    frequency: Optional[ScheduleFrequencyEnum] = Field(
        default=None, description="頻率篩選"
    )
    is_enabled: Optional[bool] = Field(default=None, description="啟用狀態篩選")
    tags: Optional[List[str]] = Field(default=None, description="標籤篩選")
    sort_by: str = Field(default="created_at", description="排序欄位")
    sort_order: str = Field(
        default="desc", pattern="^(asc|desc)$", description="排序方向"
    )

    @validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v):
        """驗證排序欄位"""
        allowed_fields = [
            "name",
            "created_at",
            "updated_at",
            "report_type",
            "status",
            "frequency",
            "next_run_time",
            "last_run_time",
        ]
        if v not in allowed_fields:
            raise ValueError(f'排序欄位必須是: {", ".join(allowed_fields)}')
        return v


# ==================== 報表排程響應模型 ====================


class ReportSchedule(BaseModel):
    """報表排程響應模型"""

    schedule_id: str = Field(..., description="排程ID")
    name: str = Field(..., description="排程名稱")
    description: Optional[str] = Field(default=None, description="排程描述")
    report_type: str = Field(..., description="報表類型")
    template_id: Optional[str] = Field(default=None, description="報表模板ID")
    template_name: Optional[str] = Field(default=None, description="報表模板名稱")
    frequency: str = Field(..., description="執行頻率")
    cron_expression: Optional[str] = Field(default=None, description="Cron 表達式")
    start_time: datetime = Field(..., description="開始時間")
    end_time: Optional[datetime] = Field(default=None, description="結束時間")
    timezone: str = Field(..., description="時區")
    parameters: Dict[str, Any] = Field(..., description="報表參數")
    notification_settings: Optional[Dict[str, Any]] = Field(
        default=None, description="通知設定"
    )
    output_format: str = Field(..., description="輸出格式")
    status: str = Field(..., description="排程狀態")
    is_enabled: bool = Field(..., description="是否啟用")
    tags: Optional[List[str]] = Field(default=None, description="標籤")

    # 執行統計
    total_executions: int = Field(default=0, description="總執行次數")
    successful_executions: int = Field(default=0, description="成功執行次數")
    failed_executions: int = Field(default=0, description="失敗執行次數")
    last_execution_time: Optional[datetime] = Field(
        default=None, description="最後執行時間"
    )
    last_execution_status: Optional[str] = Field(
        default=None, description="最後執行狀態"
    )
    next_execution_time: Optional[datetime] = Field(
        default=None, description="下次執行時間"
    )

    # 元數據
    created_by: str = Field(..., description="創建者")
    created_at: datetime = Field(..., description="創建時間")
    updated_at: datetime = Field(..., description="更新時間")


class ReportScheduleResponse(BaseModel):
    """單個報表排程響應模型"""

    schedule: ReportSchedule = Field(..., description="排程詳情")
    execution_history: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="執行歷史"
    )
    permissions: Dict[str, bool] = Field(..., description="權限信息")


class ReportScheduleListResponse(BaseModel):
    """報表排程列表響應模型"""

    schedules: List[ReportSchedule] = Field(..., description="排程列表")
    total: int = Field(..., description="總數量")
    page: int = Field(..., description="當前頁碼")
    page_size: int = Field(..., description="每頁數量")
    total_pages: int = Field(..., description="總頁數")
    has_next: bool = Field(..., description="是否有下一頁")
    has_prev: bool = Field(..., description="是否有上一頁")


class ScheduleExecution(BaseModel):
    """排程執行記錄模型"""

    execution_id: str = Field(..., description="執行ID")
    schedule_id: str = Field(..., description="排程ID")
    schedule_name: str = Field(..., description="排程名稱")
    report_type: str = Field(..., description="報表類型")
    status: str = Field(..., description="執行狀態")
    start_time: datetime = Field(..., description="開始時間")
    end_time: Optional[datetime] = Field(default=None, description="結束時間")
    duration: Optional[float] = Field(default=None, description="執行時長（秒）")

    # 執行結果
    report_id: Optional[str] = Field(default=None, description="生成的報表ID")
    output_file_path: Optional[str] = Field(default=None, description="輸出檔案路徑")
    file_size: Optional[int] = Field(default=None, description="檔案大小（bytes）")
    download_url: Optional[str] = Field(default=None, description="下載連結")

    # 錯誤信息
    error_message: Optional[str] = Field(default=None, description="錯誤訊息")
    error_details: Optional[Dict[str, Any]] = Field(
        default=None, description="錯誤詳情"
    )

    # 通知狀態
    notification_sent: bool = Field(default=False, description="是否已發送通知")
    notification_status: Optional[str] = Field(default=None, description="通知狀態")

    created_at: datetime = Field(..., description="創建時間")


class ScheduleExecutionListResponse(BaseModel):
    """排程執行歷史列表響應模型"""

    executions: List[ScheduleExecution] = Field(..., description="執行記錄列表")
    total: int = Field(..., description="總數量")
    page: int = Field(..., description="當前頁碼")
    page_size: int = Field(..., description="每頁數量")
    total_pages: int = Field(..., description="總頁數")
    has_next: bool = Field(..., description="是否有下一頁")
    has_prev: bool = Field(..., description="是否有上一頁")


class ScheduleExecutionResponse(BaseModel):
    """手動執行排程響應模型"""

    execution_id: str = Field(..., description="執行ID")
    schedule_id: str = Field(..., description="排程ID")
    status: str = Field(..., description="執行狀態")
    message: str = Field(..., description="執行訊息")
    estimated_completion_time: Optional[datetime] = Field(
        default=None, description="預計完成時間"
    )
    progress_url: Optional[str] = Field(default=None, description="進度查詢URL")
    created_at: datetime = Field(..., description="創建時間")
