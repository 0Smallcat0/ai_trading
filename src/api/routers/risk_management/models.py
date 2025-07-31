"""風險管理系統模型

此模組定義風險管理系統相關的請求和響應模型。
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field, validator


# ==================== 請求模型 ====================


class RiskParametersRequest(BaseModel):
    """風險參數設定請求模型"""

    # 停損/停利設定
    stop_loss_type: str = Field(..., description="停損類型 (percent/atr/trailing)")
    stop_loss_value: float = Field(..., gt=0, le=0.5, description="停損值")
    take_profit_type: str = Field(
        ..., description="停利類型 (percent/target/risk_reward)"
    )
    take_profit_value: float = Field(..., gt=0, le=1.0, description="停利值")

    # 資金管理設定
    max_position_size: float = Field(
        default=0.1, gt=0, le=1.0, description="最大單一部位比例"
    )
    max_portfolio_risk: float = Field(
        default=0.02, gt=0, le=0.1, description="最大投資組合風險"
    )
    max_daily_loss: float = Field(default=0.05, gt=0, le=0.2, description="最大日損失")
    max_drawdown: float = Field(default=0.15, gt=0, le=0.5, description="最大回撤限制")

    # VaR 設定
    var_confidence_level: float = Field(
        default=0.95, ge=0.9, le=0.99, description="VaR 信心水準"
    )
    var_time_horizon: int = Field(
        default=1, ge=1, le=30, description="VaR 時間範圍（天）"
    )
    var_method: str = Field(default="historical", description="VaR 計算方法")

    # 相關性設定
    max_correlation: float = Field(
        default=0.7, ge=0.1, le=1.0, description="最大相關性"
    )
    correlation_lookback: int = Field(
        default=60, ge=30, le=252, description="相關性回看期間"
    )

    # 集中度設定
    max_sector_exposure: float = Field(
        default=0.3, gt=0, le=1.0, description="最大行業曝險"
    )
    max_single_stock: float = Field(
        default=0.15, gt=0, le=1.0, description="最大單一股票比例"
    )

    @validator("stop_loss_type")
    def validate_stop_loss_type(cls, v):  # pylint: disable=no-self-argument
        """驗證停損類型"""
        allowed_types = ["percent", "atr", "trailing", "support_resistance"]
        if v not in allowed_types:
            raise ValueError(f'停損類型必須是: {", ".join(allowed_types)}')
        return v

    @validator("take_profit_type")
    def validate_take_profit_type(cls, v):  # pylint: disable=no-self-argument
        """驗證停利類型"""
        allowed_types = ["percent", "target", "risk_reward", "trailing"]
        if v not in allowed_types:
            raise ValueError(f'停利類型必須是: {", ".join(allowed_types)}')
        return v

    @validator("var_method")
    def validate_var_method(cls, v):  # pylint: disable=no-self-argument
        """驗證 VaR 方法"""
        allowed_methods = ["historical", "parametric", "monte_carlo"]
        if v not in allowed_methods:
            raise ValueError(f'VaR 方法必須是: {", ".join(allowed_methods)}')
        return v


class RiskControlToggleRequest(BaseModel):
    """風控機制切換請求模型"""

    control_name: str = Field(..., description="風控機制名稱")
    enabled: bool = Field(..., description="是否啟用")
    reason: Optional[str] = Field(default=None, description="操作原因")

    @validator("control_name")
    def validate_control_name(cls, v):  # pylint: disable=no-self-argument
        """驗證風控機制名稱"""
        allowed_controls = [
            "stop_loss",
            "take_profit",
            "position_limit",
            "var_monitoring",
            "drawdown_protection",
            "correlation_check",
            "sector_limit",
            "emergency_stop",
        ]
        if v not in allowed_controls:
            raise ValueError(f'風控機制名稱必須是: {", ".join(allowed_controls)}')
        return v


class AlertAcknowledgeRequest(BaseModel):
    """警報確認請求模型"""

    alert_ids: List[str] = Field(..., min_items=1, description="警報 ID 列表")
    acknowledged_by: str = Field(..., description="確認人")
    notes: Optional[str] = Field(default=None, description="確認備註")


# ==================== 響應模型 ====================


class RiskParameters(BaseModel):
    """風險參數響應模型"""

    # 停損/停利設定
    stop_loss_type: str = Field(..., description="停損類型")
    stop_loss_value: float = Field(..., description="停損值")
    take_profit_type: str = Field(..., description="停利類型")
    take_profit_value: float = Field(..., description="停利值")

    # 資金管理設定
    max_position_size: float = Field(..., description="最大單一部位比例")
    max_portfolio_risk: float = Field(..., description="最大投資組合風險")
    max_daily_loss: float = Field(..., description="最大日損失")
    max_drawdown: float = Field(..., description="最大回撤限制")

    # VaR 設定
    var_confidence_level: float = Field(..., description="VaR 信心水準")
    var_time_horizon: int = Field(..., description="VaR 時間範圍")
    var_method: str = Field(..., description="VaR 計算方法")

    # 相關性設定
    max_correlation: float = Field(..., description="最大相關性")
    correlation_lookback: int = Field(..., description="相關性回看期間")

    # 集中度設定
    max_sector_exposure: float = Field(..., description="最大行業曝險")
    max_single_stock: float = Field(..., description="最大單一股票比例")

    # 元數據
    updated_at: datetime = Field(..., description="更新時間")
    updated_by: str = Field(..., description="更新人")


class RiskMetrics(BaseModel):
    """風險指標響應模型"""

    # 基本風險指標
    portfolio_value: float = Field(..., description="投資組合價值")
    cash_amount: float = Field(..., description="現金金額")
    invested_amount: float = Field(..., description="投資金額")
    leverage_ratio: float = Field(..., description="槓桿比率")

    # 收益風險指標
    daily_pnl: float = Field(..., description="日損益")
    daily_pnl_percent: float = Field(..., description="日損益百分比")
    total_return: float = Field(..., description="總回報率")
    annualized_return: float = Field(..., description="年化回報率")

    # 風險指標
    volatility: float = Field(..., description="波動率")
    sharpe_ratio: float = Field(..., description="夏普比率")
    max_drawdown: float = Field(..., description="最大回撤")
    current_drawdown: float = Field(..., description="當前回撤")

    # VaR 指標
    var_95: float = Field(..., description="95% VaR")
    var_99: float = Field(..., description="99% VaR")
    cvar_95: float = Field(..., description="95% CVaR")
    cvar_99: float = Field(..., description="99% CVaR")

    # 集中度風險
    concentration_risk: float = Field(..., description="集中度風險")
    sector_exposure: Dict[str, float] = Field(..., description="行業曝險")
    top_holdings: List[Dict[str, Any]] = Field(..., description="主要持倉")

    # 相關性風險
    avg_correlation: float = Field(..., description="平均相關性")
    max_correlation: float = Field(..., description="最大相關性")
    correlation_risk_score: float = Field(..., description="相關性風險評分")

    # 更新時間
    calculated_at: datetime = Field(..., description="計算時間")


class RiskControlStatus(BaseModel):
    """風控機制狀態響應模型"""

    control_name: str = Field(..., description="風控機制名稱")
    enabled: bool = Field(..., description="是否啟用")
    status: str = Field(..., description="狀態")
    last_triggered: Optional[datetime] = Field(default=None, description="最後觸發時間")
    trigger_count: int = Field(..., description="觸發次數")
    description: str = Field(..., description="描述")


class RiskAlert(BaseModel):
    """風險警報響應模型"""

    id: str = Field(..., description="警報 ID")
    alert_type: str = Field(..., description="警報類型")
    severity: str = Field(..., description="嚴重程度")
    title: str = Field(..., description="警報標題")
    message: str = Field(..., description="警報訊息")
    symbol: Optional[str] = Field(default=None, description="相關股票代碼")
    portfolio_id: Optional[str] = Field(default=None, description="相關投資組合 ID")
    metric_value: Optional[float] = Field(default=None, description="指標值")
    threshold_value: Optional[float] = Field(default=None, description="閾值")
    created_at: datetime = Field(..., description="創建時間")
    acknowledged: bool = Field(..., description="是否已確認")
    acknowledged_at: Optional[datetime] = Field(default=None, description="確認時間")
    acknowledged_by: Optional[str] = Field(default=None, description="確認人")
    resolved: bool = Field(..., description="是否已解決")
    resolved_at: Optional[datetime] = Field(default=None, description="解決時間")
