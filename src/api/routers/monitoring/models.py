"""監控系統共用模型

此模組定義了監控系統中使用的所有 Pydantic 模型，包括請求模型和響應模型。
"""

import logging
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


# ==================== 請求模型 ====================


class AlertRuleRequest(BaseModel):
    """警報規則創建請求模型

    此模型定義了創建警報規則時需要的所有參數。

    Attributes:
        name: 警報規則名稱
        description: 警報規則描述
        metric_type: 監控指標類型
        threshold_type: 閾值類型
        threshold_value: 閾值
        comparison_operator: 比較運算符
        severity: 警報嚴重程度
        notification_channels: 通知渠道列表
        enabled: 是否啟用
        suppression_duration: 抑制時間（秒）

    Example:
        >>> rule = AlertRuleRequest(
        ...     name="CPU 使用率警報",
        ...     metric_type="cpu_usage",
        ...     threshold_type="percentage",
        ...     threshold_value=80.0,
        ...     comparison_operator=">",
        ...     severity="WARNING",
        ...     notification_channels=["email", "webhook"]
        ... )
    """
    name: str = Field(..., min_length=1, max_length=100, description="警報規則名稱")
    description: Optional[str] = Field(default=None, max_length=500, description="警報規則描述")
    metric_type: str = Field(..., description="監控指標類型")
    threshold_type: str = Field(..., description="閾值類型")
    threshold_value: float = Field(..., description="閾值")
    comparison_operator: str = Field(..., description="比較運算符")
    severity: str = Field(..., description="警報嚴重程度")
    notification_channels: List[str] = Field(..., min_items=1, description="通知渠道")
    enabled: bool = Field(default=True, description="是否啟用")
    suppression_duration: int = Field(default=300, ge=60, le=3600, description="抑制時間（秒）")

    @validator('metric_type')
    def validate_metric_type(cls, v):  # pylint: disable=no-self-argument
        """驗證監控指標類型

        Args:
            v: 待驗證的監控指標類型

        Returns:
            str: 驗證通過的監控指標類型

        Raises:
            ValueError: 當監控指標類型不在允許列表中時
        """
        allowed_types = [
            'cpu_usage', 'memory_usage', 'disk_usage', 'network_io',
            'api_latency', 'api_error_rate', 'trading_volume', 'order_success_rate',
            'active_connections', 'queue_length', 'cache_hit_rate'
        ]
        if v not in allowed_types:
            raise ValueError(f'監控指標類型必須是: {", ".join(allowed_types)}')
        return v

    @validator('threshold_type')
    def validate_threshold_type(cls, v):  # pylint: disable=no-self-argument
        """驗證閾值類型

        Args:
            v: 待驗證的閾值類型

        Returns:
            str: 驗證通過的閾值類型

        Raises:
            ValueError: 當閾值類型不在允許列表中時
        """
        allowed_types = ['absolute', 'percentage', 'rate_of_change']
        if v not in allowed_types:
            raise ValueError(f'閾值類型必須是: {", ".join(allowed_types)}')
        return v

    @validator('comparison_operator')
    def validate_comparison_operator(cls, v):  # pylint: disable=no-self-argument
        """驗證比較運算符

        Args:
            v: 待驗證的比較運算符

        Returns:
            str: 驗證通過的比較運算符

        Raises:
            ValueError: 當比較運算符不在允許列表中時
        """
        allowed_operators = ['>', '>=', '<', '<=', '==', '!=']
        if v not in allowed_operators:
            raise ValueError(f'比較運算符必須是: {", ".join(allowed_operators)}')
        return v

    @validator('severity')
    def validate_severity(cls, v):  # pylint: disable=no-self-argument
        """驗證警報嚴重程度

        Args:
            v: 待驗證的警報嚴重程度

        Returns:
            str: 驗證通過的警報嚴重程度

        Raises:
            ValueError: 當警報嚴重程度不在允許列表中時
        """
        allowed_severities = ['INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_severities:
            raise ValueError(f'警報嚴重程度必須是: {", ".join(allowed_severities)}')
        return v.upper()

    @validator('notification_channels')
    def validate_notification_channels(cls, v):  # pylint: disable=no-self-argument
        """驗證通知渠道

        Args:
            v: 待驗證的通知渠道列表

        Returns:
            List[str]: 驗證通過的通知渠道列表

        Raises:
            ValueError: 當通知渠道不在允許列表中時
        """
        allowed_channels = ['email', 'webhook', 'system', 'sms']
        for channel in v:
            if channel not in allowed_channels:
                raise ValueError(f'通知渠道必須是: {", ".join(allowed_channels)}')
        return v


class LogQueryRequest(BaseModel):
    """日誌查詢請求模型

    此模型定義了查詢日誌時需要的參數。

    Attributes:
        start_time: 開始時間
        end_time: 結束時間
        log_level: 日誌級別
        module: 模組名稱
        keyword: 關鍵字搜尋
        page: 頁碼
        page_size: 每頁數量

    Example:
        >>> query = LogQueryRequest(
        ...     log_level="ERROR",
        ...     module="trading",
        ...     keyword="timeout",
        ...     page=1,
        ...     page_size=50
        ... )
    """
    start_time: Optional[datetime] = Field(default=None, description="開始時間")
    end_time: Optional[datetime] = Field(default=None, description="結束時間")
    log_level: Optional[str] = Field(default=None, description="日誌級別")
    module: Optional[str] = Field(default=None, description="模組名稱")
    keyword: Optional[str] = Field(default=None, description="關鍵字搜尋")
    page: int = Field(default=1, ge=1, description="頁碼")
    page_size: int = Field(default=50, ge=1, le=1000, description="每頁數量")

    @validator('log_level')
    def validate_log_level(cls, v):  # pylint: disable=no-self-argument
        """驗證日誌級別

        Args:
            v: 待驗證的日誌級別

        Returns:
            str: 驗證通過的日誌級別

        Raises:
            ValueError: 當日誌級別不在允許列表中時
        """
        if v is not None:
            allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if v.upper() not in allowed_levels:
                raise ValueError(f'日誌級別必須是: {", ".join(allowed_levels)}')
            return v.upper()
        return v

    @validator('end_time')
    def validate_time_range(cls, v, values):  # pylint: disable=no-self-argument
        """驗證時間範圍

        Args:
            v: 結束時間
            values: 其他欄位值

        Returns:
            datetime: 驗證通過的結束時間

        Raises:
            ValueError: 當結束時間不晚於開始時間時
        """
        if v is not None and values.get('start_time') is not None:
            if v <= values['start_time']:
                raise ValueError('結束時間必須大於開始時間')
        return v


class AlertUpdateRequest(BaseModel):
    """警報更新請求模型

    此模型定義了更新警報時可以修改的欄位。

    Attributes:
        acknowledged: 是否已確認
        acknowledged_by: 確認人
        resolved: 是否已解決
        resolved_by: 解決人
        notes: 備註

    Note:
        所有欄位都是可選的，只有提供的欄位會被更新
    """
    acknowledged: Optional[bool] = Field(default=None, description="是否已確認")
    acknowledged_by: Optional[str] = Field(default=None, description="確認人")
    resolved: Optional[bool] = Field(default=None, description="是否已解決")
    resolved_by: Optional[str] = Field(default=None, description="解決人")
    notes: Optional[str] = Field(default=None, max_length=1000, description="備註")


class SystemReportRequest(BaseModel):
    """系統報表請求模型

    此模型定義了生成系統報表時需要的參數。

    Attributes:
        report_type: 報表類型
        period_start: 統計期間開始
        period_end: 統計期間結束
        include_details: 是否包含詳細資訊
        format: 報表格式

    Example:
        >>> request = SystemReportRequest(
        ...     report_type="performance",
        ...     period_start=datetime(2024, 1, 1),
        ...     period_end=datetime(2024, 1, 31),
        ...     format="pdf"
        ... )
    """
    report_type: str = Field(..., description="報表類型")
    period_start: datetime = Field(..., description="統計期間開始")
    period_end: datetime = Field(..., description="統計期間結束")
    include_details: bool = Field(default=True, description="是否包含詳細資訊")
    report_format: str = Field(default="json", description="報表格式")

    @validator('report_type')
    def validate_report_type(cls, v):  # pylint: disable=no-self-argument
        """驗證報表類型

        Args:
            v: 待驗證的報表類型

        Returns:
            str: 驗證通過的報表類型

        Raises:
            ValueError: 當報表類型不在允許列表中時
        """
        allowed_types = ['system', 'performance', 'alerts', 'comprehensive']
        if v not in allowed_types:
            raise ValueError(f'報表類型必須是: {", ".join(allowed_types)}')
        return v

    @validator('report_format')
    def validate_report_format(cls, v):  # pylint: disable=no-self-argument
        """驗證報表格式

        Args:
            v: 待驗證的報表格式

        Returns:
            str: 驗證通過的報表格式

        Raises:
            ValueError: 當報表格式不在允許列表中時
        """
        allowed_formats = ['json', 'pdf', 'excel', 'csv']
        if v.lower() not in allowed_formats:
            raise ValueError(f'報表格式必須是: {", ".join(allowed_formats)}')
        return v.lower()

    @validator('period_end')
    def validate_period_range(cls, v, values):  # pylint: disable=no-self-argument
        """驗證統計期間範圍

        Args:
            v: 統計期間結束時間
            values: 其他欄位值

        Returns:
            datetime: 驗證通過的結束時間

        Raises:
            ValueError: 當結束時間不晚於開始時間時
        """
        if 'period_start' in values and v <= values['period_start']:
            raise ValueError('統計期間結束時間必須大於開始時間')
        return v
