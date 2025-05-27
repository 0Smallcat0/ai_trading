"""報表查詢系統模型

此模組定義報表查詢系統相關的請求和響應模型。
"""

from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union

from pydantic import BaseModel, Field, validator


# ==================== 基礎請求模型 ====================


class ReportRequest(BaseModel):
    """基礎報表請求模型"""

    start_date: date = Field(..., description="開始日期")
    end_date: date = Field(..., description="結束日期")
    format: str = Field(default="json", description="報表格式 (json/csv/excel/pdf)")
    timezone: str = Field(default="Asia/Taipei", description="時區")

    @validator("end_date")
    def validate_date_range(cls, v, values):  # pylint: disable=no-self-argument
        """驗證日期範圍"""
        if "start_date" in values and v < values["start_date"]:
            raise ValueError("結束日期不能早於開始日期")
        return v

    @validator("format")
    def validate_format(cls, v):  # pylint: disable=no-self-argument
        """驗證報表格式"""
        allowed_formats = ["json", "csv", "excel", "pdf"]
        if v.lower() not in allowed_formats:
            raise ValueError(f'報表格式必須是: {", ".join(allowed_formats)}')
        return v.lower()


class PerformanceReportRequest(ReportRequest):
    """績效報表請求模型"""

    portfolio_ids: Optional[List[str]] = Field(default=None, description="投資組合 ID 列表")
    benchmark: Optional[str] = Field(default="TAIEX", description="基準指數")
    include_benchmark: bool = Field(default=True, description="是否包含基準比較")
    metrics: Optional[List[str]] = Field(default=None, description="指定績效指標")

    @validator("metrics")
    def validate_metrics(cls, v):  # pylint: disable=no-self-argument
        """驗證績效指標"""
        if v is not None:
            allowed_metrics = [
                "total_return",
                "annualized_return",
                "volatility",
                "sharpe_ratio",
                "max_drawdown",
                "calmar_ratio",
                "sortino_ratio",
                "alpha",
                "beta",
            ]
            invalid_metrics = [m for m in v if m not in allowed_metrics]
            if invalid_metrics:
                raise ValueError(f'無效的績效指標: {", ".join(invalid_metrics)}')
        return v


class PortfolioReportRequest(ReportRequest):
    """投資組合報表請求模型"""

    portfolio_ids: Optional[List[str]] = Field(default=None, description="投資組合 ID 列表")
    include_positions: bool = Field(default=True, description="是否包含持倉詳情")
    include_transactions: bool = Field(default=False, description="是否包含交易記錄")
    groupby: Optional[str] = Field(default=None, description="分組方式")

    @validator("groupby")
    def validate_groupby(cls, v):  # pylint: disable=no-self-argument
        """驗證分組方式"""
        if v is not None:
            allowed_groupby = ["sector", "industry", "market_cap", "country", "currency"]
            if v not in allowed_groupby:
                raise ValueError(f'分組方式必須是: {", ".join(allowed_groupby)}')
        return v


class RiskReportRequest(ReportRequest):
    """風險報表請求模型"""

    portfolio_ids: Optional[List[str]] = Field(default=None, description="投資組合 ID 列表")
    risk_metrics: Optional[List[str]] = Field(default=None, description="風險指標")
    confidence_levels: List[float] = Field(
        default=[0.95, 0.99], description="信心水準列表"
    )
    include_stress_test: bool = Field(default=False, description="是否包含壓力測試")

    @validator("risk_metrics")
    def validate_risk_metrics(cls, v):  # pylint: disable=no-self-argument
        """驗證風險指標"""
        if v is not None:
            allowed_metrics = [
                "var",
                "cvar",
                "volatility",
                "beta",
                "correlation",
                "concentration",
                "liquidity_risk",
            ]
            invalid_metrics = [m for m in v if m not in allowed_metrics]
            if invalid_metrics:
                raise ValueError(f'無效的風險指標: {", ".join(invalid_metrics)}')
        return v

    @validator("confidence_levels")
    def validate_confidence_levels(cls, v):  # pylint: disable=no-self-argument
        """驗證信心水準"""
        for level in v:
            if not 0.5 <= level <= 0.999:
                raise ValueError("信心水準必須在 0.5 到 0.999 之間")
        return v


class TradingReportRequest(ReportRequest):
    """交易報表請求模型"""

    portfolio_ids: Optional[List[str]] = Field(default=None, description="投資組合 ID 列表")
    symbols: Optional[List[str]] = Field(default=None, description="股票代碼列表")
    order_types: Optional[List[str]] = Field(default=None, description="訂單類型")
    include_costs: bool = Field(default=True, description="是否包含交易成本")
    include_performance: bool = Field(default=True, description="是否包含交易績效")

    @validator("order_types")
    def validate_order_types(cls, v):  # pylint: disable=no-self-argument
        """驗證訂單類型"""
        if v is not None:
            allowed_types = ["market", "limit", "stop", "stop_limit", "trailing_stop"]
            invalid_types = [t for t in v if t not in allowed_types]
            if invalid_types:
                raise ValueError(f'無效的訂單類型: {", ".join(invalid_types)}')
        return v


class AnalyticsReportRequest(ReportRequest):
    """分析報表請求模型"""

    analysis_type: str = Field(..., description="分析類型")
    symbols: Optional[List[str]] = Field(default=None, description="股票代碼列表")
    factors: Optional[List[str]] = Field(default=None, description="分析因子")
    include_predictions: bool = Field(default=False, description="是否包含預測")

    @validator("analysis_type")
    def validate_analysis_type(cls, v):  # pylint: disable=no-self-argument
        """驗證分析類型"""
        allowed_types = [
            "factor_analysis",
            "correlation_analysis",
            "sector_analysis",
            "attribution_analysis",
            "style_analysis",
        ]
        if v not in allowed_types:
            raise ValueError(f'分析類型必須是: {", ".join(allowed_types)}')
        return v


# ==================== 響應模型 ====================


class ReportResponse(BaseModel):
    """基礎報表響應模型"""

    report_id: str = Field(..., description="報表 ID")
    report_type: str = Field(..., description="報表類型")
    generated_at: datetime = Field(..., description="生成時間")
    start_date: date = Field(..., description="開始日期")
    end_date: date = Field(..., description="結束日期")
    format: str = Field(..., description="報表格式")
    file_url: Optional[str] = Field(default=None, description="檔案下載 URL")
    status: str = Field(..., description="報表狀態")


class PerformanceReport(BaseModel):
    """績效報表響應模型"""

    portfolio_performance: Dict[str, Any] = Field(..., description="投資組合績效")
    benchmark_performance: Optional[Dict[str, Any]] = Field(
        default=None, description="基準績效"
    )
    relative_performance: Optional[Dict[str, Any]] = Field(
        default=None, description="相對績效"
    )
    period_returns: List[Dict[str, Any]] = Field(..., description="期間回報")
    risk_metrics: Dict[str, float] = Field(..., description="風險指標")
    attribution_analysis: Optional[Dict[str, Any]] = Field(
        default=None, description="歸因分析"
    )


class PortfolioReport(BaseModel):
    """投資組合報表響應模型"""

    portfolio_summary: Dict[str, Any] = Field(..., description="投資組合摘要")
    asset_allocation: Dict[str, float] = Field(..., description="資產配置")
    sector_allocation: Dict[str, float] = Field(..., description="行業配置")
    top_holdings: List[Dict[str, Any]] = Field(..., description="主要持倉")
    performance_summary: Dict[str, Any] = Field(..., description="績效摘要")
    transactions: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="交易記錄"
    )


class RiskReport(BaseModel):
    """風險報表響應模型"""

    risk_summary: Dict[str, Any] = Field(..., description="風險摘要")
    var_analysis: Dict[str, float] = Field(..., description="VaR 分析")
    stress_test_results: Optional[Dict[str, Any]] = Field(
        default=None, description="壓力測試結果"
    )
    concentration_analysis: Dict[str, Any] = Field(..., description="集中度分析")
    correlation_matrix: Optional[List[List[float]]] = Field(
        default=None, description="相關性矩陣"
    )
    risk_decomposition: Dict[str, Any] = Field(..., description="風險分解")


class TradingReport(BaseModel):
    """交易報表響應模型"""

    trading_summary: Dict[str, Any] = Field(..., description="交易摘要")
    order_statistics: Dict[str, Any] = Field(..., description="訂單統計")
    execution_analysis: Dict[str, Any] = Field(..., description="執行分析")
    cost_analysis: Dict[str, Any] = Field(..., description="成本分析")
    performance_attribution: Dict[str, Any] = Field(..., description="績效歸因")
    trade_details: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="交易詳情"
    )


class AnalyticsReport(BaseModel):
    """分析報表響應模型"""

    analysis_summary: Dict[str, Any] = Field(..., description="分析摘要")
    factor_exposures: Optional[Dict[str, float]] = Field(
        default=None, description="因子曝險"
    )
    correlation_analysis: Optional[Dict[str, Any]] = Field(
        default=None, description="相關性分析"
    )
    sector_analysis: Optional[Dict[str, Any]] = Field(
        default=None, description="行業分析"
    )
    predictions: Optional[Dict[str, Any]] = Field(default=None, description="預測結果")
    recommendations: Optional[List[str]] = Field(default=None, description="建議")
