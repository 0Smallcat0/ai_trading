# -*- coding: utf-8 -*-
"""風險管理資料庫模型

此模組定義了風險管理相關的資料庫模型。

Classes:
    RiskParameter: 風險參數模型
    RiskControlStatus: 風險控制狀態模型
    RiskAlert: 風險警報模型
    RiskLog: 風險日誌模型

Example:
    >>> from src.database.models.risk_management_models import RiskParameter
    >>> param = RiskParameter(
    ...     parameter_name="stop_loss_percent",
    ...     parameter_value="5.0",
    ...     parameter_type="float",
    ...     category="stop_loss"
    ... )
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float,
    UniqueConstraint, Index
)

from .base_models import Base


class RiskParameter(Base):
    """風險參數模型
    
    儲存系統的風險管理參數配置。
    
    Attributes:
        id: 主鍵
        parameter_name: 參數名稱
        parameter_value: 參數值（字串格式）
        parameter_type: 參數類型（string, int, float, bool）
        category: 參數分類
        description: 參數描述
        is_system: 是否為系統參數
        is_active: 是否啟用
        min_value: 最小值
        max_value: 最大值
        default_value: 預設值
        updated_at: 更新時間
        created_at: 創建時間
    """
    
    __tablename__ = "risk_parameters"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    parameter_name = Column(String(50), nullable=False, unique=True)
    parameter_value = Column(String(100), nullable=False)
    parameter_type = Column(String(20), default="string")
    category = Column(String(50), default="general")
    description = Column(Text, default="")
    is_system = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    min_value = Column(String(50), nullable=True)
    max_value = Column(String(50), nullable=True)
    default_value = Column(String(100), nullable=True)
    updated_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    # 索引
    __table_args__ = (
        Index('idx_risk_parameter_name', 'parameter_name'),
        Index('idx_risk_parameter_category', 'category'),
        Index('idx_risk_parameter_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<RiskParameter(name='{self.parameter_name}', value='{self.parameter_value}')>"


class RiskControlStatus(Base):
    """風險控制狀態模型
    
    儲存各種風險控制機制的狀態。
    
    Attributes:
        id: 主鍵
        control_name: 控制機制名稱
        control_type: 控制機制類型
        is_enabled: 是否啟用
        is_master_enabled: 主開關是否啟用
        emergency_stop: 是否緊急停止
        status_name: 狀態名稱（向後兼容）
        is_active: 是否活躍（向後兼容）
        last_triggered: 最後觸發時間
        trigger_count: 觸發次數
        description: 描述
        created_at: 創建時間
        updated_at: 更新時間
    """
    
    __tablename__ = "risk_control_status"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    control_name = Column(String(50), nullable=False, unique=True)
    control_type = Column(String(50), default="general")
    is_enabled = Column(Boolean, default=True)
    is_master_enabled = Column(Boolean, default=True)
    emergency_stop = Column(Boolean, default=False)
    status_name = Column(String(50), nullable=True)  # 向後兼容
    is_active = Column(Boolean, default=True)  # 向後兼容
    last_triggered = Column(DateTime, nullable=True)
    trigger_count = Column(Integer, default=0)
    description = Column(Text, default="")
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(DateTime, nullable=True)
    
    # 索引
    __table_args__ = (
        Index('idx_risk_control_name', 'control_name'),
        Index('idx_risk_control_type', 'control_type'),
        Index('idx_risk_control_enabled', 'is_enabled'),
    )
    
    def __repr__(self):
        return f"<RiskControlStatus(name='{self.control_name}', enabled={self.is_enabled})>"


class RiskAlert(Base):
    """風險警報模型
    
    儲存風險警報記錄。
    
    Attributes:
        id: 主鍵
        alert_id: 警報ID（唯一標識）
        alert_type: 警報類型
        severity: 嚴重程度
        title: 警報標題
        message: 警報訊息
        symbol: 相關股票代碼
        portfolio_id: 相關投資組合ID
        metric_value: 指標值
        threshold_value: 閾值
        acknowledged: 是否已確認
        acknowledged_at: 確認時間
        acknowledged_by: 確認人
        created_at: 創建時間
        resolved_at: 解決時間
    """
    
    __tablename__ = "risk_alerts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(50), nullable=False, unique=True)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    symbol = Column(String(20), nullable=True)
    portfolio_id = Column(String(50), nullable=True)
    metric_value = Column(Float, nullable=True)
    threshold_value = Column(Float, nullable=True)
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(50), nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    resolved_at = Column(DateTime, nullable=True)
    
    # 索引
    __table_args__ = (
        Index('idx_risk_alert_id', 'alert_id'),
        Index('idx_risk_alert_type', 'alert_type'),
        Index('idx_risk_alert_severity', 'severity'),
        Index('idx_risk_alert_symbol', 'symbol'),
        Index('idx_risk_alert_acknowledged', 'acknowledged'),
        Index('idx_risk_alert_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<RiskAlert(id='{self.alert_id}', type='{self.alert_type}', severity='{self.severity}')>"


class RiskLog(Base):
    """風險日誌模型
    
    儲存風險管理操作日誌。
    
    Attributes:
        id: 主鍵
        log_type: 日誌類型
        operation: 操作類型
        description: 操作描述
        user_id: 操作用戶ID
        symbol: 相關股票代碼
        portfolio_id: 相關投資組合ID
        old_value: 舊值
        new_value: 新值
        result: 操作結果
        error_message: 錯誤訊息
        created_at: 創建時間
    """
    
    __tablename__ = "risk_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    log_type = Column(String(50), nullable=False)  # parameter, control, alert, etc.
    operation = Column(String(50), nullable=False)  # create, update, delete, trigger
    description = Column(Text, nullable=False)
    user_id = Column(String(50), nullable=True)
    symbol = Column(String(20), nullable=True)
    portfolio_id = Column(String(50), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    result = Column(String(20), nullable=False)  # success, failure, warning
    error_message = Column(Text, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    # 索引
    __table_args__ = (
        Index('idx_risk_log_type', 'log_type'),
        Index('idx_risk_log_operation', 'operation'),
        Index('idx_risk_log_user', 'user_id'),
        Index('idx_risk_log_symbol', 'symbol'),
        Index('idx_risk_log_result', 'result'),
        Index('idx_risk_log_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<RiskLog(type='{self.log_type}', operation='{self.operation}', result='{self.result}')>"
